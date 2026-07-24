import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models import InstallationChecklist, StorageUnit, User, utc_now
from app.schemas import (
    InstallationCreate,
    InstallationOut,
    InstallationUpdate,
    InstallationValidateIn,
)
from app.services.audit import record_audit_event
from app.services.installations import (
    FINAL_INSTALLATION_STATUSES,
    installation_out,
    list_installations,
    require_installation_access,
    validate_installation,
    verify_installation_references,
)

router = APIRouter(prefix="/installations", dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[InstallationOut])
def get_installations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[InstallationOut]:
    return [installation_out(item, current_user) for item in list_installations(db, current_user)]


@router.post("", response_model=InstallationOut, status_code=status.HTTP_201_CREATED)
def create_installation(
    payload: InstallationCreate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> InstallationOut:
    device = verify_installation_references(
        db,
        current_user,
        device_id=payload.device_id,
        first_reading_id=payload.first_reading_id,
        test_alert_id=payload.test_alert_id,
    )
    if payload.technician_id is not None:
        _validate_technician_assignment(db, device.storage_unit_id, payload.technician_id)
    checklist = InstallationChecklist(
        company_id=device.company_id,
        storage_unit_id=device.storage_unit_id,
        device_id=device.id,
        technician_id=payload.technician_id,
        status="IN_PROGRESS" if payload.responses else "DRAFT",
        started_at=utc_now() if payload.responses else None,
        checklist_version=payload.checklist_version,
        responses_json=json.dumps(payload.responses, ensure_ascii=True),
        first_reading_id=payload.first_reading_id,
        test_alert_id=payload.test_alert_id,
        notes=payload.notes,
        next_review_at=payload.next_review_at,
        created_by_id=current_user.id,
    )
    db.add(checklist)
    db.flush()
    record_audit_event(
        db,
        action="installation.create",
        summary="Checklist de instalacion creado",
        user=current_user,
        resource_type="installation",
        resource_id=checklist.id,
        metadata={"device_id": device.id, "technician_id": payload.technician_id},
    )
    db.commit()
    db.refresh(checklist)
    return installation_out(checklist, current_user)


@router.get("/{installation_id}", response_model=InstallationOut)
def get_installation(
    installation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InstallationOut:
    return installation_out(require_installation_access(db, current_user, installation_id), current_user)


@router.patch("/{installation_id}", response_model=InstallationOut)
def update_installation(
    installation_id: int,
    payload: InstallationUpdate,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> InstallationOut:
    checklist = require_installation_access(db, current_user, installation_id)
    if checklist.status in FINAL_INSTALLATION_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El checklist finalizado es inmutable. Registra una nueva revision.",
        )
    values = payload.model_dump(exclude_unset=True)
    technician_id = values.get("technician_id")
    if technician_id is not None:
        if current_user.role != "admin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo admin puede reasignar.")
        _validate_technician_assignment(db, checklist.storage_unit_id, technician_id)
    if "first_reading_id" in values or "test_alert_id" in values:
        verify_installation_references(
            db,
            current_user,
            device_id=checklist.device_id,
            first_reading_id=values.get("first_reading_id", checklist.first_reading_id),
            test_alert_id=values.get("test_alert_id", checklist.test_alert_id),
        )
    if "responses" in values:
        checklist.responses_json = json.dumps(values.pop("responses") or {}, ensure_ascii=True)
        checklist.started_at = checklist.started_at or utc_now()
        checklist.status = "IN_PROGRESS"
    for key, value in values.items():
        setattr(checklist, key, value)
    record_audit_event(
        db,
        action="installation.update",
        summary="Checklist de instalacion actualizado",
        user=current_user,
        resource_type="installation",
        resource_id=checklist.id,
    )
    db.commit()
    db.refresh(checklist)
    return installation_out(checklist, current_user)


@router.post("/{installation_id}/validate", response_model=InstallationOut)
def validate_installation_endpoint(
    installation_id: int,
    payload: InstallationValidateIn,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> InstallationOut:
    checklist = require_installation_access(db, current_user, installation_id)
    if checklist.status in FINAL_INSTALLATION_STATUSES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El checklist ya fue finalizado.")
    validate_installation(db, checklist, current_user, payload.final_status)
    db.commit()
    db.refresh(checklist)
    return installation_out(checklist, current_user)


def _validate_technician_assignment(db: Session, storage_unit_id: int, technician_id: int) -> None:
    technician = db.get(User, technician_id)
    unit = db.get(StorageUnit, storage_unit_id)
    if technician is None or technician.role != "technician" or not technician.is_active:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Tecnico invalido.")
    if unit is None or unit.assigned_technician_id != technician.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="El tecnico debe estar asignado al silo o campo.",
        )
