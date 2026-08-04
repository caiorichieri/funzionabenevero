"""Generate PDFs for fattura sanitaria (patient) and fattura commissione (BIDOC → therapist).
Italian fiscal compliance: esente IVA art. 10 DPR 633/72 c.1 n.18 (sanitaria);
IVA 22% (commissione B2B). Marca da bollo €2 for sanitarie ≥ €77,47.
"""
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
)


def _base_doc(buf: BytesIO) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title="Fattura FunzionaBene",
    )


def _fmt_eur(cents: int) -> str:
    return f"€ {cents / 100:.2f}".replace(".", ",")


def _issuer_therapist(t: dict) -> str:
    parts = [
        f"<b>Dott./ssa {t.get('nome','')} {t.get('cognome','')}</b>",
        f"Iscrizione Albo: {t.get('albo_numero','—')} · {t.get('albo_ordine','—')}",
        f"P.IVA: {t.get('partita_iva','—')} · C.F.: {t.get('codice_fiscale','—')}",
        f"{t.get('indirizzo','—')}",
    ]
    return "<br/>".join(parts)


def _issuer_bidoc() -> str:
    return "<br/>".join([
        "<b>BIDOC SRL</b>",
        "Via Mazzini, 62 · 33097 Spilimbergo (PN)",
        "P.IVA: 01985930930",
        "Marchio: <i>Funzionabene</i>",
    ])


def _recipient_paziente(p: dict, u: dict) -> str:
    return "<br/>".join([
        f"<b>{p.get('nome','')} {p.get('cognome','')}</b>",
        f"C.F.: {p.get('codice_fiscale','—')}",
        f"{p.get('indirizzo_residenza','—')}",
        f"Email: {u.get('email','—')}",
    ])


def _styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(name="Title2", fontName="Helvetica-Bold", fontSize=18, leading=22, spaceAfter=6))
    ss.add(ParagraphStyle(name="Small", fontName="Helvetica", fontSize=9, leading=12, textColor=colors.grey))
    ss.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=10, leading=14))
    return ss


def build_fattura_sanitaria_pdf(*, tx: dict, appt: dict, terapista: dict, paziente: dict, paziente_user: dict) -> bytes:
    """PDF of a fattura sanitaria (exempt IVA), emitted by therapist to patient.
    BIDOC's role indicated as 'mandato all'incasso'."""
    buf = BytesIO()
    doc = _base_doc(buf)
    ss = _styles()
    story = []

    story.append(Paragraph("FATTURA SANITARIA", ss["Title2"]))
    story.append(Paragraph(
        f"N. FS-{tx.get('invoice_number', str(tx.get('_id',''))[:10])}  ·  "
        f"Data: {(tx.get('paid_at') or datetime.now()).strftime('%d/%m/%Y')}",
        ss["Small"]
    ))
    story.append(Spacer(1, 0.5 * cm))

    header_table = Table([
        [Paragraph("<b>PRESTATORE</b>", ss["Body"]), Paragraph("<b>PAZIENTE</b>", ss["Body"])],
        [Paragraph(_issuer_therapist(terapista), ss["Body"]),
         Paragraph(_recipient_paziente(paziente, paziente_user), ss["Body"])],
    ], colWidths=[8.5 * cm, 8.5 * cm])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.6 * cm))

    amount = tx.get("amount", 0)
    bollo_amount = tx.get("marca_da_bollo_amount", 0)
    total = amount  # patient paid gross; bollo is a cost of the professional
    data_ora = appt.get("data_ora", "")
    if isinstance(data_ora, str) and "T" in data_ora:
        try: data_ora = datetime.fromisoformat(data_ora.replace("Z","")).strftime("%d/%m/%Y %H:%M")
        except Exception: pass

    rows = [
        ["Descrizione", "Data", "Importo"],
        [f"Sessione di psicoterapia/sessuologia\n({appt.get('durata_minuti',50)}' · {appt.get('modalita','classica')})",
         str(data_ora), _fmt_eur(amount)],
    ]
    body_table = Table(rows, colWidths=[10 * cm, 3.5 * cm, 3.5 * cm])
    body_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F4CB78")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#0A0A0A")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#0A0A0A")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(body_table)
    story.append(Spacer(1, 0.4 * cm))

    totals_rows = [["Totale prestazione", _fmt_eur(amount)]]
    if bollo_amount:
        totals_rows.append(["Marca da bollo €2 (a carico del prestatore)", _fmt_eur(bollo_amount)])
    totals_rows.append(["TOTALE PAGATO DAL PAZIENTE", _fmt_eur(total)])
    tt = Table(totals_rows, colWidths=[13 * cm, 4 * cm])
    tt.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.HexColor("#0A0A0A")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tt)
    story.append(Spacer(1, 0.8 * cm))

    story.append(Paragraph(
        "<i>Prestazione sanitaria esente IVA ex art. 10 DPR 633/72 c.1 n.18.</i><br/>"
        + ("<i>Marca da bollo €2,00 assolta virtualmente ex DM 17/06/2014.</i><br/>" if bollo_amount else "")
        + ("<i>Il paziente ha esercitato l'opposizione all'invio dei dati al Sistema TS (art. 3 D.M. 31/07/2015).</i><br/>" if tx.get("opposizione_ts") else "")
        + "Pagamento incassato da BIDOC SRL in mandato all'incasso con rappresentanza per conto del prestatore.",
        ss["Small"],
    ))
    doc.build(story)
    return buf.getvalue()


