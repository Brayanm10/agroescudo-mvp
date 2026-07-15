from sqlalchemy import select

from app.core.security import verify_password
from app.models import EducationArticle, StorageUnit, User


def _auth_headers(client, email="admin@agroescudo.local", password="admin123"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def test_signup_company_email_verify_and_pending_approval(client, db_session):
    payload = {
        "responsible_name": "Laura Rojas",
        "work_email": "laura@nuevoacopio.bo",
        "phone": "+59170000010",
        "commercial_name": "Nuevo Acopio Piloto",
        "legal_name": "Nuevo Acopio Piloto S.R.L.",
        "tax_id": "NAP-001",
        "sector": "acopiador",
        "city": "Montero",
        "department": "Santa Cruz",
        "estimated_sites": 1,
        "estimated_storage_units": 2,
        "use_case": "Monitoreo de silos de maiz para piloto comercial.",
        "password": "Piloto123",
        "language": "es",
        "consent_terms": True,
        "consent_privacy": True,
    }

    response = client.post("/api/auth/signup/company", json=payload)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "PENDING_REVIEW"
    assert body["verification_preview_token"]

    verify_response = client.post("/api/auth/email/verify", json={"token": body["verification_preview_token"]})
    assert verify_response.status_code == 200, verify_response.text

    user = db_session.scalar(select(User).where(User.email == "laura@nuevoacopio.bo"))
    assert user.status == "PENDING_APPROVAL"
    assert user.email_verified_at is not None

    login_response = client.post("/api/auth/login", json={"email": "laura@nuevoacopio.bo", "password": "Piloto123"})
    assert login_response.status_code == 403


def test_password_forgot_and_reset_revokes_old_password(client, db_session):
    response = client.post("/api/auth/password/forgot", json={"email": "admin@agroescudo.local"})

    assert response.status_code == 200, response.text
    token = response.json()["reset_preview_token"]
    assert token

    reset = client.post("/api/auth/password/reset", json={"token": token, "password": "Nueva123"})
    assert reset.status_code == 200, reset.text

    user = db_session.scalar(select(User).where(User.email == "admin@agroescudo.local"))
    assert verify_password("Nueva123", user.hashed_password)
    assert client.post("/api/auth/login", json={"email": "admin@agroescudo.local", "password": "admin123"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "admin@agroescudo.local", "password": "Nueva123"}).status_code == 200


def test_control_center_summary_returns_versioned_index(client):
    response = client.get("/api/control-center/summary", headers=_auth_headers(client))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["formula_version"] == "control-index-v1.0"
    assert 0 <= body["score"] <= 100
    assert body["status"] in {"PROTEGIDA", "ATENCION", "CRITICA", "SIN_DATOS"}
    assert "storage_units" in body["kpis"]


def test_agro_assistant_uses_verified_rules_without_external_credentials(client):
    response = client.post(
        "/api/agro-assistant/messages",
        headers=_auth_headers(client, "cliente@silo-demo.local", "cliente123"),
        json={"message": "Que debo revisar hoy?"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "rules"
    assert body["facts"]
    assert body["recommended_actions"]


def test_admin_can_inspect_integrations_without_exposing_secrets(client):
    response = client.get("/api/admin/integrations/status", headers=_auth_headers(client))

    assert response.status_code == 200, response.text
    body = response.json()
    assert "gemini" in body["services"]
    assert "telegram" in body["services"]
    assert "whatsapp" in body["services"]
    assert "token" not in response.text.lower()


def test_service_case_and_maintenance_report_flow(client, db_session):
    storage_unit = db_session.scalar(select(StorageUnit))
    headers = _auth_headers(client, "tecnico@agroescudo.local", "tecnico123")

    response = client.post(
        "/api/service-cases",
        headers=headers,
        json={
            "storage_unit_id": storage_unit.id,
            "title": "Revision preventiva de nodo",
            "description": "Validar bateria y conectividad del sensor asignado.",
            "priority": "high",
        },
    )
    assert response.status_code == 201, response.text
    case_id = response.json()["id"]

    event = client.post(
        f"/api/service-cases/{case_id}/events",
        headers=headers,
        json={"event_type": "field_note", "note": "Nodo revisado y caja limpiada."},
    )
    assert event.status_code == 201, event.text

    report = client.post(
        f"/api/service-cases/{case_id}/maintenance-reports",
        headers=headers,
        json={
            "summary": "Revision tecnica completada.",
            "actions_performed": "Se verifico bateria, conexion y posicion del sensor.",
            "recommendations": "Mantener seguimiento semanal.",
            "status": "completed",
        },
    )
    assert report.status_code == 201, report.text
    assert report.json()["status"] == "completed"


def test_education_article_completion(client, db_session):
    article = EducationArticle(
        slug="test-bitacora-operativa",
        locale="es",
        title="Bitacora operativa",
        summary="Resumen",
        body="Contenido tecnico.",
        category="operacion",
    )
    db_session.add(article)
    db_session.commit()

    headers = _auth_headers(client, "cliente@silo-demo.local", "cliente123")
    listed = client.get("/api/education/articles", headers=headers)
    assert listed.status_code == 200, listed.text
    assert any(item["slug"] == "test-bitacora-operativa" for item in listed.json())

    complete = client.post(f"/api/education/articles/{article.id}/complete", headers=headers)
    assert complete.status_code == 200, complete.text
    assert complete.json()["article_id"] == article.id


def test_agro_assistant_rules_response(client, db_session):
    storage_unit = db_session.scalar(select(StorageUnit))
    response = client.post(
        "/api/agro-assistant/messages",
        headers=_auth_headers(client, "cliente@silo-demo.local", "cliente123"),
        json={"storage_unit_id": storage_unit.id, "message": "Que debo revisar hoy?"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source"] == "rules"
    assert body["facts"]
    assert body["recommended_actions"]
