#!/usr/bin/env python3
import json
import os
import threading
import time
import uuid
from pathlib import Path

import psycopg

PGURL = os.environ.get('PGURL', 'postgresql://postgres:postgres@127.0.0.1:54322/postgres')
REPORT = Path(os.environ.get('CP3_R3_CONCURRENCY_REPORT', 'cp3-r3-concurrency-report.json'))
PERIOD_START = '2026-01-01'
PERIOD_END = '2026-01-01'


def connect():
    return psycopg.connect(PGURL, autocommit=False)


def one(query, params=()):
    with connect() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None


def create_pool(correction_of=None):
    payload = {
        'period_start': PERIOD_START,
        'period_end': PERIOD_END,
        'reason': 'CP3 R3 concurrency pool',
    }
    if correction_of:
        payload['correction_of_pool_id'] = str(correction_of)
    result = one(
        'select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s::uuid)',
        (json.dumps(payload), str(uuid.uuid4())),
    )
    return result['pool_id']


def cancel_pool(pool_id, expected_version=2):
    return one(
        'select erp.cancel_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s)',
        (str(pool_id), 'CP3 R3 concurrency cleanup', str(uuid.uuid4()), expected_version),
    )


def holder_activate(pool_id, started, result, delay=1.0):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            cur.execute('select erp._cp3_lock_business_period(%s::date,%s::date)', (PERIOD_START, PERIOD_END))
            started.set()
            time.sleep(delay)
            cur.execute(
                'select erp.activate_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s)',
                (str(pool_id), 'CP3 R3 concurrent activate', str(uuid.uuid4()), 1),
            )
            result['value'] = cur.fetchone()[0]
        conn.commit()
        result['status'] = 'PASS'
    except Exception as exc:
        conn.rollback()
        result['status'] = 'FAIL'
        result['error'] = str(exc)
    finally:
        conn.close()


def blocked_call(started, result, query, params, expected_fragment):
    started.wait(timeout=10)
    began = time.monotonic()
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            cur.execute(query, params)
            result['unexpected_value'] = cur.fetchone()[0] if cur.description else None
        conn.commit()
        result['status'] = 'UNEXPECTED_SUCCESS'
    except Exception as exc:
        conn.rollback()
        result['error'] = str(exc)
        result['status'] = 'EXPECTED_REJECTION' if expected_fragment in str(exc) else 'WRONG_ERROR'
    finally:
        result['elapsed_seconds'] = round(time.monotonic() - began, 3)
        conn.close()


def activation_first_scenario(label, pool_id, query, params, expected_fragment):
    started = threading.Event()
    activate_result = {}
    source_result = {}
    ta = threading.Thread(target=holder_activate, args=(pool_id, started, activate_result), daemon=True)
    tb = threading.Thread(target=blocked_call, args=(started, source_result, query, params, expected_fragment), daemon=True)
    ta.start(); tb.start(); ta.join(timeout=20); tb.join(timeout=20)
    if ta.is_alive() or tb.is_alive():
        raise RuntimeError(f'{label}: thread timeout')
    if activate_result.get('status') != 'PASS':
        raise RuntimeError(f'{label}: activation failed: {activate_result}')
    if source_result.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'{label}: source mutation was not rejected correctly: {source_result}')
    if source_result.get('elapsed_seconds', 0) < 0.5:
        raise RuntimeError(f'{label}: source mutation did not demonstrably wait on the shared period lock: {source_result}')
    cancel_pool(pool_id)
    return {
        'label': label,
        'activation': activate_result,
        'source_mutation': source_result,
        'terminal_pool_status': one('select status from erp.attendance_hpp_pools where id=%s::uuid', (str(pool_id),)),
    }


