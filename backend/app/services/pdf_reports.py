from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from textwrap import shorten
from xml.sax.saxutils import escape

from reportlab.graphics.shapes import Circle, Drawing, Line, Path as DrawingPath, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    CondPageBreak,
    Image,
    KeepTogether,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Alert, Device, IotGateway, NotificationDelivery, OperationalLog, SensorReading, StorageUnit, ThresholdConfig
from app.schemas import WeeklyReportOut
from app.services.chart_context import build_device_chart_context

GREEN_950 = colors.HexColor("#022C22")
GREEN_900 = colors.HexColor("#064E3B")
GREEN_700 = colors.HexColor("#047857")
GREEN_100 = colors.HexColor("#DDF4EA")
AMBER = colors.HexColor("#D99A00")
AMBER_100 = colors.HexColor("#FFF4D6")
TEXT = colors.HexColor("#26343D")
MUTED = colors.HexColor("#64748B")
LINE = colors.HexColor("#D9E5E0")
PAGE = colors.HexColor("#F7FAF8")
RED = colors.HexColor("#B42318")
RED_100 = colors.HexColor("#FEE4E2")
LOGO_PATH = Path(__file__).resolve().parents[1] / "assets" / "brand" / "logo-horizontal-white.png"


def build_weekly_pdf(
    db: Session,
    storage_unit: StorageUnit,
    report: WeeklyReportOut,
    device_id: int | None = None,
) -> bytes:
    return build_report_pdf(db, storage_unit, report, device_id=device_id, document_type="full")


def build_report_pdf(
    db: Session,
    storage_unit: StorageUnit,
    report: WeeklyReportOut,
    *,
    device_id: int | None = None,
    document_type: str = "full",
) -> bytes:
    if document_type not in {"full", "logbook"}:
        raise ValueError("Tipo de documento no soportado.")

    device = db.get(Device, device_id) if device_id is not None else None
    device_stmt = select(Device).where(Device.storage_unit_id == storage_unit.id)
    if device_id is not None:
        device_stmt = device_stmt.where(Device.id == device_id)
    devices = list(db.scalars(device_stmt.order_by(Device.name)).all())
    device_names = {item.id: item.external_id for item in devices}
    readings = _readings(db, storage_unit.id, report, device_id)
    alerts = _alerts_query(db, storage_unit.id, report, device_id)
    logs = _logs_query(db, storage_unit.id, report, device_id)
    chart_contexts = [
        build_device_chart_context(
            db,
            device_id=item.id,
            from_=report.date_from,
            to=report.date_to,
        )
        for item in devices
    ]
    chart_events = [event for context in chart_contexts for event in context.events]
    chart_actions = [action for context in chart_contexts for action in context.actions]
    active_alerts = list(db.scalars(select(Alert).where(
        Alert.storage_unit_id == storage_unit.id,
        Alert.is_active.is_(True),
        Alert.device_id == device_id if device_id is not None else Alert.storage_unit_id == storage_unit.id,
    ).order_by(Alert.created_at.desc())).all())
    deliveries = _notification_deliveries(db, alerts)
    thresholds = _configured_thresholds(db, storage_unit, device_id)
    gateway = db.scalar(
        select(IotGateway)
        .where(or_(IotGateway.storage_unit_id == storage_unit.id, IotGateway.site_id == storage_unit.site_id))
        .order_by(IotGateway.last_seen_at.desc())
    )

    output = BytesIO()
    document_title = "Bitácora operativa" if document_type == "logbook" else "Reporte técnico de monitoreo postcosecha"
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title=f"AgroEscudo - {document_title} - {storage_unit.name}",
        author="AgroEscudo",
        subject=f"Evidencia {report.period_label.lower()} de monitoreo IoT y trazabilidad operativa",
    )
    styles = _styles()
    if document_type == "logbook":
        pages = [
            _simple_logbook_entry_page(styles, report, readings, active_alerts),
            _simple_logbook_charts_page(styles, readings, thresholds, device, chart_events, chart_actions),
            _simple_logbook_history_page(styles, report, logs, active_alerts, device_names),
        ]
    else:
        pages = [
            _state_page(styles, report, storage_unit, device, readings, alerts, active_alerts, gateway),
            _summary_page(styles, report, readings, alerts),
            _single_metric_page(styles, "03", "Temperatura del grano", "Historial térmico con bandas de riesgo", readings, "grain_temperature", "°C", GREEN_700, thresholds, chart_events, chart_actions, device),
            _single_metric_page(styles, "04", "Humedad ambiente", "Evolución de humedad durante el periodo", readings, "ambient_humidity", "%", AMBER, thresholds, chart_events, chart_actions, device),
            _single_metric_page(styles, "05", "Nivel estimado", "Tendencia del nivel sin convertir altura en volumen", readings, "level_percent", "%", colors.HexColor("#0F766E"), thresholds, chart_events, chart_actions, device),
            _risk_response_page(styles, alerts, logs, deliveries, device_names),
            _operational_logbook_page(styles, logs, device_names),
            _system_health_page(styles, report, device, gateway, readings, logs),
            _operational_impact_page(styles, report, alerts, logs, storage_unit),
            _next_steps_page(styles, alerts, report),
        ]

    story = []
    for index, page in enumerate(pages):
        if index:
            story.append(PageBreak())
        story.extend(page)

    doc.build(
        story,
        onFirstPage=lambda canvas, current_doc: _decorate_page(canvas, current_doc, "PÁG. 1", cover=False),
        onLaterPages=lambda canvas, current_doc: _decorate_page(
            canvas,
            current_doc,
            f"PÁG. {current_doc.page}",
            cover=False,
        ),
    )
    return output.getvalue()


def pdf_filename(
    storage_unit_name: str,
    generated_date,
    *,
    period: str = "weekly",
    document_type: str = "full",
) -> str:
    slug = "".join(char.lower() if char.isalnum() else "-" for char in storage_unit_name)
    slug = "-".join(part for part in slug.split("-") if part)[:60] or "unidad"
    kind = "bitacora" if document_type == "logbook" else "reporte"
    return f"agroescudo-{kind}-{period}-{slug}-{generated_date:%Y-%m-%d}.pdf"


def _readings(db, storage_unit_id, report, device_id):
    statement = select(SensorReading).where(
        SensorReading.storage_unit_id == storage_unit_id,
        SensorReading.timestamp >= report.date_from,
        SensorReading.timestamp <= report.date_to,
    )
    if device_id is not None:
        statement = statement.where(SensorReading.device_id == device_id)
    return list(db.scalars(statement.order_by(SensorReading.timestamp.asc())).all())


def _alerts_query(db, storage_unit_id, report, device_id):
    statement = select(Alert).where(
        Alert.storage_unit_id == storage_unit_id,
        Alert.created_at >= report.date_from,
        Alert.created_at <= report.date_to,
    )
    if device_id is not None:
        statement = statement.where(Alert.device_id == device_id)
    return list(db.scalars(statement.order_by(Alert.created_at.desc())).all())


def _logs_query(db, storage_unit_id, report, device_id):
    statement = select(OperationalLog).where(
        OperationalLog.storage_unit_id == storage_unit_id,
        OperationalLog.timestamp >= report.date_from,
        OperationalLog.timestamp <= report.date_to,
    )
    if device_id is not None:
        statement = statement.where(OperationalLog.device_id == device_id)
    return list(db.scalars(statement.order_by(OperationalLog.timestamp.desc())).all())


def _notification_deliveries(db: Session, alerts: list[Alert]) -> list[NotificationDelivery]:
    alert_ids = [item.id for item in alerts]
    if not alert_ids:
        return []
    return list(
        db.scalars(
            select(NotificationDelivery)
            .where(NotificationDelivery.alert_id.in_(alert_ids))
            .order_by(NotificationDelivery.created_at.asc())
        ).all()
    )


def _configured_thresholds(db: Session, storage_unit: StorageUnit, device_id: int | None) -> dict[str, float]:
    configs = list(
        db.scalars(
            select(ThresholdConfig).where(
                ThresholdConfig.company_id == storage_unit.company_id,
                ThresholdConfig.is_active.is_(True),
            )
        ).all()
    )
    applicable = [
        item
        for item in configs
        if item.storage_unit_id in {None, storage_unit.id} and item.device_id in {None, device_id}
    ]
    applicable.sort(key=lambda item: (item.device_id == device_id, item.storage_unit_id == storage_unit.id))
    return {item.metric: item.value for item in applicable}


