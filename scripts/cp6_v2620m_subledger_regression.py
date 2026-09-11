#!/usr/bin/env python3
"""Independent business counterexamples and controls on disposable native M."""
import hashlib
import json
import os
import re
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_v2620e_counterexample_regression as base
import cp6_v2620l_runtime as l_runtime
import cp6_v2620m_runtime as m_runtime
import cp6_preuse_rollback_maintenance as maintenance

SOURCE = Path('supabase/tests/cp6_subledger_exact_cent.sql')
BEFORE_CASES = ('OPENING_READY', 'OPENING_LAST_CENT', 'OPENING_OVERPAY',
    'OPENING_CORRECTION', 'OPENING_REVERSE_CORRECTION', 'OPENING_REVERSE_SETTLEMENT',
    'SUPPLIER_LAST_CENT', 'SUPPLIER_OVERPAY', 'SUPPLIER_REVERSE_PAYMENT',
    'SUPPLIER_CORRECTION', 'SUPPLIER_REVERSE_CORRECTION', 'SUPPLIER_RETURN')
CASES = BEFORE_CASES + ('OPENING_PARTIES', 'SUPPLIER_VALID_LIFECYCLE',
    'SUPPLIER_INVOICE_LIFECYCLE', 'FRACTIONAL_PURCHASES', 'SUPPLIER_AMOUNT_WASH',
    'OPENING_PARTY_WASH', 'OPENING_STATUS_FAULT', 'PAYMENT_INVERSE_FAULT')


def run():
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    if params != dict(user='postgres', password='postgres', host='127.0.0.1', port='54322', dbname='postgres'):
        raise AssertionError('M_DISPOSABLE_ENDPOINT_REQUIRED')
    if os.environ.get('CP6_M_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('M_EXPLICIT_DISPOSABLE_CONFIRMATION_REQUIRED')
    phase = os.environ.get('CP6_M_PHASE', 'AFTER_M')
    if phase not in ('BEFORE_M', 'AFTER_M'):
        raise AssertionError('M_UNKNOWN_PHASE')
    fixed = phase == 'AFTER_M'
    result = {'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'), 'production_go': False,
        'classification': 'DISPOSABLE_NATIVE_' + phase, 'phase': phase,
        'oracle_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'cases': {}}
    with psycopg.connect(**params, autocommit=False) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='180s';set local lock_timeout='8s'")
        if len(l_runtime.verified_successor(cur)) != 3:
            raise AssertionError('M_EXACT_L_REQUIRED')
        successor = m_runtime.verified_successor(cur)
        if len(successor) != (15 if fixed else 0):
            raise AssertionError('M_PHASE_RUNTIME_MISMATCH')
        expected = maintenance.TRUSTED_FUNCTIONS['M']
        if not fixed:
            maintenance._function_snapshot(conn, expected)
        result['runtime'] = {'verified_l_functions': 3, 'verified_m_functions': len(successor),
            'm_predecessor_source_pins_exact': not fixed, 'engine': base.one(cur, 'select version()')}
        cur.execute("select set_config('request.jwt.claims',%s,true)",
            (json.dumps({'sub': base.OPERATOR_AUTH, 'role': 'authenticated'}),))
        cur.execute("select set_config('app.change_reason','CP6 M independent subledger oracles',true)")
        base.load_fixture_foundation(cur)
        cur.execute(SOURCE.read_text(), prepare=False)
        for name in (CASES if fixed else BEFORE_CASES):
            cur.execute('savepoint m_case')
            stage = 'BUSINESS_ORACLE'
            try:
                result['cases'][name] = base.one(cur, 'select pg_temp.m_case(%s,%s)', (name, fixed))
                if not fixed:
                    stage = 'PREEXISTING_HISTORY_UPGRADE_GUARD'
                    boundary = base.one(cur, 'select pg_temp.m_boundary()')
                    # These two original cases finish in a consistent state;
                    # M may upgrade them without rewriting their business facts.
                    allowed = name in ('OPENING_READY', 'SUPPLIER_LAST_CENT')
                    cur.execute('savepoint m_upgrade')
                    rejected = False
                    try:
                        body = re.sub(r'^(begin|commit);$', '', m_runtime.MIGRATION.read_text(), flags=re.M | re.I)
                        cur.execute(body, prepare=False)
                        if not allowed:
                            raise AssertionError('M_UNSAFE_HISTORY_UPGRADE_ACCEPTED')
                        if base.one(cur, 'select pg_temp.m_report()') != 'READY':
                            raise AssertionError('M_VALID_HISTORY_UPGRADE_FALSE_BLOCKED')
                    except psycopg.Error as exc:
                        if allowed or exc.sqlstate != 'P0001' or 'M_PREEXISTING_SUBLEDGER_REVIEW_REQUIRED' not in str(exc):
                            raise
                        rejected = True
                    finally:
                        cur.execute('rollback to savepoint m_upgrade'); cur.execute('release savepoint m_upgrade')
                    if rejected == allowed or base.one(cur, 'select pg_temp.m_boundary()') != boundary:
                        raise AssertionError('M_UPGRADE_GUARD_BOUNDARY_FAILED')
                    maintenance._function_snapshot(conn, expected)
                    if m_runtime.verified_successor(cur):
                        raise AssertionError('M_UPGRADE_GUARD_RESIDUE')
                    result['cases'][name]['upgrade_guard'] = {
                        'valid_history_accepted': allowed, 'invalid_history_refused': rejected,
                        'business_facts_unchanged': True, 'runtime_restored': True}
            except Exception as exc:
                result['cases'][name] = {'status': 'FAIL', 'stage': stage,
                    'code': getattr(exc, 'sqlstate', None) or 'M_ORACLE_FAILED'}
            finally:
                cur.execute('rollback to savepoint m_case'); cur.execute('release savepoint m_case')
            if base.one(cur, 'select pg_temp.m_report()') != 'READY':
                raise AssertionError('M_CASE_RESTORE_NOT_READY')
            result['cases'][name]['rolled_back_to_ready'] = True
        conn.rollback()
    status = 'PASS' if fixed else 'KNOWN_L_BUG_REPRODUCED'
    result['all_case_effects_rolled_back'] = True
    result['status'] = status if all(c['status'] == status for c in result['cases'].values()) else 'FAIL'
    return result


def main():
    phase = os.environ.get('CP6_M_PHASE', 'AFTER_M')
    report = Path('cp6-proof/CP6_V2620M_' + ('L_COUNTEREXAMPLES' if phase == 'BEFORE_M' else 'SUBLEDGER_REGRESSION') + '.json')
    try:
        result = run()
    except Exception as exc:
        result = {'status': 'FAIL', 'code': getattr(exc, 'sqlstate', None) or 'M_PREFLIGHT_FAILED',
            'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'), 'production_go': False}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps({'status': result['status'], 'case_count': len(result.get('cases', {})), 'production_go': False}))
    if result['status'] == 'FAIL':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
