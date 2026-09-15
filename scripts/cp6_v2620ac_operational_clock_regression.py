#!/usr/bin/env python3
"""Focused AC long-transaction regression for operational business clocks.

This test-only wrapper reuses the already-qualified physical PostgreSQL clock
harness without changing any installed function.  A fresh transaction and a
transaction held across Jakarta midnight receive the same lawful input.  Every
case rolls back and the copied database is destroyed by the shared harness.
"""
from __future__ import annotations

import hashlib
import json
import os
import traceback
import uuid
from datetime import datetime, time as daytime, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg

import cp6_aa_midnight_audit as clock
import cp6_aa_invoice_partial_audit as invoice
import cp6_v2620h_adversarial_regression as payment_fixture
import cp6_v2620ac_runtime as runtime


prior, one, base = invoice.prior, invoice.one, invoice.base
REPORT = Path(
    'cp6-proof/writer-ac/AC_OPERATIONAL_CLOCK_REGRESSION.json'
)
ROOT = REPORT.parent / 'operational-clock'
FRESH_CONTROLS: dict[str, dict] = {}


def verified_ac_runtime(cur):
    objects = runtime.verified_successor(cur)
    if len(objects) != 272:
        raise AssertionError('AC_OPERATIONAL_EXACT_INSTALLED_AC_REQUIRED')
    return objects


def error_detail(exc: psycopg.Error) -> dict[str, str | None]:
    return {
        'sqlstate': exc.sqlstate,
        'message': exc.diag.message_primary,
    }


def payment_case(cur: psycopg.Cursor, new_day) -> dict:
    """Post a lawful new-day customer payment through the ordinary OWNER RPC."""
    prior.as_admin(cur)
    fixture = payment_fixture.opening_sale(
        cur, 'AC-OP-CLOCK-' + uuid.uuid4().hex[:10]
    )
    payment = uuid.uuid4()
    physical_at = one(cur, 'select clock_timestamp()')
    cash = one(
        cur,
        'select id from erp.cash_accounts where is_active '
        'order by cash_account_code limit 1',
    )
    cur.execute(
        """insert into erp.sales_payments(
          id,sale_id,payment_number,payment_date,amount,cash_account_id,
          status,created_by
        ) values(%s,%s,%s,%s,.01,%s,'DRAFT',%s)""",
        (
            payment, fixture['sale'], 'AC-OP-PAY-' + str(payment), physical_at,
            cash, base.OPERATOR_APP,
        ),
    )
    prior.as_owner(cur)
    cur.execute('savepoint ab_operational_payment')
    failure = None
    try:
        cur.execute('select erp.post_sales_payment(%s)', (payment,))
    except psycopg.Error as exc:
        failure = error_detail(exc)
        cur.execute('rollback to savepoint ab_operational_payment')
    cur.execute('release savepoint ab_operational_payment')

    evidence = {
        'operation': 'CUSTOMER_PAYMENT',
        'ordinary_owner_post': True,
        'admin_seeded_draft_only': True,
        'payment_id': str(payment),
        'sale_id': fixture['sale'],
        'physical_at': physical_at,
        'expected_business_date': str(new_day),
        'operation_error': failure,
        'status': 'INCOMPLETE',
    }
    if failure is not None:
        return evidence

    prior.as_admin(cur)
    status, created_day = cur.execute(
        "select status,(created_at at time zone 'Asia/Jakarta')::date::text "
        "from erp.sales_payments where id=%s",
        (payment,),
    ).fetchone()
    rows = cur.execute(
        """select e.id::text,e.economic_date::text,e.transaction_date::text,
          (posting_at at time zone 'Asia/Jakarta')::date::text,
          round(sum(debit),2)::text,round(sum(credit),2)::text
        from erp.journal_entries e join erp.journal_lines l
          on l.journal_entry_id=e.id
        where e.source_type='SALES_PAYMENT' and e.source_id=%s
        group by e.id,e.economic_date,e.transaction_date,e.posting_at""",
        (payment,),
    ).fetchall()
    evidence.update(
        document_status=status,
        created_at_business_day=created_day,
        journals=rows,
    )
    correct = (
        status == 'POSTED'
        and created_day == str(new_day)
        and len(rows) == 1
        and rows[0][1] == str(new_day)
        and rows[0][2] == str(new_day)
        and rows[0][3] == str(new_day)
        and Decimal(rows[0][4]) == Decimal('.01')
        and Decimal(rows[0][5]) == Decimal('.01')
    )
    evidence['status'] = 'CONTROL_PASS' if correct else 'COUNTEREXAMPLE'
    evidence['classification'] = (
        'LAWFUL_NEW_DAY_CUSTOMER_PAYMENT'
        if correct else 'CUSTOMER_PAYMENT_WRONG_OPERATIONAL_DAY'
    )
    if not correct:
        evidence['severity'] = 'P2'
    return evidence


