from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.api.deps import assigned_storage_unit_ids
from app.models import Alert, Device, MetricReading, Site, StorageUnit, User
from app.schemas import (
    PluviometryMapSiteOut,
    PluviometryMapSnapshotOut,
    PluviometryParcelOut,
    PluviometrySiteOut,
    RainGaugeLatestMetricsOut,
    RainGaugeMapDeviceOut,
)
from app.services.telemetry import device_communication_status
from app.services.company_features import PLUVIOMETRY, enabled_company_ids, require_company_feature


POPUP_METRICS = {
    "AMBIENT_TEMPERATURE_C": "temperature_c",
    "AMBIENT_RELATIVE_HUMIDITY_PCT": "humidity_pct",
    "WIND_SPEED_KMH": "wind_speed_kmh",
    "WIND_DIRECTION_DEG": "wind_direction_deg",
    "BATTERY_PERCENT": "battery_pct",
}


def _authorized_field_units(db: Session, user: User, *, site_id: int | None = None) -> list[StorageUnit]:
    entitled_company_ids = enabled_company_ids(db, PLUVIOMETRY)
    if not entitled_company_ids:
        return []
    stmt = select(StorageUnit).where(
        StorageUnit.company_id.in_(entitled_company_ids),
        StorageUnit.operation_type == "field",
        StorageUnit.is_active.is_(True),
        StorageUnit.deleted_at.is_(None),
    )
    if site_id is not None:
        stmt = stmt.where(StorageUnit.site_id == site_id)
    if user.role != "admin":
        unit_ids = assigned_storage_unit_ids(db, user)
        if not unit_ids:
            return []
        stmt = stmt.where(StorageUnit.id.in_(unit_ids))
    return list(db.scalars(stmt.order_by(StorageUnit.name, StorageUnit.id)).all())


def list_pluviometry_sites(db: Session, user: User) -> list[PluviometrySiteOut]:
    units = _authorized_field_units(db, user)
    if not units:
        return []
    unit_ids = [unit.id for unit in units]
    site_ids = sorted({unit.site_id for unit in units})
    counts = dict(
        db.execute(
            select(Device.site_id, func.count(Device.id))
            .where(
                Device.storage_unit_id.in_(unit_ids),
                Device.device_type == "rain_gauge",
                Device.deleted_at.is_(None),
            )
            .group_by(Device.site_id)
        ).all()
    )
    sites = db.scalars(select(Site).where(Site.id.in_(site_ids)).order_by(Site.name, Site.id)).all()
    return [
        PluviometrySiteOut(
            id=site.id,
            name=site.name,
            latitude=site.latitude,
            longitude=site.longitude,
            timezone=site.timezone,
            rain_gauge_count=int(counts.get(site.id, 0)),
        )
        for site in sites
    ]


def _utc_day_window(site: Site, now: datetime) -> tuple[datetime, datetime]:
    reference = now if now.tzinfo is not None else now.replace(tzinfo=timezone.utc)
    try:
        local_zone = ZoneInfo(site.timezone)
    except ZoneInfoNotFoundError:
        local_zone = timezone.utc
    local_now = reference.astimezone(local_zone)
    local_midnight = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    return local_midnight.astimezone(timezone.utc), reference.astimezone(timezone.utc)


def _latest_metrics(db: Session, device_ids: list[int]) -> dict[int, dict[str, float]]:
    if not device_ids:
        return {}
    ranked = (
        select(
            MetricReading.device_id.label("device_id"),
            MetricReading.metric_code.label("metric_code"),
            MetricReading.raw_value.label("raw_value"),
            MetricReading.calibrated_value.label("calibrated_value"),
            MetricReading.display_value.label("display_value"),
            func.row_number()
            .over(
                partition_by=(MetricReading.device_id, MetricReading.metric_code),
                order_by=(MetricReading.sampled_at.desc(), MetricReading.id.desc()),
            )
            .label("position"),
        )
        .where(
            MetricReading.device_id.in_(device_ids),
            MetricReading.metric_code.in_(tuple(POPUP_METRICS)),
        )
        .subquery()
    )
    rows = db.execute(select(ranked).where(ranked.c.position == 1)).all()
    result: dict[int, dict[str, float]] = {}
    for row in rows:
        value = row.display_value
        if value is None:
            value = row.calibrated_value if row.calibrated_value is not None else row.raw_value
        result.setdefault(row.device_id, {})[POPUP_METRICS[row.metric_code]] = float(value)
    return result


