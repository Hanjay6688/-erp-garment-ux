#!/usr/bin/env python3
"""Native PostgreSQL regression for CP6 audit counterexamples C01-C06.

The workflow runs this only against its disposable Supabase database. Every
scenario is enclosed in a savepoint and the outer transaction is rolled back.
"""
from __future__ import annotations

import json
import os
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

import psycopg


PGURL = os.environ.get(
    'PGURL', 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'
)
REPORT = Path(
    os.environ.get(
        'CP6_V2620E_COUNTEREXAMPLE_REPORT',
        'cp6-proof/CP6_V2620E_COUNTEREXAMPLE_REGRESSION.json',
    )
)
HEAD = os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND')

OPERATOR_AUTH = 'c8c00000-0000-4000-8000-000000000101'
OPERATOR_APP = 'c8c00000-0000-4000-8000-000000000001'
BASE_PRODUCT = 'c8c10000-0000-4000-8000-000000000004'
SIZE = 'c8c10000-0000-4000-8000-000000000002'
VENDOR = 'c8c20000-0000-4000-8000-000000000002'
BASE_PROCESS = 'c8c20000-0000-4000-8000-000000000003'
LOCATION = 'c8c20000-0000-4000-8000-000000000001'

SEED = Path('supabase/tests/cp6_laundry_qc_concurrency_seed.sql').read_text()
FIXTURE_BLOCK = SEED[
    SEED.index('insert into erp.production_orders('):
    SEED.index('-- Independent-audit F02 owns')
]


def one(cur: psycopg.Cursor, query: str, params: tuple[Any, ...] = ()) -> Any:
    cur.execute(query, params)
    row = cur.fetchone()
    return row[0] if row else None


def row(cur: psycopg.Cursor, query: str, params: tuple[Any, ...] = ()) -> tuple[Any, ...]:
    cur.execute(query, params)
    value = cur.fetchone()
    if value is None:
        raise AssertionError(f'query returned no row: {query}')
    return value


def action(
    cur: psycopg.Cursor,
    action_name: str,
    payload: dict[str, Any],
    expected_version: int,
) -> dict[str, Any]:
    cur.execute('set local role authenticated')
    cur.execute(
        'select public.erp_save_laundry_qc_action_v1(%s,%s::jsonb,%s::uuid,%s)',
        (action_name, json.dumps(payload), str(uuid.uuid4()), expected_version),
    )
    response = cur.fetchone()[0]
    cur.execute('reset role')
    return response


def expect_error(
    cur: psycopg.Cursor,
    operation: Callable[[], None],
    expected_message: str,
) -> str:
    cur.execute('savepoint expected_rejection')
    try:
        operation()
    except psycopg.Error as exc:
        message = str(exc)
        cur.execute('rollback to savepoint expected_rejection')
        cur.execute('release savepoint expected_rejection')
        if expected_message not in message:
            raise AssertionError(
                f'wrong rejection; expected {expected_message!r}, got {message!r}'
            ) from exc
        return message.splitlines()[0]
    cur.execute('rollback to savepoint expected_rejection')
    cur.execute('release savepoint expected_rejection')
    raise AssertionError(f'operation unexpectedly succeeded; expected {expected_message!r}')


def fresh(cur: psycopg.Cursor, tag: str) -> dict[str, str]:
    prefix = f'c8{tag}'
    roll_id = f'{prefix}30000-0000-4000-8000-000000000001'
    block = (
        FIXTURE_BLOCK
        .replace('c8c40000', f'{prefix}40000')
        .replace('c8c50000', f'{prefix}50000')
        .replace('CP6-RACE', f'CP6-V2620E-{tag}')
        .replace('c8c30000-0000-4000-8000-000000000003', roll_id)
    )
    cur.execute(
        """
        insert into erp.material_rolls(
          id,material_id,supplier_id,roll_number,original_qty,cached_qty,
          status,received_at
        ) values(
          %s,'c8c30000-0000-4000-8000-000000000002',
          'c8c30000-0000-4000-8000-000000000001',%s,10,10,
          'AVAILABLE','2026-08-31 07:00+00'
        )
        """,
        (roll_id, f'CP6-V2620E-ROLL-{tag}'),
    )
    cur.execute(block, prepare=False)

    def oid(tail: str) -> str:
        return f'{prefix}40000-0000-4000-8000-{tail.zfill(12)}'

    return {'po': oid('1'), 'group': oid('3'), 'batch': oid('8')}


