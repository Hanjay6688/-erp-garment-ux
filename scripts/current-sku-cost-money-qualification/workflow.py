"""Prepare one unarmed owning workflow while retaining the full accepted setup."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import yaml

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PARENT='.github/workflows/cp7-sku-moving-average-native5.yml'
OUTPUT='.github/workflows/cp7-sku-cost-money-native19.yml'
BRANCH='astra-a/sku-cost-money-native19-20261103'

def derive():
    raw=(ROOT/PARENT).read_bytes()
    if sha256(raw).hexdigest()!='647b9af8f742211e5f8b122d3d72e2c6fb4c7bafa6056cd9d7991477284649c3':raise ValueError('SKU_MONEY_ACCEPTED_PARENT_WORKFLOW_CHANGED')
    parent=yaml.safe_load(raw);result=deepcopy(parent)
    result['name']='CP7 A SKU source money Native19'
    result['on']['push']=dict(branches=[BRANCH],paths=[OUTPUT,'scripts/current-sku-cost-money-qualification/**','scripts/cp7_sku_cost_components/**'])
    result['concurrency']['group']='cp7-sku-cost-money-native19'
    job=result['jobs']['p21'];job['name']='Source money Native19 and complete restore'
    job['if']="github.ref == 'refs/heads/"+BRANCH+"'"
    steps=[];changes=[]
    for original in parent['jobs']['p21']['steps']:
        step=deepcopy(original);name=step.get('name','')
        if name=='Admit exact SKU27 parent and declared moving-average child before database':
            step['name']='Admit exact Native27 and moving6 parents plus the full money19 graph before database'
            step['run']='python -B scripts/current-sku-cost-money-qualification/check.py --complete';changes.append(name)
        elif name=='Run actual SKU moving-average Native6 and complete restoration':
            step['name']='Run actual source money Native19 once with complete owning restoration'
            step['run']="python '../auditor/scripts/current-sku-cost-money-qualification/probe.py'";changes.append(name)
        elif name=='Preserve exact original JSON report bytes in a bounded compressed log receipt':
            step['run']=step['run'].replace('CP7_SKU_MOVING_AVERAGE_QUALIFICATION','CP7_SKU_COST_MONEY_QUALIFICATION').replace('CP7_SKU_MOVING_AVERAGE_NATIVE6','CP7_SKU_COST_MONEY_NATIVE19');changes.append(name)
        elif str(step.get('uses','')).startswith('actions/upload-artifact@'):
            step['with']['name']='cp7-a-sku-source-money-native19-${{ github.run_attempt }}';changes.append('artifact name')
        steps.append(step)
        if name=='Select exact qualified prerequisite heads':
            steps.append(dict(name='Require sufficient real WIB day before expensive setup',**{'working-directory':'auditor'},
                run='python -B scripts/current-sku-managed-recovery-native27-qualification/attempt_policy.py --require-window'))
        if name=='Bind exact Root-accepted SKU27 parent Originals':
            steps.append(dict(name='Bind exact accepted moving Native6 and complete restoration Originals',env={'GH_TOKEN':'${{ github.token }}'},
                **{'working-directory':'auditor'},run='python -B scripts/current-sku-cost-money-qualification/fetch_moving_parent.py'))
        if name=='Run actual SKU moving-average Native6 and complete restoration':
            steps.append(dict(name='Retain complete writer-CWD monetary census on every outcome',**{'if':'always()','working-directory':'auditor'},run="""python - <<'PY'
from pathlib import Path
from hashlib import sha256
import json,shutil
source=Path('../writer/cp6-proof/t3');destination=Path('cp6-proof/t3/ORIGINAL_WRITER_CENSUS');destination.mkdir(parents=True,exist_ok=True)
retained=[]
for original in sorted(source.glob('SKU_COST_*_FULL_CURRENT_CENSUS.json')):
    raw=original.read_bytes();target=destination/original.name
    if target.exists():raise ValueError('MONEY_CENSUS_DESTINATION_ALREADY_EXISTS')
    shutil.copyfile(original,target)
    if target.read_bytes()!=raw:raise ValueError('MONEY_CENSUS_COPY_CHANGED')
    retained.append(dict(name=original.name,bytes=len(raw),sha256=sha256(raw).hexdigest()))
(destination/'MANIFEST.json').write_text(json.dumps(dict(original_bytes_retained=retained),indent=2)+'\\n')
print(json.dumps(dict(complete_census_files=len(retained),financial_case_credit=0)))
PY
"""))
    job['steps']=steps
    if len(changes)!=4 or len(steps)!=len(parent['jobs']['p21']['steps'])+3:raise ValueError('SKU_MONEY_WORKFLOW_DECLARED_CHANGE_COUNT')
    # Budgets, pinned actions, full source/archive graph, disposable clone,
    # cleanup and complete package engine are inherited from the actual6 run.
    assert job['timeout-minutes']==parent['jobs']['p21']['timeout-minutes']==120
    return result,dict(parent_sha256=sha256(raw).hexdigest(),changed_steps=changes,additional_steps=3,
        original_steps=len(parent['jobs']['p21']['steps']),prepared_steps=len(steps),activation_branch=BRANCH,
        production_go=False,workflow_armed=False)

if __name__=='__main__':
    workflow,proof=derive();(ROOT/OUTPUT).write_text(yaml.safe_dump(workflow,sort_keys=False,width=120))
    print(json.dumps(proof,sort_keys=True))
