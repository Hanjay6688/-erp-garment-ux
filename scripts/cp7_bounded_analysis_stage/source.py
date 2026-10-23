"""Source-factory portion of the versioned adapter; no installer or job yet."""
from pathlib import Path
from hashlib import sha256
import json
import re

ROOT = Path(__file__).resolve().parent
NATIVE = ROOT.parent/'cp7-src'/'planning'
SCHEMA = 'cp7_bounded_analysis_stage'
CURRENT_FP = ROOT.parent/'cp7_production_stage'/'sql'/'cp7_supply_native__fingerprint.sql'
REQUEST = 'cp7.bounded-analysis-request.v1'
REFERENCE = 'cp7.bounded-analysis-reference.v1'


def block(file, name):
    match = re.search(r'create function '+re.escape(name)+r'\(.*?\$\$;', (NATIVE/file).read_text(), re.S)
    if match is None:
        raise ValueError('BOUNDED_ANALYSIS_NATIVE_MISSING: '+name)
    return match[0]


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('BOUNDED_ANALYSIS_NATIVE_DERIVATION_CHANGED: '+old[:100])
    return text.replace(old,new)


def native_dependencies():
    out = {}
    for file,name,signature in [('supply-source.sql','cp7_supply_native.source_parts_within','(integer)'),
       ('schedule-scenario.sql','cp7_schedule_native.source_within','(integer)'),
       ('netting.sql','cp7_netting_native.source_within','(integer,integer)'),
       ('analysis.sql','cp7_analysis_native.source_within','(integer,integer)')]:
        raw = block(file,name)
        body = re.search(r'as \$\$(.*?)\$\$;',raw,re.S)[1]
        out[name+signature] = dict(body_sha256=sha256(body.encode()).hexdigest(),owner='cp7_capture')
    raw = CURRENT_FP.read_text()
    body = re.search(r'as \$\$(.*?)\$\$;',raw,re.S)[1]
    out['cp7_supply_native.fingerprint(jsonb)'] = dict(body_sha256=sha256(body.encode()).hexdigest(),owner='cp7_capture')
    return out


