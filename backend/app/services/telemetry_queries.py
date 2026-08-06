from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DeviceChannel, MetricReading, SensorReading, User
from app.schemas import MetricReadingPointOut, MetricReadingsOut


LEGACY_METRIC_FIELDS = {
    "GRAIN_TEMPERATURE_C": ("grain_temperature", "degC", 1.0),
    "AMBIENT_TEMPERATURE_C": ("ambient_temperature", "degC", 1.0),
    "AMBIENT_RELATIVE_HUMIDITY_PCT": ("ambient_humidity", "percent", 1.0),
    "SOIL_MOISTURE_PCT": ("soil_moisture_percent", "percent", 1.0),
    "LEVEL_DISTANCE_MM": ("level_distance_cm", "mm", 10.0),
    "LEVEL_PERCENT": ("level_percent", "percent", 1.0),
    "BATTERY_VOLTAGE_MV": ("battery_voltage", "mV", 1000.0),
    "SIGNAL_RSSI_DBM": ("signal_quality", "dBm", 1.0),
}


def query_metric_readings(
    db: Session,
    *,
    device_id: int,
    channel: DeviceChannel,
    metric_code: str,
    user: User,
    from_: datetime | None,
    to: datetime | None,
    resolution: str,
    limit: int,
    order: str,
) -> MetricReadingsOut:
    stmt = select(MetricReading).where(
        MetricReading.device_id == device_id,
        MetricReading.sensor_channel_id == channel.id,
        MetricReading.metric_code == metric_code,
    )
    if from_ is not None:
        stmt = stmt.where(MetricReading.sampled_at >= from_)
    if to is not None:
        stmt = stmt.where(MetricReading.sampled_at <= to)
    direction = MetricReading.sampled_at.asc() if order == "asc" else MetricReading.sampled_at.desc()
    normalized = list(db.scalars(stmt.order_by(direction).limit(limit)).all())
    if normalized:
        points = [
            MetricReadingPointOut(
                id=row.id,
                telemetry_event_id=row.telemetry_event_id,
                device_id=device_id,
                channel_key=channel.channel_key,
                metric_code=metric_code,
                raw_value=row.raw_value if user.role in {"admin", "technician"} else None,
                calibrated_value=row.calibrated_value,
                value=row.display_value,
                unit=row.canonical_unit,
                quality_status=row.quality_status,
                calibration_version=row.calibration_version,
                sampled_at=row.sampled_at,
                source="normalized",
            )
            for row in normalized
        ]
    else:
        points = _legacy_fallback(
            db,
            device_id=device_id,
            channel=channel,
            metric_code=metric_code,
            user=user,
            from_=from_,
            to=to,
            limit=limit,
            order=order,
        )
    return MetricReadingsOut(
        device_id=device_id,
        channel_key=channel.channel_key,
        metric_code=metric_code,
        resolution=resolution,
        reconciliation_approved=False,
        points=_aggregate(points, resolution, order),
    )


def _legacy_fallback(
    db: Session,
    *,
    device_id: int,
    channel: DeviceChannel,
    metric_code: str,
    user: User,
    from_: datetime | None,
    to: datetime | None,
    limit: int,
    order: str,
) -> list[MetricReadingPointOut]:
    mapping = LEGACY_METRIC_FIELDS.get(metric_code)
    if mapping is None:
        return []
    field_name, unit, multiplier = mapping
    if metric_code == "SIGNAL_RSSI_DBM" and user.role == "client":
        return []
    stmt = select(SensorReading).where(SensorReading.device_id == device_id)
    if from_ is not None:
        stmt = stmt.where(SensorReading.timestamp >= from_)
    if to is not None:
        stmt = stmt.where(SensorReading.timestamp <= to)
    direction = SensorReading.timestamp.asc() if order == "asc" else SensorReading.timestamp.desc()
    rows = db.scalars(stmt.order_by(direction).limit(limit)).all()
    result = []
    for row in rows:
        value = getattr(row, field_name)
        if value is None:
            continue
        result.append(
            MetricReadingPointOut(
                device_id=device_id,
                channel_key=channel.channel_key,
                metric_code=metric_code,
                raw_value=float(value) * multiplier if user.role in {"admin", "technician"} else None,
                value=float(value) * multiplier,
                unit=unit,
                quality_status="LEGACY_UNVERSIONED",
                sampled_at=row.timestamp,
                source="legacy_fallback",
            )
        )
    return result


def _aggregate(
    points: list[MetricReadingPointOut],
    resolution: str,
    order: str,
) -> list[MetricReadingPointOut]:
    seconds = {"raw": 0, "5m": 300, "15m": 900, "1h": 3600, "1d": 86400}[resolution]
    if seconds == 0 or not points:
        return points
    buckets: dict[int, list[MetricReadingPointOut]] = defaultdict(list)
    for point in points:
        key = int(point.sampled_at.timestamp()) // seconds
        buckets[key].append(point)
    aggregated = []
    for bucket_points in buckets.values():
        values = [point.value for point in bucket_points if point.value is not None]
        if not values:
            continue
        base = bucket_points[0]
        aggregated.append(
            base.model_copy(
                update={
                    "id": None,
                    "telemetry_event_id": None,
                    "raw_value": None,
                    "calibrated_value": None,
                    "value": sum(values) / len(values),
                    "quality_status": "AGGREGATED",
                }
            )
        )
    return sorted(aggregated, key=lambda item: item.sampled_at, reverse=order == "desc")