def close_case(cur: psycopg.Cursor, old_day) -> dict:
    """Close yesterday after midnight through the ordinary OWNER function."""
    prior.as_owner(cur)
    cur.execute('savepoint ab_operational_close')
    failure = None
    observed = None
    try:
        cur.execute(
            'select erp.close_accounting_through(%s,%s)',
            (old_day, 'AC operational clock independent close'),
        )
        prior.as_admin(cur)
        observed = one(
            cur,
            'select closed_through::text from erp.accounting_period_control '
            'where singleton_id=1',
        )
    except psycopg.Error as exc:
        failure = error_detail(exc)
        cur.execute('rollback to savepoint ab_operational_close')
    cur.execute('release savepoint ab_operational_close')
    return {
        'operation': 'ACCOUNTING_CLOSE',
        'ordinary_owner_call': True,
        'target_closed_through': str(old_day),
        'observed_closed_through': observed,
        'operation_error': failure,
        'status': (
            'CONTROL_PASS'
            if failure is None and observed == str(old_day)
            else 'COUNTEREXAMPLE' if failure is None
            else 'INCOMPLETE'
        ),
        'classification': 'LAWFUL_PRIOR_DAY_ACCOUNTING_CLOSE',
    }


def current_view_case(cur: psycopg.Cursor, new_day) -> dict:
    """Prove a current view advances after transaction start, within one query."""
    prior.as_admin(cur)
    effective_from = datetime.combine(
        new_day, daytime(0, 0, 1), tzinfo=prior.JAKARTA
    )
    cur.execute('savepoint ac_current_view_probe')
    try:
        product_id = base.create_product(
            cur, 'AC-CURRENT-VIEW-' + uuid.uuid4().hex[:12]
        )
        version_id = uuid.uuid4()
        cur.execute(
            """insert into erp.product_price_versions(
              id,product_id,price,effective_from,effective_to,change_note,
              created_by
            ) values(%s,%s,.01,%s,null,
              'AC deterministic statement-clock view probe',%s)""",
            (version_id, product_id, effective_from, base.OPERATOR_APP),
        )
        created_at = one(
            cur,
            'select created_at from erp.product_price_versions where id=%s',
            (version_id,),
        )
        observed = cur.execute(
            "select effective_from from erp.v_current_product_prices "
            "where product_id=%s",
            (product_id,),
        ).fetchone()
    finally:
        cur.execute('rollback to savepoint ac_current_view_probe')
        cur.execute('release savepoint ac_current_view_probe')
    created_day = created_at.astimezone(prior.JAKARTA).date()
    correct = (
        observed is not None
        and observed[0] == effective_from
        and created_day == new_day
    )
    return {
        'status': 'CONTROL_PASS' if correct else 'COUNTEREXAMPLE',
        'classification': (
            'STATEMENT_STABLE_CURRENT_VIEW'
            if correct else 'CURRENT_VIEW_FROZEN_AT_TRANSACTION_START'
        ),
        'view': 'erp.v_current_product_prices',
        'product_id': str(product_id),
        'price_version_id': str(version_id),
        'effective_from': effective_from,
        'observed_effective_from': observed[0] if observed else None,
        'created_at': created_at,
        'created_at_business_day': str(created_day),
        'admin_seeded_single_version_fixture_only': True,
    }


