#!/usr/bin/env python3
"""Two materials sharing one adjustment: both native orders and writer abort."""
import json
import os
import threading
from pathlib import Path

import psycopg

import cp6_v2620e_counterexample_regression as base
import cp6_v2620h_maintenance_rollback_matrix as matrix
import cp6_v2620t_runtime as runtime

ROOT = Path('cp6-proof/T_MATERIAL_ADJUSTMENT_NATIVE_RACES')
CASES = ('MATERIAL_A_FIRST', 'MATERIAL_B_FIRST', 'MATERIAL_A_ABORT')
HELPERS = tuple(Path('supabase/tests') / name for name in (
    'cp6_subledger_exact_cent.sql', 'cp6_supplier_cent_lifecycle.sql',
    'cp6_supplier_return_document_allocation.sql',
    'cp6_material_adjustment_revaluation.sql',
))


def session(name):
    conn = psycopg.connect(matrix.CLONE, application_name='cp6-t-' + name)
    with conn.cursor() as cur:
        cur.execute("set timezone='UTC';set statement_timeout='35s';set lock_timeout='25s'")
        for source in HELPERS:
            cur.execute(source.read_text(), prepare=False)
    conn.commit()
    return conn


def operator(cur):
    matrix.legacy.operator(cur)
    cur.execute("select set_config('app.change_reason','T native shared adjustment race',true)")


