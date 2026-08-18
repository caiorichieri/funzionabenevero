"""Twilio Verify — SMS OTP service.
Replaces the Skebby implementation. Twilio Verify handles code generation,
storage, expiration and rate-limiting server-side — no local code storage
needed on our side.
"""
import os
import logging
import asyncio
import re
from typing import Optional
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
VERIFY_SERVICE_SID = os.environ.get("TWILIO_VERIFY_SERVICE_SID", "")
# For outbound transactional SMS (reminders): either a Twilio phone number OR a Messaging Service SID
FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")
MESSAGING_SERVICE_SID = os.environ.get("TWILIO_MESSAGING_SERVICE_SID", "")

_client = None
if ACCOUNT_SID and AUTH_TOKEN:
    try:
        from twilio.rest import Client as _TwilioClient
        _client = _TwilioClient(ACCOUNT_SID, AUTH_TOKEN)
    except Exception as e:
        logger.error(f"[SMS] Failed to initialize Twilio client: {e}")


def _normalize_phone(phone: str) -> str:
    """Return an E.164-formatted number. Defaults to +39 (Italy) if no country code."""
    if not phone:
        return ""
    p = re.sub(r"[\s\-()]", "", phone.strip())
    if p.startswith("+"):
        return p
    if p.startswith("00"):
        return "+" + p[2:]
    if p.startswith("39") and len(p) >= 12:
        return "+" + p
    return "+39" + p.lstrip("0")


async def send_sms_otp(phone: str, otp_code: str = "", context: str = "verifica") -> bool:
    """Trigger Twilio Verify to send an SMS with a code to the given phone.
    The `otp_code` argument is kept for backwards-compat with the old Skebby
    signature but IS IGNORED — Twilio Verify generates its own code.
    Returns True on success."""
    if not (_client and VERIFY_SERVICE_SID):
        logger.warning("[SMS] Twilio not configured, skipping OTP send")
        return False
    to = _normalize_phone(phone)
    if not to:
        return False
    try:
        v = await asyncio.to_thread(
            lambda: _client.verify.v2.services(VERIFY_SERVICE_SID).verifications.create(
                to=to, channel="sms", locale="it",
            )
        )
        logger.info(f"[SMS] Verify created for {to[:-4]}**** (status={v.status}, ctx={context})")
        return v.status in ("pending", "sent")
    except Exception as e:
        logger.error(f"[SMS] Twilio Verify send failed: {e}")
        return False


async def verify_sms_otp(phone: str, code: str) -> bool:
    """Check the user-supplied code against Twilio Verify. Returns True if approved."""
    if not (_client and VERIFY_SERVICE_SID):
        logger.warning("[SMS] Twilio not configured")
        return False
    to = _normalize_phone(phone)
    if not to or not code:
        return False
    try:
        check = await asyncio.to_thread(
            lambda: _client.verify.v2.services(VERIFY_SERVICE_SID).verification_checks.create(
                to=to, code=code.strip(),
            )
        )
        logger.info(f"[SMS] Verify check for {to[:-4]}**** → {check.status}")
        return check.status == "approved"
    except Exception as e:
        logger.error(f"[SMS] Twilio Verify check failed: {e}")
        return False


async def send_sms_reminder(phone: str, body: str) -> bool:
    """Send a transactional SMS reminder (session-related messages).
    Requires either TWILIO_FROM_NUMBER or TWILIO_MESSAGING_SERVICE_SID.
    Returns True on success, False if not configured or send fails."""
    if not _client:
        logger.warning("[SMS] Twilio not configured, skipping reminder")
        return False
    if not (FROM_NUMBER or MESSAGING_SERVICE_SID):
        logger.warning("[SMS] No TWILIO_FROM_NUMBER or TWILIO_MESSAGING_SERVICE_SID set, skipping reminder")
        return False
    to = _normalize_phone(phone)
    if not to or not body:
        return False
    try:
        kwargs = {"to": to, "body": body}
        if MESSAGING_SERVICE_SID:
            kwargs["messaging_service_sid"] = MESSAGING_SERVICE_SID
        else:
            kwargs["from_"] = FROM_NUMBER
        msg = await asyncio.to_thread(lambda: _client.messages.create(**kwargs))
        logger.info(f"[SMS] Reminder sent to {to[:-4]}**** (sid={msg.sid}, status={msg.status})")
        return True
    except Exception as e:
        logger.error(f"[SMS] Reminder send failed: {e}")
        return False