def source_first_record(pool_id):
    started = threading.Event()
    source_result = {}
    activate_result = {}

    def source_holder():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute('select erp._cp3_lock_business_date(%s::date)', (PERIOD_START,))
                cur.execute(
                    'select erp.record_sewing_terminal_v1(%s::jsonb,%s::uuid)',
                    (json.dumps({
                        'work_completion_id': 'a5000000-0000-0000-0000-000000000012',
                        'qty_pcs': 5,
                        'reason': 'CP3 R3 source-first race',
                    }), str(uuid.uuid4())),
                )
                source_result['value'] = cur.fetchone()[0]
                started.set()
                time.sleep(1.0)
            conn.commit()
            source_result['status'] = 'PASS'
        except Exception as exc:
            conn.rollback()
            source_result['status'] = 'FAIL'
            source_result['error'] = str(exc)
            started.set()
        finally:
            conn.close()

    def waiting_activate():
        started.wait(timeout=10)
        began = time.monotonic()
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute(
                    'select erp.activate_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s)',
                    (str(pool_id), 'CP3 R3 source-first activation', str(uuid.uuid4()), 1),
                )
                activate_result['unexpected_value'] = cur.fetchone()[0]
            conn.commit()
            activate_result['status'] = 'UNEXPECTED_SUCCESS'
        except Exception as exc:
            conn.rollback()
            activate_result['error'] = str(exc)
            activate_result['status'] = 'EXPECTED_STALE_REJECTION' if 'STALE_POOL_INPUT' in str(exc) else 'WRONG_ERROR'
        finally:
            activate_result['elapsed_seconds'] = round(time.monotonic() - began, 3)
            conn.close()

    ts = threading.Thread(target=source_holder, daemon=True)
    ta = threading.Thread(target=waiting_activate, daemon=True)
    ts.start(); ta.start(); ts.join(timeout=20); ta.join(timeout=20)
    if ts.is_alive() or ta.is_alive():
        raise RuntimeError('source-first: thread timeout')
    if source_result.get('status') != 'PASS':
        raise RuntimeError(f'source-first record failed: {source_result}')
    if activate_result.get('status') != 'EXPECTED_STALE_REJECTION':
        raise RuntimeError(f'source-first activation did not fail stale: {activate_result}')
    if activate_result.get('elapsed_seconds', 0) < 0.5:
        raise RuntimeError(f'source-first activation did not wait on shared lock: {activate_result}')
    return {
        'label': 'record-first-vs-activate',
        'source_mutation': source_result,
        'activation': activate_result,
        'pool_status': one('select status from erp.attendance_hpp_pools where id=%s::uuid', (str(pool_id),)),
    }


def source_first_cancel_payroll(pool_id):
    started = threading.Event()
    source_result = {}
    activate_result = {}

    def cancellation_holder():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute('select erp._cp3_lock_business_period(%s::date,%s::date)', (PERIOD_START, PERIOD_END))
                cur.execute(
                    'select erp.cancel_unpaid_payroll(%s::uuid,%s)',
                    ('a6000000-0000-0000-0000-000000000002', 'CP3 R3 cancellation-first race'),
                )
                started.set()
                time.sleep(1.0)
            conn.commit()
            source_result['status'] = 'PASS'
        except Exception as exc:
            conn.rollback()
            source_result['status'] = 'FAIL'
            source_result['error'] = str(exc)
            started.set()
        finally:
            conn.close()

    def waiting_activate():
        started.wait(timeout=10)
        began = time.monotonic()
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute(
                    'select erp.activate_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s)',
                    (str(pool_id), 'CP3 R3 cancellation-first activation', str(uuid.uuid4()), 1),
                )
                activate_result['unexpected_value'] = cur.fetchone()[0]
            conn.commit()
            activate_result['status'] = 'UNEXPECTED_SUCCESS'
        except Exception as exc:
            conn.rollback()
            activate_result['error'] = str(exc)
            activate_result['status'] = 'EXPECTED_STALE_REJECTION' if 'STALE_POOL_INPUT' in str(exc) else 'WRONG_ERROR'
        finally:
            activate_result['elapsed_seconds'] = round(time.monotonic() - began, 3)
            conn.close()

    ts = threading.Thread(target=cancellation_holder, daemon=True)
    ta = threading.Thread(target=waiting_activate, daemon=True)
    ts.start(); ta.start(); ts.join(timeout=20); ta.join(timeout=20)
    if ts.is_alive() or ta.is_alive():
        raise RuntimeError('cancellation-first: thread timeout')
    if source_result.get('status') != 'PASS':
        raise RuntimeError(f'cancellation-first payroll mutation failed: {source_result}')
    if activate_result.get('status') != 'EXPECTED_STALE_REJECTION':
        raise RuntimeError(f'cancellation-first activation did not fail stale: {activate_result}')
    if activate_result.get('elapsed_seconds', 0) < 0.5:
        raise RuntimeError(f'cancellation-first activation did not wait on shared lock: {activate_result}')
    return {
        'label': 'cancel-payroll-first-vs-activate',
        'source_mutation': source_result,
        'activation': activate_result,
        'pool_status': one('select status from erp.attendance_hpp_pools where id=%s::uuid', (str(pool_id),)),
        'payroll_status': one("select status from erp.payroll_settlements where id='a6000000-0000-0000-0000-000000000002'::uuid"),
    }

