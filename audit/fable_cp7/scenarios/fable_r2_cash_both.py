"""Fable r2 probe on 2e9d6a46: owner D15-1 (16 Oct 2026, wording in audit/fable_cp17_combined/OWNER_DECISIONS_TO_AUDITOR_20261016.md):
"periksa saldo harian per rekening menurut tanggal ekonomi dan tanggal buku/pengakuan. Tolak transaksi jika salah satunya
menjadi minus. Terapkan juga pada detektor dan koreksi/pembalikan, tanpa mengubah tanggal asli atau membuka ulang periode
tertutup secara otomatis."

Oracles fixed before any run:
CASH_BOTH_BASES_INVARIANT — sequence through the CP7 misc writers (SAVE/POST/REVERSE, erp_cp7_correct_misc_finance_v1):
  a income I1 = balance+1000 dated two days inside the closed period          -> accepted (control)
  b expense E1 = book balance through yesterday + 500, dated yesterday         -> REFUSED CP7_CASH_NEGATIVE (book basis)
  c expense E2 = balance + 500, dated now                                      -> accepted (both bases stay >= 0)
  d REVERSE income I1                                                           -> REFUSED (both bases would go < 0)
  e correct income I1 down to 0.01                                              -> REFUSED (final state < 0)
  f correct income I1 down by 100.00                                            -> accepted (final state >= 0; control)
  After every accepted step both per-day series of the bank (economic_date and transaction_date) are >= 0, no existing
  journal changed its economic/transaction date, closed_through unchanged.
  Any accepted step leaving a negative day -> COUNTEREXAMPLE. A control refused with CP7_CASH_NEGATIVE although its final
  state is >= 0 on both bases -> COUNTEREXAMPLE (the rule refuses only when one basis goes negative). A step refused or
  stopped for an unrelated reason -> recorded, not evidence either way (FAIL only if no guarded step was reached).
DETECTOR_BOOK_DATE — a book-date-only negative day is made by posting the expense of step b with the guard trigger
  disabled inside the case savepoint (fixture state, restored by the rollback). cp7_guard.findings() must list
  CASH_NEGATIVE_BOOK_DATE for that bank and must not list CASH_NEGATIVE (economic basis stays >= 0). Else COUNTEREXAMPLE.
"""
from datetime import timedelta
from decimal import Decimal as D
import json,uuid
import cp7_misc_cases as misc
import cp7_misc_correction_cases as mcorr
from fable_cp17_chain import q,one,sp,js
b,auth=misc.b,misc.auth


def series(cur,coa,lo,hi,col):
    rows=q(cur,f"""select d::date,(select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
             where l.account_id=%s and j.status in('POSTED','REVERSED') and j.{col}<=d::date)
             from generate_series(%s::date,%s::date,interval '1 day') d""",(coa,lo,hi))
    return [(str(d),str(v)) for d,v in rows]


def dates_fingerprint(cur,coa):
    return one(cur,"""select md5(coalesce(string_agg(j.id::text||j.economic_date::text||j.transaction_date::text,',' order by j.id),''))
                      from erp.journal_entries j where exists(select 1 from erp.journal_lines l where l.journal_entry_id=j.id and l.account_id=%s)""",(coa,))


def post_misc(cur,f,kind,amount,physical):
    p=misc.save_payload(f,kind,str(amount));p['physical_at']=physical
    s=misc.command(cur,'SAVE',p);return misc.command(cur,'POST',misc.intent(s))


