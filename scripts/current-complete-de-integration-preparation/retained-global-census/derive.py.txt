"""Counted reversible extensions of every ee145 runtime consumer.

All19 SQL queries stay byte exact. Only dependency representation, raw-file
retention and the explicitly named successor routes change.
"""
from hashlib import sha256
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
NS = 'scripts/current-de-sku-global-census-multiset-qualification'
PARENT = 'scripts/current-de-sku-global-census-qualification'
HELPER = 'scripts/current-global-actual-writer-census-qualification'
OLD = 'scripts/current-vendor-receivable-qualification/probe.py'
LABEL = 'CP7_D1_E_SKU_GLOBAL_CENSUS_MULTISET'
CASE = 'D1_E_SKU_GLOBAL_WRITER_MULTISET_SOURCE_ONLY'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def replace_exact(text, changes, kind):
    original = text
    for before, after in changes:
        if text.count(before) != 1 or after in text: raise ValueError('GLOBAL_MULTISET_COUNTED_' + kind + '_ANCHOR_CHANGED')
        text = text.replace(before, after, 1)
    reverse = text
    for before, after in reversed(changes):
        if reverse.count(after) != 1: raise ValueError('GLOBAL_MULTISET_REVERSE_ANCHOR_CHANGED')
        reverse = reverse.replace(after, before, 1)
    if reverse != original: raise ValueError('GLOBAL_MULTISET_NOT_BYTE_REVERSIBLE')
    compile(text, '<global-multiset-' + kind + '>', 'exec')
    return text, dict(kind=kind, before_sha256=sha256(original.encode()).hexdigest(),
        after_sha256=sha256(text.encode()).hexdigest(), counted_changes=len(changes), byte_reversible=True)


def parent(kind):
    return getattr(load('global_multiset_frozen_ee145_derivation', ROOT / PARENT / 'derive.py'), kind)()


def capture():
    text = (ROOT / HELPER / 'capture.py').read_text()
    injection = """spec.loader.exec_module(census)
_bag_spec = importlib.util.spec_from_file_location('global_multiset_lossless_codec', HERE.parents[1] / '""" + NS + """/multiset.py')
multiset = importlib.util.module_from_spec(_bag_spec)
_bag_spec.loader.exec_module(multiset)"""
    return replace_exact(text, (
        ('spec.loader.exec_module(census)', injection),
        ("CONTRACT = 'cp7.global.actual-writer-census.supplement.v1'", "CONTRACT = 'cp7.global.actual-writer-census.supplement.multiset.v2'"),
        ('def capture(cur, catalog, *, progress=None):', 'def capture(cur, catalog, *, raw_directory, progress=None):'),
        ('    groups = {}\n    if progress is None:', '    raw_groups = {}\n    if progress is None:'),
        ("            raise\n        values = dict(rows)\n        census.require(len(values) == len(rows), 'GLOBAL_CENSUS_DUPLICATE_SUPPLEMENT_IDENTITY:' + name)\n        groups[name] = values\n        progress(dict(component='GLOBAL_CENSUS_READ_ONLY', phase=name, status='CAPTURED', rows=len(values)))",
         "            multiset.persist_raw(raw_directory, catalog, identity, params, raw_groups, QUERIES,\n"
         "                failure=dict(phase=name, sqlstate=getattr(error, 'sqlstate', None)))\n"
         "            raise\n"
         "        raw_groups[name] = [list(row) for row in rows]\n"
         "        progress(dict(component='GLOBAL_CENSUS_READ_ONLY', phase=name, status='CAPTURED', rows=len(rows)))\n"
         "    raw_reference = multiset.persist_raw(raw_directory, catalog, identity, params, raw_groups, QUERIES)\n"
         "    groups = {name: multiset.encode_group(name, rows) for name, rows in raw_groups.items()}"),
        ('                  identity=list(identity), groups=groups, transaction_writes=False,',
         '                  identity=list(identity), groups=groups, raw_capture_reference=raw_reference, transaction_writes=False,'),
        ('    groups = supplement[\'groups\']',
         "    multiset.reference(supplement.get('raw_capture_reference'))\n"
         "    census.require(supplement['raw_capture_reference']['catalogue_sha256'] == census.digest(catalog), 'GLOBAL_MULTISET_RAW_REFERENCE_CATALOGUE_CHANGED')\n"
         "    groups = supplement['groups']\n"
         "    for name in multiset.BAG_GROUPS:\n"
         "        census.require(groups.get(name, {}).get('group') == name, 'GLOBAL_MULTISET_BAG_GROUP_IDENTITY_CHANGED')\n"
         "        multiset.values(groups[name])"),
        ("for row in groups['view_relation_dependencies'].values():", "for row in multiset.values(groups['view_relation_dependencies']):"),
        ("for row in groups['dependencies'].values()),", "for row in multiset.values(groups['dependencies'])),"),
        ("for row in groups['dependencies'].values() if row[0] == 'pg_proc'", "for row in multiset.values(groups['dependencies']) if row[0] == 'pg_proc'"),
        ("bool(groups['dependencies']) and all", "bool(multiset.values(groups['dependencies'])) and all"),
    ), 'capture')


