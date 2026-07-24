import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_secret, hash_secret
from app.models import (
    Company,
    Device,
    IotDevice,
    IotGateway,
    IotGatewayCredential,
    IotIngestionBatch,
    IotIngestionEvent,
    IotReading,
    SensorReading,
    StorageUnit,
    utc_now,
)
from app.schemas import IotBatchIn, IotBatchOut, IotBatchReadingIn, IotBatchResultOut
from app.services.alert_engine import evaluate_alerts
from app.services.calibration import CalibrationResult, apply_active_calibration, persist_metric
from app.services.notifications import dispatch_alert_notifications
from app.services.telemetry import calculate_level_percent, sensor_profile

ALLOWED_RESULT_STATUSES = {
    "accepted",
    "duplicate",
    "rejected_invalid",
    "rejected_unknown_device",
    "rejected_unauthorized",
    "temporary_error",
}


def ingest_gateway_batch(
    db: Session,
    *,
    body: bytes,
    gateway_header: str | None,
    timestamp_header: str | None,
    nonce_header: str | None,
    signature_header: str | None,
) -> IotBatchOut:
    gateway = _verify_gateway_request(
        db,
        body=body,
        gateway_header=gateway_header,
        timestamp_header=timestamp_header,
        nonce_header=nonce_header,
        signature_header=signature_header,
    )
    try:
        payload = IotBatchIn.model_validate(json.loads(body.decode("utf-8")))
    except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid batch payload") from exc

    if payload.gateway_id != gateway.gateway_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gateway header does not match payload")

    existing_nonce = db.scalar(
        select(IotIngestionBatch).where(
            IotIngestionBatch.gateway_id == gateway.id,
            IotIngestionBatch.nonce == nonce_header,
        )
    )
    if existing_nonce is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Replay detected")

    batch = IotIngestionBatch(
        gateway_id=gateway.id,
        batch_id=payload.batch_id,
        nonce=nonce_header or "",
        sent_at=payload.sent_at,
        status="processed",
    )
    db.add(batch)
    gateway.firmware_version = payload.firmware_version or gateway.firmware_version
    gateway.last_seen_at = utc_now()
    db.flush()

    results: list[IotBatchResultOut] = []
    new_alerts: list[tuple[Any, SensorReading]] = []
    for reading in payload.readings:
        result, alert_context = _process_reading(db, gateway, batch, reading)
        results.append(result)
        new_alerts.extend(alert_context)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate batch or ingestion record") from exc

    for alert, sensor_reading in new_alerts:
        dispatch_alert_notifications(db, alert, sensor_reading)
    if new_alerts:
        db.commit()

    return IotBatchOut(batch_id=payload.batch_id, results=results)


def _verify_gateway_request(
    db: Session,
    *,
    body: bytes,
    gateway_header: str | None,
    timestamp_header: str | None,
    nonce_header: str | None,
    signature_header: str | None,
) -> IotGateway:
    if not gateway_header or not timestamp_header or not nonce_header or not signature_header:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing gateway authentication headers")

    gateway = db.scalar(select(IotGateway).where(IotGateway.gateway_id == gateway_header))
    if gateway is None or not gateway.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown or inactive gateway")

    _validate_timestamp(timestamp_header)
    credential = db.scalar(
        select(IotGatewayCredential)
        .where(
            IotGatewayCredential.gateway_id == gateway.id,
            IotGatewayCredential.is_active.is_(True),
        )
        .order_by(IotGatewayCredential.key_version.desc())
    )
    if credential is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gateway credential not configured")

    try:
        secret = decrypt_secret(credential.encrypted_secret)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gateway credential unavailable") from exc
    if not hmac.compare_digest(hash_secret(secret), credential.secret_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gateway credential integrity check failed")

    body_hash = hashlib.sha256(body).hexdigest()
    message = f"{gateway_header}{timestamp_header}{nonce_header}{body_hash}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=").strip()
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid gateway signature")
    return gateway


def _validate_timestamp(raw_timestamp: str) -> None:
    try:
        if raw_timestamp.isdigit():
            timestamp = datetime.fromtimestamp(int(raw_timestamp), tz=timezone.utc)
        else:
            timestamp = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid gateway timestamp") from exc

    delta = abs((datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)).total_seconds())
    if delta > settings.iot_signature_window_seconds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Gateway timestamp outside allowed window")


