"""Writer retest of OWN-BE-01/02/04/05 and RELATED-01. Disposable data only.
Oracles copied from owner-delivered audit expectations; these are writer results.
"""
from datetime import timedelta
from decimal import Decimal as D
import json,uuid
import cp6_be_probe as be
import cp6_ax_probe as ax
import cp6_pocket_period_trial as native_pocket
b=be.bdp
one,q,api=be.one,be.q,be.api
bc=b.bcp

def opening(cur,today,product=None,target=None,unit='1234.57'):
    api.admin(cur);day=today-timedelta(days=2)
    product=product or b.sized_product(cur,be.chain.base.SIZE,'BER-OPEN-'+uuid.uuid4().hex[:8])
    target=target or b.sized_product(cur,be.chain.base.SIZE,'BER-DEST-'+uuid.uuid4().hex[:8])
    ident=str(uuid.uuid4())
    cur.execute("insert into erp.opening_balance_headers(id,opening_number,opening_date,status,created_by) values(%s,%s,%s,'DRAFT',%s)",
      (ident,'BER-'+ident,day,be.chain.base.OPERATOR_APP))
    cur.execute("insert into erp.opening_balance_items(opening_id,balance_type,product_id,location_id,qty,unit_cost_snapshot,quality_grade,hpp_input_method) values(%s,'FINISHED_GOODS',%s,%s,13,%s,'GRADE_A','MANUAL')",
      (ident,product,be.chain.base.LOCATION,unit))
    b.internal(cur,'post_opening_balance',ident)
    lot=one(cur,"select id::text from erp.fg_lots where product_id=%s and lot_origin='OPENING' order by created_at desc,id limit 1",product)
    return dict(lot=lot,product=product,target=target,location=be.chain.base.LOCATION,day=today-timedelta(days=1))

def convert(cur,f,qty=5,hour=15,at=None,**extra):
    return be.be(cur,'POST',dict(source_lot_id=f['lot'],target_product_id=f['target'],location_id=f['location'],qty_pcs=qty,
      physical_at=b.iso(at or be.chain.production.at(f['day'],hour)),reason='BE audit revision sourced conversion',
      expected_version=one(cur,'select erp.be_source_revision_v1(%s,%s)',f['lot'],f['location']),**extra))

def ledger(cur):return {k:b.gl(cur,k) for k in ('FG_INVENTORY','COGS','OTHER_INCOME','OTHER_EXPENSE')}

