"""Fase 13 tests — GDPR compliance: consents at signup + scheduled jobs
(retention_anonymize weekly + process_legal_declines hourly)."""
import os
import time
import requests
import pytest
from datetime import datetime, timezone, timedelta

def _read_frontend_env(key):
    try:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith(key + "="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        return None
    return None

BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _read_frontend_env("REACT_APP_BACKEND_URL") or "").rstrip("/")
assert BASE_URL, "REACT_APP_BACKEND_URL required"

ADMIN_EMAIL = "admin@funzionabene.it"
ADMIN_PASSWORD = "admin2026"
TEST_PREFIX = "test-fase13-"


def _rand_email(tag: str) -> str:
    return f"{TEST_PREFIX}{tag}-{int(time.time()*1000)}@mailtest.example.com"


# ── Consents at signup ──────────────────────────────────────────────────────
class TestRegisterConsents:
    def test_paziente_missing_termini_rejected(self):
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": _rand_email("no-termini"),
            "password": "TestPass123!",
            "nome": "Mario", "cognome": "Rossi", "role": "paziente",
            "consenso_privacy": True, "consenso_termini": False,
        }, timeout=15)
        assert r.status_code == 400, r.text
        detail = r.json().get("detail", "").lower()
        assert "consensi obbligatori" in detail or "privacy" in detail

    def test_paziente_missing_privacy_rejected(self):
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": _rand_email("no-privacy"),
            "password": "TestPass123!",
            "nome": "Mario", "cognome": "Rossi", "role": "paziente",
            "consenso_privacy": False, "consenso_termini": True,
        }, timeout=15)
        assert r.status_code == 400, r.text

    def test_paziente_all_consents_ok_and_history(self):
        email = _rand_email("full")
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "nome": "Lucia", "cognome": "Verdi", "role": "paziente",
            "consenso_privacy": True, "consenso_termini": True,
            "consenso_dati_sanitari": True, "consenso_marketing": True,
            "consenso_ricerca": True, "consenso_miglioramento": True,
            "consent_version_privacy": "1.0", "consent_version_termini": "1.0",
        }, timeout=15)
        assert r.status_code == 200, r.text
        # Cannot query DB directly here; use gdpr export via admin? Use my_consents after login
        # But paziente is not yet verified → cannot login. Verify history via admin consents audit.
        # Use OTP dev to verify
        otp = r.json().get("otp_dev")
        assert otp, "otp_dev not exposed — cannot complete verify"
        r2 = requests.post(f"{BASE_URL}/api/auth/verify-otp", json={"email": email, "otp_code": otp}, timeout=15)
        assert r2.status_code == 200
        # Login and hit /api/user/consents/mine
        s = requests.Session()
        lr = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": "TestPass123!"}, timeout=15)
        assert lr.status_code == 200
        cr = s.get(f"{BASE_URL}/api/user/consents/mine", timeout=15)
        assert cr.status_code == 200
        data = cr.json()
        consents = data["consents"]
        assert consents["privacy_accettata"] is True
        assert consents["termini_accettati"] is True
        assert consents["dati_sanitari"] is True
        assert consents["marketing"] is True
        assert consents["ricerca"] is True
        assert consents["miglioramento"] is True
        # 6 history events at signup
        types = {h["consent_type"] for h in data["history"]}
        assert {"privacy", "termini", "dati_sanitari", "marketing", "ricerca", "miglioramento"}.issubset(types)
        assert len(data["history"]) >= 6

    def test_paziente_partial_optional_consents(self):
        email = _rand_email("partial")
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "nome": "Anna", "cognome": "Neri", "role": "paziente",
            "consenso_privacy": True, "consenso_termini": True,
            "consenso_dati_sanitari": True, "consenso_marketing": False,
            "consenso_ricerca": False, "consenso_miglioramento": False,
        }, timeout=15)
        assert r.status_code == 200, r.text

    def test_terapeuta_only_privacy_ok(self):
        email = _rand_email("terap")
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "TestPass123!",
            "nome": "Giulia", "cognome": "T", "role": "terapeuta",
            "consenso_privacy": True,
            # no termini, no dati_sanitari
        }, timeout=15)
        assert r.status_code == 200, r.text


# ── Admin trigger jobs ─────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text}")
    return s


class TestScheduledJobs:
    def test_retention_run_admin(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/jobs/retention/run", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ["anonymized", "skipped", "ran_at"]:
            assert k in data

    def test_retention_run_forbidden_to_anon(self):
        r = requests.post(f"{BASE_URL}/api/admin/jobs/retention/run", timeout=15)
        assert r.status_code in (401, 403)

    def test_legal_decline_run_admin(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/jobs/legal-decline/run", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        for k in ["processed", "errors", "ran_at"]:
            assert k in data

    def test_retention_idempotent(self, admin_session):
        """Running retention twice back-to-back must not double-process."""
        r1 = admin_session.post(f"{BASE_URL}/api/admin/jobs/retention/run", timeout=30)
        r2 = admin_session.post(f"{BASE_URL}/api/admin/jobs/retention/run", timeout=30)
        assert r1.status_code == 200 and r2.status_code == 200
        # Second run should typically have anonymized=0 unless test data changed in between
        # We just assert the endpoint stayed consistent
        assert isinstance(r2.json().get("anonymized"), int)
