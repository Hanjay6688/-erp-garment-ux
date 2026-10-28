"""Retain A3194 setup/admissions; substitute only B's existing real-Auth runtime."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json,subprocess,yaml
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PARENT='.github/workflows/cp7-d17-18-factory-live-heartbeat.yml'
TARGET='.github/workflows/cp7-d17-18-combined-finance-browser.yml'
FOLDER='scripts/current-finance-combined-browser-qualification'
LABEL='CP7_D17_18_COMBINED_FINANCE_UI_BROWSER2'
BRANCH='astra-b/d17-18-qualified-backend3194-browser-qualification-20261028'
def expected(repo,here):
    cfg=json.loads((here/'CONFIG.json').read_bytes())
    rule=json.loads((here/'WORKFLOW_3194_ORIGIN.json').read_bytes())
    raw=(repo/PARENT).read_bytes();assert sha256(raw).hexdigest()==rule['sha256']
    assert raw==subprocess.check_output(['git','-C',str(repo),'show',rule['head']+':'+PARENT])
    value=deepcopy(yaml.safe_load(raw));value['name']='CP7 B qualified3194 real Auth desktop mobile'
    value['on']['push']['branches']=[BRANCH];value['on']['push']['paths']=[TARGET,FOLDER+'/**']
    value['concurrency']['group']='cp7-B-qualified3194-browser-${{ github.run_id }}'
    job=value['jobs']['p21'];job['name']=value['name'];job['env']['D17_18_SELECTED_BACKEND_ROOT']='${{ github.workspace }}/auditor'
    steps=job['steps'];steps[0]['with']['ref']=cfg['backend_head']
    frontend=deepcopy(steps[0]);frontend['with']['path']='browser-source';frontend['with'].pop('ref');steps.insert(1,frontend)
    def step(name):
        found=[s for s in steps if s.get('name')==name];assert len(found)==1,name;return found[0]
    anchor=step('Admit exact unchanged backend and six actual retained groups')
    additions=[dict(name='Fetch exact backend3194 and retained11c archives for B browser',**{'working-directory':'browser-source'},env={'GH_TOKEN':'${{ github.token }}'},run='python '+FOLDER+'/fetch_combined.py'),
      dict(name='Verify B successor boundaries before DB',**{'working-directory':'browser-source'},run='python -m unittest discover -s '+FOLDER+' -p "test_3194*.py"'),
      dict(name='Admit actual selected backend and B browser before DB',**{'working-directory':'writer'},run="python '../browser-source/"+FOLDER+"/admission.py'")]
    index=steps.index(anchor)+1;steps[index:index]=additions
    runtime=step('Run one fresh factory closure and complete restoration; retain six exact 11c groups')
    browser=dict(name='Install pinned browser runtime and verify declared B UI successor',**{'working-directory':'browser-source'},run='''set -euo pipefail
npm ci --no-audit --no-fund
npx playwright install --with-deps chromium
npx tsc --noEmit --project tsconfig.app.json
npx tsc --noEmit --project scripts/cp7_current_progress_finance_ui/tsconfig.json
node --test scripts/current-finance-combined-browser-qualification/console_evidence.test.mjs
node --test scripts/current-progress-finance-ui-browser-qualification/progress_oracle.test.mjs
node scripts/current-finance-combined-browser-qualification/check_build_3194.mjs
ln -s "$GITHUB_WORKSPACE/browser-source/node_modules" "$GITHUB_WORKSPACE/auditor/node_modules"
''')
    # Browser/source installation is before database startup. A build failure
    # cannot consume the aligned database or leave an unexecuted install.
    start=step('Start disposable database');steps.insert(steps.index(start),browser)
    runtime['name']='Run real Auth desktop and mobile on exact qualified combined backend'
    runtime['run']="python '../browser-source/"+FOLDER+"/probe.py'"
    logs=step('Preserve exact original JSON report bytes in a bounded compressed log receipt')
    logs['run']=logs['run'].replace('CP7_D17_18_FACTORY_LIVE_HEARTBEAT_CLOSURE1',LABEL)
    upload=[s for s in steps if s.get('uses','').startswith('actions/upload-artifact@')];assert len(upload)==1
    upload[0]['with']['name']='cp7-B-qualified3194-browser-${{ github.run_attempt }}'
    return value

def check(repo,here,*,actual=None):
    value=yaml.safe_load((repo/TARGET).read_bytes())if actual is None else actual
    assert value==expected(repo,here),'COMBINED_BROWSER_UNDECLARED_WORKFLOW_CHANGE'
    return dict(exact_declared_derivation=True,entire_frozen_backend_checkout_required=True,complete_A_prerequisites_unchanged=True,
        same_pinned_browser_runtime=True,actual_Auth_desktop_mobile_cases_required=2,raw_reports_and_screenshots_retained=True,heavy_backend_groups_repeated=False,production_go=False)
