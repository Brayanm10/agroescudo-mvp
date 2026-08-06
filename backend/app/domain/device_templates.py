from __future__ import annotations

from typing import Final, TypedDict


class ChannelTemplate(TypedDict):
    channel_key: str
    sensor_type: str
    hardware_port: str
    metric_codes: tuple[str, ...]
    required: bool
    client_visible: bool
    chart_enabled: bool
    alert_enabled: bool
    calibration_required: bool
    display_name: str
    display_order: int


BASE_AMBIENT: Final[tuple[ChannelTemplate, ...]] = (
    {
        "channel_key": "ambient_temp_1",
        "sensor_type": "SHT31",
        "hardware_port": "I2C:SDA21:SCL22",
        "metric_codes": ("AMBIENT_TEMPERATURE_C",),
        "required": True,
        "client_visible": True,
        "chart_enabled": True,
        "alert_enabled": True,
        "calibration_required": False,
        "display_name": "Temperatura ambiente",
        "display_order": 20,
    },
    {
        "channel_key": "ambient_rh_1",
        "sensor_type": "SHT31",
        "hardware_port": "I2C:SDA21:SCL22",
        "metric_codes": ("AMBIENT_RELATIVE_HUMIDITY_PCT",),
        "required": True,
        "client_visible": True,
        "chart_enabled": True,
        "alert_enabled": True,
        "calibration_required": False,
        "display_name": "Humedad ambiente",
        "display_order": 30,
    },
    {
        "channel_key": "battery_1",
        "sensor_type": "BATTERY_ADC",
        "hardware_port": "BOARD_BATTERY_ADC",
        "metric_codes": ("BATTERY_VOLTAGE_MV", "BATTERY_PERCENT"),
        "required": True,
        "client_visible": True,
        "chart_enabled": True,
        "alert_enabled": True,
        "calibration_required": False,
        "display_name": "Bateria",
        "display_order": 80,
    },
)

DEVICE_TEMPLATES: Final[dict[str, tuple[ChannelTemplate, ...]]] = {
    "SILO_SENSOR_BASE": (
        {
            "channel_key": "grain_temp_1",
            "sensor_type": "DS18B20",
            "hardware_port": "ONEWIRE:GPIO4",
            "metric_codes": ("GRAIN_TEMPERATURE_C",),
            "required": True,
            "client_visible": True,
            "chart_enabled": True,
            "alert_enabled": True,
            "calibration_required": False,
            "display_name": "Temperatura de grano",
            "display_order": 10,
        },
        *BASE_AMBIENT,
    ),
    "SILO_SENSOR_WITH_LEVEL": (
        {
            "channel_key": "grain_temp_1",
            "sensor_type": "DS18B20",
            "hardware_port": "ONEWIRE:GPIO4",
            "metric_codes": ("GRAIN_TEMPERATURE_C",),
            "required": True,
            "client_visible": True,
            "chart_enabled": True,
            "alert_enabled": True,
            "calibration_required": False,
            "display_name": "Temperatura de grano",
            "display_order": 10,
        },
        *BASE_AMBIENT,
        {
            "channel_key": "level_ultrasonic_1",
            "sensor_type": "JSN_SR04T",
            "hardware_port": "TRIG:GPIO32:ECHO:GPIO33_LEVEL_SHIFTED",
            "metric_codes": ("LEVEL_DISTANCE_MM", "LEVEL_PERCENT"),
            "required": False,
            "client_visible": True,
            "chart_enabled": True,
            "alert_enabled": True,
            "calibration_required": True,
            "display_name": "Nivel estimado",
            "display_order": 60,
        },
    ),
    "CAMPO_SENSOR_BASE": (
        {
            "channel_key": "soil_moisture_1",
            "sensor_type": "ANALOG_SOIL",
            "hardware_port": "ADC1:GPIO32",
            "metric_codes": ("SOIL_MOISTURE_RAW", "SOIL_MOISTURE_PCT"),
            "required": True,
            "client_visible": True,
            "chart_enabled": True,
            "alert_enabled": True,
            "calibration_required": True,
            "display_name": "Humedad de suelo",
            "display_order": 10,
        },
        *BASE_AMBIENT,
    ),
}