def _process_reading(
    db: Session,
    gateway: IotGateway,
    batch: IotIngestionBatch,
    reading: IotBatchReadingIn,
) -> tuple[IotBatchResultOut, list[tuple[Any, SensorReading]]]:
    status_value = _validate_reading_ranges(reading)
    iot_device = db.scalar(select(IotDevice).where(IotDevice.node_id == reading.device_id))
    if iot_device is None:
        return _record_event(db, gateway, batch, reading, "rejected_unknown_device", "IoT device not registered"), []
    if not iot_device.is_active:
        return _record_event(db, gateway, batch, reading, "rejected_unauthorized", "IoT device is inactive"), []
    if status_value is not None:
        return _record_event(db, gateway, batch, reading, "rejected_invalid", status_value), []

    existing = db.scalar(
        select(IotReading).where(
            IotReading.iot_device_id == iot_device.id,
            IotReading.boot_id == reading.boot_id,
            IotReading.sequence == reading.sequence,
        )
    )
    if existing is not None:
        return _record_event(db, gateway, batch, reading, "duplicate", "Reading already stored"), []

    device = db.get(Device, iot_device.device_id)
    if device is None or not device.is_active:
        return _record_event(db, gateway, batch, reading, "rejected_unauthorized", "Linked sensor is inactive"), []
    storage_unit = db.get(StorageUnit, device.storage_unit_id)
    company = db.get(Company, device.company_id)
    if storage_unit is None or company is None or not storage_unit.is_active or not company.is_active:
        return _record_event(db, gateway, batch, reading, "rejected_unauthorized", "Linked company or storage unit is inactive"), []

    profile = sensor_profile(device)
    if reading.sensor_profile is not None and reading.sensor_profile != profile:
        return _record_event(db, gateway, batch, reading, "rejected_invalid", "Sensor profile does not match device"), []
    if profile == "field_sensor" and (reading.grain_temp_c_x100 is not None or reading.level_distance_cm is not None):
        return _record_event(db, gateway, batch, reading, "rejected_invalid", "Field sensor contains silo metrics"), []
    if profile == "silo_sensor" and (
        reading.soil_moisture_x100 is not None
        or reading.soil_moisture_raw is not None
        or reading.soil_temp_c_x100 is not None
    ):
        return _record_event(db, gateway, batch, reading, "rejected_invalid", "Silo sensor contains soil metrics"), []
    if reading.soil_moisture_x100 is not None and reading.soil_moisture_raw is not None:
        return _record_event(db, gateway, batch, reading, "rejected_invalid", "Soil moisture raw and legacy percent cannot coexist"), []

    try:
        raw_metrics = {
            "grain_temperature": reading.grain_temp_c_x100 / 100 if reading.grain_temp_c_x100 is not None else None,
            "ambient_temperature": reading.air_temp_c_x100 / 100 if reading.air_temp_c_x100 is not None else None,
            "ambient_humidity": reading.rh_x100 / 100 if reading.rh_x100 is not None else None,
            "battery_voltage": reading.battery_mv / 1000 if reading.battery_mv is not None else None,
            "soil_temperature_c": reading.soil_temp_c_x100 / 100 if reading.soil_temp_c_x100 is not None else None,
        }
        calibrated = {
            variable: apply_active_calibration(db, device, variable, raw)
            for variable, raw in raw_metrics.items()
            if raw is not None
        }
        soil_result = None
        if reading.soil_moisture_raw is not None:
            soil_result = apply_active_calibration(
                db,
                device,
                "soil_moisture_percent",
                float(reading.soil_moisture_raw),
            )
        elif reading.soil_moisture_x100 is not None:
            legacy_soil = reading.soil_moisture_x100 / 100
            soil_result = CalibrationResult(
                raw_value=legacy_soil,
                value=legacy_soil,
                calibrated_value=None,
                calibration=None,
                unit="%",
                quality_status="legacy_reported",
            )
        level_result = None
        level_percent = None
        if reading.level_distance_cm is not None:
            level_result = apply_active_calibration(db, device, "level_percent", reading.level_distance_cm)
            level_percent = (
                level_result.calibrated_value
                if level_result.calibration is not None
                else calculate_level_percent(device, reading.level_distance_cm)
            )
    except ValueError as exc:
        return _record_event(db, gateway, batch, reading, "rejected_invalid", str(exc)), []

    timestamp = datetime.fromtimestamp(reading.timestamp_utc, tz=timezone.utc)
    sensor_reading = SensorReading(
        company_id=device.company_id,
        site_id=device.site_id,
        storage_unit_id=device.storage_unit_id,
        device_id=device.id,
        grain_temperature=calibrated["grain_temperature"].value if "grain_temperature" in calibrated else None,
        ambient_temperature=calibrated["ambient_temperature"].value if "ambient_temperature" in calibrated else None,
        ambient_humidity=calibrated["ambient_humidity"].value if "ambient_humidity" in calibrated else None,
        battery_voltage=calibrated["battery_voltage"].value if "battery_voltage" in calibrated else None,
        signal_quality=reading.rssi_dbm,
        level_distance_cm=reading.level_distance_cm,
        level_percent=level_percent,
        soil_moisture_percent=(
            soil_result.value
            if soil_result is not None and (soil_result.calibration is not None or soil_result.quality_status == "legacy_reported")
            else None
        ),
        soil_temperature_c=calibrated["soil_temperature_c"].value if "soil_temperature_c" in calibrated else None,
        sensor_status=reading.sensor_status,
        timestamp=timestamp,
    )
    db.add(sensor_reading)
    db.flush()
    for variable, result in calibrated.items():
        persist_metric(db, sensor_reading, device, variable, result)
    if soil_result is not None:
        persist_metric(db, sensor_reading, device, "soil_moisture_percent", soil_result)
    if reading.level_distance_cm is not None:
        persist_metric(
            db,
            sensor_reading,
            device,
            "level_distance_cm",
            CalibrationResult(
                raw_value=reading.level_distance_cm,
                value=reading.level_distance_cm,
                calibrated_value=None,
                calibration=None,
                unit="cm",
                quality_status="raw",
            ),
        )
        if level_result is not None and level_percent is not None:
            if level_result.calibration is None:
                level_result = CalibrationResult(
                    raw_value=reading.level_distance_cm,
                    value=level_percent,
                    calibrated_value=level_percent,
                    calibration=None,
                    unit="%",
                    quality_status="legacy_calibrated",
                )
            persist_metric(db, sensor_reading, device, "level_percent", level_result)

    iot_reading = IotReading(
        iot_device_id=iot_device.id,
        device_id=device.id,
        gateway_id=gateway.id,
        sensor_reading_id=sensor_reading.id,
        company_id=device.company_id,
        site_id=device.site_id,
        storage_unit_id=device.storage_unit_id,
        boot_id=reading.boot_id,
        sequence=reading.sequence,
        sample_counter=reading.sample_counter,
        timestamp_utc=reading.timestamp_utc,
        timestamp=timestamp,
        time_quality=reading.time_quality,
        grain_temp_c_x100=reading.grain_temp_c_x100,
        air_temp_c_x100=reading.air_temp_c_x100,
        rh_x100=reading.rh_x100,
        battery_mv=reading.battery_mv,
        soil_moisture_x100=reading.soil_moisture_x100,
        soil_moisture_raw=reading.soil_moisture_raw,
        soil_temp_c_x100=reading.soil_temp_c_x100,
        level_distance_mm=round(reading.level_distance_cm * 10) if reading.level_distance_cm is not None else None,
        level_percent_x100=round(level_percent * 100) if level_percent is not None else None,
        sensor_status=reading.sensor_status,
        firmware_version=reading.firmware_version,
        rssi_dbm=reading.rssi_dbm,
        snr_db_x10=reading.snr_db_x10,
    )
    db.add(iot_reading)
    device.last_seen_at = utc_now()
    db.flush()

    alerts = evaluate_alerts(db=db, device=device, reading=sensor_reading)
    new_alerts = [(alert, sensor_reading) for alert in alerts if getattr(alert, "_was_created", False)]
    return _record_event(db, gateway, batch, reading, "accepted", None), new_alerts


