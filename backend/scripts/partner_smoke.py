"""Executable HTTP examples; reads local credentials at runtime, never logs tokens."""
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
import httpx


def run(config):
    with httpx.Client(base_url=config['base_url'],timeout=5) as client:
        r=client.post('/api/v1/partner/oauth/token',auth=(config['client_id'],config['client_secret']),data={'grant_type':'client_credentials'})
        r.raise_for_status();token=r.json()['access_token']
        h={'Authorization':'Bearer '+token,'X-LEADY-Organization-Id':config['organization_id'],'X-LEADY-Producer-Id':config['producers'][0]}
        prefix='/api/v1/partner/storage-units'
        a=client.get(prefix,headers=h);a.raise_for_status();units_a=a.json()['items'];assert units_a
        for u in units_a:
            for suffix,params in [('latest',{}),('readings',{'from':(datetime.now(timezone.utc)-timedelta(days=2)).isoformat(),'to':datetime.now(timezone.utc).isoformat(),'limit':100}),('alerts',{'limit':100})]:
                r=client.get(prefix+'/'+u['id']+'/'+suffix,headers=h,params=params);r.raise_for_status();assert isinstance(r.json()['items'],list)
        h['X-LEADY-Producer-Id']=config['producers'][1]
        b=client.get(prefix,headers=h);b.raise_for_status();units_b=b.json()['items']
        shared=set(u['id'] for u in units_a)&set(u['id'] for u in units_b);assert len(shared)==1
        for uid in shared:
            da={d['id'] for u in units_a if u['id']==uid for d in u['devices']}
            db={d['id'] for u in units_b if u['id']==uid for d in u['devices']};assert da.isdisjoint(db)
        private=next(u['id'] for u in units_a if u['id'] not in shared)
        assert client.get(prefix+'/'+private+'/latest',headers=h).status_code==404
    print('PASS HTTP sandbox: token, cuatro GET, productores A/B, centro compartido y rechazo cruzado. No se imprimen secretos.')


if __name__=='__main__':
    run(json.loads((Path(__file__).resolve().parents[2]/'.sandbox/leady/credentials.json').read_text(encoding='utf-8')))
