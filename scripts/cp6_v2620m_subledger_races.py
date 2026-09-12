#!/usr/bin/env python3
"""Three real business-lock schedules on separate fresh disposable M clones."""
import json
import os
import threading
import uuid
from decimal import Decimal
from pathlib import Path

import psycopg

import cp6_v2620e_counterexample_regression as base
import cp6_v2620h_maintenance_rollback_matrix as matrix
import cp6_v2620m_runtime as runtime
from cp6_v2620m_subledger_regression import SOURCE

ROOT = Path('cp6-proof/M_SUBLEDGER_NATIVE_RACES')
CASES = ('SUPPLIER_CAPACITY', 'OPENING_LAST_CENT', 'OPENING_CORRECTION_VS_SETTLEMENT')
SOURCE_GENERATION = os.environ.get('CP6_M_RACE_SOURCE_GENERATION', 'M')


def session(name):
    conn = psycopg.connect(matrix.CLONE, application_name='cp6-m-' + name)
    with conn.cursor() as cur:
        cur.execute("set timezone='UTC';set statement_timeout='30s';set lock_timeout='20s'")
        cur.execute(SOURCE.read_text(), prepare=False)
    conn.commit()
    return conn


def operator(cur):
    matrix.legacy.operator(cur)
    cur.execute("select set_config('app.change_reason','M independent native money race',true)")


def run_case(name, folder):
    matrix.command(['bash', 'scripts/clone-cp6-disposable-database.sh', matrix.SOURCE,
        matrix.MAINTENANCE, matrix.CLONE, 'cp6_rollback', matrix.CONTAINER,
        str(folder / 'PHYSICAL_BOUNDARY')], folder / 'clone.log')
    matrix.verify_setup_source(SOURCE_GENERATION)
    with session('fixture') as conn, conn.cursor() as cur:
        if len(runtime.verified_successor(cur)) != 15:
            raise AssertionError('M_RACE_RUNTIME_MISMATCH')
        operator(cur); base.load_fixture_foundation(cur); operator(cur)
        fixture = base.one(cur, 'select pg_temp.m_purchase()' if name == 'SUPPLIER_CAPACITY'
            else 'select pg_temp.m_opening()')
        item = None if name == 'SUPPLIER_CAPACITY' else base.one(cur,
            'select opening_item_id from erp.opening_subledger_balances where id=%s', (fixture,))
        first_id, second_id = uuid.uuid4(), uuid.uuid4()
        cash = base.one(cur, 'select id from erp.cash_accounts where is_active order by cash_account_code limit 1')
        if name == 'SUPPLIER_CAPACITY':
            for ident, amount in ((first_id, Decimal(60)), (second_id, Decimal('40.01'))):
                cur.execute("insert into erp.supplier_payments(id,purchase_id,payment_number,payment_date,amount,cash_account_id,status) "
                    "values(%s,%s,%s,'2026-09-02',%s,%s,'DRAFT')", (ident, fixture, 'M-RACE-' + str(ident), amount, cash))
        else:
            payments = ((first_id, Decimal('99.99')), (second_id, Decimal('.01'))) if name == 'OPENING_LAST_CENT' else ((second_id, Decimal(100)),)
            for ident, amount in payments:
                cur.execute("insert into erp.opening_subledger_settlements(id,balance_id,settlement_number,physical_at,amount,cash_account_id,status) "
                    "values(%s,%s,%s,'2026-09-02T12:00:00Z',%s,%s,'DRAFT')", (ident, fixture, 'M-RACE-' + str(ident), amount, cash))
        contender_function = 'erp.post_supplier_payment' if name == 'SUPPLIER_CAPACITY' else 'erp.post_opening_subledger_settlement'
        contender_query = 'select ' + contender_function + '(%s)'
        conn.commit()
    first = session('first'); second = session('second')
    outcome = {}; thread = None
    try:
        with first.cursor() as cur:
            operator(cur)
            if name == 'SUPPLIER_CAPACITY':
                base.one(cur, 'select erp.post_supplier_payment(%s)', (first_id,))
            elif name == 'OPENING_LAST_CENT':
                base.one(cur, 'select erp.post_opening_subledger_settlement(%s)', (first_id,))
            else:
                base.one(cur, "select erp.post_opening_financial_correction(%s,60,'M concurrent lawful correction','2026-09-02')", (item,))
        # No prelock, advisory gate, trigger, retry or synthetic function is
        # installed. The first real business call owns its natural row locks.
        def contender():
            try:
                with second.cursor() as cur:
                    operator(cur)
                    base.one(cur, contender_query, (second_id,))
                second.commit(); outcome.update(status='COMMITTED')
            except psycopg.Error as exc:
                second.rollback(); outcome.update(status='REJECTED', sqlstate=exc.sqlstate)
            except Exception as exc:
                second.rollback(); outcome.update(status='FAIL', error_type=type(exc).__name__)
        thread = threading.Thread(target=contender, daemon=True); thread.start()
        with psycopg.connect(matrix.CLONE, autocommit=True, application_name='cp6-m-observer') as observer:
            def observation():
                with observer.cursor() as cur:
                    cur.execute('select pid,state,wait_event_type,wait_event,pg_blocking_pids(pid),query '
                        'from pg_stat_activity where pid=%s', (second.info.backend_pid,))
                    row = cur.fetchone()
                    if row and first.info.backend_pid in row[4] and row[1] == 'active' and row[2] == 'Lock':
                        return {'pid': row[0], 'state': row[1], 'wait_event_type': row[2],
                            'wait_event': row[3], 'blocking_pids': row[4],
                            'query_kind': contender_function,
                            'real_business_query_observed': contender_function in row[5]}
                    return None
            blocking = matrix.wait_for(observation, 12)
            if not blocking['real_business_query_observed'] or outcome:
                raise AssertionError('M_RACE_DID_NOT_BLOCK_IN_REAL_BUSINESS_CALL')
        first.commit(); thread.join(25)
        if thread.is_alive():
            raise AssertionError('M_RACE_CONTENDER_DID_NOT_FINISH')
        wanted = 'COMMITTED' if name == 'OPENING_LAST_CENT' else 'REJECTED'
        if outcome.get('status') != wanted or (wanted == 'REJECTED' and outcome.get('sqlstate') != 'P0001'):
            raise AssertionError('M_RACE_CAPACITY_ORACLE_FAILED')
        with session('reconcile') as conn, conn.cursor() as cur:
            operator(cur)
            actual = base.one(cur, 'select pg_temp.m_purchase_state(%s)' if name == 'SUPPLIER_CAPACITY'
                else 'select pg_temp.m_open_state(%s)', (fixture,))
            if actual['report'] != 'READY':
                raise AssertionError('M_RACE_FALSE_BLOCKED')
            if name == 'SUPPLIER_CAPACITY':
                valid = actual['paid'] == 60 and actual['ap_gl'] == 40 and actual['status'] == 'PARTIAL'
                drafts = base.one(cur, "select count(*) from erp.supplier_payments where purchase_id=%s and status='DRAFT'", (fixture,))
            else:
                valid = ((actual['original'], actual['settled'], actual['remaining'], actual['status']) ==
                    ((100, 100, 0, 'SETTLED') if name == 'OPENING_LAST_CENT' else (60, 0, 60, 'OPEN')))
                drafts = base.one(cur, "select count(*) from erp.opening_subledger_settlements where balance_id=%s and status='DRAFT'", (fixture,))
            expected_drafts = 0 if wanted == 'COMMITTED' else 1
            if not valid or drafts != expected_drafts:
                raise AssertionError('M_RACE_BUSINESS_RESIDUE_OR_AMOUNT_FAILED')
        return {'case': name, 'status': 'PASS', 'first_pid': first.info.backend_pid,
            'second_pid': second.info.backend_pid, 'blocking_observation': blocking,
            'first_real_function_completed_before_commit': True, 'connections_distinct': True,
            'manual_prelock_count': 0, 'retry_count': 0, 'contender': outcome,
            'actual': actual, 'preexisting_unposted_drafts': drafts, 'expected_unposted_drafts': expected_drafts,
            'unexpected_draft_residue': 0, 'engine': 'NATIVE_POSTGRESQL'}
    finally:
        first.rollback(); first.close()
        if thread is not None and thread.is_alive():
            second.cancel(); thread.join(5)
        second.close()


