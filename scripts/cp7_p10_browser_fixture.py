"""Disposable ordinary source commands; the browser qualifies P10 reads, not P11 writes."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_fg_cases as cases
import cp7_fg_adjustment_cases as adjustments
import cp7_fg_book_cases as book

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in ('127.0.0.1','localhost') and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    op=sys.argv[1];p=json.loads(sys.argv[2])
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        # Fixture-only native commands need schema resolution; the grant is never
        # committed or exposed to the live browser/Auth session.
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='create_book':
            f=book.fixture(cur,date.fromisoformat(p['today']));out=dict(f,facts=book.facts(cur))
            if p.get('ops'):
                role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
                cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
                for key in ('warehouse.movement.view','warehouse.stock.adjust'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,key))
        elif op=='read_book':out=dict(book=book.read(cur,p),facts=book.facts(cur),qty=cases.qty(cases.workspace(cur,p)))
        elif op=='create_adjust':
            f=cases.fixture(cur,date.fromisoformat(p['today']));g=cases.fixture(cur,date.fromisoformat(p['today']))
            out=dict(f,second=g,number='P10-UI-'+__import__('uuid').uuid4().hex[:10],accounts=[[str(x) for x in row] for row in adjustments.accounts(cur)])
            if p.get('ops'):
                role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
                cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
                for key in ('warehouse.fg.view','warehouse.stock.adjust'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)',(role,key))
        elif op=='read_adjust':
            d=cur.execute('select id::text,status,row_version::text from erp.fg_adjustments where adjustment_number=%s',(p['number'],)).fetchone()
            out=dict(qty=adjustments.qty(cur,p),second_qty=adjustments.qty(cur,p['second']),document=dict(id=d[0],status=d[1],version=d[2]) if d else None,accounts=[[str(x) for x in row] for row in adjustments.accounts(cur)])
        elif op=='create':
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
