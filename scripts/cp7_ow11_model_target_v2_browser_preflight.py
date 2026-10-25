"""Closed Browser2 declaration and actual leading F05 admission checks."""
import ast,json,re
from pathlib import Path
import cp7_f05_analysis_probe as probe
import cp7_ow11_model_target_v2_browser_cases as c
root=Path(__file__).resolve().parents[1]
d=json.loads((root/'docs/cp7/d17-14/ow11/MODEL_TARGET_V2_BROWSER_CONTRACT.json').read_text())
assert(d['contract'],d['required_case_ids'],d['required_case_counts'],d['expected_case_count'])==(c.CONTRACT,c.IDS,c.REQUIRED,c.EXPECTED)
assert c.EXPECTED==c.DECLARED==2 and c.REQUIRED==dict(browser=2)
assert d['target_v2_source_sha256']==c.sources()
assert d['public_rpcs']==list(c.FUNCTIONS)and d['schedules']==c.SCHEDULES
assert probe.bounded_group_names(c.REQUIRED)==('browser',)
script=(root/'scripts/cp7_ow11_model_target_v2_browser.mjs').read_text()
assert set(re.findall(r"\['(OW11_MODEL_TARGET_V2_BROWSER_[A-Z_]+)'",script))==set(c.IDS['browser'])
tree=ast.parse(Path(probe.__file__).read_text());run=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='run');checks=[]
for n in run.body:
 if not isinstance(n,ast.Assert):break
 checks.append(n)
assert checks
run.body=checks+[ast.Return(ast.Constant(True))];ns={};exec(compile(ast.fix_missing_locations(ast.Module(body=[run],type_ignores=[])),'actual-admission','exec'),ns)
args=dict(wa_forward=True,ow14b_rules=True,ow13a_initial=True,ow10_supply=True,ow10_reorder=True,ow13c_checked=True,ow13c_history_inputs=True,ow13c_history_reference=True,ow13c_bounded_stage=True,ow11_model_history_runtime=True,ow11_model_scoped_evaluation=True,ow11_model_target_consumer_v2=True,ow11_model_target_v2_browser=True)
assert ns['run'](**args)
for altered in ({'ow11_model_target_consumer_v2':False},{'ow11_model_target_v2_transport_part':'A'}):
 try:ns['run'](**{**args,**altered})
 except AssertionError as e:assert str(e)=='MODEL_TARGET_V2_BROWSER_REQUIRES_OWN_TWO_CASE_BUDGET'
 else:raise AssertionError('VERSIONED_BROWSER_MIXED_PARENT_ACCEPTED')
for flag in ('ow11_model_target_source_v2','ow11_model_target_consumer','ow11_model_selection','ow11_model_target_binding','ow11_model_scoped_transport','ow11_model_scoped_browser','ow11_model_history_transport'):
 try:ns['run'](**{**args,flag:True})
 except AssertionError:pass
 else:raise AssertionError('VERSIONED_BROWSER_MIXED_PREDECESSOR_ACCEPTED: '+flag)
print(json.dumps(dict(status='PASS',browser_cases=2,source_pins=len(c.sources()),actual_F05_admission=True,invalid_parent_and_mixed_route_refused=True,actual_browser=False,actual_Auth_HTTP_credit=False,production_go=False)))
