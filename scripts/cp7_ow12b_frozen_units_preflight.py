"""Static admission for the private prepared adapter; no Native qualification."""
import ast
import copy
import inspect
import json
import re
from pathlib import Path
import cp7_frozen_analysis_units_v2 as stage
import cp7_ow12b_frozen_units_cases as cases
import cp7_f05_analysis_probe as probe

stage.verify_sources();stage.capsule.verify_sources()
originals=stage.render.originals();replacements=stage.render.replacements()
assert len(originals)==len(replacements)==len(stage.FUNCTIONS)==8
assert len(cases.IDS['native'])==cases.EXPECTED==cases.DECLARED==4
assert cases.REQUIRED==dict(native=4)
count=0
for group in(originals,replacements,stage.private_definitions()):
 for sig,sql in group.items():
  node=re.match(r'create (?:or replace )?function ([a-z_0-9.]+)\((.*?)\)\s*returns',sql,re.S)
  assert node,sig
  types=[' '.join(p.strip().split()[1:])for p in node[2].split(',')if p.strip()]
  assert node[1]+'('+','.join(types)+')'==sig,sig
  count+=1
# The outer unit boundary only swaps the local-reference loader. Every
# PAGE early return, allocation/quantity expression and failure path remains.
assert stage._body(stage.render.run_hook()).replace('c:=cp7_frozen_analysis_units_v2.unit_reference(j,u);',"c:=j.reference||'{}'::jsonb;")==stage._body(stage.render.original_run())
request=stage.render.request_candidate()
old=stage.render.block(stage.render.BOUNDED.read_text(),'cp7_bounded_analysis_stage.request')
back=request.replace('cp7_frozen_analysis_units_v2.request(','cp7_bounded_analysis_stage.request(',1)
back=back.replace('cp7.bounded-analysis-request.v2','cp7.bounded-analysis-request.v1')
back=back.replace('cp7_frozen_analysis_units_v2.source(q,true)','cp7_bounded_analysis_stage.source(q,true)',1)
assert back==old
# No new call to the compiler in the request or any live-source read in cache.
cache=(stage.ROOT/'cache.sql').read_text()
assert cache.count('cp7_frozen_analysis_v2.prepare(')==1
assert 'cp7_history_bounded.compile('not in request and '.source('not in cache
assert 'update cp7_analysis_stage.jobs'not in cache and 'on conflict'not in cache.lower()
assert not re.search(r'create\s+(?:or replace\s+)?(?:table|function public\.)','\n'.join(p.read_text()for p in stage.ROOT.glob('*.sql')),re.I)
for p in (*stage.ROOT.glob('*.py'),Path(cases.__file__)):ast.parse(p.read_text())
declaration=json.loads((stage.ROOT.parents[1]/'docs/cp7/d17-14/ow12b/FROZEN_UNITS_NATIVE4_CONTRACT.json').read_text())
assert(declaration['contract'],declaration['required_case_ids'],declaration['required_case_counts'],declaration['expected_case_count'])==(cases.CONTRACT,cases.IDS,cases.REQUIRED,4)
assert declaration['frozen_units_source_sha256']==declaration['target_v2_source_sha256']==cases.sources()
assert declaration['public_rpcs']==list(cases.FUNCTIONS)and declaration['schedules']==cases.SCHEDULES
run=next(n for n in ast.parse(Path(probe.__file__).read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='run')
checks=[]
for node in run.body:
 if not isinstance(node,ast.Assert):break
 checks.append(node)
admission=copy.deepcopy(run);admission.body=checks+[ast.Return(ast.Constant(True))]
ns={};exec(compile(ast.fix_missing_locations(ast.Module(body=[admission],type_ignores=[])),'actual-route-admission','exec'),ns)
args=dict(wa_forward=True,ow14b_rules=True,ow13a_initial=True,ow10_supply=True,ow10_reorder=True,ow13c_checked=True,
 ow13c_history_inputs=True,ow13c_history_reference=True,ow13c_bounded_stage=True,
 ow11_model_history_runtime=True,ow11_model_scoped_evaluation=True,ow11_model_target_consumer_v2=True,ow12b_frozen_units=True)
assert ns['run'](**args);refused=0
for flag in set(args)-{'ow12b_frozen_units'}:
 try:ns['run'](**{**args,flag:False})
 except AssertionError as error:assert str(error)=='FROZEN_UNITS_REQUIRES_OWN_NATIVE4_BUDGET';refused+=1
 else:raise AssertionError('FROZEN_UNITS_MISSING_PARENT_ACCEPTED:'+flag)
for flag in set(inspect.signature(probe.run).parameters)-set(args):
 try:ns['run'](**{**args,flag:'A'if flag.endswith('_part')else True})
 except AssertionError as error:
  expected='STOCK_BINARY'if flag=='ow12b_stock_binary'else'FROZEN_CAPSULE'if flag=='ow12b_frozen_capsule'else'FROZEN_UNITS'
  assert str(error)==expected+'_REQUIRES_OWN_NATIVE4_BUDGET';refused+=1
 else:raise AssertionError('FROZEN_UNITS_MIXED_ROUTE_ACCEPTED:'+flag)
body=[]
for node in run.body:
 if isinstance(node,ast.Try):break
 body.append(node)
actual=copy.deepcopy(run);actual.name='actual_source_only';actual.body=body+[ast.Return(ast.Name('report',ast.Load()))]
ns=dict(vars(probe));exec(compile(ast.fix_missing_locations(ast.Module(body=[actual],type_ignores=[])),'actual-source-prefix','exec'),ns)
output=ns['actual_source_only'](**args)
assert output['label']=='CP7_OW12B_FROZEN_UNITS'and output['required_case_ids']==cases.IDS and output['required_case_counts']==cases.REQUIRED
assert output['predeclared_case_contract']==declaration and output['frozen_units_source_sha256']==cases.sources()
assert output['public_or_default_request_adopted']is False and output['private_request_and_units_qualified']is False
report=dict(status='PASS',exact_SQL_signatures_checked=count,private_functions=8,existing_replacements=8,
 source_pins=len(cases.sources()),Native4_provider_prepared=True,Native4_F05_route_wired=True,actual_F05_prefix_and_contract=True,missing_or_mixed_routes_refused=refused,
 actual_outer_unit_math_unchanged=True,actual_request_access_lock_replay_and_scope_guards_unchanged=True,
 no_live_source_in_unit_cache=True,jobs_reference_never_updated=True,
 actual_Native=False,actual_Auth_HTTP_credit=False,default_request_adopted=False,production_go=False)
print(json.dumps(report))
