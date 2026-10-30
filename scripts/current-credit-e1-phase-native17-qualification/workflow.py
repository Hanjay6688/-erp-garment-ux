"""Exact old E17 complete workflow, explicit routes/descriptors and pre-GET gate."""
from pathlib import Path
from hashlib import sha256

ROOT=Path(__file__).resolve().parents[2]
OLD_NS='scripts/current-credit-e1-current-d1-native17-qualification'
NS='scripts/current-credit-e1-phase-native17-qualification'
PARENT='.github/workflows/cp7-credit-e1-current-d1-native17.yml'
PATH='.github/workflows/cp7-credit-e1-phase-native17.yml'
BRANCH='astra-a/credit-e1-phase-native17-20261030'


def derive(raw):
    text=raw.decode()
    replacements=((OLD_NS,NS),(PARENT,PATH),('astra-a/credit-e1-current-d1-native17-20261030',BRANCH),
        ('CP7 A incoming credit E1 Native17 gated by exact successful D1','CP7 A current E1 consumer phase fresh Native17'),
        ('cp7-a-credit-e1-native17-${{ github.run_attempt }}','cp7-a-credit-e1-phase-native17-${{ github.run_attempt }}'))
    counts=[]
    for before,after in replacements:
        count=text.count(before)
        if not count:raise ValueError('E_PHASE_WORKFLOW_ROUTE_MISSING:'+before)
        text=text.replace(before,after);counts.append(count)
    anchor='    - uses: actions/setup-python@'
    if text.count(anchor)!=1:raise ValueError('E_PHASE_WORKFLOW_PRE_GET_ANCHOR_REQUIRED')
    step='    - name: Verify complete public E source319 before any retained artifact GET\n      working-directory: auditor\n      run: python -B '+NS+'/source_check.py\n'
    text=text.replace(anchor,step+anchor,1)
    return text,dict(original_sha256=sha256(raw).hexdigest(),derived_sha256=sha256(text.encode()).hexdigest(),
        routing_descriptor_occurrences=counts,added_source_only_pre_GET_steps=1,unchanged_engine_substitutions=6)