def _page_heading(styles, number: str, title: str, subtitle: str):
    return [
        _brand_logo(styles, width=38 * mm),
        Spacer(1, 6 * mm),
        Paragraph(f"{number} · {title.upper()}", styles["eyebrow"]),
        Paragraph(title, styles["section"]),
        Paragraph(subtitle, styles["body"]),
        Spacer(1, 5 * mm),
    ]


def _state_page(styles, report, storage_unit, device, readings, period_alerts, active_alerts, gateway):
    latest = readings[-1] if readings else None
    current_status = _status(active_alerts) if latest else "Sin datos"
    period_risk = _status(period_alerts) if readings else "Sin datos"
    recommendations = _recommendations(active_alerts or period_alerts, report)
    metrics = [
        ("Temperatura actual", _reading_number(latest, "grain_temperature", " °C"), "grano"),
        ("Humedad actual", _reading_number(latest, "ambient_humidity", "%"), "ambiente"),
        ("Nivel actual", _reading_number(latest, "level_percent", "%"), "altura ocupada"),
    ]
    gateway_online = bool(gateway and gateway.last_seen_at and _minutes_since(gateway.last_seen_at) <= 120)
    sensor_online = bool(device and device.last_seen_at and _minutes_since(device.last_seen_at) <= 120)
    elements = _page_heading(styles, "01", storage_unit.name, f"{report.site_name} · {_date(report.date_from)} a {_date(report.date_to)}")
    elements.extend([
        _dual_status_panel(styles, current_status, period_risk),
        Spacer(1, 6 * mm),
        Paragraph(_current_state_copy(current_status, period_risk), styles["body"]),
        Spacer(1, 7 * mm),
        _three_metric_grid(styles, metrics),
        Spacer(1, 8 * mm),
        _card(styles, "ACCIÓN RECOMENDADA", recommendations[0], accent=AMBER),
        Spacer(1, 5 * mm),
        _table(styles, [
            ["Última lectura", _datetime(latest.timestamp) if latest else "Sin dato", "Nodo", device.external_id if device else "Consolidado"],
            ["Sensor", "Online" if sensor_online else "Offline", "Gateway", "Online" if gateway_online else "Sin conexión reciente"],
            ["Batería", _reading_number(latest, "battery_voltage", " V", 2), "Periodo", report.period_label],
        ], [33 * mm, 49 * mm, 27 * mm, 57 * mm], header=False, large=True),
    ])
    return elements


def _summary_page(styles, report, readings, alerts):
    latest = readings[-1] if readings else None
    pending = sum(1 for alert in alerts if alert.is_active)
    metrics = [
        ("Lecturas", str(report.reading_count), "recibidas"),
        ("Temp. máxima", _number(report.max_grain_temperature, " °C"), "del periodo"),
        ("Alertas", str(report.alerts_generated), "eventos"),
        ("Pendientes", str(pending), "requieren cierre"),
        ("Acciones", str(len(report.operational_actions)), "registradas"),
        ("Fuera de rango", f"{report.approximate_hours_out_of_range:g} h", "observado"),
    ]
    next_steps = _recommendations(alerts, report)[:3]
    while len(next_steps) < 3:
        next_steps.append("Mantener monitoreo y documentar cualquier cambio operativo relevante.")
    elements = _page_heading(styles, "02", "Resumen ejecutivo", "Lectura rápida del periodo para priorizar decisiones operativas")
    elements.extend([
        _card(styles, "Conclusión ejecutiva", _executive_summary(report, _status(alerts)), accent=AMBER),
        Spacer(1, 4 * mm),
        _metric_grid(styles, metrics),
        Spacer(1, 7 * mm),
        _card(styles, "Próximos pasos", "<br/>".join(f"{index}) {text}" for index, text in enumerate(next_steps, 1)), accent=GREEN_700),
        Spacer(1, 4 * mm),
        _card(styles, "Última evidencia recibida", f"{_datetime(latest.timestamp)}. {_latest_text(latest)}" if latest else "No se recibieron lecturas en el periodo.", accent=GREEN_700 if latest else RED),
    ])
    return elements


def _single_metric_page(styles, number, title, subtitle, readings, attribute, unit, color, thresholds, events, actions, device):
    points = [(item.timestamp, getattr(item, attribute)) for item in readings if getattr(item, attribute) is not None]
    elements = _page_heading(styles, number, title, subtitle)
    if len(points) < 2:
        message = "Nivel no disponible para esta unidad." if attribute == "level_percent" else "No existen lecturas suficientes para construir esta gráfica."
        elements.extend([Spacer(1, 20 * mm), _card(styles, "Sin datos suficientes", message, accent=AMBER)])
        return elements
    values = [float(value) for _, value in points]
    threshold_set = _threshold_set(attribute, thresholds)
    chart = _compact_metric_chart(points, title, unit, color, threshold_set, events, actions, device.expected_reading_interval_minutes if device else None) if attribute == "level_percent" else _premium_metric_chart(points, title, unit, color, threshold_set, events, actions, device.expected_reading_interval_minutes if device else None)
    if attribute == "level_percent":
        elements.extend([_pdf_level_visual(values[-1], values[0], threshold_set), Spacer(1, 5 * mm)])
    elements.extend([
        chart,
        Spacer(1, 8 * mm),
        _three_metric_grid(styles, [
            ("Actual", f"{values[-1]:.1f}{unit}", "última lectura"),
            ("Máximo", f"{max(values):.1f}{unit}", _datetime(points[values.index(max(values))][0])),
            ("Variación", f"{values[-1] - values[0]:+.1f}{unit}", "inicio vs. cierre"),
        ]),
        Spacer(1, 7 * mm),
        _card(
            styles,
            "Lectura operativa",
            _metric_interpretation(attribute, values, threshold_set),
            accent=AMBER if threshold_set else GREEN_700,
        ),
    ])
    return elements


def _risk_response_page(styles, alerts, logs, deliveries, device_names):
    elements = _page_heading(styles, "06", "Riesgos y respuesta del operador", "Eventos, acciones y resultados en una sola lectura")
    if not alerts:
        elements.append(_card(styles, "Sin eventos", "No se registraron alertas durante el periodo seleccionado.", accent=GREEN_700))
        return elements
    rows = [["Evento", "Fecha", "Máximo", "Duración", "Estado", "Acción"]]
    for alert in alerts[:8]:
        action = next((item for item in logs if item.alert_id == alert.id), None)
        rows.append([
            alert.title,
            _datetime(alert.created_at),
            _number(alert.observed_value),
            _alert_duration(alert),
            "Activa" if alert.is_active else "Resuelta",
            action.action_taken if action else "Sin acción registrada",
        ])
    elements.extend([
        _table(styles, rows, [36 * mm, 26 * mm, 18 * mm, 20 * mm, 20 * mm, 46 * mm], header=True),
        Spacer(1, 8 * mm),
        Paragraph("Línea de respuesta del evento prioritario", styles["subsection"]),
        _response_timeline(styles, alerts[0], logs, deliveries),
    ])
    return elements


def _operational_logbook_page(styles, logs, device_names):
    elements = _page_heading(styles, "07", "Bitácora operativa", "Registro claro de fecha, acción, responsable y resultado")
    if not logs:
        elements.append(_card(styles, "Sin acciones registradas", "No existe evidencia operativa durante el periodo seleccionado.", accent=AMBER))
        return elements
    rows = [["Fecha", "Actividad", "Responsable", "Resultado"]]
    for log in logs[:14]:
        result = shorten(log.notes or "Sin resultado documentado.", width=110, placeholder="…")
        rows.append([_datetime(log.timestamp), log.action_taken, log.operator_name, result])
    elements.extend([
        _table(styles, rows, [27 * mm, 48 * mm, 35 * mm, 56 * mm], header=True),
        Spacer(1, 7 * mm),
        _card(styles, "Regla de evidencia", "Cada acción importante debe conservar fecha, responsable, resultado y evidencia cuando exista.", accent=GREEN_700),
    ])
    return elements


