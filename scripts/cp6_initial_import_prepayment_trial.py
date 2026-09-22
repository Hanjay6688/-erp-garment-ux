"""Money-conservation oracles for imported advances and native settlement paths."""
from datetime import timedelta
from decimal import Decimal as D
import uuid
from cp6_initial_import_receipt_trial import rpc
from cp6_initial_import_advance_trial import ledger
import cp6_initial_import_receipt_trial as receipts
import cp6_v2620h_adversarial_regression as sales
import cp6_v2620f_final_runtime_regression as laundry


def fixture(a,cur,today,kind,party=None,bill='67.25',finish=True):
    code='PP'+uuid.uuid4().hex[:12]
    batch=a.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(today-timedelta(days=1))))['batch_id']
    table,field,name,entity={'SUPPLIER':('suppliers','supplier_code','supplier_name','SUPPLIER'),
      'CUSTOMER':('customers','customer_code','customer_name','CUSTOMER'),
      'VENDOR':('laundry_vendors','vendor_code','vendor_name','LAUNDRY_VENDOR')}[kind]
    party_code=cur.execute('select '+field+' from erp.'+table+' where id=%s',(party,)).fetchone()[0] if party else code
    if not party:a.upload(cur,batch,entity,[{field:party_code,name:'Uang muka '+kind}])
    advance_code=code+'A'
    a.upload(cur,batch,'CHART_ACCOUNT',[
      dict(account_code=code,account_name='Prepayment bank',account_type='ASSET',report_group='CURRENT_ASSETS',normal_balance='DEBIT'),
      dict(account_code=advance_code,account_name='Dedicated advance',account_type='LIABILITY' if kind=='CUSTOMER' else 'ASSET',
        report_group='CURRENT_LIABILITIES' if kind=='CUSTOMER' else 'CURRENT_ASSETS',normal_balance='CREDIT' if kind=='CUSTOMER' else 'DEBIT')])
    a.upload(cur,batch,'CASH_ACCOUNT',[dict(cash_account_code=code,cash_account_name='Advance bank',coa_account_code=code,account_kind='BANK')])
    rows=[dict(balance_type='CASH_BANK',cash_account_code=code,amount='100.00',control_key='BANK')]
    controls=[dict(control_key='BANK',balance_type='CASH_BANK',amount='100.00'),dict(control_key='ADV',balance_type=kind+'_ADVANCE',amount='67.25')]
    if bill is not None:
        balance_type=kind+('_RECEIVABLE' if kind=='CUSTOMER' else '_PAYABLE')
        rows.append(dict(balance_type=balance_type,**{field:party_code},document_number='BILL-'+code,document_date=str(today-timedelta(days=45)),
          original_amount='100',settled_before_cutover=str(100-D(bill)),amount=bill,control_key='BILL'))
        controls.append(dict(control_key='BILL',balance_type=balance_type,amount=bill))
    a.upload(cur,batch,'OPENING_BALANCE_ITEM',rows)
    row=dict(party_type=kind,party_code=party_code,coa_account_code=advance_code,document_number='DEP-'+code,
      document_date=str(today-timedelta(days=60)),original_amount='100',settled_before_cutover='32.75',amount='67.25',control_key='ADV')
    a.upload(cur,batch,'OPENING_ADVANCE',[row]);a.upload(cur,batch,'OPENING_CONTROL',controls)
    f=dict(batch=batch,code=code,kind=kind,party_code=party_code,row=row,controls=controls)
    if not finish:return f
    before=ledger(cur);checked=a.invoke(cur,'VALIDATE',batch)
    assert checked['error_rows']==0,a.read(cur,batch)
    assert ledger(cur)==before,'Advance preview posted money'
    assert a.invoke(cur,'FINALIZE',batch)['status']=='POSTED',a.read(cur,batch)
    source=cur.execute('select id,party_id,coa_account_id from erp.initial_import_prepayments where batch_id=%s',(batch,)).fetchone()
    f.update(advance=source[0],party=source[1],account=source[2],cash=cur.execute('select id from erp.cash_accounts where cash_account_code=%s',(code,)).fetchone()[0])
    return f


