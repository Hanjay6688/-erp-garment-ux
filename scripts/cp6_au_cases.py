"""Master lifecycle regressions and authority/history counterexamples."""
from datetime import timedelta
import uuid
import cp6_au_probe as review
import cp6_at_probe as attempt
import cp6_as_probe as dates
import cp6_ao_ap_installed as api
import cp6_initial_import_production_trial as production
import cp6_successor_regression as boundary

def fixture(cur,today,used=False):
 f=production.fixture(api,cur,today);_,sources=production.finalize(api,cur,f)
 product=cur.execute('select id,sku,model_id,brand_id,size_id from erp.products where sku=%s',(f['code'],)).fetchone()
 if not used:
  code=f['code']+'U';brand=cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s) returning id',(code,code)).fetchone()[0]
  pid=cur.execute('''insert into erp.products(sku,product_name,model_id,brand_id,size_id,color_name,is_active,effective_from)
     values(%s,%s,%s,%s,%s,'Blue',true,%s) returning id''',(code,code,product[2],brand,product[4],dates.invoice.at(today-timedelta(days=6),0))).fetchone()[0]
  product=(pid,code,product[2],brand,product[4])
 return f,sources,product

def edit(cur,p,effective,color='Green'):
 api.ordinary(cur)
 return cur.execute('select erp.edit_product_identity_effective(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
  (p[0],p[1],p[2],p[3],color,p[4],'AU lifecycle',effective,'AU exact lifecycle request')).fetchone()[0]

def cancel(cur,p):
 api.ordinary(cur)
 return cur.execute('select erp.cancel_product_identity_successor(%s,%s)',(p,'AU unused version cancellation')).fetchone()[0]

def extra(cur,today,variant):
 f,s,p=fixture(cur,today,variant.startswith('USED') or variant in ('REPLAY','FORGED_UPDATE','PHYSICAL_HISTORY','NAME_ONLY','CANCEL_USED','FORGED_CHILD_ID'))
 effective=cur.execute("select clock_timestamp()+interval '1 day'").fetchone()[0]
 before_identity=cur.execute('select sku,color_name,effective_from,effective_to from erp.products where id=%s',(p[0],)).fetchone()
 if variant=='NAME_ONLY':
  api.ordinary(cur)
  cur.execute('select erp.edit_product_identity_effective(%s,%s,%s,%s,%s,%s,%s,%s,%s)',(p[0],p[1],p[2],p[3],'Blue',p[4],'Display only',effective,'AU name only'))
  api.admin(cur)
  assert cur.execute('select sku,color_name,effective_from,effective_to from erp.products where id=%s',(p[0],)).fetchone()==before_identity
  return dict(status='PASS',identity_unchanged=True)
 if variant=='PRICE_REFERENCE':
  cur.execute('insert into erp.product_price_versions(product_id,price,effective_from) values(%s,1000,%s)',(p[0],effective))
 if variant=='CANCEL_USED':
  code=f['code']+'USED';brand=cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s) returning id',(code,code)).fetchone()[0]
  old,child=attempt.series(cur,code,p[2],brand,p[4],dates.invoice.at(today-timedelta(days=6),0),dates.invoice.at(today-timedelta(days=3),0))
  p=(child,code,p[2],brand,p[4])
  cur.execute('''insert into erp.fg_lots(lot_number,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,lot_origin)
      values(%s,%s,1,1,clock_timestamp(),'OTHER')''',('AU'+uuid.uuid4().hex,p[0]))
 if variant=='PHYSICAL_HISTORY':
  effective=cur.execute("select clock_timestamp()-interval '1 minute'").fetchone()[0]
  cur.execute('''insert into erp.fg_lots(lot_number,product_id,initial_qty_pcs,cached_qty_pcs,produced_at,lot_origin)
      values(%s,%s,1,1,clock_timestamp(),'OTHER')''',('AU'+uuid.uuid4().hex,p[0]))
 if variant in ('PRICE_REFERENCE','REPLAY'):
  result=edit(cur,p,effective);api.admin(cur)
  assert result!=p[0]
  old=cur.execute('select color_name,effective_to from erp.products where id=%s',(p[0],)).fetchone()
  assert old==('Blue',effective)
  after=boundary.snapshot(cur)
  assert edit(cur,p,effective)==result
  assert boundary.snapshot(cur)==after
  assert cur.execute('select count(*) from erp.product_identity_mutation_context_v1').fetchone()==(0,)
  if variant=='REPLAY':
   assert cancel(cur,result)==p[0];after=boundary.snapshot(cur)
   assert cancel(cur,result)==p[0];assert boundary.snapshot(cur)==after
  return dict(status='PASS',old_identity_preserved=True,exact_retry_no_mutation=True,unused_authority_rows=0)
 if variant=='FORGED_CHILD_ID':
  child=edit(cur,p,effective);api.admin(cur)
 before=boundary.snapshot(cur)
 def operation():
  api.ordinary(cur)
  if variant=='FORGED_CHILD_ID':return cur.execute('update erp.products set id=%s where id=%s',(uuid.uuid4(),child))
  if variant=='CANCEL_USED':return cancel(cur,p[0])
  if variant=='PHYSICAL_HISTORY':return edit(cur,p,effective)
  if variant=='FORGED_CONTEXT':
   return cur.execute("insert into erp.product_identity_mutation_context_v1 values(pg_backend_pid(),txid_current(),%s,'[]','[]')",(p[0],))
  cur.execute("select set_config('app.product_identity_controlled','on',true)")
  if variant=='FORGED_INSERT':
   return cur.execute('''insert into erp.products(sku,product_name,model_id,brand_id,size_id,color_name,is_active,effective_from,effective_to)
      values(%s,'Forged interval',%s,%s,%s,'Yellow',true,%s,%s)''',(p[1]+'FORGE',p[2],p[3],p[4],dates.invoice.at(today-timedelta(days=2),0),effective))
  if variant=='FORGED_UPDATE':return cur.execute('update erp.products set effective_to=%s where id=%s',(effective,p[0]))
  if variant=='FORGED_UNUSED':return cur.execute("update erp.products set color_name='Orange' where id=%s",(p[0],))
  if variant=='INVALID_CHILD':
   return cur.execute('select erp.cancel_product_identity_successor(%s,%s)',(uuid.uuid4(),'AU unknown product'))
  raise AssertionError(variant)
 _,error=attempt.attempt(cur,operation)
 assert error,(variant,'Unexpectedly accepted')
 assert boundary.snapshot(cur)==before
 if variant=='FORGED_CONTEXT':assert error['sqlstate']=='42501',error
 else:assert error['sqlstate']=='P0001',error
 return dict(status='PASS',refusal=error,all_boundary_unchanged=True)

def cases(cur,today):
 result=[('MASTER:'+v,lambda v=v:review.master_case(cur,today,v)) for v in ('DISPLAY_NAME','UNUSED_IDENTITY','USED_SUCCESSOR','CANCEL_FUTURE')]
 result += [('AU:'+v,lambda v=v:extra(cur,today,v)) for v in ('NAME_ONLY','PRICE_REFERENCE','CANCEL_USED','PHYSICAL_HISTORY','REPLAY','FORGED_CONTEXT','FORGED_INSERT','FORGED_UPDATE','FORGED_UNUSED','FORGED_CHILD_ID','INVALID_CHILD')]
 return result
