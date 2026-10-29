"""Unchanged E17 callbacks plus a separately labelled committed E witness.

Import is inert. Only the root-selected disposable package caller executes SQL.
"""
from hashlib import sha256
from pathlib import Path
import importlib.util
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASE = 'CREDIT_E1_NATIVE17_AND_SEPARATE_COMMITTED_USED_INVERSE'
LABEL = 'CP7_CREDIT_E1_NATIVE17_CASES'
FIXTURE_PATHS = ('scripts', 'scripts/cp7_customer_credit/consumer',
                 'scripts/cp7_customer_credit/reconciliation/native', 'scripts/cp7_customer_credit/native',
                 'scripts/cp7_customer_credit/initial-settlement')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def require_local(connection, cursor):
    if connection.info.host not in ('localhost', '127.0.0.1') or connection.info.port != 54322:
        raise ValueError('E1_LOCAL_DISPOSABLE_PORT_ONLY')
    if cursor.execute('select current_database()').fetchone() != ('cp6_rollback',):
        raise ValueError('E1_DISPOSABLE_DATABASE_ONLY')


def scheduler_quiet(url):
    return load('e1_unchanged_vendor_scheduler_quiet', ROOT/'scripts/current-vendor-receivable-qualification/native_runner.py').scheduler_quiet(url)


def retain_originals(native, report):
    destination = ROOT/'cp6-proof/t3'; destination.mkdir(parents=True, exist_ok=True)
    retained = []
    for name in (LABEL+'.json', LABEL+'_BUSINESS_DAY_FIRST_ATTEMPT.json'):
        path = native.r1.OUT/name
        if path.is_file():
            raw = path.read_bytes(); (destination/name).write_bytes(raw)
            retained.append(dict(name=name, bytes=len(raw), sha256=sha256(raw).hexdigest()))
    report['strict_group_originals'] = retained


def committed_witness(url, state, business, product, control, financial_truth):
    import psycopg
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        require_local(conn, cur)
        native = business.native
        if not cur.execute('select count(*) from erp.app_users').fetchone()[0]:
            native.b.api.seed(cur)
        cur.execute('grant usage on schema erp to authenticated')  # unchanged isolated Native harness capability only
        today = cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
        pair = business.fixture.prepare(cur, today)
        applied, _, _ = business.basic.apply(cur, pair, '80.00')
        source = pair['source']['f']
        source_facts = native.note.unchanged_facts(cur, source['sale'])
        source_payment = native.payment_snapshot(cur, source['payment'])
        physical = business.physical(cur, pair)
        events = native._array(cur, 'cp7_credit.consumption_events', 'true', ())
        journals = {e['journal_id']: native.journal(cur, e['journal_id']) for e in events['document']}
        accounts = native.cmd.accounts(cur)
        cost_ids = [native.cmd.mapping(cur, name) for name in ('FG_INVENTORY', 'COGS', 'WIP')]
        before_truth = financial_truth.all_truth(cur)
        original = pair['target']['sale']
        made, payload, version, basis, request = business.post(cur, pair, '110.00')
        actual = business.profile(cur, pair, original, made['sale_id'], '550.00', '80.00', '120.00')
        native.b.api.admin(cur)
        if business.physical(cur, pair) != physical:
            raise AssertionError('E1_WITNESS_CHANGED_STOCK_HPP_OR_CASH')
        if native.note.unchanged_facts(cur, source['sale']) != source_facts or native.payment_snapshot(cur, source['payment']) != source_payment:
            raise AssertionError('E1_WITNESS_CHANGED_ORIGINAL_SOURCE_SALE_OR_PAYMENT')
        if native._array(cur, 'cp7_credit.consumption_events', 'true', ()) != events:
            raise AssertionError('E1_WITNESS_MUTATED_OR_DUPLICATED_MONEY_EVENTS')
        if any(native.journal(cur, ident) != raw for ident, raw in journals.items()):
            raise AssertionError('E1_WITNESS_MUTATED_ORIGINAL_CONSUMER_JOURNAL')
        after_accounts = native.cmd.accounts(cur)
        if any(accounts.get(key, 0) != after_accounts.get(key, 0) for key in cost_ids):
            raise AssertionError('E1_WITNESS_CHANGED_FG_COGS_OR_WIP')
        after_truth = financial_truth.all_truth(cur)
        if not financial_truth.truth_quiet(before_truth, after_truth):
            raise AssertionError(('E1_WITNESS_NEW_FINANCIAL_TRUTH_ISSUE', before_truth, after_truth))
        row = cur.execute('select operation_id::text,source_sale_id::text,replacement_sale_id::text from cp7_credit_note_carry_de.operations_v1 where request_id=%s', (request,)).fetchall()
        if len(row) != 1 or row[0][1:] != (original, made['sale_id']):
            raise AssertionError('E1_WITNESS_ACTUAL_ASSIGNMENT_NOT_COMMITTED')
        cur.execute('set constraints all immediate'); cur.execute('set constraints all deferred')
        conn.commit()
        result = dict(status='NATIVE_E_CORRECTION_COMMITTED', scope='SEPARATE_USED_INVERSE_WITNESS_ZERO_NATIVE17_CREDIT',
            actual_E_response=made, actual_profile=actual, original_APPLY=applied,
            original_money_events=events, original_money_journals=journals, unchanged_physical_HPP_and_cash=physical,
            same_original_money_event_and_journal_preserved_by_unchanged_E_post=True,
            original_source_sale_and_payment_immutable=True, physical_HPP_cash_and_cost_GL_unchanged=True,
            financial_truth_before=before_truth, financial_truth_after=after_truth,
            E_Native_case_credit=0, real_Auth=False)
        with control.product_catalog(cur):
            *_, catalog = product.runtime()
            before_catalog, before_data = catalog._catalog_rows(cur), catalog._data(cur)
            try:
                product.rollback_delta_preuse(cur, state)
            except ValueError as error:
                if str(error) != product.USED_ERROR:
                    raise
                result['actual_used_inverse_error'] = str(error)
            else:
                raise AssertionError('E1_USED_INVERSE_WAS_NOT_REFUSED')
            if catalog._catalog_rows(cur) != before_catalog or catalog._data(cur) != before_data:
                raise AssertionError('E1_USED_INVERSE_REFUSAL_CHANGED_CATALOG_DATA_OR_SEQUENCES')
        conn.rollback()
        return result


