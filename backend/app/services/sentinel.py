import re
import secrets
import unicodedata
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_secret, verify_secret
from app.models import (
    Alert,
    AlertContact,
    NotificationDelivery,
    SentinelDevice,
    SentinelJob,
    StorageUnit,
    utc_now,
)

SEVERITY_RANK = {"info": 0, "technical": 1, "warning": 2, "critical": 3}
TERMINAL_JOB_STATUSES = {"submitted", "attempted", "cancelled", "expired"}


def normalize_phone_e164(value: str) -> str:
    compact = re.sub(r"[\s().-]", "", value.strip())
    if not re.fullmatch(r"\+[1-9]\d{7,14}", compact):
        raise ValueError("El telefono debe usar formato internacional E.164, por ejemplo +5917XXXXXXX.")
    return compact


def mask_phone(value: str | None) -> str | None:
    if not value:
        return value
    visible = value[-3:]
    return f"{value[:4]}{'*' * max(4, len(value) - 7)}{visible}"


def issue_sentinel_token() -> tuple[str, str]:
    token = f"ags_{secrets.token_urlsafe(32)}"
    return token, hash_secret(token)


def authenticate_sentinel(db: Session, token: str, device_uid: str | None = None) -> SentinelDevice:
    device = db.scalar(select(SentinelDevice).where(SentinelDevice.token_hash == hash_secret(token)))
    if (
        device is None
        or not device.active
        or not verify_secret(token, device.token_hash)
        or (device_uid is not None and device.device_uid != device_uid)
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales Sentinel invalidas.")
    return device


def queue_alert_jobs(db: Session, alert: Alert) -> list[SentinelJob]:
    contacts = list(
        db.scalars(
            select(AlertContact)
            .where(
                AlertContact.company_id == alert.company_id,
                AlertContact.active.is_(True),
                or_(
                    AlertContact.storage_unit_id.is_(None),
                    AlertContact.storage_unit_id == alert.storage_unit_id,
                ),
            )
            .order_by(AlertContact.priority.asc(), AlertContact.id.asc())
        ).all()
    )
    jobs: list[SentinelJob] = []
    for contact in contacts:
        if SEVERITY_RANK.get(alert.severity, -1) < SEVERITY_RANK.get(contact.minimum_severity, 3):
            continue
        if contact.receive_sms:
            jobs.append(_create_job(db, alert=alert, contact=contact, job_type="sms"))
        if contact.receive_call:
            jobs.append(_create_job(db, alert=alert, contact=contact, job_type="call"))
    return jobs


def create_test_job(db: Session, contact: AlertContact, job_type: str) -> SentinelJob:
    if job_type not in {"sms", "call"}:
        raise ValueError("Canal Sentinel no soportado.")
    nonce = secrets.token_hex(8)
    message = "AGROESCUDO: Numero de alerta verificado."
    delivery = NotificationDelivery(
        company_id=contact.company_id,
        channel=job_type,
        provider="agroescudo_sentinel",
        destination=contact.phone_e164,
        severity="test",
        status="pending",
        dry_run=False,
        payload_preview=message,
        idempotency_key=f"sentinel:test:{contact.id}:{job_type}:{nonce}",
    )
    db.add(delivery)
    db.flush()
    job = SentinelJob(
        alert_contact_id=contact.id,
        notification_delivery_id=delivery.id,
        job_type=job_type,
        status="pending",
        destination_phone=contact.phone_e164,
        message=message,
        ring_seconds=settings.sentinel_default_ring_seconds if job_type == "call" else None,
        idempotency_key=f"sentinel:test:{contact.id}:{job_type}:{nonce}",
        not_before=utc_now(),
        expires_at=utc_now() + timedelta(minutes=settings.sentinel_job_expiry_minutes),
        max_attempts=settings.sentinel_max_attempts,
    )
    db.add(job)
    db.flush()
    return job


def cancel_future_jobs(db: Session, alert_id: int) -> int:
    now = utc_now()
    delivery_ids = list(
        db.scalars(
            select(SentinelJob.notification_delivery_id).where(
                SentinelJob.alert_id == alert_id,
                SentinelJob.status.in_(("pending", "failed")),
                SentinelJob.notification_delivery_id.is_not(None),
            )
        ).all()
    )
    result = db.execute(
        update(SentinelJob)
        .where(
            SentinelJob.alert_id == alert_id,
            SentinelJob.status.in_(("pending", "failed")),
        )
        .values(status="cancelled", completed_at=now, updated_at=now, lease_until=None)
    )
    if delivery_ids:
        db.execute(
            update(NotificationDelivery)
            .where(NotificationDelivery.id.in_(delivery_ids))
            .values(status="cancelled", updated_at=now, next_retry_at=None)
        )
    return int(result.rowcount or 0)


def poll_sentinel(db: Session, device: SentinelDevice, *, source_ip: str | None = None) -> dict:
    now = utc_now()
    _expire_jobs(db, now)
    job = _claim_next_job(db, device, now)
    device.last_seen_at = now
    device.last_ip = source_ip[:80] if source_ip else None
    device.updated_at = now
    db.commit()
    if job is not None:
        db.refresh(job)

    pending_jobs = db.scalar(
        select(func.count(SentinelJob.id)).where(SentinelJob.status.in_(("pending", "failed")))
    ) or 0
    critical_alerts = db.scalar(
        select(func.count(Alert.id)).where(Alert.is_active.is_(True), Alert.severity == "critical")
    ) or 0
    last_status = db.scalar(
        select(SentinelJob.status)
        .where(SentinelJob.sentinel_device_id == device.id)
        .order_by(SentinelJob.updated_at.desc())
        .limit(1)
    )
    return {
        "server": "online",
        "database": "online",
        "server_time": now,
        "critical_alerts": int(critical_alerts),
        "pending_jobs": int(pending_jobs),
        "poll_after_seconds": max(30, min(600, settings.sentinel_poll_after_seconds)),
        "last_job_status": last_status,
        "job": (
            {
                "id": job.id,
                "type": job.job_type,
                "phone": job.destination_phone,
                "message": job.message,
                "ring_seconds": job.ring_seconds,
                "lease_until": job.lease_until,
            }
            if job is not None
            else None
        ),
    }


def record_job_result(
    db: Session,
    device: SentinelDevice,
    job_id: str,
    *,
    result_status: str,
    result_code: str,
    message: str | None,
) -> SentinelJob:
    job = db.get(SentinelJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trabajo Sentinel no encontrado.")
    if job.sentinel_device_id != device.id or job.status != "claimed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El trabajo no esta reclamado por este Sentinel.")
    now = utc_now()
    if job.lease_until is None or _as_aware(job.lease_until) < now:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El lease del trabajo expiro.")
    if result_status == "submitted" and job.job_type != "sms":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="submitted solo aplica a SMS.")
    if result_status == "attempted" and job.job_type != "call":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="attempted solo aplica a llamadas.")

    clean_message = _sanitize_error(message)
    job.result_code = result_code[:80]
    job.updated_at = now
    job.lease_until = None
    delivery = db.get(NotificationDelivery, job.notification_delivery_id) if job.notification_delivery_id else None
    if result_status in {"submitted", "attempted"}:
        job.status = result_status
        job.completed_at = now
        job.last_error_code = None
        job.last_error_message = None
        if delivery is not None:
            delivery.status = result_status
            delivery.sent_at = now if result_status == "submitted" else None
            delivery.attempted_at = now
            delivery.provider_response = (
                "El modem acepto el SMS." if result_status == "submitted" else "El modem inicio la llamada."
            )
            delivery.updated_at = now
    else:
        job.status = "failed"
        job.last_error_code = result_code[:80]
        job.last_error_message = clean_message
        if job.attempt_count < job.max_attempts:
            delay = (1, 5, 15)[min(max(job.attempt_count - 1, 0), 2)]
            job.not_before = now + timedelta(minutes=delay)
        else:
            job.completed_at = now
        if delivery is not None:
            delivery.status = "failed"
            delivery.failed_at = now
            delivery.error_code = result_code[:80]
            delivery.error_message_sanitized = clean_message
            delivery.error = clean_message
            delivery.retry_count = job.attempt_count
            delivery.updated_at = now
    db.commit()
    db.refresh(job)
    return job


