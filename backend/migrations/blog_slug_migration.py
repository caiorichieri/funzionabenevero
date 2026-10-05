"""Blog slug migration — one-shot, idempotent startup task.

Purpose
-------
Add a kebab-case `slug` field to the production `articoli` collection using a
fixed, user-approved mapping of production ObjectIds → slug. The mapping was
generated once from the live production titles with the agreed slugify
algorithm (NFKD + kebab-case + apostrophe→'-' + max 70 chars) and MUST remain
immutable; new articles are slugified on write by the router, not here.

Guarantees
----------
1. Runs at FastAPI startup, before serving traffic.
2. Idempotent: subsequent runs no-op when all mapped articles already have a slug.
3. Creates a timestamped backup collection BEFORE any write. If the backup
   row-count does not match the live `articoli` count → ABORT, no mutation.
4. Writes ONLY the `slug` field, and ONLY on articles whose `_id` is in the
   mapping AND which do NOT already have a slug. Never overwrites an existing
   slug, never touches any other field, never deletes.
5. If the backup fails for any reason, logs ERROR but allows the server to
   boot normally (requested behaviour: uptime > data migration).
6. Creates a unique sparse index on `slug` (idempotent).

Mapping
-------
15 live production articles (fetched 2026-02-21 from https://funzionabene.it/api/public/blog)
mapped to slugs with the same algorithm applied to preview DB. No duplicates.
"""
import logging
from datetime import datetime, timezone

from pymongo import ASCENDING

logger = logging.getLogger("blog_slug_migration")

# ---------------------------------------------------------------------------
# Immutable production slug mapping — approved by product owner on 2026-02-21.
# Any new article must be slugified at write-time by the router (see routers/blog.py).
# ---------------------------------------------------------------------------
PROD_SLUG_MAPPING = {
    "6a954241e36c582b9cacb144": "il-desiderio-sessuale-cos-e-come-cambia-e-quando-ascoltarlo",
    "6a954241e36c582b9cacb145": "eiaculazione-precoce-oltre-il-tabu-verso-la-cura",
    "6a954241e36c582b9cacb146": "vaginismo-quando-il-corpo-chiede-protezione",
    "6a954241e36c582b9cacb147": "disfunzione-erettile-ritrovare-la-fiducia-nel-proprio-corpo",
    "6a954241e36c582b9cacb148": "l-orgasmo-femminile-un-viaggio-non-una-destinazione",
    "6a954241e36c582b9cacb149": "comunicazione-e-intimita-come-parlarsi-davvero",
    "6a954241e36c582b9cacb14a": "la-sessualita-nel-tempo-cambia-ma-non-finisce",
    "6a954241e36c582b9cacb14b": "orientamento-sessuale-e-identita-di-genere-un-percorso-di-scoperta",
    "6a954241e36c582b9cacb14c": "il-desiderio-dopo-il-parto-ritrovarsi-nel-corpo-che-cambia",
    "6a954241e36c582b9cacb14d": "pornografia-e-intimita-reale-quando-lo-schermo-prende-il-sopravvento",
    "6a954241e36c582b9cacb14e": "anorgasmia-quando-il-piacere-sembra-lontano",
    "6a954241e36c582b9cacb14f": "sessualita-e-malattia-cronica-il-corpo-cambia-il-piacere-puo-restare",
    "6a954241e36c582b9cacb150": "dispareunia-quando-fare-l-amore-fa-male",
    "6a954241e36c582b9cacb151": "immagine-corporea-e-sessualita-amarsi-per-amarsi",
    "6a954241e36c582b9cacb152": "la-terapia-sessuologica-cos-e-davvero-e-a-chi-si-rivolge",
}


