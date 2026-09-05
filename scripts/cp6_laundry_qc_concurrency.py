#!/usr/bin/env python3
"""Real two-connection races for CP6 Laundry -> QC -> FG reliability."""
from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Callable

import psycopg


PGURL = os.environ.get('CP6_RACE_PGURL', 'postgresql://postgres:postgres@127.0.0.1:54322/cp6_race')
REPORT = Path(os.environ.get('CP6_LAUNDRY_QC_RACE_REPORT', 'cp6-laundry-qc-concurrency.json'))
HOLD_SECONDS = 1.0
WAIT_FLOOR_SECONDS = 0.5

OPERATOR_AUTH = 'c8c00000-0000-4000-8000-000000000101'
OPERATOR_APP = 'c8c00000-0000-4000-8000-000000000001'
GROUP = 'c8c40000-0000-4000-8000-000000000003'
BATCH = 'c8c40000-0000-4000-8000-000000000008'
SIZE = 'c8c10000-0000-4000-8000-000000000002'
VENDOR = 'c8c20000-0000-4000-8000-000000000002'
PROCESS = 'c8c20000-0000-4000-8000-000000000003'
LOCATION = 'c8c20000-0000-4000-8000-000000000001'
PRODUCT = 'c8c10000-0000-4000-8000-000000000004'
PO = 'c8c40000-0000-4000-8000-000000000001'
FIRST_ACCRUAL_PO = 'c8d40000-0000-4000-8000-000000000001'
F02_PO = 'c8e40000-0000-4000-8000-000000000001'
F02_GROUP = 'c8e40000-0000-4000-8000-000000000003'
F02_BATCH = 'c8e40000-0000-4000-8000-000000000008'
VENDOR_INVOICE = 'c8c70000-0000-4000-8000-000000000001'
VENDOR_INVOICE_ITEM = 'c8c70000-0000-4000-8000-000000000002'
VENDOR_INVOICE_QC = 'c8c70000-0000-4000-8000-000000000003'
VENDOR_INVOICE_QC_ITEM = 'c8c70000-0000-4000-8000-000000000004'
VENDOR_INVOICE_QC_AFTER = 'c8c70000-0000-4000-8000-000000000005'
VENDOR_INVOICE_QC_AFTER_ITEM = 'c8c70000-0000-4000-8000-000000000006'
VENDOR_INVOICE_REPLACED = 'c8c70000-0000-4000-8000-000000000007'
VENDOR_INVOICE_REPLACED_ITEM = 'c8c70000-0000-4000-8000-000000000008'
VENDOR_INVOICE_REPLACEMENT = 'c8c70000-0000-4000-8000-000000000009'
VENDOR_INVOICE_REPLACEMENT_ITEM = 'c8c70000-0000-4000-8000-000000000010'

REQUESTS = {
    'delivery_winner': 'c8c60000-0000-4000-8000-000000000001',
    'delivery_loser': 'c8c60000-0000-4000-8000-000000000002',
    'receipt_winner': 'c8c60000-0000-4000-8000-000000000003',
    'receipt_loser': 'c8c60000-0000-4000-8000-000000000004',
    'qc_winner': 'c8c60000-0000-4000-8000-000000000005',
    'qc_loser': 'c8c60000-0000-4000-8000-000000000006',
    'qc_reverse': 'c8c60000-0000-4000-8000-000000000007',
    'qc_repost_winner': 'c8c60000-0000-4000-8000-000000000008',
    'receipt_reverse_loser': 'c8c60000-0000-4000-8000-000000000009',
    'invoice_receipt_reverse_loser': 'c8c60000-0000-4000-8000-000000000010',
    'invoice_qc_post': 'c8c60000-0000-4000-8000-000000000011',
    'invoice_qc_reverse': 'c8c60000-0000-4000-8000-000000000012',
    'invoice_reversal_qc_post': 'c8c60000-0000-4000-8000-000000000013',
    'invoice_reversal_qc_reverse': 'c8c60000-0000-4000-8000-000000000014',
    'qc_before_invoice_post': 'c8c60000-0000-4000-8000-000000000015',
    'qc_before_invoice_reverse': 'c8c60000-0000-4000-8000-000000000016',
    'qc_before_invoice_reversal_post': 'c8c60000-0000-4000-8000-000000000017',
    'qc_before_invoice_reversal_reverse': 'c8c60000-0000-4000-8000-000000000018',
    'failed_wash_winner': 'c8c60000-0000-4000-8000-000000000019',
    'failed_wash_receipt_loser': 'c8c60000-0000-4000-8000-000000000020',
    'failed_wash_reverse': 'c8c60000-0000-4000-8000-000000000021',
    'f02_first_delivery': 'c8e60000-0000-4000-8000-000000000001',
    'f02_physical_return': 'c8e60000-0000-4000-8000-000000000002',
    'f02_backdated_rejected': 'c8e60000-0000-4000-8000-000000000003',
    'f02_later_delivery': 'c8e60000-0000-4000-8000-000000000004',
}


def connect():
    return psycopg.connect(PGURL, autocommit=False)


def set_operator_claims(cur):
    """Attach the real operator identity while retaining the backend DB role."""
    claims = json.dumps({'sub': OPERATOR_AUTH, 'role': 'authenticated'})
    cur.execute("select set_config('request.jwt.claims',%s,true)", (claims,))


def set_operator_context(cur):
    set_operator_claims(cur)
    cur.execute('set local role authenticated')


def scalar(query: str, params=()):
    with connect() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None


def action(cur, action_name: str, payload: dict[str, Any], request_id: str, expected_version: int):
    cur.execute(
        'select public.erp_save_laundry_qc_action_v1(%s,%s::jsonb,%s::uuid,%s)',
        (action_name, json.dumps(payload), request_id, expected_version),
    )
    return cur.fetchone()[0]


def single_action(
    action_name: str,
    payload: dict[str, Any],
    request_id: str,
    expected_version: int,
):
    with connect() as conn, conn.cursor() as cur:
        set_operator_context(cur)
        response = action(cur, action_name, payload, request_id, expected_version)
        conn.commit()
        return response


def run_race(
    name: str,
    action_name: str,
    payload: dict[str, Any],
    expected_version: int,
    winner_request: str,
    loser_request: str,
    allowed_loser_errors: tuple[str, ...],
) -> dict[str, Any]:
    """Hold a completed winner action before commit, using runtime lock order.

    The winner action itself establishes the canonical runtime lock order.  A
    fixture must never pre-lock a business row before invoking the facade:
    doing so would manufacture a row -> advisory order opposite to the
    production advisory -> row order and turn a valid serialization proof into
    a test-induced deadlock.
    """
    started = threading.Event()
    winner: dict[str, Any] = {}
    loser: dict[str, Any] = {}

    def holder():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_context(cur)
                winner['response'] = action(
                    cur, action_name, payload, winner_request, expected_version,
                )
                started.set()
                time.sleep(HOLD_SECONDS)
            conn.commit()
            winner['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - emitted into CI evidence
            conn.rollback()
            winner['status'] = 'FAIL'
            winner['error'] = str(exc)
            started.set()
        finally:
            conn.close()

    def waiter():
        started.wait(timeout=10)
        began = time.monotonic()
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_context(cur)
                loser['unexpected_response'] = action(
                    cur, action_name, payload, loser_request, expected_version,
                )
            conn.commit()
            loser['status'] = 'UNEXPECTED_SUCCESS'
        except Exception as exc:  # pragma: no cover - expected loser path
            conn.rollback()
            loser['error'] = str(exc)
            loser['status'] = (
                'EXPECTED_REJECTION'
                if any(token in str(exc) for token in allowed_loser_errors)
                else 'WRONG_ERROR'
            )
        finally:
            loser['elapsed_seconds'] = round(time.monotonic() - began, 3)
            conn.close()

    first = threading.Thread(target=holder, daemon=True)
    second = threading.Thread(target=waiter, daemon=True)
    first.start()
    second.start()
    first.join(timeout=20)
    second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError(f'{name} race thread timeout')
    if winner.get('status') != 'PASS' or loser.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'{name} race mismatch: winner={winner}, loser={loser}')
    if loser.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'{name} did not observe a real serialization wait: {loser}')
    return {'winner': winner, 'loser': loser}


