"""Terapisti (therapists) router: CRUD + profile + slots + documents + admin verification."""
import hashlib
import logging
import os
import re
import secrets as _secrets
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, EmailStr, Field

from deps import db, require_auth, require_admin, find_user_by_id, hash_password
from models import TerapistaProfileInput
from email_service import (
    send_therapist_approved_email,
    send_new_therapist_admin_alert,
    send_therapist_activation_email,
    send_therapist_ready_for_review_email,
)
from storage_service import put_object, get_object, mime_for_ext, APP_NAME as STORAGE_APP

router = APIRouter()

ACTIVATION_TOKEN_DAYS = 7
ADMIN_REVIEW_EMAIL = os.environ.get("ADMIN_REVIEW_EMAIL", "hr@funzionabene.it")


def _token_digest(raw: str) -> str:
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def _frontend_origin(request: Request) -> str:
    env_url = os.environ.get("FRONTEND_URL") or os.environ.get("REACT_APP_BACKEND_URL")
    if env_url:
        return env_url.rstrip("/")
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    return origin.rstrip("/")


# ─── Public: therapist application (lead capture) ─────────────────────────
class CandidaturaTerapistaInput(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    cognome: str = Field(min_length=1, max_length=80)
    email: EmailStr
    telefono: str = Field(min_length=6, max_length=32)
    messaggio: str | None = Field(default=None, max_length=800)


def _normalize_phone(raw: str) -> str:
    s = re.sub(r"[^\d+]", "", raw or "")
    return s


@router.post("/terapeuti/candidatura")
async def submit_terapeuta_candidatura(body: CandidaturaTerapistaInput, request: Request):
    """Public endpoint: capture therapist lead. No account is created; the record lives
    in the `terapisti` collection with approval_status='lead' and is invisible to
    patients (documenti_verificati=False, calendario_bozza=True). Admin is notified
    via email and will contact the applicant manually to onboard them.
    """
    email = body.email.lower().strip()
    telefono = _normalize_phone(body.telefono)
    if len(telefono) < 6:
        raise HTTPException(400, "Numero di telefono non valido")

    # Avoid duplicates (case-insensitive) among leads or existing terapisti users
    now = datetime.now(timezone.utc)
    existing_lead = await db.terapisti.find_one({"email": email, "approval_status": "lead"})
    if existing_lead:
        # Update timestamp to reflect re-submission but don't create a second row
        await db.terapisti.update_one(
            {"_id": existing_lead["_id"]},
            {"$set": {
                "nome": body.nome.strip(),
                "cognome": body.cognome.strip(),
                "telefono": telefono,
                "messaggio": (body.messaggio or "").strip() or None,
                "last_submitted_at": now,
            }},
        )
    else:
        existing_user = await db.users.find_one({"email": email, "role": "terapeuta"})
        if existing_user:
            raise HTTPException(409, "Esiste già un profilo terapeuta con questa email")
        await db.terapisti.insert_one({
            "nome": body.nome.strip(),
            "cognome": body.cognome.strip(),
            "email": email,
            "telefono": telefono,
            "messaggio": (body.messaggio or "").strip() or None,
            "approval_status": "lead",
            "documenti_verificati": False,
            "calendario_bozza": True,
            "user_id": None,
            "source": "candidatura_form",
            "source_ip": (request.client.host if request.client else None),
            "source_ua": (request.headers.get("user-agent") or "")[:400],
            "created_at": now,
            "last_submitted_at": now,
        })

    # Notify admin (best-effort)
    try:
        await send_new_therapist_admin_alert({
            "nome": body.nome.strip(),
            "cognome": body.cognome.strip(),
            "email": email,
            "telefono": telefono,
            "messaggio": (body.messaggio or "").strip() or None,
            "created_at": now.strftime("%d/%m/%Y %H:%M"),
        })
    except Exception as e:
        logging.error(f"[EMAIL] admin candidatura alert failed: {e}")

    return {"message": "Candidatura ricevuta. Ti contatteremo a breve."}

# ─── Docs storage constants ────────────────────────────────────────────────
# Legacy on-disk path — kept ONLY as a read-fallback for pre-migration docs.
# New uploads go to Emergent Object Storage under {STORAGE_APP}/terapisti_docs/{user_id}/{tipo}-{uuid}{ext}.
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
TERAPISTI_DOCS_DIR = UPLOADS_DIR / "terapisti_docs"
ALLOWED_DOC_TYPES = {"cv", "assicurazione", "laurea"}
ALLOWED_EXTS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_DOC_SIZE = 10 * 1024 * 1024  # 10MB

# ─── Slot helpers ─────────────────────────────────────────────────────────
GIORNI_IT = {"Lunedì": 0, "Martedì": 1, "Mercoledì": 2, "Giovedì": 3,
             "Venerdì": 4, "Sabato": 5, "Domenica": 6}
GIORNI_IT_INV = {v: k for k, v in GIORNI_IT.items()}


def fmt_slot_it(dt: datetime) -> str:
    giorno = GIORNI_IT_INV.get(dt.weekday(), "")
    return f"{giorno} {dt.strftime('%d/%m/%Y %H:%M')}"


# ─── CRUD ─────────────────────────────────────────────────────────────────
@router.get("/terapisti")
async def list_terapisti(user: dict = Depends(require_auth)):
    query = {} if user["role"] == "admin" else {"user_id": user["_id"]}
    docs = await db.terapisti.find(query).to_list(200)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


@router.get("/terapisti/profilo/me")
async def get_my_terapista_profile(user: dict = Depends(require_auth)):
    if user["role"] not in ["terapeuta", "admin"]:
        raise HTTPException(status_code=403, detail="Accesso negato")
    doc = await db.terapisti.find_one({"user_id": user["_id"]})
    if not doc:
        raise HTTPException(status_code=404, detail="Profilo non trovato")
    doc["_id"] = str(doc["_id"])
    return doc


@router.put("/terapisti/profilo/me")
async def update_my_terapista_profile(data: TerapistaProfileInput, user: dict = Depends(require_auth)):
    if user["role"] not in ["terapeuta", "admin"]:
        raise HTTPException(status_code=403, detail="Accesso negato")
    update = {k: v for k, v in data.model_dump().items() if v is not None}
    update["updated_at"] = datetime.now(timezone.utc)
    await db.terapisti.update_one({"user_id": user["_id"]}, {"$set": update}, upsert=True)
    doc = await db.terapisti.find_one({"user_id": user["_id"]})
    doc["_id"] = str(doc["_id"])
    return doc


@router.get("/terapisti/me/documenti")
async def list_my_terapista_docs(user: dict = Depends(require_auth)):
    if user["role"] != "terapeuta":
        raise HTTPException(403, "Accesso negato")
    doc = await db.terapisti.find_one(
        {"user_id": user["_id"]},
        {"documenti": 1, "autocertificazione_dpr445": 1, "documenti_verificati": 1},
    )
    if not doc:
        return {"documenti": {}, "autocertificazione_dpr445": False, "documenti_verificati": False}
    return {
        "documenti": doc.get("documenti", {}),
        "autocertificazione_dpr445": doc.get("autocertificazione_dpr445", False),
        "documenti_verificati": doc.get("documenti_verificati", False),
    }


@router.post("/terapisti/me/documenti/{tipo}")
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

    # Upload to Emergent Object Storage (persistent, survives pod restarts)
    storage_path = f"{STORAGE_APP}/terapisti_docs/{user['_id']}/{tipo}-{uuid.uuid4().hex}{ext}"
    try:
        result = put_object(storage_path, content, mime_for_ext(ext))
    except Exception as e:
        logging.exception(f"[STORAGE] upload failed for {tipo}: {e}")
        raise HTTPException(503, "Impossibile caricare il documento. Riprova.")
    stored_path = result.get("path", storage_path)

    now = datetime.now(timezone.utc)
    await db.terapisti.update_one(
        {"user_id": user["_id"]},
        {"$set": {
            f"documenti.{tipo}": {
                "filename": file.filename,
                "ext": ext,
                "size": len(content),
                "storage_path": stored_path,
                "uploaded_at": now,
            }
        }},
    )
    return {"message": "Documento caricato", "tipo": tipo, "size": len(content)}


@router.post("/terapisti/me/autocertificazione-dpr445")
async def firma_autocert_dpr445(request: Request, user: dict = Depends(require_auth)):
    """Therapist signs the DPR 445/2000 self-certification after uploading docs and verifying phone."""
    if user["role"] != "terapeuta":
        raise HTTPException(403, "Accesso negato")
    u = await find_user_by_id(user["_id"])
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


@router.post("/terapisti/me/onboarding-completato")
async def marca_onboarding_completato(user: dict = Depends(require_auth)):
    """Called by the therapist after finishing the full onboarding flow
    (docs + phone verification + DPR 445 signature). Marks approval_status="pronto_per_review"
    and notifies the admin by email so they can do the final documenti_verificati toggle."""
    if user["role"] != "terapeuta":
        raise HTTPException(403, "Accesso negato")
    t = await db.terapisti.find_one({"user_id": user["_id"]})
    if not t:
        raise HTTPException(404, "Profilo terapeuta non trovato")
    # Guard: all onboarding steps must be complete
    docs = t.get("documenti", {}) or {}
    missing = [k for k in ALLOWED_DOC_TYPES if k not in docs]
    if missing:
        raise HTTPException(400, f"Documenti mancanti: {', '.join(missing)}")
    if not t.get("autocertificazione_firmata"):
        raise HTTPException(400, "Devi firmare l'autocertificazione DPR 445 prima di completare l'onboarding.")
    u = await find_user_by_id(user["_id"])
    if not u or not u.get("telefono_verificato"):
        raise HTTPException(400, "Devi verificare il telefono via SMS prima di completare l'onboarding.")

    now = datetime.now(timezone.utc)
    # Idempotent — safe to call multiple times
    already = t.get("approval_status") == "pronto_per_review"
    await db.terapisti.update_one(
        {"_id": t["_id"]},
        {"$set": {
            "approval_status": "pronto_per_review",
            "onboarding_completato_at": now,
        }},
    )
    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": {"approval_status": "pronto_per_review"}},
    )

    if not already:
        try:
            await send_therapist_ready_for_review_email(
                admin_email=ADMIN_REVIEW_EMAIL,
                terapista_nome=f"{t.get('nome', '')} {t.get('cognome', '')}".strip(),
                terapista_email=u.get("email", ""),
                terapista_id=str(t["_id"]),
            )
        except Exception as e:
            logging.error(f"[EMAIL] admin review notification failed: {e}")

    return {"message": "Onboarding completato. L'amministrazione revisionerà il profilo a breve."}


