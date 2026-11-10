"""Exact physical source closure for the reviewed Mandor 15+2 evidence.

This is a closed source preparation route. It does not admit the financial
runtime or rewrite the historical single-run contract.
"""
from hashlib import sha1
from pathlib import Path
import importlib.util
import json


HERE = Path(__file__).resolve().parent
BACKEND = dict(head='a0e7d5616a0ac470876409d31c41388159f17692',
               tree='9e4cea296f2370d7ead31a6ac2b05c132fb09521')
BROWSER = dict(head='e63c758990f54dbec4e635ecf3d53c6e80b03041',
               tree='c7634a3a39254c08894ea1ba5ea0f1b8fc2c7b7a')
PRODUCT_CSS = 'src/payroll-connected.css'
BROWSER_DELTA = frozenset((
    '.github/workflows/cp7-mandor-shop-native17.yml',
    'scripts/current-mandor-shop-native-qualification/mobile_layout_diagnostic.mjs',
    'scripts/current-mandor-shop-native-qualification/mobile_layout_fixture.mjs',
    'scripts/current-mandor-shop-native-qualification/mobile_transaction_focus.py',
    PRODUCT_CSS,
))
EVIDENCE_COMMIT = '1cc838c834ebc49642f4d27274a8c5ebabb46822'
EVIDENCE_PREFIX = 'docs/cp7/sku-cumulative-source-20261110/'


def load_parent():
    spec = importlib.util.spec_from_file_location('sku_cumulative_exact_parent', HERE / 'cumulative_parent.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(fence, baseline):
    assembly = fence.assembly
    require = assembly.require
    parent = load_parent()
    require(all(getattr(assembly.admission, name) is None for name in assembly.admission.GATES),
            'SKU_CUMULATIVE_SOURCE_ALL_FINANCIAL_GATES_MUST_BE_CLOSED')
    root_raw = (HERE / 'MANDOR17_PARENT_ROOT_ACTUAL_INTAKE.json').read_bytes()
    root = parent.verify(root_raw)
    value = json.loads((HERE / 'CUMULATIVE_SOURCE_MAP.json').read_bytes())
    require(value['classification'] == 'EXACT_CUMULATIVE_SOURCE_PREPARATION_NOT_QUALIFICATION'
            and value['backend'] == BACKEND and value['browser'] == BROWSER
            and value['parent_root'] == parent.pin(root_raw)
            and root['head'] == BACKEND['head'] and root['tree'] == BACKEND['tree']
            and value['runtime_admission'] is False and value['independent_acceptance'] is False,
            'SKU_CUMULATIVE_EXACT_SOURCE_IDENTITIES_REQUIRED')
    for identity in (BACKEND, BROWSER, dict(head=fence.MANDOR_BASE, tree=fence.MANDOR_BASE_TREE),
                     dict(head=fence.MANDOR_HEAD, tree=fence.MANDOR_TREE)):
        require(assembly.git('rev-parse', identity['head'] + '^{tree}').decode().strip() == identity['tree'],
                'SKU_CUMULATIVE_IMMUTABLE_GIT_TREE_REQUIRED')

    def delta(before, after):
        return set(assembly.git('diff', '--name-only', before, after, '--').decode().splitlines())

    before, backend, browser = (fence.entries(tree) for tree in
                               (fence.MANDOR_BASE_TREE, BACKEND['tree'], BROWSER['tree']))
    prepared = delta(fence.MANDOR_BASE, fence.MANDOR_HEAD)
    adopted = delta(fence.MANDOR_HEAD, BACKEND['head'])
    all_backend = delta(fence.MANDOR_BASE, BACKEND['head'])
    require(len(prepared) == 92 and len(adopted) == 33
            and set(value['backend_adoption_paths']) == adopted
            and all_backend == prepared | adopted == set(value['backend_files']),
            'SKU_CUMULATIVE_COMPLETE_33_PATH_BACKEND_DELTA_REQUIRED')
    require(delta(BACKEND['head'], BROWSER['head']) == BROWSER_DELTA
            and set(value['browser_product_files']) == {PRODUCT_CSS},
            'SKU_CUMULATIVE_EXACT_PAIRED_BROWSER_PRODUCT_DELTA_REQUIRED')
    require(set(value['browser_build_inputs']) == fence.BUILD_INPUTS
            and all(value['browser_build_inputs'][name] == backend[name] == browser[name]
                    for name in fence.BUILD_INPUTS),
            'SKU_CUMULATIVE_BROWSER_BUILD_INPUT_CHANGED')

    def physical(name, row, expected_before, expected_after):
        require(row['before'] == expected_before and row['after'] == expected_after,
                'SKU_CUMULATIVE_EXACT_BEFORE_AFTER_REQUIRED:' + name)
        path = fence.ROOT / name
        require(path.is_file() and not any(part.is_symlink() for part in (path, *path.parents)),
                'SKU_CUMULATIVE_REGULAR_SOURCE_REQUIRED:' + name)
        raw = path.read_bytes()
        require(parent.pin(raw) == row['pin']
                and sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == expected_after['blob']
                and bool(path.stat().st_mode & 0o111) == (expected_after['mode'] == '100755'),
                'SKU_CUMULATIVE_EVERY_PHYSICAL_SOURCE_BYTE_REQUIRED:' + name)
        return expected_after

    adopted_files = {}
    for name, row in value['backend_files'].items():
        require(before.get(name) == baseline.get(name), 'SKU_CUMULATIVE_BASELINE_CHANGED:' + name)
        adopted_files[name] = physical(name, row, before.get(name), backend[name])
    for name, row in value['browser_product_files'].items():
        adopted_files[name] = physical(name, row, backend[name], browser[name])

    # Published replay documents are inputs, not arbitrary extra source files.
    evidence = {name: identity for name, identity in fence.entries(EVIDENCE_COMMIT).items()
                if name.startswith(EVIDENCE_PREFIX)}
    require(len(evidence) == 9 and set(value['evidence_files']) == set(evidence),
            'SKU_CUMULATIVE_EXACT_PUBLISHED_EVIDENCE_SET_REQUIRED')
    for name, row in value['evidence_files'].items():
        physical(name, row, None, evidence[name])
    proof = dict(backend=BACKEND, paired_browser=BROWSER, backend_adoption_paths=33,
                 current_backend_paths=len(all_backend), paired_browser_product_paths=1,
                 original_failed_run=root['cumulative_evidence']['original_run'],
                 successful_paired_browser_run=root['cumulative_evidence']['paired_browser_run'],
                 parent_root=parent.pin(root_raw), runtime_admission=False,
                 independent_acceptance=False, actual_ERP_cases=0)
    return adopted_files, set(evidence), proof
