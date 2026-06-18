from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Alert, NotificationDelivery, NotificationEvent, NotificationPreference, PushDeviceToken, SensorReading, User

CHANNELS = {"whatsapp", "telegram", "push"}


def upsert_preference(
    db: Session,
    user: User,
    *,
    channel: str,
    enabled: bool,
    destination: str | None,
    minimum_severity: str,
) -> NotificationPreference:
    if channel not in CHANNELS:
        raise ValueError("Unsupported notification channel")
    preference = db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user.id,
            NotificationPreference.channel == channel,
        )
    )
    if preference is None:
        preference = NotificationPreference(company_id=user.company_id, user_id=user.id, channel=channel)
        db.add(preference)
    preference.company_id = user.company_id
    preference.enabled = enabled
    preference.destination = destination
    preference.minimum_severity = minimum_severity
    preference.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(preference)
    return preference


def register_push_token(db: Session, user: User, *, token: str, platform: str) -> PushDeviceToken:
    record = db.scalar(select(PushDeviceToken).where(PushDeviceToken.token == token))
    if record is None:
        record = PushDeviceToken(company_id=user.company_id, user_id=user.id, token=token)
        db.add(record)
    record.company_id = user.company_id
    record.user_id = user.id
    record.platform = platform
    record.is_active = True
    record.last_seen_at = datetime.now(timezone.utc)

    preference = db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user.id,
            NotificationPreference.channel == "push",
        )
    )
    if preference is None:
        preference = NotificationPreference(
            company_id=user.company_id,
            user_id=user.id,
            channel="push",
            enabled=True,
            minimum_severity="critical",
        )
        db.add(preference)

    db.commit()
    db.refresh(record)
    return record


def dispatch_alert_notifications(db: Session, alert: Alert, reading: SensorReading | None = None) -> list[NotificationEvent]:
    preferences = list(
        db.scalars(
            select(NotificationPreference).where(
                NotificationPreference.company_id == alert.company_id,
                NotificationPreference.enabled.is_(True),
            )
        ).all()
    )
    events: list[NotificationEvent] = []
    for preference in preferences:
        if not _passes_severity(alert.severity, preference.minimum_severity):
            continue
        if preference.channel == "push":
            tokens = list(
                db.scalars(
                    select(PushDeviceToken).where(
                        PushDeviceToken.user_id == preference.user_id,
                        PushDeviceToken.is_active.is_(True),
                    )
                ).all()
            )
            for token in tokens:
                events.append(_send_or_record(db, alert, preference, token.token, reading))
        else:
            events.append(_send_or_record(db, alert, preference, preference.destination, reading))
            _create_delivery_for_alert(db, alert, preference, preference.destination, reading)
    return events


def send_test_notification(db: Session, user: User, channel: str) -> NotificationEvent:
    preference = db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == user.id,
            NotificationPreference.channel == channel,
        )
    )
    if preference is None:
        preference = NotificationPreference(
            company_id=user.company_id,
            user_id=user.id,
            channel=channel,
            enabled=True,
            destination=None,
            minimum_severity="all",
        )
        db.add(preference)
        db.flush()

    destination = preference.destination
    if channel == "push":
        token = db.scalar(
            select(PushDeviceToken).where(PushDeviceToken.user_id == user.id, PushDeviceToken.is_active.is_(True))
        )
        destination = token.token if token else None

    message = "Prueba AgroEscudo: canal de notificacion configurado para piloto."
    event = NotificationEvent(
        company_id=user.company_id,
        user_id=user.id,
        channel=channel,
        destination=destination,
        message=message,
        status="pending",
    )
    db.add(event)
    db.flush()
    _deliver_event(event, title="Prueba AgroEscudo", body=message)
    db.commit()
    db.refresh(event)
    return event


def create_admin_test_delivery(
    db: Session,
    *,
    user: User | None,
    channel: str,
    destination: str | None,
    message: str,
) -> NotificationDelivery:
    if channel not in {"whatsapp", "telegram"}:
        raise ValueError("Unsupported notification channel")
    delivery = NotificationDelivery(
        alert_id=None,
        user_id=user.id if user else None,
        channel=channel,
        destination=destination,
        severity="test",
        status="dry_run" if settings.notifications_dry_run else "pending",
        dry_run=settings.notifications_dry_run,
        payload_preview=message,
    )
    db.add(delivery)
    db.flush()
    _deliver_delivery(delivery)
    db.commit()
    db.refresh(delivery)
    return delivery


