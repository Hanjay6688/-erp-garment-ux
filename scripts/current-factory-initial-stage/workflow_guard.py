from copy import deepcopy
from hashlib import sha256
import json,yaml
PARENT='.github/workflows/cp7-d17-18-factory-operational-profile.yml'
TARGET='.github/workflows/cp7-d17-18-factory-initial-stage.yml'
FOLDER='scripts/current-factory-initial-stage'
LABEL='CP7_D17_18_FACTORY_INITIAL_STAGE_NATIVE_SOURCE_CRON7'
def expected(repo,here):
    rule=json.loads((here/'WORKFLOW_ORIGIN.json').read_bytes());raw=(repo/PARENT).read_bytes()
    assert sha256(raw).hexdigest()==rule['parent_sha256']
    value=deepcopy(yaml.safe_load(raw));value['name']='CP7 D17-18 bounded factory initial stage and combined all7'
    value['on']['push']['branches']=['astra-a/d17-18-factory-initial-stage-20261028']
    value['on']['push']['paths']=[TARGET,FOLDER+'/**']
    value['concurrency']['group']='cp7-d17-18-factory-initial-stage-${{ github.run_id }}'
    job=value['jobs']['p21'];job['name']=value['name'];steps=job['steps']
    runtime=[s for s in steps if s.get('run')=="python '../auditor/scripts/current-factory-operational-profile-qualification/probe.py'"]
    assert len(runtime)==1
    runtime[0]['name']='Run bounded factory initial stage with all7 and complete restoration'
    runtime[0]['run']="python '../auditor/"+FOLDER+"/probe.py'"
    anchor=[s for s in steps if s.get('run')=='python scripts/current-factory-operational-profile-qualification/admission.py']
    assert len(anchor)==1;idx=steps.index(anchor[0])+1
    steps[idx:idx]=[
        dict(name='Fetch exact 5b32 measured profile and complete restoration evidence',**{'working-directory':'auditor'},env={'GH_TOKEN':'${{ github.token }}'},run='python '+FOLDER+'/fetch_profile.py'),
        dict(name='Check initial worker boundaries and unchanged seven-group oracles',**{'working-directory':'auditor'},run='python -m unittest discover -s '+FOLDER+' -p "test*.py"'),
        dict(name='Admit bounded initial worker and exact complete predecessor sources',**{'working-directory':'auditor'},run='python '+FOLDER+'/admission.py')]
    logs=[s for s in steps if s.get('name')=='Preserve exact original JSON report bytes in a bounded compressed log receipt'];assert len(logs)==1
    old='CP7_D17_18_CURRENT_FACTORY_OPERATIONAL_PROFILE1';assert logs[0]['run'].count(old)==1
    logs[0]['run']=logs[0]['run'].replace(old,LABEL)
    uploads=[s for s in steps if s.get('uses','').startswith('actions/upload-artifact@')];assert len(uploads)==1
    uploads[0]['with']['name']='cp7-d17-18-factory-initial-stage-${{ github.run_attempt }}'
    return value
def check(repo,here,*,actual=None):
    value=yaml.safe_load((repo/TARGET).read_bytes())if actual is None else actual
    assert value==expected(repo,here),'INITIAL_STAGE_UNDECLARED_WORKFLOW_CHANGE'
    return dict(exact_profile_setup_retained=True,all_seven_groups_required=True,all_prerequisites_before_DB=True,
        actual_profile_not_substituted_for_backend_acceptance=True)
