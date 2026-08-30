"""Auth router: register, OTP verify/resend, login, logout, me, password reset."""
import hashlib
import hmac as _hmac
import logging
import os
import secrets as _secrets
from datetime import datetime, timezone, timedelta

import bcrypt
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from deps import (
    db, get_current_user,
    hash_password, verify_password,
    create_access_token, create_refresh_token, generate_otp,
)
from models import RegisterInput, OTPInput, LoginInput, ForgotPasswordRequest, ResetPasswordRequest
from email_service import send_otp_email, send_password_reset_email, send_new_therapist_admin_alert

router = APIRouter()

# ─── Password reset internals (OWASP-compliant) ───────────────────────────────
RESET_TOKEN_MINUTES = 30
_DUMMY_HASH_FOR_TIMING = bcrypt.hashpw(b"timing-padding-unused", bcrypt.gensalt()).decode()


def _token_digest(raw: str) -> str:
    return hashlib.sha256(raw.encode("ascii")).hexdigest()


def _get_frontend_origin(request: Request) -> str:
    env_url = os.environ.get("FRONTEND_URL") or os.environ.get("REACT_APP_BACKEND_URL")
    if env_url:
        return env_url.rstrip("/")
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    return origin.rstrip("/")


# ─── Registration & OTP ───────────────────────────────────────────────────────
@router.post("/auth/register")
async def register(data: RegisterInput, response: Response):
    email = data.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email già registrata")
    if len(data.password) < 8:
        raise HTTPException(status_code=400, detail="Password deve avere almeno 8 caratteri")
    if data.role not in ["paziente", "terapeuta"]:
        raise HTTPException(status_code=400, detail="Ruolo non valido")
    if data.role == "terapeuta":
        # Direct therapist registration is disabled. New therapists must submit a
        # candidatura via POST /api/terapeuti/candidatura and be manually onboarded
        # by an admin (data-collection flow, not self-service signup).
        raise HTTPException(
            status_code=403,
            detail="La registrazione diretta dei terapeuti non è più disponibile. Compila il modulo di candidatura e verrai contattato dal nostro team.",
        )

    otp_code = generate_otp()
    otp_expires = datetime.now(timezone.utc) + timedelta(minutes=10)

    now = datetime.now(timezone.utc)
    consents_snapshot = {
        "privacy_accettata": bool(data.consenso_privacy),
        "privacy_accettata_at": now if data.consenso_privacy else None,
        "privacy_versione": data.consent_version_privacy,
        "termini_accettati": bool(data.consenso_termini),
        "termini_accettati_at": now if data.consenso_termini else None,
        "termini_versione": data.consent_version_termini,
        "dati_sanitari": bool(data.consenso_dati_sanitari),
        "dati_sanitari_at": now if data.consenso_dati_sanitari else None,
        "marketing": bool(data.consenso_marketing),
        "marketing_at": now if data.consenso_marketing else None,
        "ricerca": bool(data.consenso_ricerca),
        "ricerca_at": now if data.consenso_ricerca else None,
        "miglioramento": bool(data.consenso_miglioramento),
        "miglioramento_at": now if data.consenso_miglioramento else None,
    }

    # Paziente MUST accept mandatory consents
    if data.role == "paziente":
        if not (data.consenso_privacy and data.consenso_termini):
            raise HTTPException(status_code=400, detail="I consensi obbligatori (privacy e termini) sono richiesti per completare la registrazione")

    user_doc = {
        "email": email,
        "password_hash": hash_password(data.password),
        "nome": data.nome,
        "cognome": data.cognome,
        "role": data.role,
        "is_verified": False,
        "is_active": True,
        "otp_code": otp_code,
        "otp_expires": otp_expires,
        "consenso_privacy": data.consenso_privacy,
        "consents": consents_snapshot,
        "created_at": now,
    }
    if data.role == "terapeuta":
        user_doc["approval_status"] = "pending"

    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)

    # Record initial consents into the audit history (art. 7 GDPR accountability)
    consent_signup_map = {
        "privacy": bool(data.consenso_privacy),
        "termini": bool(data.consenso_termini),
        "dati_sanitari": bool(data.consenso_dati_sanitari),
        "marketing": bool(data.consenso_marketing),
        "ricerca": bool(data.consenso_ricerca),
        "miglioramento": bool(data.consenso_miglioramento),
    }
    consent_events = [{
        "user_id": user_id,
        "consent_type": ctype,
        "action": "grant" if granted else "not_granted_at_signup",
        "timestamp": now,
        "ip_anonymized": "",
        "source": "signup",
    } for ctype, granted in consent_signup_map.items()]
    if consent_events:
        await db.consent_history.insert_many(consent_events)

    if data.role == "paziente":
        await db.pazienti.insert_one({
            "user_id": user_id, "nome": data.nome, "cognome": data.cognome,
            "created_at": datetime.now(timezone.utc),
        })
    else:
        await db.terapisti.insert_one({
            "user_id": user_id, "nome": data.nome, "cognome": data.cognome,
            "autocertificazione_firmata": False,
            "created_at": datetime.now(timezone.utc),
        })
        # Notify admin(s) of new therapist awaiting approval
        try:
            await send_new_therapist_admin_alert({
                "nome": data.nome,
                "cognome": data.cognome,
                "email": email,
                "created_at": now.strftime("%d/%m/%Y %H:%M"),
            })
        except Exception as e:
            logging.error(f"[EMAIL] admin new-therapist alert failed: {e}")

    logging.info(f"[OTP] {email}: {otp_code}")
    email_sent = await send_otp_email(email, otp_code, data.nome)
    response_body = {"message": "Registrazione completata. Controlla la tua email per il codice OTP."}
    expose_dev = os.environ.get("EXPOSE_OTP_DEV", "false").lower() == "true"
    if not email_sent or expose_dev:
        response_body["otp_dev"] = otp_code
    return response_body


