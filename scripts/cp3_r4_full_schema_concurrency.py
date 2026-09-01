#!/usr/bin/env python3
"""Real two-session CP3 R4 races on the exact restored ERP Enteng schema."""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Callable

import psycopg

PGURL = os.environ.get('PGURL', 'postgresql://postgres:postgres@127.0.0.1:54322/postgres')
REPORT = Path(os.environ.get('CP3_R4_CONCURRENCY_REPORT', 'cp3-r4-concurrency-report.json'))
WAIT_FLOOR_SECONDS = 0.5
HOLD_SECONDS = 1.0


def connect():
    return psycopg.connect(PGURL, autocommit=False)


def one(query: str, params=()):
    with connect() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None


def scalar(query: str, params=()):
    return one(query, params)


def create_pool(period: str, correction_of=None):
    payload = {'period_start': period, 'period_end': period, 'reason': f'CP3 R4 race pool {period}'}
    if correction_of:
        payload['correction_of_pool_id'] = str(correction_of)
    result = one(
        'select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s::uuid)',
        (json.dumps(payload), str(uuid.uuid4())),
    )
    return result['pool_id']


def cancel_pool(pool_id, expected_version=2, reason='CP3 R4 race cleanup'):
    return one(
        'select erp.cancel_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s)',
        (str(pool_id), reason, str(uuid.uuid4()), expected_version),
    )


def assert_wait(result: dict, label: str):
    if result.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'{label}: shared-lock wait was not observed: {result}')


def activation_holder(pool_id, period: str, started: threading.Event, result: dict):
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute("set local lock_timeout='10s'")
            cur.execute('select erp._cp3_lock_business_period(%s::date,%s::date)', (period, period))
            # Lock manifest contractors before announcing activation-first, so policy races are ordered too.
            cur.execute('select erp._cp3_lock_manifest_contractors(%s::date,%s::date)', (period, period))
            started.set()
            time.sleep(HOLD_SECONDS)
            cur.execute(
                'select erp.activate_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s)',
                (str(pool_id), f'CP3 R4 concurrent activate {period}', str(uuid.uuid4()), 1),
            )
            result['value'] = cur.fetchone()[0]
        conn.commit()
        result['status'] = 'PASS'
    except Exception as exc:
        conn.rollback()
        result['status'] = 'FAIL'
        result['error'] = str(exc)
        started.set()
    finally:
        conn.close()


def waiting_call(started: threading.Event, result: dict, query: str, params, expected_fragment: str):
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


def activation_first(label: str, period: str, query: str, params, expected_fragment: str):
    pool_id = create_pool(period)
    started = threading.Event()
    activation = {}
    mutation = {}
    ta = threading.Thread(target=activation_holder, args=(pool_id, period, started, activation), daemon=True)
    tm = threading.Thread(target=waiting_call, args=(started, mutation, query, params, expected_fragment), daemon=True)
    ta.start(); tm.start(); ta.join(timeout=25); tm.join(timeout=25)
    if ta.is_alive() or tm.is_alive():
        raise RuntimeError(f'{label}: thread timeout')
    if activation.get('status') != 'PASS':
        raise RuntimeError(f'{label}: activation failed: {activation}')
    if mutation.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'{label}: mutation was not rejected as expected: {mutation}')
    assert_wait(mutation, label)
    cancel_pool(pool_id)
    return {
        'label': label,
        'order': 'ACTIVATION_FIRST',
        'pool_id': str(pool_id),
        'activation': activation,
        'mutation': mutation,
        'terminal_pool_status': scalar('select status from erp.attendance_hpp_pools where id=%s::uuid', (str(pool_id),)),
    }


