"""Thirteen predeclared D1 Native cases plus a real committed used witness.

The outer unchanged package owns install, preuse inverse and complete backup
restoration. These cases use authenticated SQL, never real Auth or a browser.
"""
from pathlib import Path
from hashlib import sha256
import sys
import psycopg

ROOT = Path(__file__).resolve().parents[2]
for relative in ('scripts', 'scripts/cp7_customer_credit/consumer',
                 'scripts/cp7_customer_credit/reconciliation/native',
                 'scripts/cp7_customer_credit/native',
                 'scripts/cp7_customer_credit/initial-settlement'):
    sys.path.insert(0, str(ROOT / relative))

from cp7_credit_correction_de import cases as business, composition as product
from cp7_p21_current_chain_rehearsal_probe import helper
from cp7_catalog_state import exact_public_catalog
import cp6_bd_probe as financial_truth

LABEL = 'CP7_CREDIT_DE_NATIVE13_CASES'


def require_local(connection, cursor):
    assert connection.info.host in ('localhost', '127.0.0.1') and connection.info.port == 54322, 'D1_LOCAL_DISPOSABLE_ONLY'
    assert cursor.execute('select current_database()').fetchone() == ('cp6_rollback',), 'D1_DISPOSABLE_DATABASE_ONLY'


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


def exercise(conn, cur, database, url, report, state):
    control = helper.control
    native = control.native
    require_local(conn, cur)
    assert state['sources'] == product.sources(), 'D1_EXACT_CURRENT_INSTALLATION_REQUIRED'
    conn.rollback()
    cur.close()
    conn.close()

    def verify(cursor):
        with control.product_catalog(cursor):
            return product.verify(cursor, state)

    try:
        with exact_public_catalog(native, retain_raw=True) as public:
            actual = native.strict_group(LABEL, business.cases, verify)
    finally:
        retain_originals(native, report)
    report.update(native=actual, public_catalog_observation=public,
                  actual_Native_cases=0, actual_Auth_browser=False, actual_two_session_races=0,
                  qualification_scope='D1_NATIVE_ONLY', D_complete=False, E_complete=False,
                  production_go=False, independent_acceptance=False)
    assert actual.get('counts') == {'PASS': 13} and set(actual.get('cases', {})) == set(business.IDS), actual
    assert actual.get('status') == 'PASS' and actual.get('complete_boundary_restored') is True, actual

    # The qualification must commit an actual D1 correction before proving that
    # inverse DDL cannot erase it. A changed fixture alone would be insufficient.
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        require_local(connection, cursor)
        if not cursor.execute('select count(*) from erp.app_users').fetchone()[0]:
            business.native.b.api.seed(cursor)
        cursor.execute('grant usage on schema erp to authenticated')  # isolated harness grant, not product authority
        today = cursor.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
        pair = business.fixture.prepare(cursor, today)
        source = pair['source']['f']
        documents = (source, pair['target'])
        lot_ids = [f['lot'] for f in documents]
        stock_query = "select product_id,lot_id,location_id,quality_grade,physical_qty,reserved_qty,available_qty from cp7_fg.positions('',true) where lot_id=any(%s::uuid[]) order by product_id,lot_id,location_id,quality_grade"
        positions = cursor.execute(stock_query, (lot_ids,)).fetchall()
        hpp = cursor.execute('select lot_id::text,total_cost::text,hpp_per_pcs::text from erp.v_current_hpp where lot_id=any(%s::uuid[]) order by lot_id', (lot_ids,)).fetchall()
        hpp_history = business.native._array(cursor, 'erp.hpp_versions', 'lot_id=any(%s::uuid[])', (lot_ids,))
        alignment_query = 'select cp7_credit.source_first_nonpo_hpp_alignment_v1(cp7_credit.source_native_snapshot_v1(%s))'
        alignment = cursor.execute(alignment_query, (source['sale'],)).fetchone()[0]
        sale_fact = business.native.note.unchanged_facts(cursor, source['sale'])
        payment_fact = business.native.payment_snapshot(cursor, source['payment'])
        accounts = business.native.cmd.accounts(cursor)
        cost_accounts = [business.native.cmd.mapping(cursor, name) for name in ('FG_INVENTORY', 'COGS', 'WIP')]
        before_truth = financial_truth.all_truth(cursor)
        made, payload, version, quote, request = business.post(cursor, pair)
        truth = business.profile(cursor, pair, '250.00', '250.00')
        business.native.b.api.admin(cursor)
        assert cursor.execute(stock_query, (lot_ids,)).fetchall() == positions, 'D1_PHYSICAL_RESERVATION_OR_AVAILABLE_STOCK_CHANGED'
        assert cursor.execute('select lot_id::text,total_cost::text,hpp_per_pcs::text from erp.v_current_hpp where lot_id=any(%s::uuid[]) order by lot_id', (lot_ids,)).fetchall() == hpp, 'D1_STATIC_HPP_CHANGED'
        assert business.native._array(cursor, 'erp.hpp_versions', 'lot_id=any(%s::uuid[])', (lot_ids,)) == hpp_history, 'D1_HPP_HISTORY_CHANGED'
        assert cursor.execute(alignment_query, (source['sale'],)).fetchone()[0] == alignment, 'D1_HPP_BOOK_ALIGNMENT_CHANGED'
        assert business.native.note.unchanged_facts(cursor, source['sale']) == sale_fact
        assert business.native.payment_snapshot(cursor, source['payment']) == payment_fact
        after_accounts = business.native.cmd.accounts(cursor)
        assert all(accounts.get(account, 0) == after_accounts.get(account, 0) for account in cost_accounts), 'D1_COST_GL_CHANGED'
        after_truth = financial_truth.all_truth(cursor)
        assert financial_truth.truth_quiet(before_truth, after_truth), (before_truth, after_truth)
        assert cursor.execute('select count(*) from cp7_credit_correction_de.operations_v1 where request_id=%s and return_id=%s and replacement_id=%s', (request, payload['return_id'], made['return_id'])).fetchone()[0] == 1
        cursor.execute('set constraints all immediate')
        cursor.execute('set constraints all deferred')
        connection.commit()
        with control.product_catalog(cursor):
            *_, catalog = product.runtime()
            before = catalog._catalog_rows(cursor)
            data = catalog._data(cursor)
            try:
                product.rollback_delta_preuse(cursor, state)
            except ValueError as error:
                assert str(error) == product.USED_ERROR, str(error)
            else:
                raise AssertionError('D1_USED_INVERSE_NOT_REFUSED')
            assert catalog._catalog_rows(cursor) == before and catalog._data(cursor) == data
        connection.rollback()
    report.update(status='PASS', actual_Native_cases=13, used_guard_refused_before_DDL=True,
                  committed_correction=made, committed_source_truth=truth,
                  unchanged_physical_stock_HPP_cost_GL_and_original_sale_payment=True,
                  Native_financial_truth_before=before_truth, Native_financial_truth_after=after_truth,
                  failure_evidence_preserved=True, acceptance_requires_complete_outer_restore_and_package=True,
                  new_money_or_HPP_engine_created=False, D_complete=False, E_complete=False)
