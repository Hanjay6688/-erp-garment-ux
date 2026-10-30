"""Frozen complete Native14 workflow with bounded successor routing metadata."""
from copy import deepcopy

OLD='.github/workflows/cp7-s03-choice-reader-native14.yml'
NEW='.github/workflows/cp7-s03-lawful-fixture-native14.yml'
NS='scripts/current-s03-lawful-fixture-successor-qualification'
NAME='CP7 A S03 lawful fixture successor Native11 then Reader3'
BRANCH='astra-a/s03-lawful-fixture-native14-20261030'
PARENT_NS='scripts/current-attendance-choice-reader-native14-qualification'


def derive(original):
    value=deepcopy(original);value['name']=NAME
    value['on']['push']=dict(branches=[BRANCH],paths=[NEW,NS+'/**'])
    value['concurrency']['group']='cp7-s03-lawful-fixture-native14-${{ github.run_id }}'
    job=value['jobs']['p21'];job['name']='Lawful fixture successor fresh11 then Reader3; same runtime15 and full restore'
    job['if']="github.ref == 'refs/heads/"+BRANCH+"'"
    steps=job['steps'];changed=0
    for step in steps:
        if 'run' in step and PARENT_NS in step['run']:
            step['run']=step['run'].replace(PARENT_NS,NS);changed+=1
        if step.get('uses','').startswith('actions/upload-artifact@'):
            step['with']['name']='cp7-a-s03-lawful-fixture-native14-${{ github.run_attempt }}'
    assert changed==6,'S03_LAWFUL_EXACT_SIX_WORKFLOW_ROUTING_STEPS_REQUIRED'
    return value