def source_first_stales(
    label: str,
    period: str,
    source_work: Callable,
    expected_source_status: str = 'PASS',
):
    pool_id = create_pool(period)
    started = threading.Event()
    source_result = {}
    activation_result = {}

    def source_holder():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                source_work(cur, source_result)
                started.set()
                time.sleep(HOLD_SECONDS)
            conn.commit()
            source_result.setdefault('status', 'PASS')
        except Exception as exc:
            conn.rollback()
            source_result['status'] = 'FAIL'
            source_result['error'] = str(exc)
            started.set()
        finally:
            conn.close()

    def waiting_activation():
        started.wait(timeout=10)
        began = time.monotonic()
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute(
                    'select erp.activate_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s)',
                    (str(pool_id), f'CP3 R4 {label}', str(uuid.uuid4()), 1),
                )
                activation_result['unexpected_value'] = cur.fetchone()[0]
            conn.commit()
            activation_result['status'] = 'UNEXPECTED_SUCCESS'
        except Exception as exc:
            conn.rollback()
            activation_result['error'] = str(exc)
            activation_result['status'] = 'EXPECTED_STALE_REJECTION' if 'STALE_POOL_INPUT' in str(exc) else 'WRONG_ERROR'
        finally:
            activation_result['elapsed_seconds'] = round(time.monotonic() - began, 3)
            conn.close()

    ts = threading.Thread(target=source_holder, daemon=True)
    ta = threading.Thread(target=waiting_activation, daemon=True)
    ts.start(); ta.start(); ts.join(timeout=25); ta.join(timeout=25)
    if ts.is_alive() or ta.is_alive():
        raise RuntimeError(f'{label}: thread timeout')
    if source_result.get('status') != expected_source_status:
        raise RuntimeError(f'{label}: source mutation failed: {source_result}')
    if activation_result.get('status') != 'EXPECTED_STALE_REJECTION':
        raise RuntimeError(f'{label}: activation did not reject stale DRAFT: {activation_result}')
    assert_wait(activation_result, label)
    cancel_pool(pool_id, expected_version=1, reason=f'CP3 R4 void stale {label}')
    return {
        'label': label,
        'order': 'SOURCE_FIRST',
        'pool_id': str(pool_id),
        'source_mutation': source_result,
        'activation': activation_result,
        'terminal_pool_status': scalar('select status from erp.attendance_hpp_pools where id=%s::uuid', (str(pool_id),)),
    }


def reverse_work_rejects_first_then_activation(period: str, completion_id: str):
    label = 'reverse-work-first-rejects-vs-activate'
    pool_id = create_pool(period)
    started = threading.Event()
    reverse_result = {}
    activation_result = {}

    def reverse_holder():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute('select erp._cp3_lock_business_date(%s::date)', (period,))
                cur.execute('savepoint before_reverse')
                try:
                    cur.execute('select erp.reverse_work_completion(%s::uuid,%s)', (completion_id, 'CP3 R4 reverse-first dependency proof'))
                    reverse_result['status'] = 'UNEXPECTED_SUCCESS'
                except Exception as exc:
                    message = str(exc)
                    reverse_result['error'] = message
                    reverse_result['status'] = (
                        'EXPECTED_REJECTION'
                        if 'Work completion masih memiliki SELESAI_DIJAHIT aktif' in message
                        and 'reverse_sewing_terminal_v1() terlebih dahulu' in message
                        else 'WRONG_ERROR'
                    )
                    cur.execute('rollback to savepoint before_reverse')
                cur.execute('release savepoint before_reverse')
                started.set()
                time.sleep(HOLD_SECONDS)
            conn.commit()
        except Exception as exc:
            conn.rollback()
            reverse_result['status'] = 'FAIL'
            reverse_result['error'] = str(exc)
            started.set()
        finally:
            conn.close()

    def waiting_activation():
        started.wait(timeout=10)
        began = time.monotonic()
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute(
                    'select erp.activate_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s)',
                    (str(pool_id), 'CP3 R4 activation after rejected reverse work', str(uuid.uuid4()), 1),
                )
                activation_result['value'] = cur.fetchone()[0]
            conn.commit()
            activation_result['status'] = 'PASS'
        except Exception as exc:
            conn.rollback()
            activation_result['status'] = 'FAIL'
            activation_result['error'] = str(exc)
        finally:
            activation_result['elapsed_seconds'] = round(time.monotonic() - began, 3)
            conn.close()

    tr = threading.Thread(target=reverse_holder, daemon=True)
    ta = threading.Thread(target=waiting_activation, daemon=True)
    tr.start(); ta.start(); tr.join(timeout=25); ta.join(timeout=25)
    if tr.is_alive() or ta.is_alive():
        raise RuntimeError(f'{label}: thread timeout')
    if reverse_result.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'{label}: reverse did not fail closed: {reverse_result}')
    if activation_result.get('status') != 'PASS':
        raise RuntimeError(f'{label}: activation should succeed after rejected non-mutation: {activation_result}')
    assert_wait(activation_result, label)
    if scalar('select status from erp.work_completion_events where id=%s::uuid', (completion_id,)) != 'POSTED':
        raise RuntimeError(f'{label}: rejected reversal changed completion state')
    cancel_pool(pool_id)
    return {
        'label': label,
        'order': 'REVERSE_WORK_LOCK_FIRST',
        'reverse_work': reverse_result,
        'activation': activation_result,
        'terminal_pool_status': scalar('select status from erp.attendance_hpp_pools where id=%s::uuid', (str(pool_id),)),
    }


