"""Actual isolated payroll/source/accounting facts for E05 browser assertions."""
from datetime import date
from decimal import Decimal as D
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_installment_cases as cases


def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    op,p=sys.argv[1],json.load(sys.stdin)
    with psycopg.connect(target)as conn,conn.cursor()as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='prepare':out=cases.fixture(cur,date.fromisoformat(p['today']))
        elif op=='state':
            f=p['fixture'];r=cases.read(cur,f['payroll']);d=r['document'];paid=D(d['paid_amount'])
            assert D(d['approved_net'])==D('1000.00')
            assert cases.physical.stock_cost(cur)==f['physical']
            assert cases.legacy.journal(cur,f['payroll'],'PAYROLL_ATTENDANCE_ACCRUAL')==(2,D(1000),D(1000))
            expected={}if paid==0 else{cases.legacy.acct(cur,'CONTRACTOR_PAYABLE'):paid,f['cash']['account_id']:-paid}
            assert cases.delta(cur,f)==expected,(cases.delta(cur,f),expected)
            requests=cur.execute("select request_id,action,payload,response from cp7_installment.requests where payload->>'payroll_id'=%s order by request_id",(f['payroll'],)).fetchall()
            out=dict(document=d,payments=r['payments'],approved_cost1000_once=True,stock_HPP_unchanged=True,GL_cash_equals_active_native_payments=True,
                     requests=[dict(request_id=str(i),action=a,payload=pl,response=re)for i,a,pl,re in requests])
        elif op in('revoke','restore'):
            role=cur.execute("select id from erp.app_roles where role_code='ADMIN'").fetchone()[0]
            if op=='revoke':cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.payroll.pay'",(role,))
            else:cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.payroll.pay')on conflict do nothing",(role,))
            out=dict(status='PASS',current_ADMIN_pay_permission=op=='restore')
        else:raise ValueError('Unknown E05 browser fixture operation')
        cases.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))


if __name__=='__main__':main()
