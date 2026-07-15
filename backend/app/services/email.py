from dataclasses import dataclass

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


def _requires_credentials() -> None:
    if not settings.email_from or not settings.email_api_key:
        raise EmailConfigurationError("REQUIERE CREDENCIAL: configura EMAIL_FROM y EMAIL_API_KEY.")


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

    if settings.email_provider.lower() != "resend":
        raise EmailConfigurationError("EMAIL_PROVIDER no soportado. Usa resend.")

    _requires_credentials()
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