def integration():
    text, inherited = parent('integration')
    text, proof = replace_exact(text, (
        ("spec = importlib.util.spec_from_file_location('global_census_integration_capture', HERE / 'capture.py')\ncapture = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(capture)",
         "spec = importlib.util.spec_from_file_location('global_multiset_integration_capture_compiler', HERE.parents[1] / '" + NS + "/compile_modules.py')\n_compiler = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(_compiler)\ncapture = _compiler.capture()"),
        ("ORIGINAL = 'GLOBAL_ACTUAL_WRITER_SUPPLEMENT.json'", "ORIGINAL = 'GLOBAL_ACTUAL_WRITER_SUPPLEMENT_V2.json'"),
        ('    capture.validate(supplement, catalog)\n    directory = Path(directory)',
         '    capture.validate(supplement, catalog)\n    capture.multiset.require_projection(directory, supplement, catalog, capture.QUERIES)\n    directory = Path(directory)'),
        ('    capture.validate(observed, catalog)\n    return observed, raw',
         '    capture.validate(observed, catalog)\n    capture.multiset.require_projection(directory, observed, catalog, capture.QUERIES)\n    return observed, raw'),
    ), 'integration')
    return text, dict(inherited=inherited, successor=proof)


def census():
    text = (ROOT / HELPER / 'census.py').read_text()
    return replace_exact(text, (
        ('def analyze(catalog, *, expected_contexts, raw_authority=None, supplement=None, roots=None, provenance=None):',
         'def analyze(catalog, *, expected_contexts, raw_authority=None, supplement=None, roots=None, provenance=None, original_directory=None):'),
        ("        spec = importlib.util.spec_from_file_location('global_census_supplement_validator', HERE / 'capture.py')\n        module = importlib.util.module_from_spec(spec)\n        spec.loader.exec_module(module)\n        supplemental_proof = module.validate(supplement, catalog)",
         "        require(original_directory is not None, 'GLOBAL_MULTISET_ANALYSIS_RAW_ORIGINAL_REQUIRED')\n"
         "        spec = importlib.util.spec_from_file_location('global_multiset_analysis_compiler', HERE.parents[1] / '" + NS + "/compile_modules.py')\n"
         "        compiler = importlib.util.module_from_spec(spec)\n        spec.loader.exec_module(compiler)\n"
         "        module = compiler.capture()\n        supplemental_proof = module.validate(supplement, catalog)\n"
         "        module.multiset.require_projection(original_directory, supplement, catalog, module.QUERIES)"),
        ("for row in supplement['groups']['view_relation_dependencies'].values():",
         "for row in module.multiset.values(supplement['groups']['view_relation_dependencies']):"),
    ), 'census')


def runner():
    text, inherited = parent('runner')
    text, proof = replace_exact(text, (
        ("    census_capture=load('global_actual_census_capture',ROOT/'" + HELPER + "/capture.py')",
         "    census_capture=load('global_multiset_capture_loader',ROOT/'" + NS + "/loader.py').capture()"),
        ("    census_integration=load('global_actual_census_integration_loader',ROOT/'" + PARENT + "/loader.py').integration()",
         "    census_integration=load('global_multiset_integration_loader',ROOT/'" + NS + "/loader.py').integration()"),
        ("    supplemental_capture=census_capture.capture(cur,before['catalog'])",
         "    report['read_before']=before\n"
         "    report['global_writer_read_transaction']=read_transaction\n"
         "    supplemental_capture=census_capture.capture(cur,before['catalog'],raw_directory=ROOT/'cp6-proof/t3')"),
        ("CASE='D1_E_SKU_GLOBAL_WRITER_CENSUS_SOURCE_ONLY'", "CASE='" + CASE + "'"),
        ("classification='ACTUAL_D1_E_SKU_GLOBAL_WRITER_METADATA_ONLY'", "classification='ACTUAL_D1_E_SKU_GLOBAL_WRITER_MULTISET_METADATA_ONLY'"),
    ), 'runner')
    return text, dict(inherited=inherited, successor=proof, runtime_entry=None, actual_Native_credit=0)


