"""Payments router: Stripe checkout, webhook, therapist earnings,
admin payouts + fattura sanitaria/commissione PDFs."""
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

import stripe as _stripe
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response as _FastResponse

from deps import (
    db, require_auth, require_admin, find_user_by_id,
    STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, PLATFORM_FEE_PERCENT,
)
from models import CheckoutBookingRequest, MarkPayoutPaidRequest
from invoice_pdf import build_fattura_sanitaria_pdf, build_fattura_commissione_pdf
from booking_service import finalize_confirmed_booking
from pydantic import BaseModel


class RefundRequest(BaseModel):
    transaction_id: str
    reason: str = "requested_by_customer"  # Stripe reason
    admin_note: str = ""

_stripe.api_key = STRIPE_SECRET_KEY

router = APIRouter()


async def _mark_payment_paid(session_id: str, payment_intent_id: Optional[str] = None) -> bool:
    """Idempotent: transition tx→paid, appointment→confermato, and provision room+emails.
    Returns True if this call actually flipped the tx to paid."""
    tx = await db.payment_transactions.find_one({"session_id": session_id})
    if not tx:
        return False
    if tx.get("payment_status") == "paid":
        return False
    now = datetime.now(timezone.utc)
    upd = {
        "status": "completed",
        "payment_status": "paid",
        "paid_at": now,
        "updated_at": now,
    }
    if payment_intent_id:
        upd["stripe_payment_intent_id"] = payment_intent_id
    result = await db.payment_transactions.update_one(
        {"session_id": session_id, "payment_status": {"$ne": "paid"}},
        {"$set": upd},
    )
    if result.modified_count == 0:
        return False
    appt_id = tx.get("appointment_id")
    if appt_id:
        await db.appuntamenti.update_one(
            {"_id": ObjectId(appt_id)},
            {"$set": {"stato": "confermato", "paid_at": now}},
        )
        paziente_user = await find_user_by_id(tx["paziente_user_id"])
        if paziente_user:
            paziente_user["_id"] = str(paziente_user["_id"])
            await finalize_confirmed_booking(appt_id, paziente_user)
    return True


