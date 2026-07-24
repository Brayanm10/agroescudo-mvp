from datetime import datetime
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1)


def _validate_new_password(value: str) -> str:
    if len(value) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    if not any(char.isalpha() for char in value):
        raise ValueError("La contraseña debe incluir al menos una letra.")
    if not any(char.isdigit() for char in value):
        raise ValueError("La contraseña debe incluir al menos un numero.")
    return value


class UserProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    phone_whatsapp: str | None = Field(default=None, max_length=80)
    telegram_chat_id: str | None = Field(default=None, max_length=120)
    receives_alerts: bool | None = None
    language: str | None = Field(default=None, min_length=2, max_length=10)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)


class ChangePasswordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)
    confirm_password: str = Field(min_length=8)

    @field_validator("new_password")
    @classmethod
    def validate_strength(cls, value: str) -> str:
        return _validate_new_password(value)


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    tax_id: str | None = Field(default=None, max_length=64)
    type: str = Field(default="acopiador", min_length=1, max_length=40)
    city: str | None = Field(default=None, max_length=120)
    contact_name: str | None = Field(default=None, max_length=160)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=80)


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    tax_id: str | None = Field(default=None, max_length=64)
    type: str | None = Field(default=None, min_length=1, max_length=40)
    city: str | None = Field(default=None, max_length=120)
    contact_name: str | None = Field(default=None, max_length=160)
    contact_email: str | None = Field(default=None, max_length=255)
    contact_phone: str | None = Field(default=None, max_length=80)
    is_active: bool | None = None


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    tax_id: str | None = None
    type: str = "acopiador"
    city: str | None = None
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    is_active: bool = True
    approval_status: str = "APPROVED"
    approved_at: datetime | None = None
    approved_by_id: int | None = None
    rejection_reason: str | None = None
    created_at: datetime
    updated_at: datetime | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int | None = None
    email: str
    full_name: str
    role: str
    is_active: bool
    status: str = "ACTIVE"
    locale: str = "es"
    email_verified_at: datetime | None = None
    password_changed_at: datetime | None = None
    phone_whatsapp: str | None = None
    telegram_chat_id: str | None = None
    receives_alerts: bool = True
    language: str = "es"
    timezone: str = "America/La_Paz"
    created_at: datetime
    updated_at: datetime | None = None
    last_login_at: datetime | None = None
    last_seen_at: datetime | None = None
    company: CompanyOut | None = None


class UserCreate(BaseModel):
    company_id: int | None = None
    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=8)
    role: Literal["admin", "technician", "client"]
    phone_whatsapp: str | None = Field(default=None, max_length=80)
    telegram_chat_id: str | None = Field(default=None, max_length=120)
    receives_alerts: bool = True
    storage_unit_ids: list[int] = []

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_new_password(value)


class UserUpdate(BaseModel):
    company_id: int | None = None
    email: str | None = Field(default=None, min_length=3, max_length=255)
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    role: Literal["admin", "technician", "client"] | None = None
    is_active: bool | None = None
    phone_whatsapp: str | None = Field(default=None, max_length=80)
    telegram_chat_id: str | None = Field(default=None, max_length=120)
    receives_alerts: bool | None = None


class PasswordResetIn(BaseModel):
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return _validate_new_password(value)


class UserStorageUnitAssignmentsIn(BaseModel):
    storage_unit_ids: list[int] = []


class SiteCreate(BaseModel):
    company_id: int
    name: str = Field(min_length=1, max_length=160)
    location: str | None = Field(default=None, max_length=255)
    latitude: float | None = None
    longitude: float | None = None
    timezone: str = Field(default="America/La_Paz", max_length=64)
    address: str | None = Field(default=None, max_length=255)
    department: str | None = Field(default=None, max_length=120)
    municipality: str | None = Field(default=None, max_length=120)


class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    name: str
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str = "America/La_Paz"
    address: str | None = None
    department: str | None = None
    municipality: str | None = None
    created_at: datetime


class StorageUnitCreate(BaseModel):
    company_id: int
    site_id: int
    name: str = Field(min_length=1, max_length=160)
    unit_type: str = Field(min_length=1, max_length=40)
    operation_type: Literal["storage", "field"] = "storage"
    capacity_tons: float | None = None
    surface_hectares: float | None = Field(default=None, gt=0)
    location: str | None = Field(default=None, max_length=255)
    crop_type: str | None = Field(default=None, max_length=120)
    assigned_technician_id: int | None = None
    assigned_client_id: int | None = None


class StorageUnitUpdate(BaseModel):
    company_id: int | None = None
    site_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=160)
    unit_type: str | None = Field(default=None, min_length=1, max_length=40)
    operation_type: Literal["storage", "field"] | None = None
    capacity_tons: float | None = None
    surface_hectares: float | None = Field(default=None, gt=0)
    location: str | None = Field(default=None, max_length=255)
    crop_type: str | None = Field(default=None, max_length=120)
    assigned_technician_id: int | None = None
    assigned_client_id: int | None = None
    is_active: bool | None = None


class StorageUnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    site_id: int
    name: str
    unit_type: str
    operation_type: Literal["storage", "field"] = "storage"
    capacity_tons: float | None = None
    surface_hectares: float | None = None
    location: str | None = None
    crop_type: str | None = None
    is_active: bool = True
    assigned_technician_id: int | None = None
    assigned_client_id: int | None = None
    last_report_generated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class StorageUnitAssignmentsIn(BaseModel):
    assigned_technician_id: int | None = None
    assigned_client_id: int | None = None


DEVICE_TYPES = {
    "silo_sensor",
    "field_sensor",
    "esp32_iot_node",
    "esp32_lora_wifi_node",
    "esp32_lora_node",
}


def validate_device_type_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized not in DEVICE_TYPES:
        raise ValueError("El tipo de sensor debe ser silo_sensor o field_sensor.")
    return normalized


class DeviceCreate(BaseModel):
    company_id: int
    site_id: int
    storage_unit_id: int
    external_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    device_token: str = Field(min_length=1)
    device_type: str = Field(default="silo_sensor", min_length=1, max_length=80)
    model_version: str | None = Field(default=None, max_length=80)
    physical_location: str | None = Field(default=None, max_length=255)
    installed_at: datetime | None = None
    capabilities: list[str] = []
    is_active: bool = True

    _validate_device_type = field_validator("device_type")(validate_device_type_value)


class AdminDeviceCreate(BaseModel):
    storage_unit_id: int
    external_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    device_type: str = Field(default="silo_sensor", min_length=1, max_length=80)
    model_version: str | None = Field(default=None, max_length=80)
    physical_location: str | None = Field(default=None, max_length=255)
    installed_at: datetime | None = None
    capabilities: list[str] = []
    is_active: bool = True

    _validate_device_type = field_validator("device_type")(validate_device_type_value)


class AdminDeviceUpdate(BaseModel):
    storage_unit_id: int | None = None
    external_id: str | None = Field(default=None, min_length=1, max_length=80)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    device_type: str | None = Field(default=None, min_length=1, max_length=80)
    model_version: str | None = Field(default=None, max_length=80)
    physical_location: str | None = Field(default=None, max_length=255)
    installed_at: datetime | None = None
    capabilities: list[str] | None = None
    is_active: bool | None = None

    _validate_device_type = field_validator("device_type")(validate_device_type_value)


class DeviceCalibrationIn(BaseModel):
    empty_distance_cm: float
    full_distance_cm: float

    @field_validator("empty_distance_cm", "full_distance_cm")
    @classmethod
    def validate_distance(cls, value: float) -> float:
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Las distancias de calibracion deben ser positivas y finitas.")
        return value


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    site_id: int
    storage_unit_id: int
    external_id: str
    name: str
    device_type: str = "esp32_iot_node"
    model_version: str | None = None
    physical_location: str | None = None
    installed_at: datetime | None = None
    is_active: bool
    created_at: datetime
    last_seen_at: datetime | None = None
    updated_at: datetime | None = None


class AdminDeviceOut(DeviceOut):
    empty_distance_cm: float | None = None
    full_distance_cm: float | None = None


class AdminDeviceSecretOut(AdminDeviceOut):
    api_key: str


class SensorReadingCreate(BaseModel):
    device_id: str = Field(min_length=1, max_length=80)
    device_token: str = Field(min_length=1)
    grain_temperature: float | None = None
    ambient_temperature: float | None = None
    ambient_humidity: float | None = None
    battery_voltage: float | None = None
    signal_quality: int | None = None
    level_distance_cm: float | None = None
    soil_moisture_percent: float | None = None
    soil_moisture_raw: float | None = None
    soil_temperature_c: float | None = None
    sensor_status: int | None = None
    timestamp: datetime

    @field_validator(
        "grain_temperature",
        "ambient_temperature",
        "ambient_humidity",
        "battery_voltage",
        "level_distance_cm",
        "soil_moisture_percent",
        "soil_moisture_raw",
        "soil_temperature_c",
    )
    @classmethod
    def validate_finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("La telemetria debe contener valores numericos finitos.")
        return value


class IotBatchReadingIn(BaseModel):
    device_id: int
    boot_id: int
    sequence: int
    sample_counter: int
    timestamp_utc: int
    time_quality: int
    protocol_version: int = 1
    sensor_profile: Literal["silo_sensor", "field_sensor"] | None = None
    metric_flags: int | None = None
    grain_temp_c_x100: int | None = None
    air_temp_c_x100: int | None = None
    rh_x100: int | None = None
    battery_mv: int | None = None
    soil_moisture_x100: int | None = None
    soil_moisture_raw: int | None = None
    soil_temp_c_x100: int | None = None
    level_distance_cm: float | None = None
    sensor_status: int
    firmware_version: int
    rssi_dbm: int | None = None
    snr_db_x10: int | None = None


