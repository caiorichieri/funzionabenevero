"""Fatture router — genera e serve XML+PDF di fatture sanitarie (per conto del terapeuta)
e commissioni B2B (BIDOC → terapeuta).
"""
import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from html import escape

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response
from pymongo.errors import DuplicateKeyError

from deps import db, require_auth, require_admin, find_user_by_id
from fatturazione import (
    next_fattura_number,
    generate_xml_sanitaria,
    generate_xml_commissione,
    generate_xml_nota_credito_sanitaria,
    generate_pdf,
    COMMISSIONE_PERCENT, IVA_COMMISSIONE, BOLLO_SOGLIA, BIDOC,
)
from object_storage import put_object, get_object

logger = logging.getLogger(__name__)
router = APIRouter()


# Appointment states that indicate a paid session (money collected → fattura
# sanitaria owed at payment + commission owed at month-end). Refunded sessions
# transition to 'cancellato' via /admin/refunds side-effects and are excluded.
PAID_APPT_STATES = [
    "completato",
    "confermato",
    "in_corso",
    "no_show_paziente",
    "no_show_terapeuta",
    "no_show_entrambi",
    "cancellato_con_addebito",
]


async def _get_terapeuta_full(user_id: str) -> dict | None:
    u = await find_user_by_id(user_id)
    if not u:
        return None
    p = await db.terapisti.find_one({"user_id": user_id}) or {}
    return {**u, **{k: v for k, v in p.items() if k not in ["_id", "user_id"]}}


async def _get_paziente_full(user_id: str) -> dict:
    u = await find_user_by_id(user_id)
    if not u:
        return {"nome": "Paziente", "cognome": "", "codice_fiscale": ""}
    p = await db.pazienti.find_one({"user_id": user_id}) or {}
    return {
        "nome": u.get("nome", ""),
        "cognome": u.get("cognome", ""),
        "codice_fiscale": p.get("codice_fiscale") or u.get("codice_fiscale", ""),
        "indirizzo": p.get("indirizzo", ""),
        "cap": p.get("cap", ""),
        "comune": p.get("comune", ""),
        "provincia": p.get("provincia", ""),
    }


async def _resolve_terapeuta_user_id(appt: dict) -> str | None:
    """Return the therapist's users._id for an appointment.

    Real bookings created via /payments/checkout/booking store only `terapeuta_id`
    (points to terapisti._id). Older/test bookings also store `terapeuta_user_id`.
    This resolver handles both, and backfills the missing field on the appointment
    so downstream flows (monthly commissione aggregation, etc.) see it too.
    """
    uid = appt.get("terapeuta_user_id")
    if uid:
        return uid
    tid = appt.get("terapeuta_id")
    if not tid:
        return None
    try:
        t = await db.terapisti.find_one({"_id": ObjectId(tid)})
    except Exception:
        t = None
    if not t:
        return None
    uid = t.get("user_id")
    if uid:
        # Best-effort backfill; safe if it fails (we already have the value).
        try:
            await db.appuntamenti.update_one(
                {"_id": appt["_id"]},
                {"$set": {"terapeuta_user_id": str(uid)}},
            )
        except Exception:
            pass
    return uid


