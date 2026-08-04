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
    get_current_user, require_admin, require_auth,
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
@api_router.post("/auth/register")
async def register(data: RegisterInput, response: Response):
    email = data.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email già registrata")
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password deve avere almeno 8 caratteri")
    if data.role not in ["paziente", "terapeuta"]:
        raise HTTPException(status_code=400, detail="Ruolo non valido")

    otp_code = generate_otp()
    otp_expires = datetime.now(timezone.utc) + timedelta(minutes=10)

    user_doc = {
        "email": email,
        "password_hash": hash_password(data.password),
        "nome": data.nome,
        "cognome": data.cognome,
        "role": data.role,
        "is_verified": False,
        "is_active": True,
        "otp_code": otp_code,
        "otp_expires": otp_expires,
        "consenso_privacy": data.consenso_privacy,
        "created_at": datetime.now(timezone.utc)
    }
    if data.role == "terapeuta":
        user_doc["approval_status"] = "pending"

    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)

    # Create empty profile
    if data.role == "paziente":
        await db.pazienti.insert_one({
            "user_id": user_id, "nome": data.nome, "cognome": data.cognome,
            "created_at": datetime.now(timezone.utc)
        })
    else:
        await db.terapisti.insert_one({
            "user_id": user_id, "nome": data.nome, "cognome": data.cognome,
            "autocertificazione_firmata": False,
            "created_at": datetime.now(timezone.utc)
        })

    logging.info(f"[OTP] {email}: {otp_code}")
    email_sent = await send_otp_email(email, otp_code, data.nome)
    response_body = {"message": "Registrazione completata. Controlla la tua email per il codice OTP."}
    # Always expose otp_dev when EXPOSE_OTP_DEV=true (useful for testing when email delivery is unreliable)
    expose_dev = os.environ.get("EXPOSE_OTP_DEV", "false").lower() == "true"
    if not email_sent or expose_dev:
        response_body["otp_dev"] = otp_code
    return response_body

@api_router.post("/auth/verify-otp")
async def verify_otp(data: OTPInput, response: Response):
    email = data.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    if user.get("is_verified"):
        raise HTTPException(status_code=400, detail="Account già verificato")
    otp_expires = user.get("otp_expires")
    if otp_expires:
        if isinstance(otp_expires, str):
            otp_expires = datetime.fromisoformat(otp_expires)
        if otp_expires.tzinfo is None:
            otp_expires = otp_expires.replace(tzinfo=timezone.utc)
    if not otp_expires or datetime.now(timezone.utc) > otp_expires:
        raise HTTPException(status_code=400, detail="Codice OTP scaduto")
    if user.get("otp_code") != data.otp_code:
        raise HTTPException(status_code=400, detail="Codice OTP non valido")

    await db.users.update_one({"_id": user["_id"]}, {"$set": {"is_verified": True, "otp_code": None}})
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email, user["role"])
    refresh_token = create_refresh_token(user_id)
    response.set_cookie("access_token", access_token, httponly=True, samesite="none", secure=True, max_age=28800, path="/")
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="none", secure=True, max_age=604800, path="/")
    return {"message": "Account verificato con successo", "role": user["role"], "nome": user["nome"]}

@api_router.post("/auth/resend-otp")
async def resend_otp(body: dict):
    email = body.get("email", "").lower().strip()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    otp_code = generate_otp()
    otp_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"otp_code": otp_code, "otp_expires": otp_expires}})
    logging.info(f"[OTP Resend] {email}: {otp_code}")
    email_sent = await send_otp_email(email, otp_code, user.get("nome", ""))
    response_body = {"message": "Nuovo codice OTP inviato"}
    expose_dev = os.environ.get("EXPOSE_OTP_DEV", "false").lower() == "true"
    if not email_sent or expose_dev:
        response_body["otp_dev"] = otp_code
    return response_body

@api_router.post("/auth/login")
async def login(data: LoginInput, response: Response):
    email = data.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    if not user.get("is_verified") and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Account non verificato. Controlla la tua email per il codice OTP.")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account disattivato")

    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email, user["role"])
    refresh_token = create_refresh_token(user_id)
    response.set_cookie("access_token", access_token, httponly=True, samesite="none", secure=True, max_age=28800, path="/")
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="none", secure=True, max_age=604800, path="/")
    return {"_id": user_id, "email": email, "nome": user["nome"], "cognome": user["cognome"], "role": user["role"]}

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logout effettuato con successo"}

