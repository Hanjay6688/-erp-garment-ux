"""Unchanged eleven callbacks, actual source capture and committed used proof."""
from pathlib import Path
from hashlib import sha256
import importlib.util
import psycopg
from cp7_attendance_period_choice import composition as product
from cp7_attendance_period_choice import native_delta
from cp7_p21_current_chain_rehearsal_probe import helper
from cp7_catalog_state import exact_public_catalog
import cp6_bd_probe as financial_truth

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
LABEL = 'CP7_S03_ATTENDANCE_CHOICE_NATIVE11_CASES'
spec = importlib.util.spec_from_file_location('s03_native11_unchanged_prepared_business',
    ROOT / 'scripts/current-attendance-period-choice-qualification/cases.py')
business = importlib.util.module_from_spec(spec)
spec.loader.exec_module(business)


def require_local(connection, cursor):
    if connection.info.host not in ('localhost', '127.0.0.1') or connection.info.port != 54322:
        raise ValueError('S03_NATIVE11_LOCAL_DISPOSABLE_ONLY')
    if cursor.execute('select current_database()').fetchone() != ('cp6_rollback',):
        raise ValueError('S03_NATIVE11_DISPOSABLE_DATABASE_ONLY')


def retain_originals(native, report):
    destination = ROOT / 'cp6-proof/t3'
    destination.mkdir(parents=True, exist_ok=True)
    retained = []
    for name in (LABEL + '.json', LABEL + '_BUSINESS_DAY_FIRST_ATTEMPT.json'):
        path = native.r1.OUT / name
        if path.is_file():
            raw = path.read_bytes()
            (destination / name).write_bytes(raw)
            retained.append(dict(name=name, bytes=len(raw), sha256=sha256(raw).hexdigest()))
    report['strict_group_originals'] = retained


def sequence_prefix(before, after):
    if set(before) != set(after):
        raise ValueError('S03_NATIVE11_FULL_DATA_KEYSET_CHANGED')
    changes = {key: dict(before=before[key], after=after[key])
               for key in before if before[key] != after[key]}
    if any(not key.startswith('sequence:') for key in changes):
        raise ValueError('S03_NATIVE11_STRICT_CASES_PERSISTED_ROWS')
    return changes


