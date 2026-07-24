from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import assigned_storage_unit_ids, get_current_user, require_device_access, require_role, require_storage_unit_access
from app.db.session import get_db
from app.models import StorageUnit, User
from app.schemas import WeeklyReportOut
from app.services.pdf_reports import build_weekly_pdf, pdf_filename
from app.services.reports import build_weekly_report
from app.services.audit import record_audit_event
from app.services.p1_reports import (
    build_executive_report,
    build_technical_report,
    report_filename,
)

router = APIRouter(prefix="/reports", dependencies=[Depends(get_current_user)])


@router.get("/executive")
def executive_report_pdf(
    storage_unit_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    start, end = _report_period(date_from, date_to)
    units = _report_units(db, current_user, storage_unit_id)
    if not units:
        raise HTTPException(status_code=404, detail="No existen unidades autorizadas para el reporte.")
    content = build_executive_report(
        db,
        current_user,
        units,
        date_from=start,
        date_to=end,
        responsible=current_user.full_name,
    )
    _audit_report(db, current_user, "executive", units, start, end)
    filename = report_filename("ejecutivo", units, end)
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/technical")
def technical_report_pdf(
    storage_unit_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> Response:
    start, end = _report_period(date_from, date_to)
    units = _report_units(db, current_user, storage_unit_id)
    if not units:
        raise HTTPException(status_code=404, detail="No existen unidades autorizadas para el reporte.")
    content = build_technical_report(
        db,
        current_user,
        units,
        date_from=start,
        date_to=end,
        responsible=current_user.full_name,
    )
    _audit_report(db, current_user, "technical", units, start, end)
    filename = report_filename("tecnico", units, end)
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/weekly", response_model=WeeklyReportOut)
def weekly_report(
    storage_unit_id: int,
    device_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeeklyReportOut:
    storage_unit = require_storage_unit_access(db, current_user, storage_unit_id)
    if device_id is not None:
        device = require_device_access(db, current_user, device_id)
        if device.storage_unit_id != storage_unit_id:
            raise HTTPException(status_code=422, detail="El nodo no pertenece a la unidad seleccionada.")
    storage_unit.last_report_generated_at = datetime.now(timezone.utc)
    db.commit()
    report = build_weekly_report(db, storage_unit_id, device_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Storage unit not found")
    return report


@router.get("/weekly/pdf")
def weekly_report_pdf(
    storage_unit_id: int,
    device_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    storage_unit = require_storage_unit_access(db, current_user, storage_unit_id)
    if device_id is not None:
        device = require_device_access(db, current_user, device_id)
        if device.storage_unit_id != storage_unit_id:
            raise HTTPException(status_code=422, detail="El nodo no pertenece a la unidad seleccionada.")
    storage_unit.last_report_generated_at = datetime.now(timezone.utc)
    db.commit()
    report = build_weekly_report(db, storage_unit_id, device_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Storage unit not found")
    content = build_weekly_pdf(db, storage_unit, report, device_id=device_id)
    filename = pdf_filename(storage_unit.name, report.date_to)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _report_period(date_from: datetime | None, date_to: datetime | None) -> tuple[datetime, datetime]:
    end = date_to or datetime.now(timezone.utc)
    start = date_from or end - timedelta(days=7)
    if start >= end:
        raise HTTPException(status_code=422, detail="El inicio del periodo debe ser anterior al fin.")
    return start, end


def _report_units(db: Session, user: User, storage_unit_id: int | None) -> list[StorageUnit]:
    if storage_unit_id is not None:
        return [require_storage_unit_access(db, user, storage_unit_id)]
    ids = assigned_storage_unit_ids(db, user)
    return list(db.scalars(select(StorageUnit).where(StorageUnit.id.in_(ids)).order_by(StorageUnit.name)).all()) if ids else []


def _audit_report(db, user, kind, units, start, end):
    record_audit_event(
        db,
        action=f"report.{kind}",
        summary=f"Reporte {kind} generado.",
        user=user,
        resource_type="report",
        metadata={"storage_unit_ids": [item.id for item in units], "from": start.isoformat(), "to": end.isoformat()},
    )
    for unit in units:
        unit.last_report_generated_at = datetime.now(timezone.utc)
    db.commit()
