from datetime import datetime, timedelta, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, select, text

from app.core.config import settings
from app.core.security import hash_secret
from app.domain.device_templates import DEVICE_TEMPLATES
from app.domain.metric_registry import METRICS_BY_CODE
from app.models import Company, Device, DeviceChannel, Site, StorageUnit, User
from app.schemas import DeviceCreate, IotBatchReadingIn, IotMetricIn, SiteCreate, StorageUnitCreate
from app.services.telemetry import (
    device_communication_status,
    sensor_profile,
    validate_device_unit_compatibility,
)
from app.services.telemetry_queries import _aggregate, _aggregate_values, _detect_gaps
from app.schemas import MetricReadingPointOut


def _login(client, email="admin@agroescudo.local", password="admin123"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _points(values):
    start = datetime(2026, 9, 24, 12, 1, tzinfo=timezone.utc)
    return [
        MetricReadingPointOut(
            device_id=1,
            channel_key="test_1",
            metric_code="TEST",
            value=value,
            unit="unit",
            quality_status="VALID",
            sampled_at=start + timedelta(minutes=index),
            source="normalized",
        )
        for index, value in enumerate(values)
    ]


def test_rain_gauge_is_explicit_profile_and_requires_field_unit():
    device = Device(device_type="rain_gauge")
    assert sensor_profile(device) == "rain_gauge"
    assert sensor_profile(device) != "silo_sensor"
    validate_device_unit_compatibility("rain_gauge", "field")
    with pytest.raises(ValueError):
        validate_device_unit_compatibility("rain_gauge", "storage")


def test_legacy_device_profiles_remain_explicit():
    assert sensor_profile(Device(device_type="silo_sensor")) == "silo_sensor"
    assert sensor_profile(Device(device_type="esp32_lora_node")) == "silo_sensor"
    assert sensor_profile(Device(device_type="field_sensor")) == "field_sensor"
    assert sensor_profile(Device(device_type="unregistered")) == "unknown"


def test_rain_gauge_template_contains_the_six_canonical_channels():
    channels = DEVICE_TEMPLATES["RAIN_GAUGE_BASE"]
    assert {channel["channel_key"]: channel["metric_codes"] for channel in channels} == {
        "rain_1": ("RAIN_DELTA_MM",),
        "ambient_temp_1": ("AMBIENT_TEMPERATURE_C",),
        "ambient_rh_1": ("AMBIENT_RELATIVE_HUMIDITY_PCT",),
        "wind_speed_1": ("WIND_SPEED_KMH",),
        "wind_direction_1": ("WIND_DIRECTION_DEG",),
        "battery_1": ("BATTERY_PERCENT",),
    }


@pytest.mark.parametrize(
    ("metric_code", "values", "expected"),
    [
        ("RAIN_DELTA_MM", [0.2, 0.4, 0.1], 0.7),
        ("AMBIENT_TEMPERATURE_C", [20.0, 22.0, 24.0], 22.0),
        ("AMBIENT_RELATIVE_HUMIDITY_PCT", [60.0, 66.0, 72.0], 66.0),
        ("WIND_SPEED_KMH", [6.0, 12.0, 18.0], 12.0),
        ("BATTERY_PERCENT", [90.0, 84.0, 81.0], 81.0),
    ],
)
def test_metric_registry_drives_bucket_aggregation(metric_code, values, expected):
    strategy = METRICS_BY_CODE[metric_code].aggregation_strategy
    result = _aggregate(_points(values), "1h", strategy)
    assert len(result) == 1
    assert result[0].value == pytest.approx(expected)


def test_wind_direction_uses_circular_mean():
    strategy = METRICS_BY_CODE["WIND_DIRECTION_DEG"].aggregation_strategy
    result = _aggregate(_points([359.0, 1.0]), "1h", strategy)
    angle = result[0].value
    assert angle is not None
    assert min(abs(angle), abs(angle - 360)) < 0.001
    assert angle != pytest.approx(180.0)


def test_hil_wifi_gap_is_absence_and_does_not_add_zero_rain():
    start = datetime(2026, 9, 26, 5, 0, tzinfo=timezone.utc)
    points = [
        MetricReadingPointOut(
            device_id=7,
            channel_key="rain_1",
            metric_code="RAIN_DELTA_MM",
            value=value,
            unit="mm",
            quality_status="VALID",
            sampled_at=sampled_at,
            source="normalized",
        )
        for value, sampled_at in (
            (0.4, start),
            (0.6, start + timedelta(minutes=16)),
        )
    ]

    gaps, _ = _detect_gaps(points, cadence_minutes=1)
    assert len(gaps) == 1
    assert gaps[0].duration_seconds == 16 * 60
    assert _aggregate(points, "1h", "sum")[0].value == pytest.approx(1.0)


def test_all_supported_aggregation_strategies():
    assert _aggregate_values([2.0, 4.0], "avg") == 3.0
    assert _aggregate_values([2.0, 4.0], "sum") == 6.0
    assert _aggregate_values([2.0, 4.0], "min") == 2.0
    assert _aggregate_values([2.0, 4.0], "max") == 4.0
    assert _aggregate_values([2.0, 4.0], "last") == 4.0


@pytest.mark.parametrize(
    ("metric_code", "value"),
    [
        ("RAIN_DELTA_MM", -0.1),
        ("AMBIENT_RELATIVE_HUMIDITY_PCT", 100.1),
        ("WIND_DIRECTION_DEG", 360.0),
        ("WIND_SPEED_KMH", -0.1),
        ("BATTERY_PERCENT", 100.1),
    ],
)
def test_invalid_pluviometry_metric_values_are_rejected(metric_code, value):
    with pytest.raises(ValidationError):
        IotMetricIn(channel_key="test_1", metric_code=metric_code, raw_value=value, unit="unit")


def test_rain_gauge_sampled_at_requires_timezone():
    with pytest.raises(ValidationError):
        IotBatchReadingIn(
            device_id=1,
            boot_id=1,
            sequence=1,
            sample_counter=1,
            sampled_at=datetime(2026, 9, 24, 12, 0),
            time_quality=1,
            firmware_version="1.0",
            sensor_profile="rain_gauge",
            metrics=[
                IotMetricIn(
                    channel_key="rain_1",
                    metric_code="RAIN_DELTA_MM",
                    raw_value=0.2,
                    unit="mm",
                )
            ],
        )


def test_coordinates_and_geojson_validation():
    device = DeviceCreate(
        company_id=1,
        site_id=1,
        storage_unit_id=1,
        external_id="P-01",
        name="Pluviometro 01",
        device_token="secret",
        device_type="rain_gauge",
        latitude=-17.78,
        longitude=-63.18,
        template_code="RAIN_GAUGE_BASE",
    )
    assert device.latitude == -17.78
    assert SiteCreate(
        company_id=1,
        name="Predio",
        boundary_geojson={"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0, 1], [0, 0]]]},
    ).boundary_geojson["type"] == "Polygon"
    assert StorageUnitCreate(
        company_id=1,
        site_id=1,
        name="Parcela",
        unit_type="parcela",
        operation_type="field",
        boundary_geojson={"type": "MultiPolygon", "coordinates": [[[[0, 0], [1, 0], [0, 1], [0, 0]]]]},
    ).boundary_geojson["type"] == "MultiPolygon"
    with pytest.raises(ValidationError):
        DeviceCreate(
            company_id=1,
            site_id=1,
            storage_unit_id=1,
            external_id="P-02",
            name="Pluviometro 02",
            device_token="secret",
            device_type="rain_gauge",
            latitude=91,
            longitude=-63.18,
        )


def test_admin_can_create_located_rain_gauge_with_canonical_template(client, db_session):
    company = db_session.scalar(select(Company).where(Company.name == "AgroEscudo Demo"))
    site = db_session.scalar(select(Site).where(Site.company_id == company.id))
    field = StorageUnit(
        company_id=company.id,
        site_id=site.id,
        name="Parcela Norte",
        unit_type="parcela",
        operation_type="field",
    )
    db_session.add(field)
    db_session.commit()

    response = client.post(
        "/api/admin/devices",
        headers=_login(client),
        json={
            "storage_unit_id": field.id,
            "external_id": "RAIN-001",
            "name": "Pluviometro P-01",
            "device_type": "rain_gauge",
            "latitude": -17.78,
            "longitude": -63.18,
            "template_code": "RAIN_GAUGE_BASE",
        },
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["device_type"] == "rain_gauge"
    assert payload["latitude"] == -17.78
    assert payload["longitude"] == -63.18
    channels = db_session.scalars(
        select(DeviceChannel).where(DeviceChannel.device_id == payload["id"])
    ).all()
    assert {channel.channel_key for channel in channels} == {
        "rain_1",
        "ambient_temp_1",
        "ambient_rh_1",
        "wind_speed_1",
        "wind_direction_1",
        "battery_1",
    }


def test_client_cannot_read_rain_gauge_from_another_company(client, db_session):
    company_b = Company(name="Empresa B")
    db_session.add(company_b)
    db_session.flush()
    site_b = Site(company_id=company_b.id, name="Predio B")
    db_session.add(site_b)
    db_session.flush()
    unit_b = StorageUnit(
        company_id=company_b.id,
        site_id=site_b.id,
        name="Parcela B",
        unit_type="parcela",
        operation_type="field",
    )
    db_session.add(unit_b)
    db_session.flush()
    client_b = User(
        company_id=company_b.id,
        email="cliente@empresa-b.local",
        full_name="Cliente B",
        hashed_password="unused",
        role="client",
    )
    db_session.add(client_b)
    db_session.flush()
    unit_b.assigned_client_id = client_b.id
    rain_b = Device(
        company_id=company_b.id,
        site_id=site_b.id,
        storage_unit_id=unit_b.id,
        external_id="RAIN-B-001",
        name="Pluviometro B",
        device_type="rain_gauge",
        token_hash=hash_secret("rain-b-secret"),
    )
    db_session.add(rain_b)
    db_session.commit()

    headers = _login(client, "cliente@silo-demo.local", "cliente123")
    response = client.get(f"/api/devices/{rain_b.id}", headers=headers)
    assert response.status_code == 403
    listed = client.get("/api/devices", headers=headers)
    assert rain_b.id not in {item["id"] for item in listed.json()}


def test_communication_status_uses_expected_interval():
    now = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)
    device = Device(
        device_type="rain_gauge",
        is_active=True,
        operational_status="operational",
        expected_reading_interval_minutes=10,
    )
    device.last_seen_at = now - timedelta(minutes=20)
    assert device_communication_status(device, now) == "ONLINE"
    device.last_seen_at = now - timedelta(minutes=21)
    assert device_communication_status(device, now) == "DELAYED"
    device.last_seen_at = now - timedelta(minutes=61)
    assert device_communication_status(device, now) == "OFFLINE"
    device.is_active = False
    assert device_communication_status(device, now) == "OFFLINE"


def test_hil_one_minute_cadence_uses_exact_online_delayed_offline_boundaries():
    last_seen = datetime(2026, 9, 26, 5, 0, tzinfo=timezone.utc)
    device = Device(
        device_type="rain_gauge",
        is_active=True,
        operational_status="operational",
        expected_reading_interval_minutes=1,
        last_seen_at=last_seen,
    )

    assert device_communication_status(device, last_seen + timedelta(minutes=2)) == "ONLINE"
    assert device_communication_status(device, last_seen + timedelta(minutes=2, seconds=1)) == "DELAYED"
    assert device_communication_status(device, last_seen + timedelta(minutes=6)) == "DELAYED"
    assert device_communication_status(device, last_seen + timedelta(minutes=6, seconds=1)) == "OFFLINE"


def test_alembic_upgrade_adds_pluviometry_core(tmp_path, monkeypatch):
    database_path = tmp_path / "pluviometry-upgrade.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    monkeypatch.setattr(settings, "database_url", database_url)
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))

    command.upgrade(config, "head")

    engine = create_engine(database_url)
    inspector = inspect(engine)
    assert "boundary_geojson" in {item["name"] for item in inspector.get_columns("sites")}
    assert "boundary_geojson" in {item["name"] for item in inspector.get_columns("storage_units")}
    assert {"latitude", "longitude"}.issubset({item["name"] for item in inspector.get_columns("devices")})
    assert "aggregation_strategy" in {item["name"] for item in inspector.get_columns("metric_definitions")}
    with engine.connect() as connection:
        strategies = dict(
            connection.execute(
                text(
                    "SELECT metric_code, aggregation_strategy FROM metric_definitions "
                    "WHERE metric_code IN ('RAIN_DELTA_MM', 'WIND_DIRECTION_DEG', 'BATTERY_PERCENT')"
                )
            ).all()
        )
    assert strategies == {
        "RAIN_DELTA_MM": "sum",
        "WIND_DIRECTION_DEG": "circular_mean",
        "BATTERY_PERCENT": "last",
    }
    engine.dispose()
