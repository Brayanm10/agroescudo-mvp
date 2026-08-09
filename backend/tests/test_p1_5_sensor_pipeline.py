import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.domain.metric_registry import METRIC_REGISTRY, METRICS_BY_CODE, METRICS_BY_ID
from app.models import (
    Alert,
    Device,
    DeviceChannel,
    MetricDefinition,
    MetricReading,
    OperationalLog,
    SensorReading,
    TelemetryEvent,
)
from app.services.device_capabilities import ensure_metric_registry, sync_device_channels


GATEWAY_ID = "GW-CBBA-001"
GATEWAY_SECRET = "gateway-secret-001"


def _headers(client, email="admin@agroescudo.local", password="admin123"):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _signed_headers(body: bytes, nonce: str):
    timestamp = str(int(datetime.now(timezone.utc).timestamp()))
    body_hash = hashlib.sha256(body).hexdigest()
    message = f"{GATEWAY_ID}{timestamp}{nonce}{body_hash}".encode()
    signature = hmac.new(GATEWAY_SECRET.encode(), message, hashlib.sha256).hexdigest()
    return {
        "X-Agro-Gateway-ID": GATEWAY_ID,
        "X-Agro-Timestamp": timestamp,
        "X-Agro-Nonce": nonce,
        "X-Agro-Signature": signature,
        "Content-Type": "application/json",
    }


def _post_event(client, *, sequence=1, metrics=None, nonce=None, sampled_at=None):
    request_nonce = nonce or f"p1-5-{sequence}"
    payload = {
        "gateway_id": GATEWAY_ID,
        "batch_id": f"p1-5-{sequence}-{request_nonce}",
        "sent_at": datetime.now(timezone.utc).isoformat(),
        "protocol_version": 4,
        "events": [
            {
                "device_id": "SILO-001",
                "boot_id": 7001,
                "sequence": sequence,
                "sample_counter": sequence,
                "sampled_at": (sampled_at or datetime.now(timezone.utc)).isoformat(),
                "time_quality": "SYNCED",
                "firmware_version": "1.5.0",
                "protocol_version": 4,
                "capabilities_version": 2,
                "sensor_status_flags": 0,
                "metrics": metrics
                or [
                    {
                        "channel_key": "grain_temp_1",
                        "metric_code": "GRAIN_TEMPERATURE_C",
                        "raw_value": 25.4,
                        "unit": "degC",
                        "quality": "VALID",
                    },
                    {
                        "channel_key": "ambient_rh_1",
                        "metric_code": "AMBIENT_RELATIVE_HUMIDITY_PCT",
                        "raw_value": 63.2,
                        "unit": "percent",
                        "quality": "VALID",
                    },
                ],
            }
        ],
    }
    body = json.dumps(payload, separators=(",", ":")).encode()
    return client.post(
        "/api/iot/v1/ingest/batch",
        content=body,
        headers=_signed_headers(body, request_nonce),
    )


def _prepare_device(db_session):
    ensure_metric_registry(db_session)
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    device.device_type = "silo_sensor"
    sync_device_channels(db_session, device, template_code="SILO_SENSOR_BASE")
    db_session.commit()
    return device


def test_registry_ids_and_codes_are_unique_and_stable():
    assert len(METRIC_REGISTRY) == 15
    assert len(METRICS_BY_ID) == len(METRIC_REGISTRY)
    assert len(METRICS_BY_CODE) == len(METRIC_REGISTRY)
    assert METRICS_BY_ID[1].metric_code == "GRAIN_TEMPERATURE_C"
    assert METRICS_BY_ID[3].metric_code == "AMBIENT_RELATIVE_HUMIDITY_PCT"
    assert METRICS_BY_ID[6].metric_code == "LEVEL_DISTANCE_MM"
    assert METRICS_BY_ID[15].metric_code == "TIME_QUALITY"


def test_explicit_metrics_dual_write_without_positional_mapping(client, db_session):
    device = _prepare_device(db_session)
    response = _post_event(client, sequence=4101)

    assert response.status_code == 200
    assert response.json()["results"][0]["canonical_status"] == "ACCEPTED"
    event = db_session.scalar(select(TelemetryEvent))
    rows = db_session.scalars(
        select(MetricReading).where(MetricReading.telemetry_event_id == event.id)
    ).all()
    legacy = db_session.scalar(select(SensorReading))
    assert event.device_id == device.id
    assert {(row.metric_code, row.raw_value) for row in rows} == {
        ("GRAIN_TEMPERATURE_C", 25.4),
        ("AMBIENT_RELATIVE_HUMIDITY_PCT", 63.2),
    }
    assert legacy.grain_temperature == 25.4
    assert legacy.ambient_humidity == 63.2


