"""Exact retained replay/inverse and corrupt-date oracles on completed fixture."""
from cp6_v2620y_cash_business_date_regression import *
import payment_oracle

def setup(cur, cash, kind):
    if kind == 'OPENING_SUBLEDGER_SETTLEMENT':
        evidence = audit.settlement_date(cur, cash, 'CUSTOMER_RECEIVABLE', 'America/New_York')
        ident = evidence['settlement_id']
    else:
        evidence = payment_oracle.payment_date(cur, cash, kind, 'America/New_York')
        ident = evidence['payment_id']
    if evidence['status'] != 'CONTROL_PASS':
        raise AssertionError('Y_EXTENSION_REQUIRES_CORRECT_CORE')
    return ident, evidence


def lifecycle(cur, cash, kind):
    ident, evidence = setup(cur, cash, kind)
    source = evidence['journals'][0][0]
    before = audit.boundary(cur)
    audit.owner(cur)
    replay = refuse(cur, 'select erp.' + FUNCTIONS[kind][0] + '(%s)', (ident,), 'DRAFT')
    audit.admin(cur)
    if audit.boundary(cur) != before:
        raise AssertionError('Y_POST_REPLAY_CHANGED_BOUNDARY')
    # JSON serializes timestamptz in the observer's timezone. Pin observation
    # to UTC while leaving the tested reversal call in Honolulu below.
    audit.zone(cur, 'UTC')
    fact_before = audit.one(cur, 'select to_jsonb(f) from erp.sales_payment_posting_facts f where payment_id=%s', (ident,)) if kind == 'SALES_PAYMENT' else None
    journal_before = audit.one(cur, 'select to_jsonb(j) from erp.journal_entries j where id=%s', (source,))
    audit.owner(cur)
    audit.zone(cur, 'Pacific/Honolulu')
    cur.execute('select erp.' + FUNCTIONS[kind][1] + "(%s,'Y linked inverse date proof')", (ident,))
    after_reports = audit.scrap.reports(cur, tuple(evidence['daily_evidence']))
    for day, original in evidence['daily_evidence'].items():
        if after_reports[day]['data_confidence']['status'] != 'READY' or after_reports[day]['financial_position'] != original['after']['financial_position']:
            raise AssertionError('Y_REVERSAL_REWROTE_EARLIER_AS_OF')
    audit.admin(cur)
    audit.zone(cur, 'UTC')
    if kind == 'SALES_PAYMENT' and audit.one(cur, 'select to_jsonb(f) from erp.sales_payment_posting_facts f where payment_id=%s', (ident,)) != fact_before:
        raise AssertionError('Y_REVERSAL_MUTATED_POSTING_FACT')
    journal_after = audit.one(cur, 'select to_jsonb(j) from erp.journal_entries j where id=%s', (source,))
    for key in ('economic_date', 'transaction_date', 'posting_at', 'source_type', 'source_id'):
        if journal_after[key] != journal_before[key]:
            raise AssertionError('Y_REVERSAL_MUTATED_SOURCE_CLOCK')
    cur.execute("select id::text,economic_date,transaction_date,posting_at from erp.journal_entries where reversal_of_id=%s and status='POSTED'", (source,))
    reversals = cur.fetchall()
    expected_today = audit.one(cur, 'select current_timestamp').astimezone(ZoneInfo('Asia/Jakarta')).date()
    if len(reversals) != 1 or reversals[0][1] != expected_today or reversals[0][2] != expected_today:
        raise AssertionError('Y_REVERSAL_DATE_OR_CARDINALITY')
    cash_account = audit.one(cur, 'select coa_account_id from erp.cash_accounts where id=%s', (cash,))
    cash_net = audit.one(cur, 'select sum(l.debit-l.credit) from erp.journal_lines l where l.journal_entry_id in(%s,%s) and l.account_id=%s', (source, reversals[0][0], cash_account))
    if cash_net != Decimal(0):
        raise AssertionError('Y_LINKED_INVERSE_CASH_NOT_ZERO')
    return dict(status='CONTROL_PASS', classification='REAL_OWNER_REPLAY_REFUSAL_AND_LINKED_INVERSE',
                kind=kind, replay_refusal=replay, replay_boundary_exact=True, original_clock_preserved=True,
                immutable_sales_fact_preserved=kind == 'SALES_PAYMENT', inverse=reversals,
                expected_reversal_date=expected_today, cash_net=str(cash_net), earlier_as_of_preserved=True)


def detector_fault(cur, cash, kind):
    ident, evidence = setup(cur, cash, kind)
    source = evidence['journals'][0][0]
    audit.admin(cur)
    # Explicit privileged corruption probe, rolled back by the outer case. It
    # is not an ordinary-user exploit and must never be presented as one.
    cur.execute("set local session_replication_role='replica'")
    cur.execute('update erp.journal_entries set economic_date=economic_date-1,transaction_date=transaction_date-1 where id=%s', (source,))
    if cur.rowcount != 1:
        raise AssertionError('Y_DETECTOR_EMPTY_MUTATION')
    cur.execute("set local session_replication_role='origin'")
    audit.owner(cur)
    observations = []
    for function in ('run_v267_financial_truth_checks', 'run_v268_financial_report_checks'):
        cur.execute('select * from erp.' + function + '() where check_name=%s', (DETECTORS[kind],))
        rows = cur.fetchall()
        if len(rows) != 1 or rows[0][1] != 'CRITICAL' or rows[0][2] != 1:
            raise AssertionError('Y_CANONICAL_DETECTOR_NOT_CONNECTED:' + str(rows))
        observations.append(dict(function=function, rows=rows))
    reports = audit.scrap.reports(cur, tuple(evidence['daily_evidence']))
    if any(r['data_confidence']['status'] != 'BLOCKED' for r in reports.values()):
        raise AssertionError('Y_CORRUPT_DATE_FALSE_READY')
    return dict(status='CONTROL_PASS', classification='PRIVILEGED_DISPOSABLE_CORRUPTION_DETECTOR_PROBE',
                ordinary_user_exploit=False, kind=kind, affected_journal_count=1, detectors=observations,
                report_confidence='BLOCKED', restored_by_case_rollback=True)
