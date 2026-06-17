from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import hash_password, hash_secret
from app.db.session import SessionLocal
from app.models import Alert, Company, Device, NotificationPreference, OperationalLog, SensorReading, Site, StorageUnit, ThresholdConfig, User

DEMO_COMPANY = "Acopio Valle Bajo S.R.L."
DEMO_SITE = "Centro de Acopio Norte"


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
        )
        technician = _ensure_user(
            db,
            company.id,
            email="tecnico@agroescudo.local",
            full_name="Técnico AgroEscudo",
            password="tecnico123",
            role="technician",
        )
        client = _ensure_user(
            db,
            company.id,
            email="cliente@silo-demo.local",
            full_name="Responsable de Operaciones",
            password="cliente123",
            role="client",
        )
        site = _ensure_site(db, company.id)

        demo_assets = [
            ("Silo Maíz Seco 01", "silo", 500.0, "SILO-001", "Nodo Silo Maíz 001", "secret-token"),
            ("Galpón Sorgo 02", "galpón", 300.0, "GALPON-001", "Nodo Galpón Sorgo 001", "secret-token-galpon-001"),
            ("Almacén Balanceado 03", "almacén", 150.0, "SILO-002", "Nodo Almacén Balanceado 002", "secret-token-silo-002"),
        ]
        assets: dict[str, tuple[StorageUnit, Device]] = {}
        for name, unit_type, capacity, external_id, device_name, device_token in demo_assets:
            storage_unit, device = _ensure_asset(
                db,
                company,
                site,
                technician,
                client,
                name=name,
                unit_type=unit_type,
                capacity_tons=capacity,
                external_id=external_id,
                device_name=device_name,
                device_token=device_token,
            )
            assets[external_id] = (storage_unit, device)
            _ensure_thresholds(db, company.id, storage_unit.id)

        _remove_legacy_informal_logs(db, company.id)
        for user in [technician, client]:
            _ensure_notification_preferences(db, user)
        anchor = _demo_anchor()
        readings = _ensure_historical_readings(db, assets, anchor)
        _ensure_demo_alerts(db, company, site, assets, readings, anchor)
        _ensure_demo_logs(db, company, site, technician, assets, anchor)

        db.commit()
        print(
            "Seed data ready: Acopio Valle Bajo S.R.L., 3 storage units, "
            "3 devices, 7 days of readings, alerts, maintenance and demo users"
        )
    finally:
        db.close()


def _ensure_company(db: Session) -> Company:
    company = db.scalar(select(Company).where(Company.name == DEMO_COMPANY))
    if company is None:
        company = db.scalar(select(Company).where(Company.name == "AgroEscudo Demo"))
    if company is None:
        company = Company(name=DEMO_COMPANY, tax_id="VALLE-BAJO-DEMO")
        db.add(company)
    else:
        company.name = DEMO_COMPANY
        company.tax_id = "VALLE-BAJO-DEMO"
    db.flush()
    return company


def _ensure_site(db: Session, company_id: int) -> Site:
    site = db.scalar(select(Site).where(Site.company_id == company_id, Site.name == DEMO_SITE))
    if site is None:
        site = Site(company_id=company_id, name=DEMO_SITE, location="Quillacollo, Cochabamba")
        db.add(site)
    else:
        site.location = "Quillacollo, Cochabamba"
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
    external_id: str,
    device_name: str,
    device_token: str,
) -> tuple[StorageUnit, Device]:
    device = db.scalar(select(Device).where(Device.external_id == external_id))
    storage_unit = db.get(StorageUnit, device.storage_unit_id) if device else None
    if storage_unit is None:
        storage_unit = db.scalar(select(StorageUnit).where(StorageUnit.site_id == site.id, StorageUnit.name == name))
    if storage_unit is None and external_id == "SILO-001":
        storage_unit = db.scalar(select(StorageUnit).where(StorageUnit.site_id == site.id, StorageUnit.name == "Silo Demo 1"))
    if storage_unit is None:
        storage_unit = StorageUnit(company_id=company.id, site_id=site.id, name=name, unit_type=unit_type)
        db.add(storage_unit)

    storage_unit.company_id = company.id
    storage_unit.site_id = site.id
    storage_unit.name = name
    storage_unit.unit_type = unit_type
    storage_unit.capacity_tons = capacity_tons
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
    else:
        device.company_id = company.id
        device.site_id = site.id
        device.storage_unit_id = storage_unit.id
        device.name = device_name
        device.token_hash = hash_secret(device_token)
        device.is_active = True
    db.flush()
    return storage_unit, device


