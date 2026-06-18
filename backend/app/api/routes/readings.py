from datetime import datetime

from fastapi import APIRouter, Depends, status
from fastapi import Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_device_access, scope_storage_unit_records_query
from app.db.session import get_db
from app.models import Device, SensorReading, User
from app.schemas import ReadingIngestResponse, ReadingOut, SensorReadingCreate
from app.services.reading_ingest import ingest_authenticated_reading

router = APIRouter()


@router.post("/readings", response_model=ReadingIngestResponse, status_code=status.HTTP_201_CREATED)
def create_reading(payload: SensorReadingCreate, db: Session = Depends(get_db)) -> ReadingIngestResponse:
    return ingest_authenticated_reading(db, payload)


@router.get("/readings", response_model=list[ReadingOut], dependencies=[Depends(get_current_user)])
def list_readings(
    device_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SensorReading]:
    stmt = scope_storage_unit_records_query(select(SensorReading), SensorReading, current_user, db)
    if device_id is not None:
        device = db.scalar(select(Device).where(Device.external_id == device_id))
        if device is None and device_id.isdigit():
            device = db.get(Device, int(device_id))
        if device is None:
            return []
        try:
            require_device_access(db, current_user, device.id)
        except Exception:
            return []
        stmt = stmt.where(SensorReading.device_id == device.id)
    if from_ is not None:
        stmt = stmt.where(SensorReading.timestamp >= from_)
    if to is not None:
        stmt = stmt.where(SensorReading.timestamp <= to)

    stmt = stmt.order_by(SensorReading.timestamp.desc()).limit(limit)
    return list(db.scalars(stmt).all())
