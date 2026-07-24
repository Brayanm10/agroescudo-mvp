from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Alert, Device, SensorReading, ThresholdConfig

GRAIN_TEMPERATURE_HIGH = "grain_temperature_high"
AMBIENT_HUMIDITY_HIGH = "ambient_humidity_high"
CRITICAL_ENVIRONMENT = "critical_environment"
BATTERY_LOW = "battery_low"
LEVEL_LOW = "level_low"
LEVEL_HIGH = "level_high"
LEVEL_DISTANCE_OUT_OF_RANGE = "level_distance_out_of_range"
SOIL_MOISTURE_LOW = "soil_moisture_low"
SOIL_MOISTURE_HIGH = "soil_moisture_high"


@dataclass(frozen=True)
class ThresholdSet:
    grain_temperature_high: float | None = None
    ambient_humidity_high: float | None = None
    battery_low: float = 3.5
    critical_temperature: float | None = None
    critical_humidity: float | None = None
    level_low: float | None = None
    level_high: float | None = None
    soil_moisture_low: float | None = None
    soil_moisture_high: float | None = None


def evaluate_alerts(db: Session, device: Device, reading: SensorReading) -> list[Alert]:
    thresholds = _load_thresholds(db, device)
    alert_specs = _build_alert_specs(reading, thresholds)
    alerts: list[Alert] = []

    for spec in alert_specs:
        alerts.append(_get_or_create_active_alert(db, device, reading, **spec))

    return alerts


def _load_thresholds(db: Session, device: Device) -> ThresholdSet:
    configs = db.scalars(
        select(ThresholdConfig).where(
            ThresholdConfig.company_id == device.company_id,
            ThresholdConfig.is_active.is_(True),
        )
    ).all()

    grain_temperature_high = _resolve_threshold(configs, "grain_temperature", device.storage_unit_id)
    ambient_humidity_high = _resolve_threshold(configs, "ambient_humidity", device.storage_unit_id)
    battery_low = _resolve_threshold(configs, "battery_voltage", device.storage_unit_id) or 3.5
    critical_temperature = (
        _resolve_threshold(configs, "critical_temperature", device.storage_unit_id) or grain_temperature_high
    )
    critical_humidity = _resolve_threshold(configs, "critical_humidity", device.storage_unit_id) or ambient_humidity_high
    level_low = _resolve_threshold(configs, "level_percent_low", device.storage_unit_id)
    level_high = _resolve_threshold(configs, "level_percent_high", device.storage_unit_id)
    soil_moisture_low = _resolve_threshold(configs, "soil_moisture_low", device.storage_unit_id)
    soil_moisture_high = _resolve_threshold(configs, "soil_moisture_high", device.storage_unit_id)

    return ThresholdSet(
        grain_temperature_high=grain_temperature_high,
        ambient_humidity_high=ambient_humidity_high,
        battery_low=battery_low,
        critical_temperature=critical_temperature,
        critical_humidity=critical_humidity,
        level_low=level_low,
        level_high=level_high,
        soil_moisture_low=soil_moisture_low,
        soil_moisture_high=soil_moisture_high,
    )


def _resolve_threshold(configs: list[ThresholdConfig], metric: str, storage_unit_id: int) -> float | None:
    unit_config = next(
        (config for config in configs if config.metric == metric and config.storage_unit_id == storage_unit_id),
        None,
    )
    if unit_config is not None:
        return unit_config.value

    company_config = next(
        (config for config in configs if config.metric == metric and config.storage_unit_id is None),
        None,
    )
    return company_config.value if company_config is not None else None


