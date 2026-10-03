"""Actual QC queue -> owning Laundry receipt. No new physical/money writer.

Native cutting/sewing/send/receipt commands create every physical observation.
The existing inverse owns WIP, pricing/HPP and all current dependency guards.
"""
import json,uuid
import cp7_wip_source_cases as physical
import cp7_material_cases as material
b,auth=material.b,material.auth
KINDS=('LAUNDRY_DELIVERY','LAUNDRY_DELIVERY_LINE','LAUNDRY_DELIVERY_BATCH_SIZE_LINE',
 'LAUNDRY_RECEIPT','LAUNDRY_RECEIPT_LINE','LAUNDRY_RECEIPT_BATCH_SIZE_LINE')

def resolve(cur,kind,ident,subject=None):
 import cp7_transaction_source_cases as source
 return source.read(cur,kind,ident,subject)

def workspace(cur,q=None,subject=None):
 auth.actor(cur,subject)
 r=cur.execute("select public.erp_get_laundry_qc_workspace_v1('LAUNDRY',%s)",(q,)).fetchone()[0]
 b.api.admin(cur);return r

def fixture(cur,today):
 f=physical.fixture(cur,today,finish=False);b.api.admin(cur)
 f['delivery_number'],f['group_number']=cur.execute('select d.delivery_number,g.group_number from erp.laundry_deliveries d join erp.laundry_delivery_lines l on l.delivery_id=d.id join erp.cutting_groups g on g.id=l.cutting_group_id where d.id=%s',(f['delivery'],)).fetchone()
 f['receipt_number']=cur.execute('select receipt_number from erp.laundry_receipts where id=%s',(f['receipt'],)).fetchone()[0]
 f['delivery_line'],f['delivery_size']=map(str,cur.execute('select l.id,s.id from erp.laundry_delivery_lines l join erp.laundry_delivery_batch_size_lines s on s.delivery_line_id=l.id where l.delivery_id=%s',(f['delivery'],)).fetchone())
 return f

def selected(cur,f,subject=None):
 d=next(x for x in workspace(cur,f['delivery_number'],subject)['deliveries']if x['delivery_id']==f['delivery'])
 return d,next(r for r in d['receipts']if r['id']==f['receipt'])

def observe(cur,f):
 b.api.admin(cur);cur.execute("set local timezone='UTC'")
 rows=lambda sql,param:[row[0]for row in cur.execute(sql,(param,)).fetchall()]
 original=rows("select to_jsonb(w)from erp.wip_stage_events w where w.source_type='LAUNDRY_RECEIPT_LINE'and w.source_id=%s order by id",f['receipt_line'])
 inverses=rows("select to_jsonb(w)from erp.wip_stage_events w where w.source_type='CP6_LAUNDRY_RECEIPT_WIP_REVERSAL'and w.source_id in(select id from erp.wip_stage_events where source_type='LAUNDRY_RECEIPT_LINE'and source_id=%s)order by id",f['receipt_line'])
 return dict(delivery=cur.execute('select to_jsonb(d)from erp.laundry_deliveries d where id=%s',(f['delivery'],)).fetchone()[0],
  receipt=cur.execute('select to_jsonb(r)from erp.laundry_receipts r where id=%s',(f['receipt'],)).fetchone()[0],
  receipt_lines=rows('select to_jsonb(l)from erp.laundry_receipt_lines l where receipt_id=%s order by id',f['receipt']),
  receipt_sizes=rows('select to_jsonb(s)from erp.laundry_receipt_batch_size_lines s where receipt_line_id=%s order by id',f['receipt_line']),
  original_WIP=original,inverse_WIP=inverses,business=b.boundary.snapshot(cur))

def reverse(cur,f,key=None,subject=None,version=None):
 if version is None:version=selected(cur,f,subject)[1]['row_version']
 auth.actor(cur,subject)
 r=cur.execute("select public.erp_save_laundry_qc_action_v1('REVERSE_RECEIPT',%s::jsonb,%s,%s)",
  (json.dumps(dict(receipt_id=f['receipt'],reason='Wrong physical receipt after source inspection')),key or uuid.uuid4(),version)).fetchone()[0]
 b.api.admin(cur);return r

