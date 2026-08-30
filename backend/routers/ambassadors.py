"""Ambassadors router: public read + admin CRUD.

Ambassadors are people (typically paralympic athletes or persons with lived
experience of disability) who publicly support the "Sessualità e Disabilità"
landing page. Each has: name, role, short testimonial, longer story, photo.
"""
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from deps import db, require_admin

router = APIRouter()

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads" / "ambassadors"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
_ALLOWED_MIME = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


class AmbassadorInput(BaseModel):
    nome: str = Field(min_length=1, max_length=120)
    ruolo: str = Field(min_length=1, max_length=120)
    testimonianza: str = Field(min_length=1, max_length=280)
    storia: str = Field(default="", max_length=3000)
    ordine: int = Field(default=100, ge=0, le=9999)
    attivo: bool = True


def _serialize(doc: dict) -> dict:
    """Project ambassador doc → JSON shape used by both public + admin views."""
    foto = doc.get("foto_filename")
    return {
        "id": str(doc["_id"]),
        "nome": doc.get("nome"),
        "ruolo": doc.get("ruolo"),
        "testimonianza": doc.get("testimonianza"),
        "storia": doc.get("storia") or "",
        "ordine": doc.get("ordine", 100),
        "attivo": doc.get("attivo", True),
        "foto_url": f"/api/media/ambassadors/{foto}" if foto else None,
        "created_at": (doc["created_at"].isoformat() if doc.get("created_at") else None),
        "updated_at": (doc["updated_at"].isoformat() if doc.get("updated_at") else None),
    }


# ─── Public ─────────────────────────────────────────────────────────────
@router.get("/public/ambassadors")
async def list_public_ambassadors():
    """Only active ambassadors, ordered by `ordine` then created_at."""
    docs = await db.ambassadors.find({"attivo": True}).sort([("ordine", 1), ("created_at", -1)]).to_list(50)
    return [_serialize(d) for d in docs]


# ─── Admin CRUD ─────────────────────────────────────────────────────────
@router.get("/admin/ambassadors")
async def list_admin_ambassadors(user: dict = Depends(require_admin)):
    docs = await db.ambassadors.find({}).sort([("ordine", 1), ("created_at", -1)]).to_list(200)
    return [_serialize(d) for d in docs]


@router.post("/admin/ambassadors")
async def create_ambassador(body: AmbassadorInput, user: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc)
    doc = {
        **body.model_dump(),
        "foto_filename": None,
        "created_at": now,
        "updated_at": now,
        "created_by": user.get("email"),
    }
    result = await db.ambassadors.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _serialize(doc)


@router.patch("/admin/ambassadors/{amb_id}")
async def update_ambassador(amb_id: str, body: AmbassadorInput, user: dict = Depends(require_admin)):
    try:
        oid = ObjectId(amb_id)
    except Exception:
        raise HTTPException(400, "ID non valido")
    update = {**body.model_dump(), "updated_at": datetime.now(timezone.utc)}
    result = await db.ambassadors.update_one({"_id": oid}, {"$set": update})
    if result.matched_count == 0:
        raise HTTPException(404, "Ambassador non trovato")
    doc = await db.ambassadors.find_one({"_id": oid})
    return _serialize(doc)


@router.delete("/admin/ambassadors/{amb_id}")
async def delete_ambassador(amb_id: str, user: dict = Depends(require_admin)):
    try:
        oid = ObjectId(amb_id)
    except Exception:
        raise HTTPException(400, "ID non valido")
    doc = await db.ambassadors.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Ambassador non trovato")
    # Delete photo file if any (best effort)
    if doc.get("foto_filename"):
        try:
            (UPLOADS_DIR / doc["foto_filename"]).unlink(missing_ok=True)
        except Exception as e:
            logging.warning(f"[AMBASSADOR] photo delete failed: {e}")
    await db.ambassadors.delete_one({"_id": oid})
    return {"message": "Ambassador eliminato"}


@router.post("/admin/ambassadors/{amb_id}/foto")
async def upload_ambassador_photo(
    amb_id: str, file: UploadFile = File(...), user: dict = Depends(require_admin)
):
    try:
        oid = ObjectId(amb_id)
    except Exception:
        raise HTTPException(400, "ID non valido")
    doc = await db.ambassadors.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Ambassador non trovato")
    ext = _ALLOWED_MIME.get(file.content_type)
    if not ext:
        raise HTTPException(400, "Formato non supportato. Usa JPG, PNG o WEBP.")
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(400, f"Immagine troppo grande. Max {_MAX_BYTES // (1024*1024)}MB.")
    # Replace previous file if exists
    if doc.get("foto_filename"):
        try:
            (UPLOADS_DIR / doc["foto_filename"]).unlink(missing_ok=True)
        except Exception:
            pass
    filename = f"{amb_id}{ext}"
    (UPLOADS_DIR / filename).write_bytes(data)
    await db.ambassadors.update_one(
        {"_id": oid},
        {"$set": {"foto_filename": filename, "updated_at": datetime.now(timezone.utc)}},
    )
    return {"foto_url": f"/api/media/ambassadors/{filename}"}
