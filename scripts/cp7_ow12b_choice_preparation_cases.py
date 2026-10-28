"""Prepared Native6 provider for A's separate route; not registered or run.

Uses actual parent Native fixtures, public bounded RPCs and compiler. No change
to old Native6 budgets/results, F05 routing, default installer or production.
"""
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from time import monotonic
import json
import traceback
import uuid
import cp7_frozen_choice_preparation as stage
import cp7_ow12b_frozen_choice_cases as parent
from cp7_ow04_restore_bundle import _catalog_rows

plan,reader,native,choice=parent.plan,parent.reader,parent.native,parent.choice
CONTRACT='cp7.ow12b.choice-preparation-native6.v1'
IDS=dict(native=['OW12B_CHOICE_PREPARATION_CATALOG22_PREUSE',
 'OW12B_CHOICE_PREPARATION_K3_REQUEST_STEP_READ_SAVE_REPLAY',
 'OW12B_CHOICE_PREPARATION_CURRENT_ACCESS_AND_LIVE_SOURCE',
 'OW12B_CHOICE_PREPARATION_ATOMIC_SAVE_K2_USED_RESTORE',
 'OW12B_CHOICE_PREPARATION_CANCEL_RETRY_TERMINAL_FAILURE',
 'OW12B_CHOICE_PREPARATION_FACTORY1200X3_CACHED_K3_PHASE_PARITY'])
REQUIRED=dict(native=6);EXPECTED=DECLARED=6
FUNCTIONS=(*parent.FUNCTIONS,*(x.split('(')[0].removeprefix('public.')for x in stage.render.PUBLIC))
SCHEDULES=parent.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None

def sources():
 root=Path(__file__).resolve().parent
 return{**parent.sources(),**{'cp7_frozen_choice_preparation/'+k:v for k,v in stage.sources().items()},
  **{p.name:sha256(p.read_bytes()).hexdigest()for p in(Path(__file__),root/'cp7_ow12b_frozen_choice_preparation_local.mjs',root/'cp7_ow12b_frozen_choice_preparation_preflight.py')}}

def install(cur):
 parent.PARENT_CHECKER=PARENT_CHECKER
 for name in('INSTALL_STATES','REORDER_STATES','CHECKED_STATE','SCHEDULE_STATE','BOUNDED_STATE','REFERENCE_STATE','STAGE_STATE'):
  setattr(parent,name,globals()[name])
 parents=parent.install(cur)
 own=stage.install_delta(cur,lambda c:parent.stage.verify(c,parents['current']))
 return dict(parents=parents,current=own)

def call(cur,verb,f,observed,actor=None,epoch=None):
 start=monotonic()
 try:
  result=plan.staged.limited(cur,'erp_cp7_'+verb+'_frozen_choice_preparation_v1',
   (f['key'],epoch or f['pages']['access_epoch']),actor or f['subject'])
 except Exception as error:
  observed.setdefault('failed_calls',[]).append(dict(phase=verb,millis=round((monotonic()-start)*1000,3),sqlstate=getattr(error,'sqlstate',None),error=str(error)))
  raise
 elapsed=round((monotonic()-start)*1000,3)
 assert elapsed<8000,('CHOICE_PREPARATION_UNIT_OVER8S',verb,elapsed)
 observed.setdefault('calls',[]).append(dict(phase=verb,millis=elapsed,state=result['state'],units_done=result['units_done']))
 assert result['contract_version']=='cp7.frozen-choice-preparation.v1'
 assert result['source_request']==f['key']and result['run_id']==f['done']['run_id']
 assert result['reference']==f['pages']['reference']and result['stage']=='FROZEN_INPUTS'
 assert result['unit_count']==1 and result['units_done']==(1 if result['state']=='READY'else 0)
 assert result['choice_saved']is False and result['production_go']is False
 return result

def work(cur,f):
 plan.b.api.admin(cur)
 return cur.execute('select to_jsonb(w)from cp7_frozen_choice_preparation.work w where job_id=%s',(f['row']['id'],)).fetchone()[0]

