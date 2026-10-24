"""Derive bounded history inputs from the qualified read-only reorder compiler.

This does not promote a raw Native INCOMPLETE capture to COMPLETE. It returns
an explicit complete SQL-summary input alongside the unchanged raw status.
"""
from pathlib import Path
from hashlib import sha256
import json
import re

ROOT = Path(__file__).resolve().parent
NATIVE = ROOT.parent/'cp7_reorder_inputs'
SCHEMA = 'cp7_history_bounded'


def once(text, before, after):
    if text.count(before) != 1:
        raise ValueError('BOUNDED_HISTORY_DERIVATION_CHANGED: '+before[:100])
    return text.replace(before, after)


def native_block(file, name):
    match = re.search(r'create function '+re.escape(name)+r'\(.*?\$\$;', (NATIVE/file).read_text(), re.S)
    if match is None:
        raise ValueError('BOUNDED_HISTORY_DEPENDENCY_MISSING: '+name)
    return match[0]


def dependencies():
    names = [('capture.sql','capture_baseline','(integer)'),('history.sql','history','(jsonb,jsonb)'),
             ('stock.sql','stock_summary','(jsonb,timestamp with time zone,jsonb)'),
             ('history.sql','current_stock','(jsonb,jsonb,text)')]
    out = {}
    for file, name, signature in names:
        raw = native_block(file,'cp7_reorder_inputs.'+name)
        body = re.search(r'as \$\$(.*?)\$\$;',raw,re.S)[1]
        out['cp7_reorder_inputs.'+name+signature] = dict(body_sha256=sha256(body.encode()).hexdigest(), owner='cp7_capture')
    return out


def render():
    pins = json.loads((ROOT/'MANIFEST.json').read_text())
    for file,digest in pins['source_files_sha256'].items():
        if sha256((NATIVE/file).read_bytes()).hexdigest() != digest:
            raise ValueError('BOUNDED_HISTORY_PINNED_SOURCE_CHANGED: '+file)
    if pins['dependencies'] != dependencies():
        raise ValueError('BOUNDED_HISTORY_DEPENDENCIES_CHANGED')
    raw = native_block('read.sql','cp7_reorder_inputs.compile')
    raw = once(raw,'create function cp7_reorder_inputs.compile(s jsonb)',
               'create function '+SCHEMA+'.compile(p_capture jsonb,p_query jsonb,p_summary jsonb,p_products integer)')
    raw = once(raw,'path text;p_products integer;', 'path text;')
    a = raw.index('begin\n')+len('begin\n')
    b = raw.index(" if c->>'status'='COMPLETE'then",a)
    raw = raw[:a]+""" perform cp7_wip.fields(p_query,array['from_date','through_date','group_mode']);
 if p_products is null or p_products not between 1 and 5000
  or p_capture->>'contract_version'is distinct from'cp7.native-demand-facts.v1'
  or p_capture->>'scope'is distinct from'GLOBAL_CURRENT_PHYSICAL_ROOTS'
  or jsonb_array_length(p_capture->'facts'->'products')>p_products then
  raise exception 'CP7_BOUNDED_HISTORY_SOURCE_SHAPE';end if;
 perform cp7_demand.instant(p_capture->'captured_at');
 c:=p_capture;f:=c->'facts';q:=p_query;summary:=p_summary;
"""+raw[b:]
    # Everything through Native events/availability/rows/current stock/target
    # remains derived, including every non-stock incompleteness refusal.
    # ROP defaults/manuals/lead selection are outside this input reader.
    raw = once(raw, "  summary:=s->'stock_summary';\n", '')
    a = raw.index(" compiled:=cp7_reorder_inputs.points(")
    raw = raw[:a]+""" return jsonb_build_object('contract_version','cp7.bounded-history-inputs.v1',
  'captured_at',c->'captured_at','query',q,'raw_native_capture_status',c->'status',
  'coverage','COMPLETE','input_path',path,'inputs',inputs,
  'raw_stock_rows_read',summary->'raw_rows_read','stock_raw_omitted',coalesce(c->'stock_raw_omitted','false'::jsonb),
  'raw_native_status_overridden',false,'apply_enabled',false,'production_go',false);
end $$;"""
    capture = """
create function cp7_history_bounded.capture(p_query jsonb,p_products integer)returns jsonb
language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$
declare c jsonb;summary jsonb;
begin
 if p_products is null or p_products not between 1 and 5000 then raise exception 'CP7_BOUNDED_HISTORY_PRODUCT_BOUND';end if;
 perform cp7_wip.fields(p_query,array['from_date','through_date','group_mode']);
 c:=cp7_reorder_inputs.capture_baseline(p_products);
 if c->'stock_raw_omitted'='true'::jsonb or jsonb_array_length(c->'facts'->'stock')=50001 then
  summary:=cp7_reorder_inputs.stock_summary(c->'facts'->'products',(c->>'captured_at')::timestamptz,p_query);
 end if;
 return cp7_history_bounded.compile(c,p_query,summary,p_products);
end $$;
"""
    suffix = ''
    for sig in ('compile(jsonb,jsonb,jsonb,integer)','capture(jsonb,integer)'):
        suffix += 'alter function '+SCHEMA+'.'+sig+' owner to cp7_capture;\n'
        suffix += 'revoke all on function '+SCHEMA+'.'+sig+' from public,anon,authenticated,service_role;\n'
    return 'create schema '+SCHEMA+' authorization cp7_capture;\nrevoke all on schema '+SCHEMA+' from public,anon,authenticated,service_role;\n'+raw+'\n'+capture+suffix
