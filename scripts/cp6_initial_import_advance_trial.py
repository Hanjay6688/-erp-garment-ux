"""Cash advance lifecycle cases for the combined, rolled-back AO/AP runtime.

The oracle is money conservation: historical cash is unchanged, only the net
payroll cash leaves the bank, and repayment/reversal restores exact balances.
"""
from datetime import timedelta
from decimal import Decimal as D
import uuid
from cp6_initial_import_receipt_trial import rpc


def ledger(cur):
    # The inherited receipt oracle observes only inventory/supplier accounts.
    # Advances must compare every account, including cash, payroll and income.
    return dict(cur.execute("select l.account_id::text,sum(l.debit-l.credit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED') group by l.account_id having sum(l.debit-l.credit)<>0 order by l.account_id").fetchall())


def fixture(a,cur,today,source_kind='CONTRACTOR_CASH_ADVANCE'):
    batch,code,row=a.financial_batch(cur,today,balance_type='CONTRACTOR_RECEIVABLE')
    row['source_kind']=source_kind
    a.upload(cur,batch,'CHART_ACCOUNT',[dict(account_code=code,account_name='Advance bank',account_type='ASSET',report_group='CURRENT_ASSETS',normal_balance='DEBIT')])
    a.upload(cur,batch,'CASH_ACCOUNT',[dict(cash_account_code=code,cash_account_name='Advance bank',coa_account_code=code,account_kind='BANK')])
    a.upload(cur,batch,'OPENING_BALANCE_ITEM',[row,dict(balance_type='CASH_BANK',cash_account_code=code,amount='100.00',control_key='CASH')])
    a.upload(cur,batch,'OPENING_CONTROL',[dict(control_key='AR',balance_type='CONTRACTOR_RECEIVABLE',amount='67.25'),dict(control_key='CASH',balance_type='CASH_BANK',amount='100.00')])
    before=ledger(cur)
    assert a.invoke(cur,'VALIDATE',batch)['error_rows']==0,a.read(cur,batch)
    assert ledger(cur)==before
    assert a.invoke(cur,'FINALIZE',batch)['status']=='POSTED',a.read(cur,batch)
    balance,contractor,cash=cur.execute('select b.id,b.contractor_id,c.id from erp.initial_import_financial_sources s join erp.opening_subledger_balances b on b.opening_item_id=s.opening_item_id cross join erp.cash_accounts c where s.batch_id=%s and c.cash_account_code=%s',(batch,code)).fetchone()
    return dict(batch=batch,code=code,balance=balance,contractor=contractor,cash=cash)


def payroll(cur,f,today,earnings='20',days=0):
    day=today-timedelta(days=days)
    return cur.execute("insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end,manual_adjustment,payment_date,payment_cash_account_id) values(%s,%s,%s,%s,%s,%s,%s) returning id",('ADV-'+uuid.uuid4().hex,f['contractor'],day,day,earnings,today,f['cash'])).fetchone()[0]


def allocation(a,cur,f,p,amount,key=None,payload=None):
    payload=payload or dict(batch_id=f['batch'],expected_revision=a.read(cur,f['batch'])['batch']['revision'],
        balance_id=f['balance'],payroll_id=p,amount=amount,
        expected_payroll_version=str(cur.execute('select row_version from erp.payroll_settlements where id=%s',(p,)).fetchone()[0]))
    return a.call(cur,'ALLOCATE_CASH_ADVANCE',payload,key),payload


def state(a,cur,f):
    s=a.read(cur,f['batch'])['batch']['cash_advances'][0]
    receivable=cur.execute("select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.status in('POSTED','REVERSED') and l.contractor_id=%s and l.account_id=erp.account_id('CONTRACTOR_RECEIVABLE')",(f['contractor'],)).fetchone()[0]
    assert receivable==D(s['remaining_amount']),(receivable,s)
    return s


def bank(cur,f):
    value=cur.execute("select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id join erp.cash_accounts c on c.coa_account_id=l.account_id where c.id=%s and j.status in('POSTED','REVERSED')",(f['cash'],)).fetchone()[0]
    reported=cur.execute("select amount from erp.get_balance_sheet(erp._cp3_business_date(statement_timestamp())) where account_code=%s",(f['code'],)).fetchone()
    assert reported==(value,),('Bank report does not match ledger',value,reported)
    return value


