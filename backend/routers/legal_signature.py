"""Legal signature, MAJOR-version notification, and GDPR user rights (export + delete).

Endpoints:
 - POST /api/contracts/sign               → Signs one or more contracts, generates receipt PDF, stores it in Object Storage, emails it.
 - GET  /api/contracts/signatures/mine    → Lists all signature receipts for current user.
 - GET  /api/contracts/receipt/{sig_id}   → Downloads the PDF receipt (owner or admin).
 - GET  /api/contracts/pending/mine       → Docs the current user needs to sign (unsigned OR outdated after MAJOR).

 - POST /api/admin/contracts/{cid}/notify-major → Send MAJOR-update email to all users required to accept.
 - GET  /api/legal/decline/{token}        → Public endpoint: user clicks "NON ACCETTO" from email. Marks profile for 48h deactivation.

 - GET  /api/user/gdpr/export             → Portabilità (art. 20 GDPR) — full JSON of user's data.
 - POST /api/user/gdpr/delete-account     → Cancellazione (art. 17 GDPR) — soft-delete + admin workflow.
"""
import os
import uuid
import asyncio
import hashlib
import secrets
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from deps import db, require_auth, require_admin, find_user_by_id
from object_storage import put_object, get_object
from signature_pdf import generate_signature_receipt
from email_service import send_legal_major_update_email, send_signature_receipt_email

logger = logging.getLogger(__name__)

router = APIRouter()

# Kinds of documents required for a therapist to become active on the platform.
TERAPEUTA_REQUIRED_KINDS = [
    "contratto_collaborazione",
    "privacy_terapeuti",
    "termini_pazienti",  # T&C che si applicano anche al rapporto con la piattaforma
    "cookie_policy",
]


def _anonymize_ip(raw_ip: str) -> str:
    """Mask last octet (IPv4) or last 80 bits (IPv6)."""
    import ipaddress
    if not raw_ip:
        return ""
    try:
        ip = ipaddress.ip_address(raw_ip)
        if isinstance(ip, ipaddress.IPv4Address):
            parts = str(ip).split(".")
            parts[-1] = "0"
            return ".".join(parts)
        net = ipaddress.IPv6Network(f"{ip}/48", strict=False)
        return str(net.network_address)
    except ValueError:
        return ""


def _client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else ""


# ─── Signature ────────────────────────────────────────────────────────────────


class SignContractsInput(BaseModel):
    contract_ids: list[str] = Field(..., min_length=1, max_length=10)
    signature_name: str = Field(..., min_length=3, max_length=200)
    scrolled_all: bool = Field(default=True)  # frontend must set to true only after full scroll on every doc


