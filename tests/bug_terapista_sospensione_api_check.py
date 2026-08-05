#!/usr/bin/env python3
"""Focused API/integration verification for admin therapist suspension/reactivation."""

import json
import os
import sys
import time
from pathlib import Path

import requests
from bson import ObjectId
from pymongo import MongoClient


ROOT = Path("/app")
OUT = ROOT / "test_reports" / "bug_terapista_sospensione_api_result.json"
ADMIN_EMAIL = "admin@funzionabene.it"
ADMIN_PASSWORD = "admin2026"
THERAPIST_EMAIL = "demo.terapeuta@funzionabene.it"
THERAPIST_PASSWORD = "terapeuta2026"
THERAPIST_ID_HINT = "69e5c83ca585e313092bd593"
MISSING_VALID_OBJECT_ID = "64f000000000000000000000"


def parse_env(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        data[key.strip()] = val.strip().strip('"').strip("'")
    return data


frontend_env = parse_env(ROOT / "frontend" / ".env")
backend_env = parse_env(ROOT / "backend" / ".env")
BASE = os.environ.get("API_BASE") or f"{frontend_env.get('REACT_APP_BACKEND_URL', 'http://localhost:8001').rstrip('/')}/api"
MONGO_URL = backend_env.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = backend_env.get("DB_NAME", "funzionabene_db")


results = {
    "api_base": BASE,
    "checks": [],
    "failures": [],
    "observations": [],
    "therapist_id": None,
    "cleanup_done": False,
}


def record(name: str, ok: bool, detail=None):
    entry = {"name": name, "ok": bool(ok), "detail": detail}
    results["checks"].append(entry)
    print(("PASS" if ok else "FAIL") + f": {name} :: {detail}")
    if not ok:
        results["failures"].append(entry)


def request_json(session, method, url, **kwargs):
    resp = session.request(method, url, timeout=30, **kwargs)
    try:
        body = resp.json()
    except Exception:
        body = resp.text[:500]
    return resp, body


def login(email: str, password: str):
    s = requests.Session()
    resp, body = request_json(s, "POST", f"{BASE}/auth/login", json={"email": email, "password": password})
    return s, resp, body


client = MongoClient(MONGO_URL)
db = client[DB_NAME]
original_t = None
original_u = None
therapist_oid = None
user_oid = None
unique_problem = f"qa-sospensione-{int(time.time())}"


try:
    user_doc = db.users.find_one({"email": THERAPIST_EMAIL})
    if not user_doc:
        raise AssertionError(f"Therapist user not found for {THERAPIST_EMAIL}")
    user_oid = user_doc["_id"]
    t_doc = db.terapisti.find_one({"_id": ObjectId(THERAPIST_ID_HINT)}) or db.terapisti.find_one({"user_id": str(user_oid)})
    if not t_doc:
        raise AssertionError("Maria Rossi therapist profile not found")
    therapist_oid = t_doc["_id"]
    therapist_id = str(therapist_oid)
    results["therapist_id"] = therapist_id
    original_t = dict(t_doc)
    original_u = dict(user_doc)

    # Seed only fields needed to make public list/matching deterministic; restored in finally.
    db.terapisti.update_one(
        {"_id": therapist_oid},
        {"$set": {
            "documenti_verificati": True,
            "specializzazioni": [unique_problem],
            "genere": "F",
            "sospeso": False,
            "sospeso_at": None,
            "sospeso_by": None,
        }},
    )
    db.users.update_one({"_id": user_oid}, {"$set": {"is_active": True}})

    admin_s, resp, body = login(ADMIN_EMAIL, ADMIN_PASSWORD)
    record("admin login succeeds", resp.status_code == 200 and body.get("role") == "admin", {"status": resp.status_code, "body": body})

    resp, body = request_json(admin_s, "GET", f"{BASE}/auth/me")
    record("admin session cookie works on protected route", resp.status_code == 200 and body.get("role") == "admin", {"status": resp.status_code, "body": body})

    therapist_s, resp, body = login(THERAPIST_EMAIL, THERAPIST_PASSWORD)
    record("therapist can login before suspension", resp.status_code == 200 and body.get("role") == "terapeuta", {"status": resp.status_code, "body": body})

    resp, body = request_json(admin_s, "GET", f"{BASE}/terapisti")
    maria_admin = next((t for t in body if t.get("_id") == therapist_id), None) if isinstance(body, list) else None
    record("admin terapisti list contains Maria with sospeso false baseline", resp.status_code == 200 and maria_admin and maria_admin.get("sospeso") is not True, {"status": resp.status_code, "maria": maria_admin})

    resp, body = request_json(requests.Session(), "GET", f"{BASE}/public/terapisti")
    public_before = any(t.get("_id") == therapist_id for t in body) if isinstance(body, list) else False
    record("public therapist list contains active verified Maria before suspension", resp.status_code == 200 and public_before, {"status": resp.status_code, "count": len(body) if isinstance(body, list) else None})

    matching_payload = {"problemi": [unique_problem], "preferenza_terapeuta": "Preferisco una donna"}
    resp, body = request_json(requests.Session(), "POST", f"{BASE}/public/matching", json=matching_payload)
    matching_before = any(t.get("_id") == therapist_id for t in body.get("terapisti", [])) if isinstance(body, dict) else False
    record("public matching contains Maria before suspension", resp.status_code == 200 and matching_before, {"status": resp.status_code, "body": body})

    resp, body = request_json(therapist_s, "PATCH", f"{BASE}/admin/terapisti/{therapist_id}/sospendi", json={"sospeso": True})
    record("non-admin therapist cannot call suspension endpoint", resp.status_code == 403, {"status": resp.status_code, "body": body})

    resp, body = request_json(admin_s, "PATCH", f"{BASE}/admin/terapisti/{MISSING_VALID_OBJECT_ID}/sospendi", json={"sospeso": True})
    record("missing therapist returns 404", resp.status_code == 404, {"status": resp.status_code, "body": body})

    resp, body = request_json(admin_s, "PATCH", f"{BASE}/admin/terapisti/{therapist_id}/sospendi", json={"sospeso": True})
    record("admin can suspend Maria", resp.status_code == 200 and body.get("sospeso") is True, {"status": resp.status_code, "body": body})

    suspended_t = db.terapisti.find_one({"_id": therapist_oid})
    suspended_u = db.users.find_one({"_id": user_oid})
    record("suspension persisted to terapisti.sospeso and users.is_active=false", suspended_t.get("sospeso") is True and suspended_u.get("is_active") is False, {"sospeso": suspended_t.get("sospeso"), "is_active": suspended_u.get("is_active")})

    suspended_login_s, resp, body = login(THERAPIST_EMAIL, THERAPIST_PASSWORD)
    record("suspended therapist login is blocked with Account disattivato", resp.status_code == 403 and body.get("detail") == "Account disattivato", {"status": resp.status_code, "body": body, "cookies": suspended_login_s.cookies.get_dict()})

    resp, body = request_json(requests.Session(), "GET", f"{BASE}/public/terapisti")
    public_after_suspend = any(t.get("_id") == therapist_id for t in body) if isinstance(body, list) else True
    record("public therapist list hides Maria while suspended", resp.status_code == 200 and not public_after_suspend, {"status": resp.status_code, "count": len(body) if isinstance(body, list) else None})

    resp, body = request_json(requests.Session(), "POST", f"{BASE}/public/matching", json=matching_payload)
    matching_after_suspend = any(t.get("_id") == therapist_id for t in body.get("terapisti", [])) if isinstance(body, dict) else True
    record("public matching hides Maria while suspended", resp.status_code == 200 and not matching_after_suspend, {"status": resp.status_code, "body": body})

    resp, body = request_json(requests.Session(), "GET", f"{BASE}/public/terapisti/{therapist_id}")
    results["observations"].append({"name": "direct public therapist detail while suspended", "status": resp.status_code, "body_contains_sospeso": isinstance(body, dict) and body.get("sospeso") is True})
    print(f"OBSERVE: direct public therapist detail while suspended :: status={resp.status_code}, body_contains_sospeso={isinstance(body, dict) and body.get('sospeso') is True}")

    resp, body = request_json(admin_s, "GET", f"{BASE}/terapisti")
    maria_suspended_admin = next((t for t in body if t.get("_id") == therapist_id), None) if isinstance(body, list) else None
    record("admin terapisti list shows Maria with sospeso true after suspension", resp.status_code == 200 and maria_suspended_admin and maria_suspended_admin.get("sospeso") is True, {"status": resp.status_code, "maria": maria_suspended_admin})

    resp, body = request_json(admin_s, "PATCH", f"{BASE}/admin/terapisti/{therapist_id}/sospendi", json={"sospeso": False})
    record("admin can reactivate Maria", resp.status_code == 200 and body.get("sospeso") is False, {"status": resp.status_code, "body": body})

    active_t = db.terapisti.find_one({"_id": therapist_oid})
    active_u = db.users.find_one({"_id": user_oid})
    record("reactivation persisted to terapisti.sospeso=false and users.is_active=true", active_t.get("sospeso") is False and active_u.get("is_active") is True, {"sospeso": active_t.get("sospeso"), "is_active": active_u.get("is_active")})

    therapist_s2, resp, body = login(THERAPIST_EMAIL, THERAPIST_PASSWORD)
    record("therapist can login again after reactivation", resp.status_code == 200 and body.get("role") == "terapeuta", {"status": resp.status_code, "body": body})

    resp, body = request_json(requests.Session(), "GET", f"{BASE}/public/terapisti")
    public_after_reactivate = any(t.get("_id") == therapist_id for t in body) if isinstance(body, list) else False
    record("public therapist list shows Maria again after reactivation", resp.status_code == 200 and public_after_reactivate, {"status": resp.status_code, "count": len(body) if isinstance(body, list) else None})

    resp, body = request_json(requests.Session(), "POST", f"{BASE}/public/matching", json=matching_payload)
    matching_after_reactivate = any(t.get("_id") == therapist_id for t in body.get("terapisti", [])) if isinstance(body, dict) else False
    record("public matching shows Maria again after reactivation", resp.status_code == 200 and matching_after_reactivate, {"status": resp.status_code, "body": body})

except Exception as exc:
    record("test script exception", False, repr(exc))
finally:
    if therapist_oid and user_oid and original_t and original_u:
        restore_t_set = {
            "documenti_verificati": original_t.get("documenti_verificati"),
            "specializzazioni": original_t.get("specializzazioni", []),
            "genere": original_t.get("genere"),
            # Per request: leave DB clean with Maria non-suspended and able to login.
            "sospeso": False,
            "sospeso_at": None,
            "sospeso_by": None,
        }
        db.terapisti.update_one({"_id": therapist_oid}, {"$set": restore_t_set})
        db.users.update_one({"_id": user_oid}, {"$set": {"is_active": True}})
        results["cleanup_done"] = True
        results["cleanup_state"] = {"sospeso": False, "is_active": True, "restored_profile_fields": ["documenti_verificati", "specializzazioni", "genere"]}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    results["overall_ok"] = len(results["failures"]) == 0
    OUT.write_text(json.dumps(results, indent=2, default=str))
    print(f"Wrote {OUT}")
    sys.exit(0 if results["overall_ok"] else 1)