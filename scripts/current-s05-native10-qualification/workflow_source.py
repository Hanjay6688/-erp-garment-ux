"""New root-published workflow from the exact workflow declared by vendor41c raw.

Runtime setup, frozen sources, preconditions, clone, cleanup and package path
stay in their original order. Only this child's source admission/run/artifact
steps replace the old vendor-specific ones. Never dispatches or publishes.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PATH = '.github/workflows/cp7-current-s05-native10.yml'
PARENT_SHA256 = 'e013bfb64da3dc55299c7273cdf1de0ee5d75dfd4df3be3a2e8fabae5d6ecca1'
ROOT_PUBLISH_BRANCH = 'astra-a/s05-native10-import-argv-20261029'
OLD_RUNTIME = 'Run fresh Native7 then actual race3 AuthHTTP1 and complete restoration'
NEW_RUNTIME = 'Run unchanged S05 Native10, separate committed Native witness and complete restore'


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in result:
            raise ValueError('S05_DUPLICATE_WORKFLOW_KEY: '+str(key))
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)


def generated(raw):
    if sha256(raw).hexdigest() != PARENT_SHA256:
        raise ValueError('S05_EXACT_VENDOR41C_WORKFLOW_BYTES_REQUIRED')
    parent = yaml.load(raw, Loader=UniqueLoader)
    result = deepcopy(parent)
    result['name'] = 'CP7 S05 accessory category report Native10 and complete restore'
    result['on'] = {'push': {'branches': [ROOT_PUBLISH_BRANCH], 'paths': [PATH, 'scripts/current-s05-native10-qualification/**']}, 'workflow_dispatch': {}}
    result['concurrency']['group'] = 'cp7-s05-native10-${{ github.run_id }}'
    job = result['jobs']['p21']
    job['name'] = 'S05 read-only Native10 and full vendor-parent restoration'
    job['env']['S05_NATIVE_CONFIRM'] = 'cp6_rollback'
    changed = []
    steps = []
    for old in parent['jobs']['p21']['steps']:
        step = deepcopy(old)
        name = step.get('name')
        if name == 'Bind exact qualified backend3194 Original':
            step = dict(name='Admit mandatory retained vendor11 Original and all five package gates before database',
                **{'working-directory': 'auditor'}, run='python -B scripts/current-s05-native10-qualification/check.py')
        elif name == 'Bind complete actual observer Native7 and all five package gates before database':
            # Exact complete current vendor11 supersedes the older Native7
            # precursor as this child's mandatory retained parent proof.
            changed.append(dict(parent_step=name, replacement='EXACT_VENDOR11_RAW_AND_PACKAGE_GATE_ABOVE'))
            continue
        elif name == 'Check vendor qualification syntax':
            step = dict(name='Check unchanged S05 source and wrapper controls', **{'working-directory': 'auditor'},
                run="python -B -m unittest discover -s scripts/current-s05-native10-qualification -p 'test_*.py'")
        elif name == 'Admit exact backend3194 parent and declared vendor delta before database':
            step = dict(name='Admit exact vendor41c backend3194 and frozen S05 component before database',
                **{'working-directory': 'writer'}, run="python '../auditor/scripts/current-s05-native10-qualification/check.py' --runtime")
        elif name == OLD_RUNTIME:
            step = dict(name=NEW_RUNTIME, **{'working-directory': 'writer'},
                run="python '../auditor/scripts/current-s05-native10-qualification/probe.py'")
        elif name == 'Preserve exact original JSON report bytes in a bounded compressed log receipt':
            step['run'] = 'python scripts/current-s05-native10-qualification/retain_reports.py'
        elif step.get('uses', '').startswith('actions/upload-artifact@'):
            step['with']['name'] = 'cp7-s05-native10-${{ github.run_attempt }}'
        if step != old:
            changed.append(dict(parent_step=name or old.get('uses'), replacement=step.get('name') or step.get('uses')))
        steps.append(step)
    job['steps'] = steps
    text = yaml.safe_dump(result, sort_keys=False, width=1000)
    return text, dict(original_sha256=PARENT_SHA256, generated_sha256=sha256(text.encode()).hexdigest(),
        parent_step_count=len(parent['jobs']['p21']['steps']), child_step_count=len(steps), replacements=changed,
        triggers=['push', 'workflow_dispatch'], root_publish_branch=ROOT_PUBLISH_BRANCH,
        automatic_on_default_or_other_branches=False,
        unchanged_runtime_setup_clone_cleanup_and_package_gates=True)


def checked(text):
    expected, proof = generated((HERE/'frozen_vendor/workflow.yml').read_bytes())
    if text != expected:
        raise ValueError('S05_GENERATED_WORKFLOW_CHANGED')
    value = yaml.load(text, Loader=UniqueLoader)
    expected_triggers = {'push': {'branches': [ROOT_PUBLISH_BRANCH], 'paths': [PATH, 'scripts/current-s05-native10-qualification/**']}, 'workflow_dispatch': {}}
    if value['on'] != expected_triggers or value['concurrency']['cancel-in-progress'] is not False:
        raise ValueError('S05_ROOT_PUBLISHED_RESTORING_WORKFLOW_REQUIRED')
    allowed = {'name', 'id', 'if', 'uses', 'with', 'run', 'env', 'shell', 'working-directory', 'continue-on-error', 'timeout-minutes'}
    steps = value['jobs']['p21']['steps']
    for step in steps:
        if set(step)-allowed or ('uses' in step) == ('run' in step):
            raise ValueError('S05_INVALID_ACTIONS_STEP')
        if step.get('continue-on-error'):
            raise ValueError('S05_NO_WEAKENED_WORKFLOW_GATES')
    names = [step.get('name') for step in steps]
    if names.index('Admit exact vendor41c backend3194 and frozen S05 component before database') >= names.index('Start disposable database'):
        raise ValueError('S05_SOURCE_ADMISSION_MUST_PRECEDE_DATABASE')
    if names.index(NEW_RUNTIME) <= names.index('Clone the aligned AB state for install'):
        raise ValueError('S05_PACKAGE_RUN_MUST_FOLLOW_ALIGNED_CLONE')
    cleanup = next(s for s in steps if s.get('name') == 'Remove disposable database')
    upload = next(s for s in steps if s.get('uses', '').startswith('actions/upload-artifact@'))
    if cleanup.get('if') != 'always()' or upload.get('if') != 'always()' or upload['with']['path'] != 'auditor/cp6-proof/t3':
        raise ValueError('S05_FULL_ARTIFACT_AND_CLEANUP_REQUIRED')
    return proof


if __name__ == '__main__':
    text, _ = generated((HERE/'frozen_vendor/workflow.yml').read_bytes())
    (ROOT/PATH).write_text(text)
