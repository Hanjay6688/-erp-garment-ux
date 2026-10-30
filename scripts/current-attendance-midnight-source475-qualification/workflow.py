"""Bounded producer/own-path successor of the exact historical c097 workflow."""
from copy import deepcopy
from midnight_common import NS, WORKFLOW

OLD_NS = 'scripts/current-attendance-midnight-native1-qualification'
OLD_WF = '.github/workflows/cp7-attendance-midnight-native1.yml'
OLD_BRANCH = 'astra-a/attendance-midnight-native1-20261030'
OLD_NAME = 'CP7 A attendance midnight output Native1'
OLD = NS + 'retained-c097/' + OLD_WF
NAME = 'CP7 A attendance midnight Source475 Native1'
BRANCH = 'astra-a/attendance-midnight-source475-native1-20261030'


def derive(original):
    def route(value):
        if isinstance(value, dict):
            return {key: route(item) for key, item in value.items()}
        if isinstance(value, list):
            return [route(item) for item in value]
        if isinstance(value, str):
            for before, after in ((OLD_NS, NS.rstrip('/')), (OLD_WF, WORKFLOW),
                                  (OLD_BRANCH, BRANCH), (OLD_NAME, NAME)):
                value = value.replace(before, after)
        return value
    value = route(deepcopy(original))
    value['concurrency']['group'] = 'cp7-attendance-midnight-source475-native1-${{ github.run_id }}'
    steps = value['jobs']['p21']['steps']
    local = next(row for row in steps if row.get('name') == 'Check exact midnight callback source and labelled local controls before database')
    local['run'] += 'python -B ' + NS + 'check.py --current-originals\n'
    upload = next(row for row in steps if row.get('uses', '').startswith('actions/upload-artifact@'))
    upload['with']['name'] = 'cp7-a-attendance-midnight-source475-native1-${{ github.run_attempt }}'
    return value
