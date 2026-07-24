from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Alert, NotificationDelivery, NotificationEvent, NotificationPreference, PushDeviceToken, SensorReading, User
from app.services.email import EmailConfigurationError, send_transactional_email

CHANNELS = {"whatsapp", "telegram", "push", "email", "in_app"}


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
        preference = NotificationPreference(company_id=user.company_id or 0, user_id=user.id, channel=channel)
        db.add(preference)
    preference.company_id = user.company_id or 0
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


def deactivate_push_token(db: Session, user: User, *, token: str) -> None:
    record = db.scalar(
        select(PushDeviceToken).where(
            PushDeviceToken.token == token,
            PushDeviceToken.user_id == user.id,
        )
    )
    if record is not None:
        record.is_active = False
        record.last_seen_at = datetime.now(timezone.utc)
        db.commit()


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
    severity: str = "test",
) -> NotificationDelivery:
    if channel not in {"whatsapp", "telegram"}:
        raise ValueError("Unsupported notification channel")
    resolved_destination = destination
    if user is not None and not resolved_destination:
        resolved_destination = user.phone_whatsapp if channel == "whatsapp" else user.telegram_chat_id

    status = "dry_run" if settings.notifications_dry_run else "pending"
    error = None
    if not resolved_destination:
        status = "skipped"
        error = "Usuario sin telefono WhatsApp" if channel == "whatsapp" else "Usuario sin Telegram chat_id"

    delivery = NotificationDelivery(
        company_id=user.company_id if user else None,
        alert_id=None,
        user_id=user.id if user else None,
        channel=channel,
        provider=_provider_name(channel),
        destination=resolved_destination,
        severity=severity,
        status=status,
        dry_run=settings.notifications_dry_run,
        payload_preview=message,
        error=error,
        error_message_sanitized=error,
        idempotency_key=_idempotency_key("test", user.id if user else None, channel, message, datetime.now(timezone.utc).isoformat()),
    )
    db.add(delivery)
    db.flush()
    if resolved_destination:
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
        company_id=alert.company_id,
        alert_id=alert.id,
        user_id=preference.user_id,
        channel=preference.channel,
        provider=_provider_name(preference.channel),
        destination=destination,
        severity=alert.severity,
        status="dry_run" if settings.notifications_dry_run else "pending",
        dry_run=settings.notifications_dry_run,
        payload_preview=message,
        idempotency_key=_idempotency_key("alert", alert.id, preference.user_id, preference.channel, "v1"),
    )
    db.add(delivery)
    db.flush()
    _deliver_delivery(delivery)
    return delivery


def _deliver_delivery(delivery: NotificationDelivery) -> None:
    now = datetime.now(timezone.utc)
    delivery.updated_at = now
    delivery.attempted_at = now
    delivery.next_retry_at = None
    if delivery.dry_run:
        delivery.status = "dry_run"
        delivery.provider_response = "Dry-run activo. No se envio mensaje real."
        return
    if delivery.channel == "whatsapp":
        _send_whatsapp_delivery(delivery)
    elif delivery.channel == "telegram":
        _send_telegram_delivery(delivery)
    elif delivery.channel == "email":
        _send_email_delivery(delivery)
    elif delivery.channel == "in_app":
        delivery.status = "delivered"
        delivery.sent_at = now
        delivery.delivered_at = now
        delivery.provider_response = "Disponible en el centro de notificaciones."
    else:
        delivery.status = "skipped"
        _set_delivery_error(delivery, "UNSUPPORTED_CHANNEL", "Canal no soportado para delivery comercial.")


