"""No-database checks of retained business assertions, routes and workflow syntax."""
from pathlib import Path
import ast, importlib.util, json, subprocess, sys
from types import SimpleNamespace
import yaml

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))

def load(name,path):
    s=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def run():
    import psycopg
    original_connect=psycopg.connect
    def no_db(*args,**kwargs):raise AssertionError('LOCAL_PREFLIGHT_MUST_NOT_CONNECT_DATABASE')
    psycopg.connect=no_db
    try:
        guard=load('public_finance_preflight_guard',HERE/'source_guard.py')
        source=guard.check(REPO,HERE)
        text=(HERE/'cases.py').read_text();rejected=[]
        mutations={
            'legacy_finance_route':text.replace('erp_cp7_request_bounded_frozen_finance_analysis_v2','erp_cp7_request_bounded_finance_analysis_v1'),
            'legacy_operational_route':text.replace('erp_cp7_request_bounded_staged_analysis_v2','erp_cp7_request_bounded_staged_analysis_v1'),
            'partial_composer':text.replace('import cp7_current_frozen_public_installation as product','import cp7_current_frozen_finance_installation as product'),
            'relaxed_request_limit':text.replace("set local statement_timeout='8s'","set local statement_timeout='30s'"),
            'metrics_dropped':text.replace('assert len(metrics)==24','assert len(metrics)>0'),
            'capture_comparison_dropped':text.replace("assert native.stored_capture(cur,sealed['id'])==sealed",'assert True'),
            'current_permission_guard_dropped':text.replace("assert answer.get('sqlstate')=='42501',answer",'assert True'),
        }
        for name,mutant in mutations.items():
            assert mutant!=text,name
            try:guard.check(REPO,HERE,case_text=mutant)
            except AssertionError:rejected.append(name)
            else:raise AssertionError(('SOURCE_MUTATION_ACCEPTED',name))
        raw=(HERE/'utc_snapshot.py').read_bytes()
        try:guard.check(REPO,HERE,snapshot_bytes=raw.replace(b'set(raw)==set(canonical)',b'True'))
        except AssertionError:rejected.append('capture_columns_dropped')
        else:raise AssertionError('CAPTURE_OBSERVER_MUTATION_ACCEPTED')
        probe=load('public_finance_preflight_probe',HERE/'probe.py')
        assert len(probe.IDS)==len(set(probe.IDS))==10
        assert probe.product.CONTRACT=='cp7.current-AB-public-frozen-finance.v1'
        assert probe.product.predecessor.predecessor.predecessor.CONTRACT=='cp7.current-AB-finance-versioned-performance.v1'
        cases=probe.transport;old_staged=cases.staged;calls=[]
        def limited(cur,name,args,actor):
            calls.append((cur,name,args,actor));return {'name':name,'query':json.loads(args[0]),'request':args[1],'actor':actor}
        base={'as_of':'2026-10-26','group_mode':'AS_RECORDED'}
        cases.staged=SimpleNamespace(query=lambda day:dict(base),limited=limited,checked=lambda value,key:value)
        try:
            for kind,changed,route in [('finance',False,cases.REQUEST),('operational',False,cases.OPERATIONAL),('finance',True,cases.REQUEST)]:
                value=cases.request('CUR','2026-10-26','REQUEST_UUID','ACTOR_UUID',kind,changed)
                wanted=dict(base)
                if kind=='finance':wanted['finance_mode']='STAGED'
                if changed:wanted['group_mode']='RESTATED'
                assert value==dict(name=route,query=wanted,request='REQUEST_UUID',actor='ACTOR_UUID')
        finally:cases.staged=old_staged
        assert cases.staged is old_staged and len(calls)==3
        paths=list(HERE.glob('*.py'))
        for p in paths:ast.parse(p.read_text())
        workflow=REPO/'.github/workflows/cp7-current-frozen-public-finance.yml'
        wf=yaml.safe_load(workflow.read_text());steps=wf['jobs']['p21']['steps'];shell_count=0
        assert wf['on']['push']['branches']==['astra-a/d17-14-frozen-public-finance-20261026']
        for step in steps:
            if 'run'in step:
                result=subprocess.run(['bash','-n'],input=step['run'],text=True,capture_output=True)
                assert result.returncode==0,(step.get('name'),result.stderr);shell_count+=1
        result=dict(status='PASS_LOCAL_PREPARATION_ONLY',retained_source=source,
            rejected_controls=rejected,request_routes_checked=3,request_hook_restored=True,
            case_count=10,Auth_cases=3,two_backend_races=7,python_files=len(paths),bash_steps=shell_count,
            database_executed=False,runtime_qualified=False,actual_Auth_HTTP_credit=False,
            SOURCE_bound=(HERE/'SOURCE.json').exists(),production_go=False,independent_acceptance=False)
        (HERE/'LOCAL_PREFLIGHT.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True)
    finally:psycopg.connect=original_connect

if __name__=='__main__':run()
