from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_alert_access
from app.db.session import get_db
from app.models import User
from app.schemas import AiAlertRecommendationOut
from app.services.ai_recommendations import build_alert_recommendation

router = APIRouter(prefix="/ai", dependencies=[Depends(get_current_user)])


@router.get("/alerts/{alert_id}/recommendation", response_model=AiAlertRecommendationOut)
def get_alert_recommendation(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AiAlertRecommendationOut:
    alert = require_alert_access(db, current_user, alert_id)
    return build_alert_recommendation(db, alert)
