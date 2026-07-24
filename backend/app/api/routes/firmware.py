from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_device_access, require_role, scope_storage_unit_records_query
from app.db.session import get_db
from app.models import (
    Device,
    FirmwareRelease,
    FirmwareUpdateRecord,
    IotDevice,
    MaintenanceRecord,
    OperationalLog,
    User,
    utc_now,
)
from app.schemas import (
    DeviceFirmwareStatusOut,
    FirmwareReleaseCreate,
    FirmwareReleaseOut,
    FirmwareReleaseUpdate,
    FirmwareUpdateRecordIn,
    FirmwareUpdateRecordOut,
)
from app.services.audit import record_audit_event
from app.services.maintenance import require_maintenance_access
router = APIRouter(prefix="/firmware", dependencies=[Depends(get_current_user)])
device_router = APIRouter(prefix="/devices", dependencies=[Depends(get_current_user)])
VALID_RELEASE_TRANSITIONS = {
    "DRAFT": {"DRAFT", "TESTING", "REVOKED"},
    "TESTING": {"TESTING", "RELEASED", "DRAFT", "REVOKED"},
    "RELEASED": {"RELEASED", "DEPRECATED", "REVOKED"},
    "DEPRECATED": {"DEPRECATED", "REVOKED"},
    "REVOKED": {"REVOKED"},
}