def render():
    pins = json.loads((ROOT/'SOURCE_MANIFEST.json').read_text())
    for file,digest in pins['native_files_sha256'].items():
        if sha256((NATIVE/file).read_bytes()).hexdigest() != digest:
            raise ValueError('BOUNDED_ANALYSIS_NATIVE_SOURCE_CHANGED: '+file)
    if pins['native_dependencies'] != native_dependencies():
        raise ValueError('BOUNDED_ANALYSIS_NATIVE_DEPENDENCIES_CHANGED')
    if sha256(CURRENT_FP.read_bytes()).hexdigest() != pins['current_supply_fingerprint_file_sha256']:
        raise ValueError('BOUNDED_ANALYSIS_CURRENT_SUPPLY_FP_CHANGED')
    native_fp = once(CURRENT_FP.read_text(), 'create or replace function cp7_supply_native.fingerprint(',
                     'create function '+SCHEMA+'.native_work_fingerprint(')
    supply = block('supply-source.sql','cp7_supply_native.source_parts_within')
    supply = once(supply,'cp7_supply_native.source_parts_within(',SCHEMA+'.source_parts(')
    supply = once(supply,'cp7_baseline_native.source_within(p_products)','cp7_reorder_inputs.capture_baseline(p_products)')
    schedule = block('schedule-scenario.sql','cp7_schedule_native.source_within')
    schedule = once(schedule,'cp7_schedule_native.source_within(',SCHEMA+'.schedule_source(')
    schedule = once(schedule,'cp7_supply_native.source_within(p_products)',"("+SCHEMA+".source_parts(p_products)->'c')")
    net = block('netting.sql','cp7_netting_native.source_within')
    net = once(net,'cp7_netting_native.source_within(',SCHEMA+'.netting_source(')
    net = once(net,'cp7_schedule_native.source_within(p_products)',SCHEMA+'.schedule_source(p_products)')
    analysis = block('analysis.sql','cp7_analysis_native.source_within')
    analysis = once(analysis,'cp7_analysis_native.source_within(',SCHEMA+'.analysis_source(')
    analysis = once(analysis,'cp7_netting_native.source_within(p_products,p_match)',SCHEMA+'.netting_source(p_products,p_match)')
    analysis = once(analysis,"'cp7_finance')", "'cp7_finance','"+SCHEMA+"')")
    producer = r"""
create function cp7_bounded_analysis_stage.producer_hash()returns text
language sql stable security invoker set search_path=''set TimeZone='UTC'as $$
 select encode(extensions.digest(convert_to(string_agg(p.oid::regprocedure::text||':'||pg_get_functiondef(p.oid),
  E'\n'order by p.oid::regprocedure::text),'UTF8'),'sha256'),'hex')
 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
 where n.nspname in('cp7_bounded_analysis_stage','cp7_history_bounded','cp7_history_reference')and p.prokind='f'
$$;
create function cp7_bounded_analysis_stage.work_fingerprint(c jsonb)returns text
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare stock jsonb:=c->'bounded_stock_reference';producer text:=c->>'bounded_producer_hash';
begin
 if c->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v1'
  or c->>'bounded_reference_contract'is distinct from'cp7.bounded-analysis-reference.v1'
  or producer is null or producer!~'^[0-9a-f]{64}$'
  or stock->>'contract_version'is distinct from'cp7.native-stock-row-digest.v1'
  or stock->>'scope'is distinct from'ALL_NATIVE_STOCK_FIELDS_AND_BOTH_VISIBILITY_CLOCKS'
  or stock->'captured_at'is distinct from c->'captured_at'
  or stock->>'rows_sha256'is null or stock->>'rows_sha256'!~'^[0-9a-f]{64}$'
  or stock->>'row_count'is null or stock->>'row_count'!~'^(0|[1-9][0-9]{0,19})$'
  or stock->'raw_rows_truncated'is distinct from'false'::jsonb
  or stock->'raw_native_capture_status_overridden'is distinct from'false'::jsonb then
  raise exception 'CP7_BOUNDED_ANALYSIS_REFERENCE_SHAPE';end if;
 -- No capture clock or selected demand query enters work-calendar identity.
 return encode(extensions.digest(convert_to(jsonb_build_object('contract','cp7.bounded-work-source.v1',
  'native',cp7_bounded_analysis_stage.native_work_fingerprint(c),'full_stock_rows',stock->'rows_sha256',
  'producer',producer)::text,'UTF8'),'sha256'),'hex');
end $$;
create function cp7_bounded_analysis_stage.source(p_query jsonb,p_with_inputs boolean)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare q jsonb;c jsonb;b jsonb:=cp7_analysis_stage.bounds();stock jsonb;summary jsonb;inputs jsonb;
 lo date;hi date;products integer;
begin
 if p_with_inputs is null then raise exception 'CP7_BOUNDED_ANALYSIS_CAPTURE_MODE';end if;
 q:=cp7_planning.history_query(p_query);
 c:=cp7_bounded_analysis_stage.analysis_source((b->>'job_targets')::integer,(b->>'job_matching_products')::integer)
   ||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED');
 products:=jsonb_array_length(c->'facts'->'products');
 if products>(b->>'job_targets')::integer then raise exception 'CP7_ANALYSIS_STAGED_TARGET_LIMIT';end if;
 lo:=cp7_demand.day(q->'from_date');hi:=cp7_demand.day(q->'through_date');
 if hi<lo or hi-lo>3660 or hi>=((c->>'captured_at')::timestamptz at time zone'Asia/Jakarta')::date
  or products::bigint*(hi-lo+1)>(b->>'job_history_cells')::bigint then raise exception 'CP7_BOUNDED_ANALYSIS_HISTORY_SCOPE';end if;
 stock:=cp7_history_reference.stock_digest(c->'facts'->'products',(c->>'captured_at')::timestamptz);
 if p_with_inputs then
  if c->'stock_raw_omitted'='true'::jsonb or jsonb_array_length(c->'facts'->'stock')=50001 then
   summary:=cp7_reorder_inputs.stock_summary(c->'facts'->'products',(c->>'captured_at')::timestamptz,q);
  end if;
  inputs:=cp7_history_bounded.compile(c,q,summary,(b->>'job_targets')::integer);
  if inputs->>'coverage'is distinct from'COMPLETE'or inputs->'raw_native_capture_status'is distinct from c->'status'
   or inputs->'captured_at'is distinct from c->'captured_at'or inputs->'query'is distinct from q then
   raise exception 'CP7_BOUNDED_ANALYSIS_INPUT_BINDING';end if;
 end if;
 return c||jsonb_build_object('bounded_request_contract','cp7.bounded-analysis-request.v1',
  'bounded_reference_contract','cp7.bounded-analysis-reference.v1','bounded_query',q,
  'bounded_producer_hash',cp7_bounded_analysis_stage.producer_hash(),'bounded_stock_reference',stock,
  'bounded_history_inputs',inputs);
end $$;
"""
    sql = 'create schema '+SCHEMA+' authorization cp7_capture;\nrevoke all on schema '+SCHEMA+' from public,anon,authenticated,service_role;\n'
    sql += '\n'.join([supply,schedule,net,analysis,native_fp,producer])+'\n'
    for sig in ('source_parts(integer)','schedule_source(integer)','netting_source(integer,integer)',
                'analysis_source(integer,integer)','native_work_fingerprint(jsonb)','work_fingerprint(jsonb)','producer_hash()','source(jsonb,boolean)'):
        sql += 'alter function '+SCHEMA+'.'+sig+' owner to cp7_capture;\n'
        sql += 'revoke all on function '+SCHEMA+'.'+sig+' from public,anon,authenticated,service_role;\n'
    return sql