def owner_report_case(cur: psycopg.Cursor, new_day) -> dict:
    """Use the ordinary OWNER report with its production two-argument call."""
    prior.as_owner(cur)
    cur.execute('savepoint ab_operational_owner_report')
    failure = None
    report = None
    try:
        report = one(
            cur,
            'select erp.get_owner_financial_snapshot_v2(%s,%s)',
            (new_day, new_day),
        )
    except psycopg.Error as exc:
        failure = error_detail(exc)
        cur.execute('rollback to savepoint ab_operational_owner_report')
    cur.execute('release savepoint ab_operational_owner_report')
    basis = (report or {}).get('basis') or {}
    view_clock = current_view_case(cur, new_day)
    correct = (
        failure is None
        and basis.get('period_from') == str(new_day)
        and basis.get('period_to') == str(new_day)
        and basis.get('balance_sheet_as_of') == str(new_day)
        and (report.get('data_confidence') or {}).get('status')
        in ('READY', 'RECALC_PENDING', 'BLOCKED')
        and view_clock.get('status') == 'CONTROL_PASS'
    )
    return {
        'operation': 'OWNER_REPORT_DEFAULT_AS_OF',
        'ordinary_owner_call': True,
        'two_argument_production_call': True,
        'expected_default_as_of': str(new_day),
        'observed_basis': basis,
        'observed_confidence': (report or {}).get('data_confidence'),
        'current_view_clock': view_clock,
        'operation_error': failure,
        'status': (
            'CONTROL_PASS' if correct
            else 'INCOMPLETE' if failure is not None
            or view_clock.get('status') == 'INCOMPLETE'
            else 'COUNTEREXAMPLE'
        ),
        'classification': 'OWNER_REPORT_CURRENT_OPERATIONAL_DAY',
    }


def supplier_invoice_case(cur: psycopg.Cursor, new_day) -> dict:
    """Finalize a valid current-day supplier invoice as the ordinary OWNER."""
    prior.as_admin(cur)
    fixture = invoice.estimated_receipt(cur, new_day)
    version = int(one(
        cur,
        'select row_version from erp.material_purchase_headers where id=%s',
        (fixture['purchase'],),
    ))
    invoice_number = 'AC-OP-INV-' + str(uuid.uuid4())
    request_id = uuid.uuid4()
    physical_at = one(cur, 'select clock_timestamp()')
    payload = {
        'purchase_id': fixture['purchase'],
        'supplier_invoice_number': invoice_number,
        'invoice_date': new_day,
        'received_at': physical_at,
        'reason': 'AC operational clock current-day supplier invoice',
        'lines': [{
            'purchase_item_id': fixture['item'],
            'qty_invoiced': 10,
            'final_unit_price': 20,
        }],
    }
    cur.execute('savepoint ab_operational_supplier_invoice')
    failure = None
    response = None
    try:
        response = invoice.rpc(
            cur,
            'erp.finalize_material_purchase_invoice_v2',
            payload,
            request_id,
            version,
        )
    except psycopg.Error as exc:
        failure = error_detail(exc)
        cur.execute('rollback to savepoint ab_operational_supplier_invoice')
    cur.execute('release savepoint ab_operational_supplier_invoice')
    evidence = {
        'operation': 'SUPPLIER_INVOICE',
        'ordinary_owner_finalize': True,
        'admin_seeded_masters_and_draft_only': True,
        'purchase_id': str(fixture['purchase']),
        'invoice_number': invoice_number,
        'invoice_date': str(new_day),
        'received_at': physical_at,
        'operation_error': failure,
        'response': response,
        'status': 'INCOMPLETE',
    }
    if failure is not None:
        return evidence
    prior.as_admin(cur)
    invoice_id = uuid.UUID(response['supplier_invoice_id'])
    evidence['invoice_id'] = str(invoice_id)
    rows = cur.execute(
        """select h.status,j.economic_date::text,j.transaction_date::text,
          round(sum(l.debit),2)::text,round(sum(l.credit),2)::text
          ,(h.created_at at time zone 'Asia/Jakarta')::date::text
          ,(h.posted_at at time zone 'Asia/Jakarta')::date::text
        from erp.material_supplier_invoices h
        join erp.journal_entries j
          on j.source_type='MATERIAL_SUPPLIER_INVOICE' and j.source_id=h.id
        join erp.journal_lines l on l.journal_entry_id=j.id
        where h.id=%s
        group by h.status,h.created_at,h.posted_at,
          j.id,j.economic_date,j.transaction_date""",
        (invoice_id,),
    ).fetchall()
    correct = (
        len(rows) == 1
        and rows[0][0] == 'POSTED'
        and rows[0][1] == str(new_day)
        and rows[0][2] == str(new_day)
        and Decimal(rows[0][3]) == Decimal(rows[0][4])
        and Decimal(rows[0][3]) > 0
        and rows[0][5] == str(new_day)
        and rows[0][6] == str(new_day)
    )
    evidence.update(
        journals=rows,
        status='CONTROL_PASS' if correct else 'COUNTEREXAMPLE',
        classification=(
            'LAWFUL_CURRENT_DAY_SUPPLIER_INVOICE'
            if correct else 'SUPPLIER_INVOICE_WRONG_OPERATIONAL_DAY'
        ),
    )
    if not correct:
        evidence['severity'] = 'P1'
    return evidence


