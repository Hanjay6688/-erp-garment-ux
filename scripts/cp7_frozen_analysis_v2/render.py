"""Explicit frozen source v2; derive admission from the unchanged compiler."""
from pathlib import Path
from hashlib import sha256
import json
import re
from cp7_production_stage import _body
from cp7_history_reference_binary_v2.render import LAYOUT_SHA256

ROOT = Path(__file__).resolve().parent
SCHEMA = 'cp7_frozen_analysis_v2'
PARENT = ROOT.parent / 'cp7_model_target_consumer_v2_stage' / 'hooks.sql'
FUNCTIONS = {
    'base(jsonb)': 'i', 'admit(jsonb,jsonb,integer)': 'i',
    'stock_reference(jsonb,jsonb)': 'i',
    'capsule_hash(jsonb,jsonb,jsonb,jsonb,text)': 'i',
    'reference(jsonb,jsonb,jsonb,text)': 'i',
    'seal(jsonb,jsonb,jsonb,jsonb,text,integer)': 'i',
    'verify_capsule(jsonb,jsonb,integer)': 'i',
    'work_fingerprint(jsonb)': 'i', 'prepare(jsonb,jsonb,integer)': 'i',
    'producer_hash()': 's', 'source(jsonb,boolean)': 's',
}


def block(text, name):
    found = re.findall(r'create (?:or replace )?function ' + re.escape(name) + r'\(.*?\$\$;', text, re.S)
    if len(found) != 1:
        raise ValueError('FROZEN_SOURCE_V2_PARENT_FUNCTION_CHANGED: ' + name)
    return found[0]


def admissions():
    compiler = block(PARENT.read_text(), 'cp7_history_bounded.compile')
    start = compiler.index("  perform cp7_wip.fields(f,array[")
    end = compiler.index("  if summary->>'contract_version'", start)
    incomplete = compiler[start:end].replace('p_products', 'p_cap')
    # This tail is the exact existing non-stock completeness predicate. Use
    # it on COMPLETE captures as well; do not recalculate targets on capture.
    tail = incomplete[incomplete.index("   or jsonb_array_length(f->'products')"):]
    complete = "  if jsonb_array_length(f->'stock')>50000\n" + tail
    return incomplete, complete


def dependencies():
    parent = PARENT.read_text()
    paths = {
        'cp7_analysis_stage.bounds()': ('cp7-src/planning/analysis-stages.sql', 'cp7_analysis_stage.bounds'),
        'cp7_demand.instant(jsonb)': ('cp7-src/demand/bootstrap.sql', 'cp7_demand.instant'),
        'cp7_demand.day(jsonb)': ('cp7-src/demand/bootstrap.sql', 'cp7_demand.day'),
        'cp7_demand.items(jsonb,integer)': ('cp7-src/demand/bootstrap.sql', 'cp7_demand.items'),
        'cp7_wip.fields(jsonb,text[])': ('cp7-src/wip/bootstrap.sql', 'cp7_wip.fields'),
        'cp7_planning.utc(timestamp with time zone)': ('cp7-src/planning/bootstrap.sql', 'cp7_planning.utc'),
        'cp7_planning.history_query(jsonb)': ('cp7-src/planning/bootstrap.sql', 'cp7_planning.history_query'),
        'cp7_reorder_inputs.stock_summary(jsonb,timestamp with time zone,jsonb)': ('cp7_reorder_inputs/stock.sql', 'cp7_reorder_inputs.stock_summary'),
        'cp7_history_reference_binary_v2.stock_digest(jsonb,timestamp with time zone)': ('cp7_history_reference_binary_v2/digest.sql', 'cp7_history_reference_binary_v2.stock_digest'),
    }
    out = {sig: {'body_sha256': sha256(_body(block((ROOT.parent / path).read_text(), name)).encode()).hexdigest(), 'owner': 'cp7_capture'}
           for sig, (path, name) in paths.items()}
    for name, signature in (
        ('cp7_history_bounded.compile', '(jsonb,jsonb,jsonb,integer)'),
        ('cp7_bounded_analysis_stage.analysis_source', '(integer,integer)'),
        ('cp7_bounded_analysis_stage.native_work_fingerprint', '(jsonb)'),
        ('cp7_bounded_analysis_stage.producer_hash', '()'),
    ):
        out[name + signature] = {'body_sha256': sha256(_body(block(parent, name)).encode()).hexdigest(), 'owner': 'cp7_capture'}
    return out


def render():
    incomplete, complete = admissions()
    template = (ROOT / 'capsule.template.sql').read_text()
    for token, value in (('@@INCOMPLETE_ADMISSION@@', incomplete),
                         ('@@COMPLETE_ADMISSION@@', complete),
                         ('@@BINARY_LAYOUT@@', LAYOUT_SHA256)):
        if template.count(token) != 1:
            raise ValueError('FROZEN_SOURCE_V2_TEMPLATE_CHANGED: ' + token)
        template = template.replace(token, value)
    for sig in FUNCTIONS:
        template += 'alter function ' + SCHEMA + '.' + sig + ' owner to cp7_capture;\n'
        template += 'revoke all on function ' + SCHEMA + '.' + sig + ' from public,anon,authenticated,service_role;\n'
    return template


def manifest():
    return {
        'contract': 'cp7.frozen-analysis-stage.v2',
        'parent_compiler_body_sha256': dependencies()['cp7_history_bounded.compile(jsonb,jsonb,jsonb,integer)']['body_sha256'],
        'dependencies': dependencies(), 'sql_sha256': sha256(render().encode()).hexdigest(),
        'private_functions': len(FUNCTIONS), 'existing_replacements': 0,
        'new_tables': 0, 'public_rpcs': 0, 'Native_ERP_DML': False,
        'unchanged_compiler_called_only_by_prepare': True,
        'request_or_unit_integration': False, 'actual_Native_qualified': False,
        'full_factory_qualified': False, 'production_go': False,
    }


if __name__ == '__main__':
    (ROOT / 'capsule.sql').write_text(render())
    (ROOT / 'MANIFEST.json').write_text(json.dumps(manifest(), indent=2) + '\n')
