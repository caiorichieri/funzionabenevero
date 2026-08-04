"""Blog router: therapist articles + admin approval + public feed."""
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from deps import db, require_auth, require_admin
from models import ArticoloInput

router = APIRouter()


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
