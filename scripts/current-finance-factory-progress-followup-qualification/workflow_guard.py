"""Preserve AF setup; qualify both concrete corrections and all seven groups."""
from copy import deepcopy
from pathlib import Path
from hashlib import sha256
import json,yaml

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PARENT='.github/workflows/cp7-d17-18-consistent-reader-stream.yml'
TARGET='.github/workflows/cp7-d17-18-factory-progress.yml'
FOLDER='scripts/current-finance-factory-progress-followup-qualification'
LABEL='CP7_D17_18_FACTORY_PROGRESS_NATIVE_SOURCE_CRON7'


def expected(repo,here):
    rule=json.loads((here/'WORKFLOW_ORIGIN.json').read_bytes())
    raw=(repo/PARENT).read_bytes();assert sha256(raw).hexdigest()==rule['parent_sha256']
    value=deepcopy(yaml.safe_load(raw))
    value['name']='CP7 D17-18 unchanged finance real factory progress and all7'
    value['on']['push']['branches']=['astra-a/d17-18-factory-progress-qualification-20261028']
    value['on']['push']['paths']=[TARGET,FOLDER+'/**']
    value['concurrency']['group']='cp7-d17-18-factory-progress-${{ github.run_id }}'
    job=value['jobs']['p21'];job['name']=value['name'];steps=job['steps']
    def step(name):
        matches=[s for s in steps if s.get('name')==name];assert len(matches)==1,name;return matches[0]
    anchor=step('Admit complete AF first outcome and corrected reader stream source')
    index=steps.index(anchor)+1
    steps[index:index]=[
        dict(name='Fetch exact retained D3 sixPASS factory cutoff and package bytes',**{'working-directory':'auditor'},
            env={'GH_TOKEN':'${{ github.token }}'},run='python '+FOLDER+'/fetch_d3.py'),
        dict(name='Verify unchanged D3 readers and bounded progress watcher before DB',**{'working-directory':'auditor'},
            run='python -m unittest discover -s '+FOLDER+' -p "test*.py"'),
        dict(name='Admit exact D3 first outcome and factory progress all7 source',**{'working-directory':'auditor'},
            run='python '+FOLDER+'/admission.py')]
    runtime=step('Run same7 with private stable opening reader and exact streaming data restoration')
    runtime['name']='Run all7 with unchanged D3 finance and read-only factory progress observation'
    runtime['run']="python '../auditor/"+FOLDER+"/probe.py'"
    logs=step('Preserve exact original JSON report bytes in a bounded compressed log receipt')
    prior='CP7_D17_18_CONSISTENT_READERS_STREAM_NATIVE_FACTORY_CRON7'
    assert logs['run'].count(prior)==1;logs['run']=logs['run'].replace(prior,LABEL)
    upload=[s for s in steps if s.get('uses','').startswith('actions/upload-artifact@')]
    assert len(upload)==1;upload[0]['with']['name']='cp7-d17-18-factory-progress-${{ github.run_attempt }}'
    return value


def check(repo,here,*,actual=None):
    value=yaml.safe_load((repo/TARGET).read_bytes())if actual is None else actual
    assert value==expected(repo,here),'READER_STREAM_UNDECLARED_WORKFLOW_CHANGE'
    return dict(exact_declared_derivation=True,old_parent_setup_worktrees_and_restoration_retained=True,
        complete_first_AF_failure_before_DB=True,all_seven_groups_still_required=True,
        production_limits_and_Native_bodies_unchanged=True,first_failure_not_retried_unchanged=True)


if __name__=='__main__':
    p=HERE/'WORKFLOW_ORIGIN.json';assert not p.exists()
    p.write_text(json.dumps(dict(parent=PARENT,parent_sha256=sha256((ROOT/PARENT).read_bytes()).hexdigest()),indent=2)+'\n')
    target=ROOT/TARGET;assert not target.exists();target.write_text(yaml.safe_dump(expected(ROOT,HERE),sort_keys=False,allow_unicode=True,width=110))
    print(json.dumps(check(ROOT,HERE)))
