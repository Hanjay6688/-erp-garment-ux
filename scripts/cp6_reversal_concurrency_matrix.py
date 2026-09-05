#!/usr/bin/env python3
"""Two-connection CP6 reversal conflict matrix in both meaningful orders."""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable

import psycopg


PGURL = os.environ.get(
    'CP6_RACE_PGURL',
    'postgresql://postgres:postgres@127.0.0.1:54322/cp6_race',
)
REPORT = Path(os.environ.get(
    'CP6_REVERSAL_RACE_REPORT',
    'cp6-reversal-concurrency-matrix.json',
))
HOLD_SECONDS = 1.0
WAIT_FLOOR_SECONDS = 0.5
OPERATOR_AUTH = 'c8c00000-0000-4000-8000-000000000101'
OPERATOR_APP = 'c8c00000-0000-4000-8000-000000000001'
SIZE = 'c8c10000-0000-4000-8000-000000000002'
PRODUCT = 'c8c10000-0000-4000-8000-000000000004'
VENDOR = 'c8c20000-0000-4000-8000-000000000002'
PROCESS = 'c8c20000-0000-4000-8000-000000000003'
LOCATION = 'c8c20000-0000-4000-8000-000000000001'
REQUEST_NAMESPACE = uuid.UUID('ca600000-0000-4000-8000-000000000001')

successful_facades: list[tuple[str, str, bool]] = []
rejected_facades: list[str] = []


def connect():
    return psycopg.connect(PGURL, autocommit=False)


def request_id(label: str) -> str:
    return str(uuid.uuid5(REQUEST_NAMESPACE, label))


def set_operator_claims(cur):
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


def call_facade(
    cur,
    action_name: str,
    payload: dict[str, Any],
    client_request_id: str,
    expected_version: int,
):
    set_operator_context(cur)
    cur.execute(
        'select public.erp_save_laundry_qc_action_v1(%s,%s::jsonb,%s::uuid,%s)',
        (action_name, json.dumps(payload), client_request_id, expected_version),
    )
    return cur.fetchone()[0]


def facade_operation(
    action_name: str,
    payload: dict[str, Any],
    client_request_id: str,
    expected_version: int,
) -> dict[str, Any]:
    return {
        'kind': 'facade',
        'client_request_id': client_request_id,
        'operation_name': f'cp6_laundry_qc_action_v1:{action_name.lower()}',
        'nested_final_sku': action_name == 'POST_FINAL_SKU',
        'call': lambda cur: call_facade(
            cur, action_name, payload, client_request_id, expected_version,
        ),
    }


def invoice_post_operation(
    invoice_id: str,
    deferred_item: dict[str, Any] | None = None,
) -> dict[str, Any]:
    def invoke(cur):
        set_operator_claims(cur)
        # The reverse-receipt-first schedule cannot pre-link a DRAFT item:
        # reverse_laundry_receipt correctly treats every non-REVERSED linked
        # invoice as an existing dependency.  Link the draft inside the
        # competing transaction, then exercise the real production post.
        if deferred_item is not None:
            cur.execute(
                """
                insert into erp.vendor_invoice_items(
                  id,invoice_id,receipt_line_id,description,
                  qty_pcs,actual_rate,actual_amount
                ) values(%s::uuid,%s::uuid,%s::uuid,
                  'CP6 matrix deferred exact receipt',10,%s,%s)
                """,
                (
                    deferred_item['invoice_item_id'], invoice_id,
                    deferred_item['receipt_line_id'], deferred_item['rate'],
                    deferred_item['rate'] * 10,
                ),
            )
        cur.execute('select erp.post_vendor_invoice(%s::uuid)', (invoice_id,))
        return None

    return {'kind': 'invoice', 'call': invoke}


def invoice_reverse_operation(invoice_id: str, reason: str) -> dict[str, Any]:
    def invoke(cur):
        set_operator_claims(cur)
        cur.execute(
            'select erp.reverse_vendor_invoice(%s::uuid,%s)',
            (invoice_id, reason),
        )
        return None

    return {'kind': 'invoice', 'call': invoke}


def remember_success(operation: dict[str, Any]):
    if operation['kind'] == 'facade':
        successful_facades.append((
            operation['client_request_id'],
            operation['operation_name'],
            operation['nested_final_sku'],
        ))


def remember_rejection(operation: dict[str, Any]):
    if operation['kind'] == 'facade':
        rejected_facades.append(operation['client_request_id'])


def single(operation: dict[str, Any]):
    with connect() as conn, conn.cursor() as cur:
        cur.execute("set local lock_timeout='10s'")
        response = operation['call'](cur)
        conn.commit()
    remember_success(operation)
    return response


def cp6flow_prelock(group_id: str) -> Callable[[Any], None]:
    """Acquire the exact shared Potongan fence before a rejected facade."""
    def acquire(cur):
        set_operator_context(cur)
        cur.execute(
            "select pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||%s::text,0))",
            (group_id,),
        )

    return acquire


def invoice_post_prelock(invoice_id: str, group_id: str) -> Callable[[Any], None]:
    """Mirror post_vendor_invoice's header -> shared Potongan lock order."""
    def acquire(cur):
        set_operator_claims(cur)
        cur.execute(
            'select id from erp.vendor_invoices where id=%s::uuid for update',
            (invoice_id,),
        )
        if cur.fetchone() is None:
            raise RuntimeError('Rejected invoice holder header disappeared before race')
        cur.execute(
            "select pg_advisory_xact_lock(hashtextextended('CP6FLOW:'||%s::text,0))",
            (group_id,),
        )

    return acquire


