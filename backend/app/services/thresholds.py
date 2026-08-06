from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device, DeviceChannel, MetricDefinition, ThresholdConfig
from app.schemas import ThresholdsIn, ThresholdsOut

METRIC_MAP = {
    "max_grain_temperature": ("grain_temperature", ">", "warning"),
    "max_ambient_humidity": ("ambient_humidity", ">", "warning"),
    "min_battery_voltage": ("battery_voltage", "<", "technical"),
    "critical_temperature": ("critical_temperature", ">", "critical"),
    "critical_humidity": ("critical_humidity", ">", "critical"),
    "min_level_percent": ("level_percent_low", "<", "warning"),
    "max_level_percent": ("level_percent_high", ">", "warning"),
    "min_soil_moisture_percent": ("soil_moisture_low", "<", "warning"),
    "max_soil_moisture_percent": ("soil_moisture_high", ">", "warning"),
}

THRESHOLD_METRIC_SCOPE = {
    "grain_temperature": ("grain_temp_1", "GRAIN_TEMPERATURE_C"),
    "ambient_humidity": ("ambient_rh_1", "AMBIENT_RELATIVE_HUMIDITY_PCT"),
    "battery_voltage": ("battery_1", "BATTERY_VOLTAGE_MV"),
    "level_percent_low": ("level_ultrasonic_1", "LEVEL_PERCENT"),
    "level_percent_high": ("level_ultrasonic_1", "LEVEL_PERCENT"),
    "soil_moisture_low": ("soil_moisture_1", "SOIL_MOISTURE_PCT"),
    "soil_moisture_high": ("soil_moisture_1", "SOIL_MOISTURE_PCT"),
}

DEFAULT_THRESHOLDS = {
    "max_grain_temperature": 30.0,
    "max_ambient_humidity": 70.0,
    "min_battery_voltage": 3.5,
    "critical_temperature": 30.0,
    "critical_humidity": 70.0,
    "min_level_percent": None,
    "max_level_percent": None,
    "min_soil_moisture_percent": None,
    "max_soil_moisture_percent": None,
}


def get_device_thresholds(db: Session, device: Device) -> ThresholdsOut:
    values = DEFAULT_THRESHOLDS.copy()
    configs = _load_configs(db, device)
    for field_name, (metric, _operator, _severity) in METRIC_MAP.items():
        config = _resolve_config(configs, metric, device.storage_unit_id)
        if config is not None:
            values[field_name] = config.value

    return ThresholdsOut(device_id=device.id, **values)


def upsert_device_thresholds(db: Session, device: Device, payload: ThresholdsIn) -> ThresholdsOut:
    for field_name, (metric, operator, severity) in METRIC_MAP.items():
        value = getattr(payload, field_name)
        if value is None:
            continue
        config = db.scalar(
            select(ThresholdConfig).where(
                ThresholdConfig.company_id == device.company_id,
                ThresholdConfig.storage_unit_id == device.storage_unit_id,
                ThresholdConfig.metric == metric,
            )
        )
        if config is None:
            config = ThresholdConfig(
                company_id=device.company_id,
                site_id=device.site_id,
                storage_unit_id=device.storage_unit_id,
                device_id=device.id,
                metric=metric,
                operator=operator,
                value=value,
                severity=severity,
            )
            db.add(config)
        else:
            config.operator = operator
            config.value = value
            config.severity = severity
            config.is_active = True
            config.device_id = device.id
        scope = THRESHOLD_METRIC_SCOPE.get(metric)
        if scope is not None:
            channel_key, metric_code = scope
            channel = db.scalar(
                select(DeviceChannel).where(
                    DeviceChannel.device_id == device.id,
                    DeviceChannel.channel_key == channel_key,
                )
            )
            definition = db.scalar(
                select(MetricDefinition).where(MetricDefinition.metric_code == metric_code)
            )
            config.sensor_channel_id = channel.id if channel else None
            config.metric_definition_id = definition.id if definition else None

    db.flush()
    return get_device_thresholds(db, device)


def _load_configs(db: Session, device: Device) -> list[ThresholdConfig]:
    return list(
        db.scalars(
            select(ThresholdConfig).where(
                ThresholdConfig.company_id == device.company_id,
                ThresholdConfig.is_active.is_(True),
            )
        ).all()
    )


def _resolve_config(
    configs: list[ThresholdConfig],
    metric: str,
    storage_unit_id: int,
) -> ThresholdConfig | None:
    unit_config = next(
        (config for config in configs if config.metric == metric and config.storage_unit_id == storage_unit_id),
        None,
    )
    if unit_config is not None:
        return unit_config

    return next(
        (config for config in configs if config.metric == metric and config.storage_unit_id is None),
        None,
    )