async def _generate_fattura_paziente(appuntamento_id: str) -> dict:
    """Idempotent + race-safe: unique index on {appuntamento_id, kind} guarantees
    only one fattura sanitaria per appuntamento. Number is allocated AFTER content
    build succeeds so failed generations don't burn fiscal numbers."""
    existing = await db.fatture.find_one({"appuntamento_id": appuntamento_id, "kind": "sanitaria"})
    if existing:
        return existing
    appt = await db.appuntamenti.find_one({"_id": ObjectId(appuntamento_id)})
    if not appt:
        raise ValueError(f"Appuntamento {appuntamento_id} non trovato")
    terapeuta_user_id = await _resolve_terapeuta_user_id(appt)
    terapeuta = await _get_terapeuta_full(terapeuta_user_id) if terapeuta_user_id else None
    if not terapeuta:
        raise ValueError("Terapeuta non trovato")
    if not (terapeuta.get("partita_iva") and terapeuta.get("codice_fiscale")):
        raise ValueError("Dati fiscali terapeuta incompleti (P.IVA/CF)")
    paziente = await _get_paziente_full(appt.get("paziente_user_id"))

    importo = Decimal(str(
        appt.get("prezzo")
        or terapeuta.get("prezzo_sessione")
        or terapeuta.get("tariffa")
        or 70
    ))
    year = datetime.now(timezone.utc).year
    data = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    causale = f"Prestazione psicologica del {appt.get('data_ora', '')[:10]}"

    # Validate anagraphics BEFORE allocating a fiscal number.
    # This dry-run also catches any character issues in cedente/cessionario.
    _validate_anagrafica("terapeuta", terapeuta, ["nome", "cognome", "partita_iva", "codice_fiscale"])
    _validate_anagrafica("paziente", paziente, ["nome", "cognome"])

    # Allocate number AFTER validation → minimizes wasted fiscal numbers
    numero = await next_fattura_number(db, "sanitaria", year)

    try:
        xml_bytes = generate_xml_sanitaria(
            numero=numero, data=data, terapeuta=terapeuta, paziente=paziente,
            importo=importo, causale=causale,
        )
        pdf_bytes = generate_pdf(
            fattura={
                "numero": numero, "data": data, "totale": importo,
                "imponibile": importo, "imposta": Decimal("0"),
                "linee": [{"descrizione": causale, "prezzo": importo}],
                "causale": causale,
            },
            cedente_display=_safe_html_block(
                f"<b>{escape(terapeuta.get('nome',''))} {escape(terapeuta.get('cognome',''))}</b>",
                f"P.IVA {escape(terapeuta.get('partita_iva',''))}",
                f"CF {escape(terapeuta.get('codice_fiscale',''))}",
                escape(terapeuta.get('residenza_indirizzo','')),
                f"{escape(terapeuta.get('residenza_cap',''))} {escape(terapeuta.get('residenza_comune',''))} {escape(terapeuta.get('residenza_provincia',''))}",
            ),
            cessionario_display=_safe_html_block(
                f"<b>{escape(paziente.get('nome',''))} {escape(paziente.get('cognome',''))}</b>",
                f"CF {escape(paziente.get('codice_fiscale','—'))}",
                escape(paziente.get('indirizzo','')),
                f"{escape(paziente.get('cap',''))} {escape(paziente.get('comune',''))} {escape(paziente.get('provincia',''))}",
            ),
            is_sanitaria=True,
        )
    except Exception as e:
        logger.exception(f"[FATTURA] Content generation failed for {numero} appt={appuntamento_id}: {e}")
        # Record burned number for fiscal audit trail (Italian law requires explaining gaps)
        await db.fattura_burned_numbers.insert_one({
            "numero": numero, "kind": "sanitaria", "year": year,
            "reason": str(e)[:500], "appuntamento_id": appuntamento_id,
            "burned_at": datetime.now(timezone.utc),
        })
        raise

    # Upload to Object Storage OFF the event loop (non-blocking)
    xml_path = pdf_path = None
    xml_b64 = pdf_b64 = None
    try:
        xml_result = await asyncio.to_thread(put_object, f"funzionabene/fatture/{numero}.xml", xml_bytes, "application/xml")
        pdf_result = await asyncio.to_thread(put_object, f"funzionabene/fatture/{numero}.pdf", pdf_bytes, "application/pdf")
        xml_path = xml_result.get("path")
        pdf_path = pdf_result.get("path")
    except Exception as e:
        import base64
        logger.warning(f"[FATTURA] Object Storage failed for {numero}, using inline: {e}")
        xml_b64 = base64.b64encode(xml_bytes).decode("ascii")
        pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    doc = {
        "kind": "sanitaria",
        "numero": numero,
        "data": data,
        "appuntamento_id": appuntamento_id,
        "terapeuta_user_id": terapeuta_user_id,
        "paziente_user_id": appt.get("paziente_user_id"),
        "importo_totale": float(importo),
        "importo_imponibile": float(importo),
        "importo_iva": 0.0,
        "aliquota_iva": 0.0,
        "natura": "N4",
        "marca_bollo": importo >= BOLLO_SOGLIA,
        "xml_storage_path": xml_path,
        "pdf_storage_path": pdf_path,
        "xml_inline_b64": xml_b64,
        "pdf_inline_b64": pdf_b64,
        "created_at": datetime.now(timezone.utc),
        "trasmessa_sistema_ts": False,
    }
    try:
        result = await db.fatture.insert_one(doc)
        doc["_id"] = result.inserted_id
    except DuplicateKeyError:
        # Race: another concurrent request already generated this fattura.
        # Burn our number and return the pre-existing document.
        await db.fattura_burned_numbers.insert_one({
            "numero": numero, "kind": "sanitaria", "year": year,
            "reason": "concurrent duplicate — fatture unique index triggered",
            "appuntamento_id": appuntamento_id,
            "burned_at": datetime.now(timezone.utc),
        })
        existing = await db.fatture.find_one({"appuntamento_id": appuntamento_id, "kind": "sanitaria"})
        return existing
    return doc


