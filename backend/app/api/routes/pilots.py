from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role, require_storage_unit_access, scope_company_query
from app.core.security import hash_password, hash_secret
from app.db.session import get_db
from app.models import Alert, Company, Device, OperationalLog, SensorReading, Site, StorageUnit, ThresholdConfig, User
from app.schemas import OperationalDataDeleteOut, PilotAssignmentsIn, PilotCreate, PilotOut
from app.services.pilots import build_pilot_summary

router = APIRouter(prefix="/pilots", dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[PilotOut])
def list_pilots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PilotOut]:
    stmt = scope_company_query(select(StorageUnit), StorageUnit, current_user)
    storage_units = db.scalars(stmt.order_by(StorageUnit.created_at.desc())).all()
    return [build_pilot_summary(db, storage_unit) for storage_unit in storage_units]


@router.get("/{storage_unit_id}", response_model=PilotOut)
def get_pilot(
    storage_unit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PilotOut:
    storage_unit = require_storage_unit_access(db, current_user, storage_unit_id)
    return build_pilot_summary(db, storage_unit)


@router.post("", response_model=PilotOut, status_code=status.HTTP_201_CREATED)
def create_pilot(
    payload: PilotCreate,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> PilotOut:
    technician = _get_role_user(db, payload.technician_user_id, "technician", "Technician not found")
    company = db.scalar(select(Company).where(Company.name == payload.company_name))
    if company is None:
        company = Company(name=payload.company_name, tax_id=payload.company_tax_id)
        db.add(company)
        db.flush()

    site = db.scalar(
        select(Site).where(
            Site.company_id == company.id,
            Site.name == payload.site_name,
        )
    )
    if site is None:
        site = Site(company_id=company.id, name=payload.site_name, location=payload.site_location)
        db.add(site)
        db.flush()

    client = db.scalar(select(User).where(User.email == payload.client_email))
    if client is None:
        client = User(
            company_id=company.id,
            email=payload.client_email,
            full_name=payload.client_full_name,
            hashed_password=hash_password(payload.client_password),
            role="client",
            is_active=True,
        )
        db.add(client)
        db.flush()
    else:
        client.company_id = company.id
        client.full_name = payload.client_full_name
        client.hashed_password = hash_password(payload.client_password)
        client.role = "client"
        client.is_active = True

    storage_unit = db.scalar(
        select(StorageUnit).where(
            StorageUnit.site_id == site.id,
            StorageUnit.name == payload.storage_unit_name,
        )
    )
    if storage_unit is None:
        storage_unit = StorageUnit(
            company_id=company.id,
            site_id=site.id,
            name=payload.storage_unit_name,
            unit_type=payload.storage_unit_type,
            capacity_tons=payload.capacity_tons,
        )
        db.add(storage_unit)
        db.flush()
    storage_unit.assigned_technician_id = technician.id
    storage_unit.assigned_client_id = client.id

    device = db.scalar(select(Device).where(Device.external_id == payload.device_external_id))
    if device is not None and device.storage_unit_id != storage_unit.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Device external ID already assigned")
    if device is None:
        device = Device(
            company_id=company.id,
            site_id=site.id,
            storage_unit_id=storage_unit.id,
            external_id=payload.device_external_id,
            name=payload.device_name,
            token_hash=hash_secret(payload.device_token),
            is_active=True,
        )
        db.add(device)
    else:
        device.name = payload.device_name
        device.token_hash = hash_secret(payload.device_token)
        device.is_active = True

    _ensure_default_thresholds(db, company.id, storage_unit.id)
    db.commit()
    db.refresh(storage_unit)
    return build_pilot_summary(db, storage_unit)


@router.patch("/{storage_unit_id}/assignments", response_model=PilotOut)
def update_pilot_assignments(
    storage_unit_id: int,
    payload: PilotAssignmentsIn,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> PilotOut:
    storage_unit = db.get(StorageUnit, storage_unit_id)
    if storage_unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage unit not found")
    if payload.technician_user_id is not None:
        technician = _get_role_user(db, payload.technician_user_id, "technician", "Technician not found")
        storage_unit.assigned_technician_id = technician.id
    if payload.client_user_id is not None:
        client = _get_role_user(db, payload.client_user_id, "client", "Client user not found")
        if client.company_id != storage_unit.company_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client user belongs to another company")
        storage_unit.assigned_client_id = client.id
    db.commit()
    db.refresh(storage_unit)
    return build_pilot_summary(db, storage_unit)


@router.delete("/{storage_unit_id}/operational-data", response_model=OperationalDataDeleteOut)
def delete_pilot_operational_data(
    storage_unit_id: int,
    _: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> OperationalDataDeleteOut:
    storage_unit = db.get(StorageUnit, storage_unit_id)
    if storage_unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage unit not found")

    logs_deleted = db.execute(
        delete(OperationalLog).where(OperationalLog.storage_unit_id == storage_unit_id)
    ).rowcount
    alerts_deleted = db.execute(
        delete(Alert).where(Alert.storage_unit_id == storage_unit_id)
    ).rowcount
    readings_deleted = db.execute(
        delete(SensorReading).where(SensorReading.storage_unit_id == storage_unit_id)
    ).rowcount
    storage_unit.last_report_generated_at = None
    db.commit()
    return OperationalDataDeleteOut(
        storage_unit_id=storage_unit_id,
        readings_deleted=readings_deleted or 0,
        alerts_deleted=alerts_deleted or 0,
        logs_deleted=logs_deleted or 0,
    )


def _get_role_user(db: Session, user_id: int, role: str, detail: str) -> User:
    user = db.get(User, user_id)
    if user is None or user.role != role or not user.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return user


def _ensure_default_thresholds(db: Session, company_id: int, storage_unit_id: int) -> None:
    defaults = [
        ("grain_temperature", ">", 30.0, "warning"),
        ("ambient_humidity", ">", 70.0, "warning"),
        ("battery_voltage", "<", 3.5, "technical"),
        ("critical_temperature", ">", 32.0, "critical"),
        ("critical_humidity", ">", 75.0, "critical"),
    ]
    for metric, operator, value, severity in defaults:
        exists = db.scalar(
            select(ThresholdConfig).where(
                ThresholdConfig.company_id == company_id,
                ThresholdConfig.storage_unit_id == storage_unit_id,
                ThresholdConfig.metric == metric,
            )
        )
        if exists is None:
            db.add(
                ThresholdConfig(
                    company_id=company_id,
                    storage_unit_id=storage_unit_id,
                    metric=metric,
                    operator=operator,
                    value=value,
                    severity=severity,
                )
            )
