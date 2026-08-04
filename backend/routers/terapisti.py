"""Terapisti (therapists) router: CRUD + profile + slots + documents + admin verification."""
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from fastapi.responses import FileResponse

from deps import db, require_auth, require_admin
from models import TerapistaProfileInput

router = APIRouter()

# ─── Local constants (docs storage) ────────────────────────────────────────
UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
TERAPISTI_DOCS_DIR = UPLOADS_DIR / "terapisti_docs"
TERAPISTI_DOCS_DIR.mkdir(parents=True, exist_ok=True)
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
    user_dir = TERAPISTI_DOCS_DIR / user["_id"]
    user_dir.mkdir(parents=True, exist_ok=True)
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


@router.post("/terapisti/me/autocertificazione-dpr445")
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
                if slot_t <= now:
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
                    if slot_t > now:
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


@router.get("/admin/terapisti/{terapista_id}/documenti/{tipo}/download")
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


@router.patch("/admin/terapisti/{terapista_id}/verifica")
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