def state(a,cur,f):return a.read(cur,f['batch'])['batch']['prepayments'][0]


def manage(a,cur,f,op,today,key=None,payload=None,**extra):
    payload=payload or dict(batch_id=f['batch'],expected_revision=a.read(cur,f['batch'])['batch']['revision'],advance_id=f['advance'],
      operation=op,effective_date=str(today),reason='Verified '+op,**extra)
    return a.call(cur,'PREPAYMENT',payload,key),payload


def bank(cur,f):
    amount=cur.execute('select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.cash_accounts c on c.coa_account_id=l.account_id join erp.journal_entries j on j.id=l.journal_entry_id where c.id=%s and j.status in(\'POSTED\',\'REVERSED\')',(f['cash'],)).fetchone()[0]
    assert cur.execute('select amount from erp.get_balance_sheet(erp._cp3_business_date(statement_timestamp())) where account_code=%s',(f['code'],)).fetchone()==(amount,)
    return amount


def truth(cur):
    names=['AP_PREPAYMENT_CAPACITY','AP_PREPAYMENT_PAYMENT_SOURCE','AP_PREPAYMENT_PAYMENT_JOURNAL','AP_PREPAYMENT_OPENING_JOURNAL',
      'AP_PREPAYMENT_EVENT_JOURNAL','AP_PREPAYMENT_GL_SUBLEDGER','V2620M_OPENING_SUBLEDGER_STATE','V2620M_PAYMENT_SOURCE_JOURNAL_MISMATCH',
      'V2620M_ORPHAN_PAYMENT_JOURNAL','V2620Y_OPENING_SETTLEMENT_BUSINESS_DATE','V2620U_JOURNAL_REVERSAL_BUSINESS_DATE',
      'V2620S_SUPPLIER_PAYMENT_BUSINESS_DATE','V2620Y_VENDOR_PAYMENT_BUSINESS_DATE','V2620Y_SALES_PAYMENT_BUSINESS_DATE']
    rows=cur.execute('select check_name,issue_count from erp.run_v267_financial_truth_checks() where check_name=any(%s)',(names,)).fetchall()
    assert len(rows)==len(names) and all(n==0 for _,n in rows),rows
    rows2=cur.execute("select check_name,issue_count from erp.run_v268_financial_report_checks() where check_name in('V2620I_SALES_PAYMENT_JOURNAL_LINEAGE_MISMATCH','V2620J_SALES_PAYMENT_IMMUTABLE_FACT_MISMATCH')").fetchall()
    assert len(rows2)==2 and all(n==0 for _,n in rows2),rows2
    return dict(rows+rows2)


