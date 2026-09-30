"""E05 fixed native money/source/date oracles, real locks and real Auth.

No mocked business writers. Each fixture creates valid native DRAFT/posted
attendance, then uses the existing controlled prepare/approval facade.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
import json,threading,time,uuid
import psycopg
import cp7_settlement_cases as legacy
import cp7_misc_cases as physical
import cp7_installment_bundle as bundle
import cp7_opening_payroll_cases as opening
import cp7_wip_source_cases as wip_source
auth,b=legacy.auth,legacy.b


def read(cur,pid,subject=None,**query):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_get_payroll_installments_v1(%s)',(json.dumps(dict(payroll_id=str(pid),**query)),)).fetchone()[0]
    b.api.admin(cur)
    return r


def command(cur,action,payload,version,key=None,subject=None):
    auth.actor(cur,subject)
    r=cur.execute('select public.erp_cp7_save_payroll_installment_v1(%s,%s,%s,%s)',(action,json.dumps(payload),key or uuid.uuid4(),str(version))).fetchone()[0]
    b.api.admin(cur)
    return r


def intent(doc,action,f=None,amount=None,payment=None):
    p=dict(payroll_id=doc['payroll_id'],review_token=doc['review_token'],change_reason='Native cash, dates, source and remaining payroll reviewed')
    if action=='PAY':
        p.update(amount=amount,payment_date=f['payment_date'],cash_account_id=f['cash']['id'],cash_review_token=f['cash']['review_token'])
    elif action=='REVERSE_PAYMENT':p['payment_id']=payment
    return p


def act(cur,f,action='PAY',amount='600.00',payment=None,key=None,subject=None):
    doc=read(cur,f['payroll'],subject)['document']
    return command(cur,action,intent(doc,action,f,amount,payment),doc['row_version'],key,subject)


def fixture(cur,today,attendance=True,manual='1000.00',deduction=False,deduction_amount='200.00'):
    b.api.admin(cur);day=today-timedelta(days=1)
    physical.source.receipt.aa.prior.set_open_period(cur,day-timedelta(days=3))
    tag='E05-'+uuid.uuid4().hex[:12]
    contractor=str(cur.execute('insert into erp.contractors(contractor_code,contractor_name,attendance_required)values(%s,%s,%s)returning id',(tag,tag,attendance)).fetchone()[0])
    pid=str(cur.execute('insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,manual_adjustment,payment_date)values(%s,%s,%s,%s,%s,%s)returning id',(tag,contractor,day,day,'0.00'if attendance else manual,day)).fetchone()[0])
    if attendance:
        w=legacy.native(cur,'select public.erp_save_worker_roster_v1(%s::jsonb,%s,null)',(json.dumps(dict(contractor_id=contractor,worker_code=tag,worker_name='E05 native attendance worker',job_description='Jahit',pay_scheme='DAILY',initial_daily_rate=1000,rate_effective_from=str(day),joined_at=str(day),is_active=True,reason='E05 real worker with fixed daily1000')),uuid.uuid4()))
        wid=legacy.bc.awp.find(w,'worker_id')
        ap=legacy.native(cur,'select public.erp_save_attendance_period_v1(%s::jsonb,%s,null,false)',(json.dumps(dict(contractor_id=contractor,period_number=tag+'-ATT',period_start=str(day),period_end=str(day),pay_date=str(day),reason='E05 posted earned attendance',attendance=[dict(worker_id=str(wid),attendance_date=str(day),status='PRESENT')])),uuid.uuid4()))
        legacy.native(cur,'select public.erp_post_attendance_period_v1(%s,%s,%s,%s)',(legacy.bc.awp.find(ap,'period_id'),'E05 attendance reviewed',uuid.uuid4(),legacy.bc.awp.find(ap,'row_version')))
    item=None
    if deduction:
        fx=legacy.bc.fixture(cur,day,zones=False)
        _,item=legacy.bc.note(cur,fx,1,deduction_amount,day,contractor=contractor)
    legacy.act(cur,'PREPARE',legacy.doc(cur,pid))
    before_approval=legacy.gl(cur,contractor)
    legacy.act(cur,'APPROVE',legacy.doc(cur,pid))
    bank=legacy.cash(cur)
    cash=cur.execute('select cp7_installment.cash(%s)',(bank,)).fetchone()[0]
    approved=legacy.doc(cur,pid)
    expected=(D('1000.00')if attendance else D(manual))-(D(deduction_amount)if deduction else D(0))
    assert D(approved['net_payable'])==expected,approved
    return dict(tag=tag,payroll=pid,contractor=contractor,cash=cash,payment_date=str(day),today=str(today),approved=approved,item=item,
                before_approval={k:str(v)for k,v in before_approval.items()},approved_gl={k:str(v)for k,v in legacy.gl(cur,contractor).items()},physical=physical.stock_cost(cur))


def delta(cur,f):return legacy.change({k:D(v)for k,v in f['approved_gl'].items()},legacy.gl(cur,f['contractor']))
def assert_balance(cur,f,paid,remaining,status='APPROVED'):
    d=read(cur,f['payroll'])['document']
    assert(D(d['approved_net']),D(d['paid_amount']),None if d['remaining_amount']is None else D(d['remaining_amount']),d['native_status'])==(D(f['approved']['net_payable']),D(paid),None if remaining is None else D(remaining),status),d
    assert physical.stock_cost(cur)==f['physical']
    return d


def cases(cur,today):
    def lifecycle():
        f=fixture(cur,today);cost=legacy.journal(cur,f['payroll'],'PAYROLL_ATTENDANCE_ACCRUAL');assert cost==(2,D(1000),D(1000))
        first=act(cur,f);assert_balance(cur,f,'600','400');assert delta(cur,f)=={legacy.acct(cur,'CONTRACTOR_PAYABLE'):D(600),f['cash']['account_id']:D(-600)}
        f['payment_date']=str(today);act(cur,f,amount='400.00');assert_balance(cur,f,'1000','0','PAID');assert legacy.journal(cur,f['payroll'],'PAYROLL_ATTENDANCE_ACCRUAL')==cost
        act(cur,f,'REVERSE_PAYMENT',payment=first['payment_id']);assert_balance(cur,f,'400','600');assert legacy.journal(cur,f['payroll'],'PAYROLL_ATTENDANCE_ACCRUAL')==cost
        hist=read(cur,f['payroll'])['payments']['rows'];original=next(x for x in hist if x['id']==first['payment_id']);assert original['payment_date']==str(today-timedelta(days=1))and original['reversal_accounting_date']==str(today)and original['reversal_journal_id']is not None
        act(cur,f,amount='600.00');assert_balance(cur,f,'1000','0','PAID');assert delta(cur,f)=={legacy.acct(cur,'CONTRACTOR_PAYABLE'):D(1000),f['cash']['account_id']:D(-1000)}
        assert legacy.journal(cur,f['payroll'],'PAYROLL_ATTENDANCE_ACCRUAL')==cost
        return dict(status='PASS',approved1000_cash600_remaining400_final400_same_document=True,cost1000_recognized_once=True,individual_inverse_preserves_original_and_own_date=True,replacement600_settles_same_net=True)
    def deductions():
        f=fixture(cur,today,deduction=True);base=legacy.gl(cur,f['contractor']);act(cur,f);assert_balance(cur,f,'600','200')
        assert legacy.journal(cur,f['payroll'],'PAYROLL_MATERIAL_DEDUCTION')==(0,D(0),D(0))
        assert cur.execute('select payroll_status from erp.contractor_material_issue_items where id=%s',(f['item'],)).fetchone()[0]=='ALLOCATED'
        act(cur,f,amount='200.00');assert_balance(cur,f,'800','0','PAID');assert legacy.journal(cur,f['payroll'],'PAYROLL_MATERIAL_DEDUCTION')==(2,D(200),D(200))
        assert cur.execute('select payroll_status from erp.contractor_material_issue_items where id=%s',(f['item'],)).fetchone()[0]=='SETTLED'
        payment=read(cur,f['payroll'])['payments']['rows'][0]['id'];act(cur,f,'REVERSE_PAYMENT',payment=payment);assert_balance(cur,f,'200','600');assert legacy.journal(cur,f['payroll'],'PAYROLL_MATERIAL_DEDUCTION')==(0,D(0),D(0))
        assert cur.execute('select payroll_status from erp.contractor_material_issue_items where id=%s',(f['item'],)).fetchone()[0]=='ALLOCATED'
        act(cur,f,amount='600.00');assert_balance(cur,f,'800','0','PAID');assert legacy.journal(cur,f['payroll'],'PAYROLL_MATERIAL_DEDUCTION')==(2,D(200),D(200))
        assert legacy.change(base,legacy.gl(cur,f['contractor']))=={legacy.acct(cur,'CONTRACTOR_PAYABLE'):D(1000),legacy.acct(cur,'CONTRACTOR_RECEIVABLE'):D(-200),f['cash']['account_id']:D(-800)}
        return dict(status='PASS',gross1000_reserved_material200_net800_cash600_remaining200=True,deduction_reserved_until_final_and_settled_once=True,paid_inverse_reopens_native_reservation_then_repayment_settles_once=True)
    def whole(partial):
        f=fixture(cur,today);act(cur,f)
        if not partial:act(cur,f,amount='400.00')
        act(cur,f,'REVERSE_PAYROLL');assert_balance(cur,f,'0',None,'REVERSED')
        assert legacy.change({k:D(v)for k,v in f['before_approval'].items()},legacy.gl(cur,f['contractor']))=={}
        assert all(p['status']=='REVERSED'and p['reversal_journal_id']for p in read(cur,f['payroll'])['payments']['rows'])
        return dict(status='PASS',partial=partial,all_active_cash_and_approved_cost_inversed_once=True,no_false_outstanding_balance=True)
    def large():
        f=fixture(cur,today,attendance=False,manual='9007199254740993.01');act(cur,f,amount='9007199254740993.00');assert_balance(cur,f,'9007199254740993.00','0.01');act(cur,f,amount='0.01');assert_balance(cur,f,'9007199254740993.01','0','PAID')
        assert delta(cur,f)=={legacy.acct(cur,'CONTRACTOR_PAYABLE'):D('9007199254740993.01'),f['cash']['account_id']:D('-9007199254740993.01')}
        return dict(status='PASS',native_exact9007199254740993_01_two_installments=True,no_float_or_second_cost_engine=True)
    def amounts():
        f=fixture(cur,today);act(cur,f);d=read(cur,f['payroll'])['document'];before=b.boundary.snapshot(cur)
        for v in ('400.01','600.00','0','-1','1.001','NaN','Infinity','1e2',600):
            p=intent(d,'PAY',f,v);auth.refused(cur,lambda:command(cur,'PAY',p,d['row_version']),'CP7_INSTALLMENT_')
        assert b.boundary.snapshot(cur)==before;assert_balance(cur,f,'600','400')
        return dict(status='PASS',overpayment_zero_negative_float_and_noncent_money_refused_atomically=True)
    def fields():
        f=fixture(cur,today);d=read(cur,f['payroll'])['document'];p=intent(d,'PAY',f,'600.00');before=b.boundary.snapshot(cur)
        for patch in ({'force':True},{'payroll_id':'bad'},{'cash_account_id':'bad'},{'review_token':'bad'},{'change_reason':'x'},{'payment_date':'2026-02-30'},{'payment_date':str(today+timedelta(days=1))}):
            auth.refused(cur,lambda:command(cur,'PAY',dict(p,**patch),d['row_version']),'CP7_INSTALLMENT_')
        auth.refused(cur,lambda:command(cur,'PAY',p,'0'),'CP7_INSTALLMENT_FIELDS');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',closed_canonical_UUID_source_revision_reason_and_native_date_fields=True,no_partial_effects=True)
    def replay():
        f=fixture(cur,today);d=read(cur,f['payroll'])['document'];p=intent(d,'PAY',f,'600.00');key=uuid.uuid4();r=command(cur,'PAY',p,d['row_version'],key);before=b.boundary.snapshot(cur)
        assert command(cur,'PAY',p,d['row_version'],key)==r and b.boundary.snapshot(cur)==before
        auth.refused(cur,lambda:command(cur,'PAY',dict(p,amount='400.00'),d['row_version'],key),'CP7_INSTALLMENT_REQUEST_CHANGED')
        act(cur,f,'REVERSE_PAYROLL');assert command(cur,'PAY',p,d['row_version'],key)==r;assert_balance(cur,f,'0',None,'REVERSED')
        return dict(status='PASS',exact_cached_outcome_one_effect_and_changed_intent_atomic=True,cached_outcome_not_repainted_as_current_native_state=True)
    def stale():
        f=fixture(cur,today);d=read(cur,f['payroll'])['document'];p=intent(d,'PAY',f,'600.00');act(cur,f);before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:command(cur,'PAY',p,d['row_version']),'CP7_INSTALLMENT_REVIEW_CHANGED');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',stale_approved_review_cannot_create_second_effect=True)
    def cash_source():
        f=fixture(cur,today);d=read(cur,f['payroll'])['document'];p=intent(d,'PAY',f,'600.00');cur.execute('update erp.cash_accounts set is_active=false where id=%s',(f['cash']['id'],));before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:command(cur,'PAY',p,d['row_version']),'CP7_INSTALLMENT_CASH_SOURCE_CHANGED');assert b.boundary.snapshot(cur)==before
        return dict(status='PASS',current_cash_master_not_invented_eligible_from_old_option=True)
    def access():
        f=fixture(cur,today);subject,role=legacy.source.procurement.custom(cur,('finance.payroll.view','finance.payroll.pay'));act(cur,f,subject=subject)
        auth.refused(cur,lambda:act(cur,f,'REVERSE_PAYROLL',subject=subject),'CP7_INSTALLMENT_ACCESS_DENIED')
        pid=read(cur,f['payroll'],subject)['payments']['rows'][0]['id'];act(cur,f,'REVERSE_PAYMENT',payment=pid,subject=subject)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.payroll.pay'",(role,));assert read(cur,f['payroll'],subject)['capabilities']==dict(pay=False,reverse_payroll=False)
        auth.refused(cur,lambda:act(cur,f,subject=subject),'CP7_INSTALLMENT_ACCESS_DENIED');bundle.verify(cur)
        return dict(status='PASS',custom_current_view_pay_role_can_installment_and_individual_inverse=True,whole_payroll_inverse_requires_approve_too=True,view_only_reads_without_writes=True,no_ERP_DML_native_EXEC_or_private_context=True)
    def legacy_bypass():
        f=fixture(cur,today);act(cur,f);before=b.boundary.snapshot(cur)
        for action in ('PAY','CANCEL'):
            kwargs=dict(payment_date=f['payment_date'],cash_account_id=f['cash']['id'])if action=='PAY'else{}
            auth.refused(cur,lambda:legacy.act(cur,action,legacy.doc(cur,f['payroll']),**kwargs),'CP7_INSTALLMENT_PRIVATE_CONTEXT_REQUIRED')
        auth.refused(cur,lambda:physical.source.fixture_journal_call(cur,'select erp.post_payroll_payment(%s)',(f['payroll'],)),'CP7_INSTALLMENT_PRIVATE_CONTEXT_REQUIRED')
        assert b.boundary.snapshot(cur)==before;assert_balance(cur,f,'600','400')
        return dict(status='PASS',legacy_full_payment_cancel_and_direct_native_payment_cannot_bypass_managed_cash=True,all_refusals_atomic=True)
    def immutable():
        f=fixture(cur,today);act(cur,f);before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:cur.execute('update erp.payroll_settlements set manual_adjustment=1 where id=%s',(f['payroll'],)),'CP7_INSTALLMENT_APPROVED_SOURCE_IMMUTABLE')
        auth.refused(cur,lambda:cur.execute("insert into erp.payroll_deductions(payroll_id,deduction_type,amount)values(%s,'OTHER',1)",(f['payroll'],)),'CP7_INSTALLMENT_APPROVED_SOURCE_IMMUTABLE')
        row=read(cur,f['payroll'])['payments']['rows'][0]
        auth.refused(cur,lambda:physical.source.fixture_journal_call(cur,'select erp.reverse_journal(%s,%s)',(row['journal_id'],'Bypass control')),'CP7_INSTALLMENT_PRIVATE_CONTEXT_REQUIRED')
        assert b.boundary.snapshot(cur)==before;assert_balance(cur,f,'600','400')
        return dict(status='PASS',approved_header_children_and_original_native_cash_immutable_outside_owning_flow=True)
    def dates():
        f=fixture(cur,today);act(cur,f);before=read(cur,f['payroll']);rows=[]
        for tz in ('UTC','Asia/Jakarta','America/Los_Angeles'):
            cur.execute("select set_config('TimeZone',%s,true)",(tz,));r=read(cur,f['payroll']);r.pop('captured_at');rows.append(r)
            cash=cur.execute('select cp7_installment.cash(%s)',(f['cash']['id'],)).fetchone()[0]
            assert cash==f['cash'],(tz,cash,f['cash'])
        assert rows[0]==rows[1]==rows[2];cur.execute("set local timezone='UTC'")
        # The payment applies under WIB although these review tokens were read
        # under UTC. It must use the same actual native cash/source facts.
        act(cur,f,amount='400.00');assert_balance(cur,f,'1000','0','PAID')
        assert before['payments']['rows'][0]['economic_date']==f['payment_date']
        return dict(status='PASS',physical_and_accounting_native_dates_and_complete_review_caller_timezone_independent=True)
    def pages():
        f=fixture(cur,today)
        for _ in range(30):act(cur,f,amount='1.23')
        before=b.boundary.snapshot(cur);a=read(cur,f['payroll']);z=read(cur,f['payroll'],payment_offset=25)
        assert[a['payments']['total'],z['payments']['total']]==['30','30']and[len(a['payments']['rows']),len(z['payments']['rows'])]==[25,5]
        assert a['document']==z['document']and D(a['document']['paid_amount'])==D('36.90')and D(a['document']['remaining_amount'])==D('963.10')
        assert len({p['id']for r in(a,z)for p in r['payments']['rows']})==30 and b.boundary.snapshot(cur)==before
        return dict(status='PASS',native30_installments_complete25_plus5_pages=True,full_paid36_90_remaining963_10_not_page_subtotal=True,read_only=True)
    def legacy_history():
        f=fixture(cur,today);legacy.act(cur,'PAY',legacy.doc(cur,f['payroll']),payment_date=f['payment_date'],cash_account_id=f['cash']['id'])
        d=read(cur,f['payroll']);assert not d['document']['managed']and d['payments']['total']=='0';assert_balance(cur,f,'1000','0','PAID')
        auth.refused(cur,lambda:act(cur,f),'CP7_INSTALLMENT_APPROVED_POSITIVE_PAYROLL_ONLY')
        return dict(status='PASS',existing_native_full_payment_remains_exact_readonly_legacy_cash=True,no_fake_installment_import_or_unpaid_zero=True)
    def zero():
        f=fixture(cur,today,attendance=False,manual='1.00');legacy.act(cur,'CANCEL',legacy.doc(cur,f['payroll']))
        auth.refused(cur,lambda:act(cur,f),'CP7_INSTALLMENT_APPROVED_POSITIVE_PAYROLL_ONLY')
        assert read(cur,f['payroll'])['document']['remaining_amount']is None
        return dict(status='PASS',inactive_payroll_not_falsely_eligible_for_cash=True)
    def opening_sources():
        f=opening.fixture(cur,today);pid=f['payroll'];before=opening.state(cur,f);opening.all_sources(cur,f)
        legacy.act(cur,'PREPARE',legacy.doc(cur,pid));legacy.act(cur,'APPROVE',legacy.doc(cur,pid));native=legacy.doc(cur,pid)
        assert native['net_payable']=='6060.00'
        cash=cur.execute('select cp7_installment.cash(%s)',(f['cash'],)).fetchone()[0]
        ef=dict(f,cash=cash,payment_date=str(today),approved=native,approved_gl={k:str(v)for k,v in legacy.gl(cur,f['contractor']).items()},physical=physical.stock_cost(cur))
        first=act(cur,ef,amount='3000.00');assert_balance(cur,ef,'3000','3060');opening.assert_remaining(opening.state(cur,f),65,20,30,2)
        assert legacy.journal(cur,pid,'PAYROLL_CASH_ADVANCE_DEDUCTION')==(0,D(0),D(0))
        act(cur,ef,amount='3060.00');assert_balance(cur,ef,'6060','0','PAID');opening.assert_remaining(opening.state(cur,f),0,0,0,2)
        assert legacy.journal(cur,pid,'PAYROLL_CASH_ADVANCE_DEDUCTION')==(2,D(30),D(30))
        act(cur,ef,'REVERSE_PAYMENT',payment=first['payment_id']);assert_balance(cur,ef,'3060','3000');opening.assert_remaining(opening.state(cur,f),65,20,30,2)
        act(cur,ef,amount='3000.00');assert_balance(cur,ef,'6060','0','PAID');opening.assert_remaining(opening.state(cur,f),0,0,0,2)
        act(cur,ef,'REVERSE_PAYROLL');assert_balance(cur,ef,'0',None,'REVERSED');after=opening.state(cur,f);opening.assert_remaining(after,65,20,30,4)
        assert legacy.change(before['gl'],after['gl'])=={}and after['physical']==before['physical']
        return dict(status='PASS',native_opening_payable85_advance30_carry2x2_50_net6060_cash3000_plus3060=True,source_reservations_until_final_and_expense5_once=True,individual_inverse_reopens_native_opening_balances=True,whole_inverse_restores_source_cash_and_cost=True)
    def zero_net():
        f=fixture(cur,today,deduction=True,deduction_amount='1000.00')
        cost=legacy.journal(cur,f['payroll'],'PAYROLL_ATTENDANCE_ACCRUAL')
        assert cost==(2,D(1000),D(1000));assert_balance(cur,f,'0','0')
        before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:act(cur,f,amount='1.00'),'CP7_INSTALLMENT_APPROVED_POSITIVE_PAYROLL_ONLY')
        assert b.boundary.snapshot(cur)==before
        assert cur.execute('select count(*)from cp7_installment.accounts where payroll_id=%s',(f['payroll'],)).fetchone()[0]==0
        legacy.act(cur,'PAY',legacy.doc(cur,f['payroll']),payment_date=f['payment_date'],cash_account_id=f['cash']['id'])
        assert_balance(cur,f,'0','0','PAID')
        assert legacy.journal(cur,f['payroll'],'PAYROLL_PAYMENT')==(0,D(0),D(0))
        assert legacy.journal(cur,f['payroll'],'PAYROLL_MATERIAL_DEDUCTION')==(2,D(1000),D(1000))
        assert legacy.journal(cur,f['payroll'],'PAYROLL_ATTENDANCE_ACCRUAL')==cost
        assert cur.execute('select payroll_status from erp.contractor_material_issue_items where id=%s',(f['item'],)).fetchone()[0]=='SETTLED'
        assert read(cur,f['payroll'])['payments']['total']=='0'
        return dict(status='PASS',native_attendance1000_material1000_net0_cash_refused_atomically=True,native_zero_cash_final_settles_material_once_without_fake_installment=True,approved_cost1000_unchanged=True)
    def active_hpp():
        f=fixture(cur,today);day=today-timedelta(days=1)
        legacy.native(cur,'select public.erp_set_contractor_hpp_policy_v1(%s::jsonb,%s,null)',(json.dumps(dict(contractor_id=f['contractor'],effective_from=str(day),is_special=False,attendance_required=True,reason='E05 explicit normal Mandor attendance HPP policy')),uuid.uuid4()))
        # Existing source fixture posts real receipt/cutting/pickup/completion/
        # sewing through the unchanged native lifecycle. No HPP status is seeded.
        production=wip_source.b.chain.production;old=production.CONTRACTOR
        try:
            production.CONTRACTOR=f['contractor']
            sewn=wip_source.b.two_size_fixture(cur,today+timedelta(days=1),'E05-ACTIVE-HPP',q1=6,q2=4)
        finally:production.CONTRACTOR=old
        assert sewn['day']==day
        native_hpp=lambda sql,args:physical.source.fixture_journal_call(cur,sql,args)
        preview=native_hpp('select erp.preview_attendance_hpp_pool_v1(%s,%s)',(day,day))
        assert(D(str(preview['numerator_amount'])),int(preview['denominator_qty']))==(D(1000),10),preview
        pool=native_hpp('select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s)',(json.dumps(dict(period_start=str(day),period_end=str(day),reason='E05 native immutable sewn10 attendance1000 allocation')),uuid.uuid4()))
        pool=native_hpp('select erp.activate_attendance_hpp_pool_v1(%s,%s,%s,%s)',(pool['pool_id'],'E05 activate native attendance HPP',uuid.uuid4(),pool['row_version']))
        assert pool['status']=='ACTIVE'
        f['physical']=physical.stock_cost(cur)
        def hpp_facts():
            return {t:cur.execute('select md5(coalesce(jsonb_agg(to_jsonb(t)order by to_jsonb(t)::text),\'[]\')::text)from erp.'+t+' t').fetchone()[0]for t in('attendance_hpp_pools','attendance_hpp_pool_sources','attendance_hpp_pool_allocations')}
        hpp=hpp_facts();cost=legacy.journal(cur,f['payroll'],'PAYROLL_ATTENDANCE_ACCRUAL')
        first=act(cur,f);act(cur,f,amount='400.00');assert_balance(cur,f,'1000','0','PAID')
        act(cur,f,'REVERSE_PAYMENT',payment=first['payment_id']);assert_balance(cur,f,'400','600')
        assert hpp_facts()==hpp and legacy.journal(cur,f['payroll'],'PAYROLL_ATTENDANCE_ACCRUAL')==cost
        before=b.boundary.snapshot(cur)
        auth.refused(cur,lambda:act(cur,f,'REVERSE_PAYROLL'),'PAYROLL_CONSUMED_BY_ACTIVE_HPP_POOL')
        assert b.boundary.snapshot(cur)==before and hpp_facts()==hpp
        cancelled=native_hpp('select erp.cancel_attendance_hpp_pool_v1(%s,%s,%s,%s)',(pool['pool_id'],'E05 owning HPP cancellation before payroll inverse',uuid.uuid4(),pool['row_version']))
        assert cancelled['status']=='CANCELLED'
        f['physical']=physical.stock_cost(cur)
        act(cur,f,'REVERSE_PAYROLL');assert_balance(cur,f,'0',None,'REVERSED')
        assert legacy.change({k:D(v)for k,v in f['before_approval'].items()},legacy.gl(cur,f['contractor']))=={}
        return dict(status='PASS',native_attendance1000_sewn10_ACTIVE_pool=True,individual_cash_inverse_preserves_HPP_pool_and_cost=True,whole_payroll_inverse_refused_before_any_cash_while_pool_active=True,native_pool_cancellation_then_whole_inverse_restores_cash_and_cost=True)
    names=[('FIXED_1000_600_400_INVERSE',lifecycle),('DEDUCTION_RESERVATION',deductions),('WHOLE_PARTIAL_INVERSE',lambda:whole(True)),('WHOLE_PAID_INVERSE',lambda:whole(False)),('EXACT_LARGE_CENTS',large),('AMOUNT_CAP',amounts),('CLOSED_FIELDS',fields),('REPLAY',replay),('STALE_REVIEW',stale),('CURRENT_CASH',cash_source),('CURRENT_ACCESS_PRIVATE',access),('LEGACY_BYPASS',legacy_bypass),('IMMUTABLE_APPROVED_SOURCE',immutable),('NATIVE_DATES_TZ',dates),('COMPLETE_30_PAGES',pages),('LEGACY_FULL_HISTORY',legacy_history),('INACTIVE_NOT_PAYABLE',zero)]
    return [('E05_'+name,fn)for name,fn in names]+[('E05_OPENING_ADVANCE_CARRY_INSTALLMENTS',opening_sources),('E05_ZERO_NET_NO_CASH',zero_net),('E05_ACTIVE_HPP_CASH_CORRECTION',active_hpp)]


def races(tools,today):
    def same_uuid():
        with tools.connect()as conn,conn.cursor()as cur:
            f=fixture(cur,today);d=read(cur,f['payroll'])['document'];p=intent(d,'PAY',f,'600.00');conn.commit()
        gate=threading.Barrier(2);key=uuid.uuid4()
        def send():
            with tools.connect()as conn,conn.cursor()as cur:
                gate.wait();r=command(cur,'PAY',p,d['row_version'],key);conn.commit();return r
        with ThreadPoolExecutor(max_workers=2)as pool:
            jobs=[pool.submit(send)for _ in range(2)];rows=[j.result(30)for j in jobs]
        assert rows[0]==rows[1]
        with tools.connect()as conn,conn.cursor()as cur:
            assert_balance(cur,f,'600','400');assert cur.execute('select count(*)from cp7_installment.payments where payroll_id=%s',(f['payroll'],)).fetchone()[0]==1
            assert cur.execute('select count(*)from cp7_installment.requests where request_id=%s',(key,)).fetchone()[0]==1
        return dict(status='PASS',two_real_transactions_same_UUID_one600_cash_effect=True)
    def cap():
        with tools.connect()as conn,conn.cursor()as cur:
            f=fixture(cur,today);d=read(cur,f['payroll'])['document'];p=intent(d,'PAY',f,'600.00');conn.commit()
        gate=threading.Barrier(2)
        def send():
            with tools.connect()as conn,conn.cursor()as cur:
                gate.wait()
                try:r=command(cur,'PAY',p,d['row_version']);conn.commit();return r
                except psycopg.Error as e:conn.rollback();return str(e)
        with ThreadPoolExecutor(max_workers=2)as pool:
            jobs=[pool.submit(send)for _ in range(2)];rows=[j.result(30)for j in jobs]
        assert sum(isinstance(r,dict)for r in rows)==1 and any(isinstance(r,str)and'CP7_INSTALLMENT_REVIEW_CHANGED'in r for r in rows),rows
        with tools.connect()as conn,conn.cursor()as cur:assert_balance(cur,f,'600','400')
        return dict(status='PASS',two_distinct_UUID600_requests_on1000_cannot_overpay=True,observed_native_payroll_lock_serializes_stale_review=True)
    def revoke_cached():
        with tools.connect()as conn,conn.cursor()as cur:
            f=fixture(cur,today);subject,role=legacy.source.procurement.custom(cur,('finance.payroll.view','finance.payroll.pay'));d=read(cur,f['payroll'],subject)['document'];p=intent(d,'PAY',f,'600.00');key=uuid.uuid4();saved=command(cur,'PAY',p,d['row_version'],key,subject);conn.commit()
        with tools.connect()as holder,holder.cursor()as cur:
            cur.execute('select 1 from cp7_installment.requests where actor=%s and request_id=%s for update',(subject,key))
            def send():
                with tools.connect()as conn,conn.cursor()as cur:
                    try:r=command(cur,'PAY',p,d['row_version'],key,subject);conn.commit();return r
                    except psycopg.Error as e:conn.rollback();return str(e)
            with ThreadPoolExecutor(max_workers=1)as pool:
                job=pool.submit(send);waiting=False;deadline=time.monotonic()+8
                while time.monotonic()<deadline:
                    with tools.connect()as conn,conn.cursor()as cur:
                        waiting=cur.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event_type='Lock'and query like 'select public.erp_cp7_save_payroll_installment_v1%')").fetchone()[0]
                    if waiting:break
                    time.sleep(.05)
                try:
                    assert waiting,'Cached request lock was not observed'
                    with tools.connect()as conn,conn.cursor()as cur:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.payroll.pay'",(role,));conn.commit()
                finally:holder.rollback()
                result=job.result(30)
        assert isinstance(result,str)and'CP7_INSTALLMENT_ACCESS_DENIED'in result,result
        with tools.connect()as conn,conn.cursor()as cur:
            assert cur.execute('select response from cp7_installment.requests where request_id=%s',(key,)).fetchone()[0]==saved;assert_balance(cur,f,'600','400')
        return dict(status='PASS',current_revocation_during_observed_request_lock_refuses_cached_outcome=True,original600_commit_preserved=True)
    return [('E05_RACE_SAME_UUID',same_uuid),('E05_RACE_DISTINCT_UUID_CAP',cap),('E05_RACE_CURRENT_REVOKE',revoke_cached)]


def http_cases(http,today):
    def flow():
        owner=http.login('OWNER','e05-installment-owner')
        with http.connect()as conn,conn.cursor()as cur:f=fixture(cur,today);conn.commit()
        r=owner.rpc('erp_cp7_get_payroll_installments_v1',dict(p_query=dict(payroll_id=f['payroll'])));assert r['status']==200,r;d=r['body']['document']
        args=dict(p_action='PAY',p_payload=intent(d,'PAY',f,'600.00'),p_expected=d['row_version'],p_request=str(uuid.uuid4()))
        assert http.anon_rpc('erp_cp7_save_payroll_installment_v1',args)['status']in(401,403)
        r=owner.rpc('erp_cp7_save_payroll_installment_v1',args);assert r['status']==200,r;first=r['body'];assert owner.rpc('erp_cp7_save_payroll_installment_v1',args)['body']==first
        with http.connect()as conn,conn.cursor()as cur:assert_balance(cur,f,'600','400');conn.rollback()
        r=owner.rpc('erp_cp7_get_payroll_installments_v1',dict(p_query=dict(payroll_id=f['payroll'])));assert r['status']==200,r;d=r['body']['document'];last=dict(p_action='PAY',p_payload=intent(d,'PAY',f,'400.00'),p_expected=d['row_version'],p_request=str(uuid.uuid4()))
        r=owner.rpc('erp_cp7_save_payroll_installment_v1',last);assert r['status']==200 and r['body']['native_status']=='PAID',r
        r=owner.rpc('erp_cp7_get_payroll_installments_v1',dict(p_query=dict(payroll_id=f['payroll'])));assert r['status']==200,r;d=r['body']['document'];inverse=dict(p_action='REVERSE_PAYMENT',p_payload=intent(d,'REVERSE_PAYMENT',payment=first['payment_id']),p_expected=d['row_version'],p_request=str(uuid.uuid4()))
        r=owner.rpc('erp_cp7_save_payroll_installment_v1',inverse);assert r['status']==200 and r['body']['native_status']=='APPROVED',r
        with http.connect()as conn,conn.cursor()as cur:
            assert_balance(cur,f,'400','600');cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_save_payroll_installment_v1',args)['status']==403
        assert owner.rpc('erp_cp7_get_payroll_installments_v1',dict(p_query=dict(payroll_id=f['payroll'])))['status']==403
        return dict(status='PASS',actual_Auth_partial600_final400_individual_inverse600=True,native_remaining600_and_cost1000_once=True,exact_replay_and_current_deactivation_before_cached_response=True)
    return [('E05_REAL_AUTH_HTTP',flow)]
