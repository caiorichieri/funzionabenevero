"""Booking finalization service.

Owns the APScheduler instance and the post-payment booking side-effects
(Daily.co room provisioning, confirmation emails, reminder scheduling).

Extracted from server.py so that routers/payments.py can call
`_finalize_confirmed_booking` directly (no lazy `from server import ...`).
"""
import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from bson import ObjectId

from deps import db
from daily_service import create_room_for_appointment
from email_service import send_booking_confirmation_email, send_reminder_email

# Single scheduler instance used by the whole app.
scheduler = AsyncIOScheduler()


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()
        logging.info("[SCHEDULER] started")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown()


def schedule_reminders(app_id: str, ctx: dict) -> None:
    """Schedule 1-day-before and 1-hour-before reminder emails for a booking."""
    try:
        start = datetime.fromisoformat(ctx["data_ora"].replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        one_day = start - timedelta(days=1)
        one_hour = start - timedelta(hours=1)
        now = datetime.now(timezone.utc)
        if one_day > now:
            scheduler.add_job(
                send_reminder_email, "date", run_date=one_day,
                args=[ctx, "1-giorno"], id=f"rem1d-{app_id}", replace_existing=True,
            )
        if one_hour > now:
            scheduler.add_job(
                send_reminder_email, "date", run_date=one_hour,
                args=[ctx, "1-ora"], id=f"rem1h-{app_id}", replace_existing=True,
            )
    except Exception as e:
        logging.error(f"[SCHEDULER] failed to schedule reminders: {e}")


async def finalize_confirmed_booking(appointment_id: str, paziente_user: dict):
    """Provision Daily.co room + send confirmation emails + schedule reminders.

    Called AFTER the payment succeeds (webhook or polling).
    Idempotent: only creates the room / sends emails once.
    """
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
    if appt.get("_confirmation_email_sent"):
        return appt
    try:
        terapista = await db.terapisti.find_one({"_id": ObjectId(appt["terapeuta_id"])})
        paziente = await db.pazienti.find_one({"_id": ObjectId(appt["paziente_id"])})
        if terapista and paziente:
            t_user = await db.users.find_one({"_id": terapista.get("user_id")})
            ctx = {
                "paziente_nome": paziente.get("nome", ""),
                "paziente_cognome": paziente.get("cognome", ""),
                "paziente_email": paziente_user.get("email"),
                "terapista_nome": terapista.get("nome", ""),
                "terapista_cognome": terapista.get("cognome", ""),
                "terapista_email": t_user.get("email") if t_user else None,
                "data_ora": appt["data_ora"],
                "durata_minuti": appt["durata_minuti"],
                "prezzo": terapista.get("prezzo_sessione", 90),
                "room_url": appt.get("daily_room_url"),
                "app_id": appointment_id,
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