def _ensure_historical_readings(
    db: Session,
    assets: dict[str, tuple[StorageUnit, Device]],
    anchor: datetime,
) -> dict[str, list[SensorReading]]:
    readings: dict[str, list[SensorReading]] = {}
    for external_id, (storage_unit, device) in assets.items():
        unit_readings: list[SensorReading] = []
        for index in range(29):
            timestamp = anchor - timedelta(hours=(28 - index) * 6)
            metrics = _reading_metrics(external_id, index)
            reading = db.scalar(
                select(SensorReading).where(
                    SensorReading.device_id == device.id,
                    SensorReading.timestamp == timestamp,
                )
            )
            if reading is None:
                reading = SensorReading(
                    company_id=device.company_id,
                    site_id=device.site_id,
                    storage_unit_id=device.storage_unit_id,
                    device_id=device.id,
                    timestamp=timestamp,
                    received_at=timestamp + timedelta(minutes=2),
                    **metrics,
                )
                db.add(reading)
            else:
                for field, value in metrics.items():
                    setattr(reading, field, value)
            unit_readings.append(reading)
        db.flush()
        readings[external_id] = unit_readings
    return readings


def _reading_metrics(external_id: str, index: int) -> dict[str, float | int]:
    cycle = index % 6
    metrics: dict[str, float | int] = {
        "grain_temperature": round(24.2 + cycle * 0.55, 1),
        "ambient_temperature": round(22.8 + cycle * 0.7, 1),
        "ambient_humidity": round(57.0 + cycle * 1.8, 1),
        "battery_voltage": round(3.95 - index * 0.005, 2),
        "signal_quality": -61 - cycle * 2,
    }
    if external_id == "SILO-001":
        if index == 22:
            metrics.update(grain_temperature=31.2, ambient_temperature=27.5, ambient_humidity=67.4)
        if index == 25:
            metrics.update(grain_temperature=28.7, ambient_temperature=27.1, ambient_humidity=72.8)
        if index == 28:
            metrics.update(grain_temperature=34.6, ambient_temperature=29.2, ambient_humidity=80.4)
    elif external_id == "GALPON-001":
        if index >= 26:
            metrics.update(grain_temperature=27.7 + (index - 26) * 0.35, ambient_humidity=72.4 + (index - 26) * 1.5)
    elif external_id == "SILO-002" and index == 28:
        metrics.update(battery_voltage=3.34, signal_quality=-78)
    return metrics


def _ensure_demo_alerts(
    db: Session,
    company: Company,
    site: Site,
    assets: dict[str, tuple[StorageUnit, Device]],
    readings: dict[str, list[SensorReading]],
    anchor: datetime,
) -> None:
    specs = [
        ("SILO-001", 22, "grain_temperature_high", "warning", "Temperatura de grano elevada", "La temperatura de grano superó el umbral configurado.", False, anchor - timedelta(hours=30)),
        ("SILO-001", 25, "ambient_humidity_high", "warning", "Humedad ambiental elevada", "La humedad ambiental superó el umbral configurado.", False, anchor - timedelta(hours=12)),
        ("SILO-001", 28, "critical_environment", "critical", "Riesgo crítico de conservación", "Temperatura de grano y humedad ambiental superan los umbrales configurados.", True, None),
        ("GALPON-001", 28, "ambient_humidity_high", "warning", "Humedad ambiental elevada", "La humedad ambiental supera el umbral configurado.", True, None),
        ("SILO-002", 28, "battery_low", "technical", "Batería baja del dispositivo", "El voltaje de batería está por debajo del umbral configurado.", True, None),
    ]
    for external_id, reading_index, alert_type, severity, title, message, is_active, resolved_at in specs:
        storage_unit, device = assets[external_id]
        reading = readings[external_id][reading_index]
        alert = db.scalar(select(Alert).where(Alert.device_id == device.id, Alert.reading_id == reading.id, Alert.alert_type == alert_type))
        if alert is None:
            alert = Alert(
                company_id=company.id,
                site_id=site.id,
                storage_unit_id=storage_unit.id,
                device_id=device.id,
                reading_id=reading.id,
                alert_type=alert_type,
                severity=severity,
                title=title,
                message=message,
                created_at=reading.timestamp,
            )
            db.add(alert)
        alert.severity = severity
        alert.title = title
        alert.message = message
        alert.is_active = is_active
        alert.resolved_at = resolved_at
        alert.acknowledged_at = resolved_at


