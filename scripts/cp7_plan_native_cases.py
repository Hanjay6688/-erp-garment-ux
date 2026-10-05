"""Native draft/intent oracles. No speculative cut is posted or reserved."""
import copy,json,uuid,threading,time
from datetime import timedelta
from decimal import Decimal as D
from concurrent.futures import ThreadPoolExecutor
import psycopg
import cp7_analysis_cases as analysis
import cp7_procurement_cases as receipt
previous=analysis.previous;schedule=previous.schedule;auth=previous.auth;b=previous.b

def rpc(cur,name,args,subject=None):return schedule.rpc(cur,name,args,subject)
def save(cur,p,key=None,subject=None):return rpc(cur,'erp_cp7_save_plan_draft_v1',(json.dumps(p),key or uuid.uuid4()),subject)
def preview(cur,d,subject=None):return rpc(cur,'erp_cp7_preview_plan_action_v1',(d,),subject)
def read(cur,d,subject=None):return rpc(cur,'erp_cp7_read_plan_draft_v1',(d,),subject)
def apply(cur,p,key=None,subject=None):return rpc(cur,'erp_cp7_apply_plan_action_v1',(json.dumps(p),key or uuid.uuid4()),subject)
def options(cur,q,subject=None):return rpc(cur,'erp_cp7_get_plan_options_v1',(json.dumps(q),),subject)
def action(d,**changes):return dict(draft_id=d['draft_id'],expected_revision=d['revision'],explicit_review=True,reason='Explicit operator review: create unposted Native cutting draft only',**changes)
def monetary_state(cur):
 values={};zone=cur.execute("select current_setting('TimeZone')").fetchone()[0]
 cur.execute("select set_config('TimeZone','UTC',true)")
 try:
  for table in('material_stock_movements','fg_stock_movements','journal_entries','journal_lines','materials'):
   values[table]=cur.execute('select md5(coalesce(jsonb_agg(to_jsonb(x)order by id),\'[]\'::jsonb)::text)from erp.'+table+' x').fetchone()[0]
  return values
 finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))
def source_diagnostic(cur,run):
 stored=cur.execute('select actor,query,facts,dependency_hash from cp7_analysis_native.runs where id=%s',(run,)).fetchone()
 assert stored is not None
 analysis.read(cur,run,str(stored[0]))
 cur.execute('set local role cp7_capture')
 current=cur.execute('select cp7_analysis_native.source(%s::jsonb)',(json.dumps(stored[1]),)).fetchone()[0]
 current_hash=cur.execute('select cp7_analysis_native.fingerprint(%s::jsonb)',(json.dumps(current),)).fetchone()[0]
 b.api.admin(cur)
 return dict(stored_hash=stored[3],current_hash=current_hash,stored=stored[2],current=current)
def custom(cur):
 subject,role=auth.custom_actor(cur)
 for permission in('production.cutting.view','production.cutting.create','production.cutting.edit_draft'):
  cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',(role,permission))
 return subject,role

