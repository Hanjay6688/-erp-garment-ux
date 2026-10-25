"""Closed Native6 frozen work admission; no database execution."""
import ast,copy,inspect,json
from pathlib import Path
import cp7_f05_analysis_probe as probe
import cp7_ow12b_frozen_work_cases as cases
root=Path(__file__).resolve().parents[1]
d=json.loads((root/'docs/cp7/d17-14/ow12b/FROZEN_WORK_NATIVE6_CONTRACT.json').read_text())
assert(d['contract'],d['required_case_ids'],d['required_case_counts'],d['expected_case_count'])==(cases.CONTRACT,cases.IDS,cases.REQUIRED,6)
assert cases.REQUIRED==dict(native=6)and cases.EXPECTED==cases.DECLARED==6
assert d['target_v2_source_sha256']==d['frozen_work_source_sha256']==cases.sources()
assert d['public_rpcs']==list(cases.FUNCTIONS)and d['schedules']==cases.SCHEDULES
run=next(n for n in ast.parse(root.joinpath('scripts','cp7_f05_analysis_probe.py').read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='run')
checks=[]
for node in run.body:
 if not isinstance(node,ast.Assert):break
 checks.append(node)
admission=copy.deepcopy(run);admission.body=checks+[ast.Return(ast.Constant(True))]
ns={};exec(compile(ast.fix_missing_locations(ast.Module(body=[admission],type_ignores=[])),'actual-choice-route','exec'),ns)
args=dict(wa_forward=True,ow14b_rules=True,ow13a_initial=True,ow10_supply=True,ow10_reorder=True,ow13c_checked=True,
 ow13c_history_inputs=True,ow13c_history_reference=True,ow13c_bounded_stage=True,
 ow11_model_history_runtime=True,ow11_model_scoped_evaluation=True,ow11_model_target_consumer_v2=True,ow12b_frozen_work=True)
assert ns['run'](**args);refused=0
for flag in set(args)-{'ow12b_frozen_work'}:
 try:ns['run'](**{**args,flag:False})
 except AssertionError as error:assert str(error)=='FROZEN_WORK_REQUIRES_OWN_NATIVE6_BUDGET';refused+=1
 else:raise AssertionError('FROZEN_WORK_MISSING_PARENT_ACCEPTED:'+flag)
for flag in set(inspect.signature(probe.run).parameters)-set(args):
 try:ns['run'](**{**args,flag:'A'if flag.endswith('_part')else True})
 except AssertionError as error:
  expected={'ow12b_stock_binary':'STOCK_BINARY_REQUIRES_OWN_NATIVE4_BUDGET','ow12b_frozen_capsule':'FROZEN_CAPSULE_REQUIRES_OWN_NATIVE4_BUDGET','ow12b_frozen_units':'FROZEN_UNITS_REQUIRES_OWN_NATIVE4_BUDGET','ow12b_frozen_facade':'FROZEN_FACADE_REQUIRES_OWN_TRANSPORT8_BUDGET','ow12b_frozen_reader':'FROZEN_READER_REQUIRES_OWN_NATIVE4_BUDGET','ow12b_frozen_choice':'FROZEN_CHOICE_REQUIRES_OWN_NATIVE6_BUDGET'}.get(flag,'FROZEN_WORK_REQUIRES_OWN_NATIVE6_BUDGET')
  assert str(error)==expected,(flag,str(error),expected);refused+=1
 else:raise AssertionError('FROZEN_WORK_MIXED_ROUTE_ACCEPTED:'+flag)
body=[]
for node in run.body:
 if isinstance(node,ast.Try):break
 body.append(node)
actual=copy.deepcopy(run);actual.name='source_only';actual.body=body+[ast.Return(ast.Name('report',ast.Load()))]
ns=dict(vars(probe));exec(compile(ast.fix_missing_locations(ast.Module(body=[actual],type_ignores=[])),'actual-choice-prefix','exec'),ns)
result=ns['source_only'](**args)
assert result['label']=='CP7_OW12B_FROZEN_WORK'and result['predeclared_case_contract']==d
assert(result['required_case_ids'],result['required_case_counts'],result['expected_case_count'])==(cases.IDS,cases.REQUIRED,6)
assert result['frozen_work_source_sha256']==cases.sources()
assert result['frozen_work_native_qualified']is False and result['actual_Auth_HTTP_credit']is False
assert probe.bounded_group_names(cases.REQUIRED)==('native',)
ast.parse(root.joinpath('scripts','cp7_ow12b_frozen_work_cases.py').read_text())
print(json.dumps(dict(status='PASS_PREPARATION_ONLY',source_pins=len(cases.sources()),exact_case_budget=cases.REQUIRED,missing_or_mixed_routes_refused=refused,actual_F05_prefix_and_contract=True,SQL_unchanged=True,existing_public_work_read_and_save=True,actual_Native=False,actual_Auth_HTTP_credit=False,default_or_UI_adopted=False,production_go=False)))
