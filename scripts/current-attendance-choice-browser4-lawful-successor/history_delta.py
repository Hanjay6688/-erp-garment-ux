"""Reversible30ee harness successor; prior seals read exact recovered preimages."""
from hashlib import sha256
from pathlib import Path
import json
import importlib.util
import os
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
PARENT = '30ee9874d049632050faf53b299a0cd8a11fe9f6'


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def previous(name, current=None, *, root=ROOT, here=HERE):
    plan = json.loads((here / 'CANCELLED_HISTORY_DELTA.json').read_bytes())
    if plan['parent_commit'] != PARENT or plan['contract'] != 'cp7.s03.cancelled-history-observation.v1':
        raise ValueError('S03_HISTORY_EXACT_TRANSITION_REQUIRED')
    rows = [x for x in plan['files'] if x['name'] == name]
    if not rows:
        return (here / name).read_bytes() if current is None else current
    if len(rows) != 1:
        raise ValueError('S03_HISTORY_UNIQUE_TRANSITION_FILE_REQUIRED')
    row = rows[0]
    old = (here / 'retained-30ee' / name).read_bytes()
    path = root / row['path'] if name == 'workflow.yml' else here / name
    actual = path.read_bytes() if current is None else current
    if name == 'cases.mjs':
        spec=importlib.util.spec_from_file_location('s03_exact_current_refresh_inverse',here/'refresh_delta.py')
        refresh=importlib.util.module_from_spec(spec);spec.loader.exec_module(refresh)
        actual=refresh.previous(actual,here)
    git = subprocess.check_output(['/usr/bin/git', '-C', str(root), 'show', PARENT + ':' + row['path']],
                                  env=dict(os.environ, GIT_NO_LAZY_FETCH='1'))
    if old != git or pin(old) != row['before'] or pin(actual) != row['after']:
        raise ValueError('S03_HISTORY_EXACT_PREIMAGE_AND_CURRENT_REQUIRED:' + name)
    text = old.decode()
    for change in row['changes']:
        if change['count'] != 1 or not change['before'] or text.count(change['before']) != 1:
            raise ValueError('S03_HISTORY_ONE_FORWARD_ANCHOR_REQUIRED')
        text = text.replace(change['before'], change['after'], 1)
    if text.encode() != actual:
        raise ValueError('S03_HISTORY_COMPLETE_DERIVATION_REQUIRED')
    for change in reversed(row['changes']):
        if not change['after'] or text.count(change['after']) != 1:
            raise ValueError('S03_HISTORY_ONE_REVERSE_ANCHOR_REQUIRED')
        text = text.replace(change['after'], change['before'], 1)
    if text.encode() != old:
        raise ValueError('S03_HISTORY_LOSSLESS_PREIMAGE_REQUIRED')
    return old


def verify(root=ROOT, here=HERE):
    plan = json.loads((here / 'CANCELLED_HISTORY_DELTA.json').read_bytes())
    for row in plan['files']:
        previous(row['name'], root=root, here=here)
    old = (here / 'retained-30ee/cases.mjs').read_text()
    current = (here / 'cases.mjs').read_text()
    marker = 'async function desktop('
    if old[old.index(marker):] != current[current.index(marker):]:
        raise ValueError('S03_HISTORY_ALL_FOUR_FINANCIAL_CALLBACKS_MUST_REMAIN_EXACT')
    for name, expected in plan['unchanged'].items():
        if pin((root / name).read_bytes()) != expected:
            raise ValueError('S03_HISTORY_FROZEN_NATIVE_OR_ORACLE_CHANGED:' + name)
    return dict(status='EXACT_30EE_HARNESS_HISTORY_SUCCESSOR_SOURCE_ONLY',
        counted_changes=sum(len(x['changes']) for x in plan['files']),
        complete_previous_source_bytes_recovered=True, four_financial_callbacks_exact=True,
        current_ACTIVE_Native_validator_retained=True, ordinary_Native_validator_retained=True,
        cancelled_history_requires_pre_cancel_Native_validated_authority=True,
        phase_specific_FG_HPP_inverse_oracles_exact=True, Native_SQL_changed=False,
        workflow_timeout_minutes=240, actual_Native_Auth_browser_credit=0)
