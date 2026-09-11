#!/usr/bin/env python3
"""Trusted N capsule and helper guards plus maintenance-only exact N-to-M restore."""
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
    'supabase/rollbacks/20260911124328_erp_v2_6_20n_cp6_supplier_cent_lifecycle.rollback.sql'
)
REPORT = Path('cp6-proof/CP6_V2620N_ROLLBACK_GUARDS.json')
MAINTENANCE_REPORT = Path('cp6-proof/V2620N_MAIN_MAINTENANCE_ROLLBACK.json')
CLONE_ROOT = Path('cp6-proof/N_TRUSTED_CAPSULE_GUARD')
DIRECT_N_GUARD_NAMES = (
    'platform_bytes', 'successor', 'definition_drift', 'acl_drift',
    'boundary_drift', 'post_install_boundary_history',
    'coherent_capsule_and_checksum',
) + ('helper_definition', 'helper_acl', 'fact_trigger', 'fact_grant', 'inherited_fact_guard')
EXTRA_FAULTS = (
    ('helper_definition', 'alter function erp._cp6_supplier_cent_state(uuid[]) cost 999',
     'N_EXTRA_FUNCTION_OWNER_ACL_MISMATCH', 'Exact predecessor function/ACL mismatch'),
    ('helper_acl', 'grant execute on function erp._cp6_supplier_cent_ledger(uuid[]) to anon',
     'N_EXTRA_FUNCTION_OWNER_ACL_MISMATCH', 'Exact predecessor function/ACL mismatch'),
    ('fact_trigger', 'alter table erp.supplier_cent_posting_facts disable trigger trg_supplier_cent_fact_append_only',
     'N_CENT_FACT_SECURITY_MISMATCH', 'N_CENT_FACT_SECURITY_MISMATCH'),
    ('fact_grant', 'grant select on erp.supplier_cent_posting_facts to authenticated',
     'N_CENT_FACT_SECURITY_MISMATCH', 'N_CENT_FACT_SECURITY_MISMATCH'),
    ('inherited_fact_guard', 'alter function erp.guard_sales_payment_fact_append_only() cost 999',
     'N_INHERITED_FACT_GUARD_MISMATCH', 'Exact predecessor function/ACL mismatch'),
)


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


def coherent_capsule_fault(pgurl: str) -> tuple[str, str, str]:
    with psycopg.connect(pgurl, autocommit=False) as conn, conn.cursor() as cur:
        cur.execute(
            """select object_regidentity,object_definition,definition_sha256
               from erp.cp6_v2620n_rollback_capsule
               order by object_regidentity limit 1"""
        )
        identity, definition, original_sha = cur.fetchone()
        tampered = canonical_cost_tamper(definition)
        cur.execute(
            """update erp.cp6_v2620n_rollback_capsule
               set object_definition=%s,
                 definition_sha256=encode(extensions.digest(
                   convert_to(%s,'UTF8'),'sha256'),'hex')
               where object_regidentity=%s""",
            (tampered, tampered, identity),
        )
        cur.execute(
            """select definition_sha256
               from erp.cp6_v2620n_rollback_capsule
               where object_regidentity=%s""",
            (identity,),
        )
        tampered_sha = cur.fetchone()[0]
        conn.commit()
    if tampered_sha == original_sha:
        raise AssertionError('Coherent capsule mutation did not change checksum')
    return identity, original_sha, tampered_sha


def verify_n_capsule_fault() -> dict[str, Any]:
    """Return public verification outcomes, never capsule contents or credentials."""
    CLONE_ROOT.mkdir(parents=True, exist_ok=True)
    marker = maintenance.TARGETS['N']['marker']
    with disposable_clone_confirmation(matrix.CLONE):
        try:
            matrix.prepare('N', 'REPORT', CLONE_ROOT, source_generation='N')
            coherent_capsule_fault(matrix.CLONE)
            rejection = None
            try:
                maintenance.run_maintenance_rollback(
                    target_name='N',
                    target_pgurl=matrix.CLONE,
                    maintenance_pgurl=matrix.ADMISSION_CONTROL,
                    report_path=CLONE_ROOT / 'maintenance.json',
                    drain_timeout=5,
                    natural_grace=0,
                    terminate_after_grace=True,
                )
            except maintenance.MaintenanceRollbackError as exc:
                rejection = str(exc)
            if rejection is None or 'TRUSTED_PREDECESSOR_PIN_MISMATCH' not in rejection:
                raise AssertionError(f'N coherent capsule fault was not rejected: {rejection}')
            observed = matrix.read_json_if_present(CLONE_ROOT / 'maintenance.json') or {}
            if observed.get('admission_closed') or observed.get('rollback_started'):
                raise AssertionError(f'N trust failure crossed mutation boundary: {observed}')
            with psycopg.connect(matrix.CLONE, autocommit=True) as conn, conn.cursor() as cur:
                cur.execute(
                    'select count(*) from erp.schema_migrations where version=%s',
                    (marker,),
                )
                marker_count = cur.fetchone()[0]
            if marker_count != 1:
                raise AssertionError('N trusted guard changed installed generation')
            return {
                'target': 'N',
                'status': 'PASS',
                'coherent_checksum_changed': True,
                'trusted_pin_rejected': True,
                'admission_closed': False,
                'rollback_started': False,
                'installed_generation_preserved': True,
            }
        finally:
            try:
                matrix.reopen_clone()
            except Exception:
                pass
            matrix.legacy.drop_clone()


