#!/usr/bin/env python3
"""Nine real two-connection races for CP6 Laundry -> QC -> FG."""
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
FLOW_LOCK_SQL = (
    "select pg_advisory_xact_lock("
    "hashtextextended('CP6FLOW:'||(%s::uuid)::text,0))"
)

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
VENDOR_INVOICE_QC = 'c8c70000-0000-4000-8000-000000000003'
VENDOR_INVOICE_QC_ITEM = 'c8c70000-0000-4000-8000-000000000004'
VENDOR_INVOICE_QC_AFTER = 'c8c70000-0000-4000-8000-000000000005'
VENDOR_INVOICE_QC_AFTER_ITEM = 'c8c70000-0000-4000-8000-000000000006'

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
                set_operator_context(cur)
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
                set_operator_context(cur)
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
                set_operator_context(cur)
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


def create_vendor_invoice(
    receipt_line: str,
    invoice_id: str,
    item_id: str,
    invoice_number: str,
    actual_rate: int,
):
    total = actual_rate * 10
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into erp.vendor_invoices(
              id,invoice_number,vendor_id,invoice_date,received_at,due_date,
              status,total_amount,notes,created_by
            ) values(%s::uuid,%s,%s::uuid,'2026-09-01',
              '2026-09-01 12:30:00+00','2026-09-15','DRAFT',%s,
              'CP6 invoice/reversal serialization proof',%s::uuid);
            insert into erp.vendor_invoice_items(
              id,invoice_id,receipt_line_id,description,qty_pcs,actual_rate,actual_amount
            ) values(%s::uuid,%s::uuid,%s::uuid,
              'CP6 exact posted receipt',10,%s,%s)
            """,
            (
                invoice_id, invoice_number, VENDOR, total, OPERATOR_APP,
                item_id, invoice_id, receipt_line, actual_rate, total,
            ),
        )
        conn.commit()


def reverse_vendor_invoice(invoice_id: str, reason: str):
    with connect() as conn, conn.cursor() as cur:
        set_operator_context(cur)
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
          'vendor_ap_net',(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l
            where l.po_id=%s::uuid and l.account_id=erp.account_id('AP_VENDOR')),
          'unbalanced_journals',(select count(*) from(
            select e.id from erp.journal_entries e join erp.journal_lines l on l.journal_entry_id=e.id
            group by e.id having sum(l.debit)<>sum(l.credit)
          ) bad)
        )
        """,
        (
            invoice_id, receipt_line, receipt_line, PO, PO, PO,
            PO, PO, PO, PO, PO,
        ),
    )


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
        'POST_RECEIPT', FLOW_LOCK_SQL, (GROUP,),
        'POST_RECEIPT', receipt_payload, delivery_version,
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
        'POST_FINAL_SKU', FLOW_LOCK_SQL, (GROUP,),
        'POST_FINAL_SKU', qc_payload, group_version,
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
            PO, receipt_line, PO, PO, PO, PO, PO,
            [
                REQUESTS['delivery_winner'], REQUESTS['receipt_winner'],
                REQUESTS['invoice_qc_post'], REQUESTS['invoice_qc_reverse'],
                REQUESTS['invoice_reversal_qc_post'],
                REQUESTS['invoice_reversal_qc_reverse'],
                REQUESTS['qc_before_invoice_post'],
                REQUESTS['qc_before_invoice_reverse'],
                REQUESTS['qc_before_invoice_reversal_post'],
                REQUESTS['qc_before_invoice_reversal_reverse'],
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
        'voided_hpp_history_lots': 5,
        'receipt_cost_status': 'ESTIMATED',
        'laundry_accrual': 70,
        'wip_net': 0,
        'fg_net': 70,
        'accrued_net': -70,
        'vendor_ap_net': 0,
        'unbalanced_journals': 0,
        'execution_context_rows': 0,
        'winner_idempotency_rows': 19,
        'loser_idempotency_rows': 0,
    }
    report['invariants'] = invariants
    report['expected'] = expected
    if invariants != expected:
        raise RuntimeError(f'CP6 serialized-state invariant mismatch: expected={expected}, actual={invariants}')
    report['status'] = 'PASS'
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + '\n', encoding='utf8')
    print('CP6 Laundry/QC/FG concurrency passed: nine serialized races, including both invoice post/reversal scheduling directions versus Final-SKU and source reversal; no duplicate physical, finance, stock, or HPP fact.')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        REPORT.write_text(json.dumps({'status': 'FAIL', 'error': str(exc), 'production_go': False}, indent=2) + '\n', encoding='utf8')
        raise
