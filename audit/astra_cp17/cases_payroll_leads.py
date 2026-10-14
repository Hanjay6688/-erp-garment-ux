"""Astra reproductions prompted by owner-forwarded Fable static leads.

All financial actions use candidate public payroll/Nota RPCs. Direct inserts
are limited to the unchanged writer's draft/master fixture. No posted cost,
paid state or journal is manufactured. Full first observations are retained.
"""
import json,re,traceback,uuid
from datetime import timedelta
from decimal import Decimal as D
import psycopg
import cp7_settlement_cases as s
import cp7_installment_cases as instal
from cases_stage import admin,check,wrap,save

def attempt(cur,operation):
    admin(cur);cur.execute('savepoint astra_lead_action')
    try:
        value=operation()
        return dict(accepted=True,value=value)
    except psycopg.Error as exc:
        out=dict(accepted=False,sqlstate=exc.sqlstate,message=exc.diag.message_primary,detail=exc.diag.message_detail)
        cur.execute('rollback to savepoint astra_lead_action')
        return out
    finally:
        admin(cur);cur.execute('release savepoint astra_lead_action')

def alarm(cur):
    admin(cur)
    rows=cur.execute("select check_name,severity,issue_count,details from erp.run_integrity_checks() where check_name='PAYROLL_ATTENDANCE_DUPLICATE'").fetchall()
    check(len(rows)==1,'Duplicate-attendance detector must be present exactly once',rows=rows)
    return dict(zip(('check_name','severity','issue_count','details'),rows[0]))

def payroll(cur,pid):
    return s.doc(cur,pid)

def prepare_approve(cur,pid):
    s.act(cur,'PREPARE',payroll(cur,pid));s.act(cur,'APPROVE',payroll(cur,pid))

def journals(cur,pids):
    admin(cur)
    return cur.execute("select j.source_type,j.source_id::text,j.transaction_date,j.status,l.account_id::text,l.debit,l.credit,j.economic_date from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where j.source_id=any(%s::uuid[]) order by j.source_type,j.source_id,j.transaction_date,l.account_id,l.id",(pids,)).fetchall()

def cases(cur,today):
    def control():
        f=s.review.fixture(cur,today);s.attendance(cur,f,today);pid=f['payroll'];bank=s.cash(cur)
        before=alarm(cur);check(before['issue_count']==0,'Clean fixture starts with no duplicate attendance',alarm=before)
        prepare_approve(cur,pid)
        check(D(payroll(cur,pid)['attendance_total'])==100,'One day at 100 creates one attendance entitlement')
        s.act(cur,'PAY',payroll(cur,pid),payment_date=str(today),cash_account_id=bank)
        check(s.journal(cur,pid,'PAYROLL_ATTENDANCE_ACCRUAL')==(2,D(100),D(100)),'One attendance accrual')
        check(s.journal(cur,pid,'PAYROLL_PAYMENT')==(2,D(6100),D(6100)),'6000 work plus100 attendance paid once')
        check(alarm(cur)['issue_count']==0,'Legal single payment preserves duplicate detector zero')
        return dict(payroll=pid,attendance='100',work='6000',payment='6100',journals=journals(cur,[pid]))

    def duplicate(first_paid):
        f=s.review.fixture(cur,today);s.attendance(cur,f,today);first=f['payroll'];bank=s.cash(cur)
        prepare_approve(cur,first)
        if first_paid:s.act(cur,'PAY',payroll(cur,first),payment_date=str(today),cash_account_id=bank)
        base=alarm(cur);check(base['issue_count']==0,'Single active source starts clean',alarm=base)
        # Fresh physical repair entitlement, distinct card; same contractor/date.
        s.source.ax.post(cur,s.source.ax.repair_payload(f,1))
        witness=dict(first_payroll=first,first_paid=first_paid,alarm_before=base)
        def second_note():
            n=s.n.command(cur,'SAVE',s.n.payload(cur,f,today));n=s.n.act(cur,'POST',n)
            second=n['payroll_id'];witness['second_payroll']=second
            s.act(cur,'PREPARE',payroll(cur,second));witness['prepared']=payroll(cur,second)
            witness['detector_prepared']=alarm(cur)
            s.act(cur,'APPROVE',payroll(cur,second));witness['approved']=payroll(cur,second)
            s.act(cur,'PAY',payroll(cur,second),payment_date=str(today),cash_account_id=bank)
            if not first_paid:s.act(cur,'PAY',payroll(cur,first),payment_date=str(today),cash_account_id=bank)
            witness['final']=[payroll(cur,p) for p in (first,second)]
            admin(cur)
            witness['duplicated_paid_records']=cur.execute("select i.attendance_record_id::text,count(*),sum(i.amount) from erp.payroll_attendance_items i join erp.payroll_settlements p on p.id=i.payroll_id where p.id=any(%s::uuid[]) and p.status='PAID' group by i.attendance_record_id having count(*)>1",([first,second],)).fetchall()
            witness['detector_final']=alarm(cur);witness['journals']=journals(cur,[first,second])
            return witness['final']
        witness['attempt']=attempt(cur,second_note)
        save('CP17_PAYROLL_DUPLICATE_'+str(first_paid)+'_FIRST',witness)
        if not witness['attempt']['accepted']:
            message=witness['attempt']['message'] or ''
            check(bool(re.search('duplicate|already.*(allocat|paid)|attendance.*(allocat|paid)|overlap|same.*period',message,re.I)),
                'Only a source-ownership refusal disproves this lead; unrelated setup failures remain reviewable',witness=witness)
        else:
            check(not witness['duplicated_paid_records'],'One attendance record must not fund two paid payrolls',witness=witness)
        return witness

    def early(installment=False):
        if installment:
            f=instal.fixture(cur,today);pid=f['payroll'];date=today-timedelta(days=2)
            def pay():
                f['payment_date']=str(date);return instal.act(cur,f,amount='1000.00')
        else:
            f=s.review.fixture(cur,today);s.attendance(cur,f,today);pid=f['payroll'];prepare_approve(cur,pid)
            date=today-timedelta(days=1);bank=s.cash(cur)
            def pay():return s.act(cur,'PAY',payroll(cur,pid),payment_date=str(date),cash_account_id=bank)
        before=journals(cur,[pid]);result=attempt(cur,pay);after=journals(cur,[pid])
        witness=dict(payroll=pid,payment_date=str(date),installment=installment,before=before,attempt=result,after=after)
        save('CP17_PAYROLL_EARLY_'+str(installment)+'_FIRST',witness)
        if not result['accepted']:
            check(bool(re.search('date|tanggal|period|periode|accrual|akrual',result['message'] or '',re.I)),
                'Early payment refused for a date/source rule',witness=witness)
        else:
            # The same source's attendance payable is recognized at period_end.
            accrual_dates=[r[2] for r in after if r[0]=='PAYROLL_ATTENDANCE_ACCRUAL']
            check(bool(accrual_dates),'Fixture has real attendance accrual',witness=witness)
            check(date>=min(accrual_dates),'Ordinary payroll settlement cannot precede its attendance accrual; advance requires its own source',witness=witness)
        return witness

    return [wrap('CP17-ASTRA-PAY-01-CONTROL',control),
        wrap('CP17-ASTRA-PAY-02-PAID-SOURCE',lambda:duplicate(True)),
        wrap('CP17-ASTRA-PAY-03-APPROVED-SOURCE',lambda:duplicate(False)),
        wrap('CP17-ASTRA-PAY-04-EARLY-FULL',lambda:early(False)),
        wrap('CP17-ASTRA-PAY-05-EARLY-INSTALLMENT',lambda:early(True))]
