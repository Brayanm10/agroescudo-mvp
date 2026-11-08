"""Integration tests against the same routes, SQL grants and schemas as sandbox."""
import json
import logging
from datetime import timedelta
import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.models import Alert, Company, Device, DeviceChannel, MetricDefinition, MetricReading, SensorReading, Site, StorageUnit, TelemetryEvent
from app.partner_models import PartnerAudit, PartnerClient, PartnerCredential, PartnerGrant, PartnerOrganization, PartnerProducer, PartnerToken
from app.services import partner_admin as admin
from app.services.device_capabilities import ensure_metric_registry, sync_device_channels
from app.services.partner_security import digest, now, public_id, quota, PartnerError

BASE='/api/v1/partner'


@pytest.fixture
def partner(db_session,monkeypatch):
    for k,v in {'partner_api_enabled':True,'partner_sandbox':True,'partner_burst':1000,'partner_requests_per_minute':6000,'partner_auth_burst':100,'partner_auth_per_minute':1000}.items():monkeypatch.setattr(settings,k,v)
    db=db_session
    cl,secret=admin.create_client(db,'test-partner','Fictional partner',sorted(admin.SCOPES),'test')
    org=admin.link_org(db,cl,'org_a',1,'test');pa=admin.link_producer(db,org,'producer_a','test');pb=admin.link_producer(db,org,'producer_b','test')
    ensure_metric_registry(db)
    d1=db.get(Device,1);d1.expected_reading_interval_minutes=10;d1.last_seen_at=now()
    sync_device_channels(db,d1)
    d2=Device(company_id=1,site_id=1,storage_unit_id=1,external_id='PARTNER-DEMO-2',name='Shared restricted',token_hash='unused',expected_reading_interval_minutes=10,last_seen_at=now()-timedelta(hours=5))
    db.add(d2);db.flush();sync_device_channels(db,d2)
    u2=StorageUnit(company_id=1,site_id=1,name='Private B',unit_type='silo');db.add(u2);db.flush()
    company=Company(name='Other fictional company');db.add(company);db.flush()
    site=Site(company_id=company.id,name='Other site');db.add(site);db.flush()
    foreign=StorageUnit(company_id=company.id,site_id=site.id,name='Foreign',unit_type='silo');db.add(foreign);db.flush()
    org2=admin.link_org(db,cl,'org_other',company.id,'test');admin.link_producer(db,org2,'producer_other','test')
    ga=admin.grant(db,pa,1,'test',d1.id);admin.grant(db,pb,1,'test',d2.id);admin.grant(db,pb,u2.id,'test')
    stamp=now()-timedelta(minutes=2)
    for d,value in [(d1,23.0),(d2,81.0)]:
        db.add(SensorReading(company_id=1,site_id=1,storage_unit_id=1,device_id=d.id,ambient_temperature=value,ambient_humidity=55,timestamp=stamp,received_at=stamp))
        db.add(Alert(company_id=1,site_id=1,storage_unit_id=1,device_id=d.id,alert_type='humidity',metric='ambient_humidity',severity='warning',title='Internal title',message='DO_NOT_EXPOSE_INTERNAL_NOTE',is_active=True,observed_value=75,threshold_value=70,created_at=stamp))
    db.commit()
    return {'secret':secret,'client':cl.id,'grant':ga.id,'pa':pa.id,'pb':pb.id,'org':org.id,'unit':public_id('su',1),'private':public_id('su',u2.id),'foreign':public_id('su',foreign.id),'device':public_id('dev',1),'other_device':public_id('dev',d2.id),'d2':d2.id,'stamp':stamp}


def token(client,p,scope=None):
    body={'grant_type':'client_credentials'}
    if scope is not None:body['scope']=scope
    return client.post(BASE+'/oauth/token',auth=('test-partner',p['secret']),data=body)


def headers(client,p,producer='producer_a',scope=None):
    r=token(client,p,scope);assert r.status_code==200,r.text
    return {'Authorization':'Bearer '+r.json()['access_token'],'X-LEADY-Organization-Id':'org_a','X-LEADY-Producer-Id':producer}


