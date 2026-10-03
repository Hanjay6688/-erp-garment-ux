"""Posted cutting metadata -> existing Native ALL distribution history.

Only masters/drafts are prepared by fixture setup. Receipt, cutting issue,
pickup and QC effects use actual Native writers; no stock/money outcome is
seeded. These three DB and two Auth cases add to every earlier source case.
"""
from datetime import timedelta
import uuid
import cp7_qc_source_cases as qc
import cp7_material_cases as material
b,auth=material.b,material.auth

def source(cur,kind,ident,subject=None):
 import cp7_transaction_source_cases as navigation
 return navigation.read(cur,kind,ident,subject)

def queue(cur,offset=0,subject=None):
 auth.actor(cur,subject)
 r=cur.execute("select public.erp_get_cutting_pickup_queue_v1('ALL',null,null,100,%s)",(offset,)).fetchone()[0]
 b.api.admin(cur);return r

def posted(cur,today,post=True):
 prod=qc.physical.b.chain.production;base=qc.physical.base
 f=prod.estimated_receipt(cur,today);b.api.admin(cur)
 day=f['purchase_day']+timedelta(days=1);po=str(uuid.uuid4())
 cur.execute("insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes) values(%s,%s,%s,10,'CUTTING','CUTTING',%s,'CP7 source fixture')",
  (po,'CP7-SRC-CUT-'+po,prod.MODEL,prod.at(day,7)))
 payload=dict(action='SAVE_DRAFT',po_id=po,pattern_id=prod.PATTERN,source_location_id=f['location'],cut_at=prod.at(day,8),
  change_reason='Actual posted cutting source fixture',size_slots=[dict(slot_no=1,size_id=base.SIZE,drawing_no=1)],
  rolls=[dict(roll_id=f['roll'],qty_issued=10,qty_consumed=10,qty_reported_remaining=0,yields=[dict(slot_no=1,qty_pcs=10)])])
 saved=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',payload)
 if post:saved=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(payload,id=saved['cutting_group_id'],action='POST'),expected_version=int(saved['row_version']))
 b.api.admin(cur)
 return dict(group=saved['cutting_group_id'],po=po,post=post)

def document(cur,f,kind='CUTTING_GROUP',subject=None):
 r=source(cur,kind,f['group'],subject);d=r['document']
 assert r['status']=='AVAILABLE' and r['business_DML']is False
 assert set(d)=={'domain','route','id','number','status','revision','focus'}
 assert d['domain']=='CUTTING'and d['route']=='mandor-wip'and d['id']==f['group']
 assert set(d['focus'])=={'kind','id','parent_id','page_offset'}
 assert d['focus']['kind']=='CUTTING_GROUP'and d['focus']['id']==f['group']and d['focus']['parent_id']==f['po']
 w=queue(cur,d['focus']['page_offset'],subject)
 row=next(x for x in w['rows']if x['cutting_group_id']==f['group'])
 assert row['po_id']==f['po']and row['group_number']==d['number']and row['status']==d['status']and str(row['row_version'])==d['revision']
 return d,row

def advanced(cur,today):
 f=qc.fixture(cur,today);b.api.admin(cur)
 po,number=cur.execute('select po_id,group_number from erp.cutting_groups where id=%s',(f['group'],)).fetchone()
 f['po'],f['group_number']=str(po),number
 f['receipt_id']=str(cur.execute('select l.receipt_id from erp.qc_inspection_items i join erp.laundry_receipt_batch_size_lines s on s.id=i.source_laundry_receipt_batch_size_line_id join erp.laundry_receipt_lines l on l.id=s.receipt_line_id where i.id=%s',(f['item'],)).fetchone()[0])
 move=cur.execute("select id,material_id,roll_id,location_id from erp.material_stock_movements where source_type='CUTTING_GROUP'and source_id=%s and movement_type='CUTTING_ISSUE'order by id limit 1",(f['group'],)).fetchone();assert move
 f['material_movement'],f['material'],f['roll'],f['location']=map(str,move)
 f['material_sku']=cur.execute('select material_sku from erp.materials where id=%s',(f['material'],)).fetchone()[0]
 f['roll_number']=cur.execute('select roll_number from erp.material_rolls where id=%s',(f['roll'],)).fetchone()[0]
 j=cur.execute("select id,journal_number,transaction_date from erp.journal_entries where source_type='CUTTING_MATERIAL_ISSUE'and source_id=%s and status='POSTED'order by id limit 1",(f['group'],)).fetchone();assert j
 f['journal_id'],f['journal_number'],f['journal_date']=str(j[0]),j[1],str(j[2])
 return f

def browser_fixture(cur,today):
 f=advanced(cur,today);unpicked=posted(cur,today);d,row=document(cur,unpicked)
 assert row['pickup']is None and row['picked_up_at']is None
 j=cur.execute("select id,journal_number,transaction_date from erp.journal_entries where source_type='CUTTING_MATERIAL_ISSUE'and source_id=%s and status='POSTED'order by id limit 1",(unpicked['group'],)).fetchone();assert j
 unpicked.update(group_number=d['number'],journal_id=str(j[0]),journal_number=j[1],journal_date=str(j[2]),Native_row=row)
 f['unpicked']=unpicked;return f

