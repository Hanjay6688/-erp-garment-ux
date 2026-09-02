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


def pool_evidence(pool_id):
    evidence = one(
        """
        select jsonb_build_object(
          'pool_status',p.status,
          'row_version',p.row_version,
          'post_journal_entry_id',p.post_journal_entry_id,
          'post_journal_status',post_je.status,
          'cancellation_journal_entry_id',p.cancellation_journal_entry_id,
          'cancellation_journal_status',cancel_je.status,
          'source_rows',(select count(*) from erp.attendance_hpp_pool_sources s where s.pool_id=p.id),
          'allocation_rows',(select count(*) from erp.attendance_hpp_pool_allocations a where a.pool_id=p.id),
          'journal_link_rows',(select count(*) from erp.attendance_hpp_journal_line_links l where l.pool_id=p.id),
          'active_same_period_pool_count',(
            select count(*) from erp.attendance_hpp_pools other
            where other.period_start=p.period_start and other.period_end=p.period_end and other.status='ACTIVE'
          ),
          'posted_protected_pool_journal_count',(
            select count(*) from erp.journal_entries je
            where je.source_type='ATTENDANCE_HPP_POOL' and je.source_id=p.id and je.status='POSTED'
          )
        )
        from erp.attendance_hpp_pools p
        left join erp.journal_entries post_je on post_je.id=p.post_journal_entry_id
        left join erp.journal_entries cancel_je on cancel_je.id=p.cancellation_journal_entry_id
        where p.id=%s::uuid
        """,
        (str(pool_id),),
    )
    if not evidence:
        raise RuntimeError(f'pool evidence missing for {pool_id}')
    if evidence['pool_status'] == 'CANCELLED':
        residue_ok = (
            evidence['post_journal_status'] == 'REVERSED'
            and evidence['cancellation_journal_status'] == 'POSTED'
            and evidence['active_same_period_pool_count'] == 0
            and evidence['posted_protected_pool_journal_count'] == 0
        )
    elif evidence['pool_status'] == 'VOIDED':
        residue_ok = (
            evidence['post_journal_entry_id'] is None
            and evidence['cancellation_journal_entry_id'] is None
            and evidence['active_same_period_pool_count'] == 0
            and evidence['posted_protected_pool_journal_count'] == 0
        )
    else:
        residue_ok = False
    evidence['residue_status'] = 'PASS' if residue_ok else 'FAIL'
    if not residue_ok:
        raise RuntimeError(f'pool terminal residue mismatch: {evidence}')
    return evidence


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
        'first_lock': 'BUSINESS_PERIOD_THEN_MANIFEST_CONTRACTORS',
        'pool_id': str(pool_id),
        'activation': activation,
        'mutation': mutation,
        'terminal_pool_status': scalar('select status from erp.attendance_hpp_pools where id=%s::uuid', (str(pool_id),)),
        'terminal_evidence': pool_evidence(pool_id),
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
        'first_lock': 'SOURCE_LIFECYCLE_LOCK_SET',
        'pool_id': str(pool_id),
        'source_mutation': source_result,
        'activation': activation_result,
        'terminal_pool_status': scalar('select status from erp.attendance_hpp_pools where id=%s::uuid', (str(pool_id),)),
        'terminal_evidence': pool_evidence(pool_id),
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
        'first_lock': 'BUSINESS_DATE_THEN_WORK_COMPLETION',
        'pool_id': str(pool_id),
        'reverse_work': reverse_result,
        'activation': activation_result,
        'terminal_pool_status': scalar('select status from erp.attendance_hpp_pools where id=%s::uuid', (str(pool_id),)),
        'terminal_evidence': pool_evidence(pool_id),
    }