def create_product(cur: psycopg.Cursor, label: str) -> str:
    product_id = str(uuid.uuid4())
    cur.execute(
        """
        insert into erp.products(
          id,sku,model_id,brand_id,color_name,size_id,product_name,
          identity_root_id,effective_from,is_active,is_portal_visible
        )
        select %s,%s,model_id,brand_id,%s,size_id,%s,%s,effective_from,true,true
        from erp.products where id=%s
        """,
        (
            product_id,
            f'CP6-E-{label}',
            f'CP6-E-{label}',
            f'CP6 E {label}',
            product_id,
            BASE_PRODUCT,
        ),
    )
    cur.execute(
        """
        insert into erp.accessory_bom_versions(
          product_id,version_label,effective_from,is_active,notes
        ) values(%s,'CP6-E-EMPTY','2026-01-01',true,'Explicit empty BOM')
        """,
        (product_id,),
    )
    return product_id


def create_customer(cur: psycopg.Cursor, label: str) -> str:
    customer_id = str(uuid.uuid4())
    cur.execute(
        """
        insert into erp.customers(id,customer_code,customer_name,is_active)
        values(%s,%s,%s,true)
        """,
        (customer_id, f'CP6-E-{label}', f'CP6 E {label} customer'),
    )
    return customer_id


def group_version(cur: psycopg.Cursor, group_id: str) -> int:
    return int(one(cur, 'select row_version from erp.cutting_groups where id=%s', (group_id,)))


def delivery_version(cur: psycopg.Cursor, delivery_id: str) -> int:
    return int(one(cur, 'select row_version from erp.laundry_deliveries where id=%s', (delivery_id,)))


def delivery_size_line(cur: psycopg.Cursor, delivery_id: str) -> str:
    return str(one(
        cur,
        """
        select x.id
        from erp.laundry_delivery_batch_size_lines x
        join erp.laundry_delivery_lines l on l.id=x.delivery_line_id
        where l.delivery_id=%s
        """,
        (delivery_id,),
    ))


def post_delivery(
    cur: psycopg.Cursor,
    fixture: dict[str, str],
    process_id: str,
    physical_at: str,
) -> dict[str, Any]:
    return action(
        cur,
        'POST_DELIVERY',
        {
            'distribution_batch_id': fixture['batch'],
            'vendor_id': VENDOR,
            'wash_process_id': process_id,
            'target_dyeing_color': 'CP6-E-NAVY',
            'physical_at': physical_at,
            'reason': 'CP6 v2.6.20e native counterexample proof',
            'notes': 'Disposable CI only',
            'lines': [{'size_id': SIZE, 'qty_sent_pcs': 10}],
        },
        group_version(cur, fixture['group']),
    )


def post_receipt(
    cur: psycopg.Cursor,
    delivery_id: str,
    process_id: str,
    physical_at: str,
) -> tuple[dict[str, Any], str, str]:
    size_line = delivery_size_line(cur, delivery_id)
    response = action(
        cur,
        'POST_RECEIPT',
        {
            'delivery_id': delivery_id,
            'wash_process_id': process_id,
            'physical_at': physical_at,
            'reason': 'CP6 v2.6.20e native receipt',
            'lines': [{
                'delivery_batch_size_line_id': size_line,
                'qty_good_received': 10,
                'qty_bs_laundry': 0,
                'bs_product_id': None,
            }],
        },
        delivery_version(cur, delivery_id),
    )
    receipt_size, receipt_line = row(
        cur,
        """
        select x.id,x.receipt_line_id
        from erp.laundry_receipt_batch_size_lines x
        join erp.laundry_receipt_lines l on l.id=x.receipt_line_id
        where l.receipt_id=%s
        """,
        (response['receipt_id'],),
    )
    return response, str(receipt_size), str(receipt_line)


