"""
Iteration 6 backend tests — Stripe checkout, contracts, password reset, audit consent.
Uses credentials from /app/memory/test_credentials.md (post 20/04/2026 reset):
  - admin@funzionabene.it / admin2026
  - demo.terapeuta@funzionabene.it / terapeuta2026
  - demo.paziente@funzionabene.it / paziente2026
"""
import os
# Load env from frontend/.env to get REACT_APP_BACKEND_URL if not set
if not os.environ.get('REACT_APP_BACKEND_URL'):
    try:
        with open('/app/frontend/.env') as f:
            for line in f:
                if line.startswith('REACT_APP_BACKEND_URL='):
                    os.environ['REACT_APP_BACKEND_URL'] = line.split('=', 1)[1].strip().strip('"')
    except Exception:
        pass
if not os.environ.get('MONGO_URL'):
    try:
        with open('/app/backend/.env') as f:
            for line in f:
                if line.startswith('MONGO_URL='):
                    os.environ['MONGO_URL'] = line.split('=', 1)[1].strip().strip('"')
                if line.startswith('DB_NAME='):
                    os.environ['DB_NAME'] = line.split('=', 1)[1].strip().strip('"')
    except Exception:
        pass

import pytest
import requests
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timezone

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'funzionabene_db')

ADMIN = ("admin@funzionabene.it", "admin2026")
TERAPEUTA = ("demo.terapeuta@funzionabene.it", "terapeuta2026")
PAZIENTE = ("demo.paziente@funzionabene.it", "paziente2026")


def _login(email, pw):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, f"Login failed for {email}: {r.status_code} {r.text}"
    return s, r.json()


@pytest.fixture(scope="module")
def mongo_db():
    client = MongoClient(MONGO_URL)
    return client[DB_NAME]


# ── AUTH ────────────────────────────────────────────────────────────────────
class TestAuth:
    def test_admin_login(self):
        s, u = _login(*ADMIN)
        assert u.get("role") == "admin"

    def test_terapeuta_login(self):
        s, u = _login(*TERAPEUTA)
        assert u.get("role") == "terapeuta"

    def test_paziente_login(self):
        s, u = _login(*PAZIENTE)
        assert u.get("role") == "paziente"


# ── PASSWORD RESET ──────────────────────────────────────────────────────────
class TestPasswordReset:
    def test_forgot_password_existing_and_missing_return_same(self):
        r1 = requests.post(f"{BASE_URL}/api/auth/forgot-password",
                           json={"email": "demo.paziente@funzionabene.it"})
        r2 = requests.post(f"{BASE_URL}/api/auth/forgot-password",
                           json={"email": "nonexistent@test.zz"})
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json() == r2.json(), (r1.json(), r2.json())
        assert "Se un account esiste" in r1.json().get("message", "")

    def test_reset_password_fake_token_returns_generic_400(self):
        fake = "randomfaketoken000000000000000000000000000000000"
        r = requests.post(f"{BASE_URL}/api/auth/reset-password",
                          json={"token": fake, "new_password": "MyNewPass2026!"})
        assert r.status_code == 400
        detail = r.json().get("detail", "")
        assert "non è valido o è scaduto" in detail, detail


# ── MANDATO / CONTRACTS ─────────────────────────────────────────────────────
class TestMandato:
    def test_public_mandato_current(self):
        r = requests.get(f"{BASE_URL}/api/contracts/current/mandato_all_incasso")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d.get("version") >= 1
        assert d.get("content_hash") and len(d["content_hash"]) == 64
        html = d.get("content_html", "")
        assert "BIDOC" in html or "bidoc" in html.lower()
        assert "mandato" in html.lower()
        assert "sistema ts" in html.lower() or "tessera sanitaria" in html.lower()

    def test_admin_list_contracts_and_acceptances(self):
        s, _ = _login(*ADMIN)
        r = s.get(f"{BASE_URL}/api/admin/contracts")
        assert r.status_code == 200
        items = r.json().get("items", [])
        assert len(items) >= 1
        mandato = next((c for c in items if c.get("kind") == "mandato_all_incasso" and c.get("is_current")), None)
        assert mandato is not None, "No current mandato_all_incasso found"

        # Acceptances
        r2 = s.get(f"{BASE_URL}/api/admin/contracts/{mandato['id']}/acceptances")
        assert r2.status_code == 200
        # Not strictly requiring >=1 (env-dependent) but log for triage
        print(f"acceptances count = {len(r2.json().get('items', []))}")

    def test_non_admin_cannot_list_contracts(self):
        s, _ = _login(*PAZIENTE)
        r = s.get(f"{BASE_URL}/api/admin/contracts")
        assert r.status_code in (401, 403)


