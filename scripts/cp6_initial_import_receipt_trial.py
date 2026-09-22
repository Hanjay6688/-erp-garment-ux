"""Opening GRNI acceptance family on the combined AO+AP transaction proposal."""
from datetime import timedelta
from decimal import Decimal as D
import json,uuid
import cp6_final_gap_native as calendar

def rpc(a,cur,name,*params):
    # Existing invoice/return APIs are private-schema v2 APIs. The temporary
    # schema usage is fixture-only; the import RPC itself needs no such grant.
    a.admin(cur);cur.execute('grant usage on schema erp to authenticated');a.ordinary(cur)
    value=cur.execute('select erp.'+name+'('+','.join(['%s']*len(params))+')',params).fetchone()[0]
    a.admin(cur);cur.execute('revoke usage on schema erp from authenticated');return value

def fixture(a,cur,today,roll=False,code=None,number=None,qty='20',cost='2.25'):
    code=code or 'R'+uuid.uuid4().hex[:10];number=number or 'RECEIPT-'+uuid.uuid4().hex[:10]
    batch=a.call(cur,'CREATE',dict(batch_code='AP-'+uuid.uuid4().hex,cutover_date=str(today-timedelta(days=8))))['batch_id']
    unit=cur.execute("select unit_code from erp.uom_definitions where dimension='LENGTH' and is_active and unit_code=upper(unit_code) order by unit_code limit 1").fetchone()[0] if roll else 'PCS'
    for entity,rows in {
        'SUPPLIER':[dict(supplier_code=code,supplier_name='Unbilled supplier')],
        'LOCATION':[dict(location_code=code,location_name='Unbilled warehouse',location_type='RAW_MATERIAL_WAREHOUSE')],
        'MATERIAL':[dict(material_sku=code,material_name='Unbilled opening',material_type='FABRIC' if roll else 'OTHER',unit_code=unit)],
    }.items():a.upload(cur,batch,entity,rows)
    stock=dict(material_sku=code,location_code=code,unit_cost=cost,opening_source_key='STOCK',control_key='STOCK')
    stock.update(dict(roll_number=code+'-'+uuid.uuid4().hex[:6],opening_qty=qty,supplier_code=code) if roll else dict(balance_type='MATERIAL',qty=qty))
    entity='MATERIAL_ROLL' if roll else 'OPENING_BALANCE_ITEM'
    a.upload(cur,batch,entity,[stock])
    receipt=dict(receipt_number=number,receipt_line_number='001',receipt_date=str(today-timedelta(days=30)),supplier_code=code,
                 material_sku=code,location_code=code,qty=qty,unit_cost=cost,opening_source_key='STOCK',control_key='GRNI')
    a.upload(cur,batch,'UNINVOICED_RECEIPT',[receipt])
    amount=str((D(qty)*D(cost)).quantize(D('.01')))
    a.upload(cur,batch,'OPENING_CONTROL',[dict(control_key='STOCK',balance_type='MATERIAL',qty=qty,amount=amount),dict(control_key='GRNI',balance_type='GRNI_MATERIAL',qty=qty,amount=amount)])
    return dict(batch=batch,code=code,receipt=receipt,stock=stock,stock_entity=entity)

def finalize(a,cur,f):
    before=a.production.ledger(cur);assert a.invoke(cur,'VALIDATE',f['batch'])['error_rows']==0,a.read(cur,f['batch'])
    assert a.production.ledger(cur)==before
    payload=dict(batch_id=f['batch'],expected_revision=a.read(cur,f['batch'])['batch']['revision']);key=uuid.uuid4()
    result=a.call(cur,'FINALIZE',payload,key);assert result['status']=='POSTED',a.read(cur,f['batch'])
    boundary=a.actors.boundary(cur);assert a.call(cur,'FINALIZE',payload,key)==result and a.actors.boundary(cur)==boundary
    row=a.read(cur,f['batch'])['batch']['uninvoiced_receipts'][0]
    extra=cur.execute('select i.material_id,h.location_id,oi.roll_id from erp.material_purchase_items i join erp.material_purchase_headers h on h.id=i.purchase_id join erp.initial_import_receipt_lines l on l.purchase_item_id=i.id join erp.opening_balance_items oi on oi.id=l.opening_item_id where i.id=%s',(row['purchase_item_id'],)).fetchone()
    return {**row,**dict(zip(['material_id','location_id','roll_id'],extra))}

