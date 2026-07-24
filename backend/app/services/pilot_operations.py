from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import mean

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import assigned_storage_unit_ids
from app.models import (
    Alert,
    Device,
    IotDevice,
    IotGateway,
    IotIngestionEvent,
    MaintenanceRecord,
    NotificationDelivery,
    OperationalLog,
    SensorMetricValue,
    SensorReading,
    ServiceCase,
    StorageUnit,
    User,
    utc_now,
)
from app.schemas import GatewayOut, PilotMetricsOut, SystemHealthOut

GATEWAY_ONLINE_AFTER = timedelta(minutes=5)
GATEWAY_DELAYED_AFTER = timedelta(minutes=30)
DEVICE_ONLINE_MULTIPLIER = 2
DEVICE_DELAYED_MULTIPLIER = 6


def gateway_effective_status(gateway: IotGateway, now: datetime | None = None) -> str:
    now = now or utc_now()
    explicit = (gateway.status or "UNKNOWN").upper()
    if explicit == "MAINTENANCE":
        return "MAINTENANCE"
    if not gateway.is_active:
        return "OFFLINE"
    if gateway.last_seen_at is None:
        return "UNKNOWN"
    age = now - _aware(gateway.last_seen_at)
    if age > GATEWAY_DELAYED_AFTER:
        return "OFFLINE"
    if (
        explicit == "DEGRADED"
        or gateway.internet_status.lower() in {"offline", "degraded"}
        or gateway.last_error_at is not None
        and now - _aware(gateway.last_error_at) <= GATEWAY_DELAYED_AFTER
    ):
        return "DEGRADED"
    if age > GATEWAY_ONLINE_AFTER:
        return "DELAYED"
    return "ONLINE"


def gateway_to_out(gateway: IotGateway, now: datetime | None = None) -> GatewayOut:
    return GatewayOut(
        id=gateway.id,
        company_id=gateway.company_id,
        site_id=gateway.site_id,
        storage_unit_id=gateway.storage_unit_id,
        gateway_id=gateway.gateway_id,
        name=gateway.name,
        status=gateway.status,
        effective_status=gateway_effective_status(gateway, now),
        firmware_version=gateway.firmware_version,
        internet_status=gateway.internet_status,
        local_queue_size=gateway.local_queue_size,
        associated_devices_count=gateway.associated_devices_count,
        restart_count=gateway.restart_count,
        last_restart_reason=gateway.last_restart_reason,
        last_error_code=gateway.last_error_code,
        last_error_at=gateway.last_error_at,
        last_seen_at=gateway.last_seen_at,
        is_active=gateway.is_active,
    )


def scoped_gateway_query(db: Session, user: User):
    stmt = select(IotGateway)
    if user.role == "admin":
        return stmt
    unit_ids = assigned_storage_unit_ids(db, user)
    if not unit_ids:
        return stmt.where(IotGateway.id == -1)
    device_gateway_ids = select(IotDevice.gateway_id).join(Device, Device.id == IotDevice.device_id).where(
        Device.storage_unit_id.in_(unit_ids),
        IotDevice.gateway_id.is_not(None),
    )
    return stmt.where(
        (IotGateway.storage_unit_id.in_(unit_ids)) | (IotGateway.id.in_(device_gateway_ids))
    )


