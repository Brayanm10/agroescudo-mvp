"""Regression evidence for the Internet exposure review, no remote services."""
import asyncio
from types import SimpleNamespace
import pytest
from sqlalchemy.exc import OperationalError
from test_partner_api import partner,headers,token,BASE
from app.core.config import settings,Settings


@pytest.mark.parametrize('case',['utf8','query','duplicate_auth'])
def test_strict_token_inputs(client,partner,case):
    h={'Content-Type':'application/x-www-form-urlencoded'}
    url=BASE+'/oauth/token';body=b'grant_type=client_credentials'
    if case=='utf8':body=b'grant_type=\xff'
    if case=='query':url+='?client_secret=DO_NOT_LOG_THIS'
    if case=='duplicate_auth':h=[('Content-Type','application/x-www-form-urlencoded'),('Authorization','Basic x'),('Authorization','Basic y')]
    r=client.post(url,content=body,headers=h)
    assert r.status_code==400,r.text
    assert 'DO_NOT_LOG_THIS' not in r.text


def test_audit_storage_failure_is_fail_closed(client,partner,monkeypatch):
    h=headers(client,partner)
    import app.api.routes.partner as route
    def broken(**kwargs):raise OperationalError('PRIVATE_SQL',{},Exception('PRIVATE_DATABASE_URL'))
    monkeypatch.setattr(route,'PartnerAudit',broken)
    r=client.get(BASE+'/storage-units',headers=h)
    assert r.status_code==503 and r.json()['error']['code']=='SERVICE_UNAVAILABLE'
    assert 'PRIVATE_' not in r.text and 'items' not in r.json()


def test_quota_storage_failure_is_fail_closed(client,partner,monkeypatch):
    import app.api.routes.partner as route
    def broken(*args,**kwargs):raise OperationalError('PRIVATE_SQL',{},Exception('PRIVATE_PASSWORD'))
    monkeypatch.setattr(route,'quota',broken)
    r=token(client,partner)
    assert r.status_code==503 and 'access_token' not in r.json() and 'PRIVATE_' not in r.text


def test_unexpected_dependency_failure_is_safe(client,partner,monkeypatch):
    h=headers(client,partner)
    import app.services.partner_data as data
    def broken(*args,**kwargs):raise RuntimeError('PRIVATE_PAYLOAD')
    monkeypatch.setattr(data,'context',broken)
    r=client.get(BASE+'/storage-units',headers=h)
    assert r.status_code==500 and 'PRIVATE_PAYLOAD' not in r.text


def test_token_body_deadline(client,partner,monkeypatch):
    import app.api.routes.partner as route
    async def timeout(coro,timeout):
        assert timeout==10
        coro.close()
        raise asyncio.TimeoutError()
    monkeypatch.setattr(route.asyncio,'wait_for',timeout)
    r=token(client,partner)
    assert r.status_code==408 and r.json()['error']=='invalid_request'


def config(**changes):
    d=dict(environment='staging',database_url='postgresql+psycopg://leady_staging_role:FAKE@ep-test.example.neon.tech/leady_staging?sslmode=verify-full',
        partner_staging_expected_host='ep-test.example.neon.tech',partner_staging_expected_database='leady_staging',partner_staging_expected_role='leady_staging_role')
    d.update(changes);return SimpleNamespace(**d)


@pytest.mark.parametrize('changes',[{'environment':'production'},{'database_url':'sqlite://'},{'partner_staging_expected_host':''},{'partner_staging_expected_host':'ep-other.example.neon.tech'},{'partner_staging_expected_database':'neondb'},{'database_url':'postgresql://leady_staging_role:FAKE@ep-test.example.neon.tech/leady_staging?sslmode=disable'}])
def test_staging_rejects_uncertain_destination_before_connection(changes):
    from app.services.partner_staging import destination
    with pytest.raises(ValueError):destination(config(**changes))


def test_destination_accepts_only_explicit_staging():
    from app.services.partner_staging import destination
    assert len(destination(config()))==64


@pytest.mark.parametrize('peer,headers_,expected',[('127.0.0.1',[(b'x-forwarded-proto',b'https')],'https'),('203.0.113.1',[(b'x-forwarded-proto',b'https')],'http'),('127.0.0.1',[(b'x-forwarded-proto',b'https'),(b'x-forwarded-proto',b'http')],'http')])
def test_forwarded_scheme_only_from_explicit_proxy(peer,headers_,expected):
    from app.partner_staging import TrustedStagingProxy
    result=[]
    async def app(scope,receive,send):result.append(scope['scheme'])
    async def receive():return {}
    async def send(x):pass
    proxy=TrustedStagingProxy(app,'127.0.0.0/8')
    asyncio.run(proxy({'type':'http','scheme':'http','client':(peer,123),'headers':headers_},receive,send))
    assert result==[expected]
    with pytest.raises(ValueError):TrustedStagingProxy(app,'0.0.0.0/0')


def test_staging_factory_excludes_original_login_and_iot(monkeypatch):
    import app.partner_staging as module
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    monkeypatch.setattr(module,'destination',lambda s:None)
    monkeypatch.setattr(module,'create_engine',lambda *a,**kw:create_engine('sqlite://'))
    monkeypatch.setattr(settings,'partner_staging_allowed_hosts','staging.example.test')
    app=module.create_app()
    with TestClient(app,base_url='http://staging.example.test') as client:
        assert client.get('/health').status_code==200
        assert client.post('/api/auth/login',json={}).status_code==404
        assert client.post('/api/readings',json={}).status_code==404
        assert client.get('/health',headers={'Host':'attacker.example.test'}).status_code==400
        assert client.get('/ready').status_code==503  # no marker/database service


def test_sql_bucket_never_moves_clock_backwards(db_session,partner,monkeypatch):
    from datetime import timedelta
    from app.services import partner_security as security
    from app.partner_models import PartnerBucket
    from sqlalchemy import select
    from app.services.partner_security import aware
    future=security.now()+timedelta(seconds=30)
    db_session.add(PartnerBucket(key='clock-test',balance=1,updated_at=future,version=0));db_session.commit()
    security.quota(db_session,'clock-test',60,10)
    row=db_session.scalar(select(PartnerBucket).where(PartnerBucket.key=='clock-test'))
    assert aware(row.updated_at)>=future and row.balance<1


@pytest.mark.parametrize('suffix',['','/{unit}/latest','/{unit}/readings','/{unit}/alerts'])
def test_other_client_cannot_spoof_existing_headers(client,db_session,partner,suffix):
    from app.services.partner_admin import create_client,SCOPES
    from test_partner_api import period
    other,secret=create_client(db_session,'other-service','Other service',sorted(SCOPES),'test');db_session.commit()
    response=client.post(BASE+'/oauth/token',auth=('other-service',secret),data={'grant_type':'client_credentials'})
    assert response.status_code==200,response.text
    h={'Authorization':'Bearer '+response.json()['access_token'],'X-LEADY-Organization-Id':'org_a','X-LEADY-Producer-Id':'producer_a'}
    r=client.get(BASE+'/storage-units'+suffix.format(unit=partner['unit']),headers=h,params=period() if suffix.endswith('readings') else {})
    assert r.status_code==403,r.text
