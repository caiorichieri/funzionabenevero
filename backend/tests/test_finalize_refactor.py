"""Tests for the refactored booking_service.finalize_confirmed_booking().

Focuses on:
  * Existence + import of the 7 new helper functions
  * Correct behavior: Daily room provisioned, reschedule/magic tokens,
    confirmation email sent, reminders scheduled, informed consent created
  * Idempotency: second call does NOT rotate tokens nor resend confirmation email
  * /appuntamenti/{id}/video-token returns 412 when paziente has no granted consent
"""
import asyncio
import os
import uuid
import inspect
from datetime import datetime, timezone, timedelta

import pytest
import requests
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "funzionabene_db")


# ─── 1. Static import / signature checks ─────────────────────────────────────
class TestHelperImports:
    def test_import_all_seven_helpers(self):
        import booking_service as bs
        for name in [
            "_ensure_informed_consent",
            "_ensure_daily_room",
            "_parse_start",
            "_ensure_reschedule_token",
            "_ensure_videocall_magic_token",
            "_build_notification_ctx",
            "_send_confirmation_and_schedule",
            "finalize_confirmed_booking",
        ]:
            assert hasattr(bs, name), f"Missing helper: {name}"
            fn = getattr(bs, name)
            assert callable(fn), f"Not callable: {name}"

    def test_async_helpers_are_coroutines(self):
        import booking_service as bs
        for name in [
            "_ensure_informed_consent",
            "_ensure_daily_room",
            "_ensure_reschedule_token",
            "_ensure_videocall_magic_token",
            "_build_notification_ctx",
            "_send_confirmation_and_schedule",
            "finalize_confirmed_booking",
        ]:
            assert inspect.iscoroutinefunction(getattr(bs, name)), f"{name} should be async"

    def test_parse_start_utility(self):
        import booking_service as bs
        # aware ISO
        dt = bs._parse_start({"data_ora": "2026-05-01T10:00:00+00:00"})
        assert dt.tzinfo is not None
        # Z suffix
        dt = bs._parse_start({"data_ora": "2026-05-01T10:00:00Z"})
        assert dt.tzinfo is not None
        # invalid → fallback to now (aware utc)
        dt = bs._parse_start({"data_ora": "not-a-date"})
        assert dt.tzinfo is not None


