from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "AgroEscudo_Handoff_Hardware_Pluviometria.pdf"
LOGO = ROOT / "backend" / "app" / "assets" / "brand" / "logo-horizontal-transparent.png"
FONT_REGULAR = Path("C:/Windows/Fonts/arial.ttf")
FONT_BOLD = Path("C:/Windows/Fonts/arialbd.ttf")

PAGE_W, PAGE_H = A4
GREEN = colors.HexColor("#064E3B")
GREEN_2 = colors.HexColor("#0B6B4D")
EMERALD = colors.HexColor("#10B981")
GOLD = colors.HexColor("#D99A00")
INK = colors.HexColor("#14251F")
MUTED = colors.HexColor("#5C6E67")
PALE = colors.HexColor("#ECFDF5")
PALE_GOLD = colors.HexColor("#FFF8E7")
LINE = colors.HexColor("#D3E3DC")
SOFT = colors.HexColor("#F7FAF8")

if FONT_REGULAR.exists() and FONT_BOLD.exists():
    pdfmetrics.registerFont(TTFont("AgroRegular", str(FONT_REGULAR)))
    pdfmetrics.registerFont(TTFont("AgroBold", str(FONT_BOLD)))
    REGULAR = "AgroRegular"
    BOLD = "AgroBold"
else:
    REGULAR = "Helvetica"
    BOLD = "Helvetica-Bold"

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverTitle", fontName=BOLD, fontSize=27, leading=33, textColor=colors.white, alignment=TA_LEFT, spaceAfter=12))
styles.add(ParagraphStyle(name="CoverSubtitle", fontName=REGULAR, fontSize=13.5, leading=20, textColor=colors.HexColor("#D1FAE5"), spaceAfter=12))
styles.add(ParagraphStyle(name="Status", fontName=BOLD, fontSize=12, leading=16, textColor=GREEN, alignment=TA_CENTER, backColor=colors.white, borderColor=GOLD, borderWidth=1, borderPadding=9, spaceAfter=10))
styles.add(ParagraphStyle(name="H1", fontName=BOLD, fontSize=20, leading=24, textColor=GREEN, spaceBefore=2, spaceAfter=9))
styles.add(ParagraphStyle(name="H2", fontName=BOLD, fontSize=12.5, leading=16, textColor=GREEN_2, spaceBefore=7, spaceAfter=4))
styles.add(ParagraphStyle(name="Body", fontName=REGULAR, fontSize=9.2, leading=13.5, textColor=INK, spaceAfter=5))
styles.add(ParagraphStyle(name="Small", fontName=REGULAR, fontSize=7.7, leading=10.5, textColor=MUTED, spaceAfter=3))
styles.add(ParagraphStyle(name="BulletX", fontName=REGULAR, fontSize=8.9, leading=12.5, textColor=INK, leftIndent=12, firstLineIndent=-7, spaceAfter=2.5))
styles.add(ParagraphStyle(name="CodeX", fontName="Courier", fontSize=7.9, leading=10.5, textColor=GREEN, backColor=PALE, borderColor=LINE, borderWidth=0.5, borderPadding=7, spaceBefore=8, spaceAfter=8))
styles.add(ParagraphStyle(name="Callout", fontName=BOLD, fontSize=8.9, leading=12.5, textColor=GREEN, backColor=PALE, borderColor=EMERALD, borderWidth=0.8, borderPadding=8, spaceBefore=10, spaceAfter=8))
styles.add(ParagraphStyle(name="Warning", fontName=BOLD, fontSize=8.9, leading=12.5, textColor=colors.HexColor("#7C4A03"), backColor=PALE_GOLD, borderColor=GOLD, borderWidth=0.8, borderPadding=8, spaceBefore=10, spaceAfter=8))
styles.add(ParagraphStyle(name="Cell", fontName=REGULAR, fontSize=7.1, leading=9.4, textColor=INK))
styles.add(ParagraphStyle(name="CellHead", fontName=BOLD, fontSize=7.2, leading=9.5, textColor=colors.white))


def p(text: str, style: str = "Body") -> Paragraph:
    return Paragraph(text, styles[style])


def bullets(items: list[str]) -> list[Paragraph]:
    return [Paragraph(f"- {item}", styles["BulletX"]) for item in items]


def data_table(rows: list[list[str]], widths: list[float], repeat: bool = True) -> Table:
    data = []
    for row_index, row in enumerate(rows):
        style = styles["CellHead"] if row_index == 0 else styles["Cell"]
        data.append([Paragraph(str(cell), style) for cell in row])
    result = Table(data, colWidths=widths, repeatRows=1 if repeat else 0, hAlign="LEFT")
    result.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
    ]))
    return result


