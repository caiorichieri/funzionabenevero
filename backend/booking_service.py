"""Booking finalization service.

Owns the APScheduler instance and the post-payment booking side-effects
(Daily.co room provisioning, confirmation emails, reminder scheduling).
"""
import hashlib
import logging
import os
import secrets as _secrets
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.mongodb import MongoDBJobStore
from bson import ObjectId

from deps import db, find_user_by_id
from daily_service import create_room_for_appointment
from email_service import send_booking_confirmation_email, send_reminder_email
from sms_service import send_sms_reminder
from routers.informed_consents import ensure_consent_for_booking

# Persistent scheduler — jobs survive backend restarts/deploys.
# Uses MongoDB as the jobstore so reminder emails scheduled hours or days
# in advance don't disappear when the pod restarts.
_mongo_url = os.environ["MONGO_URL"]
_db_name = os.environ["DB_NAME"]
scheduler = AsyncIOScheduler(
    jobstores={"default": MongoDBJobStore(database=_db_name, collection="apscheduler_jobs", host=_mongo_url)},
    timezone="UTC",
)

# Reschedule link is valid up to appointment start
RESCHEDULE_TOKEN_DAYS = 30


def _token_digest(raw: str) -> str:
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()
        logging.info("[SCHEDULER] started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()


def _format_sms_datetime(iso_str: str) -> str:
    """Return a short IT date/time like '12/03 alle 15:30'."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        # Convert to Europe/Rome for user-facing display
        try:
            from zoneinfo import ZoneInfo
            dt = dt.astimezone(ZoneInfo("Europe/Rome"))
        except Exception:
            pass
        return dt.strftime("%d/%m alle %H:%M")
    except Exception:
        return iso_str


async def _send_sms_30min_reminder(app_id: str, ctx: dict) -> None:
    """SMS reminder 30 minutes before session (paziente only)."""
    phone = ctx.get("paziente_phone")
    if not phone:
        return
    dt_short = _format_sms_datetime(ctx["data_ora"])
    text = (
        f"FunzionaBene: la tua seduta con Dr. {ctx['terapista_cognome']} inizia alle {dt_short}. "
        f"Riceverai il link di accesso via email 15 min prima. Trovi tutto anche in area personale."
    )
    await send_sms_reminder(phone, text)


async def _send_review_invite_email(app_id: str, ctx: dict) -> None:
    """Post-session email inviting the patient to leave a review.

    Also transitions status `in_corso` → `completato` for sessions that both
    participants attended but never got auto-closed. This is the single
    guaranteed post-session hook, so we piggy-back the state cleanup here.

    Thin wrapper that delegates to `email_service.send_review_invite_email` so
    the send goes through the standard `_send_tracked` pipeline (email_events
    audit trail, Resend tags for opened/clicked webhooks).
    """
    try:
        # Auto-complete the appointment if the session ended cleanly (both attended).
        await _auto_complete_appointment(app_id)

        from email_service import send_review_invite_email
        if not ctx.get("paziente_email"):
            return
        await send_review_invite_email(
            paziente_email=ctx["paziente_email"],
            paziente_nome=ctx.get("paziente_nome", "") or "",
            terapista_cognome=ctx.get("terapista_cognome", "") or "",
            appuntamento_id=app_id,
            paziente_id=ctx.get("paziente_id"),
            terapista_id=ctx.get("terapista_id"),
        )
    except Exception as e:
        logging.error(f"[REVIEW-INVITE] failed: {e}")


async def _auto_complete_appointment(app_id: str) -> None:
    """Transition `in_corso` → `completato` if the session end has passed.

    Fixes the bug where `no_show_service` set `in_corso` at start+15min when
    both participants attended, but never had a hook to move the state to
    `completato` afterwards.
    """
    try:
        appt = await db.appuntamenti.find_one({"_id": ObjectId(app_id)})
        if not appt or appt.get("stato") != "in_corso":
            return
        await db.appuntamenti.update_one(
            {"_id": ObjectId(app_id), "stato": "in_corso"},
            {"$set": {
                "stato": "completato",
                "completato_at": datetime.now(timezone.utc),
                "completato_source": "auto_post_session",
            }},
        )
        logging.info(f"[AUTO-COMPLETE] appuntamento {app_id} marked completato")
    except Exception as e:
        logging.error(f"[AUTO-COMPLETE] failed for {app_id}: {e}")


async def sweep_stale_in_corso() -> int:
    """Startup sweep: any `in_corso` appointment whose session end + 30min is
    already in the past gets flipped to `completato`. Handles:
      - historical rows stuck before the auto_complete hook existed
      - rows for which the review-invite job failed to fire (crash, restart, etc.)
    Returns the number of rows updated.
    """
    try:
        now = datetime.now(timezone.utc)
        cursor = db.appuntamenti.find({"stato": "in_corso"})
        updated = 0
        async for appt in cursor:
            try:
                raw = appt.get("data_ora")
                if not raw:
                    continue
                start = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                dur = int(appt.get("durata_minuti") or 50)
                if start + timedelta(minutes=dur + 30) < now:
                    await db.appuntamenti.update_one(
                        {"_id": appt["_id"], "stato": "in_corso"},
                        {"$set": {
                            "stato": "completato",
                            "completato_at": now,
                            "completato_source": "sweep_startup",
                        }},
                    )
                    updated += 1
            except Exception as inner:
                logging.warning(f"[SWEEP] skipped {appt.get('_id')}: {inner}")
        if updated:
            logging.info(f"[SWEEP] auto-completed {updated} stale in_corso appointments")
        return updated
    except Exception as e:
        logging.error(f"[SWEEP] failed: {e}")
        return 0


def _reminder_job_ids(app_id: str) -> list[str]:
    """All APScheduler job ids owned by a single appointment. Kept in ONE place
    so cancel + re-schedule stay in sync. Includes both reminder and no-show
    jobs registered by schedule_reminders + schedule_no_show_check."""
    return [
        f"rem1d-{app_id}", f"rem1h-{app_id}", f"sms30m-{app_id}",
        f"rem15m-{app_id}", f"review-{app_id}",
        f"noshow-final-{app_id}", f"noshow-post-{app_id}", f"noshow-24h-{app_id}",
    ]


def cancel_scheduled_jobs(app_id: str) -> None:
    """Cancel all reminder + no-show jobs for an appointment. Called when the
    appt is rescheduled (creates a new id) or cancelled outright. Never raises."""
    for jid in _reminder_job_ids(app_id):
        try:
            scheduler.remove_job(jid)
        except Exception:
            # JobLookupError when the job doesn't exist — ignore.
            pass


def schedule_reminders(app_id: str, ctx: dict) -> None:
    """Schedule multi-step reminders for an appointment. All run-times derive
    from the appointment's `data_ora` interpreted in **Europe/Rome** (the fiscal
    timezone of record). Naive stored strings are treated as Rome-local; ISO
    strings with explicit offset are honoured as given. Idempotent via
    `replace_existing=True` — safe to call again after a reschedule.

    Scheduled jobs (all id-namespaced by app_id — see `_reminder_job_ids`):
    - 24h before: email (no link)
    - 1h before: email (announces link arrival)
    - 30min before: SMS (paziente)
    - 15min before: email with magic-link direct-join button
    - +durata+30min after start: review invite
    - Also registers the 3 no-show jobs via schedule_no_show_check.
    """
    try:
        rome_tz = ZoneInfo("Europe/Rome")
        raw = ctx.get("data_ora") or ""
        # Prefer explicit tz-aware parse. If the ISO has no offset (legacy naive
        # values), interpret as Rome-local — the source of truth for scheduling.
        try:
            parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except Exception:
            logging.error(f"[SCHEDULER] unparseable data_ora for appt={app_id}: {raw!r}")
            return
        if parsed.tzinfo is None:
            start = parsed.replace(tzinfo=rome_tz)
        else:
            start = parsed
        # Always normalise to UTC for APScheduler (its default job store also
        # uses UTC) — this stays timezone-correct across DST transitions.
        start = start.astimezone(timezone.utc)
        now = datetime.now(timezone.utc)

        durata = int(ctx.get("durata_minuti", 50))
        jobs = [
            (start - timedelta(days=1),      send_reminder_email,      [ctx, "1-giorno"], f"rem1d-{app_id}"),
            (start - timedelta(hours=1),     send_reminder_email,      [ctx, "1-ora"],    f"rem1h-{app_id}"),
            (start - timedelta(minutes=30),  _send_sms_30min_reminder, [app_id, ctx],     f"sms30m-{app_id}"),
            (start - timedelta(minutes=15),  send_reminder_email,      [ctx, "15-min"],   f"rem15m-{app_id}"),
            (start + timedelta(minutes=durata + 30), _send_review_invite_email, [app_id, ctx], f"review-{app_id}"),
        ]
        for run_at, fn, args, job_id in jobs:
            if run_at > now:
                scheduler.add_job(fn, "date", run_date=run_at, args=args, id=job_id, replace_existing=True)

        # Register the no-show detection jobs (final @ start+15min + follow-ups)
        try:
            from no_show_service import schedule_no_show_check
            # Pass the corrected (aware UTC) ISO so no-show service uses the
            # same interpretation of Rome-local naive strings.
            schedule_no_show_check(scheduler, app_id, start.isoformat(), durata)
        except Exception as e:
            logging.error(f"[SCHEDULER] failed to schedule no-show check: {e}")
    except Exception as e:
        logging.error(f"[SCHEDULER] failed to schedule reminders: {e}")


def reschedule_reminders(old_app_id: str, new_app_id: str, ctx: dict) -> None:
    """When an appointment is rescheduled (new time OR new id), drop the old
    jobs and register fresh ones bound to the new id + new time.
    Both no-op safely if the old jobs don't exist."""
    cancel_scheduled_jobs(old_app_id)
    if new_app_id and ctx:
        schedule_reminders(new_app_id, ctx)


