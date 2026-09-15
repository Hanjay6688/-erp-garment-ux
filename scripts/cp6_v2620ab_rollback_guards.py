#!/usr/bin/env python3
"""Trusted AB capsule guards and maintenance-only exact AB-to-AA restore."""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

import cp6_preuse_rollback_maintenance as maintenance
import cp6_v2620h_maintenance_rollback_matrix as matrix
import cp6_v2620n_rollback_guards as n_guards

ROLLBACK = Path(
    'supabase/rollbacks/20260914190500_erp_v2_6_20ab_cp6_operational_business_clock.rollback.sql'
)
REPORT = Path('cp6-proof/CP6_V2620AB_ROLLBACK_GUARDS.json')
DIRECT_REPORT = Path('cp6-proof/CP6_V2620AB_DIRECT_GUARD_DIAGNOSTICS.json')
EXTRA_REPORT = Path('cp6-proof/CP6_V2620AB_EXTRA_GUARD_DIAGNOSTICS.json')
MAINTENANCE_REPORT = Path('cp6-proof/V2620AB_MAIN_MAINTENANCE_ROLLBACK.json')
CLONE_ROOT = Path('cp6-proof/AB_TRUSTED_CAPSULE_GUARD')
DIRECT_GUARD_NAMES = (
    'platform_bytes', 'successor', 'definition_drift', 'acl_drift',
    'boundary_drift', 'post_install_boundary_history',
    'post_install_other_module_history',
    'coherent_capsule_and_checksum',
)
EXTRA_FAULTS = (
    ('ab_definition_process_cost_recalc_queue', 'erp.process_cost_recalc_queue(integer)',
     'alter function erp.process_cost_recalc_queue(integer) cost 999',
     'TRUSTED_PREDECESSOR_PIN_MISMATCH'),
    ('ab_acl_process_cost_recalc_queue', 'erp.process_cost_recalc_queue(integer)',
     'grant execute on function erp.process_cost_recalc_queue(integer) to anon',
     'TRUSTED_PREDECESSOR_PIN_MISMATCH'),
    ('ab_definition_resolve_accounting_transaction_date',
     'erp.resolve_accounting_transaction_date(date)',
     'alter function erp.resolve_accounting_transaction_date(date) cost 999',
     'TRUSTED_PREDECESSOR_PIN_MISMATCH'),
    ('ab_acl_resolve_accounting_transaction_date',
     'erp.resolve_accounting_transaction_date(date)',
     'grant execute on function erp.resolve_accounting_transaction_date(date) to anon',
     'TRUSTED_PREDECESSOR_PIN_MISMATCH'),
    ('ab_definition_reverse_journal_internal',
     'erp._cp3_r4_reverse_journal_internal(uuid,text)',
     'alter function erp._cp3_r4_reverse_journal_internal(uuid,text) cost 999',
     'TRUSTED_PREDECESSOR_PIN_MISMATCH'),
    ('ab_acl_reverse_journal_internal',
     'erp._cp3_r4_reverse_journal_internal(uuid,text)',
     'grant execute on function erp._cp3_r4_reverse_journal_internal(uuid,text) to anon',
     'TRUSTED_PREDECESSOR_PIN_MISMATCH'),
    ('ab_definition_post_journal', 'erp.post_journal(text,uuid,date,text,jsonb)',
     'alter function erp.post_journal(text,uuid,date,text,jsonb) cost 999',
     'TRUSTED_PREDECESSOR_PIN_MISMATCH'),
    ('ab_acl_post_journal', 'erp.post_journal(text,uuid,date,text,jsonb)',
     'grant execute on function erp.post_journal(text,uuid,date,text,jsonb) to anon',
     'TRUSTED_PREDECESSOR_PIN_MISMATCH'),
    ('ab_owner_post_journal', 'erp.post_journal(text,uuid,date,text,jsonb)',
     'alter function erp.post_journal(text,uuid,date,text,jsonb) owner to service_role',
     'TRUSTED_PREDECESSOR_PIN_MISMATCH'),
    ('recost_definition',
     'erp._recalculate_material_cost_core(uuid,timestamptz,boolean)',
     'alter function erp._recalculate_material_cost_core(uuid,timestamptz,boolean) cost 999',
     'TRUSTED_PREDECESSOR_PIN_MISMATCH'),
    ('recost_acl',
     'erp._recalculate_material_cost_core(uuid,timestamptz,boolean)',
     'grant execute on function erp._recalculate_material_cost_core(uuid,timestamptz,boolean) to anon',
     'TRUSTED_PREDECESSOR_PIN_MISMATCH'),
    ('authorization_role_definition',
     'erp.current_app_role()',
     'alter function erp.current_app_role() cost 999',
     'Exact predecessor function/ACL mismatch'),
    ('authorization_identity_acl',
     'erp.current_app_user_id()',
     'grant execute on function erp.current_app_user_id() to anon',
     'Exact predecessor function/ACL mismatch'),
    ('helper_definition',
     'erp._cp6_supplier_cent_state(uuid[])',
     'alter function erp._cp6_supplier_cent_state(uuid[]) cost 999',
     'Exact predecessor function/ACL mismatch'),
    ('helper_acl',
     'erp._cp6_supplier_cent_ledger(uuid[])',
     'grant execute on function erp._cp6_supplier_cent_ledger(uuid[]) to anon',
     'Exact predecessor function/ACL mismatch'),
    ('fact_trigger',
     'erp.supplier_cent_posting_facts',
     'alter table erp.supplier_cent_posting_facts disable trigger trg_supplier_cent_fact_append_only',
     'S_CENT_FACT_SECURITY_MISMATCH'),
    ('fact_grant',
     'erp.supplier_cent_posting_facts',
     'grant select on erp.supplier_cent_posting_facts to authenticated',
     'S_CENT_FACT_SECURITY_MISMATCH'),
    ('inherited_fact_guard',
     'erp.guard_sales_payment_fact_append_only()',
     'alter function erp.guard_sales_payment_fact_append_only() cost 999',
     'Exact predecessor function/ACL mismatch'),
    ('t_helper_definition',
     'erp._cp6_material_adjustment_revaluation_state(uuid)',
     'alter function erp._cp6_material_adjustment_revaluation_state(uuid) cost 999',
     'Exact predecessor function/ACL mismatch'),
    ('t_helper_acl',
     'erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)',
     'grant execute on function erp._cp6_sync_material_adjustment_revaluation(uuid,uuid) to anon',
     'Exact predecessor function/ACL mismatch'),
    ('t_fact_trigger',
     'erp.material_adjustment_revaluation_facts',
     'alter table erp.material_adjustment_revaluation_facts disable trigger trg_material_adjustment_revaluation_fact_append_only',
     'T_ADJUSTMENT_FACT_SECURITY_MISMATCH'),
    ('t_fact_grant',
     'erp.material_adjustment_revaluation_facts',
     'grant select on erp.material_adjustment_revaluation_facts to authenticated',
     'T_ADJUSTMENT_FACT_SECURITY_MISMATCH'),
)


