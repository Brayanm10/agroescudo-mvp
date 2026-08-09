from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import Alert, MetricDefinition, OperationalLog
from app.schemas import (
    DeviceChartActionOut,
    DeviceChartContextOut,
    DeviceChartEventOut,
    MetricSeriesPeriodOut,
)


LEGACY_METRIC_CODES = {
    "grain_temperature": "GRAIN_TEMPERATURE_C",
    "ambient_temperature": "AMBIENT_TEMPERATURE_C",
    "ambient_humidity": "AMBIENT_RELATIVE_HUMIDITY_PCT",
    "level_percent": "LEVEL_PERCENT",
    "level_distance_cm": "LEVEL_DISTANCE_MM",
    "soil_moisture_percent": "SOIL_MOISTURE_PCT",
    "soil_temperature_c": "SOIL_TEMPERATURE_C",
    "battery_voltage": "BATTERY_VOLTAGE_MV",
}


def build_device_chart_context(
    db: Session,
    *,
    device_id: int,
    from_: datetime | None,
    to: datetime | None,
) -> DeviceChartContextOut:
    alert_stmt = select(Alert).where(Alert.device_id == device_id)
    if from_ is not None:
        alert_stmt = alert_stmt.where(Alert.created_at >= from_)
    if to is not None:
        alert_stmt = alert_stmt.where(Alert.created_at <= to)
    alerts = list(db.scalars(alert_stmt.order_by(Alert.created_at)).all())

    definitions = {
        item.id: item.metric_code
        for item in db.scalars(
            select(MetricDefinition).where(
                MetricDefinition.id.in_(
                    [item.metric_definition_id for item in alerts if item.metric_definition_id is not None]
                )
            )
        ).all()
    }
    events = [
        DeviceChartEventOut(
            id=alert.id,
            timestamp=alert.created_at,
            event_type=alert.alert_type,
            severity=alert.severity,
            title=alert.title,
            metric_code=definitions.get(alert.metric_definition_id)
            or LEGACY_METRIC_CODES.get(alert.metric or ""),
            observed_value=alert.observed_value,
            threshold_value=alert.threshold_value,
            status=(
                "resolved"
                if alert.resolved_at is not None
                else "acknowledged"
                if alert.acknowledged_at is not None
                else "active"
            ),
        )
        for alert in alerts
    ]

    action_stmt = (
        select(OperationalLog)
        .outerjoin(Alert, OperationalLog.alert_id == Alert.id)
        .where(or_(OperationalLog.device_id == device_id, Alert.device_id == device_id))
    )
    if from_ is not None:
        action_stmt = action_stmt.where(OperationalLog.timestamp >= from_)
    if to is not None:
        action_stmt = action_stmt.where(OperationalLog.timestamp <= to)
    logs = list(db.scalars(action_stmt.order_by(OperationalLog.timestamp)).unique().all())
    actions = [
        DeviceChartActionOut(
            id=log.id,
            timestamp=log.timestamp,
            category=log.category,
            title=log.action_taken,
            result=log.notes or None,
            operator_name=log.operator_name,
            alert_id=log.alert_id,
        )
        for log in logs
    ]
    return DeviceChartContextOut(
        device_id=device_id,
        period=MetricSeriesPeriodOut(from_=from_, to=to),
        events=events,
        actions=actions,
    )
