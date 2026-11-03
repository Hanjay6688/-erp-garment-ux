"""Own the declared Native9/HTTP2/session2/browser2 on installed disposable state."""
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
from contextlib import contextmanager
import importlib.util,json,os

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CASE='CURRENT_AFUI_GOOD_NONPAYABLE_NATIVE9_HTTP2_SESSION2_BROWSER2'
LABEL='CP7_AFUI_GOOD_NONPAYABLE_FULL15'
NATIVE_LABEL=LABEL+'_NATIVE9'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def scheduler_quiet(url):
    return load('afui_original_scheduler_quiet',ROOT/'scripts/current-vendor-receivable-qualification/native_runner.py').scheduler_quiet(url)

def save(name,value):
    path=ROOT/'cp6-proof/t3'/name;path.parent.mkdir(parents=True,exist_ok=True)
    raw=(json.dumps(value,sort_keys=True,default=str)+'\n').encode()
    if path.exists()and path.read_bytes()!=raw:raise ValueError('NONPAYABLE_FIRST_ORIGINAL_OVERWRITE_REFUSED:'+name)
    if not path.exists():
        with path.open('xb')as stream:stream.write(raw)
    return dict(name=name,bytes=len(raw),sha256=sha256(raw).hexdigest())

def retain(native,report):
    records=[]
    for name in(NATIVE_LABEL+'.json',NATIVE_LABEL+'_BUSINESS_DAY_FIRST_ATTEMPT.json'):
        source=native.r1.OUT/name
        if not source.is_file():continue
        raw=source.read_bytes();target=ROOT/'cp6-proof/t3'/name
        if target.exists()and target.read_bytes()!=raw:raise ValueError('NONPAYABLE_FIRST_STRICT_NATIVE_ORIGINAL_CHANGED')
        if not target.exists():
            with target.open('xb')as stream:stream.write(raw)
        records.append(dict(name=name,bytes=len(raw),sha256=sha256(raw).hexdigest()))
    report['strict_group_originals']=records

def local(conn,cur,url):
    p=urlparse(url)
    if(p.hostname not in('127.0.0.1','localhost')or p.port!=54322 or p.path!='/cp6_rollback'
        or conn.info.host not in('127.0.0.1','localhost')or conn.info.port!=54322
        or cur.execute('select current_database()').fetchone()!=('cp6_rollback',)):
        raise ValueError('NONPAYABLE_WHOLE_QUALIFIER_EXACT_LOCAL_DISPOSABLE_ONLY')

def retain_failed_case(cur,name,error,before,modules,catalog):
    """Preserve a valid failed transaction before the mandatory rollback.

    A SQL error leaves PostgreSQL INERROR; never query that transaction or
    replace the original failure with a secondary diagnostic failure.
    """
    value=dict(status='FAILED_NATIVE_CASE_OBSERVATION_NOT_ACCEPTANCE',case_id=name,
        error_type=type(error).__name__,error=str(error),before=before,
        actual_case_credit=0,production_go=False,independent_acceptance=False)
    try:
        status=cur.connection.info.transaction_status.name
        value['transaction_status']=status
        if status=='INTRANS':
            modules.bc.api.admin(cur)
            with modules.control.product_catalog(cur):
                value['after_operation']=dict(actual_all22=catalog._catalog_rows(cur),
                    full_data_and_sequences=catalog._data(cur))
        else:
            value['observation_unavailable']='FAILED_TRANSACTION_NOT_QUERYABLE:'+status
    except Exception as capture_error:
        value['observation_error']=dict(error_type=type(capture_error).__name__,error=str(capture_error))
    original=None
    try:
        original=save('AFUI_NATIVE_FIRST_FAILURE_'+name+'.json',value)
        note='AFUI_NATIVE_FAILED_TRANSACTION_ORIGINAL:'+json.dumps(original,sort_keys=True)
    except Exception as save_error:
        note='AFUI_NATIVE_FAILURE_OBSERVATION_SAVE_FAILED:'+str(save_error)
    try:error.add_note(note)
    except Exception:pass  # The mandatory rollback and original failure take priority.
    return original

