from datetime import datetime, timezone
from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.config import settings
from app.core.security import hash_password, hash_secret
from app.db.session import get_db
from app.models import Company, Device, NotificationDelivery, NotificationPreference, Site, StorageUnit, User, utc_now
from app.schemas import (
    AdminDeviceCreate,
    AdminDeviceSecretOut,
    AdminDeviceUpdate,
    AdminNotificationTestIn,
    CompanyCreate,
    CompanyOut,
    CompanyUpdate,
    DeviceOut,
    NotificationDeliveryOut,
    PasswordResetIn,
    StorageUnitCreate,
    StorageUnitOut,
    StorageUnitUpdate,
    UserCreate,
    UserOut,
    UserStorageUnitAssignmentsIn,
    UserUpdate,
)
from app.services.notifications import create_admin_test_delivery, upsert_preference

router = APIRouter(prefix="/admin", dependencies=[Depends(require_role("admin"))])


@router.get("/integrations/status")
def integration_status() -> dict[str, object]:
    """Expose configuration readiness without ever returning credential values."""
    return {
        "notifications_dry_run": settings.notifications_dry_run,
        "services": {
            "gemini": {
                "enabled": settings.ai_enabled and settings.agro_assistant_llm_enabled and settings.ai_provider == "gemini",
                "configured": bool(settings.gemini_api_key),
                "model": settings.gemini_model,
            },
            "telegram": {
                "enabled": settings.telegram_enabled,
                "configured": bool(settings.telegram_bot_token),
            },
            "whatsapp": {
                "enabled": settings.whatsapp_enabled,
                "configured": bool(settings.whatsapp_access_token and settings.whatsapp_phone_number_id),
                "template_configured": bool(settings.whatsapp_template_alert),
            },
            "email": {
                "enabled": settings.email_enabled,
                "configured": bool(settings.email_from and settings.email_api_key),
                "provider": settings.email_provider,
            },
            "fcm": {
                "enabled": settings.fcm_enabled,
                "configured": bool(
                    settings.firebase_project_id
                    and (settings.firebase_service_account_file or settings.firebase_service_account_json)
                ),
            },
            "storage": {
                "provider": settings.storage_provider,
                "configured": settings.storage_provider == "local"
                or bool(
                    settings.s3_endpoint_url
                    and settings.s3_bucket
                    and settings.s3_access_key_id
                    and settings.s3_secret_access_key
                ),
            },
        },
    }


@router.get("/companies", response_model=list[CompanyOut])
def list_admin_companies(db: Session = Depends(get_db)) -> list[Company]:
    return list(db.scalars(select(Company).order_by(Company.name)).all())


