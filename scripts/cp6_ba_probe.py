"""BA T1_FAMILY probe: product fixes of the independent CP6 audit (writer handoff AUDIT_WRITER_HANDOFF_CP6.md, 25 Sep 2026)
and the owner decisions D02/D03 (OWNER_CONFIRMED_CHAT, 25 Sep 2026, option A), before and after.

Label T1_FAMILY: targeted family evidence on the disposable chain AN -> AU -> AV -> AW -> AX -> AY -> AZ (+ BA in phase
'after'), never release evidence. Oracles come from the audit findings, the auditor's own scenarios and the owner decisions,
never from observed behaviour:
  A1 (CP6-09) a second import batch that re-declares an opening item another import batch already posted (same material,
     warehouse and roll; same product, warehouse and grade; same cash account; WIP/BS without a PO source by model, stage
     and holder) doubled stock, value or cash. Expected: refused BA_IMPORT_OPENING_ALREADY_POSTED, nothing changes; another
     warehouse stays admissible.
  A3 (CP6-02, auditor SI-02) a completion dated before an earlier output's reversal used the pieces the reversal returned
     later (the sewing timeline went negative). Expected: refused BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING; a completion on or
     after the reversal day, and a backdated one that fits every later day, post with a non-negative physical timeline.
  A10 (CP6-18, auditor SI-01, D03=A) opening WIP of product A (brand A, Blue) completed as product B (brand B, Red).
     Expected: refused BA_WIP_OUTPUT_PRODUCT_BOUND; without a product on the source, a brand/colour that contradicts the
     source row is refused BA_WIP_OUTPUT_SOURCE_MISMATCH; the same product, a matching unbound source and an unbound source
     without attributes post, and each output records what was checked and what stayed unknown.
  A9 (CP6-07, auditor BCR1 advance cases, D02=A) a refund or use of an opening advance dated before the correction that
     funds it made the dated advance balance negative. Expected: refused BA_ADVANCE_DATED_CAPACITY; the ordered sequence
     posts (auditor's ordered control). Same rule for stock (AUD-S04), already enforced before BA: a transfer out of a
     warehouse dated before the stock arrived there is refused AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY in
     both phases (regression control); after the arrival it posts.
  A4 (CP6-03, auditor BLIND-MONEY-CENT cases, M:3816-3825) one unit received, cut, then corrected or invoiced 10.005 <-> 10.014:
     material inventory must be 0.00 at zero stock and WIP the endpoint-rounded unit (10.01, half away from zero).
  A5 (CP6-04, auditor XA2/XI selector cases) an old claimable Laundry delivery after 100 newer ones, and the oldest of 51
     import drafts, were missing from what the pages can select. Expected: both listed.
  A6 (CP6-24) a second close of the date already closed filed twice. Expected: refused CLOSE_ALREADY_CLOSED with one filing;
     a close after a reopen still files.
Phase 'before' must show every finding (COUNTEREXAMPLE) and pass every control; phase 'after' must pass every case. A
refusal in 'before', or a refusal with another message in 'after', is INCOMPLETE; r1.peer.attempt proves every refusal left
the complete boundary unchanged. Each case runs inside the group's rolled-back savepoint; nothing is committed to the clone.
"""
from datetime import timedelta
from decimal import Decimal,ROUND_HALF_UP
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess,sys,traceback,uuid
import psycopg

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_aw_probe as awp
import cp6_ax_probe as axp
import cp6_ay_probe as ayp
import cp6_az_probe as azp
import cp6_ba_build as ba
import cp6_opening_overlap_probe as ovp
r1,api,boundary,prior,chain=awp.r1,awp.api,awp.boundary,awp.prior,awp.chain

OUT=AUDITOR/'cp6-proof/ba'
BA_SQL=AUDITOR/'supabase/dev/cp6_ba_t1_family.sql'
LABEL='T1_FAMILY'
FUNCTIONS=tuple(ba.REPLACED)+tuple(ba.NEW_FUNCTIONS)
D=Decimal


def dev_source(signature):
    """The body of one BA function exactly as the committed dev file defines it."""
    name=signature.split('(')[0]
    text=BA_SQL.read_text()
    head=re.search(r'(?i)create or replace function '+re.escape(name)+r'\(',text).start()
    start=re.compile(r'(?i)\bas \$function\$').search(text,head).end();end=text.index('$function$;',start)
    return text[start:end]


def ba_installed(cur):
    return cur.execute('select count(*) from erp.schema_migrations where version=%s',(ba.VERSION,)).fetchone()[0]==1


def ba_verified(cur):
    base=azp.az_verified(cur)
    assert ba_installed(cur),'BA_T1_MARKER'
    for signature in FUNCTIONS:
        src=cur.execute('select prosrc from pg_proc where oid=%s::regprocedure',(signature,)).fetchone()[0]
        assert src==dev_source(signature),('BA_T1_FUNCTION_NOT_CURRENT',signature)
    for table in ba.NEW_TABLES:
        assert cur.execute('select to_regclass(%s) is not null',('erp.'+table,)).fetchone()[0],('BA_T1_TABLE_MISSING',table)
    return dict(base,stage='AV_PLUS_AW_AX_AY_AZ_BA_T1',ba_sql_sha256=hashlib.sha256(BA_SQL.read_bytes()).hexdigest(),ba_functions=list(FUNCTIONS))


def install_ba():
    with psycopg.connect(boundary.PG,autocommit=True) as conn,conn.cursor() as cur:cur.execute(BA_SQL.read_text(),prepare=False)
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        result=ba_verified(cur);conn.rollback()
    return result


# ---------------------------------------------------------------- shared outcome rules

def code_of(error):
    """The product code a refusal message starts with ('BA_X: ...', 'AM_X for material ...')."""
    m=re.match(r'[A-Z][A-Z0-9_]+',(error or {}).get('message') or '')
    return m.group(0) if m else ''