def payroll_payment_case(cur: psycopg.Cursor, new_day) -> dict:
    """Pay a valid approved one-unit payroll on the current business day."""
    contractor = uuid.uuid4()
    payroll = uuid.uuid4()
    prior.as_admin(cur)
    cash = one(
        cur,
        'select id from erp.cash_accounts where is_active '
        'order by cash_account_code limit 1',
    )
    cur.execute(
        """insert into erp.contractors(
          id,contractor_code,contractor_name,contractor_type,
          attendance_required
        ) values(%s,%s,%s,'MANDOR',false)""",
        (
            contractor,
            'AC-OP-PAYROLL-' + contractor.hex[:12],
            'AC operational clock payroll contractor',
        ),
    )
    cur.execute(
        """insert into erp.payroll_settlements(
          id,payroll_number,contractor_id,period_start,period_end,status,
          payment_cash_account_id,payment_date,manual_adjustment,notes
        ) values(%s,%s,%s,%s,%s,'DRAFT',%s,%s,1,
          'AC operational clock current-day payroll')""",
        (
            payroll,
            'AC-OP-PAY-' + payroll.hex[:16],
            contractor,
            new_day - timedelta(days=1),
            new_day - timedelta(days=1),
            cash,
            new_day,
        ),
    )
    prior.as_owner(cur)
    cur.execute('select erp.populate_payroll_draft(%s)', (payroll,))
    cur.execute('select erp.approve_payroll(%s)', (payroll,))
    approved = cur.execute(
        'select status,net_payable from erp.payroll_settlements '
        'where id=%s',
        (payroll,),
    ).fetchone()
    if approved[0] != 'APPROVED' or Decimal(approved[1]) != Decimal('1.00'):
        raise AssertionError('AC_OPERATIONAL_PAYROLL_APPROVAL_NOT_QUALIFIED')
    cur.execute('savepoint ab_operational_payroll_payment')
    failure = None
    try:
        cur.execute('select erp.post_payroll_payment(%s)', (payroll,))
    except psycopg.Error as exc:
        failure = error_detail(exc)
        cur.execute('rollback to savepoint ab_operational_payroll_payment')
    cur.execute('release savepoint ab_operational_payroll_payment')
    evidence = {
        'operation': 'PAYROLL_PAYMENT',
        'ordinary_owner_approval_and_payment': True,
        'admin_seeded_master_and_draft_only': True,
        'payroll_id': str(payroll),
        'payment_date': str(new_day),
        'approved_net_payable': str(approved[1]),
        'operation_error': failure,
        'status': 'INCOMPLETE',
    }
    if failure is not None:
        return evidence
    prior.as_admin(cur)
    rows = cur.execute(
        """select h.status,j.economic_date::text,j.transaction_date::text,
          round(sum(l.debit),2)::text,round(sum(l.credit),2)::text
          ,(h.created_at at time zone 'Asia/Jakarta')::date::text
          ,(h.settled_at at time zone 'Asia/Jakarta')::date::text
        from erp.payroll_settlements h
        join erp.journal_entries j
          on j.source_type='PAYROLL_PAYMENT' and j.source_id=h.id
        join erp.journal_lines l on l.journal_entry_id=j.id
        where h.id=%s
        group by h.status,h.created_at,h.settled_at,
          j.id,j.economic_date,j.transaction_date""",
        (payroll,),
    ).fetchall()
    correct = (
        len(rows) == 1
        and rows[0][0] == 'PAID'
        and rows[0][1] == str(new_day)
        and rows[0][2] == str(new_day)
        and Decimal(rows[0][3]) == Decimal('1.00')
        and Decimal(rows[0][4]) == Decimal('1.00')
        and rows[0][5] == str(new_day)
        and rows[0][6] == str(new_day)
    )
    evidence.update(
        journals=rows,
        status='CONTROL_PASS' if correct else 'COUNTEREXAMPLE',
        classification=(
            'LAWFUL_CURRENT_DAY_PAYROLL_PAYMENT'
            if correct else 'PAYROLL_PAYMENT_WRONG_OPERATIONAL_DAY'
        ),
    )
    if not correct:
        evidence['severity'] = 'P1'
    return evidence


