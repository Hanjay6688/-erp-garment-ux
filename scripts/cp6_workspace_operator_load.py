#!/usr/bin/env python3
"""Eight-operator CP6 write/load proof on independent authoritative sources."""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import psycopg


PGURL = os.environ.get(
    'CP6_RACE_PGURL',
    'postgresql://postgres:postgres@127.0.0.1:54322/cp6_race',
)
REPORT = Path(os.environ.get(
    'CP6_SCALE_LOAD_REPORT', 'cp6-workspace-operator-load.json',
))
CASES = [f'SCALE_OP_{index:02d}' for index in range(1, 9)]
SIZE = 'c8c10000-0000-4000-8000-000000000002'
PRODUCT = 'c8c10000-0000-4000-8000-000000000004'
VENDOR = 'c8c20000-0000-4000-8000-000000000002'
PROCESS = 'c8c20000-0000-4000-8000-000000000003'
LOCATION = 'c8c20000-0000-4000-8000-000000000001'
REQUEST_NAMESPACE = uuid.UUID('ca6f0000-0000-4000-8000-000000000001')
ACTION_BUDGET_MS = 5000.0
TOTAL_BUDGET_MS = 10000.0
OBSERVED_TRANSACTION_AGE_BUDGET_SECONDS = 5.0


def md5_uuid(value: str) -> str:
    return str(uuid.UUID(hashlib.md5(value.encode()).hexdigest()))


def request_id(label: str) -> str:
    return str(uuid.uuid5(REQUEST_NAMESPACE, label))


def connect(application_name: str = 'cp6-scale-control'):
    return psycopg.connect(
        PGURL, autocommit=False, application_name=application_name,
    )


def set_actor(cur, index: int):
    claims = json.dumps({
        'sub': md5_uuid(f'CP6-SCALE-AUTH-{index:02d}'),
        'role': 'authenticated',
    })
    cur.execute("select set_config('request.jwt.claims',%s,true)", (claims,))
    cur.execute('set local role authenticated')


def facade(cur, action_name: str, payload: dict[str, Any], req: str, version: int):
    cur.execute(
        'select public.erp_save_laundry_qc_action_v1(%s,%s::jsonb,%s::uuid,%s)',
        (action_name, json.dumps(payload), req, version),
    )
    return cur.fetchone()[0]


def scalar(query: str, params=()):
    with connect() as conn, conn.cursor() as cur:
        cur.execute(query, params)
        row = cur.fetchone()
        conn.commit()
        return row[0] if row else None


def setup_source(case: str, index: int) -> dict[str, Any]:
    source = scalar(
        """
        select jsonb_build_object(
          'po_id',po.id,'group_id',g.id,'group_version',g.row_version,'batch_id',b.id
        )
        from erp.production_orders po
        join erp.cutting_groups g on g.po_id=po.id
        join erp.cutting_pickups p on p.cutting_group_id=g.id and p.status='POSTED'
        join erp.cutting_distribution_batches b on b.pickup_id=p.id
        where po.po_number=%s
        """,
        (f'CP6-MX-{case}',),
    )
    if not source:
        raise RuntimeError(f'Missing scale source {case}')
    with connect(f'cp6-scale-setup-{index:02d}') as conn, conn.cursor() as cur:
        set_actor(cur, index)
        delivery = facade(cur, 'POST_DELIVERY', {
            'distribution_batch_id': str(source['batch_id']),
            'vendor_id': VENDOR,
            'wash_process_id': PROCESS,
            'target_dyeing_color': 'NAVY',
            'physical_at': '2026-08-30T11:00:00Z',
            'reason': f'CP6 scale operator {index:02d} delivery',
            'notes': 'Real multi-operator load source',
            'lines': [{'size_id': SIZE, 'qty_sent_pcs': 10}],
        }, request_id(f'{case}:DELIVERY'), int(source['group_version']))
        conn.commit()

    delivery_line = scalar(
        """
        select x.id from erp.laundry_delivery_batch_size_lines x
        join erp.laundry_delivery_lines dl on dl.id=x.delivery_line_id
        where dl.delivery_id=%s::uuid
        """,
        (str(delivery['delivery_id']),),
    )
    with connect(f'cp6-scale-setup-{index:02d}') as conn, conn.cursor() as cur:
        set_actor(cur, index)
        receipt = facade(cur, 'POST_RECEIPT', {
            'delivery_id': str(delivery['delivery_id']),
            'wash_process_id': PROCESS,
            'physical_at': '2026-08-30T12:00:00Z',
            'reason': f'CP6 scale operator {index:02d} receipt',
            'lines': [{
                'delivery_batch_size_line_id': str(delivery_line),
                'qty_good_received': 10,
                'qty_bs_laundry': 0,
                'bs_product_id': None,
            }],
        }, request_id(f'{case}:RECEIPT'), int(delivery['row_version']))
        conn.commit()

    lineage = scalar(
        """
        select jsonb_build_object('receipt_line_id',rl.id,'receipt_size_line_id',rx.id)
        from erp.laundry_receipt_lines rl
        join erp.laundry_receipt_batch_size_lines rx on rx.receipt_line_id=rl.id
        where rl.receipt_id=%s::uuid
        """,
        (str(receipt['receipt_id']),),
    )
    return {
        **source,
        **lineage,
        'group_version': int(scalar(
            'select row_version from erp.cutting_groups where id=%s::uuid',
            (str(source['group_id']),),
        )),
    }


