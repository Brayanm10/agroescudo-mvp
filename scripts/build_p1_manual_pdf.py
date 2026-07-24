from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "AgroEscudo_Manual_Usuario_Servicio_Piloto.pdf"
LOGO = ROOT / "frontend" / "public" / "brand" / "logo-horizontal-transparent.png"
SHIELD_WHITE = ROOT / "frontend" / "public" / "brand" / "shield-white.png"

GREEN_DARK = colors.HexColor("#053F31")
GREEN = colors.HexColor("#075B44")
GREEN_LIGHT = colors.HexColor("#E8F7F0")
AMBER = colors.HexColor("#C89116")
AMBER_LIGHT = colors.HexColor("#FFF4D6")
INK = colors.HexColor("#16352D")
MUTED = colors.HexColor("#62756F")
LINE = colors.HexColor("#DDE7E2")
FIELD = colors.HexColor("#F7FAF8")
RED = colors.HexColor("#B42318")
RED_LIGHT = colors.HexColor("#FFEBE9")


def register_fonts() -> tuple[str, str]:
    regular = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("AgroSans", str(regular)))
        pdfmetrics.registerFont(TTFont("AgroSansBold", str(bold)))
        return "AgroSans", "AgroSansBold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_fonts()


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def bullets(items: list[str], styles: dict[str, ParagraphStyle]) -> list:
    flowables: list = []
    for item in items:
        flowables.append(
            Table(
                [
                    [
                        paragraph(">", styles["bullet_mark"]),
                        paragraph(item, styles["body"]),
                    ]
                ],
                colWidths=[6 * mm, 161 * mm],
                style=TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("TOPPADDING", (0, 0), (-1, -1), 1.5 * mm),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5 * mm),
                    ]
                ),
            )
        )
    return flowables


def numbered(items: list[str], styles: dict[str, ParagraphStyle]) -> list:
    rows = []
    for index, item in enumerate(items, 1):
        rows.append(
            [
                paragraph(str(index), styles["number"]),
                paragraph(item, styles["body"]),
            ]
        )
    return [
        Table(
            rows,
            colWidths=[12 * mm, 155 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), GREEN),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("LEFTPADDING", (0, 0), (0, -1), 2 * mm),
                    ("RIGHTPADDING", (0, 0), (0, -1), 2 * mm),
                    ("LEFTPADDING", (1, 0), (1, -1), 3 * mm),
                    ("RIGHTPADDING", (1, 0), (1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 2 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
                ]
            ),
        )
    ]


def callout(
    title: str,
    text: str,
    styles: dict[str, ParagraphStyle],
    tone: str = "green",
) -> Table:
    background = GREEN_LIGHT if tone == "green" else AMBER_LIGHT if tone == "amber" else RED_LIGHT
    accent = GREEN if tone == "green" else AMBER if tone == "amber" else RED
    return Table(
        [[paragraph(title, styles["callout_title"]), paragraph(text, styles["callout_body"])]],
        colWidths=[42 * mm, 125 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.7, accent),
                ("LINEBEFORE", (0, 0), (0, 0), 4, accent),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
            ]
        ),
    )


def section_title(
    number: str,
    title: str,
    subtitle: str,
    styles: dict[str, ParagraphStyle],
) -> list:
    return [
        paragraph(f"SECCIÓN {number}", styles["kicker"]),
        paragraph(title, styles["h1"]),
        paragraph(subtitle, styles["lead"]),
        Spacer(1, 5 * mm),
    ]


def checklist_table(
    title: str,
    items: list[str],
    styles: dict[str, ParagraphStyle],
) -> Table:
    rows = [[paragraph(title, styles["table_title"]), "RESP.", "FECHA"]]
    rows.extend(
        [
            [
                paragraph(item, styles["table_body"]),
                "( )",
                "____ / ____",
            ]
            for item in items
        ]
    )
    return Table(
        rows,
        colWidths=[116 * mm, 20 * mm, 31 * mm],
        repeatRows=1,
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FIELD]),
                ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
            ]
        ),
    )


def role_card(
    role: str,
    purpose: str,
    actions: list[str],
    styles: dict[str, ParagraphStyle],
) -> Table:
    return Table(
        [
            [paragraph(role, styles["card_title"])],
            [paragraph(purpose, styles["card_copy"])],
            [paragraph("<br/>".join(f"- {item}" for item in actions), styles["card_copy"])],
        ],
        colWidths=[52 * mm],
        style=TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
            ]
        ),
    )