def service_role_reversal_proof():
    period = '2026-01-01'
    pool_id = create_pool(period)
    active = one(
        'select erp.activate_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s)',
        (str(pool_id), 'CP3 R4 protected reversal proof', str(uuid.uuid4()), 1),
    )
    pool_journal = scalar('select post_journal_entry_id from erp.attendance_hpp_pools where id=%s::uuid', (str(pool_id),))
    payroll_journal = scalar(
        "select id from erp.journal_entries where source_type='PAYROLL_ATTENDANCE_ACCRUAL' "
        "and source_id='a6000000-0000-0000-0000-000000000001'::uuid and status='POSTED'",
    )
    rejected = []
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute('set role service_role')
            protected = (
                (pool_journal, 'ATTENDANCE_HPP_POOL'),
                (payroll_journal, 'PAYROLL_ATTENDANCE_ACCRUAL'),
            )
            for index, (journal_id, expected_source_type) in enumerate(protected, start=1):
                cur.execute(f'savepoint protected_{index}')
                try:
                    cur.execute('select erp.reverse_journal(%s::uuid,%s)', (str(journal_id), 'CP3 R4 direct service-role protected reversal'))
                    raise RuntimeError(f'protected journal {journal_id} unexpectedly reversed')
                except psycopg.Error as exc:
                    message = str(exc)
                    cur.execute(f'rollback to savepoint protected_{index}')
                    expected_public_denial = (
                        'permission denied for schema erp' in message
                        or 'permission denied for function reverse_journal' in message
                    )
                    if not expected_public_denial:
                        raise RuntimeError(f'wrong service_role public denial: {message}')
                    rejected.append({
                        'journal_id': str(journal_id),
                        'expected_source_type': expected_source_type,
                        'error': message,
                    })
                cur.execute(f'release savepoint protected_{index}')
            cur.execute('reset role')
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    if scalar('select status from erp.journal_entries where id=%s::uuid', (str(pool_journal),)) != 'POSTED':
        raise RuntimeError('direct service_role reversal changed protected pool journal')
    if scalar('select status from erp.journal_entries where id=%s::uuid', (str(payroll_journal),)) != 'POSTED':
        raise RuntimeError('direct service_role reversal changed protected payroll accrual')

    owning_cancel = cancel_pool(pool_id)

    unprotected_id = one(
        "select erp.post_journal('CP3_R4_UNPROTECTED_COMPAT',gen_random_uuid(),current_date,%s,%s::jsonb)",
        (
            'CP3 R4 generic reversal compatibility',
            json.dumps([
                {'mapping_key': 'WIP', 'debit': 1, 'credit': 0, 'description': 'compat debit'},
                {'mapping_key': 'LABOR_COST', 'debit': 0, 'credit': 1, 'description': 'compat credit'},
            ]),
        ),
    )
    unprotected_reversal = one(
        'select erp.reverse_journal(%s::uuid,%s)',
        (str(unprotected_id), 'CP3 R4 unprotected compatibility'),
    )
    if scalar('select status from erp.journal_entries where id=%s::uuid', (str(unprotected_id),)) != 'REVERSED':
        raise RuntimeError('unprotected generic reverse_journal compatibility broke')

    acl = one("""
      select jsonb_build_object(
        'public',exists(
          select 1
          from pg_proc p join pg_namespace n on n.oid=p.pronamespace
          cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
          where n.nspname='erp' and p.proname='_reverse_journal_internal'
            and pg_get_function_identity_arguments(p.oid)='p_journal_entry_id uuid, p_reason text'
            and a.grantee=0 and a.privilege_type='EXECUTE'
        ),
        'anon',has_function_privilege('anon','erp._reverse_journal_internal(uuid,text)','EXECUTE'),
        'authenticated',has_function_privilege('authenticated','erp._reverse_journal_internal(uuid,text)','EXECUTE'),
        'service_role',has_function_privilege('service_role','erp._reverse_journal_internal(uuid,text)','EXECUTE')
      )
    """)
    if any(acl.values()):
        raise RuntimeError(f'private reversal primitive is exposed: {acl}')

    # Owning payroll lifecycle must still reverse the protected accrual internally.
    one("select erp.post_payroll_payment('a6000000-0000-0000-0000-000000000001'::uuid)")
    one("select erp.reverse_paid_payroll('a6000000-0000-0000-0000-000000000001'::uuid,%s)", ('CP3 R4 owning paid reversal',))
    one("select erp.cancel_unpaid_payroll('a6000000-0000-0000-0000-000000000021'::uuid,%s)", ('CP3 R4 owning unpaid cancellation',))
    if scalar("select status from erp.payroll_settlements where id='a6000000-0000-0000-0000-000000000001'::uuid") != 'REVERSED':
        raise RuntimeError('owning paid reversal did not finish')
    if scalar("select status from erp.payroll_settlements where id='a6000000-0000-0000-0000-000000000021'::uuid") != 'REVERSED':
        raise RuntimeError('owning unpaid cancellation did not finish')

    return {
        'label': 'protected-journal-service-role-and-owning-lifecycle',
        'active_pool': active,
        'service_role_public_denials': rejected,
        'owning_pool_cancel': owning_cancel,
        'unprotected_generic_reversal_id': str(unprotected_reversal),
        'private_primitive_acl': acl,
        'owning_paid_reversal': True,
        'owning_unpaid_cancellation': True,
    }


