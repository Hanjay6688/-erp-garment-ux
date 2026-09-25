"""GPT round8 independent business oracles. Tool9dd7bc2, producta095a9d, after.

Original M/P/BR plus ratified C0 e83d56e6. This is AUDITOR_SCENARIO,
not release acceptance. Writer modules supply fixtures/transport only.
Negative tests require the specified refusal and unchanged full domain boundary.
Multi-receipt cent expectations use the sum of document-rounded invoice costs,
never the implementation's moving-average calculation. All databases disposable.
"""
from pathlib import Path
from datetime import timedelta
from decimal import Decimal as D
import importlib.util, uuid
import cp6_aw_probe as awp
import cp6_az_probe as azp
import cp6_ba_probe as bap

api, boundary = awp.api, awp.boundary

def module(name):
    spec=importlib.util.spec_from_file_location('gpt8_'+name,Path(__file__).with_name(name+'.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

money,stock,business,selector,xaudit5,xaudit6=[module(n) for n in ('money','stock','business','selector','xaudit5','xaudit6')]

def attempt(cur, operation):
    api.admin(cur); before=boundary.snapshot(cur)
    result,error=stock._attempt(cur,operation)
    api.admin(cur)
    return result,error,boundary.snapshot(cur)==before

def refused(result,error,atomic,code):
    exact=bool(error and error.get('sqlstate')=='P0001' and error['message'].split(':',1)[0]==code)
    return dict(status='PASS' if exact and atomic else 'COUNTEREXAMPLE' if error is None else 'INCOMPLETE',
                expected_code=code,result=result,refusal=error,full_refusal_boundary_unchanged=atomic)

def wip_identity(cur,today):
    f=stock._fixture(cur,today)
    r,e,a=attempt(cur,lambda:stock._call(cur,'WIP_OUTPUT',stock._output_payload(cur,f,today-timedelta(days=2),'4','B')))
    return refused(r,e,a,'BA_WIP_OUTPUT_PRODUCT_BOUND')

def wip_dates(cur,today,positive=False,partial=False):
    f=stock._fixture(cur,today)
    first=stock._call(cur,'WIP_OUTPUT',stock._output_payload(cur,f,today-timedelta(days=3),'4' if partial else '8'))
    s=stock._source(cur,f)
    rev=stock._call(cur,'WIP_OUTPUT',dict(batch_id=f['batch'],opening_item_id=s['opening_item_id'],expected_remaining=str(s['remaining_qty_pcs']),
        operation='REVERSE',output_id=first['output_id'],reason='GPT8 dated capacity fixture reversal'))
    day=today if positive else today-timedelta(days=1)
    r,e,a=attempt(cur,lambda:stock._call(cur,'WIP_OUTPUT',stock._output_payload(cur,f,day,'4' if partial else '8')))
    if not positive and not partial:return refused(r,e,a,'BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING')
    if e:return dict(status='INCOMPLETE',refusal=e,expected='Legal dated remaining must be usable')
    api.admin(cur)
    minimum=cur.execute("""select min(n) from (select sum(case when stage_to='SEWING' then qty_pcs else 0 end-case when stage_from='SEWING' then qty_pcs else 0 end)
      over(order by physical_at,created_at,id) n from erp.wip_stage_events where po_id=%s) z""",(s['po_id'],)).fetchone()[0]
    return dict(status='PASS' if r.get('status')=='POSTED' and minimum>=0 else 'COUNTEREXAMPLE',minimum_sewing=str(minimum),result=r,reversal=rev)

def identity_control(cur,today,filled,attributes,suffix):
    # Same legal CSV data as writer's fixture; the assertions below are independent.
    f=bap.wip_batch(cur,today,product=filled,attributes=attributes)
    r,e,a=attempt(cur,lambda:stock._call(cur,'WIP_OUTPUT',stock._output_payload(cur,f,today-timedelta(days=2),'4',suffix)))
    if attributes and not filled and suffix=='B':return refused(r,e,a,'BA_WIP_OUTPUT_SOURCE_MISMATCH')
    if e:return dict(status='INCOMPLETE',refusal=e)
    expected='OPENING_PRODUCT' if filled else 'SOURCE_ATTRIBUTES' if attributes else 'ASSIGNED_AT_COMPLETION'
    api.admin(cur)
    p=cur.execute('select basis,opening_product_id,output_product_id,checked,unknown,source_attributes from erp.initial_import_wip_output_identity_v1 where output_id=%s',(r['output_id'],)).fetchone()
    expected_product=cur.execute('select id from erp.products where sku=%s',(f['code']+suffix,)).fetchone()[0]
    ok=p is not None and p[0]==expected and p[2]==expected_product and (not filled or p[1]==p[2]) and not(set(p[3])&set(p[4]))
    return dict(status='PASS' if ok and r.get('status')=='POSTED' else 'COUNTEREXAMPLE',expected_basis=expected,provenance=money.strings(p),result=r)

def overlap(cur,today,kind,distinct=False):
    import cp6_opening_overlap_probe as ovp
    first=ovp.imported(cur,today,kind);api.admin(cur)
    tag,first_batch=cur.execute('select b.batch_code,b.id from erp.migration_batches b join erp.opening_balance_headers h on h.migration_batch_id=b.id where h.id=%s',(first,)).fetchone()
    code='G8OPEN'+uuid.uuid4().hex[:12]
    b=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(today-timedelta(days=1))))['batch_id']
    row,control=bap.opening_rows(kind,tag)
    if distinct:
        api.upload(cur,b,'LOCATION',[dict(location_code=code,location_name='GPT8 distinct warehouse',location_type='RAW_MATERIAL_WAREHOUSE' if kind=='MATERIAL' else 'FG_WAREHOUSE')])
        row['location_code']=code
    api.upload(cur,b,'OPENING_BALANCE_ITEM',[row]);api.upload(cur,b,'OPENING_CONTROL',[control])
    v=api.invoke(cur,'VALIDATE',b)
    if v.get('error_rows')!=0:return dict(status='INCOMPLETE',validation=v)
    r,e,a=attempt(cur,lambda:api.invoke(cur,'FINALIZE',b))
    if not distinct:return dict(kind=kind,**refused(r,e,a,'BA_IMPORT_OPENING_ALREADY_POSTED'))
    api.admin(cur)
    count=cur.execute("select count(*) from erp.opening_balance_headers where migration_batch_id=any(%s::uuid[]) and status='POSTED'",([str(first_batch),str(b)],)).fetchone()[0]
    return dict(status='PASS' if not e and r.get('status')=='POSTED' and count==2 else 'INCOMPLETE' if e else 'COUNTEREXAMPLE',kind=kind,distinct_source='different warehouse',posted_headers=count,result=r,refusal=e)

