from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "AgroEscudo_Manual_Visual_Flujos_Piloto.pdf"
LOGO = ROOT / "frontend" / "public" / "brand" / "logo-horizontal-transparent.png"

GREEN_DARK = colors.HexColor("#064B35")
GREEN = colors.HexColor("#047857")
GREEN_LIGHT = colors.HexColor("#DFF3E9")
AMBER = colors.HexColor("#C89116")
AMBER_LIGHT = colors.HexColor("#FFF4D6")
INK = colors.HexColor("#25332F")
MUTED = colors.HexColor("#60716B")
LINE = colors.HexColor("#D7E4DF")
SOFT = colors.HexColor("#F7FAF8")
RED = colors.HexColor("#B42318")
WHITE = colors.white


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="Cover", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=28, leading=34, alignment=TA_CENTER, textColor=GREEN_DARK))
styles.add(ParagraphStyle(name="CoverSub", parent=styles["Normal"], fontName="Helvetica", fontSize=11.5, leading=17, alignment=TA_CENTER, textColor=MUTED))
styles.add(ParagraphStyle(name="H1", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=23, textColor=GREEN_DARK, spaceAfter=8))
styles.add(ParagraphStyle(name="H2", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=GREEN_DARK, spaceBefore=6, spaceAfter=4))
styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.8, leading=13, textColor=INK, spaceAfter=5))
styles.add(ParagraphStyle(name="Small", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.3, leading=9.6, textColor=MUTED))
styles.add(ParagraphStyle(name="Cell", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.5, leading=10, textColor=INK))
styles.add(ParagraphStyle(name="Head", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.5, leading=9.5, textColor=WHITE))
styles.add(ParagraphStyle(name="FlowTitle", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9, leading=11, textColor=GREEN_DARK, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="FlowBody", parent=styles["BodyText"], fontName="Helvetica", fontSize=6.8, leading=8.5, textColor=INK, alignment=TA_CENTER))


def p(text: str, style: str = "Body") -> Paragraph:
    return Paragraph(text, styles[style])


def data_table(rows: list[list[str]], widths: list[float]) -> Table:
    content = []
    for row_index, row in enumerate(rows):
        style = "Head" if row_index == 0 else "Cell"
        content.append([p(str(value), style) for value in row])
    result = Table(content, colWidths=widths, repeatRows=1, hAlign="LEFT")
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN_DARK),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, SOFT]),
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return result


def flow_box(title: str, body: str, tone: str = "green", width: float = 3.25 * cm) -> Table:
    background = GREEN_LIGHT if tone == "green" else AMBER_LIGHT if tone == "amber" else SOFT
    border = GREEN if tone == "green" else AMBER if tone == "amber" else LINE
    result = Table([[p(title, "FlowTitle")], [p(body, "FlowBody")]], colWidths=[width], rowHeights=[0.65 * cm, 1.05 * cm])
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return result


def arrow() -> Paragraph:
    return Paragraph("<font color='#C89116'><b>&gt;</b></font>", ParagraphStyle("Arrow", parent=styles["Body"], fontSize=17, leading=18, alignment=TA_CENTER))


def flow_row(items: list[tuple[str, str, str]], width: float = 3.15 * cm) -> Table:
    cells = []
    widths = []
    for index, (title, body, tone) in enumerate(items):
        cells.append(flow_box(title, body, tone, width))
        widths.append(width)
        if index < len(items) - 1:
            cells.append(arrow())
            widths.append(0.55 * cm)
    result = Table([cells], colWidths=widths, hAlign="CENTER")
    result.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return result


def header_footer(canvas: Canvas, document) -> None:
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(LINE)
    canvas.line(1.45 * cm, height - 1.3 * cm, width - 1.45 * cm, height - 1.3 * cm)
    canvas.line(1.45 * cm, 1.15 * cm, width - 1.45 * cm, 1.15 * cm)
    canvas.setFillColor(GREEN_DARK)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(1.45 * cm, height - 1.0 * cm, "AgroEscudo - Manual visual de flujos del piloto")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(width - 1.45 * cm, height - 1.0 * cm, "Registro, instalación, monitoreo y evidencia")
    canvas.drawString(1.45 * cm, 0.75 * cm, "Uso operativo - versión 2026-08-13")
    canvas.drawRightString(width - 1.45 * cm, 0.75 * cm, f"Página {document.page}")
    canvas.restoreState()


