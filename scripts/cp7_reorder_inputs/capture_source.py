"""Derive two read-only captures from pinned Native source; no database DDL here.

Only a proven >50,000-stock-row scope avoids building a discarded JSON prefix.
Every other Native query, field and COMPLETE predicate stays byte-derived.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent/'cp7-src'


def block(path, name):
    raw = (ROOT/path).read_text()
    match = re.search(r'create function '+re.escape(name)+r'\(.*?\$\$;', raw, re.S)
    if match is None:
        raise ValueError('OW10_BOUNDED_CAPTURE_NATIVE_SOURCE_MISSING: '+name)
    return match[0]


def render():
    raw = block('planning/history-source.sql', 'cp7_planning.history_source_within')
    before = re.search(r'stock as materialized\(\n(.*?)\n\),\nsales as materialized', raw, re.S)
    if before is None:
        raise ValueError('OW10_BOUNDED_CAPTURE_STOCK_CTE_CHANGED')
    stock = before[1]
    end = ' order by m.id limit 50001'
    if stock.count(end) != 1 or stock.count('\n from erp.fg_stock_movements ') != 1:
        raise ValueError('OW10_BOUNDED_CAPTURE_STOCK_QUERY_CHANGED')
    source = stock[stock.index('\n from erp.fg_stock_movements '):stock.index(end)]
    limited = 'stock_limit as materialized(select count(*)n from(select 1'+source+' limit 50001)counted),\n'
    retained = stock.replace(end, ' and(select n from stock_limit)<=50000'+end)
    raw = raw[:before.start()]+limited+'stock as materialized(\n'+retained+'\n),\nsales as materialized'+raw[before.end():]
    predicate = "'status',case when jsonb_array_length(facts->'products')<=p_products"
    if raw.count(predicate) != 1:
        raise ValueError('OW10_BOUNDED_CAPTURE_COMPLETE_PREDICATE_CHANGED')
    raw = raw.replace(predicate, predicate+'\n  and(select n from stock_limit)<=50000')
    tail = "'facts',facts)from source cross join clock c"
    if raw.count(tail) != 1:
        raise ValueError('OW10_BOUNDED_CAPTURE_RESULT_CHANGED')
    raw = raw.replace(tail, "'facts',facts,'stock_raw_omitted',(select n>50000 from stock_limit),"
                      "'stock_rows_at_least',(select n from stock_limit))from source cross join clock c")
    raw = raw.replace('create function cp7_planning.history_source_within(',
                      'create function cp7_reorder_inputs.capture_history(')
    baseline = block('planning/baseline-source.sql', 'cp7_baseline_native.source_within')
    if baseline.count('cp7_planning.history_source_within(p_products)') != 1:
        raise ValueError('OW10_BOUNDED_CAPTURE_BASELINE_SOURCE_CHANGED')
    baseline = baseline.replace('create function cp7_baseline_native.source_within(',
                                'create function cp7_reorder_inputs.capture_baseline(')
    baseline = baseline.replace('cp7_planning.history_source_within(p_products)',
                                'cp7_reorder_inputs.capture_history(p_products)')
    suffix = '\n'
    for name in ('capture_history', 'capture_baseline'):
        suffix += 'alter function cp7_reorder_inputs.'+name+'(integer)owner to cp7_capture;\n'
        suffix += 'revoke all on function cp7_reorder_inputs.'+name+'(integer)from public,anon,authenticated,service_role;\n'
    return '-- Derived from pinned Native bodies; original functions are unchanged.\n'+raw+'\n'+baseline+suffix
