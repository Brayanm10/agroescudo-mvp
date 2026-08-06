from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.metric_registry import METRICS_BY_CODE
from app.models import (
    Device,
    DeviceChannel,
    IotGateway,
    IotReading,
    MetricDefinition,
    MetricReading,
    SensorMetricValue,
    SensorReading,
    TelemetryEvent,
    utc_now,
)
from app.schemas import IotBatchReadingIn, IotMetricIn
from app.services.device_capabilities import channel_accepts_metric
from app.services.telemetry import sensor_profile


@dataclass(frozen=True, slots=True)
class IncomingMetric:
    channel_key: str
    metric_code: str
    raw_value: float
    unit: str
    quality: str


def validate_explicit_metrics(
    db: Session,
    device: Device,
    reading: IotBatchReadingIn,
) -> str | None:
    if not reading.metrics:
        return None
    channels = _channels_by_key(db, device.id)
    seen: set[tuple[str, str]] = set()
    profile_code = "CAMPO_SENSOR" if sensor_profile(device) == "field_sensor" else "SILO_SENSOR"
    for metric in reading.metrics:
        key = (metric.channel_key, metric.metric_code)
        if key in seen:
            return f"Metrica duplicada en el evento: {metric.channel_key}/{metric.metric_code}"
        seen.add(key)
        channel = channels.get(metric.channel_key)
        if channel is None:
            return f"Canal no registrado: {metric.channel_key}"
        if not channel.is_installed or not channel.is_enabled or channel.status in {"DISABLED", "RETIRED"}:
            return f"Canal no habilitado: {metric.channel_key}"
        definition = METRICS_BY_CODE.get(metric.metric_code)
        if definition is None:
            return f"Metrica no canonica: {metric.metric_code}"
        if definition.is_derived:
            return f"La metrica derivada {metric.metric_code} debe calcularse en backend"
        if not channel_accepts_metric(channel, metric.metric_code):
            return f"La metrica {metric.metric_code} no pertenece al canal {metric.channel_key}"
        if metric.unit != definition.canonical_unit:
            return (
                f"Unidad incompatible para {metric.metric_code}: "
                f"{metric.unit}; se esperaba {definition.canonical_unit}"
            )
        if profile_code not in definition.product_compatibility and "ALL" not in definition.product_compatibility:
            return f"La metrica {metric.metric_code} no es compatible con {profile_code}"
        if definition.physical_min is not None and metric.raw_value < definition.physical_min:
            return f"{metric.metric_code} fuera de rango fisico"
        if definition.physical_max is not None and metric.raw_value > definition.physical_max:
            return f"{metric.metric_code} fuera de rango fisico"
    return None


def apply_explicit_metrics_to_legacy(reading: IotBatchReadingIn) -> None:
    """Fill the compatibility projection without guessing positional meaning."""
    if not reading.metrics:
        return
    values = {metric.metric_code: metric.raw_value for metric in reading.metrics}
    if "GRAIN_TEMPERATURE_C" in values:
        reading.grain_temp_c_x100 = round(values["GRAIN_TEMPERATURE_C"] * 100)
    if "AMBIENT_TEMPERATURE_C" in values:
        reading.air_temp_c_x100 = round(values["AMBIENT_TEMPERATURE_C"] * 100)
    if "AMBIENT_RELATIVE_HUMIDITY_PCT" in values:
        reading.rh_x100 = round(values["AMBIENT_RELATIVE_HUMIDITY_PCT"] * 100)
    if "SOIL_MOISTURE_RAW" in values:
        reading.soil_moisture_raw = round(values["SOIL_MOISTURE_RAW"])
    if "LEVEL_DISTANCE_MM" in values:
        reading.level_distance_cm = values["LEVEL_DISTANCE_MM"] / 10
    if "BATTERY_VOLTAGE_MV" in values:
        reading.battery_mv = round(values["BATTERY_VOLTAGE_MV"])


