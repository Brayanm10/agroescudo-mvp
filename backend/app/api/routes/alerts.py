from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_alert_access, require_role, scope_company_query
from app.db.session import get_db
from app.models import Alert, User
from app.schemas import AlertOut

router = APIRouter(prefix="/alerts", dependencies=[Depends(get_current_user)])


@router.get("", response_model=list[AlertOut])
def list_alerts(
    company_id: int | None = None,
    site_id: int | None = None,
    storage_unit_id: int | None = None,
    device_id: int | None = None,
    status: str | None = None,
    severity: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Alert]:
    return _query_alerts(db, current_user, company_id, site_id, storage_unit_id, device_id, status, severity)


@router.get("/active", response_model=list[AlertOut])
def list_active_alerts(
    company_id: int | None = None,
    site_id: int | None = None,
    storage_unit_id: int | None = None,
    device_id: int | None = None,
    severity: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Alert]:
    return _query_alerts(db, current_user, company_id, site_id, storage_unit_id, device_id, "active", severity)


@router.patch("/{alert_id}/acknowledge", response_model=AlertOut)
def acknowledge_alert(
    alert_id: int,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> Alert:
    alert = require_alert_access(db, current_user, alert_id)
    if alert.acknowledged_at is None:
        alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


@router.patch("/{alert_id}/resolve", response_model=AlertOut)
def resolve_alert(
    alert_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> Alert:
    alert = require_alert_access(db, current_user, alert_id)
    alert.is_active = False
    if alert.resolved_at is None:
        alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return alert


def _query_alerts(
    db: Session,
    current_user: User,
    company_id: int | None,
    site_id: int | None,
    storage_unit_id: int | None,
    device_id: int | None,
    status: str | None,
    severity: str | None,
) -> list[Alert]:
    if company_id is not None and current_user.role == "client" and company_id != current_user.company_id:
        return []
    stmt = scope_company_query(select(Alert), Alert, current_user)
    if company_id is not None:
        stmt = stmt.where(Alert.company_id == company_id)
    if site_id is not None:
        stmt = stmt.where(Alert.site_id == site_id)
    if storage_unit_id is not None:
        stmt = stmt.where(Alert.storage_unit_id == storage_unit_id)
    if device_id is not None:
        stmt = stmt.where(Alert.device_id == device_id)
    if severity is not None:
        stmt = stmt.where(Alert.severity == severity)
    if status == "active":
        stmt = stmt.where(Alert.is_active.is_(True))
    elif status in {"resolved", "inactive"}:
        stmt = stmt.where(Alert.is_active.is_(False))
    elif status == "acknowledged":
        stmt = stmt.where(Alert.acknowledged_at.is_not(None))
    return list(db.scalars(stmt.order_by(Alert.created_at.desc())).all())
