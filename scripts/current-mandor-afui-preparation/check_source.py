"""Whole current candidate fence; sparse observation never grants runtime."""
from hashlib import sha1, sha256
from pathlib import Path
import argparse
import ast
import importlib.util
import json
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('mandor_current_exact_caller_routes', HERE / 'routes.py')
routes = importlib.util.module_from_spec(spec)
spec.loader.exec_module(routes)

UI_HEAD = '1c66a74295eae2f09b7535619325e4d023942e19'
UI_TREE = '587760d45b5026f27d19cf57adce92330fff3df3'
UI_BEFORE = '601afd5adbb167991b018eb24688d5ecb8fb3173'
UI_AFTER = '15dc4bde83e1ac74871f8d4aaf005e9e36445aeb'
UI_PATHS = frozenset(('src/ConnectedInitialImportPage.tsx', 'src/ConnectedPocketFabricPage.tsx', 'src/initial-import.css'))
BUILD_INPUTS = frozenset(('index.html', 'package-lock.json', 'package.json', 'tsconfig.app.json',
                         'tsconfig.contracts.json', 'tsconfig.json', 'vite.config.ts'))
ACTIVE_WORKFLOW = '.github/workflows/cp7-mandor-shop-native17.yml'
PARENT_ROOT = routes.NS + 'AFUI15_PARENT_ROOT_ACTUAL_INTAKE.json'
COMPONENT_ADMISSION = 'scripts/cp7_mandor_shop/admission.py'
COMPONENT_SOURCE = 'scripts/cp7_mandor_shop/SOURCE.json'
PREPARED = 'CURRENT_AFUI_MANDOR_SOURCE_PREPARATION_NOT_RUNTIME'
ADOPTED = 'CURRENT_AFUI_MANDOR_ACTUAL_PARENT_BOUND_SOURCE'


def require(value, reason):
    if not value:
        raise ValueError(reason)


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))


def entries(tree):
    result = {}
    for item in git('ls-tree', '-rz', tree).split(b'\0'):
        if not item:
            continue
        meta, name = item.split(b'\t', 1)
        mode, kind, blob = meta.decode().split()
        require(kind == 'blob' and mode in ('100644', '100755'), 'MANDOR_CURRENT_REGULAR_GIT_BLOB_REQUIRED')
        result[name.decode()] = dict(mode=mode, blob=blob)
    return result


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def bind_empty_values(raw, values):
    text = raw.decode()
    for key, value in values.items():
        old = f'{key}=None\n'
        require(text.count(old) == 1, 'MANDOR_ACTUAL_PARENT_BINDING_EXACT_ANCHOR:' + key)
        text = text.replace(old, f'{key}={value!r}\n', 1)
    return text.encode()


def actual_adoption(manifest):
    adoption = manifest['actual_Afui_adoption']
    require(set(adoption) == {PARENT_ROOT, ACTIVE_WORKFLOW}, 'MANDOR_ONLY_ROOT_AND_OWNING_WORKFLOW_ADDITIONS')
    for name, expected in adoption.items():
        path = ROOT / name
        require(path.is_file() and not path.is_symlink() and pin(path.read_bytes()) == expected,
                'MANDOR_EXACT_ACTUAL_ADOPTION_SOURCE:' + name)
    path = HERE / 'workflow.py'
    require(pin(path.read_bytes()) == manifest['files'][str(path.relative_to(ROOT))],
            'MANDOR_EXACT_CURRENT_OWNING_WORKFLOW_CHECKER')
    spec = importlib.util.spec_from_file_location('mandor_actual_source_workflow', path)
    workflow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(workflow)
    checked = workflow.check(owning=True)
    receipt = json.loads((ROOT / PARENT_ROOT).read_bytes())
    require(receipt['head'] == checked['parent_head'] == routes.AFUI and receipt['tree'] == routes.AFUI_TREE
            and receipt['run_id'] == checked['parent_run'] and receipt['job_id'] == checked['parent_job']
            and all(type(receipt[key]) is int and receipt[key] > 0 for key in ('run_id', 'job_id', 'artifact_id')),
            'MANDOR_ACTUAL_ROOT_MUST_MATCH_EXACT_FROZEN_SOURCE_AND_RUN')
    bindings = dict(PARENT_RUN=receipt['run_id'], PARENT_JOB=receipt['job_id'],
                    PARENT_ROOT_PIN=adoption[PARENT_ROOT], RUNTIME_ENTRY=routes.NS + 'qualification.py')
    contract = {key: receipt[key] for key in ('status', 'actual_Native_cases', 'actual_Auth_HTTP_cases',
                'actual_two_session_races', 'actual_browser_cases', 'actual_business_cases',
                'complete15_qualified', 'prior_runs_aggregated')}
    component = bind_empty_values(git('show', routes.BASE + ':' + COMPONENT_ADMISSION),
        dict(PARENT_HEAD=routes.AFUI, PARENT_TREE=routes.AFUI_TREE, PARENT_ROOT_CONTRACT=contract, **bindings))
    baseline = json.loads(git('show', routes.BASE + ':' + COMPONENT_SOURCE))
    baseline['files'][COMPONENT_ADMISSION] = pin(component)
    source = (json.dumps(baseline, indent=2) + '\n').encode()
    return bindings, {COMPONENT_ADMISSION: component, COMPONENT_SOURCE: source}, set(adoption)


