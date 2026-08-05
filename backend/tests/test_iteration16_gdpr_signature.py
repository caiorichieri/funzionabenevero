"""Iteration 16 - GDPR compliance features test:
   1) legal signature flow (pending / sign / receipt / list)
   2) MAJOR notification + public decline token
   3) User GDPR (export / delete / consents)
"""
import os
import io
import hashlib
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "https://portugues-writer-2.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN = ("admin@funzionabene.it", "admin2026")
TERAPEUTA = ("demo.terapeuta@funzionabene.it", "terapeuta2026")
PAZIENTE = ("demo.paziente@funzionabene.it", "paziente2026")
TERAPEUTA_FULL_NAME = "Maria Rossi"

REQUIRED_KINDS = ["contratto_collaborazione", "privacy_terapeuti", "termini_pazienti", "cookie_policy"]


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"Login failed for {email}: {r.status_code} {r.text[:200]}")
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def paziente_session():
    return _login(*PAZIENTE)


@pytest.fixture(scope="function")
def terapeuta_session():
    """Fresh terapeuta session each test (state changes across tests)."""
    return _login(*TERAPEUTA)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _ensure_current_contracts(admin_s):
    """Make sure each required kind has a current contract; return dict kind->id."""
    ids = {}
    for kind in REQUIRED_KINDS:
        r = requests.get(f"{API}/contracts/current/{kind}", timeout=15)
        if r.status_code == 200:
            ids[kind] = r.json()["id"]
            continue
        # create one
        payload = {
            "kind": kind,
            "title": f"Test {kind}",
            "content_html": f"<h1>{kind}</h1><p>Contenuto test iter16.</p>",
        }
        rc = admin_s.post(f"{API}/admin/contracts", json=payload, timeout=20)
        assert rc.status_code == 200, f"admin create contract {kind} failed: {rc.text[:200]}"
        ids[kind] = rc.json()["id"]
    return ids


def _reset_terapeuta_signatures(admin_s):
    """Remove existing acceptances for terapeuta so pending returns 4."""
    # Access DB via a helper endpoint? None available. Use a raw mongo cmd via python.
    from pymongo import MongoClient
    m = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    dbn = os.environ.get("DB_NAME", "funzionabene_db")
    u = m[dbn].users.find_one({"email": TERAPEUTA[0]})
    if u:
        m[dbn].contract_acceptances.delete_many({"user_id": str(u["_id"])})
    m.close()


# ─── Tests: pending ───────────────────────────────────────────────────────────

class TestPending:
    def test_pending_paziente_empty(self, paziente_session):
        r = paziente_session.get(f"{API}/contracts/pending/mine", timeout=15)
        assert r.status_code == 200
        assert r.json().get("pending") == []

    def test_pending_terapeuta_four_docs(self, admin_session, terapeuta_session):
        _ensure_current_contracts(admin_session)
        _reset_terapeuta_signatures(admin_session)
        r = terapeuta_session.get(f"{API}/contracts/pending/mine", timeout=15)
        assert r.status_code == 200
        pending = r.json().get("pending", [])
        kinds = {p["kind"] for p in pending}
        assert kinds == set(REQUIRED_KINDS), f"expected 4 kinds, got {kinds}"


# ─── Tests: sign ──────────────────────────────────────────────────────────────

class TestSign:
    def test_sign_wrong_name_400(self, admin_session, terapeuta_session):
        _ensure_current_contracts(admin_session)
        _reset_terapeuta_signatures(admin_session)
        pending = terapeuta_session.get(f"{API}/contracts/pending/mine", timeout=15).json()["pending"]
        cids = [p["contract_id"] for p in pending]
        r = terapeuta_session.post(f"{API}/contracts/sign", json={
            "contract_ids": cids,
            "signature_name": "Nome Sbagliato",
            "scrolled_all": True,
        }, timeout=30)
        assert r.status_code == 400
        assert "corrispondere" in r.text.lower() or "nome" in r.text.lower()

    def test_sign_correct_name_case_insensitive(self, admin_session, terapeuta_session):
        _ensure_current_contracts(admin_session)
        _reset_terapeuta_signatures(admin_session)
        pending = terapeuta_session.get(f"{API}/contracts/pending/mine", timeout=15).json()["pending"]
        cids = [p["contract_id"] for p in pending]
        assert len(cids) == 4
        r = terapeuta_session.post(f"{API}/contracts/sign", json={
            "contract_ids": cids,
            "signature_name": TERAPEUTA_FULL_NAME.lower(),  # case-insensitive
            "scrolled_all": True,
        }, timeout=60)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body["receipt_id"]
        assert body["pdf_hash"] and len(body["pdf_hash"]) == 64
        assert len(body["documents_signed"]) == 4
        # storage_path may be None if object storage fails silently — allow either
        # After signing, pending should be empty
        r2 = terapeuta_session.get(f"{API}/contracts/pending/mine", timeout=15)
        assert r2.status_code == 200
        assert r2.json()["pending"] == []
        # Store receipt id for next test
        pytest.receipt_id = body["receipt_id"]
        pytest.storage_path = body.get("storage_path")

    def test_sign_scroll_flag_false(self, admin_session, terapeuta_session):
        _ensure_current_contracts(admin_session)
        _reset_terapeuta_signatures(admin_session)
        pending = terapeuta_session.get(f"{API}/contracts/pending/mine", timeout=15).json()["pending"]
        r = terapeuta_session.post(f"{API}/contracts/sign", json={
            "contract_ids": [pending[0]["contract_id"]],
            "signature_name": TERAPEUTA_FULL_NAME,
            "scrolled_all": False,
        }, timeout=30)
        assert r.status_code == 400