# ─── 2. End-to-end (direct call) — with monkeypatching side effects ──────────
@pytest.mark.asyncio
async def test_finalize_confirmed_booking_end_to_end(monkeypatch):
    """Inject a confermato appointment + call finalize_confirmed_booking twice.
    Verifies field population + idempotency without hitting Stripe."""
    import booking_service as bs
    import email_service
    import daily_service
    from routers import informed_consents as ic_mod

    # ── Stub externals ────────────────────────────────────────────────────
    email_calls = {"confirmation": 0, "reminder": 0, "consent": 0}

    async def _fake_confirmation(ctx):
        email_calls["confirmation"] += 1
        return True

    async def _fake_reminder(ctx, when):
        email_calls["reminder"] += 1
        return True

    async def _fake_send_raw(params):
        # Used by consent email + review invite
        email_calls["consent"] += 1
        return True

    async def _fake_create_room(app_id, data_ora, durata):
        return {
            "room_url": f"https://daily.co/test-{app_id}",
            "room_name": f"test-room-{app_id}",
        }

    monkeypatch.setattr(bs, "send_booking_confirmation_email", _fake_confirmation)
    monkeypatch.setattr(bs, "send_reminder_email", _fake_reminder)
    monkeypatch.setattr(bs, "create_room_for_appointment", _fake_create_room)
    monkeypatch.setattr(ic_mod, "_send_raw", _fake_send_raw)
    monkeypatch.setattr(email_service, "_send_raw", _fake_send_raw)

    # ── Seed DB ──────────────────────────────────────────────────────────
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    marker = f"TEST_finalize_{uuid.uuid4().hex[:8]}"

    p_user_id = ObjectId()
    t_user_id = ObjectId()
    paziente_id = ObjectId()
    terapista_id = ObjectId()

    try:
        await db.users.insert_one({
            "_id": p_user_id, "email": f"{marker}_paz@example.com",
            "nome": "Mario", "cognome": "Rossi", "role": "paziente",
            "telefono": "+393331112233",
        })
        await db.users.insert_one({
            "_id": t_user_id, "email": f"{marker}_ter@example.com",
            "nome": "Anna", "cognome": "Bianchi", "role": "terapeuta",
        })
        await db.pazienti.insert_one({
            "_id": paziente_id, "user_id": str(p_user_id),
            "nome": "Mario", "cognome": "Rossi", "telefono": "+393331112233",
        })
        await db.terapisti.insert_one({
            "_id": terapista_id, "user_id": str(t_user_id),
            "nome": "Anna", "cognome": "Bianchi", "prezzo_sessione": 90,
        })

        future = datetime.now(timezone.utc) + timedelta(days=3)
        appt_doc = {
            "terapeuta_id": str(terapista_id),
            "paziente_id": str(paziente_id),
            "paziente_user_id": str(p_user_id),
            "data_ora": future.isoformat().replace("+00:00", "Z"),
            "durata_minuti": 50,
            "tipologia": "individuale",
            "modalita": "online",
            "stato": "confermato",
            "created_at": datetime.now(timezone.utc),
        }
        ins = await db.appuntamenti.insert_one(appt_doc)
        appt_id = str(ins.inserted_id)

        paziente_user = {
            "_id": str(p_user_id),
            "email": f"{marker}_paz@example.com",
            "nome": "Mario",
            "cognome": "Rossi",
            "telefono": "+393331112233",
        }

        # ── First call ───────────────────────────────────────────────────
        result = await bs.finalize_confirmed_booking(appt_id, paziente_user)
        assert result is not None

        updated = await db.appuntamenti.find_one({"_id": ins.inserted_id})
        assert updated["daily_room_url"] == f"https://daily.co/test-{appt_id}"
        assert updated["daily_room_name"] == f"test-room-{appt_id}"
        assert "riprogramma_token_hash" in updated
        assert "riprogramma_token_expires" in updated
        assert "videocall_magic_hash" in updated
        assert "videocall_magic_expires" in updated
        assert updated.get("_confirmation_email_sent") is True
        assert "consenso_informato_ok" in updated

        tok_reschedule_1 = updated["riprogramma_token_hash"]
        tok_magic_1 = updated["videocall_magic_hash"]
        confirmation_calls_after_first = email_calls["confirmation"]
        assert confirmation_calls_after_first == 1, "Confirmation email should be sent exactly once"

        # Consent should exist in pending status
        consent = await db.informed_consents.find_one({
            "paziente_id": str(p_user_id),
            "terapista_id": str(terapista_id),
        })
        assert consent is not None, "Informed consent should be created"
        assert consent["status"] == "pending"

        # ── Second call (idempotency) ────────────────────────────────────
        await bs.finalize_confirmed_booking(appt_id, paziente_user)
        updated2 = await db.appuntamenti.find_one({"_id": ins.inserted_id})
        assert updated2["riprogramma_token_hash"] == tok_reschedule_1, "Reschedule token must NOT rotate"
        assert updated2["videocall_magic_hash"] == tok_magic_1, "Magic token must NOT rotate"
        assert email_calls["confirmation"] == confirmation_calls_after_first, \
            "Confirmation email must not be resent"

    finally:
        # Cleanup
        await db.users.delete_many({"email": {"$regex": f"^{marker}"}})
        await db.pazienti.delete_one({"_id": paziente_id})
        await db.terapisti.delete_one({"_id": terapista_id})
        await db.appuntamenti.delete_many({"terapeuta_id": str(terapista_id)})
        await db.informed_consents.delete_many({"terapista_id": str(terapista_id)})
        client.close()


