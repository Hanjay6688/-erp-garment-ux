"""Actual minute pg_cron on the disposable current installation, no page ticks.

This exercises the existing production command and its sixty bounded transactions.
No clock, schedule frequency, stored actor or job progress is altered by the test.
"""
from pathlib import Path
from time import monotonic, sleep
from urllib.parse import urlparse, urlunparse
import importlib.util
import json
import uuid
import psycopg
import cp7_schedule as schedule
import cp7_k4_runner_cases as k4
import cp7_current_frozen_finance_installation as product

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('current_cron_finance_cases',ROOT/'scripts/current-frozen-finance-native-qualification/finance_cases.py')
finance=importlib.util.module_from_spec(spec);spec.loader.exec_module(finance)
CASE='CURRENT_FROZEN_PRIVATE_FACTORY_1200X3_ACTUAL_MINUTE_OFFICIAL_FINANCE'
_spec=importlib.util.spec_from_file_location('factory1200x3_fixture',Path(__file__).with_name('fixture.py'))
factory=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(factory)
_diag_spec=importlib.util.spec_from_file_location('factory_terminal_diagnostics',Path(__file__).with_name('diagnostics.py'))
diagnostics=importlib.util.module_from_spec(_diag_spec);_diag_spec.loader.exec_module(diagnostics)


def erp_data(cur):
    return {k:v for k,v in product.catalog._data(cur).items()
        if k.startswith(('erp.','sequence:erp.'))}


def quiet(cur,database):
    deadline=monotonic()+60
    while monotonic()<deadline:
        cur.execute('select pg_stat_clear_snapshot()')
        if not cur.execute("select count(*)from pg_stat_activity where datname=%s and application_name='pg_cron'",(database,)).fetchone()[0]:
            return
        sleep(.5)
    raise AssertionError('CURRENT_CRON_SESSION_LEFT')


def scheduler_quiet(admin_url):
    u=urlparse(admin_url)
    assert u.hostname in('localhost','127.0.0.1')and u.port==54322 and u.path=='/cp6_rollback'
    with psycopg.connect(urlunparse(u._replace(path='/postgres')),autocommit=True)as conn,conn.cursor()as cur:
        assert schedule.installed(cur,'cp6_rollback')==[],'CURRENT_CRON_SCHEDULE_STILL_ACTIVE'
        quiet(cur,'cp6_rollback')
    return True


