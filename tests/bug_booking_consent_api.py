#!/usr/bin/env python3
"""Focused backend/API checks for BookingSheet registration consent bug.

This script intentionally targets only the reported flow:
anonymous checkout registration must send/accept both mandatory consents
(privacy + terms) and return otp_dev in this preview environment.
"""
import json
import os
import time
from pathlib import Path

import requests
from dotenv import dotenv_values
from pymongo import MongoClient


APP = Path("/app")
FRONTEND_ENV = dotenv_values(APP / "frontend" / ".env")
BACKEND_ENV = dotenv_values(APP / "backend" / ".env")
BASE_URL = (FRONTEND_ENV.get("REACT_APP_BACKEND_URL") or "http://localhost:8001").rstrip("/")
API = f"{BASE_URL}/api"
DB_NAME = BACKEND_ENV.get("DB_NAME", "funzionabene_db")
MONGO_URL = BACKEND_ENV.get("MONGO_URL", "mongodb://localhost:27017").strip('"')
OUT = APP / "test_reports" / "booking_consent_api_result.json"


def cleanup_user(db, email: str):
    user = db.users.find_one({"email": email}, {"_id": 1})
    if user:
        uid = str(user["_id"])
        db.pazienti.delete_many({"user_id": uid})
        db.consent_history.delete_many({"user_id": uid})
        db.users.delete_one({"_id": user["_id"]})


def find_public_therapist_with_slot():
    r = requests.get(f"{API}/public/terapisti", timeout=20)
    r.raise_for_status()
    therapists = r.json()
    for t in therapists:
        tid = t["_id"]
        slots_r = requests.get(f"{API}/terapisti/{tid}/slots?settimane=2", timeout=20)
        if slots_r.status_code != 200:
            continue
        slots = slots_r.json().get("slots", [])
        first = next((s for s in slots if s.get("disponibile")), None)
        if first:
            return {"therapist": t, "slot": first}
    return {"therapist_count": len(therapists), "slot": None}


def main():
    client = MongoClient(MONGO_URL)
    db = client[DB_NAME]
    stamp = int(time.time())
    # Pydantic EmailStr rejects reserved test domains; use the app domain with a QA prefix.
    bad_email = f"qa.booking.no.terms.{stamp}@funzionabene.it"
    ok_email = f"qa.booking.consents.{stamp}@funzionabene.it"
    password = "Password123!"
    result = {
        "base_url": BASE_URL,
        "api": API,
        "target": find_public_therapist_with_slot(),
        "checks": [],
    }

    for email in (bad_email, ok_email):
        cleanup_user(db, email)

    # Backend should still reject the old/buggy payload (privacy only, no terms).
    old_payload = {
        "email": bad_email,
        "password": password,
        "nome": "QA",
        "cognome": "NoTerms",
        "role": "paziente",
        "consenso_privacy": True,
    }
    old_r = requests.post(f"{API}/auth/register", json=old_payload, timeout=20)
    result["checks"].append({
        "name": "old_payload_without_consenso_termini_rejected",
        "status_code": old_r.status_code,
        "body": old_r.json() if old_r.headers.get("content-type", "").startswith("application/json") else old_r.text,
        "passed": old_r.status_code == 400 and "consensi obbligatori" in old_r.text,
    })

    # Fixed payload expected from BookingSheet: both mandatory consents true.
    fixed_payload = {
        "email": ok_email,
        "password": password,
        "nome": "QA",
        "cognome": "Booking",
        "role": "paziente",
        "consenso_privacy": True,
        "consenso_termini": True,
    }
    ok_r = requests.post(f"{API}/auth/register", json=fixed_payload, timeout=20)
    ok_body = ok_r.json() if ok_r.headers.get("content-type", "").startswith("application/json") else {"text": ok_r.text}
    user = db.users.find_one({"email": ok_email}, {"_id": 1, "email": 1, "consenso_privacy": 1, "consents": 1, "otp_code": 1})
    persisted = None
    if user:
        persisted = {
            "email": user.get("email"),
            "consenso_privacy": user.get("consenso_privacy"),
            "consents_privacy_accettata": (user.get("consents") or {}).get("privacy_accettata"),
            "consents_termini_accettati": (user.get("consents") or {}).get("termini_accettati"),
            "otp_present": bool(user.get("otp_code")),
        }
    result["checks"].append({
        "name": "fixed_payload_with_both_consents_registers_and_returns_otp_dev",
        "status_code": ok_r.status_code,
        "body": ok_body,
        "persisted": persisted,
        "passed": (
            ok_r.status_code == 200
            and bool(ok_body.get("otp_dev"))
            and persisted is not None
            and persisted.get("consents_privacy_accettata") is True
            and persisted.get("consents_termini_accettati") is True
        ),
    })

    result["passed"] = all(c["passed"] for c in result["checks"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()