def truth(cur):
    names=['V2620M_OPENING_SUBLEDGER_STATE','V2620M_PAYMENT_SOURCE_JOURNAL_MISMATCH','V2620M_ORPHAN_PAYMENT_JOURNAL',
           'V2620U_JOURNAL_REVERSAL_BUSINESS_DATE','V2620Y_OPENING_SETTLEMENT_BUSINESS_DATE',
           'AP_CASH_ADVANCE_CAPACITY','AP_CASH_ADVANCE_SOURCE','AP_CASH_ADVANCE_PAYROLL_JOURNAL']
    rows=cur.execute('select check_name,issue_count from erp.run_v267_financial_truth_checks() where check_name=any(%s)',(names,)).fetchall()
    assert len(rows)==len(names) and all(v==0 for _,v in rows),rows
    return dict(rows)


def repay(cur,f,today,amount='10'):
    return cur.execute("insert into erp.opening_subledger_settlements(settlement_number,balance_id,amount,cash_account_id,physical_at,status,created_by) values(%s,%s,%s,%s,%s,'DRAFT',erp.current_app_user_id()) returning id",('ADV-REPAY-'+uuid.uuid4().hex,f['balance'],amount,f['cash'],str(today)+'T10:00:00+07:00')).fetchone()[0]


def lifecycle(a,cur,today,zone,closed=False):
    cur.execute("set local timezone to 'Pacific/Kiritimati'" if zone!='UTC' else "set local timezone to 'UTC'")
    f=fixture(a,cur,today);assert bank(cur,f)==100
    s=state(a,cur,f)
    assert (s['original_amount'],s['settled_before_cutover'],s['remaining_amount'])==('100.00','32.75','67.25'),s
    p=payroll(cur,f,today);before=ledger(cur);key=uuid.uuid4()
    result,payload=allocation(a,cur,f,p,'12.75',key)
    boundary=a.actors.boundary(cur)
    assert a.call(cur,'ALLOCATE_CASH_ADVANCE',payload,key)==result and a.actors.boundary(cur)==boundary
    assert ledger(cur)==before,'Draft allocation posted money'
    s=state(a,cur,f);assert (s['remaining_amount'],s['reserved_amount'],s['available_amount'])==('67.25','12.75','54.50'),s
    if closed:
        # Real payment date may be closed; canonical posting uses today's open
        # transaction date without changing the economic payment date.
        cur.execute('update erp.payroll_settlements set payment_date=%s where id=%s',(today-timedelta(days=1),p))
        rpc(a,cur,'close_accounting_through',today-timedelta(days=1),'Advance economic date closed')
    rpc(a,cur,'approve_payroll',p);truth(cur)
    assert state(a,cur,f)['settled_amount']=='0.00' and bank(cur,f)==100
    rpc(a,cur,'post_payroll_payment',p);truth(cur)
    assert bank(cur,f)==D('92.75') and state(a,cur,f)['remaining_amount']=='54.50'
    expected=today-timedelta(days=1) if closed else today
    rows=cur.execute("select economic_date,transaction_date from erp.journal_entries where source_id=%s and source_type in('PAYROLL_PAYMENT','PAYROLL_CASH_ADVANCE_DEDUCTION')",(p,)).fetchall()
    assert len(rows)==2 and all(e==expected and t==today for e,t in rows),rows
    payment=repay(cur,f,today)
    rpc(a,cur,'post_opening_subledger_settlement',payment);truth(cur)
    assert bank(cur,f)==D('102.75') and state(a,cur,f)['remaining_amount']=='44.50'
    p2=payroll(cur,f,today,'44.50',days=1)
    allocation(a,cur,f,p2,'44.50');rpc(a,cur,'approve_payroll',p2);rpc(a,cur,'post_payroll_payment',p2);truth(cur)
    assert bank(cur,f)==D('102.75') and state(a,cur,f)['remaining_amount']=='0.00'
    assert not cur.execute("select 1 from erp.journal_entries where source_id=%s and source_type='PAYROLL_PAYMENT'",(p2,)).fetchone()
    rpc(a,cur,'reverse_paid_payroll',p2,'Restore carried cash advance');truth(cur)
    assert state(a,cur,f)['remaining_amount']=='44.50'
    rpc(a,cur,'reverse_opening_subledger_settlement',payment,'Restore returned cash advance');truth(cur)
    assert bank(cur,f)==D('92.75') and state(a,cur,f)['remaining_amount']=='54.50'
    rpc(a,cur,'reverse_paid_payroll',p,'Restore first cash advance payroll');truth(cur)
    assert bank(cur,f)==100 and state(a,cur,f)['remaining_amount']=='67.25'
    assert ledger(cur)==before,'Payroll/refund/reversal did not restore ledger'
    return dict(status='PASS',zone=zone,closed=closed,opening='67.25',old_repaid='32.75',payroll_deduction='12.75',payroll_cash='7.25',cash_return='10.00',carry='44.50',final_remaining='67.25',replay_exact=True,truth=truth(cur))


