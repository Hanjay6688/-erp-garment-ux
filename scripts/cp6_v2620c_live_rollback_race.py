#!/usr/bin/env python3
"""Prove an exact CP6 rollback ordering against an actual uncommitted facade.

The default target remains v2.6.20c for the historical proof. Environment
overrides let a forward successor reuse the same native two-connection test
without weakening it into a synthetic marker check.
"""
from __future__ import annotations

import json
import os
import re
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
TARGET_VERSION = os.environ.get('CP6_ROLLBACK_TARGET_VERSION', 'v2.6.20c')
PLATFORM_NAME = os.environ.get(
    'CP6_ROLLBACK_PLATFORM_NAME',
    'erp_v2_6_20c_cp6_deep_business_reliability',
)
PREDECESSOR_VERSION = os.environ.get('CP6_ROLLBACK_PREDECESSOR_VERSION', 'v2.6.20b')
TARGET_REG_KIND = os.environ.get('CP6_ROLLBACK_TARGET_REG_KIND', 'procedure')
TARGET_REG_IDENTITY = os.environ.get(
    'CP6_ROLLBACK_TARGET_REG_IDENTITY',
    'public.erp_search_laundry_bs_products_v1(uuid,timestamp with time zone,text,text,integer)',
)
REFUSAL = os.environ.get(
    'CP6_ROLLBACK_POST_USE_REFUSAL',
    'v2.6.20c rollback refused: post-install business/HPP history exists',
)
EVIDENCE_TAG = os.environ.get('CP6_ROLLBACK_EVIDENCE_TAG', 'V2620C')
GATE_RELATION = os.environ.get('CP6_ROLLBACK_GATE_RELATION', 'erp.qc_inspection_items')
REPORT = Path(os.environ.get(
    'CP6_ROLLBACK_RACE_REPORT',
    f'cp6-{EVIDENCE_TAG.lower()}-live-rollback-{MODE.lower()}.json',
))
ROLLBACK = Path(os.environ.get(
    'CP6_ROLLBACK_SQL_PATH',
    'supabase/rollbacks/20260907190000_erp_v2_6_20c_cp6_deep_business_reliability.rollback.sql',
))
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
ROLLBACK_FIRST_BLOCK_TIMEOUT_SECONDS = 8.0


def connect(application_name: str):
    return psycopg.connect(PGURL, autocommit=False, application_name=application_name)


def scalar(query: str, params=()):
    with connect(f'cp6-{EVIDENCE_TAG.lower()}-rollback-probe') as conn, conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None


def set_operator(cur):
    claims = json.dumps({'sub': OPERATOR_AUTH, 'role': 'authenticated'})
    cur.execute("select set_config('request.jwt.claims',%s,true)", (claims,))
    cur.execute('set local role authenticated')


def expected_version_from_workspace(cur) -> int:
    # Resolve the optimistic version through the same authenticated public
    # workspace contract used by the client. Never grant/read the private
    # cutting_groups table merely to make a rollback harness pass.
    cur.execute("select public.erp_get_laundry_qc_workspace_v1('LAUNDRY',null)")
    workspace = cur.fetchone()[0]
    ready_batch = next(
        (
            row for row in workspace.get('ready_batches', [])
            if row.get('distribution_batch_id') == BATCH
        ),
        None,
    )
    if ready_batch is None:
        raise RuntimeError('Authenticated workspace did not expose the seeded ready batch')
    expected_version = int(ready_batch['cutting_group_row_version'])
    return expected_version


