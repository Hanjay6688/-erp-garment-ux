"""Actual QC item -> inspection navigation; immutable Native owning inverse.

All outputs below come from Native cutting/sewing/laundry/QC commands. A
historical source outside the reader window is built by real QC executions.
"""
from datetime import timedelta
import json,uuid
import cp7_wip_source_cases as physical
import cp7_material_cases as material
b,auth=material.b,material.auth

def resolve(cur,kind,ident,subject=None):
 import cp7_transaction_source_cases as source
 return source.read(cur,kind,ident,subject)

def workspace(cur,q=None,subject=None):
 auth.actor(cur,subject)
 r=cur.execute("select public.erp_get_laundry_qc_workspace_v1('QC',%s)",(q,)).fetchone()[0]
 b.api.admin(cur);return r

def fixture(cur,today,history=False):
 if not history:
  f=physical.fixture(cur,today,finish=False)
 else:
  limit=workspace(cur)['collection_window']['transaction_limit']
  assert isinstance(limit,int)and 1<=limit<=500
  native=physical.b;f=native.two_size_fixture(cur,native.case_day(today),'CP7-QC-SOURCE',q1=limit+20,q2=10)
  b.api.admin(cur);f['product']=native.sized_product(cur,physical.base.SIZE,'QC-SOURCE-'+uuid.uuid4().hex[:8])
  payload=dict(distribution_batch_id=f['batch'],vendor_id=f['vendor'],wash_process_id=f['process'],target_dyeing_color='QC-SOURCE',
   physical_at=f['send'].isoformat(),reason='Actual QC history for exact source lookup',lines=[dict(size_id=physical.base.SIZE,qty_sent_pcs=limit+20)])
  sent=native.bd(cur,'POST_PRICED_DELIVERY',dict(delivery=payload,expected_version=str(physical.base.group_version(cur,f['group'])),pricing=dict(deferred=True)))
  f['delivery']=sent['delivery_id'];b.api.admin(cur)
  ds=native.one(cur,'select s.id::text from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where l.delivery_id=%s',f['delivery'])
  rec=native.chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=f['delivery'],wash_process_id=f['process'],physical_at=native.chain.production.at(f['day'],13).isoformat(),reason='Actual returned GOOD for every QC',
   lines=[dict(delivery_batch_size_line_id=ds,qty_good_received=limit+20,qty_bs_laundry=0,bs_product_id=None)]),physical.base.delivery_version(cur,f['delivery']))
  b.api.admin(cur);f['receipt']=rec['receipt_id'];f['receipt_line']=native.receipt_line(cur,f['receipt'])
  f['receipt_size']=native.one(cur,'select id::text from erp.laundry_receipt_batch_size_lines where receipt_line_id=%s',f['receipt_line']);f['reader_limit']=limit
 # Distinct economic timestamps ensure this first real QC is outside an
 # unfiltered newest-first window after the subsequent Native executions.
 target=physical.qc(cur,f,1,0,14);f['qc']=target['qc_inspection_id'];b.api.admin(cur)
 f['item']=str(cur.execute('select id from erp.qc_inspection_items where inspection_id=%s',(f['qc'],)).fetchone()[0])
 f['lot']=str(cur.execute('select id from erp.fg_lots where qc_item_id=%s',(f['item'],)).fetchone()[0])
 f['number']=cur.execute('select inspection_number from erp.qc_inspections where id=%s',(f['qc'],)).fetchone()[0]
 if history:
  for _ in range(f['reader_limit']):physical.qc(cur,f,1,0,15)
 f['lot_number']=cur.execute('select lot_number from erp.fg_lots where id=%s',(f['lot'],)).fetchone()[0]
 f['movement']=str(cur.execute("select id from erp.fg_stock_movements where source_type='QC_ITEM'and source_id=%s and movement_type='QC_GOOD'and reversal_of_id is null",(f['item'],)).fetchone()[0])
 return {k:f[k]for k in('qc','item','lot','lot_number','number','day','group','product','movement')}|dict(history=history,reader_limit=f.get('reader_limit'))

def observe(cur,f):
 b.api.admin(cur);cur.execute("set local timezone='UTC'")
 return dict(inspection=cur.execute('select to_jsonb(q)from erp.qc_inspections q where id=%s',(f['qc'],)).fetchone()[0],
  items=[row[0]for row in cur.execute('select to_jsonb(i)from erp.qc_inspection_items i where inspection_id=%s order by id',(f['qc'],)).fetchall()],
  original_movements=[row[0]for row in cur.execute("select to_jsonb(m)from erp.fg_stock_movements m where source_type='QC_ITEM'and source_id=%s and movement_type='QC_GOOD'and reversal_of_id is null order by id",(f['item'],)).fetchall()],
  inverse_movements=[row[0]for row in cur.execute('select to_jsonb(m)from erp.fg_stock_movements m where reversal_of_id=%s order by id',(f['movement'],)).fetchall()],
  lot_qty=str(cur.execute('select coalesce(sum(qty_signed),0)from erp.fg_stock_movements where lot_id=%s',(f['lot'],)).fetchone()[0]),business=b.boundary.snapshot(cur))

def reverse(cur,f,key=None,subject=None,version=None):
 if version is None:version=next(q for q in workspace(cur,f['number'],subject)['qc_history']if q['qc_inspection_id']==f['qc'])['row_version']
 auth.actor(cur,subject)
 r=cur.execute("select public.erp_save_laundry_qc_action_v1('REVERSE_FINAL_SKU',%s::jsonb,%s,%s)",
  (json.dumps(dict(qc_inspection_id=f['qc'],reason='Exact source QC inverse after inspection')),key or uuid.uuid4(),version)).fetchone()[0]
 b.api.admin(cur);return r

