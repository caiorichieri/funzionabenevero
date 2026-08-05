"""Generate the legally-binding PDF receipt (Ricevuta di Sottoscrizione) for a
Terapeuta signature of the Contratto di Collaborazione and related legal docs.

Uses ReportLab (already in requirements — invoice_pdf.py uses the same lib).
"""
from io import BytesIO
from datetime import datetime
from html import unescape
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
)


def _html_to_paragraphs(html: str, style) -> list:
    """Rough HTML → paragraphs. Preserves h1/h2/h3/p/strong/em/ul/li tags."""
    import re
    # Split by block-level tags
    txt = html
    # Convert <li> to bulleted text
    txt = re.sub(r'<li[^>]*>', '• ', txt, flags=re.IGNORECASE)
    txt = re.sub(r'</li>', '<br/>', txt, flags=re.IGNORECASE)
    # Headings become bold prefixes
    txt = re.sub(r'<h1[^>]*>', '<br/><b><font size="14">', txt, flags=re.IGNORECASE)
    txt = re.sub(r'</h1>', '</font></b><br/>', txt, flags=re.IGNORECASE)
    txt = re.sub(r'<h2[^>]*>', '<br/><b><font size="12">', txt, flags=re.IGNORECASE)
    txt = re.sub(r'</h2>', '</font></b><br/>', txt, flags=re.IGNORECASE)
    txt = re.sub(r'<h3[^>]*>', '<br/><b><font size="10">', txt, flags=re.IGNORECASE)
    txt = re.sub(r'</h3>', '</font></b><br/>', txt, flags=re.IGNORECASE)
    txt = re.sub(r'<p[^>]*>', '', txt, flags=re.IGNORECASE)
    txt = re.sub(r'</p>', '<br/><br/>', txt, flags=re.IGNORECASE)
    txt = re.sub(r'</?ul[^>]*>', '<br/>', txt, flags=re.IGNORECASE)
    txt = re.sub(r'</?ol[^>]*>', '<br/>', txt, flags=re.IGNORECASE)
    txt = re.sub(r'<hr[^/]*/?>', '<br/>_________________<br/>', txt, flags=re.IGNORECASE)
    # Split into chunks by double breaks
    parts = txt.split('<br/><br/>')
    paragraphs = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        try:
            paragraphs.append(Paragraph(part, style))
        except Exception:
            # Fallback: escape everything if ReportLab can't parse
            import html as _h
            paragraphs.append(Paragraph(_h.escape(part), style))
    return paragraphs


