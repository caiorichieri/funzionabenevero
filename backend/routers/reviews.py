"""Reviews (recensioni) for therapists, submitted by patients after completed sessions.

Approval workflow: patient submits → status=pending → admin reviews → approved/rejected.
Only approved reviews are visible on public therapist profile.
"""
import logging
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from deps import db, require_auth, require_admin

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/reviews/pending-appointments")
async def my_pending_review_appointments(user: dict = Depends(require_auth)):
    """List completed appointments for which the current patient hasn't yet left a review."""
    if user["role"] != "paziente":
        raise HTTPException(403, "Solo pazienti")
    paziente = await db.pazienti.find_one({"user_id": user["_id"]})
    if not paziente:
        return []
    reviewed_ids = set()
    async for r in db.reviews.find({"paziente_id": user["_id"]}, {"appuntamento_id": 1}):
        if r.get("appuntamento_id"):
            reviewed_ids.add(r["appuntamento_id"])
    now = datetime.now(timezone.utc)
    out = []
    async for a in db.appuntamenti.find({
        "paziente_id": str(paziente["_id"]),
        "stato": {"$nin": ["cancellato", "annullato"]},
    }).sort("data_ora", -1):
        try:
            start = datetime.fromisoformat(a["data_ora"].replace("Z", "+00:00"))
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if start > now:
            continue  # session in the future
        aid = str(a["_id"])
        if aid in reviewed_ids:
            continue
        t = await db.terapisti.find_one({"_id": ObjectId(a["terapeuta_id"])})
        out.append({
            "appuntamento_id": aid,
            "data_ora": a["data_ora"],
            "terapista_id": a["terapeuta_id"],
            "terapista_nome": t.get("nome", "") if t else "",
            "terapista_cognome": t.get("cognome", "") if t else "",
        })
    return out


@router.post("/reviews")
async def submit_review(body: dict, user: dict = Depends(require_auth)):
    """Patient submits a review for a completed appointment. Starts as status=pending."""
    if user["role"] != "paziente":
        raise HTTPException(403, "Solo pazienti")
    app_id = body.get("appuntamento_id")
    voto = int(body.get("voto", 0))
    testo = (body.get("testo") or "").strip()[:2000]
    if not app_id or voto < 1 or voto > 5:
        raise HTTPException(400, "appuntamento_id e voto (1-5) richiesti")
    try:
        app = await db.appuntamenti.find_one({"_id": ObjectId(app_id)})
    except Exception:
        raise HTTPException(404, "Appuntamento non trovato")
    if not app:
        raise HTTPException(404, "Appuntamento non trovato")
    paziente = await db.pazienti.find_one({"user_id": user["_id"]})
    if not paziente or str(paziente["_id"]) != app.get("paziente_id"):
        raise HTTPException(403, "Non autorizzato")
    if app.get("stato") in ("cancellato", "annullato"):
        raise HTTPException(400, "Non puoi recensire una sessione annullata")
    # Session must be in the past
    try:
        start = datetime.fromisoformat(app["data_ora"].replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        if start > datetime.now(timezone.utc):
            raise HTTPException(400, "Attendi la fine della sessione per recensire")
    except HTTPException:
        raise
    except Exception:
        pass
    # One review per appointment
    existing = await db.reviews.find_one({"appuntamento_id": app_id, "paziente_id": user["_id"]})
    if existing:
        raise HTTPException(400, "Hai già recensito questa sessione")

    now = datetime.now(timezone.utc)
    r = await db.reviews.insert_one({
        "appuntamento_id": app_id,
        "terapista_id": app["terapeuta_id"],
        "paziente_id": user["_id"],
        "voto": voto,
        "testo": testo,
        "status": "pending",
        "created_at": now,
        "moderato_at": None,
        "moderato_by": None,
        "moderato_motivo": None,
    })
    return {"message": "Recensione inviata, in attesa di approvazione", "review_id": str(r.inserted_id)}


@router.get("/reviews/terapista/{terapista_id}")
async def public_reviews(terapista_id: str, limit: int = 20):
    """Public: approved reviews for a therapist's public profile."""
    out = []
    async for r in db.reviews.find(
        {"terapista_id": terapista_id, "status": "approved"},
    ).sort("moderato_at", -1).limit(limit):
        # Fetch patient first name only (privacy)
        p_user = await db.users.find_one({"_id": ObjectId(r["paziente_id"])})
        first_name = (p_user.get("nome", "") if p_user else "").split()[0] or "Paziente"
        out.append({
            "voto": r.get("voto"),
            "testo": r.get("testo"),
            "created_at": r.get("moderato_at").isoformat() if r.get("moderato_at") else r.get("created_at").isoformat(),
            "paziente_nome": first_name,
        })
    # Aggregate rating
    total = await db.reviews.count_documents({"terapista_id": terapista_id, "status": "approved"})
    avg_cursor = db.reviews.aggregate([
        {"$match": {"terapista_id": terapista_id, "status": "approved"}},
        {"$group": {"_id": None, "avg": {"$avg": "$voto"}}},
    ])
    avg = 0
    async for a in avg_cursor:
        avg = round(a["avg"], 1)
    return {"reviews": out, "total": total, "avg_rating": avg}


# ─── Admin moderation ─────────────────────────────────────────────────────────
@router.get("/admin/reviews/pending")
async def admin_list_pending(user: dict = Depends(require_admin)):
    """List reviews awaiting moderation."""
    out = []
    async for r in db.reviews.find({"status": "pending"}).sort("created_at", 1):
        t = await db.terapisti.find_one({"_id": ObjectId(r["terapista_id"])})
        p_user = await db.users.find_one({"_id": ObjectId(r["paziente_id"])})
        out.append({
            "review_id": str(r["_id"]),
            "voto": r.get("voto"),
            "testo": r.get("testo"),
            "created_at": r["created_at"].isoformat(),
            "terapista": {
                "id": r["terapista_id"],
                "nome": t.get("nome", "") if t else "",
                "cognome": t.get("cognome", "") if t else "",
            },
            "paziente": {
                "email": p_user.get("email", "") if p_user else "",
                "nome": p_user.get("nome", "") if p_user else "",
            },
        })
    return out


@router.post("/admin/reviews/{review_id}/approve")
async def admin_approve(review_id: str, user: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    r = await db.reviews.update_one(
        {"_id": ObjectId(review_id), "status": "pending"},
        {"$set": {"status": "approved", "moderato_at": now, "moderato_by": user["_id"]}},
    )
    if r.modified_count == 0:
        raise HTTPException(404, "Recensione non trovata o già moderata")
    return {"message": "Approvata"}


@router.post("/admin/reviews/{review_id}/reject")
async def admin_reject(review_id: str, body: dict, user: dict = Depends(require_admin)):
    motivo = (body.get("motivo") or "").strip()[:400]
    now = datetime.now(timezone.utc)
    r = await db.reviews.update_one(
        {"_id": ObjectId(review_id), "status": "pending"},
        {"$set": {"status": "rejected", "moderato_at": now, "moderato_by": user["_id"], "moderato_motivo": motivo}},
    )
    if r.modified_count == 0:
        raise HTTPException(404, "Recensione non trovata o già moderata")
    return {"message": "Rifiutata"}


@router.get("/admin/reviews/count-pending")
async def admin_count_pending(user: dict = Depends(require_admin)):
    """For badge in admin sidebar."""
    cnt = await db.reviews.count_documents({"status": "pending"})
    return {"count": cnt}
