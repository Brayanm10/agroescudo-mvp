"""Console-only staging workflow: bootstrap, verify, seed or serve.

Requires explicit ENVIRONMENT, approved Neon host/database/role and TLS. No
fallback to a local/production DB; no general app seed; no credentials in logs.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import certifi


def main():
    # libpq/OpenSSL must use the same maintained CA bundle on Windows and Render.
    # Keep verify-full enabled; never fall back to an unverified TLS connection.
    os.environ.setdefault('SSL_CERT_FILE',certifi.where())
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['bootstrap','verify','seed','serve'])
    p.add_argument('--credentials-output',help='Solo seed: archivo privado fuera del repositorio para entrega segura')
    a=p.parse_args()
    try:
        from app.core.config import settings
        from app.services.partner_staging import check_connection,destination,engine_options
        destination(settings)
        from sqlalchemy import create_engine
        engine=create_engine(settings.database_url,**engine_options())
        with engine.begin() as conn:check_connection(conn,settings,initialize=a.command=='bootstrap')
        if a.command=='bootstrap':
            # Both the target and physical identity have passed before Alembic.
            subprocess.run([sys.executable,'-m','alembic','upgrade','head'],check=True,capture_output=True)
            print('PASS: destino staging verificado y migraciones aplicadas.')
        elif a.command=='seed':
            if not a.credentials_output:raise ValueError('Se requiere un destino privado de credenciales.')
            output=Path(a.credentials_output).resolve()
            repo=Path(__file__).resolve().parents[2]
            if output==repo or repo in output.parents or output.exists():raise ValueError('No guardar secretos en el repositorio ni sobrescribir archivos.')
            from sqlalchemy.orm import Session
            from app.services.partner_sandbox import seed_staging
            # Create exclusively and with restrictive mode before creating a client.
            fd=os.open(output,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            with os.fdopen(fd,'w',encoding='utf-8') as handle:
                with Session(engine,expire_on_commit=False) as db:data=seed_staging(db)
                data['base_url']='https://'+settings.partner_staging_allowed_hosts.split(',')[0]
                data['environment']='staging'
                data['service_label']='AgroEscudo LEADY Staging'
                json.dump(data,handle,ensure_ascii=False,indent=2)
            print('PASS: datos ficticios cargados; credenciales en el archivo privado solicitado, nunca en stdout.')
        elif a.command=='serve':
            import uvicorn
            uvicorn.run('app.partner_staging:create_app',factory=True,host='0.0.0.0',port=int(os.getenv('PORT','8000')),proxy_headers=False,access_log=False,limit_concurrency=20,timeout_keep_alive=5)
        else:print('PASS: destino e identidad de staging verificados; no se modificó la base.')
        engine.dispose()
    except Exception as exc:
        p.exit(1,'BLOQUEADO ('+type(exc).__name__+'): comprobar destino aprobado, identidad, TLS y conectividad en la consola segura. No se imprimen cadenas, credenciales ni errores SQL.\n')


if __name__=='__main__':main()