def _rain_today(
    db: Session,
    device_ids: list[int],
    *,
    start_utc: datetime,
    end_utc: datetime,
) -> dict[int, float]:
    if not device_ids:
        return {}
    value = func.coalesce(MetricReading.display_value, MetricReading.calibrated_value, MetricReading.raw_value)
    rows = db.execute(
        select(MetricReading.device_id, func.sum(value))
        .where(
            MetricReading.device_id.in_(device_ids),
            MetricReading.metric_code == "RAIN_DELTA_MM",
            MetricReading.sampled_at >= start_utc,
            MetricReading.sampled_at <= end_utc,
        )
        .group_by(MetricReading.device_id)
    ).all()
    return {device_id: round(float(total), 3) for device_id, total in rows if total is not None}


def build_pluviometry_map_snapshot(
    db: Session,
    user: User,
    site_id: int,
    *,
    now: datetime | None = None,
) -> PluviometryMapSnapshotOut:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    require_company_feature(db, site.company_id, PLUVIOMETRY)

    parcels = _authorized_field_units(db, user, site_id=site_id)
    if user.role != "admin" and not parcels:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para esta seccion.")

    parcel_ids = [parcel.id for parcel in parcels]
    devices = []
    if parcel_ids:
        devices = list(
            db.scalars(
                select(Device)
                .where(
                    Device.site_id == site_id,
                    Device.storage_unit_id.in_(parcel_ids),
                    Device.device_type == "rain_gauge",
                    Device.deleted_at.is_(None),
                )
                .order_by(Device.name, Device.id)
            ).all()
        )
    device_ids = [device.id for device in devices]
    current_time = now or datetime.now(timezone.utc)
    start_utc, end_utc = _utc_day_window(site, current_time)
    latest = _latest_metrics(db, device_ids)
    rain = _rain_today(db, device_ids, start_utc=start_utc, end_utc=end_utc)
    critical_ids = set()
    if device_ids:
        critical_ids = set(
            db.scalars(
                select(Alert.device_id)
                .where(
                    Alert.device_id.in_(device_ids),
                    Alert.is_active.is_(True),
                    Alert.resolved_at.is_(None),
                    func.lower(Alert.severity) == "critical",
                )
                .distinct()
            ).all()
        )
    parcel_names = {parcel.id: parcel.name for parcel in parcels}
    output_devices = []
    for device in devices:
        communication = device_communication_status(device, current_time).lower()
        if communication == "degraded":
            communication = "delayed"
        device_status = "critical" if device.id in critical_ids else communication
        output_devices.append(
            RainGaugeMapDeviceOut(
                id=device.id,
                device_id=device.external_id,
                name=device.name,
                storage_unit_id=device.storage_unit_id,
                parcel_name=parcel_names[device.storage_unit_id],
                latitude=device.latitude,
                longitude=device.longitude,
                status=device_status,
                last_seen_at=device.last_seen_at,
                latest=RainGaugeLatestMetricsOut(**latest.get(device.id, {})),
                rain_today_mm=rain.get(device.id),
            )
        )

    return PluviometryMapSnapshotOut(
        site=PluviometryMapSiteOut(
            id=site.id,
            name=site.name,
            latitude=site.latitude,
            longitude=site.longitude,
            timezone=site.timezone,
            boundary_geojson=site.boundary_geojson,
        ),
        parcels=[
            PluviometryParcelOut(
                id=parcel.id,
                name=parcel.name,
                boundary_geojson=parcel.boundary_geojson,
                surface_hectares=parcel.surface_hectares,
            )
            for parcel in parcels
        ],
        devices=output_devices,
    )
