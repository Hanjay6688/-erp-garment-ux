"""Additional independent family oracles, beyond the incoming eight failures."""
from datetime import timedelta
from decimal import Decimal
import json
import uuid
import psycopg
import cp6_as_probe as probe
import cp6_ao_ap_installed as api
import cp6_initial_import_production_trial as production
import cp6_successor_regression as predecessor


def staged_brand(cur, today):
    f = production.fixture(api, cur, today)
    code, second = f['code'], f['code']+'B'
    api.upload(cur, f['batch'], 'MODEL', [dict(model_code=code,model_name=code),dict(model_code=second,model_name=second)])
    api.upload(cur, f['batch'], 'BRAND', [dict(brand_code=code,brand_name=code),dict(brand_code=second,brand_name=second)])
    api.upload(cur, f['batch'], 'PRODUCT', [dict(sku=code,product_name=code,model_code=model,brand_code=model,size_code=code,color_name='Blue') for model in (code,second)])
    api.upload(cur, f['batch'], 'OPEN_PO', [dict(po_number=code,model_code=second,contractor_code=code,target_qty_pcs='10',status='SEWING',current_stage='SEWING')])
    for row in f['rows']:
        if row['balance_type']=='BS':
            row.update(brand_code=second,model_code=second,color_name='Blue')
        if row['balance_type']=='FINISHED_GOODS':
            row.update(brand_code=code,model_code=code,color_name='Blue',size_code=code)
    api.upload(cur, f['batch'], 'OPENING_BALANCE_ITEM', f['rows'])
    result = api.invoke(cur, 'VALIDATE', f['batch'])
    workspace = api.read(cur, f['batch'])
    errors = [dict(entity=r['entity'],payload=r['payload'],errors=r['errors']) for r in workspace['batch']['rows'] if r['validation_status']=='ERROR']
    if result['error_rows']:
        return dict(status='COUNTEREXAMPLE', errors=errors, finding='Qualified cross-brand BS rejected because another brand model is selected')
    posted = api.invoke(cur, 'FINALIZE', f['batch'])
    assert posted['status']=='POSTED', posted
    chosen = cur.execute('''select b.brand_code,m.model_code,z.size_code
        from erp.opening_balance_items i join erp.opening_balance_headers h on h.id=i.opening_id
        join erp.products p on p.id=i.product_id join erp.brands b on b.id=p.brand_id
        join erp.product_models m on m.id=p.model_id join erp.sizes z on z.id=p.size_id
        where h.migration_batch_id=%s and i.balance_type='BS' ''', (f['batch'],)).fetchone()
    assert chosen == (second,second,code), chosen
    production.truth(cur)
    return dict(status='PASS', explicit_brand_model_size_preserved=True, posted_bs_identity=chosen)


