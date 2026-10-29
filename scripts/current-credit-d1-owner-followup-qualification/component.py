"""Fresh3 only, plus a separate committed continuation used-inverse witness."""
from hashlib import sha256
from pathlib import Path
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASE = 'CREDIT_D1_CONTINUATION_NATIVE3_AND_SEPARATE_COMMITTED_USED_INVERSE'
LABEL = 'CP7_CREDIT_D1_CONTINUATION_NATIVE3_CASES'
FIXTURE_PATHS = ('scripts','scripts/cp7_customer_credit/consumer','scripts/cp7_customer_credit/reconciliation/native',
                 'scripts/cp7_customer_credit/native','scripts/cp7_customer_credit/initial-settlement')


def load(name,path):
    spec = importlib.util.spec_from_file_location(name,path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def require_local(conn,cur):
    if conn.info.host not in ('localhost','127.0.0.1')or conn.info.port != 54322:
        raise ValueError('D1_CONT_LOCAL_DISPOSABLE_PORT_ONLY')
    if cur.execute('select current_database()').fetchone() != ('cp6_rollback',):
        raise ValueError('D1_CONT_DISPOSABLE_DATABASE_ONLY')


@load('continuation_scoped_scheduler_arguments',HERE/'argv_scope.py').inherited_entrypoint
def scheduler_quiet(url):
    return load('continuation_unchanged_vendor_scheduler',ROOT/'scripts/current-vendor-receivable-qualification/native_runner.py').scheduler_quiet(url)


def retain_originals(native,report):
    destination = ROOT/'cp6-proof/t3'; destination.mkdir(parents=True,exist_ok=True)
    retained = []
    for name in (LABEL+'.json',LABEL+'_BUSINESS_DAY_FIRST_ATTEMPT.json'):
        path = native.r1.OUT/name
        if path.is_file():
            raw = path.read_bytes(); target = destination/name
            if target.exists()and target.read_bytes() != raw:
                raise ValueError('D1_CONT_PRIOR_RAW_ORIGINAL_MUST_NOT_BE_OVERWRITTEN:'+name)
            target.write_bytes(raw)
            retained.append(dict(name=name,bytes=len(raw),sha256=sha256(raw).hexdigest()))
    report['strict_group_originals'] = retained


def committed_witness(url,state,business,product,control,financial_truth):
    import psycopg
    with psycopg.connect(url)as conn,conn.cursor()as cur:
        require_local(conn,cur); native = business.n.native
        if not cur.execute('select count(*)from erp.app_users').fetchone()[0]:
            native.b.api.seed(cur)
        cur.execute('grant usage on schema erp to authenticated')  # unchanged isolated Native harness capability
        today = cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
        before_truth = financial_truth.all_truth(cur)
        setup = business.prepare_250(cur,today,'COMMITTED_CONTINUATION')
        signed = business.consume_undo(cur,setup,'APPLY','COMMITTED_APPLY220')
        business.assert_old(cur,setup)
        after_truth = financial_truth.all_truth(cur)
        if not financial_truth.truth_quiet(before_truth,after_truth):
            raise AssertionError(('D1_CONT_COMMITTED_FINANCIAL_TRUTH_CHANGED',before_truth,after_truth))
        if signed['restored'] != business.n.oracle.GOLD['APPLY_UNDONE']:
            raise AssertionError('D1_CONT_COMMITTED_SIGNED_HISTORY_PROFILE_CHANGED')
        cur.execute('set constraints all immediate'); cur.execute('set constraints all deferred'); conn.commit()
        result = dict(status='ACTUAL_D1_AND_SIGNED_APPLY220_UNDO_COMMITTED',
            scope='SEPARATE_COMMITTED_CONTINUATION_USED_INVERSE_WITNESS_ZERO_NATIVE3_CREDIT',
            committed_D1=setup['out'],signed_events=[signed['original'],signed['undo']],actual_profile=signed['restored'],
            raw_signed_history=signed['raw_history'],complete_prefixes=signed['evidence'],
            immutable_old_D1_sale_payment_HPP_stock_cost_and_money_oracles_retained=True,
            financial_truth_before=before_truth,financial_truth_after=after_truth,Native_case_credit=0,actual_Auth=False)
        with control.product_catalog(cur):
            *_,catalog = product.runtime(); before_catalog,before_data = catalog._catalog_rows(cur),catalog._data(cur)
            try:
                product.rollback_delta_preuse(cur,state)
            except ValueError as error:
                if str(error) != product.USED_ERROR:
                    raise
                result['actual_used_inverse_error'] = str(error)
            else:
                raise AssertionError('D1_CONT_COMMITTED_USED_INVERSE_NOT_REFUSED')
            if catalog._catalog_rows(cur) != before_catalog or catalog._data(cur) != before_data:
                raise AssertionError('D1_CONT_USED_REFUSAL_CHANGED_CATALOG_ROWS_OR_SEQUENCES')
        conn.rollback()
        return result


@load('continuation_scoped_component_arguments',HERE/'argv_scope.py').inherited_entrypoint
def exercise(conn,cur,database,url,report,state):
    for relative in FIXTURE_PATHS:
        sys.path.insert(0,str(ROOT/relative))
    from cp7_credit_correction_de import composition as product
    from cp7_p21_current_chain_rehearsal_probe import helper
    from cp7_catalog_state import exact_public_catalog
    import cp6_bd_probe as financial_truth
    business = load('continuation_actual_three_business_callbacks',ROOT/'scripts/current-credit-d1-continuation-qualification/cases.py')
    admission = load('continuation_component_parent_admission',HERE/'admission.py')
    gate = load('continuation_component_group_gate',HERE/'gate.py')
    require_local(conn,cur)
    if state['sources'] != product.sources()or list(business.IDS) != admission.cfg()['fresh_native_case_ids']:
        raise ValueError('D1_CONT_EXACT_CURRENT_INSTALLATION_AND_THREE_CASES_REQUIRED')
    parent_proof, originals = admission.retained(product,admission.source_only())
    pin = admission.cfg()['accepted_native13']
    business.admit_native13(originals['strict_native13'],original_report_sha256=pin['original']['sha256'],
        qualified_backend_commit=pin['head'],installed_state=state)
    conn.rollback(); cur.close(); conn.close(); control,native = helper.control,helper.control.native
    report.update(status='INCOMPLETE',actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,
        actual_two_session_races=0,retained_Native13_reexecuted=False,retained_parent=parent_proof,
        qualification_scope='D1_CONTINUATION3_ONLY_ABOVE_RETAINED_QUALIFIED_D1_NATIVE13',
        D_complete=False,E_complete=False,production_go=False,independent_acceptance=False)

    def verify(cursor):
        with control.product_catalog(cursor):
            return product.verify(cursor,state)

    try:
        with exact_public_catalog(native,retain_raw=True)as public:
            actual = native.strict_group(LABEL,business.cases,verify)
    finally:
        retain_originals(native,report)
    report.update(native=actual,public_catalog_observation=public)
    gate.exact_group(actual,business.IDS,3)
    report['separate_committed_continuation_witness'] = committed_witness(url,state,business,product,control,financial_truth)
    report.update(status='PASS',actual_Native_cases=3,used_guard_refused_before_DDL=True,
        committed_witness_additional_cases=0,acceptance_requires_complete_outer_restore_and_all_five_package_gates=True,
        unchanged_three_business_callbacks_and_financial_history_oracles=True)