def device_summary(db: Session, device: SentinelDevice) -> dict:
    now = utc_now()
    last_seen = _as_aware(device.last_seen_at) if device.last_seen_at else None
    pending = db.scalar(select(func.count(SentinelJob.id)).where(SentinelJob.status.in_(("pending", "failed")))) or 0
    last_status = db.scalar(
        select(SentinelJob.status)
        .where(SentinelJob.sentinel_device_id == device.id)
        .order_by(SentinelJob.updated_at.desc())
        .limit(1)
    )
    return {
        "id": device.id,
        "device_uid": device.device_uid,
        "name": device.name,
        "active": device.active,
        "online": bool(last_seen and (now - last_seen).total_seconds() <= settings.sentinel_offline_after_seconds),
        "last_seen_at": device.last_seen_at,
        "firmware_version": device.firmware_version,
        "wifi_rssi": device.wifi_rssi,
        "gsm_registered": device.gsm_registered,
        "sim_ready": device.sim_ready,
        "pending_jobs": int(pending),
        "last_job_status": last_status,
        "created_at": device.created_at,
        "updated_at": device.updated_at,
    }


def _create_job(db: Session, *, alert: Alert, contact: AlertContact, job_type: str) -> SentinelJob:
    key = f"sentinel:alert:{alert.id}:contact:{contact.id}:{job_type}"
    existing = db.scalar(select(SentinelJob).where(SentinelJob.idempotency_key == key))
    if existing is not None:
        return existing
    unit = db.get(StorageUnit, alert.storage_unit_id)
    message = _alert_sms(alert, unit.name if unit else "unidad monitoreada")
    delivery = NotificationDelivery(
        company_id=alert.company_id,
        alert_id=alert.id,
        channel=job_type,
        provider="agroescudo_sentinel",
        destination=contact.phone_e164,
        severity=alert.severity,
        status="pending",
        dry_run=False,
        payload_preview=message,
        idempotency_key=key,
    )
    db.add(delivery)
    db.flush()
    created = _as_aware(alert.created_at)
    job = SentinelJob(
        alert_id=alert.id,
        alert_contact_id=contact.id,
        notification_delivery_id=delivery.id,
        job_type=job_type,
        status="pending",
        destination_phone=contact.phone_e164,
        message=message,
        ring_seconds=settings.sentinel_default_ring_seconds if job_type == "call" else None,
        idempotency_key=key,
        not_before=created + timedelta(minutes=contact.escalation_delay_minutes),
        expires_at=created + timedelta(minutes=settings.sentinel_job_expiry_minutes),
        max_attempts=settings.sentinel_max_attempts,
    )
    db.add(job)
    db.flush()
    return job