def build_system_health(db: Session, user: User) -> SystemHealthOut:
    now = utc_now()
    unit_ids = _scoped_unit_ids(db, user)
    devices = _devices(db, unit_ids)
    device_ids = [item.id for item in devices]
    gateways = list(db.scalars(scoped_gateway_query(db, user)).all())
    gateway_states = defaultdict(int)
    for gateway in gateways:
        gateway_states[gateway_effective_status(gateway, now).lower()] += 1

    device_states = defaultdict(int)
    for device in devices:
        device_states[_device_status(device, now).lower()] += 1

    day_ago = now - timedelta(hours=24)
    readings_24h = _count(
        db,
        select(func.count(SensorReading.id)).where(
            SensorReading.device_id.in_(device_ids) if device_ids else SensorReading.id == -1,
            SensorReading.timestamp >= day_ago,
        ),
    )
    rejected_24h = _count(
        db,
        select(func.count(IotIngestionEvent.id))
        .join(IotDevice, IotDevice.id == IotIngestionEvent.iot_device_id, isouter=True)
        .join(Device, Device.id == IotDevice.device_id, isouter=True)
        .where(
            Device.storage_unit_id.in_(unit_ids) if unit_ids else IotIngestionEvent.id == -1,
            IotIngestionEvent.created_at >= day_ago,
            IotIngestionEvent.status.like("rejected%"),
        ),
    )
    active_alerts = _count(
        db,
        select(func.count(Alert.id)).where(
            Alert.storage_unit_id.in_(unit_ids) if unit_ids else Alert.id == -1,
            Alert.is_active.is_(True),
        ),
    )
    alert_rows = list(
        db.scalars(
            select(Alert).where(
                Alert.storage_unit_id.in_(unit_ids) if unit_ids else Alert.id == -1,
                Alert.created_at >= day_ago,
            )
        ).all()
    )
    ack_minutes = [
        (_aware(item.acknowledged_at) - _aware(item.created_at)).total_seconds() / 60
        for item in alert_rows
        if item.acknowledged_at is not None
    ]
    resolution_minutes = [
        (_aware(item.resolved_at) - _aware(item.created_at)).total_seconds() / 60
        for item in alert_rows
        if item.resolved_at is not None
    ]
    notification_counts = _notification_counts(db, unit_ids, user)

    return SystemHealthOut(
        generated_at=now,
        backend={"status": "ok"},
        database={"status": "ok"},
        gateways={"total": len(gateways), **dict(gateway_states)},
        devices={"total": len(devices), **dict(device_states)},
        data={"readings_24h": readings_24h, "rejected_24h": rejected_24h},
        alerts={
            "active": active_alerts,
            "mean_acknowledgement_minutes_24h": round(mean(ack_minutes), 2) if ack_minutes else None,
            "mean_resolution_minutes_24h": round(mean(resolution_minutes), 2) if resolution_minutes else None,
        },
        notifications=notification_counts,
    )


