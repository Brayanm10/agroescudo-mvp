from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import (
    Alert,
    Company,
    Device,
    MaintenanceRecord,
    SensorReading,
    Site,
    StorageUnit,
    StoredFile,
    User,
)


def auth_headers(client, email="admin@agroescudo.local", password="admin123"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_maintenance_assignment_completion_overdue_and_immutability(client, db_session):
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    technician = db_session.scalar(select(User).where(User.role == "technician"))
    admin = auth_headers(client)
    created = client.post(
        "/api/maintenance",
        headers=admin,
        json={
            "device_id": device.id,
            "maintenance_type": "SENSOR_REPLACEMENT",
            "priority": "HIGH",
            "technician_id": technician.id,
            "scheduled_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        },
    )
    assert created.status_code == 201
    maintenance_id = created.json()["id"]
    assert created.json()["effective_status"] == "OVERDUE"

    client_headers = auth_headers(client, "cliente@silo-demo.local", "cliente123")
    assert client.post("/api/maintenance", headers=client_headers, json={}).status_code == 403

    technician_headers = auth_headers(client, "tecnico@agroescudo.local", "tecnico123")
    visible = client.get("/api/maintenance", headers=technician_headers)
    assert visible.status_code == 200
    assert {item["id"] for item in visible.json()} == {maintenance_id}
    assert client.post(
        f"/api/maintenance/{maintenance_id}/start",
        headers=technician_headers,
        json={"note": "Inicio de inspeccion y reemplazo."},
    ).status_code == 200
    completed = client.post(
        f"/api/maintenance/{maintenance_id}/complete",
        headers=technician_headers,
        json={
            "observations": "Sensor retirado con desgaste visible.",
            "diagnosis": "Falla intermitente confirmada.",
            "action_taken": "Se reemplazo el sensor y se verifico cableado.",
            "device_status_after": "calibration_pending",
            "parts_replaced": ["Sensor de temperatura"],
            "sensor_replaced": True,
            "calibration_required": True,
            "next_maintenance_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"
    assert db_session.get(Device, device.id).operational_status == "calibration_pending"
    calibration_task = db_session.scalar(
        select(MaintenanceRecord).where(
            MaintenanceRecord.parent_maintenance_id == maintenance_id,
            MaintenanceRecord.maintenance_type == "CALIBRATION",
        )
    )
    assert calibration_task is not None
    immutable = client.patch(
        f"/api/maintenance/{maintenance_id}",
        headers=admin,
        json={"priority": "LOW"},
    )
    assert immutable.status_code == 409


def test_installation_requires_first_reading_and_critical_validation(client, db_session):
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    technician = db_session.scalar(select(User).where(User.role == "technician"))
    admin = auth_headers(client)
    created = client.post(
        "/api/installations",
        headers=admin,
        json={"device_id": device.id, "technician_id": technician.id, "responses": {}},
    )
    assert created.status_code == 201
    installation_id = created.json()["id"]
    technician_headers = auth_headers(client, "tecnico@agroescudo.local", "tecnico123")
    rejected = client.post(
        f"/api/installations/{installation_id}/validate",
        headers=technician_headers,
        json={"final_status": "PASSED"},
    )
    assert rejected.status_code == 422
    assert "primera lectura" in str(rejected.json()).lower()

    reading = SensorReading(
        company_id=device.company_id,
        site_id=device.site_id,
        storage_unit_id=device.storage_unit_id,
        device_id=device.id,
        grain_temperature=24.5,
        ambient_temperature=22,
        ambient_humidity=55,
        battery_voltage=3.9,
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(reading)
    db_session.flush()
    test_alert = Alert(
        company_id=device.company_id,
        site_id=device.site_id,
        storage_unit_id=device.storage_unit_id,
        device_id=device.id,
        reading_id=reading.id,
        alert_type="installation_test",
        severity="technical",
        title="Alerta de prueba",
        message="Validacion controlada.",
        is_active=False,
    )
    db_session.add(test_alert)
    db_session.commit()
    responses = {
        "hardware": {
            "enclosure_ok": True,
            "mounting_ok": True,
            "antenna_ok": True,
            "battery_ok": True,
            "sensor_ok": True,
            "wiring_ok": True,
            "sealed_ok": True,
            "qr_applied": True,
        },
        "communication": {
            "gateway_required": True,
            "first_transmission": True,
            "time_synced": True,
            "connectivity_ok": True,
        },
        "validation": {
            "reading_compared": True,
            "thresholds_validated": True,
            "test_alert_passed": True,
            "client_access_validated": True,
            "technician_access_validated": True,
            "test_report_generated": True,
        },
    }
    updated = client.patch(
        f"/api/installations/{installation_id}",
        headers=technician_headers,
        json={
            "responses": responses,
            "first_reading_id": reading.id,
            "test_alert_id": test_alert.id,
            "notes": "Instalacion verificada en sitio.",
        },
    )
    assert updated.status_code == 200
    passed = client.post(
        f"/api/installations/{installation_id}/validate",
        headers=technician_headers,
        json={"final_status": "PASSED"},
    )
    assert passed.status_code == 200
    assert passed.json()["status"] == "PASSED"


def test_device_qr_is_random_requires_auth_for_data_and_can_be_revoked(client, db_session):
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    admin = auth_headers(client)
    generated = client.post(f"/api/devices/{device.id}/qr", headers=admin)
    assert generated.status_code == 200
    token = generated.json()["public_token"]
    assert len(token) >= 32
    assert token != device.external_id

    public_scan = client.get(f"/api/devices/scan/{token}")
    assert public_scan.status_code == 200
    assert public_scan.json()["authenticated"] is False
    assert public_scan.json()["device_id"] is None
    assert public_scan.json()["storage_unit_id"] is None

    technician = auth_headers(client, "tecnico@agroescudo.local", "tecnico123")
    technical_scan = client.get(f"/api/devices/scan/{token}", headers=technician)
    assert technical_scan.status_code == 200
    assert "maintenance" in technical_scan.json()["allowed_actions"]

    assert client.post(f"/api/devices/{device.id}/qr/revoke", headers=admin).status_code == 204
    assert client.get(f"/api/devices/scan/{token}").status_code == 410


def test_evidence_validates_mime_scope_and_soft_delete(client, db_session):
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    technician = db_session.scalar(select(User).where(User.role == "technician"))
    admin = auth_headers(client)
    maintenance = client.post(
        "/api/maintenance",
        headers=admin,
        json={
            "device_id": device.id,
            "maintenance_type": "INSPECTION",
            "technician_id": technician.id,
        },
    ).json()
    technician_headers = auth_headers(client, "tecnico@agroescudo.local", "tecnico123")
    invalid = client.post(
        "/api/evidence",
        headers=technician_headers,
        data={
            "storage_unit_id": device.storage_unit_id,
            "entity_type": "maintenance",
            "entity_id": maintenance["id"],
            "file_type": "PHOTO",
        },
        files={"file": ("malware.exe", b"MZ\x00\x00binary", "application/octet-stream")},
    )
    assert invalid.status_code == 415

    uploaded = client.post(
        "/api/evidence",
        headers=technician_headers,
        data={
            "storage_unit_id": device.storage_unit_id,
            "entity_type": "maintenance",
            "entity_id": maintenance["id"],
            "file_type": "PHOTO",
            "description": "Vista de la caja despues de limpieza.",
        },
        files={"file": ("evidencia.png", b"\x89PNG\r\n\x1a\nvalid", "image/png")},
    )
    assert uploaded.status_code == 201
    evidence_id = uploaded.json()["id"]
    assert uploaded.json()["checksum_sha256"]
    assert client.get(f"/api/evidence/{evidence_id}/download", headers=technician_headers).status_code == 200

    other_company = Company(name="Otra Empresa")
    db_session.add(other_company)
    db_session.flush()
    other_site = Site(company_id=other_company.id, name="Sitio Ajeno")
    db_session.add(other_site)
    db_session.flush()
    other_unit = StorageUnit(
        company_id=other_company.id,
        site_id=other_site.id,
        name="Silo Ajeno",
        unit_type="silo",
    )
    db_session.add(other_unit)
    db_session.flush()
    foreign_file = StoredFile(
        company_id=other_company.id,
        storage_unit_id=other_unit.id,
        uploaded_by_id=None,
        entity_type="site",
        entity_id=other_site.id,
        file_type="DOCUMENT",
        storage_provider="local",
        object_key="foreign/document.pdf",
        original_filename="document.pdf",
        content_type="application/pdf",
        size_bytes=10,
    )
    db_session.add(foreign_file)
    db_session.commit()
    assert client.get(f"/api/evidence/{foreign_file.id}", headers=technician_headers).status_code == 403

    assert client.delete(f"/api/evidence/{evidence_id}", headers=technician_headers).status_code == 204
    assert db_session.get(StoredFile, evidence_id).deleted_at is not None
    assert client.get(f"/api/evidence/{evidence_id}", headers=technician_headers).status_code == 404
