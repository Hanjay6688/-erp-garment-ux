"""New observation coverage for FIN-01, not a retry of PAY-06.

PAY-06 preserved only the financial-position section. This case asks the
previously unmeasured question: what do the full report and all three native
financial/integrity detector families show before and during the defect?
"""
from datetime import timedelta
from decimal import Decimal as D
import json
import cases_business as b
import cases_payroll_leads as lead
import cp7_installment_cases as ins
from cases_stage import admin, check, save, wrap

def detectors(cur):
    admin(cur)
    return [dict(family=f, name=n, severity=s, issues=int(i)) for f,n,s,i in cur.execute("""
        select 'v268',check_name,severity,issue_count from erp.run_v268_financial_report_checks()
        union all select 'v267',check_name,severity,issue_count from erp.run_v267_financial_truth_checks()
        union all select 'integrity',check_name,severity,issue_count from erp.run_integrity_checks()
        order by 1,2,3,4
    """).fetchall()]

def cases(cur, today):
    def observe():
        f=ins.fixture(cur,today)
        day=today-timedelta(days=2)
        f['payment_date']=str(day)
        before=dict(report=b.finance.read(cur,day),detectors=detectors(cur))
        response=lead.attempt(cur,lambda:ins.act(cur,f,amount='375.25'))
        if not response['accepted']:
            check(any(k in response['message'].lower() for k in ('date','tanggal','period','akrual')),
                  'Relevant date refusal required',response=response)
            return dict(refused=response,before=before)
        during=dict(report=b.finance.read(cur,day),detectors=detectors(cur))
        admin(cur)
        journals=cur.execute("""select j.source_type,j.source_id::text,j.transaction_date,j.economic_date,
            sum(l.credit-l.debit) from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
            where l.contractor_id=%s and l.account_id=erp.account_id('CONTRACTOR_PAYABLE')
            and j.status in('POSTED','REVERSED') and j.transaction_date<=%s
            group by 1,2,3,4 order by 1,2""",(f['contractor'],day)).fetchall()
        due=sum((D(x[-1]) for x in journals),D(0))
        witness=dict(purpose='Observe full detector and report confidence for the already confirmed date defect',
            payroll=f['payroll'],as_of=str(day),accrual_date=str(today-timedelta(days=1)),
            response=response,dated_payable=due,journals=journals,before=before,during=during,
            after_inverse='NOT_PERFORMED: transaction rollback is verified by strict runner; no guessed reversal API')
        save('CP17_FIN01_FULL_OBSERVABILITY_FIRST',witness)
        check(due>=0,'Ordinary payment cannot predate its entire payable accrual',witness=witness)
        return witness
    return [wrap('CP17-ASTRA-FIN-07-FULL-DETECTOR-OBSERVATION',observe)]
