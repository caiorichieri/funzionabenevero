"""Backend tests for iteration 28 — no-show detection + video-call access gating.

Covers:
  - POST /api/appuntamenti/{id}/video-token   → 425 too_early / 410 session_closed / 200 in-window
  - GET  /api/videocall-magic/{id}?token=X    → 425 / 410 (role_hint=paziente) / 403 invalid
  - GET  /api/admin/seduta-logs               → admin-only, filters (outcome / dates / terapeuta)
  - GET  /api/appuntamenti/{id}/presenze      → prefers snapshot, falls back to live
  - daily_service.create_room_for_appointment / create_meeting_token → nbf = start-20min
  - booking_service.schedule_reminders → registers noshow-final / noshow-post / noshow-24h jobs
  - no_show_service.run_no_show_check → snapshot + stato + idempotency of no_show_notified_at
  - booking_service._ensure_videocall_magic_token → videocall_magic_expires = start + 15 min
  - email_service.send_no_show_* templates → SEND_EMAILS=false fallback returns False, no raise
"""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest
import requests
from bson import ObjectId

# Make backend importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient  # noqa: E402

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    # Read from frontend .env
    fe_env = Path(__file__).resolve().parent.parent.parent / "frontend" / ".env"
    for line in fe_env.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL"):
            BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
            break

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

ADMIN_EMAIL = "hr@funzionabene.it"
ADMIN_PASS = "@Bidoc2026!"

# Test-scoped users seeded in DB (demo users may be absent after DB reset)
_uniq = ObjectId().binary.hex()[:8]
PAZ_EMAIL = f"test_noshow_paz_{_uniq}@example.com"
PAZ_PASS = "TestPaziente2026!"
TER_EMAIL = f"test_noshow_ter_{_uniq}@example.com"
TER_PASS = "TestTerapeuta2026!"


# ─── DB fixtures ──────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def db(event_loop):
    client = AsyncIOMotorClient(MONGO_URL)
    return client[DB_NAME]


