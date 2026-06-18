from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role, require_storage_unit_access, scope_storage_unit_records_query
from app.db.session import get_db
from app.models import Alert, Device, OperationalLog, User
from app.schemas import InstallationChecklistCreate, OperationalLogCreate, OperationalLogOut

router = APIRouter(prefix="/operational-logs", dependencies=[Depends(get_current_user)])


@router.post("", response_model=OperationalLogOut, status_code=status.HTTP_201_CREATED)
def create_operational_log(
    payload: OperationalLogCreate,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> OperationalLog:
    storage_unit = require_storage_unit_access(db, current_user, payload.storage_unit_id)
    if payload.device_id is not None:
        device = db.get(Device, payload.device_id)
        if device is None or device.storage_unit_id != storage_unit.id:
            raise HTTPException(status_code=404, detail="Device not found")
    if payload.alert_id is not None and (
        (alert := db.get(Alert, payload.alert_id)) is None
        or alert.storage_unit_id != storage_unit.id
    ):
        raise HTTPException(status_code=404, detail="Alert not found")

    log = OperationalLog(
        company_id=storage_unit.company_id,
        site_id=storage_unit.site_id,
        storage_unit_id=storage_unit.id,
        device_id=payload.device_id,
        alert_id=payload.alert_id,
        user_id=current_user.id,
        category=payload.category,
        action_taken=payload.action_taken,
        operator_name=payload.operator_name,
        notes=payload.notes,
        timestamp=payload.timestamp,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.post("/installations", response_model=OperationalLogOut, status_code=status.HTTP_201_CREATED)
def create_installation_checklist(
    payload: InstallationChecklistCreate,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> OperationalLog:
    storage_unit = require_storage_unit_access(db, current_user, payload.storage_unit_id)
    device = db.get(Device, payload.device_id)
    if device is None or device.storage_unit_id != storage_unit.id:
        raise HTTPException(status_code=404, detail="Device not found")

    checklist_notes = "\n".join(
        [
            f"Ubicacion fisica: {payload.physical_location}",
            f"Sensor instalado correctamente: {_yes_no(payload.sensor_installed_correctly)}",
            f"Conectividad verificada: {_yes_no(payload.connectivity_verified)}",
            f"Lectura inicial registrada: {_yes_no(payload.initial_reading_registered)}",
            f"Bateria verificada: {_yes_no(payload.battery_verified)}",
            f"Observaciones: {payload.observations or 'Sin observaciones adicionales.'}",
        ]
    )
    log = OperationalLog(
        company_id=storage_unit.company_id,
        site_id=storage_unit.site_id,
        storage_unit_id=storage_unit.id,
        device_id=device.id,
        user_id=current_user.id,
        category="installation",
        action_taken="Checklist de instalacion registrado",
        operator_name=payload.technician_name,
        notes=checklist_notes,
        timestamp=payload.timestamp,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


@router.get("", response_model=list[OperationalLogOut])
def list_operational_logs(
    storage_unit_id: int | None = None,
    alert_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OperationalLog]:
    stmt = scope_storage_unit_records_query(select(OperationalLog), OperationalLog, current_user, db)
    if storage_unit_id is not None:
        require_storage_unit_access(db, current_user, storage_unit_id)
        stmt = stmt.where(OperationalLog.storage_unit_id == storage_unit_id)
    if alert_id is not None:
        stmt = stmt.where(OperationalLog.alert_id == alert_id)
    return list(db.scalars(stmt.order_by(OperationalLog.timestamp.desc())).all())


def _yes_no(value: bool) -> str:
    return "Si" if value else "No"