@router.post("/contracts/sign")
async def sign_contracts(data: SignContractsInput, request: Request, user: dict = Depends(require_auth)):
    """Sign one or more contracts atomically.

    Validates: user identity, contracts exist and are current, name matches anagrafica,
    scroll flag is set. Then generates a PDF receipt, uploads to Object Storage,
    creates a `contract_acceptances` record per contract, sends email with PDF.
    """
    if not data.scrolled_all:
        raise HTTPException(400, "Devi leggere per intero ogni documento prima di firmare")

    # Load contracts
    contracts = []
    for cid in data.contract_ids:
        try:
            c = await db.contracts.find_one({"_id": ObjectId(cid)})
        except Exception:
            raise HTTPException(400, f"ID contratto non valido: {cid}")
        if not c:
            raise HTTPException(404, f"Contratto non trovato: {cid}")
        if not c.get("is_current"):
            raise HTTPException(400, f"Il contratto '{c.get('title')}' non è la versione corrente")
        contracts.append(c)

    # Validate signature_name matches user's name in anagrafica (case-insensitive)
    user_doc = await find_user_by_id(user["_id"])
    if not user_doc:
        raise HTTPException(404, "Utente non trovato")
    expected_full = f"{user_doc.get('nome', '').strip()} {user_doc.get('cognome', '').strip()}".strip().lower()
    typed = data.signature_name.strip().lower()
    if not expected_full or typed != expected_full:
        raise HTTPException(400, f"Il nome digitato deve corrispondere esattamente a: {user_doc.get('nome', '')} {user_doc.get('cognome', '')}")

    # Load terapeuta profile for the PDF (if user is terapeuta)
    terapeuta_doc = {}
    if user["role"] == "terapeuta":
        terapeuta_doc = await db.terapisti.find_one({"user_id": user["_id"]}) or {}
    terapeuta_data = {
        "nome": user_doc.get("nome", ""),
        "cognome": user_doc.get("cognome", ""),
        "email": user_doc.get("email", ""),
        "telefono": user_doc.get("telefono", ""),
        "codice_fiscale": terapeuta_doc.get("codice_fiscale", ""),
        "partita_iva": terapeuta_doc.get("partita_iva", ""),
        "albo_ordine": terapeuta_doc.get("albo_ordine", ""),
        "albo_numero": terapeuta_doc.get("albo_numero", ""),
    }

    now = datetime.now(timezone.utc)
    raw_ip = _client_ip(request)
    user_agent = (request.headers.get("user-agent") or "")[:300]

    # Generate PDF receipt
    docs_signed_pdf = [
        {
            "kind": c.get("kind"),
            "title": c.get("title"),
            "version": c.get("version"),
            "hash": c.get("content_hash"),
            "content_html": c.get("content_html"),
        }
        for c in contracts
    ]
    try:
        pdf_bytes = generate_signature_receipt(
            terapeuta_data=terapeuta_data,
            documents_signed=docs_signed_pdf,
            signature_name=data.signature_name.strip(),
            timestamp=now,
            ip_address=raw_ip,
            user_agent=user_agent,
        )
    except Exception as e:
        logger.exception("[SIGN] PDF generation failed")
        raise HTTPException(500, f"Errore generazione PDF: {e}")

    # Store PDF in Object Storage (with inline DB fallback if upload fails)
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()
    pdf_uuid = str(uuid.uuid4())
    storage_path = f"funzionabene/signature-receipts/{user['_id']}/{pdf_uuid}.pdf"
    canonical_path = None
    pdf_inline_b64 = None
    try:
        upload_res = await asyncio.to_thread(put_object, storage_path, pdf_bytes, "application/pdf")
        canonical_path = upload_res.get("path", storage_path)
    except Exception as e:
        logger.exception(f"[SIGN] Object Storage upload failed, falling back to inline DB storage: {e}")
        import base64
        pdf_inline_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    # Create acceptance records — one per contract, all linked by receipt_id
    receipt_id = str(uuid.uuid4())
    acceptance_ids = []
    for c in contracts:
        doc = {
            "user_id": user["_id"],
            "user_role": user["role"],
            "contract_id": str(c["_id"]),
            "contract_kind": c.get("kind"),
            "contract_version": c.get("version"),
            "content_hash": c.get("content_hash"),
            "signature_name": data.signature_name.strip(),
            "ip_anonymized": _anonymize_ip(raw_ip),
            "ip_raw": raw_ip,  # kept short-term for legal challenge; retention 10 years
            "user_agent": user_agent,
            "scrolled_to_end": data.scrolled_all,
            "receipt_id": receipt_id,
            "receipt_storage_path": canonical_path,
            "receipt_pdf_inline_b64": pdf_inline_b64,  # only set when Object Storage upload failed
            "receipt_pdf_hash": pdf_hash,
            "accepted_at": now,
        }
        result = await db.contract_acceptances.insert_one(doc)
        acceptance_ids.append(str(result.inserted_id))

    # Update user flags
    if user["role"] == "terapeuta":
        signed_kinds = [c.get("kind") for c in contracts]
        needs_all = all(k in signed_kinds for k in TERAPEUTA_REQUIRED_KINDS)
        if needs_all:
            await db.users.update_one(
                {"_id": ObjectId(user["_id"])},
                {"$set": {"dpa_firmato": True, "dpa_firmato_at": now}},
            )

    # Send email with PDF attachment (best-effort)
    try:
        await send_signature_receipt_email(
            email=user_doc.get("email", ""),
            nome=user_doc.get("nome", ""),
            doc_titles=[c.get("title") for c in contracts],
            pdf_bytes=pdf_bytes,
        )
    except Exception as e:
        logger.error(f"[SIGN] receipt email failed: {e}")

    return {
        "receipt_id": receipt_id,
        "acceptance_ids": acceptance_ids,
        "documents_signed": [{"kind": c.get("kind"), "title": c.get("title"), "version": c.get("version")} for c in contracts],
        "storage_path": canonical_path,
        "pdf_hash": pdf_hash,
        "signed_at": now.isoformat(),
    }


