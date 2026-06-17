from __future__ import annotations

from io import BytesIO
from pathlib import Path
from textwrap import shorten

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Device, OperationalLog, SensorReading, StorageUnit
from app.schemas import WeeklyReportOut

GREEN_950 = colors.HexColor("#022C22")
GREEN_900 = colors.HexColor("#064E3B")
GREEN_700 = colors.HexColor("#047857")
AMBER = colors.HexColor("#D99A00")
TEXT = colors.HexColor("#334155")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#DDE7E2")
PAGE = colors.HexColor("#F8FAF9")
RED = colors.HexColor("#B91C1C")
LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "brand" / "logo-horizontal-transparent.png"


def build_weekly_pdf(db: Session, storage_unit: StorageUnit, report: WeeklyReportOut) -> bytes:
    device = db.scalar(select(Device).where(Device.storage_unit_id == storage_unit.id).order_by(Device.id))
    readings = list(
        db.scalars(
            select(SensorReading)
            .where(
                SensorReading.storage_unit_id == storage_unit.id,
                SensorReading.timestamp >= report.date_from,
                SensorReading.timestamp <= report.date_to,
            )
            .order_by(SensorReading.timestamp.desc())
        ).all()
    )
    alerts = list(
        db.scalars(
            select(Alert)
            .where(
                Alert.storage_unit_id == storage_unit.id,
                Alert.created_at >= report.date_from,
                Alert.created_at <= report.date_to,
            )
            .order_by(Alert.created_at.desc())
        ).all()
    )
    logs = list(
        db.scalars(
            select(OperationalLog)
            .where(
                OperationalLog.storage_unit_id == storage_unit.id,
                OperationalLog.timestamp >= report.date_from,
                OperationalLog.timestamp <= report.date_to,
            )
            .order_by(OperationalLog.timestamp.desc())
        ).all()
    )

    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=21 * mm,
        bottomMargin=18 * mm,
        title=f"AgroEscudo - {storage_unit.name}",
        author="AgroEscudo",
    )
    styles = _styles()
    story = []
    status = _status(alerts)

    story.extend(_cover(styles, report, status))
    story.append(PageBreak())
    story.extend(_summary(styles, report, readings, alerts))
    story.append(PageBreak())
    story.extend(_metrics(styles, report, storage_unit, device))
    story.append(PageBreak())
    story.extend(_alerts(styles, alerts))
    story.append(PageBreak())
    story.extend(_logs_and_recommendations(styles, logs, alerts, report))

    doc.build(
        story,
        onFirstPage=lambda canvas, current_doc: _decorate_page(canvas, current_doc, "Portada"),
        onLaterPages=lambda canvas, current_doc: _decorate_page(canvas, current_doc, f"Pag. {current_doc.page}"),
    )
    return output.getvalue()


def pdf_filename(storage_unit_name: str, generated_date) -> str:
    slug = "".join(char.lower() if char.isalnum() else "-" for char in storage_unit_name)
    slug = "-".join(part for part in slug.split("-") if part)[:60] or "storage-unit"
    return f"agroescudo-reporte-{slug}-{generated_date:%Y-%m-%d}.pdf"


