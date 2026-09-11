#!/usr/bin/env python3
"""Native F/G/H/I/J/K/L/M/N rollback qualification under a closed-admission contract.

Nine target generations x five real backend paths x four schedules = 180
fresh-clone cases. Unlike the superseded live-DDL matrix, no reviewed rollback
runs while an old invocation can resume: database admission closes first and
all old sessions must drain. Every case is persisted, even after a failure.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict

import cp6_v2620g_expanded_rollback_races as legacy
import cp6_preuse_rollback_maintenance as maintenance


ROOT = Path('cp6-proof/H_MAINTENANCE_ROLLBACK')
SOURCE = legacy.SOURCE
MAINTENANCE = legacy.MAINTENANCE
ADMISSION_CONTROL = os.environ.get('CP6_ADMISSION_CONTROL_PGURL', '')
CLONE = legacy.CLONE
CONTAINER = legacy.CONTAINER
TARGETS = {
    'F': ('20260909174713', 'erp_v2_6_20f_cp6_final_runtime_reliability', 'v2.6.20f', 'v2.6.20e', 8),
    'G': ('20260910031103', 'erp_v2_6_20g_cp6_independent_audit_closure', 'v2.6.20g', 'v2.6.20f', 7),
    'H': ('20260910061516', 'erp_v2_6_20h_cp6_expanded_audit_closure', 'v2.6.20h', 'v2.6.20g', 6),
    'I': ('20260910100051', 'erp_v2_6_20i_cp6_h2_audit_closure', 'v2.6.20i', 'v2.6.20h', 1),
    'J': ('20260910170556', 'erp_v2_6_20j_cp6_payment_fact_closure', 'v2.6.20j', 'v2.6.20i', 3),
    'K': ('20260911023222', 'erp_v2_6_20k_cp6_payment_date_conservation', 'v2.6.20k', 'v2.6.20j', 4),
    'L': ('20260911070622', 'erp_v2_6_20l_cp6_exact_ledger_conservation', 'v2.6.20l', 'v2.6.20k', 3),
    'M': ('20260911092622', 'erp_v2_6_20m_cp6_subledger_exact_cent_closure', 'v2.6.20m', 'v2.6.20l', 15),
    'N': ('20260911124328', 'erp_v2_6_20n_cp6_supplier_cent_lifecycle', 'v2.6.20n', 'v2.6.20m', 7),
}
OPERATIONS = ('SALE', 'RETURN', 'CONVERSION', 'REPORT', 'FK_SYNC')
MODES = ('WRITER_FIRST', 'ADMISSION_FIRST', 'WRITER_ABORT', 'DRAIN_TIMEOUT')
BODY_GATES = {
    'SALE': ('erp.sales_headers', 'sale'),
    'RETURN': ('erp.sales_returns', 'return'),
    'CONVERSION': ('erp.product_conversions', 'conversion'),
    'REPORT': ('erp.journal_entries', None),
    'FK_SYNC': ('erp.sales_headers', 'next_sale'),
}


def path(target: str, rollback: bool = False) -> Path:
    stamp, name, _, _, _ = TARGETS[target]
    folder, suffix = ('rollbacks', '.rollback.sql') if rollback else ('migrations', '.sql')
    return Path(f'supabase/{folder}/{stamp}_{name}{suffix}')


def command(args: list[str], log: Path) -> None:
    with log.open('w') as output:
        import subprocess
        subprocess.run(
            args,
            stdout=output,
            stderr=subprocess.STDOUT,
            check=True,
            timeout=180,
        )


def wait_for(predicate: Any, timeout: float = 15.0) -> Any:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(.025)
    raise AssertionError('Required maintenance observation timed out')


def read_json_if_present(path_value: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path_value.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def reopen_clone() -> None:
    with psycopg.connect(ADMISSION_CONTROL, autocommit=True) as conn, conn.cursor() as cur:
        cur.execute(
            sql.SQL('alter database {} with allow_connections true').format(
                sql.Identifier('cp6_rollback')
            )
        )


def maintenance_strip(target: str, folder: Path) -> dict[str, Any]:
    report_path = folder / f'setup_strip_{target}.json'
    return maintenance.run_maintenance_rollback(
        target_name=target,
        target_pgurl=CLONE,
        maintenance_pgurl=ADMISSION_CONTROL,
        report_path=report_path,
        drain_timeout=5,
        natural_grace=0,
        terminate_after_grace=True,
    )


def setup_rollback_plan(target: str, source_generation: str) -> tuple[str, ...]:
    # The full matrix clones L; each older guard names its restored source.
    # Missing or unexpected successors are checked before fixture writes.
    if source_generation not in ('I', 'J', 'K', 'L', 'M', 'N') or target not in TARGETS:
        raise AssertionError('Unsupported rollback fixture generation')
    generations = tuple(TARGETS)
    start, stop = generations.index(source_generation), generations.index(target)
    if stop > start:
        raise AssertionError('Rollback fixture target is newer than its source')
    return tuple(reversed(generations[stop:start + 1]))


def verify_setup_source(source_generation: str) -> None:
    stamp, name, _, _, _ = TARGETS[source_generation]
    with legacy.connect('h-maintenance-source-generation') as conn, conn.cursor() as cur:
        cur.execute(
            'select version,name from supabase_migrations.schema_migrations '
            'order by version desc limit 1'
        )
        if cur.fetchone() != (stamp, name):
            raise AssertionError('Rollback fixture source platform generation mismatch')
        for generation, (_, _, marker, _, _) in TARGETS.items():
            cur.execute(
                'select (select count(*) from erp.schema_migrations where version=%s), '
                'to_regclass(%s) is not null',
                (marker, maintenance.TARGETS[generation]['capsule']),
            )
            installed = generation <= source_generation
            if cur.fetchone() != (int(installed), installed):
                raise AssertionError('Rollback fixture source marker/capsule mismatch')


def prepare(
    target: str, operation: str, folder: Path, *, source_generation: str = 'N',
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rollback_plan = setup_rollback_plan(target, source_generation)
    command(
        [
            'bash', 'scripts/clone-cp6-disposable-database.sh', SOURCE, MAINTENANCE,
            CLONE, 'cp6_rollback', CONTAINER, str(folder / 'PHYSICAL_BOUNDARY'),
        ],
        folder / 'clone.log',
    )
    # Validate the physical clone before the first rollback or fixture write.
    # Every installed generation still uses the full maintenance executor.
    verify_setup_source(source_generation)
    for generation in rollback_plan:
        maintenance_strip(generation, folder)

    with legacy.connect('h-maintenance-predecessor-fixture') as conn, conn.cursor() as cur:
        fixture = legacy.seed(cur, operation)
        conn.commit()

    command(
        ['psql', CLONE, '-X', '-v', 'ON_ERROR_STOP=1', '-f', str(path(target))],
        folder / 'install.log',
    )
    stamp, name, _, _, capsule_count = TARGETS[target]
    source = path(target).read_text()
    with legacy.connect('h-maintenance-exact-platform-ledger') as conn, conn.cursor() as cur:
        cur.execute(
            'insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',
            (stamp, name, [source]),
        )
        conn.commit()
    capsule = legacy.capture_capsule(target)
    if len(capsule) != capsule_count:
        raise AssertionError(f'Wrong {target} capsule count: {len(capsule)}')
    legacy.verify_functions(capsule, True)
    return fixture, capsule


def assert_business_postcondition(operation: str, after: dict[str, Any]) -> None:
    if after['unbalanced_journals'] or after['execution_context']:
        raise AssertionError(f'Business residue: {after}')
    if operation == 'REPORT':
        return
    if operation == 'SALE':
        expected = (
            after['stock'] == 5
            and after['sale_status'] == 'POSTED'
            and tuple(map(Decimal, after['book'])) == (Decimal(35), Decimal(35))
        )
    elif operation == 'RETURN':
        expected = (
            after['stock'] == 7
            and after['return_status'] == 'POSTED'
            and tuple(map(Decimal, after['book'])) == (Decimal(49), Decimal(21))
        )
    elif operation == 'CONVERSION':
        expected = (
            after['stock'] == 8
            and after['destination_stock'] == 2
            and after['conversion_status'] == 'POSTED'
            and tuple(map(Decimal, after['po_value'])) == (Decimal(70), Decimal(0), Decimal(0))
        )
    else:
        expected = (
            after['stock'] == 9
            and after['sale_status'] == 'REVERSED'
            and tuple(map(Decimal, after['book'])) == (Decimal('.10'), Decimal('.01'))
        )
    if not expected:
        raise AssertionError(f'{operation} post-condition failed: {after}')


def run_business_once(operation: str, fixture: dict[str, Any], application: str) -> Any:
    with legacy.connect(application) as conn, conn.cursor() as cur:
        response = legacy.business(cur, operation, fixture)
        conn.commit()
        return response


def run_case(target: str, operation: str, mode: str, folder: Path) -> dict[str, Any]:
    fixture, capsule = prepare(target, operation, folder)
    before = legacy.facts(fixture)
    writer_ready = threading.Event()
    writer_pid_ready = threading.Event()
    writer_warmup_ready = threading.Event()
    writer_after_gate = threading.Event()
    writer_release = threading.Event()
    writer: dict[str, Any] = {'started': False}
    rollback_outcome: dict[str, Any] = {}
    pause_file = folder / 'ADMISSION_CLOSED'
    continue_file = folder / 'CONTINUE_DRAIN'
    controller_report_path = folder / 'maintenance.json'
    writer_thread: threading.Thread | None = None
    controller_thread: threading.Thread | None = None
    gate: psycopg.Connection | None = None
    gate_pid: int | None = None
    inflight_lock_observation: Any = None
    body_gate: dict[str, Any] | None = None
    writer_at_close: dict[str, Any] | None = None
    writer_body_entry_proven: bool | None = None
    controller_result: dict[str, Any] | None = None
    after_boundary: dict[str, Any] | None = None
    sentinel: Any = None

    def old_writer() -> None:
        writer['started'] = True
        try:
            with legacy.connect('h-old-generation-' + operation.lower()) as conn, conn.cursor() as cur:
                cur.execute("set local lock_timeout='20s'; set local statement_timeout='45s'")
                writer['pid'] = legacy.base.one(cur, 'select pg_backend_pid()')
                writer_pid_ready.set()
                if mode == 'WRITER_FIRST':
                    cur.execute('savepoint cp6_writer_body_warmup')
                    legacy.business(cur, operation, fixture)
                    cur.execute('rollback to savepoint cp6_writer_body_warmup')
                    cur.execute('release savepoint cp6_writer_body_warmup')
                    writer['warmup_body_completed'] = True
                    writer['warmup_effects_rolled_back'] = True
                    writer_warmup_ready.set()
                    if not writer_after_gate.wait(20):
                        raise AssertionError('Writer body gate did not arrive after warm-up')
                writer['response'] = legacy.business(cur, operation, fixture)
                writer['entered_and_returned'] = True
                writer_ready.set()
                if not writer_release.wait(25):
                    raise AssertionError('Writer release did not arrive')
                if mode in ('WRITER_ABORT', 'DRAIN_TIMEOUT'):
                    conn.rollback()
                    writer['outcome'] = 'ABORTED'
                else:
                    conn.commit()
                    writer['outcome'] = 'COMMITTED'
        except Exception as exc:
            diag = getattr(exc, 'diag', None)
            writer.update(
                outcome='ERROR', error=str(exc), sqlstate=getattr(exc, 'sqlstate', None),
                message_primary=getattr(diag, 'message_primary', None),
                diagnostic_context=getattr(diag, 'context', None),
            )
            writer_pid_ready.set()
            writer_warmup_ready.set()
            writer_after_gate.set()
            writer_ready.set()

    def controller() -> None:
        try:
            rollback_outcome['result'] = maintenance.run_maintenance_rollback(
                target_name=target,
                target_pgurl=CLONE,
                maintenance_pgurl=ADMISSION_CONTROL,
                report_path=controller_report_path,
                drain_timeout=.75 if mode == 'DRAIN_TIMEOUT' else 8,
                natural_grace=.1,
                terminate_after_grace=mode != 'DRAIN_TIMEOUT',
                pause_after_close_file=pause_file,
                continue_file=continue_file,
            )
        except Exception as exc:
            rollback_outcome.update(error=str(exc), error_type=type(exc).__name__)
            rollback_outcome['result'] = read_json_if_present(controller_report_path)

    try:
        if mode != 'ADMISSION_FIRST':
            writer_thread = threading.Thread(target=old_writer, daemon=True)
            writer_thread.start()
            if not writer_pid_ready.wait(20) or writer.get('outcome') == 'ERROR':
                raise AssertionError(f'Old-generation writer failed before backend entry: {writer}')
            if mode == 'WRITER_FIRST':
                if not writer_warmup_ready.wait(20) or writer.get('outcome') == 'ERROR':
                    raise AssertionError(
                        f'Old-generation writer did not complete rollback-only body warm-up: {writer}'
                    )
                gate = legacy.connect('h-inflight-body-gate-' + operation.lower())
                with gate.cursor() as cur:
                    cur.execute("set local lock_timeout='12s'")
                    gate_pid = int(legacy.base.one(cur, 'select pg_backend_pid()'))
                    relation, fixture_key = BODY_GATES[operation]
                    if fixture_key is None:
                        cur.execute(
                            sql.SQL('lock table {} in access exclusive mode').format(
                                sql.Identifier(*relation.split('.'))
                            )
                        )
                        body_gate = {
                            'kind': 'TABLE_ACCESS_EXCLUSIVE', 'relation': relation,
                            'fixture_key': None,
                        }
                    else:
                        cur.execute(
                            sql.SQL('select id from {} where id=%s for update').format(
                                sql.Identifier(*relation.split('.'))
                            ),
                            (fixture[fixture_key],),
                        )
                        if cur.fetchone() is None:
                            raise AssertionError(
                                f'Body row gate fixture absent: {relation}/{fixture_key}'
                            )
                        body_gate = {
                            'kind': 'ROW_FOR_UPDATE', 'relation': relation,
                            'fixture_key': fixture_key, 'fixture_id': fixture[fixture_key],
                        }
                body_gate['writer_warmup_body_completed'] = True
                body_gate['writer_warmup_effects_rolled_back'] = True
                writer_after_gate.set()
                wait_for(lambda: legacy.blocked(writer['pid'], gate_pid))
                writer['blocked_inside_backend'] = True
                inflight_lock_observation = legacy.lock_snapshot([gate_pid, writer['pid']])
            elif not writer_ready.wait(20) or writer.get('outcome') == 'ERROR':
                raise AssertionError(f'Old-generation writer failed before admission close: {writer}')

        controller_thread = threading.Thread(target=controller, daemon=True)
        controller_thread.start()
        wait_for(lambda: pause_file.exists() or rollback_outcome.get('error'))
        if rollback_outcome.get('error'):
            raise AssertionError(f'Maintenance failed before closing admission: {rollback_outcome}')

        admission_attempt: dict[str, Any] | None = None
        if mode == 'ADMISSION_FIRST':
            try:
                with psycopg.connect(CLONE, connect_timeout=1):
                    admission_attempt = {'accepted': True}
            except psycopg.Error as exc:
                admission_attempt = {
                    'accepted': False,
                    'error': str(exc).splitlines()[0],
                    'sqlstate': exc.sqlstate,
                }
            if admission_attempt['accepted']:
                raise AssertionError('New connection entered while datallowconn=false')
        elif mode == 'WRITER_ABORT':
            writer_release.set()
            writer_thread.join(10)
            if writer.get('outcome') != 'ABORTED':
                raise AssertionError(f'Writer did not abort during maintenance grace: {writer}')

        continue_file.write_text('CONTINUE\n')
        controller_thread.join(30)
        if controller_thread.is_alive():
            raise AssertionError('Maintenance controller did not finish')

        controller_result = rollback_outcome.get('result') or read_json_if_present(
            controller_report_path
        )
        if not controller_result:
            raise AssertionError('Maintenance controller report is missing')
        phase_names = [phase['phase'] for phase in controller_result.get('phases', [])]
        if mode == 'DRAIN_TIMEOUT':
            if not rollback_outcome.get('error'):
                raise AssertionError('Persistent old invocation did not force a drain timeout')
            if not controller_result:
                raise AssertionError('Drain-timeout controller report is missing')
            if (
                controller_result.get('rollback_started')
                or controller_result.get('rollback_committed')
                or not controller_result.get('admission_still_closed')
            ):
                raise AssertionError(f'Drain timeout was not fail-closed: {controller_result}')
            writer_release.set()
            writer_thread.join(10)
            if writer.get('outcome') != 'ABORTED':
                raise AssertionError(f'Timeout writer did not abort cleanly: {writer}')
            reopen_clone()
            expected_installed = True
            safe_phase_order = (
                'ADMISSION_CLOSED' in phase_names
                and 'ROLLBACK_STARTED' not in phase_names
                and phase_names[-1:] == ['FAILED_CLOSED']
            )
        else:
            if rollback_outcome.get('error') or not controller_result:
                raise AssertionError(f'Maintenance rollback failed: {rollback_outcome}')
            if (
                controller_result.get('status') != 'PASS'
                or not controller_result.get('rollback_committed')
                or not controller_result.get('admission_reopened')
            ):
                raise AssertionError(f'Maintenance contract incomplete: {controller_result}')
            if mode == 'WRITER_FIRST':
                writer_release.set()
                writer_thread.join(10)
                if writer.get('outcome') != 'ERROR':
                    raise AssertionError(f'Old session survived the drain: {writer}')
                terminated_pids = {
                    session['pid'] for session in controller_result['terminated_sessions']
                }
                if writer['pid'] not in terminated_pids or gate_pid not in terminated_pids:
                    raise AssertionError(
                        f'In-flight writer/gate were not both terminated: {controller_result}'
                    )
                writer_at_close = next(
                    (
                        session for session in controller_result['sessions_at_close']
                        if session['pid'] == writer['pid']
                    ),
                    None,
                )
                expected_call = {
                    'SALE': 'post_sale_v2',
                    'RETURN': 'post_sales_return',
                    'CONVERSION': 'post_product_conversion',
                    'REPORT': 'get_owner_financial_snapshot_v2',
                    'FK_SYNC': 'post_sale_v2',
                }[operation]
                if (
                    not writer_at_close
                    or writer_at_close['state'] != 'active'
                    or writer_at_close['wait_event_type'] != 'Lock'
                    or expected_call not in writer_at_close['query']
                ):
                    raise AssertionError(
                        f'Writer was not proven inside the actual backend body: {writer_at_close}'
                    )
                diagnostic_context = writer.get('diagnostic_context') or ''
                expected_context = {
                    'SALE': ('post_sale_v2',),
                    'RETURN': ('post_sales_return',),
                    'CONVERSION': ('post_product_conversion',),
                    'REPORT': (
                        'get_owner_financial_snapshot_v2',
                        'run_v268_financial_report_checks',
                    ),
                    'FK_SYNC': ('post_sale_v2',),
                }[operation]
                if (
                    writer.get('warmup_body_completed') is not True
                    or writer.get('warmup_effects_rolled_back') is not True
                    or 'compilation of PL/pgSQL function' in diagnostic_context
                    or 'PL/pgSQL function' not in diagnostic_context
                    or 'at SQL statement' not in diagnostic_context
                    or not any(name in diagnostic_context for name in expected_context)
                ):
                    raise AssertionError(
                        'Writer termination did not prove body SQL entry: '
                        + repr(diagnostic_context)
                    )
                writer_body_entry_proven = True
                writer['wait_stage'] = 'BODY_SQL_STATEMENT'
            expected_installed = False
            safe_phase_order = all(
                phase_names.index(left) < phase_names.index(right)
                for left, right in (
                    ('ADMISSION_CLOSED', 'DRAINED'),
                    ('DRAINED', 'ROLLBACK_STARTED'),
                    ('ROLLBACK_STARTED', 'ROLLBACK_COMMITTED'),
                    ('ROLLBACK_COMMITTED', 'PREDECESSOR_VERIFIED'),
                    ('PREDECESSOR_VERIFIED', 'ADMISSION_REOPENED'),
                )
            )
        safe_phase_order = safe_phase_order and all(
            phase_names.index(left) < phase_names.index(right)
            for left, right in (
                ('ENDPOINT_VERIFIED', 'CAPSULE_VERIFIED'),
                ('CAPSULE_VERIFIED', 'ADMISSION_CLOSED'),
            )
        )
        if not safe_phase_order:
            raise AssertionError(f'Unsafe maintenance phase order: {phase_names}')

        after_boundary = legacy.facts(fixture)
        if before != after_boundary:
            raise AssertionError(f'Boundary changed before sentinel: {before} -> {after_boundary}')

        sentinel = run_business_once(operation, fixture, 'h-post-maintenance-sentinel')
        after_sentinel = legacy.facts(fixture)
        if (
            operation == 'REPORT'
            and (
                not isinstance(sentinel, dict)
                or sentinel.get('data_confidence', {}).get('status') != 'READY'
            )
        ):
            raise AssertionError(f'Report sentinel is not READY: {sentinel}')
        assert_business_postcondition(operation, after_sentinel)
        if 'compute_non_po_product_hpp_targets_v2620f' in writer.get('error', ''):
            raise AssertionError(f'Old helper failure escaped maintenance: {writer}')

        stamp, name, marker, predecessor, _ = TARGETS[target]
        marker_count = legacy.scalar(
            'select count(*) from erp.schema_migrations where version=%s', (marker,)
        )
        platform_count = legacy.scalar(
            'select count(*) from supabase_migrations.schema_migrations where name=%s',
            (name,),
        )
        predecessor_count = legacy.scalar(
            'select count(*) from erp.schema_migrations where version=%s', (predecessor,)
        )
        if marker_count != (1 if expected_installed else 0) or marker_count != platform_count:
            raise AssertionError('Application/platform marker state mismatch')
        if predecessor_count != 1:
            raise AssertionError('Expected predecessor marker is absent')
        if expected_installed:
            legacy.verify_functions(capsule, True)

        return {
            'status': 'PASS',
            'target': target,
            'target_marker': marker,
            'operation': operation,
            'mode': mode,
            'actual_backend_sql': {
                'SALE': 'erp.post_sale_v2',
                'RETURN': 'erp.post_sales_return',
                'CONVERSION': 'erp.post_product_conversion',
                'REPORT': 'erp.get_owner_financial_snapshot_v2',
                'FK_SYNC': 'erp.post_sale_v2 -> erp.reverse_sale -> F synchronizer when installed',
            }[operation],
            'database_admission_closed_before_ddl': safe_phase_order,
            'maintenance_phase_order': phase_names,
            'old_generation_drained': (
                True if mode in ('WRITER_FIRST', 'WRITER_ABORT')
                else False if mode == 'DRAIN_TIMEOUT' else None
            ),
            'inflight_inside_backend_before_admission_close': (
                mode == 'WRITER_FIRST'
            ),
            'inflight_lock_observation': inflight_lock_observation,
            'body_gate': body_gate,
            'writer_at_close': writer_at_close,
            'writer_body_entry_proven': writer_body_entry_proven,
            'writer_warmup_body_completed': writer.get('warmup_body_completed'),
            'writer_warmup_effects_rolled_back': writer.get('warmup_effects_rolled_back'),
            'new_admission_attempt': admission_attempt,
            'rollback_expected': mode != 'DRAIN_TIMEOUT',
            'rollback_committed': bool(controller_result.get('rollback_committed')),
            'failure_kept_admission_closed': (
                bool(controller_result.get('admission_still_closed'))
                if mode == 'DRAIN_TIMEOUT' else None
            ),
            'writer': writer,
            'maintenance': controller_result,
            'before': before,
            'after_boundary': after_boundary,
            'sentinel_response': sentinel,
            'after_sentinel': after_sentinel,
            'missing_helper_error_absent': True,
            'final_schema': {
                'application_marker': marker_count,
                'platform_marker': platform_count,
                'predecessor_marker': predecessor_count,
            },
            'migration_sha256': hashlib.sha256(path(target).read_bytes()).hexdigest(),
            'rollback_sha256': hashlib.sha256(path(target, True).read_bytes()).hexdigest(),
        }
    finally:
        writer_release.set()
        writer_after_gate.set()
        if pause_file.exists() and not continue_file.exists():
            continue_file.write_text('CLEANUP_CONTINUE\n')
        if gate is not None:
            try:
                gate.rollback()
            except psycopg.Error:
                pass
            try:
                gate.close()
            except psycopg.Error:
                pass
        if writer_thread is not None:
            writer_thread.join(10)
        if controller_thread is not None:
            controller_thread.join(15)
        controller_result = controller_result or read_json_if_present(
            controller_report_path
        )
        case_context = {
            'target': target,
            'operation': operation,
            'mode': mode,
            'writer': writer,
            'gate_pid': gate_pid,
            'inflight_lock_observation': inflight_lock_observation,
            'body_gate': body_gate,
            'writer_at_close': writer_at_close,
            'writer_body_entry_proven': writer_body_entry_proven,
            'writer_warmup_body_completed': writer.get('warmup_body_completed'),
            'writer_warmup_effects_rolled_back': writer.get('warmup_effects_rolled_back'),
            'rollback_outcome': rollback_outcome,
            'controller_report': controller_result,
            'controller_thread_alive_after_cleanup': bool(
                controller_thread and controller_thread.is_alive()
            ),
            'before': before,
            'after_boundary': after_boundary,
            'sentinel': sentinel,
        }
        (folder / 'case_context.json').write_text(
            json.dumps(case_context, indent=2, default=str) + '\n'
        )
        try:
            reopen_clone()
        except Exception:
            pass


def main() -> None:
    expected_environment = (SOURCE, MAINTENANCE, CLONE, CONTAINER, 'cp6_rollback')
    actual_environment = (
        os.environ.get('PGURL'),
        os.environ.get('CP6_MAINTENANCE_PGURL'),
        os.environ.get('CP6_ROLLBACK_RACE_PGURL'),
        os.environ.get('CP6_DATABASE_CONTAINER'),
        os.environ.get('CP6_MAINTENANCE_CONFIRM_DATABASE'),
    )
    if actual_environment != expected_environment:
        raise SystemExit('Refusing non-allowlisted disposable maintenance target')
    admission_info = conninfo_to_dict(ADMISSION_CONTROL)
    expected_admission = {
        'dbname': 'template1',
        'host': '127.0.0.1',
        'port': '54322',
        'user': 'cp6_maintenance_admission',
    }
    if (
        any(admission_info.get(key) != value for key, value in expected_admission.items())
        or not admission_info.get('password')
    ):
        raise SystemExit('Refusing non-allowlisted admission-control authority')
    ROOT.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'),
        'production_go': False,
        'classification': 'NATIVE_POSTGRESQL_CLOSED_ADMISSION_ROLLBACK_MATRIX',
        'expected_case_count': 180,
        'cases': [],
    }
    for target in TARGETS:
        for operation in OPERATIONS:
            for mode in MODES:
                folder = ROOT / f'{target}_{operation}_{mode}'
                folder.mkdir()
                try:
                    case = run_case(target, operation, mode, folder)
                except Exception as exc:
                    case = {
                        'status': 'FAIL',
                        'target': target,
                        'operation': operation,
                        'mode': mode,
                        'error_code': 'MATRIX_CASE_FAILED',
                        'error_type': type(exc).__name__,
                        'sqlstate': getattr(exc, 'sqlstate', None),
                        'maintenance': read_json_if_present(folder / 'maintenance.json'),
                        'context': read_json_if_present(folder / 'case_context.json'),
                    }
                finally:
                    try:
                        reopen_clone()
                    except Exception:
                        pass
                    legacy.drop_clone()
                case['remaining_clone_databases'] = 0
                (folder / 'result.json').write_text(json.dumps(case, indent=2, default=str) + '\n')
                report['cases'].append(case)
                report['completed_case_count'] = len(report['cases'])
                (ROOT / 'progress.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
                print(json.dumps({
                    key: case.get(key)
                    for key in ('status', 'target', 'operation', 'mode', 'error_code', 'error_type', 'sqlstate')
                    if case.get(key) is not None
                }), flush=True)

    report['failed_case_count'] = sum(case['status'] != 'PASS' for case in report['cases'])
    writer_first = [case for case in report['cases'] if case['mode'] == 'WRITER_FIRST']
    writer_first_body_entry = sum(
        case.get('writer_body_entry_proven') is True for case in writer_first
    )
    compilation_only_contexts = sum(
        'compilation of PL/pgSQL function'
        in str(
            (case.get('writer') or (case.get('context') or {}).get('writer') or {}).get(
                'diagnostic_context', ''
            )
        )
        for case in writer_first
    )
    report['writer_first_body_entry'] = {
        'expected': 45,
        'observed': writer_first_body_entry,
        'compilation_only_contexts': compilation_only_contexts,
    }
    report['status'] = (
        'PASS'
        if len(report['cases']) == report['expected_case_count']
        and report['failed_case_count'] == 0
        and writer_first_body_entry == 45
        and compilation_only_contexts == 0
        else 'FAIL'
    )
    (ROOT / 'manifest.json').write_text(json.dumps(report, indent=2, default=str) + '\n')
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