def period():
    return {'from':(now()-timedelta(days=1)).isoformat(),'to':(now()+timedelta(days=1)).isoformat()}


def test_oauth_hashes_and_cache_headers(client,db_session,partner):
    r=token(client,partner);assert r.status_code==200,r.text
    assert r.json()['expires_in']==600 and 'refresh_token' not in r.json()
    assert r.headers['cache-control']=='no-store'
    stored=db_session.scalar(select(PartnerToken));assert stored.token_hash==digest(r.json()['access_token'])
    cred=db_session.scalar(select(PartnerCredential));assert partner['secret'] not in cred.secret_hash
    assert cred.secret_hash.startswith('scrypt$')


@pytest.mark.parametrize('case,expected',[('bad_secret',401),('unknown_client',401),('unsupported',400),('bad_scope',400),('empty_scope',400),('no_auth',401),('json',400),('duplicate',400)])
def test_oauth_errors(client,partner,case,expected):
    auth=('test-partner',partner['secret']);data={'grant_type':'client_credentials'}
    if case=='bad_secret':auth=('test-partner','wrong')
    if case=='unknown_client':auth=('unknown','wrong')
    if case=='unsupported':data['grant_type']='password'
    if case=='bad_scope':data['scope']='admin'
    if case=='empty_scope':data['scope']=''
    if case=='no_auth':auth=None
    if case=='json':r=client.post(BASE+'/oauth/token',auth=auth,json=data)
    elif case=='duplicate':r=client.post(BASE+'/oauth/token',auth=auth,content='grant_type=client_credentials&grant_type=password',headers={'Content-Type':'application/x-www-form-urlencoded'})
    else:r=client.post(BASE+'/oauth/token',auth=auth,data=data)
    assert r.status_code==expected,r.text
    assert isinstance(r.json()['error'],str)


@pytest.mark.parametrize('kind',['expired','token','credential','client','scope'])
def test_revocation_and_expiration(client,db_session,partner,kind):
    h=headers(client,partner);db=db_session
    t=db.scalar(select(PartnerToken))
    if kind=='expired':t.expires_at=now()-timedelta(seconds=1)
    elif kind=='token':t.revoked_at=now()
    elif kind=='credential':db.get(PartnerCredential,t.credential_id).revoked_at=now()
    elif kind=='client':db.get(PartnerClient,partner['client']).is_active=False
    elif kind=='scope':db.get(PartnerClient,partner['client']).scopes='readings:read'
    db.commit()
    r=client.get(BASE+'/storage-units',headers=h)
    assert r.status_code==(403 if kind=='scope' else 401),r.text


@pytest.mark.parametrize('route,scope',[('/storage-units','readings:read'),('/storage-units/{unit}/latest','alerts:read'),('/storage-units/{unit}/readings','alerts:read'),('/storage-units/{unit}/alerts','readings:read')])
def test_each_scope_enforced(client,partner,route,scope):
    r=client.get(BASE+route.format(unit=partner['unit']),headers=headers(client,partner,scope=scope),params=period() if route.endswith('readings') else {})
    assert r.status_code==403,r.text


def test_catalogue_shared_unit_devices_are_different(client,partner):
    a=client.get(BASE+'/storage-units',headers=headers(client,partner)).json()
    b=client.get(BASE+'/storage-units',headers=headers(client,partner,'producer_b')).json()
    assert len(a['items'])==1 and len(b['items'])==2
    assert a['items'][0]['devices'][0]['id']==partner['device']
    assert all(d['id']!=partner['device'] for u in b['items'] for d in u['devices'])


@pytest.mark.parametrize('bad',['organization','producer','missing_headers','missing_token','foreign','private'])
def test_context_and_cross_unit_isolation(client,partner,bad):
    h=headers(client,partner);path=BASE+'/storage-units'
    if bad=='organization':h['X-LEADY-Organization-Id']='unlinked'
    if bad=='producer':h['X-LEADY-Producer-Id']='unlinked'
    if bad=='missing_headers':del h['X-LEADY-Producer-Id']
    if bad=='missing_token':del h['Authorization']
    if bad in ['foreign','private']:path+='/'+partner[bad]+'/latest'
    r=client.get(path,headers=h)
    assert r.status_code=={'organization':403,'producer':403,'missing_headers':422,'missing_token':401,'foreign':404,'private':404}[bad],r.text
    assert set(r.json()['error'])=={'code','message','request_id'}