def output_guard(cur, today, variant):
    f = production.fixture(api, cur, today)
    _, sources = production.finalize(api, cur, f)
    product = cur.execute('select id,model_id,size_id from erp.products where sku=%s',(f['code'],)).fetchone()
    tag = f['code']+'B'
    brand = cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s) returning id',(tag,tag)).fetchone()[0]
    other = cur.execute('''insert into erp.products(sku,product_name,model_id,brand_id,size_id,color_name,is_active,effective_from)
        values(%s,%s,%s,%s,%s,'Blue',true,%s) returning id''',
        (f['code'],tag,product[1],brand,product[2],probe.invoice.at(today-timedelta(days=6),8))).fetchone()[0]
    payload = dict(batch_id=f['batch'],opening_item_id=sources['WIP']['opening_item_id'],expected_remaining='8',
                   operation='COMPLETE',qty_pcs='4',product_sku=f['code'],brand_code=tag,
                   location_code=f['code']+'F',date=str(today-timedelta(days=3)),reason='AS complete qualified product')
    if variant=='WRONG_BRAND': payload['brand_code']='MISSING-'+tag
    if variant=='CONFLICTING_ID': payload['product_id']=str(product[0])
    if variant=='FUTURE_ID':
        # A new master version cannot receive production before it ever existed.
        cur.execute('insert into erp.products(sku,product_name,model_id,brand_id,size_id,color_name,is_active,effective_from) values(%s,%s,%s,%s,%s,\'Blue\',true,%s) returning id',
                    (tag,tag,product[1],brand,product[2],probe.invoice.at(today,8)))
        payload.update(product_id=str(cur.fetchone()[0]),product_sku=tag)
    before = predecessor.snapshot(cur)
    refusal = None
    cur.execute('savepoint output_call')
    try: result = api.call(cur,'WIP_OUTPUT',payload)
    except psycopg.Error as exc:
        refusal = dict(sqlstate=exc.sqlstate,message=exc.diag.message_primary)
        cur.execute('rollback to savepoint output_call')
    api.admin(cur);cur.execute('release savepoint output_call')
    if variant!='BRAND_SECOND':
        assert refusal and predecessor.snapshot(cur)==before, (variant,refusal)
        return dict(status='PASS',variant=variant,refusal=refusal,all_data_unchanged=True)
    assert not refusal, refusal
    chosen = cur.execute('select product_id from erp.fg_lots where id=%s',(result['lot_id'],)).fetchone()[0]
    if chosen!=other:
        return dict(status='COUNTEREXAMPLE',expected=other,chosen=chosen,variant=variant)
    production.truth(cur)
    production.reverse_output(api,cur,f,result)
    assert next(x for x in api.read(cur,f['batch'])['batch']['production_sources'] if x['balance_type']=='WIP')['remaining_qty_pcs']==8
    return dict(status='PASS',variant=variant,exact_brand=True,linked_inverse_restores_wip=True)


def adjustment_date(cur, today, closed):
    f = probe.invoice.estimated_receipt(cur,today)
    api.admin(cur)
    adjustment = cur.execute('''insert into erp.material_adjustments(adjustment_number,physical_at,location_id,reason_code,notes,status)
        values(%s,%s,%s,'COUNT_CORRECTION','AS ordinary adjustment date probe','DRAFT') returning id''',
        ('AS-'+uuid.uuid4().hex,probe.invoice.at(today-timedelta(days=2),12),f['location'])).fetchone()[0]
    cur.execute('insert into erp.material_adjustment_items(adjustment_id,material_id,roll_id,qty_signed) values(%s,%s,%s,-2)',(adjustment,f['material'],f['roll']))
    api.ordinary(cur);cur.execute('select erp.post_material_adjustment(%s)',(adjustment,))
    if closed:
        cur.execute('select erp.close_accounting_through(%s,%s)',(f['purchase_day'],'AS adjustment close'))
    api.admin(cur)
    version = cur.execute('select row_version from erp.material_purchase_headers where id=%s',(f['purchase'],)).fetchone()[0]
    payload = dict(purchase_id=f['purchase'],supplier_invoice_number='AS-'+uuid.uuid4().hex,invoice_date=f['purchase_day'],
                   received_at=probe.invoice.at(today-timedelta(days=1),15),reason='AS late invoice after stock adjustment',
                   lines=[dict(purchase_item_id=f['item'],qty_invoiced=10,final_unit_price='20.003')])
    probe.invoice.rpc(cur,'erp.finalize_material_purchase_invoice_v2',payload,uuid.uuid4(),version)
    api.admin(cur)
    rows = cur.execute('''select r.effective_date,j.economic_date,j.transaction_date,r.ledger_delta
        from erp.material_adjustment_revaluation_facts r join erp.journal_entries j on j.id=r.journal_entry_id
        where r.adjustment_id=%s order by r.created_at,r.id''',(adjustment,)).fetchall()
    assert rows and all(r[1]==f['purchase_day'] for r in rows), rows
    expected = today if closed else f['purchase_day']
    errors = [r for r in rows if r[0]!=expected or r[2]!=expected]
    # The document invoice date and journal economic date remain the source date.
    doc = cur.execute('select distinct h.id,h.row_version,h.invoice_date from erp.material_supplier_invoices h join erp.material_supplier_invoice_items l on l.invoice_id=h.id join erp.material_purchase_items i on i.id=l.purchase_item_id where i.purchase_id=%s and h.status=\'POSTED\'',(f['purchase'],)).fetchone()
    assert doc[2]==f['purchase_day']
    api.receipts.rpc(api,cur,'reverse_material_supplier_invoice_v2',doc[0],'AS linked invoice inverse',uuid.uuid4(),doc[1])
    api.admin(cur)
    inverse = cur.execute('''select r.effective_date,j.economic_date,j.transaction_date from erp.material_adjustment_revaluation_facts r
        join erp.journal_entries j on j.id=r.journal_entry_id where r.adjustment_id=%s and j.economic_date=%s''',(adjustment,today)).fetchall()
    assert inverse and all(r==(today,today,today) for r in inverse), inverse
    return dict(status='COUNTEREXAMPLE' if errors else 'PASS',closed=closed,recognition_expected=expected,
                economic_date=f['purchase_day'],observations=rows,mismatches=errors,inverse_current_day=True)