def reservation_release(a,cur,today,approved):
    f=fixture(a,cur,today);p=payroll(cur,f,today,'100');p2=payroll(cur,f,today,'100',days=1)
    before=ledger(cur);allocation(a,cur,f,p,'50');allocation(a,cur,f,p2,'17.25')
    assert ledger(cur)==before and state(a,cur,f)['available_amount']=='0.00'
    a.inherited.refused(cur,lambda:allocation(a,cur,f,p2,'17.26'))
    payment=repay(cur,f,today,'0.01');a.inherited.refused(cur,lambda:rpc(a,cur,'post_opening_subledger_settlement',payment))
    if approved:
        rpc(a,cur,'approve_payroll',p)
        a.inherited.refused(cur,lambda:allocation(a,cur,f,p,'0'))
        rpc(a,cur,'cancel_unpaid_payroll',p,'Release approved advance reservation')
    else:allocation(a,cur,f,p,'0')
    assert state(a,cur,f)['available_amount']=='50.00';truth(cur)
    assert bank(cur,f)==100
    if not approved:assert ledger(cur)==before
    return dict(status='PASS',approved=approved,reserved_amount='17.25',available_amount='50.00',oversubscription_and_repay_refused=True)


def refusal(a,cur,today,kind):
    f=fixture(a,cur,today,source_kind='BALANCE' if kind=='GENERAL_RECEIVABLE' else 'CONTRACTOR_CASH_ADVANCE')
    p=payroll(cur,f,today)
    if kind=='WRONG_CONTRACTOR':
        other=cur.execute("insert into erp.contractors(contractor_code,contractor_name) values(%s,'Other advance contractor') returning id",('OTHER-'+uuid.uuid4().hex[:8],)).fetchone()[0]
        cur.execute('update erp.payroll_settlements set contractor_id=%s where id=%s',(other,p))
    before=ledger(cur)
    if kind=='STALE':
        _,payload=allocation(a,cur,f,p,'5')
        a.inherited.refused(cur,lambda:allocation(a,cur,f,p,'5',payload=payload))
    elif kind=='STALE_EARNINGS':
        allocation(a,cur,f,p,'12.75');cur.execute('update erp.payroll_settlements set manual_adjustment=1 where id=%s',(p,))
        a.inherited.refused(cur,lambda:rpc(a,cur,'approve_payroll',p))
    elif kind=='DATE_BEFORE_CUTOVER':
        allocation(a,cur,f,p,'12.75');cur.execute('update erp.payroll_settlements set payment_date=%s where id=%s',(today-timedelta(days=2),p))
        a.inherited.refused(cur,lambda:rpc(a,cur,'approve_payroll',p))
    elif kind=='CORRECTION_BELOW_RESERVED':
        allocation(a,cur,f,p,'12.75')
        item=cur.execute('select opening_item_id from erp.opening_subledger_balances where id=%s',(f['balance'],)).fetchone()[0]
        a.inherited.refused(cur,lambda:rpc(a,cur,'post_opening_financial_correction',item,D('10'),'Cannot erase reserved source',today))
    elif kind=='DIRECT_DML':
        def direct():
            a.admin(cur);cur.execute('grant usage on schema erp to authenticated');a.ordinary(cur)
            cur.execute("insert into erp.payroll_deductions(payroll_id,deduction_type,opening_cash_advance_balance_id,amount) values(%s,'CASH_ADVANCE',%s,1.001)",(p,f['balance']))
        a.inherited.refused(cur,direct);a.admin(cur)
    else:
        amount={'EXCESS_PRECISION':'1.001','NEGATIVE':'-1','EARNINGS_CAP':'20.01'}.get(kind,'5')
        a.inherited.refused(cur,lambda:allocation(a,cur,f,p,amount))
    assert ledger(cur)==before and bank(cur,f)==100
    truth(cur)
    return dict(status='PASS',kind=kind,ledger_unchanged=True)


