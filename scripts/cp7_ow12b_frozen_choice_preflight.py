"""Prepared choice adapter: exact admitted guards, no Native execution."""
import ast
import copy
import inspect
import json
from pglast import parse_sql
import cp7_frozen_analysis_choice_v2 as stage
import cp7_product_analog_consumer_stage.render as admitted

stage.verify_sources();old=stage.render.originals();new=stage.render.definitions();r=stage.render
assert stage._body(old[r.APPLY])==stage._body(admitted.replacements()[r.APPLY])
s=new[r.SCHEMA+'.apply(jsonb,uuid)']
changes=[('create function '+r.SCHEMA+'.apply(','create or replace function cp7_product_analog_choice.apply('),
 ('cp7.product-analog-choice-command.v2','cp7.product-analog-choice-command.v1'),
 ('cp7.product-analog-choice-outcome.v2','cp7.product-analog-choice-outcome.v1'),
 ("reviewed jsonb;review_context jsonb;material jsonb;","reviewed jsonb;material jsonb;"),
 ("review_context:="+r.SCHEMA+".review_context((p_payload->>'source_request')::uuid,target,0,1,p_payload->>'access_epoch');\n  reviewed:=review_context->'reviewed';","reviewed:=cp7_product_analog_stage.read_candidates((p_payload->>'source_request')::uuid,target,0,1,p_payload->>'access_epoch');"),
 (r.SCHEMA+".material(review_context->'reference',target,",'cp7_product_analog_choice.material(j.reference,target,'),
 ("target,p_payload->>'source_key',reviewed->'result')||jsonb_build_object(","target,p_payload->>'source_key')||jsonb_build_object("),
 (r.SCHEMA+'.normalize_confirmed_delta(','cp7_product_analog_consumer.normalize_confirmed_delta(')]
