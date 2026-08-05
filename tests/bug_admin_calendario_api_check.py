#!/usr/bin/env python3
"""Focused backend verification for admin calendar aggregation bug.

Checks that /api/admin/calendario includes both bookings-only days and draft
therapist availability days for August 2026 with enriched display fields.
"""
import json
import os
from pathlib import Path

import requests


ROOT = Path("/app")
REPORT = ROOT / "test_reports" / "admin_calendario_api_result.json"


def read_frontend_backend_url() -> str:
    env_path = ROOT / "frontend" / ".env"
    for line in env_path.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().strip('"')
    return os.environ.get("REACT_APP_BACKEND_URL", "http://localhost:8001")


def main() -> int:
    base = read_frontend_backend_url().rstrip("/")
    api = f"{base}/api"
    session = requests.Session()
    result = {"api_base": api, "checks": []}

    try:
        login = session.post(
            f"{api}/auth/login",
            json={"email": "admin@funzionabene.it", "password": "admin2026"},
            timeout=20,
        )
        result["login_status"] = login.status_code
        login.raise_for_status()
        result["login_user"] = login.json()

        resp = session.get(f"{api}/admin/calendario", params={"anno": 2026, "mese": 8}, timeout=20)
        result["calendar_status"] = resp.status_code
        resp.raise_for_status()
        payload = resp.json()
        result["days_returned"] = len(payload.get("days", []))

        day_map = {d["data"]: d for d in payload.get("days", [])}
        d806 = day_map.get("2026-08-06")
        d807 = day_map.get("2026-08-07")
        result["day_2026_08_06"] = d806
        result["day_2026_08_07"] = d807

        checks = [
            ("2026-08-06 present", d806 is not None),
            ("2026-08-06 has one booking", bool(d806 and d806.get("appuntamenti_count") == 1)),
            ("2026-08-06 is bookings-only", bool(d806 and d806.get("terapisti_count") == 0 and d806.get("slot_count") == 0)),
            (
                "2026-08-06 booking enriched",
                bool(
                    d806
                    and d806.get("appuntamenti")
                    and d806["appuntamenti"][0].get("ora") == "15:00"
                    and d806["appuntamenti"][0].get("paziente_nome") == "Luca Bianchi"
                    and d806["appuntamenti"][0].get("terapeuta_nome") == "Maria Rossi"
                    and d806["appuntamenti"][0].get("stato") == "confermato"
                ),
            ),
            ("2026-08-07 present", d807 is not None),
            ("2026-08-07 has one therapist", bool(d807 and d807.get("terapisti_count") == 1)),
            ("2026-08-07 has two slots", bool(d807 and d807.get("slot_count") == 2)),
            (
                "2026-08-07 draft therapist availability included",
                bool(
                    d807
                    and d807.get("terapisti")
                    and d807["terapisti"][0].get("nome") == "Maria Rossi"
                    and d807["terapisti"][0].get("bozza") is True
                    and d807["terapisti"][0].get("slots") == ["14:00", "15:00"]
                ),
            ),
        ]
        result["checks"] = [{"name": name, "passed": passed} for name, passed in checks]
        result["passed"] = all(passed for _, passed in checks)
    except Exception as exc:  # noqa: BLE001 - report exact test blocker/failure
        result["passed"] = False
        result["error"] = repr(exc)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())