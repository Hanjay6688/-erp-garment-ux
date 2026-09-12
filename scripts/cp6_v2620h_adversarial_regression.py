#!/usr/bin/env python3
"""Native PostgreSQL proof for CP6 expanded-audit findings R02 and R03."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable

import psycopg
import cp6_v2620k_runtime as k_runtime
import cp6_v2620l_runtime as l_runtime
import cp6_v2620m_runtime as m_runtime

import cp6_v2620e_counterexample_regression as base


MIGRATION = Path(
    'supabase/migrations/20260910061516_erp_v2_6_20h_cp6_expanded_audit_closure.sql'
)
SUCCESSOR_I = Path(
    'supabase/migrations/20260910100051_erp_v2_6_20i_cp6_h2_audit_closure.sql'
)
SUCCESSOR_J = Path(
    'supabase/migrations/20260910170556_erp_v2_6_20j_cp6_payment_fact_closure.sql'
)
REPORT = Path(
    os.environ.get(
        'CP6_H_REPORT', 'cp6-proof/CP6_V2620H_EXPANDED_AUDIT_REGRESSION.json'
    )
)
PGURL = os.environ.get('PGURL', '')
HEAD = os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND')


def exact_runtime(cur: psycopg.Cursor) -> dict[str, Any]:
    k_successor = k_runtime.verified_successor(cur)
    l_successor = l_runtime.verified_successor(cur)
    m_successor = m_runtime.verified_successor(cur)
    versions = base.one(
        cur,
        """select jsonb_agg(version order by version) from erp.schema_migrations
           where version in(
             'v2.6.20e','v2.6.20f','v2.6.20g','v2.6.20h','v2.6.20i','v2.6.20j'
           )""",
    )
    if versions != [
        'v2.6.20e', 'v2.6.20f', 'v2.6.20g',
        'v2.6.20h', 'v2.6.20i', 'v2.6.20j',
    ]:
        raise AssertionError(f'Final E+F+G+H+I+J runtime not present: {versions}')
    i_installed = base.one(
        cur,
        "select installed_definition_sha256 from erp.cp6_v2620i_rollback_capsule",
    )
    cur.execute(
        """select object_regidentity,definition_sha256,installed_definition_sha256,
          encode(extensions.digest(convert_to(pg_get_functiondef(
            to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex') actual
          from erp.cp6_v2620j_rollback_capsule order by object_regidentity"""
    )
    j_pre_m_rows = k_runtime.extend_rows(k_successor, cur.fetchall())
    j_rows = m_runtime.extend_rows(m_successor, j_pre_m_rows)
    if len(j_rows) != 3 or any(item[2] != item[3] for item in j_rows):
        raise AssertionError(f'J successor capsule/function mismatch: {j_rows}')
    j_by_identity = {item[0]: item[2] for item in j_rows}
    j_pre_m_by_identity = {item[0]: item[2] for item in j_pre_m_rows}
    cur.execute(
        """select object_regidentity,installed_definition_sha256,
          encode(extensions.digest(convert_to(pg_get_functiondef(
            to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex') actual
          from erp.cp6_v2620h_rollback_capsule order by object_regidentity"""
    )
    functions = [
        {'identity': row[0], 'installed_sha256': row[1], 'actual_sha256': row[2]}
        for row in cur.fetchall()
    ]
    for item in functions:
        item['h_installed_sha256'] = item['installed_sha256']
        if item['identity'] in j_by_identity:
            item['installed_sha256'] = j_pre_m_by_identity[item['identity']]
            item['expected_generation'] = 'K' if k_successor else 'J'
        elif item['identity'] == 'erp.run_v268_financial_report_checks()':
            item['installed_sha256'] = i_installed
            item['expected_generation'] = 'I'
        else:
            item['expected_generation'] = 'H'
    l_runtime.extend_items(l_successor, functions)
    m_runtime.extend_items(m_successor, functions)
    if len(functions) != 6 or any(
        item['installed_sha256'] != item['actual_sha256'] for item in functions
    ):
        raise AssertionError('H installed definition differs from effective H/I/J runtime')
    cur.execute(
        """select object_regidentity,definition_sha256,installed_definition_sha256,
          encode(extensions.digest(convert_to(pg_get_functiondef(
            to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex') actual
          from erp.cp6_v2620i_rollback_capsule"""
    )
    i_row = cur.fetchone()
    if (
        i_row is None
        or i_row[0] != 'erp.run_v268_financial_report_checks()'
        or i_row[1] != '3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f'
        or i_row[3] != j_by_identity['erp.run_v268_financial_report_checks()']
    ):
        raise AssertionError(f'I capsule/effective report mismatch: {i_row}')
    source = MIGRATION.read_bytes()
    file_sha = hashlib.sha256(source).hexdigest()
    platform = base.one(
        cur,
        """select encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),
          'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations
          where name='erp_v2_6_20h_cp6_expanded_audit_closure'""",
    )
    if platform not in (file_sha, hashlib.sha256(source[:-1]).hexdigest()):
        raise AssertionError(f'H source/platform drift: {platform} != {file_sha}')
    i_source = SUCCESSOR_I.read_bytes()
    i_file_sha = hashlib.sha256(i_source).hexdigest()
    i_platform = base.one(
        cur,
        """select encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),
          'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations
          where name='erp_v2_6_20i_cp6_h2_audit_closure'""",
    )
    if i_platform not in (i_file_sha, hashlib.sha256(i_source[:-1]).hexdigest()):
        raise AssertionError(f'I source/platform drift: {i_platform} != {i_file_sha}')
    j_source = SUCCESSOR_J.read_bytes()
    j_file_sha = hashlib.sha256(j_source).hexdigest()
    j_platform = base.one(
        cur,
        """select encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),
          'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations
          where name='erp_v2_6_20j_cp6_payment_fact_closure'""",
    )
    if j_platform not in (j_file_sha, hashlib.sha256(j_source[:-1]).hexdigest()):
        raise AssertionError(f'J source/platform drift: {j_platform} != {j_file_sha}')
    return {
        'engine': base.one(cur, 'select version()'),
        'versions': versions + (['v2.6.20k'] if k_successor else []) + (['v2.6.20l'] if l_successor else []) + (['v2.6.20m'] if m_successor else []) + (['v2.6.20n'] if any('pre_n_installed_sha256' in x for x in m_successor.values()) else []) + (['v2.6.20o'] if any('pre_o_installed_sha256' in x for x in m_successor.values()) else []) + (['v2.6.20p'] if any('pre_p_installed_sha256' in x for x in m_successor.values()) else []) + (['v2.6.20q'] if any('pre_q_installed_sha256' in x for x in m_successor.values()) else []),
        'functions': functions,
        'migration_bytes': len(source),
        'migration_sha256': file_sha,
        'platform_sha256': platform,
        'successor_i_capsule': {
            'identity': i_row[0],
            'predecessor_sha256': i_row[1],
            'installed_sha256': i_row[2],
            'actual_sha256': i_row[3],
        },
        'successor_i_migration_bytes': len(i_source),
        'successor_i_migration_sha256': i_file_sha,
        'successor_i_platform_sha256': i_platform,
        'successor_j_capsule': [
            {
                'identity': item[0], 'predecessor_sha256': item[1],
                'installed_sha256': item[2], 'actual_sha256': item[3],
                'j_installed_sha256': k_successor[item[0]]['predecessor_sha256'] if k_successor else item[2],
                'expected_generation': 'K' if k_successor else 'J',
            }
            for item in j_rows
        ],
        'successor_j_migration_bytes': len(j_source),
        'successor_j_migration_sha256': j_file_sha,
        'successor_j_platform_sha256': j_platform,
    }


def owner(cur: psycopg.Cursor) -> dict[str, Any]:
    return base.one(
        cur,
        "select erp.get_owner_financial_snapshot_v2('2026-09-01',current_date,current_date)",
    )


def issue_count(cur: psycopg.Cursor, check_name: str) -> int:
    return int(base.one(
        cur,
        'select issue_count from erp.run_v268_financial_report_checks() where check_name=%s',
        (check_name,),
    ))


def targeted_issues(cur: psycopg.Cursor) -> int:
    return int(base.one(
        cur,
        """select coalesce(sum(issue_count),0)::bigint
           from erp.run_v268_financial_report_checks()
           where check_name in(
             'V2620H_FAILED_WASH_RETURN_TIME_MISMATCH',
             'V2620H_CUSTOMER_AR_STATUS_MISMATCH',
             'V2620H_CUSTOMER_AR_BY_CUSTOMER_MISMATCH',
             'V2620I_SALES_PAYMENT_JOURNAL_LINEAGE_MISMATCH',
             'V268_AR_GL_SUBLEDGER_MISMATCH'
           )""",
    ))


def expect_error(
    cur: psycopg.Cursor, operation: Callable[[], Any], message: str
) -> str:
    cur.execute('savepoint h_expected_error')
    try:
        operation()
    except psycopg.Error as exc:
        actual = str(exc)
        cur.execute('rollback to savepoint h_expected_error')
        cur.execute('release savepoint h_expected_error')
        if message not in actual:
            raise AssertionError(f'Wrong rejection: {actual}') from exc
        return actual.splitlines()[0]
    cur.execute('rollback to savepoint h_expected_error')
    cur.execute('release savepoint h_expected_error')
    raise AssertionError(f'Operation unexpectedly succeeded; expected {message!r}')


def opening_sale(
    cur: psycopg.Cursor, label: str, customer_id: str | None = None
) -> dict[str, str]:
    product = base.create_product(cur, f'H-{label}')
    customer = customer_id or base.create_customer(cur, f'H-{label}')
    opening = str(uuid.uuid4())
    cur.execute(
        """insert into erp.opening_balance_headers(
          id,opening_number,opening_date,status,created_by
        ) values(%s,%s,'2026-09-01','DRAFT',%s)""",
        (opening, f'H-OPEN-{uuid.uuid4()}', base.OPERATOR_APP),
    )
    cur.execute(
        """insert into erp.opening_balance_items(
          opening_id,balance_type,product_id,location_id,qty,unit_cost_snapshot,
          quality_grade,hpp_input_method
        ) values(%s,'FINISHED_GOODS',%s,%s,5,7,'GRADE_A','MANUAL')""",
        (opening, product, base.LOCATION),
    )
    base.one(cur, 'select erp.post_opening_balance(%s)', (opening,))
    sale = base.create_sale(cur, product, customer, 5)
    base.one(cur, 'select erp.post_sale(%s)', (sale['sale_id'],))
    return {
        'product': product,
        'customer': customer,
        'opening': opening,
        'sale': sale['sale_id'],
    }


def post_payment(cur: psycopg.Cursor, sale: str, amount: Decimal) -> str:
    payment = str(uuid.uuid4())
    cur.execute(
        """insert into erp.sales_payments(
          id,sale_id,payment_number,payment_date,amount,cash_account_id,status,created_by
        ) values(%s,%s,%s,clock_timestamp(),%s,
          (select id from erp.cash_accounts where is_active order by cash_account_code limit 1),
          'DRAFT',%s)""",
        (payment, sale, f'H-PAY-{uuid.uuid4()}', amount, base.OPERATOR_APP),
    )
    base.one(cur, 'select erp.post_sales_payment(%s)', (payment,))
    return payment


def ar_for_customer(cur: psycopg.Cursor, customer: str) -> Decimal:
    return Decimal(str(base.one(
        cur,
        """select coalesce(sum(l.debit-l.credit),0)
           from erp.journal_lines l join erp.journal_entries e on e.id=l.journal_entry_id
           where e.status in('POSTED','REVERSED') and l.customer_id=%s
             and l.account_id=erp.account_id('AR_CUSTOMER')""",
        (customer,),
    )))


def case_r02(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = base.fresh(cur, 'a')
    delivery = base.post_delivery(
        cur, fixture, base.BASE_PROCESS, '2026-09-01T11:00:00Z'
    )
    delivery_id = str(delivery['delivery_id'])
    failed = base.action(
        cur,
        'POST_FAILED_WASH',
        {
            'delivery_id': delivery_id,
            'wash_process_id': base.BASE_PROCESS,
            'custody_outcome': 'RETURN_UNPROCESSED',
            'physical_at': '2026-09-02T11:00:00Z',
            'reason': 'H native authoritative full physical return',
            'lines': [{
                'delivery_batch_size_line_id': base.delivery_size_line(cur, delivery_id),
                'qty_attempted_pcs': 10,
            }],
        },
        base.delivery_version(cur, delivery_id),
    )
    inverse = str(base.one(
        cur,
        """select return_wip_event_id from erp.laundry_failed_wash_attempts
           where receipt_id=%s""",
        (failed['receipt_id'],),
    ))
    baseline = owner(cur)['data_confidence']['status']
    if baseline != 'READY' or targeted_issues(cur) != 0:
        raise AssertionError('R02 lawful baseline is not READY')
    cur.execute('savepoint h_r02_fault')
    cur.execute(
        "update erp.wip_stage_events set physical_at='2026-09-01T12:00:00Z' where id=%s",
        (inverse,),
    )
    blocked_issue = issue_count(cur, 'V2620H_FAILED_WASH_RETURN_TIME_MISMATCH')
    blocked_status = owner(cur)['data_confidence']['status']
    if blocked_issue != 1 or blocked_status != 'BLOCKED':
        raise AssertionError(
            f'R02 fault escaped: issue={blocked_issue}, status={blocked_status}'
        )
    cur.execute('rollback to savepoint h_r02_fault')
    cur.execute('release savepoint h_r02_fault')
    restored = owner(cur)['data_confidence']['status']
    if restored != 'READY' or targeted_issues(cur) != 0:
        raise AssertionError('R02 rollback did not restore READY baseline')
    return {
        'status': 'PASS',
        'dispatch_physical_at': '2026-09-01T11:00:00Z',
        'authoritative_return_physical_at': '2026-09-02T11:00:00Z',
        'fault_inverse_physical_at': '2026-09-01T12:00:00Z',
        'fault_issue_count': blocked_issue,
        'fault_report_status': blocked_status,
        'restored_report_status': restored,
    }


def case_r03_underpaid(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = opening_sale(cur, 'UNDERPAID')
    first = post_payment(cur, fixture['sale'], Decimal('99.99'))
    status_after_first = base.one(
        cur, 'select status from erp.sales_headers where id=%s', (fixture['sale'],)
    )
    ar_after_first = ar_for_customer(cur, fixture['customer'])
    if status_after_first != 'PARTIAL_PAID' or ar_after_first != Decimal('.01'):
        raise AssertionError(
            f'99.99 boundary mismatch: {status_after_first}, AR {ar_after_first}'
        )
    final = post_payment(cur, fixture['sale'], Decimal('.01'))
    status_final = base.one(
        cur, 'select status from erp.sales_headers where id=%s', (fixture['sale'],)
    )
    ar_final = ar_for_customer(cur, fixture['customer'])
    if status_final != 'PAID' or ar_final != 0 or targeted_issues(cur) != 0:
        raise AssertionError(f'Final cent not settled exactly: {status_final}, AR {ar_final}')

    base.one(cur, "select erp.reverse_sales_payment(%s,'H exact-cent inverse')", (final,))
    inverse_partial = base.one(
        cur, 'select status from erp.sales_headers where id=%s', (fixture['sale'],)
    )
    base.one(cur, "select erp.reverse_sales_payment(%s,'H remaining-payment inverse')", (first,))
    inverse_open = base.one(
        cur, 'select status from erp.sales_headers where id=%s', (fixture['sale'],)
    )
    if inverse_partial != 'PARTIAL_PAID' or inverse_open != 'POSTED':
        raise AssertionError(f'Payment inverse status mismatch: {inverse_partial}/{inverse_open}')

    lifecycle = opening_sale(cur, 'RETURN-LIFECYCLE')
    post_payment(cur, lifecycle['sale'], Decimal('60'))
    return_id = base.insert_return(
        cur, lifecycle['sale'], lifecycle['customer'], 2, Decimal('40'), 2
    )
    base.one(cur, 'select erp.post_sales_return(%s)', (return_id,))
    after_return = base.one(
        cur, 'select status from erp.sales_headers where id=%s', (lifecycle['sale'],)
    )
    ar_after_return = ar_for_customer(cur, lifecycle['customer'])
    base.one(
        cur,
        "select erp.reverse_sales_return(%s,'H exact-cent lawful return inverse')",
        (return_id,),
    )
    after_return_inverse = base.one(
        cur, 'select status from erp.sales_headers where id=%s', (lifecycle['sale'],)
    )
    ar_after_return_inverse = ar_for_customer(cur, lifecycle['customer'])
    if (
        after_return != 'PAID'
        or ar_after_return != 0
        or after_return_inverse != 'PARTIAL_PAID'
        or ar_after_return_inverse != Decimal('40')
        or targeted_issues(cur) != 0
    ):
        raise AssertionError(
            'Lawful return/reversal exact status or AR mismatch: '
            f'{after_return}/{ar_after_return} -> '
            f'{after_return_inverse}/{ar_after_return_inverse}'
        )
    return {
        'status': 'PASS',
        'after_99_99': {'sale_status': status_after_first, 'customer_ar': str(ar_after_first)},
        'after_0_01': {'sale_status': status_final, 'customer_ar': str(ar_final)},
        'inverse_statuses': [inverse_partial, inverse_open],
        'lawful_return_lifecycle': {
            'after_return': {'sale_status': after_return, 'customer_ar': str(ar_after_return)},
            'after_inverse': {
                'sale_status': after_return_inverse,
                'customer_ar': str(ar_after_return_inverse),
            },
        },
    }


def case_r03_paid_return(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = opening_sale(cur, 'PAID-RETURN')
    post_payment(cur, fixture['sale'], Decimal('100'))
    return_id = base.insert_return(
        cur, fixture['sale'], fixture['customer'], 1, Decimal('.01'), 1
    )
    before = base.row(
        cur,
        """select (select count(*) from erp.fg_stock_movements),
                  (select count(*) from erp.journal_entries),
                  (select cached_qty_pcs from erp.fg_lots where product_id=%s),
                  (select status from erp.sales_returns where id=%s)""",
        (fixture['product'], return_id),
    )
    rejected = expect_error(
        cur,
        lambda: base.one(cur, 'select erp.post_sales_return(%s)', (return_id,)),
        'membuat pembayaran customer melebihi nilai penjualan tersisa',
    )
    after = base.row(
        cur,
        """select (select count(*) from erp.fg_stock_movements),
                  (select count(*) from erp.journal_entries),
                  (select cached_qty_pcs from erp.fg_lots where product_id=%s),
                  (select status from erp.sales_returns where id=%s)""",
        (fixture['product'], return_id),
    )
    if before != after or after[3] != 'DRAFT' or targeted_issues(cur) != 0:
        raise AssertionError(f'Paid-return rejection was not atomic: {before} -> {after}')
    return {'status': 'PASS', 'rejected': rejected, 'before': before, 'after': after}


def case_r03_overpaid(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = opening_sale(cur, 'OVERPAID')
    payment = str(uuid.uuid4())
    cur.execute(
        """insert into erp.sales_payments(
          id,sale_id,payment_number,payment_date,amount,cash_account_id,status,created_by
        ) values(%s,%s,%s,clock_timestamp(),100.01,
          (select id from erp.cash_accounts where is_active order by cash_account_code limit 1),
          'DRAFT',%s)""",
        (payment, fixture['sale'], f'H-OVERPAY-{uuid.uuid4()}', base.OPERATOR_APP),
    )
    before_journals = int(base.one(cur, 'select count(*) from erp.journal_entries'))
    rejected = expect_error(
        cur,
        lambda: base.one(cur, 'select erp.post_sales_payment(%s)', (payment,)),
        'exceeds exact remaining receivable',
    )
    after_journals = int(base.one(cur, 'select count(*) from erp.journal_entries'))
    payment_status = base.one(
        cur, 'select status from erp.sales_payments where id=%s', (payment,)
    )
    sale_status = base.one(
        cur, 'select status from erp.sales_headers where id=%s', (fixture['sale'],)
    )
    if (
        before_journals != after_journals
        or payment_status != 'DRAFT'
        or sale_status != 'POSTED'
        or targeted_issues(cur) != 0
    ):
        raise AssertionError('Overpayment rejection was not atomic and report-safe')
    return {
        'status': 'PASS',
        'rejected': rejected,
        'journal_delta': after_journals - before_journals,
        'payment_status': payment_status,
        'sale_status': sale_status,
    }


def case_r03_detectors(cur: psycopg.Cursor) -> dict[str, Any]:
    first = opening_sale(cur, 'DETECT-A')
    second = opening_sale(cur, 'DETECT-B')
    post_payment(cur, first['sale'], Decimal('99.99'))
    if targeted_issues(cur) != 0:
        raise AssertionError('Detector baseline is not clean')

    cur.execute('savepoint h_status_fault')
    cur.execute("update erp.sales_headers set status='PAID' where id=%s", (first['sale'],))
    status_issue = issue_count(cur, 'V2620H_CUSTOMER_AR_STATUS_MISMATCH')
    status_confidence = owner(cur)['data_confidence']['status']
    cur.execute('rollback to savepoint h_status_fault')
    cur.execute('release savepoint h_status_fault')
    if status_issue != 1 or status_confidence != 'BLOCKED':
        raise AssertionError('Incorrect PAID status escaped exact detector')

    cur.execute('savepoint h_customer_fault')
    cur.execute("set local session_replication_role='replica'")
    cur.execute(
        """update erp.journal_lines l set customer_id=%s
           from erp.journal_entries e
           where e.id=l.journal_entry_id and e.source_type='SALE' and e.source_id=%s
             and l.account_id=erp.account_id('AR_CUSTOMER')""",
        (second['customer'], first['sale']),
    )
    customer_issue = issue_count(cur, 'V2620H_CUSTOMER_AR_BY_CUSTOMER_MISMATCH')
    global_issue = issue_count(cur, 'V268_AR_GL_SUBLEDGER_MISMATCH')
    customer_confidence = owner(cur)['data_confidence']['status']
    cur.execute('rollback to savepoint h_customer_fault')
    cur.execute('release savepoint h_customer_fault')
    if customer_issue < 1 or global_issue != 0 or customer_confidence != 'BLOCKED':
        raise AssertionError(
            f'Cross-customer wash escaped: per={customer_issue}, global={global_issue}, '
            f'status={customer_confidence}'
        )
    if targeted_issues(cur) != 0 or owner(cur)['data_confidence']['status'] != 'READY':
        raise AssertionError('Detector fault rollback did not restore READY')
    return {
        'status': 'PASS',
        'incorrect_paid': {'issue_count': status_issue, 'report': status_confidence},
        'cross_customer_wash': {
            'per_customer_issue_count': customer_issue,
            'global_issue_count': global_issue,
            'report': customer_confidence,
        },
        'restored_report': 'READY',
    }


def run() -> dict[str, Any]:
    result: dict[str, Any] = {
        'head': HEAD,
        'classification': 'DISPOSABLE_NATIVE_POSTGRESQL_AFTER_E_F_G_H_I',
        'production_go': False,
        'cases': {},
    }
    if not PGURL:
        raise AssertionError('PGURL is required')
    with psycopg.connect(PGURL, autocommit=False) as conn, conn.cursor() as cur:
        cur.execute(
            "set local timezone='UTC'; set local statement_timeout='180s'; set local lock_timeout='8s'"
        )
        result['runtime'] = exact_runtime(cur)
        cur.execute(
            "select set_config('request.jwt.claims',%s,true)",
            (json.dumps({'sub': base.OPERATOR_AUTH, 'role': 'authenticated'}),),
        )
        cur.execute("select set_config('app.change_reason','H expanded audit regression',true)")
        base.load_fixture_foundation(cur)
        cases: tuple[tuple[str, Callable[[psycopg.Cursor], dict[str, Any]]], ...] = (
            ('R02_WIP_RETURN_CLOCK', case_r02),
            ('R03_UNDERPAID_FINAL_CENT_AND_INVERSES', case_r03_underpaid),
            ('R03_PAID_RETURN_ATOMIC_REFUSAL', case_r03_paid_return),
            ('R03_OVERPAYMENT_ATOMIC_REFUSAL', case_r03_overpaid),
            ('R03_STATUS_AND_PER_CUSTOMER_DETECTORS', case_r03_detectors),
        )
        for name, case in cases:
            cur.execute('savepoint h_case')
            try:
                result['cases'][name] = case(cur)
            except Exception as exc:
                result['cases'][name] = {
                    'status': 'FAIL',
                    'error': str(exc),
                    'sqlstate': getattr(exc, 'sqlstate', None),
                }
            finally:
                cur.execute('rollback to savepoint h_case')
                cur.execute('release savepoint h_case')
        if base.one(cur, 'select count(*) from erp.cp6_laundry_qc_execution_context') != 0:
            raise AssertionError('H regression left execution-context residue')
        conn.rollback()
    result['all_case_effects_rolled_back'] = True
    result['status'] = (
        'PASS'
        if all(case['status'] == 'PASS' for case in result['cases'].values())
        else 'FAIL'
    )
    return result


def main() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = run()
    except Exception as exc:
        result = {
            'head': HEAD,
            'status': 'FAIL',
            'error': str(exc),
            'production_go': False,
        }
    REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps(result, sort_keys=True, default=str))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
