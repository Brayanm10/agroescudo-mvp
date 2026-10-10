from datetime import datetime, timedelta, timezone
import math

import pytest
from sqlalchemy import func, select

from app.core.security import hash_secret
from app.models import Company, Device, IotDevice, IotGateway, MetricReading, Site, StorageUnit, TelemetryEvent, User
from app.schemas import IotBatchReadingIn
from app.services.agua_suelo_demo import DEMO_MODEL, historical_event, inspect_account, prepare_demo, seed_history, signed_ingest
from app.services.device_capabilities import ensure_metric_registry
from app.services.pluviometry import build_pluviometry_map_snapshot


def prepared(db):
    ensure_metric_registry(db)
    user = db.scalar(select(User).where(User.email == "cliente@silo-demo.local"))
    admin = db.scalar(select(User).where(User.role == "admin"))
    arguments = dict(email=user.email, company_id=user.company_id, actor_id=admin.id,
                     latitude=-17.3928, longitude=-66.2814, location_reference="Ubicación virtual de prueba",
                     physical_id="DEMO-AGUA-SUELO-P01", gateway_id="DEMO-AGUA-SUELO-GW01", node_id=81001)
    device, gateway, secret = prepare_demo(db, **arguments)
    db.commit()
    return user, device, gateway, secret, arguments


def test_preparation_is_idempotent_and_preserves_existing_device(db_session):
    original = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    values = (original.name, original.site_id, original.model_version, original.expected_reading_interval_minutes)
    user, device, gateway, secret, arguments = prepared(db_session)
    second, second_gateway, new_secret = prepare_demo(db_session, **arguments)
    assert second.id == device.id and second_gateway.id == gateway.id and new_secret is None
    assert secret and device.model_version == DEMO_MODEL
    assert values == (original.name, original.site_id, original.model_version, original.expected_reading_interval_minutes)
    snapshot = build_pluviometry_map_snapshot(db_session, user, site_id=device.site_id)
    assert snapshot.devices[0].is_demo and snapshot.devices[0].status == "offline"
    assert snapshot.site.timezone == "America/La_Paz"


def test_missing_account_is_not_created(db_session):
    assert not inspect_account(db_session, "missing@example.test")["exists"]
    assert not db_session.scalar(select(User).where(User.email == "missing@example.test"))


def test_refuses_other_company_and_non_admin(db_session):
    user, _, _, _, args = prepared(db_session)
    with pytest.raises(ValueError, match="empresa"):
        prepare_demo(db_session, **{**args, "company_id": args["company_id"] + 999})
    with pytest.raises(ValueError, match="Administrador"):
        prepare_demo(db_session, **{**args, "actor_id": user.id})


def test_existing_real_id_never_repurposed(db_session):
    _, _, _, _, args = prepared(db_session)
    real = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    real.external_id = "DEMO-OCCUPIED"; db_session.flush()
    with pytest.raises(ValueError, match="no DEMO"):
        prepare_demo(db_session, **{**args, "physical_id": real.external_id})
    assert real.model_version != DEMO_MODEL


def test_six_metrics_schema_ranges_and_incremental_rain():
    start = datetime(2026, 9, 24, tzinfo=timezone.utc)
    events = [historical_event("DEMO-TEST", start + timedelta(minutes=i), i, 100) for i in range(1440)]
    for event in events:
        reading = IotBatchReadingIn.model_validate(event)
        assert len(reading.metrics) == 6
        assert all(math.isfinite(m.raw_value) for m in reading.metrics)
    rain = [event["metrics"][0]["raw_value"] for event in events]
    assert sum(rain) == pytest.approx(12)  # 6 mm/hour for two hours, not a cumulative counter.
    assert rain.count(0) == 1320


def test_hmac_ingestion_duplicate_and_live_state(db_session):
    user, device, gateway, secret, _ = prepared(db_session)
    event = historical_event(device.external_id, datetime.now(timezone.utc), 0, 811)
    event["firmware_version"] = "agua-suelo-demo-1.0.0"
    first = signed_ingest(db_session, gateway, secret, [event])
    duplicate = signed_ingest(db_session, gateway, secret, [event])
    assert first.results[0].canonical_status == "ACCEPTED"
    assert duplicate.results[0].canonical_status == "DUPLICATE"
    assert db_session.scalar(select(func.count(TelemetryEvent.id)).where(TelemetryEvent.device_id == device.id)) == 1
    assert db_session.scalar(select(func.count(MetricReading.id)).where(MetricReading.device_id == device.id)) == 6
    assert build_pluviometry_map_snapshot(db_session, user, site_id=device.site_id).devices[0].status == "online"
    with pytest.raises(Exception) as failure:
        signed_ingest(db_session, gateway, "invalid-test-secret", [event])
    assert failure.value.status_code == 401


def test_gateway_cannot_ingest_real_device_or_reveal_duplicate(db_session):
    _, device, gateway, secret, _ = prepared(db_session)
    original = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    event = historical_event(original.external_id, datetime.now(timezone.utc), 0, 0)
    result = signed_ingest(db_session, gateway, secret, [event])
    assert result.results[0].canonical_status == "REJECTED"
    assert db_session.scalar(select(func.count(TelemetryEvent.id)).where(TelemetryEvent.device_id == original.id)) == 0


def test_assigned_gateway_with_wrong_tenant_scope_is_rejected(db_session):
    _, device, gateway, secret, _ = prepared(db_session)
    other = Company(name="Other company"); db_session.add(other); db_session.flush()
    gateway.company_id = other.id; db_session.commit()
    result = signed_ingest(db_session, gateway, secret, [historical_event(device.external_id, datetime.now(timezone.utc), 0, 50)])
    assert result.results[0].canonical_status == "REJECTED"


def test_history_is_idempotent_and_does_not_make_device_online(db_session):
    _, device, gateway, secret, _ = prepared(db_session)
    start = (datetime.now(timezone.utc) - timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
    first = seed_history(db_session, device=device, gateway=gateway, secret=secret, start=start, days=1)
    second = seed_history(db_session, device=device, gateway=gateway, secret=secret, start=start, days=1)
    assert first == {"ACCEPTED": 1440, "DUPLICATE": 0}
    assert second == {"ACCEPTED": 0, "DUPLICATE": 1440}
    assert device.last_seen_at is None
    with pytest.raises(ValueError, match="solapa"):
        seed_history(db_session, device=device, gateway=gateway, secret=secret, start=start + timedelta(hours=1), days=1)


def test_history_cannot_target_real_device(db_session):
    _, _, gateway, secret, _ = prepared(db_session)
    real = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    with pytest.raises(ValueError, match="exclusivamente"):
        seed_history(db_session, device=real, gateway=gateway, secret=secret, start=datetime.now(timezone.utc) - timedelta(days=2), days=1)
