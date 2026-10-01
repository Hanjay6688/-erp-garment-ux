"""O06/O07 arithmetic against actual Native stock, sales and shared planning.

Future demand is an explicitly selected owner scenario. Master records are
administrative fixture setup; stock, reservations, posting and cancellation
use the accepted Native writers. No planner DTO or financial balance is seeded.
"""
from datetime import timedelta
from decimal import Decimal as D
import uuid
import cp7_planning_history_cases as history
import cp7_planning_netting_cases as netting

baseline=netting.baseline
sales=history.sales
b=history.b

def select_profiles(cur,daily_by_root):
 source=cur.execute('select cp7_baseline_native.source()').fetchone()[0]
 roots=[p['root_id']for p in source['facts']['products']]
 for p in baseline.get(cur,roots)['rows']:
  baseline.save(cur,dict(root_id=p['root_id'],product_version_id=p['product_version_id'],expected_revision=p['revision'],
   reason='Frozen O06/O07 explicit selected future-demand scenario; comparison-root zero is an assumption',
   config=dict(mean_mode='SELECTED_MANUAL',daily_pcs=str(daily_by_root.get(p['root_id'],0)),
    minimum_available_days='20',lead_days='3',review_days='7',buffer_days='0')))

def observe(cur,today,root,expected_stock,projected):
 before=b.boundary.snapshot(cur)
 run=netting.capture(cur,today)
 assert b.boundary.snapshot(cur)==before,'PLANNER_CHANGED_NATIVE_BUSINESS_STATE'
 row=netting.row(run,root)
 assert row['profile']['quality']=='SELECTED_ASSUMPTION'and row['target']['status']=='SCENARIO',row
 native=sales.fg.workspace(cur,dict(sku=cur.execute('select sku from erp.products where id=%s',(root,)).fetchone()[0]))
 assert sales.fg.qty(native)==expected_stock,native
 assert D(row['available_fg_pcs'])==expected_stock[2],row
 assert D(row['timeline']['end_balance_pcs'])==projected,row
 assert run['apply_enabled']is False and row['apply_enabled']is False
 return run,row

def size_sources(cur,today):
 # Two roots share one brand/model/color and one real commercial SKU. Give them
 # distinct Native size identities before any stock exists.
 root_s,_=sales.fg.ax.owner_only_model_product(cur,effective_from=today-timedelta(days=10))
 b.api.admin(cur);root_l=str(uuid.uuid4());tag='O07-'+uuid.uuid4().hex[:10];sizes=[]
 model=cur.execute('select model_id from erp.products where id=%s',(root_s,)).fetchone()[0]
 for i,label in enumerate(('S','L')):
  sid=str(uuid.uuid4());sizes.append(sid)
  cur.execute('insert into erp.sizes(id,size_code,sort_order,is_active)values(%s,%s,%s,true)',(sid,tag+'-'+label,200+i))
  cur.execute('insert into erp.product_model_sizes(model_id,size_id,sort_order)values(%s,%s,%s)',(model,sid,200+i))
 cur.execute('update erp.products set size_id=%s where id=%s',(sizes[0],root_s))
 cur.execute("""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from,is_active,is_portal_visible)
  select %s,%s,model_id,brand_id,color_name,%s,'O07 Native L',%s,effective_from,true,true from erp.products where id=%s""",
  (root_l,tag+'-L',sizes[1],root_l,root_s))
 cur.execute("insert into erp.accessory_bom_versions(product_id,version_label,effective_from,is_active,notes)values(%s,'O07-EMPTY','2026-01-01',true,'Explicit empty BOM')",(root_l,))
 at=history.receipt.aa.at(today-timedelta(days=1),6)
 group=netting.bf.group(cur,[root_s,root_l],at,settings=dict(price=None,bom=None,work_rates=[],laundry_rates=[]))
 netting.bf.save(cur,[group],at)
 for root,qty in((root_s,25),(root_l,5)):
  sales.fg.ax.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=root,location_id=sales.fg.base.LOCATION,
   qty_pcs=qty,physical_at=history.receipt.aa.at(today-timedelta(days=1),8).isoformat(),reason='O07 actual Native size stock',
   owner_unit_value='10',owner_value_reason='O07 explicit owner source value'))
  b.api.admin(cur)
 return root_s,root_l,sizes,group['id']

def cases(cur,today):
 def reservation_once():
  f=history.fixture(cur,today,qty=24,stock=100);select_profiles(cur,{f['product']:2})
  first,x=observe(cur,today,f['product'],[100,24,76],D(100)-24-20)
  assert D(x['target']['target_pcs'])==20,x
  stored=cur.execute('select facts,result from cp7_netting_native.runs where id=%s',(first['run_id'],)).fetchone()
  sales.fg.post_sale(cur,f['draft'])
  _,posted=observe(cur,today,f['product'],[76,0,76],D(100)-24-20)
  old=netting.read(cur,first['run_id'])
  assert old['source_state']=='ARCHIVED_STALE'and D(netting.row(old,f['product'])['timeline']['end_balance_pcs'])==56,old
  assert cur.execute('select facts,result from cp7_netting_native.runs where id=%s',(first['run_id'],)).fetchone()==stored
  cancelled=history.fixture(cur,today,qty=24,stock=100);select_profiles(cur,{cancelled['product']:2})
  observe(cur,today,cancelled['product'],[100,24,76],D(100)-24-20)
  sales.fg.cancel(cur,cancelled['draft'])
  observe(cur,today,cancelled['product'],[100,0,100],D(100)-20)
  return dict(status='PASS',oracle='O06',native_draft=[100,24,76],selected_residual_future_demand=20,
   draft_projected=56,posted_projected=56,cancelled_projected=80,posted_available=posted['available_fg_pcs'],
   same_native_reservation_not_subtracted_twice=True,stored_source_cut_immutable=True)
 def size_gap():
  root_s,root_l,sizes,sku=size_sources(cur,today);select_profiles(cur,{root_s:1,root_l:2})
  _,s=observe(cur,today,root_s,[25,0,25],D(25)-10)
  _,l=observe(cur,today,root_l,[5,0,5],D(5)-20)
  assert [s['size_id'],l['size_id']]==sizes and s['target_key']!=l['target_key'],(s,l)
  assert D(s['target']['target_pcs'])==10 and D(l['target']['target_pcs'])==20
  assert D(s['base_gap_pcs'])==0 and D(l['base_gap_pcs'])==15,(s,l)
  members=cur.execute('select m.product_root::text from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id where v.sku_id=%s order by 1',(sku,)).fetchall()
  assert {r[0]for r in members}=={root_s,root_l},members
  return dict(status='PASS',oracle='O07',same_native_commercial_sku=sku,native_size_stock=[25,5],
   selected_size_need=[10,20],independent_arithmetic=dict(surplus_s=25-10,gap_l=20-5,aggregate_stock=25+5),
   native_timeline=[s['timeline']['end_balance_pcs'],l['timeline']['end_balance_pcs']],
   native_size_gaps=[s['base_gap_pcs'],l['base_gap_pcs']],aggregate_sku_does_not_hide_l_gap=True)
 return [('O06_NATIVE_RESERVATION_PLANNER_ONCE',reservation_once),('O07_NATIVE_SAME_SKU_SIZE_GAP',size_gap)]
