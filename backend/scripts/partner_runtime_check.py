"""Isolated HTTP regression on the minimal staging dependency stack (no network)."""
import os
import secrets
from datetime import datetime,timedelta,timezone


def main():
    os.environ.update(ENVIRONMENT='local',DATABASE_URL='sqlite://',PARTNER_SANDBOX='true',PARTNER_API_ENABLED='true',JWT_SECRET=secrets.token_urlsafe(48),PARTNER_SIGNING_KEY=secrets.token_urlsafe(48))
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from sqlalchemy.pool import StaticPool
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.models import Base
    from app.api.routes.partner import router
    from app.db.session import get_db
    from app.services.partner_sandbox import seed
    from app.partner_schemas import PartnerLatestOut,PartnerUnitsOut,PartnerReadingsOut,PartnerAlertsOut
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine,expire_on_commit=False) as db:
        config=seed(db)
        app=FastAPI();app.include_router(router,prefix='/api')
        def isolated():yield db
        app.dependency_overrides[get_db]=isolated
        with TestClient(app) as client:
            r=client.post('/api/v1/partner/oauth/token',auth=(config['client_id'],config['client_secret']),data={'grant_type':'client_credentials'});assert r.status_code==200,r.status_code
            h={'Authorization':'Bearer '+r.json()['access_token'],'X-LEADY-Organization-Id':config['organization_id'],'X-LEADY-Producer-Id':'prod_demo_a'}
            r=client.get('/api/v1/partner/storage-units',headers=h);assert r.status_code==200,r.status_code;PartnerUnitsOut.model_validate(r.json())
            units=r.json()['items']
            unit=units[0]['id'];prefix='/api/v1/partner/storage-units/'+unit
            for suffix,model in [('latest',PartnerLatestOut),('readings',PartnerReadingsOut),('alerts',PartnerAlertsOut)]:
                params={'from':(datetime.now(timezone.utc)-timedelta(days=2)).isoformat(),'to':datetime.now(timezone.utc).isoformat(),'limit':2} if suffix=='readings' else {}
                r=client.get(prefix+'/'+suffix,headers=h,params=params);assert r.status_code==200,r.status_code;model.model_validate(r.json())
            h['X-LEADY-Producer-Id']='not-linked'
            assert client.get(prefix+'/latest',headers=h).status_code==403
            # Export this stack's real five operations; no deployment is claimed.
            import json
            from pathlib import Path
            schema=app.openapi()
            schema['info']={'title':'AgroEscudo LEADY staging preparado NO DESPLEGADO','version':'1.1.0'}
            Path('../tmp/leady-hardening/openapi-staging-preparado.json').write_text(json.dumps(schema,ensure_ascii=False,indent=2),encoding='utf-8')
    engine.dispose()
    print('PASS: runtime mínimo, token, cuatro GET, schemas reales y contexto no vinculado. PostgreSQL/Internet NO probados.')


if __name__=='__main__':main()