def persist_extra(status: str, results: list[dict[str, Any]]) -> None:
    """Keep a lossless, artifact-safe checkpoint after every fault boundary."""
    EXTRA_REPORT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
        'status': status,
        'expected_case_count': len(EXTRA_FAULTS),
        'completed_case_count': sum(case.get('status') == 'PASS' for case in results),
        'cases': results,
        'production_go': False,
    }
    temporary = EXTRA_REPORT.with_suffix(EXTRA_REPORT.suffix + '.tmp')
    temporary.write_text(json.dumps(payload, indent=2) + '\n')
    temporary.replace(EXTRA_REPORT)


def apply_extra_fault(mutation: str) -> None:
    """Inject privileged catalog drift only into the fixed disposable clone."""
    params = conninfo_to_dict(matrix.CLONE)
    expected = {
        'user': 'postgres', 'password': 'postgres', 'host': '127.0.0.1',
        'port': '54322', 'dbname': 'cp6_rollback',
    }
    if params != expected:
        raise AssertionError('AB_EXTRA_FAULT_CANONICAL_CLONE_REQUIRED')
    params['user'] = 'supabase_admin'
    with psycopg.connect(**params, autocommit=True) as conn:
        identity = conn.execute(
            """select current_database(),current_user,session_user,
              inet_server_addr()::text,inet_server_port(),
              (select rolsuper from pg_roles where rolname=current_user)"""
        ).fetchone()
        if identity != ('cp6_rollback', 'supabase_admin', 'supabase_admin',
                        '127.0.0.1', 54322, True):
            raise AssertionError('AB_EXTRA_FAULT_ENDPOINT_IDENTITY_MISMATCH')
        conn.execute(mutation, prepare=False)