def opening_lifecycle(a,cur,today,kind,closed):
    cur.execute("set local timezone to 'Pacific/Kiritimati'" if closed else "set local timezone to 'UTC'")
    f=fixture(a,cur,today,kind);before=ledger(cur);s=state(a,cur,f)
    assert (s['original_amount'],s['settled_before_cutover'],s['remaining_amount'])==('100.00','32.75','67.25')
    target=s['targets'][0]['id'];date=today-timedelta(days=1) if closed else today
    if closed:rpc(a,cur,'close_accounting_through',date,'Close advance economic date')
    key=uuid.uuid4();result,payload=manage(a,cur,f,'APPLY',date,key=key,target_id=target,amount='12.75')
    boundary=a.actors.boundary(cur);assert a.call(cur,'PREPAYMENT',payload,key)==result and a.actors.boundary(cur)==boundary
    s=state(a,cur,f);first=s['payments'][0]['id'];assert bank(cur,f)==100 and s['remaining_amount']=='54.50';truth(cur)
    manage(a,cur,f,'REFUND',date,amount='10',cash_account_id=f['cash']);s=state(a,cur,f);event=s['events'][0]['id']
    assert bank(cur,f)==(90 if kind=='CUSTOMER' else 110) and s['remaining_amount']=='44.50';truth(cur)
    manage(a,cur,f,'APPLY',date,target_id=target,amount='44.50');s=state(a,cur,f);second=next(p['id'] for p in s['payments'] if p['id']!=first)
    assert s['remaining_amount']=='0.00' and s['targets'][0]['remaining_amount']=='10.00';truth(cur)
    pay=cur.execute("insert into erp.opening_subledger_settlements(balance_id,settlement_number,physical_at,amount,cash_account_id,created_by) values(%s,%s,%s,10,%s,erp.current_app_user_id()) returning id",(target,'CASH-'+uuid.uuid4().hex,str(date)+'T12:00:00+07:00',f['cash'])).fetchone()[0]
    rpc(a,cur,'post_opening_subledger_settlement',pay);assert bank(cur,f)==100 and state(a,cur,f)['targets']==[];truth(cur)
    dates=cur.execute("select j.economic_date,j.transaction_date from erp.journal_entries j join erp.initial_import_prepayment_payments l on l.payment_id=j.source_id where l.advance_id=%s",(f['advance'],)).fetchall()
    assert len(dates)==2 and all(e==date and t==today for e,t in dates),dates
    rpc(a,cur,'reverse_opening_subledger_settlement',pay,'Restore cash settlement');truth(cur)
    manage(a,cur,f,'REVERSE_PAYMENT',today,payment_id=second);truth(cur)
    manage(a,cur,f,'REVERSE_EVENT',today,event_id=event);truth(cur)
    manage(a,cur,f,'REVERSE_PAYMENT',today,payment_id=first);truth(cur)
    assert ledger(cur)==before and bank(cur,f)==100 and state(a,cur,f)['remaining_amount']=='67.25'
    return dict(status='PASS',party_type=kind,closed=closed,opening='67.25',advance_applications=['12.75','44.50'],refund='10',cash_settlement='10',ledger_restored=True,replay_exact=True,truth=truth(cur))


def native_document(a,cur,today,kind):
    a.admin(cur)
    if kind=='SUPPLIER':
        rf=receipts.fixture(a,cur,today);rr=receipts.finalize(a,cur,rf)
        invoice=receipts.invoice(a,cur,today,rr,20,'5');receipts.post_invoice(a,cur,invoice)
        party,target=rr['supplier_id'],rr['purchase_id'];reverse_invoice=lambda:rpc(a,cur,'reverse_material_supplier_invoice',invoice['supplier_invoice_id'],'Restore invoice')
    elif kind=='CUSTOMER':
        sf=sales.opening_sale(cur,'PP-'+uuid.uuid4().hex[:8]);party,target=sf['customer'],sf['sale']
        reverse_invoice=None
    else:
        vf=a.base.fresh(cur,'b');delivery=a.base.post_delivery(cur,vf,a.base.BASE_PROCESS,'2026-09-01T11:00:00Z')
        _,_,line=a.base.post_receipt(cur,str(delivery['delivery_id']),a.base.BASE_PROCESS,'2026-09-02T11:00:00Z')
        target=laundry.finalize_laundry_invoice(cur,line,D('10'));party=a.base.VENDOR
        reverse_invoice=lambda:rpc(a,cur,'reverse_vendor_invoice',target,'Restore vendor invoice')
    f=fixture(a,cur,today,kind,party=party,bill=None);before=ledger(cur)
    selected=next(t for t in state(a,cur,f)['targets'] if t['id']==str(target));assert selected['remaining_amount']=='100.00',selected
    manage(a,cur,f,'APPLY',today,target_id=target,amount='67.25');s=state(a,cur,f);payment=s['payments'][0]['id']
    assert bank(cur,f)==100 and s['remaining_amount']=='0.00';truth(cur)
    if reverse_invoice:a.inherited.refused(cur,reverse_invoice)
    table,fk,rpc_name={'SUPPLIER':('supplier_payments','purchase_id','supplier_payment'),'CUSTOMER':('sales_payments','sale_id','sales_payment'),'VENDOR':('vendor_payments','vendor_invoice_id','vendor_payment')}[kind]
    cash=cur.execute('insert into erp.'+table+'('+fk+',payment_number,payment_date,amount,cash_account_id) values(%s,%s,%s,32.75,%s) returning id',(target,'CASH-'+uuid.uuid4().hex,str(today)+'T12:00:00+07:00',f['cash'])).fetchone()[0]
    rpc(a,cur,'post_'+rpc_name,cash);truth(cur)
    assert bank(cur,f)==(D('132.75') if kind=='CUSTOMER' else D('67.25'))
    over=cur.execute('insert into erp.'+table+'('+fk+',payment_number,payment_date,amount,cash_account_id) values(%s,%s,%s,0.01,%s) returning id',(target,'OVER-'+uuid.uuid4().hex,str(today)+'T12:00:00+07:00',f['cash'])).fetchone()[0]
    a.inherited.refused(cur,lambda:rpc(a,cur,'post_'+rpc_name,over))
    rpc(a,cur,'reverse_'+rpc_name,cash,'Restore ordinary cash payment');truth(cur)
    manage(a,cur,f,'REVERSE_PAYMENT',today,payment_id=payment);truth(cur)
    assert ledger(cur)==before and bank(cur,f)==100 and state(a,cur,f)['remaining_amount']=='67.25'
    return dict(status='PASS',party_type=kind,native_invoice='100.00',noncash='67.25',cash='32.75',original_cash_path_preserved=True,exact_reversal=True)


