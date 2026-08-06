"""Create a consistent, portable PostgreSQL data snapshot without pg_dump.

This utility is intended for constrained operator workstations where PostgreSQL
client binaries are unavailable. It exports every table in the public schema,
its reflected structure, row counts and per-table SHA-256 checksums into a ZIP.
The database transaction is repeatable-read and read-only.

It does not replace pg_dump for disaster recovery, but provides independently
verifiable evidence and a complete row-level snapshot before additive Alembic
migrations.
"""

from __future__ import annotations

import argparse
import base64
from datetime import date, datetime, time, timezone
from decimal import Decimal
import hashlib
import io
import json
import os
from pathlib import Path
from typing import Any
from uuid import UUID
import zipfile

import psycopg
from psycopg import sql


def serialize(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime, date, time)):
        return {"__type__": type(value).__name__, "value": value.isoformat()}
    if isinstance(value, Decimal):
        return {"__type__": "decimal", "value": str(value)}
    if isinstance(value, UUID):
        return {"__type__": "uuid", "value": str(value)}
    if isinstance(value, memoryview):
        value = value.tobytes()
    if isinstance(value, bytes):
        return {"__type__": "bytes", "base64": base64.b64encode(value).decode("ascii")}
    return {"__type__": type(value).__name__, "value": str(value)}


def normalize_url(url: str) -> str:
    if url.startswith("postgresql+psycopg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    raise ValueError("DATABASE_URL debe apuntar a PostgreSQL.")


def export_snapshot(database_url: str, output_dir: Path, label: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    issued_at = datetime.now(timezone.utc)
    filename = f"agroescudo-postgres-{label}-{issued_at:%Y%m%dT%H%M%SZ}.zip"
    target = output_dir / filename
    manifest: dict[str, Any] = {
        "format": "agroescudo-portable-postgres-snapshot-v1",
        "created_at": issued_at.isoformat(),
        "transaction": "REPEATABLE READ READ ONLY",
        "schema": "public",
        "tables": {},
    }

    connection_url = normalize_url(database_url).replace("postgresql+psycopg://", "postgresql://", 1)
    with psycopg.connect(connection_url, connect_timeout=20) as connection:
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        tables = [
            row[0]
            for row in connection.execute(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
                """
            ).fetchall()
        ]
        columns = connection.execute(
            """
            SELECT table_name, ordinal_position, column_name, data_type,
                   udt_name, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_schema = 'public'
            ORDER BY table_name, ordinal_position
            """
        ).fetchall()
        constraints = connection.execute(
            """
            SELECT tc.table_name, tc.constraint_name, tc.constraint_type,
                   kcu.column_name, ccu.table_name AS foreign_table_name,
                   ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints tc
            LEFT JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            LEFT JOIN information_schema.constraint_column_usage ccu
              ON tc.constraint_name = ccu.constraint_name
             AND tc.table_schema = ccu.table_schema
            WHERE tc.table_schema = 'public'
            ORDER BY tc.table_name, tc.constraint_name, kcu.ordinal_position
            """
        ).fetchall()
        indexes = connection.execute(
            """
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
            """
        ).fetchall()
        schema_snapshot = {
            "columns": [
                {
                    "table": row[0],
                    "position": row[1],
                    "name": row[2],
                    "data_type": row[3],
                    "udt_name": row[4],
                    "nullable": row[5],
                    "default": row[6],
                }
                for row in columns
            ],
            "constraints": [
                {
                    "table": row[0],
                    "name": row[1],
                    "type": row[2],
                    "column": row[3],
                    "foreign_table": row[4],
                    "foreign_column": row[5],
                }
                for row in constraints
            ],
            "indexes": [
                {"table": row[0], "name": row[1], "definition": row[2]}
                for row in indexes
            ],
        }

        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for table_name in tables:
                row_count = connection.execute(
                    sql.SQL("SELECT count(*) FROM {}.{}").format(
                        sql.Identifier("public"),
                        sql.Identifier(table_name),
                    )
                ).fetchone()[0]
                checksum = hashlib.sha256()
                entry_name = f"tables/{table_name}.csv"
                copy_sql = sql.SQL(
                    "COPY {}.{} TO STDOUT WITH (FORMAT CSV, HEADER TRUE, ENCODING 'UTF8')"
                ).format(sql.Identifier("public"), sql.Identifier(table_name))
                with archive.open(entry_name, "w") as stream:
                    with connection.cursor().copy(copy_sql) as copy:
                        for block in copy:
                            chunk = bytes(block)
                            checksum.update(chunk)
                            stream.write(chunk)
                manifest["tables"][table_name] = {
                    "rows": row_count,
                    "sha256": checksum.hexdigest().upper(),
                    "entry": entry_name,
                }

            revision_row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
            manifest["alembic_revision"] = revision_row[0] if revision_row else None
            archive.writestr(
                "schema.json",
                json.dumps(schema_snapshot, ensure_ascii=False, indent=2, sort_keys=True),
            )
            archive.writestr(
                "manifest.json",
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
            )
        connection.rollback()

    archive_hash = hashlib.sha256(target.read_bytes()).hexdigest().upper()
    target.with_suffix(".zip.sha256").write_text(
        f"{archive_hash}  {target.name}\n",
        encoding="ascii",
    )
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="../var/backups")
    parser.add_argument("--label", default="pre-migration")
    args = parser.parse_args()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL no configurada.")
    target = export_snapshot(database_url, Path(args.output_dir).resolve(), args.label)
    print(f"Backup created: {target}")
    print(f"Checksum file: {target.with_suffix('.zip.sha256')}")


if __name__ == "__main__":
    main()