def qualify_probe(kind: str, evidence: dict, long_transaction: bool) -> dict:
    """Only a matching fresh control can qualify a long-transaction refusal."""
    if not long_transaction:
        FRESH_CONTROLS[kind] = evidence.copy()
        return evidence
    failure = evidence.get('operation_error')
    control = FRESH_CONTROLS.get(kind)
    if not failure or not control or control.get('status') != 'CONTROL_PASS':
        return evidence
    message = (failure.get('message') or '').lower()
    expected = failure.get('sqlstate') == 'P0001' and {
        'CUSTOMER_PAYMENT': 'future' in message or 'masa depan' in message,
        'SUPPLIER_INVOICE': 'future' in message,
        'PAYROLL_PAYMENT': 'masa depan' in message or 'future' in message,
        'ACCOUNTING_CLOSE': 'tutup buku hanya boleh' in message,
        'OWNER_REPORT_DEFAULT_AS_OF': 'p_to cannot be after p_as_of' in message,
    }[kind]
    if expected:
        evidence.update(
            status='COUNTEREXAMPLE',
            severity='P2',
            classification={
                'CUSTOMER_PAYMENT': (
                    'LAWFUL_NEW_DAY_CUSTOMER_PAYMENT_FALSE_REFUSAL'
                ),
                'ACCOUNTING_CLOSE': (
                    'LAWFUL_PRIOR_DAY_ACCOUNTING_CLOSE_FALSE_REFUSAL'
                ),
                'SUPPLIER_INVOICE': (
                    'LAWFUL_CURRENT_DAY_SUPPLIER_INVOICE_FALSE_REFUSAL'
                ),
                'PAYROLL_PAYMENT': (
                    'LAWFUL_CURRENT_DAY_PAYROLL_PAYMENT_FALSE_REFUSAL'
                ),
                'OWNER_REPORT_DEFAULT_AS_OF': (
                    'OWNER_CURRENT_DAY_REPORT_FALSE_REFUSAL'
                ),
            }[kind],
            paired_fresh_control=True,
        )
    return evidence


