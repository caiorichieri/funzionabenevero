"""Calendario router: date-specific availability per therapist + admin aggregated view + reschedule flow."""
import hashlib
import logging
import secrets as _secrets
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, List, Optional

from deps import db, require_auth, require_admin

router = APIRouter()


# ─── Models ───────────────────────────────────────────────────────────────────
class DaySlots(BaseModel):
    """Slot list for a specific date: list of start times HH:MM."""
    slots: List[str]


class CalendarioUpdate(BaseModel):
    """Batch update: dict of ISO date → list of HH:MM slot start times."""
    calendario: Dict[str, List[str]]
    pubblica: bool = False  # if True, marks status "pubblicato"


class RiprogrammaConfirm(BaseModel):
    token: str
    nuova_data_ora: str  # ISO


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _valid_hhmm(s: str) -> bool:
    if not isinstance(s, str) or len(s) != 5 or s[2] != ":":
        return False
    try:
        h = int(s[0:2])
        m = int(s[3:5])
        return 0 <= h < 24 and 0 <= m < 60
    except ValueError:
        return False


def _valid_iso_date(s: str) -> bool:
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def _token_digest(raw: str) -> str:
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


# ─── Therapist endpoints ──────────────────────────────────────────────────────
@router.get("/terapisti/me/calendario")
async def get_my_calendario(user: dict = Depends(require_auth)):
    """Return therapist's date-specific availability + publish status."""
    if user["role"] != "terapeuta":
        raise HTTPException(403, "Accesso negato")
    t = await db.terapisti.find_one({"user_id": user["_id"]})
    if not t:
        raise HTTPException(404, "Profilo terapeuta non trovato")
    return {
        "calendario": t.get("disponibilita_calendario", {}),
        "calendario_pubblicato_at": (
            t["calendario_pubblicato_at"].isoformat() if isinstance(t.get("calendario_pubblicato_at"), datetime) else None
        ),
        "calendario_bozza": bool(t.get("calendario_bozza")),
        "durata_sessione_minuti": 50,
    }


@router.put("/terapisti/me/calendario")
async def update_my_calendario(body: CalendarioUpdate, user: dict = Depends(require_auth)):
    """Update calendar (batch). If pubblica=True → status live; else bozza."""
    if user["role"] != "terapeuta":
        raise HTTPException(403, "Accesso negato")
    # Validate input shape
    cleaned: Dict[str, List[str]] = {}
    for date_key, slots in (body.calendario or {}).items():
        if not _valid_iso_date(date_key):
            raise HTTPException(400, f"Formato data invalido: {date_key}")
        if not isinstance(slots, list):
            raise HTTPException(400, f"Slot per {date_key} deve essere una lista")
        valid_slots = []
        for s in slots:
            if not _valid_hhmm(s):
                raise HTTPException(400, f"Orario invalido: {s} (usa HH:MM)")
            valid_slots.append(s)
        # deduplicate + sort
        cleaned[date_key] = sorted(set(valid_slots))

    now = datetime.now(timezone.utc)
    update = {
        "disponibilita_calendario": cleaned,
        "calendario_updated_at": now,
        "calendario_bozza": not body.pubblica,
    }
    if body.pubblica:
        update["calendario_pubblicato_at"] = now
    await db.terapisti.update_one({"user_id": user["_id"]}, {"$set": update})
    return {
        "calendario": cleaned,
        "calendario_bozza": not body.pubblica,
        "calendario_pubblicato_at": now.isoformat() if body.pubblica else None,
    }