async def _ensure_informed_consent(appointment_id: str, appt: dict, paziente_user: dict) -> None:
    """Trigger informed-consent flow (creates pending + email if missing)."""
    try:
        has_consent, _ = await ensure_consent_for_booking(
            paziente_id=paziente_user["_id"],
            terapista_id=appt["terapeuta_id"],
        )
        await db.appuntamenti.update_one(
            {"_id": ObjectId(appointment_id)},
            {"$set": {"consenso_informato_ok": has_consent}},
        )
    except Exception as e:
        logging.error(f"[CONSENT] ensure_consent_for_booking failed: {e}")


async def _ensure_daily_room(appointment_id: str, appt: dict) -> None:
    """Create Daily.co video room if not yet provisioned. Mutates `appt` in place."""
    if appt.get("daily_room_url"):
        return
    room = await create_room_for_appointment(
        appointment_id, appt["data_ora"], appt["durata_minuti"],
    )
    if room:
        await db.appuntamenti.update_one(
            {"_id": ObjectId(appointment_id)},
            {"$set": {"daily_room_url": room.get("room_url"), "daily_room_name": room.get("room_name")}},
        )
        appt["daily_room_url"] = room.get("room_url")
        appt["daily_room_name"] = room.get("room_name")


def _parse_start(appt: dict) -> datetime:
    """Parse ISO data_ora into an aware UTC datetime. Falls back to now()."""
    try:
        start = datetime.fromisoformat(appt["data_ora"].replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        return start
    except Exception:
        return datetime.now(timezone.utc)


async def _ensure_reschedule_token(appointment_id: str, appt: dict) -> str | None:
    """Generate a single-use reschedule token (expires 1h before appt). Returns raw or None."""
    if appt.get("riprogramma_token_hash"):
        return None
    raw = _secrets.token_urlsafe(32)
    expires = _parse_start(appt) - timedelta(hours=1)
    await db.appuntamenti.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": {
            "riprogramma_token_hash": _token_digest(raw),
            "riprogramma_token_expires": expires,
        }},
    )
    return raw


