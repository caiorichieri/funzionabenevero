"""Email service — Resend integration for transactional emails (OTP, booking confirmations)."""
import os
import asyncio
import logging

import resend

logger = logging.getLogger(__name__)

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "onboarding@resend.dev")
SEND_EMAILS = os.environ.get("SEND_EMAILS", "false").lower() == "true"

if RESEND_API_KEY and RESEND_API_KEY != "placeholder_resend_key":
    resend.api_key = RESEND_API_KEY


def _otp_template(otp_code: str, nome: str = "") -> str:
    saluto = f"Ciao {nome}" if nome else "Ciao"
    return f"""<!DOCTYPE html>
<html lang="it">
<head><meta charset="UTF-8"><title>Verifica email - FunzionaBene</title></head>
<body style="margin:0;padding:0;background-color:#0A0A0A;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;color:#F4F1ED;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color:#0A0A0A;padding:40px 20px;">
    <tr><td align="center">
      <table role="presentation" width="520" cellspacing="0" cellpadding="0" border="0" style="max-width:520px;background-color:#111111;border:1px solid rgba(255,255,255,0.08);border-radius:20px;overflow:hidden;">
        <tr><td style="padding:40px 40px 20px 40px;text-align:center;">
          <div style="display:inline-block;width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,#D4A017 0%,#6B8FA3 100%);line-height:56px;color:#111111;font-weight:bold;font-size:18px;">FB</div>
          <div style="margin-top:16px;font-family:Georgia,serif;font-size:22px;color:#F4F1ED;letter-spacing:-0.3px;">funzionabene</div>
          <div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#6B8FA3;margin-top:4px;">psicologi e sessuologi</div>
        </td></tr>
        <tr><td style="padding:20px 40px 0 40px;">
          <h1 style="font-family:Georgia,serif;font-size:28px;font-weight:500;color:#F4F1ED;margin:0 0 16px 0;line-height:1.3;">Verifica la tua email</h1>
          <p style="color:rgba(230,226,216,0.7);font-size:15px;line-height:1.6;margin:0 0 24px 0;">
            {saluto}, grazie per esserti registrato su <strong style="color:#F4F1ED;">funzionabene.it</strong>.<br>
            Inserisci questo codice nella pagina di verifica per completare la registrazione:
          </p>
        </td></tr>
        <tr><td style="padding:0 40px;">
          <div style="background-color:rgba(212,160,23,0.08);border:1px solid rgba(212,160,23,0.3);border-radius:14px;padding:24px;text-align:center;">
            <div style="font-family:'Courier New',monospace;font-size:36px;font-weight:bold;letter-spacing:12px;color:#D4A017;">{otp_code}</div>
            <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:rgba(230,226,216,0.5);margin-top:10px;">Codice valido per 10 minuti</div>
          </div>
        </td></tr>
        <tr><td style="padding:32px 40px 20px 40px;">
          <p style="color:rgba(230,226,216,0.5);font-size:13px;line-height:1.6;margin:0;">
            Se non hai richiesto questa email, puoi ignorarla. Il codice scadrà automaticamente.
          </p>
        </td></tr>
        <tr><td style="padding:20px 40px 40px 40px;border-top:1px solid rgba(255,255,255,0.08);">
          <p style="color:rgba(230,226,216,0.4);font-size:11px;line-height:1.6;margin:0;text-align:center;">
            © FunzionaBene — Clinica di Psicologia e Sessuologia<br>
            Trattamento dati ai sensi del GDPR (Reg. UE 2016/679)
          </p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


async def send_otp_email(email: str, otp_code: str, nome: str = "") -> bool:
    """Send OTP verification email. Returns True on success, False on failure."""
    if not SEND_EMAILS:
        logger.info(f"[EMAIL DISABLED] OTP for {email}: {otp_code}")
        return False
    if not RESEND_API_KEY or RESEND_API_KEY == "placeholder_resend_key":
        logger.warning(f"[EMAIL] No Resend API key configured, skipping send to {email}")
        return False

    params = {
        "from": f"FunzionaBene <{SENDER_EMAIL}>",
        "to": [email],
        "subject": f"Il tuo codice di verifica: {otp_code}",
        "html": _otp_template(otp_code, nome),
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL SENT] OTP to {email} (id={result.get('id') if isinstance(result, dict) else result})")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] Failed to send OTP to {email}: {e}")
        return False


def _format_data_ora_it(iso: str) -> str:
    from datetime import datetime as _dt
    GIORNI = ["Lunedì","Martedì","Mercoledì","Giovedì","Venerdì","Sabato","Domenica"]
    MESI = ["gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]
    try:
        d = _dt.fromisoformat(iso.replace("Z", "+00:00"))
        g = GIORNI[d.weekday()]
        return f"{g} {d.day} {MESI[d.month-1]} {d.year} · {d.hour:02d}:{d.minute:02d}"
    except Exception:
        return iso


def _booking_template(ctx: dict, recipient: str) -> str:
    """recipient = 'paziente' or 'terapista'."""
    dt_fmt = _format_data_ora_it(ctx["data_ora"])
    saluto = f"Ciao {ctx['paziente_nome']}" if recipient == "paziente" else f"Gentile Dr. {ctx['terapista_cognome']}"
    descrizione = (
        f"La tua seduta con <strong>Dr. {ctx['terapista_nome']} {ctx['terapista_cognome']}</strong> è stata confermata."
        if recipient == "paziente"
        else f"Una nuova prenotazione da <strong>{ctx['paziente_nome']} {ctx['paziente_cognome']}</strong>."
    )
    return f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0A0A0A;font-family:'Helvetica Neue',Arial,sans-serif;color:#F4F1ED;">
<table width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#0A0A0A;padding:40px 20px;">
<tr><td align="center">
<table width="560" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;background:#111;border:1px solid rgba(255,255,255,0.08);border-radius:20px;overflow:hidden;">
<tr><td style="padding:40px 40px 20px;text-align:center;">
  <div style="font-family:Georgia,serif;font-size:26px;color:#F4F1ED;">funzionabene</div>
  <div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#6B8FA3;margin-top:4px;">psicologi e sessuologi</div>
</td></tr>
<tr><td style="padding:10px 40px 0;">
  <h1 style="font-family:Georgia,serif;font-size:28px;font-weight:500;margin:0 0 16px;color:#F4F1ED;">Prenotazione confermata</h1>
  <p style="color:rgba(230,226,216,0.75);font-size:15px;line-height:1.6;margin:0 0 24px;">{saluto},<br>{descrizione}</p>
</td></tr>
<tr><td style="padding:0 40px;">
  <table width="100%" style="background:rgba(212,160,23,0.06);border:1px solid rgba(212,160,23,0.25);border-radius:14px;padding:20px;">
    <tr><td style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#6B8FA3;padding-bottom:8px;">Quando</td></tr>
    <tr><td style="font-family:Georgia,serif;font-size:20px;color:#D4A017;padding-bottom:14px;">{dt_fmt}</td></tr>
    <tr><td style="font-size:13px;color:rgba(230,226,216,0.6);border-top:1px solid rgba(255,255,255,0.08);padding-top:12px;">
      Durata: {ctx['durata_minuti']} minuti · Modalità: Online<br>
      Totale: €{ctx.get('prezzo', 90)}
    </td></tr>
  </table>
</td></tr>
<tr><td style="padding:28px 40px 20px;">
  <p style="font-size:13px;color:rgba(230,226,216,0.6);line-height:1.6;margin:0 0 16px;">
    Il link per entrare nella stanza video sarà disponibile 15 minuti prima della seduta nella tua area personale.
    Riceverai un promemoria 1 giorno prima.
  </p>
  <p style="font-size:12px;color:rgba(230,226,216,0.4);line-height:1.6;margin:0;">
    Non puoi partecipare? {"<a href='" + ctx['reschedule_url'] + "' style='color:#6B8FA3;text-decoration:underline;'>Riprogramma qui</a> · " if ctx.get('reschedule_url') and recipient == 'paziente' else ""}Per un rimborso scrivi a <a href="mailto:assistenza@funzionabene.it" style="color:#6B8FA3;text-decoration:underline;">assistenza@funzionabene.it</a>.
  </p>
</td></tr>
<tr><td style="padding:20px 40px 40px;border-top:1px solid rgba(255,255,255,0.08);text-align:center;">
  <p style="color:rgba(230,226,216,0.4);font-size:11px;line-height:1.6;margin:0;">© FunzionaBene — Clinica di Psicologia e Sessuologia<br>Trattamento dati ai sensi del GDPR</p>
</td></tr>
</table></td></tr></table></body></html>"""


