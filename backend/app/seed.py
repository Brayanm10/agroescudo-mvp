import os

from sqlalchemy import delete, select

from app.core.config import settings
from sqlalchemy.orm import Session

from app.core.security import encrypt_secret, hash_password, hash_secret
from app.db.session import SessionLocal
from app.models import (
    Alert,
    Company,
    Device,
    EducationArticle,
    IotDevice,
    IotGateway,
    IotGatewayCredential,
    IotGatewayHealth,
    IotIngestionBatch,
    IotIngestionEvent,
    IotReading,
    NotificationDelivery,
    NotificationEvent,
    NotificationPreference,
    OperationalLog,
    PushDeviceToken,
    SensorReading,
    Site,
    StorageUnit,
    ThresholdConfig,
    User,
)

PILOT_COMPANY = "Acopio Valle Bajo S.R.L."
PILOT_SITE = "Centro de Acopio Norte"
CLIENT_EMAIL = "operaciones@vallebajo.bo"


def seed() -> None:
    db = SessionLocal()
    try:
        company = _ensure_company(db)
        _ensure_user(
            db,
            company.id,
            email="admin@agroescudo.local",
            full_name="Administrador AgroEscudo",
            password="admin123",
            role="admin",
            receives_alerts=False,
        )
        technician = _ensure_user(
            db,
            company.id,
            email="tecnico@agroescudo.local",
            full_name="Tecnico AgroEscudo",
            password="tecnico123",
            role="technician",
            phone_whatsapp="+59170000001",
            telegram_chat_id="100001",
        )
        client = _ensure_user(
            db,
            company.id,
            email=CLIENT_EMAIL,
            full_name="Responsable de Operaciones",
            password="cliente123",
            role="client",
            phone_whatsapp="+59170000002",
            telegram_chat_id="100002",
        )
        site = _ensure_site(db, company.id)

        demo_assets = [
            ("Silo Maiz Seco 01", "silo", 500.0, "Maiz seco", "Sector norte - bateria 1", "SILO-001", "Nodo Silo Maiz 001", "secret-token"),
            ("Galpon Sorgo 02", "galpon", 300.0, "Sorgo", "Galpon ventilado - ala este", "GALPON-001", "Nodo Galpon Sorgo 001", "secret-token-galpon-001"),
            ("Almacen Balanceado 03", "almacen", 150.0, "Alimento balanceado", "Almacen cerrado - zona despacho", "SILO-002", "Nodo Almacen Balanceado 002", "secret-token-silo-002"),
        ]
        assets: dict[str, tuple[StorageUnit, Device]] = {}
        for name, unit_type, capacity, crop_type, location, external_id, device_name, device_token in demo_assets:
            storage_unit, device = _ensure_asset(
                db,
                company,
                site,
                technician,
                client,
                name=name,
                unit_type=unit_type,
                capacity_tons=capacity,
                crop_type=crop_type,
                location=location,
                external_id=external_id,
                device_name=device_name,
                device_token=device_token,
            )
            assets[external_id] = (storage_unit, device)
            _ensure_thresholds(db, company.id, storage_unit.id)

        for user in [technician, client]:
            _ensure_notification_preferences(db, user)
        _ensure_education_articles(db)
        _ensure_iot_gateway(db)
        _ensure_iot_devices(db, assets)
        if os.getenv("RESET_OPERATIONAL_DATA_ON_SEED", "false").lower() == "true":
            _clear_seeded_operational_data(db, company.id)

        db.commit()
        print(
            "Pilot base ready: Acopio Valle Bajo S.R.L., 3 storage units, "
            "3 devices, users and thresholds. Existing operational data was preserved."
        )
    finally:
        db.close()


def _ensure_company(db: Session) -> Company:
    company = db.scalar(select(Company).where(Company.name == PILOT_COMPANY))
    if company is None:
        company = Company(name=PILOT_COMPANY, tax_id="VALLE-BAJO")
        db.add(company)
    company.name = PILOT_COMPANY
    company.tax_id = "VALLE-BAJO"
    company.type = "acopiador"
    company.city = "Quillacollo, Cochabamba"
    company.contact_name = "Gerencia Operativa"
    company.contact_email = "operaciones@vallebajo.bo"
    company.contact_phone = "+59170000000"
    company.is_active = True
    company.approval_status = "APPROVED"
    company.rejection_reason = None
    db.flush()
    return company


def _ensure_site(db: Session, company_id: int) -> Site:
    site = db.scalar(select(Site).where(Site.company_id == company_id, Site.name == PILOT_SITE))
    if site is None:
        site = Site(company_id=company_id, name=PILOT_SITE, location="Quillacollo, Cochabamba")
        db.add(site)
    else:
        site.location = "Quillacollo, Cochabamba"
    site.address = "Zona norte de Quillacollo"
    site.department = "Cochabamba"
    site.municipality = "Quillacollo"
    site.timezone = "America/La_Paz"
    db.flush()
    return site