def recovery(cur,today,po,usage,excess=False):
    # Non-PO recovery includes next-day receipt/inspection/value at 09:00-11:00.
    # Finish that sequence yesterday so it is valid even just after midnight.
    f=be.fixture(cur,today) if po else opening(cur,today-timedelta(days=1),unit='1.00' if excess else '1234.57')
    a=bc.fixture(cur,f['day'],stock_qty=100,cost='23.17')
    bc.policy(cur,'ACC_DEC04',dict(OWN_FG_REPAIR_account_id=bc.account(cur,'5100')))
    bc.policy(cur,'ACC_DEC07',dict(approval='NONE'))
    bc.policy(cur,'ACC_DEC03',dict(credit_account_id=bc.account(cur,'4100'),unit_value_cap='MOVING_AVERAGE'))
    # BC's material fixture removes its temporary native-schema grant. This
    # savepoint case uses native sales as a labelled prerequisite, as BE's
    # existing chain-cost probe does; HTTP cases never receive this grant.
    api.admin(cur);cur.execute('grant usage on schema erp to authenticated')
    c=convert(cur,f,expected_returns=[dict(material_id=a['material'],qty='5',holder='BE independent audit recovery')]);dest=c['destination_lot_id']
    base=b.lot_value(cur,dest)
    if not po:assert base==D('5.00' if excess else '6172.85'),base
    if usage:
      be.be(cur,'POST_USAGE',dict(conversion_id=c['conversion_id'],expected_version=one(cur,'select erp.be_conversion_revision_v1(%s)',c['conversion_id']),
        location_id=a['main'],physical_at=b.iso(be.chain.production.at(f['day'],16)),items=[dict(material_id=a['material'],qty='5')],reason='Five replacement accessories'))
      assert b.lot_value(cur,dest)==base+D('115.85')
    sale=b.sell(cur,f,f['target'],1,17)
    snapshots=q(cur,'select id,total_hpp from erp.sale_stock_allocations where sale_item_id in(select id from erp.sales_items where sale_id=%s)',sale)
    out=one(cur,'select outstanding_id::text from erp.be_conversion_returns_v1 where conversion_id=%s',c['conversion_id'])
    r=bc.receive(cur,a,'TEARDOWN',[(3,out)],f['day']+timedelta(days=1),reference='Actual three of five returned')['lot_ids'][0]
    bc.inspect(cur,r,bc.local_at(f['day']+timedelta(days=1),10),'BE revision inspector',usable=2,damaged=1)
    payload=dict(lot_id=r,condition='USABLE',qty='2',unit_value='7.13',location_id=a['main'],physical_at=bc.local_at(f['day']+timedelta(days=1),11),reason='Two usable accessories reduce garment cost')
    before=ledger(cur);stock=bc.stock(cur,a['material'],a['main']);old=b.lot_value(cur,dest);truth=b.all_truth(cur)
    key=str(uuid.uuid4())
    if excess:
      refused=b.refused(cur,lambda:bc.svc(cur,'VALUE_CUSTODY',payload,key=key),'BE_RECOVERY_EXCEEDS_VALUE')
      return b.verdict(dict(refused=refused['ok'],atomic=ledger(cur)==before and b.lot_value(cur,dest)==old and bc.stock(cur,a['material'],a['main'])==stock))
    value=bc.svc(cur,'VALUE_CUSTODY',payload,key=key);after=ledger(cur)
    replay=bc.svc(cur,'VALUE_CUSTODY',payload,key=key)
    progress=one(cur,'select erp.be_return_progress_v1(%s)',c['conversion_id'])
    checks=dict(recovery=b.lot_value(cur,dest)==old-D('14.26'),fg=after['FG_INVENTORY']-before['FG_INVENTORY']==D('-11.41'),
      cogs=after['COGS']-before['COGS']==D('-2.85'),no_income=after['OTHER_INCOME']==before['OTHER_INCOME'],
      two_usable_only=bc.stock(cur,a['material'],a['main'])==stock+2,missing_two=progress[0]['unreturned']=='2.000000',
      replay=value==replay and ledger(cur)==after,truth=b.truth_quiet(truth,b.all_truth(cur)),
      sale_snapshot=snapshots==q(cur,'select id,total_hpp from erp.sale_stock_allocations where sale_item_id in(select id from erp.sales_items where sale_id=%s)',sale))
    bc.reverse(cur,value['document_id'])
    checks['inverse']=ledger(cur)==before and b.lot_value(cur,dest)==old and bc.stock(cur,a['material'],a['main'])==stock
    return b.verdict(checks,po=po,new_usage=usage,base=str(base),recovery='14.26',delta={k:after[k]-before[k] for k in before})

def nonpo_books(cur,products):
    for product in products:
      target=q(cur,'select * from erp.compute_non_po_product_hpp_targets_v2620f(%s)',product)[0]
      book=q(cur,'select * from erp.compute_non_po_product_hpp_book_v2620f(%s)',product)[0]
      assert target==book,(product,target,book)
    return True