def calendar_policy(raw):
    """A separate arithmetic oracle; never rewrite the historical HOLD result."""
    assert raw['status']=='DATE_POLICY_REVIEW_REQUIRED' and not raw['receipt_day_closed']
    initial = dict(MATERIAL_INVENTORY=Decimal(0),WIP=Decimal(85),FG_INVENTORY=Decimal(51),
                   COGS=Decimal(34),AP_SUPPLIER=Decimal(0),GRNI_MATERIAL=Decimal(-100))
    observations=[]
    for stage in raw['observations']:
        assert not stage['mismatches'] and stage['replay_exact']
        differences={}
        for key,field in probe.invoice.REPORT_KEYS.items():
            expected=(Decimal(stage['expected'][key])-initial[key])*(-1 if key in ('AP_SUPPLIER','GRNI_MATERIAL') else 1)
            actual=Decimal(str(stage['historical_report_after']['financial_position'][field]))-Decimal(str(stage['historical_report_before']['financial_position'][field]))
            if actual!=expected:differences[field]=dict(expected=expected,actual=actual)
        expected=Decimal(stage['expected']['COGS'])-initial['COGS']
        actual=Decimal(str(stage['historical_report_after']['performance']['cogs_gl']))-Decimal(str(stage['historical_report_before']['performance']['cogs_gl']))
        if actual!=expected:differences['cogs_gl']=dict(expected=expected,actual=actual)
        for event in stage['state']['revaluation_events']:
            if str(event[1])!=str(raw['purchase_date']):differences['material_event_date']=event
        observations.append(dict(qty=stage['qty'],rate=stage['rate'],mismatches=differences))
    return dict(status='PASS' if all(not x['mismatches'] for x in observations) else 'COUNTEREXAMPLE',
                policy='OPEN_PERIOD_RECOGNIZES_INVOICE_ECONOMIC_DATE',purchase_date=raw['purchase_date'],
                original_status=raw['status'],historical_result_unchanged=True,observations=observations)


def new_cases(cur,today):
    cases=[]
    for closed in (False,True):
        for zone in ('Asia/Jakarta','UTC','Etc/GMT+12','Pacific/Kiritimati'):
            for partial,cost in ((False,'20.003'),(True,'20'),(True,'20.003')):
                cases.append((f'DATE:{closed}:{zone}:{partial}:{cost}',lambda c=closed,z=zone,p=partial,v=cost:probe.invoice_dates(cur,today,z,c,p,v)))
    for variant in ('UNIQUE','AMBIGUOUS','EXPLICIT_SECOND'):
        cases.append(('WIP_IDENTITY:'+variant,lambda v=variant:probe.wip_identity(cur,today,v)))
    cases.append(('STAGED_BS_BRAND_MODEL',lambda:staged_brand(cur,today)))
    for variant in ('BRAND_SECOND','WRONG_BRAND','CONFLICTING_ID','FUTURE_ID'):
        cases.append(('WIP_GUARD:'+variant,lambda v=variant:output_guard(cur,today,v)))
    for closed in (False,True):
        cases.append(('ADJUSTMENT_DATE:'+str(closed),lambda c=closed:adjustment_date(cur,today,c)))
    return cases
