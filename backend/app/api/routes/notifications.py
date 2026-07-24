from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import assigned_storage_unit_ids, get_current_user, require_alert_access, require_role, scope_company_query
from app.db.session import get_db
from app.models import Alert, MaintenanceRecord, NotificationDelivery, NotificationEvent, NotificationPreference, PushDeviceToken, User
from app.schemas import (
    NotificationEventOut,
    NotificationDeliveryOut,
    NotificationProviderStatusIn,
    NotificationPreferenceOut,
    NotificationPreferenceUpdate,
    NotificationTestOut,
    PushDeviceTokenIn,
    PushDeviceTokenOut,
)
from app.services.maintenance import require_maintenance_access
from app.services.notifications import (
    CHANNELS,
    deactivate_push_token,
    register_push_token,
    retry_delivery,
    send_test_notification,
    update_provider_delivery_status,
    upsert_preference,
)

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


@router.delete("/push-tokens/current", status_code=status.HTTP_204_NO_CONTENT)
def delete_current_push_token(
    payload: PushDeviceTokenIn,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    deactivate_push_token(db, current_user, token=payload.token)


@router.get("/events", response_model=list[NotificationEventOut])
def list_events(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationEvent]:
    stmt = scope_company_query(select(NotificationEvent), NotificationEvent, current_user)
    if current_user.role == "client":
        stmt = stmt.where(NotificationEvent.user_id == current_user.id)
    return list(db.scalars(stmt.order_by(NotificationEvent.created_at.desc()).limit(100)).all())


@router.get("/deliveries", response_model=list[NotificationDeliveryOut])
def list_deliveries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[NotificationDelivery]:
    stmt = select(NotificationDelivery)
    if current_user.role == "client":
        stmt = stmt.where(NotificationDelivery.user_id == current_user.id)
    elif current_user.role == "technician":
        unit_ids = assigned_storage_unit_ids(db, current_user)
        allowed_alert_ids = select(Alert.id).where(
            Alert.storage_unit_id.in_(unit_ids)
        )
        allowed_maintenance_ids = select(MaintenanceRecord.id).where(
            MaintenanceRecord.technician_id == current_user.id
        )
        stmt = stmt.where(
            (NotificationDelivery.user_id == current_user.id)
            | (NotificationDelivery.alert_id.in_(allowed_alert_ids))
            | (NotificationDelivery.maintenance_id.in_(allowed_maintenance_ids))
        )
    return list(db.scalars(stmt.order_by(NotificationDelivery.created_at.desc()).limit(200)).all())


@router.post("/{delivery_id}/retry", response_model=NotificationDeliveryOut)
def retry_notification_delivery(
    delivery_id: int,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> NotificationDelivery:
    delivery = db.get(NotificationDelivery, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Entrega no encontrada.")
    _require_delivery_access(db, current_user, delivery)
    try:
        return retry_delivery(db, delivery)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{delivery_id}/provider-status", response_model=NotificationDeliveryOut)
def set_notification_provider_status(
    delivery_id: int,
    payload: NotificationProviderStatusIn,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> NotificationDelivery:
    delivery = db.get(NotificationDelivery, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Entrega no encontrada.")
    try:
        return update_provider_delivery_status(
            db,
            delivery,
            provider_status=payload.status,
            provider_message_id=payload.provider_message_id,
            error_code=payload.error_code,
            error_message=payload.error_message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


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


def _require_delivery_access(db: Session, user: User, delivery: NotificationDelivery) -> None:
    if user.role == "admin" or delivery.user_id == user.id:
        return
    if delivery.alert_id is not None:
        require_alert_access(db, user, delivery.alert_id)
        return
    if delivery.maintenance_id is not None:
        require_maintenance_access(db, user, delivery.maintenance_id)
        return
    raise HTTPException(status_code=403, detail="No tienes permisos para esta entrega.")
