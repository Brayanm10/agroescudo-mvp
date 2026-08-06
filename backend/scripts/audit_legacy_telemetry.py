from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.session import SessionLocal
from app.models import Device, IotReading, SensorReading


FIELDS = {
    SensorReading: (
        "grain_temperature",
        "ambient_temperature",
        "ambient_humidity",
        "battery_voltage",
        "signal_quality",
        "level_distance_cm",
        "level_percent",
        "soil_moisture_percent",
        "soil_temperature_c",
        "sensor_status",
    ),
    IotReading: (
        "grain_temp_c_x100",
        "air_temp_c_x100",
        "rh_x100",
        "battery_mv",
        "soil_moisture_x100",
        "soil_moisture_raw",
        "soil_temp_c_x100",
        "level_distance_mm",
        "level_percent_x100",
        "sensor_status",
        "rssi_dbm",
        "snr_db_x10",
    ),
}


def audit() -> dict[str, object]:
    with SessionLocal() as db:
        result: dict[str, object] = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "database": db.get_bind().dialect.name,
            "tables": {},
            "devices": db.scalar(select(func.count(Device.id))) or 0,
        }
        for model, fields in FIELDS.items():
            rows = list(db.scalars(select(model).order_by(model.id)).all())
            timestamps = [row.timestamp for row in rows if row.timestamp is not None]
            nulls = {
                field: sum(getattr(row, field) is None for row in rows)
                for field in fields
            }
            checksum = hashlib.sha256()
            duplicate_keys: Counter[tuple[object, ...]] = Counter()
            for row in rows:
                serialized = {
                    "id": row.id,
                    "device_id": row.device_id,
                    "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                    **{field: getattr(row, field) for field in fields},
                }
                checksum.update(
                    json.dumps(serialized, sort_keys=True, default=str, separators=(",", ":")).encode()
                )
                if model is IotReading:
                    duplicate_keys[(row.device_id, row.boot_id, row.sequence)] += 1
                else:
                    duplicate_keys[(row.device_id, row.timestamp)] += 1
            result["tables"][model.__tablename__] = {
                "count": len(rows),
                "min_timestamp": min(timestamps).isoformat() if timestamps else None,
                "max_timestamp": max(timestamps).isoformat() if timestamps else None,
                "null_counts": nulls,
                "duplicate_groups": sum(value > 1 for value in duplicate_keys.values()),
                "logical_sha256": checksum.hexdigest(),
            }
        return result


def markdown(report: dict[str, object]) -> str:
    lines = [
        "# DATA MAPPING AUDIT - P1.5",
        "",
        f"Generado: {report['generated_at']}",
        f"Motor: `{report['database']}`",
        f"Dispositivos: {report['devices']}",
        "",
        "## Tablas legacy",
        "",
        "| Tabla | Filas | Fecha minima | Fecha maxima | Duplicados | SHA-256 logico |",
        "|---|---:|---|---|---:|---|",
    ]
    for table, data in report["tables"].items():
        lines.append(
            f"| {table} | {data['count']} | {data['min_timestamp'] or '-'} | "
            f"{data['max_timestamp'] or '-'} | {data['duplicate_groups']} | `{data['logical_sha256']}` |"
        )
    lines.extend(
        [
            "",
            "## Proteccion",
            "",
            "- Esta auditoria es solo lectura.",
            "- No elimina, actualiza ni recalcula filas legacy.",
            "- Los nulos se registran por campo en el JSON de evidencia.",
            "- La migracion productiva requiere `pg_dump` verificado y ejecucion previa en copia.",
        ]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", default="../var/audit/p1_5_legacy_audit.json")
    parser.add_argument("--markdown", default="../docs/DATA_MAPPING_AUDIT.md")
    args = parser.parse_args()
    report = audit()
    json_path = Path(args.json).resolve()
    markdown_path = Path(args.markdown).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    markdown_path.write_text(markdown(report), encoding="utf-8")
    print(json_path)
    print(markdown_path)
