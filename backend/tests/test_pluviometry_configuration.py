from sqlalchemy import select

from app.models import AuditEvent, Company, Site, StorageUnit


POLYGON = {
    "type": "Polygon",
    "coordinates": [[[-66.29, -17.39], [-66.27, -17.39], [-66.27, -17.37], [-66.29, -17.39]]],
}
MULTIPOLYGON = {
    "type": "MultiPolygon",
    "coordinates": [[[[-66.29, -17.39], [-66.28, -17.39], [-66.28, -17.38], [-66.29, -17.39]]]],
}


def auth_headers(client, email="admin@agroescudo.local", password="admin123"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_admin_can_update_site_boundary_and_audit(client, db_session):
    site = db_session.scalar(select(Site))
    response = client.patch(f"/api/sites/{site.id}", json={"boundary_geojson": POLYGON}, headers=auth_headers(client))
    assert response.status_code == 200
    assert response.json()["boundary_geojson"] == POLYGON
    event = db_session.scalar(select(AuditEvent).where(AuditEvent.action == "pluviometry.site_boundary_updated"))
    assert event is not None
    assert event.resource_id == str(site.id)


def test_client_cannot_update_site_boundary(client, db_session):
    site = db_session.scalar(select(Site))
    response = client.patch(f"/api/sites/{site.id}", json={"boundary_geojson": POLYGON}, headers=auth_headers(client, "cliente@silo-demo.local", "cliente123"))
    assert response.status_code == 403


def test_technician_cannot_update_site_boundary(client, db_session):
    site = db_session.scalar(select(Site))
    response = client.patch(f"/api/sites/{site.id}", json={"boundary_geojson": POLYGON}, headers=auth_headers(client, "tecnico@agroescudo.local", "tecnico123"))
    assert response.status_code == 403


def test_admin_creates_field_for_selected_site_and_audits(client, db_session):
    site = db_session.scalar(select(Site))
    response = client.post(
        "/api/admin/storage-units",
        headers=auth_headers(client),
        json={
            "company_id": site.company_id,
            "site_id": site.id,
            "name": "Parcela QA DEMO",
            "unit_type": "field",
            "operation_type": "field",
            "surface_hectares": 1.25,
            "boundary_geojson": POLYGON,
        },
    )
    assert response.status_code == 201
    payload = response.json()
    assert payload["site_id"] == site.id
    assert payload["operation_type"] == "field"
    assert db_session.scalar(select(AuditEvent).where(AuditEvent.action == "pluviometry.parcel_created")) is not None


def test_valid_polygon_and_multipolygon_are_preserved(client, db_session):
    site = db_session.scalar(select(Site))
    polygon_response = client.patch(f"/api/sites/{site.id}", json={"boundary_geojson": POLYGON}, headers=auth_headers(client))
    multipolygon_response = client.patch(f"/api/sites/{site.id}", json={"boundary_geojson": MULTIPOLYGON}, headers=auth_headers(client))
    assert polygon_response.status_code == 200
    assert multipolygon_response.status_code == 200
    assert multipolygon_response.json()["boundary_geojson"] == MULTIPOLYGON


def test_invalid_geojson_is_rejected(client, db_session):
    site = db_session.scalar(select(Site))
    invalid = {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [0, 1]]]}
    response = client.patch(f"/api/sites/{site.id}", json={"boundary_geojson": invalid}, headers=auth_headers(client))
    assert response.status_code == 422
    assert "cierre" in response.text


def test_out_of_range_coordinate_is_rejected(client, db_session):
    site = db_session.scalar(select(Site))
    invalid = {"type": "Polygon", "coordinates": [[[181, 0], [1, 0], [0, 1], [181, 0]]]}
    response = client.patch(f"/api/sites/{site.id}", json={"boundary_geojson": invalid}, headers=auth_headers(client))
    assert response.status_code == 422


def test_company_scope_prevents_site_leak_for_client(client, db_session):
    other_company = Company(name="Empresa ajena")
    db_session.add(other_company)
    db_session.flush()
    other_site = Site(company_id=other_company.id, name="Predio ajeno")
    db_session.add(other_site)
    db_session.commit()
    headers = auth_headers(client, "cliente@silo-demo.local", "cliente123")
    listing = client.get("/api/sites", headers=headers)
    direct = client.get(f"/api/sites/{other_site.id}", headers=headers)
    assert listing.status_code == 200
    assert other_site.id not in {item["id"] for item in listing.json()}
    assert direct.status_code == 403


def test_non_admin_cannot_create_field_by_direct_id(client, db_session):
    site = db_session.scalar(select(Site))
    response = client.post(
        "/api/admin/storage-units",
        headers=auth_headers(client, "cliente@silo-demo.local", "cliente123"),
        json={"company_id": site.company_id, "site_id": site.id, "name": "Intrusa", "unit_type": "field", "operation_type": "field", "boundary_geojson": POLYGON},
    )
    assert response.status_code == 403
    assert db_session.scalar(select(StorageUnit).where(StorageUnit.name == "Intrusa")) is None