@router.get("/contracts/signatures/mine")
async def my_signatures(user: dict = Depends(require_auth)):
    """List all signature receipts (grouped by receipt_id) for the current user."""
    receipts: dict = {}
    async for a in db.contract_acceptances.find({"user_id": user["_id"]}).sort("accepted_at", -1):
        rid = a.get("receipt_id") or str(a["_id"])
        if rid not in receipts:
            receipts[rid] = {
                "receipt_id": rid,
                "signed_at": a.get("accepted_at").isoformat() if a.get("accepted_at") else None,
                "signature_name": a.get("signature_name"),
                "storage_path": a.get("receipt_storage_path"),
                "pdf_hash": a.get("receipt_pdf_hash"),
                "documents": [],
            }
        receipts[rid]["documents"].append({
            "kind": a.get("contract_kind"),
            "version": a.get("contract_version"),
            "hash": a.get("content_hash"),
        })
    return {"items": list(receipts.values())}


@router.get("/contracts/receipt/{receipt_id}")
async def download_receipt(receipt_id: str, user: dict = Depends(require_auth)):
    """Download the PDF receipt. Owner or admin only."""
    acc = await db.contract_acceptances.find_one({"receipt_id": receipt_id})
    if not acc:
        raise HTTPException(404, "Ricevuta non trovata")
    if acc.get("user_id") != user["_id"] and user["role"] != "admin":
        raise HTTPException(403, "Accesso negato")
    # Try inline base64 fallback first
    inline_b64 = acc.get("receipt_pdf_inline_b64")
    if inline_b64:
        import base64
        try:
            return Response(content=base64.b64decode(inline_b64), media_type="application/pdf", headers={
                "Content-Disposition": f'attachment; filename="ricevuta_{receipt_id[:8]}.pdf"'
            })
        except Exception:
            pass
    storage_path = acc.get("receipt_storage_path")
    if not storage_path:
        raise HTTPException(410, "PDF non più disponibile — contatta privacy@bidoc.it")
    try:
        data, ct = await asyncio.to_thread(get_object, storage_path)
    except Exception as e:
        logger.exception(f"[RECEIPT DOWNLOAD] failed: {e}")
        raise HTTPException(502, "Errore recupero PDF")
    return Response(content=data, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="ricevuta_{receipt_id[:8]}.pdf"'
    })


@router.get("/contracts/pending/mine")
async def pending_signatures(user: dict = Depends(require_auth)):
    """Return list of documents the current user needs to sign now.
    Terapeuti must sign TERAPEUTA_REQUIRED_KINDS.
    Pazienti currently need nothing (consents will be added in a later phase).
    """
    if user["role"] != "terapeuta":
        return {"pending": []}

    pending = []
    for kind in TERAPEUTA_REQUIRED_KINDS:
        current = await db.contracts.find_one({"kind": kind, "is_current": True})
        if not current:
            continue
        # Has the user accepted the CURRENT version?
        already = await db.contract_acceptances.find_one({
            "user_id": user["_id"],
            "contract_kind": kind,
            "contract_version": current.get("version"),
        })
        if not already:
            pending.append({
                "contract_id": str(current["_id"]),
                "kind": kind,
                "title": current.get("title"),
                "version": current.get("version"),
                "content_hash": current.get("content_hash"),
                "is_current": True,
            })
    return {"pending": pending}


# ─── MAJOR version notification & decline flow ────────────────────────────────


class NotifyMajorInput(BaseModel):
    """Optional body for /admin/contracts/{cid}/notify-major."""
    include_terapeuti: bool = True
    include_pazienti: bool = False


