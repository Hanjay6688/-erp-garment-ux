#!/usr/bin/env python3
"""Trusted F/G/H/I capsule guards plus maintenance-only exact I-to-H restore."""
from __future__ import annotations

import hashlib
import json
import os
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_preuse_rollback_maintenance as maintenance
import cp6_v2620h_maintenance_rollback_matrix as matrix


ROLLBACK = Path(
    'supabase/rollbacks/20260910100051_erp_v2_6_20i_cp6_h2_audit_closure.rollback.sql'
)
REPORT = Path('cp6-proof/CP6_V2620I_ROLLBACK_GUARDS.json')
MAINTENANCE_REPORT = Path('cp6-proof/V2620I_MAIN_MAINTENANCE_ROLLBACK.json')
CLONE_ROOT = Path('cp6-proof/I_TRUSTED_CAPSULE_GUARDS')


@contextmanager
def disposable_clone_confirmation(pgurl: str):
    """Temporarily confirm only the fixed disposable rollback clone."""
    database = conninfo_to_dict(pgurl).get('dbname', '')
    if database != 'cp6_rollback':
        raise AssertionError(f'Refusing non-disposable guard database: {database}')
    previous = os.environ.get('CP6_MAINTENANCE_CONFIRM_DATABASE')
    os.environ['CP6_MAINTENANCE_CONFIRM_DATABASE'] = database
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop('CP6_MAINTENANCE_CONFIRM_DATABASE', None)
        else:
            os.environ['CP6_MAINTENANCE_CONFIRM_DATABASE'] = previous


def function_catalog(cur: psycopg.Cursor) -> list[tuple[Any, ...]]:
    cur.execute(
        """select p.oid::regprocedure::text,pg_get_functiondef(p.oid),
          p.proacl::text,pg_get_userbyid(p.proowner)
          from pg_proc p join pg_namespace n on n.oid=p.pronamespace
          where n.nspname='erp' and p.prokind='f' order by 1"""
    )
    return cur.fetchall()


def canonical_cost_tamper(definition: str) -> str:
    tampered, count = re.subn(
        r'\nAS (\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$)',
        r'\nCOST 999\nAS \1',
        definition,
        count=1,
    )
    if count != 1 or tampered == definition:
        raise AssertionError('Could not build deterministic coherent capsule fault')
    return tampered


def coherent_capsule_fault(
    pgurl: str, capsule: str
) -> tuple[str, str, str]:
    with psycopg.connect(pgurl, autocommit=False) as conn, conn.cursor() as cur:
        cur.execute(
            f"""select object_regidentity,object_definition,definition_sha256
                from {capsule} order by object_regidentity limit 1"""
        )
        identity, definition, original_sha = cur.fetchone()
        tampered = canonical_cost_tamper(definition)
        cur.execute(
            f"""update {capsule} set object_definition=%s,
                  definition_sha256=encode(extensions.digest(convert_to(%s,'UTF8'),'sha256'),'hex')
                where object_regidentity=%s""",
            (tampered, tampered, identity),
        )
        cur.execute(
            f'select definition_sha256 from {capsule} where object_regidentity=%s',
            (identity,),
        )
        tampered_sha = cur.fetchone()[0]
        conn.commit()
    if tampered_sha == original_sha:
        raise AssertionError('Coherent capsule mutation did not change its checksum')
    return identity, original_sha, tampered_sha