def _styles():
    sample = getSampleStyleSheet()
    return {
        "brand": ParagraphStyle("brand", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=25, leading=28, textColor=GREEN_900),
        "tag": ParagraphStyle("tag", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=AMBER),
        "eyebrow": ParagraphStyle("eyebrow", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=8.5, leading=10, textColor=AMBER, spaceAfter=4),
        "cover_title": ParagraphStyle("cover_title", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=30, leading=33, textColor=GREEN_900, alignment=TA_LEFT),
        "section": ParagraphStyle("section", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=16, leading=19, textColor=GREEN_900, spaceAfter=8),
        "body": ParagraphStyle("body", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.5, leading=14, textColor=TEXT),
        "small": ParagraphStyle("small", parent=sample["BodyText"], fontName="Helvetica", fontSize=7.7, leading=10, textColor=MUTED),
        "table": ParagraphStyle("table", parent=sample["BodyText"], fontName="Helvetica", fontSize=7.4, leading=9.4, textColor=TEXT),
        "table_head": ParagraphStyle("table_head", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=7.2, leading=9, textColor=GREEN_900),
        "center": ParagraphStyle("center", parent=sample["BodyText"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=9.5, textColor=GREEN_900),
    }


def _cover(styles, report: WeeklyReportOut, status: str):
    meta = [
        ["Cliente / institucion", report.company_name, "Sitio", report.site_name],
        ["Silo / galpon", report.storage_unit_name, "Periodo", f"{_date(report.date_from)} - {_date(report.date_to)}"],
        ["Preparado por", "AgroEscudo", "Estado general", status],
        ["Estado del piloto", report.pilot_status.capitalize(), "Version", "Piloto 1.0"],
    ]
    return [
        Spacer(1, 1 * mm),
        _brand_logo(styles),
        Paragraph("Datos que protegen. Decisiones que transforman.", styles["tag"]),
        Spacer(1, 8 * mm),
        Paragraph("REPORTE TÉCNICO", styles["eyebrow"]),
        Paragraph("Reporte técnico de monitoreo postcosecha", styles["cover_title"]),
        Spacer(1, 3 * mm),
        Paragraph("Monitoreo IoT, trazabilidad operativa y gestión de riesgos para silos, galpones y centros de acopio.", styles["body"]),
        Spacer(1, 8 * mm),
        _table(styles, meta, [33 * mm, 53 * mm, 30 * mm, 50 * mm], header=False),
    ]


def _summary(styles, report, readings, alerts):
    latest = readings[0] if readings else None
    critical = len([alert for alert in alerts if alert.severity == "critical" and alert.is_active])
    consultation = (
        f"Se detectan {critical} alerta(s) critica(s) activa(s). Priorizar intervencion, inspeccion fisica y registro de accion correctiva."
        if critical
        else "No hay alertas criticas activas. Mantener monitoreo y rutina de revision operativa."
    )
    metrics = [
        ["Lecturas", str(report.reading_count), "Temp. maxima", _number(report.max_grain_temperature, " C")],
        ["Humedad maxima", _number(report.max_ambient_humidity, "%"), "Horas fuera rango", f"{report.approximate_hours_out_of_range} h"],
        ["Alertas generadas", str(report.alerts_generated), "Acciones registradas", str(len(report.operational_actions))],
    ]
    elements = [
        Paragraph("RESUMEN EJECUTIVO", styles["eyebrow"]),
        Paragraph("Condiciones registradas y evidencia operativa", styles["section"]),
        _card(styles, "Resumen técnico", _executive_summary(report, _status(alerts))),
        Spacer(1, 4 * mm),
        _card(styles, "Consulta operativa del sensor", consultation),
        Spacer(1, 5 * mm),
        _table(styles, metrics, [32 * mm, 24 * mm, 36 * mm, 30 * mm], header=False, large=True),
    ]
    if latest:
        elements.extend(
            [
                Spacer(1, 6 * mm),
                _card(
                    styles,
                    "Ultima lectura",
                    f"{_datetime(latest.timestamp)}. Temperatura de grano: {_number(latest.grain_temperature, ' C')}. "
                    f"Humedad ambiente: {_number(latest.ambient_humidity, '%')}. Batería: {_number(latest.battery_voltage, ' V', 2)}.",
                ),
            ]
        )
    return elements


def _metrics(styles, report, storage_unit, device):
    rows = [
        ["Métrica", "Valor", "Unidad", "Interpretación"],
        ["Temperatura máxima de grano", _number(report.max_grain_temperature), "C", "Vigilar evolución térmica."],
        ["Humedad ambiente máxima", _number(report.max_ambient_humidity), "%", "Revisar contra umbral configurado."],
        ["Número de lecturas", str(report.reading_count), "lecturas", "Volumen de evidencia del periodo."],
        ["Alertas generadas", str(report.alerts_generated), "alertas", "Eventos que requieren seguimiento."],
        ["Alertas resueltas", str(report.alerts_resolved), "alertas", "Cierre operativo documentado."],
        ["Horas fuera de rango", str(report.approximate_hours_out_of_range), "horas", "Exposición aproximada al riesgo."],
        ["Instalaciones", str(report.installation_count), "registros", "Evidencia de puesta en marcha."],
        ["Mantenimientos", str(report.maintenance_count), "registros", "Seguimiento técnico documentado."],
    ]
    asset = [
        ["Activo", storage_unit.name],
        ["Tipo", storage_unit.unit_type],
        ["Capacidad", f"{storage_unit.capacity_tons:g} t" if storage_unit.capacity_tons else "Dato no disponible"],
        ["Dispositivo", device.external_id if device else "Dato no disponible"],
        ["Estado nodo", "Activo" if device and device.is_active else "Dato no disponible"],
    ]
    return [
        Paragraph("METRICAS PRINCIPALES", styles["eyebrow"]),
        Paragraph("Indicadores tecnicos del periodo", styles["section"]),
        _table(styles, rows, [53 * mm, 25 * mm, 24 * mm, 64 * mm], header=True),
        Spacer(1, 8 * mm),
        Paragraph("ACTIVO MONITOREADO", styles["eyebrow"]),
        _table(styles, asset, [42 * mm, 124 * mm], header=False, large=True),
    ]


def _alerts(styles, alerts):
    rows = [["Fecha", "Evento", "Nivel", "Estado", "Recomendacion"]]
    rows.extend(
        [
            [
                _datetime(alert.created_at),
                alert.title,
                _severity(alert.severity),
                "Activa" if alert.is_active else "Resuelta",
                _recommendation_for(alert),
            ]
            for alert in alerts[:16]
        ]
    )
    return [
        Paragraph("ALERTAS Y EVENTOS", styles["eyebrow"]),
        Paragraph("Riesgos detectados por AgroEscudo", styles["section"]),
        _table(styles, rows, [24 * mm, 43 * mm, 20 * mm, 18 * mm, 61 * mm], header=True),
    ]


def _logs_and_recommendations(styles, logs, alerts, report):
    rows = [["Fecha", "Operador", "Registro operativo", "Alerta"]]
    rows.extend(
        [
            [
                _datetime(log.timestamp),
                log.operator_name,
                f"{log.action_taken}. {shorten(log.notes or 'Sin notas adicionales.', width=190, placeholder='...')}",
                f"#{log.alert_id}" if log.alert_id else "Sin alerta",
            ]
            for log in logs[:16]
        ]
    )
    recommendations = _recommendations(alerts, report)
    return [
        Paragraph("BITACORA OPERATIVA", styles["eyebrow"]),
        Paragraph("Acciones registradas durante el periodo", styles["section"]),
        _table(styles, rows, [24 * mm, 28 * mm, 96 * mm, 18 * mm], header=True),
        Spacer(1, 7 * mm),
        Paragraph("CONCLUSIONES Y RECOMENDACIONES", styles["eyebrow"]),
        *[_card(styles, f"Recomendacion {index + 1}", text) for index, text in enumerate(recommendations)],
        Spacer(1, 3 * mm),
        Paragraph("Las entradas de bitácora constituyen evidencia registrada por operadores. Validar redacción antes de entregar a un cliente externo.", styles["small"]),
    ]


def _card(styles, title, text):
    content = Table(
        [[Paragraph(title, styles["table_head"])], [Paragraph(text, styles["body"])]],
        colWidths=[166 * mm],
    )
    content.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PAGE),
                ("BOX", (0, 0), (-1, -1), 0.7, LINE),
                ("LINEBEFORE", (0, 0), (0, -1), 2.5, AMBER),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return KeepTogether([content, Spacer(1, 3 * mm)])


