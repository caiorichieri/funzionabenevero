"""Fire ALL patient-facing email templates against a single test address so we
can visually confirm each one arrives with correct subject, layout, attachments
and reply-to. Intended for post-deploy sanity checks — NOT for tests suite.

Usage:
    cd /app/backend && set -a && source .env && set +a && python -m scripts.e2e_email_smoke caiorichieri@gmail.com
"""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta


# In-memory fake fattura + ctx used by all templates
def _fake_ctx(paziente_email: str) -> dict:
    when = (datetime.now(timezone.utc) + timedelta(days=1, hours=2)).isoformat()
    return {
        "paziente_email": paziente_email,
        "paziente_nome": "Caio",
        "paziente_cognome": "Ricchieri",
        "terapista_email": paziente_email,  # send therapist copies to same inbox for review
        "terapista_nome": "Laura",
        "terapista_cognome": "De Clara",
        "terapista_id": "6a883255ad52b95ec7a048b1",
        "app_id": "6a883255ad52b95ec7a048b1",
        "data_ora": when,
        "durata_minuti": 50,
        "tipologia": "psicoterapia",
        "modalita": "video",
        "prezzo": 80,
    }


def _fake_fattura() -> dict:
    return {
        "numero": "FZ-2026-TEST",
        "importo_totale": 80.00,
        "data": datetime.now(timezone.utc).isoformat()[:10],
        "causale": "Prestazione sanitaria — psicoterapia individuale (test smoke)",
    }


async def main(to_email: str) -> None:
    from email_service import (
        send_otp_email,
        send_booking_confirmation_email,
        send_reminder_email,
        send_reschedule_notification_email,
        send_fattura_paziente_email,
        send_signature_receipt_email,
        send_no_show_paziente_email,
        send_no_show_terapeuta_email,
        send_terapeuta_absent_paziente_email,
        send_terapeuta_absent_terapeuta_email,
        send_no_show_admin_alert,
        send_password_reset_email,
    )

    ctx = _fake_ctx(to_email)
    fattura = _fake_fattura()
    # Small "fake PDF" bytes — real MIME arrival is what we're testing
    fake_pdf = b"%PDF-1.4\n%TestSmoke\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"

    checks = [
        ("01 OTP email",                    send_otp_email(to_email, "123456", "Caio")),
        ("02 Booking confirmation",          send_booking_confirmation_email(ctx)),
        ("03 Reminder 24h",                  send_reminder_email(ctx, "1-giorno")),
        ("04 Reminder 1h",                   send_reminder_email(ctx, "1-ora")),
        ("05 Reminder 15min (magic link)",   send_reminder_email(ctx, "15-min")),
        ("06 Reschedule notification",       send_reschedule_notification_email(
            to_email=to_email, to_nome="Caio", paziente_nome="Caio Ricchieri",
            old_datetime_iso=ctx["data_ora"],
            new_datetime_iso=(datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            role="paziente",
        )),
        ("07 Fattura sanitaria (BRANDED)",   send_fattura_paziente_email(
            paziente_email=to_email, paziente_nome="Caio",
            terapeuta_cognome="De Clara", data_seduta_iso=ctx["data_ora"],
            fattura=fattura, pdf_bytes=fake_pdf,
        )),
        ("08 Nota di credito (signature-receipt template)", send_signature_receipt_email(
            email=to_email, nome="Caio",
            doc_titles=[
                "Nota di Credito FZ-2026-NC-TEST — storno fattura FZ-2026-TEST",
                "Importo stornato: € 80,00",
                "Conservala insieme alla fattura originale.",
            ],
            pdf_bytes=fake_pdf,
        )),
        ("09 No-show paziente (paziente copy)", send_no_show_paziente_email(ctx)),
        ("10 No-show paziente (terapeuta copy)", send_no_show_terapeuta_email(ctx)),
        ("11 Terapeuta absent (paziente copy)", send_terapeuta_absent_paziente_email(ctx)),
        ("12 Terapeuta absent (terapeuta copy)", send_terapeuta_absent_terapeuta_email(ctx)),
        ("13 No-show admin alert (hr@)",     send_no_show_admin_alert(to_email, "no_show_paziente", ctx)),
        ("14 Password reset",                send_password_reset_email(to_email, "https://funzionabene.it/reset?token=TEST", "Caio")),
    ]

    print(f"\n╔══ SMOKE EMAIL RUN → {to_email} ══════════════════════════════════════╗\n")
    results = []
    for label, coro in checks:
        try:
            ret = await coro
            # send_fattura_paziente_email returns (ok, err); the others return bool
            if isinstance(ret, tuple):
                ok, err = ret
            else:
                ok, err = bool(ret), ""
            status = "✓ OK  " if ok else f"✗ FAIL"
            print(f"  {status}  {label}" + (f"  — {err}" if err else ""))
            results.append((label, ok))
        except Exception as e:
            print(f"  ✗ EXC  {label}  — {e!r}")
            results.append((label, False))

    ok_count = sum(1 for _, ok in results if ok)
    print(f"\n╚══ {ok_count}/{len(results)} sent to {to_email}. Check the inbox ══════════╝\n")


if __name__ == "__main__":
    to = sys.argv[1] if len(sys.argv) > 1 else "caiorichieri@gmail.com"
    # Make sure imports resolve
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    asyncio.run(main(to))
