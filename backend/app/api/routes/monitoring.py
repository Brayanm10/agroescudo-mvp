from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas import MonitoringSummaryOut
from app.services.monitoring import build_monitoring_summary

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/monitoring/summary", response_model=MonitoringSummaryOut)
def monitoring_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonitoringSummaryOut:
    return build_monitoring_summary(db, current_user)
