"""Exact complete Native14 workflow derivative; only owned producer/routing changes."""
from copy import deepcopy
from midnight_common import NS, WORKFLOW

OLD = '.github/workflows/cp7-s03-choice-reader-native14.yml'
NAME = 'CP7 A attendance midnight output Native1'
EARLY = 'Require actual accepted successor14 six Originals before ERP GET or database'


def derive(original, branch):
    value = deepcopy(original)
    value['name'] = NAME
    value['on']['push'] = dict(branches=[branch], paths=[WORKFLOW, NS + '**'])
    value['concurrency']['group'] = 'cp7-attendance-midnight-native1-' + '$' + '{{ github.run_id }}'
    job = value['jobs']['p21']
    job['name'] = 'One midnight Native case; accepted14 retained; complete restore'
    job['if'] = "github.ref == 'refs/heads/" + branch + "'"
    steps = job['steps']
    early = steps[1]
    early['name'] = EARLY
    early['run'] = ("python -B - <<'PY'\nimport sys,json\nfrom pathlib import Path\n"
        "p=Path('" + NS[:-1] + "');sys.path.insert(0,str(p))\n"
        "import midnight_gate\nmidnight_gate.selected(json.loads((p/'CONFIG.json').read_bytes()))\nPY\n")
    local = next(s for s in steps if s.get('name') == 'Check Native14 closed source and isolated generated-output controls before database')
    local['name'] = 'Check exact midnight callback source and labelled local controls before database'
    local['run'] = ("python -B -m unittest discover -s " + NS[:-1] + " -p 'test_*.py'\n"
                    "python -B " + NS + "check.py --offline\n")
    intake = next(s for s in steps if s.get('name') == 'Admit exact vendor41c and current15 source for fresh11 plus Reader3 before database')
    intake['name'] = 'Admit retained accepted14 six Originals and actual current7 source before database'
    intake['run'] = "python '../auditor/" + NS + "probe.py' --check"
    run = next(s for s in steps if s.get('name') == 'Run actual original11 then Reader3 same candidate and unchanged used witness restore')
    run['name'] = 'Run exact midnight1 once and unchanged committed used witness full restore'
    run['run'] = "python '../auditor/" + NS + "probe.py'"
    result = next(s for s in steps if s.get('name') == 'Require both actual groups11 plus3 outer14 used guard full restore and all5 gates')
    result['name'] = 'Require exact raw midnight1 full outer restore and all five new package gates'
    result['run'] = 'python -B ' + NS + 'result_gate.py'
    retain = next(s for s in steps if s.get('name') == 'Preserve exact original JSON report bytes in a bounded compressed log receipt')
    retain['run'] = 'python -B ' + NS + 'retain_reports.py'
    upload = next(s for s in steps if s.get('uses', '').startswith('actions/upload-artifact@'))
    upload['with']['name'] = 'cp7-a-attendance-midnight-native1-' + '$' + '{{ github.run_attempt }}'
    return value
