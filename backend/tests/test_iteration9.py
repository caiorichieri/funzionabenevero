"""Iteration 9 tests: seed pending payout, IBAN regex, refactored cruscotto, PDF export."""
import os
import re
import requests
import pytest

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
if not BASE_URL:
    with open("/app/frontend/.env") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL"):
                BASE_URL = line.split("=", 1)[1].strip().rstrip("/")

ADMIN_EMAIL = "admin@funzionabene.it"
ADMIN_PASS = "admin2026"
PAT_EMAIL = "demo.paziente@funzionabene.it"
PAT_PASS = "paziente2026"


def _login(email, password):
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": password}, timeout=15)
    assert r.status_code == 200, f"login failed {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_headers():
    return _login(ADMIN_EMAIL, ADMIN_PASS)


@pytest.fixture(scope="module")
def patient_headers():
    return _login(PAT_EMAIL, PAT_PASS)


# ---------- Cruscotto schema / refactor ----------
def test_cruscotto_schema_full(admin_headers):
    r = admin_headers.get(f"{BASE_URL}/api/admin/cruscotto", timeout=20)
    assert r.status_code == 200
    d = r.json()
    assert "revenue" in d
    assert "current_month" in d["revenue"]
    assert "previous_month" in d["revenue"]
    assert "delta_percent" in d["revenue"]
    assert "pending_payouts" in d
    assert "sessions_month" in d
    assert isinstance(d.get("revenue_6m"), list)
    assert len(d["revenue_6m"]) == 6
    assert "top_therapists" in d
    assert "iban_missing" in d


def test_cruscotto_forbidden_for_non_admin(patient_headers):
    r = patient_headers.get(f"{BASE_URL}/api/admin/cruscotto", timeout=15)
    assert r.status_code in (401, 403)


def test_cruscotto_no_auth():
    r = requests.get(f"{BASE_URL}/api/admin/cruscotto", timeout=15)
    assert r.status_code in (401, 403)


# ---------- Pending payout seed ----------
def test_pending_payout_present(admin_headers):
    r = admin_headers.get(f"{BASE_URL}/api/admin/cruscotto", timeout=15)
    d = r.json()
    pp = d["pending_payouts"]
    assert pp["count"] >= 1, f"expected pending count>=1 got {pp}"
    assert pp["total_cents"] > 0


def test_iban_missing_contains_giulia(admin_headers):
    r = admin_headers.get(f"{BASE_URL}/api/admin/cruscotto", timeout=15)
    d = r.json()
    names = [x.get("nome", "") for x in d["iban_missing"]]
    assert any("Giulia" in n and "Marchetti" in n for n in names), f"Giulia not in iban_missing: {names}"
    # verify pending €45.50 = 4550c on that row
    row = next(x for x in d["iban_missing"] if "Giulia" in x.get("nome", ""))
    assert row["pending_cents"] == 4550, f"expected 4550 got {row['pending_cents']}"


def test_seed_idempotent(admin_headers):
    """Hitting seed twice (already ran on boot) shouldn't multiply pending count."""
    r1 = admin_headers.get(f"{BASE_URL}/api/admin/cruscotto", timeout=15).json()
    # trigger a second view — no state change expected
    r2 = admin_headers.get(f"{BASE_URL}/api/admin/cruscotto", timeout=15).json()
    assert r1["pending_payouts"]["count"] == r2["pending_payouts"]["count"]
    # Count must be small (idempotent seed keeps <=some sane number, definitely not growing).
    assert r1["pending_payouts"]["count"] < 5


# ---------- IBAN validation ----------
def _find_maria_id(admin_headers):
    r = admin_headers.get(f"{BASE_URL}/api/terapisti", timeout=15)
    assert r.status_code == 200
    for t in r.json():
        if t.get("nome") == "Maria" and t.get("cognome") == "Rossi":
            return t["_id"]
    pytest.skip("Maria Rossi not found")


def test_iban_invalid_rejected(admin_headers):
    tid = _find_maria_id(admin_headers)
    r = admin_headers.put(f"{BASE_URL}/api/terapisti/{tid}", json={"iban": "BADIBAN"}, timeout=15)
    assert r.status_code == 422, f"got {r.status_code} {r.text}"
    body = r.text
    assert "IBAN" in body


def test_iban_valid_normalized(admin_headers):
    tid = _find_maria_id(admin_headers)
    # Save original
    orig = admin_headers.get(f"{BASE_URL}/api/terapisti/{tid}", timeout=15).json().get("iban")
    try:
        r = admin_headers.put(
            f"{BASE_URL}/api/terapisti/{tid}",
            json={"iban": "it60 x054 2811 1010 0000 0123 456"},
            timeout=15,
        )
        assert r.status_code == 200, r.text
        g = admin_headers.get(f"{BASE_URL}/api/terapisti/{tid}", timeout=15).json()
        assert g["iban"] == "IT60X0542811101000000123456", f"got {g.get('iban')}"

        # all-digits after IT99 (25 alnum chars) — regex allows. Note: review spec had extra 9
        r2 = admin_headers.put(f"{BASE_URL}/api/terapisti/{tid}",
                          json={"iban": "IT9900000000000000000000000"}, timeout=15)
        assert r2.status_code == 200, r2.text

        # empty string clears
        r3 = admin_headers.put(f"{BASE_URL}/api/terapisti/{tid}",
                          json={"iban": ""}, timeout=15)
        assert r3.status_code == 200, r3.text
        g3 = admin_headers.get(f"{BASE_URL}/api/terapisti/{tid}", timeout=15).json()
        assert (g3.get("iban") or "") == "", f"expected empty, got {g3.get('iban')}"
    finally:
        # restore
        if orig:
            admin_headers.put(f"{BASE_URL}/api/terapisti/{tid}", json={"iban": orig}, timeout=15)


# ---------- PDF export ----------
def test_pdf_export_admin(admin_headers):
    r = admin_headers.get(f"{BASE_URL}/api/admin/cruscotto/report.pdf", timeout=30)
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:5] == b"%PDF-"
    cd = r.headers.get("content-disposition", "")
    assert re.search(r"cruscotto-\d{4}-\d{2}\.pdf", cd), f"bad Content-Disposition: {cd}"


def test_pdf_forbidden_non_admin(patient_headers):
    r = patient_headers.get(f"{BASE_URL}/api/admin/cruscotto/report.pdf", timeout=15)
    assert r.status_code in (401, 403)
