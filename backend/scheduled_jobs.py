"""Scheduled background jobs — runs inside the FastAPI process via APScheduler.

Jobs:
 - retention_anonymize: weekly, anonymizes pazienti inactive >= 36 months
 - process_legal_declines: hourly, hard-deactivates users whose 48h grace has expired
   (cancels future appointments, refunds via Stripe, disables the profile)
"""
import logging
from datetime import datetime, timezone, timedelta
from bson import ObjectId

logger = logging.getLogger(__name__)


# Retention: 36 months for pazienti inactivity, then anonymize
INACTIVITY_MONTHS = 36


def _anonymize_user_fields(user_id: str) -> dict:
    """Return the $set payload that anonymizes a user account."""
    fake_email = f"anon-{user_id[-8:]}@anon.funzionabene.local"
    return {
        "email": fake_email,
        "nome": "Anonimo",
        "cognome": "",
        "telefono": None,
        "is_active": False,
        "gdpr_anonymized_at": datetime.now(timezone.utc),
        "gdpr_anonymized_reason": "inactivity_36_months",
    }


async def retention_anonymize(db) -> dict:
    """Anonymize inactive pazienti (36+ months since last activity).

    Fiscal data (fatture) are kept for 10 years by law and are NOT anonymized
    (they live in a separate collection `fatture` linked by user_id).
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=INACTIVITY_MONTHS * 30)

    # A user is "inactive" if their last activity (last_login_at OR created_at) is before cutoff
    # AND they are a paziente (never anonymize a terapeuta automatically — they have professional obligations)
    query = {
        "role": "paziente",
        "gdpr_anonymized_at": {"$exists": False},
        "$or": [
            {"last_login_at": {"$lt": cutoff}},
            {"$and": [{"last_login_at": {"$exists": False}}, {"created_at": {"$lt": cutoff}}]},
        ],
    }
    anonymized = 0
    skipped = 0
    async for u in db.users.find(query).limit(500):
        uid = str(u["_id"])
        # Skip if user has appointments in the last 36 months (safety net)
        has_recent_appt = await db.appuntamenti.find_one({
            "paziente_user_id": uid,
            "data_ora": {"$gte": cutoff.isoformat()},
        })
        if has_recent_appt:
            skipped += 1
            continue
        # Anonymize
        try:
            await db.users.update_one(
                {"_id": ObjectId(uid)},
                {"$set": _anonymize_user_fields(uid)},
            )
            # Anonymize paziente profile (keep it but strip PII)
            await db.pazienti.update_one(
                {"user_id": uid},
                {"$set": {
                    "nome": "Anonimo",
                    "cognome": "",
                    "telefono": None,
                    "indirizzo": None,
                    "note": None,
                    "gdpr_anonymized_at": now,
                }},
            )
            anonymized += 1
            logger.info(f"[RETENTION] anonymized user_id={uid}")
        except Exception as e:
            logger.exception(f"[RETENTION] failed to anonymize {uid}: {e}")

    logger.info(f"[RETENTION] complete — anonymized={anonymized} skipped={skipped}")
    return {"anonymized": anonymized, "skipped": skipped, "ran_at": now.isoformat()}


async def process_legal_declines(db) -> dict:
    """Hard-deactivate accounts whose 48h grace after legal_decline has expired.

    Steps:
     1. Cancel future confirmed appointments (paziente auto-refund via Stripe)
     2. Set user.is_active=false + terapista.sospeso=true (definitivo)
     3. Log event to admin_actions (audit trail)
    """
    now = datetime.now(timezone.utc)
    processed = 0
    errors = 0

    # Find users due for hard deactivation
    query = {
        "pending_deactivation_reason": "legal_decline",
        "pending_deactivation_at": {"$lt": now},
        "is_active": {"$ne": False},
    }

    async for u in db.users.find(query):
        uid = str(u["_id"])
        role = u.get("role")
        try:
            # 1. Cancel future confirmed appointments for terapeuti
            if role == "terapeuta":
                future = db.appuntamenti.find({
                    "terapeuta_user_id": uid,
                    "stato": {"$in": ["confermato", "prenotato"]},
                    "data_ora": {"$gte": now.isoformat()},
                })
                async for appt in future:
                    await db.appuntamenti.update_one(
                        {"_id": appt["_id"]},
                        {"$set": {
                            "stato": "cancellato",
                            "cancellato_motivo": "legal_decline_terapeuta",
                            "cancellato_at": now,
                            "rimborso_pending": True,  # to be picked up by refund worker
                        }},
                    )
            # 2. Hard deactivate
            await db.users.update_one(
                {"_id": ObjectId(uid)},
                {"$set": {
                    "is_active": False,
                    "legal_decline_deactivated_at": now,
                }, "$unset": {
                    "pending_deactivation_reason": "",
                    "pending_deactivation_at": "",
                }},
            )
            if role == "terapeuta":
                await db.terapisti.update_one(
                    {"user_id": uid},
                    {"$set": {"sospeso": True, "sospeso_motivo": "legal_decline_definitive", "sospeso_at": now}},
                )
            # 3. Audit log
            await db.admin_actions.insert_one({
                "action": "legal_decline_hard_deactivation",
                "user_id": uid,
                "user_email": u.get("email"),
                "user_role": role,
                "contract_kind": u.get("pending_deactivation_contract_kind"),
                "contract_version": u.get("pending_deactivation_contract_version"),
                "timestamp": now,
                "auto": True,
            })
            processed += 1
            logger.info(f"[LEGAL DECLINE JOB] hard-deactivated {uid} ({role})")
        except Exception as e:
            errors += 1
            logger.exception(f"[LEGAL DECLINE JOB] failed for {uid}: {e}")

    if processed or errors:
        logger.info(f"[LEGAL DECLINE JOB] complete — processed={processed} errors={errors}")
    return {"processed": processed, "errors": errors, "ran_at": now.isoformat()}


def register_jobs(scheduler, db):
    """Register all background jobs on the given AsyncIOScheduler."""
    # Weekly Sunday 03:00 UTC
    scheduler.add_job(
        retention_anonymize, "cron",
        day_of_week="sun", hour=3, minute=0,
        args=[db], id="retention_anonymize", replace_existing=True,
        max_instances=1, coalesce=True,
    )
    # Every hour at :07
    scheduler.add_job(
        process_legal_declines, "cron",
        minute=7,
        args=[db], id="process_legal_declines", replace_existing=True,
        max_instances=1, coalesce=True,
    )
    logger.info("[SCHEDULER] registered retention_anonymize (weekly) + process_legal_declines (hourly)")