def draw_circuit(canvas, x: float, y: float, flip: bool = False) -> None:
    canvas.saveState()
    canvas.setLineWidth(0.45)
    canvas.setStrokeColor(colors.Color(GREEN.red, GREEN.green, GREEN.blue, alpha=0.22))
    canvas.setFillColor(AMBER)
    direction = -1 if flip else 1
    points = [
        (x, y),
        (x + direction * 13 * mm, y),
        (x + direction * 19 * mm, y + 6 * mm),
        (x + direction * 35 * mm, y + 6 * mm),
    ]
    path = canvas.beginPath()
    path.moveTo(*points[0])
    for point in points[1:]:
        path.lineTo(*point)
    canvas.drawPath(path)
    canvas.circle(points[-1][0], points[-1][1], 1.2 * mm, fill=1, stroke=0)
    canvas.restoreState()


def cover_page(canvas, doc) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(GREEN_DARK)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#0A4B3A"))
    canvas.circle(width - 12 * mm, height - 18 * mm, 70 * mm, fill=1, stroke=0)
    canvas.circle(12 * mm, 10 * mm, 55 * mm, fill=1, stroke=0)
    draw_circuit(canvas, 14 * mm, height - 25 * mm)
    draw_circuit(canvas, width - 14 * mm, 28 * mm, flip=True)
    if SHIELD_WHITE.exists():
        canvas.drawImage(
            str(SHIELD_WHITE),
            70 * mm,
            188 * mm,
            70 * mm,
            70 * mm,
            preserveAspectRatio=True,
            mask="auto",
        )
    canvas.setFont(FONT_BOLD, 30)
    canvas.setFillColor(colors.white)
    canvas.drawCentredString(width / 2, 167 * mm, "AgroEscudo")
    canvas.setFont(FONT_BOLD, 10)
    canvas.setFillColor(colors.HexColor("#E4BD58"))
    canvas.drawCentredString(width / 2, 157 * mm, "CONTROL, TRAZABILIDAD Y PROTECCIÓN OPERATIVA")
    canvas.setStrokeColor(AMBER)
    canvas.setLineWidth(2)
    canvas.line(70 * mm, 147 * mm, 140 * mm, 147 * mm)
    canvas.setFont(FONT_BOLD, 22)
    canvas.setFillColor(colors.white)
    canvas.drawCentredString(width / 2, 127 * mm, "Manual de usuario, operación")
    canvas.drawCentredString(width / 2, 116 * mm, "y servicio para piloto")
    canvas.setFont(FONT, 11)
    canvas.setFillColor(colors.HexColor("#D7E8E2"))
    canvas.drawCentredString(width / 2, 99 * mm, "Web, Android, dispositivos IoT, alertas y reportes")
    canvas.setFillColor(colors.Color(1, 1, 1, alpha=0.08))
    canvas.roundRect(28 * mm, 39 * mm, 154 * mm, 38 * mm, 5 * mm, fill=1, stroke=0)
    canvas.setFont(FONT_BOLD, 9)
    canvas.setFillColor(colors.white)
    canvas.drawString(36 * mm, 64 * mm, "VERSIÓN")
    canvas.drawString(82 * mm, 64 * mm, "APLICACIÓN")
    canvas.drawString(140 * mm, 64 * mm, "EMISIÓN")
    canvas.setFont(FONT, 9)
    canvas.setFillColor(colors.HexColor("#D7E8E2"))
    canvas.drawString(36 * mm, 54 * mm, "1.0")
    canvas.drawString(82 * mm, 54 * mm, "Primeros pilotos")
    canvas.drawString(140 * mm, 54 * mm, "23/07/2026")
    canvas.restoreState()


