"""Generate the monthly executive Cruscotto PDF report for BIDOC direction.

Layout: KPI header, revenue delta, sessions & completion, 6-month revenue table
+ inline bar chart (Drawing), Top 5 therapists, IBAN-missing alert.
"""
from io import BytesIO
from datetime import datetime, timezone

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart


ACCENT = colors.HexColor("#6B8FA3")
INK = colors.HexColor("#0A0A0A")
MUTED = colors.HexColor("#6B7280")
CARD_BG = colors.HexColor("#F5F5F0")
DANGER = colors.HexColor("#B91C1C")
DANGER_BG = colors.HexColor("#FEE2E2")


def _fmt_eur(cents: int) -> str:
    return f"€ {(cents or 0) / 100:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _build_styles():
    ss = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=ss["Heading1"], fontSize=22, textColor=INK, spaceAfter=4),
        "sub": ParagraphStyle("sub", parent=ss["Normal"], fontSize=10, textColor=MUTED, spaceAfter=14),
        "h2": ParagraphStyle("h2", parent=ss["Heading2"], fontSize=14, textColor=INK, spaceAfter=6, spaceBefore=12),
        "body": ParagraphStyle("body", parent=ss["Normal"], fontSize=10, textColor=INK, leading=14),
        "kpi_label": ParagraphStyle("kpi_label", parent=ss["Normal"], fontSize=9, textColor=MUTED),
        "kpi_value": ParagraphStyle("kpi_value", parent=ss["Normal"], fontSize=16, textColor=INK, leading=20),
        "kpi_sub": ParagraphStyle("kpi_sub", parent=ss["Normal"], fontSize=8, textColor=MUTED, leading=10),
        "danger": ParagraphStyle("danger", parent=ss["Normal"], fontSize=10, textColor=DANGER, leading=14),
    }


def _kpi_cell(styles, label: str, value: str, sub: str = ""):
    lines = [Paragraph(label, styles["kpi_label"]),
             Paragraph(f"<b>{value}</b>", styles["kpi_value"])]
    if sub:
        lines.append(Paragraph(sub, styles["kpi_sub"]))
    return lines


def _build_bar_chart(revenue_6m):
    """Bar chart of gross revenue (in €) over the last 6 months."""
    d = Drawing(16 * cm, 6 * cm)
    values = [round((m.get("gross_cents", 0) or 0) / 100) for m in revenue_6m]
    labels = [m.get("label", "") for m in revenue_6m]

    chart = VerticalBarChart()
    chart.x = 40
    chart.y = 20
    chart.height = 5 * cm
    chart.width = 14 * cm
    chart.data = [values]
    chart.categoryAxis.categoryNames = labels
    chart.categoryAxis.labels.fontSize = 9
    chart.valueAxis.valueMin = 0
    if max(values) > 0:
        chart.valueAxis.valueMax = max(values) * 1.2
        chart.valueAxis.valueStep = max(1, round(max(values) / 4))
    else:
        chart.valueAxis.valueMax = 100
        chart.valueAxis.valueStep = 25
    chart.valueAxis.labels.fontSize = 9
    chart.bars[0].fillColor = ACCENT
    chart.bars[0].strokeColor = None
    chart.barSpacing = 4
    chart.groupSpacing = 12
    d.add(chart)
    return d