def _ensure_demo_logs(
    db: Session,
    company: Company,
    site: Site,
    technician: User,
    assets: dict[str, tuple[StorageUnit, Device]],
    anchor: datetime,
) -> None:
    specs = [
        ("SILO-001", "installation", "Instalación inicial del nodo IoT.", "Se instaló y validó el nodo en el punto definido para monitoreo continuo.", -168),
        ("GALPON-001", "installation", "Instalación inicial del nodo IoT.", "Se verificó fijación, conectividad y primera lectura del dispositivo.", -164),
        ("SILO-002", "installation", "Instalación inicial del nodo IoT.", "Se registró instalación inicial y disponibilidad operativa del nodo.", -160),
        ("SILO-001", "inspection", "Se verificó ventilación del área monitoreada.", "La inspección confirmó circulación de aire y ausencia de obstrucciones visibles.", -34),
        ("SILO-001", "corrective_action", "Se activó aireación preventiva durante 30 minutos.", "Acción preventiva aplicada ante incremento térmico observado en la serie de lecturas.", -28),
        ("SILO-002", "maintenance", "Se revisó estado de batería y conexión del nodo.", "Se programó recambio preventivo de batería y se verificó enlace de comunicación.", -20),
        ("SILO-001", "inspection", "Se inspeccionó físicamente el punto de monitoreo.", "Se revisó el área de almacenamiento y se confirmó la necesidad de seguimiento operativo.", -10),
        ("GALPON-001", "inspection", "Se validó lectura con revisión operativa del almacenamiento.", "La lectura fue contrastada con una revisión visual del galpón.", -8),
        ("SILO-002", "maintenance", "Revisión de batería del nodo.", "Se verificó voltaje reportado y se dejó recomendación de recambio preventivo.", -18),
        ("GALPON-001", "maintenance", "Revisión de conectividad del nodo.", "Se comprobó intensidad de señal y continuidad de transmisión.", -16),
        ("SILO-001", "maintenance", "Limpieza de caja de protección.", "Se retiró polvo superficial y se verificó el cierre de la caja del dispositivo.", -14),
        ("SILO-001", "maintenance", "Validación del sensor de temperatura.", "Se contrastó la lectura del sensor con inspección operativa del punto monitoreado.", -12),
    ]
    for external_id, category, action_taken, notes, hours_delta in specs:
        storage_unit, device = assets[external_id]
        timestamp = anchor + timedelta(hours=hours_delta)
        log = db.scalar(
            select(OperationalLog).where(
                OperationalLog.storage_unit_id == storage_unit.id,
                OperationalLog.category == category,
                OperationalLog.action_taken == action_taken,
                OperationalLog.timestamp == timestamp,
            )
        )
        if log is None:
            db.add(
                OperationalLog(
                    company_id=company.id,
                    site_id=site.id,
                    storage_unit_id=storage_unit.id,
                    device_id=device.id,
                    user_id=technician.id,
                    category=category,
                    action_taken=action_taken,
                    operator_name=technician.full_name,
                    notes=notes,
                    timestamp=timestamp,
                )
            )


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


def _ensure_user(db: Session, company_id: int, email: str, full_name: str, password: str, role: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(company_id=company_id, email=email, full_name=full_name, hashed_password="", role=role)
        db.add(user)
    user.company_id = company_id
    user.full_name = full_name
    user.hashed_password = hash_password(password)
    user.role = role
    user.is_active = True
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
        if preference.destination is None and channel == "telegram":
            preference.destination = ""
        preference.enabled = False


def _remove_legacy_informal_logs(db: Session, company_id: int) -> None:
    db.execute(
        delete(OperationalLog).where(
            OperationalLog.company_id == company_id,
            OperationalLog.action_taken.in_(["ARREGLAR", "Checklist de instalacion registrado"]),
        )
    )


def _demo_anchor() -> datetime:
    now = datetime.now(timezone.utc)
    return now.replace(hour=(now.hour // 6) * 6, minute=0, second=0, microsecond=0)


if __name__ == "__main__":
    seed()
