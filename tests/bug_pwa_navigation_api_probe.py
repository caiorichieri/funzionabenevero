import json
import os
from datetime import datetime, timezone

import requests


BASE_URL = os.environ.get("PREVIEW_URL", "https://portugues-writer-2.preview.emergentagent.com")
API = f"{BASE_URL.rstrip('/')}/api"


def dump(label, data):
    print(f"\n## {label}")
    print(json.dumps(data, ensure_ascii=False, indent=2, default=str))


def main():
    s = requests.Session()
    r = s.post(f"{API}/auth/login", json={"email": "demo.paziente@funzionabene.it", "password": "paziente2026"}, timeout=20)
    print("login", r.status_code)
    r.raise_for_status()
    dump("me", r.json())

    for path in ["/auth/me", "/appuntamenti", "/paziente/mio-terapeuta"]:
        resp = s.get(f"{API}{path}", timeout=20)
        print(path, resp.status_code)
        resp.raise_for_status()
        data = resp.json()
        if path == "/appuntamenti":
            now = datetime.now(timezone.utc)
            appts = data if isinstance(data, list) else []
            compact = [
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
            dump(path, compact)
        else:
            dump(path, data)

    tid = "69e5c83ca585e313092bd593"
    for path in [f"/public/terapisti/{tid}", f"/terapisti/{tid}/slots?settimane=2"]:
        resp = s.get(f"{API}{path}", timeout=20)
        print(path, resp.status_code)
        try:
            data = resp.json()
        except Exception:
            data = resp.text[:500]
        if isinstance(data, dict) and "slots" in data:
            data = {**data, "slots_sample": data.get("slots", [])[:3], "slots_count": len(data.get("slots", []))}
            data.pop("slots", None)
        dump(path, data)


if __name__ == "__main__":
    main()