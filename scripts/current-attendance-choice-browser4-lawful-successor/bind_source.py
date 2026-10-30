"""Bind complete declared current bytes, without changing any old source or acceptance.

Run locally after review. It never imports ERP, opens SQL, fetches, publishes,
or converts a prepared dependency into a qualified backend.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FROZEN = ROOT / 'scripts/current-attendance-choice-browser4-qualification'
BASE = 'a5774f59ce67fd18427a9aa700ee5e34fdece5b3'
UI_ALIAS = '598dfe935e97ab7a43d63cd34d9b3b6abd7c7496'
UI_TREE = '95d2abc716e0f9af12f5d0a55df29b6a50082868'
NAMESPACE = str(HERE.relative_to(ROOT))
WORKFLOW = '.github/workflows/cp7-current-s03-browser4-lawful.yml'


def git(*args):
    return subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), *args], text=True,
        env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))


def pin(path):
    raw = (ROOT / path).read_bytes()
    return dict(path=path, bytes=len(raw), sha256=sha256(raw).hexdigest())


def main():
    if git('rev-parse', UI_ALIAS + '^{tree}').strip() != UI_TREE:
        raise ValueError('S03_BROWSER4_EXACT_PUBLIC_PREPARED_UI_BASELINE_REQUIRED')
    config = json.loads((HERE / 'CONFIG.json').read_bytes())
    baseline_files = git('diff', '--name-only', BASE, UI_ALIAS).splitlines()
    for name in baseline_files:
        retained = subprocess.check_output(['/usr/bin/git', '-C', str(ROOT), 'show', UI_ALIAS + ':' + name],
            env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))
        if (ROOT / name).read_bytes() != retained:
            raise ValueError('S03_BROWSER4_FROZEN_PUBLIC_UI_OR_SOURCE38_CHANGED:' + name)
    own = [str(path.relative_to(ROOT)) for path in HERE.rglob('*') if path.is_file()
        and path != HERE / 'SOURCE.json' and '__pycache__' not in path.parts and path.suffix != '.pyc']
    inherited = [
        'docs/cp7/framework-v2/verification/semantic_contract.py',
        'docs/cp7/framework-v2/contracts/analysis.schema.json',
        'scripts/current-vendor-receivable-qualification/probe.py',
        'scripts/current-vendor-receivable-qualification/native_runner.py',
        'scripts/current-attendance-period-choice-qualification/fixtures.py',
        'scripts/current-attendance-period-choice-qualification/cases.py',
        'scripts/current-attendance-period-choice-native11-qualification/proof_inputs.py',
        'scripts/current-attendance-period-choice-native11-qualification/argv_boundary.py',
        'scripts/current-attendance-choice-mount-ui/browser_adapter.py',
        'scripts/current-attendance-choice-mount-ui/SOURCE.json',
        'scripts/ow04-payment-current-qualification/copy_authority.py',
        'scripts/cp6_auditor_modes.py', 'scripts/cp6_auditor_browser_host.mjs',
        'scripts/cp6_auditor_business_day.py', 'scripts/cp6_auditor_business_day.mjs',
        'scripts/current-vendor-money-browser/visual.mjs', 'scripts/current-vendor-money-browser/gradient.mjs',
        'scripts/cp7_r3_hpp_pool_cases.py', 'scripts/cp7_finance_analysis_cases.py',
        'scripts/cp7_cp17_fix_cases.py', 'scripts/cp7_settlement_cases.py', 'scripts/cp6_bd_probe.py',
        'scripts/cp7_ow04_restore_bundle.py',
        '.github/workflows/cp7-current-vendor-receivable-native.yml',
    ]
    extra = config.get('backend_binding', {}).get('additional_exact_sources', {}) if config.get('backend_binding') else {}
    for name, expected in extra.items():
        actual = pin(name)
        if actual['bytes'] != expected['bytes'] or actual['sha256'] != expected['sha256']:
            raise ValueError('S03_BROWSER4_DECLARED_QUALIFIED_BACKEND_SOURCE_CHANGED:' + name)
    parent = json.loads((HERE / 'FROZEN_BROWSER_PARENT.json').read_bytes())
    for name, expected in parent['files'].items():
        actual = pin(name)
        if (actual['bytes'], actual['sha256']) != (expected['bytes'], expected['sha256']):
            raise ValueError('S03_BROWSER4_FROZEN_CBB_PARENT_CHANGED:' + name)
    inherited_source = json.loads((FROZEN / 'SOURCE.json').read_bytes())
    covered = set(baseline_files + own + inherited + list(extra)) | set(parent['files'])
    covered.update(row['path'] for row in inherited_source['files'])
    accepted_inputs = json.loads((HERE / 'QUALIFIED_SOURCE_INPUTS.json').read_bytes())
    covered.update(accepted_inputs['canonical_new_qualifier_paths'])
    covered.update(json.loads((HERE / 'BUILD_OUTPUT_CONTRACT.json').read_bytes())['producer_files'])
    # Explicit current inherited source inventory from the public prepared
    # qualifier plus static imports/literal paths. No metadata is used as an
    # execution verdict and no absent author files are copied into this tree.
    prepared_author = json.loads((HERE / 'PREPARED_AUTHOR_BINDING.json').read_bytes())
    retained_source = (HERE / 'retained-source-metadata/PREPARED_NATIVE14_SOURCE.json').read_bytes()
    if sha256(retained_source).hexdigest() != prepared_author['qualifier_source']['sha256']:
        raise ValueError('S03_BROWSER4_PREPARED_PUBLIC_SOURCE_REFERENCE_CHANGED')
    reference = json.loads(retained_source)
    covered.update(name for name in reference['files'] if (ROOT / name).is_file())
    spec = importlib.util.spec_from_file_location('s03_browser4_source_inventory_only', HERE / 'source_inventory.py')
    inventory = importlib.util.module_from_spec(spec);spec.loader.exec_module(inventory)
    covered, import_proof = inventory.inventory(ROOT, covered, ROOT / 'scripts', (HERE / 'SOURCE.json',))
    if (ROOT / WORKFLOW).is_file():
        covered.add(WORKFLOW)
    current = set(git('diff', '--name-only', BASE).splitlines())
    allowed_changes = set(baseline_files + own + [WORKFLOW, NAMESPACE + '/SOURCE.json']) | set(parent['files'])
    accepted_inputs = json.loads((HERE / 'QUALIFIED_SOURCE_INPUTS.json').read_bytes())
    allowed_changes.update(accepted_inputs['canonical_new_qualifier_paths'])
    selected_runtime = json.loads((HERE / 'RUNTIME_SOURCE.json').read_bytes())
    allowed_changes.update(selected_runtime['runtime_files'])
    allowed_changes.add(selected_runtime['package_entry']['path'])
    if not current <= allowed_changes:
        raise ValueError('S03_BROWSER4_UNALLOCATED_SOURCE_OUTSIDE_EXACT_BASELINE_OR_OWN_NAMESPACE:' + ','.join(sorted(current - allowed_changes)))
    old = json.loads((ROOT / 'scripts/current-attendance-choice-mount-ui/SOURCE.json').read_bytes())
    physical = []
    for name, expected in old['copied_eight_exact_sha256'].items():
        retained = str(FROZEN.relative_to(ROOT)) + '/retained-ui8/' + name
        if pin(retained)['sha256'] != expected or (ROOT / name).read_bytes() != (ROOT / retained).read_bytes():
            raise ValueError('S03_BROWSER4_PHYSICAL_UI8_BASELINE_CHANGED:' + name)
        physical.append(dict(live=name, retained=retained, sha256=expected))
    inputs = inventory.historical_inputs(ROOT)
    value = dict(contract_version='cp7.s03-browser4-source.v1',
        classification='COMPLETE_DECLARED_CURRENT_SOURCE_NOT_ACTUAL_BROWSER_OR_BACKEND_ACCEPTANCE',
        public_base_commit=BASE, public_base_tree=git('rev-parse', BASE + '^{tree}').strip(),
        prepared_UI_public_alias=UI_ALIAS, prepared_UI_tree=UI_TREE,
        UI_alias_is_runtime_prerequisite=False, physical_UI8_baseline=physical,
        frozen_public_UI_paths=baseline_files,
        frozen_browser_parent_paths=sorted(parent['files']),
        frozen_browser_parent_source=pin(str((FROZEN / 'SOURCE.json').relative_to(ROOT))),
        inherited_import_inventory=import_proof,
        prepared_qualifier_reference_is_runtime_prerequisite=False,
        prepared_canonical_author_files=len(prepared_author['author_binding']['files']),
        case_ids=config['case_ids'], files=[pin(name) for name in sorted(covered)],
        allowed_current_delta=sorted(allowed_changes),
        exact_untracked_inputs=inputs, old_frozen_mount16_reexecuted_against_expanded_HEAD=False,
        private_abdbc_Git_required=False, actual_backend14_accepted=config['accepted_originals'] is not None,
        actual_Native_Auth_browser_cases=0, production_go=False)
    (HERE / 'SOURCE.json').write_text(json.dumps(value, indent=2) + '\n')
    print(json.dumps(dict(exact_files=len(value['files']), whole_current_delta=len(current),
        source_sha256=sha256((HERE / 'SOURCE.json').read_bytes()).hexdigest(), actual_executed=0)))


if __name__ == '__main__':
    main()