class Pipeline(Flowable):
    def __init__(self, labels: list[str], width: float = 168 * mm, height: float = 29 * mm):
        super().__init__()
        self.labels = labels
        self.width = width
        self.height = height

    def draw(self):
        canvas = self.canv
        gap = 4 * mm
        box_w = (self.width - gap * (len(self.labels) - 1)) / len(self.labels)
        y = 6 * mm
        box_h = 17 * mm
        for index, label in enumerate(self.labels):
            x = index * (box_w + gap)
            canvas.setFillColor(PALE if index % 2 == 0 else PALE_GOLD)
            canvas.setStrokeColor(EMERALD if index % 2 == 0 else GOLD)
            canvas.roundRect(x, y, box_w, box_h, 3, fill=1, stroke=1)
            canvas.setFillColor(GREEN)
            canvas.setFont(BOLD, 6.7)
            words = label.split()
            split_at = max(1, len(words) // 2)
            lines = [label] if len(label) <= 14 else [" ".join(words[:split_at]), " ".join(words[split_at:])]
            for line_index, line in enumerate(lines):
                canvas.drawCentredString(x + box_w / 2, y + box_h / 2 + 2 - line_index * 8, line)
            if index < len(self.labels) - 1:
                start = x + box_w + 0.8 * mm
                end = x + box_w + gap - 0.8 * mm
                mid = y + box_h / 2
                canvas.setStrokeColor(GOLD)
                canvas.line(start, mid, end, mid)
                canvas.line(end, mid, end - 1.7 * mm, mid + 1.3 * mm)
                canvas.line(end, mid, end - 1.7 * mm, mid - 1.3 * mm)


def cover_page(canvas, _doc):
    canvas.saveState()
    canvas.setFillColor(GREEN)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    canvas.setFillColor(GREEN_2)
    canvas.circle(PAGE_W - 10 * mm, PAGE_H - 20 * mm, 56 * mm, fill=1, stroke=0)
    canvas.setFillColor(colors.HexColor("#075A43"))
    canvas.circle(10 * mm, 16 * mm, 42 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(GOLD)
    canvas.setLineWidth(2)
    canvas.line(18 * mm, 31 * mm, PAGE_W - 18 * mm, 31 * mm)
    canvas.restoreState()


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, PAGE_H - 17 * mm, PAGE_W - 18 * mm, PAGE_H - 17 * mm)
    canvas.setFont(BOLD, 7.6)
    canvas.setFillColor(GREEN)
    canvas.drawString(18 * mm, PAGE_H - 13 * mm, "AGROESCUDO | HANDOFF DE HARDWARE | PLUVIOMETRÍA")
    canvas.setFont(REGULAR, 7.1)
    canvas.setFillColor(MUTED)
    canvas.drawRightString(PAGE_W - 18 * mm, PAGE_H - 13 * mm, "Versión 1.0 | 28 septiembre 2026")
    canvas.line(18 * mm, 14 * mm, PAGE_W - 18 * mm, 14 * mm)
    canvas.drawString(18 * mm, 9.5 * mm, "Documento técnico | Sin secretos productivos")
    canvas.drawRightString(PAGE_W - 18 * mm, 9.5 * mm, f"Página {doc.page}")
    canvas.restoreState()


def story() -> list:
    items = []
    items += [Spacer(1, 27 * mm), Image(str(LOGO), width=73 * mm, height=20 * mm), Spacer(1, 30 * mm)]
    items += [p("Handoff técnico de hardware<br/>Pluviometría IoT", "CoverTitle")]
    items += [p("Qué debe construir y entregar hardware para ser compatible con AgroEscudo", "CoverSubtitle")]
    items += [Spacer(1, 8 * mm), p("PLUVIOMETRÍA SOFTWARE MVP", "CoverSubtitle")]
    items += [p("SOFTWARE READY FOR HARDWARE INTEGRATION", "Status")]
    items += [Spacer(1, 30 * mm), p("Para colaboradores de electrónica, firmware, integración y validación de sensores.", "CoverSubtitle")]
    items += [p("Versión 1.0 | 28 septiembre 2026", "CoverSubtitle")]
    items += [p("No contiene contraseñas, secrets, tokens ni credenciales productivas.", "CoverSubtitle")]
    items.append(PageBreak())

    items += [p("1. Estado y resultado esperado", "H1")]
    items += [p("El software productivo está aprobado. El equipo de hardware debe entregar una unidad que produzca datos físicos calibrados y complete la cadena end-to-end sin alterar el contrato canónico.")]
    items += [Pipeline(["Sensores", "ESP32", "Comunicación", "Ingesta", "Telemetry Event", "Metric Reading", "Dashboard"])]
    items += [p("Terminado en software", "H2")]
    items += bullets(["Registro de predios, parcelas y pluviómetros.", "Ingesta HMAC, validación, deduplicación y normalización.", "Mapa, dashboard, gráfico, histórico y estados operativos.", "HIL físico ESP32 -> WiFi -> API -> HTTP 200 -> ACCEPTED -> dashboard."])
    items += [p("Pendiente de hardware", "H2")]
    items += bullets(["Selección e integración de sensores reales.", "Conversión a unidades canónicas y calibración trazable.", "Firmware versionado, identidad y tiempo UTC.", "Pruebas de reinicio, red, recuperación y aceptación end-to-end.", "Diseño posterior de buffer/store-and-forward."])
    items += [Spacer(1, 3 * mm)]
    items += [p("El HIL es referencia de integración; no es firmware definitivo y no valida sensores, autonomía, LoRa ni campo.", "Warning")]
    items.append(PageBreak())

    items += [p("2. Contrato final de métricas", "H1")]
    items += [data_table([
        ["Canal", "Métrica", "Unidad", "Rango", "Semántica"],
        ["rain_1", "RAIN_DELTA_MM", "mm", "x >= 0", "Incremento desde la lectura anterior."],
        ["ambient_temp_1", "AMBIENT_TEMPERATURE_C", "degC", "-40 <= x <= 80", "Temperatura ambiente."],
        ["ambient_rh_1", "AMBIENT_RELATIVE_HUMIDITY_PCT", "percent", "0 <= x <= 100", "Humedad relativa."],
        ["wind_speed_1", "WIND_SPEED_KMH", "km/h", "x >= 0", "Velocidad del viento."],
        ["wind_direction_1", "WIND_DIRECTION_DEG", "degree", "0 <= x < 360", "Dirección meteorológica: de dónde viene."],
        ["battery_1", "BATTERY_PERCENT", "percent", "0 <= x <= 100", "Porcentaje de batería."],
    ], [25 * mm, 58 * mm, 18 * mm, 25 * mm, 42 * mm])]
    items += [p("Los nombres y unidades son exactos. Todos los valores deben ser finitos; no enviar NaN, infinito ni strings numéricos.", "Callout")]
    items += [p("Lluvia: delta, no acumulado", "H2")]
    items += [p("Si el acumulado físico cambia de 12.0 mm a 12.4 mm, AgroEscudo debe recibir <b>RAIN_DELTA_MM = 0.4</b>. No debe recibir 12.4 como delta.")]
    items += [p("La solución final de reinicio, overflow, tara, rebote, ruido, resolución y persistencia depende del sensor elegido y debe documentarse después de seleccionarlo.", "Warning")]
    items += [p("Dirección del viento", "H2")]
    items += [p("La convención es meteorológica: 0 grados representa viento que viene del Norte. El firmware debe tratar correctamente 359 -> 0 -> 1 y nunca enviar 360.")]
    items.append(PageBreak())

    items += [p("3. Identidad, tiempo y resultados", "H1")]
    items += [data_table([
        ["Campo", "Regla de hardware"],
        ["Device ID", "Usar el identificador físico aprobado, por ejemplo PLUV-001. No usar el ID interno de base de datos."],
        ["boot_id", "Nuevo valor por ciclo de arranque."],
        ["sequence", "Monotónica dentro del arranque; puede volver a 0 con nuevo boot_id."],
        ["sample_counter", "Contador de adquisiciones para diagnosticar pérdidas."],
        ["batch_id", "Identidad única de cada lote HTTP."],
        ["nonce", "Valor anti-replay; no reutilizar con el mismo gateway."],
        ["timestamp_utc", "Unix epoch UTC obtenido con NTP."],
    ], [36 * mm, 132 * mm])]
    items += [p("Mismo Device ID + boot_id + sequence = DUPLICATE", "Callout")]
    items += [p("No restar manualmente cuatro horas. El ESP32 y el backend trabajan en UTC; la presentación Bolivia usa Site.timezone = America/La_Paz.", "Warning")]
    items += [p("Clasificación real", "H2")]
    items += [data_table([
        ["Resultado", "Cuándo ocurre", "Persistencia"],
        ["HTTP 422", "JSON/modelo inválido o rango canónico inválido.", "El lote no se procesa."],
        ["QUARANTINED", "Canal, unidad, métrica o plantilla incompatibles.", "No crea evento ni métricas normalizadas."],
        ["ACCEPTED", "Autenticación, contrato y persistencia correctos.", "Crea TelemetryEvent y MetricReading."],
        ["DUPLICATE", "Identidad de muestra ya almacenada.", "No duplica la lectura."],
        ["REJECTED", "Dispositivo/perfil/rango legacy no autorizado o inválido.", "No crea lectura operacional."],
    ], [28 * mm, 87 * mm, 53 * mm])]
    items.append(PageBreak())

    items += [p("4. Orden de integración de sensores", "H1")]
    items += [data_table([
        ["Fase", "Sensor", "Salida AgroEscudo", "Cierre de fase"],
        ["1", "SHT31", "Temperatura + humedad", "Estable, finita, rango y referencia."],
        ["2", "Pluviómetro", "RAIN_DELTA_MM", "Delta repetible, cero y varios puntos."],
        ["3", "Anemómetro", "WIND_SPEED_KMH", "Cero, escala y referencia."],
        ["4", "Veleta", "WIND_DIRECTION_DEG", "Convención, orientación y cruce 359/0."],
        ["5", "Batería", "BATTERY_PERCENT", "Coherencia con multímetro y curva."],
    ], [15 * mm, 34 * mm, 48 * mm, 71 * mm])]
    items += [p("Una fase a la vez", "H2")]
    items += bullets(["Leer localmente sin NaN ni inestabilidad.", "Convertir a la unidad exacta.", "Calibrar y registrar error.", "Enviar JSON firmado.", "Obtener HTTP 200 + ACCEPTED.", "Confirmar mapa y gráfico.", "Repetir tras reinicio y falla básica."])
    items += [p("Criterios mínimos", "H2")]
    items += bullets(["Temperatura y humedad: comparación con referencia.", "Lluvia: deltas no negativos, repetibles y calibrados.", "Viento: cero y escala correctos.", "Dirección: orientación física y 0/360 correctamente tratados.", "Batería: estimación explicada y comparada con multímetro."])
    items += [Spacer(1, 3 * mm)]
    items += [p("Ver correctamente una variable por Serial no la convierte en una variable terminada.", "Callout")]
    items.append(PageBreak())

    items += [p("5. Calibración y evidencia", "H1")]
    items += [p("Cada sesión debe registrar instrumento de referencia, valor real, valor sensor, errores, corrección, fecha UTC, responsable y versión de firmware.")]
    items += [data_table([
        ["Punto", "Valor real", "Valor sensor", "Error abs.", "Error rel. %", "Factor/offset", "Resultado"],
        ["1", "", "", "", "", "", ""],
        ["2", "", "", "", "", "", ""],
        ["3", "", "", "", "", "", ""],
        ["4", "", "", "", "", "", ""],
        ["5", "", "", "", "", "", ""],
    ], [14 * mm, 26 * mm, 27 * mm, 23 * mm, 24 * mm, 31 * mm, 23 * mm])]
    items += [Spacer(1, 3 * mm)]
    items += [p("error absoluto = valor sensor - valor real<br/>error relativo (%) = 100 * |error absoluto| / |valor real|", "CodeX")]
    items += [p("Para lluvia", "H2")]
    items += bullets(["Varios volúmenes o niveles equivalentes de precipitación.", "Varias repeticiones y verificación de cero.", "Área del colector, pulsos, resolución, drenaje y pérdidas documentados.", "Pruebas de reinicio, overflow y debounce/ruido."])
    items += [Spacer(1, 3 * mm)]
    items += [p("No declarar una precisión que el fabricante y el ensayo no demuestren. La tolerancia final debe acordarse con AgroEscudo según el uso agronómico.", "Warning")]
    items += [p("Evidencia por fase", "H2")]
    items += bullets(["Esquema, pinout y hoja técnica.", "Fórmula de conversión y frecuencia de muestreo.", "Tabla de calibración.", "Logs sanitizados, respuesta API y captura de gráfico.", "Firmware versionado y lista de desviaciones."])
    items.append(PageBreak())

    items += [p("6. Prueba end-to-end y resiliencia", "H1")]
    items += [Pipeline(["Sensor real", "ESP32", "JSON", "HMAC", "HTTP 200", "ACCEPTED", "DB", "Mapa y gráfico"])]
    items += [p("Pruebas obligatorias", "H2")]
    items += bullets(["Rangos válidos y límites.", "HTTP 422 con payload/rango inválido.", "QUARANTINED con canal o unidad incorrectos.", "DUPLICATE sin segunda lectura.", "Nuevo boot_id después de reinicio.", "HTTP 401 con firma incorrecta.", "Hora local correcta sin modificar UTC.", "Ejecución prolongada sin degradación relevante."])
    items += [p("Deuda offline conocida", "H2")]
    items += [p("El HIL actual no tiene store-and-forward. El firmware productivo deberá abordar más adelante pérdida de red, buffer, reintentos con backoff, persistencia, conservación de identidad, deduplicación y recuperación tras reinicio.")]
    items += [Spacer(1, 2 * mm)]
    items += [p("No declarar recuperación offline implementada hasta demostrar que las muestras sobreviven a desconexión y corte de energía sin pérdidas ni duplicados.", "Warning")]
    items += [p("Paquete de evidencia", "H2")]
    items += bullets(["Informe de pruebas con fecha UTC.", "Logs y JSON sanitizados.", "Respuestas ACCEPTED/DUPLICATE/errores esperados.", "Capturas de mapa y gráfico.", "Calibración, versión de firmware y fallas conocidas."])
    items.append(PageBreak())

    items += [p("7. Seguridad y entrega", "H1")]
    items += [p("Firma conceptual", "H2")]
    items += [p("body_hash = SHA256(body exacto)<br/>mensaje = gateway_id + timestamp + nonce + body_hash<br/>firma = HMAC-SHA256(secret dedicado, mensaje)", "CodeX")]
    items += [p("No usar una clave global compartida. Cada entorno/unidad o gateway debe aprovisionarse con una credencial dedicada, entregada por canal seguro y fuera de Git.", "Callout")]
    items += [p("Sí puede recibir", "H2")]
    items += bullets(["Guía de instalación y PDF de handoff.", "Documentación de este paquete.", "esp32_hil.ino y secrets.example.h.", "Contratos, diagramas, códigos de métricas y checklist."])
    items += [p("Nunca entregar por Git", "H2")]
    items += bullets(["secrets.h, WiFi real o gateway secrets.", "DATABASE_URL, JWT_SECRET o claves MapTiler.", "Tokens, contraseñas, archivos .env o dumps.", "Logs con credenciales o encabezados reutilizables."])
    items += [Spacer(1, 3 * mm)]
    items += [p("Este paquete no modifica frontend, backend, Neon, Render ni Vercel. Tampoco implementa sensores, LoRa o firmware productivo.", "Warning")]
    items.append(PageBreak())

    items += [p("8. Checklist final del colaborador", "H1")]
    checks = [
        "ESP32 identificado", "firmware versionado", "timestamp UTC", "Device ID correcto",
        "temperatura", "humedad", "lluvia delta", "viento", "dirección", "batería",
        "rangos válidos", "HMAC", "HTTP 200", "ACCEPTED", "datos visibles en dashboard",
        "calibración documentada", "pruebas de reinicio", "pruebas sin red",
    ]
    rows = []
    for index in range(0, len(checks), 2):
        left = f"[ ] {checks[index]}"
        right = f"[ ] {checks[index + 1]}" if index + 1 < len(checks) else ""
        rows.append([left, right])
    checklist = Table([[Paragraph(cell, styles["Body"]) for cell in row] for row in rows], colWidths=[84 * mm, 84 * mm])
    checklist.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    items += [checklist, Spacer(1, 7 * mm)]
    items += [p("Device ID: ______________________________________________")]
    items += [p("Firmware / commit: ______________________________________")]
    items += [p("Responsable hardware: __________________________________")]
    items += [p("Responsable AgroEscudo: ________________________________")]
    items += [p("Fecha/hora UTC: _________________________________________")]
    items += [p("Resultado:  [ ] APROBADO   [ ] RECHAZADO   [ ] CON OBSERVACIONES", "Callout")]
    items += [Spacer(1, 4 * mm), p("SOFTWARE READY FOR HARDWARE INTEGRATION", "Status")]
    return items


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = SimpleDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=19 * mm,
        title="AgroEscudo - Handoff técnico de hardware de Pluviometría",
        author="AgroEscudo",
        subject="Contrato y criterios de entrega del hardware de pluviómetro compatible con AgroEscudo",
    )
    document.build(story(), onFirstPage=cover_page, onLaterPages=header_footer)
    print(OUTPUT)


if __name__ == "__main__":
    main()
