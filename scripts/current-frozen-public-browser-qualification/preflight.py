"""Local retained browser/transport preparation; no runtime database or browser credit."""
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
        cfg=json.loads((HERE/'CONFIG.json').read_bytes());kind=cfg['kind']
        guard=load('public_retained_preflight_guard',HERE/'source_guard.py');source=guard.check(REPO,HERE)
        probe=load('public_retained_preflight_probe',HERE/'probe.py')
        assert len(probe.IDS)==len(set(probe.IDS))==cfg['count']
        text=(HERE/'probe.py').read_text();refused=[]
        for name,a,b in [
            ('partial_composer','import cp7_current_frozen_public_installation as quote_capability','import cp7_current_versioned_performance_installation as quote_capability'),
            ('old_native_admission','current-frozen-public-native-qualification/probe.py','current-versioned-performance-native-qualification/probe.py'),
            ('cleanup_guard_removed',"group.get('database_remaining')==0",'True'),
            ('inverse_guard_removed',"assert report['quiesce_before_removal']['clear'],'OW09_CHAIN_REMOVAL_LOCK_WAIT_EXHAUSTED'",'assert True')]:
            assert a in text,name
            try:guard.check(REPO,HERE,probe_text=text.replace(a,b))
            except AssertionError:refused.append(name)
            else:raise AssertionError(('GUARD_WEAKENING_ACCEPTED',name))
        route=None
        if kind=='transport':
            t=probe.transport;target=t.target;state={};leaf=state
            for _ in range(30):leaf['predecessor']={};leaf=leaf['predecessor']
            marker=object();seen=[]
            def checker(cur):seen.append(cur);return marker
            hooks=(t.policy.native.install,t.evaluation.native.install,target.original.install,target.STATE,target.CHECKER)
            admin=target.plan.b.api.admin;target.plan.b.api.admin=lambda cur:None
            try:
                with t.installed(probe.native.business,state,checker):
                    assert target.STATE is state
                    assert target.install('CUR')==(None,None,state)
                    assert target.verify_full('CUR',state)is marker
                    try:target.verify_full('CUR',state['predecessor'])
                    except AssertionError:pass
                    else:raise AssertionError('WRONG_CURRENT_FULL_STATE_ACCEPTED')
            finally:target.plan.b.api.admin=admin
            assert hooks==(t.policy.native.install,t.evaluation.native.install,target.original.install,target.STATE,target.CHECKER)
            assert seen==['CUR','CUR']
            route=dict(full_state_identity_verified=True,wrong_state_refused=True,all_setup_hooks_restored=True)
        else:
            r=subprocess.run(['node',str(HERE/'check-imports.mjs')],capture_output=True,text=True)
            assert r.returncode==0,r.stderr;route=json.loads(r.stdout)
            assert route['actual_ESM_modules_loaded']==3 and route['case_ids']==list(probe.IDS)and route['browser_executed']is False
        wf=yaml.safe_load((REPO/('.github/workflows/cp7-current-frozen-public-'+kind+'.yml')).read_text());shells=0
        assert wf['on']['push']['branches']==['astra-a/d17-14-frozen-public-'+kind+'-20261026']
        for step in wf['jobs']['p21']['steps']:
            if 'run'in step:
                r=subprocess.run(['bash','-n'],input=step['run'],capture_output=True,text=True)
                assert r.returncode==0,(step.get('name'),r.stderr);shells+=1
        for p in HERE.glob('*.py'):ast.parse(p.read_text())
        result=dict(status='PASS_LOCAL_PREPARATION_ONLY',kind=kind,case_count=cfg['count'],source_guard=source,
            rejected_controls=refused,local_route_checks=route,bash_steps=shells,
            SOURCE_bound=(HERE/'SOURCE.json').exists(),database_executed=False,runtime_qualified=False,
            new_public_finance_UI_claim=False,production_go=False,independent_acceptance=False)
        (HERE/'LOCAL_PREFLIGHT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
    finally:psycopg.connect=original
if __name__=='__main__':run()
