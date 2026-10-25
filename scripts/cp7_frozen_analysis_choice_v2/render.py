"""Explicit frozen confirmation from the actual admitted analog-consumer body."""
from pathlib import Path
from hashlib import sha256
import json
from cp7_production_stage import _body
from cp7_bounded_analysis_stage.source import once
from cp7_frozen_analysis_v2.render import block
from cp7_frozen_analysis_readers_v2 import render as reader

ROOT=Path(__file__).resolve().parent
SCHEMA='cp7_frozen_analysis_choice_v2'
PUBLIC='public.erp_cp7_save_product_analog_choice_v2'
APPLY='cp7_product_analog_choice.apply(jsonb,uuid)'
NORMALIZE='cp7_product_analog_consumer.normalize_confirmed_delta(jsonb,jsonb,jsonb)'
READ=reader.NEW+'('+reader.ARGS+')'
MATERIAL='cp7_product_analog_choice.material(jsonb,text,text)'


def originals():
 return{APPLY:block((ROOT.parent/'cp7_product_analog_consumer_stage/hooks.sql').read_text(),APPLY.split('(')[0]),
  NORMALIZE:block((ROOT.parent/'cp7_product_analog_consumer_stage/confirmation.sql').read_text(),NORMALIZE.split('(')[0]),
  READ:reader.reader(),MATERIAL:block((ROOT.parent/'cp7_product_analog_choice_stage/choice.sql').read_text(),MATERIAL.split('(')[0])}


def definitions():
 parent=originals();apply=parent[APPLY];normalize=parent[NORMALIZE];context=parent[READ];material=parent[MATERIAL]
 # The same validated immutable reference and advisory envelope stay local to
 # this command. K3 fallback compiles once; no cache, stored reference or old
 # reader is changed. Keep both live freshness checks in their original order.
 context=once(context,'create function '+reader.NEW+'(','create function '+SCHEMA+'.review_context(')
 context=once(context,'producer text;c jsonb;','producer text;c jsonb;reviewed jsonb;')
 context=once(context,' return jsonb_build_object(', ' reviewed:=jsonb_build_object(')
 context=once(context,'end $$;', " return jsonb_build_object('reviewed',reviewed,'reference',c);\nend $$;")
 material=once(material,'create function cp7_product_analog_choice.material(c jsonb,p_target text,p_source text)',
  'create function '+SCHEMA+'.material(c jsonb,p_target text,p_source text,p_envelope jsonb)')
 material=once(material,' envelope:=cp7_product_analog_stage.candidates(c,p_target,0,1);',' envelope:=p_envelope;')
 apply=once(apply,'create or replace function cp7_product_analog_choice.apply(','create function '+SCHEMA+'.apply(')
 apply=once(apply,'cp7.product-analog-choice-command.v1','cp7.product-analog-choice-command.v2')
 apply=once(apply,'cp7.product-analog-choice-outcome.v1','cp7.product-analog-choice-outcome.v2')
 apply=once(apply,'reviewed jsonb;material jsonb;','reviewed jsonb;review_context jsonb;material jsonb;')
 apply=once(apply,"reviewed:=cp7_product_analog_stage.read_candidates((p_payload->>'source_request')::uuid,target,0,1,p_payload->>'access_epoch');",
  "review_context:="+SCHEMA+".review_context((p_payload->>'source_request')::uuid,target,0,1,p_payload->>'access_epoch');\n  reviewed:=review_context->'reviewed';")
 apply=once(apply,'cp7_product_analog_choice.material(j.reference,target,',
  SCHEMA+".material(review_context->'reference',target,")
 apply=once(apply,"target,p_payload->>'source_key')||jsonb_build_object(","target,p_payload->>'source_key',reviewed->'result')||jsonb_build_object(")
 apply=once(apply,'cp7_product_analog_consumer.normalize_confirmed_delta(',SCHEMA+'.normalize_confirmed_delta(')
 normalize=once(normalize,'cp7_product_analog_consumer.normalize_confirmed_delta(',SCHEMA+'.normalize_confirmed_delta(')
 normalize=once(normalize,'cp7.product-analog-choice-outcome.v1','cp7.product-analog-choice-outcome.v2')
 return{SCHEMA+'.review_context('+reader.ARGS+')':context,SCHEMA+'.material(jsonb,text,text,jsonb)':material,
  SCHEMA+'.normalize_confirmed_delta(jsonb,jsonb,jsonb)':normalize,SCHEMA+'.apply(jsonb,uuid)':apply}


def render():
 s=f'create schema {SCHEMA} authorization cp7_capture;\nrevoke all on schema {SCHEMA} from public,anon,authenticated,service_role;\n'
 for sig,definition in definitions().items():
  s+='\n'+definition+f'\nalter function {sig}owner to cp7_capture;\nrevoke all on function {sig}from public,anon,authenticated,service_role;\n'
 s+=f'''
create function {PUBLIC}(p_payload jsonb,p_request uuid)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$
 select {SCHEMA}.apply(p_payload,p_request)
$$;
alter function {PUBLIC}(jsonb,uuid)owner to cp7_capture;
revoke all on function {PUBLIC}(jsonb,uuid)from public,anon,authenticated,service_role,postgres;
grant execute on function {PUBLIC}(jsonb,uuid)to authenticated;
'''
 return s


def manifest():
 return dict(contract='cp7.frozen-analysis-choice.prepared.v2',
  parent_bodies_sha256={sig:sha256(_body(sql).encode()).hexdigest()for sig,sql in originals().items()},
  new_bodies_sha256={sig:sha256(_body(sql).encode()).hexdigest()for sig,sql in definitions().items()},
  sql_sha256=sha256(render().encode()).hexdigest(),private_functions=4,new_public_rpcs=1,new_tables=0,existing_replacements=0,
  single_frozen_reference_per_confirmation=True,same_reviewed_candidate_envelope_reused=True,
  actual_admitted_consumer_postwrite_delta_guard_retained=True,shared_append_only_choice_and_command_tables=True,
  exact_v2_command_and_outcome=True,global_FG_envelope_and_current_access_guards_unchanged=True,
  actual_Native_qualified=False,actual_Auth_HTTP_credit=False,default_adopted=False,production_go=False)


if __name__=='__main__':
 (ROOT/'choice.prepared.sql').write_text(render())
 (ROOT/'PREPARATION.json').write_text(json.dumps(manifest(),indent=2)+'\n')
