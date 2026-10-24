"""Twelve unchanged payment controls with explicitly posted fixture capital.

Owner D14-3 forbids negative cash. The prior exact raw Crossflow142 report
preserves the empty-cash failures. Both baseline and current runs receive the
same labelled Native capital before each retained case; no oracle is changed.
"""
from datetime import date,timedelta
from decimal import Decimal
import cp6_v2620ai_family as original
import cp7_retained_cp6_fixture as fixture
import cp7_cash_funding as capital
IDS=('OPENING_SUBLEDGER:SUPPLIER_LAST_CENT', 'OPENING_SUBLEDGER:SUPPLIER_REVERSE_PAYMENT', 'OPENING_SUBLEDGER:SUPPLIER_CORRECTION', 'OPENING_SUBLEDGER:SUPPLIER_REVERSE_CORRECTION', 'OPENING_SUBLEDGER:SUPPLIER_RETURN', 'OPENING_SUBLEDGER:OPENING_PARTIES', 'OPENING_SUBLEDGER:SUPPLIER_VALID_LIFECYCLE', 'OPENING_SUBLEDGER:SUPPLIER_INVOICE_LIFECYCLE', 'OPENING_SUBLEDGER:FRACTIONAL_PURCHASES', 'OPENING_SUBLEDGER:SUPPLIER_AMOUNT_WASH', 'SUPPLIER_CENT:INVOICE_PAY_REVERSE', 'SUPPLIER_RETURN:LOW_CREDIT_PAYMENT_CAPACITY')
PHASE_IDS={'funded_retained_crossflow':IDS}

def declared_cases():
    found=[(n,fn)for n,fn in original.phase_cases('crossflow')if n in IDS]
    assert tuple(n for n,_ in found)==IDS
    return found


def cases(cur,today,*,current,evidence):
    day=today-timedelta(days=3)
    fixture.prepare(cur,today,current=current,closed_through=date(2026,8,31),evidence=evidence)
    found=declared_cases()
    result=[]
    for name,fn in found:
        def run(n=name,operation=fn):
            original.actors.admin(cur)
            cash,code,coa=cur.execute('select id,cash_account_code,coa_account_id from erp.cash_accounts where is_active order by cash_account_code limit 1').fetchone()
            journal=capital.fund(cur,cash,'1000.00',date(2026,9,1))
            original.actors.admin(cur)
            status,total_debit,total_credit,bank_debit=cur.execute("select j.status,sum(l.debit),sum(l.credit),sum(case when l.account_id=%s then l.debit-l.credit else 0 end)from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where j.id=%s group by j.status",(coa,journal)).fetchone()
            assert (status,total_debit,total_credit,bank_debit)==('POSTED',Decimal('1000'),Decimal('1000'),Decimal('1000'))
            funded=dict(journal_id=str(journal),cash_account_id=str(cash),cash_account_code=code,
                amount='1000.00',economic_date='2026-09-01',native_journal_posted=True,
                accounting_balanced=True,fixture_only=True,owner_real_figures_used=False)
            row=operation(cur,day)
            return dict(status=row.get('status'),original_result=row,retained_case_id=n,
                fixture_capital=funded,original_body_and_oracle_unchanged=True,cash_guard_unchanged=True)
        result.append((name,run))
    return result
