"""Explicit frozen analog reader, derived from the admitted v2 reader body."""
from pathlib import Path
from hashlib import sha256
import json
from cp7_production_stage import _body
from cp7_bounded_analysis_stage.source import once
from cp7_frozen_analysis_v2.render import block

ROOT=Path(__file__).resolve().parent
PARENT=ROOT.parent/'cp7_product_analog_provenance_stage/hooks.sql'
OLD='cp7_product_analog_stage.read_candidates'
NEW='cp7_frozen_analysis_readers_v2.read_candidates'
ARGS='uuid,text,integer,integer,text'
PUBLIC='public.erp_cp7_read_product_analog_candidates_v2'


def original():return block(PARENT.read_text(),OLD)


def reader():
 s=original()
 s=once(s,'create or replace function '+OLD+'(','create function '+NEW+'(')
 s=once(s,'sealed jsonb;candidates jsonb;producer text;','sealed jsonb;candidates jsonb;producer text;c jsonb;')
 s=s.replace('cp7.bounded-analysis-request.v1','cp7.bounded-analysis-request.v2').replace('cp7.bounded-analysis-reference.v1','cp7.bounded-analysis-reference.v2')
 s=once(s,' candidates:=cp7_product_analog_stage.candidates(j.reference,p_target,p_offset,p_limit);',
  ' c:=cp7_frozen_analysis_readers_v2.reference(j);\n candidates:=cp7_product_analog_stage.candidates(c,p_target,p_offset,p_limit);')
 s=once(s,'producer:=cp7_bounded_analysis_stage.producer_hash();','producer:=cp7_frozen_analysis_units_v2.producer_hash();')
 s=once(s,"'contract_version','cp7.product-analog-candidates-read.v2'", "'contract_version','cp7.product-analog-candidates-read.v3',\n  'bounded_request_contract',c->'bounded_request_contract','bounded_reference_contract',c->'bounded_reference_contract'")
 s=once(s,"jsonb_array_elements(j.reference#>'{bounded_history_inputs,inputs,targets}')", "jsonb_array_elements(c#>'{bounded_history_inputs,inputs,targets}')")
 return s


def render():
 return reader()+f'''
alter function {NEW}({ARGS})owner to cp7_capture;
revoke all on function {NEW}({ARGS})from public,anon,authenticated,service_role;
create function {PUBLIC}(p_request uuid,p_target text,p_offset integer,p_limit integer,p_access text)returns jsonb
language sql volatile security definer set search_path=''set TimeZone='UTC'as $$
 select {NEW}(p_request,p_target,p_offset,p_limit,p_access)
$$;
alter function {PUBLIC}({ARGS})owner to cp7_capture;
revoke all on function {PUBLIC}({ARGS})from public,anon,authenticated,service_role,postgres;
grant execute on function {PUBLIC}({ARGS})to authenticated;
'''


def manifest():
 return dict(contract='cp7.frozen-analysis-readers.prepared.v2',
  original_reader_body_sha256=sha256(_body(original()).encode()).hexdigest(),
  explicit_reader_body_sha256=sha256(_body(reader()).encode()).hexdigest(),
  SQL_sha256=sha256(render().encode()).hexdigest(),
  reference_SQL_sha256=sha256((ROOT/'reference.sql').read_bytes()).hexdigest(),
  private_functions=2,new_public_rpcs=1,new_tables=0,existing_replacements=0,
  unchanged_candidate_math=True,missing_K3_cache_recompiles_only_frozen_capsule=True,
  Native_qualified=False,Auth_qualified=False,default_adopted=False,production_go=False)


if __name__=='__main__':
 (ROOT/'reader.prepared.sql').write_text(render())
 (ROOT/'PREPARATION.json').write_text(json.dumps(manifest(),indent=2)+'\n')