async def _generate_nota_credito_paziente(fattura_id: str, motivo: str = "Rimborso richiesto") -> dict:
    """Idempotent: emette una Nota di Credito TD04 collegata a una fattura sanitaria.
    Se una NC esiste già per questa fattura, la restituisce.

    Storno FULL: NC per l'intero importo della fattura originale.
    """
    existing = await db.fatture.find_one({"kind": "nota_credito_sanitaria", "fattura_originale_id": fattura_id})
    if existing:
        return existing

    try:
        oid = ObjectId(fattura_id)
    except Exception:
        raise ValueError(f"ID fattura non valido: {fattura_id}")

    fattura_orig = await db.fatture.find_one({"_id": oid})
    if not fattura_orig:
        raise ValueError(f"Fattura {fattura_id} non trovata")
    if fattura_orig.get("kind") != "sanitaria":
        raise ValueError("Nota di credito supportata solo per fatture sanitarie")

    terapeuta = await _get_terapeuta_full(fattura_orig.get("terapeuta_user_id"))
    if not terapeuta:
        raise ValueError("Terapeuta non trovato")
    paziente = await _get_paziente_full(fattura_orig.get("paziente_user_id"))

    importo = Decimal(str(fattura_orig.get("importo_totale", 0)))
    if importo <= 0:
        raise ValueError("Importo fattura originale non valido")

    year = datetime.now(timezone.utc).year
    data = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    causale = f"Storno fattura {fattura_orig.get('numero','')} — {motivo}"[:200]

    _validate_anagrafica("terapeuta", terapeuta, ["nome", "cognome", "partita_iva", "codice_fiscale"])
    _validate_anagrafica("paziente", paziente, ["nome", "cognome"])

    numero = await next_fattura_number(db, "nota_credito_sanitaria", year)
    fattura_riferimento = {
        "numero": fattura_orig.get("numero"),
        "data": fattura_orig.get("data"),
    }

    try:
        xml_bytes = generate_xml_nota_credito_sanitaria(
            numero=numero, data=data, terapeuta=terapeuta, paziente=paziente,
            importo=importo, causale=causale, fattura_riferimento=fattura_riferimento,
        )
        pdf_bytes = generate_pdf(
            fattura={
                "numero": f"NC {numero}",
                "data": data,
                "totale": importo,
                "imponibile": importo,
                "imposta": Decimal("0"),
                "linee": [{"descrizione": causale, "prezzo": importo}],
                "causale": causale,
                "is_nota_credito": True,
                "fattura_riferimento": fattura_riferimento,
            },
            cedente_display=_safe_html_block(
                f"<b>{escape(terapeuta.get('nome',''))} {escape(terapeuta.get('cognome',''))}</b>",
                f"P.IVA {escape(terapeuta.get('partita_iva',''))}",
                f"CF {escape(terapeuta.get('codice_fiscale',''))}",
                escape(terapeuta.get('residenza_indirizzo','')),
                f"{escape(terapeuta.get('residenza_cap',''))} {escape(terapeuta.get('residenza_comune',''))} {escape(terapeuta.get('residenza_provincia',''))}",
            ),
            cessionario_display=_safe_html_block(
                f"<b>{escape(paziente.get('nome',''))} {escape(paziente.get('cognome',''))}</b>",
                f"CF {escape(paziente.get('codice_fiscale','—'))}",
                escape(paziente.get('indirizzo','')),
                f"{escape(paziente.get('cap',''))} {escape(paziente.get('comune',''))} {escape(paziente.get('provincia',''))}",
            ),
            is_sanitaria=True,
        )
    except Exception as e:
        logger.exception(f"[NOTA CREDITO] Content generation failed for {numero} fattura={fattura_id}: {e}")
        await db.fattura_burned_numbers.insert_one({
            "numero": numero, "kind": "nota_credito_sanitaria", "year": year,
            "reason": str(e)[:500], "fattura_originale_id": fattura_id,
            "burned_at": datetime.now(timezone.utc),
        })
        raise

    xml_path = pdf_path = None
    xml_b64 = pdf_b64 = None
    try:
        xml_result = await asyncio.to_thread(put_object, f"funzionabene/fatture/{numero}.xml", xml_bytes, "application/xml")
        pdf_result = await asyncio.to_thread(put_object, f"funzionabene/fatture/{numero}.pdf", pdf_bytes, "application/pdf")
        xml_path = xml_result.get("path")
        pdf_path = pdf_result.get("path")
    except Exception as e:
        import base64
        logger.warning(f"[NOTA CREDITO] Object Storage failed for {numero}, using inline: {e}")
        xml_b64 = base64.b64encode(xml_bytes).decode("ascii")
        pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

    doc = {
        "kind": "nota_credito_sanitaria",
        "numero": numero,
        "data": data,
        "fattura_originale_id": fattura_id,
        "fattura_originale_numero": fattura_orig.get("numero"),
        "appuntamento_id": fattura_orig.get("appuntamento_id"),
        "terapeuta_user_id": fattura_orig.get("terapeuta_user_id"),
        "paziente_user_id": fattura_orig.get("paziente_user_id"),
        "importo_totale": -float(importo),  # segno negativo per contabilizzazione
        "importo_imponibile": -float(importo),
        "importo_iva": 0.0,
        "aliquota_iva": 0.0,
        "natura": "N4",
        "marca_bollo": False,
        "motivo_storno": motivo[:400],
        "xml_storage_path": xml_path,
        "pdf_storage_path": pdf_path,
        "xml_inline_b64": xml_b64,
        "pdf_inline_b64": pdf_b64,
        "created_at": datetime.now(timezone.utc),
        "trasmessa_sistema_ts": False,
    }
    try:
        result = await db.fatture.insert_one(doc)
        doc["_id"] = result.inserted_id
    except DuplicateKeyError:
        await db.fattura_burned_numbers.insert_one({
            "numero": numero, "kind": "nota_credito_sanitaria", "year": year,
            "reason": "concurrent duplicate", "fattura_originale_id": fattura_id,
            "burned_at": datetime.now(timezone.utc),
        })
        existing = await db.fatture.find_one({"kind": "nota_credito_sanitaria", "fattura_originale_id": fattura_id})
        return existing

    # Mark the original fattura as stornata
    await db.fatture.update_one(
        {"_id": oid},
        {"$set": {"stornata": True, "stornata_at": datetime.now(timezone.utc),
                  "nota_credito_id": str(doc["_id"]), "nota_credito_numero": numero}},
    )
    return doc




def _validate_anagrafica(who: str, data: dict, required: list[str]):
    """Fail-fast pre-check so a fiscal number isn't allocated for a broken record."""
    missing = [k for k in required if not (data or {}).get(k)]
    if missing:
        raise ValueError(f"Dati {who} mancanti: {', '.join(missing)}")


def _safe_html_block(*lines: str) -> str:
    """Join pre-escaped lines with <br/> for ReportLab Paragraph rendering."""
    return "<br/>".join(l for l in lines if l is not None and str(l).strip())