class IotBatchIn(BaseModel):
    gateway_id: str = Field(min_length=1, max_length=80)
    firmware_version: str | None = Field(default=None, max_length=40)
    sent_at: datetime
    batch_id: str = Field(min_length=1, max_length=120)
    readings: list[IotBatchReadingIn] = Field(min_length=1, max_length=100)


class IotBatchResultOut(BaseModel):
    device_id: int
    boot_id: int
    sequence: int
    status: Literal[
        "accepted",
        "duplicate",
        "rejected_invalid",
        "rejected_unknown_device",
        "rejected_unauthorized",
        "temporary_error",
    ]
    detail: str | None = None


class IotBatchOut(BaseModel):
    batch_id: str
    results: list[IotBatchResultOut]


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    site_id: int
    storage_unit_id: int
    device_id: int
    grain_temperature: float | None = None
    ambient_temperature: float | None = None
    ambient_humidity: float | None = None
    battery_voltage: float | None = None
    signal_quality: int | None = None
    level_distance_cm: float | None = None
    level_percent: float | None = None
    soil_moisture_percent: float | None = None
    soil_temperature_c: float | None = None
    sensor_status: int | None = None
    metrics: list["MetricValueOut"] = []
    timestamp: datetime
    received_at: datetime


class MetricValueOut(BaseModel):
    variable_type: str
    raw_value: float | None = None
    value: float
    calibrated_value: float | None = None
    is_calibrated: bool = False
    calibration_version: int | None = None
    unit: str
    quality_status: str


class DeviceDiagnosticsOut(BaseModel):
    signal_quality: int | None = None
    snr_db: float | None = None
    sensor_status: int | None = None
    firmware_version: str | None = None


class DeviceCalibrationOut(BaseModel):
    empty_distance_cm: float | None = None
    full_distance_cm: float | None = None


CalibrationMethod = Literal["OFFSET", "LINEAR_TWO_POINT", "LEVEL_GEOMETRY"]


class CalibrationPreviewIn(BaseModel):
    variable_type: str = Field(min_length=1, max_length=80)
    method: CalibrationMethod
    device_channel_id: int | None = None
    raw_value: float | None = None
    offset: float | None = None
    dry_raw: float | None = None
    wet_raw: float | None = None
    dry_percent: float | None = Field(default=None, ge=0, le=100)
    wet_percent: float | None = Field(default=None, ge=0, le=100)
    parameters: dict[str, Any] = {}


class CalibrationCreateIn(CalibrationPreviewIn):
    reference_instrument: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)


class CalibrationPreviewOut(BaseModel):
    method: CalibrationMethod
    variable_type: str
    raw_value: float | None = None
    calibrated_value: float | None = None
    offset: float | None = None
    slope: float | None = None
    intercept: float | None = None
    parameters: dict[str, Any] = {}


class CalibrationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_id: int
    device_channel_id: int | None = None
    variable_type: str
    method: CalibrationMethod
    offset: float | None = None
    slope: float | None = None
    intercept: float | None = None
    dry_raw: float | None = None
    wet_raw: float | None = None
    dry_percent: float | None = None
    wet_percent: float | None = None
    parameters: dict[str, Any] = {}
    calibration_version: int
    is_active: bool
    calibrated_at: datetime
    calibrated_by_user_id: int | None = None
    calibrated_by_name: str | None = None
    reference_instrument: str | None = None
    notes: str | None = None
    created_at: datetime


class CalibrationStatusOut(BaseModel):
    variable_type: str
    status: Literal["uncalibrated", "calibrated", "review_required"]
    calibration_version: int | None = None
    calibrated_at: datetime | None = None
    calibrated_by_name: str | None = None


class ProductSummaryOut(BaseModel):
    storage_unit: StorageUnitOut
    product_type: Literal["silo_sensor", "field_sensor"]
    device_count: int
    active_device_count: int
    active_alerts: int
    latest_reading: ReadingOut | None = None
    calibration_statuses: list[CalibrationStatusOut] = []


class DeviceSummaryOut(BaseModel):
    device: DeviceOut
    latest_reading: ReadingOut | None = None
    active_alerts: int = 0
    calibration_status: Literal["configured", "pending", "not_applicable"]
    diagnostics: DeviceDiagnosticsOut | None = None
    calibration: DeviceCalibrationOut | None = None
    calibration_statuses: list[CalibrationStatusOut] = []


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    site_id: int
    storage_unit_id: int
    device_id: int
    reading_id: int | None = None
    alert_type: str
    severity: str
    title: str
    message: str
    metric: str | None = None
    observed_value: float | None = None
    threshold_value: float | None = None
    is_active: bool
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class ReadingIngestResponse(BaseModel):
    reading: ReadingOut
    alerts: list[AlertOut]


