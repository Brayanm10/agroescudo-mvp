from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import assigned_storage_unit_ids, get_current_user, require_device_access, require_storage_unit_access
from app.db.session import get_db
from app.models import (
    Alert,
    MaintenanceRecord,
    SensorMetricValue,
    SensorReading,
    ServiceCase,
    User,
    utc_now,
)
from app.services.audit import record_audit_event

router = APIRouter(prefix="/exports", dependencies=[Depends(get_current_user)])
MAX_EXPORT_ROWS = 50_000


@router.get("/readings.csv")
def export_readings(
    storage_unit_id: int | None = None,
    device_id: int | None = None,
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    start, end = _period(date_from, date_to)
    unit_ids = _units(db, current_user, storage_unit_id)
    if device_id is not None:
        device = require_device_access(db, current_user, device_id)
        if device.storage_unit_id not in unit_ids:
            raise HTTPException(status_code=403, detail="No tienes permisos para exportar este nodo.")
    stmt = select(SensorReading).where(
        SensorReading.storage_unit_id.in_(unit_ids) if unit_ids else SensorReading.id == -1,
        SensorReading.timestamp >= start,
        SensorReading.timestamp <= end,
    )
    if device_id is not None:
        stmt = stmt.where(SensorReading.device_id == device_id)
    rows = list(db.scalars(stmt.order_by(SensorReading.timestamp).limit(MAX_EXPORT_ROWS + 1)).all())
    truncated = len(rows) > MAX_EXPORT_ROWS
    rows = rows[:MAX_EXPORT_ROWS]
    reading_ids = [item.id for item in rows]
    metric_map: dict[int, list[SensorMetricValue]] = {}
    if reading_ids:
        for metric in db.scalars(select(SensorMetricValue).where(SensorMetricValue.sensor_reading_id.in_(reading_ids))).all():
            metric_map.setdefault(metric.sensor_reading_id, []).append(metric)
    data = [
        [
            row.id,
            row.company_id,
            row.storage_unit_id,
            row.device_id,
            row.timestamp.isoformat(),
            row.grain_temperature,
            row.ambient_temperature,
            row.ambient_humidity,
            row.battery_voltage,
            row.level_distance_cm,
            row.level_percent,
            row.soil_moisture_percent,
            row.soil_temperature_c,
            json.dumps({item.variable_type: item.raw_value for item in metric_map.get(row.id, [])}, ensure_ascii=False),
            json.dumps({item.variable_type: item.calibrated_value for item in metric_map.get(row.id, [])}, ensure_ascii=False),
            json.dumps({item.variable_type: item.calibration_version_applied for item in metric_map.get(row.id, [])}, ensure_ascii=False),
            "UTC",
        ]
        for row in rows
    ]
    return _csv_response(
        db,
        current_user,
        "readings",
        [
            "reading_id", "company_id", "storage_unit_id", "device_id", "timestamp_utc",
            "grain_temperature_c", "ambient_temperature_c", "ambient_humidity_percent",
            "battery_voltage_v", "level_distance_cm", "level_percent", "soil_moisture_percent",
            "soil_temperature_c", "raw_metrics_json", "calibrated_metrics_json",
            "calibration_versions_json", "timezone",
        ],
        data,
        start,
        end,
        truncated,
    )


@router.get("/alerts.csv")
def export_alerts(
    storage_unit_id: int | None = None,
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    start, end = _period(date_from, date_to)
    unit_ids = _units(db, current_user, storage_unit_id)
    rows = list(db.scalars(select(Alert).where(
        Alert.storage_unit_id.in_(unit_ids) if unit_ids else Alert.id == -1,
        Alert.created_at >= start,
        Alert.created_at <= end,
    ).order_by(Alert.created_at).limit(MAX_EXPORT_ROWS + 1)).all())
    truncated = len(rows) > MAX_EXPORT_ROWS
    data = [[row.id, row.storage_unit_id, row.device_id, row.created_at.isoformat(), row.alert_type, row.metric, row.severity, row.observed_value, row.threshold_value, "active" if row.is_active else "resolved", row.acknowledged_at, row.resolved_at, "UTC"] for row in rows[:MAX_EXPORT_ROWS]]
    return _csv_response(db, current_user, "alerts", ["alert_id", "storage_unit_id", "device_id", "created_at_utc", "type", "metric", "severity", "observed_value", "threshold_value", "status", "acknowledged_at", "resolved_at", "timezone"], data, start, end, truncated)


@router.get("/incidents.csv")
def export_incidents(
    storage_unit_id: int | None = None,
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    start, end = _period(date_from, date_to)
    unit_ids = _units(db, current_user, storage_unit_id)
    rows = list(db.scalars(select(ServiceCase).where(
        ServiceCase.storage_unit_id.in_(unit_ids) if unit_ids else ServiceCase.id == -1,
        ServiceCase.created_at >= start,
        ServiceCase.created_at <= end,
    ).order_by(ServiceCase.created_at).limit(MAX_EXPORT_ROWS + 1)).all())
    truncated = len(rows) > MAX_EXPORT_ROWS
    data = [[row.id, row.storage_unit_id, row.device_id, row.created_at.isoformat(), row.title, row.priority, row.status, row.assigned_technician_id, row.closed_at, "UTC"] for row in rows[:MAX_EXPORT_ROWS]]
    return _csv_response(db, current_user, "incidents", ["incident_id", "storage_unit_id", "device_id", "created_at_utc", "title", "priority", "status", "technician_id", "closed_at", "timezone"], data, start, end, truncated)


@router.get("/maintenance.csv")
def export_maintenance(
    storage_unit_id: int | None = None,
    date_from: datetime | None = Query(default=None, alias="from"),
    date_to: datetime | None = Query(default=None, alias="to"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    start, end = _period(date_from, date_to)
    unit_ids = _units(db, current_user, storage_unit_id)
    rows = list(db.scalars(select(MaintenanceRecord).where(
        MaintenanceRecord.storage_unit_id.in_(unit_ids) if unit_ids else MaintenanceRecord.id == -1,
        MaintenanceRecord.created_at >= start,
        MaintenanceRecord.created_at <= end,
    ).order_by(MaintenanceRecord.created_at).limit(MAX_EXPORT_ROWS + 1)).all())
    truncated = len(rows) > MAX_EXPORT_ROWS
    data = [[row.id, row.storage_unit_id, row.device_id, row.created_at.isoformat(), row.maintenance_type, row.status, row.priority, row.technician_id, row.diagnosis, row.action_taken, row.evidence_count, row.completed_at, "UTC"] for row in rows[:MAX_EXPORT_ROWS]]
    return _csv_response(db, current_user, "maintenance", ["maintenance_id", "storage_unit_id", "device_id", "created_at_utc", "type", "status", "priority", "technician_id", "diagnosis", "action_taken", "evidence_count", "completed_at", "timezone"], data, start, end, truncated)


def _period(date_from, date_to):
    end = date_to or utc_now()
    start = date_from or end - timedelta(days=7)
    if start >= end:
        raise HTTPException(status_code=422, detail="El inicio debe ser anterior al fin.")
    return start, end


def _units(db, user, storage_unit_id):
    if storage_unit_id is not None:
        require_storage_unit_access(db, user, storage_unit_id)
        return [storage_unit_id]
    return assigned_storage_unit_ids(db, user)


def _csv_response(db, user, kind, headers, rows, start, end, truncated):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(headers)
    writer.writerows(rows)
    record_audit_event(
        db,
        action=f"export.{kind}",
        summary=f"Exportacion CSV de {kind}.",
        user=user,
        resource_type="data_export",
        metadata={"from": start.isoformat(), "to": end.isoformat(), "rows": len(rows), "truncated": truncated},
    )
    db.commit()
    filename = f"agroescudo-{kind}-{utc_now():%Y-%m-%d}.csv"
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8-sig")]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Export-Truncated": str(truncated).lower(),
            "X-Export-Limit": str(MAX_EXPORT_ROWS),
        },
    )
