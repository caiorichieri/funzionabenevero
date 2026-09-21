"""Fire the 15-min reminder email manually so caio receives it."""
import asyncio, os, sys
sys.path.insert(0, "/app/backend")
from dotenv import load_dotenv
load_dotenv("/app/backend/.env")
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId

async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    appt = await db.appuntamenti.find_one({"paziente_user_id": {"$exists": True}}, sort=[("created_at", -1)])
    if not appt:
        print("No appointment")
        return
    print(f"Appt: {appt['_id']} at {appt['data_ora']} stato={appt['stato']}")

    # Build context
    p_user = await db.users.find_one({"_id": ObjectId(appt["paziente_user_id"])})
    from booking_service import _build_notification_ctx, _token_digest
    import secrets, hashlib, datetime as dt

    # Generate a magic token for videocall link
    raw_magic = secrets.token_urlsafe(24)
    await db.appuntamenti.update_one(
        {"_id": appt["_id"]},
        {"$set": {
            "magic_token_digest": _token_digest(raw_magic),
            "magic_token_expires_at": dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=2),
            "daily_room_url": "https://funzionabene.daily.co/test-e2e-demo",
        }},
    )
    appt = await db.appuntamenti.find_one({"_id": appt["_id"]})

    p_user["_id"] = str(p_user["_id"])
    ctx = await _build_notification_ctx(str(appt["_id"]), appt, p_user, None, raw_magic)
    print(f"Ctx built. Firing reminder 15-min…")

    from email_service import send_reminder_email
    ok = await send_reminder_email(ctx, "15-min")
    print(f"Reminder sent: {ok}")

asyncio.run(main())
