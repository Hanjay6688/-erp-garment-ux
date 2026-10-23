"""Explicit, source-pinned adaptation of real Native jobs, never fabricated DONE.

The old bodies remain the legacy branch. Only immutable references created by
the new request route select complete bounded inputs and full raw-stock hashes.
"""
from pathlib import Path
from hashlib import sha256
import json
import re
from . import source

ROOT = Path(__file__).resolve().parent
SCHEMA = source.SCHEMA
REQUEST = source.REQUEST
REFERENCE = source.REFERENCE
PUBLIC = 'public.erp_cp7_request_bounded_staged_analysis_v1(jsonb,uuid)'
SUPPLY_FP = 'cp7_supply_native.fingerprint(jsonb)'
RUN = 'cp7_analysis_stage.run_scenario_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units,jsonb)'
SKELETON = 'cp7_analysis_stage.analysis_skeleton(jsonb,jsonb,uuid,jsonb,jsonb,jsonb,jsonb,jsonb,boolean,text)'
CHECK = 'cp7_analysis_stage.check_source(uuid)'
WORKSPACE = 'cp7_schedule_staged_review.workspace(uuid)'
SAVE = 'cp7_schedule_staged_review.save(jsonb,uuid)'
OLD_REQUEST = 'cp7_analysis_stage.request(jsonb,uuid)'
PRIVATE = {
    'source_parts(integer)': ('s', False), 'schedule_source(integer)': ('s', False),
    'netting_source(integer,integer)': ('s', False), 'analysis_source(integer,integer)': ('s', False),
    'native_work_fingerprint(jsonb)': ('i', False), 'work_fingerprint(jsonb)': ('i', False),
    'producer_hash()': ('s', False), 'source(jsonb,boolean)': ('s', False),
    'require_inputs(jsonb,jsonb)': ('i', False), 'history_prep(jsonb,jsonb,integer,bigint,integer)': ('i', False),
    'run_scenario_unit(cp7_analysis_stage.jobs,cp7_analysis_stage.units,jsonb)': ('v', False),
    'source_for(jsonb,jsonb)': ('s', False), 'request(jsonb,uuid)': ('v', False),
}


def originals():
    out = {SUPPLY_FP: source.CURRENT_FP.read_text()}
    for signature in (RUN, SKELETON, CHECK, OLD_REQUEST):
        out[signature] = source.block('analysis-stages.sql', signature.split('(')[0])
    text = (ROOT.parent/'cp7_schedule_staged_review'/'review.sql').read_text()
    for signature in (WORKSPACE, SAVE):
        out[signature] = re.search(r'create function '+re.escape(signature.split('(')[0])+r'\(.*?\$\$;', text, re.S)[0]
    return out


def replace_header(sql):
    return sql if sql.startswith('create or replace function ') else source.once(sql, 'create function ', 'create or replace function ')


def private_copy(sql, name):
    return re.sub(r'^create (?:or replace )?function [^(]+', 'create function '+SCHEMA+'.'+name, sql, count=1)