def finding(cur,code,result,error,harm,**evidence):
    """A finding: without BA it must post and show the harm (COUNTEREXAMPLE); with BA it must be refused with the exact code
    (r1.peer.attempt already proved the refusal atomic). Anything else is INCOMPLETE, a post with BA is FAIL."""
    if ba_installed(cur):
        status='PASS' if error is not None and code_of(error)==code else ('FAIL' if error is None else 'INCOMPLETE')
    else:
        status='COUNTEREXAMPLE' if error is None and harm else 'INCOMPLETE'
    return dict(evidence,status=status,expected_refusal=code if ba_installed(cur) else None,refusal=error,
                result=result,harm_observed=harm if error is None else None)


def control(cur,ok,error,**evidence):
    """A positive control: posts and meets its checks in both phases."""
    status='PASS' if error is None and ok else ('FAIL' if ba_installed(cur) and error is None else 'INCOMPLETE')
    return dict(evidence,status=status,refusal=error)


def gl(cur):
    api.admin(cur)
    return {str(a):D(str(v)) for a,v in cur.execute("""select l.account_id,sum(l.debit-l.credit) from erp.journal_lines l
      join erp.journal_entries j on j.id=l.journal_entry_id and j.status in('POSTED','REVERSED') group by 1""").fetchall()}


def moved(before,after):
    return {k:str(after.get(k,D(0))-before.get(k,D(0))) for k in set(before)|set(after) if after.get(k,D(0))!=before.get(k,D(0))}


def plain(value):
    if isinstance(value,dict):return {str(k):plain(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [plain(v) for v in value]
    if isinstance(value,(D,uuid.UUID)):return str(value)
    if hasattr(value,'isoformat'):return value.isoformat()
    return value


# ---------------------------------------------------------------- A1 import identity across batches

def opening_rows(kind,tag):
    """The opening item and control of cp6_opening_overlap_probe.imported for `kind`, naming its masters by `tag`."""
    row=dict(balance_type=kind,control_key='CHECK');control=dict(balance_type=kind,control_key='CHECK',amount='17.25')
    if kind=='CASH_BANK':row.update(cash_account_code=tag,amount='17.25')
    elif kind=='MATERIAL':
        row.update(material_sku=tag,location_code=tag,qty='7',unit_cost='2.25');control.update(qty='7',amount='15.75')
    elif kind in('FINISHED_GOODS','BS'):
        row.update(product_sku=tag,location_code=tag,qty='7');control.update(qty='7',amount='15.75' if kind=='FINISHED_GOODS' else '0')
        if kind=='FINISHED_GOODS':row['unit_cost']='2.25'
    elif kind=='WIP':row.update(model_code=tag,stage='SEWING',amount='17.25')
    else:raise AssertionError(kind)
    return row,control


def import_overlap(cur,today,kind,cutover_days=1,other_location=False):
    first=ovp.imported(cur,today,kind)
    api.admin(cur)
    tag,first_batch=cur.execute("""select b.batch_code,b.id from erp.migration_batches b join erp.opening_balance_headers h
      on h.migration_batch_id=b.id where h.id=%s""",(first,)).fetchone()
    code='BA1'+uuid.uuid4().hex[:12]
    batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(today-timedelta(days=cutover_days))))['batch_id']
    row,ctl=opening_rows(kind,tag)
    if other_location:
        api.upload(cur,batch,'LOCATION',[dict(location_code=code,location_name='BA second warehouse',
            location_type='RAW_MATERIAL_WAREHOUSE' if kind=='MATERIAL' else 'FG_WAREHOUSE')])
        row['location_code']=code
    api.upload(cur,batch,'OPENING_BALANCE_ITEM',[row]);api.upload(cur,batch,'OPENING_CONTROL',[ctl])
    before=gl(cur)
    result,error=r1.peer.attempt(cur,lambda:api.invoke(cur,'FINALIZE',batch))
    api.admin(cur)
    headers=cur.execute("select count(*) from erp.opening_balance_headers where migration_batch_id=any(%s::uuid[]) and status='POSTED'",
                        ([str(first_batch),str(batch)],)).fetchone()[0]
    evidence=dict(kind=kind,second_cutover=str(today-timedelta(days=cutover_days)),other_location=other_location,
                  posted_headers=headers,ledger_delta=moved(before,gl(cur)),finalize=result)
    if other_location:
        return control(cur,isinstance(result,dict) and result.get('status')=='POSTED' and headers==2,error,**evidence)
    return finding(cur,'BA_IMPORT_OPENING_ALREADY_POSTED',None,error,
                   isinstance(result,dict) and result.get('status')=='POSTED' and headers==2,**evidence)


# ---------------------------------------------------------------- A3/A10 opening WIP outputs

def wip_batch(cur,today,product=True,attributes=True):
    """Eight identified, valued SEWING pcs (the auditor's SI fixture) and two same-model/size products: A (brand A, Blue)
    and B (brand B, Red). product: the WIP row names product A; attributes: it names brand A and Blue."""
    code='BW'+uuid.uuid4().hex[:12]
    batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(today-timedelta(days=8))))['batch_id']
    item=dict(balance_type='WIP',po_number=code,model_code=code,size_code=code,contractor_code=code,stage='SEWING',qty='8',
              unit_cost='5',amount='40.00',opening_source_key='WIP',control_key='WIP',accessory_cost_included='true')
    if product:item['product_sku']=code+'A'
    if attributes:item.update(brand_code=code+'A',color_name='Blue')
    rows={'MODEL':[dict(model_code=code,model_name='BA WIP model')],'SIZE':[dict(size_code=code)],
          'BRAND':[dict(brand_code=code+'A',brand_name='BA source brand'),dict(brand_code=code+'B',brand_name='BA other brand')],
          'PRODUCT':[dict(sku=code+s,product_name='BA '+s,model_code=code,brand_code=code+s,color_name=c,size_code=code) for s,c in (('A','Blue'),('B','Red'))],
          'CONTRACTOR':[dict(contractor_code=code,contractor_name='BA WIP holder',contractor_type='MANDOR')],
          'LOCATION':[dict(location_code=code,location_name='BA FG',location_type='FG_WAREHOUSE')],
          'OPEN_PO':[dict(po_number=code,model_code=code,contractor_code=code,target_qty_pcs='8',status='SEWING',current_stage='SEWING')],
          'OPENING_BALANCE_ITEM':[item],'OPENING_CONTROL':[dict(control_key='WIP',balance_type='WIP',qty='8',amount='40.00')]}
    for entity,payloads in rows.items():api.upload(cur,batch,entity,payloads)
    checked=api.invoke(cur,'VALIDATE',batch)
    if checked.get('error_rows')!=0:
        errors=cur.execute("select entity_type,validation_errors::text from erp.migration_staging_rows where batch_id=%s and validation_status='ERROR'",(batch,)).fetchall()
        raise AssertionError(('BA_WIP_FIXTURE_REFUSED',checked,errors))
    posted=api.invoke(cur,'FINALIZE',batch)
    assert posted.get('status')=='POSTED',('BA_WIP_FIXTURE_NOT_POSTED',posted)
    source=wip_source(cur,dict(batch=batch))
    return dict(batch=batch,code=code,item=source['opening_item_id'],po=source['po_id'])


