from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1)


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    tax_id: str | None = Field(default=None, max_length=64)


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    tax_id: str | None = None
    created_at: datetime


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    company: CompanyOut | None = None


class UserCreate(BaseModel):
    company_id: int
    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=6)
    role: Literal["admin", "technician", "client"]


class UserUpdate(BaseModel):
    company_id: int | None = None
    email: str | None = Field(default=None, min_length=3, max_length=255)
    full_name: str | None = Field(default=None, min_length=1, max_length=160)
    role: Literal["admin", "technician", "client"] | None = None
    is_active: bool | None = None


class PasswordResetIn(BaseModel):
    password: str = Field(min_length=6)


class UserStorageUnitAssignmentsIn(BaseModel):
    storage_unit_ids: list[int] = []


class SiteCreate(BaseModel):
    company_id: int
    name: str = Field(min_length=1, max_length=160)
    location: str | None = Field(default=None, max_length=255)


class SiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    name: str
    location: str | None = None
    created_at: datetime


class StorageUnitCreate(BaseModel):
    company_id: int
    site_id: int
    name: str = Field(min_length=1, max_length=160)
    unit_type: str = Field(min_length=1, max_length=40)
    capacity_tons: float | None = None
    assigned_technician_id: int | None = None
    assigned_client_id: int | None = None


class StorageUnitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    site_id: int
    name: str
    unit_type: str
    capacity_tons: float | None = None
    assigned_technician_id: int | None = None
    assigned_client_id: int | None = None
    last_report_generated_at: datetime | None = None
    created_at: datetime


class StorageUnitAssignmentsIn(BaseModel):
    assigned_technician_id: int | None = None
    assigned_client_id: int | None = None


class DeviceCreate(BaseModel):
    company_id: int
    site_id: int
    storage_unit_id: int
    external_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    device_token: str = Field(min_length=1)
    is_active: bool = True


class DeviceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    site_id: int
    storage_unit_id: int
    external_id: str
    name: str
    is_active: bool
    created_at: datetime


class SensorReadingCreate(BaseModel):
    device_id: str = Field(min_length=1, max_length=80)
    device_token: str = Field(min_length=1)
    grain_temperature: float
    ambient_temperature: float
    ambient_humidity: float
    battery_voltage: float
    signal_quality: int
    timestamp: datetime


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    site_id: int
    storage_unit_id: int
    device_id: int
    grain_temperature: float
    ambient_temperature: float
    ambient_humidity: float
    battery_voltage: float
    signal_quality: int
    timestamp: datetime
    received_at: datetime


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


class ThresholdsOut(ThresholdsIn):
    device_id: int


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
    client_password: str = Field(min_length=6)


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
    alert_id: int | None = None
    user_id: int | None = None
    channel: str
    destination: str | None = None
    severity: str
    status: str
    dry_run: bool
    payload_preview: str
    provider_response: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class AdminNotificationTestIn(BaseModel):
    user_id: int | None = None
    destination: str | None = Field(default=None, max_length=255)
    message: str = Field(default="Prueba AgroEscudo: canal de notificacion configurado para piloto.", max_length=500)


class AiAlertRecommendationOut(BaseModel):
    alert_id: int
    source: str
    risk_level: str
    summary: str
    recommended_actions: list[str]
    client_message: str
    technical_notes: list[str] = []
