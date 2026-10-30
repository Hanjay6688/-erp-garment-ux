"""Counted in-memory runner/gate derivation for the next admitted successor.

This module only returns source strings. It neither writes canonical parent
files nor creates a runnable release/CI entrypoint or launches a database.
"""
from hashlib import sha256
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-global-actual-writer-census-qualification'
PARENT = 'scripts/current-de-sku-parent-catalogue-qualification'
RUNNER = PARENT + '/runner.py'
GATE = PARENT + '/result_gate.py'

RUNNER_EDITS = (
    ("    cc=load('catalogue_actual_context_reader',HERE/'context_catalog.py')",
     "    cc=load('catalogue_actual_context_reader',HERE/'context_catalog.py')\n"
     "    census_capture=load('global_actual_census_capture',ROOT/'" + NS + "/capture.py')\n"
     "    census_integration=load('global_actual_census_integration',ROOT/'" + NS + "/integration.py')\n"
     "    read_transaction=census_integration.begin_readonly(conn,cur)"),
    ("    before=dict(catalog=catalog._catalog_rows(cur),data_and_sequences=catalog._data(cur))",
     "    before=dict(catalog=catalog._catalog_rows(cur),data_and_sequences=catalog._data(cur))\n"
     "    census_integration.require_current_preuse(before,state)\n"
     "    supplemental_capture=census_capture.capture(cur,before['catalog'])\n"
     "    supplemental_reference=census_integration.persist_original(ROOT/'cp6-proof/t3',supplemental_capture,before['catalog'])\n"
     "    report['global_writer_supplemental_reference']=supplemental_reference\n"
     "    report['global_writer_read_transaction']=read_transaction"),
    ("    if before!=after:raise ValueError('DE_SKU_CATALOGUE_READ_CHANGED_ACTUAL_CATALOG_ROWS_OR_SEQUENCES')",
     "    if before!=after:raise ValueError('DE_SKU_CATALOGUE_READ_CHANGED_ACTUAL_CATALOG_ROWS_OR_SEQUENCES')\n"
     "    report['global_writer_supplemental_noeffect']=census_integration.finish(before,after,supplemental_capture,state)"),
)

GATE_EDITS = (
    ("def checked(report,package,head):",
     "def checked(report,package,head,original_directory=None):"),
    ("    require(case['actual_composite_catalogue']==case['read_before']['catalog'],'DE_SKU_ACTUAL_CATALOGUE_NOT_EMBEDDED_EXACTLY')",
     "    require(case['actual_composite_catalogue']==case['read_before']['catalog'],'DE_SKU_ACTUAL_CATALOGUE_NOT_EMBEDDED_EXACTLY')\n"
     "    import importlib.util\n"
     "    spec=importlib.util.spec_from_file_location('global_census_result_integration',ROOT/'" + NS + "/integration.py')\n"
     "    census_integration=importlib.util.module_from_spec(spec);spec.loader.exec_module(census_integration)\n"
     "    census_integration.validate_case(case,original_directory if original_directory is not None else ROOT/'cp6-proof/t3')"),
    ("    result=checked(*(json.loads(raw)for raw in raws),head)",
     "    result=checked(*(json.loads(raw)for raw in raws),head,original_directory=args.directory)"),
)


def derive(kind, raw=None):
    if kind not in ('runner', 'gate'):
        raise ValueError('GLOBAL_CENSUS_EXACT_DERIVATIVE_KIND_REQUIRED')
    filename, edits = (RUNNER, RUNNER_EDITS) if kind == 'runner' else (GATE, GATE_EDITS)
    expected = json.loads((HERE / 'INTEGRATION_SOURCE.json').read_bytes())['files'][filename]
    raw = (ROOT / filename).read_bytes() if raw is None else raw
    if len(raw) != expected['bytes'] or sha256(raw).hexdigest() != expected['sha256']:
        raise ValueError('GLOBAL_CENSUS_EXACT_PARENT_DERIVATIVE_SOURCE_REQUIRED:' + kind)
    text = raw.decode()
    for before, after in edits:
        if text.count(before) != 1 or after in text:
            raise ValueError('GLOBAL_CENSUS_EXACT_COUNTED_ANCHOR_REQUIRED:' + kind)
        text = text.replace(before, after, 1)
    reverse = text
    for before, after in reversed(edits):
        if reverse.count(after) != 1:
            raise ValueError('GLOBAL_CENSUS_EXACT_REVERSE_ANCHOR_REQUIRED:' + kind)
        reverse = reverse.replace(after, before, 1)
    if reverse.encode() != raw:
        raise ValueError('GLOBAL_CENSUS_DERIVATION_NOT_BYTE_REVERSIBLE:' + kind)
    compile(text, filename, 'exec')
    return text, dict(kind=kind, original_path=filename, original_sha256=sha256(raw).hexdigest(),
        derived_sha256=sha256(text.encode()).hexdigest(), counted_changes=len(edits),
        byte_reversible=True, canonical_parent_written=False,
        next_successor_source_admission_required=True, next_producer_metadata_required=True,
        metadata_launch_prepared=False, runtime_entry=None,
        actual_Native_credit=0, production_go=False, independent_acceptance=False)