def mixed(cur,today):
    p=be.fixture(cur,today);n=opening(cur,today,p['product'],p['target'])
    source_qty=be.qty(cur,p['lot'])
    a=convert(cur,n,5,15);c=convert(cur,p,3,16);z=convert(cur,n,1,17)
    assert b.lot_value(cur,a['destination_lot_id'])==D('6172.85')
    assert b.lot_value(cur,z['destination_lot_id'])==D('1234.57')
    products=[p['product'],p['target']];nonpo_books(cur,products)
    sale=b.sell(cur,p,p['target'],2,18)
    snapshots=q(cur,'select id,total_hpp from erp.sale_stock_allocations where sale_item_id in(select id from erp.sales_items where sale_id=%s) order by id',sale)
    ret=str(uuid.uuid4());be.chain.production.owner(cur)
    cur.execute("insert into erp.sales_returns(id,return_number,sale_id,customer_id,physical_at,created_by) select %s,%s,id,customer_id,%s,erp.current_app_user_id() from erp.sales_headers where id=%s",
      (ret,'BER-RET-'+ret,b.iso(be.chain.production.at(p['day'],19)),sale))
    cur.execute("insert into erp.sales_return_items(return_id,sale_stock_allocation_id,product_id,lot_id,location_id,qty_pcs,refund_amount) select %s,a.id,l.product_id,l.id,a.location_id,1,20000 from erp.sale_stock_allocations a join erp.fg_lots l on l.id=a.lot_id where a.id=%s",(ret,snapshots[0][0]))
    cur.execute('select erp.post_sales_return(%s)',(ret,));api.admin(cur);nonpo_books(cur,products)
    # Keep both origin families alive while a late PO invoice changes HPP.
    receipt=one(cur,'select r.id::text from erp.laundry_receipts r join erp.laundry_deliveries d on d.id=r.delivery_id where d.vendor_id=%s',p['vendor'])
    b.invoice_policies(cur);_,inv=b.invoice(cur,p,[dict(line=b.receipt_line(cur,receipt),qty=10,amount='55000.00')],'55000.00')
    nonpo_books(cur,products)
    assert b.lot_value(cur,a['destination_lot_id'])==D('6172.85')
    b.bd(cur,'REVERSE_INVOICE',dict(invoice_id=inv['invoice_id'],expected_version=inv['row_version'],reason='BE mixed source inverse invoice'))
    nonpo_books(cur,products)
    # Additional historical pocket stock has both conversion families beside it.
    pocket=be.pocket_probe.roundtrip(cur,today,True)
    nonpo_books(cur,products)
    # The original PO conversion can carry the FIFO sale/return above. Keep
    # that used lineage alive and reverse an unused sibling PO conversion;
    # the PO reversal must still stay outside the live non-PO book.
    unused_po=convert(cur,p,1,20);nonpo_books(cur,products)
    for conversion in (unused_po,z):
      key=str(uuid.uuid4());payload=dict(conversion_id=conversion['conversion_id'],reason='BE mixed origin conversion inverse')
      reversed_once=be.be(cur,'REVERSE',payload,key)
      assert be.be(cur,'REVERSE',payload,key)==reversed_once
      assert be.qty(cur,conversion['destination_lot_id'])==0
      nonpo_books(cur,products)
    return b.verdict(dict(both_origins=True,late_invoice_isolated=True,sale_return=True,pocket=pocket['status']=='PASS',
      mixed_conversion_inverse=be.qty(cur,p['lot'])==source_qty-3 and be.qty(cur,n['lot'])==8,
      sales_immutable=snapshots==q(cur,'select id,total_hpp from erp.sale_stock_allocations where sale_item_id in(select id from erp.sales_items where sale_id=%s) order by id',sale)),pocket=pocket)

def pocket_many(cur,today,old_days=20,new_days=10):
    pp=be.pocket_probe
    def source(days):
      cut=today-timedelta(days=days)
      f=b.bbp.production_post(cur,today,pp.active_unit(cur,pp.rows(cut)),cutover_days=days)
      return cut-timedelta(days=1),cut
    start,end=source(old_days);new_start,new_end=source(new_days)
    def post(first,last):
      p=pp.preview(cur,first,last)
      return pp.call(cur,'POST_PERIOD',dict(period_start=str(first),period_end=str(last),expected_revision=p['revision'],reason='BE 52-period accessibility probe'))['id']
    original=post(start,end)
    for _ in range(51):
      ident=post(new_start,new_end);state=one(cur,'select erp.pocket_period_state_v1(%s)',ident)
      pp.call(cur,'CANCEL_PERIOD',dict(id=ident,expected_revision=state['revision'],reason='BE later cancelled period'))
    return dict(id=original,start=str(start),end=str(end),before=pp.amounts(cur),
      stock=one(cur,'select count(*) from erp.material_stock_movements'))

def pocket_page(cur,query='',offset=0):
    bc.session(cur);result=one(cur,'select public.erp_get_pocket_periods_v1(%s,%s)',query,offset);api.admin(cur);return result

def pocket_history(cur,today):
    f=pocket_many(cur,today);first=pocket_page(cur);second=pocket_page(cur,offset=50)
    assert f['id'] not in [p['id'] for p in first['periods']]
    assert f['id'] in [p['id'] for p in second['periods']]
    assert f['id'] in [p['id'] for p in pocket_page(cur,f['id'])['periods']]
    found=next(p for p in pocket_page(cur,f['end'])['periods'] if p['id']==f['id'])
    key=str(uuid.uuid4());payload=dict(id=f['id'],expected_revision=found['revision'],reason='BE cancel oldest active from search')
    pp=be.pocket_probe;out=pp.call(cur,'CANCEL_PERIOD',payload,key);again=pp.call(cur,'CANCEL_PERIOD',payload,key)
    delta=pp.difference(f['before'],pp.amounts(cur))
    return b.verdict(dict(paged=first['period_next_offset']==50 and second['period_next_offset'] is None,
      search_id_and_date=True,once=out==again,no_stock=one(cur,'select count(*) from erp.material_stock_movements')==f['stock'],
      inverse=delta['WIP']==D('-5.62') and delta['FG_INVENTORY']==D('-3.38') and delta['COGS']==D('-2.25') and delta['OTHER_EXPENSE']==D('11.25')),delta=delta)

