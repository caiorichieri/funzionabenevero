"""Iteration 10 — Router refactor regression tests.

Verifies that the endpoints moved from server.py into
routers/{payments,terapisti,appuntamenti}.py still return identical
behaviour (status codes + response shape).

Auth is cookie-session based via requests.Session.
"""
import os
import re
import requests
import pytest


def _base_url():
    url = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
    if not url:
        with open("/app/frontend/.env") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL"):
                    url = line.split("=", 1)[1].strip().rstrip("/")
    return url


BASE_URL = _base_url()

ADMIN = ("admin@funzionabene.it", "admin2026")
THER = ("demo.terapeuta@funzionabene.it", "terapeuta2026")
PAT = ("demo.paziente@funzionabene.it", "paziente2026")


def _login(email, pwd):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=15)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def therapist():
    return _login(*THER)


@pytest.fixture(scope="module")
def patient():
    return _login(*PAT)


# ─── TERAPISTI router ────────────────────────────────────────────────────────
class TestTerapistiRouter:
    def test_list_terapisti_public_or_auth(self, admin):
        r = admin.get(f"{BASE_URL}/api/terapisti", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) >= 1
        # Data assertion: each terapista should have nome + cognome
        assert all("nome" in t and "cognome" in t for t in data)

    def test_get_single_terapista(self, admin):
        lst = admin.get(f"{BASE_URL}/api/terapisti", timeout=15).json()
        tid = lst[0]["_id"]
        r = admin.get(f"{BASE_URL}/api/terapisti/{tid}", timeout=15)
        assert r.status_code == 200
        assert r.json()["_id"] == tid

    def test_iban_regex_bad(self, admin):
        lst = admin.get(f"{BASE_URL}/api/terapisti", timeout=15).json()
        maria = next((t for t in lst if t.get("nome") == "Maria" and t.get("cognome") == "Rossi"), None)
        assert maria, "Maria Rossi not seeded"
        r = admin.put(f"{BASE_URL}/api/terapisti/{maria['_id']}", json={"iban": "BADIBAN"}, timeout=15)
        assert r.status_code == 422

    def test_iban_valid_and_empty(self, admin):
        lst = admin.get(f"{BASE_URL}/api/terapisti", timeout=15).json()
        maria = next(t for t in lst if t.get("nome") == "Maria" and t.get("cognome") == "Rossi")
        tid = maria["_id"]
        orig = maria.get("iban")
        try:
            r = admin.put(f"{BASE_URL}/api/terapisti/{tid}",
                          json={"iban": "IT60X0542811101000000123456"}, timeout=15)
            assert r.status_code == 200
            assert admin.get(f"{BASE_URL}/api/terapisti/{tid}").json()["iban"] == "IT60X0542811101000000123456"
            # empty clears
            r = admin.put(f"{BASE_URL}/api/terapisti/{tid}", json={"iban": ""}, timeout=15)
            assert r.status_code == 200
        finally:
            if orig:
                admin.put(f"{BASE_URL}/api/terapisti/{tid}", json={"iban": orig}, timeout=15)

    def test_terapista_slots(self, admin):
        lst = admin.get(f"{BASE_URL}/api/terapisti", timeout=15).json()
        tid = lst[0]["_id"]
        r = admin.get(f"{BASE_URL}/api/terapisti/{tid}/slots", timeout=15)
        assert r.status_code == 200
        # slots endpoint returns {terapeuta_id, durata_minuti, slots:[...]}
        body = r.json()
        assert "slots" in body and isinstance(body["slots"], list)

    def test_profilo_me_admin_404(self, admin):
        r = admin.get(f"{BASE_URL}/api/terapisti/profilo/me", timeout=15)
        # Admin has no therapist profile
        assert r.status_code == 404

    def test_profilo_me_therapist_200(self, therapist):
        r = therapist.get(f"{BASE_URL}/api/terapisti/profilo/me", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert d.get("nome") == "Maria"

    def test_therapist_documents_list(self, therapist):
        r = therapist.get(f"{BASE_URL}/api/terapisti/me/documenti", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list) or isinstance(r.json(), dict)


# ─── APPUNTAMENTI router ─────────────────────────────────────────────────────
class TestAppuntamentiRouter:
    def test_admin_list(self, admin):
        r = admin.get(f"{BASE_URL}/api/appuntamenti", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_therapist_list(self, therapist):
        r = therapist.get(f"{BASE_URL}/api/appuntamenti", timeout=15)
        assert r.status_code == 200

    def test_patient_list(self, patient):
        r = patient.get(f"{BASE_URL}/api/appuntamenti", timeout=15)
        assert r.status_code == 200

    def test_stato_invalid_400(self, admin):
        # Try patching an existing or a non-existent id — even a garbage stato should 400 before mongo lookup
        # First fetch or create one to have a valid id
        lst = admin.get(f"{BASE_URL}/api/appuntamenti", timeout=15).json()
        if not lst:
            pytest.skip("No appuntamenti available for stato test")
        aid = lst[0]["_id"]
        r = admin.patch(f"{BASE_URL}/api/appuntamenti/{aid}/stato",
                        json={"stato": "not-a-valid-stato"}, timeout=15)
        assert r.status_code == 400

    def test_unauth_list_401(self):
        r = requests.get(f"{BASE_URL}/api/appuntamenti", timeout=15)
        assert r.status_code in (401, 403)


# ─── PAYMENTS router ─────────────────────────────────────────────────────────
class TestPaymentsRouter:
    def test_status_unknown_session_404(self):
        r = requests.get(f"{BASE_URL}/api/payments/status/cs_test_does_not_exist_xyz", timeout=15)
        assert r.status_code == 404

    def test_webhook_no_signature_400(self):
        r = requests.post(f"{BASE_URL}/api/stripe/webhook", data=b"{}", timeout=15)
        assert r.status_code == 400

    def test_therapist_earnings(self, therapist):
        r = therapist.get(f"{BASE_URL}/api/therapist/earnings", timeout=15)
        assert r.status_code == 200
        d = r.json()
        for k in ("paid_out", "pending_payout", "sessions_count"):
            assert k in d

    def test_therapist_earnings_forbidden_for_admin(self, admin):
        r = admin.get(f"{BASE_URL}/api/therapist/earnings", timeout=15)
        assert r.status_code == 403

    def test_admin_payouts(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/payouts", timeout=15)
        assert r.status_code == 200
        d = r.json()
        assert "items" in d and "summary" in d
        assert isinstance(d["items"], list)
        assert isinstance(d["summary"], list)

    def test_admin_payouts_pending_filter(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/payouts?payout_status=pending", timeout=15)
        assert r.status_code == 200

    def test_admin_payouts_forbidden_non_admin(self, patient):
        r = patient.get(f"{BASE_URL}/api/admin/payouts", timeout=15)
        assert r.status_code in (401, 403)

    def test_checkout_booking_requires_paziente(self, admin):
        # Admin trying to checkout — should be 403 (role guard runs after body validation)
        r = admin.post(f"{BASE_URL}/api/payments/checkout/booking", json={
            "terapeuta_id": "000000000000000000000000",
            "paziente_id": "000000000000000000000000",
            "data_ora": "2030-01-01T10:00:00Z",
            "durata_minuti": 50,
            "tipologia": "individuale",
            "modalita": "online",
            "origin_url": "https://funzionabene.it",
        }, timeout=15)
        assert r.status_code == 403

    def test_checkout_booking_patient_needs_sms(self, patient):
        """SMS check runs before terapista lookup. Accept 403 (SMS expired) OR 404 (SMS ok, bad terapista_id)."""
        r = patient.post(f"{BASE_URL}/api/payments/checkout/booking", json={
            "terapeuta_id": "000000000000000000000000",
            "paziente_id": "000000000000000000000000",
            "data_ora": "2030-01-01T10:00:00Z",
            "durata_minuti": 50,
            "tipologia": "individuale",
            "modalita": "online",
            "origin_url": "https://funzionabene.it",
        }, timeout=15)
        assert r.status_code in (403, 404), r.text


# ─── CRUSCOTTO smoke (still in admin_analytics.py, but must still work) ──────
class TestCruscottoStillWorks:
    def test_cruscotto(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/cruscotto", timeout=20)
        assert r.status_code == 200
        d = r.json()
        for k in ("revenue", "pending_payouts", "sessions_month", "revenue_6m",
                  "top_therapists", "iban_missing"):
            assert k in d
        assert len(d["revenue_6m"]) == 6

    def test_cruscotto_pdf(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/cruscotto/report.pdf", timeout=30)
        assert r.status_code == 200
        assert r.content[:5] == b"%PDF-"


# ─── Untouched surface: auth/dashboard/users ─────────────────────────────────
class TestUntouchedEndpoints:
    def test_dashboard_stats(self, admin):
        r = admin.get(f"{BASE_URL}/api/dashboard/stats", timeout=15)
        assert r.status_code == 200

    def test_users_list(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/utenti", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_articoli_list(self):
        r = requests.get(f"{BASE_URL}/api/public/blog", timeout=15)
        assert r.status_code == 200