def wip_source(cur,fx):
    sources=api.read(cur,fx['batch'])['batch']['production_sources']
    assert len(sources)==1,('BA_WIP_FIXTURE_SOURCES',sources)
    return sources[0]


def wip_output(cur,fx,day,qty,suffix='A'):
    source=wip_source(cur,fx)
    return api.call(cur,'WIP_OUTPUT',dict(batch_id=fx['batch'],opening_item_id=source['opening_item_id'],
        expected_remaining=str(source['remaining_qty_pcs']),operation='COMPLETE',qty_pcs=str(qty),product_sku=fx['code']+suffix,
        brand_code=fx['code']+suffix,location_code=fx['code'],date=str(day),reason='BA probe opening WIP output'))


def wip_reverse(cur,fx,output):
    source=wip_source(cur,fx)
    return api.call(cur,'WIP_OUTPUT',dict(batch_id=fx['batch'],opening_item_id=source['opening_item_id'],
        expected_remaining=str(source['remaining_qty_pcs']),operation='REVERSE',output_id=output['output_id'],
        reason='BA probe WIP output reversed today'))


def sewing_timeline(cur,po):
    """The auditor's SI-02 oracle: SEWING pieces after every physical event of the PO (physical time, then creation)."""
    api.admin(cur)
    rows=cur.execute("""with e as (select id,physical_at,created_at,source_type,
          case when stage_to='SEWING' then qty_pcs else 0 end-case when stage_from='SEWING' then qty_pcs else 0 end delta
        from erp.wip_stage_events where po_id=%s)
      select physical_at,source_type,delta,sum(delta) over(order by physical_at,created_at,id) from e order by physical_at,created_at,id""",(po,)).fetchall()
    return min(r[3] for r in rows),[[str(v) for v in r] for r in rows]


def identity(cur,output_id):
    api.admin(cur)
    row=cur.execute("""select basis,opening_product_id,output_product_id,checked,unknown,source_attributes
      from erp.initial_import_wip_output_identity_v1 where output_id=%s""",(output_id,)).fetchone() if ba_installed(cur) else None
    return None if row is None else dict(zip(('basis','opening_product_id','output_product_id','checked','unknown','source_attributes'),plain(list(row))))


def product_of(cur,fx,suffix):
    api.admin(cur)
    return str(cur.execute('select id from erp.products where sku=%s',(fx['code']+suffix,)).fetchone()[0])


def a3_before_reversal(cur,today):
    fx=wip_batch(cur,today)
    first=wip_output(cur,fx,today-timedelta(days=3),8)
    wip_reverse(cur,fx,first)
    result,error=r1.peer.attempt(cur,lambda:wip_output(cur,fx,today-timedelta(days=1),8))
    minimum,timeline=sewing_timeline(cur,fx['po'])
    return finding(cur,'BA_WIP_OUTPUT_EXCEEDS_DATED_REMAINING',result,error,minimum<0,sewing_minimum=minimum,timeline=timeline,
                   oracle='SI-02: SEWING pieces never negative on the physical timeline; the pieces came back only today')


def a3_after_reversal(cur,today):
    """Control with BA. Without BA it records whether the output dated on the reversal day lands before the reversal on
    the physical timeline (its physical time comes from erp.product_opening_physical_at, not from the reversal): an
    observation, planned PASS or COUNTEREXAMPLE."""
    fx=wip_batch(cur,today)
    first=wip_output(cur,fx,today-timedelta(days=3),8)
    wip_reverse(cur,fx,first)
    result,error=r1.peer.attempt(cur,lambda:wip_output(cur,fx,today,8))
    minimum,timeline=sewing_timeline(cur,fx['po'])
    out=control(cur,result is not None and minimum>=0,error,sewing_minimum=minimum,timeline=timeline,output=result,
                oracle='completion on the reversal day posts; the physical timeline stays non-negative within the day')
    if not ba_installed(cur) and error is None and minimum<0:out['status']='COUNTEREXAMPLE'
    return out


def a3_backdated_fits(cur,today):
    fx=wip_batch(cur,today)
    wip_output(cur,fx,today-timedelta(days=1),3)
    result,error=r1.peer.attempt(cur,lambda:wip_output(cur,fx,today-timedelta(days=3),5))
    minimum,timeline=sewing_timeline(cur,fx['po'])
    return control(cur,result is not None and minimum>=0,error,sewing_minimum=minimum,timeline=timeline,output=result,
                   oracle='a backdated completion that fits every later day (5 of 8, 3 more later) posts')


