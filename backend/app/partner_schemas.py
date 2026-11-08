"""Public P0 schemas. No ORM serialization of internal entities."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict

MetricCode = Literal['GRAIN_TEMPERATURE_C', 'AMBIENT_TEMPERATURE_C', 'AMBIENT_RELATIVE_HUMIDITY_PCT']

class PublicModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Capability(PublicModel):
    channel_key: str
    metric_code: MetricCode
    unit: Literal['degC', 'percent']

class PartnerDeviceOut(PublicModel):
    id: str
    status: Literal['online', 'offline', 'unknown', 'inactive']
    last_seen_at: datetime | None
    expected_interval_seconds: int | None
    offline_after_seconds: int | None
    capabilities: list[Capability]

class PartnerUnitOut(PublicModel):
    id: str
    name: str
    operation_type: Literal['storage']
    unit_type: str
    devices: list[PartnerDeviceOut]

class PartnerReadingOut(PublicModel):
    reading_id: str
    device_id: str
    channel_key: str
    metric_code: MetricCode
    value: float | None
    unit: Literal['degC', 'percent']
    sampled_at: datetime
    received_at: datetime
    quality_status: Literal['valid', 'invalid', 'uncalibrated', 'unknown']
    stale_after_seconds: int | None
    is_stale: bool | None

class PartnerLatestOut(PublicModel):
    storage_unit_id: str
    generated_at: datetime
    devices: list[PartnerDeviceOut]
    items: list[PartnerReadingOut]

class PartnerUnitsOut(PublicModel):
    items: list[PartnerUnitOut]
    next_cursor: str | None

class PartnerReadingsOut(PublicModel):
    items: list[PartnerReadingOut]
    next_cursor: str | None

class PartnerAlertOut(PublicModel):
    id: str
    storage_unit_id: str
    device_id: str
    metric_code: str
    severity: Literal['warning', 'critical', 'technical', 'unknown']
    status: Literal['active', 'acknowledged', 'resolved']
    message: str
    observed_value: float | None
    threshold_value: float | None
    unit: str | None
    created_at: datetime
    resolved_at: datetime | None

class PartnerAlertsOut(PublicModel):
    items: list[PartnerAlertOut]
    next_cursor: str | None

class PartnerTokenOut(PublicModel):
    access_token: str
    token_type: Literal['Bearer'] = 'Bearer'
    expires_in: int = 600
    scope: str

class PartnerErrorDetail(PublicModel):
    code: str
    message: str
    request_id: str

class PartnerErrorOut(PublicModel):
    error: PartnerErrorDetail

class OAuthErrorOut(PublicModel):
    error: str
    error_description: str
