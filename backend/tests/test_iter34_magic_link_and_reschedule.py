"""Iteration 34 backend tests.

BUG A — /api/videocall-magic/{id}?token=X gate:
  - accepts videocall_magic_expires as ISO string (previously 500'd via .tzinfo on str)
  - accepts videocall_magic_expires as native BSON datetime (no regression)
  - extended window: start+durata+15 (was start+15) → past-start-but-in-session opens
  - beyond window (start+durata+15) → 410 session_closed
  - before window (>20 min before) → 425 too_early
  - invalid token → 403
  - expires None → falls back to start+durata+15

BUG B — booking_service scheduler helpers:
  - schedule_reminders with ISO+offset registers 5 reminder + 3 no-show jobs
  - schedule_reminders with naive string is interpreted as Europe/Rome
  - idempotency: repeat call keeps single job per id (replace_existing=True)
  - cancel_scheduled_jobs removes all 8 jobs
  - reschedule_reminders cancels old_id jobs and registers fresh new_id jobs
"""
import asyncio
import hashlib
import os
import secrets as _secrets
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import requests
from bson import ObjectId

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    fe_env = Path(__file__).resolve().parent.parent.parent / "frontend" / ".env"
    for line in fe_env.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL"):
            BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
            break

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def db(event_loop):
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


def _digest(raw: str) -> str:
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


async def _seed_magic_appt(db, data_ora_iso, durata=50, expires_value="__auto_str__"):
    """Seed an appointment doc with videocall_magic_hash+expires.
    expires_value:
      "__auto_str__" → ISO string = data_ora + durata+15 min
      "__auto_dt__"  → aware datetime
      None           → omit the field entirely
      any datetime/str → used as-is
    """
    raw = _secrets.token_urlsafe(32)
    start = datetime.fromisoformat(data_ora_iso.replace("Z", "+00:00"))
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    close_at = start + timedelta(minutes=durata + 15)
    if expires_value == "__auto_str__":
        exp = close_at.isoformat()
    elif expires_value == "__auto_dt__":
        exp = close_at
    else:
        exp = expires_value

    # Also seed a paziente since gate/handler queries paziente after gate passes
    paz_uid = str(ObjectId())
    paziente = {"_id": ObjectId(), "user_id": paz_uid, "nome": "Test", "cognome": "Magic",
                "test_seed": True}
    await db.pazienti.insert_one(paziente)

    doc = {
        "terapeuta_id": str(ObjectId()),
        "paziente_id": str(paziente["_id"]),
        "paziente_user_id": paz_uid,
        "data_ora": data_ora_iso,
        "durata_minuti": durata,
        "stato": "confermato",
        "daily_room_name": f"appuntamento-TEST_{ObjectId()}",
        "daily_room_url": "https://mock.daily.co/test",
        "videocall_magic_hash": _digest(raw),
        "created_at": datetime.now(timezone.utc),
        "test_seed": True,
    }
    if expires_value is not None:
        doc["videocall_magic_expires"] = exp
    r = await db.appuntamenti.insert_one(doc)
    doc["_id"] = r.inserted_id
    return doc, raw


@pytest.fixture(scope="module", autouse=True)
def cleanup(event_loop, db):
    yield
    async def _t():
        await db.appuntamenti.delete_many({"test_seed": True})
        await db.pazienti.delete_many({"test_seed": True})
    event_loop.run_until_complete(_t())


