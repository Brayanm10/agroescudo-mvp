"""Internal provisioning. Callers need trusted OS/DB access; no HTTP admin API."""
import secrets
from datetime import timedelta
from sqlalchemy import func, select
from app.models import Company, Device, DeviceChannel, Site, StorageUnit, User
from app.partner_models import PartnerAudit, PartnerClient, PartnerCredential, PartnerGrant, PartnerOrganization, PartnerProducer, PartnerToken
from app.services.partner_security import SCOPES, aware, now, secret_hash


def audit(db, actor, action, resource):
    if not actor or len(actor)>160:
        raise ValueError('Responsable de aprobación requerido (máximo 160 caracteres).')
    # Actor is an internal operator reference, not personal data in public logs.
    db.add(PartnerAudit(request_id=secrets.token_hex(16),client_id=None,action='admin.'+action,
                        resource=(actor+':'+str(resource))[:200],status_code=200,occurred_at=now(),latency_ms=0))


def create_client(db, client_id, name, scopes, actor, demo=False):
    if not client_id or len(client_id)>128 or not scopes or not set(scopes)<=SCOPES:
        raise ValueError('Identificador/scopes inválidos.')
    if db.scalar(select(PartnerClient.id).where(PartnerClient.client_id==client_id)):
        raise ValueError('El cliente ya existe; use rotación explícita.')
    client=PartnerClient(client_id=client_id,name=name,scopes=' '.join(sorted(set(scopes))),is_demo=demo)
    db.add(client);db.flush()
    raw=secrets.token_urlsafe(48)
    db.add(PartnerCredential(client_id=client.id,secret_hash=secret_hash(raw)))
    audit(db,actor,'create_client',client_id)
    db.flush()
    return client,raw


def link_org(db, client, external_id, company_id, actor):
    company=db.get(Company,company_id)
    if not company or not company.is_active or company.deleted_at:raise ValueError('Empresa no válida.')
    if not external_id or len(external_id)>128:raise ValueError('Identificador externo inválido.')
    row=PartnerOrganization(client_id=client.id,external_id=external_id,company_id=company_id)
    db.add(row);db.flush();audit(db,actor,'link_organization',row.id)
    return row


def link_producer(db, org, external_id, actor, user_id=None):
    if not external_id or len(external_id)>128:raise ValueError('Identificador externo inválido.')
    if user_id:
        u=db.get(User,user_id)
        if not u or u.company_id!=org.company_id or not u.is_active or u.deleted_at or u.status!='ACTIVE':raise ValueError('Usuario no válido para la empresa.')
    row=PartnerProducer(organization_id=org.id,external_id=external_id,user_id=user_id)
    db.add(row);db.flush();audit(db,actor,'link_producer',row.id)
    return row


def grant(db, producer, unit_id, actor, device_id=None, channel_key=None, valid_from=None, expires_at=None):
    org=db.get(PartnerOrganization,producer.organization_id)
    unit=db.get(StorageUnit,unit_id)
    site=db.get(Site,unit.site_id) if unit else None
    company=db.get(Company,org.company_id)
    if not company or not company.is_active or company.deleted_at or not unit or not site or unit.company_id!=org.company_id or site.company_id!=org.company_id or unit.deleted_at or not unit.is_active or unit.operation_type!='storage':
        raise ValueError('Jerarquía de empresa/sitio/unidad inválida.')
    if device_id:
        d=db.get(Device,device_id)
        if not d or d.storage_unit_id!=unit.id or d.company_id!=org.company_id or d.site_id!=site.id or d.deleted_at:
            raise ValueError('Dispositivo ajeno a la unidad/empresa.')
    if channel_key:
        ch=db.scalar(select(DeviceChannel).where(DeviceChannel.device_id==device_id,DeviceChannel.channel_key==channel_key))
        if not device_id or not ch or not ch.is_active or not ch.is_installed or not ch.is_enabled or ch.retired_at or not ch.is_visible_to_client:
            raise ValueError('Canal no disponible o dispositivo requerido.')
    if producer.revoked_at or org.revoked_at:raise ValueError('Vínculo revocado.')
    if db.scalar(select(func.count(PartnerGrant.id)).where(PartnerGrant.producer_id==producer.id,PartnerGrant.revoked_at.is_(None)))>=1000:
        raise ValueError('Máximo 1000 concesiones activas; acotar configuración.')
    valid_from=valid_from or now()
    if valid_from.tzinfo is None or (expires_at and (expires_at.tzinfo is None or expires_at<=valid_from)):
        raise ValueError('Vigencia inválida; usar fechas con zona horaria.')
    row=PartnerGrant(producer_id=producer.id,storage_unit_id=unit_id,device_id=device_id,channel_key=channel_key,
        approved_by=actor,authorized_at=now(),valid_from=valid_from,expires_at=expires_at)
    db.add(row);db.flush();audit(db,actor,'grant',row.id)
    return row


def rotate(db, client, actor, overlap=0):
    if not 0<=overlap<=86400:raise ValueError('Solapamiento máximo 86400 segundos.')
    credentials=list(db.scalars(select(PartnerCredential).where(PartnerCredential.client_id==client.id,PartnerCredential.revoked_at.is_(None)).order_by(PartnerCredential.id)).all())
    stamp=now()
    current=[c for c in credentials if c.expires_at is None or aware(c.expires_at)>stamp]
    for c in credentials:
        if overlap and current and c.id==current[-1].id:
            cutoff=stamp+timedelta(seconds=overlap)
            c.expires_at=min(aware(c.expires_at),cutoff) if c.expires_at else cutoff
        else:c.revoked_at=stamp
    raw=secrets.token_urlsafe(48)
    db.add(PartnerCredential(client_id=client.id,secret_hash=secret_hash(raw)))
    audit(db,actor,'rotate',client.client_id)
    return raw


def revoke(db, kind, row, actor):
    row.revoked_at=now()
    if kind=='client':row.is_active=False
    audit(db,actor,'revoke_'+kind,row.id)
