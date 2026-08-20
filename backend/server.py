from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / '.env')

import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Annotated

import bcrypt
import jwt
import secrets as _secrets
from bson import ObjectId
from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field, BeforeValidator, EmailStr, field_validator

from email_service import send_otp_email, send_booking_confirmation_email, send_reminder_email, send_password_reset_email
from daily_service import create_room_for_appointment, create_meeting_token, get_room_presenza
from sms_service import send_sms_otp, verify_sms_otp
from codicefiscale import codicefiscale

# ─── Shared config, DB, helpers, auth deps ─────────────────────────────────────
from deps import (
    JWT_SECRET, JWT_ALGORITHM, FRONTEND_URL,
    STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, PLATFORM_FEE_PERCENT,
    client, db,
    PyObjectId, hash_password, verify_password,
    create_access_token, create_refresh_token,
    generate_otp, validate_codice_fiscale,
    get_current_user, require_admin, require_auth, find_user_by_id,
)
# ─── Shared Pydantic models ───────────────────────────────────────────────────
from models import (
    RegisterInput, LoginInput, OTPInput,
    FormazioneItem, DisponibilitaItem,
    TerapistaProfileInput, PazienteProfileInput,
    AppuntamentoInput, AppuntamentoStatoInput,
    ArticoloInput, ConsentPrefs, ConsentLogInput,
    ContractInput, ContractAcceptInput,
    CheckoutBookingRequest, MarkPayoutPaidRequest,
)

# ─── FastAPI setup ────────────────────────────────────────────────────────────
app = FastAPI(title="FunzionaBene API")
api_router = APIRouter(prefix="/api")

UPLOADS_DIR = Path(__file__).parent / "uploads"

@api_router.get("/media/therapists/{filename}")
async def get_therapist_photo(filename: str):
    """Serve therapist photos. Whitelist-only for safety."""
    if "/" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")
    path = UPLOADS_DIR / "therapists" / filename
    if not path.exists():
        raise HTTPException(404, "Photo not found")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})

# ─── AUTH ROUTES ─────────────────────────────────────────────────────────────

# ─── TERAPISTI ────────────────────────────────────────────────────────────────

# ─── PAZIENTI ─────────────────────────────────────────────────────────────────
@api_router.get("/pazienti")
async def list_pazienti(user: dict = Depends(require_auth)):
    docs: list = []
    if user["role"] == "admin":
        docs = await db.pazienti.find({}).to_list(500)
    elif user["role"] == "terapeuta":
        terapista = await db.terapisti.find_one({"user_id": user["_id"]})
        tid = str(terapista["_id"]) if terapista else None
        docs = await db.pazienti.find({"terapeuta_assegnato": tid}).to_list(200)
    else:
        docs = await db.pazienti.find({"user_id": user["_id"]}).to_list(1)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs

