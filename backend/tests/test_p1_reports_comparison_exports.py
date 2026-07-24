from datetime import timedelta
from io import BytesIO

from pypdf import PdfReader
from sqlalchemy import select

from app.models import Company, Device, SensorReading, Site, StorageUnit, utc_now


def _headers(client, email: str = "admin@agroescudo.local", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _seed_readings(db_session, *, count_a: int = 4, count_b: int = 4):
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    device.expected_reading_interval_minutes = 60
    now = utc_now()
    for index in range(count_a):
        db_session.add(
            SensorReading(
                company_id=device.company_id,
                site_id=device.site_id,
                storage_unit_id=device.storage_unit_id,
                device_id=device.id,
                grain_temperature=20 + index,
                ambient_temperature=18 + index,
                ambient_humidity=55 + index,
                battery_voltage=3.9,
                timestamp=now - timedelta(days=2, hours=index),
            )
        )
    for index in range(count_b):
        db_session.add(
            SensorReading(
                company_id=device.company_id,
                site_id=device.site_id,
                storage_unit_id=device.storage_unit_id,
                device_id=device.id,
                grain_temperature=25 + index,
                ambient_temperature=20 + index,
                ambient_humidity=60 + index,
                battery_voltage=3.8,
                timestamp=now - timedelta(hours=index),
            )
        )
    db_session.commit()
    return device, now


def test_executive_and_technical_reports_have_distinct_rbac(client, db_session):
    device, now = _seed_readings(db_session)
    params = {
        "storage_unit_id": device.storage_unit_id,
        "date_from": (now - timedelta(days=7)).isoformat(),
        "date_to": now.isoformat(),
    }
    executive = client.get(
        "/api/reports/executive",
        headers=_headers(client, "cliente@silo-demo.local", "cliente123"),
        params=params,
    )
    assert executive.status_code == 200, executive.text
    assert executive.content.startswith(b"%PDF")
    executive_reader = PdfReader(BytesIO(executive.content))
    assert len(executive_reader.pages) >= 2
    executive_text = "\n".join(page.extract_text() or "" for page in executive_reader.pages)
    assert "Reporte ejecutivo de operacion" in executive_text
    assert "certificacion" in executive_text
    assert "Senal" not in executive_text

    client_technical = client.get(
        "/api/reports/technical",
        headers=_headers(client, "cliente@silo-demo.local", "cliente123"),
        params=params,
    )
    assert client_technical.status_code == 403

    technical = client.get(
        "/api/reports/technical",
        headers=_headers(client, "tecnico@agroescudo.local", "tecnico123"),
        params=params,
    )
    assert technical.status_code == 200, technical.text
    technical_text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(technical.content)).pages)
    assert "Reporte tecnico de operacion" in technical_text
    assert "Senal" in technical_text
    assert "Calibracion" in technical_text


def test_period_comparison_uses_one_device_and_reports_coverage(client, db_session):
    device, now = _seed_readings(db_session)
    response = client.get(
        f"/api/devices/{device.id}/compare",
        headers=_headers(client),
        params={
            "variable": "grain_temperature",
            "period_a_from": (now - timedelta(days=3)).isoformat(),
            "period_a_to": (now - timedelta(days=1)).isoformat(),
            "period_b_from": (now - timedelta(hours=5)).isoformat(),
            "period_b_to": now.isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["device_id"] == device.id
    assert body["sufficient_data"] is True
    assert body["absolute_difference"] > 0
    assert body["period_a"]["coverage_method"] == "configured_cadence"
    assert "causalidad" in body["note"]


def test_period_comparison_rejects_conclusion_with_insufficient_data(client, db_session):
    device, now = _seed_readings(db_session, count_a=1, count_b=1)
    response = client.get(
        f"/api/devices/{device.id}/compare",
        headers=_headers(client),
        params={
            "variable": "grain_temperature",
            "period_a_from": (now - timedelta(days=3)).isoformat(),
            "period_a_to": (now - timedelta(days=1)).isoformat(),
            "period_b_from": (now - timedelta(hours=5)).isoformat(),
            "period_b_to": now.isoformat(),
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["sufficient_data"] is False
    assert response.json()["absolute_difference"] is None
    assert "Datos insuficientes" in response.json()["note"]


def test_csv_exports_are_scoped_and_identify_raw_calibrated_fields(client, db_session):
    device, now = _seed_readings(db_session)
    response = client.get(
        "/api/exports/readings.csv",
        headers=_headers(client, "cliente@silo-demo.local", "cliente123"),
        params={"storage_unit_id": device.storage_unit_id},
    )
    assert response.status_code == 200, response.text
    decoded = response.content.decode("utf-8-sig")
    assert "raw_metrics_json" in decoded
    assert "calibrated_metrics_json" in decoded
    assert "SILO-001" not in decoded
    assert response.headers["x-export-truncated"] == "false"

    other_company = Company(name="Export Ajeno")
    db_session.add(other_company)
    db_session.flush()
    site = Site(company_id=other_company.id, name="Sitio Export Ajeno")
    db_session.add(site)
    db_session.flush()
    unit = StorageUnit(company_id=other_company.id, site_id=site.id, name="Unidad Export Ajena", unit_type="silo")
    db_session.add(unit)
    db_session.commit()
    blocked = client.get(
        "/api/exports/alerts.csv",
        headers=_headers(client, "cliente@silo-demo.local", "cliente123"),
        params={"storage_unit_id": unit.id},
    )
    assert blocked.status_code == 403
