"""Closed versioned transport partitions and actual F05 route admissions."""
import ast,json
from pathlib import Path
import cp7_f05_analysis_probe as probe
from cp7_ow11_model_target_transport_v2_parts import selected,verify_coverage,sources
root=Path(__file__).resolve().parents[1]
for part in ('A','B'):
 c=selected(part);d=json.loads((root/('docs/cp7/d17-14/ow11/MODEL_TARGET_V2_TRANSPORT_PART_'+part+'_CONTRACT.json')).read_text())
 assert d['contract']==c.CONTRACT and d['required_case_ids']==c.IDS and d['required_case_counts']==c.REQUIRED
 assert d['expected_case_count']==c.EXPECTED==c.DECLARED and d['target_v2_source_sha256']==c.sources()
 assert d['partition_source_sha256']==sources() and d['public_rpcs']==list(c.FUNCTIONS)and d['schedules']==c.SCHEDULES
 assert probe.bounded_group_names(c.REQUIRED,transport=True,model_target_v2_part=part)==tuple(c.REQUIRED)
 # Each part owns an exact budget. Missing, extra and inflated controls cannot
 # borrow a predecessor's route or receive partial qualification credit.
 altered=[{}, {**c.REQUIRED,'native':c.REQUIRED['native']+1},
          {**c.REQUIRED,'browser':1},
          {k:v for k,v in c.REQUIRED.items()if k!='races'}]
 for required in altered:
  try:probe.bounded_group_names(required,transport=True,model_target_v2_part=part)
  except ValueError as e:assert str(e)=='MODEL_TARGET_V2_TRANSPORT_PART_BUDGET_CHANGED'
  else:raise AssertionError('VERSIONED_TRANSPORT_ALTERED_BUDGET_ACCEPTED')
 for route in ({'transport':False}, {'model_target':True},
               {'model_target_part':'A'}, {'history_runtime':True},
               {'scoped_evaluation':True}):
  try:probe.bounded_group_names(c.REQUIRED,**{'transport':True,'model_target_v2_part':part,**route})
  except ValueError as e:assert str(e)=='MODEL_TARGET_V2_TRANSPORT_PART_BUDGET_CHANGED'
  else:raise AssertionError('VERSIONED_TRANSPORT_MIXED_ROUTE_ACCEPTED')
for args in ({'ow11_model_target_v2_transport_part':'A'}, {'ow11_model_target_consumer_v2':True,'ow11_model_target_v2_transport_part':'C'}):
 try:probe.run(**args)
 except AssertionError as e:assert str(e)=='MODEL_TARGET_V2_TRANSPORT_REQUIRES_OWN_PART'
 else:raise AssertionError('VERSIONED_TRANSPORT_INVALID_PART_ACCEPTED')
tree=ast.parse(Path(probe.__file__).read_text());run=next(x for x in tree.body if isinstance(x,ast.FunctionDef)and x.name=='run');checks=[]
for n in run.body:
 if not isinstance(n,ast.Assert):break
 checks.append(n)
assert checks
run.body=checks+[ast.Return(ast.Constant(True))];ns={};exec(compile(ast.fix_missing_locations(ast.Module(body=[run],type_ignores=[])),'actual-admission','exec'),ns)
for part in ('A','B'):
 assert ns['run'](wa_forward=True,ow14b_rules=True,ow13a_initial=True,ow10_supply=True,ow10_reorder=True,ow13c_checked=True,ow13c_history_inputs=True,ow13c_history_reference=True,ow13c_bounded_stage=True,ow11_model_history_runtime=True,ow11_model_scoped_evaluation=True,ow11_model_target_consumer_v2=True,ow11_model_target_v2_transport_part=part)
print(json.dumps(dict(status='PASS',**verify_coverage(),actual_F05_partition_admission=True,invalid_part_or_parent_refused=True,altered_budget_and_mixed_routes_refused=True,actual_Native=False,actual_Auth_HTTP_credit=False,production_go=False)))
