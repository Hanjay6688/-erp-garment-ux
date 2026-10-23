"""Native initial-analysis browser helpers, isolated browser copy only."""
from datetime import date
from urllib.parse import urlparse
import contextlib
import hashlib
import json
import os
import sys
import psycopg
import cp7_ow13a_initial_cases as case


def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    operation,p=sys.argv[1],json.load(sys.stdin)
    with psycopg.connect(target)as conn,conn.cursor()as cur:
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        case.b.api.admin(cur)
        if operation=='prepare':
            with contextlib.redirect_stdout(sys.stderr):
                f,subject,payload=case.prepare(cur,date.fromisoformat(p['today']),subject=p['actor'],configured=False)
            out=dict(product=f['product'],subject=subject)
        elif operation=='state':
            row=cur.execute('select i.request_id::text,j.state,j.units_done,j.unit_count from cp7_initial_analysis.intents i '
                'join cp7_analysis_stage.jobs j on j.id=i.job_id where i.actor=%s',(p['actor'],)).fetchone()
            snapshot=case.retained.formula.business(cur)
            out=dict(native_hash=hashlib.sha256(json.dumps(snapshot,sort_keys=True,default=str).encode()).hexdigest(),
                own_intents=cur.execute('select count(*)from cp7_initial_analysis.intents where actor=%s',(p['actor'],)).fetchone()[0],
                job=dict(zip(('request_id','state','units_done','unit_count'),row))if row else None)
        elif operation=='worker':
            # Existing private K4 worker, actual Native source and job. The
            # app page is closed by Playwright; no client step is sent.
            cur.execute("set local statement_timeout='8s';set local role cp7_capture")
            out=cur.execute('select cp7_analysis_stage.run_next()').fetchone()[0]
            cur.execute('reset role');case.b.api.admin(cur)
        elif operation in('deactivate','restore'):
            cur.execute('update erp.app_users set is_active=%s where auth_user_id=%s',(operation=='restore',p['actor']))
            out=dict(status='PASS')
        else:raise ValueError('UNKNOWN_OW13A_BROWSER_OPERATION')
        case.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))


if __name__=='__main__':main()