def main():
    if SOURCE_GENERATION not in ('M', 'N', 'O', 'P', 'Q', 'R'):
        raise SystemExit('M_RACE_UNSUPPORTED_SOURCE_GENERATION')
    expected = (matrix.SOURCE, matrix.MAINTENANCE, matrix.CLONE, matrix.CONTAINER, 'cp6_rollback')
    if tuple(os.environ.get(k) for k in ('PGURL', 'CP6_MAINTENANCE_PGURL', 'CP6_ROLLBACK_RACE_PGURL',
        'CP6_DATABASE_CONTAINER', 'CP6_MAINTENANCE_CONFIRM_DATABASE')) != expected:
        raise SystemExit('M_RACE_DISPOSABLE_ENDPOINT_CONFIRMATION_REQUIRED')
    ROOT.mkdir(parents=True, exist_ok=True)
    report = {'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'), 'production_go': False,
        'classification': 'NATIVE_POSTGRESQL_REAL_SUBLEDGER_BUSINESS_LOCKS',
        'source_generation': SOURCE_GENERATION, 'cases': []}
    for name in CASES:
        folder = ROOT / name; folder.mkdir()
        try:
            result = run_case(name, folder)
        except Exception as exc:
            result = {'case': name, 'status': 'FAIL', 'error_code': 'M_NATIVE_RACE_FAILED',
                'error_type': type(exc).__name__, 'sqlstate': getattr(exc, 'sqlstate', None)}
        finally:
            matrix.legacy.drop_clone()
        result['remaining_clone_databases'] = 0
        (folder / 'result.json').write_text(json.dumps(result, indent=2, default=str) + '\n')
        report['cases'].append(result)
    report['status'] = 'PASS' if len(report['cases']) == 3 and all(c['status'] == 'PASS' for c in report['cases']) else 'FAIL'
    (ROOT / 'manifest.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
    print(json.dumps({'status': report['status'], 'case_count': len(report['cases']), 'production_go': False}))
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
