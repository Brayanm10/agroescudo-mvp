"""Read-only partner surface; internal administration is CLI-only."""
import logging
import asyncio
import time
from uuid import uuid4
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Form, Header, Path, Query, Request, Response, Security
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.security.http import HTTPBase
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.db.session import get_db
from app.partner_models import PartnerAudit
from app.partner_schemas import PartnerAlertsOut, PartnerErrorOut, PartnerLatestOut, PartnerReadingsOut, PartnerTokenOut, PartnerUnitsOut, OAuthErrorOut, MetricCode
from app.services import partner_data as data
from app.services.partner_security import PartnerError, authenticate_client, db_dependency, digest, issue_token, now, principal, quota

log = logging.getLogger('agroescudo.partner')
basic = HTTPBase(scheme='basic',scheme_name='PartnerBasic',auto_error=False)


class PartnerRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handle(request):
            started = time.monotonic()
            request_id = uuid4().hex
            token_route = self.path.endswith('/oauth/token')
            db_generator = None
            async def read_token_body():
                chunks = []
                size = 0
                async for chunk in request.stream():
                    size += len(chunk)
                    if size > 4096:
                        raise PartnerError(400, 'invalid_request', 'Solicitud demasiado grande.')
                    chunks.append(chunk)
                return b''.join(chunks)
            def error(status, code, message='Solicitud no disponible.', headers=None):
                content = {'error': code, 'error_description': message} if token_route else {'error': {'code': code, 'message': message, 'request_id': request_id}}
                return JSONResponse(content, status_code=status, headers=headers)
            try:
                if not settings.partner_api_enabled:
                    raise PartnerError(404, 'RESOURCE_NOT_FOUND')
                if settings.environment != 'local' and request.url.scheme != 'https':
                    raise PartnerError(400, 'HTTPS_REQUIRED', 'HTTPS es obligatorio.')
                # Open the same get_db provider (including isolated test overrides)
                # before validation, so malformed requests are audited and token
                # abuse quotas also cover missing/duplicate/oversized parameters.
                if len(request.url.query)>4096 or len(request.headers.get('authorization',''))>2048:
                    raise PartnerError(400, 'INVALID_REQUEST')
                if len(request.headers.getlist('authorization')) > 1:
                    raise PartnerError(400, 'INVALID_REQUEST')
                provider = request.app.dependency_overrides.get(get_db, get_db)
                db_generator = provider()
                request.state.partner_db = next(db_generator)
                if token_route:
                    peer = request.client.host if request.client else 'unknown'
                    await run_in_threadpool(quota, request.state.partner_db, 'auth-peer:'+digest(peer), settings.partner_auth_per_minute, settings.partner_auth_burst)
                if token_route:
                    if request.url.query:
                        raise PartnerError(400, 'invalid_request', 'No enviar credenciales o parámetros en la URL.')
                    if request.headers.get('content-type','').split(';')[0] != 'application/x-www-form-urlencoded':
                        raise PartnerError(400, 'invalid_request', 'Usar application/x-www-form-urlencoded.')
                    request._body = await asyncio.wait_for(read_token_body(), timeout=10)
                    from urllib.parse import parse_qs
                    body=parse_qs(request._body.decode('utf-8'),keep_blank_values=True)
                    if set(body)-{'grant_type','scope'} or any(len(v)!=1 for v in body.values()):
                        raise PartnerError(400,'invalid_request','Parámetros no admitidos o repetidos.')
                else:
                    allowed={'limit','cursor'} if self.path.endswith('storage-units') else set()
                    if self.path.endswith('/readings'):allowed|={'from','to','device_id','metric_code','channel_key','limit','cursor'}
                    if self.path.endswith('/alerts'):allowed|={'from','to','device_id','status','severity','limit','cursor'}
                    if set(request.query_params)-allowed or any(len(request.query_params.getlist(k))!=1 for k in request.query_params):
                        raise PartnerError(400,'INVALID_REQUEST','Filtros no admitidos o repetidos.')
                response = await original(request)
                if not token_route and len(response.body)>settings.partner_max_response_bytes:
                    response=error(400,'RESPONSE_TOO_LARGE','Reducir limit o acotar concesiones.')
            except PartnerError as exc:
                code=exc.code
                if token_route and code.isupper():
                    code='temporarily_unavailable' if exc.status in (429,503) else 'invalid_request'
                response=error(exc.status,code,exc.message,exc.headers)
            except RequestValidationError:
                response=error(400 if token_route else 422,'invalid_request' if token_route else 'VALIDATION_ERROR','Parámetros inválidos o incompletos.')
            except (UnicodeError, ValueError):
                response=error(400,'invalid_request' if token_route else 'INVALID_REQUEST')
            except asyncio.TimeoutError:
                response=error(408,'invalid_request' if token_route else 'REQUEST_TIMEOUT')
            except (SQLAlchemyError, OSError):
                response=error(503,'temporarily_unavailable' if token_route else 'SERVICE_UNAVAILABLE')
            except Exception:
                response=error(500,'server_error' if token_route else 'INTERNAL_ERROR')
            elapsed=(time.monotonic()-started)*1000
            db=getattr(request.state,'partner_db',None)
            if db is not None:
                def store_audit():
                    try:
                        db.rollback()
                        db.add(PartnerAudit(request_id=request_id,client_id=getattr(request.state,'partner_client',None),
                            action=request.method+' '+self.path,resource=(request.path_params.get('storage_unit_id') or '')[:128],
                            status_code=response.status_code,occurred_at=now(),latency_ms=elapsed))
                        db.commit()
                    finally:
                        db.close()
                try:
                    await run_in_threadpool(store_audit)
                except Exception:
                    response=error(503,'temporarily_unavailable' if token_route else 'SERVICE_UNAVAILABLE')
            log.info('partner_request request_id=%s status=%s latency_ms=%.2f', request_id,response.status_code,elapsed)
            if db_generator is not None:
                db_generator.close()
            response.headers['X-Request-Id']=request_id
            response.headers['Cache-Control']='no-store'
            if token_route:response.headers['Pragma']='no-cache'
            return response
        return handle