def cases(cur,today):
 def exact():
  f=advanced(cur,today);before=b.boundary.snapshot(cur)
  for kind in ('CUTTING_GROUP','CUTTING_MATERIAL_ISSUE'):
   d,row=document(cur,f,kind);assert row['picked_up_at']is not None and row['pickup']['status']=='POSTED'
  auth.actor(cur)
  draft=cur.execute('select public.erp_get_cutting_workspace_v2(p_selected_draft_id=>%s)',(f['group'],)).fetchone()[0]
  b.api.admin(cur)
  assert draft['selected_draft']is None
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_cut_issue_and_journal_same_Native_group_PO=True,after_pickup_and_QC_history_readable_not_cutting_draft=True,complete_business_boundary_unchanged=True)
 def page():
  groups=[posted(cur,today)['group']for _ in range(101)]
  group,po=cur.execute('select id::text,po_id::text from erp.cutting_groups where id=any(%s::uuid[])order by cut_at desc,group_number desc,id desc limit 1',(groups,)).fetchone()
  f=dict(group=group,po=po);before=b.boundary.snapshot(cur);d,row=document(cur,f)
  assert d['focus']['page_offset']>=100 and d['focus']['page_offset']%100==0
  first=queue(cur,0);assert len(first['rows'])==100 and group not in[x['cutting_group_id']for x in first['rows']]
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual101_Native_cut_posts_exact_target_outside_first100=True,Native_ALL_order_page_and_PO_rechecked=True,page_offset=d['focus']['page_offset'],no_business_write_from_navigation=True)
 def authority():
  f=posted(cur,today);subject,role=auth.custom_actor(cur)
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'production.cutting.view')",(role,))
  auth.refused(cur,lambda:source(cur,'CUTTING_GROUP',f['group'],subject),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'production.distribution.view')",(role,))
  document(cur,f,subject=subject)
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.distribution.view'",(role,))
  for ident in (f['group'],str(uuid.uuid4())):auth.refused(cur,lambda:source(cur,'CUTTING_GROUP',ident,subject),'CP7_TRANSACTION_SOURCE_ACCESS_DENIED')
  missing=str(uuid.uuid4());auth.refused(cur,lambda:source(cur,'CUTTING_GROUP',missing),'CP7_TRANSACTION_SOURCE_UNAVAILABLE')
  unposted=posted(cur,today,False);r=source(cur,'CUTTING_GROUP',unposted['group']);assert r['status']=='UNSUPPORTED_SOURCE'and r['document']is None
  assert not cur.execute("select has_function_privilege('cp7_transaction_source_read','public.erp_save_cutting_pickup_v1(jsonb,uuid,bigint)','EXECUTE')or has_table_privilege('cp7_transaction_source_read','erp.cutting_groups','INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER')").fetchone()[0]
  return dict(status='PASS',current_distribution_view_before_metadata_not_implied_by_cutting_view=True,same_subject_after_revoke_denied_including_unknown_group=True,missing_and_unposted_group_not_guessed=True,no_Native_writer_or_ERP_DML_grant=True)
 return [('CP7_SOURCE_CUTTING_POSTED_EXACT',exact),('CP7_SOURCE_CUTTING_NATIVE_PAGE100',page),('CP7_SOURCE_CUTTING_CURRENT_AUTHORITY',authority)]

def http_cases(http,today):
 def exact():
  owner=http.login('OWNER','cp7-source-cutting-owner')
  with http.connect()as conn,conn.cursor()as cur:f=advanced(cur,today);conn.commit();before=b.boundary.snapshot(cur);conn.rollback()
  args=dict(p_source=dict(source_type='CUTTING_GROUP',source_id=f['group']))
  assert http.anon_rpc('erp_cp7_resolve_transaction_source_v1',args)['status']in(401,403)
  r=owner.rpc('erp_cp7_resolve_transaction_source_v1',args);assert r['status']==200,r
  d=r['body']['document'];assert r['body']['actor_scope_id']==owner.auth_user_id and d['id']==f['group']and d['focus']['parent_id']==f['po']and r['body']['business_DML']is False
  w=owner.rpc('erp_get_cutting_pickup_queue_v1',dict(p_filter='ALL',p_pattern_id=None,p_query=None,p_limit=100,p_offset=d['focus']['page_offset']));assert w['status']==200
  row=next(x for x in w['body']['rows']if x['cutting_group_id']==d['id']);assert row['po_id']==f['po']and str(row['row_version'])==d['revision']
  with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==before;conn.rollback()
  return dict(status='PASS',actual_Auth_HTTP_group_to_Native_ALL_page_exact_PO_version=True,anonymous_denied_full_business_boundary_unchanged=True)
 def revoke():
  admin=http.login('ADMIN','cp7-source-cutting-current-admin')
  with http.connect()as conn,conn.cursor()as cur:
   f=posted(cur,today);role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(admin.auth_user_id,)).fetchone()[0]
   cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'production.distribution.view')on conflict do nothing",(role,));conn.commit()
  args=dict(p_source=dict(source_type='CUTTING_MATERIAL_ISSUE',source_id=f['group']))
  r=admin.rpc('erp_cp7_resolve_transaction_source_v1',args);assert r['status']==200
  with http.connect()as conn,conn.cursor()as cur:
   cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.distribution.view'",(role,));conn.commit();before=b.boundary.snapshot(cur);conn.rollback()
  assert admin.rpc('erp_cp7_resolve_transaction_source_v1',args)['status']==403
  assert admin.rpc('erp_get_cutting_pickup_queue_v1',dict(p_filter='ALL',p_pattern_id=None,p_query=None,p_limit=100,p_offset=0))['status']==403
  with http.connect()as conn,conn.cursor()as cur:assert b.boundary.snapshot(cur)==before;conn.rollback()
  return dict(status='PASS',same_Auth_token_after_current_distribution_view_revoke_both_metadata_and_Native_reader_denied=True,no_business_write=True)
 return [('CP7_SOURCE_CUTTING_HTTP_EXACT',exact),('CP7_SOURCE_CUTTING_HTTP_CURRENT_REVOKE',revoke)]
