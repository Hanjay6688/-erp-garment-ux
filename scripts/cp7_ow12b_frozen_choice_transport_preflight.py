"""Closed transport10 declaration and routing; never runtime qualification."""
import ast
import copy
import inspect
import json
from pathlib import Path
import cp7_f05_analysis_probe as probe
import cp7_ow12b_frozen_choice_transport_cases as cases

root=Path(__file__).resolve().parents[1]
d=json.loads((root/'docs/cp7/d17-14/ow12b/FROZEN_CHOICE_TRANSPORT10_CONTRACT.json').read_text())
assert (d['contract'],d['required_case_ids'],d['required_case_counts'],d['expected_case_count'])==(cases.CONTRACT,cases.IDS,cases.REQUIRED,10)
assert cases.EXPECTED==cases.DECLARED==10 and cases.REQUIRED==dict(native=1,races=6,http=3)
assert d['target_v2_source_sha256']==d['frozen_choice_transport_source_sha256']==cases.sources()
assert d['public_rpcs']==list(cases.FUNCTIONS)and d['schedules']==cases.SCHEDULES
cases.native.stage.verify_sources()
cases.native.reader.stage.verify_sources()
for p in [Path(cases.__file__),Path(__file__),root/'scripts/cp7_ow12b_frozen_choice_transport_probe.py']:ast.parse(p.read_text())
run=next(n for n in ast.parse(Path(probe.__file__).read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='run')
checks=[]
for node in run.body:
 if not isinstance(node,ast.Assert):break
 checks.append(node)
admission=copy.deepcopy(run);admission.body=checks+[ast.Return(ast.Constant(True))]
ns={};exec(compile(ast.fix_missing_locations(ast.Module(body=[admission],type_ignores=[])),'actual-work-transport-route','exec'),ns)
args=dict(wa_forward=True,ow14b_rules=True,ow13a_initial=True,ow10_supply=True,ow10_reorder=True,ow13c_checked=True,
 ow13c_history_inputs=True,ow13c_history_reference=True,ow13c_bounded_stage=True,
 ow11_model_history_runtime=True,ow11_model_scoped_evaluation=True,ow11_model_target_consumer_v2=True,ow12b_frozen_choice_transport=True)
assert ns['run'](**args)
refused=0
for flag in set(args)-{'ow12b_frozen_choice_transport'}:
 try:ns['run'](**{**args,flag:False})
 except AssertionError:refused+=1
 else:raise AssertionError('FROZEN_CHOICE_TRANSPORT_MISSING_PARENT_ACCEPTED:'+flag)
for flag in set(inspect.signature(probe.run).parameters)-set(args):
 try:ns['run'](**{**args,flag:'A'if flag.endswith('_part')else True})
 except AssertionError:refused+=1
 else:raise AssertionError('FROZEN_CHOICE_TRANSPORT_MIXED_ROUTE_ACCEPTED:'+flag)
body=[]
for node in run.body:
 if isinstance(node,ast.Try):break
 body.append(node)
actual=copy.deepcopy(run);actual.name='source_only';actual.body=body+[ast.Return(ast.Name('report',ast.Load()))]
ns=dict(vars(probe));exec(compile(ast.fix_missing_locations(ast.Module(body=[actual],type_ignores=[])),'actual-work-transport-prefix','exec'),ns)
r=ns['source_only'](**args)
assert r['label']=='CP7_OW12B_FROZEN_CHOICE_TRANSPORT'and r['predeclared_case_contract']==d
assert (r['required_case_ids'],r['required_case_counts'],r['expected_case_count'])==(cases.IDS,cases.REQUIRED,10)
assert r['frozen_choice_transport_source_sha256']==cases.sources()
assert not r['frozen_choice_transport_qualified']and not r['actual_Auth_HTTP_credit']and not r['actual_concurrency']
assert probe.bounded_group_names(cases.REQUIRED,transport=True)==('native','races','http')
for bad in [dict(native=1),dict(native=2,races=6,http=3),dict(native=1,races=5,http=3),dict(native=1,races=6,http=2),dict(native=1,races=6,http=3,browser=1)]:
 try:probe.bounded_group_names(bad,transport=True)
 except ValueError as e:assert str(e)=='BOUNDED_TRANSPORT_BUDGET_CHANGED'
 else:raise AssertionError('FROZEN_CHOICE_TRANSPORT_CHANGED_BUDGET_ACCEPTED')
# Check the actual post-install execution branch as well as declaration admission.
def group_test(group):
 matches=[]
 for node in ast.walk(run):
  if not isinstance(node,ast.If):continue
  for child in node.body:
   if not isinstance(child,ast.Assign):continue
   if any(isinstance(t,ast.Subscript)and isinstance(t.value,ast.Name)and t.value.id=='report'and isinstance(t.slice,ast.Constant)and t.slice.value==group for t in child.targets):matches.append(node.test)
 assert len(matches)==1,(group,len(matches))
 return compile(ast.Expression(matches[0]),'actual-runtime-group-gate','eval')
values={k:v.default for k,v in inspect.signature(probe.run).parameters.items()};values.update(args)
assert eval(group_test('native'),{},values)is True
assert eval(group_test('races'),{},values)is True
assert eval(group_test('http'),{},values)is True
assert eval(group_test('browser'),{},values)is False
print(json.dumps(dict(status='PASS_PREPARATION_ONLY',exact_case_budget=cases.REQUIRED,source_pins=len(cases.sources()),
 missing_or_mixed_routes_refused=refused,changed_group_budgets_refused=5,actual_F05_prefix_and_contract=True,actual_post_install_native_races_HTTP_execution_gate=True,
 SQL_unchanged=True,actual_Native=False,actual_Auth_HTTP_credit=False,actual_concurrency=False,default_adopted=False,production_go=False)))