def run_first_accrual_creation_race() -> dict[str, Any]:
    """Prove two first callers create one state row and one money delta."""
    first_finished = threading.Event()
    first: dict[str, Any] = {}
    second: dict[str, Any] = {}

    def holder():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_claims(cur)
                cur.execute(
                    'select erp.sync_laundry_accrual(%s::uuid,%s::date)',
                    (FIRST_ACCRUAL_PO, '2026-09-04'),
                )
                first_finished.set()
                time.sleep(HOLD_SECONDS)
            conn.commit()
            first['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - emitted into CI evidence
            conn.rollback()
            first['status'] = 'FAIL'
            first['error'] = str(exc)
            first_finished.set()
        finally:
            conn.close()

    def waiter():
        first_finished.wait(timeout=10)
        began = time.monotonic()
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_claims(cur)
                cur.execute(
                    'select erp.sync_laundry_accrual(%s::uuid,%s::date)',
                    (FIRST_ACCRUAL_PO, '2026-09-04'),
                )
            conn.commit()
            second['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - emitted into CI evidence
            conn.rollback()
            second['status'] = 'FAIL'
            second['error'] = str(exc)
        finally:
            second['elapsed_seconds'] = round(time.monotonic() - began, 3)
            conn.close()

    one = threading.Thread(target=holder, daemon=True)
    two = threading.Thread(target=waiter, daemon=True)
    one.start()
    two.start()
    one.join(timeout=20)
    two.join(timeout=20)
    if one.is_alive() or two.is_alive():
        raise RuntimeError('FIRST_ACCRUAL_CREATION race thread timeout')
    if first.get('status') != 'PASS' or second.get('status') != 'PASS':
        raise RuntimeError(f'First accrual race mismatch: first={first}, second={second}')
    if second.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'Second first-accrual caller did not wait for the PO_HPP fence: {second}')
    return {'first': first, 'second': second}


def run_f02_physical_prefix_proof() -> dict[str, Any]:
    """Reject redispatch before return time and accept it after return time."""
    group_version = int(scalar(
        'select row_version from erp.cutting_groups where id=%s::uuid', (F02_GROUP,),
    ))
    first_delivery = single_action(
        'POST_DELIVERY',
        {
            'distribution_batch_id': F02_BATCH,
            'vendor_id': VENDOR,
            'wash_process_id': PROCESS,
            'target_dyeing_color': 'NAVY',
            'physical_at': '2026-09-01T11:00:00Z',
            'reason': 'CP6 F02 first physical dispatch',
            'notes': 'Immutable day-one custody handoff',
            'lines': [{'size_id': SIZE, 'qty_sent_pcs': 10}],
        },
        REQUESTS['f02_first_delivery'],
        group_version,
    )
    first_delivery_id = str(first_delivery['delivery_id'])
    first_delivery_size_line = str(scalar(
        'select x.id from erp.laundry_delivery_batch_size_lines x '
        'join erp.laundry_delivery_lines l on l.id=x.delivery_line_id '
        'where l.delivery_id=%s::uuid',
        (first_delivery_id,),
    ))
    returned = single_action(
        'POST_FAILED_WASH',
        {
            'delivery_id': first_delivery_id,
            'wash_process_id': PROCESS,
            'custody_outcome': 'RETURN_UNPROCESSED',
            'physical_at': '2026-09-03T11:00:00Z',
            'reason': 'CP6 F02 physical return from vendor',
            'lines': [{
                'delivery_batch_size_line_id': first_delivery_size_line,
                'qty_attempted_pcs': 10,
            }],
        },
        REQUESTS['f02_physical_return'],
        int(first_delivery['row_version']),
    )
    if returned.get('delivery_status') != 'REVERSED':
        raise RuntimeError(f'F02 return did not reverse original custody: {returned}')

    group_version = int(scalar(
        'select row_version from erp.cutting_groups where id=%s::uuid', (F02_GROUP,),
    ))
    backdated_payload = {
        'distribution_batch_id': F02_BATCH,
        'vendor_id': VENDOR,
        'wash_process_id': PROCESS,
        'target_dyeing_color': 'NAVY',
        'physical_at': '2026-09-02T11:00:00Z',
        'reason': 'CP6 F02 forbidden backdated redispatch',
        'notes': 'Must not precede the linked day-three return',
        'lines': [{'size_id': SIZE, 'qty_sent_pcs': 10}],
    }
    rejection_errors: list[str] = []
    for _ in range(2):
        conn = connect()
        try:
            with conn.cursor() as cur:
                set_operator_context(cur)
                action(
                    cur, 'POST_DELIVERY', backdated_payload,
                    REQUESTS['f02_backdated_rejected'], group_version,
                )
            conn.commit()
            raise RuntimeError('F02 backdated redispatch unexpectedly committed')
        except psycopg.Error as exc:
            conn.rollback()
            if 'precedes sufficient linked physical return' not in str(exc):
                raise RuntimeError(f'F02 backdated redispatch returned wrong error: {exc}') from exc
            rejection_errors.append(str(exc).splitlines()[0])
        finally:
            conn.close()

    later_payload = dict(backdated_payload)
    later_payload.update({
        'physical_at': '2026-09-04T11:00:00Z',
        'reason': 'CP6 F02 lawful post-return redispatch',
        'notes': 'New custody starts after the immutable return',
    })
    later_delivery = single_action(
        'POST_DELIVERY', later_payload, REQUESTS['f02_later_delivery'], group_version,
    )
    timeline = scalar(
        """
        select jsonb_build_object(
          'delivery_rows',(select count(*) from erp.laundry_deliveries
            where po_id=%s::uuid),
          'active_delivery_rows',(select count(*) from erp.laundry_deliveries
            where po_id=%s::uuid and status<>'REVERSED'),
          'failed_wash_attempt_rows',(select count(*)
            from erp.laundry_failed_wash_attempts where delivery_id=%s::uuid),
          'linked_return_rows',(select count(*)
            from erp.laundry_failed_wash_attempts a
            join erp.wip_stage_events rv on rv.id=a.return_wip_event_id
            where a.delivery_id=%s::uuid
              and rv.source_type='CP6_LAUNDRY_DELIVERY_WIP_REVERSAL'
              and rv.physical_at='2026-09-03 11:00:00+00'),
          'laundry_at_day_2',(select coalesce(sum(case
              when stage_to='LAUNDRY' then qty_pcs
              when stage_from='LAUNDRY' then -qty_pcs else 0 end),0)
            from erp.wip_stage_events where cutting_group_id=%s::uuid
              and physical_at<='2026-09-02 11:00:00+00'),
          'laundry_at_day_3',(select coalesce(sum(case
              when stage_to='LAUNDRY' then qty_pcs
              when stage_from='LAUNDRY' then -qty_pcs else 0 end),0)
            from erp.wip_stage_events where cutting_group_id=%s::uuid
              and physical_at<='2026-09-03 11:00:00+00'),
          'laundry_at_day_4',(select coalesce(sum(case
              when stage_to='LAUNDRY' then qty_pcs
              when stage_from='LAUNDRY' then -qty_pcs else 0 end),0)
            from erp.wip_stage_events where cutting_group_id=%s::uuid
              and physical_at<='2026-09-04 11:00:00+00'),
          'rejected_request_rows',(select count(*) from erp.idempotency_requests
            where client_request_id=%s::uuid),
          'execution_context_rows',(select count(*)
            from erp.cp6_laundry_qc_execution_context)
        )
        """,
        (
            F02_PO, F02_PO, first_delivery_id, first_delivery_id,
            F02_GROUP, F02_GROUP, F02_GROUP,
            REQUESTS['f02_backdated_rejected'],
        ),
    )
    expected = {
        'delivery_rows': 2,
        'active_delivery_rows': 1,
        'failed_wash_attempt_rows': 1,
        'linked_return_rows': 1,
        'laundry_at_day_2': 10,
        'laundry_at_day_3': 0,
        'laundry_at_day_4': 10,
        'rejected_request_rows': 0,
        'execution_context_rows': 0,
    }
    if timeline != expected:
        raise RuntimeError(
            f'F02 physical-prefix conservation mismatch: expected={expected}, actual={timeline}'
        )
    return {
        'status': 'PASS',
        'same_rejected_uuid_attempts': len(rejection_errors),
        'rejection_errors': rejection_errors,
        'later_delivery_id': str(later_delivery['delivery_id']),
        'timeline': timeline,
    }


def run_committed_action_race(
    name: str,
    winner_action: str,
    winner_payload: dict[str, Any],
    winner_request: str,
    winner_expected_version: int,
    loser_action: str,
    loser_payload: dict[str, Any],
    loser_request: str,
    loser_expected_version: int,
    allowed_loser_errors: tuple[str, ...],
) -> dict[str, Any]:
    """Hold the winner uncommitted after its action acquired business locks."""
    posted = threading.Event()
    winner: dict[str, Any] = {}
    loser: dict[str, Any] = {}

    def holder():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_context(cur)
                winner['response'] = action(
                    cur, winner_action, winner_payload, winner_request,
                    winner_expected_version,
                )
                posted.set()
                time.sleep(HOLD_SECONDS)
            conn.commit()
            winner['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - emitted into CI evidence
            conn.rollback()
            winner['status'] = 'FAIL'
            winner['error'] = str(exc)
            posted.set()
        finally:
            conn.close()

    def waiter():
        posted.wait(timeout=10)
        began = time.monotonic()
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_context(cur)
                loser['unexpected_response'] = action(
                    cur, loser_action, loser_payload, loser_request,
                    loser_expected_version,
                )
            conn.commit()
            loser['status'] = 'UNEXPECTED_SUCCESS'
        except Exception as exc:  # pragma: no cover - expected loser path
            conn.rollback()
            loser['error'] = str(exc)
            loser['status'] = (
                'EXPECTED_REJECTION'
                if any(token in str(exc) for token in allowed_loser_errors)
                else 'WRONG_ERROR'
            )
        finally:
            loser['elapsed_seconds'] = round(time.monotonic() - began, 3)
            conn.close()

    first = threading.Thread(target=holder, daemon=True)
    second = threading.Thread(target=waiter, daemon=True)
    first.start()
    second.start()
    first.join(timeout=20)
    second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError(f'{name} race thread timeout')
    if winner.get('status') != 'PASS' or loser.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'{name} race mismatch: winner={winner}, loser={loser}')
    if loser.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'{name} did not wait for the winner receipt lock: {loser}')
    return {'winner': winner, 'loser': loser}


