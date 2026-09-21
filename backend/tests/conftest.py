"""Load backend/.env so tests can access MONGO_URL, DB_NAME etc."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    _env = Path(__file__).resolve().parent.parent / ".env"
    if _env.exists():
        load_dotenv(_env, override=False)
except ImportError:
    pass