async def _generate_fatture_commissione_mensile(year: int, month: int) -> list[dict]:
    """Aggrega gli appuntamenti completati del mese per terapeuta e crea 1 fattura B2B per terapeuta."""
    pipeline_start = f"{year:04d}-{month:02d}-01"
    if month == 12:
        pipeline_end = f"{year+1:04d}-01-01"
    else:
        pipeline_end = f"{year:04d}-{month+1:02d}-01"

    generated = []
    # See PAID_APPT_STATES at module-level: aligns commission billing with the
    # actual fiscal reality — every paid session counts unless refunded.
    tera_ids = await db.appuntamenti.distinct("terapeuta_user_id", {
        "stato": {"$in": PAID_APPT_STATES},
        "data_ora": {"$gte": pipeline_start, "$lt": pipeline_end},
    })
    for tera_id in tera_ids:
        # Skip if already generated
        existing = await db.fatture.find_one({
            "kind": "commissione", "terapeuta_user_id": tera_id,
            "anno_riferimento": year, "mese_riferimento": month,
        })
        if existing:
            generated.append(existing)
            continue
        # Sum
        cursor = db.appuntamenti.find({
            "terapeuta_user_id": tera_id,
            "stato": {"$in": PAID_APPT_STATES},
            "data_ora": {"$gte": pipeline_start, "$lt": pipeline_end},
        })
        total_lordo = Decimal("0")
        count = 0
        async for a in cursor:
            total_lordo += Decimal(str(a.get("prezzo", 0)))
            count += 1
        if total_lordo <= 0:
            continue
        commissione = (total_lordo * COMMISSIONE_PERCENT / Decimal("100")).quantize(Decimal("0.01"))

        terapeuta = await _get_terapeuta_full(tera_id)
        if not terapeuta:
            continue
        if not (terapeuta.get("codice_sdi") or terapeuta.get("pec")):
            logger.warning(f"[FATTURA CM] terapeuta {tera_id} manca codice_sdi/pec, skip")
            continue

        numero = await next_fattura_number(db, "commissione", year)
        data = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        causale = f"Commissione {COMMISSIONE_PERCENT}% su prestazioni {month:02d}/{year} ({count} sedute lorde € {total_lordo})"

        try:
            xml_bytes = generate_xml_commissione(
                numero=numero, data=data, terapeuta=terapeuta,
                importo_imponibile=commissione, causale=causale,
            )
        except Exception as e:
            logger.exception(f"[FATTURA CM] XML gen failed: {e}")
            continue

        imposta = (commissione * IVA_COMMISSIONE / Decimal("100")).quantize(Decimal("0.01"))
        totale = commissione + imposta

        pdf_bytes = generate_pdf(
            fattura={
                "numero": numero, "data": data,
                "totale": totale, "imponibile": commissione, "imposta": imposta,
                "linee": [{"descrizione": causale, "prezzo": commissione}],
                "causale": causale,
            },
            cedente_display=("<b>BIDOC SRL</b><br/>Marchio: Funzionabene<br/>"
                              "P.IVA/CF 01985930930<br/>REA PN-377600<br/>"
                              "P.za I Maggio, 2/interno 2, 33097 Spilimbergo (PN)<br/>PEC bidocsrl@pecimprese.it"),
            cessionario_display=_safe_html_block(
                f"<b>{escape(terapeuta.get('nome',''))} {escape(terapeuta.get('cognome',''))}</b>",
                f"P.IVA {escape(terapeuta.get('partita_iva',''))}",
                f"CF {escape(terapeuta.get('codice_fiscale',''))}",
                f"SDI: {escape(terapeuta.get('codice_sdi') or '0000000')}",
                f"PEC: {escape(terapeuta.get('pec','—'))}",
            ),
            is_sanitaria=False,
        )

        xml_path = pdf_path = None
        xml_b64 = pdf_b64 = None
        try:
            xml_result = await asyncio.to_thread(put_object, f"funzionabene/fatture-commissione/{numero}.xml", xml_bytes, "application/xml")
            pdf_result = await asyncio.to_thread(put_object, f"funzionabene/fatture-commissione/{numero}.pdf", pdf_bytes, "application/pdf")
            xml_path = xml_result.get("path")
            pdf_path = pdf_result.get("path")
        except Exception as e:
            import base64
            logger.warning(f"[FATTURA CM] Storage failed for {numero}: {e}")
            xml_b64 = base64.b64encode(xml_bytes).decode("ascii")
            pdf_b64 = base64.b64encode(pdf_bytes).decode("ascii")

        doc = {
            "kind": "commissione",
            "numero": numero,
            "data": data,
            "terapeuta_user_id": tera_id,
            "anno_riferimento": year,
            "mese_riferimento": month,
            "sedute_count": count,
            "sedute_totale_lordo": float(total_lordo),
            "importo_imponibile": float(commissione),
            "importo_iva": float(imposta),
            "aliquota_iva": float(IVA_COMMISSIONE),
            "importo_totale": float(totale),
            "xml_storage_path": xml_path,
            "pdf_storage_path": pdf_path,
            "xml_inline_b64": xml_b64,
            "pdf_inline_b64": pdf_b64,
            "created_at": datetime.now(timezone.utc),
        }
        r = await db.fatture.insert_one(doc)
        doc["_id"] = r.inserted_id
        generated.append(doc)
        logger.info(f"[FATTURA CM] created {numero} for terapeuta {tera_id} — €{totale}")

    return generated


# ─── Endpoints ────────────────────────────────────────────────────────────────


def _serialize(f: dict) -> dict:
    return {
        "id": str(f.get("_id")),
        "kind": f.get("kind"),
        "numero": f.get("numero"),
        "data": f.get("data"),
        "importo_imponibile": f.get("importo_imponibile"),
        "importo_iva": f.get("importo_iva"),
        "importo_totale": f.get("importo_totale"),
        "aliquota_iva": f.get("aliquota_iva"),
        "marca_bollo": f.get("marca_bollo", False),
        "terapeuta_user_id": f.get("terapeuta_user_id"),
        "paziente_user_id": f.get("paziente_user_id"),
        "appuntamento_id": f.get("appuntamento_id"),
        "anno_riferimento": f.get("anno_riferimento"),
        "mese_riferimento": f.get("mese_riferimento"),
        "sedute_count": f.get("sedute_count"),
        "created_at": f.get("created_at").isoformat() if f.get("created_at") else None,
        "has_xml": bool(f.get("xml_storage_path") or f.get("xml_inline_b64")),
        "has_pdf": bool(f.get("pdf_storage_path") or f.get("pdf_inline_b64")),
    }


