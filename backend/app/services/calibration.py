from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Device, DeviceChannel, SensorCalibration, SensorMetricValue, SensorReading, User, utc_now
from app.schemas import CalibrationCreateIn, CalibrationPreviewIn, CalibrationPreviewOut


PERCENT_VARIABLES = {"ambient_humidity", "soil_moisture_percent", "level_percent"}
VARIABLE_UNITS = {
    "grain_temperature": "C",
    "ambient_temperature": "C",
    "ambient_humidity": "%",
    "battery_voltage": "V",
    "level_distance_cm": "cm",
    "level_percent": "%",
    "soil_moisture_percent": "%",
    "soil_temperature_c": "C",
}
SILO_VARIABLES = {
    "grain_temperature",
    "ambient_temperature",
    "ambient_humidity",
    "battery_voltage",
    "level_distance_cm",
    "level_percent",
}
FIELD_VARIABLES = {
    "ambient_temperature",
    "ambient_humidity",
    "battery_voltage",
    "soil_moisture_percent",
    "soil_temperature_c",
}


@dataclass(frozen=True)
class CalibrationResult:
    raw_value: float
    value: float
    calibrated_value: float | None
    calibration: SensorCalibration | None
    unit: str
    quality_status: str


def validate_variable_for_device(device: Device, variable_type: str) -> None:
    from app.services.telemetry import sensor_profile

    allowed = FIELD_VARIABLES if sensor_profile(device) == "field_sensor" else SILO_VARIABLES
    if variable_type not in allowed:
        raise ValueError("La variable no es compatible con el tipo de dispositivo.")


def resolve_channel(
    db: Session,
    device: Device,
    variable_type: str,
    device_channel_id: int | None,
) -> DeviceChannel | None:
    if device_channel_id is not None:
        channel = db.get(DeviceChannel, device_channel_id)
        if channel is None or channel.device_id != device.id:
            raise ValueError("El canal no pertenece al dispositivo seleccionado.")
        if channel.metric_type and channel.metric_type != variable_type:
            raise ValueError("El canal no corresponde a la variable seleccionada.")
        return channel
    return db.scalar(
        select(DeviceChannel).where(
            DeviceChannel.device_id == device.id,
            DeviceChannel.is_active.is_(True),
            DeviceChannel.metric_type == variable_type,
        )
    )


def active_calibration(
    db: Session,
    device_id: int,
    variable_type: str,
    device_channel_id: int | None = None,
) -> SensorCalibration | None:
    stmt = select(SensorCalibration).where(
        SensorCalibration.device_id == device_id,
        SensorCalibration.variable_type == variable_type,
        SensorCalibration.is_active.is_(True),
    )
    if device_channel_id is None:
        stmt = stmt.where(SensorCalibration.device_channel_id.is_(None))
    else:
        stmt = stmt.where(SensorCalibration.device_channel_id == device_channel_id)
    calibration = db.scalar(stmt.order_by(SensorCalibration.calibration_version.desc()))
    if calibration is None and device_channel_id is not None:
        calibration = db.scalar(
            select(SensorCalibration)
            .where(
                SensorCalibration.device_id == device_id,
                SensorCalibration.variable_type == variable_type,
                SensorCalibration.device_channel_id.is_(None),
                SensorCalibration.is_active.is_(True),
            )
            .order_by(SensorCalibration.calibration_version.desc())
        )
    return calibration


def _finite(value: float | None, label: str, *, required: bool = False) -> float | None:
    if value is None:
        if required:
            raise ValueError(f"{label} es obligatorio.")
        return None
    if not math.isfinite(value):
        raise ValueError(f"{label} debe ser un numero finito.")
    return float(value)


def _parameters(payload: CalibrationPreviewIn) -> dict[str, Any]:
    return dict(payload.parameters or {})