@router.post("/payments/checkout/booking")
async def create_booking_checkout(req: CheckoutBookingRequest, user: dict = Depends(require_auth)):
    """Create a pending appointment + Stripe Checkout Session."""
    if user["role"] != "paziente":
        raise HTTPException(403, "Solo i pazienti possono prenotare")

    u_doc = await find_user_by_id(user["_id"])
    tv_at = (u_doc or {}).get("telefono_verificato_at")
    if isinstance(tv_at, str):
        try:
            tv_at = datetime.fromisoformat(tv_at)
        except Exception:
            tv_at = None
    if tv_at and tv_at.tzinfo is None:
        tv_at = tv_at.replace(tzinfo=timezone.utc)
    if not (u_doc and u_doc.get("telefono_verificato") and tv_at and (datetime.now(timezone.utc) - tv_at) <= timedelta(minutes=60)):
        raise HTTPException(403, "Verifica il numero di telefono via SMS prima di procedere al pagamento")

    terapista = await db.terapisti.find_one({"_id": ObjectId(req.terapeuta_id)})
    if not terapista:
        raise HTTPException(404, "Terapista non trovato")
    prezzo = terapista.get("prezzo_sessione") or 0
    if prezzo <= 0:
        raise HTTPException(400, "Prezzo sessione non configurato per questo terapista")

    # Defense-in-depth: reject if slot is already booked by anyone (even a still-pending checkout).
    # The frontend calendar filters booked slots too, but a stale UI or concurrent bookings could bypass.
    conflict = await db.appuntamenti.find_one({
        "terapeuta_id": req.terapeuta_id,
        "data_ora": req.data_ora,
        "stato": {"$nin": ["cancellato", "annullato", "payment_failed", "payment_expired"]},
    })
    if conflict:
        raise HTTPException(409, "Questo orario non è più disponibile. Scegli un altro slot.")

    amount_cents = int(round(prezzo * 100))
    platform_fee_cents = int(round(amount_cents * PLATFORM_FEE_PERCENT / 100))
    therapist_amount_cents = amount_cents - platform_fee_cents

    MARCA_DA_BOLLO_SOGLIA_CENTS = 7747
    marca_da_bollo_required = amount_cents >= MARCA_DA_BOLLO_SOGLIA_CENTS
    marca_da_bollo_amount = 200 if marca_da_bollo_required else 0

    appt_doc = {
        "terapeuta_id": req.terapeuta_id,
        "paziente_id": req.paziente_id,
        "paziente_user_id": user["_id"],
        "data_ora": req.data_ora,
        "durata_minuti": req.durata_minuti,
        "tipologia": req.tipologia,
        "modalita": req.modalita,
        "note": req.note,
        "stato": "in_attesa_pagamento",
        "created_at": datetime.now(timezone.utc),
    }
    ins = await db.appuntamenti.insert_one(appt_doc)
    appointment_id = str(ins.inserted_id)

    trusted_origins = {
        "https://funzionabene.it",
        "https://www.funzionabene.it",
    }
    env_origin = (os.environ.get("FRONTEND_URL") or os.environ.get("REACT_APP_BACKEND_URL") or "").rstrip("/")
    if env_origin:
        trusted_origins.add(env_origin)
    client_origin = (req.origin_url or "").rstrip("/")
    if client_origin in trusted_origins:
        base_url = client_origin
    else:
        base_url = env_origin or next(iter(trusted_origins))

    session = _stripe.checkout.Session.create(
        mode="payment",
        line_items=[{
            "price_data": {
                "currency": "eur",
                "product_data": {
                    "name": f"Sessione con {terapista.get('nome','')} {terapista.get('cognome','')}",
                    "description": f"{req.durata_minuti}' · {req.modalita} · {req.tipologia}",
                    "metadata": {"terapeuta_id": req.terapeuta_id},
                },
                "unit_amount": amount_cents,
            },
            "quantity": 1,
        }],
        success_url=f"{base_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{base_url}/payment/cancel?session_id={{CHECKOUT_SESSION_ID}}",
        metadata={
            "appointment_id": appointment_id,
            "terapeuta_id": req.terapeuta_id,
            "paziente_id": req.paziente_id,
            "paziente_user_id": user["_id"],
        },
        customer_email=user.get("email"),
    )

    await db.payment_transactions.insert_one({
        "session_id": session.id,
        "appointment_id": appointment_id,
        "terapeuta_id": req.terapeuta_id,
        "paziente_id": req.paziente_id,
        "paziente_user_id": user["_id"],
        "amount": amount_cents,
        "currency": "eur",
        "platform_fee_amount": platform_fee_cents,
        "platform_fee_percent": PLATFORM_FEE_PERCENT,
        "therapist_amount": therapist_amount_cents,
        "opposizione_ts": req.opposizione_ts,
        "marca_da_bollo_required": marca_da_bollo_required,
        "marca_da_bollo_amount": marca_da_bollo_amount,
        "fattura_sanitaria_status": "da_emettere",
        "status": "initiated",
        "payment_status": "pending",
        "payout_status": "pending",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })

    await db.appuntamenti.update_one(
        {"_id": ins.inserted_id},
        {"$set": {"stripe_session_id": session.id}},
    )

    return {
        "checkout_url": session.url,
        "session_id": session.id,
        "appointment_id": appointment_id,
        "amount": amount_cents,
        "currency": "eur",
    }


@router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str):
    """Unauthenticated status probe used by the /payment/success page."""
    tx = await db.payment_transactions.find_one({"session_id": session_id})
    if not tx:
        raise HTTPException(404, "Transaction not found")
    if tx.get("payment_status") != "paid":
        try:
            s = _stripe.checkout.Session.retrieve(session_id)
            if s.payment_status == "paid" or s.status == "complete":
                await _mark_payment_paid(session_id, s.payment_intent)
                tx = await db.payment_transactions.find_one({"session_id": session_id})
        except _stripe.error.StripeError:
            pass
    return {
        "session_id": session_id,
        "status": tx.get("status"),
        "payment_status": tx.get("payment_status"),
        "appointment_id": tx.get("appointment_id"),
    }