def _table(styles, rows, widths, header, large=False):
    cells = []
    for row_index, row in enumerate(rows):
        style = styles["table_head"] if header and row_index == 0 else styles["table"]
        cells.append([Paragraph(str(value), style) for value in row])
    table = Table(cells, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    rules = [
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), PAGE if header else colors.white),
        ("TOPPADDING", (0, 0), (-1, -1), 8 if large else 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8 if large else 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]
    table.setStyle(TableStyle(rules))
    return table


def _decorate_page(canvas, doc, label):
    width, height = A4
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.6)
    canvas.line(18 * mm, height - 13 * mm, width - 18 * mm, height - 13 * mm)
    canvas.line(18 * mm, 12 * mm, width - 18 * mm, 12 * mm)
    canvas.setStrokeColor(AMBER)
    canvas.line(width - 50 * mm, height - 13 * mm, width - 18 * mm, height - 13 * mm)
    canvas.setFillColor(GREEN_900)
    canvas.setFont("Helvetica-Bold", 8)
    canvas.drawString(18 * mm, 7 * mm, "AgroEscudo / Evidencia operativa postcosecha")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(width - 18 * mm, 7 * mm, label)
    canvas.restoreState()


def _executive_summary(report, status):
    if not report.reading_count:
        return "No se cuenta con evidencia suficiente para emitir una conclusión técnica del periodo. Validar conectividad del dispositivo y continuidad de lecturas."
    if status == "Crítico":
        return "Durante el periodo analizado se identificaron condiciones fuera de rango que requieren seguimiento operativo, inspección física y registro de acciones correctivas."
    if status == "Alerta":
        return "Durante el periodo analizado se identificaron condiciones preventivas que requieren observación operativa y seguimiento en bitácora."
    return "Durante el periodo analizado, las condiciones registradas se mantuvieron dentro de rangos operativos aceptables."


