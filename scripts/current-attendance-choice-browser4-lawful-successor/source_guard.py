"""Source-only checks and a closed-before-import execution boundary."""
from hashlib import sha256
from pathlib import Path, PurePosixPath
import importlib.util
import json
import os
import subprocess
import argparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = ROOT / 'scripts/current-attendance-choice-browser4-qualification'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check():
    declaration = json.loads((HERE / 'SOURCE.json').read_bytes())
    if declaration['contract_version'] != 'cp7.s03-browser4-source.v1':
        raise ValueError('S03_BROWSER4_SOURCE_CONTRACT_REQUIRED')
    files = declaration['files']
    if len({item['path'] for item in files}) != len(files):
        raise ValueError('S03_BROWSER4_DUPLICATE_SOURCE')
    for item in files:
        name = PurePosixPath(item['path'])
        if name.is_absolute() or '..' in name.parts or '\\' in item['path']:
            raise ValueError('S03_BROWSER4_UNSAFE_SOURCE_PATH')
        path = ROOT / str(name)
        cursor = ROOT
        for part in name.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise ValueError('S03_BROWSER4_SOURCE_SYMLINK:' + str(name))
        if not path.is_file() or not path.resolve().is_relative_to(ROOT.resolve()):
            raise ValueError('S03_BROWSER4_SOURCE_MISSING:' + str(name))
        raw = path.read_bytes()
        if len(raw) != item['bytes'] or sha256(raw).hexdigest() != item['sha256']:
            raise ValueError('S03_BROWSER4_SOURCE_CHANGED:' + str(name))
    # Immutable public endpoint plus a complete declared current delta. No
    # historical test is silently aimed at an expanded tree or private Git ID.
    ui_delta = load('s03_declared_one_css_successor', HERE / 'ui_delta.py')
    git = lambda *args: subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), *args], text=True,
        env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))
    baseline = declaration['public_base_commit']
    if git('rev-parse', baseline + '^{tree}').strip() != declaration['public_base_tree']:
        raise ValueError('S03_BROWSER4_PUBLIC_BASE_TREE_CHANGED')
    ui = declaration['prepared_UI_public_alias']
    if git('rev-parse', ui + '^{tree}').strip() != declaration['prepared_UI_tree']:
        raise ValueError('S03_BROWSER4_PUBLIC_UI_TREE_CHANGED')
    frozen_paths = git('diff', '--name-only', baseline, ui).splitlines()
    if frozen_paths != declaration['frozen_public_UI_paths']:
        raise ValueError('S03_BROWSER4_COMPLETE_FROZEN_PUBLIC_UI_BASELINE_REQUIRED')
    for name in frozen_paths:
        retained = subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), 'show', ui + ':' + name],
            env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))
        if (ROOT / name).read_bytes() != ui_delta.expected(ROOT, HERE, name, retained):
            raise ValueError('S03_BROWSER4_FROZEN_PUBLIC_UI_OR_SOURCE38_CHANGED:' + name)
    covered = {entry['path'] for entry in files} | {str((HERE / 'SOURCE.json').relative_to(ROOT))}
    changed = set(git('diff', '--name-only', baseline).splitlines())
    untracked = set(git('ls-files', '--others', '--exclude-standard').splitlines())
    declared_inputs = declaration.get('exact_untracked_inputs', {})
    for name, pin in declared_inputs.items():
        path = ROOT / name
        if path.exists():
            raw = path.read_bytes()
            if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
                raise ValueError('S03_BROWSER4_EXACT_HISTORICAL_INPUT_CHANGED:' + name)
    namespace = str(HERE.relative_to(ROOT)) + '/'
    parent = json.loads((HERE / 'FROZEN_BROWSER_PARENT.json').read_bytes())
    if declaration['frozen_browser_parent_paths'] != sorted(parent['files']):
        raise ValueError('S03_BROWSER4_EXACT_FROZEN_CBB_PARENT_REQUIRED')
    for name, pin in parent['files'].items():
        raw = (ROOT / name).read_bytes()
        if len(raw) != pin['bytes'] or sha256(raw).hexdigest() != pin['sha256']:
            raise ValueError('S03_BROWSER4_FROZEN_CBB_PARENT_CHANGED:' + name)
    allowed_changes = set(frozen_paths) | set(parent['files']) | {path for path in covered if path.startswith(namespace)}
    allowed_changes.add('.github/workflows/cp7-current-s03-browser4-lawful.yml')
    qualified_inputs = json.loads((HERE / 'QUALIFIED_SOURCE_INPUTS.json').read_bytes())
    allowed_changes.update(qualified_inputs['canonical_new_qualifier_paths'])
    runtime = json.loads((HERE / 'RUNTIME_SOURCE.json').read_bytes())
    allowed_changes.update(runtime['runtime_files'])
    allowed_changes.add(runtime['package_entry']['path'])
    if sorted(allowed_changes) != declaration['allowed_current_delta']:
        raise ValueError('S03_BROWSER4_EXACT_OWN_NAMESPACE_AND_WORKFLOW_ALLOCATION_REQUIRED')
    if not changed <= allowed_changes:
        raise ValueError('S03_BROWSER4_UNDECLARED_CURRENT_WHOLE_SOURCE_DELTA')
    unknown = untracked - allowed_changes - set(declared_inputs)
    outputs = load('s03_browser4_closed_generated_output_admission', HERE / 'output_admission.py')
    accepted_outputs, output_proof = outputs.admit(ROOT, HERE, unknown)
    if not unknown <= accepted_outputs:
        raise ValueError('S03_BROWSER4_UNDECLARED_CURRENT_WHOLE_SOURCE_DELTA:' + repr(sorted(unknown - accepted_outputs)))
    inventory = load('s03_browser4_closed_static_source_inventory', HERE / 'source_inventory.py')
    if declared_inputs != inventory.historical_inputs(ROOT):
        raise ValueError('S03_BROWSER4_DECLARED_INPUTS_MUST_EQUAL_EXACT28_INHERITED_NONCODE_ORIGINALS')
    original_files = {entry['path'] for entry in files}
    found, proof = inventory.inventory(ROOT, original_files, ROOT / 'scripts', (HERE / 'SOURCE.json',))
    # The 28 predeclared, separately byte-checked historical inputs may be
    # materialized after the first source-only gate. They contain no Python.
    if found - original_files - set(declared_inputs) or proof != declaration['inherited_import_inventory']:
        raise ValueError('S03_BROWSER4_IMPORTED_QUALIFIER_OR_ORACLE_SOURCE_NOT_EXPLICITLY_PINNED')
    for item in declaration['physical_UI8_baseline']:
        original = (ROOT / item['retained']).read_bytes()
        if sha256(original).hexdigest() != item['sha256'] or (ROOT / item['live']).read_bytes() != ui_delta.expected(ROOT, HERE, item['live'], original):
            raise ValueError('S03_BROWSER4_PHYSICAL_FROZEN_UI_BASELINE_CHANGED:' + item['live'])
    current_ui = ui_delta.verify(ROOT, HERE)
    if declaration['current_UI_delta'] != current_ui or declaration['current_UI_product_alias'] != current_ui['public_commit']:
        raise ValueError('S03_BROWSER4_EXACT_CURRENT_UI_DELTA_REQUIRED')
    config = json.loads((HERE / 'CONFIG.json').read_bytes())
    if config['case_ids'] != declaration['case_ids'] or len(set(config['case_ids'])) != 4:
        raise ValueError('S03_BROWSER4_EXACT_FOUR_IDS_REQUIRED')
    if config.get('normal_App_only') is not True or config.get('Enteng_or_hosted') is not False:
        raise ValueError('S03_BROWSER4_NORMAL_APP_LOOPBACK_ONLY')
    load('s03_browser4_lawful_counted_source_derivation', HERE / 'derive_successor.py').verify()
    accepted = load('s03_browser4_exact_current475_physical_inputs', HERE / 'accepted_inputs.py')
    accepted.static(ROOT, HERE, config)
    return dict(status='SOURCE_PASS', exact_sources=len(files), config=config,
        generated_output_provenance_only=output_proof, fresh_Native_Auth_HTTP_race_browser_cases=0, production_go=False)


def admitted():
    checked = check()
    config = checked['config']
    if os.environ.get('AUDITOR_UI_MODE', 'DISPOSABLE').upper() != 'DISPOSABLE':
        raise ValueError('S03_BROWSER4_ENTENG_OR_HOSTED_FORBIDDEN')
    # Before ERP imports, raw-file access outside the source closure, GET or DB.
    if (config.get('actual_execution_authorized') is not True or config.get('backend_binding') is None
            or config.get('accepted_originals') is None):
        raise ValueError('S03_BROWSER4_CLOSED_REQUIRES_EXACT_BACKEND14_FULL_RESTORE_ALL5_ORIGINALS')
    binder = load('s03_browser4_actual_original_binder', HERE / 'proof_binder.py')
    return binder.admit(ROOT, HERE, config, checked)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-actual', action='store_true')
    args = parser.parse_args()
    result = admitted() if args.require_actual else check()
    print(json.dumps(dict(status=result['status'], actual_new_Native_Auth_browser_cases=0,
        production_go=False)))
