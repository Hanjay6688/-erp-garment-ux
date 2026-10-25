"""Prepared Native4 for explicit frozen analog reads; no F05/default adoption."""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from time import monotonic
import json
import traceback
import uuid
import cp7_frozen_analysis_readers_v2 as stage
import cp7_ow12b_frozen_units_cases as native
import cp7_ow11_analog_consumer_cases as consumer
from cp7_ow04_restore_bundle import _catalog_rows

plan,bounded,reader=native.plan,native.bounded,consumer.reader
RPC='erp_cp7_read_product_analog_candidates_v2'
CONTRACT='cp7.ow12b.frozen-reader-native4.v2'
IDS=dict(native=['OW12B_FROZEN_READER_V2_CATALOG22_EXACT_PREUSE',
 'OW12B_FROZEN_READER_V2_PHYSICAL_SIZE_ZERO_UNKNOWN_K3_POST',
 'OW12B_FROZEN_READER_V2_CURRENT_ACCESS_OLD_METHOD_RETENTION',
 'OW12B_FROZEN_READER_V2_FACTORY1200X3_CACHED_K3_PARITY'])
REQUIRED=dict(native=4);EXPECTED=DECLARED=4
FUNCTIONS=(*native.FUNCTIONS,RPC);SCHEDULES=native.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None


def sources():
 root=Path(__file__).resolve().parent
 return {**native.sources(),**{'cp7_frozen_analysis_readers_v2/'+k:v for k,v in stage.sources().items()},
  **{p.name:sha256(p.read_bytes()).hexdigest()for p in(Path(__file__),root/'cp7_ow12b_frozen_reader_local.mjs',
    root/'cp7_ow12b_frozen_acl_local.mjs',root/'cp7_ow12b_frozen_acl_preflight.py',root/'cp7_ow12b_frozen_reader_probe.py',root/'cp7_ow12b_frozen_reader_preflight.py',
    Path(consumer.__file__),Path(reader.__file__),Path(reader.historical.__file__),Path(reader.volume.__file__))},
  '../src/nativeProductAnalog.ts':sha256((root.parent/'src/nativeProductAnalog.ts').read_bytes()).hexdigest()}


def install(cur):
 native.PARENT_CHECKER=PARENT_CHECKER
 for name in('INSTALL_STATES','REORDER_STATES','CHECKED_STATE','SCHEDULE_STATE','BOUNDED_STATE','REFERENCE_STATE','STAGE_STATE'):
  setattr(native,name,globals()[name])
 parents=native.install(cur)
 own=stage.install_delta(cur,lambda c:native.stage.verify(c,parents['current']))
 return dict(parents=parents,current=own)


def call(cur,f,target,observed,offset=0,actor=None,access=None):
 start=monotonic()
 try:
  result=plan.staged.limited(cur,RPC,(f['key'],target,offset,50,access or f['pages']['access_epoch']),actor or f['subject'])
 except Exception as error:
  observed['failed_read']=dict(millis=round((monotonic()-start)*1000,3),sqlstate=getattr(error,'sqlstate',None),error=str(error));raise
 elapsed=round((monotonic()-start)*1000,3)
 assert elapsed<8000,('FROZEN_READER_OVER8S',elapsed)
 observed.setdefault('read_millis',[]).append(elapsed)
 assert result['contract_version']=='cp7.product-analog-candidates-read.v3'
 assert result['bounded_request_contract']=='cp7.bounded-analysis-request.v2'
 assert result['bounded_reference_contract']=='cp7.bounded-analysis-reference.v2'
 assert result['reference']==f['pages']['reference']and result['query']==f['row']['query']
 assert result['request_id']==f['key']and result['run_id']==f['done']['run_id']
 assert result['identity_hash']==f['pages']['identity_hash']and result['actor_scope_id']==str(f['subject'])
 assert result['access_epoch']==f['pages']['access_epoch']
 assert result['producer_hash']==f['row']['reference']['bounded_producer_hash']
 assert result['source_state']=='CAPTURED_NOT_CHECKED'and result['captured_source_only']is True
 assert all(result[k]is False for k in('selected','reviewed','forecast_applied','production_go'))
 c=dict(f['row']['reference'],bounded_history_inputs=f['expected'],bounded_input_coverage='COMPLETE')
 expected=native.frozen.call(cur,'cp7_product_analog_stage.candidates',(json.dumps(c),target,offset,50))
 assert result['result']==expected
 assert result['target_demand']==next(x['demand_provenance']for x in f['expected']['inputs']['targets']if x['target_key']==target)
 return result


