from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from statistics import mean

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Alert,
    Company,
    Device,
    IotDevice,
    IotGateway,
    MaintenanceRecord,
    SensorCalibration,
    SensorReading,
    ServiceCase,
    Site,
    StoredFile,
    StorageUnit,
    User,
    utc_now,
)
from app.services.pilot_operations import build_pilot_metrics, gateway_effective_status

GREEN = colors.HexColor("#064E3B")
EMERALD = colors.HexColor("#047857")
AMBER = colors.HexColor("#D99A00")
TEXT = colors.HexColor("#334155")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#DDE7E2")
SOFT = colors.HexColor("#F8FAF9")
RED = colors.HexColor("#B91C1C")
LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "brand" / "logo-horizontal-transparent.png"


def build_executive_report(
    db: Session,
    user: User,
    units: list[StorageUnit],
    *,
    date_from: datetime,
    date_to: datetime,
    responsible: str,
) -> bytes:
    context = _context(db, units, date_from, date_to)
    metrics = build_pilot_metrics(
        db,
        user,
        date_from=date_from,
        date_to=date_to,
        company_id=units[0].company_id if _single_company(units) else None,
        storage_unit_id=units[0].id if len(units) == 1 else None,
    )
    report_number = _report_number("EXEC", units, date_to)
    story = _cover(
        "Reporte ejecutivo de operacion",
        "Evidencia de monitoreo, alertas y respuesta operativa",
        report_number,
        units,
        date_from,
        date_to,
        responsible,
    )
    story += [
        PageBreak(),
        _title("Resumen ejecutivo"),
        Paragraph(_executive_summary(context), _styles()["body"]),
        Spacer(1, 5 * mm),
        _kpi_table(
            [
                ("Cobertura de datos", _percent(metrics.data_availability.get("coverage_percent"))),
                ("Lecturas validas", _value(metrics.data_availability.get("valid_readings"))),
                ("Dispositivos operativos", str(context["operational_devices"])),
                ("Dispositivos fuera de linea", str(context["offline_devices"])),
                ("Alertas criticas", str(context["critical_alerts"])),
                ("Incidentes", str(len(context["incidents"]))),
                ("Tiempo medio de reconocimiento", _minutes(metrics.operations.get("mean_acknowledgement_minutes"))),
                ("Tiempo medio de resolucion", _minutes(metrics.operations.get("mean_resolution_minutes"))),
            ]
        ),
        Spacer(1, 7 * mm),
        _title("Evolucion de variables clave"),
        _variable_evolution(context["readings"]),
        Spacer(1, 7 * mm),
        _title("Eventos relevantes"),
        _alerts_table(context["alerts"], technical=False),
        PageBreak(),
        _title("Acciones y mantenimiento relevante"),
        _maintenance_table(context["maintenance"], technical=False),
        Spacer(1, 7 * mm),
        _title("Recomendaciones operativas"),
        *_recommendation_paragraphs(context),
        Spacer(1, 7 * mm),
        Paragraph(
            "Alcance: este reporte resume evidencia registrada por AgroEscudo. No constituye certificacion, "
            "diagnostico definitivo, garantia de ahorro ni sustituto de inspeccion fisica.",
            _styles()["notice"],
        ),
    ]
    return _build_pdf(story, report_number, "Reporte ejecutivo AgroEscudo")


def build_technical_report(
    db: Session,
    user: User,
    units: list[StorageUnit],
    *,
    date_from: datetime,
    date_to: datetime,
    responsible: str,
) -> bytes:
    context = _context(db, units, date_from, date_to)
    metrics = build_pilot_metrics(
        db,
        user,
        date_from=date_from,
        date_to=date_to,
        company_id=units[0].company_id if _single_company(units) else None,
        storage_unit_id=units[0].id if len(units) == 1 else None,
    )
    report_number = _report_number("TECH", units, date_to)
    story = _cover(
        "Reporte tecnico de operacion",
        "Diagnostico de nodos, conectividad, calidad de datos y mantenimiento",
        report_number,
        units,
        date_from,
        date_to,
        responsible,
    )
    story += [
        PageBreak(),
        _title("Inventario tecnico"),
        _device_table(context["devices"], context["latest"], context["gateway_by_device"]),
        Spacer(1, 7 * mm),
        _title("Calibracion y calidad de datos"),
        _technical_quality_table(metrics, context),
        Spacer(1, 7 * mm),
        _title("Fallas y alertas"),
        _alerts_table(context["alerts"], technical=True),
        PageBreak(),
        _title("Mantenimiento y evidencias"),
        _maintenance_table(context["maintenance"], technical=True),
        Spacer(1, 6 * mm),
        Paragraph(
            f"Evidencias vigentes asociadas: {context['evidence_count']}. "
            f"Proximas revisiones programadas: {context['next_reviews']}.",
            _styles()["body"],
        ),
        Spacer(1, 7 * mm),
        _title("Recomendaciones tecnicas"),
        *_technical_recommendations(context),
        Spacer(1, 7 * mm),
        Paragraph(
            "Anexo operativo. Los valores de disponibilidad se estiman desde cadencia configurada y marcas de tiempo. "
            "Cuando no existe cadencia, la cobertura se presenta como no calculable.",
            _styles()["notice"],
        ),
    ]
    return _build_pdf(story, report_number, "Reporte tecnico AgroEscudo")