def render():
    old = originals()
    require = r"""
create function cp7_bounded_analysis_stage.require_inputs(c jsonb,q jsonb)returns jsonb
language plpgsql immutable security invoker set search_path=''set TimeZone='UTC'as $$
declare b jsonb:=c->'bounded_history_inputs';i jsonb:=b->'inputs';n integer:=jsonb_array_length(c->'facts'->'products');keys jsonb;
begin
 perform cp7_bounded_analysis_stage.work_fingerprint(c);
 if c->'bounded_query'is distinct from q or b->>'contract_version'is distinct from'cp7.bounded-history-inputs.v1'
  or b->>'coverage'is distinct from'COMPLETE' or b->'captured_at'is distinct from c->'captured_at'
  or b->'query'is distinct from q or b->'raw_native_capture_status'is distinct from c->'status'
  or b->'raw_native_status_overridden'is distinct from'false'::jsonb
  or i->>'contract_version'is distinct from'cp7.reorder-native-inputs.v1'
  or i->'captured_at'is distinct from c->'captured_at' or i->'query'is distinct from q
  or i->'products'is distinct from c->'facts'->'products'
  or i->>'source_hash'is null or i->>'source_hash'!~'^[0-9a-f]{64}$'
  or i->>'history_hash'is null or i->>'history_hash'!~'^[0-9a-f]{64}$'
  or jsonb_typeof(i->'history')is distinct from'array' or jsonb_typeof(i->'current_stock')is distinct from'array'
  or jsonb_typeof(i->'targets')is distinct from'array' then
  raise exception 'CP7_BOUNDED_ANALYSIS_INPUT_BINDING';end if;
 -- One actual Native result per product. Never accept missing or duplicate
 -- rows as zero, or a result for a different target/root/size.
 select coalesce(jsonb_object_agg((p->>'root_id')||':'||(p->>'size_id'),true),'{}')into keys
  from jsonb_array_elements(c->'facts'->'products')p;
 if exists(select 1 from jsonb_each(jsonb_build_object('history',i->'history','stock',i->'current_stock','targets',i->'targets'))a
  where jsonb_array_length(a.value)<>n or n<>(select count(distinct x->>'target_key')from jsonb_array_elements(a.value)x)
   or exists(select 1 from jsonb_array_elements(a.value)x where not(keys?(x->>'target_key'))))then
  raise exception 'CP7_BOUNDED_ANALYSIS_INPUT_TARGETS';end if;
 return i;
end $$;
create function cp7_bounded_analysis_stage.source_for(p_reference jsonb,p_query jsonb)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
begin
 if p_reference?'bounded_request_contract'then
  if p_reference->>'bounded_request_contract'is distinct from'cp7.bounded-analysis-request.v1'
   or p_reference->'bounded_query'is distinct from p_query then raise exception 'CP7_BOUNDED_ANALYSIS_REFERENCE_SHAPE';end if;
  begin
   return cp7_bounded_analysis_stage.source(p_query,false);
  exception when raise_exception then
   if sqlerrm in('CP7_ANALYSIS_STAGED_TARGET_LIMIT','CP7_BOUNDED_ANALYSIS_HISTORY_SCOPE')then
    raise exception using errcode='40001',message='CP7_SCHEDULE_SOURCE_CHANGED';end if;
   raise;
  end;
 end if;
 return cp7_schedule_staged_review.current_source();
end $$;
"""
    prep = private_copy((ROOT.parent/'cp7_production_stage'/'sql'/'cp7_analysis_stage__history_prep.sql').read_text(), 'history_prep')
    prep = source.once(prep, " if c->>'status'is distinct from 'COMPLETE'then raise exception 'CP7_PLANNING_CAPTURE_INCOMPLETE';end if;",
        ' perform cp7_bounded_analysis_stage.require_inputs(c,q);')
    prep = source.once(prep, " hash:=encode(extensions.digest(convert_to((c->'facts')::text,'UTF8'),'sha256'),'hex');",
        " hash:=c#>>'{bounded_history_inputs,inputs,history_hash}';")
    prep = source.once(prep, " avail_clean:=cp7_analysis_stage.availability_clean(c,q);", ' avail_clean:=true; -- Complete prepared SQL history is sliced below; no raw-prefix availability.')
    prep = source.once(prep, "'baseline_hash',encode(extensions.digest(convert_to(jsonb_build_object('target_kernel','target-unified-2','native',c->'facts','profiles',c->'profiles','production_policies',c->'production_policies'->'rows')::text,'UTF8'),'sha256'),'hex')",
        "'baseline_hash',c#>>'{bounded_history_inputs,inputs,source_hash}'")
    scenario = private_copy(old[RUN], 'run_scenario_unit')
    scenario = source.once(scenario,'keys jsonb;roots jsonb;', 'prepared jsonb;keys jsonb;roots jsonb;')
    scenario = source.once(scenario, 'g:=cp7_analysis_stage.history_prep(', 'g:=cp7_bounded_analysis_stage.history_prep(')
    lo = scenario.index(" if u.kind='HIST_ROWS'then")
    hi = scenario.index(" if u.kind='BASE_ROWS'then", lo)
    scenario = scenario[:lo]+r""" if u.kind='HIST_ROWS'then
  select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into prepared
   from jsonb_array_elements(c#>'{bounded_history_inputs,inputs,history}')x;
  select coalesce(jsonb_agg(prepared->(g->'targets'->(k.i::integer-1)->>'key')order by k.pos),'[]')into rows
   from jsonb_array_elements_text(val->'key_order')with ordinality k(i,pos)
   where k.pos between u.lo and u.hi;
  if jsonb_array_length(rows)<>u.hi-u.lo+1 then raise exception 'CP7_BOUNDED_ANALYSIS_HISTORY_SLICE';end if;
  insert into cp7_analysis_stage.target_rows select j.id,'HIST',u.lo+x.o-1,x.v->>'target_key',x.v
   from jsonb_array_elements(rows)with ordinality x(v,o);
  days:=(g->>'through')::date-(g->>'from')::date+1;
  return jsonb_build_object('rows',jsonb_array_length(rows),'availability_rows',jsonb_array_length(rows)*days);
 end if;
 if u.kind='HIST_STOCK'then
  select coalesce(jsonb_object_agg(x->>'target_key',x),'{}')into prepared
   from jsonb_array_elements(c#>'{bounded_history_inputs,inputs,current_stock}')x;
  select coalesce(jsonb_agg(prepared->((p.product->>'root_id')||':'||(p.product->>'size_id'))order by p.o),'[]')into rows
   from jsonb_array_elements(g->'stock_order')with ordinality p(product,o)
   where p.o between u.lo and u.hi;
  if jsonb_array_length(rows)<>greatest(0,u.hi-u.lo+1)then raise exception 'CP7_BOUNDED_ANALYSIS_STOCK_SLICE';end if;
  insert into cp7_analysis_stage.target_rows select j.id,'STOCK',u.lo+x.o-1,x.v->>'target_key',x.v
   from jsonb_array_elements(rows)with ordinality x(v,o);
  return jsonb_build_object('rows',jsonb_array_length(rows));
 end if;
"""+scenario[hi:]
    replacements = {}
    replacements[SUPPLY_FP] = source.once(old[SUPPLY_FP], ' select encode(',
        " select case when c->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'\n"
        ' then cp7_bounded_analysis_stage.work_fingerprint(c) else encode(')
    replacements[SUPPLY_FP] = source.once(replacements[SUPPLY_FP], "'sha256'),'hex')\n$$;", "'sha256'),'hex') end\n$$;")
    replacements[RUN] = source.once(old[RUN], "begin\n if u.kind='HIST_PREP'then", "begin\n if c->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'then\n"
        '  return cp7_bounded_analysis_stage.run_scenario_unit(j,u,c);end if;\n'+" if u.kind='HIST_PREP'then")
    replacements[SKELETON] = source.once(old[SKELETON], "complete boolean:=c->>'status'='COMPLETE'and wip->>'status'='COMPLETE';",
        "complete boolean:=(c->>'status'='COMPLETE'or(case when c->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'\n"
        ' then cp7_bounded_analysis_stage.require_inputs(c,q)is not null else false end))and '+"wip->>'status'='COMPLETE';")
    replacements[SKELETON] = source.once(replacements[SKELETON], "begin\n if scenario_revision", "begin\n if c->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'and c->>'status'='INCOMPLETE'then\n"
        "  warnings0:=warnings0||'\"RAW_NATIVE_CAPTURE_INCOMPLETE_COMPLETE_SQL_HISTORY_INPUTS\"'::jsonb;end if;\n if scenario_revision")
    check = source.once(old[CHECK], 'declare a jsonb;hash text;', 'declare r record;a jsonb;hash text;')
    check = source.once(check, 'select j.source_hash into hash', 'select j.source_hash,j.reference,j.query into r')
    check = source.once(check, ' if hash is null then', ' hash:=r.source_hash;\n if hash is null then')
    capture = "c:=cp7_analysis_native.source_within((b->>'job_targets')::integer,(b->>'job_matching_products')::integer)\n  ||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED');"
    check = source.once(check, capture, "begin\n  if r.reference?'bounded_request_contract'then c:=cp7_bounded_analysis_stage.source_for(r.reference,r.query);\n  else "+capture+"end if;\n exception when serialization_failure then\n"
        "  if cp7_schedule_native.access_now(false)is distinct from a then raise exception using errcode='42501',message='CP7_ANALYSIS_ACCESS_CHANGED';end if;\n"
        "  return jsonb_build_object('source_state','ARCHIVED_STALE','checked_at',cp7_planning.utc(statement_timestamp()));\n end;")
    replacements[CHECK] = check
    replacements[WORKSPACE] = source.once(old[WORKSPACE], 'j.state job_state,j.reference facts,', 'j.state job_state,j.query,j.reference facts,')
    replacements[WORKSPACE] = source.once(replacements[WORKSPACE], 'c:=cp7_schedule_staged_review.current_source();',
        'c:=cp7_bounded_analysis_stage.source_for(r.facts,r.query);')
    replacements[WORKSPACE] = source.once(replacements[WORKSPACE], ' return outcome;',
        " if r.facts->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'then\n"
        "  outcome:=outcome||jsonb_build_object('contract_version','cp7.planning-schedule-staged-bounded.v1',\n"
        "   'bounded_request_contract',r.facts->'bounded_request_contract','bounded_reference_contract',r.facts->'bounded_reference_contract',\n"
        "   'history_input_coverage',r.facts#>'{bounded_history_inputs,coverage}');end if;\n return outcome;")
    replacements[SAVE] = source.once(old[SAVE], 'j.state job_state,j.source_hash analysis_source_hash,', 'j.state job_state,j.reference facts,j.query,j.source_hash analysis_source_hash,')
    replacements[SAVE] = replacements[SAVE].replace('cp7_schedule_staged_review.current_source()', 'cp7_bounded_analysis_stage.source_for(run.facts,run.query)')
    replacements[SAVE] = source.once(replacements[SAVE], ' insert into cp7_schedule_native.commands(actor,request_id,payload,result)',
        " if run.facts->>'bounded_request_contract'='cp7.bounded-analysis-request.v1'then\n"
        "  outcome:=outcome||jsonb_build_object('contract_version','cp7.planning-schedule-staged-bounded-outcome.v1',\n"
        "   'bounded_request_contract',run.facts->'bounded_request_contract','bounded_reference_contract',run.facts->'bounded_reference_contract');end if;\n"
        ' insert into cp7_schedule_native.commands(actor,request_id,payload,result)')
    # The old route must refuse a new-method UUID too, rather than silently
    # returning a reference it never captured under that method.
    replacements[OLD_REQUEST] = source.once(old[OLD_REQUEST], '  if jq<>q then',
        "  if exists(select 1 from cp7_analysis_stage.jobs x where x.id=jid and x.reference?'bounded_request_contract')then\n"
        "   raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;\n  if jq<>q then")
    request = private_copy(old[OLD_REQUEST], 'request')
    request = source.once(request, '  if jq<>q then', "  if not exists(select 1 from cp7_analysis_stage.jobs x where x.id=jid\n"
        "   and x.reference->>'bounded_request_contract'='cp7.bounded-analysis-request.v1')then\n"
        "   raise exception 'CP7_ANALYSIS_REQUEST_CHANGED';end if;\n  if jq<>q then")
    request = source.once(request, "cp7_analysis_native.source_within((b->>'job_targets')::integer,(b->>'job_matching_products')::integer)\n  ||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED')", 'cp7_bounded_analysis_stage.source(q,true)')
    sql = source.render()+'\n'+require+'\n'+prep+'\n'+scenario+'\n'+request+'\n'
    for signature in PRIVATE:
        sql += 'alter function '+SCHEMA+'.'+signature+' owner to cp7_capture;\n'
        sql += 'revoke all on function '+SCHEMA+'.'+signature+' from public,anon,authenticated,service_role;\n'
    sql += '\n'.join(replace_header(text) for text in replacements.values())+'\n'
    sql += "grant create on schema public to cp7_capture;\ncreate function public.erp_cp7_request_bounded_staged_analysis_v1(p_query jsonb,p_request uuid)returns jsonb\n"
    sql += "language sql volatile security definer set search_path=''set TimeZone='UTC'as $$select cp7_bounded_analysis_stage.request(p_query,p_request)$$;\n"
    sql += 'alter function '+PUBLIC+' owner to cp7_capture;\nrevoke all on function '+PUBLIC+' from public,anon,authenticated,service_role;\n'
    sql += 'grant execute on function '+PUBLIC+' to authenticated;\nrevoke create on schema public from cp7_capture;\n'
    return sql, {sig: replace_header(text) for sig, text in replacements.items()}


def manifest():
    sql, new = render()
    body = lambda text: re.search(r'as \$\$(.*?)\$\$;',text,re.S)[1]
    return dict(contract='cp7.bounded-analysis-stage.v1', sql_sha256=sha256(sql.encode()).hexdigest(),
        replacements={sig: dict(before_sha256=sha256(body(text).encode()).hexdigest(),
                               after_sha256=sha256(body(new[sig]).encode()).hexdigest())
                      for sig,text in originals().items()},
        source_files={str(p.relative_to(ROOT.parent)):sha256(p.read_bytes()).hexdigest() for p in
            [source.CURRENT_FP, ROOT.parent/'cp7_production_stage/sql/cp7_analysis_stage__history_prep.sql',
             source.NATIVE/'analysis-stages.sql', ROOT.parent/'cp7_schedule_staged_review/review.sql']})
