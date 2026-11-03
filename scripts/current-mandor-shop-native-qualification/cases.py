"""Nine new actual Native scenarios; no case is dispatched on import.

SQL Native evidence is separate from the still pending independent two-backend,
Auth HTTP and browser acceptance. No retained financial scenario is rerun here.
"""
from decimal import Decimal as D,ROUND_HALF_UP
import json,uuid
import oracle,additional_cases

IDS=(
 'FG_MANDOR_FUTURE_WEEK_DRAFT_RESERVE_RELEASE_THEN_ELIGIBLE_WEEK_300000_OFFSET_2000000_GROSS_1700000_NET_REPLAY',
 'FG_MANDOR_PARTIAL100000_REMAINDER200000_ON_SECOND_MANUALLY_SELECTED_WEEK',
 'FG_MANDOR_EXPLICIT_RELEASE_AND_UNPAID_CANCELLATION_RELEASE_ALLOCATION_WITHOUT_AR_PAYMENT',
 'FG_MANDOR_NATIVE_PAID_REVERSAL_REOPENS_SAME_INVOICE_AND_RESTORES_PREAPPROVAL_BOOKS',
 'FG_MANDOR_CURRENT_CAPACITY_WRONG_MANDOR_AND_STALE_REVIEW_REFUSE_WITHOUT_EFFECT',
 'FG_MANDOR_ORDINARY_STORE_NATIVE_CREATE_POST_COGS_AND_STOCK_REGRESSION',
)+additional_cases.IDS


def account_ids(n,cur,f):
    n.admin(cur)
    return dict(CONTRACTOR_PAYABLE=n.sales.mapping(cur,'CONTRACTOR_PAYABLE'),AR_CUSTOMER=n.sales.mapping(cur,'AR_CUSTOMER'),
        CASH=cur.execute('select coa_account_id::text from erp.cash_accounts where id=%s::uuid',(f['accessory']['cash'],)).fetchone()[0])


def approved(n,cur,f,payroll,today):
    prepared,_=n.payroll_command(cur,f,payroll,'PREPARE')
    funding=n.fund_payroll(cur,f,payroll,today)
    before=n.observe(cur,f,payroll)
    reply,call=n.payroll_command(cur,f,payroll,'APPROVE')
    replay=n.replay(cur,call,reply)
    return dict(prepared=prepared,funding=funding,approved=reply,replay=replay,before_approval=before)


def pay(n,cur,f,payroll,today,amount):
    before=n.observe(cur,f,payroll)
    reply,call=n.payroll_command(cur,f,payroll,'PAY',today=today)
    after=n.observe(cur,f,payroll)
    proof=oracle.payment(before,after,amount,account_ids(n,cur,f))
    replay=n.replay(cur,call,reply)
    return dict(reply=reply,before=before,after=after,equations=proof,replay=replay)


def selected_week(n,cur,today):
    f,physical=n.physical(cur,today);sale=n.create_invoice(cur,f)
    future=n.payroll(cur,f,today,back=-7)
    before=n.observe(cur,f,future);future_allocation=n.allocation(cur,f,future,'300000.00');held=n.observe(cur,f,future)
    future_draft=oracle.reservation(before,held,'300000.00')
    oracle.require(oracle.money(held['payroll']['net_payable'])==D('1700000.00'),'MANDOR_NATIVE_FUTURE_DRAFT_OWNER_1700000_NET')
    released=n.allocation(cur,f,future,None,release=future_allocation['reply']['allocation_id'])
    after_release=n.observe(cur,f,future);future_release=oracle.released(held,after_release,'300000.00')
    cancelled,cancel_call=n.payroll_command(cur,f,future,'CANCEL');future_after=n.observe(cur,f,future)
    oracle.require(future_after['payroll']['status']=='REVERSED','MANDOR_NATIVE_FUTURE_UNPAID_DRAFT_CANCELLED')
    payroll=n.payroll(cur,f,today,back=7)
    eligible_before=n.observe(cur,f,payroll);allocation=n.allocation(cur,f,payroll,'300000.00');eligible_held=n.observe(cur,f,payroll)
    eligible_draft=oracle.reservation(eligible_before,eligible_held,'300000.00');approval=approved(n,cur,f,payroll,today)
    payment=pay(n,cur,f,payroll,today,'300000.00')
    oracle.require(oracle.money(payment['after']['invoice']['outstanding'])==0,'MANDOR_NATIVE_FULL_SAME_INVOICE_SETTLEMENT')
    oracle.require(oracle.money(payment['after']['payroll']['net_payable'])==D('1700000.00'),'MANDOR_NATIVE_OWNER_1700000_NET')
    return dict(status='PASS',physical=physical,sale=sale,future_week=dict(payroll_id=future,allocation=future_allocation,
        reservation_equations=future_draft,release=released,release_equations=future_release,cancel=cancelled,
        cancel_replay=n.replay(cur,cancel_call,cancelled),paid=False),eligible_week=dict(payroll_id=payroll,
        allocation=allocation,reservation_equations=eligible_draft,approval=approval,payment=payment),
        manual_adjustment_fixture_uses_unchanged_Native_expense_rules=True,actual_Auth_HTTP_or_browser_credit=False)


