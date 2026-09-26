from sqlalchemy import select

from app.models import AuditEvent, Company, Device, DeviceChannel, Site, StorageUnit


POLYGON = {
    "type": "Polygon",
    "coordinates": [[[-63.2, -17.8], [-63.0, -17.8], [-63.0, -17.6], [-63.2, -17.6], [-63.2, -17.8]]],
}


def auth_headers(client, email="admin@agroescudo.local", password="admin123"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def field_parcel(db_session, *, company=None, site=None, name="Parcela QA"):
    company = company or db_session.scalar(select(Company).where(Company.name == "AgroEscudo Demo"))
    site = site or db_session.scalar(select(Site).where(Site.company_id == company.id))
    parcel = StorageUnit(company_id=company.id, site_id=site.id, name=name, unit_type="field", operation_type="field", boundary_geojson=POLYGON)
    db_session.add(parcel)
    db_session.commit()
    return parcel


def payload(parcel, external_id="PLUV-QA-003"):
    return {
        "company_id": parcel.company_id,
        "site_id": parcel.site_id,
        "storage_unit_id": parcel.id,
        "external_id": external_id,
        "name": "P-03 QA DEMO",
        "device_type": "rain_gauge",
        "latitude": -17.7,
        "longitude": -63.1,
        "expected_reading_interval_minutes": 15,
        "template_code": "RAIN_GAUGE_BASE",
        "is_active": True,
    }


def test_admin_installs_canonical_rain_gauge_with_channels_and_audit(client, db_session):
    parcel = field_parcel(db_session)
    response = client.post("/api/admin/devices", json=payload(parcel), headers=auth_headers(client))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["operational_status"] == "awaiting_first_reading"
    assert body["expected_reading_interval_minutes"] == 15
    assert body["last_seen_at"] is None
    device = db_session.get(Device, body["id"])
    assert device.template_code == "RAIN_GAUGE_BASE"
    assert set(db_session.scalars(select(DeviceChannel.channel_key).where(DeviceChannel.device_id == device.id)).all()) == {
        "rain_1", "ambient_temp_1", "ambient_rh_1", "wind_speed_1", "wind_direction_1", "battery_1"
    }
    assert db_session.scalar(select(AuditEvent).where(AuditEvent.action == "pluviometry.device_installed", AuditEvent.resource_id == str(device.id)))


def test_install_rejects_duplicate_wrong_hierarchy_outside_and_disabled_feature(client, db_session):
    parcel = field_parcel(db_session)
    headers = auth_headers(client)
    assert client.post("/api/admin/devices", json=payload(parcel), headers=headers).status_code == 201
    assert client.post("/api/admin/devices", json=payload(parcel), headers=headers).status_code == 409
    wrong_site = payload(parcel, "PLUV-WRONG-SITE") | {"site_id": parcel.site_id + 999}
    assert client.post("/api/admin/devices", json=wrong_site, headers=headers).status_code == 422
    outside = payload(parcel, "PLUV-OUTSIDE") | {"longitude": -64.0}
    assert client.post("/api/admin/devices", json=outside, headers=headers).status_code == 422

    company = Company(name="Sin Pluviometría")
    db_session.add(company); db_session.flush()
    site = Site(company_id=company.id, name="Predio sin módulo")
    db_session.add(site); db_session.flush()
    disabled_parcel = field_parcel(db_session, company=company, site=site, name="Parcela sin módulo")
    assert client.post("/api/admin/devices", json=payload(disabled_parcel, "PLUV-DISABLED"), headers=headers).status_code == 403


def test_technician_cannot_install_and_external_id_is_immutable(client, db_session):
    parcel = field_parcel(db_session)
    tech = auth_headers(client, "tecnico@agroescudo.local", "tecnico123")
    assert client.post("/api/admin/devices", json=payload(parcel), headers=tech).status_code == 403
    admin = auth_headers(client)
    created = client.post("/api/admin/devices", json=payload(parcel), headers=admin).json()
    response = client.patch(f"/api/admin/devices/{created['id']}", json={"external_id": "CHANGED"}, headers=admin)
    assert response.status_code == 422


def test_rain_gauge_move_and_activation_changes_are_audited_without_losing_identity(client, db_session):
    parcel = field_parcel(db_session)
    second = field_parcel(db_session, name="Parcela QA 2")
    headers = auth_headers(client)
    created = client.post("/api/admin/devices", json=payload(parcel), headers=headers).json()
    response = client.patch(
        f"/api/admin/devices/{created['id']}",
        json={"storage_unit_id": second.id, "latitude": -17.69, "longitude": -63.09, "is_active": False, "name": "P-03 reubicado"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["external_id"] == "PLUV-QA-003"
    actions = set(db_session.scalars(select(AuditEvent.action).where(AuditEvent.resource_id == str(created["id"]))).all())
    assert {"pluviometry.location_updated", "pluviometry.parcel_changed", "pluviometry.deactivated"}.issubset(actions)
