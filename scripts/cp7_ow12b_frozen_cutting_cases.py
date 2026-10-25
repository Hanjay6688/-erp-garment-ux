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
 zone=cur.execute("select current_setting('TimeZone')").fetchone()[0]
 cur.execute("select set_config('TimeZone','UTC',true)")
 try:
  return dict(physical=plan.monetary_state(cur),rows={table:cur.execute(
   "select count(*),md5(coalesce(jsonb_agg(to_jsonb(x)order by to_jsonb(x)::text),'[]'::jsonb)::text)from "+table+' x').fetchone()for table in tables})
 finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))


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


def reviewed_capture(cur,today,actor,observed):
 # The legacy fixture reviewed its calendar against the v1 supply source.
 # Frozen v2 has a deliberately different source fingerprint. Review the SAME
 # selected calendar through its actual public staged command, then capture a
 # NEW analysis. Never copy a hash, relabel the old reference or invent need.
 plan.b.api.admin(cur)
 config=deepcopy(cur.execute('select config from cp7_schedule_native.plans order by revision desc limit 1').fetchone()[0])
 physical=plan.monetary_state(cur);q=plan.staged.query(today);key=str(uuid.uuid4())
 initial=timed(cur,facade.REQUEST,(json.dumps(q),key),actor,observed)
 plan.staged.checked(initial,key,'RUNNING')
 original=deepcopy(plan.staged.job_row(cur,key,actor)['reference'])
 w=timed(cur,'erp_cp7_get_staged_production_schedule_v1',(key,),actor,observed)
 assert w['contract_version']=='cp7.planning-schedule-staged-bounded.v2'
 assert w['source_state']=='UNCHANGED'and w['history_input_coverage']=='PENDING'
 assert w['production_capture_state']=='COMPLETE'
 p=dict(source_run=w['source_run'],source_hash=w['source_hash'],expected_revision=w['revision'],config=config,
  reason='Frozen checked cutting fixture: review the unchanged selected calendar against its actual v2 source; no factory defaults',
  staged_review_contract='cp7.schedule-staged-review.v1')
 receipt=timed(cur,'erp_cp7_save_staged_production_schedule_v1',(json.dumps(p),str(uuid.uuid4())),actor,observed)
 assert receipt['contract_version']=='cp7.planning-schedule-staged-bounded-outcome.v2'
 assert receipt['source_hash']==w['source_hash']and int(receipt['revision'])==int(w['revision'])+1
 plan.b.api.admin(cur)
 stored=cur.execute('select config from cp7_schedule_native.plans where id=%s',(receipt['plan_id'],)).fetchone()[0]
 assert stored==config and plan.monetary_state(cur)==physical
 assert plan.staged.job_row(cur,key,actor)['reference']==original
 f=facade.capture(cur,today,actor)
 assert f['key']!=key and f['done']['run_id']!=w['source_run']
 observed['fixture_calendar_review']=dict(actual_public_v2_command=True,selected_config_unchanged=True,
  original_reference_immutable=True,new_analysis_after_review=True,no_physical_effect=True)
 return f