def paired_case(old_day, long_transaction: bool, close_operation: bool) -> dict:
    old_start = datetime.combine(
        old_day, daytime(23, 59, 50), tzinfo=prior.JAKARTA
    )
    new_start = datetime.combine(
        old_day + timedelta(days=1), daytime(0, 0, 5), tzinfo=prior.JAKARTA
    )
    setup_clock = clock.set_clock(old_start if long_transaction else new_start)
    kind = 'ACCOUNTING_CLOSE' if close_operation else 'CUSTOMER_PAYMENT'
    with clock.connect() as conn, conn.cursor() as cur:
        cur.execute(
            "set local timezone='Asia/Jakarta';"
            "set local statement_timeout='180s';set local lock_timeout='8s'"
        )
        before = prior.stable_boundary(cur)
        initial_clock = clock.clocks(cur)
        change_clock = clock.set_clock(new_start) if long_transaction else None
        after_clock = clock.clocks(cur)
        if (
            initial_clock['transaction_id'] != after_clock['transaction_id']
            or initial_clock['transaction'] != after_clock['transaction']
        ):
            raise AssertionError('AC_OPERATIONAL_TRANSACTION_NOT_PRESERVED')
        wanted_transaction_day = old_day if long_transaction else old_day + timedelta(days=1)
        if (
            after_clock['transaction'].astimezone(prior.JAKARTA).date()
            != wanted_transaction_day
            or after_clock['statement'].astimezone(prior.JAKARTA).date()
            != old_day + timedelta(days=1)
            or after_clock['wall'].astimezone(prior.JAKARTA).date()
            != old_day + timedelta(days=1)
        ):
            raise AssertionError('AC_OPERATIONAL_MIDNIGHT_NOT_QUALIFIED')

        probes = {}
        try:
            if close_operation:
                probes['ACCOUNTING_CLOSE'] = close_case(cur, old_day)
            else:
                probes['OWNER_REPORT_DEFAULT_AS_OF'] = owner_report_case(
                    cur, old_day + timedelta(days=1)
                )
                probes['CUSTOMER_PAYMENT'] = payment_case(
                    cur, old_day + timedelta(days=1)
                )
                probes['SUPPLIER_INVOICE'] = supplier_invoice_case(
                    cur, old_day + timedelta(days=1)
                )
                probes['PAYROLL_PAYMENT'] = payroll_payment_case(
                    cur, old_day + timedelta(days=1)
                )
        except Exception as exc:
            probes[kind] = {
                'operation': kind,
                'status': 'INCOMPLETE',
                'error': str(exc),
                'traceback': traceback.format_exc(),
            }
        for probe_kind, probe in probes.items():
            qualify_probe(probe_kind, probe, long_transaction)
        statuses = {probe.get('status') for probe in probes.values()}
        evidence = dict(
            operation=kind,
            probes=probes,
            status=(
                'INCOMPLETE' if 'INCOMPLETE' in statuses
                else 'COUNTEREXAMPLE' if 'COUNTEREXAMPLE' in statuses
                else 'CONTROL_PASS'
            ),
            long_transaction=long_transaction,
            setup_clock=setup_clock,
            change_clock=change_clock,
            initial_clock=initial_clock,
            after_clock=after_clock,
        )
        conn.rollback()
        prior.as_admin(cur)
        evidence['full_boundary_restored'] = prior.stable_boundary(cur) == before
        conn.rollback()
        if not evidence['full_boundary_restored']:
            evidence['status'] = 'INCOMPLETE'
        return evidence


