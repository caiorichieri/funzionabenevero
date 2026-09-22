"""No-show detection + attendance log snapshot for video sessions.

Fires at `start + 15 min` for every confirmed appointment: queries Daily.co for
who actually joined, persists a durable snapshot to `db.seduta_logs`, tags the
appointment with an outcome (`in_corso`, `no_show_paziente`, `no_show_terapeuta`,
`no_show_entrambi`), and triggers the follow-up emails.

Runs also periodically for 24h after start to keep the log up-to-date if people
join late.
"""
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId

from deps import db, find_user_by_id
from daily_service import get_room_presenza

logger = logging.getLogger(__name__)


OUTCOME_BOTH = "entrambi_presenti"
OUTCOME_NO_PAT = "no_show_paziente"
OUTCOME_NO_TER = "no_show_terapeuta"
OUTCOME_NONE = "no_show_entrambi"

HR_ALERT_EMAIL = os.environ.get("HR_EMAIL", "hr@funzionabene.it")


def _iso(dt) -> Optional[str]:
    if not dt:
        return None
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    return str(dt)


def _match_participant(presenze: list, target_names: list[str]) -> bool:
    """Return True if any participant's user_name matches (case-insensitive substring)."""
    if not presenze:
        return False
    for p in presenze:
        name = (p.get("user_name") or "").strip().lower()
        for t in target_names:
            t_low = (t or "").strip().lower()
            if not t_low or not name:
                continue
            if t_low in name or name in t_low:
                return True
    return False


