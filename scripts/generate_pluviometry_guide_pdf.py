from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "AgroEscudo_Guia_Instalacion_Pluviometro.pdf"
LOGO = ROOT / "backend" / "app" / "assets" / "brand" / "logo-horizontal-white.png"

PAGE_W, PAGE_H = A4
GREEN = colors.HexColor("#064E3B")
GREEN_2 = colors.HexColor("#0B6B4D")
EMERALD = colors.HexColor("#10B981")
GOLD = colors.HexColor("#D99A00")
INK = colors.HexColor("#13231D")
MUTED = colors.HexColor("#5B6B65")
PALE = colors.HexColor("#ECFDF5")
PALE_GOLD = colors.HexColor("#FFF8E7")
LINE = colors.HexColor("#D5E4DD")


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="GuideTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=29, leading=34, textColor=colors.white, alignment=TA_LEFT, spaceAfter=12))
styles.add(ParagraphStyle(name="GuideSubtitle", parent=styles["Normal"], fontName="Helvetica", fontSize=14, leading=21, textColor=colors.HexColor("#D1FAE5"), spaceAfter=18))
styles.add(ParagraphStyle(name="H1x", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=GREEN, spaceBefore=4, spaceAfter=10))
styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=GREEN_2, spaceBefore=8, spaceAfter=5))
styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.6, leading=14, textColor=INK, spaceAfter=6))
styles.add(ParagraphStyle(name="Smallx", parent=styles["BodyText"], fontName="Helvetica", fontSize=8.2, leading=11.5, textColor=MUTED, spaceAfter=4))
styles.add(ParagraphStyle(name="Bulletx", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.4, leading=13.5, textColor=INK, leftIndent=13, firstLineIndent=-8, bulletIndent=2, spaceAfter=3))
styles.add(ParagraphStyle(name="Codex", parent=styles["Code"], fontName="Courier", fontSize=8.3, leading=11, textColor=GREEN, backColor=PALE, borderColor=LINE, borderWidth=0.5, borderPadding=7, spaceAfter=8))
styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9.2, leading=13, textColor=GREEN, backColor=PALE, borderColor=EMERALD, borderWidth=0.8, borderPadding=8, spaceBefore=3, spaceAfter=8))
styles.add(ParagraphStyle(name="Cell", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.6, leading=10, textColor=INK))
styles.add(ParagraphStyle(name="CellHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.8, leading=10, textColor=colors.white))
styles.add(ParagraphStyle(name="Footer", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.2, leading=9, textColor=MUTED))


def p(text, style="Bodyx"):
    return Paragraph(text, styles[style])


def bullets(items):
    return [Paragraph(f"- {item}", styles["Bulletx"]) for item in items]


def table(rows, widths, header=True, font_size=7.6):
    data = []
    for row_index, row in enumerate(rows):
        data.append([Paragraph(str(cell), styles["CellHead"] if header and row_index == 0 else styles["Cell"]) for cell in row])
    result = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAF8")]),
    ]
    result.setStyle(TableStyle(commands))
    return result


class FlowDiagram(Flowable):
    def __init__(self, labels, width=170 * mm, height=32 * mm):
        super().__init__()
        self.labels = labels
        self.width = width
        self.height = height

    def draw(self):
        canvas = self.canv
        gap = 5 * mm
        box_w = (self.width - gap * (len(self.labels) - 1)) / len(self.labels)
        box_h = 18 * mm
        y = 8 * mm
        for index, label in enumerate(self.labels):
            x = index * (box_w + gap)
            canvas.setFillColor(PALE if index % 2 == 0 else PALE_GOLD)
            canvas.setStrokeColor(EMERALD if index % 2 == 0 else GOLD)
            canvas.roundRect(x, y, box_w, box_h, 4, fill=1, stroke=1)
            canvas.setFillColor(GREEN)
            canvas.setFont("Helvetica-Bold", 7.5)
            words = label.split(" ")
            lines = [label] if len(label) <= 16 else [" ".join(words[: max(1, len(words)//2)]), " ".join(words[max(1, len(words)//2):])]
            for line_index, line in enumerate(lines):
                canvas.drawCentredString(x + box_w / 2, y + box_h / 2 + 2 - line_index * 9, line)
            if index < len(self.labels) - 1:
                start_x = x + box_w
                end_x = x + box_w + gap - 1.5 * mm
                center_y = y + box_h / 2
                canvas.setStrokeColor(GOLD)
                canvas.setFillColor(GOLD)
                canvas.line(start_x + 1 * mm, center_y, end_x, center_y)
                canvas.line(end_x, center_y, end_x - 2 * mm, center_y + 1.5 * mm)
                canvas.line(end_x, center_y, end_x - 2 * mm, center_y - 1.5 * mm)


def page_header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, PAGE_H - 17 * mm, PAGE_W - 18 * mm, PAGE_H - 17 * mm)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(GREEN)
    canvas.drawString(18 * mm, PAGE_H - 13 * mm, "AGROESCUDO | GUÍA DE PLUVIOMETRÍA IOT")
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(PAGE_W - 18 * mm, PAGE_H - 13 * mm, "Versión 1.0 | 27 septiembre 2026")
    canvas.line(18 * mm, 14 * mm, PAGE_W - 18 * mm, 14 * mm)
    canvas.drawString(18 * mm, 9.5 * mm, "Documento operativo | No contiene secretos")
    canvas.drawRightString(PAGE_W - 18 * mm, 9.5 * mm, f"Página {doc.page}")
    canvas.restoreState()


def cover(canvas, _doc):
    canvas.saveState()
    canvas.setFillColor(GREEN)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(GREEN_2)
    canvas.circle(PAGE_W - 8 * mm, PAGE_H - 20 * mm, 58 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#075A43"))
    canvas.circle(12 * mm, 20 * mm, 44 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(2)
    canvas.line(18 * mm, 33 * mm, PAGE_W - 18 * mm, 33 * mm)
    canvas.restoreState()


def build_story():
    story = []
    logo = Image(str(LOGO), width=72 * mm, height=19 * mm)
    story += [Spacer(1, 31 * mm), logo, Spacer(1, 35 * mm)]
    story += [p("Guía de instalación y conexión<br/>de pluviómetros IoT", "GuideTitle")]
    story += [p("Registro, ubicación, aprovisionamiento y validación de un dispositivo ESP32", "GuideSubtitle")]
    story += [Spacer(1, 8 * mm), p("VERSIÓN 1.0 | 27 SEPTIEMBRE 2026", "GuideSubtitle")]
    story += [Spacer(1, 45 * mm), p("Para técnicos, instaladores, colaboradores de hardware y operadores AgroEscudo.", "GuideSubtitle")]
    story += [p("Sin contraseñas, secretos, credenciales productivas ni claves reales.", "GuideSubtitle")]
    story.append(PageBreak())

    story += [p("1. Del sensor al dashboard", "H1x"), p("La instalación se entiende como una cadena completa. Cada tramo debe estar operativo antes de declarar el equipo validado.")]
    story += [FlowDiagram(["Pluviómetro / sensores", "ESP32", "Conectividad", "API AgroEscudo", "Base de datos", "Dashboard"]), Spacer(1, 3 * mm)]
    story += [p("Prueba HIL validada", "H2x"), p("ESP32 -> WiFi -> FastAPI -> AgroEscudo", "Codex")]
    story += [p("El hardware final puede incorporar gateway o LoRa posteriormente. Esa evolución no forma parte de este procedimiento ni autoriza una instalación física de campo.", "Callout")]
    story += [p("2. Estructura operativa", "H1x"), FlowDiagram(["Empresa", "Predio", "Parcela", "Pluviómetro", "Lecturas"], height=30 * mm)]
    story += [table([
        ["Concepto", "Representación", "Qué significa"],
        ["Predio", "Site", "Lugar general de la operación agrícola."],
        ["Parcela", 'StorageUnit / operation_type="field"', "Área específica dentro del predio."],
        ["Pluviómetro", 'Device / device_type="rain_gauge"', "Equipo registrado que envía telemetría."],
        ["Lectura", "Evento de telemetría", "Muestra UTC con métricas del dispositivo."],
    ], [35 * mm, 61 * mm, 72 * mm])]
    story.append(PageBreak())

    story += [p("3. Preparación antes del ESP32", "H1x")]
    story += bullets(["Empresa creada.", "Módulo PLUVIOMETRY habilitado para esa empresa.", "Predio creado.", "Parcela creada.", "Límite geográfico definido cuando corresponda."])
    story += [p("Ruta de trabajo", "H2x"), p("Configuración -> seleccionar predio -> seleccionar parcela -> Añadir pluviómetro", "Codex")]
    story += [p("4. Encontrar y confirmar la ubicación", "H1x")]
    story += [table([
        ["Paso", "Acción"],
        ["1", "Buscar lugar, municipio o coordenadas."],
        ["2", "Acercarse hasta reconocer el área correcta."],
        ["3", "Seleccionar la parcela."],
        ["4", "Activar Seleccionar ubicación en mapa."],
        ["5", "Marcar la posición exacta y confirmar coordenadas."],
        ["6", "Guardar el dispositivo."],
    ], [16 * mm, 152 * mm])]
    story += [p("Ejemplo DEMO: latitud -17.392800 | longitud -66.281400", "Callout")]
    story += [p("La latitud representa la posición norte-sur y la longitud la posición este-oeste. AgroEscudo guarda ambas en el Device; no se reenvían en cada lectura.")]
    story += [p("5. Crear el pluviómetro", "H1x")]
    story += [table([
        ["Campo", "Ejemplo"], ["Nombre", "P-01 Norte"], ["Device ID", "PLUV-001"], ["Predio", "Predio DEMO"], ["Parcela", "Parcela Norte DEMO"], ["Latitud / longitud", "-17.392800 / -66.281400"], ["Frecuencia", "15 minutos"], ["Template", "RAIN_GAUGE_BASE"], ["Estado inicial", "Esperando primera lectura"],
    ], [56 * mm, 112 * mm])]
    story.append(PageBreak())

    story += [p("6. Contrato actual de telemetría", "H1x"), p("El template RAIN_GAUGE_BASE define los seis canales que AgroEscudo espera para esta integración.")]
    story += [table([
        ["Canal", "Métrica", "Unidad", "Interpretación"],
        ["rain_1", "RAIN_DELTA_MM", "mm", "Lluvia desde la muestra anterior."],
        ["ambient_temp_1", "AMBIENT_TEMPERATURE_C", "degC", "Temperatura ambiente."],
        ["ambient_rh_1", "AMBIENT_RELATIVE_HUMIDITY_PCT", "percent", "Humedad relativa ambiente."],
        ["wind_speed_1", "WIND_SPEED_KMH", "km/h", "Velocidad del viento."],
        ["wind_direction_1", "WIND_DIRECTION_DEG", "degree", "Dirección del viento."],
        ["battery_1", "BATTERY_PERCENT", "percent", "Nivel estimado de batería."],
    ], [31 * mm, 53 * mm, 22 * mm, 62 * mm])]
    story += [p("RAIN_DELTA_MM es lluvia incremental desde la muestra anterior. No es un total acumulado que el sensor deba mantener.", "Callout")]
    story += [p("7. Ejemplo ESP32 HIL", "H1x"), p("El ejemplo validado está en:")]
    story += [p("hardware/pluviometry/esp32_hil/<br/>|-- esp32_hil.ino<br/>+-- secrets.example.h", "Codex")]
    story += [p("Copie secrets.example.h como secrets.h únicamente en la estación segura. secrets.h no se sube a Git y nunca debe contener credenciales copiadas en documentación.", "Callout")]
    story += [p("Alcance HIL", "H2x")]
    story += bullets(["Valida ESP32, WiFi, HTTP, API, base de datos y web.", "No valida sensores físicos, LoRa, batería real, montaje ni condiciones ambientales."])
    story.append(PageBreak())

    story += [p("8. Flujo de ingesta", "H1x"), p("POST /api/iot/v1/ingest/batch", "Codex")]
    story += [p("Cada lote identifica Gateway ID, Device ID, boot_id, sequence, timestamp UTC, métricas y firma HMAC. La firma demuestra que el emisor conoce el secreto asignado sin incluir ese secreto en el payload.")]
    story += [p("HTTP 200 + ACCEPTED = lectura aceptada", "Callout")]
    story += [p("9. Verificar la primera lectura", "H1x")]
    story += [table([
        ["Momento", "Estado esperado"],
        ["Antes de telemetría", "Esperando primera lectura"],
        ["Después de telemetría válida", "En línea / operational, según frescura"],
    ], [62 * mm, 106 * mm])]
    story += [p("Pluviometría -> mapa -> marcador -> popup -> Ver pluviómetro -> gráfico", "Codex")]
    story += [p("10. Estados operativos", "H1x")]
    story += [table([
        ["Estado", "Interpretación"],
        ["En línea", "Lecturas dentro del intervalo esperado."],
        ["Demorado", "La lectura supera la tolerancia normal."],
        ["Sin conexión", "No existen lecturas recientes suficientes."],
        ["Crítico", "Existe una alerta crítica real."],
    ], [38 * mm, 130 * mm])]
    story += [p("Crítico no significa simplemente offline. Una desconexión requiere atención, pero sólo una alerta crítica real debe producir estado crítico.", "Callout")]
    story += [p("11. Zona horaria", "H1x"), p("El ESP32 transmite UTC. El backend guarda UTC. AgroEscudo presenta la hora mediante Site.timezone.")]
    story += [p("05:40 UTC -> 01:40 Bolivia | America/La_Paz", "Codex")]
    story.append(PageBreak())

    story += [p("12. Checklist imprimible", "H1x"), p("Complete cada punto antes del cierre técnico.")]
    checklist = ["Empresa habilitada", "PLUVIOMETRY activo", "Predio creado", "Parcela creada", "Ubicación confirmada", "Device ID único", "RAIN_GAUGE_BASE asignado", "Credencial IoT aprovisionada", "ESP32 conectado", "Hora UTC sincronizada", "HTTP 200", "ACCEPTED", "Equipo aparece online", "Métricas visibles", "Histórico correcto"]
    checklist_rows = [[f"[ ] {item}", f"[ ] {checklist[index + 1]}" if index + 1 < len(checklist) else ""] for index, item in enumerate(checklist) if index % 2 == 0]
    checklist_table = Table([[Paragraph(cell, styles["Bodyx"]) for cell in row] for row in checklist_rows], colWidths=[84 * mm, 84 * mm])
    checklist_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("GRID", (0, 0), (-1, -1), 0.5, LINE), ("BACKGROUND", (0, 0), (-1, -1), colors.white), ("LEFTPADDING", (0, 0), (-1, -1), 8), ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    story += [checklist_table, Spacer(1, 6 * mm), p("Firma / responsable: __________________________________________", "Bodyx"), p("Fecha y hora de validación: ____________________________________", "Bodyx")]
    story.append(PageBreak())

    story += [p("13. Troubleshooting", "H1x")]
    story += [table([
        ["Síntoma", "Qué revisar"],
        ["ESP32 no conecta WiFi", "SSID y password en secrets.h; no publicarlos."],
        ["HTTP -1", "IP, backend, red y uso incorrecto de localhost."],
        ["HTTP 401", "HMAC, timestamp y nonce/secuencia."],
        ["duplicate", "El evento ya fue procesado; no crear una lectura nueva."],
        ["No aparece equipo", "Device ID y asignación a empresa, predio y parcela."],
        ["Mapa sin ubicación", "Latitud y longitud guardadas en el Device."],
        ["Hora incorrecta", "Site.timezone; no modificar UTC."],
        ["Sin datos", "Endpoint, respuesta de ingesta y lecturas aceptadas."],
    ], [50 * mm, 118 * mm])]
    story += [Spacer(1, 4 * mm), p("14. Seguridad", "H1x")]
    story += [p("Nunca incluya en PDFs, Git, capturas o mensajería:", "Bodyx")]
    story += bullets(["contraseña WiFi;", "secreto de gateway;", "JWT_SECRET;", "DATABASE_URL;", "clave MapTiler real;", "credenciales productivas."])
    story += [p("Use secretos dedicados por entorno, mantenga secrets.h fuera de Git y rote cualquier credencial expuesta.", "Callout")]
    story += [p("15. Cierre", "H1x"), p("La integración queda validada cuando el equipo está ubicado, la primera lectura fue aceptada, las métricas aparecen con hora Bolivia correcta y el histórico conserva continuidad. Este cierre valida software y comunicación HIL; no reemplaza la validación eléctrica, mecánica o ambiental del hardware de campo.")]
    return story


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=19 * mm,
        title="AgroEscudo - Guía de instalación y conexión de pluviómetros IoT",
        author="AgroEscudo",
        subject="Registro, ubicación, aprovisionamiento y validación de un dispositivo ESP32",
    )
    document.build(build_story(), onFirstPage=cover, onLaterPages=page_header_footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
