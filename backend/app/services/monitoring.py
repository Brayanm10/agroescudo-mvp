from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import scope_storage_units_query
from app.core.config import settings
from app.models import Alert, Device, OperationalLog, SensorReading, StorageUnit, User, utc_now
from app.schemas import MonitoringActivityOut, MonitoringMilestoneOut, MonitoringSummaryOut


def build_monitoring_summary(db: Session, user: User) -> MonitoringSummaryOut:
    now = _aware(utc_now())
    today_start = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)
    history_start = today_start - timedelta(days=89)
    units = list(db.scalars(scope_storage_units_query(select(StorageUnit), user, db)).all())
    unit_ids = [unit.id for unit in units]
    devices = list(
        db.scalars(
            select(Device).where(
                Device.storage_unit_id.in_(unit_ids) if unit_ids else Device.id == -1,
                Device.is_active.is_(True),
            )
        ).all()
    )
    device_ids = [device.id for device in devices]
    readings = list(
        db.scalars(
            select(SensorReading)
            .where(
                SensorReading.device_id.in_(device_ids) if device_ids else SensorReading.id == -1,
                SensorReading.timestamp >= history_start,
                SensorReading.timestamp <= now,
            )
            .order_by(SensorReading.timestamp.asc())
        ).all()
    )

    readings_by_device_day: dict[tuple[int, date], int] = defaultdict(int)
    for reading in readings:
        readings_by_device_day[(reading.device_id, _aware(reading.timestamp).date())] += 1

    daily_coverages: list[tuple[date, float]] = []
    current_day = history_start.date()
    while current_day <= now.date():
        day_start = datetime.combine(current_day, time.min, tzinfo=timezone.utc)
        day_end = min(day_start + timedelta(days=1), now)
        expected = received = eligible = 0
        calculable = True
        for device in devices:
            cadence = device.expected_reading_interval_minutes
            active_from = max(day_start, _aware(device.installed_at or device.created_at))
            if active_from >= day_end:
                continue
            eligible += 1
            if not cadence or cadence <= 0:
                calculable = False
                continue
            expected_for_device = max(1, int((day_end - active_from).total_seconds() // (cadence * 60)) + 1)
            expected += expected_for_device
            received += min(readings_by_device_day[(device.id, current_day)], expected_for_device)
        if eligible and calculable and expected:
            daily_coverages.append((current_day, round(received / expected * 100, 2)))
        current_day += timedelta(days=1)

    coverage_by_day = dict(daily_coverages)
    coverage_today = coverage_by_day.get(now.date())
    target = settings.monitoring_coverage_target_pct
    current_streak = 0
    cursor = now.date()
    while cursor in coverage_by_day and coverage_by_day[cursor] >= target:
        current_streak += 1
        cursor -= timedelta(days=1)

    best_streak = running = 0
    for _day, coverage in daily_coverages:
        if coverage >= target:
            running += 1
            best_streak = max(best_streak, running)
        else:
            running = 0

    received_today = sum(1 for reading in readings if _aware(reading.timestamp) >= today_start)
    expected_today = _expected_for_period(devices, today_start, now) if coverage_today is not None else None
    offline_cutoff = now - timedelta(minutes=settings.device_offline_after_minutes)
    online_devices = sum(1 for device in devices if device.last_seen_at and _aware(device.last_seen_at) >= offline_cutoff)

    alerts = list(
        db.scalars(
            select(Alert)
            .where(Alert.storage_unit_id.in_(unit_ids) if unit_ids else Alert.id == -1)
            .order_by(Alert.created_at.desc())
            .limit(8)
        ).all()
    )
    logs = list(
        db.scalars(
            select(OperationalLog)
            .where(OperationalLog.storage_unit_id.in_(unit_ids) if unit_ids else OperationalLog.id == -1)
            .order_by(OperationalLog.timestamp.desc())
            .limit(8)
        ).all()
    )

    return MonitoringSummaryOut(
        current_streak_days=current_streak,
        best_streak_days=best_streak,
        coverage_today_pct=coverage_today,
        coverage_target_pct=target,
        expected_readings_today=expected_today,
        received_readings_today=received_today,
        active_devices=len(devices),
        online_devices=online_devices,
        no_data_devices=len(devices) - online_devices,
        calculation_status="available" if coverage_today is not None else "not_calculable",
        recent_activity=_recent_activity(readings[-8:], alerts, logs)[:5],
        milestones=_milestones(units, devices, readings, alerts, current_streak, best_streak),
        generated_at=now,
    )


def _expected_for_period(devices: list[Device], start: datetime, end: datetime) -> int:
    total = 0
    for device in devices:
        cadence = device.expected_reading_interval_minutes
        if not cadence or cadence <= 0:
            continue
        active_from = max(start, _aware(device.installed_at or device.created_at))
        if active_from < end:
            total += max(1, int((end - active_from).total_seconds() // (cadence * 60)) + 1)
    return total


def _recent_activity(
    readings: list[SensorReading], alerts: list[Alert], logs: list[OperationalLog]
) -> list[MonitoringActivityOut]:
    items: list[MonitoringActivityOut] = []
    if readings:
        reading = readings[-1]
        items.append(
            MonitoringActivityOut(
                kind="reading",
                title="Lectura recibida",
                detail="La plataforma recibió nueva telemetría de la unidad monitoreada.",
                timestamp=reading.timestamp,
                storage_unit_id=reading.storage_unit_id,
                device_id=reading.device_id,
            )
        )
    for alert in alerts[:3]:
        items.append(
            MonitoringActivityOut(
                kind="alert",
                title="Alerta resuelta" if not alert.is_active else "Alerta activa",
                detail=alert.title,
                timestamp=alert.resolved_at or alert.created_at,
                storage_unit_id=alert.storage_unit_id,
                device_id=alert.device_id,
                severity=alert.severity,
            )
        )
    for log in logs[:3]:
        items.append(
            MonitoringActivityOut(
                kind="action",
                title="Acción registrada",
                detail=log.action_taken,
                timestamp=log.timestamp,
                storage_unit_id=log.storage_unit_id,
                device_id=log.device_id,
            )
        )
    return sorted(items, key=lambda item: _aware(item.timestamp), reverse=True)


def _milestones(
    units: list[StorageUnit],
    devices: list[Device],
    readings: list[SensorReading],
    alerts: list[Alert],
    current_streak: int,
    best_streak: int,
) -> list[MonitoringMilestoneOut]:
    milestones: list[MonitoringMilestoneOut] = []
    if devices:
        first = min(devices, key=lambda item: _aware(item.created_at))
        milestones.append(MonitoringMilestoneOut(key="first_sensor", label="Primer sensor conectado", achieved_at=first.created_at))
    if readings:
        first_reading = min(readings, key=lambda item: _aware(item.timestamp))
        milestones.append(MonitoringMilestoneOut(key="first_reading", label="Primera telemetría recibida", achieved_at=first_reading.timestamp))
    if max(current_streak, best_streak) >= 7:
        milestones.append(MonitoringMilestoneOut(key="seven_days", label="7 días de monitoreo continuo"))
    report_dates = [unit.last_report_generated_at for unit in units if unit.last_report_generated_at]
    if report_dates:
        milestones.append(MonitoringMilestoneOut(key="first_report", label="Primer reporte generado", achieved_at=min(report_dates)))
    resolved = [alert for alert in alerts if alert.resolved_at]
    if resolved:
        first_resolved = min(alert.resolved_at for alert in resolved if alert.resolved_at)
        milestones.append(MonitoringMilestoneOut(key="first_alert_resolved", label="Primera alerta atendida", achieved_at=first_resolved))
    return milestones


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
