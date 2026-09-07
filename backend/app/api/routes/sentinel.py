from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models import SentinelDevice, SentinelJob, utc_now
from app.schemas import (
    DeletionOut,
    SentinelDeviceCreate,
    SentinelDeviceCreatedOut,
    SentinelDeviceOut,
    SentinelDeviceUpdate,
    SentinelJobOut,
    SentinelJobResultIn,
    SentinelPollIn,
    SentinelPollOut,
)
from app.services.sentinel import (
    authenticate_sentinel,
    device_summary,
    issue_sentinel_token,
    mask_phone,
    poll_sentinel,
    record_job_result,
)
from app.services.soft_delete import soft_delete_sentinel

router = APIRouter(prefix="/sentinel")
admin_router = APIRouter(prefix="/admin/sentinel", dependencies=[Depends(require_role("admin"))])
sentinel_bearer = HTTPBearer(auto_error=False)


@router.post("/poll", response_model=SentinelPollOut)
def sentinel_poll(
    payload: SentinelPollIn,
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(sentinel_bearer),
    db: Session = Depends(get_db),
) -> dict:
    token = _bearer_token(credentials)
    device = authenticate_sentinel(db, token, payload.device_uid)
    device.firmware_version = payload.firmware_version
    device.wifi_rssi = payload.wifi_rssi
    device.gsm_registered = payload.gsm_registered
    device.sim_ready = payload.sim_ready
    return poll_sentinel(db, device, source_ip=request.client.host if request.client else None)


@router.post("/jobs/{job_id}/result", response_model=SentinelJobOut)
def sentinel_job_result(
    job_id: str,
    payload: SentinelJobResultIn,
    credentials: HTTPAuthorizationCredentials | None = Depends(sentinel_bearer),
    db: Session = Depends(get_db),
) -> dict:
    device = authenticate_sentinel(db, _bearer_token(credentials))
    job = record_job_result(
        db,
        device,
        job_id,
        result_status=payload.status,
        result_code=payload.result_code,
        message=payload.message,
    )
    return _masked_job(job)


@admin_router.get("/devices", response_model=list[SentinelDeviceOut])
def list_sentinel_devices(db: Session = Depends(get_db)) -> list[dict]:
    devices = list(
        db.scalars(
            select(SentinelDevice)
            .where(SentinelDevice.deleted_at.is_(None))
            .order_by(SentinelDevice.created_at.desc())
        ).all()
    )
    return [device_summary(db, device) for device in devices]


@admin_router.post("/devices", response_model=SentinelDeviceCreatedOut, status_code=status.HTTP_201_CREATED)
def create_sentinel_device(payload: SentinelDeviceCreate, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(SentinelDevice.id).where(SentinelDevice.device_uid == payload.device_uid)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un Sentinel con ese UID.")
    token, token_hash = issue_sentinel_token()
    device = SentinelDevice(device_uid=payload.device_uid, name=payload.name, token_hash=token_hash)
    db.add(device)
    db.commit()
    db.refresh(device)
    return {**device_summary(db, device), "token": token}


@admin_router.post("/devices/{device_id}/rotate-token", response_model=SentinelDeviceCreatedOut)
def rotate_sentinel_token(device_id: int, db: Session = Depends(get_db)) -> dict:
    device = _get_device(db, device_id)
    token, token_hash = issue_sentinel_token()
    device.token_hash = token_hash
    device.token_rotated_at = utc_now()
    db.commit()
    db.refresh(device)
    return {**device_summary(db, device), "token": token}


@admin_router.patch("/devices/{device_id}", response_model=SentinelDeviceOut)
def update_sentinel_device(device_id: int, payload: SentinelDeviceUpdate, db: Session = Depends(get_db)) -> dict:
    device = _get_device(db, device_id)
    values = payload.model_dump(exclude_unset=True)
    if "device_uid" in values and values["device_uid"] != device.device_uid:
        duplicate = db.scalar(
            select(SentinelDevice.id).where(
                SentinelDevice.device_uid == values["device_uid"],
                SentinelDevice.id != device.id,
            )
        )
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe un Sentinel con ese UID.")
    for key, value in values.items():
        setattr(device, key, value)
    db.commit()
    db.refresh(device)
    return device_summary(db, device)


@admin_router.post("/devices/{device_id}/activate", response_model=SentinelDeviceOut)
def activate_sentinel(device_id: int, db: Session = Depends(get_db)) -> dict:
    device = _get_device(db, device_id)
    device.active = True
    db.commit()
    db.refresh(device)
    return device_summary(db, device)


@admin_router.post("/devices/{device_id}/deactivate", response_model=SentinelDeviceOut)
def deactivate_sentinel(device_id: int, db: Session = Depends(get_db)) -> dict:
    device = _get_device(db, device_id)
    device.active = False
    db.commit()
    db.refresh(device)
    return device_summary(db, device)


@admin_router.delete("/devices/{device_id}", response_model=DeletionOut)
def delete_sentinel(
    device_id: int,
    current_user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> DeletionOut:
    device = _get_device(db, device_id)
    soft_delete_sentinel(db, current_user, device)
    db.commit()
    return DeletionOut(
        entity="sentinel",
        id=device.id,
        deleted_at=device.deleted_at,
        message="Sentinel eliminado de la operacion.",
    )


@admin_router.get("/jobs", response_model=list[SentinelJobOut])
def list_sentinel_jobs(status_filter: str | None = None, limit: int = 100, db: Session = Depends(get_db)) -> list[dict]:
    stmt = select(SentinelJob)
    if status_filter:
        stmt = stmt.where(SentinelJob.status == status_filter)
    jobs = list(db.scalars(stmt.order_by(SentinelJob.created_at.desc()).limit(min(max(limit, 1), 500))).all())
    return [_masked_job(job) for job in jobs]


def _get_device(db: Session, device_id: int) -> SentinelDevice:
    device = db.get(SentinelDevice, device_id)
    if device is None or device.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sentinel no encontrado.")
    return device


def _bearer_token(credentials: HTTPAuthorizationCredentials | None) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token Sentinel requerido.")
    return credentials.credentials


def _masked_job(job: SentinelJob) -> dict:
    return {
        column.name: (mask_phone(job.destination_phone) if column.name == "destination_phone" else getattr(job, column.name))
        for column in job.__table__.columns
        if column.name != "idempotency_key"
    }
