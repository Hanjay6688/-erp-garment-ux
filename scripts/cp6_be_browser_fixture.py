"""BE browser setup/read on its committed disposable copy only. No product DML bypass."""
from datetime import date,timedelta
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp6_be_probe as be
b=be.bdp

def create(cur,today,kind):
    if kind=='conversion':
        f=be.fixture(cur,today)
        return dict(lot=f['lot'],target=f['target'],location=f['location'],day=str(f['day']),
          value=str(b.lot_value(cur,f['lot'])),sku=be.one(cur,'select sku from erp.products where id=%s',f['product']),
          target_sku=be.one(cur,'select sku from erp.products where id=%s',f['target']))
    if kind=='pocket':
        cut=today-timedelta(days=10)
        f=b.bbp.production_post(cur,today,be.pocket_probe.active_unit(cur,be.pocket_probe.rows(cut)))
        return dict(batch=f['batch'],code=f['code'],cut=str(cut),period=str(cut-timedelta(days=1)),
          usage=be.one(cur,'select id::text from erp.be_pocket_usage_v1 where batch_id=%s',f['batch']),before=be.pocket_probe.amounts(cur))
    raise RuntimeError('BE_BROWSER_FIXTURE_KIND')

def read(cur,f):
    b.api.admin(cur)
    if 'lot' in f:
        docs=be.q(cur,"select c.id::text,c.status,erp._cp3_business_date(c.physical_at)::text,(c.physical_at at time zone 'Asia/Jakarta')::time::text, a.destination_lot_id::text from erp.product_conversions c join erp.be_conversion_sources_v1 s on s.conversion_id=c.id join erp.product_conversion_allocations a on a.conversion_id=c.id where s.source_lot_id=%s order by c.created_at",f['lot'])
        return dict(source_qty=be.qty(cur,f['lot']),documents=docs,target_qty=be.qty(cur,docs[-1][4]) if docs else 0,
          target_value=str(b.lot_value(cur,docs[-1][4])) if docs else None)
    return dict(amount=str(be.one(cur,'select erp.be_pocket_usage_amount_v1(%s)',f['usage'])),ledger=be.pocket_probe.amounts(cur),
      pools=be.q(cur,"select s.pool_id::text,e.kind,e.economic_date::text from erp.pocket_period_sources s join erp.pocket_period_events e on e.pool_id=s.pool_id where s.historical_usage_id=%s order by e.created_at,e.id",f['usage']))

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];parsed=urlparse(target)
    if parsed.hostname not in ('127.0.0.1','localhost') or parsed.path!='/cp6_auditor_browser':raise RuntimeError('BE_BROWSER_COPY_ONLY')
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        if sys.argv[1]=='create':
            had=be.one(cur,"select has_schema_privilege('authenticated','erp','usage')")
            if not had:cur.execute('grant usage on schema erp to authenticated')
            f=json.loads(sys.argv[2]);out=create(cur,date.fromisoformat(f['today']),f['kind']);b.api.admin(cur)
            if not had:cur.execute('revoke usage on schema erp from authenticated')
            assert be.one(cur,"select has_schema_privilege('authenticated','erp','usage')")==had
            conn.commit()
        elif sys.argv[1]=='read':out=read(cur,json.loads(sys.argv[2]));conn.rollback()
        else:raise RuntimeError('BE_BROWSER_OPERATION')
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
