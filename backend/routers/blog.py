"""Blog router: therapist articles + admin approval + public feed."""
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response

from deps import db, require_auth, require_admin
from models import ArticoloInput
from storage_service import put_object, get_object, mime_for_ext, APP_NAME as STORAGE_APP

router = APIRouter()

_BLOG_ALLOWED_MIME = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}
_BLOG_MAX_IMG_BYTES = 5 * 1024 * 1024  # 5 MB


@router.get("/blog")
async def list_articoli(user: dict = Depends(require_auth)):
    if user["role"] == "terapeuta":
        docs = await db.articoli.find({"autore_id": user["_id"]}).sort("created_at", -1).to_list(100)
    else:
        docs = await db.articoli.find({}).sort("created_at", -1).to_list(100)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


@router.post("/blog")
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


@router.put("/blog/{art_id}")
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


@router.patch("/blog/{art_id}/approva")
async def approva_articolo(art_id: str, user: dict = Depends(require_admin)):
    await db.articoli.update_one(
        {"_id": ObjectId(art_id)},
        {"$set": {"stato": "pubblicato", "approvato_da": user["_id"], "approvato_il": datetime.now(timezone.utc)}},
    )
    return {"message": "Articolo approvato e pubblicato"}


@router.patch("/blog/{art_id}/rifiuta")
async def rifiuta_articolo(art_id: str, user: dict = Depends(require_admin)):
    await db.articoli.update_one(
        {"_id": ObjectId(art_id)},
        {"$set": {"stato": "rifiutato", "updated_at": datetime.now(timezone.utc)}},
    )
    return {"message": "Articolo rifiutato"}


@router.delete("/blog/{art_id}")
async def delete_articolo(art_id: str, user: dict = Depends(require_auth)):
    doc = await db.articoli.find_one({"_id": ObjectId(art_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Articolo non trovato")
    if user["role"] != "admin" and doc.get("autore_id") != user["_id"]:
        raise HTTPException(status_code=403, detail="Accesso negato")
    await db.articoli.delete_one({"_id": ObjectId(art_id)})
    return {"message": "Articolo eliminato"}


@router.get("/public/blog")
async def public_blog():
    docs = await db.articoli.find({"stato": "pubblicato"}).sort("created_at", -1).to_list(50)
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs


# ─── Blog inline image upload (admin/therapist) ───────────────────────────
@router.post("/blog/upload-image")
async def upload_blog_image(file: UploadFile = File(...), user: dict = Depends(require_auth)):
    """Upload an inline image for a blog article. Returns a public URL to embed in the HTML.
    Available to therapists (own articles) and admins."""
    if user["role"] not in ("admin", "terapeuta"):
        raise HTTPException(403, "Accesso negato")
    ext = _BLOG_ALLOWED_MIME.get(file.content_type)
    if not ext:
        raise HTTPException(400, "Formato non supportato. Usa JPG, PNG, WEBP o GIF.")
    data = await file.read()
    if len(data) > _BLOG_MAX_IMG_BYTES:
        raise HTTPException(400, f"Immagine troppo grande. Max {_BLOG_MAX_IMG_BYTES // (1024*1024)}MB.")
    if len(data) == 0:
        raise HTTPException(400, "File vuoto")

    filename = f"{uuid.uuid4().hex}{ext}"
    storage_path = f"{STORAGE_APP}/blog/{filename}"
    try:
        put_object(storage_path, data, file.content_type)
    except Exception as e:
        logging.exception(f"[STORAGE] blog image upload failed: {e}")
        raise HTTPException(503, "Impossibile caricare l'immagine. Riprova.")
    # Persist mapping so /media/blog/{filename} can look up the object storage path
    await db.blog_media.insert_one({
        "filename": filename,
        "storage_path": storage_path,
        "content_type": file.content_type,
        "size": len(data),
        "uploaded_by": user["_id"],
        "uploaded_at": datetime.now(timezone.utc),
    })
    return {"url": f"/api/media/blog/{filename}", "filename": filename}


@router.get("/media/blog/{filename}")
async def get_blog_image(filename: str):
    """Public: serves a blog inline image (jpg/png/webp/gif) from Object Storage."""
    if "/" in filename or ".." in filename:
        raise HTTPException(400, "Invalid filename")
    doc = await db.blog_media.find_one({"filename": filename}, {"storage_path": 1, "content_type": 1})
    if not doc or not doc.get("storage_path"):
        raise HTTPException(404, "Image not found")
    try:
        data, ct = get_object(doc["storage_path"])
    except Exception as e:
        logging.warning(f"[STORAGE] blog image fetch failed: {e}")
        raise HTTPException(404, "Image not found")
    return Response(
        content=data,
        media_type=ct or doc.get("content_type") or mime_for_ext(Path(filename).suffix),
        headers={"Cache-Control": "public, max-age=86400"},
    )
