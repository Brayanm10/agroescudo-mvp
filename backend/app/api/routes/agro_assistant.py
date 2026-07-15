from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import User
from app.schemas import AgroAssistantMessageIn, AgroAssistantMessageOut
from app.services.agro_assistant import answer_agro_assistant

router = APIRouter()


@router.post("/agro-assistant/messages", response_model=AgroAssistantMessageOut)
def agro_assistant_message(
    payload: AgroAssistantMessageIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AgroAssistantMessageOut:
    result = answer_agro_assistant(db, current_user, payload)
    db.commit()
    return result
