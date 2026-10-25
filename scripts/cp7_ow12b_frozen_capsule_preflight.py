"""Check the actual opt-in route and exact unchanged-compiler derivation."""
import ast
import copy
import inspect
import json
from pathlib import Path
import cp7_f05_analysis_probe as probe
import cp7_ow12b_frozen_capsule_cases as cases

root=Path(__file__).resolve().parents[1]
d=json.loads((root/'docs/cp7/d17-14/ow12b/FROZEN_CAPSULE_NATIVE4_CONTRACT.json').read_text())
assert(d['contract'],d['required_case_ids'],d['required_case_counts'],d['expected_case_count'])==(cases.CONTRACT,cases.IDS,cases.REQUIRED,4)
assert cases.EXPECTED==cases.DECLARED==4
assert d['frozen_capsule_source_sha256']==d['target_v2_source_sha256']==cases.sources()
assert d['public_rpcs']==list(cases.FUNCTIONS)and d['schedules']==cases.SCHEDULES
cases.capsule.verify_sources();cases.binary.verify_sources()
run=next(n for n in ast.parse(Path(probe.__file__).read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='run')
checks=[]
for node in run.body:
 if not isinstance(node,ast.Assert):break
 checks.append(node)
admission=copy.deepcopy(run);admission.body=checks+[ast.Return(ast.Constant(True))]
ns={};exec(compile(ast.fix_missing_locations(ast.Module(body=[admission],type_ignores=[])),'actual-admission','exec'),ns)
args=dict(wa_forward=True,ow14b_rules=True,ow13a_initial=True,ow10_supply=True,ow10_reorder=True,ow13c_checked=True,
 ow13c_history_inputs=True,ow13c_history_reference=True,ow13c_bounded_stage=True,
 ow11_model_history_runtime=True,ow11_model_scoped_evaluation=True,ow11_model_target_consumer_v2=True,ow12b_frozen_capsule=True)
assert ns['run'](**args)
refused=0
for flag in set(args)-{'ow12b_frozen_capsule'}:
 try:ns['run'](**{**args,flag:False})
 except AssertionError as error:assert str(error)=='FROZEN_CAPSULE_REQUIRES_OWN_NATIVE4_BUDGET';refused+=1
 else:raise AssertionError('FROZEN_CAPSULE_MISSING_PARENT_ACCEPTED:'+flag)
for flag in set(inspect.signature(probe.run).parameters)-set(args):
 try:ns['run'](**{**args,flag:'A'if flag.endswith('_part')else True})
 except AssertionError as error:
  assert str(error)==('STOCK_BINARY_REQUIRES_OWN_NATIVE4_BUDGET'if flag=='ow12b_stock_binary'else'FROZEN_CAPSULE_REQUIRES_OWN_NATIVE4_BUDGET');refused+=1
 else:raise AssertionError('FROZEN_CAPSULE_MIXED_ROUTE_ACCEPTED:'+flag)
body=[]
for node in run.body:
 if isinstance(node,ast.Try):break
 body.append(node)
actual=copy.deepcopy(run);actual.name='source_only';actual.body=body+[ast.Return(ast.Name('report',ast.Load()))]
ns=dict(vars(probe));exec(compile(ast.fix_missing_locations(ast.Module(body=[actual],type_ignores=[])),'actual-source-only','exec'),ns)
report=ns['source_only'](**args)
assert report['label']=='CP7_OW12B_FROZEN_CAPSULE'
assert report['expected_case_count']==4 and report['required_case_ids']==cases.IDS and report['required_case_counts']==cases.REQUIRED
assert report['predeclared_case_contract']==d and report['frozen_capsule_source_sha256']==cases.sources()
assert report['request_or_unit_integrated']is False
parent=cases.capsule.render.block(cases.capsule.render.PARENT.read_text(),'cp7_history_bounded.compile')
incomplete,complete=cases.capsule.render.admissions()
assert incomplete.replace('p_cap','p_products')in parent
assert len(cases.capsule.FUNCTIONS)==11
print(json.dumps(dict(status='PASS',native_cases_declared=4,source_pins=len(cases.sources()),
 actual_F05_prefix_and_contract=True,missing_or_mixed_routes_refused=refused,
 original_non_stock_admission_copied_exactly=True,compiler_unchanged=True,
 actual_Native=False,actual_Auth_HTTP_credit=False,request_or_unit_integrated=False,production_go=False)))
