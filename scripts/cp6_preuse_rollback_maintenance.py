#!/usr/bin/env python3
"""Admission-closed executor for reviewed CP6 pre-use rollbacks.

PostgreSQL can continue an already-entered PL/pgSQL body after CREATE OR
REPLACE/DROP changes its dependencies. Table locks therefore are necessary but
not sufficient for a live DDL rollback. This controller opens the one rollback
session first, persistently closes database admission, drains or terminates all
other client sessions, and only then executes the exact reviewed rollback.

On any ambiguous or pre-commit failure admission remains closed. An operator
must inspect the structured report and explicitly recover; the controller never
guesses whether a failed DDL command committed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict


TARGETS: dict[str, dict[str, Any]] = {
    'F': {
        'rollback': Path('supabase/rollbacks/20260909174713_erp_v2_6_20f_cp6_final_runtime_reliability.rollback.sql'),
        'rollback_sha256': '83819e093d1489af70431704c59e2cb50a0149e1adc8520d5b9536510572a23d',
        'marker': 'v2.6.20f',
        'platform': 'erp_v2_6_20f_cp6_final_runtime_reliability',
        'predecessor': 'v2.6.20e',
        'capsule': 'erp.cp6_v2620f_rollback_capsule',
        'capsule_count': 8,
    },
    'G': {
        'rollback': Path('supabase/rollbacks/20260910031103_erp_v2_6_20g_cp6_independent_audit_closure.rollback.sql'),
        'rollback_sha256': '8946f4ca8b75850cb284cee669b609e7e938b6020f4e9fa7a270e9794b2becd8',
        'marker': 'v2.6.20g',
        'platform': 'erp_v2_6_20g_cp6_independent_audit_closure',
        'predecessor': 'v2.6.20f',
        'capsule': 'erp.cp6_v2620g_rollback_capsule',
        'capsule_count': 7,
    },
    'H': {
        'rollback': Path('supabase/rollbacks/20260910061516_erp_v2_6_20h_cp6_expanded_audit_closure.rollback.sql'),
        'rollback_sha256': '0d0318e3848344c3642f1796a205d25bcf1cc2d2091ce28d1fc9cf6d186ecbe5',
        'marker': 'v2.6.20h',
        'platform': 'erp_v2_6_20h_cp6_expanded_audit_closure',
        'predecessor': 'v2.6.20g',
        'capsule': 'erp.cp6_v2620h_rollback_capsule',
        'capsule_count': 6,
    },
}


class MaintenanceRollbackError(RuntimeError):
    """A fail-closed maintenance boundary refused or could not finish."""


def _scalar(conn: psycopg.Connection, query: Any, params: tuple[Any, ...] = ()) -> Any:
    with conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        return row[0] if row else None


def _write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(report, indent=2, default=str) + '\n')
    temporary.replace(path)


def _phase(path: Path, report: dict[str, Any], name: str, **facts: Any) -> None:
    report['phase'] = name
    report.setdefault('phases', []).append({
        'phase': name,
        'observed_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        **facts,
    })
    _write_report(path, report)


def _sessions(control: psycopg.Connection, database: str, keep_pid: int) -> list[dict[str, Any]]:
    with control.cursor() as cur:
        cur.execute(
            """select pid,application_name,state,backend_type,
                      xact_start::text,query_start::text,wait_event_type,wait_event,query
               from pg_stat_activity
               where datname=%s and pid<>%s and backend_type='client backend'
               order by case when state='active' then 0 else 1 end,pid""",
            (database, keep_pid),
        )
        columns = [column.name for column in cur.description]
        return [dict(zip(columns, row, strict=True)) for row in cur.fetchall()]


def _capsule_snapshot(
    target_conn: psycopg.Connection, target: dict[str, Any]
) -> list[dict[str, Any]]:
    capsule = sql.Identifier(*target['capsule'].split('.'))
    query = sql.SQL(
        """select object_regidentity,definition_sha256,owner_snapshot,acl_snapshot
           from {} order by object_regidentity"""
    ).format(capsule)
    with target_conn.cursor() as cur:
        cur.execute(query)
        rows = [
            {
                'identity': row[0],
                'sha256': row[1],
                'owner': row[2],
                'acl': row[3],
            }
            for row in cur.fetchall()
        ]
    if len(rows) != target['capsule_count']:
        raise MaintenanceRollbackError(
            f"Target capsule count {len(rows)} != {target['capsule_count']}"
        )
    return rows


def _function_snapshot(
    target_conn: psycopg.Connection, expected: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    observed: list[dict[str, Any]] = []
    with target_conn.cursor() as cur:
        for item in expected:
            cur.execute(
                """select encode(extensions.digest(convert_to(
                         pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
                         pg_get_userbyid(p.proowner),
                         case when p.proacl is null then null else
                           array(select a::text from unnest(p.proacl) a order by a::text) end
                   from pg_proc p where p.oid=to_regprocedure(%s)""",
                (item['identity'],),
            )
            row = cur.fetchone()
            if row is None:
                raise MaintenanceRollbackError(
                    f"Restored function is missing: {item['identity']}"
                )
            actual = {
                'identity': item['identity'],
                'sha256': row[0],
                'owner': row[1],
                'acl': row[2],
            }
            if actual != item:
                raise MaintenanceRollbackError(
                    f"Exact predecessor function/ACL mismatch: {item['identity']}"
                )
            observed.append(actual)
    return observed


def _validate_connections(target_pgurl: str, maintenance_pgurl: str) -> tuple[str, str]:
    target_info = conninfo_to_dict(target_pgurl)
    maintenance_info = conninfo_to_dict(maintenance_pgurl)
    database = target_info.get('dbname', '')
    maintenance_database = maintenance_info.get('dbname', '')
    if not database or database in {'template0', 'template1'}:
        raise MaintenanceRollbackError('Refusing a template or unresolved rollback database')
    if database == 'postgres' and os.environ.get(
        'CP6_MAINTENANCE_ALLOW_SYSTEM_DATABASE'
    ) != database:
        raise MaintenanceRollbackError(
            'Refusing postgres without CP6_MAINTENANCE_ALLOW_SYSTEM_DATABASE=postgres'
        )
    if maintenance_database == database:
        raise MaintenanceRollbackError('Maintenance connection must use a different database')
    for key in ('host', 'hostaddr', 'port'):
        left = target_info.get(key)
        right = maintenance_info.get(key)
        if left and right and left != right:
            raise MaintenanceRollbackError(f'Target/maintenance server mismatch: {key}')
    confirmed = os.environ.get('CP6_MAINTENANCE_CONFIRM_DATABASE')
    if confirmed != database:
        raise MaintenanceRollbackError(
            'CP6_MAINTENANCE_CONFIRM_DATABASE must exactly name the target database'
        )
    return database, maintenance_database


def run_maintenance_rollback(
    *,
    target_name: str,
    target_pgurl: str,
    maintenance_pgurl: str,
    report_path: Path,
    drain_timeout: float,
    natural_grace: float,
    terminate_after_grace: bool,
    pause_after_close_file: Path | None = None,
    continue_file: Path | None = None,
) -> dict[str, Any]:
    if target_name not in TARGETS:
        raise MaintenanceRollbackError(f'Unsupported rollback target: {target_name}')
    target = TARGETS[target_name]
    database, maintenance_database = _validate_connections(target_pgurl, maintenance_pgurl)
    rollback_path = target['rollback'].resolve()
    repository = Path.cwd().resolve()
    if repository not in rollback_path.parents or not rollback_path.is_file():
        raise MaintenanceRollbackError('Reviewed rollback path is absent or outside the repository')
    rollback_bytes = rollback_path.read_bytes()
    rollback_sha256 = hashlib.sha256(rollback_bytes).hexdigest()
    if rollback_sha256 != target['rollback_sha256']:
        raise MaintenanceRollbackError(
            f"Reviewed rollback checksum mismatch: {rollback_sha256}"
        )
    report: dict[str, Any] = {
        'contract': 'CP6_PREUSE_ROLLBACK_MAINTENANCE_V1',
        'target': target_name,
        'database': database,
        'maintenance_database': maintenance_database,
        'rollback_path': str(target['rollback']),
        'rollback_sha256': rollback_sha256,
        'terminate_after_grace': terminate_after_grace,
        'drain_timeout_seconds': drain_timeout,
        'natural_grace_seconds': natural_grace,
        'admission_closed': False,
        'rollback_started': False,
        'rollback_committed': False,
        'admission_reopened': False,
        'status': 'RUNNING',
    }
    _phase(report_path, report, 'PREFLIGHT')

    rollback_conn: psycopg.Connection | None = None
    control: psycopg.Connection | None = None
    lock_held = False
    try:
        rollback_conn = psycopg.connect(
            target_pgurl,
            autocommit=True,
            application_name=f'cp6-maintenance-{target_name.lower()}-rollback',
        )
        control = psycopg.connect(
            maintenance_pgurl,
            autocommit=True,
            application_name='cp6-maintenance-admission-control',
        )
        rollback_pid = int(_scalar(rollback_conn, 'select pg_backend_pid()'))
        actual_database = str(_scalar(rollback_conn, 'select current_database()'))
        if actual_database != database:
            raise MaintenanceRollbackError('Connected rollback database identity changed')
        if not _scalar(control, 'select rolsuper from pg_roles where rolname=current_user'):
            raise MaintenanceRollbackError('Admission control requires a database superuser')
        if not _scalar(
            control, 'select exists(select 1 from pg_database where datname=%s)', (database,)
        ):
            raise MaintenanceRollbackError('Target database no longer exists')
        _scalar(
            control,
            "select pg_advisory_lock(hashtextextended('CP6_PREUSE_ROLLBACK_MAINTENANCE',0))",
        )
        lock_held = True
        capsule = _capsule_snapshot(rollback_conn, target)
        report['predecessor_function_expectations'] = capsule
        _phase(report_path, report, 'CAPSULE_VERIFIED', rollback_pid=rollback_pid)

        with control.cursor() as cur:
            cur.execute(
                sql.SQL('alter database {} with allow_connections false').format(
                    sql.Identifier(database)
                )
            )
        if _scalar(control, 'select datallowconn from pg_database where datname=%s', (database,)):
            raise MaintenanceRollbackError('Database admission did not close')
        report['admission_closed'] = True
        _phase(report_path, report, 'ADMISSION_CLOSED', rollback_pid=rollback_pid)

        if pause_after_close_file is not None:
            pause_after_close_file.parent.mkdir(parents=True, exist_ok=True)
            pause_after_close_file.write_text('ADMISSION_CLOSED\n')
        if continue_file is not None:
            deadline = time.monotonic() + drain_timeout
            while not continue_file.exists() and time.monotonic() < deadline:
                time.sleep(.025)
            if not continue_file.exists():
                raise MaintenanceRollbackError('Admission-close test barrier timed out')

        natural_deadline = time.monotonic() + natural_grace
        active = _sessions(control, database, rollback_pid)
        report['sessions_at_close'] = active
        while active and time.monotonic() < natural_deadline:
            time.sleep(.025)
            active = _sessions(control, database, rollback_pid)
        report['sessions_after_natural_grace'] = active

        terminated: list[dict[str, Any]] = []
        if active and terminate_after_grace:
            with control.cursor() as cur:
                for session in active:
                    cur.execute('select pg_terminate_backend(%s)', (session['pid'],))
                    terminated.append({**session, 'terminate_requested': bool(cur.fetchone()[0])})
        report['terminated_sessions'] = terminated
        drain_deadline = time.monotonic() + drain_timeout
        active = _sessions(control, database, rollback_pid)
        while active and time.monotonic() < drain_deadline:
            time.sleep(.025)
            active = _sessions(control, database, rollback_pid)
        report['sessions_after_drain'] = active
        if active:
            raise MaintenanceRollbackError('DRAIN_TIMEOUT: old client invocations remain')
        if _scalar(control, 'select datallowconn from pg_database where datname=%s', (database,)):
            raise MaintenanceRollbackError('Admission reopened before rollback')
        _phase(report_path, report, 'DRAINED', terminated_count=len(terminated))

        report['rollback_started'] = True
        _phase(report_path, report, 'ROLLBACK_STARTED')
        with rollback_conn.cursor() as cur:
            cur.execute(rollback_bytes.decode('utf-8'), prepare=False)
        report['rollback_committed'] = True
        _phase(report_path, report, 'ROLLBACK_COMMITTED')

        marker_count = int(_scalar(
            rollback_conn,
            'select count(*) from erp.schema_migrations where version=%s',
            (target['marker'],),
        ))
        predecessor_count = int(_scalar(
            rollback_conn,
            'select count(*) from erp.schema_migrations where version=%s',
            (target['predecessor'],),
        ))
        platform_count = int(_scalar(
            rollback_conn,
            'select count(*) from supabase_migrations.schema_migrations where name=%s',
            (target['platform'],),
        ))
        capsule_present = bool(_scalar(
            rollback_conn, 'select to_regclass(%s) is not null', (target['capsule'],)
        ))
        if (marker_count, predecessor_count, platform_count, capsule_present) != (0, 1, 0, False):
            raise MaintenanceRollbackError('Exact predecessor marker/capsule postcondition failed')
        report['restored_functions'] = _function_snapshot(rollback_conn, capsule)
        report['postconditions'] = {
            'target_marker_count': marker_count,
            'predecessor_marker_count': predecessor_count,
            'target_platform_count': platform_count,
            'target_capsule_present': capsule_present,
            'functions_owner_acl_exact': True,
        }
        _phase(report_path, report, 'PREDECESSOR_VERIFIED')

        with control.cursor() as cur:
            cur.execute(
                sql.SQL('alter database {} with allow_connections true').format(
                    sql.Identifier(database)
                )
            )
        if not _scalar(control, 'select datallowconn from pg_database where datname=%s', (database,)):
            raise MaintenanceRollbackError('Database admission did not reopen after verified commit')
        report['admission_reopened'] = True
        report['status'] = 'PASS'
        _phase(report_path, report, 'ADMISSION_REOPENED')
        return report
    except Exception as exc:
        report['status'] = 'FAIL'
        report['error'] = str(exc)
        report['error_type'] = type(exc).__name__
        # Fail closed: do not reopen admission here. The structured state and
        # exact database flag remain available for explicit recovery.
        if control is not None and report['admission_closed']:
            try:
                report['admission_still_closed'] = not bool(_scalar(
                    control,
                    'select datallowconn from pg_database where datname=%s',
                    (database,),
                ))
            except Exception as observation_error:
                report['admission_observation_error'] = str(observation_error)
        _phase(report_path, report, 'FAILED_CLOSED')
        raise
    finally:
        if control is not None and lock_held:
            try:
                _scalar(
                    control,
                    "select pg_advisory_unlock(hashtextextended('CP6_PREUSE_ROLLBACK_MAINTENANCE',0))",
                )
            except Exception:
                pass
        if rollback_conn is not None:
            rollback_conn.close()
        if control is not None:
            control.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--target', choices=tuple(TARGETS), required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--drain-timeout', type=float, default=10.0)
    parser.add_argument('--natural-grace', type=float, default=1.0)
    parser.add_argument('--no-terminate', action='store_true')
    parser.add_argument('--pause-after-close-file', type=Path)
    parser.add_argument('--continue-file', type=Path)
    args = parser.parse_args()
    target_pgurl = (
        os.environ.get('CP6_ROLLBACK_TARGET_PGURL')
        or os.environ.get('CP6_ROLLBACK_RACE_PGURL', '')
    )
    maintenance_pgurl = os.environ.get('CP6_ADMISSION_CONTROL_PGURL', '')
    if not target_pgurl or not maintenance_pgurl:
        raise SystemExit(
            'CP6_ROLLBACK_TARGET_PGURL (or CP6_ROLLBACK_RACE_PGURL) '
            'and CP6_ADMISSION_CONTROL_PGURL are required'
        )
    try:
        run_maintenance_rollback(
            target_name=args.target,
            target_pgurl=target_pgurl,
            maintenance_pgurl=maintenance_pgurl,
            report_path=args.report,
            drain_timeout=args.drain_timeout,
            natural_grace=args.natural_grace,
            terminate_after_grace=not args.no_terminate,
            pause_after_close_file=args.pause_after_close_file,
            continue_file=args.continue_file,
        )
    except Exception as exc:
        print(json.dumps({'status': 'FAIL', 'error': str(exc)}, sort_keys=True))
        raise SystemExit(1) from exc
    print(json.dumps({'status': 'PASS', 'target': args.target}, sort_keys=True))


if __name__ == '__main__':
    main()
