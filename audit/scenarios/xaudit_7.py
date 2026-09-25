"""AUDITOR SCENARIO xaudit_7 rev2 (rev1 3ed20b76 run 36095943675 had a MATERIAL fixture field mistake) (Fable, r8, head 9dd7bc2 / product a095a9d) — independent POSITIVE controls and adversarial
bypass attempts for the BA fixes A1, A3, A6, A9, A10. Oracles from the contract and the ratified addendum
(D02 §4, D03 §5.1–5.3), never from the writer's probe expectations. Writer helpers are used for fixtures only.
Statuses: PASS / COUNTEREXAMPLE / INCOMPLETE. Every case runs in the runtime's rolled-back savepoint."""
from datetime import timedelta
from decimal import Decimal as D
import json,traceback,uuid
import psycopg
import cp6_aw_probe as awp
import cp6_ba_probe as bap
import cp6_opening_overlap_probe as ovp
api,boundary=awp.api,awp.boundary

def attempt(cur,fn):
    api.admin(cur);cur.execute('savepoint xa7')
    try:
        r=fn();cur.execute('release savepoint xa7');api.admin(cur);return r,None
    except psycopg.Error as exc:
        cur.execute('rollback to savepoint xa7');api.admin(cur);return None,dict(sqlstate=exc.sqlstate,message=(exc.diag.message_primary or str(exc))[:300])

def code_of(err):return (err or {}).get('message','').split(':')[0] if err else None

# ---------------------------------------------------------------- A1 (CP6-09)
def second_batch(cur,today,kind,mutate):
    first=ovp.imported(cur,today,kind);api.admin(cur)
    tag,first_batch=cur.execute("""select b.batch_code,b.id from erp.migration_batches b join erp.opening_balance_headers h
      on h.migration_batch_id=b.id where h.id=%s""",(first,)).fetchone()
    code='XA7'+uuid.uuid4().hex[:12]
    batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(today-timedelta(days=1))))['batch_id']
    row,ctl=bap.opening_rows(kind,tag);extra=mutate(cur,batch,row,ctl,tag,code)
    api.upload(cur,batch,'OPENING_BALANCE_ITEM',[row]);api.upload(cur,batch,'OPENING_CONTROL',[ctl])
    before=bap.gl(cur)
    result,error=attempt(cur,lambda:api.invoke(cur,'FINALIZE',batch))
    api.admin(cur)
    headers=cur.execute("select count(*) from erp.opening_balance_headers where migration_batch_id=any(%s::uuid[]) and status='POSTED'",([str(first_batch),str(batch)],)).fetchone()[0]
    return dict(kind=kind,row=row,extra=extra,result=result,error=error,posted_headers=headers,ledger_delta=bap.moved(before,bap.gl(cur)))

def a1_other_material_same_location(cur,today):
    def mutate(cur,batch,row,ctl,tag,code):
        api.upload(cur,batch,'MATERIAL',[dict(material_sku=code,material_name='XA7 other material',material_type='OTHER',unit_code='PCS')]);row['material_sku']=code;return dict(material=code)
    o=second_batch(cur,today,'MATERIAL',mutate)
    ok=o['error'] is None and isinstance(o['result'],dict) and o['result'].get('status')=='POSTED' and o['posted_headers']==2
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',expected='distinct source (another material, same warehouse) must still post: 2 POSTED headers (M:1024 ALL, A1 "sumber berbeda tetap boleh")',**{k:str(v)[:300] for k,v in o.items()})

def a1_same_item_case_whitespace(cur,today):
    def mutate(cur,batch,row,ctl,tag,code):
        row['material_sku']='  '+tag.swapcase()+' ';row['location_code']=' '+tag.swapcase()+'  ';return dict(variant=row['material_sku'])
    o=second_batch(cur,today,'MATERIAL',mutate)
    doubled=o['posted_headers']==2
    return dict(status='COUNTEREXAMPLE' if doubled else 'PASS',refusal_code=code_of(o['error']),
                expected='same physical item written with other case/whitespace must not post twice (refused BA_IMPORT_OPENING_ALREADY_POSTED or by validation); 1 POSTED header, no ledger delta',**{k:str(v)[:300] for k,v in o.items()})