def next_receipt(cur,first,day,price,kind):
    prod=azp.chain.production
    payload=dict(purchase_number='G8MULTI-'+uuid.uuid4().hex,
        supplier_id=prod.prior.BASE_SUPPLIER,location_id=first['location'],physical_at=prod.at(day,11),change_reason='Independent second receipt, same material',
        lines=[dict(material_id=first['material'],qty=1,unit_price=price,price_state='FINAL' if kind=='DIRECT' else 'ESTIMATED',
        price_source='SUPPLIER_INVOICE' if kind=='DIRECT' else 'MANUAL_ESTIMATE',rolls=[dict(roll_number='G8R-'+uuid.uuid4().hex,qty=1)])])
    if kind=='DIRECT':payload['supplier_invoice_number']='G8INV-'+uuid.uuid4().hex
    d=prod.rpc(cur,'erp.save_material_purchase_draft_v2',payload)
    pid=uuid.UUID(d['purchase_id'])
    cur.execute('select erp.post_material_purchase_v2(%s,%s,%s,%s)',(pid,uuid.uuid4(),int(d['row_version']),'GPT8 second receipt post'))
    api.admin(cur)
    item,roll=cur.execute('select i.id,r.id from erp.material_purchase_items i join erp.material_rolls r on r.purchase_item_id=i.id where i.purchase_id=%s',(pid,)).fetchone()
    return dict(material=first['material'],location=first['location'],purchase=pid,item=item,roll=roll)