def coefficients(payload: CalibrationPreviewIn) -> tuple[float | None, float | None, float | None, dict[str, Any]]:
    parameters = _parameters(payload)
    if payload.method == "OFFSET":
        offset = _finite(payload.offset, "El offset", required=True)
        return offset, None, None, parameters

    if payload.method == "LINEAR_TWO_POINT":
        dry_raw = _finite(payload.dry_raw, "La lectura seca", required=True)
        wet_raw = _finite(payload.wet_raw, "La lectura humeda", required=True)
        dry_percent = _finite(payload.dry_percent, "El porcentaje seco", required=True)
        wet_percent = _finite(payload.wet_percent, "El porcentaje humedo", required=True)
        if dry_raw == wet_raw:
            raise ValueError("Las lecturas raw seca y humeda deben ser diferentes.")
        adc_min = float(parameters.get("adc_min", 0))
        adc_max = float(parameters.get("adc_max", 4095))
        if adc_min >= adc_max or not adc_min <= dry_raw <= adc_max or not adc_min <= wet_raw <= adc_max:
            raise ValueError("Las lecturas raw estan fuera del rango ADC configurado.")
        slope = (wet_percent - dry_percent) / (wet_raw - dry_raw)
        intercept = dry_percent - slope * dry_raw
        return None, slope, intercept, {"adc_min": adc_min, "adc_max": adc_max}

    if payload.method == "LEVEL_GEOMETRY":
        mode = str(parameters.get("mode", "two_distance"))
        mounting_offset = float(parameters.get("mounting_offset_cm", 0))
        if mode == "two_distance":
            empty = _finite(float(parameters.get("empty_distance_cm", 0)), "La distancia de silo vacio", required=True)
            full = _finite(float(parameters.get("full_distance_cm", 0)), "La distancia de silo lleno", required=True)
            if empty <= full or full <= 0:
                raise ValueError("La distancia de silo vacio debe ser mayor que la distancia de silo lleno.")
            return None, None, None, {
                "mode": mode,
                "empty_distance_cm": empty,
                "full_distance_cm": full,
                "mounting_offset_cm": mounting_offset,
            }
        if mode == "height_dead_zone":
            total = _finite(float(parameters.get("total_height_cm", 0)), "La altura total", required=True)
            dead_zone = _finite(float(parameters.get("dead_zone_cm", 0)), "La zona muerta", required=True)
            if total <= dead_zone or dead_zone < 0:
                raise ValueError("La altura total debe ser mayor que la zona muerta.")
            return None, None, None, {
                "mode": mode,
                "total_height_cm": total,
                "dead_zone_cm": dead_zone,
                "mounting_offset_cm": mounting_offset,
            }
        raise ValueError("El metodo geometrico de nivel no es valido.")

    raise ValueError("El metodo de calibracion no es valido.")


def _apply_formula(
    method: str,
    raw_value: float,
    *,
    offset: float | None,
    slope: float | None,
    intercept: float | None,
    parameters: dict[str, Any],
) -> float:
    if method == "OFFSET":
        return raw_value + float(offset or 0)
    if method == "LINEAR_TWO_POINT":
        if slope is None or intercept is None:
            raise ValueError("La calibracion lineal no tiene coeficientes validos.")
        return slope * raw_value + intercept
    if method == "LEVEL_GEOMETRY":
        measured = raw_value + float(parameters.get("mounting_offset_cm", 0))
        if parameters.get("mode") == "height_dead_zone":
            total = float(parameters["total_height_cm"])
            usable = total - float(parameters["dead_zone_cm"])
            return ((total - measured) / usable) * 100
        empty = float(parameters["empty_distance_cm"])
        full = float(parameters["full_distance_cm"])
        return ((empty - measured) / (empty - full)) * 100
    raise ValueError("El metodo de calibracion no es valido.")


def preview_calibration(payload: CalibrationPreviewIn) -> CalibrationPreviewOut:
    offset, slope, intercept, parameters = coefficients(payload)
    calibrated = None
    if payload.raw_value is not None:
        raw = _finite(payload.raw_value, "El valor raw", required=True)
        calibrated = _apply_formula(
            payload.method,
            raw,
            offset=offset,
            slope=slope,
            intercept=intercept,
            parameters=parameters,
        )
        if payload.variable_type in PERCENT_VARIABLES:
            calibrated = max(0.0, min(100.0, calibrated))
        calibrated = round(calibrated, 4)
    return CalibrationPreviewOut(
        method=payload.method,
        variable_type=payload.variable_type,
        raw_value=payload.raw_value,
        calibrated_value=calibrated,
        offset=offset,
        slope=slope,
        intercept=intercept,
        parameters=parameters,
    )