def test_latest_history_and_alerts_are_isolated(client,partner):
    h=headers(client,partner)
    for suffix in ['latest','readings','alerts']:
        r=client.get(BASE+'/storage-units/'+partner['unit']+'/'+suffix,headers=h,params=period() if suffix=='readings' else {})
        assert r.status_code==200,r.text
        assert r.json()['items']
        assert all(x['device_id']==partner['device'] for x in r.json()['items'])
        assert 'DO_NOT_EXPOSE_INTERNAL_NOTE' not in r.text
    r=client.get(BASE+'/storage-units/'+partner['unit']+'/readings',headers=h,params={**period(),'device_id':partner['other_device']})
    assert r.status_code==404


def test_channel_grant_isolation_and_revoke(client,db_session,partner):
    db=db_session;g=db.get(PartnerGrant,partner['grant']);g.channel_key='ambient_temp_1';db.commit()
    h=headers(client,partner)
    for suffix in ['latest','readings','alerts']:
        r=client.get(BASE+'/storage-units/'+partner['unit']+'/'+suffix,headers=h,params=period() if suffix=='readings' else {})
        assert r.status_code==200,r.text
        assert all(x.get('metric_code')=='AMBIENT_TEMPERATURE_C' for x in r.json()['items'])
    db.get(PartnerGrant,partner['grant']).revoked_at=now();db.commit()
    assert client.get(BASE+'/storage-units/'+partner['unit']+'/latest',headers=h).status_code==404
    assert client.get(BASE+'/storage-units',headers=h).json()['items']==[]


def test_stale_offline_unknown_and_missing(client,db_session,partner):
    db=db_session
    reading=db.scalar(select(SensorReading).where(SensorReading.device_id==1));reading.timestamp=now()-timedelta(hours=4)
    db.get(Device,1).last_seen_at=now();db.commit()
    h=headers(client,partner)
    r=client.get(BASE+'/storage-units/'+partner['unit']+'/latest',headers=h).json()
    assert r['devices'][0]['status']=='online'
    assert all(x['is_stale'] for x in r['items'])
    b=client.get(BASE+'/storage-units/'+partner['unit']+'/latest',headers=headers(client,partner,'producer_b')).json()
    assert b['devices'][0]['status']=='offline'
    db.get(Device,1).expected_reading_interval_minutes=None;db.commit()
    r=client.get(BASE+'/storage-units/'+partner['unit']+'/latest',headers=h).json()
    assert r['devices'][0]['status']=='unknown' and all(x['is_stale'] is None for x in r['items'])
    r=client.get(BASE+'/storage-units/'+partner['private']+'/latest',headers=headers(client,partner,'producer_b')).json()
    assert r['items']==[] and r['devices']==[]


@pytest.mark.parametrize('field,value',[('ambient_temperature',200),('ambient_temperature',float('inf')),('ambient_humidity',-5)])
def test_invalid_values_are_null(client,db_session,partner,field,value):
    row=db_session.scalar(select(SensorReading).where(SensorReading.device_id==1));setattr(row,field,value);db_session.commit()
    r=client.get(BASE+'/storage-units/'+partner['unit']+'/latest',headers=headers(client,partner))
    assert r.status_code==200,r.text
    invalid=[x for x in r.json()['items'] if x['quality_status']=='invalid'];assert invalid and invalid[0]['value'] is None


def test_not_installed_channel_and_no_readings(client,db_session,partner):
    db=db_session
    for c in db.scalars(select(DeviceChannel).where(DeviceChannel.device_id==1)):c.is_installed=False
    db.commit()
    r=client.get(BASE+'/storage-units/'+partner['unit']+'/latest',headers=headers(client,partner)).json()
    assert r['items']==[] and r['devices'][0]['capabilities']==[]


