"""End-to-end test for scheduled_jobs: creates stale user, runs jobs, verifies effects.
Uses direct MongoDB access + admin HTTP endpoints."""
import os
import time
import requests
import pytest
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import motor.motor_asyncio
import asyncio

def _read_env(path, key):
    with open(path) as f:
        for line in f:
            if line.startswith(key + "="):
                return line.split("=", 1)[1].strip().strip('"')
    return None

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _read_env("/app/frontend/.env", "REACT_APP_BACKEND_URL")).rstrip("/")
MONGO_URL = _read_env("/app/backend/.env", "MONGO_URL")
DB_NAME = _read_env("/app/backend/.env", "DB_NAME")

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@funzionabene.it")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin2026")


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    assert r.status_code == 200
    return s


@pytest.fixture
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def db(event_loop):
    client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL, io_loop=event_loop)
    return client[DB_NAME]


def _run(loop, coro):
    return loop.run_until_complete(coro)


class TestRetentionJobE2E:
    def test_retention_anonymizes_stale_paziente(self, admin_session, db, event_loop):
        # Create a stale paziente user directly in DB
        stale_ts = datetime.now(timezone.utc) - timedelta(days=40 * 30)  # 40 months
        email = f"test-fase13-stale-{int(time.time()*1000)}@mailtest.example.com"
        user_doc = {
            "email": email,
            "password_hash": "x",
            "nome": "StaleUser",
            "cognome": "Retention",
            "telefono": "+391234567890",
            "role": "paziente",
            "is_verified": True,
            "is_active": True,
            "created_at": stale_ts,
            "last_login_at": stale_ts,
        }
        res = _run(event_loop, db.users.insert_one(user_doc))
        uid = str(res.inserted_id)
        _run(event_loop, db.pazienti.insert_one({"user_id": uid, "nome": "StaleUser", "cognome": "Retention", "telefono": "+391234567890"}))
        # Also seed a fattura to verify it survives
        fattura_id = _run(event_loop, db.fatture.insert_one({"user_id": uid, "numero": "TEST-F13-001", "importo": 100.0}))
        try:
            # Run retention
            r = admin_session.post(f"{BASE_URL}/api/admin/jobs/retention/run", timeout=30)
            assert r.status_code == 200, r.text
            data = r.json()
            assert data["anonymized"] >= 1

            # Verify user anonymized
            u = _run(event_loop, db.users.find_one({"_id": ObjectId(uid)}))
            assert u["nome"] == "Anonimo"
            assert u["telefono"] is None
            assert u["is_active"] is False
            assert "gdpr_anonymized_at" in u
            assert u["email"] != email  # anonymized email

            # Fattura still intact
            f = _run(event_loop, db.fatture.find_one({"_id": fattura_id.inserted_id}))
            assert f is not None
            assert f["numero"] == "TEST-F13-001"
            assert f["importo"] == 100.0
        finally:
            _run(event_loop, db.users.delete_one({"_id": ObjectId(uid)}))
            _run(event_loop, db.pazienti.delete_one({"user_id": uid}))
            _run(event_loop, db.fatture.delete_one({"_id": fattura_id.inserted_id}))

    def test_retention_skips_paziente_with_recent_appointment(self, admin_session, db, event_loop):
        stale_ts = datetime.now(timezone.utc) - timedelta(days=40 * 30)
        email = f"test-fase13-skipactive-{int(time.time()*1000)}@mailtest.example.com"
        res = _run(event_loop, db.users.insert_one({
            "email": email, "password_hash": "x", "nome": "ActiveOldLogin", "cognome": "Skip",
            "role": "paziente", "is_verified": True, "is_active": True,
            "created_at": stale_ts, "last_login_at": stale_ts,
        }))
        uid = str(res.inserted_id)
        # Recent appointment (within last 36 months)
        recent = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        appt_res = _run(event_loop, db.appuntamenti.insert_one({
            "paziente_user_id": uid, "terapeuta_user_id": "fake-t", "data_ora": recent, "stato": "confermato",
        }))
        try:
            r = admin_session.post(f"{BASE_URL}/api/admin/jobs/retention/run", timeout=30)
            assert r.status_code == 200
            data = r.json()
            assert data["skipped"] >= 1
            u = _run(event_loop, db.users.find_one({"_id": ObjectId(uid)}))
            assert u["nome"] == "ActiveOldLogin"  # NOT anonymized
        finally:
            _run(event_loop, db.users.delete_one({"_id": ObjectId(uid)}))
            _run(event_loop, db.appuntamenti.delete_one({"_id": appt_res.inserted_id}))


class TestLegalDeclineJobE2E:
    def test_legal_decline_hard_deactivates_terapeuta(self, admin_session, db, event_loop):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        email = f"test-fase13-decline-{int(time.time()*1000)}@mailtest.example.com"
        res = _run(event_loop, db.users.insert_one({
            "email": email, "password_hash": "x", "nome": "Dec", "cognome": "Line",
            "role": "terapeuta", "is_verified": True, "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "pending_deactivation_reason": "legal_decline",
            "pending_deactivation_at": past,
            "pending_deactivation_contract_kind": "privacy_terapeuti",
            "pending_deactivation_contract_version": "1.0",
        }))
        uid = str(res.inserted_id)
        _run(event_loop, db.terapisti.insert_one({"user_id": uid, "nome": "Dec", "cognome": "Line"}))
        future = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        appt_res = _run(event_loop, db.appuntamenti.insert_one({
            "terapeuta_user_id": uid, "paziente_user_id": "p1",
            "data_ora": future, "stato": "confermato",
        }))
        try:
            r = admin_session.post(f"{BASE_URL}/api/admin/jobs/legal-decline/run", timeout=30)
            assert r.status_code == 200, r.text
            assert r.json()["processed"] >= 1

            u = _run(event_loop, db.users.find_one({"_id": ObjectId(uid)}))
            assert u["is_active"] is False
            assert "legal_decline_deactivated_at" in u
            assert "pending_deactivation_reason" not in u  # unset

            t = _run(event_loop, db.terapisti.find_one({"user_id": uid}))
            assert t["sospeso"] is True
            assert t["sospeso_motivo"] == "legal_decline_definitive"

            # future appointment cancelled + rimborso_pending
            a = _run(event_loop, db.appuntamenti.find_one({"_id": appt_res.inserted_id}))
            assert a["stato"] == "cancellato"
            assert a["rimborso_pending"] is True
            assert a["cancellato_motivo"] == "legal_decline_terapeuta"

            # Audit log
            audit = _run(event_loop, db.admin_actions.find_one({"user_id": uid, "action": "legal_decline_hard_deactivation"}))
            assert audit is not None
            assert audit["auto"] is True
        finally:
            _run(event_loop, db.users.delete_one({"_id": ObjectId(uid)}))
            _run(event_loop, db.terapisti.delete_one({"user_id": uid}))
            _run(event_loop, db.appuntamenti.delete_one({"_id": appt_res.inserted_id}))
            _run(event_loop, db.admin_actions.delete_many({"user_id": uid}))

    def test_legal_decline_idempotent(self, admin_session, db, event_loop):
        # Running twice should not error out and second run should process 0
        r1 = admin_session.post(f"{BASE_URL}/api/admin/jobs/legal-decline/run", timeout=30)
        r2 = admin_session.post(f"{BASE_URL}/api/admin/jobs/legal-decline/run", timeout=30)
        assert r1.status_code == 200 and r2.status_code == 200
        assert r2.json()["processed"] == 0
