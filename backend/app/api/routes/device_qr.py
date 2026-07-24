import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_optional_current_user, require_device_access, require_role
from app.db.session import get_db
from app.models import Device, User, utc_now
from app.schemas import DeviceQrOut, DeviceScanOut
from app.services.audit import record_audit_event
from app.services.telemetry import sensor_profile

router = APIRouter()


@router.post("/devices/{device_id}/qr", response_model=DeviceQrOut)
def create_device_qr(
    device_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> DeviceQrOut:
    device = require_device_access(db, current_user, device_id)
    if not device.public_token or device.qr_revoked_at is not None:
        _set_new_token(device)
        record_audit_event(
            db,
            action="device.qr.create",
            summary="QR seguro de dispositivo generado",
            user=current_user,
            resource_type="device",
            resource_id=device.id,
            metadata={"qr_version": device.qr_version},
        )
        db.commit()
        db.refresh(device)
    return _qr_out(device)


@router.post("/devices/{device_id}/qr/rotate", response_model=DeviceQrOut)
def rotate_device_qr(
    device_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> DeviceQrOut:
    device = require_device_access(db, current_user, device_id)
    previous_version = device.qr_version
    _set_new_token(device)
    record_audit_event(
        db,
        action="device.qr.rotate",
        summary="QR seguro de dispositivo rotado",
        user=current_user,
        resource_type="device",
        resource_id=device.id,
        metadata={"previous_version": previous_version, "qr_version": device.qr_version},
    )
    db.commit()
    db.refresh(device)
    return _qr_out(device)


@router.post("/devices/{device_id}/qr/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_device_qr(
    device_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> None:
    device = require_device_access(db, current_user, device_id)
    if not device.public_token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="El dispositivo no tiene QR.")
    device.qr_revoked_at = utc_now()
    record_audit_event(
        db,
        action="device.qr.revoke",
        summary="QR seguro de dispositivo revocado",
        user=current_user,
        resource_type="device",
        resource_id=device.id,
        metadata={"qr_version": device.qr_version},
    )
    db.commit()


@router.get("/devices/scan/{public_token}", response_model=DeviceScanOut)
def scan_device_qr(
    public_token: str,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> DeviceScanOut:
    device = db.scalar(select(Device).where(Device.public_token == public_token))
    if device is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR no reconocido.")
    if device.qr_revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="QR revocado.")
    device.qr_last_scanned_at = utc_now()
    record_audit_event(
        db,
        action="device.qr.scan",
        summary="QR de dispositivo escaneado",
        user=current_user,
        company_id=device.company_id,
        resource_type="device",
        resource_id=device.id,
        metadata={"authenticated": current_user is not None, "qr_version": device.qr_version},
    )
    db.commit()
    profile = sensor_profile(device)
    product_name = "AgroEscudo CampoSensor" if profile == "field_sensor" else "AgroEscudo SiloSensor"
    if current_user is None:
        return DeviceScanOut(
            authenticated=False,
            product_name=product_name,
            device_type=profile,
            qr_version=device.qr_version,
            allowed_actions=["login"],
        )
    require_device_access(db, current_user, device.id)
    actions = ["status", "readings", "alerts", "reports"]
    if current_user.role == "technician":
        actions.extend(["maintenance", "installation", "incidents", "calibration", "diagnostics"])
    elif current_user.role == "admin":
        actions.extend(
            [
                "maintenance",
                "installation",
                "incidents",
                "calibration",
                "diagnostics",
                "qr_management",
            ]
        )
    return DeviceScanOut(
        authenticated=True,
        product_name=product_name,
        device_type=profile,
        qr_version=device.qr_version,
        device_id=device.id,
        storage_unit_id=device.storage_unit_id,
        role=current_user.role,
        allowed_actions=actions,
    )


def _set_new_token(device: Device) -> None:
    device.public_token = secrets.token_urlsafe(32)
    device.qr_version = (device.qr_version or 0) + 1
    device.qr_created_at = utc_now()
    device.qr_revoked_at = None
    device.qr_last_scanned_at = None


def _qr_out(device: Device) -> DeviceQrOut:
    if not device.public_token or not device.qr_created_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="QR no disponible.")
    return DeviceQrOut(
        device_id=device.id,
        public_token=device.public_token,
        qr_version=device.qr_version,
        scan_path=f"/devices/scan/{device.public_token}",
        created_at=device.qr_created_at,
    )
