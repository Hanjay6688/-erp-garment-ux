"""Disposable native misc source/ledger assertions; stdin never truncates bodies."""
from datetime import date
from decimal import Decimal as D
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_misc_cases as cases
def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    op,p=sys.argv[1],json.load(sys.stdin)
    with psycopg.connect(target)as conn,conn.cursor()as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0];acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='prepare':out=cases.fixture(cur,date.fromisoformat(p['today']))
        elif op in('read','verify'):
            native=cases.read(cur,p['query'])
            if op=='verify':cases.compare(p['report'],native);out=dict(status='PASS',complete_misc_native_source=True)
            else:out=dict(report=native)
        elif op=='state':
            f=p['fixture'];ident=p['transaction_id'];doc=cases.native_document(cur,ident);assert doc is not None
            assert cases.stock_cost(cur)==f['stock_cost'],'MISC_PHYSICAL_OR_HPP_EFFECT'
            cash_delta=(cases.cash_balance(cur,f['cash']['id'])-D(f['cash_before'])).quantize(D('.01'))
            records=cur.execute("select action,request_id,payload,response from cp7_misc.requests where response->>'transaction_id'=%s order by action,request_id",(ident,)).fetchall()
            out=dict(document=doc,cash_delta=str(cash_delta),stock_HPP_unchanged=True,requests=[dict(action=a,request_id=str(i),payload=p,response=r)for a,i,p,r in records])
        elif op=='revoke':
            role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0];cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.cash.view'",(role,));out=dict(status='PASS',current_ADMIN_cash_view_revoked=True)
        else:raise ValueError('Unknown misc fixture operation')
        cases.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
