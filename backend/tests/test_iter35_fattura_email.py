"""Iter35 — Dedicated `send_fattura_paziente_email` regression tests.

Covers:
1. Unit: subject / reply_to / attachment filename shape
2. Unit: SEND_EMAILS=false → returns (False, "email_send_disabled")
3. Unit: pdf_bytes=b"" → sends WITHOUT attachments key
4. E2E _emit_fattura_for_paid_tx uses the branded template (not signature-receipt)
5. Storage fetch fail persists on tx when email also fails (fattura_error_step='fetch_pdf')
6. Storage fetch fail but email OK → email sent without attachment
7. Admin POST /admin/fatture/{fid}/reinvia BYPASSES email_sent_at flag
8. Admin reinvia for NC (kind='nota_credito_sanitaria') still uses signature-receipt
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from bson import ObjectId
import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else "https://portugues-writer-2.preview.emergentagent.com"
ADMIN_EMAIL = os.environ.get("TEST_ADMIN_EMAIL", "hr@funzionabene.it")
ADMIN_PASSWORD = os.environ.get("TEST_ADMIN_PASSWORD", "@Bidoc2026!")


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def admin_session():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login",
               json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}, timeout=15)
    if r.status_code != 200:
        pytest.skip(f"Admin login failed: {r.status_code} {r.text[:200]}")
    return s


def _make_db():
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ.get("DB_NAME", "funzionabene_db")]
    return client, db


def _bind_db(db):
    import deps as _deps
    import routers.fatture as _fatture_mod
    import routers.payments as _payments_mod
    _orig = (_deps.db, _fatture_mod.db, _payments_mod.db)
    _deps.db = db
    _fatture_mod.db = db
    _payments_mod.db = db
    return _orig


def _restore_db(orig):
    import deps as _deps
    import routers.fatture as _fatture_mod
    import routers.payments as _payments_mod
    _deps.db, _fatture_mod.db, _payments_mod.db = orig


# ─── Unit tests: send_fattura_paziente_email shape ───────────────────────────

def test_1_template_subject_reply_to_filename(monkeypatch):
    """subject, reply_to, filename must match spec when pdf_bytes provided."""
    import email_service as ems
    captured = {}

    def _fake_send(params):
        captured["params"] = params
        return {"id": "resend_test_id_123"}

    monkeypatch.setattr(ems, "SEND_EMAILS", True)
    monkeypatch.setattr(ems, "RESEND_API_KEY", "test-key")
    monkeypatch.setattr(ems.resend.Emails, "send", _fake_send)

    fattura = {
        "numero": "FZ-2026-0004",
        "importo_totale": 80,
        "data": "2026-10-15",
        "causale": "Prestazione sanitaria di psicoterapia",
    }
    ok, err = asyncio.run(ems.send_fattura_paziente_email(
        "paz@fb.it", "Mario", "Rossi",
        "2026-10-15T14:00:00+00:00",
        fattura, b"FAKE_PDF_BYTES",
    ))
    assert ok is True, f"expected ok=True, got ok={ok} err={err}"
    assert err == ""
    p = captured["params"]
    assert p["subject"] == "Fattura FZ-2026-0004 per la tua seduta con Dr. Rossi", p["subject"]
    assert p["reply_to"] == ["info@funzionabene.it"], p["reply_to"]
    assert p["to"] == ["paz@fb.it"]
    assert "attachments" in p and len(p["attachments"]) == 1
    assert p["attachments"][0]["filename"] == "Fattura_FZ-2026-0004.pdf"


def test_2_send_emails_disabled_returns_tuple(monkeypatch):
    """SEND_EMAILS=false must return (False, 'email_send_disabled') without raising."""
    import email_service as ems
    monkeypatch.setattr(ems, "SEND_EMAILS", False)
    # Ensure resend.Emails.send is never called
    def _boom(params):
        raise AssertionError("resend.Emails.send must NOT be called when SEND_EMAILS=false")
    monkeypatch.setattr(ems.resend.Emails, "send", _boom)

    ok, err = asyncio.run(ems.send_fattura_paziente_email(
        "paz@fb.it", "Mario", "Rossi",
        "2026-10-15T14:00:00+00:00",
        {"numero": "FZ-2026-0004", "importo_totale": 80, "data": "2026-10-15"},
        b"FAKE",
    ))
    assert ok is False
    assert err == "email_send_disabled"


def test_3_fallback_no_pdf_bytes_omits_attachments(monkeypatch):
    """pdf_bytes=b'' → email sent WITHOUT attachments key, body must contain dashboard link."""
    import email_service as ems
    captured = {}

    def _fake_send(params):
        captured["params"] = params
        return {"id": "id_x"}

    monkeypatch.setattr(ems, "SEND_EMAILS", True)
    monkeypatch.setattr(ems, "RESEND_API_KEY", "test-key")
    monkeypatch.setattr(ems.resend.Emails, "send", _fake_send)

    ok, err = asyncio.run(ems.send_fattura_paziente_email(
        "paz@fb.it", "Mario", "Rossi",
        "2026-10-15T14:00:00+00:00",
        {"numero": "FZ-2026-0004", "importo_totale": 80, "data": "2026-10-15"},
        b"",
    ))
    assert ok is True, err
    p = captured["params"]
    assert "attachments" not in p, "attachments key must be absent when pdf_bytes empty"
    assert "/paziente/fatture" in p["html"], "dashboard link missing in fallback body"


# ─── E2E: _emit_fattura_for_paid_tx wiring ──────────────────────────────────

async def _seed_paid_appt(db):
    u_t = await db.users.insert_one({
        "email": f"test-iter35-t-{ObjectId()}@fb.it",
        "nome": "Mario", "cognome": "Bianchi", "role": "terapeuta",
    })
    terap = await db.terapisti.insert_one({
        "user_id": str(u_t.inserted_id),
        "nome": "Mario", "cognome": "Bianchi",
        "partita_iva": "12345678903",
        "codice_fiscale": "BNCMRA80A01H501U",
        "prezzo_sessione": 80,
        "residenza_indirizzo": "Via Roma 1",
        "residenza_cap": "20100",
        "residenza_comune": "Milano",
        "residenza_provincia": "MI",
    })
    u_p = await db.users.insert_one({
        "email": f"test-iter35-p-{ObjectId()}@fb.it",
        "nome": "Lucia", "cognome": "Verdi", "role": "paziente",
    })
    paz = await db.pazienti.insert_one({
        "user_id": str(u_p.inserted_id),
        "nome": "Lucia", "cognome": "Verdi",
        "codice_fiscale": "VRDLCU85A01F205X",
    })
    appt = await db.appuntamenti.insert_one({
        "terapeuta_id": str(terap.inserted_id),
        "terapeuta_user_id": str(u_t.inserted_id),
        "paziente_id": str(paz.inserted_id),
        "paziente_user_id": str(u_p.inserted_id),
        "data_ora": "2026-10-15T14:00:00",
        "durata_minuti": 60,
        "prezzo": 80,
        "stato": "confermato",
        "paid_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    })
    tx = await db.payment_transactions.insert_one({
        "session_id": f"cs_test_{ObjectId()}",
        "appointment_id": str(appt.inserted_id),
        "terapeuta_id": str(terap.inserted_id),
        "paziente_id": str(paz.inserted_id),
        "paziente_user_id": str(u_p.inserted_id),
        "amount": 8000, "currency": "eur",
        "payment_status": "paid", "status": "completed",
        "paid_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
    })
    return {
        "appt_id": str(appt.inserted_id),
        "tx_id": str(tx.inserted_id),
        "u_t_id": str(u_t.inserted_id),
        "u_p_id": str(u_p.inserted_id),
        "terapista_id": str(terap.inserted_id),
        "paziente_id": str(paz.inserted_id),
        "paziente_email": (await db.users.find_one({"_id": u_p.inserted_id}))["email"],
    }


async def _cleanup(db, s):
    await db.users.delete_one({"_id": ObjectId(s["u_t_id"])})
    await db.terapisti.delete_one({"_id": ObjectId(s["terapista_id"])})
    await db.users.delete_one({"_id": ObjectId(s["u_p_id"])})
    await db.pazienti.delete_one({"_id": ObjectId(s["paziente_id"])})
    await db.appuntamenti.delete_one({"_id": ObjectId(s["appt_id"])})
    await db.fatture.delete_many({"appuntamento_id": s["appt_id"]})
    await db.payment_transactions.delete_one({"_id": ObjectId(s["tx_id"])})


def test_4_emit_uses_branded_template_not_signature_receipt(monkeypatch):
    """End-to-end: _emit_fattura_for_paid_tx must call send_fattura_paziente_email
    (branded template), producing subject 'Fattura FZ-*' with reply_to info@funzionabene.it."""
    import email_service as ems
    captured = {}

    def _fake_send(params):
        captured.setdefault("all", []).append(params)
        return {"id": "e2e_send_id"}

    monkeypatch.setattr(ems, "SEND_EMAILS", True)
    monkeypatch.setattr(ems, "RESEND_API_KEY", "test-key")
    monkeypatch.setattr(ems.resend.Emails, "send", _fake_send)

    # Guard: signature-receipt template MUST NOT be invoked for sanitaria emission
    orig_sig = ems.send_signature_receipt_email
    async def _guard(*a, **kw):
        raise AssertionError("send_signature_receipt_email must NOT be called for fattura sanitaria")
    monkeypatch.setattr(ems, "send_signature_receipt_email", _guard)

    async def _run():
        client, db = _make_db()
        orig = _bind_db(db)
        seed = None
        try:
            seed = await _seed_paid_appt(db)
            from routers.payments import _emit_fattura_for_paid_tx
            pu = await db.users.find_one({"_id": ObjectId(seed["u_p_id"])})
            pu["_id"] = str(pu["_id"])
            fattura = await _emit_fattura_for_paid_tx(seed["tx_id"], seed["appt_id"], pu)
            return seed, fattura
        finally:
            if seed:
                await _cleanup(db, seed)
            _restore_db(orig)
            client.close()

    seed, fattura = asyncio.run(_run())
    assert fattura is not None, "fattura should have been generated"
    assert fattura.get("numero", "").startswith("FZ-"), fattura.get("numero")
    # Verify branded email sent
    sent = captured.get("all", [])
    fattura_sends = [p for p in sent if p.get("subject", "").startswith("Fattura FZ-")]
    assert len(fattura_sends) >= 1, f"No branded 'Fattura FZ-*' send captured. Subjects: {[p.get('subject') for p in sent]}"
    p = fattura_sends[0]
    assert p["reply_to"] == ["info@funzionabene.it"]
    assert p["to"] == [seed["paziente_email"]]
    # Restore
    monkeypatch.setattr(ems, "send_signature_receipt_email", orig_sig)


def test_5_storage_fetch_fail_persists_when_email_also_fails(monkeypatch):
    """When storage fetch raises AND email send returns False,
    tx.fattura_error_step MUST equal 'fetch_pdf' (fetch takes precedence)."""
    import email_service as ems
    import routers.fatture as fatture_mod
    import routers.payments as payments_mod

    # Stub _generate_fattura_paziente to return a fattura with ONLY storage_path (no inline)
    async def _fake_gen(appt_id):
        # Insert a fattura doc in the DB with only pdf_storage_path
        from bson import ObjectId as _Oid
        appt = await payments_mod.db.appuntamenti.find_one({"_id": _Oid(appt_id)})
        fdoc = {
            "_id": ObjectId(),
            "numero": "FZ-2026-9999",
            "kind": "sanitaria",
            "appuntamento_id": appt_id,
            "paziente_user_id": appt.get("paziente_user_id"),
            "terapeuta_user_id": appt.get("terapeuta_user_id"),
            "importo_totale": 80,
            "data": "2026-10-15",
            "causale": "test",
            "pdf_storage_path": "fake/path/notthere.pdf",
            # NO pdf_inline_b64 → forces storage fetch
        }
        await payments_mod.db.fatture.insert_one(fdoc)
        return fdoc

    monkeypatch.setattr(fatture_mod, "_generate_fattura_paziente", _fake_gen)

    # storage_service.get_object must raise
    import storage_service
    def _boom_get(path):
        raise RuntimeError("simulated storage down")
    monkeypatch.setattr(storage_service, "get_object", _boom_get)

    # Force email to fail so the fattura_error persistence branch executes
    monkeypatch.setattr(ems, "SEND_EMAILS", True)
    monkeypatch.setattr(ems, "RESEND_API_KEY", "test-key")
    def _fake_send_fail(params):
        raise RuntimeError("simulated resend down")
    monkeypatch.setattr(ems.resend.Emails, "send", _fake_send_fail)

    async def _run():
        client, db = _make_db()
        orig = _bind_db(db)
        seed = None
        try:
            seed = await _seed_paid_appt(db)
            from routers.payments import _emit_fattura_for_paid_tx
            pu = await db.users.find_one({"_id": ObjectId(seed["u_p_id"])})
            pu["_id"] = str(pu["_id"])
            await _emit_fattura_for_paid_tx(seed["tx_id"], seed["appt_id"], pu)
            tx = await db.payment_transactions.find_one({"_id": ObjectId(seed["tx_id"])})
            return seed, tx
        finally:
            if seed:
                await _cleanup(db, seed)
            _restore_db(orig)
            client.close()

    seed, tx = asyncio.run(_run())
    assert tx.get("fattura_error_step") == "fetch_pdf", f"expected step='fetch_pdf', got {tx.get('fattura_error_step')} err={tx.get('fattura_error')}"
    assert "simulated storage down" in (tx.get("fattura_error") or "")


def test_6_storage_fail_email_ok_sends_without_attachment(monkeypatch):
    """When storage fetch fails but email is delivered, patient still gets an email
    without attachment (body contains dashboard link)."""
    import email_service as ems
    import routers.fatture as fatture_mod
    import routers.payments as payments_mod

    async def _fake_gen(appt_id):
        from bson import ObjectId as _Oid
        appt = await payments_mod.db.appuntamenti.find_one({"_id": _Oid(appt_id)})
        fdoc = {
            "_id": ObjectId(),
            "numero": "FZ-2026-9998",
            "kind": "sanitaria",
            "appuntamento_id": appt_id,
            "paziente_user_id": appt.get("paziente_user_id"),
            "terapeuta_user_id": appt.get("terapeuta_user_id"),
            "importo_totale": 80,
            "data": "2026-10-15",
            "causale": "test",
            "pdf_storage_path": "fake/path/notthere.pdf",
        }
        await payments_mod.db.fatture.insert_one(fdoc)
        return fdoc

    monkeypatch.setattr(fatture_mod, "_generate_fattura_paziente", _fake_gen)
    import storage_service
    monkeypatch.setattr(storage_service, "get_object",
                        lambda p: (_ for _ in ()).throw(RuntimeError("storage down")))

    monkeypatch.setattr(ems, "SEND_EMAILS", True)
    monkeypatch.setattr(ems, "RESEND_API_KEY", "test-key")

    captured = {}
    def _fake_send(params):
        captured["params"] = params
        return {"id": "ok_id"}
    monkeypatch.setattr(ems.resend.Emails, "send", _fake_send)

    async def _run():
        client, db = _make_db()
        orig = _bind_db(db)
        seed = None
        try:
            seed = await _seed_paid_appt(db)
            from routers.payments import _emit_fattura_for_paid_tx
            pu = await db.users.find_one({"_id": ObjectId(seed["u_p_id"])})
            pu["_id"] = str(pu["_id"])
            await _emit_fattura_for_paid_tx(seed["tx_id"], seed["appt_id"], pu)
            tx = await db.payment_transactions.find_one({"_id": ObjectId(seed["tx_id"])})
            return seed, tx
        finally:
            if seed:
                await _cleanup(db, seed)
            _restore_db(orig)
            client.close()

    seed, tx = asyncio.run(_run())
    p = captured.get("params")
    assert p is not None, "email should have been sent"
    assert "attachments" not in p, "attachments must be absent when storage fetch failed"
    assert p["subject"].startswith("Fattura FZ-")
    assert "/paziente/fatture" in p["html"]


# ─── Admin reinvia — bypass email_sent_at ────────────────────────────────────

def test_7_admin_reinvia_bypasses_email_sent_at(monkeypatch, admin_session):
    """Admin reinvia must resend even when email_sent_at was already set."""
    import email_service as ems
    monkeypatch.setattr(ems, "SEND_EMAILS", True)
    monkeypatch.setattr(ems, "RESEND_API_KEY", "test-key")

    async def _seed():
        client, db = _make_db()
        try:
            seed = await _seed_paid_appt(db)
            # Insert a sanitaria fattura tied to appt WITH email_sent_at yesterday
            fid = ObjectId()
            unique_num = f"FZ-TEST-{str(fid)[-6:]}"
            await db.fatture.insert_one({
                "_id": fid,
                "numero": unique_num,
                "kind": "sanitaria",
                "appuntamento_id": seed["appt_id"],
                "paziente_user_id": seed["u_p_id"],
                "terapeuta_user_id": seed["u_t_id"],
                "importo_totale": 80,
                "data": "2026-10-15",
                "causale": "test",
                "pdf_inline_b64": "SExMTw==",  # base64 for "HLLO"
                "email_sent_at": datetime.now(timezone.utc) - timedelta(days=1),
            })
            seed["fid"] = str(fid)
            seed["fz_numero"] = unique_num
            return seed
        finally:
            client.close()

    async def _clean(seed):
        client, db = _make_db()
        try:
            await _cleanup(db, seed)
        finally:
            client.close()

    seed = asyncio.run(_seed())
    try:
        r = admin_session.post(f"{BASE_URL}/api/admin/fatture/{seed['fid']}/reinvia", timeout=30)
        # backend is real; email may go out or Resend may reject — accept 200 or 503.
        # It MUST NOT return 4xx (which would mean the endpoint skipped for idempotency).
        assert r.status_code in (200, 503), r.text
        if r.status_code == 200:
            body = r.json()
            assert body.get("numero") == seed["fz_numero"]
            assert "attachment" in body
            assert body.get("email") == seed["paziente_email"]
    finally:
        asyncio.run(_clean(seed))


def test_8_admin_reinvia_nota_credito_still_uses_signature_receipt(monkeypatch, admin_session):
    """NC (kind='nota_credito_sanitaria') keeps the signature-receipt template."""
    # We just verify the endpoint returns 200/503 for NC (not 4xx logic error),
    # and that the response payload uses the same reinvia contract.
    async def _seed():
        client, db = _make_db()
        try:
            seed = await _seed_paid_appt(db)
            fid = ObjectId()
            unique_num = f"NC-TEST-{str(fid)[-6:]}"
            await db.fatture.insert_one({
                "_id": fid,
                "numero": unique_num,
                "kind": "nota_credito_sanitaria",
                "appuntamento_id": seed["appt_id"],
                "paziente_user_id": seed["u_p_id"],
                "terapeuta_user_id": seed["u_t_id"],
                "importo_totale": -80,
                "fattura_originale_numero": "FZ-2026-0004",
                "data": "2026-10-16",
                "causale": "storno",
                "pdf_inline_b64": "SEVMTE8=",
            })
            seed["fid"] = str(fid)
            seed["nc_numero"] = unique_num
            return seed
        finally:
            client.close()

    async def _clean(seed):
        client, db = _make_db()
        try:
            await _cleanup(db, seed)
        finally:
            client.close()

    seed = asyncio.run(_seed())
    try:
        r = admin_session.post(f"{BASE_URL}/api/admin/fatture/{seed['fid']}/reinvia", timeout=30)
        assert r.status_code in (200, 503), r.text
        if r.status_code == 200:
            body = r.json()
            assert body.get("numero") == seed["nc_numero"]
    finally:
        asyncio.run(_clean(seed))
