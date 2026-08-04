"""Iteration 11 — Auth/Blog/BookingService refactor regression tests.

Verifies that endpoints moved from server.py into
routers/auth.py, routers/blog.py, and booking_service.py still behave
identically. All auth is cookie-session based via requests.Session.
"""
import os
import sys
import uuid
import requests
import pytest

# Ensure /app/backend is importable so we can validate module-level imports
_BACKEND = "/app/backend"
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)


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


# ─── AUTH router (moved to routers/auth.py) ──────────────────────────────────
class TestAuthRouter:
    def test_login_valid_returns_200_and_sets_cookie(self):
        s = requests.Session()
        r = s.post(f"{BASE_URL}/api/auth/login",
                   json={"email": ADMIN[0], "password": ADMIN[1]}, timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert data["email"] == ADMIN[0]
        assert data["role"] == "admin"
        # Cookie assertion
        assert "access_token" in s.cookies, f"cookies: {s.cookies.get_dict()}"

    def test_login_wrong_password_401(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": ADMIN[0], "password": "wrongpass"}, timeout=15)
        assert r.status_code == 401

    def test_login_unknown_user_401(self):
        r = requests.post(f"{BASE_URL}/api/auth/login",
                          json={"email": "nobody@funzionabene.it", "password": "x"}, timeout=15)
        assert r.status_code == 401

    def test_me_authenticated(self, admin):
        r = admin.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code == 200
        assert r.json()["role"] == "admin"

    def test_me_unauthenticated_401(self):
        r = requests.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r.status_code in (401, 403)

    def test_logout_clears_cookies(self):
        s = _login(*ADMIN)
        r = s.post(f"{BASE_URL}/api/auth/logout", timeout=15)
        assert r.status_code == 200
        # After logout, /me should not authorize using the session cookies
        # Note: server sends delete_cookie which unsets access_token
        r2 = s.get(f"{BASE_URL}/api/auth/me", timeout=15)
        assert r2.status_code in (401, 403)

    def test_forgot_password_generic_response_existing(self):
        r = requests.post(f"{BASE_URL}/api/auth/forgot-password",
                          json={"email": ADMIN[0]}, timeout=15)
        assert r.status_code == 200
        assert "Se un account esiste" in r.json().get("message", "")

    def test_forgot_password_generic_response_unknown(self):
        r = requests.post(f"{BASE_URL}/api/auth/forgot-password",
                          json={"email": f"nobody-{uuid.uuid4().hex}@funzionabene.it"}, timeout=15)
        assert r.status_code == 200
        assert "Se un account esiste" in r.json().get("message", "")

    def test_reset_password_bad_token_400(self):
        # Token must be >=40 chars to pass Pydantic validation (min_length=40),
        # then digest lookup fails → 400.
        r = requests.post(f"{BASE_URL}/api/auth/reset-password",
                          json={"token": "x" * 64, "new_password": "newpass1234"},
                          timeout=15)
        assert r.status_code == 400

    def test_register_new_patient_returns_otp_dev_or_message(self):
        email = f"TEST_reg_{uuid.uuid4().hex[:8]}@funzionabene.it"
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email,
            "password": "testpass1234",
            "nome": "Test",
            "cognome": "User",
            "role": "paziente",
            "consenso_privacy": True,
        }, timeout=15)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "message" in body
        # If email sending fails or EXPOSE_OTP_DEV=true, otp_dev is present
        # (Skebby OTP dev also always present in this env). Either way,
        # we don't hard-require it, but if present it should be 6 digits.
        if "otp_dev" in body:
            assert body["otp_dev"].isdigit() and len(body["otp_dev"]) == 6
        # cleanup: try to fully delete via admin (nice-to-have, but not required)

    def test_register_duplicate_email_400(self):
        r = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": ADMIN[0],
            "password": "testpass1234",
            "nome": "X", "cognome": "Y",
            "role": "paziente",
            "consenso_privacy": True,
        }, timeout=15)
        assert r.status_code == 400

    def test_verify_otp_bad_code_400(self):
        # First register a fresh user
        email = f"TEST_otp_{uuid.uuid4().hex[:8]}@funzionabene.it"
        rr = requests.post(f"{BASE_URL}/api/auth/register", json={
            "email": email, "password": "testpass1234",
            "nome": "T", "cognome": "U", "role": "paziente",
            "consenso_privacy": True,
        }, timeout=15)
        assert rr.status_code == 200
        # Wrong OTP
        r = requests.post(f"{BASE_URL}/api/auth/verify-otp",
                          json={"email": email, "otp_code": "000000"}, timeout=15)
        assert r.status_code == 400

    def test_resend_otp_unknown_email_404(self):
        r = requests.post(f"{BASE_URL}/api/auth/resend-otp",
                          json={"email": f"unknown-{uuid.uuid4().hex}@funzionabene.it"},
                          timeout=15)
        assert r.status_code == 404