def truth(cur):
    names=('V267_GRNI_GL_SUBLEDGER_MISMATCH','V267_AP_GL_SUBLEDGER_MISMATCH','V267_ESTIMATED_RECEIPT_MISSING_GRNI_RECLASS',
           'V267_INVOICE_MATCH_OVER_RECEIPT','V267_PAYMENT_EXCEEDS_FINAL_AP','V2620M_SUPPLIER_PAYMENT_EXACT_STATUS',
           'AP_OPENING_RECEIPT_SOURCE_DRIFT','AP_OPENING_RECEIPT_JOURNAL_DRIFT')
    rows=cur.execute('select check_name,issue_count from erp.run_v267_financial_truth_checks() where check_name=any(%s)',(list(names),)).fetchall()
    assert len(rows)==len(names) and all(v==0 for _,v in rows),rows
    return dict(rows)

def invoice(a,cur,today,row,qty,price='3',date=None):
    payload=dict(invoice_number='INV-'+uuid.uuid4().hex,supplier_id=row['supplier_id'],invoice_date=str(date or today-timedelta(days=2)),
                 change_reason='Imported receipt invoice',lines=[dict(purchase_item_id=row['purchase_item_id'],qty_invoiced=str(qty),unit_price=price)])
    return rpc(a,cur,'save_material_supplier_invoice_draft_v2',json.dumps(payload,default=str),uuid.uuid4(),None)

def post_invoice(a,cur,draft):
    key=uuid.uuid4();args=(draft['supplier_invoice_id'],key,draft['row_version'],'Post imported receipt invoice')
    result=rpc(a,cur,'post_material_supplier_invoice_v2',*args)
    before=a.actors.boundary(cur);assert rpc(a,cur,'post_material_supplier_invoice_v2',*args)==result and a.actors.boundary(cur)==before
    return result

