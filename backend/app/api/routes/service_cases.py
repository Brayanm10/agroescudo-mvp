from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role, require_storage_unit_access
from app.db.session import get_db
from app.models import MaintenanceReport, MaintenanceReportPhoto, MaintenanceSignature, ServiceCase, ServiceCaseEvent, User, utc_now
from app.schemas import (
    MaintenanceReportCreate,
    MaintenanceReportOut,
    MaintenanceSignatureIn,
    MaintenanceSignatureOut,
    ServiceCaseCreate,
    ServiceCaseEventCreate,
    ServiceCaseEventOut,
    ServiceCaseOut,
    ServiceCaseUpdate,
    StoredFileOut,
)
from app.services.audit import record_audit_event
from app.services.storage import StorageConfigurationError, store_upload

router = APIRouter()


def _require_case_access(db: Session, user: User, case_id: int) -> ServiceCase:
    service_case = db.get(ServiceCase, case_id)
    if service_case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Caso no encontrado.")
    require_storage_unit_access(db, user, service_case.storage_unit_id)
    return service_case


@router.get("/service-cases", response_model=list[ServiceCaseOut])
def list_service_cases(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ServiceCase]:
    from app.api.deps import assigned_storage_unit_ids

    stmt = select(ServiceCase).order_by(ServiceCase.created_at.desc())
    if current_user.role != "admin":
        unit_ids = assigned_storage_unit_ids(db, current_user)
        stmt = stmt.where(ServiceCase.storage_unit_id.in_(unit_ids or [-1]))
    return list(db.scalars(stmt).all())


@router.post("/service-cases", response_model=ServiceCaseOut, status_code=status.HTTP_201_CREATED)
def create_service_case(
    payload: ServiceCaseCreate,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> ServiceCase:
    storage_unit = require_storage_unit_access(db, current_user, payload.storage_unit_id)
    service_case = ServiceCase(
        company_id=storage_unit.company_id,
        site_id=storage_unit.site_id,
        storage_unit_id=storage_unit.id,
        device_id=payload.device_id,
        alert_id=payload.alert_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        status="assigned" if payload.assigned_technician_id else "open",
        assigned_technician_id=payload.assigned_technician_id,
        opened_by_id=current_user.id,
        due_at=payload.due_at,
    )
    db.add(service_case)
    db.flush()
    db.add(ServiceCaseEvent(service_case_id=service_case.id, user_id=current_user.id, event_type="created", note="Caso creado."))
    record_audit_event(db, action="service_case.create", summary="Caso de servicio creado", user=current_user, resource_type="service_case", resource_id=service_case.id)
    db.commit()
    db.refresh(service_case)
    return service_case


@router.get("/service-cases/{case_id}", response_model=ServiceCaseOut)
def get_service_case(case_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ServiceCase:
    return _require_case_access(db, current_user, case_id)


@router.patch("/service-cases/{case_id}", response_model=ServiceCaseOut)
def update_service_case(
    case_id: int,
    payload: ServiceCaseUpdate,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> ServiceCase:
    service_case = _require_case_access(db, current_user, case_id)
    values = payload.model_dump(exclude_unset=True)
    for key, value in values.items():
        setattr(service_case, key, value)
    if payload.status in {"resolved", "closed", "cancelled"} and service_case.closed_at is None:
        service_case.closed_at = utc_now()
    db.add(ServiceCaseEvent(service_case_id=service_case.id, user_id=current_user.id, event_type="updated", note="Caso actualizado."))
    record_audit_event(db, action="service_case.update", summary="Caso de servicio actualizado", user=current_user, resource_type="service_case", resource_id=service_case.id, metadata=values)
    db.commit()
    db.refresh(service_case)
    return service_case


@router.post("/service-cases/{case_id}/events", response_model=ServiceCaseEventOut, status_code=status.HTTP_201_CREATED)
def create_case_event(
    case_id: int,
    payload: ServiceCaseEventCreate,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> ServiceCaseEvent:
    service_case = _require_case_access(db, current_user, case_id)
    event = ServiceCaseEvent(service_case_id=service_case.id, user_id=current_user.id, event_type=payload.event_type, note=payload.note)
    db.add(event)
    record_audit_event(db, action="service_case.event", summary="Evento de caso registrado", user=current_user, resource_type="service_case", resource_id=service_case.id)
    db.commit()
    db.refresh(event)
    return event


@router.post("/service-cases/{case_id}/maintenance-reports", response_model=MaintenanceReportOut, status_code=status.HTTP_201_CREATED)
def create_maintenance_report(
    case_id: int,
    payload: MaintenanceReportCreate,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> MaintenanceReport:
    service_case = _require_case_access(db, current_user, case_id)
    report = MaintenanceReport(
        service_case_id=service_case.id,
        storage_unit_id=service_case.storage_unit_id,
        technician_user_id=current_user.id,
        summary=payload.summary,
        actions_performed=payload.actions_performed,
        recommendations=payload.recommendations,
        status=payload.status,
        completed_at=utc_now() if payload.status == "completed" else None,
    )
    db.add(report)
    record_audit_event(db, action="maintenance_report.create", summary="Reporte de mantenimiento creado", user=current_user, resource_type="service_case", resource_id=service_case.id)
    db.commit()
    db.refresh(report)
    return report


@router.post("/service-cases/{case_id}/photos", response_model=StoredFileOut, status_code=status.HTTP_201_CREATED)
async def upload_case_photo(
    case_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> StoredFileOut:
    _require_case_access(db, current_user, case_id)
    try:
        stored = await store_upload(db, file=file, user=current_user, prefix=f"service-cases/{case_id}/photos")
    except StorageConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    record_audit_event(db, action="service_case.photo", summary="Foto de caso cargada", user=current_user, resource_type="service_case", resource_id=case_id, metadata={"file_id": stored.id})
    db.commit()
    return StoredFileOut.model_validate(stored)


@router.post("/service-cases/{case_id}/signature", response_model=MaintenanceSignatureOut, status_code=status.HTTP_201_CREATED)
def create_case_signature(
    case_id: int,
    payload: MaintenanceSignatureIn,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> MaintenanceSignature:
    service_case = _require_case_access(db, current_user, case_id)
    report = db.scalar(select(MaintenanceReport).where(MaintenanceReport.service_case_id == service_case.id).order_by(MaintenanceReport.created_at.desc()))
    if report is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Crea un reporte de mantenimiento antes de registrar firma.")
    signature = MaintenanceSignature(maintenance_report_id=report.id, signer_name=payload.signer_name, signer_role=payload.signer_role)
    db.add(signature)
    record_audit_event(db, action="maintenance_signature.create", summary="Firma de mantenimiento registrada", user=current_user, resource_type="maintenance_report", resource_id=report.id)
    db.commit()
    db.refresh(signature)
    return signature