def _reminder_template(ctx: dict, when: str) -> str:
    """when = '1-giorno' | '1-ora' | '15-min'."""
    dt_fmt = _format_data_ora_it(ctx["data_ora"])
    if when == "15-min":
        titolo = "La tua seduta inizia tra 15 minuti"
        sottotitolo = "Clicca il pulsante qui sotto per entrare direttamente nella stanza."
    elif when == "1-ora":
        titolo = "La tua seduta è tra un'ora"
        sottotitolo = "Il link per entrare arriverà 15 minuti prima dell'inizio via email — sarà anche disponibile nella tua area personale."
    else:  # 1-giorno
        titolo = "La tua seduta è domani"
        sottotitolo = "Ti aspettiamo. Controlla i dettagli qui sotto."

    # Direct-join button (only for 15-min reminder with magic link)
    join_button_html = ""
    if when == "15-min" and ctx.get("videocall_url"):
        join_button_html = f"""<tr><td style="padding:24px 40px 0;text-align:center;">
    <a href="{ctx['videocall_url']}" style="display:inline-block;background:#D4A017;color:#0A0A0A;font-weight:600;text-decoration:none;padding:16px 40px;border-radius:12px;font-size:15px;letter-spacing:0.5px;">Entra nella stanza video →</a>
    <p style="font-size:11px;color:rgba(230,226,216,0.4);margin:12px 0 0;">Il link è personale e valido solo per te fino a 15 minuti dopo l'inizio della sessione.</p>
</td></tr>"""

    reschedule_html = ""
    if ctx.get("reschedule_url") and when != "15-min":
        reschedule_html = f"""<p style="font-size:12px;color:rgba(230,226,216,0.5);line-height:1.6;margin:16px 0 0;text-align:center;">
      Non puoi partecipare? <a href="{ctx['reschedule_url']}" style="color:#6B8FA3;text-decoration:underline;">Riprogramma qui</a> · Per un rimborso scrivi a <a href="mailto:assistenza@funzionabene.it" style="color:#6B8FA3;text-decoration:underline;">assistenza@funzionabene.it</a>
    </p>"""
    return f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0A0A0A;font-family:'Helvetica Neue',Arial,sans-serif;color:#F4F1ED;">
