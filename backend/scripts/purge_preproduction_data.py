"""Explicit, transactional removal of selected preproduction companies.

Run from backend/. This never changes normal CRUD semantics.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.base import Base
from app.db.session import SessionLocal
from app.models import AuditEvent, Company, User

CONFIRMATION = "PURGE PREPRODUCTION COMPANIES"


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Purga empresas prepiloto seleccionadas y sus dependencias.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--company", action="append", required=True, help="Nombre exacto; repetir por empresa.")
    parser.add_argument("--environment", required=True, choices=("local", "staging", "production"))
    parser.add_argument("--backup-confirmed", help="Referencia verificable del backup (obligatoria al ejecutar).")
    parser.add_argument("--confirm", help=f'Confirmación exacta: "{CONFIRMATION}"')
    return parser.parse_args()


def closure(db, company_ids: set[int]) -> dict[str, set[object]]:
    targets: dict[str, set[object]] = {"companies": set(company_ids)}
    changed = True
    while changed:
        changed = False
        for table in Base.metadata.sorted_tables:
            if len(table.primary_key.columns) != 1:
                continue
            pk = next(iter(table.primary_key.columns))
            for fk in table.foreign_keys:
                parent_ids = targets.get(fk.column.table.name)
                if not parent_ids:
                    continue
                found = set(db.scalars(select(pk).where(fk.parent.in_(parent_ids))).all())
                bucket = targets.setdefault(table.name, set())
                old = len(bucket)
                bucket.update(found)
                changed |= len(bucket) != old
    return {name: ids for name, ids in targets.items() if ids}


def main() -> None:
    args = arguments()
    with SessionLocal() as db:
        companies = db.scalars(select(Company).where(Company.name.in_(args.company))).all()
        found = {row.name for row in companies}
        missing = sorted(set(args.company) - found)
        if missing:
            raise SystemExit(f"No existen nombres exactos: {', '.join(missing)}. No se modificó nada.")
        targets = closure(db, {row.id for row in companies})
        protected_admins = set(db.scalars(select(User.id).where(User.role == "admin", User.deleted_at.is_(None))).all())
        targets.get("users", set()).difference_update(protected_admins)
        admin_before = db.scalar(select(func.count(User.id)).where(User.role == "admin", User.deleted_at.is_(None))) or 0
        print(f"Ambiente: {args.environment}")
        print("Empresas seleccionadas: " + ", ".join(sorted(found)))
        for name in sorted(targets):
            print(f"  {name}: {len(targets[name])}")
        print(f"  administradores protegidos: {admin_before}")
        if args.dry_run:
            print("DRY RUN: no se modificaron datos.")
            return
        if not args.backup_confirmed:
            raise SystemExit("Falta --backup-confirmed. No se modificó nada.")
        if args.confirm != CONFIRMATION:
            raise SystemExit("Confirmación fuerte inválida. No se modificó nada.")
        try:
            # Keep a system-scoped audit record; company-scoped records are part of the purge.
            db.add(AuditEvent(action="preproduction_purge", resource_type="company", resource_id=",".join(map(str, sorted(targets["companies"]))), summary="Purga controlada de datos preproducción", metadata_json=json.dumps({"environment": args.environment, "backup_reference": args.backup_confirmed, "companies": sorted(found), "at": datetime.now(timezone.utc).isoformat()})))
            # Break the deliberate Company.approved_by -> User -> Company cycle.
            for company in companies:
                company.approved_by_id = None
            for admin in db.scalars(select(User).where(User.id.in_(protected_admins))).all():
                if admin.company_id in targets["companies"]:
                    admin.company_id = None
            db.flush()
            for table in reversed(Base.metadata.sorted_tables):
                ids = targets.get(table.name)
                if not ids or len(table.primary_key.columns) != 1:
                    continue
                pk = next(iter(table.primary_key.columns))
                db.execute(table.delete().where(pk.in_(ids)))
            admins_after = db.scalar(select(func.count(User.id)).where(User.role == "admin", User.deleted_at.is_(None))) or 0
            if admins_after != admin_before or admins_after < 1:
                raise RuntimeError("La protección de administradores falló")
            remaining = db.scalar(select(func.count(Company.id)).where(Company.id.in_(targets["companies"]))) or 0
            if remaining:
                raise RuntimeError("Persisten empresas seleccionadas")
            db.commit()
        except Exception:
            db.rollback()
            raise
        print("PURGA COMPLETADA")
        print(f"Empresas seleccionadas restantes: {remaining}")
        print(f"Administradores antes/después: {admin_before}/{admins_after}")


if __name__ == "__main__":
    main()