@router.post("/companies", response_model=CompanyOut, status_code=status.HTTP_201_CREATED)
def create_admin_company(payload: CompanyCreate, db: Session = Depends(get_db)) -> Company:
    if db.scalar(select(Company).where(Company.name == payload.name)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una empresa con ese nombre.")
    company = Company(**payload.model_dump(), approval_status="APPROVED", approved_at=utc_now())
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


@router.patch("/companies/{company_id}", response_model=CompanyOut)
def update_admin_company(company_id: int, payload: CompanyUpdate, db: Session = Depends(get_db)) -> Company:
    company = _get_company(db, company_id)
    values = payload.model_dump(exclude_unset=True)
    if "name" in values and values["name"] != company.name:
        if db.scalar(select(Company).where(Company.name == values["name"], Company.id != company.id)) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una empresa con ese nombre.")
    _apply_values(company, values)
    db.commit()
    db.refresh(company)
    return company


@router.post("/companies/{company_id}/activate", response_model=CompanyOut)
def activate_admin_company(company_id: int, db: Session = Depends(get_db)) -> Company:
    company = _get_company(db, company_id)
    company.is_active = True
    company.approval_status = "APPROVED"
    company.approved_at = utc_now()
    company.rejection_reason = None
    db.commit()
    db.refresh(company)
    return company


@router.post("/companies/{company_id}/deactivate", response_model=CompanyOut)
def deactivate_admin_company(company_id: int, db: Session = Depends(get_db)) -> Company:
    company = _get_company(db, company_id)
    company.is_active = False
    company.approval_status = "NEEDS_INFO"
    db.commit()
    db.refresh(company)
    return company


@router.get("/storage-units", response_model=list[StorageUnitOut])
def list_admin_storage_units(company_id: int | None = None, db: Session = Depends(get_db)) -> list[StorageUnit]:
    stmt = select(StorageUnit)
    if company_id is not None:
        stmt = stmt.where(StorageUnit.company_id == company_id)
    return list(db.scalars(stmt.order_by(StorageUnit.name)).all())


@router.post("/storage-units", response_model=StorageUnitOut, status_code=status.HTTP_201_CREATED)
def create_admin_storage_unit(payload: StorageUnitCreate, db: Session = Depends(get_db)) -> StorageUnit:
    company = _get_company(db, payload.company_id)
    _require_active_company(company)
    site = _get_site(db, payload.site_id)
    if site.company_id != company.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El sitio no pertenece a la empresa seleccionada.")
    _validate_assignees(db, payload.company_id, payload.assigned_technician_id, payload.assigned_client_id)
    unit = StorageUnit(**payload.model_dump())
    db.add(unit)
    db.commit()
    db.refresh(unit)
    return unit


@router.patch("/storage-units/{storage_unit_id}", response_model=StorageUnitOut)
def update_admin_storage_unit(
    storage_unit_id: int,
    payload: StorageUnitUpdate,
    db: Session = Depends(get_db),
) -> StorageUnit:
    unit = _get_storage_unit(db, storage_unit_id)
    values = payload.model_dump(exclude_unset=True)
    company_id = values.get("company_id", unit.company_id)
    site_id = values.get("site_id", unit.site_id)
    company = _get_company(db, company_id)
    site = _get_site(db, site_id)
    if site.company_id != company.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El sitio no pertenece a la empresa seleccionada.")
    _validate_assignees(
        db,
        company_id,
        values.get("assigned_technician_id", unit.assigned_technician_id),
        values.get("assigned_client_id", unit.assigned_client_id),
    )
    _apply_values(unit, values)
    db.commit()
    db.refresh(unit)
    return unit


@router.post("/storage-units/{storage_unit_id}/activate", response_model=StorageUnitOut)
def activate_admin_storage_unit(storage_unit_id: int, db: Session = Depends(get_db)) -> StorageUnit:
    unit = _get_storage_unit(db, storage_unit_id)
    unit.is_active = True
    db.commit()
    db.refresh(unit)
    return unit


@router.post("/storage-units/{storage_unit_id}/deactivate", response_model=StorageUnitOut)
def deactivate_admin_storage_unit(storage_unit_id: int, db: Session = Depends(get_db)) -> StorageUnit:
    unit = _get_storage_unit(db, storage_unit_id)
    unit.is_active = False
    db.commit()
    db.refresh(unit)
    return unit


@router.get("/devices", response_model=list[DeviceOut])
def list_admin_devices(storage_unit_id: int | None = None, db: Session = Depends(get_db)) -> list[Device]:
    stmt = select(Device)
    if storage_unit_id is not None:
        stmt = stmt.where(Device.storage_unit_id == storage_unit_id)
    return list(db.scalars(stmt.order_by(Device.external_id)).all())


@router.post("/devices", response_model=AdminDeviceSecretOut, status_code=status.HTTP_201_CREATED)
def create_admin_device(payload: AdminDeviceCreate, db: Session = Depends(get_db)) -> Device:
    unit = _get_storage_unit(db, payload.storage_unit_id)
    _require_active_storage_unit(unit)
    if db.scalar(select(Device).where(Device.external_id == payload.external_id)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un sensor con ese device_id.")
    api_key = _new_sensor_api_key()
    device = Device(
        company_id=unit.company_id,
        site_id=unit.site_id,
        storage_unit_id=unit.id,
        external_id=payload.external_id,
        name=payload.name,
        device_type=payload.device_type,
        token_hash=hash_secret(api_key),
        is_active=payload.is_active,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    setattr(device, "api_key", api_key)
    return device


@router.patch("/devices/{device_id}", response_model=DeviceOut)
def update_admin_device(device_id: int, payload: AdminDeviceUpdate, db: Session = Depends(get_db)) -> Device:
    device = _get_device(db, device_id)
    values = payload.model_dump(exclude_unset=True)
    if "external_id" in values and values["external_id"] != device.external_id:
        if db.scalar(select(Device).where(Device.external_id == values["external_id"], Device.id != device.id)) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un sensor con ese device_id.")
    if "storage_unit_id" in values:
        unit = _get_storage_unit(db, values["storage_unit_id"])
        device.company_id = unit.company_id
        device.site_id = unit.site_id
        device.storage_unit_id = unit.id
        values.pop("storage_unit_id")
    _apply_values(device, values)
    db.commit()
    db.refresh(device)
    return device


@router.post("/devices/{device_id}/reset-api-key", response_model=AdminDeviceSecretOut)
def reset_admin_device_api_key(device_id: int, db: Session = Depends(get_db)) -> Device:
    device = _get_device(db, device_id)
    api_key = _new_sensor_api_key()
    device.token_hash = hash_secret(api_key)
    device.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(device)
    setattr(device, "api_key", api_key)
    return device


@router.post("/devices/{device_id}/activate", response_model=DeviceOut)
def activate_admin_device(device_id: int, db: Session = Depends(get_db)) -> Device:
    device = _get_device(db, device_id)
    device.is_active = True
    db.commit()
    db.refresh(device)
    return device


@router.post("/devices/{device_id}/deactivate", response_model=DeviceOut)
def deactivate_admin_device(device_id: int, db: Session = Depends(get_db)) -> Device:
    device = _get_device(db, device_id)
    device.is_active = False
    db.commit()
    db.refresh(device)
    return device


@router.get("/users", response_model=list[UserOut])
def list_admin_users(
    role: str | None = None,
    db: Session = Depends(get_db),
) -> list[User]:
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    return list(db.scalars(stmt.order_by(User.full_name)).all())


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_admin_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User).where(User.email == payload.email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    _validate_user_payload(db, payload.role, payload.company_id, payload.storage_unit_ids)
    user = User(
        company_id=payload.company_id,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
        status="ACTIVE",
        locale="es",
        phone_whatsapp=payload.phone_whatsapp,
        telegram_chat_id=payload.telegram_chat_id,
        receives_alerts=payload.receives_alerts,
    )
    db.add(user)
    db.flush()
    _sync_user_assignments(db, user, payload.storage_unit_ids)
    _sync_user_notification_preferences(db, user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_admin_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)) -> User:
    user = _get_user(db, user_id)
    values = payload.model_dump(exclude_unset=True)
    new_role = values.get("role", user.role)
    new_company_id = values.get("company_id", user.company_id)
    current_unit_ids = _current_user_unit_ids(db, user)
    _validate_user_payload(db, new_role, new_company_id, current_unit_ids, allow_empty_assignment=True)
    if "email" in values and values["email"] != user.email:
        if db.scalar(select(User).where(User.email == values["email"], User.id != user.id)) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    _apply_values(user, values)
    _sync_user_notification_preferences(db, user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password", response_model=UserOut)
def reset_admin_user_password(user_id: int, payload: PasswordResetIn, db: Session = Depends(get_db)) -> User:
    user = _get_user(db, user_id)
    user.hashed_password = hash_password(payload.password)
    user.password_changed_at = utc_now()
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/activate", response_model=UserOut)
def activate_admin_user(user_id: int, db: Session = Depends(get_db)) -> User:
    user = _get_user(db, user_id)
    user.is_active = True
    user.status = "ACTIVE"
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/deactivate", response_model=UserOut)
def deactivate_admin_user(user_id: int, db: Session = Depends(get_db)) -> User:
    user = _get_user(db, user_id)
    user.is_active = False
    user.status = "INACTIVE"
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/assign-storage-units", response_model=UserOut)
def assign_admin_user_storage_units(
    user_id: int,
    payload: UserStorageUnitAssignmentsIn,
    db: Session = Depends(get_db),
) -> User:
    user = _get_user(db, user_id)
    _validate_user_payload(db, user.role, user.company_id, payload.storage_unit_ids)
    _sync_user_assignments(db, user, payload.storage_unit_ids)
    db.commit()
    db.refresh(user)
    return user


@router.get("/technicians", response_model=list[UserOut])
def list_admin_technicians(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).where(User.role == "technician").order_by(User.full_name)).all())


@router.get("/clients", response_model=list[UserOut])
def list_admin_clients(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).where(User.role == "client").order_by(User.full_name)).all())