def test_duplicate_event_does_not_create_second_normalized_event(client, db_session):
    _prepare_device(db_session)
    first = _post_event(client, sequence=4102, nonce="p1-5-dup-a")
    duplicate = _post_event(client, sequence=4102, nonce="p1-5-dup-b")

    assert first.json()["results"][0]["canonical_status"] == "ACCEPTED"
    assert duplicate.json()["results"][0]["canonical_status"] == "DUPLICATE"
    assert len(db_session.scalars(select(TelemetryEvent)).all()) == 1


def test_unknown_or_mismatched_channel_is_quarantined(client, db_session):
    _prepare_device(db_session)
    response = _post_event(
        client,
        sequence=4103,
        metrics=[
            {
                "channel_key": "ambient_rh_1",
                "metric_code": "GRAIN_TEMPERATURE_C",
                "raw_value": 22.5,
                "unit": "degC",
                "quality": "VALID",
            }
        ],
    )

    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["canonical_status"] == "QUARANTINED"
    assert "no pertenece" in result["detail"]
    assert db_session.scalar(select(TelemetryEvent)) is None
    assert db_session.scalar(select(SensorReading)) is None


def test_dashboard_schema_and_series_are_exact_per_channel_and_role(client, db_session):
    device = _prepare_device(db_session)
    _post_event(client, sequence=4104)
    admin = _headers(client)
    customer = _headers(client, "cliente@silo-demo.local", "cliente123")

    schema = client.get(
        f"/api/devices/{device.id}/dashboard-schema",
        headers=customer,
    )
    assert schema.status_code == 200
    metric_codes = {item["metric_code"] for item in schema.json()["metrics"]}
    assert "GRAIN_TEMPERATURE_C" in metric_codes
    assert "SIGNAL_RSSI_DBM" not in metric_codes
    assert schema.json()["thresholds"]["grain_temperature"] == 30.0
    series = client.get(
        f"/api/devices/{device.id}/metrics/GRAIN_TEMPERATURE_C/readings",
        params={"channel_key": "grain_temp_1", "resolution": "raw"},
        headers=customer,
    )
    assert series.status_code == 200
    assert series.json()["points"][0]["raw_value"] is None
    assert series.json()["points"][0]["value"] == 25.4

    technical = client.get(
        f"/api/devices/{device.id}/metrics/GRAIN_TEMPERATURE_C/readings",
        params={"channel_key": "grain_temp_1"},
        headers=admin,
    )
    assert technical.json()["points"][0]["raw_value"] == 25.4


def test_hiding_chart_preserves_metric_history(client, db_session):
    device = _prepare_device(db_session)
    _post_event(client, sequence=4105)
    channel = db_session.scalar(
        select(DeviceChannel).where(
            DeviceChannel.device_id == device.id,
            DeviceChannel.channel_key == "grain_temp_1",
        )
    )
    response = client.patch(
        f"/api/devices/{device.id}/channels/{channel.id}",
        json={"chart_enabled": False},
        headers=_headers(client),
    )

    assert response.status_code == 200
    assert response.json()["chart_enabled"] is False
    assert db_session.scalar(select(MetricReading)) is not None
    series = client.get(
        f"/api/devices/{device.id}/metrics/GRAIN_TEMPERATURE_C/readings",
        params={"channel_key": "grain_temp_1"},
        headers=_headers(client),
    )
    assert len(series.json()["points"]) == 1


