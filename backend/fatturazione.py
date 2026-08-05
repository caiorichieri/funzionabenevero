"""FatturaPA v1.2.2 XML generator + PDF generator + numbering helper.

MVP con campi obbligatori dello schema Agenzia delle Entrate. Due tipi:
  - SANITARIA (esente IVA art. 10 DPR 633/72) — BIDOC emette in nome del terapeuta
  - COMMISSIONE B2B (BIDOC → terapeuta, IVA 22%)

Serie fatture: "FZ-YYYY-NNNN" atomica via db.fattura_counters.
"""
import logging
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from xml.etree import ElementTree as ET
from xml.dom import minidom

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)

# BIDOC SRL — cedente prestatore per le commissioni B2B, o "trasmittente" per fatture sanitarie
BIDOC = {
    "denominazione": "BIDOC SRL",
    "cf": "01985930930",
    "piva": "01985930930",
    "sede": {
        "indirizzo": "Via Mazzini, 62",
        "cap": "33097",
        "comune": "Spilimbergo",
        "provincia": "PN",
        "nazione": "IT",
    },
    "rea": {"ufficio": "PN", "numero": "377600"},
    "pec": "bidocsrl@pecimprese.it",
    "email": "info@bidoc.it",
    "regime_fiscale": "RF01",  # Ordinario
}

REGIME_FISCALE_MAP = {
    "forfettario": "RF19",
    "ordinario_esente": "RF01",
    "ordinario_iva": "RF01",
    "minimi": "RF02",
}

COMMISSIONE_PERCENT = Decimal("30.00")
IVA_COMMISSIONE = Decimal("22.00")
BOLLO_SOGLIA = Decimal("77.47")
BOLLO_IMPORTO = Decimal("2.00")


