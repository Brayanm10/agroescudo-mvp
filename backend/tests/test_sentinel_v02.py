from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.models import Alert, AlertContact, NotificationDelivery, SentinelDevice, SentinelJob


def _headers(client, email: str = "admin@agroescudo.local", password: str = "admin123") -> dict[str, str]:
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _contact_payload(**overrides):
    payload = {
        "company_id": 1,
        "storage_unit_id": 1,
        "name": "Responsable de planta",
        "phone_e164": "+59170000001",
        "priority": 1,
        "escalation_delay_minutes": 0,
        "receive_sms": True,
        "receive_call": True,
        "minimum_severity": "critical",
        "active": True,
    }
    payload.update(overrides)
    return payload


def _critical_reading(client):
    return client.post(
        "/api/readings",
        json={
            "device_id": "SILO-001",
            "device_token": "secret-token",
            "grain_temperature": 35.0,
            "ambient_temperature": 30.0,
            "ambient_humidity": 80.0,
            "battery_voltage": 3.9,
            "signal_quality": -61,
            "timestamp": "2026-08-09T12:00:00Z",
        },
    )


def _create_sentinel(client):
    response = client.post(
        "/api/admin/sentinel/devices",
        headers=_headers(client),
        json={"device_uid": "sentinel-home-001", "name": "AgroEscudo Sentinel Casa"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_contact_e164_scope_and_role_enforcement(client, db_session):
    created = client.post("/api/alert-contacts", headers=_headers(client), json=_contact_payload())
    assert created.status_code == 201, created.text
    assert created.json()["phone_e164"] == "+59170000001"

    invalid = client.post(
        "/api/alert-contacts",
        headers=_headers(client),
        json=_contact_payload(phone_e164="70000001"),
    )
    assert invalid.status_code == 422
    assert "E.164" in invalid.json()["detail"]

    technician = client.post(
        "/api/alert-contacts",
        headers=_headers(client, "tecnico@agroescudo.local", "tecnico123"),
        json=_contact_payload(phone_e164="+59170000002"),
    )
    assert technician.status_code == 403


def test_alert_creates_idempotent_sms_and_call_jobs(client, db_session):
    client.post("/api/alert-contacts", headers=_headers(client), json=_contact_payload())
    first = _critical_reading(client)
    second = _critical_reading(client)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    jobs = list(db_session.scalars(select(SentinelJob).order_by(SentinelJob.job_type)).all())
    assert {job.job_type for job in jobs} == {"sms", "call"}
    assert len(jobs) == 2
    assert all(job.status == "pending" for job in jobs)
    assert db_session.scalar(select(NotificationDelivery).where(NotificationDelivery.channel == "sms")) is not None


def test_minimum_severity_and_escalation_delay(client, db_session):
    client.post(
        "/api/alert-contacts",
        headers=_headers(client),
        json=_contact_payload(receive_call=False, minimum_severity="critical", escalation_delay_minutes=5),
    )
    warning = client.post(
        "/api/readings",
        json={
            "device_id": "SILO-001",
            "device_token": "secret-token",
            "grain_temperature": 31.0,
            "ambient_temperature": 27.0,
            "ambient_humidity": 60.0,
            "battery_voltage": 3.9,
            "signal_quality": -60,
            "timestamp": "2026-08-09T11:00:00Z",
        },
    )
    assert warning.status_code == 201
    assert db_session.scalar(select(SentinelJob)) is None

    critical = _critical_reading(client)
    assert critical.status_code == 201
    job = db_session.scalar(select(SentinelJob))
    assert job is not None
    assert job.not_before > job.created_at


def test_poll_claim_result_and_honest_delivery_status(client, db_session):
    contact = client.post("/api/alert-contacts", headers=_headers(client), json=_contact_payload(receive_call=False))
    assert contact.status_code == 201
    assert _critical_reading(client).status_code == 201
    sentinel = _create_sentinel(client)
    sentinel_headers = {"Authorization": f"Bearer {sentinel['token']}"}

    poll = client.post(
        "/api/sentinel/poll",
        headers=sentinel_headers,
        json={
            "device_uid": "sentinel-home-001",
            "firmware_version": "0.2.0",
            "uptime_seconds": 120,
            "wifi_rssi": -55,
            "gsm_registered": True,
            "sim_ready": True,
        },
    )
    assert poll.status_code == 200, poll.text
    assert poll.json()["job"]["type"] == "sms"
    assert poll.json()["poll_after_seconds"] >= 30

    second_poll = client.post(
        "/api/sentinel/poll",
        headers=sentinel_headers,
        json={"device_uid": "sentinel-home-001", "uptime_seconds": 121},
    )
    assert second_poll.status_code == 200
    assert second_poll.json()["job"] is None

    result = client.post(
        f"/api/sentinel/jobs/{poll.json()['job']['id']}/result",
        headers=sentinel_headers,
        json={"status": "submitted", "result_code": "SIM800_CMGS_OK", "message": None},
    )
    assert result.status_code == 200, result.text
    assert result.json()["status"] == "submitted"
    delivery = db_session.scalar(select(NotificationDelivery).where(NotificationDelivery.channel == "sms"))
    assert delivery.status == "submitted"
    assert delivery.delivered_at is None


def test_invalid_revoked_token_and_wrong_sentinel_cannot_complete(client, db_session):
    first = _create_sentinel(client)
    bad = client.post(
        "/api/sentinel/poll",
        headers={"Authorization": "Bearer invalid"},
        json={"device_uid": "sentinel-home-001", "uptime_seconds": 1},
    )
    assert bad.status_code == 401

    device = db_session.scalar(select(SentinelDevice).where(SentinelDevice.device_uid == "sentinel-home-001"))
    device.active = False
    db_session.commit()
    revoked = client.post(
        "/api/sentinel/poll",
        headers={"Authorization": f"Bearer {first['token']}"},
        json={"device_uid": "sentinel-home-001", "uptime_seconds": 2},
    )
    assert revoked.status_code == 401


def test_acknowledge_cancels_future_escalation_jobs(client, db_session):
    client.post(
        "/api/alert-contacts",
        headers=_headers(client),
        json=_contact_payload(receive_call=False, escalation_delay_minutes=10),
    )
    response = _critical_reading(client)
    alert_id = response.json()["alerts"][0]["id"]
    acknowledged = client.patch(f"/api/alerts/{alert_id}/acknowledge", headers=_headers(client))
    assert acknowledged.status_code == 200
    job = db_session.scalar(select(SentinelJob).where(SentinelJob.alert_id == alert_id))
    assert job.status == "cancelled"


def test_client_cannot_access_sentinel_admin(client):
    response = client.get(
        "/api/admin/sentinel/devices",
        headers=_headers(client, "cliente@silo-demo.local", "cliente123"),
    )
    assert response.status_code == 403


def test_test_contact_creates_queue_job_without_marking_verified(client, db_session):
    created = client.post("/api/alert-contacts", headers=_headers(client), json=_contact_payload(receive_call=False))
    response = client.post(
        f"/api/alert-contacts/{created.json()['id']}/test",
        headers=_headers(client),
        json={"channel": "sms"},
    )
    assert response.status_code == 201, response.text
    contact = db_session.get(AlertContact, created.json()["id"])
    assert contact.verified_at is None
    assert response.json()["destination_phone"].endswith("001")


def test_global_company_contact_applies_to_storage_alert(client, db_session):
    created = client.post(
        "/api/alert-contacts",
        headers=_headers(client),
        json=_contact_payload(storage_unit_id=None, receive_call=False),
    )
    assert created.status_code == 201
    assert _critical_reading(client).status_code == 201
    job = db_session.scalar(select(SentinelJob))
    assert job is not None
    assert job.alert_contact_id == created.json()["id"]


def test_call_result_is_attempted_not_answered(client, db_session):
    client.post(
        "/api/alert-contacts",
        headers=_headers(client),
        json=_contact_payload(receive_sms=False, receive_call=True),
    )
    assert _critical_reading(client).status_code == 201
    sentinel = _create_sentinel(client)
    headers = {"Authorization": f"Bearer {sentinel['token']}"}
    poll = client.post(
        "/api/sentinel/poll",
        headers=headers,
        json={"device_uid": "sentinel-home-001", "uptime_seconds": 10, "gsm_registered": True, "sim_ready": True},
    )
    job_id = poll.json()["job"]["id"]
    result = client.post(
        f"/api/sentinel/jobs/{job_id}/result",
        headers=headers,
        json={"status": "attempted", "result_code": "SIM800_CALL_STARTED"},
    )
    assert result.status_code == 200
    assert result.json()["status"] == "attempted"
    assert "answered" not in result.text.lower()


def test_failed_job_is_reprogrammed_with_backend_backoff(client, db_session):
    client.post("/api/alert-contacts", headers=_headers(client), json=_contact_payload(receive_call=False))
    assert _critical_reading(client).status_code == 201
    sentinel = _create_sentinel(client)
    headers = {"Authorization": f"Bearer {sentinel['token']}"}
    poll = client.post(
        "/api/sentinel/poll",
        headers=headers,
        json={"device_uid": "sentinel-home-001", "uptime_seconds": 10},
    )
    result = client.post(
        f"/api/sentinel/jobs/{poll.json()['job']['id']}/result",
        headers=headers,
        json={"status": "failed", "result_code": "GSM_NOT_REGISTERED", "message": "Sin registro GSM"},
    )
    assert result.status_code == 200
    assert result.json()["status"] == "failed"
    job = db_session.get(SentinelJob, result.json()["id"])
    not_before = job.not_before if job.not_before.tzinfo else job.not_before.replace(tzinfo=timezone.utc)
    assert not_before > datetime.now(timezone.utc)
    assert job.completed_at is None


def test_expired_lease_rejects_late_result(client, db_session):
    client.post("/api/alert-contacts", headers=_headers(client), json=_contact_payload(receive_call=False))
    assert _critical_reading(client).status_code == 201
    sentinel = _create_sentinel(client)
    headers = {"Authorization": f"Bearer {sentinel['token']}"}
    poll = client.post(
        "/api/sentinel/poll",
        headers=headers,
        json={"device_uid": "sentinel-home-001", "uptime_seconds": 10},
    )
    job = db_session.get(SentinelJob, poll.json()["job"]["id"])
    job.lease_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    db_session.commit()
    result = client.post(
        f"/api/sentinel/jobs/{job.id}/result",
        headers=headers,
        json={"status": "submitted", "result_code": "SIM800_CMGS_OK"},
    )
    assert result.status_code == 409
    assert "lease" in result.json()["detail"].lower()
