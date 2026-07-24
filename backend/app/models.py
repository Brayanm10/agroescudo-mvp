from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    type: Mapped[str] = mapped_column(String(40), default="acopiador", index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    approval_status: Mapped[str] = mapped_column(String(32), default="APPROVED", index=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    users: Mapped[list["User"]] = relationship(back_populates="company", foreign_keys="User.company_id")
    sites: Mapped[list["Site"]] = relationship(back_populates="company")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(160))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(24), default="client", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    phone_whatsapp: Mapped[str | None] = mapped_column(String(80), nullable=True)
    telegram_chat_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    receives_alerts: Mapped[bool] = mapped_column(Boolean, default=True)
    language: Mapped[str] = mapped_column(String(10), default="es")
    locale: Mapped[str] = mapped_column(String(10), default="es")
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", index=True)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="America/La_Paz")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    company: Mapped["Company"] = relationship(back_populates="users", foreign_keys=[company_id])


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="America/La_Paz")
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    municipality: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    company: Mapped["Company"] = relationship(back_populates="sites")
    storage_units: Mapped[list["StorageUnit"]] = relationship(back_populates="site")


class StorageUnit(Base):
    __tablename__ = "storage_units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    unit_type: Mapped[str] = mapped_column(String(40))
    operation_type: Mapped[str] = mapped_column(String(20), default="storage", index=True)
    capacity_tons: Mapped[float | None] = mapped_column(Float, nullable=True)
    surface_hectares: Mapped[float | None] = mapped_column(Float, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    crop_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    assigned_technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    assigned_client_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    last_report_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    site: Mapped["Site"] = relationship(back_populates="storage_units")
    devices: Mapped[list["Device"]] = relationship(back_populates="storage_unit")


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    storage_unit_id: Mapped[int] = mapped_column(ForeignKey("storage_units.id"), index=True)
    external_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    token_hash: Mapped[str] = mapped_column(String(255))
    device_type: Mapped[str] = mapped_column(String(80), default="esp32_iot_node", index=True)
    model_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    physical_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    operational_status: Mapped[str] = mapped_column(String(32), default="operational", index=True)
    expected_reading_interval_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    empty_distance_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    full_distance_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    public_token: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True, index=True)
    qr_version: Mapped[int] = mapped_column(Integer, default=0)
    qr_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    qr_revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    qr_last_scanned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    storage_unit: Mapped["StorageUnit"] = relationship(back_populates="devices")
    readings: Mapped[list["SensorReading"]] = relationship(back_populates="device")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="device")


