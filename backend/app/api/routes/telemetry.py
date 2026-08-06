from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_device_access, require_role
from app.db.session import get_db
from app.domain.metric_registry import METRICS_BY_CODE, REGISTRY_VERSION
from app.models import (
    DeviceChannel,
    DeviceDashboardPreference,
    MetricDefinition,
    MetricReading,
    User,
    utc_now,
)
from app.schemas import (
    DashboardMetricOut,
    DeviceDashboardSchemaOut,
    MetricReadingsOut,
    SensorChannelCreateIn,
    SensorChannelOut,
    SensorChannelUpdateIn,
)
from app.services.audit import record_audit_event
from app.services.device_capabilities import channel_accepts_metric, channel_metric_codes
from app.services.telemetry import sensor_profile
from app.services.telemetry_queries import query_metric_readings

router = APIRouter(prefix="/devices", dependencies=[Depends(get_current_user)])


def _channel_out(channel: DeviceChannel, *, technical: bool) -> SensorChannelOut:
    return SensorChannelOut(
        id=channel.id,
        device_id=channel.device_id,
        channel_key=channel.channel_key,
        sensor_type=channel.sensor_type if technical else None,
        hardware_port=channel.hardware_port if technical else None,
        metric_codes=channel_metric_codes(channel),
        canonical_unit=channel.canonical_unit,
        is_installed=channel.is_installed,
        is_enabled=channel.is_enabled,
        is_required=channel.is_required,
        is_visible_to_client=channel.is_visible_to_client,
        chart_enabled=channel.chart_enabled,
        alert_enabled=channel.alert_enabled,
        calibration_required=channel.calibration_required,
        status=channel.status,
        display_name=channel.display_name or channel.name,
        display_order=channel.display_order,
        last_valid_reading_at=channel.last_valid_reading_at,
        retired_at=channel.retired_at,
        retirement_reason=channel.retirement_reason if technical else None,
    )


@router.get("/{device_id}/channels", response_model=list[SensorChannelOut])
def list_device_channels(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SensorChannelOut]:
    require_device_access(db, current_user, device_id)
    stmt = select(DeviceChannel).where(DeviceChannel.device_id == device_id)
    if current_user.role == "client":
        stmt = stmt.where(DeviceChannel.is_visible_to_client.is_(True))
    rows = db.scalars(stmt.order_by(DeviceChannel.display_order, DeviceChannel.channel_key)).all()
    return [_channel_out(item, technical=current_user.role in {"admin", "technician"}) for item in rows]