@pytest.mark.parametrize('params',[{'from':'2026-01-03T00:00:00Z','to':'2026-01-01T00:00:00Z'}, {'from':'2026-01-01','to':'2026-01-02'}, {'from':'2026-01-01T00:00:00Z','to':'2026-03-01T00:00:00Z'}, {'from':'2026-01-01T00:00:00+01:00','to':'2026-01-02T00:00:00+01:00'}, {'limit':501}, {'metric_code':'GRAIN_MOISTURE_EMC_PCT'}, {'unknown':'x'}])
def test_invalid_filters(client,partner,params):
    r=client.get(BASE+'/storage-units/'+partner['unit']+'/readings',headers=headers(client,partner),params=params)
    assert r.status_code in [400,422],r.text


def test_pagination_ties_snapshot_and_cursor_binding(client,db_session,partner):
    db=db_session
    for i in range(112):db.add(SensorReading(company_id=1,site_id=1,storage_unit_id=1,device_id=1,ambient_temperature=20+i/100,timestamp=partner['stamp'],received_at=partner['stamp']))
    db.commit()
    h=headers(client,partner);params={**period(),'limit':7};url=BASE+'/storage-units/'+partner['unit']+'/readings'
    r=client.get(url,headers=h,params=params);assert r.status_code==200,r.text
    first=r.json();cursor=first['next_cursor'];assert cursor
    for changed in [{**params,'metric_code':'AMBIENT_TEMPERATURE_C'},{**params,'limit':8},{**params,'cursor':cursor+'x'}]:
        q={**changed,'cursor':changed.get('cursor',cursor)}
        assert client.get(url,headers=h,params=q).status_code==400
    assert client.get(url,headers=headers(client,partner,'producer_b'),params={**params,'cursor':cursor}).status_code==400
    # Late arrival must not alter the frozen cursor snapshot.
    db.add(SensorReading(company_id=1,site_id=1,storage_unit_id=1,device_id=1,ambient_temperature=29,timestamp=partner['stamp']-timedelta(seconds=1),received_at=now()));db.commit()
    found=list(first['items'])
    while cursor:
        r=client.get(url,headers=h,params={**params,'cursor':cursor});assert r.status_code==200,r.text
        found+=r.json()['items'];cursor=r.json()['next_cursor']
    assert len(found)==114
    assert len({x['reading_id'] for x in found})==114


def test_canonical_legacy_reconciliation(client,db_session,partner):
    db=db_session;legacy=db.scalar(select(SensorReading).where(SensorReading.device_id==1))
    channel=db.scalar(select(DeviceChannel).where(DeviceChannel.device_id==1,DeviceChannel.channel_key=='ambient_temp_1'))
    definition=db.scalar(select(MetricDefinition).where(MetricDefinition.metric_code=='AMBIENT_TEMPERATURE_C'))
    event=TelemetryEvent(company_id=1,storage_unit_id=1,device_id=1,sensor_reading_id=legacy.id,boot_id=100,sequence=1,sample_counter=1,sampled_at=legacy.timestamp,received_at_cloud=legacy.received_at,time_quality='NTP_SYNCED',protocol_version=1)
    db.add(event);db.flush()
    db.add(MetricReading(telemetry_event_id=event.id,company_id=1,storage_unit_id=1,device_id=1,sensor_channel_id=channel.id,metric_definition_id=definition.id,metric_code=definition.metric_code,raw_value=23,display_value=23,canonical_unit='degC',quality_status='VALID',sampled_at=legacy.timestamp,received_at=legacy.received_at));db.commit()
    r=client.get(BASE+'/storage-units/'+partner['unit']+'/readings',headers=headers(client,partner),params=period())
    assert r.status_code==200,r.text
    assert len(r.json()['items'])==2
    assert [x for x in r.json()['items'] if x['metric_code']=='AMBIENT_TEMPERATURE_C'][0]['quality_status']=='valid'


def test_rate_limit_and_token_abuse(client,partner,monkeypatch):
    h=headers(client,partner)
    monkeypatch.setattr(settings,'partner_burst',2);monkeypatch.setattr(settings,'partner_requests_per_minute',1)
    # Existing data bucket has not been used by token requests.
    assert client.get(BASE+'/storage-units',headers=h).status_code==200
    assert client.get(BASE+'/storage-units',headers=h).status_code==200
    r=client.get(BASE+'/storage-units',headers=h);assert r.status_code==429 and int(r.headers['retry-after'])>=1
    monkeypatch.setattr(settings,'partner_auth_burst',1);monkeypatch.setattr(settings,'partner_auth_per_minute',1)
    r=token(client,partner);assert r.status_code==200
    assert token(client,partner).status_code==429


