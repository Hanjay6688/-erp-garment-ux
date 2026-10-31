"""Exercise the actual nested observer against candidate and primary models.

No parent gate is bypassed and no connection is opened: only the exact observer
AST and pure P0 selector run here. Catalogue-query collectors are explicit spies.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import ModuleType,SimpleNamespace
import argparse,ast,json,subprocess

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
OLD='3d64cf509ce9129e02279d2d866e7bcd799ea693'
NS='scripts/current-complete-de-integration-preparation/'


def module(raw,path):
    m=ModuleType('scope_control_pure_P0');m.__file__=str(path)
    exec(compile(raw,str(path),'exec'),m.__dict__);return m


def check():
    # Reuse the existing declared synthetic fixture; do not duplicate its oracle.
    fixture=module((HERE/'p0_dependency_controls.py').read_bytes(),HERE/'p0_dependency_controls.py')
    fn=next(n for n in ast.parse((HERE/'p0_dependency_controls.py').read_bytes()).body
        if isinstance(n,ast.FunctionDef)and n.name=='check')
    prefix=[]
    for node in fn.body:
        if isinstance(node,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='selected'for t in node.targets):break
        prefix.append(node)
    env=dict(fixture.__dict__);exec(compile(ast.Module(body=prefix,type_ignores=[]),'P0_existing_synthetic_fixture','exec'),env)
    candidate=env['base'];primary=deepcopy(candidate)
    primary.update(database='postgres',primary_scheduler_database=True)
    primary['groups']['routines']['rows']=[];primary['groups']['relations']['rows']=[]
    old_observer=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',OLD+':'+NS+'system_metadata.py'])
    old_p0=subprocess.check_output(['/usr/bin/git','-C',str(ROOT),'show',OLD+':'+NS+'p0_dependencies.py'])
    current_observer=(HERE/'system_metadata.py').read_bytes()
    current_p0=(HERE/'p0_dependencies.py').read_bytes()
    def run(observer,selector,kind,data):
        observed=[];loads=[];original=deepcopy(data)
        def collect(cursor):return deepcopy(data)
        def load(name,path):
            loads.append(path.name)
            if path.name=='p0_dependencies.py':return module(selector,HERE/'p0_dependencies.py')
            def capture(cursor,base):observed.append(path.name);return {'model':path.name}
            return SimpleNamespace(capture=capture)
        fn=[n for n in ast.walk(ast.parse(observer))if isinstance(n,ast.FunctionDef)and n.name=='observe']
        assert len(fn)==1
        scope=dict(collector=SimpleNamespace(capture=collect,capture_scheduler=collect),
            kind=kind,load=load,HERE=HERE)
        exec(compile(ast.Module(body=fn,type_ignores=[]),'exact_owning_metadata_observer','exec'),scope)
        result=scope['observe'](object());assert data==original
        expected=['execution_oids.py','dispatch_oids.py']
        if kind=='candidate'and b'P0_privilege_supplement'in observer:expected.append('p0_privileges.py')
        assert observed==expected
        return result,loads
    try:run(old_observer,old_p0,'primary_scheduler',primary)
    except ValueError as error:assert str(error)=='DE_P0_ALL_SIX_FUNCTIONS_REQUIRED';first=str(error)
    else:raise AssertionError('ORIGINAL_PRIMARY_FAILURE_NOT_REPRODUCED')
    positive,loads=run(current_observer,current_p0,'candidate',candidate)
    assert len(positive['P0_dependency_supplement']['selected']['functions'])==6
    observed,loads=run(current_observer,current_p0,'primary_scheduler',primary)
    assert 'P0_dependency_supplement'not in observed and 'p0_dependencies.py'not in loads
    assert 'P0_privilege_supplement'not in observed and 'p0_privileges.py'not in loads
    negative=[]
    for label,data in [('missing-candidate-function',deepcopy(candidate)),('primary-as-candidate',primary)]:
        if label=='missing-candidate-function':data['groups']['routines']['rows'].pop()
        try:run(current_observer,current_p0,'candidate',data)
        except ValueError:negative.append(label)
        else:raise AssertionError('CANDIDATE_BOUNDARY_REFUSAL_MISSING:'+label)
    selector=module(current_p0,HERE/'p0_dependencies.py')
    for label,db,flag in [('wrong-database','postgres',False),('wrong-marker','cp6_rollback',True),
                         ('missing-marker','cp6_rollback',None),('boolean-integer-marker','cp6_rollback',0)]:
        data=deepcopy(candidate);data.update(database=db,primary_scheduler_database=flag)
        try:selector.capture(data)
        except ValueError as error:assert str(error)=='DE_P0_INSTALLED_CANDIDATE_SNAPSHOT_REQUIRED';negative.append(label)
        else:raise AssertionError('P0_DATABASE_SCOPE_NOT_REFUSED:'+label)
    return dict(status='PASS_ACTUAL_OBSERVER_CANDIDATE_PRIMARY_SCOPE_CONTROLS',
        first_failure=dict(head=OLD,error=first,observer_sha256=sha256(old_observer).hexdigest(),
            kind='PURE_ROUTING_REPRODUCTION_NOT_ACTUAL_ERP_RUN'),
        positive_candidate=1,positive_primary_without_ERP_functions=1,negative_controls=negative,
        original_catalogues_not_mutated=True,system_and_dispatch_collectors_called_on_both=True,
        owning_observer_sha256=sha256(current_observer).hexdigest(),selector_sha256=sha256(current_p0).hexdigest(),
        actual_SQL_executed=0,actual_ERP_calls=0,actual_Native_case_credit=0,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=check();a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],original_failure=result['first_failure']['error'],
        positive=2,negative=len(result['negative_controls']),actual_ERP_calls=0)))
