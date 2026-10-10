from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.domain.emc import apply_emc_offset, calculate_maize_emc_wb, dry_basis_to_wet_basis_pct
from app.models import Device, SensorReading, StorageUnit


def auth_headers(client, email="admin@agroescudo.local", password="admin123"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def add_reading(db_session, *, temperature=17.9, humidity=51.4, at=None):
    unit = db_session.scalar(select(StorageUnit))
    device = db_session.scalar(select(Device))
    row = SensorReading(
        company_id=unit.company_id,
        site_id=unit.site_id,
        storage_unit_id=unit.id,
        device_id=device.id,
        grain_temperature=18.6,
        ambient_temperature=temperature,
        ambient_humidity=humidity,
        battery_voltage=3.8,
        level_distance_cm=120,
        timestamp=at or datetime.now(timezone.utc),
    )
    db_session.add(row)
    db_session.commit()
    return unit, device, row


def test_modified_chung_pfost_maize_reference_value():
    assert calculate_maize_emc_wb(17.9, 51.4) == pytest.approx(11.85, abs=0.02)


def test_dry_basis_is_converted_to_wet_basis_percent():
    assert dry_basis_to_wet_basis_pct(0.12) == pytest.approx(10.7142857)


@pytest.mark.parametrize("temperature,humidity", [(20, 0), (20, 100), (-31, 50), (float("nan"), 50)])
def test_emc_rejects_invalid_inputs(temperature, humidity):
    with pytest.raises(ValueError):
        calculate_maize_emc_wb(temperature, humidity)


def test_emc_offset_is_applied_and_clamped():
    assert apply_emc_offset(12.0, 1.5) == 13.5
    assert apply_emc_offset(99.0, 5.0) == 100.0
    assert apply_emc_offset(1.0, -5.0) == 0.0


def test_emc_series_is_dynamic_and_does_not_persist_duplicate_telemetry(client, db_session):
    unit, device, _ = add_reading(db_session)
    before = db_session.scalar(select(func.count()).select_from(SensorReading))
    response = client.get(f"/api/devices/{device.id}/emc-readings", headers=auth_headers(client))
    after = db_session.scalar(select(func.count()).select_from(SensorReading))

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["metric_code"] == "GRAIN_MOISTURE_EMC_PCT"
    assert payload["summary"]["current"] == pytest.approx(11.85, abs=0.02)
    assert payload["points"][0]["emc_raw_wb"] == pytest.approx(11.85, abs=0.02)
    assert payload["points"][0]["quality_status"] == "DERIVED_UNCALIBRATED"
    assert before == after
    assert unit.emc_calibration_offset_pp is None


def test_admin_calibration_uses_raw_reading_at_reference_and_client_can_only_read(client, db_session):
    reference_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    unit, device, _ = add_reading(db_session, at=reference_at)
    admin = auth_headers(client)
    response = client.put(
        f"/api/admin/storage-units/{unit.id}/emc-configuration",
        headers=admin,
        json={
            "enabled": True,
            "crop": "MAIZE",
            "reference_moisture_wb": 13.0,
            "reference_timestamp": (reference_at + timedelta(seconds=5)).isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    configured = response.json()
    assert configured["emc_raw_at_reference_wb"] == pytest.approx(11.85, abs=0.02)
    assert configured["emc_calibration_offset_pp"] == pytest.approx(1.15, abs=0.02)

    client_headers = auth_headers(client, "cliente@silo-demo.local", "cliente123")
    forbidden = client.put(
        f"/api/admin/storage-units/{unit.id}/emc-configuration",
        headers=client_headers,
        json={"enabled": True, "crop": "MAIZE", "reference_moisture_wb": None, "reference_timestamp": None},
    )
    assert forbidden.status_code == 403
    visible = client.get(f"/api/devices/{device.id}/emc-readings", headers=client_headers)
    assert visible.status_code == 200
    assert visible.json()["summary"]["current"] == pytest.approx(13.0, abs=0.02)
    technician_headers = auth_headers(client, "tecnico@agroescudo.local", "tecnico123")
    assert client.put(
        f"/api/admin/storage-units/{unit.id}/emc-configuration",
        headers=technician_headers,
        json={"enabled": True, "crop": "MAIZE", "reference_moisture_wb": None, "reference_timestamp": None},
    ).status_code == 403

    cleared = client.put(
        f"/api/admin/storage-units/{unit.id}/emc-configuration",
        headers=admin,
        json={"enabled": True, "crop": "MAIZE", "reference_moisture_wb": None, "reference_timestamp": None},
    )
    assert cleared.status_code == 200
    assert cleared.json()["emc_calibration_offset_pp"] is None
    recalculated = client.get(f"/api/devices/{device.id}/emc-readings", headers=client_headers).json()
    assert recalculated["summary"]["current"] == pytest.approx(11.85, abs=0.02)


def test_missing_input_returns_pending_empty_series_without_changing_device(client, db_session):
    unit, device, _ = add_reading(db_session, humidity=None)
    original_seen = device.last_seen_at
    response = client.get(f"/api/devices/{device.id}/emc-readings", headers=auth_headers(client))
    assert response.status_code == 200
    assert response.json()["points"] == []
    assert response.json()["summary"]["current"] is None
    db_session.refresh(device)
    assert device.last_seen_at == original_seen
    assert unit.emc_enabled is True
    general = client.get(f"/api/devices/{device.id}/readings", headers=auth_headers(client))
    assert general.status_code == 200
    assert len(general.json()) == 1


def test_calibration_requires_complete_reference_pair(client, db_session):
    unit = db_session.scalar(select(StorageUnit))
    response = client.put(
        f"/api/admin/storage-units/{unit.id}/emc-configuration",
        headers=auth_headers(client),
        json={"enabled": True, "crop": "MAIZE", "reference_moisture_wb": 12.0, "reference_timestamp": None},
    )
    assert response.status_code == 422
