"""Disposable existing Native history fixture and v2 observations with one explicit posted-sale control."""
from datetime import date
from urllib.parse import urlparse
import os,sys,json,hashlib
import psycopg
import cp7_model_native_cases as cases

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    op,p=sys.argv[1],json.load(sys.stdin)
    with psycopg.connect(target)as conn,conn.cursor()as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='prepare':out=cases.previous.fixture(cur,date.fromisoformat(p['today']))
        elif op=='state':
            before=cases.b.boundary.snapshot(cur)
            out=dict(business_sha256=hashlib.sha256(json.dumps(before,sort_keys=True,default=str).encode()).hexdigest(),
             policy_rows=cur.execute('select count(*)from cp7_model_policy.policies where actor=%s',(p['actor'],)).fetchone()[0],
             command_rows=cur.execute('select count(*)from cp7_model_policy.commands where actor=%s',(p['actor'],)).fetchone()[0],
             registry_rows=cur.execute('select count(*)from cp7_model_native.registry').fetchone()[0],
             v2_rows=cur.execute('select count(*)from cp7_model_registry_adapter.runs where actor=%s',(p['actor'],)).fetchone()[0],
             v2_hash=cur.execute("select md5(coalesce(jsonb_agg(to_jsonb(r)order by r.id)::text,'[]'))from cp7_model_registry_adapter.runs r where actor=%s",(p['actor'],)).fetchone()[0],
             model_rows=cur.execute('select count(*)from cp7_model_native.runs where actor=%s',(p['actor'],)).fetchone()[0])
        elif op=='post':
            cases.previous.sales.fg.post_sale(cur,p['draft']);out=dict(status='PASS',actual_posted_sale=True)
        elif op in('deactivate','restore'):
            cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
        else:raise ValueError('UNKNOWN_MODEL_V2_BROWSER_CONTROL')
        cases.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))

if __name__=='__main__':main()