# ---------------------------------------------------------------- A3 (CP6-02) / A10 (CP6-18)
def wip_fixture(cur,today,product=True,brand=True,color=True):
    """Own fixture: 8 identified SEWING pcs; products A (brand A, Blue), B (brand B, Red), C (brand A, Red)."""
    code='XW'+uuid.uuid4().hex[:12]
    batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(today-timedelta(days=8))))['batch_id']
    item=dict(balance_type='WIP',po_number=code,model_code=code,size_code=code,contractor_code=code,stage='SEWING',qty='8',
              unit_cost='5',amount='40.00',opening_source_key='WIP',control_key='WIP',accessory_cost_included='true')
    if product:item['product_sku']=code+'A'
    if brand:item['brand_code']=code+'A'
    if color:item['color_name']='Blue'
    rows={'MODEL':[dict(model_code=code,model_name='XA7 model')],'SIZE':[dict(size_code=code)],
          'BRAND':[dict(brand_code=code+'A',brand_name='XA7 brand A'),dict(brand_code=code+'B',brand_name='XA7 brand B')],
          'PRODUCT':[dict(sku=code+s,product_name='XA7 '+s,model_code=code,brand_code=code+b,color_name=c,size_code=code) for s,b,c in (('A','A','Blue'),('B','B','Red'),('C','A','Red'))],
          'CONTRACTOR':[dict(contractor_code=code,contractor_name='XA7 holder',contractor_type='MANDOR')],
          'LOCATION':[dict(location_code=code,location_name='XA7 FG',location_type='FG_WAREHOUSE')],
          'OPEN_PO':[dict(po_number=code,model_code=code,contractor_code=code,target_qty_pcs='8',status='SEWING',current_stage='SEWING')],
          'OPENING_BALANCE_ITEM':[item],'OPENING_CONTROL':[dict(control_key='WIP',balance_type='WIP',qty='8',amount='40.00')]}
    for entity,payloads in rows.items():api.upload(cur,batch,entity,payloads)
    checked=api.invoke(cur,'VALIDATE',batch)
    if checked.get('error_rows')!=0:
        raise AssertionError(('XA7_WIP_FIXTURE_REFUSED',cur.execute("select entity_type,validation_errors::text from erp.migration_staging_rows where batch_id=%s and validation_status='ERROR'",(batch,)).fetchall()))
    posted=api.invoke(cur,'FINALIZE',batch);assert posted.get('status')=='POSTED',posted
    src=bap.wip_source(cur,dict(batch=batch))
    return dict(batch=batch,code=code,po=src['po_id'])

def output(cur,fx,day,qty,sku_suffix,brand_suffix=None):
    src=bap.wip_source(cur,fx)
    p=dict(batch_id=fx['batch'],opening_item_id=src['opening_item_id'],expected_remaining=str(src['remaining_qty_pcs']),operation='COMPLETE',
           qty_pcs=str(qty),product_sku=fx['code']+sku_suffix,location_code=fx['code'],date=str(day),reason='XA7 output')
    if brand_suffix:p['brand_code']=fx['code']+brand_suffix
    return api.call(cur,'WIP_OUTPUT',p)

def lot_product(cur,result):
    api.admin(cur);return str(cur.execute('select product_id from erp.fg_lots where id=%s',(result['lot_id'],)).fetchone()[0]) if result else None

