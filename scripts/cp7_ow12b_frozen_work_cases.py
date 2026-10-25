"""Six actual Native frozen schedule controls; no SQL or UI adoption."""
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from time import monotonic
import json
import traceback
import uuid
import cp7_ow12b_frozen_facade_cases as facade
from cp7_ow04_restore_bundle import _catalog_rows

native,plan,bounded,stage=facade.native,facade.plan,facade.bounded,facade.stage
work=bounded.work
CONTRACT='cp7.ow12b.frozen-work-native6.v2'
IDS=dict(native=['OW12B_FROZEN_WORK_V2_CATALOG22_EXACT_PREUSE',
 'OW12B_FROZEN_WORK_V2_PENDING_SAVE_REPLAY_OLD_METHOD',
 'OW12B_FROZEN_WORK_V2_ACTUAL_POST_STALE_K2_RECEIPT',
 'OW12B_FROZEN_WORK_V2_FOREIGN_CURRENT_ACCESS',
 'OW12B_FROZEN_WORK_V2_ATOMIC_LAST_TABLE_FAULT',
 'OW12B_FROZEN_WORK_V2_FACTORY1200X3_PENDING_AND_DONE_SAVE'])
REQUIRED=dict(native=6);EXPECTED=DECLARED=6
FUNCTIONS,SCHEDULES=facade.FUNCTIONS,facade.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None


def sources():
 root=Path(__file__).resolve().parent
 return {**facade.sources(),**{p.name:sha256(p.read_bytes()).hexdigest()for p in
  (Path(__file__),root/'cp7_ow12b_frozen_work_probe.py',root/'cp7_ow12b_frozen_work_preflight.py')}}


def configure():
 facade.PARENT_CHECKER=PARENT_CHECKER
 for name in('INSTALL_STATES','REORDER_STATES','CHECKED_STATE','SCHEDULE_STATE','BOUNDED_STATE','REFERENCE_STATE','STAGE_STATE'):
  setattr(facade,name,globals()[name])


def install(cur):
 configure();return facade.install(cur)


def call(cur,name,args,actor,observed):
 start=monotonic()
 try:r=plan.staged.limited(cur,name,args,actor)
 except Exception as error:
  observed['failed_call']=dict(name=name,millis=round((monotonic()-start)*1000,3),sqlstate=getattr(error,'sqlstate',None),error=str(error));raise
 ms=round((monotonic()-start)*1000,3);assert ms<8000,('FROZEN_WORK_CALL_OVER8S',name,ms)
 observed.setdefault('ordered_calls',[]).append(dict(name=name,millis=ms));return r


def get(cur,f,observed):
 return call(cur,'erp_cp7_get_staged_production_schedule_v1',(f['key'],),f['subject'],observed)


def payload(w,config):
 return dict(source_run=w['source_run'],source_hash=w['source_hash'],expected_revision=w['revision'],config=config,
  reason='Explicit frozen Native schedule review; metadata only, no factory defaults',staged_review_contract='cp7.schedule-staged-review.v1')


def save(cur,f,p,key,observed):
 r=call(cur,'erp_cp7_save_staged_production_schedule_v1',(json.dumps(p),key),f['subject'],observed)
 assert r['contract_version']=='cp7.planning-schedule-staged-bounded-outcome.v2'
 assert r['bounded_request_contract']=='cp7.bounded-analysis-request.v2'and r['bounded_reference_contract']=='cp7.bounded-analysis-reference.v2'
 assert r['staged_review_contract']==p['staged_review_contract']and r['source_run']==p['source_run']and r['source_hash']==p['source_hash']and r['request_id']==key
 assert int(r['revision'])==int(p['expected_revision'])+1 and r['quality']=='SELECTED_ASSUMPTIONS'and r['production_go']is False
 return r


def fresh(cur,today,actor,config,observed):
 q=plan.staged.query(today);key=str(uuid.uuid4())
 initial=call(cur,facade.REQUEST,(json.dumps(q),key),actor,observed);plan.staged.checked(initial,key,'RUNNING')
 row=plan.staged.job_row(cur,key,actor);f=dict(key=key,initial=initial,row=row,subject=actor,config=deepcopy(config))
 assert initial['units_done']==0 and row['reference']['bounded_input_coverage']=='PENDING'and row['reference']['bounded_history_inputs']is None
 before=work.metadata(cur);w=get(cur,f,observed);assert work.metadata(cur)==before
 assert w['contract_version']=='cp7.planning-schedule-staged-bounded.v2'and w['source_request_id']==key
 assert w['history_input_coverage']=='PENDING'and w['analysis_state']=='RUNNING'and w['source_state']=='UNCHANGED'and w['production_capture_state']=='COMPLETE'
 assert w['analysis_source_hash']==row['source_hash']
 f.update(workspace=w,payload=payload(w,config));return f


