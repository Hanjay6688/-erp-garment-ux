"""Bind the real concurrency caller to the retained private race derivative.

The c397 source admitted the new schedule but still loaded the original race
module. Check the actual loader before DB imports and the actual callable at
runtime. Neither a source inventory entry nor a protocol double earns credit.
"""
from hashlib import sha256
from pathlib import Path
from types import CodeType
import ast
import importlib.util
import json

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
NS='scripts/current-sku-managed-recovery-native27-qualification'
LOADER="business = load('sku_concurrency_current_pocket_races', ROOT / '"+NS+"/races.py')"


def deriver():
    spec=importlib.util.spec_from_file_location('sku27_bound_complete_deriver',HERE/'derive.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def _route(text):
    function=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef)and n.name=='exercise')
    assigned=[n for n in ast.walk(function)if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='business'for t in n.targets)]
    expected=ast.parse(LOADER).body[0]
    if len(assigned)!=1 or ast.dump(assigned[0])!=ast.dump(expected):
        raise ValueError('SKU27_CURRENT_RACE_CALLER_ROUTE_REQUIRED')
    binding=[n for n in ast.walk(function)if isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)
             and isinstance(n.func.value,ast.Name)and n.func.value.id=='race_binding'and n.func.attr=='require_runtime_module']
    if len(binding)!=1 or ast.unparse(binding[0])!='race_binding.require_runtime_module(business)':
        raise ValueError('SKU27_ACTUAL_RACE_CALLABLE_GATE_REQUIRED')
    return ast.unparse(assigned[0])


def source_check():
    d=deriver();caller,_=d.derive('concurrency');callee,proof=d.derive('races')
    wrapper=HERE/'races.py'
    if not wrapper.is_file()or wrapper.is_symlink():raise ValueError('SKU27_CURRENT_RACE_WRAPPER_REQUIRED')
    route=_route(caller)
    return dict(status='EXACT_CURRENT_CALLER_TO_PRIVATE_RACE_SOURCE_ONLY',loader_statement=route,
        wrapper_path=NS+'/races.py',wrapper_sha256=sha256(wrapper.read_bytes()).hexdigest(),
        caller_derived_sha256=sha256(caller.encode()).hexdigest(),
        race_derived_sha256=sha256(callee.encode()).hexdigest(),derivation=proof,
        actual_Native_cases=0,actual_two_session_races=0,production_go=False,independent_acceptance=False)


def require_runtime_module(module):
    source=source_check();d=deriver();text,proof=d.derive('races')
    filename=str(ROOT/d.SOURCES['races'][0]);compiled=compile(text,filename,'exec')
    expected=[c for c in compiled.co_consts if isinstance(c,CodeType)and c.co_name=='exercise']
    actual=getattr(module,'exercise',None)
    if len(expected)!=1 or not callable(actual)or actual.__code__!=expected[0]or actual.__code__.co_filename!=filename:
        raise ValueError('SKU27_ACTUAL_CURRENT_RACE_CODE_REQUIRED')
    if json.dumps(getattr(module,'SKU27_DERIVATION',None),sort_keys=True)!=json.dumps(proof,sort_keys=True):
        raise ValueError('SKU27_ACTUAL_CURRENT_RACE_DERIVATION_REQUIRED')
    schedule=getattr(module,'schedule',None)
    if schedule is None or actual.__globals__.get('schedule')is not schedule:
        raise ValueError('SKU27_ACTUAL_RACE_SCHEDULE_GLOBAL_REQUIRED')
    if Path(schedule.__file__).resolve()!=HERE/'race_schedule.py':
        raise ValueError('SKU27_ACTUAL_RACE_SCHEDULE_MODULE_REQUIRED')
    schedule_code=compile((HERE/'race_schedule.py').read_bytes(),str(HERE/'race_schedule.py'),'exec')
    expected_functions={c.co_name:c for c in schedule_code.co_consts if isinstance(c,CodeType)}
    for name in ('run','require_contention'):
        actual_function=getattr(schedule,name,None)
        if not callable(actual_function)or actual_function.__code__!=expected_functions[name]or actual_function.__code__.co_filename!=str(HERE/'race_schedule.py'):
            raise ValueError('SKU27_ACTUAL_RACE_SCHEDULE_CODE_REQUIRED:'+name)
    return dict(source,status='ACTUAL_CURRENT_RACE_MODULE_BOUND_BEFORE_CALLBACKS',
        compiled_function_identity=True,actual_schedule_global_identity=True,
        financial_case_success_not_implied=True)
