"""Prepared-candidate checks only; do not open a database or bind missing evidence."""
from pathlib import Path
import ast,importlib.util,json,re,subprocess,sys
import yaml
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.dont_write_bytecode=True

def main():
    spec=importlib.util.spec_from_file_location('prepared_progress_guard',HERE/'source_guard.py')
    guard=importlib.util.module_from_spec(spec);spec.loader.exec_module(guard)
    result=guard.check(REPO,HERE)
    required=json.loads((HERE/'BUSINESS_GUARDS.json').read_bytes())
    path='scripts/current-progress-finance-ui-browser-qualification/browser.mjs'
    text=(REPO/path).read_text();negative=[]
    for token in required[path][-5:]:
        try:guard.check(REPO,HERE,{path:text.replace(token,'REMOVED_NEW_GUARD',1)})
        except AssertionError:negative.append(token)
        else:raise AssertionError(('NEGATIVE_GUARD_ACCEPTED',token))
    assert len(negative)==5
    for p in HERE.glob('*.py'):ast.parse(p.read_text())
    for p in HERE.glob('*.mjs'):subprocess.run(['node','--check',str(p)],check=True,capture_output=True)
    w=yaml.safe_load((REPO/'.github/workflows/cp7-d17-18-progress-finance-ui-browser.yml').read_bytes())
    assert w['on']['push']['branches']==['astra-a/d17-18-progress-finance-ui-browser-20261026']
    assert w['jobs']['p21']['timeout-minutes']==120
    steps=[s for s in w['jobs']['p21']['steps']if 'run'in s]
    for s in steps:
        subprocess.run(['bash','-n'],input=re.sub(r'\$\{\{.*?\}\}','CI_VALUE',s['run'],flags=re.S),text=True,check=True,capture_output=True)
    cfg=json.loads((HERE/'CONFIG.json').read_bytes());assert cfg['choice_head']is None
    assert not(HERE/'SOURCE.json').exists()
    refused=subprocess.run([sys.executable,str(HERE/'bind_source.py'),'--proof','missing','--original','missing'],text=True,capture_output=True)
    assert refused.returncode!=0 and 'ACTUAL_NATIVE6_PASS_REQUIRED_BEFORE_BINDING'in refused.stderr
    assert not(HERE/'SOURCE.json').exists()
    modules=json.loads(subprocess.check_output(['node',str(HERE/'check-imports.mjs')],cwd=REPO,text=True))
    assert modules['cases']==2 and modules['browser_executed']is False
    subprocess.run(['node','--test',str(HERE/'progress_oracle.test.mjs')],check=True)
    receipt=dict(status='PASS_LOCAL_PREPARATION_ONLY',source=result,new_guard_negative_controls=negative,
        oracle_unit_tests=5,module_check=modules,shell_steps_checked=len(steps),missing_actual_Native6_refused_before_binding=True,
        SOURCE_bound=False,actual_database=False,actual_browser=False,production_go=False,independent_acceptance=False)
    (HERE/'LOCAL_PREFLIGHT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(status=receipt['status'],negative_controls=5,shell_steps=len(steps),SOURCE_bound=False,actual_database=False)))

if __name__=='__main__':main()
