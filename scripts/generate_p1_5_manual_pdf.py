from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "MANUAL_TECNICO_INTEGRACION_SENSORES_LORA_P1_5.md"
OUTPUT = ROOT / "output" / "pdf" / "AgroEscudo_Manual_Tecnico_Sensores_LoRa_P1_5.pdf"
LOGO = ROOT / "frontend" / "public" / "brand" / "logo-horizontal-transparent.png"
SHIELD = ROOT / "frontend" / "public" / "brand" / "shield-white.png"

GREEN_DARK = colors.HexColor("#064B35")
GREEN = colors.HexColor("#047857")
GREEN_SOFT = colors.HexColor("#EAF6F1")
AMBER = colors.HexColor("#C89116")
AMBER_SOFT = colors.HexColor("#FFF6DD")
INK = colors.HexColor("#24342F")
MUTED = colors.HexColor("#60746C")
LINE = colors.HexColor("#DDE7E2")
SOFT = colors.HexColor("#F8FAF9")
RED = colors.HexColor("#B42318")


def register_fonts() -> tuple[str, str]:
    regular = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    mono = Path("C:/Windows/Fonts/consola.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("AgroSans", str(regular)))
        pdfmetrics.registerFont(TTFont("AgroSansBold", str(bold)))
        if mono.exists():
            pdfmetrics.registerFont(TTFont("AgroMono", str(mono)))
        return "AgroSans", "AgroSansBold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_fonts()
MONO = "AgroMono" if "AgroMono" in pdfmetrics.getRegisteredFontNames() else "Courier"


def inline(text: str) -> str:
    value = escape(text)
    value = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", value)
    value = re.sub(r"`(.+?)`", r"<font name='%s'>\1</font>" % MONO, value)
    return value


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="ManualH1",
        fontName=FONT_BOLD,
        fontSize=18,
        leading=23,
        textColor=GREEN_DARK,
        spaceBefore=7 * mm,
        spaceAfter=3 * mm,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        name="ManualH2",
        fontName=FONT_BOLD,
        fontSize=11,
        leading=14,
        textColor=GREEN_DARK,
        spaceBefore=4 * mm,
        spaceAfter=2 * mm,
        keepWithNext=True,
    )
)
styles.add(
    ParagraphStyle(
        name="ManualBody",
        fontName=FONT,
        fontSize=9.1,
        leading=13.8,
        textColor=INK,
        spaceAfter=2.4 * mm,
    )
)
styles.add(
    ParagraphStyle(
        name="ManualBullet",
        parent=styles["ManualBody"],
        leftIndent=6 * mm,
        firstLineIndent=-3.5 * mm,
        bulletIndent=0,
        spaceAfter=1.3 * mm,
    )
)
styles.add(
    ParagraphStyle(
        name="ManualCallout",
        parent=styles["ManualBody"],
        backColor=AMBER_SOFT,
        borderColor=AMBER,
        borderWidth=0.8,
        borderPadding=4 * mm,
        spaceBefore=2 * mm,
        spaceAfter=4 * mm,
    )
)
styles.add(
    ParagraphStyle(
        name="ManualCode",
        fontName=MONO,
        fontSize=7.3,
        leading=10,
        textColor=colors.HexColor("#17362E"),
        backColor=SOFT,
        borderColor=LINE,
        borderWidth=0.5,
        borderPadding=3 * mm,
        leftIndent=0,
        rightIndent=0,
        spaceBefore=2 * mm,
        spaceAfter=4 * mm,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverTitle",
        fontName=FONT_BOLD,
        fontSize=26,
        leading=31,
        textColor=colors.white,
        alignment=TA_CENTER,
        spaceAfter=5 * mm,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverSub",
        fontName=FONT,
        fontSize=11,
        leading=16,
        textColor=colors.HexColor("#D6E7E1"),
        alignment=TA_CENTER,
        spaceAfter=4 * mm,
    )
)
styles.add(
    ParagraphStyle(
        name="TableHead",
        fontName=FONT_BOLD,
        fontSize=7.2,
        leading=9,
        textColor=colors.white,
        alignment=TA_LEFT,
    )
)
styles.add(
    ParagraphStyle(
        name="TableCell",
        fontName=FONT,
        fontSize=7.2,
        leading=9.3,
        textColor=INK,
    )
)