def full_case(cur,name,operation,state,control):
    from . import assembly,case_boundary,native_cases
    # Use the unchanged Native fixture's administrative actor; no new grants.
    import cp6_bc_probe as bc
    modules=SimpleNamespace(bc=bc,control=control,product=assembly)
    before=native_cases.boundary(cur,modules,state);catalog=assembly.runtime()[-1]
    cur.execute('savepoint afui_full_current_case');error=None;result=None;observed=None
    try:
        result=operation()
        bc.api.admin(cur)
        cur.execute('set constraints all immediate');cur.execute('set constraints all deferred')
        with control.product_catalog(cur):observed=case_boundary.capture_generated(cur,catalog,before)
    except Exception as caught:
        error=caught
        retain_failed_case(cur,name,caught,before,modules,catalog)
    try:
        cur.execute('rollback to savepoint afui_full_current_case');cur.execute('release savepoint afui_full_current_case')
    except Exception as caught:raise ValueError('NONPAYABLE_STRICT_CASE_TRANSACTION_BOUNDARY_LOST; original='+str(error))from caught
    if error is not None:raise error
    after=native_cases.boundary(cur,modules,state)
    if type(result)is not dict:raise ValueError('NONPAYABLE_NATIVE_CASE_OBJECT_REQUIRED')
    boundary=dict(before=before,after=after,after_operation=observed)
    boundary['verification']=case_boundary.validate(boundary,case_id=name,result=result)
    result['actual_full22_case_boundary']=boundary
    return result

def committed_prerequisite(url,state,report,control):
    from . import assembly,browser_prepare,native_fixture
    import psycopg
    with psycopg.connect(url,connect_timeout=5)as conn,conn.cursor()as cur:
        local(conn,cur,url)
        with control.product_catalog(cur):assembly.verify(cur,state)
        import cp6_bc_probe as bc
        bc.api.admin(cur)
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        today=cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
        prepared=browser_prepare.prepare(cur,today,state)
        bc.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        # The committed source for Auth/browser copies has exact product ACLs.
        # The original SQL-only usage overlay is not carried into real Auth.
        if assembly.runtime()[-1]._catalog_rows(cur)!=state['after']:
            raise ValueError('NONPAYABLE_COMMITTED_PREREQUISITE_MUST_KEEP_EXACT_PRODUCT_AUTHORITY')
        assembly.verify(cur,state);cur.execute('set constraints all immediate');cur.execute('set constraints all deferred');conn.commit()
        report['browser_fixture_original']=save('AFUI_BROWSER_NATIVE_PREREQUISITE.json',prepared)
        report['browser_settings_state_original']=save('AFUI_BROWSER_SETTINGS_STATE.json',state)
        before=native_fixture.observe(cur,SimpleNamespace(bc=bc),prepared['fixture'])
        with control.product_catalog(cur):
            catalog=assembly.runtime()[-1]
            census_before=dict(actual_all22=catalog._catalog_rows(cur),full_data_and_sequences=catalog._data(cur))
            try:assembly.rollback_delta_preuse(cur,state)
            except ValueError as error:
                if str(error)!=assembly.USED_ERROR:raise
                refusal=str(error)
            else:raise ValueError('NONPAYABLE_ACTUALLY_USED_ASSEMBLY_REMOVAL_WAS_NOT_REFUSED')
            census_after=dict(actual_all22=catalog._catalog_rows(cur),full_data_and_sequences=catalog._data(cur))
            if census_before!=census_after:raise ValueError('NONPAYABLE_USED_INVERSE_REFUSAL_CHANGED_CATALOG_ROWS_OR_SEQUENCES')
        conn.rollback()
        report['separate_committed_Native_use']=dict(status='ACTUAL_POSITIVE_HPP_ZERO_REIMBURSEMENT_GOOD_COMMITTED',
            actual_GOOD_lot=prepared['fixture']['lot'],actual_economics=before,Native_case_credit=0,
            actual_used_inverse_error=refusal,before=census_before,after=census_after,used_guard_before_DDL=True)

