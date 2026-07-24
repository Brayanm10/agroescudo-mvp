from sqlalchemy import select

from app.models import Device, FirmwareUpdateRecord, IotDevice, OperationalLog


def _headers(client, email: str = "admin@agroescudo.local", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_firmware_release_recommendation_and_outdated_status(client, db_session):
    response = client.post(
        "/api/firmware/releases",
        headers=_headers(client),
        json={
            "device_type": "silo_sensor",
            "version": "2.0.0",
            "status": "RELEASED",
            "release_notes": "Version validada para piloto.",
            "checksum": "a" * 64,
            "is_recommended": True,
            "is_mandatory": False,
        },
    )
    assert response.status_code == 201, response.text
    release = response.json()
    assert release["device_type"] == "silo_sensor"
    assert release["released_at"] is not None

    status_response = client.get("/api/firmware/devices/status", headers=_headers(client))
    assert status_response.status_code == 200, status_response.text
    node = next(item for item in status_response.json() if item["external_id"] == "SILO-001")
    assert node["current_version"] == "1.0.0"
    assert node["recommended_version"] == "2.0.0"
    assert node["is_outdated"] is True
    assert node["update_status"] == "outdated"


def test_technician_records_manual_firmware_update_with_audit_log(client, db_session):
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    release = client.post(
        "/api/firmware/releases",
        headers=_headers(client),
        json={
            "device_type": "silo_sensor",
            "version": "2.1.0",
            "status": "RELEASED",
            "release_notes": "Version de campo.",
            "checksum": "b" * 64,
            "is_recommended": True,
        },
    ).json()

    response = client.post(
        f"/api/devices/{device.id}/firmware-update-record",
        headers=_headers(client, "tecnico@agroescudo.local", "tecnico123"),
        json={
            "firmware_release_id": release["id"],
            "new_version": "2.1.0",
            "result": "SUCCESS",
            "notes": "Actualizacion manual verificada en sitio.",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["previous_version"] == "1.0.0"
    assert response.json()["new_version"] == "2.1.0"
    iot_device = db_session.scalar(select(IotDevice).where(IotDevice.device_id == device.id))
    assert iot_device.firmware_version == "2.1.0"
    assert db_session.scalar(
        select(OperationalLog).where(
            OperationalLog.device_id == device.id,
            OperationalLog.action_taken == "Actualizacion de firmware registrada.",
        )
    ) is not None
    assert db_session.scalar(select(FirmwareUpdateRecord).where(FirmwareUpdateRecord.device_id == device.id)) is not None


def test_client_cannot_manage_firmware_and_invalid_checksum_is_rejected(client):
    client_headers = _headers(client, "cliente@silo-demo.local", "cliente123")
    assert client.get("/api/firmware/releases", headers=client_headers).status_code == 403
    assert client.get("/api/firmware/devices/status", headers=client_headers).status_code == 403

    invalid = client.post(
        "/api/firmware/releases",
        headers=_headers(client),
        json={
            "device_type": "silo_sensor",
            "version": "bad-checksum",
            "status": "DRAFT",
            "checksum": "not-a-sha256",
        },
    )
    assert invalid.status_code == 422


def test_released_firmware_cannot_return_to_draft(client):
    created = client.post(
        "/api/firmware/releases",
        headers=_headers(client),
        json={
            "device_type": "field_sensor",
            "version": "1.0.0",
            "status": "RELEASED",
            "checksum": "c" * 64,
        },
    ).json()
    response = client.patch(
        f"/api/firmware/releases/{created['id']}",
        headers=_headers(client),
        json={"status": "DRAFT"},
    )
    assert response.status_code == 409
    assert "Transicion no permitida" in response.json()["detail"]
