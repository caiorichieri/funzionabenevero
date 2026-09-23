"""Load backend/.env so tests can access MONGO_URL, DB_NAME etc."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _env = Path(__file__).resolve().parent.parent / ".env"
    if _env.exists():
        load_dotenv(_env, override=False)
    # Also load frontend/.env for REACT_APP_BACKEND_URL
    _fe = Path(__file__).resolve().parent.parent.parent / "frontend" / ".env"
    if _fe.exists():
        load_dotenv(_fe, override=False)
except ImportError:
    pass