async def run_blog_slug_migration(db) -> dict:
    """Execute the migration against the given motor DB.

    Returns a dict summary. Never raises — on any error logs and returns a
    report with `aborted=True`.
    """
    from bson import ObjectId  # local import to avoid top-level dep leakage

    report = {
        "aborted": False,
        "reason": None,
        "mapping_size": len(PROD_SLUG_MAPPING),
        "live_articoli_count": 0,
        "backup_collection": None,
        "backup_count": 0,
        "updated": 0,
        "already_had_slug": 0,
        "missing_from_db": 0,
        "backup_failed": False,
        "index_created": False,
    }

    # ─── Early exit: already migrated? ─────────────────────────────────────
    try:
        mapped_oids = []
        for id_hex in PROD_SLUG_MAPPING.keys():
            try:
                mapped_oids.append(ObjectId(id_hex))
            except Exception:
                logger.warning("[BLOG_SLUG] mapping contains invalid ObjectId '%s' — skipping", id_hex)
        if not mapped_oids:
            report["aborted"] = True
            report["reason"] = "mapping produced zero valid ObjectIds"
            logger.warning("[BLOG_SLUG] %s", report["reason"])
            return report

        needs_update = await db.articoli.count_documents(
            {"_id": {"$in": mapped_oids}, "slug": {"$exists": False}}
        )
        if needs_update == 0:
            logger.info("[BLOG_SLUG] already migrated — all mapped articles have a slug. Skipping.")
            # Still ensure the index exists on steady-state deployments.
            try:
                await db.articoli.create_index([("slug", ASCENDING)], unique=True, sparse=True)
                report["index_created"] = True
            except Exception as e:
                logger.warning("[BLOG_SLUG] index already exists or create skipped: %s", e)
            report["already_had_slug"] = await db.articoli.count_documents(
                {"_id": {"$in": mapped_oids}, "slug": {"$exists": True}}
            )
            return report

        # ─── Preflight count ──────────────────────────────────────────────
        live_count = await db.articoli.count_documents({})
        report["live_articoli_count"] = live_count

        # ─── Create backup collection ─────────────────────────────────────
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"articoli_backup_slug_migration_{stamp}"
        report["backup_collection"] = backup_name

        try:
            cursor = db.articoli.find({})
            all_articoli = await cursor.to_list(length=None)
            if all_articoli:
                await db[backup_name].insert_many(all_articoli)
            backup_count = await db[backup_name].count_documents({})
            report["backup_count"] = backup_count
        except Exception as e:
            report["backup_failed"] = True
            report["aborted"] = True
            report["reason"] = f"backup creation failed: {e}"
            logger.error("[BLOG_SLUG] %s — migration aborted, no mutation performed", report["reason"])
            return report  # Server continues (requested behaviour)

        # Backup must match live row count — otherwise abort.
        if backup_count != live_count:
            report["aborted"] = True
            report["reason"] = (
                f"backup row count ({backup_count}) does not match live articoli count ({live_count}) — abort"
            )
            logger.error("[BLOG_SLUG] %s", report["reason"])
            # Clean up incomplete backup to avoid noise next run.
            try:
                await db[backup_name].drop()
                logger.info("[BLOG_SLUG] incomplete backup collection %s dropped", backup_name)
            except Exception as e:
                logger.warning("[BLOG_SLUG] could not drop incomplete backup %s: %s", backup_name, e)
            return report

        logger.info("[BLOG_SLUG] backup OK: collection=%s rows=%d", backup_name, backup_count)

        # ─── Apply slug $set only where missing ───────────────────────────
        updated = 0
        already_had = 0
        missing = 0
        for id_hex, slug in PROD_SLUG_MAPPING.items():
            try:
                oid = ObjectId(id_hex)
            except Exception:
                continue
            # Count only matches where slug is missing.
            r = await db.articoli.update_one(
                {"_id": oid, "slug": {"$exists": False}},
                {"$set": {"slug": slug}},
            )
            if r.matched_count == 0:
                # Either article doesn't exist OR it already has a slug.
                existing = await db.articoli.find_one({"_id": oid}, {"slug": 1})
                if existing is None:
                    missing += 1
                else:
                    already_had += 1
            elif r.modified_count == 1:
                updated += 1

        report["updated"] = updated
        report["already_had_slug"] = already_had
        report["missing_from_db"] = missing

        # ─── Unique sparse index on slug ───────────────────────────────────
        try:
            await db.articoli.create_index([("slug", ASCENDING)], unique=True, sparse=True)
            report["index_created"] = True
        except Exception as e:
            logger.warning("[BLOG_SLUG] index creation skipped: %s", e)

        logger.info(
            "[BLOG_SLUG] migration complete: updated=%d already_had_slug=%d missing_from_db=%d index=%s backup=%s",
            updated, already_had, missing, report["index_created"], backup_name,
        )
        return report

    except Exception as e:
        report["aborted"] = True
        report["reason"] = f"unexpected error: {e}"
        logger.exception("[BLOG_SLUG] migration failed with unexpected error — server continues")
        return report