def _system_health_page(styles, report, device, gateway, readings, logs):
    latest = readings[-1] if readings else None
    cadence = device.expected_reading_interval_minutes if device else None
    expected = int((report.date_to - report.date_from).total_seconds() / (cadence * 60)) + 1 if cadence else None
    integrity = min(100.0, len(readings) / expected * 100) if expected else None
    gaps = _gap_count(readings, cadence)
    node_online = bool(device and device.last_seen_at and _minutes_since(device.last_seen_at) <= 120)
    gateway_online = bool(gateway and gateway.last_seen_at and _minutes_since(gateway.last_seen_at) <= 120)
    elements = _page_heading(styles, "08", "Salud del sistema y evidencia", "Confiabilidad de la captura, conectividad y respaldo de campo")
    elements.extend([
        _three_metric_grid(styles, [
            ("Nodo", "Online" if node_online else "Offline", device.external_id if device else "Sin nodo"),
            ("Gateway", "Online" if gateway_online else "Sin dato", gateway.gateway_id if gateway else "No registrado"),
            ("Batería", _reading_number(latest, "battery_voltage", " V", 2), "última lectura"),
        ]),
        Spacer(1, 7 * mm),
        _table(styles, [
            ["Integridad de datos", f"{integrity:.1f}%" if integrity is not None else "No calculable sin cadencia"],
            ["Lecturas recibidas", str(len(readings))],
            ["Lecturas esperadas", str(expected) if expected is not None else "Sin dato"],
            ["Ventanas sin información", str(gaps) if cadence else "No calculable"],
            ["Última transmisión", _datetime(latest.timestamp) if latest else "Sin dato"],
            ["Mantenimientos registrados", str(sum(log.category == "maintenance" for log in logs))],
        ], [62 * mm, 104 * mm], header=False, large=True),
        Spacer(1, 8 * mm),
        _card(styles, "Evidencia de campo", "Sin evidencia visual registrada." if not logs else "La bitácora conserva intervenciones. Las fotografías aparecen cuando están asociadas a un caso de servicio.", accent=AMBER),
    ])
    return elements


def _operational_impact_page(styles, report, alerts, logs, storage_unit):
    response_minutes = sorted(
        (alert.acknowledged_at - alert.created_at).total_seconds() / 60
        for alert in alerts
        if alert.acknowledged_at is not None
    )
    median = response_minutes[len(response_minutes) // 2] if response_minutes else None
    elements = _page_heading(styles, "09", "Impacto operacional", "Resultados medibles sin atribuir ahorro o merma no demostrados")
    elements.extend([
        _metric_grid(styles, [
            ("Eventos", str(len(alerts)), "detectados"),
            ("Intervenciones", str(len(logs)), "registradas"),
            ("Normalizados", str(sum(not alert.is_active for alert in alerts)), "eventos"),
            ("Respuesta mediana", f"{median:.0f} min" if median is not None else "Sin dato", "alerta a reconocimiento"),
            ("Exposición", f"{report.approximate_hours_out_of_range:g} h", "fuera de rango"),
            ("Inventario", f"{storage_unit.capacity_tons:g} t" if storage_unit.capacity_tons else "Sin dato", "capacidad monitoreada"),
        ]),
        Spacer(1, 9 * mm),
        Paragraph("Valor protegido", styles["subsection"]),
        _table(styles, [
            ["Inventario monitoreado", f"{storage_unit.capacity_tons:g} t" if storage_unit.capacity_tons else "Dato pendiente del cliente"],
            ["Valor económico", "Dato pendiente del cliente"],
            ["Merma evitada", "No calculada"],
            ["Ahorro demostrado", "Pendiente de validación"],
        ], [55 * mm, 111 * mm], header=False, large=True),
        Spacer(1, 7 * mm),
        _card(styles, "Criterio", "No se atribuye ahorro, causalidad o merma evitada sin metodología y evidencia aprobadas.", accent=AMBER),
    ])
    return elements


def _next_steps_page(styles, alerts, report):
    steps = _recommendations(alerts, report)[:5]
    while len(steps) < 3:
        steps.append("Verificar la evolución del nodo durante la siguiente ventana operativa.")
    elements = _page_heading(styles, "10", "Próximos pasos", "Plan corto, accionable y verificable")
    for index, step in enumerate(steps, 1):
        elements.append(_card(styles, f"{index:02d} · Acción", step, accent=GREEN_700 if index > 1 else AMBER))
    elements.extend([
        Spacer(1, 7 * mm),
        _signature_block(styles),
        Spacer(1, 7 * mm),
        _card(styles, "CIERRE", "Ver. Entender. Alertar. Actuar. Verificar. Registrar. Demostrar.", accent=AMBER),
    ])
    return elements


def _simple_logbook_entry_page(styles, report, readings, active_alerts):
    latest = readings[-1] if readings else None
    state = _status(active_alerts) if latest else "Sin datos"
    elements = _page_heading(styles, "BITÁCORA SIMPLE / 01", "Bitácora simple del silo", "Simple, rápida y bonita. Solo registra lo importante.")
    elements.extend([
        _card(
            styles,
            "CÓMO USARLA",
            "1. Qué pasó  ·  2. Qué hiciste  ·  3. Cómo quedó  ·  4. Foto opcional  ·  5. Guardar",
            accent=AMBER,
        ),
        Spacer(1, 5 * mm),
        _three_metric_grid(styles, [
            ("Hoy", _simple_state(state), "estado del silo"),
            ("Última lectura", _datetime(latest.timestamp) if latest else "Sin dato", "automática"),
            ("Alertas", str(len(active_alerts)), "activas"),
        ]),
        Spacer(1, 7 * mm),
    ])
    for index, (title, copy) in enumerate([
        ("1 · ¿QUÉ PASÓ?", "Alerta / revisión / mantenimiento / rutina / otro"),
        ("2 · ¿QUÉ HICISTE?", "Inspeccioné / aireé / ventilé / moví grano / tomé muestra"),
        ("3 · ¿CÓMO QUEDÓ?", "Mejoró / sigue igual / sigue con problema / resuelto"),
        ("4 · FOTO OPCIONAL", "Añade evidencia cuando aporte contexto a la acción"),
    ]):
        elements.append(_card(styles, title, copy, accent=GREEN_700 if index < 3 else AMBER))
    return elements


def _simple_logbook_charts_page(styles, readings, thresholds, device, events, actions):
    elements = _page_heading(styles, "BITÁCORA SIMPLE / 02", "Resumen visual", "Tres gráficas fáciles de leer para revisar el periodo")
    for attribute, label, unit, color in [
        ("grain_temperature", "Temperatura del grano", "°C", GREEN_700),
        ("ambient_humidity", "Humedad ambiente", "%", colors.HexColor("#2563EB")),
        ("level_percent", "Nivel estimado", "%", colors.HexColor("#0F766E")),
    ]:
        points = [(item.timestamp, getattr(item, attribute)) for item in readings if getattr(item, attribute) is not None]
        if len(points) >= 2:
            elements.extend([_compact_metric_chart(points, label, unit, color, _threshold_set(attribute, thresholds), events, actions, device.expected_reading_interval_minutes if device else None), Spacer(1, 4 * mm)])
        else:
            elements.extend([_card(styles, label, "Sin datos suficientes para este periodo.", accent=AMBER), Spacer(1, 2 * mm)])
    return elements


def _simple_logbook_history_page(styles, report, logs, active_alerts, device_names):
    elements = _page_heading(styles, "BITÁCORA SIMPLE / 03", "Lo que hicimos", "Resumen rápido para revisar la semana o el periodo seleccionado")
    elements.extend([
        _three_metric_grid(styles, [
            ("Alertas", str(report.alerts_generated), "del periodo"),
            ("Acciones", str(len(logs)), "registradas"),
            ("Pendientes", str(len(active_alerts)), "requieren revisión"),
        ]),
        Spacer(1, 7 * mm),
    ])
    if logs:
        rows = [["Fecha", "Qué hicimos", "Responsable", "Resultado"]]
        rows.extend([[_datetime(item.timestamp), item.action_taken, item.operator_name, shorten(item.notes or "Sin resultado", width=80, placeholder="…")] for item in logs[:10]])
        elements.append(_table(styles, rows, [28 * mm, 55 * mm, 35 * mm, 48 * mm], header=True))
    else:
        elements.append(_card(styles, "Sin acciones", "No se registraron intervenciones en este periodo.", accent=AMBER))
    elements.extend([Spacer(1, 8 * mm), _card(styles, "PENDIENTE", "Volver a revisar las condiciones y documentar el resultado cuando exista una alerta activa.", accent=AMBER)])
    return elements


def _dual_status_panel(styles, current_status: str, period_risk: str):
    current_color, current_bg = _status_colors(current_status)
    risk_color, risk_bg = _status_colors(period_risk)
    table = Table([
        [Paragraph("ESTADO ACTUAL", styles["metric_label"]), Paragraph("MÁXIMO RIESGO DEL PERIODO", styles["metric_label"])],
        [Paragraph(current_status.upper(), styles["metric_value"]), Paragraph(period_risk.upper(), styles["metric_value"])],
    ], colWidths=[82 * mm, 82 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), current_bg),
        ("BACKGROUND", (1, 0), (1, -1), risk_bg),
        ("TEXTCOLOR", (0, 1), (0, 1), current_color),
        ("TEXTCOLOR", (1, 1), (1, 1), risk_color),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
    ]))
    return table