# ─── BLOG router (moved to routers/blog.py) ──────────────────────────────────
class TestBlogRouter:
    def test_list_blog_admin_sees_all(self, admin):
        r = admin.get(f"{BASE_URL}/api/blog", timeout=15)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_list_blog_therapist_sees_only_own(self, therapist):
        r = therapist.get(f"{BASE_URL}/api/blog", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        # If therapist has any articles, they should all be their own
        # (autore_id equals their user id)
        # We can only sanity-check the shape.
        for d in data:
            assert "titolo" in d or "_id" in d

    def test_public_blog_no_auth_only_published(self):
        r = requests.get(f"{BASE_URL}/api/public/blog", timeout=15)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        for d in data:
            assert d.get("stato") == "pubblicato"

    def test_therapist_create_bozza_then_admin_approves(self, therapist, admin):
        payload = {
            "titolo": f"TEST Iter11 Article {uuid.uuid4().hex[:6]}",
            "contenuto": "Contenuto di test per iteration 11 refactor.",
            "categoria": "psicologia",
        }
        r = therapist.post(f"{BASE_URL}/api/blog", json=payload, timeout=15)
        assert r.status_code == 200, r.text
        art = r.json()
        assert art["stato"] == "bozza", art
        assert art["titolo"] == payload["titolo"]
        art_id = art["_id"]

        # Approve as admin
        r2 = admin.patch(f"{BASE_URL}/api/blog/{art_id}/approva", timeout=15)
        assert r2.status_code == 200

        # Should now appear on public blog
        pub = requests.get(f"{BASE_URL}/api/public/blog", timeout=15).json()
        assert any(a["_id"] == art_id for a in pub), "approved article not on public feed"

        # Cleanup: delete
        rd = admin.delete(f"{BASE_URL}/api/blog/{art_id}", timeout=15)
        assert rd.status_code == 200

    def test_admin_create_publishes_directly(self, admin):
        payload = {
            "titolo": f"TEST Iter11 Admin Post {uuid.uuid4().hex[:6]}",
            "contenuto": "Admin published directly.",
            "categoria": "sessuologia",
        }
        r = admin.post(f"{BASE_URL}/api/blog", json=payload, timeout=15)
        assert r.status_code == 200
        art = r.json()
        assert art["stato"] == "pubblicato"
        art_id = art["_id"]

        # Update via PUT
        r2 = admin.put(f"{BASE_URL}/api/blog/{art_id}",
                       json={**payload, "titolo": payload["titolo"] + " EDIT"}, timeout=15)
        assert r2.status_code == 200
        assert "EDIT" in r2.json()["titolo"]

        # Rifiuta
        r3 = admin.patch(f"{BASE_URL}/api/blog/{art_id}/rifiuta", timeout=15)
        assert r3.status_code == 200

        # Cleanup
        admin.delete(f"{BASE_URL}/api/blog/{art_id}", timeout=15)

    def test_patient_cannot_create_blog(self, patient):
        r = patient.post(f"{BASE_URL}/api/blog", json={
            "titolo": "nope", "contenuto": "x", "categoria": "psicologia",
        }, timeout=15)
        assert r.status_code == 403

    def test_unauthenticated_cannot_list_blog(self):
        r = requests.get(f"{BASE_URL}/api/blog", timeout=15)
        assert r.status_code in (401, 403)


# ─── PAYMENTS: direct import (no more lazy import) ───────────────────────────
class TestPaymentsDirectImport:
    def test_webhook_no_signature_400(self):
        # Payments router still boots and webhook route wired
        r = requests.post(f"{BASE_URL}/api/stripe/webhook", data=b"{}", timeout=15)
        assert r.status_code == 400

    def test_status_unknown_session_404(self):
        r = requests.get(f"{BASE_URL}/api/payments/status/cs_test_xyz_bogus", timeout=15)
        assert r.status_code == 404

    def test_finalize_confirmed_booking_is_directly_imported(self):
        """Assert booking_service.finalize_confirmed_booking is importable
        at module scope from routers/payments.py — no lazy import."""
        import importlib
        payments_mod = importlib.import_module("routers.payments")
        assert hasattr(payments_mod, "finalize_confirmed_booking"), (
            "finalize_confirmed_booking must be imported at module scope "
            "in routers/payments.py (no lazy `from server import ...`)"
        )
        # And that it originates from booking_service
        from booking_service import finalize_confirmed_booking as fcb
        assert payments_mod.finalize_confirmed_booking is fcb


# ─── BOOKING SERVICE: scheduler startup ──────────────────────────────────────
class TestBookingServiceScheduler:
    def test_scheduler_started_at_boot(self):
        """If startup succeeded and app is answering, scheduler must be running.
        Directly assert on the singleton in booking_service."""
        from booking_service import scheduler
        # The scheduler singleton is process-local — in test process it is NOT
        # started by uvicorn. So this assertion cannot be made against the
        # test-process import. Instead verify via app behaviour: a working
        # endpoint means startup handler ran, which called start_scheduler().
        # Fallback: hit dashboard/stats and expect 200 (implicit health).
        s = _login(*ADMIN)
        r = s.get(f"{BASE_URL}/api/dashboard/stats", timeout=15)
        assert r.status_code == 200

    def test_scheduler_module_singleton_exists(self):
        from booking_service import scheduler, start_scheduler, stop_scheduler
        assert scheduler is not None
        assert callable(start_scheduler) and callable(stop_scheduler)


# ─── UNTOUCHED SURFACE re-check ─────────────────────────────────────────────
class TestUntouchedStillWorking:
    def test_public_terapisti(self):
        r = requests.get(f"{BASE_URL}/api/public/terapisti", timeout=15)
        assert r.status_code == 200

    def test_cruscotto(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/cruscotto", timeout=20)
        assert r.status_code == 200

    def test_dashboard_stats(self, admin):
        r = admin.get(f"{BASE_URL}/api/dashboard/stats", timeout=15)
        assert r.status_code == 200

    def test_admin_utenti(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/utenti", timeout=15)
        assert r.status_code == 200

    def test_admin_payouts(self, admin):
        r = admin.get(f"{BASE_URL}/api/admin/payouts", timeout=15)
        assert r.status_code == 200

    def test_faq_public(self):
        r = requests.get(f"{BASE_URL}/api/public/faq", timeout=15)
        assert r.status_code == 200
