"""Diario Emozionale — patient's emotional journal.

Simple, private notes the patient writes between sessions.
Therapists can view (read-only) all entries of their assigned patients
before a session to arrive prepared.

Endpoints:
 - POST   /api/diario                              paziente creates
 - GET    /api/diario/mine                         paziente lists own
 - PUT    /api/diario/{entry_id}                   paziente edits (only if not letto)
 - DELETE /api/diario/{entry_id}                   paziente deletes own
 - GET    /api/diario/paziente/{paziente_id}       terapeuta reads (marks letto)
 - GET    /api/diario/paziente/{paziente_id}/count terapeuta unread counter (badge)
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from deps import db, require_auth

logger = logging.getLogger(__name__)
router = APIRouter()

VALID_MOODS = {"felice", "sereno", "neutro", "ansioso", "triste", "arrabbiato"}
MOOD_EMOJI = {
    "felice": "😊", "sereno": "🙂", "neutro": "😐",
    "ansioso": "😟", "triste": "😢", "arrabbiato": "😠",
}
MAX_CONTENT = 1000


class DiarioInput(BaseModel):
    mood: str = Field(..., description="Uno dei mood validi")
    contenuto: str = Field(..., min_length=1, max_length=MAX_CONTENT)
    tags: Optional[list[str]] = Field(default_factory=list, max_length=8)
    condividi_con_terapeuta: bool = Field(default=True, description="Se il terapeuta potrà leggere questa nota")


def _serialize(d: dict) -> dict:
    return {
        "id": str(d["_id"]),
        "mood": d.get("mood"),
        "mood_emoji": MOOD_EMOJI.get(d.get("mood"), ""),
        "contenuto": d.get("contenuto"),
        "tags": d.get("tags", []),
        "condividi_con_terapeuta": d.get("condividi_con_terapeuta", True),
        "letto_da_terapeuta": d.get("letto_da_terapeuta", False),
        "letto_at": d.get("letto_at").isoformat() if d.get("letto_at") else None,
        "created_at": d.get("created_at").isoformat() if d.get("created_at") else None,
        "updated_at": d.get("updated_at").isoformat() if d.get("updated_at") else None,
    }


def _validate_mood(m: str):
    if m not in VALID_MOODS:
        raise HTTPException(400, f"Mood non valido. Ammessi: {', '.join(sorted(VALID_MOODS))}")


@router.post("/diario")
async def create_entry(data: DiarioInput, user: dict = Depends(require_auth)):
    if user.get("role") != "paziente":
        raise HTTPException(403, "Solo i pazienti possono scrivere nel proprio diario")
    _validate_mood(data.mood)
    now = datetime.now(timezone.utc)
    doc = {
        "paziente_id": user["_id"],
        "mood": data.mood,
        "contenuto": data.contenuto.strip(),
        "tags": [t.strip().lower() for t in (data.tags or []) if t.strip()][:8],
        "condividi_con_terapeuta": bool(data.condividi_con_terapeuta),
        "letto_da_terapeuta": False,
        "letto_at": None,
        "created_at": now,
        "updated_at": now,
    }
    r = await db.diario_entries.insert_one(doc)
    doc["_id"] = r.inserted_id
    return _serialize(doc)


@router.get("/diario/mine")
async def list_mine(user: dict = Depends(require_auth), limit: int = 50):
    if user.get("role") != "paziente":
        raise HTTPException(403, "Solo i pazienti")
    limit = max(1, min(200, limit))
    out = []
    async for d in db.diario_entries.find({"paziente_id": user["_id"]}).sort("created_at", -1).limit(limit):
        out.append(_serialize(d))
    return {"items": out, "count": len(out)}


@router.put("/diario/{entry_id}")
async def update_entry(entry_id: str, data: DiarioInput, user: dict = Depends(require_auth)):
    if user.get("role") != "paziente":
        raise HTTPException(403, "Solo i pazienti")
    _validate_mood(data.mood)
    try:
        oid = ObjectId(entry_id)
    except Exception:
        raise HTTPException(400, "ID non valido")
    existing = await db.diario_entries.find_one({"_id": oid, "paziente_id": user["_id"]})
    if not existing:
        raise HTTPException(404, "Voce non trovata")
    if existing.get("letto_da_terapeuta"):
        raise HTTPException(409, "Non puoi modificare una nota già letta dal terapeuta")
    await db.diario_entries.update_one(
        {"_id": oid},
        {"$set": {
            "mood": data.mood,
            "contenuto": data.contenuto.strip(),
            "tags": [t.strip().lower() for t in (data.tags or []) if t.strip()][:8],
            "condividi_con_terapeuta": bool(data.condividi_con_terapeuta),
            "updated_at": datetime.now(timezone.utc),
        }},
    )
    updated = await db.diario_entries.find_one({"_id": oid})
    return _serialize(updated)


@router.delete("/diario/{entry_id}")
async def delete_entry(entry_id: str, user: dict = Depends(require_auth)):
    if user.get("role") != "paziente":
        raise HTTPException(403, "Solo i pazienti")
    try:
        oid = ObjectId(entry_id)
    except Exception:
        raise HTTPException(400, "ID non valido")
    r = await db.diario_entries.delete_one({"_id": oid, "paziente_id": user["_id"]})
    if r.deleted_count == 0:
        raise HTTPException(404, "Voce non trovata")
    return {"message": "Voce eliminata"}


async def _assert_therapist_can_read(user: dict, paziente_id: str):
    """Only a therapist who has at least one appuntamento with the patient can read."""
    if user.get("role") == "admin":
        return
    if user.get("role") != "terapeuta":
        raise HTTPException(403, "Accesso negato")
    appt = await db.appuntamenti.find_one({
        "terapeuta_user_id": user["_id"],
        "paziente_user_id": paziente_id,
    })
    if not appt:
        raise HTTPException(403, "Non hai un rapporto terapeutico con questo paziente")


@router.get("/diario/paziente/{paziente_id}")
async def list_for_terapeuta(paziente_id: str, user: dict = Depends(require_auth), limit: int = 50):
    await _assert_therapist_can_read(user, paziente_id)
    limit = max(1, min(200, limit))
    # Only entries the paziente wanted to share
    cursor = db.diario_entries.find({
        "paziente_id": paziente_id,
        "condividi_con_terapeuta": True,
    }).sort("created_at", -1).limit(limit)

    items = []
    new_ids = []
    async for d in cursor:
        items.append(_serialize(d))
        if not d.get("letto_da_terapeuta"):
            new_ids.append(d["_id"])

    # Mark as read (only when a real therapist views, not admin)
    if new_ids and user.get("role") == "terapeuta":
        now = datetime.now(timezone.utc)
        await db.diario_entries.update_many(
            {"_id": {"$in": new_ids}},
            {"$set": {"letto_da_terapeuta": True, "letto_at": now, "letto_by": user["_id"]}},
        )

    return {"items": items, "count": len(items), "just_marked_read": len(new_ids)}


@router.get("/diario/paziente/{paziente_id}/count")
async def unread_count(paziente_id: str, user: dict = Depends(require_auth)):
    await _assert_therapist_can_read(user, paziente_id)
    n = await db.diario_entries.count_documents({
        "paziente_id": paziente_id,
        "condividi_con_terapeuta": True,
        "letto_da_terapeuta": False,
    })
    return {"unread": n}
