"""PREPARED actual Native callbacks. Never run on hosted or primary databases.

The owning frozen vendor/package runner must install/reinstall this additive
stage, invoke its actual verifier and preserve full restoration/package gates.
This module creates no connection, Auth service, runner, workflow or test JWT.
"""
from pathlib import Path
from collections import Counter
from datetime import timedelta
from decimal import Decimal as D,ROUND_HALF_UP
import importlib.util,json,uuid
from cp7_attendance_period_choice import composition
import cp7_installment_cases as installments

HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
f=load('S03_prepared_Native_fixture',HERE/'fixtures.py')
admission=load('S03_prepared_parent_admission',HERE/'admission.py')

IDS=(
 'S03_NATIVE_OWNER_FIELDS_READ_FULL_NO_EFFECT',
 'S03_NATIVE_EXPENSE_APPROVAL_ONCE_PAID_E05_REOPEN',
 'S03_NATIVE_TWO_EXACT_PERIODS_CENTS_AND_NATIVE_HPP',
 'S03_NATIVE_P2_PAYROLL_POOL_COEXIST_AND_POLICY_FENCES',
 'S03_NATIVE_OWNING_CANCEL_LATE_OUTPUT_AND_RESTORATION_FLOOR',
 'S03_NATIVE_BOTH_CORRECTIONS_LINKED_INVERSES_NO_RECOGNITION',
 'S03_NATIVE_STALE_REVIEW_UUID_RECOVERY_AND_APPEND_ONLY',
 'S03_NATIVE_CLOSED_SOURCE_OPEN_OUTPUT_AND_CLOSED_CORRECTION',
 'S03_NATIVE_ZERO_OUTPUT_SUCCESSOR_POLICY_RETAINS_OLD_INFO',
 'S03_NATIVE_FINISHED_PO_FG_COGS_COST_AND_CANCEL_EXACT',
 'S03_NATIVE_OLD_ACCRUAL_LATER_BOOK_REOPEN_DATE_FLOOR',
)

def current_hash(cur,pool):return f.native(cur,'select erp._cp3_manifest_sha256(cp7_attendance_choice.pool_manifest_v1(%s))',(pool,))
def source_hash(cur,s):return f.native(cur,'select cp7_attendance_choice.capture_v1(%s,%s,true)->>\'source_binding\'',(s['day'],s['day']))
def accrued(cur,s):
    f.admin(cur);return f.one(cur,"select jsonb_agg(to_jsonb(j)order by j.id)from erp.journal_entries j where source_type='PAYROLL_ATTENDANCE_ACCRUAL'and source_id=%s",(s['payroll'],))
def original_accrual(cur,s):
    """Direct ERP journal/line oracle; no expected finance from facade output."""
    f.admin(cur)
    heads=accrued(cur,s);assert len(heads)==1,('S03_EXPECT_ONE_ORIGINAL_ACCRUAL',heads)
    head=heads[0];assert(head['status'],head['source_type'],head['source_id'],head['economic_date'])==('POSTED','PAYROLL_ATTENDANCE_ACCRUAL',s['payroll'],str(s['day'])),head
    lines=f.one(cur,'select jsonb_agg(to_jsonb(l)order by l.id)from erp.journal_lines l where journal_entry_id=%s',(head['id'],))
    assert len(lines)==2,lines
    wip=str(f.one(cur,"select erp.account_id('WIP')"));payable=str(f.one(cur,"select erp.account_id('CONTRACTOR_PAYABLE')"))
    money={(x['account_id'],D(str(x['debit'])),D(str(x['credit'])))for x in lines}
    assert money=={(wip,f.AMOUNT,D(0)),(payable,D(0),f.AMOUNT)},money
    assert all(x['contractor_id']==s['contractor']and all(x[key]is None for key in('po_id','vendor_id','customer_id','product_id'))for x in lines)
    audit=f.one(cur,"select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]'::jsonb)from erp.audit_logs a where entity_type='payroll_settlements'and entity_id=%s and action='POST'and new_data->>'lifecycle_action'='APPROVE'",(s['payroll'],))
    assert len(audit)==1 and D(str(audit[0]['new_data']['attendance_accrual']))==f.AMOUNT and audit[0]['changed_by']is not None,audit
    return dict(header=head,lines=lines,Native_approval_audit=audit)
