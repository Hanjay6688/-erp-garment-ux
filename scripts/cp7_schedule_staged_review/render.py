"""Derive the existing work validator/writer on a real retained staged handle.

The old Native functions and their limits remain byte-identical. No fixture
inserts a supply run or supplies a completeness flag/source hash to the engine.
"""
from hashlib import sha256
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parent
NATIVE = ROOT.parent/'cp7-src/planning/schedule.sql'
SCHEMA = 'cp7_schedule_staged_review'
CONTRACT = 'cp7.schedule-staged-review.v1'


def block(name):
    text = NATIVE.read_text()
    match = re.search(r'create function cp7_schedule_native\.'+re.escape(name)+r'\(.*?\$\$;', text, re.S)
    if match is None:
        raise ValueError('STAGED_SCHEDULE_NATIVE_BLOCK_MISSING: '+name)
    return match[0]


def body(text):
    return re.search(r'\bas\s+\$\$(.*?)\$\$;', text, re.S)[1]


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('STAGED_SCHEDULE_NATIVE_ANCHOR_CHANGED: '+old[:100])
    return text.replace(old, new, 1)


def dependencies():
    return {'cp7_schedule_native.'+name+signature: dict(body_sha256=sha256(body(block(name)).encode()).hexdigest(), owner='cp7_capture')
            for name, signature in [('workspace','(uuid)'),('save','(jsonb,uuid)'),
                                    ('validate','(jsonb,jsonb,jsonb)'),('source_at','(timestamp with time zone)'),
                                    ('route','(text)'),('position_model','(jsonb,jsonb)'),('access_now','(boolean)')]}