def _build_alert_specs(reading: SensorReading, thresholds: ThresholdSet) -> list[dict]:
    grain_high = (
        thresholds.grain_temperature_high is not None
        and reading.grain_temperature is not None
        and reading.grain_temperature > thresholds.grain_temperature_high
    )
    humidity_high = (
        thresholds.ambient_humidity_high is not None
        and reading.ambient_humidity is not None
        and reading.ambient_humidity > thresholds.ambient_humidity_high
    )
    critical_environment = (
        thresholds.critical_temperature is not None
        and thresholds.critical_humidity is not None
        and reading.grain_temperature is not None
        and reading.ambient_humidity is not None
        and reading.grain_temperature > thresholds.critical_temperature
        and reading.ambient_humidity > thresholds.critical_humidity
    )
    battery_low = reading.battery_voltage is not None and reading.battery_voltage < thresholds.battery_low

    specs: list[dict[str, str]] = []
    if critical_environment:
        specs.append(
            {
                "alert_type": CRITICAL_ENVIRONMENT,
                "severity": "critical",
                "title": "Riesgo critico de conservacion",
                "message": "Temperatura de grano y humedad ambiental superan los umbrales configurados.",
                "metric": "critical_environment",
                "observed_value": None,
                "threshold_value": None,
            }
        )
    else:
        if grain_high:
            specs.append(
                {
                    "alert_type": GRAIN_TEMPERATURE_HIGH,
                    "severity": "warning",
                    "title": "Temperatura de grano elevada",
                    "message": "La temperatura de grano supera el umbral configurado.",
                    "metric": "grain_temperature",
                    "observed_value": reading.grain_temperature,
                    "threshold_value": thresholds.grain_temperature_high,
                }
            )
        if humidity_high:
            specs.append(
                {
                    "alert_type": AMBIENT_HUMIDITY_HIGH,
                    "severity": "warning",
                    "title": "Humedad ambiental elevada",
                    "message": "La humedad ambiental supera el umbral configurado.",
                    "metric": "ambient_humidity",
                    "observed_value": reading.ambient_humidity,
                    "threshold_value": thresholds.ambient_humidity_high,
                }
            )

    if battery_low:
        specs.append(
            {
                "alert_type": BATTERY_LOW,
                "severity": "technical",
                "title": "Bateria baja del dispositivo",
                "message": "El voltaje de bateria esta por debajo del umbral configurado.",
                "metric": "battery_voltage",
                "observed_value": reading.battery_voltage,
                "threshold_value": thresholds.battery_low,
            }
        )

    if reading.level_percent is not None and thresholds.level_low is not None and reading.level_percent < thresholds.level_low:
        specs.append({
            "alert_type": LEVEL_LOW,
            "severity": "warning",
            "title": "Nivel estimado bajo",
            "message": "La altura ocupada estimada esta por debajo del umbral configurado.",
            "metric": "level_percent",
            "observed_value": reading.level_percent,
            "threshold_value": thresholds.level_low,
        })
    if reading.level_percent is not None and thresholds.level_high is not None and reading.level_percent > thresholds.level_high:
        specs.append({
            "alert_type": LEVEL_HIGH,
            "severity": "warning",
            "title": "Nivel estimado alto",
            "message": "La altura ocupada estimada supera el umbral configurado.",
            "metric": "level_percent",
            "observed_value": reading.level_percent,
            "threshold_value": thresholds.level_high,
        })
    if (
        reading.soil_moisture_percent is not None
        and thresholds.soil_moisture_low is not None
        and reading.soil_moisture_percent < thresholds.soil_moisture_low
    ):
        specs.append({
            "alert_type": SOIL_MOISTURE_LOW,
            "severity": "warning",
            "title": "Humedad de suelo por debajo del rango",
            "message": "La humedad del suelo esta por debajo del umbral configurado.",
            "metric": "soil_moisture_percent",
            "observed_value": reading.soil_moisture_percent,
            "threshold_value": thresholds.soil_moisture_low,
        })
    if (
        reading.soil_moisture_percent is not None
        and thresholds.soil_moisture_high is not None
        and reading.soil_moisture_percent > thresholds.soil_moisture_high
    ):
        specs.append({
            "alert_type": SOIL_MOISTURE_HIGH,
            "severity": "warning",
            "title": "Humedad de suelo por encima del rango",
            "message": "La humedad del suelo supera el umbral configurado.",
            "metric": "soil_moisture_percent",
            "observed_value": reading.soil_moisture_percent,
            "threshold_value": thresholds.soil_moisture_high,
        })
    device = reading.device
    if (
        reading.level_distance_cm is not None
        and device is not None
        and device.empty_distance_cm is not None
        and device.full_distance_cm is not None
        and not device.full_distance_cm <= reading.level_distance_cm <= device.empty_distance_cm
    ):
        specs.append({
            "alert_type": LEVEL_DISTANCE_OUT_OF_RANGE,
            "severity": "technical",
            "title": "Distancia ultrasonica fuera de calibracion",
            "message": "La distancia medida esta fuera del intervalo calibrado del nodo.",
            "metric": "level_distance_cm",
            "observed_value": reading.level_distance_cm,
            "threshold_value": device.empty_distance_cm,
        })

    return specs


def _get_or_create_active_alert(
    db: Session,
    device: Device,
    reading: SensorReading,
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    metric: str | None = None,
    observed_value: float | None = None,
    threshold_value: float | None = None,
) -> Alert:
    existing = db.scalar(
        select(Alert).where(
            Alert.device_id == device.id,
            Alert.alert_type == alert_type,
            Alert.is_active.is_(True),
        )
    )
    if existing is not None:
        existing._was_created = False
        return existing

    alert = Alert(
        company_id=device.company_id,
        site_id=device.site_id,
        storage_unit_id=device.storage_unit_id,
        device_id=device.id,
        reading_id=reading.id,
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        metric=metric,
        observed_value=observed_value,
        threshold_value=threshold_value,
    )
    db.add(alert)
    db.flush()
    alert._was_created = True
    return alert