def _send_whatsapp_delivery(delivery: NotificationDelivery) -> None:
    if not settings.whatsapp_enabled or not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        delivery.status = "skipped"
        _set_delivery_error(delivery, "PROVIDER_NOT_CONFIGURED", "WhatsApp Cloud API no configurado.")
        return
    if not delivery.destination:
        delivery.status = "skipped"
        _set_delivery_error(delivery, "DESTINATION_MISSING", "Destino WhatsApp no configurado.")
        return
    url = (
        f"https://graph.facebook.com/{settings.whatsapp_api_version}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    payload = _whatsapp_payload(delivery.destination, delivery.payload_preview)
    _post_json_delivery(delivery, url, payload, {"Authorization": f"Bearer {settings.whatsapp_access_token}"})


def _send_telegram_delivery(delivery: NotificationDelivery) -> None:
    if not settings.telegram_enabled or not settings.telegram_bot_token:
        delivery.status = "skipped"
        _set_delivery_error(delivery, "PROVIDER_NOT_CONFIGURED", "Telegram Bot API no configurado.")
        return
    if not delivery.destination:
        delivery.status = "skipped"
        _set_delivery_error(delivery, "DESTINATION_MISSING", "Chat ID de Telegram no configurado.")
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    payload = {"chat_id": delivery.destination, "text": delivery.payload_preview[:3900]}
    _post_json_delivery(delivery, url, payload)


def _send_email_delivery(delivery: NotificationDelivery) -> None:
    if not delivery.destination:
        delivery.status = "skipped"
        _set_delivery_error(delivery, "DESTINATION_MISSING", "Correo de destino no configurado.")
        return
    try:
        result = send_transactional_email(
            to_email=delivery.destination,
            subject="Notificacion operativa AgroEscudo",
            body=delivery.payload_preview,
        )
    except EmailConfigurationError:
        delivery.status = "skipped"
        _set_delivery_error(delivery, "PROVIDER_NOT_CONFIGURED", "Proveedor de correo no configurado.")
        return
    delivery.provider = result.provider
    if result.status == "sent":
        delivery.status = "sent"
        delivery.sent_at = datetime.now(timezone.utc)
        delivery.provider_message_id = result.provider_message_id
        delivery.provider_response = "El proveedor acepto el mensaje."
    elif result.status == "preview":
        delivery.status = "dry_run"
        delivery.dry_run = True
        delivery.provider_response = "Correo simulado; EMAIL_ENABLED esta desactivado."
    else:
        _mark_delivery_failed(delivery, "EMAIL_PROVIDER_ERROR", result.error or "El proveedor rechazo el correo.")


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
    payload = _whatsapp_payload(event.destination, body)
    _post_json(event, url, payload, {"Authorization": f"Bearer {settings.whatsapp_access_token}"})


def _whatsapp_payload(destination: str, body: str) -> dict[str, Any]:
    if settings.whatsapp_template_alert:
        return {
            "messaging_product": "whatsapp",
            "to": destination,
            "type": "template",
            "template": {
                "name": settings.whatsapp_template_alert,
                "language": {"code": settings.whatsapp_template_language},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": body[:900]}],
                    }
                ],
            },
        }
    return {
        "messaging_product": "whatsapp",
        "to": destination,
        "type": "text",
        "text": {"body": body[:3900]},
    }


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
    if not settings.fcm_enabled or not settings.firebase_project_id or not (
        settings.firebase_service_account_file or settings.firebase_service_account_json
    ):
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

        scopes = ["https://www.googleapis.com/auth/firebase.messaging"]
        if settings.firebase_service_account_json:
            raw = settings.firebase_service_account_json.strip()
            try:
                service_account_info = json.loads(raw)
            except json.JSONDecodeError:
                service_account_info = json.loads(base64.b64decode(raw).decode("utf-8"))
            credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)
        else:
            credentials = service_account.Credentials.from_service_account_file(
                settings.firebase_service_account_file,
                scopes=scopes,
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
            _mark_delivery_failed(delivery, f"HTTP_{response.status_code}", f"Proveedor HTTP {response.status_code}.")
            return
        data = response.json() if response.content else {}
        delivery.status = "sent"
        delivery.provider_message_id = _provider_id(data)
        delivery.provider_response = "El proveedor acepto el mensaje."
        delivery.sent_at = datetime.now(timezone.utc)
        delivery.failed_at = None
        delivery.error = None
        delivery.error_code = None
        delivery.error_message_sanitized = None
        delivery.next_retry_at = None
        delivery.updated_at = delivery.sent_at
    except Exception as exc:  # pragma: no cover - network failure shape depends on provider
        _mark_delivery_failed(delivery, "PROVIDER_CONNECTION_ERROR", f"Error de conexion: {exc.__class__.__name__}.")


def retry_delivery(db: Session, delivery: NotificationDelivery) -> NotificationDelivery:
    if delivery.dry_run:
        raise ValueError("Los mensajes simulados no requieren reintento.")
    if delivery.status not in {"failed", "skipped"}:
        raise ValueError("Solo se pueden reintentar entregas fallidas u omitidas.")
    if delivery.retry_count >= settings.notification_max_retries:
        raise ValueError("La entrega alcanzo el maximo de reintentos.")
    delivery.retry_count += 1
    delivery.status = "pending"
    delivery.error = None
    delivery.error_code = None
    delivery.error_message_sanitized = None
    delivery.failed_at = None
    _deliver_delivery(delivery)
    db.commit()
    db.refresh(delivery)
    return delivery


def update_provider_delivery_status(
    db: Session,
    delivery: NotificationDelivery,
    *,
    provider_status: str,
    provider_message_id: str | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> NotificationDelivery:
    now = datetime.now(timezone.utc)
    if provider_status == "DELIVERED":
        if delivery.status not in {"sent", "delivered"}:
            raise ValueError("Solo una entrega SENT puede confirmarse como DELIVERED.")
        delivery.status = "delivered"
        delivery.delivered_at = now
        delivery.next_retry_at = None
    elif provider_status == "FAILED":
        _mark_delivery_failed(delivery, error_code or "PROVIDER_REPORTED_FAILURE", error_message or "Fallo reportado por proveedor.")
    else:
        raise ValueError("Estado de proveedor no soportado.")
    if provider_message_id:
        delivery.provider_message_id = provider_message_id
    delivery.updated_at = now
    db.commit()
    db.refresh(delivery)
    return delivery


def _mark_delivery_failed(delivery: NotificationDelivery, code: str, message: str) -> None:
    now = datetime.now(timezone.utc)
    delivery.status = "failed"
    delivery.failed_at = now
    _set_delivery_error(delivery, code, message)
    if delivery.retry_count < settings.notification_max_retries:
        delay_minutes = (3, 6, 12)[min(delivery.retry_count, 2)]
        delivery.next_retry_at = now + timedelta(minutes=delay_minutes)
    else:
        delivery.next_retry_at = None


def _set_delivery_error(delivery: NotificationDelivery, code: str, message: str) -> None:
    sanitized = message.replace("\r", " ").replace("\n", " ")[:500]
    delivery.error_code = code[:80]
    delivery.error_message_sanitized = sanitized
    delivery.error = sanitized


def _provider_name(channel: str) -> str:
    return {
        "whatsapp": "meta_cloud_api",
        "telegram": "telegram_bot_api",
        "email": settings.email_provider,
        "push": "fcm",
        "in_app": "agroescudo",
    }.get(channel, "unknown")


def _idempotency_key(*parts: object) -> str:
    raw = "|".join(str(part) for part in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


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