def a10_output(cur,today,product,attributes,suffix,code=None):
    fx=wip_batch(cur,today,product,attributes)
    result,error=r1.peer.attempt(cur,lambda:wip_output(cur,fx,today-timedelta(days=2),4,suffix))
    evidence=dict(opening_product=product,source_attributes=attributes,output_suffix=suffix,
                  output_product=product_of(cur,fx,suffix),source_product=product_of(cur,fx,'A') if product else None)
    if code:
        # Finding: the output took another product, brand or colour than its source names.
        harm=result is not None and cur.execute('select product_id from erp.fg_lots where id=%s',(result['lot_id'],)).fetchone()[0]!=uuid.UUID(product_of(cur,fx,'A'))
        return finding(cur,code,result,error,harm,**evidence)
    record=identity(cur,result['output_id']) if result else None
    expected={(True,True):('OPENING_PRODUCT',['PRODUCT_IDENTITY','PO_MODEL','SIZE'],[]),
              (False,True):('SOURCE_ATTRIBUTES',['PO_MODEL','SIZE','BRAND','COLOR'],['PATTERN','MATERIAL']),
              (False,False):('ASSIGNED_AT_COMPLETION',['PO_MODEL','SIZE'],['BRAND','COLOR','PATTERN','MATERIAL'])}[(product,attributes)]
    recorded=record is not None and (record['basis'],record['checked'],record['unknown'])==expected \
        and record['output_product_id']==evidence['output_product'] and record['opening_product_id']==evidence['source_product']
    return control(cur,result is not None and (recorded if ba_installed(cur) else True),error,identity_record=record,
                   expected_identity=expected if ba_installed(cur) else None,output=result,**evidence)


# ---------------------------------------------------------------- A9 dated advance capacity, AUD-S04 dated stock

def advance_fixture(cur,today,kind,target=False):
    """The auditor's BCR1 fixture: bank 100, opening advance 67.25 (100 original, 32.75 settled before cutover) on its own
    account; `target`: an opening payable/receivable of 100 for the same party to use the advance on."""
    cutover=today-timedelta(days=8)
    boundary.historical.prior.set_open_period(cur,cutover-timedelta(days=1))
    code='BAV'+uuid.uuid4().hex[:12]
    batch=api.call(cur,'CREATE',dict(batch_code=code,cutover_date=str(cutover)))['batch_id']
    entity,field,name,extra={'SUPPLIER':('SUPPLIER','supplier_code','supplier_name',dict(supplier_type='MATERIAL')),
        'CUSTOMER':('CUSTOMER','customer_code','customer_name',{}),'VENDOR':('LAUNDRY_VENDOR','vendor_code','vendor_name',{})}[kind]
    customer=kind=='CUSTOMER'
    api.upload(cur,batch,entity,[dict({field:code,name:'BA advance party'},**extra)])
    api.upload(cur,batch,'CHART_ACCOUNT',[dict(account_code=code+'B',account_name='BA bank',account_type='ASSET',report_group='CURRENT_ASSETS',normal_balance='DEBIT'),
        dict(account_code=code+'A',account_name='BA advance',account_type='LIABILITY' if customer else 'ASSET',
             report_group='CURRENT_LIABILITIES' if customer else 'CURRENT_ASSETS',normal_balance='CREDIT' if customer else 'DEBIT')])
    api.upload(cur,batch,'CASH_ACCOUNT',[dict(cash_account_code=code,cash_account_name='BA bank',coa_account_code=code+'B',account_kind='BANK')])
    items=[dict(balance_type='CASH_BANK',cash_account_code=code,amount='100.00',control_key='BANK')]
    controls=[dict(control_key='BANK',balance_type='CASH_BANK',amount='100.00'),dict(control_key='ADV',balance_type=kind+'_ADVANCE',amount='67.25')]
    if target:
        balance={'SUPPLIER':'SUPPLIER_PAYABLE','CUSTOMER':'CUSTOMER_RECEIVABLE','VENDOR':'VENDOR_PAYABLE'}[kind]
        items.append({'balance_type':balance,field:code,'amount':'100.00','control_key':'TARGET'})
        controls.append(dict(control_key='TARGET',balance_type=balance,amount='100.00'))
    api.upload(cur,batch,'OPENING_BALANCE_ITEM',items)
    api.upload(cur,batch,'OPENING_ADVANCE',[dict(party_type=kind,party_code=code,coa_account_code=code+'A',document_number=code+'DEP',
        document_date=str(cutover-timedelta(days=30)),original_amount='100.00',settled_before_cutover='32.75',amount='67.25',control_key='ADV')])
    api.upload(cur,batch,'OPENING_CONTROL',controls)
    checked=api.invoke(cur,'VALIDATE',batch)
    if checked.get('error_rows')!=0:
        errors=cur.execute("select entity_type,validation_errors::text from erp.migration_staging_rows where batch_id=%s and validation_status='ERROR'",(batch,)).fetchall()
        raise AssertionError(('BA_ADVANCE_FIXTURE_REFUSED',checked,errors))
    posted=api.invoke(cur,'FINALIZE',batch)
    assert posted.get('status')=='POSTED',('BA_ADVANCE_FIXTURE_NOT_POSTED',posted)
    api.admin(cur)
    advance,account=cur.execute('select id,coa_account_id from erp.initial_import_prepayments where batch_id=%s',(batch,)).fetchone()
    cash=cur.execute('select id from erp.cash_accounts where cash_account_code=%s',(code,)).fetchone()[0]
    fx=dict(batch=batch,advance=advance,account=account,cash=cash,cutover=cutover,kind=kind)
    if target:
        fx['target']=cur.execute("select id from erp.initial_prepayment_targets_v1(%s) where target_kind='OPENING'",(advance,)).fetchone()[0]
    return fx


def prepay(cur,fx,operation,**fields):
    return api.call(cur,'PREPAYMENT',dict(batch_id=fx['batch'],expected_revision=api.read(cur,fx['batch'])['batch']['revision'],
        advance_id=fx['advance'],operation=operation,reason='BA probe advance '+operation.lower(),**fields))


def advance_asof(cur,fx,day):
    """The auditor's oracle: the advance account's dated balance (account_daily_balances), in the advance's own direction."""
    api.admin(cur)
    value=D(str(cur.execute('select coalesce(sum(debit_total-credit_total),0) from erp.account_daily_balances where account_id=%s and balance_date<=%s',
                            (fx['account'],day)).fetchone()[0]))
    return -value if fx['kind']=='CUSTOMER' else value