@router.get("/fatture/mine")
async def my_fatture(user: dict = Depends(require_auth)):
    """Terapeuta: sees his invoices (sanitarie con lui come emittente + commissioni B2B ricevute da BIDOC).
    Paziente: sees fatture where he is the destinatario (sanitarie)."""
    query_field = "terapeuta_user_id" if user["role"] == "terapeuta" else "paziente_user_id"
    items = []
    async for f in db.fatture.find({query_field: user["_id"]}).sort("created_at", -1).limit(500):
        items.append(_serialize(f))
    return {"items": items}


@router.get("/admin/fatture")
async def admin_fatture(kind: str = None, admin: dict = Depends(require_admin)):
    """Admin BIDOC cassetto — tutte le fatture con filtro kind opzionale."""
    q = {}
    if kind in ("sanitaria", "commissione", "nota_credito_sanitaria"):
        q["kind"] = kind
    items = []
    async for f in db.fatture.find(q).sort("created_at", -1).limit(2000):
        items.append(_serialize(f))
    return {"items": items, "count": len(items)}


@router.get("/admin/fatture/diagnostics")
async def admin_fatture_diagnostics(admin: dict = Depends(require_admin)):
    """Diagnostic endpoint: return paid appointments that DON'T have a fattura
    sanitaria yet AND refunded transactions that DON'T have a nota di credito yet.
    Helps the admin see if the auto-emit at payment/refund failed silently."""
    paid_appts = await db.appuntamenti.find({
        "stato": {"$in": PAID_APPT_STATES},
        "paid_at": {"$exists": True},
    }).sort("data_ora", -1).limit(200).to_list(200)

    missing = []
    for a in paid_appts:
        appt_id = str(a["_id"])
        existing = await db.fatture.find_one({"appuntamento_id": appt_id, "kind": "sanitaria"})
        if existing:
            continue
        # Fetch patient + therapist names for the UI
        pu = await db.users.find_one({"_id": ObjectId(a["paziente_user_id"])}) if a.get("paziente_user_id") else None
        tu_id = a.get("terapeuta_user_id")
        if not tu_id and a.get("terapeuta_id"):
            try:
                _t = await db.terapisti.find_one({"_id": ObjectId(a["terapeuta_id"])})
                tu_id = _t.get("user_id") if _t else None
            except Exception:
                tu_id = None
        tu = None
        if tu_id:
            try:
                tu = await db.users.find_one({"_id": ObjectId(tu_id)})
            except Exception:
                tu = None
        # Look up last known failure on the linked payment_transaction
        tx = await db.payment_transactions.find_one({"appointment_id": appt_id})
        missing.append({
            "appuntamento_id": appt_id,
            "data_ora": a.get("data_ora"),
            "stato": a.get("stato"),
            "paid_at": a.get("paid_at").isoformat() if hasattr(a.get("paid_at"), "isoformat") else str(a.get("paid_at")),
            "prezzo": a.get("prezzo"),
            "last_error": (tx or {}).get("fattura_error"),
            "last_error_step": (tx or {}).get("fattura_error_step"),
            "paziente": {"user_id": a.get("paziente_user_id"), "nome": pu.get("nome") if pu else "", "cognome": pu.get("cognome") if pu else "", "email": pu.get("email") if pu else ""},
            "terapeuta": {"user_id": tu_id, "nome": tu.get("nome") if tu else "", "cognome": tu.get("cognome") if tu else ""},
        })

    # Refunded transactions without a nota di credito
    refunded = await db.payment_transactions.find({
        "$or": [{"payment_status": "refunded"}, {"is_refunded": True}, {"status": "refunded"}],
    }).sort("refunded_at", -1).limit(200).to_list(200)
    missing_nc = []
    for tx in refunded:
        appt_id = tx.get("appointment_id")
        if not appt_id:
            continue
        original = await db.fatture.find_one({"appuntamento_id": appt_id, "kind": "sanitaria"})
        if not original:
            continue  # Can't emit NC without a source invoice — surfaces in the fatture-missing list above
        nc_exists = await db.fatture.find_one({"kind": "nota_credito_sanitaria", "fattura_originale_id": str(original["_id"])})
        if nc_exists:
            continue
        pu = await db.users.find_one({"_id": ObjectId(tx["paziente_user_id"])}) if tx.get("paziente_user_id") else None
        missing_nc.append({
            "transaction_id": str(tx["_id"]),
            "appuntamento_id": appt_id,
            "fattura_id": str(original["_id"]),
            "fattura_numero": original.get("numero"),
            "refunded_at": tx.get("refunded_at").isoformat() if hasattr(tx.get("refunded_at"), "isoformat") else str(tx.get("refunded_at")),
            "paziente": {"user_id": tx.get("paziente_user_id"), "nome": pu.get("nome") if pu else "", "cognome": pu.get("cognome") if pu else "", "email": pu.get("email") if pu else ""},
            "importo": tx.get("amount", 0) / 100 if isinstance(tx.get("amount"), (int, float)) else 0,
        })
    return {
        "missing_count": len(missing),
        "checked_paid_count": len(paid_appts),
        "missing": missing,
        "missing_nc_count": len(missing_nc),
        "checked_refunded_count": len(refunded),
        "missing_nc": missing_nc,
    }


