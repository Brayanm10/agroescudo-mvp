from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device, ThresholdConfig
from app.schemas import ThresholdsIn, ThresholdsOut

METRIC_MAP = {
    "max_grain_temperature": ("grain_temperature", ">", "warning"),
    "max_ambient_humidity": ("ambient_humidity", ">", "warning"),
    "min_battery_voltage": ("battery_voltage", "<", "technical"),
    "critical_temperature": ("critical_temperature", ">", "critical"),
    "critical_humidity": ("critical_humidity", ">", "critical"),
}

DEFAULT_THRESHOLDS = {
    "max_grain_temperature": 30.0,
    "max_ambient_humidity": 70.0,
    "min_battery_voltage": 3.5,
    "critical_temperature": 30.0,
    "critical_humidity": 70.0,
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
                metric=metric,
                operator=operator,
                value=getattr(payload, field_name),
                severity=severity,
            )
            db.add(config)
        else:
            config.operator = operator
            config.value = getattr(payload, field_name)
            config.severity = severity
            config.is_active = True

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
