"""Resend webhook receiver.

Resend posts email lifecycle events to us (delivered, opened, clicked,
bounced, complained). We append each event to the matching row in
`email_events` (keyed by `resend_id`) so the admin can see the full
audit trail per template / appuntamento.

Signature is verified via Svix (Resend uses Svix under the hood). The
signing secret comes from `RESEND_WEBHOOK_SECRET` in .env. If the secret
is not configured, we accept the payload but tag the event as unverified —
this lets developers set up the endpoint before wiring the console secret.
"""
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from deps import db

router = APIRouter()
logger = logging.getLogger(__name__)

RESEND_WEBHOOK_SECRET = os.environ.get("RESEND_WEBHOOK_SECRET", "")


def _verify_svix_signature(headers: dict, raw_body: bytes) -> bool:
    """Return True if the Svix signature on the request matches our secret.
    Returns False if the secret is not configured (dev mode)."""
    if not RESEND_WEBHOOK_SECRET:
        return False
    try:
        from svix.webhooks import Webhook  # local import so unit tests can skip
        wh = Webhook(RESEND_WEBHOOK_SECRET)
        wh.verify(
            raw_body,
            {
                "svix-id": headers.get("svix-id", ""),
                "svix-timestamp": headers.get("svix-timestamp", ""),
                "svix-signature": headers.get("svix-signature", ""),
            },
        )
        return True
    except Exception as e:
        logger.warning(f"[RESEND WEBHOOK] signature verify failed: {e}")
        return False


@router.post("/webhooks/resend")
async def resend_webhook(request: Request):
    """Ingest a single Resend email event and append it to the matching row."""
    raw = await request.body()
    verified = _verify_svix_signature({k.lower(): v for k, v in request.headers.items()}, raw)

    # If a secret is configured, we REQUIRE a valid signature; otherwise a public
    # endpoint could be spammed. If no secret, accept for local dev but tag it.
    if RESEND_WEBHOOK_SECRET and not verified:
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json")

    event_type = str(payload.get("type", "")).lower()  # e.g. "email.delivered"
    data = payload.get("data") or {}
    resend_id = data.get("email_id") or data.get("id")
    if not resend_id:
        # Nothing to correlate — accept and drop
        logger.info(f"[RESEND WEBHOOK] {event_type} with no email_id — skipping")
        return {"ok": True, "skipped": True}

    kind = event_type.replace("email.", "") or "unknown"
    event_doc = {
        "kind": kind,
        "at": datetime.now(timezone.utc),
        "verified": verified,
    }
    # Enrich with the small subset of resend fields useful in the admin UI
    if "click" in data and isinstance(data["click"], dict):
        event_doc["url"] = data["click"].get("link")
    if "bounce" in data and isinstance(data["bounce"], dict):
        event_doc["bounce_type"] = data["bounce"].get("type")
    if "user_agent" in data:
        event_doc["user_agent"] = data.get("user_agent")

    # Roll-up latest status onto the parent doc so the admin listing can sort
    # by "last activity" without needing to unwind the events array.
    update = {
        "$push": {"events": event_doc},
        "$set": {"status": kind, "last_event_at": event_doc["at"]},
    }
    result = await db.email_events.update_one({"resend_id": resend_id}, update)
    if result.matched_count == 0:
        # We received an event for an email we never persisted (e.g., sent via
        # `_send_raw` directly). Store a stub so the trail isn't lost.
        await db.email_events.insert_one({
            "resend_id": resend_id,
            "template": "unknown",
            "recipient": data.get("to") if isinstance(data.get("to"), str) else (data.get("to") or [None])[0],
            "subject": data.get("subject"),
            "status": kind,
            "last_event_at": event_doc["at"],
            "sent_at": event_doc["at"],
            "events": [event_doc],
            "orphan": True,
        })
    logger.info(f"[RESEND WEBHOOK] {kind} for resend_id={resend_id} (matched={result.matched_count})")
    return {"ok": True, "kind": kind}