def _status_colors(status: str):
    if status == "Crítico":
        return RED, RED_100
    if status == "Alerta":
        return AMBER, AMBER_100
    if status == "Sin datos":
        return MUTED, PAGE
    return GREEN_700, GREEN_100


def _three_metric_grid(styles, metrics):
    cards = []
    for label, value, note in metrics:
        card = Table([
            [Paragraph(label.upper(), styles["metric_label"])],
            [Paragraph(value, styles["metric_value"])],
            [Paragraph(note, styles["small"])],
        ], colWidths=[51 * mm])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PAGE),
            ("BOX", (0, 0), (-1, -1), 0.6, LINE),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ]))
        cards.append(card)
    grid = Table([cards], colWidths=[55 * mm] * 3, hAlign="LEFT")
    grid.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return grid


def _threshold_set(attribute: str, values: dict[str, float]) -> dict[str, float]:
    if attribute == "grain_temperature":
        return _present(max=values.get("grain_temperature"), critical_max=values.get("critical_temperature"))
    if attribute == "ambient_humidity":
        return _present(max=values.get("ambient_humidity"), critical_max=values.get("critical_humidity"))
    if attribute == "level_percent":
        return _present(min=values.get("level_percent_low"), max=values.get("level_percent_high"))
    if attribute == "soil_moisture_percent":
        return _present(min=values.get("soil_moisture_low"), max=values.get("soil_moisture_high"))
    return {}


def _present(**values):
    return {key: value for key, value in values.items() if value is not None}


def _premium_metric_chart(points, label, unit, color, thresholds, events, actions, cadence_minutes):
    return _draw_metric_chart(points, label, unit, color, thresholds, events, actions, cadence_minutes, height=96 * mm)


def _compact_metric_chart(points, label, unit, color, thresholds, events, actions, cadence_minutes):
    return _draw_metric_chart(points, label, unit, color, thresholds, events, actions, cadence_minutes, height=48 * mm)


def _draw_metric_chart(points, label, unit, color, thresholds, events, actions, cadence_minutes, *, height):
    ordered = sorted((_as_utc_pdf(timestamp), float(value)) for timestamp, value in points)
    segments, gaps = _chart_segments(ordered, cadence_minutes)
    budget = max(12, 180 // max(len(segments), 1))
    sampled_segments = [_downsample_extremes(segment, budget) for segment in segments]
    sampled = [point for segment in sampled_segments for point in segment]
    values = [value for _, value in ordered]
    percentage = unit == "%"
    configured = list(thresholds.values())
    low = 0.0 if percentage else min([*values, *configured])
    high = 100.0 if percentage else max([*values, *configured])
    if not percentage:
        padding = max((high - low) * 0.14, 0.5)
        low -= padding
        high += padding
    span = high - low or 1.0
    width = 166 * mm
    left, right = 14 * mm, 8 * mm
    top = 19 * mm if height > 60 * mm else 13 * mm
    bottom = 15 * mm if height > 60 * mm else 10 * mm
    chart_width = width - left - right
    chart_height = height - top - bottom
    start = ordered[0][0]
    end = ordered[-1][0]
    time_span = max((end - start).total_seconds(), 1)
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, rx=6, ry=6, fillColor=colors.white, strokeColor=LINE, strokeWidth=0.8))
    drawing.add(Rect(left, bottom, chart_width, chart_height, fillColor=colors.HexColor("#F7FAF8"), strokeColor=None))

    def y(value):
        return bottom + (value - low) / span * chart_height

    def x(timestamp):
        return left + (timestamp - start).total_seconds() / time_span * chart_width

    max_threshold = thresholds.get("max")
    critical_max = thresholds.get("critical_max")
    min_threshold = thresholds.get("min")
    if max_threshold is not None:
        upper = critical_max if critical_max is not None else high
        drawing.add(Rect(left, y(max_threshold), chart_width, max(0, y(upper) - y(max_threshold)), fillColor=colors.HexColor("#FFF4D6"), strokeColor=None))
    if critical_max is not None:
        drawing.add(Rect(left, y(critical_max), chart_width, max(0, y(high) - y(critical_max)), fillColor=colors.HexColor("#FEE4E2"), strokeColor=None))
    if min_threshold is not None:
        drawing.add(Rect(left, y(low), chart_width, max(0, y(min_threshold) - y(low)), fillColor=colors.HexColor("#FFF4D6"), strokeColor=None))

    for index in range(5):
        grid_value = low + span * index / 4
        grid_y = y(grid_value)
        drawing.add(Line(left, grid_y, left + chart_width, grid_y, strokeColor=LINE, strokeWidth=0.35))
        drawing.add(String(left - 2 * mm, grid_y - 1.5, f"{grid_value:.0f}", textAnchor="end", fontName="Helvetica", fontSize=6.5, fillColor=MUTED))

    for key, value, stroke in (("max", max_threshold, AMBER), ("critical_max", critical_max, RED), ("min", min_threshold, AMBER)):
        if value is not None:
            drawing.add(Line(left, y(value), left + chart_width, y(value), strokeColor=stroke, strokeWidth=0.7, strokeDashArray=[4, 3]))

    for sampled_segment in sampled_segments:
        segment_path = DrawingPath()
        for index, (timestamp, value) in enumerate(sampled_segment):
            if index == 0:
                segment_path.moveTo(x(timestamp), y(value))
            else:
                segment_path.lineTo(x(timestamp), y(value))
        segment_path.strokeColor = color
        segment_path.strokeWidth = 2
        segment_path.fillColor = None
        drawing.add(segment_path)

    for gap_start, gap_end in gaps[:2]:
        gap_x1, gap_x2 = x(gap_start), x(gap_end)
        drawing.add(Rect(gap_x1, bottom, max(gap_x2 - gap_x1, 0.5), chart_height, fillColor=colors.HexColor("#F1F5F3"), strokeColor=None))
        drawing.add(String((gap_x1 + gap_x2) / 2, bottom + 2, _duration_label((gap_end - gap_start).total_seconds()), textAnchor="middle", fontName="Helvetica", fontSize=5.5, fillColor=MUTED))

    maximum_time, maximum = max(ordered, key=lambda item: item[1])
    drawing.add(Line(x(maximum_time), bottom, x(maximum_time), y(maximum), strokeColor=RED, strokeWidth=0.7, strokeDashArray=[3, 3]))
    drawing.add(Circle(x(maximum_time), y(maximum), 2.2, fillColor=RED, strokeColor=colors.white, strokeWidth=1))
    relevant_events = [event for event in events if _event_matches_chart(event.metric_code, label) and start <= _as_utc_pdf(event.timestamp) <= end]
    relevant_ids = {event.id for event in relevant_events}
    for event in relevant_events:
        event_time = _as_utc_pdf(event.timestamp)
        marker_value = event.observed_value if event.observed_value is not None else _nearest_chart_value(ordered, event_time)
        marker_color = RED if event.severity == "critical" else AMBER
        drawing.add(Circle(x(event_time), y(marker_value), 2.2, fillColor=marker_color, strokeColor=colors.white, strokeWidth=1))
    for action in actions:
        action_time = _as_utc_pdf(action.timestamp)
        if start <= action_time <= end and (action.alert_id in relevant_ids or (action.alert_id is None and "Temperatura" in label)):
            drawing.add(Circle(x(action_time), y(_nearest_chart_value(ordered, action_time)), 2, fillColor=GREEN_700, strokeColor=colors.white, strokeWidth=0.8))

    drawing.add(String(left, height - 7 * mm, label, fontName="Helvetica-Bold", fontSize=11 if height > 60 * mm else 8.5, fillColor=GREEN_950))
    drawing.add(String(width - right, height - 7 * mm, f"Actual {values[-1]:.1f} {unit}", textAnchor="end", fontName="Helvetica-Bold", fontSize=9, fillColor=color))
    drawing.add(Circle(left, height - 12 * mm, 1.5, fillColor=RED, strokeColor=None))
    drawing.add(String(left + 3 * mm, height - 12.8 * mm, "Evento", fontName="Helvetica", fontSize=6, fillColor=MUTED))
    drawing.add(Circle(left + 21 * mm, height - 12 * mm, 1.5, fillColor=GREEN_700, strokeColor=None))
    drawing.add(String(left + 24 * mm, height - 12.8 * mm, "Acción", fontName="Helvetica", fontSize=6, fillColor=MUTED))
    if not thresholds:
        drawing.add(String(width - right, height - 12 * mm, "Umbrales no configurados", textAnchor="end", fontName="Helvetica", fontSize=6.5, fillColor=MUTED))
    drawing.add(String(left, 4 * mm, _date(start), fontName="Helvetica", fontSize=6.5, fillColor=MUTED))
    drawing.add(String(width - right, 4 * mm, _date(end), textAnchor="end", fontName="Helvetica", fontSize=6.5, fillColor=MUTED))
    drawing.add(String(left + chart_width / 2, 4 * mm, f"Máx. {maximum:.1f} {unit} · {len(points)} lecturas", textAnchor="middle", fontName="Helvetica", fontSize=6.5, fillColor=MUTED))
    return drawing


