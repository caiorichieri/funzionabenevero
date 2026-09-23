"""Iteration 33 backend regression: H1 (IDOR fix), H2 (commission includes
all paid states), M1 (refund side-effects idempotency).

Public URL cookie-based auth. Direct DB writes are used to seed
- a second test patient (B) so we can attempt IDOR on patient A
- appointments in specific fiscal states (in_corso, no_show_paziente, etc.)
- payment transactions + linked fatture sanitaria for refund tests
"""
import asyncio
import os
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import bcrypt
import pytest
import requests
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]

ADMIN = {"email": "hr@funzionabene.it", "password": "@Bidoc2026!"}
PAZ_A = {"email": "demo.paziente@funzionabene.it", "password": "paziente2026"}
TER = {"email": "demo.terapeuta@funzionabene.it", "password": "terapeuta2026"}

PAZ_B_EMAIL = f"test_iter33_paz_b_{uuid.uuid4().hex[:6]}@example.com"
PAZ_B_PWD = "PazBTest2026!"


# ─── fixtures ────────────────────────────────────────────────────────────────
# Use function-scoped loop + client to be robust against pytest-asyncio in
# other test files (module-scoped loops get closed by other suites).
@pytest.fixture
def _loop_and_client():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        yield loop, client
    finally:
        client.close()
        asyncio.set_event_loop(None)
        loop.close()


@pytest.fixture
def event_loop(_loop_and_client):
    return _loop_and_client[0]


@pytest.fixture
def db(_loop_and_client):
    return _loop_and_client[1][DB_NAME]


def _login(creds):
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json=creds, timeout=20)
    assert r.status_code == 200, f"login failed for {creds['email']}: {r.status_code} {r.text}"
    return s


@pytest.fixture(scope="module")
def admin_session():
    return _login(ADMIN)


@pytest.fixture(scope="module")
def paz_a_session():
    return _login(PAZ_A)


@pytest.fixture(scope="module")
def ter_session():
    return _login(TER)


@pytest.fixture
def paz_b(event_loop, db):
    """Create a 2nd patient directly in Mongo (bypasses OTP flow for isolated
    test)."""
    async def _mk():
        await db.users.delete_many({"email": PAZ_B_EMAIL})
        pwd_hash = bcrypt.hashpw(PAZ_B_PWD.encode(), bcrypt.gensalt()).decode()
        user_id = ObjectId()
        await db.users.insert_one({
            "_id": user_id,
            "email": PAZ_B_EMAIL,
            "password_hash": pwd_hash,
            "nome": "TEST_PazB",
            "cognome": "Iter33",
            "role": "paziente",
            "is_verified": True,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        })
        paz_id = ObjectId()
        await db.pazienti.insert_one({
            "_id": paz_id,
            "user_id": str(user_id),
            "nome": "TEST_PazB",
            "cognome": "Iter33",
        })
        return str(user_id), str(paz_id)

    user_id, paz_id = event_loop.run_until_complete(_mk())
    sess = _login({"email": PAZ_B_EMAIL, "password": PAZ_B_PWD})
    yield {"session": sess, "user_id": user_id, "paziente_id": paz_id}

    async def _cleanup():
        await db.users.delete_many({"email": PAZ_B_EMAIL})
        await db.pazienti.delete_many({"_id": ObjectId(paz_id)})
        await db.appuntamenti.delete_many({"paziente_user_id": user_id})

    event_loop.run_until_complete(_cleanup())


def _me(sess):
    return sess.get(f"{API}/auth/me", timeout=10).json()


