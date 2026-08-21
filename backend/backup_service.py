"""Automated MongoDB backup to Backblaze B2 (or any S3-compatible bucket).

Runs nightly at 03:00 UTC via APScheduler.
Retention: 30 daily backups + 12 monthly (1st of each month kept).

Required env vars (all optional — if any missing, backup is skipped with a warning):
    B2_KEY_ID           — Backblaze application key ID
    B2_APP_KEY          — Backblaze application key
    B2_BUCKET_NAME      — target bucket (e.g. 'funzionabene-backups')
    B2_ENDPOINT         — S3 endpoint (default: https://s3.eu-central-003.backblazeb2.com)

To bootstrap:
1. Sign up on https://www.backblaze.com/b2/cloud-storage.html (free tier: 10GB storage)
2. Create a private bucket 'funzionabene-backups'
3. Create an Application Key with read+write access to that bucket
4. Add the 4 env vars in Emergent Segreti → redeploy

To restore:
    mongorestore --uri="$MONGO_URL" --nsInclude="funzionabene_db.*" --gzip --archive=<backup_file>
"""
import gzip
import logging
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _cfg():
    return {
        "key_id": os.environ.get("B2_KEY_ID"),
        "app_key": os.environ.get("B2_APP_KEY"),
        "bucket": os.environ.get("B2_BUCKET_NAME"),
        "endpoint": os.environ.get("B2_ENDPOINT", "https://s3.eu-central-003.backblazeb2.com"),
        "mongo_url": os.environ.get("MONGO_URL"),
        "db_name": os.environ.get("DB_NAME", "funzionabene_db"),
    }


def _is_configured() -> bool:
    c = _cfg()
    return bool(c["key_id"] and c["app_key"] and c["bucket"] and c["mongo_url"])


async def run_backup() -> bool:
    """Dump MongoDB → gzip → upload to B2. Returns True on success."""
    if not _is_configured():
        logger.warning("[BACKUP] B2 credentials not set — skipping backup")
        return False

    c = _cfg()
    now = datetime.now(timezone.utc)
    fname = f"backup-{c['db_name']}-{now.strftime('%Y-%m-%d')}.archive.gz"

    with tempfile.TemporaryDirectory() as tmp:
        archive_path = os.path.join(tmp, fname)
        try:
            # 1) mongodump into a single archive, gzipped
            result = subprocess.run(
                [
                    "mongodump",
                    "--uri", c["mongo_url"],
                    "--db", c["db_name"],
                    "--archive=" + archive_path,
                    "--gzip",
                ],
                capture_output=True, text=True, timeout=600,
            )
            if result.returncode != 0:
                logger.error(f"[BACKUP] mongodump failed: {result.stderr}")
                return False
            size_mb = os.path.getsize(archive_path) / 1024 / 1024
            logger.info(f"[BACKUP] Dump created: {fname} ({size_mb:.1f} MB)")

            # 2) Upload to B2 via boto3 (S3-compatible)
            import boto3  # lazy import
            s3 = boto3.client(
                "s3",
                endpoint_url=c["endpoint"],
                aws_access_key_id=c["key_id"],
                aws_secret_access_key=c["app_key"],
            )
            key = f"daily/{fname}"
            s3.upload_file(archive_path, c["bucket"], key)
            logger.info(f"[BACKUP] Uploaded to s3://{c['bucket']}/{key}")

            # 3) Also archive as monthly if day == 1
            if now.day == 1:
                monthly_key = f"monthly/{fname}"
                s3.copy_object(
                    Bucket=c["bucket"],
                    CopySource={"Bucket": c["bucket"], "Key": key},
                    Key=monthly_key,
                )
                logger.info(f"[BACKUP] Monthly snapshot: s3://{c['bucket']}/{monthly_key}")

            return True
        except Exception as e:
            logger.error(f"[BACKUP] Unexpected error: {e}")
            return False


async def cleanup_old_backups() -> int:
    """Remove daily backups > 30 days, and monthly > 365 days. Returns count deleted."""
    if not _is_configured():
        return 0
    c = _cfg()
    try:
        import boto3
        from datetime import timedelta
        s3 = boto3.client(
            "s3",
            endpoint_url=c["endpoint"],
            aws_access_key_id=c["key_id"],
            aws_secret_access_key=c["app_key"],
        )
        now = datetime.now(timezone.utc)
        daily_cutoff = now - timedelta(days=30)
        monthly_cutoff = now - timedelta(days=365)
        deleted = 0
        for prefix, cutoff in [("daily/", daily_cutoff), ("monthly/", monthly_cutoff)]:
            paginator = s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=c["bucket"], Prefix=prefix):
                for obj in page.get("Contents", []):
                    if obj["LastModified"].replace(tzinfo=timezone.utc) < cutoff:
                        s3.delete_object(Bucket=c["bucket"], Key=obj["Key"])
                        deleted += 1
        if deleted:
            logger.info(f"[BACKUP] Cleaned up {deleted} old backups")
        return deleted
    except Exception as e:
        logger.error(f"[BACKUP] cleanup failed: {e}")
        return 0