def direct_n_guards(target_pgurl: str) -> list[dict[str, Any]]:
    rollback_sql = ROLLBACK.read_text()
    with psycopg.connect(target_pgurl, autocommit=False) as conn:
        with conn.cursor() as cur:
            before = function_catalog(cur)
            cur.execute(
                """select object_regidentity,object_definition
                   from erp.cp6_v2620n_rollback_capsule
                   order by object_regidentity limit 1"""
            )
            identity, definition = cur.fetchone()
            coherent = canonical_cost_tamper(definition)
        conn.commit()
        cases = (
            (
                'platform_bytes',
                "update supabase_migrations.schema_migrations set statements=array['tampered N'] where name='erp_v2_6_20n_cp6_supplier_cent_lifecycle'",
                'N_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR',
                None,
            ),
            (
                'successor',
                "insert into supabase_migrations.schema_migrations(version,statements,name) values('99999999999999',array['successor'],'j_successor_probe')",
                'N_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR',
                None,
            ),
            (
                'definition_drift',
                'alter function erp.run_v267_financial_truth_checks() cost 999',
                'N_TRUSTED_PREDECESSOR_PIN_MISMATCH',
                None,
            ),
            (
                'acl_drift',
                'grant execute on function erp.run_v267_financial_truth_checks() to anon',
                'N_TRUSTED_PREDECESSOR_PIN_MISMATCH',
                None,
            ),
            (
                'boundary_drift',
                "update erp.cp6_v2620n_rollback_capsule set boundary_snapshot=boundary_snapshot-'sales_payments'",
                'N_BOUNDARY_SNAPSHOT_MISMATCH',
                None,
            ),
            (
                'post_install_boundary_history',
                "update erp.cp6_v2620i_rollback_capsule set boundary_snapshot=boundary_snapshot||'{\"j_post_use_probe\":true}'::jsonb",
                'N_POST_USE_ROLLBACK_REFUSED',
                None,
            ),
            (
                'coherent_capsule_and_checksum',
                None,
                'N_TRUSTED_PREDECESSOR_PIN_MISMATCH',
                coherent,
            ),
        ) + tuple((name, mutation, rejection, None) for name, mutation, rejection, _ in EXTRA_FAULTS)
        if tuple(case[0] for case in cases) != DIRECT_N_GUARD_NAMES:
            raise AssertionError('Direct N guard case manifest drift')
        for name, mutation, expected_error, coherent_definition in cases:
            error = None
            try:
                with conn.cursor() as cur:
                    if coherent_definition is None:
                        cur.execute(mutation, prepare=False)
                    else:
                        cur.execute(
                            """update erp.cp6_v2620n_rollback_capsule
                               set object_definition=%s,
                                 definition_sha256=encode(extensions.digest(
                                   convert_to(%s,'UTF8'),'sha256'),'hex')
                               where object_regidentity=%s""",
                            (coherent_definition, coherent_definition, identity),
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
    # Build public labels from the fixed case manifest only after every guard
    # has rejected its fault and its transaction/catalog residue was checked.
    # Do not propagate fields from tuples that also carry database definitions.
    return [
        {'case': name, 'status': 'PASS', 'expected_rejection_observed': True}
        for name in DIRECT_N_GUARD_NAMES
    ]


def verify_extra_preflight_guards() -> list[dict[str, Any]]:
    """Committed object faults must stop before database admission is touched."""
    results = []
    with disposable_clone_confirmation(matrix.CLONE):
        for name, mutation, _, expected in EXTRA_FAULTS:
            folder = CLONE_ROOT / name
            folder.mkdir(parents=True, exist_ok=True)
            try:
                matrix.prepare('N', 'REPORT', folder, source_generation='N')
                with psycopg.connect(matrix.CLONE, autocommit=True) as conn:
                    conn.execute(mutation, prepare=False)
                rejection = None
                try:
                    maintenance.run_maintenance_rollback(
                        target_name='N', target_pgurl=matrix.CLONE,
                        maintenance_pgurl=matrix.ADMISSION_CONTROL,
                        report_path=folder / 'maintenance.json', drain_timeout=5,
                        natural_grace=0, terminate_after_grace=True,
                    )
                except (maintenance.MaintenanceRollbackError, AssertionError) as exc:
                    rejection = str(exc)
                if rejection is None or expected not in rejection:
                    raise AssertionError('N_EXTRA_PREFLIGHT_WRONG_REJECTION: ' + name)
                observed = matrix.read_json_if_present(folder / 'maintenance.json') or {}
                if observed.get('admission_closed') or observed.get('rollback_started'):
                    raise AssertionError('N_EXTRA_PREFLIGHT_MUTATED_ADMISSION: ' + name)
                with psycopg.connect(matrix.ADMISSION_CONTROL, autocommit=True) as conn:
                    admission = conn.execute("select datallowconn from pg_database where datname='cp6_rollback'").fetchone()
                with psycopg.connect(matrix.CLONE, autocommit=True) as conn:
                    marker = conn.execute("select count(*) from erp.schema_migrations where version='v2.6.20n'").fetchone()
                if admission != (True,) or marker != (1,):
                    raise AssertionError('N_EXTRA_PREFLIGHT_STATE_CHANGED: ' + name)
                results.append({'case': name, 'status': 'PASS', 'admission_closed': False,
                    'rollback_started': False, 'installed_generation_preserved': True})
            finally:
                try:
                    matrix.reopen_clone()
                except Exception:
                    pass
                matrix.legacy.drop_clone()
    return results


def verify_exact_m_restore(target_pgurl: str) -> dict[str, Any]:
    expected = maintenance.TRUSTED_FUNCTIONS['N']
    with psycopg.connect(target_pgurl, autocommit=False) as conn, conn.cursor() as cur:
        actual = maintenance._function_snapshot(conn, expected)
        cur.execute(
            """select not exists(select 1 from erp.schema_migrations where version='v2.6.20n')
              and exists(select 1 from erp.schema_migrations where version='v2.6.20m')
              and not exists(select 1 from supabase_migrations.schema_migrations
                where name='erp_v2_6_20n_cp6_supplier_cent_lifecycle')
              and to_regclass('erp.cp6_v2620n_rollback_capsule') is null
              and to_regclass('erp.supplier_cent_posting_facts') is null
              and to_regprocedure('erp._cp6_supplier_cent_state(uuid[])') is null
              and to_regprocedure('erp._cp6_supplier_cent_ledger(uuid[])') is null
              and to_regprocedure('erp._cp6_apply_supplier_cent_event(text,uuid,date,text,jsonb,boolean)') is null
              and to_regclass('erp.sales_payment_posting_facts') is not null
              and to_regclass('erp.sales_payment_reversal_facts') is not null
              and exists(select 1 from information_schema.columns
                where table_schema='erp' and table_name='sales_payments'
                  and column_name='replaces_payment_id')
              and to_regclass('erp.cp6_v2620m_rollback_capsule') is not null"""
        )
        if cur.fetchone()[0] is not True:
            raise AssertionError('N rollback metadata/schema residue')
    return {
        'generation': 'M',
        'restored_function_count': len(actual),
        # The maintenance report already records the independently observed
        # function hashes, owners and ACLs. Keep this public summary structural;
        # never serialize database-returned values through a conninfo-tainted path.
        'owner_acl_exact': True,
        'metadata_schema_residue': 0,
    }


def run() -> dict[str, Any]:
    target_pgurl = os.environ['PGURL']
    maintenance_pgurl = os.environ['CP6_ADMISSION_CONTROL_PGURL']
    maintenance._validate_connections(target_pgurl, maintenance_pgurl)
    result: dict[str, Any] = {
        'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
        'classification': 'DISPOSABLE_NATIVE_N_TRUSTED_GUARDS_AND_CLOSED_ADMISSION_RESTORE',
        'rollback_sha256': hashlib.sha256(ROLLBACK.read_bytes()).hexdigest(),
        'production_go': False,
    }
    result['trusted_capsule_guard'] = verify_n_capsule_fault()
    result['extra_object_preflight_guards'] = verify_extra_preflight_guards()
    result['guards'] = direct_n_guards(target_pgurl)
    maintenance_result = maintenance.run_maintenance_rollback(
        target_name='N',
        target_pgurl=target_pgurl,
        maintenance_pgurl=maintenance_pgurl,
        report_path=MAINTENANCE_REPORT,
        drain_timeout=10,
        natural_grace=.25,
        terminate_after_grace=True,
    )
    if maintenance_result['status'] != 'PASS':
        raise AssertionError(f'N maintenance rollback failed: {maintenance_result}')
    required_phases = {
        'ENDPOINT_VERIFIED', 'CAPSULE_VERIFIED', 'ADMISSION_CLOSED',
        'DRAINED', 'ROLLBACK_STARTED', 'ROLLBACK_COMMITTED',
        'PREDECESSOR_VERIFIED', 'ADMISSION_REOPENED',
    }
    observed_phases = {
        item.get('phase') for item in maintenance_result.get('phases', [])
    }
    if not required_phases.issubset(observed_phases):
        raise AssertionError('N maintenance phase evidence incomplete')
    result.update(
        status='PASS',
        exact_pre_use_restore=verify_exact_m_restore(target_pgurl),
        maintenance={
            'status': 'PASS',
            'target': 'N',
            'endpoint_verified': True,
            'capsule_verified': True,
            'admission_closed_before_rollback': True,
            'old_sessions_drained': True,
            'rollback_committed': True,
            'predecessor_verified': True,
            'admission_reopened_after_success': True,
        },
    )
    return result


def main() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = run()
    except Exception as exc:
        result = {
            'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
            'status': 'FAIL',
            'error_code': 'V2620N_ROLLBACK_GUARD_FAILED',
            'error_type': type(exc).__name__,
            'production_go': False,
        }
    REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps(result, sort_keys=True, default=str))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
