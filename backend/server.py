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
from pydantic import BaseModel, Field, BeforeValidator, EmailStr

from email_service import send_otp_email, send_booking_confirmation_email, send_reminder_email, send_password_reset_email
from daily_service import create_room_for_appointment, create_meeting_token, get_room_presenza
from sms_service import send_sms_otp, verify_sms_otp
from codicefiscale import codicefiscale

# ─── Config ───────────────────────────────────────────────────────────────────
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# ─── MongoDB ──────────────────────────────────────────────────────────────────
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

# ─── Helpers ──────────────────────────────────────────────────────────────────
def PyObjectId(v):
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v):
        return v
    raise ValueError(f"ObjectId non valido: {v}")

def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_access_token(user_id: str, email: str, role: str) -> str:
    return jwt.encode(
        {"sub": user_id, "email": email, "role": role,
         "exp": datetime.now(timezone.utc) + timedelta(hours=8), "type": "access"},
        JWT_SECRET, algorithm=JWT_ALGORITHM
    )

def create_refresh_token(user_id: str) -> str:
    return jwt.encode(
        {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"},
        JWT_SECRET, algorithm=JWT_ALGORITHM
    )

def generate_otp() -> str:
    return str(_secrets.randbelow(900000) + 100000)

def validate_codice_fiscale(cf: str) -> bool:
    cf = cf.upper().strip()
    if len(cf) != 16:
        return False
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    if not all(c in allowed for c in cf):
        return False
    odd = {'0':1,'1':0,'2':5,'3':7,'4':9,'5':13,'6':15,'7':17,'8':19,'9':21,
           'A':1,'B':0,'C':5,'D':7,'E':9,'F':13,'G':15,'H':17,'I':19,'J':21,
           'K':2,'L':4,'M':18,'N':20,'O':11,'P':3,'Q':6,'R':8,'S':12,'T':14,
           'U':16,'V':10,'W':22,'X':25,'Y':24,'Z':23}
    even = {'0':0,'1':1,'2':2,'3':3,'4':4,'5':5,'6':6,'7':7,'8':8,'9':9,
            'A':0,'B':1,'C':2,'D':3,'E':4,'F':5,'G':6,'H':7,'I':8,'J':9,
            'K':10,'L':11,'M':12,'N':13,'O':14,'P':15,'Q':16,'R':17,'S':18,
            'T':19,'U':20,'V':21,'W':22,'X':23,'Y':24,'Z':25}
    total = sum(odd.get(c, 0) if i % 2 == 0 else even.get(c, 0) for i, c in enumerate(cf[:-1]))
    return cf[-1] == chr(ord('A') + (total % 26))

# ─── Auth dependency ──────────────────────────────────────────────────────────
async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Non autenticato")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Token non valido")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="Utente non trovato")
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sessione scaduta")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token non valido")

async def require_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accesso riservato agli amministratori")
    return user

async def require_auth(user: dict = Depends(get_current_user)):
    return user

# ─── Pydantic models ──────────────────────────────────────────────────────────
class RegisterInput(BaseModel):
    email: EmailStr
    password: str
    nome: str
    cognome: str
    role: str = "paziente"
    consenso_privacy: bool = True

class LoginInput(BaseModel):
    email: EmailStr
    password: str

class OTPInput(BaseModel):
    email: EmailStr
    otp_code: str

class FormazioneItem(BaseModel):
    titolo: str
    istituto: str
    anno: Optional[int] = None

class DisponibilitaItem(BaseModel):
    giorno: str
    ora_inizio: str
    ora_fine: str

class TerapistaProfileInput(BaseModel):
    nome: Optional[str] = None
    cognome: Optional[str] = None
    telefono: Optional[str] = None
    bio: Optional[str] = None
    anni_esperienza: Optional[int] = None
    specializzazioni: Optional[List[str]] = []
    formazione: Optional[List[FormazioneItem]] = []
    approccio_terapeutico: Optional[str] = None
    genere: Optional[str] = None
    albo_numero: Optional[str] = None
    albo_ordine: Optional[str] = None
    albo_iscrizione_data: Optional[str] = None
    assicurazione_compagnia: Optional[str] = None
    assicurazione_numero_polizza: Optional[str] = None
    assicurazione_scadenza: Optional[str] = None
    prezzo_sessione: Optional[float] = None
    lingue: Optional[List[str]] = []
    disponibilita: Optional[List[DisponibilitaItem]] = []
    iban: Optional[str] = None

class PazienteProfileInput(BaseModel):
    nome: Optional[str] = None
    cognome: Optional[str] = None
    data_nascita: Optional[str] = None
    genere: Optional[str] = None
    codice_fiscale: Optional[str] = None
    telefono: Optional[str] = None
    # Luogo di nascita (per codice fiscale)
    nato_all_estero: Optional[bool] = False
    luogo_nascita_provincia: Optional[str] = None
    luogo_nascita_comune: Optional[str] = None
    paese_nascita: Optional[str] = None
    # Residenza
    indirizzo: Optional[str] = None
    citta: Optional[str] = None
    cap: Optional[str] = None
    provincia_residenza: Optional[str] = None
    # Altri
    note_cliniche: Optional[str] = None
    terapeuta_assegnato: Optional[str] = None
    dati_fiscali_completi: Optional[bool] = None

