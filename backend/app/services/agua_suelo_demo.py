"""Scoped pilot preparation. Never creates users or alters existing real devices."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import math
import re
import secrets

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.security import encrypt_secret, hash_secret
from app.domain.metric_registry import METRICS_BY_CODE
from app.models import Company, Device, IotDevice, IotGateway, IotGatewayCredential, MetricDefinition, Site, StorageUnit, TelemetryEvent, User
from app.services.audit import record_audit_event
from app.services.company_features import PLUVIOMETRY, is_feature_enabled, set_company_feature
from app.services.device_capabilities import sync_device_channels
from app.services.iot_ingestion import ingest_gateway_batch

DEMO_MODEL = "AGUA_SUELO_DEMO_V1"
FIRMWARE = "agua-suelo-demo-1.0.0"
METRICS = (
    ("rain_1", "RAIN_DELTA_MM", "mm"),
    ("ambient_temp_1", "AMBIENT_TEMPERATURE_C", "degC"),
    ("ambient_rh_1", "AMBIENT_RELATIVE_HUMIDITY_PCT", "percent"),
    ("wind_speed_1", "WIND_SPEED_KMH", "km/h"),
    ("wind_direction_1", "WIND_DIRECTION_DEG", "degree"),
    ("battery_1", "BATTERY_PERCENT", "percent"),
)


def inspect_account(db: Session, email: str) -> dict:
    user = db.scalar(select(User).where(func.lower(User.email) == email.lower(), User.deleted_at.is_(None)))
    if user is None:
        return {"email": email, "exists": False, "blocker": "Crear cuenta mediante el flujo administrativo existente"}
    company = db.get(Company, user.company_id) if user.company_id else None
    devices = list(db.scalars(select(Device).where(Device.company_id == user.company_id, Device.deleted_at.is_(None)))) if company else []
    return {"email": user.email, "exists": True, "user_id": user.id, "role": user.role,
            "active": user.is_active, "company_id": user.company_id, "company": company.name if company else None,
            "pluviometry": is_feature_enabled(db, company.id, PLUVIOMETRY) if company else False,
            "devices": [{"id": d.id, "physical_id": d.external_id, "name": d.name,
                         "site_id": d.site_id, "parcel_id": d.storage_unit_id,
                         "demo": d.model_version == DEMO_MODEL,
                         "event_count": db.scalar(select(func.count(TelemetryEvent.id)).where(TelemetryEvent.device_id == d.id))}
                        for d in devices]}


def prepare_demo(db: Session, *, email: str, company_id: int, actor_id: int,
                 latitude: float, longitude: float, location_reference: str,
                 physical_id: str, gateway_id: str, node_id: int) -> tuple[Device, IotGateway, str | None]:
    account = inspect_account(db, email)
    if not account.get("exists") or account["company_id"] != company_id or not account["active"] or account["role"] != "client":
        raise ValueError("Cuenta cliente activa y empresa confirmada requeridas")
    actor = db.get(User, actor_id)
    company = db.get(Company, company_id)
    if not actor or actor.role != "admin" or not actor.is_active or actor.deleted_at or not company or not company.is_active or company.deleted_at:
        raise ValueError("Administrador activo y empresa activa requeridos")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180) or not location_reference.strip():
        raise ValueError("Coordenadas verificadas y referencia requeridas")
    if not re.fullmatch(r"DEMO-[A-Za-z0-9_-]{1,75}", physical_id) or not re.fullmatch(r"DEMO-[A-Za-z0-9_-]{1,75}", gateway_id) or node_id < 1:
        raise ValueError("Identificadores dedicados DEMO- y node_id positivo requeridos")
    # Validate the migrated registry without updating global definitions.
    for _, code, unit in METRICS:
        definition = db.scalar(select(MetricDefinition).where(MetricDefinition.metric_code == code))
        if not definition or definition.numeric_id != METRICS_BY_CODE[code].numeric_id or definition.canonical_unit != unit:
            raise ValueError("Registro canónico ausente/incompatible; revisar migraciones")
    existing = db.scalar(select(Device).where(Device.external_id == physical_id))
    if existing:
        if existing.company_id != company_id or existing.model_version != DEMO_MODEL or existing.deleted_at:
            raise ValueError("ID ocupado por equipo ajeno o no DEMO; no se modifica")
        parcel = db.get(StorageUnit, existing.storage_unit_id)
        link = db.scalar(select(IotDevice).where(IotDevice.device_id == existing.id))
        gateway = db.get(IotGateway, link.gateway_id) if link else None
        if not parcel or parcel.assigned_client_id != account["user_id"] or not gateway or gateway.gateway_id != gateway_id or gateway.company_id != company_id or not gateway.is_active or gateway.deleted_at or link.node_id != node_id or not link.is_active:
            raise ValueError("Configuración DEMO existente incompatible; revisar sin sobrescribir")
        if existing.latitude != latitude or existing.longitude != longitude or existing.expected_reading_interval_minutes != 1 or not existing.is_active or not is_feature_enabled(db, company_id, PLUVIOMETRY):
            raise ValueError("Configuración DEMO existente cambió; revisión administrativa requerida")
        return existing, gateway, None
    if db.scalar(select(IotGateway.id).where(IotGateway.gateway_id == gateway_id)) or db.scalar(select(IotDevice.id).where(IotDevice.node_id == node_id)):
        raise ValueError("Gateway/node_id ocupado; no se reutilizan credenciales")
    site = Site(company_id=company_id, name="Agua y Suelo · Estación DEMO", latitude=latitude,
                longitude=longitude, timezone="America/La_Paz", location="Ubicación DEMO: " + location_reference)
    db.add(site); db.flush()
    # A virtual plot, explicitly unrelated to a customer's surveyed property.
    ring = [[longitude-.0003, latitude-.0003], [longitude+.0003, latitude-.0003],
            [longitude+.0003, latitude+.0003], [longitude-.0003, latitude+.0003],
            [longitude-.0003, latitude-.0003]]
    parcel = StorageUnit(company_id=company_id, site_id=site.id, name="Parcela meteorológica · DEMO",
                         unit_type="parcela_demo", operation_type="field", location="Polígono virtual DEMO, no catastral",
                         boundary_geojson={"type": "Polygon", "coordinates": [ring]},
                         assigned_client_id=account["user_id"], is_active=True)
    db.add(parcel); db.flush()
    device = Device(company_id=company_id, site_id=site.id, storage_unit_id=parcel.id,
                    external_id=physical_id, name="Agua y Suelo · DEMO · SIMULADO", device_type="rain_gauge",
                    model_version=DEMO_MODEL, token_hash=hash_secret(secrets.token_urlsafe(32)),
                    latitude=latitude, longitude=longitude, physical_location="DEMO: " + location_reference,
                    expected_reading_interval_minutes=1, operational_status="demo", is_active=True)
    db.add(device); db.flush()
    sync_device_channels(db, device, template_code="RAIN_GAUGE_BASE")
    gateway = IotGateway(company_id=company_id, site_id=site.id, storage_unit_id=parcel.id,
                         gateway_id=gateway_id, name="Agua y Suelo · Gateway DEMO", is_active=True)
    db.add(gateway); db.flush()
    secret = secrets.token_urlsafe(32)
    db.add(IotGatewayCredential(gateway_id=gateway.id, key_version=1, secret_hash=hash_secret(secret), encrypted_secret=encrypt_secret(secret), is_active=True))
    db.add(IotDevice(node_id=node_id, device_id=device.id, gateway_id=gateway.id, firmware_version=FIRMWARE, is_active=True))
    if not is_feature_enabled(db, company_id, PLUVIOMETRY):
        set_company_feature(db, company_id=company_id, feature_code=PLUVIOMETRY, enabled=True, actor=actor)
    record_audit_event(db, action="pluviometry.demo_prepared", summary="Estación dedicada con datos simulados",
                       user=actor, company_id=company_id, resource_type="device", resource_id=device.id)
    db.flush()
    return device, gateway, secret


def historical_event(physical_id: str, timestamp: datetime, sequence: int, boot_id: int, *, interval_seconds: int = 60) -> dict:
    local_hour = (timestamp.hour - 4 + timestamp.minute / 60) % 24
    wave = math.sin(2 * math.pi * (local_hour - 8) / 24)
    rainy = timestamp.day % 3 == 0 and 14 <= local_hour < 16
    values = (6 * interval_seconds / 3600 if rainy else 0, 23 + 4 * wave - (2 if rainy else 0),
              65 - 12 * wave + (14 if rainy else 0), 9 + 3 * math.sin(sequence * .03) + (8 if rainy else 0),
              (225 + 25 * math.sin(sequence * .008)) % 360, 94 - 3 * math.sin(sequence * .0002)**2)
    return {"device_id": physical_id, "boot_id": boot_id, "sequence": sequence, "sample_counter": sequence,
            "timestamp_utc": int(timestamp.timestamp()), "time_quality": "NTP_SYNCED", "protocol_version": 4,
            "capabilities_version": 1, "firmware_version": "demo-history-1.0.0", "sensor_profile": "rain_gauge", "sensor_status_flags": 0,
            "metrics": [{"channel_key": channel, "metric_code": code, "unit": unit, "raw_value": value, "quality": "VALID"}
                        for (channel, code, unit), value in zip(METRICS, values)]}


def signed_ingest(db: Session, gateway: IotGateway, secret: str, events: list[dict]):
    now = datetime.now(timezone.utc)
    nonce = secrets.token_hex(16)
    body = json.dumps({"gateway_id": gateway.gateway_id, "batch_id": "demo-" + nonce, "sent_at": now.isoformat(),
                       "firmware_version": FIRMWARE, "protocol_version": 4, "events": events}, separators=(",", ":")).encode()
    stamp = str(int(now.timestamp()))
    signature = hmac.new(secret.encode(), (gateway.gateway_id + stamp + nonce + hashlib.sha256(body).hexdigest()).encode(), hashlib.sha256).hexdigest()
    return ingest_gateway_batch(db, body=body, gateway_header=gateway.gateway_id, timestamp_header=stamp,
                                nonce_header=nonce, signature_header=signature)


def seed_history(db: Session, *, device: Device, gateway: IotGateway, secret: str, start: datetime, days: int = 7) -> dict:
    if device.model_version != DEMO_MODEL or not device.external_id.startswith("DEMO-") or gateway.company_id != device.company_id:
        raise ValueError("Historial permitido exclusivamente en el equipo DEMO dedicado")
    if start.tzinfo is None or not 1 <= days <= 7 or start + timedelta(days=days) > datetime.now(timezone.utc):
        raise ValueError("Inicio UTC explícito, 1..7 días completos en el pasado requeridos")
    start = start.astimezone(timezone.utc)
    # Fixed start + boot + sequence make restart/re-run idempotent; fresh request nonce each time.
    boot = int.from_bytes(hashlib.sha256((device.external_id + start.isoformat()).encode()).digest()[:4], "big")
    if db.scalar(select(TelemetryEvent.id).where(
        TelemetryEvent.device_id == device.id,
        TelemetryEvent.firmware_version == "demo-history-1.0.0",
        TelemetryEvent.sampled_at >= start,
        TelemetryEvent.sampled_at < start + timedelta(days=days),
        TelemetryEvent.boot_id != boot,
    ).limit(1)):
        raise ValueError("La ventana solapa otro historial DEMO; reutilizar el inicio original")
    counts = {"ACCEPTED": 0, "DUPLICATE": 0}
    for offset in range(0, days * 1440, 100):
        events = [historical_event(device.external_id, start + timedelta(minutes=i), i, boot)
                  for i in range(offset, min(offset + 100, days * 1440))]
        result = signed_ingest(db, gateway, secret, events)
        for item in result.results:
            if item.canonical_status not in counts:
                raise ValueError("Historial detenido: " + item.canonical_status)
            counts[item.canonical_status] += 1
    return counts