class DemoSimulationOut(BaseModel):
    storage_unit_id: int
    device_id: int
    device_external_id: str
    reading: ReadingOut
    alerts: list[AlertOut]


class OperationalLogCreate(BaseModel):
    alert_id: int | None = None
    storage_unit_id: int
    device_id: int | None = None
    category: Literal["installation", "maintenance", "corrective_action", "inspection", "general"] = "corrective_action"
    action_taken: str = Field(min_length=1, max_length=160)
    operator_name: str = Field(min_length=1, max_length=160)
    notes: str = Field(default="")
    timestamp: datetime


class OperationalLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    site_id: int
    storage_unit_id: int
    device_id: int | None = None
    alert_id: int | None = None
    user_id: int | None = None
    category: str
    action_taken: str
    operator_name: str
    notes: str
    timestamp: datetime
    created_at: datetime


class InstallationChecklistCreate(BaseModel):
    storage_unit_id: int
    device_id: int
    physical_location: str = Field(min_length=1, max_length=255)
    sensor_installed_correctly: bool
    connectivity_verified: bool
    initial_reading_registered: bool
    battery_verified: bool
    observations: str = ""
    technician_name: str = Field(min_length=1, max_length=160)
    timestamp: datetime


class ThresholdsIn(BaseModel):
    max_grain_temperature: float
    max_ambient_humidity: float
    min_battery_voltage: float
    critical_temperature: float
    critical_humidity: float
    min_level_percent: float | None = Field(default=None, ge=0, le=100)
    max_level_percent: float | None = Field(default=None, ge=0, le=100)
    min_soil_moisture_percent: float | None = Field(default=None, ge=0, le=100)
    max_soil_moisture_percent: float | None = Field(default=None, ge=0, le=100)


class ThresholdsOut(ThresholdsIn):
    device_id: int


class WeeklyNodeReportOut(BaseModel):
    device_id: int
    device_external_id: str
    device_name: str
    device_type: str
    reading_count: int
    max_grain_temperature: float | None = None
    max_ambient_humidity: float | None = None
    min_level_percent: float | None = None
    max_level_percent: float | None = None
    alerts_generated: int = 0


class WeeklyReportOut(BaseModel):
    company_name: str
    site_name: str
    storage_unit_name: str
    date_from: datetime
    date_to: datetime
    reading_count: int
    max_grain_temperature: float | None
    max_ambient_humidity: float | None
    alerts_generated: int
    alerts_resolved: int
    approximate_hours_out_of_range: float
    pilot_status: str
    installation_count: int
    maintenance_count: int
    last_report_generated_at: datetime | None = None
    operational_actions: list[OperationalLogOut]
    device_id: int | None = None
    device_external_id: str | None = None
    nodes: list[WeeklyNodeReportOut] = Field(default_factory=list)


class PilotCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=160)
    company_tax_id: str | None = Field(default=None, max_length=64)
    site_name: str = Field(min_length=1, max_length=160)
    site_location: str | None = Field(default=None, max_length=255)
    storage_unit_name: str = Field(min_length=1, max_length=160)
    storage_unit_type: str = Field(default="silo", min_length=1, max_length=40)
    capacity_tons: float | None = None
    device_external_id: str = Field(min_length=1, max_length=80)
    device_name: str = Field(min_length=1, max_length=160)
    device_token: str = Field(min_length=1)
    technician_user_id: int
    client_email: str = Field(min_length=3, max_length=255)
    client_full_name: str = Field(min_length=1, max_length=160)
    client_password: str = Field(min_length=8)

    @field_validator("client_password")
    @classmethod
    def validate_client_password(cls, value: str) -> str:
        return _validate_new_password(value)


class PilotAssignmentsIn(BaseModel):
    technician_user_id: int | None = None
    client_user_id: int | None = None


class PilotOut(BaseModel):
    storage_unit_id: int
    storage_unit_name: str
    storage_unit_type: str
    company_id: int
    company_name: str
    site_id: int
    site_name: str
    site_location: str | None = None
    device_id: int | None = None
    device_external_id: str | None = None
    technician_user_id: int | None = None
    technician_name: str | None = None
    client_user_id: int | None = None
    client_name: str | None = None
    status: str
    days_monitored: int
    reading_count: int
    alerts_generated: int
    alerts_resolved: int
    active_alerts: int
    actions_registered: int
    installation_count: int
    maintenance_count: int
    approximate_hours_out_of_range: float
    last_reading_at: datetime | None = None
    last_report_generated_at: datetime | None = None


class OperationalDataDeleteOut(BaseModel):
    storage_unit_id: int
    readings_deleted: int
    alerts_deleted: int
    logs_deleted: int


