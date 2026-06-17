from sqlalchemy import select

from app.models import Alert, NotificationEvent, NotificationPreference, PushDeviceToken, SensorReading, User


def valid_payload(**overrides):
    payload = {
        "device_id": "SILO-001",
        "device_token": "secret-token",
        "grain_temperature": 28.5,
        "ambient_temperature": 27.2,
        "ambient_humidity": 65.1,
        "battery_voltage": 3.91,
        "signal_quality": -67,
        "timestamp": "2026-05-26T20:00:00Z",
    }
    payload.update(overrides)
    return payload


def test_create_valid_reading(client, db_session):
    response = client.post("/api/readings", json=valid_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["reading"]["grain_temperature"] == 28.5
    assert body["alerts"] == []
    assert db_session.scalar(select(SensorReading)) is not None


def test_rejects_invalid_device_token(client):
    response = client.post("/api/readings", json=valid_payload(device_token="wrong-token"))

    assert response.status_code == 401


def test_creates_grain_temperature_alert(client):
    response = client.post("/api/readings", json=valid_payload(grain_temperature=31.0))

    assert response.status_code == 201
    alerts = response.json()["alerts"]
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "grain_temperature_high"
    assert alerts[0]["severity"] == "warning"


def test_creates_ambient_humidity_alert(client):
    response = client.post("/api/readings", json=valid_payload(ambient_humidity=72.0))

    assert response.status_code == 201
    alerts = response.json()["alerts"]
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "ambient_humidity_high"
    assert alerts[0]["severity"] == "warning"


def test_creates_critical_alert_when_temperature_and_humidity_are_high(client):
    response = client.post(
        "/api/readings",
        json=valid_payload(grain_temperature=31.5, ambient_humidity=72.1),
    )

    assert response.status_code == 201
    alerts = response.json()["alerts"]
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "critical_environment"
    assert alerts[0]["severity"] == "critical"


def test_creates_battery_low_alert(client):
    response = client.post("/api/readings", json=valid_payload(battery_voltage=3.3))

    assert response.status_code == 201
    alerts = response.json()["alerts"]
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "battery_low"
    assert alerts[0]["severity"] == "technical"


def test_does_not_duplicate_active_alerts(client, db_session):
    payload = valid_payload(grain_temperature=32.0)

    first_response = client.post("/api/readings", json=payload)
    second_response = client.post("/api/readings", json=payload)

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    alert_count = len(db_session.scalars(select(Alert).where(Alert.alert_type == "grain_temperature_high")).all())
    assert alert_count == 1
    assert second_response.json()["alerts"][0]["id"] == first_response.json()["alerts"][0]["id"]


def test_new_alert_creates_notification_event_when_preference_enabled(client, db_session):
    user = db_session.scalar(select(User).where(User.email == "cliente@silo-demo.local"))
    db_session.add(
        NotificationPreference(
            company_id=user.company_id,
            user_id=user.id,
            channel="telegram",
            destination="123456",
            minimum_severity="warning",
            enabled=True,
        )
    )
    db_session.commit()

    response = client.post("/api/readings", json=valid_payload(grain_temperature=31.0))

    assert response.status_code == 201
    event = db_session.scalar(select(NotificationEvent).where(NotificationEvent.channel == "telegram"))
    assert event is not None
    assert event.status == "skipped"
    assert "Telegram" in event.error


def test_reused_active_alert_does_not_create_duplicate_notification_event(client, db_session):
    user = db_session.scalar(select(User).where(User.email == "cliente@silo-demo.local"))
    db_session.add(
        NotificationPreference(
            company_id=user.company_id,
            user_id=user.id,
            channel="telegram",
            destination="123456",
            minimum_severity="warning",
            enabled=True,
        )
    )
    db_session.commit()
    payload = valid_payload(grain_temperature=31.0)

    client.post("/api/readings", json=payload)
    client.post("/api/readings", json=payload)

    events = db_session.scalars(select(NotificationEvent).where(NotificationEvent.channel == "telegram")).all()
    assert len(events) == 1
