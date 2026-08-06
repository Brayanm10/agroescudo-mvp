from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer

import generate_p1_5_manual_pdf as base


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "MANUAL_GATEWAY_SILO_CAMPO_ARDUINO_IDE.md"
OUTPUT = ROOT / "output" / "pdf" / "AgroEscudo_Manual_Gateway_SiloSensor_CampoSensor_Arduino_IDE.pdf"


def cover_page(canvas, doc) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(base.GREEN_DARK)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#0B5A43"))
    canvas.circle(width - 10 * mm, height - 12 * mm, 72 * mm, fill=1, stroke=0)
    canvas.circle(8 * mm, 5 * mm, 60 * mm, fill=1, stroke=0)
    base.draw_circuit(canvas, 15 * mm, height - 24 * mm)
    base.draw_circuit(canvas, width - 15 * mm, 26 * mm, flip=True)
    canvas.setStrokeColor(base.AMBER)
    canvas.setLineWidth(2)
    canvas.line(65 * mm, 42 * mm, 145 * mm, 42 * mm)
    canvas.setFont(base.FONT, 8)
    canvas.setFillColor(colors.HexColor("#D6E7E1"))
    canvas.drawCentredString(width / 2, 31 * mm, "FIRMWARE V4 - 06 AGO 2026 - AGROESCUDO")
    canvas.restoreState()


def body_page(canvas, doc) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setStrokeColor(base.LINE)
    canvas.setLineWidth(0.5)
    canvas.line(18 * mm, height - 14 * mm, width - 18 * mm, height - 14 * mm)
    canvas.line(18 * mm, 14 * mm, width - 18 * mm, 14 * mm)
    canvas.setFont(base.FONT_BOLD, 7.5)
    canvas.setFillColor(base.GREEN_DARK)
    canvas.drawString(18 * mm, height - 10 * mm, "AgroEscudo | Gateway - SiloSensor - CampoSensor")
    canvas.setFont(base.FONT, 7)
    canvas.setFillColor(base.MUTED)
    canvas.drawRightString(width - 18 * mm, height - 10 * mm, "Manual Arduino IDE V4")
    canvas.drawString(18 * mm, 9 * mm, "Instalacion, provisionamiento y operacion de firmware")
    canvas.drawRightString(width - 18 * mm, 9 * mm, f"Pagina {doc.page}")
    canvas.restoreState()


def build() -> Path:
    base.SOURCE = SOURCE
    base.OUTPUT = OUTPUT
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title="AgroEscudo - Manual Gateway, SiloSensor y CampoSensor",
        author="AgroEscudo",
        subject="Firmware estructurado para Arduino IDE y operacion de piloto",
    )
    cover = []
    if base.SHIELD.exists():
        shield = Image(str(base.SHIELD), width=56 * mm, height=56 * mm)
        shield.hAlign = "CENTER"
        cover.extend([Spacer(1, 22 * mm), shield, Spacer(1, 7 * mm)])
    cover.extend(
        [
            Paragraph("Manual de firmware AgroEscudo", base.styles["CoverTitle"]),
            Paragraph("Gateway multinodo, SiloSensor y CampoSensor", base.styles["CoverTitle"]),
            Paragraph(
                "Arduino IDE - LoRa V4 - AES-CCM - HTTPS firmado - telemetria por canal",
                base.styles["CoverSub"],
            ),
            Spacer(1, 18 * mm),
            Paragraph(
                "Software compilado. La instalacion fisica requiere prueba de banco, provisionamiento y validacion del sitio.",
                base.styles["CoverSub"],
            ),
            PageBreak(),
        ]
    )
    doc.build(cover + base.parse_manual(), onFirstPage=cover_page, onLaterPages=body_page)
    return OUTPUT


if __name__ == "__main__":
    print(build())
