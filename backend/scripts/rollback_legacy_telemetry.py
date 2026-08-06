from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sqlalchemy import delete, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models import (
    LegacyMappingResult,
    LegacyMigrationBatch,
    MetricReading,
    TelemetryEvent,
    utc_now,
)


def rollback(batch_id: str, *, confirm: bool) -> dict[str, object]:
    if not confirm:
        raise RuntimeError("Rollback cancelado. Agrega --confirm.")
    with SessionLocal() as db:
        batch = db.scalar(
            select(LegacyMigrationBatch).where(LegacyMigrationBatch.batch_id == batch_id)
        )
        if batch is None:
            raise RuntimeError("Batch no encontrado.")
        metric_count = db.query(MetricReading).filter(
            MetricReading.migration_batch_id == batch_id
        ).count()
        event_count = db.query(TelemetryEvent).filter(
            TelemetryEvent.migration_batch_id == batch_id
        ).count()
        mapping_count = db.query(LegacyMappingResult).filter(
            LegacyMappingResult.migration_batch_id == batch_id
        ).count()
        db.execute(delete(MetricReading).where(MetricReading.migration_batch_id == batch_id))
        db.execute(delete(TelemetryEvent).where(TelemetryEvent.migration_batch_id == batch_id))
        db.execute(
            delete(LegacyMappingResult).where(
                LegacyMappingResult.migration_batch_id == batch_id
            )
        )
        batch.status = "ROLLED_BACK"
        batch.rolled_back_at = utc_now()
        db.commit()
        return {
            "batch_id": batch_id,
            "metric_readings_removed": metric_count,
            "telemetry_events_removed": event_count,
            "mapping_results_removed": mapping_count,
            "legacy_rows_removed": 0,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("batch_id")
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    print(json.dumps(rollback(args.batch_id, confirm=args.confirm), indent=2))
