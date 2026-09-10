#!/usr/bin/env python3
"""Exact-G native SQL regressions; transaction/savepoint isolated, never hosted."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import psycopg

import cp6_v2620e_counterexample_regression as base

MIGRATION = Path('supabase/migrations/20260910031103_erp_v2_6_20g_cp6_independent_audit_closure.sql')
CASES = ('g_n01_split_loss', 'g_n01_gain_lumped', 'g_n02_multiline',
         'g_n02_corrected_loss', 'g_n02_zero_minor_units', 'g_n03_source_detector',
         'g_n01_threshold_matrix', 'g_n02_reserved_reprice')
REPORT = Path(os.environ.get('CP6_G_REPORT', 'cp6-proof/CP6_V2620G_INDEPENDENT_REGRESSION.json'))


def runtime(cur):
    cur.execute("select version()")
    engine = cur.fetchone()[0]
    cur.execute("select version from erp.schema_migrations where version in('v2.6.20e','v2.6.20f','v2.6.20g') order by version")
    versions = [r[0] for r in cur.fetchall()]
    if versions != ['v2.6.20e', 'v2.6.20f', 'v2.6.20g']:
        raise AssertionError(f'Final E+F+G runtime not present: {versions}')
    cur.execute("""select object_regidentity,installed_definition_sha256,
      encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),
        'UTF8'),'sha256'),'hex') actual from erp.cp6_v2620g_rollback_capsule
      order by object_regidentity""")
    definitions = [dict(zip(('identity', 'installed_sha256', 'actual_sha256'), r)) for r in cur.fetchall()]
    if len(definitions) != 7 or any(r['installed_sha256'] != r['actual_sha256'] for r in definitions):
        raise AssertionError('G installed definition differs from capsule')
    cur.execute("""select encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),
      'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations
      where name='erp_v2_6_20g_cp6_independent_audit_closure'""")
    platform = [r[0] for r in cur.fetchall()]
    source = MIGRATION.read_bytes()
    digests = [hashlib.sha256(source).hexdigest(), hashlib.sha256(source[:-1]).hexdigest()]
    if len(platform) != 1 or platform[0] not in digests:
        raise AssertionError(f'G source/platform drift: {platform}')
    return {'engine': engine, 'versions': versions, 'capsule': definitions,
            'migration_bytes': len(source), 'migration_sha256': digests[0],
            'platform_sha256': platform[0]}


def run():
    result = {'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
              'classification': 'DISPOSABLE_NATIVE_POSTGRESQL_AFTER_E_F_G',
              'production_go': False, 'cases': {}}
    with psycopg.connect(os.environ['PGURL'], autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("set local timezone='UTC'; set local statement_timeout='180s'; set local lock_timeout='8s'")
            result['runtime'] = runtime(cur)
            cur.execute("select set_config('request.jwt.claims',%s,true)",
                        (json.dumps({'sub': base.OPERATOR_AUTH, 'role': 'authenticated'}),))
            cur.execute("select set_config('app.change_reason','G independent native regression',true)")
            base.load_fixture_foundation(cur)
            cur.execute(Path('supabase/tests/cp6_independent_n_regression.sql').read_text(), prepare=False)
            for name in CASES:
                cur.execute('savepoint g_case')
                try:
                    result['cases'][name] = base.one(cur, f'select pg_temp.{name}()')
                except Exception as exc:
                    result['cases'][name] = {'status': 'FAIL', 'error': str(exc),
                                            'sqlstate': getattr(exc, 'sqlstate', None)}
                finally:
                    cur.execute('rollback to savepoint g_case; release savepoint g_case')
            if base.one(cur, 'select count(*) from erp.cp6_laundry_qc_execution_context') != 0:
                raise AssertionError('G execution-context residue')
        conn.rollback()
        result['all_case_effects_rolled_back'] = True
    result['status'] = 'PASS' if all(r['status'] == 'PASS' for r in result['cases'].values()) else 'FAIL'
    return result


if __name__ == '__main__':
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = run()
    except Exception as exc:
        result = {'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'), 'status': 'FAIL',
                  'error': str(exc), 'production_go': False}
    REPORT.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))
    if result['status'] != 'PASS':
        raise SystemExit(1)
