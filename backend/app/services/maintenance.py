from __future__ import annotations

import json
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import assigned_storage_unit_ids, require_device_access, require_storage_unit_access
from app.models import (
    Device,
    FirmwareUpdateRecord,
    MaintenanceEvent,
    MaintenanceRecord,
    OperationalLog,
    SensorCalibration,
    StoredFile,
    User,
    utc_now,
)
from app.schemas import MaintenanceCompleteIn, MaintenanceOut
from app.services.audit import record_audit_event


FINAL_STATUSES = {"COMPLETED", "CANCELLED"}
OPEN_STATUSES = {"SCHEDULED", "ASSIGNED", "IN_PROGRESS", "WAITING_PARTS"}


def effective_maintenance_status(record: MaintenanceRecord, now: datetime | None = None) -> str:
    now = now or utc_now()
    if (
        record.status in {"SCHEDULED", "ASSIGNED"}
        and record.scheduled_at is not None
        and _aware(record.scheduled_at) < now
    ):
        return "OVERDUE"
    return record.status


def list_maintenance_records(
    db: Session,
    user: User,
    *,
    device_id: int | None = None,
    status_filter: str | None = None,
) -> list[MaintenanceRecord]:
    stmt = select(MaintenanceRecord).order_by(MaintenanceRecord.created_at.desc())
    if user.role == "technician":
        stmt = stmt.where(MaintenanceRecord.technician_id == user.id)
    elif user.role == "client":
        unit_ids = assigned_storage_unit_ids(db, user)
        stmt = stmt.where(MaintenanceRecord.storage_unit_id.in_(unit_ids or [-1]))
    if device_id is not None:
        require_device_access(db, user, device_id)
        stmt = stmt.where(MaintenanceRecord.device_id == device_id)
    records = list(db.scalars(stmt).all())
    if status_filter:
        normalized = status_filter.upper()
        records = [record for record in records if effective_maintenance_status(record) == normalized]
    return records