@contextmanager
def browser_environment(report):
    changes=dict(AFUI_BROWSER_CONFIRM='cp6_auditor_browser',
        AFUI_BROWSER_FIXTURE_SHA256=report['browser_fixture_original']['sha256'],
        AFUI_BROWSER_STATE_SHA256=report['browser_settings_state_original']['sha256'],
        AUDITOR_BROWSER_CASE_TIMEOUT_MS='600000')
    original={name:os.environ.get(name)for name in changes}
    os.environ.update(changes)
    try:yield
    finally:
        for name,value in original.items():
            if value is None:os.environ.pop(name,None)
            else:os.environ[name]=value

def exercise(conn,cur,database,url,report,state):
    from . import admission,assembly,native_cases,access_cases,browser_prepare,copy_context,qualification_gate
    admission.parent_receipt()  # Before ERP graph, connection or fixture use.
    from cp7_p21_current_chain_rehearsal_probe import helper
    from cp7_catalog_state import exact_public_catalog
    local(conn,cur,url);control=helper.control;native=control.native
    with control.product_catalog(cur):assembly.verify(cur,state)
    report.update(status='INCOMPLETE',actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
        actual_browser_cases=0,retained_FREE3_fresh_case_credit=0,production_go=False,independent_acceptance=False,
        global_writer_or_permission_or_lock_closure=False)
    conn.rollback();cur.close();conn.close()
    def verify(cursor):
        with control.product_catalog(cursor):return assembly.verify(cursor,state)
    def cases(cursor,today):
        failed=[]
        def one(name,operation):
            if failed:return dict(status='INCOMPLETE',blocked_by_first_case=failed[0],
                error='NONPAYABLE_REMAINING_CASES_NOT_RUN_AFTER_FIRST_FAILURE',actual_case_credit=0)
            try:return full_case(cursor,name,operation,state,control)
            except Exception:
                failed.append(name);raise
        return[(name,lambda name=name,operation=operation:one(name,operation))
            for name,operation in native_cases.cases(cursor,today,state)]
    try:
        with exact_public_catalog(native,retain_raw=True)as public:
            actual=native.strict_group(NATIVE_LABEL,cases,verify)
    finally:retain(native,report)
    report.update(native=actual,public_catalog_observation=public)
    report['Native9_gate']=qualification_gate.native(actual,native_cases.IDS)
    report['actual_Native_cases']=9
    committed_prerequisite(url,state,report,control)
    modes=load('afui_unchanged_original_real_Auth_and_browser_modes',ROOT/'scripts/current-s03-sku-s05-composite-qualification/modes.py')
    adapter=SimpleNamespace(http_cases=lambda http,today:access_cases.http_cases(http,today,state=state),
        races=lambda tools,today:access_cases.races(tools,today,state=state))
    with copy_context.scope(modes,state)as copies:
        report['copy_authority']=copies
        report['http']=modes.run_http(adapter,verify,'afui_dates_http2')
        report['HTTP2_gate']=qualification_gate.copies(report['http'],access_cases.HTTP_IDS,mode='HTTP')
        report['actual_Auth_HTTP_cases']=2
        report['races']=modes.run_races(adapter,verify,'afui_dates_session2')
        report['session2_gate']=qualification_gate.copies(report['races'],access_cases.RACE_IDS,mode='RACE')
        report['actual_two_session_races']=2
        with browser_environment(report):report['browser']=modes.run_browser(HERE/'browser.mjs',verify,'afui_dates_browser2')
        report['browser2_gate']=qualification_gate.copies(report['browser'],browser_prepare.IDS,mode='BROWSER')
        report['actual_browser_cases']=2
    if(len(report['copy_authority']['actual_copy_admissions'])!=4
        or any(row.get('all22_groups_equal_original_install')is not True
            or row.get('product_state_modified')is not False
            or row.get('Native_or_schema_or_RPC_permissions_changed')is not False
            for row in report['copy_authority']['actual_copy_admissions'])):
        raise ValueError('NONPAYABLE_FOUR_FRESH_COMPLETE_AUTHORITY_PRESERVED_COPIES_REQUIRED')
    report.update(status='PASS',actual_business_cases=15,used_guard_refused_before_DDL=True,
        full_outer_backup_all22_data_ALL_sequences_roles_CP6_advisors_Auth_restore_and_all5_still_required=True)

