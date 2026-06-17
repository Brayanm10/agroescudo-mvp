from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Alert, Company, Device, OperationalLog, SensorReading, Site, StorageUnit, User
from app.schemas import PilotOut
from app.services.reports import estimate_hours_out_of_range


def calculate_pilot_status(db: Session, storage_unit: StorageUnit) -> str:
    active_alerts = _count(
        db,
        select(func.count(Alert.id)).where(
            Alert.storage_unit_id == storage_unit.id,
            Alert.is_active.is_(True),
        ),
    )
    installation_count = _log_category_count(db, storage_unit.id, "installation")
    reading_count = _count(
        db,
        select(func.count(SensorReading.id)).where(SensorReading.storage_unit_id == storage_unit.id),
    )

    if installation_count == 0:
        return "pendiente de instalacion"
    if active_alerts:
        return "con alerta activa"
    if reading_count == 0:
        return "instalado"
    if storage_unit.last_report_generated_at is not None:
        first_reading = db.scalar(
            select(func.min(SensorReading.timestamp)).where(SensorReading.storage_unit_id == storage_unit.id)
        )
        if first_reading and (datetime.now(timezone.utc) - _as_utc(first_reading)).days >= 60:
            return "listo para evaluacion"
        return "reporte generado"
    return "en monitoreo"


def build_pilot_summary(db: Session, storage_unit: StorageUnit) -> PilotOut:
    company = db.get(Company, storage_unit.company_id)
    site = db.get(Site, storage_unit.site_id)
    device = db.scalar(
        select(Device)
        .where(Device.storage_unit_id == storage_unit.id)
        .order_by(Device.created_at.asc())
    )
    technician = db.get(User, storage_unit.assigned_technician_id) if storage_unit.assigned_technician_id else None
    client = db.get(User, storage_unit.assigned_client_id) if storage_unit.assigned_client_id else None
    readings = list(
        db.scalars(
            select(SensorReading)
            .where(SensorReading.storage_unit_id == storage_unit.id)
            .order_by(SensorReading.timestamp.asc())
        ).all()
    )
    first_reading_at = readings[0].timestamp if readings else None
    last_reading_at = readings[-1].timestamp if readings else None
    days_monitored = max(1, (datetime.now(timezone.utc) - _as_utc(first_reading_at)).days + 1) if first_reading_at else 0

    return PilotOut(
        storage_unit_id=storage_unit.id,
        storage_unit_name=storage_unit.name,
        storage_unit_type=storage_unit.unit_type,
        company_id=storage_unit.company_id,
        company_name=company.name if company else "",
        site_id=storage_unit.site_id,
        site_name=site.name if site else "",
        site_location=site.location if site else None,
        device_id=device.id if device else None,
        device_external_id=device.external_id if device else None,
        technician_user_id=technician.id if technician else None,
        technician_name=technician.full_name if technician else None,
        client_user_id=client.id if client else None,
        client_name=client.full_name if client else None,
        status=calculate_pilot_status(db, storage_unit),
        days_monitored=days_monitored,
        reading_count=len(readings),
        alerts_generated=_count(
            db,
            select(func.count(Alert.id)).where(Alert.storage_unit_id == storage_unit.id),
        ),
        alerts_resolved=_count(
            db,
            select(func.count(Alert.id)).where(
                Alert.storage_unit_id == storage_unit.id,
                Alert.resolved_at.is_not(None),
            ),
        ),
        active_alerts=_count(
            db,
            select(func.count(Alert.id)).where(
                Alert.storage_unit_id == storage_unit.id,
                Alert.is_active.is_(True),
            ),
        ),
        actions_registered=_count(
            db,
            select(func.count(OperationalLog.id)).where(OperationalLog.storage_unit_id == storage_unit.id),
        ),
        installation_count=_log_category_count(db, storage_unit.id, "installation"),
        maintenance_count=_log_category_count(db, storage_unit.id, "maintenance"),
        approximate_hours_out_of_range=estimate_hours_out_of_range(db, storage_unit, readings),
        last_reading_at=last_reading_at,
        last_report_generated_at=storage_unit.last_report_generated_at,
    )


def _log_category_count(db: Session, storage_unit_id: int, category: str) -> int:
    return _count(
        db,
        select(func.count(OperationalLog.id)).where(
            OperationalLog.storage_unit_id == storage_unit_id,
            OperationalLog.category == category,
        ),
    )


def _count(db: Session, stmt) -> int:
    return db.scalar(stmt) or 0


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
