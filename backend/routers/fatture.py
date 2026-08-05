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
    generate_pdf,
    COMMISSIONE_PERCENT, IVA_COMMISSIONE, BOLLO_SOGLIA, BIDOC,
)
from object_storage import put_object, get_object

logger = logging.getLogger(__name__)
router = APIRouter()


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
    terapeuta = await _get_terapeuta_full(appt.get("terapeuta_user_id"))
    if not terapeuta:
        raise ValueError("Terapeuta non trovato")
    if not (terapeuta.get("partita_iva") and terapeuta.get("codice_fiscale")):
        raise ValueError("Dati fiscali terapeuta incompleti (P.IVA/CF)")
    paziente = await _get_paziente_full(appt.get("paziente_user_id"))

    importo = Decimal(str(appt.get("prezzo", terapeuta.get("tariffa", 70))))
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
        "terapeuta_user_id": appt.get("terapeuta_user_id"),
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
    tera_ids = await db.appuntamenti.distinct("terapeuta_user_id", {
        "stato": {"$in": ["completato", "confermato"]},
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
            "stato": {"$in": ["completato", "confermato"]},
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
                              "Via Mazzini 62, 33097 Spilimbergo (PN)<br/>PEC bidocsrl@pecimprese.it"),
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
    if kind in ("sanitaria", "commissione"):
        q["kind"] = kind
    items = []
    async for f in db.fatture.find(q).sort("created_at", -1).limit(2000):
        items.append(_serialize(f))
    return {"items": items, "count": len(items)}


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


@router.post("/admin/fatture/generate/commissione/{year}/{month}")
async def admin_gen_commissione(year: int, month: int, admin: dict = Depends(require_admin)):
    if not (1 <= month <= 12):
        raise HTTPException(400, "Mese non valido")
    generated = await _generate_fatture_commissione_mensile(year, month)
    return {"generated": len(generated), "items": [_serialize(f) for f in generated]}