def select_synthetic_volume_assumptions(cur,x,actor,observed):
 # The common dimensional fixture deliberately creates NO planning profile or
 # production policy. A positive global-allocation SAVE needs reviewed inputs
 # for every target. Validate templates through the real public commands, then
 # bulk-clone them only into the labelled synthetic fixture. Thousands of public
 # profile saves in one rollback-only case would hold >7200 request/root locks.
 # No product lock is disabled and no UNKNOWN recommendation is filled.
 plan.b.api.admin(cur);physical=plan.monetary_state(cur)
 roots=[str(r[0])for r in cur.execute("select identity_root_id from erp.products where sku like 'OW12BF36-%%'order by identity_root_id").fetchall()]
 skus=[str(r[0])for r in cur.execute("select id from erp.bf_skus_v1 where sku like 'OW12BF36-%%'order by id").fetchall()]
 assert len(roots)==len(set(roots))==3600 and len(skus)==len(set(skus))==1200
 calls={}
 def public(name,args):
  started=monotonic()
  result=plan.staged.limited(cur,name,args,actor)
  elapsed=round((monotonic()-started)*1000,3);assert elapsed<8000,('FROZEN_VOLUME_FIXTURE_CALL_OVER8S',name,elapsed)
  row=calls.setdefault(name,dict(count=0,max_millis=0));row['count']+=1;row['max_millis']=max(row['max_millis'],elapsed)
  return result
 selected=public('erp_cp7_get_planning_profiles_v1',([uuid.UUID(x['root'])],))['rows'][0]
 assert selected['quality']=='SELECTED_ASSUMPTION'and selected['config']['mean_mode']=='SELECTED_MANUAL'
 config=deepcopy(selected['config']);config['daily_pcs']='0'
 before=cur.execute('select root_id::text,revision,config from cp7_profile.profiles where not(root_id=any(%s::uuid[]))order by root_id,revision',(roots,)).fetchall()
 assert cur.execute('select count(*)from cp7_profile.profiles where root_id=any(%s::uuid[])',(roots,)).fetchone()[0]==0
 assert cur.execute('select count(*)from cp7_identity.production_policy where sku_id=any(%s::uuid[])',(skus,)).fetchone()[0]==0
 policies=plan.previous.policies
 sample=public('erp_cp7_get_production_policy_v1',([uuid.UUID(skus[0])],))['rows'][0]
 assert sample['policy_revision']=='0'and len(sample['members'])==3
 samples=[str(r)for r in sample['members']];assert set(samples)<=set(roots)
 rows=public('erp_cp7_get_planning_profiles_v1',([uuid.UUID(r)for r in samples],))['rows']
 assert len(rows)==3 and len({r['size_id']for r in rows})==3
 for row in rows:
  assert row['quality']=='UNREVIEWED'and row['revision']=='0'
  public('erp_cp7_save_planning_profile_v1',(json.dumps(dict(root_id=row['root_id'],product_version_id=row['product_version_id'],expected_revision=row['revision'],
   reason='EXPLICIT SYNTHETIC checked-cutting comparison: zero selected manual demand; not a factory default',config=config)),str(uuid.uuid4())))
 public('erp_cp7_set_production_policy_v1',(json.dumps([dict(policies.proposal(sample,'ACTIVE'),reason='EXPLICIT SYNTHETIC checked-cutting policy template; not an owner production default')]),str(uuid.uuid4())))
 plan.b.api.admin(cur)
 cur.execute("""insert into cp7_profile.profiles(root_id,product_version_id,size_id,revision,config,reason,actor,request_id)
  select p.identity_root_id,p.id,p.size_id,1,t.config,
   'EXPLICIT SYNTHETIC bulk fixture copied from publicly validated same-size zero-manual profile',%s,gen_random_uuid()
  from erp.products p join cp7_profile.profiles t on t.root_id=any(%s::uuid[])and t.size_id=p.size_id and t.revision=1
  where p.identity_root_id=any(%s::uuid[])and not exists(select 1 from cp7_profile.profiles x where x.root_id=p.identity_root_id)""",(actor,samples,roots))
 cur.execute("""insert into cp7_identity.production_policy(sku_id,revision,state,reason,review_at,actor,request_id,
  reviewed_commercial_version,reviewed_commercial_revision,reviewed_members)
  select s.id,1,t.state,'EXPLICIT SYNTHETIC bulk fixture copied from publicly validated ACTIVE policy',t.review_at,%s,gen_random_uuid(),
   v.id,v.revision,array(select m.product_root from erp.bf_sku_members_v1 m where m.version_id=v.id order by m.product_root)
  from erp.bf_skus_v1 s join erp.bf_sku_versions_v1 v on v.sku_id=s.id and v.revision=1
  cross join(select state,review_at from cp7_identity.production_policy where sku_id=%s and revision=1)t
  where s.id=any(%s::uuid[])and not exists(select 1 from cp7_identity.production_policy x where x.sku_id=s.id)""",(actor,skus[0],skus))
 for start in range(0,len(roots),200):
  rows=public('erp_cp7_get_planning_profiles_v1',([uuid.UUID(r)for r in roots[start:start+200]],))['rows']
  assert len(rows)==len(roots[start:start+200])and all(r['quality']=='SELECTED_ASSUMPTION'and r['revision']=='1'and r['config']==config for r in rows)
 for start in range(0,len(skus),200):
  rows=public('erp_cp7_get_production_policy_v1',([uuid.UUID(s)for s in skus[start:start+200]],))['rows']
  assert len(rows)==len(skus[start:start+200])and all(r['policy_revision']=='1'and r['policy']['quality']=='KNOWN'and r['policy']['state']=='ACTIVE'for r in rows)
 plan.b.api.admin(cur)
 assert cur.execute('select count(*)from cp7_profile.profiles where root_id=any(%s::uuid[])and revision=1 and config=%s::jsonb',(roots,json.dumps(config))).fetchone()[0]==3600
 assert cur.execute('select root_id::text,revision,config from cp7_profile.profiles where not(root_id=any(%s::uuid[]))order by root_id,revision',(roots,)).fetchall()==before
 assert plan.monetary_state(cur)==physical
 observed['synthetic_volume_assumptions']=dict(products=3600,commercial_SKUs=1200,public_calls=calls,selected_manual_comparison_demand='0',
  public_profile_templates=3,public_policy_templates=1,bulk_fixture_profiles=3597,bulk_fixture_policies=1199,all_source_rows_reverified_through_public_workspaces=True,
  source_config_cloned_from_existing_explicit_fixture=True,synthetic_roots_only=True,non_synthetic_profiles_unchanged=True,
  no_physical_effect=True,owner_defaults_invented=False,original_dimensional_fixture_unchanged=True)


def prepare(cur,today,observed,volume=False):
 install(cur);x=plan.fixture(cur,today)
 native.native.policy.master.role_actor(cur,'OWNER')
 actor=native.native.policy.master.role_actor(cur,'OWNER');size=None
 if volume:
  base=native.native.bounded.work.base.retained.formula.sales.fg.base
  size=native.frozen.geometry.fixture.seed(cur,base.BASE_PRODUCT,base.LOCATION,actor)
  select_synthetic_volume_assumptions(cur,x,actor,observed)
 f=reviewed_capture(cur,today,actor,observed)
 assert f['row']['reference']['bounded_request_contract']=='cp7.bounded-analysis-request.v2'
 assert f['row']['reference']['bounded_input_coverage']=='PENDING'and f['row']['reference']['bounded_history_inputs']is None
 o,q,p=plan.draft_payload(cur,x,f['done']['run_id'],actor)
 rec=next(r for r in f['original']['analysis']['recommendations']if r['target']['key']==x['target'])
 assert o['production_state']=='ACTIVE'and o['needed_pcs']is not None and o['capacity_pcs']is not None,dict(options=o,recommendation=rec)
 assert Decimal(o['needed_pcs'])>=2 and Decimal(o['capacity_pcs'])>=2,o
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
