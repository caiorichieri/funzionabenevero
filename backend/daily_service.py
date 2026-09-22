"""Daily.co service — video call room creation + meeting tokens + attendance logs."""
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

DAILY_API_KEY = os.environ.get("DAILY_API_KEY", "")
DAILY_DOMAIN = os.environ.get("DAILY_DOMAIN", "")
DAILY_API_URL = "https://api.daily.co/v1"

_enabled = DAILY_API_KEY and DAILY_API_KEY != "placeholder_daily_key"


def _headers():
    return {
        "Authorization": f"Bearer {DAILY_API_KEY}",
        "Content-Type": "application/json",
    }


def _is_enabled() -> bool:
    return _enabled


async def create_room_for_appointment(appuntamento_id: str, data_ora_iso: str, durata_min: int = 50) -> Optional[dict]:
    """Create a Daily.co private room for an appointment.
    Room is available 15 min before scheduled time and expires 15 min after session ends.
    Returns {room_url, room_name, expires_at} or None on failure / disabled."""
    if not _is_enabled():
        logger.info(f"[DAILY] disabled — mock room for appuntamento {appuntamento_id}")
        return {
            "room_url": f"https://{DAILY_DOMAIN or 'mock'}.daily.co/appuntamento-{appuntamento_id}",
            "room_name": f"appuntamento-{appuntamento_id}",
            "mock": True,
        }

    try:
        start = datetime.fromisoformat(data_ora_iso.replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
    except Exception as e:
        logger.error(f"[DAILY] invalid data_ora: {data_ora_iso} ({e})")
        return None

    nbf = int((start - timedelta(minutes=20)).timestamp())
    exp = int((start + timedelta(minutes=durata_min + 15)).timestamp())

    payload = {
        "name": f"appuntamento-{appuntamento_id}",
        "privacy": "private",
        "properties": {
            "nbf": nbf,
            "exp": exp,
            "eject_at_room_exp": True,
            "max_participants": 3,
            "enable_screenshare": True,
            "enable_chat": True,
            "enable_knocking": False,
            "lang": "it",
        },
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{DAILY_API_URL}/rooms", headers=_headers(), json=payload)
        if r.status_code == 200:
            d = r.json()
            logger.info(f"[DAILY] room created: {d.get('name')} ({d.get('url')})")
            return {"room_url": d.get("url"), "room_name": d.get("name"), "expires_at": exp}
        # 409 = already exists → fetch it
        if r.status_code == 409 or (r.status_code == 400 and "already exists" in r.text.lower()):
            async with httpx.AsyncClient(timeout=15.0) as client:
                g = await client.get(f"{DAILY_API_URL}/rooms/{payload['name']}", headers=_headers())
            if g.status_code == 200:
                d = g.json()
                return {"room_url": d.get("url"), "room_name": d.get("name"), "expires_at": exp}
        logger.error(f"[DAILY] create room failed {r.status_code}: {r.text}")
        return None
    except Exception as e:
        logger.error(f"[DAILY] create room exception: {e}")
        return None


async def create_meeting_token(room_name: str, user_name: str, is_owner: bool, data_ora_iso: str, durata_min: int = 50) -> Optional[str]:
    """Create a meeting token for a participant. Token limits access to the specific room and time window."""
    if not _is_enabled():
        return None

    try:
        start = datetime.fromisoformat(data_ora_iso.replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
    except Exception:
        return None

    nbf = int((start - timedelta(minutes=20)).timestamp())
    exp = int((start + timedelta(minutes=durata_min + 15)).timestamp())

    payload = {
        "properties": {
            "room_name": room_name,
            "user_name": user_name,
            "is_owner": is_owner,
            "nbf": nbf,
            "exp": exp,
            "enable_screenshare": True,
            "start_video_off": False,
            "start_audio_off": False,
            "lang": "it",
        }
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(f"{DAILY_API_URL}/meeting-tokens", headers=_headers(), json=payload)
        if r.status_code == 200:
            return r.json().get("token")
        logger.error(f"[DAILY] token creation failed {r.status_code}: {r.text}")
        return None
    except Exception as e:
        logger.error(f"[DAILY] token exception: {e}")
        return None


async def get_room_presenza(room_name: str) -> list:
    """Get room participant logs (attendance). Returns list of {user_name, join_time, duration}."""
    if not _is_enabled():
        return []
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.get(f"{DAILY_API_URL}/meetings", headers=_headers(), params={"room": room_name, "limit": 20})
        if r.status_code != 200:
            logger.error(f"[DAILY] meetings fetch failed {r.status_code}: {r.text}")
            return []
        data = r.json().get("data", [])
        results = []
        for m in data:
            for p in m.get("participants", []):
                results.append({
                    "user_name": p.get("user_name", "—"),
                    "join_time": p.get("join_time"),
                    "duration_seconds": p.get("duration"),
                })
        return results
    except Exception as e:
        logger.error(f"[DAILY] meetings exception: {e}")
        return []