def main():
    results = []

    # 1. Activation wins, then exact-period payroll approval waits and is rejected.
    results.append(activation_first(
        'activate-vs-approve-payroll', '2026-02-01',
        'select erp.approve_payroll(%s::uuid)',
        ('a6000000-0000-0000-0000-000000000021',),
        'Cancel the ACTIVE pool first before approving this payroll',
    ))

    # 2. Approval wins, then activation waits and rejects the stale DRAFT manifest.
    def approve_first(cur, result):
        cur.execute("select erp._cp3_lock_business_period('2026-02-01'::date,'2026-02-01'::date)")
        cur.execute("select erp.approve_payroll('a6000000-0000-0000-0000-000000000021'::uuid)")
        result['payroll_status_inside_tx'] = cur.execute(
            "select status from erp.payroll_settlements where id='a6000000-0000-0000-0000-000000000021'::uuid"
        ).fetchone()[0]
    results.append(source_first_stales('approve-payroll-first-vs-activate', '2026-02-01', approve_first))

    # 3. Activation owns contractor lock; overlapping policy update waits and is rejected.
    policy_id = scalar("""
      select id from erp.contractor_hpp_policy_versions
      where contractor_id='a1000000-0000-0000-0000-000000000001'::uuid
        and '2026-03-01'::date between effective_from and coalesce(effective_to,'infinity'::date)
    """)
    policy_payload = {
        'contractor_id': 'a1000000-0000-0000-0000-000000000001',
        'effective_from': '2026-03-01',
        'is_special': False,
        'attendance_required': True,
        'reason': 'CP3 R4 policy race',
    }
    results.append(activation_first(
        'activate-vs-policy-update', '2026-03-01',
        'select erp.set_contractor_hpp_policy_v1(%s::jsonb,%s::uuid,%s::uuid)',
        (json.dumps(policy_payload), str(uuid.uuid4()), str(policy_id)),
        'overlaps an ACTIVE attendance HPP pool',
    ))

    # 4. Policy update wins contractor lock; activation waits and rejects stale input.
    def policy_first(cur, result):
        cur.execute(
            "select pg_advisory_xact_lock(hashtextextended('CONTRACTOR_HPP_POLICY|'||%s::uuid::text,0))",
            ('a1000000-0000-0000-0000-000000000001',),
        )
        cur.execute(
            'select erp.set_contractor_hpp_policy_v1(%s::jsonb,%s::uuid,%s::uuid)',
            (json.dumps(policy_payload), str(uuid.uuid4()), str(policy_id)),
        )
        result['value'] = cur.fetchone()[0]
    results.append(source_first_stales('policy-update-first-vs-activate', '2026-03-01', policy_first))

    # 5. Activation wins; reverse_work_completion waits and rejects unreversed terminal dependency.
    results.append(activation_first(
        'activate-vs-reverse-work-completion', '2026-04-01',
        'select erp.reverse_work_completion(%s::uuid,%s)',
        ('a5000000-0000-0000-0000-000000000040', 'CP3 R4 activation-first reverse work'),
        'reverse_sewing_terminal_v1() terlebih dahulu',
    ))

    # 6. Reverse call owns date lock first but still fails closed; activation waits then succeeds.
    results.append(reverse_work_rejects_first_then_activation('2026-04-01', 'a5000000-0000-0000-0000-000000000040'))

    # 7. Correct owning reversal chain wins; activation waits and rejects stale DRAFT.
    event_d = scalar("""
      select id from erp.sewing_terminal_events
      where source_work_completion_id='a5000000-0000-0000-0000-000000000040'::uuid
        and event_kind='SELESAI_DIJAHIT'
    """)
    event_d_version = scalar('select row_version from erp.sewing_terminal_events where id=%s::uuid', (str(event_d),))
    def owning_work_reverse_first(cur, result):
        cur.execute("select erp._cp3_lock_business_date('2026-04-01'::date)")
        cur.execute(
            'select erp.reverse_sewing_terminal_v1(%s::uuid,%s,%s::uuid,%s)',
            (str(event_d), 'CP3 R4 owning source-first terminal reverse', str(uuid.uuid4()), event_d_version),
        )
        result['terminal_reversal'] = cur.fetchone()[0]
        cur.execute(
            "select erp.reverse_work_completion('a5000000-0000-0000-0000-000000000040'::uuid,%s)",
            ('CP3 R4 source-first work reversal',),
        )
        result['work_status_inside_tx'] = cur.execute(
            "select status from erp.work_completion_events where id='a5000000-0000-0000-0000-000000000040'::uuid"
        ).fetchone()[0]
    results.append(source_first_stales('owning-reverse-work-first-vs-activate', '2026-04-01', owning_work_reverse_first))

    # 8. Regression: activation wins against a late/backdated terminal record.
    results.append(activation_first(
        'activate-vs-record-sewing', '2026-01-01',
        'select erp.record_sewing_terminal_v1(%s::jsonb,%s::uuid)',
        (json.dumps({'work_completion_id': 'a5000000-0000-0000-0000-000000000011', 'qty_pcs': 10,
                     'reason': 'CP3 R4 activation-first late record'}), str(uuid.uuid4())),
        'ACTIVE_ATTENDANCE_HPP_PERIOD_LOCKED',
    ))

    # 9. Regression: record wins; activation waits and rejects stale DRAFT.
    def record_first(cur, result):
        cur.execute("select erp._cp3_lock_business_date('2026-01-01'::date)")
        cur.execute(
            'select erp.record_sewing_terminal_v1(%s::jsonb,%s::uuid)',
            (json.dumps({'work_completion_id': 'a5000000-0000-0000-0000-000000000012', 'qty_pcs': 5,
                         'reason': 'CP3 R4 record-first'}), str(uuid.uuid4())),
        )
        result['value'] = cur.fetchone()[0]
    results.append(source_first_stales('record-sewing-first-vs-activate', '2026-01-01', record_first))

    # 10. Regression: activation wins against terminal reversal.
    event_a = scalar("""
      select id from erp.sewing_terminal_events
      where source_work_completion_id='a5000000-0000-0000-0000-000000000001'::uuid
        and event_kind='SELESAI_DIJAHIT'
    """)
    event_a_version = scalar('select row_version from erp.sewing_terminal_events where id=%s::uuid', (str(event_a),))
    results.append(activation_first(
        'activate-vs-reverse-sewing', '2026-01-01',
        'select erp.reverse_sewing_terminal_v1(%s::uuid,%s,%s::uuid,%s)',
        (str(event_a), 'CP3 R4 activation-first reverse sewing', str(uuid.uuid4()), event_a_version),
        'consumed by an ACTIVE attendance HPP pool',
    ))

    # 11. Regression: terminal reversal wins; activation waits and rejects stale DRAFT.
    def reverse_sewing_first(cur, result):
        cur.execute("select erp._cp3_lock_business_date('2026-01-01'::date)")
        cur.execute(
            'select erp.reverse_sewing_terminal_v1(%s::uuid,%s,%s::uuid,%s)',
            (str(event_a), 'CP3 R4 reverse-sewing-first', str(uuid.uuid4()), event_a_version),
        )
        result['value'] = cur.fetchone()[0]
    results.append(source_first_stales('reverse-sewing-first-vs-activate', '2026-01-01', reverse_sewing_first))

    # 12. Regression: activation wins against payroll cancellation.
    results.append(activation_first(
        'activate-vs-cancel-payroll', '2026-01-01',
        'select erp.cancel_unpaid_payroll(%s::uuid,%s)',
        ('a6000000-0000-0000-0000-000000000002', 'CP3 R4 activation-first payroll cancel'),
        'PAYROLL_CONSUMED_BY_ACTIVE_HPP_POOL',
    ))

    # 13. Regression: payroll cancellation wins; activation waits and rejects stale DRAFT.
    def cancel_payroll_first(cur, result):
        cur.execute("select erp._cp3_lock_business_period('2026-01-01'::date,'2026-01-01'::date)")
        cur.execute(
            "select erp.cancel_unpaid_payroll('a6000000-0000-0000-0000-000000000002'::uuid,%s)",
            ('CP3 R4 cancel-first payroll',),
        )
        result['payroll_status_inside_tx'] = cur.execute(
            "select status from erp.payroll_settlements where id='a6000000-0000-0000-0000-000000000002'::uuid"
        ).fetchone()[0]
    results.append(source_first_stales('cancel-payroll-first-vs-activate', '2026-01-01', cancel_payroll_first))

    # 14. Security/compatibility and owning reversal proof.
    security = service_role_reversal_proof()
    results.append(security)

    report = {
        'status': 'PASS',
        'mode': 'REAL_TWO_CONNECTION_FULL_SCHEMA',
        'postgres_connections_per_race': 2,
        'business_timezone': 'Asia/Jakarta',
        'scenario_count': len(results),
        'scenarios': results,
        'assertions': {
            'activate_vs_approve_both_orders': True,
            'activate_vs_policy_both_orders': True,
            'activate_vs_reverse_work_both_orders': True,
            'owning_terminal_then_work_source_first': True,
            'activate_vs_record_regression': True,
            'activate_vs_reverse_sewing_regression': True,
            'activate_vs_cancel_payroll_regression': True,
            'direct_service_role_protected_reversal_rejected': True,
            'unprotected_generic_reversal_compatible': True,
            'owning_pool_cancel_succeeds': True,
            'owning_paid_and_unpaid_payroll_reversal_succeeds': True,
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
