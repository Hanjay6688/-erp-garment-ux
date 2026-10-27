"""Exercise the actual combined installation; never install either half alone."""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from time import monotonic
import importlib.util,json
import psycopg

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


product=load('combined_qualification_product',HERE/'composition.py')
retained=load('combined_unchanged_consistency_operations',ROOT/'scripts/current-finance-consistent-capture-diagnostic/cases.py')
factory=load('combined_current_public_factory_cron',HERE/'qualification_factory.py')
STATE=None


def verify_existing(conn,cur,report):
    if STATE is None:raise ValueError('COMBINED_ACTUAL_INSTALLATION_REQUIRED')
    product.sources()
    _,patch,single,_,catalog=product.runtime()
    # A complete dump/reparse has narrowly declared portable spellings. Keep
    # the original raw seal unchanged; do not project this catalog into it.
    assert catalog._portable(catalog._catalog_rows(cur))==catalog._portable(STATE['after'])
    for signature,old in STATE['rows'].items():
        assert patch.row(cur,signature)[:5]==old[:5],signature
    report['actual_combined_installation_verified']=True
    report['diagnostic_install_replaced_only_by_existing_install_verification']=True
    conn.rollback()


@contextmanager
def installed_operations(state):
    global STATE
    prior_state,prior_install=STATE,retained.install
    STATE=state;retained.install=verify_existing
    try:yield
    finally:STATE=prior_state;retained.install=prior_install


def factory_cron(conn,cur,database,url,report):
    verify_existing(conn,cur,report)
    factory.exercise(conn,cur,database,url,report)
    expected,actual=cur.execute('select report_book_signature,book_signature from cp7_finance_capture.captures where id=%s',
        (report['finance_capture_id'],)).fetchone()
    assert expected is not None and expected==actual
    conn.rollback()
    report['report_and_collected_book_signatures_equal']=True


def measure(url,dates,baseline,limit):
    if STATE is None:raise ValueError('COMBINED_ACTUAL_INSTALLATION_REQUIRED')
    _,patch,_,_,catalog=product.runtime()
    with psycopg.connect(url)as conn,conn.cursor()as cur:
        assert conn.info.host in ('localhost','127.0.0.1') and conn.info.port==54322
        assert cur.execute('select current_database()').fetchone()==('cp6_rollback',)
        cur.execute("set local track_functions='all'");cur.execute("set local lock_timeout='2s'")
        cur.execute("select set_config('statement_timeout',%s,true)",(str(limit),))
        before=catalog._catalog_rows(cur);data=catalog._data(cur)
        if baseline:
            # Diagnostic reference only: restore the exact four accepted
            # bodies inside this transaction, then roll back the entire call.
            # This is not the product inverse and does not erase used data.
            for row in STATE['original_rows'].values():cur.execute(row[5],prepare=False)
        writes=retained.single.table_writes(cur)
        with retained.capture.as_capture(cur):
            counters=retained.single.profile.functions(cur);started=monotonic()
            value=cur.execute('select cp7_finance_capture.report_unit(%s::jsonb)',(json.dumps(dates),)).fetchone()[0]
            elapsed=round((monotonic()-started)*1000,3)
            functions=retained.single.profile.difference(counters,retained.single.profile.functions(cur))
        assert retained.single.writes_delta(writes,retained.single.table_writes(cur))=={}
        assert catalog._data(cur)==data
        calls={r['function']:r['calls']for r in functions}
        assert calls['erp.run_v268_financial_report_checks()']==(2 if baseline else 1)
        assert calls.get(patch.HELPER,0)==(0 if baseline else 1)
        metadata=cur.execute('select p.oid::regprocedure::text,p.provolatile,p.prosecdef,'
            'pg_get_userbyid(p.proowner),p.proconfig,p.prorettype::regtype::text,pg_get_functiondef(p.oid) '
            'from pg_proc p where p.oid=any(%s::regprocedure[])order by 1',(list(calls),)).fetchall()
        assert {row[0]for row in metadata}==set(calls),'COMBINED_OBSERVED_FUNCTION_METADATA_INCOMPLETE'
        observed={row[0]:dict(volatility=row[1],security_definer=row[2],owner=row[3],config=row[4],
            return_type=row[5],definition=row[6],definition_sha256=sha256(row[6].encode()).hexdigest())for row in metadata}
        # The accepted Native access guard returns void and supplies no money
        # value. Its permission observation is deliberately separate from the
        # financial readers. Do not exempt any other volatile observed reader.
        nonstable={name:row['volatility']for name,row in observed.items()
            if row['volatility']not in ('s','i')and not(name=='erp.require_internal()'and row['return_type']=='void')}
        if not baseline:
            expected=retained.reference.signature(cur,dates['as_of'],10000)
            assert value['expected_book_signature']==expected['signature']
            assert value['rows']==expected['rows']
        report=dict(value['report']);assert report.pop('captured_at')
        conn.rollback()
        assert catalog._catalog_rows(cur)==before and catalog._data(cur)==data
        conn.rollback()
    return report,value['rows'],dict(elapsed_ms=elapsed,statement_limit_ms=limit,
        functions=functions,official_check_calls=2 if baseline else 1,book_signature_calls=0 if baseline else 1,
        observed_reader_catalog=observed,observed_nonstable_financial_readers=nonstable,
        observed_function_metadata_complete=True,complete_transitive_call_graph_verified=False,
        zero_table_write_attempts=True,all22_data_sequences_restored=True,
        temporary_original_reader_bodies_only=baseline,performance_qualification=False,
        report_sha256=sha256(json.dumps(report,sort_keys=True,default=str).encode()).hexdigest())


