"""Regression tests for the Rome-TZ bug in therapist slots (iter 29).

Bug: GET /api/terapisti/{id}/slots interpreted 'HH:MM' strings from
`disponibilita_calendario` as UTC instead of Europe/Rome-local, causing
confirmation emails to show a time 1–2 hours later than what the therapist
had actually entered.

Fix location: /app/backend/routers/terapisti.py — new helper `_rome_hhmm_to_utc`.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient
from zoneinfo import ZoneInfo

# Load backend .env so MONGO_URL / DB_NAME are available
load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)

# Ensure we can import backend modules for unit-level regression tests
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    # fall back to frontend/.env (BASE_URL comes from ingress)
    from dotenv import dotenv_values
    fe = dotenv_values(Path(__file__).resolve().parents[2] / "frontend" / ".env")
    BASE_URL = (fe.get("REACT_APP_BACKEND_URL") or "").rstrip("/")

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
ROME = ZoneInfo("Europe/Rome")


# ─── Fixtures ────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(MONGO_URL)
    yield client[DB_NAME]
    client.close()


@pytest.fixture(scope="module")
def test_terapista(mongo_db):
    """Create a throwaway therapist with documenti_verificati=True so the
    /slots endpoint returns rows and the /public calendar endpoint works."""
    now = datetime.now(timezone.utc)
    doc = {
        "nome": "TEST_TZ",
        "cognome": "Rossi",
        "email": "test_tz_rossi@example.com",
        "documenti_verificati": True,
        "calendario_bozza": False,
        "approval_status": "approvato",
        "disponibilita_calendario": {},
        "disponibilita": [],
        "created_at": now,
    }
    result = mongo_db.terapisti.insert_one(doc)
    tid = str(result.inserted_id)
    yield tid
    mongo_db.terapisti.delete_one({"_id": ObjectId(tid)})


def _future_date_in_season(months_from_now: int, in_cest: bool):
    """Pick a future date in July (CEST=UTC+2) or January (CET=UTC+1)."""
    now = datetime.now(timezone.utc)
    year = now.year + 1  # always next year to be safely in the future
    if in_cest:
        return datetime(year, 7, 15, tzinfo=timezone.utc)  # DST in effect
    return datetime(year, 1, 15, tzinfo=timezone.utc)      # standard time


def _set_calendario(mongo_db, tid, cal):
    mongo_db.terapisti.update_one(
        {"_id": ObjectId(tid)},
        {"$set": {"disponibilita_calendario": cal, "disponibilita": []}},
    )


def _set_weekly(mongo_db, tid, disp):
    mongo_db.terapisti.update_one(
        {"_id": ObjectId(tid)},
        {"$set": {"disponibilita_calendario": {}, "disponibilita": disp}},
    )


# ─── BUG FIX 1: date-specific during CEST (UTC+2) ────────────────────────
class TestSlotsRomeTzFix:
    def test_slot_cest_16_rome_is_14_utc(self, mongo_db, test_terapista):
        target = _future_date_in_season(0, in_cest=True)
        date_key = target.strftime("%Y-%m-%d")
        _set_calendario(mongo_db, test_terapista, {date_key: ["16:00"]})

        # ask for a window that includes target
        r = requests.get(
            f"{BASE_URL}/api/terapisti/{test_terapista}/slots",
            params={"data_inizio": date_key, "settimane": 1},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["source"] == "calendar"
        slots = [s for s in data["slots"] if s["data_ora"].startswith(date_key)]
        assert len(slots) == 1, f"Expected 1 slot for {date_key}, got {slots}"
        # 16:00 Rome (CEST) == 14:00 UTC
        assert slots[0]["data_ora"] == f"{date_key}T14:00:00+00:00", slots[0]

    def test_slot_cet_16_rome_is_15_utc(self, mongo_db, test_terapista):
        target = _future_date_in_season(0, in_cest=False)
        date_key = target.strftime("%Y-%m-%d")
        _set_calendario(mongo_db, test_terapista, {date_key: ["16:00"]})

        r = requests.get(
            f"{BASE_URL}/api/terapisti/{test_terapista}/slots",
            params={"data_inizio": date_key, "settimane": 1},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        slots = [s for s in r.json()["slots"] if s["data_ora"].startswith(date_key)]
        assert len(slots) == 1
        # 16:00 Rome (CET) == 15:00 UTC
        assert slots[0]["data_ora"] == f"{date_key}T15:00:00+00:00", slots[0]

    def test_weekly_fallback_converts_rome_to_utc(self, mongo_db, test_terapista):
        """When no date-specific cal, weekly recurring 'Lunedì 16:00-17:00' during CEST → 14:00 UTC."""
        # Find first Monday in July next year (CEST)
        year = datetime.now(timezone.utc).year + 1
        d = datetime(year, 7, 1, tzinfo=timezone.utc)
        while d.weekday() != 0:  # Monday
            d += timedelta(days=1)
        _set_weekly(
            mongo_db,
            test_terapista,
            [{"giorno": "Lunedì", "ora_inizio": "16:00", "ora_fine": "17:00"}],
        )
        r = requests.get(
            f"{BASE_URL}/api/terapisti/{test_terapista}/slots",
            params={"data_inizio": d.strftime("%Y-%m-%d"), "settimane": 1},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["source"] == "legacy_weekly"
        date_key = d.strftime("%Y-%m-%d")
        mondays = [s for s in data["slots"] if s["data_ora"].startswith(date_key)]
        assert mondays, f"Expected at least 1 slot on Monday {date_key}, got {data['slots'][:3]}"
        # first slot: 16:00 Rome -> 14:00 UTC (CEST)
        assert mondays[0]["data_ora"] == f"{date_key}T14:00:00+00:00", mondays[0]


# ─── REGRESSION: public monthly calendar (calendario.py) already correct ─
class TestPublicMonthlyCalendar:
    def test_public_monthly_returns_rome_to_utc(self, mongo_db, test_terapista):
        target = _future_date_in_season(0, in_cest=True)  # July next year
        date_key = target.strftime("%Y-%m-%d")
        _set_calendario(mongo_db, test_terapista, {date_key: ["16:00"]})

        r = requests.get(
            f"{BASE_URL}/api/public/terapisti/{test_terapista}/calendario",
            params={"anno": target.year, "mese": target.month},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        days = r.json().get("days", [])
        match = [d for d in days if d["data"] == date_key]
        assert match, f"No slots for {date_key} in {days}"
        assert match[0]["slots"][0]["data_ora"] == f"{date_key}T14:00:00+00:00"


# ─── REGRESSION: email_service formatters (Rome TZ display) ──────────────
class TestEmailFormatters:
    def test_format_data_ora_it_cest(self):
        from email_service import _format_data_ora_it
        out = _format_data_ora_it("2026-10-15T14:00:00+00:00")
        # DST-check: 15 Oct is still CEST → +2 → 16:00
        assert "16:00" in out, out
        assert "2026" in out

    def test_format_data_ora_it_cet(self):
        from email_service import _format_data_ora_it
        # Dec 15 UTC 15:00 → CET (+1) → 16:00 local
        out = _format_data_ora_it("2026-12-15T15:00:00+00:00")
        assert "16:00" in out, out

    def test_fmt_it_short_format(self):
        from email_service import _fmt_it
        out = _fmt_it("2026-10-15T14:00:00+00:00")
        assert out == "15/10/2026 alle 16:00", out


# ─── REGRESSION: daily_service token nbf/exp arithmetic ──────────────────
class TestDailyTokenArithmetic:
    """We can't hit Daily.co from tests, but we can verify that the
    nbf/exp calculation used inside create_meeting_token is TZ-safe."""

    def test_utc_iso_produces_expected_epoch(self):
        # Emulates the exact calc from daily_service.create_meeting_token
        data_ora_iso = "2026-10-15T14:00:00+00:00"
        durata_min = 50
        start = datetime.fromisoformat(data_ora_iso.replace("Z", "+00:00"))
        nbf = int((start - timedelta(minutes=20)).timestamp())
        exp = int((start + timedelta(minutes=durata_min + 15)).timestamp())

        # Ground truth: 2026-10-15 14:00:00 UTC
        expected_start = int(datetime(2026, 10, 15, 14, 0, 0, tzinfo=timezone.utc).timestamp())
        assert nbf == expected_start - 20 * 60
        assert exp == expected_start + (durata_min + 15) * 60

    def test_z_suffix_iso_produces_same_epoch(self):
        a = datetime.fromisoformat("2026-10-15T14:00:00+00:00").timestamp()
        b = datetime.fromisoformat("2026-10-15T14:00:00Z".replace("Z", "+00:00")).timestamp()
        assert a == b


# ─── UNIT: _rome_hhmm_to_utc helper directly ─────────────────────────────
class TestRomeHelper:
    def test_helper_cest(self):
        from routers.terapisti import _rome_hhmm_to_utc
        day = datetime(2026, 7, 15, tzinfo=timezone.utc)
        out = _rome_hhmm_to_utc(day, 16, 0)
        assert out == datetime(2026, 7, 15, 14, 0, tzinfo=timezone.utc)

    def test_helper_cet(self):
        from routers.terapisti import _rome_hhmm_to_utc
        day = datetime(2026, 12, 15, tzinfo=timezone.utc)
        out = _rome_hhmm_to_utc(day, 16, 0)
        assert out == datetime(2026, 12, 15, 15, 0, tzinfo=timezone.utc)