@router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = _stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except _stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")
    # Normalize Stripe object → plain dict so `.get` never crashes on unexpected shapes
    raw = event["data"]["object"]
    obj = raw.to_dict_recursive() if hasattr(raw, "to_dict_recursive") else (dict(raw) if hasattr(raw, "keys") else {})
    t = event["type"]
    try:
        if t == "checkout.session.completed":
            if obj.get("payment_status") == "paid":
                await _mark_payment_paid(obj.get("id"), obj.get("payment_intent"))
        elif t == "checkout.session.async_payment_succeeded":
            await _mark_payment_paid(obj.get("id"), obj.get("payment_intent"))
        elif t in ("checkout.session.async_payment_failed", "checkout.session.expired"):
            new_status = "failed" if "failed" in t else "expired"
            await db.payment_transactions.update_one(
                {"session_id": obj.get("id")},
                {"$set": {"status": new_status, "payment_status": new_status, "updated_at": datetime.now(timezone.utc)}},
            )
            tx = await db.payment_transactions.find_one({"session_id": obj.get("id")})
            if tx and tx.get("appointment_id"):
                await db.appuntamenti.update_one(
                    {"_id": ObjectId(tx["appointment_id"]), "stato": "in_attesa_pagamento"},
                    {"$set": {"stato": "annullato", "annullato_motivo": f"payment_{new_status}"}},
                )
        elif t == "charge.refunded":
            pi = obj.get("payment_intent")
            if pi:
                await db.payment_transactions.update_one(
                    {"stripe_payment_intent_id": pi},
                    {"$set": {"status": "refunded", "payment_status": "refunded", "updated_at": datetime.now(timezone.utc)}},
                )
    except Exception as e:
        # Never 500 to Stripe — log and ack so it won't retry aggressively
        import logging as _lg
        _lg.error(f"[STRIPE][WEBHOOK] handler error for event={t}: {e}", exc_info=True)
    return {"status": "ok"}


@router.get("/therapist/earnings")
async def therapist_earnings(user: dict = Depends(require_auth)):
    """Therapist earnings breakdown (paid = 70% of paid sessions)."""
    if user["role"] != "terapeuta":
        raise HTTPException(403, "Solo i terapeuti possono vedere gli incassi")
    terapista = await db.terapisti.find_one({"user_id": user["_id"]})
    if not terapista:
        try:
            terapista = await db.terapisti.find_one({"user_id": ObjectId(user["_id"])})
        except Exception:
            terapista = None
    if not terapista:
        raise HTTPException(404, "Profilo terapeuta non trovato")
    tid = str(terapista["_id"])
    pipeline = [
        {"$match": {"terapeuta_id": tid, "payment_status": "paid"}},
        {"$group": {
            "_id": "$payout_status",
            "total_therapist_amount": {"$sum": "$therapist_amount"},
            "total_platform_fee": {"$sum": "$platform_fee_amount"},
            "count": {"$sum": 1},
        }},
    ]
    result = {"paid_out": 0, "pending_payout": 0, "sessions_count": 0, "platform_fee_total": 0}
    async for row in db.payment_transactions.aggregate(pipeline):
        if row["_id"] == "paid":
            result["paid_out"] = row["total_therapist_amount"]
        else:
            result["pending_payout"] += row["total_therapist_amount"]
        result["sessions_count"] += row["count"]
        result["platform_fee_total"] += row["total_platform_fee"]
    return result


# ─── Admin Payouts & Fatture ─────────────────────────────────────────────────
@router.get("/admin/payouts")
async def list_admin_payouts(
    payout_status: Optional[str] = None,
    terapeuta_id: Optional[str] = None,
    user: dict = Depends(require_admin),
):
    """List paid payment_transactions to help admin plan bonifici to therapists."""
    q = {"payment_status": "paid"}
    if payout_status in ("pending", "paid"):
        q["payout_status"] = payout_status
    if terapeuta_id:
        q["terapeuta_id"] = terapeuta_id

    items = []
    async for tx in db.payment_transactions.find(q).sort("paid_at", -1).limit(500):
        t = await db.terapisti.find_one({"_id": ObjectId(tx["terapeuta_id"])})
        p = await db.pazienti.find_one({"_id": ObjectId(tx["paziente_id"])})
        items.append({
            "id": str(tx["_id"]),
            "session_id": tx.get("session_id"),
            "appointment_id": tx.get("appointment_id"),
            "amount": tx.get("amount"),
            "platform_fee_amount": tx.get("platform_fee_amount"),
            "therapist_amount": tx.get("therapist_amount"),
            "marca_da_bollo_amount": tx.get("marca_da_bollo_amount", 0),
            "opposizione_ts": tx.get("opposizione_ts", False),
            "payout_status": tx.get("payout_status"),
            "payout_date": (tx.get("payout_date").isoformat() if tx.get("payout_date") else None),
            "payout_reference": tx.get("payout_reference"),
            "paid_at": (tx.get("paid_at").isoformat() if tx.get("paid_at") else None),
            "terapeuta": {
                "id": tx.get("terapeuta_id"),
                "nome": t.get("nome") if t else "—",
                "cognome": t.get("cognome") if t else "",
                "iban": t.get("iban") if t else None,
            },
            "paziente_initials": (
                (p.get("nome", "?")[0] + "." + p.get("cognome", "?")[0] + ".") if p else "—"
            ),
        })

    summary = {}
    for it in items:
        tid = it["terapeuta"]["id"]
        s = summary.setdefault(tid, {
            "terapeuta": it["terapeuta"],
            "pending_amount": 0,
            "paid_amount": 0,
            "sessions_count": 0,
        })
        if it["payout_status"] == "paid":
            s["paid_amount"] += it["therapist_amount"] or 0
        else:
            s["pending_amount"] += it["therapist_amount"] or 0
        s["sessions_count"] += 1

    return {"items": items, "summary": list(summary.values())}