def coherent_capsule_fault(pgurl: str) -> None:
    with psycopg.connect(pgurl, autocommit=False) as conn, conn.cursor() as cur:
        cur.execute("""select object_regidentity,object_definition
          from erp.cp6_v2620ab_rollback_capsule
          order by object_regidentity limit 1""")
        identity, definition = cur.fetchone()
        tampered = n_guards.canonical_cost_tamper(definition)
        cur.execute("""update erp.cp6_v2620ab_rollback_capsule
          set object_definition=%s,
            definition_sha256=encode(extensions.digest(
              convert_to(%s,'UTF8'),'sha256'),'hex')
          where object_regidentity=%s""", (tampered, tampered, identity))
        conn.commit()


def verify_capsule_fault() -> dict[str, Any]:
    CLONE_ROOT.mkdir(parents=True, exist_ok=True)
    with n_guards.disposable_clone_confirmation(matrix.CLONE):
        try:
            matrix.prepare('AB', 'REPORT', CLONE_ROOT, source_generation='AB')
            coherent_capsule_fault(matrix.CLONE)
            rejection = None
            try:
                maintenance.run_maintenance_rollback(
                    target_name='AB', target_pgurl=matrix.CLONE,
                    maintenance_pgurl=matrix.ADMISSION_CONTROL,
                    report_path=CLONE_ROOT / 'maintenance.json',
                    drain_timeout=5, natural_grace=0,
                    terminate_after_grace=True,
                )
            except maintenance.MaintenanceRollbackError as exc:
                rejection = str(exc)
            if rejection is None or 'TRUSTED_PREDECESSOR_PIN_MISMATCH' not in rejection:
                raise AssertionError('AB coherent capsule fault was not rejected')
            observed = matrix.read_json_if_present(
                CLONE_ROOT / 'maintenance.json'
            ) or {}
            if observed.get('admission_closed') or observed.get('rollback_started'):
                raise AssertionError('AB trust failure crossed mutation boundary')
            with psycopg.connect(matrix.CLONE, autocommit=True) as conn:
                marker = conn.execute("""select count(*) from erp.schema_migrations
                  where version='v2.6.20ab'""").fetchone()
            if marker != (1,):
                raise AssertionError('AB trust guard changed installed generation')
            return {
                'target': 'AB', 'status': 'PASS',
                'coherent_checksum_changed': True,
                'trusted_pin_rejected': True,
                'admission_closed': False, 'rollback_started': False,
                'installed_generation_preserved': True,
            }
        finally:
            try:
                matrix.reopen_clone()
            except Exception:
                pass
            matrix.legacy.drop_clone()


def table_boundary(cur: psycopg.Cursor) -> dict[str, Any]:
    cur.execute("""select c.relname from pg_class c
      join pg_namespace n on n.oid=c.relnamespace
      where n.nspname='erp' and c.relkind in('r','p')
        and c.relname not in('schema_migrations','cp6_v2620ab_rollback_capsule')
      order by c.relname""")
    names = [row[0] for row in cur.fetchall()]
    if len(names) != 213:
        raise AssertionError(f'AB_DIRECT_BOUNDARY_CARDINALITY:{len(names)}')
    result = {}
    for name in names:
        cur.execute(sql.SQL("""select count(*),
          encode(extensions.digest(convert_to(
            coalesce(string_agg(row_hash,',' order by row_hash),''),'UTF8'),
            'sha256'),'hex')
          from(select encode(extensions.digest(convert_to(to_jsonb(t)::text,
            'UTF8'),'sha256'),'hex') row_hash from {} t) rows""").format(
                sql.Identifier('erp', name)))
        count, digest = cur.fetchone()
        result[name] = {'rows': count, 'sha256': digest}
    return result