@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user

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

# ─── APPUNTAMENTI ─────────────────────────────────────────────────────────────

# ─── BLOG ─────────────────────────────────────────────────────────────────────
@api_router.get("/blog")
async def list_articoli(user: dict = Depends(require_auth)):
    if user["role"] == "terapeuta":
        docs = await db.articoli.find({"autore_id": user["_id"]}).sort("created_at", -1).to_list(100)
    else:
        docs = await db.articoli.find({}).sort("created_at", -1).to_list(100)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs

@api_router.post("/blog")
async def create_articolo(data: ArticoloInput, user: dict = Depends(require_auth)):
    if user["role"] not in ["terapeuta", "admin"]:
        raise HTTPException(status_code=403, detail="Accesso negato")
    doc = data.model_dump()
    doc["autore_id"] = user["_id"]
    doc["autore_nome"] = f"{user.get('nome','')} {user.get('cognome','')}".strip()
    doc["stato"] = "bozza" if user["role"] == "terapeuta" else "pubblicato"
    doc["created_at"] = datetime.now(timezone.utc)
    result = await db.articoli.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

@api_router.put("/blog/{art_id}")
async def update_articolo(art_id: str, data: ArticoloInput, user: dict = Depends(require_auth)):
    doc = await db.articoli.find_one({"_id": ObjectId(art_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Articolo non trovato")
    if user["role"] != "admin" and doc.get("autore_id") != user["_id"]:
        raise HTTPException(status_code=403, detail="Accesso negato")
    update = data.model_dump(exclude_none=True)
    update["updated_at"] = datetime.now(timezone.utc)
    await db.articoli.update_one({"_id": ObjectId(art_id)}, {"$set": update})
    doc = await db.articoli.find_one({"_id": ObjectId(art_id)})
    doc["_id"] = str(doc["_id"])
    return doc

@api_router.patch("/blog/{art_id}/approva")
async def approva_articolo(art_id: str, user: dict = Depends(require_admin)):
    await db.articoli.update_one(
        {"_id": ObjectId(art_id)},
        {"$set": {"stato": "pubblicato", "approvato_da": user["_id"], "approvato_il": datetime.now(timezone.utc)}}
    )
    return {"message": "Articolo approvato e pubblicato"}

@api_router.patch("/blog/{art_id}/rifiuta")
async def rifiuta_articolo(art_id: str, user: dict = Depends(require_admin)):
    await db.articoli.update_one(
        {"_id": ObjectId(art_id)},
        {"$set": {"stato": "rifiutato", "updated_at": datetime.now(timezone.utc)}}
    )
    return {"message": "Articolo rifiutato"}

@api_router.delete("/blog/{art_id}")
async def delete_articolo(art_id: str, user: dict = Depends(require_auth)):
    doc = await db.articoli.find_one({"_id": ObjectId(art_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Articolo non trovato")
    if user["role"] != "admin" and doc.get("autore_id") != user["_id"]:
        raise HTTPException(status_code=403, detail="Accesso negato")
    await db.articoli.delete_one({"_id": ObjectId(art_id)})
    return {"message": "Articolo eliminato"}


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
    docs = await db.terapisti.find({"documenti_verificati": True}).to_list(100)
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
    doc["_id"] = str(doc["_id"])
    doc.pop("documenti", None)
    doc.pop("note_cliniche", None)
    return doc

@api_router.post("/public/matching")
async def matching(data: MatchingInput):
    docs = await db.terapisti.find({"documenti_verificati": True}).to_list(100)
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

@api_router.get("/public/blog")
async def public_blog():
    docs = await db.articoli.find({"stato": "pubblicato"}).sort("created_at", -1).to_list(50)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs

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
async def _finalize_confirmed_booking(appointment_id: str, paziente_user: dict):
    """Provision Daily.co room + send confirmation emails + schedule reminders.
    Called AFTER the payment succeeds (webhook or polling)."""
    appt = await db.appuntamenti.find_one({"_id": ObjectId(appointment_id)})
    if not appt:
        return None
    # Idempotent: only create room if not present
    if not appt.get("daily_room_url"):
        room = await create_room_for_appointment(appointment_id, appt["data_ora"], appt["durata_minuti"])
        if room:
            await db.appuntamenti.update_one(
                {"_id": ObjectId(appointment_id)},
                {"$set": {"daily_room_url": room.get("room_url"), "daily_room_name": room.get("room_name")}},
            )
            appt["daily_room_url"] = room.get("room_url")
            appt["daily_room_name"] = room.get("room_name")
    # Skip emails if already sent
    if appt.get("_confirmation_email_sent"):
        return appt
    try:
        terapista = await db.terapisti.find_one({"_id": ObjectId(appt["terapeuta_id"])})
        paziente = await db.pazienti.find_one({"_id": ObjectId(appt["paziente_id"])})
        if terapista and paziente:
            t_user = await db.users.find_one({"_id": terapista.get("user_id")})
            ctx = {
                "paziente_nome": paziente.get("nome", ""),
                "paziente_cognome": paziente.get("cognome", ""),
                "paziente_email": paziente_user.get("email"),
                "terapista_nome": terapista.get("nome", ""),
                "terapista_cognome": terapista.get("cognome", ""),
                "terapista_email": t_user.get("email") if t_user else None,
                "data_ora": appt["data_ora"],
                "durata_minuti": appt["durata_minuti"],
                "prezzo": terapista.get("prezzo_sessione", 90),
                "room_url": appt.get("daily_room_url"),
                "app_id": appointment_id,
            }
            await send_booking_confirmation_email(ctx)
            schedule_reminders(appointment_id, ctx)
        await db.appuntamenti.update_one(
            {"_id": ObjectId(appointment_id)},
            {"$set": {"_confirmation_email_sent": True}},
        )
    except Exception as e:
        logging.error(f"[BOOKING EMAIL] failed: {e}")
    return appt


@api_router.post("/public/prenota")
async def prenota_pubblico(data: AppuntamentoInput, user: dict = Depends(require_auth)):
    if user["role"] != "paziente":
        raise HTTPException(403, "Solo i pazienti possono prenotare")
    # Require recent SMS phone verification (last 60 min) before confirming booking
    u_doc = await db.users.find_one({"_id": ObjectId(user["_id"])})
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
    """Trigger Twilio Verify to send an OTP by SMS. Twilio owns code lifecycle."""
    phone = (body.get("phone") or "").strip()
    context = (body.get("context") or "verifica").strip()[:40]
    if not phone:
        raise HTTPException(400, "Numero di telefono mancante")
    # Record the request for audit/rate-limiting (we no longer store the code)
    await db.sms_otp.update_one(
        {"user_id": user["_id"], "phone": phone},
        {"$set": {
            "user_id": user["_id"],
            "phone": phone,
            "verified": False,
            "provider": "twilio_verify",
            "context": context,
            "created_at": datetime.now(timezone.utc),
        }},
        upsert=True,
    )
    sent = await send_sms_otp(phone, "", context)
    logging.info(f"[SMS OTP] Twilio Verify send to {phone} (sent={sent}) for user {user['email']}")
    if not sent:
        raise HTTPException(502, "Impossibile inviare l'SMS. Riprova tra qualche minuto.")
    return {"message": "OTP inviato via SMS"}


@api_router.post("/sms/verify-otp")
async def sms_verify_otp(body: dict, user: dict = Depends(require_auth)):
    """Verify the SMS OTP via Twilio Verify. On success marks user telefono_verificato=True."""
    phone = (body.get("phone") or "").strip()
    code = (body.get("otp_code") or "").strip()
    if not phone or not code:
        raise HTTPException(400, "Dati incompleti")
    approved = await verify_sms_otp(phone, code)
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


# ─── Password Reset ──────────────────────────────────────────────────────────
# Follows OWASP Forgot Password Cheat Sheet:
# - crypto-secure single-use tokens (32 bytes URL-safe = 256 bits)
# - store only SHA-256 hash (raw token never persisted)
# - 30-minute expiration
# - generic responses (never reveal if email exists)
# - atomic consume via find_one_and_update
# - timing-safe comparison
import hmac as _hmac
import hashlib

RESET_TOKEN_MINUTES = 30
_DUMMY_HASH_FOR_TIMING = bcrypt.hashpw(b"timing-padding-unused", bcrypt.gensalt()).decode()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=40, max_length=512)
    new_password: str = Field(min_length=8, max_length=128)


def _token_digest(raw: str) -> str:
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def _get_frontend_origin(request: Request) -> str:
    """Prefer trusted config; fall back to Origin header only if not set."""
    env_url = os.environ.get("FRONTEND_URL") or os.environ.get("REACT_APP_BACKEND_URL")
    if env_url:
        return env_url.rstrip("/")
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    return origin.rstrip("/")


@api_router.post("/auth/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email}, {"_id": 1, "email": 1, "nome": 1})

    if user is None:
        # Timing equalization — perform bcrypt work in the not-found branch too.
        bcrypt.checkpw(b"timing-padding", _DUMMY_HASH_FOR_TIMING.encode())
    else:
        raw_token = _secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        # Invalidate any prior unused tokens for this user
        await db.password_reset_tokens.delete_many({
            "user_id": user["_id"], "used_at": None,
        })
        await db.password_reset_tokens.insert_one({
            "user_id": user["_id"],
            "token_hash": _token_digest(raw_token),
            "expires_at": now + timedelta(minutes=RESET_TOKEN_MINUTES),
            "used_at": None,
            "created_at": now,
        })
        frontend = _get_frontend_origin(request)
        reset_url = f"{frontend}/reset-password?token={raw_token}"
        try:
            await send_password_reset_email(email, reset_url, user.get("nome", ""))
        except Exception as e:
            logging.error(f"[RESET] email send exception: {e}")

    # Uniform response regardless of user existence.
    return {"message": "Se un account esiste con questa email, riceverai un link per il reset."}


@api_router.post("/auth/reset-password")
async def reset_password(body: ResetPasswordRequest):
    generic_error = HTTPException(400, "Il link di reset non è valido o è scaduto.")
    digest = _token_digest(body.token)
    now = datetime.now(timezone.utc)

    # Atomic single-use claim
    token_doc = await db.password_reset_tokens.find_one_and_update(
        {"token_hash": digest, "used_at": None, "expires_at": {"$gt": now}},
        {"$set": {"used_at": now}},
        projection={"user_id": 1, "token_hash": 1},
    )
    if token_doc is None:
        raise generic_error
    # Defensive timing-safe compare
    if not _hmac.compare_digest(token_doc["token_hash"], digest):
        raise generic_error

    new_hash = hash_password(body.new_password)
    result = await db.users.update_one(
        {"_id": token_doc["user_id"]},
        {"$set": {"password_hash": new_hash, "password_changed_at": now}},
    )
    if result.modified_count != 1:
        logging.error("[RESET] consumed token but user update failed")
        raise HTTPException(500, "Impossibile completare il reset.")

    return {"message": "Password reimpostata con successo. Ora puoi accedere."}



app.include_router(api_router)

# Mount modular routers under /api
from routers.admin_analytics import build_router as _build_admin_analytics_router
from routers.appuntamenti import router as _appuntamenti_router
from routers.terapisti import router as _terapisti_router
from routers.payments import router as _payments_router
app.include_router(_build_admin_analytics_router(db, require_admin), prefix="/api")
app.include_router(_appuntamenti_router, prefix="/api")
app.include_router(_terapisti_router, prefix="/api")
app.include_router(_payments_router, prefix="/api")
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

# ─── Startup ──────────────────────────────────────────────────────────────────
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Scheduler for email reminders
scheduler = AsyncIOScheduler()

def schedule_reminders(app_id: str, ctx: dict):
    """Schedule 1-day-before and 1-hour-before reminder emails for a booking."""
    try:
        from datetime import datetime as _dt
        start = _dt.fromisoformat(ctx["data_ora"].replace("Z", "+00:00"))
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        one_day = start - timedelta(days=1)
        one_hour = start - timedelta(hours=1)
        now = datetime.now(timezone.utc)
        if one_day > now:
            scheduler.add_job(send_reminder_email, "date", run_date=one_day, args=[ctx, "1-giorno"], id=f"rem1d-{app_id}", replace_existing=True)
        if one_hour > now:
            scheduler.add_job(send_reminder_email, "date", run_date=one_hour, args=[ctx, "1-ora"], id=f"rem1h-{app_id}", replace_existing=True)
    except Exception as e:
        logging.error(f"[SCHEDULER] failed to schedule reminders: {e}")

@app.on_event("startup")
async def startup():
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.password_reset_tokens.create_index("token_hash", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await seed_data()
    await _seed_default_contract()
    # Backfill: make existing self-certified therapists publicly visible under the new gate
    await db.terapisti.update_many(
        {"autocertificazione_firmata": True, "documenti_verificati": {"$exists": False}},
        {"$set": {"documenti_verificati": True}},
    )
    if not scheduler.running:
        scheduler.start()
        logging.info("[SCHEDULER] started")


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
    if scheduler.running:
        scheduler.shutdown()
    client.close()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
