"""Regression test for the auto-fattura flow after Stripe payment.

Bug: appointments created by /payments/checkout/booking store `terapeuta_id`
(→ terapisti._id) but the fattura generator was reading `terapeuta_user_id`
(→ users._id), which was never set. Result: silent ValueError, no fattura,
patient never gets billed.

Fix: `_resolve_terapeuta_user_id` in routers/fatture.py falls back to
terapisti.user_id when the appointment doesn't already have terapeuta_user_id,
and backfills the field on the appointment.
"""
import asyncio
import os
import sys
from datetime import datetime, timezone
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def test_generate_fattura_when_appt_missing_terapeuta_user_id():
    """One-shot async test: inserts terapista+paziente+appt (WITHOUT terapeuta_user_id),
    calls the fattura generator, and asserts number+backfill happen correctly."""
    async def _run():
        # Use a dedicated client bound to this test's loop.
        client = AsyncIOMotorClient(os.environ["MONGO_URL"])
        db = client[os.environ.get("DB_NAME", "funzionabene_db")]

        # Rebind the module-level `db` in deps + routers.fatture so the generator
        # uses our per-test client. This avoids "Event loop closed" from a stale
        # motor client bound to a different loop.
        import deps as _deps
        import routers.fatture as _fatture_mod
        original_deps_db = _deps.db
        original_fatture_db = _fatture_mod.db
        _deps.db = db
        _fatture_mod.db = db
        try:
            u_t = await db.users.insert_one({
                "email": f"test-fattura-{ObjectId()}@fb.it",
                "nome": "Mario", "cognome": "Rossi", "role": "terapeuta",
            })
            terapista = await db.terapisti.insert_one({
                "user_id": str(u_t.inserted_id),
                "nome": "Mario", "cognome": "Rossi",
                "partita_iva": "12345678903",
                "codice_fiscale": "RSSMRA80A01H501U",
                "prezzo_sessione": 80,
                "residenza_indirizzo": "Via Roma 1",
                "residenza_cap": "20100",
                "residenza_comune": "Milano",
                "residenza_provincia": "MI",
            })
            u_p = await db.users.insert_one({
                "email": f"test-fattura-pz-{ObjectId()}@fb.it",
                "nome": "Lucia", "cognome": "Verdi", "role": "paziente",
            })
            paziente = await db.pazienti.insert_one({
                "user_id": str(u_p.inserted_id),
                "nome": "Lucia", "cognome": "Verdi",
                "codice_fiscale": "VRDLCU85A01F205X",
            })
            r = await db.appuntamenti.insert_one({
                "terapeuta_id": str(terapista.inserted_id),  # terapisti._id (production shape)
                # NOTE: no terapeuta_user_id — reproduces the bug
                "paziente_id": str(paziente.inserted_id),
                "paziente_user_id": str(u_p.inserted_id),
                "data_ora": "2026-10-01T10:00:00",
                "durata_minuti": 60,
                "prezzo": 80,
                "stato": "confermato",
                "paid_at": datetime.now(timezone.utc),
                "created_at": datetime.now(timezone.utc),
            })
            appt_id = str(r.inserted_id)

            from routers.fatture import _generate_fattura_paziente, _resolve_terapeuta_user_id

            # 1. Resolver returns the therapist's user_id even without appt.terapeuta_user_id.
            appt = await db.appuntamenti.find_one({"_id": r.inserted_id})
            uid = await _resolve_terapeuta_user_id(appt)
            assert uid == str(u_t.inserted_id), f"expected {u_t.inserted_id}, got {uid}"

            # 2. Fattura generator succeeds end-to-end.
            f = await _generate_fattura_paziente(appt_id)
            assert f["numero"].startswith("FZ-"), f
            assert f["terapeuta_user_id"] == str(u_t.inserted_id)
            assert f["paziente_user_id"] == str(u_p.inserted_id)
            assert float(f["importo_totale"]) == 80.0

            # 3. Appointment now has terapeuta_user_id backfilled.
            appt_after = await db.appuntamenti.find_one({"_id": r.inserted_id})
            assert appt_after.get("terapeuta_user_id") == str(u_t.inserted_id)

            # 4. Idempotent: second call returns same fattura.
            f2 = await _generate_fattura_paziente(appt_id)
            assert str(f["_id"]) == str(f2["_id"])
            assert f["numero"] == f2["numero"]

            # Cleanup
            await db.users.delete_one({"_id": u_t.inserted_id})
            await db.terapisti.delete_one({"_id": terapista.inserted_id})
            await db.users.delete_one({"_id": u_p.inserted_id})
            await db.pazienti.delete_one({"_id": paziente.inserted_id})
            await db.appuntamenti.delete_one({"_id": r.inserted_id})
            await db.fatture.delete_many({"appuntamento_id": appt_id})
        finally:
            _deps.db = original_deps_db
            _fatture_mod.db = original_fatture_db
            client.close()

    asyncio.run(_run())