def a3_partial_reversal(cur,today,qty):
    fx=wip_fixture(cur,today)
    first=output(cur,fx,today-timedelta(days=3),5,'A')
    bap.wip_reverse(cur,fx,first)   # the 5 pcs come back today
    result,error=attempt(cur,lambda:output(cur,fx,today-timedelta(days=1),qty,'A'))
    minimum,timeline=bap.sewing_timeline(cur,fx['po'])
    if qty<=3:
        ok=error is None and result is not None and minimum>=0
        return dict(status='PASS' if ok else 'COUNTEREXAMPLE',error=error,sewing_minimum=minimum,timeline=timeline[-6:],
                    expected='3 pcs never left the stage: a completion of 3 dated d-1 (after a 5-pc output at d-3 reversed today) must POST with a non-negative physical timeline')
    ok=error is not None and code_of(error)=='BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING' and minimum>=0
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',error=error,sewing_minimum=minimum,timeline=timeline[-6:],
                expected='4 pcs dated d-1 exceed the 3 pcs present on d-1 (the 5 returned only today): refused BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING, timeline unchanged (M:3816-3823, SI-02)')

def a10_bound_sku_a_brand_b(cur,today):
    fx=wip_fixture(cur,today)
    result,error=attempt(cur,lambda:output(cur,fx,today-timedelta(days=2),4,'A','B'))
    posted=lot_product(cur,result);a=bap.product_of(cur,fx,'A')
    ok=error is not None or posted==a
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',error=error,posted_product=posted,product_a=a,
                expected='bound source (product A): a payload naming SKU A with brand B must be refused or resolve to A; never another product (D03 §5.1)')

def a10_unbound_brand_match_color_mismatch(cur,today):
    fx=wip_fixture(cur,today,product=False)          # source: brand A, Blue
    result,error=attempt(cur,lambda:output(cur,fx,today-timedelta(days=2),4,'C','A'))   # product C: brand A, Red
    ok=error is not None and code_of(error)=='BA_WIP_OUTPUT_SOURCE_MISMATCH'
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',error=error,posted_product=lot_product(cur,result),
                expected='unbound source with brand A/Blue: product C (brand A, Red) contradicts the colour -> BA_WIP_OUTPUT_SOURCE_MISMATCH (D03 §5.2)')

def a10_unbound_brand_only_color_unknown(cur,today):
    fx=wip_fixture(cur,today,product=False,color=False)   # source: brand A only
    result,error=attempt(cur,lambda:output(cur,fx,today-timedelta(days=2),4,'C','A'))
    rec=bap.identity(cur,result['output_id']) if result else None
    ok=error is None and rec is not None and rec['basis']=='SOURCE_ATTRIBUTES' and 'BRAND' in rec['checked'] and 'COLOR' in rec['unknown'] and 'COLOR' not in rec['checked']
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',error=error,identity_record=rec,
                expected='source names only brand A: product C (brand A, Red) posts; provenance basis SOURCE_ATTRIBUTES, BRAND checked, COLOR recorded as unknown (never as matched) (D03 §5.3)')

def a10_bound_same_product_posts(cur,today):
    fx=wip_fixture(cur,today)
    result,error=attempt(cur,lambda:output(cur,fx,today-timedelta(days=2),4,'A'))
    rec=bap.identity(cur,result['output_id']) if result else None
    ok=error is None and lot_product(cur,result)==bap.product_of(cur,fx,'A') and rec is not None and rec['basis']=='OPENING_PRODUCT'
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',error=error,identity_record=rec,expected='positive control: bound product A completed as A posts with basis OPENING_PRODUCT')

# ---------------------------------------------------------------- A9 (CP6-07, D02)
def a9_same_day(cur,today,kind,use_offset):
    fx=bap.advance_fixture(cur,today,kind)
    correction_day=today-timedelta(days=2);use_day=today-timedelta(days=use_offset)
    bap.prepay(cur,fx,'CORRECT',amount='100.00',effective_date=str(correction_day))
    result,error=attempt(cur,lambda:bap.prepay(cur,fx,'REFUND',amount='100.00',effective_date=str(use_day),cash_account_id=str(fx['cash'])))
    days=sorted({fx['cutover'],use_day,correction_day,today});bal={str(d):str(bap.advance_asof(cur,fx,d)) for d in days}
    if use_offset==2:
        ok=error is None and all(D(v)>=0 for v in bal.values())
        return dict(status='PASS' if ok else 'COUNTEREXAMPLE',error=error,asof=bal,expected='refund 100 dated ON the correction day (capacity 100 that day) posts; no negative dated balance (D02 §4)')
    ok=error is not None and code_of(error)=='BA_ADVANCE_DATED_CAPACITY' and all(D(v)>=0 for v in bal.values())
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',error=error,asof=bal,expected='refund 100 dated one day BEFORE the correction (capacity 67.25) refused BA_ADVANCE_DATED_CAPACITY, balances unchanged (D02 §4)')

