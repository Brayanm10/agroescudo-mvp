from __future__ import annotations

import json

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import assigned_storage_unit_ids, require_device_access, require_storage_unit_access
from app.models import (
    Alert,
    Device,
    InstallationChecklist,
    IotDevice,
    IotGateway,
    OperationalLog,
    SensorReading,
    User,
    utc_now,
)
from app.schemas import InstallationOut
from app.services.audit import record_audit_event


FINAL_INSTALLATION_STATUSES = {"PASSED", "PASSED_WITH_OBSERVATIONS", "FAILED"}

CRITICAL_RESPONSE_PATHS = (
    "hardware.enclosure_ok",
    "hardware.mounting_ok",
    "hardware.antenna_ok",
    "hardware.battery_ok",
    "hardware.sensor_ok",
    "hardware.wiring_ok",
    "hardware.sealed_ok",
    "hardware.qr_applied",
    "communication.first_transmission",
    "communication.time_synced",
    "communication.connectivity_ok",
    "validation.reading_compared",
    "validation.thresholds_validated",
    "validation.test_alert_passed",
    "validation.client_access_validated",
    "validation.technician_access_validated",
    "validation.test_report_generated",
)


def list_installations(db: Session, user: User) -> list[InstallationChecklist]:
    stmt = select(InstallationChecklist).order_by(InstallationChecklist.created_at.desc())
    if user.role == "technician":
        stmt = stmt.where(InstallationChecklist.technician_id == user.id)
    elif user.role == "client":
        unit_ids = assigned_storage_unit_ids(db, user)
        stmt = stmt.where(InstallationChecklist.storage_unit_id.in_(unit_ids or [-1]))
    return list(db.scalars(stmt).all())


def require_installation_access(db: Session, user: User, installation_id: int) -> InstallationChecklist:
    checklist = db.get(InstallationChecklist, installation_id)
    if checklist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Checklist no encontrado.")
    require_storage_unit_access(db, user, checklist.storage_unit_id)
    if user.role == "technician" and checklist.technician_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Instalacion no asignada al tecnico.")
    return checklist


def installation_out(checklist: InstallationChecklist, user: User) -> InstallationOut:
    responses = _json_object(checklist.responses_json)
    validation_errors = _json_list(checklist.validation_errors_json)
    if user.role == "client":
        responses = {
            "identification": responses.get("identification", {}),
            "validation": {
                "first_reading": checklist.first_reading_id is not None,
                "test_alert": checklist.test_alert_id is not None,
            },
            "final_status": checklist.status,
        }
        validation_errors = []
    return InstallationOut(
        id=checklist.id,
        company_id=checklist.company_id,
        storage_unit_id=checklist.storage_unit_id,
        device_id=checklist.device_id,
        technician_id=checklist.technician_id,
        status=checklist.status,
        started_at=checklist.started_at,
        completed_at=checklist.completed_at,
        checklist_version=checklist.checklist_version,
        responses=responses,
        first_reading_id=checklist.first_reading_id,
        test_alert_id=checklist.test_alert_id,
        notes=checklist.notes,
        validation_errors=validation_errors,
        next_review_at=checklist.next_review_at,
        created_by_id=checklist.created_by_id,
        created_at=checklist.created_at,
        updated_at=checklist.updated_at,
    )


def validate_installation(
    db: Session,
    checklist: InstallationChecklist,
    user: User,
    final_status: str,
) -> list[str]:
    errors: list[str] = []
    device = db.get(Device, checklist.device_id)
    if device is None or device.storage_unit_id != checklist.storage_unit_id:
        errors.append("El dispositivo no esta asociado a la unidad.")
    if checklist.technician_id is None:
        errors.append("No existe tecnico responsable.")

    first_reading = db.get(SensorReading, checklist.first_reading_id) if checklist.first_reading_id else None
    if first_reading is None or first_reading.device_id != checklist.device_id:
        errors.append("No existe una primera lectura valida del dispositivo.")

    test_alert = db.get(Alert, checklist.test_alert_id) if checklist.test_alert_id else None
    if test_alert is None or test_alert.device_id != checklist.device_id:
        errors.append("No existe una alerta de prueba valida del dispositivo.")

    responses = _json_object(checklist.responses_json)
    for path in CRITICAL_RESPONSE_PATHS:
        if _path_value(responses, path) is not True:
            errors.append(f"Falta validar: {path}.")

    gateway_required = _path_value(responses, "communication.gateway_required")
    if gateway_required is not False:
        iot_device = db.scalar(select(IotDevice).where(IotDevice.device_id == checklist.device_id))
        gateway = db.get(IotGateway, iot_device.gateway_id) if iot_device and iot_device.gateway_id else None
        if gateway is None or not gateway.is_active:
            errors.append("No existe gateway activo asociado.")

    active_sensor_fault = db.scalar(
        select(Alert).where(
            Alert.device_id == checklist.device_id,
            Alert.is_active.is_(True),
            (Alert.alert_type.ilike("%sensor%")) | (Alert.metric == "sensor_status"),
        )
    )
    if active_sensor_fault is not None:
        errors.append("Existe una falla de sensor activa.")

    if final_status in {"PASSED", "PASSED_WITH_OBSERVATIONS"} and errors:
        checklist.validation_errors_json = json.dumps(errors, ensure_ascii=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "El checklist no cumple los criterios de aprobacion.", "errors": errors},
        )

    previous_status = checklist.status
    checklist.status = final_status
    checklist.completed_at = utc_now()
    checklist.validation_errors_json = json.dumps(errors, ensure_ascii=True) if errors else None
    if device is not None:
        device.installed_at = device.installed_at or checklist.completed_at
        device.operational_status = "operational" if final_status.startswith("PASSED") else "degraded"
        db.add(
            OperationalLog(
                company_id=checklist.company_id,
                site_id=device.site_id,
                storage_unit_id=checklist.storage_unit_id,
                device_id=checklist.device_id,
                user_id=user.id,
                category="installation",
                action_taken=f"Checklist de instalacion {final_status.lower()}",
                operator_name=user.full_name,
                notes=checklist.notes or "Validacion digital de instalacion.",
                timestamp=checklist.completed_at,
            )
        )
    record_audit_event(
        db,
        action="installation.validate",
        summary="Checklist de instalacion validado",
        user=user,
        resource_type="installation",
        resource_id=checklist.id,
        metadata={"previous_status": previous_status, "status": final_status, "errors": errors},
    )
    return errors


def verify_installation_references(
    db: Session,
    user: User,
    *,
    device_id: int,
    first_reading_id: int | None,
    test_alert_id: int | None,
) -> Device:
    device = require_device_access(db, user, device_id)
    if first_reading_id is not None:
        reading = db.get(SensorReading, first_reading_id)
        if reading is None or reading.device_id != device.id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Primera lectura invalida.")
    if test_alert_id is not None:
        alert = db.get(Alert, test_alert_id)
        if alert is None or alert.device_id != device.id:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Alerta de prueba invalida.")
    return device


def _json_object(value: str | None) -> dict:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _json_list(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(item) for item in parsed] if isinstance(parsed, list) else []


def _path_value(payload: dict, path: str):
    value = payload
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value
