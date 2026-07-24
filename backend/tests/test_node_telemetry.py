from datetime import datetime, timezone

from sqlalchemy import select

from app.core.security import hash_secret
from app.models import Device, SensorReading, StorageUnit


def auth_headers(client, email="admin@agroescudo.local", password="admin123"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def payload(device_id="SILO-001", token="secret-token", **values):
    body = {
        "device_id": device_id,
        "device_token": token,
        "grain_temperature": 27.5,
        "ambient_temperature": 25.0,
        "ambient_humidity": 60.0,
        "battery_voltage": 3.9,
        "signal_quality": -68,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    body.update(values)
    return body


def add_second_device(db_session, *, device_type="silo_sensor"):
    unit = db_session.scalar(select(StorageUnit))
    device = Device(
        company_id=unit.company_id,
        site_id=unit.site_id,
        storage_unit_id=unit.id,
        external_id="NODE-B",
        name="Nodo B",
        device_type=device_type,
        token_hash=hash_secret("node-b-token"),
        is_active=True,
    )
    db_session.add(device)
    db_session.commit()
    return device


def test_device_readings_never_mix_nodes(client, db_session):
    first = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    second = add_second_device(db_session)
    assert client.post("/api/readings", json=payload()).status_code == 201
    assert client.post("/api/readings", json=payload("NODE-B", "node-b-token", grain_temperature=19)).status_code == 201

    headers = auth_headers(client)
    first_rows = client.get(f"/api/devices/{first.id}/readings", headers=headers).json()
    second_rows = client.get(f"/api/devices/{second.id}/readings", headers=headers).json()
    assert {row["device_id"] for row in first_rows} == {first.id}
    assert {row["device_id"] for row in second_rows} == {second.id}


def test_ultrasonic_level_uses_backend_calibration(client, db_session):
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    device.device_type = "silo_sensor"
    device.empty_distance_cm = 600
    device.full_distance_cm = 50
    db_session.commit()

    response = client.post("/api/readings", json=payload(level_distance_cm=325))
    assert response.status_code == 201
    assert response.json()["reading"]["level_distance_cm"] == 325
    assert response.json()["reading"]["level_percent"] == 50


def test_ultrasonic_level_clamps_and_pending_calibration(client, db_session):
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    device.device_type = "silo_sensor"
    db_session.commit()
    pending = client.post("/api/readings", json=payload(level_distance_cm=325))
    assert pending.status_code == 201
    assert pending.json()["reading"]["level_percent"] is None

    device.empty_distance_cm = 600
    device.full_distance_cm = 50
    db_session.commit()
    full = client.post("/api/readings", json=payload(level_distance_cm=25))
    empty = client.post("/api/readings", json=payload(level_distance_cm=700))
    assert full.json()["reading"]["level_percent"] == 100
    assert empty.json()["reading"]["level_percent"] == 0


def test_invalid_ultrasonic_values_and_calibration_are_rejected(client, db_session):
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    negative = client.post("/api/readings", json=payload(level_distance_cm=-1))
    assert negative.status_code == 422
    invalid_calibration = client.patch(
        f"/api/admin/devices/{device.id}/calibration",
        json={"empty_distance_cm": 50, "full_distance_cm": 600},
        headers=auth_headers(client),
    )
    assert invalid_calibration.status_code == 422


def test_client_does_not_receive_signal_or_diagnostics(client):
    client.post("/api/readings", json=payload())
    client_headers = auth_headers(client, "cliente@silo-demo.local", "cliente123")
    device = client.get("/api/devices", headers=client_headers).json()[0]
    rows = client.get(f"/api/devices/{device['id']}/readings", headers=client_headers).json()
    summary = client.get(f"/api/devices/{device['id']}/summary", headers=client_headers).json()
    assert rows[0]["signal_quality"] is None
    assert rows[0]["sensor_status"] is None
    assert summary["diagnostics"] is None
    assert summary["calibration"] is None


def test_technician_receives_authorized_diagnostics(client):
    client.post("/api/readings", json=payload(sensor_status=7))
    headers = auth_headers(client, "tecnico@agroescudo.local", "tecnico123")
    device = client.get("/api/devices", headers=headers).json()[0]
    summary = client.get(f"/api/devices/{device['id']}/summary", headers=headers).json()
    assert summary["diagnostics"]["signal_quality"] == -68
    assert summary["diagnostics"]["sensor_status"] == 7
    assert summary["calibration"] is None


def test_field_sensor_keeps_soil_and_ambient_humidity_separate(client, db_session):
    device = add_second_device(db_session, device_type="field_sensor")
    body = payload(
        "NODE-B",
        "node-b-token",
        grain_temperature=None,
        ambient_humidity=58,
        soil_moisture_percent=31,
        soil_temperature_c=20,
    )
    response = client.post("/api/readings", json=body)
    assert response.status_code == 201
    reading = db_session.scalar(select(SensorReading).where(SensorReading.device_id == device.id))
    assert reading.ambient_humidity == 58
    assert reading.soil_moisture_percent == 31


def test_weekly_report_groups_devices(client, db_session):
    second = add_second_device(db_session)
    client.post("/api/readings", json=payload())
    client.post("/api/readings", json=payload("NODE-B", "node-b-token", grain_temperature=20))
    unit = db_session.scalar(select(StorageUnit))
    report = client.get(f"/api/reports/weekly?storage_unit_id={unit.id}", headers=auth_headers(client))
    assert report.status_code == 200
    assert {node["device_external_id"] for node in report.json()["nodes"]} == {"SILO-001", "NODE-B"}

    node_report = client.get(
        f"/api/reports/weekly?storage_unit_id={unit.id}&device_id={second.id}",
        headers=auth_headers(client),
    )
    assert node_report.status_code == 200
    assert node_report.json()["device_external_id"] == "NODE-B"
    assert node_report.json()["reading_count"] == 1
    assert [node["device_external_id"] for node in node_report.json()["nodes"]] == ["NODE-B"]


def test_low_level_alert_records_metric_value_and_threshold(client, db_session):
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    device.device_type = "silo_sensor"
    device.empty_distance_cm = 600
    device.full_distance_cm = 50
    db_session.commit()
    thresholds = client.put(
        f"/api/devices/{device.id}/thresholds",
        headers=auth_headers(client),
        json={
            "max_grain_temperature": 90,
            "max_ambient_humidity": 99,
            "min_battery_voltage": 1,
            "critical_temperature": 95,
            "critical_humidity": 100,
            "min_level_percent": 20,
            "max_level_percent": 95,
        },
    )
    assert thresholds.status_code == 200

    response = client.post("/api/readings", json=payload(level_distance_cm=550))
    assert response.status_code == 201
    alert = next(item for item in response.json()["alerts"] if item["alert_type"] == "level_low")
    assert alert["metric"] == "level_percent"
    assert alert["observed_value"] == 9.09
    assert alert["threshold_value"] == 20