def _validate_reading_ranges(reading: IotBatchReadingIn) -> str | None:
    if reading.sequence < 0 or reading.boot_id < 0 or reading.sample_counter < 0:
        return "Sequence, boot_id and sample_counter must be non-negative"
    if reading.grain_temp_c_x100 is not None and not -4000 <= reading.grain_temp_c_x100 <= 10000:
        return "Grain temperature outside physical range"
    if reading.air_temp_c_x100 is not None and not -4000 <= reading.air_temp_c_x100 <= 8000:
        return "Air temperature outside physical range"
    if reading.rh_x100 is not None and not 0 <= reading.rh_x100 <= 10000:
        return "Humidity outside physical range"
    if reading.battery_mv is not None and not 0 <= reading.battery_mv <= 6000:
        return "Battery voltage outside physical range"
    if reading.soil_moisture_x100 is not None and not 0 <= reading.soil_moisture_x100 <= 10000:
        return "Soil moisture outside physical range"
    if reading.soil_moisture_raw is not None and not 0 <= reading.soil_moisture_raw <= 4095:
        return "Soil moisture raw outside ADC range"
    if reading.soil_temp_c_x100 is not None and not -4000 <= reading.soil_temp_c_x100 <= 8000:
        return "Soil temperature outside physical range"
    if reading.level_distance_cm is not None and not 0 < reading.level_distance_cm <= 2000:
        return "Ultrasonic distance outside physical range"
    metrics = (
        reading.grain_temp_c_x100,
        reading.air_temp_c_x100,
        reading.rh_x100,
        reading.battery_mv,
        reading.soil_moisture_x100,
        reading.soil_moisture_raw,
        reading.soil_temp_c_x100,
        reading.level_distance_cm,
    )
    if all(value is None for value in metrics):
        return "Reading contains no metrics"
    return None


def _record_event(
    db: Session,
    gateway: IotGateway,
    batch: IotIngestionBatch,
    reading: IotBatchReadingIn,
    result_status: str,
    detail: str | None,
) -> IotBatchResultOut:
    db.add(
        IotIngestionEvent(
            batch_id=batch.id,
            gateway_id=gateway.id,
            device_identifier=reading.device_id,
            boot_id=reading.boot_id,
            sequence=reading.sequence,
            status=result_status,
            error=detail,
        )
    )
    return IotBatchResultOut(
        device_id=reading.device_id,
        boot_id=reading.boot_id,
        sequence=reading.sequence,
        status=result_status,  # type: ignore[arg-type]
        detail=detail,
    )
