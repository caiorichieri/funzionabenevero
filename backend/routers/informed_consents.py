"""Informed consent (Consenso Informato al Trattamento) router.

Legal architecture: the consent is issued by the PATIENT directly to the
individual THERAPIST (not to Bidoc SRL, which acts as a marketplace only).
One valid consent per (paziente, terapeuta) pair. If a patient books with a
new therapist, a NEW consent is required before the session.

Flow:
1. Patient books first session with a therapist.
2. Booking service checks for an active consent for that (paziente, terapeuta).
3. If missing, creates a `pending` consent + sends email with a magic-link
   pointing to /consenso-informato/{consent_id}?token=xxx.
4. Patient opens the link, reads the therapist's text, ticks the checkbox,
   clicks "Presto il mio consenso". Backend records timestamp, IP, user-agent,
   sets status=granted.
5. On subsequent bookings with the SAME therapist: consent is still valid
   (unless revoked).
"""
import hashlib
import logging
import secrets
from datetime import datetime, timezone, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request

from deps import db, require_auth
from email_service import _send_raw, SENDER_EMAIL
import os

router = APIRouter()
logger = logging.getLogger(__name__)

# Default consent text used when a therapist has not customized their own.
DEFAULT_CONSENT_TEMPLATE = """Con la presente, il/la sottoscritto/a paziente dichiara di essere stato/a
adeguatamente informato/a dal Dr./Dr.ssa {terapista_nome} {terapista_cognome} in merito a:

1. **Natura e finalità della prestazione professionale**: sessioni di
   psicoterapia/consulenza sessuologica erogate a distanza tramite piattaforma
   FunzionaBene, di durata indicativa di 50 minuti ciascuna.

2. **Metodologia e strumenti utilizzati**: dialogo clinico strutturato,
   somministrazione di eventuali test o questionari psicometrici, tecniche
   proprie dell'approccio terapeutico del/la professionista.

3. **Rischi e limiti**: la psicoterapia può comportare l'emergere di vissuti
   emotivi intensi. Non sono garantiti esiti specifici. Il/la professionista
   opera nel rispetto del Codice Deontologico degli Psicologi Italiani.

4. **Alternative disponibili**: il/la paziente può in ogni momento richiedere
   consulto con altro professionista o interrompere il percorso.

5. **Trattamento dei dati personali sanitari**: i dati emersi durante le
   sedute sono trattati esclusivamente dal/la professionista come Titolare
   autonomo del Trattamento, ai sensi degli artt. 6 e 9 GDPR, con obbligo di
   segreto professionale (art. 622 c.p.). FunzionaBene (Bidoc SRL) agisce
   unicamente come fornitore tecnologico e non ha accesso ai contenuti clinici.

6. **Diritto di revoca**: il/la paziente può revocare il presente consenso in
   qualsiasi momento contattando direttamente il/la professionista.

7. **Conservazione**: la documentazione clinica è conservata dal/la
   professionista per il tempo previsto dalla normativa (10 anni dall'ultima
   prestazione)."""


def _digest(raw: str) -> str:
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


async def _get_terapista_and_user(terapista_id: str):
    t = await db.terapisti.find_one({"_id": ObjectId(terapista_id)})
    if not t:
        return None, None
    u = await db.users.find_one({"_id": ObjectId(t["user_id"])}) if t.get("user_id") else None
    return t, u


async def _consent_email(
    paziente_email: str, paziente_nome: str,
    terapista_nome: str, terapista_cognome: str,
    consent_id: str, raw_token: str,
) -> None:
    frontend = (os.environ.get("FRONTEND_URL") or "https://funzionabene.it").rstrip("/")
    link = f"{frontend}/consenso-informato/{consent_id}?token={raw_token}"
    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:40px 20px;background:#0A0A0A;font-family:Helvetica,Arial,sans-serif;color:#F4F1ED;">
