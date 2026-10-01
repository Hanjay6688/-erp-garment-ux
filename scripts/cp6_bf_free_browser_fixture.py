"""Disposable prerequisites and read-only vendor evidence for the current UI.

This entrypoint never inserts a laundry tariff into SKU settings.
"""
from urllib.parse import urlparse
from datetime import timedelta,timezone
import json,os,sys
import psycopg
import cp6_bf_free_probe as free
from cp6_bd_modes import _fixture_usage

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];p=urlparse(target)
    assert p.hostname in ('127.0.0.1','localhost') and p.path=='/cp6_auditor_browser','VENDOR_FREE_BROWSER_COPY_ONLY'
    op=sys.argv[1] if len(sys.argv)>1 else 'create'
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        with _fixture_usage(cur):
            if op=='create':
                f=free.master_fixture(cur)
                sizes=[free.one(cur,'select size_code from erp.sizes where id=%s',s) for _,s in f['rows']]
                local=(f['now']-timedelta(minutes=2)).astimezone(timezone(timedelta(hours=7))).replace(microsecond=0,tzinfo=None).isoformat()
                out=dict(tag=sizes[0].rsplit('-',1)[0],sku=f['g']['sku'],roots=[r for r,_ in f['rows']],sizes=sizes,rates=f['rates'],vendor=f['vendor'],effective_local=local)
            elif op=='read':
                f=json.loads(sys.argv[2]);free.b.api.admin(cur)
                out=dict(rates=cur.execute('select distinct on(c.id) c.id::text,r.rate_status,r.rate_per_pcs::text,r.reason from erp.bd_laundry_components_v1 c join erp.bd_laundry_component_rates_v1 r on r.component_id=c.id where c.vendor_id=%s order by c.id,r.effective_from desc',(f['vendor'],)).fetchall())
            else:raise ValueError('VENDOR_FREE_BROWSER_OPERATION')
        if op=='create':conn.commit()
        else:conn.rollback()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