# ─── Tests: receipt download & list ───────────────────────────────────────────

class TestReceipt:
    def test_receipt_download_owner(self, admin_session, terapeuta_session):
        _ensure_current_contracts(admin_session)
        _reset_terapeuta_signatures(admin_session)
        pending = terapeuta_session.get(f"{API}/contracts/pending/mine", timeout=15).json()["pending"]
        cids = [p["contract_id"] for p in pending]
        sr = terapeuta_session.post(f"{API}/contracts/sign", json={
            "contract_ids": cids, "signature_name": TERAPEUTA_FULL_NAME, "scrolled_all": True,
        }, timeout=60)
        assert sr.status_code == 200, sr.text
        rid = sr.json()["receipt_id"]
        storage_path = sr.json().get("storage_path")

        r = terapeuta_session.get(f"{API}/contracts/receipt/{rid}", timeout=30)
        if storage_path is None:
            # Object storage failed silently -> 410
            assert r.status_code == 410
        else:
            assert r.status_code == 200
            assert r.headers.get("content-type", "").startswith("application/pdf")
            assert r.content[:4] == b"%PDF"

    def test_receipt_forbidden_other_user(self, admin_session, terapeuta_session, paziente_session):
        _ensure_current_contracts(admin_session)
        _reset_terapeuta_signatures(admin_session)
        pending = terapeuta_session.get(f"{API}/contracts/pending/mine", timeout=15).json()["pending"]
        cids = [p["contract_id"] for p in pending]
        sr = terapeuta_session.post(f"{API}/contracts/sign", json={
            "contract_ids": cids, "signature_name": TERAPEUTA_FULL_NAME, "scrolled_all": True,
        }, timeout=60).json()
        rid = sr["receipt_id"]
        # paziente should be forbidden
        r = paziente_session.get(f"{API}/contracts/receipt/{rid}", timeout=15)
        assert r.status_code == 403
        # admin should be allowed
        ra = admin_session.get(f"{API}/contracts/receipt/{rid}", timeout=15)
        assert ra.status_code in (200, 410), ra.text[:200]

    def test_list_signatures_grouped(self, admin_session, terapeuta_session):
        _ensure_current_contracts(admin_session)
        _reset_terapeuta_signatures(admin_session)
        pending = terapeuta_session.get(f"{API}/contracts/pending/mine", timeout=15).json()["pending"]
        cids = [p["contract_id"] for p in pending]
        sr = terapeuta_session.post(f"{API}/contracts/sign", json={
            "contract_ids": cids, "signature_name": TERAPEUTA_FULL_NAME, "scrolled_all": True,
        }, timeout=60).json()
        rid = sr["receipt_id"]

        r = terapeuta_session.get(f"{API}/contracts/signatures/mine", timeout=15)
        assert r.status_code == 200
        items = r.json()["items"]
        matching = [i for i in items if i["receipt_id"] == rid]
        assert matching, "signed receipt not found in listing"
        assert len(matching[0]["documents"]) == 4


# ─── Tests: MAJOR notification + decline ─────────────────────────────────────