def _send_or_record(
    db: Session,
    alert: Alert,
    preference: NotificationPreference,
    destination: str | None,
    reading: SensorReading | None,
) -> NotificationEvent:
    message = _alert_message(alert, reading)
    event = NotificationEvent(
        company_id=alert.company_id,
        user_id=preference.user_id,
        alert_id=alert.id,
        channel=preference.channel,
        destination=destination,
        message=message,
        status="pending",
    )
    db.add(event)
    db.flush()
    _deliver_event(event, title=alert.title, body=message)
    return event


def _create_delivery_for_alert(
    db: Session,
    alert: Alert,
    preference: NotificationPreference,
    destination: str | None,
    reading: SensorReading | None,
) -> NotificationDelivery:
    existing = db.scalar(
        select(NotificationDelivery).where(
            NotificationDelivery.alert_id == alert.id,
            NotificationDelivery.user_id == preference.user_id,
            NotificationDelivery.channel == preference.channel,
        )
    )
    if existing is not None:
        return existing

    message = _alert_message(alert, reading)
    delivery = NotificationDelivery(
        alert_id=alert.id,
        user_id=preference.user_id,
        channel=preference.channel,
        destination=destination,
        severity=alert.severity,
        status="dry_run" if settings.notifications_dry_run else "pending",
        dry_run=settings.notifications_dry_run,
        payload_preview=message,
    )
    db.add(delivery)
    db.flush()
    _deliver_delivery(delivery)
    return delivery


def _deliver_delivery(delivery: NotificationDelivery) -> None:
    delivery.updated_at = datetime.now(timezone.utc)
    if delivery.dry_run:
        delivery.status = "dry_run"
        delivery.provider_response = "Dry-run activo. No se envio mensaje real."
        return
    if delivery.channel == "whatsapp":
        _send_whatsapp_delivery(delivery)
    elif delivery.channel == "telegram":
        _send_telegram_delivery(delivery)
    else:
        delivery.status = "skipped"
        delivery.error = "Canal no soportado para delivery comercial."


def _send_whatsapp_delivery(delivery: NotificationDelivery) -> None:
    if not settings.whatsapp_enabled or not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        delivery.status = "skipped"
        delivery.error = "WhatsApp Cloud API no configurado."
        return
    if not delivery.destination:
        delivery.status = "skipped"
        delivery.error = "Destino WhatsApp no configurado."
        return
    url = (
        f"https://graph.facebook.com/{settings.whatsapp_api_version}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": delivery.destination,
        "type": "text",
        "text": {"body": delivery.payload_preview[:3900]},
    }
    _post_json_delivery(delivery, url, payload, {"Authorization": f"Bearer {settings.whatsapp_access_token}"})


def _send_telegram_delivery(delivery: NotificationDelivery) -> None:
    if not settings.telegram_enabled or not settings.telegram_bot_token:
        delivery.status = "skipped"
        delivery.error = "Telegram Bot API no configurado."
        return
    if not delivery.destination:
        delivery.status = "skipped"
        delivery.error = "Chat ID de Telegram no configurado."
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {"chat_id": delivery.destination, "text": delivery.payload_preview[:3900]}
    _post_json_delivery(delivery, url, payload)


def _deliver_event(event: NotificationEvent, *, title: str, body: str) -> None:
    if event.channel == "whatsapp":
        _send_whatsapp(event, body)
    elif event.channel == "telegram":
        _send_telegram(event, body)
    elif event.channel == "push":
        _send_push(event, title, body)
    else:
        event.status = "skipped"
        event.error = "Canal no soportado."


def _send_whatsapp(event: NotificationEvent, body: str) -> None:
    if settings.notifications_dry_run:
        event.status = "skipped"
        event.error = "Dry-run activo para WhatsApp. No se envio mensaje real."
        return
    if not settings.whatsapp_enabled or not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        event.status = "skipped"
        event.error = "WhatsApp Cloud API no configurado."
        return
    if not event.destination:
        event.status = "skipped"
        event.error = "Destino WhatsApp no configurado."
        return
    url = (
        f"https://graph.facebook.com/{settings.whatsapp_api_version}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": event.destination,
        "type": "text",
        "text": {"body": body[:3900]},
    }
    _post_json(event, url, payload, {"Authorization": f"Bearer {settings.whatsapp_access_token}"})