def exercise(conn,cur,database_module,admin_url,report):
    target='cp6_rollback';u=urlparse(admin_url)
    assert u.hostname in('localhost','127.0.0.1')and u.port==54322 and u.path=='/'+target
    assert cur.execute('select current_database()').fetchone()==(target,)
    granted,_=database_module._foundation(cur)
    today=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
    # All posting precedes both captures; no browser or Auth credit.
    finance.setup(cur,today)
    factory_fixture=report.setdefault('factory_fixture',{})
    factory.seed(conn,cur,today,factory_fixture)
    finance_key=str(uuid.uuid4());bounded_key=str(uuid.uuid4())
    first=finance.request(cur,today,finance_key)
    sidecar=finance.sidecar(first,finance_key,'RUNNING')
    capture=sidecar['capture']['capture_id']
    second=finance.request(cur,today,bounded_key,None)
    assert 'finance_capture'not in second
    assert first['units_done']==second['units_done']==0 and second['state']=='RUNNING'
    assert sidecar['capture']['units_done']==0
    finance.staged.b.api.admin(cur)
    defs=[d for d in schedule.definitions(cur)if d['name']==k4.RUNNER['name']]
    assert defs==[k4.RUNNER],('CURRENT_CRON_DEFINITION_CHANGED',defs)
    schedule.same_database(cur,target)
    if granted:cur.execute('revoke usage on schema erp from authenticated')
    conn.commit()
    before=erp_data(cur);before_catalog=product.catalog._catalog_rows(cur);conn.rollback()
    report.update(case_id=CASE,status='INCOMPLETE',definition=defs[0],test_schedule_override=None,
        page_or_test_ticks=0,real_Auth_browser_claim=False,finance_request=finance_key,bounded_request=bounded_key,
        finance_capture_id=capture,production_go=False)
    ids={};cron_url=urlunparse(u._replace(path='/postgres'))
    with psycopg.connect(cron_url,autocommit=True)as cron,cron.cursor()as cc:
        assert schedule.installed(cc,target)==[],'CURRENT_CRON_DISPOSABLE_TARGET_ALREADY_SCHEDULED'
        unrelated=cc.execute('select jobid,to_jsonb(j)from cron.job j order by jobid').fetchall()
        version=cc.execute("select extversion from pg_extension where extname='pg_cron'").fetchone()
        assert version,'CURRENT_CRON_EXTENSION_REQUIRED'
        report['pg_cron']=version[0]
        since=cc.execute('select now()').fetchone()[0]
        try:
            ids=schedule.install(cc,target,'postgres',defs)
            assert schedule.matches(cc,target,'postgres',defs)[0]
            # Re-admitting the same schedule must retain the same job identity.
            assert schedule.install(cc,target,'postgres',defs)==ids
            report['schedule_ids']=ids
            started=monotonic();deadline=started+300;states=None
            with psycopg.connect(admin_url,autocommit=True)as watch,watch.cursor()as wc:
                while monotonic()<deadline:
                    states=wc.execute("select request_id::text,state from cp7_analysis_stage.jobs where request_id=any(%s::uuid[])order by request_id",([finance_key,bounded_key],)).fetchall()
                    financial=wc.execute('select state from cp7_finance_capture.captures where id=%s',(capture,)).fetchone()[0]
                    assert len(states)==2
                    if all(x[1]!='RUNNING'for x in states)and financial!='RUNNING':break
                    sleep(2)
            report.update(observed_job_states=dict(states or []),observed_finance_state=financial,
                elapsed_seconds=round(monotonic()-started,3))
            assert states and all(x[1]=='DONE'for x in states)and financial=='READY',report
        finally:
            # Only this database's explicitly empty-before schedule was added.
            removed=schedule.uninstall(cc,target);quiet(cc,target)
            if ids:
                recorded=schedule.wait_recorded(cc,ids.values())
                runs=schedule.runs(cc,ids[k4.RUNNER['name']],since)
                report.update(cron_runs=runs,all_runs_recorded=recorded,removed=removed)
                cc.execute('delete from cron.job_run_details where jobid=any(%s)',(list(ids.values()),))
            assert schedule.installed(cc,target)==[]
            assert cc.execute('select jobid,to_jsonb(j)from cron.job j order by jobid').fetchall()==unrelated
            report['schedules_removed_and_unrelated_jobs_unchanged']=True
            report['terminal_diagnostics']=diagnostics.capture(admin_url,[finance_key,bounded_key],capture)
    assert report['all_runs_recorded']and report['cron_runs']
    assert all(r['status']=='succeeded'and r['end']is not None for r in report['cron_runs']),report['cron_runs']
    assert erp_data(cur)==before and product.catalog._catalog_rows(cur)==before_catalog
    current=finance.staged.status(cur,finance_key)
    result=finance.sidecar(current,finance_key,'READY')['result']
    source=finance.finance.call(cur,'select cp7_finance_capture.result(%s)',(capture,))
    official=finance.finance.official(cur,source['dates'])
    assert all(source['report']['snapshot'][p]==official['snapshot'][p]
        for p in('performance','financial_position','basis','data_confidence'))
    wanted,readiness=finance.finance.metrics(cur,source)
    assert {m['metric_id']:m['value']for m in result['metrics']}==wanted
    assert result['readiness']==readiness
    unknown=[k for k,v in wanted.items()if v['state']=='UNKNOWN']
    assert all('value'not in wanted[k]for k in unknown)
    signature,counts=finance.finance.independent_signature(cur,source['dates']['as_of'])
    assert signature==source['book_signature']
    assert counts=={family:source['capture']['plan'][family]['rows']for family in finance.finance.FAMILIES}
    assert len(wanted)==24
    assert result['capture_id']==capture and result['source_hash']==source['source_hash']
    assert result['dates']==source['dates']
    assert all(source['source_hash']in json.dumps(value['refs'])for value in wanted.values())
    finance.staged.b.api.admin(cur)
    assert cur.execute('select count(*)from cp7_finance_capture.captures').fetchone()[0]==1
    pages={}
    for key in(finance_key,bounded_key):
        job=finance.staged.status(cur,key)
        assert job['state']=='DONE'and job['server_runner']['active']is True
        original,paged,meta=finance.staged.fetch(cur,job['run_id'])
        coverage=factory.coverage(original,paged,factory_fixture)
        assert original['financial_source']is None
        pages[key]=dict(run_id=job['run_id'],page_meta=meta,identity_hash=paged['identity_hash'],factory_coverage=coverage,
            units=k4.units_once(cur,key))
    held=product.catalog._data(cur)
    assert finance.request(cur,today,finance_key)['run_id']==current['run_id']
    assert finance.request(cur,today,bounded_key,None)['run_id']==pages[bounded_key]['run_id']
    assert product.catalog._data(cur)==held
    assert erp_data(cur)==before
    conn.rollback()
    report.update(status='PASS',same_UUID_no_second_effect=True,official_sections_and_metrics_exact=True,
        independent_book_signature=True,metric_count=len(wanted),readiness=readiness,
        unknown_metric_ids=unknown,unknown_never_zero=True,server_runner_active=True,
        pages=pages,all22_catalog_exact=True,Native_money_stock_HPP_unchanged=True,full_current_finance_model_installation=True,
        explicit_private_STAGED_and_operational_DEFERRED=True,all_capture_family_counts_exact=True,
        unchanged_production_minute_schedule=True,manual_finance_or_operational_steps=0,
        exact_1200_commercial_skus_three_sizes=True,factory_native_finance_qualified=True)
