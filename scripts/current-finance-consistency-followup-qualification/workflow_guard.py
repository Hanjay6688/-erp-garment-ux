"""Only focused entry points and exact retained84 admission differ from run84."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json,yaml

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PARENT='.github/workflows/cp7-d17-18-consistent-capture-infra.yml'
TARGET='.github/workflows/cp7-d17-18-consistency-native20-cron.yml'
FOLDER='scripts/current-finance-consistency-followup-qualification'
LABEL='CP7_D17_18_CONSISTENCY_FOCUSED_NATIVE20_CRON1'


def expected(repo,here):
    rule=json.loads((here/'ORIGIN.json').read_bytes())['workflow']
    raw=(repo/PARENT).read_bytes();assert sha256(raw).hexdigest()==rule['parent_sha256']
    value=deepcopy(yaml.safe_load(raw))
    value['name']='CP7 D17-18 focused unchanged Native20 and actual minute cron'
    value['on']['push']['branches']=['astra-a/d17-18-consistency-native20-cron-qualification-20261028']
    value['on']['push']['paths']=[TARGET,FOLDER+'/**']
    value['concurrency']['group']='cp7-d17-18-consistency-focused-${{ github.run_id }}'
    job=value['jobs']['p21'];job['name']=value['name'];steps=job['steps']
    anchors=[s for s in steps if s.get('name')=='Admit exact retained first diagnostics and consistency candidate before database']
    assert len(anchors)==1;index=steps.index(anchors[0])+1
    steps[index:index]=[
        dict(name='Fetch exact retained actual84 first failure and package bytes',**{'working-directory':'auditor'},
            env={'GH_TOKEN':'${{ github.token }}'},run='python '+FOLDER+'/fetch_retained.py'),
        dict(name='Verify focused fixture scopes and exact retained first outcome',**{'working-directory':'auditor'},
            run='python -m unittest discover -s '+FOLDER+' -p "test*.py"'),
        dict(name='Admit exact focused source and retained84 before database',**{'working-directory':'auditor'},
            run='python '+FOLDER+'/admission.py')]
    runtime=[s for s in steps if s.get('name')=='Run seven isolated report book consistency diagnostics with full database restoration']
    assert len(runtime)==1
    runtime[0]['name']='Run corrected unchanged Native20 and actual minute cron with full restoration'
    runtime[0]['run']="python '../auditor/"+FOLDER+"/probe.py'"
    logs=[s for s in steps if s.get('name')=='Preserve exact original JSON report bytes in a bounded compressed log receipt']
    assert len(logs)==1 and logs[0]['run'].count('CP7_D17_18_FINANCE_REPORT_BOOK_CONSISTENCY_ISOLATED7')==1
    logs[0]['run']=logs[0]['run'].replace('CP7_D17_18_FINANCE_REPORT_BOOK_CONSISTENCY_ISOLATED7',LABEL)
    upload=[s for s in steps if s.get('uses','').startswith('actions/upload-artifact@')]
    assert len(upload)==1;upload[0]['with']['name']='cp7-d17-18-consistency-native20-cron-${{ github.run_attempt }}'
    return value


def check(repo,here,*,actual=None):
    value=yaml.safe_load((repo/TARGET).read_bytes())if actual is None else actual
    assert value==expected(repo,here),'FOCUSED_UNDECLARED_WORKFLOW_CHANGE'
    return dict(exact_declared_derivation=True,source_worktrees_startup_and_DB_restores_retained=True,
        original_ERP_diagnostics_oracles_not_changed=True,actual_focused_groups=2,retained_prior_pass_groups=5,
        prior_whole84_status='INCOMPLETE',previous_result_not_promoted_to_PASS=True)


if __name__=='__main__':
    rule=json.loads((HERE/'ORIGIN.json').read_bytes());assert 'workflow'not in rule
    rule['workflow']=dict(parent=PARENT,parent_sha256=sha256((ROOT/PARENT).read_bytes()).hexdigest())
    (HERE/'ORIGIN.json').write_text(json.dumps(rule,indent=2)+'\n')
    target=ROOT/TARGET;assert not target.exists()
    target.write_text(yaml.safe_dump(expected(ROOT,HERE),sort_keys=False,allow_unicode=True,width=110))
    print(json.dumps(check(ROOT,HERE)))