def _pdf_level_visual(current: float, initial: float, thresholds: dict[str, float]):
    width, height = 166 * mm, 44 * mm
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, rx=6, ry=6, fillColor=PAGE, strokeColor=LINE, strokeWidth=0.8))
    left, bottom = 10 * mm, 6 * mm
    silo_width, silo_height = 31 * mm, 32 * mm
    outline = DrawingPath()
    outline.moveTo(left, bottom + silo_height * 0.78)
    outline.lineTo(left + silo_width / 2, bottom + silo_height)
    outline.lineTo(left + silo_width, bottom + silo_height * 0.78)
    outline.lineTo(left + silo_width, bottom + silo_height * 0.18)
    outline.lineTo(left + silo_width * 0.72, bottom)
    outline.lineTo(left + silo_width * 0.28, bottom)
    outline.lineTo(left, bottom + silo_height * 0.18)
    outline.closePath()
    outline.fillColor = colors.HexColor("#EEF5F1")
    outline.strokeColor = GREEN_900
    outline.strokeWidth = 2
    drawing.add(outline)
    fill = max(0.0, min(100.0, current)) / 100
    body_bottom = bottom + silo_height * 0.18
    body_height = silo_height * 0.6
    drawing.add(Rect(left + 2.5 * mm, body_bottom, silo_width - 5 * mm, body_height * fill, fillColor=GREEN_700, strokeColor=None))
    condition = "Normal"
    condition_color = GREEN_700
    if thresholds.get("max") is not None and current >= thresholds["max"]:
        condition, condition_color = "Atención", AMBER
    if thresholds.get("min") is not None and current <= thresholds["min"]:
        condition, condition_color = "Atención", AMBER
    drawing.add(String(50 * mm, 29 * mm, "NIVEL ACTUAL", fontName="Helvetica-Bold", fontSize=7, fillColor=MUTED))
    drawing.add(String(50 * mm, 17 * mm, f"{current:.1f}%", fontName="Helvetica-Bold", fontSize=24, fillColor=GREEN_950))
    drawing.add(String(91 * mm, 19 * mm, condition.upper(), fontName="Helvetica-Bold", fontSize=8, fillColor=condition_color))
    drawing.add(String(50 * mm, 8 * mm, f"Inicio {initial:.1f}%  ·  Variación {current - initial:+.1f} pts", fontName="Helvetica", fontSize=8, fillColor=TEXT))
    drawing.add(String(126 * mm, 8 * mm, "Altura ocupada, no volumen", fontName="Helvetica", fontSize=6.5, fillColor=MUTED))
    return drawing


