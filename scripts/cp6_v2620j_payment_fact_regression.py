#!/usr/bin/env python3
"""Native PostgreSQL proof for CP6 I-01/I-02 and v2.6.20j payment facts."""
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
import cp6_v2620h_adversarial_regression as h


MIGRATION = Path(
    'supabase/migrations/20260910170556_erp_v2_6_20j_cp6_payment_fact_closure.sql'
)
REPORT = Path(
    os.environ.get(
        'CP6_V2620J_PAYMENT_FACT_REPORT',
        'cp6-proof/CP6_V2620J_PAYMENT_FACT_REGRESSION.json',
    )
)
PGURL = os.environ.get('PGURL', '')
HEAD = os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND')
CHECK = 'V2620J_SALES_PAYMENT_IMMUTABLE_FACT_MISMATCH'


def issue_count(cur: psycopg.Cursor) -> int:
    return int(base.one(
        cur,
        'select issue_count from erp.run_v268_financial_report_checks() where check_name=%s',
        (CHECK,),
    ))


def confidence(cur: psycopg.Cursor) -> str:
    return h.owner(cur)['data_confidence']['status']


def assert_clean(cur: psycopg.Cursor, label: str) -> None:
    actual = (issue_count(cur), confidence(cur))
    if actual != (0, 'READY'):
        raise AssertionError(f'{label} is not clean: {actual}')


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
    expected_versions = [
        'v2.6.20e', 'v2.6.20f', 'v2.6.20g',
        'v2.6.20h', 'v2.6.20i', 'v2.6.20j',
    ]
    if versions != expected_versions:
        raise AssertionError(f'Final E+F+G+H+I+J runtime not present: {versions}')
    cur.execute(
        """select object_regidentity,definition_sha256,installed_definition_sha256,
          encode(extensions.digest(convert_to(pg_get_functiondef(
            to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex') actual,
          owner_snapshot,acl_snapshot
          from erp.cp6_v2620j_rollback_capsule order by object_regidentity"""
    )
    rows = cur.fetchall()
    expected = {
        'erp.post_sales_payment(uuid)': (
            '010de4bae594258ba73348463ba90305a01485ed30b9c11918583be198c1f6df',
            '5634d6fa8fa613e455b9de57b2bd186ac6424815ea2a0aa33866c7c235918e5a',
            ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres'],
        ),
        'erp.reverse_sales_payment(uuid,text)': (
            '09c33e1cfbc673f9118878bd6da55e0df9c433252f0ecb099ef547895cab3ef6',
            '00d2c2e0dea82508840c06a9aa7ddade503df9a552a29b664beeb32cd081e5b6',
            ['authenticated=X/postgres', 'postgres=X/postgres'],
        ),
        'erp.run_v268_financial_report_checks()': (
            'c25defe6a1403a7199e71f92fd3799f941b7748f6228671e78586ba1ede5f8e1',
            '3ab1c4e42616eadac12dd0d37811703fdd0436690a57ebe962c651af56e3588f',
            ['authenticated=X/postgres', 'postgres=X/postgres', 'service_role=X/postgres'],
        ),
    }
    if len(rows) != len(expected):
        raise AssertionError(f'J capsule cardinality mismatch: {rows}')
    for row in rows:
        wanted = expected.get(row[0])
        if wanted is None or row[1] != wanted[0] or row[2] != wanted[1]:
            raise AssertionError(f'J capsule hash mismatch: {row}')
        if m_runtime.effective_hash(m_successor, row[0], k_runtime.effective_hash(k_successor, row[0], row[2])) != row[3] or row[4] != 'postgres' or row[5] != wanted[2]:
            raise AssertionError(f'J installed function owner/ACL mismatch: {row}')
    source = MIGRATION.read_bytes()
    file_sha = hashlib.sha256(source).hexdigest()
    ledger_sha = base.one(
        cur,
        """select encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),
          'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations
          where name='erp_v2_6_20j_cp6_payment_fact_closure'""",
    )
    accepted = (file_sha, hashlib.sha256(source[:-1]).hexdigest())
    if ledger_sha not in accepted:
        raise AssertionError(f'J source/platform drift: {ledger_sha} not in {accepted}')
    rels = base.one(
        cur,
        """select jsonb_build_object(
          'posting_facts',to_regclass('erp.sales_payment_posting_facts') is not null,
          'reversal_facts',to_regclass('erp.sales_payment_reversal_facts') is not null,
          'link_column',exists(select 1 from information_schema.columns
            where table_schema='erp' and table_name='sales_payments'
              and column_name='replaces_payment_id'),
          'strict_trigger',exists(select 1 from pg_trigger
            where tgrelid='erp.sales_payments'::regclass
              and tgname='trg_cp6_v2620j_sales_payment_identity' and not tgisinternal)
        )""",
    )
    if not all(rels.values()):
        raise AssertionError(f'J immutable fact relations incomplete: {rels}')
    return {
        'engine': base.one(cur, 'select version()'),
        'versions': versions + (['v2.6.20k'] if k_successor else []) + (['v2.6.20l'] if l_successor else []) + (['v2.6.20m'] if m_successor else []),
        'capsule': [
            {
                'identity': row[0], 'predecessor_sha256': row[1],
                'installed_sha256': m_runtime.effective_hash(m_successor, row[0], k_runtime.effective_hash(k_successor, row[0], row[2])),
                'j_installed_sha256': row[2], 'actual_sha256': row[3],
                'owner': row[4], 'acl': row[5],
            }
            for row in rows
        ],
        'relations': rels,
        'migration_bytes': len(source),
        'migration_sha256': file_sha,
        'platform_sha256': ledger_sha,
    }