class NotificationPreferenceUpdate(BaseModel):
    enabled: bool = True
    destination: str | None = Field(default=None, max_length=255)
    minimum_severity: Literal["all", "technical", "warning", "critical"] = "critical"


class NotificationPreferenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    user_id: int
    channel: str
    destination: str | None = None
    minimum_severity: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class PushDeviceTokenIn(BaseModel):
    token: str = Field(min_length=8, max_length=512)
    platform: Literal["android", "ios", "web"] = "android"


class PushDeviceTokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    user_id: int
    token: str
    platform: str
    is_active: bool
    created_at: datetime
    last_seen_at: datetime


class NotificationEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    user_id: int | None = None
    alert_id: int | None = None
    channel: str
    destination: str | None = None
    status: str
    message: str
    provider_message_id: str | None = None
    error: str | None = None
    created_at: datetime
    sent_at: datetime | None = None


class NotificationTestOut(BaseModel):
    channel: str
    event: NotificationEventOut


class NotificationDeliveryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int | None = None
    alert_id: int | None = None
    incident_id: int | None = None
    maintenance_id: int | None = None
    user_id: int | None = None
    channel: str
    provider: str | None = None
    destination: str | None = None
    severity: str
    status: str
    dry_run: bool
    payload_preview: str
    provider_response: str | None = None
    error: str | None = None
    attempted_at: datetime | None = None
    sent_at: datetime | None = None
    delivered_at: datetime | None = None
    failed_at: datetime | None = None
    error_code: str | None = None
    error_message_sanitized: str | None = None
    provider_message_id: str | None = None
    retry_count: int = 0
    next_retry_at: datetime | None = None
    idempotency_key: str | None = None
    payload_version: str
    created_at: datetime
    updated_at: datetime


class NotificationProviderStatusIn(BaseModel):
    status: Literal["DELIVERED", "FAILED"]
    provider_message_id: str | None = Field(default=None, max_length=255)
    error_code: str | None = Field(default=None, max_length=80)
    error_message: str | None = Field(default=None, max_length=500)


class AdminNotificationTestIn(BaseModel):
    user_id: int | None = None
    storage_unit_id: int | None = None
    destination: str | None = Field(default=None, max_length=255)
    severity: Literal["info", "technical", "warning", "critical", "test"] = "test"
    message: str = Field(default="Prueba AgroEscudo: canal de notificacion configurado para piloto.", max_length=500)


class AiAlertRecommendationOut(BaseModel):
    alert_id: int
    source: str
    risk_level: str
    summary: str
    recommended_actions: list[str]
    client_message: str
    technical_notes: list[str] = []


class InsightEvidenceOut(BaseModel):
    label: str
    value: str


class StorageUnitInsightOut(BaseModel):
    storage_unit_id: int
    storage_unit_name: str
    period: Literal["24h", "7d", "30d"]
    status: Literal["normal", "attention", "critical", "offline", "insufficient_data"]
    confidence: Literal["high", "medium", "low"]
    data_points: int
    summary: str
    recommendations: list[str]
    evidence: list[InsightEvidenceOut] = []
    generated_at: datetime


class InsightsOut(BaseModel):
    period: Literal["24h", "7d", "30d"]
    insights: list[StorageUnitInsightOut]


class SignupCompanyIn(BaseModel):
    responsible_name: str = Field(min_length=1, max_length=160)
    work_email: str = Field(min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=80)
    commercial_name: str = Field(min_length=1, max_length=160)
    legal_name: str | None = Field(default=None, max_length=160)
    tax_id: str | None = Field(default=None, max_length=64)
    sector: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    estimated_sites: int | None = Field(default=None, ge=0)
    estimated_storage_units: int | None = Field(default=None, ge=0)
    use_case: str | None = Field(default=None, max_length=2000)
    password: str = Field(min_length=8)
    language: str = Field(default="es", max_length=10)
    consent_terms: bool
    consent_privacy: bool
    consent_marketing: bool = False

    @field_validator("password")
    @classmethod
    def validate_signup_password(cls, value: str) -> str:
        return _validate_new_password(value)


class SignupCompanyOut(BaseModel):
    request_id: int
    company_id: int
    user_id: int
    status: str
    email_required: bool
    verification_preview_token: str | None = None
    message: str


class DemoRequestIn(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    company_name: str = Field(min_length=1, max_length=160)
    position: str | None = Field(default=None, max_length=120)
    email: str = Field(min_length=3, max_length=255)
    phone: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=120)
    interest: str | None = Field(default=None, max_length=2000)
    consent: bool


class GenericMessageOut(BaseModel):
    message: str
    status: str = "ok"


class InvitePreviewIn(BaseModel):
    token: str = Field(min_length=16, max_length=255)


