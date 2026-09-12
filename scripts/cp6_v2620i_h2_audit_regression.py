#!/usr/bin/env python3
"""Native PostgreSQL proof for CP6 H2-01 and final I payment lineage."""
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
    'supabase/migrations/20260910100051_erp_v2_6_20i_cp6_h2_audit_closure.sql'
)
SUCCESSOR_J = Path(
    'supabase/migrations/20260910170556_erp_v2_6_20j_cp6_payment_fact_closure.sql'
)
REPORT = Path(
    os.environ.get(
        'CP6_V2620I_H2_REPORT', 'cp6-proof/CP6_V2620I_H2_AUDIT_REGRESSION.json'
    )
)
PGURL = os.environ.get('PGURL', '')
HEAD = os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND')
CHECK = 'V2620I_SALES_PAYMENT_JOURNAL_LINEAGE_MISMATCH'


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
          from erp.cp6_v2620i_rollback_capsule"""
    )
    row = cur.fetchone()
    if (
        row is None
        or row[0] != 'erp.run_v268_financial_report_checks()'
        or row[1] != '3afc0bef1136bafb14d4fdde69fa0cdf79fff0883c35c65607bdfa624d8cf65f'
        or row[2] != 'c25defe6a1403a7199e71f92fd3799f941b7748f6228671e78586ba1ede5f8e1'
        or row[4] != 'postgres'
        or row[5] != [
            'authenticated=X/postgres',
            'postgres=X/postgres',
            'service_role=X/postgres',
        ]
    ):
        raise AssertionError(f'I predecessor capsule mismatch: {row}')
    cur.execute(
        """select object_regidentity,definition_sha256,installed_definition_sha256,
          encode(extensions.digest(convert_to(pg_get_functiondef(
            to_regprocedure(object_regidentity)),'UTF8'),'sha256'),'hex') actual,
          owner_snapshot,acl_snapshot
          from erp.cp6_v2620j_rollback_capsule order by object_regidentity"""
    )
    j_rows = m_runtime.extend_rows(m_successor, k_runtime.extend_rows(k_successor, cur.fetchall()))
    if len(j_rows) != 3 or any(item[2] != item[3] for item in j_rows):
        raise AssertionError(f'J successor capsule/function mismatch: {j_rows}')
    j_report = next(
        (item for item in j_rows if item[0] == 'erp.run_v268_financial_report_checks()'),
        None,
    )
    if j_report is None or row[3] != j_report[2]:
        raise AssertionError(f'I-to-J report lineage mismatch: I={row}, J={j_report}')
    source = MIGRATION.read_bytes()
    file_sha = hashlib.sha256(source).hexdigest()
    ledger_sha = base.one(
        cur,
        """select encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),
          'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations
          where name='erp_v2_6_20i_cp6_h2_audit_closure'""",
    )
    accepted = (file_sha, hashlib.sha256(source[:-1]).hexdigest())
    if ledger_sha not in accepted:
        raise AssertionError(f'I source/platform drift: {ledger_sha} not in {accepted}')
    j_source = SUCCESSOR_J.read_bytes()
    j_file_sha = hashlib.sha256(j_source).hexdigest()
    j_ledger_sha = base.one(
        cur,
        """select encode(extensions.digest(convert_to(array_to_string(statements,E'\n'),
          'UTF8'),'sha256'),'hex') from supabase_migrations.schema_migrations
          where name='erp_v2_6_20j_cp6_payment_fact_closure'""",
    )
    if j_ledger_sha not in (j_file_sha, hashlib.sha256(j_source[:-1]).hexdigest()):
        raise AssertionError(f'J source/platform drift: {j_ledger_sha} != {j_file_sha}')
    return {
        'engine': base.one(cur, 'select version()'),
        'versions': versions + (['v2.6.20k'] if k_successor else []) + (['v2.6.20l'] if l_successor else []) + (['v2.6.20m'] if m_successor else []) + (['v2.6.20n'] if any('pre_n_installed_sha256' in x for x in m_successor.values()) else []) + (['v2.6.20o'] if any('pre_o_installed_sha256' in x for x in m_successor.values()) else []) + (['v2.6.20p'] if any('pre_p_installed_sha256' in x for x in m_successor.values()) else []),
        'capsule': {
            'identity': row[0], 'predecessor_sha256': row[1],
            'installed_sha256': row[2], 'actual_sha256': row[3],
            'owner': row[4], 'acl': row[5], 'effective_generation': 'M' if m_successor else 'K' if k_successor else 'J',
        },
        'successor_j_capsule': [
            {
                'identity': item[0], 'predecessor_sha256': item[1],
                'installed_sha256': item[2], 'actual_sha256': item[3],
                'j_installed_sha256': k_successor[item[0]]['predecessor_sha256'] if k_successor else item[2],
                'expected_generation': 'K' if k_successor else 'J',
                'owner': item[4], 'acl': item[5],
            }
            for item in j_rows
        ],
        'migration_bytes': len(source),
        'migration_sha256': file_sha,
        'platform_sha256': ledger_sha,
        'successor_j_migration_bytes': len(j_source),
        'successor_j_migration_sha256': j_file_sha,
        'successor_j_platform_sha256': j_ledger_sha,
    }


def case_same_customer_cross_invoice(cur: psycopg.Cursor) -> dict[str, Any]:
    first = h.opening_sale(cur, 'I-SAME-CUSTOMER-A')
    second = h.opening_sale(cur, 'I-SAME-CUSTOMER-B', first['customer'])
    first_payment = h.post_payment(cur, first['sale'], Decimal('50'))
    second_payment = h.post_payment(cur, second['sale'], Decimal('50'))
    assert_clean(cur, 'same-customer baseline')

    cur.execute('savepoint i_same_customer_fault')
    cur.execute("set local session_replication_role='replica'")
    cur.execute(
        """update erp.sales_payments set amount=case id
             when %s then 49.99 when %s then 50.01 else amount end
           where id in(%s,%s)""",
        (first_payment, second_payment, first_payment, second_payment),
    )
    i_issues = issue_count(cur)
    h_customer = h.issue_count(cur, 'V2620H_CUSTOMER_AR_BY_CUSTOMER_MISMATCH')
    global_ar = h.issue_count(cur, 'V268_AR_GL_SUBLEDGER_MISMATCH')
    report = confidence(cur)
    if (i_issues, h_customer, global_ar, report) != (2, 0, 0, 'BLOCKED'):
        raise AssertionError(
            'Same-customer cross-invoice wash escaped exact lineage: '
            f'I={i_issues}, H-customer={h_customer}, global={global_ar}, report={report}'
        )
    cur.execute('rollback to savepoint i_same_customer_fault')
    cur.execute('release savepoint i_same_customer_fault')
    assert_clean(cur, 'same-customer restored baseline')
    return {
        'status': 'PASS',
        'fault_payment_amounts': ['49.99', '50.01'],
        'aggregate_customer_amount': '100.00',
        'i_lineage_issue_count': i_issues,
        'h_customer_issue_count': h_customer,
        'global_ar_issue_count': global_ar,
        'fault_report_status': report,
        'restored_report_status': 'READY',
    }


def case_valid_payment_inverse(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = h.opening_sale(cur, 'I-VALID-INVERSE')
    payment = h.post_payment(cur, fixture['sale'], Decimal('100'))
    assert_clean(cur, 'valid posted payment')
    base.one(cur, "select erp.reverse_sales_payment(%s,'I exact valid inverse')", (payment,))
    assert_clean(cur, 'valid reversed payment')
    states = base.row(
        cur,
        """select p.status,s.status,o.status,r.status
           from erp.sales_payments p join erp.sales_headers s on s.id=p.sale_id
           join erp.journal_entries o on o.source_type='SALES_PAYMENT' and o.source_id=p.id
           join erp.journal_entries r on r.source_type='JOURNAL_REVERSAL'
             and r.source_id=o.id and r.reversal_of_id=o.id
           where p.id=%s""",
        (payment,),
    )
    if states != ('REVERSED', 'POSTED', 'REVERSED', 'POSTED'):
        raise AssertionError(f'Valid payment inverse lifecycle mismatch: {states}')
    return {'status': 'PASS', 'states': states, 'issue_count': 0, 'report': 'READY'}


def fault_probe(
    cur: psycopg.Cursor, name: str, mutation: Callable[[], Any]
) -> dict[str, Any]:
    cur.execute('savepoint i_lineage_fault')
    cur.execute("set local session_replication_role='replica'")
    mutation()
    issues = issue_count(cur)
    report = confidence(cur)
    if issues < 1 or report != 'BLOCKED':
        raise AssertionError(f'{name} escaped: issues={issues}, report={report}')
    cur.execute('rollback to savepoint i_lineage_fault')
    cur.execute('release savepoint i_lineage_fault')
    assert_clean(cur, f'{name} restored baseline')
    return {'case': name, 'status': 'PASS', 'issue_count': issues, 'report': report}


def case_lineage_fault_matrix(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = h.opening_sale(cur, 'I-LINEAGE-MATRIX')
    payment = h.post_payment(cur, fixture['sale'], Decimal('50'))
    other_customer = base.create_customer(cur, 'I-LINEAGE-OTHER')
    original = str(base.one(
        cur,
        "select id from erp.journal_entries where source_type='SALES_PAYMENT' and source_id=%s",
        (payment,),
    ))
    probes = [
        fault_probe(
            cur,
            'balanced_original_line_amount_drift',
            lambda: cur.execute(
                """update erp.journal_lines
                   set debit=case when debit>0 then debit-.01 else debit end,
                       credit=case when credit>0 then credit-.01 else credit end
                   where journal_entry_id=%s""",
                (original,),
            ),
        ),
        fault_probe(
            cur,
            'payment_journal_customer_drift',
            lambda: cur.execute(
                'update erp.journal_lines set customer_id=%s where journal_entry_id=%s',
                (other_customer, original),
            ),
        ),
        fault_probe(
            cur,
            'orphan_sales_payment_journal',
            lambda: cur.execute(
                "update erp.journal_entries set source_id=%s where id=%s",
                (str(uuid.uuid4()), original),
            ),
        ),
    ]

    reversed_fixture = h.opening_sale(cur, 'I-INVERSE-LINK')
    reversed_payment = h.post_payment(cur, reversed_fixture['sale'], Decimal('100'))
    base.one(
        cur,
        "select erp.reverse_sales_payment(%s,'I inverse-link fault fixture')",
        (reversed_payment,),
    )
    reversal = str(base.one(
        cur,
        """select r.id from erp.journal_entries o join erp.journal_entries r
             on r.reversal_of_id=o.id and r.source_id=o.id
           where o.source_type='SALES_PAYMENT' and o.source_id=%s""",
        (reversed_payment,),
    ))
    assert_clean(cur, 'inverse-link baseline')
    probes.append(fault_probe(
        cur,
        'inverse_link_drift',
        lambda: cur.execute(
            'update erp.journal_entries set reversal_of_id=null where id=%s',
            (reversal,),
        ),
    ))
    return {'status': 'PASS', 'probes': probes, 'restored_report_status': 'READY'}


def case_authenticated_direct_write_denied(cur: psycopg.Cursor) -> dict[str, Any]:
    fixture = h.opening_sale(cur, 'I-AUTH-DENY')
    payment = h.post_payment(cur, fixture['sale'], Decimal('50'))
    cur.execute('savepoint i_auth_denied')
    rejection = None
    try:
        cur.execute('set local role authenticated')
        cur.execute('update erp.sales_payments set amount=49.99 where id=%s', (payment,))
    except psycopg.Error as exc:
        rejection = str(exc).splitlines()[0]
    finally:
        cur.execute('rollback to savepoint i_auth_denied')
        cur.execute('release savepoint i_auth_denied')
    if rejection is None:
        raise AssertionError('Authenticated direct payment mutation was accepted')
    amount = Decimal(str(base.one(
        cur, 'select amount from erp.sales_payments where id=%s', (payment,)
    )))
    if amount != Decimal('50'):
        raise AssertionError(f'Authenticated denial left payment drift: {amount}')
    assert_clean(cur, 'authenticated denial restored baseline')
    return {'status': 'PASS', 'rejection': rejection, 'amount': str(amount), 'report': 'READY'}


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
        cur.execute("select set_config('app.change_reason','I H2 audit regression',true)")
        base.load_fixture_foundation(cur)
        cases: tuple[tuple[str, Callable[[psycopg.Cursor], dict[str, Any]]], ...] = (
            ('H2_01_SAME_CUSTOMER_CROSS_INVOICE_WASH', case_same_customer_cross_invoice),
            ('VALID_PAYMENT_AND_EXACT_INVERSE', case_valid_payment_inverse),
            ('PAYMENT_LINEAGE_FAULT_MATRIX', case_lineage_fault_matrix),
            ('AUTHENTICATED_DIRECT_PAYMENT_WRITE_DENIED', case_authenticated_direct_write_denied),
        )
        for name, case in cases:
            cur.execute('savepoint i_case')
            try:
                result['cases'][name] = case(cur)
            except Exception as exc:
                result['cases'][name] = {
                    'status': 'FAIL', 'error': str(exc),
                    'sqlstate': getattr(exc, 'sqlstate', None),
                }
            finally:
                cur.execute('rollback to savepoint i_case')
                cur.execute('release savepoint i_case')
        if base.one(cur, 'select count(*) from erp.cp6_laundry_qc_execution_context') != 0:
            raise AssertionError('I regression left execution-context residue')
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
