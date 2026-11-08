"""Dedicated ASGI factory: partner-only staging, no human/IoT/admin routers."""
import ipaddress
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.core.config import settings
from app.db.session import get_db
from app.api.routes.partner import router
from app.services.partner_staging import check_connection,destination,engine_options


class TrustedStagingProxy:
    def __init__(self,app,cidrs):
        self.app=app
        self.networks=[ipaddress.ip_network(c.strip()) for c in cidrs.split(',') if c.strip()]
        if any(n.prefixlen==0 for n in self.networks):raise ValueError('No confiar en todas las redes de proxy.')

    async def __call__(self,scope,receive,send):
        if scope['type']=='http':
            headers=[(k.lower(),v) for k,v in scope.get('headers',[])]
            peer=(scope.get('client') or ('',0))[0]
            try:trusted=any(ipaddress.ip_address(peer) in n for n in self.networks)
            except ValueError:trusted=False
            proto=[v for k,v in headers if k==b'x-forwarded-proto']
            if trusted and proto==[b'https']:
                scope=dict(scope,scheme='https')
            elif proto==[b'https']:
                # Actual socket peer only, no credentials or forwarded client IP.
                # Allows an operator to establish the platform proxy allowlist.
                logging.getLogger('agroescudo.partner.proxy').warning('untrusted_proxy_peer=%s',peer)
            # No X-Forwarded-For override. Peer quotas remain conservative behind
            # NAT/proxy; tune only after observing the actual trusted topology.
        await self.app(scope,receive,send)


def create_app():
    destination(settings)  # No connection until the explicit target passes.
    hosts=[h.strip() for h in settings.partner_staging_allowed_hosts.split(',') if h.strip()]
    if not hosts or any('*' in h or '/' in h for h in hosts):raise ValueError('Configurar hosts exactos del servicio staging.')
    engine=create_engine(settings.database_url,**engine_options())
    factory=sessionmaker(bind=engine,expire_on_commit=False)
    app=FastAPI(title='AgroEscudo LEADY Staging',version='1.1.0',docs_url='/docs',redoc_url=None)
    def isolated_db():
        with factory() as db:yield db
    app.dependency_overrides[get_db]=isolated_db
    app.include_router(router,prefix='/api')
    app.add_middleware(TrustedStagingProxy,cidrs=settings.partner_staging_proxy_cidrs)
    app.add_middleware(TrustedHostMiddleware,allowed_hosts=hosts)

    @app.get('/health',include_in_schema=False)
    def health():return {'status':'ok','environment':'staging','version':'1.1.0'}

    @app.get('/ready',include_in_schema=False)
    def ready():
        try:
            with engine.connect() as conn:check_connection(conn,settings)
            if not settings.partner_api_enabled:raise ValueError('disabled')
            return {'status':'ready','environment':'staging'}
        except Exception:return JSONResponse({'status':'unavailable'},status_code=503)
    return app