class InvitePreviewOut(BaseModel):
    email: str
    role: str
    company_name: str
    expires_at: datetime
    status: str


class InviteAcceptIn(BaseModel):
    token: str = Field(min_length=16, max_length=255)
    full_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def validate_invite_password(cls, value: str) -> str:
        return _validate_new_password(value)


class EmailVerifyIn(BaseModel):
    token: str = Field(min_length=16, max_length=255)


class PasswordForgotIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)


class PasswordForgotOut(BaseModel):
    message: str
    reset_preview_token: str | None = None


class PasswordResetPublicIn(BaseModel):
    token: str = Field(min_length=16, max_length=255)
    password: str = Field(min_length=8)

    @field_validator("password")
    @classmethod
    def validate_reset_password(cls, value: str) -> str:
        return _validate_new_password(value)


class ControlCenterBreakdownItem(BaseModel):
    key: str
    label: str
    count: int | float
    penalty: float
    cap: float


class ControlCenterPriorityOut(BaseModel):
    type: str
    severity: str
    title: str
    detail: str
    storage_unit_id: int | None = None
    alert_id: int | None = None


class ControlCenterSiteOut(BaseModel):
    site_id: int
    site_name: str
    status: str
    score: int
    storage_units: int
    active_alerts: int


class ControlCenterDeviceHealthOut(BaseModel):
    device_id: int
    external_id: str
    storage_unit_id: int
    status: str
    last_seen_at: datetime | None = None
    battery_voltage: float | None = None
    signal_quality: float | None = None


class ControlCenterSummaryOut(BaseModel):
    generated_at: datetime
    score: int
    status: Literal["PROTEGIDA", "ATENCION", "CRITICA", "SIN_DATOS"]
    formula_version: str
    breakdown: list[ControlCenterBreakdownItem]
    kpis: dict[str, int | float | str | None]
    priorities: list[ControlCenterPriorityOut]
    sites: list[ControlCenterSiteOut]
    device_health: list[ControlCenterDeviceHealthOut]
    recent_alerts: list[AlertOut]
    recent_activity: list[OperationalLogOut]


class ServiceCaseCreate(BaseModel):
    storage_unit_id: int
    device_id: int | None = None
    alert_id: int | None = None
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=4000)
    priority: Literal["low", "medium", "high", "critical"] = "medium"
    assigned_technician_id: int | None = None
    due_at: datetime | None = None


class ServiceCaseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    priority: Literal["low", "medium", "high", "critical"] | None = None
    status: Literal["open", "assigned", "in_progress", "waiting_client", "resolved", "closed", "cancelled"] | None = None
    assigned_technician_id: int | None = None
    due_at: datetime | None = None


class ServiceCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    site_id: int
    storage_unit_id: int
    device_id: int | None = None
    alert_id: int | None = None
    title: str
    description: str
    priority: str
    status: str
    assigned_technician_id: int | None = None
    opened_by_id: int | None = None
    due_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime | None = None


class ServiceCaseEventCreate(BaseModel):
    event_type: str = Field(default="note", min_length=1, max_length=60)
    note: str = Field(min_length=1, max_length=4000)


class ServiceCaseEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_case_id: int
    user_id: int | None = None
    event_type: str
    note: str
    created_at: datetime


class MaintenanceReportCreate(BaseModel):
    summary: str = Field(min_length=1, max_length=4000)
    actions_performed: str = Field(min_length=1, max_length=4000)
    recommendations: str | None = Field(default=None, max_length=4000)
    status: Literal["draft", "completed"] = "completed"


class MaintenanceReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    service_case_id: int
    storage_unit_id: int
    technician_user_id: int | None = None
    summary: str
    actions_performed: str
    recommendations: str | None = None
    status: str
    created_at: datetime
    completed_at: datetime | None = None


class StoredFileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int | None = None
    storage_provider: str
    object_key: str
    original_filename: str
    content_type: str
    size_bytes: int
    checksum_sha256: str | None = None
    created_at: datetime


class MaintenanceSignatureIn(BaseModel):
    signer_name: str = Field(min_length=1, max_length=160)
    signer_role: str | None = Field(default=None, max_length=80)


class MaintenanceSignatureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    maintenance_report_id: int
    signer_name: str
    signer_role: str | None = None
    signature_file_id: int | None = None
    signed_at: datetime


class AgroAssistantMessageIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    storage_unit_id: int | None = None


class AgroAssistantMessageOut(BaseModel):
    source: str
    answer: str
    facts: list[str]
    interpretation: str
    recommended_actions: list[str]
    conversation_id: int


class EducationArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    locale: str
    title: str
    summary: str
    body: str
    category: str
    translation_status: str
    is_published: bool
    created_at: datetime
    updated_at: datetime | None = None


class EducationCompleteOut(BaseModel):
    article_id: int
    completed_at: datetime