def cases(cur,today):
 def documents():
  f=fixture(cur,today);before=observe(cur,f)
  refs=[('LAUNDRY_DELIVERY',f['delivery']),('LAUNDRY_DELIVERY_LINE',f['delivery_line']),('LAUNDRY_DELIVERY_BATCH_SIZE_LINE',f['delivery_size']),
   ('LAUNDRY_RECEIPT',f['receipt']),('LAUNDRY_RECEIPT_LINE',f['receipt_line']),('LAUNDRY_RECEIPT_BATCH_SIZE_LINE',f['receipt_size'])]
  for kind,ident in refs:
   r=resolve(cur,kind,ident);d=r['document'];assert r['business_DML']is False and d['domain']=='LAUNDRY'and d['route']=='laundry'and d['id']==f['delivery']and d['number']==f['delivery_number']
   if 'RECEIPT'in kind:assert d['focus']==dict(kind='LAUNDRY_RECEIPT',id=f['receipt'],page_offset=0)
   else:assert d['focus']is None
  assert observe(cur,f)==before
  delivery,receipt=selected(cur,f);assert delivery['returned_qty_pcs']==30 and receipt['reversible']is True
  key=str(uuid.uuid4());version=receipt['row_version'];one=reverse(cur,f,key,version=version);assert reverse(cur,f,key,version=version)==one
  after=observe(cur,f);assert after['receipt']['status']=='REVERSED'
  assert after['receipt_lines']==before['receipt_lines']and after['receipt_sizes']==before['receipt_sizes']and after['original_WIP']==before['original_WIP']
  assert len(before['original_WIP'])==1 and before['original_WIP'][0]['qty_pcs']==30 and before['inverse_WIP']==[]and len(after['inverse_WIP'])==1
  original,inverse=before['original_WIP'][0],after['inverse_WIP'][0]
  assert inverse['source_id']==original['id']and inverse['qty_pcs']==30 and(inverse['stage_from'],inverse['stage_to'])==('QC','LAUNDRY')
  delivery,receipt=selected(cur,f);assert delivery['returned_qty_pcs']==0 and receipt['status']=='REVERSED'and receipt['reversible']is False
  assert resolve(cur,'LAUNDRY_RECEIPT',f['receipt'])['document']['focus']['id']==f['receipt']
  return dict(status='PASS',all_six_actual_Native_child_FKs_no_DML=True,exact_delivery_query_and_embedded_receipt=True,unchanged_owning_inverse_exact_UUID_one30_PCS_WIP_effect=True,original_lines_sizes_WIP_retained=True)
 def dependencies():
  f=fixture(cur,today);qc=physical.qc(cur,f,1,0,14);delivery,receipt=selected(cur,f)
  assert receipt['reversible']is False and 'QC'in receipt['reversal_blocker']
  before=observe(cur,f);auth.refused(cur,lambda:reverse(cur,f),'QC');assert observe(cur,f)==before
  # The unchanged owning QC inverse must clear its actual dependency first.
  auth.actor(cur)
  w=cur.execute("select public.erp_get_laundry_qc_workspace_v1('QC',null)").fetchone()[0]
  q=next(x for x in w['qc_history']if x['qc_inspection_id']==qc['qc_inspection_id'])
  cur.execute("select public.erp_save_laundry_qc_action_v1('REVERSE_FINAL_SKU',%s::jsonb,%s,%s)",
   (json.dumps(dict(qc_inspection_id=q['qc_inspection_id'],reason='Actual downstream QC correction before receipt')),uuid.uuid4(),q['row_version']))
  b.api.admin(cur);assert selected(cur,f)[1]['reversible']is True
  reverse(cur,f);assert observe(cur,f)['receipt']['status']=='REVERSED'
  return dict(status='PASS',actual_active_QC_dependency_named_by_Native_reader=True,unsafe_parent_inverse_refused_full_state_unchanged=True,unchanged_owning_QC_then_explicit_receipt_inverse=True,no_browser_inverse_chain_claimed_atomic=True)
 def authority():
  f=fixture(cur,today);subject,role=material.receipt.custom(cur,('production.laundry.view',))
  assert resolve(cur,'LAUNDRY_RECEIPT_BATCH_SIZE_LINE',f['receipt_size'],subject)['document']['id']==f['delivery']
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.laundry.view'",(role,));before=b.boundary.snapshot(cur)
  for kind,ident in [('LAUNDRY_RECEIPT',f['receipt']),('LAUNDRY_DELIVERY',f['delivery'])]:auth.refused(cur,lambda kind=kind,ident=ident:resolve(cur,kind,ident,subject),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_custom_role_current_view_before_parent_child_resolution=True,revoked_view_no_header_or_finance_leak_or_DML=True)
 def unavailable():
  f=fixture(cur,today);before=b.boundary.snapshot(cur)
  for kind in KINDS:auth.refused(cur,lambda kind=kind:resolve(cur,kind,str(uuid.uuid4())),'CP7_TRANSACTION_SOURCE_UNAVAILABLE')
  auth.refused(cur,lambda:resolve(cur,'LAUNDRY_RECEIPT',f['delivery']),'CP7_TRANSACTION_SOURCE_UNAVAILABLE')
  assert b.boundary.snapshot(cur)==before
  legacy=cur.execute('select l.delivery_id from erp.laundry_delivery_lines l where not exists(select 1 from erp.laundry_delivery_batch_size_lines s where s.delivery_line_id=l.id)limit 1').fetchone()
  if legacy:assert resolve(cur,'LAUNDRY_DELIVERY',str(legacy[0]))['status']=='UNSUPPORTED_SOURCE'
  return dict(status='PASS',all_six_missing_sources_and_wrong_kind_UUID_refused_no_DML=True,actual_legacy_source_observed=bool(legacy),legacy_batch_mapping_not_fabricated=True)
 return [('CP7_SOURCE_LAUNDRY_DOCUMENTS',documents),('CP7_SOURCE_LAUNDRY_DEPENDENCIES',dependencies),('CP7_SOURCE_LAUNDRY_AUTHORITY',authority),('CP7_SOURCE_LAUNDRY_UNAVAILABLE',unavailable)]

