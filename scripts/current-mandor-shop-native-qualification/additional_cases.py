"""Three additional actual Mandor flows; no connection or case on import.

Every transaction uses the installed ERP owner. Native source originals,
money equations and the owning whole-package restoration are still required.
These cases do not claim Auth HTTP, two-backend or browser acceptance.
"""
from decimal import Decimal as D,ROUND_HALF_UP
import json,uuid
import oracle

IDS=(
 'FG_MANDOR_ACTIVE_OFFSET_RETURN_CORRECTION_REFUSE_THEN_LAWFUL_REVERSE_AND_REAL_RETURN_CORRECTION',
 'FG_MANDOR_INSTALLMENT_PARTIAL_FINAL_REOPEN_REPAY_AND_WHOLE_REVERSAL',
 'FG_MANDOR_CURRENT_PERMISSION_REPLAY_REFUSAL_AND_ZERO_NET_NO_CASH',
)


def correction_return(n,cur,today):
    from cases import approved,pay
    f,physical=n.physical(cur,today);sale=n.create_invoice(cur,f);payroll=n.payroll(cur,f,today)
    held=n.allocation(cur,f,payroll,'300000.00');approval=approved(n,cur,f,payroll,today)
    payment=pay(n,cur,f,payroll,today,'300000.00')
    original_sale=f['sale'];n.admin(cur)
    original_items=cur.execute('select coalesce(jsonb_agg(to_jsonb(i)order by i.id),\'[]\'::jsonb)from erp.sales_items i where i.sale_id=%s::uuid',(original_sale,)).fetchone()[0]
    allocation_cost=cur.execute('select a.unit_hpp_snapshot::text from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s::uuid',
        (original_sale,)).fetchall()
    oracle.require(len(allocation_cost)==1,'MANDOR_NATIVE_ONE_ORIGINAL_COST_ALLOCATION')
    original_unit_cost=D(allocation_cost[0][0])
    refused_return=n.refusal(cur,n.return_intent(cur,f),
        'CP7_MANDOR_SHOP_ACTIVE_OFFSET_REVERSE_PAYROLL_BEFORE_SALES_RETURN')
    refused_correction=n.refusal(cur,n.correction_intent(cur,f),
        'CP7_MANDOR_SHOP_ACTIVE_OFFSET_REVERSE_PAYROLL_BEFORE_INVOICE_CORRECTION')
    reversed_payroll,reverse_call=n.payroll_command(cur,f,payroll,'REVERSE')
    reversal=oracle.reversal(approval['before_approval'],payment['after'],n.observe(cur,f,payroll),'300000.00')
    reverse_replay=n.replay(cur,reverse_call,reversed_payroll)
    before=n.observe(cur,f,payroll);before_stock=n.sales.available(cur,f)
    make_return=n.return_intent(cur,f);returned=make_return();return_replay=n.replay(cur,make_return,returned)
    after=n.observe(cur,f,payroll)
    oracle.require(n.sales.available(cur,f)==before_stock+1,'MANDOR_NATIVE_RETURN_RESTORES_ONE_REAL_PCS')
    oracle.require(oracle.money(after['invoice']['net'])==D('225000.00')and oracle.money(after['invoice']['paid'])==0,
        'MANDOR_NATIVE_RETURN_EXACT_UNPAID_NET_225000')
    # The actual original allocation owns COGS; a return must restore that
    # frozen cost, never today's calculated or client-provided HPP.
    n.admin(cur)
    returned_cost=cur.execute('select sum(qty_pcs*unit_hpp_snapshot)::text from erp.sales_return_items where return_id=%s::uuid',
        (returned['return_id'],)).fetchone()[0]
    oracle.require(D(returned_cost)==original_unit_cost and original_unit_cost>0,'MANDOR_NATIVE_RETURN_MUST_USE_ORIGINAL_POSITIVE_HPP')
    cost=original_unit_cost.quantize(D('.01'),rounding=ROUND_HALF_UP)
    expected={n.sales.mapping(cur,'AR_CUSTOMER'):D('-75000.00'),n.sales.mapping(cur,'SALES_REVENUE'):D('75000.00'),
        n.sales.mapping(cur,'FG_INVENTORY'):cost,n.sales.mapping(cur,'COGS'):-cost}
    oracle.require(oracle.deltas(before,after)==expected,'MANDOR_NATIVE_RETURN_EXACT_AR_REVENUE_FG_COGS')
    undo=n.sale_intent(cur,f,'RETURN_REVERSE',dict(return_id=returned['return_id']))
    undone=undo();undo_replay=n.replay(cur,undo,undone)
    restored=n.observe(cur,f,payroll)
    oracle.require(restored['balances']==before['balances']and restored['invoice']==before['invoice']
        and n.sales.available(cur,f)==before_stock,'MANDOR_NATIVE_RETURN_INVERSE_RESTORES_FINANCIAL_AND_PHYSICAL_POSITION')
    # Increase price without changing quantity; this avoids an unrelated
    # overpayment refusal hiding the specific active-offset correction guard.
    correct=n.correction_intent(cur,f);corrected=correct();correction_replay=n.replay(cur,correct,corrected)
    f['sale']=corrected['sale_id'];after_correct=n.observe(cur,f,payroll)
    oracle.require(f['sale']!=original_sale and oracle.money(after_correct['invoice']['net'])==D('300004.00')
        and oracle.money(after_correct['invoice']['paid'])==0,'MANDOR_NATIVE_CORRECTION_NEW_300004_INVOICE')
    oracle.require(n.sales.available(cur,f)==before_stock,'MANDOR_NATIVE_PRICE_CORRECTION_CHANGED_STOCK')
    n.admin(cur)
    oracle.require(cur.execute('select coalesce(jsonb_agg(to_jsonb(i)order by i.id),\'[]\'::jsonb)from erp.sales_items i where i.sale_id=%s::uuid',
        (original_sale,)).fetchone()[0]==original_items,'MANDOR_NATIVE_ORIGINAL_POSTED_ITEMS_REWRITTEN')
    identity=cur.execute('select contractor_id::text,customer_id::text from cp7_mandor_shop.sales where sale_id=%s::uuid',
        (f['sale'],)).fetchone()
    oracle.require(identity==(f['contractor'],f['customer']),'MANDOR_NATIVE_CORRECTED_INVOICE_LOST_MANDOR_IDENTITY')
    oracle.require(oracle.deltas(restored,after_correct)=={n.sales.mapping(cur,'AR_CUSTOMER'):D('4.00'),
        n.sales.mapping(cur,'SALES_REVENUE'):D('-4.00')},'MANDOR_NATIVE_PRICE_CORRECTION_EXACT_FOUR_RUPIAH_ONLY')
    return dict(status='PASS',physical=physical,sale=sale,allocation=held,approval=approval,payment=payment,
        active_return_refusal=refused_return,active_correction_refusal=refused_correction,
        payroll_reversal=reversed_payroll,reversal_equations=reversal,reversal_replay=reverse_replay,
        actual_return=returned,return_replay=return_replay,original_return_HPP=str(cost),return_inverse=undone,
        return_inverse_replay=undo_replay,correction=corrected,correction_replay=correction_replay,
        original_posted_items_unchanged=True,corrected_Mandor_identity_preserved=True)