def run() -> dict:
    if os.environ.get('CP6_AB_PHASE') != 'AC_REGRESSION':
        raise AssertionError('AC_OPERATIONAL_AUDIT_REQUIRES_INSTALLED_AC_PHASE')
    head, tree = runtime.verify_audit_source()
    phase = 'AC_REGRESSION'

    FRESH_CONTROLS.clear()
    clock.ROOT = ROOT
    clock.REPORT = REPORT
    clock.paired_case = paired_case
    clock.verify_repository_source = lambda: (phase, head, tree)
    clock.verify_source_runtime = verified_ac_runtime
    result = clock.run()
    harness_status = result.get('status')
    physical_harness_complete = (
        harness_status in ('PASS_BOUNDED_AUDIT', 'FAIL_NEW_COUNTEREXAMPLE')
        and not result.get('cleanup_errors')
        and result.get('remaining_clock_containers') == 0
        and result.get('source_boundary_unchanged') is True
        and result.get('source_clock_still_real') is True
    )
    renamed = {}
    mapping = {
        'FRESH:PRIOR_DAY_SOURCE': ('FRESH', (
            'OWNER_REPORT_DEFAULT_AS_OF', 'CUSTOMER_PAYMENT',
            'SUPPLIER_INVOICE', 'PAYROLL_PAYMENT')),
        'LONG:PRIOR_DAY_SOURCE': ('LONG', (
            'OWNER_REPORT_DEFAULT_AS_OF', 'CUSTOMER_PAYMENT',
            'SUPPLIER_INVOICE', 'PAYROLL_PAYMENT')),
        'FRESH:CURRENT_DAY_SOURCE': ('FRESH', ('ACCOUNTING_CLOSE',)),
        'LONG:CURRENT_DAY_SOURCE': ('LONG', ('ACCOUNTING_CLOSE',)),
    }
    for raw_name, (transaction_kind, operations) in mapping.items():
        raw = result['cases'][raw_name]
        for operation in operations:
            probe = dict(raw.get('probes', {}).get(operation, {}))
            probe.update(
                long_transaction=raw.get('long_transaction'),
                setup_clock=raw.get('setup_clock'),
                change_clock=raw.get('change_clock'),
                initial_clock=raw.get('initial_clock'),
                after_clock=raw.get('after_clock'),
                full_boundary_restored=raw.get('full_boundary_restored'),
            )
            if not probe.get('full_boundary_restored'):
                probe['status'] = 'INCOMPLETE'
            renamed[f'{operation}:{transaction_kind}'] = probe
    result.update(
        format='CP6_V2620AC_OPERATIONAL_CLOCK_REGRESSION_V1',
        head=head,
        tree=tree,
        cases=renamed,
        expected_cases=10,
        physical_harness_complete=physical_harness_complete,
        independent_acceptance_complete=False,
        runtime_generation='AC',
        business_predecessor_head=runtime.AB_HEAD,
        audit_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        reused_physical_harness_sha256=result.pop('source_sha256'),
        audit_scope=[
            'erp.post_sales_payment(uuid)',
            'erp.close_accounting_through(date,text)',
            'erp.get_owner_financial_snapshot_v2(date,date,date)',
            'erp.post_material_supplier_invoice(uuid)',
            'erp.post_payroll_payment(uuid)',
            'erp.v_current_product_prices',
            'erp.product_price_versions.created_at default',
            'erp.sales_payments.created_at default',
            'erp.journal_entries.posting_at default',
        ],
        production_go=False,
    )
    result['controls'] = sum(
        case['status'] == 'CONTROL_PASS' for case in renamed.values()
    )
    result['counterexamples'] = sum(
        case['status'] == 'COUNTEREXAMPLE' for case in renamed.values()
    )
    result['incomplete'] = sum(
        case['status'] == 'INCOMPLETE' for case in renamed.values()
    )
    if (
        not physical_harness_complete
        or result['incomplete']
        or len(renamed) != 10
    ):
        result['status'] = 'INCOMPLETE'
    elif result['counterexamples']:
        result['status'] = 'FAIL_NEW_COUNTEREXAMPLE'
    elif result['controls'] == 10:
        result['status'] = 'PASS_BOUNDED_AUDIT'
    else:
        result['status'] = 'INCOMPLETE'
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
    return result


if __name__ == '__main__':
    try:
        outcome = run()
    except Exception as exc:
        outcome = {
            'status': 'INCOMPLETE',
            'error': str(exc),
            'traceback': traceback.format_exc(),
            'production_go': False,
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(outcome, indent=2, default=str) + '\n')
    print(json.dumps({k: v for k, v in outcome.items() if k != 'cases'}, default=str))
    raise SystemExit(
        0 if outcome['status'] == 'PASS_BOUNDED_AUDIT'
        else 1 if outcome['status'] == 'FAIL_NEW_COUNTEREXAMPLE'
        else 2
    )
