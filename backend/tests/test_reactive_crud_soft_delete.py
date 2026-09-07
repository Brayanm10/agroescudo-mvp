from sqlalchemy import select

from app.models import Device, IotDevice, IotGateway, SensorReading, SentinelDevice, StorageUnit, User


def auth_headers(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@agroescudo.local", "password": "admin123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_device_soft_delete_preserves_history_and_hides_inventory(client, db_session):
    headers = auth_headers(client)
    ingest = client.post(
        "/api/readings",
        json={
            "device_id": "SILO-001",
            "device_token": "secret-token",
            "grain_temperature": 27.2,
            "timestamp": "2026-09-06T12:00:00Z",
        },
    )
    assert ingest.status_code == 201
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    reading_count = len(list(db_session.scalars(select(SensorReading).where(SensorReading.device_id == device.id))))

    response = client.delete(f"/api/admin/devices/{device.id}", headers=headers)

    assert response.status_code == 200
    db_session.refresh(device)
    assert device.deleted_at is not None
    assert device.is_active is False
    assert len(list(db_session.scalars(select(SensorReading).where(SensorReading.device_id == device.id)))) == reading_count
    assert all(item["id"] != device.id for item in client.get("/api/admin/devices", headers=headers).json())
    link = db_session.scalar(select(IotDevice).where(IotDevice.device_id == device.id))
    assert link is not None and link.is_active is False


def test_storage_unit_delete_requires_sensor_retirement(client, db_session):
    headers = auth_headers(client)
    unit = db_session.scalar(select(StorageUnit).where(StorageUnit.name == "Silo Demo 1"))

    blocked = client.delete(f"/api/admin/storage-units/{unit.id}", headers=headers)
    assert blocked.status_code == 409
    assert "sensores vinculados" in blocked.json()["detail"]

    device = db_session.scalar(select(Device).where(Device.storage_unit_id == unit.id))
    assert client.delete(f"/api/admin/devices/{device.id}", headers=headers).status_code == 200
    removed = client.delete(f"/api/admin/storage-units/{unit.id}", headers=headers)
    assert removed.status_code == 200
    db_session.refresh(unit)
    assert unit.deleted_at is not None


def test_admin_cannot_delete_self_or_last_operational_admin(client, db_session):
    headers = auth_headers(client)
    admin = db_session.scalar(select(User).where(User.email == "admin@agroescudo.local"))

    response = client.delete(f"/api/admin/users/{admin.id}", headers=headers)

    assert response.status_code == 409
    assert "propia cuenta" in response.json()["detail"]


def test_gateway_create_returns_secret_once_and_delete_unassigns_nodes(client, db_session):
    headers = auth_headers(client)
    created = client.post(
        "/api/admin/gateways",
        headers=headers,
        json={"gateway_id": "GW-REACTIVE-001", "name": "Gateway Piloto"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["secret"]
    assert body["gateway_id"] == "GW-REACTIVE-001"

    removed = client.delete(f"/api/admin/gateways/{body['id']}", headers=headers)
    assert removed.status_code == 200
    gateway = db_session.get(IotGateway, body["id"])
    assert gateway.deleted_at is not None
    assert gateway.is_active is False


def test_pilot_patch_updates_without_recreating_infrastructure(client, db_session):
    headers = auth_headers(client)
    unit = db_session.scalar(select(StorageUnit).where(StorageUnit.name == "Silo Demo 1"))

    response = client.patch(
        f"/api/pilots/{unit.id}",
        headers=headers,
        json={"storage_unit_name": "Silo Norte Principal", "capacity_tons": 540},
    )

    assert response.status_code == 200
    assert response.json()["storage_unit_name"] == "Silo Norte Principal"
    db_session.refresh(unit)
    assert unit.name == "Silo Norte Principal"
    assert unit.capacity_tons == 540


def test_gateway_and_sentinel_identity_updates_are_persisted(client, db_session):
    headers = auth_headers(client)
    gateway_response = client.post(
        "/api/admin/gateways",
        headers=headers,
        json={"gateway_id": "GW-EDIT-001", "name": "Gateway Inicial"},
    )
    assert gateway_response.status_code == 201
    gateway_id = gateway_response.json()["id"]

    gateway_update = client.patch(
        f"/api/admin/gateways/{gateway_id}",
        headers=headers,
        json={"name": "Gateway Principal", "is_active": False},
    )
    assert gateway_update.status_code == 200
    assert gateway_update.json()["name"] == "Gateway Principal"
    assert gateway_update.json()["is_active"] is False

    sentinel_response = client.post(
        "/api/admin/sentinel/devices",
        headers=headers,
        json={"device_uid": "sentinel-edit-001", "name": "Sentinel Inicial"},
    )
    assert sentinel_response.status_code == 201
    sentinel_id = sentinel_response.json()["id"]

    sentinel_update = client.patch(
        f"/api/admin/sentinel/devices/{sentinel_id}",
        headers=headers,
        json={"device_uid": "sentinel-edit-002", "name": "Sentinel Principal"},
    )
    assert sentinel_update.status_code == 200
    assert sentinel_update.json()["device_uid"] == "sentinel-edit-002"
    assert sentinel_update.json()["name"] == "Sentinel Principal"
    sentinel = db_session.get(SentinelDevice, sentinel_id)
    assert sentinel is not None and sentinel.device_uid == "sentinel-edit-002"
