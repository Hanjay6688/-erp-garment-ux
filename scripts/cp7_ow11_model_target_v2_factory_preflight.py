"""Check the actual source-only F05 route and dimensional mutation controls."""
import ast,copy,json,subprocess
from collections import Counter
from pathlib import Path
import cp7_f05_analysis_probe as probe
import cp7_ow11_model_target_v2_factory_cases as cases

root=Path(__file__).resolve().parents[1]
contract_path=root/'docs/cp7/d17-14/ow11/MODEL_TARGET_V2_FACTORY_CONTRACT.json'
d=json.loads(contract_path.read_text())
assert(d['contract'],d['required_case_ids'],d['required_case_counts'],d['expected_case_count'])==(cases.CONTRACT,cases.IDS,cases.REQUIRED,cases.EXPECTED)
assert cases.EXPECTED==cases.DECLARED==2 and d['target_v2_source_sha256']==cases.sources()
assert d['public_rpcs']==list(cases.FUNCTIONS)and d['schedules']==cases.SCHEDULES
tree=ast.parse(Path(probe.__file__).read_text())
run=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='run')
admission=copy.deepcopy(run);checks=[]
for n in run.body:
 if not isinstance(n,ast.Assert):break
 checks.append(n)
assert checks
admission.body=checks+[ast.Return(ast.Constant(True))]
ns={};exec(compile(ast.fix_missing_locations(ast.Module(body=[admission],type_ignores=[])),'actual-admission','exec'),ns)
args=dict(wa_forward=True,ow14b_rules=True,ow13a_initial=True,ow10_supply=True,ow10_reorder=True,ow13c_checked=True,ow13c_history_inputs=True,ow13c_history_reference=True,ow13c_bounded_stage=True,ow11_model_history_runtime=True,ow11_model_scoped_evaluation=True,ow11_model_target_consumer_v2=True,ow11_model_target_v2_factory=True)
assert ns['run'](**args)
refused=0
for flag in set(args)-{'ow11_model_target_v2_factory'}:
 try:ns['run'](**{**args,flag:False})
 except AssertionError as error:assert str(error)=='MODEL_TARGET_V2_FACTORY_REQUIRES_OWN_NATIVE2_BUDGET';refused+=1
 else:raise AssertionError('FACTORY_MISSING_PARENT_ACCEPTED: '+flag)
for flag in('ow11_model_target_v2_scale','ow11_model_target_v2_browser','ow11_model_target_source_v2','ow11_model_target_binding','ow11_model_selection','ow11_model_scoped_dataset','ow11_model_history_scope','ow11_model_scoped_transport','ow11_model_scoped_browser','ow11_model_history_transport','ow11_model_target_consumer','ow11_model_target_browser','ow11_model_target_transport','ow11_model_policy','ow11_model_evaluation_v2','ow11_analog_choice','ow11_analog_consumer','ow11_analog_provenance','ow11_model_target_v2_transport_part'):
 try:ns['run'](**{**args,flag:'A'if flag=='ow11_model_target_v2_transport_part'else True})
 except AssertionError as error:assert str(error)=='MODEL_TARGET_V2_FACTORY_REQUIRES_OWN_NATIVE2_BUDGET';refused+=1
 else:raise AssertionError('FACTORY_MIXED_ROUTE_ACCEPTED: '+flag)
# Execute the whole actual prefix, including provider/declaration/report routing;
# stop before its first database try. Do not replace the provider or its source.
prefix=[]
for n in run.body:
 if isinstance(n,ast.Try):break
 prefix.append(n)
source=copy.deepcopy(run);source.name='actual_source_only';source.body=prefix+[ast.Return(ast.Name('report',ast.Load()))]
ns=dict(vars(probe));exec(compile(ast.fix_missing_locations(ast.Module(body=[source],type_ignores=[])),'actual-source-only','exec'),ns)
report=ns['actual_source_only'](**args)
assert report['label']=='CP7_OW11_MODEL_TARGET_V2_FACTORY'
assert report['expected_case_count']==2 and report['required_case_counts']==dict(native=2)
assert report['required_case_ids']==cases.IDS and report['predeclared_case_contract']==d
assert report['target_v2_source_sha256']==cases.sources()
# Preserve every existing assertion, including nested closures, from the last
# qualified one-size component. Additional dimensional checks cannot replace it.
baseline=subprocess.check_output(['git','show','7786d2db38c623f53f3f7c38d2e3ab6f65718d73:scripts/cp7_ow11_model_target_v2_scale_cases.py'],text=True)
asserts=lambda text:Counter(ast.dump(n,include_attributes=False)for n in ast.walk(ast.parse(text))if isinstance(n,ast.Assert))
before=asserts(baseline);after=asserts(Path(cases.common.__file__).read_text())
assert not(before-after),'FACTORY_DROPPED_OR_CHANGED_QUALIFIED_PARITY_ASSERTION'
# Independent geometry vectors expose lost/duplicate members, same-size copies,
# commercial splits, ambiguity and mixed commercial versions. No Native credit.
products=[]
for sku in range(1200):
 for size in range(3):
  products.append(dict(id=f'p{sku}:{size}',root_id=f'r{sku}:{size}',size_id=f's{size}',sku=f'OW12BF36-{sku}',commercial=[dict(sku_id=f'c{sku}',sku=f'OW12BF36-{sku}',version_id=f'v{sku}',revision='1')]))
assert len(cases.dimensional_signature(products))==3600
mutations=[]
v=copy.deepcopy(products);v.pop();mutations.append(v)
v=copy.deepcopy(products);v[1]['root_id']=v[0]['root_id'];mutations.append(v)
v=copy.deepcopy(products);v[1]['size_id']=v[0]['size_id'];mutations.append(v)
v=copy.deepcopy(products);v[1]['commercial'][0]['sku_id']='OTHER';mutations.append(v)
v=copy.deepcopy(products);v[1]['commercial'].append(copy.deepcopy(v[1]['commercial'][0]));mutations.append(v)
v=copy.deepcopy(products);v[1]['commercial'][0]['version_id']='OTHER';mutations.append(v)
for altered in mutations:
 try:cases.dimensional_signature(altered)
 except AssertionError:pass
 else:raise AssertionError('FACTORY_DIMENSIONAL_MUTATION_ACCEPTED')
print(json.dumps(dict(status='PASS',native_cases_declared=2,source_pins=len(cases.sources()),actual_F05_source_only_route=True,invalid_parent_or_mixed_routes_refused=refused,qualified_existing_assertions_preserved=sum(before.values()),dimensional_mutations_refused=len(mutations),database_executed=False,actual_Native=False,actual_Auth_HTTP_credit=False,production_go=False)))
