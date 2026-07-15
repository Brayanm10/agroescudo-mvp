from dataclasses import dataclass
from email.message import EmailMessage
import smtplib

import httpx

from app.core.config import settings


class EmailConfigurationError(RuntimeError):
    pass


@dataclass
class EmailResult:
    status: str
    provider: str
    preview_token: str | None = None
    provider_message_id: str | None = None
    error: str | None = None


def _requires_credentials(provider: str) -> None:
    if not settings.email_from:
        raise EmailConfigurationError("REQUIERE CREDENCIAL: configura EMAIL_FROM.")
    if provider == "resend" and not settings.email_api_key:
        raise EmailConfigurationError("REQUIERE CREDENCIAL: configura EMAIL_API_KEY.")
    if provider in {"gmail", "smtp"} and not (settings.smtp_username and settings.smtp_password):
        raise EmailConfigurationError("REQUIERE CREDENCIAL: configura SMTP_USERNAME y SMTP_PASSWORD.")


def send_transactional_email(
    *,
    to_email: str,
    subject: str,
    body: str,
    preview_token: str | None = None,
) -> EmailResult:
    if not settings.email_enabled:
        return EmailResult(
            status="preview",
            provider="disabled",
            preview_token=preview_token if settings.environment.lower() != "production" else None,
        )

    provider = settings.email_provider.lower()
    if provider not in {"resend", "gmail", "smtp"}:
        raise EmailConfigurationError("EMAIL_PROVIDER no soportado. Usa resend, gmail o smtp.")

    _requires_credentials(provider)
    if provider in {"gmail", "smtp"}:
        return _send_smtp_email(to_email=to_email, subject=subject, body=body, provider=provider)

    payload: dict[str, object] = {
        "from": settings.email_from,
        "to": [to_email],
        "subject": subject,
        "text": body,
    }
    if settings.email_reply_to:
        payload["reply_to"] = [settings.email_reply_to]

    try:
        with httpx.Client(timeout=15) as client:
            response = client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.email_api_key}"},
                json=payload,
            )
        if response.status_code >= 300:
            return EmailResult(
                status="failed",
                provider="resend",
                error=f"Resend HTTP {response.status_code}: {response.text[:240]}",
            )
        message_id = (response.json() or {}).get("id")
        return EmailResult(status="sent", provider="resend", provider_message_id=message_id)
    except httpx.HTTPError as exc:
        return EmailResult(status="failed", provider="resend", error=f"Resend network error: {exc.__class__.__name__}")


def _send_smtp_email(*, to_email: str, subject: str, body: str, provider: str) -> EmailResult:
    message = EmailMessage()
    message["From"] = settings.email_from
    message["To"] = to_email
    message["Subject"] = subject
    if settings.email_reply_to:
        message["Reply-To"] = settings.email_reply_to
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as client:
            if settings.smtp_use_tls:
                client.starttls()
            client.login(settings.smtp_username, settings.smtp_password)
            client.send_message(message)
        return EmailResult(status="sent", provider=provider)
    except (OSError, smtplib.SMTPException) as exc:
        return EmailResult(status="failed", provider=provider, error=f"SMTP error: {exc.__class__.__name__}")