def test_audit_safe_and_existing_login_compatible(client,db_session,partner,caplog):
    with caplog.at_level(logging.INFO,logger='agroescudo.partner'):
        h=headers(client,partner);r=client.get(BASE+'/storage-units',headers=h)
    audit=db_session.scalar(select(PartnerAudit).where(PartnerAudit.request_id==r.headers['x-request-id']))
    assert audit.status_code==200 and audit.client_id=='test-partner'
    assert partner['secret'] not in caplog.text and h['Authorization'] not in caplog.text
    assert 'token_hash' not in r.text and 'secret_hash' not in r.text
    assert client.post('/api/auth/login',json={'email':'admin@agroescudo.local','password':'admin123'}).status_code==200


def test_disabled_and_https(client,partner,monkeypatch):
    monkeypatch.setattr(settings,'partner_api_enabled',False)
    assert client.get(BASE+'/storage-units').status_code==404
    monkeypatch.setattr(settings,'partner_api_enabled',True);monkeypatch.setattr(settings,'environment','production')
    assert client.get(BASE+'/storage-units').status_code==400


def test_admin_rejects_inconsistent_hierarchy(db_session,partner):
    producer=db_session.get(PartnerProducer,partner['pa'])
    foreign=db_session.scalar(select(StorageUnit).where(StorageUnit.name=='Foreign'))
    with pytest.raises(ValueError):admin.grant(db_session,producer,foreign.id,'test')
    with pytest.raises(ValueError):admin.grant(db_session,producer,1,'test',device_id=9999)
    with pytest.raises(ValueError):admin.grant(db_session,producer,1,'test',channel_key='ambient_temp_1')


def test_only_five_routes_and_openapi_security(client,partner):
    schema=client.get('/openapi.json').json();paths={k:v for k,v in schema['paths'].items() if k.startswith(BASE)}
    assert len(paths)==5
    assert schema['components']['securitySchemes']['PartnerBasic']['scheme']=='basic'
    assert schema['components']['securitySchemes']['PartnerClientCredentials']['flows']['clientCredentials']['tokenUrl']==BASE+'/oauth/token'
    assert client.post(BASE+'/storage-units',headers=headers(client,partner),json={}).status_code==405


@pytest.mark.parametrize('kind',['organization','producer','expired_grant','future_grant','bad_device_company','deleted_unit'])
def test_live_link_and_hierarchy_checks(client,db_session,partner,kind):
    h=headers(client,partner);db=db_session
    if kind=='organization':db.get(PartnerOrganization,partner['org']).revoked_at=now()
    elif kind=='producer':db.get(PartnerProducer,partner['pa']).revoked_at=now()
    elif kind=='expired_grant':db.get(PartnerGrant,partner['grant']).expires_at=now()-timedelta(seconds=1)
    elif kind=='future_grant':db.get(PartnerGrant,partner['grant']).valid_from=now()+timedelta(hours=1)
    elif kind=='bad_device_company':db.get(Device,1).company_id=99999
    elif kind=='deleted_unit':db.get(StorageUnit,1).deleted_at=now()
    db.commit();r=client.get(BASE+'/storage-units/'+partner['unit']+'/latest',headers=h)
    if kind in ['organization','producer']:assert r.status_code==403,r.text
    elif kind=='bad_device_company':assert r.status_code==200 and r.json()['devices']==[] and r.json()['items']==[]
    else:assert r.status_code==404,r.text


def test_secret_rotation_and_demo_disabled_outside_sandbox(client,db_session,partner,monkeypatch):
    h=headers(client,partner);db=db_session
    cl=db.get(PartnerClient,partner['client']);new=admin.rotate(db,cl,'test',overlap=0);db.commit()
    assert token(client,partner).status_code==401
    assert client.get(BASE+'/storage-units',headers=h).status_code==401
    partner['secret']=new
    assert token(client,partner).status_code==200
    db.get(PartnerClient,partner['client']).is_demo=True;db.commit();monkeypatch.setattr(settings,'partner_sandbox',False)
    assert token(client,partner).status_code==401