def _q(v) -> str:
    """Format money with 2 decimals as required by FatturaPA schema."""
    return str(Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def next_fattura_number(db, kind: str, year: int) -> str:
    """Atomic counter — returns 'FZ-{year}-{NNNN}' for sanitaria or 'CM-{year}-{NNNN}' for commissione."""
    prefix = "FZ" if kind == "sanitaria" else "CM"
    counter_key = f"{prefix}-{year}"
    result = await db.fattura_counters.find_one_and_update(
        {"_id": counter_key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    seq = result.get("seq") if result else 1
    return f"{prefix}-{year}-{seq:04d}"


# ─── XML FatturaPA v1.2.2 ────────────────────────────────────────────────────

NS = "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
NSMAP_ATTR = {
    "xmlns:p": "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2",
    "xmlns:ds": "http://www.w3.org/2000/09/xmldsig#",
    "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "xsi:schemaLocation": (
        "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2 "
        "https://www.fatturapa.gov.it/export/documenti/fatturapa/v1.2.2/Schema_del_file_xml_FatturaPA_versione_1.2.2.xsd"
    ),
    "versione": "FPR12",
}


def _add(parent, tag, text=None):
    el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = str(text)
    return el


def _build_common_header(root, cedente: dict, cessionario: dict, cedente_type: str, cessionario_type: str):
    hdr = _add(root, "FatturaElettronicaHeader")

    # DatiTrasmissione
    dt = _add(hdr, "DatiTrasmissione")
    idtx = _add(dt, "IdTrasmittente")
    _add(idtx, "IdPaese", "IT")
    _add(idtx, "IdCodice", BIDOC["piva"])
    _add(dt, "ProgressivoInvio", _now_utc().strftime("%y%m%d%H%M%S"))
    _add(dt, "FormatoTrasmissione", "FPR12")
    codice_dest = (cessionario.get("codice_sdi") or "").strip() or "0000000"
    _add(dt, "CodiceDestinatario", codice_dest[:7])
    if codice_dest == "0000000" and cessionario.get("pec"):
        _add(dt, "PECDestinatario", cessionario["pec"])

    # CedentePrestatore
    ced = _add(hdr, "CedentePrestatore")
    dati_ced = _add(ced, "DatiAnagrafici")
    idfisc = _add(dati_ced, "IdFiscaleIVA")
    _add(idfisc, "IdPaese", "IT")
    _add(idfisc, "IdCodice", cedente["piva"])
    if cedente.get("cf"):
        _add(dati_ced, "CodiceFiscale", cedente["cf"])
    ana = _add(dati_ced, "Anagrafica")
    if cedente_type == "azienda":
        _add(ana, "Denominazione", cedente["denominazione"])
    else:
        _add(ana, "Nome", cedente["nome"])
        _add(ana, "Cognome", cedente["cognome"])
    _add(dati_ced, "RegimeFiscale", cedente.get("regime_fiscale", "RF01"))
    sede = _add(ced, "Sede")
    _add(sede, "Indirizzo", cedente["sede"]["indirizzo"])
    _add(sede, "CAP", cedente["sede"]["cap"])
    _add(sede, "Comune", cedente["sede"]["comune"])
    if cedente["sede"].get("provincia"):
        _add(sede, "Provincia", cedente["sede"]["provincia"])
    _add(sede, "Nazione", cedente["sede"].get("nazione", "IT"))

    # CessionarioCommittente
    ces = _add(hdr, "CessionarioCommittente")
    dati_ces = _add(ces, "DatiAnagrafici")
    if cessionario_type == "privato":
        if cessionario.get("cf"):
            _add(dati_ces, "CodiceFiscale", cessionario["cf"])
        ana2 = _add(dati_ces, "Anagrafica")
        _add(ana2, "Nome", cessionario.get("nome", ""))
        _add(ana2, "Cognome", cessionario.get("cognome", ""))
    else:  # azienda / professionista con P.IVA
        idfisc2 = _add(dati_ces, "IdFiscaleIVA")
        _add(idfisc2, "IdPaese", "IT")
        _add(idfisc2, "IdCodice", cessionario["piva"])
        if cessionario.get("cf"):
            _add(dati_ces, "CodiceFiscale", cessionario["cf"])
        ana2 = _add(dati_ces, "Anagrafica")
        if cessionario_type == "azienda":
            _add(ana2, "Denominazione", cessionario.get("denominazione", ""))
        else:
            _add(ana2, "Nome", cessionario.get("nome", ""))
            _add(ana2, "Cognome", cessionario.get("cognome", ""))
    sede2 = _add(ces, "Sede")
    s = cessionario.get("sede") or {}
    _add(sede2, "Indirizzo", s.get("indirizzo", "N/D"))
    _add(sede2, "CAP", s.get("cap", "00000"))
    _add(sede2, "Comune", s.get("comune", "N/D"))
    if s.get("provincia"):
        _add(sede2, "Provincia", s["provincia"])
    _add(sede2, "Nazione", s.get("nazione", "IT"))


def _build_body(root, fattura: dict, natura: str = None, aliquota_iva: Decimal = Decimal("0.00"), bollo: bool = False):
    body = _add(root, "FatturaElettronicaBody")
    dg = _add(body, "DatiGenerali")
    dgd = _add(dg, "DatiGeneraliDocumento")
    _add(dgd, "TipoDocumento", "TD01")
    _add(dgd, "Divisa", "EUR")
    _add(dgd, "Data", fattura["data"])
    _add(dgd, "Numero", fattura["numero"])
    if bollo:
        db_el = _add(dgd, "DatiBollo")
        _add(db_el, "BolloVirtuale", "SI")
        _add(db_el, "ImportoBollo", _q(BOLLO_IMPORTO))
    _add(dgd, "ImportoTotaleDocumento", _q(fattura["totale"]))
    if fattura.get("causale"):
        _add(dgd, "Causale", fattura["causale"][:200])

    # DettaglioLinee
    dbb = _add(body, "DatiBeniServizi")
    for i, line in enumerate(fattura.get("linee", []), start=1):
        dl = _add(dbb, "DettaglioLinee")
        _add(dl, "NumeroLinea", str(i))
        _add(dl, "Descrizione", line["descrizione"][:1000])
        _add(dl, "Quantita", "1.00")
        _add(dl, "PrezzoUnitario", _q(line["prezzo"]))
        _add(dl, "PrezzoTotale", _q(line["prezzo"]))
        _add(dl, "AliquotaIVA", _q(aliquota_iva))
        if natura:
            _add(dl, "Natura", natura)

    # DatiRiepilogo
    dr = _add(dbb, "DatiRiepilogo")
    _add(dr, "AliquotaIVA", _q(aliquota_iva))
    if natura:
        _add(dr, "Natura", natura)
    imponibile = sum((Decimal(str(l["prezzo"])) for l in fattura.get("linee", [])), Decimal("0"))
    imposta = (imponibile * aliquota_iva / Decimal("100")).quantize(Decimal("0.01"))
    _add(dr, "ImponibileImporto", _q(imponibile))
    _add(dr, "Imposta", _q(imposta))
    if natura:
        _add(dr, "RiferimentoNormativo", "Prestazione sanitaria esente IVA art. 10 DPR 633/72 c.1 n.18")


def _prettify(root) -> bytes:
    """Serialize with correct namespace and pretty formatting."""
    root.set("versione", NSMAP_ATTR["versione"])
    root.set("xmlns:ds", NSMAP_ATTR["xmlns:ds"])
    root.set("xmlns:xsi", NSMAP_ATTR["xmlns:xsi"])
    root.set("xsi:schemaLocation", NSMAP_ATTR["xsi:schemaLocation"])
    rough = ET.tostring(root, encoding="utf-8")
    reparsed = minidom.parseString(rough)
    return reparsed.toprettyxml(indent="  ", encoding="UTF-8")


def generate_xml_sanitaria(*, numero: str, data: str, terapeuta: dict, paziente: dict, importo: Decimal, causale: str) -> bytes:
    """Genera XML FatturaPA per prestazione sanitaria (esente IVA art. 10)."""
    root = ET.Element("p:FatturaElettronica", {
        "xmlns:p": NSMAP_ATTR["xmlns:p"],
    })
    cedente = {
        "piva": terapeuta.get("partita_iva", ""),
        "cf": terapeuta.get("codice_fiscale", ""),
        "nome": terapeuta.get("nome", ""),
        "cognome": terapeuta.get("cognome", ""),
        "regime_fiscale": REGIME_FISCALE_MAP.get(terapeuta.get("regime_fiscale", "forfettario"), "RF19"),
        "sede": terapeuta.get("sede") or {"indirizzo": terapeuta.get("residenza_indirizzo", "N/D"),
                                            "cap": terapeuta.get("residenza_cap", "00000"),
                                            "comune": terapeuta.get("residenza_comune", "N/D"),
                                            "provincia": terapeuta.get("residenza_provincia", ""),
                                            "nazione": "IT"},
    }
    cessionario = {
        "cf": paziente.get("codice_fiscale", ""),
        "nome": paziente.get("nome", ""),
        "cognome": paziente.get("cognome", ""),
        "codice_sdi": "0000000",
        "sede": {
            "indirizzo": paziente.get("indirizzo", "N/D"),
            "cap": paziente.get("cap", "00000"),
            "comune": paziente.get("comune", "N/D"),
            "provincia": paziente.get("provincia", ""),
            "nazione": "IT",
        },
    }
    _build_common_header(root, cedente, cessionario, "professionista", "privato")
    bollo_needed = Decimal(str(importo)) >= BOLLO_SOGLIA
    _build_body(root,
                fattura={"numero": numero, "data": data, "totale": importo,
                         "linee": [{"descrizione": causale, "prezzo": importo}],
                         "causale": causale},
                natura="N4",  # esente
                aliquota_iva=Decimal("0.00"),
                bollo=bollo_needed)
    return _prettify(root)


def generate_xml_commissione(*, numero: str, data: str, terapeuta: dict, importo_imponibile: Decimal, causale: str) -> bytes:
    """Genera XML FatturaPA per commissione B2B BIDOC → Terapeuta (IVA 22%)."""
    root = ET.Element("p:FatturaElettronica", {
        "xmlns:p": NSMAP_ATTR["xmlns:p"],
    })
    cedente = {**BIDOC, "denominazione": BIDOC["denominazione"]}
    cessionario = {
        "piva": terapeuta.get("partita_iva", ""),
        "cf": terapeuta.get("codice_fiscale", ""),
        "nome": terapeuta.get("nome", ""),
        "cognome": terapeuta.get("cognome", ""),
        "codice_sdi": terapeuta.get("codice_sdi") or "0000000",
        "pec": terapeuta.get("pec", ""),
        "sede": terapeuta.get("sede") or {"indirizzo": terapeuta.get("residenza_indirizzo", "N/D"),
                                            "cap": terapeuta.get("residenza_cap", "00000"),
                                            "comune": terapeuta.get("residenza_comune", "N/D"),
                                            "provincia": terapeuta.get("residenza_provincia", ""),
                                            "nazione": "IT"},
    }
    imponibile = Decimal(str(importo_imponibile))
    imposta = (imponibile * IVA_COMMISSIONE / Decimal("100")).quantize(Decimal("0.01"))
    totale = imponibile + imposta
    _build_common_header(root, cedente, cessionario, "azienda", "professionista")
    _build_body(root,
                fattura={"numero": numero, "data": data, "totale": totale,
                         "linee": [{"descrizione": causale, "prezzo": imponibile}],
                         "causale": causale},
                natura=None,
                aliquota_iva=IVA_COMMISSIONE,
                bollo=False)
    return _prettify(root)


# ─── PDF leggibile ───────────────────────────────────────────────────────────


def generate_pdf(*, fattura: dict, cedente_display: dict, cessionario_display: dict, is_sanitaria: bool) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=1.8*cm, leftMargin=1.8*cm,
                             topMargin=1.8*cm, bottomMargin=1.8*cm,
                             title=f"Fattura {fattura['numero']}")
    styles = getSampleStyleSheet()
    body = ParagraphStyle('body', parent=styles['Normal'], fontSize=9, leading=12,
                          textColor=colors.HexColor('#0A0A0A'))
    small = ParagraphStyle('small', parent=styles['Normal'], fontSize=8,
                            textColor=colors.HexColor('#666'))
    title = ParagraphStyle('title', parent=styles['Heading1'], fontSize=16,
                            textColor=colors.HexColor('#0A0A0A'), alignment=TA_LEFT, spaceAfter=6)
    right = ParagraphStyle('right', parent=styles['Normal'], fontSize=9, alignment=TA_RIGHT)
    story = []

    story.append(Paragraph(f"<b>FATTURA {fattura['numero']}</b>", title))
    story.append(Paragraph(f"Data emissione: <b>{fattura['data']}</b>", body))
    story.append(Spacer(1, 0.6*cm))

    header_rows = [
        [Paragraph("<b>Emittente</b>", body), Paragraph("<b>Destinatario</b>", body)],
        [Paragraph(cedente_display, body), Paragraph(cessionario_display, body)],
    ]
    story.append(Table(header_rows, colWidths=[8.5*cm, 8.5*cm], style=TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOX', (0,0), (-1,-1), 0.3, colors.HexColor('#CCC')),
        ('INNERGRID', (0,0), (-1,-1), 0.3, colors.HexColor('#EEE')),
        ('LEFTPADDING', (0,0), (-1,-1), 8), ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8), ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ])))

    story.append(Spacer(1, 0.6*cm))

    # Linee
    rows = [["#", "Descrizione", "Importo €"]]
    for i, line in enumerate(fattura.get("linee", []), start=1):
        rows.append([str(i), line["descrizione"], _q(line["prezzo"])])
    story.append(Table(rows, colWidths=[1*cm, 12.5*cm, 3.5*cm], style=TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F0F0F0')),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (2,0), (2,-1), 'RIGHT'),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#CCC')),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 6), ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ])))

    story.append(Spacer(1, 0.4*cm))

    # Totali
    imponibile = fattura.get("imponibile", fattura.get("totale"))
    imposta = fattura.get("imposta", Decimal("0"))
    tot_rows = [
        ["Imponibile", f"€ {_q(imponibile)}"],
    ]
    if not is_sanitaria and Decimal(str(imposta)) > 0:
        tot_rows.append(["IVA 22%", f"€ {_q(imposta)}"])
    if is_sanitaria and Decimal(str(imponibile)) >= BOLLO_SOGLIA:
        tot_rows.append(["Marca da bollo €2 a carico del prestatore", "(virtuale)"])
    tot_rows.append([Paragraph("<b>TOTALE FATTURA</b>", body), Paragraph(f"<b>€ {_q(fattura['totale'])}</b>", right)])
    story.append(Table(tot_rows, colWidths=[13.5*cm, 3.5*cm], style=TableStyle([
        ('FONTSIZE', (0,0), (-1,-1), 9),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('LINEABOVE', (0,-1), (-1,-1), 1, colors.HexColor('#0A0A0A')),
        ('TOPPADDING', (0,-1), (-1,-1), 6), ('BOTTOMPADDING', (0,-1), (-1,-1), 6),
    ])))

    if is_sanitaria:
        story.append(Spacer(1, 0.5*cm))
        story.append(Paragraph(
            "Prestazione sanitaria esente IVA ai sensi dell'art. 10 c.1 n.18 DPR 633/72. "
            "Marca da bollo virtuale €2,00 assolta ove applicabile (art. 6 tabella B DPR 642/72).",
            small))

    if fattura.get("causale"):
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(f"<b>Causale:</b> {fattura['causale']}", small))

    doc.build(story)
    return buf.getvalue()