class IotGateway(Base):
    __tablename__ = "iot_gateways"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), nullable=True, index=True)
    storage_unit_id: Mapped[int | None] = mapped_column(ForeignKey("storage_units.id"), nullable=True, index=True)
    gateway_id: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(32), default="UNKNOWN", index=True)
    firmware_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    internet_status: Mapped[str] = mapped_column(String(32), default="unknown", index=True)
    local_queue_size: Mapped[int] = mapped_column(Integer, default=0)
    associated_devices_count: Mapped[int] = mapped_column(Integer, default=0)
    restart_count: Mapped[int] = mapped_column(Integer, default=0)
    last_restart_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address_sanitized: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IotGatewayCredential(Base):
    __tablename__ = "iot_gateway_credentials"
    __table_args__ = (
        UniqueConstraint("gateway_id", "key_version", name="uq_iot_gateway_credentials_gateway_key_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gateway_id: Mapped[int] = mapped_column(ForeignKey("iot_gateways.id"), index=True)
    key_version: Mapped[int] = mapped_column(Integer, default=1)
    secret_hash: Mapped[str] = mapped_column(String(255))
    encrypted_secret: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IotDevice(Base):
    __tablename__ = "iot_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    gateway_id: Mapped[int | None] = mapped_column(ForeignKey("iot_gateways.id"), nullable=True, index=True)
    key_version: Mapped[int] = mapped_column(Integer, default=1)
    firmware_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class IotIngestionBatch(Base):
    __tablename__ = "iot_ingestion_batches"
    __table_args__ = (
        UniqueConstraint("gateway_id", "nonce", name="uq_iot_ingestion_batches_gateway_nonce"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gateway_id: Mapped[int] = mapped_column(ForeignKey("iot_gateways.id"), index=True)
    batch_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    nonce: Mapped[str] = mapped_column(String(160), index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32), default="processed", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IotReading(Base):
    __tablename__ = "iot_readings"
    __table_args__ = (
        UniqueConstraint("iot_device_id", "boot_id", "sequence", name="uq_iot_readings_device_boot_sequence"),
        Index("ix_iot_readings_device_timestamp", "iot_device_id", "timestamp"),
        Index("ix_iot_readings_gateway_timestamp", "gateway_id", "timestamp"),
        Index("ix_iot_readings_storage_timestamp", "storage_unit_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    iot_device_id: Mapped[int] = mapped_column(ForeignKey("iot_devices.id"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    gateway_id: Mapped[int] = mapped_column(ForeignKey("iot_gateways.id"), index=True)
    sensor_reading_id: Mapped[int | None] = mapped_column(ForeignKey("sensor_readings.id"), nullable=True, index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    storage_unit_id: Mapped[int] = mapped_column(ForeignKey("storage_units.id"), index=True)
    boot_id: Mapped[int] = mapped_column(Integer)
    sequence: Mapped[int] = mapped_column(Integer)
    sample_counter: Mapped[int] = mapped_column(Integer)
    timestamp_utc: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    time_quality: Mapped[int] = mapped_column(Integer)
    grain_temp_c_x100: Mapped[int | None] = mapped_column(Integer, nullable=True)
    air_temp_c_x100: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rh_x100: Mapped[int | None] = mapped_column(Integer, nullable=True)
    battery_mv: Mapped[int | None] = mapped_column(Integer, nullable=True)
    soil_moisture_x100: Mapped[int | None] = mapped_column(Integer, nullable=True)
    soil_moisture_raw: Mapped[int | None] = mapped_column(Integer, nullable=True)
    soil_temp_c_x100: Mapped[int | None] = mapped_column(Integer, nullable=True)
    level_distance_mm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    level_percent_x100: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sensor_status: Mapped[int] = mapped_column(Integer)
    firmware_version: Mapped[int] = mapped_column(Integer)
    rssi_dbm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    snr_db_x10: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IotIngestionEvent(Base):
    __tablename__ = "iot_ingestion_events"
    __table_args__ = (
        Index("ix_iot_ingestion_events_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("iot_ingestion_batches.id"), index=True)
    gateway_id: Mapped[int] = mapped_column(ForeignKey("iot_gateways.id"), index=True)
    iot_device_id: Mapped[int | None] = mapped_column(ForeignKey("iot_devices.id"), nullable=True, index=True)
    device_identifier: Mapped[int] = mapped_column(Integer, index=True)
    boot_id: Mapped[int] = mapped_column(Integer)
    sequence: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(40), index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class IotGatewayHealth(Base):
    __tablename__ = "iot_gateway_health"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    gateway_id: Mapped[int] = mapped_column(ForeignKey("iot_gateways.id"), index=True)
    firmware_version: Mapped[str | None] = mapped_column(String(40), nullable=True)
    queue_depth: Mapped[int | None] = mapped_column(Integer, nullable=True)
    free_heap: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (Index("ix_sensor_readings_device_timestamp", "device_id", "timestamp"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    storage_unit_id: Mapped[int] = mapped_column(ForeignKey("storage_units.id"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    grain_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    ambient_temperature: Mapped[float | None] = mapped_column(Float, nullable=True)
    ambient_humidity: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_voltage: Mapped[float | None] = mapped_column(Float, nullable=True)
    signal_quality: Mapped[int | None] = mapped_column(Integer, nullable=True)
    level_distance_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    level_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_moisture_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    sensor_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    device: Mapped["Device"] = relationship(back_populates="readings")
    metric_values: Mapped[list["SensorMetricValue"]] = relationship(
        back_populates="sensor_reading",
        cascade="all, delete-orphan",
    )


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    storage_unit_id: Mapped[int] = mapped_column(ForeignKey("storage_units.id"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    reading_id: Mapped[int | None] = mapped_column(ForeignKey("sensor_readings.id"), nullable=True, index=True)
    alert_type: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    title: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text)
    metric: Mapped[str | None] = mapped_column(String(80), nullable=True)
    observed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    device: Mapped["Device"] = relationship(back_populates="alerts")


class OperationalLog(Base):
    __tablename__ = "operational_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    storage_unit_id: Mapped[int] = mapped_column(ForeignKey("storage_units.id"), index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    category: Mapped[str] = mapped_column(String(40), default="corrective_action", index=True)
    action_taken: Mapped[str] = mapped_column(String(160), index=True)
    operator_name: Mapped[str] = mapped_column(String(160))
    notes: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    channel: Mapped[str] = mapped_column(String(32), index=True)
    destination: Mapped[str | None] = mapped_column(String(255), nullable=True)
    minimum_severity: Mapped[str] = mapped_column(String(20), default="critical")
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class PushDeviceToken(Base):
    __tablename__ = "push_device_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(32), default="android")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class NotificationEvent(Base):
    __tablename__ = "notification_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(32), index=True)
    destination: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    message: Mapped[str] = mapped_column(Text)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"), nullable=True, index=True)
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("service_cases.id"), nullable=True, index=True)
    maintenance_id: Mapped[int | None] = mapped_column(ForeignKey("maintenance_records.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    channel: Mapped[str] = mapped_column(String(32), index=True)
    provider: Mapped[str | None] = mapped_column(String(40), nullable=True)
    destination: Mapped[str | None] = mapped_column(String(255), nullable=True)
    severity: Mapped[str] = mapped_column(String(20), default="info", index=True)
    status: Mapped[str] = mapped_column(String(32), default="dry_run", index=True)
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    payload_preview: Mapped[str] = mapped_column(Text)
    provider_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message_sanitized: Mapped[str | None] = mapped_column(String(500), nullable=True)
    provider_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True, index=True)
    payload_version: Mapped[str] = mapped_column(String(32), default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ThresholdConfig(Base):
    __tablename__ = "threshold_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    site_id: Mapped[int | None] = mapped_column(ForeignKey("sites.id"), nullable=True, index=True)
    storage_unit_id: Mapped[int | None] = mapped_column(ForeignKey("storage_units.id"), nullable=True, index=True)
    metric: Mapped[str] = mapped_column(String(80), index=True)
    operator: Mapped[str] = mapped_column(String(8))
    value: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OrganizationRequest(Base):
    __tablename__ = "organization_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    requester_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    responsible_name: Mapped[str] = mapped_column(String(160))
    work_email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    commercial_name: Mapped[str] = mapped_column(String(160))
    legal_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    tax_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(80), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    department: Mapped[str | None] = mapped_column(String(120), nullable=True)
    estimated_sites: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_storage_units: Mapped[int | None] = mapped_column(Integer, nullable=True)
    use_case: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(10), default="es")
    status: Mapped[str] = mapped_column(String(32), default="PENDING_REVIEW", index=True)
    consent_terms: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_privacy: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_marketing: Mapped[bool] = mapped_column(Boolean, default=False)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class UserInvite(Base):
    __tablename__ = "user_invites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    role: Mapped[str] = mapped_column(String(32), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    invited_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    storage_unit_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="INVITED", index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    jti: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    resource_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    resource_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    summary: Mapped[str] = mapped_column(String(255))
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    company_name: Mapped[str] = mapped_column(String(160))
    position: Mapped[str | None] = mapped_column(String(120), nullable=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(80), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    interest: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(40), default="web", index=True)
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class DeviceChannel(Base):
    __tablename__ = "device_channels"
    __table_args__ = (
        UniqueConstraint("device_id", "code", name="uq_device_channels_device_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(80), index=True)
    zone: Mapped[str | None] = mapped_column(String(120), nullable=True)
    level: Mapped[str | None] = mapped_column(String(80), nullable=True)
    position_description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metric_type: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    unit: Mapped[str | None] = mapped_column(String(24), nullable=True)
    adc_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    adc_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class SensorCalibration(Base):
    __tablename__ = "sensor_calibrations"
    __table_args__ = (
        Index("ix_sensor_calibrations_lookup", "device_id", "variable_type", "is_active"),
        UniqueConstraint(
            "device_id",
            "device_channel_id",
            "variable_type",
            "calibration_version",
            name="uq_sensor_calibrations_version",
        ),
        Index(
            "uq_sensor_calibrations_active_device_variable",
            "device_id",
            "variable_type",
            unique=True,
            sqlite_where=text("is_active = 1 AND device_channel_id IS NULL"),
            postgresql_where=text("is_active = true AND device_channel_id IS NULL"),
        ),
        Index(
            "uq_sensor_calibrations_device_variable_version",
            "device_id",
            "variable_type",
            "calibration_version",
            unique=True,
            sqlite_where=text("device_channel_id IS NULL"),
            postgresql_where=text("device_channel_id IS NULL"),
        ),
        Index(
            "uq_sensor_calibrations_active_channel_variable",
            "device_channel_id",
            "variable_type",
            unique=True,
            sqlite_where=text("is_active = 1 AND device_channel_id IS NOT NULL"),
            postgresql_where=text("is_active = true AND device_channel_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    device_channel_id: Mapped[int | None] = mapped_column(ForeignKey("device_channels.id"), nullable=True, index=True)
    variable_type: Mapped[str] = mapped_column(String(80), index=True)
    method: Mapped[str] = mapped_column(String(40), index=True)
    offset: Mapped[float | None] = mapped_column(Float, nullable=True)
    slope: Mapped[float | None] = mapped_column(Float, nullable=True)
    intercept: Mapped[float | None] = mapped_column(Float, nullable=True)
    dry_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    wet_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    dry_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    wet_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    parameters_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    calibration_version: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    calibrated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    calibrated_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    reference_instrument: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SensorMetricValue(Base):
    __tablename__ = "sensor_metric_values"
    __table_args__ = (
        Index("ix_sensor_metric_values_reading_variable", "sensor_reading_id", "variable_type"),
        UniqueConstraint(
            "sensor_reading_id",
            "device_channel_id",
            "variable_type",
            name="uq_sensor_metric_values_reading_channel_variable",
        ),
        Index(
            "uq_sensor_metric_values_reading_variable_no_channel",
            "sensor_reading_id",
            "variable_type",
            unique=True,
            sqlite_where=text("device_channel_id IS NULL"),
            postgresql_where=text("device_channel_id IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sensor_reading_id: Mapped[int] = mapped_column(ForeignKey("sensor_readings.id"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    device_channel_id: Mapped[int | None] = mapped_column(ForeignKey("device_channels.id"), nullable=True, index=True)
    calibration_id: Mapped[int | None] = mapped_column(ForeignKey("sensor_calibrations.id"), nullable=True, index=True)
    variable_type: Mapped[str] = mapped_column(String(80), index=True)
    raw_value: Mapped[float] = mapped_column(Float)
    calibrated_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(24))
    calibration_version_applied: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality_status: Mapped[str] = mapped_column(String(40), default="raw", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    sensor_reading: Mapped["SensorReading"] = relationship(back_populates="metric_values")


class MaintenanceRecord(Base):
    __tablename__ = "maintenance_records"
    __table_args__ = (
        Index("ix_maintenance_records_scope_status", "company_id", "storage_unit_id", "status"),
        Index("ix_maintenance_records_device_schedule", "device_id", "scheduled_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    storage_unit_id: Mapped[int] = mapped_column(ForeignKey("storage_units.id"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    service_case_id: Mapped[int | None] = mapped_column(ForeignKey("service_cases.id"), nullable=True, index=True)
    parent_maintenance_id: Mapped[int | None] = mapped_column(
        ForeignKey("maintenance_records.id"),
        nullable=True,
        index=True,
    )
    maintenance_type: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(32), default="SCHEDULED", index=True)
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM", index=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnosis: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_taken: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_status_after: Mapped[str | None] = mapped_column(String(40), nullable=True)
    parts_replaced_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    battery_replaced: Mapped[bool] = mapped_column(Boolean, default=False)
    sensor_replaced: Mapped[bool] = mapped_column(Boolean, default=False)
    calibration_required: Mapped[bool] = mapped_column(Boolean, default=False)
    firmware_updated: Mapped[bool] = mapped_column(Boolean, default=False)
    previous_firmware_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    new_firmware_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    next_maintenance_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class MaintenanceEvent(Base):
    __tablename__ = "maintenance_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    maintenance_id: Mapped[int] = mapped_column(ForeignKey("maintenance_records.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    note: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class InstallationChecklist(Base):
    __tablename__ = "installation_checklists"
    __table_args__ = (
        Index("ix_installation_checklists_scope_status", "company_id", "storage_unit_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    storage_unit_id: Mapped[int] = mapped_column(ForeignKey("storage_units.id"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checklist_version: Mapped[str] = mapped_column(String(32), default="p1-v1")
    responses_json: Mapped[str] = mapped_column(Text, default="{}")
    first_reading_id: Mapped[int | None] = mapped_column(
        ForeignKey("sensor_readings.id"),
        nullable=True,
        index=True,
    )
    test_alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"), nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_errors_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ServiceCase(Base):
    __tablename__ = "service_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    site_id: Mapped[int] = mapped_column(ForeignKey("sites.id"), index=True)
    storage_unit_id: Mapped[int] = mapped_column(ForeignKey("storage_units.id"), index=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"), nullable=True, index=True)
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(32), default="medium", index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    assigned_technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    opened_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class ServiceCaseEvent(Base):
    __tablename__ = "service_case_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_case_id: Mapped[int] = mapped_column(ForeignKey("service_cases.id"), index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    note: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class StoredFile(Base):
    __tablename__ = "stored_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    storage_unit_id: Mapped[int | None] = mapped_column(ForeignKey("storage_units.id"), nullable=True, index=True)
    uploaded_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    file_type: Mapped[str] = mapped_column(String(32), default="OTHER", index=True)
    storage_provider: Mapped[str] = mapped_column(String(32), default="local")
    bucket: Mapped[str | None] = mapped_column(String(160), nullable=True)
    object_key: Mapped[str] = mapped_column(String(512), unique=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer)
    checksum_sha256: Mapped[str | None] = mapped_column(String(80), nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_sensitive: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class MaintenanceReport(Base):
    __tablename__ = "maintenance_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    service_case_id: Mapped[int] = mapped_column(ForeignKey("service_cases.id"), index=True)
    storage_unit_id: Mapped[int] = mapped_column(ForeignKey("storage_units.id"), index=True)
    technician_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    summary: Mapped[str] = mapped_column(Text)
    actions_performed: Mapped[str] = mapped_column(Text)
    recommendations: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MaintenanceReportPhoto(Base):
    __tablename__ = "maintenance_report_photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    maintenance_report_id: Mapped[int] = mapped_column(ForeignKey("maintenance_reports.id"), index=True)
    stored_file_id: Mapped[int] = mapped_column(ForeignKey("stored_files.id"), index=True)
    photo_type: Mapped[str] = mapped_column(String(40), default="evidence", index=True)
    caption: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class MaintenanceSignature(Base):
    __tablename__ = "maintenance_signatures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    maintenance_report_id: Mapped[int] = mapped_column(ForeignKey("maintenance_reports.id"), index=True)
    signer_name: Mapped[str] = mapped_column(String(160))
    signer_role: Mapped[str | None] = mapped_column(String(80), nullable=True)
    signature_file_id: Mapped[int | None] = mapped_column(ForeignKey("stored_files.id"), nullable=True, index=True)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class FirmwareRelease(Base):
    __tablename__ = "firmware_releases"
    __table_args__ = (
        UniqueConstraint("device_type", "version", name="uq_firmware_releases_device_type_version"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_type: Mapped[str] = mapped_column(String(80), index=True)
    version: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(32), default="DRAFT", index=True)
    release_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    is_recommended: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class FirmwareUpdateRecord(Base):
    __tablename__ = "firmware_update_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    storage_unit_id: Mapped[int] = mapped_column(ForeignKey("storage_units.id"), index=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    firmware_release_id: Mapped[int | None] = mapped_column(
        ForeignKey("firmware_releases.id"),
        nullable=True,
        index=True,
    )
    maintenance_id: Mapped[int | None] = mapped_column(
        ForeignKey("maintenance_records.id"),
        nullable=True,
        index=True,
    )
    previous_version: Mapped[str | None] = mapped_column(String(80), nullable=True)
    new_version: Mapped[str] = mapped_column(String(80))
    result: Mapped[str] = mapped_column(String(32), index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    recorded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class EducationArticle(Base):
    __tablename__ = "education_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    locale: Mapped[str] = mapped_column(String(10), default="es", index=True)
    title: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), default="postcosecha", index=True)
    translation_status: Mapped[str] = mapped_column(String(32), default="VERIFIED", index=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)


class EducationProgress(Base):
    __tablename__ = "education_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "article_id", name="uq_education_progress_user_article"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    article_id: Mapped[int] = mapped_column(ForeignKey("education_articles.id"), index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class AiConversation(Base):
    __tablename__ = "ai_conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    storage_unit_id: Mapped[int | None] = mapped_column(ForeignKey("storage_units.id"), nullable=True, index=True)
    source: Mapped[str] = mapped_column(String(40), default="rules", index=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class AiUsage(Base):
    __tablename__ = "ai_usage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("ai_conversations.id"), nullable=True, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(40), default="rules", index=True)
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    tool_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)


class RateLimitEvent(Base):
    __tablename__ = "rate_limit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    identifier: Mapped[str] = mapped_column(String(255), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    count: Mapped[int] = mapped_column(Integer, default=1)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
