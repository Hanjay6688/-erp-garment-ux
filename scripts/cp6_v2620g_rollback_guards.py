#!/usr/bin/env python3
"""Native pre-use G guard/restore qualification on the disposable CI database."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import psycopg

import cp6_v2620g_independent_regression as regression
import cp6_preuse_rollback_maintenance as maintenance

ROLLBACK = Path('supabase/rollbacks/20260910031103_erp_v2_6_20g_cp6_independent_audit_closure.rollback.sql')
REPORT = Path('cp6-proof/CP6_V2620G_ROLLBACK_GUARDS.json')
MAINTENANCE_REPORT = Path('cp6-proof/V2620G_MAIN_MAINTENANCE_ROLLBACK.json')


def functions(cur):
    cur.execute("""select p.oid::regprocedure::text,pg_get_functiondef(p.oid),
      p.proacl::text,pg_get_userbyid(p.proowner)
      from pg_proc p join pg_namespace n on n.oid=p.pronamespace
      where n.nspname='erp' and p.prokind='f' order by 1""")
    return cur.fetchall()


def run():
    sql = ROLLBACK.read_text()
    result = {'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
              'classification': 'DISPOSABLE_NATIVE_G_PRE_USE_ROLLBACK',
              'rollback_sha256': hashlib.sha256(ROLLBACK.read_bytes()).hexdigest(),
              'production_go': False, 'guards': []}
    with psycopg.connect(os.environ['PGURL'], autocommit=False) as conn:
        with conn.cursor() as cur:
            result['runtime_before'] = regression.runtime(cur)
            before = functions(cur)
            cur.execute('select object_regidentity,definition_sha256,acl_snapshot,owner_snapshot from erp.cp6_v2620g_rollback_capsule order by object_regidentity')
            expected = cur.fetchall()
        conn.commit()
        cases = (
            ('platform_bytes', "update supabase_migrations.schema_migrations set statements=array[array_to_string(statements,E'\n')||'tamper'] where name='erp_v2_6_20g_cp6_independent_audit_closure'", 'exact platform ledger identity'),
            ('successor', "insert into supabase_migrations.schema_migrations(version,statements,name) values('99999999999999',array['disposable successor'],'g_successor_probe')", 'successor installed'),
            ('definition_drift', 'alter function erp.post_fg_adjustment(uuid) cost 999', 'DRIFT_CONCURRENT_MUTATION_DETECTED'),
            ('acl_drift', 'grant execute on function erp.post_fg_adjustment(uuid) to anon', 'DRIFT_CONCURRENT_MUTATION_DETECTED'),
            ('boundary_drift', "update erp.cp6_v2620g_rollback_capsule set boundary_snapshot=boundary_snapshot-'products'", 'incomplete business boundary'),
        )
        for name, mutation, expected_error in cases:
            error = None
            try:
                with conn.cursor() as cur:
                    cur.execute(mutation, prepare=False)
                    cur.execute(sql, prepare=False)
            except psycopg.Error as exc:
                error = str(exc)
            finally:
                conn.rollback()
            if error is None or expected_error not in error:
                raise AssertionError(f'{name}: wrong/missing rejection {error}')
            with conn.cursor() as cur:
                if functions(cur) != before:
                    raise AssertionError(f'{name}: guard left function/ACL residue')
            conn.commit()
            result['guards'].append({'case': name, 'status': 'PASS', 'rejection': error.splitlines()[0]})
    maintenance_result = maintenance.run_maintenance_rollback(
        target_name='G', target_pgurl=os.environ['PGURL'],
        maintenance_pgurl=os.environ['CP6_ADMISSION_CONTROL_PGURL'],
        report_path=MAINTENANCE_REPORT, drain_timeout=10,
        natural_grace=.25, terminate_after_grace=True,
    )
    restored = []
    with psycopg.connect(os.environ['PGURL'], autocommit=False) as conn, conn.cursor() as cur:
        for identity, digest, acl, owner in expected:
            cur.execute("""select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
              case when p.proacl is null then null else array(select a::text from unnest(p.proacl) a order by a::text) end,
              pg_get_userbyid(p.proowner) from pg_proc p where p.oid=to_regprocedure(%s)""", (identity,))
            actual = cur.fetchone()
            if actual != (digest, acl, owner):
                raise AssertionError(f'G exact F restore failed {identity}: {actual}')
            restored.append({'identity': identity, 'restored_sha256': digest, 'owner_acl_exact': True})
        cur.execute("""select not exists(select 1 from erp.schema_migrations where version='v2.6.20g')
          and exists(select 1 from erp.schema_migrations where version='v2.6.20f')
          and not exists(select 1 from supabase_migrations.schema_migrations where name='erp_v2_6_20g_cp6_independent_audit_closure')
          and to_regclass('erp.cp6_v2620g_rollback_capsule') is null""")
        if cur.fetchone()[0] is not True:
            raise AssertionError('G rollback metadata residue')
    result.update(status='PASS', exact_pre_use_restore=restored,
                  maintenance=maintenance_result, metadata_residue=0)
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