@pytest.fixture(scope="module", autouse=True)
def seed_users(event_loop, db):
    """Seed a test paziente + terapeuta (users + pazienti + terapisti docs) so tests
    have deterministic accounts even if demo seed data is missing."""
    import bcrypt as _bc

    def _hash(p):
        return _bc.hashpw(p.encode(), _bc.gensalt()).decode()

    async def _seed():
        now = datetime.now(timezone.utc)
        # paziente user
        paz_user = {
            "email": PAZ_EMAIL, "password_hash": _hash(PAZ_PASS),
            "nome": "Luca", "cognome": "Bianchi", "role": "paziente",
            "is_verified": True, "is_active": True, "created_at": now,
            "test_seed": True,
        }
        r = await db.users.update_one({"email": PAZ_EMAIL}, {"$set": paz_user}, upsert=True)
        paz_u = await db.users.find_one({"email": PAZ_EMAIL})
        await db.pazienti.update_one(
            {"user_id": str(paz_u["_id"])},
            {"$set": {"user_id": str(paz_u["_id"]), "nome": "Luca", "cognome": "Bianchi",
                      "created_at": now, "test_seed": True}},
            upsert=True,
        )
        # terapeuta user
        ter_user = {
            "email": TER_EMAIL, "password_hash": _hash(TER_PASS),
            "nome": "Mario", "cognome": "Rossi", "role": "terapeuta",
            "is_verified": True, "is_active": True, "approval_status": "approvato",
            "created_at": now, "test_seed": True,
        }
        await db.users.update_one({"email": TER_EMAIL}, {"$set": ter_user}, upsert=True)
        ter_u = await db.users.find_one({"email": TER_EMAIL})
        await db.terapisti.update_one(
            {"user_id": str(ter_u["_id"])},
            {"$set": {"user_id": str(ter_u["_id"]), "nome": "Mario", "cognome": "Rossi",
                      "prezzo_sessione": 90, "created_at": now, "test_seed": True}},
            upsert=True,
        )
    event_loop.run_until_complete(_seed())
    yield
    async def _teardown():
        await db.users.delete_many({"test_seed": True})
        await db.pazienti.delete_many({"test_seed": True})
        await db.terapisti.delete_many({"test_seed": True})
    event_loop.run_until_complete(_teardown())


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_sess():
    return _login(ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture(scope="module")
def paz_sess():
    return _login(PAZ_EMAIL, PAZ_PASS)


@pytest.fixture(scope="module")
def ter_sess():
    return _login(TER_EMAIL, TER_PASS)


# Seed helper: creates an appointment linked to demo paziente & demo terapeuta
async def _seed_appt(db, data_ora_iso, durata=50, extra=None):
    ter_user = await db.users.find_one({"email": TER_EMAIL})
    paz_user = await db.users.find_one({"email": PAZ_EMAIL})
    terapista = await db.terapisti.find_one({"user_id": str(ter_user["_id"])})
    paziente = await db.pazienti.find_one({"user_id": str(paz_user["_id"])})
    assert terapista and paziente, "Demo therapist/patient missing — reseed backend"

    doc = {
        "terapeuta_id": str(terapista["_id"]),
        "paziente_id": str(paziente["_id"]),
        "terapeuta_user_id": str(ter_user["_id"]),
        "paziente_user_id": str(paz_user["_id"]),
        "data_ora": data_ora_iso,
        "durata_minuti": durata,
        "stato": "confermato",
        "daily_room_name": f"appuntamento-TEST_{ObjectId()}",
        "daily_room_url": "https://mock.daily.co/test",
        "created_at": datetime.now(timezone.utc),
        "test_seed": True,
    }
    if extra:
        doc.update(extra)
    # Grant informed consent so patient can hit video-token endpoint
    await db.informed_consents.update_one(
        {"paziente_id": str(paz_user["_id"]), "terapista_id": str(terapista["_id"])},
        {"$set": {"paziente_id": str(paz_user["_id"]),
                  "terapista_id": str(terapista["_id"]),
                  "status": "granted",
                  "granted_at": datetime.now(timezone.utc),
                  "test_seed": True}},
        upsert=True,
    )
    res = await db.appuntamenti.insert_one(doc)
    doc["_id"] = res.inserted_id
    return doc


@pytest.fixture(scope="module", autouse=True)
def cleanup(event_loop, db):
    yield
    async def _cleanup():
        await db.appuntamenti.delete_many({"test_seed": True})
        await db.seduta_logs.delete_many({"appuntamento_id": {"$exists": True}, "presenze.test_seed": True})
        await db.seduta_logs.delete_many({"room_name": {"$regex": "^appuntamento-TEST_"}})
        await db.informed_consents.delete_many({"test_seed": True})
    event_loop.run_until_complete(_cleanup())


# ─── video-token endpoint (auth flow) ─────────────────────────────────────────
class TestVideoToken:
    def test_425_too_early_when_more_than_20min_before(self, event_loop, db, paz_sess):
        future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        appt = event_loop.run_until_complete(_seed_appt(db, future))
        r = paz_sess.post(f"{BASE_URL}/api/appuntamenti/{appt['_id']}/video-token")
        assert r.status_code == 425, f"expected 425 got {r.status_code}: {r.text}"
        body = r.json()["detail"]
        assert body["code"] == "too_early"
        assert "available_at" in body and "start_at" in body

    def test_410_session_closed_when_past_close(self, event_loop, db, paz_sess):
        # start 2h ago, durata 50 min → close_at = start + 65 min → still ~55 min past close
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        appt = event_loop.run_until_complete(_seed_appt(db, past))
        r = paz_sess.post(f"{BASE_URL}/api/appuntamenti/{appt['_id']}/video-token")
        assert r.status_code == 410, f"expected 410 got {r.status_code}: {r.text}"
        assert r.json()["detail"]["code"] == "session_closed"

    def test_200_in_window(self, event_loop, db, paz_sess):
        # start 5 min from now — inside [-20, +65]
        soon = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        appt = event_loop.run_until_complete(_seed_appt(db, soon))
        r = paz_sess.post(f"{BASE_URL}/api/appuntamenti/{appt['_id']}/video-token")
        # Daily might be disabled → token can be None but status must be 200
        assert r.status_code == 200, f"expected 200 got {r.status_code}: {r.text}"
        body = r.json()
        assert "room_url" in body
        assert body.get("is_owner") is False


# ─── videocall-magic endpoint (public token) ──────────────────────────────────
class TestVideocallMagic:
    def _seed_with_magic(self, event_loop, db, data_ora_iso):
        import hashlib
        import secrets as _secrets
        raw = _secrets.token_urlsafe(32)
        h = hashlib.sha256(raw.encode("ascii")).hexdigest()
        extra = {"videocall_magic_hash": h,
                 "videocall_magic_expires": datetime.fromisoformat(data_ora_iso) + timedelta(minutes=15)}
        appt = event_loop.run_until_complete(_seed_appt(db, data_ora_iso, extra=extra))
        return appt, raw

    def test_403_invalid_token(self, event_loop, db):
        future = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        appt, _ = self._seed_with_magic(event_loop, db, future)
        r = requests.get(f"{BASE_URL}/api/videocall-magic/{appt['_id']}", params={"token": "wrong"})
        assert r.status_code == 403

    def test_425_too_early(self, event_loop, db):
        future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        appt, raw = self._seed_with_magic(event_loop, db, future)
        r = requests.get(f"{BASE_URL}/api/videocall-magic/{appt['_id']}", params={"token": raw})
        assert r.status_code == 425
        assert r.json()["detail"]["code"] == "too_early"

    def test_410_with_role_hint_paziente(self, event_loop, db):
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        appt, raw = self._seed_with_magic(event_loop, db, past)
        r = requests.get(f"{BASE_URL}/api/videocall-magic/{appt['_id']}", params={"token": raw})
        assert r.status_code == 410
        d = r.json()["detail"]
        assert d["code"] == "session_closed"
        assert d.get("role_hint") == "paziente"


# ─── daily_service nbf offset ─────────────────────────────────────────────────
class TestDailyNbfOffset:
    def test_create_room_uses_nbf_start_minus_20(self, event_loop, monkeypatch):
        """Force Daily enabled and stub httpx.AsyncClient.post to capture payload."""
        import daily_service

        captured = {}

        class _Resp:
            status_code = 200
            def json(self): return {"name": "room", "url": "https://x/y"}
            text = ""

        class _StubClient:
            def __init__(self, *a, **kw): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def post(self, url, headers=None, json=None):
                captured["payload"] = json
                return _Resp()
            async def get(self, url, headers=None): return _Resp()

        monkeypatch.setattr(daily_service, "_is_enabled", lambda: True)
        monkeypatch.setattr(daily_service.httpx, "AsyncClient", _StubClient)

        start = datetime(2030, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        event_loop.run_until_complete(
            daily_service.create_room_for_appointment("appt1", start.isoformat(), 50)
        )
        expected_nbf = int((start - timedelta(minutes=20)).timestamp())
        assert captured["payload"]["properties"]["nbf"] == expected_nbf

    def test_create_meeting_token_uses_nbf_start_minus_20(self, event_loop, monkeypatch):
        import daily_service
        captured = {}

        class _Resp:
            status_code = 200
            def json(self): return {"token": "tok"}
            text = ""

        class _StubClient:
            def __init__(self, *a, **kw): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def post(self, url, headers=None, json=None):
                captured["payload"] = json
                return _Resp()

        monkeypatch.setattr(daily_service, "_is_enabled", lambda: True)
        monkeypatch.setattr(daily_service.httpx, "AsyncClient", _StubClient)

        start = datetime(2030, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        event_loop.run_until_complete(
            daily_service.create_meeting_token("room1", "Test User", False, start.isoformat(), 50)
        )
        expected_nbf = int((start - timedelta(minutes=20)).timestamp())
        assert captured["payload"]["properties"]["nbf"] == expected_nbf


# ─── no_show_service.run_no_show_check ────────────────────────────────────────
class TestNoShowService:
    def test_run_no_show_check_no_show_entrambi_and_idempotent(self, event_loop, db, monkeypatch):
        import no_show_service
        # empty participants → no_show_entrambi
        async def fake_presenza(_room): return []
        monkeypatch.setattr(no_show_service, "get_room_presenza", fake_presenza)
        # Neutralize email sends
        async def _noop(*a, **kw): return False
        for name in ["send_no_show_paziente_email", "send_no_show_terapeuta_email",
                     "send_terapeuta_absent_paziente_email", "send_terapeuta_absent_terapeuta_email",
                     "send_no_show_admin_alert"]:
            monkeypatch.setattr(f"email_service.{name}", _noop)

        past = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
        appt = event_loop.run_until_complete(_seed_appt(db, past))
        app_id = str(appt["_id"])

        snap1 = event_loop.run_until_complete(no_show_service.run_no_show_check(app_id, is_final=True))
        assert snap1 is not None
        assert snap1["outcome"] == no_show_service.OUTCOME_NONE
        assert snap1["paziente_joined"] is False and snap1["terapeuta_joined"] is False

        # stato updated
        appt_after = event_loop.run_until_complete(db.appuntamenti.find_one({"_id": ObjectId(app_id)}))
        assert appt_after["stato"] == "no_show_entrambi"
        assert appt_after["outcome"] == no_show_service.OUTCOME_NONE
        first_notified = appt_after.get("no_show_notified_at")
        assert first_notified is not None

        # Second run → idempotent: no_show_notified_at preserved
        snap2 = event_loop.run_until_complete(no_show_service.run_no_show_check(app_id, is_final=True))
        assert snap2 is not None
        appt_after2 = event_loop.run_until_complete(db.appuntamenti.find_one({"_id": ObjectId(app_id)}))
        assert appt_after2["no_show_notified_at"] == first_notified, "no_show_notified_at must not be overwritten"

    def test_run_no_show_paziente_only(self, event_loop, db, monkeypatch):
        """Simulate patient in room, therapist absent → outcome no_show_terapeuta."""
        import no_show_service
        # Patient's demo name is Luca Bianchi
        async def fake_presenza(_room):
            return [{"user_name": "Luca Bianchi", "join_time": "x", "duration": 300}]
        monkeypatch.setattr(no_show_service, "get_room_presenza", fake_presenza)
        for name in ["send_no_show_paziente_email", "send_no_show_terapeuta_email",
                     "send_terapeuta_absent_paziente_email", "send_terapeuta_absent_terapeuta_email",
                     "send_no_show_admin_alert"]:
            async def _n(*a, **kw): return False
            monkeypatch.setattr(f"email_service.{name}", _n)

        past = (datetime.now(timezone.utc) - timedelta(minutes=25)).isoformat()
        appt = event_loop.run_until_complete(_seed_appt(db, past))
        snap = event_loop.run_until_complete(
            no_show_service.run_no_show_check(str(appt["_id"]), is_final=True)
        )
        assert snap["outcome"] == no_show_service.OUTCOME_NO_TER
        assert snap["paziente_joined"] is True
        assert snap["terapeuta_joined"] is False


# ─── booking_service.schedule_reminders adds no-show jobs ─────────────────────
class TestScheduleReminders:
    def test_schedule_reminders_registers_noshow_jobs(self, event_loop, db):
        import booking_service
        # Ensure scheduler is up (AsyncIOScheduler needs a running loop)
        async def _start_if_needed():
            if not booking_service.scheduler.running:
                booking_service.scheduler.start()
        event_loop.run_until_complete(_start_if_needed())

        # Insert a fake appt with future data_ora
        future = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
        appt = event_loop.run_until_complete(_seed_appt(db, future))
        app_id = str(appt["_id"])
        ctx = {
            "data_ora": future,
            "durata_minuti": 50,
            "paziente_email": "x@y.z",
            "paziente_nome": "Luca",
            "terapista_cognome": "Rossi",
            "paziente_phone": None,
        }
        booking_service.schedule_reminders(app_id, ctx)
        ids = {j.id for j in booking_service.scheduler.get_jobs()}
        assert f"noshow-final-{app_id}" in ids, ids
        assert f"noshow-post-{app_id}" in ids, ids
        assert f"noshow-24h-{app_id}" in ids, ids

        # cleanup jobs
        for jid in [f"noshow-final-{app_id}", f"noshow-post-{app_id}", f"noshow-24h-{app_id}",
                    f"rem1d-{app_id}", f"rem1h-{app_id}", f"sms30m-{app_id}",
                    f"rem15m-{app_id}", f"review-{app_id}"]:
            try:
                booking_service.scheduler.remove_job(jid)
            except Exception:
                pass


# ─── _ensure_videocall_magic_token uses start+15 min expiry ───────────────────
class TestMagicTokenExpiry:
    def test_magic_expires_is_start_plus_15min(self, event_loop, db):
        import booking_service
        future = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
        appt = event_loop.run_until_complete(_seed_appt(db, future, extra={"videocall_magic_hash": None}))
        # Remove any pre-existing magic hash to force generation
        event_loop.run_until_complete(db.appuntamenti.update_one(
            {"_id": appt["_id"]}, {"$unset": {"videocall_magic_hash": "", "videocall_magic_expires": ""}}
        ))
        appt_fresh = event_loop.run_until_complete(db.appuntamenti.find_one({"_id": appt["_id"]}))
        raw = event_loop.run_until_complete(
            booking_service._ensure_videocall_magic_token(str(appt["_id"]), appt_fresh)
        )
        assert raw is not None
        stored = event_loop.run_until_complete(db.appuntamenti.find_one({"_id": appt["_id"]}))
        exp = stored["videocall_magic_expires"]
        start = datetime.fromisoformat(future)
        # ensure tz aware for compare
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        diff = (exp - start).total_seconds()
        # iter34 fix: magic-link expiry now mirrors the logged-in join window
        # (start + durata + 15 min = 65 min for a 50-min session), not start+15.
        assert 64 * 60 <= diff <= 66 * 60, f"expected ~65 min offset (start+durata+15), got {diff}s"


# ─── admin/seduta-logs listing + permissions ──────────────────────────────────
class TestSedutaLogs:
    def test_admin_seduta_logs_403_for_paziente(self, paz_sess):
        r = paz_sess.get(f"{BASE_URL}/api/admin/seduta-logs")
        assert r.status_code == 403

    def test_admin_seduta_logs_403_for_terapeuta(self, ter_sess):
        r = ter_sess.get(f"{BASE_URL}/api/admin/seduta-logs")
        assert r.status_code == 403

    def test_admin_seduta_logs_lists_and_filters(self, event_loop, db, admin_sess):
        # Seed a snapshot manually
        appt_iso = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        appt = event_loop.run_until_complete(_seed_appt(db, appt_iso))
        now = datetime.now(timezone.utc)
        event_loop.run_until_complete(db.seduta_logs.update_one(
            {"appuntamento_id": str(appt["_id"])},
            {"$set": {
                "appuntamento_id": str(appt["_id"]),
                "terapeuta_id": appt["terapeuta_id"],
                "paziente_id": appt["paziente_id"],
                "room_name": appt["daily_room_name"],
                "presenze": [{"user_name": "TEST_dummy"}],
                "paziente_joined": False,
                "terapeuta_joined": False,
                "outcome": "no_show_entrambi",
                "snapshot_at": now,
            }, "$setOnInsert": {"created_at": now}},
            upsert=True,
        ))
        r = admin_sess.get(f"{BASE_URL}/api/admin/seduta-logs", params={"outcome": "no_show_entrambi"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body and "count" in body
        assert body["count"] >= 1
        assert any(it["appuntamento_id"] == str(appt["_id"]) for it in body["items"])

        # filter by terapeuta_id — should still include our seeded row
        r2 = admin_sess.get(f"{BASE_URL}/api/admin/seduta-logs",
                            params={"terapeuta_id": appt["terapeuta_id"]})
        assert r2.status_code == 200
        assert any(it["appuntamento_id"] == str(appt["_id"]) for it in r2.json()["items"])

        # filter with mismatching outcome → excludes it
        r3 = admin_sess.get(f"{BASE_URL}/api/admin/seduta-logs",
                            params={"outcome": "entrambi_presenti", "terapeuta_id": appt["terapeuta_id"]})
        assert r3.status_code == 200
        assert not any(it["appuntamento_id"] == str(appt["_id"]) for it in r3.json()["items"])


# ─── /appuntamenti/{id}/presenze prefers snapshot ─────────────────────────────
class TestPresenzeEndpoint:
    def test_snapshot_source_preferred(self, event_loop, db, admin_sess):
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        appt = event_loop.run_until_complete(_seed_appt(db, past))
        now = datetime.now(timezone.utc)
        event_loop.run_until_complete(db.seduta_logs.update_one(
            {"appuntamento_id": str(appt["_id"])},
            {"$set": {
                "appuntamento_id": str(appt["_id"]),
                "presenze": [{"user_name": "TEST_snap"}],
                "paziente_joined": True,
                "terapeuta_joined": False,
                "outcome": "no_show_terapeuta",
                "snapshot_at": now,
                "room_name": appt["daily_room_name"],
            }, "$setOnInsert": {"created_at": now}},
            upsert=True,
        ))
        r = admin_sess.get(f"{BASE_URL}/api/appuntamenti/{appt['_id']}/presenze")
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "snapshot"
        assert body["outcome"] == "no_show_terapeuta"
        assert body["paziente_joined"] is True and body["terapeuta_joined"] is False

    def test_presenze_403_for_paziente(self, event_loop, db, paz_sess):
        past = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        appt = event_loop.run_until_complete(_seed_appt(db, past))
        r = paz_sess.get(f"{BASE_URL}/api/appuntamenti/{appt['_id']}/presenze")
        assert r.status_code == 403


# ─── Email templates: SEND_EMAILS=false → False without raising ───────────────
class TestEmailTemplatesFallback:
    def test_all_five_no_show_templates_return_false_when_disabled(self, event_loop, monkeypatch):
        import email_service
        monkeypatch.setattr(email_service, "SEND_EMAILS", False)

        ctx = {
            "paziente_email": "p@x.it",
            "terapista_email": "t@x.it",
            "paziente_nome": "Luca",
            "paziente_cognome": "Bianchi",
            "terapista_cognome": "Rossi",
            "terapista_id": "abc",
            "app_id": "xyz",
            "data_ora": "2030-01-01T12:00:00+00:00",
        }

        async def run_all():
            return [
                await email_service.send_no_show_paziente_email(ctx),
                await email_service.send_no_show_terapeuta_email(ctx),
                await email_service.send_terapeuta_absent_paziente_email(ctx),
                await email_service.send_terapeuta_absent_terapeuta_email(ctx),
                await email_service.send_no_show_admin_alert("hr@funzionabene.it", "no_show_entrambi", ctx),
            ]

        results = event_loop.run_until_complete(run_all())
        assert results == [False, False, False, False, False], results
