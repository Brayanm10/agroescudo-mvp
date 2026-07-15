from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Alert, Device, OperationalLog, SensorReading, Site, StorageUnit, utc_now
from app.schemas import (
    AlertOut,
    ControlCenterBreakdownItem,
    ControlCenterDeviceHealthOut,
    ControlCenterPriorityOut,
    ControlCenterSiteOut,
    ControlCenterSummaryOut,
    OperationalLogOut,
)


FORMULA_VERSION = "control-index-v1.0"


def _score_status(score: int, has_data: bool) -> str:
    if not has_data:
        return "SIN_DATOS"
    if score >= 90:
        return "PROTEGIDA"
    if score >= 70:
        return "ATENCION"
    return "CRITICA"


def _penalty(count: int | float, value: float, cap: float) -> float:
    return min(float(count) * value, cap)


def build_control_center_summary(db: Session, user) -> ControlCenterSummaryOut:
    from app.api.deps import scope_storage_units_query

    now = utc_now()
    unit_stmt = scope_storage_units_query(select(StorageUnit), user, db)
    storage_units = list(db.scalars(unit_stmt).all())
    unit_ids = [unit.id for unit in storage_units]

    if not unit_ids:
        return ControlCenterSummaryOut(
            generated_at=now,
            score=0,
            status="SIN_DATOS",
            formula_version=FORMULA_VERSION,
            breakdown=[],
            kpis={"storage_units": 0, "active_alerts": 0, "readings_24h": 0},
            priorities=[],
            sites=[],
            device_health=[],
            recent_alerts=[],
            recent_activity=[],
        )

    device_stmt = select(Device).where(Device.storage_unit_id.in_(unit_ids))
    devices = list(db.scalars(device_stmt).all())
    device_ids = [device.id for device in devices]

    active_alerts = list(
        db.scalars(
            select(Alert)
            .where(Alert.storage_unit_id.in_(unit_ids), Alert.is_active.is_(True))
            .order_by(Alert.created_at.desc())
        ).all()
    )
    critical_alerts = [alert for alert in active_alerts if alert.severity == "critical"]
    warning_alerts = [alert for alert in active_alerts if alert.severity in {"warning", "high", "technical"}]

    reading_cutoff = now - timedelta(hours=24)
    readings_24h = db.scalar(
        select(func.count(SensorReading.id)).where(
            SensorReading.storage_unit_id.in_(unit_ids),
            SensorReading.timestamp >= reading_cutoff,
        )
    ) or 0

    latest_by_device: dict[int, SensorReading] = {}
    if device_ids:
        rows = db.scalars(
            select(SensorReading)
            .where(SensorReading.device_id.in_(device_ids))
            .order_by(SensorReading.device_id.asc(), SensorReading.timestamp.desc())
        ).all()
        for reading in rows:
            latest_by_device.setdefault(reading.device_id, reading)

    offline_after = timedelta(minutes=settings.device_offline_after_minutes)
    offline_devices = 0
    stale_readings = 0
    low_battery = 0
    device_health: list[ControlCenterDeviceHealthOut] = []
    for device in devices:
        latest = latest_by_device.get(device.id)
        last_seen_at = latest.timestamp if latest else device.last_seen_at
        is_offline = last_seen_at is None or now - last_seen_at > offline_after
        if is_offline:
            offline_devices += 1
        if latest and now - latest.timestamp > offline_after:
            stale_readings += 1
        if latest and latest.battery_voltage < 3.5:
            low_battery += 1
        device_health.append(
            ControlCenterDeviceHealthOut(
                device_id=device.id,
                external_id=device.external_id,
                storage_unit_id=device.storage_unit_id,
                status="offline" if is_offline else "online",
                last_seen_at=last_seen_at,
                battery_voltage=latest.battery_voltage if latest else None,
                signal_quality=latest.signal_quality if latest else None,
            )
        )

    resolved_alerts = db.scalar(
        select(func.count(Alert.id)).where(Alert.storage_unit_id.in_(unit_ids), Alert.is_active.is_(False), Alert.resolved_at.is_not(None))
    ) or 0
    logs_count = db.scalar(select(func.count(OperationalLog.id)).where(OperationalLog.storage_unit_id.in_(unit_ids))) or 0
    hours_out_of_range = sum(1 for alert in active_alerts if alert.severity in {"warning", "critical"}) * 2
    maintenance_overdue = db.scalar(
        select(func.count(OperationalLog.id)).where(
            OperationalLog.storage_unit_id.in_(unit_ids),
            OperationalLog.category == "maintenance",
            OperationalLog.timestamp < now - timedelta(days=30),
        )
    ) or 0

    breakdown = [
        ControlCenterBreakdownItem(key="critical_alerts", label="Alertas criticas activas", count=len(critical_alerts), penalty=_penalty(len(critical_alerts), 18, 36), cap=36),
        ControlCenterBreakdownItem(key="warning_alerts", label="Alertas warning/altas", count=len(warning_alerts), penalty=_penalty(len(warning_alerts), 8, 24), cap=24),
        ControlCenterBreakdownItem(key="hours_out_of_range", label="Horas fuera de rango", count=hours_out_of_range, penalty=_penalty(hours_out_of_range, 1.5, 20), cap=20),
        ControlCenterBreakdownItem(key="offline_devices", label="Dispositivos offline", count=offline_devices, penalty=_penalty(offline_devices, 10, 30), cap=30),
        ControlCenterBreakdownItem(key="stale_readings", label="Lecturas atrasadas", count=stale_readings, penalty=_penalty(stale_readings, 6, 18), cap=18),
        ControlCenterBreakdownItem(key="low_battery", label="Bateria baja", count=low_battery, penalty=_penalty(low_battery, 5, 15), cap=15),
        ControlCenterBreakdownItem(key="maintenance_overdue", label="Mantenimientos vencidos", count=maintenance_overdue, penalty=_penalty(maintenance_overdue, 8, 24), cap=24),
    ]
    score = max(0, min(100, round(100 - sum(item.penalty for item in breakdown))))

    priorities = [
        ControlCenterPriorityOut(
            type="alert",
            severity=alert.severity,
            title=alert.alert_type,
            detail=alert.message,
            storage_unit_id=alert.storage_unit_id,
            alert_id=alert.id,
        )
        for alert in active_alerts[:6]
    ]

    sites: list[ControlCenterSiteOut] = []
    for site in db.scalars(select(Site).where(Site.id.in_({unit.site_id for unit in storage_units}))).all():
        site_unit_ids = [unit.id for unit in storage_units if unit.site_id == site.id]
        site_alerts = [alert for alert in active_alerts if alert.storage_unit_id in site_unit_ids]
        site_score = max(0, 100 - min(len(site_alerts) * 12, 48))
        sites.append(
            ControlCenterSiteOut(
                site_id=site.id,
                site_name=site.name,
                status=_score_status(site_score, bool(site_unit_ids)),
                score=site_score,
                storage_units=len(site_unit_ids),
                active_alerts=len(site_alerts),
            )
        )

    recent_logs = list(
        db.scalars(
            select(OperationalLog)
            .where(OperationalLog.storage_unit_id.in_(unit_ids))
            .order_by(OperationalLog.timestamp.desc())
            .limit(8)
        ).all()
    )

    return ControlCenterSummaryOut(
        generated_at=now,
        score=score,
        status=_score_status(score, readings_24h > 0),
        formula_version=FORMULA_VERSION,
        breakdown=breakdown,
        kpis={
            "storage_units": len(storage_units),
            "devices": len(devices),
            "active_alerts": len(active_alerts),
            "critical_alerts": len(critical_alerts),
            "readings_24h": readings_24h,
            "resolved_alerts": resolved_alerts,
            "logs": logs_count,
        },
        priorities=priorities,
        sites=sites,
        device_health=device_health,
        recent_alerts=[AlertOut.model_validate(alert) for alert in active_alerts[:8]],
        recent_activity=[OperationalLogOut.model_validate(log) for log in recent_logs],
    )
