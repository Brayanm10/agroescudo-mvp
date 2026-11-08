"""Fictional seed only, guarded against operational databases and environments."""
from datetime import timedelta
from sqlalchemy import func, select
from app.core.config import settings
from app.models import Alert, Company, Device, DeviceChannel, SensorReading, Site, StorageUnit
from app.services import partner_admin as admin
from app.services.device_capabilities import ensure_metric_registry, sync_device_channels
from app.services.partner_security import now, public_id


def seed(db):
    if settings.environment!='local' or not settings.partner_sandbox:
        raise ValueError('El seed solo funciona con PARTNER_SANDBOX=true en local.')
    return _seed_fictional(db, 'leady-sandbox', True)


def seed_staging(db):
    from app.services.partner_staging import check_connection
    check_connection(db.connection(), settings)
    return _seed_fictional(db, 'leady-staging', False)


def _seed_fictional(db, client_id, demo):
    if db.scalar(select(func.count(Company.id))):
        raise ValueError('Sandbox requiere una base nueva vacía. No se modifican datos existentes.')
    company=Company(name='Organización ficticia Sandbox LEADY');db.add(company);db.flush()
    site=Site(company_id=company.id,name='Centro ficticio de almacenamiento');db.add(site);db.flush()
    units=[]
    for name in ['Almacén A con lecturas antiguas','Almacén B sin lecturas','Centro compartido']:
        u=StorageUnit(company_id=company.id,site_id=site.id,name=name,unit_type='silo',operation_type='storage')
        db.add(u);db.flush();units.append(u)
    devices=[]
    for i,u in enumerate([units[0],units[1],units[2],units[2]],start=1):
        d=Device(company_id=company.id,site_id=site.id,storage_unit_id=u.id,name=f'Dispositivo ficticio {i}',external_id=f'SANDBOX-NODE-{i}',token_hash='not-an-ingestion-credential',expected_reading_interval_minutes=10,last_seen_at=now()-timedelta(hours=4) if i in (1,3) else now())
        db.add(d);db.flush();sync_device_channels(db,d)
        # This demo installation has ambient channels, no physical grain probe.
        if i in (2,3):
            for ch in db.scalars(select(DeviceChannel).where(DeviceChannel.device_id==d.id,DeviceChannel.channel_key=='grain_temp_1')):ch.is_installed=False
        devices.append(d)
    ensure_metric_registry(db)
    stamp=now()
    for i,d in enumerate(devices):
        if i==1:continue
        for j in range(25):
            measured=stamp-timedelta(hours=4 if i==0 else 0,minutes=j*10)
            db.add(SensorReading(company_id=company.id,site_id=site.id,storage_unit_id=d.storage_unit_id,device_id=d.id,
                grain_temperature=24+j/10 if i in (0,3) else None,ambient_temperature=23+j/20,ambient_humidity=54+j/3,
                timestamp=measured,received_at=measured+timedelta(seconds=3)))
        for active in [True,False]:
            db.add(Alert(company_id=company.id,site_id=site.id,storage_unit_id=d.storage_unit_id,device_id=d.id,
                alert_type='ambient_humidity_high',metric='ambient_humidity',severity='warning',title='Alerta ficticia',message='Ejemplo ficticio de humedad relativa.',observed_value=74,threshold_value=70,is_active=active,created_at=stamp-timedelta(hours=2 if active else 6),resolved_at=None if active else stamp-timedelta(hours=5)))
    client,secret=admin.create_client(db,client_id,'LEADY sandbox ficticio',sorted(admin.SCOPES),'sandbox-seed',demo=demo)
    org=admin.link_org(db,client,'org_demo_001',company.id,'sandbox-seed')
    pa=admin.link_producer(db,org,'prod_demo_a','sandbox-seed');pb=admin.link_producer(db,org,'prod_demo_b','sandbox-seed')
    admin.grant(db,pa,units[0].id,'sandbox-seed',devices[0].id)
    admin.grant(db,pb,units[1].id,'sandbox-seed',devices[1].id)
    admin.grant(db,pa,units[2].id,'sandbox-seed',devices[2].id,'ambient_temp_1')
    admin.grant(db,pb,units[2].id,'sandbox-seed',devices[3].id)
    # Second organization proves that external IDs alone do not grant resources.
    c2=Company(name='Segunda organización ficticia');db.add(c2);db.flush()
    o2=admin.link_org(db,client,'org_demo_other',c2.id,'sandbox-seed');admin.link_producer(db,o2,'prod_demo_other','sandbox-seed')
    db.commit()
    return {'client_id':client.client_id,'client_secret':secret,'organization_id':'org_demo_001','producers':['prod_demo_a','prod_demo_b'],
            'units':{u.name:public_id('su',u.id) for u in units},'base_url':'http://127.0.0.1:8020'}