def a9_advance(cur,today,kind,operation,backdated):
    """Correction to 100 (+32.75) and a refund/use of 100: ordered (correction first by date) or backdated (the refund/use
    dated two days before the correction that funds it; submitted after it, as in the auditor's case)."""
    fx=advance_fixture(cur,today,kind,target=operation=='APPLY')
    correction_day=today-timedelta(days=2 if backdated else 4)
    use_day=today-timedelta(days=4 if backdated else 2)
    prepay(cur,fx,'CORRECT',amount='100.00',effective_date=str(correction_day))
    fields=dict(amount='100.00',effective_date=str(use_day))
    if operation=='REFUND':fields['cash_account_id']=str(fx['cash'])
    else:fields['target_id']=str(fx['target'])
    result,error=r1.peer.attempt(cur,lambda:prepay(cur,fx,operation,**fields))
    days=sorted({fx['cutover'],use_day,correction_day,today})
    balances={str(day):advance_asof(cur,fx,day) for day in days}
    evidence=dict(kind=kind,operation=operation,correction_day=str(correction_day),use_day=str(use_day),advance_asof=plain(balances))
    if backdated:
        return finding(cur,'BA_ADVANCE_DATED_CAPACITY',result,error,any(v<0 for v in balances.values()),**evidence,
                       oracle='D02=A: a refund/use needs the capacity it has on its own date and every later day')
    expected={str(day):D('67.25')+(D('32.75') if day>=correction_day else 0)-(D('100.00') if day>=use_day else 0) for day in days}
    return control(cur,balances==expected,error,expected_asof=plain(expected),**evidence)


def stock_history(cur,material,location,roll):
    api.admin(cur)
    rows=cur.execute("""select physical_at,movement_type,qty_signed,sum(qty_signed) over(order by physical_at,system_created_at,id)
      from erp.material_stock_movements where material_id=%s and location_id=%s and roll_id is not distinct from %s
      order by physical_at,system_created_at,id""",(material,location,roll)).fetchall()
    return min([r[3] for r in rows] or [D(0)]),[[str(v) for v in r] for r in rows]


def transfer(cur,source,destination,material,roll,qty,at):
    prod=chain.production
    prod.owner(cur)
    draft=cur.execute('select erp.save_material_transfer_draft_v2(%s::jsonb,%s,%s)',(json.dumps(dict(transfer_number='BA-TR-'+uuid.uuid4().hex[:20],
        from_location_id=str(source),to_location_id=str(destination),physical_at=at.isoformat(),change_reason='BA probe warehouse transfer',
        items=[dict(material_id=str(material),roll_id=str(roll),qty=qty)])),uuid.uuid4(),None)).fetchone()[0]
    prod.owner(cur)
    posted=cur.execute('select erp.post_material_transfer_v2(%s,%s,%s,%s)',(uuid.UUID(draft['material_transfer_id']),uuid.uuid4(),
        int(draft['row_version']),'BA probe warehouse transfer post')).fetchone()[0]
    api.admin(cur)
    return posted


def s04_transfer_back(cur,today,before_arrival):
    """AUD-S04 (D02=A for stock), regression control in both phases: 10 units received in warehouse L on d-4, moved L -> A
    on d-2; then 5 moved back A -> L dated d-3 (before they arrived in A: the current balance of A allows it, its history on
    d-3 does not) or d-1. The material recalculation (AO erp._recalculate_material_cost_core) already refuses the first
    with AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY (native 'before' run 36085934997), so BA changes nothing
    here; the case keeps that refusal and the history of A non-negative in both phases."""
    prod=chain.production
    boundary.historical.prior.set_open_period(cur,today-timedelta(days=5))
    fx=azp.final_receipt(cur,today-timedelta(days=4))
    api.admin(cur)
    roll=cur.execute('select id from erp.material_rolls where purchase_item_id=%s',(fx['item'],)).fetchone()[0]
    other=uuid.uuid4()
    cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,'BA second raw warehouse','RAW_MATERIAL_WAREHOUSE',true)",
                (other,'BA-LOC-'+other.hex[:20]))
    transfer(cur,fx['location'],other,fx['material'],roll,10,prod.at(today-timedelta(days=2),10))
    day=today-timedelta(days=3 if before_arrival else 1)
    result,error=r1.peer.attempt(cur,lambda:transfer(cur,other,fx['location'],fx['material'],roll,5,prod.at(day,10)))
    minimum,history=stock_history(cur,fx['material'],other,roll)
    evidence=dict(transfer_back_day=str(day),warehouse_history_minimum=str(minimum),warehouse_history=history,transfer=result)
    if before_arrival:
        refused=error is not None and code_of(error)=='AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY'
        return dict(evidence,status='PASS' if refused and minimum>=0 else ('COUNTEREXAMPLE' if error is None else 'INCOMPLETE'),
                    refusal=error,expected_refusal='AM_BACKDATE_WOULD_CREATE_NEGATIVE_LOCATION_ROLL_HISTORY',
                    oracle='D02=A / AUD-S04: stock arriving later does not fund an earlier outflow of the same warehouse and roll')
    return control(cur,result is not None and minimum>=0,error,**evidence)


# ---------------------------------------------------------------- A4 cents

KEYS=('MATERIAL_INVENTORY','WIP','AP_SUPPLIER','GRNI_MATERIAL')


def cents(value):
    return D(str(value)).quantize(D('0.01'),rounding=ROUND_HALF_UP)


def daily(cur,days):
    api.admin(cur)
    rows=cur.execute("""select j.transaction_date,a.mapping_key,sum(l.debit-l.credit) from erp.journal_lines l
      join erp.journal_entries j on j.id=l.journal_entry_id and j.status in('POSTED','REVERSED')
      join erp.accounting_account_mappings a on a.account_id=l.account_id where a.mapping_key=any(%s) group by 1,2""",(list(KEYS),)).fetchall()
    return {str(day):{k:sum((D(str(v)) for t,key,v in rows if key==k and t<=day),D(0)) for k in KEYS} for day in days}


