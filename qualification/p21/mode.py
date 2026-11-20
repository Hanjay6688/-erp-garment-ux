"""Bind the S06 integration to its exact public branch and disposable product."""

import json
import os
import re
from pathlib import Path

from audit.codex.p20_evidence import PRODUCT, PRODUCT_TREE


MODE_KEY = 'CP7_P21_TARGET'
TARGET = 'PUBLIC_GITHUB_DISPOSABLE_LOOPBACK'
REPOSITORY = 'Hanjay6688/-erp-garment-ux'
BRANCH = 'writer-a/cp7-close11-global-public'
WORKFLOW = '.github/workflows/cp7-close11-global-public.yml'
EVENT = 'push'
SCOPE = 'GLOBAL_FFDA_INSTALLED_HANDOFF'


def enabled():
    value = os.environ.get(MODE_KEY, '')
    if value not in ('', TARGET) or (value and os.environ.get('P20_GLOBAL_SUCCESSOR')):
        raise ValueError('CP7_P21_EXACT_DISPOSABLE_TARGET_REQUIRED')
    return value == TARGET


def dispatch_product():
    if not enabled():
        return PRODUCT
    pins = json.loads(Path(__file__).with_name('switch-roll').joinpath('PINS.json').read_bytes())
    if not (pins['parent'] == PRODUCT == os.environ.get('P21_PRODUCT_SHA')
            and pins['product_head'] == os.environ.get('CP7_P21_SWITCH_ROLL_HEAD')
            and pins['product_tree'] == os.environ.get('CP7_P21_SWITCH_ROLL_TREE')):
        raise ValueError('CP7_P21_SWITCH_ROLL_DISPATCH_PINS_REQUIRED')
    return pins['product_head']


def public_identity(head):
    ref = 'refs/heads/' + BRANCH
    workflow = f'{REPOSITORY}/{WORKFLOW}@{ref}'
    values = os.environ
    if not (enabled() and values.get('GITHUB_ACTIONS') == 'true'
            and values.get('GITHUB_REPOSITORY') == REPOSITORY
            and values.get('GITHUB_EVENT_NAME') == EVENT
            and values.get('GITHUB_REF') == ref
            and values.get('GITHUB_WORKFLOW_REF') == workflow
            and values.get('GITHUB_JOB') == 'ordinary'
            and values.get('GITHUB_RUN_ATTEMPT') == '1'
            and re.fullmatch(r'[a-f0-9]{40}', head)
            and values.get('GITHUB_SHA') == head):
        raise ValueError('P21_PUBLIC_EXACT_JOB_REQUIRED')
    event = json.loads(Path(values['GITHUB_EVENT_PATH']).read_bytes())
    repository = event['repository']
    run = values.get('GITHUB_RUN_ID', '')
    if not (repository['full_name'] == REPOSITORY and repository['private'] is False
            and event['ref'] == ref and event['after'] == head
            and event['deleted'] is False and re.fullmatch(r'[1-9][0-9]*', run)):
        raise ValueError('P21_PUBLIC_EXACT_PUSH_REQUIRED')
    return dict(repository=REPOSITORY, event=EVENT, pr=None, base=None, head=head,
                merge=head, candidate_sha=dispatch_product(), run_id=int(run), run_attempt=1)
