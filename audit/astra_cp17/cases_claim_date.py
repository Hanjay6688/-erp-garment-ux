"""Valid MISSING-claim fixtures for Fable R3-03; independent date oracles."""
from datetime import timedelta
from decimal import Decimal as D
import uuid
import cp6_bd_probe as bd
import cp7_finance_cases as finance
from cases_stage import admin,check,save,wrap
from cases_payroll_leads import attempt
from cases_finance_observability import detectors

def observe(cur,f,day):
    admin(cur)
    rows=cur.execute("""select j.id::text,j.source_type,j.source_id::text,j.transaction_date,j.economic_date,j.status,l.debit,l.credit
      from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id
      where l.vendor_id=%s and l.account_id=erp.account_id('AP_VENDOR')
      and j.status in('POSTED','REVERSED') order by j.transaction_date,j.id,l.id""",(f['vendor'],)).fetchall()
    return dict(journals=rows,dated_ap=sum((D(x[-1])-D(x[-2])for x in rows if x[3]<=day),D(0)),
        current_ap=D(bd.ap(cur,f['vendor'])),report=finance.read(cur,day),detectors=detectors(cur))

def scenario(cur,today,early):
    f=bd.fixture(cur,today-timedelta(days=3),'ASTRA-CLAIM-DATE')
    bd.process_rate(cur,f,'20.00');bd.invoice_policies(cur)
    delivery=bd.plain_delivery(cur,f,5,11)
    receipt=bd.receive(cur,delivery,f,4,13)
    line=bd.receipt_line(cur,receipt['receipt_id'])
    _,invoice=bd.invoice(cur,f,[dict(line=line,qty=4,amount='80.00')],'80.00')
    number='AS-CLAIM-'+uuid.uuid4().hex[:12]
    created=bd.d12_bs(cur,'SAVE_CLAIM',dict(action='SAVE',claim_number=number,vendor_id=f['vendor'],delivery_id=delivery,qty_claimed=1,claim_type='MISSING',compensation_amount=0,opened_at=str(f['day'])+'T15:00:00+07:00',change_reason='Astra five sent, four returned, one missing'))
    claim=bd.one(cur,'select id::text from erp.laundry_claims where claim_number=%s',number)
    day=f['day']-timedelta(days=1)if early else f['day']
    before=observe(cur,f,day)
    assert before['current_ap']==80 and before['dated_ap']==(0 if early else 80),before
    assert cur.execute('select status,qty_claimed,claim_type from erp.laundry_claims where id=%s',(claim,)).fetchone()==('OPEN',1,'MISSING')
    def resolve():
        accepted=bd.d12_bs(cur,'SAVE_CLAIM',dict(id=claim,action='SAVE',status='ACCEPTED',compensation_amount=20,resolution_date=str(day),change_reason='Astra reviewed compensation twenty'),bd.one(cur,'select row_version from erp.laundry_claims where id=%s',claim))
        settled=bd.d12_bs(cur,'RESOLVE_CLAIM',dict(laundry_claim_id=claim,resolution='SETTLED',change_reason='Astra first settlement date probe'),bd.one(cur,'select row_version from erp.laundry_claims where id=%s',claim))
        return dict(accepted=accepted,settled=settled)
    boundary_before=bd.boundary.snapshot(cur)
    result=attempt(cur,resolve)
    after=observe(cur,f,day)
    witness=dict(lead='Fable R3-03',oracle_origin='ASTRA_AFTER_AUTHORIZED_EXPOSURE',early=early,source_day=str(f['day']),resolution_day=str(day),vendor=f['vendor'],delivery=delivery,receipt=receipt,invoice=invoice,claim=claim,created=created,before=before,attempt=result,after=after)
    save('CP17_CLAIM_DATE_'+str(early)+'_FIRST',witness)
    if not result['accepted']:
        assert early and any(k in (result.get('message')or'').lower()for k in('date','tanggal','period','periode','accrual','akrual','payable','utang')),witness
        check(bd.boundary.snapshot(cur)==boundary_before and after['journals']==before['journals'] and after['dated_ap']==before['dated_ap'] and after['current_ap']==before['current_ap'] and after['detectors']==before['detectors'],'Rejected early claim must leave all business rows, journals and detectors unchanged',witness=witness)
        return witness
    assert after['current_ap']==60,witness
    if not early:
        check(after['dated_ap']==60,'Lawful same-day compensation reduces AP eighty to sixty',witness=witness)
    else:
        check(after['dated_ap']>=0,'Ordinary claim offset cannot settle vendor AP before any source payable exists',witness=witness)
    return witness

def cases(cur,today):
    return [wrap('CP17-ASTRA-CLAIM-01-SAME-DAY-CONTROL',lambda:scenario(cur,today,False)),
      wrap('CP17-ASTRA-CLAIM-02-BEFORE-SOURCE',lambda:scenario(cur,today,True))]