def setup(cur,today,subject=None,new_plan_po=False):
 f=previous.production.cut.fixture(cur,today)
 # A clean accepted database need not contain unused fabric. Create its source
 # through the real receipt SAVE/POST before freezing the analysis dependencies;
 # never inject movements or assume that the production fixture left fabric.
 fabric=receipt.fixture(cur,today,qty='10',price='10')
 source_receipt=receipt.post(cur,receipt.command(cur,'SAVE_DRAFT',fabric['payload']))
 if new_plan_po:
  # Master only, before freezing dependencies. A new two-piece plan must not
  # reuse the predecessor PO whose hundred pieces have already been sewn.
  po=str(uuid.uuid4());start=cur.execute('select clock_timestamp()').fetchone()[0]-timedelta(hours=2)
  cur.execute("insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)values(%s,%s,%s,2,'CUTTING','CUTTING',%s,'P08 explicit plan actual master fixture')",(po,'0000-P08-ACTUAL-'+po,f['model'],start))
 root=str(f['product']);previous.select_profiles(cur,root,True)
 supply=previous.supply.capture(cur,today);p=schedule.payload(cur,supply,str(cur.execute('select coalesce(max(revision),0)from cp7_schedule_native.plans').fetchone()[0]))
 load=sum(int(step['remaining_minutes'])for pos in p['config']['positions']for step in pos['remaining_steps'])
 start=cur.execute('select clock_timestamp()').fetchone()[0].replace(microsecond=0)+timedelta(hours=1)
 p['config']['windows']=[dict(key='p08-whole-retained-queue',starts_at=schedule.stamp(start),ends_at=schedule.stamp(start+timedelta(minutes=load+120)),other_load_minutes='0')]
 p['config']['through_at']=schedule.stamp(start+timedelta(minutes=load+180));schedule.save(cur,p)
 original=analysis.capture(cur,today,subject=subject);target=analysis.recommendation(original['analysis'],root)['target']['key']
 loc=fabric['location']
 q=dict(run_id=original['run_id'],target_key=target,location_id=loc,po_query='',roll_query='',po_offset='0',roll_offset='0',pattern_offset='0',limit='50');o=options(cur,q,subject)
 assert o['orders']and o['patterns']and o['rolls']and D(o['needed_pcs'])>=2 and D(o['capacity_pcs'])>=2,o
 # Pin the exact newly posted ten-unit receipt at its unique location. Never
 # borrow another roll or turn a seed balance into this scenario's source.
 matching_rolls=[x for x in o['rolls']if x['material_id']==fabric['material']]
 assert len(matching_rolls)==1 and D(matching_rolls[0]['available'])==10,matching_rolls
 roll=matching_rolls[0]
 payload=dict(run_id=original['run_id'],target_key=target,plan_id=None,expected_revision=None,source_hash=o['source_hash'],
  reason='P08 explicit selected exact-size draft composition; no installed-material or reservation claim',reviewed_assumption_ids=[x['id']for x in o['assumptions']],
  cutting=dict(po_id=o['orders'][0]['id'],pattern_id=o['patterns'][0]['id'],source_location_id=loc,cut_at=cur.execute('select clock_timestamp()').fetchone()[0].isoformat(),notes='P08 unposted reviewed planning intent',
   size_slots=[dict(slot_no='1',size_id=o['size_id'],drawing_no='1')],rolls=[dict(roll_id=roll['id'],qty_issued='1',qty_consumed='0.5',qty_reported_remaining='0.5',yields=[dict(slot_no='1',qty_pcs='2')])]))
 if new_plan_po:
  payload['cutting']['po_id']=po;payload['cutting']['cut_at']=(cur.execute('select clock_timestamp()').fetchone()[0]-timedelta(hours=1)).isoformat()
 return dict(fixture=f,root=root,original=original,query=q,options=o,payload=payload,source_receipt=source_receipt)

def current_payload(cur,today,f,issued='6',subject=None):
 original=analysis.capture(cur,today,subject=subject)
 payload=copy.deepcopy(f['payload']);payload.update(run_id=original['run_id'],source_hash=original['analysis']['snapshot']['source_hash'])
 roll=payload['cutting']['rolls'][0]
 roll.update(qty_issued=issued,qty_consumed=str(D(issued)/2),qty_reported_remaining=str(D(issued)/2))
 return payload

def shared_material_setup(cur,today):
 first=setup(cur,today,new_plan_po=True);second=setup(cur,today,new_plan_po=True)
 second['payload']['cutting']['source_location_id']=first['payload']['cutting']['source_location_id']
 second['payload']['cutting']['rolls'][0]['roll_id']=first['payload']['cutting']['rolls'][0]['roll_id']
 assert first['payload']['target_key']!=second['payload']['target_key']
 return first,second

def material_pool(cur,payload):
 b.api.admin(cur)
 return cur.execute('select cp7_plan_native.material_pool(%s,%s)',(payload['cutting']['rolls'][0]['roll_id'],payload['cutting']['source_location_id'])).fetchone()[0]

