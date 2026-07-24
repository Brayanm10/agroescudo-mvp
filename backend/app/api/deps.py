from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.security import ALGORITHM
from app.core.config import settings
from app.db.session import get_db
from app.models import Alert, Company, Device, SensorReading, Site, StorageUnit, User, UserSession, utc_now

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
optional_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def _as_utc_aware(value):
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=utc_now().tzinfo)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    return _resolve_user_from_token(token, db)


def get_optional_current_user(
    token: str | None = Depends(optional_oauth2_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if token is None:
        return None
    return _resolve_user_from_token(token, db)


def _resolve_user_from_token(token: str, db: Session) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        jti = payload.get("jti")
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
    if getattr(user, "status", "ACTIVE") != "ACTIVE":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario desactivado. Contacta al administrador.")
    if jti:
        session = db.scalar(select(UserSession).where(UserSession.jti == jti, UserSession.user_id == user.id))
        if session is None or session.revoked_at is not None or _as_utc_aware(session.expires_at) < utc_now():
            raise credentials_error
        session.last_seen_at = utc_now()
        user.last_seen_at = utc_now()
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


def assigned_storage_unit_ids(db: Session, user: User) -> list[int]:
    if user.role == "admin":
        return list(db.scalars(select(StorageUnit.id)).all())
    if user.role == "technician":
        stmt = select(StorageUnit.id).where(StorageUnit.assigned_technician_id == user.id)
    elif user.role == "client":
        stmt = select(StorageUnit.id).where(StorageUnit.assigned_client_id == user.id)
    else:
        return []
    return list(db.scalars(stmt).all())


def _assigned_site_ids(db: Session, user: User) -> list[int]:
    if user.role == "admin":
        return list(db.scalars(select(Site.id)).all())
    unit_ids = assigned_storage_unit_ids(db, user)
    if not unit_ids:
        return []
    return list(db.scalars(select(StorageUnit.site_id).where(StorageUnit.id.in_(unit_ids)).distinct()).all())


def _assigned_company_ids(db: Session, user: User) -> list[int]:
    if user.role == "admin":
        return list(db.scalars(select(Company.id)).all())
    unit_ids = assigned_storage_unit_ids(db, user)
    company_ids: set[int] = set()
    if unit_ids:
        company_ids.update(
            db.scalars(select(StorageUnit.company_id).where(StorageUnit.id.in_(unit_ids)).distinct()).all()
        )
    if user.role == "client" and user.company_id:
        company_ids.add(user.company_id)
    return sorted(company_ids)


def can_access_company(user: User, company_id: int) -> bool:
    return user.role == "admin" or user.company_id == company_id


def require_company_access(db: Session, user: User, company_id: int) -> None:
    if user.role == "admin":
        return
    if company_id not in _assigned_company_ids(db, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para esta seccion.")


def require_site_access(db: Session, user: User, site_id: int) -> Site:
    site = db.get(Site, site_id)
    if site is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    if user.role != "admin" and site.id not in _assigned_site_ids(db, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para esta seccion.")
    return site


def can_access_storage_unit(user: User, storage_unit: StorageUnit) -> bool:
    if user.role == "admin":
        return True
    if user.role == "technician":
        return storage_unit.assigned_technician_id == user.id
    if user.role == "client":
        return storage_unit.assigned_client_id == user.id
    return False


def require_storage_unit_access(db: Session, user: User, storage_unit_id: int) -> StorageUnit:
    storage_unit = db.get(StorageUnit, storage_unit_id)
    if storage_unit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage unit not found")
    if not can_access_storage_unit(user, storage_unit):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tienes permisos para esta seccion.")
    return storage_unit


def require_device_access(db: Session, user: User, device_id: int) -> Device:
    device = db.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found")
    require_storage_unit_access(db, user, device.storage_unit_id)
    return device


def require_alert_access(db: Session, user: User, alert_id: int) -> Alert:
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    require_storage_unit_access(db, user, alert.storage_unit_id)
    return alert


def scope_companies_query(stmt, user: User, db: Session):
    if user.role == "admin":
        return stmt
    company_ids = _assigned_company_ids(db, user)
    if not company_ids:
        return stmt.where(Company.id == -1)
    return stmt.where(Company.id.in_(company_ids))


def scope_sites_query(stmt, user: User, db: Session):
    if user.role == "admin":
        return stmt
    site_ids = _assigned_site_ids(db, user)
    if not site_ids:
        return stmt.where(Site.id == -1)
    return stmt.where(Site.id.in_(site_ids))


def scope_storage_units_query(stmt, user: User, db: Session):
    if user.role == "admin":
        return stmt
    unit_ids = assigned_storage_unit_ids(db, user)
    if not unit_ids:
        return stmt.where(StorageUnit.id == -1)
    return stmt.where(StorageUnit.id.in_(unit_ids))


def scope_storage_unit_records_query(stmt, model, user: User, db: Session):
    if user.role == "admin":
        return stmt
    unit_ids = assigned_storage_unit_ids(db, user)
    if not unit_ids:
        return stmt.where(model.storage_unit_id == -1)
    return stmt.where(model.storage_unit_id.in_(unit_ids))


def scope_company_query(stmt, model, user: User):
    if user.role == "admin":
        return stmt
    return stmt.where(model.company_id == user.company_id)