<table width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#0A0A0A;padding:40px 20px;">
<tr><td align="center">
<table width="560" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;background:#111;border:1px solid rgba(255,255,255,0.08);border-radius:20px;overflow:hidden;">
<tr><td style="padding:40px 40px 20px;text-align:center;">
  <div style="font-family:Georgia,serif;font-size:26px;color:#F4F1ED;">funzionabene</div>
  <div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#6B8FA3;margin-top:4px;">promemoria seduta</div>
</td></tr>
<tr><td style="padding:10px 40px 0;">
  <h1 style="font-family:Georgia,serif;font-size:30px;font-weight:500;margin:0 0 10px;color:#D4A017;">{titolo}</h1>
  <p style="color:rgba(230,226,216,0.75);font-size:14px;line-height:1.6;margin:0 0 24px;">{sottotitolo}</p>
</td></tr>
<tr><td style="padding:0 40px;">
  <table width="100%" style="background:rgba(212,160,23,0.06);border:1px solid rgba(212,160,23,0.25);border-radius:14px;padding:20px;">
    <tr><td style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#6B8FA3;padding-bottom:8px;">Appuntamento</td></tr>
    <tr><td style="font-family:Georgia,serif;font-size:18px;color:#D4A017;padding-bottom:10px;">{dt_fmt}</td></tr>
    <tr><td style="font-size:13px;color:rgba(230,226,216,0.7);padding-bottom:8px;">
      Con Dr. {ctx['terapista_nome']} {ctx['terapista_cognome']}
    </td></tr>
  </table>
  {reschedule_html}
</td></tr>
{join_button_html}
<tr><td style="padding:28px 40px 40px;border-top:1px solid rgba(255,255,255,0.08);text-align:center;margin-top:20px;">
  <p style="color:rgba(230,226,216,0.4);font-size:11px;margin:0;">© FunzionaBene · Psicologi e Sessuologi</p>
</td></tr>
</table></td></tr></table></body></html>"""


async def _send_raw(params: dict) -> bool:
    if not SEND_EMAILS or not RESEND_API_KEY or RESEND_API_KEY == "placeholder_resend_key":
        logger.info(f"[EMAIL DISABLED] {params.get('subject')} to {params.get('to')}")
        return False
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL SENT] {params.get('subject')} to {params.get('to')} (id={result.get('id') if isinstance(result, dict) else result})")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] {params.get('subject')} to {params.get('to')}: {e}")
        return False


async def send_booking_confirmation_email(ctx: dict) -> bool:
    """Send booking confirmation to both paziente and terapista."""
    results = []
    # Paziente
    if ctx.get("paziente_email"):
        results.append(await _send_raw({
            "from": f"FunzionaBene <{SENDER_EMAIL}>",
            "to": [ctx["paziente_email"]],
            "subject": "Prenotazione confermata - FunzionaBene",
            "html": _booking_template(ctx, "paziente"),
        }))
    # Terapista
    if ctx.get("terapista_email"):
        results.append(await _send_raw({
            "from": f"FunzionaBene <{SENDER_EMAIL}>",
            "to": [ctx["terapista_email"]],
            "subject": f"Nuova prenotazione: {ctx.get('paziente_nome')} {ctx.get('paziente_cognome')}",
            "html": _booking_template(ctx, "terapista"),
        }))
    return any(results)


async def send_reminder_email(ctx: dict, when: str) -> bool:
    """Send reminder email to paziente. when = '1-giorno' | '1-ora' | '15-min'."""
    if not ctx.get("paziente_email"):
        return False
    subjects = {
        "1-giorno": "Promemoria: la tua seduta è domani",
        "1-ora": "La tua seduta è tra un'ora",
        "15-min": "🎥 La tua seduta inizia tra 15 minuti — entra qui",
    }
    subject = subjects.get(when, "Promemoria seduta")
    return await _send_raw({
        "from": f"FunzionaBene <{SENDER_EMAIL}>",
        "to": [ctx["paziente_email"]],
        "subject": subject,
        "html": _reminder_template(ctx, when),
    })



async def send_password_reset_email(email: str, reset_url: str, nome: str = "") -> bool:
    """Send password reset link. Returns True on success. Never leaks user existence in logs."""
    if not SEND_EMAILS:
        logger.info(f"[EMAIL DISABLED] Password reset link ready for {email}")
        return False
    if not RESEND_API_KEY or RESEND_API_KEY == "placeholder_resend_key":
        logger.warning("[EMAIL] No Resend API key configured, skipping password reset send")
        return False

    ciao = f"Ciao {nome}," if nome else "Ciao,"
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"/></head>
<body style="margin:0;padding:0;background:#F4EAA8;font-family:-apple-system,Helvetica,Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F4EAA8;padding:40px 20px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:24px;padding:48px 40px;box-shadow:0 20px 40px rgba(0,0,0,0.08);">
        <tr><td>
          <div style="text-align:center;margin-bottom:32px;">
            <div style="font-family:'Georgia',serif;font-size:36px;color:#0A0A0A;font-weight:700;">FunzionaBene</div>
          </div>
          <h1 style="color:#0A0A0A;font-family:'Georgia',serif;font-size:28px;margin:0 0 16px;">Reimposta la tua password</h1>
          <p style="color:#0A0A0A;font-size:15px;line-height:1.6;margin:0 0 24px;">{ciao}</p>
          <p style="color:#0A0A0A;font-size:15px;line-height:1.6;margin:0 0 24px;">
            Abbiamo ricevuto una richiesta di reset della tua password. Clicca sul pulsante qui sotto per crearne una nuova.
          </p>
          <div style="text-align:center;margin:32px 0;">
            <a href="{reset_url}" style="display:inline-block;padding:14px 32px;background:linear-gradient(135deg,#F58A1F,#F5D419);color:#0A0A0A;text-decoration:none;font-weight:700;border-radius:999px;font-size:15px;">Imposta nuova password</a>
          </div>
          <p style="color:#0A0A0A;font-size:13px;line-height:1.6;margin:0 0 12px;">
            Se il pulsante non funziona, copia questo link nel tuo browser:<br/>
            <span style="color:#F58A1F;font-size:11px;word-break:break-all;">{reset_url}</span>
          </p>
          <hr style="border:none;border-top:1px solid #eee;margin:32px 0;"/>
          <p style="color:#666;font-size:12px;line-height:1.5;margin:0;">
            Il link scade tra <strong>30 minuti</strong> e può essere usato <strong>una sola volta</strong>.<br/>
            Se non hai richiesto il reset, ignora semplicemente questa email — la tua password attuale rimane valida.
          </p>
        </td></tr>
      </table>
      <p style="color:#0A0A0A;opacity:0.5;font-size:11px;margin-top:20px;">
        BIDOC SRL · Via Mazzini 62 · Spilimbergo (PN) · funzionabene.it
      </p>
    </td></tr>
  </table>
</body></html>"""

    params = {
        "from": f"FunzionaBene <{SENDER_EMAIL}>",
        "to": [email],
        "subject": "Reimposta la tua password FunzionaBene",
        "html": html,
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL SENT] password reset (id={result.get('id') if isinstance(result, dict) else result})")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] password reset send failed: {e}")
        return False



