from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.core.config import settings
from app.db.session import get_db
from app.models import Device, User
from app.schemas import DemoSimulationOut, SensorReadingCreate
from app.services.reading_ingest import create_device_reading

router = APIRouter(prefix="/demo")


@router.post("/simulate-critical-reading", response_model=DemoSimulationOut, status_code=status.HTTP_201_CREATED)
def simulate_critical_reading(
    _current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> DemoSimulationOut:
    if settings.environment not in {"local", "demo"}:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo mode is not available.")

    device = db.scalar(select(Device).where(Device.external_id == "SILO-001", Device.is_active.is_(True)))
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo device SILO-001 not found.")

    result = create_device_reading(
        db,
        device,
        SensorReadingCreate(
            device_id=device.external_id,
            device_token="internal-demo-simulation",
            grain_temperature=36.8,
            ambient_temperature=30.4,
            ambient_humidity=84.6,
            battery_voltage=3.87,
            signal_quality=-62,
            timestamp=datetime.now(timezone.utc),
        ),
    )
    return DemoSimulationOut(
        storage_unit_id=device.storage_unit_id,
        device_id=device.id,
        device_external_id=device.external_id,
        reading=result.reading,
        alerts=result.alerts,
    )