def lifecycle(a,cur,today,roll=False,consume=False,zone='UTC'):
    cur.execute('set local timezone to '+("'Pacific/Kiritimati'" if zone!='UTC' else "'UTC'"))
    truth(cur);f=fixture(a,cur,today,roll);row=finalize(a,cur,f);truth(cur)
    stock=lambda:cur.execute('select cached_stock_qty,moving_average_cost from erp.materials where id=%s',(row['material_id'],)).fetchone()
    assert stock()==(D(20),D('2.25')),stock()
    assert cur.execute("select count(*) from erp.material_stock_movements where material_id=%s",(row['material_id'],)).fetchone()[0]==1
    assert cur.execute("select count(*) from erp.journal_entries where source_id=%s and source_type in('MATERIAL_PURCHASE','MATERIAL_PURCHASE_GRNI_RECLASS')",(row['purchase_id'],)).fetchone()[0]==0
    original=cur.execute('select to_jsonb(i) from erp.opening_balance_items i where id=%s',(row['opening_item_id'],)).fetchone()[0]
    if consume:
        payload=dict(adjustment_number='ADJ-'+uuid.uuid4().hex,reason_code='COUNT_CORRECTION',physical_at=str(today-timedelta(days=5))+'T10:00:00+07:00',location_id=row['location_id'],change_reason='Post-cutover physical shortage',items=[dict(material_id=row['material_id'],roll_id=row['roll_id'],qty_signed='-5')])
        adj=rpc(a,cur,'save_material_adjustment_draft_v2',json.dumps(payload,default=str),uuid.uuid4(),None)
        rpc(a,cur,'post_material_adjustment_v2',adj['material_adjustment_id'],uuid.uuid4(),adj['row_version'],'Post physical shortage')
    prior_journals=[x[0] for x in cur.execute('select id from erp.journal_entries').fetchall()]
    baseline=a.production.ledger(cur);d=invoice(a,cur,today,row,8)
    assert a.production.ledger(cur)==baseline
    first=post_invoice(a,cur,d);truth(cur)
    assert stock()==(D(15 if consume else 20),D('2.55')),stock()
    assert cur.execute('select erp.material_purchase_grni_total(%s),erp.material_purchase_final_ap_total(%s)',(row['purchase_id'],row['purchase_id'])).fetchone()==(D(27),D(24))
    second=post_invoice(a,cur,invoice(a,cur,today,row,12));truth(cur)
    assert stock()==(D(15 if consume else 20),D(3)),stock()
    assert cur.execute('select erp.material_purchase_grni_total(%s),erp.material_purchase_final_ap_total(%s)',(row['purchase_id'],row['purchase_id'])).fetchone()==(0,60)
    bad=invoice(a,cur,today,row,1)
    a.inherited.refused(cur,lambda:post_invoice(a,cur,bad))
    rpc(a,cur,'reverse_material_supplier_invoice_v2',second['supplier_invoice_id'],'Reverse second invoice',uuid.uuid4(),second['row_version']);truth(cur)
    assert stock()==(D(15 if consume else 20),D('2.55'))
    rpc(a,cur,'reverse_material_supplier_invoice_v2',first['supplier_invoice_id'],'Reverse first invoice',uuid.uuid4(),first['row_version']);truth(cur)
    assert stock()==(D(15 if consume else 20),D('2.25'))
    assert cur.execute('select to_jsonb(i) from erp.opening_balance_items i where id=%s',(row['opening_item_id'],)).fetchone()[0]==original
    assert cur.execute('select count(*) from erp.invoice_recost_execution_context').fetchone()[0]==0
    dates=cur.execute('select source_type,economic_date from erp.journal_entries where not (id=any(%s))',(prior_journals,)).fetchall()
    assert dates and all(d==today-timedelta(days=2) for _,d in dates),dates
    return dict(status='PASS',invoice_dates_consistent=True,roll=roll,post_cutover_consumption=consume,zone=zone,stock_received_once=True,partial_then_full_then_reversed=True,
                opening_snapshot_immutable=True,replay_identical=True,financial_truth=truth(cur))

def return_lifecycle(a,cur,today,roll=False,matched=False):
    f=fixture(a,cur,today,roll);row=finalize(a,cur,f)
    if matched:post_invoice(a,cur,invoice(a,cur,today,row,20))
    payload=dict(return_number='RET-'+uuid.uuid4().hex,supplier_id=row['supplier_id'],location_id=row['location_id'],
                 physical_at=str(today-timedelta(days=1))+'T10:00:00+07:00',change_reason='Imported receipt return',
                 items=[dict(material_id=row['material_id'],roll_id=row['roll_id'],purchase_item_id=row['purchase_item_id'],qty='5')])
    d=rpc(a,cur,'save_material_supplier_return_draft_v2',json.dumps(payload,default=str),uuid.uuid4(),None)
    p=rpc(a,cur,'post_material_supplier_return_v2',d['material_supplier_return_id'],uuid.uuid4(),d['row_version'],'Post imported receipt return');truth(cur)
    assert cur.execute('select cached_stock_qty from erp.materials where id=%s',(row['material_id'],)).fetchone()[0]==15
    assert cur.execute('select erp.material_purchase_grni_total(%s),erp.material_purchase_final_ap_total(%s)',(row['purchase_id'],row['purchase_id'])).fetchone()==((0,D(45)) if matched else (D('33.75'),0))
    rpc(a,cur,'reverse_material_supplier_return_v2',d['material_supplier_return_id'],'Restore receipt return',uuid.uuid4(),p['row_version']);truth(cur)
    assert cur.execute('select cached_stock_qty from erp.materials where id=%s',(row['material_id'],)).fetchone()[0]==20
    return dict(status='PASS',roll=roll,matched=matched,return_and_reverse=True,financial_truth=truth(cur))

