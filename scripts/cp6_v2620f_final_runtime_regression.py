#!/usr/bin/env python3
"""Native PostgreSQL regression for CP6 audit blockers A01-A03.

The workflow invokes this only after v2.6.20e and v2.6.20f are installed on
the disposable database.  Every case is savepoint-isolated and the enclosing
transaction is rolled back, so this proof cannot leave business residue.
"""
from __future__ import annotations

import json
import os
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

import psycopg

import cp6_v2620e_counterexample_regression as base


PGURL = os.environ.get(
    'PGURL', 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'
)
REPORT = Path(os.environ.get(
    'CP6_V2620F_RELIABILITY_REPORT',
    'cp6-proof/CP6_V2620F_FINAL_RUNTIME_REGRESSION.json',
))
HEAD = os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND')


def decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def targeted_issue_count(cur: psycopg.Cursor) -> int:
    return int(base.one(
        cur,
        """
        select coalesce(sum(issue_count),0)::bigint
        from erp.run_v268_financial_report_checks()
        where check_name in(
          'V2620C_PO_HPP_TARGET_STATE_MISMATCH',
          'V2620C_PO_HPP_BOOK_MISMATCH',
          'V2620C_WIP_SOURCE_CONSERVATION_MISMATCH',
          'V2620C_HPP_COMPONENT_SUM_MISMATCH',
          'V2620D_SALE_LIFECYCLE_HPP_DIMENSION_MISMATCH',
          'V2620F_NON_PO_PRODUCT_HPP_BOOK_MISMATCH',
          'V2620E_SALES_RETURN_VALUE_EXCEEDS_SALE',
          'V2620E_OPENING_HPP_LINEAGE_MISMATCH',
          'V2620E_OPENING_FG_GL_MISMATCH',
          'V2620D_REDISPATCH_PARTICIPANT_LINEAGE_MISMATCH',
          'V2620E_REDISPATCH_EVENT_MISMATCH',
          'V2620F_CONVERSION_VALUE_LINEAGE_MISMATCH'
        )
        """,
    ))


def po_state(cur: psycopg.Cursor, po_id: str) -> tuple[Decimal, Decimal, Decimal]:
    values = base.row(
        cur,
        'select fg_value,cogs_value,other_out_value '
        'from erp.po_hpp_gl_state where po_id=%s',
        (po_id,),
    )
    return tuple(decimal(value) for value in values)  # type: ignore[return-value]