async def _ensure_videocall_magic_token(appointment_id: str, appt: dict) -> str | None:
    """Generate a magic token for direct-join videocall link. Returns raw or None.
    Expiry mirrors the logged-in join window: `start + durata + 15 min` — this
    lets a patient re-enter via the email link if they get disconnected mid-
    session. The no-show detection cutoff (at start+15 min) is handled by the
    scheduled job in no_show_service and does NOT block entry."""
    if appt.get("videocall_magic_hash"):
        return None
    raw = _secrets.token_urlsafe(32)
    durata = int(appt.get("durata_minuti", 50))
    magic_expires = _parse_start(appt) + timedelta(minutes=durata + 15)
    await db.appuntamenti.update_one(
        {"_id": ObjectId(appointment_id)},
        {"$set": {
            "videocall_magic_hash": _token_digest(raw),
            "videocall_magic_expires": magic_expires,
        }},
    )
    return raw


async def _build_notification_ctx(
    appointment_id: str, appt: dict, paziente_user: dict,
    raw_reschedule_token: str | None, raw_magic_token: str | None,
) -> dict | None:
    """Assemble the ctx dict passed to email templates + reminder scheduler."""
    terapista = await db.terapisti.find_one({"_id": ObjectId(appt["terapeuta_id"])})
    paziente = await db.pazienti.find_one({"_id": ObjectId(appt["paziente_id"])})
    if not terapista or not paziente:
        return None
    t_user = await find_user_by_id(terapista.get("user_id"))
    frontend = (os.environ.get("FRONTEND_URL") or "https://funzionabene.it").rstrip("/")
    reschedule_url = f"{frontend}/riprogramma/{appointment_id}?token={raw_reschedule_token}" if raw_reschedule_token else None
    videocall_url = f"{frontend}/videocall/{appointment_id}?token={raw_magic_token}" if raw_magic_token else None
    return {
        "paziente_nome": paziente.get("nome", ""),
        "paziente_cognome": paziente.get("cognome", ""),
        "paziente_email": paziente_user.get("email"),
        "paziente_phone": paziente_user.get("telefono") or paziente.get("telefono"),
        "terapista_nome": terapista.get("nome", ""),
        "terapista_cognome": terapista.get("cognome", ""),
        "terapista_email": t_user.get("email") if t_user else None,
        "data_ora": appt["data_ora"],
        "durata_minuti": appt["durata_minuti"],
        "prezzo": terapista.get("prezzo_sessione", 90),
        "room_url": appt.get("daily_room_url"),
        "app_id": appointment_id,
        "reschedule_url": reschedule_url,
        "videocall_url": videocall_url,
    }