def main():
    results = []

    # 1. Activation wins; a late/backdated sewing record waits and then fails closed.
    p1 = create_pool()
    results.append(activation_first_scenario(
        'activate-vs-record', p1,
        'select erp.record_sewing_terminal_v1(%s::jsonb,%s::uuid)',
        (json.dumps({
            'work_completion_id': 'a5000000-0000-0000-0000-000000000011',
            'qty_pcs': 10,
            'reason': 'CP3 R3 activation-first late record',
        }), str(uuid.uuid4())),
        'ACTIVE_ATTENDANCE_HPP_PERIOD_LOCKED',
    ))

    # 2. Activation wins; a terminal reversal waits and then sees the active consumption.
    p2 = create_pool(p1)
    event_a = one("select id from erp.sewing_terminal_events where source_work_completion_id='a5000000-0000-0000-0000-000000000001'::uuid")
    event_version = one('select row_version from erp.sewing_terminal_events where id=%s::uuid', (str(event_a),))
    results.append(activation_first_scenario(
        'activate-vs-reverse-sewing', p2,
        'select erp.reverse_sewing_terminal_v1(%s::uuid,%s,%s::uuid,%s)',
        (str(event_a), 'CP3 R3 activation-first reverse', str(uuid.uuid4()), event_version),
        'consumed by an ACTIVE attendance HPP pool',
    ))

    # 3. Activation wins; payroll cancellation waits and then cannot remove a consumed source.
    p3 = create_pool(p2)
    results.append(activation_first_scenario(
        'activate-vs-cancel-approved-payroll', p3,
        'select erp.cancel_unpaid_payroll(%s::uuid,%s)',
        ('a6000000-0000-0000-0000-000000000002', 'CP3 R3 activation-first payroll cancel'),
        'PAYROLL_CONSUMED_BY_ACTIVE_HPP_POOL',
    ))

    # 4. Source mutation wins; activation waits and then rejects the stale DRAFT manifest.
    p4 = create_pool(p3)
    results.append(source_first_record(p4))
    cancel_pool(p4, expected_version=1)

    # 5. Payroll source cancellation wins; activation waits and rejects the stale DRAFT basis.
    p5 = create_pool()
    results.append(source_first_cancel_payroll(p5))
    cancel_pool(p5, expected_version=1)

    report = {
        'status': 'PASS',
        'mode': 'REAL_TWO_CONNECTION_FULL_SCHEMA',
        'postgres_connections_per_race': 2,
        'business_timezone': 'Asia/Jakarta',
        'scenarios': results,
        'assertions': {
            'activate_vs_record': True,
            'activate_vs_reverse': True,
            'activate_vs_payroll_cancel': True,
            'record_first_stales_activation': True,
            'payroll_cancel_first_stales_activation': True,
            'stale_drafts_voided': True,
            'shared_lock_wait_observed': True,
        },
    }
    REPORT.write_text(json.dumps(report, indent=2, default=str) + '\n')
    print(json.dumps(report, indent=2, default=str))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        failure = {'status': 'FAIL', 'error': str(exc)}
        REPORT.write_text(json.dumps(failure, indent=2) + '\n')
        raise