@router.post("/terapisti/me/calendario/pubblica")
async def pubblica_calendario(user: dict = Depends(require_auth)):
    """Publish the current draft calendar (make it visible to patients)."""
    if user["role"] != "terapeuta":
        raise HTTPException(403, "Accesso negato")
    now = datetime.now(timezone.utc)
    result = await db.terapisti.update_one(
        {"user_id": user["_id"]},
        {"$set": {"calendario_bozza": False, "calendario_pubblicato_at": now}},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Profilo non trovato")
    return {"message": "Calendario pubblicato", "pubblicato_at": now.isoformat()}


# ─── Admin: aggregated calendar ───────────────────────────────────────────────
@router.get("/admin/calendario")
async def admin_calendario(anno: int, mese: int, user: dict = Depends(require_admin)):
    """Return day-by-day count of therapists with any availability for the given month."""
    if not (1 <= mese <= 12) or not (2020 <= anno <= 2100):
        raise HTTPException(400, "Anno/mese invalido")

    # Compute all dates in month
    start = datetime(anno, mese, 1, tzinfo=timezone.utc)
    if mese == 12:
        end = datetime(anno + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(anno, mese + 1, 1, tzinfo=timezone.utc)

    days_in_month: Dict[str, Dict] = {}
    d = start
    while d < end:
        days_in_month[d.strftime("%Y-%m-%d")] = {"terapisti_count": 0, "slot_count": 0, "terapisti": []}
        d += timedelta(days=1)

    # Fetch published therapists
    cursor = db.terapisti.find(
        {"calendario_bozza": {"$ne": True}, "documenti_verificati": True},
        {"nome": 1, "cognome": 1, "disponibilita_calendario": 1},
    )
    async for t in cursor:
        cal = t.get("disponibilita_calendario") or {}
        nome = f"{t.get('nome','')} {t.get('cognome','')}".strip() or "—"
        for date_key, slots in cal.items():
            if date_key in days_in_month and slots:
                days_in_month[date_key]["terapisti_count"] += 1
                days_in_month[date_key]["slot_count"] += len(slots)
                days_in_month[date_key]["terapisti"].append({
                    "id": str(t["_id"]),
                    "nome": nome,
                    "slots": slots,
                })

    return {
        "anno": anno,
        "mese": mese,
        "days": [
            {"data": k, **v}
            for k, v in sorted(days_in_month.items())
        ],
    }


# ─── Public: booked slots for a therapist (to build /riprogramma UI) ─────────
@router.get("/public/terapisti/{terapista_id}/calendario")
async def public_terapista_calendario(terapista_id: str, anno: int, mese: int):
    """Public: return published availability for a therapist in a given month, with booked slots excluded."""
    if not (1 <= mese <= 12):
        raise HTTPException(400, "Mese invalido")
    t = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    if not t or t.get("calendario_bozza") or not t.get("documenti_verificati"):
        raise HTTPException(404, "Terapeuta non disponibile")

    start = datetime(anno, mese, 1, tzinfo=timezone.utc)
    if mese == 12:
        end = datetime(anno + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(anno, mese + 1, 1, tzinfo=timezone.utc)

    # Booked slots exclusion
    existing = await db.appuntamenti.find({
        "terapeuta_id": terapista_id,
        "stato": {"$nin": ["cancellato", "annullato"]},
        "data_ora": {"$gte": start.isoformat(), "$lt": end.isoformat()},
    }).to_list(500)
    booked = {a["data_ora"][:16] for a in existing}

    now = datetime.now(timezone.utc)
    cal = t.get("disponibilita_calendario") or {}
    days_out = []
    d = start
    while d < end:
        date_key = d.strftime("%Y-%m-%d")
        raw_slots = cal.get(date_key, [])
        slots_out = []
        for hhmm in raw_slots:
            slot_dt = datetime(d.year, d.month, d.day, int(hhmm[:2]), int(hhmm[3:5]), tzinfo=timezone.utc)
            if slot_dt <= now:
                continue
            key = slot_dt.isoformat()[:16]
            slots_out.append({
                "ora": hhmm,
                "data_ora": slot_dt.isoformat(),
                "disponibile": key not in booked,
            })
        if slots_out:
            days_out.append({"data": date_key, "slots": slots_out})
        d += timedelta(days=1)

    return {
        "terapista": {
            "id": str(t["_id"]),
            "nome": t.get("nome"),
            "cognome": t.get("cognome"),
        },
        "days": days_out,
    }


# ─── Reschedule: validate token & confirm ────────────────────────────────────
@router.get("/riprogramma/{appuntamento_id}/validate")
async def validate_reschedule_token(appuntamento_id: str, token: str):
    """Public: validate the signed reschedule token and return current appointment info."""
    digest = _token_digest(token)
    now = datetime.now(timezone.utc)
    appt = await db.appuntamenti.find_one({
        "_id": ObjectId(appuntamento_id),
        "riprogramma_token_hash": digest,
        "riprogramma_token_expires": {"$gt": now},
        "stato": {"$in": ["confermato", "prenotato"]},
    })
    if not appt:
        raise HTTPException(404, "Link non valido o scaduto. Contatta assistenza@funzionabene.it per un rimborso o supporto.")

    t = await db.terapisti.find_one({"_id": ObjectId(appt["terapeuta_id"])})
    p = await db.pazienti.find_one({"_id": ObjectId(appt["paziente_id"])})
    return {
        "appuntamento": {
            "id": str(appt["_id"]),
            "data_ora": appt["data_ora"],
            "durata_minuti": appt.get("durata_minuti", 50),
            "stato": appt["stato"],
        },
        "terapista": {
            "id": str(t["_id"]),
            "nome": t.get("nome"),
            "cognome": t.get("cognome"),
        } if t else None,
        "paziente_nome": f"{p.get('nome','')}" if p else "",
    }


@router.post("/riprogramma/{appuntamento_id}/confirm")
async def confirm_reschedule(appuntamento_id: str, body: RiprogrammaConfirm):
    """Public: cancel old appointment and create new one with same therapist. No refund."""
    digest = _token_digest(body.token)
    now = datetime.now(timezone.utc)
    appt = await db.appuntamenti.find_one({
        "_id": ObjectId(appuntamento_id),
        "riprogramma_token_hash": digest,
        "riprogramma_token_expires": {"$gt": now},
        "stato": {"$in": ["confermato", "prenotato"]},
    })
    if not appt:
        raise HTTPException(404, "Link non valido o scaduto")

    # Parse new datetime
    try:
        nuova_dt = datetime.fromisoformat(body.nuova_data_ora.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(400, "Data non valida")
    if nuova_dt.tzinfo is None:
        nuova_dt = nuova_dt.replace(tzinfo=timezone.utc)
    if nuova_dt <= now + timedelta(hours=1):
        raise HTTPException(400, "Scegli uno slot almeno 1 ora nel futuro")

    # Check the new slot is in therapist's published calendar
    terapista = await db.terapisti.find_one({"_id": ObjectId(appt["terapeuta_id"])})
    if not terapista or terapista.get("calendario_bozza"):
        raise HTTPException(404, "Terapista non disponibile")
    cal = terapista.get("disponibilita_calendario") or {}
    date_key = nuova_dt.strftime("%Y-%m-%d")
    hhmm = nuova_dt.strftime("%H:%M")
    if hhmm not in cal.get(date_key, []):
        raise HTTPException(400, "Slot non disponibile nel calendario del terapista")

    # Check slot not already booked
    existing = await db.appuntamenti.find_one({
        "terapeuta_id": appt["terapeuta_id"],
        "data_ora": {"$regex": f"^{nuova_dt.isoformat()[:16]}"},
        "stato": {"$nin": ["cancellato", "annullato"]},
        "_id": {"$ne": appt["_id"]},
    })
    if existing:
        raise HTTPException(409, "Slot appena prenotato da un altro utente. Ricarica la pagina.")

    # Mark old as cancelled and create new
    await db.appuntamenti.update_one(
        {"_id": appt["_id"]},
        {"$set": {
            "stato": "cancellato",
            "cancellato_at": now,
            "cancellato_motivo": "riprogrammato",
            "riprogramma_token_hash": None,  # consume token
            "riprogramma_token_expires": None,
        }},
    )
    new_doc = {
        "terapeuta_id": appt["terapeuta_id"],
        "paziente_id": appt["paziente_id"],
        "paziente_user_id": appt.get("paziente_user_id"),
        "data_ora": nuova_dt.isoformat(),
        "durata_minuti": appt.get("durata_minuti", 50),
        "tipo": appt.get("tipo", "online"),
        "tipologia": appt.get("tipologia"),
        "modalita": appt.get("modalita"),
        "stato": "confermato",
        "riprogrammato_da": str(appt["_id"]),
        "created_at": now,
        "paid_at": appt.get("paid_at"),
    }
    ins = await db.appuntamenti.insert_one(new_doc)
    new_id = str(ins.inserted_id)

    # Move payment_transactions reference to new appointment
    await db.payment_transactions.update_many(
        {"appointment_id": str(appt["_id"])},
        {"$set": {"appointment_id": new_id, "riprogrammato_at": now}},
    )

    logging.info(f"[RESCHEDULE] {appt['_id']} → {new_id} for terapista {appt['terapeuta_id']}")
    return {
        "message": "Appuntamento riprogrammato con successo",
        "old_appuntamento_id": str(appt["_id"]),
        "new_appuntamento_id": new_id,
        "nuova_data_ora": nuova_dt.isoformat(),
    }


def generate_reschedule_token_for_appt(appuntamento_id: str) -> str:
    """Utility (called from booking_service): generate a raw token, store hash on the appuntamento.
    Returns the RAW token to embed in email."""
    # This function is sync-oriented — the actual DB write happens inside the async caller.
    return _secrets.token_urlsafe(32)