def gate():
    text, inherited = parent('gate')
    text, proof = replace_exact(text, (
        ("    spec=importlib.util.spec_from_file_location('global_census_result_integration',ROOT/'" + HELPER + "/integration.py')\n    census_integration=importlib.util.module_from_spec(spec);spec.loader.exec_module(census_integration)",
         "    spec=importlib.util.spec_from_file_location('global_multiset_result_loader',ROOT/'" + NS + "/loader.py')\n    census_loader=importlib.util.module_from_spec(spec);spec.loader.exec_module(census_loader)\n    census_integration=census_loader.integration()"),
        ("CASE='D1_E_SKU_GLOBAL_WRITER_CENSUS_SOURCE_ONLY'", "CASE='" + CASE + "'"),
        ("report.get('label')=='CP7_D1_E_SKU_GLOBAL_CENSUS'", "report.get('label')=='" + LABEL + "'"),
        ("'CP7_D1_E_SKU_GLOBAL_CENSUS.json'", "'" + LABEL + ".json'"),
        ("status='ACTUAL_D1_E_SKU_GLOBAL_CENSUS_METADATA_PREUSE_AND_ALL5_QUALIFIED'",
         "status='ACTUAL_D1_E_SKU_GLOBAL_MULTISET_METADATA_PREUSE_AND_ALL5_QUALIFIED'"),
    ), 'gate')
    return text, dict(inherited=inherited, successor=proof, runtime_entry=None, actual_Native_credit=0)


def engine():
    text, inherited = parent('engine')
    # The runner loader and admission each reference the successor namespace.
    text, proof = replace_exact(text, (
        ("REPO/'" + PARENT + "/loader.py'", "REPO/'" + NS + "/loader.py'"),
        ("REPO/'" + PARENT + "/admission.py'", "REPO/'" + NS + "/admission.py'"),
        ("LABEL='CP7_D1_E_SKU_GLOBAL_CENSUS'", "LABEL='" + LABEL + "'"),
        ("PRE_DUMP='/tmp/current_de_sku_global_census_pre.dump'", "PRE_DUMP='/tmp/current_de_sku_global_census_multiset_pre.dump'"),
    ), 'engine')
    return text, dict(inherited=inherited, successor=proof,
        install_preuse_inverse_reinstall_commit_outer_restore_all5_preserved=True,
        actual_business_cases=0, runtime_entry=None, actual_Native_credit=0)


def file_transitions(root=ROOT):
    plan = json.loads((Path(root) / NS / 'FILE_TRANSITIONS.json').read_bytes())
    for name, row in plan.items():
        raw = (Path(root) / row['parent_path']).read_text(); observed = (Path(root) / NS / name).read_text()
        if sha256(raw.encode()).hexdigest() != row['before_sha256']: raise ValueError('GLOBAL_MULTISET_FILE_PARENT_CHANGED:' + name)
        text = raw
        for edit in row['changes']:
            if edit['count'] != 1 or text.count(edit['before']) != 1: raise ValueError('GLOBAL_MULTISET_FILE_COUNT_CHANGED:' + name)
            text = text.replace(edit['before'], edit['after'], 1)
        if text != observed or sha256(text.encode()).hexdigest() != row['after_sha256']:
            raise ValueError('GLOBAL_MULTISET_UNDECLARED_FILE_TRANSITION:' + name)
        for edit in reversed(row['changes']):
            if text.count(edit['after']) != 1: raise ValueError('GLOBAL_MULTISET_FILE_REVERSE_COUNT_CHANGED:' + name)
            text = text.replace(edit['after'], edit['before'], 1)
        if text != raw: raise ValueError('GLOBAL_MULTISET_FILE_NOT_REVERSIBLE:' + name)
    return dict(files=len(plan), byte_reversible=True)
