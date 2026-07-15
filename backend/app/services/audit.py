import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditEvent, User

_SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "authorization", "jwt"}


def _redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "[REDACTED]" if any(sensitive in key.lower() for sensitive in _SENSITIVE_KEYS) else _redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


def record_audit_event(
    db: Session,
    *,
    action: str,
    summary: str,
    user: User | None = None,
    company_id: int | None = None,
    resource_type: str | None = None,
    resource_id: str | int | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        company_id=company_id if company_id is not None else (user.company_id if user else None),
        user_id=user.id if user else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        summary=summary[:255],
        metadata_json=json.dumps(_redact(metadata or {}), ensure_ascii=False),
    )
    db.add(event)
    return event
