"""
Focused bug-verification plan (iteration 15):
- User bug: admin needs to suspend/reactivate a therapist instead of only deleting.
- Affected flow: admin PATCH suspension -> public therapist visibility/detail -> therapist login block/restore.
- Direct proof required: Maria Rossi can be suspended/reactivated; while suspended she is excluded from public list/matching,
  direct public detail returns 404, and login returns 403; after reactivation all return to normal.
- Edge case: an existing but never-verified therapist (documenti_verificati=false) must also return 404 from public detail.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bson import ObjectId
from pymongo import MongoClient


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "test_reports" / "bug_terapista_sospensione_iter15_api_result.json"

THERAPIST_ID = "69e5c83ca585e313092bd593"
ADMIN_EMAIL = "admin@funzionabene.it"
ADMIN_PASSWORD = "admin2026"
THERAPIST_EMAIL = "demo.terapeuta@funzionabene.it"
THERAPIST_PASSWORD = "terapeuta2026"


def read_env(path: Path) -> dict:
    values = {}
    if not path.exists():
        return values
    for raw in path.read_text().splitlines():
        raw = raw.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, val = raw.split("=", 1)
        values[key.strip()] = val.strip().strip('"').strip("'")
    return values


backend_env = read_env(ROOT / "backend" / ".env")
API_BASE = os.environ.get("TEST_API_BASE", "http://localhost:8001/api").rstrip("/")
MONGO_URL = backend_env.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = backend_env.get("DB_NAME", "funzionabene_db")


results = {
    "started_at": datetime.now(timezone.utc).isoformat(),
    "api_base": API_BASE,
    "checks": [],
    "cleanup": [],
}


def record(name: str, passed: bool, detail=None):
    item = {"name": name, "passed": bool(passed), "detail": detail}
    results["checks"].append(item)
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}: {detail}")
    if not passed:
        raise AssertionError(f"{name}: {detail}")


def body_preview(response: requests.Response):
    try:
        return response.json()
    except Exception:
        return response.text[:500]


def require_status(response: requests.Response, expected, name: str):
    expected_values = expected if isinstance(expected, (list, tuple, set)) else [expected]
    ok = response.status_code in expected_values
    record(name, ok, {"status": response.status_code, "body": body_preview(response)})
    return response


def therapist_ids_from_list(payload):
    return {str(item.get("_id")) for item in payload if isinstance(item, dict)}


def therapist_ids_from_matching(payload):
    return {str(item.get("_id")) for item in payload.get("terapisti", []) if isinstance(item, dict)}


admin_session = requests.Session()
mongo = MongoClient(MONGO_URL)
db = mongo[DB_NAME]
temp_id = None
admin_logged_in = False

try:
    maria = db.terapisti.find_one({"_id": ObjectId(THERAPIST_ID)})
    record("Maria therapist document exists", bool(maria), {"therapist_id": THERAPIST_ID})
    record(
        "Maria is document-verified before public visibility checks",
        bool(maria.get("documenti_verificati")),
        {"documenti_verificati": maria.get("documenti_verificati")},
    )

    maria_user_id = maria.get("user_id")
    record("Maria therapist has linked user_id", bool(maria_user_id), {"user_id": maria_user_id})

    # Admin login and baseline reactivation.
    admin_login = admin_session.post(
        f"{API_BASE}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=15,
    )
    require_status(admin_login, 200, "Admin login works")
    # The backend marks cookies secure/samesite=none. Python requests will not resend Secure cookies
    # over local http://localhost, so use the access token as the documented Bearer fallback.
    access_token = admin_login.cookies.get("access_token")
    record("Admin login sets access_token cookie", bool(access_token), {"cookie_names": list(admin_login.cookies.keys())})
    admin_session.headers.update({"Authorization": f"Bearer {access_token}"})
    admin_logged_in = True

    reactivate_start = admin_session.patch(
        f"{API_BASE}/admin/terapisti/{THERAPIST_ID}/sospendi",
        json={"sospeso": False},
        timeout=15,
    )
    require_status(reactivate_start, 200, "Admin can reactivate Maria via PATCH before baseline")
    record("Reactivate response says sospeso=false", reactivate_start.json().get("sospeso") is False, reactivate_start.json())

    # Baseline public/list/login behavior while active.
    public_list_active = requests.get(f"{API_BASE}/public/terapisti", timeout=15)
    require_status(public_list_active, 200, "Public therapist list works while active")
    active_ids = therapist_ids_from_list(public_list_active.json())
    record("Public therapist list includes active Maria", THERAPIST_ID in active_ids, {"count": len(active_ids)})

    public_detail_active = requests.get(f"{API_BASE}/public/terapisti/{THERAPIST_ID}", timeout=15)
    require_status(public_detail_active, 200, "Public therapist detail returns 200 for active Maria")
    active_detail = public_detail_active.json()
    record("Public active detail belongs to Maria", active_detail.get("_id") == THERAPIST_ID, active_detail)

    therapist_login_active = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": THERAPIST_EMAIL, "password": THERAPIST_PASSWORD},
        timeout=15,
    )
    require_status(therapist_login_active, 200, "Therapist login works before suspension")

    matching_active = requests.post(f"{API_BASE}/public/matching", json={}, timeout=15)
    require_status(matching_active, 200, "Public matching endpoint works while Maria active")
    results["matching_active_ids"] = sorted(therapist_ids_from_matching(matching_active.json()))

    # Edge case: existing therapist doc with documenti_verificati=false must not expose public detail.
    temp_doc = {
        "nome": "QA",
        "cognome": "Non Verificato Iter15",
        "email": "qa.nonverificato.iter15@example.test",
        "documenti_verificati": False,
        "sospeso": False,
        "created_at": datetime.now(timezone.utc),
    }
    temp_id = db.terapisti.insert_one(temp_doc).inserted_id
    results["temp_unverified_id"] = str(temp_id)
    temp_detail = requests.get(f"{API_BASE}/public/terapisti/{temp_id}", timeout=15)
    require_status(temp_detail, 404, "Public detail returns 404 for never-verified therapist")

    # Suspend Maria.
    suspend = admin_session.patch(
        f"{API_BASE}/admin/terapisti/{THERAPIST_ID}/sospendi",
        json={"sospeso": True},
        timeout=15,
    )
    require_status(suspend, 200, "Admin can suspend Maria via PATCH")
    record("Suspend response says sospeso=true", suspend.json().get("sospeso") is True, suspend.json())

    maria_suspended = db.terapisti.find_one({"_id": ObjectId(THERAPIST_ID)})
    maria_user_suspended = db.users.find_one({"_id": ObjectId(maria_user_id)})
    record(
        "Database persisted Maria sospeso=true",
        maria_suspended.get("sospeso") is True,
        {"sospeso": maria_suspended.get("sospeso")},
    )
    record(
        "Database persisted linked user is_active=false",
        maria_user_suspended.get("is_active") is False,
        {"is_active": maria_user_suspended.get("is_active")},
    )

    public_list_suspended = requests.get(f"{API_BASE}/public/terapisti", timeout=15)
    require_status(public_list_suspended, 200, "Public therapist list works while Maria suspended")
    suspended_ids = therapist_ids_from_list(public_list_suspended.json())
    record("Public therapist list excludes suspended Maria", THERAPIST_ID not in suspended_ids, {"count": len(suspended_ids)})

    public_detail_suspended = requests.get(f"{API_BASE}/public/terapisti/{THERAPIST_ID}", timeout=15)
    require_status(public_detail_suspended, 404, "Public therapist detail returns 404 for suspended Maria")

    therapist_login_suspended = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": THERAPIST_EMAIL, "password": THERAPIST_PASSWORD},
        timeout=15,
    )
    require_status(therapist_login_suspended, 403, "Therapist login is blocked while suspended")
    record(
        "Suspended login error is Account disattivato",
        body_preview(therapist_login_suspended).get("detail") == "Account disattivato",
        body_preview(therapist_login_suspended),
    )

    matching_suspended = requests.post(f"{API_BASE}/public/matching", json={}, timeout=15)
    require_status(matching_suspended, 200, "Public matching endpoint works while Maria suspended")
    suspended_matching_ids = therapist_ids_from_matching(matching_suspended.json())
    record(
        "Public matching excludes suspended Maria when returned therapists are inspected",
        THERAPIST_ID not in suspended_matching_ids,
        {"matching_ids": sorted(suspended_matching_ids)},
    )

    # Reactivate Maria and verify normal behavior is restored.
    reactivate = admin_session.patch(
        f"{API_BASE}/admin/terapisti/{THERAPIST_ID}/sospendi",
        json={"sospeso": False},
        timeout=15,
    )
    require_status(reactivate, 200, "Admin can reactivate Maria via PATCH after suspension")
    record("Final reactivate response says sospeso=false", reactivate.json().get("sospeso") is False, reactivate.json())

    maria_reactivated = db.terapisti.find_one({"_id": ObjectId(THERAPIST_ID)})
    maria_user_reactivated = db.users.find_one({"_id": ObjectId(maria_user_id)})
    record("Database persisted Maria sospeso=false", maria_reactivated.get("sospeso") is False, {"sospeso": maria_reactivated.get("sospeso")})
    record("Database persisted linked user is_active=true", maria_user_reactivated.get("is_active") is True, {"is_active": maria_user_reactivated.get("is_active")})

    public_list_reactivated = requests.get(f"{API_BASE}/public/terapisti", timeout=15)
    require_status(public_list_reactivated, 200, "Public therapist list works after reactivation")
    reactivated_ids = therapist_ids_from_list(public_list_reactivated.json())
    record("Public therapist list includes reactivated Maria", THERAPIST_ID in reactivated_ids, {"count": len(reactivated_ids)})

    public_detail_reactivated = requests.get(f"{API_BASE}/public/terapisti/{THERAPIST_ID}", timeout=15)
    require_status(public_detail_reactivated, 200, "Public therapist detail returns 200 for reactivated Maria")

    therapist_login_reactivated = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": THERAPIST_EMAIL, "password": THERAPIST_PASSWORD},
        timeout=15,
    )
    require_status(therapist_login_reactivated, 200, "Therapist login works after reactivation")

    results["verdict"] = "fixed"

except Exception as exc:
    results["verdict"] = "not_fixed"
    results["error"] = repr(exc)
    print(f"[ERROR] {exc}")
    raise
finally:
    if temp_id is not None:
        deleted = db.terapisti.delete_one({"_id": temp_id}).deleted_count
        results["cleanup"].append({"temp_unverified_deleted": deleted == 1, "id": str(temp_id)})
    # Requirement from main agent: leave Maria non-suspended and linked user active.
    try:
        if admin_logged_in:
            cleanup_resp = admin_session.patch(
                f"{API_BASE}/admin/terapisti/{THERAPIST_ID}/sospendi",
                json={"sospeso": False},
                timeout=15,
            )
            results["cleanup"].append({"api_reactivate_status": cleanup_resp.status_code, "body": body_preview(cleanup_resp)})
        db.terapisti.update_one({"_id": ObjectId(THERAPIST_ID)}, {"$set": {"sospeso": False, "sospeso_at": None, "sospeso_by": None}})
        final_doc = db.terapisti.find_one({"_id": ObjectId(THERAPIST_ID)})
        final_user_id = final_doc.get("user_id") if final_doc else None
        if final_user_id:
            db.users.update_one({"_id": ObjectId(final_user_id)}, {"$set": {"is_active": True}})
        results["cleanup"].append({"db_final_sospeso_false_user_active_true": True})
    except Exception as cleanup_exc:
        results["cleanup"].append({"cleanup_error": repr(cleanup_exc)})
    results["finished_at"] = datetime.now(timezone.utc).isoformat()
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False, default=str))
    print(f"Wrote raw API result to {REPORT_PATH}")

sys.exit(0 if results.get("verdict") == "fixed" else 1)