def build_story() -> list:
    story: list = [Spacer(1, 1.1 * cm)]
    if LOGO.exists():
        logo = Image(str(LOGO), width=10.2 * cm, height=2.25 * cm)
        logo.hAlign = "CENTER"
        story.extend([logo, Spacer(1, 1.2 * cm)])
    story.append(p("MANUAL OPERATIVO VISUAL", "Small"))
    story.append(p("Flujos de trabajo del piloto AgroEscudo", "Cover"))
    story.append(p("Desde crear una cuenta y aprobar la empresa hasta enlazar el sensor, atender una alerta y descargar evidencia.", "CoverSub"))
    story.append(Spacer(1, 1.1 * cm))
    story.append(data_table([
        ["Servicio", "Estado"],
        ["Web pública", "https://agroescudobo.vercel.app - verificada HTTP 200"],
        ["API pública", "https://agroescudo-api.onrender.com - PostgreSQL ok"],
        ["Alcance", "Admin, técnico, cliente, SiloSensor, CampoSensor, LoRa, Sentinel y PDF"],
        ["Regla", "JWT, API key del sensor, HMAC del gateway y token Sentinel son credenciales diferentes."],
    ], [4 * cm, 12.5 * cm]))
    story.append(Spacer(1, 1.0 * cm))
    story.append(flow_row([
        ("CUENTA", "Registro y verificación", "green"),
        ("PILOTO", "Empresa, sitio y unidad", "green"),
        ("SENSOR", "Alta y aprovisionamiento", "amber"),
        ("OPERACIÓN", "Lecturas, alertas y acción", "green"),
    ], 3.4 * cm))
    story.append(PageBreak())

    story.append(p("1. Crear cuenta, aprobar y acceder", "H1"))
    story.append(flow_row([
        ("CREAR CUENTA", "Datos de empresa, responsable y consentimiento", "green"),
        ("VERIFICAR", "Confirmar correo cuando el servicio esté activo", "green"),
        ("REVISIÓN", "Empresa PENDING_REVIEW", "amber"),
        ("APROBACIÓN", "Admin activa empresa y usuario", "green"),
    ], 3.4 * cm))
    story.append(Spacer(1, 0.5 * cm))
    story.append(data_table([
        ["Actor", "Qué debe hacer", "Resultado"],
        ["Cliente", "Crear cuenta, aceptar términos y verificar correo.", "Solicitud trazable, todavía sin acceso productivo completo."],
        ["Admin", "Validar organización, contacto y alcance del piloto.", "Empresa aprobada y activa."],
        ["Sistema", "Login y GET /api/me aplican rol y empresa.", "JWT de sesión; nunca se usa en el sensor."],
    ], [3.2 * cm, 7.3 * cm, 6 * cm]))
    story.append(p("Rutas clave", "H2"))
    story.append(p("POST /api/auth/signup/company, verificación de correo, login y GET /api/me. Si el correo productivo no está configurado, el flujo debe informarlo claramente; no se deben inventar verificaciones.", "Body"))

    story.append(p("2. Alta administrativa del piloto", "H1"))
    story.append(flow_row([
        ("EMPRESA", "Cliente aprobado", "green"),
        ("SITIO", "Ubicación operativa", "green"),
        ("UNIDAD", "Silo, galpón o parcela", "green"),
        ("RESPONSABLES", "Técnico + cliente", "amber"),
    ], 3.4 * cm))
    story.append(Spacer(1, 0.35 * cm))
    story.append(flow_row([
        ("PRODUCTO", "SiloSensor / CampoSensor", "green"),
        ("DISPOSITIVO", "device_id único", "green"),
        ("API KEY", "Visible una vez", "amber"),
        ("INSTALACIÓN", "Checklist + primera lectura", "green"),
    ], 3.4 * cm))
    story.append(PageBreak())

    story.append(p("3. Enlazar un sensor por Wi-Fi directo", "H1"))
    story.append(flow_row([
        ("ADMIN", "Crea el dispositivo", "green"),
        ("SECRETO", "Copia API key una vez", "amber"),
        ("ESP32", "Configura Wi-Fi, URL, ID y key", "green"),
        ("FASTAPI", "Valida, guarda y alerta", "green"),
    ], 3.4 * cm))
    story.append(Spacer(1, 0.45 * cm))
    story.append(data_table([
        ["Elemento", "Valor o regla"],
        ["Endpoint", "POST /api/readings"],
        ["Identidad", "device_id externo único"],
        ["Autenticación", "device_token = API key entregada al crear/rotar"],
        ["Datos", "Solo métricas presentes; un sensor ausente no se representa con cero"],
        ["Timestamp", "UTC ISO 8601"],
        ["Secreto", "Guardar únicamente en firmware/NVS o aprovisionamiento local; nunca en web/app/PDF/Git"],
    ], [4.2 * cm, 12.3 * cm]))
    story.append(p("Prueba mínima", "H2"))
    story.append(p("Enviar una lectura controlada, confirmar respuesta aceptada, abrir el nodo correcto y verificar que la serie no se mezcla con otros dispositivos de la misma unidad.", "Body"))

    story.append(p("4. Enlazar nodos por LoRa", "H1"))
    story.append(flow_row([
        ("NODO", "Mide y persiste", "green"),
        ("LORA", "Payload binario V1/V2/V3", "green"),
        ("GATEWAY", "Valida, deduplica y encola", "amber"),
        ("API BATCH", "HMAC + replay protection", "green"),
    ], 3.4 * cm))
    story.append(Spacer(1, 0.45 * cm))
    story.append(data_table([
        ["Control", "Responsabilidad"],
        ["ACK LoRa", "El gateway responde después de persistir la lectura localmente."],
        ["HMAC", "Firma body + timestamp + nonce con secreto propio del gateway."],
        ["Idempotencia", "device_id + boot_id + sequence impide duplicados operativos."],
        ["Respuesta batch", "accepted, duplicate, rejected o temporary_error por lectura."],
        ["Borrado", "Gateway borra de cola solo accepted o duplicate."],
    ], [4.2 * cm, 12.3 * cm]))
    story.append(PageBreak())

    story.append(p("5. Lectura, alerta, acción y reporte", "H1"))
    story.append(flow_row([
        ("LECTURA", "Validada y calibrada", "green"),
        ("UMBRAL", "Backend evalúa", "green"),
        ("ALERTA", "No duplicada", "amber"),
        ("ACCIÓN", "Inspección + bitácora", "green"),
    ], 3.4 * cm))
    story.append(Spacer(1, 0.35 * cm))
    story.append(flow_row([
        ("VERIFICAR", "Lectura posterior", "green"),
        ("RESOLVER", "Cerrar con evidencia", "green"),
        ("PDF", "Diario/semanal/mensual", "green"),
        ("CLIENTE", "Consulta su operación", "green"),
    ], 3.4 * cm))
    story.append(Spacer(1, 0.5 * cm))
    story.append(data_table([
        ["Estado", "Acción mínima"],
        ["Temperatura alta", "Inspeccionar punto, acumulación térmica y aireación."],
        ["Humedad alta", "Revisar ventilación, condensación e ingreso de agua."],
        ["Batería baja", "Medir alimentación, conexión y transmisión posterior."],
        ["Sin lecturas", "Revisar energía, antena, gateway, cola y última comunicación."],
        ["Crítica", "Priorizar, avisar responsable, documentar y no resolver sin verificación."],
    ], [4.2 * cm, 12.3 * cm]))

    story.append(p("6. Credenciales: no intercambiarlas", "H1"))
    story.append(data_table([
        ["Equipo/persona", "Credencial", "Uso exclusivo"],
        ["Usuario", "Password + JWT", "Web y app; RBAC de admin/técnico/cliente."],
        ["Sensor Wi-Fi", "device_id + API key", "POST /api/readings."],
        ["Gateway LoRa", "Gateway ID + HMAC", "POST /api/iot/v1/ingest/batch."],
        ["Sentinel GSM", "UID + token Sentinel", "Poll y resultado de SMS/llamada."],
    ], [4.2 * cm, 5.2 * cm, 7.1 * cm]))
    story.append(PageBreak())

    story.append(p("7. Roles y separación de responsabilidades", "H1"))
    story.append(data_table([
        ["Capacidad", "Admin", "Técnico", "Cliente"],
        ["Aprobar empresa / alta piloto", "Sí", "No", "No"],
        ["Crear y rotar sensor", "Sí", "No", "No"],
        ["Ver diagnóstico RSSI/SNR", "Sí", "Sí, asignados", "No"],
        ["Reconocer alertas", "Sí", "Sí, asignados", "Lectura"],
        ["Registrar mantenimiento", "Sí", "Sí, asignados", "Lectura"],
        ["Ver y descargar PDF", "Todos", "Asignados", "Solo propios"],
        ["Editar umbral crítico", "Sí", "Solo permiso definido", "No"],
    ], [7.2 * cm, 3.1 * cm, 3.1 * cm, 3.1 * cm]))
    story.append(p("8. Checklist para el primer dispositivo", "H1"))
    checklist = [
        "1. Web y /api/health/db responden.",
        "2. Empresa aprobada; sitio y unidad creados.",
        "3. Device ID único y tipo compatible.",
        "4. API key guardada una sola vez fuera de Git.",
        "5. Técnico y cliente asignados.",
        "6. Firmware, alimentación, antena y caja validados.",
        "7. Primera lectura aceptada y contrastada localmente.",
        "8. Nodo correcto visible; sin mezcla entre dispositivos.",
        "9. Umbrales y calibración documentados.",
        "10. Alerta, acknowledge, bitácora y resolve probados.",
        "11. PDF abierto y revisado.",
        "12. SMS/llamada probados físicamente si se ofrecen.",
    ]
    story.append(Table([[p(item, "Cell") for item in checklist[:6]], [p(item, "Cell") for item in checklist[6:]]], colWidths=[2.75 * cm] * 6, style=TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("BACKGROUND", (0, 0), (-1, -1), SOFT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ])))
    story.append(Spacer(1, 0.5 * cm))
    story.append(p("Cierre", "H2"))
    story.append(p("El piloto puede empezar cuando la nube, los roles y la lectura estén verificados, y cuando los canales externos prometidos hayan sido probados en el sitio. 'Sin dato' no significa cero y 'enviado' no significa entregado.", "Body"))
    return story


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=1.45 * cm,
        rightMargin=1.45 * cm,
        topMargin=1.65 * cm,
        bottomMargin=1.45 * cm,
        title="AgroEscudo - Manual visual de flujos del piloto",
        author="AgroEscudo",
        subject="Registro, alta, enlace de dispositivos, alertas, roles y evidencia",
    )
    document.build(build_story(), onFirstPage=header_footer, onLaterPages=header_footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