@router.post("/admin/fatture/generate-missing-nc")
async def admin_generate_missing_nc(admin: dict = Depends(require_admin)):
    """Emit nota di credito for every refunded transaction that doesn't have one yet,
    and email each PDF to the corresponding patient."""
    refunded = await db.payment_transactions.find({
        "$or": [{"payment_status": "refunded"}, {"is_refunded": True}, {"status": "refunded"}],
    }).sort("refunded_at", -1).limit(500).to_list(500)

    generated = []
    errors = []
    from email_service import send_signature_receipt_email
    from storage_service import get_object as _sto_get
    import base64
    for tx in refunded:
        appt_id = tx.get("appointment_id")
        if not appt_id:
            continue
        original = await db.fatture.find_one({"appuntamento_id": appt_id, "kind": "sanitaria"})
        if not original:
            continue
        nc_exists = await db.fatture.find_one({"kind": "nota_credito_sanitaria", "fattura_originale_id": str(original["_id"])})
        if nc_exists:
            continue
        try:
            nc = await _generate_nota_credito_paziente(
                str(original["_id"]),
                motivo=tx.get("refund_admin_note") or "Rimborso Stripe",
            )
            generated.append({"transaction_id": str(tx["_id"]), "numero": nc["numero"], "fattura_originale": original.get("numero")})
            # Email the patient the NC PDF
            pu = await db.users.find_one({"_id": ObjectId(tx["paziente_user_id"])})
            if pu and pu.get("email"):
                pdf_bytes = base64.b64decode(nc["pdf_inline_b64"]) if nc.get("pdf_inline_b64") else b""
                if not pdf_bytes and nc.get("pdf_storage_path"):
                    try:
                        pdf_bytes, _ = _sto_get(nc["pdf_storage_path"])
                    except Exception:
                        pdf_bytes = b""
                await send_signature_receipt_email(
                    email=pu["email"],
                    nome=pu.get("nome", ""),
                    doc_titles=[
                        f"Nota di Credito {nc['numero']} — storno fattura {original.get('numero','')}",
                        f"Importo stornato: € {abs(nc.get('importo_totale', 0)):.2f}",
                        "Conservala insieme alla fattura originale.",
                    ],
                    pdf_bytes=pdf_bytes,
                )
        except Exception as e:
            errors.append({"transaction_id": str(tx["_id"]), "error": str(e)[:300]})
    return {"generated_count": len(generated), "generated": generated, "errors_count": len(errors), "errors": errors}


@router.post("/admin/fatture/generate-missing")
async def admin_generate_missing_fatture(admin: dict = Depends(require_admin)):
    """Try to generate fatture sanitarie for ALL paid appointments that don't have one.
    Also emails each PDF to the corresponding patient (best-effort).
    Returns per-appointment success/error so the admin can see what still fails."""
    paid_appts = await db.appuntamenti.find({
        "stato": {"$in": PAID_APPT_STATES},
        "paid_at": {"$exists": True},
    }).sort("data_ora", -1).limit(500).to_list(500)

    from email_service import send_fattura_paziente_email
    from storage_service import get_object as _sto_get
    import base64

    async def _terapeuta_ctx(appt_doc: dict) -> tuple[str, str]:
        """(terapeuta_cognome, data_seduta_iso) enrichment for the branded email."""
        cognome = ""
        data_iso = (appt_doc or {}).get("data_ora") or ""
        try:
            if appt_doc and appt_doc.get("terapeuta_id"):
                t = await db.terapisti.find_one({"_id": ObjectId(appt_doc["terapeuta_id"])})
                if t:
                    cognome = t.get("cognome", "")
        except Exception as e:
            logger.warning(f"[GEN MISSING] enrich terapeuta failed: {e}")
        return cognome, data_iso

    generated = []
    errors = []
    for a in paid_appts:
        appt_id = str(a["_id"])
        existing = await db.fatture.find_one({"appuntamento_id": appt_id, "kind": "sanitaria"})
        if existing:
            continue
        try:
            f = await _generate_fattura_paziente(appt_id)
            generated.append({"appuntamento_id": appt_id, "numero": f.get("numero")})
            # Clear error on the linked tx
            await db.payment_transactions.update_one(
                {"appointment_id": appt_id},
                {"$set": {
                    "fattura_sanitaria_status": "emessa",
                    "fattura_id": str(f["_id"]),
                    "fattura_numero": f.get("numero"),
                    "fattura_emessa_at": datetime.now(timezone.utc),
                }, "$unset": {"fattura_error": "", "fattura_error_step": ""}},
            )
            # Email best-effort
            pu = await db.users.find_one({"_id": ObjectId(a["paziente_user_id"])}) if a.get("paziente_user_id") else None
            if pu and pu.get("email"):
                pdf_bytes = base64.b64decode(f["pdf_inline_b64"]) if f.get("pdf_inline_b64") else b""
                if not pdf_bytes and f.get("pdf_storage_path"):
                    try:
                        pdf_bytes, _ = _sto_get(f["pdf_storage_path"])
                    except Exception as e:
                        logger.warning(f"[GEN MISSING] storage fetch failed for {f.get('numero')}: {e}")
                terapeuta_cognome, data_seduta_iso = await _terapeuta_ctx(a)
                try:
                    ok, err_msg = await send_fattura_paziente_email(
                        paziente_email=pu["email"],
                        paziente_nome=pu.get("nome", ""),
                        terapeuta_cognome=terapeuta_cognome,
                        data_seduta_iso=data_seduta_iso,
                        fattura=f,
                        pdf_bytes=pdf_bytes,
                    )
                    if ok:
                        await db.fatture.update_one(
                            {"_id": f["_id"]},
                            {"$set": {"email_sent_at": datetime.now(timezone.utc)},
                             "$unset": {"email_error": ""}},
                        )
                    else:
                        await db.fatture.update_one(
                            {"_id": f["_id"]},
                            {"$set": {"email_error": err_msg or "send failed",
                                      "email_last_attempt_at": datetime.now(timezone.utc)}},
                        )
                except Exception as e:
                    logger.warning(f"[GEN MISSING] email send failed for {f.get('numero')}: {e}")
        except Exception as e:
            errors.append({"appuntamento_id": appt_id, "error": str(e)[:300]})
            # Persist error on the linked tx so it surfaces in diagnostics
            try:
                await db.payment_transactions.update_one(
                    {"appointment_id": appt_id},
                    {"$set": {
                        "fattura_error": str(e)[:500],
                        "fattura_error_step": "generate_fattura",
                        "fattura_error_at": datetime.now(timezone.utc),
                    }},
                )
            except Exception:
                pass
    return {"generated_count": len(generated), "generated": generated, "errors_count": len(errors), "errors": errors}


