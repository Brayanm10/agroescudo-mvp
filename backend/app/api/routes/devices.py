from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_device_access, require_role, require_storage_unit_access, scope_storage_unit_records_query
from app.core.security import hash_secret
from app.db.session import get_db
from app.models import Alert, Device, IotDevice, IotReading, OperationalLog, SensorCalibration, SensorReading, StorageUnit, User, utc_now
from app.schemas import (
    AlertOut,
    CalibrationCreateIn,
    CalibrationOut,
    CalibrationPreviewIn,
    CalibrationPreviewOut,
    CalibrationStatusOut,
    ComparisonOut,
    DeviceCalibrationOut,
    DeviceCreate,
    DeviceDiagnosticsOut,
    DeviceOut,
    DeviceSummaryOut,
    ReadingOut,
    ThresholdsIn,
    ThresholdsOut,
)
from app.services.audit import record_audit_event
from app.services.calibration import create_calibration, preview_calibration
from app.services.comparison import compare_device_periods
from app.services.thresholds import get_device_thresholds, upsert_device_thresholds
from app.services.telemetry import reading_out_for_user, sensor_profile, validate_device_unit_compatibility

router = APIRouter(prefix="/devices", dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[DeviceOut])
def list_devices(
    storage_unit_id: int | None = None,
    device_type: str | None = None,
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
    if device_type is not None:
        normalized = device_type.strip().lower()
        if normalized == "silo_sensor":
            stmt = stmt.where(Device.device_type.in_(["silo_sensor", "esp32_iot_node", "esp32_lora_wifi_node", "esp32_lora_node"]))
        else:
            stmt = stmt.where(Device.device_type == normalized)
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
    try:
        validate_device_unit_compatibility(payload.device_type, storage_unit.operation_type)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if db.scalar(select(Device).where(Device.external_id == payload.external_id)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Device ID already registered")

    device = Device(
        company_id=payload.company_id,
        site_id=payload.site_id,
        storage_unit_id=payload.storage_unit_id,
        external_id=payload.external_id,
        name=payload.name,
        device_type=payload.device_type,
        model_version=payload.model_version,
        physical_location=payload.physical_location,
        installed_at=payload.installed_at,
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


@router.get("/{device_id}/readings", response_model=list[ReadingOut])
def get_device_readings(
    device_id: int,
    limit: int = 100,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    order: str = Query(default="desc", pattern="^(asc|desc)$"),
    variable: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReadingOut]:
    require_device_access(db, current_user, device_id)
    stmt = select(SensorReading).where(SensorReading.device_id == device_id)
    if from_ is not None:
        stmt = stmt.where(SensorReading.timestamp >= from_)
    if to is not None:
        stmt = stmt.where(SensorReading.timestamp <= to)
    direction = SensorReading.timestamp.asc() if order == "asc" else SensorReading.timestamp.desc()
    readings = db.scalars(stmt.order_by(direction).limit(max(1, min(limit, 1000)))).all()
    results = [reading_out_for_user(reading, current_user) for reading in readings]
    if variable:
        for result in results:
            result.metrics = [metric for metric in result.metrics if metric.variable_type == variable]
    return results


@router.get("/{device_id}/compare", response_model=ComparisonOut)
def compare_device(
    device_id: int,
    variable: str,
    period_a_from: datetime,
    period_a_to: datetime,
    period_b_from: datetime,
    period_b_to: datetime,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ComparisonOut:
    device = require_device_access(db, current_user, device_id)
    try:
        return compare_device_periods(
            db,
            device,
            variable=variable,
            period_a_from=period_a_from,
            period_a_to=period_a_to,
            period_b_from=period_b_from,
            period_b_to=period_b_to,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


def _calibration_out(db: Session, calibration: SensorCalibration, user: User) -> CalibrationOut:
    calibrated_by = db.get(User, calibration.calibrated_by_user_id) if calibration.calibrated_by_user_id else None
    technical = user.role in {"admin", "technician"}
    import json

    return CalibrationOut(
        id=calibration.id,
        device_id=calibration.device_id,
        device_channel_id=calibration.device_channel_id,
        variable_type=calibration.variable_type,
        method=calibration.method,
        offset=calibration.offset if technical else None,
        slope=calibration.slope if technical else None,
        intercept=calibration.intercept if technical else None,
        dry_raw=calibration.dry_raw if technical else None,
        wet_raw=calibration.wet_raw if technical else None,
        dry_percent=calibration.dry_percent if technical else None,
        wet_percent=calibration.wet_percent if technical else None,
        parameters=json.loads(calibration.parameters_json or "{}") if technical else {},
        calibration_version=calibration.calibration_version,
        is_active=calibration.is_active,
        calibrated_at=calibration.calibrated_at,
        calibrated_by_user_id=calibration.calibrated_by_user_id if technical else None,
        calibrated_by_name=calibrated_by.full_name if calibrated_by else None,
        reference_instrument=calibration.reference_instrument if technical else None,
        notes=calibration.notes if technical else None,
        created_at=calibration.created_at,
    )


@router.get("/{device_id}/calibrations", response_model=list[CalibrationOut])
def list_calibrations(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CalibrationOut]:
    require_device_access(db, current_user, device_id)
    rows = db.scalars(
        select(SensorCalibration)
        .where(SensorCalibration.device_id == device_id)
        .order_by(SensorCalibration.variable_type, SensorCalibration.calibration_version.desc())
    ).all()
    return [_calibration_out(db, item, current_user) for item in rows]


@router.get("/{device_id}/calibrations/active", response_model=list[CalibrationStatusOut])
def list_active_calibrations(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CalibrationStatusOut]:
    require_device_access(db, current_user, device_id)
    rows = db.scalars(
        select(SensorCalibration).where(
            SensorCalibration.device_id == device_id,
            SensorCalibration.is_active.is_(True),
        )
    ).all()
    result = []
    for item in rows:
        calibrated_by = db.get(User, item.calibrated_by_user_id) if item.calibrated_by_user_id else None
        result.append(
            CalibrationStatusOut(
                variable_type=item.variable_type,
                status="calibrated",
                calibration_version=item.calibration_version,
                calibrated_at=item.calibrated_at,
                calibrated_by_name=calibrated_by.full_name if calibrated_by else None,
            )
        )
    return result


@router.post("/{device_id}/calibrations/preview", response_model=CalibrationPreviewOut)
def preview_device_calibration(
    device_id: int,
    payload: CalibrationPreviewIn,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> CalibrationPreviewOut:
    device = require_device_access(db, current_user, device_id)
    from app.services.calibration import resolve_channel, validate_variable_for_device

    try:
        validate_variable_for_device(device, payload.variable_type)
        resolve_channel(db, device, payload.variable_type, payload.device_channel_id)
        return preview_calibration(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/{device_id}/calibrations", response_model=CalibrationOut, status_code=status.HTTP_201_CREATED)
def create_device_calibration(
    device_id: int,
    payload: CalibrationCreateIn,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> CalibrationOut:
    device = require_device_access(db, current_user, device_id)
    try:
        calibration = create_calibration(db, device, payload, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    db.flush()
    record_audit_event(
        db,
        action="sensor.calibration.create",
        summary="Calibracion versionada creada",
        user=current_user,
        resource_type="sensor_calibration",
        resource_id=calibration.id,
        metadata={
            "device_id": device.id,
            "variable_type": calibration.variable_type,
            "method": calibration.method,
            "version": calibration.calibration_version,
        },
    )
    db.add(
        OperationalLog(
            company_id=device.company_id,
            site_id=device.site_id,
            storage_unit_id=device.storage_unit_id,
            device_id=device.id,
            user_id=current_user.id,
            category="maintenance",
            action_taken=f"Calibracion {calibration.variable_type} v{calibration.calibration_version}",
            operator_name=current_user.full_name or current_user.email,
            notes=payload.notes or "Calibracion registrada desde la plataforma.",
            timestamp=calibration.calibrated_at,
        )
    )
    db.commit()
    db.refresh(calibration)
    return _calibration_out(db, calibration, current_user)


@router.post("/{device_id}/calibrations/{calibration_id}/activate", response_model=CalibrationOut)
def activate_device_calibration(
    device_id: int,
    calibration_id: int,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> CalibrationOut:
    require_device_access(db, current_user, device_id)
    calibration = db.get(SensorCalibration, calibration_id)
    if calibration is None or calibration.device_id != device_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calibracion no encontrada.")
    stmt = select(SensorCalibration).where(
        SensorCalibration.device_id == device_id,
        SensorCalibration.variable_type == calibration.variable_type,
        SensorCalibration.is_active.is_(True),
    )
    if calibration.device_channel_id is None:
        stmt = stmt.where(SensorCalibration.device_channel_id.is_(None))
    else:
        stmt = stmt.where(SensorCalibration.device_channel_id == calibration.device_channel_id)
    for current in db.scalars(stmt).all():
        current.is_active = False
        current.deactivated_at = utc_now()
    calibration.is_active = True
    calibration.deactivated_at = None
    record_audit_event(
        db,
        action="sensor.calibration.activate",
        summary="Version de calibracion activada",
        user=current_user,
        resource_type="sensor_calibration",
        resource_id=calibration.id,
        metadata={"device_id": device_id, "version": calibration.calibration_version},
    )
    db.commit()
    db.refresh(calibration)
    return _calibration_out(db, calibration, current_user)


@router.post("/{device_id}/calibrations/{calibration_id}/deactivate", response_model=CalibrationOut)
def deactivate_device_calibration(
    device_id: int,
    calibration_id: int,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> CalibrationOut:
    require_device_access(db, current_user, device_id)
    calibration = db.get(SensorCalibration, calibration_id)
    if calibration is None or calibration.device_id != device_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calibracion no encontrada.")
    calibration.is_active = False
    calibration.deactivated_at = utc_now()
    record_audit_event(
        db,
        action="sensor.calibration.deactivate",
        summary="Calibracion desactivada",
        user=current_user,
        resource_type="sensor_calibration",
        resource_id=calibration.id,
        metadata={"device_id": device_id, "version": calibration.calibration_version},
    )
    db.commit()
    db.refresh(calibration)
    return _calibration_out(db, calibration, current_user)


@router.get("/{device_id}/alerts", response_model=list[AlertOut])
def get_device_alerts(
    device_id: int,
    active_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Alert]:
    require_device_access(db, current_user, device_id)
    stmt = select(Alert).where(Alert.device_id == device_id)
    if active_only:
        stmt = stmt.where(Alert.is_active.is_(True))
    return list(db.scalars(stmt.order_by(Alert.created_at.desc())).all())


@router.get("/{device_id}/summary", response_model=DeviceSummaryOut)
def get_device_summary(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceSummaryOut:
    device = require_device_access(db, current_user, device_id)
    latest = db.scalar(
        select(SensorReading)
        .where(SensorReading.device_id == device.id)
        .order_by(SensorReading.timestamp.desc())
    )
    active_alerts = db.scalar(
        select(func.count(Alert.id)).where(Alert.device_id == device.id, Alert.is_active.is_(True))
    ) or 0
    profile = sensor_profile(device)
    calibration_status = "not_applicable"
    if profile == "silo_sensor":
        calibration_status = (
            "configured"
            if device.empty_distance_cm is not None and device.full_distance_cm is not None
            else "pending"
        )
    diagnostics = None
    if current_user.role in {"admin", "technician"}:
        iot_device = db.scalar(select(IotDevice).where(IotDevice.device_id == device.id))
        iot_reading = None
        if iot_device is not None:
            iot_reading = db.scalar(
                select(IotReading)
                .where(IotReading.iot_device_id == iot_device.id)
                .order_by(IotReading.timestamp.desc())
            )
        diagnostics = DeviceDiagnosticsOut(
            signal_quality=latest.signal_quality if latest else None,
            snr_db=iot_reading.snr_db_x10 / 10 if iot_reading and iot_reading.snr_db_x10 is not None else None,
            sensor_status=latest.sensor_status if latest else None,
            firmware_version=str(iot_reading.firmware_version) if iot_reading else iot_device.firmware_version if iot_device else None,
        )
    active_calibrations = db.scalars(
        select(SensorCalibration).where(
            SensorCalibration.device_id == device.id,
            SensorCalibration.is_active.is_(True),
        )
    ).all()
    calibration_statuses = []
    for calibration_item in active_calibrations:
        calibrated_by = db.get(User, calibration_item.calibrated_by_user_id) if calibration_item.calibrated_by_user_id else None
        calibration_statuses.append(
            CalibrationStatusOut(
                variable_type=calibration_item.variable_type,
                status="calibrated",
                calibration_version=calibration_item.calibration_version,
                calibrated_at=calibration_item.calibrated_at,
                calibrated_by_name=calibrated_by.full_name if calibrated_by else None,
            )
        )
    return DeviceSummaryOut(
        device=device,
        latest_reading=reading_out_for_user(latest, current_user) if latest else None,
        active_alerts=active_alerts,
        calibration_status=calibration_status,
        diagnostics=diagnostics,
        calibration=DeviceCalibrationOut(
            empty_distance_cm=device.empty_distance_cm,
            full_distance_cm=device.full_distance_cm,
        ) if current_user.role == "admin" else None,
        calibration_statuses=calibration_statuses,
    )


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
