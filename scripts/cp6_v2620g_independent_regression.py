#!/usr/bin/env python3
"""Exact-G native SQL regressions; transaction/savepoint isolated, never hosted."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import psycopg
import cp6_v2620k_runtime as k_runtime

import cp6_v2620e_counterexample_regression as base

MIGRATION = Path('supabase/migrations/20260910031103_erp_v2_6_20g_cp6_independent_audit_closure.sql')
SUCCESSOR_J = Path('supabase/migrations/20260910170556_erp_v2_6_20j_cp6_payment_fact_closure.sql')
CASES = ('g_n01_split_loss', 'g_n01_gain_lumped', 'g_n02_multiline',
         'g_n02_corrected_loss', 'g_n02_zero_minor_units', 'g_n03_source_detector',
         'g_n01_threshold_matrix', 'g_n02_reserved_reprice')
REPORT = Path(os.environ.get('CP6_G_REPORT', 'cp6-proof/CP6_V2620G_INDEPENDENT_REGRESSION.json'))


def runtime(cur):
    k_successor = k_runtime.verified_successor(cur)
    cur.execute("select version()")
    engine = cur.fetchone()[0]
    cur.execute("select version from erp.schema_migrations where version in('v2.6.20e','v2.6.20f','v2.6.20g','v2.6.20h','v2.6.20i','v2.6.20j') order by version")
    versions = [r[0] for r in cur.fetchall()]
    if versions not in (
        ['v2.6.20e', 'v2.6.20f', 'v2.6.20g'],
        ['v2.6.20e', 'v2.6.20f', 'v2.6.20g', 'v2.6.20h'],
        ['v2.6.20e', 'v2.6.20f', 'v2.6.20g', 'v2.6.20h', 'v2.6.20i'],
        ['v2.6.20e', 'v2.6.20f', 'v2.6.20g', 'v2.6.20h', 'v2.6.20i', 'v2.6.20j'],
    ):
        raise AssertionError(f'Final E+F+G with optional forward H/I/J runtime not present: {versions}')
    has_h = 'v2.6.20h' in versions
    has_i = 'v2.6.20i' in versions
    has_j = 'v2.6.20j' in versions
    cur.execute("""select object_regidentity,installed_definition_sha256,
      encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),
        'UTF8'),'sha256'),'hex') actual from erp.cp6_v2620g_rollback_capsule
      order by object_regidentity""")
    definitions = [dict(zip(('identity', 'installed_sha256', 'actual_sha256'), r)) for r in cur.fetchall()]
    successor = []
    successor_i = []
    successor_j = []
    i_by_identity = {}
    if has_i:
        cur.execute("""select object_regidentity,definition_sha256,installed_definition_sha256,
          encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),
            'UTF8'),'sha256'),'hex') actual from erp.cp6_v2620i_rollback_capsule""")
        successor_i = [dict(zip(
            ('identity', 'predecessor_sha256', 'installed_sha256', 'actual_sha256'), r
        )) for r in cur.fetchall()]
        i_by_identity = {item['identity']: item['installed_sha256'] for item in successor_i}
    j_by_identity = {}
    if has_j:
        cur.execute("""select object_regidentity,definition_sha256,installed_definition_sha256,
          encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),
            'UTF8'),'sha256'),'hex') actual from erp.cp6_v2620j_rollback_capsule
          order by object_regidentity""")
        successor_j = [dict(zip(
            ('identity', 'predecessor_sha256', 'installed_sha256', 'actual_sha256'), r
        )) for r in cur.fetchall()]
        j_by_identity = {item['identity']: item['installed_sha256'] for item in successor_j}
        for item in successor_i:
            item['i_installed_sha256'] = item['installed_sha256']
            if item['identity'] in j_by_identity:
                item['installed_sha256'] = j_by_identity[item['identity']]
                item['expected_generation'] = 'J'
    if has_h:
        cur.execute("""select object_regidentity,installed_definition_sha256,
          encode(extensions.digest(convert_to(pg_get_functiondef(to_regprocedure(object_regidentity)),
            'UTF8'),'sha256'),'hex') actual from erp.cp6_v2620h_rollback_capsule
          order by object_regidentity""")
        successor = [dict(zip(('identity', 'installed_sha256', 'actual_sha256'), r)) for r in cur.fetchall()]
        h_by_identity = {item['identity']: item['installed_sha256'] for item in successor}
        for item in successor:
            item['h_installed_sha256'] = item['installed_sha256']
            if item['identity'] in i_by_identity:
                item['installed_sha256'] = i_by_identity[item['identity']]
                item['expected_generation'] = 'I'
            if item['identity'] in j_by_identity:
                item['installed_sha256'] = j_by_identity[item['identity']]
                item['expected_generation'] = 'J'
        for item in definitions:
            item['g_installed_sha256'] = item['installed_sha256']
            if item['identity'] in h_by_identity:
                item['installed_sha256'] = h_by_identity[item['identity']]
                item['expected_generation'] = 'H'
            else:
                item['expected_generation'] = 'G'
            if item['identity'] in i_by_identity:
                item['installed_sha256'] = i_by_identity[item['identity']]
                item['expected_generation'] = 'I'
            if item['identity'] in j_by_identity:
                item['installed_sha256'] = j_by_identity[item['identity']]
                item['expected_generation'] = 'J'
    for collection in (definitions, successor, successor_i, successor_j):
        k_runtime.extend_items(k_successor, collection)
    if len(definitions) != 7 or any(
        r['installed_sha256'] != r['actual_sha256'] for r in definitions
    ):
        raise AssertionError('Effective G functions differ from G/H/I/J capsule lineage')
    if has_h and (
        len(successor) != 6
        or any(r['installed_sha256'] != r['actual_sha256'] for r in successor)
    ):
        raise AssertionError('H successor functions differ from effective H/I/J capsule lineage')
    if has_i and (
        len(successor_i) != 1
        or successor_i[0]['predecessor_sha256'] != '3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f'
        or successor_i[0]['installed_sha256'] != successor_i[0]['actual_sha256']
    ):
        raise AssertionError('I successor report differs from effective I/J capsule lineage')
    if has_j and (
        len(successor_j) != 3
        or any(item['installed_sha256'] != item['actual_sha256'] for item in successor_j)
    ):
        raise AssertionError('J successor functions differ from J capsule')
    cur.execute("""select encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),
      'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations
      where name='erp_v2_6_20g_cp6_independent_audit_closure'""")
    platform = [r[0] for r in cur.fetchall()]
    source = MIGRATION.read_bytes()
    digests = [hashlib.sha256(source).hexdigest(), hashlib.sha256(source[:-1]).hexdigest()]
    if len(platform) != 1 or platform[0] not in digests:
        raise AssertionError(f'G source/platform drift: {platform}')
    j_source = SUCCESSOR_J.read_bytes() if has_j else b''
    j_platform = None
    if has_j:
        cur.execute("""select encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),
          'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations
          where name='erp_v2_6_20j_cp6_payment_fact_closure'""")
        j_platform = cur.fetchone()[0]
        if j_platform not in (
            hashlib.sha256(j_source).hexdigest(), hashlib.sha256(j_source[:-1]).hexdigest()
        ):
            raise AssertionError(f'J source/platform drift: {j_platform}')
    return {'engine': engine, 'versions': versions + (['v2.6.20k'] if k_successor else []), 'capsule': definitions,
            'successor_capsule': successor,
            'successor_i_capsule': successor_i,
            'successor_j_capsule': successor_j,
            'migration_bytes': len(source), 'migration_sha256': digests[0],
            'platform_sha256': platform[0],
            'successor_j_migration_sha256': hashlib.sha256(j_source).hexdigest() if has_j else None,
            'successor_j_platform_sha256': j_platform}


def run():
    result = {'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
              'classification': 'DISPOSABLE_NATIVE_POSTGRESQL_AFTER_E_F_G_WITH_OPTIONAL_FORWARD_H_I_J',
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