def _recommendations(alerts, report):
    if not report.reading_count:
        return ["No se cuenta con evidencia suficiente para emitir conclusión técnica."]
    values = []
    if any(alert.severity == "critical" for alert in alerts):
        values.append("Priorizar intervención operativa y documentar acción correctiva.")
    if any("humidity" in alert.alert_type for alert in alerts):
        values.append("Revisar ventilación, aireación y posibles puntos de condensación.")
    if any("temperature" in alert.alert_type or "environment" in alert.alert_type for alert in alerts):
        values.append("Inspeccionar físicamente el punto monitoreado y verificar acumulación térmica.")
    if any("battery" in alert.alert_type for alert in alerts):
        values.append("Programar revisión técnica del nodo.")
    return values or ["Mantener monitoreo semanal, bitácora operativa y revisión periódica de umbrales."]


def _recommendation_for(alert):
    if "humidity" in alert.alert_type:
        return "Revisar ventilación, aireación y condensación."
    if "temperature" in alert.alert_type or "environment" in alert.alert_type:
        return "Inspeccionar punto monitoreado y acumulación térmica."
    if "battery" in alert.alert_type:
        return "Programar revisión técnica del nodo."
    return "Evaluar condición y registrar acción."


def _status(alerts):
    if any(alert.severity == "critical" for alert in alerts):
        return "Crítico"
    if alerts:
        return "Alerta"
    return "Normal"


def _severity(value):
    return {"critical": "Crítica", "warning": "Preventiva", "technical": "Técnica"}.get(value, value)


def _brand_logo(styles):
    if LOGO_PATH.exists():
        return Image(str(LOGO_PATH), width=55 * mm, height=31 * mm)
    return Paragraph("AgroEscudo", styles["brand"])


def _date(value):
    return value.strftime("%d/%m/%Y")


def _datetime(value):
    return value.strftime("%d/%m/%Y %H:%M")


def _number(value, suffix="", digits=1):
    return "Dato no disponible" if value is None else f"{value:.{digits}f}{suffix}"
