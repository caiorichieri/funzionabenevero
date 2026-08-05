"""Shared dependencies: DB client, config constants, auth helpers.

Imported by server.py and all router modules to avoid duplication and
circular imports.
"""
import os
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import bcrypt
import jwt
import secrets as _secrets
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / ".env")

# ─── Config ───────────────────────────────────────────────────────────────────
JWT_SECRET = os.environ["JWT_SECRET"]
JWT_ALGORITHM = "HS256"
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY") or "sk_test_emergent"
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
PLATFORM_FEE_PERCENT = 30  # BIDOC retention (%)

# ─── MongoDB ──────────────────────────────────────────────────────────────────
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]


# ─── Helpers ──────────────────────────────────────────────────────────────────
def PyObjectId(v):
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, str) and ObjectId.is_valid(v):
        return v
    raise ValueError(f"ObjectId non valido: {v}")


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str, email: str, role: str) -> str:
    return jwt.encode(
        {"sub": user_id, "email": email, "role": role,
         "exp": datetime.now(timezone.utc) + timedelta(hours=8), "type": "access"},
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )


def create_refresh_token(user_id: str) -> str:
    return jwt.encode(
        {"sub": user_id, "exp": datetime.now(timezone.utc) + timedelta(days=7), "type": "refresh"},
        JWT_SECRET, algorithm=JWT_ALGORITHM,
    )


def generate_otp() -> str:
    return str(_secrets.randbelow(900000) + 100000)


def validate_codice_fiscale(cf: str) -> bool:
    cf = cf.upper().strip()
    if len(cf) != 16:
        return False
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    if not all(c in allowed for c in cf):
        return False
    odd = {'0': 1, '1': 0, '2': 5, '3': 7, '4': 9, '5': 13, '6': 15, '7': 17, '8': 19, '9': 21,
           'A': 1, 'B': 0, 'C': 5, 'D': 7, 'E': 9, 'F': 13, 'G': 15, 'H': 17, 'I': 19, 'J': 21,
           'K': 2, 'L': 4, 'M': 18, 'N': 20, 'O': 11, 'P': 3, 'Q': 6, 'R': 8, 'S': 12, 'T': 14,
           'U': 16, 'V': 10, 'W': 22, 'X': 25, 'Y': 24, 'Z': 23}
    even = {'0': 0, '1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
            'A': 0, 'B': 1, 'C': 2, 'D': 3, 'E': 4, 'F': 5, 'G': 6, 'H': 7, 'I': 8, 'J': 9,
            'K': 10, 'L': 11, 'M': 12, 'N': 13, 'O': 14, 'P': 15, 'Q': 16, 'R': 17, 'S': 18,
            'T': 19, 'U': 20, 'V': 21, 'W': 22, 'X': 23, 'Y': 24, 'Z': 25}
    total = sum(odd.get(c, 0) if i % 2 == 0 else even.get(c, 0) for i, c in enumerate(cf[:-1]))
    return cf[-1] == chr(ord('A') + (total % 26))


# ─── Auth dependency ──────────────────────────────────────────────────────────
async def find_user_by_id(uid) -> dict | None:
    """Safe user lookup by _id. Casts str/ObjectId inputs to ObjectId automatically.
    Returns None on invalid ID or missing user (never raises)."""
    if uid is None:
        return None
    if isinstance(uid, ObjectId):
        oid = uid
    else:
        try:
            oid = ObjectId(str(uid))
        except Exception:
            return None
    return await db.users.find_one({"_id": oid})


async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Non autenticato")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Token non valido")
        user = await find_user_by_id(payload["sub"])
        if not user:
            raise HTTPException(status_code=401, detail="Utente non trovato")
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Sessione scaduta")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token non valido")


async def require_admin(user: dict = Depends(get_current_user)):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accesso riservato agli amministratori")
    return user


async def require_auth(user: dict = Depends(get_current_user)):
    return user



# Required legal document kinds a therapist MUST sign (mirrors legal_signature.TERAPEUTA_REQUIRED_KINDS
# but declared here to avoid circular imports).
_TERAPEUTA_REQUIRED_KINDS = [
    "contratto_collaborazione",
    "privacy_terapeuti",
    "termini_pazienti",
    "cookie_policy",
]


async def require_therapist_signed(user: dict = Depends(get_current_user)):
    """Server-side gate: rejects therapists who haven't signed all mandatory legal documents.
    Admins and non-therapists pass through unchanged."""
    if user.get("role") != "terapeuta":
        return user
    # Check every required kind against its CURRENT version
    for kind in _TERAPEUTA_REQUIRED_KINDS:
        current = await db.contracts.find_one({"kind": kind, "is_current": True})
        if not current:
            continue
        signed = await db.contract_acceptances.find_one({
            "user_id": user["_id"],
            "contract_kind": kind,
            "contract_version": current.get("version"),
        })
        if not signed:
            raise HTTPException(
                status_code=403,
                detail="Devi firmare i documenti obbligatori prima di eseguire questa operazione. Vai su /terapeuta/firma-documenti",
            )
    return user
