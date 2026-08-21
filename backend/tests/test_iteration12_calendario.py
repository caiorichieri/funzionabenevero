"""Iteration 12 — Calendario + Reschedule flow tests."""
import os
import hashlib
from datetime import datetime, timezone, timedelta

import pytest
import requests
from bson import ObjectId
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv("/app/backend/.env")
load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = (os.environ.get("ADMIN_EMAIL", "admin@funzionabene.it"), os.environ.get("ADMIN_PASSWORD", "admin2026"))
TERA = ("demo.terapeuta@funzionabene.it", "terapeuta2026")
PAZ = ("demo.paziente@funzionabene.it", "paziente2026")


# ─── Fixtures ────────────────────────────────────────────────────────────────
def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def tera_session():
    return _login(*TERA)


@pytest.fixture(scope="module")
def paz_session():
    return _login(*PAZ)


@pytest.fixture(scope="module")
def mongo_db():
    mongo_url = os.environ.get("MONGO_URL")
    dbname = os.environ.get("DB_NAME")
    assert mongo_url and dbname, "MONGO_URL/DB_NAME missing"
    client = MongoClient(mongo_url)
    return client[dbname]


# ─── Therapist calendar ──────────────────────────────────────────────────────
class TestTherapistCalendario:
    def test_get_my_calendario(self, tera_session):
        r = tera_session.get(f"{API}/terapisti/me/calendario")
        assert r.status_code == 200, r.text
        data = r.json()
        assert "calendario" in data
        assert "calendario_bozza" in data
        assert data["durata_sessione_minuti"] == 50

    def test_get_calendario_non_therapist_forbidden(self, paz_session):
        r = paz_session.get(f"{API}/terapisti/me/calendario")
        assert r.status_code == 403

    def test_put_valid_calendario_publishes(self, tera_session):
        body = {"calendario": {"2026-02-20": ["09:00", "14:00"], "2026-02-21": ["10:00"]}, "pubblica": True}
        r = tera_session.put(f"{API}/terapisti/me/calendario", json=body)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["calendario_bozza"] is False
        assert data["calendario_pubblicato_at"] is not None
        assert data["calendario"]["2026-02-20"] == ["09:00", "14:00"]
        # Persist verification via GET
        r2 = tera_session.get(f"{API}/terapisti/me/calendario")
        assert r2.json()["calendario"]["2026-02-20"] == ["09:00", "14:00"]

    def test_put_invalid_date_400(self, tera_session):
        body = {"calendario": {"2026-13-01": ["09:00"]}}
        r = tera_session.put(f"{API}/terapisti/me/calendario", json=body)
        assert r.status_code == 400

    def test_put_invalid_time_400(self, tera_session):
        body = {"calendario": {"2026-02-20": ["BAD"]}}
        r = tera_session.put(f"{API}/terapisti/me/calendario", json=body)
        assert r.status_code == 400

    def test_put_empty_clears(self, tera_session):
        # First put stuff, then empty
        tera_session.put(f"{API}/terapisti/me/calendario", json={"calendario": {"2026-03-10": ["11:00"]}, "pubblica": True})
        r = tera_session.put(f"{API}/terapisti/me/calendario", json={"calendario": {}, "pubblica": True})
        assert r.status_code == 200
        assert r.json()["calendario"] == {}
        # And restore for downstream tests
        tera_session.put(f"{API}/terapisti/me/calendario", json={
            "calendario": {"2026-02-20": ["09:00", "14:00"], "2026-02-21": ["10:00"]}, "pubblica": True
        })

    def test_pubblica_endpoint(self, tera_session):
        # save draft (pubblica=False) then publish
        tera_session.put(f"{API}/terapisti/me/calendario", json={
            "calendario": {"2026-02-20": ["09:00", "14:00"]}, "pubblica": False
        })
        r = tera_session.post(f"{API}/terapisti/me/calendario/pubblica")
        assert r.status_code == 200
        # verify bozza=False
        d = tera_session.get(f"{API}/terapisti/me/calendario").json()
        assert d["calendario_bozza"] is False


# ─── Admin aggregated calendar ───────────────────────────────────────────────
class TestAdminCalendario:
    def test_admin_calendario_feb_2026(self, admin_session):
        r = admin_session.get(f"{API}/admin/calendario", params={"anno": 2026, "mese": 2})
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["days"]) == 28
        # Check day for 2026-02-20 has our therapist
        d20 = next((d for d in data["days"] if d["data"] == "2026-02-20"), None)
        assert d20 is not None
        assert d20["terapisti_count"] >= 1
        assert d20["slot_count"] >= 2

    def test_admin_calendario_invalid_month(self, admin_session):
        r = admin_session.get(f"{API}/admin/calendario", params={"anno": 2026, "mese": 13})
        assert r.status_code == 400

    def test_admin_calendario_forbidden_for_paziente(self, paz_session):
        r = paz_session.get(f"{API}/admin/calendario", params={"anno": 2026, "mese": 2})
        assert r.status_code == 403


# ─── Public calendar for reschedule ──────────────────────────────────────────
class TestPublicTerapistaCalendario:
    def test_public_calendario(self, mongo_db):
        t = mongo_db.terapisti.find_one({"nome": "Maria"})
        assert t is not None, "Maria terapista not found"
        tid = str(t["_id"])
        r = requests.get(f"{API}/public/terapisti/{tid}/calendario", params={"anno": 2026, "mese": 2})
        assert r.status_code == 200, r.text
        data = r.json()
        assert "days" in data
        assert data["terapista"]["id"] == tid