@router.post("/admin/fatture/retry/{appuntamento_id}")
async def admin_retry_fattura(appuntamento_id: str, admin: dict = Depends(require_admin)):
    """Per-row retry for a single paid appointment missing its fattura.

    Generates fattura + emails PDF to patient. Idempotent — if a fattura already
    exists it's returned as-is and the email is retried best-effort.
    """
    from email_service import send_fattura_paziente_email
    from storage_service import get_object as _sto_get
    import base64
    try:
        appt = await db.appuntamenti.find_one({"_id": ObjectId(appuntamento_id)})
    except Exception:
        raise HTTPException(400, "ID appuntamento non valido")
    if not appt:
        raise HTTPException(404, "Appuntamento non trovato")
    try:
        f = await _generate_fattura_paziente(appuntamento_id)
    except Exception as e:
        # Persist error on tx
        try:
            await db.payment_transactions.update_one(
                {"appointment_id": appuntamento_id},
                {"$set": {
                    "fattura_error": str(e)[:500],
                    "fattura_error_step": "generate_fattura",
                    "fattura_error_at": datetime.now(timezone.utc),
                }},
            )
        except Exception:
            pass
        raise HTTPException(422, str(e)[:400])

    pu = await db.users.find_one({"_id": ObjectId(appt["paziente_user_id"])}) if appt.get("paziente_user_id") else None
    email_sent = False
    if pu and pu.get("email"):
        pdf_bytes = base64.b64decode(f["pdf_inline_b64"]) if f.get("pdf_inline_b64") else b""
        if not pdf_bytes and f.get("pdf_storage_path"):
            try:
                pdf_bytes, _ = _sto_get(f["pdf_storage_path"])
            except Exception as e:
                logger.warning(f"[RETRY FATTURA] storage fetch failed: {e}")
        # Enrich terapeuta cognome + data seduta for the branded template
        terapeuta_cognome = ""
        data_seduta_iso = appt.get("data_ora") or ""
        if appt.get("terapeuta_id"):
            try:
                t = await db.terapisti.find_one({"_id": ObjectId(appt["terapeuta_id"])})
                if t:
                    terapeuta_cognome = t.get("cognome", "")
            except Exception:
                pass
        try:
            email_sent, err_msg = await send_fattura_paziente_email(
                paziente_email=pu["email"],
                paziente_nome=pu.get("nome", ""),
                terapeuta_cognome=terapeuta_cognome,
                data_seduta_iso=data_seduta_iso,
                fattura=f,
                pdf_bytes=pdf_bytes,
            )
            if email_sent:
                await db.fatture.update_one(
                    {"_id": f["_id"]},
                    {"$set": {"email_sent_at": datetime.now(timezone.utc)},
                     "$unset": {"email_error": ""}},
                )
            else:
                await db.fatture.update_one(
                    {"_id": f["_id"]},
                    {"$set": {"email_error": err_msg or "send failed",
                              "email_last_attempt_at": datetime.now(timezone.utc)}},
                )
        except Exception as e:
            logger.warning(f"[RETRY FATTURA] email send failed: {e}")

    await db.payment_transactions.update_one(
        {"appointment_id": appuntamento_id},
        {"$set": {
            "fattura_sanitaria_status": "emessa",
            "fattura_id": str(f["_id"]),
            "fattura_numero": f.get("numero"),
            "fattura_emessa_at": datetime.now(timezone.utc),
        }, "$unset": {"fattura_error": "", "fattura_error_step": ""}},
    )
    return {
        "numero": f.get("numero"),
        "id": str(f["_id"]),
        "email_sent": email_sent,
        "paziente_email": pu.get("email") if pu else None,
    }


async def _fetch_and_serve(fid: str, fmt: str, user: dict):
    """Return (fattura_doc, file_bytes) — single fetch, off-loop storage read."""
    try:
        f = await db.fatture.find_one({"_id": ObjectId(fid)})
    except Exception:
        raise HTTPException(400, "ID non valido")
    if not f:
        raise HTTPException(404, "Fattura non trovata")
    if user["role"] != "admin" and f.get("terapeuta_user_id") != user["_id"] and f.get("paziente_user_id") != user["_id"]:
        raise HTTPException(403, "Accesso negato")

    inline_key = f"{fmt}_inline_b64"
    path_key = f"{fmt}_storage_path"
    if f.get(inline_key):
        import base64
        return f, base64.b64decode(f[inline_key])
    if f.get(path_key):
        data, _ = await asyncio.to_thread(get_object, f[path_key])
        return f, data
    raise HTTPException(410, f"File {fmt.upper()} non disponibile")


@router.get("/fatture/{fid}/xml")
async def download_xml(fid: str, user: dict = Depends(require_auth)):
    f, data = await _fetch_and_serve(fid, "xml", user)
    return Response(content=data, media_type="application/xml", headers={
        "Content-Disposition": f'attachment; filename="{f.get("numero","fattura")}.xml"'
    })


@router.get("/fatture/{fid}/pdf")
async def download_pdf(fid: str, user: dict = Depends(require_auth)):
    f, data = await _fetch_and_serve(fid, "pdf", user)
    return Response(content=data, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{f.get("numero","fattura")}.pdf"'
    })


