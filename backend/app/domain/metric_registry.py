from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Final, Literal


REGISTRY_VERSION: Final[int] = 1

ProductCode = Literal["SILO_SENSOR", "CAMPO_SENSOR", "GATEWAY", "ALL"]


@dataclass(frozen=True, slots=True)
class MetricSpec:
    numeric_id: int
    metric_code: str
    display_name: str
    description: str
    canonical_unit: str
    storage_type: str
    scale_factor: float
    physical_min: float | None
    physical_max: float | None
    default_decimals: int
    default_chart_type: str
    product_compatibility: tuple[ProductCode, ...]
    client_visibility: bool
    is_derived: bool
    calibration_method: str | None
    alert_supported: bool
    display_order: int

    def as_record(self) -> dict[str, object]:
        record = asdict(self)
        record["product_compatibility"] = ",".join(self.product_compatibility)
        record["registry_version"] = REGISTRY_VERSION
        return record


METRIC_REGISTRY: Final[tuple[MetricSpec, ...]] = (
    MetricSpec(1, "GRAIN_TEMPERATURE_C", "Temperatura de grano", "Temperatura interna de la masa almacenada.", "degC", "float", 0.01, -40, 100, 2, "line", ("SILO_SENSOR",), True, False, "OFFSET", True, 10),
    MetricSpec(2, "AMBIENT_TEMPERATURE_C", "Temperatura ambiente", "Temperatura del aire en el punto monitoreado.", "degC", "float", 0.01, -40, 80, 2, "line", ("SILO_SENSOR", "CAMPO_SENSOR"), True, False, "OFFSET", True, 20),
    MetricSpec(3, "AMBIENT_RELATIVE_HUMIDITY_PCT", "Humedad ambiente", "Humedad relativa ambiental.", "percent", "float", 0.01, 0, 100, 2, "line", ("SILO_SENSOR", "CAMPO_SENSOR"), True, False, "OFFSET", True, 30),
    MetricSpec(4, "SOIL_MOISTURE_RAW", "Humedad de suelo raw", "Lectura cruda ADC del sensor de suelo.", "ADC_RAW", "integer", 1, 0, 4095, 0, "line", ("CAMPO_SENSOR",), False, False, None, False, 40),
    MetricSpec(5, "SOIL_MOISTURE_PCT", "Humedad de suelo", "Porcentaje derivado desde lectura ADC calibrada.", "percent", "float", 0.01, 0, 100, 1, "line", ("CAMPO_SENSOR",), True, True, "LINEAR_TWO_POINT", True, 50),
    MetricSpec(6, "LEVEL_DISTANCE_MM", "Distancia de nivel", "Distancia del sensor a la superficie del producto.", "mm", "float", 1, 20, 20000, 0, "line", ("SILO_SENSOR",), True, False, "LEVEL_GEOMETRY", True, 60),
    MetricSpec(7, "LEVEL_PERCENT", "Nivel estimado", "Altura ocupada derivada de la geometria configurada.", "percent", "float", 0.01, 0, 100, 1, "area", ("SILO_SENSOR",), True, True, "LEVEL_GEOMETRY", True, 70),
    MetricSpec(8, "BATTERY_VOLTAGE_MV", "Voltaje de bateria", "Tension medida en milivoltios.", "mV", "integer", 1, 0, 6000, 0, "line", ("SILO_SENSOR", "CAMPO_SENSOR", "GATEWAY"), True, False, None, True, 80),
    MetricSpec(9, "BATTERY_PERCENT", "Bateria estimada", "Porcentaje derivado mediante curva de descarga configurada.", "percent", "float", 0.01, 0, 100, 0, "line", ("SILO_SENSOR", "CAMPO_SENSOR", "GATEWAY"), True, True, "BATTERY_CURVE", True, 90),
    MetricSpec(10, "SIGNAL_RSSI_DBM", "RSSI", "Potencia de senal recibida por el gateway.", "dBm", "integer", 1, -160, 20, 0, "line", ("GATEWAY",), False, False, None, True, 100),
    MetricSpec(11, "SIGNAL_SNR_DB", "SNR", "Relacion senal a ruido observada por el gateway.", "dB", "float", 0.1, -40, 30, 1, "line", ("GATEWAY",), False, False, None, True, 110),
    MetricSpec(12, "DEVICE_INTERNAL_TEMPERATURE_C", "Temperatura interna del nodo", "Temperatura interna, solo cuando existe un sensor fisico.", "degC", "float", 0.01, -40, 125, 2, "line", ("SILO_SENSOR", "CAMPO_SENSOR", "GATEWAY"), False, False, "OFFSET", True, 120),
    MetricSpec(13, "GATEWAY_QUEUE_SIZE", "Cola del gateway", "Cantidad de eventos pendientes de entrega.", "count", "integer", 1, 0, None, 0, "bar", ("GATEWAY",), False, False, None, True, 130),
    MetricSpec(14, "SENSOR_STATUS_FLAGS", "Estado de sensores", "Mascara de estados reportados por el nodo.", "flags", "integer", 1, 0, 65535, 0, "status", ("SILO_SENSOR", "CAMPO_SENSOR"), False, False, None, True, 140),
    MetricSpec(15, "TIME_QUALITY", "Calidad temporal", "Fuente y confiabilidad del timestamp.", "code", "integer", 1, 0, 255, 0, "status", ("SILO_SENSOR", "CAMPO_SENSOR", "GATEWAY"), False, False, None, False, 150),
)