def body_page(canvas, doc) -> None:
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(colors.white)
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    if LOGO.exists():
        canvas.drawImage(
            str(LOGO),
            20 * mm,
            height - 23 * mm,
            47 * mm,
            13 * mm,
            preserveAspectRatio=True,
            mask="auto",
        )
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.7)
    canvas.line(20 * mm, height - 27 * mm, width - 20 * mm, height - 27 * mm)
    canvas.setFont(FONT_BOLD, 7.5)
    canvas.setFillColor(GREEN)
    canvas.drawRightString(width - 20 * mm, height - 18 * mm, "MANUAL DE USUARIO Y SERVICIO")
    draw_circuit(canvas, width - 20 * mm, height - 32 * mm, flip=True)
    canvas.line(20 * mm, 17 * mm, width - 20 * mm, 17 * mm)
    canvas.setFont(FONT, 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(20 * mm, 10 * mm, "AgroEscudo | Uso controlado en primeros pilotos")
    canvas.drawRightString(width - 20 * mm, 10 * mm, f"Página {doc.page}")
    canvas.restoreState()


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontName=FONT,
            fontSize=9.5,
            leading=14,
            textColor=INK,
            spaceAfter=2 * mm,
        ),
        "h1": ParagraphStyle(
            "H1",
            fontName=FONT_BOLD,
            fontSize=23,
            leading=28,
            textColor=GREEN_DARK,
            spaceAfter=2.5 * mm,
        ),
        "h2": ParagraphStyle(
            "H2",
            fontName=FONT_BOLD,
            fontSize=14,
            leading=18,
            textColor=GREEN,
            spaceBefore=4 * mm,
            spaceAfter=2.5 * mm,
        ),
        "lead": ParagraphStyle(
            "Lead",
            fontName=FONT,
            fontSize=10.5,
            leading=15,
            textColor=MUTED,
        ),
        "kicker": ParagraphStyle(
            "Kicker",
            fontName=FONT_BOLD,
            fontSize=7.5,
            leading=10,
            textColor=AMBER,
            spaceAfter=2 * mm,
        ),
        "number": ParagraphStyle(
            "Number",
            fontName=FONT_BOLD,
            fontSize=8,
            leading=9,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "bullet_mark": ParagraphStyle(
            "BulletMark",
            fontName=FONT_BOLD,
            fontSize=12,
            leading=14,
            textColor=AMBER,
        ),
        "callout_title": ParagraphStyle(
            "CalloutTitle",
            fontName=FONT_BOLD,
            fontSize=9,
            leading=12,
            textColor=GREEN_DARK,
        ),
        "callout_body": ParagraphStyle(
            "CalloutBody",
            fontName=FONT,
            fontSize=8.7,
            leading=12,
            textColor=INK,
        ),
        "table_title": ParagraphStyle(
            "TableTitle",
            fontName=FONT_BOLD,
            fontSize=8,
            leading=10,
            textColor=colors.white,
        ),
        "table_body": ParagraphStyle(
            "TableBody",
            fontName=FONT,
            fontSize=8.5,
            leading=11,
            textColor=INK,
        ),
        "card_title": ParagraphStyle(
            "CardTitle",
            fontName=FONT_BOLD,
            fontSize=11,
            leading=14,
            textColor=colors.white,
        ),
        "card_copy": ParagraphStyle(
            "CardCopy",
            fontName=FONT,
            fontSize=8.2,
            leading=11.5,
            textColor=INK,
        ),
        "small": ParagraphStyle(
            "Small",
            fontName=FONT,
            fontSize=7.6,
            leading=10,
            textColor=MUTED,
        ),
        "toc": ParagraphStyle(
            "Toc",
            fontName=FONT,
            fontSize=9.5,
            leading=15,
            textColor=INK,
        ),
    }


