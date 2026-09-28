"""Real purchase, return and payment oracles for portable supplier credit."""
import json,uuid
from datetime import timedelta
from psycopg.types.json import Jsonb
import cp6_bf_probe as bf
from cp6_bd_modes import _fixture_usage
b=bf.b;one=bf.one;bc=b.bcp

def fixture(cur,today,fabric=False):
    fx=bc.fixture(cur,today,purchase=False,zones=False)
    if fabric:
        unit=one(cur,"select unit_code from erp.uom_definitions where dimension='LENGTH' and is_active order by unit_code limit 1")
        fx['material']=str(one(cur,"insert into erp.materials(material_sku,material_name,material_type,unit_code) values(%s,'BF fabric credit','FABRIC',%s) returning id",'CR-'+uuid.uuid4().hex[:12],unit))
    purchases=[]
    for rate in ('10.00','10.00','6.00'):
        line=dict(material_id=fx['material'],qty=10,unit_price=rate,price_state='FINAL',price_source='SUPPLIER_INVOICE')
        if fabric:line['rolls']=[dict(roll_number='CR-'+uuid.uuid4().hex[:12],qty=10)]
        saved=bc.internal(cur,'save_material_purchase_draft_v2',Jsonb(dict(purchase_number='CR-'+uuid.uuid4().hex[:12],supplier_id=fx['supplier'],location_id=fx['main'],
          physical_at=bc.local_at(fx['received'],9),change_reason='Supplier credit fixture receipt',lines=[line])),str(uuid.uuid4()),None)
        bc.internal(cur,'post_material_purchase_v2',saved['purchase_id'],str(uuid.uuid4()),saved['row_version'],'Supplier credit receipt post')
        purchases.append(saved['purchase_id'])
    ret=str(uuid.uuid4());item=one(cur,'select id::text from erp.material_purchase_items where purchase_id=%s',purchases[0])
    roll=one(cur,'select id::text from erp.material_rolls where purchase_item_id=%s',item) if fabric else None
    cur.execute("insert into erp.material_supplier_returns(id,return_number,supplier_id,location_id,physical_at,status,reason) values(%s,%s,%s,%s,%s,'DRAFT','Supplier responsibility return')",
      (ret,'CR-RETURN-'+ret,fx['supplier'],fx['main'],bc.local_at(today-timedelta(days=2),9)))
    cur.execute('insert into erp.material_supplier_return_items(return_id,material_id,roll_id,qty,purchase_item_id,supplier_credit_unit_price) values(%s,%s,%s,2,%s,10)',(ret,fx['material'],roll,item))
    bc.internal(cur,'post_material_supplier_return',ret)
    return dict(fx,purchases=purchases,ret=ret)

def call(cur,payload,key=None,auth=None):
    if auth:bc.session(cur,auth)
    else:b.chain.production.owner(cur)
    result=one(cur,'select public.erp_save_supplier_credit_v1(%s::jsonb,%s)',json.dumps(payload),key or str(uuid.uuid4()))
    b.api.admin(cur);return result

def payload(cur,f,allocations):
    return dict(return_id=f['ret'],source_purchase_id=f['purchases'][0],expected_version=one(cur,'select erp.bf_supplier_credit_revision_v1(%s)',f['ret']),
      allocations=[dict(purchase_id=p,amount=a) for p,a in allocations],reason='Owner reallocates supplier return credit')

def state(cur,f):
    return dict(ap=[str(one(cur,'select round(erp.material_purchase_final_ap_total(%s),2)',p)) for p in f['purchases']],
      stock=str(one(cur,'select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=%s',f['material'])),
      values=one(cur,"select coalesce(jsonb_agg(jsonb_build_array(id,unit_cost_snapshot,qty_signed*unit_cost_snapshot) order by id),'[]') from erp.material_stock_movements where material_id=%s",f['material']),
      ledger=str(one(cur,"select coalesce(sum(credit_total-debit_total),0) from erp.account_daily_balances where account_id=erp.account_id('AP_SUPPLIER')")))