def post_final(
    cur: psycopg.Cursor,
    fixture: dict[str, str],
    product_id: str,
    receipt_size: str,
    receipt_line: str,
    physical_at: str,
) -> dict[str, Any]:
    return action(
        cur,
        'POST_FINAL_SKU',
        {
            'cutting_group_id': fixture['group'],
            'destination_location_id': LOCATION,
            'physical_at': physical_at,
            'reason': 'CP6 v2.6.20e exact-size FG proof',
            'good_qty_pcs': 10,
            'completion_mode': 'ALL_READY',
            'lines': [{
                'final_product_id': product_id,
                'qty_good_pcs': 10,
                'qty_bs_pcs': 0,
                'source_laundry_receipt_line_id': receipt_line,
                'source_laundry_receipt_batch_size_line_id': receipt_size,
            }],
        },
        group_version(cur, fixture['group']),
    )


def setup_tiny_fg(
    cur: psycopg.Cursor, tag: str, failed_qty: int
) -> dict[str, str]:
    fixture = fresh(cur, tag)
    product_id = create_product(cur, f'TINY-{tag}')
    process_id = str(uuid.uuid4())
    cur.execute(
        "insert into erp.wash_processes(id,process_code,process_name,is_active) "
        "values(%s,%s,'CP6 E one-cent wash',true)",
        (process_id, f'CP6-E-CENT-{tag}'),
    )
    cur.execute(
        """
        insert into erp.laundry_vendor_rate_versions(
          vendor_id,wash_process_id,rate_per_pcs,effective_from,notes
        ) values(%s,%s,0.01,'2026-01-01','Exact one-cent native fixture')
        """,
        (VENDOR, process_id),
    )
    delivery = post_delivery(cur, fixture, process_id, '2026-09-01T11:00:00Z')
    delivery_id = str(delivery['delivery_id'])
    size_line = delivery_size_line(cur, delivery_id)
    action(
        cur,
        'POST_FAILED_WASH',
        {
            'delivery_id': delivery_id,
            'wash_process_id': process_id,
            'custody_outcome': 'RETRY_AT_VENDOR',
            'physical_at': '2026-09-01T12:00:00Z',
            'reason': 'CP6 E explicit failed participants',
            'lines': [{
                'delivery_batch_size_line_id': size_line,
                'qty_attempted_pcs': failed_qty,
            }],
        },
        delivery_version(cur, delivery_id),
    )
    _, receipt_size, receipt_line = post_receipt(
        cur, delivery_id, process_id, '2026-09-02T11:00:00Z'
    )
    post_final(
        cur, fixture, product_id, receipt_size, receipt_line,
        '2026-09-02T13:00:00Z',
    )
    lot_id = str(one(
        cur,
        """
        select id from erp.fg_lots
        where po_id=%s and product_id=%s and lot_origin='PRODUCTION'
        """,
        (fixture['po'], product_id),
    ))
    return {
        **fixture,
        'product': product_id,
        'process': process_id,
        'receipt_line': receipt_line,
        'lot': lot_id,
    }


def create_sale(
    cur: psycopg.Cursor,
    product_id: str,
    customer_id: str,
    qty: int,
    unit_price: Decimal = Decimal('20'),
) -> dict[str, Any]:
    return one(
        cur,
        'select erp.save_sale_draft_v2(%s::jsonb,%s::uuid,null)',
        (
            json.dumps({
                'sale_number': f'CP6-E-SALE-{uuid.uuid4()}',
                'customer_id': customer_id,
                'source_location_id': LOCATION,
                'sale_date': '2026-09-03T15:00:00Z',
                'reason': 'CP6 v2.6.20e native sale',
                'items': [{
                    'product_id': product_id,
                    'qty_pcs': qty,
                    'unit_price_snapshot': str(unit_price),
                    'discount_amount': 0,
                }],
            }),
            str(uuid.uuid4()),
        ),
    )


