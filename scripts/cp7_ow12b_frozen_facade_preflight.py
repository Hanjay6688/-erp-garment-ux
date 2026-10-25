"""Closed Native3/races3/HTTP2 admission; no runtime qualification."""
import ast
import copy
import inspect
import json
from pathlib import Path
import cp7_f05_analysis_probe as probe
import cp7_ow12b_frozen_facade_cases as cases

root=Path(__file__).resolve().parents[1]
d=json.loads((root/'docs/cp7/d17-14/ow12b/FROZEN_FACADE_TRANSPORT8_CONTRACT.json').read_text())
assert (d['contract'],d['required_case_ids'],d['required_case_counts'],d['expected_case_count'])==(cases.CONTRACT,cases.IDS,cases.REQUIRED,8)
assert cases.EXPECTED==cases.DECLARED==8 and cases.REQUIRED==dict(native=3,races=3,http=2)
assert d['target_v2_source_sha256']==d['frozen_facade_source_sha256']==cases.sources()
assert d['public_rpcs']==list(cases.FUNCTIONS)and d['schedules']==cases.SCHEDULES
cases.native.stage.verify_sources();cases.native.frozen.capsule.verify_sources()
sql=(cases.stage.ROOT/'facade.sql').read_text()
assert sql.count('create function public.')==1 and 'create or replace'not in sql.lower()
assert 'select cp7_frozen_analysis_units_v2.request(p_query,p_request)'in sql
assert "security definer set search_path=''set TimeZone='UTC'"in sql
assert 'grant execute on function public.'+cases.REQUEST+'(jsonb,uuid)to authenticated;'in sql
for p in [Path(cases.__file__),cases.stage.ROOT/'__init__.py',Path(__file__)]:ast.parse(p.read_text())
run=next(n for n in ast.parse(Path(probe.__file__).read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='run')
checks=[]
for node in run.body:
 if not isinstance(node,ast.Assert):break
 checks.append(node)
admission=copy.deepcopy(run);admission.body=checks+[ast.Return(ast.Constant(True))]
ns={};exec(compile(ast.fix_missing_locations(ast.Module(body=[admission],type_ignores=[])),'actual-facade-route-admission','exec'),ns)
args=dict(wa_forward=True,ow14b_rules=True,ow13a_initial=True,ow10_supply=True,ow10_reorder=True,ow13c_checked=True,
 ow13c_history_inputs=True,ow13c_history_reference=True,ow13c_bounded_stage=True,
 ow11_model_history_runtime=True,ow11_model_scoped_evaluation=True,ow11_model_target_consumer_v2=True,ow12b_frozen_facade=True)
assert ns['run'](**args)
refused=0
for flag in set(args)-{'ow12b_frozen_facade'}:
 try:ns['run'](**{**args,flag:False})
 except AssertionError as error:assert str(error)=='FROZEN_FACADE_REQUIRES_OWN_TRANSPORT8_BUDGET';refused+=1
 else:raise AssertionError('FROZEN_FACADE_MISSING_PARENT_ACCEPTED:'+flag)
for flag in set(inspect.signature(probe.run).parameters)-set(args):
 try:ns['run'](**{**args,flag:'A'if flag.endswith('_part')else True})
 except AssertionError as error:
  expected={'ow12b_stock_binary':'STOCK_BINARY_REQUIRES_OWN_NATIVE4_BUDGET','ow12b_frozen_capsule':'FROZEN_CAPSULE_REQUIRES_OWN_NATIVE4_BUDGET','ow12b_frozen_units':'FROZEN_UNITS_REQUIRES_OWN_NATIVE4_BUDGET'}.get(flag,'FROZEN_FACADE_REQUIRES_OWN_TRANSPORT8_BUDGET')
  assert str(error)==expected,(flag,str(error),expected);refused+=1
 else:raise AssertionError('FROZEN_FACADE_MIXED_ROUTE_ACCEPTED:'+flag)
body=[]
for node in run.body:
 if isinstance(node,ast.Try):break
 body.append(node)
actual=copy.deepcopy(run);actual.name='source_only';actual.body=body+[ast.Return(ast.Name('report',ast.Load()))]
ns=dict(vars(probe));exec(compile(ast.fix_missing_locations(ast.Module(body=[actual],type_ignores=[])),'actual-facade-prefix','exec'),ns)
r=ns['source_only'](**args)
assert r['label']=='CP7_OW12B_FROZEN_FACADE'and r['predeclared_case_contract']==d
assert (r['required_case_ids'],r['required_case_counts'],r['expected_case_count'])==(cases.IDS,cases.REQUIRED,8)
assert r['frozen_facade_source_sha256']==cases.sources()
assert r['public_facade_transport_qualified']is False and r['actual_Auth_HTTP_credit']is False and r['actual_concurrency']is False
assert probe.bounded_group_names(cases.REQUIRED,transport=True,frozen_facade=True)==('native','races','http')
for bad in [dict(native=3),dict(native=4,races=3,http=2),dict(native=3,races=2,http=2),dict(native=3,races=3,http=1),dict(native=3,races=3,http=2,browser=1)]:
 try:probe.bounded_group_names(bad,transport=True,frozen_facade=True)
 except ValueError as e:assert str(e)=='FROZEN_FACADE_TRANSPORT_BUDGET_CHANGED'
 else:raise AssertionError('FROZEN_FACADE_CHANGED_BUDGET_ACCEPTED')
print(json.dumps(dict(status='PASS',exact_case_budget=cases.REQUIRED,source_pins=len(cases.sources()),
 missing_or_mixed_routes_refused=refused,changed_group_budgets_refused=5,actual_F05_prefix_and_contract=True,
 actual_Native=False,actual_Auth_HTTP_credit=False,actual_concurrency=False,public_or_default_adopted=False,production_go=False)))