@router.get("/{device_id}/dashboard-schema", response_model=DeviceDashboardSchemaOut)
def get_dashboard_schema(
    device_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceDashboardSchemaOut:
    device = require_device_access(db, current_user, device_id)
    channels = db.scalars(
        select(DeviceChannel)
        .where(DeviceChannel.device_id == device_id, DeviceChannel.is_installed.is_(True))
        .order_by(DeviceChannel.display_order, DeviceChannel.channel_key)
    ).all()
    preferences = {
        (item.sensor_channel_id, item.metric_code): item
        for item in db.scalars(
            select(DeviceDashboardPreference).where(DeviceDashboardPreference.device_id == device_id)
        ).all()
    }
    definitions = {
        item.metric_code: item
        for item in db.scalars(select(MetricDefinition)).all()
    }
    technical = current_user.role in {"admin", "technician"}
    visible_channels = [
        channel
        for channel in channels
        if technical or channel.is_visible_to_client
    ]
    metrics = []
    for channel in visible_channels:
        for metric_code in channel_metric_codes(channel):
            definition = definitions.get(metric_code)
            if definition is None:
                continue
            preference = preferences.get((channel.id, metric_code))
            client_visible = (
                preference.client_visible if preference else channel.is_visible_to_client and definition.client_visibility
            )
            if not technical and not client_visible:
                continue
            metrics.append(
                DashboardMetricOut(
                    **{
                        key: getattr(definition, key)
                        for key in (
                            "numeric_id",
                            "metric_code",
                            "display_name",
                            "description",
                            "canonical_unit",
                            "physical_min",
                            "physical_max",
                            "default_decimals",
                            "default_chart_type",
                            "client_visibility",
                            "is_derived",
                            "calibration_method",
                            "alert_supported",
                            "display_order",
                            "registry_version",
                        )
                    },
                    channel_id=channel.id,
                    channel_key=channel.channel_key,
                    chart_enabled=preference.chart_enabled if preference else channel.chart_enabled,
                    client_visible=client_visible,
                    display_name_override=preference.display_name_override if preference else channel.display_name,
                    chart_type_override=preference.chart_type_override if preference else None,
                )
            )
    return DeviceDashboardSchemaOut(
        registry_version=REGISTRY_VERSION,
        capabilities_version=device.capabilities_version,
        device_id=device.id,
        device_external_id=device.external_id,
        device_name=device.name,
        device_profile=sensor_profile(device),
        template_code=device.template_code,
        channels=[_channel_out(item, technical=technical) for item in visible_channels],
        metrics=sorted(metrics, key=lambda item: (item.display_order, item.channel_key)),
    )


@router.get("/{device_id}/metrics/{metric_code}/readings", response_model=MetricReadingsOut)
def get_metric_readings(
    device_id: int,
    metric_code: str,
    channel_key: str,
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    resolution: str = Query(default="raw", pattern="^(raw|5m|15m|1h|1d)$"),
    limit: int = Query(default=1000, ge=1, le=5000),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MetricReadingsOut:
    require_device_access(db, current_user, device_id)
    definition = db.scalar(select(MetricDefinition).where(MetricDefinition.metric_code == metric_code))
    if definition is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Metrica no registrada.")
    channel = db.scalar(
        select(DeviceChannel).where(
            DeviceChannel.device_id == device_id,
            DeviceChannel.channel_key == channel_key,
        )
    )
    if channel is None or not channel_accepts_metric(channel, metric_code):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Canal o metrica no disponible.")
    if current_user.role == "client" and (
        not channel.is_visible_to_client or not definition.client_visibility
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para esta metrica.")
    return query_metric_readings(
        db,
        device_id=device_id,
        channel=channel,
        metric_code=metric_code,
        user=current_user,
        from_=from_,
        to=to,
        resolution=resolution,
        limit=limit,
        order=order,
    )


@router.post("/{device_id}/channels", response_model=SensorChannelOut, status_code=status.HTTP_201_CREATED)
def create_device_channel(
    device_id: int,
    payload: SensorChannelCreateIn,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> SensorChannelOut:
    device = require_device_access(db, current_user, device_id)
    if db.scalar(
        select(DeviceChannel).where(
            DeviceChannel.device_id == device_id,
            DeviceChannel.channel_key == payload.channel_key,
        )
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El channel_key ya existe.")
    profile_code = "CAMPO_SENSOR" if sensor_profile(device) == "field_sensor" else "SILO_SENSOR"
    definitions = []
    for metric_code in payload.metric_codes:
        definition = METRICS_BY_CODE.get(metric_code)
        if definition is None:
            raise HTTPException(status_code=422, detail=f"Metrica no canonica: {metric_code}")
        if profile_code not in definition.product_compatibility:
            raise HTTPException(status_code=422, detail=f"{metric_code} no es compatible con {profile_code}.")
        definitions.append(definition)
    primary = definitions[0]
    channel = DeviceChannel(
        device_id=device_id,
        name=payload.display_name,
        code=payload.channel_key,
        channel_key=payload.channel_key,
        sensor_type=payload.sensor_type,
        hardware_port=payload.hardware_port,
        metric_type=primary.metric_code,
        metric_codes=",".join(payload.metric_codes),
        unit=primary.canonical_unit,
        canonical_unit=primary.canonical_unit,
        is_active=payload.is_installed,
        is_installed=payload.is_installed,
        is_enabled=payload.is_installed,
        is_required=payload.is_required,
        is_visible_to_client=payload.is_visible_to_client,
        chart_enabled=payload.chart_enabled,
        alert_enabled=payload.alert_enabled,
        calibration_required=payload.calibration_required,
        status="CONFIGURED_NOT_SEEN" if payload.is_installed else "DISABLED",
        display_name=payload.display_name,
        display_order=payload.display_order,
    )
    db.add(channel)
    device.capabilities_version += 1
    db.flush()
    record_audit_event(
        db,
        action="sensor.channel.create",
        summary="Canal de sensor agregado",
        user=current_user,
        resource_type="device_channel",
        resource_id=channel.id,
        metadata={"device_id": device_id, "channel_key": channel.channel_key, "metrics": payload.metric_codes},
    )
    db.commit()
    db.refresh(channel)
    return _channel_out(channel, technical=True)


@router.patch("/{device_id}/channels/{channel_id}", response_model=SensorChannelOut)
def update_device_channel(
    device_id: int,
    channel_id: int,
    payload: SensorChannelUpdateIn,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> SensorChannelOut:
    device = require_device_access(db, current_user, device_id)
    channel = db.get(DeviceChannel, channel_id)
    if channel is None or channel.device_id != device_id:
        raise HTTPException(status_code=404, detail="Canal no encontrado.")
    values = payload.model_dump(exclude_unset=True)
    reason = values.pop("reason", None)
    requested_status = values.get("status")
    if requested_status in {"DISABLED", "RETIRED"} and not reason:
        raise HTTPException(status_code=422, detail="Debes registrar un motivo.")
    if requested_status == "RETIRED":
        channel.retired_at = utc_now()
        channel.retired_by_id = current_user.id
        channel.retirement_reason = reason
        values.update({"is_active": False, "is_enabled": False, "chart_enabled": False, "alert_enabled": False})
    elif requested_status == "DISABLED":
        channel.retirement_reason = reason
        values.update({"is_active": False, "is_enabled": False, "alert_enabled": False})
    for name, value in values.items():
        setattr(channel, name, value)
    channel.updated_at = utc_now()
    device.capabilities_version += 1
    record_audit_event(
        db,
        action="sensor.channel.update",
        summary="Configuracion de canal actualizada",
        user=current_user,
        resource_type="device_channel",
        resource_id=channel.id,
        metadata={"device_id": device_id, "channel_key": channel.channel_key, "status": channel.status},
    )
    db.commit()
    db.refresh(channel)
    return _channel_out(channel, technical=True)