def http_cases(http,today):
 def current():
  user=http.login('ADMIN','cp7-source-Laundry-current')
  with http.connect()as conn,conn.cursor()as cur:
   f=fixture(cur,today);role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(user.auth_user_id,)).fetchone()[0]
   cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'production.laundry.view')on conflict do nothing",(role,));conn.commit()
  args=dict(p_source=dict(source_type='LAUNDRY_RECEIPT',source_id=f['receipt']));r=user.rpc('erp_cp7_resolve_transaction_source_v1',args)
  assert r['status']==200 and r['body']['document']['id']==f['delivery']and r['body']['document']['focus']==dict(kind='LAUNDRY_RECEIPT',id=f['receipt'],page_offset=0)
  own=user.rpc('erp_get_laundry_qc_workspace_v1',dict(p_scope='LAUNDRY',p_query=r['body']['document']['number']))
  assert own['status']==200 and any(d['delivery_id']==f['delivery']and any(x['id']==f['receipt']for x in d['receipts'])for d in own['body']['deliveries'])
  with http.connect()as conn,conn.cursor()as cur:
   cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.laundry.view'",(role,));before=b.boundary.snapshot(cur);conn.commit()
  assert user.rpc('erp_cp7_resolve_transaction_source_v1',args)['status']==403
  assert user.rpc('erp_get_laundry_qc_workspace_v1',dict(p_scope='LAUNDRY',p_query=f['delivery_number']))['status']==403
  with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_ADMIN_JWT_exact_Laundry_parent_and_child=True,same_token_current_view_revoke_both_readers_403_no_DML=True)
 return [('CP7_SOURCE_LAUNDRY_HTTP_CURRENT_VIEW',current)]