@router.get("/releases", response_model=list[FirmwareReleaseOut])
def list_firmware_releases(
    device_type: str | None = None,
    _: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> list[FirmwareRelease]:
    stmt = select(FirmwareRelease)
    if device_type:
        stmt = stmt.where(FirmwareRelease.device_type == _canonical_device_type(device_type))
    return list(db.scalars(stmt.order_by(FirmwareRelease.device_type, FirmwareRelease.created_at.desc())).all())


@router.post("/releases", response_model=FirmwareReleaseOut, status_code=status.HTTP_201_CREATED)
def create_firmware_release(
    payload: FirmwareReleaseCreate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> FirmwareRelease:
    device_type = _canonical_device_type(payload.device_type)
    if db.scalar(
        select(FirmwareRelease).where(
            FirmwareRelease.device_type == device_type,
            FirmwareRelease.version == payload.version,
        )
    ):
        raise HTTPException(status_code=409, detail="La version ya existe para este tipo de nodo.")
    _validate_checksum(payload.checksum)
    release = FirmwareRelease(
        **payload.model_dump(exclude={"device_type"}),
        device_type=device_type,
        created_by_id=current_user.id,
    )
    if release.status == "RELEASED" and release.released_at is None:
        release.released_at = utc_now()
    db.add(release)
    db.flush()
    if release.is_recommended:
        _clear_recommended(db, device_type, except_id=release.id)
    record_audit_event(
        db,
        action="firmware.release.create",
        summary=f"Version de firmware {release.version} registrada.",
        user=current_user,
        resource_type="firmware_release",
        resource_id=release.id,
        metadata={"device_type": device_type, "status": release.status},
    )
    db.commit()
    db.refresh(release)
    return release


@router.patch("/releases/{release_id}", response_model=FirmwareReleaseOut)
def update_firmware_release(
    release_id: int,
    payload: FirmwareReleaseUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> FirmwareRelease:
    release = db.get(FirmwareRelease, release_id)
    if release is None:
        raise HTTPException(status_code=404, detail="Version de firmware no encontrada.")
    values = payload.model_dump(exclude_unset=True)
    next_status = values.get("status", release.status)
    if next_status not in VALID_RELEASE_TRANSITIONS.get(release.status, {release.status}):
        raise HTTPException(status_code=409, detail=f"Transicion no permitida: {release.status} a {next_status}.")
    _validate_checksum(values.get("checksum"))
    for key, value in values.items():
        setattr(release, key, value)
    if release.status == "RELEASED" and release.released_at is None:
        release.released_at = utc_now()
    if release.is_recommended:
        if release.status != "RELEASED":
            raise HTTPException(status_code=422, detail="Solo una version RELEASED puede ser recomendada.")
        _clear_recommended(db, release.device_type, except_id=release.id)
    record_audit_event(
        db,
        action="firmware.release.update",
        summary=f"Version de firmware {release.version} actualizada.",
        user=current_user,
        resource_type="firmware_release",
        resource_id=release.id,
        metadata={"changes": values},
    )
    db.commit()
    db.refresh(release)
    return release


@router.get("/devices/status", response_model=list[DeviceFirmwareStatusOut])
def list_device_firmware_status(
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> list[DeviceFirmwareStatusOut]:
    devices = list(
        db.scalars(
            scope_storage_unit_records_query(select(Device), Device, current_user, db).order_by(Device.external_id)
        ).all()
    )
    return [_device_status(db, device) for device in devices]


@router.post("/devices/{device_id}/update-record", response_model=FirmwareUpdateRecordOut, status_code=201)
def create_firmware_update_record(
    device_id: int,
    payload: FirmwareUpdateRecordIn,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> FirmwareUpdateRecord:
    device = require_device_access(db, current_user, device_id)
    release = None
    if payload.firmware_release_id is not None:
        release = db.get(FirmwareRelease, payload.firmware_release_id)
        if release is None:
            raise HTTPException(status_code=404, detail="Version de firmware no encontrada.")
        if release.status != "RELEASED":
            raise HTTPException(status_code=422, detail="Solo se puede registrar una version RELEASED.")
        if release.device_type != _canonical_device_type(device.device_type):
            raise HTTPException(status_code=422, detail="La version no corresponde al tipo de nodo.")
        if release.version != payload.new_version:
            raise HTTPException(status_code=422, detail="La version informada no coincide con el release.")
    if payload.maintenance_id is not None:
        maintenance = require_maintenance_access(db, current_user, payload.maintenance_id)
        if maintenance.device_id != device.id:
            raise HTTPException(status_code=422, detail="El mantenimiento no corresponde al nodo.")
    iot_device = db.scalar(select(IotDevice).where(IotDevice.device_id == device.id))
    previous = iot_device.firmware_version if iot_device else None
    record = FirmwareUpdateRecord(
        company_id=device.company_id,
        storage_unit_id=device.storage_unit_id,
        device_id=device.id,
        firmware_release_id=payload.firmware_release_id,
        maintenance_id=payload.maintenance_id,
        previous_version=previous,
        new_version=payload.new_version,
        result=payload.result,
        notes=payload.notes,
        recorded_by_id=current_user.id,
    )
    db.add(record)
    if payload.result == "SUCCESS" and iot_device is not None:
        iot_device.firmware_version = payload.new_version
        iot_device.updated_at = utc_now()
    db.add(
        OperationalLog(
            company_id=device.company_id,
            site_id=device.site_id,
            storage_unit_id=device.storage_unit_id,
            device_id=device.id,
            user_id=current_user.id,
            category="maintenance",
            action_taken="Actualizacion de firmware registrada.",
            operator_name=current_user.full_name,
            notes=f"Resultado: {payload.result}. Version: {payload.new_version}.",
            timestamp=utc_now(),
        )
    )
    db.flush()
    record_audit_event(
        db,
        action="firmware.update.record",
        summary=f"Actualizacion de firmware registrada para {device.external_id}.",
        user=current_user,
        resource_type="firmware_update_record",
        resource_id=record.id,
        metadata={
            "device_id": device.id,
            "previous_version": previous,
            "new_version": payload.new_version,
            "result": payload.result,
        },
    )
    db.commit()
    db.refresh(record)
    return record


@device_router.post("/{device_id}/firmware-update-record", response_model=FirmwareUpdateRecordOut, status_code=201)
def create_firmware_update_record_compat(
    device_id: int,
    payload: FirmwareUpdateRecordIn,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> FirmwareUpdateRecord:
    return create_firmware_update_record(device_id, payload, current_user, db)


def _device_status(db: Session, device: Device) -> DeviceFirmwareStatusOut:
    iot_device = db.scalar(select(IotDevice).where(IotDevice.device_id == device.id))
    current = iot_device.firmware_version if iot_device else None
    canonical = _canonical_device_type(device.device_type)
    recommended = db.scalar(
        select(FirmwareRelease)
        .where(
            FirmwareRelease.device_type == canonical,
            FirmwareRelease.status == "RELEASED",
            FirmwareRelease.is_recommended.is_(True),
        )
        .order_by(FirmwareRelease.released_at.desc())
    )
    latest = db.scalar(
        select(FirmwareUpdateRecord)
        .where(FirmwareUpdateRecord.device_id == device.id)
        .order_by(FirmwareUpdateRecord.recorded_at.desc())
    )
    recommended_version = recommended.version if recommended else None
    outdated = None if not current or not recommended_version else current != recommended_version
    return DeviceFirmwareStatusOut(
        device_id=device.id,
        external_id=device.external_id,
        device_type=canonical,
        current_version=current,
        recommended_version=recommended_version,
        is_outdated=outdated,
        update_status=(
            "unknown"
            if current is None
            else "outdated"
            if outdated
            else "current"
        ),
        last_update_at=latest.recorded_at if latest else None,
    )


def _canonical_device_type(value: str) -> str:
    return "field_sensor" if (value or "").strip().lower() == "field_sensor" else "silo_sensor"


def _clear_recommended(db: Session, device_type: str, *, except_id: int) -> None:
    for release in db.scalars(
        select(FirmwareRelease).where(
            FirmwareRelease.device_type == device_type,
            FirmwareRelease.id != except_id,
            FirmwareRelease.is_recommended.is_(True),
        )
    ).all():
        release.is_recommended = False


def _validate_checksum(checksum: str | None) -> None:
    if checksum is None:
        return
    value = checksum.lower().strip()
    if len(value) != 64 or any(char not in "0123456789abcdef" for char in value):
        raise HTTPException(status_code=422, detail="El checksum debe ser SHA-256 hexadecimal de 64 caracteres.")
