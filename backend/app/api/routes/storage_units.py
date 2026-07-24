from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role, require_storage_unit_access, scope_storage_units_query
from app.db.session import get_db
from app.models import Alert, Device, SensorCalibration, SensorReading, Site, StorageUnit, User
from app.schemas import (
    CalibrationStatusOut,
    DeviceOut,
    OperationalLogOut,
    ProductSummaryOut,
    ReadingOut,
    StorageUnitAssignmentsIn,
    StorageUnitCreate,
    StorageUnitOut,
)
from app.services.telemetry import reading_out_for_user

router = APIRouter(prefix="/storage-units", dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[StorageUnitOut])
def list_storage_units(
    site_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[StorageUnit]:
    stmt = scope_storage_units_query(select(StorageUnit), current_user, db)
    if site_id is not None:
        site = db.get(Site, site_id)
        if site is None:
            return []
        if current_user.role != "admin" and site.id not in {unit.site_id for unit in db.scalars(scope_storage_units_query(select(StorageUnit), current_user, db)).all()}:
            return []
        stmt = stmt.where(StorageUnit.site_id == site_id)
    return list(db.scalars(stmt.order_by(StorageUnit.name)).all())


@router.post("", response_model=StorageUnitOut, status_code=status.HTTP_201_CREATED)
def create_storage_unit(
    payload: StorageUnitCreate,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> StorageUnit:
    site = db.get(Site, payload.site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    if site.company_id != payload.company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Site does not belong to company")

    storage_unit = StorageUnit(
        company_id=payload.company_id,
        site_id=payload.site_id,
        name=payload.name,
        unit_type=payload.unit_type,
        operation_type=payload.operation_type,
        capacity_tons=payload.capacity_tons,
        surface_hectares=payload.surface_hectares,
        location=payload.location,
        crop_type=payload.crop_type,
        assigned_technician_id=payload.assigned_technician_id,
        assigned_client_id=payload.assigned_client_id,
    )
    db.add(storage_unit)
    db.commit()
    db.refresh(storage_unit)
    return storage_unit


@router.get("/{storage_unit_id}", response_model=StorageUnitOut)
def get_storage_unit(
    storage_unit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StorageUnit:
    return require_storage_unit_access(db, current_user, storage_unit_id)


@router.patch("/{storage_unit_id}/assignments", response_model=StorageUnitOut)
def update_storage_unit_assignments(
    storage_unit_id: int,
    payload: StorageUnitAssignmentsIn,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> StorageUnit:
    storage_unit = db.get(StorageUnit, storage_unit_id)
    if storage_unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage unit not found")
    storage_unit.assigned_technician_id = payload.assigned_technician_id
    storage_unit.assigned_client_id = payload.assigned_client_id
    db.commit()
    db.refresh(storage_unit)
    return storage_unit


@router.get("/{storage_unit_id}/readings", response_model=list[ReadingOut])
def list_storage_unit_readings(
    storage_unit_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    device_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models import Device, SensorReading

    require_storage_unit_access(db, current_user, storage_unit_id)
    stmt = (
        select(SensorReading)
        .where(SensorReading.storage_unit_id == storage_unit_id)
    )
    if device_id is not None:
        device = db.get(Device, device_id)
        if device is None or device.storage_unit_id != storage_unit_id:
            return []
        stmt = stmt.where(SensorReading.device_id == device_id)
    if from_ is not None:
        stmt = stmt.where(SensorReading.timestamp >= from_)
    if to is not None:
        stmt = stmt.where(SensorReading.timestamp <= to)
    stmt = stmt.order_by(SensorReading.timestamp.desc()).limit(limit)
    return [reading_out_for_user(reading, current_user) for reading in db.scalars(stmt).all()]


@router.get("/{storage_unit_id}/devices", response_model=list[DeviceOut])
def list_storage_unit_devices(
    storage_unit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Device]:
    require_storage_unit_access(db, current_user, storage_unit_id)
    return list(
        db.scalars(
            select(Device)
            .where(Device.storage_unit_id == storage_unit_id)
            .order_by(Device.name, Device.id)
        ).all()
    )


@router.get("/{storage_unit_id}/operational-logs", response_model=list[OperationalLogOut])
def list_storage_unit_operational_logs(
    storage_unit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models import OperationalLog

    require_storage_unit_access(db, current_user, storage_unit_id)
    stmt = (
        select(OperationalLog)
        .where(OperationalLog.storage_unit_id == storage_unit_id)
        .order_by(OperationalLog.timestamp.desc())
    )
    return list(db.scalars(stmt).all())


@router.get("/{storage_unit_id}/product-summary", response_model=ProductSummaryOut)
def get_storage_unit_product_summary(
    storage_unit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProductSummaryOut:
    unit = require_storage_unit_access(db, current_user, storage_unit_id)
    devices = list(db.scalars(select(Device).where(Device.storage_unit_id == unit.id)).all())
    latest = db.scalar(
        select(SensorReading)
        .where(SensorReading.storage_unit_id == unit.id)
        .order_by(SensorReading.timestamp.desc())
    )
    active_alerts = db.scalar(
        select(func.count(Alert.id)).where(
            Alert.storage_unit_id == unit.id,
            Alert.is_active.is_(True),
        )
    ) or 0
    calibration_rows = db.scalars(
        select(SensorCalibration).where(
            SensorCalibration.device_id.in_([device.id for device in devices] or [-1]),
            SensorCalibration.is_active.is_(True),
        )
    ).all()
    statuses = []
    for calibration in calibration_rows:
        calibrated_by = db.get(User, calibration.calibrated_by_user_id) if calibration.calibrated_by_user_id else None
        statuses.append(
            CalibrationStatusOut(
                variable_type=calibration.variable_type,
                status="calibrated",
                calibration_version=calibration.calibration_version,
                calibrated_at=calibration.calibrated_at,
                calibrated_by_name=calibrated_by.full_name if calibrated_by else None,
            )
        )
    return ProductSummaryOut(
        storage_unit=unit,
        product_type="field_sensor" if unit.operation_type == "field" else "silo_sensor",
        device_count=len(devices),
        active_device_count=sum(1 for device in devices if device.is_active),
        active_alerts=active_alerts,
        latest_reading=reading_out_for_user(latest, current_user) if latest else None,
        calibration_statuses=statuses,
    )
