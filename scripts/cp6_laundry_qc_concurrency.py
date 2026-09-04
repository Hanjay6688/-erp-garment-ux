#!/usr/bin/env python3
"""Five real two-connection races for CP6 Laundry -> QC -> FG."""
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
VENDOR_INVOICE = 'c8c70000-0000-4000-8000-000000000001'
VENDOR_INVOICE_ITEM = 'c8c70000-0000-4000-8000-000000000002'

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
}


def connect():
    return psycopg.connect(PGURL, autocommit=False)


def set_operator_context(cur):
    claims = json.dumps({'sub': OPERATOR_AUTH, 'role': 'authenticated'})
    cur.execute("select set_config('request.jwt.claims',%s,true)", (claims,))
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
    lock_sql: str,
    lock_params: tuple[Any, ...],
    action_name: str,
    payload: dict[str, Any],
    expected_version: int,
    winner_request: str,
    loser_request: str,
    allowed_loser_errors: tuple[str, ...],
) -> dict[str, Any]:
    started = threading.Event()
    winner: dict[str, Any] = {}
    loser: dict[str, Any] = {}

    def holder():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute(lock_sql, lock_params)
                started.set()
                time.sleep(HOLD_SECONDS)
                set_operator_context(cur)
                winner['response'] = action(
                    cur, action_name, payload, winner_request, expected_version,
                )
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
                set_operator_context(cur)
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


def create_vendor_invoice(receipt_line: str):
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into erp.vendor_invoices(
              id,invoice_number,vendor_id,invoice_date,received_at,due_date,
              status,total_amount,notes,created_by
            ) values(%s::uuid,'CP6-RACE-VI-001',%s::uuid,'2026-09-01',
              '2026-09-01 12:30:00+00','2026-09-15','DRAFT',70,
              'CP6 invoice/reversal serialization proof',%s::uuid);
            insert into erp.vendor_invoice_items(
              id,invoice_id,receipt_line_id,description,qty_pcs,actual_rate,actual_amount
            ) values(%s::uuid,%s::uuid,%s::uuid,
              'CP6 exact posted receipt',10,7,70)
            """,
            (
                VENDOR_INVOICE, VENDOR, OPERATOR_APP,
                VENDOR_INVOICE_ITEM, VENDOR_INVOICE, receipt_line,
            ),
        )
        conn.commit()


def reverse_vendor_invoice():
    with connect() as conn, conn.cursor() as cur:
        set_operator_context(cur)
        cur.execute(
            "select erp.reverse_vendor_invoice(%s::uuid,%s)",
            (VENDOR_INVOICE, 'CP6 restore pre-invoice state after serialization proof'),
        )
        conn.commit()


def main():
    report: dict[str, Any] = {
        'status': 'RUNNING',
        'database_scope': 'ISOLATED_CLONE_DESTROYED_BY_WORKFLOW',
        'production_go': False,
        'races': {},
    }

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
        'POST_DELIVERY',
        'select b.id from erp.cutting_distribution_batches b '
        'join erp.cutting_pickups p on p.id=b.pickup_id where b.id=%s::uuid for update of b,p',
        (BATCH,), 'POST_DELIVERY', delivery_payload, group_version,
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
    report['races']['post_receipt'] = run_race(
        'POST_RECEIPT', 'select id from erp.laundry_deliveries where id=%s::uuid for update',
        (delivery_id,), 'POST_RECEIPT', receipt_payload, delivery_version,
        REQUESTS['receipt_winner'], REQUESTS['receipt_loser'], ('STALE_VERSION',),
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

    create_vendor_invoice(receipt_line)
    receipt_version = int(scalar(
        'select row_version from erp.laundry_receipts where id=%s::uuid', (receipt_id,),
    ))
    report['races']['vendor_invoice_vs_reverse_receipt'] = (
        run_vendor_invoice_vs_receipt_reversal(receipt_id, receipt_version)
    )
    reverse_vendor_invoice()

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
    report['races']['post_final_sku'] = run_race(
        'POST_FINAL_SKU', 'select id from erp.laundry_receipts where id=%s::uuid for update',
        (receipt_id,), 'POST_FINAL_SKU', qc_payload, group_version,
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

    invariants = scalar(
        """
        select jsonb_build_object(
          'active_delivery_count',(select count(*) from erp.laundry_deliveries
            where po_id=%s::uuid and status<>'REVERSED'),
          'delivery_size_qty',(select coalesce(sum(x.qty_sent_pcs),0)
            from erp.laundry_delivery_batch_size_lines x
            join erp.laundry_delivery_lines l on l.id=x.delivery_line_id
            where l.delivery_id=%s::uuid),
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
            join erp.fg_lots l on l.id=h.lot_id where l.po_id=%s::uuid and h.is_current),
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
          'vendor_ap_net',(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
            where l.po_id=%s::uuid and l.account_id=erp.account_id('AP_VENDOR')),
          'unbalanced_journals',(select count(*) from(
            select e.id from erp.journal_entries e join erp.journal_lines l on l.journal_entry_id=e.id
            group by e.id having sum(l.debit)<>sum(l.credit)
          ) bad),
          'execution_context_rows',(select count(*) from erp.cp6_laundry_qc_execution_context),
          'winner_idempotency_rows',(select count(*) from erp.idempotency_requests
            where client_request_id=any(%s::uuid[]) and status='COMPLETED'),
          'loser_idempotency_rows',(select count(*) from erp.idempotency_requests
            where client_request_id=any(%s::uuid[]))
        )
        """,
        (
            PO, delivery_id, delivery_id, receipt_id, PO, PO, PO, PO,
            receipt_line, PO, PO, PO, PO, PO,
            [
                REQUESTS['delivery_winner'], REQUESTS['receipt_winner'],
                REQUESTS['qc_winner'], REQUESTS['qc_reverse'],
                REQUESTS['qc_repost_winner'],
            ],
            [
                REQUESTS['delivery_loser'], REQUESTS['receipt_loser'],
                REQUESTS['qc_loser'], REQUESTS['receipt_reverse_loser'],
                REQUESTS['invoice_receipt_reverse_loser'],
            ],
        ),
    )
    expected = {
        'active_delivery_count': 1,
        'delivery_size_qty': 10,
        'posted_receipt_count': 1,
        'receipt_good_qty': 10,
        'posted_qc_count': 1,
        'qc_accounted_qty': 10,
        'fg_stock_qty': 10,
        'current_hpp_total': 70,
        'receipt_cost_status': 'ESTIMATED',
        'laundry_accrual': 70,
        'wip_net': 0,
        'fg_net': 70,
        'accrued_net': -70,
        'vendor_ap_net': 0,
        'unbalanced_journals': 0,
        'execution_context_rows': 0,
        'winner_idempotency_rows': 7,
        'loser_idempotency_rows': 0,
    }
    report['invariants'] = invariants
    report['expected'] = expected
    if invariants != expected:
        raise RuntimeError(f'CP6 serialized-state invariant mismatch: expected={expected}, actual={invariants}')
    report['status'] = 'PASS'
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + '\n', encoding='utf8')
    print('CP6 Laundry/QC/FG concurrency passed: five serialized races, including vendor invoice and Final-SKU versus receipt reversal; no duplicate physical, finance, stock, or HPP fact.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        REPORT.write_text(json.dumps({'status': 'FAIL', 'error': str(exc), 'production_go': False}, indent=2) + '\n', encoding='utf8')
        raise