def production_lifecycle(a,cur,today,closed=False):
    production=a.production
    cutover=today-timedelta(days=8)
    original_reports=production.reports
    def period_reports(cursor,through):
        production.owner(cursor)
        return {str(day):production.one(cursor,'select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',(cutover,day,day))
                for day in (through-timedelta(days=1),through)}
    production.reports=period_reports
    a.admin(cur);cur.execute('grant usage on schema erp to authenticated')
    try:
        production.prior.set_open_period(cur,cutover-timedelta(days=1))
        baseline=production.ledger(cur);baseline_report=production.reports(cur,today);a.admin(cur)
        f=fixture(a,cur,today,True,qty='10',cost='10');row=finalize(a,cur,f)
        movement=cur.execute("select id from erp.material_stock_movements where source_type='OPENING_BALANCE_ITEM' and source_id=%s",(row['opening_item_id'],)).fetchone()[0]
        graph=dict(material=row['material_id'],purchase=row['purchase_id'],item=row['purchase_item_id'],roll=row['roll_id'],
                   movement=movement,location=row['location_id'],purchase_day=cutover,ledger_baseline=baseline,report_baseline=baseline_report)
        a.admin(cur);cur.execute('grant usage on schema erp to authenticated')
        class OrdinaryDraftCursor:
            def __getattr__(self,name):return getattr(cur,name)
            def execute(self,query,params=None,**kwargs):
                if 'insert into erp.work_completion_events(' in str(query) or 'insert into erp.work_completion_lines(' in str(query):calendar.peer.ordinary(cur)
                return cur.execute(query,params,**kwargs)
        production.partial_production(OrdinaryDraftCursor(),graph)
        before=production.observe(cur,graph,today)
        errors,_=calendar.accounting_mismatches(before,100,0,100);assert not errors,errors
        if closed:
            calendar.peer.ordinary(cur);cur.execute('select erp.close_accounting_through(%s,%s)',(cutover,'Opening receipt cutover closed'))
        results=[];remaining=D(10);ap=D(0)
        for qty,rate in [(3,D('8.25')),(7,D('11.75'))]:
            a.admin(cur);prior={r[0] for r in cur.execute('select id from erp.journal_entries').fetchall()}
            post_invoice(a,cur,invoice(a,cur,today,row,qty,str(rate)))
            a.admin(cur);fresh=[r for r in cur.execute('select id,economic_date,transaction_date from erp.journal_entries').fetchall() if r[0] not in prior]
            assert fresh and all(e==today-timedelta(days=2) and t==today-timedelta(days=2) for _,e,t in fresh),fresh
            remaining-=qty;ap+=qty*rate
            a.admin(cur);cur.execute('grant usage on schema erp to authenticated')
            state=production.observe(cur,graph,today)
            errors,expected=calendar.accounting_mismatches(state,ap+remaining*10,ap,remaining*10)
            assert not errors,errors
            assert all(q[1]=='DONE' for q in state['queue']),state['queue']
            a.admin(cur);truth(cur)
            results.append(dict(qty=qty,price=str(rate),expected=expected,queue_finished_before_return=True))
        return dict(status='PASS',cutover_closed=closed,opening_stock_once=True,partial_production=True,ledger_and_report_reconciled=True,observations=results)
    finally:
        production.reports=original_reports

def document_cents(a,cur,today):
    f=fixture(a,cur,today,qty='1',cost='0.333333')
    stock=f['stock'];receipt=f['receipt']
    a.upload(cur,f['batch'],'OPENING_BALANCE_ITEM',[stock,dict(stock,opening_source_key='STOCK-2')])
    a.upload(cur,f['batch'],'UNINVOICED_RECEIPT',[receipt,dict(receipt,opening_source_key='STOCK-2',receipt_line_number='002')])
    a.upload(cur,f['batch'],'OPENING_CONTROL',[dict(control_key='STOCK',balance_type='MATERIAL',qty='2',amount='0.66'),dict(control_key='GRNI',balance_type='GRNI_MATERIAL',qty='2',amount='0.67')])
    row=finalize(a,cur,f);truth(cur)
    assert cur.execute('select erp.material_purchase_grni_total(%s)',(row['purchase_id'],)).fetchone()[0]==D('0.666666')
    assert len(a.read(cur,f['batch'])['batch']['uninvoiced_receipts'])==2
    return dict(status='PASS',stock_opening='0.66',document_grni='0.67',line_count=2,rounded_per_document=True)