def allocation(cur,today,fabric=False):
    f=fixture(cur,today,fabric);a,z,k=f['purchases'];before=state(cur,f)
    request=payload(cur,f,[(z,'12.00'),(k,'8.00')]);key=str(uuid.uuid4());first=call(cur,request,key);again=call(cur,request,key)
    split=state(cur,f)
    wrong=payload(cur,f,[(z,'20.01')]);refused=b.refused(cur,lambda:call(cur,wrong),'BF_CREDIT_EXCEEDS_RETURN')
    stale=b.refused(cur,lambda:call(cur,request),'STALE_VERSION')
    held=b.refused(cur,lambda:bc.internal(cur,'reverse_material_supplier_return',f['ret'],'No orphaned allocation'),'BF_CREDIT_RETURN_IN_USE')
    restored=call(cur,payload(cur,f,[]));after=state(cur,f)
    checks=dict(original=before['ap']==['80.00','100.00','60.00'],split=split['ap']==['100.00','88.00','52.00'],
      amount_once=split['ledger']==before['ledger'],stock_once=b.D(split['stock'])==b.D(before['stock'])==28,hpp_unchanged=split['values']==before['values'],
      replay=again['replayed'] and first['version']==again['version'],over_credit=refused['ok'],stale=stale['ok'],return_dependency=held['ok'],original_restored=after==before,
      history=one(cur,'select count(*) from erp.bf_supplier_credit_moves_v1 where return_id=%s',f['ret'])==4)
    return b.verdict(checks,fabric=fabric,before=before,split=split,after=after)

def cash_and_reallocation(cur,today):
    f=fixture(cur,today);a,z,k=f['purchases']
    call(cur,payload(cur,f,[(z,'20.00')]))
    pay=bc.supplier_payment(cur,z,'80.00',f['cash'],today)
    bc.internal(cur,'post_supplier_payment',pay)
    paid=state(cur,f);call(cur,payload(cur,f,[(k,'20.00')]))
    shifted=state(cur,f)
    # The paid purchase now owes 20 again; the new target receives that credit.
    balances=[one(cur,'select round(erp.material_purchase_final_ap_total(%s),2)-coalesce((select sum(amount) from erp.supplier_payments where purchase_id=%s and status=\'POSTED\'),0)',p,p) for p in f['purchases']]
    origin_pay=bc.supplier_payment(cur,a,'100.00',f['cash'],today);bc.internal(cur,'post_supplier_payment',origin_pay)
    blocked=b.refused(cur,lambda:call(cur,payload(cur,f,[])),'BF_CREDIT_TARGET_ALREADY_PAID')
    bc.internal(cur,'reverse_supplier_payment',origin_pay,'Release original payment before moving credit back')
    call(cur,payload(cur,f,[]))
    truth=b.q(cur,"select check_name,issue_count from erp.run_v267_financial_truth_checks() where check_name in('V267_AP_GL_SUBLEDGER_MISMATCH','V267_PAYMENT_EXCEEDS_FINAL_AP','V2620M_SUPPLIER_PAYMENT_EXACT_STATUS')")
    return b.verdict(dict(balances=balances==[100,20,40],net_ap_unchanged=paid['ledger']==shifted['ledger'],stock_costs_unchanged=paid['values']==shifted['values'],
      no_double_use=blocked['ok'],original_restored=state(cur,f)['ap']==['80.00','100.00','60.00'],financial_truth=all(n==0 for _,n in truth)),truth=truth)

def race(tools,today,commit):
    with tools.connect() as conn,conn.cursor() as cur:
        with _fixture_usage(cur):f=fixture(cur,today)
        a=payload(cur,f,[(f['purchases'][1],'20.00')]);z=payload(cur,f,[(f['purchases'][2],'20.00')]);conn.commit()
    held,contention,outcome=tools.two_sessions(lambda cur:call(cur,a),lambda cur:call(cur,z),commit)
    with tools.connect() as conn,conn.cursor() as cur:after=state(cur,f);conn.rollback()
    from cp6_bd_modes import _verdict
    return _verdict('SUPPLIER_CREDIT_ONE_BALANCE',commit,held,contention,outcome,'STALE_VERSION',after,
      after['ap']==(['100.00','80.00','60.00'] if commit else ['100.00','100.00','40.00']))
