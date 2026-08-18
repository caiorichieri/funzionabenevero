"""Booking finalization service.

Owns the APScheduler instance and the post-payment booking side-effects
(Daily.co room provisioning, confirmation emails, reminder scheduling).
"""
import hashlib
import logging
import os
import secrets as _secrets
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bson import ObjectId

from deps import db, find_user_by_id
from daily_service import create_room_for_appointment
from email_service import send_booking_confirmation_email, send_reminder_email
from sms_service import send_sms_reminder

# Single scheduler instance used by the whole app.
scheduler = AsyncIOScheduler()

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


def schedule_reminders(app_id: str, ctx: dict) -> None:
    """Schedule multi-step reminders for an appointment:
    - 24h before: email (no link)
    - 1h before: email (announces link arrival)
    - 30min before: SMS (paziente)
    - 15min before: email with magic-link direct-join button
    """
    try:
        start = datetime.fromisoformat(ctx["data_ora"].replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)

        jobs = [
            (start - timedelta(days=1),      send_reminder_email,   [ctx, "1-giorno"], f"rem1d-{app_id}"),
            (start - timedelta(hours=1),     send_reminder_email,   [ctx, "1-ora"],    f"rem1h-{app_id}"),
            (start - timedelta(minutes=30),  _send_sms_30min_reminder, [app_id, ctx],  f"sms30m-{app_id}"),
            (start - timedelta(minutes=15),  send_reminder_email,   [ctx, "15-min"],   f"rem15m-{app_id}"),
        ]
        for run_at, fn, args, job_id in jobs:
            if run_at > now:
                scheduler.add_job(fn, "date", run_date=run_at, args=args, id=job_id, replace_existing=True)
    except Exception as e:
        logging.error(f"[SCHEDULER] failed to schedule reminders: {e}")


async def finalize_confirmed_booking(appointment_id: str, paziente_user: dict):
    """Provision Daily.co room + generate reschedule token + send confirmation emails + schedule reminders.
    Called AFTER the payment succeeds. Idempotent."""
    appt = await db.appuntamenti.find_one({"_id": ObjectId(appointment_id)})
    if not appt:
        return None
    if not appt.get("daily_room_url"):
        room = await create_room_for_appointment(appointment_id, appt["data_ora"], appt["durata_minuti"])
        if room:
            await db.appuntamenti.update_one(
                {"_id": ObjectId(appointment_id)},
                {"$set": {"daily_room_url": room.get("room_url"), "daily_room_name": room.get("room_name")}},
            )
            appt["daily_room_url"] = room.get("room_url")
            appt["daily_room_name"] = room.get("room_name")

    # Generate a single-use reschedule token (valid until 1 hour before appointment)
    raw_token = None
    if not appt.get("riprogramma_token_hash"):
        raw_token = _secrets.token_urlsafe(32)
        try:
            start = datetime.fromisoformat(appt["data_ora"].replace("Z", "+00:00"))
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            expires = start - timedelta(hours=1)
        except Exception:
            expires = datetime.now(timezone.utc) + timedelta(days=RESCHEDULE_TOKEN_DAYS)
        await db.appuntamenti.update_one(
            {"_id": ObjectId(appointment_id)},
            {"$set": {
                "riprogramma_token_hash": _token_digest(raw_token),
                "riprogramma_token_expires": expires,
            }},
        )

    # Generate a magic token for the direct-join videocall link (email 15 min before).
    # Valid from 20 min before start to 30 min after start (grace).
    raw_magic = None
    if not appt.get("videocall_magic_hash"):
        raw_magic = _secrets.token_urlsafe(32)
        try:
            start = datetime.fromisoformat(appt["data_ora"].replace("Z", "+00:00"))
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            magic_expires = start + timedelta(minutes=int(appt.get("durata_minuti", 50)) + 15)
        except Exception:
            magic_expires = datetime.now(timezone.utc) + timedelta(days=1)
        await db.appuntamenti.update_one(
            {"_id": ObjectId(appointment_id)},
            {"$set": {
                "videocall_magic_hash": _token_digest(raw_magic),
                "videocall_magic_expires": magic_expires,
            }},
        )

    if appt.get("_confirmation_email_sent"):
        return appt

    try:
        terapista = await db.terapisti.find_one({"_id": ObjectId(appt["terapeuta_id"])})
        paziente = await db.pazienti.find_one({"_id": ObjectId(appt["paziente_id"])})
        if terapista and paziente:
            t_user = await find_user_by_id(terapista.get("user_id"))
            frontend = (os.environ.get("FRONTEND_URL") or "https://funzionabene.it").rstrip("/")
            reschedule_url = (
                f"{frontend}/riprogramma/{appointment_id}?token={raw_token}" if raw_token else None
            )
            videocall_url = (
                f"{frontend}/videocall/{appointment_id}?token={raw_magic}" if raw_magic else None
            )
            ctx = {
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
            await send_booking_confirmation_email(ctx)
            schedule_reminders(appointment_id, ctx)
        await db.appuntamenti.update_one(
            {"_id": ObjectId(appointment_id)},
            {"$set": {"_confirmation_email_sent": True}},
        )
    except Exception as e:
        logging.error(f"[BOOKING EMAIL] failed: {e}")
    return appt