def writer_call(cur, request_id: str, expected_version: int | None = None):
    set_operator(cur)
    if expected_version is None:
        expected_version = expected_version_from_workspace(cur)
    payload = {
        'distribution_batch_id': BATCH,
        'vendor_id': VENDOR,
        'wash_process_id': PROCESS,
        'target_dyeing_color': 'NAVY',
        'physical_at': '2026-09-05T11:00:00Z',
        'reason': f'CP6 {EVIDENCE_TAG} live rollback {MODE.lower()}',
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


def relation_lock_snapshot(*pids: int) -> list[dict[str, Any]]:
    """Resolve the exact relation locks without relying on ephemeral OIDs."""
    return scalar(
        """
        select coalesce(jsonb_agg(jsonb_build_object(
          'pid',l.pid,'relation_oid',l.relation,
          'relation_name',coalesce(l.relation::regclass::text,'UNKNOWN'),
          'mode',l.mode,'granted',l.granted
        ) order by l.pid,l.granted,l.relation,l.mode),'[]'::jsonb)
        from pg_locks l
        where l.locktype='relation' and l.pid=any(%s::integer[])
        """,
        (list(pids),),
    )


def relation_names_from_error(error: str) -> dict[str, str]:
    relation_oids = sorted({int(value) for value in re.findall(r'relation (\d+)', error)})
    return {
        str(oid): scalar('select %s::oid::regclass::text', (oid,))
        for oid in relation_oids
    }


def state(request_id: str) -> dict[str, Any]:
    if TARGET_REG_KIND == 'procedure':
        target_presence = 'to_regprocedure(%s) is not null'
    elif TARGET_REG_KIND == 'class':
        target_presence = 'to_regclass(%s) is not null'
    else:
        raise RuntimeError(f'Unsupported CP6_ROLLBACK_TARGET_REG_KIND: {TARGET_REG_KIND}')
    return scalar(
        f"""
        select jsonb_build_object(
          'application_marker',(select count(*) from erp.schema_migrations
            where version=%s),
          'platform_marker',(select count(*) from supabase_migrations.schema_migrations
            where name=%s),
          'target_object',{target_presence},
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
        (TARGET_VERSION, PLATFORM_NAME, TARGET_REG_IDENTITY, request_id),
    )


def writer_first() -> dict[str, Any]:
    request_id = REQUESTS[MODE]
    effects_ready = threading.Event()
    writer: dict[str, Any] = {}

    def work():
        conn = connect(f'cp6-{EVIDENCE_TAG.lower()}-business-writer-first')
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
            writer['sqlstate'] = getattr(exc, 'sqlstate', None)
            effects_ready.set()
        finally:
            conn.close()

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    if not effects_ready.wait(timeout=20) or writer.get('response') is None:
        raise RuntimeError(f'Business writer did not reach uncommitted facade completion: {writer}')

    app_name = f'cp6-{EVIDENCE_TAG.lower()}-rollback-after-writer'
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
    if REFUSAL not in combined:
        raise RuntimeError(f'Rollback returned the wrong post-use decision: {combined}')
    final_state = state(request_id)
    expected = {
        'application_marker': 1, 'platform_marker': 1,
        'target_object': True, 'delivery_rows': 1,
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
    # Complete the authenticated, public read-only workspace lookup before
    # starting the rollback gate. The measured interval below therefore covers
    # the actual mutating facade reaching a conflicting table lock, not variable
    # CI time spent rendering its optimistic-version workspace.
    with connect(f'cp6-{EVIDENCE_TAG.lower()}-workspace-before-rollback-gate') as preread:
        with preread.cursor() as preread_cur:
            set_operator(preread_cur)
            expected_version = expected_version_from_workspace(preread_cur)
        preread.commit()

    gate = connect(f'cp6-{EVIDENCE_TAG.lower()}-rollback-order-gate')
    gate_cur = gate.cursor()
    gate_cur.execute('select pg_backend_pid()')
    gate_pid = gate_cur.fetchone()[0]
    # Instrumentation only: pause the exact rollback on its final listed table
    # after it has acquired the earlier business-table locks. The business
    # blocker asserted below must be the rollback PID, never this gate PID.
    if not re.fullmatch(r'erp\.[a-z0-9_]+', GATE_RELATION):
        raise RuntimeError(f'Unsafe CP6_ROLLBACK_GATE_RELATION: {GATE_RELATION}')
    gate_cur.execute(f'lock table {GATE_RELATION} in access exclusive mode')

    app_name = f'cp6-{EVIDENCE_TAG.lower()}-rollback-before-writer'
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
        conn = connect(f'cp6-{EVIDENCE_TAG.lower()}-business-writer-after-rollback-lock')
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute('select pg_backend_pid()')
                writer['pid'] = cur.fetchone()[0]
                writer_started.set()
                writer['response'] = writer_call(cur, request_id, expected_version)
            conn.commit()
            writer['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - CI evidence
            conn.rollback()
            writer['status'] = 'FAIL'
            writer['error'] = str(exc)
            writer['sqlstate'] = getattr(exc, 'sqlstate', None)
            writer_started.set()
        finally:
            conn.close()

    thread = threading.Thread(target=work, daemon=True)
    thread.start()
    if not writer_started.wait(timeout=10):
        raise RuntimeError('Rollback-first writer did not publish its PID')
    writer_blocked_by_rollback = observe_blocker(
        writer['pid'], rollback_pid, ROLLBACK_FIRST_BLOCK_TIMEOUT_SECONDS,
    )
    pre_release_locks = relation_lock_snapshot(rollback_pid, writer['pid'])
    gate.rollback()
    gate_cur.close()
    gate.close()
    stdout, stderr = rollback.communicate(timeout=30)
    thread.join(timeout=30)
    if rollback.returncode != 0:
        raise RuntimeError(f'Pre-use rollback failed: {stdout + stderr}')
    if thread.is_alive() or writer.get('status') != 'PASS':
        relation_names = relation_names_from_error(writer.get('error', ''))
        raise RuntimeError(
            'Post-rollback predecessor writer failed: '
            f'writer={writer}, relation_names={relation_names}, '
            f'pre_release_locks={pre_release_locks}, '
            f'rollback_returncode={rollback.returncode}, rollback_output={stdout + stderr}'
        )
    if not writer_blocked_by_rollback:
        raise RuntimeError(f'Actual writer was not blocked by rollback PID: {writer}')
    final_state = state(request_id)
    expected = {
        'application_marker': 0, 'platform_marker': 0,
        'target_object': False, 'delivery_rows': 1,
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
        'optimistic_version_source': 'AUTHENTICATED_PUBLIC_WORKSPACE_BEFORE_ROLLBACK_GATE',
        'block_observation_timeout_seconds': ROLLBACK_FIRST_BLOCK_TIMEOUT_SECONDS,
        'pre_use_rollback_committed': True,
        'writer_committed_under_restored_predecessor': PREDECESSOR_VERSION,
        'final_state': final_state,
    }


def main():
    if MODE not in REQUESTS:
        raise RuntimeError(f'Unsupported CP6_ROLLBACK_RACE_MODE: {MODE}')
    result = writer_first() if MODE == 'WRITER_FIRST' else rollback_first()
    report = {
        'classification': f'DISPOSABLE_{EVIDENCE_TAG}_ACTUAL_BUSINESS_FACADE_ROLLBACK_RACE',
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
        'classification': f'DISPOSABLE_{EVIDENCE_TAG}_ACTUAL_BUSINESS_FACADE_ROLLBACK_RACE',
        'mode': MODE, 'error': str(error), 'production_go': False,
    }, indent=2, sort_keys=True) + '\n')
    raise
