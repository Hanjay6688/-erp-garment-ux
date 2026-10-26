"""Paired, rollback-only single-snapshot-check experiment; no product adoption."""
from pathlib import Path
from time import monotonic
from hashlib import sha256
from urllib.parse import urlparse
import importlib.util,json,os,platform
import psycopg

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
profile=load('unchanged_profile_dependencies',ROOT/'scripts/current-frozen-finance-stage-profile/runner.py')
reader=load('single_snapshot_check_experiment',HERE/'reuse.py')
price_fixture=load('real_price_percent_opening_fixture',HERE/'price_fixture.py')
finance,product=profile.finance,profile.product
scheduler_quiet=profile.scheduler_quiet
CASE='FINANCE_SINGLE_SNAPSHOT_CHECK_SMALL_PRICE_PERCENT_FACTORY_DIAGNOSTIC'

def table_writes(cur):
    return {r[0]:list(r[1:])for r in cur.execute("select schemaname||'.'||relname,n_tup_ins,n_tup_upd,n_tup_del from pg_stat_xact_user_tables order by 1").fetchall()}

def writes_delta(before,after):
    return {k:diff for k,v in after.items()if any(diff:=[v[i]-before.get(k,[0,0,0])[i]for i in range(3)])}

def measure(admin_url,dates,candidate,limit):
    u=urlparse(admin_url);assert u.hostname in('localhost','127.0.0.1')and u.port==54322 and u.path=='/cp6_rollback'
    out=dict(candidate=candidate,status='INCOMPLETE',diagnostic_only=True,statement_limit_ms=limit,retries=0)
    with psycopg.connect(admin_url)as conn,conn.cursor()as cur:
        try:
            cur.execute("set local track_functions='all'");cur.execute("set local lock_timeout='2s'")
            cur.execute("select set_config('statement_timeout',%s,true)",(str(limit),))
            before_catalog=product.catalog._catalog_rows(cur);before_data=product.catalog._data(cur)
            if candidate:out['temporary_patch']=reader.install_for_rollback(cur)
            writes_before=table_writes(cur)
            with finance.finance.as_capture(cur):
                counters_before=profile.functions(cur);started=monotonic()
                value=cur.execute('select cp7_finance_capture.report_unit(%s::jsonb)',(json.dumps(dates),)).fetchone()[0]
                out['elapsed_ms']=round((monotonic()-started)*1000,3)
                out['functions']=profile.difference(counters_before,profile.functions(cur))
            out['table_write_attempts']=writes_delta(writes_before,table_writes(cur))
            out['all_data_and_sequences_unchanged_before_rollback']=product.catalog._data(cur)==before_data
            if candidate:
                assert out['table_write_attempts']=={},('READER_STILL_WRITES',out['table_write_attempts'])
                assert out['all_data_and_sequences_unchanged_before_rollback'],'READER_CHANGED_STORED_DATA'
            report=dict(value['report']);stamp=report.pop('captured_at')
            assert stamp and 'snapshot'in report
            raw=json.dumps(report,sort_keys=True,default=str).encode()
            out.update(status='COMPLETED_DIAGNOSTIC',report_bytes=len(raw),report_sha256=sha256(raw).hexdigest(),
                excluded_comparison_fields=['report.captured_at'],rows=value['rows'],server_report_ms=value['server_ms'])
        finally:
            conn.rollback()
        assert product.catalog._catalog_rows(cur)==before_catalog
        assert product.catalog._data(cur)==before_data
        conn.rollback()
    out['all22_all_data_and_sequences_restored']=True
    return out,report