def ready(cur,f,observed):
 # Reuse timings already collected by the real staged driver. No additional
 # reads or compiler calls for instrumentation. These are unit-call durations
 # (including fixture actor/setup overhead), not whole-analysis wall time.
 calls=deepcopy(f['calls']);assert calls
 by_stage={}
 for row in calls:
  group=by_stage.setdefault(row['stage'],dict(calls=0,total_millis=0,slowest_millis=0))
  group['calls']+=1;group['total_millis']+=row['ms'];group['slowest_millis']=max(group['slowest_millis'],row['ms'])
 for group in by_stage.values():group['total_millis']=round(group['total_millis'],3)
 observed.setdefault('completed_analysis_unit_timings',[]).append(dict(
  source_request=f['key'],run_id=f['done']['run_id'],targets=f['pages']['targets_total'],
  units_done=f['done']['units_done'],unit_count=f['done']['unit_count'],calls=calls,by_stage=by_stage,
  unit_calls_total_millis=round(sum(row['ms']for row in calls),3),
  includes_fixture_role_setup_overhead=True,whole_analysis_wall_time=False,
  added_database_calls=0,total8s_gate=False))
 before=plan.staged.job_row(cur,f['key'],f['subject'])
 first=call(cur,'request',f,observed);assert first['state']=='QUEUED'
 assert call(cur,'request',f,observed)==first and call(cur,'get',f,observed)==first
 result=call(cur,'step',f,observed);assert result['state']=='READY'
 assert work(cur,f)['payload']['inputs']==f['expected']
 assert call(cur,'step',f,observed)==result and call(cur,'get',f,observed)==result
 assert plan.staged.job_row(cur,f['key'],f['subject'])==before
 return result

