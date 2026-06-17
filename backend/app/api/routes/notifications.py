from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, scope_company_query
from app.db.session import get_db
from app.models import NotificationEvent, NotificationPreference, PushDeviceToken, User
from app.schemas import (
    NotificationEventOut,
    NotificationPreferenceOut,
    NotificationPreferenceUpdate,
    NotificationTestOut,
    PushDeviceTokenIn,
    PushDeviceTokenOut,
)
from app.services.notifications import CHANNELS, register_push_token, send_test_notification, upsert_preference

router = APIRouter(prefix="/notifications", dependencies=[Depends(get_current_user)])


@router.get("/preferences", response_model=list[NotificationPreferenceOut])
def list_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationPreference]:
    return list(
        db.scalars(
            select(NotificationPreference)
            .where(NotificationPreference.user_id == current_user.id)
            .order_by(NotificationPreference.channel)
        ).all()
    )


@router.put("/preferences/{channel}", response_model=NotificationPreferenceOut)
def update_preference(
    channel: str,
    payload: NotificationPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationPreference:
    if channel not in CHANNELS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Canal no soportado")
    try:
        return upsert_preference(
            db,
            current_user,
            channel=channel,
            enabled=payload.enabled,
            destination=payload.destination,
            minimum_severity=payload.minimum_severity,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/push-tokens", response_model=PushDeviceTokenOut, status_code=status.HTTP_201_CREATED)
def create_push_token(
    payload: PushDeviceTokenIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PushDeviceToken:
    return register_push_token(db, current_user, token=payload.token, platform=payload.platform)


@router.get("/events", response_model=list[NotificationEventOut])
def list_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationEvent]:
    stmt = scope_company_query(select(NotificationEvent), NotificationEvent, current_user)
    if current_user.role == "client":
        stmt = stmt.where(NotificationEvent.user_id == current_user.id)
    return list(db.scalars(stmt.order_by(NotificationEvent.created_at.desc()).limit(100)).all())


@router.post("/test/{channel}", response_model=NotificationTestOut)
def test_notification(
    channel: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationTestOut:
    if channel not in CHANNELS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Canal no soportado")
    event = send_test_notification(db, current_user, channel)
    return NotificationTestOut(channel=channel, event=event)