def estimated_one(cur,day,price):
    prod=chain.production;base=prod.prior
    api.admin(cur);prod.zone(cur,'Asia/Jakarta')
    material=base.clone_material(cur,'bacent')
    location=uuid.uuid4()
    cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,'BA cent raw warehouse','RAW_MATERIAL_WAREHOUSE',true)",
                (location,'BA-CENT-'+location.hex[:20]))
    draft=prod.rpc(cur,'erp.save_material_purchase_draft_v2',dict(purchase_number='BA-CENT-'+str(uuid.uuid4()),supplier_id=base.BASE_SUPPLIER,
        location_id=location,physical_at=prod.at(day,10),change_reason='BA cent estimated receipt',lines=[dict(material_id=material,qty=1,
        unit_price=price,price_state='ESTIMATED',price_source='MANUAL_ESTIMATE',rolls=[dict(roll_number='BA-CENT-ROLL-'+str(uuid.uuid4()),qty=1)])]))
    purchase=uuid.UUID(draft['purchase_id'])
    cur.execute('select erp.post_material_purchase_v2(%s,%s,%s,%s)',(purchase,uuid.uuid4(),int(draft['row_version']),'BA cent receipt post'))
    api.admin(cur)
    item=cur.execute('select id from erp.material_purchase_items where purchase_id=%s',(purchase,)).fetchone()[0]
    return dict(material=material,purchase=purchase,item=item,location=location)


def a4_cents(cur,today,kind,old,new):
    """The auditor's BLIND-MONEY-CENT case: one unit received at `old` on d-4, cut on d-3, corrected (DIRECT) or invoiced
    (INVOICE) at `new` on d-2. Expected per day, endpoint rounded: MATERIAL 0 from the cut, WIP the rounded unit."""
    prod=chain.production
    receipt_day,cutting_day,invoice_day=[today-timedelta(days=n) for n in (4,3,2)]
    days=[receipt_day,cutting_day,invoice_day,today]
    boundary.historical.prior.set_open_period(cur,receipt_day-timedelta(days=1))
    before=daily(cur,days)
    fx=azp.final_receipt(cur,receipt_day,qty=1,price=old) if kind=='DIRECT' else estimated_one(cur,receipt_day,old)
    api.admin(cur)
    fx['roll']=cur.execute('select id from erp.material_rolls where purchase_item_id=%s',(fx['item'],)).fetchone()[0]
    azp.cut(cur,fx,cutting_day,1)
    api.admin(cur)
    if kind=='DIRECT':
        corr=cur.execute("""insert into erp.material_purchase_cost_corrections(correction_number,purchase_id,invoice_date,reason)
          values(%s,%s,%s,'BA cent correction') returning id""",('BA-CC-'+uuid.uuid4().hex[:12],fx['purchase'],invoice_day)).fetchone()[0]
        cur.execute('insert into erp.material_purchase_cost_correction_items(correction_id,purchase_item_id,new_unit_price) values(%s,%s,%s)',(corr,fx['item'],new))
        prod.owner(cur);cur.execute('select erp.post_material_purchase_cost_correction(%s)',(corr,))
    else:
        version=int(cur.execute('select row_version from erp.material_purchase_headers where id=%s',(fx['purchase'],)).fetchone()[0])
        prod.rpc(cur,'erp.finalize_material_purchase_invoice_v2',dict(purchase_id=fx['purchase'],supplier_invoice_number='BA-INV-'+uuid.uuid4().hex[:12],
            invoice_date=invoice_day,received_at=prod.at(today-timedelta(days=1),15),reason='BA cent late invoice',
            lines=[dict(purchase_item_id=fx['item'],qty_invoiced=1,final_unit_price=new)]),uuid.uuid4(),version)
    prod.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');api.admin(cur)
    after=daily(cur,days)
    observed={day:{k:after[day][k]-before[day][k] for k in KEYS} for day in after}
    original,corrected=cents(old),cents(new)
    expected={}
    for day in days:
        amount=corrected if day>=invoice_day else original
        row=dict.fromkeys(KEYS,D('0.00'))
        row['MATERIAL_INVENTORY']=amount if day<cutting_day else D('0.00')
        row['WIP']=amount if day>=cutting_day else D('0.00')
        row['AP_SUPPLIER' if kind=='DIRECT' or day>=invoice_day else 'GRNI_MATERIAL']=-amount
        expected[str(day)]=row
    qty=D(str(cur.execute('select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=%s',(fx['material'],)).fetchone()[0]))
    mismatch={day:{k:dict(expected=str(expected[day][k]),actual=str(observed[day][k])) for k in KEYS if expected[day][k]!=observed[day][k]} for day in observed}
    mismatch={day:row for day,row in mismatch.items() if row}
    good=not mismatch and qty==0
    status='PASS' if good else ('FAIL' if ba_installed(cur) else 'COUNTEREXAMPLE')
    return dict(status=status,kind=kind,old=old,new=new,raw_qty=str(qty),mismatches=mismatch,observed=plain(observed),expected=plain(expected))


# ---------------------------------------------------------------- A5 selectors

