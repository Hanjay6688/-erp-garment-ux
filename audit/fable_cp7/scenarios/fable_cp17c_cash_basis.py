"""Fable cp17c probe on dfab13bf: owner D14-3 cash guard vs the date basis of the cash reports.

Source reading (dfab13bf, scripts/cp7-src/finance/dated-guards.sql):
  * cp7_guard.guard_cash_line / min_debit_balance_from run the running cash balance on journal ECONOMIC_DATE.
  * erp.post_journal books account_daily_balances on transaction_date (= erp.resolve_accounting_transaction_date(economic_date));
    a document dated inside the closed period is recognised today.
  * the owner cash reader public.erp_cp7_get_finance_analysis_v1 states basis GL_TRANSACTION_DATE (account_daily_balances).
Hypothesis: income dated inside the closed period is recognised today, but the guard counts it on its economic date, so a
payment dated yesterday (open) passes the guard while the bank's transaction-date balance for yesterday is negative.

Oracle (fixed before any run, owner D14-3: "ditolak kalau membuat saldo kas/bank minus pada tanggal mana pun"):
  * expense refused with CP7_CASH_NEGATIVE                                   -> PASS (guard covers the report basis)
  * expense accepted and the bank's per-day balance on transaction_date (account_daily_balances, the basis the owner
    cash reader uses) is below zero on any day                               -> COUNTEREXAMPLE
  * expense accepted and no negative day                                     -> PASS (hypothesis refuted)
  * closed-period income cannot be recorded through the CP7 misc writer      -> the native capital journal is tried as the
    second route; the route used is recorded. Neither route reached          -> FAIL (plumbing, not evidence)
Writer helpers used as fixtures only (cp7_misc_cases.fixture/save_payload/command/intent); no guard is changed or bypassed.
"""
from datetime import timedelta
from decimal import Decimal as D
import json
import cp7_misc_cases as misc
import cp7_cash_funding as funding
from fable_cp17_chain import q,one,sp,js
b,auth=misc.b,misc.auth


def t_series(cur,coa,lo,hi):
    """Per-day closing balance of one cash COA on transaction_date (account_daily_balances), lo..hi inclusive."""
    rows=q(cur,"""select d::date,(select coalesce(sum(b.debit_total-b.credit_total),0) from erp.account_daily_balances b
                 where b.account_id=%s and b.balance_date<=d::date) from generate_series(%s::date,%s::date,interval '1 day') d""",(coa,lo,hi))
    return [(str(d),str(v)) for d,v in rows]


def e_series(cur,coa,lo,hi):
    """Same per-day balance on economic_date (the guard's basis), from journal lines POSTED/REVERSED."""
    rows=q(cur,"""select d::date,(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
                 where l.account_id=%s and j.status in('POSTED','REVERSED') and j.economic_date<=d::date)
                 from generate_series(%s::date,%s::date,interval '1 day') d""",(coa,lo,hi))
    return [(str(d),str(v)) for d,v in rows]