<table width="560" cellpadding="0" cellspacing="0" style="margin:0 auto;background:#111;border-radius:20px;overflow:hidden;">
<tr><td style="padding:32px 40px;text-align:center;border-bottom:1px solid rgba(255,255,255,0.08);">
<div style="font-family:Georgia,serif;font-size:22px;color:#F4F1ED;">funzionabene</div>
<div style="font-size:10px;letter-spacing:3px;color:#6B8FA3;margin-top:6px;">CONSENSO INFORMATO AL TRATTAMENTO</div>
</td></tr>
<tr><td style="padding:32px 40px 12px;">
<h1 style="font-family:Georgia,serif;font-size:26px;color:#D4A017;margin:0 0 14px;font-weight:500;">
Un passo prima della tua prima seduta
</h1>
<p style="color:rgba(230,226,216,0.85);font-size:15px;line-height:1.6;margin:0 0 12px;">
Ciao {paziente_nome},<br><br>
prima della prima seduta con Dr./Dr.ssa <strong>{terapista_nome} {terapista_cognome}</strong>,
la legge italiana e il Codice Deontologico degli Psicologi richiedono che tu firmi
il <strong>Consenso Informato al Trattamento</strong>.
</p>
<p style="color:rgba(230,226,216,0.75);font-size:14px;line-height:1.6;margin:0 0 8px;">
Clicca il pulsante qui sotto per leggere il documento e prestare il tuo consenso.
Il pulsante è personale e valido per te.
</p>
</td></tr>
<tr><td style="padding:20px 40px 28px;text-align:center;">
<a href="{link}" style="display:inline-block;background:#D4A017;color:#0A0A0A;font-weight:600;text-decoration:none;padding:16px 40px;border-radius:12px;font-size:15px;letter-spacing:0.5px;">Leggi e presta il tuo consenso →</a>
<p style="font-size:11px;color:rgba(230,226,216,0.4);margin:16px 0 0;">
Il consenso è verso il singolo/la singola professionista, non verso Bidoc SRL/FunzionaBene.<br>
Puoi revocarlo in qualsiasi momento contattando direttamente il/la professionista.
</p>
</td></tr>
<tr><td style="padding:20px 40px;border-top:1px solid rgba(255,255,255,0.08);text-align:center;">
<p style="color:rgba(230,226,216,0.4);font-size:11px;margin:0;">© FunzionaBene · Bidoc SRL (marketplace tecnologico)</p>
</td></tr>
</table></body></html>"""
    await _send_raw({
        "from": f"FunzionaBene <{SENDER_EMAIL}>",
        "to": [paziente_email],
        "subject": f"Consenso informato — Dr. {terapista_nome} {terapista_cognome}",
        "html": html,
    })


async def ensure_consent_for_booking(paziente_id: str, terapista_id: str) -> tuple[bool, str]:
    """Check if patient has a granted consent for this therapist.
    If not, create a pending consent + send email. Returns (has_valid_consent, consent_id).
    Called from booking_service before finalizing a booking.
    """
    active = await db.informed_consents.find_one({
        "paziente_id": paziente_id,
        "terapista_id": terapista_id,
        "status": "granted",
        "revoked_at": None,
    })
    if active:
        return True, str(active["_id"])

    # No active consent — check if there's a pending one already
    pending = await db.informed_consents.find_one({
        "paziente_id": paziente_id,
        "terapista_id": terapista_id,
        "status": "pending",
    })
    if pending:
        return False, str(pending["_id"])

    # Create a new pending consent + send email
    t, t_user = await _get_terapista_and_user(terapista_id)
    if not t:
        return False, ""
    p_user = await db.users.find_one({"_id": ObjectId(paziente_id)})
    if not p_user or not p_user.get("email"):
        return False, ""
    paziente_doc = await db.pazienti.find_one({"user_id": paziente_id})
    paziente_nome = paziente_doc.get("nome", "") if paziente_doc else p_user.get("nome", "")

    raw = secrets.token_urlsafe(32)
    consent_text = t.get("consenso_informato_testo") or DEFAULT_CONSENT_TEMPLATE.format(
        terapista_nome=t.get("nome", ""),
        terapista_cognome=t.get("cognome", ""),
    )
    now = datetime.now(timezone.utc)
    doc = {
        "paziente_id": paziente_id,
        "terapista_id": terapista_id,
        "terapista_user_id": t.get("user_id"),
        "consent_text": consent_text,
        "status": "pending",
        "token_hash": _digest(raw),
        "token_expires": now + timedelta(days=30),
        "created_at": now,
        "granted_at": None,
        "revoked_at": None,
        "ip": None,
        "user_agent": None,
    }
    r = await db.informed_consents.insert_one(doc)
    try:
        await _consent_email(
            paziente_email=p_user["email"],
            paziente_nome=paziente_nome,
            terapista_nome=t.get("nome", ""),
            terapista_cognome=t.get("cognome", ""),
            consent_id=str(r.inserted_id),
            raw_token=raw,
        )
    except Exception as e:
        logger.error(f"[CONSENT] email send failed: {e}")
    return False, str(r.inserted_id)


@router.get("/consenso-informato/{consent_id}")
async def get_consent(consent_id: str, token: str):
    """Public endpoint: fetch consent details for display in the magic-link page."""
    try:
        c = await db.informed_consents.find_one({"_id": ObjectId(consent_id)})
    except Exception:
        raise HTTPException(404, "Consenso non trovato")
    if not c:
        raise HTTPException(404, "Consenso non trovato")
    if _digest(token) != c.get("token_hash"):
        raise HTTPException(403, "Link non valido")
    exp = c.get("token_expires")
    if exp:
        exp = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp:
            raise HTTPException(410, "Link scaduto")
    t = await db.terapisti.find_one({"_id": ObjectId(c["terapista_id"])})
    p = await db.pazienti.find_one({"user_id": c["paziente_id"]})
    p_user = await db.users.find_one({"_id": ObjectId(c["paziente_id"])})
    return {
        "consent_id": consent_id,
        "status": c.get("status"),
        "consent_text": c.get("consent_text"),
        "granted_at": c.get("granted_at").isoformat() if c.get("granted_at") else None,
        "terapista": {
            "nome": t.get("nome", "") if t else "",
            "cognome": t.get("cognome", "") if t else "",
        },
        "paziente": {
            "nome": (p.get("nome") if p else None) or (p_user.get("nome") if p_user else ""),
            "cognome": (p.get("cognome") if p else None) or (p_user.get("cognome") if p_user else ""),
            "email": p_user.get("email") if p_user else "",
        },
    }


@router.post("/consenso-informato/{consent_id}/accept")
async def accept_consent(consent_id: str, body: dict, request: Request):
    """Public endpoint: patient clicks 'Presto il mio consenso' — records timestamp+IP."""
    token = body.get("token", "")
    try:
        c = await db.informed_consents.find_one({"_id": ObjectId(consent_id)})
    except Exception:
        raise HTTPException(404, "Consenso non trovato")
    if not c:
        raise HTTPException(404, "Consenso non trovato")
    if _digest(token) != c.get("token_hash"):
        raise HTTPException(403, "Link non valido")
    if c.get("status") == "granted":
        return {"message": "Consenso già prestato", "granted_at": c.get("granted_at").isoformat() if c.get("granted_at") else None}
    exp = c.get("token_expires")
    if exp:
        exp = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > exp:
            raise HTTPException(410, "Link scaduto")

    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "").split(",")[0].strip()
    ua = request.headers.get("user-agent", "")[:400]
    now = datetime.now(timezone.utc)
    await db.informed_consents.update_one(
        {"_id": ObjectId(consent_id)},
        {"$set": {
            "status": "granted",
            "granted_at": now,
            "ip": ip,
            "user_agent": ua,
            # Invalidate token immediately after acceptance (single-use)
            "token_hash": _digest(secrets.token_urlsafe(32)),
        }},
    )
    return {"message": "Consenso registrato", "granted_at": now.isoformat()}


@router.get("/consenso-informato/mia/{terapista_id}")
async def get_my_consent_status(terapista_id: str, user: dict = Depends(require_auth)):
    """Authenticated: current patient checks their consent status for a given therapist."""
    c = await db.informed_consents.find_one({
        "paziente_id": user["_id"],
        "terapista_id": terapista_id,
    })
    if not c:
        return {"status": "none"}
    return {
        "status": c.get("status"),
        "granted_at": c.get("granted_at").isoformat() if c.get("granted_at") else None,
        "consent_id": str(c["_id"]),
    }


@router.post("/consenso-informato/mia/{terapista_id}/revoca")
async def revoke_my_consent(terapista_id: str, user: dict = Depends(require_auth)):
    """Authenticated: patient revokes an existing consent."""
    r = await db.informed_consents.update_one(
        {"paziente_id": user["_id"], "terapista_id": terapista_id, "status": "granted"},
        {"$set": {"status": "revoked", "revoked_at": datetime.now(timezone.utc)}},
    )
    if r.modified_count == 0:
        raise HTTPException(404, "Nessun consenso attivo da revocare")
    return {"message": "Consenso revocato"}


@router.patch("/terapeuta/consenso-informato")
async def update_therapist_consent_text(body: dict, user: dict = Depends(require_auth)):
    """Authenticated therapist: customize their own informed consent text."""
    if user.get("role") != "terapeuta":
        raise HTTPException(403, "Solo terapisti")
    text = (body.get("consenso_informato_testo") or "").strip()
    if len(text) < 100:
        raise HTTPException(400, "Il testo del consenso deve essere di almeno 100 caratteri")
    await db.terapisti.update_one(
        {"user_id": user["_id"]},
        {"$set": {"consenso_informato_testo": text}},
    )
    return {"message": "Testo del consenso aggiornato"}