# ─── BUG A: magic link gate ──────────────────────────────────────────────────
class TestMagicLinkGate:
    def test_expires_as_iso_string_returns_200(self, event_loop, db):
        # start = now + 5 min (inside window), expires stored AS STRING
        soon = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        appt, raw = event_loop.run_until_complete(_seed_magic_appt(db, soon, expires_value="__auto_str__"))
        # sanity: field is a str
        stored = event_loop.run_until_complete(db.appuntamenti.find_one({"_id": appt["_id"]}))
        assert isinstance(stored["videocall_magic_expires"], str), \
            f"expected str, got {type(stored['videocall_magic_expires'])}"
        r = requests.get(f"{BASE_URL}/api/videocall-magic/{appt['_id']}", params={"token": raw})
        assert r.status_code == 200, f"BUG A regression: got {r.status_code}: {r.text[:400]}"

    def test_expires_as_datetime_returns_200(self, event_loop, db):
        soon = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        appt, raw = event_loop.run_until_complete(_seed_magic_appt(db, soon, expires_value="__auto_dt__"))
        stored = event_loop.run_until_complete(db.appuntamenti.find_one({"_id": appt["_id"]}))
        assert isinstance(stored["videocall_magic_expires"], datetime)
        r = requests.get(f"{BASE_URL}/api/videocall-magic/{appt['_id']}", params={"token": raw})
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:400]}"

    def test_extended_window_start_minus_30_is_open(self, event_loop, db):
        # start = now - 30 min, durata 50 → close_at = start + 65 → 35 min in future
        past = (datetime.now(timezone.utc) - timedelta(minutes=30)).isoformat()
        # Force expires to None to test the FALLBACK (start + durata + 15)
        appt, raw = event_loop.run_until_complete(_seed_magic_appt(db, past, durata=50, expires_value=None))
        r = requests.get(f"{BASE_URL}/api/videocall-magic/{appt['_id']}", params={"token": raw})
        assert r.status_code == 200, \
            f"BUG A extended-window regression: expected 200 (close_at=+35min), got {r.status_code}: {r.text[:300]}"

    def test_beyond_window_returns_410(self, event_loop, db):
        # start = now - 90 min, durata 50 → close_at = -25 min (closed)
        past = (datetime.now(timezone.utc) - timedelta(minutes=90)).isoformat()
        appt, raw = event_loop.run_until_complete(_seed_magic_appt(db, past, durata=50, expires_value=None))
        r = requests.get(f"{BASE_URL}/api/videocall-magic/{appt['_id']}", params={"token": raw})
        assert r.status_code == 410, f"got {r.status_code}: {r.text[:300]}"
        assert r.json()["detail"]["code"] == "session_closed"

    def test_before_window_returns_425(self, event_loop, db):
        future = (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()
        appt, raw = event_loop.run_until_complete(_seed_magic_appt(db, future, expires_value=None))
        r = requests.get(f"{BASE_URL}/api/videocall-magic/{appt['_id']}", params={"token": raw})
        assert r.status_code == 425, f"got {r.status_code}: {r.text[:300]}"
        assert r.json()["detail"]["code"] == "too_early"

    def test_invalid_token_returns_403(self, event_loop, db):
        soon = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        appt, _raw = event_loop.run_until_complete(_seed_magic_appt(db, soon, expires_value=None))
        r = requests.get(f"{BASE_URL}/api/videocall-magic/{appt['_id']}", params={"token": "invalid"})
        assert r.status_code == 403

    def test_expires_none_uses_fallback_window(self, event_loop, db):
        # start = now + 5 min inside window, expires missing → should still open
        soon = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        appt, raw = event_loop.run_until_complete(_seed_magic_appt(db, soon, expires_value=None))
        stored = event_loop.run_until_complete(db.appuntamenti.find_one({"_id": appt["_id"]}))
        assert "videocall_magic_expires" not in stored
        r = requests.get(f"{BASE_URL}/api/videocall-magic/{appt['_id']}", params={"token": raw})
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:300]}"


