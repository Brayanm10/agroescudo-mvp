"""Scoped production operator command. Inspection by default; secrets never stdout."""
from __future__ import annotations
import argparse
from datetime import datetime
import getpass
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import select
from app.db.session import SessionLocal
from app.models import IotGatewayCredential
from app.core.security import decrypt_secret
from app.services.agua_suelo_demo import inspect_account, prepare_demo, seed_history


def check_migrations(db):
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "alembic"))
    expected = set(ScriptDirectory.from_config(config).get_heads())
    actual = set(MigrationContext.configure(db.connection()).get_current_heads())
    if actual != expected:
        raise ValueError("Migraciones pendientes o divergentes; no se modifica la base")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--email", default="sueloyagua@gmail.com")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--company-id", type=int)
    parser.add_argument("--actor-id", type=int)
    parser.add_argument("--latitude", type=float)
    parser.add_argument("--longitude", type=float)
    parser.add_argument("--location-reference")
    parser.add_argument("--physical-id", default="DEMO-AGUA-SUELO-P01")
    parser.add_argument("--gateway-id", default="DEMO-AGUA-SUELO-GW01")
    parser.add_argument("--node-id", type=int)
    parser.add_argument("--backup-file", type=Path, help="pg_dump recuperable, fuera de Git")
    parser.add_argument("--backup-sha256", help="Checksum del respaldo verificado")
    parser.add_argument("--secret-output", type=Path, help="Archivo local ignorado; exclusivo, nunca sobrescrito")
    parser.add_argument("--history-start", help="UTC ISO8601 fijo, por ejemplo YYYY-MM-DDT00:00:00+00:00")
    parser.add_argument("--history-days", type=int, default=7)
    args = parser.parse_args()
    with SessionLocal() as db:
        report = inspect_account(db, args.email)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if not args.execute:
            print("READ_ONLY: sin cambios; se requiere --execute para aprovisionar")
            return
        if any(value is None for value in (args.company_id, args.actor_id, args.latitude, args.longitude,
                                            args.location_reference, args.node_id, args.backup_file,
                                            args.backup_sha256, args.secret_output)):
            raise ValueError("Empresa/administrador/coordenadas/node_id/respaldo/checksum/salida segura requeridos")
        if not args.backup_file.is_file() or args.backup_file.stat().st_size < 100:
            raise ValueError("Respaldo recuperable requerido antes de modificar producción")
        with args.backup_file.open("rb") as backup:
            digest = hashlib.file_digest(backup, "sha256").hexdigest()
        if digest.lower() != args.backup_sha256.lower():
            raise ValueError("Checksum del respaldo no coincide")
        check_migrations(db)
        output = args.secret_output.resolve()
        repo = ROOT.parent
        # Require ignored output inside this repo; refuse writing secrets into tracked paths.
        if not output.is_relative_to(repo) or output.exists():
            raise ValueError("Salida debe ser nueva, local, ignorada por Git y dentro del repositorio")
        ignored = subprocess.run(["git", "check-ignore", "--quiet", str(output)], cwd=repo, check=False)
        if ignored.returncode:
            raise ValueError("Salida no ignorada por Git")
        output.parent.mkdir(parents=True, exist_ok=True)
        device, gateway, new_secret = prepare_demo(db, email=args.email, company_id=args.company_id,
            actor_id=args.actor_id, latitude=args.latitude, longitude=args.longitude,
            location_reference=args.location_reference, physical_id=args.physical_id,
            gateway_id=args.gateway_id, node_id=args.node_id)
        credential = db.scalar(select(IotGatewayCredential).where(IotGatewayCredential.gateway_id == gateway.id,
            IotGatewayCredential.is_active.is_(True)).order_by(IotGatewayCredential.key_version.desc()))
        if not credential:
            raise ValueError("Credencial DEMO ausente")
        secret = new_secret or decrypt_secret(credential.encrypted_secret)
        # Save before commit. No credentials are emitted to logs or command arguments.
        descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        if os.name == "nt":
            principal = os.environ.get("USERDOMAIN", "") + "\\" + getpass.getuser()
            permissions = subprocess.run(["icacls", str(output), "/inheritance:r", "/grant:r", principal + ":(F)"],
                                         capture_output=True, check=False)
            if permissions.returncode:
                os.close(descriptor)
                output.unlink()
                raise ValueError("No se pudo restringir ACL del archivo; no se guardaron secretos ni se confirma DB")
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write('#pragma once\n#define WIFI_SSID "REPLACE_LOCAL_WIFI"\n#define WIFI_PASSWORD "REPLACE_LOCAL_WIFI_PASSWORD"\n')
            handle.write('#define AGRO_BASE_URL "https://agroescudo-api.onrender.com"\n')
            handle.write(f'#define AGRO_DEVICE_ID "{device.external_id}"\n#define AGRO_GATEWAY_ID "{gateway.gateway_id}"\n#define AGRO_GATEWAY_SECRET "{secret}"\n')
        try:
            db.commit()
        except Exception:
            # Only remove the new file this command created; no existing file can be overwritten.
            output.unlink()
            raise
        print(json.dumps({"device_db_id": device.id, "physical_id": device.external_id, "company_id": device.company_id,
            "site_id": device.site_id, "parcel_id": device.storage_unit_id, "credential_saved": True,
            "device_url": f"https://agroescudobo.vercel.app/pluviometria/pluviometros/{device.id}"}, ensure_ascii=False))
        if args.history_start:
            start = datetime.fromisoformat(args.history_start.replace("Z", "+00:00"))
            print(json.dumps(seed_history(db, device=device, gateway=gateway, secret=secret,
                start=start, days=args.history_days)))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Database exceptions may contain connection strings or encrypted secrets: don't print them.
        print("BLOCKED: " + (str(exc) if isinstance(exc, ValueError) else type(exc).__name__), file=sys.stderr)
        sys.exit(1)
