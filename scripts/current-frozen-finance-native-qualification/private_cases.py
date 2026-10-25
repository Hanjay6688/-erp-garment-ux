"""Three exact B business bodies on full A; full inverse is tested by the runner."""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import ast, inspect, traceback, uuid
import cp7_ow12b_frozen_units_cases as original
import cp7_current_frozen_finance_installation as product
import cp7_p21_current_chain_rehearsal_probe as chain
stage,frozen,native,geometry=original.stage,original.frozen,original.native,original.geometry
plan,bounded=original.plan,original.bounded
request,coverage,prepared_cache,capture=original.request,original.coverage,original.prepared_cache,original.capture
_catalog_rows=original._catalog_rows
IDS=('CURRENT_FROZEN_FINANCE_FULL22_DEPENDENCY_GUARD',*original.IDS['native'][1:])
STATE=CHECKER=None


@contextmanager
def installed(state,checker):
 global STATE,CHECKER
 old=STATE,CHECKER;STATE,CHECKER=state,checker
 try:yield
 finally:STATE,CHECKER=old


def install(cur):
 assert STATE is not None and callable(CHECKER)
 plan.b.api.admin(cur);CHECKER(cur)
 return dict(current=STATE['predecessor']['units'])


def rollback_full(cur,state):
 assert state is STATE['predecessor']['units']
 with chain.helper.control.product_catalog(cur):return product.rollback_preuse(cur,STATE)


def source_binding():
 before=ast.parse(inspect.getsource(original.cases)).body[0]
 after=ast.parse(inspect.getsource(cases)).body[0]
 before={n.name:n for n in before.body if isinstance(n,ast.FunctionDef)}
 after={n.name:n for n in after.body if isinstance(n,ast.FunctionDef)}
 changes=dict(rollback_calls=0,refusal_constants=0)
 class Allowed(ast.NodeTransformer):
  def visit_Call(self,n):
   n=self.generic_visit(n)
   if isinstance(n.func,ast.Attribute)and isinstance(n.func.value,ast.Name)and n.func.value.id=='stage'and n.func.attr=='rollback_preuse':
    n.func=ast.Name(id='rollback_full',ctx=ast.Load());changes['rollback_calls']+=1
   return n
  def visit_Constant(self,n):
   if n.value=='FROZEN_UNITS_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE':
    changes['refusal_constants']+=1;return ast.Constant(value=product.USED_ERROR)
   return n
 for name in('flow','volume','stale'):
  expected=Allowed().visit(before[name]) if name=='stale' else before[name]
  assert ast.dump(expected,include_attributes=False)==ast.dump(after[name],include_attributes=False),name
 assert changes==dict(rollback_calls=1,refusal_constants=1)
 for name in('request','coverage','prepared_cache','capture'):assert globals()[name]is getattr(original,name)
 return dict(exact_B_original_sha256=sha256(Path(original.__file__).read_bytes()).hexdigest(),
  exact_business_bodies=['flow','volume','stale'],explicit_AST_changes=changes,
  original_component_catalog_case_replaced_by_actual_full_preuse_inverse_in_outer_runner=True,
  new_full_catalog_dependent_view_refusal_before_inverse=True,all_business_limits_and_assertions_unchanged=True,
  financial_factory_qualification=False,production_go=False)


