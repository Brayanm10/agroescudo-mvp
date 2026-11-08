"""Isolated local sandbox. Run from backend: python -m scripts.partner_sandbox init|serve|smoke."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'.sandbox/leady'


def configure():
    runtime=json.loads((DIRECTORY/'runtime.json').read_text(encoding='utf-8'))
    # Always override inherited DATABASE_URL; never run sandbox on production.
    os.environ.update(DATABASE_URL='sqlite:///'+(DIRECTORY/'sandbox.db').as_posix(),ENVIRONMENT='local',
        PARTNER_SANDBOX='true',PARTNER_API_ENABLED='true',JWT_SECRET=runtime['jwt_secret'],PARTNER_SIGNING_KEY=runtime['partner_signing_key'],
        NOTIFICATIONS_DRY_RUN='true',EMAIL_ENABLED='false',WHATSAPP_ENABLED='false',TELEGRAM_ENABLED='false',FCM_ENABLED='false',AI_ENABLED='false',AGRO_ASSISTANT_LLM_ENABLED='false')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('command',choices=['init','serve','smoke','admin']);p.add_argument('args',nargs=argparse.REMAINDER);a=p.parse_args()
    if a.command=='init':
        DIRECTORY.mkdir(parents=True,exist_ok=True)
        if (DIRECTORY/'sandbox.db').exists() or (DIRECTORY/'runtime.json').exists():
            p.exit(1,'Sandbox ya inicializado o incompleto. No se borra ni sobrescribe. Use serve; para reinstalar, conserve/renombre el directorio explícitamente.\n')
        runtime={'jwt_secret':secrets.token_urlsafe(48),'partner_signing_key':secrets.token_urlsafe(48)}
        (DIRECTORY/'runtime.json').write_text(json.dumps(runtime),encoding='utf-8')
        if os.name!='nt':(DIRECTORY/'runtime.json').chmod(0o600)
        configure()
        subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT/'backend',check=True)
        from app.db.session import SessionLocal
        from app.services.partner_sandbox import seed
        with SessionLocal() as db:credentials=seed(db)
        (DIRECTORY/'credentials.json').write_text(json.dumps(credentials,ensure_ascii=False,indent=2),encoding='utf-8')
        if os.name!='nt':(DIRECTORY/'credentials.json').chmod(0o600)
        print('Sandbox inicializado. Credenciales locales en .sandbox/leady/credentials.json (no versionar ni compartir por chat).')
    else:
        if not (DIRECTORY/'credentials.json').exists():p.exit(1,'Primero ejecutar init.\n')
        configure()
        if a.command=='serve':
            import uvicorn
            uvicorn.run('app.main:app',host='127.0.0.1',port=8020,access_log=False,proxy_headers=False)
        elif a.command=='smoke':
            from scripts.partner_smoke import run
            run(json.loads((DIRECTORY/'credentials.json').read_text(encoding='utf-8')))
        elif a.command=='admin':
            # Preserve exactly the isolated DB and runtime keys for local operations.
            subprocess.run([sys.executable,'-m','scripts.partner_admin',*a.args],cwd=ROOT/'backend',check=True,env=os.environ.copy())


if __name__=='__main__':main()