def material_cases(cur,today):
 def next_target():
  first,second=shared_material_setup(cur,today);one=current_payload(cur,today,first);d=save(cur,one);before=monetary_state(cur)
  out=apply(cur,action(d));pool=material_pool(cur,one)
  assert [D(pool[k])for k in('native_available','linked_native_draft_qty','free_for_new_plan')]==[D(10),D(6),D(4)],pool
  assert pool['linked_native_drafts'][0]['group_id']==out['native']['cutting_group_id']
  p=current_payload(cur,today,second);auth.refused(cur,lambda:save(cur,p),'CP7_PLAN_SHARED_MATERIAL_BUDGET_CHANGED')
  p=current_payload(cur,today,second,'4');d2=save(cur,p);apply(cur,action(d2));pool=material_pool(cur,p)
  assert [D(pool[k])for k in('native_available','linked_native_draft_qty','free_for_new_plan')]==[D(10),D(10),D(0)],pool
  assert monetary_state(cur)==before and cur.execute('select count(*)from cp7_plan_native.intents').fetchone()[0]==2
  return dict(status='PASS',two_actual_distinct_targets_one_Native_roll10=True,first_linked_draft6_then_second6_refused_and_second4_committed=True,physical_stock_money_HPP_unchanged=True,final_complete_pool=pool)
 def posted_once():
  from cp7_plan_actual_cases import post
  f=setup(cur,today,new_plan_po=True);p=current_payload(cur,today,f);p['cutting']['rolls'][0].update(qty_consumed='6',qty_reported_remaining='0')
  d=save(cur,p);out=apply(cur,action(d));f.update(payload=p,group=out['native']['cutting_group_id']);post(cur,f)
  pool=material_pool(cur,p)
  assert [D(pool[k])for k in('native_available','linked_native_draft_qty','free_for_new_plan')]==[D(4),D(0),D(4)],pool
  assert pool['linked_native_drafts']==[]
  return dict(status='PASS',actual_unchanged_Native_POST_issue6_stock10_to4=True,posted_intent_not_second_physical_deduction=True,final_complete_pool=pool)
 def edited_current():
  f=setup(cur,today,new_plan_po=True);p=current_payload(cur,today,f);d=save(cur,p);before=monetary_state(cur);out=apply(cur,action(d));gid=out['native']['cutting_group_id']
  changed=copy.deepcopy(p['cutting']);changed['rolls'][0].update(qty_issued='3',qty_consumed='1.5',qty_reported_remaining='1.5')
  b.chain.production.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(changed,id=gid,action='SAVE_DRAFT',change_reason='P08 actual Native draft composition correction six to three'),expected_version=int(b.chain.base.group_version(cur,gid)))
  pool=material_pool(cur,p)
  assert [D(pool[k])for k in('native_available','linked_native_draft_qty','free_for_new_plan')]==[D(10),D(3),D(7)],pool
  assert cur.execute('select payload from cp7_plan_native.drafts where id=%s',(d['draft_id'],)).fetchone()[0]['cutting']['rolls'][0]['qty_issued']=='6'
  assert monetary_state(cur)==before
  return dict(status='PASS',actual_unchanged_Native_SAVE_DRAFT_edit6_to3=True,current_Native_composition_not_old_immutable_estimate=True,physical_stock_money_HPP_unchanged=True,final_complete_pool=pool)
 return [('P08_SHARED_FABRIC_NEXT_TARGET',next_target),('P08_SHARED_FABRIC_POSTED_ONCE',posted_once),('P08_SHARED_FABRIC_NATIVE_DRAFT_EDIT',edited_current)]

