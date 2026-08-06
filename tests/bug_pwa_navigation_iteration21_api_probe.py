"""
Focused API probe for iteration 21 Luca standalone-PWA therapist navigation bug.

This confirms the backend data that the UI should use: Luca auth, existing
appointments, linked therapist (Maria Rossi), and Maria's public profile/slots.
"""

import json
import os
from datetime import datetime, timezone

import requests


BASE_URL = os.environ.get("PREVIEW_URL", "https://portugues-writer-2.preview.emergentagent.com").rstrip("/")
API = f"{BASE_URL}/api"
THERAPIST_ID = "69e5c83ca585e313092bd593"


def dump(label, data):
    print(f"\n## {label}")
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def main():
    s = requests.Session()
    login = s.post(
        f"{API}/auth/login",
        json={"email": "demo.paziente@funzionabene.it", "password": "paziente2026"},
        timeout=20,
    )
    print("login", login.status_code)
    login.raise_for_status()
    dump("login_user", login.json())

    for path in ["/auth/me", "/appuntamenti", "/paziente/mio-terapeuta"]:
        resp = s.get(f"{API}{path}", timeout=20)
        print(path, resp.status_code)
        resp.raise_for_status()
        data = resp.json()
        if path == "/appuntamenti":
            now = datetime.now(timezone.utc)
            appts = data if isinstance(data, list) else []
            data = [
                {
                    "_id": a.get("_id"),
                    "terapeuta_id": a.get("terapeuta_id"),
                    "terapeuta_nome": a.get("terapeuta_nome"),
                    "data_ora": a.get("data_ora"),
                    "stato": a.get("stato"),
                    "future_or_today": str(a.get("data_ora", "")) >= now.isoformat(),
                }
                for a in appts[:10]
            ]
        dump(path, data)

    for path in [f"/public/terapisti/{THERAPIST_ID}", f"/terapisti/{THERAPIST_ID}/slots?settimane=2"]:
        resp = s.get(f"{API}{path}", timeout=20)
        print(path, resp.status_code)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict) and "slots" in data:
            slots = data.get("slots", [])
            data = {
                "slots_count": len(slots),
                "available_count": len([slot for slot in slots if slot.get("disponibile")]),
                "slots_sample": slots[:5],
            }
        dump(path, data)


if __name__ == "__main__":
    main()