# ─── Reschedule flow ─────────────────────────────────────────────────────────
class TestRescheduleFlow:
    @pytest.fixture(scope="class")
    def test_appt(self, mongo_db):
        """Insert appointment with reschedule token."""
        t = mongo_db.terapisti.find_one({"nome": "Maria"})
        p = mongo_db.pazienti.find_one({})
        # Find paziente user
        u = mongo_db.users.find_one({"email": PAZ[0]})
        assert t and p and u
        raw_token = "TESTTOKEN12345"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        future = datetime.now(timezone.utc) + timedelta(days=30)
        # Ensure date_ora is future (Sep 20 2026 09:00)
        data_ora = datetime(2026, 9, 20, 9, 0, tzinfo=timezone.utc).isoformat()
        # Set expires far in future to allow test
        expires = datetime.now(timezone.utc) + timedelta(days=25)
        doc = {
            "terapeuta_id": str(t["_id"]),
            "paziente_id": str(p["_id"]),
            "paziente_user_id": str(u["_id"]),
            "data_ora": data_ora,
            "durata_minuti": 50,
            "tipo": "online",
            "stato": "confermato",
            "riprogramma_token_hash": token_hash,
            "riprogramma_token_expires": expires,
            "created_at": datetime.now(timezone.utc),
            "_TEST": True,
        }
        # Cleanup any prior test appts
        mongo_db.appuntamenti.delete_many({"_TEST": True})
        ins = mongo_db.appuntamenti.insert_one(doc)
        appt_id = str(ins.inserted_id)
        # Ensure terapista published + verified
        mongo_db.terapisti.update_one({"_id": t["_id"]}, {"$set": {
            "calendario_bozza": False,
            "documenti_verificati": True,
            "disponibilita_calendario": {
                "2026-02-20": ["09:00", "14:00"],
                "2026-09-20": ["09:00", "14:00"],
                "2026-09-21": ["10:00", "11:00"],
            },
        }})
        yield {"id": appt_id, "token": raw_token, "terapista_id": str(t["_id"])}
        mongo_db.appuntamenti.delete_many({"_TEST": True})
        mongo_db.appuntamenti.delete_many({"riprogrammato_da": appt_id})

    def test_validate_valid_token(self, test_appt):
        r = requests.get(
            f"{API}/riprogramma/{test_appt['id']}/validate",
            params={"token": test_appt["token"]},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["appuntamento"]["id"] == test_appt["id"]
        assert d["terapista"]["id"] == test_appt["terapista_id"]

    def test_validate_invalid_token(self, test_appt):
        r = requests.get(
            f"{API}/riprogramma/{test_appt['id']}/validate",
            params={"token": "wrongtoken"},
        )
        assert r.status_code == 404

    def test_confirm_missing_slot(self, test_appt):
        # date that isn't in therapist calendar
        r = requests.post(
            f"{API}/riprogramma/{test_appt['id']}/confirm",
            json={"token": test_appt["token"], "nuova_data_ora": "2026-09-25T15:00:00+00:00"},
        )
        assert r.status_code == 400

    def test_confirm_success(self, test_appt, mongo_db):
        # Insert a payment_transactions doc referencing old appt
        mongo_db.payment_transactions.delete_many({"_TEST": True})
        mongo_db.payment_transactions.insert_one({
            "appointment_id": test_appt["id"],
            "amount": 90,
            "_TEST": True,
        })
        r = requests.post(
            f"{API}/riprogramma/{test_appt['id']}/confirm",
            json={"token": test_appt["token"], "nuova_data_ora": "2026-09-21T10:00:00+00:00"},
        )
        assert r.status_code == 200, r.text
        d = r.json()
        assert "new_appuntamento_id" in d
        # Verify old is cancelled
        old = mongo_db.appuntamenti.find_one({"_id": ObjectId(test_appt["id"])})
        assert old["stato"] == "cancellato"
        assert old["cancellato_motivo"] == "riprogrammato"
        # Verify new
        new = mongo_db.appuntamenti.find_one({"_id": ObjectId(d["new_appuntamento_id"])})
        assert new["stato"] == "confermato"
        assert new["riprogrammato_da"] == test_appt["id"]
        # Payment moved
        pt = mongo_db.payment_transactions.find_one({"_TEST": True})
        assert pt["appointment_id"] == d["new_appuntamento_id"]
        mongo_db.payment_transactions.delete_many({"_TEST": True})
        mongo_db.appuntamenti.delete_many({"_id": ObjectId(d["new_appuntamento_id"])})


# ─── Booking service checks ──────────────────────────────────────────────────
class TestBookingServiceReminders:
    def test_only_one_day_reminder(self):
        import sys
        sys.path.insert(0, "/app/backend")
        import booking_service as bs
        # Read source to confirm no 1-hour job
        import inspect
        src = inspect.getsource(bs.schedule_reminders)
        assert "1-giorno" in src
        # Ensure only one add_job call
        assert src.count("scheduler.add_job") == 1, "Expected exactly 1 reminder job"