def cases(cur,today):
    yday=today-timedelta(days=1)

    def setup():
        f=misc.fixture(cur,today);b.api.admin(cur)
        C=one(cur,'select closed_through from erp.accounting_period_control where singleton_id=1')
        bank=f['cash']['id'];coa=str(f['cash']['account_id'])
        now=one(cur,"select to_char((clock_timestamp()-interval '2 minutes') at time zone 'Asia/Jakarta','YYYY-MM-DD\"T\"HH24:MI:SS')||'+07:00'")
        return f,C,bank,coa,now

    def invariant():
        f,C,bank,coa,now=setup();lo=C-timedelta(days=6)
        P=D(str(misc.cash_balance(cur,bank)))
        Pt=D(one(cur,"select coalesce(sum(debit_total-credit_total),0)::text from erp.account_daily_balances where account_id=%s and balance_date<=%s",(coa,yday)))
        closed_day=C-timedelta(days=2)
        steps={};docs={}
        def check(name,expect,fn):
            fp0=dates_fingerprint(cur,coa);c0=one(cur,'select closed_through from erp.accounting_period_control where singleton_id=1')
            r=sp(cur,fn);b.api.admin(cur)
            es=series(cur,coa,lo,today,'economic_date');ts=series(cur,coa,lo,today,'transaction_date')
            neg=[x for x in es+ts if D(x[1])<0]
            refused_cash=r[0]!='OK' and 'CP7_CASH_NEGATIVE' in json.dumps(js(r))
            c1=one(cur,'select closed_through from erp.accounting_period_control where singleton_id=1')
            steps[name]=dict(expect=expect,outcome='ACCEPTED' if r[0]=='OK' else ('REFUSED_CASH' if refused_cash else 'STOPPED_OTHER'),
                             result=js(r)[:2] if r[0]!='OK' else 'OK',negative_days_after=neg,economic=es,book=ts,
                             closed_through_unchanged=(c0==c1))
            if r[0]=='OK':docs[name]=r[1]
            return r
        I1=P+D('1000.00')
        check('a_income_closed_day','ACCEPTED',lambda:post_misc(cur,f,'OTHER_INCOME',I1,str(closed_day)+'T08:00:00+07:00'))
        E1=Pt+D('500.00')
        check('b_expense_yesterday_book_negative','REFUSED',lambda:post_misc(cur,f,'OTHER_EXPENSE',E1,str(yday)+'T09:00:00+07:00'))
        E2=P+D('500.00')
        check('c_expense_now_covered','ACCEPTED',lambda:post_misc(cur,f,'OTHER_EXPENSE',E2,now))
        inc=docs.get('a_income_closed_day')
        if inc:
            check('d_reverse_income','REFUSED',lambda:misc.command(cur,'REVERSE',misc.intent(inc)))
            def correct(amount):
                old=dict(transaction_id=inc['transaction_id'],document=misc.native_document(cur,inc['transaction_id']))
                return mcorr.correct(cur,mcorr.payload(f,old,amount=str(amount)))
            check('e_correct_income_to_0_01','REFUSED',lambda:correct('0.01'))
            check('f_correct_income_minus_100','ACCEPTED',lambda:correct(I1-D('100.00')))
        bad=[];over=[];reached=[]
        for k,v in steps.items():
            if v['outcome']=='ACCEPTED' and v['negative_days_after']:bad.append(k)
            if not v['closed_through_unchanged']:bad.append(k+':closed_through_changed')
            if v['outcome']!='STOPPED_OTHER':reached.append(k)
            if v['expect']=='ACCEPTED' and v['outcome']=='REFUSED_CASH':over.append(k)
        guarded=[k for k in ('b_expense_yesterday_book_negative','d_reverse_income','e_correct_income_to_0_01') if k in reached]
        status='COUNTEREXAMPLE' if (bad or over) else ('PASS' if guarded else 'FAIL')
        return dict(status=status,violations=bad,over_refusals=over,guarded_steps_reached=guarded,closed_through=str(C),
                    amounts=dict(P=str(P),Pt_yday=str(Pt),I1=str(I1),E1=str(E1),E2=str(E2)),steps=steps,
                    oracle='D15-1: accepted steps keep economic and book per-day balance >= 0; refusals only when one basis goes negative')

    def detector():
        f,C,bank,coa,now=setup()
        P=D(str(misc.cash_balance(cur,bank)))
        Pt=D(one(cur,"select coalesce(sum(debit_total-credit_total),0)::text from erp.account_daily_balances where account_id=%s and balance_date<=%s",(coa,yday)))
        closed_day=C-timedelta(days=2)
        inc=sp(cur,lambda:post_misc(cur,f,'OTHER_INCOME',P+D('1000.00'),str(closed_day)+'T08:00:00+07:00'));b.api.admin(cur)
        if inc[0]!='OK':return dict(status='FAIL',reason='income not posted',income=js(inc))
        def bypass():
            cur.execute('reset role');cur.execute('alter table erp.journal_lines disable trigger cp7_guard_cash_not_negative')
            try:
                b.api.admin(cur);r=post_misc(cur,f,'OTHER_EXPENSE',Pt+D('500.00'),str(yday)+'T09:00:00+07:00')
            finally:
                cur.execute('reset role');cur.execute('alter table erp.journal_lines enable trigger cp7_guard_cash_not_negative');b.api.admin(cur)
            return r
        made=sp(cur,bypass);b.api.admin(cur)
        if made[0]!='OK':return dict(status='INCOMPLETE',stage='fixture bypass',error=js(made))
        trig=one(cur,"select tgenabled::text from pg_trigger where tgname='cp7_guard_cash_not_negative'")
        rows=q(cur,"""select f.kind,f.on_day::text,f.amount::text from cp7_guard.findings() f join erp.cash_accounts c on c.id=f.subject_id
                      where c.coa_account_id=%s and f.kind like 'CASH%%'""",(coa,))
        kinds={r[0] for r in rows}
        book=series(cur,coa,C-timedelta(days=6),today,'transaction_date');econ=series(cur,coa,C-timedelta(days=6),today,'economic_date')
        ok='CASH_NEGATIVE_BOOK_DATE' in kinds and 'CASH_NEGATIVE' not in kinds
        return dict(status='PASS' if ok else 'COUNTEREXAMPLE',findings=[list(r) for r in rows],trigger_enabled_after=trig,
                    book=book,economic=econ,oracle='book-only negative listed as CASH_NEGATIVE_BOOK_DATE, not as CASH_NEGATIVE')

    return [('FABLE_R2:CASH_BOTH_BASES_INVARIANT',invariant),('FABLE_R2:DETECTOR_BOOK_DATE',detector)]

def races(tools,today):return []
def http_cases(http,today):return []
