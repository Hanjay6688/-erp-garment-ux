#!/usr/bin/env python3
"""Two real receipt/invoice serialization orders on fresh native S clones."""
import json
import os
import threading
import uuid
from pathlib import Path

import psycopg

import cp6_v2620e_counterexample_regression as base
import cp6_v2620h_maintenance_rollback_matrix as matrix
import cp6_v2620r_runtime as runtime

ROOT = Path('cp6-proof/R_RECEIPT_INVOICE_NATIVE_RACES')
CASES = ('INVOICE_POST_FIRST', 'RECEIPT_REVERSE_FIRST')
HELPERS = tuple(Path('supabase/tests') / name for name in (
    'cp6_subledger_exact_cent.sql', 'cp6_supplier_cent_lifecycle.sql',
    'cp6_supplier_return_document_allocation.sql',
    'cp6_supplier_invoice_exact_quantity.sql', 'cp6_receipt_invoice_dependency.sql',
))


def session(name):
    conn = psycopg.connect(matrix.CLONE, application_name='cp6-r-' + name)
    with conn.cursor() as cur:
        cur.execute("set timezone='UTC';set statement_timeout='30s';set lock_timeout='20s'")
        for source in HELPERS:
            cur.execute(source.read_text(), prepare=False)
    conn.commit()
    return conn


def operator(cur):
    matrix.legacy.operator(cur)
    cur.execute("select set_config('app.change_reason','R native receipt/invoice race',true)")


def run_case(name, folder):
    matrix.command(['bash', 'scripts/clone-cp6-disposable-database.sh', matrix.SOURCE,
        matrix.MAINTENANCE, matrix.CLONE, 'cp6_rollback', matrix.CONTAINER,
        str(folder / 'PHYSICAL_BOUNDARY')], folder / 'clone.log')
    matrix.verify_setup_source('S')
    with session('fixture') as conn, conn.cursor() as cur:
        if len(runtime.verified_successor(cur)) != 3:
            raise AssertionError('R_RACE_RUNTIME_MISMATCH')
        operator(cur); base.load_fixture_foundation(cur); operator(cur)
        purchase = base.one(cur, 'select pg_temp.o_purchase(array[1]::numeric[],10000,false)')
        draft = base.one(cur, 'select pg_temp.r_invoice_draft(array[%s]::uuid[])', (purchase,))
        invoice = draft['supplier_invoice_id']
        if base.one(cur, 'select pg_temp.m_report()') != 'READY':
            raise AssertionError('R_RACE_FIXTURE_NOT_READY')
        conn.commit()
    post = ('select erp.post_material_supplier_invoice_v2(%s,%s,%s,%s)',
        (invoice, uuid.uuid4(), int(draft['row_version']), 'R concurrent invoice post'),
        'erp.post_material_supplier_invoice_v2')
    reverse = ('select erp.reverse_material_purchase(%s,%s)',
        (purchase, 'R concurrent receipt reversal'), 'erp.reverse_material_purchase')
    first_action, second_action = (post, reverse) if name == 'INVOICE_POST_FIRST' else (reverse, post)
    first = session('first'); second = session('second')
    outcome = {}; thread = None
    try:
        with first.cursor() as cur:
            operator(cur)
            base.one(cur, first_action[0], first_action[1])
            winner_boundary = base.one(cur, 'select pg_temp.o_boundary()')
        # The completed real writer holds its natural receipt row lock. No
        # manual prelock, modified function/trigger, advisory gate or retry.
        def contender():
            try:
                with second.cursor() as cur:
                    operator(cur)
                    base.one(cur, second_action[0], second_action[1])
                second.commit(); outcome.update(status='COMMITTED')
            except psycopg.Error as exc:
                second.rollback()
                outcome.update(status='REJECTED', sqlstate=exc.sqlstate,
                    message=exc.diag.message_primary)
            except Exception as exc:
                second.rollback(); outcome.update(status='FAIL', error_type=type(exc).__name__)
        thread = threading.Thread(target=contender, daemon=True); thread.start()
        with psycopg.connect(matrix.CLONE, autocommit=True, application_name='cp6-r-observer') as observer:
            def observation():
                row = observer.execute('select pid,state,wait_event_type,wait_event,pg_blocking_pids(pid),query '
                    'from pg_stat_activity where pid=%s', (second.info.backend_pid,)).fetchone()
                if row and first.info.backend_pid in row[4] and row[1] == 'active' and row[2] == 'Lock':
                    return {'pid': row[0], 'state': row[1], 'wait_event_type': row[2],
                        'wait_event': row[3], 'blocking_pids': row[4],
                        'query_kind': second_action[2],
                        'real_business_query_observed': second_action[2] in row[5]}
                return None
            blocking = matrix.wait_for(observation, 12)
            if not blocking['real_business_query_observed'] or outcome:
                raise AssertionError('R_RACE_DID_NOT_BLOCK_IN_REAL_BUSINESS_CALL')
        first.commit(); thread.join(25)
        if thread.is_alive():
            raise AssertionError('R_RACE_CONTENDER_DID_NOT_FINISH')
        expected_message = ('Reverse posted supplier invoices before reversing this receipt'
            if name == 'INVOICE_POST_FIRST' else 'Source purchase must be POSTED')
        if outcome != {'status': 'REJECTED', 'sqlstate': 'P0001', 'message': expected_message}:
            raise AssertionError('R_RACE_DEPENDENCY_ORACLE_FAILED')
        with session('reconcile') as conn, conn.cursor() as cur:
            operator(cur)
            actual = base.one(cur, 'select pg_temp.q_state(%s)', (purchase,))
            report = base.one(cur, 'select pg_temp.m_report()')
            purchase_status = base.one(cur, 'select status from erp.material_purchase_headers where id=%s', (purchase,))
            invoice_status = base.one(cur, 'select status from erp.material_supplier_invoices where id=%s', (invoice,))
            unchanged = base.one(cur, 'select pg_temp.o_boundary()') == winner_boundary
            posted_first = name == 'INVOICE_POST_FIRST'
            expected = ('POSTED', 'POSTED', 1, 10000, 10000, 0) if posted_first else ('REVERSED', 'DRAFT', 0, 0, 0, 0)
            observed = (purchase_status, invoice_status, actual['stock'], actual['ledger']['ap'],
                actual['ledger']['inventory'], actual['ledger']['grni'])
            if observed != expected or actual['ledger']['variance'] != 0 or report != 'READY' or not unchanged:
                raise AssertionError('R_RACE_BUSINESS_RESIDUE_OR_AMOUNT_FAILED')
        return {'case': name, 'status': 'PASS', 'first_pid': first.info.backend_pid,
            'second_pid': second.info.backend_pid, 'blocking_observation': blocking,
            'first_real_function_completed_before_commit': True, 'connections_distinct': True,
            'manual_prelock_count': 0, 'retry_count': 0, 'contender': outcome,
            'actual': actual, 'purchase_status': purchase_status, 'invoice_status': invoice_status,
            'report': report, 'contender_business_boundary_unchanged': unchanged,
            'engine': 'NATIVE_POSTGRESQL', 'authority': 'OWNER_CLAIMS_IN_TRUSTED_SQL_SESSION'}
    finally:
        first.rollback(); first.close()
        if thread is not None and thread.is_alive():
            second.cancel(); thread.join(5)
        second.close()