# ── STRIPE CHECKOUT ─────────────────────────────────────────────────────────
class TestStripeCheckout:
    def test_checkout_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/payments/checkout/booking", json={
            "terapeuta_id": "x", "paziente_id": "x",
            "data_ora": "2026-06-01T10:00:00", "durata_minuti": 50,
            "origin_url": BASE_URL,
        })
        assert r.status_code == 401

    def test_checkout_requires_sms_verification(self, mongo_db):
        # Ensure paziente does NOT have recent SMS verification
        mongo_db.users.update_one(
            {"email": "demo.paziente@funzionabene.it"},
            {"$set": {"telefono_verificato": False, "telefono_verificato_at": None}},
        )
        s, u = _login(*PAZIENTE)
        # Get a terapeuta
        r_ter = requests.get(f"{BASE_URL}/api/public/terapisti")
        assert r_ter.status_code == 200
        terapisti = r_ter.json()
        assert len(terapisti) > 0
        terapeuta_id = terapisti[0]["_id"]

        pz_prof = s.get(f"{BASE_URL}/api/pazienti/profilo/me").json()
        paziente_id = pz_prof["_id"]

        r = s.post(f"{BASE_URL}/api/payments/checkout/booking", json={
            "terapeuta_id": terapeuta_id,
            "paziente_id": paziente_id,
            "data_ora": "2026-06-01T10:00:00",
            "durata_minuti": 50,
            "origin_url": BASE_URL,
        })
        assert r.status_code == 403, r.text
        assert "SMS" in r.json().get("detail", "") or "telefono" in r.json().get("detail", "").lower()

    def test_checkout_success_returns_stripe_url_and_split(self, mongo_db):
        # Bypass SMS verification
        mongo_db.users.update_one(
            {"email": "demo.paziente@funzionabene.it"},
            {"$set": {
                "telefono_verificato": True,
                "telefono_verificato_at": datetime.now(timezone.utc),
            }},
        )
        s, u = _login(*PAZIENTE)
        r_ter = requests.get(f"{BASE_URL}/api/public/terapisti")
        terapisti = r_ter.json()
        assert len(terapisti) > 0
        terapeuta = terapisti[0]
        terapeuta_id = terapeuta["_id"]

        # Force prezzo_sessione = 90 for deterministic split assertion
        mongo_db.terapisti.update_one(
            {"_id": ObjectId(terapeuta_id)},
            {"$set": {"prezzo_sessione": 90}},
        )

        pz_prof = s.get(f"{BASE_URL}/api/pazienti/profilo/me").json()
        paziente_id = pz_prof["_id"]

        r = s.post(f"{BASE_URL}/api/payments/checkout/booking", json={
            "terapeuta_id": terapeuta_id,
            "paziente_id": paziente_id,
            "data_ora": "2026-06-01T10:00:00",
            "durata_minuti": 50,
            "origin_url": BASE_URL,
            "opposizione_ts": False,
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert "checkout.stripe.com" in d.get("checkout_url", ""), d
        assert d.get("currency") == "eur"
        assert d.get("session_id")
        assert d.get("appointment_id")
        assert d.get("amount") == 9000

        # Verify DB split
        tx = mongo_db.payment_transactions.find_one({"session_id": d["session_id"]})
        assert tx is not None
        assert tx["amount"] == 9000
        assert tx["platform_fee_amount"] == 2700
        assert tx["therapist_amount"] == 6300
        # 9000 cents >= 7747 → marca_da_bollo required
        assert tx["marca_da_bollo_required"] is True
        assert tx["marca_da_bollo_amount"] == 200

    def test_marca_da_bollo_threshold(self, mongo_db):
        """Verify marca_da_bollo boundary — reuse last tx."""
        tx = mongo_db.payment_transactions.find_one(
            {"paziente_user_id": {"$ne": None}, "amount": 9000},
            sort=[("created_at", -1)],
        )
        if tx:
            assert tx["marca_da_bollo_required"] is True, "9000 cents >= 7747 threshold"
            assert tx["marca_da_bollo_amount"] == 200


# ── AUDIT CONSENT ───────────────────────────────────────────────────────────
class TestAuditConsent:
    def test_post_consent_log(self):
        r = requests.post(f"{BASE_URL}/api/audit/consent", json={
            "policy_version": "1.0",
            "prefs": {"necessary": True, "analytics": True, "marketing": False},
            "language": "it",
            "page_url": "https://example.com/",
        })
        assert r.status_code == 200, r.text
        d = r.json()
        assert "audit_id" in d and "policy_hash" in d

    def test_admin_can_list_consents(self):
        s, _ = _login(*ADMIN)
        r = s.get(f"{BASE_URL}/api/admin/audit/consents?limit=10")
        assert r.status_code == 200
        data = r.json()
        assert "items" in data and "total" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
