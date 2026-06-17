from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.security import ALGORITHM
from app.core.config import settings
from app.db.session import get_db
from app.models import Alert, Device, Site, StorageUnit, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if subject is None:
            raise credentials_error
    except JWTError as exc:
        raise credentials_error from exc

    user = db.scalar(
        select(User)
        .options(joinedload(User.company))
        .where(User.id == int(subject), User.is_active.is_(True))
    )
    if user is None:
        raise credentials_error
    return user


def require_role(*roles: str):
    allowed = set(roles)

    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para esta seccion.",
            )
        return current_user

    return dependency


def is_admin(user: User) -> bool:
    return user.role == "admin"


def has_demo_wide_access(user: User) -> bool:
    return user.role in {"admin", "technician"}


def can_access_company(user: User, company_id: int) -> bool:
    return has_demo_wide_access(user) or user.company_id == company_id


def require_company_access(user: User, company_id: int) -> None:
    if not can_access_company(user, company_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para esta seccion.")


def require_site_access(db: Session, user: User, site_id: int) -> Site:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    require_company_access(user, site.company_id)
    return site


def require_storage_unit_access(db: Session, user: User, storage_unit_id: int) -> StorageUnit:
    storage_unit = db.get(StorageUnit, storage_unit_id)
    if storage_unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage unit not found")
    require_company_access(user, storage_unit.company_id)
    return storage_unit


def require_device_access(db: Session, user: User, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    require_company_access(user, device.company_id)
    return device


def require_alert_access(db: Session, user: User, alert_id: int) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    require_company_access(user, alert.company_id)
    return alert


def scope_company_query(stmt, model, user: User):
    if has_demo_wide_access(user):
        return stmt
    return stmt.where(model.company_id == user.company_id)
