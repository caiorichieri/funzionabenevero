"""Calendario router: date-specific availability per therapist + admin aggregated view + reschedule flow."""
import hashlib
import logging
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, List

from deps import db, require_auth, require_admin, find_user_by_id

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
    """Return therapist's date-specific availability + booked appointments + publish status."""
    if user["role"] != "terapeuta":
        raise HTTPException(403, "Accesso negato")
    t = await db.terapisti.find_one({"user_id": user["_id"]})
    if not t:
        raise HTTPException(404, "Profilo terapeuta non trovato")

    tid = str(t["_id"])
    # Fetch upcoming appointments (next 90 days) with patient names
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=90)
    appuntamenti_map: Dict[str, List[Dict]] = {}
    cursor = db.appuntamenti.find({
        "terapeuta_id": tid,
        "stato": {"$nin": ["cancellato", "annullato"]},
        "data_ora": {"$gte": now.isoformat()[:10], "$lt": horizon.isoformat()[:10]},
    })
    async for a in cursor:
        date_key = a["data_ora"][:10]
        ora = a["data_ora"][11:16]
        pnome = "Paziente"
        try:
            p = await db.pazienti.find_one({"_id": ObjectId(a["paziente_id"])})
            if p:
                pnome = f"{p.get('nome','')} {p.get('cognome','')}".strip() or "Paziente"
        except Exception:
            pass
        appuntamenti_map.setdefault(date_key, []).append({
            "id": str(a["_id"]),
            "ora": ora,
            "paziente_nome": pnome,
            "stato": a.get("stato", "confermato"),
        })

    return {
        "calendario": t.get("disponibilita_calendario", {}),
        "appuntamenti": appuntamenti_map,
        "calendario_pubblicato_at": (
            t["calendario_pubblicato_at"].isoformat() if isinstance(t.get("calendario_pubblicato_at"), datetime) else None
        ),
        "calendario_bozza": bool(t.get("calendario_bozza")),
        "durata_sessione_minuti": 50,
    }


@router.put("/terapisti/me/calendario")
async def update_my_calendario(body: CalendarioUpdate, user: dict = Depends(require_auth)):
    """Update calendar (batch). If pubblica=True → status live; else bozza.
    Filtra silenziosamente gli slot passati o entro 2 ore da adesso."""
    if user["role"] != "terapeuta":
        raise HTTPException(403, "Accesso negato")
    cleaned, dropped = _clean_calendar_payload(body.calendario or {})
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
        "dropped_past_slots": dropped,
    }


def _clean_calendar_payload(raw: Dict[str, List[str]]) -> tuple:
    """Validate + drop past slots. Returns (cleaned_dict, dropped_count)."""
    min_slot_time = datetime.now(timezone.utc) + timedelta(hours=2)
    cleaned: Dict[str, List[str]] = {}
    dropped = 0
    for date_key, slots in (raw or {}).items():
        if not _valid_iso_date(date_key):
            raise HTTPException(400, f"Formato data invalido: {date_key}")
        if not isinstance(slots, list):
            raise HTTPException(400, f"Slot per {date_key} deve essere una lista")
        valid_slots = []
        for s in slots:
            if not _valid_hhmm(s):
                raise HTTPException(400, f"Orario invalido: {s} (usa HH:MM)")
            try:
                y, m, d = date_key.split("-")
                h, mn = s.split(":")
                slot_dt = datetime(int(y), int(m), int(d), int(h), int(mn), tzinfo=timezone.utc)
            except Exception:
                raise HTTPException(400, f"Data/ora invalida: {date_key} {s}")
            if slot_dt < min_slot_time:
                dropped += 1
                continue
            valid_slots.append(s)
        if valid_slots:
            cleaned[date_key] = sorted(set(valid_slots))
    return cleaned, dropped