def require_maintenance_access(db: Session, user: User, maintenance_id: int) -> MaintenanceRecord:
    record = db.get(MaintenanceRecord, maintenance_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mantenimiento no encontrado.")
    require_storage_unit_access(db, user, record.storage_unit_id)
    if user.role == "technician" and record.technician_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mantenimiento no asignado al tecnico.")
    return record


def maintenance_out(record: MaintenanceRecord, user: User) -> MaintenanceOut:
    parts = _json_list(record.parts_replaced_json)
    diagnosis = record.diagnosis
    observations = record.observations
    if user.role == "client":
        diagnosis = None
        parts = []
        if record.status != "COMPLETED":
            observations = None
    return MaintenanceOut(
        id=record.id,
        company_id=record.company_id,
        storage_unit_id=record.storage_unit_id,
        device_id=record.device_id,
        service_case_id=record.service_case_id,
        parent_maintenance_id=record.parent_maintenance_id,
        maintenance_type=record.maintenance_type,
        status=record.status,
        effective_status=effective_maintenance_status(record),
        priority=record.priority,
        scheduled_at=record.scheduled_at,
        started_at=record.started_at,
        completed_at=record.completed_at,
        cancelled_at=record.cancelled_at,
        technician_id=record.technician_id,
        created_by_id=record.created_by_id,
        observations=observations,
        diagnosis=diagnosis,
        action_taken=record.action_taken if record.status == "COMPLETED" else None,
        device_status_after=record.device_status_after,
        parts_replaced=parts,
        battery_replaced=record.battery_replaced,
        sensor_replaced=record.sensor_replaced,
        calibration_required=record.calibration_required,
        firmware_updated=record.firmware_updated,
        previous_firmware_version=record.previous_firmware_version,
        new_firmware_version=record.new_firmware_version,
        evidence_count=record.evidence_count,
        next_maintenance_at=record.next_maintenance_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def append_maintenance_event(
    db: Session,
    record: MaintenanceRecord,
    user: User,
    *,
    event_type: str,
    note: str,
    previous_status: str | None = None,
    metadata: dict | None = None,
) -> MaintenanceEvent:
    event = MaintenanceEvent(
        maintenance_id=record.id,
        user_id=user.id,
        event_type=event_type,
        previous_status=previous_status,
        new_status=record.status,
        note=note,
        metadata_json=json.dumps(metadata, ensure_ascii=True, default=str) if metadata else None,
    )
    db.add(event)
    return event


def complete_maintenance(
    db: Session,
    record: MaintenanceRecord,
    user: User,
    payload: MaintenanceCompleteIn,
) -> MaintenanceRecord:
    if record.status in FINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un mantenimiento finalizado es inmutable. Registra una nueva intervencion.",
        )
    if record.technician_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Asigna un tecnico antes de completar.")
    if user.role == "technician" and record.technician_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Mantenimiento no asignado al tecnico.")
    if payload.firmware_updated and not payload.new_firmware_version:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Registra la nueva version de firmware.",
        )

    previous_status = record.status
    device = db.get(Device, record.device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispositivo no encontrado.")

    record.status = "COMPLETED"
    record.completed_at = utc_now()
    record.observations = payload.observations
    record.diagnosis = payload.diagnosis
    record.action_taken = payload.action_taken
    record.device_status_after = payload.device_status_after
    record.parts_replaced_json = json.dumps(payload.parts_replaced, ensure_ascii=True)
    record.battery_replaced = payload.battery_replaced
    record.sensor_replaced = payload.sensor_replaced
    record.calibration_required = payload.calibration_required
    record.firmware_updated = payload.firmware_updated
    record.previous_firmware_version = payload.previous_firmware_version
    record.new_firmware_version = payload.new_firmware_version
    record.next_maintenance_at = payload.next_maintenance_at
    device.operational_status = payload.device_status_after

    if payload.firmware_updated and payload.new_firmware_version:
        db.add(
            FirmwareUpdateRecord(
                company_id=record.company_id,
                storage_unit_id=record.storage_unit_id,
                device_id=record.device_id,
                maintenance_id=record.id,
                previous_version=payload.previous_firmware_version,
                new_version=payload.new_firmware_version,
                result="SUCCESS",
                notes="Actualizacion registrada al completar mantenimiento.",
                recorded_by_id=user.id,
            )
        )
        iot_device = device_iot_record(db, device.id)
        if iot_device is not None:
            iot_device.firmware_version = payload.new_firmware_version

    if payload.sensor_replaced and payload.calibration_required:
        device.operational_status = "calibration_pending"
        calibration_task = MaintenanceRecord(
            company_id=record.company_id,
            storage_unit_id=record.storage_unit_id,
            device_id=record.device_id,
            parent_maintenance_id=record.id,
            maintenance_type="CALIBRATION",
            status="ASSIGNED",
            priority="HIGH",
            scheduled_at=payload.next_maintenance_at or utc_now(),
            technician_id=record.technician_id,
            created_by_id=user.id,
            observations="Calibracion requerida despues del reemplazo de sensor.",
        )
        db.add(calibration_task)

    db.add(
        OperationalLog(
            company_id=record.company_id,
            site_id=device.site_id,
            storage_unit_id=record.storage_unit_id,
            device_id=record.device_id,
            user_id=user.id,
            category="maintenance",
            action_taken=f"Mantenimiento {record.maintenance_type.lower()} completado",
            operator_name=user.full_name,
            notes=payload.action_taken,
            timestamp=record.completed_at,
        )
    )
    append_maintenance_event(
        db,
        record,
        user,
        event_type="completed",
        note="Mantenimiento completado con evidencia operativa.",
        previous_status=previous_status,
        metadata={
            "battery_replaced": payload.battery_replaced,
            "sensor_replaced": payload.sensor_replaced,
            "firmware_updated": payload.firmware_updated,
            "device_status_after": device.operational_status,
        },
    )
    record_audit_event(
        db,
        action="maintenance.complete",
        summary="Mantenimiento completado",
        user=user,
        resource_type="maintenance",
        resource_id=record.id,
        metadata={"device_id": record.device_id, "status_after": device.operational_status},
    )
    return record


def device_maintenance_summary(db: Session, device: Device) -> dict:
    records = list(
        db.scalars(
            select(MaintenanceRecord)
            .where(MaintenanceRecord.device_id == device.id)
            .order_by(MaintenanceRecord.created_at.desc())
        ).all()
    )
    completed = [item for item in records if item.status == "COMPLETED"]
    pending = [item for item in records if item.status not in FINAL_STATUSES]
    overdue = [item for item in pending if effective_maintenance_status(item) == "OVERDUE"]

    def last_completed(kind: str) -> datetime | None:
        match = next((item for item in completed if item.maintenance_type == kind), None)
        return match.completed_at if match else None

    active_calibration = db.scalar(
        select(SensorCalibration)
        .where(SensorCalibration.device_id == device.id, SensorCalibration.is_active.is_(True))
        .order_by(SensorCalibration.calibrated_at.desc())
    )
    next_review = min(
        (item.next_maintenance_at for item in records if item.next_maintenance_at is not None),
        default=None,
    )
    latest = completed[0] if completed else None
    return {
        "device_id": device.id,
        "last_intervention_at": latest.completed_at if latest else None,
        "next_review_at": next_review,
        "pending_count": len(pending),
        "overdue_count": len(overdue),
        "last_battery_change_at": last_completed("BATTERY_CHANGE"),
        "last_sensor_change_at": last_completed("SENSOR_REPLACEMENT"),
        "last_calibration_at": active_calibration.calibrated_at if active_calibration else None,
        "firmware_version": latest.new_firmware_version if latest and latest.firmware_updated else None,
        "technician_id": latest.technician_id if latest else None,
        "operational_status": device.operational_status,
    }


def refresh_evidence_count(db: Session, record: MaintenanceRecord) -> None:
    record.evidence_count = db.scalar(
        select(func.count(StoredFile.id)).where(
            StoredFile.entity_type == "maintenance",
            StoredFile.entity_id == record.id,
            StoredFile.deleted_at.is_(None),
        )
    ) or 0


def device_iot_record(db: Session, device_id: int):
    from app.models import IotDevice

    return db.scalar(select(IotDevice).where(IotDevice.device_id == device_id))


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=utc_now().tzinfo)