def main():
    sources = [setup_source(case, index) for index, case in enumerate(CASES, 1)]
    barrier = threading.Barrier(len(CASES))
    release_commit = threading.Event()
    action_done = [threading.Event() for _ in CASES]
    outcomes: list[dict[str, Any]] = [{} for _ in CASES]

    def worker(index: int, case: str, source: dict[str, Any]):
        outcome = outcomes[index - 1]
        started = time.monotonic()
        conn = connect(f'cp6-scale-op-{index:02d}')
        try:
            with conn.cursor() as cur:
                cur.execute("set local lock_timeout='10s'")
                cur.execute("set local statement_timeout='10s'")
                set_actor(cur, index)
                cur.execute(
                    'select public.erp_search_final_sku_products_v1(%s::uuid,%s::timestamptz,%s,null,25)',
                    (str(source['receipt_size_line_id']), '2026-08-30T13:00:00Z', 'CP6-RACE-SKU'),
                )
                page = cur.fetchone()[0]
                if [row['id'] for row in page['products']] != [PRODUCT]:
                    raise RuntimeError(f'{case}: resolver mismatch {page}')
                barrier.wait(timeout=15)
                action_started = time.monotonic()
                response = facade(cur, 'POST_FINAL_SKU', {
                    'cutting_group_id': str(source['group_id']),
                    'destination_location_id': LOCATION,
                    'physical_at': '2026-08-30T13:00:00Z',
                    'reason': f'CP6 concurrent scale operator {index:02d}',
                    'good_qty_pcs': 10,
                    'completion_mode': 'ALL_READY',
                    'lines': [{
                        'final_product_id': PRODUCT,
                        'qty_good_pcs': 10,
                        'qty_bs_pcs': 0,
                        'source_laundry_receipt_line_id': str(source['receipt_line_id']),
                        'source_laundry_receipt_batch_size_line_id': str(source['receipt_size_line_id']),
                        'notes': 'Independent source under eight-operator write load',
                    }],
                }, request_id(f'{case}:FINAL_SKU'), int(source['group_version']))
                outcome.update({
                    'status': 'ACTION_DONE',
                    'action_ms': round((time.monotonic() - action_started) * 1000, 3),
                    'qc_inspection_id': str(response['qc_inspection_id']),
                })
                action_done[index - 1].set()
                if not release_commit.wait(timeout=15):
                    raise RuntimeError(f'{case}: commit release timeout')
            conn.commit()
            outcome['status'] = 'PASS'
        except Exception as exc:  # pragma: no cover - CI evidence
            conn.rollback()
            outcome['status'] = 'FAIL'
            outcome['error'] = str(exc)
            action_done[index - 1].set()
            release_commit.set()
        finally:
            outcome['total_ms'] = round((time.monotonic() - started) * 1000, 3)
            conn.close()

    threads = [
        threading.Thread(target=worker, args=(index, case, source), daemon=True)
        for index, (case, source) in enumerate(zip(CASES, sources), 1)
    ]
    for thread in threads:
        thread.start()
    for event in action_done:
        if not event.wait(timeout=20):
            release_commit.set()
            raise RuntimeError('Eight-operator actions did not all reach the commit fence')

    observation = scalar(
        """
        select jsonb_build_object(
          'active_transactions',count(*),
          'all_idle_in_transaction',bool_and(state='idle in transaction'),
          'max_transaction_age_seconds',round(max(extract(epoch from(clock_timestamp()-xact_start))::numeric),3),
          'blocked_transactions',count(*) filter(where cardinality(pg_blocking_pids(pid))>0),
          'backend_pids',jsonb_agg(pid order by application_name)
        )
        from pg_stat_activity
        where application_name like 'cp6-scale-op-%' and xact_start is not null
        """
    )
    release_commit.set()
    for thread in threads:
        thread.join(timeout=20)
    if any(thread.is_alive() for thread in threads):
        raise RuntimeError('Eight-operator commit threads did not terminate')
    if any(outcome.get('status') != 'PASS' for outcome in outcomes):
        raise RuntimeError(f'Eight-operator write failure: {outcomes}')

    action_latencies = [float(outcome['action_ms']) for outcome in outcomes]
    p95_action_ms = max(action_latencies)  # conservative for a bounded n=8 proof
    max_total_ms = max(float(outcome['total_ms']) for outcome in outcomes)
    if observation != {
        **observation,
        'active_transactions': 8,
        'all_idle_in_transaction': True,
        'blocked_transactions': 0,
    }:
        raise RuntimeError(f'Multi-operator overlap observation mismatch: {observation}')
    if float(observation['max_transaction_age_seconds']) >= OBSERVED_TRANSACTION_AGE_BUDGET_SECONDS:
        raise RuntimeError(f'Multi-operator transaction-age budget exceeded: {observation}')
    if p95_action_ms >= ACTION_BUDGET_MS or max_total_ms >= TOTAL_BUDGET_MS:
        raise RuntimeError(
            f'Multi-operator latency budget exceeded: p95={p95_action_ms}, max={max_total_ms}'
        )

    po_numbers = [f'CP6-MX-{case}' for case in CASES]
    final_request_ids = [request_id(f'{case}:FINAL_SKU') for case in CASES]
    reconciliation = scalar(
        """
        with target_po as(select id from erp.production_orders where po_number=any(%s)),
        target_request as(select unnest(%s::uuid[]) client_request_id)
        select jsonb_build_object(
          'posted_qc',(select count(*) from erp.qc_inspections where po_id in(select id from target_po) and status='POSTED'),
          'fg_qty',(select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m
            join erp.fg_lots l on l.id=m.lot_id where l.po_id in(select id from target_po)),
          'current_hpp',(select coalesce(sum(h.total_cost),0) from erp.hpp_versions h
            join erp.fg_lots l on l.id=h.lot_id
            where l.po_id in(select id from target_po) and l.lot_origin='PRODUCTION' and h.is_current),
          'wip_net',(select coalesce(sum(j.debit-j.credit),0) from erp.journal_lines j
            where j.po_id in(select id from target_po) and j.account_id=erp.account_id('WIP')),
          'fg_net',(select coalesce(sum(j.debit-j.credit),0) from erp.journal_lines j
            where j.po_id in(select id from target_po) and j.account_id=erp.account_id('FG_INVENTORY')),
          'accrued_net',(select coalesce(sum(j.debit-j.credit),0) from erp.journal_lines j
            where j.po_id in(select id from target_po) and j.account_id=erp.account_id('ACCRUED_MANUFACTURING')),
          'final_idempotency_rows',(select count(*) from erp.idempotency_requests i
            join target_request r using(client_request_id) where i.status='COMPLETED'),
          'execution_context_rows',(select count(*) from erp.cp6_laundry_qc_execution_context),
          'unbalanced_journals',(select count(*) from(
            select e.id from erp.journal_entries e join erp.journal_lines j
              on j.journal_entry_id=e.id
            where j.po_id in(select id from target_po)
            group by e.id having sum(j.debit)<>sum(j.credit)
          ) bad)
        )
        """,
        (po_numbers, final_request_ids),
    )
    expected = {
        'posted_qc': 8,
        'fg_qty': 80,
        'current_hpp': 560,
        'wip_net': 0,
        'fg_net': 560,
        'accrued_net': -560,
        'final_idempotency_rows': 16,
        'execution_context_rows': 0,
        'unbalanced_journals': 0,
    }
    if reconciliation != expected:
        raise RuntimeError(
            f'Multi-operator financial/stock reconciliation mismatch: '
            f'expected={expected}, actual={reconciliation}'
        )

    report = {
        'status': 'PASS',
        'classification': 'DISPOSABLE_CP6_EIGHT_OPERATOR_WRITE_LOAD',
        'operators': len(CASES),
        'simultaneous_uncommitted_writes_observed': observation,
        'p95_action_ms_conservative': p95_action_ms,
        'max_total_ms': max_total_ms,
        'budgets': {
            'action_ms': ACTION_BUDGET_MS,
            'total_ms': TOTAL_BUDGET_MS,
            'observed_transaction_age_seconds': OBSERVED_TRANSACTION_AGE_BUDGET_SECONDS,
        },
        'outcomes': outcomes,
        'reconciliation': reconciliation,
        'database_scope': 'PHYSICAL_DISPOSABLE_CLONE_DESTROYED_BY_WORKFLOW',
        'production_go': False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(
        'CP6 eight-operator write load passed: eight simultaneous independent '
        'Final-SKU transactions, zero blockers, bounded transaction age/latency, '
        'stock/HPP/WIP/journals reconciled.'
    )


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps({
            'status': 'FAIL', 'error': str(error), 'production_go': False,
        }, indent=2, sort_keys=True) + '\n')
        raise