def build_fattura_commissione_pdf(*, terapista: dict, transactions: list, year: int, month: int) -> bytes:
    """PDF of BIDOC's monthly commission invoice (30% + 22% IVA) to the therapist."""
    buf = BytesIO()
    doc = _base_doc(buf)
    ss = _styles()
    story = []

    story.append(Paragraph("FATTURA DI COMMISSIONE", ss["Title2"]))
    story.append(Paragraph(
        f"N. FC-{year}{month:02d}-{str(terapista.get('_id',''))[:6]}  ·  "
        f"Periodo: {month:02d}/{year}",
        ss["Small"]
    ))
    story.append(Spacer(1, 0.5 * cm))

    header = Table([
        [Paragraph("<b>EMITTENTE</b>", ss["Body"]), Paragraph("<b>DESTINATARIO</b>", ss["Body"])],
        [Paragraph(_issuer_bidoc(), ss["Body"]),
         Paragraph(_issuer_therapist(terapista), ss["Body"])],
    ], colWidths=[8.5 * cm, 8.5 * cm])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, 0), 8)]))
    story.append(header)
    story.append(Spacer(1, 0.6 * cm))

    rows = [["Data sessione", "Paziente (iniziali)", "Importo lordo", "Commissione (30%)"]]
    tot_commission_cents = 0
    for tx in transactions:
        raw_date = tx.get("paid_at") or tx.get("created_at")
        date_str = raw_date.strftime("%d/%m/%Y") if hasattr(raw_date, "strftime") else str(raw_date or "")[:10]
        initials = (tx.get("paziente_initials") or "—")
        rows.append([date_str, initials, _fmt_eur(tx.get("amount", 0)), _fmt_eur(tx.get("platform_fee_amount", 0))])
        tot_commission_cents += tx.get("platform_fee_amount", 0)

    body_table = Table(rows, colWidths=[3 * cm, 4 * cm, 5 * cm, 5 * cm])
    body_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F4CB78")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#0A0A0A")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#0A0A0A")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(body_table)
    story.append(Spacer(1, 0.5 * cm))

    iva_cents = int(round(tot_commission_cents * 0.22))
    total_cents = tot_commission_cents + iva_cents
    tt = Table([
        ["Imponibile (30% delle sessioni)", _fmt_eur(tot_commission_cents)],
        ["IVA 22%", _fmt_eur(iva_cents)],
        ["TOTALE DOVUTO", _fmt_eur(total_cents)],
    ], colWidths=[13 * cm, 4 * cm])
    tt.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LINEABOVE", (0, -1), (-1, -1), 0.75, colors.HexColor("#0A0A0A")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(tt)
    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(
        "<i>Servizi di intermediazione tecnica e finanziaria (mandato all'incasso con rappresentanza). "
        "Fattura emessa ex art. 21 DPR 633/72. Pagamento tramite compensazione sul rimborso delle sessioni.</i>",
        ss["Small"],
    ))
    doc.build(story)
    return buf.getvalue()
