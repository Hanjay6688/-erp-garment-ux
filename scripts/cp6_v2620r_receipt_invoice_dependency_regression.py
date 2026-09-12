#!/usr/bin/env python3
"""Q counterexamples and R receipt/invoice dependency proof."""
import hashlib
import json
import os
import re
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_preuse_rollback_maintenance as maintenance
import cp6_v2620e_counterexample_regression as base
import cp6_v2620m_runtime as m_runtime
import cp6_v2620q_runtime as q_runtime
import cp6_v2620r_runtime as r_runtime


SOURCE = Path('supabase/tests/cp6_receipt_invoice_dependency.sql')
CONTROL_CASES = ('REVERSE_INVOICE_THEN_RECEIPT', 'REVERSED_AND_DRAFT_INVOICES', 'DRAFT_INVOICE_LATE_POST', 'DIRECT_FINAL_NO_INVOICE', 'RECEIPT_REPEAT_REVERSE', 'POSTED_RETURN_GUARD', 'POSTED_PAYMENT_GUARD', 'POSTED_CORRECTION_GUARD')
AFFECTED_CASES = ('POSTED_FULL_INVOICE', 'POSTED_PARTIAL_INVOICE', 'MULTI_RECEIPT_INVOICE', 'REMAINING_POSTED_INVOICE', 'DETECTOR_SOURCE_STATE')
CASES = AFFECTED_CASES + CONTROL_CASES
UNSAFE_POSTED_HISTORY = {'MULTI_RECEIPT_INVOICE', 'POSTED_FULL_INVOICE', 'REMAINING_POSTED_INVOICE', 'POSTED_PARTIAL_INVOICE'}


def run():
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    expected = dict(
        user='postgres', password='postgres', host='127.0.0.1',
        port='54322', dbname='postgres',
    )
    if params != expected:
        raise AssertionError('R_DISPOSABLE_ENDPOINT_REQUIRED')
    if os.environ.get('CP6_R_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('R_EXPLICIT_DISPOSABLE_CONFIRMATION_REQUIRED')
    phase = os.environ.get('CP6_R_PHASE', 'AFTER_R')
    if phase not in ('BEFORE_R', 'AFTER_R'):
        raise AssertionError('R_UNKNOWN_PHASE')
    fixed = phase == 'AFTER_R'
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
        q_successor = q_runtime.verified_successor(cur)
        if len(q_successor) != 4:
            raise AssertionError('R_EXACT_Q_REQUIRED')
        successor = r_runtime.verified_successor(cur)
        if len(successor) != (3 if fixed else 0):
            raise AssertionError('R_PHASE_RUNTIME_MISMATCH')
        m_successor = m_runtime.verified_successor(cur)
        if len(m_successor) != 15:
            raise AssertionError('R_HISTORICAL_M_CHAIN_MISMATCH')
        if not fixed:
            maintenance._function_snapshot(conn, maintenance.TRUSTED_FUNCTIONS['R'])
        result['runtime'] = {
            'verified_q_functions': len(q_successor),
            'verified_r_functions': len(successor),
            'verified_m_functions': len(m_successor),
            'extra_objects_verified': r_runtime.verify_extra_objects(cur),
            'engine': base.one(cur, 'select version()'),
        }
        cur.execute("select set_config('request.jwt.claims',%s,true)", (
            json.dumps({'sub': base.OPERATOR_AUTH, 'role': 'authenticated'}),
        ))
        cur.execute("select set_config('app.change_reason',%s,true)", (
            'CP6 R receipt/invoice dependency oracles',
        ))
        base.load_fixture_foundation(cur)
        for source in (
            Path('supabase/tests/cp6_subledger_exact_cent.sql'),
            Path('supabase/tests/cp6_supplier_cent_lifecycle.sql'),
            Path('supabase/tests/cp6_supplier_return_document_allocation.sql'),
            Path('supabase/tests/cp6_supplier_invoice_exact_quantity.sql'),
            SOURCE,
        ):
            cur.execute(source.read_text(), prepare=False)
        migration_body = re.sub(
            r'^(begin|commit);$', '', r_runtime.MIGRATION.read_text(),
            flags=re.M | re.I,
        )
        for name in CASES:
            cur.execute('savepoint r_case')
            try:
                case = base.one(cur, 'select pg_temp.r_case(%s,%s)', (name, fixed))
                wanted = 'PASS' if fixed else (
                    'KNOWN_Q_BUG_REPRODUCED'
                    if name in AFFECTED_CASES else 'CONTROL_PASS'
                )
                if case['status'] != wanted:
                    raise AssertionError('R_ORACLE_STATUS_MISMATCH')
                if not fixed:
                    business_boundary = base.one(cur, 'select pg_temp.o_boundary()')
                    cur.execute('savepoint r_upgrade')
                    rejected = False
                    try:
                        cur.execute(migration_body, prepare=False)
                        if name in UNSAFE_POSTED_HISTORY:
                            raise AssertionError('R_UNSAFE_HISTORY_UPGRADE_ACCEPTED')
                    except psycopg.Error as exc:
                        if (
                            name not in UNSAFE_POSTED_HISTORY
                            or exc.sqlstate != 'P0001'
                            or 'R_PREEXISTING_INVOICE_SOURCE_REVIEW_REQUIRED'
                               not in str(exc)
                        ):
                            raise
                        rejected = True
                    finally:
                        cur.execute('rollback to savepoint r_upgrade')
                        cur.execute('release savepoint r_upgrade')
                    if (
                        rejected != (name in UNSAFE_POSTED_HISTORY)
                        or base.one(cur, 'select pg_temp.o_boundary()')
                           != business_boundary
                    ):
                        raise AssertionError('R_UPGRADE_GUARD_BOUNDARY_FAILED')
                    maintenance._function_snapshot(
                        conn, maintenance.TRUSTED_FUNCTIONS['R']
                    )
                    if r_runtime.verified_successor(cur):
                        raise AssertionError('R_UPGRADE_GUARD_RESIDUE')
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
                    'code': getattr(exc, 'sqlstate', None) or 'R_ORACLE_FAILED',
                    'message': str(exc),
                }
            finally:
                cur.execute('rollback to savepoint r_case')
                cur.execute('release savepoint r_case')
            if base.one(cur, 'select pg_temp.m_report()') != 'READY':
                raise AssertionError('R_CASE_RESTORE_NOT_READY')
            result['cases'][name]['rolled_back_to_ready'] = True
        conn.rollback()
    acceptable = {'PASS'} if fixed else {
        'CONTROL_PASS', 'KNOWN_Q_BUG_REPRODUCED',
    }
    result['all_case_effects_rolled_back'] = True
    result['status'] = (
        'PASS'
        if all(c['status'] in acceptable for c in result['cases'].values())
        else 'FAIL'
    )
    return result


def main():
    phase = os.environ.get('CP6_R_PHASE', 'AFTER_R')
    filename = (
        'CP6_V2620R_Q_COUNTEREXAMPLES.json' if phase == 'BEFORE_R'
        else 'CP6_V2620R_RECEIPT_INVOICE_DEPENDENCY_REGRESSION.json'
    )
    report = Path('cp6-proof') / filename
    try:
        result = run()
    except Exception as exc:
        result = {
            'status': 'FAIL',
            'code': getattr(exc, 'sqlstate', None) or 'R_PREFLIGHT_FAILED',
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