def a5_bs_sources(cur,today):
    """The auditor's XA2 selector case (F1-15/CP6-04): one old claimable Laundry delivery and 100 newer claimable ones.
    Privileged fixture, as the auditor's: clones of a posted seed delivery and its lines, inserted with triggers off
    (session_replication_role=replica) on the disposable clone; the selector is read through the public facade as the page
    reads it. Expected: the old delivery is among the claimable sources the workspace gives the page."""
    api.admin(cur)
    src=cur.execute("""select d.id from erp.laundry_deliveries d where d.status in('SENT','PARTIAL_RETURN','RETURNED','CLOSED')
      and exists(select 1 from erp.laundry_delivery_lines l where l.delivery_id=d.id and l.qty_sent_pcs>0) order by d.physical_at,d.id limit 1""").fetchone()
    if src is None:return dict(status='INCOMPLETE',reason='no posted seed Laundry delivery to clone')
    made=[]
    cur.execute("set local session_replication_role=replica")
    try:
        for n in range(101):
            new=uuid.uuid4();at=chain.production.at(today-timedelta(days=200 if n==0 else 1),8)+timedelta(minutes=n)
            cur.execute("""insert into erp.laundry_deliveries select (jsonb_populate_record(null::erp.laundry_deliveries,to_jsonb(d)||jsonb_build_object(
                'id',%s::uuid,'delivery_number',%s::text,'physical_at',%s::timestamptz,'status','SENT'))).* from erp.laundry_deliveries d where d.id=%s""",
                (new,'BA5-LDR-%03d-%s'%(n,new.hex[:8]),at,src[0]))
            cur.execute("""insert into erp.laundry_delivery_lines select (jsonb_populate_record(null::erp.laundry_delivery_lines,to_jsonb(l)||jsonb_build_object(
                'id',gen_random_uuid(),'delivery_id',%s::uuid))).* from erp.laundry_delivery_lines l where l.delivery_id=%s""",(new,src[0]))
            made.append(str(new))
    finally:
        cur.execute("set local session_replication_role=origin")
    api.ordinary(cur)
    ws=cur.execute("select public.erp_get_bs_resolution_workspace_v1('ACTIVE','ALL',null,null,50,0)").fetchone()[0]
    api.admin(cur)
    sources={s['id']:s for s in ws['lookups']['laundry_sources']}
    old=sources.get(made[0])
    evidence=dict(clones=len(made),listed=len(sources),old_listed=old is not None,old=old,
                  newer_listed=sum(1 for m in made[1:] if m in sources),
                  zero_capacity_listed=sum(1 for s in sources.values() if s['qty_claimable_pcs']<=0))
    ok=old is not None and old['qty_claimable_pcs']>0 and evidence['newer_listed']==100
    return dict(evidence,status='PASS' if ok else ('FAIL' if ba_installed(cur) else 'COUNTEREXAMPLE'),
                oracle='CP6-04: an old source that can still be claimed stays selectable after 100 newer ones')


def a5_import_drafts(cur,today):
    """The auditor's XI selector case (CP6-04): 51 drafts created through the public CREATE action. Expected: the oldest
    editable draft is listed by the workspace the page reads."""
    ids=[]
    for n in range(51):
        ids.append(str(api.call(cur,'CREATE',dict(batch_code='BA5-%02d-%s'%(n,uuid.uuid4().hex[:8]),cutover_date=str(today-timedelta(days=1))))['batch_id']))
    api.admin(cur)
    ordered=[r[0] for r in cur.execute('select id::text from erp.migration_batches where id=any(%s::uuid[]) order by created_at desc,id',(ids,)).fetchall()]
    listed=[str(r['id']) for r in api.read(cur,None)['recent']]
    oldest=ordered[-1]
    ok=oldest in listed and all(i in listed for i in ids)
    return dict(status='PASS' if ok else ('FAIL' if ba_installed(cur) else 'COUNTEREXAMPLE'),created=len(ids),listed=len(listed),
                oldest_listed=oldest in listed,authored_listed=sum(1 for i in ids if i in listed),
                oracle='CP6-04: an older editable draft stays discoverable after 51 drafts')


# ---------------------------------------------------------------- A6 single close filing

def filings(cur,day):
    api.admin(cur)
    return cur.execute('select count(*) from erp.accounting_close_filings_v1 where closed_through=%s',(day,)).fetchone()[0]


def a6_close(cur,today,reopen):
    """Close d (READY after quieting the seed, as the auditor's XA5 R2); then close d again (finding) or reopen to d-1 and
    close d again (control: a close after a reopen files)."""
    d=today-timedelta(days=1);d0=today-timedelta(days=4)
    boundary.historical.prior.set_open_period(cur,d0-timedelta(days=1))
    quiet=awp.quiet_seed(cur,d0,d)
    ready=awp.preflight(cur,d)
    if ready is None or ready['status']!='READY':
        return dict(status='INCOMPLETE',reason='fixture not READY',blockers=awp.blockers_brief(ready))
    first=awp.close(cur,d,'BA probe first close')
    if first[0]!='ACCEPTED':return dict(status='INCOMPLETE',reason='first close refused',first=first)
    if reopen:
        api.ordinary(cur);cur.execute('select erp.reopen_accounting_through(%s,%s)',(d-timedelta(days=1),'BA probe reopen before closing again'));api.admin(cur)
    count=filings(cur,d)
    second=awp.close(cur,d,'BA probe second close of the same date')
    after=filings(cur,d)
    evidence=dict(closed_through=str(d),reopened=reopen,filings_before_second=count,filings_after_second=after,second=second[0],
                  second_error=second[1],quiet=quiet)
    if reopen:
        return control(cur,second[0]=='ACCEPTED' and after==count+1,None if second[0]=='ACCEPTED' else second[1],**evidence)
    error=None if second[0]=='ACCEPTED' else second[1]
    harm=second[0]=='ACCEPTED' and after==2
    out=finding(cur,'CLOSE_ALREADY_CLOSED',None,error,harm,**evidence)
    if out['status']=='PASS' and after!=1:out['status']='FAIL'
    return out


# ---------------------------------------------------------------- registration

