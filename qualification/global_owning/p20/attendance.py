"""Check the official report against the Native close engine on the installed candidate."""

from decimal import Decimal
from uuid import uuid4

from psycopg.types.json import Jsonb

import cp7_finance_cases as finance
import cp7_period_cases as periods
import cp7_r3_hpp_pool_cases as pool
import cp7_settlement_cases as payroll


OWNER = finance.auth.base.OPERATOR_AUTH
CHOICES = {
    'EXPENSE': 'ATTENDANCE_ZERO_PERIOD_EXPENSE',
    'CARRY': 'ATTENDANCE_ZERO_CARRY_WAITING',
}
REQUIRED = 'ATTENDANCE_ZERO_CHOICE_REQUIRED'
AMOUNT = Decimal('100.00')


def observe(cur, day):
    report = finance.read(cur, day, OWNER)
    close = periods.read(cur, day, OWNER)
    assert report['close_preflight'] == close['preflight'], 'P20_OW07_CLOSE_REPORT_DIVERGED'
    snapshot = report['snapshot']
    confidence = snapshot['data_confidence']
    assert confidence['blockers'] == close['preflight']['blockers'], 'P20_OW07_REPORT_BLOCKERS_DIVERGED'
    assert confidence['info'] == close['preflight']['info'], 'P20_OW07_REPORT_INFO_DIVERGED'
    return snapshot, close


def values(snapshot):
    position = snapshot['financial_position']
    performance = snapshot['performance']
    return {name: Decimal(position[name]) for name in ('cash', 'wip_inventory', 'fg_inventory', 'liabilities')} | {
        name: Decimal(performance[name]) for name in ('cogs_gl', 'operating_and_other_expense')}


def expect_delta(before, current, **expected):
    after = values(current)
    delta = {name: value - before[name] for name, value in after.items() if value != before[name]}
    assert delta == expected, 'P20_OW07_WRONG_FINANCIAL_DELTA'


def clear_day(cur, today):
    day = cur.execute("""
        select candidate.day from (
            select %s::date - offsets.days as day, priority
            from unnest(array[2,1,3,4,5]) with ordinality offsets(days,priority)
        ) candidate
        where not exists (
            select 1 from erp.accounting_period_control where closed_through >= candidate.day
        ) and not exists (
            select 1 from erp.payroll_settlements where candidate.day between period_start and period_end
        ) and not exists (
            select 1 from erp.sewing_terminal_events where erp._cp3_business_date(physical_at) = candidate.day
        ) order by candidate.priority limit 1
    """, (today,)).fetchone()
    assert day is not None, 'P20_OW07_SYNTHETIC_PERIOD_NOT_OPEN_OR_OCCUPIED'
    day = day[0]
    original, close = observe(cur, day)
    assert close['preflight']['date_allowed'], 'P20_OW07_SYNTHETIC_PERIOD_NOT_OPEN'
    return day, original, close


def choose(cur, day, choice):
    intent = dict(period_start=str(day), period_end=str(day), choice=choice,
                  output_start=None, output_end=None, reason='P20 review of the real synthetic attendance source')
    finance.auth.actor(cur, OWNER)
    token = cur.execute('select public.erp_cp7_preview_attendance_choice_v1(%s,%s)',
                        ('CHOOSE', Jsonb(intent))).fetchone()[0]['review_token']
    payload = Jsonb(dict(intent, review_token=token))
    key = uuid4()
    approval = cur.execute('select public.erp_cp7_save_attendance_choice_v1(%s,%s,%s)',
                           ('CHOOSE', payload, key)).fetchone()[0]
    assert cur.execute('select public.erp_cp7_save_attendance_choice_v1(%s,%s,%s)',
                       ('CHOOSE', payload, key)).fetchone()[0] == approval, 'P20_OW07_WRONG_CHOICE_REPLAY'
    finance.b.api.admin(cur)
    assert approval['amount_cents'] == '10000', 'P20_OW07_WRONG_CHOICE_CENTS'


def run(cur, today, choice):
    day, original, opening = clear_day(cur, today)
    balances = values(original)
    contractor = pool.contractor(cur, 'P20-OW07-' + choice)
    pool.policy(cur, contractor, day)
    payroll_id = str(cur.execute("""
        insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,payment_date)
        values(%s,%s,%s,%s,%s) returning id
    """, ('P20-OW07-' + choice, contractor, day, day, day)).fetchone()[0])
    payroll.attendance(cur, dict(contractor=contractor), day)
    payroll.act(cur, 'PREPARE', payroll.doc(cur, payroll_id, OWNER), subject=OWNER)
    pending, _ = observe(cur, day)
    expect_delta(balances, pending)
    payroll.act(cur, 'APPROVE', payroll.doc(cur, payroll_id, OWNER), subject=OWNER)
    approved, blocked = observe(cur, day)
    expect_delta(balances, approved, wip_inventory=AMOUNT, liabilities=AMOUNT)
    baseline = opening['preflight']
    before = baseline['blockers']
    during = blocked['preflight']['blockers']
    assert all(entry in during for entry in before), 'P20_OW07_UNRELATED_BLOCKER_CHANGED'
    changed = [row['code'] for row in during if row not in before]
    assert changed == [REQUIRED] and approved['data_confidence']['status'] == 'BLOCKED', 'P20_OW07_FALSE_READY'
    filings = periods.filings(cur)
    refused = finance.auth.refused(cur, lambda: periods.command(
        cur, 'CLOSE', periods.intent(blocked), subject=OWNER), 'CLOSE_BLOCKED')
    assert REQUIRED in refused, 'P20_OW07_CLOSE_REFUSAL_MISSING_CHOICE'
    assert periods.filings(cur) == filings, 'P20_OW07_REFUSAL_WROTE_A_FILING'

    choose(cur, day, choice)
    decided, after = observe(cur, day)
    measure = 'operating_and_other_expense' if choice == 'EXPENSE' else 'wip_inventory'
    position = {'liabilities': AMOUNT, measure: AMOUNT}
    expect_delta(balances, decided, **position)
    assert after['preflight']['blockers'] == before, 'P20_OW07_AFTER_CHOICE_BLOCKERS_CHANGED'
    assert [r['code'] for r in after['preflight']['info'] if r not in baseline['info']] == [CHOICES[choice]], 'P20_OW07_INFO_MISSING'
    assert after['preflight']['status'] == baseline['status'], 'P20_OW07_AFTER_CHOICE_STATUS_CHANGED'
    return dict(status='PASS', choice=choice, source_day=str(day), amount=str(AMOUNT),
                official_report_matches_close=True, pending_choice_blocks_report_and_close=True,
                observed_choice_info=CHOICES[choice], unrelated_blockers_retained=len(before),
                stock_cogs_and_cash_unchanged=True, choice_replay=True,
                amounts={key: str(val) for key, val in position.items()})
