from __future__ import annotations

from io import BytesIO

from app.models.schemas import ConversationResponse


def conversation_to_markdown(conv: ConversationResponse) -> str:
    lines: list[str] = [
        f"# {conv.title}",
        "",
        f"- 对话 ID：{conv.conversation_id}",
        f"- 创建时间：{conv.created_at.isoformat() if conv.created_at else '未知'}",
        f"- 消息数：{len(conv.messages)}",
        "",
        "---",
        "",
    ]

    for msg in conv.messages:
        role_label = "**用户**" if msg.role == "user" else "**智能客服**"
        lines.append(f"### {role_label}")
        lines.append("")
        lines.append(msg.content)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def _register_pdf_font() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont

    font_name = "STSong-Light"
    try:
        pdfmetrics.getFont(font_name)
    except KeyError:
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
    return font_name


def _draw_pdf_footer(canvas, doc, conv: ConversationResponse, font_name: str) -> None:
    from reportlab.lib import colors
    from reportlab.lib.units import mm

    page_width, _ = doc.pagesize
    footer_y = 10 * mm
    line_y = 14 * mm

    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#cbd2d9"))
    canvas.setLineWidth(0.5)
    canvas.line(doc.leftMargin, line_y, page_width - doc.rightMargin, line_y)

    canvas.setFont(font_name, 9)
    canvas.setFillColor(colors.HexColor("#52606d"))
    canvas.drawString(doc.leftMargin, footer_y, f"ApplianceRAG 智能客服 | {conv.conversation_id}")
    canvas.drawRightString(page_width - doc.rightMargin, footer_y, f"第 {canvas.getPageNumber()} 页")
    canvas.restoreState()


def conversation_to_pdf_bytes(conv: ConversationResponse) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    font_name = _register_pdf_font()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"{conv.title}.pdf",
    )

    base_styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ChatTitle",
        parent=base_styles["Title"],
        fontName=font_name,
        fontSize=22,
        leading=28,
        textColor=colors.HexColor("#16324f"),
        spaceAfter=8,
        wordWrap="CJK",
    )
    subtitle_style = ParagraphStyle(
        "ChatSubtitle",
        parent=base_styles["BodyText"],
        fontName=font_name,
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#4b5d73"),
        spaceAfter=10,
        wordWrap="CJK",
    )
    section_style = ParagraphStyle(
        "ChatSection",
        parent=base_styles["Heading2"],
        fontName=font_name,
        fontSize=13.5,
        leading=19,
        textColor=colors.HexColor("#0f4c5c"),
        spaceBefore=10,
        spaceAfter=6,
        wordWrap="CJK",
    )
    body_style = ParagraphStyle(
        "ChatBody",
        parent=base_styles["BodyText"],
        fontName=font_name,
        fontSize=10.5,
        leading=15,
        textColor=colors.HexColor("#222222"),
        spaceAfter=8,
        wordWrap="CJK",
    )

    from xml.sax.saxutils import escape as xml_escape

    def safe(text: str) -> str:
        return xml_escape(text).replace("\n", "<br/>")

    story = [
        Paragraph(f"对话记录：{safe(conv.title)}", title_style),
        Paragraph(
            f"对话 ID：{safe(conv.conversation_id)}<br/>"
            f"创建时间：{conv.created_at.isoformat() if conv.created_at else '未知'}<br/>"
            f"消息数：{len(conv.messages)}",
            subtitle_style,
        ),
        Spacer(1, 6),
    ]

    for msg in conv.messages:
        role_label = "用户" if msg.role == "user" else "智能客服"
        story.append(Paragraph(f"{role_label}：", section_style))
        story.append(Paragraph(safe(msg.content), body_style))
        story.append(Spacer(1, 3))

    def draw_footer(canvas, document) -> None:
        _draw_pdf_footer(canvas, document, conv, font_name)

    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return buffer.getvalue()