def cases(cur,today):
    yday=today-timedelta(days=1)

    def cash_basis_mismatch():
        f=misc.fixture(cur,today);b.api.admin(cur)
        C=one(cur,'select closed_through from erp.accounting_period_control where singleton_id=1')
        bank=f['cash']['id'];coa=str(f['cash']['account_id'])
        guard_installed=one(cur,"select to_regprocedure('cp7_guard.guard_cash_line()') is not null and exists(select 1 from pg_trigger where tgname='cp7_guard_cash_not_negative')")
        closed_day=C-timedelta(days=2)
        lo=closed_day-timedelta(days=2)
        p_all=D(str(misc.cash_balance(cur,bank)))
        p_t_yday=D(one(cur,"select coalesce(sum(debit_total-credit_total),0)::text from erp.account_daily_balances where account_id=%s and balance_date<=%s",(coa,yday)))
        income=p_all+D('1000.00');expense=p_t_yday+D('500.00')
        pre=dict(closed_through=str(C),closed_income_day=str(closed_day),bank=bank,coa=coa,guard_installed=guard_installed,
                 bank_balance_all_dates_before=str(p_all),bank_transaction_date_balance_yday_before=str(p_t_yday),
                 income_amount=str(income),expense_amount=str(expense))
        if not guard_installed:return dict(status='FAIL',reason='D14-3 guard not installed in this stack',pre=pre)
        # route 1: CP7 misc OTHER_INCOME, physical date inside the closed period
        p=misc.save_payload(f,'OTHER_INCOME',str(income));p['physical_at']=str(closed_day)+'T08:00:00+07:00'
        def misc_income():
            s=misc.command(cur,'SAVE',p);return misc.command(cur,'POST',misc.intent(s))
        inc=sp(cur,misc_income);route='APP_erp_cp7_save_misc_finance_v1_OTHER_INCOME'
        inc_journal=None
        if inc[0]=='OK':
            inc_journal=(inc[1].get('document') or {}).get('journals')
        else:
            pre['app_income_refused']=js(inc)
            inc=sp(cur,lambda:funding.fund(cur,bank,str(income),closed_day,'FABLE_CP17C_CLOSED_DAY_CAPITAL'));route='NATIVE_capital_journal_closed_day'
            b.api.admin(cur)
            if inc[0]!='OK':return dict(status='FAIL',reason='closed-period income not recorded by either route',pre=pre,native=js(inc))
            inc_journal=q(cur,"select id::text,economic_date::text,transaction_date::text,period_shifted from erp.journal_entries where id=%s",(inc[1],))
        # expense dated yesterday (open period) through the CP7 misc writer
        pe=misc.save_payload(f,'OTHER_EXPENSE',str(expense));pe['physical_at']=str(yday)+'T09:00:00+07:00'
        def misc_expense():
            s=misc.command(cur,'SAVE',pe);return misc.command(cur,'POST',misc.intent(s))
        exp=sp(cur,misc_expense);b.api.admin(cur)
        hi=today
        ts=t_series(cur,coa,lo,hi);es=e_series(cur,coa,lo,hi)
        neg_t=[x for x in ts if D(x[1])<0];neg_e=[x for x in es if D(x[1])<0]
        det=sp(cur,lambda:q(cur,"select kind,label,on_day::text,amount::text from cp7_guard.findings() where position('CASH' in kind)>0"))
        b.api.admin(cur)
        def reader(d):
            auth.actor(cur,None)
            r=one(cur,'select public.erp_cp7_get_finance_analysis_v1(%s)',(json.dumps({'from':str(d),'to':str(d),'as_of':str(d),'compare_from':str(d-timedelta(days=7)),'compare_to':str(d-timedelta(days=1))}),))
            b.api.admin(cur);return r.get('cash')
        rd=sp(cur,lambda:reader(yday));b.api.admin(cur)
        exp_journal=None
        if exp[0]=='OK':exp_journal=(exp[1].get('document') or {}).get('journals')
        refused_cash=exp[0]!='OK' and 'CP7_CASH_NEGATIVE' in json.dumps(js(exp))
        if exp[0]!='OK' and not refused_cash:status='FAIL'
        elif refused_cash:status='PASS'
        elif neg_t:status='COUNTEREXAMPLE'
        else:status='PASS'
        return dict(status=status,income_route=route,pre=pre,income_journals=js(inc_journal),expense=js(exp),expense_journals=js(exp_journal),
                    expense_refused_by_cash_guard=refused_cash,
                    bank_balance_by_transaction_date=ts,bank_balance_by_economic_date=es,
                    negative_days_transaction_date=neg_t,negative_days_economic_date=neg_e,
                    detector_cp7_guard_findings_cash=js(det),owner_cash_reader_yday_all_cash_coa=js(rd),
                    oracle='D14-3 any-day non-negative cash on the basis the owner cash report uses (transaction_date)')
    return [('FABLE_CP17C:CASH_BASIS_MISMATCH',cash_basis_mismatch)]

def races(tools,today):return []
def http_cases(http,today):return []