class TestMajorAndDecline:
    def test_notify_major_and_decline(self, admin_session, terapeuta_session):
        # Ensure baseline: terapeuta signed current versions
        _ensure_current_contracts(admin_session)
        _reset_terapeuta_signatures(admin_session)
        pending = terapeuta_session.get(f"{API}/contracts/pending/mine", timeout=15).json()["pending"]
        cids = [p["contract_id"] for p in pending]
        terapeuta_session.post(f"{API}/contracts/sign", json={
            "contract_ids": cids, "signature_name": TERAPEUTA_FULL_NAME, "scrolled_all": True,
        }, timeout=60)

        # Admin creates a new version (v>1) of contratto_collaborazione
        kind = "contratto_collaborazione"
        rc = admin_session.post(f"{API}/admin/contracts", json={
            "kind": kind, "title": "Contratto v-next iter16",
            "content_html": "<p>Nuova versione MAJOR</p>",
        }, timeout=20)
        assert rc.status_code == 200
        new_cid = rc.json()["id"]

        r = admin_session.post(f"{API}/admin/contracts/{new_cid}/notify-major", json={
            "include_terapeuti": True, "include_pazienti": False,
        }, timeout=30)
        assert r.status_code == 200, r.text[:300]
        body = r.json()
        assert body["notified_count"] >= 1
        assert body["contract_kind"] == kind

        # Verify decline token was written
        from pymongo import MongoClient
        m = MongoClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
        dbn = os.environ.get("DB_NAME", "funzionabene_db")
        tok_doc = m[dbn].legal_decline_tokens.find_one({"contract_id": new_cid, "used": False})
        assert tok_doc, "no decline token created"
        # We can't recover the raw token from hash, so create a fresh one via a second notify
        # Instead simulate a token flow: insert a controlled token then hit endpoint
        import secrets, hashlib as hh
        raw_tok = secrets.token_urlsafe(24)
        m[dbn].legal_decline_tokens.insert_one({
            "token_hash": hh.sha256(raw_tok.encode()).hexdigest(),
            "user_id": tok_doc["user_id"],
            "contract_id": new_cid,
            "contract_kind": kind,
            "contract_version": tok_doc["contract_version"],
            "created_at": tok_doc["created_at"],
            "expires_at": tok_doc["expires_at"],
            "used": False,
        })

        # Invalid token -> 404
        r_invalid = requests.get(f"{API}/legal/decline/xxx-not-real-token", timeout=15)
        assert r_invalid.status_code == 404

        # Valid token -> 200
        r_ok = requests.get(f"{API}/legal/decline/{raw_tok}", timeout=15)
        assert r_ok.status_code == 200, r_ok.text[:300]
        assert "deactivate_at" in r_ok.json()

        # Reuse -> 410
        r_reuse = requests.get(f"{API}/legal/decline/{raw_tok}", timeout=15)
        assert r_reuse.status_code == 410

        # Cleanup: reactivate the therapist so downstream tests work
        u = m[dbn].users.find_one({"email": TERAPEUTA[0]})
        if u:
            m[dbn].users.update_one({"_id": u["_id"]}, {"$unset": {
                "pending_deactivation_reason": "", "pending_deactivation_at": "",
                "pending_deactivation_contract_kind": "", "pending_deactivation_contract_version": "",
            }, "$set": {"is_active": True}})
            m[dbn].terapisti.update_one({"user_id": str(u["_id"])},
                {"$set": {"sospeso": False}, "$unset": {"sospeso_motivo": "", "sospeso_at": ""}})
        m.close()


# ─── Tests: GDPR user rights ──────────────────────────────────────────────────

class TestGdprUserRights:
    def test_gdpr_export(self, terapeuta_session):
        r = terapeuta_session.get(f"{API}/user/gdpr/export", timeout=30)
        assert r.status_code == 200
        data = r.json()
        for key in ["generated_at", "titolare", "utente", "appuntamenti", "firme_contratti"]:
            assert key in data, f"missing key {key}"
        assert data["titolare"]["ragione_sociale"] == "BIDOC SRL"
        assert data["utente"]["email"] == TERAPEUTA[0]

    def test_gdpr_delete_wrong_confirm(self, paziente_session):
        r = paziente_session.post(f"{API}/user/gdpr/delete-account", json={
            "confirm_text": "delete", "motivazione": "test"
        }, timeout=15)
        assert r.status_code == 400

    def test_consents_get_and_update(self, paziente_session):
        # get initial
        r = paziente_session.get(f"{API}/user/consents/mine", timeout=15)
        assert r.status_code == 200
        assert "consents" in r.json() and "history" in r.json()

        # grant marketing
        r1 = paziente_session.post(f"{API}/user/consents/update", json={
            "consent_type": "marketing", "granted": True
        }, timeout=15)
        assert r1.status_code == 200
        assert r1.json()["granted"] is True

        # revoke marketing
        r2 = paziente_session.post(f"{API}/user/consents/update", json={
            "consent_type": "marketing", "granted": False
        }, timeout=15)
        assert r2.status_code == 200
        assert r2.json()["granted"] is False

        # invalid type -> 400
        r3 = paziente_session.post(f"{API}/user/consents/update", json={
            "consent_type": "bogus", "granted": True
        }, timeout=15)
        assert r3.status_code == 400

        # history should contain grant and revoke
        r4 = paziente_session.get(f"{API}/user/consents/mine", timeout=15)
        hist = r4.json()["history"]
        actions = [(h["consent_type"], h["action"]) for h in hist]
        assert ("marketing", "grant") in actions
        assert ("marketing", "revoke") in actions