def draw_circuit(canvas, x: float, y: float, flip: bool = False) -> None:
    direction = -1 if flip else 1
    canvas.saveState()
    canvas.setStrokeColor(colors.Color(1, 1, 1, alpha=0.18))
    canvas.setFillColor(AMBER)
    canvas.setLineWidth(0.5)
    path = canvas.beginPath()
    path.moveTo(x, y)
    path.lineTo(x + direction * 16 * mm, y)
    path.lineTo(x + direction * 22 * mm, y + 7 * mm)
    path.lineTo(x + direction * 42 * mm, y + 7 * mm)
    canvas.drawPath(path)
    canvas.circle(x + direction * 42 * mm, y + 7 * mm, 1.2 * mm, fill=1, stroke=0)
    canvas.restoreState()


def cover_page(canvas, doc) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(GREEN_DARK)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#0B5A43"))
    canvas.circle(width - 10 * mm, height - 12 * mm, 72 * mm, fill=1, stroke=0)
    canvas.circle(8 * mm, 5 * mm, 60 * mm, fill=1, stroke=0)
    draw_circuit(canvas, 15 * mm, height - 24 * mm)
    draw_circuit(canvas, width - 15 * mm, 26 * mm, flip=True)
    canvas.setStrokeColor(AMBER)
    canvas.setLineWidth(2)
    canvas.line(65 * mm, 42 * mm, 145 * mm, 42 * mm)
    canvas.setFont(FONT, 8)
    canvas.setFillColor(colors.HexColor("#D6E7E1"))
    canvas.drawCentredString(width / 2, 31 * mm, "P1.5 - 24 JUL 2026 - AGROESCUDO")
    canvas.restoreState()


def body_page(canvas, doc) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, height - 14 * mm, width - 18 * mm, height - 14 * mm)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont(FONT_BOLD, 7.5)
    canvas.setFillColor(GREEN_DARK)
    canvas.drawString(18 * mm, height - 10 * mm, "AgroEscudo | Integración Sensor - LoRa - Plataforma")
    canvas.setFont(FONT, 7)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(width - 18 * mm, height - 10 * mm, "Manual técnico P1.5")
    canvas.drawString(18 * mm, 9 * mm, "Uso técnico para instalación y soporte de piloto")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"Página {doc.page}")
    canvas.restoreState()


def table_from_lines(lines: list[str]) -> Table:
    parsed = [[cell.strip() for cell in line.strip().strip("|").split("|")] for line in lines]
    if len(parsed) > 1 and all(re.fullmatch(r":?-{3,}:?", cell) for cell in parsed[1]):
        parsed.pop(1)
    columns = max(len(row) for row in parsed)
    for row in parsed:
        row.extend([""] * (columns - len(row)))
    usable = 174 * mm
    headers = [cell.lower() for cell in parsed[0]]
    if columns == 6 and "métrica" in headers:
        widths = [18 * mm, 25 * mm, 31 * mm, 48 * mm, 22 * mm, 30 * mm]
    elif columns == 2:
        widths = [45 * mm, 129 * mm]
    else:
        widths = [usable / columns] * columns
    converted = []
    for row_index, row in enumerate(parsed):
        style = styles["TableHead"] if row_index == 0 else styles["TableCell"]
        converted.append([Paragraph(inline(cell), style) for cell in row])
    table = Table(converted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN_DARK),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
                ("LEFTPADDING", (0, 0), (-1, -1), 2.2 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2.2 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
            ]
        )
    )
    return table


def image_flowable(relative_path: str) -> Image | None:
    path = (SOURCE.parent / relative_path).resolve()
    if not path.exists():
        return None
    image = Image(str(path))
    max_width = 170 * mm
    max_height = 105 * mm
    ratio = min(max_width / image.imageWidth, max_height / image.imageHeight)
    image.drawWidth = image.imageWidth * ratio
    image.drawHeight = image.imageHeight * ratio
    image.hAlign = "CENTER"
    return image


