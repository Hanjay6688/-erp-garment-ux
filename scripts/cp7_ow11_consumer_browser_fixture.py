"""Explicit historical fixture plus actual posted sale, only on browser clone."""
from datetime import date,timedelta
from urllib.parse import urlparse
import json,os,sys,uuid
import psycopg
import cp7_ow11_analog_consumer_cases as consumer


def main():
    url=os.environ['AUDITOR_BROWSER_DB_URL'];p=json.load(sys.stdin)
    assert urlparse(url).hostname in('localhost','127.0.0.1')and urlparse(url).path=='/cp6_auditor_browser'
    assert sys.argv[1]=='prepare'
    with psycopg.connect(url)as conn,conn.cursor()as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        today=date.fromisoformat(p['today']);f=consumer.prepare(cur,today,dense=p['dense'])
        import cp7_sales_cases as sales
        import cp7_procurement_cases as receipt
        day=today-timedelta(days=1);product=f['source'].split(':')[0]
        sales.fg.ax.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=product,location_id=sales.fg.base.LOCATION,
          qty_pcs=10,physical_at=receipt.aa.at(day,8).isoformat(),reason='Consumer browser Native posted sale fixture'))
        consumer.plan.b.api.admin(cur);tag='OW11CB-'+uuid.uuid4().hex[:10]
        customer=str(sales.fg.base.create_customer(cur,tag))
        draft=consumer.plan.b.chain.production.rpc(cur,'erp.save_sale_draft_v2',dict(sale_number=tag,customer_id=customer,
          source_location_id=sales.fg.base.LOCATION,sale_date=receipt.aa.at(day,10).isoformat(),reason='Consumer browser actual Native demand',
          items=[dict(product_id=product,qty_pcs=1,unit_price_snapshot='20',discount_amount='0')]),uuid.uuid4(),None)
        sales.fg.post_sale(cur,draft);consumer.plan.b.api.admin(cur)
        sku=cur.execute('select sku from erp.products where id=%s',(f['target'].split(':')[0],)).fetchone()[0]
        days=1 if p['dense']else 3
        out=dict(root=f['target'].split(':')[0],target_key=f['target'],source_key=f['source'],sku=sku,
          query=dict(from_date=str(today-timedelta(days=days)),through_date=str(day),group_mode='AS_SOLD'),
          size=f['size'],expected_targets=len(f['row']['reference']['facts']['products']),
          scale='0.5'if p['dense']else'1',expected_target='2'if p['dense']else'1',source_total_pcs='1',available_days=str(days),
          actual_Native_posted_sale=True,synthetic_historical_openings=True)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))


if __name__=='__main__':main()