MaintenanceType = Literal[
    "INSTALLATION",
    "INSPECTION",
    "CALIBRATION",
    "BATTERY_CHANGE",
    "SENSOR_REPLACEMENT",
    "CLEANING",
    "SIGNAL_ADJUSTMENT",
    "ENCLOSURE_REPAIR",
    "FIRMWARE_UPDATE",
    "GATEWAY_CHECK",
    "REMOVAL",
    "OTHER",
]
MaintenancePriority = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]


class MaintenanceCreate(BaseModel):
    device_id: int
    maintenance_type: MaintenanceType
    priority: MaintenancePriority = "MEDIUM"
    scheduled_at: datetime | None = None
    technician_id: int | None = None
    service_case_id: int | None = None
    observations: str | None = Field(default=None, max_length=4000)
    next_maintenance_at: datetime | None = None


class MaintenanceUpdate(BaseModel):
    maintenance_type: MaintenanceType | None = None
    priority: MaintenancePriority | None = None
    scheduled_at: datetime | None = None
    technician_id: int | None = None
    observations: str | None = Field(default=None, max_length=4000)
    next_maintenance_at: datetime | None = None
    status: Literal["SCHEDULED", "ASSIGNED", "WAITING_PARTS"] | None = None


class MaintenanceStartIn(BaseModel):
    note: str = Field(default="Trabajo tecnico iniciado.", min_length=3, max_length=1000)


class MaintenanceCompleteIn(BaseModel):
    observations: str = Field(min_length=5, max_length=4000)
    diagnosis: str = Field(min_length=3, max_length=4000)
    action_taken: str = Field(min_length=5, max_length=4000)
    device_status_after: Literal["operational", "degraded", "calibration_pending", "offline"]
    parts_replaced: list[str] = Field(default_factory=list, max_length=100)
    battery_replaced: bool = False
    sensor_replaced: bool = False
    calibration_required: bool = False
    firmware_updated: bool = False
    previous_firmware_version: str | None = Field(default=None, max_length=80)
    new_firmware_version: str | None = Field(default=None, max_length=80)
    next_maintenance_at: datetime | None = None


