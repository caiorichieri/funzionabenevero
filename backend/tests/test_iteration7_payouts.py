"""Iteration 7 — Fase 2 fatturazione + payouts admin dashboard tests.
Tests: /api/admin/payouts (GET, filter), /api/admin/payouts/mark-paid (POST),
/api/admin/fattura-sanitaria/{tx_id}, /api/admin/fattura-commissione/{terapeuta_id}/{year}/{month}.
Also asserts Twilio sms_service module loads with config present.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://portugues-writer-2.preview.emergentagent.com").rstrip("/")
ADMIN_EMAIL = "admin@funzionabene.it"
ADMIN_PASS = "admin2026"


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASS}, timeout=30)
    assert r.status_code == 200, f"Admin login failed: {r.status_code} {r.text}"
    return s


# ─── Auth guard ─────────────────────────────────────────────────────────────
class TestAuthGuard:
    def test_payouts_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/payouts", timeout=15)
        assert r.status_code in (401, 403), f"Expected 401/403, got {r.status_code}"

    def test_fattura_sanitaria_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/fattura-sanitaria/000000000000000000000000", timeout=15)
        assert r.status_code in (401, 403)

    def test_fattura_commissione_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/admin/fattura-commissione/000000000000000000000000/2026/8", timeout=15)
        assert r.status_code in (401, 403)


# ─── Payouts listing ────────────────────────────────────────────────────────
class TestPayoutsList:
    def test_list_all_schema(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/payouts", timeout=30)
        assert r.status_code == 200, r.text
        data = r.json()
        assert "items" in data and isinstance(data["items"], list)
        assert "summary" in data and isinstance(data["summary"], list)
        assert len(data["items"]) >= 1, "Expected at least 1 transaction seeded"
        it = data["items"][0]
        for k in ("id", "amount", "platform_fee_amount", "therapist_amount",
                  "payout_status", "terapeuta", "paziente_initials"):
            assert k in it, f"Missing key {k} in item"
        assert "nome" in it["terapeuta"] and "cognome" in it["terapeuta"]

    def test_seed_transaction_present(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/payouts", timeout=30)
        items = r.json()["items"]
        # Look for Dr. Maria Rossi with amount 9000 (€90.00)
        matches = [
            it for it in items
            if it["terapeuta"].get("cognome") == "Rossi"
            and it["amount"] == 9000
            and it["platform_fee_amount"] == 2700
            and it["therapist_amount"] == 6300
        ]
        assert len(matches) >= 1, f"Expected Dr. Maria Rossi €90 tx (30% fee) — got items sample: {items[:2]}"
        assert matches[0]["paziente_initials"] == "L.B.", f"Expected L.B. initials, got {matches[0]['paziente_initials']}"

    def test_filter_pending(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/payouts?payout_status=pending", timeout=30)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["payout_status"] != "paid", f"Non-pending item leaked: {it['payout_status']}"

    def test_filter_paid(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/payouts?payout_status=paid", timeout=30)
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["payout_status"] == "paid"


# ─── mark-paid workflow ─────────────────────────────────────────────────────
class TestMarkPaid:
    def test_mark_paid_and_verify(self, admin_session):
        # Get one pending item
        r = admin_session.get(f"{BASE_URL}/api/admin/payouts?payout_status=pending", timeout=30)
        pending = r.json()["items"]
        if not pending:
            pytest.skip("No pending payouts to mark paid (seed may already be paid)")
        tx_id = pending[0]["id"]
        r2 = admin_session.post(
            f"{BASE_URL}/api/admin/payouts/mark-paid",
            json={"transaction_ids": [tx_id], "payout_reference": "TEST-BONIFICO-001"},
            timeout=30,
        )
        assert r2.status_code == 200, r2.text
        body = r2.json()
        assert body.get("marked") == 1, f"Expected marked=1, got {body}"

        # Verify moved to paid
        r3 = admin_session.get(f"{BASE_URL}/api/admin/payouts?payout_status=paid", timeout=30)
        paid_ids = [it["id"] for it in r3.json()["items"]]
        assert tx_id in paid_ids
        marked = next(it for it in r3.json()["items"] if it["id"] == tx_id)
        assert marked["payout_status"] == "paid"
        assert marked.get("payout_reference") == "TEST-BONIFICO-001"

    def test_mark_paid_empty_ids(self, admin_session):
        r = admin_session.post(
            f"{BASE_URL}/api/admin/payouts/mark-paid",
            json={"transaction_ids": []},
            timeout=15,
        )
        assert r.status_code == 400


# ─── PDF generation ─────────────────────────────────────────────────────────
class TestFatturaPDF:
    def test_fattura_sanitaria_pdf(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/payouts?payout_status=paid", timeout=30)
        paid = r.json()["items"]
        if not paid:
            pytest.skip("No paid transactions available for fattura sanitaria")
        tx_id = paid[0]["id"]
        pdf_r = admin_session.get(f"{BASE_URL}/api/admin/fattura-sanitaria/{tx_id}", timeout=60)
        assert pdf_r.status_code == 200, pdf_r.text[:200]
        assert "application/pdf" in pdf_r.headers.get("content-type", "")
        assert pdf_r.content[:4] == b"%PDF", f"Not a PDF: {pdf_r.content[:20]}"

    def test_fattura_commissione_pdf(self, admin_session):
        # Find a paid tx to get the therapist_id + month
        r = admin_session.get(f"{BASE_URL}/api/admin/payouts?payout_status=paid", timeout=30)
        paid = r.json()["items"]
        if not paid:
            pytest.skip("No paid transactions")
        it = paid[0]
        terapeuta_id = it["terapeuta"]["id"]
        paid_at = it.get("paid_at") or ""
        # paid_at is ISO string
        from datetime import datetime
        dt = datetime.fromisoformat(paid_at.replace("Z", "+00:00")) if paid_at else datetime.utcnow()
        year, month = dt.year, dt.month

        pdf_r = admin_session.get(
            f"{BASE_URL}/api/admin/fattura-commissione/{terapeuta_id}/{year}/{month}", timeout=60
        )
        assert pdf_r.status_code == 200, pdf_r.text[:200]
        assert "application/pdf" in pdf_r.headers.get("content-type", "")
        assert pdf_r.content[:4] == b"%PDF"

    def test_fattura_commissione_bad_period(self, admin_session):
        r = admin_session.get(
            f"{BASE_URL}/api/admin/fattura-commissione/000000000000000000000000/2026/13", timeout=15
        )
        assert r.status_code == 400


# ─── SMS service module smoke ───────────────────────────────────────────────
class TestSMSServiceModule:
    def test_env_vars_present(self):
        # Read the actual env file to verify keys exist
        env_path = "/app/backend/.env"
        with open(env_path) as f:
            content = f.read()
        for key in ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_VERIFY_SERVICE_SID"):
            assert key in content, f"{key} missing from backend/.env"

    def test_sms_service_imports_and_client(self):
        # Load the module fresh and assert Client initialised
        import importlib, sys
        sys.path.insert(0, "/app/backend")
        import sms_service
        importlib.reload(sms_service)
        assert sms_service._client is not None, "Twilio Client failed to init"
        assert sms_service.VERIFY_SERVICE_SID, "TWILIO_VERIFY_SERVICE_SID not loaded"

    def test_normalize_phone(self):
        import sys
        sys.path.insert(0, "/app/backend")
        from sms_service import _normalize_phone
        assert _normalize_phone("3518230667") == "+393518230667"
        assert _normalize_phone("+393518230667") == "+393518230667"
        assert _normalize_phone("003518230667") == "+3518230667"
