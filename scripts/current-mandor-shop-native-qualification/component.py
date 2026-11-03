"""Native9 and a separate committed-use restoration witness, all gated.

The caller supplies the already admitted assembly and fixed local maintenance
connector. Nine scenarios include Native return/correction, installments and
sequential current rights; they grant no Auth HTTP, browser or two-session
credit. No operation runs while this module is imported.
"""
from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
import importlib.util,json
import admission,cases
from native_fixture import Native,local,require

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CASE='FG_MANDOR_NATIVE9_SELECTED_WEEK_PARTIAL_RELEASE_REVERSE_REFUSALS_STORE'
LABEL='CP7_FG_MANDOR_NATIVE9'
NATIVE_LABEL=LABEL+'_STRICT'


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


def source_record(path):
    raw=path.read_bytes();return dict(name=path.name,bytes=len(raw),sha256=sha256(raw).hexdigest())


def scheduler_quiet(url):
    from assembly import FROZEN
    return load('mandor_unchanged_qualified_scheduler_control',FROZEN/'scripts/current-vendor-receivable-qualification/native_runner.py').scheduler_quiet(url)


def context(product,state,*,scope='NATIVE9'):
    require(product.domain_modules is not None,'MANDOR_NATIVE_ACTUAL_PARENT_DOMAIN_IMPORT_REQUIRED')
    # The owning caller puts the exact frozen parent's scripts on sys.path.
    # These module identities are independently pinned by that parent's graph.
    import cp7_cp17_fix_cases as finish
    import cp7_master_cases as master
    import cp7_sales_command_cases as sales
    import cp7_sales_draft_cases as draft
    import cp7_cash_funding as funding
    from assembly import FROZEN
    require(Path(funding.__file__).resolve()==FROZEN/'scripts/cp7_cash_funding.py',
        'MANDOR_NATIVE_EXACT_PARENT_CASH_FUNDING_MODULE')
    return Native(product.domain_modules,product.fixture,finish,master,sales,draft,
        product.mandor,state['Mandor'],funding=funding,scope=scope)


def exercise(product,trusted_connection,conn,cur,database,url,report,state):
    admission.parent(product.parent_raw);local(cur);product.verify(cur,state)
    from cp7_p21_current_chain_rehearsal_probe import helper
    control=helper.control;native=control.native
    report.update(status='INCOMPLETE',actual_Native_cases=0,actual_Auth_HTTP_cases=0,
        actual_two_session_races=0,actual_browser_cases=0,global_writer_or_permission_or_lock_closure=False,
        production_go=False,independent_acceptance=False)
    conn.rollback();cur.close();conn.close()
    report['scheduler_quiet_before_Native']=scheduler_quiet(url)
    def verify(cursor):
        with control.product_catalog(cursor):return product.verify(cursor,state)
    def factory(cursor,today):
        verify(cursor);return cases.cases(context(product,state),cursor,today)
    observed=native.strict_group(NATIVE_LABEL,factory,verify)
    originals=[]
    for name in(NATIVE_LABEL+'.json',NATIVE_LABEL+'_BUSINESS_DAY_FIRST_ATTEMPT.json'):
        path=native.r1.OUT/name
        if not path.exists():continue
        target=ROOT/'cp6-proof/t3'/name;target.parent.mkdir(parents=True,exist_ok=True)
        raw=path.read_bytes()
        if target.exists():require(target.read_bytes()==raw,'MANDOR_NATIVE_FIRST_STRICT_ORIGINAL_CHANGED')
        else:
            with target.open('xb')as output:output.write(raw)
        originals.append(source_record(target))
    report['strict_group_originals']=originals
    require(observed['status']=='PASS'and observed['planned_case_ids']==list(cases.IDS),
        'MANDOR_NATIVE_EXACT_NINE_ACTUAL_CASES_REQUIRED')
    require(set(observed['cases'])==set(cases.IDS)and all(x['status']=='PASS'for x in observed['cases'].values()),
        'MANDOR_NATIVE_INCOMPLETE_OR_MISSING_CASE')
    require(observed['complete_boundary_restored']is True,'MANDOR_NATIVE_COMPLETE_STRICT_GROUP_RESTORE')
    # A committed positive payment is necessary to exercise the genuine used
    # inverse refusal and full backup restore; it earns ZERO extra case credit.
    import psycopg
    committed=context(product,state,scope='COMMITTED_USE')
    with psycopg.connect(url)as used,used.cursor()as cursor:
        local(cursor);verify(cursor)
        today=cursor.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
        before=committed.modules.bc.findings(cursor)
        witness=cases.selected_week(committed,cursor,today)
        committed.admin(cursor);cursor.execute('set constraints all immediate')
        after=committed.modules.bc.findings(cursor)
        require(not committed.modules.bc.new_findings(before,after),'MANDOR_COMMITTED_USE_NEW_FINANCIAL_FINDINGS')
        product.verify(cursor,state);used.commit()
    before_refusal=None;after_refusal=None
    with trusted_connection()as check,check.cursor()as cursor:
        local(cursor);before_refusal=committed.boundary(cursor)
        try:product.rollback_delta_preuse(cursor,state)
        except ValueError as error:
            require(str(error)==product.USED_ERROR,'MANDOR_NATIVE_EXPECTED_ACTUAL_USED_INVERSE_REFUSAL')
            message=str(error)
        else:raise ValueError('MANDOR_NATIVE_USED_FINANCIAL_STAGE_REMOVAL_WAS_ALLOWED')
        after_refusal=committed.boundary(cursor)
        require(before_refusal==after_refusal,'MANDOR_NATIVE_USED_REFUSAL_CHANGED_METADATA_DATA_OR_SEQUENCE')
        check.rollback()
    report.update(status='PASS',actual_Native_cases=9,strict_case_ids=list(cases.IDS),
        separate_committed_Native_use=dict(status='ACTUAL_MANDOR_INVOICE_OFFSET_AND_NET_PAYROLL_COMMITTED',
            native_case_credit=0,witness=witness,financial_findings_before=before,financial_findings_after=after,
            actual_used_inverse_error=message,before_original=committed.original('REFUSAL_BEFORE',before_refusal),
            after_original=committed.original('REFUSAL_AFTER',after_refusal),used_guard_before_DDL=True),
        used_guard_refused_before_DDL=True,actual_Mandor_Auth_browser_race_acceptance_pending=True)


def runner(product,trusted_connection):
    return SimpleNamespace(CASE=CASE,LABEL=LABEL,scheduler_quiet=scheduler_quiet,
        exercise=lambda conn,cur,database,url,report,state:exercise(product,trusted_connection,conn,cur,database,url,report,state))
