from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device, DeviceChannel, MetricReading, SensorReading, User
from app.schemas import (
    MetricDataGapOut,
    MetricReadingPointOut,
    MetricReadingsOut,
    MetricSeriesPeriodOut,
    MetricSeriesSummaryOut,
)


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
    normalized = list(db.scalars(stmt.order_by(direction)).all())
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
                bucket_min=row.display_value,
                bucket_max=row.display_value,
                sample_count=1,
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
    chronological = sorted(points, key=lambda item: _epoch(item.sampled_at))
    device = db.get(Device, device_id)
    gaps, coverage_seconds = _detect_gaps(
        chronological,
        device.expected_reading_interval_minutes if device else None,
    )
    aggregated = _aggregate(chronological, resolution)
    ordered = sorted(
        aggregated,
        key=lambda item: _epoch(item.sampled_at),
        reverse=order == "desc",
    )
    visible = ordered[:limit]
    values = [point.value for point in chronological if point.value is not None]
    period_from = from_ or (chronological[0].sampled_at if chronological else None)
    period_to = to or (chronological[-1].sampled_at if chronological else None)
    current = chronological[-1].value if chronological else None
    initial = chronological[0].value if chronological else None
    return MetricReadingsOut(
        device_id=device_id,
        channel_key=channel.channel_key,
        metric_code=metric_code,
        resolution=resolution,
        reconciliation_approved=False,
        points=visible,
        period=MetricSeriesPeriodOut(from_=period_from, to=period_to),
        summary=MetricSeriesSummaryOut(
            current=current,
            initial=initial,
            minimum=min(values) if values else None,
            maximum=max(values) if values else None,
            average=sum(values) / len(values) if values else None,
            change=current - initial if current is not None and initial is not None else None,
            sample_count=len(values),
            point_count=len(aggregated),
            coverage_seconds=coverage_seconds,
        ),
        gaps=gaps,
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
    rows = db.scalars(stmt.order_by(direction)).all()
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
                bucket_min=float(value) * multiplier,
                bucket_max=float(value) * multiplier,
                sample_count=1,
            )
        )
    return result


def _aggregate(
    points: list[MetricReadingPointOut],
    resolution: str,
) -> list[MetricReadingPointOut]:
    seconds = {"raw": 0, "5m": 300, "15m": 900, "1h": 3600, "1d": 86400}[resolution]
    if seconds == 0 or not points:
        return points
    buckets: dict[int, list[MetricReadingPointOut]] = defaultdict(list)
    for point in points:
        key = int(_epoch(point.sampled_at)) // seconds
        buckets[key].append(point)
    aggregated = []
    for key, bucket_points in sorted(buckets.items()):
        bucket_points.sort(key=lambda item: _epoch(item.sampled_at))
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
                    "sampled_at": datetime.fromtimestamp(key * seconds, tz=timezone.utc),
                    "bucket_min": min(values),
                    "bucket_max": max(values),
                    "sample_count": sum(point.sample_count for point in bucket_points),
                }
            )
        )
    return aggregated


def _detect_gaps(
    points: list[MetricReadingPointOut],
    cadence_minutes: int | None,
) -> tuple[list[MetricDataGapOut], float]:
    if len(points) < 2:
        return [], 0
    timestamps = [_utc(point.sampled_at) for point in points]
    deltas = [
        (current - previous).total_seconds()
        for previous, current in zip(timestamps, timestamps[1:])
        if current > previous
    ]
    if not deltas:
        return [], 0
    expected_seconds = cadence_minutes * 60 if cadence_minutes else median(deltas)
    gap_threshold = max(expected_seconds * 3, 15 * 60)
    gaps: list[MetricDataGapOut] = []
    coverage = 0.0
    for previous, current in zip(timestamps, timestamps[1:]):
        delta = (current - previous).total_seconds()
        if delta > gap_threshold:
            gaps.append(MetricDataGapOut(from_=previous, to=current, duration_seconds=delta))
        elif delta > 0:
            coverage += delta
    return gaps, coverage


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _epoch(value: datetime) -> float:
    return _utc(value).timestamp()
