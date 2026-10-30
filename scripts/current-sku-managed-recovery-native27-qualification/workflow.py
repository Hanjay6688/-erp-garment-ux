"""Structural child of exact public602 workflow; unaffected steps byte-equivalent."""
from copy import deepcopy

OLD_NS='scripts/current-sku-all-member-native23-qualification'
NS='scripts/current-sku-managed-recovery-native27-qualification'
OLD='.github/workflows/cp7-sku-all-member-native23.yml'
NEW='.github/workflows/cp7-sku-managed-recovery-native27.yml'
BRANCH='astra-a/sku-managed-recovery-native27-20261030'
NAME='CP7 A SKU managed recovery full Native27'

def derive(original):
    value=deepcopy(original);value['name']=NAME
    value['on']['push']=dict(branches=[BRANCH],paths=[NEW,NS+'/**'])
    value['concurrency']['group']='cp7-sku-managed-recovery-native27-${{ github.run_id }}'
    job=value['jobs']['p21'];job['if']="github.ref == 'refs/heads/"+BRANCH+"'"
    job['name']='Native7 cost5 races3 permission waits7 recovery busy1 Auth browser4; full restore'
    for step in job['steps']:
        if'run'in step:step['run']=step['run'].replace(OLD_NS,NS)
    runtime=next(s for s in job['steps']if s.get('name','').startswith('Run one installed SKU base7'))
    runtime['name']='Run current managed SKU Native27 and complete restoration'
    preserve=next(s for s in job['steps']if s.get('name','').startswith('Preserve exact original JSON report bytes'))
    preserve['run']=preserve['run'].replace('CP7_SKU_ALL_MEMBER_NATIVE23','CP7_SKU_MANAGED_RECOVERY_NATIVE27').replace('CP7_SKU_GROUP_COST_NATIVE3','CP7_SKU_GROUP_COST_NATIVE5')
    upload=next(s for s in job['steps']if s.get('uses','').startswith('actions/upload-artifact@'))
    upload['with']['name']='cp7-a-sku-managed-recovery-native27-${{ github.run_attempt }}'
    upload['with']['path']+='\nauditor/cp6-proof/t3/SKU27_SEQUENCE_PREFIX_*.json'
    delta=next(s for s in job['steps']if s.get('name')=='Check SKU delta and unchanged runner derivation before database')
    delta['run']='python -B '+NS+'/attempt_policy.py --require-window\n'+delta['run']
    delta['run']+="\npython -B -m unittest discover -s scripts/cp7_sku_pair_conversion -p test_recovery.py\n"
    delta['run']+="node --test "+NS+"/test_node_source.mjs\n"
    return value
