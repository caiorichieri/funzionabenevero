"""Send a REAL working video session link to caiorichieri@gmail.com.

Creates a test appointment 5 minutes from now, provisions a real Daily.co room,
generates a real magic token, and sends the 15-min reminder email (which is the
one that contains the "Entra nella stanza video →" button).
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from bson import ObjectId

sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")

from motor.motor_asyncio import AsyncIOMotorClient
from deps import hash_password

PATIENT_EMAIL = "caiorichieri@gmail.com"


async def ensure_patient(db):
    u = await db.users.find_one({"email": PATIENT_EMAIL})
    if not u:
        uid = ObjectId()
        await db.users.insert_one({
            "_id": uid,
            "email": PATIENT_EMAIL,
            "password_hash": hash_password("Caio2026!"),
            "nome": "Caio",
            "cognome": "Test",
            "role": "paziente",
            "is_active": True, "is_verified": True,
            "approval_status": "approvato",
            "telefono_verificato": True,
            "telefono": "+393331234567",
        })
        u = await db.users.find_one({"_id": uid})
    pid = ObjectId()
    await db.pazienti.update_one(
        {"user_id": str(u["_id"])},
        {"$setOnInsert": {"_id": pid},
         "$set": {
             "user_id": str(u["_id"]),
             "nome": "Caio", "cognome": "Test",
             "codice_fiscale": "TSTCAI85A01F205X",
             "indirizzo": "Via Test 5",
             "cap": "20100",
             "comune": "Milano",
             "provincia": "MI",
             "dati_fiscali_completi": True,
             "email": PATIENT_EMAIL,
             "telefono": "+393331234567",
        }},
        upsert=True,
    )
    return await db.pazienti.find_one({"user_id": str(u["_id"])}), u


async def get_first_active_therapist(db):
    """Fetch first approved & non-suspended therapist that also has a user record."""
    async for t in db.terapisti.find({"approval_status": "approvato", "sospeso": {"$ne": True}}):
        try:
            u = await db.users.find_one({"_id": ObjectId(t["user_id"])})
        except Exception:
            u = None
        if u and u.get("is_active"):
            return t, u
    return None, None


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    print("→ 1/4 finding first active therapist…")
    t, t_user = await get_first_active_therapist(db)
    if not t:
        print("❌ No active therapist found. Aborting.")
        return
    print(f"    ✓ therapist: Dr. {t['nome']} {t['cognome']} ({t_user['email']})")

    print("→ 2/4 ensuring test patient Caio Test…")
    p, p_user = await ensure_patient(db)
    print(f"    ✓ patient: {p['nome']} {p['cognome']} ({p_user['email']})")

    # 3. Create appointment 5 min from now (UTC ISO)
    start_utc = datetime.now(timezone.utc) + timedelta(minutes=5)
    data_ora_iso = start_utc.replace(second=0, microsecond=0).isoformat()
    print(f"→ 3/4 creating appointment at {data_ora_iso} (UTC, ~5 min from now)…")

    appt_id = ObjectId()
    await db.appuntamenti.insert_one({
        "_id": appt_id,
        "paziente_id": str(p["_id"]),
        "paziente_user_id": str(p_user["_id"]),
        "terapeuta_id": str(t["_id"]),
        "terapeuta_user_id": str(t["user_id"]),
        "data_ora": data_ora_iso,
        "durata_minuti": t.get("durata_sessione", 50),
        "prezzo": t.get("prezzo_sessione", 80),
        "stato": "confermato",
        "paid_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "_test_session": True,
    })
    print(f"    ✓ appointment_id: {appt_id}")

    # 4. Provision Daily.co room + generate magic token + send 15-min reminder email
    print("→ 4/4 provisioning Daily.co room + magic token + sending email…")
    from booking_service import (
        _ensure_daily_room, _ensure_videocall_magic_token,
        _ensure_reschedule_token, _build_notification_ctx,
    )
    from email_service import send_reminder_email

    appt = await db.appuntamenti.find_one({"_id": appt_id})
    await _ensure_daily_room(str(appt_id), appt)
    raw_reschedule = await _ensure_reschedule_token(str(appt_id), appt)
    raw_magic = await _ensure_videocall_magic_token(str(appt_id), appt)

    # Reload with newly-persisted fields
    appt = await db.appuntamenti.find_one({"_id": appt_id})
    p_user_ready = {**p_user, "_id": str(p_user["_id"])}
    ctx = await _build_notification_ctx(str(appt_id), appt, p_user_ready, raw_reschedule, raw_magic)

    # Force paziente-only send: strip therapist so the therapist doesn't get spammed
    ctx["terapista_email"] = None

    print(f"    videocall_url: {ctx.get('videocall_url')}")
    print(f"    daily room:    {ctx.get('room_url')}")

    ok = await send_reminder_email(ctx, "15-min")
    print(f"    email sent: {ok}")

    print(f"\n🎉 DONE — check inbox for {PATIENT_EMAIL}")
    print(f"   Subject: '🎥 La tua seduta inizia tra 15 minuti — entra qui'")
    print(f"   Click the button 'Entra nella stanza video →' — it opens the real Daily.co room.")
    print(f"\n   Appointment starts at: {data_ora_iso} (UTC)")
    print(f"   Magic link valid until: session end + 15 min")


if __name__ == "__main__":
    asyncio.run(main())
