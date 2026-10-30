"""Exact64-step currentAC workflow plus one pre-GET source-only step."""
from pathlib import Path
from hashlib import sha256

ROOT=Path(__file__).resolve().parents[2]
PARENT='.github/workflows/cp7-current-s05-current-ac-editor.yml'
PATH='.github/workflows/cp7-current-s05-wib-owner-fixture-successor.yml'
OLD_NS='scripts/current-s05-current-ac-editor-qualification'
NS='scripts/current-s05-wib-owner-fixture-successor-qualification'
BRANCH='astra-a/s05-wib-owner-fixture-successor-20261030'


def derive(raw):
    text=raw.decode();counts=[]
    for before,after in ((OLD_NS,NS),(PARENT,PATH),('astra-a/s05-current-ac-editor-20261030',BRANCH),
        ('CP7 S05 current AC editor Native10 and complete restore','CP7 S05 lawful WIB and Owner fixture fresh Native10'),
        ('cp7-s05-current-ac-editor-','cp7-s05-wib-owner-fixture-')):
        count=text.count(before)
        if not count:raise ValueError('S05_FIXTURE_WORKFLOW_DESCRIPTOR_REQUIRED:'+before)
        text=text.replace(before,after);counts.append(count)
    anchor='    - uses: actions/setup-python@'
    if text.count(anchor)!=1:raise ValueError('S05_FIXTURE_EXACT_WORKFLOW_PRE_GET_ANCHOR_REQUIRED')
    text=text.replace(anchor,'    - name: Verify complete public52eed source before retained artifact GET\n      working-directory: auditor\n      run: python -B '+NS+'/source_check.py\n'+anchor,1)
    return text,dict(parent_sha256=sha256(raw).hexdigest(),derived_sha256=sha256(text.encode()).hexdigest(),
        descriptor_occurrences=counts,added_pre_GET_source_steps=1,complete_vendor_engine_changes=0)
