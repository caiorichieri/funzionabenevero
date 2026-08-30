"""Emergent Object Storage wrapper.

Used to persist user-uploaded files (therapist verification documents, etc.)
outside the ephemeral pod disk so they survive deploys and restarts.

Playbook: https://integrations.emergentagent.com/objstore
"""
import logging
import os
from typing import Tuple

import requests

logger = logging.getLogger(__name__)

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = os.environ.get("STORAGE_APP_NAME", "funzionabene")

_storage_key: str | None = None


def init_storage() -> str:
    """Call once at startup. Returns a session-scoped storage_key that is reused globally."""
    global _storage_key
    if _storage_key:
        return _storage_key
    if not EMERGENT_KEY:
        raise RuntimeError("EMERGENT_LLM_KEY is not set")
    resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
    resp.raise_for_status()
    _storage_key = resp.json()["storage_key"]
    logger.info("[STORAGE] initialized (app=%s)", APP_NAME)
    return _storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict:
    """Upload bytes to Object Storage. Returns the storage response ({path, size, etag, ...})."""
    key = init_storage()
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data,
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def get_object(path: str) -> Tuple[bytes, str]:
    """Download bytes from Object Storage. Returns (content, content_type)."""
    key = init_storage()
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


# ─── Content-Type helper ─────────────────────────────────────────────────
_MIME_BY_EXT = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def mime_for_ext(ext: str) -> str:
    return _MIME_BY_EXT.get(ext.lower(), "application/octet-stream")
