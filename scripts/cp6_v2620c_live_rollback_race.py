#!/usr/bin/env python3
"""Prove v2.6.20c rollback ordering against an actual uncommitted CP6 facade."""
from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

import psycopg


PGURL = os.environ.get(
    'CP6_ROLLBACK_RACE_PGURL',
    'postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback',
)
MODE = os.environ.get('CP6_ROLLBACK_RACE_MODE', 'WRITER_FIRST')
REPORT = Path(os.environ.get(
    'CP6_ROLLBACK_RACE_REPORT',
    f'cp6-v2620c-live-rollback-{MODE.lower()}.json',
))
ROLLBACK = Path(
    'supabase/rollbacks/'
    '20260907190000_erp_v2_6_20c_cp6_deep_business_reliability.rollback.sql'
)
OPERATOR_AUTH = 'c8c00000-0000-4000-8000-000000000101'
GROUP = 'c8c40000-0000-4000-8000-000000000003'
BATCH = 'c8c40000-0000-4000-8000-000000000008'
SIZE = 'c8c10000-0000-4000-8000-000000000002'
VENDOR = 'c8c20000-0000-4000-8000-000000000002'
PROCESS = 'c8c20000-0000-4000-8000-000000000003'
REQUESTS = {
    'WRITER_FIRST': 'c8fa0000-0000-4000-8000-000000000001',
    'ROLLBACK_FIRST': 'c8fa0000-0000-4000-8000-000000000002',
}
HOLD_SECONDS = 1.5


def connect(application_name: str):
    return psycopg.connect(PGURL, autocommit=False, application_name=application_name)


def scalar(query: str, params=()):
    with connect('cp6-v2620c-rollback-probe') as conn, conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None


def set_operator(cur):
    claims = json.dumps({'sub': OPERATOR_AUTH, 'role': 'authenticated'})
    cur.execute("select set_config('request.jwt.claims',%s,true)", (claims,))
    cur.execute('set local role authenticated')


def writer_call(cur, request_id: str):
    set_operator(cur)
    cur.execute('select row_version from erp.cutting_groups where id=%s::uuid', (GROUP,))
    expected_version = cur.fetchone()[0]
    payload = {
        'distribution_batch_id': BATCH,
        'vendor_id': VENDOR,
        'wash_process_id': PROCESS,
        'target_dyeing_color': 'NAVY',
        'physical_at': '2026-09-05T11:00:00Z',
        'reason': f'CP6 v20c live rollback {MODE.lower()}',
        'notes': 'Actual public business facade; no synthetic marker',
        'lines': [{'size_id': SIZE, 'qty_sent_pcs': 10}],
    }
    cur.execute(
        'select public.erp_save_laundry_qc_action_v1(%s,%s::jsonb,%s::uuid,%s)',
        ('POST_DELIVERY', json.dumps(payload), request_id, expected_version),
    )
    response = cur.fetchone()[0]
    if not response.get('committed') or response.get('action') != 'POST_DELIVERY':
        raise RuntimeError(f'Facade returned a non-commit envelope: {response}')
    return response


def rollback_process(label: str):
    env = {**os.environ, 'PGAPPNAME': label}
    return subprocess.Popen(
        ['psql', PGURL, '-X', '-v', 'ON_ERROR_STOP=1', '-f', str(ROLLBACK)],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
    )


def activity_pid(application_name: str) -> int | None:
    return scalar(
        "select pid from pg_stat_activity where application_name=%s order by pid limit 1",
        (application_name,),
    )