def purge(cur,f):
 plan.b.api.admin(cur)
 result=cur.execute('select cp7_analysis_stage.purge_intermediates(%s)',(f['row']['id'],)).fetchone()[0]
 assert result['removed']['target_rows']>0
 assert cur.execute("select count(*)from cp7_analysis_stage.target_rows where job_id=%s and kind='FROZEN_INPUTS_V2'",(f['row']['id'],)).fetchone()[0]==0


def cases(cur,today):
 observed={}
 def catalog():
  before=_catalog_rows(cur);s=install(cur);v=stage.verify(cur,s['current'])
  assert(v['private_functions'],v['new_public_rpcs'],v['new_tables'],v['existing_replacements'])==(2,1,0,0)
  cur.execute('create view public.frozen_reader_inverse_guard as select public.'+RPC+'(null,null,0,50,null)value')
  held=_catalog_rows(cur)
  try:stage.rollback_preuse(cur,s['current'])
  except Exception as error:assert getattr(error,'sqlstate',None)=='2BP01',str(error)
  else:raise AssertionError('FROZEN_READER_DEPENDENT_VIEW_DROPPED')
  assert _catalog_rows(cur)==held;cur.execute('drop view public.frozen_reader_inverse_guard')
  stage.rollback_preuse(cur,s['current']);native.unwind(cur,s['parents']);assert _catalog_rows(cur)==before
  return dict(status='PASS',private2_public1_tables0_replacements0=True,exact22_composed_inverse=True,dependent_view_refused_atomically=True)
 def history():
  install(cur);x=plan.fixture(cur,today)
  imported=reader.volume.import_batch(cur,today,11,reader.volume.Phases())
  historical=reader.historical.seed(cur,imported);target=imported[0]['target'];consumer.profile(cur,imported[0]['root'])
  actor=native.native.policy.master.role_actor(cur,'OWNER');f=native.capture(cur,today,actor,observed)
  physical=plan.monetary_state(cur);first=call(cur,f,target,observed)
  candidate=first['result']['candidates'];same=[p for p in historical if p['target'].split(':')[1]==target.split(':')[1]]
  assert len(candidate)==len(same)==1 and candidate[0]['target_key']==same[0]['target']
  assert candidate[0]['available_days']==1 and Decimal(candidate[0]['observed_available_daily_mean'])==0
  own=next(r for r in f['expected']['inputs']['history']if r['target_key']==target)
  assert own['available_days']==0 and own['unknown_days']==1 and own['available_sales_mean']is None
  purge(cur,f);assert call(cur,f,target,observed)==first
  assert plan.monetary_state(cur)==physical
  plan.found_fg(cur,x,'1');physical=plan.monetary_state(cur)
  assert bounded.work.get(cur,f['key'],actor)['source_state']=='ARCHIVED_STALE'
  assert call(cur,f,target,observed)==first
  assert plan.staged.job_row(cur,f['key'],actor)['reference']==f['row']['reference']
  assert plan.monetary_state(cur)==physical
  return dict(status='PASS',same_physical_size_available_zero=True,other_nine_sizes_excluded=True,own_UNKNOWN_not_zero=True,
   whole_candidate_and_provenance_exact=True,K3_then_real_post_preserves_frozen_read=True,observations=deepcopy(observed))
 def access():
  install(cur);plan.fixture(cur,today)
  other=native.native.policy.master.role_actor(cur,'OWNER');actor=native.native.policy.master.role_actor(cur,'OWNER')
  q=plan.staged.query(today);key=str(uuid.uuid4());initial=native.request(cur,q,key,actor)
  row=plan.staged.job_row(cur,key,actor);target=row['reference']['facts']['products'][0]
  target=target['root_id']+':'+target['size_id']
  f=dict(key=key,initial=initial,row=row,subject=actor,pages=dict(access_epoch=reader.epoch(cur,actor)))
  plan.refused(cur,lambda:call(cur,f,target,observed),'CP7_PRODUCT_ANALOG_RUN_UNAVAILABLE','42501')
  bounded.finish(cur,f);f['expected']=native.prepared_cache(cur,row['id'])['inputs'];call(cur,f,target,observed)
  plan.refused(cur,lambda:call(cur,f,target,observed,access='0'*64),'CP7_ANALYSIS_ACCESS_CHANGED','42501')
  foreign_epoch=reader.epoch(cur,other)
  plan.refused(cur,lambda:call(cur,f,target,observed,actor=other,access=foreign_epoch),'CP7_PRODUCT_ANALOG_RUN_UNAVAILABLE','42501')
  plan.refused(cur,lambda:plan.staged.limited(cur,reader.RPC,(key,target,0,50,f['pages']['access_epoch']),actor),'CP7_PRODUCT_ANALOG_BOUNDED_REQUIRED')
  plan.b.api.admin(cur);bounded.retention.age(cur,f['done']['run_id'],timedelta(days=8))
  plan.refused(cur,lambda:call(cur,f,target,observed),bounded.retention.EXPIRED)
  plan.b.api.admin(cur);cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(actor,))
  assert plan.refusal(cur,lambda:call(cur,f,target,observed))[0]=='42501'
  return dict(status='PASS',running_foreign_wrong_epoch_old_method_expired_revoked_refused=True,observations=deepcopy(observed))
 def volume():
  install(cur);plan.fixture(cur,today);actor=native.native.policy.master.role_actor(cur,'OWNER')
  base=native.native.bounded.work.base.retained.formula.sales.fg.base
  size=native.geometry.fixture.seed(cur,base.BASE_PRODUCT,base.LOCATION,actor)
  plan.b.api.admin(cur)
  roots=cur.execute("select identity_root_id from erp.products where sku='OW12BF36-1'order by size_id").fetchall()
  assert len(roots)==3
  for(root,)in roots:consumer.profile(cur,str(root))
  f=native.capture(cur,today,actor,observed);products=f['row']['reference']['facts']['products']
  assert len(products)==f['pages']['targets_total']==3602 and len(native.geometry.dimensional_signature(products))==3600
  targets={p['size_id']:p['root_id']+':'+p['size_id']for p in products if p['sku']=='OW12BF36-1'}
  assert len(targets)==3
  physical=plan.monetary_state(cur);before={k:call(cur,f,k,observed)for k in targets.values()}
  purge(cur,f)
  assert {k:call(cur,f,k,observed)for k in targets.values()}==before
  assert plan.staged.job_row(cur,f['key'],actor)['reference']==f['row']['reference']and plan.monetary_state(cur)==physical
  return dict(size,status='PASS',all3602_compiled_targets_exact=True,one_first_page_per_physical_size_cached_K3_exact=True,
   per_read_limit_millis=8000,factory_SLA_claim=False,observations=deepcopy(observed))
 def checked(fn):
  def run():
   observed.clear()
   try:return fn()
   except Exception as error:return dict(status='INCOMPLETE',error=str(error),traceback=traceback.format_exc(),observations=deepcopy(observed),production_go=False)
  return run
 return list(zip(IDS['native'],map(checked,(catalog,history,access,volume))))


def races(tools,today):return []
def http_cases(http,today):return []