def _ensure_asset(
    db: Session,
    company: Company,
    site: Site,
    technician: User,
    client: User,
    *,
    name: str,
    unit_type: str,
    capacity_tons: float,
    crop_type: str,
    location: str,
    external_id: str,
    device_name: str,
    device_token: str,
) -> tuple[StorageUnit, Device]:
    device = db.scalar(select(Device).where(Device.external_id == external_id))
    storage_unit = db.get(StorageUnit, device.storage_unit_id) if device else None
    if storage_unit is None:
        storage_unit = db.scalar(select(StorageUnit).where(StorageUnit.site_id == site.id, StorageUnit.name == name))
    if storage_unit is None:
        storage_unit = StorageUnit(company_id=company.id, site_id=site.id, name=name, unit_type=unit_type)
        db.add(storage_unit)

    storage_unit.company_id = company.id
    storage_unit.site_id = site.id
    storage_unit.name = name
    storage_unit.unit_type = unit_type
    storage_unit.capacity_tons = capacity_tons
    storage_unit.crop_type = crop_type
    storage_unit.location = location
    storage_unit.is_active = True
    storage_unit.assigned_technician_id = technician.id
    storage_unit.assigned_client_id = client.id
    db.flush()

    if device is None:
        device = Device(
            company_id=company.id,
            site_id=site.id,
            storage_unit_id=storage_unit.id,
            external_id=external_id,
            name=device_name,
            token_hash=hash_secret(device_token),
        )
        db.add(device)
    device.company_id = company.id
    device.site_id = site.id
    device.storage_unit_id = storage_unit.id
    device.name = device_name
    device.token_hash = hash_secret(device_token)
    device.device_type = "esp32_lora_wifi_node"
    device.is_active = True
    db.flush()
    return storage_unit, device


def _ensure_thresholds(db: Session, company_id: int, storage_unit_id: int) -> None:
    specs = [
        ("grain_temperature", ">", 30.0, "warning"),
        ("ambient_humidity", ">", 70.0, "warning"),
        ("battery_voltage", "<", 3.5, "technical"),
        ("critical_temperature", ">", 32.0, "critical"),
        ("critical_humidity", ">", 75.0, "critical"),
    ]
    for metric, operator, value, severity in specs:
        threshold = db.scalar(
            select(ThresholdConfig).where(
                ThresholdConfig.company_id == company_id,
                ThresholdConfig.storage_unit_id == storage_unit_id,
                ThresholdConfig.metric == metric,
            )
        )
        if threshold is None:
            threshold = ThresholdConfig(company_id=company_id, storage_unit_id=storage_unit_id, metric=metric)
            db.add(threshold)
        threshold.operator = operator
        threshold.value = value
        threshold.severity = severity
        threshold.is_active = True


def _ensure_iot_gateway(db: Session) -> IotGateway:
    gateway = db.scalar(select(IotGateway).where(IotGateway.gateway_id == "GW-CBBA-001"))
    if gateway is None:
        gateway = IotGateway(gateway_id="GW-CBBA-001", name="Gateway Centro de Acopio Norte")
        db.add(gateway)
        db.flush()
    gateway.name = "Gateway Centro de Acopio Norte"
    gateway.firmware_version = "1.0.0"
    gateway.is_active = True

    secret = os.getenv("AGRO_SEED_GATEWAY_SECRET") or hash_secret(f"{settings.secret_key}:GW-CBBA-001")[:48]
    credential = db.scalar(
        select(IotGatewayCredential).where(
            IotGatewayCredential.gateway_id == gateway.id,
            IotGatewayCredential.key_version == 1,
        )
    )
    if credential is None:
        credential = IotGatewayCredential(gateway_id=gateway.id, key_version=1, secret_hash="", encrypted_secret="")
        db.add(credential)
    credential.secret_hash = hash_secret(secret)
    credential.encrypted_secret = encrypt_secret(secret)
    credential.is_active = True
    credential.revoked_at = None
    db.flush()
    return gateway


def _ensure_iot_devices(db: Session, assets: dict[str, tuple[StorageUnit, Device]]) -> None:
    node_ids = {
        "SILO-001": 1001,
        "GALPON-001": 1002,
        "SILO-002": 1003,
    }
    for external_id, node_id in node_ids.items():
        _storage_unit, device = assets[external_id]
        iot_device = db.scalar(select(IotDevice).where(IotDevice.node_id == node_id))
        if iot_device is None:
            iot_device = IotDevice(node_id=node_id, device_id=device.id)
            db.add(iot_device)
        iot_device.device_id = device.id
        iot_device.key_version = 1
        iot_device.firmware_version = "1.0.0"
        iot_device.is_active = True