def installments(n,cur,today):
    from cases import approved,account_ids
    f,physical=n.physical(cur,today);sale=n.create_invoice(cur,f);payroll=n.payroll(cur,f,today)
    held=n.allocation(cur,f,payroll,'300000.00');approval=approved(n,cur,f,payroll,today)
    accounts=account_ids(n,cur,f);before=n.observe(cur,f,payroll)
    first_call=n.installment_intent(cur,f,payroll,'PAY',today=today,amount='600000.00')
    first=first_call();first_after=n.observe(cur,f,payroll)
    first_equations=oracle.installment(before,first_after,'600000.00','0.00',accounts,'APPROVED')
    first_replay=n.replay(cur,first_call,first)
    final_call=n.installment_intent(cur,f,payroll,'PAY',today=today,amount='1100000.00')
    final=final_call();final_after=n.observe(cur,f,payroll)
    final_equations=oracle.installment(first_after,final_after,'1100000.00','300000.00',accounts,'PAID')
    final_replay=n.replay(cur,final_call,final)
    undo=n.installment_intent(cur,f,payroll,'REVERSE_PAYMENT',payment=first['payment_id'])
    reopened=undo();reopened_after=n.observe(cur,f,payroll)
    reopened_equations=oracle.installment(final_after,reopened_after,'-600000.00','-300000.00',accounts,'APPROVED')
    reopened_replay=n.replay(cur,undo,reopened)
    oracle.require(all(x['state']=='RESERVED'for x in reopened_after['allocation_states']),
        'MANDOR_NATIVE_INSTALLMENT_REOPEN_MUST_RETAIN_RESERVATION')
    again=n.installment_intent(cur,f,payroll,'PAY',today=today,amount='600000.00')
    repaid=again();repaid_after=n.observe(cur,f,payroll)
    repaid_equations=oracle.installment(reopened_after,repaid_after,'600000.00','300000.00',accounts,'PAID')
    repaid_replay=n.replay(cur,again,repaid)
    whole=n.installment_intent(cur,f,payroll,'REVERSE_PAYROLL')
    reversed_payroll=whole();end=n.observe(cur,f,payroll)
    reversal=oracle.reversal(approval['before_approval'],repaid_after,end,'300000.00')
    whole_replay=n.replay(cur,whole,reversed_payroll)
    return dict(status='PASS',physical=physical,sale=sale,allocation=held,approval=approval,
        first=dict(reply=first,equations=first_equations,replay=first_replay),
        final=dict(reply=final,equations=final_equations,replay=final_replay),
        reopen=dict(reply=reopened,equations=reopened_equations,replay=reopened_replay),
        repay=dict(reply=repaid,equations=repaid_equations,replay=repaid_replay),
        whole_reverse=dict(reply=reversed_payroll,equations=reversal,replay=whole_replay))