def payment_lifecycle(a,cur,today):
    f=fixture(a,cur,today);code=f['code'];b=f['batch']
    a.upload(cur,b,'CHART_ACCOUNT',[dict(account_code=code,account_name='Receipt bank',account_type='ASSET',report_group='CURRENT_ASSETS',normal_balance='DEBIT')])
    a.upload(cur,b,'CASH_ACCOUNT',[dict(cash_account_code=code,cash_account_name='Receipt bank',coa_account_code=code,account_kind='BANK')])
    a.upload(cur,b,'OPENING_BALANCE_ITEM',[f['stock'],dict(balance_type='CASH_BANK',cash_account_code=code,amount='100',control_key='CASH')])
    a.upload(cur,b,'OPENING_CONTROL',[dict(control_key='STOCK',balance_type='MATERIAL',qty='20',amount='45'),dict(control_key='GRNI',balance_type='GRNI_MATERIAL',qty='20',amount='45'),dict(control_key='CASH',balance_type='CASH_BANK',amount='100')])
    row=finalize(a,cur,f)
    cash=cur.execute('select id from erp.cash_accounts where cash_account_code=%s',(code,)).fetchone()[0]
    balance=lambda:cur.execute('select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.chart_accounts c on c.id=l.account_id where c.account_code=%s',(code,)).fetchone()[0]
    assert balance()==100
    payment=cur.execute("insert into erp.supplier_payments(purchase_id,payment_number,payment_date,amount,cash_account_id) values(%s,%s,%s,10,%s) returning id",(row['purchase_id'],'PAY-'+uuid.uuid4().hex,a.production.at(today-timedelta(days=1),12),cash)).fetchone()[0]
    a.inherited.refused(cur,lambda:rpc(a,cur,'post_supplier_payment',payment))
    assert balance()==100
    posted=post_invoice(a,cur,invoice(a,cur,today,row,8))
    rpc(a,cur,'post_supplier_payment',payment);truth(cur);assert balance()==90
    a.inherited.refused(cur,lambda:rpc(a,cur,'reverse_material_supplier_invoice_v2',posted['supplier_invoice_id'],'Cannot undo paid invoice',uuid.uuid4(),posted['row_version']))
    rpc(a,cur,'reverse_supplier_payment',payment,'Restore payment');truth(cur);assert balance()==100
    rpc(a,cur,'reverse_material_supplier_invoice_v2',posted['supplier_invoice_id'],'Restore invoice',uuid.uuid4(),posted['row_version']);truth(cur)
    return dict(status='PASS',grni_cannot_be_paid=True,bank_restored=True,paid_invoice_reversal_refused=True)

