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
          <div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#6B8FA3;margin-top:4px;">clinica psicologica</div>
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
  <div style="font-size:10px;letter-spacing:3px;text-transform:uppercase;color:#6B8FA3;margin-top:4px;">clinica psicologica</div>
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
    Riceverai un promemoria 1 giorno prima e 1 ora prima.
  </p>
  <p style="font-size:12px;color:rgba(230,226,216,0.4);line-height:1.6;margin:0;">
    Puoi cancellare o riprogrammare fino a 24 ore prima.
  </p>
</td></tr>
<tr><td style="padding:20px 40px 40px;border-top:1px solid rgba(255,255,255,0.08);text-align:center;">
  <p style="color:rgba(230,226,216,0.4);font-size:11px;line-height:1.6;margin:0;">© FunzionaBene — Clinica di Psicologia e Sessuologia<br>Trattamento dati ai sensi del GDPR</p>
</td></tr>
</table></td></tr></table></body></html>"""


def _reminder_template(ctx: dict, when: str) -> str:
    """when = '1-giorno' or '1-ora'."""
    dt_fmt = _format_data_ora_it(ctx["data_ora"])
    titolo = "La tua seduta è domani" if when == "1-giorno" else "La tua seduta inizia tra un'ora"
    sottotitolo = (
        "Ricorda: puoi entrare nella stanza video 15 minuti prima dell'orario."
        if when == "1-ora"
        else "Ti aspettiamo. Controlla i dettagli qui sotto."
    )
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
</td></tr>
<tr><td style="padding:28px 40px 40px;border-top:1px solid rgba(255,255,255,0.08);text-align:center;margin-top:20px;">
  <p style="color:rgba(230,226,216,0.4);font-size:11px;margin:0;">© FunzionaBene · Clinica di Psicologia e Sessuologia</p>
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
    """Send reminder email to paziente. when = '1-giorno' | '1-ora'."""
    if not ctx.get("paziente_email"):
        return False
    subject = "Promemoria: la tua seduta è domani" if when == "1-giorno" else "La tua seduta inizia tra un'ora"
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
