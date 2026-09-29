"""Disposable ordinary source commands; the browser qualifies P10 reads, not P11 writes."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_fg_cases as cases

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in ('127.0.0.1','localhost') and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    op=sys.argv[1];p=json.loads(sys.argv[2])
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        # Fixture-only native commands need schema resolution; the grant is never
        # committed or exposed to the live browser/Auth session.
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='create':
            f=cases.fixture(cur,date.fromisoformat(p['today']));d=cases.draft(cur,f);out=dict(f,sale=d)
            if p.get('ops'):
                cases.b.api.admin(cur);role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
                cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
                for key in ('warehouse.fg.view','warehouse.stock.view'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,key))
        elif op=='cancel':cases.cancel(cur,p['sale']);out=dict(ok=True)
        elif op=='post':d=cases.draft(cur,p);cases.post_sale(cur,d);out=dict(ok=True)
        elif op=='read':
            out=dict(qty=cases.qty(cases.workspace(cur,p)),movements=cur.execute('select count(*) from erp.fg_stock_movements where lot_id=%s',(p['lot'],)).fetchone()[0])
        else:raise ValueError('Unknown fixture operation')
        cases.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]==had
        conn.commit()
    print(json.dumps(out,default=str))

if __name__=='__main__':main()
