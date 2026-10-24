"""Single physical-root history, derived from the existing Native projections.

No global bound is raised, no current model caller is replaced, and no past
knowledge time is invented. The caller must separately persist/admit a capture.
"""
from pathlib import Path
from hashlib import sha256
import json
import re

ROOT = Path(__file__).resolve().parent
SCRIPTS = ROOT.parent
SCHEMA = 'cp7_model_history_scope'
PINNED = ('cp7_reorder_inputs/capture.sql', 'cp7_reorder_inputs/history.sql',
          'cp7_reorder_inputs/stock.sql', 'cp7_history_reference/digest.sql',
          'cp7-src/planning/history.sql', 'cp7-src/planning/history-source.sql',
          'cp7-src/demand/history.sql')


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError('MODEL_HISTORY_SCOPE_DERIVATION_CHANGED: '+old[:90])
    return text.replace(old, new)


def block(path, name):
    found = re.search(r'create function '+re.escape(name)+r'\(.*?\$\$;', (SCRIPTS/path).read_text(), re.S)
    if found is None:
        raise ValueError('MODEL_HISTORY_SCOPE_DEPENDENCY_MISSING: '+name)
    return found[0]


def render():
    raw = block('cp7_reorder_inputs/capture.sql', 'cp7_reorder_inputs.capture_history')
    raw = once(raw, 'cp7_reorder_inputs.capture_history(p_products integer)', SCHEMA+'.raw(p_root uuid)')
    # Select the whole identity root before the original completeness check.
    # Do not filter size here: two active versions of one root must still fail.
    raw = once(raw, 'where p.effective_from<=c.at', 'where coalesce(p.identity_root_id,p.id)=p_root and p.effective_from<=c.at')
    raw = once(raw, 'limit p_products+1', 'limit 2')
    raw = once(raw, "jsonb_array_length(facts->'products')<=p_products", "jsonb_array_length(facts->'products')=1")
    raw = raw.replace('cp7.native-demand-facts.v1', 'cp7.model-history-facts.v1').replace('GLOBAL_CURRENT_PHYSICAL_ROOTS', 'SINGLE_CURRENT_PHYSICAL_ROOT')
    build = block('cp7-src/planning/history.sql', 'cp7_planning.history_build')
    build = once(build, 'cp7_planning.history_build(c jsonb,q jsonb)', SCHEMA+'.build(c jsonb,q jsonb,summary jsonb)')
    start = build.index('begin\n')+len('begin\n')
    end = build.index(' input:=', start)
    build = build[:start]+""" hash:=cp7_model_history_scope.identity(c);
 perform cp7_wip.fields(q,array['from_date','through_date','group_mode']);
 if cp7_demand.day(q->'through_date')<cp7_demand.day(q->'from_date')
  or cp7_demand.day(q->'through_date')-cp7_demand.day(q->'from_date')>365
  or cp7_demand.day(q->'through_date')>=((c->>'captured_at')::timestamptz at time zone'Asia/Jakarta')::date
  or q->>'group_mode'is null or q->>'group_mode'not in('AS_SOLD','RESTATED')then
  raise exception 'CP7_MODEL_HISTORY_SCOPE_QUERY';end if;
 if c->>'status'='COMPLETE'then
  if summary is not null and summary<>'null'::jsonb then raise exception 'CP7_MODEL_HISTORY_SCOPE_UNEXPECTED_SUMMARY';end if;
 else
  if summary->>'contract_version'is distinct from'cp7.reorder-stock-summary.v1'
   or summary->'captured_at'is distinct from c->'captured_at' or summary->'query'is distinct from q
   or summary->'products'is distinct from'1'::jsonb
   or summary->'raw_rows_truncated'is distinct from'false'::jsonb
   or summary->'Native_capture_status_overridden'is distinct from'false'::jsonb
   or(summary->>'raw_rows_read')::bigint is distinct from(c->'stock_reference'->>'row_count')::bigint
   or jsonb_array_length(summary->'availability')is distinct from(cp7_demand.day(q->'through_date')-cp7_demand.day(q->'from_date')+1)
   or exists(select 1 from jsonb_array_elements(summary->'availability')x where x->'target_key'is distinct from c->'target_key'
     or x->'known_at'is distinct from c->'captured_at')then
   raise exception 'CP7_MODEL_HISTORY_SCOPE_SUMMARY_BINDING';end if;
 end if;
"""+build[end:]
    build = once(build, "'availability',cp7_planning.history_availability(c,q)",
                 "'availability',case when c->>'status'='COMPLETE'then cp7_planning.history_availability(c,q)else summary->'availability'end")
    start = build.index(' -- P19:')
    end = build.index(" return jsonb_build_object('contract_version'", start)
    build = build[:start]+""" -- Retain the same reservation/current-stock kernel on both input paths.
 select coalesce(array_agg(jsonb_set(x,'{availability,inputs,scope_id}',to_jsonb('SINGLE_CURRENT_PHYSICAL_ROOT'::text))order by x->>'target_key'),'{}'::jsonb[])
 into current_rows from jsonb_array_elements(cp7_reorder_inputs.current_stock(c,summary,hash))x;
"""+build[end:]
    build = build.replace('GLOBAL_CURRENT_PHYSICAL_ROOTS', 'SINGLE_CURRENT_PHYSICAL_ROOT')
    build = build.replace('cp7.native-demand-history.v1', 'cp7.scoped-demand-history.v1').replace("'producer','native-demand-1'", "'producer','scoped-native-demand-1'")
    build = once(build, "'capture_complete',true,", "'capture_complete',true,'target_key',c->'target_key','raw_capture_status',c->'status','raw_status_overridden',false,")
    suffix = ''
    for sig in ('raw(uuid)', 'identity(jsonb)', 'build(jsonb,jsonb,jsonb)', 'capture(text,jsonb,boolean)'):
        suffix += 'alter function '+SCHEMA+'.'+sig+' owner to cp7_capture;\n'
        suffix += 'revoke all on function '+SCHEMA+'.'+sig+' from public,anon,authenticated,service_role;\n'
    return ('create schema '+SCHEMA+' authorization cp7_capture;\nrevoke all on schema '+SCHEMA+' from public,anon,authenticated,service_role;\n'
            +raw+'\n'+(ROOT/'identity.sql').read_text()+'\n'+build+'\n'+(ROOT/'capture.sql').read_text()+'\n'+suffix)


def manifest():
    return dict(contract='cp7.model-history-scope-private.v1', private_functions=4, new_tables=0, public_rpcs=0,
                existing_replacements=0, scope='SINGLE_CURRENT_PHYSICAL_ROOT', days_maximum=366,
                source_files_sha256={p:sha256((SCRIPTS/p).read_bytes()).hexdigest()for p in PINNED},
                generated_sql_sha256=sha256(render().encode()).hexdigest(),
                immutable_capture_runtime_qualified=False, model_caller_integrated=False, production_go=False)


if __name__ == '__main__':
    (ROOT/'scope.sql').write_text(render())
    (ROOT/'MANIFEST.json').write_text(json.dumps(manifest(), indent=2)+'\n')