def exercise(conn, cur, database, url, report, state):
    for relative in FIXTURE_PATHS:
        sys.path.insert(0, str(ROOT/relative))
    from cp7_credit_correction_de import e_cases as business, e_composition as product
    from cp7_p21_current_chain_rehearsal_probe import helper
    from cp7_catalog_state import exact_public_catalog
    import cp6_bd_probe as financial_truth
    gate = load('e1_actual_exact_group_gate', HERE/'gate.py')
    plan = load('e1_actual_unchanged_plan', HERE/'plan.py')
    require_local(conn, cur)
    if tuple(business.IDS) != plan.E_IDS or state['sources'] != product.sources():
        raise ValueError('E1_EXACT_INSTALLED_CHILD_AND_SEVENTEEN_CASES_REQUIRED')
    conn.rollback(); cur.close(); conn.close()
    control, native = helper.control, helper.control.native
    report.update(status='INCOMPLETE', actual_Native_cases=0, actual_two_session_races=0,
        actual_Auth_HTTP_cases=0, actual_browser_cases=0, real_Auth=False,
        qualification_scope='E1_NATIVE17_ONLY_ABOVE_RETAINED_QUALIFIED_D1',
        D_complete=False, E_complete=False, production_go=False, independent_acceptance=False)

    def verify(cursor):
        with control.product_catalog(cursor):
            return product.verify(cursor, state)

    try:
        with exact_public_catalog(native, retain_raw=True) as public:
            actual = native.strict_group(LABEL, business.cases, verify)
    finally:
        retain_originals(native, report)
    report.update(native=actual, public_catalog_observation=public)
    gate.exact_group(actual, plan.E_IDS, 17)
    report['separate_committed_E_witness'] = committed_witness(url, state, business, product, control, financial_truth)
    report.update(status='PASS', actual_Native_cases=17, used_guard_refused_before_DDL=True,
        fresh_D1_cases=0, retained_D1_Native13_reexecuted=False,
        acceptance_requires_complete_outer_restore_and_five_package_gates=True,
        unchanged_seventeen_business_callbacks_and_originals=True)