def test_alert_filters_pagination_and_missing_dates(client,db_session,partner):
    db=db_session;stamp=partner['stamp']
    for i in range(16):db.add(Alert(company_id=1,site_id=1,storage_unit_id=1,device_id=1,alert_type='demo',metric='ambient_temperature',severity='critical',title='test',message='test',is_active=False,resolved_at=now(),created_at=stamp))
    db.commit();h=headers(client,partner);url=BASE+'/storage-units/'+partner['unit']+'/alerts'
    r=client.get(url,headers=h,params={'status':'resolved','severity':'critical','limit':3});assert r.status_code==200,r.text
    found=r.json()['items'];cursor=r.json()['next_cursor']
    while cursor:
        r=client.get(url,headers=h,params={'status':'resolved','severity':'critical','limit':3,'cursor':cursor});assert r.status_code==200,r.text
        found+=r.json()['items'];cursor=r.json()['next_cursor']
    assert len(found)==16 and len({x['id'] for x in found})==16
    assert client.get(url,headers=h,params={'from':stamp.isoformat()}).status_code==400
    assert client.get(url,headers=h,params={'device_id':partner['other_device']}).status_code==404


def test_half_open_period_and_latest_per_channel(client,db_session,partner):
    db=db_session;t=partner['stamp']
    db.add(SensorReading(company_id=1,site_id=1,storage_unit_id=1,device_id=1,ambient_temperature=25,timestamp=t+timedelta(seconds=5),received_at=t+timedelta(seconds=5)));db.commit()
    h=headers(client,partner);url=BASE+'/storage-units/'+partner['unit']
    r=client.get(url+'/readings',headers=h,params={'from':t.isoformat(),'to':(t+timedelta(seconds=5)).isoformat()})
    assert r.status_code==200,r.text
    assert len(r.json()['items'])==2
    r=client.get(url+'/latest',headers=h);assert r.status_code==200,r.text
    values={v['metric_code']:v for v in r.json()['items']}
    assert values['AMBIENT_TEMPERATURE_C']['value']==25
    assert values['AMBIENT_RELATIVE_HUMIDITY_PCT']['sampled_at']!=values['AMBIENT_TEMPERATURE_C']['sampled_at']


def test_cursor_revocation_no_cache_and_size_limit(client,db_session,partner,monkeypatch):
    h=headers(client,partner);url=BASE+'/storage-units/'+partner['unit']+'/readings';params={**period(),'limit':1}
    r=client.get(url,headers=h,params=params);assert r.status_code==200,r.text
    cursor=r.json()['next_cursor'];assert cursor
    db_session.get(PartnerGrant,partner['grant']).revoked_at=now();db_session.commit()
    assert client.get(url,headers=h,params={**params,'cursor':cursor}).status_code==404
    h_b=headers(client,partner,'producer_b')
    monkeypatch.setattr(settings,'partner_max_response_bytes',20)
    assert client.get(BASE+'/storage-units',headers=h_b).status_code==400


def test_shared_sql_quota_and_client_separation(db_session,partner):
    from sqlalchemy.orm import Session
    engine=db_session.get_bind()
    with Session(engine) as a:quota(a,'test-shared',1,1)
    with Session(engine) as b:
        with pytest.raises(PartnerError) as exc:quota(b,'test-shared',1,1)
        assert exc.value.status==429
        quota(b,'other-client',1,1)


def test_malformed_auth_is_limited_and_audited(client,db_session,partner,monkeypatch):
    monkeypatch.setattr(settings,'partner_auth_burst',1);monkeypatch.setattr(settings,'partner_auth_per_minute',1)
    r=client.post(BASE+'/oauth/token',json={'grant_type':'client_credentials'});assert r.status_code==400
    event=db_session.scalar(select(PartnerAudit).where(PartnerAudit.request_id==r.headers['x-request-id']))
    assert event.status_code==400
    assert client.post(BASE+'/oauth/token',json={}).status_code==429