def _chart_segments(ordered, cadence_minutes):
    if len(ordered) < 2:
        return [ordered], []
    intervals = sorted(
        (ordered[index][0] - ordered[index - 1][0]).total_seconds()
        for index in range(1, len(ordered))
        if ordered[index][0] > ordered[index - 1][0]
    )
    observed = intervals[(len(intervals) - 1) // 2] if intervals else 0
    expected = cadence_minutes * 60 if cadence_minutes else observed
    threshold = max(expected * 3, 15 * 60)
    segments = [[ordered[0]]]
    gaps = []
    for previous, current in zip(ordered, ordered[1:]):
        if (current[0] - previous[0]).total_seconds() > threshold:
            gaps.append((previous[0], current[0]))
            segments.append([current])
        else:
            segments[-1].append(current)
    return segments, gaps


def _downsample_extremes(points, limit):
    if len(points) <= limit:
        return points
    bucket_count = max(1, limit // 2)
    selected = {points[0][0]: points[0], points[-1][0]: points[-1]}
    for bucket in range(bucket_count):
        start = int(bucket * len(points) / bucket_count)
        end = max(start + 1, int((bucket + 1) * len(points) / bucket_count))
        values = points[start:end]
        for item in (min(values, key=lambda point: point[1]), max(values, key=lambda point: point[1])):
            selected[item[0]] = item
    return [selected[key] for key in sorted(selected)]


def _event_matches_chart(metric_code: str | None, label: str) -> bool:
    expected = {
        "Temperatura del grano": "GRAIN_TEMPERATURE_C",
        "Humedad ambiente": "AMBIENT_RELATIVE_HUMIDITY_PCT",
        "Nivel estimado": "LEVEL_PERCENT",
    }.get(label)
    return metric_code == expected


def _nearest_chart_value(points, timestamp):
    return min(points, key=lambda point: abs((point[0] - timestamp).total_seconds()))[1]


def _duration_label(seconds):
    if seconds < 3600:
        return f"Sin datos {seconds / 60:.0f} min"
    return f"Sin datos {seconds / 3600:.1f} h"


def _as_utc_pdf(value):
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _metric_interpretation(attribute: str, values: list[float], thresholds: dict[str, float]) -> str:
    if not thresholds:
        return "Umbrales no configurados. Interpretar la serie junto con la inspección operativa y el contexto del producto."
    current = values[-1]
    if thresholds.get("critical_max") is not None and current > thresholds["critical_max"]:
        return "El valor actual permanece sobre el umbral crítico configurado. Priorizar inspección y acción documentada."
    if thresholds.get("max") is not None and current > thresholds["max"]:
        return "El valor actual supera el umbral de atención configurado. Mantener seguimiento y verificar condiciones físicas."
    if thresholds.get("min") is not None and current < thresholds["min"]:
        return "El valor actual está por debajo del mínimo configurado. Verificar sensor y condición operativa."
    return "El valor actual se encuentra dentro de los límites configurados. Mantener monitoreo y bitácora al día."


def _response_timeline(styles, alert, logs, deliveries):
    related_logs = sorted((item for item in logs if item.alert_id == alert.id), key=lambda item: item.timestamp)
    delivery = next((item for item in deliveries if item.alert_id == alert.id), None)
    intervention = related_logs[0] if related_logs else None
    verification = related_logs[1] if len(related_logs) > 1 else None
    values = [
        ("Alerta", alert.created_at),
        ("Notificación", delivery.sent_at or delivery.created_at if delivery else None),
        ("Reconocimiento", alert.acknowledged_at),
        ("Intervención", intervention.timestamp if intervention else None),
        ("Verificación", verification.timestamp if verification else None),
        ("Normalización", alert.resolved_at),
    ]
    cells = []
    for label, value in values:
        cells.append(Table([
            [Paragraph(label.upper(), styles["metric_label"])],
            [Paragraph(_datetime(value) if value else "Sin dato", styles["small"])],
        ], colWidths=[26 * mm]))
    table = Table([cells], colWidths=[27.5 * mm] * 6)
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("BACKGROUND", (0, 0), (-1, -1), PAGE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def _alert_duration(alert):
    if alert.resolved_at is None:
        return "Sin dato"
    seconds = max(0, (alert.resolved_at - alert.created_at).total_seconds())
    return f"{seconds / 3600:.1f} h"


def _gap_count(readings, cadence_minutes):
    if not cadence_minutes or len(readings) < 2:
        return 0
    ordered = sorted(readings, key=lambda item: item.timestamp)
    threshold = cadence_minutes * 60 * 2
    return sum((ordered[index].timestamp - ordered[index - 1].timestamp).total_seconds() > threshold for index in range(1, len(ordered)))


def _reading_number(reading, attribute, suffix, digits=1):
    if reading is None:
        return "Sin dato"
    value = getattr(reading, attribute, None)
    return "Sin dato" if value is None else f"{value:.{digits}f}{suffix}"


def _minutes_since(value):
    aware = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return max(0, (datetime.now(timezone.utc) - aware).total_seconds() / 60)


def _current_state_copy(current_status, period_risk):
    if current_status == "Sin datos":
        return "No existe una lectura reciente suficiente para confirmar el estado actual."
    if current_status == "Normal" and period_risk in {"Alerta", "Crítico"}:
        return f"La condición actual está estable, aunque el máximo riesgo del periodo fue {period_risk.lower()}. Mantener verificación y trazabilidad."
    if current_status == "Crítico":
        return "Existe riesgo crítico activo. Inspeccionar el punto monitoreado y registrar la intervención."
    if current_status == "Alerta":
        return "La operación requiere atención preventiva y seguimiento de la siguiente lectura."
    return "La condición actual se encuentra estable con la evidencia disponible."


def _simple_state(status):
    return {"Normal": "Bien", "Alerta": "Revisar", "Crítico": "Problema", "Sin datos": "Sin dato"}.get(status, status)


def _styles():
    sample = getSampleStyleSheet()
    base = dict(allowWidows=0, allowOrphans=0, splitLongWords=0, wordWrap="LTR")
    return {
        "brand": ParagraphStyle("brand", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=25, leading=28, textColor=GREEN_900, **base),
        "tag": ParagraphStyle("tag", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=AMBER, **base),
        "eyebrow": ParagraphStyle("eyebrow", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=GREEN_700, spaceAfter=4, **base),
        "cover_title": ParagraphStyle("cover_title", parent=sample["Title"], fontName="Helvetica-Bold", fontSize=29, leading=33, textColor=GREEN_950, alignment=TA_LEFT, spaceAfter=5, **base),
        "cover_subtitle": ParagraphStyle("cover_subtitle", parent=sample["BodyText"], fontName="Helvetica", fontSize=11, leading=17, textColor=TEXT, **base),
        "section": ParagraphStyle("section", parent=sample["Heading2"], fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=GREEN_950, spaceAfter=8, **base),
        "subsection": ParagraphStyle("subsection", parent=sample["Heading3"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=GREEN_900, spaceAfter=5, **base),
        "body": ParagraphStyle("body", parent=sample["BodyText"], fontName="Helvetica", fontSize=9.2, leading=14, textColor=TEXT, **base),
        "small": ParagraphStyle("small", parent=sample["BodyText"], fontName="Helvetica", fontSize=7.5, leading=10, textColor=MUTED, **base),
        "table": ParagraphStyle("table", parent=sample["BodyText"], fontName="Helvetica", fontSize=7.1, leading=9.2, textColor=TEXT, **base),
        "table_head": ParagraphStyle("table_head", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=GREEN_950, **base),
        "metric_label": ParagraphStyle("metric_label", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=7, leading=9, textColor=MUTED, **base),
        "metric_value": ParagraphStyle("metric_value", parent=sample["BodyText"], fontName="Helvetica-Bold", fontSize=15, leading=18, textColor=GREEN_950, **base),
        "center": ParagraphStyle("center", parent=sample["BodyText"], alignment=TA_CENTER, fontName="Helvetica-Bold", fontSize=9, textColor=GREEN_900, **base),
    }


def _cover(styles, report: WeeklyReportOut, status: str, document_type: str):
    title = "Bitácora operativa y trazabilidad" if document_type == "logbook" else "Reporte técnico de monitoreo postcosecha"
    subtitle = (
        "Registro verificable de intervenciones, responsables y acciones del periodo."
        if document_type == "logbook"
        else "Monitoreo IoT, trazabilidad operativa y gestión de riesgos para almacenamiento postcosecha."
    )
    meta = [
        ["CLIENTE / INSTITUCIÓN", report.company_name, "SITIO", report.site_name],
        ["UNIDAD MONITOREADA", report.storage_unit_name, "PERIODO", report.period_label],
        ["RANGO ANALIZADO", f"{_date(report.date_from)} — {_date(report.date_to)}", "ESTADO", status],
        ["PREPARADO POR", "AgroEscudo", "VERSIÓN", "Control Center 1.0"],
    ]
    return [
        Spacer(1, 2 * mm),
        _brand_logo(styles, width=72 * mm),
        Paragraph("DATOS QUE PROTEGEN. DECISIONES QUE TRANSFORMAN.", styles["tag"]),
        Spacer(1, 20 * mm),
        Paragraph(f"INFORME {report.period_label.upper()} · EVIDENCIA OPERATIVA", styles["eyebrow"]),
        Paragraph(title, styles["cover_title"]),
        Paragraph(subtitle, styles["cover_subtitle"]),
        Spacer(1, 9 * mm),
        _status_panel(styles, status, report),
        Spacer(1, 8 * mm),
        _table(styles, meta, [35 * mm, 50 * mm, 31 * mm, 50 * mm], header=False, large=True),
        Spacer(1, 12 * mm),
        Paragraph(
            "Documento generado desde datos autorizados de AgroEscudo. Las recomendaciones apoyan la operación y deben validarse mediante inspección humana cuando exista riesgo.",
            styles["small"],
        ),
    ]


def _status_panel(styles, status, report):
    color, background = (RED, RED_100) if status == "Crítico" else (AMBER, AMBER_100) if status == "Alerta" else (GREEN_700, GREEN_100)
    table = Table(
        [[
            Paragraph("ESTADO GENERAL", styles["metric_label"]),
            Paragraph(status.upper(), styles["metric_value"]),
            Paragraph("LECTURAS", styles["metric_label"]),
            Paragraph(str(report.reading_count), styles["metric_value"]),
            Paragraph("ALERTAS", styles["metric_label"]),
            Paragraph(str(report.alerts_generated), styles["metric_value"]),
        ]],
        colWidths=[25 * mm, 30 * mm, 20 * mm, 24 * mm, 20 * mm, 25 * mm],
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (1, 0), background),
        ("TEXTCOLOR", (1, 0), (1, 0), color),
        ("BACKGROUND", (2, 0), (-1, 0), PAGE),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def _summary(styles, report, readings, alerts):
    latest = readings[-1] if readings else None
    rows = [
        ("Lecturas", str(report.reading_count), "datos"),
        ("Temp. máxima", _number(report.max_grain_temperature, " °C"), "riesgo térmico"),
        ("Humedad máxima", _number(report.max_ambient_humidity, "%"), "ambiente"),
        ("Fuera de rango", f"{report.approximate_hours_out_of_range:g} h", "aproximado"),
        ("Alertas", str(report.alerts_generated), "generadas"),
        ("Acciones", str(len(report.operational_actions)), "bitácora"),
    ]
    elements = [
        Paragraph("01 · RESUMEN EJECUTIVO", styles["eyebrow"]),
        Paragraph("Situación del periodo", styles["section"]),
        _card(styles, "Conclusión ejecutiva", _executive_summary(report, _status(alerts)), accent=AMBER),
        Spacer(1, 4 * mm),
        _metric_grid(styles, rows),
        Spacer(1, 6 * mm),
    ]
    if latest:
        latest_text = _latest_text(latest)
        elements.append(_card(styles, "Última evidencia recibida", f"{_datetime(latest.timestamp)}. {latest_text}", accent=GREEN_700))
    else:
        elements.append(_card(styles, "Disponibilidad de datos", "No se recibieron lecturas durante el periodo seleccionado.", accent=RED))
    return elements


def _trends(styles, readings):
    elements = [
        Paragraph("02 · TENDENCIAS", styles["eyebrow"]),
        Paragraph("Evolución de variables monitoreadas", styles["section"]),
        Paragraph("Cada serie se construye únicamente con lecturas del nodo y periodo seleccionados. Los espacios sin datos no se interpretan como estabilidad.", styles["body"]),
        Spacer(1, 5 * mm),
    ]
    specs = [
        ("grain_temperature", "Temperatura de grano", "°C", GREEN_700),
        ("ambient_humidity", "Humedad ambiente", "%", AMBER),
        ("level_percent", "Nivel estimado", "%", colors.HexColor("#0F766E")),
        ("soil_moisture_percent", "Humedad de suelo", "%", colors.HexColor("#2563EB")),
    ]
    charts = 0
    for attribute, label, unit, color in specs:
        points = [(item.timestamp, getattr(item, attribute)) for item in readings if getattr(item, attribute) is not None]
        if len(points) < 2:
            continue
        elements.extend([_metric_chart(points, label, unit, color), Spacer(1, 5 * mm)])
        charts += 1
        if charts == 3:
            break
    if not charts:
        elements.append(_card(styles, "Sin series suficientes", "Se requieren al menos dos lecturas válidas de una misma variable para mostrar una tendencia."))
    return elements


def _metric_chart(points, label, unit, color):
    sampled = points if len(points) <= 80 else points[:: max(1, len(points) // 80)]
    values = [float(value) for _, value in sampled]
    low, high = min(values), max(values)
    span = high - low or 1.0
    width, height = 166 * mm, 48 * mm
    left, bottom, chart_width, chart_height = 12 * mm, 10 * mm, 148 * mm, 27 * mm
    drawing = Drawing(width, height)
    drawing.add(Rect(0, 0, width, height, rx=5, ry=5, fillColor=PAGE, strokeColor=LINE, strokeWidth=0.7))
    drawing.add(String(left, height - 7 * mm, label, fontName="Helvetica-Bold", fontSize=9, fillColor=GREEN_950))
    drawing.add(String(width - 12 * mm, height - 7 * mm, f"{values[-1]:.1f} {unit}", textAnchor="end", fontName="Helvetica-Bold", fontSize=9, fillColor=color))
    for index in range(4):
        y = bottom + chart_height * index / 3
        drawing.add(Line(left, y, left + chart_width, y, strokeColor=LINE, strokeWidth=0.4))
    path = DrawingPath()
    for index, value in enumerate(values):
        x = left + chart_width * index / max(1, len(values) - 1)
        y = bottom + (value - low) / span * chart_height
        path.moveTo(x, y) if index == 0 else path.lineTo(x, y)
    path.strokeColor = color
    path.strokeWidth = 1.8
    path.fillColor = None
    drawing.add(path)
    drawing.add(String(left, 3.5 * mm, f"Mín. {low:.1f} {unit}", fontName="Helvetica", fontSize=6.8, fillColor=MUTED))
    drawing.add(String(width - 12 * mm, 3.5 * mm, f"Máx. {high:.1f} {unit} · {len(points)} puntos", textAnchor="end", fontName="Helvetica", fontSize=6.8, fillColor=MUTED))
    return drawing


def _metrics(styles, report, storage_unit, device):
    rows = [
        ["Métrica", "Valor", "Unidad", "Lectura operativa"],
        ["Temperatura máxima de grano", _number(report.max_grain_temperature), "°C", "Evaluar tendencia y umbral configurado."],
        ["Humedad ambiente máxima", _number(report.max_ambient_humidity), "%", "Revisar ventilación y condensación."],
        ["Lecturas recibidas", str(report.reading_count), "registros", "Volumen de evidencia del periodo."],
        ["Alertas generadas", str(report.alerts_generated), "eventos", "Condiciones que requieren seguimiento."],
        ["Alertas resueltas", str(report.alerts_resolved), "eventos", "Cierres documentados durante el periodo."],
        ["Horas fuera de rango", f"{report.approximate_hours_out_of_range:g}", "horas", "Estimación basada en cadencia de lecturas."],
        ["Mantenimientos", str(report.maintenance_count), "registros", "Intervenciones técnicas documentadas."],
    ]
    asset = [
        ["Activo monitoreado", storage_unit.name],
        ["Tipo de unidad", storage_unit.unit_type],
        ["Capacidad", f"{storage_unit.capacity_tons:g} t" if storage_unit.capacity_tons else "No registrada"],
        ["Nodo seleccionado", device.external_id if device else "Consolidado de la unidad"],
        ["Periodo", report.period_label],
    ]
    elements = [
        Paragraph("03 · INDICADORES", styles["eyebrow"]),
        Paragraph("Métricas y activo monitoreado", styles["section"]),
        _table(styles, rows, [50 * mm, 25 * mm, 23 * mm, 68 * mm], header=True),
        Spacer(1, 7 * mm),
        Paragraph("Ficha del activo", styles["subsection"]),
        _table(styles, asset, [45 * mm, 121 * mm], header=False, large=True),
    ]
    if report.nodes:
        node_rows = [["Nodo", "Perfil", "Lecturas", "Temp. máx.", "Humedad máx.", "Nivel"]]
        for node in report.nodes:
            level = (
                f"{_number(node.min_level_percent)} — {_number(node.max_level_percent)} %"
                if node.min_level_percent is not None and node.max_level_percent is not None
                else "Sin dato"
            )
            node_rows.append([
                node.device_external_id,
                node.device_type,
                str(node.reading_count),
                _number(node.max_grain_temperature, " °C"),
                _number(node.max_ambient_humidity, "%"),
                level,
            ])
        elements.extend([Spacer(1, 7 * mm), Paragraph("Desglose por nodo", styles["subsection"]), _table(styles, node_rows, [30 * mm, 30 * mm, 22 * mm, 28 * mm, 29 * mm, 27 * mm], header=True)])
    return elements


def _alerts(styles, alerts, device_names):
    elements = [
        Paragraph("04 · ALERTAS", styles["eyebrow"]),
        Paragraph("Eventos y respuesta recomendada", styles["section"]),
    ]
    if not alerts:
        elements.append(_card(styles, "Sin alertas generadas", "No se registraron alertas durante el periodo seleccionado.", accent=GREEN_700))
        return elements
    rows = [["Fecha", "Nodo", "Evento", "Nivel", "Estado", "Recomendación"]]
    rows.extend([
        [
            _datetime(alert.created_at),
            device_names.get(alert.device_id, f"Nodo #{alert.device_id}"),
            alert.title,
            _severity(alert.severity),
            "Activa" if alert.is_active else "Resuelta",
            _recommendation_for(alert),
        ]
        for alert in alerts[:24]
    ])
    elements.append(_table(styles, rows, [23 * mm, 24 * mm, 35 * mm, 18 * mm, 18 * mm, 48 * mm], header=True))
    if len(alerts) > 24:
        elements.extend([Spacer(1, 3 * mm), Paragraph(f"Se muestran 24 de {len(alerts)} alertas. El detalle completo permanece disponible en la plataforma.", styles["small"])])
    return elements


def _logbook(styles, logs, device_names, report):
    elements = [
        Paragraph("BITÁCORA OPERATIVA", styles["eyebrow"]),
        Paragraph(f"Trazabilidad {report.period_label.lower()} de intervenciones", styles["section"]),
        Paragraph("Cada entrada conserva fecha, nodo, responsable, categoría, acción y notas registradas por el operador.", styles["body"]),
        Spacer(1, 5 * mm),
    ]
    if not logs:
        elements.append(_card(styles, "Sin registros", "No se ingresaron acciones operativas durante el periodo seleccionado."))
        return elements
    rows = [["Fecha", "Nodo", "Responsable", "Categoría", "Acción y evidencia"]]
    informal = False
    for log in logs[:40]:
        text = f"{log.action_taken}. {shorten(log.notes or 'Sin notas adicionales.', width=230, placeholder='…')}"
        informal = informal or _looks_informal(log.action_taken) or _looks_informal(log.notes or "")
        rows.append([
            _datetime(log.timestamp),
            device_names.get(log.device_id, "Unidad completa") if log.device_id else "Unidad completa",
            log.operator_name,
            _category(log.category),
            text,
        ])
    elements.append(_table(styles, rows, [23 * mm, 24 * mm, 29 * mm, 25 * mm, 65 * mm], header=True))
    if informal:
        elements.extend([Spacer(1, 4 * mm), _card(styles, "Nota de control documental", "Registro ingresado por operador. Validar redacción antes de entregar a cliente externo.", accent=AMBER)])
    elements.extend([Spacer(1, 8 * mm), _signature_block(styles)])
    return elements


def _logs_and_recommendations(styles, logs, alerts, report, device_names):
    elements = [
        Paragraph("05 · TRAZABILIDAD", styles["eyebrow"]),
        Paragraph("Bitácora, conclusiones y próximos pasos", styles["section"]),
        *_logbook(styles, logs, device_names, report)[2:],
        CondPageBreak(55 * mm),
        Paragraph("Conclusiones y recomendaciones", styles["subsection"]),
    ]
    for index, text in enumerate(_recommendations(alerts, report), 1):
        elements.append(_card(styles, f"{index:02d} · Recomendación", text, accent=AMBER))
    return elements


def _signature_block(styles):
    table = Table([
        [Paragraph("RESPONSABLE OPERATIVO", styles["metric_label"]), Paragraph("VALIDACIÓN AGROESCUDO", styles["metric_label"])],
        [Spacer(1, 15 * mm), Spacer(1, 15 * mm)],
        [Paragraph("Nombre / firma / fecha", styles["small"]), Paragraph("Nombre / firma / fecha", styles["small"])],
    ], colWidths=[80 * mm, 80 * mm])
    table.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("BACKGROUND", (0, 0), (-1, 0), PAGE),
        ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return table


def _metric_grid(styles, metrics):
    cards = []
    for label, value, note in metrics:
        card = Table([
            [Paragraph(label.upper(), styles["metric_label"])],
            [Paragraph(value, styles["metric_value"])],
            [Paragraph(note, styles["small"])],
        ], colWidths=[49 * mm])
        card.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), PAGE),
            ("BOX", (0, 0), (-1, -1), 0.6, LINE),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 7),
            ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ]))
        cards.append(card)
    grid = Table([cards[:3], cards[3:]], colWidths=[53 * mm] * 3, hAlign="LEFT")
    grid.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return grid