@router.post("/auth/verify-otp")
async def verify_otp(data: OTPInput, response: Response):
    email = data.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    if user.get("is_verified"):
        raise HTTPException(status_code=400, detail="Account già verificato")
    otp_expires = user.get("otp_expires")
    if otp_expires:
        if isinstance(otp_expires, str):
            otp_expires = datetime.fromisoformat(otp_expires)
        if otp_expires.tzinfo is None:
            otp_expires = otp_expires.replace(tzinfo=timezone.utc)
    if not otp_expires or datetime.now(timezone.utc) > otp_expires:
        raise HTTPException(status_code=400, detail="Codice OTP scaduto")
    if user.get("otp_code") != data.otp_code:
        raise HTTPException(status_code=400, detail="Codice OTP non valido")

    await db.users.update_one({"_id": user["_id"]}, {"$set": {"is_verified": True, "otp_code": None}})
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email, user["role"])
    refresh_token = create_refresh_token(user_id)
    response.set_cookie("access_token", access_token, httponly=True, samesite="none", secure=True, max_age=28800, path="/")
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="none", secure=True, max_age=604800, path="/")
    return {"message": "Account verificato con successo", "role": user["role"], "nome": user["nome"]}


@router.post("/auth/resend-otp")
async def resend_otp(body: dict):
    email = body.get("email", "").lower().strip()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    otp_code = generate_otp()
    otp_expires = datetime.now(timezone.utc) + timedelta(minutes=10)
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"otp_code": otp_code, "otp_expires": otp_expires}})
    logging.info(f"[OTP Resend] {email}: {otp_code}")
    email_sent = await send_otp_email(email, otp_code, user.get("nome", ""))
    response_body = {"message": "Nuovo codice OTP inviato"}
    expose_dev = os.environ.get("EXPOSE_OTP_DEV", "false").lower() == "true"
    if not email_sent or expose_dev:
        response_body["otp_dev"] = otp_code
    return response_body


@router.post("/auth/login")
async def login(data: LoginInput, response: Response):
    email = data.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(data.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Credenziali non valide")
    if not user.get("is_verified") and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Account non verificato. Controlla la tua email per il codice OTP.")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account disattivato")
    # Therapists must be explicitly approved by an admin before they can access the platform.
    # Legacy `approval_status` value is "approvato" (see admin approve endpoint); newer flow may
    # use "verified" — accept either. Therapists in onboarding ("in_onboarding" / "pronto_per_review")
    # are also allowed to login so they can complete their profile.
    if user.get("role") == "terapeuta" and user.get("approval_status") not in (
        "approvato", "verified", "in_onboarding", "pronto_per_review"
    ):
        raise HTTPException(
            status_code=403,
            detail="Il tuo profilo è in fase di valutazione. Ti contatteremo dopo la verifica.",
        )

    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email, user["role"])
    refresh_token = create_refresh_token(user_id)
    response.set_cookie("access_token", access_token, httponly=True, samesite="none", secure=True, max_age=28800, path="/")
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="none", secure=True, max_age=604800, path="/")
    return {"_id": user_id, "email": email, "nome": user["nome"], "cognome": user["cognome"], "role": user["role"]}


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logout effettuato con successo"}


@router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user