PLAN=[('A1:MATERIAL_SECOND_BATCH_SAME_ITEM','COUNTEREXAMPLE',lambda c,t:import_overlap(c,t,'MATERIAL')),
      ('A1:MATERIAL_SECOND_BATCH_EARLIER_CUTOVER','COUNTEREXAMPLE',lambda c,t:import_overlap(c,t,'MATERIAL',cutover_days=2)),
      ('A1:FINISHED_GOODS_SECOND_BATCH_SAME_ITEM','COUNTEREXAMPLE',lambda c,t:import_overlap(c,t,'FINISHED_GOODS')),
      ('A1:CASH_BANK_SECOND_BATCH_SAME_ACCOUNT','COUNTEREXAMPLE',lambda c,t:import_overlap(c,t,'CASH_BANK')),
      ('A1:WIP_SUMMARY_SECOND_BATCH_SAME_MODEL_STAGE','COUNTEREXAMPLE',lambda c,t:import_overlap(c,t,'WIP')),
      ('A1:BS_SUMMARY_SECOND_BATCH_SAME_PRODUCT','COUNTEREXAMPLE',lambda c,t:import_overlap(c,t,'BS')),
      ('A1:MATERIAL_SECOND_BATCH_OTHER_WAREHOUSE_CONTROL','PASS',lambda c,t:import_overlap(c,t,'MATERIAL',other_location=True)),
      ('A1:FINISHED_GOODS_SECOND_BATCH_OTHER_WAREHOUSE_CONTROL','PASS',lambda c,t:import_overlap(c,t,'FINISHED_GOODS',other_location=True)),
      ('A3:COMPLETE_DATED_BEFORE_REVERSAL','COUNTEREXAMPLE',a3_before_reversal),
      ('A3:COMPLETE_ON_REVERSAL_DAY_CONTROL',('PASS','COUNTEREXAMPLE'),a3_after_reversal),
      ('A3:BACKDATED_COMPLETE_FITS_LATER_DAYS_CONTROL','PASS',a3_backdated_fits),
      ('A10:BOUND_PRODUCT_OUTPUT_OTHER_PRODUCT','COUNTEREXAMPLE',lambda c,t:a10_output(c,t,True,True,'B','BA_WIP_OUTPUT_PRODUCT_BOUND')),
      ('A10:UNBOUND_SOURCE_BRAND_COLOR_MISMATCH','COUNTEREXAMPLE',lambda c,t:a10_output(c,t,False,True,'B','BA_WIP_OUTPUT_SOURCE_MISMATCH')),
      ('A10:BOUND_PRODUCT_SAME_PRODUCT_CONTROL','PASS',lambda c,t:a10_output(c,t,True,True,'A')),
      ('A10:UNBOUND_SOURCE_MATCHING_CONTROL','PASS',lambda c,t:a10_output(c,t,False,True,'A')),
      ('A10:UNBOUND_SOURCE_NO_ATTRIBUTES_CONTROL','PASS',lambda c,t:a10_output(c,t,False,False,'A'))]
PLAN+=[('A9:%s_%s_%s'%(op,kind,'DATED_CAPACITY' if back else 'ORDERED_CONTROL'),'COUNTEREXAMPLE' if back else 'PASS',
        lambda c,t,k=kind,o=op,b=back:a9_advance(c,t,k,o,b))
       for op in ('REFUND','APPLY') for kind in ('SUPPLIER','CUSTOMER','VENDOR') for back in (True,False)]
PLAN+=[('A9:S04_TRANSFER_BACK_BEFORE_ARRIVAL_REFUSED','PASS',lambda c,t:s04_transfer_back(c,t,True)),
       ('A9:S04_TRANSFER_BACK_AFTER_ARRIVAL_CONTROL','PASS',lambda c,t:s04_transfer_back(c,t,False))]
PLAN+=[('A4:CENT_%s_%s'%(kind,direction),'COUNTEREXAMPLE',lambda c,t,k=kind,o=old,n=new:a4_cents(c,t,k,o,n))
       for kind in ('DIRECT','INVOICE') for direction,old,new in (('UP','10.005','10.014'),('DOWN','10.014','10.005'))]
PLAN+=[('A5:BS_OLD_CLAIMABLE_DELIVERY_AFTER_100_NEWER','COUNTEREXAMPLE',a5_bs_sources),
       ('A5:IMPORT_OLDEST_DRAFT_AFTER_51','COUNTEREXAMPLE',a5_import_drafts)]
PLAN+=[('A6:SECOND_CLOSE_SAME_DATE','COUNTEREXAMPLE',lambda c,t:a6_close(c,t,False)),
       ('A6:CLOSE_AGAIN_AFTER_REOPEN_CONTROL','PASS',lambda c,t:a6_close(c,t,True))]
assert len({k for k,_,_ in PLAN})==len(PLAN),'BA_DUPLICATE_CASE_ID'


def cases(cur,today):
    return [(key,lambda f=fn:f(cur,today)) for key,_,fn in PLAN]


def run(phase):
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    r1.OUT=OUT
    planned={k:(e if isinstance(e,tuple) else (e,)) if phase=='before' else ('PASS',) for k,e,_ in PLAN}
    report=dict(status='INCOMPLETE',label=LABEL,phase=phase,source=r1.source(),production_go=False,independent_acceptance=False,release_evidence=False,
                planned={k:list(v) for k,v in planned.items()})
    r1.save('RESULT_'+phase.upper(),report)
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        r1.writer.install_at()
        control_url=os.environ['CP6_ADMISSION_CONTROL_PGURL']
        report['au_install']=awp.au_runtime.change('install',boundary.PG,control_url)['status']
        report['av_install']=awp.av_runtime.change('install',boundary.PG,control_url)['status']
        report['aw_install']=awp.install_aw();report['ax_install']=axp.install_ax();report['ay_install']=ayp.install_ay()
        report['az_install']=azp.install_az();verify=azp.az_verified
        if phase=='after':report['ba_install']=install_ba();verify=ba_verified
        r1.save('RESULT_'+phase.upper(),report)
        print(json.dumps(dict(ba_probe_setup={k:report.get(k) for k in ('au_install','av_install','az_install','ba_install')}),default=str),flush=True)
        group=r1.group('BA_CASES_'+phase.upper(),cases,verify)
        report['ba_cases']={k:group[k] for k in ('status','counts')}
        final={k:v['status'] for k,v in group['cases'].items()}
        report['final']=final
        report['expectation_mismatch']={k:dict(planned=list(e),final=final.get(k)) for k,e in planned.items() if final.get(k) not in e}
        report['status']='REVIEW_COMPLETE' if group['status']!='INCOMPLETE' and not report['expectation_mismatch'] else 'INCOMPLETE'
    except Exception as exc:report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        r1.save('RESULT_'+phase.upper(),report)
    print(json.dumps(dict(ba_probe_phase=phase,**{k:v for k,v in report.items() if k!='source'}),default=str),flush=True)
    assert report['status']=='REVIEW_COMPLETE',report.get('error') or ('BA_PROBE_EXPECTATION_MISMATCH',report.get('expectation_mismatch'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('before','after'),required=True)
    run(parser.parse_args().phase)