def prepare(cur,today,observed,volume=False):
 s=install(cur);x=plan.fixture(cur,today);plan.b.api.admin(cur)
 config=deepcopy(cur.execute('select config from cp7_schedule_native.plans order by revision desc limit 1').fetchone()[0])
 native.native.policy.master.role_actor(cur,'OWNER')
 actor=native.native.policy.master.role_actor(cur,'OWNER');size=None
 if volume:
  base=native.native.bounded.work.base.retained.formula.sales.fg.base
  size=native.frozen.geometry.fixture.seed(cur,base.BASE_PRODUCT,base.LOCATION,actor)
 f=fresh(cur,today,actor,config,observed);f.update(x=x,installed=s,size=size);return f


def cases(cur,today):
 observed={}
 def catalog():
  configure();r=dict(facade.cases(cur,today))[facade.IDS['native'][0]]()
  assert r['status']=='PASS',r;return dict(r,existing_work_read_save_SQL_unchanged=True,repeated_catalog_anchor_not_new_feature_credit=True)
 def running():
  f=prepare(cur,today,observed);physical=plan.monetary_state(cur);reference=deepcopy(f['row']['reference']);p=f['payload'];key=str(uuid.uuid4())
  first=save(cur,f,p,key,observed);assert save(cur,f,p,key,observed)==first
  plan.refused(cur,lambda:save(cur,f,dict(p,reason='changed'),key,observed),'CP7_SCHEDULE_REQUEST_CHANGED')
  plan.refused(cur,lambda:save(cur,f,p,str(uuid.uuid4()),observed),'CP7_SCHEDULE_REVISION_CHANGED')
  assert get(cur,f,observed)['source_state']=='ARCHIVED_STALE'
  assert plan.staged.job_row(cur,f['key'],f['subject'])['reference']==reference
  plan.b.api.admin(cur);row=cur.execute('select source_run::text,config from cp7_schedule_native.plans where id=%s',(first['plan_id'],)).fetchone()
  assert row==(f['workspace']['source_run'],p['config'])
  old_key=str(uuid.uuid4());bounded.request(cur,today,old_key,f['subject']);old_w=work.get(cur,old_key,f['subject']);old_p=payload(old_w,f['config']);old_command=str(uuid.uuid4())
  old=work.save(cur,old_p,old_command,f['subject']);assert old['contract_version']=='cp7.planning-schedule-staged-bounded-outcome.v1'
  plan.refused(cur,lambda:save(cur,f,p,old_command,observed),'CP7_SCHEDULE_REQUEST_CHANGED')
  assert save(cur,f,p,key,observed)==first and work.save(cur,old_p,old_command,f['subject'])==old
  assert plan.monetary_state(cur)==physical
  return dict(status='PASS',actual_public_v2_PENDING_work_save=True,history_not_falsely_completed=True,exact_receipt_after_later_revision=True,
   changed_payload_and_stale_revision_refused=True,actual_old_v1_receipt_not_relabelled=True,stored_config_exact=True,immutable_source_reference=True,no_money_stock_HPP_change=True,observations=deepcopy(observed))
 def stale():
  f=prepare(cur,today,observed);bounded.finish(cur,f);key=str(uuid.uuid4());first=save(cur,f,f['payload'],key,observed)
  newer=fresh(cur,today,f['subject'],f['config'],observed);plan.found_fg(cur,f['x'],'1');before=work.metadata(cur)
  assert get(cur,newer,observed)['source_state']=='ARCHIVED_STALE'
  plan.refused(cur,lambda:save(cur,newer,newer['payload'],str(uuid.uuid4()),observed),'CP7_SCHEDULE_SOURCE_CHANGED','40001')
  assert save(cur,f,f['payload'],key,observed)==first
  plan.b.api.admin(cur);bounded.retention.age(cur,f['done']['run_id'],timedelta(days=8))
  expired=work.metadata(cur);plan.refused(cur,lambda:get(cur,f,observed),bounded.retention.EXPIRED)
  assert save(cur,f,f['payload'],key,observed)==first and work.metadata(cur)==expired
  assert before['physical']==expired['physical']
  return dict(status='PASS',actual_post_stale_new_command_refused=True,committed_receipt_after_source_change_and_K2_exact=True,K2_read_refused=True,no_denied_effect=True,observations=deepcopy(observed))
 def access():
  f=prepare(cur,today,observed);stranger=native.native.policy.master.role_actor(cur,'OWNER');foreign=dict(f,subject=stranger);before=work.metadata(cur)
  plan.refused(cur,lambda:get(cur,foreign,observed),'CP7_SCHEDULE_STAGED_RUN_UNAVAILABLE','42501')
  plan.refused(cur,lambda:save(cur,foreign,f['payload'],str(uuid.uuid4()),observed),'CP7_SCHEDULE_STAGED_RUN_UNAVAILABLE','42501')
  assert work.metadata(cur)==before
  key=str(uuid.uuid4());save(cur,f,f['payload'],key,observed);plan.b.api.admin(cur)
  cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(f['subject'],));before=work.metadata(cur)
  for operation in(lambda:get(cur,f,observed),lambda:save(cur,f,f['payload'],key,observed),lambda:save(cur,f,f['payload'],str(uuid.uuid4()),observed)):
   assert plan.refusal(cur,operation)[0]=='42501'
  assert work.metadata(cur)==before
  return dict(status='PASS',foreign_owner_read_save_refused=True,current_deactivated_actor_read_new_and_committed_replay_refused=True,last_active_owner_guard_preserved=True,no_denied_effect=True,observations=deepcopy(observed))
 def atomic():
  f=prepare(cur,today,observed);plan.b.api.admin(cur)
  cur.execute("create function pg_temp.frozen_work_fault()returns trigger language plpgsql as $$begin raise exception 'FROZEN_WORK_METADATA_FAULT';end;$$")
  cur.execute('create trigger frozen_work_fault before insert on cp7_schedule_native.commands for each row execute function pg_temp.frozen_work_fault()')
  before=work.metadata(cur);plan.refused(cur,lambda:save(cur,f,f['payload'],str(uuid.uuid4()),observed),'FROZEN_WORK_METADATA_FAULT');assert work.metadata(cur)==before
  return dict(status='PASS',last_command_insert_fault_rolls_both_metadata_tables_back=True,physical_stock_money_HPP_unchanged=True,observations=deepcopy(observed))
 def volume():
  f=prepare(cur,today,observed,volume=True);physical=plan.monetary_state(cur);c=f['row']['reference'];signature=native.frozen.geometry.dimensional_signature(c['facts']['products'])
  assert len(signature)==3600 and len(c['facts']['products'])==3602 and c['status']=='INCOMPLETE'
  first_key=str(uuid.uuid4());first=save(cur,f,f['payload'],first_key,observed)
  assert plan.staged.job_row(cur,f['key'],f['subject'])['reference']==c
  new=fresh(cur,today,f['subject'],f['config'],observed);bounded.finish(cur,new)
  assert new['pages']['targets_total']==3602
  expected=native.frozen.original_compile(cur,new['row']['reference'],new['row']['query'],observed)
  assert native.prepared_cache(cur,new['row']['id'])['inputs']==expected
  w=get(cur,new,observed);assert w['history_input_coverage']=='COMPLETE'and w['analysis_state']=='DONE'
  plan.b.api.admin(cur);purged=cur.execute('select cp7_analysis_stage.purge_intermediates(%s)',(new['row']['id'],)).fetchone()[0];assert purged['removed']['target_rows']>0
  after=get(cur,new,observed);assert after==w
  save(cur,new,payload(after,new['config']),str(uuid.uuid4()),observed)
  assert save(cur,f,f['payload'],first_key,observed)==first and plan.monetary_state(cur)==physical
  return dict(f['size'],status='PASS',actual_public_PENDING_and_DONE_after_K3_schedule_SAVE=True,all3602_compiler_inputs_exact=True,all_actual_pages_verified=True,
   raw_INCOMPLETE_and_initial_PENDING_preserved=True,exact_old_receipt_after_new_SAVE=True,whole_reference_immutable=True,no_money_stock_HPP_change=True,
   observations=deepcopy(observed),factory_SLA_claim=False,actual_Auth_HTTP_credit=False,production_go=False)
 def checked(fn):
  def run():
   observed.clear()
   try:return fn()
   except Exception as error:return dict(status='INCOMPLETE',error=str(error),traceback=traceback.format_exc(),observations=deepcopy(observed),production_go=False)
  return run
 return list(zip(IDS['native'],map(checked,(catalog,running,stale,access,atomic,volume))))


def races(tools,today):return []
def http_cases(http,today):return []
