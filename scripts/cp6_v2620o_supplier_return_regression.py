#!/usr/bin/env python3
"""N counterexamples and O cumulative supplier-return allocation proof."""
import hashlib
import json
import os
import re
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_preuse_rollback_maintenance as maintenance
import cp6_v2620e_counterexample_regression as base
import cp6_v2620n_runtime as n_runtime
import cp6_v2620o_runtime as o_runtime

SOURCE = Path('supabase/tests/cp6_supplier_return_document_allocation.sql')
CONTROL_CASES = (
    'NO_INVOICE_TWO_ROLL_FULL',
    'DIRECT_FINAL_TWO_ROLL_FULL',
    'FULL_INVOICE_TWO_ROLL_FULL',
    'PARTIAL_ONE_ROLL_FULL',
    'PARTIAL_TWO_RETURN_DOCUMENTS',
    'PARTIAL_TWO_LINES_BELOW_CAP',
    'HIGH_CREDIT_ATOMIC_REFUSAL',
)
AFFECTED_CASES = (
    'PARTIAL_TWO_ROLL_FULL',
    'PARTIAL_TWO_LINES_CROSS_CAP',
    'PARTIAL_THREE_ROLL_FULL',
    'SPLIT_INVOICES_TWO_ROLL_FULL',
    'REPRICED_PARTIAL_TWO_ROLL_FULL',
    'PRIOR_RELIEF_CROSS_REMAINING_CAP',
    'LOW_CREDIT_SILENT_MISPOST',
    'LOW_CREDIT_PAYMENT_CAPACITY',
    'LATE_INVOICE_LAUNDER',
    'RETURN_REVERSE_RESTORE',
    'FRACTIONAL_QUANTITY',
)
CASES = CONTROL_CASES + AFFECTED_CASES
UNSAFE_POSTED_HISTORY = {
    'LOW_CREDIT_SILENT_MISPOST', 'LATE_INVOICE_LAUNDER',
}