@router.get("/notifications/deliveries", response_model=list[NotificationDeliveryOut])
def list_notification_deliveries(db: Session = Depends(get_db)) -> list[NotificationDelivery]:
    stmt = select(NotificationDelivery).order_by(NotificationDelivery.created_at.desc()).limit(200)
    return list(db.scalars(stmt).all())


@router.post("/notifications/test/{channel}", response_model=NotificationDeliveryOut)
def test_admin_notification_channel(
    channel: str,
    payload: AdminNotificationTestIn,
    db: Session = Depends(get_db),
) -> NotificationDelivery:
    user = db.get(User, payload.user_id) if payload.user_id is not None else None
    unit = db.get(StorageUnit, payload.storage_unit_id) if payload.storage_unit_id is not None else None
    if payload.user_id is not None and user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if payload.storage_unit_id is not None and unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage unit not found")
    try:
        return create_admin_test_delivery(
            db,
            user=user,
            channel=channel,
            destination=payload.destination,
            message=_notification_test_message(payload, unit),
            severity=payload.severity,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _get_company(db: Session, company_id: int) -> Company:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


def _get_site(db: Session, site_id: int) -> Site:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    return site


def _get_storage_unit(db: Session, storage_unit_id: int) -> StorageUnit:
    unit = db.get(StorageUnit, storage_unit_id)
    if unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage unit not found")
    return unit


def _get_device(db: Session, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    return device


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _apply_values(model, values: dict) -> None:
    for key, value in values.items():
        setattr(model, key, value)


def _require_active_company(company: Company) -> None:
    if not company.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La empresa esta inactiva.")


def _require_active_storage_unit(unit: StorageUnit) -> None:
    if not unit.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El silo/galpon esta inactivo.")


def _validate_assignees(
    db: Session,
    company_id: int,
    technician_id: int | None,
    client_id: int | None,
) -> None:
    if technician_id is not None:
        technician = _get_user(db, technician_id)
        if technician.role != "technician":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El responsable tecnico debe tener rol technician.")
    if client_id is not None:
        client = _get_user(db, client_id)
        if client.role != "client":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El usuario cliente debe tener rol client.")
        if client.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El cliente pertenece a otra empresa.")


def _validate_user_payload(
    db: Session,
    role: str,
    company_id: int | None,
    storage_unit_ids: list[int],
    *,
    allow_empty_assignment: bool = False,
) -> None:
    if role not in {"admin", "technician", "client"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rol invalido.")
    if role == "client" and company_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Un cliente debe tener empresa asignada.")
    if company_id is not None:
        _get_company(db, company_id)
    if role in {"client", "technician"} and not storage_unit_ids and not allow_empty_assignment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Asigna al menos un silo/galpon al usuario.")
    if storage_unit_ids:
        units = list(db.scalars(select(StorageUnit).where(StorageUnit.id.in_(storage_unit_ids))).all())
        if len(units) != len(set(storage_unit_ids)):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage unit not found")
        if role == "client" and any(unit.company_id != company_id for unit in units):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="El cliente no puede asignarse a silos de otra empresa.")


def _sync_user_assignments(db: Session, user: User, storage_unit_ids: list[int]) -> None:
    if user.role == "technician":
        for current in db.scalars(select(StorageUnit).where(StorageUnit.assigned_technician_id == user.id)).all():
            current.assigned_technician_id = None
        db.flush()
        for unit in db.scalars(select(StorageUnit).where(StorageUnit.id.in_(storage_unit_ids))).all():
            unit.assigned_technician_id = user.id
    elif user.role == "client":
        for current in db.scalars(select(StorageUnit).where(StorageUnit.assigned_client_id == user.id)).all():
            current.assigned_client_id = None
        db.flush()
        for unit in db.scalars(select(StorageUnit).where(StorageUnit.id.in_(storage_unit_ids))).all():
            unit.assigned_client_id = user.id


def _current_user_unit_ids(db: Session, user: User) -> list[int]:
    if user.role == "technician":
        stmt = select(StorageUnit.id).where(StorageUnit.assigned_technician_id == user.id)
    elif user.role == "client":
        stmt = select(StorageUnit.id).where(StorageUnit.assigned_client_id == user.id)
    else:
        return []
    return list(db.scalars(stmt).all())


def _sync_user_notification_preferences(db: Session, user: User) -> None:
    if user.company_id is None:
        return
    channels = [
        ("whatsapp", user.phone_whatsapp),
        ("telegram", user.telegram_chat_id),
    ]
    for channel, destination in channels:
        upsert_preference(
            db,
            user,
            channel=channel,
            enabled=bool(user.receives_alerts and destination),
            destination=destination,
            minimum_severity="critical",
        )


def _notification_test_message(payload: AdminNotificationTestIn, unit: StorageUnit | None) -> str:
    unit_label = f"\nSilo/galpon: {unit.name}" if unit is not None else ""
    return f"{payload.message}\nNivel: {payload.severity.upper()}{unit_label}"


def _new_sensor_api_key() -> str:
    return f"agro_{token_urlsafe(24)}"