@router.post("/admin/fatture/generate/paziente/{appuntamento_id}")
async def admin_gen_sanitaria(appuntamento_id: str, admin: dict = Depends(require_admin)):
    try:
        doc = await _generate_fattura_paziente(appuntamento_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _serialize(doc)


@router.post("/admin/fatture/{fattura_id}/nota-credito")
async def admin_gen_nota_credito(fattura_id: str, admin: dict = Depends(require_admin)):
    """Manually emit a Nota di Credito (TD04) for a given fattura sanitaria.
    Normally triggered automatically by /admin/refunds — this endpoint is for
    manual/exceptional cases (e.g. refund done outside our platform)."""
    from fastapi import Body
    body_data = {}
    try:
        doc = await _generate_nota_credito_paziente(fattura_id, motivo="Storno manuale admin")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _serialize(doc)


@router.post("/admin/fatture/{fattura_id}/reinvia")
async def admin_reinvia_fattura(fattura_id: str, admin: dict = Depends(require_admin)):
    """Resend the fattura (sanitaria or NC) PDF via email to the patient.

    Explicit admin action → bypasses any prior `email_sent_at` flag: the admin
    is telling us "the patient says they didn't get it — send again", so we
    always retry even if a previous attempt succeeded.
    """
    try:
        oid = ObjectId(fattura_id)
    except Exception:
        raise HTTPException(400, "ID non valido")
    f = await db.fatture.find_one({"_id": oid})
    if not f:
        raise HTTPException(404, "Fattura non trovata")
    paziente = await db.users.find_one({"_id": ObjectId(f["paziente_user_id"])})
    if not paziente or not paziente.get("email"):
        raise HTTPException(400, "Email paziente mancante")

    # Load PDF: preferably from Object Storage, fallback to inline base64.
    import base64
    pdf_bytes = base64.b64decode(f["pdf_inline_b64"]) if f.get("pdf_inline_b64") else b""
    fetch_err = None
    if not pdf_bytes and f.get("pdf_storage_path"):
        from storage_service import get_object
        try:
            pdf_bytes, _ = get_object(f["pdf_storage_path"])
            logger.info(f"[REINVIA] numero={f['numero']} fetched PDF from storage bytes={len(pdf_bytes)}")
        except Exception as e:
            fetch_err = str(e)[:300]
            logger.error(f"[REINVIA] numero={f['numero']} failed to fetch PDF from storage: {e}")

    is_nc = f.get("kind") == "nota_credito_sanitaria"
    if is_nc:
        # Notes of credit still use the signature-receipt template for now —
        # they are rarer and the wording ("storno") is different enough.
        imp = abs(float(f.get("importo_totale", 0)))
        titles = [
            f"Nota di Credito {f['numero']} — storno fattura {f.get('fattura_originale_numero','')}",
            f"Importo stornato: € {imp:.2f}",
            "Conservala insieme alla fattura originale.",
        ]
        from email_service import send_signature_receipt_email
        ok = await send_signature_receipt_email(
            email=paziente["email"], nome=paziente.get("nome", ""),
            doc_titles=titles, pdf_bytes=pdf_bytes,
        )
        err_msg = "" if ok else "resend returned False"
    else:
        # Fattura sanitaria → dedicated branded template. Enrich with therapist
        # cognome + session date so subject and body are meaningful.
        terapeuta_cognome = ""
        data_seduta_iso = ""
        appt_id = f.get("appuntamento_id")
        if appt_id:
            try:
                appt = await db.appuntamenti.find_one({"_id": ObjectId(appt_id)})
                if appt:
                    data_seduta_iso = appt.get("data_ora") or ""
                    if appt.get("terapeuta_id"):
                        t = await db.terapisti.find_one({"_id": ObjectId(appt["terapeuta_id"])})
                        if t:
                            terapeuta_cognome = t.get("cognome", "")
            except Exception as e:
                logger.warning(f"[REINVIA] enrich terapeuta failed: {e}")
        from email_service import send_fattura_paziente_email
        ok, err_msg = await send_fattura_paziente_email(
            paziente_email=paziente["email"],
            paziente_nome=paziente.get("nome", ""),
            terapeuta_cognome=terapeuta_cognome,
            data_seduta_iso=data_seduta_iso,
            fattura=f,
            pdf_bytes=pdf_bytes,
        )

    now = datetime.now(timezone.utc)
    if not ok:
        await db.fatture.update_one(
            {"_id": oid},
            {"$set": {
                "email_error": (fetch_err or err_msg or "send failed")[:400],
                "email_last_attempt_at": now,
                "resent_by_admin": admin["_id"],
            }},
        )
        raise HTTPException(503, f"Invio email fallito: {err_msg or fetch_err or 'unknown'}")

    # Success — record the resend AND clear stale email_error / lift any
    # transaction-level fattura_error tied to this appt.
    await db.fatture.update_one(
        {"_id": oid},
        {"$set": {"resent_at": now, "email_sent_at": now, "resent_by_admin": admin["_id"]},
         "$unset": {"email_error": ""}},
    )
    if f.get("appuntamento_id"):
        await db.payment_transactions.update_one(
            {"appointment_id": f["appuntamento_id"]},
            {"$unset": {"fattura_error": "", "fattura_error_step": ""}},
        )
    return {
        "message": "Fattura reinviata",
        "email": paziente["email"],
        "numero": f["numero"],
        "attachment": bool(pdf_bytes),
    }



@router.post("/admin/fatture/generate/commissione/{year}/{month}")
async def admin_gen_commissione(year: int, month: int, admin: dict = Depends(require_admin)):
    if not (1 <= month <= 12):
        raise HTTPException(400, "Mese non valido")
    generated = await _generate_fatture_commissione_mensile(year, month)
    return {"generated": len(generated), "items": [_serialize(f) for f in generated]}
