"""Idempotent bootstrap for a real pilot. Prints newly generated secrets once."""
from __future__ import annotations

import argparse
import secrets
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.security import encrypt_secret, hash_password, hash_secret
from app.db.session import SessionLocal
from app.models import AlertContact, Company, Device, IotDevice, IotGateway, IotGatewayCredential, Site, StorageUnit, User


def args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Crea o reutiliza el árbol completo de un piloto real.")
    p.add_argument("--company-name", required=True)
    p.add_argument("--responsible-name", required=True); p.add_argument("--responsible-email", required=True); p.add_argument("--responsible-phone")
    p.add_argument("--confirm-client-email", action="store_true", help="Autoriza crear/reutilizar la cuenta cliente.")
    p.add_argument("--site-name", required=True); p.add_argument("--site-address", required=True)
    p.add_argument("--unit-name", required=True); p.add_argument("--capacity-tons", required=True, type=float)
    p.add_argument("--technician-name", required=True); p.add_argument("--technician-email", required=True)
    p.add_argument("--device-id", required=True); p.add_argument("--device-name", default="SiloSensor")
    p.add_argument("--gateway-id", required=True); p.add_argument("--gateway-name", default="Gateway")
    p.add_argument("--node-id", required=True, type=int); p.add_argument("--reading-interval-minutes", type=int, default=15)
    p.add_argument("--sentinel-contact", help="Contacto operativo E.164; se crea inactivo y sin consentimiento.")
    p.add_argument("--execute", action="store_true", help="Sin esto solo valida argumentos.")
    return p.parse_args()


def one(db, model, **filters):
    return db.scalar(select(model).filter_by(**filters))


def main() -> None:
    a = args()
    if not a.execute:
        print("VALIDACIÓN OK: agregue --execute para escribir. No se modificaron datos."); return
    generated: dict[str, str] = {}
    with SessionLocal() as db:
        try:
            company = one(db, Company, name=a.company_name) or Company(name=a.company_name, type="early_production", contact_name=a.responsible_name, contact_email=a.responsible_email, contact_phone=a.responsible_phone, is_active=True)
            db.add(company); db.flush()
            site = one(db, Site, company_id=company.id, name=a.site_name) or Site(company_id=company.id, name=a.site_name, address=a.site_address, location=a.site_address, timezone="America/La_Paz")
            db.add(site); db.flush()
            client = one(db, User, email=a.responsible_email.lower()) if a.confirm_client_email else None
            if a.confirm_client_email and not client:
                generated["CLIENT_TEMP_PASSWORD"] = secrets.token_urlsafe(18)
                client = User(company_id=company.id, email=a.responsible_email.lower(), full_name=a.responsible_name, phone_whatsapp=a.responsible_phone, role="client", hashed_password=hash_password(generated["CLIENT_TEMP_PASSWORD"]), status="PASSWORD_CHANGE_REQUIRED")
                db.add(client); db.flush()
            technician = one(db, User, email=a.technician_email.lower())
            if not technician:
                generated["TECHNICIAN_TEMP_PASSWORD"] = secrets.token_urlsafe(18)
                technician = User(email=a.technician_email.lower(), full_name=a.technician_name, role="technician", hashed_password=hash_password(generated["TECHNICIAN_TEMP_PASSWORD"]), status="PASSWORD_CHANGE_REQUIRED")
                db.add(technician); db.flush()
            unit = one(db, StorageUnit, company_id=company.id, site_id=site.id, name=a.unit_name) or StorageUnit(company_id=company.id, site_id=site.id, name=a.unit_name, unit_type="silo", operation_type="storage", capacity_tons=a.capacity_tons, location=a.site_address, is_active=False, pilot_status="PENDING_INSTALLATION")
            unit.assigned_client_id=client.id if client else None; unit.assigned_technician_id=technician.id; db.add(unit); db.flush()
            device = one(db, Device, external_id=a.device_id)
            if not device:
                generated["DEVICE_TOKEN"] = secrets.token_urlsafe(32)
                device = Device(company_id=company.id, site_id=site.id, storage_unit_id=unit.id, external_id=a.device_id, name=a.device_name, token_hash=hash_secret(generated["DEVICE_TOKEN"]), device_type="silo_sensor", model_version="v4", expected_reading_interval_minutes=a.reading_interval_minutes, operational_status="commissioning", is_active=False)
                db.add(device); db.flush()
            gateway = one(db, IotGateway, gateway_id=a.gateway_id) or IotGateway(company_id=company.id, site_id=site.id, storage_unit_id=unit.id, gateway_id=a.gateway_id, name=a.gateway_name, status="UNKNOWN", internet_status="unknown", is_active=False)
            db.add(gateway); db.flush()
            if not one(db, IotGatewayCredential, gateway_id=gateway.id):
                generated["GATEWAY_SECRET"] = secrets.token_urlsafe(32)
                db.add(IotGatewayCredential(gateway_id=gateway.id, key_version=1, secret_hash=hash_secret(generated["GATEWAY_SECRET"]), encrypted_secret=encrypt_secret(generated["GATEWAY_SECRET"])))
            link = one(db, IotDevice, device_id=device.id)
            if not link:
                db.add(IotDevice(node_id=a.node_id, device_id=device.id, gateway_id=gateway.id, firmware_version="4", is_active=False))
            if a.sentinel_contact and not one(db, AlertContact, company_id=company.id, storage_unit_id=unit.id, phone_e164=a.sentinel_contact):
                admin = db.scalar(select(User).where(User.role == "admin", User.deleted_at.is_(None)).order_by(User.id))
                if not admin:
                    raise RuntimeError("Se requiere un administrador existente para registrar el contacto Sentinel")
                db.add(AlertContact(company_id=company.id, storage_unit_id=unit.id, name="Sentinel AgroEscudo", phone_e164=a.sentinel_contact, priority=1, receive_sms=False, receive_call=False, active=False, created_by_user_id=admin.id))
            db.commit()
        except Exception:
            db.rollback(); raise
        print(f"COMPANY_ID={company.id}\nSITE_ID={site.id}\nSTORAGE_UNIT_ID={unit.id}\nPILOT_STATUS={unit.pilot_status}\nDEVICE_DB_ID={device.id}\nDEVICE_ID={device.external_id}\nGATEWAY_DB_ID={gateway.id}\nGATEWAY_ID={gateway.gateway_id}\nAPI_BASE_URL=https://agroescudo-api.onrender.com\nFIRMWARE_PROTOCOL=v4\nREADING_INTERVAL_MINUTES={a.reading_interval_minutes}")
        if generated:
            print("SECRETOS NUEVOS (MOSTRAR/GUARDAR AHORA; NO SE RECUPERAN EN OTRA EJECUCIÓN):")
            for key, value in generated.items(): print(f"{key}={value}")
        else: print("Ejecución idempotente: no se generaron secretos nuevos.")


if __name__ == "__main__":
    main()
