from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_device_access, require_role, require_storage_unit_access, scope_storage_unit_records_query
from app.core.security import hash_secret
from app.db.session import get_db
from app.models import Device, StorageUnit, User
from app.schemas import DeviceCreate, DeviceOut, ThresholdsIn, ThresholdsOut
from app.services.thresholds import get_device_thresholds, upsert_device_thresholds

router = APIRouter(prefix="/devices", dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[DeviceOut])
def list_devices(
    storage_unit_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Device]:
    stmt = scope_storage_unit_records_query(select(Device), Device, current_user, db)
    if storage_unit_id is not None:
        storage_unit = db.get(StorageUnit, storage_unit_id)
        if storage_unit is None:
            return []
        try:
            require_storage_unit_access(db, current_user, storage_unit.id)
        except HTTPException:
            return []
        stmt = stmt.where(Device.storage_unit_id == storage_unit_id)
    return list(db.scalars(stmt.order_by(Device.external_id)).all())


@router.post("", response_model=DeviceOut, status_code=status.HTTP_201_CREATED)
def create_device(
    payload: DeviceCreate,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> Device:
    storage_unit = db.get(StorageUnit, payload.storage_unit_id)
    if storage_unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage unit not found")
    if storage_unit.company_id != payload.company_id or storage_unit.site_id != payload.site_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Device hierarchy is inconsistent")
    if not storage_unit.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Storage unit is inactive")
    if db.scalar(select(Device).where(Device.external_id == payload.external_id)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Device ID already registered")

    device = Device(
        company_id=payload.company_id,
        site_id=payload.site_id,
        storage_unit_id=payload.storage_unit_id,
        external_id=payload.external_id,
        name=payload.name,
        device_type=payload.device_type,
        token_hash=hash_secret(payload.device_token),
        is_active=payload.is_active,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@router.get("/{device_id}", response_model=DeviceOut)
def get_device(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Device:
    return require_device_access(db, current_user, device_id)


@router.get("/{device_id}/thresholds", response_model=ThresholdsOut)
def get_thresholds(
    device_id: int,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> ThresholdsOut:
    device = require_device_access(db, current_user, device_id)
    return get_device_thresholds(db, device)


@router.put("/{device_id}/thresholds", response_model=ThresholdsOut)
def update_thresholds(
    device_id: int,
    payload: ThresholdsIn,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> ThresholdsOut:
    device = require_device_access(db, current_user, device_id)
    thresholds = upsert_device_thresholds(db, device, payload)
    db.commit()
    return thresholds
