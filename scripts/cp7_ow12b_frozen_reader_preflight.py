"""Closed Native4 declaration and actual route checks; no DB execution."""
import ast
import copy
import inspect
import json
from pathlib import Path
import cp7_f05_analysis_probe as probe
import cp7_ow12b_frozen_reader_cases as cases

stage=cases.stage;stage.verify_sources();cases.native.stage.verify_sources()
root=Path(__file__).resolve().parents[1]
d=json.loads((root/'docs/cp7/d17-14/ow12b/FROZEN_READER_NATIVE4_CONTRACT.json').read_text())
assert(d['contract'],d['required_case_ids'],d['required_case_counts'],d['expected_case_count'])==(cases.CONTRACT,cases.IDS,cases.REQUIRED,4)
assert cases.REQUIRED==dict(native=4)and cases.EXPECTED==cases.DECLARED==4
assert d['target_v2_source_sha256']==d['frozen_reader_source_sha256']==cases.sources()
assert d['public_rpcs']==list(cases.FUNCTIONS)and d['schedules']==cases.SCHEDULES
sql=(stage.ROOT/'reader.prepared.sql').read_text();reference=(stage.ROOT/'reference.sql').read_text()
assert len(stage.FUNCTIONS)==3 and sql.count('create function public.')==1 and 'create or replace'not in sql
assert "security definer set search_path=''set TimeZone='UTC'"in sql
assert 'grant execute on function public.'+cases.RPC+'(uuid,text,integer,integer,text)to authenticated;'in sql
assert reference.count('cp7_frozen_analysis_v2.prepare(')==1 and '.source('not in reference
assert all(word not in reference.lower()for word in('insert into','update cp7_','delete from','on conflict'))
# The new reader retains the parent's actor/epoch/retention/query/clock/source
# guards, unchanged candidates math and final access check. Undo only the
# explicit method/loader/provenance additions and require the exact old body.
s=stage.render.reader().replace('create function '+stage.render.NEW+'(','create or replace function '+stage.render.OLD+'(',1)
s=s.replace('sealed jsonb;candidates jsonb;producer text;c jsonb;','sealed jsonb;candidates jsonb;producer text;')
s=s.replace('cp7.bounded-analysis-request.v2','cp7.bounded-analysis-request.v1').replace('cp7.bounded-analysis-reference.v2','cp7.bounded-analysis-reference.v1')
s=s.replace(' c:=cp7_frozen_analysis_readers_v2.reference(j);\n candidates:=cp7_product_analog_stage.candidates(c,p_target,p_offset,p_limit);',' candidates:=cp7_product_analog_stage.candidates(j.reference,p_target,p_offset,p_limit);')
s=s.replace('producer:=cp7_frozen_analysis_units_v2.producer_hash();','producer:=cp7_bounded_analysis_stage.producer_hash();')
s=s.replace("'contract_version','cp7.product-analog-candidates-read.v3',\n  'bounded_request_contract',c->'bounded_request_contract','bounded_reference_contract',c->'bounded_reference_contract'","'contract_version','cp7.product-analog-candidates-read.v2'")
s=s.replace("jsonb_array_elements(c#>'{bounded_history_inputs,inputs,targets}')","jsonb_array_elements(j.reference#>'{bounded_history_inputs,inputs,targets}')")
assert s==stage.render.original()
for p in(*stage.ROOT.rglob('*.py'),Path(cases.__file__),Path(__file__)):ast.parse(p.read_text())
run=next(n for n in ast.parse(Path(probe.__file__).read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='run')
checks=[]
for node in run.body:
 if not isinstance(node,ast.Assert):break
 checks.append(node)
admission=copy.deepcopy(run);admission.body=checks+[ast.Return(ast.Constant(True))]
ns={};exec(compile(ast.fix_missing_locations(ast.Module(body=[admission],type_ignores=[])),'actual-reader-route-admission','exec'),ns)
args=dict(wa_forward=True,ow14b_rules=True,ow13a_initial=True,ow10_supply=True,ow10_reorder=True,ow13c_checked=True,
 ow13c_history_inputs=True,ow13c_history_reference=True,ow13c_bounded_stage=True,
 ow11_model_history_runtime=True,ow11_model_scoped_evaluation=True,ow11_model_target_consumer_v2=True,ow12b_frozen_reader=True)
assert ns['run'](**args);refused=0
for flag in set(args)-{'ow12b_frozen_reader'}:
 try:ns['run'](**{**args,flag:False})
 except AssertionError as error:assert str(error)=='FROZEN_READER_REQUIRES_OWN_NATIVE4_BUDGET';refused+=1
 else:raise AssertionError('FROZEN_READER_MISSING_PARENT_ACCEPTED:'+flag)
for flag in set(inspect.signature(probe.run).parameters)-set(args):
 try:ns['run'](**{**args,flag:'A'if flag.endswith('_part')else True})
 except AssertionError as error:
  expected={'ow12b_stock_binary':'STOCK_BINARY_REQUIRES_OWN_NATIVE4_BUDGET','ow12b_frozen_capsule':'FROZEN_CAPSULE_REQUIRES_OWN_NATIVE4_BUDGET','ow12b_frozen_units':'FROZEN_UNITS_REQUIRES_OWN_NATIVE4_BUDGET','ow12b_frozen_facade':'FROZEN_FACADE_REQUIRES_OWN_TRANSPORT8_BUDGET'}.get(flag,'FROZEN_READER_REQUIRES_OWN_NATIVE4_BUDGET')
  assert str(error)==expected,(flag,str(error),expected);refused+=1
 else:raise AssertionError('FROZEN_READER_MIXED_ROUTE_ACCEPTED:'+flag)
body=[]
for node in run.body:
 if isinstance(node,ast.Try):break
 body.append(node)
actual=copy.deepcopy(run);actual.name='source_only';actual.body=body+[ast.Return(ast.Name('report',ast.Load()))]
ns=dict(vars(probe));exec(compile(ast.fix_missing_locations(ast.Module(body=[actual],type_ignores=[])),'actual-reader-prefix','exec'),ns)
r=ns['source_only'](**args)
assert r['label']=='CP7_OW12B_FROZEN_READER'and r['predeclared_case_contract']==d
assert(r['required_case_ids'],r['required_case_counts'],r['expected_case_count'])==(cases.IDS,cases.REQUIRED,4)
assert r['frozen_reader_source_sha256']==cases.sources()
assert r['frozen_reader_native_qualified']is False and r['actual_Auth_HTTP_credit']is False
assert probe.bounded_group_names(cases.REQUIRED)==('native',)
print(json.dumps(dict(status='PASS',source_pins=len(cases.sources()),exact_case_budget=cases.REQUIRED,
 missing_or_mixed_routes_refused=refused,actual_F05_prefix_and_contract=True,
 actual_admitted_reader_guards_and_candidate_math_unchanged=True,
 actual_Native=False,actual_Auth_HTTP_credit=False,public_or_default_adopted=False,production_go=False)))