# ---------------------------------------------------------------- A6 (CP6-24)
def a6_close_next_day(cur,today):
    d1=today-timedelta(days=2);d2=today-timedelta(days=1);d0=today-timedelta(days=4)
    boundary.historical.prior.set_open_period(cur,d0-timedelta(days=1))
    awp.quiet_seed(cur,d0,d2)
    ready=awp.preflight(cur,d1)
    if ready is None or ready['status']!='READY':return dict(status='INCOMPLETE',reason='fixture not READY',blockers=awp.blockers_brief(ready))
    first=awp.close(cur,d1,'XA7 close d1')
    if first[0]!='ACCEPTED':return dict(status='INCOMPLETE',reason='first close refused',first=first)
    ready2=awp.preflight(cur,d2)
    if ready2 is None or ready2['status']!='READY':return dict(status='INCOMPLETE',reason='d2 not READY',blockers=awp.blockers_brief(ready2))
    second=awp.close(cur,d2,'XA7 close d2 after d1')
    f1,f2=bap.filings(cur,d1),bap.filings(cur,d2)
    ok=second[0]=='ACCEPTED' and f1==1 and f2==1
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',second=second[0],second_error=second[1],filings_d1=f1,filings_d2=f2,
                expected='closing the NEXT date after a close still files (exactly one filing per date); CLOSE_ALREADY_CLOSED only for the same date (S06, A6)')

def cases(cur,today):
    def wrap(fn,*a):
        def run():
            try:return fn(cur,today,*a)
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:900],traceback=traceback.format_exc()[-1200:])
        return run
    return [('XA7:A1_OTHER_MATERIAL_SAME_WAREHOUSE_POSTS',wrap(a1_other_material_same_location)),
            ('XA7:A1_SAME_ITEM_CASE_WHITESPACE_NOT_DOUBLED',wrap(a1_same_item_case_whitespace)),
            ('XA7:A3_PARTIAL_REVERSAL_3_OF_3_POSTS',wrap(a3_partial_reversal,3)),
            ('XA7:A3_PARTIAL_REVERSAL_4_OF_3_REFUSED',wrap(a3_partial_reversal,4)),
            ('XA7:A10_BOUND_SKU_A_BRAND_B_NOT_OTHER_PRODUCT',wrap(a10_bound_sku_a_brand_b)),
            ('XA7:A10_UNBOUND_BRAND_MATCH_COLOR_MISMATCH_REFUSED',wrap(a10_unbound_brand_match_color_mismatch)),
            ('XA7:A10_UNBOUND_BRAND_ONLY_COLOR_UNKNOWN_POSTS',wrap(a10_unbound_brand_only_color_unknown)),
            ('XA7:A10_BOUND_SAME_PRODUCT_POSTS',wrap(a10_bound_same_product_posts)),
            ('XA7:A9_SUPPLIER_REFUND_ON_CORRECTION_DAY_POSTS',wrap(a9_same_day,'SUPPLIER',2)),
            ('XA7:A9_SUPPLIER_REFUND_DAY_BEFORE_CORRECTION_REFUSED',wrap(a9_same_day,'SUPPLIER',3)),
            ('XA7:A9_VENDOR_REFUND_DAY_BEFORE_CORRECTION_REFUSED',wrap(a9_same_day,'VENDOR',3)),
            ('XA7:A6_CLOSE_NEXT_DATE_AFTER_CLOSE_FILES',wrap(a6_close_next_day))]
