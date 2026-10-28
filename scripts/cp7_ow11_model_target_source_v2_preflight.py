"""Closed candidate declaration and actual F05 admission, before database work."""
import ast
import hashlib
import json
from pathlib import Path
import cp7_ow11_model_target_source_v2_cases as cases
import cp7_f05_analysis_probe as probe

root = Path(__file__).resolve().parents[1]
path = root/'docs/cp7/d17-14/ow11/MODEL_TARGET_SOURCE_V2_NATIVE_CONTRACT.json'
d = json.loads(path.read_text())
assert d['contract'] == cases.CONTRACT
assert d['required_case_ids'] == cases.IDS and d['required_case_counts'] == cases.REQUIRED
assert d['expected_case_count'] == cases.EXPECTED == cases.DECLARED == 4
assert d['public_rpcs'] == list(cases.FUNCTIONS) and d['schedules'] == cases.SCHEDULES
assert d['source_v2_sha256'] == cases.sources()
assert probe.bounded_group_names(cases.REQUIRED) == ('native',)
for args in ({'ow11_model_target_source_v2':True},
             {'ow11_model_target_source_v2':True,'ow11_model_scoped_evaluation':True,'ow11_model_scoped_browser':True},
             {'ow11_model_target_source_v2':True,'ow11_model_scoped_evaluation':True,'ow11_model_scoped_transport':True}):
    try: probe.run(**args)
    except AssertionError as e: assert str(e) == 'MODEL_TARGET_SOURCE_V2_REQUIRES_OWN_NATIVE4_BUDGET'
    else: raise AssertionError('MODEL_TARGET_SOURCE_V2_INVALID_ROUTE_ALLOWED')
# Exercise the real leading admissions with the exact valid candidate flags,
# stopping before any installer/capture or connection is reachable.
tree = ast.parse(Path(probe.__file__).read_text())
run = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name == 'run')
assertions = []
for node in run.body:
    if not isinstance(node,ast.Assert): break
    assertions.append(node)
assert assertions
run.body = assertions+[ast.Return(value=ast.Constant(value=True))]
ns = {};exec(compile(ast.fix_missing_locations(ast.Module(body=[run],type_ignores=[])),'actual-F05-admission','exec'),ns)
assert ns['run'](wa_forward=True,ow14b_rules=True,ow13a_initial=True,ow10_supply=True,
 ow10_reorder=True,ow13c_checked=True,ow13c_history_inputs=True,ow13c_history_reference=True,
 ow13c_bounded_stage=True,ow11_model_history_runtime=True,ow11_model_scoped_evaluation=True,ow11_model_target_source_v2=True)
print(json.dumps(dict(status='PASS',exact_Native4_declaration=True,actual_F05_admission=True,
 invalid_parent_or_mixed_routes_refused=3,declaration_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
 actual_Native=False,actual_Auth_HTTP_credit=False,production_go=False)))