def main():
    expected = (matrix.SOURCE, matrix.MAINTENANCE, matrix.CLONE, matrix.CONTAINER, 'cp6_rollback')
    if tuple(os.environ.get(k) for k in ('PGURL', 'CP6_MAINTENANCE_PGURL', 'CP6_ROLLBACK_RACE_PGURL',
        'CP6_DATABASE_CONTAINER', 'CP6_MAINTENANCE_CONFIRM_DATABASE')) != expected:
        raise SystemExit('R_RACE_DISPOSABLE_ENDPOINT_CONFIRMATION_REQUIRED')
    ROOT.mkdir(parents=True, exist_ok=True)
    report = {'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'), 'production_go': False,
        'classification': 'NATIVE_POSTGRESQL_REAL_RECEIPT_INVOICE_LOCKS',
        'source_generation': 'S', 'cases': []}
    for name in CASES:
        folder = ROOT / name; folder.mkdir()
        try:
            result = run_case(name, folder)
        except Exception as exc:
            result = {'case': name, 'status': 'FAIL', 'error_code': 'R_NATIVE_RACE_FAILED',
                'error_type': type(exc).__name__, 'sqlstate': getattr(exc, 'sqlstate', None)}
        finally:
            matrix.legacy.drop_clone()
        result['remaining_clone_databases'] = 0
        (folder / 'result.json').write_text(json.dumps(result, indent=2, default=str) + '\n')
        report['cases'].append(result)
    report['status'] = 'PASS' if len(report['cases']) == 2 and all(c['status'] == 'PASS' for c in report['cases']) else 'FAIL'
    (ROOT / 'manifest.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
    print(json.dumps({'status': report['status'], 'case_count': len(report['cases']), 'production_go': False}))
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
