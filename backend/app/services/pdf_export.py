"""
Renders an AIReport as a downloadable PDF — the same data the API
already returns as JSON, laid out for someone to save or hand to another
investor outside the platform. Uses reportlab's platypus (high-level
flowables: Paragraph, Table, Spacer) rather than raw canvas drawing, so
layout/pagination is handled automatically instead of manually placed.

Deliberately mirrors the API response exactly — same scores, same flags,
same citation_verified markers — rather than a prettied-up summary that
could drift from what's actually stored and auditable.
"""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    ListFlowable,
    ListItem,
)

from app import models

_styles = getSampleStyleSheet()
_TITLE = ParagraphStyle("ReportTitle", parent=_styles["Title"], fontSize=18, spaceAfter=4)
_META = ParagraphStyle("Meta", parent=_styles["Normal"], fontSize=9, textColor=colors.grey, spaceAfter=12)
_H2 = ParagraphStyle("H2", parent=_styles["Heading2"], fontSize=12, spaceBefore=14, spaceAfter=6)
_BODY = ParagraphStyle("Body", parent=_styles["Normal"], fontSize=10, leading=14)
_EVIDENCE = ParagraphStyle("Evidence", parent=_styles["Normal"], fontSize=8.5, textColor=colors.grey, leading=11, spaceAfter=8)
_DISCLAIMER = ParagraphStyle("Disclaimer", parent=_styles["Normal"], fontSize=8, textColor=colors.grey, leading=11)


def _score_table(report: models.AIReport) -> Table:
    labels = [
        ("Overall", report.overall_score), ("Financial", report.financial_health_score),
        ("Growth", report.growth_score), ("Profitability", report.profitability_score),
        ("Governance", report.governance_score), ("Moat", report.moat_score),
        ("Valuation", report.valuation_score), ("Risk", report.risk_score),
    ]
    header = [label for label, _ in labels]
    values = [str(v) if v is not None else "—" for _, v in labels]
    table = Table([header, values], colWidths=[55] * len(labels))
    table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.grey),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 4),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
                ("TOPPADDING", (0, 1), (-1, 1), 4),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 12),
            ]
        )
    )
    return table


def _flag_flowables(title: str, flags: list) -> list:
    if not flags:
        return []
    elements = [Paragraph(title, _H2)]
    for flag in flags:
        citation = (
            f"p.{flag.get('page_number')}" if flag.get("source_type") == "document"
            else flag.get("period") or "—"
        )
        verified = "verified" if flag.get("citation_verified") else "UNVERIFIED — treat with caution"
        elements.append(Paragraph(f"&#8226; {flag['statement']}", _BODY))
        elements.append(
            Paragraph(f"{flag['evidence']} &nbsp;&mdash;&nbsp; [{citation}, {verified}]", _EVIDENCE)
        )
    return elements


def _text_list_flowables(title: str, items: list) -> list:
    if not items:
        return []
    return [
        Paragraph(title, _H2),
        ListFlowable(
            [ListItem(Paragraph(item, _BODY), bulletColor=colors.grey) for item in items],
            bulletType="bullet",
        ),
    ]


def generate_ai_report_pdf(report: models.AIReport, company: models.Company) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm, leftMargin=20 * mm, rightMargin=20 * mm,
    )

    story = [
        Paragraph(f"{company.name} ({company.symbol})", _TITLE),
        Paragraph(
            f"AI analysis generated {report.generated_at:%d %b %Y, %H:%M} &middot; "
            f"{report.llm_provider}/{report.llm_model} &middot; "
            f"confidence {float(report.confidence_score) * 100:.0f}%",
            _META,
        ),
        _score_table(report),
        Spacer(1, 10),
        Paragraph("Summary", _H2),
        Paragraph(report.summary, _BODY),
    ]

    story += _flag_flowables("Green flags", report.green_flags)
    story += _flag_flowables("Red flags", report.red_flags)
    story += _text_list_flowables("Questions investors should ask", report.questions_investors_should_ask)
    story += _text_list_flowables("Things to verify", report.things_to_verify)
    story += _text_list_flowables("Potential risks", report.potential_risks)

    story.append(Spacer(1, 16))
    story.append(
        Paragraph(
            "This is an evidence-based analysis tool, not investment advice. It does not "
            "recommend buying or selling any security. Citations marked UNVERIFIED could not "
            "be matched against the data the model was given for this report and should be "
            "checked independently before being relied on.",
            _DISCLAIMER,
        )
    )

    doc.build(story)
    return buffer.getvalue()