async def _send_confirmation_and_schedule(appointment_id: str, ctx: dict) -> None:
    """Send booking confirmation email + register the reminder jobs."""
    await send_booking_confirmation_email(ctx)
    schedule_reminders(appointment_id, ctx)


async def finalize_confirmed_booking(appointment_id: str, paziente_user: dict):
    """Provision Daily.co room + generate tokens + send confirmation emails + schedule reminders.
    Called AFTER the payment succeeds. Idempotent — safe to call multiple times."""
    appt = await db.appuntamenti.find_one({"_id": ObjectId(appointment_id)})
    if not appt:
        return None

    # 1. Kick off informed consent flow (patient ↔ therapist) if missing
    await _ensure_informed_consent(appointment_id, appt, paziente_user)

    # 2. Provision the Daily.co video room
    await _ensure_daily_room(appointment_id, appt)

    # 3. Generate single-use tokens (reschedule + videocall magic link)
    raw_reschedule = await _ensure_reschedule_token(appointment_id, appt)
    raw_magic = await _ensure_videocall_magic_token(appointment_id, appt)

    # 4. Skip email/reminders if already sent (idempotency)
    if appt.get("_confirmation_email_sent"):
        return appt

    try:
        ctx = await _build_notification_ctx(appointment_id, appt, paziente_user, raw_reschedule, raw_magic)
        if ctx:
            await _send_confirmation_and_schedule(appointment_id, ctx)
        await db.appuntamenti.update_one(
            {"_id": ObjectId(appointment_id)},
            {"$set": {"_confirmation_email_sent": True}},
        )
    except Exception as e:
        logging.error(f"[BOOKING EMAIL] failed: {e}")
    return appt