def exercise(conn, cur, database, url, report, state):
    control, native = helper.control, helper.control.native
    require_local(conn, cur)
    if state['sources'] != product.sources():
        raise ValueError('S03_NATIVE11_EXACT_INSTALLED_STATE_REQUIRED')
    if (set(state['originals']) != set(native_delta.SIGNATURES)
            or len(state['originals']) != 13 or len(state['clones']) != 2
            or state['definitions'] != native_delta.patched(state['originals'])
            or state['clones'] != native_delta.clones(state['originals'])):
        raise ValueError('S03_NATIVE11_ACTUAL13_ORIGINALS_TWO_CLONES_REQUIRED')
    report.update(actual_Native_cases=0, required_Native_case_ids=list(business.IDS),
        actual_Auth_browser=False, actual_two_session_races=0,
        actual_installed_capture=dict(originals=state['originals'], definitions=state['definitions'],
            clones=state['clones'], actual_all22=state['after'], source_derived_local_ABI_used=False),
        production_go=False, independent_acceptance=False)
    conn.rollback()
    cur.close()
    conn.close()

    def verify(cursor):
        with control.product_catalog(cursor):
            return product.verify(cursor, state)

    def cases(cursor, today):
        # The strict runner adds its own ERP USAGE before invoking the factory.
        # Only that exact accepted overlay is physically removed/restored here.
        with control.product_catalog(cursor):
            planned = business.cases(cursor, today, state=state, evidence=report)
        if tuple(key for key, _ in planned) != business.IDS or len(planned) != 11:
            raise ValueError('S03_NATIVE11_EXACT_CALLBACK_IDS_REQUIRED')
        return planned

    try:
        with exact_public_catalog(native, retain_raw=True) as public:
            actual = native.strict_group(LABEL, cases, verify)
    finally:
        retain_originals(native, report)
    report.update(native=actual, public_catalog_observation=public)
    if (actual.get('counts') != {'PASS': 11} or actual.get('status') != 'PASS'
            or actual.get('planned_case_ids') != list(business.IDS)
            or set(actual.get('cases', {})) != set(business.IDS)
            or actual.get('complete_boundary_restored') is not True):
        raise ValueError('S03_NATIVE11_COMPLETE_ELEVEN_PASS_REQUIRED')

    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        require_local(connection, cursor)
        business.f.admin(cursor)
        with control.product_catalog(cursor):
            _, _, _, _, catalog = product.runtime()
            product.verify(cursor, state)
            after_strict = catalog._data(cursor)
            prefixes = sequence_prefix(state['preuse_data_and_sequences'], after_strict)
        report['strict_group_scope'] = dict(all_current_business_rows_restored=True,
            actual_all22_restored=True, observed_sequence_allocations=prefixes,
            sequence_reseed_performed=False, complete_sequence_restore_proved=False,
            complete_sequence_restore_requires='OUTER_FULL_DATABASE_BACKUP_RESTORE_AND_PACKAGE_GATES')
        connection.rollback()

        if not cursor.execute('select count(*) from erp.app_users').fetchone()[0]:
            business.f.hp.b.api.seed(cursor)
        cursor.execute('grant usage on schema erp to authenticated')  # unchanged SQL harness overlay only
        today = cursor.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        before_truth = financial_truth.all_truth(cursor)
        fixture, output, physical = business.pair(cursor, today)
        original_accrual = business.original_accrual(cursor, fixture)
        binding = business.source_hash(cursor, fixture)
        made = business.allocate(cursor, fixture, output)
        oracle = business.f.assert_pool(cursor, fixture, made, output)
        if business.original_accrual(cursor, fixture) != original_accrual or business.source_hash(cursor, fixture) != binding:
            raise ValueError('S03_NATIVE11_USED_WITNESS_CHANGED_ORIGINAL_ACCRUAL')
        after_truth = financial_truth.all_truth(cursor)
        if not financial_truth.truth_quiet(before_truth, after_truth):
            raise ValueError('S03_NATIVE11_USED_WITNESS_NEW_FINANCIAL_FINDING')
        cursor.execute('set constraints all immediate')
        cursor.execute('set constraints all deferred')
        connection.commit()  # A real choice and Native cost allocation, not a test row.
        with control.product_catalog(cursor):
            before_catalog, before_data = catalog._catalog_rows(cursor), catalog._data(cursor)
            try:
                product.rollback_delta_preuse(cursor, state)
            except ValueError as error:
                if str(error) != product.USED_ERROR:
                    raise
            else:
                raise AssertionError('S03_NATIVE11_USED_INVERSE_NOT_REFUSED')
            after_catalog, after_data = catalog._catalog_rows(cursor), catalog._data(cursor)
            if after_catalog != before_catalog or after_data != before_data:
                raise ValueError('S03_NATIVE11_USED_REFUSAL_CHANGED_ALL22_ROWS_SEQUENCES')
        connection.rollback()
    report.update(status='PASS', actual_Native_cases=11, used_guard_refused_before_DDL=True,
        committed_choice_and_allocation=made, independent_Native_pool_oracle=oracle,
        committed_fixture_source_period=str(fixture['day']), output_period=str(output),
        original_accrual_and_source_binding_unchanged=True,
        original_accrual=original_accrual, Native_financial_truth_before=before_truth,
        Native_financial_truth_after=after_truth, failure_evidence_preserved=True,
        used_inverse_refusal_before=dict(actual_all22=before_catalog, full_data_and_sequences=before_data),
        used_inverse_refusal_after=dict(actual_all22=after_catalog, full_data_and_sequences=after_data),
        acceptance_requires_complete_outer_restore_and_all_five_package_gates=True,
        source_derived_ABI_is_actual_runtime_capture=False, fresh_Auth_HTTP_race_browser_credit=0,
        full_S03_acceptance=False, production_go=False, independent_acceptance=False)