def unsupported_rework(cur,today):
    f=ax.repair_fixture(cur,today)
    before=one(cur,'select count(*) from erp.rework_orders')
    payload=dict(rework_number='BER-NONPO-'+uuid.uuid4().hex,bs_case_id=f['case'],destination_type='CONTRACTOR',contractor_id=f['contractor'],qty_sent=3,
      physical_sent_at=f['at'],return_fg_location_id=be.chain.base.LOCATION,accessory_bom_item_ids=[],change_reason='BE unsupported generic non-PO entry')
    refused=b.refused(cur,lambda:be.chain.bs_action(cur,'SAVE_REWORK',payload,None),'BE_NONPO_REWORK_UNSUPPORTED')
    assert one(cur,'select count(*) from erp.rework_orders')==before
    repaired=ax.post(cur,ax.repair_payload(f,2))
    target=b.sized_product(cur,be.chain.base.SIZE,'BER-AX-'+uuid.uuid4().hex[:10])
    x=convert(cur,dict(lot=repaired['lot_id'],target=target,location=be.chain.base.LOCATION,day=today),1,at=ax.r1.now(cur)-timedelta(minutes=1))
    return b.verdict(dict(early_refusal=refused['ok'],ax_repair=be.qty(cur,repaired['lot_id'])==1,ax_conversion=be.qty(cur,x['destination_lot_id'])==1))

def sewing_fixture(cur,today):
    f=native_pocket.fixture(api,cur,today)
    made=native_pocket.pocket.call(api,cur,'POST_PERIOD',f['payload'])
    event=one(cur,'select event_id::text from erp.pocket_period_destinations where pool_id=%s',made['id'])
    return dict(pool=made['id'],event=event,version=one(cur,'select row_version from erp.sewing_terminal_events where id=%s',event))

def sewing_reverse(cur,today):
    f=sewing_fixture(cur,today)
    def call(version,key=None):
      bc.session(cur)
      value=one(cur,'select public.erp_reverse_sewing_terminal_v1(%s,%s,%s,%s)',f['event'],'BE public versioned reversal',key or str(uuid.uuid4()),version)
      api.admin(cur);return value
    def refused_message(version,message):
      # These legacy guards return a sentence, not the symbolic token consumed
      # by b.refused/code_of. Require the exact message and SQLSTATE instead.
      result,error=bc.r1.peer.attempt(cur,lambda:call(version))
      return dict(expected_message=message,refusal=error,result=result,
        ok=error is not None and error.get('sqlstate')=='P0001' and error.get('message')==message)
    missing=refused_message(None,'event_id and expected_version are required')
    stale=b.refused(cur,lambda:call(f['version']+1),'STALE_VERSION')
    held=refused_message(f['version'],'Batalkan alokasi kain kantong terkait sebelum mengoreksi hasil jahit')
    state=one(cur,'select erp.pocket_period_state_v1(%s)',f['pool'])
    be.pocket_probe.call(cur,'CANCEL_PERIOD',dict(id=f['pool'],expected_revision=state['revision'],reason='BE release active denominator'))
    key=str(uuid.uuid4());result=call(f['version'],key);again=call(f['version'],key)
    return b.verdict(dict(missing_version=missing['ok'],stale=stale['ok'],dependency=held['ok'],replay=result==again,
      reversed_once=one(cur,'select count(*) from erp.sewing_terminal_events where reversal_of_id=%s',f['event'])==1),refusals=[missing,stale,held])

def cases(cur,today):
    return [(f'BE_REV:RECOVERY_{"PO" if po else "NONPO"}_{"USAGE" if usage else "ZERO"}',lambda po=po,usage=usage:recovery(cur,today,po,usage)) for po in (False,True) for usage in (False,True)]+[
      ('BE_REV:RECOVERY_EXCEEDS_GARMENT_ATOMIC',lambda:recovery(cur,today,False,False,True)),
      ('BE_REV:MIXED_PO_NONPO_SALE_RETURN_INVOICE_POCKET',lambda:mixed(cur,today)),
      ('BE_REV:52_POCKET_PERIODS_SEARCH_PAGE_INVERSE',lambda:pocket_history(cur,today)),
      ('BE_REV:NONPO_ENTRY_REFUSED_AX_REPAIR_CONVERSION',lambda:unsupported_rework(cur,today)),
      ('BE_REV:PUBLIC_SEWING_VERSION_DEPENDENCY_REPLAY',lambda:sewing_reverse(cur,today))]