def report_filename(kind: str, units: list[StorageUnit], date_to: datetime) -> str:
    scope = units[0].name if len(units) == 1 else "operacion"
    slug = "-".join("".join(char.lower() if char.isalnum() else " " for char in scope).split())[:60]
    return f"agroescudo-{kind}-{slug or 'piloto'}-{date_to:%Y-%m-%d}.pdf"


def _context(db: Session, units: list[StorageUnit], date_from: datetime, date_to: datetime) -> dict[str, object]:
    unit_ids = [item.id for item in units]
    devices = list(db.scalars(select(Device).where(Device.storage_unit_id.in_(unit_ids))).all())
    device_ids = [item.id for item in devices]
    readings = list(
        db.scalars(
            select(SensorReading)
            .where(
                SensorReading.device_id.in_(device_ids) if device_ids else SensorReading.id == -1,
                SensorReading.timestamp >= date_from,
                SensorReading.timestamp <= date_to,
            )
            .order_by(SensorReading.timestamp)
        ).all()
    )
    latest: dict[int, SensorReading] = {}
    for reading in readings:
        latest[reading.device_id] = reading
    alerts = list(
        db.scalars(
            select(Alert)
            .where(
                Alert.storage_unit_id.in_(unit_ids),
                Alert.created_at >= date_from,
                Alert.created_at <= date_to,
            )
            .order_by(Alert.created_at.desc())
        ).all()
    )
    incidents = list(
        db.scalars(
            select(ServiceCase).where(
                ServiceCase.storage_unit_id.in_(unit_ids),
                ServiceCase.created_at >= date_from,
                ServiceCase.created_at <= date_to,
            )
        ).all()
    )
    maintenance = list(
        db.scalars(
            select(MaintenanceRecord)
            .where(
                MaintenanceRecord.storage_unit_id.in_(unit_ids),
                MaintenanceRecord.created_at <= date_to,
                (MaintenanceRecord.completed_at.is_(None)) | (MaintenanceRecord.completed_at >= date_from),
            )
            .order_by(MaintenanceRecord.created_at.desc())
        ).all()
    )
    iot_links = list(db.scalars(select(IotDevice).where(IotDevice.device_id.in_(device_ids))).all()) if device_ids else []
    gateways = {
        item.id: item
        for item in db.scalars(
            select(IotGateway).where(IotGateway.id.in_({link.gateway_id for link in iot_links if link.gateway_id}))
        ).all()
    } if iot_links else {}
    gateway_by_device = {
        link.device_id: gateways.get(link.gateway_id)
        for link in iot_links
        if link.gateway_id is not None
    }
    now = utc_now()
    offline = sum(
        1
        for device in devices
        if device.last_seen_at is None
        or (
            device.expected_reading_interval_minutes
            and (now - _aware(device.last_seen_at)).total_seconds() / 60
            > device.expected_reading_interval_minutes * 6
        )
    )
    calibration_count = int(
        db.scalar(
            select(func.count(SensorCalibration.id)).where(
                SensorCalibration.device_id.in_(device_ids) if device_ids else SensorCalibration.id == -1,
                SensorCalibration.is_active.is_(True),
            )
        )
        or 0
    )
    evidence_count = int(
        db.scalar(
            select(func.count(StoredFile.id)).where(
                StoredFile.storage_unit_id.in_(unit_ids),
                StoredFile.deleted_at.is_(None),
            )
        )
        or 0
    )
    return {
        "devices": devices,
        "readings": readings,
        "latest": latest,
        "alerts": alerts,
        "incidents": incidents,
        "maintenance": maintenance,
        "gateway_by_device": gateway_by_device,
        "operational_devices": len(devices) - offline,
        "offline_devices": offline,
        "critical_alerts": sum(1 for item in alerts if item.severity == "critical"),
        "calibration_count": calibration_count,
        "evidence_count": evidence_count,
        "next_reviews": sum(1 for item in maintenance if item.next_maintenance_at and item.next_maintenance_at > now),
    }


