"""Registro dei Trattamenti — GDPR Art. 30.

CRUD + PDF export for the Register of Processing Activities.
Only accessible to admin.

Endpoints:
 - GET  /api/admin/registro-trattamenti           → list all entries
 - POST /api/admin/registro-trattamenti           → create
 - PUT  /api/admin/registro-trattamenti/{id}      → update
 - DELETE /api/admin/registro-trattamenti/{id}    → hard delete (rarely used; prefer archive)
 - POST /api/admin/registro-trattamenti/{id}/archive   → archive
 - GET  /api/admin/registro-trattamenti/export/pdf     → PDF download
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from deps import db, require_admin

logger = logging.getLogger(__name__)
router = APIRouter()


class RegistroEntryInput(BaseModel):
    codice: str = Field(..., min_length=1, max_length=20)
    denominazione: str = Field(..., min_length=3, max_length=200)
    ruolo: str = Field(..., pattern="^(titolare|responsabile|contitolare)$")
    finalita: str = Field(..., min_length=3, max_length=2000)
    base_giuridica: str = Field(..., min_length=3, max_length=1000)
    categorie_interessati: str = Field(..., min_length=3, max_length=1000)
    categorie_dati: str = Field(..., min_length=3, max_length=2000)
    categorie_particolari: Optional[str] = Field(default="", max_length=1000)
    destinatari: Optional[str] = Field(default="", max_length=2000)
    trasferimenti_extra_ue: Optional[str] = Field(default="Nessun trasferimento extra-UE", max_length=1000)
    misure_sicurezza: str = Field(..., min_length=3, max_length=3000)
    termini_cancellazione: str = Field(..., min_length=3, max_length=1000)
    note: Optional[str] = Field(default="", max_length=2000)


def _serialize(doc: dict) -> dict:
    return {
        "id": str(doc["_id"]),
        "codice": doc.get("codice"),
        "denominazione": doc.get("denominazione"),
        "ruolo": doc.get("ruolo"),
        "finalita": doc.get("finalita"),
        "base_giuridica": doc.get("base_giuridica"),
        "categorie_interessati": doc.get("categorie_interessati"),
        "categorie_dati": doc.get("categorie_dati"),
        "categorie_particolari": doc.get("categorie_particolari", ""),
        "destinatari": doc.get("destinatari", ""),
        "trasferimenti_extra_ue": doc.get("trasferimenti_extra_ue", ""),
        "misure_sicurezza": doc.get("misure_sicurezza"),
        "termini_cancellazione": doc.get("termini_cancellazione"),
        "note": doc.get("note", ""),
        "archived": doc.get("archived", False),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
        "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
    }


@router.get("/admin/registro-trattamenti")
async def list_entries(include_archived: bool = False, admin: dict = Depends(require_admin)):
    query = {} if include_archived else {"archived": {"$ne": True}}
    out = []
    async for d in db.registro_trattamenti.find(query).sort("codice", 1):
        out.append(_serialize(d))
    return {"items": out, "count": len(out)}


@router.post("/admin/registro-trattamenti")
async def create_entry(data: RegistroEntryInput, admin: dict = Depends(require_admin)):
    dup = await db.registro_trattamenti.find_one({"codice": data.codice, "archived": {"$ne": True}})
    if dup:
        raise HTTPException(400, f"Esiste già una voce attiva con codice {data.codice}")
    now = datetime.now(timezone.utc)
    doc = {
        **data.model_dump(),
        "archived": False,
        "created_at": now, "updated_at": now,
        "created_by": admin["_id"], "updated_by": admin["_id"],
    }
    r = await db.registro_trattamenti.insert_one(doc)
    doc["_id"] = r.inserted_id
    return _serialize(doc)


@router.put("/admin/registro-trattamenti/{entry_id}")
async def update_entry(entry_id: str, data: RegistroEntryInput, admin: dict = Depends(require_admin)):
    try:
        oid = ObjectId(entry_id)
    except Exception:
        raise HTTPException(400, "ID non valido")
    existing = await db.registro_trattamenti.find_one({"_id": oid})
    if not existing:
        raise HTTPException(404, "Voce non trovata")
    now = datetime.now(timezone.utc)
    await db.registro_trattamenti.update_one(
        {"_id": oid},
        {"$set": {**data.model_dump(), "updated_at": now, "updated_by": admin["_id"]}},
    )
    updated = await db.registro_trattamenti.find_one({"_id": oid})
    return _serialize(updated)


@router.post("/admin/registro-trattamenti/{entry_id}/archive")
async def archive_entry(entry_id: str, admin: dict = Depends(require_admin)):
    try:
        oid = ObjectId(entry_id)
    except Exception:
        raise HTTPException(400, "ID non valido")
    r = await db.registro_trattamenti.update_one(
        {"_id": oid},
        {"$set": {"archived": True, "archived_at": datetime.now(timezone.utc), "archived_by": admin["_id"]}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, "Voce non trovata")
    return {"message": "Voce archiviata"}


@router.delete("/admin/registro-trattamenti/{entry_id}")
async def delete_entry(entry_id: str, admin: dict = Depends(require_admin)):
    try:
        oid = ObjectId(entry_id)
    except Exception:
        raise HTTPException(400, "ID non valido")
    r = await db.registro_trattamenti.delete_one({"_id": oid})
    if r.deleted_count == 0:
        raise HTTPException(404, "Voce non trovata")
    return {"message": "Voce eliminata"}


@router.get("/admin/registro-trattamenti/export/pdf")
async def export_pdf(admin: dict = Depends(require_admin)):
    """Genera un PDF conforme all'art. 30 GDPR pronto per il Garante."""
    from registro_pdf import generate_registro_pdf
    entries = []
    async for d in db.registro_trattamenti.find({"archived": {"$ne": True}}).sort("codice", 1):
        entries.append(d)
    pdf_bytes = generate_registro_pdf(entries, admin_name=f"{admin.get('nome','')} {admin.get('cognome','')}".strip())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="registro_trattamenti_{datetime.now(timezone.utc).strftime("%Y%m%d")}.pdf"'},
    )
