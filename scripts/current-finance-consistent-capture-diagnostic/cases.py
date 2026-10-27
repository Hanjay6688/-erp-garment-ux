"""Prepared qualification operations; enclosing full-database restore is mandatory."""
from pathlib import Path
from datetime import date
from time import monotonic
import importlib.util,json,sys
import psycopg

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


patch=load('report_book_prepared_patch',HERE/'patch.py')
reference=load('report_book_independent_reference',HERE/'signature_reference.py')
visibility=load('unchanged_child_visibility_oracle',ROOT/'scripts/current-finance-source-visibility-diagnostic/runner.py')
cron=load('unchanged_actual_minute_cron',ROOT/'scripts/current-choice-finance-cron-qualification/runner.py')
single=load('retained_finance_report_measurement',ROOT/'scripts/current-finance-single-check-diagnostic/runner.py')
business=load('unchanged_readonly_Native13',ROOT/'scripts/current-finance-readonly-integration-qualification/cases.py')
import cp7_p21_current_chain_rehearsal_probe as chain
from cp7_finance_capture import cases as capture
from cp7_catalog_state import exact_public_catalog
product=single.product
control=chain.helper.control


def install(conn,cur,report):
    detail=patch.install_for_rollback(cur,product.catalog)
    # Complete original catalog/data are already kept by the outer dump and
    # assertions. Keep only the small candidate metadata in the case receipt.
    report['temporary_candidate']={k:v for k,v in detail.items()if k not in ('original_catalog','original_data')}
    conn.commit()


def independent(conn,cur,database,url,report):
    install(conn,cur,report)
    granted,_=database._foundation(cur)
    today=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
    single.finance.setup(cur,today);capture.b.api.admin(cur)
    if granted:cur.execute('revoke usage on schema erp from authenticated')
    conn.commit()
    observations=[]
    for as_of,size,label in ((date.min,10000,'EMPTY_DATED_FAMILIES'),(today,1,'MULTICHUNK_REFERENCE_ONLY'),(today,10000,'UNCHANGED_PRODUCTION_CHUNK_POLICY')):
        expected=reference.signature(cur,as_of,size)
        observed=cur.execute('select cp7_finance_capture.report_book_diagnostic_v1(%s,%s)',(as_of,size)).fetchone()[0]
        assert observed=={k:expected[k]for k in ('rows','signature')}
        if label=='EMPTY_DATED_FAMILIES':assert all(expected['rows'][f]==0 for f in ('journal','line','book'))
        if size==1:assert expected['chunks']>4
        observations.append(dict(label=label,as_of=str(as_of),helper_chunk_size=size,**expected))
    official_signature,official_counts=capture.independent_signature(cur,today)
    assert observations[-1]['signature']==official_signature and observations[-1]['rows']==official_counts
    assert cur.execute('select cp7_finance_capture.chunk_rows()').fetchone()==(10000,)
    conn.rollback()
    report.update(status='PASS',direct_table_reference_exact=True,original_reference_exact=True,
        production_chunk_policy_unchanged=True,observations=observations)


def child_visibility(conn,cur,database,url,report):
    install(conn,cur,report)
    visibility.exercise(conn,cur,database,url,report)
    assert report['changed_source_refused_before_seal'] is True


def native20(conn,cur,database,url,report):
    install(conn,cur,report)
    expected=product.catalog._catalog_rows(cur);conn.rollback()
    ids=(*business.IDS,*capture.IDS);assert len(ids)==len(set(ids))==20
    def cases(c,today):return business.cases(c,today)+capture.cases(c,today)
    def verify(c):
        with control.product_catalog(c):
            assert product.catalog._catalog_rows(c)==expected,'CONSISTENT_CAPTURE_CATALOG_CHANGED'
    previous=control.STATE
    try:
        control.STATE=dict(installed_catalog=expected)
        with exact_public_catalog(control.native,retain_raw=True)as public:
            result=control.native.strict_group('D17_CONSISTENT_CAPTURE_UNCHANGED_NATIVE20',cases,verify)
        report.update(native=result,native_public_catalog_comparison=public)
        assert result['status']=='PASS' and result['counts']=={'PASS':20}
        assert result['complete_boundary_restored'] is True
        assert set(result['cases'])==set(ids)
        report.update(status='PASS',original_Native13_plus_capture7_unchanged=True,
            Business_Report_actuals_and_prior_period_cases_retained=True,
            rollback_only_native_group=True)
    finally:control.STATE=previous