def selective_ui(value, base, approved):
    require(value['head'] == UI_HEAD and value['tree'] == UI_TREE
            and value['before_src_tree'] == UI_BEFORE and value['after_src_tree'] == UI_AFTER,
            'MANDOR_ONLY_EXACT_SELECTIVE_B_UI_SOURCE')
    require(set(value['files']) == UI_PATHS and set(value['root_build_inputs']) == BUILD_INPUTS,
            'MANDOR_ONLY_THREE_SELECTIVE_UI_PATHS_AND_COMPLETE_BUILD_INPUTS')
    result = {}
    for name, row in value['files'].items():
        require(row['before'] == base[name] and row['after'] == approved[name]
                and row['before']['mode'] == row['after']['mode'] == '100644',
                'MANDOR_EXACT_UI_BEFORE_AND_APPROVED_AFTER_BLOBS:' + name)
        path = ROOT / name
        require(path.is_file() and not path.is_symlink(), 'MANDOR_REGULAR_APPROVED_UI_FILE:' + name)
        raw = path.read_bytes()
        require(dict(bytes=len(raw), sha256=sha256(raw).hexdigest()) == row['pin']
                and sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == row['after']['blob'],
                'MANDOR_APPROVED_UI_EVERY_BYTE_REQUIRED:' + name)
        result[name] = row['after']
    for name, identity in value['root_build_inputs'].items():
        require(identity == base[name] == approved[name], 'MANDOR_UI_BUILD_INPUT_CHANGED:' + name)
    return result


