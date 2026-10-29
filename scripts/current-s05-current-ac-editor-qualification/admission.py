"""Exact historical source checks plus one bounded successor scope binding."""
from hashlib import sha256
from pathlib import Path
from types import ModuleType
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD_NS = 'scripts/current-s05-lawful-master-dates-qualification'
NS = 'scripts/current-s05-current-ac-editor-qualification'
WORKFLOW = '.github/workflows/cp7-current-s05-current-ac-editor.yml'
BASE = 'cdbdea26ef8e4d15bfc16a362c6fad636d961ef2'
OLD_SOURCE_SHA = '906d938a7b85e9391bdf55a8b824960b5657d694079d65eee6af3527a341c407'
OLD_ADMISSION_SHA = 'ae8fbf5837d4a984bcfbc98633bd1f8e357185b927ef5b4e4389a6ba9a2ed5d4'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def tracked_scope(repo=ROOT):
    changed = subprocess.check_output(['git', '-C', str(repo), 'diff', '--name-only', BASE, '--'],
                                     env=dict(os.environ, GIT_NO_LAZY_FETCH='1')).decode().splitlines()
    if any(not (path.startswith(NS+'/') or path == WORKFLOW) for path in changed):
        raise ValueError('S05_CURRENT_AC_FROZEN_CDBDEA_BYTES_CHANGED')
    return dict(base_head=BASE, all_other_cdbdea_tracked_files_unchanged=True,
                allowed_new_prefix=NS, allowed_new_workflow=WORKFLOW)


def historical_admission(repo=ROOT):
    path = Path(repo)/OLD_NS/'admission.py'
    raw = path.read_bytes()
    old = '    scope = tracked_scope(repo)\n'
    new = '    scope = __S05_CURRENT_AC_SUCCESSOR_SCOPE__(repo)\n'
    if sha256(raw).hexdigest() != OLD_ADMISSION_SHA or raw.count(old.encode()) != 1:
        raise ValueError('S05_CURRENT_AC_EXACT_HISTORICAL_SOURCE_READER_REQUIRED')
    code = raw.replace(old.encode(), new.encode(), 1)
    if code.replace(new.encode(), old.encode(), 1) != raw:
        raise ValueError('S05_CURRENT_AC_SCOPE_BINDING_NOT_REVERSIBLE')
    module = ModuleType('s05_current_AC_private_historical_admission')
    module.__file__ = str(path)
    module.__S05_CURRENT_AC_SUCCESSOR_SCOPE__ = tracked_scope
    exec(compile(code, str(path), 'exec'), module.__dict__)
    return module, dict(original_sha256=OLD_ADMISSION_SHA, derived_sha256=sha256(code).hexdigest(),
        counted_private_scope_bindings=1, all_historical_pins_original_readers_premises_and_source_guards_retained=True)


def offline(repo=ROOT, here=HERE):
    repo, here = Path(repo), Path(here)
    source = json.loads((here/'SOURCE.json').read_bytes())
    if (source['contract'] != 'cp7.s05-current-ac-editor-qualification.v1'
            or source['status'] != 'PREPARED' or type(source['actual_Native_credit']) is not int
            or source['actual_Native_credit'] != 0 or source['production_go'] is not False
            or source['independent_acceptance'] is not False):
        raise ValueError('S05_CURRENT_AC_PREPARATION_NOT_ACCEPTANCE')
    old_raw = (repo/OLD_NS/'SOURCE.json').read_bytes()
    if sha256(old_raw).hexdigest() != OLD_SOURCE_SHA:
        raise ValueError('S05_CURRENT_AC_FROZEN_CDBDEA_MANIFEST_CHANGED')
    old_source = json.loads(old_raw)
    for path, digest in old_source['files'].items():
        if source['files'].get(path) != digest:
            raise ValueError('S05_CURRENT_AC_HISTORICAL_SOURCE_OR_ORACLE_REPINNED:'+path)
    allowed = lambda p: p.startswith(NS+'/') or p in (WORKFLOW, OLD_NS+'/SOURCE.json',
        'supabase/release/cp6-t3/20260915031500_erp_v2_6_20ac_cp6_temporal_surface_closure.sql')
    if any(not allowed(p) for p in set(source['files'])-set(old_source['files'])):
        raise ValueError('S05_CURRENT_AC_UNDECLARED_SOURCE_EXTENSION')
    historical, scope_binding = historical_admission(repo)
    historical.pins(repo, source)
    own = {str(p.relative_to(repo)) for p in here.rglob('*') if p.is_file()}
    expected = {p for p in source['files'] if p.startswith(NS+'/')} | {NS+'/SOURCE.json'}
    if own != expected or any(p.is_symlink() for p in here.rglob('*')):
        raise ValueError('S05_CURRENT_AC_UNDECLARED_OWN_SOURCE')
    inherited = historical.offline(repo, repo/OLD_NS)
    binding = load('s05_current_AC_exact_premise', here/'binding.py')
    _, current = binding.premise(repo)
    declared = json.loads((here/'CURRENT_AC_EDITOR_PREMISE.json').read_bytes())
    if declared != current:
        raise ValueError('S05_CURRENT_AC_DECLARED_PREMISE_CHANGED')
    _, recipe = binding.current_recipe((repo/OLD_NS/'recipe.py').read_bytes())
    failure = load('s05_current_AC_first_failure', here/'first_failure.py').checked(here)
    workflow = load('s05_current_AC_full_workflow', here/'workflow_source.py').checked((repo/WORKFLOW).read_text(), repo)
    if source['Native_case_ids'] != inherited['Native_case_ids'] or len(source['Native_case_ids']) != 10:
        raise ValueError('S05_CURRENT_AC_EXACT_ORIGINAL_TEN_IDS_REQUIRED')
    return dict(status='EXACT_S05_CURRENT_AC_EDITOR_PREPARED_SOURCE_ONLY', source_files=len(source['files']),
        Native_case_ids=source['Native_case_ids'], inherited=inherited,
        source_scope_binding=scope_binding, current_AC_premise=current, private_recipe_ABI_binding=recipe,
        retained_cdbdea_failure=failure, workflow_derivation=workflow, tracked_scope=tracked_scope(repo),
        source_qualification=source, all_product_SQL_native_engines_oracles_dates_FIFO_unchanged=True,
        actual_Native_credit=0, database_calls=0, production_go=False, independent_acceptance=False)