for a,b in changes:s=r.once(s,a,b)
assert s==old[r.APPLY]
s=new[r.SCHEMA+'.normalize_confirmed_delta(jsonb,jsonb,jsonb)']
s=r.once(s,r.SCHEMA+'.normalize_confirmed_delta(','cp7_product_analog_consumer.normalize_confirmed_delta(')
s=r.once(s,'cp7.product-analog-choice-outcome.v2','cp7.product-analog-choice-outcome.v1')
assert s==old[r.NORMALIZE]
s=new[r.SCHEMA+'.review_context('+r.reader.ARGS+')']
s=r.once(s,'create function '+r.SCHEMA+'.review_context(','create function '+r.reader.NEW+'(')
s=r.once(s,'producer text;c jsonb;reviewed jsonb;','producer text;c jsonb;')
s=r.once(s,' reviewed:=jsonb_build_object(',' return jsonb_build_object(')
s=r.once(s," return jsonb_build_object('reviewed',reviewed,'reference',c);\nend $$;",'end $$;')
assert s==old[r.READ]
s=new[r.SCHEMA+'.material(jsonb,text,text,jsonb)']
s=r.once(s,'create function '+r.SCHEMA+'.material(c jsonb,p_target text,p_source text,p_envelope jsonb)','create function cp7_product_analog_choice.material(c jsonb,p_target text,p_source text)')
s=r.once(s,' envelope:=p_envelope;',' envelope:=cp7_product_analog_stage.candidates(c,p_target,0,1);')
assert s==old[r.MATERIAL]
sql=r.render();assert len(parse_sql(sql))==18
assert sql.count('cp7_frozen_analysis_readers_v2.reference(j)')==1
assert sql.count('cp7_product_analog_stage.candidates(c,p_target,p_offset,p_limit)')==1
assert 'cp7_product_analog_stage.candidates(c,p_target,0,1)'not in sql
assert 'create table'not in sql.lower()and 'create or replace'not in sql.lower()
assert "hashtextextended('FG_HPP_SALES_V2620C',0)"in sql
assert "hashtextextended('CP7:ANALOG:REQUEST:'"in sql
assert sql.count('cp7_schedule_native.access_now(true)is distinct from a')==4
assert sql.count('cp7_bounded_analysis_stage.source_for(j.reference,j.query)')==2
for p in stage.ROOT.glob('*.py'):ast.parse(p.read_text())
import cp7_f05_analysis_probe as probe
import cp7_ow12b_frozen_choice_cases as cases
root=stage.ROOT.parents[1]
d=json.loads((root/'docs/cp7/d17-14/ow12b/FROZEN_CHOICE_NATIVE6_CONTRACT.json').read_text())
assert(d['contract'],d['required_case_ids'],d['required_case_counts'],d['expected_case_count'])==(cases.CONTRACT,cases.IDS,cases.REQUIRED,6)
assert cases.REQUIRED==dict(native=6)and cases.EXPECTED==cases.DECLARED==6
assert d['target_v2_source_sha256']==d['frozen_choice_source_sha256']==cases.sources()
assert d['public_rpcs']==list(cases.FUNCTIONS)and d['schedules']==cases.SCHEDULES
run=next(n for n in ast.parse(stage.ROOT.parent.joinpath('cp7_f05_analysis_probe.py').read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='run')
checks=[]
for node in run.body:
 if not isinstance(node,ast.Assert):break
 checks.append(node)
admission=copy.deepcopy(run);admission.body=checks+[ast.Return(ast.Constant(True))]
ns={};exec(compile(ast.fix_missing_locations(ast.Module(body=[admission],type_ignores=[])),'actual-choice-route','exec'),ns)
args=dict(wa_forward=True,ow14b_rules=True,ow13a_initial=True,ow10_supply=True,ow10_reorder=True,ow13c_checked=True,
 ow13c_history_inputs=True,ow13c_history_reference=True,ow13c_bounded_stage=True,
 ow11_model_history_runtime=True,ow11_model_scoped_evaluation=True,ow11_model_target_consumer_v2=True,ow12b_frozen_choice=True)
assert ns['run'](**args);refused=0
for flag in set(args)-{'ow12b_frozen_choice'}:
 try:ns['run'](**{**args,flag:False})
 except AssertionError as error:assert str(error)=='FROZEN_CHOICE_REQUIRES_OWN_NATIVE6_BUDGET';refused+=1
 else:raise AssertionError('FROZEN_CHOICE_MISSING_PARENT_ACCEPTED:'+flag)
for flag in set(inspect.signature(probe.run).parameters)-set(args):
 try:ns['run'](**{**args,flag:'A'if flag.endswith('_part')else True})
 except AssertionError as error:
  expected={'ow12b_stock_binary':'STOCK_BINARY_REQUIRES_OWN_NATIVE4_BUDGET','ow12b_frozen_capsule':'FROZEN_CAPSULE_REQUIRES_OWN_NATIVE4_BUDGET','ow12b_frozen_units':'FROZEN_UNITS_REQUIRES_OWN_NATIVE4_BUDGET','ow12b_frozen_facade':'FROZEN_FACADE_REQUIRES_OWN_TRANSPORT8_BUDGET','ow12b_frozen_reader':'FROZEN_READER_REQUIRES_OWN_NATIVE4_BUDGET'}.get(flag,'FROZEN_CHOICE_REQUIRES_OWN_NATIVE6_BUDGET')
  assert str(error)==expected,(flag,str(error),expected);refused+=1
 else:raise AssertionError('FROZEN_CHOICE_MIXED_ROUTE_ACCEPTED:'+flag)
body=[]
for node in run.body:
 if isinstance(node,ast.Try):break
 body.append(node)
actual=copy.deepcopy(run);actual.name='source_only';actual.body=body+[ast.Return(ast.Name('report',ast.Load()))]
ns=dict(vars(probe));exec(compile(ast.fix_missing_locations(ast.Module(body=[actual],type_ignores=[])),'actual-choice-prefix','exec'),ns)
result=ns['source_only'](**args)
assert result['label']=='CP7_OW12B_FROZEN_CHOICE'and result['predeclared_case_contract']==d
assert(result['required_case_ids'],result['required_case_counts'],result['expected_case_count'])==(cases.IDS,cases.REQUIRED,6)
assert result['frozen_choice_source_sha256']==cases.sources()
assert result['frozen_choice_native_qualified']is False and result['actual_Auth_HTTP_credit']is False
assert probe.bounded_group_names(cases.REQUIRED)==('native',)
ast.parse(stage.ROOT.parent.joinpath('cp7_ow12b_frozen_choice_cases.py').read_text())
print(json.dumps(dict(status='PASS_PREPARATION_ONLY',SQL_statements=18,private_functions=4,new_public_rpc=1,new_tables=0,
 source_pins=len(cases.sources()),exact_case_budget=cases.REQUIRED,missing_or_mixed_routes_refused=refused,actual_F05_prefix_and_contract=True,
 exact_admitted_consumer_parent_and_own_delta_guard=True,global_FG_envelope_shared_UUID_locks_current_access_and_freshness_unchanged=True,
 existing_choice_tables_and_material_math_unchanged=True,command_outcome_and_normalizer_explicit_v2=True,
 actual_Native=False,actual_Auth_HTTP_credit=False,default_or_UI_adopted=False,production_go=False)))