def cases(cur,today):
 observed={}
 def catalog():
  before=_catalog_rows(cur);s=install(cur);v=stage.verify(cur,s['current'])
  assert(v['private_functions'],v['new_public_rpcs'],v['new_tables'])==(10,3,1)
  assert v['existing_replacements']==list(stage.render.originals())
  cur.execute('create view public.choice_preparation_inverse_guard as select public.erp_cp7_get_frozen_choice_preparation_v1(null,null)value')
  held=_catalog_rows(cur)
  try:stage.rollback_preuse(cur,s['current'])
  except Exception as error:assert getattr(error,'sqlstate',None)=='2BP01',str(error)
  else:raise AssertionError('CHOICE_PREPARATION_DEPENDENT_VIEW_DROPPED')
  assert _catalog_rows(cur)==held;cur.execute('drop view public.choice_preparation_inverse_guard')
  stage.rollback_preuse(cur,s['current']);parent.stage.rollback_preuse(cur,s['parents']['current'])
  reader.stage.rollback_preuse(cur,s['parents']['parents']['current']);native.unwind(cur,s['parents']['parents']['parents'])
  assert _catalog_rows(cur)==before
  return dict(status='PASS',exact_catalog22_composed_preuse_inverse=True,dependent_view_refused_atomically=True)
 def lifecycle():
  install(cur);f=parent.prepare(cur,today,observed);reader.purge(cur,f)
  physical=plan.monetary_state(cur);metadata=choice.metadata(cur)
  plan.refused(cur,lambda:reader.call(cur,f,f['target'],observed),'CP7_CHOICE_PREPARATION_REQUIRED')
  plan.refused(cur,lambda:parent.save(cur,f),'CP7_CHOICE_PREPARATION_REQUIRED')
  assert choice.metadata(cur)==metadata and plan.monetary_state(cur)==physical
  ready(cur,f,observed);before=work(cur,f);reader.call(cur,f,f['target'],observed)
  key=str(uuid.uuid4());p=parent.payload(f);result=parent.save(cur,f,p,key,observed)
  assert parent.save(cur,f,p,key,observed)==result and work(cur,f)==before
  assert plan.monetary_state(cur)==physical
  return dict(status='PASS',cold_read_and_save_refuse_without_compilation=True,
   whole_prepared_inputs_equal_original_compiler=True,same_source_request_reopens_and_deduplicates=True,
   preparation_does_not_save_choice=True,explicit_prepare_then_candidate_then_SAVE=True,exact_receipt_replay=True,no_money_stock_HPP_change=True)
 def access():
  install(cur);f=parent.prepare(cur,today,observed);ready(cur,f,observed)
  other=native.native.policy.master.role_actor(cur,'OWNER');epoch=reader.reader.epoch(cur,other)
  for verb in('request','get','step'):
   plan.refused(cur,lambda:call(cur,verb,f,observed,actor=other,epoch=epoch),'CP7_PRODUCT_ANALOG_RUN_UNAVAILABLE','42501')
   plan.refused(cur,lambda:call(cur,verb,f,observed,epoch='0'*64),'CP7_ANALYSIS_ACCESS_CHANGED','42501')
  plan.found_fg(cur,f['x'],'1');metadata=choice.metadata(cur);physical=plan.monetary_state(cur)
  reader.call(cur,f,f['target'],observed) # Same frozen analysis remains a historical read.
  plan.refused(cur,lambda:parent.save(cur,f),'CP7_ANALOG_CHOICE_SOURCE_CHANGED','40001')
  assert choice.metadata(cur)==metadata and plan.monetary_state(cur)==physical
  plan.b.api.admin(cur);cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(f['subject'],))
  for verb in('request','get','step'):assert plan.refusal(cur,lambda:call(cur,verb,f,observed))[0]=='42501'
  return dict(status='PASS',foreign_actor_wrong_epoch_revoked_access_refused=True,
   historical_preparation_never_authorizes_new_stale_SAVE=True,real_post_changes_source=True)
 def atomic_retention():
  s=install(cur);f=parent.prepare(cur,today,observed);ready(cur,f,observed);plan.b.api.admin(cur)
  cur.execute("create function pg_temp.choice_preparation_save_fault()returns trigger language plpgsql as $$begin raise exception 'CHOICE_PREPARATION_LAST_TABLE_FAULT';end$$")
  cur.execute('create trigger choice_preparation_save_fault before insert on cp7_product_analog_choice.commands for each row execute function pg_temp.choice_preparation_save_fault()')
  metadata=choice.metadata(cur);physical=plan.monetary_state(cur)
  plan.refused(cur,lambda:parent.save(cur,f),'CHOICE_PREPARATION_LAST_TABLE_FAULT')
  assert choice.metadata(cur)==metadata and plan.monetary_state(cur)==physical
  plan.b.api.admin(cur);cur.execute('drop trigger choice_preparation_save_fault on cp7_product_analog_choice.commands')
  key=str(uuid.uuid4());p=parent.payload(f);saved=parent.save(cur,f,p,key)
  plan.b.api.admin(cur);parent.bounded.retention.age(cur,f['done']['run_id'],timedelta(days=8))
  plan.refused(cur,lambda:call(cur,'get',f,observed),parent.bounded.retention.EXPIRED)
  assert parent.save(cur,f,p,key)==saved
  plan.b.api.admin(cur);assert cur.execute('select cp7_frozen_choice_preparation.purge_expired(100)').fetchone()[0]==1
  assert work(cur,f)['payload']is None and work(cur,f)['state']=='EXPIRED'
  held=_catalog_rows(cur)
  try:stage.rollback_preuse(cur,s['current'])
  except ValueError as error:assert str(error)=='CHOICE_PREPARATION_AFTER_USE_REQUIRES_COMPOSED_RESTORE'
  else:raise AssertionError('CHOICE_PREPARATION_USED_INVERSE_ALLOWED')
  assert _catalog_rows(cur)==held and parent.save(cur,f,p,key)==saved
  return dict(status='PASS',last_table_failure_atomic=True,expired_payload_cleared_identity_and_receipt_retained=True,used_inverse_refused=True)
 def cancellation():
  install(cur);f=parent.prepare(cur,today,observed);reader.purge(cur,f);call(cur,'request',f,observed);plan.b.api.admin(cur)
  cur.execute("create function pg_temp.choice_preparation_cancel()returns trigger language plpgsql as $$begin if new.state='READY'then raise exception using errcode='57014',message='INJECTED_CHOICE_PREPARATION_CANCEL';end if;return new;end$$")
  cur.execute('create trigger choice_preparation_cancel before update on cp7_frozen_choice_preparation.work for each row execute function pg_temp.choice_preparation_cancel()')
  first=call(cur,'step',f,observed);assert first['state']=='QUEUED'and first['unit_attempts']==1 and work(cur,f)['payload']is None
  plan.b.api.admin(cur);cur.execute('drop trigger choice_preparation_cancel on cp7_frozen_choice_preparation.work')
  recovered=call(cur,'step',f,observed);assert recovered['state']=='READY'and work(cur,f)['payload']['inputs']==f['expected']
  new=parent.fresh(cur,today,f,observed);reader.purge(cur,new);call(cur,'request',new,observed);plan.b.api.admin(cur)
  cur.execute('create trigger choice_preparation_cancel before update on cp7_frozen_choice_preparation.work for each row execute function pg_temp.choice_preparation_cancel()')
  for n in range(1,4):
   result=call(cur,'step',new,observed);assert result['unit_attempts']==n and result['units_done']==0
   assert result['state']==('QUEUED'if n<3 else'FAILED')and work(cur,new)['payload']is None
  assert call(cur,'step',new,observed)==result
  return dict(status='PASS',injected_SQL57014_not_claimed_as_wall_clock_timeout=True,
   cancellation_rolls_back_payload=True,same_work_safe_recovery=True,third_cancellation_terminal=True)
 def factory():
  install(cur);plan.fixture(cur,today);actor=native.native.policy.master.role_actor(cur,'OWNER')
  base=native.native.bounded.work.base.retained.formula.sales.fg.base;plan.b.api.admin(cur)
  size=native.geometry.fixture.seed(cur,base.BASE_PRODUCT,base.LOCATION,actor)
  roots=cur.execute("select identity_root_id::text,size_id::text from erp.products where sku in('OW12BF36-1','OW12BF36-2')order by size_id,sku").fetchall()
  root,sz=roots[0];source_root,source_sz=roots[1];assert sz==source_sz
  parent.consumer.profile(cur,root)
  f=parent.fresh(cur,today,dict(subject=actor,target=root+':'+sz,source=source_root+':'+sz),observed)
  assert len(f['expected']['inputs']['targets'])==3602
  physical=plan.monetary_state(cur);ready(cur,f,observed);reader.call(cur,f,f['target'],observed)
  first=parent.save(cur,f,observed=observed);assert first['revision']=='1'
  new=parent.fresh(cur,today,f,observed);reader.purge(cur,new)
  ready(cur,new,observed);reader.call(cur,new,new['target'],observed)
  second=parent.save(cur,new,parent.payload(new,'1'),observed=observed);assert second['revision']=='2'
  assert plan.monetary_state(cur)==physical
  return dict(size,status='PASS',all3602_prepared_targets_equal_original_compiler=True,
   actual_cached_and_after_K3_prepare_read_SAVE=True,phase_times_separate_no_total8s_gate=True,
   full_current_source_checks_per_SAVE=2,statement_limit_per_unit='8s',old_failures_reclassified=False,
   factory_SLA_claim=False,official_finance_included=False)
 def checked(fn):
  def run():
   observed.clear()
   try:return dict(fn(),observations=deepcopy(observed),production_go=False)
   except Exception as error:return dict(status='INCOMPLETE',error=str(error),traceback=traceback.format_exc(),observations=deepcopy(observed),production_go=False)
  return run
 return list(zip(IDS['native'],map(checked,(catalog,lifecycle,access,atomic_retention,cancellation,factory))))

def races(tools,today):return []
def http_cases(http,today):return []