METRICS_BY_CODE: Final = {item.metric_code: item for item in METRIC_REGISTRY}
METRICS_BY_ID: Final = {item.numeric_id: item for item in METRIC_REGISTRY}

if len(METRICS_BY_CODE) != len(METRIC_REGISTRY) or len(METRICS_BY_ID) != len(METRIC_REGISTRY):
    raise RuntimeError("El registro canonico contiene IDs o codigos duplicados.")


LEGACY_FIELD_MAPPING: Final[dict[str, tuple[str, str]]] = {
    "grain_temperature": ("grain_temp_1", "GRAIN_TEMPERATURE_C"),
    "grain_temp_c_x100": ("grain_temp_1", "GRAIN_TEMPERATURE_C"),
    "ambient_temperature": ("ambient_temp_1", "AMBIENT_TEMPERATURE_C"),
    "air_temp_c_x100": ("ambient_temp_1", "AMBIENT_TEMPERATURE_C"),
    "ambient_humidity": ("ambient_rh_1", "AMBIENT_RELATIVE_HUMIDITY_PCT"),
    "rh_x100": ("ambient_rh_1", "AMBIENT_RELATIVE_HUMIDITY_PCT"),
    "soil_moisture_raw": ("soil_moisture_1", "SOIL_MOISTURE_RAW"),
    "soil_moisture_percent": ("soil_moisture_1", "SOIL_MOISTURE_PCT"),
    "soil_moisture_x100": ("soil_moisture_1", "SOIL_MOISTURE_PCT"),
    "level_distance_cm": ("level_ultrasonic_1", "LEVEL_DISTANCE_MM"),
    "level_distance_mm": ("level_ultrasonic_1", "LEVEL_DISTANCE_MM"),
    "level_percent": ("level_ultrasonic_1", "LEVEL_PERCENT"),
    "level_percent_x100": ("level_ultrasonic_1", "LEVEL_PERCENT"),
    "battery_voltage": ("battery_1", "BATTERY_VOLTAGE_MV"),
    "battery_mv": ("battery_1", "BATTERY_VOLTAGE_MV"),
    "signal_quality": ("radio_link_1", "SIGNAL_RSSI_DBM"),
    "rssi_dbm": ("radio_link_1", "SIGNAL_RSSI_DBM"),
    "snr_db_x10": ("radio_link_1", "SIGNAL_SNR_DB"),
    "sensor_status": ("status_1", "SENSOR_STATUS_FLAGS"),
    "time_quality": ("time_1", "TIME_QUALITY"),
}

# These fields are preserved for human mapping. They must never be inferred as
# another canonical metric merely because they share a physical unit.
AMBIGUOUS_LEGACY_FIELDS: Final[tuple[str, ...]] = (
    "soil_temperature_c",
    "soil_temp_c_x100",
)