def partial(n,cur,today):
    f,physical=n.physical(cur,today);sale=n.create_invoice(cur,f)
    first=n.payroll(cur,f,today,gross='1000000.00',back=14)
    held=n.allocation(cur,f,first,'100000.00');approval1=approved(n,cur,f,first,today);paid1=pay(n,cur,f,first,today,'100000.00')
    oracle.require(oracle.money(paid1['after']['invoice']['outstanding'])==D('200000.00'),'MANDOR_NATIVE_FIRST_PARTIAL_BALANCE')
    second=n.payroll(cur,f,today,back=7)
    workspace=n.workspace(cur,f,second);card=next(x for x in workspace['cards']if x['sale_id']==f['sale'])
    oracle.require(oracle.money(card['available_to_reserve'])==D('200000.00'),'MANDOR_NATIVE_REMAINDER_AVAILABLE_ON_NEXT_WEEK')
    oracle.require(any(x['allocation']['payroll_id']==first for x in card['allocations']),'MANDOR_NATIVE_CARD_MUST_SHOW_PREVIOUS_PAYROLL')
    held2=n.allocation(cur,f,second,'200000.00');approval2=approved(n,cur,f,second,today);paid2=pay(n,cur,f,second,today,'200000.00')
    oracle.require(oracle.money(paid2['after']['invoice']['outstanding'])==0,'MANDOR_NATIVE_REMAINDER_SETTLES_ORIGINAL_INVOICE')
    return dict(status='PASS',physical=physical,sale=sale,first=dict(allocation=held,approval=approval1,payment=paid1),
        second=dict(card=card,allocation=held2,approval=approval2,payment=paid2),same_invoice_id=f['sale'])


def release_cancel(n,cur,today):
    f,physical=n.physical(cur,today);sale=n.create_invoice(cur,f);payroll=n.payroll(cur,f,today)
    held=n.allocation(cur,f,payroll,'100000.00');before=n.observe(cur,f,payroll)
    released=n.allocation(cur,f,payroll,None,release=held['reply']['allocation_id']);after=n.observe(cur,f,payroll)
    explicit=oracle.released(before,after,'100000.00')
    held2=n.allocation(cur,f,payroll,'200000.00');before_cancel=n.observe(cur,f,payroll)
    reply,call=n.payroll_command(cur,f,payroll,'CANCEL');after_cancel=n.observe(cur,f,payroll)
    automatic=oracle.released(before_cancel,after_cancel,'200000.00')
    oracle.require(after_cancel['payroll']['status']=='REVERSED','MANDOR_NATIVE_UNPAID_CANCELLATION_STATUS')
    oracle.require(all(x['state']=='RELEASED'for x in after_cancel['allocation_states']),'MANDOR_NATIVE_CANCEL_MUST_RELEASE_ALL_ALLOCATIONS')
    return dict(status='PASS',physical=physical,sale=sale,reserve=held,release=released,explicit_release=explicit,
        second_reserve=held2,cancel=reply,automatic_release=automatic,cancel_replay=n.replay(cur,call,reply))


def paid_reverse(n,cur,today):
    f,physical=n.physical(cur,today);sale=n.create_invoice(cur,f);payroll=n.payroll(cur,f,today)
    held=n.allocation(cur,f,payroll,'300000.00');approval=approved(n,cur,f,payroll,today);payment=pay(n,cur,f,payroll,today,'300000.00')
    reply,call=n.payroll_command(cur,f,payroll,'REVERSE');after=n.observe(cur,f,payroll)
    reversal=oracle.reversal(approval['before_approval'],payment['after'],after,'300000.00')
    return dict(status='PASS',physical=physical,sale=sale,allocation=held,approval=approval,payment=payment,reversed=reply,
        after=after,reversal_equations=reversal,reversal_replay=n.replay(cur,call,reply))