def actual_cron(conn,cur,database,url,report):
    install(conn,cur,report)
    cron.exercise(conn,cur,database,url,report)
    row=cur.execute('select report_book_signature,book_signature,report_snapshot::text from cp7_finance_capture.captures where id=%s',
        (report['finance_capture_id'],)).fetchone()
    assert row[0] is not None and row[0]==row[1]
    conn.rollback()
    report.update(report_and_collected_book_signatures_equal=True,observed_report_snapshot=row[2],
        unchanged_actual_minute_cron_oracles=True)


def measure(url,dates,candidate,limit):
    with psycopg.connect(url)as conn,conn.cursor()as cur:
        assert conn.info.host in ('localhost','127.0.0.1') and conn.info.port==54322
        assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
        cur.execute("set local track_functions='all'")
        cur.execute("set local lock_timeout='2s'")
        cur.execute("select set_config('statement_timeout',%s,true)",(str(limit),))
        before_catalog=product.catalog._catalog_rows(cur);before_data=product.catalog._data(cur)
        if candidate:patch.install_for_rollback(cur,product.catalog)
        writes=single.table_writes(cur)
        with capture.as_capture(cur):
            started=monotonic()
            value=cur.execute('select cp7_finance_capture.report_unit(%s::jsonb)',(json.dumps(dates),)).fetchone()[0]
            elapsed=round((monotonic()-started)*1000,3)
        assert single.writes_delta(writes,single.table_writes(cur))=={}
        assert product.catalog._data(cur)==before_data
        detail=dict(elapsed_ms=elapsed,statement_limit_ms=limit,table_write_attempts={},candidate=candidate)
        if candidate:
            expected=reference.signature(cur,dates['as_of'],10000)
            assert value['expected_book_signature']==expected['signature'] and value['rows']==expected['rows']
            calls=cur.execute('select calls from pg_stat_xact_user_functions where funcid=%s::regprocedure',(patch.HELPER,)).fetchone()
            assert calls==(1,),'REPORT_BOOK_SCAN_MUST_RUN_ONCE'
            detail.update(independent_signature_exact=True,whole_book_scan_calls=1)
        conn.rollback()
        assert product.catalog._catalog_rows(cur)==before_catalog and product.catalog._data(cur)==before_data
        conn.rollback()
    report=dict(value['report']);assert report.pop('captured_at')
    return report,value['rows'],detail


def overhead(conn,cur,database,url,report):
    today=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
    pairs=report.setdefault('pairs',{})
    for label,limit in (('SMALL',8000),('PRICE_PERCENT',8000),('FACTORY_1200X3',30000)):
        granted,_=database._foundation(cur)
        if label=='SMALL':single.finance.setup(cur,today)
        elif label=='PRICE_PERCENT':report['price_percent_fixture']=single.price_fixture.seed(cur,today)
        else:single.profile.retained.factory.seed(conn,cur,today,report.setdefault('factory_fixture',{}))
        capture.b.api.admin(cur)
        if granted:cur.execute('revoke usage on schema erp from authenticated')
        conn.commit();dates={k:str(today)for k in ('from','to','as_of')}
        evidence=pairs.setdefault(label,dict(status='INCOMPLETE'))
        old,old_rows,before=measure(url,dates,False,limit);evidence['accepted_parent']=before
        new,new_rows,after=measure(url,dates,True,limit);evidence['same_snapshot_signature_candidate']=after
        assert old==new and old_rows==new_rows,'OFFICIAL_REPORT_OR_SOURCE_COUNTS_CHANGED'
        evidence.update(status='PASS',full_report_equal_except_captured_at=True,
            elapsed_change_ms=round(after['elapsed_ms']-before['elapsed_ms'],3),performance_qualification=False)
    report.update(status='PASS',diagnostic_only=True,product_adoption=False,production_go=False,
        factory3600_acceptance=False,original_report_checker_calls_unchanged=True)


CHILDREN=(('REPORT_BOOK_INDEPENDENT_CANONICAL_SIGNATURE',independent),
          ('REPORT_BOOK_UNCHANGED_CHILD_VISIBILITY_COUNTEREXAMPLE',child_visibility),
          ('REPORT_BOOK_UNCHANGED_NATIVE20',native20),
          ('REPORT_BOOK_UNCHANGED_ACTUAL_MINUTE_CRON',actual_cron),
          ('REPORT_BOOK_SMALL_PRICE_FACTORY_OVERHEAD',overhead))
