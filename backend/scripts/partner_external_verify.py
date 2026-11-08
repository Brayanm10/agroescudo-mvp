"""Bounded public HTTPS probe. No production fallback and no secret output."""
import argparse
import json
import time
from datetime import datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlsplit
import httpx
from app.partner_schemas import PartnerAlertsOut,PartnerLatestOut,PartnerReadingsOut,PartnerUnitsOut


def verify(config,check_rate=False):
    url=urlsplit(config['base_url'])
    if config.get('environment')!='staging' or config.get('service_label')!='AgroEscudo LEADY Staging':raise ValueError('not-staging')
    if url.scheme!='https' or not url.hostname or not url.hostname.endswith('.onrender.com') or url.username or url.password or url.port not in (None,443) or url.path not in ('','/') or url.query or url.fragment:raise ValueError('unapproved-url')
    with httpx.Client(base_url=config['base_url'],timeout=httpx.Timeout(10,connect=5),follow_redirects=False) as client:
        health=client.get('/health');assert health.status_code==200 and health.json()['environment']=='staging'
        assert client.get('/ready').status_code==200
        auth=client.post('/api/v1/partner/oauth/token',auth=(config['client_id'],config['client_secret']),data={'grant_type':'client_credentials'})
        assert auth.status_code==200 and auth.json()['expires_in']==600
        token=auth.json()['access_token']
        def get(path,producer,**kwargs):
            h={'Authorization':'Bearer '+token,'X-LEADY-Organization-Id':config['organization_id'],'X-LEADY-Producer-Id':producer}
            for _ in range(4):
                r=client.get(path,headers=h,**kwargs)
                if r.status_code!=429:return r
                delay=int(r.headers.get('Retry-After','1'))
                if not 1<=delay<=5:raise ValueError('retry-budget')
                time.sleep(delay)
            raise ValueError('quota-not-recovered')
        prefix='/api/v1/partner/storage-units';a,b=config['producers'][:2]
        ra=get(prefix,a);assert ra.status_code==200;PartnerUnitsOut.model_validate(ra.json());ua=ra.json()['items']
        rb=get(prefix,b);assert rb.status_code==200;PartnerUnitsOut.model_validate(rb.json());ub=rb.json()['items']
        assert ua and ub
        for unit in ua:
            path=prefix+'/'+unit['id']
            r=get(path+'/latest',a);assert r.status_code==200;PartnerLatestOut.model_validate(r.json())
            params={'from':(datetime.now(timezone.utc)-timedelta(days=2)).isoformat(),'to':datetime.now(timezone.utc).isoformat(),'limit':2}
            ids=[]
            for _ in range(3):
                r=get(path+'/readings',a,params=params);assert r.status_code==200;PartnerReadingsOut.model_validate(r.json());ids += [x['reading_id'] for x in r.json()['items']]
                if not r.json()['next_cursor']:break
                params['cursor']=r.json()['next_cursor']
            assert len(ids)==len(set(ids))
            for state in ('active','resolved'):
                r=get(path+'/alerts',a,params={'status':state});assert r.status_code==200;PartnerAlertsOut.model_validate(r.json())
        shared={u['id'] for u in ua}&{u['id'] for u in ub};assert shared
        for uid in shared:
            da={d['id'] for u in ua if u['id']==uid for d in u['devices']};db={d['id'] for u in ub if u['id']==uid for d in u['devices']}
            assert da.isdisjoint(db)
        private=next(u['id'] for u in ua if u['id'] not in shared)
        assert get(prefix+'/'+private+'/latest',b).status_code==404
        if check_rate:
            h={'Authorization':'Bearer '+token,'X-LEADY-Organization-Id':config['organization_id'],'X-LEADY-Producer-Id':a}
            results=[client.get(prefix,headers=h) for _ in range(12)]
            assert any(r.status_code==429 and int(r.headers['Retry-After'])>=1 for r in results)
    return {'https_health':'PASS','oauth':'PASS','four_gets':'PASS','schemas':'PASS','pagination':'PASS','isolation':'PASS','revocation':'PENDING_CONSOLE_TEST','postman':'PENDING_COLLECTION_RUN','rate_limit':'PASS' if check_rate else 'PENDING','commit':'RECORD_FROM_RENDER'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--credentials-file',required=True);p.add_argument('--check-rate-limit',action='store_true');a=p.parse_args()
    try:
        result=verify(json.loads(Path(a.credentials_file).read_text(encoding='utf-8')),a.check_rate_limit)
        print(json.dumps(result,indent=2))
    except Exception:p.exit(1,'FAIL: verificación externa no aprobada. Revisar consola del entorno staging; no se imprimen URL privadas, cuerpos ni credenciales.\n')