ERRORS={code:{'model':PartnerErrorOut,'description':description} for code,description in {
    400:'Solicitud, intervalo o cursor inválido',401:'Token inválido o vencido',403:'Scope/contexto no autorizado',
    404:'Recurso inexistente o no concedido',422:'Validación de parámetros',429:'Cuota excedida; Retry-After en segundos',
    500:'Error interno seguro',503:'Servicio no disponible'}.items()}
router=APIRouter(prefix='/v1/partner',tags=['partner'],route_class=PartnerRoute)


@router.post('/oauth/token',response_model=PartnerTokenOut,responses={400:{'model':OAuthErrorOut},401:{'model':OAuthErrorOut},404:{'model':OAuthErrorOut},408:{'model':OAuthErrorOut},429:{'model':OAuthErrorOut},500:{'model':OAuthErrorOut},503:{'model':OAuthErrorOut},'4XX':{'model':OAuthErrorOut}})
def token(request: Request, response: Response, grant_type: str=Form(...), scope: str | None=Form(default=None), authorization: str | None=Header(default=None), db: Session=Depends(db_dependency), _basic=Security(basic)):
    client,credential=authenticate_client(request,db,authorization)
    if grant_type!='client_credentials':
        raise PartnerError(400,'unsupported_grant_type','Solo client_credentials está admitido.')
    return issue_token(db,client,credential,scope)


def context_dependency(scope):
    def dependency(request: Request,actor=Security(principal,scopes=[scope]),db: Session=Depends(db_dependency),
                   org: str=Header(...,alias='X-LEADY-Organization-Id',min_length=1,max_length=128),
                   producer: str=Header(...,alias='X-LEADY-Producer-Id',min_length=1,max_length=128)):
        for name in ['X-LEADY-Organization-Id','X-LEADY-Producer-Id']:
            if len(request.headers.getlist(name))!=1:raise PartnerError(400,'INVALID_REQUEST')
        return data.context(db,actor,org,producer,scope)
    return dependency


@router.get('/storage-units',response_model=PartnerUnitsOut,responses=ERRORS)
def units(limit: int=Query(100,ge=1,le=500),cursor: str | None=Query(None,max_length=2048),ctx=Depends(context_dependency('storage_units:read'))):
    return data.catalogue(ctx,limit,cursor)


@router.get('/storage-units/{storage_unit_id}/latest',response_model=PartnerLatestOut,responses=ERRORS)
def latest(storage_unit_id: str=Path(...,min_length=1,max_length=128),ctx=Depends(context_dependency('readings:read'))):
    return data.observations(ctx,storage_unit_id,latest=True)


@router.get('/storage-units/{storage_unit_id}/readings',response_model=PartnerReadingsOut,responses=ERRORS)
def readings(storage_unit_id: str=Path(...,min_length=1,max_length=128),from_: datetime=Query(...,alias='from'),to: datetime=Query(...),
             device_id: str | None=Query(None,max_length=128),channel_key: str | None=Query(None,max_length=80),metric_code: MetricCode | None=None,
             limit: int=Query(100,ge=1,le=500),cursor: str | None=Query(None,max_length=2048),ctx=Depends(context_dependency('readings:read'))):
    data.window(from_,to)
    return data.observations(ctx,storage_unit_id,from_=from_,to=to,device_id=device_id,metric_code=metric_code,channel_key=channel_key,limit=limit,cursor=cursor)


@router.get('/storage-units/{storage_unit_id}/alerts',response_model=PartnerAlertsOut,responses=ERRORS)
def alerts(storage_unit_id: str=Path(...,min_length=1,max_length=128),from_: datetime | None=Query(None,alias='from'),to: datetime | None=None,
           device_id: str | None=Query(None,max_length=128),status: Literal['active','acknowledged','resolved'] | None=None,
           severity: Literal['warning','critical','technical','unknown'] | None=None,limit: int=Query(100,ge=1,le=500),
           cursor: str | None=Query(None,max_length=2048),ctx=Depends(context_dependency('alerts:read'))):
    data.window(from_,to,required=False)
    return data.alerts(ctx,storage_unit_id,from_,to,device_id,status,severity,limit,cursor)