def observe_blocker(waiter_pid: int, holder_pid: int, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        blockers = scalar('select pg_blocking_pids(%s)', (waiter_pid,))
        if holder_pid in blockers:
            return True
        time.sleep(0.025)
    return False


def state(request_id: str) -> dict[str, Any]:
    return scalar(
        """
        select jsonb_build_object(
          'application_marker',(select count(*) from erp.schema_migrations
            where version='v2.6.20c'),
          'platform_marker',(select count(*) from supabase_migrations.schema_migrations
            where name='erp_v2_6_20c_cp6_deep_business_reliability'),
          'laundry_bs_resolver',to_regprocedure(
            'public.erp_search_laundry_bs_products_v1(uuid,timestamp with time zone,text,text,integer)'
          ) is not null,
          'delivery_rows',(select count(*) from erp.laundry_deliveries
            where special_instruction='Actual public business facade; no synthetic marker'),
          'request_status',(select status from erp.idempotency_requests
            where client_request_id=%s::uuid
              and operation_name='cp6_laundry_qc_action_v1:post_delivery'),
          'execution_context_rows',(select count(*) from erp.cp6_laundry_qc_execution_context),
          'unbalanced_journals',(select count(*) from(
            select e.id from erp.journal_entries e
            join erp.journal_lines l on l.journal_entry_id=e.id
            group by e.id having sum(l.debit)<>sum(l.credit)
          ) bad)
        )
        """,
        (request_id,),
    )


def writer_first() -> dict[str, Any]:
    request_id = REQUESTS[MODE]
    effects_ready = threading.Event()
    writer: dict[str, Any] = {}

    def work():
        conn = connect('cp6-v2620c-business-writer-first')
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute('select pg_backend_pid()')
                writer['pid'] = cur.fetchone()[0]
                writer['response'] = writer_call(cur, request_id)
                effects_ready.set()
                time.sleep(HOLD_SECONDS)
            conn.commit()
            writer['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - CI evidence
            conn.rollback()
            writer['status'] = 'FAIL'
            writer['error'] = str(exc)
            effects_ready.set()
        finally:
            conn.close()

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    if not effects_ready.wait(timeout=20) or writer.get('response') is None:
        raise RuntimeError(f'Business writer did not reach uncommitted facade completion: {writer}')

    app_name = 'cp6-v2620c-rollback-after-writer'
    started = time.monotonic()
    rollback = rollback_process(app_name)
    rollback_pid = None
    blocker_observed = False
    deadline = time.monotonic() + HOLD_SECONDS
    while time.monotonic() < deadline and rollback.poll() is None:
        rollback_pid = activity_pid(app_name)
        if rollback_pid and observe_blocker(rollback_pid, writer['pid'], 0.1):
            blocker_observed = True
            break
        time.sleep(0.025)
    stdout, stderr = rollback.communicate(timeout=30)
    elapsed = time.monotonic() - started
    thread.join(timeout=20)
    combined = stdout + stderr
    if thread.is_alive() or writer.get('status') != 'PASS':
        raise RuntimeError(f'Business writer failed: {writer}')
    if rollback.returncode == 0 or not blocker_observed:
        raise RuntimeError(
            f'Rollback did not block behind actual facade: rc={rollback.returncode}, '
            f'blocker={blocker_observed}, output={combined}'
        )
    if 'v2.6.20c rollback refused: post-install business/HPP history exists' not in combined:
        raise RuntimeError(f'Rollback returned the wrong post-use decision: {combined}')
    final_state = state(request_id)
    expected = {
        'application_marker': 1, 'platform_marker': 1,
        'laundry_bs_resolver': True, 'delivery_rows': 1,
        'request_status': 'COMPLETED', 'execution_context_rows': 0,
        'unbalanced_journals': 0,
    }
    if final_state != expected:
        raise RuntimeError(f'Writer-first final state mismatch: {final_state}')
    return {
        'status': 'PASS', 'ordering': 'BUSINESS_WRITER_THEN_ROLLBACK',
        'writer': writer, 'rollback_pid': rollback_pid,
        'pg_blocking_pids_observed': blocker_observed,
        'rollback_waited_seconds': round(elapsed, 3),
        'rollback_refused_post_use': True, 'final_state': final_state,
    }


def rollback_first() -> dict[str, Any]:
    request_id = REQUESTS[MODE]
    gate = connect('cp6-v2620c-rollback-order-gate')
    gate_cur = gate.cursor()
    gate_cur.execute('select pg_backend_pid()')
    gate_pid = gate_cur.fetchone()[0]
    # Instrumentation only: pause the exact rollback on its final listed table
    # after it has acquired the earlier business-table locks. The business
    # blocker asserted below must be the rollback PID, never this gate PID.
    gate_cur.execute('lock table erp.qc_inspection_items in access exclusive mode')

    app_name = 'cp6-v2620c-rollback-before-writer'
    rollback = rollback_process(app_name)
    rollback_pid = None
    rollback_blocked_by_gate = False
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        rollback_pid = activity_pid(app_name)
        if rollback_pid and observe_blocker(rollback_pid, gate_pid, 0.1):
            rollback_blocked_by_gate = True
            break
        if rollback.poll() is not None:
            break
        time.sleep(0.025)
    if not rollback_pid or not rollback_blocked_by_gate:
        gate.rollback()
        gate.close()
        stdout, stderr = rollback.communicate(timeout=30)
        raise RuntimeError(f'Could not pause exact rollback: {stdout + stderr}')

    writer: dict[str, Any] = {}
    writer_started = threading.Event()

    def work():
        conn = connect('cp6-v2620c-business-writer-after-rollback-lock')
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute('select pg_backend_pid()')
                writer['pid'] = cur.fetchone()[0]
                writer_started.set()
                writer['response'] = writer_call(cur, request_id)
            conn.commit()
            writer['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - CI evidence
            conn.rollback()
            writer['status'] = 'FAIL'
            writer['error'] = str(exc)
            writer_started.set()
        finally:
            conn.close()

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    if not writer_started.wait(timeout=10):
        raise RuntimeError('Rollback-first writer did not publish its PID')
    writer_blocked_by_rollback = observe_blocker(writer['pid'], rollback_pid, 2.0)
    gate.rollback()
    gate_cur.close()
    gate.close()
    stdout, stderr = rollback.communicate(timeout=30)
    thread.join(timeout=30)
    if rollback.returncode != 0:
        raise RuntimeError(f'Pre-use rollback failed: {stdout + stderr}')
    if thread.is_alive() or writer.get('status') != 'PASS':
        raise RuntimeError(f'Post-rollback predecessor writer failed: {writer}')
    if not writer_blocked_by_rollback:
        raise RuntimeError(f'Actual writer was not blocked by rollback PID: {writer}')
    final_state = state(request_id)
    expected = {
        'application_marker': 0, 'platform_marker': 0,
        'laundry_bs_resolver': False, 'delivery_rows': 1,
        'request_status': 'COMPLETED', 'execution_context_rows': 0,
        'unbalanced_journals': 0,
    }
    if final_state != expected:
        raise RuntimeError(f'Rollback-first final state mismatch: {final_state}')
    return {
        'status': 'PASS', 'ordering': 'ROLLBACK_LOCKS_THEN_BUSINESS_WRITER',
        'rollback_pid': rollback_pid, 'writer': writer,
        'gate_instrumentation_pid': gate_pid,
        'rollback_blocked_by_gate_before_writer_started': True,
        'writer_blocked_by_exact_rollback_pid': writer_blocked_by_rollback,
        'pre_use_rollback_committed': True,
        'writer_committed_under_restored_v2620b': True,
        'final_state': final_state,
    }


def main():
    if MODE not in REQUESTS:
        raise RuntimeError(f'Unsupported CP6_ROLLBACK_RACE_MODE: {MODE}')
    result = writer_first() if MODE == 'WRITER_FIRST' else rollback_first()
    report = {
        'classification': 'DISPOSABLE_V2620C_ACTUAL_BUSINESS_FACADE_ROLLBACK_RACE',
        'database_scope': 'ISOLATED_CLONE_DESTROYED_BY_WORKFLOW',
        'actual_facade': 'public.erp_save_laundry_qc_action_v1',
        'synthetic_business_marker_used': False,
        'production_go': False,
        **result,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, sort_keys=True))


try:
    main()
except Exception as error:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps({
        'status': 'FAIL',
        'classification': 'DISPOSABLE_V2620C_ACTUAL_BUSINESS_FACADE_ROLLBACK_RACE',
        'mode': MODE, 'error': str(error), 'production_go': False,
    }, indent=2, sort_keys=True) + '\n')
    raise
