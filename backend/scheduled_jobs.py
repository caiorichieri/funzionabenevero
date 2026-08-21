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
    # Weekly Sunday 20:00 UTC — send weekly fatture email to terapisti
    scheduler.add_job(
        weekly_fatture_email, "cron",
        day_of_week="sun", hour=20, minute=0,
        args=[db], id="weekly_fatture_email", replace_existing=True,
        max_instances=1, coalesce=True,
    )
    # Monthly 1st at 03:30 UTC — generate B2B commission invoices for previous month
    scheduler.add_job(
        monthly_generate_commissioni, "cron",
        day=1, hour=3, minute=30,
        args=[db], id="monthly_generate_commissioni", replace_existing=True,
        max_instances=1, coalesce=True,
    )
    # Daily 03:00 UTC — MongoDB backup to Backblaze B2 (skipped if not configured)
    try:
        from backup_service import run_backup, cleanup_old_backups
        scheduler.add_job(
            run_backup, "cron", hour=3, minute=0,
            id="db_backup_daily", replace_existing=True,
            max_instances=1, coalesce=True,
        )
        # Weekly Sunday 04:00 UTC — cleanup old backups (retention)
        scheduler.add_job(
            cleanup_old_backups, "cron",
            day_of_week="sun", hour=4, minute=0,
            id="db_backup_cleanup", replace_existing=True,
            max_instances=1, coalesce=True,
        )
    except Exception as e:
        logger.warning(f"[SCHEDULER] backup jobs not registered: {e}")
    logger.info("[SCHEDULER] registered retention_anonymize (weekly) + process_legal_declines (hourly) + weekly_fatture_email + monthly_generate_commissioni + db_backup_daily")


async def weekly_fatture_email(db) -> dict:
    """Every Sunday: email each terapeuta with all fatture (sanitarie + commissioni)
    generated in the past 7 days, attaching PDF+XML of each fattura."""
    from datetime import timedelta
    import base64
    from email_service import send_weekly_fatture_email
    from object_storage import get_object

    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)
    week_from = week_ago.strftime("%d/%m/%Y")
    week_to = now.strftime("%d/%m/%Y")

    # Group all fatture (sanitaria + commissione) by terapeuta_user_id
    by_terapeuta: dict = {}
    async for f in db.fatture.find({"created_at": {"$gte": week_ago}}):
        tid = f.get("terapeuta_user_id")
        if not tid:
            continue
        by_terapeuta.setdefault(tid, []).append(f)

    sent = 0
    for tid, items in by_terapeuta.items():
        user = await db.users.find_one({"_id": ObjectId(tid)})
        if not user or not user.get("email"):
            continue

        # Split by kind for the email template
        sanitarie = [f for f in items if f.get("kind") == "sanitaria"]
        commissioni = [f for f in items if f.get("kind") == "commissione"]

        # Build attachments: PDF + XML for each fattura (from Object Storage or inline b64 fallback)
        attachments: list = []
        for f in items:
            numero = f.get("numero", "fattura")
            # PDF
            pdf_b64 = None
            if f.get("pdf_storage_path"):
                try:
                    data, _ = get_object(f["pdf_storage_path"])
                    pdf_b64 = base64.b64encode(data).decode("ascii")
                except Exception as e:
                    logger.warning(f"[WEEKLY FATTURE] PDF fetch failed for {numero}: {e}")
            if not pdf_b64:
                pdf_b64 = f.get("pdf_inline_b64")
            if pdf_b64:
                attachments.append({"filename": f"{numero}.pdf", "content": pdf_b64})
            # XML
            xml_b64 = None
            if f.get("xml_storage_path"):
                try:
                    data, _ = get_object(f["xml_storage_path"])
                    xml_b64 = base64.b64encode(data).decode("ascii")
                except Exception as e:
                    logger.warning(f"[WEEKLY FATTURE] XML fetch failed for {numero}: {e}")
            if not xml_b64:
                xml_b64 = f.get("xml_inline_b64")
            if xml_b64:
                attachments.append({"filename": f"{numero}.xml", "content": xml_b64})

        try:
            ok = await send_weekly_fatture_email(
                email=user["email"],
                nome=user.get("nome", "Terapeuta"),
                fatture_sanitarie=sanitarie,
                fatture_commissioni=commissioni,
                attachments=attachments,
                week_from=week_from,
                week_to=week_to,
            )
            if ok:
                sent += 1
        except Exception as e:
            logger.error(f"[WEEKLY FATTURE] email fail terapeuta {tid}: {e}")

    logger.info(f"[WEEKLY FATTURE] sent to {sent} terapeuti (out of {len(by_terapeuta)} with activity)")
    return {"sent": sent, "candidates": len(by_terapeuta), "ran_at": now.isoformat()}


async def monthly_generate_commissioni(db) -> dict:
    """First day of month: generate B2B commission invoices for the previous month."""
    from routers.fatture import _generate_fatture_commissione_mensile
    now = datetime.now(timezone.utc)
    year = now.year
    month = now.month - 1
    if month == 0:
        month = 12
        year -= 1
    try:
        generated = await _generate_fatture_commissione_mensile(year, month)
    except Exception as e:
        logger.exception(f"[MONTHLY COMMISSIONE] failed: {e}")
        return {"error": str(e), "ran_at": now.isoformat()}
    logger.info(f"[MONTHLY COMMISSIONE] generated {len(generated)} fatture for {month}/{year}")
    return {"generated": len(generated), "year": year, "month": month, "ran_at": now.isoformat()}