async def send_reschedule_notification_email(
    to_email: str,
    to_nome: str,
    paziente_nome: str,
    old_datetime_iso: str,
    new_datetime_iso: str,
    role: str = "terapista",
) -> bool:
    """Notify a therapist (or patient) that an appointment has been rescheduled by the counterpart."""
    if not RESEND_API_KEY or RESEND_API_KEY == "placeholder_resend_key":
        logger.warning("[EMAIL] No Resend API key configured, skipping reschedule notification")
        return False

    old_fmt = _format_data_ora_it(old_datetime_iso)
    new_fmt = _format_data_ora_it(new_datetime_iso)
    ciao = f"Ciao {to_nome}," if to_nome else "Ciao,"
    subject_prefix = "Il paziente ha riprogrammato" if role == "terapista" else "Appuntamento riprogrammato"

    html = f"""<!DOCTYPE html>
<html lang="it"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0A0A0A;font-family:'Helvetica Neue',Arial,sans-serif;color:#F4F1ED;">
<table width="100%" cellspacing="0" cellpadding="0" border="0" style="background:#0A0A0A;padding:40px 20px;">
<tr><td align="center">
<table width="560" cellspacing="0" cellpadding="0" border="0" style="max-width:560px;background:#111;border:1px solid rgba(255,255,255,0.08);border-radius:20px;overflow:hidden;">
  <tr><td style="padding:40px 40px 20px;text-align:center;">
    <div style="font-family:Georgia,serif;font-size:26px;color:#F4F1ED;">funzionabene</div>
    <div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#6B8FA3;margin-top:4px;">appuntamento riprogrammato</div>
  </td></tr>
  <tr><td style="padding:10px 40px 24px;">
    <h1 style="font-family:Georgia,serif;font-size:26px;font-weight:500;margin:0 0 12px;color:#D4A017;">{subject_prefix}</h1>
    <p style="color:rgba(230,226,216,0.75);font-size:14px;line-height:1.6;margin:0 0 20px;">{ciao} il paziente <strong>{paziente_nome}</strong> ha riprogrammato la seduta.</p>
    <table width="100%" style="background:rgba(212,160,23,0.06);border:1px solid rgba(212,160,23,0.25);border-radius:14px;padding:16px;margin-bottom:12px;">
      <tr><td style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:rgba(230,226,216,0.5);padding-bottom:6px;">Vecchio orario (cancellato)</td></tr>
      <tr><td style="font-size:15px;color:rgba(230,226,216,0.6);text-decoration:line-through;padding-bottom:4px;">{old_fmt}</td></tr>
    </table>
    <table width="100%" style="background:rgba(107,143,163,0.14);border:1px solid rgba(107,143,163,0.5);border-radius:14px;padding:16px;">
      <tr><td style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#6B8FA3;padding-bottom:6px;">Nuovo orario</td></tr>
      <tr><td style="font-family:Georgia,serif;font-size:20px;color:#D4A017;padding-bottom:4px;">{new_fmt}</td></tr>
    </table>
    <p style="color:rgba(230,226,216,0.55);font-size:12px;line-height:1.6;margin:20px 0 0;">
      Riceverai un nuovo link per la videocall nella stanza rigenerata automaticamente. Nessuna azione richiesta.
    </p>
  </td></tr>
  <tr><td style="padding:20px 40px 40px;border-top:1px solid rgba(255,255,255,0.08);text-align:center;">
    <p style="color:rgba(230,226,216,0.4);font-size:11px;margin:0;">© FunzionaBene · BIDOC SRL · funzionabene.it</p>
  </td></tr>
</table>
</td></tr></table></body></html>"""

    params = {
        "from": f"FunzionaBene <{SENDER_EMAIL}>",
        "to": [to_email],
        "subject": f"{subject_prefix} — {new_fmt}",
        "html": html,
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL SENT] reschedule notify to {to_email} (id={result.get('id') if isinstance(result, dict) else result})")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] reschedule notify failed: {e}")
        return False