@router.post("/admin/contracts/{contract_id}/notify-major")
async def notify_major_update(contract_id: str, body: NotifyMajorInput, admin: dict = Depends(require_admin)):
    """Send MAJOR-update email to all users who accepted a previous version of this kind."""
    try:
        contract = await db.contracts.find_one({"_id": ObjectId(contract_id)})
    except Exception:
        raise HTTPException(400, "ID contratto non valido")
    if not contract:
        raise HTTPException(404, "Contratto non trovato")

    kind = contract.get("kind")
    version = contract.get("version")
    title = contract.get("title")
    frontend_url = os.environ.get("FRONTEND_URL") or os.environ.get("REACT_APP_BACKEND_URL", "https://www.funzionabene.it")

    # Find previous acceptances for this kind (any previous version)
    prev_acceptances = db.contract_acceptances.find({"contract_kind": kind, "contract_version": {"$ne": version}})
    notified_user_ids: set = set()
    async for a in prev_acceptances:
        uid = a.get("user_id")
        if not uid or uid in notified_user_ids:
            continue
        u = await find_user_by_id(uid)
        if not u:
            continue
        role = u.get("role")
        if role == "terapeuta" and not body.include_terapeuti:
            continue
        if role == "paziente" and not body.include_pazienti:
            continue
        notified_user_ids.add(uid)

        # Generate a decline token (one-time, valid 60 days)
        token = secrets.token_urlsafe(32)
        await db.legal_decline_tokens.insert_one({
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
            "user_id": uid,
            "contract_id": contract_id,
            "contract_kind": kind,
            "contract_version": version,
            "created_at": datetime.now(timezone.utc),
            "expires_at": datetime.now(timezone.utc) + timedelta(days=60),
            "used": False,
        })
        try:
            await send_legal_major_update_email(
                email=u.get("email", ""),
                nome=u.get("nome", "Terapeuta"),
                doc_title=title,
                doc_version=version,
                frontend_url=frontend_url,
                decline_token=token,
            )
        except Exception as e:
            logger.error(f"[MAJOR NOTIFY] email failed for {u.get('email')}: {e}")

    # Mark on the contract that major notify was sent
    await db.contracts.update_one(
        {"_id": ObjectId(contract_id)},
        {"$set": {"major_notification_sent_at": datetime.now(timezone.utc), "major_notification_by": admin["_id"]}},
    )

    return {
        "notified_count": len(notified_user_ids),
        "contract_kind": kind,
        "contract_version": version,
    }


