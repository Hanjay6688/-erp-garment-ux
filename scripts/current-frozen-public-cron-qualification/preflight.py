"""Local source, scheduling and public-route controls; never run a database."""
from pathlib import Path
import ast,importlib.util,json,subprocess,sys,yaml

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def run():
    import psycopg
    original=psycopg.connect
    def no_db(*a,**kw):raise AssertionError('LOCAL_PREFLIGHT_MUST_NOT_CONNECT_DATABASE')
    psycopg.connect=no_db
    try:
        guard=load('public_cron_preflight_guard',HERE/'source_guard.py');source=guard.check(REPO,HERE)
        runner=(HERE/'runner.py').read_text();probe=(HERE/'probe.py').read_text();rejected=[]
        controls={
            'private_request_helper':('runner_text',runner.replace('current-frozen-public-native-qualification/public_finance_cases.py','current-frozen-finance-native-qualification/finance_cases.py')),
            'partial_composer':('runner_text',runner.replace('cp7_current_frozen_public_installation','cp7_current_frozen_finance_installation')),
            'relaxed300s':('runner_text',runner.replace('deadline=started+300','deadline=started+900')),
            'metric_oracle_dropped':('runner_text',runner.replace('assert len(wanted)==24','assert len(wanted)>0')),
            'schedule_definition_changed':('runner_text',runner.replace("assert defs==[k4.RUNNER],('CURRENT_CRON_DEFINITION_CHANGED',defs)",'assert True')),
            'money_stock_HPP_check_dropped':('runner_text',runner.replace('assert erp_data(cur)==before and product.catalog._catalog_rows(cur)==before_catalog','assert True')),
            'restore_rows_dropped':('probe_text',probe.replace('assert product.catalog._data(cur)==baseline_data','assert True')),
            'used_guard_dropped':('probe_text',probe.replace('assert str(error)==product.USED_ERROR','assert True')),
        }
        for name,(key,mutant)in controls.items():
            assert mutant!=(runner if key=='runner_text'else probe),name
            try:guard.check(REPO,HERE,**{key:mutant})
            except AssertionError:rejected.append(name)
            else:raise AssertionError(('CONTROL_ACCEPTED',name))
        runtime=load('public_cron_preflight_probe',HERE/'probe.py')
        assert runtime.product.CONTRACT=='cp7.current-AB-public-frozen-finance.v1'
        assert runtime.product.predecessor.predecessor.predecessor.CONTRACT=='cp7.current-AB-finance-versioned-performance.v1'
        helper=runtime.runner.finance;staged=helper.staged_original;prior=staged.limited;calls=[]
        def capture(cur,name,args,subject=None,timeout=staged.STATEMENT_TIMEOUT):
            calls.append((cur,name,args,subject,timeout));return calls[-1]
        staged.limited=capture
        try:
            for name,want in [('erp_cp7_request_bounded_finance_analysis_v1','erp_cp7_request_bounded_frozen_finance_analysis_v2'),('erp_cp7_request_bounded_staged_analysis_v1','erp_cp7_request_bounded_staged_analysis_v2'),('erp_cp7_get_staged_analysis_v1','erp_cp7_get_staged_analysis_v1')]:
                args=('EXACT_QUERY','EXACT_UUID')
                assert helper.staged.limited('CUR',name,args,'ACTOR','8s')==('CUR',want,args,'ACTOR','8s')
        finally:staged.limited=prior
        assert staged.limited is prior and len(calls)==3
        wf=yaml.safe_load((REPO/'.github/workflows/cp7-current-frozen-public-cron.yml').read_text());count=0
        assert wf['on']['push']['branches']==['astra-a/d17-14-frozen-public-cron-20261026']
        for step in wf['jobs']['p21']['steps']:
            if 'run'in step:
                r=subprocess.run(['bash','-n'],input=step['run'],text=True,capture_output=True)
                assert r.returncode==0,(step.get('name'),r.stderr);count+=1
        for p in HERE.glob('*.py'):ast.parse(p.read_text())
        receipt=dict(status='PASS_LOCAL_PREPARATION_ONLY',source_guard=source,rejected_controls=rejected,
            request_routes_checked=3,request_hook_restored=True,bash_steps=count,case_ids=list(runtime.IDS),
            SOURCE_bound=(HERE/'SOURCE.json').exists(),actual_cron_claim=False,actual_Auth_HTTP_credit=False,
            database_executed=False,production_go=False,independent_acceptance=False)
        (HERE/'LOCAL_PREFLIGHT.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
    finally:psycopg.connect=original
if __name__=='__main__':run()
