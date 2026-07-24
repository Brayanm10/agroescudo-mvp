from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import hash_secret
from app.models import Device, SensorCalibration, SensorMetricValue, Site, StorageUnit


def auth_headers(client, email="admin@agroescudo.local", password="admin123"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_field_device(db_session):
    site = db_session.scalar(select(Site))
    storage = StorageUnit(
        company_id=site.company_id,
        site_id=site.id,
        name="Parcela Norte",
        unit_type="parcela",
        operation_type="field",
        surface_hectares=12.5,
        crop_type="maiz",
    )
    db_session.add(storage)
    db_session.flush()
    source_unit = db_session.scalar(select(StorageUnit).where(StorageUnit.name == "Silo Demo 1"))
    storage.assigned_technician_id = source_unit.assigned_technician_id
    storage.assigned_client_id = source_unit.assigned_client_id
    device = Device(
        company_id=site.company_id,
        site_id=site.id,
        storage_unit_id=storage.id,
        external_id="FIELD-001",
        name="CampoSensor 001",
        device_type="field_sensor",
        token_hash=hash_secret("field-token"),
        is_active=True,
    )
    db_session.add(device)
    db_session.commit()
    return storage, device


def calibration_payload(**changes):
    payload = {
        "variable_type": "soil_moisture_percent",
        "method": "LINEAR_TWO_POINT",
        "raw_value": 2000,
        "dry_raw": 3000,
        "wet_raw": 1000,
        "dry_percent": 0,
        "wet_percent": 100,
        "parameters": {"adc_min": 0, "adc_max": 4095},
        "reference_instrument": "Protocolo gravimetrico de referencia",
        "notes": "Calibracion inicial de parcela.",
    }
    payload.update(changes)
    return payload


def test_admin_registers_compatible_products_and_rejects_incompatible_unit(client, db_session):
    silo = db_session.scalar(select(StorageUnit).where(StorageUnit.name == "Silo Demo 1"))
    headers = auth_headers(client)
    incompatible = client.post(
        "/api/admin/devices",
        headers=headers,
        json={
            "storage_unit_id": silo.id,
            "external_id": "FIELD-BAD",
            "name": "Campo en silo",
            "device_type": "field_sensor",
            "capabilities": ["soil_moisture_percent"],
        },
    )
    assert incompatible.status_code == 422

    field, _ = create_field_device(db_session)
    created = client.post(
        "/api/admin/devices",
        headers=headers,
        json={
            "storage_unit_id": field.id,
            "external_id": "FIELD-002",
            "name": "CampoSensor 002",
            "device_type": "field_sensor",
            "capabilities": ["soil_moisture_percent", "ambient_temperature"],
        },
    )
    assert created.status_code == 201
    assert created.json()["device_type"] == "field_sensor"
    assert {item["device_type"] for item in client.get("/api/devices", headers=headers).json()} >= {
        "esp32_iot_node",
        "field_sensor",
    }


def test_two_point_negative_slope_preview_and_raw_preservation(client, db_session):
    _, device = create_field_device(db_session)
    headers = auth_headers(client)
    preview = client.post(
        f"/api/devices/{device.id}/calibrations/preview",
        headers=headers,
        json=calibration_payload(),
    )
    assert preview.status_code == 200
    assert preview.json()["slope"] == -0.05
    assert preview.json()["calibrated_value"] == 50

    created = client.post(
        f"/api/devices/{device.id}/calibrations",
        headers=headers,
        json=calibration_payload(),
    )
    assert created.status_code == 201
    assert created.json()["calibration_version"] == 1

    reading = client.post(
        "/api/readings",
        json={
            "device_id": "FIELD-001",
            "device_token": "field-token",
            "ambient_temperature": 24,
            "ambient_humidity": 52,
            "battery_voltage": 3.9,
            "soil_moisture_raw": 2000,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert reading.status_code == 201
    assert reading.json()["reading"]["soil_moisture_percent"] == 50
    metric = db_session.scalar(
        select(SensorMetricValue).where(
            SensorMetricValue.device_id == device.id,
            SensorMetricValue.variable_type == "soil_moisture_percent",
        )
    )
    assert metric.raw_value == 2000
    assert metric.value == 50
    assert metric.calibration_version_applied == 1


def test_calibration_history_is_versioned_and_client_is_read_only(client, db_session):
    _, device = create_field_device(db_session)
    admin_headers = auth_headers(client)
    first = client.post(
        f"/api/devices/{device.id}/calibrations",
        headers=admin_headers,
        json=calibration_payload(),
    )
    second = client.post(
        f"/api/devices/{device.id}/calibrations",
        headers=admin_headers,
        json=calibration_payload(dry_raw=3200, wet_raw=1200),
    )
    assert first.status_code == second.status_code == 201
    assert second.json()["calibration_version"] == 2
    rows = db_session.scalars(
        select(SensorCalibration)
        .where(SensorCalibration.device_id == device.id)
        .order_by(SensorCalibration.calibration_version)
    ).all()
    assert [item.is_active for item in rows] == [False, True]

    client_headers = auth_headers(client, "cliente@silo-demo.local", "cliente123")
    visible = client.get(f"/api/devices/{device.id}/calibrations", headers=client_headers)
    assert visible.status_code == 200
    assert visible.json()[0]["slope"] is None
    forbidden = client.post(
        f"/api/devices/{device.id}/calibrations",
        headers=client_headers,
        json=calibration_payload(),
    )
    assert forbidden.status_code == 403


def test_technician_calibrates_only_assigned_device(client, db_session):
    _, assigned = create_field_device(db_session)
    technician_headers = auth_headers(client, "tecnico@agroescudo.local", "tecnico123")
    allowed = client.post(
        f"/api/devices/{assigned.id}/calibrations",
        headers=technician_headers,
        json=calibration_payload(),
    )
    assert allowed.status_code == 201

    other_site = db_session.scalar(select(Site))
    unassigned_unit = StorageUnit(
        company_id=other_site.company_id,
        site_id=other_site.id,
        name="Parcela no asignada",
        unit_type="parcela",
        operation_type="field",
    )
    db_session.add(unassigned_unit)
    db_session.flush()
    other_device = Device(
        company_id=other_site.company_id,
        site_id=other_site.id,
        storage_unit_id=unassigned_unit.id,
        external_id="FIELD-PRIVATE",
        name="Campo privado",
        device_type="field_sensor",
        token_hash=hash_secret("private-token"),
    )
    db_session.add(other_device)
    db_session.commit()
    denied = client.post(
        f"/api/devices/{other_device.id}/calibrations",
        headers=technician_headers,
        json=calibration_payload(),
    )
    assert denied.status_code == 403


def test_equal_raw_points_are_rejected(client, db_session):
    _, device = create_field_device(db_session)
    response = client.post(
        f"/api/devices/{device.id}/calibrations/preview",
        headers=auth_headers(client),
        json=calibration_payload(dry_raw=1500, wet_raw=1500),
    )
    assert response.status_code == 422


def test_product_summary_respects_storage_type(client, db_session):
    field, _ = create_field_device(db_session)
    response = client.get(
        f"/api/storage-units/{field.id}/product-summary",
        headers=auth_headers(client, "cliente@silo-demo.local", "cliente123"),
    )
    assert response.status_code == 200
    assert response.json()["product_type"] == "field_sensor"
    assert response.json()["storage_unit"]["operation_type"] == "field"