@router.get("/legal/decline/{token}")
async def legal_decline(token: str, request: Request):
    """Public endpoint reached when a therapist clicks 'NON ACCETTO' in an email.

    Marks the user for automatic deactivation in 48 hours and returns a JSON
    payload that the frontend uses to render a confirmation page.
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    tok = await db.legal_decline_tokens.find_one({"token_hash": token_hash})
    if not tok:
        raise HTTPException(404, "Link non valido o scaduto")
    if tok.get("used"):
        raise HTTPException(410, "Questo link è già stato utilizzato")
    exp = tok.get("expires_at")
    if exp is not None:
        # MongoDB returns naive datetimes (UTC) — normalize before comparing.
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp < datetime.now(timezone.utc):
            raise HTTPException(410, "Link scaduto")

    now = datetime.now(timezone.utc)
    deactivate_at = now + timedelta(hours=48)
    user = await find_user_by_id(tok["user_id"])
    if not user:
        raise HTTPException(404, "Utente non trovato")

    # Mark user as pending deactivation for legal decline reason
    await db.users.update_one(
        {"_id": ObjectId(tok["user_id"])},
        {"$set": {
            "pending_deactivation_reason": "legal_decline",
            "pending_deactivation_at": deactivate_at,
            "pending_deactivation_contract_kind": tok.get("contract_kind"),
            "pending_deactivation_contract_version": tok.get("contract_version"),
        }},
    )
    # If terapeuta, also suspend the profile immediately so patients can't book new sessions
    if user.get("role") == "terapeuta":
        await db.terapisti.update_one(
            {"user_id": tok["user_id"]},
            {"$set": {"sospeso": True, "sospeso_motivo": "legal_decline", "sospeso_at": now}},
        )

    # Mark token as used
    await db.legal_decline_tokens.update_one(
        {"_id": tok["_id"]},
        {"$set": {"used": True, "used_at": now, "user_ip_anonymized": _anonymize_ip(_client_ip(request))}},
    )

    return {
        "message": "Il tuo profilo verrà disattivato definitivamente entro 48 ore.",
        "user_email": user.get("email"),
        "user_nome": user.get("nome"),
        "contract_kind": tok.get("contract_kind"),
        "contract_version": tok.get("contract_version"),
        "deactivate_at": deactivate_at.isoformat(),
    }


# ─── GDPR user rights ────────────────────────────────────────────────────────


@router.get("/user/gdpr/export")
async def gdpr_export(user: dict = Depends(require_auth)):
    """Portabilità (art. 20 GDPR) — return a JSON with all the user's data
    that BIDOC SRL holds as titolare."""
    uid = user["_id"]
    u = await find_user_by_id(uid)
    export = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "titolare": {
            "ragione_sociale": "BIDOC SRL",
            "sede": "Via Mazzini 62, 33097 Spilimbergo (PN)",
            "p_iva": "01985930930",
            "dpo_email": "privacy@bidoc.it",
        },
        "utente": {
            "id": uid,
            "email": u.get("email") if u else None,
            "nome": u.get("nome") if u else None,
            "cognome": u.get("cognome") if u else None,
            "role": u.get("role") if u else None,
            "created_at": u.get("created_at").isoformat() if u and u.get("created_at") else None,
            "telefono_verificato": u.get("telefono_verificato") if u else None,
        } if u else None,
    }
    # Terapeuta or paziente profile
    if u and u.get("role") == "terapeuta":
        p = await db.terapisti.find_one({"user_id": uid})
        if p:
            p["_id"] = str(p["_id"])
            for k in ["documenti", "note_cliniche"]:
                p.pop(k, None)
            export["profilo_terapeuta"] = p
    elif u and u.get("role") == "paziente":
        p = await db.pazienti.find_one({"user_id": uid})
        if p:
            p["_id"] = str(p["_id"])
            export["profilo_paziente"] = p
    # Appointments
    apps = []
    async for a in db.appuntamenti.find({"$or": [{"paziente_user_id": uid}, {"terapeuta_user_id": uid}]}).limit(500):
        a["_id"] = str(a["_id"])
        apps.append(a)
    export["appuntamenti"] = apps
    # Signed contracts
    sigs = []
    async for s in db.contract_acceptances.find({"user_id": uid}):
        sigs.append({
            "receipt_id": s.get("receipt_id"),
            "contract_kind": s.get("contract_kind"),
            "contract_version": s.get("contract_version"),
            "content_hash": s.get("content_hash"),
            "accepted_at": s.get("accepted_at").isoformat() if s.get("accepted_at") else None,
        })
    export["firme_contratti"] = sigs
    # Consent history (linked to this user)
    consent_history = []
    async for c in db.consent_history.find({"user_id": uid}).sort("timestamp", -1):
        consent_history.append({
            "consent_type": c.get("consent_type"),
            "action": c.get("action"),
            "timestamp": c.get("timestamp").isoformat() if c.get("timestamp") else None,
            "ip_anonymized": c.get("ip_anonymized"),
        })
    export["storico_consensi"] = consent_history
    # Current consent flags
    if u:
        export["consensi_attuali"] = u.get("consents") or {}
    return export


class DeleteAccountInput(BaseModel):
    motivazione: Optional[str] = None
    confirm_text: str = Field(..., min_length=1)


@router.post("/user/gdpr/delete-account")
async def gdpr_delete_account(data: DeleteAccountInput, request: Request, user: dict = Depends(require_auth)):
    """Cancellazione ('oblio', art. 17 GDPR) — soft-delete + admin workflow di 15 giorni
    per verifica obblighi di conservazione (fatturazione, contenzioso in corso).
    Dopo 15 giorni un cron job (futuro) opera l'anonimizzazione definitiva."""
    if data.confirm_text.strip().upper() != "CANCELLA":
        raise HTTPException(400, "Per confermare la cancellazione digita esattamente 'CANCELLA'")

    now = datetime.now(timezone.utc)
    hard_delete_at = now + timedelta(days=15)

    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": {
            "is_active": False,
            "gdpr_delete_requested_at": now,
            "gdpr_delete_hard_at": hard_delete_at,
            "gdpr_delete_reason": (data.motivazione or "")[:500],
            "gdpr_delete_ip": _anonymize_ip(_client_ip(request)),
        }},
    )
    # Log for admin visibility
    await db.gdpr_deletion_requests.insert_one({
        "user_id": user["_id"],
        "user_email": user.get("email"),
        "user_role": user.get("role"),
        "requested_at": now,
        "hard_delete_at": hard_delete_at,
        "reason": (data.motivazione or "")[:500],
        "ip_anonymized": _anonymize_ip(_client_ip(request)),
        "status": "pending_review",
    })

    return {
        "message": "Richiesta di cancellazione registrata. Il tuo account è stato disattivato. "
                   "I dati saranno cancellati definitivamente entro 15 giorni, salvo obblighi di legge (fatture, contenzioso).",
        "requested_at": now.isoformat(),
        "hard_delete_at": hard_delete_at.isoformat(),
    }