def test_aggregated_series_preserves_extremes_and_reports_real_gaps(client, db_session):
    device = _prepare_device(db_session)
    device.expected_reading_interval_minutes = 15
    db_session.commit()
    start = datetime.now(timezone.utc).replace(minute=5, second=0, microsecond=0) - timedelta(hours=2)
    for sequence, sampled_at, value in (
        (4201, start, 20.0),
        (4202, start + timedelta(minutes=10), 40.0),
        (4203, start + timedelta(hours=2), 30.0),
    ):
        response = _post_event(
            client,
            sequence=sequence,
            sampled_at=sampled_at,
            metrics=[
                {
                    "channel_key": "grain_temp_1",
                    "metric_code": "GRAIN_TEMPERATURE_C",
                    "raw_value": value,
                    "unit": "degC",
                    "quality": "VALID",
                }
            ],
        )
        assert response.status_code == 200

    response = client.get(
        f"/api/devices/{device.id}/metrics/GRAIN_TEMPERATURE_C/readings",
        params={
            "channel_key": "grain_temp_1",
            "resolution": "1h",
            "from": start.isoformat(),
            "to": (start + timedelta(hours=3)).isoformat(),
            "order": "asc",
        },
        headers=_headers(client),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["maximum"] == 40.0
    assert payload["summary"]["sample_count"] == 3
    assert payload["points"][0]["bucket_min"] == 20.0
    assert payload["points"][0]["bucket_max"] == 40.0
    assert payload["points"][0]["sample_count"] == 2
    assert len(payload["gaps"]) == 1
    assert payload["gaps"][0]["duration_seconds"] == 6600


def test_chart_context_returns_device_events_and_actions(client, db_session):
    device = _prepare_device(db_session)
    sampled_at = datetime.now(timezone.utc) - timedelta(minutes=20)
    _post_event(
        client,
        sequence=4204,
        sampled_at=sampled_at,
        metrics=[
            {
                "channel_key": "grain_temp_1",
                "metric_code": "GRAIN_TEMPERATURE_C",
                "raw_value": 36.0,
                "unit": "degC",
                "quality": "VALID",
            }
        ],
    )
    alert = db_session.scalar(select(Alert).where(Alert.device_id == device.id))
    db_session.add(
        OperationalLog(
            company_id=device.company_id,
            site_id=device.site_id,
            storage_unit_id=device.storage_unit_id,
            device_id=device.id,
            alert_id=alert.id,
            category="corrective_action",
            action_taken="Aireacion preventiva",
            operator_name="Tecnico asignado",
            notes="Temperatura en descenso.",
            timestamp=sampled_at + timedelta(minutes=8),
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/devices/{device.id}/chart-context",
        params={
            "from": (sampled_at - timedelta(minutes=5)).isoformat(),
            "to": (sampled_at + timedelta(hours=1)).isoformat(),
        },
        headers=_headers(client, "cliente@silo-demo.local", "cliente123"),
    )

    assert response.status_code == 200
    assert response.json()["events"][0]["metric_code"] == "GRAIN_TEMPERATURE_C"
    assert response.json()["events"][0]["severity"] in {"warning", "critical"}
    assert response.json()["actions"][0]["title"] == "Aireacion preventiva"


def test_alert_is_traced_to_canonical_metric_and_channel(client, db_session):
    device = _prepare_device(db_session)
    response = _post_event(
        client,
        sequence=4106,
        metrics=[
            {
                "channel_key": "grain_temp_1",
                "metric_code": "GRAIN_TEMPERATURE_C",
                "raw_value": 35.0,
                "unit": "degC",
                "quality": "VALID",
            }
        ],
    )

    assert response.json()["results"][0]["canonical_status"] == "ACCEPTED"
    alert = db_session.scalar(select(Alert).where(Alert.alert_type == "grain_temperature_high"))
    channel = db_session.get(DeviceChannel, alert.sensor_channel_id)
    definition = db_session.get(MetricDefinition, alert.metric_definition_id)
    assert channel.channel_key == "grain_temp_1"
    assert definition.metric_code == "GRAIN_TEMPERATURE_C"


def test_legacy_channel_remains_visible_through_canonical_dashboard_schema(
    client, db_session
):
    ensure_metric_registry(db_session)
    device = db_session.scalar(select(Device).where(Device.external_id == "SILO-001"))
    db_session.add(
        DeviceChannel(
            device_id=device.id,
            name="Temperatura de grano legacy",
            code="grain_temperature",
            channel_key="grain_temperature",
            metric_type="grain_temperature",
            metric_codes="grain_temperature",
            unit="C",
            canonical_unit="C",
            is_active=True,
            is_installed=True,
            is_enabled=True,
            is_visible_to_client=True,
            chart_enabled=True,
            alert_enabled=True,
            status="ACTIVE",
        )
    )
    db_session.commit()

    response = client.get(
        f"/api/devices/{device.id}/dashboard-schema",
        headers=_headers(client, "cliente@silo-demo.local", "cliente123"),
    )

    assert response.status_code == 200
    metric = next(
        item
        for item in response.json()["metrics"]
        if item["metric_code"] == "GRAIN_TEMPERATURE_C"
    )
    assert metric["channel_key"] == "grain_temperature"