@router.get("/terapisti/{terapista_id}")
async def get_terapista(terapista_id: str, user: dict = Depends(require_auth)):
    doc = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Terapeuta non trovato")
    doc["_id"] = str(doc["_id"])
    return doc


@router.post("/terapisti")
async def create_terapista(data: TerapistaProfileInput, user: dict = Depends(require_admin)):
    doc = data.model_dump(exclude_none=True)
    doc["created_at"] = datetime.now(timezone.utc)
    doc["autocertificazione_firmata"] = False
    result = await db.terapisti.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


@router.put("/terapisti/{terapista_id}")
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


@router.delete("/terapisti/{terapista_id}")
async def delete_terapista(terapista_id: str, user: dict = Depends(require_admin)):
    result = await db.terapisti.delete_one({"_id": ObjectId(terapista_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Terapeuta non trovato")
    return {"message": "Terapeuta eliminato"}


@router.post("/terapisti/{terapista_id}/autocertificazione")
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
            "autocertificazione_ip": client_ip,
        }},
    )
    return {"message": "Autocertificazione firmata con successo", "data": datetime.now(timezone.utc).isoformat()}


@router.get("/terapisti/{terapista_id}/slots")
async def get_slots(terapista_id: str, data_inizio: str = None, settimane: int = 2):
    terapista = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    if not terapista:
        raise HTTPException(status_code=404, detail="Terapeuta non trovato")

    durata = 50
    now = datetime.now(timezone.utc)
    min_slot_time = now + timedelta(hours=2)
    if data_inizio:
        try:
            start = datetime.fromisoformat(data_inizio).replace(tzinfo=timezone.utc, hour=0, minute=0, second=0, microsecond=0)
        except Exception:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    end = start + timedelta(weeks=max(1, min(settimane, 8)))

    existing = await db.appuntamenti.find({
        "terapeuta_id": terapista_id,
        "stato": {"$nin": ["cancellato", "annullato"]},
        "data_ora": {"$gte": start.isoformat(), "$lt": end.isoformat()},
    }).to_list(500)
    booked = {a["data_ora"][:16] for a in existing}

    slots = []

    # PRIMARY: date-specific calendar (disponibilita_calendario)
    cal = terapista.get("disponibilita_calendario") or {}
    use_calendar = bool(cal) and not terapista.get("calendario_bozza")

    if use_calendar:
        current_day = start
        while current_day < end:
            date_key = current_day.strftime("%Y-%m-%d")
            for hhmm in cal.get(date_key, []):
                try:
                    h, m = int(hhmm[:2]), int(hhmm[3:5])
                except (ValueError, IndexError):
                    continue
                slot_t = current_day.replace(hour=h, minute=m, second=0, microsecond=0)
                if slot_t < min_slot_time:
                    continue
                key = slot_t.isoformat()[:16]
                slots.append({
                    "data_ora": slot_t.isoformat(),
                    "data_ora_fmt": fmt_slot_it(slot_t),
                    "disponibile": key not in booked,
                })
            current_day += timedelta(days=1)
    else:
        # FALLBACK: legacy weekly recurring availability
        disponibilita = terapista.get("disponibilita", [])
        current_day = start
        while current_day < end:
            wd = current_day.weekday()
            for disp in disponibilita:
                if GIORNI_IT.get(disp.get("giorno", ""), -1) != wd:
                    continue
                try:
                    h0, m0 = map(int, disp["ora_inizio"].split(":"))
                    h1, m1 = map(int, disp["ora_fine"].split(":"))
                except Exception:
                    continue
                slot_t = current_day.replace(hour=h0, minute=m0, second=0, microsecond=0)
                end_t = current_day.replace(hour=h1, minute=m1, second=0, microsecond=0)
                while slot_t + timedelta(minutes=durata) <= end_t:
                    if slot_t >= min_slot_time:
                        key = slot_t.isoformat()[:16]
                        slots.append({
                            "data_ora": slot_t.isoformat(),
                            "data_ora_fmt": fmt_slot_it(slot_t),
                            "disponibile": key not in booked,
                        })
                    slot_t += timedelta(minutes=durata)
            current_day += timedelta(days=1)

    return {
        "slots": slots,
        "terapeuta_id": terapista_id,
        "durata_minuti": durata,
        "source": "calendar" if use_calendar else "legacy_weekly",
    }


