from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app import seed as seed_module
from app.core.security import hash_password, verify_password
from app.models import Alert, Company, Device, NotificationDelivery, NotificationPreference, OperationalLog, PushDeviceToken, SensorReading, Site, StorageUnit, User


def valid_payload(**overrides):
    payload = {
        "device_id": "SILO-001",
        "device_token": "secret-token",
        "grain_temperature": 28.5,
        "ambient_temperature": 27.2,
        "ambient_humidity": 65.1,
        "battery_voltage": 3.91,
        "signal_quality": -67,
        "timestamp": "2026-05-26T20:00:00Z",
    }
    payload.update(overrides)
    return payload


def auth_headers(client, email="admin@agroescudo.local", password="admin123"):
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def create_alert(client):
    response = client.post(
        "/api/readings",
        json=valid_payload(
            grain_temperature=31.5,
            ambient_humidity=72.1,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )
    assert response.status_code == 201
    return response.json()["alerts"][0]


def test_login_correct(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@agroescudo.local", "password": "admin123"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"
    assert response.json()["access_token"]


def test_login_technician_and_client_roles(client):
    technician_headers = auth_headers(client, "tecnico@agroescudo.local", "tecnico123")
    technician_me = client.get("/api/me", headers=technician_headers)
    assert technician_me.status_code == 200
    assert technician_me.json()["role"] == "technician"

    client_headers = auth_headers(client, "cliente@silo-demo.local", "cliente123")
    client_me = client.get("/api/me", headers=client_headers)
    assert client_me.status_code == 200
    assert client_me.json()["role"] == "client"


def test_me_returns_admin_role(client):
    response = client.get("/api/me", headers=auth_headers(client))

    assert response.status_code == 200
    assert response.json()["email"] == "admin@agroescudo.local"
    assert response.json()["role"] == "admin"
    assert response.json()["is_active"] is True
    assert "created_at" in response.json()
    assert "last_login_at" in response.json()


def test_login_updates_last_login_at(client, db_session):
    user = db_session.scalar(select(User).where(User.email == "admin@agroescudo.local"))
    assert user.last_login_at is None

    response = client.post(
        "/api/auth/login",
        json={"email": "admin@agroescudo.local", "password": "admin123"},
    )

    assert response.status_code == 200
    db_session.refresh(user)
    assert user.last_login_at is not None


def test_update_me_allows_only_profile_fields(client):
    headers = auth_headers(client)
    response = client.patch(
        "/api/me",
        headers=headers,
        json={
            "full_name": "Administrador Operativo",
            "phone_whatsapp": "+59170000001",
            "telegram_chat_id": "12345",
            "receives_alerts": False,
            "timezone": "America/La_Paz",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Administrador Operativo"
    assert body["phone_whatsapp"] == "+59170000001"
    assert body["receives_alerts"] is False
    assert body["role"] == "admin"


def test_update_me_rejects_role_change(client):
    response = client.patch(
        "/api/me",
        headers=auth_headers(client),
        json={"role": "client"},
    )

    assert response.status_code == 422


def test_change_password_wrong_current_password(client):
    response = client.post(
        "/api/auth/change-password",
        headers=auth_headers(client),
        json={
            "current_password": "incorrecta",
            "new_password": "Nueva123",
            "confirm_password": "Nueva123",
        },
    )

    assert response.status_code == 400


def test_change_password_rejects_weak_password(client):
    response = client.post(
        "/api/auth/change-password",
        headers=auth_headers(client),
        json={
            "current_password": "admin123",
            "new_password": "debil",
            "confirm_password": "debil",
        },
    )

    assert response.status_code == 422


def test_change_password_rejects_confirmation_mismatch(client):
    response = client.post(
        "/api/auth/change-password",
        headers=auth_headers(client),
        json={
            "current_password": "admin123",
            "new_password": "Nueva123",
            "confirm_password": "Otra1234",
        },
    )

    assert response.status_code == 400


def test_change_password_success(client):
    response = client.post(
        "/api/auth/change-password",
        headers=auth_headers(client),
        json={
            "current_password": "admin123",
            "new_password": "Nueva123",
            "confirm_password": "Nueva123",
        },
    )
    assert response.status_code == 200

    old_login = client.post("/api/auth/login", json={"email": "admin@agroescudo.local", "password": "admin123"})
    new_login = client.post("/api/auth/login", json={"email": "admin@agroescudo.local", "password": "Nueva123"})
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_seed_is_idempotent_and_leaves_pilot_operational_data_clean(client, db_session, monkeypatch):
    admin = db_session.scalar(select(User).where(User.email == "admin@agroescudo.local"))
    admin.hashed_password = hash_password("old-password")
    admin.role = "client"
    admin.is_active = False
    db_session.commit()

    monkeypatch.setattr(seed_module, "SessionLocal", lambda: db_session)
    seed_module.seed()
    counts_after_first_seed = (
        db_session.scalar(select(func.count(StorageUnit.id))),
        db_session.scalar(select(func.count(Device.id))),
        db_session.scalar(select(func.count(SensorReading.id))),
        db_session.scalar(select(func.count(OperationalLog.id))),
    )
    seed_module.seed()
    counts_after_second_seed = (
        db_session.scalar(select(func.count(StorageUnit.id))),
        db_session.scalar(select(func.count(Device.id))),
        db_session.scalar(select(func.count(SensorReading.id))),
        db_session.scalar(select(func.count(OperationalLog.id))),
    )

    pilot_users = db_session.scalars(
        select(User).where(
            User.email.in_(
                [
                    "admin@agroescudo.local",
                    "tecnico@agroescudo.local",
                    "operaciones@vallebajo.bo",
                ]
            )
        )
    ).all()
    users = {user.email: user for user in pilot_users}

    assert len(pilot_users) == 3
    assert len(users) == 3
    assert users["admin@agroescudo.local"].role == "admin"
    assert users["tecnico@agroescudo.local"].role == "technician"
    assert users["operaciones@vallebajo.bo"].role == "client"
    assert users["admin@agroescudo.local"].is_active is True
    assert verify_password("admin123", users["admin@agroescudo.local"].hashed_password)
    assert verify_password("tecnico123", users["tecnico@agroescudo.local"].hashed_password)
    assert verify_password("cliente123", users["operaciones@vallebajo.bo"].hashed_password)
    assert counts_after_first_seed == counts_after_second_seed
    assert counts_after_second_seed[0] == 3
    assert counts_after_second_seed[1] == 3
    assert counts_after_second_seed[2] == 0
    assert counts_after_second_seed[3] == 0


def test_login_works_with_sqlite_test_database(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@agroescudo.local", "password": "admin123"},
    )

    assert response.status_code == 200
    assert response.json()["token_type"] == "bearer"


def test_health_db_reports_sqlite(client):
    response = client.get("/api/health/db")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "sqlite"


def test_login_incorrect(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@agroescudo.local", "password": "bad-password"},
    )

    assert response.status_code == 401


def test_inactive_user_gets_clean_login_error(client, db_session):
    user = db_session.scalar(select(User).where(User.email == "cliente@silo-demo.local"))
    user.is_active = False
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": "cliente@silo-demo.local", "password": "cliente123"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Usuario desactivado. Contacta al administrador."


def test_list_companies(client):
    response = client.get("/api/companies", headers=auth_headers(client))

    assert response.status_code == 200
    assert response.json()[0]["name"] == "AgroEscudo Demo"


def test_list_devices_does_not_expose_token(client):
    response = client.get("/api/devices", headers=auth_headers(client))

    assert response.status_code == 200
    device = response.json()[0]
    assert device["external_id"] == "SILO-001"
    assert "token_hash" not in device
    assert "device_token" not in device


def test_query_readings(client):
    client.post("/api/readings", json=valid_payload(timestamp=datetime.now(timezone.utc).isoformat()))

    response = client.get("/api/readings?device_id=SILO-001&limit=10", headers=auth_headers(client))

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_storage_unit_readings_support_period_filters(client):
    now = datetime.now(timezone.utc)
    client.post("/api/readings", json=valid_payload(timestamp=(now - timedelta(hours=2)).isoformat()))
    client.post("/api/readings", json=valid_payload(timestamp=(now - timedelta(days=3)).isoformat(), grain_temperature=29.1))

    response = client.get(
        "/api/storage-units/1/readings",
        headers=auth_headers(client),
        params={"from": (now - timedelta(hours=6)).isoformat(), "to": now.isoformat()},
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_insights_use_real_readings_and_rbac(client):
    client.post(
        "/api/readings",
        json=valid_payload(
            grain_temperature=31.2,
            ambient_humidity=72.5,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ),
    )

    response = client.get("/api/insights?period=24h", headers=auth_headers(client, "cliente@silo-demo.local", "cliente123"))

    assert response.status_code == 200
    body = response.json()
    assert body["period"] == "24h"
    assert len(body["insights"]) == 1
    assert body["insights"][0]["data_points"] == 1
    assert body["insights"][0]["status"] in {"critical", "attention"}
    assert body["insights"][0]["recommendations"]


def test_storage_unit_insight_forbidden_for_unassigned_client(client, db_session):
    company = db_session.scalar(select(Company).where(Company.name == "AgroEscudo Demo"))
    site = db_session.scalar(select(Site).where(Site.company_id == company.id))
    other = StorageUnit(company_id=company.id, site_id=site.id, name="Silo No Asignado", unit_type="silo")
    db_session.add(other)
    db_session.commit()
    db_session.refresh(other)

    response = client.get(
        f"/api/storage-units/{other.id}/insights",
        headers=auth_headers(client, "cliente@silo-demo.local", "cliente123"),
    )

    assert response.status_code == 403


def test_insights_return_insufficient_data_without_readings(client):
    response = client.get("/api/storage-units/1/insights?period=24h", headers=auth_headers(client))

    assert response.status_code == 200
    assert response.json()["status"] in {"insufficient_data", "offline"}
    assert response.json()["recommendations"] == ["No hay suficientes lecturas recientes para emitir una recomendacion confiable."]


def test_list_active_alerts(client):
    create_alert(client)

    response = client.get("/api/alerts/active", headers=auth_headers(client))

    assert response.status_code == 200
    assert response.json()[0]["is_active"] is True


def test_acknowledge_alert(client):
    alert = create_alert(client)

    response = client.patch(f"/api/alerts/{alert['id']}/acknowledge", headers=auth_headers(client))

    assert response.status_code == 200
    assert response.json()["acknowledged_at"] is not None


def test_technician_can_acknowledge_alert(client):
    alert = create_alert(client)

    response = client.patch(
        f"/api/alerts/{alert['id']}/acknowledge",
        headers=auth_headers(client, "tecnico@agroescudo.local", "tecnico123"),
    )

    assert response.status_code == 200
    assert response.json()["acknowledged_at"] is not None


def test_resolve_alert(client):
    alert = create_alert(client)

    response = client.patch(f"/api/alerts/{alert['id']}/resolve", headers=auth_headers(client))

    assert response.status_code == 200
    assert response.json()["is_active"] is False
    assert response.json()["resolved_at"] is not None


def test_technician_cannot_resolve_alert(client):
    alert = create_alert(client)

    response = client.patch(
        f"/api/alerts/{alert['id']}/resolve",
        headers=auth_headers(client, "tecnico@agroescudo.local", "tecnico123"),
    )

    assert response.status_code == 403


def test_create_operational_log(client, db_session):
    alert = create_alert(client)
    storage_unit = db_session.scalar(select(StorageUnit))

    response = client.post(
        "/api/operational-logs",
        headers=auth_headers(client),
        json={
            "alert_id": alert["id"],
            "storage_unit_id": storage_unit.id,
            "action_taken": "Ventilacion manual",
            "operator_name": "Operador Demo",
            "notes": "Se activo ventilacion y se inspecciono el silo.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    assert response.status_code == 201
    assert response.json()["action_taken"] == "Ventilacion manual"


def test_technician_can_create_operational_log(client, db_session):
    storage_unit = db_session.scalar(select(StorageUnit))

    response = client.post(
        "/api/operational-logs",
        headers=auth_headers(client, "tecnico@agroescudo.local", "tecnico123"),
        json={
            "alert_id": None,
            "storage_unit_id": storage_unit.id,
            "action_taken": "Revision tecnica de nodo",
            "operator_name": "Tecnico AgroEscudo",
            "notes": "Se verifico bateria, senal y ubicacion fisica del sensor.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    assert response.status_code == 201
    assert response.json()["user_id"] is not None


def test_client_cannot_create_operational_log(client, db_session):
    storage_unit = db_session.scalar(select(StorageUnit))

    response = client.post(
        "/api/operational-logs",
        headers=auth_headers(client, "cliente@silo-demo.local", "cliente123"),
        json={
            "alert_id": None,
            "storage_unit_id": storage_unit.id,
            "action_taken": "Intento de registro",
            "operator_name": "Cliente Demo",
            "notes": "Cliente no debe registrar acciones tecnicas.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    assert response.status_code == 403


def test_update_thresholds(client, db_session):
    device = db_session.scalar(select(Device))

    response = client.put(
        f"/api/devices/{device.id}/thresholds",
        headers=auth_headers(client),
        json={
            "max_grain_temperature": 29.5,
            "max_ambient_humidity": 68.0,
            "min_battery_voltage": 3.6,
            "critical_temperature": 31.0,
            "critical_humidity": 75.0,
        },
    )

    assert response.status_code == 200
    assert response.json()["max_grain_temperature"] == 29.5
    assert response.json()["critical_humidity"] == 75.0


def test_client_cannot_update_thresholds(client, db_session):
    device = db_session.scalar(select(Device))

    response = client.put(
        f"/api/devices/{device.id}/thresholds",
        headers=auth_headers(client, "cliente@silo-demo.local", "cliente123"),
        json={
            "max_grain_temperature": 29.5,
            "max_ambient_humidity": 68.0,
            "min_battery_voltage": 3.6,
            "critical_temperature": 31.0,
            "critical_humidity": 75.0,
        },
    )

    assert response.status_code == 403


def test_client_has_scoped_read_access(client):
    headers = auth_headers(client, "cliente@silo-demo.local", "cliente123")

    companies = client.get("/api/companies", headers=headers)
    devices = client.get("/api/devices", headers=headers)
    alerts = client.get("/api/alerts/active", headers=headers)

    assert companies.status_code == 200
    assert len(companies.json()) == 1
    assert devices.status_code == 200
    assert devices.json()[0]["external_id"] == "SILO-001"
    assert alerts.status_code == 200


def test_technician_cannot_read_unassigned_storage_unit(client, db_session):
    company = db_session.scalar(select(Company).where(Company.name == "AgroEscudo Demo"))
    site = db_session.scalar(select(Site).where(Site.company_id == company.id))
    storage_unit = StorageUnit(company_id=company.id, site_id=site.id, name="Silo No Asignado", unit_type="silo")
    db_session.add(storage_unit)
    db_session.commit()

    response = client.get(
        f"/api/storage-units/{storage_unit.id}",
        headers=auth_headers(client, "tecnico@agroescudo.local", "tecnico123"),
    )

    assert response.status_code == 403


def test_client_does_not_list_unassigned_storage_units(client, db_session):
    company = db_session.scalar(select(Company).where(Company.name == "AgroEscudo Demo"))
    site = db_session.scalar(select(Site).where(Site.company_id == company.id))
    storage_unit = StorageUnit(company_id=company.id, site_id=site.id, name="Silo Cliente No Asignado", unit_type="silo")
    db_session.add(storage_unit)
    db_session.commit()

    response = client.get(
        "/api/storage-units",
        headers=auth_headers(client, "cliente@silo-demo.local", "cliente123"),
    )

    assert response.status_code == 200
    names = {item["name"] for item in response.json()}
    assert "Silo Cliente No Asignado" not in names


def test_generate_weekly_report(client, db_session):
    alert = create_alert(client)
    client.patch(f"/api/alerts/{alert['id']}/resolve", headers=auth_headers(client))
    storage_unit = db_session.scalar(select(StorageUnit))

    log_response = client.post(
        "/api/operational-logs",
        headers=auth_headers(client),
        json={
            "alert_id": alert["id"],
            "storage_unit_id": storage_unit.id,
            "action_taken": "Revision postcosecha",
            "operator_name": "Operador Demo",
            "notes": "Se reviso el grano almacenado.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert log_response.status_code == 201

    response = client.get(
        f"/api/reports/weekly?storage_unit_id={storage_unit.id}",
        headers=auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["company_name"] == "AgroEscudo Demo"
    assert body["reading_count"] >= 1
    assert body["alerts_generated"] >= 1
    assert body["alerts_resolved"] >= 1
    assert len(body["operational_actions"]) == 1
    assert body["pilot_status"] in {"pendiente de instalacion", "con alerta activa", "en monitoreo", "reporte generado"}
    assert body["installation_count"] == 0


def test_generate_weekly_pdf_for_authorized_client(client, db_session):
    storage_unit = db_session.scalar(select(StorageUnit))

    response = client.get(
        f"/api/reports/weekly/pdf?storage_unit_id={storage_unit.id}",
        headers=auth_headers(client, "cliente@silo-demo.local", "cliente123"),
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "agroescudo-reporte-" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    assert response.content.count(b"/Type /Page") >= 2


def test_client_cannot_generate_weekly_pdf_for_other_company(client, db_session):
    from app.models import Company, Site

    company = Company(name="Otro Acopio")
    db_session.add(company)
    db_session.flush()
    site = Site(company_id=company.id, name="Sitio Ajeno")
    db_session.add(site)
    db_session.flush()
    storage_unit = StorageUnit(company_id=company.id, site_id=site.id, name="Silo Ajeno", unit_type="silo")
    db_session.add(storage_unit)
    db_session.commit()

    response = client.get(
        f"/api/reports/weekly/pdf?storage_unit_id={storage_unit.id}",
        headers=auth_headers(client, "cliente@silo-demo.local", "cliente123"),
    )

    assert response.status_code == 403


def test_admin_can_create_complete_pilot(client, db_session):
    technician = db_session.scalar(select(User).where(User.role == "technician"))

    response = client.post(
        "/api/pilots",
        headers=auth_headers(client),
        json={
            "company_name": "Acopio Piloto Sur",
            "company_tax_id": "PILOT-002",
            "site_name": "Planta Warnes",
            "site_location": "Warnes, Santa Cruz",
            "storage_unit_name": "Galpon Piloto 2",
            "storage_unit_type": "galpon",
            "capacity_tons": 240,
            "device_external_id": "GALPON-002",
            "device_name": "Nodo Galpon 002",
            "device_token": "token-galpon-002",
            "technician_user_id": technician.id,
            "client_email": "cliente@acopio-sur.local",
            "client_full_name": "Responsable Acopio Sur",
            "client_password": "cliente456",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["company_name"] == "Acopio Piloto Sur"
    assert body["site_name"] == "Planta Warnes"
    assert body["storage_unit_name"] == "Galpon Piloto 2"
    assert body["device_external_id"] == "GALPON-002"
    assert body["technician_name"] == "Tecnico AgroEscudo"
    assert body["client_name"] == "Responsable Acopio Sur"
    assert body["status"] == "pendiente de instalacion"

    login = client.post(
        "/api/auth/login",
        json={"email": "cliente@acopio-sur.local", "password": "cliente456"},
    )
    assert login.status_code == 200


def test_technician_can_register_installation_checklist(client, db_session):
    storage_unit = db_session.scalar(select(StorageUnit))
    device = db_session.scalar(select(Device))

    response = client.post(
        "/api/operational-logs/installations",
        headers=auth_headers(client, "tecnico@agroescudo.local", "tecnico123"),
        json={
            "storage_unit_id": storage_unit.id,
            "device_id": device.id,
            "physical_location": "Pared norte, acceso tecnico principal",
            "sensor_installed_correctly": True,
            "connectivity_verified": True,
            "initial_reading_registered": True,
            "battery_verified": True,
            "observations": "Nodo fijado y validado en campo.",
            "technician_name": "Tecnico AgroEscudo",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    )

    assert response.status_code == 201
    assert response.json()["category"] == "installation"
    assert response.json()["device_id"] == device.id
    assert "Conectividad verificada: Si" in response.json()["notes"]

    pilot = client.get(f"/api/pilots/{storage_unit.id}", headers=auth_headers(client))
    assert pilot.status_code == 200
    assert pilot.json()["installation_count"] == 1
    assert pilot.json()["status"] == "instalado"


def test_client_can_read_own_pilot_summary(client, db_session):
    storage_unit = db_session.scalar(select(StorageUnit))

    response = client.get(
        f"/api/pilots/{storage_unit.id}",
        headers=auth_headers(client, "cliente@silo-demo.local", "cliente123"),
    )

    assert response.status_code == 200
    assert response.json()["storage_unit_name"] == "Silo Demo 1"
    assert response.json()["client_name"] == "Cliente Silo Demo"


def test_admin_can_clear_pilot_operational_data_without_deleting_asset(client, db_session):
    storage_unit = db_session.scalar(select(StorageUnit))
    reading = client.post(
        "/api/readings",
        json=valid_payload(grain_temperature=34.0, ambient_humidity=80.0),
    )
    assert reading.status_code == 201

    response = client.delete(
        f"/api/pilots/{storage_unit.id}/operational-data",
        headers=auth_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["readings_deleted"] == 1
    assert response.json()["alerts_deleted"] == 1
    assert db_session.get(StorageUnit, storage_unit.id) is not None
    assert db_session.scalar(select(func.count(SensorReading.id))) == 0
    assert db_session.scalar(select(func.count(Alert.id))) == 0


def test_technician_cannot_clear_pilot_operational_data(client, db_session):
    storage_unit = db_session.scalar(select(StorageUnit))

    response = client.delete(
        f"/api/pilots/{storage_unit.id}/operational-data",
        headers=auth_headers(client, "tecnico@agroescudo.local", "tecnico123"),
    )

    assert response.status_code == 403


def test_admin_can_simulate_critical_demo_reading(client):
    response = client.post(
        "/api/demo/simulate-critical-reading",
        headers=auth_headers(client),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["device_external_id"] == "SILO-001"
    assert body["reading"]["grain_temperature"] == 36.8
    assert body["reading"]["ambient_humidity"] == 84.6
    assert any(alert["severity"] == "critical" for alert in body["alerts"])


def test_technician_cannot_simulate_critical_demo_reading(client):
    response = client.post(
        "/api/demo/simulate-critical-reading",
        headers=auth_headers(client, "tecnico@agroescudo.local", "tecnico123"),
    )

    assert response.status_code == 403


def test_client_cannot_simulate_critical_demo_reading(client):
    response = client.post(
        "/api/demo/simulate-critical-reading",
        headers=auth_headers(client, "cliente@silo-demo.local", "cliente123"),
    )

    assert response.status_code == 403


def test_demo_simulation_is_disabled_outside_local_environment(client, monkeypatch):
    from app.api.routes import demo as demo_routes

    monkeypatch.setattr(demo_routes.settings, "environment", "production")
    response = client.post(
        "/api/demo/simulate-critical-reading",
        headers=auth_headers(client),
    )

    assert response.status_code == 404


def test_update_notification_preference(client):
    response = client.put(
        "/api/notifications/preferences/telegram",
        headers=auth_headers(client, "cliente@silo-demo.local", "cliente123"),
        json={"enabled": True, "destination": "123456", "minimum_severity": "critical"},
    )

    assert response.status_code == 200
    assert response.json()["channel"] == "telegram"
    assert response.json()["enabled"] is True
    assert response.json()["destination"] == "123456"

    preferences = client.get(
        "/api/notifications/preferences",
        headers=auth_headers(client, "cliente@silo-demo.local", "cliente123"),
    )
    assert preferences.status_code == 200
    assert any(item["channel"] == "telegram" for item in preferences.json())


def test_register_push_token(client, db_session):
    headers = auth_headers(client, "cliente@silo-demo.local", "cliente123")
    response = client.post(
        "/api/notifications/push-tokens",
        headers=headers,
        json={"token": "fcm-token-demo-123456", "platform": "android"},
    )

    assert response.status_code == 201
    assert response.json()["platform"] == "android"
    assert db_session.scalar(select(PushDeviceToken).where(PushDeviceToken.token == "fcm-token-demo-123456")) is not None
    assert db_session.scalar(select(NotificationPreference).where(NotificationPreference.channel == "push")) is not None

    deleted = client.request(
        "DELETE",
        "/api/notifications/push-tokens/current",
        headers=headers,
        json={"token": "fcm-token-demo-123456", "platform": "android"},
    )
    assert deleted.status_code == 204
    record = db_session.scalar(select(PushDeviceToken).where(PushDeviceToken.token == "fcm-token-demo-123456"))
    assert record is not None
    assert record.is_active is False


def test_test_notification_records_skipped_event_when_channel_unconfigured(client):
    client.put(
        "/api/notifications/preferences/telegram",
        headers=auth_headers(client),
        json={"enabled": True, "destination": "123456", "minimum_severity": "all"},
    )

    response = client.post("/api/notifications/test/telegram", headers=auth_headers(client))

    assert response.status_code == 200
    assert response.json()["channel"] == "telegram"
    assert response.json()["event"]["status"] == "skipped"


def test_admin_user_management_and_assignments(client, db_session):
    company = db_session.scalar(select(Company).where(Company.name == "AgroEscudo Demo"))
    storage_unit = db_session.scalar(select(StorageUnit))
    headers = auth_headers(client)

    created = client.post(
        "/api/admin/users",
        headers=headers,
        json={
            "company_id": company.id,
            "email": "tecnico2@agroescudo.local",
            "full_name": "Tecnico Dos",
            "password": "tecnico222",
            "role": "technician",
            "storage_unit_ids": [storage_unit.id],
        },
    )
    assert created.status_code == 201
    user_id = created.json()["id"]

    assigned = client.post(
        f"/api/admin/users/{user_id}/assign-storage-units",
        headers=headers,
        json={"storage_unit_ids": [storage_unit.id]},
    )
    assert assigned.status_code == 200
    db_session.expire_all()
    assigned_unit = db_session.get(StorageUnit, storage_unit.id)
    assert assigned_unit.assigned_technician_id == user_id

    deactivated = client.post(f"/api/admin/users/{user_id}/deactivate", headers=headers)
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    reset = client.post(
        f"/api/admin/users/{user_id}/reset-password",
        headers=headers,
        json={"password": "nuevo123"},
    )
    assert reset.status_code == 200
    user = db_session.get(User, user_id)
    assert verify_password("nuevo123", user.hashed_password)


def test_admin_company_storage_and_device_flow(client, db_session):
    headers = auth_headers(client)
    company_response = client.post(
        "/api/admin/companies",
        headers=headers,
        json={
            "name": "Cooperativa Norte Demo",
            "tax_id": "NORTE-DEMO",
            "type": "cooperativa",
            "city": "Sacaba, Cochabamba",
            "contact_name": "Operaciones",
            "contact_email": "ops@norte.demo",
            "contact_phone": "+59170000009",
        },
    )
    assert company_response.status_code == 201
    company_id = company_response.json()["id"]

    site = Site(company_id=company_id, name="Planta Norte", location="Sacaba")
    db_session.add(site)
    db_session.commit()
    db_session.refresh(site)

    unit_response = client.post(
        "/api/admin/storage-units",
        headers=headers,
        json={
            "company_id": company_id,
            "site_id": site.id,
            "name": "Silo Piloto API",
            "unit_type": "silo",
            "capacity_tons": 220,
            "location": "Sector prueba",
            "crop_type": "Maiz",
        },
    )
    assert unit_response.status_code == 201
    storage_unit_id = unit_response.json()["id"]

    device_response = client.post(
        "/api/admin/devices",
        headers=headers,
        json={
            "storage_unit_id": storage_unit_id,
            "external_id": "SILO-API-001",
            "name": "Nodo API 001",
            "device_type": "esp32_lora_wifi_node",
        },
    )
    assert device_response.status_code == 201
    assert device_response.json()["api_key"].startswith("agro_")
    device_id = device_response.json()["id"]

    reset_response = client.post(f"/api/admin/devices/{device_id}/reset-api-key", headers=headers)
    assert reset_response.status_code == 200
    assert reset_response.json()["api_key"].startswith("agro_")


def test_inactive_device_rejects_reading(client, db_session):
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    device.is_active = False
    db_session.commit()

    response = client.post("/api/readings", json=valid_payload())

    assert response.status_code == 403
    assert response.json()["detail"] == "Sensor inactivo. Contacta al administrador."


def test_admin_notification_test_creates_dry_run_delivery(client):
    response = client.post(
        "/api/admin/notifications/test/telegram",
        headers=auth_headers(client),
        json={"destination": "123456", "message": "Prueba controlada AgroEscudo."},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["channel"] == "telegram"
    assert body["dry_run"] is True
    assert body["status"] == "dry_run"

    deliveries = client.get("/api/admin/notifications/deliveries", headers=auth_headers(client))
    assert deliveries.status_code == 200
    assert "Prueba controlada AgroEscudo." in deliveries.json()[0]["payload_preview"]
    assert "Nivel: TEST" in deliveries.json()[0]["payload_preview"]


def test_alert_notification_creates_delivery_without_duplicate(client, db_session):
    user = db_session.scalar(select(User).where(User.email == "cliente@silo-demo.local"))
    db_session.add(
        NotificationPreference(
            company_id=user.company_id,
            user_id=user.id,
            channel="telegram",
            destination="123456",
            minimum_severity="warning",
            enabled=True,
        )
    )
    db_session.commit()

    payload = valid_payload(grain_temperature=31.0)
    client.post("/api/readings", json=payload)
    client.post("/api/readings", json=payload)

    deliveries = db_session.scalars(select(NotificationDelivery).where(NotificationDelivery.channel == "telegram")).all()
    assert len(deliveries) == 1
    assert deliveries[0].dry_run is True
    assert deliveries[0].status == "dry_run"


def test_ai_alert_recommendation_uses_rules_without_api_key(client):
    alert = create_alert(client)

    response = client.get(
        f"/api/ai/alerts/{alert['id']}/recommendation",
        headers=auth_headers(client),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "rules"
    assert body["alert_id"] == alert["id"]
    assert body["recommended_actions"]
