from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import Company, Device, SensorReading, Site, StorageUnit


def auth_headers(client, email="admin@agroescudo.local", password="admin123"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_monitoring_summary_uses_configured_cadence(client, db_session):
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    now = datetime.now(timezone.utc)
    device.expected_reading_interval_minutes = 15
    device.installed_at = now - timedelta(minutes=5)
    device.last_seen_at = now
    db_session.add(
        SensorReading(
            company_id=device.company_id,
            site_id=device.site_id,
            storage_unit_id=device.storage_unit_id,
            device_id=device.id,
            grain_temperature=26.0,
            ambient_temperature=25.0,
            ambient_humidity=61.0,
            battery_voltage=3.9,
            timestamp=now,
        )
    )
    db_session.commit()

    response = client.get("/api/monitoring/summary", headers=auth_headers(client))

    assert response.status_code == 200
    body = response.json()
    assert body["calculation_status"] == "available"
    assert body["coverage_today_pct"] == 100.0
    assert body["current_streak_days"] == 1
    assert body["online_devices"] == 1
    assert body["recent_activity"][0]["kind"] == "reading"
    assert any(item["key"] == "first_sensor" for item in body["milestones"])


def test_monitoring_summary_does_not_invent_coverage_without_cadence(client):
    response = client.get("/api/monitoring/summary", headers=auth_headers(client))

    assert response.status_code == 200
    body = response.json()
    assert body["calculation_status"] == "not_calculable"
    assert body["coverage_today_pct"] is None
    assert body["current_streak_days"] == 0


def test_client_monitoring_summary_excludes_unassigned_units(client, db_session):
    company = db_session.scalar(select(Company))
    site = db_session.scalar(select(Site).where(Site.company_id == company.id))
    hidden_unit = StorageUnit(
        company_id=company.id,
        site_id=site.id,
        name="Unidad no asignada",
        unit_type="silo",
    )
    db_session.add(hidden_unit)
    db_session.flush()
    hidden_device = Device(
        company_id=company.id,
        site_id=site.id,
        storage_unit_id=hidden_unit.id,
        external_id="HIDDEN-001",
        name="Nodo no asignado",
        token_hash="hash",
        expected_reading_interval_minutes=15,
    )
    db_session.add(hidden_device)
    db_session.commit()

    response = client.get(
        "/api/monitoring/summary",
        headers=auth_headers(client, "cliente@silo-demo.local", "cliente123"),
    )

    assert response.status_code == 200
    assert response.json()["active_devices"] == 1
