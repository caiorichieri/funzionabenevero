"""Appuntamenti (appointments) router: CRUD + Daily.co video token + attendance."""
import hashlib
import logging
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from deps import db, require_auth, require_admin
from models import AppuntamentoInput, AppuntamentoStatoInput
from daily_service import create_room_for_appointment, create_meeting_token, get_room_presenza

router = APIRouter()


# Access window for joining a video session
JOIN_OPEN_BEFORE_MIN = 20   # room + magic link become usable 20 min before start
JOIN_CLOSE_AFTER_MIN = 15   # magic link closes 15 min after start (no-show cutoff)


def _digest(raw: str) -> str:
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def _parse_appt_start(appt: dict) -> datetime | None:
    try:
        s = datetime.fromisoformat(appt["data_ora"].replace("Z", "+00:00"))
        if s.tzinfo is None:
            s = s.replace(tzinfo=timezone.utc)
        return s
    except Exception:
        return None


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
    valid_stati = ["prenotato", "confermato", "completato", "cancellato", "cancellato_con_addebito"]
    if data.stato not in valid_stati:
        raise HTTPException(status_code=400, detail=f"Stato non valido. Usa: {valid_stati}")
    await db.appuntamenti.update_one(
        {"_id": ObjectId(app_id)},
        {"$set": {"stato": data.stato, "updated_at": datetime.now(timezone.utc)}},
    )
    # Auto-generate fattura sanitaria as a FALLBACK for legacy paid appointments
    # that were confirmed BEFORE the "fattura al pagamento" flow was introduced.
    # New flow: fattura already emitted by _mark_payment_paid → this is idempotent
    # and only sends email if we truly generated a NEW invoice here.
    if data.stato in ("completato", "cancellato_con_addebito"):
        try:
            from routers.fatture import _generate_fattura_paziente
            from email_service import send_signature_receipt_email
            already_exists = await db.fatture.find_one({"appuntamento_id": app_id, "kind": "sanitaria"})
            fattura = await _generate_fattura_paziente(app_id)
            if fattura and not already_exists:
                # Only email if this call actually created the invoice
                appt = await db.appuntamenti.find_one({"_id": ObjectId(app_id)})
                paziente_user = await db.users.find_one({"_id": ObjectId(appt.get("paziente_user_id"))}) if appt else None
                if paziente_user and paziente_user.get("email"):
                    import base64
                    pdf_bytes = base64.b64decode(fattura["pdf_inline_b64"]) if fattura.get("pdf_inline_b64") else b""
                    await send_signature_receipt_email(
                        email=paziente_user["email"],
                        nome=paziente_user.get("nome", ""),
                        doc_titles=[
                            f"Fattura {fattura['numero']} — € {fattura.get('importo_totale', 0):.2f}",
                            "💡 Detraibile 19% al 730 come spesa sanitaria (art. 15 TUIR)",
                            "Conservala per almeno 5 anni",
                        ],
                        pdf_bytes=pdf_bytes,
                    )
        except Exception as e:
            import logging
            logging.exception(f"[APPT COMPLETION] auto-fattura fallback failed: {e}")
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
        # Block patient access if informed consent is not granted for this therapist
        consent = await db.informed_consents.find_one({
            "paziente_id": user["_id"],
            "terapista_id": app.get("terapeuta_id"),
            "status": "granted",
        })
        if not consent:
            raise HTTPException(
                412,
                "Devi prestare il Consenso Informato al Trattamento prima di partecipare alla seduta. Controlla la tua email."
            )
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

    # Gate access: allow logged-in users to join from 20 min before to 15 min
    # after the session's END (so they can rejoin if disconnected mid-session).
    start = _parse_appt_start(app)
    if start:
        durata = int(app.get("durata_minuti", 50))
        open_at = start - timedelta(minutes=JOIN_OPEN_BEFORE_MIN)
        close_at = start + timedelta(minutes=durata + JOIN_CLOSE_AFTER_MIN)
        now = datetime.now(timezone.utc)
        if now < open_at:
            # 425 Too Early — client should show countdown and retry at open_at
            raise HTTPException(
                status_code=425,
                detail={"code": "too_early", "available_at": open_at.isoformat(), "start_at": start.isoformat()},
            )
        if now > close_at:
            raise HTTPException(
                status_code=410,
                detail={"code": "session_closed", "start_at": start.isoformat(),
                        "message": "La finestra di accesso alla seduta è chiusa."},
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


# ─── MAGIC LINK (from 15-min-before email; no login required) ────────────────
@router.get("/videocall-magic/{app_id}")
async def videocall_magic(app_id: str, token: str):
    """Public endpoint: validate a magic token from the 15-min-before reminder
    email and return the Daily room URL + a fresh meeting token. No login
    required. Token is valid within the appointment window (until 15 min after
    scheduled end)."""
    try:
        app = await db.appuntamenti.find_one({"_id": ObjectId(app_id)})
    except Exception:
        raise HTTPException(404, "Appuntamento non trovato")
    if not app:
        raise HTTPException(404, "Appuntamento non trovato")
    stored_hash = app.get("videocall_magic_hash")
    if not stored_hash or _digest(token) != stored_hash:
        raise HTTPException(403, "Link non valido")

    # Time-based gate: 20 min before → 15 min after start.
    start = _parse_appt_start(app)
    if start:
        open_at = start - timedelta(minutes=JOIN_OPEN_BEFORE_MIN)
        close_at = start + timedelta(minutes=JOIN_CLOSE_AFTER_MIN)
        now = datetime.now(timezone.utc)
        if now < open_at:
            raise HTTPException(
                status_code=425,
                detail={"code": "too_early", "available_at": open_at.isoformat(), "start_at": start.isoformat()},
            )
        if now > close_at:
            # Also honour the stored expires timestamp (in case duration was patched)
            expires = app.get("videocall_magic_expires")
            if expires:
                exp = expires if expires.tzinfo else expires.replace(tzinfo=timezone.utc)
                close_at = max(close_at, exp)
            if now > close_at:
                raise HTTPException(
                    status_code=410,
                    detail={"code": "session_closed", "start_at": start.isoformat(),
                            "role_hint": "paziente",  # magic links are patient-facing
                            "message": "La finestra di accesso alla seduta è chiusa."},
                )

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

    paziente = await db.pazienti.find_one({"_id": ObjectId(app["paziente_id"])})
    user_name = f"{paziente.get('nome','')} {paziente.get('cognome','')}".strip() if paziente else "Paziente"
    meeting_token = await create_meeting_token(room_name, user_name, False, app["data_ora"], app.get("durata_minuti", 50))

    return {
        "room_url": room_url,
        "room_name": room_name,
        "token": meeting_token,
        "user_name": user_name,
        "is_owner": False,
        "data_ora": app["data_ora"],
        "durata_minuti": app.get("durata_minuti", 50),
    }




@router.get("/appuntamenti/{app_id}/presenze")
async def get_presenze(app_id: str, user: dict = Depends(require_auth)):
    """Get attendance logs for a completed appointment (admin + terapista only).
    Prefers the persisted snapshot in `seduta_logs`; falls back to a live Daily.co
    query if the snapshot doesn't exist yet."""
    if user["role"] not in ("admin", "terapeuta"):
        raise HTTPException(403, "Accesso negato")
    app = await db.appuntamenti.find_one({"_id": ObjectId(app_id)})
    if not app:
        raise HTTPException(404, "Appuntamento non trovato")
    if user["role"] == "terapeuta":
        terapista = await db.terapisti.find_one({"user_id": user["_id"]})
        if not terapista or str(terapista["_id"]) != app.get("terapeuta_id"):
            raise HTTPException(403, "Non autorizzato")

    # 1. Prefer the durable snapshot
    log = await db.seduta_logs.find_one({"appuntamento_id": app_id}, sort=[("snapshot_at", -1)])
    if log:
        return {
            "source": "snapshot",
            "presenze": log.get("presenze", []),
            "outcome": log.get("outcome"),
            "paziente_joined": log.get("paziente_joined", False),
            "terapeuta_joined": log.get("terapeuta_joined", False),
            "snapshot_at": log.get("snapshot_at").isoformat() if log.get("snapshot_at") else None,
            "room_name": app.get("daily_room_name"),
        }

    # 2. Fallback: live query to Daily
    room_name = app.get("daily_room_name")
    if not room_name:
        return {"source": "none", "presenze": [], "message": "Nessuna stanza video creata"}
    presenze = await get_room_presenza(room_name)
    return {"source": "live", "presenze": presenze, "room_name": room_name}


@router.get("/admin/seduta-logs")
async def admin_seduta_logs(
    from_date: str = None, to_date: str = None,
    terapeuta_id: str = None, outcome: str = None,
    limit: int = 100,
    admin: dict = Depends(require_admin),
):
    """List persisted seduta_logs with optional filters.
    - from_date / to_date: ISO date strings, filter on snapshot_at.
    - outcome: entrambi_presenti | no_show_paziente | no_show_terapeuta | no_show_entrambi
    - terapeuta_id: filter by terapista._id string.
    """
    q: dict = {}
    if outcome:
        q["outcome"] = outcome
    if terapeuta_id:
        q["terapeuta_id"] = terapeuta_id
    date_q: dict = {}
    for k, v in [("$gte", from_date), ("$lte", to_date)]:
        if not v:
            continue
        try:
            dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            date_q[k] = dt
        except Exception:
            pass
    if date_q:
        q["snapshot_at"] = date_q

    items = []
    async for log in db.seduta_logs.find(q).sort("snapshot_at", -1).limit(min(int(limit or 100), 500)):
        appt = await db.appuntamenti.find_one({"_id": ObjectId(log["appuntamento_id"])}) if log.get("appuntamento_id") else None
        t = await db.terapisti.find_one({"_id": ObjectId(appt["terapeuta_id"])}) if appt and appt.get("terapeuta_id") else None
        p = await db.pazienti.find_one({"_id": ObjectId(appt["paziente_id"])}) if appt and appt.get("paziente_id") else None
        items.append({
            "id": str(log["_id"]),
            "appuntamento_id": log.get("appuntamento_id"),
            "data_ora": appt.get("data_ora") if appt else None,
            "outcome": log.get("outcome"),
            "paziente_joined": log.get("paziente_joined", False),
            "terapeuta_joined": log.get("terapeuta_joined", False),
            "presenze": log.get("presenze", []),
            "snapshot_at": log.get("snapshot_at").isoformat() if log.get("snapshot_at") else None,
            "room_name": log.get("room_name"),
            "terapeuta": {
                "id": appt.get("terapeuta_id") if appt else None,
                "nome": f"{t.get('nome','')} {t.get('cognome','')}".strip() if t else "—",
            },
            "paziente": {
                "id": appt.get("paziente_id") if appt else None,
                "iniziali": f"{p.get('nome','?')[0]}.{p.get('cognome','?')[0]}." if p else "—",
            },
        })
    return {"items": items, "count": len(items)}