def run_case(name, folder):
    matrix.command(['bash', 'scripts/clone-cp6-disposable-database.sh', matrix.SOURCE,
        matrix.MAINTENANCE, matrix.CLONE, 'cp6_rollback', matrix.CONTAINER,
        str(folder / 'PHYSICAL_BOUNDARY')], folder / 'clone.log')
    matrix.verify_setup_source('U')
    with session('fixture') as conn, conn.cursor() as cur:
        if len(runtime.verified_successor(cur)) != 6:
            raise AssertionError('T_RACE_RUNTIME_MISMATCH')
        operator(cur); base.load_fixture_foundation(cur); operator(cur)
        fixture = base.one(cur, 'select pg_temp.t_multi_fixture()')
        if base.one(cur, 'select pg_temp.m_report()') != 'READY':
            raise AssertionError('T_RACE_FIXTURE_NOT_READY')
        conn.commit()
    first_key, second_key = ('correction_b', 'correction_a') if name == 'MATERIAL_B_FIRST' else ('correction_a', 'correction_b')
    first = session('first'); second = session('second')
    outcome = {}; thread = None
    try:
        with first.cursor() as cur:
            operator(cur)
            base.one(cur, 'select erp.post_material_purchase_cost_correction(%s)', (fixture[first_key],))
        # The real writer has finished, and holds only locks from its business
        # transaction. Observe the actual blocking location; never prelock it.
        def contender():
            try:
                with second.cursor() as cur:
                    operator(cur)
                    base.one(cur, 'select erp.post_material_purchase_cost_correction(%s)', (fixture[second_key],))
                second.commit(); outcome.update(status='COMMITTED')
            except psycopg.Error as exc:
                second.rollback()
                outcome.update(status='REJECTED', sqlstate=exc.sqlstate,
                    message=exc.diag.message_primary)
            except Exception as exc:
                second.rollback(); outcome.update(status='FAIL', error_type=type(exc).__name__)
        thread = threading.Thread(target=contender, daemon=True); thread.start()
        with psycopg.connect(matrix.CLONE, autocommit=True, application_name='cp6-t-observer') as observer:
            def observation():
                row = observer.execute('select pid,state,wait_event_type,wait_event,pg_blocking_pids(pid),query '
                    'from pg_stat_activity where pid=%s', (second.info.backend_pid,)).fetchone()
                if row and first.info.backend_pid in row[4] and row[1] == 'active' and row[2] == 'Lock':
                    return {'pid': row[0], 'state': row[1], 'wait_event_type': row[2],
                        'wait_event': row[3], 'blocking_pids': row[4],
                        'query_kind': 'erp.post_material_purchase_cost_correction',
                        'real_business_query_observed': 'erp.post_material_purchase_cost_correction' in row[5]}
                return None
            blocking = matrix.wait_for(observation, 12)
            if not blocking['real_business_query_observed'] or outcome:
                raise AssertionError('T_RACE_DID_NOT_BLOCK_IN_REAL_BUSINESS_CALL')
        if name == 'MATERIAL_A_ABORT':
            first.rollback()
        else:
            first.commit()
        thread.join(30)
        if thread.is_alive() or outcome != {'status': 'COMMITTED'}:
            raise AssertionError('T_RACE_CONTENDER_FAILED: ' + json.dumps(outcome))
        with session('reconcile') as conn, conn.cursor() as cur:
            operator(cur)
            actual = base.one(cur, 'select pg_temp.t_delta(%s::jsonb,pg_temp.t_ledger())',
                (json.dumps(fixture['before']),))
            # Expected document endpoints, independently from T's private state.
            expected = base.one(cur, "select jsonb_build_object('AP_SUPPLIER',%s::numeric,"
                "'MATERIAL_INVENTORY',%s::numeric,'OTHER_EXPENSE',.04,'OTHER_INCOME',0)",
                ('-.07', '.03') if name == 'MATERIAL_A_ABORT' else ('-.08', '.04'))
            report = base.one(cur, 'select pg_temp.m_report()')
            state = base.one(cur, 'select erp._cp6_material_adjustment_revaluation_state(%s)', (fixture['adjustment'],))
            statuses = dict(cur.execute('select id::text,status from erp.material_purchase_cost_corrections '
                'where id in(%s,%s)', (fixture['correction_a'], fixture['correction_b'])).fetchall())
            if (actual != expected or report != 'READY' or state['book'] != state['target']
                or statuses[fixture[second_key]] != 'POSTED'
                or statuses[fixture[first_key]] != ('DRAFT' if name == 'MATERIAL_A_ABORT' else 'POSTED')):
                raise AssertionError('T_RACE_DOCUMENT_CENT_OR_ATOMICITY_FAILED')
            boundary = base.one(cur, 'select pg_temp.t_boundary()')
            for key in ('material_a', 'material_b'):
                base.one(cur, 'select erp.sync_material_cost_revaluation(%s)', (fixture[key],))
            if base.one(cur, 'select pg_temp.t_boundary()') != boundary:
                raise AssertionError('T_RACE_REPLAY_NOT_IDEMPOTENT')
        return {'case': name, 'status': 'PASS', 'first_pid': first.info.backend_pid,
            'second_pid': second.info.backend_pid, 'blocking_observation': blocking,
            'first_real_function_completed_before_commit': True, 'connections_distinct': True,
            'manual_prelock_count': 0, 'retry_count': 0, 'contender': outcome,
            'first_aborted': name == 'MATERIAL_A_ABORT', 'actual': actual, 'expected': expected,
            'report': report, 'idempotent_replay': True,
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
        raise SystemExit('T_RACE_DISPOSABLE_ENDPOINT_CONFIRMATION_REQUIRED')
    ROOT.mkdir(parents=True, exist_ok=True)
    report = {'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'), 'production_go': False,
        'classification': 'NATIVE_POSTGRESQL_REAL_SHARED_ADJUSTMENT_LOCKS',
        'source_generation': 'T', 'cases': []}
    for name in CASES:
        folder = ROOT / name; folder.mkdir()
        try:
            result = run_case(name, folder)
        except Exception as exc:
            result = {'case': name, 'status': 'FAIL', 'error_code': 'T_NATIVE_RACE_FAILED',
                'error_type': type(exc).__name__, 'sqlstate': getattr(exc, 'sqlstate', None)}
        finally:
            matrix.legacy.drop_clone()
        result['remaining_clone_databases'] = 0
        (folder / 'result.json').write_text(json.dumps(result, indent=2, default=str) + '\n')
        report['cases'].append(result)
    report['status'] = 'PASS' if len(report['cases']) == len(CASES) and all(c['status'] == 'PASS' for c in report['cases']) else 'FAIL'
    (ROOT / 'manifest.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
    print(json.dumps({'status': report['status'], 'case_count': len(report['cases']), 'production_go': False}))
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
