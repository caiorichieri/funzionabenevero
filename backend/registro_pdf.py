"""Generate PDF for the Registro dei Trattamenti (GDPR Art. 30).

Produces a compliant PDF suitable for submission to the Garante Privacy
upon request, listing all active processing activities of BIDOC SRL.
"""
from io import BytesIO
from datetime import datetime, timezone
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
)


BIDOC_TITOLARE = {
    "denominazione": "BIDOC S.R.L.",
    "sede": "Via Mazzini, 62 — 33097 Spilimbergo (PN), Italia",
    "piva_cf": "01985930930",
    "rea": "PN-377600",
    "pec": "bidocsrl@pecimprese.it",
    "rappresentante": "Legale Rappresentante pro tempore",
    "email_privacy": "privacy@funzionabene.it",
    "marchio": "Funzionabene (www.funzionabene.it)",
}


def _p(text: str, style) -> Paragraph:
    """Escape XML then paragraph."""
    from html import escape
    return Paragraph(escape(str(text or "")).replace("\n", "<br/>"), style)


def generate_registro_pdf(entries: list, admin_name: str = "") -> bytes:
    """Return PDF bytes for the Registro dei Trattamenti."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=1.2 * cm, rightMargin=1.2 * cm,
        topMargin=1.2 * cm, bottomMargin=1.5 * cm,
        title="Registro dei Trattamenti — Art. 30 GDPR",
        author="BIDOC SRL",
    )
    ss = getSampleStyleSheet()
    style_h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=16, textColor=colors.HexColor("#0A0A0A"),
                              spaceAfter=6, alignment=TA_LEFT)
    style_h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=11, textColor=colors.HexColor("#F58A1F"),
                              spaceBefore=6, spaceAfter=4, alignment=TA_LEFT)
    style_body = ParagraphStyle("body", parent=ss["BodyText"], fontSize=9, leading=12,
                                textColor=colors.HexColor("#0A0A0A"), alignment=TA_LEFT)
    style_small = ParagraphStyle("small", parent=ss["BodyText"], fontSize=7.5, leading=10,
                                 textColor=colors.HexColor("#0A0A0A"), alignment=TA_LEFT)
    style_label = ParagraphStyle("label", parent=ss["BodyText"], fontSize=7, leading=9,
                                 textColor=colors.HexColor("#666666"), alignment=TA_LEFT)
    style_center = ParagraphStyle("center", parent=ss["BodyText"], fontSize=9, alignment=TA_CENTER,
                                  textColor=colors.HexColor("#666666"))

    story = []
    # Cover page
    story.append(Paragraph("REGISTRO DELLE ATTIVITÀ DI TRATTAMENTO", style_h1))
    story.append(Paragraph("Art. 30 Regolamento (UE) 2016/679 — GDPR", style_h2))
    story.append(Spacer(1, 0.5 * cm))

    story.append(Paragraph("Titolare del Trattamento", style_h2))
    header_data = [
        ["Denominazione", BIDOC_TITOLARE["denominazione"]],
        ["Sede legale", BIDOC_TITOLARE["sede"]],
        ["P.IVA / CF", BIDOC_TITOLARE["piva_cf"]],
        ["REA", BIDOC_TITOLARE["rea"]],
        ["PEC", BIDOC_TITOLARE["pec"]],
        ["Marchio", BIDOC_TITOLARE["marchio"]],
        ["Contatto privacy", BIDOC_TITOLARE["email_privacy"]],
        ["Rappresentante", BIDOC_TITOLARE["rappresentante"]],
    ]
    header_table = Table(header_data, colWidths=[4.5 * cm, 20 * cm])
    header_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#666666")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAFA")),
        ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E5E5")),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.4 * cm))

    now = datetime.now(timezone.utc)
    story.append(Paragraph(
        f"Data emissione: <b>{now.strftime('%d/%m/%Y %H:%M UTC')}</b> · "
        f"Voci attive: <b>{len(entries)}</b> · "
        f"Emesso da: <b>{admin_name or 'Amministratore'}</b>",
        style_body,
    ))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "Il presente Registro è predisposto ai sensi dell'art. 30 GDPR e viene tenuto in forma scritta e "
        "digitale. Viene messo a disposizione dell'Autorità di controllo (Garante per la protezione dei dati "
        "personali) su richiesta.",
        style_small,
    ))
    story.append(PageBreak())

    # Entries
    for idx, e in enumerate(entries, start=1):
        story.append(Paragraph(
            f"Voce {idx}/{len(entries)} — {e.get('codice','')} · {e.get('denominazione','')}",
            style_h1,
        ))
        story.append(Paragraph(f"Ruolo: <b>{(e.get('ruolo') or '').capitalize()}</b>", style_h2))

        rows = [
            ("Finalità del trattamento", e.get("finalita", "")),
            ("Base giuridica (art. 6 GDPR)", e.get("base_giuridica", "")),
            ("Categorie di interessati", e.get("categorie_interessati", "")),
            ("Categorie di dati personali", e.get("categorie_dati", "")),
            ("Categorie particolari (art. 9)", e.get("categorie_particolari", "") or "Nessuna"),
            ("Categorie di destinatari", e.get("destinatari", "") or "Nessuno"),
            ("Trasferimenti extra-UE (art. 44-49)", e.get("trasferimenti_extra_ue", "") or "Nessun trasferimento"),
            ("Misure di sicurezza (art. 32)", e.get("misure_sicurezza", "")),
            ("Termini di cancellazione", e.get("termini_cancellazione", "")),
        ]
        if e.get("note"):
            rows.append(("Note", e.get("note")))

        table_data = [[_p(k, style_label), _p(v, style_body)] for k, v in rows]
        table = Table(table_data, colWidths=[5.2 * cm, 19.3 * cm])
        table.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#FAFAFA")),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E5E5")),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#0A0A0A")),
        ]))
        story.append(table)
        if idx < len(entries):
            story.append(PageBreak())

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(
        "— Fine del Registro dei Trattamenti —",
        style_center,
    ))

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawString(1.2 * cm, 0.8 * cm, f"BIDOC SRL · Registro Trattamenti art. 30 GDPR · pag. {doc_.page}")
        canvas.drawRightString(A4[1] - 1.2 * cm, 0.8 * cm, now.strftime("Emesso il %d/%m/%Y %H:%M UTC"))
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
