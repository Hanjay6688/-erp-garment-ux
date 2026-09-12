#!/usr/bin/env python3
"""S counterexamples and T document cents, inverse and accounting-day proof."""
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
import cp6_v2620s_runtime as s_runtime
import cp6_v2620t_runtime as t_runtime


SOURCE = Path('supabase/tests/cp6_material_adjustment_revaluation.sql')
CONTROL_CASES = ('MISSING_NONZERO_JOURNAL','COST_SINGLE_ROLL_CONTROL','COST_INTEGER_CONTROL',
    'POSITIVE_CONTROL','JAKARTA_TODAY_CONTROL','FUTURE_REFUSAL_CONTROL')
AFFECTED_CASES = ('MULTI_MATERIAL_A_FIRST','MULTI_MATERIAL_B_FIRST','COST_SPLIT',
    'COST_SINGLE_ENDPOINT','COST_HALF_YARD','COST_DECREASE','COST_PARTIAL','LINKED_INVERSE',
    'ADJUSTMENT_FIRST_INVERSE','FACT_GUARDS','DETECTOR_COST','ZERO_NET_INVERSE',
    'ZERO_NET_CORRECTED_INVERSE','REAL_DAY_BOUNDARY','CLOSED_PERIOD_DAY')
CASES = AFFECTED_CASES + CONTROL_CASES


def run():
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    expected = dict(
        user='postgres', password='postgres', host='127.0.0.1',
        port='54322', dbname='postgres',
    )
    if params != expected:
        raise AssertionError('T_DISPOSABLE_ENDPOINT_REQUIRED')
    if os.environ.get('CP6_T_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('T_EXPLICIT_DISPOSABLE_CONFIRMATION_REQUIRED')
    phase = os.environ.get('CP6_T_PHASE', 'AFTER_T')
    if phase not in ('BEFORE_T', 'AFTER_T'):
        raise AssertionError('T_UNKNOWN_PHASE')
    fixed = phase == 'AFTER_T'
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
        s_successor = s_runtime.verified_successor(cur)
        if len(s_successor) != 3:
            raise AssertionError('T_EXACT_S_REQUIRED')
        successor = t_runtime.verified_successor(cur)
        if len(successor) != (6 if fixed else 0):
            raise AssertionError('T_PHASE_RUNTIME_MISMATCH')
        m_successor = m_runtime.verified_successor(cur)
        if len(m_successor) != 15:
            raise AssertionError('T_HISTORICAL_M_CHAIN_MISMATCH')
        if not fixed:
            maintenance._function_snapshot(conn, maintenance.TRUSTED_FUNCTIONS['T'])
        result['runtime'] = {
            'verified_s_functions': len(s_successor),
            'verified_t_functions': len(successor),
            'verified_m_functions': len(m_successor),
            'extra_objects_verified': (t_runtime if fixed else s_runtime).verify_extra_objects(cur),
            'engine': base.one(cur, 'select version()'),
        }
        cur.execute("select set_config('request.jwt.claims',%s,true)", (
            json.dumps({'sub': base.OPERATOR_AUTH, 'role': 'authenticated'}),
        ))
        cur.execute("select set_config('app.change_reason',%s,true)", (
            'CP6 T material adjustment and canonical accounting day',
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
            r'^(begin|commit);$', '', t_runtime.MIGRATION.read_text(),
            flags=re.M | re.I,
        )
        for name in CASES:
            cur.execute('savepoint r_case')
            try:
                case = base.one(cur, 'select pg_temp.t_case(%s,%s)', (name, fixed))
                wanted = 'PASS' if fixed else (
                    'KNOWN_S_BUG_REPRODUCED'
                    if name in AFFECTED_CASES else 'CONTROL_PASS'
                )
                if case['status'] != wanted:
                    raise AssertionError('T_ORACLE_STATUS_MISMATCH')
                if not fixed:
                    business_boundary = base.one(cur, 'select pg_temp.t_boundary()')
                    cur.execute('savepoint r_upgrade')
                    rejected = False
                    try:
                        cur.execute(migration_body, prepare=False)
                        if case['unsafe_history']:
                            raise AssertionError('T_UNSAFE_HISTORY_UPGRADE_ACCEPTED')
                    except psycopg.Error as exc:
                        if (
                            not case['unsafe_history']
                            or exc.sqlstate != 'P0001'
                            or 'T_PREEXISTING_ADJUSTMENT_OR_BUSINESS_DATE_REVIEW_REQUIRED'
                               not in str(exc)
                        ):
                            raise
                        rejected = True
                    finally:
                        cur.execute('rollback to savepoint r_upgrade')
                        cur.execute('release savepoint r_upgrade')
                    if (
                        rejected != (case['unsafe_history'])
                        or base.one(cur, 'select pg_temp.t_boundary()')
                           != business_boundary
                    ):
                        raise AssertionError('T_UPGRADE_GUARD_BOUNDARY_FAILED')
                    maintenance._function_snapshot(
                        conn, maintenance.TRUSTED_FUNCTIONS['T']
                    )
                    if t_runtime.verified_successor(cur):
                        raise AssertionError('T_UPGRADE_GUARD_RESIDUE')
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
                    'code': getattr(exc, 'sqlstate', None) or 'T_ORACLE_FAILED',
                    'message': str(exc),
                }
            finally:
                cur.execute('rollback to savepoint r_case')
                cur.execute('release savepoint r_case')
            if base.one(cur, 'select pg_temp.m_report()') != 'READY':
                raise AssertionError('T_CASE_RESTORE_NOT_READY')
            result['cases'][name]['rolled_back_to_ready'] = True
        conn.rollback()
    acceptable = {'PASS'} if fixed else {
        'CONTROL_PASS', 'KNOWN_S_BUG_REPRODUCED',
    }
    result['all_case_effects_rolled_back'] = True
    result['status'] = (
        'PASS'
        if all(c['status'] in acceptable for c in result['cases'].values())
        else 'FAIL'
    )
    return result


def main():
    phase = os.environ.get('CP6_T_PHASE', 'AFTER_T')
    filename = (
        'CP6_V2620T_S_COUNTEREXAMPLES.json' if phase == 'BEFORE_T'
        else 'CP6_V2620T_MATERIAL_ADJUSTMENT_REVALUATION_REGRESSION.json'
    )
    report = Path('cp6-proof') / filename
    try:
        result = run()
    except Exception as exc:
        result = {
            'status': 'FAIL',
            'code': getattr(exc, 'sqlstate', None) or 'T_PREFLIGHT_FAILED',
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