def run_vendor_invoice_vs_receipt_reversal(
    receipt_id: str,
    receipt_version: int,
) -> dict[str, Any]:
    """Prove invoice finalization owns the receipt lock before it commits AP."""
    posted = threading.Event()
    winner: dict[str, Any] = {}
    loser: dict[str, Any] = {}

    def holder():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_claims(cur)
                cur.execute('select erp.post_vendor_invoice(%s::uuid)', (VENDOR_INVOICE,))
                posted.set()
                time.sleep(HOLD_SECONDS)
            conn.commit()
            winner['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - emitted into CI evidence
            conn.rollback()
            winner['status'] = 'FAIL'
            winner['error'] = str(exc)
            posted.set()
        finally:
            conn.close()

    def waiter():
        posted.wait(timeout=10)
        began = time.monotonic()
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_context(cur)
                loser['unexpected_response'] = action(
                    cur,
                    'REVERSE_RECEIPT',
                    {
                        'receipt_id': receipt_id,
                        'reason': 'CP6 invoice versus receipt reversal serialization',
                    },
                    REQUESTS['invoice_receipt_reverse_loser'],
                    receipt_version,
                )
            conn.commit()
            loser['status'] = 'UNEXPECTED_SUCCESS'
        except Exception as exc:  # pragma: no cover - expected loser path
            conn.rollback()
            loser['error'] = str(exc)
            loser['status'] = (
                'EXPECTED_REJECTION'
                if 'Penerimaan laundry ini sudah masuk invoice vendor' in str(exc)
                else 'WRONG_ERROR'
            )
        finally:
            loser['elapsed_seconds'] = round(time.monotonic() - began, 3)
            conn.close()

    first = threading.Thread(target=holder, daemon=True)
    second = threading.Thread(target=waiter, daemon=True)
    first.start()
    second.start()
    first.join(timeout=20)
    second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError('VENDOR_INVOICE_VS_REVERSE_RECEIPT race thread timeout')
    if winner.get('status') != 'PASS' or loser.get('status') != 'EXPECTED_REJECTION':
        raise RuntimeError(f'Vendor invoice race mismatch: winner={winner}, loser={loser}')
    if loser.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'Vendor invoice race did not retain the receipt lock: {loser}')
    return {'winner': winner, 'loser': loser}