def corrections(a,cur,today,kind):
    f=fixture(a,cur,today,kind,bill='100');before=ledger(cur)
    manage(a,cur,f,'CORRECT',today,amount='80.25');s=state(a,cur,f);event=s['events'][0]['id']
    assert (s['opening_amount'],s['original_amount'],s['settled_before_cutover'])==('80.25','100.00','32.75');truth(cur)
    target=s['targets'][0]['id'];manage(a,cur,f,'APPLY',today,amount='75',target_id=target);p=state(a,cur,f)['payments'][0]['id']
    a.inherited.refused(cur,lambda:manage(a,cur,f,'REVERSE_EVENT',today,event_id=event))
    a.inherited.refused(cur,lambda:manage(a,cur,f,'CORRECT',today,amount='74.99'))
    manage(a,cur,f,'REVERSE_PAYMENT',today,payment_id=p)
    manage(a,cur,f,'REVERSE_EVENT',today,event_id=event);truth(cur)
    assert ledger(cur)==before and state(a,cur,f)['opening_amount']=='67.25'
    a.inherited.refused(cur,lambda:cur.execute('update erp.initial_import_prepayments set amount=68 where id=%s',(f['advance'],)))
    return dict(status='PASS',party_type=kind,correction='80.25',consumed_correction_reversal_refused=True,original_immutable=True,restored='67.25')


def refusal(a,cur,today,kind):
    f=fixture(a,cur,today,'SUPPLIER',bill='20' if kind=='EXCEEDS_INVOICE' else '100')
    target=state(a,cur,f)['targets'][0]['id'];payload=None
    if kind=='WRONG_PARTY':target=state(a,cur,fixture(a,cur,today,'SUPPLIER'))['targets'][0]['id']
    elif kind=='STALE':_,payload=manage(a,cur,f,'APPLY',today,amount='1',target_id=target)
    before=ledger(cur)
    if kind=='GENERIC_REVERSAL':
        journal=cur.execute("select id from erp.journal_entries where source_type='OPENING_PREPAYMENT' and source_id=%s",(f['advance'],)).fetchone()[0]
        a.inherited.refused(cur,lambda:rpc(a,cur,'reverse_journal',journal,'Must use source'))
    elif kind=='DIRECT_DML':
        def direct():
            a.admin(cur);cur.execute('grant usage on schema erp to authenticated');a.ordinary(cur)
            cur.execute("insert into erp.opening_subledger_settlements(balance_id,settlement_number,physical_at,amount,cash_account_id) values(%s,%s,statement_timestamp(),1.001,null)",(target,'DIRECT-'+uuid.uuid4().hex))
        a.inherited.refused(cur,direct)
    else:
        amount={'EXCEEDS_ADVANCE':'67.26','EXCEEDS_INVOICE':'20.01','PRECISION':'1.001','NEGATIVE':'-1'}.get(kind,'1')
        date=today-timedelta(days=2) if kind=='BEFORE_CUTOVER' else today+timedelta(days=1) if kind=='FUTURE' else today
        a.inherited.refused(cur,lambda:manage(a,cur,f,'APPLY',date,payload=payload,amount=amount,target_id=target))
    assert ledger(cur)==before;truth(cur)
    return dict(status='PASS',refusal=kind,atomic=True)


