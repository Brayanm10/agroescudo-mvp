from datetime import datetime, timezone

from sqlalchemy import select

from app.core.config import settings
from app.models import NotificationDelivery, User


def _headers(client, email: str = "admin@agroescudo.local", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _delivery(db_session, *, status: str, user_id: int | None = None, retry_count: int = 0):
    user = db_session.scalar(select(User).where(User.email == "cliente@silo-demo.local"))
    record = NotificationDelivery(
        company_id=user.company_id,
        user_id=user_id if user_id is not None else user.id,
        channel="telegram",
        provider="telegram_bot_api",
        destination="123456",
        severity="critical",
        status=status,
        dry_run=False,
        payload_preview="Alerta operativa controlada.",
        retry_count=retry_count,
        idempotency_key=f"notification-test-{status}-{retry_count}-{datetime.now(timezone.utc).timestamp()}",
    )
    if status == "sent":
        record.sent_at = datetime.now(timezone.utc)
    db_session.add(record)
    db_session.commit()
    db_session.refresh(record)
    return record


def test_sent_is_not_delivered_until_provider_confirmation(client, db_session):
    delivery = _delivery(db_session, status="sent")

    listed = client.get("/api/notifications/deliveries", headers=_headers(client))
    assert listed.status_code == 200, listed.text
    row = next(item for item in listed.json() if item["id"] == delivery.id)
    assert row["status"] == "sent"
    assert row["sent_at"] is not None
    assert row["delivered_at"] is None

    confirmed = client.post(
        f"/api/notifications/{delivery.id}/provider-status",
        headers=_headers(client),
        json={"status": "DELIVERED", "provider_message_id": "provider-001"},
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "delivered"
    assert confirmed.json()["delivered_at"] is not None


def test_failed_delivery_retries_with_audit_fields(client, db_session, monkeypatch):
    delivery = _delivery(db_session, status="failed")

    def fake_deliver(record):
        record.status = "sent"
        record.sent_at = datetime.now(timezone.utc)
        record.attempted_at = record.sent_at
        record.provider_message_id = "retry-provider-001"

    monkeypatch.setattr("app.services.notifications._deliver_delivery", fake_deliver)
    response = client.post(
        f"/api/notifications/{delivery.id}/retry",
        headers=_headers(client),
    )
    assert response.status_code == 200, response.text
    assert response.json()["retry_count"] == 1
    assert response.json()["status"] == "sent"
    assert response.json()["provider_message_id"] == "retry-provider-001"


def test_retry_limit_and_dry_run_are_enforced(client, db_session):
    delivery = _delivery(
        db_session,
        status="failed",
        retry_count=settings.notification_max_retries,
    )
    response = client.post(
        f"/api/notifications/{delivery.id}/retry",
        headers=_headers(client),
    )
    assert response.status_code == 409
    assert "maximo de reintentos" in response.json()["detail"]

    dry = NotificationDelivery(
        company_id=1,
        user_id=3,
        channel="telegram",
        provider="telegram_bot_api",
        destination="123456",
        severity="test",
        status="dry_run",
        dry_run=True,
        payload_preview="Simulacion.",
        idempotency_key="dry-run-no-retry",
    )
    db_session.add(dry)
    db_session.commit()
    response = client.post(f"/api/notifications/{dry.id}/retry", headers=_headers(client))
    assert response.status_code == 409
    assert "simulados" in response.json()["detail"]


def test_client_only_lists_own_deliveries(client, db_session):
    client_user = db_session.scalar(select(User).where(User.email == "cliente@silo-demo.local"))
    technician = db_session.scalar(select(User).where(User.email == "tecnico@agroescudo.local"))
    own = _delivery(db_session, status="sent", user_id=client_user.id)
    foreign = _delivery(db_session, status="sent", user_id=technician.id)

    response = client.get(
        "/api/notifications/deliveries",
        headers=_headers(client, "cliente@silo-demo.local", "cliente123"),
    )
    assert response.status_code == 200, response.text
    ids = {item["id"] for item in response.json()}
    assert own.id in ids
    assert foreign.id not in ids