def cases(cur,today):
 def metadata():
  f=setup(cur,today);before=b.boundary.snapshot(cur);d=save(cur,f['payload']);assert b.boundary.snapshot(cur)==before
  one=read(cur,d['draft_id']);assert one['payload']==f['payload']and one['state']=='SAVED'and one['native_intent']is None
  assert not one['reservation_created']and not one['production_go']
  return dict(status='PASS',own_immutable_planning_draft_only_no_operational_or_counter_effect=True)
 def replay_save():
  f=setup(cur,today);key=uuid.uuid4();one=save(cur,f['payload'],key);assert save(cur,f['payload'],key)==one
  bad={**f['payload'],'reason':'different'};auth.refused(cur,lambda:save(cur,bad,key),'CP7_PLAN_REQUEST_CHANGED')
  assert cur.execute('select count(*)from cp7_plan_native.drafts').fetchone()[0]==1
  return dict(status='PASS',saved_draft_UUID_same_original_payload_hash_refusal=True)
 def revision():
  f=setup(cur,today);one=save(cur,f['payload']);p={**f['payload'],'plan_id':one['plan_id'],'expected_revision':one['revision'],'reason':'Reviewed version two'};two=save(cur,p)
  assert two['revision']=='2'and read(cur,one['draft_id'])['is_latest']is False
  auth.refused(cur,lambda:preview(cur,one['draft_id']),'CP7_PLAN_REVISION_CHANGED');auth.refused(cur,lambda:save(cur,p),'CP7_PLAN_REVISION_CHANGED')
  assert preview(cur,two['draft_id'])['revision']=='2'
  return dict(status='PASS',immutable_draft_revisions_and_stale_version_atomic_refusal=True)
 def readonly_preview():
  f=setup(cur,today);d=save(cur,f['payload']);before=b.boundary.snapshot(cur);r=preview(cur,d['draft_id'])
  assert b.boundary.snapshot(cur)==before and D(r['selected_new_pcs'])==2 and D(r['needed_pcs'])==D(f['options']['needed_pcs'])and D(r['unresolved_pcs'])==D(r['needed_pcs'])-2
  assert r['material_rows'][0]['basis']=='OPERATOR_SELECTED_DRAFT_COMPOSITION_NOT_PROVEN_INSTALLED_OR_RESERVED'and'qty_reserved'not in json.dumps(r)and'native_payload'not in r
  return dict(status='PASS',Native_needed_selected_feasible_and_unresolved_kept_distinct=True,preview_no_reservation_post_or_counter_change=True)
 def native_apply():
  f=setup(cur,today);d=save(cur,f['payload']);before=monetary_state(cur);n=cur.execute('select count(*)from erp.cutting_groups').fetchone()[0];out=apply(cur,action(d));native=out['native']
  assert out['state']=='NATIVE_DRAFT_CREATED'and native['material_issue_posted']is False and monetary_state(cur)==before
  assert cur.execute('select count(*)from erp.cutting_groups').fetchone()[0]==n+1
  assert D(str(native['total_pieces']))==2 and D(str(native['total_qty_issued']))==1 and D(str(native['total_qty_consumed']))==D('0.5')
  assert read(cur,d['draft_id'])['native_intent']['cutting_group_id']==native['cutting_group_id']and not out['physical_production_confirmed']
  return dict(status='PASS',unchanged_Native_SAVE_DRAFT_exact_size2_issued1_selected_consumption_half=True,single_atomic_linked_intent_no_stock_money_HPP_or_physical_confirmation=True)
 def apply_replay():
  f=setup(cur,today);d=save(cur,f['payload']);key=uuid.uuid4();p=action(d);one=apply(cur,p,key);assert apply(cur,p,key)==one
  auth.refused(cur,lambda:apply(cur,{**p,'reason':'changed'},key),'CP7_PLAN_REQUEST_CHANGED');auth.refused(cur,lambda:apply(cur,p),'CP7_PLAN_ALREADY_APPLIED')
  assert cur.execute('select count(*)from cp7_plan_native.intents').fetchone()[0]==1 and cur.execute('select count(*)from cp7_plan_native.commands').fetchone()[0]==1
  return dict(status='PASS',same_UUID_original_outcome_one_Native_domain_draft_and_intent=True,changed_or_fresh_UUID_no_duplicate=True)
 def stale():
  f=setup(cur,today);d=save(cur,f['payload']);preview(cur,d['draft_id']);previous.baseline.save(cur,previous.baseline.payload(cur,dict(product=f['root']),revision='1',daily_pcs='11'))
  before=b.boundary.snapshot(cur);auth.refused(cur,lambda:apply(cur,action(d)),'CP7_PLAN_SOURCE_CHANGED');assert b.boundary.snapshot(cur)==before and not cur.execute('select exists(select 1 from cp7_plan_native.intents)').fetchone()[0]
  return dict(status='PASS',actual_profile_revision_after_preview_requires_new_Original_no_domain_effect=True)
 def current():
  subject,role=custom(cur);f=setup(cur,today,subject);d=save(cur,f['payload'],subject=subject);key=uuid.uuid4();p=action(d);one=apply(cur,p,key,subject)
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.cutting.create'",(role,));before=b.boundary.snapshot(cur)
  auth.refused(cur,lambda:apply(cur,p,key,subject),'CP7_PLAN_ACCESS_DENIED');assert b.boundary.snapshot(cur)==before
  assert one['actor_scope_id']==subject
  return dict(status='PASS',current_permission_before_cached_commit_lookup=True)
 def foreign():
  f=setup(cur,today);d=save(cur,f['payload']);other,_=custom(cur)
  auth.refused(cur,lambda:read(cur,d['draft_id'],other),'CP7_PLAN_DRAFT_UNAVAILABLE');auth.refused(cur,lambda:apply(cur,action(d),subject=other),'CP7_PLAN_DRAFT_UNAVAILABLE')
  auth.refused(cur,lambda:options(cur,f['query'],other),'CP7_PLAN_ORIGINAL_UNAVAILABLE')
  return dict(status='PASS',foreign_Original_draft_and_application_denied=True)
 def strict():
  f=setup(cur,today);before=b.boundary.snapshot(cur)
  try:
   for extra in('quantity_override','complete_scope','reservation','production_confirmed'):
    auth.refused(cur,lambda extra=extra:save(cur,{**f['payload'],extra:True}),'CP7_PLAN_FIELDS')
   bad=copy.deepcopy(f['payload']);bad['cutting']['action']='POST';auth.refused(cur,lambda:save(cur,bad),'CP7_PLAN_FIELDS')
   bad=copy.deepcopy(f['payload']);bad['reviewed_assumption_ids']=[];auth.refused(cur,lambda:save(cur,bad),'CP7_PLAN_ASSUMPTIONS_NOT_REVIEWED')
   bad=copy.deepcopy(f['payload']);bad['cutting']['rolls'][0]['qty_reported_remaining']='0';auth.refused(cur,lambda:save(cur,bad),'CP7_PLAN_NATIVE_MATERIAL_RECONCILIATION')
   for _ in range(40):
    observed=analysis.read(cur,f['original']['run_id'])
    assert observed['source_state']=='UNCHANGED',('READ_ONLY_SOURCE_CHANGED',observed['source_state'])
  except Exception:
   from pathlib import Path
   path=Path('cp6-proof/t3/P08_CLOSED_SOURCE_DIAGNOSTIC.json');path.parent.mkdir(parents=True,exist_ok=True)
   path.write_text(json.dumps(source_diagnostic(cur,f['original']['run_id']),indent=2,default=str)+'\n');raise
  assert b.boundary.snapshot(cur)==before and not cur.execute('select exists(select 1 from cp7_plan_native.drafts)').fetchone()[0]
  return dict(status='PASS',closed_operator_review_exact_units_and_no_public_POST_override=True,read_only_Original_stability_reads=40)
 def identities():
  f=setup(cur,today);before=b.boundary.snapshot(cur)
  bad=copy.deepcopy(f['payload']);bad['cutting']['size_slots'][0]['size_id']=str(uuid.uuid4());auth.refused(cur,lambda:save(cur,bad),'CP7_PLAN_NATIVE_EXACT_SIZE')
  bad=copy.deepcopy(f['payload']);bad['cutting']['po_id']=str(uuid.uuid4());auth.refused(cur,lambda:save(cur,bad),'CP7_PLAN_NATIVE_PO_MODEL')
  bad=copy.deepcopy(f['payload']);bad['cutting']['rolls'][0]['roll_id']=str(uuid.uuid4());auth.refused(cur,lambda:save(cur,bad),'CP7_PLAN_NATIVE_ROLL')
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',Native_PO_model_exact_size_location_roll_identity_not_labels=True)
 def quantity():
  f=setup(cur,today);bad=copy.deepcopy(f['payload']);bad['cutting']['rolls'][0]['yields'][0]['qty_pcs']=str(max(D(f['options']['needed_pcs']),D(f['options']['capacity_pcs']))+1)
  auth.refused(cur,lambda:save(cur,bad),'CP7_PLAN_QUANTITY_EXCEEDS_NEED_OR_CAPACITY')
  bad=copy.deepcopy(f['payload']);bad['cutting']['rolls'][0]['qty_issued']='999999999999';bad['cutting']['rolls'][0]['qty_consumed']='999999999999';bad['cutting']['rolls'][0]['qty_reported_remaining']='0'
  auth.refused(cur,lambda:save(cur,bad),'CP7_PLAN_NATIVE_MATERIAL_NOT_READY')
  return dict(status='PASS',real_Native_balance_needed_capacity_and_unknown_not_bypassable=True)
 def atomic_fault():
  f=setup(cur,today);d=save(cur,f['payload']);before=b.boundary.snapshot(cur)
  cur.execute("create function cp7_plan_native.controlled_receipt_failure()returns trigger language plpgsql as $$begin raise exception 'P08_CONTROLLED_RECEIPT_FAILURE';end$$;create trigger p08_controlled_receipt_failure before insert on cp7_plan_native.intents for each row execute function cp7_plan_native.controlled_receipt_failure()",prepare=False)
  try:auth.refused(cur,lambda:apply(cur,action(d)),'P08_CONTROLLED_RECEIPT_FAILURE')
  finally:cur.execute('drop trigger p08_controlled_receipt_failure on cp7_plan_native.intents;drop function cp7_plan_native.controlled_receipt_failure()',prepare=False)
  assert b.boundary.snapshot(cur)==before and not cur.execute('select exists(select 1 from cp7_plan_native.intents)').fetchone()[0]
  return dict(status='PASS',controlled_after_actual_Native_writer_receipt_failure_rolls_domain_back_no_orphan=True)
 def frozen():
  f=setup(cur,today);d=save(cur,f['payload']);auth.refused(cur,lambda:cur.execute('delete from cp7_plan_native.drafts where id=%s',(d['draft_id'],)),'CP7_RUN_IMMUTABLE')
  assert not cur.execute("select has_function_privilege('cp7_capture','public.erp_cp7_apply_plan_action_v1(jsonb,uuid)','EXECUTE')or has_function_privilege('cp7_capture','public.erp_save_cutting_group_before_sewing_v2(jsonb,uuid,bigint)','EXECUTE')").fetchone()[0]
  return dict(status='PASS',immutable_draft_and_read_compute_principal_cannot_call_mutators=True)
 from cp7_plan_actual_cases import cases as actual_cases
 return list(zip(['P08_METADATA','P08_SAVE_REPLAY','P08_VERSION','P08_PREVIEW_READONLY','P08_NATIVE_APPLY','P08_APPLY_REPLAY','E09_PLAN_STALE','P08_CURRENT_AUTH','P08_FOREIGN','P08_CLOSED','P08_NATIVE_IDENTITIES','O10_PLAN_QUANTITY','P08_ATOMIC_RECEIPT_FAILURE','E22_PLAN_COMPUTE_SEPARATION'],[metadata,replay_save,revision,readonly_preview,native_apply,apply_replay,stale,current,foreign,strict,identities,quantity,atomic_fault,frozen]))+actual_cases(cur,today)+material_cases(cur,today)