# ─── Legal document MAJOR-version notification ───────────────────────────────
async def send_legal_major_update_email(
    email: str,
    nome: str,
    doc_title: str,
    doc_version: int,
    frontend_url: str,
    decline_token: str,
) -> bool:
    """Notify a user (typically terapeuta) that a legal doc had a MAJOR update.
    Includes a link to accept and a link to decline (auto-deactivation 48h)."""
    if not SEND_EMAILS or not RESEND_API_KEY or RESEND_API_KEY == "placeholder_resend_key":
        logger.info(f"[EMAIL DISABLED] MAJOR update {doc_title} v{doc_version} to {email}")
        return False
    accept_url = f"{frontend_url.rstrip('/')}/terapeuta/firma-documenti"
    decline_url = f"{frontend_url.rstrip('/')}/legal-decline/{decline_token}"
    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#0A0A0A;font-family:Helvetica,Arial,sans-serif;color:#F4F1ED;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0A0A0A;padding:40px 20px;"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="max-width:560px;background:#111;border:1px solid rgba(255,255,255,0.08);border-radius:20px;overflow:hidden;">
<tr><td style="padding:32px 40px 12px;text-align:center;">
<div style="font-family:Georgia,serif;font-size:22px;color:#F4F1ED;">funzionabene</div>
<div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#F58A1F;margin-top:4px;">DOCUMENTO LEGALE AGGIORNATO</div>
</td></tr>
<tr><td style="padding:16px 40px;">
<h1 style="font-family:Georgia,serif;font-size:24px;color:#F4F1ED;margin:0 0 12px 0;">Ciao {nome},</h1>
<p style="color:rgba(230,226,216,0.75);font-size:15px;line-height:1.6;margin:0 0 20px 0;">
è stata pubblicata una <strong style="color:#F58A1F;">nuova versione MAJOR</strong> del documento:<br>
<strong style="color:#F4F1ED;">{doc_title}</strong> — versione {doc_version}
</p>
<p style="color:rgba(230,226,216,0.65);font-size:14px;line-height:1.5;margin:0 0 24px 0;">
Per continuare a operare sulla piattaforma è necessario <strong style="color:#F4F1ED;">rileggere e ri-firmare</strong> il documento al prossimo accesso.
</p>
</td></tr>
<tr><td style="padding:0 40px 24px;text-align:center;">
<a href="{accept_url}" style="display:inline-block;padding:14px 30px;background:linear-gradient(135deg,#F58A1F,#F5D419);color:#0A0A0A;text-decoration:none;font-weight:bold;border-radius:100px;font-size:14px;">Vai alla piattaforma per firmare →</a>
</td></tr>
<tr><td style="padding:16px 40px 24px;border-top:1px solid rgba(255,255,255,0.08);">
<p style="color:rgba(230,226,216,0.55);font-size:12px;line-height:1.5;margin:0 0 8px 0;">
<strong>Non intendi accettare la nuova versione?</strong>
</p>
<p style="color:rgba(230,226,216,0.5);font-size:12px;line-height:1.5;margin:0;">
Clicca qui: <a href="{decline_url}" style="color:#F58A1F;">NON ACCETTO — disattiva il mio profilo</a>.<br>
Il tuo profilo verrà disattivato automaticamente entro 48 ore e riceverai una conferma via email.
Gli appuntamenti già confermati saranno onorati; le prenotazioni future saranno cancellate con rimborso ai pazienti.
</p>
</td></tr>
<tr><td style="padding:20px 40px;text-align:center;font-size:11px;color:rgba(230,226,216,0.3);">
BIDOC SRL · P.IVA 01985930930 · Via Mazzini 62, 33097 Spilimbergo (PN)<br>
Per assistenza: <a href="mailto:privacy@bidoc.it" style="color:rgba(230,226,216,0.5);">privacy@bidoc.it</a>
</td></tr>
</table></td></tr></table></body></html>"""
    params = {
        "from": f"FunzionaBene <{SENDER_EMAIL}>",
        "to": [email],
        "subject": f"Aggiornamento importante: {doc_title} v{doc_version}",
        "html": html,
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL SENT] MAJOR update {doc_title} v{doc_version} to {email} (id={result.get('id') if isinstance(result, dict) else result})")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] MAJOR update to {email} failed: {e}")
        return False


async def send_signature_receipt_email(email: str, nome: str, doc_titles: list, pdf_bytes: bytes) -> bool:
    """Send the signed PDF receipt as email attachment."""
    if not SEND_EMAILS or not RESEND_API_KEY or RESEND_API_KEY == "placeholder_resend_key":
        logger.info(f"[EMAIL DISABLED] Receipt for {email} ({len(doc_titles)} docs)")
        return False
    import base64
    docs_list = "".join([f"<li>{t}</li>" for t in doc_titles])
    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:40px 20px;background:#0A0A0A;font-family:Helvetica,Arial,sans-serif;color:#F4F1ED;">
<table width="560" cellpadding="0" cellspacing="0" style="margin:0 auto;max-width:560px;background:#111;border-radius:20px;overflow:hidden;">
<tr><td style="padding:32px 40px;text-align:center;">
<div style="font-family:Georgia,serif;font-size:22px;color:#F4F1ED;">funzionabene</div>
<div style="font-size:10px;letter-spacing:3px;color:#F58A1F;margin-top:4px;">RICEVUTA DI SOTTOSCRIZIONE</div>
</td></tr>
<tr><td style="padding:0 40px 24px;">
<p style="color:rgba(230,226,216,0.85);font-size:15px;line-height:1.6;margin:0 0 20px;">Ciao <strong>{nome}</strong>,</p>
<p style="color:rgba(230,226,216,0.75);font-size:14px;line-height:1.6;margin:0 0 16px;">
Grazie per aver sottoscritto i seguenti documenti legali:
</p>
<ul style="color:rgba(230,226,216,0.75);font-size:14px;line-height:1.8;">{docs_list}</ul>
<p style="color:rgba(230,226,216,0.65);font-size:13px;line-height:1.5;margin:20px 0 0;">
In allegato trovi la <strong style="color:#F4F1ED;">Ricevuta di Sottoscrizione</strong> con tutti i dettagli
(hash SHA-256, timestamp UTC, metadati di firma). Ti consigliamo di conservarla.
</p>
</td></tr>
<tr><td style="padding:20px 40px;text-align:center;font-size:11px;color:rgba(230,226,216,0.3);border-top:1px solid rgba(255,255,255,0.08);">
BIDOC SRL · P.IVA 01985930930 · privacy@bidoc.it
</td></tr>
</table></body></html>"""
    params = {
        "from": f"FunzionaBene <{SENDER_EMAIL}>",
        "to": [email],
        "subject": "Ricevuta di sottoscrizione — Funzionabene",
        "html": html,
        "attachments": [{
            "filename": "ricevuta_sottoscrizione.pdf",
            "content": base64.b64encode(pdf_bytes).decode("utf-8"),
        }],
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL SENT] Receipt to {email} (id={result.get('id') if isinstance(result, dict) else result})")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] Receipt to {email} failed: {e}")
        return False