def refusals(n,cur,today):
    f,physical=n.physical(cur,today);sale=n.create_invoice(cur,f);payroll=n.payroll(cur,f,today)
    cap=n.refusal(cur,lambda:n.allocation(cur,f,payroll,'300000.01'),'CP7_MANDOR_SHOP_INVOICE_CAPACITY_CHANGED')
    before=n.workspace(cur,f,payroll);card=next(x for x in before['cards']if x['sale_id']==f['sale'])
    held=n.allocation(cur,f,payroll,'100000.00')
    stale_payload=dict(contract_version='cp7.mandor-shop-allocation-command.v1',payroll_id=payroll,sale_id=f['sale'],review_token=card['review_token'],amount='100000.00')
    stale=n.refusal(cur,lambda:n.public(cur,'select public.erp_cp7_save_mandor_shop_allocation_v1(%s,%s::jsonb,%s::uuid)',
        ('RESERVE',json.dumps(stale_payload),uuid.uuid4()),f['actor']),'CP7_MANDOR_SHOP_REVIEW_CHANGED')
    n.admin(cur);other=n.modules.bc.fixture(cur,today,purchase=False,zones=False)
    other_f=dict(f,contractor=other['mandor'],accessory=other)
    wrong_payroll=n.payroll(cur,other_f,today)
    wrong_payload=dict(stale_payload,payroll_id=wrong_payroll)
    wrong=n.refusal(cur,lambda:n.public(cur,'select public.erp_cp7_save_mandor_shop_allocation_v1(%s,%s::jsonb,%s::uuid)',
        ('RESERVE',json.dumps(wrong_payload),uuid.uuid4()),f['actor']),'CP7_MANDOR_SHOP_WRONG_MANDOR')
    return dict(status='PASS',physical=physical,sale=sale,capacity_refusal=cap,held=held,stale_refusal=stale,wrong_mandor_refusal=wrong,
        actual_two_backend_race_or_current_rights_credit=False)


def ordinary_store(n,cur,today):
    f,physical=n.physical(cur,today);n.admin(cur)
    f['customer']=str(n.modules.bd.chain.base.create_customer(cur,f['tag']))
    before=n.sales.accounts(cur);value=D(str(n.modules.bd.lot_value(cur,f['lot'])))
    payload=n.draft.payload(f,qty='4',price='75000',discount='0');key=uuid.uuid4()
    def create():return n.sales.command(cur,'CREATE',payload,None,key,f['actor'])
    made=create();f['sale']=made['sale_id'];create_replay=n.replay(cur,create,made)
    review,version=n.sale_review(cur,f);request=uuid.uuid4()
    def post():return n.sales.command(cur,'POST',review,version,request,f['actor'])
    posted=post();post_replay=n.replay(cur,post,posted)
    cogs=(value*D(4)/D(10)).quantize(D('.01'),rounding=ROUND_HALF_UP)
    expected={n.sales.mapping(cur,'AR_CUSTOMER'):D('300000'),n.sales.mapping(cur,'SALES_REVENUE'):D('-300000'),
        n.sales.mapping(cur,'FG_INVENTORY'):-cogs,n.sales.mapping(cur,'COGS'):cogs}
    oracle.require(n.sales.delta(before,n.sales.accounts(cur))==expected,'MANDOR_NATIVE_ORDINARY_STORE_FINANCIAL_ENGINE_REGRESSION')
    oracle.require(n.sales.available(cur,f)==6,'MANDOR_NATIVE_ORDINARY_STORE_EXACT_FOUR_PCS')
    oracle.require(cur.execute('select count(*)from cp7_mandor_shop.sales where sale_id=%s::uuid',(f['sale'],)).fetchone()==(0,),'MANDOR_NATIVE_STORE_MISCLASSIFIED_AS_MANDOR')
    return dict(status='PASS',physical=physical,created=made,create_replay=create_replay,posted=posted,post_replay=post_replay,
        gross='300000.00',COGS=str(cogs),remaining_available=6,Mandor_identity_created=False)


def cases(native,cur,today):
    def run(fn):
        native.admin(cur);before=native.modules.bc.findings(cur)
        result=fn(native,cur,today)
        native.admin(cur)
        # Exercise actual deferred request FKs and financial constraint triggers
        # before the strict runner rolls back its case savepoint.
        cur.execute('set constraints all immediate')
        after=native.modules.bc.findings(cur)
        new=native.modules.bc.new_findings(before,after)
        oracle.require(not new,'MANDOR_NATIVE_NEW_FINANCIAL_INTEGRITY_FINDINGS:'+str(new))
        return dict(result,financial_findings_before=before,financial_findings_after=after,
            new_financial_findings={},actual_Auth_HTTP_cases=0,actual_browser_cases=0,actual_two_session_cases=0,
            owning_full_restore_and_all_five_required=True,production_go=False,independent_acceptance=False)
    return [(name,lambda fn=fn:run(fn))for name,fn in zip(IDS,
        (selected_week,partial,release_cancel,paid_reverse,refusals,ordinary_store)+additional_cases.FUNCTIONS,strict=True)]