def choice_audit(cur,s,result):
    """Exact successful audit lineage, actor/reason and journal/source linkage."""
    f.admin(cur);expected_user=f.one(cur,'select id::text from erp.app_users where auth_user_id=%s and is_active',(s['owner'],))
    request=f.one(cur,'select to_jsonb(r)from cp7_attendance_choice.requests_v1 r where actor=%s and request_id=%s',(s['owner'],result['request_id']))
    assert request['response']==result and request['action']==result['action']and request['app_user']==expected_user,request
    why=request['payload']['reason'];action=result['action'];decision=f.one(cur,'select to_jsonb(d)from cp7_attendance_choice.decisions_v1 d where id=%s',(result['decision_id'],))
    def logs(entity,operation):
        return f.one(cur,"select coalesce(jsonb_agg(to_jsonb(a)order by a.id),'[]'::jsonb)from erp.audit_logs a where entity_type='cp7_attendance_choice'and entity_id=%s and action=%s",(entity,operation))
    posts=[row for row in logs(result['decision_id'],'POST')if row['new_data'].get('request_id')==result['request_id']]
    assert len(posts)==1,posts
    post=posts[0];data=post['new_data']
    assert post['changed_by']==expected_user and post['change_reason']==why
    assert(data['lifecycle_action'],data['event_id'],data['pool_id'],data['original_source_binding'])==(action,result['event_id'],result['pool_id'],decision['source_binding']),data
    if action in('CHOOSE','CORRECT'):
        assert decision['id']==result['event_id']and decision['choice']==request['payload']['choice']
        assert decision['actor']==s['owner']and decision['app_user']==expected_user and decision['reason']==why
        inserted=logs(decision['id'],'INSERT');assert len(inserted)==1,inserted
        row=inserted[0];d=row['new_data']
        assert row['changed_by']==expected_user and row['change_reason']==why
        assert(d['lifecycle_action'],d['choice'],d['source_period_start'],d['source_period_end'],d['source_binding'],d['amount_cents'],d['journal_id'],d['correction_of'])==(
            'CHOOSE',decision['choice'],decision['period_start'],decision['period_end'],decision['source_binding'],str(decision['amount_cents']),decision['journal_id'],decision['correction_of']),d
    inverse_decision=decision['correction_of']if action=='CORRECT'else decision['id']if action=='REVERSE'else None
    if inverse_decision is not None:
        inverse=f.one(cur,'select to_jsonb(r)from cp7_attendance_choice.reversals_v1 r where decision_id=%s',(inverse_decision,))
        rows=logs(inverse_decision,'REVERSE');assert len(rows)==1,rows
        row=rows[0];d=row['new_data']
        assert inverse['actor']==s['owner']and inverse['app_user']==expected_user and inverse['reason']==why
        assert(row['changed_by'],row['change_reason'],d['lifecycle_action'],d['reversal_id'],d['journal_id'])==(expected_user,why,'REVERSE_CHOICE',inverse['id'],inverse['journal_id'])
        assert inverse['journal_id']==result['inverse_journal_id']
        if action=='REVERSE':assert inverse['id']==result['event_id']
    if action in('ALLOCATE','CANCEL_ALLOCATION'):
        allocation=f.one(cur,'select to_jsonb(a)from cp7_attendance_choice.allocations_v1 a where pool_id=%s',(result['pool_id'],))
        assert allocation['decision_id']==decision['id']
        lifecycle=f.hp.lifecycle(cur,result['pool_id'])
        assert lifecycle[:2]==[('CREATE_DRAFT',allocation['reason']),('ACTIVATE',allocation['reason'])],lifecycle
        native_rows=f.one(cur,"select jsonb_agg(to_jsonb(a)order by a.id)from erp.audit_logs a where entity_type='attendance_hpp_pools'and entity_id=%s",(result['pool_id'],))
        assert all(row['changed_by']==expected_user for row in native_rows),native_rows
        if action=='ALLOCATE':
            assert len(lifecycle)==2 and allocation['id']==result['event_id']and allocation['reason']==why
            assert allocation['actor']==s['owner']and allocation['app_user']==expected_user
            assert f.one(cur,'select post_journal_entry_id::text from erp.attendance_hpp_pools where id=%s',(result['pool_id'],))==result['native_result']['journal_entry_id']
        else:
            assert lifecycle==lifecycle[:2]+[('CANCEL_ACTIVE',why)],lifecycle
            inverse=f.one(cur,'select to_jsonb(r)from cp7_attendance_choice.allocation_reversals_v1 r where allocation_id=%s',(allocation['id'],))
            assert(inverse['id'],inverse['actor'],inverse['app_user'],inverse['reason'],inverse['journal_id'])==(result['event_id'],s['owner'],expected_user,why,result['native_result']['reversal_journal_entry_id'])
    return dict(audit_actor=expected_user,reason=why,request_id=result['request_id'],action=action,decision_id=decision['id'],event_id=result['event_id'],successful_audit_links_exact=True)