def paired_reports(conn,cur,database,url,report):
    verify_existing(conn,cur,report)
    today=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
    pairs=report.setdefault('pairs',{})
    for label,limit in (('SMALL',8000),('PRICE_PERCENT',8000),('FACTORY_1200X3',30000)):
        granted,_=database._foundation(cur)
        if label=='SMALL':retained.single.finance.setup(cur,today)
        elif label=='PRICE_PERCENT':report['price_percent_fixture']=retained.single.price_fixture.seed(cur,today)
        else:retained.single.profile.retained.factory.seed(conn,cur,today,report.setdefault('factory_fixture',{}))
        retained.capture.b.api.admin(cur)
        if granted:cur.execute('revoke usage on schema erp from authenticated')
        conn.commit();dates={k:str(today)for k in ('from','to','as_of')}
        evidence=pairs.setdefault(label,dict(status='INCOMPLETE'))
        left,left_rows,old=measure(url,dates,True,limit);evidence['accepted_reader_bodies']=old
        right,right_rows,new=measure(url,dates,False,limit);evidence['combined_reader']=new
        assert left==right and left_rows==right_rows,'COMBINED_WHOLE_OFFICIAL_REPORT_CHANGED'
        assert not new['observed_nonstable_financial_readers'],('COMBINED_FINANCIAL_READER_VOLATILITY_REQUIRES_DIAGNOSIS',new['observed_nonstable_financial_readers'])
        evidence.update(status='PASS',entire_official_report_equal_except_captured_at=True,
            observed_financial_readers_same_statement_snapshot=True,
            elapsed_change_ms=round(new['elapsed_ms']-old['elapsed_ms'],3))
    report.update(status='PASS',three_complete_report_pairs=True,performance_qualification=False,
        independent_signature_exact=True,zero_ERP_writes=True)


CHILDREN=(
    ('COMBINED_UNCHANGED_CHILD_VISIBILITY',retained.child_visibility),
    ('COMBINED_NULL_SNAPSHOT_REFUSAL_AND_RECOVERY',retained.assigned_transaction_visibility),
    ('COMBINED_UNCHANGED_NATIVE20',retained.native20),
    ('COMBINED_INDEPENDENT_SIGNATURE',retained.independent),
    ('COMBINED_CURRENT_PUBLIC_ACTUAL_CRON',retained.actual_cron),
    ('COMBINED_SMALL_PRICE_FACTORY_REPORT_PAIRS',paired_reports),
    ('COMBINED_CURRENT_PUBLIC_FACTORY1200X3_ACTUAL_CRON',factory_cron),
)