@router.post("/admin/payouts/mark-paid")
async def mark_payouts_paid(body: MarkPayoutPaidRequest, user: dict = Depends(require_admin)):
    """Mark a batch of transactions as payout=paid."""
    ids = [ObjectId(x) for x in body.transaction_ids if x]
    if not ids:
        raise HTTPException(400, "Nessuna transazione selezionata")
    now = datetime.now(timezone.utc)
    result = await db.payment_transactions.update_many(
        {"_id": {"$in": ids}, "payment_status": "paid", "payout_status": {"$ne": "paid"}},
        {"$set": {
            "payout_status": "paid",
            "payout_date": now,
            "payout_reference": (body.payout_reference or "").strip()[:120],
            "payout_marked_by": user["_id"],
        }},
    )
    return {"marked": result.modified_count}


@router.post("/admin/refunds")
async def create_refund(body: RefundRequest, user: dict = Depends(require_admin)):
    """Refund a paid transaction via Stripe. Cancels associated appointment.

    Only allowed on transactions where payment_status='paid' AND payout_status != 'paid'
    (once BIDOC has paid the therapist, refund must be manual/agreed with the pro).
    """
    try:
        tx = await db.payment_transactions.find_one({"_id": ObjectId(body.transaction_id)})
    except Exception:
        raise HTTPException(400, "ID transazione non valido")
    if not tx:
        raise HTTPException(404, "Transazione non trovata")
    if tx.get("payment_status") != "paid":
        raise HTTPException(400, "Solo le transazioni pagate possono essere rimborsate")
    if tx.get("payout_status") == "paid":
        raise HTTPException(400, "Rimborso non consentito: il payout al terapista è già stato eseguito. Contatta il terapista per il recupero.")
    if tx.get("status") == "refunded":
        raise HTTPException(400, "Già rimborsata")

    pi = tx.get("stripe_payment_intent_id")
    if not pi:
        raise HTTPException(400, "Manca payment_intent_id — impossibile procedere via Stripe")

    valid_reasons = {"requested_by_customer", "duplicate", "fraudulent"}
    reason = body.reason if body.reason in valid_reasons else "requested_by_customer"

    now = datetime.now(timezone.utc)
    try:
        refund = _stripe.Refund.create(
            payment_intent=pi,
            reason=reason,
            metadata={
                "admin_user_id": user["_id"],
                "admin_note": (body.admin_note or "")[:400],
                "transaction_id": body.transaction_id,
            },
            idempotency_key=f"refund-{body.transaction_id}",
        )
    except _stripe.error.StripeError as e:
        logging.error(f"[REFUND] Stripe error tx={body.transaction_id}: {e}")
        raise HTTPException(502, f"Stripe: {e.user_message or str(e)}")

    # Persist refund locally
    await db.payment_transactions.update_one(
        {"_id": ObjectId(body.transaction_id)},
        {"$set": {
            "status": "refunded",
            "payment_status": "refunded",
            "payout_status": "cancelled",
            "refunded_at": now,
            "refund_reason": reason,
            "refund_admin_note": (body.admin_note or "")[:400],
            "refund_admin_id": user["_id"],
            "stripe_refund_id": refund.id,
            "updated_at": now,
        }},
    )

    # Cancel appointment
    appt_id = tx.get("appointment_id")
    if appt_id:
        try:
            await db.appuntamenti.update_one(
                {"_id": ObjectId(appt_id), "stato": {"$nin": ["cancellato", "annullato"]}},
                {"$set": {
                    "stato": "cancellato",
                    "cancellato_at": now,
                    "cancellato_motivo": "rimborsato",
                }},
            )
        except Exception as e:
            logging.warning(f"[REFUND] appointment cancel failed: {e}")

    logging.info(f"[REFUND] tx={body.transaction_id} refund_id={refund.id} amount={tx.get('amount')}")
    return {
        "message": "Rimborso eseguito",
        "refund_id": refund.id,
        "amount": tx.get("amount"),
        "status": "refunded",
    }