async def _emit_snapshot(app_id: str, appt: dict) -> dict:
    """Query Daily and persist a fresh snapshot. Idempotent — reuses the same row."""
    room_name = appt.get("daily_room_name")
    presenze = []
    if room_name:
        try:
            presenze = await get_room_presenza(room_name)
        except Exception as e:
            logger.warning(f"[SEDUTA-LOG] Daily query failed for room={room_name}: {e}")

    # Resolve expected participant names
    terapista = await db.terapisti.find_one({"_id": ObjectId(appt["terapeuta_id"])}) if appt.get("terapeuta_id") else None
    paziente = await db.pazienti.find_one({"_id": ObjectId(appt["paziente_id"])}) if appt.get("paziente_id") else None
    ter_name = f"{(terapista or {}).get('nome','')} {(terapista or {}).get('cognome','')}".strip()
    paz_name = f"{(paziente or {}).get('nome','')} {(paziente or {}).get('cognome','')}".strip()

    paziente_joined = _match_participant(presenze, [paz_name, "paziente"])
    terapeuta_joined = _match_participant(presenze, [ter_name, "dr.", "dr "])

    if paziente_joined and terapeuta_joined:
        outcome = OUTCOME_BOTH
    elif paziente_joined and not terapeuta_joined:
        outcome = OUTCOME_NO_TER
    elif terapeuta_joined and not paziente_joined:
        outcome = OUTCOME_NO_PAT
    else:
        outcome = OUTCOME_NONE

    now = datetime.now(timezone.utc)
    snap = {
        "appuntamento_id": app_id,
        "terapeuta_id": appt.get("terapeuta_id"),
        "paziente_id": appt.get("paziente_id"),
        "paziente_user_id": appt.get("paziente_user_id"),
        "terapeuta_user_id": appt.get("terapeuta_user_id"),
        "room_name": room_name,
        "presenze": presenze,
        "paziente_joined": paziente_joined,
        "terapeuta_joined": terapeuta_joined,
        "outcome": outcome,
        "snapshot_at": now,
    }
    # Upsert on appuntamento_id — always keep the latest snapshot (most people
    # only enter once but late-joiners can change the outcome).
    await db.seduta_logs.update_one(
        {"appuntamento_id": app_id},
        {"$set": snap, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    return snap


async def _mark_appointment_outcome(app_id: str, outcome: str) -> None:
    """Set the appointment.stato based on outcome. Never overwrite a manual
    'completato'/'cancellato' state."""
    appt = await db.appuntamenti.find_one({"_id": ObjectId(app_id)})
    if not appt:
        return
    current = appt.get("stato")
    if current in ("completato", "cancellato", "cancellato_con_addebito"):
        return  # don't overwrite manual admin state
    new_stato = {
        OUTCOME_BOTH: "in_corso",
        OUTCOME_NO_PAT: "no_show_paziente",
        OUTCOME_NO_TER: "no_show_terapeuta",
        OUTCOME_NONE: "no_show_entrambi",
    }.get(outcome, current)
    await db.appuntamenti.update_one(
        {"_id": ObjectId(app_id)},
        {"$set": {"stato": new_stato, "outcome": outcome, "outcome_at": datetime.now(timezone.utc)}},
    )


async def _build_ctx(app_id: str, appt: dict) -> dict:
    terapista = await db.terapisti.find_one({"_id": ObjectId(appt["terapeuta_id"])}) if appt.get("terapeuta_id") else None
    paziente = await db.pazienti.find_one({"_id": ObjectId(appt["paziente_id"])}) if appt.get("paziente_id") else None
    paz_user = await find_user_by_id(appt.get("paziente_user_id"))
    ter_user = await find_user_by_id(terapista.get("user_id")) if terapista else None
    return {
        "app_id": app_id,
        "data_ora": appt.get("data_ora"),
        "terapista_nome": (terapista or {}).get("nome", ""),
        "terapista_cognome": (terapista or {}).get("cognome", ""),
        "terapista_id": appt.get("terapeuta_id"),
        "paziente_nome": (paziente or {}).get("nome", ""),
        "paziente_cognome": (paziente or {}).get("cognome", ""),
        "paziente_email": (paz_user or {}).get("email"),
        "terapista_email": (ter_user or {}).get("email"),
    }


async def _send_no_show_emails(outcome: str, ctx: dict) -> None:
    """Dispatch the correct follow-up emails based on outcome."""
    from email_service import (
        send_no_show_paziente_email,
        send_no_show_terapeuta_email,
        send_terapeuta_absent_paziente_email,
        send_terapeuta_absent_terapeuta_email,
        send_no_show_admin_alert,
    )
    try:
        if outcome == OUTCOME_NO_PAT:
            if ctx.get("paziente_email"):
                await send_no_show_paziente_email(ctx)
            if ctx.get("terapista_email"):
                await send_no_show_terapeuta_email(ctx)
        elif outcome == OUTCOME_NO_TER:
            if ctx.get("paziente_email"):
                await send_terapeuta_absent_paziente_email(ctx)
            if ctx.get("terapista_email"):
                await send_terapeuta_absent_terapeuta_email(ctx)
        elif outcome == OUTCOME_NONE:
            if ctx.get("paziente_email"):
                await send_no_show_paziente_email(ctx)
        # HR alert on every no-show variant
        if outcome != OUTCOME_BOTH:
            await send_no_show_admin_alert(HR_ALERT_EMAIL, outcome, ctx)
    except Exception as e:
        logger.exception(f"[NO-SHOW EMAIL] failed for {ctx.get('app_id')}: {e}")


async def run_no_show_check(app_id: str, is_final: bool = False) -> Optional[dict]:
    """Main entry point — invoked by APScheduler at start+15min.

    is_final=True → also mark the appointment status + fire follow-up emails.
    Later snapshots (is_final=False) only update the log so the presence
    record stays current if someone joins late.
    """
    appt = await db.appuntamenti.find_one({"_id": ObjectId(app_id)})
    if not appt:
        logger.warning(f"[NO-SHOW] appt {app_id} not found; skipping")
        return None
    # Skip if the appointment was cancelled before the session
    if appt.get("stato") in ("cancellato", "annullato", "payment_failed", "payment_expired"):
        return None

    snap = await _emit_snapshot(app_id, appt)
    if is_final:
        # Skip email dispatch if we already fired them (idempotency guard)
        already_notified = appt.get("no_show_notified_at")
        await _mark_appointment_outcome(app_id, snap["outcome"])
        if not already_notified:
            ctx = await _build_ctx(app_id, appt)
            await _send_no_show_emails(snap["outcome"], ctx)
            await db.appuntamenti.update_one(
                {"_id": ObjectId(app_id)},
                {"$set": {"no_show_notified_at": datetime.now(timezone.utc)}},
            )
    return snap


def schedule_no_show_check(scheduler, app_id: str, start_iso: str, durata_min: int = 50) -> None:
    """Register two APScheduler jobs for the given appointment:
     1. Final no-show check at start+15min (marks + emails).
     2. Follow-up snapshots at start+durata+15 and start+24h (keeps log fresh).
    Existing jobs with the same id are replaced (idempotent).
    """
    try:
        start = datetime.fromisoformat(start_iso.replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
    except Exception as e:
        logger.error(f"[NO-SHOW SCHED] invalid data_ora {start_iso}: {e}")
        return

    now = datetime.now(timezone.utc)
    final_at = start + timedelta(minutes=15)
    post_at = start + timedelta(minutes=int(durata_min) + 15)
    day_after_at = start + timedelta(hours=24)

    if final_at > now:
        scheduler.add_job(
            run_no_show_check, "date",
            run_date=final_at, args=[app_id, True],
            id=f"noshow-final-{app_id}", replace_existing=True,
            misfire_grace_time=3600,
        )
    if post_at > now:
        scheduler.add_job(
            run_no_show_check, "date",
            run_date=post_at, args=[app_id, False],
            id=f"noshow-post-{app_id}", replace_existing=True,
            misfire_grace_time=3600,
        )
    if day_after_at > now:
        scheduler.add_job(
            run_no_show_check, "date",
            run_date=day_after_at, args=[app_id, False],
            id=f"noshow-24h-{app_id}", replace_existing=True,
            misfire_grace_time=3600,
        )
    logger.info(f"[NO-SHOW SCHED] scheduled checks for appt={app_id} final_at={final_at.isoformat()}")
