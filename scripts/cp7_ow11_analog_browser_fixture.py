"""Real Native source and test-only access/expiration controls on one clone."""
from datetime import date,timedelta
from urllib.parse import urlparse
import json,os,sys
import psycopg
import cp7_ow11_analog_reader_cases as reader
work,plan,volume=reader.bounded.work,reader.plan,reader.volume


def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser'
    op,p=sys.argv[1],json.load(sys.stdin)
    with psycopg.connect(target)as conn,conn.cursor()as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='prepare':
            today=date.fromisoformat(p['today']);x=plan.fixture(cur,today)
            size=work.dense.seed(cur)if p['dense']else None
            if p['dense']:
                plan.b.api.admin(cur)
                root,key,sku=cur.execute("select identity_root_id::text,identity_root_id::text||':'||size_id::text,sku from erp.products where sku='OW13CSV-1'").fetchone()
                imported=None
            else:
                imported=volume.import_batch(cur,today,11,volume.Phases())
                historical=reader.historical.seed(cur,imported)
                root,key=imported[0]['root'],imported[0]['target']
                plan.b.api.admin(cur);sku=cur.execute('select sku from erp.products where id=%s',(imported[0]['product'],)).fetchone()[0]
            reader.explicit_profile(cur,root)
            c=cur.execute('select cp7_reorder_inputs.capture_baseline(5000)').fetchone()[0]
            out=dict(root=root,target_key=key,sku=sku,query=plan.staged.query(today),size=size,
                     expected_targets=len(c['facts']['products']),imported_products=0 if imported is None else len(imported),
                     other_physical_targets=[]if imported is None else[r['target']for r in historical if r['target'].split(':')[1]!=key.split(':')[1]])
        elif op=='state':
            out=dict(physical=plan.monetary_state(cur),drafts=cur.execute('select count(*)from cp7_plan_native.drafts').fetchone()[0],
                     receipts=cur.execute('select count(*)from cp7_cutting_checked.receipts').fetchone()[0])
            row=cur.execute("select state,request_id::text,run_id::text,reference->>'status',reference#>>'{bounded_history_inputs,coverage}',reference#>>'{bounded_stock_reference,row_count}'from cp7_analysis_stage.jobs where actor=%s and reference->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'order by captured_at desc limit 1",(p['actor'],)).fetchone()
            out['job']=None if row is None else dict(zip(('state','request','run','raw_history_state','coverage','raw_stock_rows'),row))
        elif op=='expire':
            reader.bounded.retention.age(cur,p['run'],timedelta(days=8));out=dict(status='PASS')
        elif op in('deactivate','restore'):
            cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
        else:raise ValueError('UNKNOWN_ANALOG_BROWSER_CONTROL')
        plan.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))


if __name__=='__main__':main()