def pool_cancel_vs_record_sewing(period: str, completion_id: str):
    """Prove both real two-session orderings for pool cancellation vs source mutation."""
    first_label = 'record-sewing-lock-first-vs-pool-cancel'
    first_pool = create_pool(period)
    first_activation = one(
        'select erp.activate_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s)',
        (str(first_pool), 'CP3 R5 pool-cancel source-first proof', str(uuid.uuid4()), 1),
    )
    source_started = threading.Event()
    source_result = {}
    cancel_result = {}

    def rejecting_source_holder():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute('select erp._cp3_lock_business_date(%s::date)', (period,))
                cur.execute('savepoint before_record')
                source_started.set()
                time.sleep(HOLD_SECONDS)
                try:
                    cur.execute(
                        'select erp.record_sewing_terminal_v1(%s::jsonb,%s::uuid)',
                        (json.dumps({
                            'work_completion_id': completion_id,
                            'qty_pcs': 10,
                            'reason': 'CP3 R5 source-first pool cancellation race',
                        }), str(uuid.uuid4())),
                    )
                    source_result['unexpected_value'] = cur.fetchone()[0]
                    source_result['status'] = 'UNEXPECTED_SUCCESS'
                except Exception as exc:
                    message = str(exc)
                    source_result['error'] = message
                    source_result['status'] = (
                        'EXPECTED_REJECTION'
                        if 'ACTIVE_ATTENDANCE_HPP_PERIOD_LOCKED' in message
                        else 'WRONG_ERROR'
                    )
                    cur.execute('rollback to savepoint before_record')
                cur.execute('release savepoint before_record')
            conn.commit()
        except Exception as exc:
            conn.rollback()
            source_result['status'] = 'FAIL'
            source_result['error'] = str(exc)
            source_started.set()
        finally:
            conn.close()

    def waiting_pool_cancel():
        source_started.wait(timeout=10)
        began = time.monotonic()
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute(
                    'select erp.cancel_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s)',
                    (str(first_pool), 'CP3 R5 source-first pool cancel', str(uuid.uuid4()), 2),
                )
                cancel_result['value'] = cur.fetchone()[0]
            conn.commit()
            cancel_result['status'] = 'PASS'
        except Exception as exc:
            conn.rollback()
            cancel_result['status'] = 'FAIL'
            cancel_result['error'] = str(exc)
        finally:
            cancel_result['elapsed_seconds'] = round(time.monotonic() - began, 3)
            conn.close()

    ts = threading.Thread(target=rejecting_source_holder, daemon=True)
    tc = threading.Thread(target=waiting_pool_cancel, daemon=True)
    ts.start(); tc.start(); ts.join(timeout=25); tc.join(timeout=25)
    if ts.is_alive() or tc.is_alive():
        raise RuntimeError(f'{first_label}: thread timeout')
    if source_result.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'{first_label}: source did not fail closed: {source_result}')
    if cancel_result.get('status') != 'PASS':
        raise RuntimeError(f'{first_label}: owning pool cancellation failed: {cancel_result}')
    assert_wait(cancel_result, first_label)
    if scalar(
        "select count(*) from erp.sewing_terminal_events where source_work_completion_id=%s::uuid and event_kind='SELESAI_DIJAHIT'",
        (completion_id,),
    ) != 0:
        raise RuntimeError(f'{first_label}: rejected source mutation left a terminal event')
    first_scenario = {
        'label': first_label,
        'order': 'SOURCE_LOCK_FIRST',
        'first_lock': 'BUSINESS_DATE',
        'waited_lock': 'POOL_CANCEL_BUSINESS_PERIOD',
        'pool_id': str(first_pool),
        'activation': first_activation,
        'source_mutation': source_result,
        'pool_cancellation': cancel_result,
        'source_state': {'active_sewing_terminal_count': 0},
        'terminal_evidence': pool_evidence(first_pool),
    }

    second_label = 'pool-cancel-first-vs-record-sewing'
    second_pool = create_pool(period, correction_of=first_pool)
    second_activation = one(
        'select erp.activate_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s)',
        (str(second_pool), 'CP3 R5 pool-cancel-first proof', str(uuid.uuid4()), 1),
    )
    cancel_started = threading.Event()
    second_cancel = {}
    record_result = {}

    def pool_cancel_holder():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute(
                    'select erp.cancel_attendance_hpp_pool_v1(%s::uuid,%s,%s::uuid,%s)',
                    (str(second_pool), 'CP3 R5 cancel-first source race', str(uuid.uuid4()), 2),
                )
                second_cancel['value'] = cur.fetchone()[0]
                second_cancel['status_inside_tx'] = 'CANCELLED'
                cancel_started.set()
                time.sleep(HOLD_SECONDS)
            conn.commit()
            second_cancel['status'] = 'PASS'
        except Exception as exc:
            conn.rollback()
            second_cancel['status'] = 'FAIL'
            second_cancel['error'] = str(exc)
            cancel_started.set()
        finally:
            conn.close()

    def waiting_record():
        cancel_started.wait(timeout=10)
        began = time.monotonic()
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute(
                    'select erp.record_sewing_terminal_v1(%s::jsonb,%s::uuid)',
                    (json.dumps({
                        'work_completion_id': completion_id,
                        'qty_pcs': 10,
                        'reason': 'CP3 R5 record after owning pool cancellation',
                    }), str(uuid.uuid4())),
                )
                record_result['value'] = cur.fetchone()[0]
            conn.commit()
            record_result['status'] = 'PASS'
        except Exception as exc:
            conn.rollback()
            record_result['status'] = 'FAIL'
            record_result['error'] = str(exc)
        finally:
            record_result['elapsed_seconds'] = round(time.monotonic() - began, 3)
            conn.close()

    tc = threading.Thread(target=pool_cancel_holder, daemon=True)
    tr = threading.Thread(target=waiting_record, daemon=True)
    tc.start(); tr.start(); tc.join(timeout=25); tr.join(timeout=25)
    if tc.is_alive() or tr.is_alive():
        raise RuntimeError(f'{second_label}: thread timeout')
    if second_cancel.get('status') != 'PASS':
        raise RuntimeError(f'{second_label}: pool cancellation failed: {second_cancel}')
    if record_result.get('status') != 'PASS':
        raise RuntimeError(f'{second_label}: source mutation did not succeed after cancellation: {record_result}')
    assert_wait(record_result, second_label)
    terminal_count = scalar(
        "select count(*) from erp.sewing_terminal_events where source_work_completion_id=%s::uuid and event_kind='SELESAI_DIJAHIT'",
        (completion_id,),
    )
    if terminal_count != 1:
        raise RuntimeError(f'{second_label}: expected one committed terminal event, found {terminal_count}')
    second_scenario = {
        'label': second_label,
        'order': 'POOL_CANCEL_FIRST',
        'first_lock': 'POOL_ROW_THEN_BUSINESS_PERIOD',
        'waited_lock': 'SOURCE_BUSINESS_DATE',
        'pool_id': str(second_pool),
        'activation': second_activation,
        'pool_cancellation': second_cancel,
        'source_mutation': record_result,
        'source_state': {'active_sewing_terminal_count': terminal_count},
        'terminal_evidence': pool_evidence(second_pool),
    }
    return [first_scenario, second_scenario]


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
    protected = (
        (pool_journal, 'ATTENDANCE_HPP_POOL'),
        (payroll_journal, 'PAYROLL_ATTENDANCE_ACCRUAL'),
    )
    role_denials = {}
    for role in ('anon', 'authenticated', 'service_role'):
        rejected = []
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute(f'set role {role}')
                for index, (journal_id, expected_source_type) in enumerate(protected, start=1):
                    cur.execute(f'savepoint protected_{index}')
                    try:
                        cur.execute(
                            'select erp.reverse_journal(%s::uuid,%s)',
                            (str(journal_id), f'CP3 R5 direct {role} protected reversal'),
                        )
                        raise RuntimeError(f'{role} unexpectedly reversed protected journal {journal_id}')
                    except psycopg.Error as exc:
                        message = str(exc)
                        cur.execute(f'rollback to savepoint protected_{index}')
                        expected_boundary_denial = (
                            'permission denied for schema erp' in message
                            or 'permission denied for function reverse_journal' in message
                        )
                        if not expected_boundary_denial:
                            raise RuntimeError(f'wrong {role} public-boundary denial: {message}')
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
        role_denials[role] = rejected

    if scalar('select status from erp.journal_entries where id=%s::uuid', (str(pool_journal),)) != 'POSTED':
        raise RuntimeError('direct external-role reversal changed protected pool journal')
    if scalar('select status from erp.journal_entries where id=%s::uuid', (str(payroll_journal),)) != 'POSTED':
        raise RuntimeError('direct external-role reversal changed protected payroll accrual')

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
          where n.nspname='erp' and p.proname='_cp3_r4_reverse_journal_internal'
            and pg_get_function_identity_arguments(p.oid)='p_journal_entry_id uuid, p_reason text'
            and a.grantee=0 and a.privilege_type='EXECUTE'
        ),
        'anon',has_function_privilege('anon','erp._cp3_r4_reverse_journal_internal(uuid,text)','EXECUTE'),
        'authenticated',has_function_privilege('authenticated','erp._cp3_r4_reverse_journal_internal(uuid,text)','EXECUTE'),
        'service_role',has_function_privilege('service_role','erp._cp3_r4_reverse_journal_internal(uuid,text)','EXECUTE')
      )
    """)
    if any(acl.values()):
        raise RuntimeError(f'private reversal primitive is exposed: {acl}')

    generic_access = one("""
      select jsonb_build_object(
        'public',jsonb_build_object(
          'schema_usage',exists(
            select 1 from pg_namespace n
            cross join lateral aclexplode(coalesce(n.nspacl,acldefault('n',n.nspowner))) a
            where n.nspname='erp' and a.grantee=0 and a.privilege_type='USAGE'
          ),
          'function_execute',exists(
            select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
            cross join lateral aclexplode(coalesce(p.proacl,acldefault('f',p.proowner))) a
            where n.nspname='erp' and p.proname='reverse_journal'
              and pg_get_function_identity_arguments(p.oid)='p_journal_entry_id uuid, p_reason text'
              and a.grantee=0 and a.privilege_type='EXECUTE'
          )
        ),
        'anon',jsonb_build_object(
          'schema_usage',has_schema_privilege('anon','erp','USAGE'),
          'function_execute',has_function_privilege('anon','erp.reverse_journal(uuid,text)','EXECUTE')
        ),
        'authenticated',jsonb_build_object(
          'schema_usage',has_schema_privilege('authenticated','erp','USAGE'),
          'function_execute',has_function_privilege('authenticated','erp.reverse_journal(uuid,text)','EXECUTE')
        ),
        'service_role',jsonb_build_object(
          'schema_usage',has_schema_privilege('service_role','erp','USAGE'),
          'function_execute',has_function_privilege('service_role','erp.reverse_journal(uuid,text)','EXECUTE')
        )
      )
    """)
    for role, privileges in generic_access.items():
        privileges['callable'] = bool(privileges['schema_usage'] and privileges['function_execute'])
    if any(privileges['callable'] for privileges in generic_access.values()):
        raise RuntimeError(f'generic reverse_journal unexpectedly callable at CP3 boundary: {generic_access}')

    # Owning payroll lifecycle must still reverse the protected accrual internally.
    one("select erp.post_payroll_payment('a6000000-0000-0000-0000-000000000001'::uuid)")
    one("select erp.reverse_paid_payroll('a6000000-0000-0000-0000-000000000001'::uuid,%s)", ('CP3 R4 owning paid reversal',))
    one("select erp.cancel_unpaid_payroll('a6000000-0000-0000-0000-000000000021'::uuid,%s)", ('CP3 R4 owning unpaid cancellation',))
    if scalar("select status from erp.payroll_settlements where id='a6000000-0000-0000-0000-000000000001'::uuid") != 'REVERSED':
        raise RuntimeError('owning paid reversal did not finish')
    if scalar("select status from erp.payroll_settlements where id='a6000000-0000-0000-0000-000000000021'::uuid") != 'REVERSED':
        raise RuntimeError('owning unpaid cancellation did not finish')

    return {
        'label': 'protected-journal-role-matrix-and-owning-lifecycle',
        'active_pool': active,
        'direct_role_public_denials': role_denials,
        'service_role_public_denials': role_denials['service_role'],
        'owning_pool_cancel': owning_cancel,
        'terminal_evidence': pool_evidence(pool_id),
        'unprotected_generic_reversal_id': str(unprotected_reversal),
        'private_primitive_acl': acl,
        'generic_reverse_effective_access': generic_access,
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

    # 9-10. Pool cancellation and a source mutation race in both real orderings.
    results.extend(pool_cancel_vs_record_sewing(
        '2026-01-01',
        'a5000000-0000-0000-0000-000000000011',
    ))

    # 11. Regression: record wins; activation waits and rejects stale DRAFT.
    def record_first(cur, result):
        cur.execute("select erp._cp3_lock_business_date('2026-01-01'::date)")
        cur.execute(
            'select erp.record_sewing_terminal_v1(%s::jsonb,%s::uuid)',
            (json.dumps({'work_completion_id': 'a5000000-0000-0000-0000-000000000012', 'qty_pcs': 5,
                         'reason': 'CP3 R4 record-first'}), str(uuid.uuid4())),
        )
        result['value'] = cur.fetchone()[0]
    results.append(source_first_stales('record-sewing-first-vs-activate', '2026-01-01', record_first))

    # 12. Regression: activation wins against terminal reversal.
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

    # 13. Regression: terminal reversal wins; activation waits and rejects stale DRAFT.
    def reverse_sewing_first(cur, result):
        cur.execute("select erp._cp3_lock_business_date('2026-01-01'::date)")
        cur.execute(
            'select erp.reverse_sewing_terminal_v1(%s::uuid,%s,%s::uuid,%s)',
            (str(event_a), 'CP3 R4 reverse-sewing-first', str(uuid.uuid4()), event_a_version),
        )
        result['value'] = cur.fetchone()[0]
    results.append(source_first_stales('reverse-sewing-first-vs-activate', '2026-01-01', reverse_sewing_first))

    # 14. Regression: activation wins against payroll cancellation.
    results.append(activation_first(
        'activate-vs-cancel-payroll', '2026-01-01',
        'select erp.cancel_unpaid_payroll(%s::uuid,%s)',
        ('a6000000-0000-0000-0000-000000000002', 'CP3 R4 activation-first payroll cancel'),
        'PAYROLL_CONSUMED_BY_ACTIVE_HPP_POOL',
    ))

    # 15. Regression: payroll cancellation wins; activation waits and rejects stale DRAFT.
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

    # 16. Security/compatibility and owning reversal proof.
    security = service_role_reversal_proof()
    results.append(security)

    for scenario in results:
        terminal_evidence = scenario.get('terminal_evidence')
        if terminal_evidence and terminal_evidence.get('residue_status') != 'PASS':
            raise RuntimeError(f"{scenario['label']}: terminal evidence is not PASS: {terminal_evidence}")

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
            'pool_cancel_vs_source_both_orders': True,
            'activate_vs_reverse_sewing_regression': True,
            'activate_vs_cancel_payroll_regression': True,
            'direct_anon_authenticated_service_role_reversal_rejected': True,
            'direct_service_role_protected_reversal_rejected': True,
            'unprotected_generic_reversal_compatible': True,
            'owning_pool_cancel_succeeds': True,
            'owning_paid_and_unpaid_payroll_reversal_succeeds': True,
            'shared_lock_wait_observed': True,
            'per_scenario_terminal_evidence': True,
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