def trusted_capsule_guards() -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    CLONE_ROOT.mkdir(parents=True, exist_ok=True)
    for target in ('F', 'G', 'H', 'I'):
        folder = CLONE_ROOT / target
        folder.mkdir(exist_ok=True)
        marker = maintenance.TARGETS[target]['marker']
        capsule = maintenance.TARGETS[target]['capsule']
        with disposable_clone_confirmation(matrix.CLONE):
            try:
                matrix.prepare(target, 'REPORT', folder)
                identity, original_sha, tampered_sha = coherent_capsule_fault(
                    matrix.CLONE, capsule
                )
                rejection = None
                try:
                    maintenance.run_maintenance_rollback(
                        target_name=target,
                        target_pgurl=matrix.CLONE,
                        maintenance_pgurl=matrix.ADMISSION_CONTROL,
                        report_path=folder / 'maintenance.json',
                        drain_timeout=5,
                        natural_grace=0,
                        terminate_after_grace=True,
                    )
                except maintenance.MaintenanceRollbackError as exc:
                    rejection = str(exc)
                if rejection is None or 'TRUSTED_PREDECESSOR_PIN_MISMATCH' not in rejection:
                    raise AssertionError(f'{target} coherent capsule fault was not rejected: {rejection}')
                report = matrix.read_json_if_present(folder / 'maintenance.json') or {}
                if report.get('admission_closed') or report.get('rollback_started'):
                    raise AssertionError(f'{target} trust failure occurred after mutation boundary: {report}')
                with psycopg.connect(matrix.CLONE, autocommit=True) as conn, conn.cursor() as cur:
                    cur.execute(
                        'select count(*) from erp.schema_migrations where version=%s',
                        (marker,),
                    )
                    marker_count = cur.fetchone()[0]
                if marker_count != 1:
                    raise AssertionError(f'{target} trusted guard changed installed generation')
                results.append({
                    'target': target,
                    'status': 'PASS',
                    'identity': identity,
                    'original_predecessor_sha256': original_sha,
                    'coherently_tampered_sha256': tampered_sha,
                    'rejection': rejection,
                    'admission_closed': False,
                    'rollback_started': False,
                    'installed_generation_preserved': True,
                })
            finally:
                try:
                    matrix.reopen_clone()
                except Exception:
                    pass
                matrix.legacy.drop_clone()
    return results