def refusal(a,cur,today,kind):
    f=fixture(a,cur,today);r=f['receipt'].copy()
    if kind=='LEGACY_FINALIZE_OMITS_RECEIPT':
        assert a.invoke(cur,'VALIDATE',f['batch'])['error_rows']==0
        cur.execute('select erp.apply_migration_master_rows(%s)',(f['batch'],))
        opening=cur.execute('select erp.prepare_migration_opening_balance(%s,null)',(f['batch'],)).fetchone()[0]
        cur.execute('select erp.post_opening_balance(%s)',(opening,))
        msg=a.inherited.refused(cur,lambda:cur.execute('select erp.finalize_migration_batch(%s)',(f['batch'],)))
        return dict(status='PASS',refusal=msg)
    if kind=='MISSING_SOURCE':r['opening_source_key']='MISSING'
    elif kind=='PRE_CUTOVER_CONSUMPTION':r['qty']='25'
    elif kind=='COST_MISMATCH':r['unit_cost']='2.250001'
    elif kind=='FUTURE_RECEIPT':r['receipt_date']=str(today)
    elif kind=='DUPLICATE_LINE':pass
    elif kind in('CROSS_BATCH','LEGACY_AFTER_IMPORT','IMMUTABLE_RECEIPT','INVOICE_BEFORE_CUTOVER','SUMMARY_AFTER_IMPORT'):
        row=finalize(a,cur,f)
        if kind=='LEGACY_AFTER_IMPORT':
            msg=a.inherited.refused(cur,lambda:cur.execute('insert into erp.material_purchase_headers(purchase_number,supplier_id,physical_at,location_id) values(%s,%s,statement_timestamp(),%s)',(r['receipt_number'].lower(),row['supplier_id'],row['location_id'])))
            return dict(status='PASS',refusal=msg)
        if kind=='IMMUTABLE_RECEIPT':
            msg=a.inherited.refused(cur,lambda:cur.execute("update erp.material_purchase_headers set status='REVERSED' where id=%s",(row['purchase_id'],)))
            return dict(status='PASS',refusal=msg)
        if kind=='INVOICE_BEFORE_CUTOVER':
            msg=a.inherited.refused(cur,lambda:invoice(a,cur,today,row,1,date=today-timedelta(days=9)))
            return dict(status='PASS',refusal=msg)
        if kind=='SUMMARY_AFTER_IMPORT':
            b=a.call(cur,'CREATE',dict(batch_code='AP-'+uuid.uuid4().hex,cutover_date=str(today-timedelta(days=1))))['batch_id']
            a.upload(cur,b,'OPENING_BALANCE_ITEM',[dict(balance_type='SUPPLIER_PAYABLE',supplier_code=f['code'],amount='45',control_key='AP')])
            a.upload(cur,b,'OPENING_CONTROL',[dict(balance_type='SUPPLIER_PAYABLE',amount='45',control_key='AP')]);f['batch']=b
        else:
            f=fixture(a,cur,today,code=f['code'],number=r['receipt_number'].lower());r=f['receipt']
    if kind!='SUMMARY_AFTER_IMPORT':a.upload(cur,f['batch'],'UNINVOICED_RECEIPT',[r,r] if kind=='DUPLICATE_LINE' else [r])
    before=a.production.ledger(cur);count=cur.execute('select count(*) from erp.initial_import_receipt_headers').fetchone()[0]
    result=a.invoke(cur,'FINALIZE',f['batch']);assert result['status']=='DRAFT' and result['error_rows']>0,result
    assert a.production.ledger(cur)==before and cur.execute('select count(*) from erp.initial_import_receipt_headers').fetchone()[0]==count
    errors=[e for x in a.read(cur,f['batch'])['batch']['rows'] for e in x['errors']]
    assert any(any(k in e for k in ('opening_source_key:','receipt_number:','receipt_date:','document_number:')) for e in errors),errors
    return dict(status='PASS',refusal=kind,ledger_unchanged=True,errors=errors)

def cases(a,cur,today):
    result=[('RECEIPT_LIFECYCLE:'+str(roll)+':'+str(consume)+':'+zone,
             lambda roll=roll,consume=consume,zone=zone:lifecycle(a,cur,today,roll,consume,zone))
            for roll,consume,zone in [(False,False,'UTC'),(True,False,'UTC'),(False,True,'UTC'),(True,True,'Pacific/Kiritimati')]]
    result += [('RECEIPT_RETURN:'+str(roll)+':'+str(matched),lambda roll=roll,matched=matched:return_lifecycle(a,cur,today,roll,matched)) for roll in (False,True) for matched in (False,True)]
    result += [('RECEIPT_PRODUCTION:'+str(closed),lambda closed=closed:production_lifecycle(a,cur,today,closed)) for closed in (False,True)]
    result += [('RECEIPT_DOCUMENT_CENTS',lambda:document_cents(a,cur,today)),('RECEIPT_PAYMENT',lambda:payment_lifecycle(a,cur,today))]
    result += [('RECEIPT_REFUSAL:'+kind,lambda kind=kind:refusal(a,cur,today,kind)) for kind in (
        'MISSING_SOURCE','PRE_CUTOVER_CONSUMPTION','COST_MISMATCH','FUTURE_RECEIPT','DUPLICATE_LINE','CROSS_BATCH',
        'LEGACY_AFTER_IMPORT','IMMUTABLE_RECEIPT','INVOICE_BEFORE_CUTOVER','SUMMARY_AFTER_IMPORT','LEGACY_FINALIZE_OMITS_RECEIPT')]
    return result