def pair(admin_url,dates,name,limit,report):
    evidence=report.setdefault('pairs',{}).setdefault(name,dict(status='INCOMPLETE'))
    print(json.dumps(dict(stage=name,variant='UNCHANGED_OFFICIAL',state='RUNNING')),flush=True)
    old,left=measure(admin_url,dates,False,limit);evidence['unchanged_official']=old
    print(json.dumps(dict(stage=name,variant='SINGLE_SNAPSHOT_CHECK_CANDIDATE',state='RUNNING')),flush=True)
    new,right=measure(admin_url,dates,True,limit);evidence['single_snapshot_check_candidate']=new
    assert left==right,('WHOLE_OFFICIAL_REPORT_CHANGED',name)
    assert old['rows']==new['rows'],'SOURCE_ROW_COUNTS_CHANGED'
    old_calls={row['function']:row['calls']for row in old['functions']}
    new_calls={row['function']:row['calls']for row in new['functions']}
    assert old_calls['erp.run_v268_financial_report_checks()']==3
    assert new_calls['erp.run_v268_financial_report_checks()']==2
    assert new_calls.get('erp.resolve_opening_fg_unit_hpp(uuid,date)',0)==0
    assert new['table_write_attempts']=={}
    evidence.update(official_check_calls_before=3,official_check_calls_after=2,
        no_result_cache=True,caller_supplied_check_results=False)
    # Only elapsed server timestamps are omitted. All checks, confidence,
    # warnings, money/HPP, filings and unknown/null fields must match exactly.
    evidence.update(status='PASS',entire_official_report_equal=True,
        elapsed_change_ms=round(new['elapsed_ms']-old['elapsed_ms'],3),
        product_performance_qualification=False,full_factory_completion=False)

def exercise(conn,cur,database_module,admin_url,report):
    assert conn.info.host in('localhost','127.0.0.1')and cur.execute('select current_database()').fetchone()==('cp6_rollback',)
    report['runtime_environment']=dict(cpu_count=os.cpu_count(),machine=platform.machine(),
        kernel=platform.release(),postgres=cur.execute('select version()').fetchone()[0],
        postgres_settings=dict(cur.execute("select name,setting from pg_settings where name in('server_version_num','work_mem','shared_buffers','jit','max_parallel_workers_per_gather')order by name").fetchall()))
    cpu=Path('/proc/cpuinfo')
    if cpu.is_file():report['runtime_environment']['cpu_model']=next((line.split(':',1)[1].strip()for line in cpu.read_text().splitlines()if line.startswith('model name')),None)
    granted,_=database_module._foundation(cur)
    today=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
    finance.setup(cur,today)
    finance.staged.b.api.admin(cur)
    dates={k:str(today)for k in('from','to','as_of')}
    if granted:cur.execute('revoke usage on schema erp from authenticated')
    conn.commit()
    report.update(case_id=CASE,diagnostic_only=True,actual_cron_claim=False,manual_committed_steps=0,
        product_timeout_changed=False,production_go=False,previous_factory_failures_remain_INCOMPLETE=True)
    pair(admin_url,dates,'SMALL',8000,report)
    granted,_=database_module._foundation(cur)
    report['price_percent_fixture']=price_fixture.seed(cur,today)
    finance.staged.b.api.admin(cur)
    if granted:cur.execute('revoke usage on schema erp from authenticated')
    conn.commit()
    pair(admin_url,dates,'PRICE_PERCENT',8000,report)
    granted,_=database_module._foundation(cur)
    profile.retained.factory.seed(conn,cur,today,report.setdefault('factory_fixture',{}))
    finance.staged.b.api.admin(cur)
    if granted:cur.execute('revoke usage on schema erp from authenticated')
    conn.commit()
    pair(admin_url,dates,'FACTORY_1200X3',30000,report)
    old=report['pairs']['FACTORY_1200X3']['unchanged_official']
    assert old['table_write_attempts'].get('erp.opening_balance_items',[0,0,0])[1]>=3600,'OLD_OPENING_WRITE_NOT_OBSERVED'
    report.update(status='PASS',diagnostic_collection_completed=True,
        all22_all_rows_and_sequences_unchanged_by_measurements=True,
        factory_native_finance_qualified=False,performance_qualification=False,
        price_percent_branch_qualification=True,source_change_race_qualification=False,
        report_check_reuse_implemented=False,temporary_snapshot_check_reuse_diagnostic=True,product_adoption=False)
