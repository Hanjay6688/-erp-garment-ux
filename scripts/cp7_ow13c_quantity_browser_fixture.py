"""Actual Native fixture/observations only; no fabricated reference or result."""
from datetime import date
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_ow13c_schedule_cases as work


def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('localhost','127.0.0.1') and url.path=='/cp6_auditor_browser'
    op,p=sys.argv[1],json.load(sys.stdin)
    with psycopg.connect(target)as conn,conn.cursor()as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='prepare':
            x=work.plan.fixture(cur,date.fromisoformat(p['today']))
            config=cur.execute('select config from cp7_schedule_native.plans order by revision desc limit 1').fetchone()[0]
            size=work.dense.seed(cur)if p.get('dense')else None
            c=cur.execute('select cp7_reorder_inputs.capture_baseline(5000)').fetchone()[0]
            out=dict(root=x['root'],target_key=x['target'],query=work.plan.staged.query(date.fromisoformat(p['today'])),config=config,
                     po_id=x['po'],location_id=str(x['fabric']['location']),material_id=str(x['fabric']['material']),
                     expected_targets=len(c['facts']['products']),raw_history_state=c['status'],size=size)
        elif op=='state':
            out=dict(drafts=cur.execute('select count(*)from cp7_plan_native.drafts where actor=%s',(p['actor'],)).fetchone()[0],
                     receipts=cur.execute('select count(*)from cp7_cutting_checked.receipts where actor=%s',(p['actor'],)).fetchone()[0],
                     intents=cur.execute('select count(*)from cp7_plan_native.intents').fetchone()[0],physical=work.plan.monetary_state(cur))
            row=cur.execute("select state,request_id::text,run_id::text,reference->>'status',reference#>>'{bounded_history_inputs,coverage}',reference#>>'{bounded_stock_reference,row_count}' "
                "from cp7_analysis_stage.jobs where actor=%s and reference->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'order by captured_at desc limit 1",(p['actor'],)).fetchone()
            out['job']=None if row is None else dict(zip(('state','request','run','raw_history_state','coverage','raw_stock_rows'),row))
        elif op=='stock':
            work.plan.found_fg(cur,dict(root=p['root']),'1');out=dict(actual_Native_stock_writer=True)
        elif op in('deactivate','restore'):
            cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
        else:raise ValueError('UNKNOWN_BOUNDED_QUANTITY_CONTROL')
        work.plan.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))


if __name__=='__main__':main()