def _cover(title, subtitle, report_number, units, date_from, date_to, responsible):
    styles = _styles()
    companies = sorted({unit.company_id for unit in units})
    return [
        Spacer(1, 4 * mm),
        _brand(),
        Spacer(1, 18 * mm),
        Paragraph("AGROESCUDO CONTROL CENTER", styles["eyebrow"]),
        Paragraph(title, styles["cover"]),
        Spacer(1, 4 * mm),
        Paragraph(subtitle, styles["subtitle"]),
        Spacer(1, 14 * mm),
        _table(
            [
                ["Numero de reporte", report_number],
                ["Alcance", units[0].name if len(units) == 1 else f"{len(units)} unidades monitoreadas"],
                ["Empresas incluidas", str(len(companies))],
                ["Periodo", f"{_date(date_from)} - {_date(date_to)}"],
                ["Responsable", responsible],
                ["Version", "P1.0"],
                ["Emitido", _date(utc_now())],
            ],
            [52 * mm, 108 * mm],
        ),
    ]


def _build_pdf(story, report_number: str, title: str) -> bytes:
    output = BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=21 * mm,
        bottomMargin=18 * mm,
        title=title,
        author="AgroEscudo",
        subject=report_number,
    )

    def decorate(canvas, document):
        canvas.saveState()
        width, height = A4
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, height - 13 * mm, width - 18 * mm, height - 13 * mm)
        canvas.line(18 * mm, 12 * mm, width - 18 * mm, 12 * mm)
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 7.5 * mm, report_number)
        canvas.drawRightString(width - 18 * mm, 7.5 * mm, f"Pagina {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)
    return output.getvalue()


def _styles():
    sample = getSampleStyleSheet()
    return {
        "cover": ParagraphStyle("p1_cover", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=28, leading=32, textColor=GREEN),
        "subtitle": ParagraphStyle("p1_subtitle", parent=sample["BodyText"], fontSize=12, leading=17, textColor=TEXT),
        "eyebrow": ParagraphStyle("p1_eyebrow", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=AMBER),
        "heading": ParagraphStyle("p1_heading", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=GREEN),
        "body": ParagraphStyle("p1_body", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.5, leading=14, textColor=TEXT),
        "cell": ParagraphStyle("p1_cell", parent=sample["BodyText"], fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=TEXT),
        "head": ParagraphStyle("p1_head", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=7.2, leading=9, textColor=GREEN),
        "notice": ParagraphStyle("p1_notice", parent=sample["BodyText"], fontName="Helvetica", fontSize=8, leading=11, textColor=MUTED, backColor=SOFT, borderColor=LINE, borderWidth=0.5, borderPadding=8),
        "kpi": ParagraphStyle("p1_kpi", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=13, leading=15, textColor=GREEN, alignment=TA_CENTER),
    }


def _brand():
    if LOGO_PATH.exists():
        image = Image(str(LOGO_PATH), width=58 * mm, height=17 * mm)
        image.hAlign = "LEFT"
        return image
    return Paragraph("AgroEscudo", _styles()["cover"])


def _title(text: str):
    return Paragraph(text, _styles()["heading"])


def _table(rows, widths, *, header=False):
    styles = _styles()
    rendered = []
    for index, row in enumerate(rows):
        style = styles["head"] if header and index == 0 else styles["cell"]
        rendered.append([Paragraph(str(value), style) for value in row])
    table = Table(rendered, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                ("BACKGROUND", (0, 0), (-1, 0), SOFT),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def _kpi_table(items):
    rows = []
    for offset in range(0, len(items), 2):
        pair = items[offset : offset + 2]
        labels = [Paragraph(label, _styles()["head"]) for label, _ in pair]
        values = [Paragraph(value, _styles()["kpi"]) for _, value in pair]
        while len(labels) < 2:
            labels.append(Paragraph("", _styles()["head"]))
            values.append(Paragraph("", _styles()["kpi"]))
        rows.extend([labels, values])
    table = Table(rows, colWidths=[80 * mm, 80 * mm])
    table.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.5, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE), ("BACKGROUND", (0, 0), (-1, -1), SOFT), ("ALIGN", (0, 0), (-1, -1), "CENTER"), ("PADDING", (0, 0), (-1, -1), 8)]))
    return table