def run_pair(
    name: str,
    holder_operation: dict[str, Any],
    waiter_operation: dict[str, Any],
    waiter_outcome: str,
    allowed_waiter_errors: tuple[str, ...] = (),
    holder_outcome: str = 'PASS',
    allowed_holder_errors: tuple[str, ...] = (),
    holder_prelock: Callable[[Any], None] | None = None,
    holder_prelock_label: str | None = None,
) -> dict[str, Any]:
    """Run production operations, observe the actual blocker, then reconcile."""
    if holder_outcome == 'REJECT' and (
        holder_prelock is None or holder_prelock_label is None
    ):
        raise RuntimeError(
            f'{name}: rejected holder requires an explicit production-order prelock'
        )
    if holder_outcome == 'PASS' and holder_prelock is not None:
        raise RuntimeError(f'{name}: successful holder must acquire locks through runtime')

    holder_ready = threading.Event()
    waiter_started = threading.Event()
    holder: dict[str, Any] = {}
    waiter: dict[str, Any] = {}

    def hold():
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute('select pg_backend_pid()')
                holder['backend_pid'] = cur.fetchone()[0]
                if holder_prelock is not None:
                    holder_prelock(cur)
                    holder['canonical_prelock'] = holder_prelock_label
                    holder_ready.set()
                    if not waiter_started.wait(timeout=10):
                        raise RuntimeError(f'{name}: waiter did not start behind prelock')
                    time.sleep(HOLD_SECONDS)
                holder['response'] = holder_operation['call'](cur)
                if holder_prelock is None:
                    holder_ready.set()
                    time.sleep(HOLD_SECONDS)
            conn.commit()
            holder['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - CI evidence
            holder['error'] = str(exc)
            holder['status'] = (
                'EXPECTED_REJECTION'
                if holder_outcome == 'REJECT'
                and any(token in str(exc) for token in allowed_holder_errors)
                else 'FAIL'
            )
            holder_ready.set()
            conn.rollback()
        finally:
            conn.close()

    def wait():
        holder_ready.wait(timeout=10)
        began = time.monotonic()
        conn = connect()
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute('select pg_backend_pid()')
                waiter['backend_pid'] = cur.fetchone()[0]
                waiter_started.set()
                waiter['response'] = waiter_operation['call'](cur)
            conn.commit()
            waiter['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - expected for reject cases
            conn.rollback()
            waiter['error'] = str(exc)
            waiter['status'] = (
                'EXPECTED_REJECTION'
                if waiter_outcome == 'REJECT'
                and any(token in str(exc) for token in allowed_waiter_errors)
                else 'FAIL'
            )
        finally:
            waiter['elapsed_seconds'] = round(time.monotonic() - began, 3)
            conn.close()

    first = threading.Thread(target=hold, daemon=True)
    second = threading.Thread(target=wait, daemon=True)
    first.start()
    second.start()
    waiter_started.wait(timeout=10)

    lock_observed = False
    deadline = time.monotonic() + HOLD_SECONDS
    while time.monotonic() < deadline:
        if holder.get('backend_pid') and waiter.get('backend_pid'):
            blockers = scalar('select pg_blocking_pids(%s)', (waiter['backend_pid'],))
            if holder['backend_pid'] in blockers:
                lock_observed = True
                break
        time.sleep(0.025)

    first.join(timeout=20)
    second.join(timeout=20)
    if first.is_alive() or second.is_alive():
        raise RuntimeError(f'{name}: thread timeout')
    expected_holder_status = (
        'PASS' if holder_outcome == 'PASS' else 'EXPECTED_REJECTION'
    )
    expected_waiter_status = 'PASS' if waiter_outcome == 'PASS' else 'EXPECTED_REJECTION'
    if (
        holder.get('status') != expected_holder_status
        or waiter.get('status') != expected_waiter_status
    ):
        raise RuntimeError(
            f'{name}: outcome mismatch holder={holder}, waiter={waiter}, '
            f'expected_holder={expected_holder_status}, '
            f'expected_waiter={expected_waiter_status}'
        )
    if waiter.get('elapsed_seconds', 0) < WAIT_FLOOR_SECONDS or not lock_observed:
        raise RuntimeError(
            f'{name}: canonical serialization was not observed; '
            f'blocker={lock_observed}, waiter={waiter}'
        )

    if holder_outcome == 'PASS':
        remember_success(holder_operation)
    else:
        remember_rejection(holder_operation)
    if waiter_outcome == 'PASS':
        remember_success(waiter_operation)
    else:
        remember_rejection(waiter_operation)
    return {
        'holder': holder,
        'waiter': waiter,
        'holder_outcome': holder_outcome,
        'waiter_outcome': waiter_outcome,
        'pg_blocking_pids_observed': lock_observed,
    }


def source(case: str) -> dict[str, Any]:
    value = scalar(
        """
        select jsonb_build_object(
          'po_id',po.id,'group_id',g.id,'group_version',g.row_version,
          'batch_id',b.id
        )
        from erp.production_orders po
        join erp.cutting_groups g on g.po_id=po.id
        join erp.cutting_pickups p on p.cutting_group_id=g.id and p.status='POSTED'
        join erp.cutting_distribution_batches b on b.pickup_id=p.id
        where po.po_number=%s
        """,
        (f'CP6-MX-{case}',),
    )
    if not value:
        raise RuntimeError(f'Missing reversal matrix source {case}')
    return value


def group_version(group_id: str) -> int:
    return int(scalar(
        'select row_version from erp.cutting_groups where id=%s::uuid',
        (group_id,),
    ))


def setup_delivery(case: str) -> dict[str, Any]:
    item = source(case)
    operation = facade_operation(
        'POST_DELIVERY',
        {
            'distribution_batch_id': str(item['batch_id']),
            'vendor_id': VENDOR,
            'wash_process_id': PROCESS,
            'target_dyeing_color': 'NAVY',
            'physical_at': '2026-08-29T11:00:00Z',
            'reason': f'CP6 matrix {case} delivery',
            'notes': 'Independent two-connection reversal schedule',
            'lines': [{'size_id': SIZE, 'qty_sent_pcs': 10}],
        },
        request_id(f'{case}:SETUP:DELIVERY'),
        int(item['group_version']),
    )
    response = single(operation)
    item.update({
        'delivery_id': str(response['delivery_id']),
        'delivery_version': int(response['row_version']),
    })
    item['delivery_size_line_id'] = str(scalar(
        """
        select x.id
        from erp.laundry_delivery_batch_size_lines x
        join erp.laundry_delivery_lines dl on dl.id=x.delivery_line_id
        where dl.delivery_id=%s::uuid
        """,
        (item['delivery_id'],),
    ))
    return item


def receipt_payload(item: dict[str, Any], case: str) -> dict[str, Any]:
    return {
        'delivery_id': item['delivery_id'],
        'wash_process_id': PROCESS,
        'physical_at': '2026-08-29T12:00:00Z',
        'reason': f'CP6 matrix {case} receipt',
        'lines': [{
            'delivery_batch_size_line_id': item['delivery_size_line_id'],
            'qty_good_received': 10,
            'qty_bs_laundry': 0,
            'bs_product_id': None,
        }],
    }


def failed_payload(item: dict[str, Any], case: str) -> dict[str, Any]:
    return {
        'delivery_id': item['delivery_id'],
        'wash_process_id': PROCESS,
        'custody_outcome': 'RETRY_AT_VENDOR',
        'physical_at': '2026-08-29T11:30:00Z',
        'reason': f'CP6 matrix {case} paid failed wash',
        'lines': [{
            'delivery_batch_size_line_id': item['delivery_size_line_id'],
            'qty_attempted_pcs': 10,
        }],
    }


def setup_receipt(case: str) -> dict[str, Any]:
    item = setup_delivery(case)
    response = single(facade_operation(
        'POST_RECEIPT', receipt_payload(item, case),
        request_id(f'{case}:SETUP:RECEIPT'), item['delivery_version'],
    ))
    item.update({
        'receipt_id': str(response['receipt_id']),
        'receipt_version': int(response['receipt_row_version']),
    })
    lines = scalar(
        """
        select jsonb_build_object('receipt_line_id',rl.id,'receipt_size_line_id',rx.id)
        from erp.laundry_receipt_lines rl
        join erp.laundry_receipt_batch_size_lines rx on rx.receipt_line_id=rl.id
        where rl.receipt_id=%s::uuid
        """,
        (item['receipt_id'],),
    )
    item.update({key: str(value) for key, value in lines.items()})
    return item


def qc_payload(
    item: dict[str, Any],
    case: str,
    quantity: int,
    completion_mode_override: str | None = None,
) -> dict[str, Any]:
    return {
        'cutting_group_id': str(item['group_id']),
        'destination_location_id': LOCATION,
        'physical_at': '2026-08-29T13:00:00Z',
        'reason': f'CP6 matrix {case} Final SKU {quantity}',
        'good_qty_pcs': quantity,
        'completion_mode': completion_mode_override or (
            'ALL_READY' if quantity == 10 else 'PARTIAL_SELECTION'
        ),
        'lines': [{
            'final_product_id': PRODUCT,
            'qty_good_pcs': quantity,
            'qty_bs_pcs': 0,
            'source_laundry_receipt_line_id': item['receipt_line_id'],
            'source_laundry_receipt_batch_size_line_id': item['receipt_size_line_id'],
            'notes': 'Exact CP6 reversal matrix source',
        }],
    }


def setup_qc(case: str, quantity: int = 10) -> dict[str, Any]:
    item = setup_receipt(case)
    response = single(facade_operation(
        'POST_FINAL_SKU', qc_payload(item, case, quantity),
        request_id(f'{case}:SETUP:QC'), group_version(str(item['group_id'])),
    ))
    item.update({
        'qc_id': str(response['qc_inspection_id']),
        'qc_version': int(response['qc_row_version']),
    })
    return item


def create_invoice(
    item: dict[str, Any],
    case: str,
    rate: int = 9,
    link_item: bool = True,
) -> str:
    invoice_id = str(uuid.uuid5(REQUEST_NAMESPACE, f'{case}:INVOICE'))
    invoice_item_id = str(uuid.uuid5(REQUEST_NAMESPACE, f'{case}:INVOICE:ITEM'))
    with connect() as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into erp.vendor_invoices(
              id,invoice_number,vendor_id,invoice_date,received_at,due_date,
              status,total_amount,notes,created_by
            ) values(%s::uuid,%s,%s::uuid,'2026-08-29','2026-08-29 12:30:00+00',
              '2026-09-15','DRAFT',%s,'CP6 reversal matrix invoice',%s::uuid)
            """,
            (invoice_id, f'CP6-MX-VI-{case}', VENDOR, rate * 10, OPERATOR_APP),
        )
        if link_item:
            cur.execute(
                """
                insert into erp.vendor_invoice_items(
                  id,invoice_id,receipt_line_id,description,
                  qty_pcs,actual_rate,actual_amount
                ) values(%s::uuid,%s::uuid,%s::uuid,
                  'CP6 matrix exact receipt',10,%s,%s)
                """,
                (invoice_item_id, invoice_id, item['receipt_line_id'], rate, rate * 10),
            )
        conn.commit()
    item['invoice_id'] = invoice_id
    item['invoice_item_id'] = invoice_item_id
    item['invoice_rate'] = rate
    return invoice_id


def post_invoice(invoice_id: str):
    single(invoice_post_operation(invoice_id))


def state(case: str) -> dict[str, Any]:
    return scalar(
        """
        select jsonb_build_object(
          'delivery_status',(select d.status from erp.laundry_deliveries d
            where d.po_id=po.id order by d.created_at desc,d.id desc limit 1),
          'posted_receipts',(select count(*) from erp.laundry_receipts r
            join erp.laundry_deliveries d on d.id=r.delivery_id
            where d.po_id=po.id and r.status='POSTED'),
          'reversed_receipts',(select count(*) from erp.laundry_receipts r
            join erp.laundry_deliveries d on d.id=r.delivery_id
            where d.po_id=po.id and r.status='REVERSED'),
          'failed_attempts',(select count(*) from erp.laundry_failed_wash_attempts a
            join erp.laundry_deliveries d on d.id=a.delivery_id where d.po_id=po.id),
          'posted_qc',(select count(*) from erp.qc_inspections q
            where q.po_id=po.id and q.status='POSTED'),
          'reversed_qc',(select count(*) from erp.qc_inspections q
            where q.po_id=po.id and q.status='REVERSED'),
          'fg_qty',(select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m
            join erp.fg_lots l on l.id=m.lot_id where l.po_id=po.id),
          'current_hpp',(select coalesce(sum(h.total_cost),0) from erp.hpp_versions h
            join erp.fg_lots l on l.id=h.lot_id
            where l.po_id=po.id and l.lot_origin='PRODUCTION' and h.is_current),
          'active_laundry_hpp',(select coalesce(sum(
              c.total_cost*greatest(coalesce(stock.qty,0),0)
                /nullif(h.qty_basis_pcs,0)
            ),0)
            from erp.hpp_versions h
            join erp.hpp_version_components c on c.hpp_version_id=h.id
              and c.component_type='LAUNDRY'
            join erp.fg_lots l on l.id=h.lot_id
            left join lateral(
              select sum(m.qty_signed)::numeric qty
              from erp.fg_stock_movements m where m.lot_id=l.id
            ) stock on true
            where l.po_id=po.id and l.lot_origin='PRODUCTION' and h.is_current),
          'current_cost_state',(select min(h.cost_state) from erp.hpp_versions h
            join erp.fg_lots l on l.id=h.lot_id
            where l.po_id=po.id and l.lot_origin='PRODUCTION' and h.is_current),
          'wip_net',(select coalesce(sum(j.debit-j.credit),0) from erp.journal_lines j
            where j.po_id=po.id and j.account_id=erp.account_id('WIP')),
          'fg_net',(select coalesce(sum(j.debit-j.credit),0) from erp.journal_lines j
            where j.po_id=po.id and j.account_id=erp.account_id('FG_INVENTORY')),
          'accrued_net',(select coalesce(sum(j.debit-j.credit),0) from erp.journal_lines j
            where j.po_id=po.id and j.account_id=erp.account_id('ACCRUED_MANUFACTURING')),
          'invoice_status',(select vi.status from erp.vendor_invoices vi
            join erp.vendor_invoice_items vii on vii.invoice_id=vi.id
            join erp.laundry_receipt_lines rl on rl.id=vii.receipt_line_id
            join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
            join erp.laundry_deliveries d on d.id=dl.delivery_id
            where d.po_id=po.id order by vi.created_at desc,vi.id desc limit 1),
          'invoice_header_status',(select vi.status from erp.vendor_invoices vi
            where vi.invoice_number='CP6-MX-VI-'||substring(po.po_number from 8)
            order by vi.created_at desc,vi.id desc limit 1),
          'invoice_item_count',(select count(*) from erp.vendor_invoice_items vii
            join erp.vendor_invoices vi on vi.id=vii.invoice_id
            where vi.invoice_number='CP6-MX-VI-'||substring(po.po_number from 8)),
          'receipt_cost_status',(select rl.actual_cost_status
            from erp.laundry_receipt_lines rl
            join erp.laundry_receipts r on r.id=rl.receipt_id
            join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
            join erp.laundry_deliveries d on d.id=dl.delivery_id
            where d.po_id=po.id order by r.physical_at desc,r.id desc,rl.id desc limit 1),
          'receipt_cost',(select rl.actual_cost
            from erp.laundry_receipt_lines rl
            join erp.laundry_receipts r on r.id=rl.receipt_id
            join erp.laundry_delivery_lines dl on dl.id=rl.delivery_line_id
            join erp.laundry_deliveries d on d.id=dl.delivery_id
            where d.po_id=po.id order by r.physical_at desc,r.id desc,rl.id desc limit 1)
        )
        from erp.production_orders po where po.po_number=%s
        """,
        (f'CP6-MX-{case}',),
    )


def require(actual: dict[str, Any], **expected):
    mismatches = {key: (expected_value, actual.get(key))
                  for key, expected_value in expected.items()
                  if actual.get(key) != expected_value}
    if mismatches:
        raise RuntimeError(f'State mismatch {mismatches}; full state={actual}')


def main():
    report: dict[str, Any] = {
        'status': 'RUNNING',
        'classification': 'DISPOSABLE_CP6_REVERSAL_RACE_MATRIX',
        'database_scope': 'ISOLATED_CLONE_DESTROYED_BY_WORKFLOW',
        'production_go': False,
        'races': {},
        'states': {},
    }

    item = setup_delivery('RECEIPT_FAILED')
    report['races']['post_receipt_vs_failed_wash'] = run_pair(
        'POST_RECEIPT_VS_FAILED_WASH',
        facade_operation('POST_RECEIPT', receipt_payload(item, 'RECEIPT_FAILED'),
                         request_id('RECEIPT_FAILED:RACE:RECEIPT'), item['delivery_version']),
        facade_operation('POST_FAILED_WASH', failed_payload(item, 'RECEIPT_FAILED'),
                         request_id('RECEIPT_FAILED:RACE:FAILED'), item['delivery_version']),
        'REJECT', ('STALE_VERSION', 'active SENT/PARTIAL_RETURN'),
    )
    report['states']['post_receipt_vs_failed_wash'] = state('RECEIPT_FAILED')
    require(report['states']['post_receipt_vs_failed_wash'], posted_receipts=1, failed_attempts=0)

    item = setup_delivery('REVDEL_RECEIPT')
    report['races']['reverse_delivery_vs_post_receipt'] = run_pair(
        'REVERSE_DELIVERY_VS_POST_RECEIPT',
        facade_operation('REVERSE_DELIVERY', {
            'delivery_id': item['delivery_id'], 'reason': 'CP6 matrix reversal wins receipt',
        }, request_id('REVDEL_RECEIPT:RACE:REVDEL'), item['delivery_version']),
        facade_operation('POST_RECEIPT', receipt_payload(item, 'REVDEL_RECEIPT'),
                         request_id('REVDEL_RECEIPT:RACE:RECEIPT'), item['delivery_version']),
        'REJECT', ('STALE_VERSION', 'active SENT/PARTIAL_RETURN'),
    )
    report['states']['reverse_delivery_vs_post_receipt'] = state('REVDEL_RECEIPT')
    require(report['states']['reverse_delivery_vs_post_receipt'], delivery_status='REVERSED', posted_receipts=0)

    item = setup_delivery('RECEIPT_REVDEL')
    report['races']['post_receipt_vs_reverse_delivery'] = run_pair(
        'POST_RECEIPT_VS_REVERSE_DELIVERY',
        facade_operation('POST_RECEIPT', receipt_payload(item, 'RECEIPT_REVDEL'),
                         request_id('RECEIPT_REVDEL:RACE:RECEIPT'), item['delivery_version']),
        facade_operation('REVERSE_DELIVERY', {
            'delivery_id': item['delivery_id'], 'reason': 'CP6 matrix receipt blocks reversal',
        }, request_id('RECEIPT_REVDEL:RACE:REVDEL'), item['delivery_version']),
        'REJECT', ('STALE_VERSION', 'memiliki penerimaan aktif'),
    )
    report['states']['post_receipt_vs_reverse_delivery'] = state('RECEIPT_REVDEL')
    require(report['states']['post_receipt_vs_reverse_delivery'], posted_receipts=1)

    item = setup_delivery('REVDEL_FAILED')
    report['races']['reverse_delivery_vs_failed_wash'] = run_pair(
        'REVERSE_DELIVERY_VS_FAILED_WASH',
        facade_operation('REVERSE_DELIVERY', {
            'delivery_id': item['delivery_id'], 'reason': 'CP6 matrix reversal wins failed wash',
        }, request_id('REVDEL_FAILED:RACE:REVDEL'), item['delivery_version']),
        facade_operation('POST_FAILED_WASH', failed_payload(item, 'REVDEL_FAILED'),
                         request_id('REVDEL_FAILED:RACE:FAILED'), item['delivery_version']),
        'REJECT', ('STALE_VERSION', 'active SENT/PARTIAL_RETURN'),
    )
    report['states']['reverse_delivery_vs_failed_wash'] = state('REVDEL_FAILED')
    require(report['states']['reverse_delivery_vs_failed_wash'], delivery_status='REVERSED', failed_attempts=0)

    item = setup_delivery('FAILED_REVDEL')
    report['races']['failed_wash_vs_reverse_delivery'] = run_pair(
        'FAILED_WASH_VS_REVERSE_DELIVERY',
        facade_operation('POST_FAILED_WASH', failed_payload(item, 'FAILED_REVDEL'),
                         request_id('FAILED_REVDEL:RACE:FAILED'), item['delivery_version']),
        facade_operation('REVERSE_DELIVERY', {
            'delivery_id': item['delivery_id'], 'reason': 'CP6 matrix failed wash blocks reversal',
        }, request_id('FAILED_REVDEL:RACE:REVDEL'), item['delivery_version']),
        'REJECT', ('STALE_VERSION', 'memiliki penerimaan aktif'),
    )
    report['states']['failed_wash_vs_reverse_delivery'] = state('FAILED_REVDEL')
    require(report['states']['failed_wash_vs_reverse_delivery'], posted_receipts=1, failed_attempts=1)

    item = setup_receipt('REVRECEIPT_INVOICE')
    invoice_id = create_invoice(item, 'REVRECEIPT_INVOICE', link_item=False)
    report['races']['reverse_receipt_vs_vendor_invoice'] = run_pair(
        'REVERSE_RECEIPT_VS_VENDOR_INVOICE',
        facade_operation('REVERSE_RECEIPT', {
            'receipt_id': item['receipt_id'], 'reason': 'CP6 matrix receipt reversal wins invoice',
        }, request_id('REVRECEIPT_INVOICE:RACE:REVRECEIPT'), item['receipt_version']),
        invoice_post_operation(invoice_id, {
            'invoice_item_id': item['invoice_item_id'],
            'receipt_line_id': item['receipt_line_id'],
            'rate': item['invoice_rate'],
        }), 'REJECT',
        (
            'Vendor invoice can only bill POSTED laundry receipt lines',
            'Vendor invoice lifecycle lost its authoritative POSTED Laundry receipt',
        ),
    )
    report['states']['reverse_receipt_vs_vendor_invoice'] = state('REVRECEIPT_INVOICE')
    require(
        report['states']['reverse_receipt_vs_vendor_invoice'],
        reversed_receipts=1,
        invoice_header_status='DRAFT',
        invoice_item_count=0,
    )

    item = setup_receipt('REVRECEIPT_QC')
    report['races']['reverse_receipt_vs_final_sku'] = run_pair(
        'REVERSE_RECEIPT_VS_FINAL_SKU',
        facade_operation('REVERSE_RECEIPT', {
            'receipt_id': item['receipt_id'], 'reason': 'CP6 matrix receipt reversal wins Final SKU',
        }, request_id('REVRECEIPT_QC:RACE:REVRECEIPT'), item['receipt_version']),
        facade_operation('POST_FINAL_SKU', qc_payload(item, 'REVRECEIPT_QC', 10),
                         request_id('REVRECEIPT_QC:RACE:QC'), group_version(str(item['group_id']))),
        'REJECT', ('STALE_VERSION', 'authoritative POSTED Laundry receipt'),
    )
    report['states']['reverse_receipt_vs_final_sku'] = state('REVRECEIPT_QC')
    require(report['states']['reverse_receipt_vs_final_sku'], reversed_receipts=1, posted_qc=0, fg_qty=0)

    item = setup_qc('REVQC_REVRECEIPT')
    report['races']['reverse_qc_vs_reverse_receipt'] = run_pair(
        'REVERSE_QC_VS_REVERSE_RECEIPT',
        facade_operation('REVERSE_FINAL_SKU', {
            'qc_inspection_id': item['qc_id'], 'reason': 'CP6 matrix reverse QC before receipt',
        }, request_id('REVQC_REVRECEIPT:RACE:REVQC'), item['qc_version']),
        facade_operation('REVERSE_RECEIPT', {
            'receipt_id': item['receipt_id'], 'reason': 'CP6 matrix receipt reversal after QC',
        }, request_id('REVQC_REVRECEIPT:RACE:REVRECEIPT'), item['receipt_version']),
        'PASS',
    )
    report['states']['reverse_qc_vs_reverse_receipt'] = state('REVQC_REVRECEIPT')
    require(report['states']['reverse_qc_vs_reverse_receipt'], reversed_receipts=1, reversed_qc=1, fg_qty=0)

    item = setup_qc('REVRECEIPT_REVQC')
    report['races']['reverse_receipt_vs_reverse_qc'] = run_pair(
        'REVERSE_RECEIPT_VS_REVERSE_QC',
        facade_operation('REVERSE_RECEIPT', {
            'receipt_id': item['receipt_id'],
            'reason': 'CP6 matrix receipt reversal rejects before QC reversal',
        }, request_id('REVRECEIPT_REVQC:RACE:REVRECEIPT'), item['receipt_version']),
        facade_operation('REVERSE_FINAL_SKU', {
            'qc_inspection_id': item['qc_id'],
            'reason': 'CP6 matrix QC reversal follows rejected receipt reversal',
        }, request_id('REVRECEIPT_REVQC:RACE:REVQC'), item['qc_version']),
        'PASS',
        holder_outcome='REJECT',
        allowed_holder_errors=('Penerimaan laundry ini sudah dipakai QC',),
        holder_prelock=cp6flow_prelock(str(item['group_id'])),
        holder_prelock_label='CP6FLOW_GROUP',
    )
    report['states']['reverse_receipt_vs_reverse_qc'] = state('REVRECEIPT_REVQC')
    require(
        report['states']['reverse_receipt_vs_reverse_qc'],
        posted_receipts=1, reversed_receipts=0, posted_qc=0, reversed_qc=1, fg_qty=0,
    )

    # The inverse invoice-replacement order is intentionally asymmetric: B
    # cannot post while A is still active. B must reject under its real
    # canonical locks; A's reversal then waits, succeeds, and restores the
    # live ESTIMATED 70 receipt state. This is evidence, not a synthetic claim
    # that both mutually exclusive invoice posts can succeed.
    item = setup_receipt('REPLACEMENT_INVERSE')
    invoice_a = create_invoice(item, 'REPLACEMENT_INVERSE_A', rate=9)
    post_invoice(invoice_a)
    invoice_b = create_invoice(item, 'REPLACEMENT_INVERSE_B', rate=10)
    report['races']['replacement_post_vs_invoice_reversal'] = run_pair(
        'REPLACEMENT_POST_VS_INVOICE_REVERSAL',
        invoice_post_operation(invoice_b),
        invoice_reverse_operation(
            invoice_a, 'CP6 inverse replacement schedule restores estimate',
        ),
        'PASS',
        holder_outcome='REJECT',
        allowed_holder_errors=(
            'Laundry receipt line is already billed by another active vendor invoice',
        ),
        holder_prelock=invoice_post_prelock(invoice_b, str(item['group_id'])),
        holder_prelock_label='INVOICE_HEADER_THEN_CP6FLOW',
    )
    report['states']['replacement_post_vs_invoice_reversal'] = scalar(
        """
        select jsonb_build_object(
          'invoice_a_status',(select status from erp.vendor_invoices where id=%s::uuid),
          'invoice_b_status',(select status from erp.vendor_invoices where id=%s::uuid),
          'receipt_cost_status',(select actual_cost_status from erp.laundry_receipt_lines
            where id=%s::uuid),
          'receipt_cost',(select actual_cost from erp.laundry_receipt_lines
            where id=%s::uuid)
        )
        """,
        (invoice_a, invoice_b, item['receipt_line_id'], item['receipt_line_id']),
    )
    require(
        report['states']['replacement_post_vs_invoice_reversal'],
        invoice_a_status='REVERSED', invoice_b_status='DRAFT',
        receipt_cost_status='ESTIMATED', receipt_cost=70,
    )

    for case, race_name, qc_first in [
        ('REVQC_INVOICE', 'reverse_qc_vs_vendor_invoice', True),
        ('INVOICE_REVQC', 'vendor_invoice_vs_reverse_qc', False),
    ]:
        item = setup_qc(case)
        invoice_id = create_invoice(item, case)
        reverse_qc = facade_operation('REVERSE_FINAL_SKU', {
            'qc_inspection_id': item['qc_id'], 'reason': f'CP6 matrix {race_name}',
        }, request_id(f'{case}:RACE:REVQC'), item['qc_version'])
        invoice_post = invoice_post_operation(invoice_id)
        report['races'][race_name] = run_pair(
            race_name.upper(),
            reverse_qc if qc_first else invoice_post,
            invoice_post if qc_first else reverse_qc,
            'PASS',
        )
        report['states'][race_name] = state(case)
        require(report['states'][race_name], reversed_qc=1, fg_qty=0,
                invoice_status='POSTED', receipt_cost_status='FINAL', receipt_cost=90)

    for case, race_name, qc_first in [
        ('REVQC_INVOICE_REV', 'reverse_qc_vs_vendor_invoice_reversal', True),
        ('INVOICE_REV_REVQC', 'vendor_invoice_reversal_vs_reverse_qc', False),
    ]:
        item = setup_qc(case)
        invoice_id = create_invoice(item, case)
        post_invoice(invoice_id)
        reverse_qc = facade_operation('REVERSE_FINAL_SKU', {
            'qc_inspection_id': item['qc_id'], 'reason': f'CP6 matrix {race_name}',
        }, request_id(f'{case}:RACE:REVQC'), item['qc_version'])
        invoice_reverse = invoice_reverse_operation(
            invoice_id, f'CP6 matrix {race_name}',
        )
        report['races'][race_name] = run_pair(
            race_name.upper(),
            reverse_qc if qc_first else invoice_reverse,
            invoice_reverse if qc_first else reverse_qc,
            'PASS',
        )
        report['states'][race_name] = state(case)
        require(report['states'][race_name], reversed_qc=1, fg_qty=0,
                invoice_status='REVERSED', receipt_cost_status='ESTIMATED', receipt_cost=70)

    item = setup_qc('REVQC_POSTQC', quantity=5)
    report['states']['partial_hpp_before_reverse_qc_vs_post_final_sku'] = state(
        'REVQC_POSTQC',
    )
    require(
        report['states']['partial_hpp_before_reverse_qc_vs_post_final_sku'],
        posted_qc=1, fg_qty=5, current_hpp=35, active_laundry_hpp=35,
        current_cost_state='ESTIMATED', fg_net=35, wip_net=35, accrued_net=-70,
    )
    report['races']['reverse_qc_vs_post_final_sku'] = run_pair(
        'REVERSE_QC_VS_POST_FINAL_SKU',
        facade_operation('REVERSE_FINAL_SKU', {
            'qc_inspection_id': item['qc_id'], 'reason': 'CP6 matrix reverse QC wins repost',
        }, request_id('REVQC_POSTQC:RACE:REVQC'), item['qc_version']),
        facade_operation('POST_FINAL_SKU', qc_payload(item, 'REVQC_POSTQC', 5),
                         request_id('REVQC_POSTQC:RACE:POSTQC'), group_version(str(item['group_id']))),
        'PASS',
    )
    report['states']['reverse_qc_vs_post_final_sku'] = state('REVQC_POSTQC')
    # A reversed historical lot keeps an immutable HPP version, so current_hpp
    # covers both historical lots. Only the active five-piece lot may remain in
    # FG: 35 Laundry in FG and the other 35 still in WIP.
    require(report['states']['reverse_qc_vs_post_final_sku'], posted_qc=1, reversed_qc=1,
            fg_qty=5, current_hpp=70, active_laundry_hpp=35,
            fg_net=35, wip_net=35, accrued_net=-70)

    item = setup_qc('POSTQC_REVQC', quantity=5)
    report['states']['partial_hpp_before_post_final_sku_vs_reverse_qc'] = state(
        'POSTQC_REVQC',
    )
    require(
        report['states']['partial_hpp_before_post_final_sku_vs_reverse_qc'],
        posted_qc=1, fg_qty=5, current_hpp=35, active_laundry_hpp=35,
        current_cost_state='ESTIMATED', fg_net=35, wip_net=35, accrued_net=-70,
    )
    report['races']['post_final_sku_vs_reverse_qc'] = run_pair(
        'POST_FINAL_SKU_VS_REVERSE_QC',
        # Before the competing reversal commits, this second 5-pcs post
        # consumes the full authoritative ready balance.  Its operator intent
        # must therefore be ALL_READY at post time; after its commit, reversal
        # of the older 5-pcs QC legitimately opens a new remainder.
        facade_operation('POST_FINAL_SKU', qc_payload(
            item, 'POSTQC_REVQC', 5, completion_mode_override='ALL_READY',
        ),
                         request_id('POSTQC_REVQC:RACE:POSTQC'), group_version(str(item['group_id']))),
        facade_operation('REVERSE_FINAL_SKU', {
            'qc_inspection_id': item['qc_id'], 'reason': 'CP6 matrix repost wins reverse QC',
        }, request_id('POSTQC_REVQC:RACE:REVQC'), item['qc_version']),
        'PASS',
    )
    report['states']['post_final_sku_vs_reverse_qc'] = state('POSTQC_REVQC')
    require(report['states']['post_final_sku_vs_reverse_qc'], posted_qc=1, reversed_qc=1,
            fg_qty=5, current_hpp=70, active_laundry_hpp=35,
            fg_net=35, wip_net=35, accrued_net=-70)

    completed_ids = [row[0] for row in successful_facades]
    completed_operations = [row[1] for row in successful_facades]
    nested_ids = [row[0] for row in successful_facades if row[2]]
    idempotency = scalar(
        """
        with expected(client_request_id,operation_name) as(
          select * from unnest(%s::uuid[],%s::text[])
        ), nested(client_request_id) as(select unnest(%s::uuid[])),
        rejected(client_request_id) as(select unnest(%s::uuid[]))
        select jsonb_build_object(
          'expected_facade_rows',(select count(*) from erp.idempotency_requests i
            join expected e using(client_request_id,operation_name)
            where i.status='COMPLETED'),
          'expected_facade_ids',(select count(distinct i.client_request_id)
            from erp.idempotency_requests i join expected e
              using(client_request_id,operation_name) where i.status='COMPLETED'),
          'expected_nested_rows',(select count(*) from erp.idempotency_requests i
            join nested n using(client_request_id)
            where i.operation_name='post_fg_partial_completion_v2' and i.status='COMPLETED'),
          'rejected_rows',(select count(*) from erp.idempotency_requests i
            join rejected r using(client_request_id)),
          'execution_context_rows',(select count(*) from erp.cp6_laundry_qc_execution_context),
          'unbalanced_journals',(select count(*) from(
            select e.id from erp.journal_entries e
            join erp.journal_lines l on l.journal_entry_id=e.id
            group by e.id having sum(l.debit)<>sum(l.credit)
          ) x),
          'matrix_vendor_ap',(select coalesce(sum(l.credit-l.debit),0)
            from erp.journal_lines l
            where l.vendor_id=%s::uuid and l.account_id=erp.account_id('AP_VENDOR'))
        )
        """,
        (completed_ids, completed_operations, nested_ids, rejected_facades, VENDOR),
    )
    expected_idempotency = {
        'expected_facade_rows': len(successful_facades),
        'expected_facade_ids': len(successful_facades),
        'expected_nested_rows': len(nested_ids),
        'rejected_rows': 0,
        'execution_context_rows': 0,
        'unbalanced_journals': 0,
        # Two matrix schedules deliberately leave one 90-unit invoice posted.
        # The original CP6 race harness ends at AP zero before this matrix.
        'matrix_vendor_ap': 180,
    }
    if idempotency != expected_idempotency:
        raise RuntimeError(
            f'CP6 reversal matrix residue/ledger mismatch: '
            f'expected={expected_idempotency}, actual={idempotency}'
        )
    report['idempotency_and_ledger'] = idempotency
    report['idempotency_expected'] = expected_idempotency
    report['race_count'] = len(report['races'])
    report['all_blockers_observed'] = all(
        value['pg_blocking_pids_observed'] for value in report['races'].values()
    )
    report['status'] = 'PASS'
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')


try:
    main()
except Exception as error:
    failure = {
        'status': 'FAIL',
        'classification': 'DISPOSABLE_CP6_REVERSAL_RACE_MATRIX',
        'error': str(error),
        'production_go': False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(failure, indent=2, sort_keys=True) + '\n')
    raise

print('CP6 reversal matrix passed: sixteen serialized schedules in both meaningful orders; all blocker PIDs observed.')
