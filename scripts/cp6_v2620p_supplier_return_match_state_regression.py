#!/usr/bin/env python3
"""O counterexamples and P supplier-return match/report-scope proof."""
import hashlib
import json
import os
import re
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_preuse_rollback_maintenance as maintenance
import cp6_v2620e_counterexample_regression as base
import cp6_v2620o_runtime as o_runtime
import cp6_v2620p_runtime as p_runtime


SOURCE = Path('supabase/tests/cp6_supplier_return_match_state.sql')
CONTROL_CASES = (
    'PARTIAL_REMAINS_PARTIAL',
    'NO_INVOICE_FULL_RETURN',
    'DIRECT_FINAL_FULL_RETURN',
    'FOLLOWUP_INVOICE_CAPACITY_REFUSAL',
)
AFFECTED_CASES = (
    'ONE_DOCUMENT_CLOSES_REMAINING_GRNI',
    'TWO_DOCUMENTS_CLOSE_REMAINING_GRNI',
    'RETURN_REVERSE_RESTORE',
    'MATCH_STATE_DETECTOR',
    'O_ALLOCATION_DETECTOR_SCOPE',
)
CASES = AFFECTED_CASES + CONTROL_CASES
UNSAFE_POSTED_HISTORY = {
    'ONE_DOCUMENT_CLOSES_REMAINING_GRNI',
    'TWO_DOCUMENTS_CLOSE_REMAINING_GRNI',
}


def run():
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    expected = dict(
        user='postgres', password='postgres', host='127.0.0.1',
        port='54322', dbname='postgres',
    )
    if params != expected:
        raise AssertionError('P_DISPOSABLE_ENDPOINT_REQUIRED')
    if os.environ.get('CP6_P_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('P_EXPLICIT_DISPOSABLE_CONFIRMATION_REQUIRED')
    phase = os.environ.get('CP6_P_PHASE', 'AFTER_P')
    if phase not in ('BEFORE_P', 'AFTER_P'):
        raise AssertionError('P_UNKNOWN_PHASE')
    fixed = phase == 'AFTER_P'
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
        o_successor = o_runtime.verified_successor(cur)
        if len(o_successor) != 2:
            raise AssertionError('P_EXACT_O_REQUIRED')
        successor = p_runtime.verified_successor(cur)
        if len(successor) != (3 if fixed else 0):
            raise AssertionError('P_PHASE_RUNTIME_MISMATCH')
        if not fixed:
            maintenance._function_snapshot(conn, maintenance.TRUSTED_FUNCTIONS['P'])
        result['runtime'] = {
            'verified_o_functions': len(o_successor),
            'verified_p_functions': len(successor),
            'extra_objects_verified': p_runtime.verify_extra_objects(cur),
            'engine': base.one(cur, 'select version()'),
        }
        cur.execute("select set_config('request.jwt.claims',%s,true)", (
            json.dumps({'sub': base.OPERATOR_AUTH, 'role': 'authenticated'}),
        ))
        cur.execute("select set_config('app.change_reason',%s,true)", (
            'CP6 P independent supplier return match/report-scope oracles',
        ))
        base.load_fixture_foundation(cur)
        for source in (
            Path('supabase/tests/cp6_subledger_exact_cent.sql'),
            Path('supabase/tests/cp6_supplier_cent_lifecycle.sql'),
            Path('supabase/tests/cp6_supplier_return_document_allocation.sql'),
            SOURCE,
        ):
            cur.execute(source.read_text(), prepare=False)
        migration_body = re.sub(
            r'^(begin|commit);$', '', p_runtime.MIGRATION.read_text(),
            flags=re.M | re.I,
        )
        for name in CASES:
            cur.execute('savepoint p_case')
            try:
                case = base.one(cur, 'select pg_temp.p_case(%s,%s)', (name, fixed))
                wanted = 'PASS' if fixed else (
                    'KNOWN_O_BUG_REPRODUCED'
                    if name in AFFECTED_CASES else 'CONTROL_PASS'
                )
                if case['status'] != wanted:
                    raise AssertionError('P_ORACLE_STATUS_MISMATCH')
                if not fixed:
                    business_boundary = base.one(cur, 'select pg_temp.o_boundary()')
                    cur.execute('savepoint p_upgrade')
                    rejected = False
                    try:
                        cur.execute(migration_body, prepare=False)
                        if name in UNSAFE_POSTED_HISTORY:
                            raise AssertionError('P_UNSAFE_HISTORY_UPGRADE_ACCEPTED')
                    except psycopg.Error as exc:
                        if (
                            name not in UNSAFE_POSTED_HISTORY
                            or exc.sqlstate != 'P0001'
                            or 'P_PREEXISTING_RETURN_MATCH_STATE_REVIEW_REQUIRED'
                               not in str(exc)
                        ):
                            raise
                        rejected = True
                    finally:
                        cur.execute('rollback to savepoint p_upgrade')
                        cur.execute('release savepoint p_upgrade')
                    if (
                        rejected != (name in UNSAFE_POSTED_HISTORY)
                        or base.one(cur, 'select pg_temp.o_boundary()')
                           != business_boundary
                    ):
                        raise AssertionError('P_UPGRADE_GUARD_BOUNDARY_FAILED')
                    maintenance._function_snapshot(
                        conn, maintenance.TRUSTED_FUNCTIONS['P']
                    )
                    if p_runtime.verified_successor(cur):
                        raise AssertionError('P_UPGRADE_GUARD_RESIDUE')
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
                    'code': getattr(exc, 'sqlstate', None) or 'P_ORACLE_FAILED',
                    'message': str(exc),
                }
            finally:
                cur.execute('rollback to savepoint p_case')
                cur.execute('release savepoint p_case')
            if base.one(cur, 'select pg_temp.m_report()') != 'READY':
                raise AssertionError('P_CASE_RESTORE_NOT_READY')
            result['cases'][name]['rolled_back_to_ready'] = True
        conn.rollback()
    acceptable = {'PASS'} if fixed else {
        'CONTROL_PASS', 'KNOWN_O_BUG_REPRODUCED',
    }
    result['all_case_effects_rolled_back'] = True
    result['status'] = (
        'PASS'
        if all(c['status'] in acceptable for c in result['cases'].values())
        else 'FAIL'
    )
    return result


def main():
    phase = os.environ.get('CP6_P_PHASE', 'AFTER_P')
    filename = (
        'CP6_V2620P_O_COUNTEREXAMPLES.json' if phase == 'BEFORE_P'
        else 'CP6_V2620P_SUPPLIER_RETURN_MATCH_STATE_REGRESSION.json'
    )
    report = Path('cp6-proof') / filename
    try:
        result = run()
    except Exception as exc:
        result = {
            'status': 'FAIL',
            'code': getattr(exc, 'sqlstate', None) or 'P_PREFLIGHT_FAILED',
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