def source(*, allow_sparse_observation=False):
    manifest = json.loads((HERE / 'SOURCE.json').read_bytes())
    adopted = 'actual_Afui_adoption' in manifest
    status = ADOPTED if adopted else PREPARED
    require(manifest['classification'] == status
            and type(manifest['actual_ERP_cases']) is int and manifest['actual_ERP_cases'] == 0
            and manifest['production_go'] is False,
            'MANDOR_CURRENT_SOURCE_ONLY_MANIFEST_REQUIRED')
    require(not adopted or not allow_sparse_observation, 'MANDOR_ACTUAL_PARENT_REQUIRES_FULL_SOURCE_CHECKOUT')
    require(git('rev-parse', routes.BASE + '^{tree}').decode().strip() == routes.BASE_TREE
            and git('rev-parse', routes.AFUI + '^{tree}').decode().strip() == routes.AFUI_TREE,
            'MANDOR_CURRENT_EXACT_COMPLETE_BASE_AND_AFUI_TREES_REQUIRED')
    bindings, replacements, additions = actual_adoption(manifest) if adopted else ({}, {}, set())
    base, afui = entries(routes.BASE_TREE), entries(routes.AFUI_TREE)
    copied = set(git('diff', '--name-only', routes.PRIOR_AFUI, routes.AFUI, '--').decode().splitlines())
    require(copied == set(manifest['exact_current_Afui_files']) and len(copied) == 44,
            'MANDOR_CURRENT_COMPLETE_FORTY_FOUR_AFUI_SOURCE_PATHS_REQUIRED')
    for name in copied:
        require(name in afui and afui[name] == manifest['exact_current_Afui_files'][name],
                'MANDOR_CURRENT_EXACT_QUALIFIED_AFUI_BLOB_REQUIRED:' + name)
    caller_paths = {routes.NS + name for name in routes.PINS}
    for name in routes.PINS:
        path = routes.NS + name
        derived, proof = routes.derive(git('show', routes.BASE + ':' + path), name)
        if adopted and name == 'admission.py':
            derived = bind_empty_values(derived, bindings)
        require((ROOT / path).read_bytes() == derived and manifest['caller_derivations'][name] == proof,
                'MANDOR_CURRENT_EXACT_REVERSIBLE_CALLER_BYTES_REQUIRED:' + path)
    for name, expected in manifest['files'].items():
        path = ROOT / name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts
                and path.is_file() and not path.is_symlink(),
                'MANDOR_CURRENT_REGULAR_DECLARED_SOURCE_REQUIRED:' + name)
        raw = path.read_bytes()
        require(dict(bytes=len(raw), sha256=sha256(raw).hexdigest()) == expected,
                'MANDOR_CURRENT_DECLARED_SOURCE_CHANGED:' + name)
    namespace = str(HERE.relative_to(ROOT)) + '/'
    declared = set(manifest['files']) | {namespace + 'SOURCE.json'}
    own = declared - caller_paths
    require(all(name.startswith(namespace) for name in own), 'MANDOR_CURRENT_SINGLE_ADDITIVE_PREPARATION_NAMESPACE')
    expected = dict(base)
    expected.update({name: afui[name] for name in copied})
    for name, raw in replacements.items():
        require(expected[name]['mode'] == '100644', 'MANDOR_ACTUAL_ADOPTION_REGULAR_SOURCE_ONLY')
        expected[name] = dict(mode='100644', blob=sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest())
    require(git('rev-parse', UI_HEAD + '^{tree}').decode().strip() == UI_TREE
            and git('rev-parse', routes.BASE + ':src').decode().strip() == UI_BEFORE
            and git('rev-parse', UI_HEAD + ':src').decode().strip() == UI_AFTER,
            'MANDOR_COMPLETE_APPROVED_UI_TREE_IDENTITIES_REQUIRED')
    expected.update(selective_ui(manifest['selective_B_UI'], base, entries(UI_TREE)))
    absent = []
    checked = 0
    for name, identity in expected.items():
        if name in caller_paths:
            continue
        path = ROOT / name
        require(not path.is_symlink(), 'MANDOR_CURRENT_PARENT_SYMLINK_REFUSED:' + name)
        if not path.is_file():
            absent.append(name)
            continue
        raw = path.read_bytes()
        require(sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest() == identity['blob'],
                'MANDOR_CURRENT_UNDECLARED_PARENT_CHANGE:' + name)
        checked += 1
    require(allow_sparse_observation or not absent, 'MANDOR_CURRENT_FULL_RUNTIME_SOURCE_MATERIALIZATION_REQUIRED')
    all_paths = {name.decode() for name in git('ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0') if name}
    require(not (additions & (set(expected) | own)) and all_paths == set(expected) | own | additions,
            'MANDOR_CURRENT_EXACT_WHOLE_CANDIDATE_FILE_SET_REQUIRED')
    if not adopted:
        tree = ast.parse((ROOT / routes.NS / 'admission.py').read_bytes())
        values = {target.id: ast.literal_eval(node.value) for node in tree.body
                  if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
                  for target in node.targets if isinstance(target, ast.Name)}
        require(values['PARENT_HEAD'] == routes.AFUI and values['PARENT_TREE'] == routes.AFUI_TREE
                and values['PARENT_RUN'] is None and values['PARENT_JOB'] is None
                and values['PARENT_ROOT_PIN'] is None and values['RUNTIME_ENTRY'] is None,
                'MANDOR_CURRENT_PENDING_AFUI_PARENT_MUST_REMAIN_CLOSED')
    parent = (dict(accepted_current_Afui_head=routes.AFUI, accepted_current_Afui_run=bindings['PARENT_RUN'])
              if adopted else dict(pending_current_Afui_head=routes.AFUI))
    return dict(status=status, base_head=routes.BASE, **parent,
                exact_current_Afui_paths=len(copied),
                exact_reversible_callers=len(routes.PINS), parent_blob_identities=len(expected),
                materialized_parent_files_checked=checked, absent_sparse_parent_files=len(absent),
                full_runtime_materialization_still_required=bool(absent), exact_additive_preparation_files=len(own),
                retained_current_UI_and_build_inputs_unchanged=False,
                exact_approved_B_UI_files=3, complete_approved_UI_src_tree=UI_AFTER,
                all_other_parent_sources_and_build_inputs_unchanged=True,
                historical_preparation_reports_relabelled=False, financial_assertions_and_recovery_unchanged=True,
                actual_parent_root_adopted=adopted, actual_ERP_cases=0, production_go=False, independent_acceptance=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--observe-sparse', action='store_true')
    args = parser.parse_args()
    print(json.dumps(source(allow_sparse_observation=args.observe_sparse), sort_keys=True))