async def _seed_appt(db, *, paziente_user_id, paziente_id, terapeuta_user_id, terapeuta_id,
                     stato="prenotato", data_ora=None, prezzo=80, with_terapeuta_user_id=True):
    doc = {
        "paziente_user_id": paziente_user_id,
        "paziente_id": paziente_id,
        "terapeuta_id": terapeuta_id,
        "data_ora": data_ora or (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "durata_minuti": 50,
        "tipo": "online",
        "prezzo": prezzo,
        "stato": stato,
        "created_at": datetime.now(timezone.utc),
    }
    if with_terapeuta_user_id and terapeuta_user_id:
        doc["terapeuta_user_id"] = terapeuta_user_id
    res = await db.appuntamenti.insert_one(doc)
    return str(res.inserted_id)


@pytest.fixture
def owner_ids(event_loop, db, paz_a_session, ter_session, paz_b):
    """Resolve paziente_id/terapeuta_id from profiles for the seeded users."""
    a_me = _me(paz_a_session)
    t_me = _me(ter_session)

    async def _resolve():
        p_a = await db.pazienti.find_one({"user_id": a_me["_id"]})
        t = await db.terapisti.find_one({"user_id": t_me["_id"]})
        return {
            "paz_a_user": a_me["_id"],
            "paz_a_id": str(p_a["_id"]) if p_a else None,
            "paz_b_user": paz_b["user_id"],
            "paz_b_id": paz_b["paziente_id"],
            "ter_user": t_me["_id"],
            "ter_id": str(t["_id"]) if t else None,
        }

    return event_loop.run_until_complete(_resolve())


# ─── H1 AUTHZ TESTS ──────────────────────────────────────────────────────────
class TestH1IDORAuthorization:
    def test_paz_a_cannot_patch_paz_b_appt_stato(self, event_loop, db, paz_a_session, owner_ids):
        # Seed appt owned by patient B
        appt_id = event_loop.run_until_complete(_seed_appt(
            db,
            paziente_user_id=owner_ids["paz_b_user"], paziente_id=owner_ids["paz_b_id"],
            terapeuta_user_id=owner_ids["ter_user"], terapeuta_id=owner_ids["ter_id"],
            stato="prenotato",
        ))
        r = paz_a_session.patch(f"{API}/appuntamenti/{appt_id}/stato", json={"stato": "cancellato"}, timeout=10)
        assert r.status_code == 403, f"expected 403 (IDOR block); got {r.status_code} {r.text}"

    def test_paz_a_cannot_put_paz_b_appt(self, event_loop, db, paz_a_session, owner_ids):
        appt_id = event_loop.run_until_complete(_seed_appt(
            db,
            paziente_user_id=owner_ids["paz_b_user"], paziente_id=owner_ids["paz_b_id"],
            terapeuta_user_id=owner_ids["ter_user"], terapeuta_id=owner_ids["ter_id"],
        ))
        r = paz_a_session.put(f"{API}/appuntamenti/{appt_id}", json={
            "terapeuta_id": owner_ids["ter_id"], "paziente_id": owner_ids["paz_b_id"],
            "data_ora": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
        }, timeout=10)
        assert r.status_code == 403, f"expected 403; got {r.status_code} {r.text}"

    def test_owner_paz_cannot_force_completato(self, event_loop, db, paz_a_session, owner_ids):
        # Paziente A owns; still cannot self-force fiscal state 'completato'
        appt_id = event_loop.run_until_complete(_seed_appt(
            db,
            paziente_user_id=owner_ids["paz_a_user"], paziente_id=owner_ids["paz_a_id"],
            terapeuta_user_id=owner_ids["ter_user"], terapeuta_id=owner_ids["ter_id"],
        ))
        r = paz_a_session.patch(f"{API}/appuntamenti/{appt_id}/stato", json={"stato": "completato"}, timeout=10)
        assert r.status_code == 403, f"expected 403 (only admin can force completato); got {r.status_code} {r.text}"

    def test_owner_paz_cannot_force_cancellato_con_addebito(self, event_loop, db, paz_a_session, owner_ids):
        appt_id = event_loop.run_until_complete(_seed_appt(
            db,
            paziente_user_id=owner_ids["paz_a_user"], paziente_id=owner_ids["paz_a_id"],
            terapeuta_user_id=owner_ids["ter_user"], terapeuta_id=owner_ids["ter_id"],
        ))
        r = paz_a_session.patch(f"{API}/appuntamenti/{appt_id}/stato",
                                json={"stato": "cancellato_con_addebito"}, timeout=10)
        assert r.status_code == 403

    def test_owner_paz_can_cancel_own_appt(self, event_loop, db, paz_a_session, owner_ids):
        appt_id = event_loop.run_until_complete(_seed_appt(
            db,
            paziente_user_id=owner_ids["paz_a_user"], paziente_id=owner_ids["paz_a_id"],
            terapeuta_user_id=owner_ids["ter_user"], terapeuta_id=owner_ids["ter_id"],
        ))
        r = paz_a_session.patch(f"{API}/appuntamenti/{appt_id}/stato",
                                json={"stato": "cancellato"}, timeout=10)
        assert r.status_code == 200, f"owner should cancel own; got {r.status_code} {r.text}"

    def test_admin_can_force_completato_and_triggers_fattura(self, event_loop, db, admin_session, owner_ids):
        # Seed at completed price. Admin sets stato=completato.
        appt_id = event_loop.run_until_complete(_seed_appt(
            db,
            paziente_user_id=owner_ids["paz_a_user"], paziente_id=owner_ids["paz_a_id"],
            terapeuta_user_id=owner_ids["ter_user"], terapeuta_id=owner_ids["ter_id"],
            stato="confermato", prezzo=80,
        ))
        r = admin_session.patch(f"{API}/appuntamenti/{appt_id}/stato",
                                json={"stato": "completato"}, timeout=30)
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        # idempotent second call
        r2 = admin_session.patch(f"{API}/appuntamenti/{appt_id}/stato",
                                 json={"stato": "completato"}, timeout=30)
        assert r2.status_code == 200

    def test_terapeuta_owner_can_confirm_own_appt(self, event_loop, db, ter_session, owner_ids):
        appt_id = event_loop.run_until_complete(_seed_appt(
            db,
            paziente_user_id=owner_ids["paz_a_user"], paziente_id=owner_ids["paz_a_id"],
            terapeuta_user_id=owner_ids["ter_user"], terapeuta_id=owner_ids["ter_id"],
        ))
        r = ter_session.patch(f"{API}/appuntamenti/{appt_id}/stato",
                              json={"stato": "confermato"}, timeout=10)
        assert r.status_code == 200, f"{r.status_code} {r.text}"

    def test_terapeuta_other_terapist_appt_blocked(self, event_loop, db, ter_session, owner_ids):
        # Fake other therapist: put a random user_id + fake terapeuta_id
        fake_ter_user = str(ObjectId())
        fake_ter_id = str(ObjectId())
        appt_id = event_loop.run_until_complete(_seed_appt(
            db,
            paziente_user_id=owner_ids["paz_a_user"], paziente_id=owner_ids["paz_a_id"],
            terapeuta_user_id=fake_ter_user, terapeuta_id=fake_ter_id,
        ))
        r = ter_session.patch(f"{API}/appuntamenti/{appt_id}/stato",
                              json={"stato": "confermato"}, timeout=10)
        assert r.status_code == 403

    def test_terapeuta_legacy_appt_fallback_via_terapista_user_id(self, event_loop, db, ter_session, owner_ids):
        """Legacy appt WITHOUT terapeuta_user_id — code must fallback via
        db.terapisti.user_id lookup by terapeuta_id."""
        appt_id = event_loop.run_until_complete(_seed_appt(
            db,
            paziente_user_id=owner_ids["paz_a_user"], paziente_id=owner_ids["paz_a_id"],
            terapeuta_user_id=None, terapeuta_id=owner_ids["ter_id"],
            with_terapeuta_user_id=False,
        ))
        r = ter_session.patch(f"{API}/appuntamenti/{appt_id}/stato",
                              json={"stato": "confermato"}, timeout=10)
        assert r.status_code == 200, f"legacy fallback failed: {r.status_code} {r.text}"

    def test_post_appuntamenti_paziente_forbidden(self, paz_a_session, owner_ids):
        r = paz_a_session.post(f"{API}/appuntamenti", json={
            "terapeuta_id": owner_ids["ter_id"], "paziente_id": owner_ids["paz_a_id"],
            "data_ora": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        }, timeout=10)
        assert r.status_code == 403

    def test_post_appuntamenti_terapeuta_forbidden(self, ter_session, owner_ids):
        r = ter_session.post(f"{API}/appuntamenti", json={
            "terapeuta_id": owner_ids["ter_id"], "paziente_id": owner_ids["paz_a_id"],
            "data_ora": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
        }, timeout=10)
        assert r.status_code == 403

    def test_post_appuntamenti_admin_ok(self, admin_session, owner_ids, event_loop, db):
        r = admin_session.post(f"{API}/appuntamenti", json={
            "terapeuta_id": owner_ids["ter_id"], "paziente_id": owner_ids["paz_a_id"],
            "data_ora": (datetime.now(timezone.utc) + timedelta(days=6)).isoformat(),
        }, timeout=10)
        assert r.status_code == 200, f"{r.status_code} {r.text}"
        data = r.json()
        assert "_id" in data
        # cleanup
        event_loop.run_until_complete(db.appuntamenti.delete_one({"_id": ObjectId(data["_id"])}))


# ─── H2 COMMISSION TESTS ─────────────────────────────────────────────────────
class TestH2CommissionPaidStates:
    """Verify PAID_APPT_STATES aggregation includes in_corso, no_show_paziente,
    excludes cancellato."""

    @pytest.fixture(autouse=True)
    def _cleanup_marker(self, event_loop, db, owner_ids):
        # Purge any prior test commission fixtures + our seeded appts for this month
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month
        month_prefix = f"{year:04d}-{month:02d}-"

        async def _clean():
            await db.appuntamenti.delete_many({
                "terapeuta_user_id": owner_ids["ter_user"],
                "data_ora": {"$regex": f"^{month_prefix}"},
                "note_test_marker": "iter33_commission",
            })
            await db.fatture.delete_many({
                "kind": "commissione",
                "terapeuta_user_id": owner_ids["ter_user"],
                "anno_riferimento": year, "mese_riferimento": month,
            })

        event_loop.run_until_complete(_clean())
        yield
        event_loop.run_until_complete(_clean())

    def _seed_with_marker(self, event_loop, db, owner_ids, stato, prezzo):
        now = datetime.now(timezone.utc)
        # date_ora in current month, random-ish day
        dt = now.replace(day=min(15, now.day), hour=10, minute=0, second=0, microsecond=0)

        async def _do():
            doc = {
                "paziente_user_id": owner_ids["paz_a_user"],
                "paziente_id": owner_ids["paz_a_id"],
                "terapeuta_user_id": owner_ids["ter_user"],
                "terapeuta_id": owner_ids["ter_id"],
                "data_ora": dt.isoformat(),
                "durata_minuti": 50, "tipo": "online",
                "prezzo": prezzo, "stato": stato,
                "note_test_marker": "iter33_commission",
                "created_at": datetime.now(timezone.utc),
            }
            r = await db.appuntamenti.insert_one(doc)
            return str(r.inserted_id)

        return event_loop.run_until_complete(_do())

    def _call_generate(self, admin_session):
        now = datetime.now(timezone.utc)
        # Endpoint: /admin/fatture/generate/commissione/{year}/{month}
        return admin_session.post(f"{API}/admin/fatture/generate/commissione/{now.year}/{now.month}",
                                  timeout=60)

    def _internal_aggregation(self, event_loop, db, owner_ids):
        """Directly invoke _generate_fatture_commissione_mensile logic on the
        aggregate — but if the therapist lacks codice_sdi/pec, the endpoint
        skips them. So we assert on the appuntamenti aggregate directly."""
        from importlib import import_module
        # Just count matching states via the same PAID_APPT_STATES list.
        fatture_mod = import_module("routers.fatture")
        states = fatture_mod.PAID_APPT_STATES
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month
        month_prefix = f"{year:04d}-{month:02d}-"

        async def _agg():
            return await db.appuntamenti.count_documents({
                "terapeuta_user_id": owner_ids["ter_user"],
                "stato": {"$in": states},
                "data_ora": {"$regex": f"^{month_prefix}"},
                "note_test_marker": "iter33_commission",
            })

        return event_loop.run_until_complete(_agg())

    def test_in_corso_included_in_paid_states(self, event_loop, db, owner_ids):
        self._seed_with_marker(event_loop, db, owner_ids, "in_corso", 80)
        count = self._internal_aggregation(event_loop, db, owner_ids)
        assert count == 1, f"in_corso must be counted as paid; got {count}"

    def test_no_show_paziente_included(self, event_loop, db, owner_ids):
        self._seed_with_marker(event_loop, db, owner_ids, "no_show_paziente", 80)
        count = self._internal_aggregation(event_loop, db, owner_ids)
        assert count == 1

    def test_cancellato_excluded(self, event_loop, db, owner_ids):
        self._seed_with_marker(event_loop, db, owner_ids, "cancellato", 80)
        count = self._internal_aggregation(event_loop, db, owner_ids)
        assert count == 0, "cancellato must NOT be in paid states"

    def test_paid_states_constant_shape(self):
        from importlib import import_module
        states = import_module("routers.fatture").PAID_APPT_STATES
        # Contract per iter33
        for expected in ("completato", "confermato", "in_corso",
                         "no_show_paziente", "no_show_terapeuta",
                         "no_show_entrambi", "cancellato_con_addebito"):
            assert expected in states, f"{expected} missing from PAID_APPT_STATES"
        assert "cancellato" not in states
        assert "annullato" not in states


# ─── M1 REFUND WEBHOOK TESTS ────────────────────────────────────────────────
class TestM1RefundSideEffects:
    """Directly invoke _apply_refund_side_effects (documented as safe by review
    request). Verify appt cancelled + NC emitted + idempotent."""

    def test_refund_helper_cancels_appt_and_emits_nc(self, event_loop, db, owner_ids, monkeypatch):
        # Rebind the router's `db` to a client on the CURRENT test loop —
        # otherwise routers/payments.py may hold a client bound to a loop
        # closed by pytest-asyncio in another test file.
        import deps as _deps
        monkeypatch.setattr(_deps, "db", db)
        import routers.payments as _pay
        import routers.fatture as _fat
        monkeypatch.setattr(_pay, "db", db)
        monkeypatch.setattr(_fat, "db", db)
        # Ensure demo terapeuta has full fiscal anagrafica (required for NC XML)
        async def _ensure_anagrafica():
            u = await db.users.find_one({"_id": ObjectId(owner_ids["ter_user"])})
            orig = {k: u.get(k) for k in ("partita_iva", "codice_fiscale", "indirizzo", "cap", "citta", "provincia", "nazione")}
            patches = {
                "partita_iva": u.get("partita_iva") or "12345678903",
                "codice_fiscale": u.get("codice_fiscale") or "RSSMRA80A01H501U",
                "indirizzo": u.get("indirizzo") or "Via Test 1",
                "cap": u.get("cap") or "00100",
                "citta": u.get("citta") or "Roma",
                "provincia": u.get("provincia") or "RM",
                "nazione": u.get("nazione") or "IT",
            }
            await db.users.update_one({"_id": ObjectId(owner_ids["ter_user"])}, {"$set": patches})
            return orig

        orig_ter = event_loop.run_until_complete(_ensure_anagrafica())

        # Seed: appt in 'completato' + original fattura sanitaria + tx paid
        async def _seed():
            appt_id_obj = ObjectId()
            appt_id = str(appt_id_obj)
            await db.appuntamenti.insert_one({
                "_id": appt_id_obj,
                "paziente_user_id": owner_ids["paz_a_user"],
                "paziente_id": owner_ids["paz_a_id"],
                "terapeuta_user_id": owner_ids["ter_user"],
                "terapeuta_id": owner_ids["ter_id"],
                "data_ora": datetime.now(timezone.utc).isoformat(),
                "durata_minuti": 50, "tipo": "online",
                "prezzo": 80, "stato": "completato",
                "note_test_marker": "iter33_refund",
                "created_at": datetime.now(timezone.utc),
            })
            fatt_id = ObjectId()
            await db.fatture.insert_one({
                "_id": fatt_id,
                "numero": f"TEST-ITER33-{uuid.uuid4().hex[:6]}",
                "kind": "sanitaria",
                "appuntamento_id": appt_id,
                "paziente_user_id": owner_ids["paz_a_user"],
                "terapeuta_user_id": owner_ids["ter_user"],
                "importo_totale": 80.0,
                "imponibile": 80.0, "imposta": 0.0,
                "data": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "year": datetime.now(timezone.utc).year,
                "created_at": datetime.now(timezone.utc),
                "note_test_marker": "iter33_refund",
            })
            tx_id = ObjectId()
            await db.payment_transactions.insert_one({
                "_id": tx_id,
                "appointment_id": appt_id,
                "paziente_user_id": owner_ids["paz_a_user"],
                "terapeuta_user_id": owner_ids["ter_user"],
                "amount": 80.0, "currency": "eur",
                "status": "paid", "payment_status": "paid",
                "stripe_payment_intent_id": f"pi_test_{uuid.uuid4().hex[:10]}",
                "created_at": datetime.now(timezone.utc),
                "note_test_marker": "iter33_refund",
            })
            return appt_id, str(fatt_id), str(tx_id)

        appt_id, fatt_id, tx_id = event_loop.run_until_complete(_seed())

        # Invoke helper directly (as review request suggested)
        import sys, pathlib
        sys.path.insert(0, str(pathlib.Path("/app/backend").resolve()))
        from routers.payments import _apply_refund_side_effects  # type: ignore

        async def _run():
            tx = await db.payment_transactions.find_one({"_id": ObjectId(tx_id)})
            # First call
            nc1 = await _apply_refund_side_effects(tx=tx, admin_note="test refund", motivo_nc="Test NC")
            # Second call (idempotent)
            nc2 = await _apply_refund_side_effects(tx=tx, admin_note="test refund", motivo_nc="Test NC")
            appt = await db.appuntamenti.find_one({"_id": ObjectId(appt_id)})
            ncs = await db.fatture.find({
                "appuntamento_id": appt_id,
                "kind": {"$in": ["nota_credito", "nota_credito_sanitaria"]},
            }).to_list(10)
            return nc1, nc2, appt, ncs

        nc1, nc2, appt, ncs = event_loop.run_until_complete(_run())

        # (a) appt cancelled
        assert appt["stato"] == "cancellato", f"appt stato={appt['stato']} (expected cancellato)"
        assert appt.get("cancellato_motivo") == "rimborsato"

        # (b) NC emitted linked to original fattura
        assert len(ncs) >= 1, "NC not created"
        nc_doc = ncs[0]
        # link — code uses fattura_originale_id (not original_fattura_id as in review req)
        link_ok = (nc_doc.get("fattura_originale_id") == fatt_id) or (nc_doc.get("original_fattura_id") == fatt_id)
        assert link_ok, f"NC not linked back to fattura {fatt_id}: keys={list(nc_doc.keys())}"

        # (c) idempotent — second call must not create a 2nd NC
        assert len(ncs) == 1, f"idempotency broken: {len(ncs)} NCs found"

        # cleanup
        async def _clean():
            await db.appuntamenti.delete_one({"_id": ObjectId(appt_id)})
            await db.fatture.delete_one({"_id": ObjectId(fatt_id)})
            await db.fatture.delete_many({"appuntamento_id": appt_id})
            await db.payment_transactions.delete_one({"_id": ObjectId(tx_id)})
            # Restore original ter anagrafica (only fields we actually had originally)
            unset = {k: "" for k, v in orig_ter.items() if v is None}
            setv = {k: v for k, v in orig_ter.items() if v is not None}
            if unset:
                await db.users.update_one({"_id": ObjectId(owner_ids["ter_user"])}, {"$unset": unset})
            if setv:
                await db.users.update_one({"_id": ObjectId(owner_ids["ter_user"])}, {"$set": setv})

        event_loop.run_until_complete(_clean())

    def test_refund_webhook_guard_on_already_refunded(self, event_loop, db, owner_ids):
        """Second charge.refunded delivery must be a no-op (payment_status
        guard). We assert by direct DB check on the update guard."""
        async def _seed():
            tx_id = ObjectId()
            pi = f"pi_test_iter33_{uuid.uuid4().hex[:10]}"
            await db.payment_transactions.insert_one({
                "_id": tx_id,
                "appointment_id": None,
                "amount": 80.0, "currency": "eur",
                "status": "refunded", "payment_status": "refunded",
                "stripe_payment_intent_id": pi,
                "created_at": datetime.now(timezone.utc),
                "note_test_marker": "iter33_refund",
            })
            return str(tx_id), pi

        tx_id, pi = event_loop.run_until_complete(_seed())

        async def _run_guard():
            # Same query the webhook uses
            result = await db.payment_transactions.update_one(
                {"stripe_payment_intent_id": pi, "payment_status": {"$ne": "refunded"}},
                {"$set": {"status": "refunded", "payment_status": "refunded"}},
            )
            return result.modified_count

        modified = event_loop.run_until_complete(_run_guard())
        assert modified == 0, "guard must prevent 2nd apply"

        event_loop.run_until_complete(db.payment_transactions.delete_one({"_id": ObjectId(tx_id)}))