def run():
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    expected = dict(
        user='postgres', password='postgres', host='127.0.0.1',
        port='54322', dbname='postgres',
    )
    if params != expected:
        raise AssertionError('O_DISPOSABLE_ENDPOINT_REQUIRED')
    if os.environ.get('CP6_O_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('O_EXPLICIT_DISPOSABLE_CONFIRMATION_REQUIRED')
    phase = os.environ.get('CP6_O_PHASE', 'AFTER_O')
    if phase not in ('BEFORE_O', 'AFTER_O'):
        raise AssertionError('O_UNKNOWN_PHASE')
    fixed = phase == 'AFTER_O'
    result = {
        'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
        'production_go': False,
        'classification': 'DISPOSABLE_NATIVE_' + phase,
        'phase': phase,
        'oracle_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'cases': {},
    }
    with psycopg.connect(**params, autocommit=False) as conn, conn.cursor() as cur:
        cur.execute(
            "set local timezone='UTC';set local statement_timeout='180s';"
            "set local lock_timeout='8s'"
        )
        n_successor = n_runtime.verified_successor(cur)
        if len(n_successor) != 7:
            raise AssertionError('O_EXACT_N_REQUIRED')
        successor = o_runtime.verified_successor(cur)
        if len(successor) != (2 if fixed else 0):
            raise AssertionError('O_PHASE_RUNTIME_MISMATCH')
        if not fixed:
            maintenance._function_snapshot(conn, maintenance.TRUSTED_FUNCTIONS['O'])
        result['runtime'] = {
            'verified_n_functions': len(n_successor),
            'verified_o_functions': len(successor),
            'extra_objects_verified': o_runtime.verify_extra_objects(cur),
            'engine': base.one(cur, 'select version()'),
        }
        cur.execute("select set_config('request.jwt.claims',%s,true)", (
            json.dumps({'sub': base.OPERATOR_AUTH, 'role': 'authenticated'}),
        ))
        cur.execute("select set_config('app.change_reason',%s,true)", (
            'CP6 O independent supplier return allocation oracles',
        ))
        base.load_fixture_foundation(cur)
        for source in (
            Path('supabase/tests/cp6_subledger_exact_cent.sql'),
            Path('supabase/tests/cp6_supplier_cent_lifecycle.sql'),
            SOURCE,
        ):
            cur.execute(source.read_text(), prepare=False)
        migration_body = re.sub(
            r'^(begin|commit);$', '', o_runtime.MIGRATION.read_text(),
            flags=re.M | re.I,
        )
        for name in CASES:
            cur.execute('savepoint o_case')
            try:
                case = base.one(
                    cur, 'select pg_temp.o_case(%s,%s)', (name, fixed)
                )
                wanted = 'PASS' if fixed else (
                    'CONTROL_PASS' if name in CONTROL_CASES
                    else 'KNOWN_N_BUG_REPRODUCED'
                )
                if case['status'] != wanted:
                    raise AssertionError('O_ORACLE_STATUS_MISMATCH')
                if not fixed:
                    business_boundary = base.one(cur, 'select pg_temp.o_boundary()')
                    cur.execute('savepoint o_upgrade')
                    rejected = False
                    try:
                        cur.execute(migration_body, prepare=False)
                        if name in UNSAFE_POSTED_HISTORY:
                            raise AssertionError('O_UNSAFE_HISTORY_UPGRADE_ACCEPTED')
                    except psycopg.Error as exc:
                        if (
                            name not in UNSAFE_POSTED_HISTORY
                            or exc.sqlstate != 'P0001'
                            or 'O_PREEXISTING_RETURN_ALLOCATION_REVIEW_REQUIRED'
                               not in str(exc)
                        ):
                            raise
                        rejected = True
                    finally:
                        cur.execute('rollback to savepoint o_upgrade')
                        cur.execute('release savepoint o_upgrade')
                    if (
                        rejected != (name in UNSAFE_POSTED_HISTORY)
                        or base.one(cur, 'select pg_temp.o_boundary()')
                           != business_boundary
                    ):
                        raise AssertionError('O_UPGRADE_GUARD_BOUNDARY_FAILED')
                    maintenance._function_snapshot(
                        conn, maintenance.TRUSTED_FUNCTIONS['O']
                    )
                    if o_runtime.verified_successor(cur):
                        raise AssertionError('O_UPGRADE_GUARD_RESIDUE')
                    case['upgrade_guard'] = {
                        'valid_history_accepted': not rejected,
                        'invalid_history_refused': rejected,
                        'business_facts_unchanged': True,
                        'runtime_restored': True,
                    }
                result['cases'][name] = case
            except Exception as exc:
                result['cases'][name] = {
                    'status': 'FAIL',
                    'code': getattr(exc, 'sqlstate', None) or 'O_ORACLE_FAILED',
                    'message': str(exc),
                }
            finally:
                cur.execute('rollback to savepoint o_case')
                cur.execute('release savepoint o_case')
            if base.one(cur, 'select pg_temp.m_report()') != 'READY':
                raise AssertionError('O_CASE_RESTORE_NOT_READY')
            result['cases'][name]['rolled_back_to_ready'] = True
        conn.rollback()
    acceptable = {'PASS'} if fixed else {
        'CONTROL_PASS', 'KNOWN_N_BUG_REPRODUCED',
    }
    result['all_case_effects_rolled_back'] = True
    result['status'] = (
        'PASS' if all(c['status'] in acceptable for c in result['cases'].values())
        else 'FAIL'
    )
    return result


def main():
    phase = os.environ.get('CP6_O_PHASE', 'AFTER_O')
    filename = (
        'CP6_V2620O_N_COUNTEREXAMPLES.json' if phase == 'BEFORE_O'
        else 'CP6_V2620O_SUPPLIER_RETURN_REGRESSION.json'
    )
    report = Path('cp6-proof') / filename
    try:
        result = run()
    except Exception as exc:
        result = {
            'status': 'FAIL',
            'code': getattr(exc, 'sqlstate', None) or 'O_PREFLIGHT_FAILED',
            'message': str(exc),
            'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
            'production_go': False,
        }
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps({
        'status': result['status'],
        'case_count': len(result.get('cases', {})),
        'production_go': False,
    }))
    if result['status'] == 'FAIL':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