def render():
    pins = json.loads((ROOT/'MANIFEST.json').read_text())
    if pins['native_dependencies'] != dependencies():
        raise ValueError('STAGED_SCHEDULE_NATIVE_SOURCE_CHANGED')
    workspace = block('workspace')
    workspace = once(workspace, 'cp7_schedule_native.workspace(', SCHEMA+'.workspace(')
    workspace = once(workspace, 'r cp7_supply_native.runs%rowtype;', 'r record;')
    workspace = once(workspace,
        "a:=cp7_schedule_native.access_now(false);select *into r from cp7_supply_native.runs where id=p_run and actor=(a->>'actor')::uuid;",
        """a:=cp7_schedule_native.access_now(false);
 select j.run_id id,j.id job_id,j.state job_state,j.reference facts,j.captured_at,j.source_hash analysis_source_hash,
  cp7_supply_native.fingerprint(j.reference)dependency_hash,
  jsonb_build_object('wip',cp7_wip.normalize_production(j.reference->'production_sources'))result
 into r from cp7_analysis_stage.jobs j where j.request_id=p_run and j.actor=(a->>'actor')::uuid and j.state in('RUNNING','DONE');""")
    workspace = once(workspace, "message='CP7_SUPPLY_RUN_UNAVAILABLE'", "message='CP7_SCHEDULE_STAGED_RUN_UNAVAILABLE'")
    workspace = once(workspace, 'c:=cp7_supply_native.source();',
                     "if r.job_state='DONE'then perform cp7_analysis_stage.require_kept(r.job_id);end if;\n c:="+SCHEMA+'.current_source();')
    workspace = once(workspace, "'cp7.planning-schedule.v1'", "'cp7.planning-schedule-staged.v1'")
    workspace = once(workspace, "'source_state',case when hash=r.dependency_hash then", "'source_state',case when hash=r.dependency_hash and cp7_analysis_native.fingerprint(c)=r.analysis_source_hash then")
    workspace = once(workspace, "'captured_at',cp7_planning.utc(r.captured_at),", "'captured_at',cp7_planning.utc(r.captured_at),'staged_review_contract','"+CONTRACT+"','analysis_source_hash',r.analysis_source_hash,")
    workspace = once(workspace, "'source_run',p_run,", "'source_run',r.id,'source_request_id',p_run,'analysis_state',r.job_state,")
    workspace = once(workspace, "'position_requirements',requirements,", "'history_capture_state',r.facts->'status','production_capture_state',r.result#>'{wip,status}','position_requirements',requirements,")
    workspace = re.sub(r'\bp_run\b', 'p_source_request', workspace)

    save = block('save')
    save = once(save, 'cp7_schedule_native.save(', SCHEMA+'.save(')
    save = once(save, 'run cp7_supply_native.runs%rowtype;', 'run record;')
    save = once(save, "array['source_run','source_hash','expected_revision','config','reason']", "array['source_run','source_hash','expected_revision','config','reason','staged_review_contract']")
    save = once(save, " perform pg_advisory_xact_lock(hashtextextended('CP7:SCHEDULE:REQUEST:'", " if p_payload->>'staged_review_contract'is distinct from'"+CONTRACT+"'then raise exception 'CP7_SCHEDULE_STAGED_CONTRACT';end if;\n perform pg_advisory_xact_lock(hashtextextended('CP7:SCHEDULE:REQUEST:'")
    save = once(save,
        "select *into run from cp7_supply_native.runs where id=(p_payload->>'source_run')::uuid and actor=(a->>'actor')::uuid;",
        """select j.run_id id,j.id job_id,j.state job_state,j.source_hash analysis_source_hash,
  cp7_supply_native.fingerprint(j.reference)dependency_hash
 into run from cp7_analysis_stage.jobs j where j.run_id=(p_payload->>'source_run')::uuid
  and j.actor=(a->>'actor')::uuid and j.state in('RUNNING','DONE');""")
    save = once(save, "message='CP7_SUPPLY_RUN_UNAVAILABLE'", "message='CP7_SCHEDULE_STAGED_RUN_UNAVAILABLE'")
    save = once(save, 'c:=cp7_supply_native.source();',
                "if run.job_state='DONE'then perform cp7_analysis_stage.require_kept(run.job_id);end if;\n c:="+SCHEMA+'.current_source();')
    save = once(save, "if hash<>run.dependency_hash or hash<>p_payload->>'source_hash'then raise exception 'CP7_SCHEDULE_SOURCE_CHANGED';end if;",
                "if hash<>run.dependency_hash or hash<>p_payload->>'source_hash'\n  or cp7_analysis_native.fingerprint(c)<>run.analysis_source_hash then raise exception using errcode='40001',message='CP7_SCHEDULE_SOURCE_CHANGED';end if;")
    save = once(save, "'cp7.planning-schedule-outcome.v1'", "'cp7.planning-schedule-staged-outcome.v1'")
    save = once(save, "'quality','SELECTED_ASSUMPTIONS','production_go',false", "'quality','SELECTED_ASSUMPTIONS','staged_review_contract','"+CONTRACT+"','source_run',run.id,'production_go',false")
    # A last potential table/index wait cannot archive an obsolete work source.
    # Its own new schedule is deliberately outside the work-source fingerprint.
    save = once(save,
        " insert into cp7_schedule_native.commands(actor,request_id,payload,result)values((a->>'actor')::uuid,p_request,p_payload,outcome);",
        " insert into cp7_schedule_native.commands(actor,request_id,payload,result)values((a->>'actor')::uuid,p_request,p_payload,outcome);\n"
        " if cp7_supply_native.fingerprint("+SCHEMA+".current_source())<>hash then\n"
        "  raise exception using errcode='40001',message='CP7_SCHEDULE_SOURCE_CHANGED';\n end if;")

    source = """create schema cp7_schedule_staged_review authorization cp7_capture;
revoke all on schema cp7_schedule_staged_review from public,anon,authenticated,service_role;
create function cp7_schedule_staged_review.current_source()returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare b jsonb:=cp7_analysis_stage.bounds();c jsonb;
begin
 c:=cp7_analysis_native.source_within((b->>'job_targets')::integer,(b->>'job_matching_products')::integer)
  ||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED');
 if jsonb_typeof(c#>'{facts,products}')is distinct from'array'
  or jsonb_array_length(c#>'{facts,products}')>(b->>'job_targets')::integer then
  raise exception 'CP7_SCHEDULE_STAGED_PRODUCT_SCOPE_LIMIT';
 end if;
 return c;
end;
$$;
"""
    definitions = source+workspace+'\n'+save+'\n'
    for signature in ('current_source()', 'workspace(uuid)', 'save(jsonb,uuid)'):
        definitions += 'alter function '+SCHEMA+'.'+signature+' owner to cp7_capture;\n'
        definitions += 'revoke all on function '+SCHEMA+'.'+signature+' from public,anon,authenticated,service_role;\n'
    definitions += 'grant create on schema public to cp7_capture;\n'
    for public, signature, target, args in [
        ('erp_cp7_get_staged_production_schedule_v1','p_source_request uuid','workspace','p_source_request'),
        ('erp_cp7_save_staged_production_schedule_v1','p_payload jsonb,p_request uuid','save','p_payload,p_request')]:
        sql_signature = '(uuid)' if target=='workspace' else '(jsonb,uuid)'
        definitions += 'create function public.'+public+'('+signature+")returns jsonb\nlanguage sql volatile security definer set search_path=''set TimeZone='UTC'as $$select "+SCHEMA+'.'+target+'('+args+')$$;\n'
        definitions += 'alter function public.'+public+sql_signature+' owner to cp7_capture;\n'
        definitions += 'revoke all on function public.'+public+sql_signature+' from public,anon,authenticated,service_role;\n'
        definitions += 'grant execute on function public.'+public+sql_signature+' to authenticated;\n'
    definitions += 'revoke create on schema public from cp7_capture;\n'
    return definitions