class AppuntamentoInput(BaseModel):
    terapeuta_id: str
    paziente_id: str
    data_ora: str
    durata_minuti: int = 50
    tipo: str = "online"
    note: Optional[str] = None

class AppuntamentoStatoInput(BaseModel):
    stato: str

class ArticoloInput(BaseModel):
    titolo: str
    contenuto: str
    categoria: Optional[str] = None
    tags: Optional[List[str]] = []
    immagine_url: Optional[str] = None

class ConsentPrefs(BaseModel):
    essential: bool = True
    analytics: bool = False
    marketing: bool = False

class ConsentLogInput(BaseModel):
    prefs: ConsentPrefs
    policy_version: str
    language: Optional[str] = None
    page_url: Optional[str] = None

# ─── Contracts (editable "Mandato all'incasso" and similar) ───────────────────
class ContractInput(BaseModel):
    kind: str  # e.g. "mandato_all_incasso"
    title: str
    content_html: str
    effective_date: Optional[str] = None

class ContractAcceptInput(BaseModel):
    contract_id: str
    scrolled_to_end: bool = False

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
@api_router.get("/terapisti")
async def list_terapisti(user: dict = Depends(require_auth)):
    query = {} if user["role"] == "admin" else {"user_id": user["_id"]}
    docs = await db.terapisti.find(query).to_list(200)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs

@api_router.get("/terapisti/{terapista_id}")
async def get_terapista(terapista_id: str, user: dict = Depends(require_auth)):
    doc = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Terapeuta non trovato")
    doc["_id"] = str(doc["_id"])
    return doc

@api_router.post("/terapisti")
async def create_terapista(data: TerapistaProfileInput, user: dict = Depends(require_admin)):
    doc = data.model_dump(exclude_none=True)
    doc["created_at"] = datetime.now(timezone.utc)
    doc["autocertificazione_firmata"] = False
    result = await db.terapisti.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

@api_router.put("/terapisti/{terapista_id}")
async def update_terapista(terapista_id: str, data: TerapistaProfileInput, user: dict = Depends(require_auth)):
    existing = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    if not existing:
        raise HTTPException(status_code=404, detail="Terapeuta non trovato")
    if user["role"] != "admin" and existing.get("user_id") != user["_id"]:
        raise HTTPException(status_code=403, detail="Accesso negato")
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc)
    await db.terapisti.update_one({"_id": ObjectId(terapista_id)}, {"$set": update})
    doc = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    doc["_id"] = str(doc["_id"])
    return doc