def source_refusal(a,cur,today,kind):
    f=fixture(a,cur,today,'CUSTOMER',finish=False);row=dict(f['row'])
    if kind=='WRONG_ACCOUNT':row['coa_account_code']=f['code']
    elif kind=='MISSING_PARTY':row['party_code']='MISSING'
    elif kind=='WRONG_REMAINDER':row['amount']='67.26'
    elif kind=='FUTURE_SOURCE':row['document_date']=str(today)
    elif kind=='UNKNOWN_KIND':row['party_type']='CONTRACTOR'
    elif kind=='DUPLICATE':pass
    a.upload(cur,f['batch'],'OPENING_ADVANCE',[row,row] if kind=='DUPLICATE' else [row]);before=ledger(cur)
    r=a.invoke(cur,'FINALIZE',f['batch']);assert r['status']=='DRAFT' and r['error_rows']>0 and ledger(cur)==before,r
    return dict(status='PASS',refusal=kind,no_business_effects=True)


def cross_batch(a,cur,today):
    f=fixture(a,cur,today,'VENDOR');g=fixture(a,cur,today,'VENDOR',party=f['party'],bill=None,finish=False)
    row={**g['row'],'document_number':f['row']['document_number']};a.upload(cur,g['batch'],'OPENING_ADVANCE',[row]);before=ledger(cur)
    r=a.invoke(cur,'FINALIZE',g['batch']);assert r['status']=='DRAFT' and r['error_rows']>0 and ledger(cur)==before
    return dict(status='PASS',cross_batch_document_refused=True)


def cases(a,cur,today):
    result=[('PREPAYMENT_OPENING:'+k+':'+str(c),lambda k=k,c=c:opening_lifecycle(a,cur,today,k,c)) for k in ('SUPPLIER','CUSTOMER','VENDOR') for c in (False,True)]
    result += [('PREPAYMENT_NATIVE:'+k,lambda k=k:native_document(a,cur,today,k)) for k in ('SUPPLIER','CUSTOMER','VENDOR')]
    result += [('PREPAYMENT_CORRECTION:'+k,lambda k=k:corrections(a,cur,today,k)) for k in ('SUPPLIER','CUSTOMER','VENDOR')]
    result += [('PREPAYMENT_REFUSAL:'+k,lambda k=k:refusal(a,cur,today,k)) for k in ('WRONG_PARTY','STALE','EXCEEDS_ADVANCE','EXCEEDS_INVOICE','PRECISION','NEGATIVE','BEFORE_CUTOVER','FUTURE','GENERIC_REVERSAL','DIRECT_DML')]
    result += [('PREPAYMENT_SOURCE:'+k,lambda k=k:source_refusal(a,cur,today,k)) for k in ('WRONG_ACCOUNT','MISSING_PARTY','WRONG_REMAINDER','FUTURE_SOURCE','UNKNOWN_KIND','DUPLICATE')]
    result += [('PREPAYMENT_CROSS_BATCH',lambda:cross_batch(a,cur,today))]
    return result