def mixed_deductions(a,cur,today):
    f=fixture(a,cur,today);p=payroll(cur,f,today)
    cur.execute("insert into erp.payroll_deductions(payroll_id,deduction_type,amount,notes) values(%s,'PENALTY',2.25,'Distinct penalty fixture')",(p,))
    allocation(a,cur,f,p,'12.75');before=ledger(cur)
    rpc(a,cur,'approve_payroll',p);rpc(a,cur,'post_payroll_payment',p);truth(cur)
    after=ledger(cur)
    income=str(cur.execute("select erp.account_id('OTHER_INCOME')").fetchone()[0])
    assert after.get(income,D('0'))-before.get(income,D('0'))==D('-2.25')
    assert bank(cur,f)==95 and state(a,cur,f)['remaining_amount']=='54.50'
    rpc(a,cur,'reverse_paid_payroll',p,'Restore mixed deductions')
    assert ledger(cur)==before and bank(cur,f)==100;truth(cur)
    return dict(status='PASS',advance='12.75',other_income='2.25',cash='5.00',reversal_exact=True)


def source_refusal(a,cur,today,kind):
    batch,code,row=a.financial_batch(cur,today,balance_type='CONTRACTOR_RECEIVABLE' if kind!='WRONG_BALANCE_TYPE' else 'CUSTOMER_RECEIVABLE')
    row['source_kind']='UNKNOWN_ADVANCE' if kind=='UNKNOWN_KIND' else 'CONTRACTOR_CASH_ADVANCE'
    if kind=='SUMMARY':
        for k in ['document_number','document_date','due_date','original_amount','settled_before_cutover']:row.pop(k,None)
    a.upload(cur,batch,'OPENING_BALANCE_ITEM',[row]);before=ledger(cur)
    result=a.invoke(cur,'FINALIZE',batch)
    assert result['status']=='DRAFT' and result['error_rows']>0 and ledger(cur)==before,result
    assert any('source_kind' in e for r in a.read(cur,batch)['batch']['rows'] for e in r['errors'])
    return dict(status='PASS',kind=kind,source_error_persisted=True,ledger_unchanged=True)


def correction_and_drift(a,cur,today):
    f=fixture(a,cur,today);p=payroll(cur,f,today,'100');allocation(a,cur,f,p,'12.75')
    item=cur.execute('select opening_item_id from erp.opening_subledger_balances where id=%s',(f['balance'],)).fetchone()[0]
    correction=rpc(a,cur,'post_opening_financial_correction',item,D('80.25'),'Verified corrected opening advance',today)
    s=state(a,cur,f)
    assert s['opening_amount']=='80.25' and s['original_amount']=='100.00' and s['settled_before_cutover']=='32.75'
    truth(cur)
    rpc(a,cur,'reverse_opening_financial_correction',correction,'Restore original opening advance');truth(cur)
    assert state(a,cur,f)['opening_amount']=='67.25'
    cur.execute('savepoint advance_detector')
    cur.execute('update erp.opening_subledger_balances set settled_amount=1 where id=%s',(f['balance'],))
    findings=cur.execute("select issue_count from erp.run_v267_financial_truth_checks() where check_name='V2620M_OPENING_SUBLEDGER_STATE'").fetchone()[0]
    assert findings==1,findings
    cur.execute('rollback to savepoint advance_detector');cur.execute('release savepoint advance_detector');truth(cur)
    return dict(status='PASS',correction='80.25',restored='67.25',original_document_immutable=True,unexplained_settlement_detected=True)


def cases(a,cur,today):
    result=[('CASH_ADVANCE_LIFECYCLE:'+z+':'+str(c),lambda z=z,c=c:lifecycle(a,cur,today,z,c)) for z,c in [('UTC',False),('Pacific/Kiritimati',False),('UTC',True)]]
    result += [('CASH_ADVANCE_RESERVATION:'+str(v),lambda v=v:reservation_release(a,cur,today,v)) for v in (False,True)]
    result += [('CASH_ADVANCE_REFUSAL:'+k,lambda k=k:refusal(a,cur,today,k)) for k in ('GENERAL_RECEIVABLE','WRONG_CONTRACTOR','STALE','STALE_EARNINGS','DATE_BEFORE_CUTOVER','CORRECTION_BELOW_RESERVED','EXCESS_PRECISION','NEGATIVE','EARNINGS_CAP','DIRECT_DML')]
    result += [('CASH_ADVANCE_MIXED_DEDUCTIONS',lambda:mixed_deductions(a,cur,today))]
    result += [('CASH_ADVANCE_SOURCE_REFUSAL:'+k,lambda k=k:source_refusal(a,cur,today,k)) for k in ('UNKNOWN_KIND','SUMMARY','WRONG_BALANCE_TYPE')]
    result += [('CASH_ADVANCE_CORRECTION_DRIFT',lambda:correction_and_drift(a,cur,today))]
    return result
