"""Exact current Native11 workflow derivative; unrelated producers/restore steps retained."""
from copy import deepcopy

OLD = '.github/workflows/cp7-s03-attendance-native11.yml'
NEW = '.github/workflows/cp7-s03-choice-reader-native14.yml'
NS = 'scripts/current-attendance-choice-reader-native14-qualification'
NAME = 'CP7 A S03 attendance choice plus owning readers Native14'
EARLY = 'Require frozen current source API and vendor41c before ERP GET or database'
LOCAL = 'Check Native14 closed source and isolated generated-output controls before database'
ADMIT = 'Admit exact vendor41c and current15 source for fresh11 plus Reader3 before database'
RUN = 'Run actual original11 then Reader3 same candidate and unchanged used witness restore'
GATE = 'Require both actual groups11 plus3 outer14 used guard full restore and all5 gates'


def derive(original, branch):
    value = deepcopy(original); value['name'] = NAME
    value['on']['push'] = dict(branches=[branch], paths=[NEW, NS + '/**',
        'scripts/cp7_attendance_period_choice/**',
        'scripts/current-attendance-period-choice-qualification/**',
        'scripts/current-attendance-period-choice-readers-qualification/**'])
    value['concurrency']['group'] = 'cp7-s03-choice-reader-native14-${{ github.run_id }}'
    job = value['jobs']['p21']
    job['name'] = 'Fresh Native11 plus Reader3 current15 source; full restore'
    job['if'] = "github.ref == 'refs/heads/" + branch + "'"
    steps = job['steps']
    steps.insert(1, dict(name=EARLY, **{'working-directory': 'auditor', 'run':
        "python -B - <<'PY'\nimport importlib.util,json\nfrom pathlib import Path\np=Path('" + NS + "');s=importlib.util.spec_from_file_location('native14_first_closed_gate',p/'gate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)\nm.selected(json.loads((p/'CONFIG.json').read_bytes()))\nPY\n"}))
    local = next(s for s in steps if s.get('name') == 'Check frozen S03 qualification and workflow controls before database')
    local['name'] = LOCAL
    local['run'] = "python -B -m unittest discover -s " + NS + " -p 'test_*.py'\npython -B " + NS + "/check.py --offline\n"
    admission = next(s for s in steps if s.get('name') == 'Admit exact vendor41c parent and frozen S03 source before database')
    admission['name'] = ADMIT; admission['run'] = "python '../auditor/" + NS + "/probe.py' --check"
    runtime = next(s for s in steps if s.get('name') == 'Run actual S03 Native11 and complete restoration')
    runtime['name'] = RUN; runtime['run'] = "python '../auditor/" + NS + "/probe.py'"
    gate = next(s for s in steps if s.get('name') == 'Require exact Native11 used guard outer restore and five package gates')
    gate['name'] = GATE; gate['run'] = 'python -B ' + NS + '/result_gate.py'
    receipt = next(s for s in steps if s.get('name') == 'Preserve exact original JSON report bytes in a bounded compressed log receipt')
    receipt['run'] = 'python -B ' + NS + '/retain_reports.py'
    upload = next(s for s in steps if s.get('uses', '').startswith('actions/upload-artifact@'))
    upload['with']['name'] = 'cp7-a-s03-choice-reader-native14-${{ github.run_attempt }}'
    return value