def expected_rejection(
    cur: psycopg.Cursor,
    label: str,
    operation: Callable[[], Any],
    *,
    sqlstates: tuple[str, ...],
    message: str,
) -> dict[str, Any]:
    cur.execute('savepoint j_expected_rejection')
    try:
        operation()
    except psycopg.Error as exc:
        cur.execute('rollback to savepoint j_expected_rejection')
        cur.execute('release savepoint j_expected_rejection')
        if exc.sqlstate not in sqlstates or message not in str(exc):
            raise AssertionError(
                f'{label} wrong rejection: sqlstate={exc.sqlstate}, error={exc}'
            ) from exc
        return {
            'case': label, 'status': 'PASS', 'sqlstate': exc.sqlstate,
            'expected_sqlstates': sqlstates, 'expected_message': message,
            'rejected': True,
        }
    cur.execute('rollback to savepoint j_expected_rejection')
    cur.execute('release savepoint j_expected_rejection')
    raise AssertionError(f'{label} unexpectedly succeeded')


def replica_fault(
    cur: psycopg.Cursor, label: str, operation: Callable[[], Any]
) -> dict[str, Any]:
    cur.execute('savepoint j_replica_fault')
    cur.execute("set local session_replication_role='replica'")
    operation()
    issues = issue_count(cur)
    report = confidence(cur)
    if issues < 1 or report != 'BLOCKED':
        raise AssertionError(f'{label} escaped J oracle: issues={issues}, report={report}')
    cur.execute('rollback to savepoint j_replica_fault')
    cur.execute('release savepoint j_replica_fault')
    assert_clean(cur, f'{label} restored baseline')
    return {'case': label, 'status': 'PASS', 'issue_count': issues, 'report': report}


def case_invoice_identity(cur: psycopg.Cursor) -> dict[str, Any]:
    customer = base.create_customer(cur, 'J-I01-SAME-CUSTOMER')
    first = h.opening_sale(cur, 'J-I01-A', customer)
    second = h.opening_sale(cur, 'J-I01-B', customer)
    first_payment = h.post_payment(cur, first['sale'], Decimal('40'))
    second_payment = h.post_payment(cur, second['sale'], Decimal('60'))
    assert_clean(cur, 'J I-01 baseline')
    params = (
        first_payment, second['sale'], second_payment, first['sale'],
        first_payment, second_payment,
    )

    def swap() -> None:
        cur.execute(
            """update erp.sales_payments set sale_id=case id
                 when %s then %s when %s then %s else sale_id end
               where id in(%s,%s)""",
            params,
        )

    direct = expected_rejection(
        cur,
        'privileged_direct_invoice_swap',
        swap,
        sqlstates=('42501',),
        message='POSTED_PAYMENT_IDENTITY_IMMUTABLE',
    )
    bypass = replica_fault(cur, 'replica_invoice_swap', swap)
    return {
        'status': 'PASS', 'direct_guard': direct, 'detector_after_trigger_bypass': bypass,
        'restored_report_status': 'READY',
    }


