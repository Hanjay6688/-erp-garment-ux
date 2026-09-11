#!/usr/bin/env python3
"""M counterexamples and N cumulative supplier lifecycle on disposable native SQL."""
import hashlib
import json
import os
import re
from pathlib import Path
import psycopg
from psycopg.conninfo import conninfo_to_dict
import cp6_v2620e_counterexample_regression as base
import cp6_v2620m_runtime as m_runtime
import cp6_v2620n_runtime as n_runtime
import cp6_preuse_rollback_maintenance as maintenance

SOURCE = Path('supabase/tests/cp6_supplier_cent_lifecycle.sql')
BEFORE_CASES = ('CORRECTION_ROUND_DELTA', 'CORRECTION_HALF_CENT', 'MULTI_PURCHASE_INVOICE', 'PARTIAL_INVOICE', 'SPLIT_RETURN')
CASES = BEFORE_CASES + ('CORRECTION_ZERO_INVERSE', 'CORRECTION_CHAIN', 'NONFIFO_INVOICE_INVERSE',
    'INVOICE_PAY_REVERSE', 'INVOICE_RETURN_INVERSE', 'NONFIFO_RETURN_INVERSE', 'SUBCENT_RETURN_INVERSE',
    'ZERO_CENT_POSTING_FACT', 'FACT_LEDGER_FAULT')


def run():
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    if params != dict(user='postgres', password='postgres', host='127.0.0.1', port='54322', dbname='postgres'):
        raise AssertionError('N_DISPOSABLE_ENDPOINT_REQUIRED')
    if os.environ.get('CP6_N_DISPOSABLE_CONFIRM') != 'postgres':
        raise AssertionError('N_EXPLICIT_DISPOSABLE_CONFIRMATION_REQUIRED')
    phase = os.environ.get('CP6_N_PHASE', 'AFTER_N')
    if phase not in ('BEFORE_N', 'AFTER_N'):
        raise AssertionError('N_UNKNOWN_PHASE')
    fixed = phase == 'AFTER_N'
    result = {'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'), 'production_go': False,
        'classification': 'DISPOSABLE_NATIVE_' + phase, 'phase': phase,
        'oracle_sha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(), 'cases': {}}
    with psycopg.connect(**params, autocommit=False) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='180s';set local lock_timeout='8s'")
        if len(m_runtime.verified_successor(cur)) != 15:
            raise AssertionError('N_EXACT_M_REQUIRED')
        successor = n_runtime.verified_successor(cur)
        if len(successor) != (7 if fixed else 0):
            raise AssertionError('N_PHASE_RUNTIME_MISMATCH')
        if not fixed:
            maintenance._function_snapshot(conn, maintenance.TRUSTED_FUNCTIONS['N'])
        result['runtime'] = {'verified_m_functions': 15, 'verified_n_functions': len(successor),
            'extra_objects_verified': n_runtime.verify_extra_objects(cur) if fixed else 0,
            'engine': base.one(cur, 'select version()')}
        cur.execute("select set_config('request.jwt.claims',%s,true)",
            (json.dumps({'sub': base.OPERATOR_AUTH, 'role': 'authenticated'}),))
        cur.execute("select set_config('app.change_reason','CP6 N independent supplier cent oracles',true)")
        base.load_fixture_foundation(cur)
        cur.execute(Path('supabase/tests/cp6_subledger_exact_cent.sql').read_text(), prepare=False)
        cur.execute(SOURCE.read_text(), prepare=False)
        for name in (CASES if fixed else BEFORE_CASES):
            cur.execute('savepoint n_case')
            try:
                result['cases'][name] = base.one(cur, 'select pg_temp.n_case(%s,%s)', (name, fixed))
                if not fixed:
                    boundary = base.one(cur, 'select pg_temp.m_boundary()')
                    allowed = name == 'PARTIAL_INVOICE'
                    cur.execute('savepoint n_upgrade')
                    rejected = False
                    try:
                        body = re.sub(r'^(begin|commit);$', '', n_runtime.MIGRATION.read_text(), flags=re.M | re.I)
                        cur.execute(body, prepare=False)
                        if not allowed:
                            raise AssertionError('N_UNSAFE_HISTORY_UPGRADE_ACCEPTED')
                    except psycopg.Error as exc:
                        if allowed or exc.sqlstate != 'P0001' or 'N_PREEXISTING_SUPPLIER_REVIEW_REQUIRED' not in str(exc):
                            raise
                        rejected = True
                    finally:
                        cur.execute('rollback to savepoint n_upgrade'); cur.execute('release savepoint n_upgrade')
                    if rejected == allowed or base.one(cur, 'select pg_temp.m_boundary()') != boundary:
                        raise AssertionError('N_UPGRADE_GUARD_BOUNDARY_FAILED')
                    maintenance._function_snapshot(conn, maintenance.TRUSTED_FUNCTIONS['N'])
                    if n_runtime.verified_successor(cur):
                        raise AssertionError('N_UPGRADE_GUARD_RESIDUE')
                    result['cases'][name]['upgrade_guard'] = {'valid_history_accepted': allowed,
                        'invalid_history_refused': rejected, 'business_facts_unchanged': True, 'runtime_restored': True}
            except Exception as exc:
                result['cases'][name] = {'status': 'FAIL', 'code': getattr(exc, 'sqlstate', None) or 'N_ORACLE_FAILED'}
            finally:
                cur.execute('rollback to savepoint n_case'); cur.execute('release savepoint n_case')
            if base.one(cur, 'select pg_temp.m_report()') != 'READY':
                raise AssertionError('N_CASE_RESTORE_NOT_READY')
            result['cases'][name]['rolled_back_to_ready'] = True
        conn.rollback()
    status = 'PASS' if fixed else 'KNOWN_M_BUG_REPRODUCED'
    result['all_case_effects_rolled_back'] = True
    result['status'] = status if all(c['status'] == status for c in result['cases'].values()) else 'FAIL'
    return result


def main():
    phase = os.environ.get('CP6_N_PHASE', 'AFTER_N')
    report = Path('cp6-proof/CP6_V2620N_' + ('M_COUNTEREXAMPLES' if phase == 'BEFORE_N' else 'SUPPLIER_CENT_REGRESSION') + '.json')
    try:
        result = run()
    except Exception as exc:
        result = {'status': 'FAIL', 'code': getattr(exc, 'sqlstate', None) or 'N_PREFLIGHT_FAILED',
            'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'), 'production_go': False}
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps({'status': result['status'], 'case_count': len(result.get('cases', {})), 'production_go': False}))
    if result['status'] == 'FAIL':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
