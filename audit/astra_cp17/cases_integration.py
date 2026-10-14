"""New Astra cross-stage worksheets. First execution only; no legacy case rerun.

SKN22 uses a real opening import before procurement. Hand-calculated constants:
10000 + 137.03 - 903.01 - 84.87 - 82.82 - 73 = 8993.33 cash;
32 raw x13.37=427.84; 32 FG x17.46=558.72; net9 sold x17.46=157.14.
Payroll and HPP leads are explicitly attributable to owner-forwarded Fable text.
"""
import json,uuid
from datetime import timedelta
from decimal import Decimal as D
import cases_business as b
import cp6_bb_probe as bb
import cp7_receipt_correction_cases as rc
import cp7_installment_cases as ins
import cases_payroll_leads as lead
from cases_stage import admin,check,wrap,save,api,new_run,read_pages

def integrity(cur):
    admin(cur)
    return [(str(k),int(n)) for k,n in cur.execute('select check_name,issue_count from erp.run_integrity_checks()').fetchall() if n]

def cases(cur,today):
    def journey():
        admin(cur);b.transport.attendance.quiet_seed(cur,today-timedelta(days=4),today)
        b.native(cur,'select erp.process_cost_recalc_queue(100)')
        start_integrity=integrity(cur)
        check(not start_integrity,'SKN22 starts with integrity zero',issues=start_integrity)
        rows=bb.masters(OPENING_BALANCE_ITEM=[dict(balance_type='CASH_BANK',cash_account_code='{C}',amount='10000.00',control_key='CASH')],
            OPENING_CONTROL=[dict(control_key='CASH',balance_type='CASH_BANK',amount='10000.00')])
        batch,code,cutover=bb.post_batch(cur,today,rows,prefix='AS17SKN22')
        bank,coa=cur.execute('select id::text,coa_account_id::text from erp.cash_accounts where cash_account_code=%s',(code,)).fetchone()
        g0=b.gl(cur);check(g0.get(coa)==10000,'Opening imported bank10000 has one real journal')
        p0=b.finance.read(cur,today)['snapshot']['financial_position']
        f=b.production(cur,today);f.update(bank=bank,cash_coa=coa)
        b.assess(cur,f)
        cards=b.nota.read(cur,'SOURCES',contractor_id=f['contractor'])['page']['rows']
        note=b.nota.command(cur,'SAVE',dict(contractor_id=f['contractor'],note_date=str(today),period_start=str(f['production_day']),period_end=str(today),cards=[dict(card_key=c['card_key'],source_token=c['source_token']) for c in cards],notes='Astra SKN22 real production sources'))
        f['payroll']=b.nota.act(cur,'POST',note)['payroll_id'];pid=f['payroll']
        b.settlement.act(cur,'PREPARE',b.settlement.doc(cur,pid));d=b.settlement.doc(cur,pid)
        check(D(d['net_payable'])==D('82.82'),'41x1.13 +41x.89 payable82.82')
        b.settlement.act(cur,'APPROVE',d)
        b.drafts.create(cur,f,b.drafts.payload(f,'13','29.91'));p,v=b.cmd.review(cur,f);b.cmd.command(cur,'POST',p,v)
        b.returns.payments.pay(cur,f,'137.03');f['allocations']=b.returns.read(cur,f)['page']['rows']
        p,v=b.returns.payload(cur,f,qty='4',refund='119.64');b.cmd.command(cur,'RETURN',p,v)
        from cp7_p18_full_cycle_cases import supplier_payment
        now=cur.execute('select clock_timestamp()').fetchone()[0]
        supplier_payment(cur,f,'903.01',now-timedelta(minutes=3))
        b.laundry.bd(cur,'PAY_VENDOR_DOCUMENT',dict(target_kind='VENDOR_INVOICE',target_id=f['laundry_invoice'],amount='84.87',date=str(today),cash_account_id=bank,reason='Astra SKN22 vendor full settlement'))
        b.settlement.act(cur,'PAY',b.settlement.doc(cur,pid),payment_date=str(today),cash_account_id=bank)
        check(b.gl(cur)[coa]==D('9066.33'),'Opening cash plus sale receipt less three actual payables')
        previous=f['purchase'];w=rc.ws(cur,previous)
        fix=rc.fix(cur,rc.payload(w,reason='Astra SKN22 original supplier price13.37, corrected after all payments',line=lambda n,item:item.update(unit_price='13.37')),w['purchase']['row_version'])
        f['purchase']=fix['purchase_id']
        b.native(cur,'select erp.process_cost_recalc_queue(100)')
        check(b.gl(cur)[coa]==D('9066.33'),'Receipt correction replays old cash once, no new cash')
        supplier_payment(cur,f,'73.00',now-timedelta(minutes=1))
        expected={b.account(cur,'MATERIAL_INVENTORY'):D('427.84'),b.account(cur,'FG_INVENTORY'):D('558.72'),b.account(cur,'AR_CUSTOMER'):D('132.16'),b.account(cur,'SALES_REVENUE'):D('-269.19'),b.account(cur,'COGS'):D('157.14'),coa:D('-1006.67')}
        actual=b.delta(g0,b.gl(cur))
        check(actual==expected,'Every final GL account equals independent worksheet',expected=expected,actual=actual)
        check(b.gl(cur)[coa]==D('8993.33') and b.fg_qty(cur,f)==32,'Final bank8993.33 and32 physical FG')
        check(rc.raw(cur,f['material'])==(D(32),D('427.84')),'Final raw32 at13.37')
        p1=b.finance.read(cur,today)['snapshot']['financial_position']
        wanted=dict(cash='-1006.67',customer_ar='132.16',material_inventory='427.84',fg_inventory='558.72',wip_inventory='0',supplier_final_ap='0',grni_estimated_liability='0',liabilities='0',assets='112.05',current_earnings='112.05',balance_difference='0')
        for k,v in wanted.items():check(D(p1[k])-D(p0[k])==D(v),'Dated report reconciles '+k,before=p0[k],after=p1[k],expected_delta=v)
        # Read all snapshot pages and live reminder obligations on this same story.
        r=new_run(cur,today,setup=False);proof=read_pages(cur,r)
        obligations=api(cur,'erp_cp7_get_reminder_obligations_v2',r['run'])
        check(obligations['basis']=='READ_NOW_NOT_FROM_SNAPSHOT' and obligations['sent'] is False,'Reminder reads live obligations without external delivery')
        related=[x for x in obligations['rows'] if str(f['sale']) in json.dumps(x)]
        check(bool(related),'Remaining customer132.16 still has named live reminder source',sale=f['sale'],obligations=obligations)
        check(all(D(x['financial_source']['remaining']['value'])==D('132.16') for x in related),'Reminder remaining matches authoritative customer debt',rows=related)
        after_integrity=integrity(cur);check(not after_integrity,'SKN22 ends with integrity zero',issues=after_integrity)
        bad=cur.execute('select journal_entry_id::text,sum(debit-credit) from erp.journal_lines group by journal_entry_id having sum(debit-credit)<>0').fetchall()
        check(not bad,'Every journal balances',bad=bad)
        return dict(opening_batch=batch,cutover=str(cutover),bank='8993.33',raw='427.84',fg='558.72',ar='132.16',revenue='269.19',cogs='157.14',gross_profit='112.05',payroll='82.82',source=f,previous_purchase=previous,report_before=p0,report_after=p1,actual_gl=actual,analysis_identity=proof['identity'],reminders=related,integrity_before=start_integrity,integrity_after=after_integrity)

    def dated_payroll():
        f=ins.fixture(cur,today);pid=f['payroll'];day=today-timedelta(days=2)
        before=integrity(cur);f['payment_date']=str(day)
        p0=b.finance.read(cur,day)['snapshot']['financial_position']
        response=lead.attempt(cur,lambda:ins.act(cur,f,amount='375.25'))
        if not response['accepted']:
            check(any(k in response['message'].lower() for k in ('date','tanggal','period','akrual')),'Relevant date refusal',result=response)
            return response
        p1=b.finance.read(cur,day)['snapshot']['financial_position'];admin(cur)
        actual=cur.execute("select j.source_type,j.source_id::text,j.transaction_date,j.economic_date,sum(l.credit-l.debit) from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where l.contractor_id=%s and l.account_id=erp.account_id('CONTRACTOR_PAYABLE') and j.status in('POSTED','REVERSED') and j.transaction_date<=%s group by 1,2,3,4 order by 1,2",(f['contractor'],day)).fetchall()
        due=sum((D(x[-1]) for x in actual),D(0));witness=dict(response=response,payroll=pid,as_of=str(day),accrual_date=str(today-timedelta(days=1)),dated_payable=due,journals=actual,before=p0,after=p1,integrity_before=before,integrity_after=integrity(cur))
        save('CP17_PAYROLL_DATED_PARTIAL_FIRST',witness)
        check(due>=0,'Ordinary partial payroll settlement must not create a negative contractor payable before any accrual',witness=witness)
        return witness

    def overlap_hpp():
        f=ins.fixture(cur,today);day=today-timedelta(days=1)
        b.native(cur,'select public.erp_set_contractor_hpp_policy_v1(%s::jsonb,%s,null)',(json.dumps(dict(contractor_id=f['contractor'],effective_from=str(day-timedelta(days=1)),is_special=False,attendance_required=True,reason='Astra overlapping pool source-identity control')),uuid.uuid4()))
        prod=ins.wip_source.b.chain.production;old=prod.CONTRACTOR
        try:
            prod.CONTRACTOR=f['contractor'];sewn=ins.wip_source.b.two_size_fixture(cur,today+timedelta(days=1),'AS17-HPP',q1=7,q2=3)
        finally:prod.CONTRACTOR=old
        call=lambda sql,args:ins.physical.source.fixture_journal_call(cur,sql,args)
        initial=call('select erp.preview_attendance_hpp_pool_v1(%s,%s)',(day,day))
        check(D(str(initial['numerator_amount']))==1000 and int(initial['denominator_qty'])==10,'Positive control:1000 real attendance,10 sewn')
        pool=call('select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s)',(json.dumps(dict(period_start=str(day),period_end=str(day),reason='Astra first attendance1000 pool')),uuid.uuid4()))
        active=call('select erp.activate_attendance_hpp_pool_v1(%s,%s,%s,%s)',(pool['pool_id'],'Astra active source control',uuid.uuid4(),pool['row_version']))
        # Broader overlapping range includes the same attendance date and sewing.
        # It must never allocate the first payroll accrual a second time.
        result=lead.attempt(cur,lambda:call('select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s)',(json.dumps(dict(period_start=str(day-timedelta(days=1)),period_end=str(day),reason='Astra overlap cannot duplicate existing accrual')),uuid.uuid4())))
        check(not result['accepted'] and 'No eligible normal-Mandor attendance payroll cost exists for this exact period' in result['message'],'A different overlapping range cannot consume the same exact-period payroll',result=result,first=active)
        return dict(first=active,second=result,source_payroll=f['payroll'],same_sewn_qty=10,scope='Same payroll source only; distinct legitimate payroll costs are not alleged duplicates')

    return [wrap('CP17-ASTRA-SKN22-OPENING-TO-CORRECTION',journey),wrap('CP17-ASTRA-PAY-06-DATED-PARTIAL',dated_payroll),wrap('CP17-ASTRA-HPP-01-OVERLAPPING-SOURCE',overlap_hpp)]
