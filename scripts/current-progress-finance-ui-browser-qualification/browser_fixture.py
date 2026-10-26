"""Loopback-only fixture and independent readback; no browser job is fabricated."""
from pathlib import Path
from urllib.parse import urlparse
from datetime import date
import importlib.util,json,os,sys,uuid
import psycopg
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('A_public_finance_UI_helpers',ROOT/'scripts/current-frozen-public-finance-qualification/cases.py')
helpers=importlib.util.module_from_spec(spec)
# Retained qualification modules validate their own CLI at import time.
# Keep this fixture's operation private to main while loading those modules.
_fixture_argv=sys.argv[:]
try:
    sys.argv=sys.argv[:1]
    spec.loader.exec_module(helpers)
finally:
    sys.argv=_fixture_argv
native,staged,plan=helpers.native,helpers.staged,helpers.plan

def prepare_ready_sources(cur,today):
    """Complete labelled seed obligations in this disposable clone via retained writers.

    The first baseline was correctly BLOCKED. Never alter report output, pool
    policy, posted sources or readiness rules to manufacture a positive case.
    """
    dates={'from':str(today),'to':str(today),'as_of':str(today)}
    before=native.finance.official(cur,dates)['snapshot']['data_confidence']
    pools=helpers.chain.prepare_attendance_pools(cur,today)
    staged.b.api.admin(cur)
    start=cur.execute('select erp.period_completeness_from_v1()').fetchone()[0]
    assert start is not None and start<=today
    attendance=helpers.chain.period.aw.quiet_seed(cur,start,today)
    assert not attendance['refused'],('POSITIVE_FIXTURE_SOURCE_COMPLETION_REFUSED',attendance)
    after=native.finance.official(cur,dates)['snapshot']['data_confidence']
    assert after['status']=='READY',('BASELINE_OFFICIAL_REPORT_NOT_READY',after)
    return dict(fixture_only=True,path='retained Native period, attendance, payroll and HPP pool writers',
                before=before,pools=pools,attendance=attendance,after=after,
                readiness_rules_unchanged=True,report_output_not_fabricated=True)

def state(cur,actor):
    staged.b.api.admin(cur)
    jobs=cur.execute('select request_id::text,id::text,run_id::text,state,reference from cp7_analysis_stage.jobs where actor=%s order by captured_at,request_id',(actor,)).fetchall()
    captures=cur.execute('select to_jsonb(c) from cp7_finance_capture.captures c where c.owner_id in(select id from cp7_analysis_stage.jobs where actor=%s) order by c.id',(actor,)).fetchall()
    return dict(jobs=[dict(zip(('request','id','run','state','reference'),r)) for r in jobs],captures=[r[0] for r in captures],physical=plan.monetary_state(cur),counts=helpers.counts(cur))

def main():
    url=os.environ['AUDITOR_BROWSER_DB_URL'];u=urlparse(url)
    assert u.hostname in('localhost','127.0.0.1') and u.path=='/cp6_auditor_browser'
    op=sys.argv[1];p=json.load(sys.stdin);actor=str(uuid.UUID(p['actor']))
    with psycopg.connect(url) as conn,conn.cursor() as cur:
        cur.execute("set local statement_timeout='8s'")
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        if op=='prepare':
            today=date.fromisoformat(p['today'])
            assert p['scenario'] in ('READY_BASELINE','BLOCKED_POSTED_FIXTURE')
            if p['scenario']=='BLOCKED_POSTED_FIXTURE':native.setup(cur,today)
            source_preparation=None
            # The clone contains deliberately unfinished historical seed sources.
            # Complete them through the retained Native fixture before capturing
            # the no-analysis-write baseline. The mobile fixture stays BLOCKED.
            if p['scenario']=='READY_BASELINE':
                source_preparation=prepare_ready_sources(cur,today)
            before=state(cur,actor);assert before['jobs']==[] and before['captures']==[]
            out=dict(query=staged.query(today),before=before,browser_job_created=False,scenario=p['scenario'],source_preparation=source_preparation)
        elif op=='state':out=state(cur,actor)
        elif op=='read':
            key=str(uuid.UUID(p['request']));job=staged.status(cur,key,actor);assert job['state']=='DONE'
            row=staged.job_row(cur,key,actor);original,pages,metadata=staged.fetch(cur,job['run_id'],actor)
            assert original['financial_source'] is None
            assert pages['request_id']==key and original['analysis']['scope']['actor_scope_id']==actor
            out=dict(job=job,full_reference=row['reference'],original=original,page_set=pages,page_metadata=metadata)
        elif op=='complete_finance':
            key=str(uuid.UUID(p['request']));job=staged.status(cur,key,actor)
            assert job['state']=='DONE' and job['finance_capture']['state']=='RUNNING'
            ready,capture=helpers.ready(cur,key,actor)
            out=dict(job=ready,capture=capture,official_sections_and_24_metrics_equal=True,
                     independent_book_signature=True,UNKNOWN_never_zero=True,
                     private_SQL_advancement_only=True,actual_cron_claim=False)
        elif op=='withdraw_finance':
            staged.b.api.admin(cur)
            role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(actor,)).fetchone()[0]
            row=cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.reports.view' returning to_jsonb(app_role_permissions)",(role,)).fetchone()
            assert row is not None and cur.rowcount==1
            out=dict(permission=row[0],role_id=str(role))
        elif op=='restore_finance':
            staged.b.api.admin(cur);row=p['permission']
            assert row['permission_key']=='finance.reports.view'
            role=cur.execute('select role_id::text from erp.app_users where auth_user_id=%s',(actor,)).fetchone()[0]
            assert str(row['role_id'])==role
            cur.execute('insert into erp.app_role_permissions select(jsonb_populate_record(null::erp.app_role_permissions,%s::jsonb)).*',(json.dumps(row),))
            assert cur.rowcount==1;out=dict(status='RESTORED')
        else:raise ValueError('UNKNOWN_A_FINANCE_BROWSER_FIXTURE_OPERATION')
        staged.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))

if __name__=='__main__':main()