def direct_i_guards(target_pgurl: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rollback_sql = ROLLBACK.read_text()
    results: list[dict[str, Any]] = []
    with psycopg.connect(target_pgurl, autocommit=False) as conn:
        with conn.cursor() as cur:
            before = function_catalog(cur)
            cur.execute(
                """select object_regidentity,definition_sha256,acl_snapshot,owner_snapshot
                   from erp.cp6_v2620i_rollback_capsule"""
            )
            predecessor = cur.fetchone()
            if predecessor is None:
                raise AssertionError('I capsule missing before rollback guards')
            coherent = canonical_cost_tamper(base_definition_for(cur))
        conn.commit()
        cases = (
            (
                'platform_bytes',
                "update supabase_migrations.schema_migrations set statements=array['tampered I'] where name='erp_v2_6_20i_cp6_h2_audit_closure'",
                'exact platform ledger identity',
                None,
            ),
            (
                'successor',
                "insert into supabase_migrations.schema_migrations(version,statements,name) values('99999999999999',array['successor'],'i_successor_probe')",
                'successor installed',
                None,
            ),
            (
                'definition_drift',
                'alter function erp.run_v268_financial_report_checks() cost 999',
                'TRUSTED_PREDECESSOR_PIN_MISMATCH',
                None,
            ),
            (
                'acl_drift',
                'grant execute on function erp.run_v268_financial_report_checks() to anon',
                'TRUSTED_PREDECESSOR_PIN_MISMATCH',
                None,
            ),
            (
                'boundary_drift',
                "update erp.cp6_v2620i_rollback_capsule set boundary_snapshot=boundary_snapshot-'sales_payments'",
                'incomplete business boundary',
                None,
            ),
            (
                'coherent_capsule_and_checksum',
                None,
                'TRUSTED_PREDECESSOR_PIN_MISMATCH',
                coherent,
            ),
        )
        for name, mutation, expected_error, coherent_definition in cases:
            error = None
            try:
                with conn.cursor() as cur:
                    if coherent_definition is None:
                        cur.execute(mutation, prepare=False)
                    else:
                        cur.execute(
                            """update erp.cp6_v2620i_rollback_capsule
                               set object_definition=%s,
                                 definition_sha256=encode(extensions.digest(
                                   convert_to(%s,'UTF8'),'sha256'),'hex')""",
                            (coherent_definition, coherent_definition),
                        )
                    cur.execute(rollback_sql, prepare=False)
            except psycopg.Error as exc:
                error = str(exc)
            finally:
                conn.rollback()
            if error is None or expected_error not in error:
                raise AssertionError(f'{name}: wrong/missing rejection {error}')
            with conn.cursor() as cur:
                if function_catalog(cur) != before:
                    raise AssertionError(f'{name}: guard left function/ACL residue')
            conn.commit()
            results.append(
                {'case': name, 'status': 'PASS', 'rejection': error.splitlines()[0]}
            )
    return results, {
        'identity': predecessor[0],
        'predecessor_sha256': predecessor[1],
        'acl': predecessor[2],
        'owner': predecessor[3],
    }


def base_definition_for(cur: psycopg.Cursor) -> str:
    cur.execute('select object_definition from erp.cp6_v2620i_rollback_capsule')
    return cur.fetchone()[0]


def run() -> dict[str, Any]:
    target_pgurl = os.environ['PGURL']
    maintenance_pgurl = os.environ['CP6_ADMISSION_CONTROL_PGURL']
    result: dict[str, Any] = {
        'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
        'classification': 'DISPOSABLE_NATIVE_I_TRUSTED_GUARDS_AND_CLOSED_ADMISSION_RESTORE',
        'rollback_sha256': hashlib.sha256(ROLLBACK.read_bytes()).hexdigest(),
        'production_go': False,
    }
    result['trusted_capsule_guards'] = trusted_capsule_guards()
    result['guards'], predecessor = direct_i_guards(target_pgurl)

    maintenance_result = maintenance.run_maintenance_rollback(
        target_name='I',
        target_pgurl=target_pgurl,
        maintenance_pgurl=maintenance_pgurl,
        report_path=MAINTENANCE_REPORT,
        drain_timeout=10,
        natural_grace=.25,
        terminate_after_grace=True,
    )
    if maintenance_result['status'] != 'PASS':
        raise AssertionError(f'I maintenance rollback failed: {maintenance_result}')

    with psycopg.connect(target_pgurl, autocommit=False) as conn, conn.cursor() as cur:
        cur.execute(
            """select encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),
                 'UTF8'),'sha256'),'hex'),
                 case when p.proacl is null then null else
                   array(select a::text from unnest(p.proacl) a order by a::text) end,
                 pg_get_userbyid(p.proowner)
               from pg_proc p where p.oid='erp.run_v268_financial_report_checks()'::regprocedure"""
        )
        actual = cur.fetchone()
        expected = (
            predecessor['predecessor_sha256'], predecessor['acl'], predecessor['owner']
        )
        if actual != expected:
            raise AssertionError(f'I exact H restore failed: {actual} != {expected}')
        cur.execute(
            """select not exists(select 1 from erp.schema_migrations where version='v2.6.20i')
              and exists(select 1 from erp.schema_migrations where version='v2.6.20h')
              and not exists(select 1 from supabase_migrations.schema_migrations
                where name='erp_v2_6_20i_cp6_h2_audit_closure')
              and to_regclass('erp.cp6_v2620i_rollback_capsule') is null
              and to_regclass('erp.cp6_v2620h_rollback_capsule') is not null"""
        )
        if cur.fetchone()[0] is not True:
            raise AssertionError('I rollback metadata residue')
    result.update(
        status='PASS',
        exact_pre_use_restore={
            'identity': predecessor['identity'],
            'restored_sha256': predecessor['predecessor_sha256'],
            'owner_acl_exact': True,
        },
        maintenance=maintenance_result,
        metadata_residue=0,
    )
    return result


def main() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = run()
    except Exception as exc:
        result = {
            'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
            'status': 'FAIL', 'error': str(exc), 'production_go': False,
        }
    REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps(result, sort_keys=True, default=str))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
