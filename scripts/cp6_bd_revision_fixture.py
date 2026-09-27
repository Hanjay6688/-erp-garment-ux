"""Native prerequisites/read-back for the BD revision's real browser, disposable only."""
from datetime import date,timedelta
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp6_bd_probe as b
from cp6_bd_revision_cases import paging_fixture
from cp6_bd_modes import _fixture_usage


def create(cur,today,kind):
    if kind=='pages':
        fx,sources,invoices=paging_fixture(b,cur,today-timedelta(days=1))
        return dict(kind=kind,vendor=fx['vendor'],sources=sources,invoices=invoices,day=str(fx['day']))
    fx=b.two_size_fixture(cur,today-timedelta(days=1),'REV-BROWSER-'+kind,7,6)
    wash=b.component(cur,fx,'REV_WASH','4321.09');finish=b.component(cur,fx,'REV_FINISH','678.91')
    package=None
    if kind=='package':
        package=b.bd(cur,'SAVE_PACKAGE',dict(vendor_id=fx['vendor'],package_code='REV_PACKAGE',package_name='Audit package',component_ids=[wash],is_active=True,reason='Synthetic browser prerequisite'))['package_id']
        b.bd(cur,'SAVE_PACKAGE_RATE',dict(package_id=package,rate_per_pcs='4321.09',effective_from=b.iso(fx['start']),reason='Synthetic browser package price'))
        b.terms(cur,fx,'PACKAGE')
        b.policy(cur,'LAU_DEC03',dict(discount='ALLOWED',extra='ALLOWED',rounding='LAST_LINE'))
    else:b.terms(cur,fx,'COMPONENTS')
    return dict(kind=kind,vendor=fx['vendor'],batch=fx['batch'],process=fx['process'],group=fx['group'],day=str(fx['day']),
        wash=wash,finish=finish,package=package,sizes=[dict(id=s,qty=n,code=b.one(cur,'select size_code from erp.sizes where id=%s',s)) for s,n in [(b.chain.base.SIZE,7),(fx['size2'],6)]])


def read(cur,f):
    ws=b.bd_ws(cur,dict(vendor_id=f['vendor']))
    return dict(deliveries=ws['priced_deliveries'],components=ws['components'],invoices=ws['invoices'],
        all_invoices=b.q(cur,'select id::text,invoice_number,status from erp.bd_laundry_invoices_v1 where vendor_id=%s order by invoice_number',f['vendor']))


def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];p=urlparse(target)
    assert p.hostname in ('127.0.0.1','localhost') and p.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        payload=json.loads(sys.argv[2])
        if sys.argv[1]=='create':
            with _fixture_usage(cur):out=create(cur,date.fromisoformat(payload['today']),payload['kind'])
            conn.commit()
        elif sys.argv[1]=='read':
            # as_owner probes its private role helper before calling the public reader.
            # Keep that fixture-only grant uncommitted; Auth/browser calls never see it.
            with _fixture_usage(cur):out=read(cur,payload)
            conn.rollback()
        else:raise ValueError('Unknown fixture operation')
    print(json.dumps(out,default=str))

if __name__=='__main__':main()