# ─── 3. HTTP: /video-token 412 when consent not granted ─────────────────────
class TestVideoTokenConsentGate:
    def _register_paziente(self, session, email, password):
        r = session.post(f"{BASE_URL}/api/auth/register", json={
            "email": email, "password": password,
            "nome": "Test", "cognome": "Paziente", "role": "paziente",
            "consenso_privacy": True,
            "consenso_termini": True,
            "consenso_marketing": False,
        })
        return r

    def test_412_without_consent(self):
        """Direct DB setup: create confermato appt + a paziente with no consent,
        login, then hit /video-token. Should get 412."""
        marker = f"TEST_vt_{uuid.uuid4().hex[:8]}"
        email = f"{marker}@example.com"
        password = "TestPass123!"

        s = requests.Session()
        r = self._register_paziente(s, email, password)
        if r.status_code not in (200, 201):
            pytest.skip(f"Cannot register paziente: {r.status_code} {r.text[:200]}")
        otp = r.json().get("otp_dev")
        if not otp:
            pytest.skip("No otp_dev returned — cannot verify account")
        vr = s.post(f"{BASE_URL}/api/auth/verify-otp", json={"email": email, "otp_code": otp})
        if vr.status_code != 200:
            pytest.skip(f"Cannot verify OTP: {vr.status_code} {vr.text[:200]}")

        # Login (register may already log in via cookie — check)
        me = s.get(f"{BASE_URL}/api/auth/me")
        if me.status_code != 200:
            lr = s.post(f"{BASE_URL}/api/auth/login", json={
                "email": email, "password": password,
            })
            if lr.status_code != 200:
                pytest.skip(f"Cannot login: {lr.status_code}")
            me = s.get(f"{BASE_URL}/api/auth/me")
        if me.status_code != 200:
            pytest.skip("Cannot fetch /me")
        user_id = me.json().get("_id") or me.json().get("id")

        # Seed appointment directly in Mongo (skip Stripe payment flow)
        async def _seed():
            client = AsyncIOMotorClient(MONGO_URL)
            db = client[DB_NAME]
            terapista_id = ObjectId()
            paziente_id = ObjectId()
            t_user_id = ObjectId()

            await db.users.insert_one({
                "_id": t_user_id, "email": f"{marker}_ter@example.com",
                "nome": "T", "cognome": "T", "role": "terapeuta",
            })
            await db.terapisti.insert_one({
                "_id": terapista_id, "user_id": str(t_user_id),
                "nome": "T", "cognome": "T", "prezzo_sessione": 90,
            })
            # Try to find existing paziente row for this user
            existing = await db.pazienti.find_one({"user_id": user_id})
            if existing:
                pid = str(existing["_id"])
            else:
                await db.pazienti.insert_one({
                    "_id": paziente_id, "user_id": user_id,
                    "nome": "Test", "cognome": "Paziente",
                })
                pid = str(paziente_id)

            future = datetime.now(timezone.utc) + timedelta(days=3)
            ins = await db.appuntamenti.insert_one({
                "terapeuta_id": str(terapista_id),
                "paziente_id": pid,
                "paziente_user_id": user_id,
                "data_ora": future.isoformat().replace("+00:00", "Z"),
                "durata_minuti": 50,
                "stato": "confermato",
                "daily_room_name": "preexisting-room",
                "daily_room_url": "https://daily.co/pre",
                "created_at": datetime.now(timezone.utc),
            })
            client.close()
            return str(ins.inserted_id), str(terapista_id), pid, str(t_user_id)

        appt_id, terapista_id, pid, t_user_id = asyncio.new_event_loop().run_until_complete(_seed())

        try:
            r = s.post(f"{BASE_URL}/api/appuntamenti/{appt_id}/video-token")
            assert r.status_code == 412, f"Expected 412, got {r.status_code}: {r.text[:200]}"
            body = r.json()
            detail = body.get("detail", "")
            assert "Consenso Informato" in detail, f"Wrong error message: {detail}"
        finally:
            async def _cleanup():
                client = AsyncIOMotorClient(MONGO_URL)
                db = client[DB_NAME]
                await db.appuntamenti.delete_one({"_id": ObjectId(appt_id)})
                await db.terapisti.delete_one({"_id": ObjectId(terapista_id)})
                await db.users.delete_one({"_id": ObjectId(t_user_id)})
                await db.users.delete_one({"email": email})
                await db.pazienti.delete_one({"user_id": user_id})
                await db.informed_consents.delete_many({"paziente_id": user_id})
                client.close()
            asyncio.new_event_loop().run_until_complete(_cleanup())