def races(tools,today):
 def shared_roll():
  from queue import Queue
  with tools.connect()as conn,conn.cursor()as cur:
   first,second=shared_material_setup(cur,today);one=current_payload(cur,today,first);two=current_payload(cur,today,second)
   d1=save(cur,one);d2=save(cur,two);before=monetary_state(cur);conn.commit()
  keys=[uuid.uuid4(),uuid.uuid4()];pids=Queue();gate=threading.Barrier(2);roll=one['cutting']['rolls'][0]['roll_id']
  def send(d,key):
   with tools.connect()as conn,conn.cursor()as cur:
    pids.put(cur.execute('select pg_backend_pid()').fetchone()[0]);gate.wait(timeout=5)
    try:result=apply(cur,action(d),key);conn.commit();return result
    except psycopg.Error as error:conn.rollback();return dict(error=error.diag.message_primary,sqlstate=error.sqlstate)
  with tools.connect()as holder,holder.cursor()as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:PLAN_MATERIAL_POOL:'||%s,0))",(roll,))
   with ThreadPoolExecutor(max_workers=2)as executor:
    jobs=[executor.submit(send,d,k)for d,k in zip((d1,d2),keys)];workers=[pids.get(timeout=5),pids.get(timeout=5)];observed=[]
    try:
     with tools.connect(autocommit=True)as inspector,inspector.cursor()as c:
      deadline=time.monotonic()+10
      while time.monotonic()<deadline:
       observed=c.execute("select pid,locktype,database,classid,objid,objsubid,granted from pg_locks where pid=any(%s)and locktype='advisory'and not granted order by pid",(workers,)).fetchall()
       if len(observed)==2:break
       time.sleep(.05)
      assert len(observed)==2 and observed[0][1:]==observed[1][1:],('SAME_PHYSICAL_POOL_WAIT_NOT_OBSERVED',observed)
    finally:holder.commit()
    results=[job.result(45)for job in jobs]
  successes=[x for x in results if x.get('kind')=='COMMITTED_OUTCOME'];losers=[x for x in results if x.get('sqlstate')=='40001']
  assert len(successes)==len(losers)==1 and losers[0]['error']in('CP7_PLAN_SHARED_MATERIAL_BUDGET_CHANGED','CP7_PLAN_SOURCE_CHANGED'),results
  with tools.connect()as conn,conn.cursor()as cur:
   pool=material_pool(cur,one);assert monetary_state(cur)==before
   assert cur.execute('select count(*)from cp7_plan_native.intents').fetchone()[0]==1
   assert [D(pool[k])for k in('native_available','linked_native_draft_qty','free_for_new_plan')]==[D(10),D(6),D(4)],pool
  return dict(status='PASS',actual_two_distinct_targets_drafts_UUIDs=True,exact_two_workers_same_physical_pool_wait=observed,one_Native_draft_and_intent_other40001=True,physical_stock_money_HPP_unchanged=True,final_complete_pool=pool)
 def prepared(two=False):
  with tools.connect()as conn,conn.cursor()as cur:
   f=setup(cur,today);d=save(cur,f['payload']);other=None
   if two:
    other,role=custom(cur);orig=analysis.capture(cur,today,subject=other);p={**f['payload'],'run_id':orig['run_id'],'source_hash':orig['analysis']['snapshot']['source_hash']};d2=save(cur,p,subject=other)
   else:d2=save(cur,f['payload'])
   conn.commit();return f,d,d2,other
 def pair(kind):
  _,d,d2,other=prepared(kind=='ACTORS');key=uuid.uuid4();gate=threading.Barrier(2)
  def send(which):
   p=action(d2 if kind=='ACTORS'and which else d);request=key if kind!='ACTORS'else uuid.uuid4()
   if kind=='PAYLOAD'and which:p['reason']='Different reviewed payload on same UUID'
   with tools.connect()as conn,conn.cursor()as cur:
    gate.wait(timeout=5)
    try:out=apply(cur,p,request,other if kind=='ACTORS'and which else None);conn.commit();return out
    except psycopg.Error as e:conn.rollback();return str(e)
  with ThreadPoolExecutor(max_workers=2)as pool:jobs=[pool.submit(send,i)for i in range(2)];results=[j.result(45)for j in jobs]
  successes=[r for r in results if isinstance(r,dict)]
  if kind=='SAME':assert len(successes)==2 and successes[0]==successes[1],results
  else:assert len(successes)==1 and any(('CP7_PLAN_REQUEST_CHANGED'if kind=='PAYLOAD'else'CP7_PLAN_LINKED_INTENT_CONFLICT')in str(r)for r in results),results
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_plan_native.intents').fetchone()[0]==1
  return dict(status='PASS',two_real_connections=True,one_Native_domain_draft_and_intent=True,mode=kind,shared_target_lock_across_actor_run_draft=True)
 def revocation(native_roll=False):
  with tools.connect()as conn,conn.cursor()as cur:
   subject,role=custom(cur);f=setup(cur,today,subject);d=save(cur,f['payload'],subject=subject)
   conn.commit()
   # Compare the fully committed Native receipt/production fixture with the
   # later committed state; do not mix a preparation transaction with the race.
   before_money=monetary_state(cur);before_groups=cur.execute('select id from erp.cutting_groups order by id').fetchall();conn.rollback()
  key=uuid.uuid4()
  with tools.connect()as holder,holder.cursor()as h:
   if native_roll:h.execute('select id from erp.material_rolls where id=%s for update',(f['payload']['cutting']['rolls'][0]['roll_id'],))
   else:h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:PLAN_TARGET:'||%s,0))",(f['payload']['target_key'],))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=apply(cur,action(d),key,subject);conn.commit();return r
     except psycopg.Error as e:conn.rollback();return dict(error=str(e),sqlstate=e.sqlstate)
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send);waiting=False;deadline=time.monotonic()+10
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as c:
      while time.monotonic()<deadline:
       waiting=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event=%s and query like 'select public.erp_cp7_apply_plan_action_v1%%')",('transactionid'if native_roll else'advisory',)).fetchone()[0]
       if waiting:break
       time.sleep(.05)
      assert waiting,'Native apply did not wait on its actual protected lock'
      c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.cutting.create'",(role,))
    finally:holder.commit()
    result=job.result(45)
   expected='CP7_PLAN_ORIGINAL_ACCESS_CHANGED'if native_roll else'CP7_PLAN_ACCESS_DENIED'
   assert isinstance(result,dict)and result.get('sqlstate')=='42501'and result.get('error','').splitlines()[0]==expected,result
  with tools.connect()as conn,conn.cursor()as cur:
   assert not cur.execute('select exists(select 1 from cp7_plan_native.intents)or exists(select 1 from cp7_plan_native.commands)').fetchone()[0]
   assert cur.execute('select id from erp.cutting_groups order by id').fetchall()==before_groups
   after_money=monetary_state(cur);assert after_money==before_money,dict(before=before_money,after=after_money)
  return dict(status='PASS',observed_real_Native_roll_wait=native_roll,observed_canonical_target_wait=not native_roll,current_authority_after_wait_no_domain_or_receipt_commit=True,exact_authorization_sqlstate='42501',exact_native_refusal=expected,all_Native_drafts_money_stock_and_HPP_unchanged=True)
 from cp7_plan_actual_cases import races as actual_races
 return [('E10_REAL_SAME_UUID',lambda:pair('SAME')),('E10_REAL_SAME_UUID_DIFFERENT_PAYLOAD',lambda:pair('PAYLOAD')),('E11_REAL_DIFFERENT_ACTOR_RUN_DRAFT',lambda:pair('ACTORS')),('P08_REAL_TARGET_WAIT_REVOKED',lambda:revocation()),('P08_REAL_NATIVE_ROLL_WAIT_REVOKED',lambda:revocation(True))]+actual_races(tools,today)+[('P08_SHARED_FABRIC_REAL_TWO_TARGET_WAIT',shared_roll)]