# ─── Password Reset (OWASP Cheat Sheet compliant) ─────────────────────────────
@router.post("/auth/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    email = body.email.strip().lower()
    user = await db.users.find_one({"email": email}, {"_id": 1, "email": 1, "nome": 1})

    if user is None:
        # Timing equalization
        bcrypt.checkpw(b"timing-padding", _DUMMY_HASH_FOR_TIMING.encode())
    else:
        raw_token = _secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        await db.password_reset_tokens.delete_many({"user_id": user["_id"], "used_at": None})
        await db.password_reset_tokens.insert_one({
            "user_id": user["_id"],
            "token_hash": _token_digest(raw_token),
            "expires_at": now + timedelta(minutes=RESET_TOKEN_MINUTES),
            "used_at": None,
            "created_at": now,
        })
        frontend = _get_frontend_origin(request)
        reset_url = f"{frontend}/reset-password?token={raw_token}"
        try:
            await send_password_reset_email(email, reset_url, user.get("nome", ""))
        except Exception as e:
            logging.error(f"[RESET] email send exception: {e}")

    return {"message": "Se un account esiste con questa email, riceverai un link per il reset."}


@router.post("/auth/reset-password")
async def reset_password(body: ResetPasswordRequest):
    generic_error = HTTPException(400, "Il link di reset non è valido o è scaduto.")
    digest = _token_digest(body.token)
    now = datetime.now(timezone.utc)

    token_doc = await db.password_reset_tokens.find_one_and_update(
        {"token_hash": digest, "used_at": None, "expires_at": {"$gt": now}},
        {"$set": {"used_at": now}},
        projection={"user_id": 1, "token_hash": 1},
    )
    if token_doc is None:
        raise generic_error
    if not _hmac.compare_digest(token_doc["token_hash"], digest):
        raise generic_error

    new_hash = hash_password(body.new_password)
    result = await db.users.update_one(
        {"_id": token_doc["user_id"]},
        {"$set": {"password_hash": new_hash, "password_changed_at": now}},
    )
    if result.modified_count != 1:
        logging.error("[RESET] consumed token but user update failed")
        raise HTTPException(500, "Impossibile completare il reset.")

    return {"message": "Password reimpostata con successo. Ora puoi accedere."}



# ─── Therapist activation (from admin-issued invitation link) ─────────────────
@router.get("/auth/attivazione-terapeuta/verifica")
async def verifica_token_attivazione(token: str):
    """Public: check if an activation token is still valid, before showing the form.
    Returns basic user info so the UI can greet the therapist by name.
    """
    digest = _token_digest(token)
    now = datetime.now(timezone.utc)
    doc = await db.password_reset_tokens.find_one({
        "token_hash": digest,
        "used_at": None,
        "expires_at": {"$gt": now},
        "purpose": "therapist_activation",
    })
    if not doc:
        raise HTTPException(400, "Il link di attivazione non è valido o è scaduto.")
    user = await db.users.find_one(
        {"_id": ObjectId(doc["user_id"])},
        {"email": 1, "nome": 1, "cognome": 1},
    )
    if not user:
        raise HTTPException(400, "Il link di attivazione non è valido o è scaduto.")
    return {"email": user.get("email"), "nome": user.get("nome"), "cognome": user.get("cognome")}


@router.post("/auth/attivazione-terapeuta/completa")
async def completa_attivazione_terapeuta(body: ResetPasswordRequest, response: Response):
    """Public: therapist sets their initial password using the admin-issued token.
    Also activates the user account (is_active=true) and logs them in immediately."""
    generic_error = HTTPException(400, "Il link di attivazione non è valido o è scaduto.")
    digest = _token_digest(body.token)
    now = datetime.now(timezone.utc)

    token_doc = await db.password_reset_tokens.find_one_and_update(
        {
            "token_hash": digest,
            "used_at": None,
            "expires_at": {"$gt": now},
            "purpose": "therapist_activation",
        },
        {"$set": {"used_at": now}},
        projection={"user_id": 1, "token_hash": 1},
    )
    if token_doc is None:
        raise generic_error
    if not _hmac.compare_digest(token_doc["token_hash"], digest):
        raise generic_error

    new_hash = hash_password(body.new_password)
    user = await db.users.find_one({"_id": ObjectId(token_doc["user_id"])})
    if not user:
        raise generic_error
    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {
            "password_hash": new_hash,
            "password_changed_at": now,
            "is_active": True,
            "is_verified": True,
        }},
    )

    # Auto-login: set the same cookies the login endpoint sets
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, user["email"], "terapeuta")
    refresh_token = create_refresh_token(user_id)
    response.set_cookie("access_token", access_token, httponly=True, samesite="none", secure=True, max_age=28800, path="/")
    response.set_cookie("refresh_token", refresh_token, httponly=True, samesite="none", secure=True, max_age=604800, path="/")
    return {
        "message": "Account attivato con successo.",
        "_id": user_id,
        "email": user["email"],
        "nome": user.get("nome", ""),
        "cognome": user.get("cognome", ""),
        "role": "terapeuta",
    }
