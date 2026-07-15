from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_secret
from app.models import Company, Device, SensorReading, StorageUnit, utc_now
from app.schemas import ReadingIngestResponse, SensorReadingCreate
from app.services.alert_engine import evaluate_alerts
from app.services.notifications import dispatch_alert_notifications


def ingest_authenticated_reading(db: Session, payload: SensorReadingCreate) -> ReadingIngestResponse:
    device = db.scalar(select(Device).where(Device.external_id == payload.device_id))
    if device is None or not verify_secret(payload.device_token, device.token_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid device credentials")
    if not device.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sensor inactivo. Contacta al administrador.")

    storage_unit = db.get(StorageUnit, device.storage_unit_id)
    company = db.get(Company, device.company_id)
    if storage_unit is None or not storage_unit.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Silo/galpon inactivo. Contacta al administrador.")
    if company is None or not company.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Empresa inactiva. Contacta al administrador.")

    return create_device_reading(db, device, payload)


def create_device_reading(db: Session, device: Device, payload: SensorReadingCreate) -> ReadingIngestResponse:
    reading = SensorReading(
        company_id=device.company_id,
        site_id=device.site_id,
        storage_unit_id=device.storage_unit_id,
        device_id=device.id,
        grain_temperature=payload.grain_temperature,
        ambient_temperature=payload.ambient_temperature,
        ambient_humidity=payload.ambient_humidity,
        battery_voltage=payload.battery_voltage,
        signal_quality=payload.signal_quality,
        timestamp=payload.timestamp,
    )
    db.add(reading)
    device.last_seen_at = utc_now()
    db.flush()

    alerts = evaluate_alerts(db=db, device=device, reading=reading)
    new_alerts = [alert for alert in alerts if getattr(alert, "_was_created", False)]
    db.commit()
    db.refresh(reading)
    for alert in alerts:
        db.refresh(alert)
    if new_alerts:
        for alert in new_alerts:
            dispatch_alert_notifications(db, alert, reading)
        db.commit()
        for alert in alerts:
            db.refresh(alert)

    return ReadingIngestResponse(reading=reading, alerts=alerts)
