"""Ten unchanged S05 Native cases plus a separately labelled business witness.

Only caller execution on its disposable target opens connections. Import is
inert; local orchestration controls never import the product runtime.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
import importlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASE = 'S05_NATIVE10_AND_SEPARATE_COMMITTED_USED_INVERSE'
LABEL = 'CP7_S05_ACCESSORY_STANDARD_NATIVE10_CASES'


def require_local(connection, cursor):
    if connection.info.host not in ('localhost', '127.0.0.1') or connection.info.port != 54322:
        raise ValueError('S05_LOCAL_DISPOSABLE_PORT_ONLY')
    if cursor.execute('select current_database()').fetchone() != ('cp6_rollback',):
        raise ValueError('S05_CP6_ROLLBACK_DATABASE_ONLY')


def scheduler_quiet(url):
    from cp7_vendor_receivable import composition as product
    module = product.parent().load('s05_unchanged_vendor_scheduler_quiet', product.ROOT/'scripts/current-factory-initial-stage/factory.py')
    return module.scheduler_quiet(url)


@contextmanager
def reader_binding(stage, control, observations, active):
    """Use the retained exact ACL capability around the unchanged stage.

    product_catalog checks the actual ERP schema ACL, removes only its one
    declared harness USAGE grant, and restores it after all reader objects are
    gone. No catalog entries/definitions are projected or substituted.
    """
    original = stage.reader_only

    @contextmanager
    def exact_interval(cursor, parent_state):
        row = dict(case_id=active['id'], status='INCOMPLETE')
        observations.append(row)
        with control.product_catalog(cursor):
            with original(cursor, parent_state) as reader_state:
                row['actual_reader_verification'] = stage.verify(cursor, reader_state)
                yield reader_state
            row.update(status='PASS', unchanged_stage_uninstall_proved_all22_data_sequences_and_parent=True)

    stage.reader_only = exact_interval
    try:
        yield
    finally:
        stage.reader_only = original


def exact_group(actual, ids):
    if actual.get('status') != 'PASS' or actual.get('counts') != {'PASS': len(ids)} or set(actual.get('cases', {})) != set(ids):
        raise ValueError('S05_EXACT_NATIVE10_PASS_REQUIRED')
    if actual.get('planned_case_ids') != list(ids) or actual.get('complete_boundary_restored') is not True:
        raise ValueError('S05_COMPLETE_STRICT_GROUP_RESTORE_REQUIRED')
    for name, row in actual['cases'].items():
        if row.get('status') != 'PASS' or row.get('full_boundary_restored') is not True or row.get('public_schema_unchanged') is not True:
            raise ValueError('S05_CASE_BOUNDARY_FAILED: '+name)
        if not row.get('all_reader_intervals_data_sequences_catalog_and_parent_equal') or not row.get('actual_raw_reads'):
            raise ValueError('S05_ACTUAL_READS_AND_NO_DML_PROOF_REQUIRED: '+name)


def fixture_sources(business):
    pins = json.loads((ROOT/'scripts/cp7_accessory_standard_report/SOURCE.json').read_bytes())['files']
    modules = (business.physical, business.issues, business.master, business.qc_source, business.sessions, business.issues.bc,
               business.physical.b, business.issues.invoice, business.issues.procurement)
    observed = {}
    for module in modules:
        path = Path(module.__file__).resolve()
        relative = 'scripts/'+path.name
        # Transitive fixtures not pinned by the original component still bind
        # to their candidate source bytes; they are never silently replaced.
        expected = pins.get(relative, sha256((ROOT/relative).read_bytes()).hexdigest())
        if sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('S05_IMPORTED_NATIVE_FIXTURE_SOURCE_CHANGED: '+relative)
        observed[module.__name__] = dict(path=str(path), sha256=expected)
    return observed


def exercise(conn, cur, database, url, report, state):
    import psycopg
    from cp7_vendor_receivable import composition as product
    from cp7_p21_current_chain_rehearsal_probe import helper
    from cp7_catalog_state import exact_public_catalog
    business = importlib.import_module('cp7_accessory_standard_report.cases')
    stage = business.stage
    control, native = helper.control, helper.control.native
    require_local(conn, cur)
    if state['sources'] != product.sources():
        raise ValueError('S05_EXACT_INSTALLED_VENDOR_PARENT_REQUIRED')
    report.update(actual_Native_cases=0, qualification_scope='READ_ONLY_S05_NATIVE10_WITH_RETAINED_PARENT',
                  imported_fixture_sources=fixture_sources(business), production_go=False, independent_acceptance=False)
    observations, active = [], {'id': 'READER_PREUSE_REINSTALL'}
    report['reader_intervals'] = observations
    # The reader itself also receives an exact preuse inverse/reinstall proof.
    with reader_binding(stage, control, observations, active):
        for phase in ('INSTALL_AND_PREUSE_INVERSE', 'REINSTALL_AND_INVERSE'):
            active['id'] = 'READER_'+phase
            with stage.reader_only(cur, state):
                pass
        report['reader_preuse_reinstall'] = dict(status='PASS', all22_data_sequences_parent_equal=True,
            phases=['INSTALL_AND_PREUSE_INVERSE', 'REINSTALL_AND_INVERSE'], new_business_DML=False)
        conn.rollback(); cur.close(); conn.close()

        def verify(cursor):
            with control.product_catalog(cursor):
                return product.verify(cursor, state)

        def factory(cursor, today):
            selected = business.cases(cursor, today, state)
            if [name for name, _ in selected] != list(business.IDS):
                raise ValueError('S05_UNCHANGED_FACTORY_IDS_REQUIRED')
            def wrapped(name, operation):
                def run():
                    active['id'] = name
                    return operation()
                return run
            return [(name, wrapped(name, operation)) for name, operation in selected]

        try:
            with exact_public_catalog(native, retain_raw=True) as public:
                actual = native.strict_group(LABEL, factory, verify)
        finally:
            destination = ROOT/'cp6-proof/t3'
            destination.mkdir(parents=True, exist_ok=True)
            originals = []
            for name in (LABEL+'.json', LABEL+'_BUSINESS_DAY_FIRST_ATTEMPT.json'):
                source = native.r1.OUT/name
                if source.is_file():
                    raw = source.read_bytes(); (destination/name).write_bytes(raw)
                    originals.append(dict(name=name, bytes=len(raw), sha256=sha256(raw).hexdigest()))
            report['strict_group_originals'] = originals
    report.update(native=actual, public_catalog_observation=public)
    exact_group(actual, business.IDS)

    # This is an honest committed Native receipt/transfer/accessory issue,
    # separate from the read-only report and excluded from its Native10 count.
    # It is necessary because the vendor parent's global used-data guard must
    # see actual business use. The unchanged full outer restore cleans it up.
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        require_local(connection, cursor)
        if not cursor.execute('select count(*)from erp.app_users').fetchone()[0]:
            business.issues.bc.api.seed(cursor)
        cursor.execute('grant usage on schema erp to authenticated')  # retained local harness capability only
        today = cursor.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
        f = business.issues.fixture(cursor, today)
        before = business.issues.observe(cursor, f)
        payload = business.issues.payload(f)
        saved = business.issues.bc.note_call(cursor, 'SAVE_DRAFT', payload)
        payload.update(id=saved['id'], expected_version=saved['row_version'])
        posted = business.issues.bc.note_call(cursor, 'POST', payload)
        observed = business.issues.assert_posted(cursor, f, before)
        connection.commit()
        witness = dict(status='NATIVE_BUSINESS_COMMITTED', scope='OUTER_USED_INVERSE_WITNESS_NOT_REPORT_DML',
            issue_id=posted['id'], actual=observed, Native10_case_credit=0, report_business_DML=False)
        report['separate_committed_business_witness'] = witness
        with control.product_catalog(cursor):
            _, _, _, _, catalog = product.runtime()
            before_catalog, before_data = catalog._catalog_rows(cursor), catalog._data(cursor)
            try:
                product.rollback_delta_preuse(cursor, state)
            except ValueError as error:
                if str(error) != product.USED_ERROR:
                    raise
                witness['actual_used_guard_error'] = str(error)
            else:
                raise AssertionError('S05_PARENT_USED_INVERSE_NOT_REFUSED')
            if catalog._catalog_rows(cursor) != before_catalog or catalog._data(cursor) != before_data:
                raise AssertionError('S05_USED_REFUSAL_CHANGED_CATALOG_DATA_OR_SEQUENCES')
        connection.rollback()
    report.update(status='PASS', actual_Native_cases=len(business.IDS), actual_two_session_races=0, actual_Auth_HTTP_cases=0,
        actual_browser_cases=0, used_guard_refused_before_DDL=True, report_business_DML=False,
        acceptance_requires_complete_outer_restore_and_all_five_package_gates=True,
        Afui_positive_HPP_zero_reimbursement_actual_coverage=False)
