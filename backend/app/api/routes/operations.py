from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_device_access, require_role, require_storage_unit_access
from app.db.session import get_db
from app.models import IotDevice, IotGateway, Site, User, utc_now
from app.schemas import (
    GatewayDeviceAssignmentIn,
    GatewayOut,
    GatewayUpdate,
    PilotMetricsOut,
    SystemHealthOut,
)
from app.services.audit import record_audit_event
from app.services.pilot_operations import (
    build_pilot_metrics,
    build_system_health,
    gateway_to_out,
    scoped_gateway_query,
)

router = APIRouter(prefix="/admin", dependencies=[Depends(require_role("admin", "technician"))])


@router.get("/system-health", response_model=SystemHealthOut)
def get_system_health(
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> SystemHealthOut:
    return build_system_health(db, current_user)


@router.get("/gateways", response_model=list[GatewayOut])
def list_gateways(
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> list[GatewayOut]:
    gateways = list(db.scalars(scoped_gateway_query(db, current_user).order_by(IotGateway.name)).all())
    return [gateway_to_out(item) for item in gateways]


@router.patch("/gateways/{gateway_id}", response_model=GatewayOut)
def update_gateway(
    gateway_id: int,
    payload: GatewayUpdate,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> GatewayOut:
    gateway = (
        db.get(IotGateway, gateway_id)
        if current_user.role == "admin"
        else db.scalar(scoped_gateway_query(db, current_user).where(IotGateway.id == gateway_id))
    )
    if gateway is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gateway no encontrado.")
    values = payload.model_dump(exclude_unset=True)
    if current_user.role == "technician":
        if set(values) != {"status"} or values["status"] not in {"MAINTENANCE", "UNKNOWN"}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El tecnico solo puede marcar o retirar mantenimiento en gateways asignados.",
            )
    if values.get("site_id") is not None:
        site = db.get(Site, values["site_id"])
        if site is None:
            raise HTTPException(status_code=404, detail="Sitio no encontrado.")
        company_id = values.get("company_id", gateway.company_id)
        if company_id is not None and site.company_id != company_id:
            raise HTTPException(status_code=422, detail="El sitio no pertenece a la empresa seleccionada.")
    if values.get("storage_unit_id") is not None:
        unit = require_storage_unit_access(db, current_user, values["storage_unit_id"])
        company_id = values.get("company_id", gateway.company_id)
        if company_id is not None and unit.company_id != company_id:
            raise HTTPException(status_code=422, detail="La unidad no pertenece a la empresa seleccionada.")
    for key, value in values.items():
        setattr(gateway, key, value)
    gateway.updated_at = utc_now()
    record_audit_event(
        db,
        action="gateway.updated",
        summary=f"Gateway {gateway.gateway_id} actualizado.",
        user=current_user,
        resource_type="iot_gateway",
        resource_id=gateway.id,
        metadata=values,
    )
    db.commit()
    db.refresh(gateway)
    return gateway_to_out(gateway)


@router.post("/gateways/{gateway_id}/assign-devices", response_model=GatewayOut)
def assign_gateway_devices(
    gateway_id: int,
    payload: GatewayDeviceAssignmentIn,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
) -> GatewayOut:
    gateway = db.get(IotGateway, gateway_id)
    if gateway is None:
        raise HTTPException(status_code=404, detail="Gateway no encontrado.")
    requested = set(payload.device_ids)
    for device_id in requested:
        device = require_device_access(db, current_user, device_id)
        if gateway.company_id is not None and device.company_id != gateway.company_id:
            raise HTTPException(status_code=422, detail="Un dispositivo no pertenece a la empresa del gateway.")
    links = list(db.scalars(select(IotDevice).where(IotDevice.device_id.in_(requested))).all()) if requested else []
    if len({item.device_id for item in links}) != len(requested):
        raise HTTPException(status_code=422, detail="Todos los dispositivos deben estar registrados como nodos IoT.")
    current_links = list(db.scalars(select(IotDevice).where(IotDevice.gateway_id == gateway.id)).all())
    for link in current_links:
        if link.device_id not in requested:
            link.gateway_id = None
    for link in links:
        link.gateway_id = gateway.id
    gateway.associated_devices_count = len(requested)
    record_audit_event(
        db,
        action="gateway.devices_assigned",
        summary=f"Asignacion de nodos actualizada para gateway {gateway.gateway_id}.",
        user=current_user,
        resource_type="iot_gateway",
        resource_id=gateway.id,
        metadata={"device_ids": sorted(requested)},
    )
    db.commit()
    db.refresh(gateway)
    return gateway_to_out(gateway)


@router.get("/pilot-metrics", response_model=PilotMetricsOut)
def get_pilot_metrics(
    company_id: int | None = None,
    storage_unit_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    current_user: User = Depends(require_role("admin", "technician")),
    db: Session = Depends(get_db),
) -> PilotMetricsOut:
    end = date_to or utc_now()
    start = date_from or (end - timedelta(days=7))
    if start >= end:
        raise HTTPException(status_code=422, detail="El inicio del periodo debe ser anterior al final.")
    if storage_unit_id is not None:
        require_storage_unit_access(db, current_user, storage_unit_id)
    return build_pilot_metrics(
        db,
        current_user,
        date_from=start,
        date_to=end,
        company_id=company_id,
        storage_unit_id=storage_unit_id,
    )
