"""Explicit frozen confirmation qualification; no default adoption."""
from copy import deepcopy
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from time import monotonic
import json
import traceback
import uuid
import cp7_frozen_analysis_choice_v2 as stage
import cp7_ow12b_frozen_reader_cases as reader
from cp7_ow04_restore_bundle import _catalog_rows

native,plan,bounded,consumer=reader.native,reader.plan,reader.bounded,reader.consumer
choice=consumer.choice
RPC='erp_cp7_save_product_analog_choice_v2'
CONTRACT='cp7.ow12b.frozen-choice-native6.v2'
IDS=dict(native=['OW12B_FROZEN_CHOICE_V2_CATALOG22_EXACT_PREUSE',
 'OW12B_FROZEN_CHOICE_V2_CONFIRM_FRESH_CLEAR_REPLAY_CLOCKS',
 'OW12B_FROZEN_CHOICE_V2_REVIEW_SIZE_UNKNOWN_OLD_METHOD',
 'OW12B_FROZEN_CHOICE_V2_CURRENT_ACCESS_SOURCE_K2',
 'OW12B_FROZEN_CHOICE_V2_ATOMIC_LAST_TABLE_FAULT',
 'OW12B_FROZEN_CHOICE_V2_FACTORY1200X3_CACHED_K3_CONFIRM'])
REQUIRED=dict(native=6);EXPECTED=DECLARED=6
FUNCTIONS=(*reader.FUNCTIONS,RPC);SCHEDULES=reader.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None


def sources():
 root=Path(__file__).resolve().parent
 return {**reader.sources(),**{'cp7_frozen_analysis_choice_v2/'+k:v for k,v in stage.sources().items()},
  **{p.name:sha256(p.read_bytes()).hexdigest()for p in(Path(__file__),root/'cp7_ow12b_frozen_choice_local.mjs',
   root/'cp7_ow12b_frozen_choice_probe.py',root/'cp7_ow12b_frozen_choice_preflight.py',Path(choice.__file__))}}


def install(cur):
 reader.PARENT_CHECKER=PARENT_CHECKER
 for name in('INSTALL_STATES','REORDER_STATES','CHECKED_STATE','SCHEDULE_STATE','BOUNDED_STATE','REFERENCE_STATE','STAGE_STATE'):
  setattr(reader,name,globals()[name])
 parents=reader.install(cur)
 own=stage.install_delta(cur,lambda c:reader.stage.verify(c,parents['current']))
 return dict(parents=parents,current=own)


def fresh(cur,today,f,observed):
 return dict(f,**native.capture(cur,today,f['subject'],observed))


def prepare(cur,today,observed):
 x=plan.fixture(cur,today)
 imported=reader.reader.volume.import_batch(cur,today,11,reader.reader.volume.Phases())
 historical=reader.reader.historical.seed(cur,imported);target=imported[0]['target']
 source=next(p['target']for p in historical if p['target'].split(':')[1]==target.split(':')[1])
 different=next(p['target']for p in historical if p['target'].split(':')[1]!=target.split(':')[1])
 consumer.profile(cur,imported[0]['root'])
 native.native.policy.master.role_actor(cur,'OWNER')
 actor=native.native.policy.master.role_actor(cur,'OWNER')
 return fresh(cur,today,dict(x=x,target=target,source=source,different=different,imported=imported,subject=actor),observed)


def payload(f,revision='0'):
 return dict(consumer.payload(f,revision),contract_version='cp7.product-analog-choice-command.v2')


def save(cur,f,p=None,key=None,observed=None):
 started=monotonic()
 try:r=plan.staged.limited(cur,RPC,(json.dumps(p or payload(f)),key or str(uuid.uuid4())),f['subject'])
 except Exception as error:
  if observed is not None:observed['failed_save']=dict(millis=round((monotonic()-started)*1000,3),sqlstate=getattr(error,'sqlstate',None),error=str(error))
  raise
 elapsed=round((monotonic()-started)*1000,3);assert elapsed<8000,('FROZEN_CHOICE_OVER8S',elapsed)
 assert r['contract_version']=='cp7.product-analog-choice-outcome.v2'
 if observed is not None:observed.setdefault('write_millis',[]).append(elapsed)
 return r


def target(f):return next(x for x in f['expected']['inputs']['targets']if x['target_key']==f['target'])


