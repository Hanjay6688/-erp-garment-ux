"""Independent P20 close acceptance on the installed, disposable product."""

from datetime import timedelta
from uuid import uuid4

from psycopg.types.json import Jsonb

import cp7_finance_cases as finance
import cp7_period_cases as periods
import cp7_r3_hpp_pool_cases as pool
import cp7_settlement_cases as payroll

from global_owning.p20 import attendance


def frozen_state(cur, day):
    journals = cur.execute("""select count(*),md5(coalesce(jsonb_agg(to_jsonb(j) order by j.id)::text,'[]'))
        from erp.journal_entries j""").fetchone()
    lines = cur.execute("""select count(*),md5(coalesce(jsonb_agg(to_jsonb(l) order by l.id)::text,'[]'))
        from erp.journal_lines l""").fetchone()
    choices = cur.execute("""select md5(coalesce(jsonb_agg(to_jsonb(d) order by d.id)::text,'[]'))
        from cp7_attendance_choice.decisions_v1 d where d.period_start=%s and d.period_end=%s""",
        (day, day)).fetchone()[0]
    return dict(journals=journals, lines=lines, choices=choices, business=periods.business(cur))


def rollback_marker(cur, today):
    decisions = cur.execute("""select md5(coalesce(jsonb_agg(to_jsonb(d) order by d.id)::text,'[]'))
        from cp7_attendance_choice.decisions_v1 d""").fetchone()[0]
    return dict(control=periods.read(cur, today)['control'], filings=periods.filings(cur),
                state=frozen_state(cur, today), decisions=decisions)


def ready_fixture(cur, today):
    """Set one disposable payroll day and check readiness through the actual reader."""
    one_day = timedelta(days=1)
    preferred = today - timedelta(days=5)
    oldest_booked = cur.execute("""select min(economic_date) from erp.journal_entries
        where status in ('POSTED', 'REVERSED')""").fetchone()[0]
    candidates = [preferred]
    if oldest_booked and oldest_booked <= preferred:
        candidates.append(oldest_booked - one_day)
    blockers = set()
    for day in candidates:
        cur.execute('savepoint p20_close_fixture')
        pool.set_closed(cur, day - one_day)
        # Give pre-existing synthetic workers their ordinary OFF/payroll evidence.
        periods.aw.quiet_seed(cur, day, day)
        snapshot, initial = attendance.observe(cur, day)
        preflight = initial['preflight']
        if preflight['date_allowed'] and preflight['status'] == 'READY' and not preflight['blockers']:
            cur.execute('release savepoint p20_close_fixture')
            return day, snapshot
        blockers.update(item['code'] for item in preflight['blockers'])
        cur.execute('rollback to savepoint p20_close_fixture')
        cur.execute('release savepoint p20_close_fixture')
    failure = AssertionError('AUDITOR_P20_CLOSE_INITIAL_NOT_READY')
    failure.audit_blocker_codes = sorted(blockers)
    raise failure


def run(cur, today):
    day, original = ready_fixture(cur, today)
    contractor = pool.contractor(cur, 'AUD-P20-CLOSE-' + uuid4().hex[:10])
    pool.policy(cur, contractor, day)
    payroll_id = str(cur.execute("""insert into erp.payroll_settlements
        (payroll_number,contractor_id,period_start,period_end,payment_date)
        values(%s,%s,%s,%s,%s) returning id""",
        ('AUD-P20-CLOSE-' + uuid4().hex[:10], contractor, day, day, day)).fetchone()[0])
    payroll.attendance(cur, dict(contractor=contractor), day)
    payroll.act(cur, 'PREPARE', payroll.doc(cur, payroll_id, attendance.OWNER), subject=attendance.OWNER)
    payroll.act(cur, 'APPROVE', payroll.doc(cur, payroll_id, attendance.OWNER), subject=attendance.OWNER)
    pending, blocked = attendance.observe(cur, day)
    assert blocked['preflight']['status'] == 'BLOCKED', 'AUDITOR_P20_CLOSE_PENDING_NOT_BLOCKED'
    assert [row['code'] for row in blocked['preflight']['blockers']] == [attendance.REQUIRED], 'AUDITOR_P20_CLOSE_PENDING_BLOCKER_NOT_EXACT'
    attendance.expect_delta(attendance.values(original), pending, wip_inventory=attendance.AMOUNT, liabilities=attendance.AMOUNT)

    attendance.choose(cur, day, 'EXPENSE')
    decided, ready = attendance.observe(cur, day)
    assert ready['preflight']['status'] == 'READY' and not ready['preflight']['blockers'], 'AUDITOR_P20_CLOSE_CHOICE_NOT_READY'
    attendance.expect_delta(attendance.values(original), decided,
                            operating_and_other_expense=attendance.AMOUNT, liabilities=attendance.AMOUNT)
    before = frozen_state(cur, day)
    filings = periods.filings(cur)
    request = uuid4()
    result = periods.command(cur, 'CLOSE', periods.intent(ready), request)
    assert result['closed_through'] == str(day) and result['filing_id'], 'AUDITOR_P20_CLOSE_NOT_CLOSED'
    after = periods.filings(cur)
    assert len(after) == len(filings) + 1 and after[-1]['id'] == result['filing_id'], 'AUDITOR_P20_CLOSE_FILING_MISMATCH'
    assert frozen_state(cur, day) == before, 'AUDITOR_P20_CLOSE_MUTATED_GL_OR_STOCK'
    assert periods.command(cur, 'CLOSE', periods.intent(ready), request) == result, 'AUDITOR_P20_CLOSE_REPLAY_RESPONSE_CHANGED'
    assert periods.filings(cur) == after and frozen_state(cur, day) == before, 'AUDITOR_P20_CLOSE_REPLAY_EFFECT'

    correction = dict(period_start=str(day), period_end=str(day), choice='CARRY',
                      output_start=None, output_end=None, reason='P20 closed-period correction refusal control')
    finance.auth.actor(cur, attendance.OWNER)
    refusal = finance.auth.refused(cur, lambda: cur.execute(
        'select public.erp_cp7_preview_attendance_choice_v1(%s,%s)', ('CORRECT', Jsonb(correction))),
        'CP7_S03_PERIOD_CLOSED')
    assert 'CP7_S03_PERIOD_CLOSED' in refusal, 'AUDITOR_P20_CORRECTION_WRONG_REFUSAL'
    assert periods.filings(cur) == after and frozen_state(cur, day) == before, 'AUDITOR_P20_CLOSED_CORRECTION_EFFECT'
    return dict(status='PASS', source_choice='EXPENSE', source_day=str(day), amount='100.00',
                initial_ready=True, pending_choice_blocked=True, ready_after_choice=True,
                filing_delta=1, same_uuid_replay_no_extra_filing=True,
                post_close_correction_refused=True, gl_and_stock_unchanged_by_close=True)