def http_cases(http,today):
 def public_chain():
  owner=http.login('OWNER','p08-native-http');foreign=http.login('OWNER','p08-native-foreign')
  with http.connect()as conn,conn.cursor()as cur:
   f=setup(cur,today,owner.auth_user_id);conn.commit()
  p=f['payload'];d=owner.rpc('erp_cp7_save_plan_draft_v1',dict(p_payload=p,p_request=str(uuid.uuid4())));assert d['status']==200,d
  saved=d['body'];v=owner.rpc('erp_cp7_preview_plan_action_v1',dict(p_draft=saved['draft_id']));assert v['status']==200,v
  key=str(uuid.uuid4());args=dict(p_payload=action(saved),p_request=key);one=owner.rpc('erp_cp7_apply_plan_action_v1',args);assert one['status']==200,one
  assert owner.rpc('erp_cp7_apply_plan_action_v1',args)['body']==one['body']
  assert foreign.rpc('erp_cp7_apply_plan_action_v1',args)['status']==403 and http.anon_rpc('erp_cp7_apply_plan_action_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_apply_plan_action_v1',args)['status']==403 and owner.rpc('erp_cp7_read_plan_draft_v1',dict(p_draft=saved['draft_id']))['status']==403
  return dict(status='PASS',actual_Auth_HTTP_Native_draft_preview_apply_replay_foreign_anonymous_and_current_deactivation_denied=True)
 from cp7_plan_actual_cases import http_cases as actual_http
 return [('P08_REAL_AUTH_HTTP',public_chain)]+actual_http(http,today)