def build_story() -> list:
    s = styles()
    story: list = [NextPageTemplate("body"), PageBreak()]
    story += section_title(
        "00",
        "Cómo usar este manual",
        "Una guía para preparar, operar y cerrar un piloto AgroEscudo con responsabilidades claras.",
        s,
    )
    story.append(
        callout(
            "ALCANCE",
            "Este documento cubre web, Android, nodos IoT, alertas, mantenimiento y reportes. No reemplaza la inspección física ni el criterio del responsable de planta.",
            s,
        )
    )
    story.append(Spacer(1, 6 * mm))
    story.append(paragraph("Contenido", s["h2"]))
    toc_items = [
        "1. Preparación y roles",
        "2. Flujo del administrador",
        "3. Flujo del técnico",
        "4. Portal del cliente",
        "5. Instalación y QR",
        "6. Lecturas, alertas y respuesta",
        "7. Mantenimiento y evidencia",
        "8. Gateways, notificaciones y reportes",
        "9. Rutinas, soporte y cierre",
        "10. Configuraciones pendientes e impresión",
    ]
    story.append(
        Table(
            [[paragraph(item, s["toc"])] for item in toc_items],
            colWidths=[167 * mm],
            style=TableStyle(
                [
                    ("ROWBACKGROUNDS", (0, 0), (-1, -1), [FIELD, colors.white]),
                    ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
                ]
            ),
        )
    )

    story.append(PageBreak())
    story += section_title(
        "01",
        "Preparación del piloto",
        "No iniciar operación hasta confirmar activos, responsables y una primera lectura confiable.",
        s,
    )
    story += numbered(
        [
            "Confirmar empresa, sitio y unidad monitoreada.",
            "Registrar producto, capacidad o superficie y ubicación física.",
            "Registrar dispositivo y gateway sin compartir secretos.",
            "Asignar técnico y usuario cliente.",
            "Definir umbrales acordados con la operación.",
            "Verificar batería, alimentación, sensor, antena y conectividad.",
            "Completar checklist digital, primera lectura y alerta de prueba.",
            "Generar QR, validar accesos y descargar reporte de prueba.",
        ],
        s,
    )
    story.append(Spacer(1, 5 * mm))
    story.append(
        callout(
            "NO INICIAR",
            "Detén el alta si no existe transmisión, la lectura no coincide con la verificación local o el cliente no puede ingresar.",
            s,
            "red",
        )
    )

    story.append(PageBreak())
    story += section_title(
        "02",
        "Roles y responsabilidades",
        "Cada usuario ve y ejecuta únicamente acciones autorizadas por backend.",
        s,
    )
    story.append(
        Table(
            [
                [
                    role_card(
                        "ADMIN",
                        "Prepara y supervisa el piloto.",
                        ["Empresas y unidades", "Usuarios y asignaciones", "Umbrales, gateways y reportes"],
                        s,
                    ),
                    role_card(
                        "TÉCNICO",
                        "Ejecuta trabajo de campo.",
                        ["QR y diagnóstico", "Instalación y mantenimiento", "Evidencia y alertas"],
                        s,
                    ),
                    role_card(
                        "CLIENTE",
                        "Consulta su operación.",
                        ["Estado y lecturas", "Alertas y bitácora", "Reporte ejecutivo"],
                        s,
                    ),
                ]
            ],
            colWidths=[55.5 * mm] * 3,
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 1.5 * mm),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 1.5 * mm),
                ]
            ),
        )
    )
    story.append(Spacer(1, 7 * mm))
    story.append(paragraph("Regla de acceso", s["h2"]))
    story += bullets(
        [
            "Admin tiene alcance completo dentro de la organización.",
            "Técnico solo opera unidades y mantenimientos asignados.",
            "Cliente solo consulta su empresa y no recibe diagnóstico sensible.",
            "Ocultar un botón no reemplaza la validación de permisos en la API.",
        ],
        s,
    )

    story.append(PageBreak())
    story += section_title(
        "03",
        "Alta administrativa",
        "Secuencia recomendada en el dashboard web para evitar activos incompletos.",
        s,
    )
    story += numbered(
        [
            "Crear o revisar empresa y sitio.",
            "Crear silo, galpón, almacén o parcela.",
            "Registrar dispositivo y guardar la API key fuera del manual.",
            "Asociar dispositivo a la unidad.",
            "Crear cliente y técnico; asignar unidades.",
            "Configurar umbrales por perfil SiloSensor o CampoSensor.",
            "Registrar gateway y asociar nodos IoT.",
            "Crear checklist de instalación y mantenimiento inicial.",
            "Revisar salud del sistema, métricas y reporte.",
        ],
        s,
    )
    story.append(Spacer(1, 5 * mm))
    story.append(
        checklist_table(
            "CONTROL DE ALTA",
            [
                "Empresa y sitio correctos",
                "Unidad y producto registrados",
                "Dispositivo y gateway asociados",
                "Técnico y cliente asignados",
                "Umbrales revisados",
                "Primera lectura disponible",
                "Reporte de prueba abierto",
            ],
            s,
        )
    )

    story.append(PageBreak())
    story += section_title(
        "04",
        "Trabajo del técnico",
        "La app Android concentra las acciones de campo sin copiar toda la administración web.",
        s,
    )
    story += numbered(
        [
            "Ingresar con usuario técnico.",
            "Revisar alertas, nodos offline y mantenimientos.",
            "Abrir Operación del piloto.",
            "Escanear el QR y comprobar el nodo.",
            "Completar checklist de instalación asignado.",
            "Tomar fotografías y seleccionar la intervención correcta.",
            "Iniciar mantenimiento antes de intervenir.",
            "Registrar diagnóstico, acción y estado final.",
            "Confirmar nueva lectura y sincronización.",
        ],
        s,
    )
    story.append(Spacer(1, 5 * mm))
    story.append(
        callout(
            "SIN INTERNET",
            "La app puede mostrar datos guardados, pero no permite cerrar mantenimiento, validar instalación ni subir evidencia sin conexión.",
            s,
            "amber",
        )
    )

    story.append(PageBreak())
    story += section_title(
        "05",
        "Portal del cliente",
        "Una lectura ejecutiva y operativa sin exponer configuración técnica.",
        s,
    )
    story += numbered(
        [
            "Ingresar al portal.",
            "Seleccionar silo, galpón o parcela.",
            "Revisar estado general y última lectura.",
            "Consultar tendencia y alertas.",
            "Leer acciones registradas.",
            "Descargar reporte PDF.",
            "Contactar soporte si el riesgo o la falta de datos persiste.",
        ],
        s,
    )
    story.append(Spacer(1, 5 * mm))
    story.append(
        callout(
            "PRIVACIDAD",
            "El cliente no ve RSSI, SNR, API keys, credenciales de gateway, configuración crítica ni datos de otras empresas.",
            s,
        )
    )

    story.append(PageBreak())
    story += section_title(
        "06",
        "Checklist físico de instalación",
        "Completar en sitio antes de aprobar digitalmente la puesta en marcha.",
        s,
    )
    story.append(
        checklist_table(
            "HARDWARE",
            [
                "Caja cerrada y protegida",
                "Montaje estable",
                "Antena instalada",
                "Batería y alimentación verificadas",
                "Sensor responde",
                "Cableado protegido",
                "Sellado revisado",
                "QR instalado y legible",
            ],
            s,
        )
    )
    story.append(Spacer(1, 5 * mm))
    story.append(
        checklist_table(
            "COMUNICACIÓN",
            [
                "Gateway asociado",
                "Primera transmisión recibida",
                "Hora sincronizada",
                "Conectividad comprobada",
            ],
            s,
        )
    )

    story.append(PageBreak())
    story += section_title(
        "07",
        "Validación de instalación",
        "La plataforma no aprueba una instalación sin evidencia mínima.",
        s,
    )
    story.append(
        checklist_table(
            "VALIDACIÓN DIGITAL",
            [
                "Primera lectura registrada",
                "Lectura comparada con referencia local",
                "Umbrales revisados",
                "Alerta de prueba confirmada",
                "Acceso técnico validado",
                "Acceso cliente validado",
                "Reporte de prueba generado",
            ],
            s,
        )
    )
    story.append(Spacer(1, 5 * mm))
    story.append(
        callout(
            "RESULTADO",
            "Usa Aprobado, Aprobado con observaciones o No aprobado. Las observaciones deben ser específicas y verificables.",
            s,
            "amber",
        )
    )

    story.append(PageBreak())
    story += section_title(
        "08",
        "Uso seguro del QR",
        "El QR identifica un nodo, pero no concede permisos globales ni reemplaza el login.",
        s,
    )
    story += numbered(
        [
            "Abrir la app e ingresar.",
            "Abrir Operación del piloto.",
            "Tocar Escanear QR.",
            "Alinear el código dentro del recuadro.",
            "Esperar la validación del backend.",
            "Comparar producto, dispositivo y acciones autorizadas.",
        ],
        s,
    )
    story.append(Spacer(1, 6 * mm))
    story.append(
        callout(
            "DETENER",
            "No continuar si el QR está revocado, no corresponde a la unidad o muestra acceso restringido.",
            s,
            "red",
        )
    )
    story.append(Spacer(1, 6 * mm))
    story.append(paragraph("Gestión administrativa", s["h2"]))
    story += bullets(
        [
            "Rotar QR cuando se sospecha copia o exposición.",
            "Revocar QR cuando el nodo se retira.",
            "No imprimir API keys ni tokens de ingestión en la etiqueta.",
        ],
        s,
    )

    story.append(PageBreak())
    story += section_title(
        "09",
        "Lecturas y gráficas",
        "Interpretar únicamente métricas disponibles y calibradas para el perfil del nodo.",
        s,
    )
    profiles = [
        [
            paragraph("SILOSENSOR", s["table_title"]),
            paragraph("CAMPOSENSOR", s["table_title"]),
        ],
        [
            paragraph(
                "Temperatura de grano<br/>Temperatura ambiente<br/>Humedad ambiente<br/>Nivel y distancia<br/>Batería<br/>Señal técnica",
                s["table_body"],
            ),
            paragraph(
                "Humedad de suelo<br/>Temperatura de suelo<br/>Temperatura ambiente<br/>Humedad ambiente<br/>Batería",
                s["table_body"],
            ),
        ],
    ]
    story.append(
        Table(
            profiles,
            colWidths=[83.5 * mm, 83.5 * mm],
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), GREEN_DARK),
                    ("BOX", (0, 0), (-1, -1), 0.6, LINE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
                ]
            ),
        )
    )
    story.append(Spacer(1, 6 * mm))
    story.append(
        callout(
            "SIN DATO",
            "Nunca interpretar un campo ausente como cero. Un hueco en la gráfica representa falta de evidencia, no continuidad.",
            s,
        )
    )

    story.append(PageBreak())
    story += section_title(
        "10",
        "Respuesta ante alertas",
        "Actuar primero sobre la condición física y documentar después cada decisión.",
        s,
    )
    alert_rows = [
        ["EVENTO", "ACCIÓN INMEDIATA", "EVIDENCIA"],
        ["Temperatura alta", "Inspeccionar punto y acumulación térmica.", "Foto, hora y lectura posterior."],
        ["Humedad alta", "Revisar ventilación, condensación e ingreso de agua.", "Acción y duración de aireación."],
        ["Crítica", "Priorizar, informar responsable y verificar físicamente.", "Diagnóstico, acción y seguimiento."],
        ["Batería baja", "Revisar alimentación, conexión y batería.", "Medición o cambio realizado."],
        ["Sin lecturas", "Revisar energía, antena, gateway y cola.", "Último contacto y pruebas."],
    ]
    story.append(
        Table(
            [
                [paragraph(cell, s["table_title"]) for cell in alert_rows[0]]
            ]
            + [
                [paragraph(cell, s["table_body"]) for cell in row]
                for row in alert_rows[1:]
            ],
            colWidths=[31 * mm, 78 * mm, 58 * mm],
            repeatRows=1,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), GREEN_DARK),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FIELD]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
                ]
            ),
        )
    )

    story.append(PageBreak())
    story += section_title(
        "11",
        "Mantenimiento trazable",
        "Una intervención completada no se modifica silenciosamente.",
        s,
    )
    story += numbered(
        [
            "Revisar orden y dispositivo.",
            "Iniciar mantenimiento antes de intervenir.",
            "Registrar diagnóstico específico.",
            "Registrar acción realizada.",
            "Indicar estado final del nodo.",
            "Adjuntar evidencia.",
            "Definir próxima revisión.",
            "Confirmar nueva lectura.",
        ],
        s,
    )
    story.append(Spacer(1, 5 * mm))
    story.append(
        callout(
            "INMUTABILIDAD",
            "Si una intervención cerrada necesita corrección, crea una nueva revisión o evento. No sustituyas el histórico.",
            s,
            "amber",
        )
    )

    story.append(PageBreak())
    story += section_title(
        "12",
        "Registro de servicio",
        "Formato de apoyo para una visita técnica.",
        s,
    )
    service_rows = [
        ["Cliente / empresa", "__________________________________________________"],
        ["Sitio / unidad", "__________________________________________________"],
        ["Dispositivo / gateway", "__________________________________________________"],
        ["Técnico", "__________________________________________________"],
        ["Fecha y hora", "__________________________________________________"],
        ["Diagnóstico", "__________________________________________________\n__________________________________________________"],
        ["Acción realizada", "__________________________________________________\n__________________________________________________"],
        ["Estado final", "( ) Operativo   ( ) Degradado   ( ) Offline   ( ) Calibración pendiente"],
        ["Próxima revisión", "__________________________________________________"],
        ["Firma / conformidad", "__________________________________________________"],
    ]
    story.append(
        Table(
            [
                [paragraph(row[0], s["table_body"]), paragraph(row[1].replace("\n", "<br/>"), s["table_body"])]
                for row in service_rows
            ],
            colWidths=[45 * mm, 122 * mm],
            style=TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, LINE),
                    ("BACKGROUND", (0, 0), (0, -1), FIELD),
                    ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
                ]
            ),
        )
    )

    story.append(PageBreak())
    story += section_title(
        "13",
        "Evidencia y privacidad",
        "Documentar sin mezclar intervenciones ni exponer información innecesaria.",
        s,
    )
    story += bullets(
        [
            "Seleccionar la intervención correcta antes de capturar una foto.",
            "Mostrar el estado del equipo, no personas ni documentos sensibles.",
            "Usar una descripción profesional y verificable.",
            "No cargar contraseñas, API keys, etiquetas secretas o pantallas con tokens.",
            "El cliente solo recibe evidencia autorizada y no sensible.",
        ],
        s,
    )
    story.append(Spacer(1, 6 * mm))
    story.append(
        checklist_table(
            "ANTES DE SUBIR",
            [
                "La foto corresponde al activo",
                "La intervención seleccionada es correcta",
                "No expone credenciales",
                "La descripción es profesional",
                "La imagen es legible",
            ],
            s,
        )
    )

    story.append(PageBreak())
    story += section_title(
        "14",
        "Gateways y salud",
        "La condición se calcula desde contacto, conectividad, cola y errores disponibles.",
        s,
    )
    story += bullets(
        [
            "Online: contacto y operación dentro de ventana.",
            "Delayed: contacto atrasado respecto de la cadencia.",
            "Offline: sin contacto dentro del límite.",
            "Degraded: comunicación o ingestión con fallas.",
            "Maintenance: intervención técnica declarada.",
            "Unknown: evidencia insuficiente.",
        ],
        s,
    )
    story.append(Spacer(1, 5 * mm))
    story.append(
        callout(
            "ALCANCE TÉCNICO",
            "El técnico puede marcar mantenimiento solo en gateways asignados. Cambios de empresa, sitio, firmware o nodos son administrativos.",
            s,
        )
    )

    story.append(PageBreak())
    story += section_title(
        "15",
        "Notificaciones auditables",
        "Distinguir simulación, envío y entrega confirmada.",
        s,
    )
    notif_rows = [
        ["ESTADO", "SIGNIFICADO", "ACCIÓN"],
        ["Dry run", "Mensaje simulado y auditado.", "Validar formato y destinatario."],
        ["Skipped", "Canal o destino no disponible.", "Corregir configuración."],
        ["Sent", "Proveedor aceptó el mensaje.", "Esperar confirmación."],
        ["Delivered", "Proveedor confirmó entrega.", "Cerrar seguimiento si aplica."],
        ["Failed", "Intento fallido.", "Revisar error y reintentar."],
    ]
    story.append(
        Table(
            [[paragraph(c, s["table_title"]) for c in notif_rows[0]]]
            + [[paragraph(c, s["table_body"]) for c in row] for row in notif_rows[1:]],
            colWidths=[30 * mm, 75 * mm, 62 * mm],
            repeatRows=1,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), GREEN_DARK),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FIELD]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
                ]
            ),
        )
    )
    story.append(Spacer(1, 5 * mm))
    story.append(
        callout(
            "IMPORTANTE",
            "Sent no significa Delivered. Nunca informes entrega confirmada sin respuesta explícita del proveedor.",
            s,
            "amber",
        )
    )

    story.append(PageBreak())
    story += section_title(
        "16",
        "Reportes y entrega al cliente",
        "Revisar datos, redacción y periodo antes de compartir un PDF.",
        s,
    )
    story += bullets(
        [
            "Ejecutivo: estado, disponibilidad, eventos, acciones y recomendaciones.",
            "Técnico: calidad, calibración, fallas, conectividad y próximas revisiones.",
            "Semanal: flujo compatible por unidad o dispositivo.",
            "CSV: lecturas, alertas, incidentes y mantenimiento según RBAC.",
        ],
        s,
    )
    story.append(Spacer(1, 5 * mm))
    story.append(
        checklist_table(
            "CONTROL DEL PDF",
            [
                "Cliente, sitio y unidad correctos",
                "Periodo correcto",
                "Alertas y acciones revisadas",
                "Sin texto informal",
                "Responsables confirmados",
                "Conclusiones prudentes",
                "Archivo abierto y páginas revisadas",
            ],
            s,
        )
    )

    story.append(PageBreak())
    story += section_title(
        "17",
        "Rutina de operación",
        "Una disciplina breve evita que las alertas y mantenimientos se acumulen.",
        s,
    )
    routine = [
        [
            paragraph("DIARIO", s["table_title"]),
            paragraph("SEMANAL", s["table_title"]),
            paragraph("MENSUAL", s["table_title"]),
        ],
        [
            paragraph("Alertas críticas<br/>Nodos offline<br/>Última lectura<br/>Batería<br/>Acciones", s["table_body"]),
            paragraph("Tendencias<br/>Vencidos<br/>Notificaciones<br/>Reporte<br/>Evidencia", s["table_body"]),
            paragraph("Usuarios<br/>Calibración<br/>Firmware<br/>Backups<br/>Métricas", s["table_body"]),
        ],
    ]
    story.append(
        Table(
            routine,
            colWidths=[55.6 * mm] * 3,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), GREEN_DARK),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
                ]
            ),
        )
    )
    story.append(Spacer(1, 7 * mm))
    story.append(
        callout(
            "REGISTRO",
            "Toda acción crítica debe quedar en bitácora con responsable, fecha, diagnóstico y resultado.",
            s,
        )
    )

    story.append(PageBreak())
    story += section_title(
        "18",
        "Soporte y escalamiento",
        "Recopilar contexto antes de escalar reduce el tiempo de diagnóstico.",
        s,
    )
    story += bullets(
        [
            "Backend o app no responden después de reintentar.",
            "Nodo permanece offline.",
            "Cola del gateway crece.",
            "QR no es reconocido.",
            "Alerta crítica persiste.",
            "PDF no se genera.",
            "Notificación falla repetidamente.",
        ],
        s,
    )
    story.append(Spacer(1, 5 * mm))
    story.append(
        checklist_table(
            "DATOS PARA SOPORTE",
            [
                "Fecha y hora",
                "Usuario y rol",
                "Empresa y unidad",
                "Dispositivo o gateway",
                "Mensaje observado",
                "Acciones ya realizadas",
                "Captura sin credenciales",
            ],
            s,
        )
    )

    story.append(PageBreak())
    story += section_title(
        "19",
        "Qué debe configurar el propietario",
        "Credenciales y servicios externos que Codex no puede inventar ni aprobar por cuenta del usuario.",
        s,
    )
    owner_rows = [
        ["SERVICIO", "DATO NECESARIO", "DÓNDE CONFIGURAR"],
        ["Render / PostgreSQL", "DATABASE_URL, JWT_SECRET, CORS", "Variables del backend"],
        ["Vercel", "NEXT_PUBLIC_API_URL", "Variables del frontend"],
        ["S3 compatible", "Endpoint, bucket y access keys", "Variables del backend"],
        ["Resend / SMTP", "API key, remitente y reply-to", "Variables del backend"],
        ["Telegram", "Bot token y chat IDs", "Variables y perfil de usuario"],
        ["WhatsApp Cloud", "Token, phone ID y plantilla", "Meta + backend"],
        ["Firebase FCM", "Proyecto y service account", "Firebase + backend/app"],
        ["Soporte", "Correo, WhatsApp y horario", "Backend y frontend"],
        ["Sentry opcional", "DSN y entorno", "Backend/frontend"],
    ]
    story.append(
        Table(
            [[paragraph(c, s["table_title"]) for c in owner_rows[0]]]
            + [[paragraph(c, s["table_body"]) for c in row] for row in owner_rows[1:]],
            colWidths=[36 * mm, 71 * mm, 60 * mm],
            repeatRows=1,
            style=TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), GREEN_DARK),
                    ("GRID", (0, 0), (-1, -1), 0.4, LINE),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, FIELD]),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2.5 * mm),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2.5 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
                ]
            ),
        )
    )
    story.append(Spacer(1, 5 * mm))
    story.append(
        callout(
            "SEGURIDAD",
            "Carga las credenciales directamente en cada proveedor. No las pegues en manuales, Git, capturas o mensajes públicos.",
            s,
            "red",
        )
    )

    story.append(PageBreak())
    story += section_title(
        "20",
        "Cómo imprimir y distribuir",
        "Configuración recomendada para conservar legibilidad y espacio de firma.",
        s,
    )
    print_rows = [
        ["Papel", "A4"],
        ["Escala", "100%"],
        ["Orientación", "Vertical"],
        ["Doble cara", "Borde largo"],
        ["Color", "Recomendado"],
        ["Márgenes", "Predeterminados"],
        ["Prueba", "Imprimir primero páginas 1 y 2"],
    ]
    story.append(
        Table(
            [[paragraph(a, s["table_body"]), paragraph(b, s["table_body"])] for a, b in print_rows],
            colWidths=[48 * mm, 119 * mm],
            style=TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, LINE),
                    ("BACKGROUND", (0, 0), (0, -1), FIELD),
                    ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
                ]
            ),
        )
    )
    story.append(Spacer(1, 7 * mm))
    story.append(
        callout(
            "CAMPO",
            "Para visitas técnicas imprime las secciones 6, 7, 10, 12 y 18. Conserva el manual completo en PDF.",
            s,
        )
    )

    story.append(PageBreak())
    story += section_title(
        "21",
        "Cierre del piloto",
        "Convertir el monitoreo en evidencia revisable para una decisión de continuidad.",
        s,
    )
    story += numbered(
        [
            "Confirmar periodo evaluado.",
            "Revisar lecturas y disponibilidad.",
            "Revisar alertas y tiempo fuera de rango.",
            "Confirmar acciones y mantenimiento.",
            "Verificar evidencia.",
            "Descargar reporte ejecutivo y técnico.",
            "Registrar observaciones del cliente.",
            "Respaldar la información.",
            "Definir continuidad, ajustes o retiro.",
        ],
        s,
    )
    story.append(Spacer(1, 6 * mm))
    story.append(
        callout(
            "ALCANCE",
            "El cierre no constituye certificación automática ni garantía de ausencia de riesgo.",
            s,
            "amber",
        )
    )

    story.append(PageBreak())
    story += section_title(
        "22",
        "Acta breve de revisión",
        "Registro imprimible para la reunión de seguimiento o cierre.",
        s,
    )
    act_rows = [
        ["Empresa", "__________________________________________________"],
        ["Sitio / unidad", "__________________________________________________"],
        ["Periodo", "__________________________________________________"],
        ["Estado general", "( ) Normal   ( ) Atención   ( ) Crítico   ( ) Sin datos"],
        ["Alertas relevantes", "__________________________________________________\n__________________________________________________"],
        ["Acciones realizadas", "__________________________________________________\n__________________________________________________"],
        ["Pendientes", "__________________________________________________\n__________________________________________________"],
        ["Decisión", "( ) Continuar   ( ) Ajustar   ( ) Pausar   ( ) Retirar"],
        ["Responsable cliente", "__________________________  Firma: _______________"],
        ["Responsable AgroEscudo", "__________________________  Firma: _______________"],
    ]
    story.append(
        Table(
            [
                [paragraph(row[0], s["table_body"]), paragraph(row[1].replace("\n", "<br/>"), s["table_body"])]
                for row in act_rows
            ],
            colWidths=[45 * mm, 122 * mm],
            style=TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, LINE),
                    ("BACKGROUND", (0, 0), (0, -1), FIELD),
                    ("FONTNAME", (0, 0), (0, -1), FONT_BOLD),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
                    ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
                ]
            ),
        )
    )
    return story


def build_pdf() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    width, height = A4
    body_frame = Frame(
        21 * mm,
        23 * mm,
        width - 42 * mm,
        height - 55 * mm,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id="body",
    )
    cover_frame = Frame(
        0,
        0,
        width,
        height,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
        id="cover",
    )
    document = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=21 * mm,
        rightMargin=21 * mm,
        topMargin=32 * mm,
        bottomMargin=23 * mm,
        title="AgroEscudo - Manual de usuario, operacion y servicio",
        author="AgroEscudo",
        subject="Operacion controlada de primeros pilotos",
    )
    document.addPageTemplates(
        [
            PageTemplate(id="cover", frames=[cover_frame], onPage=cover_page),
            PageTemplate(id="body", frames=[body_frame], onPage=body_page),
        ]
    )
    document.build(build_story())
    print(OUTPUT)


if __name__ == "__main__":
    build_pdf()
