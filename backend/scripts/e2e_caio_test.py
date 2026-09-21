"""E2E test in the preview environment for caioricchieri@gmail.com.

Runs the full booking flow end-to-end (WITHOUT Stripe):
  1. Ensure a demo therapist with valid fiscal data + a patient (caioricchieri) exist.
  2. Create a paid appointment scheduled ~17 minutes from now (so the 15-min
     reminder fires ~2 min after this script completes).
  3. Trigger `finalize_confirmed_booking` — sends booking confirmation emails
     (to patient + therapist) and schedules the 3 reminder jobs in MongoDB.
  4. Simulate `_mark_payment_paid`'s post-payment step: emit fattura sanitaria
     + email PDF to patient.
  5. After ~120s, trigger admin refund → emit Nota di Credito TD04 + email PDF.

Usage: python3 e2e_caio_test.py
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

PATIENT_EMAIL = "caioricchieri@gmail.com"
THERAPIST_EMAIL = "e2e.terapeuta@fb.it"


async def ensure_therapist(db):
    u = await db.users.find_one({"email": THERAPIST_EMAIL})
    if not u:
        uid = ObjectId()
        await db.users.insert_one({
            "_id": uid,
            "email": THERAPIST_EMAIL,
            "password_hash": hash_password("test2026"),
            "nome": "Mario", "cognome": "Rossi",
            "role": "terapeuta",
            "is_active": True, "is_verified": True,
            "approval_status": "approvato",
            "telefono_verificato": True,
        })
        u = await db.users.find_one({"_id": uid})
    tid = ObjectId()
    await db.terapisti.update_one(
        {"user_id": str(u["_id"])},
        {"$setOnInsert": {"_id": tid},
         "$set": {
             "user_id": str(u["_id"]),
             "nome": "Mario", "cognome": "Rossi",
             "partita_iva": "12345678903",
             "codice_fiscale": "RSSMRA80A01H501U",
             "residenza_indirizzo": "Via Roma 1",
             "residenza_cap": "00100",
             "residenza_comune": "Roma",
             "residenza_provincia": "RM",
             "regime_fiscale": "forfettario",
             "prezzo_sessione": 80,
             "durata_sessione": 50,
             "documenti_verificati": True,
             "autocertificazione_firmata": True,
             "approval_status": "approvato",
             "sospeso": False,
             "email": THERAPIST_EMAIL,
        }},
        upsert=True,
    )
    return await db.terapisti.find_one({"user_id": str(u["_id"])}), u


async def ensure_patient(db):
    u = await db.users.find_one({"email": PATIENT_EMAIL})
    if not u:
        uid = ObjectId()
        await db.users.insert_one({
            "_id": uid,
            "email": PATIENT_EMAIL,
            "password_hash": hash_password("Caio2026!"),
            "nome": "Caio",
            "cognome": "Ricchieri",
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
             "nome": "Caio", "cognome": "Ricchieri",
             "codice_fiscale": "RCCCAI85A01F205X",
             "indirizzo": "Via Milano 5",
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


async def main():
    client = AsyncIOMotorClient(os.environ["MONGO_URL"])
    db = client[os.environ["DB_NAME"]]

    print("→ 1/5 ensuring therapist + patient…")
    t, t_user = await ensure_therapist(db)
    p, p_user = await ensure_patient(db)
    print(f"    therapist: {t['nome']} {t['cognome']} (user_id={t['user_id']})")
    print(f"    patient:   {p['nome']} {p['cognome']} (user_id={p['user_id']}) email={p_user['email']}")

    # 2. Schedule appointment ~17 min from now (data_ora stored as UTC ISO)
    start_utc = datetime.now(timezone.utc) + timedelta(minutes=17)
    data_ora_iso = start_utc.replace(second=0, microsecond=0).isoformat()
    print(f"→ 2/5 creating appointment at {data_ora_iso} (UTC, ~17 min from now)")

    appt_id = ObjectId()
    await db.appuntamenti.insert_one({
        "_id": appt_id,
        "paziente_id": str(p["_id"]),
        "paziente_user_id": str(p_user["_id"]),
        "terapeuta_id": str(t["_id"]),
        "terapeuta_user_id": str(t["user_id"]),
        "data_ora": data_ora_iso,
        "durata_minuti": 50,
        "prezzo": 80,
        "stato": "in_attesa_pagamento",
        "created_at": datetime.now(timezone.utc),
    })
    print(f"    appuntamento_id: {appt_id}")

    # 3. Create fake payment_transaction (needed for refund flow later)
    tx_id = ObjectId()
    await db.payment_transactions.insert_one({
        "_id": tx_id,
        "appointment_id": str(appt_id),
        "paziente_user_id": str(p_user["_id"]),
        "terapeuta_id": str(t["_id"]),
        "terapeuta_user_id": str(t["user_id"]),
        "amount": 8000,  # cents (€80)
        "currency": "eur",
        "payment_status": "paid",
        "payout_status": "pending",
        "provider": "stripe",
        "stripe_charge_id": "ch_test_e2e_" + str(tx_id),  # fake, refund won't call real Stripe
        "stripe_payment_intent_id": "pi_test_e2e_" + str(tx_id),
        "created_at": datetime.now(timezone.utc),
        "paid_at": datetime.now(timezone.utc),
    })

    # Update appointment to confermato
    await db.appuntamenti.update_one(
        {"_id": appt_id},
        {"$set": {"stato": "confermato", "paid_at": datetime.now(timezone.utc)}},
    )

    # 4. Send booking confirmations + schedule reminders + emit fattura
    print("→ 3/5 sending booking confirmation emails + scheduling reminders…")
    from booking_service import finalize_confirmed_booking, scheduler
    if not scheduler.running:
        scheduler.start()

    p_user_ready = {**p_user, "_id": str(p_user["_id"])}
    await finalize_confirmed_booking(str(appt_id), p_user_ready)
    print("    ✅ Booking confirmations sent (paziente + terapeuta)")
    print(f"    ✅ Reminders scheduled: 1-giorno (past → skipped), 1-ora (past → skipped), 15-min (~2 min from now)")

    print("→ 4/5 emitting fattura sanitaria + emailing patient…")
    from routers.fatture import _generate_fattura_paziente
    from email_service import send_signature_receipt_email
    from storage_service import get_object
    import base64
    fattura = await _generate_fattura_paziente(str(appt_id))
    pdf_bytes = base64.b64decode(fattura["pdf_inline_b64"]) if fattura.get("pdf_inline_b64") else b""
    if not pdf_bytes and fattura.get("pdf_storage_path"):
        try:
            pdf_bytes, _ = get_object(fattura["pdf_storage_path"])
        except Exception as e:
            print(f"    ⚠️ Storage fetch failed: {e}")
    print(f"    fattura PDF size: {len(pdf_bytes)} bytes")
    await send_signature_receipt_email(
        email=PATIENT_EMAIL,
        nome="Caio",
        doc_titles=[
            f"Fattura {fattura['numero']} — € {fattura.get('importo_totale', 0):.2f}",
            "💡 Detraibile 19% al 730 come spesa sanitaria (art. 15 TUIR)",
            "Conservala per almeno 5 anni",
        ],
        pdf_bytes=pdf_bytes,
    )
    print(f"    ✅ Fattura {fattura['numero']} inviata a {PATIENT_EMAIL}")

    print(f"\n💡 Il reminder 15-min arriverà tra ~2 minuti a {PATIENT_EMAIL}.")
    print(f"💡 Ora vado a dormire 3 minuti prima di generare la Nota di Credito, così vedi il reminder arrivare.")

    await asyncio.sleep(180)  # wait 3 min so the 15-min reminder fires

    # 5. Simulate refund → generate NC + email
    print("\n→ 5/5 simulating admin refund → generating Nota di Credito + email…")
    from routers.fatture import _generate_nota_credito_paziente
    nc = await _generate_nota_credito_paziente(
        str(fattura["_id"]),
        motivo="Test E2E — richiesta cliente",
    )
    nc_pdf = base64.b64decode(nc["pdf_inline_b64"]) if nc.get("pdf_inline_b64") else b""
    if not nc_pdf and nc.get("pdf_storage_path"):
        try:
            nc_pdf, _ = get_object(nc["pdf_storage_path"])
        except Exception as e:
            print(f"    ⚠️ NC Storage fetch failed: {e}")
    print(f"    NC PDF size: {len(nc_pdf)} bytes")
    await send_signature_receipt_email(
        email=PATIENT_EMAIL,
        nome="Caio",
        doc_titles=[
            f"Nota di Credito {nc['numero']} — storno fattura {fattura['numero']}",
            f"Importo stornato: € {abs(nc.get('importo_totale', 0)):.2f}",
            "Conservala insieme alla fattura originale.",
        ],
        pdf_bytes=nc_pdf,
    )
    # Also mark tx refunded
    await db.payment_transactions.update_one(
        {"_id": tx_id},
        {"$set": {"is_refunded": True, "refunded_at": datetime.now(timezone.utc),
                  "payment_status": "refunded", "payout_status": "refunded"}},
    )
    await db.appuntamenti.update_one(
        {"_id": appt_id},
        {"$set": {"stato": "cancellato", "cancellato_at": datetime.now(timezone.utc)}},
    )
    print(f"    ✅ Nota di Credito {nc['numero']} inviata a {PATIENT_EMAIL}")

    print("\n🎉 TEST COMPLETO! Verifica la inbox di caioricchieri@gmail.com. Dovresti aver ricevuto:")
    print("   1) Email di conferma prenotazione (con orario Rome)")
    print("   2) Email fattura sanitaria (con PDF allegato)")
    print("   3) Email reminder 15-min prima (con link per entrare nella stanza video)")
    print("   4) Email nota di credito (con PDF)")


if __name__ == "__main__":
    asyncio.run(main())
