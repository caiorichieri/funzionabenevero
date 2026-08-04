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
from email_service import send_otp_email, send_password_reset_email

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

    otp_code = generate_otp()
    otp_expires = datetime.now(timezone.utc) + timedelta(minutes=10)

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
        "created_at": datetime.now(timezone.utc),
    }
    if data.role == "terapeuta":
        user_doc["approval_status"] = "pending"

    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)

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
