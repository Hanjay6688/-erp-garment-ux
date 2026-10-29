"""Explicit semantic workflow child; every unselected vendor step is exact."""
from copy import deepcopy

NAMESPACE = 'scripts/current-attendance-period-choice-native11-qualification'
WORKFLOW = '.github/workflows/cp7-s03-attendance-native11.yml'
BRANCH = 'astra-a/s03-attendance-native11-20261030'


def derive(original):
    value = deepcopy(original)
    value['name'] = 'CP7 A S03 attendance choice Native11'
    value['on'] = {'push': {'branches': [BRANCH], 'paths': [WORKFLOW,
        NAMESPACE + '/**', 'scripts/cp7_attendance_period_choice/**',
        'scripts/current-attendance-period-choice-qualification/**']}, 'workflow_dispatch': {}}
    value['concurrency']['group'] = 'cp7-s03-attendance-native11-${{ github.run_id }}'
    job = value['jobs']['p21']
    job['name'] = 'S03 Native11 and complete restore'
    job['if'] = "github.ref == 'refs/heads/" + BRANCH + "'"
    steps = job['steps']
    source = next(s for s in steps if s.get('name') == 'Admit exact backend3194 parent and declared vendor delta before database')
    source['name'] = 'Admit exact vendor41c parent and frozen S03 source before database'
    source['run'] = "python '../auditor/" + NAMESPACE + "/probe.py' --check"
    index = steps.index(source)
    steps.insert(index, dict(name='Check frozen S03 qualification and workflow controls before database',
        **{'working-directory': 'auditor'},
        run="python -B -m unittest discover -s " + NAMESPACE + " -p 'test_*.py'\n"
            "python -B " + NAMESPACE + "/check.py --offline"))
    execute = next(s for s in steps if s.get('name') == 'Run fresh Native7 then actual race3 AuthHTTP1 and complete restoration')
    execute['name'] = 'Run actual S03 Native11 and complete restoration'
    execute['run'] = "python '../auditor/" + NAMESPACE + "/probe.py'"
    steps.insert(steps.index(execute) + 1,
        dict(name='Require exact Native11 used guard outer restore and five package gates',
             **{'working-directory': 'auditor', 'if': 'always()'},
             run='python -B ' + NAMESPACE + '/result_gate.py'))
    receipt = next(s for s in steps if s.get('name') == 'Preserve exact original JSON report bytes in a bounded compressed log receipt')
    before = "('CP7_VENDOR_RECEIVABLE_COMBINED11.json','T3_PACKAGE_INSTALL.json','T3_BACKUP_RESTORE_DRILL.json','T3_PACKAGE_FILES_INSTALL.json')"
    after = "('CP7_S03_ATTENDANCE_CHOICE_NATIVE11.json','CP7_S03_ATTENDANCE_CHOICE_NATIVE11_CASES.json','CP7_S03_ATTENDANCE_CHOICE_NATIVE11_CASES_BUSINESS_DAY_FIRST_ATTEMPT.json','S03_NATIVE11_FINAL_GATE.json','T3_PACKAGE_INSTALL.json','T3_BACKUP_RESTORE_DRILL.json','T3_PACKAGE_FILES_INSTALL.json')"
    if receipt['run'].count(before) != 1:
        raise ValueError('S03_NATIVE11_EXACT_WORKFLOW_RECEIPT_ANCHOR_REQUIRED')
    receipt['run'] = receipt['run'].replace(before, after, 1)
    upload = next(s for s in steps if s.get('uses', '').startswith('actions/upload-artifact@'))
    upload['with']['name'] = 'cp7-a-s03-attendance-native11-${{ github.run_attempt }}'
    return value