def _claim_next_job(db: Session, device: SentinelDevice, now: datetime) -> SentinelJob | None:
    candidate_ids = list(
        db.scalars(
            select(SentinelJob.id)
            .where(
                SentinelJob.status.in_(("pending", "failed", "claimed")),
                SentinelJob.not_before <= now,
                or_(SentinelJob.expires_at.is_(None), SentinelJob.expires_at > now),
                SentinelJob.attempt_count < SentinelJob.max_attempts,
                or_(SentinelJob.status != "claimed", SentinelJob.lease_until < now),
            )
            .order_by(SentinelJob.not_before.asc(), SentinelJob.created_at.asc())
            .limit(5)
        ).all()
    )
    for candidate_id in candidate_ids:
        lease_until = now + timedelta(seconds=settings.sentinel_lease_seconds)
        result = db.execute(
            update(SentinelJob)
            .where(
                SentinelJob.id == candidate_id,
                SentinelJob.status.in_(("pending", "failed", "claimed")),
                or_(SentinelJob.status != "claimed", SentinelJob.lease_until < now),
            )
            .values(
                sentinel_device_id=device.id,
                status="claimed",
                claimed_at=now,
                lease_until=lease_until,
                attempt_count=SentinelJob.attempt_count + 1,
                updated_at=now,
            )
        )
        if result.rowcount == 1:
            db.flush()
            return db.get(SentinelJob, candidate_id)
    return None


def _expire_jobs(db: Session, now: datetime) -> None:
    delivery_ids = list(
        db.scalars(
            select(SentinelJob.notification_delivery_id).where(
                SentinelJob.expires_at.is_not(None),
                SentinelJob.expires_at <= now,
                SentinelJob.status.in_(("pending", "failed", "claimed")),
                SentinelJob.notification_delivery_id.is_not(None),
            )
        ).all()
    )
    db.execute(
        update(SentinelJob)
        .where(
            SentinelJob.expires_at.is_not(None),
            SentinelJob.expires_at <= now,
            SentinelJob.status.in_(("pending", "failed", "claimed")),
        )
        .values(status="expired", completed_at=now, lease_until=None, updated_at=now)
    )
    if delivery_ids:
        db.execute(
            update(NotificationDelivery)
            .where(NotificationDelivery.id.in_(delivery_ids))
            .values(status="expired", updated_at=now, next_retry_at=None)
        )


def _alert_sms(alert: Alert, unit_name: str) -> str:
    metric = ""
    if alert.observed_value is not None:
        metric = f" Valor {alert.observed_value:.1f}."
    raw = f"AGROESCUDO: Alerta {alert.severity} en {unit_name}.{metric} Revisar ahora."
    return _ascii_text(raw)[:300]


def _ascii_text(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")


def _sanitize_error(value: str | None) -> str | None:
    if value is None:
        return None
    return value.replace("\r", " ").replace("\n", " ")[:500]


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
