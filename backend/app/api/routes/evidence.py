from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    assigned_storage_unit_ids,
    get_current_user,
    require_role,
    require_storage_unit_access,
)
from app.db.session import get_db
from app.models import (
    Device,
    InstallationChecklist,
    MaintenanceRecord,
    ServiceCase,
    Site,
    StorageUnit,
    StoredFile,
    User,
    utc_now,
)
from app.schemas import EvidenceOut
from app.services.audit import record_audit_event
from app.services.maintenance import refresh_evidence_count
from app.services.storage import (
    InvalidUploadError,
    StorageConfigurationError,
    create_download_url,
    local_file_path,
    store_upload,
)

router = APIRouter(prefix="/evidence", dependencies=[Depends(get_current_user)])

ENTITY_TYPES = {"maintenance", "installation", "incident", "device", "site"}
FILE_TYPES = {"PHOTO", "DOCUMENT", "CHECKLIST", "SIGNATURE", "OTHER"}


@router.post("", response_model=EvidenceOut, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    storage_unit_id: int = Form(...),
    entity_type: str = Form(...),
    entity_id: int = Form(...),
    file_type: str = Form(default="PHOTO"),
    description: str | None = Form(default=None),
    captured_at: datetime | None = Form(default=None),
    is_sensitive: bool = Form(default=False),
    file: UploadFile = File(...),
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> EvidenceOut:
    unit = require_storage_unit_access(db, current_user, storage_unit_id)
    normalized_entity = entity_type.strip().lower()
    normalized_file_type = file_type.strip().upper()
    if normalized_entity not in ENTITY_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Entidad de evidencia invalida.")
    if normalized_file_type not in FILE_TYPES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Tipo de evidencia invalido.")
    _validate_entity_scope(db, storage_unit_id, normalized_entity, entity_id)
    try:
        stored = await store_upload(
            db,
            file=file,
            user=current_user,
            prefix=f"evidence/{unit.company_id}/{storage_unit_id}/{normalized_entity}",
            company_id=unit.company_id,
            storage_unit_id=storage_unit_id,
            entity_type=normalized_entity,
            entity_id=entity_id,
            file_type=normalized_file_type,
            description=description,
            captured_at=captured_at,
            is_sensitive=is_sensitive,
        )
    except InvalidUploadError as exc:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)) from exc
    except StorageConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if normalized_entity == "maintenance":
        record = db.get(MaintenanceRecord, entity_id)
        if record:
            refresh_evidence_count(db, record)
    record_audit_event(
        db,
        action="evidence.upload",
        summary="Evidencia cargada",
        user=current_user,
        resource_type=normalized_entity,
        resource_id=entity_id,
        metadata={"file_id": stored.id, "file_type": normalized_file_type},
    )
    db.commit()
    db.refresh(stored)
    return EvidenceOut.model_validate(stored)


@router.get("", response_model=list[EvidenceOut])
def list_evidence(
    storage_unit_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[StoredFile]:
    stmt = select(StoredFile).where(StoredFile.deleted_at.is_(None))
    if current_user.role != "admin":
        unit_ids = assigned_storage_unit_ids(db, current_user)
        stmt = stmt.where(StoredFile.storage_unit_id.in_(unit_ids or [-1]))
    if current_user.role == "client":
        stmt = stmt.where(StoredFile.is_sensitive.is_(False))
    if storage_unit_id is not None:
        require_storage_unit_access(db, current_user, storage_unit_id)
        stmt = stmt.where(StoredFile.storage_unit_id == storage_unit_id)
    if entity_type is not None:
        stmt = stmt.where(StoredFile.entity_type == entity_type.strip().lower())
    if entity_id is not None:
        stmt = stmt.where(StoredFile.entity_id == entity_id)
    return list(db.scalars(stmt.order_by(StoredFile.created_at.desc()).limit(250)).all())


@router.get("/{evidence_id}", response_model=EvidenceOut)
def get_evidence(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StoredFile:
    return _require_evidence_access(db, current_user, evidence_id)


@router.get("/{evidence_id}/download")
def download_evidence(
    evidence_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stored = _require_evidence_access(db, current_user, evidence_id)
    record_audit_event(
        db,
        action="evidence.download",
        summary="Evidencia descargada",
        user=current_user,
        resource_type=stored.entity_type,
        resource_id=stored.entity_id,
        metadata={"file_id": stored.id},
    )
    db.commit()
    if stored.storage_provider == "local":
        path = local_file_path(stored)
        if not path.is_file():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Archivo no disponible.")
        return FileResponse(
            path,
            media_type=stored.content_type,
            filename=stored.original_filename,
        )
    try:
        url = create_download_url(stored)
    except StorageConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    if not url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Archivo no disponible.")
    return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_evidence(
    evidence_id: int,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> None:
    stored = _require_evidence_access(db, current_user, evidence_id)
    if current_user.role == "technician" and stored.uploaded_by_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo puedes retirar evidencia propia.")
    stored.deleted_at = utc_now()
    if stored.entity_type == "maintenance" and stored.entity_id is not None:
        record = db.get(MaintenanceRecord, stored.entity_id)
        if record:
            refresh_evidence_count(db, record)
    record_audit_event(
        db,
        action="evidence.delete",
        summary="Evidencia retirada mediante borrado logico",
        user=current_user,
        resource_type=stored.entity_type,
        resource_id=stored.entity_id,
        metadata={"file_id": stored.id},
    )
    db.commit()


def _require_evidence_access(db: Session, user: User, evidence_id: int) -> StoredFile:
    stored = db.get(StoredFile, evidence_id)
    if stored is None or stored.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidencia no encontrada.")
    if stored.storage_unit_id is None:
        if user.role != "admin" and stored.company_id != user.company_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para esta evidencia.")
    else:
        require_storage_unit_access(db, user, stored.storage_unit_id)
    if user.role == "client" and stored.is_sensitive:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Evidencia tecnica restringida.")
    return stored


def _validate_entity_scope(db: Session, storage_unit_id: int, entity_type: str, entity_id: int) -> None:
    if entity_type == "maintenance":
        entity = db.get(MaintenanceRecord, entity_id)
        valid = entity is not None and entity.storage_unit_id == storage_unit_id
    elif entity_type == "installation":
        entity = db.get(InstallationChecklist, entity_id)
        valid = entity is not None and entity.storage_unit_id == storage_unit_id
    elif entity_type == "incident":
        entity = db.get(ServiceCase, entity_id)
        valid = entity is not None and entity.storage_unit_id == storage_unit_id
    elif entity_type == "device":
        entity = db.get(Device, entity_id)
        valid = entity is not None and entity.storage_unit_id == storage_unit_id
    else:
        entity = db.get(Site, entity_id)
        unit = db.get(StorageUnit, storage_unit_id)
        valid = entity is not None and unit is not None and entity.id == unit.site_id
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La evidencia no corresponde a la unidad autorizada.",
        )