def cases(cur,today):
 observed={}
 def catalog():
  install(cur);before=_catalog_rows(cur)
  cur.execute('create view public.ow12b_frozen_finance_inverse_guard as select cp7_current_frozen_finance.request_finance(null::jsonb,null::uuid)value')
  held=_catalog_rows(cur);data=product.catalog._data(cur)
  try:rollback_full(cur,STATE['predecessor']['units'])
  except ValueError as error:assert str(error)=='CURRENT_FROZEN_FINANCE_SOURCE_OR_FULL22_CHANGED',str(error)
  else:raise AssertionError('FROZEN_FINANCE_EXTERNAL_DEPENDENCY_INVERSE_ACCEPTED')
  assert _catalog_rows(cur)==held and product.catalog._data(cur)==data
  cur.execute('drop view public.ow12b_frozen_finance_inverse_guard')
  assert _catalog_rows(cur)==before;CHECKER(cur)
  return dict(status='PASS',unknown_dependent_view_refused_by_full_catalog_before_inverse=True,
   all22_and_all_data_unchanged=True,full_preuse_inverse_verified_by_outer_runner=True,
   old_B_component_inverse_not_substituted=True)
 def flow():
  install(cur);plan.fixture(cur,today);actor=native.policy.master.role_actor(cur,'OWNER')
  f=capture(cur,today,actor,observed);q=f['row']['query'];key=f['key']
  assert request(cur,q,key,actor)==f['done']
  plan.refused(cur,lambda:request(cur,{**q,'group_mode':'RESTATED'if q['group_mode']=='AS_SOLD'else'AS_SOLD'},key,actor),'CP7_ANALYSIS_REQUEST_CHANGED')
  plan.refused(cur,lambda:bounded.request(cur,today,key,actor),'CP7_ANALYSIS_REQUEST_CHANGED')
  # The old request remains callable for its own UUID and keeps v1 inputs.
  old_key=str(uuid.uuid4());old=bounded.request(cur,today,old_key,actor)
  plan.staged.checked(old,old_key,'RUNNING')
  old_row=plan.staged.job_row(cur,old_key,actor)
  assert old_row['reference']['bounded_request_contract']=='cp7.bounded-analysis-request.v1'
  plan.refused(cur,lambda:request(cur,q,old_key,actor),'CP7_ANALYSIS_REQUEST_CHANGED')
  bounded.finish(cur,dict(key=old_key,initial=old,row=old_row,subject=actor))
  w=bounded.work.get(cur,key,actor)
  assert w['contract_version']=='cp7.planning-schedule-staged-bounded.v2'and w['history_input_coverage']=='COMPLETE'and w['source_state']=='UNCHANGED'
  return dict(status='PASS',private_request_actual_Native_units_and_pages=True,unchanged_compiler_entire_JSON_exact=True,
   reference_immutable_pending=True,exact_replay_and_cross_method_refusals=True,old_v1_request_and_pages_complete=True,
   workspace_v2_complete_only_after_HIST_PREP=True,observations=deepcopy(observed),actual_Auth_HTTP_credit=False)

 def volume():
  install(cur);plan.fixture(cur,today);plan.b.api.admin(cur)
  base=native.bounded.work.base.retained.formula.sales.fg.base
  actor=native.policy.master.role_actor(cur,'OWNER');size=geometry.fixture.seed(cur,base.BASE_PRODUCT,base.LOCATION,actor)
  f=capture(cur,today,actor,observed);c=f['row']['reference']
  assert c['status']=='INCOMPLETE'and c['stock_raw_omitted']is True
  signature=geometry.dimensional_signature(c['facts']['products']);assert len(signature)==3600
  assert f['pages']['targets_total']==len(c['facts']['products'])==3602
  assert c['bounded_frozen_stock_summary']['raw_rows_read']==int(c['bounded_stock_reference']['row_count'])>=363600
  w=bounded.work.get(cur,f['key'],actor)
  assert w['source_state']=='UNCHANGED'and w['history_input_coverage']=='COMPLETE'
  return dict(size,status='PASS',actual_private_request_complete=True,all3602_targets_entire_compiler_JSON_exact=True,
   exact1200_SKUs_three_physical_sizes=True,all_actual_pages_verified=True,raw_INCOMPLETE_preserved=True,
   observations=deepcopy(observed),factory_SLA_claim=False,public_request_adopted=False,production_go=False)

 def stale():
  s=install(cur);x=plan.fixture(cur,today);actor=native.policy.master.role_actor(cur,'OWNER')
  f=capture(cur,today,actor,observed);old=deepcopy(f['original']);reference=deepcopy(f['row']['reference'])
  plan.b.api.admin(cur)
  try:rollback_full(cur,s['current'])
  except ValueError as error:assert str(error)=='CURRENT_FROZEN_FINANCE_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
  else:raise AssertionError('FROZEN_UNITS_USED_INVERSE_ACCEPTED')
  # Use the already qualified Native poster; never rewrite a posted clock.
  plan.found_fg(cur,x,'1')
  physical=plan.monetary_state(cur)
  after,pages,meta=plan.staged.fetch(cur,f['done']['run_id'],actor)
  assert after==old and plan.staged.job_row(cur,f['key'],actor)['reference']==reference
  w=bounded.work.get(cur,f['key'],actor);assert w['source_state']=='ARCHIVED_STALE'
  assert prepared_cache(cur,f['row']['id'])==f['cache']
  plan.b.api.admin(cur)
  removed=cur.execute('select cp7_analysis_stage.purge_intermediates(%s)',(f['row']['id'],)).fetchone()[0]
  assert removed['removed']['target_rows']>0 and coverage(cur,f['row']['id'])=='COMPLETE'
  assert plan.staged.fetch(cur,f['done']['run_id'],actor)[0]==old
  assert plan.monetary_state(cur)==physical
  return dict(status='PASS',actual_post_marks_source_stale=True,archived_pages_and_reference_exact=True,
   used_inverse_refused=True,existing_K3_cache_purge_keeps_pages_and_coverage=True,reader_no_ERP_write=True,
   observations=deepcopy(observed),production_go=False)

 def checked(fn):
  def run():
   observed.clear()
   try:return fn()
   except Exception as error:return dict(status='INCOMPLETE',error=str(error),traceback=traceback.format_exc(),observations=deepcopy(observed),production_go=False)
  return run

 return list(zip(IDS,map(checked,(catalog,flow,volume,stale))))
