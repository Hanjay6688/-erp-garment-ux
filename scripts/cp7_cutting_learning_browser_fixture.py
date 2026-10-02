"""Disposable Native cohorts and read-only observations for ordinary F04 UI."""
from datetime import date
from urllib.parse import urlparse
import contextlib,hashlib,json,os,sys
import psycopg
import cp7_cutting_model_cases as model


def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in ('localhost','127.0.0.1') and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    op,p=sys.argv[1],json.load(sys.stdin)
    with psycopg.connect(target) as conn,conn.cursor() as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        model.b.api.admin(cur)
        if op=='prepare':
            with contextlib.redirect_stdout(sys.stderr):
                if p['cohort']:
                    f,policy,groups=model.cohort(cur,date.fromisoformat(p['today']),p['actor'])
                else:
                    f=model.draft(cur,date.fromisoformat(p['today']),None,60,p['actor'])
                    policy=None;groups=[]
            out=dict(f,cohort_policy_id=policy['id'] if policy else None,cohort_groups=[g['group'] for g in groups])
        elif op=='post':
            model.inputs.change_native_draft(cur,p['fixture'],post=True,prospective=True);out=dict(status='PASS')
        elif op=='state':
            f=p['fixture'];snapshot=model.b.boundary.snapshot(cur)
            out=dict(native_hash=hashlib.sha256(json.dumps(snapshot,sort_keys=True,default=str).encode()).hexdigest(),
                group=cur.execute('select to_jsonb(g)from erp.cutting_groups g where id=%s',(f['group'],)).fetchone()[0],
                policies=cur.execute('select count(*)from cp7_cutting_model.policies where actor=%s',(p['actor'],)).fetchone()[0],
                model_requests=cur.execute('select count(*)from cp7_cutting_model.requests where actor=%s',(p['actor'],)).fetchone()[0],
                observations=cur.execute('select count(*)from cp7_cutting_observations.runs where actor=%s and group_id=%s',(p['actor'],f['group'])).fetchone()[0],
                observation_requests=cur.execute('select count(*)from cp7_cutting_observations.requests where actor=%s and payload->>\'group_id\'=%s',(p['actor'],f['group'])).fetchone()[0])
        elif op in ('deactivate','restore'):
            cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(op=='restore',p['actor']));out=dict(status='PASS')
        else:raise ValueError('UNKNOWN_LEARNING_BROWSER_OPERATION')
        model.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))


if __name__=='__main__':main()
