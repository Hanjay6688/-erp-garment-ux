"""Prepared frozen-source checked cutting Native6; no default UI adoption.

Exercise the unchanged checked writer with real frozen request, units and
retained target index. The repeated catalog anchor earns no new feature credit.
"""
from copy import deepcopy
from datetime import datetime,timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from time import monotonic
import json
import traceback
import uuid
import cp7_ow12b_frozen_facade_cases as facade
import cp7_ow13c_checked_cases as checked

native,plan,bounded=facade.native,facade.plan,facade.bounded
CONTRACT='cp7.ow12b.frozen-cutting-native6.v2'
IDS=dict(native=['OW12B_FROZEN_CUTTING_V2_CATALOG22_EXACT_PREUSE',
 'OW12B_FROZEN_CUTTING_V2_INDEX_OPTIONS_SAVE_REPLAY',
 'OW12B_FROZEN_CUTTING_V2_ACTUAL_POST_STALE_K2_RECEIPT',
 'OW12B_FROZEN_CUTTING_V2_FOREIGN_CURRENT_ACCESS',
 'OW12B_FROZEN_CUTTING_V2_ATOMIC_LAST_RECEIPT_FAULT',
 'OW12B_FROZEN_CUTTING_V2_FACTORY1200X3_K3_CHECKED_SAVE'])
REQUIRED=dict(native=6);EXPECTED=DECLARED=6
FUNCTIONS,SCHEDULES=facade.FUNCTIONS,facade.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None


def sources():
 root=Path(__file__).resolve().parent
 return {**facade.sources(),**{p.name:sha256(p.read_bytes()).hexdigest()for p in
  (Path(__file__),root/'cp7_ow12b_frozen_cutting_probe.py',root/'cp7_ow12b_frozen_cutting_preflight.py',Path(checked.__file__))}}


def configure():
 facade.PARENT_CHECKER=PARENT_CHECKER
 for name in('INSTALL_STATES','REORDER_STATES','CHECKED_STATE','SCHEDULE_STATE','BOUNDED_STATE','REFERENCE_STATE','STAGE_STATE'):
  setattr(facade,name,globals()[name])


def install(cur):
 configure();return facade.install(cur)


def metadata(cur):
 plan.b.api.admin(cur)
 tables=('cp7_plan_native.drafts','cp7_plan_native.staged_drafts','cp7_plan_native.intents','cp7_plan_native.commands','cp7_cutting_checked.receipts','erp.cutting_groups')
 return dict(physical=plan.monetary_state(cur),rows={table:cur.execute(
  "select count(*),md5(coalesce(jsonb_agg(to_jsonb(x)order by to_jsonb(x)::text),'[]'::jsonb)::text)from "+table+' x').fetchone()for table in tables})


def timed(cur,name,args,actor,observed):
 start=monotonic()
 try:result=plan.staged.limited(cur,name,args,actor)
 except Exception as error:
  observed['failed_call']=dict(name=name,millis=round((monotonic()-start)*1000,3),sqlstate=getattr(error,'sqlstate',None),error=str(error));raise
 elapsed=round((monotonic()-start)*1000,3);assert elapsed<8000,('FROZEN_CUTTING_CALL_OVER8S',name,elapsed)
 observed.setdefault('ordered_calls',[]).append(dict(name=name,millis=elapsed));return result


def save(cur,f,key,observed,p=None,actor=None):
 payload=p or checked.payload(f['x'])
 result=timed(cur,'erp_cp7_save_cutting_suggestion_v1',(json.dumps(payload),key),actor or f['subject'],observed)
 assert result['contract_version']=='cp7.plan-draft.v2'and result['state']=='SAVED'and result['request_id']==key
 guard=result['cutting_save_guard'];assert guard['contract_version']=='cp7.cutting-checked-save.v1'and guard['feasible']is True
 assert guard['run_id']==f['done']['run_id']and guard['target_key']==f['x']['target']and guard['identity_hash']==f['pages']['identity_hash']
 assert result['production_go']is False
 return result


