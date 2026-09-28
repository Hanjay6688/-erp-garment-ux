"""Disposable browser prerequisites and native read-back; no product mocking."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp6_bf_supplier_probe as s
from cp6_bd_modes import _fixture_usage

def read(cur,f):
    s.bc.session(cur)
    out=cur.execute('select public.erp_get_supplier_credit_v1(%s::jsonb)',(json.dumps(dict(supplier_id=f['supplier'])),)).fetchone()[0]
    s.b.api.admin(cur);return out

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];p=urlparse(target)
    assert p.hostname in('127.0.0.1','localhost') and p.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        payload=json.loads(sys.argv[2])
        if sys.argv[1]=='create':
            with _fixture_usage(cur):
                out=s.fixture(cur,date.fromisoformat(payload['today']),payload['fabric']);out['view']=read(cur,out)
            conn.commit()
        elif sys.argv[1]=='read':
            with _fixture_usage(cur):out=read(cur,payload)
            conn.rollback()
        else:raise ValueError('Unknown fixture operation')
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
