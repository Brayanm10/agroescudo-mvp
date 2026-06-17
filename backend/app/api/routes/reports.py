from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_storage_unit_access
from app.db.session import get_db
from app.models import User
from app.schemas import WeeklyReportOut
from app.services.pdf_reports import build_weekly_pdf, pdf_filename
from app.services.reports import build_weekly_report

router = APIRouter(prefix="/reports", dependencies=[Depends(get_current_user)])


@router.get("/weekly", response_model=WeeklyReportOut)
def weekly_report(
    storage_unit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WeeklyReportOut:
    storage_unit = require_storage_unit_access(db, current_user, storage_unit_id)
    storage_unit.last_report_generated_at = datetime.now(timezone.utc)
    db.commit()
    report = build_weekly_report(db, storage_unit_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Storage unit not found")
    return report


@router.get("/weekly/pdf")
def weekly_report_pdf(
    storage_unit_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    storage_unit = require_storage_unit_access(db, current_user, storage_unit_id)
    storage_unit.last_report_generated_at = datetime.now(timezone.utc)
    db.commit()
    report = build_weekly_report(db, storage_unit_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Storage unit not found")
    content = build_weekly_pdf(db, storage_unit, report)
    filename = pdf_filename(storage_unit.name, report.date_to)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