@router.get("/admin/fattura-sanitaria/{transaction_id}")
async def download_fattura_sanitaria(transaction_id: str, user: dict = Depends(require_admin)):
    """Generate a PDF fattura sanitaria for a paid transaction."""
    tx = await db.payment_transactions.find_one({"_id": ObjectId(transaction_id), "payment_status": "paid"})
    if not tx:
        raise HTTPException(404, "Transazione non trovata o non pagata")
    appt = await db.appuntamenti.find_one({"_id": ObjectId(tx["appointment_id"])})
    terapista = await db.terapisti.find_one({"_id": ObjectId(tx["terapeuta_id"])})
    paziente = await db.pazienti.find_one({"_id": ObjectId(tx["paziente_id"])})
    paziente_user = await find_user_by_id(tx["paziente_user_id"])
    if not (appt and terapista and paziente and paziente_user):
        raise HTTPException(404, "Dati incompleti per generare la fattura")
    # Fiscal completeness check — required by law
    missing = []
    if not (terapista.get("partita_iva") or "").strip():
        missing.append("Partita IVA del terapista")
    if not (terapista.get("codice_fiscale") or "").strip():
        missing.append("Codice Fiscale del terapista")
    if not (paziente.get("codice_fiscale") or "").strip():
        missing.append("Codice Fiscale del paziente")
    if missing:
        raise HTTPException(422, f"Impossibile emettere la fattura: manca {', '.join(missing)}. Aggiorna il profilo prima di procedere.")
    pdf = build_fattura_sanitaria_pdf(
        tx=tx, appt=appt, terapista=terapista, paziente=paziente, paziente_user=paziente_user,
    )
    filename = f"fattura-sanitaria-{transaction_id[:8]}.pdf"
    return _FastResponse(content=pdf, media_type="application/pdf",
                         headers={"Content-Disposition": f'inline; filename="{filename}"'})


@router.get("/admin/fattura-commissione/{terapeuta_id}/{year}/{month}")
async def download_fattura_commissione(terapeuta_id: str, year: int, month: int, user: dict = Depends(require_admin)):
    """Generate a monthly commission invoice PDF (BIDOC → therapist)."""
    if not (2020 <= year <= 2100 and 1 <= month <= 12):
        raise HTTPException(400, "Periodo invalido")
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    if month == 12:
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
    terapista = await db.terapisti.find_one({"_id": ObjectId(terapeuta_id)})
    if not terapista:
        raise HTTPException(404, "Terapista non trovato")
    if not (terapista.get("partita_iva") or "").strip():
        raise HTTPException(422, "Impossibile emettere la fattura di commissione: manca la Partita IVA del terapista.")
    txs = []
    async for tx in db.payment_transactions.find({
        "terapeuta_id": terapeuta_id,
        "payment_status": "paid",
        "paid_at": {"$gte": start, "$lt": end},
    }).sort("paid_at", 1):
        p = await db.pazienti.find_one({"_id": ObjectId(tx["paziente_id"])})
        tx["paziente_initials"] = (p.get("nome", "?")[0] + "." + p.get("cognome", "?")[0] + ".") if p else "—"
        txs.append(tx)
    if not txs:
        raise HTTPException(404, "Nessuna sessione pagata nel periodo indicato")
    pdf = build_fattura_commissione_pdf(terapista=terapista, transactions=txs, year=year, month=month)
    filename = f"fattura-commissione-{year}-{month:02d}-{terapeuta_id[:6]}.pdf"
    return _FastResponse(content=pdf, media_type="application/pdf",
                         headers={"Content-Disposition": f'inline; filename="{filename}"'})