def _card(styles, title, text, accent=GREEN_700):
    content = Table(
        [[Paragraph(_safe(title), styles["table_head"])], [Paragraph(_safe(text), styles["body"])]],
        colWidths=[166 * mm],
    )
    content.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PAGE),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, accent),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ]))
    return KeepTogether([content, Spacer(1, 3 * mm)])


def _table(styles, rows, widths, header, large=False):
    cells = []
    for row_index, row in enumerate(rows):
        style = styles["table_head"] if header and row_index == 0 else styles["table"]
        cells.append([Paragraph(_safe(value), style) for value in row])
    table = LongTable(cells, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT", splitByRow=1)
    rules = [
        ("BOX", (0, 0), (-1, -1), 0.6, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, 0), PAGE if header else colors.white),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, colors.HexColor("#FBFDFC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 8 if large else 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8 if large else 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]
    table.setStyle(TableStyle(rules))
    return table


def _decorate_page(canvas, doc, label, cover=False):
    width, height = A4
    canvas.saveState()
    canvas.setFillColor(GREEN_950)
    canvas.rect(0, height - 5 * mm, width, 5 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.55)
    canvas.line(18 * mm, height - 13 * mm, width - 18 * mm, height - 13 * mm)
    canvas.line(18 * mm, 12 * mm, width - 18 * mm, 12 * mm)
    canvas.setStrokeColor(AMBER)
    canvas.setLineWidth(1.2)
    canvas.line(width - 54 * mm, height - 13 * mm, width - 18 * mm, height - 13 * mm)
    _circuit(canvas, width - 16 * mm, height - 34 * mm)
    canvas.setFillColor(GREEN_900)
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawString(18 * mm, 7 * mm, "AGROESCUDO · EVIDENCIA OPERATIVA")
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawRightString(width - 18 * mm, 7 * mm, label)
    if cover:
        canvas.setFillColor(AMBER)
        canvas.circle(18 * mm, height - 13 * mm, 1.4 * mm, fill=1, stroke=0)
    canvas.restoreState()


def _circuit(canvas, x, y):
    canvas.setStrokeColor(colors.HexColor("#BFD2CA"))
    canvas.setLineWidth(0.45)
    for offset in (0, 5 * mm, 10 * mm):
        canvas.line(x - offset, y, x - offset, y - 12 * mm)
        canvas.line(x - offset, y - 12 * mm, x - offset - 7 * mm, y - 19 * mm)
        canvas.circle(x - offset - 7 * mm, y - 19 * mm, 0.8 * mm, fill=0, stroke=1)


def _executive_summary(report, status):
    if not report.reading_count:
        return "No se cuenta con evidencia suficiente para emitir una conclusión técnica del periodo. Validar conectividad y continuidad de lecturas."
    if status == "Crítico":
        return "Durante el periodo se identificaron condiciones fuera de rango que requieren seguimiento operativo, inspección física y registro de acciones correctivas."
    if status == "Alerta":
        return "Durante el periodo se identificaron condiciones preventivas que requieren observación y seguimiento documentado."
    return "Las condiciones registradas se mantuvieron dentro de rangos operativos aceptables durante el periodo analizado."


def _recommendations(alerts, report):
    if not report.reading_count:
        return ["Restablecer la continuidad de datos antes de emitir una conclusión técnica."]
    values = []
    if any(alert.severity == "critical" for alert in alerts):
        values.append("Priorizar intervención operativa, inspección física y registro de la acción correctiva.")
    if any("humidity" in alert.alert_type for alert in alerts):
        values.append("Revisar ventilación, aireación y posibles puntos de condensación.")
    if any("temperature" in alert.alert_type or "environment" in alert.alert_type for alert in alerts):
        values.append("Inspeccionar el punto monitoreado y verificar acumulación térmica.")
    if any("battery" in alert.alert_type for alert in alerts):
        values.append("Programar revisión técnica de batería y alimentación del nodo.")
    if any("level" in alert.alert_type or "distance" in alert.alert_type for alert in alerts):
        values.append("Validar lectura ultrasónica y calibración antes de interpretar el nivel.")
    return values or ["Mantener monitoreo, revisión periódica de umbrales y bitácora operativa actualizada."]


def _recommendation_for(alert):
    value = alert.alert_type.lower()
    if "humidity" in value:
        return "Revisar ventilación y condensación."
    if "temperature" in value or "environment" in value:
        return "Inspeccionar acumulación térmica."
    if "battery" in value:
        return "Revisar batería y alimentación."
    if "level" in value or "distance" in value:
        return "Validar sensor y calibración."
    return "Evaluar condición y registrar acción."


def _latest_text(reading):
    values = []
    for label, value, unit, digits in (
        ("Temperatura de grano", reading.grain_temperature, "°C", 1),
        ("Temperatura ambiente", reading.ambient_temperature, "°C", 1),
        ("Humedad ambiente", reading.ambient_humidity, "%", 1),
        ("Nivel", reading.level_percent, "%", 1),
        ("Humedad de suelo", reading.soil_moisture_percent, "%", 1),
        ("Batería", reading.battery_voltage, "V", 2),
    ):
        if value is not None:
            values.append(f"{label}: {value:.{digits}f} {unit}")
    return "; ".join(values) if values else "Sin métricas operativas disponibles."


def _status(alerts):
    if any(alert.severity == "critical" for alert in alerts):
        return "Crítico"
    if alerts:
        return "Alerta"
    return "Normal"


def _severity(value):
    return {"critical": "Crítica", "warning": "Preventiva", "technical": "Técnica"}.get(value, value)


def _category(value):
    return {
        "installation": "Instalación",
        "maintenance": "Mantenimiento",
        "corrective_action": "Acción correctiva",
        "inspection": "Inspección",
        "general": "General",
    }.get(value, value)


def _looks_informal(value: str) -> bool:
    letters = "".join(char for char in value if char.isalpha())
    return len(letters) > 8 and letters.isupper()


def _brand_logo(styles, width):
    if LOGO_PATH.exists():
        image = ImageReader(str(LOGO_PATH))
        source_width, source_height = image.getSize()
        height = width * source_height / source_width
        return Image(str(LOGO_PATH), width=width, height=height)
    return Paragraph("AgroEscudo", styles["brand"])


def _safe(value):
    return escape(str(value if value is not None else "Dato no disponible"))


def _date(value):
    return value.strftime("%d/%m/%Y")


def _datetime(value):
    return value.strftime("%d/%m/%Y %H:%M")


def _number(value, suffix="", digits=1):
    return "Dato no disponible" if value is None else f"{value:.{digits}f}{suffix}"
