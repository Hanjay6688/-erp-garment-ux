"""Read actual prepared callers and their exact strict-runner source contracts.

No ERP import, parent-gate replacement, database call, test case, or ref write.
This checks static bindings; an eventual actual preDB graph check stays required.
"""
from pathlib import Path
from hashlib import sha256
import argparse,ast,json,os,subprocess

RUNNER_PIN=dict(bytes=14911,sha256='2c74439f7e919e2adb2484bc774bef4881e71237124f2e6b6dabdab141348ea7')
R1_PIN=dict(bytes=29829,sha256='451d3d5cbf34fed8f6ba0bf6445cee08e5198d6979f1fd1fbc68f9e299d3724b')


def require(value,label):
    if not value:raise ValueError('DOWNSTREAM_ACTUAL_STRICT_RUNNER_SOURCE_REQUIRED:'+label)


def assignment(tree,name):
    values=[]
    for n in ast.walk(tree):
        if not isinstance(n,ast.Assign):continue
        for target in n.targets:
            if isinstance(target,ast.Name)and target.id==name:values.append(n.value)
            elif isinstance(target,ast.Tuple)and isinstance(n.value,ast.Tuple):
                for left,right in zip(target.elts,n.value.elts):
                    if isinstance(left,ast.Name)and left.id==name:values.append(right)
    require(len(values)==1,'one binding '+name)
    return ast.unparse(values[0])


def check(root,kind,head):
    root=root.resolve();env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_OPTIONAL_LOCKS='0')
    pins={}
    def source(name):
        path=root/name;raw=path.read_bytes()
        require(not path.is_symlink(),'regular source '+name)
        original=subprocess.check_output(['/usr/bin/git','-C',str(root),'show',head+':'+name],env=env)
        require(raw==original,'exact declared source '+name)
        pins[name]=dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
        return ast.parse(raw)
    def imports(tree,module,alias):
        require(any(isinstance(n,ast.Import)and any(a.name==module and(a.asname or a.name)==alias
            for a in n.names)for n in tree.body),'import '+module+' as '+alias)
    routes=[]
    def route(name,symbol,expression):
        require(assignment(source(name),symbol)==expression,name+':'+symbol)
        routes.append(dict(path=name,symbol=symbol,expression=expression))
    if kind=='FREE':
        route('scripts/current-de-free-date-preparation/component.py','native','work.runner')
        route('scripts/current-de-free-date-preparation/native_free.py','runner',
            "importlib.import_module('cp6_auditor_runner')")
        tree=source('scripts/current-de-free-date-preparation/native_free.py')
        require(any(isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='SimpleNamespace'
            and any(k.arg=='runner'and isinstance(k.value,ast.Name)and k.value.id=='runner'for k in n.keywords)
            for n in ast.walk(tree)),'returned actual runner object')
    elif kind=='AFUI':
        route('scripts/cp7_accessory_nonpayable/qualification_component.py','native','control.native')
        route('scripts/cp7_accessory_nonpayable/qualification_component.py','control','helper.control')
        tree=source('scripts/cp7_p21_current_chain_rehearsal_probe.py')
        require(assignment(tree,'spec')=="importlib.util.spec_from_file_location('p21_current_restore_helpers', REPO / 'scripts/ow04-payment-used-restore-qualification/probe.py')",'physical helper path')
        imports(source('scripts/ow04-payment-used-restore-qualification/probe.py'),'source_probe','control')
        tree=source('scripts/ow04-payment-source-qualification/source_probe.py')
        imports(tree,'cp7_full_ow04_probe','previous')
        route('scripts/ow04-payment-source-qualification/source_probe.py','native','previous.native')
        imports(source('scripts/cp7_full_ow04_probe.py'),'cp7_ow04_probe','core')
        route('scripts/cp7_full_ow04_probe.py','native','core.native')
        imports(source('scripts/cp7_ow04_probe.py'),'cp7_f05_analysis_probe','predecessor')
        route('scripts/cp7_ow04_probe.py','native','predecessor.native')
        imports(source('scripts/cp7_f05_analysis_probe.py'),'cp6_auditor_runner','native')
    else:raise ValueError('EXPLICIT_FREE_OR_AFUI_REQUIRED')
    runner=source('scripts/cp6_auditor_runner.py')
    require(pins['scripts/cp6_auditor_runner.py']==RUNNER_PIN,'unchanged qualified strict runner')
    functions={n.name:n for n in runner.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))}
    require([a.arg for a in functions['strict_group'].args.args]==['name','factory','verify'],'strict_group API')
    require([a.arg for a in functions['public_state'].args.args]==['cur'],'public_state API')
    require(assignment(runner,'r1')=='awp.r1','actual retained Original owner')
    imports(source('scripts/cp6_aw_probe.py'),'cp6_au_r1_probe','r1')
    r1=source('scripts/cp6_au_r1_probe.py')
    require(pins['scripts/cp6_au_r1_probe.py']==R1_PIN,'unchanged r1 owner')
    require(assignment(r1,'OUT')=="AUDITOR / 'cp6-proof/au-r1'",'actual Original output Path')
    return dict(status='ACTUAL_PREPARED_'+kind+'_STRICT_RUNNER_STATIC_BINDING_AND_API_PASS',
        head=head,source_pins=pins,bindings=routes,actual_ERP_imports=0,actual_SQL_executed=0,
        parent_gates_bypassed=False,actual_Native_cases=0,actual_Auth_HTTP_cases=0,
        actual_browser_cases=0,actual_two_session_races=0,
        final_actual_parent_preDB_natural_graph_still_required=True,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--free',type=Path,required=True)
    p.add_argument('--afui',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(not a.output.exists(),'new observation output')
    v=dict(FREE=check(a.free,'FREE','fe21e26e9ca1fb8428dc0b1f86f16b03de2c9fcb'),
        AFUI=check(a.afui,'AFUI','098dbd8769cbbf6f0502750a7c2a770959e02385'))
    with a.output.open('x')as f:json.dump(v,f,indent=2);f.write('\n')
    print(json.dumps({k:x['status']for k,x in v.items()}))
