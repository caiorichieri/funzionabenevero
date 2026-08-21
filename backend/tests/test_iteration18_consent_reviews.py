"""Tests for Blocco 1 + 2 features:
- Informed consent (patient ↔ therapist via magic link)
- Cancellation policy
- Reviews with admin approval
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


# ─── Informed Consent ────────────────────────────────────────────────────────
class TestInformedConsent:
    def test_get_consent_unknown_id_returns_404(self):
        r = requests.get(f"{BASE_URL}/api/consenso-informato/000000000000000000000000?token=fake")
        assert r.status_code == 404, f"Expected 404, got {r.status_code}"

    def test_accept_consent_unknown_id_returns_404(self):
        r = requests.post(
            f"{BASE_URL}/api/consenso-informato/000000000000000000000000/accept",
            json={"token": "fake"},
        )
        assert r.status_code == 404

    def test_therapist_update_consent_requires_auth(self):
        r = requests.patch(f"{BASE_URL}/api/terapeuta/consenso-informato", json={"consenso_informato_testo": "x" * 200})
        assert r.status_code == 401

    def test_mia_consent_status_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/consenso-informato/mia/xxx")
        assert r.status_code == 401


# ─── Cancellation Policy ─────────────────────────────────────────────────────
class TestCancellationPolicy:
    def test_get_policy_is_public(self):
        r = requests.get(f"{BASE_URL}/api/cancella-policy")
        assert r.status_code == 200
        data = r.json()
        assert "hours_full_refund" in data
        assert "hours_partial_refund" in data
        assert "partial_refund_pct" in data
        assert "description" in data
        # Sane defaults
        assert data["hours_full_refund"] > data["hours_partial_refund"]
        assert 0 <= data["partial_refund_pct"] <= 100

    def test_cancel_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/appuntamenti/000000000000000000000000/cancella")
        assert r.status_code == 401

    def test_preview_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/appuntamenti/000000000000000000000000/preview-cancellazione")
        assert r.status_code == 401


# ─── Reviews ─────────────────────────────────────────────────────────────────
class TestReviews:
    def test_public_reviews_unknown_therapist(self):
        r = requests.get(f"{BASE_URL}/api/reviews/terapista/000000000000000000000000")
        assert r.status_code == 200
        data = r.json()
        assert data["reviews"] == []
        assert data["total"] == 0
        assert data["avg_rating"] == 0

    def test_submit_review_requires_auth(self):
        r = requests.post(f"{BASE_URL}/api/reviews", json={"appuntamento_id": "x", "voto": 5})
        assert r.status_code == 401

    def test_pending_appointments_requires_auth(self):
        r = requests.get(f"{BASE_URL}/api/reviews/pending-appointments")
        assert r.status_code == 401

    def test_admin_pending_requires_admin(self):
        r = requests.get(f"{BASE_URL}/api/admin/reviews/pending")
        assert r.status_code == 401

    def test_admin_approve_requires_admin(self):
        r = requests.post(f"{BASE_URL}/api/admin/reviews/000000000000000000000000/approve")
        assert r.status_code == 401

    def test_admin_reject_requires_admin(self):
        r = requests.post(
            f"{BASE_URL}/api/admin/reviews/000000000000000000000000/reject",
            json={"motivo": "spam"},
        )
        assert r.status_code == 401

    def test_admin_count_pending_requires_admin(self):
        r = requests.get(f"{BASE_URL}/api/admin/reviews/count-pending")
        assert r.status_code == 401


# ─── End-to-end (admin login + reviews moderation) ───────────────────────────
class TestReviewsAdminE2E:
    @pytest.fixture(scope="class")
    def admin_session(self):
        s = requests.Session()
        # Try both possible admin credentials
        for creds in [
            {"email": os.environ.get("ADMIN_EMAIL", "admin@funzionabene.it"),
             "password": os.environ.get("ADMIN_PASSWORD", "@Bidoc2026!")},
            {"email": "admin@funzionabene.it", "password": "admin2026"},
        ]:
            r = s.post(f"{BASE_URL}/api/auth/login", json=creds)
            if r.status_code == 200 and r.json().get("role") == "admin":
                return s
        pytest.skip("Admin credentials not available for e2e test")

    def test_admin_can_list_pending(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/reviews/pending")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_admin_can_count_pending(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/reviews/count-pending")
        assert r.status_code == 200
        assert "count" in r.json()

    def test_admin_approve_unknown_returns_404(self, admin_session):
        r = admin_session.post(f"{BASE_URL}/api/admin/reviews/000000000000000000000000/approve")
        assert r.status_code == 404
