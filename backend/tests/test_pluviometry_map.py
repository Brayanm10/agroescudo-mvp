from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.security import hash_password, hash_secret
from app.models import (
    Company,
    Device,
    DeviceChannel,
    MetricDefinition,
    MetricReading,
    Site,
    StorageUnit,
    TelemetryEvent,
    User,
    utc_now,
)
from app.services.pluviometry import build_pluviometry_map_snapshot


def _login(client, email="admin@agroescudo.local", password="admin123"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _map_context(db_session):
    company = db_session.scalar(select(Company).where(Company.name == "AgroEscudo Demo"))
    site = db_session.scalar(select(Site).where(Site.company_id == company.id))
    site.name = "Predio Quillacollo"
    site.latitude = -17.39
    site.longitude = -66.16
    site.timezone = "America/La_Paz"
    site.boundary_geojson = {
        "type": "Polygon",
        "coordinates": [[[-66.2, -17.42], [-66.1, -17.42], [-66.1, -17.35], [-66.2, -17.42]]],
    }
    client_a = db_session.scalar(select(User).where(User.email == "cliente@silo-demo.local"))
    technician_a = db_session.scalar(select(User).where(User.email == "tecnico@agroescudo.local"))
    client_b = User(
        company_id=company.id,
        email="cliente-b@agroescudo.local",
        full_name="Cliente B",
        hashed_password=hash_password("clienteB123"),
        role="client",
    )
    technician_b = User(
        company_id=company.id,
        email="tecnico-b@agroescudo.local",
        full_name="Tecnico B",
        hashed_password=hash_password("tecnicoB123"),
        role="technician",
    )
    db_session.add_all([client_b, technician_b])
    db_session.flush()
    parcel_a = StorageUnit(
        company_id=company.id,
        site_id=site.id,
        name="Parcela A",
        unit_type="parcela",
        operation_type="field",
        surface_hectares=4.8,
        boundary_geojson={
            "type": "Polygon",
            "coordinates": [[[-66.19, -17.41], [-66.15, -17.41], [-66.15, -17.37], [-66.19, -17.41]]],
        },
        assigned_client_id=client_a.id,
        assigned_technician_id=technician_a.id,
    )
    parcel_b = StorageUnit(
        company_id=company.id,
        site_id=site.id,
        name="Parcela B",
        unit_type="parcela",
        operation_type="field",
        boundary_geojson={
            "type": "MultiPolygon",
            "coordinates": [[[[-66.14, -17.4], [-66.11, -17.4], [-66.11, -17.36], [-66.14, -17.4]]]],
        },
        assigned_client_id=client_b.id,
        assigned_technician_id=technician_b.id,
    )
    db_session.add_all([parcel_a, parcel_b])
    db_session.flush()
    gauge_a = Device(
        company_id=company.id,
        site_id=site.id,
        storage_unit_id=parcel_a.id,
        external_id="PLUV-A",
        name="Pluviometro A",
        token_hash=hash_secret("pluv-a"),
        device_type="rain_gauge",
        latitude=-17.39,
        longitude=-66.16,
        expected_reading_interval_minutes=10,
        last_seen_at=utc_now(),
    )
    gauge_b = Device(
        company_id=company.id,
        site_id=site.id,
        storage_unit_id=parcel_b.id,
        external_id="PLUV-B",
        name="Pluviometro B",
        token_hash=hash_secret("pluv-b"),
        device_type="rain_gauge",
        latitude=-17.38,
        longitude=-66.12,
        expected_reading_interval_minutes=10,
        last_seen_at=utc_now() - timedelta(hours=2),
    )
    db_session.add_all([gauge_a, gauge_b])
    db_session.commit()
    return site, parcel_a, parcel_b, gauge_a, gauge_b, client_a, technician_a


def test_admin_lists_and_maps_all_field_assets(client, db_session):
    site, parcel_a, parcel_b, gauge_a, gauge_b, *_ = _map_context(db_session)
    headers = _login(client)
    sites = client.get("/api/pluviometry/sites", headers=headers)
    assert sites.status_code == 200
    assert sites.json() == [{
        "id": site.id,
        "name": "Predio Quillacollo",
        "latitude": -17.39,
        "longitude": -66.16,
        "timezone": "America/La_Paz",
        "rain_gauge_count": 2,
    }]
    snapshot = client.get(f"/api/pluviometry/sites/{site.id}/map", headers=headers)
    assert snapshot.status_code == 200
    assert {item["id"] for item in snapshot.json()["parcels"]} == {parcel_a.id, parcel_b.id}
    assert {item["id"] for item in snapshot.json()["devices"]} == {gauge_a.id, gauge_b.id}


@pytest.mark.parametrize(
    ("email", "password"),
    [
        ("cliente@silo-demo.local", "cliente123"),
        ("tecnico@agroescudo.local", "tecnico123"),
    ],
)
def test_assigned_client_and_technician_only_receive_their_parcel(client, db_session, email, password):
    site, parcel_a, parcel_b, gauge_a, gauge_b, *_ = _map_context(db_session)
    response = client.get(f"/api/pluviometry/sites/{site.id}/map", headers=_login(client, email, password))
    assert response.status_code == 200
    payload = response.json()
    assert [parcel["id"] for parcel in payload["parcels"]] == [parcel_a.id]
    assert [device["id"] for device in payload["devices"]] == [gauge_a.id]
    assert parcel_b.id not in {parcel["id"] for parcel in payload["parcels"]}
    assert gauge_b.id not in {device["id"] for device in payload["devices"]}
    assert payload["parcels"][0]["boundary_geojson"] == parcel_a.boundary_geojson


def test_client_never_receives_another_clients_device_or_boundary(client, db_session):
    site, parcel_a, parcel_b, gauge_a, gauge_b, *_ = _map_context(db_session)
    payload = client.get(
        f"/api/pluviometry/sites/{site.id}/map",
        headers=_login(client, "cliente@silo-demo.local", "cliente123"),
    ).json()
    serialized = str(payload)
    assert gauge_b.external_id not in serialized
    assert parcel_b.name not in serialized
    assert str(parcel_b.boundary_geojson) not in serialized


def test_unauthorized_site_id_is_forbidden(client, db_session):
    _map_context(db_session)
    company = db_session.scalar(select(Company).where(Company.name == "AgroEscudo Demo"))
    other_site = Site(company_id=company.id, name="Predio no asignado")
    db_session.add(other_site)
    db_session.commit()
    response = client.get(
        f"/api/pluviometry/sites/{other_site.id}/map",
        headers=_login(client, "cliente@silo-demo.local", "cliente123"),
    )
    assert response.status_code == 403


def _add_metric(db_session, device, code, value, sampled_at, sequence):
    definition = db_session.scalar(select(MetricDefinition).where(MetricDefinition.metric_code == code))
    if definition is None:
        definition = MetricDefinition(
            numeric_id=900 + len(db_session.scalars(select(MetricDefinition.id)).all()),
            metric_code=code,
            display_name=code,
            description=code,
            canonical_unit="unit",
            storage_type="float",
            scale_factor=1,
            aggregation_strategy="sum" if code == "RAIN_DELTA_MM" else "last",
            product_compatibility="RAIN_GAUGE",
        )
        db_session.add(definition)
        db_session.flush()
    channel = db_session.scalar(
        select(DeviceChannel).where(DeviceChannel.device_id == device.id, DeviceChannel.code == code)
    )
    if channel is None:
        channel = DeviceChannel(
            device_id=device.id,
            name=code,
            code=code,
            channel_key=f"{code.lower()}_{device.id}",
        )
        db_session.add(channel)
        db_session.flush()
    event = TelemetryEvent(
        company_id=device.company_id,
        storage_unit_id=device.storage_unit_id,
        device_id=device.id,
        boot_id=1,
        sequence=sequence,
        sample_counter=sequence,
        sampled_at=sampled_at,
        time_quality="VALID",
        protocol_version=1,
    )
    db_session.add(event)
    db_session.flush()
    db_session.add(
        MetricReading(
            telemetry_event_id=event.id,
            company_id=device.company_id,
            storage_unit_id=device.storage_unit_id,
            device_id=device.id,
            sensor_channel_id=channel.id,
            metric_definition_id=definition.id,
            metric_code=code,
            raw_value=value,
            display_value=value,
            canonical_unit="unit",
            sampled_at=sampled_at,
        )
    )


def test_rain_today_uses_site_timezone_and_sums_only_local_day(db_session):
    site, _, _, gauge_a, _, _, _ = _map_context(db_session)
    now = datetime(2026, 9, 24, 6, 0, tzinfo=timezone.utc)  # 02:00 in America/La_Paz
    _add_metric(db_session, gauge_a, "RAIN_DELTA_MM", 9.0, datetime(2026, 9, 24, 3, 59, tzinfo=timezone.utc), 1)
    _add_metric(db_session, gauge_a, "RAIN_DELTA_MM", 1.2, datetime(2026, 9, 24, 4, 15, tzinfo=timezone.utc), 2)
    _add_metric(db_session, gauge_a, "RAIN_DELTA_MM", 2.3, datetime(2026, 9, 24, 5, 30, tzinfo=timezone.utc), 3)
    db_session.commit()
    admin = db_session.scalar(select(User).where(User.email == "admin@agroescudo.local"))
    snapshot = build_pluviometry_map_snapshot(db_session, admin, site.id, now=now)
    result = next(device for device in snapshot.devices if device.id == gauge_a.id)
    assert result.rain_today_mm == pytest.approx(3.5)


def test_offline_gauge_stays_on_map_without_becoming_critical(db_session):
    site, _, _, gauge_a, _, _, _ = _map_context(db_session)
    now = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)
    gauge_a.expected_reading_interval_minutes = 1
    gauge_a.last_seen_at = now - timedelta(minutes=7)
    original_position = (gauge_a.latitude, gauge_a.longitude)
    db_session.commit()

    admin = db_session.scalar(select(User).where(User.email == "admin@agroescudo.local"))
    snapshot = build_pluviometry_map_snapshot(db_session, admin, site.id, now=now)
    result = next(device for device in snapshot.devices if device.id == gauge_a.id)

    assert result.status == "offline"
    assert (result.latitude, result.longitude) == original_position