def test_partner_migration_additive_roundtrip():
    import importlib.util
    from pathlib import Path
    from sqlalchemy import create_engine,inspect
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from app.db.base import Base
    engine=create_engine('sqlite://')
    path=Path(__file__).parents[1]/'alembic/versions/202611070001_partner_api_p0.py'
    spec=importlib.util.spec_from_file_location('partner_migration',path);migration=importlib.util.module_from_spec(spec);spec.loader.exec_module(migration)
    with engine.begin() as connection:
        old=[t for t in Base.metadata.sorted_tables if not t.name.startswith('partner_')]
        Base.metadata.create_all(connection,tables=old)
        before=set(inspect(connection).get_table_names())
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade();assert len(set(inspect(connection).get_table_names())-before)==8
            migration.downgrade();assert set(inspect(connection).get_table_names())==before
    engine.dispose()


def test_catalogue_cursor_and_cross_endpoint_binding(client,partner):
    h=headers(client,partner,'producer_b');url=BASE+'/storage-units'
    a=client.get(url,headers=h,params={'limit':1});assert a.status_code==200,a.text
    cursor=a.json()['next_cursor'];assert cursor
    b=client.get(url,headers=h,params={'limit':1,'cursor':cursor});assert b.status_code==200,b.text
    assert a.json()['items'][0]['id']!=b.json()['items'][0]['id'] and b.json()['next_cursor'] is None
    assert client.get(url+'/'+partner['unit']+'/alerts',headers=h,params={'limit':1,'cursor':cursor}).status_code==400


def test_admin_rotation_never_revives_expired_credential(client,db_session,partner):
    db=db_session;cl=db.get(PartnerClient,partner['client'])
    old=db.scalar(select(PartnerCredential).where(PartnerCredential.client_id==cl.id));old.expires_at=now()-timedelta(seconds=1);db.commit()
    new=admin.rotate(db,db.get(PartnerClient,partner['client']),'test',overlap=3600);db.commit()
    assert token(client,partner).status_code==401
    partner['secret']=new;assert token(client,partner).status_code==200


def test_export_matches_runtime_and_contains_no_internal_schemas(client,partner):
    from scripts.export_partner_openapi import schema
    exported=schema();runtime=client.get('/openapi.json').json()
    assert exported['paths']=={k:v for k,v in runtime['paths'].items() if k.startswith(BASE)}
    assert 'AdminDeviceSecretOut' not in exported['components']['schemas']
    assert 'UserOut' not in exported['components']['schemas']


def test_sandbox_seed_is_real_and_refuses_existing_data(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.db.base import Base
    from app.services.partner_sandbox import seed
    monkeypatch.setattr(settings,'partner_sandbox',True)
    engine=create_engine('sqlite://');Base.metadata.create_all(engine)
    with Session(engine) as db:
        result=seed(db)
        assert set(result['producers'])=={'prod_demo_a','prod_demo_b'}
        assert db.scalar(select(func.count(PartnerGrant.id)))==4
        assert db.scalar(select(func.count(SensorReading.id)))==75
        with pytest.raises(ValueError):seed(db)
    monkeypatch.setattr(settings,'partner_sandbox',False)
    with Session(engine) as db:
        with pytest.raises(ValueError):seed(db)
    engine.dispose()


def test_internal_cli_list_and_revoke_never_show_hashes(db_session,partner,monkeypatch,capsys):
    import sys
    from scripts import partner_admin as cli
    monkeypatch.setattr(cli,'SessionLocal',lambda:db_session)
    monkeypatch.setattr(sys,'argv',['partner_admin','--operator','unit-test','list','--kind','credential'])
    cli.main();output=capsys.readouterr().out
    assert 'secret_hash' not in output and partner['secret'] not in output
    credential=db_session.scalar(select(PartnerCredential))
    monkeypatch.setattr(sys,'argv',['partner_admin','--operator','unit-test','revoke','--kind','credential','--id',str(credential.id)])
    cli.main();capsys.readouterr()
    assert db_session.get(PartnerCredential,credential.id).revoked_at is not None
