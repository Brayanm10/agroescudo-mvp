"""Reset operational monitoring data while preserving identity and organizations.

Run from backend/:
    py -3.13 scripts/reset_operational_data.py --dry-run
    py -3.13 scripts/reset_operational_data.py --execute --yes-really-reset

PostgreSQL execution additionally requires --backup-confirmed with a backup reference.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.engine.url import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.db.base import Base
from app.db.session import SessionLocal
from app.models import Device, StorageUnit, User


PROTECTED_TABLES = {"users", "companies", "sites", "education_articles", "metric_definitions"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Elimina unidades, dispositivos y datos dependientes sin borrar usuarios.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--yes-really-reset", action="store_true")
    parser.add_argument("--backup-confirmed", help="Ruta o referencia verificable del backup PostgreSQL.")
    return parser.parse_args()


def discover_targets(db) -> dict[str, set[int]]:
    tables = Base.metadata.tables
    targets: dict[str, set[int]] = {
        "storage_units": set(db.scalars(select(StorageUnit.id)).all()),
        "devices": set(db.scalars(select(Device.id)).all()),
    }
    changed = True
    while changed:
        changed = False
        for table in tables.values():
            if table.name in PROTECTED_TABLES or len(table.primary_key.columns) != 1:
                continue
            primary_key = next(iter(table.primary_key.columns))
            for foreign_key in table.foreign_keys:
                parent_name = foreign_key.column.table.name
                parent_ids = targets.get(parent_name, set())
                if not parent_ids:
                    continue
                row_ids = set(db.scalars(select(primary_key).where(foreign_key.parent.in_(parent_ids))).all())
                existing = targets.setdefault(table.name, set())
                before = len(existing)
                existing.update(row_ids)
                changed = changed or len(existing) != before
    return {name: ids for name, ids in targets.items() if ids}


def sqlite_backup(database_url: str) -> Path | None:
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite") or not url.database or url.database == ":memory:":
        return None
    source = Path(url.database).resolve()
    if not source.exists():
        return None
    backup_dir = source.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = backup_dir / f"{source.stem}-before-operational-reset-{stamp}{source.suffix}"
    shutil.copy2(source, destination)
    return destination


def main() -> None:
    args = parse_args()
    with SessionLocal() as db:
        user_count_before = db.scalar(select(func.count(User.id))) or 0
        targets = discover_targets(db)
        print("RESET OPERATIVO - CONTEOS")
        for table_name in sorted(targets):
            print(f"  {table_name}: {len(targets[table_name])}")
        print(f"  usuarios protegidos: {user_count_before}")

        if args.dry_run:
            print("DRY RUN: no se modificaron datos.")
            return
        if not args.yes_really_reset:
            raise SystemExit("Falta --yes-really-reset. No se modificaron datos.")

        database_url = str(db.get_bind().url)
        if database_url.startswith("postgresql") and not args.backup_confirmed:
            raise SystemExit("PostgreSQL requiere --backup-confirmed <referencia>. No se modificaron datos.")
        backup = sqlite_backup(database_url)
        if database_url.startswith("sqlite") and backup is None:
            raise SystemExit("No se pudo crear el backup SQLite. No se modificaron datos.")
        if backup:
            print(f"Backup SQLite: {backup}")

        for table in reversed(Base.metadata.sorted_tables):
            ids = targets.get(table.name)
            if not ids or table.name in PROTECTED_TABLES or len(table.primary_key.columns) != 1:
                continue
            primary_key = next(iter(table.primary_key.columns))
            db.execute(table.delete().where(primary_key.in_(ids)))
        db.commit()

        user_count_after = db.scalar(select(func.count(User.id))) or 0
        unit_count = db.scalar(select(func.count(StorageUnit.id))) or 0
        device_count = db.scalar(select(func.count(Device.id))) or 0
        if user_count_before != user_count_after:
            raise RuntimeError("La cantidad de usuarios cambió; restaura el backup inmediatamente.")
        print(f"Usuarios antes/después: {user_count_before}/{user_count_after}")
        print(f"Unidades restantes: {unit_count}")
        print(f"Dispositivos restantes: {device_count}")
        print("RESET COMPLETADO")


if __name__ == "__main__":
    main()