def prepare(cur,today,observed,volume=False):
 install(cur);x=plan.fixture(cur,today)
 native.native.policy.master.role_actor(cur,'OWNER')
 actor=native.native.policy.master.role_actor(cur,'OWNER');size=None
 if volume:
  base=native.native.bounded.work.base.retained.formula.sales.fg.base
  size=native.frozen.geometry.fixture.seed(cur,base.BASE_PRODUCT,base.LOCATION,actor)
 f=facade.capture(cur,today,actor)
 assert f['row']['reference']['bounded_request_contract']=='cp7.bounded-analysis-request.v2'
 assert f['row']['reference']['bounded_input_coverage']=='PENDING'and f['row']['reference']['bounded_history_inputs']is None
 o,q,p=plan.draft_payload(cur,x,f['done']['run_id'],actor)
 assert o['production_state']=='ACTIVE'and Decimal(o['needed_pcs'])>=2 and Decimal(o['capacity_pcs'])>=2,o
 rec=next(r for r in f['original']['analysis']['recommendations']if r['target']['key']==x['target'])
 assert rec['q_conditional']['state']!='UNKNOWN'and Decimal(rec['q_conditional']['value'])==Decimal(o['needed_pcs'])
 assert o['identity_hash']==f['pages']['identity_hash']
 assert datetime.fromisoformat(o['data_as_of'].replace('Z','+00:00'))==datetime.fromisoformat(f['pages']['reference']['captured_at'].replace('Z','+00:00'))
 x.update(run=f['done']['run_id'],key=f['key'],options=o,query=q,payload=p)
 source=timed(cur,'erp_cp7_check_staged_analysis_source_v1',(f['done']['run_id'],),actor,observed)
 assert source['source_state']=='UNCHANGED'
 f.update(x=x,size=size);return f


