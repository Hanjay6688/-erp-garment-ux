"""Predeclared P08 linked Native lifecycle; no seeded movements or client facts."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json,time,uuid
import psycopg
import cp7_plan_native_cases as plan
b,auth=plan.b,plan.auth

def read(cur,d,subject=None):return plan.rpc(cur,'erp_cp7_read_plan_actual_v1',(d,),subject)
def prepared(cur,today,subject=None):
 f=plan.setup(cur,today,subject,new_plan_po=True);d=plan.save(cur,f['payload'],subject=subject)
 out=plan.apply(cur,plan.action(d),subject=subject);f.update(draft=d,group=out['native']['cutting_group_id']);return f
def post(cur,f):
 p=f['payload']['cutting'];v=b.chain.base.group_version(cur,f['group'])
 return b.chain.production.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(p,id=f['group'],action='POST',change_reason='P08 actual physical cut two'),expected_version=int(v))
def complete_one(cur,f,product=None):
 prod,base=b.chain.production,b.chain.base;po=f['payload']['cutting']['po_id'];group=f['group']
 now=cur.execute('select clock_timestamp()').fetchone()[0]
 when=lambda minute:(now-timedelta(minutes=minute)).isoformat()
 b.api.admin(cur)
 yield_id=cur.execute('select y.id from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id where r.cutting_group_id=%s',(group,)).fetchone()[0]
 # Native POST requires every source yield to be distributed exactly once.
 # Pick up both pieces into separate batches; finish only batch one. The
 # second piece remains conserved pre-laundry WIP, not a fabricated partial
 # pickup or an invented precise sewing substage.
 payload=dict(action='SAVE_DRAFT',cutting_group_id=group,contractor_id=prod.CONTRACTOR,picked_up_at=when(50),allocation_mode='ROLL',expected_group_version=int(base.group_version(cur,group)),change_reason='P08 actual pickup two; finish one',batches=[dict(batch_no=i,allocations=[dict(cutting_roll_yield_id=str(yield_id),qty_pcs=1)])for i in(1,2)])
 pickup=prod.rpc(cur,'public.erp_save_cutting_pickup_v1',payload)
 prod.rpc(cur,'public.erp_save_cutting_pickup_v1',dict(payload,id=pickup['pickup_id'],action='POST'),expected_version=int(pickup['row_version']))
 b.api.admin(cur);batch=cur.execute('select id from erp.cutting_distribution_batches where pickup_id=%s and batch_no=1',(pickup['pickup_id'],)).fetchone()[0]
 snapshot,completion=uuid.uuid4(),uuid.uuid4()
 cur.execute('insert into erp.po_work_component_snapshots(id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at)values(%s,%s,%s,1,0,%s)',(snapshot,po,prod.COMPONENT,when(45)))
 b.chain.peer.ordinary(cur)
 cur.execute("insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by)values(%s,%s,%s,%s,%s,%s,'DRAFT','P08 actual one-piece sewing draft',%s)",(completion,'P08-WC-'+str(completion),po,prod.CONTRACTOR,group,when(40),base.OPERATOR_APP))
 cur.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot)values(%s,%s,%s,1,1,0)',(completion,snapshot,prod.COMPONENT))
 cur.execute('select erp.post_work_completion(%s)',(completion,));prod.owner(cur)
 cur.execute('select public.erp_record_sewing_terminal_v1(%s::jsonb,%s)',(json.dumps(dict(work_completion_id=str(completion),qty_pcs=1,reason='P08 actual one-piece terminal')),uuid.uuid4()));b.api.admin(cur)
 service=f['fixture'];size=f['options']['size_id']
 delivery=dict(distribution_batch_id=str(batch),vendor_id=service['vendor'],wash_process_id=service['process'],target_dyeing_color='P08-PLAN',physical_at=when(30),reason='P08 actual one-piece laundry',lines=[dict(size_id=size,qty_sent_pcs=1)])
 sent=b.bd(cur,'POST_PRICED_DELIVERY',dict(delivery=delivery,expected_version=str(base.group_version(cur,group)),pricing=dict(deferred=True)))
 delivery_id=sent['delivery_id'];b.api.admin(cur);delivery_size=base.delivery_size_line(cur,delivery_id)
 receipt=b.chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=delivery_id,wash_process_id=service['process'],physical_at=when(20),reason='P08 actual one-piece return',lines=[dict(delivery_batch_size_line_id=delivery_size,qty_good_received=1,qty_bs_laundry=0,bs_product_id=None)]),base.delivery_version(cur,delivery_id))
 b.api.admin(cur);line=b.receipt_line(cur,receipt['receipt_id']);receipt_size=cur.execute('select id from erp.laundry_receipt_batch_size_lines where receipt_line_id=%s',(line,)).fetchone()[0]
 return b.chain.laundry_action(cur,'POST_FINAL_SKU',dict(cutting_group_id=group,destination_location_id=base.LOCATION,physical_at=when(10),reason='P08 actual partial QC one',good_qty_pcs=1,completion_mode='PARTIAL_SELECTION',lines=[dict(final_product_id=product or f['root'],qty_good_pcs=1,qty_bs_pcs=0,source_laundry_receipt_line_id=line,source_laundry_receipt_batch_size_line_id=str(receipt_size))]),base.group_version(cur,group))
def vector(result):
 a=result['actual'];assert a['state']=='COMPLETE',a
 return [int(a['facts'][k]['value'])for k in('input_pcs','wip_pcs','group_fg_pcs','bs_pcs','withheld_pcs','exited_pcs','matched_fg_pcs','other_root_fg_pcs')]

def cases(cur,today):
 def unposted():
  f=plan.setup(cur,today,new_plan_po=True);d=plan.save(cur,f['payload']);before=b.boundary.snapshot(cur)
  no_intent=read(cur,d['draft_id']);assert no_intent['actual']['state']=='NOT_STARTED'and no_intent['planned_pcs']=='2'and all(x['value']=='0'for x in no_intent['actual']['facts'].values());assert b.boundary.snapshot(cur)==before
  out=plan.apply(cur,plan.action(d));before=b.boundary.snapshot(cur);result=read(cur,d['draft_id']);assert result['actual']['state']=='NOT_STARTED'and result['actual']['native_group']['id']==out['native']['cutting_group_id'];assert result['actual']['facts']['input_pcs']['value']=='0'and result['remaining_to_plan_pcs']['value']=='2'and b.boundary.snapshot(cur)==before
  return dict(status='PASS',saved_estimate_and_unposted_Native_are_not_physical_input=True,old_group_FG15_not_counted=True,all_reads_leave_full_Native_boundary_unchanged=True)
 def physical_cut():
  f=prepared(cur,today);old=plan.read(cur,f['draft']['draft_id']);post(cur,f);before=b.boundary.snapshot(cur);r=read(cur,f['draft']['draft_id']);assert vector(r)==[2,2,0,0,0,0,0,0]and r['remaining_to_plan_pcs']['value']=='2';assert r['actual']['original_source_state']=='ARCHIVED_STALE'and plan.read(cur,f['draft']['draft_id'])['payload']==old['payload']and b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_Native_cut_two_conserved_same_exact_size=True,immutable_plan_separate_from_current_physical_result=True,no_business_read_mutation=True)
 def lifecycle(other_root=False):
  f=prepared(cur,today);post(cur,f);product=None
  if other_root:product=b.sized_product(cur,f['options']['size_id'],'P08-OTHER-'+uuid.uuid4().hex[:8])
  complete_one(cur,f,product);before=b.boundary.snapshot(cur);r=read(cur,f['draft']['draft_id']);assert vector(r)==[2,1,1,0,0,0,0 if other_root else 1,1 if other_root else 0],r
  assert r['remaining_to_plan_pcs']['value']==('2'if other_root else'1')and b.boundary.snapshot(cur)==before
  assert any(x['stage']=='SEWING_UNRESOLVED'and x['remaining_pcs']=='1'for x in r['actual']['positions'])
  return dict(status='PASS',Native_pickup_exactly_reconciles_both_source_pieces=True,actual_partial_sewing_laundry_receipt_QC_one=True,original_two_equals_WIP_one_plus_FG_one=True,other_physical_root_excluded_from_plan=other_root,group_sewing_substage_not_invented=True,all_money_stock_HPP_and_Native_state_unchanged_by_read=True)
 def deleted():
  f=prepared(cur,today);p=dict(f['payload']['cutting'],id=f['group'],action='DELETE',change_reason='P08 Native unposted removal')
  b.chain.production.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',p,expected_version=int(b.chain.base.group_version(cur,f['group'])))
  before=b.boundary.snapshot(cur);r=read(cur,f['draft']['draft_id']);assert r['actual']['state']=='UNKNOWN'and r['actual']['reason']=='LINKED_NATIVE_GROUP_MISSING'and all(x['state']=='UNKNOWN'and'value'not in x for x in r['actual']['facts'].values())and r['remaining_to_plan_pcs']['state']=='UNKNOWN'and b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_Native_deleted_link_remains_UNKNOWN_not_zero=True,immutable_intent_not_recreated=True)
 def access():
  subject,role=plan.custom(cur);f=prepared(cur,today,subject);other,_=plan.custom(cur)
  auth.refused(cur,lambda:read(cur,f['draft']['draft_id'],other),'CP7_PLAN_DRAFT_UNAVAILABLE')
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.cutting.view'",(role,))
  auth.refused(cur,lambda:read(cur,f['draft']['draft_id'],subject),'CP7_PLAN_ACCESS_DENIED')
  assert not cur.execute("select has_function_privilege('authenticated','cp7_plan_native.actual_source(uuid,uuid,text)','EXECUTE')or has_function_privilege('cp7_capture','public.erp_cp7_read_plan_actual_v1(uuid)','EXECUTE')").fetchone()[0]
  return dict(status='PASS',current_cutting_view_own_Original_and_private_helper_authority=True,no_capture_to_Native_mutator_grant=True)
 def protected():
  from cp7_analysis_finance_cases import admin_actor
  subject,role=admin_actor(cur,plan.analysis)
  for permission in('production.cutting.view','production.cutting.create','production.cutting.edit_draft'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,permission))
  f=prepared(cur,today,subject);assert f['original']['financial_source']is not None;read(cur,f['draft']['draft_id'],subject)
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.reports.view'",(role,))
  auth.refused(cur,lambda:read(cur,f['draft']['draft_id'],subject),'CP7_ANALYSIS_FINANCE_ACCESS_DENIED')
  return dict(status='PASS',operational_comparison_cannot_launder_protected_Original_after_finance_authority_loss=True)
 def outside_clock():
  f=prepared(cur,today);post(cur,f)
  b.api.admin(cur)
  cur.execute('set local session_replication_role=replica')
  try:cur.execute("update erp.cutting_groups set cut_at=clock_timestamp()+interval '1 day'where id=%s",(f['group'],))
  finally:cur.execute('set local session_replication_role=origin')
  r=read(cur,f['draft']['draft_id']);assert r['actual']['state']=='UNKNOWN'and r['actual']['reason']=='LINKED_NATIVE_CUT_OUTSIDE_CAPTURE_CLOCK'and all(x['state']=='UNKNOWN'and'value'not in x for x in r['actual']['facts'].values())
  return dict(status='PASS',explicit_administrative_future_corruption_counterfixture_not_Native_event=True,no_future_physical_input_or_zero_fallback=True)
 return [('P08_ACTUAL_'+name,fn)for name,fn in [('UNPOSTED_ZERO',unposted),('PHYSICAL_CUT',physical_cut),('PARTIAL_LIFECYCLE',lifecycle),('OTHER_ROOT',lambda:lifecycle(True)),('NATIVE_DELETED_UNKNOWN',deleted),('CURRENT_PRIVATE_AUTH',access),('PROTECTED_ORIGINAL_AUTH',protected),('FUTURE_CORRUPTION_UNKNOWN',outside_clock)]]

def races(tools,today):
 def snapshot(revoke=False):
  with tools.connect()as conn,conn.cursor()as cur:
   subject,role=plan.custom(cur);f=prepared(cur,today,subject);original=cur.execute("select pg_get_functiondef('cp7_wip.capture_cutting_sources(uuid[],timestamp with time zone)'::regprocedure)").fetchone()[0]
   needle='with clock as materialized(select p_at at),';assert needle in original
   gate="with clock as materialized(select p_at at from(select case when p_groups=array['"+str(f['group'])+"'::uuid]then pg_advisory_xact_lock(8072026)end)controlled_gate),"
   cur.execute(original.replace(needle,gate),prepare=False);conn.commit()
  try:
   with tools.connect()as holder,holder.cursor()as h:
    h.execute('select pg_advisory_xact_lock(8072026)')
    def send():
     with tools.connect()as conn,conn.cursor()as c:
      try:r=read(c,f['draft']['draft_id'],subject);conn.commit();return r
      except psycopg.Error as e:conn.rollback();return dict(error=str(e),sqlstate=e.sqlstate)
    with ThreadPoolExecutor(max_workers=1)as pool:
     job=pool.submit(send);waiting=False;deadline=time.monotonic()+12
     try:
      with tools.connect(autocommit=True)as inspect,inspect.cursor()as c:
       while time.monotonic()<deadline:
        waiting=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_read_plan_actual_v1%%')").fetchone()[0]
        if waiting:break
        time.sleep(.03)
       assert waiting,'P08_ACTUAL_PUBLIC_READ_CAPTURE_WAIT_NOT_OBSERVED'
      with tools.connect()as conn,conn.cursor()as c:
       if revoke:c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.cutting.view'",(role,))
       else:post(c,f)
       conn.commit()
     finally:holder.rollback()
     result=job.result(45)
   if revoke:assert result.get('sqlstate')=='42501'and result.get('error','').splitlines()[0]=='CP7_PLAN_ACCESS_CHANGED',result
   else:
    assert result['actual']['state']=='NOT_STARTED'and result['actual']['native_group']['material_issue_posted']is False and result['actual']['facts']['input_pcs']['value']=='0',result
    with tools.connect()as conn,conn.cursor()as c:assert vector(read(c,f['draft']['draft_id'],subject))==[2,2,0,0,0,0,0,0]
   return dict(status='PASS',actual_two_connections_capture_wait_observed=True,current_authority_after_capture_wait=revoke,Native_post_commits_during_snapshot_read=not revoke,coherent_header_and_graph_from_one_MVCC_statement=not revoke,controlled_CP7_reader_only_no_Native_writer_patch=True)
  finally:
   with tools.connect()as conn,conn.cursor()as c:c.execute(original,prepare=False);conn.commit();assert c.execute("select pg_get_functiondef('cp7_wip.capture_cutting_sources(uuid[],timestamp with time zone)'::regprocedure)").fetchone()[0]==original
 return [('P08_ACTUAL_MVCC_NATIVE_POST',snapshot),('P08_ACTUAL_CAPTURE_WAIT_CURRENT_AUTH',lambda:snapshot(True))]

def http_cases(http,today):
 def actual():
  owner=http.login('OWNER','p08-actual-owner');foreign=http.login('OWNER','p08-actual-foreign')
  with http.connect()as conn,conn.cursor()as c:f=prepared(c,today,owner.auth_user_id);conn.commit()
  args=dict(p_draft=f['draft']['draft_id']);r=owner.rpc('erp_cp7_read_plan_actual_v1',args);assert r['status']==200 and r['body']['actual']['state']=='NOT_STARTED',r
  assert foreign.rpc('erp_cp7_read_plan_actual_v1',args)['status']==403 and http.anon_rpc('erp_cp7_read_plan_actual_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as c:post(c,f);conn.commit()
  r=owner.rpc('erp_cp7_read_plan_actual_v1',args);assert r['status']==200 and vector(r['body'])==[2,2,0,0,0,0,0,0],r
  with http.connect()as conn,conn.cursor()as c:c.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_read_plan_actual_v1',args)['status']==403
  return dict(status='PASS',actual_Auth_HTTP_own_read_unposted_and_Native_POST=True,foreign_anonymous_current_deactivation403=True)
 return [('P08_ACTUAL_REAL_AUTH_HTTP',actual)]
