from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.domain.metric_registry import (
    AMBIGUOUS_LEGACY_FIELDS,
    LEGACY_FIELD_MAPPING,
    METRICS_BY_CODE,
)
from app.models import (
    Device,
    DeviceChannel,
    LegacyMappingResult,
    LegacyMigrationBatch,
    MetricDefinition,
    MetricReading,
    SensorReading,
    TelemetryEvent,
    utc_now,
)
from app.services.device_capabilities import channel_accepts_metric


RULE_VERSION = "p1.5-v1"
CLASSIFICATIONS = ("SAFE_TO_MIGRATE", "REQUIRES_MAPPING", "QUARANTINED", "INVALID", "DUPLICATE")
PHYSICAL_FIELDS = {
    "grain_temperature": (-40, 100),
    "ambient_temperature": (-40, 80),
    "ambient_humidity": (0, 100),
    "battery_voltage": (0, 6),
    "level_distance_cm": (2, 2000),
    "level_percent": (0, 100),
    "soil_moisture_percent": (0, 100),
    "soil_temperature_c": (-40, 80),
}


def classify(
    row: SensorReading,
    device: Device | None,
    channels: dict[str, DeviceChannel],
    duplicate: bool,
) -> tuple[str, str]:
    if duplicate:
        return "DUPLICATE", "Misma combinacion device_id + timestamp; fuente conservada."
    if device is None:
        return "QUARANTINED", "Dispositivo inexistente."
    if row.timestamp is None:
        return "INVALID", "Timestamp ausente."
    for field, (minimum, maximum) in PHYSICAL_FIELDS.items():
        value = getattr(row, field)
        if value is not None and not minimum <= value <= maximum:
            return "INVALID", f"{field} fuera de rango fisico."
    non_null = [
        field
        for field in LEGACY_FIELD_MAPPING
        if hasattr(row, field) and getattr(row, field) is not None
    ]
    if not non_null:
        return "INVALID", "Lectura sin metricas."
    if row.soil_temperature_c is not None:
        return "REQUIRES_MAPPING", "Temperatura de suelo legacy no tiene metrica canonica P1.5 confirmada."
    for field in non_null:
        channel_key, metric_code = LEGACY_FIELD_MAPPING[field]
        channel = channels.get(channel_key)
        if channel is None or not channel_accepts_metric(channel, metric_code):
            return "REQUIRES_MAPPING", f"Falta mapeo confirmado para {field}."
    return "SAFE_TO_MIGRATE", "Dispositivo, variable, unidad, timestamp y canal inequivocos."