@router.get("/user/consents/mine")
async def my_consents(user: dict = Depends(require_auth)):
    """Return currently active consents and history for the authenticated user."""
    u = await find_user_by_id(user["_id"])
    if not u:
        raise HTTPException(404, "Utente non trovato")
    consents = u.get("consents") or {}
    history = []
    async for h in db.consent_history.find({"user_id": user["_id"]}).sort("timestamp", -1).limit(100):
        history.append({
            "action": h.get("action"),
            "consent_type": h.get("consent_type"),
            "timestamp": h.get("timestamp").isoformat() if h.get("timestamp") else None,
            "ip_anonymized": h.get("ip_anonymized"),
        })
    return {
        "consents": consents,
        "history": history,
        "dpa_firmato": u.get("dpa_firmato", False),
        "dpa_firmato_at": u.get("dpa_firmato_at").isoformat() if u.get("dpa_firmato_at") else None,
    }


class UpdateConsentInput(BaseModel):
    consent_type: str  # "marketing" | "miglioramento" | "ricerca"
    granted: bool


@router.post("/user/consents/update")
async def update_consent(data: UpdateConsentInput, request: Request, user: dict = Depends(require_auth)):
    """Update a single consent flag with history."""
    if data.consent_type not in ["marketing", "miglioramento", "ricerca", "sanitari"]:
        raise HTTPException(400, "consent_type non valido")
    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": ObjectId(user["_id"])},
        {"$set": {f"consents.{data.consent_type}": data.granted, f"consents.{data.consent_type}_at": now}},
    )
    await db.consent_history.insert_one({
        "user_id": user["_id"],
        "consent_type": data.consent_type,
        "action": "grant" if data.granted else "revoke",
        "timestamp": now,
        "ip_anonymized": _anonymize_ip(_client_ip(request)),
    })
    return {"consent_type": data.consent_type, "granted": data.granted, "timestamp": now.isoformat()}


# ─── Admin manual triggers for scheduled jobs ────────────────────────────────


@router.post("/admin/jobs/retention/run")
async def admin_run_retention(admin: dict = Depends(require_admin)):
    """Manually trigger the retention_anonymize job. Useful for testing."""
    from scheduled_jobs import retention_anonymize
    return await retention_anonymize(db)


@router.post("/admin/jobs/legal-decline/run")
async def admin_run_legal_decline(admin: dict = Depends(require_admin)):
    """Manually trigger the process_legal_declines job."""
    from scheduled_jobs import process_legal_declines
    return await process_legal_declines(db)


@router.post("/admin/jobs/weekly-fatture/run")
async def admin_run_weekly_fatture(admin: dict = Depends(require_admin)):
    """Manually trigger the weekly fatture email job."""
    from scheduled_jobs import weekly_fatture_email
    return await weekly_fatture_email(db)


@router.post("/admin/jobs/monthly-commissioni/run")
async def admin_run_monthly_commissioni(admin: dict = Depends(require_admin)):
    """Manually trigger the monthly commissioni generation job."""
    from scheduled_jobs import monthly_generate_commissioni
    return await monthly_generate_commissioni(db)