def test_latest_popup_metrics_return_most_recent_reading(db_session):
    site, _, _, gauge_a, _, _, _ = _map_context(db_session)
    now = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)
    _add_metric(db_session, gauge_a, "AMBIENT_TEMPERATURE_C", 20.0, now - timedelta(minutes=20), 10)
    _add_metric(db_session, gauge_a, "AMBIENT_TEMPERATURE_C", 23.4, now - timedelta(minutes=5), 11)
    _add_metric(db_session, gauge_a, "AMBIENT_RELATIVE_HUMIDITY_PCT", 71.0, now - timedelta(minutes=4), 12)
    db_session.commit()
    admin = db_session.scalar(select(User).where(User.email == "admin@agroescudo.local"))
    result = next(
        device for device in build_pluviometry_map_snapshot(db_session, admin, site.id, now=now).devices
        if device.id == gauge_a.id
    )
    assert result.latest.temperature_c == pytest.approx(23.4)
    assert result.latest.humidity_pct == pytest.approx(71.0)
    assert result.latest.wind_speed_kmh is None


def test_device_without_coordinates_is_returned_without_error(client, db_session):
    site, _, _, gauge_a, _, _, _ = _map_context(db_session)
    gauge_a.latitude = None
    gauge_a.longitude = None
    gauge_a.is_active = False
    db_session.commit()
    response = client.get(f"/api/pluviometry/sites/{site.id}/map", headers=_login(client))
    assert response.status_code == 200
    device = next(item for item in response.json()["devices"] if item["id"] == gauge_a.id)
    assert device["latitude"] is None
    assert device["longitude"] is None
    assert device["status"] == "offline"


@pytest.mark.parametrize("geometry_type", ["Polygon", "MultiPolygon"])
def test_polygon_and_multipolygon_are_preserved(client, db_session, geometry_type):
    site, parcel_a, _, _, _, _, _ = _map_context(db_session)
    parcel_a.boundary_geojson = (
            {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0, 1], [0, 0]]]}
        if geometry_type == "Polygon"
            else {"type": "MultiPolygon", "coordinates": [[[[0, 0], [1, 0], [0, 1], [0, 0]]]]}
    )
    db_session.commit()
    payload = client.get(f"/api/pluviometry/sites/{site.id}/map", headers=_login(client)).json()
    geometry = next(item for item in payload["parcels"] if item["id"] == parcel_a.id)["boundary_geojson"]
    assert geometry["type"] == geometry_type
