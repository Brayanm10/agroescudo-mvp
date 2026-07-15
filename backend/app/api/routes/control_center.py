from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas import ControlCenterSummaryOut
from app.services.control_center import build_control_center_summary

router = APIRouter()


@router.get("/control-center/summary", response_model=ControlCenterSummaryOut)
def control_center_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ControlCenterSummaryOut:
    return build_control_center_summary(db, current_user)
