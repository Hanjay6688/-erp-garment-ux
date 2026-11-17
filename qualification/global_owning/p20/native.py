"""P20 transaction oracles previously checked on the exact candidate's SKU replay."""

from datetime import timedelta
from decimal import Decimal as D
import json
import re
from uuid import uuid4

import psycopg

import cp7_sales_draft_cases as drafts
import cp7_finance_analysis_cases as finance
from cp7_credit_correction_de import e_cases as credit

cmd = drafts.cmd
source = cmd.source


def prepare(cur):
    cur.execute("set time zone 'Asia/Jakarta'")
    cur.execute("set lock_timeout='8s'; set statement_timeout='120s'")
    drafts.auth.actor(cur)
    drafts.b.api.admin(cur)
    cur.execute("select set_config('app.change_reason','P20 Global isolated fixture',true)")
    assert cur.execute("select erp.has_permission('sales.invoice.post')").fetchone() == (True,), 'CP7_P20_NATIVE_OWNER_REQUIRED'


def carry(conn, cur, today):
    pair = credit.fixture.prepare(cur, today)
    # Use the ordinary posted target path from the installed WIB/UTC control.
    at = source.fg.ax.r1.now(cur) - timedelta(minutes=10)
    target = credit.note.stock(cur, today, 10, at - timedelta(minutes=10))
    target['customer'] = pair['source']['f']['customer']
    target['sale_at'] = at.isoformat()
    credit.note.posted(cur, target, '5', '100')
    pair['target'] = target
    start = today - timedelta(days=8)
    query = finance.query(today, **{'from': str(start), 'compare_from': str(start-timedelta(days=9)),
                                   'compare_to': str(start-timedelta(days=1))})
    before = finance.read(cur, query)['cash']
    application = credit.basic.payload(pair, amount='80.00')
    application['physical_at'] = (at+timedelta(minutes=1)).isoformat()
    applied = credit.basic.command(cur, credit.basic.review(cur, application), uuid4())
    original = target['sale']
    before_profile = credit.fixture.retained.profiles(cur, pair)['target']
    assert before_profile['AR'] == '420.00', 'CP7_P20_PRE_CORRECTION_AR'
    assert finance.read(cur, query)['cash'] == before, 'CP7_P20_APPLY_CASH_CHANGED'
    conn.commit()

    stale, version, basis = credit.intent(cur, pair)
    assert basis['issues'] == [], ('CP7_P20_OPEN_NOTE_PAIR_UNQUALIFIED', basis['issues'])
    stale['credit_carry_review']['basis_sha256'] = '0' * 64
    snapshot = credit.observe(cur, pair)
    cur.execute('savepoint p20_stale_credit')
    try:
        credit.note.correct(cur, stale, version)
    except psycopg.Error as error:
        primary = error.diag.message_primary
        refusal = dict(sqlstate=error.sqlstate, message=primary if re.fullmatch(
                       r'(?:CP[67]_|GLOBAL_)[A-Z0-9_]{3,100}', primary or '') else type(error).__name__)
    else:
        refusal = dict(message='CP7_P20_STALE_CREDIT_ACCEPTED', sqlstate=None)
    finally:
        cur.execute('rollback to savepoint p20_stale_credit')
        cur.execute('release savepoint p20_stale_credit')
        drafts.b.api.admin(cur)
    changed = credit.observe(cur, pair)
    assert changed == snapshot, ('CP7_P20_STALE_CHANGED_NATIVE_STATE',
                                 sorted(key for key in snapshot if snapshot[key] != changed[key]))

    corrected, payload, version, _, key = credit.post(cur, pair)
    conn.commit()
    after_profile = credit.profile(cur, pair, original, corrected['sale_id'], '550.00', '80.00', '120.00')
    assert finance.read(cur, query)['cash'] == before, 'CP7_P20_CARRY_CASH_CHANGED'
    assigned = cur.execute("""select event_id::text,root_sale_id::text,replacement_sale_id::text
        from cp7_credit_note_carry_de.assignments_v1 where replacement_sale_id=%s""", (corrected['sale_id'],)).fetchall()
    assert assigned == [(applied['consumption_event_id'], original, corrected['sale_id'])], 'CP7_P20_CARRY_ASSIGNMENT'
    after = credit.observe(cur, pair)
    assert credit.note.correct(cur, payload, version, key) == corrected, 'CP7_P20_CARRY_REPLAY_OUTCOME'
    assert credit.observe(cur, pair) == after, 'CP7_P20_CARRY_REPLAY_EFFECT'
    stale_passed = refusal == dict(sqlstate='P0001', message='CP7_CREDIT_NOTE_CARRY_STALE_REVIEW')
    return dict(status='PASS' if stale_passed else 'INCOMPLETE', before_AR=before_profile['AR'],
                after_AR=after_profile['AR'], replacement_net='550.00', carried_credit='80.00', cash_delta='0.00',
                complete_cash_report_unchanged=True, exact_carry_assignment=True,
                physical_and_HPP_unchanged=True, immutable_original_and_credit_journal=True,
                exact_uuid_replay=True, stale_refusal=refusal, stale_refusal_preserved_state=True)


def seed_cash_browser(cur, today):
    day = today - timedelta(days=1)
    bank = source.bc.bank_account(cur, 'P20-PAGE')
    coa = str(cur.execute('select coa_account_id from erp.cash_accounts where id=%s',(bank,)).fetchone()[0])
    def debit(on, amount, label):
        return finance.journal(cur,on,[{'account_id':coa,'debit':amount},
            {'mapping_key':'OPENING_EQUITY','credit':amount}],label)
    debit(day - timedelta(days=1), '100.00', 'P20-PAGE-OPENING')
    for index in range(1,36):
        debit(day,str(D(index)+D('.25')),'P20-PAGE-RECEIPT')