# ─── BUG B: scheduler helpers ────────────────────────────────────────────────
class TestSchedulerHelpers:
    @pytest.fixture(autouse=True)
    def _start_scheduler(self, event_loop):
        import booking_service
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.jobstores.mongodb import MongoDBJobStore
        async def _s():
            sched = booking_service.scheduler
            # If the singleton scheduler was started on another (now closed)
            # loop by a previous test module, its jobstore MongoClient is dead
            # and its event_loop is stale. Rebuild a fresh scheduler bound to
            # the current module loop.
            need_rebuild = False
            try:
                if sched.running and sched._eventloop is not asyncio.get_event_loop():
                    need_rebuild = True
            except Exception:
                need_rebuild = True
            if need_rebuild:
                try:
                    sched.shutdown(wait=False)
                except Exception:
                    pass
                mongo_url = os.environ["MONGO_URL"]
                dbname = os.environ["DB_NAME"]
                booking_service.scheduler = AsyncIOScheduler(
                    jobstores={"default": MongoDBJobStore(
                        database=dbname, collection="apscheduler_jobs", host=mongo_url)},
                    timezone="UTC",
                )
            if not booking_service.scheduler.running:
                booking_service.scheduler.start()
        event_loop.run_until_complete(_s())
        yield

    def _make_ctx(self, data_ora, durata=50):
        return {
            "data_ora": data_ora,
            "durata_minuti": durata,
            "paziente_email": "p@x.it",
            "paziente_nome": "Luca",
            "terapista_cognome": "Rossi",
            "paziente_phone": None,
        }

    def _cleanup_jobs(self, app_id):
        import booking_service
        booking_service.cancel_scheduled_jobs(app_id)

    def test_aware_offset_registers_all_five_reminder_jobs(self, event_loop):
        import booking_service
        app_id = f"testA_{ObjectId()}"
        start = datetime.now(timezone.utc) + timedelta(hours=2)
        ctx = self._make_ctx(start.isoformat(), durata=50)
        booking_service.schedule_reminders(app_id, ctx)
        expected_offsets = {
            f"rem1d-{app_id}":  start - timedelta(days=1),
            f"rem1h-{app_id}":  start - timedelta(hours=1),
            f"sms30m-{app_id}": start - timedelta(minutes=30),
            f"rem15m-{app_id}": start - timedelta(minutes=15),
            f"review-{app_id}": start + timedelta(minutes=50 + 30),
        }
        for jid, expected_dt in expected_offsets.items():
            job = booking_service.scheduler.get_job(jid)
            if expected_dt <= datetime.now(timezone.utc):
                # rem1d likely in the past (start=+2h) → will NOT be registered
                assert job is None, f"{jid} unexpectedly scheduled at past time"
                continue
            assert job is not None, f"missing job {jid}"
            actual = job.next_run_time.astimezone(timezone.utc)
            diff = abs((actual - expected_dt).total_seconds())
            assert diff < 60, f"{jid}: expected {expected_dt}, got {actual} (diff {diff}s)"
        # no-show jobs
        for jid in [f"noshow-final-{app_id}", f"noshow-post-{app_id}", f"noshow-24h-{app_id}"]:
            assert booking_service.scheduler.get_job(jid) is not None, f"missing {jid}"
        self._cleanup_jobs(app_id)

    def test_naive_data_ora_is_interpreted_as_rome(self, event_loop):
        import booking_service
        app_id = f"testNaive_{ObjectId()}"
        rome = ZoneInfo("Europe/Rome")
        # start in Rome time = now(Rome) + 3h, stored as NAIVE (no offset)
        rome_start = datetime.now(rome) + timedelta(hours=3)
        naive_iso = rome_start.replace(tzinfo=None).isoformat()  # e.g. "2026-01-15T18:00:00"
        assert "+" not in naive_iso and "Z" not in naive_iso, naive_iso

        ctx = self._make_ctx(naive_iso, durata=50)
        booking_service.schedule_reminders(app_id, ctx)

        # rem1h job should fire at rome_start - 1h in UTC
        expected_utc = (rome_start - timedelta(hours=1)).astimezone(timezone.utc)
        job = booking_service.scheduler.get_job(f"rem1h-{app_id}")
        assert job is not None, "rem1h job missing"
        actual_utc = job.next_run_time.astimezone(timezone.utc)
        diff = abs((actual_utc - expected_utc).total_seconds())
        assert diff < 60, (
            f"Naive string not interpreted as Rome: expected {expected_utc}, "
            f"got {actual_utc}, diff={diff}s (would be ~3600s if treated as UTC)"
        )
        self._cleanup_jobs(app_id)

    def test_idempotency_replace_existing(self, event_loop):
        import booking_service
        app_id = f"testIdem_{ObjectId()}"
        start = datetime.now(timezone.utc) + timedelta(hours=4)
        ctx = self._make_ctx(start.isoformat())
        booking_service.schedule_reminders(app_id, ctx)
        first_ids = [j.id for j in booking_service.scheduler.get_jobs() if app_id in j.id]
        booking_service.schedule_reminders(app_id, ctx)
        second_ids = [j.id for j in booking_service.scheduler.get_jobs() if app_id in j.id]
        # No duplicates: unique ids after re-run
        assert len(second_ids) == len(set(second_ids)), f"duplicates: {second_ids}"
        assert sorted(first_ids) == sorted(second_ids), (
            f"job set changed after re-run: {first_ids} vs {second_ids}"
        )
        self._cleanup_jobs(app_id)

    def test_cancel_scheduled_jobs_removes_all(self, event_loop):
        import booking_service
        app_id = f"testCancel_{ObjectId()}"
        start = datetime.now(timezone.utc) + timedelta(hours=4)
        booking_service.schedule_reminders(app_id, self._make_ctx(start.isoformat()))
        # At least one job should exist beforehand
        pre = [j.id for j in booking_service.scheduler.get_jobs() if app_id in j.id]
        assert len(pre) >= 5, f"expected jobs registered, got {pre}"

        booking_service.cancel_scheduled_jobs(app_id)
        for jid in booking_service._reminder_job_ids(app_id):
            assert booking_service.scheduler.get_job(jid) is None, f"job {jid} not removed"

    def test_cancel_scheduled_jobs_is_noop_when_missing(self):
        import booking_service
        # Must not raise for missing jobs
        booking_service.cancel_scheduled_jobs(f"testNope_{ObjectId()}")

    def test_reschedule_reminders_moves_jobs(self, event_loop):
        import booking_service
        old_id = f"testOld_{ObjectId()}"
        new_id = f"testNew_{ObjectId()}"
        old_start = datetime.now(timezone.utc) + timedelta(hours=4)
        new_start = datetime.now(timezone.utc) + timedelta(hours=8)
        booking_service.schedule_reminders(old_id, self._make_ctx(old_start.isoformat()))
        # Sanity: old jobs there
        assert booking_service.scheduler.get_job(f"rem1h-{old_id}") is not None

        booking_service.reschedule_reminders(old_id, new_id, self._make_ctx(new_start.isoformat()))

        # Old cancelled
        for jid in booking_service._reminder_job_ids(old_id):
            assert booking_service.scheduler.get_job(jid) is None, f"old {jid} still present"
        # New registered
        new_job = booking_service.scheduler.get_job(f"rem1h-{new_id}")
        assert new_job is not None, "rem1h for new_id missing"
        expected = new_start - timedelta(hours=1)
        actual = new_job.next_run_time.astimezone(timezone.utc)
        assert abs((actual - expected).total_seconds()) < 60
        self._cleanup_jobs(new_id)