def parse_manual() -> list:
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    story: list = []
    index = 0
    in_code = False
    code_lines: list[str] = []
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            story.append(Paragraph(inline(" ".join(paragraph_lines)), styles["ManualBody"]))
            paragraph_lines = []

    while index < len(lines):
        line = lines[index].rstrip()
        stripped = line.strip()
        if stripped.startswith("```"):
            flush_paragraph()
            if in_code:
                story.append(Preformatted("\n".join(code_lines), styles["ManualCode"]))
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue
        if stripped.startswith("|"):
            flush_paragraph()
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index])
                index += 1
            story.append(table_from_lines(table_lines))
            story.append(Spacer(1, 3 * mm))
            continue
        image_match = re.fullmatch(r"!\[(.*?)\]\((.*?)\)", stripped)
        if image_match:
            flush_paragraph()
            image = image_flowable(image_match.group(2))
            if image:
                story.extend([image, Spacer(1, 3 * mm)])
            index += 1
            continue
        if stripped.startswith("## "):
            flush_paragraph()
            title = stripped[3:]
            if title.startswith("Estado de cierre"):
                story.append(PageBreak())
            story.append(Paragraph(inline(title), styles["ManualH1"]))
        elif stripped.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(inline(stripped[4:]), styles["ManualH2"]))
        elif stripped.startswith("# "):
            pass
        elif stripped.startswith("> "):
            flush_paragraph()
            story.append(Paragraph(inline(stripped[2:]), styles["ManualCallout"]))
        elif re.match(r"^\d+\.\s+", stripped):
            flush_paragraph()
            number, text = stripped.split(".", 1)
            story.append(
                Paragraph(
                    inline(text.strip()),
                    styles["ManualBullet"],
                    bulletText=f"{number}.",
                )
            )
        elif stripped.startswith("- ["):
            flush_paragraph()
            checked = stripped.startswith("- [x]") or stripped.startswith("- [X]")
            text = stripped[5:].strip()
            story.append(
                Paragraph(
                    inline(text),
                    styles["ManualBullet"],
                    bulletText="[x]" if checked else "[ ]",
                )
            )
        elif stripped.startswith("- "):
            flush_paragraph()
            story.append(
                Paragraph(inline(stripped[2:]), styles["ManualBullet"], bulletText="•")
            )
        elif not stripped:
            flush_paragraph()
        else:
            paragraph_lines.append(stripped)
        index += 1
    flush_paragraph()
    return story


def build() -> Path:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title="AgroEscudo - Manual técnico Sensor LoRa Plataforma P1.5",
        author="AgroEscudo",
        subject="Integración técnica para pilotos AgroEscudo",
    )
    cover = []
    if SHIELD.exists():
        shield = Image(str(SHIELD), width=56 * mm, height=56 * mm)
        shield.hAlign = "CENTER"
        cover.extend([Spacer(1, 22 * mm), shield, Spacer(1, 7 * mm)])
    elif LOGO.exists():
        logo = Image(str(LOGO), width=105 * mm, height=24 * mm)
        logo.hAlign = "CENTER"
        cover.extend([Spacer(1, 40 * mm), logo, Spacer(1, 12 * mm)])
    cover.extend(
        [
            Paragraph("Manual técnico de integración", styles["CoverTitle"]),
            Paragraph("Sensor - LoRa - Gateway - API - Base de datos - Gráficas", styles["CoverTitle"]),
            Paragraph(
                "Arquitectura, cableado, protocolo, firmware, migración, pruebas y operación de primer piloto",
                styles["CoverSub"],
            ),
            Spacer(1, 18 * mm),
            Paragraph(
                "Software verificado. Hardware, alcance LoRa y PostgreSQL productivo requieren validación controlada.",
                styles["CoverSub"],
            ),
            PageBreak(),
        ]
    )
    doc.build(cover + parse_manual(), onFirstPage=cover_page, onLaterPages=body_page)
    return OUTPUT


if __name__ == "__main__":
    print(build())
