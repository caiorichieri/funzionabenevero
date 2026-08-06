"""
Temporary seed toggle for iteration 21 UI-only verification.

setup:
  - backs up Luca's current future active appointments and Maria's therapist doc
  - temporarily marks Luca's future active appointments as annullato so the
    PazienteHome renders MioTerapeutaCard instead of NextSessionCard
  - temporarily adds one future calendar slot for Maria so the Prenota button is
    rendered and /terapeuti/:id?prenota=1 can auto-open BookingSheet

restore:
  - restores the exact backed-up Mongo documents
"""

import argparse
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bson import ObjectId, json_util
from pymongo import MongoClient


BACKUP_PATH = Path("/app/test_reports/iteration21_seed_backup.json")
THERAPIST_ID = "69e5c83ca585e313092bd593"
LUCA_EMAIL = "demo.paziente@funzionabene.it"


def therapist_query():
    try:
        return {"_id": ObjectId(THERAPIST_ID)}
    except Exception:
        return {"_id": THERAPIST_ID}


def env_value(path: str, key: str, default: str = "") -> str:
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k == key:
            return v.strip().strip('"').strip("'")
    return os.environ.get(key, default)


def db():
    mongo_url = env_value("/app/backend/.env", "MONGO_URL", "mongodb://localhost:27017")
    db_name = env_value("/app/backend/.env", "DB_NAME", "funzionabene_db")
    return MongoClient(mongo_url)[db_name]


def parse_dt(value: str):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def setup():
    database = db()
    luca = database.users.find_one({"email": LUCA_EMAIL})
    if not luca:
        raise RuntimeError("Luca user not found")

    now = datetime.now(timezone.utc)
    appts = list(database.appuntamenti.find({
        "paziente_user_id": str(luca["_id"]),
        "stato": {"$nin": ["annullato", "cancellato"]},
    }))
    future_active = []
    for appt in appts:
        dt = parse_dt(str(appt.get("data_ora", "")))
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if dt and dt >= now:
            future_active.append(appt)

    therapist = database.terapisti.find_one(therapist_query()) or database.terapisti.find_one({"_id": THERAPIST_ID})
    if not therapist:
        raise RuntimeError("Maria therapist doc not found")

    backup = {"future_active_appointments": future_active, "therapist": therapist}
    BACKUP_PATH.write_text(json_util.dumps(backup, indent=2), encoding="utf-8")

    for appt in future_active:
        database.appuntamenti.update_one(
            {"_id": appt["_id"]},
            {"$set": {"stato": "annullato", "_iteration21_temp_cancelled": True}},
        )

    slot_dt = now + timedelta(days=3)
    date_key = slot_dt.strftime("%Y-%m-%d")
    time_value = "10:00"
    cal = dict(therapist.get("disponibilita_calendario") or {})
    day_slots = set(cal.get(date_key) or [])
    day_slots.add(time_value)
    cal[date_key] = sorted(day_slots)
    database.terapisti.update_one(
        {"_id": therapist["_id"]},
        {"$set": {
            "disponibilita_calendario": cal,
            "calendario_bozza": False,
            "_iteration21_temp_slot": {"date": date_key, "time": time_value},
        }},
    )
    print(json_util.dumps({
        "setup": "ok",
        "cancelled_future_active_appointments": [a["_id"] for a in future_active],
        "temp_slot": {"date": date_key, "time": time_value},
        "backup_path": str(BACKUP_PATH),
    }, indent=2))


def restore():
    if not BACKUP_PATH.exists():
        raise RuntimeError(f"Backup missing: {BACKUP_PATH}")
    database = db()
    backup = json_util.loads(BACKUP_PATH.read_text(encoding="utf-8"))
    therapist = backup["therapist"]
    database.terapisti.replace_one({"_id": therapist["_id"]}, therapist, upsert=True)
    for appt in backup["future_active_appointments"]:
        database.appuntamenti.replace_one({"_id": appt["_id"]}, appt, upsert=True)
    print(json_util.dumps({
        "restore": "ok",
        "restored_future_active_appointments": [a["_id"] for a in backup["future_active_appointments"]],
        "restored_therapist": therapist["_id"],
    }, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["setup", "restore"])
    args = parser.parse_args()
    if args.mode == "setup":
        setup()
    else:
        restore()