async def send_weekly_fatture_email(
    email: str,
    nome: str,
    fatture_sanitarie: list,   # [{numero, data, importo_totale}]
    fatture_commissioni: list, # [{numero, data, importo_totale, mese_riferimento, anno_riferimento}]
    attachments: list,         # [{filename, content_b64}]
    week_from: str,
    week_to: str,
) -> bool:
    """Weekly digest email: attaches ALL PDF + XML of the week's fatture (sanitarie + commissioni)."""
    if not SEND_EMAILS or not RESEND_API_KEY or RESEND_API_KEY == "placeholder_resend_key":
        logger.info(f"[EMAIL DISABLED] Weekly fatture digest for {email} ({len(attachments)} allegati)")
        return False

    sanit_rows = "".join([
        f'<tr><td style="padding:6px 12px;color:#F4F1ED;font-family:monospace;">{f.get("numero","")}</td>'
        f'<td style="padding:6px 12px;color:rgba(230,226,216,0.75);">{f.get("data","")}</td>'
        f'<td style="padding:6px 12px;color:#F58A1F;text-align:right;">€ {f.get("importo_totale",0):.2f}</td></tr>'
        for f in fatture_sanitarie
    ]) or '<tr><td colspan="3" style="padding:12px;color:rgba(230,226,216,0.5);text-align:center;font-style:italic;">Nessuna fattura sanitaria emessa</td></tr>'

    comm_rows = "".join([
        f'<tr><td style="padding:6px 12px;color:#F4F1ED;font-family:monospace;">{f.get("numero","")}</td>'
        f'<td style="padding:6px 12px;color:rgba(230,226,216,0.75);">{f.get("mese_riferimento","")}/{f.get("anno_riferimento","")}</td>'
        f'<td style="padding:6px 12px;color:#F58A1F;text-align:right;">€ {f.get("importo_totale",0):.2f}</td></tr>'
        for f in fatture_commissioni
    ]) or '<tr><td colspan="3" style="padding:12px;color:rgba(230,226,216,0.5);text-align:center;font-style:italic;">Nessuna fattura di commissione ricevuta</td></tr>'

    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:40px 20px;background:#0A0A0A;font-family:Helvetica,Arial,sans-serif;color:#F4F1ED;">
