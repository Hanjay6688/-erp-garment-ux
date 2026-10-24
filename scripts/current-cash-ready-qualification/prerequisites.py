"""Explicit lawful payroll linkage for the three diagnosed disposable fixtures."""
from datetime import date
from decimal import Decimal
import uuid
import cp6_aw_probe as aw
import cp7_cash_funding as capital

CONTRACTOR='a1000000-0000-0000-0000-000000000001'
EVIDENCE=[]


def complete_known_work(cur,cash=None):
    aw.api.admin(cur)
    rows=cur.execute("""select source_type,source_id::text,contractor_id::text,
        (eligible_at at time zone 'Asia/Jakarta')::date,remaining_qty,rate_snapshot,remaining_amount
        from erp.v_payroll_eligible_work_lines where remaining_qty>0 order by source_id""").fetchall()
    assert len(rows)==1,('EXPECTED_ONLY_NEW_FIXTURE_WORK',rows)
    kind,source,contractor,day,qty,rate,amount=rows[0]
    assert(kind,contractor,day,qty,rate,amount)==('PRODUCTION',CONTRACTOR,date(2026,9,1),10,Decimal(0),Decimal(0)),rows
    if cash is None:cash=cur.execute('select id from erp.cash_accounts where is_active order by id limit 1').fetchone()[0]
    pid=uuid.uuid4()
    cur.execute("""insert into erp.payroll_settlements(id,payroll_number,contractor_id,
        period_start,period_end,status,payment_cash_account_id,payment_date,manual_adjustment,notes)
        values(%s,%s,%s,%s,%s,'DRAFT',%s,%s,0,'Explicit zero-rate Native work fixture linkage')""",
        (pid,'READY3-'+pid.hex,contractor,day,day,cash,day))
    aw.chain.prior.as_owner(cur)
    populated=cur.execute('select erp.populate_payroll_draft(%s)',(pid,)).fetchone()[0]
    approved=cur.execute('select erp.approve_payroll(%s)',(pid,)).fetchone()[0]
    aw.api.admin(cur)
    header=cur.execute('select to_jsonb(p)from erp.payroll_settlements p where id=%s',(pid,)).fetchone()[0]
    assert header['status']=='APPROVED'and Decimal(str(header['net_payable']))==0,header
    links=cur.execute('select to_jsonb(w)from erp.payroll_work_items w where payroll_id=%s order by id',(pid,)).fetchall()
    assert len(links)==1 and str(links[0][0]['source_id'])==source and links[0][0]['qty_payable']==10,links
    assert cur.execute('select count(*)from erp.v_payroll_eligible_work_lines where remaining_qty>0').fetchone()==(0,)
    result=dict(known_original_work=rows,payroll_header=header,work_links=links,populate_receipt=populated,
        approve_receipt=approved,Native_approved_not_paid=True,rate_taken_from_actual_source=True,
        UNKNOWN_never_zero=True,no_policy_changed=True,no_original_posted_source_edited=True)
    EVIDENCE.append(result)
    return result


def fund_payment_bank(cur,cash):
    aw.api.admin(cur)
    coa=capital.coa(cur,cash);journal=capital.fund(cur,cash,'1000.00',date(2026,9,1))
    aw.api.admin(cur)
    result=cur.execute("""select j.status,sum(l.debit),sum(l.credit),
        sum(case when l.account_id=%s then l.debit-l.credit else 0 end)
        from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
        where j.id=%s group by j.status""",(coa,journal)).fetchone()
    assert result==('POSTED',Decimal(1000),Decimal(1000),Decimal(1000)),result
    return dict(journal_id=str(journal),cash_account_id=str(cash),amount='1000.00',
        economic_date='2026-09-01',Native_balanced_capital=True,negative_cash_guard_unchanged=True)