def rights_zero(n,cur,today):
    from cases import approved,pay
    f,physical=n.physical(cur,today);sale=n.create_invoice(cur,f)
    payroll=n.payroll(cur,f,today,gross='300000.00');n.admin(cur)
    actor,role=n.sales.auth.custom_actor(cur)
    for permission in('finance.payroll.view','finance.payroll.approve','finance.ar.view'):
        cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',(role,permission))
    custom=dict(f,actor=actor);key=uuid.uuid4()
    held=n.allocation(cur,custom,payroll,'300000.00',key=key)
    n.admin(cur)
    cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.payroll.approve'",(role,))
    replay=lambda:n.public(cur,'select public.erp_cp7_save_mandor_shop_allocation_v1(%s,%s::jsonb,%s::uuid)',
        ('RESERVE',json.dumps(held['payload']),key),actor)
    revoked_replay=n.refusal(cur,replay,'CP7_MANDOR_SHOP_ACCESS_DENIED',sqlstate='42501')
    read=n.workspace(cur,custom,payroll)
    oracle.require(read['can_change']is False,'MANDOR_NATIVE_CURRENT_READ_ONLY_ALLOCATION')
    n.admin(cur)
    cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ar.view'",(role,))
    revoked_read=n.refusal(cur,lambda:n.workspace(cur,custom,payroll),'CP7_MANDOR_SHOP_ACCESS_DENIED',sqlstate='42501')
    n.admin(cur)
    for permission in('finance.payroll.approve','finance.ar.view','finance.payroll.pay'):
        cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',(role,permission))
    approval=approved(n,cur,custom,payroll,today)
    oracle.require(approval['funding']['ordinary_Native_capital_command']is False,'MANDOR_NATIVE_ZERO_NET_MUST_NOT_FUND_CASH')
    before_pay=n.observe(cur,custom,payroll)
    paid,pay_call=n.payroll_command(cur,custom,payroll,'PAY',today=today)
    after_pay=n.observe(cur,custom,payroll)
    from cases import account_ids
    equation=oracle.payment(before_pay,after_pay,'300000.00',account_ids(n,cur,custom))
    payment=dict(reply=paid,after=after_pay,equations=equation,replay=n.replay(cur,pay_call,paid))
    oracle.require(oracle.money(payment['after']['payroll']['net_payable'])==0,'MANDOR_NATIVE_ZERO_NET_PAYROLL')
    n.admin(cur)
    cash_rows=cur.execute("select count(*)from erp.journal_entries where source_id=%s::uuid and source_type in('PAYROLL_PAYMENT','PAYROLL_INSTALLMENT')",(payroll,)).fetchone()[0]
    oracle.require(cash_rows==0,'MANDOR_NATIVE_ZERO_NET_MUST_NOT_CREATE_CASH_JOURNAL')
    cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ar.view'",(role,))
    revoked_payment_replay=n.refusal(cur,pay_call,'CP7_MANDOR_SHOP_ACCESS_DENIED',sqlstate='42501')
    return dict(status='PASS',physical=physical,sale=sale,allocation=held,current_permission_replay_refusal=revoked_replay,
        current_AR_read_refusal=revoked_read,current_AR_payment_replay_refusal=revoked_payment_replay,
        approval=approval,payment=payment,zero_net_cash_journals=0,
        actual_two_backend_permission_race=False)


FUNCTIONS=(correction_return,installments,rights_zero)
