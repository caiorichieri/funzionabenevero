"""S3 Object Storage helper — used to archive legally-binding PDF receipts and
signed contracts (fatture, legal signatures).

Storage client is a boto3 S3 client pointed at Host.it Object Storage
(S3-compatible), cached in-memory for the process lifetime. Paths follow the
convention: funzionabene/<subfolder>/<filename>.
"""
import os
import logging
from typing import Tuple

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

S3_ACCESS_KEY = os.environ.get("S3_ACCESS_KEY")
S3_SECRET_KEY = os.environ.get("S3_SECRET_KEY")
S3_ENDPOINT = os.environ.get("S3_ENDPOINT")
S3_REGION = os.environ.get("S3_REGION", "eu-it-trn-1")
S3_DOCS_BUCKET = os.environ.get("S3_DOCS_BUCKET", "funzionabene-docs")

_s3_client = None


def _get_client():
    """Return a cached boto3 S3 client. Raises if S3 credentials are missing."""
    global _s3_client
    if _s3_client is not None:
        return _s3_client
    if not (S3_ACCESS_KEY and S3_SECRET_KEY and S3_ENDPOINT):
        raise RuntimeError(
            "S3_ACCESS_KEY, S3_SECRET_KEY and S3_ENDPOINT must be configured in backend/.env"
        )
    _s3_client = boto3.client(
        "s3",
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        endpoint_url=S3_ENDPOINT,
        region_name=S3_REGION,
        config=Config(signature_version="s3v4"),
    )
    logging.info("[OBJSTORE] S3 client initialized (bucket=%s)", S3_DOCS_BUCKET)
    return _s3_client


def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Upload bytes to S3. Returns {"path": <canonical>, "size": int}."""
    client = _get_client()
    client.put_object(
        Bucket=S3_DOCS_BUCKET,
        Key=path,
        Body=data,
        ContentType=content_type,
    )
    logging.info("[OBJSTORE] put_object path=%s size=%d", path, len(data))
    return {"path": path, "size": len(data)}


def get_object(path: str) -> Tuple[bytes, str]:
    """Download bytes for path. Returns (content, content_type)."""
    client = _get_client()
    try:
        resp = client.get_object(Bucket=S3_DOCS_BUCKET, Key=path)
    except ClientError:
        logging.exception("[OBJSTORE] get_object failed path=%s", path)
        raise
    content = resp["Body"].read()
    content_type = resp.get("ContentType", "application/pdf")
    logging.info("[OBJSTORE] get_object path=%s size=%d", path, len(content))
    return content, content_type
