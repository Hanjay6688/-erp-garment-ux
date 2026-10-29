"""Exact b0 workflow successor; inherited setup/clone/restore/artifact logic stays."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import importlib.util
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = 'scripts/current-s05-native10-qualification'
NS = 'scripts/current-s05-public-default-acl-qualification'
REPAIR = 'scripts/current-s05-public-default-acl-repair'
OLD_PATH = '.github/workflows/cp7-current-s05-native10.yml'
PATH = '.github/workflows/cp7-current-s05-public-default-acl.yml'
PARENT_SHA256 = 'b4753798b87343817d0a63af1f51acf7d9d80f39098f95a8fbc61b11c002a986'
BRANCH = 'astra-a/s05-native10-public-default-acl-20261029'
ADMISSION_NAME = 'Admit exact vendor41c and bounded S05 public ACL successor before database'
RUNTIME_NAME = 'Run unchanged S05 Native10 with bounded public ACL repair and complete restore'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def generated(raw, repo=ROOT):
    repo = Path(repo)
    if sha256(raw).hexdigest() != PARENT_SHA256:
        raise ValueError('S05_ACL_EXACT_B0_WORKFLOW_REQUIRED')
    inherited = load('s05_acl_frozen_b0_workflow_validator', repo/OLD/'workflow_source.py')
    prior = inherited.checked(raw.decode())
    parent = yaml.load(raw, Loader=inherited.UniqueLoader)
    value = deepcopy(parent)
    value['name'] = 'CP7 S05 bounded public ACL successor Native10 and complete restore'
    value['on'] = {'push': {'branches': [BRANCH], 'paths': [PATH, NS+'/**', REPAIR+'/**',
        'scripts/cp7_accessory_standard_report/SOURCE.json',
        'scripts/cp7_accessory_standard_report/stage.py',
        'scripts/cp7_accessory_standard_report/report.sql']}, 'workflow_dispatch': {}}
    value['concurrency']['group'] = 'cp7-s05-public-default-acl-${{ github.run_id }}'
    job = value['jobs']['p21']
    job['name'] = 'S05 public ACL successor Native10 and full vendor-parent restoration'
    changes = []
    for step in job['steps']:
        name = step.get('name')
        if name == 'Admit mandatory retained vendor11 Original and all five package gates before database':
            step['name'] = 'Admit retained b0 failure, vendor11 and bounded S05 ACL sources before database'
            step['run'] = 'python -B '+NS+'/check.py'
        elif name == 'Check unchanged S05 source and wrapper controls':
            step['name'] = 'Check exact public ACL source transition and successor wrapper controls'
            step['run'] = ("python -B -m unittest discover -s "+REPAIR+" -p 'test_transition.py'\n"
                           "python -B -m unittest discover -s "+NS+" -p 'test_*.py'")
        elif name == 'Admit exact vendor41c backend3194 and frozen S05 component before database':
            step['name'] = ADMISSION_NAME
            step['run'] = "python '../auditor/"+NS+"/check.py' --runtime"
        elif name == 'Run unchanged S05 Native10, separate committed Native witness and complete restore':
            step['name'] = RUNTIME_NAME
            step['run'] = "python '../auditor/"+NS+"/probe.py'"
        elif step.get('uses', '').startswith('actions/upload-artifact@'):
            step['with']['name'] = 'cp7-s05-public-default-acl-native10-${{ github.run_attempt }}'
        else:
            continue
        changes.append(name or step.get('uses'))
    if len(changes) != 5:
        raise ValueError('S05_ACL_EXACT_FIVE_WORKFLOW_STEP_ADAPTATIONS_REQUIRED')
    text = yaml.safe_dump(value, sort_keys=False, width=1000)
    return text, dict(original_b0_workflow_sha256=PARENT_SHA256,
        generated_sha256=sha256(text.encode()).hexdigest(), parent_step_count=len(parent['jobs']['p21']['steps']),
        child_step_count=len(job['steps']), adapted_steps=changes,
        root_publish_branch=BRANCH, automatic_on_default_or_other_branches=False,
        inherited_setup_source_prerequisites_clone_cleanup_package_and_full_restore_unchanged=True,
        inherited_vendor_workflow_derivation=prior)


def checked(text, repo=ROOT):
    repo = Path(repo)
    expected, proof = generated((repo/OLD_PATH).read_bytes(), repo)
    if text != expected:
        raise ValueError('S05_ACL_GENERATED_WORKFLOW_CHANGED')
    inherited = load('s05_acl_frozen_workflow_loader', repo/OLD/'workflow_source.py')
    value = yaml.load(text, Loader=inherited.UniqueLoader)
    steps = value['jobs']['p21']['steps']
    names = [step.get('name') for step in steps]
    if names.index(ADMISSION_NAME) >= names.index('Start disposable database'):
        raise ValueError('S05_ACL_SOURCE_ADMISSION_MUST_PRECEDE_DATABASE')
    if names.index(RUNTIME_NAME) <= names.index('Clone the aligned AB state for install'):
        raise ValueError('S05_ACL_FULL_ENGINE_MUST_FOLLOW_CLONE')
    if value['concurrency']['cancel-in-progress'] is not False or any(s.get('continue-on-error') for s in steps):
        raise ValueError('S05_ACL_NO_WEAKENED_WORKFLOW_GATES')
    cleanup = next(s for s in steps if s.get('name') == 'Remove disposable database')
    upload = next(s for s in steps if s.get('uses', '').startswith('actions/upload-artifact@'))
    if cleanup.get('if') != 'always()' or upload.get('if') != 'always()' or upload['with']['path'] != 'auditor/cp6-proof/t3':
        raise ValueError('S05_ACL_FULL_ARTIFACT_AND_CLEANUP_REQUIRED')
    return proof