def insert_return(
    cur: psycopg.Cursor,
    sale_id: str,
    customer_id: str,
    qty: int,
    refund: Decimal,
    sequence: int,
) -> str:
    return_id = str(uuid.uuid4())
    allocation_id, product_id, lot_id, location_id = row(
        cur,
        """
        select a.id,fl.product_id,a.lot_id,a.location_id
        from erp.sale_stock_allocations a
        join erp.sales_items i on i.id=a.sale_item_id
        join erp.fg_lots fl on fl.id=a.lot_id
        where i.sale_id=%s order by a.id limit 1
        """,
        (sale_id,),
    )
    cur.execute(
        """
        insert into erp.sales_returns(
          id,return_number,sale_id,customer_id,physical_at,status,notes,created_by
        ) values(%s,%s,%s,%s,%s,'DRAFT','CP6 E native return',%s)
        """,
        (
            return_id,
            f'CP6-E-RETURN-{uuid.uuid4()}',
            sale_id,
            customer_id,
            f'2026-09-05T10:{sequence:02d}:00Z',
            OPERATOR_APP,
        ),
    )
    cur.execute(
        """
        insert into erp.sales_return_items(
          return_id,sale_stock_allocation_id,product_id,lot_id,location_id,
          quality_grade,qty_pcs,unit_hpp_snapshot,refund_amount,notes
        ) values(%s,%s,%s,%s,%s,'GRADE_A',%s,0,%s,'Exact native return')
        """,
        (return_id, allocation_id, product_id, lot_id, location_id, qty, refund),
    )
    return return_id