def multi_cents(cur,today,kind,old,new):
    receipt_day,cut_day,invoice_day=[today-timedelta(days=n) for n in (4,3,2)]
    days=[receipt_day,cut_day,invoice_day,today]
    boundary.historical.prior.set_open_period(cur,receipt_day-timedelta(days=1))
    before=money.ledger(cur,days)
    first=azp.final_receipt(cur,receipt_day,qty=1,price=old) if kind=='DIRECT' else money.estimated_receipt(cur,receipt_day,old)
    api.admin(cur)
    first['roll']=cur.execute('select id from erp.material_rolls where purchase_item_id=%s',(first['item'],)).fetchone()[0]
    second=next_receipt(cur,first,receipt_day,old,kind)
    azp.cut(cur,first,cut_day,1,8);azp.cut(cur,second,cut_day,1,9)
    initial=money.delta(money.ledger(cur,days),before)
    for fx in (first,second):
        if kind=='DIRECT':money.correction(cur,fx,invoice_day,new)
        else:money.invoice(cur,fx,today,invoice_day,new)
    azp.chain.production.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');api.admin(cur)
    observed=money.delta(money.ledger(cur,days),before)
    expected={}
    for day in days:
        # Two invoices round separately; no permission to erase or create their cent difference.
        amount=money.cents(new if day>=invoice_day else old)*2
        row=dict.fromkeys(money.KEYS,D('0.00'))
        row['MATERIAL_INVENTORY' if day<cut_day else 'WIP']=amount
        row['AP_SUPPLIER' if kind=='DIRECT' or day>=invoice_day else 'GRNI_MATERIAL']=-amount
        expected[str(day)]=row
    qty=D(str(cur.execute('select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=%s',(first['material'],)).fetchone()[0]))
    mismatches={day:{k:dict(expected=str(expected[day][k]),actual=str(observed[day][k])) for k in money.KEYS if observed[day][k]!=expected[day][k]} for day in observed}
    mismatches={d:r for d,r in mismatches.items() if r}
    return dict(status='COUNTEREXAMPLE' if mismatches or qty!=0 else 'PASS',oracle='M3818/3820 plus A4: sum of separately posted document cents; exhausted inventory has zero value. No per-receipt tolerance authorized.',
        kind=kind,old=old,new=new,raw_qty=str(qty),initial=money.strings(initial),observed=money.strings(observed),expected=money.strings(expected),mismatches=mismatches)

def cases(cur,today):
    out=money.cases(cur,today)+business.cases(cur,today)+selector.cases(cur,today)+xaudit6.cases(cur,today)
    specs=[('SI01_BOUND_REJECT',lambda:wip_identity(cur,today)),('SI02_DATE_REJECT',lambda:wip_dates(cur,today)),
      ('SI02_DATE_CONTROL',lambda:wip_dates(cur,today,positive=True)),('SI02_PARTIAL_PREFIX_CONTROL',lambda:wip_dates(cur,today,partial=True)),
      ('SI03_EXACT_REPLAY',lambda:stock.retry_case(cur,today))]
    for filled,attrs,suffix in [(True,True,'A'),(False,True,'A'),(False,True,'B'),(False,False,'B')]:
        specs.append((f'IDENTITY_{filled}_{attrs}_{suffix}',lambda f=filled,a=attrs,s=suffix:identity_control(cur,today,f,a,s)))
    for kind in ('MATERIAL','FINISHED_GOODS','BS','CASH_BANK','WIP'):
        specs.append(('OPEN_SAME_'+kind,lambda k=kind:overlap(cur,today,k)))
    for kind in ('MATERIAL','FINISHED_GOODS'):
        specs.append(('OPEN_DISTINCT_'+kind,lambda k=kind:overlap(cur,today,k,True)))
    for kind in ('DIRECT','INVOICE'):
        for label,old,new in [('UP','10.00','10.005'),('DOWN','10.01','10.004')]:
            specs.append(('MULTI_CENT_'+kind+'_'+label,lambda k=kind,o=old,n=new:multi_cents(cur,today,k,o,n)))
    out += [('G8:'+k,lambda f=f:money.guarded(cur,f)) for k,f in specs]
    assert len({k for k,_ in out})==len(out)
    return out

def races(tools,today):
    # R2 rerun, plus physical safety of R3. Preserve observed refusal wording as P3 evidence.
    prior=dict(xaudit5.races(tools,today))
    def physical_only():
        r=prior['XA5:R3_TWO_SESSIONS_WIP_COMPLETE_SAME_REMAINING']()
        r['original_status']=r.get('status')
        c=r.get('checks',{})
        if all(c.get(k) for k in ('holder_posted','worker_refused','total_output_not_above_source')):
            r['status']='PASS';r['wording_issue_open']=not c.get('worker_stale_version')
        return r
    return [('G8:R2_CLOSE_ONCE',prior['XA5:R2_TWO_SESSIONS_CLOSE_SAME_DATE']),('G8:R3_WIP_SAFETY',physical_only)]

def http_cases(http,today):
    return xaudit5.http_cases(http,today)
