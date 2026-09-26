"""Seed local-only pluviometry demo data for Quillacollo.

This script is intentionally separate from Alembic and refuses to run outside
the local SQLite environment. Re-running it updates the demo topology and
replaces only the telemetry owned by the two demo rain gauges.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_secret
from app.db.session import SessionLocal
from app.models import (
    Company,
    CompanyFeature,
    Device,
    DeviceChannel,
    MetricDefinition,
    MetricReading,
    Site,
    StorageUnit,
    TelemetryEvent,
)
from app.services.device_capabilities import ensure_metric_registry, sync_device_channels
from app.services.company_features import PLUVIOMETRY


DEMO_COMPANY = "AgroEscudo Demo"
DEMO_SITE = "Demo Quillacollo"
DEMO_DEVICE_IDS = ("DEMO-PLUV-QLO-01", "DEMO-PLUV-QLO-02")
CADENCE_MINUTES = 15
DEMO_DAYS = 7

SITE_BOUNDARY = {
    "type": "Polygon",
    "coordinates": [[
        [-66.2900, -17.4020],
        [-66.2725, -17.4020],
        [-66.2725, -17.3895],
        [-66.2900, -17.3895],
        [-66.2900, -17.4020],
    ]],
}

DEMO_ASSETS = (
    {
        "external_id": DEMO_DEVICE_IDS[0],
        "name": "P-01 Manaco",
        "parcel": "Sector Manaco · DEMO",
        "reference": "Barrio Manaco / Calle Brasil · Quillacollo, Cochabamba · DEMO",
        "latitude": -17.3977,
        "longitude": -66.2862,
        "boundary": {
            "type": "Polygon",
            "coordinates": [[
                [-66.2884, -17.3995],
                [-66.2838, -17.3995],
                [-66.2838, -17.3957],
                [-66.2884, -17.3957],
                [-66.2884, -17.3995],
            ]],
        },
    },
    {
        "external_id": DEMO_DEVICE_IDS[1],
        "name": "P-02 Plaza Bolívar",
        "parcel": "Sector Plaza Bolívar · DEMO",
        "reference": "Plaza Bolívar · Quillacollo, Cochabamba · DEMO",
        "latitude": -17.3942,
        "longitude": -66.2764,
        "boundary": {
            "type": "Polygon",
            "coordinates": [[
                [-66.2786, -17.3960],
                [-66.2743, -17.3960],
                [-66.2743, -17.3922],
                [-66.2786, -17.3922],
                [-66.2786, -17.3960],
            ]],
        },
    },
)


def seed_pluviometry_demo(db: Session, *, now: datetime | None = None) -> dict[str, int]:
    ensure_metric_registry(db)
    generated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    generated_at = generated_at.replace(
        minute=(generated_at.minute // CADENCE_MINUTES) * CADENCE_MINUTES,
        second=0,
        microsecond=0,
    )

    company = db.scalar(select(Company).where(Company.name == DEMO_COMPANY))
    if company is None:
        company = Company(name=DEMO_COMPANY)
        db.add(company)
    company.tax_id = "DEMO-NO-FISCAL"
    company.type = "demo"
    company.city = "Quillacollo, Cochabamba"
    company.contact_name = "Datos demostrativos"
    company.contact_email = None
    company.contact_phone = None
    company.is_active = True
    company.approval_status = "APPROVED"
    company.rejection_reason = None
    db.flush()

    feature = db.scalar(select(CompanyFeature).where(
        CompanyFeature.company_id == company.id,
        CompanyFeature.feature_code == PLUVIOMETRY,
    ))
    if feature is None:
        feature = CompanyFeature(company_id=company.id, feature_code=PLUVIOMETRY)
        db.add(feature)
    feature.enabled = True
    feature.enabled_at = generated_at

    site = db.scalar(select(Site).where(Site.company_id == company.id, Site.name == DEMO_SITE))
    if site is None:
        site = Site(company_id=company.id, name=DEMO_SITE)
        db.add(site)
    site.location = "Quillacollo, Cochabamba · Ubicaciones aproximadas de demostración"
    site.address = "Sectores demostrativos Manaco y Plaza Bolívar"
    site.department = "Cochabamba"
    site.municipality = "Quillacollo"
    site.timezone = "America/La_Paz"
    site.latitude = -17.3960
    site.longitude = -66.2813
    site.boundary_geojson = SITE_BOUNDARY
    db.flush()

    devices: list[Device] = []
    for asset in DEMO_ASSETS:
        parcel = db.scalar(
            select(StorageUnit).where(StorageUnit.site_id == site.id, StorageUnit.name == asset["parcel"])
        )
        if parcel is None:
            parcel = StorageUnit(
                company_id=company.id,
                site_id=site.id,
                name=asset["parcel"],
                unit_type="parcela_demo",
            )
            db.add(parcel)
        parcel.company_id = company.id
        parcel.site_id = site.id
        parcel.operation_type = "field"
        parcel.location = asset["reference"]
        parcel.surface_hectares = 0.12
        parcel.crop_type = "DEMO"
        parcel.boundary_geojson = asset["boundary"]
        parcel.is_active = True
        parcel.deleted_at = None
        db.flush()

        device = db.scalar(select(Device).where(Device.external_id == asset["external_id"]))
        if device is None:
            device = Device(
                company_id=company.id,
                site_id=site.id,
                storage_unit_id=parcel.id,
                external_id=asset["external_id"],
                name=asset["name"],
                token_hash=hash_secret(f"local-demo-only:{asset['external_id']}"),
            )
            db.add(device)
        device.company_id = company.id
        device.site_id = site.id
        device.storage_unit_id = parcel.id
        device.name = asset["name"]
        device.device_type = "rain_gauge"
        device.model_version = "DEMO"
        device.physical_location = asset["reference"]
        device.latitude = asset["latitude"]
        device.longitude = asset["longitude"]
        device.template_code = "RAIN_GAUGE_BASE"
        device.operational_status = "demo"
        device.expected_reading_interval_minutes = CADENCE_MINUTES
        device.is_active = True
        device.deleted_at = None
        device.installed_at = generated_at - timedelta(days=DEMO_DAYS)
        device.last_seen_at = generated_at
        db.flush()
        sync_device_channels(db, device, template_code="RAIN_GAUGE_BASE")
        devices.append(device)

    device_ids = [device.id for device in devices]
    db.execute(delete(MetricReading).where(MetricReading.device_id.in_(device_ids)))
    db.execute(delete(TelemetryEvent).where(TelemetryEvent.device_id.in_(device_ids)))
    db.flush()

    definitions = {
        definition.metric_code: definition
        for definition in db.scalars(select(MetricDefinition)).all()
    }
    reading_count = 0
    samples_per_device = DEMO_DAYS * 24 * (60 // CADENCE_MINUTES) + 1
    start = generated_at - timedelta(days=DEMO_DAYS)
    for device_index, device in enumerate(devices):
        channels = {
            code: channel
            for channel in db.scalars(select(DeviceChannel).where(DeviceChannel.device_id == device.id)).all()
            for code in (channel.metric_codes or "").split(",")
            if code
        }
        for sequence in range(samples_per_device):
            sampled_at = start + timedelta(minutes=sequence * CADENCE_MINUTES)
            event = TelemetryEvent(
                company_id=device.company_id,
                storage_unit_id=device.storage_unit_id,
                device_id=device.id,
                boot_id=3100 + device_index,
                sequence=sequence,
                sample_counter=sequence,
                sampled_at=sampled_at,
                received_at_gateway=sampled_at + timedelta(seconds=2),
                received_at_cloud=sampled_at + timedelta(seconds=4),
                time_quality="VALID",
                firmware_version="demo-1.0",
                protocol_version=1,
                capabilities_version=device.capabilities_version,
                quality_summary="VALID",
            )
            db.add(event)
            db.flush()
            values = _demo_values(device_index, sequence, samples_per_device, sampled_at)
            for metric_code, value in values.items():
                definition = definitions[metric_code]
                channel = channels[metric_code]
                db.add(MetricReading(
                    telemetry_event_id=event.id,
                    company_id=device.company_id,
                    storage_unit_id=device.storage_unit_id,
                    device_id=device.id,
                    sensor_channel_id=channel.id,
                    metric_definition_id=definition.id,
                    metric_code=metric_code,
                    raw_value=value,
                    display_value=value,
                    canonical_unit=definition.canonical_unit,
                    quality_status="VALID_DEMO",
                    sampled_at=sampled_at,
                    received_at=sampled_at + timedelta(seconds=4),
                ))
                reading_count += 1
        for channel in channels.values():
            channel.status = "ONLINE"
            channel.last_valid_reading_at = generated_at

    db.commit()
    return {
        "company_id": company.id,
        "site_id": site.id,
        "devices": len(devices),
        "samples_per_device": samples_per_device,
        "metric_readings": reading_count,
    }


def _demo_values(device_index: int, sequence: int, total: int, sampled_at: datetime) -> dict[str, float]:
    progress = sequence / max(total - 1, 1)
    local_hour = (sampled_at - timedelta(hours=4)).hour + sampled_at.minute / 60
    daily_wave = math.sin(2 * math.pi * (local_hour - 8) / 24)
    slow_wave = math.sin(2 * math.pi * sequence / (96 * 3))
    temperature = 19.5 + device_index * 0.7 + 5.2 * daily_wave + 0.8 * slow_wave
    humidity = max(38.0, min(92.0, 69.0 - 0.95 * (temperature - 19.5) + 2.0 * slow_wave))
    wind_speed = max(1.5, 9.0 + device_index * 1.2 + 3.4 * math.sin(2 * math.pi * sequence / 40))
    rain = _rain_delta(device_index, total - 1 - sequence)
    direction = _wind_direction(device_index, sequence, total)
    battery = (95.0 + device_index) - 2.0 * progress
    return {
        "RAIN_DELTA_MM": round(rain, 1),
        "AMBIENT_TEMPERATURE_C": round(temperature, 1),
        "AMBIENT_RELATIVE_HUMIDITY_PCT": round(humidity, 1),
        "WIND_SPEED_KMH": round(wind_speed, 1),
        "WIND_DIRECTION_DEG": round(direction % 360, 1),
        "BATTERY_PERCENT": round(battery, 1),
    }


def _rain_delta(device_index: int, age_samples: int) -> float:
    light = [0.2, 0.4, 0.6, 0.3, 0.1]
    moderate = [0.8, 1.4, 2.1, 2.8, 2.2, 1.5, 0.7]
    if 24 <= age_samples < 24 + len(light):
        return light[age_samples - 24]
    event_offset = 100 if device_index == 0 else 132
    if event_offset <= age_samples < event_offset + len(moderate):
        return moderate[age_samples - event_offset]
    if 310 <= age_samples < 310 + len(light):
        return light[age_samples - 310]
    return 0.0


def _wind_direction(device_index: int, sequence: int, total: int) -> float:
    if device_index == 0:
        # Explicitly exercise the north crossing without making 180° appear.
        crossing = {total - 4: 359.0, total - 3: 1.0, total - 2: 5.0, total - 1: 45.0}
        if sequence in crossing:
            return crossing[sequence]
        phase = sequence % 96
        base = 45.0 if phase < 34 or phase >= 70 else 88.0
        return base + 7.0 * math.sin(2 * math.pi * sequence / 24)
    phase = sequence % 96
    base = 180.0 if phase < 32 else 225.0 if phase < 68 else 270.0
    return base + 8.0 * math.sin(2 * math.pi * sequence / 32)


def main() -> None:
    if settings.environment.lower().strip() != "local" or settings.database_backend != "sqlite":
        raise SystemExit("Este seed DEMO solo puede ejecutarse con ENVIRONMENT=local y SQLite.")
    db = SessionLocal()
    try:
        result = seed_pluviometry_demo(db)
    finally:
        db.close()
    print(
        "Seed DEMO de pluviometría completado: "
        f"{result['devices']} pluviómetros, "
        f"{result['samples_per_device']} muestras por equipo, "
        f"{result['metric_readings']} valores canónicos."
    )


if __name__ == "__main__":
    main()
