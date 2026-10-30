"""Retain the complete70-step disposable engine; explicit catalogue routes."""
from copy import deepcopy
from pathlib import Path
import json
import os
import yaml

ROOT=Path(__file__).resolve().parents[2]
NS='scripts/current-de-sku-parent-catalogue-qualification'
OLD='.github/workflows/cp7-sku-managed-recovery-native27.yml'
NEW='.github/workflows/cp7-de-sku-parent-catalogue.yml'
BRANCH='astra-a/de-sku-parent-catalogue-20261030'
NAME='CP7 A D1 E SKU actual parent catalogue and preuse restoration'


def derive(value):
    value=deepcopy(value);value['name']=NAME
    value['concurrency']['group']='cp7-de-sku-parent-catalogue-${{ github.run_id }}'
    value['on']={'push':{'branches':[BRANCH],'paths':[NEW,NS+'/**','scripts/cp7_credit_correction_de/**','scripts/cp7_sku_pair_conversion/composition.py']},'workflow_dispatch':{}}
    job=value['jobs']['p21'];job['if']="github.ref == 'refs/heads/"+BRANCH+"'"
    job['name']='Actual D1 E SKU catalogues, preuse inverse and full restoration; business Native0'
    found=[]
    for step in job['steps']:
        name=step.get('name','')
        if name=='Check SKU delta and unchanged runner derivation before database':
            step['name']='Check exact catalogue-stage source and preserved restoration engine'
            step['run']='python -B -m unittest discover -s '+NS+" -p 'test_*.py' -v";found.append(name)
        elif name=='Check combined local oracles and existing four browser preparations':
            step['name']='Check complete immutable parent and declared catalogue source before imports'
            step['run']='python -B '+NS+'/check.py --offline';found.append(name)
        elif name=='Admit retained Native21c and complete declared combined source before database':
            step['name']='Admit actual current parent-catalogue stage and full imported source before database'
            step['run']='python -B '+NS+'/probe.py --check';found.append(name)
        elif name=='Run current managed SKU Native27 and complete restoration':
            step['name']='Install preuse inverse reinstall and capture actual D1 E SKU catalogues then fully restore'
            step['run']="python -B '../auditor/"+NS+"/probe.py' --runtime";found.append(name)
        elif name.startswith('Preserve exact original JSON report bytes'):
            before="'CP7_SKU_MANAGED_RECOVERY_NATIVE27.json'";after="'CP7_D1_E_SKU_PARENT_CATALOGUE.json'"
            if step['run'].count(before)!=1:raise ValueError('DE_SKU_ORIGINAL_REPORT_RETENTION_ANCHOR_CHANGED')
            step['run']=step['run'].replace(before,after,1);found.append(name)
        elif step.get('uses','').startswith('actions/upload-artifact@'):
            step['with']['name']='cp7-de-sku-parent-catalogue-${{ github.run_attempt }}';found.append('artifact name')
    if len(found)!=6 or len(job['steps'])!=70:raise ValueError('DE_SKU_EXACT_WORKFLOW_TRANSITION_REQUIRED')
    index=next(i for i,s in enumerate(job['steps'])if s.get('name')=='Install preuse inverse reinstall and capture actual D1 E SKU catalogues then fully restore')
    job['steps'].insert(index+1,dict(name='Require exact actual catalogue scope full outer restoration and all5',
        **{'working-directory':'auditor','run':'python -B '+NS+'/result_gate.py'}))
    return value


if __name__=='__main__':
    if os.environ.get('CI')or os.environ.get('GITHUB_ACTIONS')=='true':raise ValueError('DE_SKU_WORKFLOW_FREEZE_IN_CI_REFUSED')
    (ROOT/NEW).write_text(yaml.safe_dump(derive(yaml.safe_load((ROOT/OLD).read_bytes())),sort_keys=False,width=120))
    print(json.dumps(dict(status='PREPARED_RETAINED70_PLUS_STRICT_CATALOGUE_GATE',changed_steps=6,new_gate=1,business_cases=0)))