def direct_guards(target_pgurl: str) -> list[dict[str, Any]]:
    rollback_sql = ROLLBACK.read_text()
    results: list[dict[str, Any]] = []

    def persist(status: str) -> None:
        DIRECT_REPORT.parent.mkdir(parents=True, exist_ok=True)
        DIRECT_REPORT.write_text(json.dumps({
            'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
            'status': status, 'guards': results, 'production_go': False,
        }, indent=2) + '\n')

    with psycopg.connect(target_pgurl, autocommit=False) as conn:
        with conn.cursor() as cur:
            before = n_guards.function_catalog(cur)
            cur.execute("""select object_regidentity,object_definition
              from erp.cp6_v2620ab_rollback_capsule
              order by object_regidentity limit 1""")
            identity, definition = cur.fetchone()
            coherent = n_guards.canonical_cost_tamper(definition)
        conn.commit()
        cases = (
            ('platform_bytes',
             "update supabase_migrations.schema_migrations set statements=array['tampered W'] where name='erp_v2_6_20ab_cp6_operational_business_clock'",
             'AB_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR', None),
            ('successor',
             "insert into supabase_migrations.schema_migrations(version,statements,name) values('99999999999999',array['successor'],'r_successor_probe')",
             'AB_ROLLBACK_PLATFORM_IDENTITY_OR_SUCCESSOR', None),
            ('definition_drift',
             'alter function erp.sync_material_cost_revaluation(uuid) cost 999',
             'AB_TRUSTED_PREDECESSOR_PIN_MISMATCH', None),
            ('acl_drift',
             'grant execute on function erp.sync_material_cost_revaluation(uuid) to anon',
             'AB_TRUSTED_PREDECESSOR_PIN_MISMATCH', None),
            ('boundary_drift',
             "update erp.cp6_v2620ab_rollback_capsule set boundary_snapshot=boundary_snapshot-'supplier_payments'",
             'AB_BOUNDARY_SNAPSHOT_MISMATCH', None),
            ('post_install_boundary_history',
             "update erp.cp6_v2620w_rollback_capsule set boundary_snapshot=boundary_snapshot||'{\"w_post_use_probe\":true}'::jsonb",
             'AB_POST_USE_ROLLBACK_REFUSED', None),
            ('post_install_other_module_history',
             "update erp.app_permissions set description=description||' [CP6 AB boundary probe]' where permission_key=(select permission_key from erp.app_permissions order by permission_key limit 1)",
             'AB_POST_USE_ROLLBACK_REFUSED: app_permissions', None),
            ('coherent_capsule_and_checksum', None,
             'AB_TRUSTED_PREDECESSOR_PIN_MISMATCH', coherent),
        )
        if tuple(case[0] for case in cases) != DIRECT_GUARD_NAMES:
            raise AssertionError('Direct AB guard case manifest drift')
        for name, mutation, expected_error, coherent_definition in cases:
            error = None
            detail: dict[str, Any] = {'case': name, 'status': 'PENDING',
                                      'expected_error': expected_error}
            results.append(detail)
            persist('IN_PROGRESS')
            try:
                try:
                    with conn.cursor() as cur:
                        if name == 'post_install_other_module_history':
                            original_boundary = table_boundary(cur)
                            cur.execute('update erp.sizes set sort_order=sort_order+1 where id=(select id from erp.sizes order by id limit 1)')
                            detail['legacy_empty_update'] = {
                                'table': 'sizes', 'before_rows': original_boundary['sizes']['rows'],
                                'affected_rows': cur.rowcount,
                                'full_boundary_unchanged': table_boundary(cur) == original_boundary,
                                'rollback_invoked': False,
                            }
                            if detail['legacy_empty_update'] != {
                                'table': 'sizes', 'before_rows': 0, 'affected_rows': 0,
                                'full_boundary_unchanged': True, 'rollback_invoked': False,
                            }:
                                raise AssertionError('AB_LEGACY_EMPTY_UPDATE_CONTROL_DRIFT')
                            cur.execute("""select
                              (select bool_or(boundary_snapshot ? 'app_permissions') from erp.cp6_v2620w_rollback_capsule),
                              (select bool_and(boundary_snapshot ? 'app_permissions') from erp.cp6_v2620ab_rollback_capsule)""")
                            in_w, in_y = cur.fetchone()
                            detail['boundary_membership'] = {'table': 'app_permissions', 'in_w': in_w, 'in_y': in_y}
                            if (in_w, in_y) != (False, True):
                                raise AssertionError('AB_OTHER_MODULE_BOUNDARY_MEMBERSHIP')
                            detail['before_boundary'] = original_boundary
                        if coherent_definition is None:
                            cur.execute(mutation, prepare=False)
                            if mutation.lstrip().lower().startswith(('update ', 'insert ', 'delete ')):
                                detail['affected_rows'] = cur.rowcount
                                if cur.rowcount <= 0:
                                    raise AssertionError(f'AB_EMPTY_GUARD_MUTATION:{name}:{cur.rowcount}')
                        else:
                            cur.execute("""update erp.cp6_v2620ab_rollback_capsule
                              set object_definition=%s,
                                definition_sha256=encode(extensions.digest(
                                  convert_to(%s,'UTF8'),'sha256'),'hex')
                              where object_regidentity=%s""",
                              (coherent_definition,coherent_definition,identity))
                            detail['affected_rows'] = cur.rowcount
                            if cur.rowcount != 1:
                                raise AssertionError(f'AB_COHERENT_GUARD_CARDINALITY:{cur.rowcount}')
                        if name == 'post_install_other_module_history':
                            mutated = table_boundary(cur)
                            detail['mutated_boundary'] = mutated
                            detail['changed_tables'] = [t for t in original_boundary if original_boundary[t] != mutated[t]]
                            if detail['affected_rows'] != 1 or detail['changed_tables'] != ['app_permissions']:
                                raise AssertionError('AB_OTHER_MODULE_MUTATION_NOT_ISOLATED')
                            if mutated['app_permissions']['rows'] != original_boundary['app_permissions']['rows']:
                                raise AssertionError('AB_PERMISSION_DESCRIPTION_CHANGED_ROW_COUNT')
                        cur.execute(rollback_sql, prepare=False)
                except psycopg.Error as exc:
                    error = str(exc)
                    detail['actual_sqlstate'] = exc.sqlstate
                finally:
                    conn.rollback()
                detail['actual_error'] = error
                if error is None or expected_error not in error:
                    raise AssertionError(f'{name}: wrong/missing rejection {error}')
                with conn.cursor() as cur:
                    if n_guards.function_catalog(cur) != before:
                        raise AssertionError(f'{name}: guard left function/ACL residue')
                    if name == 'post_install_other_module_history':
                        restored = table_boundary(cur)
                        detail['restored_boundary'] = restored
                        detail['full_boundary_restored'] = restored == original_boundary
                        if not detail['full_boundary_restored']:
                            raise AssertionError('AB_OTHER_MODULE_GUARD_LEFT_TABLE_RESIDUE')
                conn.commit()
                detail.update(status='PASS', expected_rejection_observed=True)
                persist('IN_PROGRESS')
            except Exception as exc:
                conn.rollback()
                detail.update(status='FAIL', error_type=type(exc).__name__, error_message=str(exc))
                persist('FAIL')
                raise
    persist('PASS')
    return results