def _send_telegram(event: NotificationEvent, body: str) -> None:
    if settings.notifications_dry_run:
        event.status = "skipped"
        event.error = "Dry-run activo para Telegram. No se envio mensaje real."
        return
    if not settings.telegram_enabled or not settings.telegram_bot_token:
        event.status = "skipped"
        event.error = "Telegram Bot API no configurado."
        return
    if not event.destination:
        event.status = "skipped"
        event.error = "Chat ID de Telegram no configurado."
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {"chat_id": event.destination, "text": body[:3900]}
    _post_json(event, url, payload)


def _send_push(event: NotificationEvent, title: str, body: str) -> None:
    if not settings.fcm_enabled or not settings.firebase_project_id or not settings.firebase_service_account_file:
        event.status = "skipped"
        event.error = "Firebase Cloud Messaging no configurado."
        return
    if not event.destination:
        event.status = "skipped"
        event.error = "Token push no configurado."
        return
    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request

        credentials = service_account.Credentials.from_service_account_file(
            settings.firebase_service_account_file,
            scopes=["https://www.googleapis.com/auth/firebase.messaging"],
        )
        credentials.refresh(Request())
        url = f"https://fcm.googleapis.com/v1/projects/{settings.firebase_project_id}/messages:send"
        payload = {
            "message": {
                "token": event.destination,
                "notification": {"title": title, "body": body[:240]},
                "data": {"source": "agroescudo", "event_id": str(event.id)},
            }
        }
        _post_json(event, url, payload, {"Authorization": f"Bearer {credentials.token}"})
    except Exception as exc:  # pragma: no cover - depends on external credentials
        event.status = "failed"
        event.error = f"FCM error: {exc.__class__.__name__}"


def _post_json(event: NotificationEvent, url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> None:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(url, json=payload, headers=headers)
        if response.status_code >= 300:
            event.status = "failed"
            event.error = f"Provider HTTP {response.status_code}: {response.text[:300]}"
            return
        data = response.json() if response.content else {}
        event.status = "sent"
        event.provider_message_id = _provider_id(data)
        event.sent_at = datetime.now(timezone.utc)
    except Exception as exc:  # pragma: no cover - network failure shape depends on provider
        event.status = "failed"
        event.error = f"Provider error: {exc.__class__.__name__}"


def _post_json_delivery(
    delivery: NotificationDelivery,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str] | None = None,
) -> None:
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(url, json=payload, headers=headers)
        if response.status_code >= 300:
            delivery.status = "failed"
            delivery.error = f"Provider HTTP {response.status_code}: {response.text[:300]}"
            return
        data = response.json() if response.content else {}
        delivery.status = "sent"
        delivery.provider_response = str(_provider_id(data) or data)[:500]
        delivery.updated_at = datetime.now(timezone.utc)
    except Exception as exc:  # pragma: no cover - network failure shape depends on provider
        delivery.status = "failed"
        delivery.error = f"Provider error: {exc.__class__.__name__}"


def _provider_id(data: dict[str, Any]) -> str | None:
    if "messages" in data and data["messages"]:
        return str(data["messages"][0].get("id"))
    if "result" in data and isinstance(data["result"], dict):
        return str(data["result"].get("message_id"))
    if "name" in data:
        return str(data["name"])
    return None


def _alert_message(alert: Alert, reading: SensorReading | None) -> str:
    metrics = ""
    if reading is not None:
        metrics = (
            f"\nLectura: grano {reading.grain_temperature:.1f} C, "
            f"humedad {reading.ambient_humidity:.1f}%, bateria {reading.battery_voltage:.2f} V."
        )
    return (
        f"AgroEscudo - {alert.title}\n"
        f"Nivel: {alert.severity.upper()}\n"
        f"{alert.message}{metrics}\n"
        "Revisar la app para reconocer la alerta y registrar accion operativa."
    )


def _passes_severity(alert_severity: str, minimum: str) -> bool:
    if minimum == "all":
        return True
    if minimum == "critical":
        return alert_severity == "critical"
    if minimum == "warning":
        return alert_severity in {"warning", "critical"}
    if minimum == "technical":
        return alert_severity in {"technical", "critical"}
    return alert_severity == minimum
