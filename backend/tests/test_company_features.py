from sqlalchemy import select

from app.core.security import hash_password, hash_secret
from app.models import AuditEvent, Company, CompanyFeature, Device, Site, StorageUnit, User
from app.services.company_features import PLUVIOMETRY


def _login(client, email: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _company_b(db_session):
    company = Company(name="Empresa B", type="productor")
    db_session.add(company)
    db_session.flush()
    site = Site(company_id=company.id, name="Predio B")
    db_session.add(site)
    db_session.flush()
    client_user = User(
        company_id=company.id,
        email="cliente-b@empresa.local",
        full_name="Cliente Empresa B",
        hashed_password=hash_password("clienteB123"),
        role="client",
    )
    technician = User(
        company_id=company.id,
        email="tecnico-b@empresa.local",
        full_name="Tecnico Empresa B",
        hashed_password=hash_password("tecnicoB123"),
        role="technician",
    )
    db_session.add_all([client_user, technician])
    db_session.flush()
    parcel = StorageUnit(
        company_id=company.id,
        site_id=site.id,
        name="Parcela B",
        unit_type="parcela",
        operation_type="field",
        assigned_client_id=client_user.id,
        assigned_technician_id=technician.id,
    )
    db_session.add(parcel)
    db_session.flush()
    gauge = Device(
        company_id=company.id,
        site_id=site.id,
        storage_unit_id=parcel.id,
        external_id="PLUV-EMPRESA-B",
        name="Pluviometro B",
        token_hash=hash_secret("feature-test"),
        device_type="rain_gauge",
    )
    db_session.add(gauge)
    db_session.commit()
    return company, site, parcel, gauge, client_user, technician


def test_disabled_company_is_rejected_without_leaking_pluviometry(client, db_session):
    company, site, _, gauge, *_ = _company_b(db_session)
    headers = _login(client, "cliente-b@empresa.local", "clienteB123")
    sites = client.get("/api/pluviometry/sites", headers=headers)
    assert sites.status_code == 403
    assert sites.json()["detail"] == "feature_not_enabled"
    snapshot = client.get(f"/api/pluviometry/sites/{site.id}/map", headers=headers)
    assert snapshot.status_code == 403
    assert snapshot.json()["detail"] == "feature_not_enabled"
    device = client.get(f"/api/devices/{gauge.id}", headers=headers)
    assert device.status_code == 403
    assert device.json()["detail"] == "feature_not_enabled"
    listed = client.get("/api/devices", headers=headers)
    assert listed.status_code == 200
    assert gauge.id not in {item["id"] for item in listed.json()}
    assert db_session.get(Company, company.id) is not None


def test_admin_can_enable_and_disable_without_deleting_data_and_audit_is_recorded(client, db_session):
    company, _, parcel, gauge, *_ = _company_b(db_session)
    headers = _login(client, "admin@agroescudo.local", "admin123")
    initial = client.get(f"/api/admin/companies/{company.id}/features", headers=headers)
    assert initial.status_code == 200, initial.text
    assert initial.json() == [{
        "feature_code": PLUVIOMETRY,
        "enabled": False,
        "enabled_at": None,
        "enabled_by_id": None,
    }]
    enabled = client.patch(
        f"/api/admin/companies/{company.id}/features/{PLUVIOMETRY}",
        headers=headers,
        json={"enabled": True},
    )
    assert enabled.status_code == 200, enabled.text
    assert enabled.json()["enabled"] is True
    disabled = client.patch(
        f"/api/admin/companies/{company.id}/features/{PLUVIOMETRY}",
        headers=headers,
        json={"enabled": False},
    )
    assert disabled.status_code == 200, disabled.text
    assert disabled.json()["enabled"] is False
    assert db_session.get(StorageUnit, parcel.id) is not None
    assert db_session.get(Device, gauge.id) is not None
    actions = set(db_session.scalars(select(AuditEvent.action).where(AuditEvent.company_id == company.id)).all())
    assert {"company.feature_enabled", "company.feature_disabled"}.issubset(actions)


def test_client_and_technician_cannot_manage_company_features(client, db_session):
    company, *_, client_user, technician = _company_b(db_session)
    for email, password in ((client_user.email, "clienteB123"), (technician.email, "tecnicoB123")):
        response = client.patch(
            f"/api/admin/companies/{company.id}/features/{PLUVIOMETRY}",
            headers=_login(client, email, password),
            json={"enabled": True},
        )
        assert response.status_code == 403


def test_company_features_are_isolated_and_exposed_by_me(client, db_session):
    company_b, site_b, _, _, *_ = _company_b(db_session)
    admin_headers = _login(client, "admin@agroescudo.local", "admin123")
    client.patch(
        f"/api/admin/companies/{company_b.id}/features/{PLUVIOMETRY}",
        headers=admin_headers,
        json={"enabled": False},
    )
    demo_me = client.get("/api/me", headers=_login(client, "cliente@silo-demo.local", "cliente123"))
    assert PLUVIOMETRY in demo_me.json()["features"]
    admin_me = client.get("/api/me", headers=admin_headers)
    assert PLUVIOMETRY in admin_me.json()["features"]
    company_b_me = client.get("/api/me", headers=_login(client, "cliente-b@empresa.local", "clienteB123"))
    assert PLUVIOMETRY not in company_b_me.json()["features"]
    setting = db_session.scalar(select(CompanyFeature).where(
        CompanyFeature.company_id == company_b.id,
        CompanyFeature.feature_code == PLUVIOMETRY,
    ))
    assert setting is not None and setting.enabled is False
    denied = client.get(f"/api/pluviometry/sites/{site_b.id}/map", headers=_login(client, "cliente-b@empresa.local", "clienteB123"))
    assert denied.status_code == 403


def test_enabled_company_still_respects_cross_company_device_rbac(client, db_session):
    company_b, _, _, gauge_b, *_ = _company_b(db_session)
    admin_headers = _login(client, "admin@agroescudo.local", "admin123")
    client.patch(
        f"/api/admin/companies/{company_b.id}/features/{PLUVIOMETRY}",
        headers=admin_headers,
        json={"enabled": True},
    )
    demo_client_headers = _login(client, "cliente@silo-demo.local", "cliente123")
    response = client.get(f"/api/devices/{gauge_b.id}", headers=demo_client_headers)
    assert response.status_code == 403