@router.put("/admin/terapisti/{terapista_id}/calendario")
async def admin_update_calendario(terapista_id: str, body: CalendarioUpdate, user: dict = Depends(require_admin)):
    """Admin: override any therapist's calendar (support/onboarding tool).
    Applies the same slot validation and past-slot filtering as the therapist self endpoint.
    Note: therapist `_id` in DB may be stored as string OR ObjectId — try both."""
    cleaned, dropped = _clean_calendar_payload(body.calendario or {})
    now = datetime.now(timezone.utc)
    update = {
        "disponibilita_calendario": cleaned,
        "calendario_updated_at": now,
        "calendario_bozza": not body.pubblica,
    }
    if body.pubblica:
        update["calendario_pubblicato_at"] = now
    # Try ObjectId first, then string _id (some seeded docs use string)
    result = None
    try:
        result = await db.terapisti.update_one({"_id": ObjectId(terapista_id)}, {"$set": update})
        matched = result.matched_count
    except Exception:
        matched = 0
    if matched == 0:
        result = await db.terapisti.update_one({"_id": terapista_id}, {"$set": update})
        matched = result.matched_count
    if matched == 0:
        raise HTTPException(404, "Terapista non trovato")
    return {
        "message": "Calendario aggiornato",
        "terapista_id": terapista_id,
        "date_count": len(cleaned),
        "slot_count": sum(len(v) for v in cleaned.values()),
        "calendario_bozza": not body.pubblica,
        "calendario_pubblicato_at": now.isoformat() if body.pubblica else None,
        "dropped_past_slots": dropped,
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
    """Return day-by-day count of therapists with any availability + booked appointments for the given month.
    Admin vede ANCHE i calendari in bozza (badge) e TUTTE le prenotazioni attive."""
    if not (1 <= mese <= 12) or not (2020 <= anno <= 2100):
        raise HTTPException(400, "Anno/mese invalido")

    start = datetime(anno, mese, 1, tzinfo=timezone.utc)
    if mese == 12:
        end = datetime(anno + 1, 1, 1, tzinfo=timezone.utc)
    else:
        end = datetime(anno, mese + 1, 1, tzinfo=timezone.utc)

    days_in_month: Dict[str, Dict] = {}
    d = start
    while d < end:
        days_in_month[d.strftime("%Y-%m-%d")] = {
            "terapisti_count": 0,
            "slot_count": 0,
            "appuntamenti_count": 0,
            "terapisti": [],
            "appuntamenti": [],
        }
        d += timedelta(days=1)

    # 1) Availability slots — include ALL therapists (admin view), flag bozza status
    cursor = db.terapisti.find(
        {},
        {"nome": 1, "cognome": 1, "disponibilita_calendario": 1, "calendario_bozza": 1, "documenti_verificati": 1},
    )
    async for t in cursor:
        cal = t.get("disponibilita_calendario") or {}
        if not cal:
            continue
        nome = f"{t.get('nome','')} {t.get('cognome','')}".strip() or "—"
        for date_key, slots in cal.items():
            if date_key in days_in_month and slots:
                days_in_month[date_key]["terapisti_count"] += 1
                days_in_month[date_key]["slot_count"] += len(slots)
                days_in_month[date_key]["terapisti"].append({
                    "id": str(t["_id"]),
                    "nome": nome,
                    "slots": sorted(slots),
                    "bozza": bool(t.get("calendario_bozza")),
                    "documenti_verificati": bool(t.get("documenti_verificati")),
                })

    # 2) Booked appointments — enrich with patient + therapist names
    start_iso = start.isoformat()[:10]
    end_iso = end.isoformat()[:10]
    async for a in db.appuntamenti.find({
        "stato": {"$in": ["confermato", "prenotato", "completato"]},
        "data_ora": {"$gte": start_iso, "$lt": end_iso},
    }):
        data_ora = a.get("data_ora", "")
        date_key = data_ora[:10]
        ora = data_ora[11:16]
        if date_key not in days_in_month:
            continue

        # Names lookup (best-effort)
        pnome, tnome = "—", "—"
        try:
            p = await db.pazienti.find_one({"_id": ObjectId(a["paziente_id"])})
            if p:
                pnome = f"{p.get('nome','')} {p.get('cognome','')}".strip() or "Paziente"
        except Exception:
            pass
        try:
            t = await db.terapisti.find_one({"_id": ObjectId(a["terapeuta_id"])})
            if t:
                tnome = f"{t.get('nome','')} {t.get('cognome','')}".strip() or "Terapista"
        except Exception:
            pass

        days_in_month[date_key]["appuntamenti_count"] += 1
        days_in_month[date_key]["appuntamenti"].append({
            "id": str(a["_id"]),
            "ora": ora,
            "terapeuta_id": a.get("terapeuta_id"),
            "terapeuta_nome": tnome,
            "paziente_nome": pnome,
            "stato": a.get("stato"),
        })

    # Sort inner lists
    for v in days_in_month.values():
        v["appuntamenti"].sort(key=lambda x: x["ora"])

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
    try:
        t = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    except Exception:
        raise HTTPException(404, "Terapeuta non disponibile")
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

    min_slot_time = datetime.now(timezone.utc) + timedelta(hours=2)
    cal = t.get("disponibilita_calendario") or {}
    days_out = []
    d = start
    while d < end:
        date_key = d.strftime("%Y-%m-%d")
        raw_slots = cal.get(date_key, [])
        slots_out = []
        for hhmm in raw_slots:
            slot_dt = datetime(d.year, d.month, d.day, int(hhmm[:2]), int(hhmm[3:5]), tzinfo=timezone.utc)
            if slot_dt < min_slot_time:
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
    if nuova_dt <= now + timedelta(hours=2):
        raise HTTPException(400, "Scegli uno slot almeno 2 ore nel futuro")

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

    # Notify therapist by email (best-effort)
    try:
        terapista_user = await find_user_by_id(terapista.get("user_id"))
        paziente = await db.pazienti.find_one({"_id": ObjectId(appt["paziente_id"])})
        if terapista_user and paziente:
            from email_service import send_reschedule_notification_email
            await send_reschedule_notification_email(
                to_email=terapista_user["email"],
                to_nome=f"{terapista.get('nome','')}",
                paziente_nome=f"{paziente.get('nome','')} {paziente.get('cognome','')}".strip(),
                old_datetime_iso=appt["data_ora"],
                new_datetime_iso=nuova_dt.isoformat(),
                role="terapista",
            )
    except Exception as e:
        logging.warning(f"[RESCHEDULE] therapist notification failed: {e}")

    return {
        "message": "Appuntamento riprogrammato con successo",
        "old_appuntamento_id": str(appt["_id"]),
        "new_appuntamento_id": new_id,
        "nuova_data_ora": nuova_dt.isoformat(),
    }