@api_router.delete("/terapisti/{terapista_id}")
async def delete_terapista(terapista_id: str, user: dict = Depends(require_admin)):
    result = await db.terapisti.delete_one({"_id": ObjectId(terapista_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Terapeuta non trovato")
    return {"message": "Terapeuta eliminato"}

@api_router.post("/terapisti/{terapista_id}/autocertificazione")
async def firma_autocertificazione(terapista_id: str, request: Request, user: dict = Depends(require_auth)):
    doc = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Terapeuta non trovato")
    if user["role"] != "admin" and doc.get("user_id") != user["_id"]:
        raise HTTPException(status_code=403, detail="Accesso negato")
    client_ip = request.client.host if request.client else "unknown"
    await db.terapisti.update_one(
        {"_id": ObjectId(terapista_id)},
        {"$set": {
            "autocertificazione_firmata": True,
            "autocertificazione_data": datetime.now(timezone.utc),
            "autocertificazione_ip": client_ip
        }}
    )
    return {"message": "Autocertificazione firmata con successo", "data": datetime.now(timezone.utc).isoformat()}

@api_router.get("/terapisti/profilo/me")
async def get_my_terapista_profile(user: dict = Depends(require_auth)):
    if user["role"] not in ["terapeuta", "admin"]:
        raise HTTPException(status_code=403, detail="Accesso negato")
    doc = await db.terapisti.find_one({"user_id": user["_id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Profilo non trovato")
    doc["_id"] = str(doc["_id"])
    return doc

@api_router.put("/terapisti/profilo/me")
async def update_my_terapista_profile(data: TerapistaProfileInput, user: dict = Depends(require_auth)):
    if user["role"] not in ["terapeuta", "admin"]:
        raise HTTPException(status_code=403, detail="Accesso negato")
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc)
    await db.terapisti.update_one({"user_id": user["_id"]}, {"$set": update}, upsert=True)
    doc = await db.terapisti.find_one({"user_id": user["_id"]})
    doc["_id"] = str(doc["_id"])
    return doc

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
@api_router.get("/appuntamenti")
async def list_appuntamenti(user: dict = Depends(require_auth)):
    docs: list = []
    if user["role"] == "admin":
        docs = await db.appuntamenti.find({}).sort("data_ora", -1).to_list(500)
    elif user["role"] == "terapeuta":
        terapista = await db.terapisti.find_one({"user_id": user["_id"]})
        tid = str(terapista["_id"]) if terapista else None
        docs = await db.appuntamenti.find({"terapeuta_id": tid}).sort("data_ora", -1).to_list(200)
    else:
        paziente = await db.pazienti.find_one({"user_id": user["_id"]})
        pid = str(paziente["_id"]) if paziente else None
        docs = await db.appuntamenti.find({"paziente_id": pid}).sort("data_ora", -1).to_list(100)
    for d in docs:
        d["_id"] = str(d["_id"])
        # Enrich with names
        if d.get("terapeuta_id"):
            try:
                t = await db.terapisti.find_one({"_id": ObjectId(d["terapeuta_id"])})
                if t:
                    d["terapeuta_nome"] = f"{t.get('nome','')} {t.get('cognome','')}".strip()
            except Exception as e:
                logging.warning(f"[APPUNTAMENTI] enrich terapeuta failed for {d.get('_id')}: {e}")
        if d.get("paziente_id"):
            try:
                p = await db.pazienti.find_one({"_id": ObjectId(d["paziente_id"])})
                if p:
                    d["paziente_nome"] = f"{p.get('nome','')} {p.get('cognome','')}".strip()
            except Exception as e:
                logging.warning(f"[APPUNTAMENTI] enrich paziente failed for {d.get('_id')}: {e}")
    return docs

@api_router.post("/appuntamenti")
async def create_appuntamento(data: AppuntamentoInput, user: dict = Depends(require_auth)):
    doc = data.model_dump()
    doc["stato"] = "prenotato"
    doc["created_at"] = datetime.now(timezone.utc)
    doc["created_by"] = user["_id"]
    result = await db.appuntamenti.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

@api_router.put("/appuntamenti/{app_id}")
async def update_appuntamento(app_id: str, data: AppuntamentoInput, user: dict = Depends(require_auth)):
    update = data.model_dump(exclude_none=True)
    update["updated_at"] = datetime.now(timezone.utc)
    await db.appuntamenti.update_one({"_id": ObjectId(app_id)}, {"$set": update})
    doc = await db.appuntamenti.find_one({"_id": ObjectId(app_id)})
    doc["_id"] = str(doc["_id"])
    return doc

@api_router.patch("/appuntamenti/{app_id}/stato")
async def update_stato_appuntamento(app_id: str, data: AppuntamentoStatoInput, user: dict = Depends(require_auth)):
    valid_stati = ["prenotato", "confermato", "completato", "cancellato"]
    if data.stato not in valid_stati:
        raise HTTPException(status_code=400, detail=f"Stato non valido. Usa: {valid_stati}")
    await db.appuntamenti.update_one(
        {"_id": ObjectId(app_id)},
        {"$set": {"stato": data.stato, "updated_at": datetime.now(timezone.utc)}}
    )
    return {"message": f"Stato aggiornato a: {data.stato}"}

@api_router.delete("/appuntamenti/{app_id}")
async def delete_appuntamento(app_id: str, user: dict = Depends(require_admin)):
    await db.appuntamenti.delete_one({"_id": ObjectId(app_id)})
    return {"message": "Appuntamento eliminato"}

# ─── VIDEO CALL (Daily.co) ────────────────────────────────────────────────────
@api_router.post("/appuntamenti/{app_id}/video-token")
async def get_video_token(app_id: str, user: dict = Depends(require_auth)):
    """Generate a Daily.co meeting token for the current user to join this appointment's video room."""
    app = await db.appuntamenti.find_one({"_id": ObjectId(app_id)})
    if not app:
        raise HTTPException(404, "Appuntamento non trovato")

    # Authorization: user must be the paziente or the terapista for this appointment
    is_owner = False
    if user["role"] == "admin":
        is_owner = True
    elif user["role"] == "paziente":
        paziente = await db.pazienti.find_one({"user_id": user["_id"]})
        if not paziente or str(paziente["_id"]) != app.get("paziente_id"):
            raise HTTPException(403, "Non autorizzato")
    elif user["role"] == "terapeuta":
        terapista = await db.terapisti.find_one({"user_id": user["_id"]})
        if not terapista or str(terapista["_id"]) != app.get("terapeuta_id"):
            raise HTTPException(403, "Non autorizzato")
        is_owner = True
    else:
        raise HTTPException(403, "Non autorizzato")

    # Ensure the room exists (create lazily if missing)
    room_name = app.get("daily_room_name")
    room_url = app.get("daily_room_url")
    if not room_name:
        room = await create_room_for_appointment(app_id, app["data_ora"], app.get("durata_minuti", 50))
        if not room:
            raise HTTPException(500, "Impossibile creare la stanza video")
        room_name = room["room_name"]
        room_url = room["room_url"]
        await db.appuntamenti.update_one(
            {"_id": ObjectId(app_id)},
            {"$set": {"daily_room_url": room_url, "daily_room_name": room_name}}
        )

    user_name = f"{user.get('nome','')} {user.get('cognome','')}".strip() or user.get("email", "Utente")
    token = await create_meeting_token(room_name, user_name, is_owner, app["data_ora"], app.get("durata_minuti", 50))

    return {
        "room_url": room_url,
        "room_name": room_name,
        "token": token,  # may be None if Daily disabled (mock mode)
        "user_name": user_name,
        "is_owner": is_owner,
        "data_ora": app["data_ora"],
        "durata_minuti": app.get("durata_minuti", 50),
    }

@api_router.get("/appuntamenti/{app_id}/presenze")
async def get_presenze(app_id: str, user: dict = Depends(require_auth)):
    """Get attendance logs for a completed appointment (admin + terapista only)."""
    if user["role"] not in ("admin", "terapeuta"):
        raise HTTPException(403, "Accesso negato")
    app = await db.appuntamenti.find_one({"_id": ObjectId(app_id)})
    if not app:
        raise HTTPException(404, "Appuntamento non trovato")
    if user["role"] == "terapeuta":
        terapista = await db.terapisti.find_one({"user_id": user["_id"]})
        if not terapista or str(terapista["_id"]) != app.get("terapeuta_id"):
            raise HTTPException(403, "Non autorizzato")
    room_name = app.get("daily_room_name")
    if not room_name:
        return {"presenze": [], "message": "Nessuna stanza video creata"}
    presenze = await get_room_presenza(room_name)
    return {"presenze": presenze, "room_name": room_name}

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

# ─── SLOT DISPONIBILITÀ ──────────────────────────────────────────────────────
GIORNI_IT = {"Lunedì":0,"Martedì":1,"Mercoledì":2,"Giovedì":3,"Venerdì":4,"Sabato":5,"Domenica":6}
GIORNI_IT_INV = {v: k for k, v in GIORNI_IT.items()}

def fmt_slot_it(dt: datetime) -> str:
    giorno = GIORNI_IT_INV.get(dt.weekday(), "")
    return f"{giorno} {dt.strftime('%d/%m/%Y %H:%M')}"

@api_router.get("/terapisti/{terapista_id}/slots")
async def get_slots(terapista_id: str, data_inizio: str = None, settimane: int = 2):
    terapista = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    if not terapista:
        raise HTTPException(status_code=404, detail="Terapeuta non trovato")

    disponibilita = terapista.get("disponibilita", [])
    durata = 50  # minuti per slot

    now = datetime.now(timezone.utc)
    if data_inizio:
        try:
            start = datetime.fromisoformat(data_inizio).replace(tzinfo=timezone.utc, hour=0, minute=0, second=0, microsecond=0)
        except Exception:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    end = start + timedelta(weeks=max(1, min(settimane, 8)))

    # Appuntamenti esistenti (non cancellati)
    existing = await db.appuntamenti.find({
        "terapeuta_id": terapista_id,
        "stato": {"$nin": ["cancellato"]},
        "data_ora": {"$gte": start.isoformat(), "$lt": end.isoformat()}
    }).to_list(500)
    booked = {a["data_ora"][:16] for a in existing}  # YYYY-MM-DDTHH:MM

    slots = []
    current_day = start
    while current_day < end:
        wd = current_day.weekday()
        for disp in disponibilita:
            if GIORNI_IT.get(disp.get("giorno",""), -1) != wd:
                continue
            try:
                h0, m0 = map(int, disp["ora_inizio"].split(":"))
                h1, m1 = map(int, disp["ora_fine"].split(":"))
            except Exception:
                continue
            slot_t = current_day.replace(hour=h0, minute=m0, second=0, microsecond=0)
            end_t  = current_day.replace(hour=h1, minute=m1, second=0, microsecond=0)
            while slot_t + timedelta(minutes=durata) <= end_t:
                if slot_t > now:
                    key = slot_t.isoformat()[:16]
                    slots.append({
                        "data_ora": slot_t.isoformat(),
                        "data_ora_fmt": fmt_slot_it(slot_t),
                        "disponibile": key not in booked
                    })
                slot_t += timedelta(minutes=durata)
        current_day += timedelta(days=1)

    return {"slots": slots, "terapeuta_id": terapista_id, "durata_minuti": durata}

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

@api_router.patch("/admin/terapisti/{terapista_user_id}/approva")
async def approva_terapista(terapista_user_id: str, user: dict = Depends(require_admin)):
    await db.users.update_one(
        {"_id": ObjectId(terapista_user_id)},
        {"$set": {"approval_status": "approvato", "is_verified": True}}
    )
    return {"message": "Terapeuta approvato"}

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
TERAPISTI_DOCS_DIR = UPLOADS_DIR / "terapisti_docs"
TERAPISTI_DOCS_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_DOC_TYPES = {"cv", "assicurazione", "laurea"}
ALLOWED_EXTS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_DOC_SIZE = 10 * 1024 * 1024  # 10MB


@api_router.post("/terapisti/me/documenti/{tipo}")
async def upload_my_terapista_doc(tipo: str, file: UploadFile = File(...), user: dict = Depends(require_auth)):
    if user["role"] != "terapeuta":
        raise HTTPException(403, "Solo i terapeuti possono caricare documenti")
    tipo = tipo.lower().strip()
    if tipo not in ALLOWED_DOC_TYPES:
        raise HTTPException(400, f"Tipo documento non valido. Ammessi: {sorted(ALLOWED_DOC_TYPES)}")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, "Formato non supportato. Ammessi: PDF, PNG, JPG")
    content = await file.read()
    if len(content) > MAX_DOC_SIZE:
        raise HTTPException(400, "File troppo grande (max 10MB)")
    if len(content) == 0:
        raise HTTPException(400, "File vuoto")
    user_dir = TERAPISTI_DOCS_DIR / user["_id"]
    user_dir.mkdir(parents=True, exist_ok=True)
    # Remove older file for same tipo (any extension)
    for old in user_dir.glob(f"{tipo}.*"):
        try:
            old.unlink()
        except Exception:
            pass
    dest = user_dir / f"{tipo}{ext}"
    dest.write_bytes(content)
    now = datetime.now(timezone.utc)
    await db.terapisti.update_one(
        {"user_id": user["_id"]},
        {"$set": {
            f"documenti.{tipo}": {
                "filename": file.filename,
                "ext": ext,
                "size": len(content),
                "uploaded_at": now,
            }
        }},
    )
    return {"message": "Documento caricato", "tipo": tipo, "size": len(content)}


@api_router.get("/terapisti/me/documenti")
async def list_my_terapista_docs(user: dict = Depends(require_auth)):
    if user["role"] != "terapeuta":
        raise HTTPException(403, "Accesso negato")
    doc = await db.terapisti.find_one({"user_id": user["_id"]}, {"documenti": 1, "autocertificazione_dpr445": 1, "documenti_verificati": 1})
    if not doc:
        return {"documenti": {}, "autocertificazione_dpr445": False, "documenti_verificati": False}
    return {
        "documenti": doc.get("documenti", {}),
        "autocertificazione_dpr445": doc.get("autocertificazione_dpr445", False),
        "documenti_verificati": doc.get("documenti_verificati", False),
    }


@api_router.post("/terapisti/me/autocertificazione-dpr445")
async def firma_autocert_dpr445(request: Request, user: dict = Depends(require_auth)):
    """Therapist signs the DPR 445/2000 self-certification after uploading docs and verifying phone."""
    if user["role"] != "terapeuta":
        raise HTTPException(403, "Accesso negato")
    u = await db.users.find_one({"_id": ObjectId(user["_id"])})
    if not u or not u.get("telefono_verificato"):
        raise HTTPException(400, "Verifica prima il numero di telefono via SMS")
    t = await db.terapisti.find_one({"user_id": user["_id"]})
    if not t:
        raise HTTPException(404, "Profilo terapeuta non trovato")
    docs = t.get("documenti", {}) or {}
    missing = [k for k in ALLOWED_DOC_TYPES if k not in docs]
    if missing:
        raise HTTPException(400, f"Carica prima tutti i documenti. Mancano: {', '.join(missing)}")
    client_ip = request.client.host if request.client else "unknown"
    now = datetime.now(timezone.utc)
    await db.terapisti.update_one(
        {"user_id": user["_id"]},
        {"$set": {
            "autocertificazione_dpr445": True,
            "autocertificazione_firmata": True,
            "autocertificazione_data": now,
            "autocertificazione_ip": client_ip,
        }},
    )
    return {"message": "Autocertificazione DPR 445/2000 firmata", "data": now.isoformat()}


# ─── ADMIN: therapist documents review & verification ────────────────────────
@api_router.get("/admin/terapisti/{terapista_id}/documenti")
async def admin_list_terapista_docs(terapista_id: str, user: dict = Depends(require_admin)):
    t = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    if not t:
        raise HTTPException(404, "Terapeuta non trovato")
    u = await db.users.find_one({"_id": ObjectId(t.get("user_id"))}) if t.get("user_id") else None
    return {
        "terapista_id": terapista_id,
        "user_id": t.get("user_id"),
        "nome": t.get("nome"),
        "cognome": t.get("cognome"),
        "email": u.get("email") if u else None,
        "telefono": u.get("telefono") if u else None,
        "telefono_verificato": bool(u.get("telefono_verificato")) if u else False,
        "autocertificazione_dpr445": bool(t.get("autocertificazione_dpr445")),
        "autocertificazione_data": t.get("autocertificazione_data").isoformat() if isinstance(t.get("autocertificazione_data"), datetime) else t.get("autocertificazione_data"),
        "documenti_verificati": bool(t.get("documenti_verificati")),
        "documenti": t.get("documenti", {}),
    }


@api_router.get("/admin/terapisti/{terapista_id}/documenti/{tipo}/download")
async def admin_download_terapista_doc(terapista_id: str, tipo: str, user: dict = Depends(require_admin)):
    tipo = tipo.lower().strip()
    if tipo not in ALLOWED_DOC_TYPES:
        raise HTTPException(400, "Tipo non valido")
    t = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    if not t or not t.get("user_id"):
        raise HTTPException(404, "Terapeuta non trovato")
    user_dir = TERAPISTI_DOCS_DIR / t["user_id"]
    matches = list(user_dir.glob(f"{tipo}.*"))
    if not matches:
        raise HTTPException(404, "Documento non trovato")
    p = matches[0]
    media = "application/pdf" if p.suffix.lower() == ".pdf" else f"image/{p.suffix.lower().lstrip('.')}"
    return FileResponse(p, media_type=media, filename=p.name)


@api_router.patch("/admin/terapisti/{terapista_id}/verifica")
async def admin_verifica_terapista(terapista_id: str, body: dict, user: dict = Depends(require_admin)):
    """Admin toggles documenti_verificati. When True, therapist becomes publicly visible."""
    verificato = bool(body.get("verificato", True))
    t = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    if not t:
        raise HTTPException(404, "Terapeuta non trovato")
    now = datetime.now(timezone.utc)
    await db.terapisti.update_one(
        {"_id": ObjectId(terapista_id)},
        {"$set": {
            "documenti_verificati": verificato,
            "documenti_verificati_at": now if verificato else None,
            "documenti_verificati_by": user["_id"] if verificato else None,
        }},
    )
    return {"message": "Aggiornato", "documenti_verificati": verificato}


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


# ─── STRIPE PAYMENTS ──────────────────────────────────────────────────────────
import stripe as _stripe

_stripe.api_key = os.environ.get("STRIPE_SECRET_KEY") or "sk_test_emergent"
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
PLATFORM_FEE_PERCENT = 30  # BIDOC retention (%)


class CheckoutBookingRequest(BaseModel):
    terapeuta_id: str
    paziente_id: str
    data_ora: str
    durata_minuti: int
    tipologia: Optional[str] = "individuale"
    modalita: Optional[str] = "classica"
    note: Optional[str] = None
    origin_url: str
    # Fattura sanitaria fields — required for compliance
    opposizione_ts: bool = False  # patient opts out of Sistema TS transmission


@api_router.post("/payments/checkout/booking")
async def create_booking_checkout(req: CheckoutBookingRequest, user: dict = Depends(require_auth)):
    """Create a pending appointment + Stripe Checkout Session. On payment success
    (webhook or polling), the appointment is confirmed and the Daily.co room + emails
    are provisioned. Split accounting: 70% therapist, 30% platform, tracked in DB."""
    if user["role"] != "paziente":
        raise HTTPException(403, "Solo i pazienti possono prenotare")

    # Reuse the same SMS-verification guard as /public/prenota
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
        raise HTTPException(403, "Verifica il numero di telefono via SMS prima di procedere al pagamento")

    terapista = await db.terapisti.find_one({"_id": ObjectId(req.terapeuta_id)})
    if not terapista:
        raise HTTPException(404, "Terapista non trovato")
    prezzo = terapista.get("prezzo_sessione") or 0
    if prezzo <= 0:
        raise HTTPException(400, "Prezzo sessione non configurato per questo terapista")
    amount_cents = int(round(prezzo * 100))
    platform_fee_cents = int(round(amount_cents * PLATFORM_FEE_PERCENT / 100))
    therapist_amount_cents = amount_cents - platform_fee_cents

    # Marca da bollo di €2 obligatoria per fatture sanitarie esenti IVA da €77,47
    # in su (soglia storica da D.P.R. 642/1972 aggiornato). Il paziente paga la
    # sessione al lordo — il bollo è a carico del professionista sanitario.
    MARCA_DA_BOLLO_SOGLIA_CENTS = 7747
    marca_da_bollo_required = amount_cents >= MARCA_DA_BOLLO_SOGLIA_CENTS
    marca_da_bollo_amount = 200 if marca_da_bollo_required else 0

    # 1. Create pending appointment
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

    # 2. Create Stripe Checkout Session (dynamic price_data, DIY tax mode).
    # Rationale: Italian psychology/sexology services are IVA-exempt under
    # art. 10 DPR 633/72; the therapist emits an exempt "fattura sanitaria"
    # separately, so Stripe should NOT calculate additional VAT.
    # Build success/cancel URLs server-side from trusted env config.
    # The client-supplied origin_url is used only as a soft hint; if it doesn't
    # match our allow-list we fall back to FRONTEND_URL/REACT_APP_BACKEND_URL.
    # This prevents open-redirect abuse post-payment.
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

    # 3. Persist payment_transaction with the split accounting
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
        # Fattura sanitaria compliance fields
        "opposizione_ts": req.opposizione_ts,
        "marca_da_bollo_required": marca_da_bollo_required,
        "marca_da_bollo_amount": marca_da_bollo_amount,
        "fattura_sanitaria_status": "da_emettere",
        "status": "initiated",
        "payment_status": "pending",
        "payout_status": "pending",  # tracked separately for manual Connect/payout later
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })

    # 4. Link session to appointment for cancel path
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
    # Confirm the linked appointment
    appt_id = tx.get("appointment_id")
    if appt_id:
        await db.appuntamenti.update_one(
            {"_id": ObjectId(appt_id)},
            {"$set": {"stato": "confermato", "paid_at": now}},
        )
        # Provision Daily.co + emails
        paziente_user = await db.users.find_one({"_id": ObjectId(tx["paziente_user_id"])})
        if paziente_user:
            paziente_user["_id"] = str(paziente_user["_id"])
            await _finalize_confirmed_booking(appt_id, paziente_user)
    return True


@api_router.get("/payments/status/{session_id}")
async def get_payment_status(session_id: str):
    """Unauthenticated status probe used by the /payment/success page.
    Returns only status flags — no sensitive info leaked."""
    tx = await db.payment_transactions.find_one({"session_id": session_id})
    if not tx:
        raise HTTPException(404, "Transaction not found")
    # Webhook fallback: verify with Stripe directly if still pending
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


@api_router.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    try:
        event = _stripe.Webhook.construct_event(payload, sig, STRIPE_WEBHOOK_SECRET)
    except _stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")
    obj, t = event["data"]["object"], event["type"]
    if t == "checkout.session.completed":
        if obj.get("payment_status") == "paid":
            await _mark_payment_paid(obj["id"], obj.get("payment_intent"))
    elif t == "checkout.session.async_payment_succeeded":
        await _mark_payment_paid(obj["id"], obj.get("payment_intent"))
    elif t in ("checkout.session.async_payment_failed", "checkout.session.expired"):
        new_status = "failed" if "failed" in t else "expired"
        await db.payment_transactions.update_one(
            {"session_id": obj["id"]},
            {"$set": {"status": new_status, "payment_status": new_status, "updated_at": datetime.now(timezone.utc)}},
        )
        # Also cancel the pending appointment
        tx = await db.payment_transactions.find_one({"session_id": obj["id"]})
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
    return {"status": "ok"}


@api_router.get("/therapist/earnings")
async def therapist_earnings(user: dict = Depends(require_auth)):
    """Show the therapist their earnings breakdown (paid = 70% of paid sessions).
    Marketplace split is currently tracked in DB; automatic Stripe Connect payouts
    can be added later without breaking this contract."""
    if user["role"] != "terapeuta":
        raise HTTPException(403, "Solo i terapeuti possono vedere gli incassi")
    terapista = await db.terapisti.find_one({"user_id": user["_id"]})
    if not terapista:
        # Fallback in case some legacy rows have ObjectId user_id
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
from fastapi.responses import Response as _FastResponse
from invoice_pdf import build_fattura_sanitaria_pdf, build_fattura_commissione_pdf


class MarkPayoutPaidRequest(BaseModel):
    transaction_ids: List[str]
    payout_reference: Optional[str] = None  # e.g., IBAN bonifico ref


@api_router.get("/admin/payouts")
async def list_admin_payouts(
    payout_status: Optional[str] = None,  # 'pending' | 'paid'
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

    # Aggregate summary by therapist
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


@api_router.post("/admin/payouts/mark-paid")
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


# ─── Cruscotto (Executive Admin Dashboard) ──────────────────────────────────
@api_router.get("/admin/cruscotto")
async def admin_cruscotto(user: dict = Depends(require_admin)):
    """Executive KPIs for BIDOC admin: revenue, payouts, sessions, top therapists, IBAN alerts."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month_start.month == 12:
        next_month_start = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month_start = month_start.replace(month=month_start.month + 1)
    if month_start.month == 1:
        prev_month_start = month_start.replace(year=month_start.year - 1, month=12)
    else:
        prev_month_start = month_start.replace(month=month_start.month - 1)

    # a) Revenue current month vs previous month (from paid tx)
    async def _sum_revenue(gte, lt):
        pipeline = [
            {"$match": {"payment_status": "paid", "paid_at": {"$gte": gte, "$lt": lt}}},
            {"$group": {
                "_id": None,
                "gross": {"$sum": "$amount"},
                "platform_fee": {"$sum": "$platform_fee_amount"},
                "therapist": {"$sum": "$therapist_amount"},
                "count": {"$sum": 1},
            }},
        ]
        async for row in db.payment_transactions.aggregate(pipeline):
            return {
                "gross_cents": row.get("gross", 0) or 0,
                "platform_fee_cents": row.get("platform_fee", 0) or 0,
                "therapist_cents": row.get("therapist", 0) or 0,
                "count": row.get("count", 0) or 0,
            }
        return {"gross_cents": 0, "platform_fee_cents": 0, "therapist_cents": 0, "count": 0}

    rev_current = await _sum_revenue(month_start, next_month_start)
    rev_previous = await _sum_revenue(prev_month_start, month_start)

    # b) Pending payouts total (paid tx not yet bonificate)
    pending_agg = [
        {"$match": {"payment_status": "paid", "payout_status": {"$ne": "paid"}}},
        {"$group": {
            "_id": None,
            "total": {"$sum": "$therapist_amount"},
            "count": {"$sum": 1},
        }},
    ]
    pending_payouts = {"total_cents": 0, "count": 0}
    async for row in db.payment_transactions.aggregate(pending_agg):
        pending_payouts = {"total_cents": row.get("total", 0) or 0, "count": row.get("count", 0) or 0}

    # c) Sessions this month: completed vs booked (confermato+completato)
    month_start_iso = month_start.isoformat()
    next_month_iso = next_month_start.isoformat()
    sessions_completed_month = await db.appuntamenti.count_documents({
        "stato": "completato",
        "data_ora": {"$gte": month_start_iso, "$lt": next_month_iso},
    })
    sessions_booked_month = await db.appuntamenti.count_documents({
        "stato": {"$in": ["confermato", "completato"]},
        "data_ora": {"$gte": month_start_iso, "$lt": next_month_iso},
    })
    completion_rate = (
        round((sessions_completed_month / sessions_booked_month) * 100, 1)
        if sessions_booked_month > 0 else 0
    )

    # d) Revenue last 6 months (bar chart) — buckets by paid_at month
    six_months_ago = month_start
    for _ in range(5):
        if six_months_ago.month == 1:
            six_months_ago = six_months_ago.replace(year=six_months_ago.year - 1, month=12)
        else:
            six_months_ago = six_months_ago.replace(month=six_months_ago.month - 1)

    monthly_pipeline = [
        {"$match": {"payment_status": "paid", "paid_at": {"$gte": six_months_ago}}},
        {"$group": {
            "_id": {"y": {"$year": "$paid_at"}, "m": {"$month": "$paid_at"}},
            "gross": {"$sum": "$amount"},
            "count": {"$sum": 1},
        }},
    ]
    buckets = {}
    async for row in db.payment_transactions.aggregate(monthly_pipeline):
        key = f"{row['_id']['y']}-{row['_id']['m']:02d}"
        buckets[key] = {"gross_cents": row.get("gross", 0) or 0, "count": row.get("count", 0) or 0}

    revenue_6m = []
    cursor = six_months_ago
    for _ in range(6):
        key = f"{cursor.year}-{cursor.month:02d}"
        b = buckets.get(key, {"gross_cents": 0, "count": 0})
        revenue_6m.append({
            "month": key,
            "label": cursor.strftime("%b").capitalize(),
            "gross_cents": b["gross_cents"],
            "count": b["count"],
        })
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)

    # e) Top 5 therapists by revenue (all-time, paid)
    top_pipeline = [
        {"$match": {"payment_status": "paid"}},
        {"$group": {
            "_id": "$terapeuta_id",
            "gross": {"$sum": "$amount"},
            "sessions": {"$sum": 1},
        }},
        {"$sort": {"gross": -1}},
        {"$limit": 5},
    ]
    top_therapists = []
    async for row in db.payment_transactions.aggregate(top_pipeline):
        tid = row["_id"]
        try:
            t = await db.terapisti.find_one({"_id": ObjectId(tid)})
        except Exception:
            t = None
        top_therapists.append({
            "terapeuta_id": tid,
            "nome": f"{t.get('nome','')} {t.get('cognome','')}".strip() if t else "Sconosciuto",
            "gross_cents": row.get("gross", 0) or 0,
            "sessions": row.get("sessions", 0) or 0,
        })

    # f) Alert: therapists with paid sessions but missing IBAN
    iban_pipeline = [
        {"$match": {"payment_status": "paid"}},
        {"$group": {"_id": "$terapeuta_id", "sessions": {"$sum": 1},
                    "pending": {"$sum": {"$cond": [{"$ne": ["$payout_status", "paid"]}, "$therapist_amount", 0]}}}},
    ]
    iban_missing = []
    async for row in db.payment_transactions.aggregate(iban_pipeline):
        tid = row["_id"]
        try:
            t = await db.terapisti.find_one({"_id": ObjectId(tid)})
        except Exception:
            t = None
        if not t:
            continue
        iban = (t.get("iban") or "").strip()
        pending_cents = row.get("pending", 0) or 0
        if not iban and pending_cents > 0:
            iban_missing.append({
                "terapeuta_id": tid,
                "nome": f"{t.get('nome','')} {t.get('cognome','')}".strip(),
                "sessions": row.get("sessions", 0) or 0,
                "pending_cents": pending_cents,
            })

    return {
        "generated_at": now.isoformat(),
        "revenue": {
            "current_month": rev_current,
            "previous_month": rev_previous,
            "delta_percent": (
                round(((rev_current["gross_cents"] - rev_previous["gross_cents"]) / rev_previous["gross_cents"]) * 100, 1)
                if rev_previous["gross_cents"] > 0 else None
            ),
        },
        "pending_payouts": pending_payouts,
        "sessions_month": {
            "completed": sessions_completed_month,
            "booked": sessions_booked_month,
            "completion_rate": completion_rate,
        },
        "revenue_6m": revenue_6m,
        "top_therapists": top_therapists,
        "iban_missing": iban_missing,
    }


@api_router.get("/admin/fattura-sanitaria/{transaction_id}")
async def download_fattura_sanitaria(transaction_id: str, user: dict = Depends(require_admin)):
    """Generate a PDF fattura sanitaria for a paid transaction."""
    tx = await db.payment_transactions.find_one({"_id": ObjectId(transaction_id), "payment_status": "paid"})
    if not tx:
        raise HTTPException(404, "Transazione non trovata o non pagata")
    appt = await db.appuntamenti.find_one({"_id": ObjectId(tx["appointment_id"])})
    terapista = await db.terapisti.find_one({"_id": ObjectId(tx["terapeuta_id"])})
    paziente = await db.pazienti.find_one({"_id": ObjectId(tx["paziente_id"])})
    paziente_user = await db.users.find_one({"_id": ObjectId(tx["paziente_user_id"])})
    if not (appt and terapista and paziente and paziente_user):
        raise HTTPException(404, "Dati incompleti per generare la fattura")
    pdf = build_fattura_sanitaria_pdf(
        tx=tx, appt=appt, terapista=terapista, paziente=paziente, paziente_user=paziente_user,
    )
    filename = f"fattura-sanitaria-{transaction_id[:8]}.pdf"
    return _FastResponse(content=pdf, media_type="application/pdf",
                         headers={"Content-Disposition": f'inline; filename="{filename}"'})


@api_router.get("/admin/fattura-commissione/{terapeuta_id}/{year}/{month}")
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


app.include_router(api_router)
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

@app.on_event("shutdown")
async def shutdown():
    if scheduler.running:
        scheduler.shutdown()
    client.close()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
