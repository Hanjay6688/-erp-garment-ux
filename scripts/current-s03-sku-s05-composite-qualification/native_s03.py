"""Private complete Native14 modules; full parent admission precedes ERP import."""
from pathlib import Path
from types import ModuleType,SimpleNamespace
import importlib.util

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def code(name,text,*,path,**bindings):
    module=ModuleType(name);module.__file__=str(path);module.__dict__.update(bindings)
    exec(compile(text,str(path),'exec'),module.__dict__);return module


def modules():
    admission=load('joined_native14_actual_parent_admission',HERE/'admission.py')
    proof=admission.admitted()  # Current exact parents, before any ERP import.
    source=load('joined_native14_whole_private_source_binding',ROOT/'scripts/current-s03-sku-native14-binding/prepare.py')
    texts,derivation=source.prepare()
    fixture=code('joined_native14_fixture',texts['fixture'],path=HERE/'joined_fixture.py')
    lawful=code('joined_native14_lawful_fixture',texts['lawful_fixture'],path=HERE/'joined_lawful_fixture.py')
    def parent_sources(actual):
        if actual!=proof['qualified_SKU_current_installation']:raise ValueError('JOIN_NATIVE14_ACTUAL_SKU_PARENT_SOURCE_CHANGED')
        return dict(status='CURRENT_ROOT_VERIFIED_SKU27_PARENT_FOR_ACTUAL_JOIN',source=proof['qualified_SKU_parent'],
            actual_composite_cases_credited=0,production_go=False)
    core=ModuleType('joined_native14_core');core.__file__=str(HERE/'joined_core.py')
    core.__dict__.update(JOIN_FIXTURE=fixture,JOIN_PARENT_ADMISSION=SimpleNamespace(admit=parent_sources),LAWFUL=lawful,CORE=core)
    exec(compile(texts['core'],core.__file__,'exec'),core.__dict__)
    group=ModuleType('joined_native14_reader_group');group.__file__=str(HERE/'joined_reader_group.py')
    def fresh11(actual):
        group.exact_group(actual,derivation['original11_ids'])
        return dict(status='CURRENT_JOIN_SOURCE_AND_FRESH_FINANCIAL11_ADMITTED',fresh_financial_cases=11,
            reader_cases_before_execution=0,production_go=False)
    reader=code('joined_native14_reader',texts['reader'],path=HERE/'joined_reader.py',
        JOIN_READER_ADMISSION=SimpleNamespace(admit=fresh11),JOIN_CORE=core,LAWFUL=lawful)
    group.__dict__.update(JOIN_CONFIG=dict(original_Native11_ids=derivation['original11_ids'],reader_Native3_ids=derivation['reader3_ids']),JOIN_READER=reader)
    exec(compile(texts['reader_group'],group.__file__,'exec'),group.__dict__)
    runner=code('joined_native14_complete_runner',texts['native_runner'],path=HERE/'joined_native_runner.py',
        JOIN_BUSINESS=core,CURRENT_READER_IDS=derivation['reader3_ids'],run_actual_reader3=group.run)
    runner.JOIN_DERIVATION=derivation
    return runner,core,derivation


def business_runtime():return modules()[1]


def exercise(conn,cur,database,url,report,state):
    runner,_,proof=modules();report['current_join_private_Native14_binding']=proof
    return runner.exercise(conn,cur,database,url,report,state)
