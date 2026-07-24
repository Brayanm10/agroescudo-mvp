from __future__ import annotations

import math

from app.models import Device, SensorReading, User
from app.schemas import MetricValueOut, ReadingOut, SensorReadingCreate

SILO_SENSOR_TYPES = {"silo_sensor", "esp32_iot_node", "esp32_lora_wifi_node", "esp32_lora_node"}
FIELD_SENSOR_TYPES = {"field_sensor"}
MAX_ULTRASONIC_DISTANCE_CM = 2000.0


def sensor_profile(device: Device) -> str:
    normalized = (device.device_type or "").strip().lower()
    if normalized in FIELD_SENSOR_TYPES:
        return "field_sensor"
    return "silo_sensor"


def validate_device_unit_compatibility(device_type: str, operation_type: str) -> None:
    profile = "field_sensor" if device_type.strip().lower() == "field_sensor" else "silo_sensor"
    expected = "field" if profile == "field_sensor" else "storage"
    if operation_type != expected:
        label = "parcela/campo" if expected == "field" else "silo/almacenamiento"
        raise ValueError(f"El dispositivo solo puede registrarse en una unidad de tipo {label}.")


def calculate_level_percent(device: Device, distance_cm: float | None) -> float | None:
    if distance_cm is None:
        return None
    if not math.isfinite(distance_cm) or distance_cm <= 0 or distance_cm > MAX_ULTRASONIC_DISTANCE_CM:
        raise ValueError("La distancia ultrasonica esta fuera del rango fisico permitido.")
    empty = device.empty_distance_cm
    full = device.full_distance_cm
    if empty is None or full is None:
        return None
    if not math.isfinite(empty) or not math.isfinite(full) or empty <= full or full <= 0:
        raise ValueError("La calibracion del nivel no es valida.")
    raw = ((empty - distance_cm) / (empty - full)) * 100
    return round(max(0.0, min(100.0, raw)), 2)


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