def migrate(*, apply: bool, batch_id: str | None = None) -> dict[str, object]:
    batch_id = batch_id or f"legacy-{datetime.now(timezone.utc):%Y%m%d%H%M%S}-{uuid4().hex[:8]}"
    with SessionLocal() as db:
        existing_batch = db.scalar(
            select(LegacyMigrationBatch).where(LegacyMigrationBatch.batch_id == batch_id)
        )
        if existing_batch:
            raise RuntimeError("El batch_id ya existe; usa otro identificador.")
        rows = list(db.scalars(select(SensorReading).order_by(SensorReading.id)).all())
        duplicate_keys = Counter((row.device_id, row.timestamp) for row in rows)
        seen_keys: set[tuple[int, datetime]] = set()
        checksum = hashlib.sha256()
        counts = Counter()
        batch = LegacyMigrationBatch(
            batch_id=batch_id,
            mapping_rule_version=RULE_VERSION,
            source_table="sensor_readings",
            status="RUNNING",
            dry_run=not apply,
            original_count=len(rows),
        )
        db.add(batch)
        definitions = {
            item.metric_code: item
            for item in db.scalars(select(MetricDefinition)).all()
        }
        for row in rows:
            key = (row.device_id, row.timestamp)
            duplicate = key in seen_keys and duplicate_keys[key] > 1
            seen_keys.add(key)
            device = db.get(Device, row.device_id)
            channels = {
                item.channel_key: item
                for item in db.scalars(
                    select(DeviceChannel).where(DeviceChannel.device_id == row.device_id)
                ).all()
            }
            classification, reason = classify(row, device, channels, duplicate)
            counts[classification] += 1
            checksum.update(f"{row.id}|{row.device_id}|{row.timestamp.isoformat()}".encode())
            mapped_fields = [
                field
                for field in LEGACY_FIELD_MAPPING
                if hasattr(row, field) and getattr(row, field) is not None
            ]
            ambiguous_fields = [
                field
                for field in AMBIGUOUS_LEGACY_FIELDS
                if hasattr(row, field) and getattr(row, field) is not None
            ]
            for field in mapped_fields + ambiguous_fields or ["__row__"]:
                channel_key, metric_code = LEGACY_FIELD_MAPPING.get(field, (None, None))
                definition = METRICS_BY_CODE.get(metric_code or "")
                db.add(
                    LegacyMappingResult(
                        migration_batch_id=batch_id,
                        legacy_table="sensor_readings",
                        legacy_row_id=row.id,
                        legacy_field=field,
                        classification=classification,
                        device_type=device.device_type if device else None,
                        sensor_type=channels.get(channel_key).sensor_type if channel_key in channels else None,
                        channel_key=channel_key,
                        metric_code=metric_code,
                        canonical_unit=definition.canonical_unit if definition else None,
                        reason=reason,
                        raw_value_text=str(getattr(row, field)) if field != "__row__" else None,
                    )
                )
            if apply and classification == "SAFE_TO_MIGRATE" and device is not None:
                event = TelemetryEvent(
                    company_id=row.company_id,
                    storage_unit_id=row.storage_unit_id,
                    device_id=row.device_id,
                    sensor_reading_id=row.id,
                    boot_id=-1,
                    sequence=row.id,
                    sample_counter=row.id,
                    sampled_at=row.timestamp,
                    received_at_cloud=row.received_at,
                    time_quality="LEGACY_UNVERSIONED",
                    firmware_version=None,
                    protocol_version=0,
                    capabilities_version=device.capabilities_version,
                    sensor_status_flags=row.sensor_status or 0,
                    quality_summary="LEGACY_MIGRATED",
                    migration_classification=classification,
                    legacy_table="sensor_readings",
                    legacy_row_id=row.id,
                    migration_batch_id=batch_id,
                    mapping_rule_version=RULE_VERSION,
                    migrated_at=utc_now(),
                )
                db.add(event)
                db.flush()
                for field in mapped_fields:
                    channel_key, metric_code = LEGACY_FIELD_MAPPING[field]
                    channel = channels[channel_key]
                    definition = definitions[metric_code]
                    raw = float(getattr(row, field))
                    if field == "level_distance_cm":
                        raw *= 10
                    elif field == "battery_voltage":
                        raw *= 1000
                    db.add(
                        MetricReading(
                            telemetry_event_id=event.id,
                            company_id=row.company_id,
                            storage_unit_id=row.storage_unit_id,
                            device_id=row.device_id,
                            sensor_channel_id=channel.id,
                            metric_definition_id=definition.id,
                            metric_code=metric_code,
                            raw_value=raw,
                            display_value=raw,
                            canonical_unit=definition.canonical_unit,
                            quality_status="LEGACY_UNVERSIONED",
                            sampled_at=row.timestamp,
                            received_at=row.received_at,
                            legacy_table="sensor_readings",
                            legacy_row_id=row.id,
                            migration_batch_id=batch_id,
                            mapping_rule_version=RULE_VERSION,
                            migrated_at=utc_now(),
                        )
                    )
        batch.safe_count = counts["SAFE_TO_MIGRATE"]
        batch.requires_mapping_count = counts["REQUIRES_MAPPING"]
        batch.quarantined_count = counts["QUARANTINED"]
        batch.invalid_count = counts["INVALID"]
        batch.duplicate_count = counts["DUPLICATE"]
        batch.source_checksum = checksum.hexdigest()
        reconciled = sum(counts[name] for name in CLASSIFICATIONS) == len(rows)
        batch.reconciliation_json = json.dumps(
            {"classification_sum": sum(counts.values()), "reconciled": reconciled},
            sort_keys=True,
        )
        batch.status = "DRY_RUN_COMPLETE" if not apply else "APPLIED"
        batch.completed_at = utc_now()
        db.commit()
        return {
            "batch_id": batch_id,
            "dry_run": not apply,
            "original": len(rows),
            **{name.lower(): counts[name] for name in CLASSIFICATIONS},
            "classification_sum": sum(counts.values()),
            "reconciled": reconciled,
            "zero_legacy_deletions": True,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Escribe solo en tablas P1.5.")
    parser.add_argument("--batch-id")
    arguments = parser.parse_args()
    print(json.dumps(migrate(apply=arguments.apply, batch_id=arguments.batch_id), indent=2))
