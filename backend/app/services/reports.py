from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Alert, Company, OperationalLog, SensorReading, Site, StorageUnit, ThresholdConfig
from app.schemas import WeeklyReportOut


def build_weekly_report(db: Session, storage_unit_id: int) -> WeeklyReportOut | None:
    storage_unit = db.get(StorageUnit, storage_unit_id)
    if storage_unit is None:
        return None

    site = db.get(Site, storage_unit.site_id)
    company = db.get(Company, storage_unit.company_id)
    date_to = datetime.now(timezone.utc)
    date_from = date_to - timedelta(days=7)

    readings = list(
        db.scalars(
            select(SensorReading)
            .where(
                SensorReading.storage_unit_id == storage_unit_id,
                SensorReading.timestamp >= date_from,
                SensorReading.timestamp <= date_to,
            )
            .order_by(SensorReading.timestamp.asc())
        ).all()
    )

    alerts_generated = db.scalar(
        select(func.count(Alert.id)).where(
            Alert.storage_unit_id == storage_unit_id,
            Alert.created_at >= date_from,
            Alert.created_at <= date_to,
        )
    ) or 0
    alerts_resolved = db.scalar(
        select(func.count(Alert.id)).where(
            Alert.storage_unit_id == storage_unit_id,
            Alert.resolved_at >= date_from,
            Alert.resolved_at <= date_to,
        )
    ) or 0

    actions = list(
        db.scalars(
            select(OperationalLog)
            .where(
                OperationalLog.storage_unit_id == storage_unit_id,
                OperationalLog.timestamp >= date_from,
                OperationalLog.timestamp <= date_to,
            )
            .order_by(OperationalLog.timestamp.desc())
        ).all()
    )

    max_grain = max((reading.grain_temperature for reading in readings), default=None)
    max_humidity = max((reading.ambient_humidity for reading in readings), default=None)
    hours_out_of_range = estimate_hours_out_of_range(db, storage_unit, readings)
    installation_count = _log_count(db, storage_unit_id, "installation", date_from, date_to)
    maintenance_count = _log_count(db, storage_unit_id, "maintenance", date_from, date_to)
    from app.services.pilots import calculate_pilot_status

    return WeeklyReportOut(
        company_name=company.name if company else "",
        site_name=site.name if site else "",
        storage_unit_name=storage_unit.name,
        date_from=date_from,
        date_to=date_to,
        reading_count=len(readings),
        max_grain_temperature=max_grain,
        max_ambient_humidity=max_humidity,
        alerts_generated=alerts_generated,
        alerts_resolved=alerts_resolved,
        approximate_hours_out_of_range=hours_out_of_range,
        pilot_status=calculate_pilot_status(db, storage_unit),
        installation_count=installation_count,
        maintenance_count=maintenance_count,
        last_report_generated_at=storage_unit.last_report_generated_at,
        operational_actions=actions,
    )


def estimate_hours_out_of_range(
    db: Session,
    storage_unit: StorageUnit,
    readings: list[SensorReading],
) -> float:
    if not readings:
        return 0.0

    grain_threshold = _threshold_value(db, storage_unit, "grain_temperature")
    humidity_threshold = _threshold_value(db, storage_unit, "ambient_humidity")
    if grain_threshold is None and humidity_threshold is None:
        return 0.0

    out_count = sum(
        1
        for reading in readings
        if (
            grain_threshold is not None
            and reading.grain_temperature > grain_threshold
        )
        or (
            humidity_threshold is not None
            and reading.ambient_humidity > humidity_threshold
        )
    )

    if len(readings) == 1:
        return float(out_count)

    span_hours = (readings[-1].timestamp - readings[0].timestamp).total_seconds() / 3600
    avg_interval = max(span_hours / (len(readings) - 1), 1.0)
    return round(out_count * avg_interval, 2)


def _log_count(
    db: Session,
    storage_unit_id: int,
    category: str,
    date_from: datetime,
    date_to: datetime,
) -> int:
    return db.scalar(
        select(func.count(OperationalLog.id)).where(
            OperationalLog.storage_unit_id == storage_unit_id,
            OperationalLog.category == category,
            OperationalLog.timestamp >= date_from,
            OperationalLog.timestamp <= date_to,
        )
    ) or 0


def _threshold_value(db: Session, storage_unit: StorageUnit, metric: str) -> float | None:
    config = db.scalar(
        select(ThresholdConfig).where(
            ThresholdConfig.company_id == storage_unit.company_id,
            ThresholdConfig.storage_unit_id == storage_unit.id,
            ThresholdConfig.metric == metric,
            ThresholdConfig.is_active.is_(True),
        )
    )
    if config is not None:
        return config.value

    company_config = db.scalar(
        select(ThresholdConfig).where(
            ThresholdConfig.company_id == storage_unit.company_id,
            ThresholdConfig.storage_unit_id.is_(None),
            ThresholdConfig.metric == metric,
            ThresholdConfig.is_active.is_(True),
        )
    )
    return company_config.value if company_config is not None else None