def generate_signature_receipt(
    *,
    terapeuta_data: dict,
    documents_signed: list,  # [{"kind": str, "title": str, "version": int, "hash": str, "content_html": str}]
    signature_name: str,
    timestamp: datetime,
    ip_address: str,
    user_agent: str,
) -> bytes:
    """Generate the PDF ricevuta. Returns raw PDF bytes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title="Ricevuta di Sottoscrizione",
        author="BIDOC SRL — Funzionabene",
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'],
        fontSize=18, textColor=colors.HexColor('#0A0A0A'),
        alignment=TA_CENTER, spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER, spaceAfter=20,
    )
    body_style = ParagraphStyle(
        'BodyStyle', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#0A0A0A'),
        alignment=TA_JUSTIFY, leading=12,
    )
    heading_style = ParagraphStyle(
        'HeadingStyle', parent=styles['Heading2'],
        fontSize=13, textColor=colors.HexColor('#0A0A0A'),
        spaceBefore=14, spaceAfter=6,
    )
    small_style = ParagraphStyle(
        'SmallStyle', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#666666'),
    )
    mono_style = ParagraphStyle(
        'MonoStyle', parent=styles['Normal'],
        fontSize=7, fontName='Courier',
        textColor=colors.HexColor('#333333'),
    )

    story = []

    # Header
    story.append(Paragraph("RICEVUTA DI SOTTOSCRIZIONE", title_style))
    story.append(Paragraph(
        "Documento probatorio ai sensi dell'art. 20 D.Lgs. 82/2005 (Codice Amministrazione Digitale)<br/>"
        "e del Regolamento (UE) 910/2014 (eIDAS)",
        subtitle_style,
    ))

    # Titolare
    story.append(Paragraph("Titolare / Piattaforma", heading_style))
    titolare_data = [
        ["Ragione sociale:", "BIDOC SRL"],
        ["Marchio commerciale:", "Funzionabene"],
        ["Sede legale:", "Via Mazzini, 62 — 33097 Spilimbergo (PN) — Italia"],
        ["P. IVA / C.F.:", "01985930930"],
        ["Iscrizione REA:", "PN-377600"],
        ["PEC:", "bidocsrl@pecimprese.it"],
        ["Email:", "info@bidoc.it"],
    ]
    story.append(Table(titolare_data, colWidths=[4.5 * cm, 12 * cm], style=TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#0A0A0A')),
    ])))

    # Sottoscrittore
    story.append(Paragraph("Sottoscrittore", heading_style))
    sub_data = [
        ["Nome:", f"{terapeuta_data.get('nome', '')} {terapeuta_data.get('cognome', '')}"],
        ["Codice Fiscale:", terapeuta_data.get('codice_fiscale', '—')],
        ["Partita IVA:", terapeuta_data.get('partita_iva', '—')],
        ["Email:", terapeuta_data.get('email', '—')],
        ["Telefono:", terapeuta_data.get('telefono', '—')],
        ["Iscrizione Ordine:", f"{terapeuta_data.get('albo_ordine', '—')} n. {terapeuta_data.get('albo_numero', '—')}"],
    ]
    story.append(Table(sub_data, colWidths=[4.5 * cm, 12 * cm], style=TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#0A0A0A')),
    ])))

    # Documenti sottoscritti
    story.append(Paragraph("Documenti Sottoscritti", heading_style))
    doc_rows = [["#", "Documento", "Versione", "Hash SHA-256"]]
    for i, d in enumerate(documents_signed, start=1):
        h = d.get('hash', '')
        doc_rows.append([str(i), d.get('title', d.get('kind', '')), f"v{d.get('version', 1)}", h])
    story.append(Table(doc_rows, colWidths=[0.7 * cm, 8 * cm, 1.8 * cm, 5.5 * cm], style=TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTNAME', (3, 1), (3, -1), 'Courier'),
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0F0F0')),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.HexColor('#CCCCCC')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ])))

    # Metadati di firma
    story.append(Paragraph("Metadati di Firma Elettronica", heading_style))
    meta_data = [
        ["Nome digitato:", signature_name],
        ["Timestamp UTC:", timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")],
        ["IP address:", ip_address or "—"],
        ["User-Agent:", (user_agent or "—")[:120]],
        ["Modalità:", "Firma elettronica ex art. 20 D.Lgs. 82/2005 — scroll obbligatorio + digitazione nome + verifica identità"],
    ]
    story.append(Table(meta_data, colWidths=[4.5 * cm, 12 * cm], style=TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#0A0A0A')),
    ])))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "<b>Dichiarazione probatoria.</b> Il presente documento attesta la sottoscrizione con firma elettronica "
        "dei documenti sopra elencati da parte del Sottoscrittore. La firma è idonea a soddisfare il requisito "
        "della forma scritta e ha valore probatorio liberamente valutabile in giudizio ai sensi dell'art. 20 "
        "del D.Lgs. 82/2005 e dell'art. 25 del Regolamento (UE) 910/2014. "
        "BIDOC SRL archivia questa ricevuta per un periodo di 10 anni.",
        body_style,
    ))

    # PAGINE SUCCESSIVE: contenuto integrale di ogni documento firmato
    for d in documents_signed:
        story.append(PageBreak())
        story.append(Paragraph(f"Allegato — {d.get('title', d.get('kind', ''))} v{d.get('version', 1)}", title_style))
        story.append(Paragraph(f"Hash SHA-256: {d.get('hash', '')}", small_style))
        story.append(Spacer(1, 0.4 * cm))
        for p in _html_to_paragraphs(d.get('content_html', ''), body_style):
            story.append(p)

    doc.build(story)
    return buf.getvalue()
