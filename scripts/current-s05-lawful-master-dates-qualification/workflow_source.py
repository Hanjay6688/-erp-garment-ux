"""Five step bindings over the exact complete successful-install 911 workflow."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import importlib.util
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-s05-lawful-master-dates-qualification'
OLD_PATH = '.github/workflows/cp7-current-s05-public-default-acl.yml'
PATH = '.github/workflows/cp7-current-s05-lawful-master-dates.yml'
BRANCH = 'astra-a/s05-lawful-master-dates-20261030'
PARENT = '855e45c56e0ea225675a0eefee777905e2611bf6d58f617eec69553ec3c7615b'


def generated(raw, repo=ROOT):
    if sha256(raw).hexdigest() != PARENT:
        raise ValueError('S05_EXACT_911_WORKFLOW_REQUIRED')
    repo = Path(repo)
    path = repo/'scripts/current-s05-public-default-acl-qualification/workflow_source.py'
    spec = importlib.util.spec_from_file_location('s05_lawful_unchanged_parent_workflow', path)
    old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
    old.checked(raw.decode(), repo)
    parent = yaml.safe_load(raw)
    value = deepcopy(parent)
    value['name'] = 'CP7 S05 lawful master dates Native10 and complete restore'
    value['on'] = {'push': {'branches': [BRANCH], 'paths': [PATH, NS+'/**']}, 'workflow_dispatch': {}}
    value['concurrency']['group'] = 'cp7-s05-lawful-master-dates-${{ github.run_id }}'
    value['jobs']['p21']['name'] = 'S05 lawful legacy master Native10 and full restoration'
    changed = []
    for step in value['jobs']['p21']['steps']:
        name = step.get('name')
        if name == 'Admit retained b0 failure, vendor11 and bounded S05 ACL sources before database':
            step.update(name='Admit exact 911 failure, lawful master premise and retained vendor11 before database',
                        run='python -B '+NS+'/check.py')
        elif name == 'Check exact public ACL source transition and successor wrapper controls':
            step.update(name='Check unchanged ACL source and lawful master-date source controls',
                        run=step['run']+"\npython -B -m unittest discover -s "+NS+" -p 'test_*.py'")
        elif name == old.ADMISSION_NAME:
            step.update(name='Admit exact vendor41c and lawful S05 fixture source before database',
                        run="python '../auditor/"+NS+"/check.py' --runtime")
        elif name == old.RUNTIME_NAME:
            step.update(name='Run exact S05 Native10 with lawful master dates and complete restore',
                        run="python '../auditor/"+NS+"/probe.py'")
        elif step.get('uses', '').startswith('actions/upload-artifact@'):
            step['with']['name'] = 'cp7-s05-lawful-master-dates-native10-${{ github.run_attempt }}'
        else:
            continue
        changed.append(name or step.get('uses'))
    if len(changed) != 5:
        raise ValueError('S05_EXACT_FIVE_WORKFLOW_STEP_BINDINGS_REQUIRED')
    text = yaml.safe_dump(value, sort_keys=False, width=1000)
    return text, dict(parent_sha256=PARENT, generated_sha256=sha256(text.encode()).hexdigest(),
                      parent_steps=len(parent['jobs']['p21']['steps']),
                      child_steps=len(value['jobs']['p21']['steps']), adapted_steps=changed,
                      unchanged_setup_all_Original_readers_clone_cleanup_upload_and_full_restore=True,
                      root_publish_branch=BRANCH, automatic_on_other_branches=False)


def checked(text, repo=ROOT):
    expected, proof = generated((Path(repo)/OLD_PATH).read_bytes(), repo)
    if text != expected:
        raise ValueError('S05_LAWFUL_WORKFLOW_CHANGED')
    return proof
