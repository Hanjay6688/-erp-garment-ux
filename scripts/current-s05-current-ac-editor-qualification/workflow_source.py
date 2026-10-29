"""Five bounded step bindings over the exact complete cdbdea workflow."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import importlib.util
import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD_NS = 'scripts/current-s05-lawful-master-dates-qualification'
NS = 'scripts/current-s05-current-ac-editor-qualification'
OLD_PATH = '.github/workflows/cp7-current-s05-lawful-master-dates.yml'
PATH = '.github/workflows/cp7-current-s05-current-ac-editor.yml'
BRANCH = 'astra-a/s05-current-ac-editor-20261030'
PARENT = '2d0d195946a431fbf582e7880fc68d2292a65645d09265082b4fa152cf816f23'


def generated(raw, repo=ROOT):
    if sha256(raw).hexdigest() != PARENT:
        raise ValueError('S05_CURRENT_AC_EXACT_CDBDEA_WORKFLOW_REQUIRED')
    parent = yaml.safe_load(raw)
    path = Path(repo)/OLD_NS/'workflow_source.py'
    spec = importlib.util.spec_from_file_location('s05_current_AC_old_workflow_guard', path)
    guard = importlib.util.module_from_spec(spec); spec.loader.exec_module(guard)
    guard.checked(raw.decode(), repo)
    result = deepcopy(parent)
    result['name'] = 'CP7 S05 current AC editor Native10 and complete restore'
    result['on'] = dict(push=dict(branches=[BRANCH], paths=[PATH, NS+'/**']), workflow_dispatch={})
    result['concurrency']['group'] = 'cp7-s05-current-ac-editor-${{ github.run_id }}'
    result['jobs']['p21']['name'] = 'S05 exact current AC editor Native10 and full restoration'
    changes = []
    for step in result['jobs']['p21']['steps']:
        name = step.get('name')
        if name == 'Admit exact 911 failure, lawful master premise and retained vendor11 before database':
            step.update(name='Admit exact cdbdea failure, current AC editor and retained vendor11 before database',
                        run='python -B '+NS+'/check.py')
        elif name == 'Check unchanged ACL source and lawful master-date source controls':
            old = "python -B -m unittest discover -s "+OLD_NS+" -p 'test_*.py'"
            if step['run'].count(old) != 1:
                raise ValueError('S05_CURRENT_AC_EXACT_LOCAL_CONTROL_STEP_REQUIRED')
            step.update(name='Check unchanged ACL and current AC editor source controls',
                        run=step['run'].replace(old, "python -B -m unittest discover -s "+NS+" -p 'test_*.py'", 1))
        elif name == 'Admit exact vendor41c and lawful S05 fixture source before database':
            step.update(name='Admit exact vendor41c and current AC editor source before database',
                        run="python '../auditor/"+NS+"/check.py' --runtime")
        elif name == 'Run exact S05 Native10 with lawful master dates and complete restore':
            step.update(name='Run unchanged S05 Native10 with exact current AC editor and complete restore',
                        run="python '../auditor/"+NS+"/probe.py'")
        elif step.get('uses', '').startswith('actions/upload-artifact@'):
            step['with']['name'] = 'cp7-s05-current-ac-editor-native10-${{ github.run_attempt }}'
        else:
            continue
        changes.append(name or step.get('uses'))
    if len(changes) != 5:
        raise ValueError('S05_CURRENT_AC_EXACT_FIVE_STEP_BINDINGS_REQUIRED')
    text = yaml.safe_dump(result, sort_keys=False, width=1000)
    return text, dict(parent_sha256=PARENT, generated_sha256=sha256(text.encode()).hexdigest(),
        parent_steps=len(parent['jobs']['p21']['steps']), child_steps=len(result['jobs']['p21']['steps']),
        adapted_steps=changes, frozen_vendor_files_and_six_existing_engine_bindings_unchanged=True,
        unchanged_full_install_reinstall_Original_readers_Auth_restore_CP6_advisors_package5=True,
        root_publish_branch=BRANCH, automatic_on_other_branches=False)


def checked(text, repo=ROOT):
    expected, proof = generated((Path(repo)/OLD_PATH).read_bytes(), repo)
    if text != expected:
        raise ValueError('S05_CURRENT_AC_WORKFLOW_CHANGED')
    return proof