<table width="620" cellpadding="0" cellspacing="0" style="margin:0 auto;max-width:620px;background:#111;border-radius:20px;overflow:hidden;">
<tr><td style="padding:32px 40px;text-align:center;border-bottom:1px solid rgba(255,255,255,0.08);">
<div style="font-family:Georgia,serif;font-size:22px;color:#F4F1ED;">funzionabene</div>
<div style="font-size:10px;letter-spacing:3px;color:#F58A1F;margin-top:4px;">RIEPILOGO FATTURE SETTIMANALE</div>
</td></tr>
<tr><td style="padding:28px 40px 12px;">
<p style="color:rgba(230,226,216,0.85);font-size:15px;line-height:1.6;margin:0 0 8px;">Ciao <strong>{nome}</strong>,</p>
<p style="color:rgba(230,226,216,0.75);font-size:14px;line-height:1.6;margin:0 0 20px;">
Ecco il riepilogo delle fatture della settimana <strong style="color:#F4F1ED;">{week_from} → {week_to}</strong>.
In allegato trovi <strong style="color:#F58A1F;">PDF e XML FatturaPA</strong> di ogni fattura per l'inoltro
al tuo commercialista e al Sistema di Interscambio (SDI).
</p>
</td></tr>
<tr><td style="padding:0 40px 12px;">
<div style="font-size:11px;letter-spacing:2px;color:#F58A1F;margin-bottom:8px;">FATTURE SANITARIE EMESSE ({len(fatture_sanitarie)})</div>
<table width="100%" style="background:rgba(255,255,255,0.03);border-radius:10px;border-collapse:separate;">
<thead><tr><th style="padding:8px 12px;text-align:left;font-size:11px;color:rgba(230,226,216,0.5);text-transform:uppercase;letter-spacing:1.5px;">Numero</th>
<th style="padding:8px 12px;text-align:left;font-size:11px;color:rgba(230,226,216,0.5);text-transform:uppercase;letter-spacing:1.5px;">Data</th>
<th style="padding:8px 12px;text-align:right;font-size:11px;color:rgba(230,226,216,0.5);text-transform:uppercase;letter-spacing:1.5px;">Totale</th></tr></thead>
<tbody>{sanit_rows}</tbody></table>
</td></tr>
<tr><td style="padding:16px 40px 12px;">
<div style="font-size:11px;letter-spacing:2px;color:#F58A1F;margin-bottom:8px;">FATTURE DI COMMISSIONE B2B RICEVUTE ({len(fatture_commissioni)})</div>
<table width="100%" style="background:rgba(255,255,255,0.03);border-radius:10px;border-collapse:separate;">
<thead><tr><th style="padding:8px 12px;text-align:left;font-size:11px;color:rgba(230,226,216,0.5);text-transform:uppercase;letter-spacing:1.5px;">Numero</th>
<th style="padding:8px 12px;text-align:left;font-size:11px;color:rgba(230,226,216,0.5);text-transform:uppercase;letter-spacing:1.5px;">Periodo</th>
<th style="padding:8px 12px;text-align:right;font-size:11px;color:rgba(230,226,216,0.5);text-transform:uppercase;letter-spacing:1.5px;">Totale</th></tr></thead>
<tbody>{comm_rows}</tbody></table>
</td></tr>
<tr><td style="padding:16px 40px 28px;">
<p style="color:rgba(230,226,216,0.6);font-size:12px;line-height:1.5;margin:12px 0 0;">
Puoi consultare, filtrare e scaricare le fatture in qualsiasi momento dalla tua dashboard →
<a href="https://www.funzionabene.it/terapeuta/fatture" style="color:#F58A1F;text-decoration:none;">Le mie fatture</a>.
</p>
</td></tr>
<tr><td style="padding:20px 40px;text-align:center;font-size:11px;color:rgba(230,226,216,0.3);border-top:1px solid rgba(255,255,255,0.08);">
BIDOC SRL · P.IVA 01985930930 · fatturazione@funzionabene.it
</td></tr>
</table></body></html>"""

    params = {
        "from": f"FunzionaBene <{SENDER_EMAIL}>",
        "to": [email],
        "subject": f"Riepilogo fatture — {week_from} → {week_to}",
        "html": html,
        "attachments": attachments,  # list of {filename, content}
    }
    try:
        result = await asyncio.to_thread(resend.Emails.send, params)
        logger.info(f"[EMAIL SENT] Weekly fatture digest to {email} — {len(attachments)} allegati (id={result.get('id') if isinstance(result, dict) else result})")
        return True
    except Exception as e:
        logger.error(f"[EMAIL ERROR] Weekly fatture digest to {email} failed: {e}")
        return False


# ─── Therapist approval workflow emails ───────────────────────────────────────
async def send_new_therapist_admin_alert(therapist: dict) -> bool:
    """Notify admin(s) that a new therapist has registered and awaits approval."""
    admin_email = os.environ.get("ADMIN_EMAIL", "hr@funzionabene.it")
    if not admin_email:
        return False
    frontend = (os.environ.get("FRONTEND_URL") or "https://funzionabene.it").rstrip("/")
    review_url = f"{frontend}/admin/terapisti"
    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:40px 20px;background:#0A0A0A;font-family:Helvetica,Arial,sans-serif;color:#F4F1ED;">
<table width="560" cellpadding="0" cellspacing="0" style="margin:0 auto;background:#111;border-radius:20px;overflow:hidden;">
<tr><td style="padding:32px 40px;text-align:center;border-bottom:1px solid rgba(255,255,255,0.08);">
<div style="font-family:Georgia,serif;font-size:22px;color:#F4F1ED;">funzionabene</div>
<div style="font-size:10px;letter-spacing:3px;color:#F58A1F;margin-top:6px;">NUOVA RICHIESTA TERAPEUTA</div>
</td></tr>
<tr><td style="padding:32px 40px 12px;">
<h1 style="font-family:Georgia,serif;font-size:26px;color:#D4A017;margin:0 0 12px;font-weight:500;">Un nuovo terapeuta si è registrato</h1>
<p style="color:rgba(230,226,216,0.75);font-size:14px;line-height:1.6;margin:0 0 20px;">Attende la tua approvazione prima di essere visibile pubblicamente sul sito.</p>
</td></tr>
<tr><td style="padding:0 40px 20px;">
<table width="100%" style="background:rgba(212,160,23,0.06);border:1px solid rgba(212,160,23,0.25);border-radius:14px;">
<tr><td style="padding:16px 20px;">
<div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#6B8FA3;padding-bottom:6px;">Dati anagrafici</div>
<div style="font-family:Georgia,serif;font-size:18px;color:#D4A017;">{therapist.get('nome','')} {therapist.get('cognome','')}</div>
<div style="font-size:13px;color:rgba(230,226,216,0.7);margin-top:4px;">{therapist.get('email','')}</div>
{f'<div style="font-size:13px;color:rgba(230,226,216,0.7);margin-top:4px;">Tel: {therapist.get("telefono")}</div>' if therapist.get("telefono") else ''}
{f'<div style="margin-top:12px;padding:10px 12px;background:rgba(255,255,255,0.03);border-radius:8px;font-size:13px;color:rgba(230,226,216,0.75);line-height:1.5;"><em>«{therapist.get("messaggio")}»</em></div>' if therapist.get("messaggio") else ''}
<div style="font-size:12px;color:rgba(230,226,216,0.5);margin-top:8px;">Registrazione: {therapist.get('created_at','')}</div>
</td></tr></table>
</td></tr>
<tr><td style="padding:0 40px 28px;text-align:center;">
<a href="{review_url}" style="display:inline-block;background:#D4A017;color:#0A0A0A;font-weight:600;text-decoration:none;padding:14px 32px;border-radius:12px;font-size:14px;letter-spacing:0.5px;">Rivedi profilo e documenti →</a>
</td></tr>
<tr><td style="padding:20px 40px;border-top:1px solid rgba(255,255,255,0.08);text-align:center;">
<p style="color:rgba(230,226,216,0.4);font-size:11px;margin:0;">© FunzionaBene · Backoffice Admin</p>
</td></tr>
</table></body></html>"""
    return await _send_raw({
        "from": f"FunzionaBene Admin <{SENDER_EMAIL}>",
        "to": [admin_email],
        "subject": f"Nuovo terapeuta da approvare: Dr. {therapist.get('nome','')} {therapist.get('cognome','')}",
        "html": html,
    })


