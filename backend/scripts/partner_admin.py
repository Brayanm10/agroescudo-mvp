"""Run from backend: python -m scripts.partner_admin --help. OS/DB access required."""
import argparse
import json
from datetime import datetime
from sqlalchemy import select
from app.db.session import SessionLocal
from app.partner_models import PartnerClient, PartnerCredential, PartnerGrant, PartnerOrganization, PartnerProducer, PartnerToken
from app.services import partner_admin as admin


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--operator',required=True,help='Referencia interna del aprobador, registrada en auditoría')
    sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('create-client');c.add_argument('--client-id',required=True);c.add_argument('--name',required=True);c.add_argument('--scopes',nargs='+',required=True)
    c=sub.add_parser('rotate-secret');c.add_argument('--client-id',required=True);c.add_argument('--overlap-seconds',type=int,default=0)
    c=sub.add_parser('set-scopes');c.add_argument('--client-id',required=True);c.add_argument('--scopes',nargs='+',required=True)
    c=sub.add_parser('link-org');c.add_argument('--client-id',required=True);c.add_argument('--external-id',required=True);c.add_argument('--company-id',required=True,type=int)
    c=sub.add_parser('link-producer');c.add_argument('--organization-id',required=True,type=int);c.add_argument('--external-id',required=True);c.add_argument('--user-id',type=int)
    c=sub.add_parser('grant');c.add_argument('--producer-id',required=True,type=int);c.add_argument('--unit-id',required=True,type=int);c.add_argument('--device-id',type=int);c.add_argument('--channel-key');c.add_argument('--expires-at');c.add_argument('--valid-from')
    c=sub.add_parser('revoke');c.add_argument('--kind',choices=['client','credential','token','organization','producer','grant'],required=True);c.add_argument('--id',type=int,required=True)
    c=sub.add_parser('list');c.add_argument('--kind',choices=['client','credential','token','organization','producer','grant'],required=True)
    a=p.parse_args()
    kinds={'client':PartnerClient,'credential':PartnerCredential,'token':PartnerToken,'organization':PartnerOrganization,'producer':PartnerProducer,'grant':PartnerGrant}
    with SessionLocal() as db:
        try:
            def client():
                row=db.scalar(select(PartnerClient).where(PartnerClient.client_id==a.client_id))
                if not row:raise ValueError('Cliente no encontrado.')
                return row
            result={}
            if a.command=='create-client':
                row,raw=admin.create_client(db,a.client_id,a.name,a.scopes,a.operator);result={'id':row.id,'client_id':row.client_id,'client_secret':raw,'notice':'Mostrar una sola vez; transferir por canal seguro, no guardar en Git/logs.'}
            elif a.command=='rotate-secret':result={'client_secret':admin.rotate(db,client(),a.operator,a.overlap_seconds),'notice':'Secreto nuevo; retirar el anterior al concluir el solapamiento.'}
            elif a.command=='set-scopes':
                from app.services.partner_security import SCOPES
                if not set(a.scopes)<=SCOPES or not a.scopes:raise ValueError('Scopes inválidos.')
                row=client();row.scopes=' '.join(sorted(set(a.scopes)));admin.audit(db,a.operator,'set_scopes',row.id)
                # Existing tokens can only lose, never gain, permissions.
            elif a.command=='link-org':result={'id':admin.link_org(db,client(),a.external_id,a.company_id,a.operator).id}
            elif a.command=='link-producer':
                org=db.get(PartnerOrganization,a.organization_id)
                if not org:raise ValueError('Organización no encontrada.')
                result={'id':admin.link_producer(db,org,a.external_id,a.operator,a.user_id).id}
            elif a.command=='grant':
                producer=db.get(PartnerProducer,a.producer_id)
                if not producer:raise ValueError('Productor no encontrado.')
                result={'id':admin.grant(db,producer,a.unit_id,a.operator,a.device_id,a.channel_key,datetime.fromisoformat(a.valid_from) if a.valid_from else None,datetime.fromisoformat(a.expires_at) if a.expires_at else None).id}
            elif a.command=='revoke':
                row=db.get(kinds[a.kind],a.id)
                if not row:raise ValueError('Registro no encontrado.')
                admin.revoke(db,a.kind,row,a.operator)
            elif a.command=='list':
                # Explicit allowlist: never serialize hashes or tokens.
                rows=list(db.scalars(select(kinds[a.kind]).limit(1000)).all())
                result=[{k:str(getattr(r,k)) for k in ['id','client_id','organization_id','external_id','company_id','producer_id','storage_unit_id','device_id','channel_key','scopes','expires_at','revoked_at'] if hasattr(r,k)} for r in rows]
            db.commit();print(json.dumps(result,ensure_ascii=False))
        except Exception:
            db.rollback()
            p.exit(1,'Operación no aplicada; revisar IDs, vigencia, permisos y unicidad. No se imprimen excepciones SQL ni secretos.\n')


if __name__=='__main__':main()
