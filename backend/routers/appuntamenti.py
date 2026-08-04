"""Appuntamenti (appointments) router: CRUD + Daily.co video token + attendance."""
import logging
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from deps import db, require_auth, require_admin
from models import AppuntamentoInput, AppuntamentoStatoInput
from daily_service import create_room_for_appointment, create_meeting_token, get_room_presenza

router = APIRouter()


@router.get("/appuntamenti")
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


@router.post("/appuntamenti")
async def create_appuntamento(data: AppuntamentoInput, user: dict = Depends(require_auth)):
    doc = data.model_dump()
    doc["stato"] = "prenotato"
    doc["created_at"] = datetime.now(timezone.utc)
    doc["created_by"] = user["_id"]
    result = await db.appuntamenti.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


@router.put("/appuntamenti/{app_id}")
async def update_appuntamento(app_id: str, data: AppuntamentoInput, user: dict = Depends(require_auth)):
    update = data.model_dump(exclude_none=True)
    update["updated_at"] = datetime.now(timezone.utc)
    await db.appuntamenti.update_one({"_id": ObjectId(app_id)}, {"$set": update})
    doc = await db.appuntamenti.find_one({"_id": ObjectId(app_id)})
    doc["_id"] = str(doc["_id"])
    return doc


@router.patch("/appuntamenti/{app_id}/stato")
async def update_stato_appuntamento(app_id: str, data: AppuntamentoStatoInput, user: dict = Depends(require_auth)):
    valid_stati = ["prenotato", "confermato", "completato", "cancellato"]
    if data.stato not in valid_stati:
        raise HTTPException(status_code=400, detail=f"Stato non valido. Usa: {valid_stati}")
    await db.appuntamenti.update_one(
        {"_id": ObjectId(app_id)},
        {"$set": {"stato": data.stato, "updated_at": datetime.now(timezone.utc)}},
    )
    return {"message": f"Stato aggiornato a: {data.stato}"}


@router.delete("/appuntamenti/{app_id}")
async def delete_appuntamento(app_id: str, user: dict = Depends(require_admin)):
    await db.appuntamenti.delete_one({"_id": ObjectId(app_id)})
    return {"message": "Appuntamento eliminato"}


# ─── VIDEO CALL (Daily.co) ────────────────────────────────────────────────────
@router.post("/appuntamenti/{app_id}/video-token")
async def get_video_token(app_id: str, user: dict = Depends(require_auth)):
    """Generate a Daily.co meeting token for the current user to join this appointment's video room."""
    app = await db.appuntamenti.find_one({"_id": ObjectId(app_id)})
    if not app:
        raise HTTPException(404, "Appuntamento non trovato")

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
            {"$set": {"daily_room_url": room_url, "daily_room_name": room_name}},
        )

    user_name = f"{user.get('nome','')} {user.get('cognome','')}".strip() or user.get("email", "Utente")
    token = await create_meeting_token(room_name, user_name, is_owner, app["data_ora"], app.get("durata_minuti", 50))

    return {
        "room_url": room_url,
        "room_name": room_name,
        "token": token,
        "user_name": user_name,
        "is_owner": is_owner,
        "data_ora": app["data_ora"],
        "durata_minuti": app.get("durata_minuti", 50),
    }


@router.get("/appuntamenti/{app_id}/presenze")
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
