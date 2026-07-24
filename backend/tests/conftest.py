import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import encrypt_secret, hash_password, hash_secret
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Company, Device, IotDevice, IotGateway, IotGatewayCredential, Site, StorageUnit, ThresholdConfig, User


@pytest.fixture()
def db_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)

    db = TestingSessionLocal()
    try:
        seed_test_data(db)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture()
def client(db_session: Session) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def seed_test_data(db: Session) -> None:
    company = Company(name="AgroEscudo Demo")
    db.add(company)
    db.flush()

    site = Site(company_id=company.id, name="Centro de Acopio Norte", location="Santa Cruz, Bolivia")
    db.add(site)
    db.flush()

    storage_unit = StorageUnit(
        company_id=company.id,
        site_id=site.id,
        name="Silo Demo 1",
        unit_type="silo",
        capacity_tons=500,
    )
    db.add(storage_unit)
    db.flush()

    device = Device(
        company_id=company.id,
        site_id=site.id,
        storage_unit_id=storage_unit.id,
        external_id="SILO-001",
        name="Sensor Silo 001",
        token_hash=hash_secret("secret-token"),
    )
    db.add(device)
    db.flush()

    gateway_secret = "gateway-secret-001"
    gateway = IotGateway(
        gateway_id="GW-CBBA-001",
        name="Gateway Test",
        firmware_version="1.0.0",
        is_active=True,
    )
    db.add(gateway)
    db.flush()
    db.add(
        IotGatewayCredential(
            gateway_id=gateway.id,
            key_version=1,
            secret_hash=hash_secret(gateway_secret),
            encrypted_secret=encrypt_secret(gateway_secret),
            is_active=True,
        )
    )
    db.add(
        IotDevice(
            node_id=1001,
            device_id=device.id,
            gateway_id=gateway.id,
            key_version=1,
            firmware_version="1.0.0",
            is_active=True,
        )
    )

    admin = User(
        company_id=company.id,
        email="admin@agroescudo.local",
        full_name="Administrador Demo",
        hashed_password=hash_password("admin123"),
        role="admin",
    )
    technician = User(
        company_id=company.id,
        email="tecnico@agroescudo.local",
        full_name="Tecnico AgroEscudo",
        hashed_password=hash_password("tecnico123"),
        role="technician",
    )
    client = User(
        company_id=company.id,
        email="cliente@silo-demo.local",
        full_name="Cliente Silo Demo",
        hashed_password=hash_password("cliente123"),
        role="client",
    )
    db.add_all([admin, technician, client])
    db.flush()
    storage_unit.assigned_technician_id = technician.id
    storage_unit.assigned_client_id = client.id

    db.add_all(
        [
            ThresholdConfig(
                company_id=company.id,
                storage_unit_id=storage_unit.id,
                metric="grain_temperature",
                operator=">",
                value=30.0,
                severity="warning",
            ),
            ThresholdConfig(
                company_id=company.id,
                storage_unit_id=storage_unit.id,
                metric="ambient_humidity",
                operator=">",
                value=70.0,
                severity="warning",
            ),
            ThresholdConfig(
                company_id=company.id,
                storage_unit_id=storage_unit.id,
                metric="battery_voltage",
                operator="<",
                value=3.5,
                severity="technical",
            ),
            ThresholdConfig(
                company_id=company.id,
                storage_unit_id=storage_unit.id,
                metric="critical_temperature",
                operator=">",
                value=30.0,
                severity="critical",
            ),
            ThresholdConfig(
                company_id=company.id,
                storage_unit_id=storage_unit.id,
                metric="critical_humidity",
                operator=">",
                value=70.0,
                severity="critical",
            ),
        ]
    )
    db.commit()
