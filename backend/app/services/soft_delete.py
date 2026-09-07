from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    AlertContact,
    Company,
    Device,
    DeviceChannel,
    IotDevice,
    IotGateway,
    NotificationPreference,
    PushDeviceToken,
    SentinelDevice,
    SentinelJob,
    StorageUnit,
    User,
    UserSession,
    utc_now,
)
from app.services.audit import record_audit_event


def soft_delete_user(db: Session, actor: User, user: User) -> None:
    if actor.id == user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes eliminar tu propia cuenta administrativa.")
    if user.role == "admin":
        remaining = db.scalar(
            select(func.count(User.id)).where(
                User.role == "admin",
                User.is_active.is_(True),
                User.deleted_at.is_(None),
                User.id != user.id,
            )
        ) or 0
        if remaining == 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No puedes eliminar el ultimo administrador operativo.")

    now = utc_now()
    for unit in db.scalars(
        select(StorageUnit).where(
            (StorageUnit.assigned_client_id == user.id) | (StorageUnit.assigned_technician_id == user.id)
        )
    ).all():
        if unit.assigned_client_id == user.id:
            unit.assigned_client_id = None
        if unit.assigned_technician_id == user.id:
            unit.assigned_technician_id = None
    for session in db.scalars(select(UserSession).where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))).all():
        session.revoked_at = now
    for preference in db.scalars(select(NotificationPreference).where(NotificationPreference.user_id == user.id)).all():
        preference.enabled = False
    for push_token in db.scalars(select(PushDeviceToken).where(PushDeviceToken.user_id == user.id)).all():
        push_token.is_active = False
    user.is_active = False
    user.status = "INACTIVE"
    user.deleted_at = now
    _audit(db, actor, "user.deleted", "Usuario retirado de la operacion.", "user", user.id)


def soft_delete_device(db: Session, actor: User, device: Device) -> None:
    now = utc_now()
    device.is_active = False
    device.operational_status = "retired"
    device.qr_revoked_at = now
    device.deleted_at = now
    for link in db.scalars(select(IotDevice).where(IotDevice.device_id == device.id)).all():
        link.is_active = False
    for channel in db.scalars(select(DeviceChannel).where(DeviceChannel.device_id == device.id)).all():
        channel.is_enabled = False
        if channel.retired_at is None:
            channel.retired_at = now
            channel.retirement_reason = "Dispositivo eliminado de la operacion"
    _audit(db, actor, "device.deleted", "Sensor retirado sin borrar telemetria historica.", "device", device.id)


def soft_delete_storage_unit(db: Session, actor: User, unit: StorageUnit) -> None:
    device_count = db.scalar(
        select(func.count(Device.id)).where(Device.storage_unit_id == unit.id, Device.deleted_at.is_(None))
    ) or 0
    if device_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Elimina primero los sensores vinculados. La telemetria historica se conservara.",
        )
    now = utc_now()
    unit.is_active = False
    unit.assigned_client_id = None
    unit.assigned_technician_id = None
    unit.deleted_at = now
    for contact in db.scalars(select(AlertContact).where(AlertContact.storage_unit_id == unit.id)).all():
        contact.active = False
    _audit(db, actor, "storage_unit.deleted", "Unidad retirada sin borrar su evidencia historica.", "storage_unit", unit.id)


def soft_delete_company(db: Session, actor: User, company: Company) -> None:
    linked_units = db.scalar(
        select(func.count(StorageUnit.id)).where(StorageUnit.company_id == company.id, StorageUnit.deleted_at.is_(None))
    ) or 0
    linked_users = db.scalar(
        select(func.count(User.id)).where(User.company_id == company.id, User.deleted_at.is_(None))
    ) or 0
    if linked_units or linked_users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"La empresa conserva {linked_units} unidad(es) y {linked_users} usuario(s). Retiralos antes de eliminarla.",
        )
    company.is_active = False
    company.deleted_at = utc_now()
    _audit(db, actor, "company.deleted", "Empresa retirada de la operacion.", "company", company.id)


def soft_delete_gateway(db: Session, actor: User, gateway: IotGateway) -> None:
    for link in db.scalars(select(IotDevice).where(IotDevice.gateway_id == gateway.id)).all():
        link.gateway_id = None
    gateway.associated_devices_count = 0
    gateway.is_active = False
    gateway.status = "DELETED"
    gateway.deleted_at = utc_now()
    _audit(db, actor, "gateway.deleted", "Gateway retirado; nodos desvinculados y lecturas preservadas.", "iot_gateway", gateway.id)


def soft_delete_sentinel(db: Session, actor: User, device: SentinelDevice) -> None:
    pending = db.scalar(
        select(func.count(SentinelJob.id)).where(
            SentinelJob.sentinel_device_id == device.id,
            SentinelJob.status.in_(["pending", "claimed"]),
        )
    ) or 0
    if pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El Sentinel tiene {pending} trabajo(s) pendiente(s). Finalizalos o espera su vencimiento antes de eliminar.",
        )
    device.active = False
    device.deleted_at = utc_now()
    _audit(db, actor, "sentinel.deleted", "Sentinel retirado de la operacion.", "sentinel_device", device.id)


def soft_delete_alert_contact(db: Session, actor: User, contact: AlertContact) -> None:
    pending = db.scalar(
        select(func.count(SentinelJob.id)).where(
            SentinelJob.alert_contact_id == contact.id,
            SentinelJob.status.in_(["pending", "claimed"]),
        )
    ) or 0
    if pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"El contacto tiene {pending} trabajo(s) Sentinel pendiente(s). Espera su cierre antes de eliminar.",
        )
    contact.active = False
    contact.deleted_at = utc_now()
    _audit(db, actor, "alert_contact.deleted", "Contacto de alerta retirado.", "alert_contact", contact.id)


def _audit(db: Session, actor: User, action: str, summary: str, resource_type: str, resource_id: int) -> None:
    record_audit_event(
        db,
        action=action,
        summary=summary,
        user=actor,
        resource_type=resource_type,
        resource_id=resource_id,
    )
