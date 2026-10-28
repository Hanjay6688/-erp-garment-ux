"""Combine retained qualification infrastructure with unchanged browser setup."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json,yaml

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PARENT='.github/workflows/cp7-d17-18-factory-progress.yml'
OLD_UI='.github/workflows/cp7-d17-18-progress-finance-ui-browser.yml'
TARGET='.github/workflows/cp7-d17-18-combined-finance-browser.yml'
FOLDER='scripts/current-finance-combined-browser-qualification'
LABEL='CP7_D17_18_COMBINED_FINANCE_UI_BROWSER2'


def expected(repo,here):
    rules=json.loads((here/'WORKFLOW_ORIGIN.json').read_bytes())
    for path,digest in rules.items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    value=deepcopy(yaml.safe_load((repo/PARENT).read_bytes()))
    old=yaml.safe_load((repo/OLD_UI).read_bytes())
    old_steps=[s for job in old['jobs'].values()for s in job['steps']]
    browser=[s for s in old_steps if s.get('name')=='Install pinned browser runtime and check the exact current progress host']
    assert len(browser)==1
    value['name']='CP7 D17-18 qualified combined finance real Auth desktop mobile'
    value['on']['push']['branches']=['astra-b/d17-18-combined-finance-browser-qualification-20261028']
    value['on']['push']['paths']=[TARGET,FOLDER+'/**']
    value['concurrency']['group']='cp7-d17-18-combined-finance-browser-${{ github.run_id }}'
    job=value['jobs']['p21'];job['name']=value['name'];steps=job['steps']
    def step(name):
        found=[s for s in steps if s.get('name')==name];assert len(found)==1,name;return found[0]
    anchor=step('Admit exact D3 first outcome and factory progress all7 source')
    additions=[
        dict(name='Fetch exact own combined seven-group Original and package',**{'working-directory':'auditor'},
            env={'GH_TOKEN':'${{ github.token }}'},run='python '+FOLDER+'/fetch_combined.py'),
        dict(name='Fetch exact UI Native6 prerequisite for unchanged real Auth cases',**{'working-directory':'auditor'},
            env={'GH_TOKEN':'${{ github.token }}'},run='python scripts/current-progress-finance-ui-browser-qualification/fetch_original.py'),
        dict(name='Verify closed combined browser and unchanged source boundaries before DB',**{'working-directory':'auditor'},
            run='python -m unittest discover -s '+FOLDER+' -p "test*.py"'),
        dict(name='Admit full combined backend and unchanged UI sources before DB',**{'working-directory':'auditor'},
            run='python '+FOLDER+'/admission.py')]
    index=steps.index(anchor)+1;steps[index:index]=additions
    runtime=step('Run all7 with unchanged D3 finance and read-only factory progress observation')
    browser_step=deepcopy(browser[0])
    browser_step['run']+='node --check '+FOLDER+'/browser.mjs\nnode --test '+FOLDER+'/console_evidence.test.mjs\n'
    steps.insert(steps.index(runtime),browser_step)
    runtime['name']='Run real Auth desktop and mobile on exact qualified combined backend'
    runtime['run']="python '../auditor/"+FOLDER+"/probe.py'"
    logs=step('Preserve exact original JSON report bytes in a bounded compressed log receipt')
    prior='CP7_D17_18_FACTORY_PROGRESS_NATIVE_SOURCE_CRON7'
    assert logs['run'].count(prior)==1;logs['run']=logs['run'].replace(prior,LABEL)
    upload=[s for s in steps if s.get('uses','').startswith('actions/upload-artifact@')]
    old_upload=[s for s in old_steps if s.get('uses','').startswith('actions/upload-artifact@')]
    assert len(upload)==len(old_upload)==1
    upload[0]['with']['name']='cp7-d17-18-combined-finance-browser-${{ github.run_attempt }}'
    upload[0]['with']['path']=old_upload[0]['with']['path']
    return value


def check(repo,here,*,actual=None):
    value=yaml.safe_load((repo/TARGET).read_bytes())if actual is None else actual
    assert value==expected(repo,here),'COMBINED_BROWSER_UNDECLARED_WORKFLOW_CHANGE'
    return dict(exact_declared_derivation=True,complete_parent_sources_and_bounded_startup_retained=True,
        same_pinned_browser_runtime=True,actual_Auth_desktop_mobile_cases_required=2,
        own_combined_runtime_prerequisite_before_DB=True,raw_reports_and_both_case_screenshots_retained=True,
        existing_tests_not_retried=True,production_go=False)


if __name__=='__main__':
    rules={path:sha256((ROOT/path).read_bytes()).hexdigest()for path in (PARENT,OLD_UI)}
    source=HERE/'WORKFLOW_ORIGIN.json';assert not source.exists();source.write_text(json.dumps(rules,indent=2)+'\n')
    target=ROOT/TARGET;assert not target.exists()
    target.write_text(yaml.safe_dump(expected(ROOT,HERE),sort_keys=False,allow_unicode=True,width=110))
    print(json.dumps(check(ROOT,HERE)))