def cases(cur,today):
 observed={}
 def catalog():
  before=_catalog_rows(cur);s=install(cur);v=stage.verify(cur,s['current'])
  assert(v['private_functions'],v['new_public_rpcs'],v['new_tables'],v['existing_replacements'])==(4,1,0,0)
  cur.execute('create view public.frozen_choice_inverse_guard as select public.'+RPC+'(null,null)value')
  held=_catalog_rows(cur)
  try:stage.rollback_preuse(cur,s['current'])
  except Exception as error:assert getattr(error,'sqlstate',None)=='2BP01',str(error)
  else:raise AssertionError('FROZEN_CHOICE_DEPENDENT_VIEW_DROPPED')
  assert _catalog_rows(cur)==held;cur.execute('drop view public.frozen_choice_inverse_guard')
  stage.rollback_preuse(cur,s['current']);reader.stage.rollback_preuse(cur,s['parents']['current'])
  native.unwind(cur,s['parents']['parents']);assert _catalog_rows(cur)==before
  return dict(status='PASS',private4_public1_tables0_replacements0=True,exact22_composed_inverse=True,dependent_view_refused_atomically=True)
 def lifecycle():
  s=install(cur);f=prepare(cur,today,observed);physical=plan.monetary_state(cur);p=payload(f);key=str(uuid.uuid4())
  assert target(f)['demand_estimate']['status']=='UNKNOWN'
  first=save(cur,f,p,key,observed);assert first['revision']=='1'and first['evidence']['available_total_pcs']=='0'
  assert first['forecast_applied']is False
  assert save(cur,f,p,key)==first
  new=fresh(cur,today,f,observed);r=target(new)
  assert r['demand_estimate']['basis']==consumer.BASIS and r['target']['target_pcs']=='0'
  assert consumer.staged_row(cur,new)['target']==r['target']
  assert bounded.work.get(cur,f['key'],f['subject'])['source_state']=='ARCHIVED_STALE'
  clear=dict(p,action='CLEAR',expected_revision='1',source_request=None,source_hash=None,source_key=None,scale_factor=None,reason='Explicit frozen test withdrawal')
  cleared=save(cur,new,clear,observed=observed);assert cleared['revision']=='2'and cleared['state']=='CLEARED'
  after=fresh(cur,today,new,observed);assert target(after)['demand_estimate']['status']=='UNKNOWN'and target(after)['target']['target_pcs']is None
  assert save(cur,f,p,key)==first
  plan.b.api.admin(cur)
  at=cur.execute('select cp7_product_analog_choice.source_at(%s,%s::timestamptz)',([f['target']],first['recorded_at'])).fetchone()[0][0]
  prior=cur.execute("select cp7_product_analog_choice.source_at(%s,%s::timestamptz-interval'1 microsecond')",([f['target']],first['recorded_at'])).fetchone()[0][0]
  assert at['choice_id']==first['choice_id']and prior['revision']=='0'
  snap=_catalog_rows(cur)
  try:stage.rollback_preuse(cur,s['current'])
  except ValueError as error:assert str(error)=='FROZEN_CHOICE_AFTER_USE_REQUIRES_COMPOSED_RESTORE'
  else:raise AssertionError('FROZEN_CHOICE_USED_INVERSE_ALLOWED')
  assert _catalog_rows(cur)==snap and plan.monetary_state(cur)==physical
  return dict(status='PASS',fresh_target_uses_reviewed_zero_same_kernel=True,CLEAR_restores_UNKNOWN_not_zero=True,
   exact_receipt_after_later_clear=True,recorded_microsecond_visible_only_after_recording=True,used_inverse_refused=True,no_money_stock_HPP_change=True,observations=deepcopy(observed))
 def validation():
  install(cur);f=prepare(cur,today,observed);p=payload(f);snap=choice.metadata(cur)
  unknown=next(x['target']for x in f['imported']if x['target']!=f['target']and x['target'].split(':')[1]==f['target'].split(':')[1])
  for change,message in[(dict(reviewed=False),'CP7_ANALOG_CHOICE_REVIEW'),(dict(reason=' '),'CP7_ANALOG_CHOICE_REVIEW'),
   (dict(scale_factor='0'),'CP7_ANALOG_CHOICE_SCALE'),(dict(source_key=f['target']),'CP7_ANALOG_CHOICE_SELF'),
   (dict(source_key=f['different']),'CP7_ANALOG_CHOICE_SIZE'),(dict(source_key=unknown),'CP7_ANALOG_CHOICE_INSUFFICIENT'),
   (dict(contract_version='cp7.product-analog-choice-command.v1'),'CP7_ANALOG_CHOICE_CONTRACT')]:
   plan.refused(cur,lambda:save(cur,f,dict(p,**change)),message)
  assert choice.metadata(cur)==snap
  key=str(uuid.uuid4());first=save(cur,f,p,key)
  plan.refused(cur,lambda:save(cur,f,dict(p,reason='changed'),key),'CP7_ANALOG_CHOICE_REQUEST_CHANGED')
  old=dict(p,contract_version='cp7.product-analog-choice-command.v1')
  plan.refused(cur,lambda:choice.save(cur,old,key,f['subject']),'CP7_ANALOG_CHOICE_REQUEST_CHANGED')
  assert save(cur,f,p,key)==first
  return dict(status='PASS',explicit_review_scale_reason_required=True,self_cross_size_UNKNOWN_refused=True,
   v1_payload_and_crossmethod_UUID_refused=True,exact_v2_replay=True)
 def access():
  install(cur);f=prepare(cur,today,observed);p=payload(f);key=str(uuid.uuid4());first=save(cur,f,p,key)
  other=native.native.policy.master.role_actor(cur,'OWNER');foreign=dict(f,subject=other)
  plan.refused(cur,lambda:save(cur,foreign,dict(p,expected_revision='1',access_epoch=reader.reader.epoch(cur,other))),'CP7_PRODUCT_ANALOG_RUN_UNAVAILABLE','42501')
  plan.found_fg(cur,f['x'],'1');snap=choice.metadata(cur)
  plan.refused(cur,lambda:save(cur,f,dict(p,expected_revision='1')),'CP7_ANALOG_CHOICE_SOURCE_CHANGED','40001')
  assert save(cur,f,p,key)==first
  plan.b.api.admin(cur);bounded.retention.age(cur,f['done']['run_id'],timedelta(days=8))
  plan.refused(cur,lambda:save(cur,f,dict(p,expected_revision='1')),bounded.retention.EXPIRED)
  assert save(cur,f,p,key)==first
  plan.b.api.admin(cur);cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(f['subject'],))
  assert plan.refusal(cur,lambda:save(cur,f,p,key))[0]=='42501'
  assert choice.metadata(cur)==snap
  return dict(status='PASS',foreign_stale_K2_refused=True,committed_receipt_retained_after_source_change_and_K2=True,current_revoked_actor_cannot_replay=True)
 def atomic():
  install(cur);f=prepare(cur,today,observed);plan.b.api.admin(cur)
  cur.execute("create function pg_temp.frozen_choice_fault()returns trigger language plpgsql as $$begin raise exception 'FROZEN_CHOICE_LAST_TABLE_FAULT';end;$$")
  cur.execute('create trigger frozen_choice_fault before insert on cp7_product_analog_choice.commands for each row execute function pg_temp.frozen_choice_fault()')
  snap=choice.metadata(cur);physical=plan.monetary_state(cur)
  plan.refused(cur,lambda:save(cur,f),'FROZEN_CHOICE_LAST_TABLE_FAULT')
  assert choice.metadata(cur)==snap and plan.monetary_state(cur)==physical
  return dict(status='PASS',last_table_failure_rolls_back_choice_and_command=True,no_orphan_or_business_write=True)
 def volume():
  install(cur);plan.fixture(cur,today);actor=native.native.policy.master.role_actor(cur,'OWNER')
  base=native.native.bounded.work.base.retained.formula.sales.fg.base;plan.b.api.admin(cur)
  size=native.geometry.fixture.seed(cur,base.BASE_PRODUCT,base.LOCATION,actor)
  roots=cur.execute("select identity_root_id::text,size_id::text from erp.products where sku in('OW12BF36-1','OW12BF36-2')order by size_id,sku").fetchall()
  root,sz=roots[0];source_root,source_sz=roots[1];assert sz==source_sz
  consumer.profile(cur,root)
  f=fresh(cur,today,dict(subject=actor,target=root+':'+sz,source=source_root+':'+sz),observed)
  assert len(f['expected']['inputs']['targets'])==3602
  physical=plan.monetary_state(cur);first=save(cur,f,observed=observed);assert first['revision']=='1'
  new=fresh(cur,today,f,observed);reader.purge(cur,new)
  second=save(cur,new,payload(new,'1'),observed=observed);assert second['revision']=='2'
  assert plan.monetary_state(cur)==physical
  return dict(size,status='PASS',actual_cached_and_after_K3_confirmations=True,
   full_source_checks_per_command=2,all3602_compiled_targets=True,factory_SLA_claim=False,observations=deepcopy(observed))
 def checked(fn):
  def run():
   observed.clear()
   try:return fn()
   except Exception as error:return dict(status='INCOMPLETE',error=str(error),traceback=traceback.format_exc(),observations=deepcopy(observed),production_go=False)
  return run
 return list(zip(IDS['native'],map(checked,(catalog,lifecycle,validation,access,atomic,volume))))


def races(tools,today):return []
def http_cases(http,today):return []