def build_pilot_metrics(
    db: Session,
    user: User,
    *,
    date_from: datetime,
    date_to: datetime,
    company_id: int | None = None,
    storage_unit_id: int | None = None,
) -> PilotMetricsOut:
    unit_ids = _scoped_unit_ids(db, user, company_id=company_id, storage_unit_id=storage_unit_id)
    devices = _devices(db, unit_ids)
    device_ids = [item.id for item in devices]
    reading_rows = list(
        db.scalars(
            select(SensorReading)
            .where(
                SensorReading.device_id.in_(device_ids) if device_ids else SensorReading.id == -1,
                SensorReading.timestamp >= date_from,
                SensorReading.timestamp <= date_to,
            )
            .order_by(SensorReading.device_id, SensorReading.timestamp)
        ).all()
    )
    expected = 0
    expected_configured = True
    duration_minutes = max(0.0, (_aware(date_to) - _aware(date_from)).total_seconds() / 60)
    for device in devices:
        interval = device.expected_reading_interval_minutes
        if not interval:
            expected_configured = False
            continue
        expected += int(duration_minutes // interval) + 1

    valid = sum(1 for row in reading_rows if row.sensor_status in {None, 0})
    received = len(reading_rows)
    coverage = (
        round(min(received / expected * 100, 100), 2)
        if expected_configured and expected > 0
        else None
    )
    availability = _estimate_device_availability(devices, reading_rows, date_from, date_to)

    alerts = list(
        db.scalars(
            select(Alert).where(
                Alert.storage_unit_id.in_(unit_ids) if unit_ids else Alert.id == -1,
                Alert.created_at >= date_from,
                Alert.created_at <= date_to,
            )
        ).all()
    )
    ack_minutes = [
        (_aware(row.acknowledged_at) - _aware(row.created_at)).total_seconds() / 60
        for row in alerts
        if row.acknowledged_at
    ]
    resolution_minutes = [
        (_aware(row.resolved_at) - _aware(row.created_at)).total_seconds() / 60
        for row in alerts
        if row.resolved_at
    ]
    incident_count = _count(
        db,
        select(func.count(ServiceCase.id)).where(
            ServiceCase.storage_unit_id.in_(unit_ids) if unit_ids else ServiceCase.id == -1,
            ServiceCase.created_at >= date_from,
            ServiceCase.created_at <= date_to,
        ),
    )
    action_count = _count(
        db,
        select(func.count(OperationalLog.id)).where(
            OperationalLog.storage_unit_id.in_(unit_ids) if unit_ids else OperationalLog.id == -1,
            OperationalLog.timestamp >= date_from,
            OperationalLog.timestamp <= date_to,
        ),
    )
    maintenance_rows = list(
        db.scalars(
            select(MaintenanceRecord).where(
                MaintenanceRecord.storage_unit_id.in_(unit_ids) if unit_ids else MaintenanceRecord.id == -1,
                MaintenanceRecord.created_at <= date_to,
                (MaintenanceRecord.completed_at.is_(None)) | (MaintenanceRecord.completed_at >= date_from),
            )
        ).all()
    )
    completed_durations = [
        (_aware(row.completed_at) - _aware(row.created_at)).total_seconds() / 3600
        for row in maintenance_rows
        if row.completed_at is not None
    ]
    overdue = sum(
        1
        for row in maintenance_rows
        if row.status not in {"COMPLETED", "CANCELLED"}
        and row.scheduled_at is not None
        and _aware(row.scheduled_at) < _aware(date_to)
    )
    rejected, duplicates = _ingestion_quality(db, unit_ids, date_from, date_to)
    uncalibrated = _count(
        db,
        select(func.count(SensorMetricValue.id))
        .join(SensorReading, SensorReading.id == SensorMetricValue.sensor_reading_id)
        .where(
            SensorReading.storage_unit_id.in_(unit_ids) if unit_ids else SensorMetricValue.id == -1,
            SensorReading.timestamp >= date_from,
            SensorReading.timestamp <= date_to,
            SensorMetricValue.quality_status.in_(["raw", "legacy_unversioned", "uncalibrated"]),
        ),
    )
    sensor_faults = sum(1 for row in reading_rows if row.sensor_status not in {None, 0})

    return PilotMetricsOut(
        generated_at=utc_now(),
        company_id=company_id,
        storage_unit_id=storage_unit_id,
        period_from=date_from,
        period_to=date_to,
        data_availability={
            "expected_readings": expected if expected_configured else None,
            "received_readings": received,
            "valid_readings": valid,
            "coverage_percent": coverage,
            "cadence_configured": expected_configured,
        },
        device_availability=availability,
        operations={
            "alerts": len(alerts),
            "critical_alerts": sum(1 for row in alerts if row.severity == "critical"),
            "incidents": incident_count,
            "mean_acknowledgement_minutes": round(mean(ack_minutes), 2) if ack_minutes else None,
            "mean_resolution_minutes": round(mean(resolution_minutes), 2) if resolution_minutes else None,
            "actions": action_count,
        },
        maintenance={
            "interventions": len(maintenance_rows),
            "overdue": overdue,
            "mean_close_hours": round(mean(completed_durations), 2) if completed_durations else None,
            "pending_devices": len({row.device_id for row in maintenance_rows if row.status not in {"COMPLETED", "CANCELLED"}}),
        },
        quality={
            "rejected_readings": rejected,
            "uncalibrated_metrics": uncalibrated,
            "sensor_faults": sensor_faults,
            "duplicates": duplicates,
            "time_errors": 0,
        },
    )


def _scoped_unit_ids(
    db: Session,
    user: User,
    *,
    company_id: int | None = None,
    storage_unit_id: int | None = None,
) -> list[int]:
    allowed = assigned_storage_unit_ids(db, user)
    if user.role == "admin":
        stmt = select(StorageUnit.id)
    elif not allowed:
        return []
    else:
        stmt = select(StorageUnit.id).where(StorageUnit.id.in_(allowed))
    if company_id is not None:
        stmt = stmt.where(StorageUnit.company_id == company_id)
    if storage_unit_id is not None:
        stmt = stmt.where(StorageUnit.id == storage_unit_id)
    return list(db.scalars(stmt).all())


def _devices(db: Session, unit_ids: list[int]) -> list[Device]:
    if not unit_ids:
        return []
    return list(db.scalars(select(Device).where(Device.storage_unit_id.in_(unit_ids))).all())


def _device_status(device: Device, now: datetime) -> str:
    if not device.is_active:
        return "OFFLINE"
    if device.operational_status in {"degraded", "calibration_pending"}:
        return "DEGRADED"
    if device.last_seen_at is None:
        return "UNKNOWN"
    interval = device.expected_reading_interval_minutes
    if not interval:
        return "ONLINE"
    age_minutes = (now - _aware(device.last_seen_at)).total_seconds() / 60
    if age_minutes > interval * DEVICE_DELAYED_MULTIPLIER:
        return "OFFLINE"
    if age_minutes > interval * DEVICE_ONLINE_MULTIPLIER:
        return "DELAYED"
    return "ONLINE"


def _estimate_device_availability(
    devices: list[Device],
    readings: list[SensorReading],
    date_from: datetime,
    date_to: datetime,
) -> dict[str, int | float | None]:
    by_device: dict[int, list[SensorReading]] = defaultdict(list)
    for reading in readings:
        by_device[reading.device_id].append(reading)
    online = delayed = offline = 0.0
    configured = 0
    for device in devices:
        interval = device.expected_reading_interval_minutes
        if not interval:
            continue
        configured += 1
        points = [_aware(date_from)] + [_aware(item.timestamp) for item in by_device[device.id]] + [_aware(date_to)]
        for previous, current in zip(points, points[1:]):
            gap = max(0.0, (current - previous).total_seconds() / 60)
            online += min(gap, interval * DEVICE_ONLINE_MULTIPLIER)
            if gap > interval * DEVICE_ONLINE_MULTIPLIER:
                delayed += min(gap - interval * DEVICE_ONLINE_MULTIPLIER, interval * 4)
            if gap > interval * DEVICE_DELAYED_MULTIPLIER:
                offline += gap - interval * DEVICE_DELAYED_MULTIPLIER
    total = online + delayed + offline
    return {
        "configured_devices": configured,
        "total_devices": len(devices),
        "estimated_online_minutes": round(online, 2) if configured else None,
        "estimated_delayed_minutes": round(delayed, 2) if configured else None,
        "estimated_offline_minutes": round(offline, 2) if configured else None,
        "estimated_online_percent": round(online / total * 100, 2) if total else None,
        "method": "sampling_gap_estimate" if configured else "not_calculable_without_cadence",
    }


def _notification_counts(db: Session, unit_ids: list[int], user: User) -> dict[str, int]:
    stmt = select(NotificationDelivery.status, func.count(NotificationDelivery.id)).group_by(
        NotificationDelivery.status
    )
    if user.role != "admin":
        stmt = stmt.where(NotificationDelivery.company_id == user.company_id)
    rows = db.execute(stmt).all()
    result = {str(status).lower(): int(count) for status, count in rows}
    result["total"] = sum(result.values())
    return result


def _ingestion_quality(
    db: Session,
    unit_ids: list[int],
    date_from: datetime,
    date_to: datetime,
) -> tuple[int, int]:
    if not unit_ids:
        return 0, 0
    rows = db.execute(
        select(IotIngestionEvent.status, func.count(IotIngestionEvent.id))
        .join(IotDevice, IotDevice.id == IotIngestionEvent.iot_device_id, isouter=True)
        .join(Device, Device.id == IotDevice.device_id, isouter=True)
        .where(
            Device.storage_unit_id.in_(unit_ids),
            IotIngestionEvent.created_at >= date_from,
            IotIngestionEvent.created_at <= date_to,
        )
        .group_by(IotIngestionEvent.status)
    ).all()
    rejected = sum(int(count) for status, count in rows if str(status).startswith("rejected"))
    duplicates = sum(int(count) for status, count in rows if status == "duplicate")
    return rejected, duplicates


def _count(db: Session, stmt) -> int:
    return int(db.scalar(stmt) or 0)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
