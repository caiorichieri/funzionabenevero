"""Session cancellation with configurable refund policy.

Policy (hours before session → refund %):
- >= HOURS_FULL_REFUND (default 24h): 100% refund
- >= HOURS_PARTIAL_REFUND (default 12h): PARTIAL_PCT % (default 50)
- < HOURS_PARTIAL_REFUND: 0% (no refund)

Overridable via env vars: CANCEL_HOURS_FULL, CANCEL_HOURS_PARTIAL, CANCEL_PARTIAL_PCT.
Applied only on patient-initiated cancellations. Admin can always issue full refund.
"""
import logging
import os
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

import stripe as _stripe
from deps import db, require_auth
from email_service import _send_raw, SENDER_EMAIL

router = APIRouter()
logger = logging.getLogger(__name__)

_stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")


def _policy():
    return {
        "hours_full": int(os.environ.get("CANCEL_HOURS_FULL", "24")),
        "hours_partial": int(os.environ.get("CANCEL_HOURS_PARTIAL", "12")),
        "partial_pct": int(os.environ.get("CANCEL_PARTIAL_PCT", "50")),
    }


def _compute_refund_pct(data_ora: str) -> tuple[int, float]:
    """Return (refund_pct, hours_before) based on time-to-session."""
    p = _policy()
    try:
        start = datetime.fromisoformat(data_ora.replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        hours = (start - datetime.now(timezone.utc)).total_seconds() / 3600
    except Exception:
        return 0, 0
    if hours >= p["hours_full"]:
        return 100, hours
    if hours >= p["hours_partial"]:
        return p["partial_pct"], hours
    return 0, hours


@router.get("/cancella-policy")
async def get_cancel_policy():
    """Public: cancellation policy for display in booking flow / T&C."""
    p = _policy()
    return {
        "hours_full_refund": p["hours_full"],
        "hours_partial_refund": p["hours_partial"],
        "partial_refund_pct": p["partial_pct"],
        "description": (
            f"Rimborso 100% se annulli almeno {p['hours_full']} ore prima; "
            f"rimborso {p['partial_pct']}% tra {p['hours_partial']} e {p['hours_full']} ore prima; "
            f"nessun rimborso se annulli meno di {p['hours_partial']} ore prima."
        ),
    }


@router.get("/appuntamenti/{app_id}/preview-cancellazione")
async def preview_cancellation(app_id: str, user: dict = Depends(require_auth)):
    """Preview refund amount before confirming cancellation."""
    if user["role"] != "paziente":
        raise HTTPException(403, "Solo pazienti possono annullare")
    try:
        app = await db.appuntamenti.find_one({"_id": ObjectId(app_id)})
    except Exception:
        raise HTTPException(404, "Appuntamento non trovato")
    if not app:
        raise HTTPException(404, "Appuntamento non trovato")
    paziente = await db.pazienti.find_one({"user_id": user["_id"]})
    if not paziente or str(paziente["_id"]) != app.get("paziente_id"):
        raise HTTPException(403, "Non autorizzato")
    if app.get("stato") in ("cancellato", "annullato", "completato"):
        raise HTTPException(400, "Impossibile annullare questo appuntamento")

    pct, hours = _compute_refund_pct(app["data_ora"])
    tx = await db.payment_transactions.find_one({"appointment_id": app_id, "payment_status": "paid"})
    amount_paid = float(tx["amount"]) if tx and tx.get("amount") else 0.0
    refund_amount = round(amount_paid * pct / 100, 2)
    return {
        "hours_before": round(hours, 2),
        "refund_pct": pct,
        "refund_amount": refund_amount,
        "amount_paid": amount_paid,
        "policy": _policy(),
    }


@router.post("/appuntamenti/{app_id}/cancella")
async def cancel_by_patient(app_id: str, user: dict = Depends(require_auth)):
    """Patient-initiated cancellation with automatic refund calculation."""
    if user["role"] != "paziente":
        raise HTTPException(403, "Solo pazienti possono annullare")
    try:
        app = await db.appuntamenti.find_one({"_id": ObjectId(app_id)})
    except Exception:
        raise HTTPException(404, "Appuntamento non trovato")
    if not app:
        raise HTTPException(404, "Appuntamento non trovato")
    paziente = await db.pazienti.find_one({"user_id": user["_id"]})
    if not paziente or str(paziente["_id"]) != app.get("paziente_id"):
        raise HTTPException(403, "Non autorizzato")
    if app.get("stato") in ("cancellato", "annullato", "completato"):
        raise HTTPException(400, "Impossibile annullare questo appuntamento")

    pct, hours = _compute_refund_pct(app["data_ora"])
    tx = await db.payment_transactions.find_one({"appointment_id": app_id, "payment_status": "paid"})
    amount_paid = float(tx["amount"]) if tx and tx.get("amount") else 0.0
    refund_amount = round(amount_paid * pct / 100, 2)
    now = datetime.now(timezone.utc)

    stripe_refund_id = None
    if pct > 0 and tx and tx.get("stripe_payment_intent_id"):
        if tx.get("payout_status") == "paid":
            logger.warning(f"[CANCEL] cannot refund tx={tx['_id']}: payout already paid")
        else:
            try:
                r = _stripe.Refund.create(
                    payment_intent=tx["stripe_payment_intent_id"],
                    amount=int(refund_amount * 100),
                    reason="requested_by_customer",
                    metadata={"appointment_id": app_id, "user_initiated": "true", "refund_pct": str(pct)},
                    idempotency_key=f"cancel-{app_id}",
                )
                stripe_refund_id = r.id
                await db.payment_transactions.update_one(
                    {"_id": tx["_id"]},
                    {"$set": {
                        "status": "refunded" if pct == 100 else "partially_refunded",
                        "payment_status": "refunded" if pct == 100 else "partially_refunded",
                        "payout_status": "cancelled",
                        "refunded_at": now, "refund_amount": refund_amount,
                        "stripe_refund_id": r.id, "updated_at": now,
                    }},
                )
            except Exception as e:
                logger.error(f"[CANCEL] Stripe refund failed: {e}")
                raise HTTPException(502, "Errore durante il rimborso. Contatta il supporto.")

    await db.appuntamenti.update_one(
        {"_id": ObjectId(app_id)},
        {"$set": {
            "stato": "cancellato",
            "cancellato_at": now,
            "cancellato_motivo": f"paziente-{pct}pct",
            "cancellato_by": user["_id"],
            "hours_before_cancellation": round(hours, 2),
            "refund_pct": pct,
            "refund_amount": refund_amount,
        }},
    )

    # Notify therapist
    try:
        terapista = await db.terapisti.find_one({"_id": ObjectId(app["terapeuta_id"])})
        t_user = await db.users.find_one({"_id": ObjectId(terapista.get("user_id"))}) if terapista else None
        if t_user and t_user.get("email"):
            await _send_raw({
                "from": f"FunzionaBene <{SENDER_EMAIL}>",
                "to": [t_user["email"]],
                "subject": f"Sessione annullata: {app['data_ora'][:16]}",
                "html": f"<p>Ciao {terapista.get('nome','')}, la sessione del {app['data_ora'][:16]} è stata annullata dal paziente ({round(hours,1)}h prima). Rimborso applicato: {pct}%.</p>",
            })
    except Exception as e:
        logger.error(f"[CANCEL] therapist notification failed: {e}")

    return {
        "message": "Sessione annullata",
        "refund_pct": pct,
        "refund_amount": refund_amount,
        "hours_before": round(hours, 2),
        "stripe_refund_id": stripe_refund_id,
    }