def create_calibration(
    db: Session,
    device: Device,
    payload: CalibrationCreateIn,
    user: User,
) -> SensorCalibration:
    validate_variable_for_device(device, payload.variable_type)
    channel = resolve_channel(db, device, payload.variable_type, payload.device_channel_id)
    preview = preview_calibration(payload)
    channel_id = channel.id if channel else None
    active_stmt = select(SensorCalibration).where(
        SensorCalibration.device_id == device.id,
        SensorCalibration.variable_type == payload.variable_type,
        SensorCalibration.is_active.is_(True),
    )
    version_stmt = select(func.max(SensorCalibration.calibration_version)).where(
        SensorCalibration.device_id == device.id,
        SensorCalibration.variable_type == payload.variable_type,
    )
    if channel_id is None:
        active_stmt = active_stmt.where(SensorCalibration.device_channel_id.is_(None))
        version_stmt = version_stmt.where(SensorCalibration.device_channel_id.is_(None))
    else:
        active_stmt = active_stmt.where(SensorCalibration.device_channel_id == channel_id)
        version_stmt = version_stmt.where(SensorCalibration.device_channel_id == channel_id)
    now = utc_now()
    for previous in db.scalars(active_stmt).all():
        previous.is_active = False
        previous.deactivated_at = now
    version = (db.scalar(version_stmt) or 0) + 1
    calibration = SensorCalibration(
        device_id=device.id,
        device_channel_id=channel_id,
        variable_type=payload.variable_type,
        method=payload.method,
        offset=preview.offset,
        slope=preview.slope,
        intercept=preview.intercept,
        dry_raw=payload.dry_raw,
        wet_raw=payload.wet_raw,
        dry_percent=payload.dry_percent,
        wet_percent=payload.wet_percent,
        parameters_json=json.dumps(preview.parameters, ensure_ascii=False),
        calibration_version=version,
        is_active=True,
        calibrated_at=now,
        calibrated_by_user_id=user.id,
        reference_instrument=payload.reference_instrument,
        notes=payload.notes,
        created_at=now,
    )
    db.add(calibration)
    if payload.method == "LEVEL_GEOMETRY":
        if preview.parameters.get("mode") == "two_distance":
            device.empty_distance_cm = float(preview.parameters["empty_distance_cm"])
            device.full_distance_cm = float(preview.parameters["full_distance_cm"])
        else:
            device.empty_distance_cm = float(preview.parameters["total_height_cm"])
            device.full_distance_cm = float(preview.parameters["dead_zone_cm"])
    return calibration


def apply_active_calibration(
    db: Session,
    device: Device,
    variable_type: str,
    raw_value: float,
    *,
    device_channel_id: int | None = None,
) -> CalibrationResult:
    calibration = active_calibration(db, device.id, variable_type, device_channel_id)
    unit = VARIABLE_UNITS.get(variable_type, "")
    if calibration is None:
        return CalibrationResult(raw_value, raw_value, None, None, unit, "raw")
    parameters = json.loads(calibration.parameters_json or "{}")
    value = _apply_formula(
        calibration.method,
        raw_value,
        offset=calibration.offset,
        slope=calibration.slope,
        intercept=calibration.intercept,
        parameters=parameters,
    )
    if variable_type in PERCENT_VARIABLES:
        value = max(0.0, min(100.0, value))
    value = round(value, 4)
    return CalibrationResult(raw_value, value, value, calibration, unit, "calibrated")


def persist_metric(
    db: Session,
    reading: SensorReading,
    device: Device,
    variable_type: str,
    result: CalibrationResult,
    *,
    device_channel_id: int | None = None,
    quality_status: str | None = None,
) -> SensorMetricValue:
    metric = SensorMetricValue(
        sensor_reading_id=reading.id,
        device_id=device.id,
        device_channel_id=device_channel_id,
        calibration_id=result.calibration.id if result.calibration else None,
        variable_type=variable_type,
        raw_value=result.raw_value,
        calibrated_value=result.calibrated_value,
        value=result.value,
        unit=result.unit,
        calibration_version_applied=result.calibration.calibration_version if result.calibration else None,
        quality_status=quality_status or result.quality_status,
        created_at=datetime.now(timezone.utc),
    )
    db.add(metric)
    return metric