def choose(cur,s,choice='CARRY'):
    result=f.save(cur,s['owner'],'CHOOSE',f.body(s['day'],choice));choice_audit(cur,s,result);return result
def allocate(cur,s,day):
    result=f.save(cur,s['owner'],'ALLOCATE',f.body(s['day'],output=day));choice_audit(cur,s,result);return result
def pair(cur,today):
    source_day,out=f.quiet_days(cur,today);s=f.source(cur,today,day=source_day)
    g=f.hp.sewn(cur,s['contractor'],'S03-OUTPUT',out);f.admin(cur);choose(cur,s)
    return s,out,g

def cases(cur,today,*,state,evidence):
    # Admission before fixture/writes; source-derived local ABI cannot unlock it.
    proof=admission.admit(composition.predecessor.sources());installed=composition.verify(cur,state)
    evidence['s03_parent_admission']=proof;evidence['s03_actual_installed_boundary']=installed
    def fields():
        s=f.source(cur,today);p=f.body(s['day'],'CARRY');before=f.census(cur)
        ws=f.read(cur,s['owner'],s['day']);r=f.review(cur,s['owner'],'CHOOSE',p)
        assert ws['amount_cents']==r['amount_cents']==str(f.CENTS)and r['source_count']=='1'
        assert ws['current_choice']is None and ws['current_allocation']is None
        assert r['economic_date']is None and r['expense_account']is None and 'context'not in r
        assert f.census(cur)==before
        for action in(None,'','UNKNOWN','CHOOSE '):f.refused(cur,lambda a=action:f.review(cur,s['owner'],a,p),'CP7_S03_ACTION')
        for extra in({'force':True},{'choice':None},{'reason':'x'},{'output_start':str(today)}):
            f.refused(cur,lambda e=extra:f.review(cur,s['owner'],'CHOOSE',dict(p,**e)),'S03')
        admin_actor=f.hp.master.role_actor(cur,'ADMIN')
        f.refused(cur,lambda:f.read(cur,admin_actor,s['day']),'CP7_S03_OWNER_REQUIRED')
        f.refused(cur,lambda:f.read(cur,s['owner'],s['day'],limit=51),'CP7_S03_PAGE')
        special=f.hp.contractor(cur,'S03-SPECIAL-'+uuid.uuid4().hex[:8])
        f.native(cur,'select erp.set_contractor_hpp_policy_v1(%s::jsonb,%s,null)',(json.dumps(dict(contractor_id=special,effective_from=str(s['day']-timedelta(days=1)),is_special=True,attendance_required=True,reason=f.REASON)),uuid.uuid4()))
        f.earned(cur,special,s['day'])
        assert f.review(cur,s['owner'],'CHOOSE',f.body(s['day'],'EXPENSE'))['amount_cents']==str(f.CENTS)
        choose(cur,s,'EXPENSE');f.admin(cur)
        assert D(f.one(cur,"select coalesce(sum(debit-credit),0)from erp.journal_lines where contractor_id=%s and account_id=erp.account_id('WIP')",(special,)))==f.AMOUNT
        return dict(status='PASS',read_preview_full_business_rows_and_sequences_equal=True,current_OWNER_only=True,Native_special_Afui_policy_source_excluded=True,excluded_WIP_retained=str(f.AMOUNT),local_ABI_substituted=False)
    def expense_payment():
        s=f.source(cur,today);original=accrued(cur,s);original_rows=original_accrual(cur,s);binding=source_hash(cur,s)
        made=choose(cur,s,'EXPENSE');f.admin(cur)
        decision=f.one(cur,'select to_jsonb(d)from cp7_attendance_choice.decisions_v1 d where id=%s',(made['decision_id'],))
        j=f.one(cur,'select to_jsonb(j)from erp.journal_entries j where id=%s',(decision['journal_id'],))
        rows=cur.execute('select account_id,po_id,contractor_id,debit,credit,description,vendor_id,customer_id,product_id from erp.journal_lines where journal_entry_id=%s',(j['id'],)).fetchall()
        wip=f.one(cur,"select erp.account_id('WIP')");expense=f.one(cur,"select erp.account_id('OTHER_EXPENSE')")
        assert len(rows)==2 and sum(x[3]for x in rows)==sum(x[4]for x in rows)==f.AMOUNT
        assert all(x[1]is None and str(x[2])==s['contractor']and x[6:]==(None,None,None)for x in rows)
        assert {(x[0],x[3],x[4])for x in rows}=={(expense,f.AMOUNT,D(0)),(wip,D(0),f.AMOUNT)}
        assert(j['source_type'],j['source_id'],j['economic_date'])==('CP7_ATTENDANCE_PERIOD_EXPENSE',made['decision_id'],str(s['day']))
        bank=installments.legacy.cash(cur,str(f.AMOUNT));cash=f.one(cur,'select cp7_installment.cash(%s)',(bank,))
        pay=dict(payroll=s['payroll'],cash=cash,payment_date=str(today))
        first=installments.act(cur,pay,amount='600.00',subject=s['owner']);installments.act(cur,pay,amount='400.03',subject=s['owner'])
        assert accrued(cur,s)==original and original_accrual(cur,s)==original_rows and source_hash(cur,s)==binding
        assert installments.read(cur,s['payroll'],subject=s['owner'])['document']['native_status']=='PAID'
        # Full E05, not a fabricated payment/context fixture: no initial cash
        # inverse or sequence allocation may precede this claimed-source refusal.
        f.refused(cur,lambda:installments.act(cur,pay,'REVERSE_PAYROLL',subject=s['owner']),'CP7_S03_PAYROLL_CLAIMED')
        installments.act(cur,pay,'REVERSE_PAYMENT',payment=first['payment_id'],subject=s['owner'])
        assert installments.read(cur,s['payroll'],subject=s['owner'])['document']['native_status']=='APPROVED'
        assert accrued(cur,s)==original and original_accrual(cur,s)==original_rows and source_hash(cur,s)==binding
        inverse=f.save(cur,s['owner'],'REVERSE',f.body(s['day']));choice_audit(cur,s,inverse)
        installments.act(cur,pay,'REVERSE_PAYROLL',subject=s['owner'])
        assert installments.read(cur,s['payroll'],subject=s['owner'])['document']['native_status']=='REVERSED'
        return dict(status='PASS',exact_unassigned_WIP_to_expense=str(f.AMOUNT),APPROVED_recognition_once=True,PAID_and_individual_inverse_settlement_only=True,held_whole_inverse_full_census_unchanged=True,owning_release_allows_whole_inverse=True)
    def exact_carry():
        s,out,g=pair(cur,today);f.hp.sewn(cur,s['contractor'],'S03-OUTPUT-SECOND',out)
        original=accrued(cur,s);made=allocate(cur,s,out);oracle=f.assert_pool(cur,s,made,out)
        assert accrued(cur,s)==original
        assert oracle['denominator']==20 and sorted(x['cents']for x in oracle['by_event'].values())==[50001,50002]
        actual=f.read(cur,s['owner'],s['day']);assert actual['current_allocation']['output_start']==str(out)
        assert actual['current_choice']['choice']=='CARRY'
        return dict(status='PASS',source_period=str(s['day']),output_period=str(out),amount_cents=str(f.CENTS),exact_20_output_floor_cents=[50001,50002],Native_validator='PASS',widened_source_period=False)
    def coexist():
        s,out,g=pair(cur,today)
        excluded=f.hp.contractor(cur,'S03-EXCLUDED-'+uuid.uuid4().hex[:8]);f.hp.sewn(cur,excluded,'S03-EXCLUDED',out)
        later=f.hp.contractor(cur,'S03-DESTINATION-'+uuid.uuid4().hex[:8]);f.hp.policy(cur,later,out);f.hp.sewn(cur,later,'S03-DESTINATION',out)
        made=allocate(cur,s,out);before=current_hash(cur,made['pool_id'])
        f.earned(cur,s['contractor'],out,D('20.02'))
        normal=f.native(cur,'select erp.create_attendance_hpp_pool_v1(%s::jsonb,%s)',(json.dumps(dict(period_start=str(out),period_end=str(out),reason=f.REASON)),uuid.uuid4()))
        f.native(cur,'select erp.activate_attendance_hpp_pool_v1(%s,%s,%s,%s)',(normal['pool_id'],f.REASON,uuid.uuid4(),normal['row_version']))
        assert current_hash(cur,made['pool_id'])==before;f.assert_pool(cur,s,made,out)
        f.refused(cur,lambda:f.native(cur,'select erp.set_contractor_hpp_policy_v1(%s::jsonb,%s,null)',(json.dumps(dict(contractor_id=excluded,effective_from=str(out),is_special=False,attendance_required=True,reason=f.REASON)),uuid.uuid4())),'CP7_S03_ACTIVE_CARRY_POLICY_CHANGED')
        f.admin(cur);destination_policy=f.one(cur,'select id from erp.contractor_hpp_policy_versions where contractor_id=%s order by effective_from desc limit 1',(later,))
        f.native(cur,'select erp.set_contractor_hpp_policy_v1(%s::jsonb,%s,%s)',(json.dumps(dict(contractor_id=later,effective_from=str(today),is_special=False,attendance_required=True,reason=f.REASON)),uuid.uuid4(),destination_policy))
        assert current_hash(cur,made['pool_id'])==before;f.assert_pool(cur,s,made,out)
        f.admin(cur);own=f.one(cur,'select id from erp.contractor_hpp_policy_versions where contractor_id=%s order by effective_from desc limit 1',(s['contractor'],))
        f.refused(cur,lambda:f.native(cur,'select erp.set_contractor_hpp_policy_v1(%s::jsonb,%s,%s)',(json.dumps(dict(contractor_id=s['contractor'],effective_from=str(today),is_special=False,attendance_required=True,reason=f.REASON)),uuid.uuid4(),own)),'CP7_S03_HELD_POLICY_CHANGED')
        return dict(status='PASS',normal_P2_payroll_and_ordinary_pool_coexist=True,old_P1_carry_identity_current=True,excluded_P2_new_eligibility_refused_full_census=True,harmless_future_destination_only_policy_allowed=True,held_source_future_policy_refused_full_census=True)
    def cancel_output():
        s,out,g=pair(cur,today);pending=f.pending_work(cur,s['contractor'],out);made=allocate(cur,s,out)
        f.refused(cur,lambda:f.native(cur,'select erp.cancel_attendance_hpp_pool_v1(%s,%s,%s,%s)',(made['pool_id'],f.REASON,uuid.uuid4(),2)),'CP7_S03_OWNING_CARRY_CANCEL_REQUIRED')
        f.refused(cur,lambda:f.native(cur,'select erp.record_sewing_terminal_v1(%s::jsonb,%s)',(json.dumps(dict(work_completion_id=pending['work'],qty_pcs=10,reason=f.REASON)),uuid.uuid4())),'CP7_S03_ACTIVE_CARRY_OUTPUT_LOCKED')
        cancelled=f.save(cur,s['owner'],'CANCEL_ALLOCATION',f.body(s['day']));choice_audit(cur,s,cancelled);f.admin(cur)
        inverse=f.one(cur,'select journal_id from cp7_attendance_choice.allocation_reversals_v1 where allocation_id=%s',(made['event_id'],))
        assert f.one(cur,'select economic_date from erp.journal_entries where id=%s',(inverse,))==today
        assert f.read(cur,s['owner'],s['day'])['current_allocation']is None
        f.refused(cur,lambda:f.review(cur,s['owner'],'ALLOCATE',f.body(s['day'],output=out)),'CP7_S03_ALLOCATION_BEFORE_WIP_AVAILABLE')
        return dict(status='PASS',direct_cancel_before_row_wait_refused=True,new_output_before_DML_refused=True,owning_cancel_metadata_closed=True,Native_inverse_day=str(today),pre_restoration_reuse_refused_full_census=True)
    def corrections():
        s=f.source(cur,today);original=accrued(cur,s);first=choose(cur,s)
        exp=f.save(cur,s['owner'],'CORRECT',f.body(s['day'],'EXPENSE'))
        choice_audit(cur,s,exp)
        carried=f.save(cur,s['owner'],'CORRECT',f.body(s['day'],'CARRY'));choice_audit(cur,s,carried);f.admin(cur)
        assert f.one(cur,'select correction_of::text from cp7_attendance_choice.decisions_v1 where id=%s',(exp['decision_id'],))==first['decision_id']
        assert f.one(cur,'select correction_of::text from cp7_attendance_choice.decisions_v1 where id=%s',(carried['decision_id'],))==exp['decision_id']
        assert accrued(cur,s)==original
        f.refused(cur,lambda:f.review(cur,s['owner'],'CORRECT',f.body(s['day'],'EXPENSE')),'CP7_S03_')
        f.sewn(cur,s['contractor'],'S03-RESTORED-TODAY',today)
        restored=allocate(cur,s,today);f.assert_pool(cur,s,restored,today)
        cancelled=f.save(cur,s['owner'],'CANCEL_ALLOCATION',f.body(s['day']));choice_audit(cur,s,cancelled)
        reversed=f.save(cur,s['owner'],'REVERSE',f.body(s['day']));choice_audit(cur,s,reversed);f.admin(cur)
        assert f.one(cur,'select id::text from cp7_attendance_choice.reversals_v1 where decision_id=%s',(carried['decision_id'],))==reversed['event_id']
        return dict(status='PASS',CARRY_to_EXPENSE_to_CARRY_linked=True,Native_expense_inverse_retained_own_dates=True,pre_restoration_expense_refused=True,lawful_actual_current_day_output_carry_proved=True,payroll_accrual_immutable=True,inverse_receipt_exact=True)
    def stale_replay():
        s=f.source(cur,today);p=f.body(s['day'],'CARRY');r=f.review(cur,s['owner'],'CHOOSE',p)
        other=f.hp.contractor(cur,'S03-OTHER-'+uuid.uuid4().hex[:8]);f.hp.policy(cur,other,s['day']-timedelta(days=1));f.earned(cur,other,s['day'],D('11.01'))
        f.refused(cur,lambda:f.command(cur,s['owner'],'CHOOSE',dict(p,review_token=r['review_token'])),'CP7_S03_STALE_REVIEW')
        # A valid unapproved source already exists before the period is held.
        # Never fabricate an APPROVED row to exercise this admission boundary.
        pending_contractor=f.hp.contractor(cur,'S03-PENDING-'+uuid.uuid4().hex[:8]);f.hp.policy(cur,pending_contractor,s['day']-timedelta(days=1))
        pending=f.earned(cur,pending_contractor,s['day'],D('13.02'),approve=False);settlement=f.hp.cp17().s
        pending_doc=settlement.doc(cur,pending);assert pending_doc['status']=='CALCULATED',pending_doc
        current=f.review(cur,s['owner'],'CHOOSE',p);intent=dict(p,review_token=current['review_token']);key=uuid.uuid4()
        made=f.command(cur,s['owner'],'CHOOSE',intent,key);choice_audit(cur,s,made);before=f.census(cur)
        f.refused(cur,lambda:settlement.act(cur,'APPROVE',pending_doc),'CP7_S03_PERIOD_CLAIMED')
        f.refused(cur,lambda:f.native(cur,'select erp.approve_payroll(%s)',(pending,)),'CP7_S03_PERIOD_CLAIMED')
        assert f.command(cur,s['owner'],'CHOOSE',intent,key)==made and f.census(cur)==before
        f.refused(cur,lambda:f.command(cur,s['owner'],'CHOOSE',dict(intent,reason=f.REASON+' changed'),key),'CP7_S03_REQUEST_CHANGED')
        inverse=f.save(cur,s['owner'],'REVERSE',f.body(s['day']));choice_audit(cur,s,inverse);before=f.census(cur)
        assert f.command(cur,s['owner'],'CHOOSE',intent,key)==made and f.census(cur)==before
        assert f.read(cur,s['owner'],s['day'])['current_choice']is None
        settlement.act(cur,'APPROVE',pending_doc);f.admin(cur)
        assert settlement.doc(cur,pending)['status']=='APPROVED'
        assert f.one(cur,"select count(*)from erp.journal_entries where source_type='PAYROLL_ATTENDANCE_ACCRUAL'and source_id=%s",(pending,))==1
        assert D(f.one(cur,"select sum(l.debit)from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.source_type='PAYROLL_ATTENDANCE_ACCRUAL'and j.source_id=%s and l.account_id=erp.account_id('WIP')",(pending,)))==D('13.02')
        f.refused(cur,lambda:cur.execute('update cp7_attendance_choice.decisions_v1 set reason=reason'),'CP7_S03_APPEND_ONLY')
        return dict(status='PASS',actual_new_payroll_invalidates_preview=True,preexisting_CALCULATED_public_and_direct_APPROVE_refuse_full_rows_sequences=True,owning_release_allows_once_only_approval=True,exact_UUID_replay_no_effect=True,historical_receipt_not_current_choice=True,append_only=True)
    def closed_periods():
        s,out,g=pair(cur,today);f.hp.set_closed(cur,s['day'])
        f.refused(cur,lambda:f.review(cur,s['owner'],'REVERSE',f.body(s['day'])),'CP7_S03_PERIOD_CLOSED')
        made=allocate(cur,s,out);f.assert_pool(cur,s,made,out)
        f.hp.set_closed(cur,out);f.refused(cur,lambda:f.review(cur,s['owner'],'CANCEL_ALLOCATION',f.body(s['day'])),'CP7_S03_PERIOD_CLOSED')
        f.hp.set_closed(cur,s['day']);cancelled=f.save(cur,s['owner'],'CANCEL_ALLOCATION',f.body(s['day']));choice_audit(cur,s,cancelled)
        return dict(status='PASS',closed_P1_does_not_fake_later_P2_date=True,closed_affected_output_inverse_requires_reopen=True,refusals_full_rows_sequences_unchanged=True)
    def blockers():
        s=f.source(cur,today)
        def rows(name):
            f.admin(cur);return cur.execute('select family,code,severity,scope,impact_date,reference,reason from '+name+'(%s)',(today,)).fetchall()
        old=rows('cp7_hpp_close.blockers_v1');new=rows('cp7_attendance_choice.blockers_v1')
        mine=lambda r:r[5].get('period_start')==str(s['day'])and r[5].get('period_end')==str(s['day'])
        assert len([r for r in old if r[1]=='ATTENDANCE_POOL_ZERO_OUTPUT'and r[2]=='INFO'and mine(r)])==1
        assert len([r for r in new if r[1]=='ATTENDANCE_ZERO_CHOICE_REQUIRED'and r[2]=='POLICY'and mine(r)])==1
        norm=lambda rs:Counter(json.dumps(list(r),default=str,sort_keys=True)for r in rs if r[1]!='ATTENDANCE_POOL_ZERO_OUTPUT'and not r[1].startswith('ATTENDANCE_ZERO_'))
        assert norm(old)==norm(new);choose(cur,s)
        assert len([r for r in rows('cp7_attendance_choice.blockers_v1')if r[1]=='ATTENDANCE_ZERO_CARRY_WAITING'and r[2]=='INFO'and mine(r)])==1
        return dict(status='PASS',old_OW07_INFO_original_not_relabelled=True,successor_D17_19C_POLICY_required=True,unrelated_blockers_byte_equal=True,explicit_CARRY_explains_waiting_WIP=True)
    def finished():
        c=f.hp.cp17();m=f.hp.contractor(cur,'S03-FINISHED-'+uuid.uuid4().hex[:10]);prod=c.bd.chain.production;old=prod.CONTRACTOR
        try:prod.CONTRACTOR=m;g=c.finish_fixture(cur,today,label='S03-FINISHED')
        finally:prod.CONTRACTOR=old
        f.admin(cur);output=f.one(cur,"select min(erp._cp3_business_date(physical_at))from erp.sewing_terminal_events where po_id=%s and event_kind='SELESAI_DIJAHIT'",(g['po'],))
        source_day=f.quiet_days(cur,today,1,before=output)[0];s=f.source(cur,today,day=source_day,contractor=m)
        c.bd.sell(cur,g,g['product'],4,16);c.finish_command(cur,c.finish_workspace(cur,g['po']),reason=f.REASON)
        f.admin(cur);assert c.po_state(cur,g['po'])['status']=='FINISHED'and c.po_wip_balance(cur,g['po'])==0
        choose(cur,s);before_cost=D(c.po_hpp(cur,g['po'])[0])
        physical=lambda:f.one(cur,"select coalesce(jsonb_agg(to_jsonb(m)order by m.id),'[]'::jsonb)from erp.fg_stock_movements m where lot_id=%s",(g['lot'],))
        original_physical=physical()
        def gl():
            f.admin(cur);return {key:D(f.one(cur,'select coalesce(sum(debit-credit),0)from erp.journal_lines where po_id=%s and account_id=erp.account_id(%s)',(g['po'],key)))for key in('WIP','FG_INVENTORY','COGS')}
        before_gl=gl();made=allocate(cur,s,output);oracle=f.assert_pool(cur,s,made,output)
        expected=D(sum(x['cents']for x in oracle['by_event'].values()if x['po']==g['po']))/100
        assert expected>0 and D(c.po_hpp(cur,g['po'])[0])-before_cost==expected
        after_gl=gl();delta={key:after_gl[key]-before_gl[key]for key in before_gl}
        cogs=(expected*D(4)/10).quantize(D('.01'),rounding=ROUND_HALF_UP)
        assert delta=={'WIP':D(0),'FG_INVENTORY':expected-cogs,'COGS':cogs},delta
        assert physical()==original_physical and c.po_wip_balance(cur,g['po'])==0
        cancelled=f.save(cur,s['owner'],'CANCEL_ALLOCATION',f.body(source_day));choice_audit(cur,s,cancelled);f.admin(cur)
        assert D(c.po_hpp(cur,g['po'])[0])==before_cost and gl()==before_gl
        assert physical()==original_physical and c.po_wip_balance(cur,g['po'])==0
        return dict(status='PASS',actual_finished_PO=g['po'],own_attendance_cost=str(expected),sold_qty=4,produced_qty=10,
            expected_COGS_delta=str(cogs),expected_FG_delta=str(expected-cogs),finished_PO_WIP_zero_after_both=True,posted_physical_rows_immutable=True,Native_cancel_exact_cost_inverse=True)
    def source_book_floor():
        source_day,out=f.quiet_days(cur,today);m=f.hp.contractor(cur,'S03-BOOK-'+uuid.uuid4().hex[:8]);f.hp.policy(cur,m,source_day-timedelta(days=1))
        payroll=f.earned(cur,m,source_day,approve=False)
        f.hp.set_closed(cur,today-timedelta(days=1))
        # Retained owning Native approval is the valid writer; no approved
        # status or shifted journal is fabricated or direct-seeded.
        f.native(cur,'select erp.approve_payroll(%s)',(payroll,));f.admin(cur)
        j=f.one(cur,"select to_jsonb(j)from erp.journal_entries j where source_type='PAYROLL_ATTENDANCE_ACCRUAL'and source_id=%s and status='POSTED'",(payroll,))
        assert j['economic_date']==str(source_day)and j['transaction_date']==str(today),j
        f.hp.set_closed(cur,source_day-timedelta(days=1))
        capture=f.native(cur,'select cp7_attendance_choice.capture_v1(%s,%s,true)',(source_day,source_day))
        assert capture['amount_cents']==str(f.CENTS)
        s=dict(day=source_day,contractor=m,payroll=payroll,owner=f.hp.owner(cur),capture=capture)
        f.refused(cur,lambda:f.review(cur,s['owner'],'CHOOSE',f.body(source_day,'EXPENSE')),'CP7_S03_EXPENSE_BEFORE_WIP_AVAILABLE')
        choose(cur,s);f.hp.sewn(cur,m,'S03-OLD-OUTPUT-BOOK-FLOOR',out)
        f.refused(cur,lambda:f.review(cur,s['owner'],'ALLOCATE',f.body(source_day,output=out)),'CP7_S03_ALLOCATION_BEFORE_WIP_AVAILABLE')
        f.sewn(cur,m,'S03-LAWFUL-OUTPUT-BOOK-FLOOR',today);made=allocate(cur,s,today);f.assert_pool(cur,s,made,today)
        return dict(status='PASS',valid_Native_APPROVED_economic=str(source_day),original_accrual_book=str(today),legitimate_reopen_does_not_rewrite_source=True,both_old_dated_consumptions_refused_full_census=True,current_day_carry_uses_original_book_floor=True)
    return list(zip(IDS,(fields,expense_payment,exact_carry,coexist,cancel_output,corrections,stale_replay,closed_periods,blockers,finished,source_book_floor)))