def cases(cur,today):
 def documents():
  f=fixture(cur,today);before=observe(cur,f)
  for kind,ident in [('QC_ITEM',f['item']),('QC_INSPECTION',f['qc'])]:
   r=resolve(cur,kind,ident);d=r['document'];assert r['business_DML']is False and d['domain']=='QC'and d['route']=='qc'and d['id']==f['qc']and d['number']==f['number']and d['focus']is None
  assert observe(cur,f)==before and before['lot_qty']=='1'
  key=str(uuid.uuid4());version=next(q for q in workspace(cur,f['number'])['qc_history']if q['qc_inspection_id']==f['qc'])['row_version']
  one=reverse(cur,f,key,version=version);assert reverse(cur,f,key,version=version)==one
  after=observe(cur,f);assert after['inspection']['status']=='REVERSED'and after['lot_qty']=='0'
  assert after['items']==before['items']and after['original_movements']==before['original_movements']
  assert before['inverse_movements']==[]and len(after['inverse_movements'])==1
  assert str(after['inverse_movements'][0]['qty_signed'])=='-1'and after['inverse_movements'][0]['reversal_of_id']==f['movement']
  assert resolve(cur,'QC_ITEM',f['item'])['document']['status']=='REVERSED'
  inverse=after['inverse_movements'][0];assert inverse['source_type']=='FG_MOVEMENT_REVERSAL'and inverse['source_id']==f['movement']
  assert resolve(cur,inverse['source_type'],inverse['source_id'])['document']['id']==f['qc']
  return dict(status='PASS',actual_QC_item_parent_no_DML=True,unchanged_Native_inverse_one_PCS_exact_UUID_and_original_history=True)
 def history():
  f=fixture(cur,today,True);first=workspace(cur);assert first['collection_window']['qc_history_truncated']is True and f['qc']not in[q['qc_inspection_id']for q in first['qc_history']]
  before=observe(cur,f);r=resolve(cur,'QC_ITEM',f['item']);exact=workspace(cur,r['document']['number']);assert[q['qc_inspection_id']for q in exact['qc_history']]==[f['qc']]
  assert exact['collection_window']['qc_history_truncated']is False and observe(cur,f)==before
  return dict(status='PASS',actual_Native_QC_executions=f['reader_limit']+1,actual_reader_limit=f['reader_limit'],source_outside_current_window_found_by_Native_query_no_DML=True)
 def authority():
  f=fixture(cur,today);subject,role=material.receipt.custom(cur,('production.final_sku.view',));r=resolve(cur,'QC_ITEM',f['item'],subject);assert r['document']['id']==f['qc']
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.final_sku.view'",(role,));before=b.boundary.snapshot(cur)
  auth.refused(cur,lambda:resolve(cur,'QC_ITEM',f['item'],subject),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED');assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',active_custom_QC_view_actual_current_revoke_no_parent_or_finance_leak=True)
 def unavailable():
  f=fixture(cur,today);before=b.boundary.snapshot(cur)
  for kind in('QC_ITEM','QC_INSPECTION'):auth.refused(cur,lambda kind=kind:resolve(cur,kind,str(uuid.uuid4())),'CP7_TRANSACTION_SOURCE_UNAVAILABLE')
  assert b.boundary.snapshot(cur)==before
  # No fake old output is created to prove legacy refusal. Actual imported
  # lineage is a separate acceptance branch rather than a guessed QC source.
  legacy=cur.execute('select inspection_id from erp.qc_inspection_items where source_laundry_receipt_batch_size_line_id is null limit 1').fetchone()
  if legacy:assert resolve(cur,'QC_INSPECTION',str(legacy[0]))['status']=='UNSUPPORTED_SOURCE'
  return dict(status='PASS',missing_actual_source_refused_no_DML=True,legacy_source_observed=bool(legacy),legacy_or_imported_output_not_claimed_as_complete_QC=True)
 return [('CP7_SOURCE_QC_DOCUMENTS',documents),('CP7_SOURCE_QC_HISTORY',history),('CP7_SOURCE_QC_AUTHORITY',authority),('CP7_SOURCE_QC_UNAVAILABLE',unavailable)]

def http_cases(http,today):
 def current():
  user=http.login('ADMIN','cp7-source-QC-current')
  with http.connect()as conn,conn.cursor()as cur:
   f=fixture(cur,today);role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(user.auth_user_id,)).fetchone()[0]
   cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'production.final_sku.view')on conflict do nothing",(role,));conn.commit()
  args=dict(p_source=dict(source_type='QC_ITEM',source_id=f['item']));r=user.rpc('erp_cp7_resolve_transaction_source_v1',args);assert r['status']==200 and r['body']['document']['id']==f['qc']
  own=user.rpc('erp_get_laundry_qc_workspace_v1',dict(p_scope='QC',p_query=f['number']));assert own['status']==200 and[q['qc_inspection_id']for q in own['body']['qc_history']]==[f['qc']]
  with http.connect()as conn,conn.cursor()as cur:
   cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.final_sku.view'",(role,));before=b.boundary.snapshot(cur);conn.commit()
  assert user.rpc('erp_cp7_resolve_transaction_source_v1',args)['status']==403
  assert user.rpc('erp_get_laundry_qc_workspace_v1',dict(p_scope='QC',p_query=f['number']))['status']==403
  with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',same_actual_ADMIN_JWT_exact_Native_QC_owner_and_current_revoke_no_DML=True)
 return [('CP7_SOURCE_QC_HTTP_CURRENT_VIEW',current)]