async def send_therapist_approved_email(email: str, nome: str) -> bool:
    """Notify a therapist that they have been approved and are now publicly visible."""
    if not email:
        return False
    frontend = (os.environ.get("FRONTEND_URL") or "https://funzionabene.it").rstrip("/")
    dashboard_url = f"{frontend}/terapeuta"
    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:40px 20px;background:#0A0A0A;font-family:Helvetica,Arial,sans-serif;color:#F4F1ED;">
<table width="560" cellpadding="0" cellspacing="0" style="margin:0 auto;background:#111;border-radius:20px;overflow:hidden;">
<tr><td style="padding:32px 40px;text-align:center;border-bottom:1px solid rgba(255,255,255,0.08);">
<div style="font-family:Georgia,serif;font-size:22px;color:#F4F1ED;">funzionabene</div>
<div style="font-size:10px;letter-spacing:3px;color:#84B57A;margin-top:6px;">PROFILO APPROVATO</div>
</td></tr>
<tr><td style="padding:32px 40px 12px;">
<h1 style="font-family:Georgia,serif;font-size:28px;color:#84B57A;margin:0 0 14px;font-weight:500;">Benvenuto/a in FunzionaBene, {nome} 🎉</h1>
<p style="color:rgba(230,226,216,0.85);font-size:15px;line-height:1.6;margin:0 0 12px;">
Il tuo profilo è stato <strong style="color:#84B57A;">approvato</strong> dall'amministrazione. Da questo momento sei visibile pubblicamente sul sito e i pazienti possono prenotare sessioni con te.
</p>
<p style="color:rgba(230,226,216,0.65);font-size:13px;line-height:1.6;margin:12px 0 0;">
Verifica di aver completato: biografia, disponibilità settimanale, prezzo sessione, foto profilo. Più il tuo profilo è completo, più pazienti troverai.
</p>
</td></tr>
<tr><td style="padding:20px 40px 28px;text-align:center;">
<a href="{dashboard_url}" style="display:inline-block;background:#D4A017;color:#0A0A0A;font-weight:600;text-decoration:none;padding:14px 32px;border-radius:12px;font-size:14px;letter-spacing:0.5px;">Vai alla dashboard →</a>
</td></tr>
<tr><td style="padding:20px 40px;border-top:1px solid rgba(255,255,255,0.08);text-align:center;">
<p style="color:rgba(230,226,216,0.4);font-size:11px;margin:0;">© FunzionaBene · Psicologi e Sessuologi</p>
</td></tr>
</table></body></html>"""
    return await _send_raw({
        "from": f"FunzionaBene <{SENDER_EMAIL}>",
        "to": [email],
        "subject": "Il tuo profilo è stato approvato — Benvenuto/a in FunzionaBene",
        "html": html,
    })