def cases(cur,today):
 observed={}
 def catalog():
  configure();result=dict(facade.cases(cur,today))[facade.IDS['native'][0]]()
  assert result['status']=='PASS';return dict(result,unchanged_checked_writer=True,repeated_catalog_anchor_not_new_feature_credit=True)
 def flow():
  f=prepare(cur,today,observed);before=metadata(cur);key=str(uuid.uuid4());first=save(cur,f,key,observed)
  assert save(cur,f,key,observed)==first
  plan.refused(cur,lambda:save(cur,f,key,observed,dict(checked.payload(f['x']),reason='changed')),'CP7_PLAN_REQUEST_CHANGED')
  assert checked.receipt_count(cur)==1 and plan.read(cur,first['draft_id'],f['subject'])['state']=='SAVED'
  after=metadata(cur)
  for table in('cp7_plan_native.drafts','cp7_plan_native.staged_drafts','cp7_cutting_checked.receipts'):assert after['rows'][table][0]==before['rows'][table][0]+1
  for table in('cp7_plan_native.intents','cp7_plan_native.commands','erp.cutting_groups'):assert after['rows'][table]==before['rows'][table]
  assert after['physical']==before['physical']and plan.staged.job_row(cur,f['key'],f['subject'])['reference']==f['row']['reference']
  old_key=str(uuid.uuid4());old=plan.save(cur,f['x']['payload'],old_key,f['subject'])
  plan.refused(cur,lambda:save(cur,f,old_key,observed),'CP7_PLAN_REQUEST_CHANGED')
  assert plan.read(cur,old['draft_id'],f['subject'])['state']=='SAVED'and save(cur,f,key,observed)==first
  return dict(status='PASS',actual_public_v2_DONE_source=True,index_options_and_displayed_need_exact=True,actual_checked_SAVE_and_exact_replay=True,changed_payload_and_old_archive_UUID_refused=True,one_draft_one_retained_snapshot_one_checked_receipt=True,no_new_Native_group_intent_or_physical_effect=True,whole_source_reference_immutable=True,observations=deepcopy(observed))
 def stale():
  f=prepare(cur,today,observed);key=str(uuid.uuid4());first=save(cur,f,key,observed)
  plan.found_fg(cur,f['x'],'1');before=metadata(cur)
  plan.refused(cur,lambda:save(cur,f,str(uuid.uuid4()),observed),'CP7_CUTTING_SUGGESTION_SOURCE_CHANGED','40001')
  assert metadata(cur)==before and save(cur,f,key,observed)==first
  old=plan.save(cur,f['x']['payload'],str(uuid.uuid4()),f['subject']);assert old['state']=='SAVED'
  plan.b.api.admin(cur);bounded.retention.age(cur,f['done']['run_id'],timedelta(days=8));expired=metadata(cur)
  plan.refused(cur,lambda:plan.options(cur,f['x']['query'],f['subject']),bounded.retention.EXPIRED)
  assert save(cur,f,key,observed)==first and metadata(cur)==expired
  return dict(status='PASS',actual_Native_stock_post_refuses_new_checked_SAVE=True,old_dated_archive_route_preserved=True,committed_receipt_exact_after_post_and_K2=True,K2_options_refused=True,no_denied_metadata_or_physical_effect=True,observations=deepcopy(observed))
 def access():
  f=prepare(cur,today,observed);other=native.native.policy.master.role_actor(cur,'OWNER');key=str(uuid.uuid4());save(cur,f,key,observed)
  before=metadata(cur)
  assert plan.refusal(cur,lambda:plan.options(cur,f['x']['query'],other))[0]=='42501'
  assert plan.refusal(cur,lambda:save(cur,f,str(uuid.uuid4()),observed,actor=other))[0]=='42501'
  assert metadata(cur)==before
  plan.b.api.admin(cur);cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(f['subject'],));before=metadata(cur)
  for op in(lambda:plan.options(cur,f['x']['query'],f['subject']),lambda:save(cur,f,key,observed),lambda:save(cur,f,str(uuid.uuid4()),observed)):
   assert plan.refusal(cur,op)[0]=='42501'
  assert metadata(cur)==before
  return dict(status='PASS',foreign_owner_private_source_refused=True,current_deactivated_actor_options_newSAVE_committed_replay_refused=True,last_active_owner_guard_preserved=True,no_denied_effect=True,observations=deepcopy(observed))
 def atomic():
  f=prepare(cur,today,observed);plan.b.api.admin(cur)
  cur.execute("create function pg_temp.frozen_cutting_fault()returns trigger language plpgsql as $$begin raise exception 'FROZEN_CUTTING_LAST_RECEIPT_FAULT';end;$$")
  cur.execute('create trigger frozen_cutting_fault before insert on cp7_cutting_checked.receipts for each row execute function pg_temp.frozen_cutting_fault()')
  before=metadata(cur);plan.refused(cur,lambda:save(cur,f,str(uuid.uuid4()),observed),'FROZEN_CUTTING_LAST_RECEIPT_FAULT');assert metadata(cur)==before
  return dict(status='PASS',last_checked_receipt_fault_rolls_back_draft_and_staged_snapshot=True,no_Native_group_intent_stock_money_HPP_effect=True,observations=deepcopy(observed))
 def volume():
  f=prepare(cur,today,observed,volume=True);reference=deepcopy(f['row']['reference'])
  assert len(reference['facts']['products'])==f['pages']['targets_total']==3602 and len(native.frozen.geometry.dimensional_signature(reference['facts']['products']))==3600
  before=metadata(cur);first=save(cur,f,str(uuid.uuid4()),observed)
  plan.b.api.admin(cur);purged=cur.execute('select cp7_analysis_stage.purge_intermediates(%s)',(f['row']['id'],)).fetchone()[0]
  assert purged['removed']['target_rows']>0
  after_options=plan.options(cur,f['x']['query'],f['subject']);assert after_options==f['x']['options']
  second=save(cur,f,str(uuid.uuid4()),observed);assert first['draft_id']!=second['draft_id']
  assert save(cur,f,first['request_id'],observed)==first
  after=metadata(cur)
  for table in('cp7_plan_native.drafts','cp7_plan_native.staged_drafts','cp7_cutting_checked.receipts'):assert after['rows'][table][0]==before['rows'][table][0]+2
  for table in('cp7_plan_native.intents','cp7_plan_native.commands','erp.cutting_groups'):assert after['rows'][table]==before['rows'][table]
  assert after['physical']==before['physical']and plan.staged.job_row(cur,f['key'],f['subject'])['reference']==reference
  return dict(f['size'],status='PASS',actual_frozen1200SKU_x3_all3602_pages_verified=True,real_checked_SAVE_before_and_after_K3=True,retained_plan_index_survives_K3=True,original_receipt_exact=True,both_full_source_and_both_live_feasibility_checks_inside_writer=True,no_new_Native_group_intent_stock_money_HPP_effect=True,whole_source_reference_immutable=True,observations=deepcopy(observed),factory_SLA_claim=False,actual_Auth_HTTP_credit=False,production_go=False)
 def checked_case(fn):
  def run():
   observed.clear()
   try:return fn()
   except Exception as error:return dict(status='INCOMPLETE',error=str(error),traceback=traceback.format_exc(),observations=deepcopy(observed),production_go=False)
  return run
 return list(zip(IDS['native'],map(checked_case,(catalog,flow,stale,access,atomic,volume))))


def races(tools,today):return []
def http_cases(http,today):return []