def case_inverse_dates(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = h.opening_sale(cur, 'J-I02')
    payment = h.post_payment(cur, fixture['sale'], Decimal('100'))
    base.one(cur, "select erp.reverse_sales_payment(%s,'J I-02 valid inverse')", (payment,))
    original = str(base.one(
        cur,
        "select id from erp.journal_entries where source_type='SALES_PAYMENT' and source_id=%s",
        (payment,),
    ))
    inverse = str(base.one(
        cur,
        "select id from erp.journal_entries where source_type='JOURNAL_REVERSAL' and reversal_of_id=%s",
        (original,),
    ))
    assert_clean(cur, 'J I-02 valid inverse baseline')
    probes = []
    for label, delta in (('inverse_one_day_before_original', -1), ('inverse_one_day_after_fact', 1)):
        probes.append(replica_fault(
            cur,
            label,
            lambda delta=delta: cur.execute(
                'update erp.journal_entries set economic_date=economic_date+(%s) where id=%s',
                (delta, inverse),
            ),
        ))
    return {'status': 'PASS', 'probes': probes, 'restored_report_status': 'READY'}


def case_linked_replacement(cur: psycopg.Cursor) -> dict[str, Any]:
    customer = base.create_customer(cur, 'J-LINKED-REPLACEMENT')
    source = h.opening_sale(cur, 'J-LINK-SOURCE', customer)
    destination = h.opening_sale(cur, 'J-LINK-DESTINATION', customer)
    foreign = h.opening_sale(cur, 'J-LINK-OTHER')

    def inventory_book() -> tuple:
        return base.row(cur, """select
          (select count(*) from erp.fg_stock_movements),
          (select coalesce(sum(cached_qty_pcs),0) from erp.fg_lots),
          coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('FG_INVENTORY')),0),
          coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('COGS')),0)
          from erp.journal_lines l join erp.journal_entries e on e.id=l.journal_entry_id
          where e.status in('POSTED','REVERSED')""")

    inventory_before = inventory_book()
    ar_before = h.ar_for_customer(cur, customer)
    payment = h.post_payment(cur, source['sale'], Decimal('40'))

    def cash_balance() -> Decimal:
        return Decimal(str(base.one(cur, """select coalesce(sum(l.debit-l.credit),0)
          from erp.journal_lines l join erp.journal_entries e on e.id=l.journal_entry_id
          where e.status in('POSTED','REVERSED') and l.account_id=(
            select a.coa_account_id from erp.cash_accounts a
            join erp.sales_payments p on p.cash_account_id=a.id where p.id=%s)""", (payment,))))

    cash_after_payment = cash_balance()

    def attempt_replacement(sale: str, amount_delta: Decimal = Decimal(0), days: int = 0) -> None:
        attempt = str(uuid.uuid4())
        cur.execute("""insert into erp.sales_payments(
          id,sale_id,payment_number,payment_date,amount,cash_account_id,
          status,created_by,replaces_payment_id
        ) select %s,%s,%s,payment_date+(%s)*interval '1 day',amount+(%s),cash_account_id,
          'DRAFT',created_by,id from erp.sales_payments where id=%s""",
          (attempt, sale, f'J-INVALID-{uuid.uuid4()}', days, amount_delta, payment))
        base.one(cur, 'select erp.post_sales_payment(%s)', (attempt,))

    invalid_replacements = [expected_rejection(
        cur, 'replacement_before_original_reversal',
        lambda: attempt_replacement(destination['sale']),
        sqlstates=('P0001',), message='Replacement requires one fully reversed posted payment',
    )]
    base.one(cur, "select erp.reverse_sales_payment(%s,'J allocation correction')", (payment,))
    for label, sale, delta, days in (
        ('replacement_wrong_customer', foreign['sale'], Decimal(0), 0),
        ('replacement_same_invoice', source['sale'], Decimal(0), 0),
        ('replacement_amount_drift', destination['sale'], Decimal('.01'), 0),
        ('replacement_original_clock_drift', destination['sale'], Decimal(0), -1),
    ):
        invalid_replacements.append(expected_rejection(
            cur, label,
            lambda sale=sale, delta=delta, days=days: attempt_replacement(sale, delta, days),
            sqlstates=('P0001',), message='Allocation replacement must preserve customer',
        ))
    replacement = str(uuid.uuid4())
    cur.execute(
        """insert into erp.sales_payments(
          id,sale_id,payment_number,payment_date,amount,cash_account_id,
          payment_method,reference_number,notes,status,created_by,replaces_payment_id
        ) select %s,%s,%s,payment_date,amount,cash_account_id,
          payment_method,reference_number,'J linked replacement','DRAFT',created_by,id
          from erp.sales_payments where id=%s""",
        (replacement, destination['sale'], f'J-REPLACE-{uuid.uuid4()}', payment),
    )
    base.one(cur, 'select erp.post_sales_payment(%s)', (replacement,))
    assert_clean(cur, 'J linked replacement')
    states = base.row(
        cur,
        """select old.status,new.status,new.replaces_payment_id::text,
          f.replaces_payment_id::text,f.predecessor_reversal_journal_id::text,
          rf.reversal_journal_entry_id::text
          from erp.sales_payments old
          join erp.sales_payments new on new.id=%s
          join erp.sales_payment_posting_facts f on f.payment_id=new.id
          join erp.sales_payment_reversal_facts rf on rf.payment_id=old.id
          where old.id=%s""",
        (replacement, payment),
    )
    if (
        states[:4] != ('REVERSED', 'POSTED', payment, payment)
        or states[4] is None
        or states[4] != states[5]
    ):
        raise AssertionError(f'Linked replacement lineage mismatch: {states}')

    duplicate = str(uuid.uuid4())
    duplicate_number = f'J-DUP-{uuid.uuid4()}'
    duplicate_rejection = expected_rejection(
        cur, 'second_replacement_for_same_payment',
        lambda: cur.execute(
            """insert into erp.sales_payments(
              id,sale_id,payment_number,payment_date,amount,cash_account_id,
              status,created_by,replaces_payment_id
            ) select %s,%s,%s,payment_date,amount,cash_account_id,
              'DRAFT',created_by,id
              from erp.sales_payments where id=%s""",
            (duplicate, destination['sale'], duplicate_number, payment),
        ),
        sqlstates=('23505',),
        message='uq_sales_payments_one_replacement',
    )
    # Lost-response replay must not undo the replacement or issue another cash inverse.
    before_replay = base.row(cur, """select
      (select count(*) from erp.journal_entries),
      (select count(*) from erp.sales_payment_posting_facts),
      (select count(*) from erp.sales_payment_reversal_facts)""")
    base.one(cur, "select erp.reverse_sales_payment(%s,'J duplicate reversal delivery')", (payment,))
    after_replay = base.row(cur, """select
      (select count(*) from erp.journal_entries),
      (select count(*) from erp.sales_payment_posting_facts),
      (select count(*) from erp.sales_payment_reversal_facts)""")
    invoice_allocations = base.row(cur, """select
      coalesce(sum(amount) filter(where sale_id=%s),0),
      coalesce(sum(amount) filter(where sale_id=%s),0)
      from erp.sales_payments where status='POSTED'""", (source['sale'], destination['sale']))
    if before_replay != after_replay or invoice_allocations != (Decimal(0), Decimal(40)):
        raise AssertionError('Replacement/reversal replay changed invoice lineage or duplicated facts')
    if inventory_book() != inventory_before:
        raise AssertionError('Payment allocation correction changed stock, FG valuation or COGS')
    if cash_balance() != cash_after_payment or h.ar_for_customer(cur, customer) != ar_before - Decimal(40):
        raise AssertionError('Payment allocation correction changed net cash or customer receivable')
    assert_clean(cur, 'J linked replacement and duplicate reversal')
    return {
        'status': 'PASS', 'states': states,
        'duplicate_rejection': duplicate_rejection, 'report': 'READY',
        'invalid_replacements': invalid_replacements,
        'duplicate_reversal_no_new_facts': True,
        'invoice_allocations': [str(value) for value in invoice_allocations],
        'net_cash_and_receivable_conserved': True,
        'stock_fg_value_cogs_unchanged': True,
    }


def case_fact_and_snapshot_guards(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = h.opening_sale(cur, 'J-FACT-GUARDS')
    payment = h.post_payment(cur, fixture['sale'], Decimal('50'))
    assert_clean(cur, 'J fact guard baseline')
    rejections = [
        expected_rejection(
            cur, 'posted_payment_number_direct_update',
            lambda: cur.execute(
                "update erp.sales_payments set payment_number=payment_number||'-X' where id=%s",
                (payment,),
            ),
            sqlstates=('42501',),
            message='POSTED_PAYMENT_IDENTITY_IMMUTABLE',
        ),
        expected_rejection(
            cur, 'posting_fact_direct_update',
            lambda: cur.execute(
                'update erp.sales_payment_posting_facts set sale_id=sale_id where payment_id=%s',
                (payment,),
            ),
            sqlstates=('42501',),
            message='POSTED_PAYMENT_FACT_APPEND_ONLY',
        ),
        expected_rejection(
            cur, 'posting_fact_direct_delete',
            lambda: cur.execute(
                'delete from erp.sales_payment_posting_facts where payment_id=%s',
                (payment,),
            ),
            sqlstates=('42501',),
            message='POSTED_PAYMENT_FACT_APPEND_ONLY',
        ),
    ]
    detector = replica_fault(
        cur,
        'payment_snapshot_after_trigger_bypass',
        lambda: cur.execute(
            "update erp.sales_payments set reference_number='FAULT' where id=%s",
            (payment,),
        ),
    )
    return {
        'status': 'PASS', 'rejections': rejections,
        'detector_after_trigger_bypass': detector, 'report': 'READY',
    }


def case_future_payment(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = h.opening_sale(cur, 'J-FUTURE-PAYMENT')
    payment = str(uuid.uuid4())
    cur.execute(
        """insert into erp.sales_payments(
          id,sale_id,payment_number,payment_date,amount,cash_account_id,status,created_by
        ) values(%s,%s,%s,clock_timestamp()+interval '1 day',50,
          (select id from erp.cash_accounts where is_active order by cash_account_code limit 1),
          'DRAFT',%s)""",
        (payment, fixture['sale'], f'J-FUTURE-{uuid.uuid4()}', base.OPERATOR_APP),
    )
    rejection = expected_rejection(
        cur, 'future_payment_business_date',
        lambda: base.one(cur, 'select erp.post_sales_payment(%s)', (payment,)),
        sqlstates=('P0001',),
        message='Customer payment business date cannot be in the future',
    )
    residue = base.row(
        cur,
        """select status,
          (select count(*) from erp.sales_payment_posting_facts where payment_id=%s),
          (select count(*) from erp.journal_entries
           where source_type='SALES_PAYMENT' and source_id=%s)
          from erp.sales_payments where id=%s""",
        (payment, payment, payment),
    )
    if residue != ('DRAFT', 0, 0):
        raise AssertionError(f'Future payment rejection left residue: {residue}')
    assert_clean(cur, 'J future payment rejection')
    return {'status': 'PASS', 'rejection': rejection, 'residue': residue, 'report': 'READY'}


def run() -> dict[str, Any]:
    result: dict[str, Any] = {
        'head': HEAD,
        'classification': 'DISPOSABLE_NATIVE_POSTGRESQL_AFTER_E_F_G_H_I_J',
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
        cur.execute("select set_config('app.change_reason','J payment fact regression',true)")
        base.load_fixture_foundation(cur)
        cases: tuple[tuple[str, Callable[[psycopg.Cursor], dict[str, Any]]], ...] = (
            ('I01_INVOICE_IDENTITY_GUARD_AND_DETECTOR', case_invoice_identity),
            ('I02_AUTHORITATIVE_INVERSE_DATES', case_inverse_dates),
            ('LINKED_ALLOCATION_REPLACEMENT', case_linked_replacement),
            ('APPEND_ONLY_FACT_AND_FULL_SNAPSHOT_GUARDS', case_fact_and_snapshot_guards),
            ('FUTURE_PAYMENT_FAIL_CLOSED', case_future_payment),
        )
        for name, case in cases:
            cur.execute('savepoint j_case')
            try:
                result['cases'][name] = case(cur)
            except Exception as exc:
                result['cases'][name] = {
                    'status': 'FAIL', 'error': str(exc),
                    'sqlstate': getattr(exc, 'sqlstate', None),
                }
            finally:
                cur.execute('rollback to savepoint j_case')
                cur.execute('release savepoint j_case')
        if base.one(cur, 'select count(*) from erp.cp6_laundry_qc_execution_context') != 0:
            raise AssertionError('J regression left execution-context residue')
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
            'head': HEAD, 'status': 'FAIL', 'error': str(exc), 'production_go': False,
        }
    REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps(result, sort_keys=True, default=str))
    if result['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