def persist_normalized_telemetry(
    db: Session,
    *,
    gateway: IotGateway,
    device: Device,
    reading: IotBatchReadingIn,
    sensor_reading: SensorReading,
    iot_reading: IotReading,
) -> TelemetryEvent:
    incoming = explicit_or_legacy_metrics(reading)
    payload_hash = hashlib.sha256(
        json.dumps(
            {
                "device_id": str(reading.device_id),
                "boot_id": reading.boot_id,
                "sequence": reading.sequence,
                "metrics": [
                    {
                        "channel_key": item.channel_key,
                        "metric_code": item.metric_code,
                        "raw_value": item.raw_value,
                        "unit": item.unit,
                        "quality": item.quality,
                    }
                    for item in incoming
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    event = TelemetryEvent(
        company_id=device.company_id,
        storage_unit_id=device.storage_unit_id,
        device_id=device.id,
        gateway_id=gateway.id,
        sensor_reading_id=sensor_reading.id,
        iot_reading_id=iot_reading.id,
        boot_id=reading.boot_id,
        sequence=reading.sequence,
        sample_counter=reading.sample_counter,
        sampled_at=sensor_reading.timestamp,
        received_at_gateway=None,
        received_at_cloud=utc_now(),
        time_quality=str(reading.time_quality),
        firmware_version=str(reading.firmware_version),
        protocol_version=reading.protocol_version,
        capabilities_version=reading.capabilities_version,
        sensor_status_flags=reading.sensor_status,
        raw_payload_hash=payload_hash,
        quality_summary="VALID" if reading.metrics else "LEGACY_PROJECTED",
    )
    db.add(event)
    db.flush()

    channels = _channels_by_key(db, device.id)
    definitions = {
        item.metric_code: item
        for item in db.scalars(select(MetricDefinition)).all()
    }
    persisted: set[tuple[str, str]] = set()
    for item in incoming:
        channel = channels.get(item.channel_key)
        definition = definitions.get(item.metric_code)
        if channel is None or definition is None or not channel_accepts_metric(channel, item.metric_code):
            event.quality_summary = "LEGACY_UNMAPPED"
            continue
        display_value = _compatibility_display_value(sensor_reading, item.metric_code, item.raw_value)
        db.add(
            MetricReading(
                telemetry_event_id=event.id,
                company_id=device.company_id,
                storage_unit_id=device.storage_unit_id,
                device_id=device.id,
                sensor_channel_id=channel.id,
                metric_definition_id=definition.id,
                metric_code=item.metric_code,
                raw_value=item.raw_value,
                calibrated_value=display_value if display_value != item.raw_value else None,
                display_value=display_value,
                canonical_unit=item.unit,
                quality_status=item.quality,
                sampled_at=sensor_reading.timestamp,
                received_at=sensor_reading.received_at,
            )
        )
        persisted.add((item.channel_key, item.metric_code))
        channel.last_valid_reading_at = sensor_reading.timestamp
        channel.status = "ACTIVE" if item.quality == "VALID" else "SENSOR_FAULT"

    _persist_derived_metrics(
        db,
        event=event,
        device=device,
        sensor_reading=sensor_reading,
        channels=channels,
        definitions=definitions,
        persisted=persisted,
    )
    return event


def explicit_or_legacy_metrics(reading: IotBatchReadingIn) -> list[IncomingMetric]:
    if reading.metrics:
        return [_from_explicit(item) for item in reading.metrics]
    metrics: list[IncomingMetric] = []
    _append_scaled(metrics, "grain_temp_1", "GRAIN_TEMPERATURE_C", reading.grain_temp_c_x100, 100, "degC")
    _append_scaled(metrics, "ambient_temp_1", "AMBIENT_TEMPERATURE_C", reading.air_temp_c_x100, 100, "degC")
    _append_scaled(metrics, "ambient_rh_1", "AMBIENT_RELATIVE_HUMIDITY_PCT", reading.rh_x100, 100, "percent")
    _append_scaled(metrics, "battery_1", "BATTERY_VOLTAGE_MV", reading.battery_mv, 1, "mV")
    _append_scaled(metrics, "soil_moisture_1", "SOIL_MOISTURE_RAW", reading.soil_moisture_raw, 1, "ADC_RAW")
    if reading.level_distance_cm is not None:
        metrics.append(
            IncomingMetric(
                "level_ultrasonic_1",
                "LEVEL_DISTANCE_MM",
                reading.level_distance_cm * 10,
                "mm",
                "VALID",
            )
        )
    return metrics


def _persist_derived_metrics(
    db: Session,
    *,
    event: TelemetryEvent,
    device: Device,
    sensor_reading: SensorReading,
    channels: dict[str, DeviceChannel],
    definitions: dict[str, MetricDefinition],
    persisted: set[tuple[str, str]],
) -> None:
    derived = (
        (
            "level_ultrasonic_1",
            "LEVEL_PERCENT",
            sensor_reading.level_percent,
            "LEVEL_DISTANCE_MM",
            "level_percent",
        ),
        (
            "soil_moisture_1",
            "SOIL_MOISTURE_PCT",
            sensor_reading.soil_moisture_percent,
            "SOIL_MOISTURE_RAW",
            "soil_moisture_percent",
        ),
    )
    for channel_key, metric_code, value, source_code, legacy_variable in derived:
        if value is None or (channel_key, metric_code) in persisted:
            continue
        channel = channels.get(channel_key)
        definition = definitions.get(metric_code)
        if channel is None or definition is None or not channel_accepts_metric(channel, metric_code):
            continue
        calibration_value = db.scalar(
            select(SensorMetricValue).where(
                SensorMetricValue.sensor_reading_id == sensor_reading.id,
                SensorMetricValue.variable_type == legacy_variable,
            )
        )
        db.add(
            MetricReading(
                telemetry_event_id=event.id,
                company_id=device.company_id,
                storage_unit_id=device.storage_unit_id,
                device_id=device.id,
                sensor_channel_id=channel.id,
                metric_definition_id=definition.id,
                calibration_id=calibration_value.calibration_id if calibration_value else None,
                metric_code=metric_code,
                raw_value=calibration_value.raw_value if calibration_value else value,
                calibrated_value=value,
                display_value=value,
                canonical_unit=definition.canonical_unit,
                quality_status=calibration_value.quality_status.upper() if calibration_value else "DERIVED",
                calibration_version=(
                    calibration_value.calibration_version_applied if calibration_value else None
                ),
                source_metric_code=source_code,
                derivation_version="p1.5-v1",
                sampled_at=sensor_reading.timestamp,
                received_at=sensor_reading.received_at,
            )
        )


def _channels_by_key(db: Session, device_id: int) -> dict[str, DeviceChannel]:
    return {
        item.channel_key: item
        for item in db.scalars(select(DeviceChannel).where(DeviceChannel.device_id == device_id)).all()
    }


def _compatibility_display_value(
    reading: SensorReading,
    metric_code: str,
    raw_value: float,
) -> float:
    mapping = {
        "GRAIN_TEMPERATURE_C": reading.grain_temperature,
        "AMBIENT_TEMPERATURE_C": reading.ambient_temperature,
        "AMBIENT_RELATIVE_HUMIDITY_PCT": reading.ambient_humidity,
        "SOIL_MOISTURE_PCT": reading.soil_moisture_percent,
        "LEVEL_DISTANCE_MM": reading.level_distance_cm * 10 if reading.level_distance_cm is not None else None,
        "LEVEL_PERCENT": reading.level_percent,
        "BATTERY_VOLTAGE_MV": reading.battery_voltage * 1000 if reading.battery_voltage is not None else None,
    }
    value = mapping.get(metric_code)
    return raw_value if value is None else float(value)


def _from_explicit(metric: IotMetricIn) -> IncomingMetric:
    return IncomingMetric(
        metric.channel_key,
        metric.metric_code,
        metric.raw_value,
        metric.unit,
        metric.quality,
    )


def _append_scaled(
    result: list[IncomingMetric],
    channel_key: str,
    metric_code: str,
    value: int | None,
    divisor: int,
    unit: str,
) -> None:
    if value is not None:
        result.append(IncomingMetric(channel_key, metric_code, value / divisor, unit, "VALID"))