def build_cruscotto_pdf(data: dict) -> bytes:
    buf = BytesIO()
    now = datetime.now(timezone.utc)
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=1.8 * cm, bottomMargin=1.8 * cm,
        title=f"Cruscotto FunzionaBene {now.strftime('%Y-%m')}",
    )
    styles = _build_styles()
    story = []

    # Header
    story.append(Paragraph("Cruscotto Direzionale", styles["h1"]))
    story.append(Paragraph(
        f"FunzionaBene · BIDOC SRL · Report al {now.strftime('%d/%m/%Y %H:%M UTC')}",
        styles["sub"],
    ))

    # KPI grid (2x2)
    rev = data.get("revenue", {})
    cur = rev.get("current_month", {})
    prev = rev.get("previous_month", {})
    pending = data.get("pending_payouts", {})
    sessions = data.get("sessions_month", {})

    delta = rev.get("delta_percent")
    delta_str = (
        f"{'+' if (delta or 0) >= 0 else ''}{delta}% vs mese scorso" if delta is not None else "vs mese scorso: n/d"
    )

    kpi_data = [
        [
            _kpi_cell(styles, "Fatturato Mese Corrente", _fmt_eur(cur.get("gross_cents", 0)), delta_str),
            _kpi_cell(styles, "Payout Pendenti (70%)", _fmt_eur(pending.get("total_cents", 0)),
                      f"{pending.get('count', 0)} transazioni da bonificare"),
        ],
        [
            _kpi_cell(styles, "Sessioni Mese",
                      f"{sessions.get('completed', 0)} / {sessions.get('booked', 0)}",
                      f"Tasso completamento: {sessions.get('completion_rate', 0)}%"),
            _kpi_cell(styles, "Fatturato Mese Precedente", _fmt_eur(prev.get("gross_cents", 0)),
                      f"{prev.get('count', 0)} transazioni"),
        ],
    ]
    kpi_table = Table(kpi_data, colWidths=[8.5 * cm, 8.5 * cm])
    kpi_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), CARD_BG),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(kpi_table)

    # Revenue 6M chart
    story.append(Paragraph("Ricavi Ultimi 6 Mesi (incassi lordi)", styles["h2"]))
    story.append(_build_bar_chart(data.get("revenue_6m", [])))

    # 6M table
    rev6 = data.get("revenue_6m", [])
    table_data = [["Mese", "Sessioni", "Ricavi lordi"]]
    for m in rev6:
        table_data.append([m.get("label", ""), str(m.get("count", 0)), _fmt_eur(m.get("gross_cents", 0))])
    rev_table = Table(table_data, colWidths=[5 * cm, 4 * cm, 5 * cm])
    rev_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), ACCENT),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 0), (2, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(rev_table)

    # Top 5 therapists
    story.append(Paragraph("Top 5 Terapisti (ricavi all-time)", styles["h2"]))
    top = data.get("top_therapists", [])
    if top:
        top_data = [["#", "Terapista", "Sessioni", "Ricavi lordi"]]
        for i, t in enumerate(top, 1):
            top_data.append([str(i), t.get("nome", "—"), str(t.get("sessions", 0)), _fmt_eur(t.get("gross_cents", 0))])
        top_table = Table(top_data, colWidths=[1 * cm, 8 * cm, 3 * cm, 4 * cm])
        top_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), INK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (2, 0), (3, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
            ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#E5E7EB")),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(top_table)
    else:
        story.append(Paragraph("Nessun dato disponibile.", styles["body"]))

    # IBAN alerts
    iban_missing = data.get("iban_missing", [])
    if iban_missing:
        story.append(Paragraph(f"⚠ IBAN Mancante ({len(iban_missing)} terapisti)", styles["h2"]))
        story.append(Paragraph(
            "I seguenti professionisti hanno sessioni pagate da bonificare ma non hanno un IBAN registrato.",
            styles["danger"],
        ))
        story.append(Spacer(1, 6))
        iban_data = [["Terapista", "Sessioni", "Da bonificare"]]
        for row in iban_missing:
            iban_data.append([
                row.get("nome", "—"),
                str(row.get("sessions", 0)),
                _fmt_eur(row.get("pending_cents", 0)),
            ])
        it = Table(iban_data, colWidths=[9 * cm, 3 * cm, 4 * cm])
        it.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), DANGER),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ALIGN", (1, 0), (2, -1), "RIGHT"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, DANGER_BG]),
            ("BOX", (0, 0), (-1, -1), 0.5, DANGER),
            ("INNERGRID", (0, 0), (-1, -1), 0.25, DANGER),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(it)

    # Footer note
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "Report generato automaticamente da FunzionaBene · BIDOC SRL · funzionabene.it",
        ParagraphStyle("footer", fontSize=7, textColor=MUTED, alignment=1),
    ))

    doc.build(story)
    return buf.getvalue()