def _executive_summary(context):
    if context["critical_alerts"]:
        return (
            "Durante el periodo se registraron condiciones criticas que requieren seguimiento operativo, "
            "inspeccion fisica y cierre documentado de acciones."
        )
    if not context["readings"]:
        return "No existe evidencia suficiente para emitir una conclusion operativa del periodo."
    return "Las lecturas disponibles no muestran alertas criticas en el periodo. Se recomienda mantener monitoreo y revision rutinaria."


def _variable_evolution(readings):
    variables = [
        ("Temperatura de grano", "grain_temperature", "C"),
        ("Humedad ambiente", "ambient_humidity", "%"),
        ("Nivel estimado", "level_percent", "%"),
        ("Humedad de suelo", "soil_moisture_percent", "%"),
    ]
    rows = [["Variable", "Inicio", "Ultimo", "Minimo", "Maximo", "Promedio"]]
    for label, attribute, unit in variables:
        values = [float(value) for row in readings if (value := getattr(row, attribute)) is not None]
        if not values:
            continue
        rows.append([label, f"{values[0]:.1f} {unit}", f"{values[-1]:.1f} {unit}", f"{min(values):.1f}", f"{max(values):.1f}", f"{mean(values):.1f}"])
    if len(rows) == 1:
        rows.append(["Sin datos comparables", "-", "-", "-", "-", "-"])
    return _table(rows, [42 * mm, 24 * mm, 24 * mm, 22 * mm, 22 * mm, 26 * mm], header=True)


def _alerts_table(alerts, *, technical):
    if technical:
        rows = [["Fecha", "Nodo", "Metrica", "Valor", "Umbral", "Nivel", "Estado"]]
        for item in alerts[:20]:
            rows.append([
                _datetime(item.created_at),
                str(item.device_id),
                item.metric or item.alert_type,
                _number(item.observed_value),
                _number(item.threshold_value),
                item.severity.upper(),
                "Activa" if item.is_active else "Resuelta",
            ])
        widths = [24, 16, 35, 20, 20, 20, 22]
    else:
        rows = [["Fecha", "Evento", "Nivel", "Estado", "Accion sugerida"]]
        for item in alerts[:15]:
            rows.append([
                _datetime(item.created_at),
                item.title,
                item.severity.upper(),
                "Activa" if item.is_active else "Resuelta",
                _alert_recommendation(item),
            ])
        widths = [27, 48, 20, 22, 43]
    if len(rows) == 1:
        rows.append(["Sin eventos registrados"] + ["-"] * (len(rows[0]) - 1))
    return _table(rows, [value * mm for value in widths], header=True)


def _maintenance_table(records, *, technical):
    if technical:
        rows = [["Fecha", "Nodo", "Tipo", "Estado", "Diagnostico", "Accion"]]
        widths = [25, 18, 28, 22, 34, 39]
        for item in records[:18]:
            rows.append([_datetime(item.created_at), str(item.device_id), item.maintenance_type, item.status, item.diagnosis or "No registrado", item.action_taken or "Pendiente"])
    else:
        rows = [["Fecha", "Intervencion", "Estado", "Accion documentada"]]
        widths = [28, 38, 24, 76]
        for item in records[:15]:
            rows.append([_datetime(item.created_at), item.maintenance_type.replace("_", " ").title(), item.status, item.action_taken or "Pendiente de cierre"])
    if len(rows) == 1:
        rows.append(["Sin mantenimiento registrado"] + ["-"] * (len(rows[0]) - 1))
    return _table(rows, [value * mm for value in widths], header=True)


def _device_table(devices, latest, gateway_by_device):
    rows = [["Nodo", "Tipo", "Firmware", "Bateria", "Senal", "Gateway", "Estado"]]
    for device in devices:
        reading = latest.get(device.id)
        gateway = gateway_by_device.get(device.id)
        rows.append([
            device.external_id,
            _device_type_label(device.device_type),
            device.model_version or "No registrada",
            f"{reading.battery_voltage:.2f} V" if reading and reading.battery_voltage is not None else "Sin dato",
            f"{reading.signal_quality} dBm" if reading and reading.signal_quality is not None else "Sin dato",
            gateway.gateway_id if gateway else "No asignado",
            gateway_effective_status(gateway) if gateway else _device_status_label(device.operational_status),
        ])
    if len(rows) == 1:
        rows.append(["Sin dispositivos", "-", "-", "-", "-", "-", "-"])
    return _table(rows, [26 * mm, 28 * mm, 24 * mm, 21 * mm, 21 * mm, 25 * mm, 21 * mm], header=True)


