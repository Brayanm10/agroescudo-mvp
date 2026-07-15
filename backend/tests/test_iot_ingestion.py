import hashlib
import hmac
from datetime import datetime, timezone

from sqlalchemy import select

from app.models import IotGateway, IotReading, SensorReading

GATEWAY_ID = "GW-CBBA-001"
GATEWAY_SECRET = "gateway-secret-001"


def batch_payload(**reading_overrides):
    reading = {
        "device_id": 1001,
        "boot_id": 843221,
        "sequence": 2048,
        "sample_counter": 2048,
        "timestamp_utc": 1782949800,
        "time_quality": 2,
        "grain_temp_c_x100": 2540,
        "air_temp_c_x100": 2380,
        "rh_x100": 6320,
        "battery_mv": 3910,
        "sensor_status": 15,
        "firmware_version": 256,
        "rssi_dbm": -72,
        "snr_db_x10": 85,
    }
    reading.update(reading_overrides)
    return {
        "gateway_id": GATEWAY_ID,
        "firmware_version": "1.0.0",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "batch_id": f"batch-{reading['sequence']}",
        "readings": [reading],
    }


def signed_headers(body: bytes, nonce: str = "nonce-1", secret: str = GATEWAY_SECRET):
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    body_hash = hashlib.sha256(body).hexdigest()
    message = f"{GATEWAY_ID}{timestamp}{nonce}{body_hash}".encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()
    return {
        "X-Agro-Gateway-ID": GATEWAY_ID,
        "X-Agro-Timestamp": timestamp,
        "X-Agro-Nonce": nonce,
        "X-Agro-Signature": signature,
    }


def post_batch(client, payload, nonce="nonce-1", secret=GATEWAY_SECRET):
    import json

    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return client.post(
        "/api/iot/v1/ingest/batch",
        content=body,
        headers={**signed_headers(body, nonce=nonce, secret=secret), "Content-Type": "application/json"},
    )


def test_iot_batch_accepts_signed_reading(client, db_session):
    response = post_batch(client, batch_payload())

    assert response.status_code == 200
    assert response.json()["results"][0]["status"] == "accepted"
    assert db_session.scalar(select(IotReading)) is not None
    sensor_reading = db_session.scalar(select(SensorReading))
    assert sensor_reading is not None
    assert sensor_reading.grain_temperature == 25.4
    assert sensor_reading.ambient_humidity == 63.2


def test_iot_batch_marks_duplicate_reading_without_second_sensor_reading(client, db_session):
    payload = batch_payload(sequence=2050)
    first = post_batch(client, payload, nonce="nonce-a")
    second_payload = batch_payload(sequence=2050)
    second_payload["batch_id"] = "batch-duplicate-check"
    second = post_batch(client, second_payload, nonce="nonce-b")

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["results"][0]["status"] == "duplicate"
    assert len(db_session.scalars(select(SensorReading)).all()) == 1


def test_iot_batch_rejects_invalid_signature(client):
    response = post_batch(client, batch_payload(sequence=2051), nonce="nonce-invalid", secret="wrong-secret")

    assert response.status_code == 401


def test_iot_batch_rejects_replayed_nonce(client):
    payload = batch_payload(sequence=2052)
    first = post_batch(client, payload, nonce="nonce-replay")
    second_payload = batch_payload(sequence=2053)
    second_payload["batch_id"] = "batch-replay-second"
    second = post_batch(client, second_payload, nonce="nonce-replay")

    assert first.status_code == 200
    assert second.status_code == 401


def test_iot_batch_reports_unknown_device(client):
    response = post_batch(client, batch_payload(device_id=9999, sequence=2054), nonce="nonce-unknown")

    assert response.status_code == 200
    assert response.json()["results"][0]["status"] == "rejected_unknown_device"


def test_iot_batch_reports_invalid_physical_range(client):
    response = post_batch(client, batch_payload(rh_x100=12000, sequence=2055), nonce="nonce-range")

    assert response.status_code == 200
    assert response.json()["results"][0]["status"] == "rejected_invalid"


def test_iot_batch_rejects_inactive_gateway(client, db_session):
    gateway = db_session.scalar(select(IotGateway).where(IotGateway.gateway_id == GATEWAY_ID))
    gateway.is_active = False
    db_session.commit()

    response = post_batch(client, batch_payload(sequence=2056), nonce="nonce-inactive")

    assert response.status_code == 401
