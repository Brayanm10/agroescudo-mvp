from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.device_templates import DEVICE_TEMPLATES, ChannelTemplate
from app.domain.metric_registry import (
    LEGACY_FIELD_MAPPING,
    METRIC_REGISTRY,
    METRICS_BY_CODE,
)
from app.models import Device, DeviceChannel, MetricDefinition, utc_now
from app.services.telemetry import sensor_profile


LEGACY_CAPABILITY_CHANNELS = {
    "grain_temperature": "grain_temp_1",
    "ambient_temperature": "ambient_temp_1",
    "ambient_humidity": "ambient_rh_1",
    "battery_voltage": "battery_1",
    "level_distance_cm": "level_ultrasonic_1",
    "level_percent": "level_ultrasonic_1",
    "soil_moisture_raw": "soil_moisture_1",
    "soil_moisture_percent": "soil_moisture_1",
}


def ensure_metric_registry(db: Session) -> None:
    existing = {
        item.metric_code: item
        for item in db.scalars(select(MetricDefinition)).all()
    }
    for specification in METRIC_REGISTRY:
        values = specification.as_record()
        definition = existing.get(specification.metric_code)
        if definition is None:
            db.add(MetricDefinition(**values))
            continue
        if definition.numeric_id != specification.numeric_id:
            raise ValueError(
                f"El ID numerico de {specification.metric_code} es inmutable."
            )
        for name, value in values.items():
            setattr(definition, name, value)
    db.flush()


def default_template_for_device(device: Device, capabilities: list[str] | None = None) -> str:
    if sensor_profile(device) == "field_sensor":
        return "CAMPO_SENSOR_BASE"
    requested = {item.strip().lower() for item in (capabilities or [])}
    if requested.intersection({"level_distance_cm", "level_percent", "level_ultrasonic_1"}):
        return "SILO_SENSOR_WITH_LEVEL"
    return "SILO_SENSOR_BASE"


def sync_device_channels(
    db: Session,
    device: Device,
    *,
    template_code: str | None = None,
    capabilities: list[str] | None = None,
) -> list[DeviceChannel]:
    selected_template = template_code or device.template_code or default_template_for_device(device, capabilities)
    if selected_template not in DEVICE_TEMPLATES:
        raise ValueError("Plantilla de dispositivo no reconocida.")
    profile = sensor_profile(device)
    if selected_template.startswith("CAMPO_") and profile != "field_sensor":
        raise ValueError("La plantilla CampoSensor requiere un dispositivo field_sensor.")
    if selected_template.startswith("SILO_") and profile != "silo_sensor":
        raise ValueError("La plantilla SiloSensor requiere un dispositivo silo_sensor.")

    definitions = {item["channel_key"]: item for item in DEVICE_TEMPLATES[selected_template]}
    requested_keys = {
        LEGACY_CAPABILITY_CHANNELS.get(item.strip().lower(), item.strip().lower())
        for item in (capabilities or [])
        if item.strip()
    }
    if requested_keys:
        # Required template channels remain present; optional channels follow the
        # explicit installation declaration.
        enabled_keys = {
            key
            for key, definition in definitions.items()
            if definition["required"] or key in requested_keys
        }
    else:
        enabled_keys = set(definitions)

    existing = {
        item.channel_key: item
        for item in db.scalars(select(DeviceChannel).where(DeviceChannel.device_id == device.id)).all()
    }
    changed = False
    for channel_key, definition in definitions.items():
        channel = existing.get(channel_key)
        should_enable = channel_key in enabled_keys
        if channel is None:
            channel = _channel_from_template(device.id, definition, should_enable)
            db.add(channel)
            changed = True
            continue
        values = _channel_values(definition, should_enable)
        for name, value in values.items():
            if getattr(channel, name) != value:
                setattr(channel, name, value)
                changed = True
        channel.updated_at = utc_now()

    device.template_code = selected_template
    if changed:
        device.capabilities_version = max(device.capabilities_version or 1, 1) + 1
    db.flush()
    return list(
        db.scalars(
            select(DeviceChannel)
            .where(DeviceChannel.device_id == device.id)
            .order_by(DeviceChannel.display_order, DeviceChannel.channel_key)
        ).all()
    )


def _channel_from_template(
    device_id: int,
    definition: ChannelTemplate,
    enabled: bool,
) -> DeviceChannel:
    values = _channel_values(definition, enabled)
    return DeviceChannel(
        device_id=device_id,
        code=definition["channel_key"],
        channel_key=definition["channel_key"],
        name=definition["display_name"],
        **values,
    )


def _channel_values(definition: ChannelTemplate, enabled: bool) -> dict[str, object]:
    primary = METRICS_BY_CODE[definition["metric_codes"][0]]
    return {
        "sensor_type": definition["sensor_type"],
        "hardware_port": definition["hardware_port"],
        "metric_type": primary.metric_code,
        "metric_codes": ",".join(definition["metric_codes"]),
        "unit": primary.canonical_unit,
        "canonical_unit": primary.canonical_unit,
        "is_active": enabled,
        "is_installed": enabled,
        "is_enabled": enabled,
        "is_required": definition["required"],
        "is_visible_to_client": definition["client_visible"],
        "chart_enabled": definition["chart_enabled"] and enabled,
        "alert_enabled": definition["alert_enabled"] and enabled,
        "calibration_required": definition["calibration_required"],
        "status": "CONFIGURED_NOT_SEEN" if enabled else "DISABLED",
        "display_name": definition["display_name"],
        "display_order": definition["display_order"],
    }


def channel_accepts_metric(channel: DeviceChannel, metric_code: str) -> bool:
    return metric_code in channel_metric_codes(channel)


def channel_metric_codes(channel: DeviceChannel) -> list[str]:
    """Return canonical codes without rewriting legacy channel metadata."""
    values = [
        item.strip()
        for item in (channel.metric_codes or channel.metric_type or "").split(",")
        if item.strip()
    ]
    candidates = values + [channel.code, channel.channel_key]
    canonical: list[str] = []
    for candidate in candidates:
        metric_code = (
            candidate
            if candidate in METRICS_BY_CODE
            else LEGACY_FIELD_MAPPING.get(candidate, (None, None))[1]
        )
        if metric_code and metric_code not in canonical:
            canonical.append(metric_code)
    return canonical
