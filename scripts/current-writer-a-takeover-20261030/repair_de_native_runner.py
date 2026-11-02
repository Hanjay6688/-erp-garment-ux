"""Exact caller-only repair after actual A861 failed before its first case."""
from hashlib import sha256
from pathlib import Path
import ast,json
from intake_common import exact,pin

HEAD='a861af7e748c6ccf1178a45546d87f034bc493a8'
TREE='ac946bb0333b512864d8d69909c166e2d6892522'
NS='scripts/current-complete-de-integration-preparation/'
CONTROL=NS+'OWNING_CALLER_SOURCE_CONTROLS.json'
ORIGIN=NS+'REPAIRED_PERMANENT_REBASE_ORIGIN.json'
SOURCE=NS+'SOURCE.json'
HELPER='''
def inspect_runner_contract(runner):
    """Inspect a module's exact API and original sources; no case execution."""
    for name,parameters in(('strict_group',('name','factory','verify')),('public_state',('cur',))):
        operation=getattr(runner,name,None)
        if not callable(operation)or tuple(inspect.signature(operation).parameters)!=parameters:
            raise ValueError('COMPLETE_DE_REAL_STRICT_RUNNER_API_REQUIRED:'+name)
    first=getattr(runner,'r1',None)
    if first is None or not isinstance(getattr(first,'OUT',None),Path):
        raise ValueError('COMPLETE_DE_REAL_STRICT_RUNNER_ORIGINAL_OUTPUT_REQUIRED')
    files={}
    for module,name in((runner,'cp6_auditor_runner.py'),(first,'cp6_au_r1_probe.py')):
        expected=(ROOT/'scripts'/name).read_bytes()
        actual=Path(module.__file__).read_bytes()
        if actual!=expected:
            raise ValueError('COMPLETE_DE_STRICT_RUNNER_EXACT_FROZEN_SOURCE_REQUIRED:'+name)
        files[name]=dict(bytes=len(actual),sha256=sha256(actual).hexdigest())
    return dict(status='ACTUAL_STRICT_RUNNER_AND_ORIGINAL_OUTPUT_API_ADMITTED_BEFORE_DATABASE',
        runner_source_files=files,strict_group_parameters=['name','factory','verify'],
        public_state_parameters=['cur'],original_output_path=str(first.OUT),
        business_fixture_is_not_the_strict_runner=True,actual_SQL_executed=0,actual_Native_cases=0)


def runner_contract():
    """Resolve the real runner under the owning natural import scope."""
    admission=load('complete_DE_strict_runner_before_any_database',HERE/'admission.py')
    with admission.import_scope(),fixture_imports():
        runner=importlib.import_module('cp6_auditor_runner')
    return runner,inspect_runner_contract(runner)

'''
PATCHES={
    NS+'component.py':((
        '    native=work.native;product=work.product;control=helper.control',
        '    native=work.runner;product=work.product;control=helper.control'),),
    NS+'native_business.py':(
        ('import ast,importlib,importlib.util,json,os,subprocess,sys',
         'import ast,importlib,importlib.util,inspect,json,os,subprocess,sys'),
        ('\ndef bind(state):',HELPER+'\ndef bind(state):'),
        ('fixture=fixture,native=d1.native,product=product,IDS=ids,cases=cases,',
         'fixture=fixture,native=d1.native,runner=runner_contract()[0],product=product,IDS=ids,cases=cases,')),
    NS+'probe.py':((
        '            engine,_=runtime();proof=engine.admitted()',
        "            engine,_=runtime();proof=engine.admitted()\n"
        "            _,runner_api=load('complete_DE_real_strict_runner_preDB_contract',HERE/'native_business.py').runner_contract()\n"
        "            proof['Native30_strict_runner_API']=runner_api"),),
}


def derive(raw,path):
    text=raw.decode();routes=[]
    for previous,following in PATCHES[path]:
        exact(text.count(previous),1,'DE_RUNNER_EXACT_ORIGINAL_CALLER_ANCHOR:'+path)
        exact(text.count(following),0,'DE_RUNNER_REPAIR_MUST_NOT_ALREADY_BE_APPLIED:'+path)
        text=text.replace(previous,following,1)
        routes.append(dict(before=previous,after=following,count=1))
    original=text
    for previous,following in reversed(PATCHES[path]):
        exact(original.count(following),1,'DE_RUNNER_EXACT_CALLER_REVERSE_ANCHOR:'+path)
        original=original.replace(following,previous,1)
    exact(original.encode(),raw,'DE_RUNNER_ENTIRE_ORIGINAL_CALLER_RECOVERED:'+path)
    compile(text,path,'exec')
    return text.encode(),dict(path=path,before=pin(raw),after=pin(text.encode()),routes=routes,
        entire_original_recovered=True,SQL_or_Native_callbacks_changed=False)


def corrected_values(g):
    declaration=json.loads(g.read(SOURCE));before={n:g.read(n)for n in set(declaration['files'])|{SOURCE}}
    values=dict(before);routes=[]
    for path in PATCHES:
        values[path],proof=derive(before[path],path);routes.append(proof)
    correction=dict(status='EXACT_FIXTURE_VERSUS_STRICT_RUNNER_CALLER_REPAIR_NOT_NATIVE_QUALIFICATION',
        original_head=HEAD,original_tree=TREE,original_run_id=41361511976,original_job_id=125012678506,
        original_conclusion='failure',original_qualified_Native_cases=0,
        original_archive=dict(artifact_id=13107391269,bytes=5836880,
            sha256='61ed3baae5560bcdb962818e441773c08df9fc3b540b116f6200cbc71578a24f'),
        first_actual_error="module 'cp7_ow04_native_source_fixture' has no attribute 'public_state'",
        masked_cleanup_error="module 'cp7_ow04_native_source_fixture' has no attribute 'r1'",
        caller_routes=routes,original_business_callback_sources_changed=0,
        strict_runner_body_changed=False,Native_SQL_changed=False,
        owning_runtime_preDB_check_required=True,actual_Native_cases=0,production_go=False,independent_acceptance=False)
    control=json.loads(before[CONTROL]);control['actual_A861_strict_runner_binding_repair']=correction
    values[CONTROL]=(json.dumps(control,indent=2)+'\n').encode()
    origin=json.loads(before[ORIGIN]);origin['actual_A861_strict_runner_binding_repair']=correction
    values[ORIGIN]=(json.dumps(origin,indent=2)+'\n').encode()
    declaration['files']={name:pin(raw)for name,raw in sorted(values.items())if name!=SOURCE}
    values[SOURCE]=(json.dumps(declaration,indent=2)+'\n').encode()
    changed={name for name in before if before[name]!=values[name]}
    exact(changed,set(PATCHES)|{CONTROL,ORIGIN,SOURCE},'DE_RUNNER_ONLY_SIX_EXISTING_OWN_CALLER_CONTROL_PIN_FILES_CHANGE')
    exact(len(values),96,'DE_RUNNER_EXACT_EXISTING_OWN96_NO_ADDITIONAL_PATHS')
    return values,correction