def targeted_issue_count(cur: psycopg.Cursor) -> int:
    return int(one(
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
          'V2620E_NON_PO_SALE_HPP_BOOK_MISMATCH',
          'V2620E_SALES_RETURN_VALUE_EXCEEDS_SALE',
          'V2620E_OPENING_HPP_LINEAGE_MISMATCH',
          'V2620E_OPENING_FG_GL_MISMATCH',
          'V2620E_REDISPATCH_EVENT_MISMATCH'
        )
        """,
    ))


def case_c01(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = fresh(cur, '1')
    product_id = create_product(cur, 'C01')
    first = post_delivery(cur, fixture, BASE_PROCESS, '2026-09-01T11:00:00Z')
    first_id = str(first['delivery_id'])
    first_line = delivery_size_line(cur, first_id)
    failed = action(
        cur,
        'POST_FAILED_WASH',
        {
            'delivery_id': first_id,
            'wash_process_id': BASE_PROCESS,
            'custody_outcome': 'RETURN_UNPROCESSED',
            'physical_at': '2026-09-02T11:00:00Z',
            'reason': 'CP6 E first paid wash returned unprocessed',
            'lines': [{
                'delivery_batch_size_line_id': first_line,
                'qty_attempted_pcs': 10,
            }],
        },
        delivery_version(cur, first_id),
    )
    if failed['delivery_status'] != 'REVERSED' or Decimal(str(failed['actual_cost'])) != 70:
        raise AssertionError(f'C01 first failed wash mismatch: {failed}')

    second = post_delivery(cur, fixture, BASE_PROCESS, '2026-09-03T11:00:00Z')
    second_id = str(second['delivery_id'])
    second_line = delivery_size_line(cur, second_id)
    reversed_second = action(
        cur,
        'REVERSE_DELIVERY',
        {
            'delivery_id': second_id,
            'reason': 'CP6 E cancel redispatch before any receipt',
        },
        delivery_version(cur, second_id),
    )
    if reversed_second['status'] != 'REVERSED':
        raise AssertionError(f'C01 cancellation mismatch: {reversed_second}')

    third = post_delivery(cur, fixture, BASE_PROCESS, '2026-09-04T11:00:00Z')
    third_id = str(third['delivery_id'])
    third_line = delivery_size_line(cur, third_id)
    _, receipt_size, receipt_line = post_receipt(
        cur, third_id, BASE_PROCESS, '2026-09-05T11:00:00Z'
    )
    post_final(
        cur, fixture, product_id, receipt_size, receipt_line,
        '2026-09-06T11:00:00Z',
    )

    hpp = Decimal(str(one(
        cur,
        """
        select coalesce(sum(h.total_cost),0)
        from erp.hpp_versions h join erp.fg_lots f on f.id=h.lot_id
        where f.po_id=%s and f.lot_origin='PRODUCTION' and h.is_current
        """,
        (fixture['po'],),
    )))
    wip = Decimal(str(one(
        cur,
        "select coalesce(sum(debit-credit),0) from erp.journal_lines "
        "where po_id=%s and account_id=erp.account_id('WIP')",
        (fixture['po'],),
    )))
    fg = Decimal(str(one(
        cur,
        "select coalesce(sum(debit-credit),0) from erp.journal_lines "
        "where po_id=%s and account_id=erp.account_id('FG_INVENTORY')",
        (fixture['po'],),
    )))
    accrual = Decimal(str(one(
        cur,
        'select accrued_amount from erp.laundry_cost_accrual_state where po_id=%s',
        (fixture['po'],),
    )))
    event_shape = row(
        cur,
        """
        select
          count(*) filter(where event_type='ALLOCATE'),
          count(*) filter(where event_type='RELEASE'),
          count(*) filter(where event_type='ALLOCATE'
            and source_delivery_batch_size_line_id=%s
            and successor_delivery_batch_size_line_id=%s
            and not exists(select 1 from erp.laundry_redispatch_participant_events x
              where x.event_type='RELEASE'
                and x.releases_allocation_event_id=laundry_redispatch_participant_events.id))
        from erp.laundry_redispatch_participant_events
        where source_delivery_batch_size_line_id=%s
           or successor_delivery_batch_size_line_id in(%s,%s)
           or released_delivery_id=%s
        """,
        (first_line, third_line, first_line, second_line, third_line, second_id),
    )
    if (hpp, wip, fg, accrual) != (
        Decimal('140'), Decimal('0'), Decimal('140'), Decimal('140')
    ) or tuple(map(int, event_shape)) != (2, 1, 1) or targeted_issue_count(cur) != 0:
        raise AssertionError(
            f'C01 mismatch hpp={hpp} wip={wip} fg={fg} accrual={accrual} '
            f'events={event_shape}'
        )
    return {
        'status': 'PASS', 'hpp': str(hpp), 'wip': str(wip), 'fg': str(fg),
        'accrual': str(accrual), 'events': list(map(int, event_shape)),
    }


def case_c02_c04_c06(cur: psycopg.Cursor) -> dict[str, Any]:
    product_id = create_product(cur, 'OPENING-C02-C04-C06')
    customer_id = create_customer(cur, 'OPENING-C02-C04-C06')
    opening_id = str(uuid.uuid4())
    cur.execute(
        """
        insert into erp.opening_balance_headers(
          id,opening_number,opening_date,status,created_by
        ) values(%s,%s,'2026-09-01','DRAFT',%s)
        """,
        (opening_id, f'CP6-E-OPEN-{uuid.uuid4()}', OPERATOR_APP),
    )
    cur.execute(
        """
        insert into erp.opening_balance_items(
          opening_id,balance_type,product_id,location_id,qty,
          unit_cost_snapshot,quality_grade,hpp_input_method
        ) values(%s,'FINISHED_GOODS',%s,%s,5,7,'GRADE_A','MANUAL')
        """,
        (opening_id, product_id, LOCATION),
    )
    one(cur, 'select erp.post_opening_balance(%s)', (opening_id,))
    opening_report = one(
        cur,
        "select erp.get_owner_financial_snapshot_v2('2026-09-01','2026-09-09','2026-09-09')",
    )
    if opening_report['data_confidence']['status'] != 'READY' or targeted_issue_count(cur) != 0:
        raise AssertionError(f'C06 opening report not READY: {opening_report}')

    sale = create_sale(cur, product_id, customer_id, 5)
    sale_id = str(sale['sale_id'])
    one(cur, 'select erp.post_sale(%s)', (sale_id,))
    stock = Decimal(str(one(
        cur,
        'select coalesce(sum(cached_qty_pcs),0) from erp.fg_inventory_balances '
        'where product_id=%s and location_id=%s',
        (product_id, LOCATION),
    )))
    cogs, fg = row(
        cur,
        """
        select
          coalesce(sum(l.debit-l.credit) filter(
            where l.account_id=erp.account_id('COGS')),0),
          coalesce(sum(l.debit-l.credit) filter(
            where l.account_id=erp.account_id('FG_INVENTORY')),0)
        from erp.journal_entries e
        join erp.journal_lines l on l.journal_entry_id=e.id
        where e.source_type='SALE' and e.source_id=%s and e.status='POSTED'
        """,
        (sale_id,),
    )
    if stock != 0 or Decimal(str(cogs)) != 35 or Decimal(str(fg)) != -35:
        raise AssertionError(f'C02 opening sale mismatch stock={stock} cogs={cogs} fg={fg}')

    return_id = insert_return(
        cur, sale_id, customer_id, 5, Decimal('100.01'), 1
    )
    rejection = expect_error(
        cur,
        lambda: one(cur, 'select erp.post_sales_return(%s)', (return_id,)),
        'Refund exceeds original net sale value for product',
    )
    if one(cur, 'select status from erp.sales_returns where id=%s', (return_id,)) != 'DRAFT':
        raise AssertionError('C04 rejected over-refund changed return status')

    valid_return = insert_return(
        cur, sale_id, customer_id, 5, Decimal('100.00'), 2
    )
    one(cur, 'select erp.post_sales_return(%s)', (valid_return,))
    return_cogs, return_fg = row(
        cur,
        """
        select
          coalesce(sum(l.debit-l.credit) filter(
            where l.account_id=erp.account_id('COGS')),0),
          coalesce(sum(l.debit-l.credit) filter(
            where l.account_id=erp.account_id('FG_INVENTORY')),0)
        from erp.journal_entries e
        join erp.journal_lines l on l.journal_entry_id=e.id
        where e.source_type='SALES_RETURN' and e.source_id=%s and e.status='POSTED'
        """,
        (valid_return,),
    )
    if Decimal(str(return_cogs)) != -35 or Decimal(str(return_fg)) != 35:
        raise AssertionError(
            f'C02 opening return mismatch cogs={return_cogs} fg={return_fg}'
        )
    one(
        cur,
        "select erp.reverse_sales_return(%s,'C02 opening return inverse')",
        (valid_return,),
    )
    inverse_status = one(
        cur, 'select status from erp.sales_returns where id=%s', (valid_return,)
    )
    inverse_stock = int(one(
        cur,
        'select coalesce(sum(cached_qty_pcs),0) from erp.fg_inventory_balances '
        'where product_id=%s and location_id=%s',
        (product_id, LOCATION),
    ))
    if inverse_status != 'REVERSED' or inverse_stock != 0:
        raise AssertionError(
            f'C02 opening return inverse mismatch status={inverse_status} stock={inverse_stock}'
        )
    final_report = one(
        cur,
        "select erp.get_owner_financial_snapshot_v2('2026-09-01','2026-09-09','2026-09-09')",
    )
    if final_report['data_confidence']['status'] != 'READY' or targeted_issue_count(cur) != 0:
        raise AssertionError(f'C02/C06 final report not READY: {final_report}')
    return {
        'C02': {
            'status': 'PASS', 'stock': str(stock), 'cogs': str(cogs),
            'fg': str(fg), 'return_cogs': str(return_cogs),
            'return_fg': str(return_fg), 'inverse_status': inverse_status,
        },
        'C04': {'status': 'PASS', 'rejection': rejection},
        'C06': {'status': 'PASS', 'confidence': 'READY'},
    }


def case_c03(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = setup_tiny_fg(cur, '3', 1)
    customer_id = create_customer(cur, 'C03')
    hpp = Decimal(str(one(
        cur,
        'select total_cost from erp.hpp_versions where lot_id=%s and is_current',
        (fixture['lot'],),
    )))
    if hpp != Decimal('0.11'):
        raise AssertionError(f'C03 fixture HPP is not 0.11: {hpp}')
    adjustment = one(
        cur,
        'select erp.save_fg_adjustment_draft_v2(%s::jsonb,%s::uuid,null)',
        (
            json.dumps({
                'adjustment_number': f'CP6-E-C03-LOSS-{uuid.uuid4()}',
                'location_id': LOCATION,
                'physical_at': '2026-09-03T10:00:00Z',
                'reason_code': 'LOSS',
                'reason': 'CP6 E loss before sale',
                'change_reason': 'C03 reverse ordering native proof',
                'items': [{
                    'lot_id': fixture['lot'],
                    'product_id': fixture['product'],
                    'quality_grade': 'GRADE_A',
                    'qty_signed': -5,
                    'notes': 'Actual loss before valid sale',
                }],
            }),
            str(uuid.uuid4()),
        ),
    )
    one(cur, 'select erp.post_fg_adjustment(%s)', (adjustment['fg_adjustment_id'],))
    sale = create_sale(cur, fixture['product'], customer_id, 5)
    one(cur, 'select erp.post_sale(%s)', (sale['sale_id'],))
    fg, cogs, other = row(
        cur,
        'select fg_value,cogs_value,other_out_value '
        'from erp.po_hpp_gl_state where po_id=%s',
        (fixture['po'],),
    )
    book = row(
        cur,
        'select * from erp.compute_po_hpp_gl_book_v2620e(%s)',
        (fixture['po'],),
    )
    stock = one(
        cur,
        'select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m '
        'where m.lot_id=%s',
        (fixture['lot'],),
    )
    expected = (Decimal('0'), Decimal('0.06'), Decimal('0.05'))
    actual = tuple(Decimal(str(value)) for value in (fg, cogs, other))
    actual_book = tuple(Decimal(str(value)) for value in book)
    if actual != expected or actual_book != expected or int(stock) != 0 or targeted_issue_count(cur) != 0:
        raise AssertionError(
            f'C03 conserved-cent mismatch state={actual} book={actual_book} stock={stock}'
        )
    return {
        'status': 'PASS', 'fg': str(actual[0]), 'cogs': str(actual[1]),
        'other': str(actual[2]), 'stock': int(stock),
    }


def case_c05(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = setup_tiny_fg(cur, '5', 4)
    customer_id = create_customer(cur, 'C05')
    invoice_id = str(uuid.uuid4())
    cur.execute(
        """
        insert into erp.vendor_invoices(
          id,invoice_number,vendor_id,invoice_date,received_at,due_date,
          status,total_amount,notes,created_by
        ) values(%s,%s,%s,'2026-09-04','2026-09-04T10:00:00Z',
          '2026-09-17','DRAFT',0,'C05 zero-rate final invoice',%s)
        """,
        (invoice_id, f'CP6-E-C05-VI-{uuid.uuid4()}', VENDOR, OPERATOR_APP),
    )
    cur.execute(
        """
        insert into erp.vendor_invoice_items(
          invoice_id,receipt_line_id,description,qty_pcs,actual_rate,actual_amount
        ) values(%s,%s,'C05 exact receipt invoice',10,0,0)
        """,
        (invoice_id, fixture['receipt_line']),
    )
    one(cur, 'select erp.post_vendor_invoice(%s)', (invoice_id,))
    hpp = Decimal(str(one(
        cur,
        'select total_cost from erp.hpp_versions where lot_id=%s and is_current',
        (fixture['lot'],),
    )))
    if hpp != Decimal('0.04'):
        raise AssertionError(f'C05 fixture HPP is not 0.04: {hpp}')

    sale = create_sale(cur, fixture['product'], customer_id, 10)
    sale_id = str(sale['sale_id'])
    one(cur, 'select erp.post_sale(%s)', (sale_id,))
    return_ids: list[str] = []
    for sequence, qty in enumerate((1, 1, 1, 1, 2), start=1):
        return_id = insert_return(
            cur, sale_id, customer_id, qty, Decimal('0'), sequence
        )
        one(cur, 'select erp.post_sales_return(%s)', (return_id,))
        return_ids.append(return_id)
    last_return = return_ids[-1]
    journal_count = int(one(
        cur,
        "select count(*) from erp.journal_entries where source_type='SALES_RETURN' "
        "and source_id=%s",
        (last_return,),
    ))
    raw_last_hpp = Decimal(str(one(
        cur,
        'select sum(qty_pcs*unit_hpp_snapshot) from erp.sales_return_items '
        'where return_id=%s',
        (last_return,),
    )))
    if journal_count != 0 or raw_last_hpp != Decimal('0.008'):
        raise AssertionError(
            f'C05 fixture must be zero-journal/raw .008: journals={journal_count} raw={raw_last_hpp}'
        )
    one(
        cur,
        "select erp.reverse_sales_return(%s,'C05 valid zero-journal inverse')",
        (last_return,),
    )
    status = one(cur, 'select status from erp.sales_returns where id=%s', (last_return,))
    stock = int(one(
        cur,
        'select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s',
        (fixture['lot'],),
    ))
    fg, cogs = row(
        cur,
        'select fg_value,cogs_value from erp.po_hpp_gl_state where po_id=%s',
        (fixture['po'],),
    )
    if (
        status != 'REVERSED' or stock != 4
        or Decimal(str(fg)) != Decimal('0.02')
        or Decimal(str(cogs)) != Decimal('0.02')
        or targeted_issue_count(cur) != 0
    ):
        raise AssertionError(
            f'C05 inverse mismatch status={status} stock={stock} fg={fg} cogs={cogs}'
        )
    return {
        'status': 'PASS', 'raw_last_hpp': str(raw_last_hpp),
        'last_return_journals': journal_count, 'inverse_status': status,
        'stock': stock, 'fg': str(fg), 'cogs': str(cogs),
    }


def run() -> dict[str, Any]:
    report: dict[str, Any] = {
        'head': HEAD,
        'boundary': 'CP6_V2620E_C01_C06_NATIVE_POSTGRESQL',
        'classification': 'DISPOSABLE_NATIVE_POSTGRESQL_REGRESSION',
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
                (json.dumps({'sub': OPERATOR_AUTH, 'role': 'authenticated'}),),
            )
            cur.execute(
                "select set_config('app.change_reason',"
                "'CP6 v2.6.20e native counterexample regression',true)"
            )
            if one(
                cur,
                "select count(*) from erp.schema_migrations where version='v2.6.20e'",
            ) != 1:
                raise AssertionError('v2.6.20e is not installed exactly once')
            if 'v_delta_other' not in str(one(
                cur,
                "select pg_get_functiondef('erp.post_sale(uuid)'::regprocedure)",
            )):
                raise AssertionError('v2.6.20e Sale runtime patch is absent')

            baseline_events = int(one(
                cur, 'select count(*) from erp.laundry_redispatch_participant_events'
            ))
            cases: tuple[tuple[str, Callable[[psycopg.Cursor], dict[str, Any]]], ...] = (
                ('C01', case_c01),
                ('C02_C04_C06', case_c02_c04_c06),
                ('C03', case_c03),
                ('C05', case_c05),
            )
            for name, case in cases:
                savepoint = f'case_{name.lower()}'
                cur.execute(f'savepoint {savepoint}')
                report['cases'][name] = case(cur)
                cur.execute(f'rollback to savepoint {savepoint}')
                cur.execute(f'release savepoint {savepoint}')

            if int(one(
                cur, 'select count(*) from erp.laundry_redispatch_participant_events'
            )) != baseline_events:
                raise AssertionError('scenario savepoints left redispatch-event residue')
            if one(cur, 'select count(*) from erp.cp6_laundry_qc_execution_context') != 0:
                raise AssertionError('scenario savepoints left execution-context residue')
            report['baseline_event_count'] = baseline_events
            report['targeted_issue_count'] = targeted_issue_count(cur)
            report['status'] = 'PASS'
        conn.rollback()
    return report


def main() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any]
    try:
        result = run()
    except Exception as exc:  # emitted into exact-SHA CI evidence
        result = {
            'head': HEAD,
            'boundary': 'CP6_V2620E_C01_C06_NATIVE_POSTGRESQL',
            'status': 'FAIL',
            'error': str(exc),
            'production_go': False,
        }
        REPORT.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, sort_keys=True))
        raise
    REPORT.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
