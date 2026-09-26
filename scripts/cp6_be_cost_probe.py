"""BE sourced cost propagation after sale and another conversion; independent invariants within writer evidence."""
from datetime import timedelta
import uuid
import cp6_bd_probe as b
api,one,q=b.api,b.one,b.q

def chain_cost(cur,today,installed,fixture,post):
    if not installed:return b.no_route(cur,lambda:post(cur,'POST',dict(reason='BE source route missing')))
    f=fixture(cur,today);bc=b.bcp;acc=bc.fixture(cur,f['day'],stock_qty=100,cost='2.00')
    bc.policy(cur,'ACC_DEC04',dict(OWN_FG_REPAIR_account_id=bc.account(cur,'5100')));bc.policy(cur,'ACC_DEC07',dict(approval='NONE'))
    api.admin(cur);cur.execute('grant usage on schema erp to authenticated')
    source=post(cur,'POST',dict(f['payload'],expected_returns=[dict(material_id=acc['material'],qty='3',holder='BE accountable holder')]))
    conv,dest=source['conversion_id'],source['destination_lot_id']
    post(cur,'POST_USAGE',dict(conversion_id=conv,expected_version=one(cur,'select erp.be_conversion_revision_v1(%s)',conv),location_id=acc['main'],physical_at=f['payload']['physical_at'],items=[dict(material_id=acc['material'],qty='6')],reason='BE six actual replacement accessories'))
    target2=b.sized_product(cur,b.chain.base.SIZE,'BE-CHILD-'+uuid.uuid4().hex[:8])
    child=post(cur,'POST',dict(source_lot_id=dest,target_product_id=target2,location_id=f['location'],qty_pcs=2,physical_at=b.iso(b.chain.production.at(f['day'],16)),reason='BE one further conversion',expected_version=one(cur,'select erp.be_source_revision_v1(%s,%s)',dest,f['location'])))['destination_lot_id']
    sale1=b.sell(cur,f,f['target'],1,17);sale2=b.sell(cur,f,target2,1,18)
    snapshots=q(cur,'select id,total_hpp from erp.sale_stock_allocations where sale_item_id in(select id from erp.sales_items where sale_id in(%s,%s)) order by id',sale1,sale2)
    source_hpp=b.lot_value(cur,f['lot']);parent0=b.lot_value(cur,dest);child0=b.lot_value(cur,child)
    gl=lambda:{k:b.gl(cur,k) for k in ['FG_INVENTORY','COGS','OTHER_EXPENSE','OTHER_INCOME']}
    g0=gl();truth=b.all_truth(cur);trial=b.bbp.receipt_trial
    invoice=trial.post_invoice(api,cur,trial.invoice(api,cur,today,dict(supplier_id=acc['supplier'],purchase_item_id=acc['item']),'100','3.00',date=f['day']+timedelta(days=1)))
    api.admin(cur);g1=gl();invoice_ok=b.lot_value(cur,dest)-parent0==6 and b.lot_value(cur,child)-child0==2 and g1['FG_INVENTORY']-g0['FG_INVENTORY']==4 and g1['COGS']-g0['COGS']==2 and g1['OTHER_EXPENSE']==g0['OTHER_EXPENSE']
    after_invoice=b.all_truth(cur)
    outstanding=one(cur,'select outstanding_id::text from erp.be_conversion_returns_v1 where conversion_id=%s',conv)
    state_before=one(cur,'select erp.be_conversion_value_state_v1(%s)',conv)
    received=bc.receive(cur,acc,'TEARDOWN',[(2,outstanding)],f['day']+timedelta(days=1),reference='BE actual teardown after sales')['lot_ids'][0]
    bc.inspect(cur,received,bc.local_at(f['day']+timedelta(days=1),10),'BE inspector',usable=2)
    price_payload=dict(lot_id=received,condition='USABLE',qty='2',unit_value='1.50',location_id=acc['main'],physical_at=bc.local_at(f['day']+timedelta(days=1),11),reason='BE sourced recovery valuation')
    pending=bc.refused(cur,lambda:bc.svc(cur,'VALUE_CUSTODY',price_payload),'BC_POLICY_PENDING')
    bc.policy(cur,'ACC_DEC03',dict(credit_account_id=bc.account(cur,'4100'),unit_value_cap='MOVING_AVERAGE'))
    v=bc.svc(cur,'VALUE_CUSTODY',price_payload);g2=gl();after_recovery=b.all_truth(cur)
    still_pending=one(cur,'select erp.be_return_progress_v1(%s)',conv)
    cap=bc.refused(cur,lambda:bc.receive(cur,acc,'TEARDOWN',[(2,outstanding)],f['day']+timedelta(days=1)),'BC_RETURN_EXCEEDS_SOURCE')
    bc.reverse(cur,v['document_id']);g3=gl()
    trial.rpc(api,cur,'reverse_material_supplier_invoice_v2',invoice['supplier_invoice_id'],'BE inverse invoice',uuid.uuid4(),invoice['row_version']);api.admin(cur)
    return b.verdict(dict(invoice_to_sold_and_child=invoice_ok,recovery_to_sold_and_child=g2['FG_INVENTORY']-g1['FG_INVENTORY']==-2 and g2['COGS']-g1['COGS']==-1,
      no_extra_income=g2['OTHER_INCOME']==g1['OTHER_INCOME'],policy=pending['ok'],capacity=cap['ok'],source_immutable=b.lot_value(cur,f['lot'])==source_hpp,
      sales_snapshots_immutable=snapshots==q(cur,'select id,total_hpp from erp.sale_stock_allocations where sale_item_id in(select id from erp.sales_items where sale_id in(%s,%s)) order by id',sale1,sale2),
      inverse_recovery=g3==g1,inverse_invoice=gl()==g0 and b.lot_value(cur,dest)==parent0 and b.lot_value(cur,child)==child0,
      provisional=state_before=='PROVISIONAL_RECOVERY' and len(still_pending)==1 and still_pending[0]['unreturned']=='1.000000' and still_pending[0]['awaiting_value']=='0.000000',
      truth=b.truth_quiet(truth,after_invoice) and b.truth_quiet(truth,after_recovery)),invoice_delta={k:g1[k]-g0[k] for k in g0},recovery_delta={k:g2[k]-g1[k] for k in g1},returns=still_pending,refusals=[pending,cap])
