from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_secret
from app.models import Company, Device, SensorReading, StorageUnit, utc_now
from app.schemas import ReadingIngestResponse, SensorReadingCreate
from app.services.alert_engine import evaluate_alerts
from app.services.calibration import CalibrationResult, apply_active_calibration, persist_metric
from app.services.notifications import dispatch_alert_notifications
from app.services.telemetry import calculate_level_percent, validate_telemetry


def ingest_authenticated_reading(db: Session, payload: SensorReadingCreate) -> ReadingIngestResponse:
    device = db.scalar(select(Device).where(Device.external_id == payload.device_id))
    if device is None or not verify_secret(payload.device_token, device.token_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device credentials")
    if not device.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sensor inactivo. Contacta al administrador.")

    storage_unit = db.get(StorageUnit, device.storage_unit_id)
    company = db.get(Company, device.company_id)
    if storage_unit is None or not storage_unit.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Silo/galpon inactivo. Contacta al administrador.")
    if company is None or not company.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Empresa inactiva. Contacta al administrador.")

    return create_device_reading(db, device, payload)


def create_device_reading(db: Session, device: Device, payload: SensorReadingCreate) -> ReadingIngestResponse:
    try:
        validate_telemetry(device, payload)
        calibrated: dict[str, CalibrationResult] = {}
        for variable in (
            "grain_temperature",
            "ambient_temperature",
            "ambient_humidity",
            "battery_voltage",
            "soil_temperature_c",
        ):
            raw = getattr(payload, variable)
            if raw is not None:
                calibrated[variable] = apply_active_calibration(db, device, variable, raw)

        soil_result = None
        if payload.soil_moisture_raw is not None:
            soil_result = apply_active_calibration(
                db,
                device,
                "soil_moisture_percent",
                payload.soil_moisture_raw,
            )
        elif payload.soil_moisture_percent is not None:
            soil_result = CalibrationResult(
                raw_value=payload.soil_moisture_percent,
                value=payload.soil_moisture_percent,
                calibrated_value=None,
                calibration=None,
                unit="%",
                quality_status="legacy_reported",
            )

        level_result = None
        level_percent = None
        if payload.level_distance_cm is not None:
            level_result = apply_active_calibration(
                db,
                device,
                "level_percent",
                payload.level_distance_cm,
            )
            level_percent = (
                level_result.calibrated_value
                if level_result.calibration is not None
                else calculate_level_percent(device, payload.level_distance_cm)
            )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    reading = SensorReading(
        company_id=device.company_id,
        site_id=device.site_id,
        storage_unit_id=device.storage_unit_id,
        device_id=device.id,
        grain_temperature=calibrated.get("grain_temperature", None).value if "grain_temperature" in calibrated else None,
        ambient_temperature=calibrated.get("ambient_temperature", None).value if "ambient_temperature" in calibrated else None,
        ambient_humidity=calibrated.get("ambient_humidity", None).value if "ambient_humidity" in calibrated else None,
        battery_voltage=calibrated.get("battery_voltage", None).value if "battery_voltage" in calibrated else None,
        signal_quality=payload.signal_quality,
        level_distance_cm=payload.level_distance_cm,
        level_percent=level_percent,
        soil_moisture_percent=(
            soil_result.value
            if soil_result is not None and (soil_result.calibration is not None or soil_result.quality_status == "legacy_reported")
            else None
        ),
        soil_temperature_c=calibrated.get("soil_temperature_c", None).value if "soil_temperature_c" in calibrated else None,
        sensor_status=payload.sensor_status,
        timestamp=payload.timestamp,
    )
    db.add(reading)
    device.last_seen_at = utc_now()
    db.flush()
    for variable, result in calibrated.items():
        persist_metric(db, reading, device, variable, result)
    if soil_result is not None:
        persist_metric(db, reading, device, "soil_moisture_percent", soil_result)
    if payload.level_distance_cm is not None:
        persist_metric(
            db,
            reading,
            device,
            "level_distance_cm",
            CalibrationResult(
                raw_value=payload.level_distance_cm,
                value=payload.level_distance_cm,
                calibrated_value=None,
                calibration=None,
                unit="cm",
                quality_status="raw",
            ),
        )
        if level_result is not None and level_percent is not None:
            if level_result.calibration is None:
                level_result = CalibrationResult(
                    raw_value=payload.level_distance_cm,
                    value=level_percent,
                    calibrated_value=level_percent,
                    calibration=None,
                    unit="%",
                    quality_status="legacy_calibrated",
                )
            persist_metric(db, reading, device, "level_percent", level_result)

    alerts = evaluate_alerts(db=db, device=device, reading=reading)
    new_alerts = [alert for alert in alerts if getattr(alert, "_was_created", False)]
    db.commit()
    db.refresh(reading)
    for alert in alerts:
        db.refresh(alert)
    if new_alerts:
        for alert in new_alerts:
            dispatch_alert_notifications(db, alert, reading)
        db.commit()
        for alert in alerts:
            db.refresh(alert)

    return ReadingIngestResponse(reading=reading, alerts=alerts)