def _ensure_user(
    db: Session,
    company_id: int,
    email: str,
    full_name: str,
    password: str,
    role: str,
    phone_whatsapp: str | None = None,
    telegram_chat_id: str | None = None,
    receives_alerts: bool = True,
) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(company_id=company_id, email=email, full_name=full_name, hashed_password="", role=role)
        db.add(user)
    user.company_id = company_id
    user.full_name = full_name
    user.hashed_password = hash_password(password)
    user.role = role
    user.is_active = True
    user.status = "ACTIVE"
    user.locale = "es"
    user.language = "es"
    user.phone_whatsapp = phone_whatsapp
    user.telegram_chat_id = telegram_chat_id
    user.receives_alerts = receives_alerts
    db.flush()
    return user


def _ensure_notification_preferences(db: Session, user: User) -> None:
    for channel in ["whatsapp", "telegram", "push"]:
        preference = db.scalar(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user.id,
                NotificationPreference.channel == channel,
            )
        )
        if preference is None:
            preference = NotificationPreference(company_id=user.company_id, user_id=user.id, channel=channel)
            db.add(preference)
        preference.company_id = user.company_id
        preference.minimum_severity = "critical"
        if channel == "whatsapp":
            preference.destination = user.phone_whatsapp
        elif channel == "telegram":
            preference.destination = user.telegram_chat_id
        preference.enabled = bool(user.receives_alerts and preference.destination and channel in {"whatsapp", "telegram"})


def _ensure_education_articles(db: Session) -> None:
    articles = [
        (
            "temperatura-alta-postcosecha",
            "Temperatura alta en grano almacenado",
            "Como interpretar incrementos termicos y que acciones registrar.",
            "Una temperatura de grano fuera de rango puede indicar acumulacion termica, mala aireacion o actividad biologica. Verifica el punto monitoreado, compara con lecturas historicas y registra toda accion correctiva.",
            "alertas",
        ),
        (
            "humedad-alta-ventilacion",
            "Humedad alta y ventilacion",
            "Criterios practicos para revisar aireacion y condensacion.",
            "La humedad ambiente elevada incrementa el riesgo de deterioro postcosecha. Revisa ventilacion, puntos de condensacion, sellos del galpon y condicion del grano cercano al sensor.",
            "postcosecha",
        ),
        (
            "bitacora-evidencia-operativa",
            "Bitacora como evidencia operativa",
            "Buenas practicas para documentar acciones tecnicas.",
            "Una bitacora clara permite demostrar trazabilidad: quien intervino, que se hizo, en que silo, a que hora y con que resultado. Evita textos informales cuando el reporte sera entregado a cliente externo.",
            "operacion",
        ),
    ]
    for slug, title, summary, body, category in articles:
        article = db.scalar(select(EducationArticle).where(EducationArticle.slug == slug))
        if article is None:
            article = EducationArticle(slug=slug, locale="es", title=title, summary=summary, body=body, category=category)
            db.add(article)
        article.locale = "es"
        article.title = title
        article.summary = summary
        article.body = body
        article.category = category
        article.translation_status = "VERIFIED"
        article.is_published = True


def _clear_seeded_operational_data(db: Session, company_id: int) -> None:
    user_ids = list(db.scalars(select(User.id).where(User.company_id == company_id)).all())
    alert_ids = list(db.scalars(select(Alert.id).where(Alert.company_id == company_id)).all())
    storage_unit_ids = list(db.scalars(select(StorageUnit.id).where(StorageUnit.company_id == company_id)).all())

    if alert_ids:
        db.execute(delete(NotificationDelivery).where(NotificationDelivery.alert_id.in_(alert_ids)))
    if user_ids:
        db.execute(delete(NotificationDelivery).where(NotificationDelivery.user_id.in_(user_ids)))
        db.execute(delete(PushDeviceToken).where(PushDeviceToken.user_id.in_(user_ids)))

    gateway_ids = list(db.scalars(select(IotGateway.id)).all())
    if gateway_ids:
        db.execute(delete(IotGatewayHealth).where(IotGatewayHealth.gateway_id.in_(gateway_ids)))
        db.execute(delete(IotIngestionEvent).where(IotIngestionEvent.gateway_id.in_(gateway_ids)))
        db.execute(delete(IotReading).where(IotReading.gateway_id.in_(gateway_ids)))
        db.execute(delete(IotIngestionBatch).where(IotIngestionBatch.gateway_id.in_(gateway_ids)))

    db.execute(delete(NotificationEvent).where(NotificationEvent.company_id == company_id))
    db.execute(delete(OperationalLog).where(OperationalLog.company_id == company_id))
    db.execute(delete(Alert).where(Alert.company_id == company_id))
    db.execute(delete(SensorReading).where(SensorReading.company_id == company_id))

    if storage_unit_ids:
        for storage_unit in db.scalars(select(StorageUnit).where(StorageUnit.id.in_(storage_unit_ids))).all():
            storage_unit.last_report_generated_at = None
    for device in db.scalars(select(Device).where(Device.company_id == company_id)).all():
        device.last_seen_at = None

if __name__ == "__main__":
    seed()