# ─── Admin: therapist approval + documents review & verification ─────────────
@router.patch("/admin/terapisti/{terapista_user_id}/approva")
async def approva_terapista(terapista_user_id: str, user: dict = Depends(require_admin)):
    await db.users.update_one(
        {"_id": ObjectId(terapista_user_id)},
        {"$set": {"approval_status": "approvato", "is_verified": True}},
    )
    return {"message": "Terapeuta approvato"}


@router.get("/admin/terapisti/{terapista_id}/documenti")
async def admin_list_terapista_docs(terapista_id: str, user: dict = Depends(require_admin)):
    t = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    if not t:
        raise HTTPException(404, "Terapeuta non trovato")
    u = await find_user_by_id(t.get("user_id")) if t.get("user_id") else None
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


@router.get("/admin/terapisti/{terapista_id}/documenti/{tipo}/download")
async def admin_download_terapista_doc(terapista_id: str, tipo: str, user: dict = Depends(require_admin)):
    tipo = tipo.lower().strip()
    if tipo not in ALLOWED_DOC_TYPES:
        raise HTTPException(400, "Tipo non valido")
    t = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    if not t or not t.get("user_id"):
        raise HTTPException(404, "Terapeuta non trovato")

    meta = (t.get("documenti") or {}).get(tipo) or {}
    storage_path = meta.get("storage_path")
    ext = (meta.get("ext") or "").lower()

    # Preferred: Emergent Object Storage (all new uploads)
    if storage_path:
        try:
            data, content_type = get_object(storage_path)
        except Exception as e:
            logging.exception(f"[STORAGE] download failed {storage_path}: {e}")
            raise HTTPException(404, "Documento non trovato")
        filename = f"{tipo}{ext or ''}"
        return Response(
            content=data,
            media_type=content_type or mime_for_ext(ext),
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    # Legacy fallback: pre-migration docs still on the pod disk (may be gone after restart).
    user_dir = TERAPISTI_DOCS_DIR / t["user_id"]
    matches = list(user_dir.glob(f"{tipo}.*")) if user_dir.exists() else []
    if not matches:
        raise HTTPException(404, "Documento non trovato")
    p = matches[0]
    return FileResponse(p, media_type=mime_for_ext(p.suffix), filename=p.name)


@router.patch("/admin/terapisti/{terapista_id}/sospendi")
async def sospendi_terapista(terapista_id: str, body: dict, user: dict = Depends(require_admin)):
    """Sospendi/riattiva un terapista. body: {sospeso: bool}.
    Sospeso=true → user.is_active=false (blocca login) + terapista.sospeso=true (nascosto al pubblico).
    Sospeso=false → riabilita entrambi."""
    sospeso = bool(body.get("sospeso", True))
    t = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    if not t:
        raise HTTPException(404, "Terapeuta non trovato")
    now = datetime.now(timezone.utc)
    await db.terapisti.update_one(
        {"_id": ObjectId(terapista_id)},
        {"$set": {
            "sospeso": sospeso,
            "sospeso_at": now if sospeso else None,
            "sospeso_by": user["_id"] if sospeso else None,
        }},
    )
    if t.get("user_id"):
        u = await find_user_by_id(t["user_id"])
        if u:
            await db.users.update_one({"_id": u["_id"]}, {"$set": {"is_active": not sospeso}})
    return {"message": "Terapeuta sospeso" if sospeso else "Terapeuta riattivato", "sospeso": sospeso}


@router.patch("/admin/terapisti/{terapista_id}/verifica")
async def admin_verifica_terapista(terapista_id: str, body: dict, user: dict = Depends(require_admin)):
    """Admin toggles documenti_verificati. When True, therapist becomes publicly visible."""
    verificato = bool(body.get("verificato", True))
    t = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    if not t:
        raise HTTPException(404, "Terapeuta non trovato")
    was_verified = bool(t.get("documenti_verificati"))
    now = datetime.now(timezone.utc)
    update = {
        "documenti_verificati": verificato,
        "documenti_verificati_at": now if verificato else None,
        "documenti_verificati_by": user["_id"] if verificato else None,
    }
    if verificato:
        # Final approval: lift the suspension applied during activation
        update["sospeso"] = False
        update["sospeso_at"] = None
        update["sospeso_by"] = None
    await db.terapisti.update_one(
        {"_id": ObjectId(terapista_id)},
        {"$set": update},
    )
    # If newly approved (transition from unverified → verified), notify therapist by email
    if verificato and not was_verified and t.get("user_id"):
        try:
            u = await find_user_by_id(t["user_id"])
            if u and u.get("email"):
                await send_therapist_approved_email(u["email"], t.get("nome", ""))
                # Also reactivate the user account + update approval_status
                await db.users.update_one(
                    {"_id": ObjectId(t["user_id"])},
                    {"$set": {"approval_status": "approvato", "is_active": True}},
                )
        except Exception as e:
            logging.error(f"[EMAIL] therapist approved notification failed: {e}")
    return {"message": "Aggiornato", "documenti_verificati": verificato}


# ─── Admin: activate lead-therapist (send activation email) ────────────────
@router.post("/admin/terapisti/candidato/{lead_id}/attiva")
async def attiva_candidato_terapeuta(lead_id: str, request: Request, user: dict = Depends(require_admin)):
    """Convert a lead-therapist into a real user account and send an activation email.

    The therapist stays 'sospeso' and 'documenti_verificati=false' until they complete
    onboarding AND the admin does the final review via /admin/terapisti/{id}/verifica.
    """
    try:
        lead_oid = ObjectId(lead_id)
    except Exception:
        raise HTTPException(400, "ID candidato non valido")

    lead = await db.terapisti.find_one({"_id": lead_oid})
    if not lead:
        raise HTTPException(404, "Candidato non trovato")
    if lead.get("approval_status") != "lead":
        raise HTTPException(400, "Questo profilo non è più in stato di candidatura")

    email = (lead.get("email") or "").lower().strip()
    if not email:
        raise HTTPException(400, "Email del candidato mancante")

    now = datetime.now(timezone.utc)
    existing_user = await db.users.find_one({"email": email})

    if existing_user:
        # Ensure the user is marked as therapist + suspended for onboarding
        user_id = str(existing_user["_id"])
        await db.users.update_one(
            {"_id": existing_user["_id"]},
            {"$set": {
                "role": "terapeuta",
                "is_active": False,
                "approval_status": "in_onboarding",
            }},
        )
    else:
        # Placeholder password (unusable) — the user will set a real one via the activation link
        placeholder = hash_password(_secrets.token_urlsafe(24))
        user_doc = {
            "email": email,
            "password_hash": placeholder,
            "role": "terapeuta",
            "nome": lead.get("nome", ""),
            "cognome": lead.get("cognome", ""),
            "telefono": lead.get("telefono"),
            "telefono_verificato": False,
            "is_verified": True,      # email is trusted (admin activated manually)
            "is_active": False,       # blocks login until password is set
            "approval_status": "in_onboarding",
            "consenso_privacy": True,
            "consenso_termini": True,
            "consenso_marketing": False,
            "created_at": now,
        }
        insert = await db.users.insert_one(user_doc)
        user_id = str(insert.inserted_id)

    # Bind terapista doc to the user + suspend + move status forward
    await db.terapisti.update_one(
        {"_id": lead_oid},
        {"$set": {
            "user_id": user_id,
            "approval_status": "in_onboarding",
            "sospeso": True,
            "sospeso_at": now,
            "sospeso_by": user["_id"],
            "documenti_verificati": False,
            "attivato_at": now,
            "attivato_by": user["_id"],
        }},
    )

    # Generate a single-use activation token (7 days). Reuses password_reset_tokens collection.
    raw_token = _secrets.token_urlsafe(32)
    await db.password_reset_tokens.delete_many({"user_id": user_id, "used_at": None})
    await db.password_reset_tokens.insert_one({
        "user_id": user_id,
        "token_hash": _token_digest(raw_token),
        "expires_at": now + timedelta(days=ACTIVATION_TOKEN_DAYS),
        "used_at": None,
        "created_at": now,
        "purpose": "therapist_activation",
    })

    frontend = _frontend_origin(request)
    activation_url = f"{frontend}/attiva-account?token={raw_token}"
    try:
        await send_therapist_activation_email(email, activation_url, lead.get("nome", ""))
    except Exception as e:
        logging.error(f"[EMAIL] therapist activation email failed: {e}")
        # Do not fail the whole operation — admin can re-trigger

    return {
        "message": "Candidato attivato. Email di attivazione inviata.",
        "user_id": user_id,
        "activation_url": activation_url if os.environ.get("ENV") != "production" else None,
    }