class MaintenanceCancelIn(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class MaintenanceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    storage_unit_id: int
    device_id: int
    service_case_id: int | None = None
    parent_maintenance_id: int | None = None
    maintenance_type: str
    status: str
    effective_status: str
    priority: str
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None
    technician_id: int | None = None
    created_by_id: int
    observations: str | None = None
    diagnosis: str | None = None
    action_taken: str | None = None
    device_status_after: str | None = None
    parts_replaced: list[str] = []
    battery_replaced: bool
    sensor_replaced: bool
    calibration_required: bool
    firmware_updated: bool
    previous_firmware_version: str | None = None
    new_firmware_version: str | None = None
    evidence_count: int
    next_maintenance_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class MaintenanceEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    maintenance_id: int
    user_id: int | None = None
    event_type: str
    previous_status: str | None = None
    new_status: str | None = None
    note: str
    created_at: datetime


class DeviceMaintenanceSummaryOut(BaseModel):
    device_id: int
    last_intervention_at: datetime | None = None
    next_review_at: datetime | None = None
    pending_count: int
    overdue_count: int
    last_battery_change_at: datetime | None = None
    last_sensor_change_at: datetime | None = None
    last_calibration_at: datetime | None = None
    firmware_version: str | None = None
    technician_id: int | None = None
    operational_status: str


class InstallationCreate(BaseModel):
    device_id: int
    technician_id: int | None = None
    checklist_version: str = Field(default="p1-v1", min_length=1, max_length=32)
    responses: dict[str, Any] = Field(default_factory=dict)
    first_reading_id: int | None = None
    test_alert_id: int | None = None
    notes: str | None = Field(default=None, max_length=4000)
    next_review_at: datetime | None = None


class InstallationUpdate(BaseModel):
    technician_id: int | None = None
    responses: dict[str, Any] | None = None
    first_reading_id: int | None = None
    test_alert_id: int | None = None
    notes: str | None = Field(default=None, max_length=4000)
    next_review_at: datetime | None = None
    status: Literal["DRAFT", "IN_PROGRESS"] | None = None


class InstallationValidateIn(BaseModel):
    final_status: Literal["PASSED", "PASSED_WITH_OBSERVATIONS", "FAILED"]


class InstallationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    storage_unit_id: int
    device_id: int
    technician_id: int | None = None
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    checklist_version: str
    responses: dict[str, Any]
    first_reading_id: int | None = None
    test_alert_id: int | None = None
    notes: str | None = None
    validation_errors: list[str] = []
    next_review_at: datetime | None = None
    created_by_id: int
    created_at: datetime
    updated_at: datetime


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int | None = None
    storage_unit_id: int | None = None
    entity_type: str | None = None
    entity_id: int | None = None
    file_type: str
    original_filename: str
    content_type: str
    size_bytes: int
    checksum_sha256: str | None = None
    captured_at: datetime | None = None
    description: str | None = None
    is_sensitive: bool
    uploaded_by_id: int | None = None
    created_at: datetime
    deleted_at: datetime | None = None


class DeviceQrOut(BaseModel):
    device_id: int
    public_token: str
    qr_version: int
    scan_path: str
    created_at: datetime


class DeviceScanOut(BaseModel):
    authenticated: bool
    product_name: str
    device_type: str
    qr_version: int
    device_id: int | None = None
    storage_unit_id: int | None = None
    role: str | None = None
    allowed_actions: list[str] = []


class GatewayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int | None = None
    site_id: int | None = None
    storage_unit_id: int | None = None
    gateway_id: str
    name: str
    status: str
    effective_status: str
    firmware_version: str | None = None
    internet_status: str
    local_queue_size: int
    associated_devices_count: int
    restart_count: int
    last_restart_reason: str | None = None
    last_error_code: str | None = None
    last_error_at: datetime | None = None
    last_seen_at: datetime | None = None
    is_active: bool


class GatewayUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    company_id: int | None = None
    site_id: int | None = None
    storage_unit_id: int | None = None
    status: Literal["ONLINE", "DELAYED", "OFFLINE", "DEGRADED", "MAINTENANCE", "UNKNOWN"] | None = None
    internet_status: Literal["online", "offline", "degraded", "unknown"] | None = None
    firmware_version: str | None = Field(default=None, max_length=40)
    last_restart_reason: str | None = Field(default=None, max_length=255)


class GatewayDeviceAssignmentIn(BaseModel):
    device_ids: list[int] = Field(default_factory=list, max_length=250)


class SystemHealthOut(BaseModel):
    generated_at: datetime
    backend: dict[str, Any]
    database: dict[str, Any]
    gateways: dict[str, int]
    devices: dict[str, int]
    data: dict[str, int]
    alerts: dict[str, int | float | None]
    notifications: dict[str, int]


class PilotMetricsOut(BaseModel):
    generated_at: datetime
    company_id: int | None = None
    storage_unit_id: int | None = None
    period_from: datetime
    period_to: datetime
    data_availability: dict[str, Any]
    device_availability: dict[str, Any]
    operations: dict[str, Any]
    maintenance: dict[str, Any]
    quality: dict[str, Any]


class ComparisonOut(BaseModel):
    device_id: int
    variable: str
    unit: str
    period_a: dict[str, Any]
    period_b: dict[str, Any]
    absolute_difference: float | None = None
    percentage_difference: float | None = None
    sufficient_data: bool
    note: str


class FirmwareReleaseCreate(BaseModel):
    device_type: str = Field(min_length=1, max_length=80)
    version: str = Field(min_length=1, max_length=80)
    status: Literal["DRAFT", "TESTING", "RELEASED", "DEPRECATED", "REVOKED"] = "DRAFT"
    release_notes: str | None = Field(default=None, max_length=4000)
    checksum: str | None = Field(default=None, max_length=128)
    released_at: datetime | None = None
    is_recommended: bool = False
    is_mandatory: bool = False


class FirmwareReleaseUpdate(BaseModel):
    status: Literal["DRAFT", "TESTING", "RELEASED", "DEPRECATED", "REVOKED"] | None = None
    release_notes: str | None = Field(default=None, max_length=4000)
    checksum: str | None = Field(default=None, max_length=128)
    released_at: datetime | None = None
    is_recommended: bool | None = None
    is_mandatory: bool | None = None


class FirmwareReleaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    device_type: str
    version: str
    status: str
    release_notes: str | None = None
    checksum: str | None = None
    released_at: datetime | None = None
    created_by_id: int
    is_recommended: bool
    is_mandatory: bool
    created_at: datetime
    updated_at: datetime


class FirmwareUpdateRecordIn(BaseModel):
    firmware_release_id: int | None = None
    maintenance_id: int | None = None
    new_version: str = Field(min_length=1, max_length=80)
    result: Literal["SUCCESS", "FAILED", "ROLLED_BACK", "PENDING_VALIDATION"]
    notes: str | None = Field(default=None, max_length=4000)


class FirmwareUpdateRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    storage_unit_id: int
    device_id: int
    firmware_release_id: int | None = None
    maintenance_id: int | None = None
    previous_version: str | None = None
    new_version: str
    result: str
    notes: str | None = None
    recorded_by_id: int
    recorded_at: datetime


class DeviceFirmwareStatusOut(BaseModel):
    device_id: int
    external_id: str
    device_type: str
    current_version: str | None = None
    recommended_version: str | None = None
    is_outdated: bool | None = None
    update_status: str
    last_update_at: datetime | None = None