def _technical_quality_table(metrics, context):
    rows = [
        ["Indicador", "Valor", "Metodo / alcance"],
        ["Lecturas recibidas", _value(metrics.data_availability.get("received_readings")), "Marcas de tiempo del periodo"],
        ["Cobertura", _percent(metrics.data_availability.get("coverage_percent")), "Cadencia configurada; si falta, no calculable"],
        ["Lecturas rechazadas", _value(metrics.quality.get("rejected_readings")), "Eventos de ingestion"],
        ["Duplicados", _value(metrics.quality.get("duplicates")), "Idempotencia IoT"],
        ["Fallas de sensor", _value(metrics.quality.get("sensor_faults")), "sensor_status informado"],
        ["Metricas sin calibrar", _value(metrics.quality.get("uncalibrated_metrics")), "Calibracion versionada"],
        ["Calibraciones activas", str(context["calibration_count"]), "Por dispositivo y variable"],
    ]
    return _table(rows, [55 * mm, 35 * mm, 76 * mm], header=True)


def _recommendation_paragraphs(context):
    recommendations = []
    if context["critical_alerts"]:
        recommendations.append("Priorizar intervencion operativa y documentar el cierre de cada alerta critica.")
    if any(item.metric == "ambient_humidity" for item in context["alerts"]):
        recommendations.append("Revisar ventilacion, aireacion y posibles puntos de condensacion.")
    if any(item.metric == "grain_temperature" for item in context["alerts"]):
        recommendations.append("Inspeccionar fisicamente el punto monitoreado y verificar acumulacion termica.")
    if not recommendations:
        recommendations.append("Mantener la frecuencia de monitoreo y la revision preventiva definida para el piloto.")
    return [Paragraph(f"- {text}", _styles()["body"]) for text in recommendations]


def _technical_recommendations(context):
    recommendations = []
    if context["offline_devices"]:
        recommendations.append("Revisar alimentacion, conectividad y cola local de los nodos fuera de linea.")
    if context["calibration_count"] < len(context["devices"]):
        recommendations.append("Verificar que cada variable critica tenga una calibracion vigente y trazable.")
    if any(item.battery_voltage is not None and item.battery_voltage < 3.5 for item in context["latest"].values()):
        recommendations.append("Programar revision de bateria en los nodos con tension inferior a 3.5 V.")
    if not recommendations:
        recommendations.append("Conservar el plan de inspeccion y registrar cualquier intervencion futura con evidencia.")
    return [Paragraph(f"- {text}", _styles()["body"]) for text in recommendations]


def _alert_recommendation(alert):
    if alert.metric == "grain_temperature":
        return "Inspeccionar el punto y verificar acumulacion termica."
    if alert.metric == "ambient_humidity":
        return "Revisar ventilacion y condensacion."
    if alert.metric == "battery_voltage":
        return "Programar revision tecnica del nodo."
    return "Revisar el evento y registrar la accion tomada."


def _report_number(prefix, units, date_to):
    scope = units[0].id if len(units) == 1 else "MULTI"
    return f"AE-{prefix}-{date_to:%Y%m%d}-{scope}"


def _device_type_label(value):
    if value == "field_sensor":
        return "CampoSensor"
    return "SiloSensor"


def _device_status_label(value):
    return {
        "operational": "Operativo",
        "degraded": "Degradado",
        "calibration_pending": "Calibracion pendiente",
        "offline": "Fuera de linea",
    }.get((value or "").lower(), (value or "Desconocido").title())


def _single_company(units):
    return len({unit.company_id for unit in units}) == 1


def _number(value):
    return f"{value:.2f}" if value is not None else "Sin dato"


def _value(value):
    return str(value) if value is not None else "No calculable"


def _percent(value):
    return f"{value:.1f}%" if value is not None else "No calculable"


def _minutes(value):
    return f"{value:.1f} min" if value is not None else "No calculable"


def _date(value):
    return _aware(value).astimezone(timezone.utc).strftime("%d/%m/%Y")


def _datetime(value):
    return _aware(value).astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")


def _aware(value):
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
