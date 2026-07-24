from datetime import timedelta

from sqlalchemy import select

from app.models import Company, Device, IotGateway, SensorReading, Site, StorageUnit, User, utc_now


def _headers(client, email: str = "admin@agroescudo.local", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_gateway_status_and_scope_are_real(client, db_session):
    gateway = db_session.scalar(select(IotGateway).where(IotGateway.gateway_id == "GW-CBBA-001"))
    gateway.company_id = 1
    gateway.last_seen_at = utc_now() - timedelta(minutes=10)
    gateway.internet_status = "online"
    db_session.commit()

    technician = client.get(
        "/api/admin/gateways",
        headers=_headers(client, "tecnico@agroescudo.local", "tecnico123"),
    )
    assert technician.status_code == 200, technician.text
    assert technician.json()[0]["effective_status"] == "DELAYED"

    other_company = Company(name="Empresa Ajena")
    db_session.add(other_company)
    db_session.flush()
    other_site = Site(company_id=other_company.id, name="Sitio Ajeno")
    db_session.add(other_site)
    db_session.flush()
    other_unit = StorageUnit(
        company_id=other_company.id,
        site_id=other_site.id,
        name="Unidad Ajena",
        unit_type="silo",
    )
    db_session.add(other_unit)
    db_session.flush()
    db_session.add(
        IotGateway(
            company_id=other_company.id,
            site_id=other_site.id,
            storage_unit_id=other_unit.id,
            gateway_id="GW-OTHER-001",
            name="Gateway Ajeno",
            last_seen_at=utc_now(),
        )
    )
    db_session.commit()

    scoped = client.get(
        "/api/admin/gateways",
        headers=_headers(client, "tecnico@agroescudo.local", "tecnico123"),
    )
    assert [item["gateway_id"] for item in scoped.json()] == ["GW-CBBA-001"]


def test_technician_can_only_toggle_maintenance_on_assigned_gateway(client, db_session):
    gateway = db_session.scalar(select(IotGateway).where(IotGateway.gateway_id == "GW-CBBA-001"))
    headers = _headers(client, "tecnico@agroescudo.local", "tecnico123")

    maintenance = client.patch(
        f"/api/admin/gateways/{gateway.id}",
        headers=headers,
        json={"status": "MAINTENANCE"},
    )
    assert maintenance.status_code == 200, maintenance.text
    assert maintenance.json()["status"] == "MAINTENANCE"

    forbidden = client.patch(
        f"/api/admin/gateways/{gateway.id}",
        headers=headers,
        json={"name": "Nombre no autorizado"},
    )
    assert forbidden.status_code == 403


def test_system_health_is_protected_and_reports_real_counts(client, db_session):
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    device.expected_reading_interval_minutes = 15
    device.last_seen_at = utc_now()
    db_session.add(
        SensorReading(
            company_id=device.company_id,
            site_id=device.site_id,
            storage_unit_id=device.storage_unit_id,
            device_id=device.id,
            grain_temperature=25,
            ambient_temperature=22,
            ambient_humidity=60,
            battery_voltage=3.9,
            timestamp=utc_now(),
        )
    )
    db_session.commit()

    assert client.get("/api/admin/system-health").status_code == 401
    response = client.get("/api/admin/system-health", headers=_headers(client))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["backend"]["status"] == "ok"
    assert body["database"]["status"] == "ok"
    assert body["devices"]["total"] == 1
    assert body["data"]["readings_24h"] == 1

    client_response = client.get(
        "/api/admin/system-health",
        headers=_headers(client, "cliente@silo-demo.local", "cliente123"),
    )
    assert client_response.status_code == 403


def test_pilot_metrics_use_configured_cadence_and_never_invent_savings(client, db_session):
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    device.expected_reading_interval_minutes = 60
    now = utc_now()
    for hours in range(4):
        db_session.add(
            SensorReading(
                company_id=device.company_id,
                site_id=device.site_id,
                storage_unit_id=device.storage_unit_id,
                device_id=device.id,
                grain_temperature=24 + hours,
                ambient_temperature=22,
                ambient_humidity=60,
                battery_voltage=3.9,
                timestamp=now - timedelta(hours=hours),
            )
        )
    db_session.commit()

    response = client.get(
        "/api/admin/pilot-metrics",
        headers=_headers(client, "tecnico@agroescudo.local", "tecnico123"),
        params={
            "storage_unit_id": device.storage_unit_id,
            "date_from": (now - timedelta(hours=4)).isoformat(),
            "date_to": now.isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["data_availability"]["expected_readings"] == 5
    assert body["data_availability"]["received_readings"] == 4
    assert body["data_availability"]["coverage_percent"] == 80
    assert body["device_availability"]["method"] == "sampling_gap_estimate"
    assert "savings" not in response.text.lower()


def test_pilot_metrics_leave_coverage_unknown_without_cadence(client, db_session):
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    device.expected_reading_interval_minutes = None
    db_session.commit()

    response = client.get(
        "/api/admin/pilot-metrics",
        headers=_headers(client),
        params={"storage_unit_id": device.storage_unit_id},
    )
    assert response.status_code == 200, response.text
    availability = response.json()["data_availability"]
    assert availability["expected_readings"] is None
    assert availability["coverage_percent"] is None
    assert availability["cadence_configured"] is False
