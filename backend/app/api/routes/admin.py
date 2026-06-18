from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.security import hash_password
from app.db.session import get_db
from app.models import Company, NotificationDelivery, StorageUnit, User
from app.schemas import (
    AdminNotificationTestIn,
    NotificationDeliveryOut,
    PasswordResetIn,
    UserCreate,
    UserOut,
    UserStorageUnitAssignmentsIn,
    UserUpdate,
)
from app.services.notifications import create_admin_test_delivery

router = APIRouter(prefix="/admin", dependencies=[Depends(require_role("admin"))])


@router.get("/users", response_model=list[UserOut])
def list_admin_users(
    role: str | None = None,
    db: Session = Depends(get_db),
) -> list[User]:
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    return list(db.scalars(stmt.order_by(User.full_name)).all())


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_admin_user(payload: UserCreate, db: Session = Depends(get_db)) -> User:
    _require_company(db, payload.company_id)
    if db.scalar(select(User).where(User.email == payload.email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        company_id=payload.company_id,
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_admin_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)) -> User:
    user = _get_user(db, user_id)
    if payload.company_id is not None:
        _require_company(db, payload.company_id)
        user.company_id = payload.company_id
    if payload.email is not None and payload.email != user.email:
        if db.scalar(select(User).where(User.email == payload.email, User.id != user.id)) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        user.email = payload.email
    if payload.full_name is not None:
        user.full_name = payload.full_name
    if payload.role is not None:
        user.role = payload.role
    if payload.is_active is not None:
        user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password", response_model=UserOut)
def reset_admin_user_password(user_id: int, payload: PasswordResetIn, db: Session = Depends(get_db)) -> User:
    user = _get_user(db, user_id)
    user.hashed_password = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/activate", response_model=UserOut)
def activate_admin_user(user_id: int, db: Session = Depends(get_db)) -> User:
    user = _get_user(db, user_id)
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/deactivate", response_model=UserOut)
def deactivate_admin_user(user_id: int, db: Session = Depends(get_db)) -> User:
    user = _get_user(db, user_id)
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/assign-storage-units", response_model=UserOut)
def assign_admin_user_storage_units(
    user_id: int,
    payload: UserStorageUnitAssignmentsIn,
    db: Session = Depends(get_db),
) -> User:
    user = _get_user(db, user_id)
    units = list(db.scalars(select(StorageUnit).where(StorageUnit.id.in_(payload.storage_unit_ids))).all())
    if len(units) != len(set(payload.storage_unit_ids)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Storage unit not found")

    if user.role == "technician":
        db.query(StorageUnit).filter(StorageUnit.assigned_technician_id == user.id).update(
            {StorageUnit.assigned_technician_id: None},
            synchronize_session=False,
        )
        for unit in units:
            unit.assigned_technician_id = user.id
    elif user.role == "client":
        db.query(StorageUnit).filter(StorageUnit.assigned_client_id == user.id).update(
            {StorageUnit.assigned_client_id: None},
            synchronize_session=False,
        )
        for unit in units:
            if unit.company_id != user.company_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Client user belongs to another company")
            unit.assigned_client_id = user.id
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only technicians and clients can be assigned")

    db.commit()
    db.refresh(user)
    return user


@router.get("/technicians", response_model=list[UserOut])
def list_admin_technicians(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).where(User.role == "technician").order_by(User.full_name)).all())


@router.get("/clients", response_model=list[UserOut])
def list_admin_clients(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).where(User.role == "client").order_by(User.full_name)).all())


@router.get("/notifications/deliveries", response_model=list[NotificationDeliveryOut])
def list_notification_deliveries(db: Session = Depends(get_db)) -> list[NotificationDelivery]:
    stmt = select(NotificationDelivery).order_by(NotificationDelivery.created_at.desc()).limit(200)
    return list(db.scalars(stmt).all())


@router.post("/notifications/test/{channel}", response_model=NotificationDeliveryOut)
def test_admin_notification_channel(
    channel: str,
    payload: AdminNotificationTestIn,
    db: Session = Depends(get_db),
) -> NotificationDelivery:
    user = db.get(User, payload.user_id) if payload.user_id is not None else None
    if payload.user_id is not None and user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        return create_admin_test_delivery(
            db,
            user=user,
            channel=channel,
            destination=payload.destination,
            message=payload.message,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _get_user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _require_company(db: Session, company_id: int) -> None:
    if db.get(Company, company_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