@api_router.get("/pazienti/{paziente_id}")
async def get_paziente(paziente_id: str, user: dict = Depends(require_auth)):
    doc = await db.pazienti.find_one({"_id": ObjectId(paziente_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Paziente non trovato")
    doc["_id"] = str(doc["_id"])
    return doc

@api_router.post("/pazienti")
async def create_paziente(data: PazienteProfileInput, user: dict = Depends(require_admin)):
    if data.codice_fiscale and not validate_codice_fiscale(data.codice_fiscale):
        raise HTTPException(status_code=400, detail="Codice Fiscale non valido")
    doc = data.model_dump(exclude_none=True)
    doc["created_at"] = datetime.now(timezone.utc)
    result = await db.pazienti.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

@api_router.put("/pazienti/{paziente_id}")
async def update_paziente(paziente_id: str, data: PazienteProfileInput, user: dict = Depends(require_auth)):
    existing = await db.pazienti.find_one({"_id": ObjectId(paziente_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Paziente non trovato")
    if data.codice_fiscale and not validate_codice_fiscale(data.codice_fiscale):
        raise HTTPException(status_code=400, detail="Codice Fiscale non valido")
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc)
    await db.pazienti.update_one({"_id": ObjectId(paziente_id)}, {"$set": update})
    doc = await db.pazienti.find_one({"_id": ObjectId(paziente_id)})
    doc["_id"] = str(doc["_id"])
    return doc

@api_router.delete("/pazienti/{paziente_id}")
async def delete_paziente(paziente_id: str, user: dict = Depends(require_admin)):
    result = await db.pazienti.delete_one({"_id": ObjectId(paziente_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Paziente non trovato")
    return {"message": "Paziente eliminato"}

@api_router.get("/pazienti/profilo/me")
async def get_my_paziente_profile(user: dict = Depends(require_auth)):
    if user["role"] != "paziente":
        raise HTTPException(status_code=403, detail="Accesso negato")
    doc = await db.pazienti.find_one({"user_id": user["_id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Profilo non trovato")
    doc["_id"] = str(doc["_id"])
    return doc

def _compute_dati_fiscali_completi(p: dict) -> bool:
    """Verifica se il paziente ha tutti i dati fiscali richiesti."""
    required_always = ["nome", "cognome", "data_nascita", "genere", "codice_fiscale", "telefono",
                       "indirizzo", "citta", "cap", "provincia_residenza"]
    if any(not p.get(f) for f in required_always):
        return False
    if p.get("nato_all_estero"):
        return bool(p.get("paese_nascita"))
    return bool(p.get("luogo_nascita_provincia") and p.get("luogo_nascita_comune"))

@api_router.put("/pazienti/profilo/me")
async def update_my_paziente_profile(data: PazienteProfileInput, user: dict = Depends(require_auth)):
    if user["role"] != "paziente":
        raise HTTPException(status_code=403, detail="Accesso negato")
    if data.codice_fiscale and not validate_codice_fiscale(data.codice_fiscale):
        raise HTTPException(status_code=400, detail="Codice Fiscale non valido")
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc)
    await db.pazienti.update_one({"user_id": user["_id"]}, {"$set": update}, upsert=True)
    doc = await db.pazienti.find_one({"user_id": user["_id"]})
    # Auto-compute dati_fiscali_completi flag
    completi = _compute_dati_fiscali_completi(doc)
    if doc.get("dati_fiscali_completi") != completi:
        await db.pazienti.update_one({"user_id": user["_id"]}, {"$set": {"dati_fiscali_completi": completi}})
        doc["dati_fiscali_completi"] = completi
    doc["_id"] = str(doc["_id"])
    return doc


@api_router.get("/paziente/mio-terapeuta")
async def get_mio_terapeuta(user: dict = Depends(require_auth)):
    """Return the paziente's current therapist (last with a confirmed/completed
    appuntamento) along with next available slot and unread message count."""
    if user["role"] != "paziente":
        raise HTTPException(status_code=403, detail="Solo pazienti")

    # Find last appuntamento in "confermato"/"completato"
    last = await db.appuntamenti.find_one(
        {"paziente_user_id": user["_id"], "stato": {"$in": ["confermato", "completato"]}},
        sort=[("data_ora", -1)],
    )
    if not last:
        return {"has_terapeuta": False}

    terapeuta_id = last.get("terapeuta_id")
    if not terapeuta_id:
        return {"has_terapeuta": False}

    try:
        t = await db.terapisti.find_one({"_id": ObjectId(terapeuta_id)})
    except Exception:
        t = None
    if not t or not t.get("documenti_verificati"):
        return {"has_terapeuta": False, "reason": "terapeuta_non_disponibile"}

    # Compute next available slot in the next 30 days (excluding booked slots)
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=30)
    booked_appts = await db.appuntamenti.find({
        "terapeuta_id": terapeuta_id,
        "stato": {"$nin": ["cancellato", "annullato"]},
        "data_ora": {"$gte": now.isoformat(), "$lt": horizon.isoformat()},
    }).to_list(500)
    booked = {a["data_ora"][:16] for a in booked_appts}

    cal = t.get("disponibilita_calendario") or {}
    min_slot_time = now + timedelta(hours=2)
    slots_available = 0
    next_slot_iso = None
    for date_key in sorted(cal.keys()):
        try:
            y, m, d = map(int, date_key.split("-"))
            slot_date = datetime(y, m, d, tzinfo=timezone.utc)
        except Exception:
            continue
        if slot_date < now - timedelta(days=1) or slot_date > horizon:
            continue
        for hhmm in cal[date_key]:
            try:
                slot_dt = datetime(y, m, d, int(hhmm[:2]), int(hhmm[3:5]), tzinfo=timezone.utc)
            except Exception:
                continue
            if slot_dt < min_slot_time or slot_dt > horizon:
                continue
            if slot_dt.isoformat()[:16] in booked:
                continue
            slots_available += 1
            if next_slot_iso is None:
                next_slot_iso = slot_dt.isoformat()

    # Unread messages from this terapeuta
    unread = await db.messaggi.count_documents({
        "destinatario_id": user["_id"],
        "mittente_id": t.get("user_id"),
        "letto": False,
    })

    return {
        "has_terapeuta": True,
        "terapeuta": {
            "id": str(t["_id"]),
            "user_id": t.get("user_id"),
            "nome": t.get("nome"),
            "cognome": t.get("cognome"),
            "foto_url": t.get("foto_url"),
            "specializzazioni": t.get("specializzazioni", [])[:3],
            "prezzo_seduta": t.get("prezzo_seduta") or t.get("tariffa") or 70,
            "durata_seduta_minuti": t.get("durata_seduta_minuti") or 50,
        },
        "next_slot": next_slot_iso,
        "slots_next_30d_count": slots_available,
        "unread_messages": unread,
        "last_appuntamento_at": last.get("data_ora"),
    }


# ─── APPUNTAMENTI ─────────────────────────────────────────────────────────────


# ─── ADMIN USER MANAGEMENT ───────────────────────────────────────────────────
@api_router.get("/admin/utenti")
async def list_utenti(user: dict = Depends(require_admin)):
    docs = await db.users.find({}, {"password_hash": 0, "otp_code": 0}).to_list(500)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs

@api_router.patch("/admin/utenti/{user_id}/stato")
async def toggle_user_stato(user_id: str, body: dict, user: dict = Depends(require_admin)):
    is_active = body.get("is_active", True)
    await db.users.update_one({"_id": ObjectId(user_id)}, {"$set": {"is_active": is_active}})
    return {"message": "Stato utente aggiornato"}

# ─── DASHBOARD ────────────────────────────────────────────────────────────────
@api_router.get("/dashboard/stats")
async def dashboard_stats(user: dict = Depends(require_auth)):
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    n_terapisti = await db.terapisti.count_documents({})
    n_pazienti = await db.pazienti.count_documents({})
    n_appuntamenti_oggi = await db.appuntamenti.count_documents({
        "data_ora": {"$gte": today.isoformat(), "$lt": (today + timedelta(days=1)).isoformat()}
    })
    n_appuntamenti_totali = await db.appuntamenti.count_documents({})
    n_terapisti_pendenti = await db.users.count_documents({"role": "terapeuta", "approval_status": "pending"})
    n_articoli_bozza = await db.articoli.count_documents({"stato": "bozza"})
    n_terapisti_senza_cert = await db.terapisti.count_documents({"autocertificazione_firmata": False})

    scadenze = []
    terapisti_docs = await db.terapisti.find({"assicurazione_scadenza": {"$exists": True}}).to_list(100)
    for t in terapisti_docs:
        scad = t.get("assicurazione_scadenza")
        if scad:
            try:
                scad_date = datetime.fromisoformat(scad.replace("Z", "+00:00"))
                giorni = (scad_date - datetime.now(timezone.utc)).days
                if giorni <= 60:
                    scadenze.append({
                        "terapeuta": f"{t.get('nome','')} {t.get('cognome','')}".strip(),
                        "scadenza": scad,
                        "giorni_rimanenti": giorni
                    })
            except Exception as e:
                logging.warning(f"[DASHBOARD] bad scadenza for terapeuta {t.get('_id')}: {e}")

    return {
        "terapisti": n_terapisti,
        "pazienti": n_pazienti,
        "appuntamenti_oggi": n_appuntamenti_oggi,
        "appuntamenti_totali": n_appuntamenti_totali,
        "terapisti_pendenti": n_terapisti_pendenti,
        "articoli_in_revisione": n_articoli_bozza,
        "terapisti_senza_autocertificazione": n_terapisti_senza_cert,
        "scadenze_assicurazione": scadenze
    }

class MatchingInput(BaseModel):
    eta: Optional[str] = None
    genere: Optional[str] = None
    problemi: Optional[List[str]] = []
    orari: Optional[List[str]] = []
    preferenza_terapeuta: Optional[str] = None

class MessaggioInput(BaseModel):
    destinatario_id: str
    testo: str

class FAQInput(BaseModel):
    domanda: str
    risposta: str
    ordine: Optional[int] = 0

# ─── PUBLIC ROUTES (no auth) ──────────────────────────────────────────────────
@api_router.get("/public/terapisti")
async def public_list_terapisti():
    docs = await db.terapisti.find({"documenti_verificati": True, "sospeso": {"$ne": True}}).to_list(100)
    for d in docs:
        d["_id"] = str(d["_id"])
        d.pop("note_cliniche", None)
        d.pop("documenti", None)
    return docs

@api_router.get("/public/terapisti/{tid}")
async def public_get_terapista(tid: str):
    doc = await db.terapisti.find_one({"_id": ObjectId(tid)})
    if not doc:
        raise HTTPException(status_code=404, detail="Terapeuta non trovato")
    if not doc.get("documenti_verificati") or doc.get("sospeso"):
        raise HTTPException(status_code=404, detail="Terapeuta non trovato")
    doc["_id"] = str(doc["_id"])
    doc.pop("documenti", None)
    doc.pop("note_cliniche", None)
    return doc

@api_router.post("/public/matching")
async def matching(data: MatchingInput):
    docs = await db.terapisti.find({"documenti_verificati": True, "sospeso": {"$ne": True}}).to_list(100)
    PREF_MAP = {"Preferisco una donna": "F", "Preferisco un uomo": "M"}
    pref_genere = PREF_MAP.get(data.preferenza_terapeuta or "", None)
    ORARIO_MAP = {"Mattina (8-12)": (8,12), "Pomeriggio (12-18)": (12,18), "Sera (18-21)": (18,21)}

    results = []
    for t in docs:
        score = 0
        reasons = []
        # Genere
        if pref_genere:
            if t.get("genere") == pref_genere:
                score += 30
                reasons.append("Preferenza di genere")
        else:
            score += 15
        # Specializzazioni
        for prob in (data.problemi or []):
            for spec in t.get("specializzazioni", []):
                if any(w in spec.lower() for w in prob.lower().split()):
                    score += 20
                    reasons.append(f"Specializzazione: {spec}")
                    break
        # Disponibilità × orari
        for disp in t.get("disponibilita", []):
            is_wkend = disp.get("giorno","") in ["Sabato","Domenica"]
            if "Weekend" in (data.orari or []) and is_wkend:
                score += 10
            elif "Weekend" not in (data.orari or []) and not is_wkend:
                score += 5
            try:
                h = int(disp.get("ora_inizio","0:0").split(":")[0])
                for orario in (data.orari or []):
                    rng = ORARIO_MAP.get(orario)
                    if rng and rng[0] <= h < rng[1]:
                        score += 10
            except Exception:
                pass
        t["_id"] = str(t["_id"])
        t["match_score"] = score
        t["match_reasons"] = list(set(reasons))
        results.append(t)
    results.sort(key=lambda x: x["match_score"], reverse=True)
    top = results[:3]
    # Normalize to percent
    max_s = top[0]["match_score"] if top else 1
    for t in top:
        t["compatibilita"] = min(99, max(70, int(t["match_score"] / max(max_s, 1) * 99)))
    return {"terapisti": top}


@api_router.get("/public/faq")
async def public_faq():
    docs = await db.faq.find({}).sort("ordine", 1).to_list(50)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs

# ─── FAQ ADMIN ────────────────────────────────────────────────────────────────
@api_router.post("/faq")
async def create_faq(data: FAQInput, user: dict = Depends(require_admin)):
    doc = data.model_dump()
    doc["created_at"] = datetime.now(timezone.utc)
    result = await db.faq.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

@api_router.put("/faq/{faq_id}")
async def update_faq(faq_id: str, data: FAQInput, user: dict = Depends(require_admin)):
    await db.faq.update_one({"_id": ObjectId(faq_id)}, {"$set": data.model_dump()})
    doc = await db.faq.find_one({"_id": ObjectId(faq_id)})
    doc["_id"] = str(doc["_id"])
    return doc

@api_router.delete("/faq/{faq_id}")
async def delete_faq(faq_id: str, user: dict = Depends(require_admin)):
    await db.faq.delete_one({"_id": ObjectId(faq_id)})
    return {"message": "FAQ eliminata"}

# ─── MESSAGGI ─────────────────────────────────────────────────────────────────
@api_router.get("/conversazioni")
async def list_conversazioni(user: dict = Depends(require_auth)):
    uid = user["_id"]
    if user["role"] == "paziente":
        paziente = await db.pazienti.find_one({"user_id": uid})
        if not paziente:
            return []
        pid = str(paziente["_id"])
        apps = await db.appuntamenti.find({"paziente_id": pid, "stato": {"$in": ["confermato","completato"]}}).to_list(100)
        tids = list({a["terapeuta_id"] for a in apps})
        convs = []
        for tid in tids:
            t = await db.terapisti.find_one({"_id": ObjectId(tid)})
            if t:
                conv_id = f"{pid}_{tid}"
                last = await db.messaggi.find_one({"conversazione_id": conv_id}, sort=[("created_at", -1)])
                unread = await db.messaggi.count_documents({"conversazione_id": conv_id, "mittente_id": {"$ne": uid}, "letto": False})
                convs.append({"conversazione_id": conv_id, "terapeuta_id": tid, "terapeuta_nome": f"{t.get('nome','')} {t.get('cognome','')}".strip(), "ultimo_messaggio": last["testo"] if last else None, "non_letti": unread})
        return convs
    else:
        terapista = await db.terapisti.find_one({"user_id": uid})
        if not terapista:
            return []
        tid = str(terapista["_id"])
        apps = await db.appuntamenti.find({"terapeuta_id": tid, "stato": {"$in": ["confermato","completato"]}}).to_list(100)
        pids = list({a["paziente_id"] for a in apps})
        convs = []
        for pid in pids:
            p = await db.pazienti.find_one({"_id": ObjectId(pid)})
            if p:
                conv_id = f"{pid}_{tid}"
                last = await db.messaggi.find_one({"conversazione_id": conv_id}, sort=[("created_at", -1)])
                unread = await db.messaggi.count_documents({"conversazione_id": conv_id, "mittente_id": {"$ne": uid}, "letto": False})
                convs.append({"conversazione_id": conv_id, "paziente_id": pid, "paziente_nome": f"{p.get('nome','')} {p.get('cognome','')}".strip(), "ultimo_messaggio": last["testo"] if last else None, "non_letti": unread})
        return convs

@api_router.get("/messaggi/{conv_id}")
async def get_messaggi(conv_id: str, user: dict = Depends(require_auth)):
    docs = await db.messaggi.find({"conversazione_id": conv_id}).sort("created_at", 1).to_list(200)
    await db.messaggi.update_many({"conversazione_id": conv_id, "mittente_id": {"$ne": user["_id"]}}, {"$set": {"letto": True}})
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs

@api_router.post("/messaggi")
async def send_messaggio(data: MessaggioInput, user: dict = Depends(require_auth)):
    uid = user["_id"]
    if user["role"] == "paziente":
        paziente = await db.pazienti.find_one({"user_id": uid})
        if not paziente:
            raise HTTPException(400, "Profilo paziente non trovato")
        pid = str(paziente["_id"])
        tid = data.destinatario_id
        conv_id = f"{pid}_{tid}"
    else:
        terapista = await db.terapisti.find_one({"user_id": uid})
        if not terapista:
            raise HTTPException(400, "Profilo terapeuta non trovato")
        tid = str(terapista["_id"])
        pid = data.destinatario_id
        conv_id = f"{pid}_{tid}"
    doc = {"conversazione_id": conv_id, "mittente_id": uid, "mittente_ruolo": user["role"], "testo": data.testo, "letto": False, "created_at": datetime.now(timezone.utc)}
    result = await db.messaggi.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

# ─── PRENOTAZIONE PUBBLICA ────────────────────────────────────────────────────
@api_router.post("/public/prenota")
async def prenota_pubblico(data: AppuntamentoInput, user: dict = Depends(require_auth)):
    if user["role"] != "paziente":
        raise HTTPException(403, "Solo i pazienti possono prenotare")
    # Require recent SMS phone verification (last 60 min) before confirming booking
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
        raise HTTPException(403, "Verifica il numero di telefono via SMS prima di confermare la prenotazione")
    doc = data.model_dump()
    doc["stato"] = "confermato"
    doc["created_at"] = datetime.now(timezone.utc)
    doc["paziente_user_id"] = user["_id"]
    result = await db.appuntamenti.insert_one(doc)
    app_id = str(result.inserted_id)
    doc["_id"] = app_id
    finalized = await _finalize_confirmed_booking(app_id, user)
    if finalized:
        doc["daily_room_url"] = finalized.get("daily_room_url")
        doc["daily_room_name"] = finalized.get("daily_room_name")
    return doc

# ─── SMS OTP (Twilio Verify) ──────────────────────────────────────────────────
# Twilio manages code generation, storage, expiration, and rate-limiting on its
# side. Our DB only records the pending request for auditing and rate-limiting
# repeated sends.


@api_router.post("/sms/send-otp")
async def sms_send_otp(body: dict, user: dict = Depends(require_auth)):
    """Trigger Twilio Verify to send an OTP by SMS.
    Fallback: if provider fails (e.g. account suspended), generate a local dev OTP
    and store it in db.sms_otp so the frontend can show it and let testing continue.
    """
    import secrets as _sec
    phone = (body.get("phone") or "").strip()
    context = (body.get("context") or "verifica").strip()[:40]
    if not phone:
        raise HTTPException(400, "Numero di telefono mancante")

    # Try the real provider first
    provider_ok = False
    try:
        provider_ok = await send_sms_otp(phone, "", context)
    except Exception as _e:
        logging.warning(f"[SMS OTP] provider raised: {_e}")
        provider_ok = False

    now = datetime.now(timezone.utc)
    if provider_ok:
        await db.sms_otp.update_one(
            {"user_id": user["_id"], "phone": phone},
            {"$set": {
                "user_id": user["_id"], "phone": phone, "verified": False,
                "provider": "twilio_verify", "context": context,
                "created_at": now, "dev_code": None,
            }},
            upsert=True,
        )
        logging.info(f"[SMS OTP] Twilio Verify sent to {phone} for {user['email']}")
        return {"message": "OTP inviato via SMS"}

    # Fallback: generate a local dev code and store it, return in payload
    dev_code = f"{_sec.randbelow(1_000_000):06d}"
    await db.sms_otp.update_one(
        {"user_id": user["_id"], "phone": phone},
        {"$set": {
            "user_id": user["_id"], "phone": phone, "verified": False,
            "provider": "dev_fallback", "context": context,
            "created_at": now, "dev_code": dev_code,
        }},
        upsert=True,
    )
    logging.warning(f"[SMS OTP] Provider unavailable → dev fallback issued for {phone}")
    return {"message": "OTP di test (SMS provider temporaneamente non disponibile)", "otp_dev": dev_code}


@api_router.post("/sms/verify-otp")
async def sms_verify_otp(body: dict, user: dict = Depends(require_auth)):
    """Verify the SMS OTP. Accepts both real Twilio codes and dev fallback codes."""
    phone = (body.get("phone") or "").strip()
    code = (body.get("otp_code") or "").strip()
    if not phone or not code:
        raise HTTPException(400, "Dati incompleti")

    # Check dev fallback first (cheaper, no external call)
    rec = await db.sms_otp.find_one({"user_id": user["_id"], "phone": phone})
    approved = False
    if rec and rec.get("provider") == "dev_fallback" and rec.get("dev_code"):
        # 15-minute expiry on dev codes
        created_at = rec.get("created_at")
        if isinstance(created_at, datetime):
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - created_at) <= timedelta(minutes=15) and code == rec["dev_code"]:
                approved = True
    if not approved:
        # Fall back to Twilio Verify
        try:
            approved = await verify_sms_otp(phone, code)
        except Exception as _e:
            logging.warning(f"[SMS VERIFY] provider raised: {_e}")
            approved = False
    if not approved:
        raise HTTPException(400, "Codice OTP non valido o scaduto")
    now = datetime.now(timezone.utc)
    await db.sms_otp.update_one(
        {"user_id": user["_id"], "phone": phone},
        {"$set": {"verified": True, "verified_at": now}},
    )
    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": {"telefono": phone, "telefono_verificato": True, "telefono_verificato_at": now}},
    )
    return {"verified": True}


# ─── THERAPIST DOCUMENTS UPLOAD (CV / Assicurazione / Laurea) ─────────────────


@api_router.post("/utils/compute-cf")
async def compute_cf(data: dict, user: dict = Depends(require_auth)):
    """Compute Italian Codice Fiscale from anagrafic data. Returns {cf: str} or {error: str}."""
    try:
        lastname = (data.get("cognome") or "").strip()
        firstname = (data.get("nome") or "").strip()
        gender = (data.get("genere") or "").strip()
        birthdate = (data.get("data_nascita") or "").strip()
        if gender in ("M", "Maschio"):
            g = "M"
        elif gender in ("F", "Femmina"):
            g = "F"
        else:
            return {"error": "Genere deve essere M o F"}
        # Birthplace: comune italiano or paese estero
        if data.get("nato_all_estero"):
            birthplace = (data.get("paese_nascita") or "").strip()
        else:
            birthplace = (data.get("luogo_nascita_comune") or "").strip()
        if not all([lastname, firstname, birthdate, birthplace]):
            return {"error": "Dati incompleti"}
        cf = codicefiscale.encode(lastname=lastname, firstname=firstname, gender=g, birthdate=birthdate, birthplace=birthplace)
        return {"cf": cf}
    except Exception as e:
        return {"error": str(e)}

# ─── GDPR — Audit Consent Log ─────────────────────────────────────────────────
# Stores an immutable record (write-once) of cookie consent decisions.
# Captures: anonymized IP, server timestamp, policy hash, prefs, user-agent.
# This provides legal evidence of compliance with EU GDPR + Italian Garante.
import hashlib as _hashlib
import ipaddress as _ipaddress


def _anonymize_ip(raw_ip: str) -> str:
    """Mask the last octet (IPv4) or last 80 bits (IPv6) to comply with GDPR data-minimization."""
    if not raw_ip:
        return ""
    try:
        ip = _ipaddress.ip_address(raw_ip)
        if isinstance(ip, _ipaddress.IPv4Address):
            parts = str(ip).split(".")
            parts[-1] = "0"
            return ".".join(parts)
        # IPv6: keep first 48 bits, zero the rest
        net = _ipaddress.IPv6Network(f"{ip}/48", strict=False)
        return str(net.network_address)
    except ValueError:
        return ""


def _policy_hash(policy_version: str, prefs: dict) -> str:
    blob = f"{policy_version}|{prefs.get('essential', True)}|{prefs.get('analytics', False)}|{prefs.get('marketing', False)}"
    return _hashlib.sha256(blob.encode()).hexdigest()


def _client_ip(request: Request) -> str:
    """Extract the client IP, honoring X-Forwarded-For from the K8s ingress."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else ""


@api_router.post("/audit/consent")
async def audit_consent(data: ConsentLogInput, request: Request):
    """Public endpoint called by the cookie banner after the user accepts/declines.
    Writes a write-once log entry. No update/delete endpoints are exposed."""
    raw_ip = _client_ip(request)
    prefs_dict = data.prefs.model_dump()
    doc = {
        "policy_version": data.policy_version,
        "policy_hash": _policy_hash(data.policy_version, prefs_dict),
        "prefs": prefs_dict,
        "ip_anonymized": _anonymize_ip(raw_ip),
        "user_agent": (request.headers.get("user-agent") or "")[:300],
        "language": (data.language or request.headers.get("accept-language") or "")[:50],
        "page_url": (data.page_url or "")[:300],
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.audit_consents.insert_one(doc)
    return {
        "audit_id": str(result.inserted_id),
        "policy_hash": doc["policy_hash"],
        "logged_at": doc["created_at"].isoformat(),
    }


@api_router.get("/admin/audit/consents")
async def list_audit_consents(
    limit: int = 50,
    skip: int = 0,
    user: dict = Depends(require_admin),
):
    """Admin-only paginated listing of consent audit log entries."""
    limit = max(1, min(limit, 200))
    skip = max(0, skip)
    total = await db.audit_consents.count_documents({})
    cursor = db.audit_consents.find({}).sort("created_at", -1).skip(skip).limit(limit)
    items = []
    async for doc in cursor:
        items.append({
            "id": str(doc["_id"]),
            "policy_version": doc.get("policy_version"),
            "policy_hash": doc.get("policy_hash"),
            "prefs": doc.get("prefs"),
            "ip_anonymized": doc.get("ip_anonymized"),
            "user_agent": doc.get("user_agent"),
            "language": doc.get("language"),
            "page_url": doc.get("page_url"),
            "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
        })
    return {"total": total, "skip": skip, "limit": limit, "items": items}


# ─── Contracts (editable Mandato all'incasso) ────────────────────────────────
# Immutable version log: admin can create new versions but never edit past ones.
# Therapist acceptance records: contract_id, version, therapist_id, timestamp,
# IP (anonymized), content_hash for legal traceability.
import hashlib as _hlib


def _hash_contract(content_html: str) -> str:
    return _hlib.sha256(content_html.encode("utf-8")).hexdigest()


@api_router.get("/admin/contracts")
async def list_contracts(user: dict = Depends(require_admin)):
    """Return all contract versions grouped by kind, most recent first."""
    out = []
    async for doc in db.contracts.find({}).sort("created_at", -1):
        out.append({
            "id": str(doc["_id"]),
            "kind": doc.get("kind"),
            "title": doc.get("title"),
            "content_html": doc.get("content_html"),
            "content_hash": doc.get("content_hash"),
            "version": doc.get("version"),
            "effective_date": doc.get("effective_date"),
            "is_current": doc.get("is_current", False),
            "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
            "created_by": doc.get("created_by"),
        })
    return {"items": out}


@api_router.post("/admin/contracts")
async def create_contract(data: ContractInput, user: dict = Depends(require_admin)):
    """Create a new immutable version of a contract kind."""
    now = datetime.now(timezone.utc)
    prev = await db.contracts.find({"kind": data.kind}).sort("version", -1).to_list(1)
    next_ver = (prev[0]["version"] + 1) if prev else 1
    await db.contracts.update_many(
        {"kind": data.kind, "is_current": True},
        {"$set": {"is_current": False}},
    )
    doc = {
        "kind": data.kind,
        "title": data.title,
        "content_html": data.content_html,
        "content_hash": _hash_contract(data.content_html),
        "version": next_ver,
        "effective_date": data.effective_date or now.isoformat(),
        "is_current": True,
        "created_at": now,
        "created_by": user["_id"],
    }
    result = await db.contracts.insert_one(doc)
    return {"id": str(result.inserted_id), "version": next_ver}


@api_router.get("/contracts/current/{kind}")
async def get_current_contract(kind: str):
    """Public: fetch the current (active) version of a contract kind."""
    doc = await db.contracts.find_one({"kind": kind, "is_current": True})
    if not doc:
        raise HTTPException(404, "Contratto non trovato")
    return {
        "id": str(doc["_id"]),
        "kind": doc.get("kind"),
        "title": doc.get("title"),
        "content_html": doc.get("content_html"),
        "content_hash": doc.get("content_hash"),
        "version": doc.get("version"),
        "effective_date": doc.get("effective_date"),
    }


@api_router.post("/contracts/accept")
async def accept_contract(data: ContractAcceptInput, request: Request, user: dict = Depends(require_auth)):
    """Therapist (or any user) accepts a contract. Write-once acceptance log."""
    contract = await db.contracts.find_one({"_id": ObjectId(data.contract_id)})
    if not contract:
        raise HTTPException(404, "Contratto non trovato")
    now = datetime.now(timezone.utc)
    raw_ip = _client_ip(request)
    doc = {
        "user_id": user["_id"],
        "user_role": user["role"],
        "contract_id": data.contract_id,
        "contract_kind": contract.get("kind"),
        "contract_version": contract.get("version"),
        "content_hash": contract.get("content_hash"),
        "ip_anonymized": _anonymize_ip(raw_ip),
        "user_agent": (request.headers.get("user-agent") or "")[:300],
        "scrolled_to_end": data.scrolled_to_end,
        "accepted_at": now,
    }
    result = await db.contract_acceptances.insert_one(doc)
    return {
        "id": str(result.inserted_id),
        "contract_kind": contract.get("kind"),
        "contract_version": contract.get("version"),
        "accepted_at": now.isoformat(),
    }


@api_router.get("/contracts/my-acceptances")
async def my_contract_acceptances(user: dict = Depends(require_auth)):
    """List contracts accepted by the current user."""
    out = []
    async for doc in db.contract_acceptances.find({"user_id": user["_id"]}).sort("accepted_at", -1):
        out.append({
            "id": str(doc["_id"]),
            "contract_kind": doc.get("contract_kind"),
            "contract_version": doc.get("contract_version"),
            "content_hash": doc.get("content_hash"),
            "accepted_at": doc.get("accepted_at").isoformat() if doc.get("accepted_at") else None,
        })
    return {"items": out}


@api_router.get("/admin/contracts/{contract_id}/acceptances")
async def list_contract_acceptances(contract_id: str, user: dict = Depends(require_admin)):
    """Admin: audit trail of who accepted a specific contract."""
    out = []
    async for doc in db.contract_acceptances.find({"contract_id": contract_id}).sort("accepted_at", -1):
        out.append({
            "id": str(doc["_id"]),
            "user_id": doc.get("user_id"),
            "user_role": doc.get("user_role"),
            "ip_anonymized": doc.get("ip_anonymized"),
            "user_agent": doc.get("user_agent"),
            "accepted_at": doc.get("accepted_at").isoformat() if doc.get("accepted_at") else None,
        })
    return {"items": out}




app.include_router(api_router)

# Mount modular routers under /api
from routers.admin_analytics import build_router as _build_admin_analytics_router
from routers.appuntamenti import router as _appuntamenti_router
from routers.terapisti import router as _terapisti_router
from routers.payments import router as _payments_router
from routers.auth import router as _auth_router
from routers.blog import router as _blog_router
from routers.calendario import router as _calendario_router
from routers.legal_signature import router as _legal_signature_router
from routers.fatture import router as _fatture_router
from routers.registro_trattamenti import router as _registro_router
from routers.diario import router as _diario_router
app.include_router(_build_admin_analytics_router(db, require_admin), prefix="/api")
app.include_router(_appuntamenti_router, prefix="/api")
app.include_router(_terapisti_router, prefix="/api")
app.include_router(_payments_router, prefix="/api")
app.include_router(_auth_router, prefix="/api")
app.include_router(_blog_router, prefix="/api")
app.include_router(_calendario_router, prefix="/api")
app.include_router(_legal_signature_router, prefix="/api")
app.include_router(_fatture_router, prefix="/api")
app.include_router(_registro_router, prefix="/api")
app.include_router(_diario_router, prefix="/api")
# CORS — supports multiple frontend origins (preview, production, custom domains) via ALLOWED_ORIGINS env var
_extra_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]
_cors_origins = list({
    FRONTEND_URL,
    "http://localhost:3000",
    "https://funzionabene.friulion.it",
    "https://www.funzionabene.friulion.it",
    "https://portugues-writer-2.preview.emergentagent.com",
    "https://portugues-writer-2.emergent.host",
    *_extra_origins,
})
logging.info(f"[CORS] Allowed origins: {_cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Therapist signature enforcement middleware ────────────────────────────────
# Rejects therapist-authenticated requests to protected endpoints when mandatory
# legal documents haven't been signed. Fail-CLOSED: any error checking signature
# status blocks the therapist (except for allowlisted paths).
from deps import _TERAPEUTA_REQUIRED_KINDS
import jwt as _jwt

# Endpoints therapists can ALWAYS access, even without signed docs (needed to
# actually complete the signature flow, log out, view their profile, etc.).
_SIGNATURE_ALLOWLIST_PREFIXES = (
    "/api/auth/",           # login, logout, /me
    "/api/contracts/",      # sign, list pending
    "/api/legal-documents/",  # read legal doc content (public reads)
    "/api/upload/",         # file uploads used by signature flow
)

@app.middleware("http")
async def therapist_signature_gate(request, call_next):
    path = request.url.path
    method = request.method
    # Skip non-API and non-mutating requests fast
    if not path.startswith("/api/") or method in ("OPTIONS", "GET", "HEAD"):
        return await call_next(request)
    if any(path.startswith(p) for p in _SIGNATURE_ALLOWLIST_PREFIXES):
        return await call_next(request)
    logging.info(f"[SIGGATE] check {method} {path}")

    # Pull token
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth.split(" ", 1)[1]
    if not token:
        return await call_next(request)  # no session → downstream deps will 401
    try:
        payload = _jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
        role = payload.get("role")
        user_id = payload.get("sub")
    except Exception:
        return await call_next(request)  # let downstream handle invalid token

    if role != "terapeuta" or not user_id:
        return await call_next(request)

    # Check signature status
    try:
        for kind in _TERAPEUTA_REQUIRED_KINDS:
            current = await db.contracts.find_one({"kind": kind, "is_current": True})
            if not current:
                continue
            signed = await db.contract_acceptances.find_one({
                "user_id": user_id,
                "contract_kind": kind,
                "contract_version": current.get("version"),
            })
            if not signed:
                from fastapi.responses import JSONResponse
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "Devi firmare i documenti obbligatori prima di eseguire questa operazione.",
                        "required_signature": True,
                    },
                )
    except Exception as e:
        logging.exception(f"[SIGNATURE GATE] check failed: {e}")
        # Fail closed for compliance
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"detail": "Verifica firma documenti temporaneamente non disponibile. Riprova."},
        )
    return await call_next(request)

# ─── Startup ──────────────────────────────────────────────────────────────────
from booking_service import scheduler, start_scheduler, stop_scheduler, schedule_reminders, finalize_confirmed_booking

# Legacy aliases kept for any internal references
_finalize_confirmed_booking = finalize_confirmed_booking

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.password_reset_tokens.create_index("token_hash", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    # Fatture uniqueness — prevent duplicate invoices under race conditions
    await db.fatture.create_index("numero", unique=True)
    await db.fatture.create_index(
        [("appuntamento_id", 1), ("kind", 1)],
        unique=True,
        partialFilterExpression={"appuntamento_id": {"$type": "string"}},
    )
    await db.fatture.create_index(
        [("terapeuta_user_id", 1), ("kind", 1), ("anno_riferimento", 1), ("mese_riferimento", 1)],
        unique=True,
        partialFilterExpression={"kind": "commissione"},
    )
    await seed_data()
    await _seed_default_contract()
    await _seed_legal_documents()
    await _seed_registro_trattamenti()

    # Start scheduled background jobs (retention, legal decline processor)
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from scheduled_jobs import register_jobs
        _scheduler = AsyncIOScheduler(timezone="UTC")
        register_jobs(_scheduler, db)
        _scheduler.start()
        app.state.scheduler = _scheduler
    except Exception as e:
        logging.exception(f"[STARTUP] failed to start scheduler: {e}")

    # Backfill: make existing self-certified therapists publicly visible under the new gate
    await db.terapisti.update_many(
        {"autocertificazione_firmata": True, "documenti_verificati": {"$exists": False}},
        {"$set": {"documenti_verificati": True}},
    )
    start_scheduler()


async def _seed_default_contract():
    """Insert the default 'Mandato all'incasso con Rappresentanza' contract only if
    no version exists yet. Admin can create new versions at will after this."""
    existing = await db.contracts.find_one({"kind": "mandato_all_incasso"})
    if existing:
        return
    default_html = """
<h2>Mandato all'incasso con Rappresentanza</h2>
<p><strong>Tra il Terapeuta</strong> — professionista sanitario iscritto all'Albo — <strong>e BIDOC SRL</strong>, con sede in Via Mazzini, 62 · Spilimbergo (PN) · P.IVA 01985930930, quale titolare del marchio <em>Funzionabene</em> (di seguito "la Piattaforma").</p>

<h3>1. Natura del rapporto</h3>
<p>La Piattaforma opera in <strong>mandato all'incasso con rappresentanza</strong> per conto del Terapeuta, ai sensi degli artt. 1703 e ss. c.c.. La Piattaforma non è parte del contratto sanitario tra Terapeuta e paziente: essa svolge esclusivamente attività di intermediazione tecnica, gestione dell'agenda, incasso e ripasso dei corrispettivi.</p>

<h3>2. Prestazione sanitaria</h3>
<p>La prestazione sanitaria è erogata direttamente dal Terapeuta al paziente. Il Terapeuta è l'unico titolare del rapporto sanitario e dei relativi obblighi (consenso informato, tenuta cartella clinica, riservatezza professionale ex art. 622 c.p. e Codice Deontologico).</p>

<h3>3. Emissione della fattura sanitaria</h3>
<p>Il Terapeuta autorizza la Piattaforma a emettere e trasmettere, in suo nome e per suo conto, la <strong>fattura sanitaria esente IVA</strong> (art. 10 DPR 633/72 c.1 n.18) al paziente, comprensiva della marca da bollo di €2,00 per fatture di importo pari o superiore a €77,47. La fattura riporterà i dati del Terapeuta (P.IVA, iscrizione all'Albo).</p>

<h3>4. Sistema Tessera Sanitaria (Sistema TS)</h3>
<p>La Piattaforma trasmette al Sistema TS, per conto del Terapeuta, i dati delle spese sanitarie sostenute dai pazienti, salvo espressa <strong>opposizione</strong> del paziente stesso (art. 3 D.M. 31/07/2015). Il paziente esprime la propria opposizione al momento della prenotazione.</p>

<h3>5. Incasso e ripasso</h3>
<p>La Piattaforma incassa il corrispettivo dal paziente per conto del Terapeuta, applicando una <strong>commissione di gestione</strong> pari al 30% del valore lordo della prestazione. Il ripasso del 70% è effettuato al Terapeuta mediante bonifico bancario sull'IBAN indicato, con cadenza <strong>mensile</strong>, entro il giorno 10 del mese successivo.</p>

<h3>6. Fattura di commissione</h3>
<p>Sulla commissione trattenuta, la Piattaforma emette al Terapeuta una <strong>fattura elettronica</strong> mensile ex art. 21 DPR 633/72, con applicazione IVA al 22%.</p>

<h3>7. Durata e recesso</h3>
<p>Il presente mandato è a tempo indeterminato. Ciascuna parte può recedere con preavviso di 30 giorni, salvo diritto di completare le prenotazioni già confermate.</p>

<h3>8. Legge applicabile</h3>
<p>Il presente contratto è disciplinato dalla legge italiana. Foro competente esclusivo: Pordenone.</p>
""".strip()
    now = datetime.now(timezone.utc)
    await db.contracts.insert_one({
        "kind": "mandato_all_incasso",
        "title": "Mandato all'incasso con Rappresentanza",
        "content_html": default_html,
        "content_hash": _hash_contract(default_html),
        "version": 1,
        "effective_date": now.isoformat(),
        "is_current": True,
        "created_at": now,
        "created_by": "system_seed",
    })
    logging.info("[CONTRACT] seeded default Mandato all'incasso v1")


# ─── Legal documents seed (Privacy, Cookie, Termini, Contratto Collaborazione) ─
LEGAL_DOCS_DIR = Path(__file__).parent.parent / "memory" / "legal"
DATA_PUBBLICAZIONE = "15 febbraio 2026"

LEGAL_DOCS_TO_SEED = [
    {
        "kind": "privacy_visitatori",
        "title": "Informativa Privacy — Visitatori del Sito",
        "filename": "informativa_privacy_visitatori.md",
    },
    {
        "kind": "privacy_pazienti",
        "title": "Informativa Privacy — Pazienti Registrati",
        "filename": "informativa_privacy_pazienti.md",
    },
    {
        "kind": "privacy_terapeuti",
        "title": "Informativa Privacy — Terapeuti (incl. DPA art. 28 GDPR)",
        "filename": "informativa_privacy_terapeuti.md",
    },
    {
        "kind": "cookie_policy",
        "title": "Cookie Policy",
        "filename": "cookie_policy.md",
    },
    {
        "kind": "termini_pazienti",
        "title": "Termini e Condizioni di Utilizzo — Pazienti",
        "filename": "termini_e_condizioni_pazienti.md",
    },
    {
        "kind": "contratto_collaborazione",
        "title": "Contratto di Collaborazione Professionale",
        "filename": "contratto_collaborazione.md",
    },
]


def _markdown_to_html(md_text: str) -> str:
    """Convert Markdown to sanitized HTML using markdown-it-py."""
    try:
        from markdown_it import MarkdownIt
        md = MarkdownIt("commonmark", {"html": False, "linkify": True, "typographer": True})
        md.enable(["table", "strikethrough"])
        return md.render(md_text)
    except ImportError:
        # Fallback: return the markdown as-is inside <pre> — should not happen since markdown-it-py is in requirements
        logging.warning("[LEGAL SEED] markdown-it-py not available, falling back to <pre>")
        import html as _html
        return f"<pre>{_html.escape(md_text)}</pre>"


async def _seed_legal_documents():
    """Seed the 6 legal documents (Privacy Visitatori, Privacy Pazienti,
    Privacy Terapeuti, Cookie Policy, Termini Pazienti, Contratto Collaborazione)
    from Markdown files in /app/memory/legal/ as version 1.

    Idempotent: only inserts if the kind has no existing version.
    """
    if not LEGAL_DOCS_DIR.exists():
        logging.warning(f"[LEGAL SEED] directory not found: {LEGAL_DOCS_DIR}")
        return

    for doc in LEGAL_DOCS_TO_SEED:
        kind = doc["kind"]
        # Skip if any version already exists — admin can create new versions in-app
        existing = await db.contracts.find_one({"kind": kind})
        if existing:
            continue
        md_path = LEGAL_DOCS_DIR / doc["filename"]
        if not md_path.exists():
            logging.warning(f"[LEGAL SEED] file not found: {md_path}")
            continue
        try:
            md_text = md_path.read_text(encoding="utf-8")
            # Substitute the publication-date placeholder
            md_text = md_text.replace("[DATA_PUBBLICAZIONE]", DATA_PUBBLICAZIONE)
            html_content = _markdown_to_html(md_text)
            now = datetime.now(timezone.utc)
            await db.contracts.insert_one({
                "kind": kind,
                "title": doc["title"],
                "content_html": html_content,
                "content_hash": _hash_contract(html_content),
                "version": 1,
                "effective_date": now.isoformat(),
                "is_current": True,
                "created_at": now,
                "created_by": "system_seed",
                "source_markdown": md_text,  # kept for future markdown-based editing
            })
            logging.info(f"[LEGAL SEED] seeded {kind} v1 ({len(html_content)} chars HTML)")
        except Exception as e:
            logging.exception(f"[LEGAL SEED] failed for {kind}: {e}")



async def _seed_registro_trattamenti():
    """Seed initial GDPR Art. 30 register entries if collection is empty."""
    if await db.registro_trattamenti.count_documents({}) > 0:
        return
    now = datetime.now(timezone.utc)
    default_entries = [
        {
            "codice": "T-01",
            "denominazione": "Gestione account e autenticazione",
            "ruolo": "titolare",
            "finalita": "Registrazione utenti (pazienti, terapisti, admin), verifica email tramite OTP, autenticazione, gestione sessioni, recupero password.",
            "base_giuridica": "Art. 6.1.b GDPR — esecuzione di misure precontrattuali/contrattuali; Art. 6.1.f — legittimo interesse alla sicurezza degli accessi.",
            "categorie_interessati": "Pazienti, Terapisti, Amministratori.",
            "categorie_dati": "Dati identificativi (nome, cognome), dati di contatto (email, telefono), credenziali (hash bcrypt), token di sessione (JWT httpOnly), log di accesso, IP anonimizzato.",
            "categorie_particolari": "Nessuna.",
            "destinatari": "Resend (invio email OTP e transazionali) — Titolare autonomo per la consegna. Nessun altro destinatario esterno.",
            "trasferimenti_extra_ue": "Resend Inc. (USA) — copertura SCC Clausole Contrattuali Standard UE ex art. 46 GDPR.",
            "misure_sicurezza": "Password hashate con bcrypt (cost 12), JWT httpOnly + secure cookie, HTTPS obbligatorio, rate limiting sui tentativi di login, anonimizzazione IP (ultimo ottetto), audit trail su modifiche account.",
            "termini_cancellazione": "Account attivi: fino a cancellazione richiesta dall'utente o inattività 36 mesi (anonimizzazione automatica); log di accesso 12 mesi; token reset password 30 minuti; token verifica OTP 10 minuti.",
            "note": "",
        },
        {
            "codice": "T-02",
            "denominazione": "Matching paziente-terapeuta e questionario pre-prenotazione",
            "ruolo": "titolare",
            "finalita": "Raccogliere le esigenze del paziente tramite questionario pubblico per proporre terapisti compatibili prima della prenotazione.",
            "base_giuridica": "Art. 6.1.b GDPR — esecuzione di misure precontrattuali su richiesta dell'interessato.",
            "categorie_interessati": "Visitatori del sito e Pazienti prospect.",
            "categorie_dati": "Preferenze terapeutiche (aree di intervento, tipologia di supporto), disponibilità oraria, fascia di età, genere del terapeuta preferito.",
            "categorie_particolari": "Dati potenzialmente relativi allo stato di salute psicologica raccolti in forma di preferenza — trattati con base ex art. 9.2.a GDPR (consenso esplicito acquisito tramite checkbox al lancio del questionario).",
            "destinatari": "Solo interno — nessuna condivisione con terzi.",
            "trasferimenti_extra_ue": "Nessun trasferimento extra-UE.",
            "misure_sicurezza": "Dati salvati in sessione temporanea, non persistiti su DB fino alla registrazione dell'account. Trasmissione HTTPS. Accesso limitato al sistema di matching.",
            "termini_cancellazione": "Se il paziente non completa la registrazione entro 72 ore: dati cancellati automaticamente. Se completa: confluiscono nel profilo Paziente (voce T-03).",
            "note": "",
        },
        {
            "codice": "T-03",
            "denominazione": "Gestione anagrafe pazienti e fatturazione sanitaria",
            "ruolo": "titolare",
            "finalita": "Raccolta dati anagrafici e fiscali per la prenotazione delle sedute, l'emissione della fattura sanitaria in nome del terapeuta (mandato all'incasso), la trasmissione al Sistema Tessera Sanitaria.",
            "base_giuridica": "Art. 6.1.b GDPR (esecuzione contratto); Art. 6.1.c (obblighi fiscali DPR 633/72, D.M. 31/07/2015 STS); Art. 9.2.h (finalità di cura).",
            "categorie_interessati": "Pazienti.",
            "categorie_dati": "Anagrafe completa (nome, cognome, data e luogo di nascita, genere, residenza), Codice Fiscale, dati di contatto, dati di pagamento (via Stripe token, mai raw PAN).",
            "categorie_particolari": "Dati sanitari (relativi al fatto di ricevere una prestazione psicologica) — art. 9.2.h GDPR e opposizione STS ex D.M. 31/07/2015.",
            "destinatari": "Stripe Payments Europe (elaborazione pagamento — Responsabile del Trattamento con DPA); Terapeuta che eroga la prestazione (Titolare autonomo per la cartella clinica); Sistema Tessera Sanitaria (Agenzia delle Entrate); commercialista BIDOC (Responsabile).",
            "trasferimenti_extra_ue": "Stripe: USA con SCC UE. Nessun altro trasferimento.",
            "misure_sicurezza": "Cifratura at-rest (MongoDB Atlas), TLS 1.3 in transito, tokenizzazione PAN via Stripe, log audit su accessi ai dati sanitari, pseudonimizzazione in reportistica interna, opposizione STS documentata al momento della prenotazione.",
            "termini_cancellazione": "Anagrafe: fino a cancellazione utente o 36 mesi inattività (anonimizzazione). Dati fiscali (fatture): 10 anni ex art. 2220 c.c. Dati STS: come da normativa AdE.",
            "note": "",
        },
        {
            "codice": "T-04",
            "denominazione": "Gestione albo terapisti e profilo pubblico",
            "ruolo": "titolare",
            "finalita": "Verifica requisiti professionali (iscrizione all'Albo, assicurazione RC professionale), gestione profilo pubblico, calendario e disponibilità.",
            "base_giuridica": "Art. 6.1.b GDPR (contratto di collaborazione); Art. 6.1.c (obblighi di verifica ex D.Lgs. 82/2005 e Codice Deontologico Psicologi).",
            "categorie_interessati": "Terapisti collaboratori.",
            "categorie_dati": "Anagrafica, P.IVA, Codice Fiscale, numero e ordine iscrizione Albo, dati assicurazione (compagnia, polizza, scadenza), biografia, specializzazioni, foto profilo, IBAN per bonifici, codice SDI/PEC per fatturazione elettronica.",
            "categorie_particolari": "Nessuna.",
            "destinatari": "Visitatori del sito (dati pubblici del profilo terapeuta); istituto bancario per bonifici; commercialista BIDOC.",
            "trasferimenti_extra_ue": "Nessun trasferimento extra-UE.",
            "misure_sicurezza": "Autocertificazione firmata digitalmente (art. 46 DPR 445/2000), verifica documentale su copia dei documenti caricati, alert automatico scadenza assicurazione a 60/30 gg, cifratura at-rest.",
            "termini_cancellazione": "Durante la collaborazione: attivo. Cessazione: dati fiscali/contrattuali conservati 10 anni ex art. 2220 c.c.; dati profilo pubblico cancellati entro 30 giorni.",
            "note": "",
        },
        {
            "codice": "T-05",
            "denominazione": "Gestione appuntamenti e videoconsulto",
            "ruolo": "responsabile",
            "finalita": "Gestione del calendario appuntamenti, generazione della stanza di videoconsulto, invio promemoria.",
            "base_giuridica": "Art. 28 GDPR — designazione a Responsabile del trattamento da parte del Terapeuta (Titolare del rapporto sanitario). DPA integrato nel Contratto di Collaborazione.",
            "categorie_interessati": "Pazienti (rispetto al terapeuta come titolare).",
            "categorie_dati": "Metadati appuntamento (data, ora, durata, stato), link videoconsulto (URL temporaneo), promemoria via email.",
            "categorie_particolari": "Nessuna (i contenuti clinici non transitano dalla Piattaforma).",
            "destinatari": "Daily.co (videoconferenza — Sub-Responsabile ex art. 28.4 GDPR).",
            "trasferimenti_extra_ue": "Daily.co (USA) — SCC UE + Data Processing Agreement.",
            "misure_sicurezza": "Videoconsulto end-to-end encrypted (SRTP/DTLS), stanze temporanee con token JWT a scadenza, nessuna registrazione video lato piattaforma, log accessi.",
            "termini_cancellazione": "Metadati appuntamento: 10 anni (obbligo fiscale collegato). Link videoconsulto: cancellati alla scadenza della sessione.",
            "note": "",
        },
        {
            "codice": "T-06",
            "denominazione": "Fatturazione elettronica di commissione B2B",
            "ruolo": "titolare",
            "finalita": "Emissione delle fatture elettroniche di commissione (30%) dovute dal Terapeuta a BIDOC, generazione XML FatturaPA e archiviazione.",
            "base_giuridica": "Art. 6.1.b GDPR (contratto); Art. 6.1.c (obblighi fiscali D.Lgs. 127/2015).",
            "categorie_interessati": "Terapisti collaboratori.",
            "categorie_dati": "Denominazione, P.IVA, CF, indirizzo di sede, codice SDI/PEC, importo prestazioni del mese, dettaglio sedute conteggiate.",
            "categorie_particolari": "Nessuna.",
            "destinatari": "Sistema di Interscambio dell'Agenzia delle Entrate (SDI); commercialista BIDOC.",
            "trasferimenti_extra_ue": "Nessun trasferimento extra-UE.",
            "misure_sicurezza": "XML firmato e archiviato in Object Storage, backup crittografato, accesso admin autenticato, retention 10 anni.",
            "termini_cancellazione": "10 anni ex art. 2220 c.c. e D.Lgs. 127/2015.",
            "note": "",
        },
        {
            "codice": "T-07",
            "denominazione": "Comunicazioni transazionali",
            "ruolo": "titolare",
            "finalita": "Invio email di conferma prenotazione, promemoria seduta, ricevute di firma documenti legali, notifiche di aggiornamento contratti/informative (MAJOR update).",
            "base_giuridica": "Art. 6.1.b GDPR (contratto) — non richiede consenso opt-in perché strettamente necessarie all'esecuzione del servizio.",
            "categorie_interessati": "Pazienti, Terapisti.",
            "categorie_dati": "Email, nome, contenuto notifica (dati appuntamento o documento).",
            "categorie_particolari": "Nessuna.",
            "destinatari": "Resend (mail transazionale — Responsabile).",
            "trasferimenti_extra_ue": "Resend (USA) con SCC UE.",
            "misure_sicurezza": "SPF/DKIM/DMARC sul dominio funzionabene.it, TLS in transito, rate limiting anti-abuse.",
            "termini_cancellazione": "Metadati invio conservati 12 mesi per audit. Contenuto email non persistito lato Piattaforma dopo l'invio.",
            "note": "",
        },
        {
            "codice": "T-08",
            "denominazione": "Marketing diretto (newsletter e comunicazioni promozionali)",
            "ruolo": "titolare",
            "finalita": "Invio comunicazioni promozionali su nuovi servizi, articoli del blog, contenuti educativi.",
            "base_giuridica": "Art. 6.1.a GDPR — consenso esplicito opt-in del paziente (checkbox al momento della registrazione, revocabile in qualsiasi momento).",
            "categorie_interessati": "Pazienti che hanno prestato consenso.",
            "categorie_dati": "Email, nome, preferenze.",
            "categorie_particolari": "Nessuna.",
            "destinatari": "Brevo (mail marketing — Responsabile).",
            "trasferimenti_extra_ue": "Brevo (Francia) — dentro l'UE. Nessun trasferimento extra-UE.",
            "misure_sicurezza": "Doppio opt-in (email di conferma), link di disiscrizione one-click in ogni comunicazione, revoca consenso registrata in `consent_history`.",
            "termini_cancellazione": "Fino a revoca del consenso o cancellazione dell'account.",
            "note": "",
        },
        {
            "codice": "T-09",
            "denominazione": "Analisi statistica e miglioramento del servizio",
            "ruolo": "titolare",
            "finalita": "Raccolta di dati aggregati e pseudonimizzati per capire l'utilizzo della Piattaforma e migliorare l'esperienza utente.",
            "base_giuridica": "Art. 6.1.a GDPR (consenso opt-in cookie di statistica).",
            "categorie_interessati": "Visitatori, Pazienti, Terapisti.",
            "categorie_dati": "Metadati di navigazione (pagine visitate, durata, referrer), dispositivo, browser, tempo medio di completamento del questionario, tasso di conversione.",
            "categorie_particolari": "Nessuna.",
            "destinatari": "Solo interno.",
            "trasferimenti_extra_ue": "Nessun trasferimento extra-UE.",
            "misure_sicurezza": "Pseudonimizzazione con hash salato, aggregazione per fasce di utenti > 5, cookie di statistica solo previo consenso.",
            "termini_cancellazione": "Dati aggregati: 24 mesi. Cookie di statistica: come da Cookie Policy (13 mesi).",
            "note": "",
        },
        {
            "codice": "T-10",
            "denominazione": "Sicurezza e prevenzione frodi",
            "ruolo": "titolare",
            "finalita": "Log degli accessi, monitoraggio tentativi di login sospetti, rilevamento anomalie sui pagamenti.",
            "base_giuridica": "Art. 6.1.f GDPR — legittimo interesse alla sicurezza della Piattaforma e degli utenti.",
            "categorie_interessati": "Tutti gli utenti.",
            "categorie_dati": "IP anonimizzato, User-Agent, timestamp, esito login, endpoint richiesto.",
            "categorie_particolari": "Nessuna.",
            "destinatari": "Amministratori BIDOC; su richiesta, Autorità giudiziaria/Polizia Postale.",
            "trasferimenti_extra_ue": "Nessun trasferimento extra-UE.",
            "misure_sicurezza": "IP mascherato (ultimo ottetto IPv4, /48 IPv6), lock automatico account dopo 5 tentativi falliti, MFA opzionale per amministratori.",
            "termini_cancellazione": "Log accessi: 12 mesi (art. 132 Codice Privacy per obblighi telematici). Log anomalie: 24 mesi.",
            "note": "",
        },
    ]
    for e in default_entries:
        await db.registro_trattamenti.insert_one({
            **e,
            "archived": False,
            "created_at": now,
            "updated_at": now,
            "created_by": "system_seed",
            "updated_by": "system_seed",
        })
    logging.info(f"[REGISTRO SEED] Inserted {len(default_entries)} default Art. 30 GDPR entries")


async def seed_data():
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@funzionabene.it")
    admin_pwd = os.environ.get("ADMIN_PASSWORD", "admin2026")
    existing = await db.users.find_one({"email": admin_email})
    if not existing:
        await db.users.insert_one({
            "email": admin_email,
            "password_hash": hash_password(admin_pwd),
            "nome": "Amministratore",
            "cognome": "FunzionaBene",
            "role": "admin",
            "is_verified": True,
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        })
        logging.info(f"[SEED] Admin creato: {admin_email}")
    else:
        # Always keep admin password in sync with env var ADMIN_PASSWORD.
        # Ensures password reset is possible via redeploy when forgotten.
        if not verify_password(admin_pwd, existing.get("password_hash", "")):
            await db.users.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "password_hash": hash_password(admin_pwd),
                    "is_verified": True,
                    "is_active": True,
                }},
            )
            logging.info(f"[SEED] Admin password resynced from env var for: {admin_email}")

    # Skip demo data in production. Set SEED_DEMO_DATA=true to enable in dev/staging.
    if os.environ.get("SEED_DEMO_DATA", "false").lower() != "true":
        logging.info("[SEED] SEED_DEMO_DATA is false — skipping demo therapists/patients/payouts")
        return

    # Seed demo therapist
    demo_email = "demo.terapeuta@funzionabene.it"
    demo_pwd = "terapeuta2026"
    demo_user = await db.users.find_one({"email": demo_email})
    if not demo_user:
        result = await db.users.insert_one({
            "email": demo_email,
            "password_hash": hash_password(demo_pwd),
            "nome": "Maria",
            "cognome": "Rossi",
            "role": "terapeuta",
            "is_verified": True,
            "is_active": True,
            "approval_status": "approvato",
            "created_at": datetime.now(timezone.utc)
        })
        await db.terapisti.insert_one({
            "user_id": str(result.inserted_id),
            "nome": "Maria",
            "cognome": "Rossi",
            "email": demo_email,
            "telefono": "+39 02 1234567",
            "bio": "Psicologa e sessuologa clinica con 12 anni di esperienza. Approccio integrato cognitivo-comportamentale e sistemico.",
            "anni_esperienza": 12,
            "specializzazioni": ["Sessuologia clinica", "Terapia di coppia", "Disfunzioni sessuali"],
            "formazione": [
                {"titolo": "Laurea in Psicologia Clinica", "istituto": "Università La Sapienza, Roma", "anno": 2010},
                {"titolo": "Specializzazione in Sessuologia", "istituto": "IISS, Milano", "anno": 2013}
            ],
            "approccio_terapeutico": "Cognitivo-Comportamentale integrato",
            "genere": "F",
            "albo_numero": "12345",
            "albo_ordine": "Ordine degli Psicologi della Lombardia",
            "albo_iscrizione_data": "2011-03-15",
            "assicurazione_compagnia": "Generali",
            "assicurazione_numero_polizza": "POL-2024-001",
            "assicurazione_scadenza": "2025-12-31",
            "prezzo_sessione": 90.0,
            "lingue": ["Italiano", "Inglese"],
            "autocertificazione_firmata": True,
            "autocertificazione_data": datetime.now(timezone.utc),
            "disponibilita": [
                {"giorno": "Lunedì", "ora_inizio": "09:00", "ora_fine": "18:00"},
                {"giorno": "Mercoledì", "ora_inizio": "09:00", "ora_fine": "18:00"},
                {"giorno": "Venerdì", "ora_inizio": "09:00", "ora_fine": "14:00"}
            ],
            "created_at": datetime.now(timezone.utc)
        })
        logging.info("[SEED] Demo terapeuta creato")
    else:
        # Resync demo therapist password on each boot for redeploy recovery
        if not verify_password(demo_pwd, demo_user.get("password_hash", "")):
            await db.users.update_one(
                {"_id": demo_user["_id"]},
                {"$set": {"password_hash": hash_password(demo_pwd), "is_verified": True, "is_active": True}},
            )
            logging.info(f"[SEED] Demo terapeuta password resynced: {demo_email}")

    # Seed 4 additional fake therapists with generated portrait photos
    ADDITIONAL = [
        {
            "email": "alessandro.conti@funzionabene.it",
            "nome": "Alessandro", "cognome": "Conti", "genere": "M",
            "foto": "alessandro_conti.png", "prezzo": 79.0, "anni": 28,
            "bio": "Psicoterapeuta e sessuologo, 28 anni di pratica clinica. Specializzato in disfunzioni sessuali legate all'ansia da prestazione e nei percorsi di coppia di lunga durata.",
            "specializzazioni": ["Ansia da prestazione", "Disfunzione erettile", "Terapia di coppia"],
            "approccio": "Integrato: cognitivo-comportamentale e psicodinamico breve",
            "formazione": [
                {"titolo": "Laurea in Medicina e Chirurgia", "istituto": "Università di Bologna", "anno": 1992},
                {"titolo": "Specializzazione in Psichiatria", "istituto": "Università di Bologna", "anno": 1998},
                {"titolo": "Master in Sessuologia Clinica", "istituto": "IISS, Milano", "anno": 2002},
            ],
            "albo_num": "7823", "albo_ord": "Ordine degli Psicologi dell'Emilia-Romagna",
            "disp": [
                {"giorno": "Martedì", "ora_inizio": "14:00", "ora_fine": "20:00"},
                {"giorno": "Giovedì", "ora_inizio": "14:00", "ora_fine": "20:00"},
            ],
        },
        {
            "email": "giulia.marchetti@funzionabene.it",
            "nome": "Giulia", "cognome": "Marchetti", "genere": "F",
            "foto": "giulia_marchetti.png", "prezzo": 65.0, "anni": 9,
            "bio": "Psicologa e sessuologa, approccio femminile e caloroso. Mi dedico con particolare attenzione al benessere sessuale femminile, all'anorgasmia e al vaginismo.",
            "specializzazioni": ["Anorgasmia", "Vaginismo", "Dispareunia", "Mindfulness sessuale"],
            "approccio": "Mindfulness-based e psicocorporeo",
            "formazione": [
                {"titolo": "Laurea in Psicologia Clinica", "istituto": "Università di Padova", "anno": 2013},
                {"titolo": "Specializzazione in Psicoterapia sistemico-relazionale", "istituto": "Scuola Mara Selvini, Milano", "anno": 2017},
                {"titolo": "Formazione in Mindful Sex", "istituto": "Lori Brotto Method", "anno": 2020},
            ],
            "albo_num": "18456", "albo_ord": "Ordine degli Psicologi del Veneto",
            "disp": [
                {"giorno": "Lunedì", "ora_inizio": "09:00", "ora_fine": "13:00"},
                {"giorno": "Mercoledì", "ora_inizio": "09:00", "ora_fine": "13:00"},
                {"giorno": "Sabato", "ora_inizio": "09:00", "ora_fine": "13:00"},
            ],
        },
        {
            "email": "marco.fontana@funzionabene.it",
            "nome": "Marco", "cognome": "Fontana", "genere": "M",
            "foto": "marco_fontana.png", "prezzo": 55.0, "anni": 5,
            "bio": "Sessuologo specializzato in tematiche LGBTQIA+, identità di genere, coming out e relazioni non tradizionali. Uno spazio davvero libero da giudizi.",
            "specializzazioni": ["LGBTQIA+", "Identità di genere", "Orientamento sessuale", "Poliamore"],
            "approccio": "Affirmative Therapy, approccio non normativo",
            "formazione": [
                {"titolo": "Laurea in Psicologia", "istituto": "Università La Sapienza, Roma", "anno": 2018},
                {"titolo": "Corso di Perfezionamento in Sessuologia", "istituto": "FISS, Roma", "anno": 2020},
                {"titolo": "Formazione in Gender Affirmative Care", "istituto": "WPATH Standard of Care", "anno": 2022},
            ],
            "albo_num": "21890", "albo_ord": "Ordine degli Psicologi del Lazio",
            "disp": [
                {"giorno": "Martedì", "ora_inizio": "16:00", "ora_fine": "21:00"},
                {"giorno": "Giovedì", "ora_inizio": "16:00", "ora_fine": "21:00"},
                {"giorno": "Venerdì", "ora_inizio": "10:00", "ora_fine": "18:00"},
            ],
        },
        {
            "email": "chiara.esposito@funzionabene.it",
            "nome": "Chiara", "cognome": "Esposito", "genere": "F",
            "foto": "chiara_esposito.png", "prezzo": 85.0, "anni": 18,
            "bio": "Psicoterapeuta e sessuologa con focus su traumi sessuali, abusi e disturbi post-traumatici. Certificata EMDR. Approccio rispettoso dei tuoi tempi.",
            "specializzazioni": ["Traumi sessuali", "Abusi", "EMDR", "Sessualità in menopausa"],
            "approccio": "EMDR, trauma-focused CBT",
            "formazione": [
                {"titolo": "Laurea in Psicologia Clinica", "istituto": "Università Federico II, Napoli", "anno": 2003},
                {"titolo": "Specializzazione in Psicoterapia Cognitivo-Comportamentale", "istituto": "APC, Roma", "anno": 2008},
                {"titolo": "Certificazione EMDR livello II", "istituto": "EMDR Italia", "anno": 2011},
                {"titolo": "Master in Sessuologia Clinica", "istituto": "IISS, Milano", "anno": 2015},
            ],
            "albo_num": "9245", "albo_ord": "Ordine degli Psicologi della Campania",
            "disp": [
                {"giorno": "Lunedì", "ora_inizio": "14:00", "ora_fine": "19:00"},
                {"giorno": "Mercoledì", "ora_inizio": "14:00", "ora_fine": "19:00"},
                {"giorno": "Venerdì", "ora_inizio": "09:00", "ora_fine": "13:00"},
            ],
        },
    ]
    for t in ADDITIONAL:
        if await db.users.find_one({"email": t["email"]}):
            continue
        uid = (await db.users.insert_one({
            "email": t["email"], "password_hash": hash_password("Terapeuta#2024!"),
            "nome": t["nome"], "cognome": t["cognome"], "role": "terapeuta",
            "is_verified": True, "is_active": True, "approval_status": "approvato",
            "created_at": datetime.now(timezone.utc),
        })).inserted_id
        await db.terapisti.insert_one({
            "user_id": str(uid),
            "nome": t["nome"], "cognome": t["cognome"], "email": t["email"],
            "telefono": "+39 02 0000000",
            "bio": t["bio"], "anni_esperienza": t["anni"],
            "specializzazioni": t["specializzazioni"],
            "formazione": t["formazione"],
            "approccio_terapeutico": t["approccio"],
            "genere": t["genere"],
            "albo_numero": t["albo_num"], "albo_ordine": t["albo_ord"],
            "albo_iscrizione_data": "2010-01-01",
            "assicurazione_compagnia": "Generali",
            "assicurazione_numero_polizza": f"POL-{t['albo_num']}",
            "assicurazione_scadenza": "2026-12-31",
            "prezzo_sessione": t["prezzo"],
            "lingue": ["Italiano"],
            "autocertificazione_firmata": True,
            "autocertificazione_data": datetime.now(timezone.utc),
            "foto_url": f"/api/media/therapists/{t['foto']}",
            "disponibilita": t["disp"],
            "created_at": datetime.now(timezone.utc),
        })
        logging.info(f"[SEED] Terapeuta creato: {t['nome']} {t['cognome']}")

    # Seed demo patient
    demo_paz_email = "demo.paziente@funzionabene.it"
    demo_paz_pwd = "paziente2026"
    demo_paz = await db.users.find_one({"email": demo_paz_email})
    if not demo_paz:
        result2 = await db.users.insert_one({
            "email": demo_paz_email,
            "password_hash": hash_password(demo_paz_pwd),
            "nome": "Luca",
            "cognome": "Bianchi",
            "role": "paziente",
            "is_verified": True,
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        })
        await db.pazienti.insert_one({
            "user_id": str(result2.inserted_id),
            "nome": "Luca",
            "cognome": "Bianchi",
            "data_nascita": "1990-05-15",
            "genere": "M",
            "codice_fiscale": "RSSMRA80A01F205X",
            "telefono": "+39 333 1234567",
            "citta": "Milano",
            "cap": "20121",
            "created_at": datetime.now(timezone.utc)
        })
        logging.info("[SEED] Demo paziente creato")
    else:
        if not verify_password(demo_paz_pwd, demo_paz.get("password_hash", "")):
            await db.users.update_one(
                {"_id": demo_paz["_id"]},
                {"$set": {"password_hash": hash_password(demo_paz_pwd), "is_verified": True, "is_active": True}},
            )
            logging.info(f"[SEED] Demo paziente password resynced: {demo_paz_email}")

    # ── Seed demo pending payout (for Cruscotto KPI "Payout Pendenti" demo) ──
    try:
        # Track by _seed:true marker so if a previous seeded row was marked paid
        # during testing, we re-create a fresh pending one on next boot.
        has_pending_seed = await db.payment_transactions.find_one({
            "_seed": True,
            "payment_status": "paid",
            "payout_status": {"$ne": "paid"},
        })
        if not has_pending_seed:
            demo_terapista = await db.terapisti.find_one({"email": "giulia.marchetti@funzionabene.it"})
            demo_paz_doc = await db.pazienti.find_one({}) if not demo_terapista else await db.pazienti.find_one({})
            demo_paz_user = await db.users.find_one({"email": demo_paz_email})
            if demo_terapista and demo_paz_doc and demo_paz_user:
                paid_at = datetime.now(timezone.utc) - timedelta(days=3)
                amount_cents = int((demo_terapista.get("prezzo_sessione", 65.0)) * 100)
                platform_fee_cents = int(round(amount_cents * 0.30))
                therapist_amount_cents = amount_cents - platform_fee_cents
                await db.payment_transactions.insert_one({
                    "session_id": f"demo_seed_pending_{int(paid_at.timestamp())}",
                    "appointment_id": None,
                    "terapeuta_id": str(demo_terapista["_id"]),
                    "paziente_id": str(demo_paz_doc["_id"]),
                    "paziente_user_id": str(demo_paz_user["_id"]),
                    "amount": amount_cents,
                    "currency": "eur",
                    "platform_fee_amount": platform_fee_cents,
                    "platform_fee_percent": 30,
                    "therapist_amount": therapist_amount_cents,
                    "opposizione_ts": False,
                    "marca_da_bollo_required": False,
                    "marca_da_bollo_amount": 0,
                    "fattura_sanitaria_status": "da_emettere",
                    "status": "completed",
                    "payment_status": "paid",
                    "payout_status": "pending",
                    "paid_at": paid_at,
                    "created_at": paid_at,
                    "updated_at": paid_at,
                    "_seed": True,
                })
                logging.info(f"[SEED] Demo pending payout creato per {demo_terapista.get('nome')} {demo_terapista.get('cognome')} (€{therapist_amount_cents/100:.2f})")
    except Exception as e:
        logging.warning(f"[SEED] pending payout seed skipped: {e}")

@app.on_event("shutdown")
async def shutdown():
    stop_scheduler()
    client.close()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