def run_vendor_invoice_vs_final_sku(
    invoice_id: str,
    qc_payload: dict[str, Any],
    group_version: int,
) -> dict[str, Any]:
    """Prove invoice cost/AP commits before a waiting Final-SKU reads HPP."""
    posted = threading.Event()
    invoice: dict[str, Any] = {}
    qc: dict[str, Any] = {}

    def holder():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_claims(cur)
                cur.execute('select erp.post_vendor_invoice(%s::uuid)', (invoice_id,))
                posted.set()
                time.sleep(HOLD_SECONDS)
            conn.commit()
            invoice['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - emitted into CI evidence
            conn.rollback()
            invoice['status'] = 'FAIL'
            invoice['error'] = str(exc)
            posted.set()
        finally:
            conn.close()

    def waiter():
        posted.wait(timeout=10)
        began = time.monotonic()
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_context(cur)
                qc['response'] = action(
                    cur, 'POST_FINAL_SKU', qc_payload,
                    REQUESTS['invoice_qc_post'], group_version,
                )
            conn.commit()
            qc['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - emitted into CI evidence
            conn.rollback()
            qc['status'] = 'FAIL'
            qc['error'] = str(exc)
        finally:
            qc['elapsed_seconds'] = round(time.monotonic() - began, 3)
            conn.close()

    first = threading.Thread(target=holder, daemon=True)
    second = threading.Thread(target=waiter, daemon=True)
    first.start()
    second.start()
    first.join(timeout=20)
    second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError('VENDOR_INVOICE_VS_FINAL_SKU race thread timeout')
    if invoice.get('status') != 'PASS' or qc.get('status') != 'PASS':
        raise RuntimeError(f'Vendor invoice/Final-SKU race mismatch: invoice={invoice}, qc={qc}')
    if qc.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'Final-SKU did not wait for invoice receipt lock: {qc}')
    return {'invoice': invoice, 'qc': qc}


def run_vendor_invoice_reversal_vs_final_sku(
    invoice_id: str,
    qc_payload: dict[str, Any],
    group_version: int,
) -> dict[str, Any]:
    """Prove invoice reversal restores estimate before waiting Final-SKU HPP."""
    reversed_invoice = threading.Event()
    invoice: dict[str, Any] = {}
    qc: dict[str, Any] = {}

    def holder():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_claims(cur)
                cur.execute(
                    'select erp.reverse_vendor_invoice(%s::uuid,%s)',
                    (invoice_id, 'CP6 concurrent invoice reversal versus Final-SKU'),
                )
                reversed_invoice.set()
                time.sleep(HOLD_SECONDS)
            conn.commit()
            invoice['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - emitted into CI evidence
            conn.rollback()
            invoice['status'] = 'FAIL'
            invoice['error'] = str(exc)
            reversed_invoice.set()
        finally:
            conn.close()

    def waiter():
        reversed_invoice.wait(timeout=10)
        began = time.monotonic()
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_context(cur)
                qc['response'] = action(
                    cur, 'POST_FINAL_SKU', qc_payload,
                    REQUESTS['invoice_reversal_qc_post'], group_version,
                )
            conn.commit()
            qc['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - emitted into CI evidence
            conn.rollback()
            qc['status'] = 'FAIL'
            qc['error'] = str(exc)
        finally:
            qc['elapsed_seconds'] = round(time.monotonic() - began, 3)
            conn.close()

    first = threading.Thread(target=holder, daemon=True)
    second = threading.Thread(target=waiter, daemon=True)
    first.start()
    second.start()
    first.join(timeout=20)
    second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError('VENDOR_INVOICE_REVERSAL_VS_FINAL_SKU race thread timeout')
    if invoice.get('status') != 'PASS' or qc.get('status') != 'PASS':
        raise RuntimeError(f'Invoice reversal/Final-SKU race mismatch: invoice={invoice}, qc={qc}')
    if qc.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'Final-SKU did not wait for invoice-reversal receipt lock: {qc}')
    return {'invoice_reversal': invoice, 'qc': qc}


def run_final_sku_before_vendor_invoice(
    invoice_id: str,
    qc_payload: dict[str, Any],
    group_version: int,
    qc_request_id: str,
    reverse_invoice: bool = False,
) -> dict[str, Any]:
    """Hold Final-SKU uncommitted, then prove invoice lifecycle recosts it."""
    posted = threading.Event()
    qc: dict[str, Any] = {}
    invoice: dict[str, Any] = {}

    def holder():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_context(cur)
                qc['response'] = action(
                    cur, 'POST_FINAL_SKU', qc_payload, qc_request_id, group_version,
                )
                posted.set()
                time.sleep(HOLD_SECONDS)
            conn.commit()
            qc['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - emitted into CI evidence
            conn.rollback()
            qc['status'] = 'FAIL'
            qc['error'] = str(exc)
            posted.set()
        finally:
            conn.close()

    def waiter():
        posted.wait(timeout=10)
        began = time.monotonic()
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_claims(cur)
                if reverse_invoice:
                    cur.execute(
                        'select erp.reverse_vendor_invoice(%s::uuid,%s)',
                        (invoice_id, 'CP6 Final-SKU-first invoice reversal serialization'),
                    )
                else:
                    cur.execute('select erp.post_vendor_invoice(%s::uuid)', (invoice_id,))
            conn.commit()
            invoice['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - emitted into CI evidence
            conn.rollback()
            invoice['status'] = 'FAIL'
            invoice['error'] = str(exc)
        finally:
            invoice['elapsed_seconds'] = round(time.monotonic() - began, 3)
            conn.close()

    first = threading.Thread(target=holder, daemon=True)
    second = threading.Thread(target=waiter, daemon=True)
    first.start()
    second.start()
    first.join(timeout=20)
    second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError('FINAL_SKU_BEFORE_VENDOR_INVOICE race thread timeout')
    if qc.get('status') != 'PASS' or invoice.get('status') != 'PASS':
        raise RuntimeError(f'Final-SKU/invoice lifecycle race mismatch: qc={qc}, invoice={invoice}')
    if invoice.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS:
        raise RuntimeError(f'Invoice lifecycle did not wait for Final-SKU receipt lock: {invoice}')
    return {'qc': qc, 'invoice_reversal' if reverse_invoice else 'invoice': invoice}


def run_invoice_reversal_vs_replacement_post(
    replaced_invoice_id: str,
    replacement_invoice_id: str,
) -> dict[str, Any]:
    """Reproduce F01 and prove the waiter refreshes prior cost under lock.

    The holder restores the receipt estimate but keeps that transaction
    uncommitted.  The replacement posting must block on the canonical CP6FLOW
    fence before it opens the cursor that captures prior_actual_*.
    """
    reversed_invoice = threading.Event()
    waiter_started = threading.Event()
    holder: dict[str, Any] = {}
    waiter: dict[str, Any] = {}

    def holder_work():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_claims(cur)
                cur.execute('select pg_backend_pid()')
                holder['backend_pid'] = cur.fetchone()[0]
                cur.execute(
                    'select erp.reverse_vendor_invoice(%s::uuid,%s)',
                    (replaced_invoice_id, 'CP6 F01 replaced invoice reversal'),
                )
                reversed_invoice.set()
                time.sleep(HOLD_SECONDS)
            conn.commit()
            holder['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - emitted into CI evidence
            conn.rollback()
            holder['status'] = 'FAIL'
            holder['error'] = str(exc)
            reversed_invoice.set()
        finally:
            conn.close()

    def waiter_work():
        reversed_invoice.wait(timeout=10)
        began = time.monotonic()
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                set_operator_claims(cur)
                cur.execute('select pg_backend_pid()')
                waiter['backend_pid'] = cur.fetchone()[0]
                waiter_started.set()
                cur.execute(
                    'select erp.post_vendor_invoice(%s::uuid)',
                    (replacement_invoice_id,),
                )
            conn.commit()
            waiter['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - emitted into CI evidence
            conn.rollback()
            waiter['status'] = 'FAIL'
            waiter['error'] = str(exc)
            waiter_started.set()
        finally:
            waiter['elapsed_seconds'] = round(time.monotonic() - began, 3)
            conn.close()

    first = threading.Thread(target=holder_work, daemon=True)
    second = threading.Thread(target=waiter_work, daemon=True)
    first.start()
    second.start()
    waiter_started.wait(timeout=10)

    lock_observed = False
    observation_deadline = time.monotonic() + HOLD_SECONDS
    while time.monotonic() < observation_deadline:
        if holder.get('backend_pid') and waiter.get('backend_pid'):
            blockers = scalar(
                'select pg_blocking_pids(%s)', (waiter['backend_pid'],),
            )
            if holder['backend_pid'] in blockers:
                lock_observed = True
                break
        time.sleep(0.025)

    first.join(timeout=20)
    second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError('INVOICE_REVERSAL_VS_REPLACEMENT_POST race thread timeout')
    if holder.get('status') != 'PASS' or waiter.get('status') != 'PASS':
        raise RuntimeError(
            f'Invoice reversal/replacement race mismatch: holder={holder}, waiter={waiter}'
        )
    if waiter.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS or not lock_observed:
        raise RuntimeError(
            'Invoice replacement did not prove a real canonical-lock wait: '
            f'lock_observed={lock_observed}, waiter={waiter}'
        )
    return {
        'invoice_reversal': holder,
        'replacement_post': waiter,
        'pg_blocking_pids_observed': lock_observed,
    }


def create_vendor_invoice(
    receipt_line: str,
    invoice_id: str,
    item_id: str,
    invoice_number: str,
    actual_rate: int,
):
    total = actual_rate * 10
    with connect() as conn, conn.cursor() as cur:
        # Psycopg 3 rejects multiple parameterized commands in one prepared
        # statement. Keep the parent and child inserts as two statements inside
        # this one transaction so they remain atomic without relying on a
        # driver-specific multi-command path.
        cur.execute(
            """
            insert into erp.vendor_invoices(
              id,invoice_number,vendor_id,invoice_date,received_at,due_date,
              status,total_amount,notes,created_by
            ) values(%s::uuid,%s,%s::uuid,'2026-09-01',
              '2026-09-01 12:30:00+00','2026-09-15','DRAFT',%s,
              'CP6 invoice/reversal serialization proof',%s::uuid)
            """,
            (invoice_id, invoice_number, VENDOR, total, OPERATOR_APP),
        )
        cur.execute(
            """
            insert into erp.vendor_invoice_items(
              id,invoice_id,receipt_line_id,description,qty_pcs,actual_rate,actual_amount
            ) values(%s::uuid,%s::uuid,%s::uuid,
              'CP6 exact posted receipt',10,%s,%s)
            """,
            (item_id, invoice_id, receipt_line, actual_rate, total),
        )
        conn.commit()


def reverse_vendor_invoice(invoice_id: str, reason: str):
    with connect() as conn, conn.cursor() as cur:
        set_operator_claims(cur)
        cur.execute(
            "select erp.reverse_vendor_invoice(%s::uuid,%s)",
            (invoice_id, reason),
        )
        conn.commit()


def invoice_qc_state(invoice_id: str, receipt_line: str):
    return scalar(
        """
        select jsonb_build_object(
          'invoice_status',(select status from erp.vendor_invoices where id=%s::uuid),
          'receipt_cost_status',(select actual_cost_status from erp.laundry_receipt_lines where id=%s::uuid),
          'receipt_actual_cost',(select actual_cost from erp.laundry_receipt_lines where id=%s::uuid),
          'posted_qc_count',(select count(*) from erp.qc_inspections where po_id=%s::uuid and status='POSTED'),
          'fg_stock_qty',(select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m
            join erp.fg_lots l on l.id=m.lot_id where l.po_id=%s::uuid),
          'current_hpp_total',(select coalesce(sum(h.total_cost),0) from erp.hpp_versions h
            join erp.fg_lots l on l.id=h.lot_id
            where l.po_id=%s::uuid and l.lot_origin='PRODUCTION' and h.is_current),
          'laundry_accrual',(select accrued_amount from erp.laundry_cost_accrual_state where po_id=%s::uuid),
          'wip_net',(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
            where l.po_id=%s::uuid and l.account_id=erp.account_id('WIP')),
          'fg_net',(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
            where l.po_id=%s::uuid and l.account_id=erp.account_id('FG_INVENTORY')),
          'accrued_net',(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
            where l.po_id=%s::uuid and l.account_id=erp.account_id('ACCRUED_MANUFACTURING')),
          -- AP is vendor-scoped: one invoice may settle receipt lines from
          -- multiple production orders, so the control line has no fake PO.
          'vendor_ap_net',(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
            where l.vendor_id=%s::uuid and l.account_id=erp.account_id('AP_VENDOR')),
          'unbalanced_journals',(select count(*) from(
            select e.id from erp.journal_entries e join erp.journal_lines l on l.journal_entry_id=e.id
            group by e.id having sum(l.debit)<>sum(l.credit)
          ) bad)
        )
        """,
        (
            invoice_id, receipt_line, receipt_line, PO, PO, PO,
            PO, PO, PO, PO, VENDOR,
        ),
    )


def main():
    report: dict[str, Any] = {
        'status': 'RUNNING',
        'database_scope': 'ISOLATED_CLONE_DESTROYED_BY_WORKFLOW',
        'production_go': False,
        'races': {},
    }

    report['races']['first_accrual_creation'] = run_first_accrual_creation_race()
    first_accrual_invariants = scalar(
        """
        select jsonb_build_object(
          'state_rows',(select count(*) from erp.laundry_cost_accrual_state
            where po_id=%s::uuid),
          'accrued_amount',(select coalesce(sum(accrued_amount),0)
            from erp.laundry_cost_accrual_state where po_id=%s::uuid),
          'event_rows',(select count(*) from erp.laundry_cost_accrual_events
            where po_id=%s::uuid),
          'event_delta',(select coalesce(sum(delta_amount),0)
            from erp.laundry_cost_accrual_events where po_id=%s::uuid),
          'journal_rows',(select count(distinct journal_entry_id)
            from erp.laundry_cost_accrual_events where po_id=%s::uuid),
          'wip_net',(select coalesce(sum(debit-credit),0) from erp.journal_lines
            where po_id=%s::uuid and account_id=erp.account_id('WIP')),
          'accrued_net',(select coalesce(sum(debit-credit),0) from erp.journal_lines
            where po_id=%s::uuid and account_id=erp.account_id('ACCRUED_MANUFACTURING')),
          'unbalanced_journals',(select count(*) from(
            select e.id from erp.journal_entries e join erp.journal_lines l
              on l.journal_entry_id=e.id
            where l.po_id=%s::uuid group by e.id having sum(l.debit)<>sum(l.credit)
          ) bad)
        )
        """,
        (FIRST_ACCRUAL_PO,) * 8,
    )
    first_accrual_expected = {
        'state_rows': 1,
        'accrued_amount': 70,
        'event_rows': 1,
        'event_delta': 70,
        'journal_rows': 1,
        'wip_net': 70,
        'accrued_net': -70,
        'unbalanced_journals': 0,
    }
    report['first_accrual_invariants'] = first_accrual_invariants
    report['first_accrual_expected'] = first_accrual_expected
    if first_accrual_invariants != first_accrual_expected:
        raise RuntimeError(
            'CP6 first-row accrual serialization mismatch: '
            f'expected={first_accrual_expected}, actual={first_accrual_invariants}'
        )

    report['f02_physical_prefix'] = run_f02_physical_prefix_proof()

    group_version = int(scalar('select row_version from erp.cutting_groups where id=%s::uuid', (GROUP,)))
    delivery_payload = {
        'distribution_batch_id': BATCH,
        'vendor_id': VENDOR,
        'wash_process_id': PROCESS,
        'target_dyeing_color': 'NAVY',
        'physical_at': '2026-09-01T11:00:00Z',
        'reason': 'CP6 delivery serialization race',
        'notes': 'One physical dispatch must win',
        'lines': [{'size_id': SIZE, 'qty_sent_pcs': 10}],
    }
    report['races']['post_delivery'] = run_race(
        'POST_DELIVERY', 'POST_DELIVERY', delivery_payload, group_version,
        REQUESTS['delivery_winner'], REQUESTS['delivery_loser'], ('STALE_VERSION',),
    )
    delivery_response = report['races']['post_delivery']['winner']['response']
    delivery_id = str(delivery_response['delivery_id'])
    delivery_version = int(delivery_response['row_version'])
    delivery_size_line = str(scalar(
        'select x.id from erp.laundry_delivery_batch_size_lines x '
        'join erp.laundry_delivery_lines l on l.id=x.delivery_line_id '
        'where l.delivery_id=%s::uuid', (delivery_id,),
    ))

    receipt_payload = {
        'delivery_id': delivery_id,
        'wash_process_id': PROCESS,
        'physical_at': '2026-09-01T12:00:00Z',
        'reason': 'CP6 receipt serialization race',
        'lines': [{
            'delivery_batch_size_line_id': delivery_size_line,
            'qty_good_received': 10,
            'qty_bs_laundry': 0,
            'bs_product_id': None,
        }],
    }
    failed_wash_payload = {
        'delivery_id': delivery_id,
        'wash_process_id': PROCESS,
        'custody_outcome': 'RETRY_AT_VENDOR',
        'physical_at': '2026-09-01T11:30:00Z',
        'reason': 'CP6 paid failed-wash versus physical receipt race',
        'lines': [{
            'delivery_batch_size_line_id': delivery_size_line,
            'qty_attempted_pcs': 10,
        }],
    }
    report['races']['failed_wash_vs_post_receipt'] = run_committed_action_race(
        'POST_FAILED_WASH_VS_POST_RECEIPT',
        'POST_FAILED_WASH', failed_wash_payload,
        REQUESTS['failed_wash_winner'], delivery_version,
        'POST_RECEIPT', receipt_payload,
        REQUESTS['failed_wash_receipt_loser'], delivery_version,
        ('STALE_VERSION',),
    )
    failed_wash_response = (
        report['races']['failed_wash_vs_post_receipt']['winner']['response']
    )
    failed_wash_receipt = str(failed_wash_response['receipt_id'])
    failed_wash_reversal = single_action(
        'REVERSE_RECEIPT',
        {
            'receipt_id': failed_wash_receipt,
            'reason': 'CP6 restore failed-wash race before physical receipt proof',
        },
        REQUESTS['failed_wash_reverse'],
        int(failed_wash_response['receipt_row_version']),
    )
    if failed_wash_reversal.get('status') != 'REVERSED':
        raise RuntimeError(
            f'CP6 could not reverse paid failed-wash race winner: {failed_wash_reversal}'
        )
    delivery_version = int(scalar(
        'select row_version from erp.laundry_deliveries where id=%s::uuid',
        (delivery_id,),
    ))
    report['races']['post_receipt'] = run_race(
        'POST_RECEIPT', 'POST_RECEIPT', receipt_payload, delivery_version,
        REQUESTS['receipt_winner'], REQUESTS['receipt_loser'],
        ('STALE_VERSION', 'Laundry receipt requires an active SENT/PARTIAL_RETURN delivery'),
    )
    receipt_response = report['races']['post_receipt']['winner']['response']
    receipt_id = str(receipt_response['receipt_id'])
    receipt_line = str(scalar(
        'select id from erp.laundry_receipt_lines where receipt_id=%s::uuid', (receipt_id,),
    ))
    receipt_size_line = str(scalar(
        'select id from erp.laundry_receipt_batch_size_lines where receipt_line_id=%s::uuid',
        (receipt_line,),
    ))

    create_vendor_invoice(
        receipt_line, VENDOR_INVOICE, VENDOR_INVOICE_ITEM, 'CP6-RACE-VI-001', 7,
    )
    receipt_version = int(scalar(
        'select row_version from erp.laundry_receipts where id=%s::uuid', (receipt_id,),
    ))
    report['races']['vendor_invoice_vs_reverse_receipt'] = (
        run_vendor_invoice_vs_receipt_reversal(receipt_id, receipt_version)
    )
    reverse_vendor_invoice(
        VENDOR_INVOICE, 'CP6 restore pre-invoice state after receipt-reversal proof',
    )

    group_version = int(scalar('select row_version from erp.cutting_groups where id=%s::uuid', (GROUP,)))
    qc_payload = {
        'cutting_group_id': GROUP,
        'destination_location_id': LOCATION,
        'physical_at': '2026-09-01T13:00:00Z',
        'reason': 'CP6 final SKU serialization race',
        'good_qty_pcs': 10,
        'completion_mode': 'ALL_READY',
        'lines': [{
            'final_product_id': PRODUCT,
            'qty_good_pcs': 10,
            'qty_bs_pcs': 0,
            'source_laundry_receipt_line_id': receipt_line,
            'source_laundry_receipt_batch_size_line_id': receipt_size_line,
            'notes': 'One exact source may become FG once',
        }],
    }

    create_vendor_invoice(
        receipt_line, VENDOR_INVOICE_QC, VENDOR_INVOICE_QC_ITEM,
        'CP6-RACE-VI-002', 9,
    )
    group_version = int(scalar(
        'select row_version from erp.cutting_groups where id=%s::uuid', (GROUP,),
    ))
    report['races']['vendor_invoice_vs_final_sku'] = run_vendor_invoice_vs_final_sku(
        VENDOR_INVOICE_QC, qc_payload, group_version,
    )
    invoice_qc_invariants = invoice_qc_state(VENDOR_INVOICE_QC, receipt_line)
    expected_invoice_qc = {
        'invoice_status': 'POSTED',
        'receipt_cost_status': 'FINAL',
        'receipt_actual_cost': 90,
        'posted_qc_count': 1,
        'fg_stock_qty': 10,
        'current_hpp_total': 90,
        'laundry_accrual': 0,
        'wip_net': 0,
        'fg_net': 90,
        'accrued_net': 0,
        'vendor_ap_net': -90,
        'unbalanced_journals': 0,
    }
    report['invoice_qc_invariants'] = invoice_qc_invariants
    report['invoice_qc_expected'] = expected_invoice_qc
    if invoice_qc_invariants != expected_invoice_qc:
        raise RuntimeError(
            'CP6 invoice/Final-SKU serialized finance mismatch: '
            f'expected={expected_invoice_qc}, actual={invoice_qc_invariants}'
        )

    invoice_qc_response = report['races']['vendor_invoice_vs_final_sku']['qc']['response']
    reversed_invoice_qc = single_action(
        'REVERSE_FINAL_SKU',
        {
            'qc_inspection_id': str(invoice_qc_response['qc_inspection_id']),
            'reason': 'CP6 restore after invoice versus Final-SKU proof',
        },
        REQUESTS['invoice_qc_reverse'],
        int(invoice_qc_response['qc_row_version']),
    )
    if reversed_invoice_qc.get('status') != 'REVERSED':
        raise RuntimeError(f'CP6 could not reverse invoice-race QC: {reversed_invoice_qc}')
    group_version = int(scalar(
        'select row_version from erp.cutting_groups where id=%s::uuid', (GROUP,),
    ))
    report['races']['vendor_invoice_reversal_vs_final_sku'] = (
        run_vendor_invoice_reversal_vs_final_sku(
            VENDOR_INVOICE_QC, qc_payload, group_version,
        )
    )
    invoice_reversal_qc_invariants = invoice_qc_state(VENDOR_INVOICE_QC, receipt_line)
    expected_invoice_reversal_qc = {
        'invoice_status': 'REVERSED',
        'receipt_cost_status': 'ESTIMATED',
        'receipt_actual_cost': 70,
        'posted_qc_count': 1,
        'fg_stock_qty': 10,
        'current_hpp_total': 70,
        'laundry_accrual': 70,
        'wip_net': 0,
        'fg_net': 70,
        'accrued_net': -70,
        'vendor_ap_net': 0,
        'unbalanced_journals': 0,
    }
    report['invoice_reversal_qc_invariants'] = invoice_reversal_qc_invariants
    report['invoice_reversal_qc_expected'] = expected_invoice_reversal_qc
    if invoice_reversal_qc_invariants != expected_invoice_reversal_qc:
        raise RuntimeError(
            'CP6 invoice-reversal/Final-SKU serialized finance mismatch: '
            f'expected={expected_invoice_reversal_qc}, actual={invoice_reversal_qc_invariants}'
        )

    invoice_reversal_qc_response = (
        report['races']['vendor_invoice_reversal_vs_final_sku']['qc']['response']
    )
    reversed_invoice_reversal_qc = single_action(
        'REVERSE_FINAL_SKU',
        {
            'qc_inspection_id': str(invoice_reversal_qc_response['qc_inspection_id']),
            'reason': 'CP6 restore after invoice-reversal versus Final-SKU proof',
        },
        REQUESTS['invoice_reversal_qc_reverse'],
        int(invoice_reversal_qc_response['qc_row_version']),
    )
    if reversed_invoice_reversal_qc.get('status') != 'REVERSED':
        raise RuntimeError(
            f'CP6 could not reverse invoice-reversal-race QC: {reversed_invoice_reversal_qc}'
        )

    # Independent-audit F01, exact schedule: A is FINAL 90; reverse A and hold
    # it uncommitted; post replacement B at 100 from another connection.  B
    # must wait before prior_actual_* is captured.  Reversing B must therefore
    # restore the live ESTIMATED 70 state, never resurrect A's cancelled 90.
    create_vendor_invoice(
        receipt_line, VENDOR_INVOICE_REPLACED, VENDOR_INVOICE_REPLACED_ITEM,
        'CP6-RACE-VI-F01-A', 9,
    )
    with connect() as conn, conn.cursor() as cur:
        set_operator_claims(cur)
        cur.execute(
            'select erp.post_vendor_invoice(%s::uuid)', (VENDOR_INVOICE_REPLACED,),
        )
        conn.commit()
    create_vendor_invoice(
        receipt_line, VENDOR_INVOICE_REPLACEMENT, VENDOR_INVOICE_REPLACEMENT_ITEM,
        'CP6-RACE-VI-F01-B', 10,
    )
    report['races']['invoice_reversal_vs_replacement_post'] = (
        run_invoice_reversal_vs_replacement_post(
            VENDOR_INVOICE_REPLACED, VENDOR_INVOICE_REPLACEMENT,
        )
    )
    f01_prior_state = scalar(
        """
        select jsonb_build_object(
          'prior_status',prior_actual_cost_status,
          'prior_rate',prior_actual_rate_snapshot,
          'prior_cost',prior_actual_cost
        )
        from erp.vendor_invoice_items where id=%s::uuid
        """,
        (VENDOR_INVOICE_REPLACEMENT_ITEM,),
    )
    f01_post_state = invoice_qc_state(VENDOR_INVOICE_REPLACEMENT, receipt_line)
    f01_post_expected = {
        'invoice_status': 'POSTED',
        'receipt_cost_status': 'FINAL',
        'receipt_actual_cost': 100,
        'posted_qc_count': 0,
        'fg_stock_qty': 0,
        'current_hpp_total': 0,
        'laundry_accrual': 0,
        'wip_net': 100,
        'fg_net': 0,
        'accrued_net': 0,
        'vendor_ap_net': -100,
        'unbalanced_journals': 0,
    }
    report['f01_replacement_prior_state'] = f01_prior_state
    report['f01_replacement_post_state'] = f01_post_state
    if f01_prior_state != {
        'prior_status': 'ESTIMATED', 'prior_rate': 7, 'prior_cost': 70,
    } or f01_post_state != f01_post_expected:
        raise RuntimeError(
            'CP6 F01 replacement captured stale prior cost or broke finance: '
            f'prior={f01_prior_state}, expected_prior=ESTIMATED/7/70, '
            f'post={f01_post_state}, expected_post={f01_post_expected}'
        )
    reverse_vendor_invoice(
        VENDOR_INVOICE_REPLACEMENT,
        'CP6 F01 prove replacement reversal restores live estimate',
    )
    f01_final_state = invoice_qc_state(VENDOR_INVOICE_REPLACEMENT, receipt_line)
    f01_final_expected = {
        'invoice_status': 'REVERSED',
        'receipt_cost_status': 'ESTIMATED',
        'receipt_actual_cost': 70,
        'posted_qc_count': 0,
        'fg_stock_qty': 0,
        'current_hpp_total': 0,
        'laundry_accrual': 70,
        'wip_net': 70,
        'fg_net': 0,
        'accrued_net': -70,
        'vendor_ap_net': 0,
        'unbalanced_journals': 0,
    }
    report['f01_replacement_final_state'] = f01_final_state
    if f01_final_state != f01_final_expected:
        raise RuntimeError(
            'CP6 F01 replacement reversal resurrected cancelled cost: '
            f'expected={f01_final_expected}, actual={f01_final_state}'
        )

    # Repeat both lifecycle directions with Final-SKU holding the receipt first.
    # The invoice may update its private transaction before it reaches the
    # status trigger, but it must wait on the receipt header, then recost active
    # HPP/GL from the committed physical truth before it can commit.
    create_vendor_invoice(
        receipt_line, VENDOR_INVOICE_QC_AFTER, VENDOR_INVOICE_QC_AFTER_ITEM,
        'CP6-RACE-VI-003', 9,
    )
    group_version = int(scalar(
        'select row_version from erp.cutting_groups where id=%s::uuid', (GROUP,),
    ))
    report['races']['final_sku_vs_vendor_invoice'] = run_final_sku_before_vendor_invoice(
        VENDOR_INVOICE_QC_AFTER, qc_payload, group_version,
        REQUESTS['qc_before_invoice_post'],
    )
    qc_before_invoice_state = invoice_qc_state(VENDOR_INVOICE_QC_AFTER, receipt_line)
    report['qc_before_invoice_invariants'] = qc_before_invoice_state
    report['qc_before_invoice_expected'] = expected_invoice_qc
    if qc_before_invoice_state != expected_invoice_qc:
        raise RuntimeError(
            'CP6 Final-SKU-first invoice recost mismatch: '
            f'expected={expected_invoice_qc}, actual={qc_before_invoice_state}'
        )
    qc_before_invoice_response = (
        report['races']['final_sku_vs_vendor_invoice']['qc']['response']
    )
    reversed_qc_before_invoice = single_action(
        'REVERSE_FINAL_SKU',
        {
            'qc_inspection_id': str(qc_before_invoice_response['qc_inspection_id']),
            'reason': 'CP6 restore after Final-SKU-first invoice proof',
        },
        REQUESTS['qc_before_invoice_reverse'],
        int(qc_before_invoice_response['qc_row_version']),
    )
    if reversed_qc_before_invoice.get('status') != 'REVERSED':
        raise RuntimeError(
            f'CP6 could not reverse Final-SKU-first invoice QC: {reversed_qc_before_invoice}'
        )

    group_version = int(scalar(
        'select row_version from erp.cutting_groups where id=%s::uuid', (GROUP,),
    ))
    report['races']['final_sku_vs_vendor_invoice_reversal'] = (
        run_final_sku_before_vendor_invoice(
            VENDOR_INVOICE_QC_AFTER, qc_payload, group_version,
            REQUESTS['qc_before_invoice_reversal_post'], reverse_invoice=True,
        )
    )
    qc_before_invoice_reversal_state = invoice_qc_state(
        VENDOR_INVOICE_QC_AFTER, receipt_line,
    )
    report['qc_before_invoice_reversal_invariants'] = qc_before_invoice_reversal_state
    report['qc_before_invoice_reversal_expected'] = expected_invoice_reversal_qc
    if qc_before_invoice_reversal_state != expected_invoice_reversal_qc:
        raise RuntimeError(
            'CP6 Final-SKU-first invoice-reversal recost mismatch: '
            f'expected={expected_invoice_reversal_qc}, actual={qc_before_invoice_reversal_state}'
        )
    qc_before_invoice_reversal_response = (
        report['races']['final_sku_vs_vendor_invoice_reversal']['qc']['response']
    )
    reversed_qc_before_invoice_reversal = single_action(
        'REVERSE_FINAL_SKU',
        {
            'qc_inspection_id': str(
                qc_before_invoice_reversal_response['qc_inspection_id']
            ),
            'reason': 'CP6 restore after Final-SKU-first invoice-reversal proof',
        },
        REQUESTS['qc_before_invoice_reversal_reverse'],
        int(qc_before_invoice_reversal_response['qc_row_version']),
    )
    if reversed_qc_before_invoice_reversal.get('status') != 'REVERSED':
        raise RuntimeError(
            'CP6 could not reverse Final-SKU-first invoice-reversal QC: '
            f'{reversed_qc_before_invoice_reversal}'
        )

    group_version = int(scalar(
        'select row_version from erp.cutting_groups where id=%s::uuid', (GROUP,),
    ))
    report['races']['post_final_sku'] = run_race(
        'POST_FINAL_SKU', 'POST_FINAL_SKU', qc_payload, group_version,
        REQUESTS['qc_winner'], REQUESTS['qc_loser'],
        ('STALE_VERSION', 'QC quantity exceeds GOOD returned for the exact Laundry batch/size'),
    )

    first_qc_response = report['races']['post_final_sku']['winner']['response']
    first_qc_id = str(first_qc_response['qc_inspection_id'])
    first_qc_version = int(first_qc_response['qc_row_version'])
    reversed_qc = single_action(
        'REVERSE_FINAL_SKU',
        {
            'qc_inspection_id': first_qc_id,
            'reason': 'CP6 prepare Final-SKU versus receipt-reversal race',
        },
        REQUESTS['qc_reverse'],
        first_qc_version,
    )
    if reversed_qc.get('status') != 'REVERSED':
        raise RuntimeError(f'CP6 could not prepare cross-operation race: {reversed_qc}')

    group_version = int(scalar(
        'select row_version from erp.cutting_groups where id=%s::uuid', (GROUP,),
    ))
    receipt_version = int(scalar(
        'select row_version from erp.laundry_receipts where id=%s::uuid', (receipt_id,),
    ))
    report['races']['final_sku_vs_reverse_receipt'] = run_committed_action_race(
        'POST_FINAL_SKU_VS_REVERSE_RECEIPT',
        'POST_FINAL_SKU', qc_payload, REQUESTS['qc_repost_winner'], group_version,
        'REVERSE_RECEIPT', {
            'receipt_id': receipt_id,
            'reason': 'CP6 competing receipt reversal must serialize',
        }, REQUESTS['receipt_reverse_loser'], receipt_version,
        ('Penerimaan laundry ini sudah dipakai QC',),
    )

    # A Final-SKU facade commit deliberately produces two durable receipts
    # under the same UUID: the public CP6 envelope and the authoritative
    # private FG-posting envelope.  Bind each UUID to its exact operation so
    # the proof rejects both missing receipts and any unrelated/duplicate
    # idempotency fact instead of accepting a loose aggregate count.
    winner_facade_expectations = [
        (REQUESTS['delivery_winner'], 'cp6_laundry_qc_action_v1:post_delivery'),
        (REQUESTS['receipt_winner'], 'cp6_laundry_qc_action_v1:post_receipt'),
        (REQUESTS['failed_wash_winner'], 'cp6_laundry_qc_action_v1:post_failed_wash'),
        (REQUESTS['failed_wash_reverse'], 'cp6_laundry_qc_action_v1:reverse_receipt'),
        (REQUESTS['invoice_qc_post'], 'cp6_laundry_qc_action_v1:post_final_sku'),
        (REQUESTS['invoice_qc_reverse'], 'cp6_laundry_qc_action_v1:reverse_final_sku'),
        (REQUESTS['invoice_reversal_qc_post'], 'cp6_laundry_qc_action_v1:post_final_sku'),
        (REQUESTS['invoice_reversal_qc_reverse'], 'cp6_laundry_qc_action_v1:reverse_final_sku'),
        (REQUESTS['qc_before_invoice_post'], 'cp6_laundry_qc_action_v1:post_final_sku'),
        (REQUESTS['qc_before_invoice_reverse'], 'cp6_laundry_qc_action_v1:reverse_final_sku'),
        (REQUESTS['qc_before_invoice_reversal_post'], 'cp6_laundry_qc_action_v1:post_final_sku'),
        (REQUESTS['qc_before_invoice_reversal_reverse'], 'cp6_laundry_qc_action_v1:reverse_final_sku'),
        (REQUESTS['qc_winner'], 'cp6_laundry_qc_action_v1:post_final_sku'),
        (REQUESTS['qc_reverse'], 'cp6_laundry_qc_action_v1:reverse_final_sku'),
        (REQUESTS['qc_repost_winner'], 'cp6_laundry_qc_action_v1:post_final_sku'),
    ]
    winner_requests = [request_id for request_id, _ in winner_facade_expectations]
    winner_operations = [operation for _, operation in winner_facade_expectations]
    final_sku_requests = [
        REQUESTS['invoice_qc_post'],
        REQUESTS['invoice_reversal_qc_post'],
        REQUESTS['qc_before_invoice_post'],
        REQUESTS['qc_before_invoice_reversal_post'],
        REQUESTS['qc_winner'],
        REQUESTS['qc_repost_winner'],
    ]
    loser_requests = [
        REQUESTS['delivery_loser'], REQUESTS['receipt_loser'],
        REQUESTS['failed_wash_receipt_loser'],
        REQUESTS['qc_loser'], REQUESTS['receipt_reverse_loser'],
        REQUESTS['invoice_receipt_reverse_loser'],
    ]

    invariants = scalar(
        """
        with expected_facade(client_request_id,operation_name) as (
          select * from unnest(%s::uuid[],%s::text[])
        ), expected_final_sku(client_request_id) as (
          select unnest(%s::uuid[])
        ), expected_loser(client_request_id) as (
          select unnest(%s::uuid[])
        )
        select jsonb_build_object(
          'active_delivery_count',(select count(*) from erp.laundry_deliveries
            where po_id=%s::uuid and status<>'REVERSED'),
          'delivery_size_qty',(select coalesce(sum(x.qty_sent_pcs),0)
            from erp.laundry_delivery_batch_size_lines x
            join erp.laundry_delivery_lines l on l.id=x.delivery_line_id
            where l.delivery_id=%s::uuid),
          'failed_wash_attempt_history',(select count(*)
            from erp.laundry_failed_wash_attempts a where a.delivery_id=%s::uuid),
          'failed_wash_active_receipts',(select count(*)
            from erp.laundry_failed_wash_attempts a
            join erp.laundry_receipts r on r.id=a.receipt_id
            where a.delivery_id=%s::uuid and r.status='POSTED'),
          'failed_wash_physical_lines',(select count(*)
            from erp.laundry_failed_wash_attempts a
            join erp.laundry_receipt_batch_size_lines x on x.receipt_line_id=a.receipt_line_id
            where a.delivery_id=%s::uuid),
          'posted_receipt_count',(select count(*) from erp.laundry_receipts
            where delivery_id=%s::uuid and status='POSTED'),
          'receipt_good_qty',(select coalesce(sum(x.qty_good_received),0)
            from erp.laundry_receipt_batch_size_lines x
            join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
            where l.receipt_id=%s::uuid),
          'posted_qc_count',(select count(*) from erp.qc_inspections
            where po_id=%s::uuid and status='POSTED'),
          'qc_accounted_qty',(select coalesce(sum(i.qty_good_pcs+i.qty_bs_pcs),0)
            from erp.qc_inspection_items i join erp.qc_inspections q on q.id=i.inspection_id
            where q.po_id=%s::uuid and q.status='POSTED'),
          'fg_stock_qty',(select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m
            join erp.fg_lots l on l.id=m.lot_id where l.po_id=%s::uuid),
          'current_hpp_total',(select coalesce(sum(h.total_cost),0) from erp.hpp_versions h
            join erp.fg_lots l on l.id=h.lot_id
            where l.po_id=%s::uuid and l.lot_origin='PRODUCTION' and h.is_current),
          'voided_hpp_history_lots',(select count(distinct l.id) from erp.fg_lots l
            join erp.hpp_versions h on h.lot_id=l.id
            where l.po_id=%s::uuid and l.lot_origin='VOIDED_PRODUCTION'),
          'receipt_cost_status',(select actual_cost_status from erp.laundry_receipt_lines
            where id=%s::uuid),
          'laundry_accrual',(select accrued_amount from erp.laundry_cost_accrual_state
            where po_id=%s::uuid),
          'wip_net',(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
            where l.po_id=%s::uuid and l.account_id=erp.account_id('WIP')),
          'fg_net',(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
            where l.po_id=%s::uuid and l.account_id=erp.account_id('FG_INVENTORY')),
          'accrued_net',(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
            where l.po_id=%s::uuid and l.account_id=erp.account_id('ACCRUED_MANUFACTURING')),
          -- AP is vendor-scoped: one invoice may settle receipt lines from
          -- multiple production orders, so the control line has no fake PO.
          'vendor_ap_net',(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
            where l.vendor_id=%s::uuid and l.account_id=erp.account_id('AP_VENDOR')),
          'unbalanced_journals',(select count(*) from(
            select e.id from erp.journal_entries e join erp.journal_lines l on l.journal_entry_id=e.id
            group by e.id having sum(l.debit)<>sum(l.credit)
          ) bad),
          'execution_context_rows',(select count(*) from erp.cp6_laundry_qc_execution_context),
          'winner_facade_idempotency_rows',(select count(*)
            from erp.idempotency_requests i join expected_facade e
              using(client_request_id,operation_name)
            where i.status='COMPLETED'),
          'winner_facade_request_ids',(select count(distinct i.client_request_id)
            from erp.idempotency_requests i join expected_facade e
              using(client_request_id,operation_name)
            where i.status='COMPLETED'),
          'winner_nested_final_sku_idempotency_rows',(select count(*)
            from erp.idempotency_requests i join expected_final_sku e
              using(client_request_id)
            where i.operation_name='post_fg_partial_completion_v2'
              and i.status='COMPLETED'),
          'winner_nested_final_sku_request_ids',(select count(distinct i.client_request_id)
            from erp.idempotency_requests i join expected_final_sku e
              using(client_request_id)
            where i.operation_name='post_fg_partial_completion_v2'
              and i.status='COMPLETED'),
          'unexpected_winner_idempotency_rows',(select count(*)
            from erp.idempotency_requests i
            where i.client_request_id in (select client_request_id from expected_facade)
              and not (
                i.status='COMPLETED'
                and (
                  exists(select 1 from expected_facade e
                    where e.client_request_id=i.client_request_id
                      and e.operation_name=i.operation_name)
                  or (
                    i.operation_name='post_fg_partial_completion_v2'
                    and exists(select 1 from expected_final_sku e
                      where e.client_request_id=i.client_request_id)
                  )
                )
              )),
          'loser_idempotency_rows',(select count(*) from erp.idempotency_requests
            where client_request_id in (select client_request_id from expected_loser))
        )
        """,
        (
            winner_requests, winner_operations, final_sku_requests, loser_requests,
            PO, delivery_id, delivery_id, delivery_id, delivery_id,
            delivery_id, receipt_id, PO, PO, PO, PO,
            PO, receipt_line, PO, PO, PO, PO, VENDOR,
        ),
    )
    expected = {
        'active_delivery_count': 1,
        'delivery_size_qty': 10,
        'failed_wash_attempt_history': 1,
        'failed_wash_active_receipts': 0,
        'failed_wash_physical_lines': 0,
        'posted_receipt_count': 1,
        'receipt_good_qty': 10,
        'posted_qc_count': 1,
        'qc_accounted_qty': 10,
        'fg_stock_qty': 10,
        'current_hpp_total': 70,
        'voided_hpp_history_lots': 5,
        'receipt_cost_status': 'ESTIMATED',
        'laundry_accrual': 70,
        'wip_net': 0,
        'fg_net': 70,
        'accrued_net': -70,
        'vendor_ap_net': 0,
        'unbalanced_journals': 0,
        'execution_context_rows': 0,
        # Exactly 15 public facade envelopes committed. The six Final-SKU
        # winners each also committed their one expected private FG envelope;
        # no other winner operation or any losing request may leave a row.
        'winner_facade_idempotency_rows': 15,
        'winner_facade_request_ids': 15,
        'winner_nested_final_sku_idempotency_rows': 6,
        'winner_nested_final_sku_request_ids': 6,
        'unexpected_winner_idempotency_rows': 0,
        'loser_idempotency_rows': 0,
    }
    report['invariants'] = invariants
    report['expected'] = expected
    if invariants != expected:
        raise RuntimeError(f'CP6 serialized-state invariant mismatch: expected={expected}, actual={invariants}')
    report['status'] = 'PASS'
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + '\n', encoding='utf8')
    print('CP6 Laundry/QC/FG concurrency passed: twelve serialized races plus physical-time prefix proof, including first-row accrual, invoice reversal/replacement, paid failed-wash versus physical receipt, and both invoice post/reversal scheduling directions versus Final-SKU/source reversal; no duplicate physical, finance, stock, or HPP fact.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        REPORT.write_text(json.dumps({'status': 'FAIL', 'error': str(exc), 'production_go': False}, indent=2) + '\n', encoding='utf8')
        raise