def verify_extra_preflight_guards() -> list[dict[str, Any]]:
    """Inherited helper/fact faults stop before database admission changes."""
    names = [case[0] for case in EXTRA_FAULTS]
    if len(names) != 22 or len(names) != len(set(names)):
        raise AssertionError('AB_EXTRA_PREFLIGHT_CASE_MANIFEST_DRIFT')
    if any(re.fullmatch(r'[a-z0-9_]+', name) is None for name in names):
        raise AssertionError('AB_EXTRA_PREFLIGHT_CASE_PATH_NOT_PORTABLE')
    results: list[dict[str, Any]] = []
    persist_extra('IN_PROGRESS', results)
    with n_guards.disposable_clone_confirmation(matrix.CLONE):
        for name, object_identity, mutation, expected in EXTRA_FAULTS:
            folder = CLONE_ROOT / name
            folder.mkdir(parents=True, exist_ok=True)
            detail: dict[str, Any] = {
                'case': name,
                'object_identity': object_identity,
                'status': 'PENDING',
                'stage': 'PREPARE_CLONE',
                'fault_executor': 'supabase_admin',
                'expected_rejection': expected,
            }
            results.append(detail)
            persist_extra('IN_PROGRESS', results)
            try:
                matrix.prepare('AB', 'REPORT', folder, source_generation='AB')
                detail['stage'] = 'APPLY_FAULT'
                persist_extra('IN_PROGRESS', results)
                apply_extra_fault(mutation)
                detail['fault_applied'] = True
                detail['stage'] = 'VERIFY_PREFLIGHT_REJECTION'
                persist_extra('IN_PROGRESS', results)
                rejection = None
                try:
                    maintenance.run_maintenance_rollback(
                        target_name='AB', target_pgurl=matrix.CLONE,
                        maintenance_pgurl=matrix.ADMISSION_CONTROL,
                        report_path=folder / 'maintenance.json',
                        drain_timeout=5, natural_grace=0,
                        terminate_after_grace=True,
                    )
                except (maintenance.MaintenanceRollbackError, AssertionError) as exc:
                    rejection = str(exc)
                detail['actual_rejection'] = rejection
                if rejection is None or expected not in rejection:
                    raise AssertionError(
                        'AB_EXTRA_PREFLIGHT_WRONG_REJECTION: ' + name
                    )
                observed = matrix.read_json_if_present(
                    folder / 'maintenance.json'
                ) or {}
                if observed.get('admission_closed') or observed.get('rollback_started'):
                    raise AssertionError(
                        'AB_EXTRA_PREFLIGHT_MUTATED_ADMISSION: ' + name
                    )
                with psycopg.connect(
                    matrix.ADMISSION_CONTROL, autocommit=True
                ) as conn:
                    admission = conn.execute("""select datallowconn
                      from pg_database where datname='cp6_rollback'""").fetchone()
                with psycopg.connect(matrix.CLONE, autocommit=True) as conn:
                    marker = conn.execute("""select count(*)
                      from erp.schema_migrations where version='v2.6.20ab'""").fetchone()
                if admission != (True,) or marker != (1,):
                    raise AssertionError(
                        'AB_EXTRA_PREFLIGHT_STATE_CHANGED: ' + name
                    )
                detail.update(
                    status='PASS', stage='COMPLETE',
                    expected_rejection_observed=True,
                    admission_closed=False, rollback_started=False,
                    installed_generation_preserved=True,
                )
                persist_extra('IN_PROGRESS', results)
            except Exception as exc:
                detail.update(
                    status='FAIL',
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
                persist_extra('FAIL', results)
                raise
            finally:
                try:
                    matrix.reopen_clone()
                except Exception:
                    pass
                matrix.legacy.drop_clone()
    persist_extra('PASS', results)
    return results


def verify_exact_aa_restore(target_pgurl: str) -> dict[str, Any]:
    expected = maintenance.TRUSTED_FUNCTIONS['AB']
    with psycopg.connect(target_pgurl, autocommit=False) as conn, conn.cursor() as cur:
        actual = maintenance._function_snapshot(conn, expected)
        cur.execute("""select
          not exists(select 1 from erp.schema_migrations where version='v2.6.20ab')
          and exists(select 1 from erp.schema_migrations where version='v2.6.20aa')
          and not exists(select 1 from supabase_migrations.schema_migrations
            where name='erp_v2_6_20ab_cp6_operational_business_clock')
          and to_regclass('erp.cp6_v2620ab_rollback_capsule') is null
          and to_regclass('erp.cp6_v2620v_rollback_capsule') is not null
          and to_regclass('erp.cp6_v2620w_rollback_capsule') is not null
          and to_regclass('erp.cp6_v2620z_rollback_capsule') is not null
          and to_regclass('erp.cp6_v2620aa_rollback_capsule') is not null
          and to_regclass('erp.cp6_v2620u_rollback_capsule') is not null
          and to_regclass('erp.material_adjustment_revaluation_facts') is not null
          and to_regprocedure('erp._cp6_material_adjustment_revaluation_state(uuid)') is not null
          and to_regprocedure('erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)') is not null
          and to_regprocedure('erp.guard_material_adjustment_revaluation_fact_v2620t()') is not null
          and to_regclass('erp.supplier_cent_posting_facts') is not null
          and to_regprocedure('erp._cp6_supplier_cent_state(uuid[])') is not null
          and to_regprocedure('erp._cp6_supplier_cent_ledger(uuid[])') is not null
          and to_regprocedure('erp._cp6_apply_supplier_cent_event(text,uuid,date,text,jsonb,boolean)') is not null""")
        if cur.fetchone()[0] is not True:
            raise AssertionError('AB rollback metadata/schema residue')
    return {
        'generation': 'AA', 'restored_function_count': len(actual),
        'owner_acl_exact': True, 'metadata_schema_residue': 0,
    }


def run() -> dict[str, Any]:
    target_pgurl = os.environ['PGURL']
    maintenance_pgurl = os.environ['CP6_ADMISSION_CONTROL_PGURL']
    maintenance._validate_connections(target_pgurl, maintenance_pgurl)
    result: dict[str, Any] = {
        'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
        'classification': (
            'DISPOSABLE_NATIVE_AB_TRUSTED_GUARDS_AND_CLOSED_ADMISSION_RESTORE'
        ),
        'rollback_sha256': hashlib.sha256(ROLLBACK.read_bytes()).hexdigest(),
        'production_go': False,
    }
    result['trusted_capsule_guard'] = verify_capsule_fault()
    result['extra_object_preflight_guards'] = verify_extra_preflight_guards()
    result['guards'] = direct_guards(target_pgurl)
    maintenance_result = maintenance.run_maintenance_rollback(
        target_name='AB', target_pgurl=target_pgurl,
        maintenance_pgurl=maintenance_pgurl,
        report_path=MAINTENANCE_REPORT,
        drain_timeout=10, natural_grace=.25, terminate_after_grace=True,
    )
    if maintenance_result['status'] != 'PASS':
        raise AssertionError('AB maintenance rollback failed')
    required_phases = {
        'ENDPOINT_VERIFIED', 'CAPSULE_VERIFIED', 'ADMISSION_CLOSED',
        'DRAINED', 'ROLLBACK_STARTED', 'ROLLBACK_COMMITTED',
        'PREDECESSOR_VERIFIED', 'ADMISSION_REOPENED',
    }
    observed_phases = {
        item.get('phase') for item in maintenance_result.get('phases', [])
    }
    if not required_phases.issubset(observed_phases):
        raise AssertionError('AB maintenance phase evidence incomplete')
    result.update(
        status='PASS',
        exact_pre_use_restore=verify_exact_aa_restore(target_pgurl),
        maintenance={
            'status': 'PASS', 'target': 'AB',
            'endpoint_verified': True, 'capsule_verified': True,
            'admission_closed_before_rollback': True,
            'old_sessions_drained': True, 'rollback_committed': True,
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
            'error_code': 'V2620AB_ROLLBACK_GUARD_FAILED',
            'error_type': type(exc).__name__,
            'error_message': str(exc),
            'production_go': False,
        }
    REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps(result, sort_keys=True, default=str))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
