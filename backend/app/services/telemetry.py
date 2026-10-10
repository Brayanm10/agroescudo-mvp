from __future__ import annotations

import math
from datetime import datetime, timezone

from app.models import Device, SensorReading, User
from app.schemas import MetricValueOut, ReadingOut, SensorReadingCreate

SILO_SENSOR_TYPES = {"silo_sensor", "esp32_iot_node", "esp32_lora_wifi_node", "esp32_lora_node"}
FIELD_SENSOR_TYPES = {"field_sensor"}
RAIN_GAUGE_TYPES = {"rain_gauge"}
MAX_ULTRASONIC_DISTANCE_CM = 2000.0
MAX_ULTRASONIC_DISTANCE_MM = MAX_ULTRASONIC_DISTANCE_CM * 10


def sensor_profile(device: Device) -> str:
    normalized = (device.device_type or "").strip().lower()
    if normalized in FIELD_SENSOR_TYPES:
        return "field_sensor"
    if normalized in RAIN_GAUGE_TYPES:
        return "rain_gauge"
    if normalized in SILO_SENSOR_TYPES:
        return "silo_sensor"
    return "unknown"


def validate_device_unit_compatibility(device_type: str, operation_type: str) -> None:
    normalized = device_type.strip().lower()
    if normalized in FIELD_SENSOR_TYPES:
        profile = "field_sensor"
    elif normalized in RAIN_GAUGE_TYPES:
        profile = "rain_gauge"
    elif normalized in SILO_SENSOR_TYPES:
        profile = "silo_sensor"
    else:
        raise ValueError("El tipo de dispositivo no esta registrado.")
    expected = "field" if profile in {"field_sensor", "rain_gauge"} else "storage"
    if operation_type != expected:
        label = "parcela/campo" if expected == "field" else "silo/almacenamiento"
        raise ValueError(f"El dispositivo solo puede registrarse en una unidad de tipo {label}.")


def product_code_for_device(device: Device) -> str:
    return {
        "silo_sensor": "SILO_SENSOR",
        "field_sensor": "CAMPO_SENSOR",
        "rain_gauge": "RAIN_GAUGE",
    }.get(sensor_profile(device), "UNKNOWN")


def device_communication_status(device: Device, now: datetime | None = None) -> str:
    if not device.is_active:
        return "OFFLINE"
    if device.operational_status in {"degraded", "calibration_pending"}:
        return "DEGRADED"
    if device.last_seen_at is None:
        return "OFFLINE"
    interval = device.expected_reading_interval_minutes
    if not interval:
        return "ONLINE"
    reference = now or datetime.now(timezone.utc)
    last_seen = device.last_seen_at
    if last_seen.tzinfo is None:
        last_seen = last_seen.replace(tzinfo=timezone.utc)
    age_minutes = (reference - last_seen.astimezone(timezone.utc)).total_seconds() / 60
    if age_minutes > interval * 6:
        return "OFFLINE"
    if age_minutes > interval * 2:
        return "DELAYED"
    return "ONLINE"


def calculate_fill_metrics(
    measured_distance_mm: float | None,
    empty_distance_mm: float | None,
    full_distance_mm: float | None,
) -> tuple[float, float] | None:
    """Derive fill percentage and product height without changing the raw distance."""
    if measured_distance_mm is None:
        return None
    if (
        not math.isfinite(measured_distance_mm)
        or measured_distance_mm <= 0
        or measured_distance_mm > MAX_ULTRASONIC_DISTANCE_MM
    ):
        raise ValueError("La distancia ultrasonica esta fuera del rango fisico permitido.")
    if empty_distance_mm is None or full_distance_mm is None:
        return None
    if (
        not math.isfinite(empty_distance_mm)
        or not math.isfinite(full_distance_mm)
        or empty_distance_mm <= full_distance_mm
        or full_distance_mm <= 0
    ):
        raise ValueError("La calibracion del nivel no es valida.")
    product_height_mm = empty_distance_mm - measured_distance_mm
    raw_percent = (product_height_mm / (empty_distance_mm - full_distance_mm)) * 100
    return round(max(0.0, min(100.0, raw_percent)), 2), round(max(0.0, product_height_mm), 2)


def calculate_level_percent(device: Device, distance_cm: float | None) -> float | None:
    result = calculate_fill_metrics(
        None if distance_cm is None else distance_cm * 10,
        None if device.empty_distance_cm is None else device.empty_distance_cm * 10,
        None if device.full_distance_cm is None else device.full_distance_cm * 10,
    )
    return result[0] if result else None


def validate_telemetry(device: Device, payload: SensorReadingCreate) -> None:
    profile = sensor_profile(device)
    values = [
        payload.grain_temperature,
        payload.ambient_temperature,
        payload.ambient_humidity,
        payload.battery_voltage,
        payload.level_distance_cm,
        payload.soil_moisture_percent,
        payload.soil_moisture_raw,
        payload.soil_temperature_c,
    ]
    if all(value is None for value in values):
        raise ValueError("La lectura no contiene metricas.")
    _range(payload.grain_temperature, -40, 100, "temperatura de grano")
    _range(payload.ambient_temperature, -40, 80, "temperatura ambiente")
    _range(payload.ambient_humidity, 0, 100, "humedad ambiente")
    _range(payload.battery_voltage, 0, 6, "voltaje de bateria")
    _range(payload.soil_moisture_percent, 0, 100, "humedad del suelo")
    _range(payload.soil_moisture_raw, 0, 4095, "lectura raw de humedad del suelo")
    _range(payload.soil_temperature_c, -40, 80, "temperatura del suelo")
    if payload.level_distance_cm is not None:
        calculate_level_percent(device, payload.level_distance_cm)

    if profile == "field_sensor" and (payload.grain_temperature is not None or payload.level_distance_cm is not None):
        raise ValueError("Un CampoSensor no admite temperatura de grano ni nivel de silo.")
    if payload.soil_moisture_raw is not None and payload.soil_moisture_percent is not None:
        raise ValueError("Envia humedad de suelo raw o porcentaje legacy, no ambos.")
    if profile == "silo_sensor" and (
        payload.soil_moisture_percent is not None
        or payload.soil_moisture_raw is not None
        or payload.soil_temperature_c is not None
    ):
        raise ValueError("Un SiloSensor no admite metricas de suelo.")


def reading_out_for_user(reading: SensorReading, user: User) -> ReadingOut:
    result = ReadingOut.model_validate(reading)
    result.metrics = [
        MetricValueOut(
            variable_type=metric.variable_type,
            raw_value=metric.raw_value if user.role in {"admin", "technician"} else None,
            value=metric.value,
            calibrated_value=metric.calibrated_value,
            is_calibrated=metric.calibration_version_applied is not None,
            calibration_version=metric.calibration_version_applied,
            unit=metric.unit,
            quality_status=metric.quality_status,
        )
        for metric in reading.metric_values
    ]
    if user.role == "client":
        result.signal_quality = None
        result.sensor_status = None
    return result


def _range(value: float | None, minimum: float, maximum: float, label: str) -> None:
    if value is None:
        return
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"La {label} esta fuera del rango fisico permitido.")
