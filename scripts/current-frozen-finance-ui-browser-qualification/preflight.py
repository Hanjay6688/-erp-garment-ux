"""Local source checks only; never open a database or claim browser execution."""
from pathlib import Path
import ast,importlib.util,json,os,re,subprocess,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
import psycopg,yaml
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def main():
    original=psycopg.connect
    def forbidden(*args,**kwargs):raise AssertionError('LOCAL_PREFLIGHT_MUST_NOT_CONNECT_DATABASE')
    psycopg.connect=forbidden
    try:
        guard=load('A_finance_UI_guard_preflight',HERE/'source_guard.py');positive=guard.check(REPO,HERE)
        negatives=[]
        for path,requirements in guard.REQUIRED.items():
            text=(REPO/path).read_text()
            for required in requirements:
                try:guard.check(REPO,HERE,{path:text.replace(required,'REMOVED_BUSINESS_GUARD',1)})
                except (AssertionError,SyntaxError):negatives.append(dict(path=path,guard=required,status='REFUSED'))
                else:raise AssertionError(('NEGATIVE_GUARD_ACCEPTED',path,required))
        assert len(negatives)==17
        for p in [*HERE.glob('*.py'),REPO/'scripts/cp7_current_frozen_finance_ui/browser_fixture.py']:ast.parse(p.read_text())
        workflow=yaml.safe_load((REPO/'.github/workflows/cp7-current-frozen-finance-ui-browser.yml').read_text())
        steps=[s for j in workflow['jobs'].values() for s in j['steps'] if 'run' in s]
        for step in steps:
            script=re.sub(r'\$\{\{.*?\}\}','CI_VALUE',step['run'],flags=re.S)
            subprocess.run(['bash','-n'],input=script,text=True,check=True,capture_output=True)
        out=subprocess.check_output(['node','scripts/current-frozen-finance-ui-browser-qualification/check-imports.mjs'],cwd=REPO,text=True)
        modules=json.loads(out)
        assert modules['cases']==2 and modules['browser_executed'] is False
        result=dict(status='PASS_LOCAL_PREPARATION_ONLY',positive=positive,negative_controls=negatives,
                    bash_steps=len(steps),module_check=modules,
                    readiness_oracle='Fresh independent desktop clone must prove official report READY; posted mobile fixture must remain BLOCKED as observed in Native52. No source facts rewritten to force READY.',
                    positive_baseline_READY_runtime_proven=False,SOURCE_bound=False,actual_database=False,production_go=False)
        (HERE/'LOCAL_PREFLIGHT.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:result[k] for k in ('status','bash_steps','SOURCE_bound','actual_database','production_go')}|{'negative_controls':len(negatives)}))
    finally:psycopg.connect=original
if __name__=='__main__':main()