def non_po_state(
    cur: psycopg.Cursor, product_id: str
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    target = base.row(
        cur,
        'select * from erp.compute_non_po_product_hpp_targets_v2620f(%s)',
        (product_id,),
    )
    book = base.row(
        cur,
        'select * from erp.compute_non_po_product_hpp_book_v2620f(%s)',
        (product_id,),
    )
    target_values = tuple(decimal(value) for value in target)
    book_values = tuple(decimal(value) for value in book)
    if target_values != book_values:
        raise AssertionError(
            f'non-PO target/book mismatch target={target_values} book={book_values}'
        )
    return target_values  # type: ignore[return-value]


def post_conversion(
    cur: psycopg.Cursor,
    source_product: str,
    target_product: str,
    qty: int,
    tag: str,
) -> str:
    conversion_id = str(uuid.uuid4())
    cur.execute(
        """
        insert into erp.product_conversions(
          id,conversion_number,from_product_id,to_product_id,location_id,
          qty_pcs,conversion_type,physical_at,status,conversion_cost_total,
          notes,created_by
        ) values(
          %s,%s,%s,%s,%s,%s,'RELABEL','2026-09-03T09:00:00Z',
          'DRAFT',0,'CP6 F native value-preserving conversion',%s
        )
        """,
        (
            conversion_id, f'CP6-F-CONVERT-{tag}-{uuid.uuid4()}',
            source_product, target_product, base.LOCATION, qty, base.OPERATOR_APP,
        ),
    )
    base.one(cur, 'select erp.post_product_conversion(%s)', (conversion_id,))
    return conversion_id


def finalize_laundry_invoice(
    cur: psycopg.Cursor, receipt_line_id: str, rate: Decimal
) -> str:
    invoice_id = str(uuid.uuid4())
    amount = Decimal('10') * rate
    cur.execute(
        """
        insert into erp.vendor_invoices(
          id,invoice_number,vendor_id,invoice_date,received_at,due_date,
          status,total_amount,notes,created_by
        ) values(
          %s,%s,%s,'2026-09-04','2026-09-04T10:00:00Z','2026-09-17',
          'DRAFT',%s,'CP6 F late exact Laundry invoice',%s
        )
        """,
        (
            invoice_id, f'CP6-F-VI-{uuid.uuid4()}', base.VENDOR, amount,
            base.OPERATOR_APP,
        ),
    )
    cur.execute(
        """
        insert into erp.vendor_invoice_items(
          invoice_id,receipt_line_id,description,qty_pcs,actual_rate,actual_amount
        ) values(%s,%s,'CP6 F exact receipt invoice',10,%s,%s)
        """,
        (invoice_id, receipt_line_id, rate, amount),
    )
    base.one(cur, 'select erp.post_vendor_invoice(%s)', (invoice_id,))
    return invoice_id


def case_a01(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = base.fresh(cur, 'a')
    source_product = base.create_product(cur, 'F-A01-SOURCE')
    target_product = base.create_product(cur, 'F-A01-TARGET')
    customer_id = base.create_customer(cur, 'F-A01')
    delivery = base.post_delivery(
        cur, fixture, base.BASE_PROCESS, '2026-09-01T11:00:00Z'
    )
    _, receipt_size, receipt_line = base.post_receipt(
        cur, str(delivery['delivery_id']), base.BASE_PROCESS,
        '2026-09-02T11:00:00Z',
    )
    base.post_final(
        cur, fixture, source_product, receipt_size, receipt_line,
        '2026-09-02T13:00:00Z',
    )
    conversion_id = post_conversion(
        cur, source_product, target_product, 4, 'A01'
    )
    before_invoice = po_state(cur, fixture['po'])
    invoice_id = finalize_laundry_invoice(cur, receipt_line, Decimal('10'))
    after_invoice = po_state(cur, fixture['po'])
    descendant = base.row(
        cur,
        """
        select fl.cached_qty_pcs,h.total_cost,h.hpp_per_pcs
        from erp.fg_lots fl
        join erp.hpp_versions h on h.lot_id=fl.id and h.is_current
        where fl.po_id=%s and fl.product_id=%s and fl.lot_origin='CONVERSION'
        """,
        (fixture['po'], target_product),
    )
    sale = base.create_sale(cur, target_product, customer_id, 4)
    base.one(cur, 'select erp.post_sale(%s)', (sale['sale_id'],))
    after_sale = po_state(cur, fixture['po'])
    if before_invoice != (Decimal('70'), Decimal('0'), Decimal('0')):
        raise AssertionError(f'A01 pre-invoice state mismatch: {before_invoice}')
    if after_invoice != (Decimal('100'), Decimal('0'), Decimal('0')):
        raise AssertionError(f'A01 late-invoice state mismatch: {after_invoice}')
    if tuple(decimal(value) for value in descendant) != (
        Decimal('4'), Decimal('40'), Decimal('10')
    ):
        raise AssertionError(f'A01 descendant HPP mismatch: {descendant}')
    if after_sale != (Decimal('60'), Decimal('40'), Decimal('0')):
        raise AssertionError(f'A01 sale state mismatch: {after_sale}')
    if targeted_issue_count(cur) != 0:
        raise AssertionError('A01 left a targeted report issue')
    return {
        'status': 'PASS', 'conversion_id': conversion_id,
        'invoice_id': invoice_id,
        'before_invoice': [str(value) for value in before_invoice],
        'after_invoice': [str(value) for value in after_invoice],
        'after_sale': [str(value) for value in after_sale],
        'descendant_hpp': str(descendant[2]),
    }


def create_opening(cur: psycopg.Cursor, product_id: str) -> str:
    opening_id = str(uuid.uuid4())
    cur.execute(
        """
        insert into erp.opening_balance_headers(
          id,opening_number,opening_date,status,created_by
        ) values(%s,%s,'2026-09-01','DRAFT',%s)
        """,
        (opening_id, f'CP6-F-OPEN-{uuid.uuid4()}', base.OPERATOR_APP),
    )
    cur.execute(
        """
        insert into erp.opening_balance_items(
          opening_id,balance_type,product_id,location_id,qty,
          unit_cost_snapshot,quality_grade,hpp_input_method
        ) values(%s,'FINISHED_GOODS',%s,%s,10,0.011,'GRADE_A','MANUAL')
        """,
        (opening_id, product_id, base.LOCATION),
    )
    base.one(cur, 'select erp.post_opening_balance(%s)', (opening_id,))
    return opening_id


def case_a02(cur: psycopg.Cursor) -> dict[str, Any]:
    product_id = base.create_product(cur, 'F-A02')
    customer_id = base.create_customer(cur, 'F-A02')
    opening_id = create_opening(cur, product_id)
    initial = non_po_state(cur, product_id)

    split_sales: list[str] = []
    for _ in range(10):
        sale = base.create_sale(
            cur, product_id, customer_id, 1, Decimal('0')
        )
        sale_id = str(sale['sale_id'])
        base.one(cur, 'select erp.post_sale(%s)', (sale_id,))
        split_sales.append(sale_id)
    after_split_sales = non_po_state(cur, product_id)
    for index in (4, 0, 8, 2, 6, 1, 9, 3, 7, 5):
        base.one(
            cur,
            "select erp.reverse_sale(%s,'CP6 F non-FIFO split-Sale reversal')",
            (split_sales[index],),
        )
    after_sale_reversals = non_po_state(cur, product_id)

    return_product_id = base.create_product(cur, 'F-A02-RETURNS')
    return_customer_id = base.create_customer(cur, 'F-A02-RETURNS')
    return_opening_id = create_opening(cur, return_product_id)
    return_initial = non_po_state(cur, return_product_id)
    lumped = base.create_sale(
        cur, return_product_id, return_customer_id, 10, Decimal('0')
    )
    lumped_id = str(lumped['sale_id'])
    base.one(cur, 'select erp.post_sale(%s)', (lumped_id,))
    split_returns: list[str] = []
    for sequence in range(10):
        return_id = base.insert_return(
            cur, lumped_id, return_customer_id, 1, Decimal('0'), sequence
        )
        base.one(cur, 'select erp.post_sales_return(%s)', (return_id,))
        split_returns.append(return_id)
    after_split_returns = non_po_state(cur, return_product_id)
    for index in (5, 1, 9, 3, 7, 0, 8, 2, 6, 4):
        base.one(
            cur,
            "select erp.reverse_sales_return(%s,'CP6 F non-FIFO return reversal')",
            (split_returns[index],),
        )
    after_return_reversals = non_po_state(cur, return_product_id)
    base.one(
        cur,
        "select erp.reverse_sale(%s,'CP6 F final lumped-Sale reversal')",
        (lumped_id,),
    )
    final = non_po_state(cur, return_product_id)

    expected_owned = (
        Decimal('0.11'), Decimal('0.11'), Decimal('0'), Decimal('0')
    )
    expected_sold = (
        Decimal('0.11'), Decimal('0'), Decimal('0.11'), Decimal('0')
    )
    if (initial != expected_owned or after_sale_reversals != expected_owned
            or return_initial != expected_owned):
        raise AssertionError(
            f'A02 owned states mismatch: initial={initial}, '
            f'reversed={after_sale_reversals}, return_initial={return_initial}'
        )
    if after_split_sales != expected_sold or after_return_reversals != expected_sold:
        raise AssertionError(
            f'A02 sold states mismatch: sales={after_split_sales}, '
            f'return inverses={after_return_reversals}'
        )
    if after_split_returns != expected_owned or final != expected_owned:
        raise AssertionError(
            f'A02 return/final states mismatch: returns={after_split_returns}, final={final}'
        )
    if targeted_issue_count(cur) != 0:
        raise AssertionError('A02 left a targeted report issue')
    return {
        'status': 'PASS', 'sale_opening_id': opening_id,
        'return_opening_id': return_opening_id,
        'after_split_sales': [str(value) for value in after_split_sales],
        'after_split_returns': [str(value) for value in after_split_returns],
        'final': [str(value) for value in final],
        'sale_reversal_order': [4, 0, 8, 2, 6, 1, 9, 3, 7, 5],
        'return_reversal_order': [5, 1, 9, 3, 7, 0, 8, 2, 6, 4],
    }


def case_a03(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = base.fresh(cur, 'b')
    first = base.post_delivery(
        cur, fixture, base.BASE_PROCESS, '2026-09-01T11:00:00Z'
    )
    first_id = str(first['delivery_id'])
    failed = base.action(
        cur,
        'POST_FAILED_WASH',
        {
            'delivery_id': first_id,
            'wash_process_id': base.BASE_PROCESS,
            'custody_outcome': 'RETURN_UNPROCESSED',
            'physical_at': '2026-09-02T11:00:00Z',
            'reason': 'CP6 F actual full physical return',
            'lines': [{
                'delivery_batch_size_line_id': base.delivery_size_line(cur, first_id),
                'qty_attempted_pcs': 10,
            }],
        },
        base.delivery_version(cur, first_id),
    )
    second = base.post_delivery(
        cur, fixture, base.BASE_PROCESS, '2026-09-03T11:00:00Z'
    )
    second_id = str(second['delivery_id'])
    base.action(
        cur,
        'REVERSE_DELIVERY',
        {'delivery_id': second_id, 'reason': 'CP6 F cancel unused redispatch'},
        base.delivery_version(cur, second_id),
    )
    reversed_receipt = base.action(
        cur,
        'REVERSE_RECEIPT',
        {
            'receipt_id': str(failed['receipt_id']),
            'reason': 'CP6 F reverse financial failed-wash cost only',
        },
        int(base.one(
            cur, 'select row_version from erp.laundry_receipts where id=%s',
            (failed['receipt_id'],),
        )),
    )
    custody = base.row(
        cur,
        """
        select r.status,a.custody_outcome,d.status,
          rv.source_type,rv.stage_from,rv.stage_to,rv.qty_pcs,
          (rv.physical_at<='2026-09-03T11:00:00Z'::timestamptz)
        from erp.laundry_failed_wash_attempts a
        join erp.laundry_receipts r on r.id=a.receipt_id
        join erp.laundry_deliveries d on d.id=a.delivery_id
        join erp.wip_stage_events rv on rv.id=a.return_wip_event_id
        where a.receipt_id=%s
        """,
        (failed['receipt_id'],),
    )
    expected = (
        'REVERSED', 'RETURN_UNPROCESSED', 'REVERSED',
        'CP6_LAUNDRY_DELIVERY_WIP_REVERSAL', 'LAUNDRY', 'SEWING', 10, True,
    )
    if custody != expected:
        raise AssertionError(f'A03 custody fact mismatch: {custody}')
    if reversed_receipt['status'] != 'REVERSED' or targeted_issue_count(cur) != 0:
        raise AssertionError(
            f'A03 reversal/report mismatch: response={reversed_receipt}'
        )
    return {
        'status': 'PASS', 'receipt_id': str(failed['receipt_id']),
        'redispatch_id': second_id, 'receipt_status': custody[0],
        'custody_outcome': custody[1], 'return_event_preserved': True,
        'report_issue_count': 0,
    }


def run() -> dict[str, Any]:
    report: dict[str, Any] = {
        'head': HEAD,
        'boundary': 'CP6_V2620F_A01_A03_FINAL_RUNTIME_NATIVE_POSTGRESQL',
        'classification': 'DISPOSABLE_NATIVE_POSTGRESQL_REGRESSION_AFTER_E_AND_F',
        'runtime_versions': ['v2.6.20e', 'v2.6.20f'],
        'production_go': False,
        'cases': {},
    }
    with psycopg.connect(PGURL, autocommit=False) as conn:
        with conn.cursor() as cur:
            cur.execute("set local timezone='UTC'")
            cur.execute("set local datestyle='ISO, MDY'")
            cur.execute("set local lock_timeout='8s'")
            cur.execute("set local statement_timeout='180s'")
            cur.execute(
                "select set_config('request.jwt.claims',%s,true)",
                (json.dumps({
                    'sub': base.OPERATOR_AUTH, 'role': 'authenticated',
                }),),
            )
            cur.execute(
                "select set_config('app.change_reason',"
                "'CP6 v2.6.20f final-runtime native regression',true)"
            )
            versions = base.row(
                cur,
                """
                select count(*) filter(where version='v2.6.20e'),
                  count(*) filter(where version='v2.6.20f')
                from erp.schema_migrations
                """,
            )
            if versions != (1, 1):
                raise AssertionError(f'E+F runtime is not installed exactly once: {versions}')
            base.load_fixture_foundation(cur)
            baseline_events = int(base.one(
                cur, 'select count(*) from erp.non_po_hpp_gl_sync_events_v2620f'
            ))
            cases: tuple[
                tuple[str, Callable[[psycopg.Cursor], dict[str, Any]]], ...
            ] = (
                ('A01', case_a01),
                ('A02', case_a02),
                ('A03', case_a03),
            )
            for name, case in cases:
                savepoint = f'case_{name.lower()}'
                cur.execute(f'savepoint {savepoint}')
                report['cases'][name] = case(cur)
                cur.execute(f'rollback to savepoint {savepoint}')
                cur.execute(f'release savepoint {savepoint}')
            if int(base.one(
                cur, 'select count(*) from erp.non_po_hpp_gl_sync_events_v2620f'
            )) != baseline_events:
                raise AssertionError('scenario savepoints left non-PO sync-event residue')
            if int(base.one(
                cur, 'select count(*) from erp.cp6_laundry_qc_execution_context'
            )) != 0:
                raise AssertionError('scenario savepoints left execution-context residue')
            report['baseline_sync_event_count'] = baseline_events
            report['targeted_issue_count'] = targeted_issue_count(cur)
            report['status'] = 'PASS'
        conn.rollback()
    return report


def main() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = run()
    except Exception as exc:
        result = {
            'head': HEAD,
            'boundary': 'CP6_V2620F_A01_A03_FINAL_RUNTIME_NATIVE_POSTGRESQL',
            'status': 'FAIL',
            'error': str(exc),
            'production_go': False,
        }
        REPORT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
        print(json.dumps(result, sort_keys=True))
        raise
    REPORT.write_text(json.dumps(result, indent=2) + '\n', encoding='utf8')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
