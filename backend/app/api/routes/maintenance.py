from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_device_access, require_role
from app.db.session import get_db
from app.models import MaintenanceEvent, MaintenanceRecord, ServiceCase, User, utc_now
from app.schemas import (
    DeviceMaintenanceSummaryOut,
    MaintenanceCancelIn,
    MaintenanceCompleteIn,
    MaintenanceCreate,
    MaintenanceEventOut,
    MaintenanceOut,
    MaintenanceStartIn,
    MaintenanceUpdate,
)
from app.services.audit import record_audit_event
from app.services.maintenance import (
    FINAL_STATUSES,
    append_maintenance_event,
    complete_maintenance,
    device_maintenance_summary,
    list_maintenance_records,
    maintenance_out,
    require_maintenance_access,
)

router = APIRouter(prefix="/maintenance", dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[MaintenanceOut])
def list_maintenance(
    device_id: int | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MaintenanceOut]:
    return [
        maintenance_out(item, current_user)
        for item in list_maintenance_records(
            db,
            current_user,
            device_id=device_id,
            status_filter=status_filter,
        )
    ]


@router.post("", response_model=MaintenanceOut, status_code=status.HTTP_201_CREATED)
def create_maintenance(
    payload: MaintenanceCreate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> MaintenanceOut:
    device = require_device_access(db, current_user, payload.device_id)
    if payload.technician_id is not None:
        _require_assigned_technician(db, device.storage_unit_id, payload.technician_id)
    if payload.service_case_id is not None:
        service_case = db.get(ServiceCase, payload.service_case_id)
        if (
            service_case is None
            or service_case.storage_unit_id != device.storage_unit_id
            or (service_case.device_id is not None and service_case.device_id != device.id)
        ):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Caso de servicio incompatible.")
    record = MaintenanceRecord(
        company_id=device.company_id,
        storage_unit_id=device.storage_unit_id,
        device_id=device.id,
        service_case_id=payload.service_case_id,
        maintenance_type=payload.maintenance_type,
        status="ASSIGNED" if payload.technician_id else "SCHEDULED",
        priority=payload.priority,
        scheduled_at=payload.scheduled_at,
        technician_id=payload.technician_id,
        created_by_id=current_user.id,
        observations=payload.observations,
        next_maintenance_at=payload.next_maintenance_at,
    )
    db.add(record)
    db.flush()
    append_maintenance_event(
        db,
        record,
        current_user,
        event_type="created",
        note="Mantenimiento programado.",
    )
    record_audit_event(
        db,
        action="maintenance.create",
        summary="Mantenimiento creado",
        user=current_user,
        resource_type="maintenance",
        resource_id=record.id,
        metadata={"device_id": device.id, "technician_id": payload.technician_id},
    )
    db.commit()
    db.refresh(record)
    return maintenance_out(record, current_user)


@router.get("/{maintenance_id}", response_model=MaintenanceOut)
def get_maintenance(
    maintenance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MaintenanceOut:
    return maintenance_out(require_maintenance_access(db, current_user, maintenance_id), current_user)


@router.patch("/{maintenance_id}", response_model=MaintenanceOut)
def update_maintenance(
    maintenance_id: int,
    payload: MaintenanceUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> MaintenanceOut:
    record = require_maintenance_access(db, current_user, maintenance_id)
    if record.status in FINAL_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un mantenimiento finalizado es inmutable. Registra una nueva intervencion.",
        )
    values = payload.model_dump(exclude_unset=True)
    if "technician_id" in values and values["technician_id"] is not None:
        _require_assigned_technician(db, record.storage_unit_id, values["technician_id"])
    previous_status = record.status
    for key, value in values.items():
        setattr(record, key, value)
    if record.technician_id and record.status == "SCHEDULED":
        record.status = "ASSIGNED"
    append_maintenance_event(
        db,
        record,
        current_user,
        event_type="updated",
        note="Programacion de mantenimiento actualizada.",
        previous_status=previous_status,
        metadata=values,
    )
    record_audit_event(
        db,
        action="maintenance.update",
        summary="Mantenimiento actualizado",
        user=current_user,
        resource_type="maintenance",
        resource_id=record.id,
        metadata=values,
    )
    db.commit()
    db.refresh(record)
    return maintenance_out(record, current_user)


@router.post("/{maintenance_id}/start", response_model=MaintenanceOut)
def start_maintenance(
    maintenance_id: int,
    payload: MaintenanceStartIn,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> MaintenanceOut:
    record = require_maintenance_access(db, current_user, maintenance_id)
    if record.status in FINAL_STATUSES or record.status == "IN_PROGRESS":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El mantenimiento no puede iniciarse.")
    if record.technician_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Asigna un tecnico antes de iniciar.")
    previous_status = record.status
    record.status = "IN_PROGRESS"
    record.started_at = record.started_at or utc_now()
    append_maintenance_event(
        db,
        record,
        current_user,
        event_type="started",
        note=payload.note,
        previous_status=previous_status,
    )
    record_audit_event(
        db,
        action="maintenance.start",
        summary="Mantenimiento iniciado",
        user=current_user,
        resource_type="maintenance",
        resource_id=record.id,
    )
    db.commit()
    db.refresh(record)
    return maintenance_out(record, current_user)


@router.post("/{maintenance_id}/complete", response_model=MaintenanceOut)
def finish_maintenance(
    maintenance_id: int,
    payload: MaintenanceCompleteIn,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> MaintenanceOut:
    record = require_maintenance_access(db, current_user, maintenance_id)
    complete_maintenance(db, record, current_user, payload)
    db.commit()
    db.refresh(record)
    return maintenance_out(record, current_user)


@router.post("/{maintenance_id}/cancel", response_model=MaintenanceOut)
def cancel_maintenance(
    maintenance_id: int,
    payload: MaintenanceCancelIn,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> MaintenanceOut:
    record = require_maintenance_access(db, current_user, maintenance_id)
    if record.status in FINAL_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El mantenimiento ya esta finalizado.")
    previous_status = record.status
    record.status = "CANCELLED"
    record.cancelled_at = utc_now()
    append_maintenance_event(
        db,
        record,
        current_user,
        event_type="cancelled",
        note=payload.reason,
        previous_status=previous_status,
    )
    record_audit_event(
        db,
        action="maintenance.cancel",
        summary="Mantenimiento cancelado",
        user=current_user,
        resource_type="maintenance",
        resource_id=record.id,
    )
    db.commit()
    db.refresh(record)
    return maintenance_out(record, current_user)


@router.get("/{maintenance_id}/events", response_model=list[MaintenanceEventOut])
def maintenance_events(
    maintenance_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MaintenanceEvent]:
    require_maintenance_access(db, current_user, maintenance_id)
    return list(
        db.scalars(
            select(MaintenanceEvent)
            .where(MaintenanceEvent.maintenance_id == maintenance_id)
            .order_by(MaintenanceEvent.created_at)
        ).all()
    )


@router.get("/device/{device_id}/summary", response_model=DeviceMaintenanceSummaryOut)
def maintenance_summary(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceMaintenanceSummaryOut:
    device = require_device_access(db, current_user, device_id)
    return DeviceMaintenanceSummaryOut(**device_maintenance_summary(db, device))


def _require_assigned_technician(db: Session, storage_unit_id: int, technician_id: int) -> User:
    from app.models import StorageUnit

    technician = db.get(User, technician_id)
    unit = db.get(StorageUnit, storage_unit_id)
    if technician is None or technician.role != "technician" or not technician.is_active:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Tecnico invalido.")
    if unit is None or unit.assigned_technician_id != technician.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El tecnico debe estar asignado al silo o campo.",
        )
    return technician
