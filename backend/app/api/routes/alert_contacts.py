from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import assigned_storage_unit_ids, get_current_user, require_company_access, require_storage_unit_access
from app.db.session import get_db
from app.models import AlertContact, Company, StorageUnit, User
from app.schemas import AlertContactCreate, AlertContactOut, AlertContactTestIn, AlertContactUpdate, SentinelJobOut
from app.services.sentinel import create_test_job, normalize_phone_e164

router = APIRouter(prefix="/alert-contacts", dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[AlertContactOut])
def list_alert_contacts(
    company_id: int | None = None,
    storage_unit_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AlertContact]:
    stmt = select(AlertContact)
    if current_user.role != "admin":
        unit_ids = assigned_storage_unit_ids(db, current_user)
        stmt = stmt.where(
            AlertContact.company_id == current_user.company_id,
            (AlertContact.storage_unit_id.is_(None) | AlertContact.storage_unit_id.in_(unit_ids or [-1])),
        )
    if company_id is not None:
        require_company_access(db, current_user, company_id)
        stmt = stmt.where(AlertContact.company_id == company_id)
    if storage_unit_id is not None:
        require_storage_unit_access(db, current_user, storage_unit_id)
        stmt = stmt.where(
            (AlertContact.storage_unit_id == storage_unit_id) | AlertContact.storage_unit_id.is_(None)
        )
    return list(db.scalars(stmt.order_by(AlertContact.priority, AlertContact.name)).all())


@router.post("", response_model=AlertContactOut, status_code=status.HTTP_201_CREATED)
def create_alert_contact(
    payload: AlertContactCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertContact:
    _require_contact_editor(current_user)
    _validate_scope(db, current_user, payload.company_id, payload.storage_unit_id)
    try:
        phone_e164 = normalize_phone_e164(payload.phone_e164)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    contact = AlertContact(
        **payload.model_dump(exclude={"phone_e164"}),
        phone_e164=phone_e164,
        created_by_user_id=current_user.id,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.patch("/{contact_id}", response_model=AlertContactOut)
def update_alert_contact(
    contact_id: int,
    payload: AlertContactUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertContact:
    _require_contact_editor(current_user)
    contact = _get_contact(db, current_user, contact_id)
    values = payload.model_dump(exclude_unset=True)
    if "storage_unit_id" in values:
        _validate_scope(db, current_user, contact.company_id, values["storage_unit_id"])
    if values.get("phone_e164") is not None:
        try:
            values["phone_e164"] = normalize_phone_e164(values["phone_e164"])
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        contact.verified_at = None
    for key, value in values.items():
        setattr(contact, key, value)
    db.commit()
    db.refresh(contact)
    return contact


@router.post("/{contact_id}/test", response_model=SentinelJobOut, status_code=status.HTTP_201_CREATED)
def test_alert_contact(
    contact_id: int,
    payload: AlertContactTestIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    _require_contact_editor(current_user)
    contact = _get_contact(db, current_user, contact_id)
    if not contact.active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El contacto esta desactivado.")
    job = create_test_job(db, contact, payload.channel)
    db.commit()
    db.refresh(job)
    return _masked_job(job)


def _get_contact(db: Session, user: User, contact_id: int) -> AlertContact:
    contact = db.get(AlertContact, contact_id)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contacto no encontrado.")
    require_company_access(db, user, contact.company_id)
    if contact.storage_unit_id is not None:
        require_storage_unit_access(db, user, contact.storage_unit_id)
    return contact


def _validate_scope(db: Session, user: User, company_id: int, storage_unit_id: int | None) -> None:
    company = db.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Empresa no encontrada.")
    require_company_access(db, user, company_id)
    if storage_unit_id is not None:
        unit = db.get(StorageUnit, storage_unit_id)
        if unit is None or unit.company_id != company_id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="El silo no pertenece a la empresa.")
        require_storage_unit_access(db, user, storage_unit_id)


def _require_contact_editor(user: User) -> None:
    if user.role not in {"admin", "client"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para editar contactos.")


def _masked_job(job) -> dict:
    from app.services.sentinel import mask_phone

    return {
        column.name: (mask_phone(job.destination_phone) if column.name == "destination_phone" else getattr(job, column.name))
        for column in job.__table__.columns
        if column.name != "idempotency_key"
    }
