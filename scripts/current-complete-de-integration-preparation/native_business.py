"""Closed binding of unchanged D1 Native13 and E Native17 business callbacks.

Import supplies no ERP import, connection, SQL, Auth, runtime or case credit.
An owning actual disposable package must admit its complete parent first.
"""
from pathlib import Path
from hashlib import sha256
from types import SimpleNamespace
from contextlib import contextmanager
import ast,importlib,importlib.util,json,os,subprocess,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
NATIVE_HEAD='928246e5f62637c7c6457e57d73d0699196e3408'
NATIVE_TREE='581303d5f0df8a6ae40f6d7ec0fab7c06678ed9a'
FIXTURE_PATHS=('scripts','scripts/cp7_customer_credit/consumer',
    'scripts/cp7_customer_credit/reconciliation/native','scripts/cp7_customer_credit/native',
    'scripts/cp7_customer_credit/initial-settlement')


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def literal(raw,name):
    values=[ast.literal_eval(n.value)for n in ast.parse(raw).body if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name)and t.id==name for t in n.targets)]
    if len(values)!=1:raise ValueError('COMPLETE_DE_EXACT_NATIVE_LITERAL_REQUIRED:'+name)
    return values[0]


def source_controls():
    record=json.loads((HERE/'NATIVE_CALLBACK_ORIGIN.json').read_bytes())
    if(record['source_head']!=NATIVE_HEAD or record['source_tree']!=NATIVE_TREE
       or record['actual_Native_cases']!=0 or record['source_callbacks_changed']!=0):
        raise ValueError('COMPLETE_DE_EXACT_NATIVE30_PUBLIC_SOURCE_REQUIRED')
    def git(*args):
        return subprocess.check_output(['/usr/bin/git','-C',str(ROOT),*args],
            env=dict(os.environ,GIT_OPTIONAL_LOCKS='0',GIT_NO_LAZY_FETCH='1'))
    if git('rev-parse',NATIVE_HEAD+'^{tree}').decode().strip()!=NATIVE_TREE:
        raise ValueError('COMPLETE_DE_EXACT_NATIVE30_ORIGIN_TREE_REQUIRED')
    expected={'scripts/cp7_credit_correction_de/'+n for n in('cases.py','e_cases.py','native_fixture.py')}
    if set(record['files'])!=expected:raise ValueError('COMPLETE_DE_EXACT_THREE_NATIVE_SOURCES_REQUIRED')
    texts={}
    for name,pin in record['files'].items():
        path=ROOT/name;raw=path.read_bytes()
        if(path.is_symlink()or len(raw)!=pin['bytes']or sha256(raw).hexdigest()!=pin['sha256']
           or raw!=git('show',NATIVE_HEAD+':'+name)):
            raise ValueError('COMPLETE_DE_UNCHANGED_NATIVE_SOURCE_REQUIRED:'+name)
        compile(raw,str(path),'exec');texts[Path(name).name]=raw
    d1=literal(texts['cases.py'],'IDS');e=literal(texts['e_cases.py'],'IDS')
    if(list(d1)!=record['D1_case_ids']or list(e)!=record['E_case_ids']
       or len(d1)!=13 or len(e)!=17 or len(set(d1+e))!=30):
        raise ValueError('COMPLETE_DE_ALL_ORIGINAL_13_AND_17_CALLBACK_IDS_REQUIRED')
    fixture=literal(texts['native_fixture.py'],'SOURCES')
    if len(fixture)!=4:raise ValueError('COMPLETE_DE_EXACT_FOUR_NATIVE_FIXTURE_INPUTS_REQUIRED')
    for name,digest in fixture.values():
        if sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise ValueError('COMPLETE_DE_EXACT_NATIVE_FIXTURE_INPUT_CHANGED:'+name)
    return dict(status='COMPLETE_DE_NATIVE30_SOURCE_ONLY',D1_case_ids=list(d1),E_case_ids=list(e),
        business_source_files=3,frozen_fixture_input_files=4,original_callback_changes=0,
        actual_Native_cases=0,actual_SQL_executed=0,production_go=False,independent_acceptance=False)


@contextmanager
def fixture_imports():
    before=list(sys.path)
    try:
        for name in reversed(FIXTURE_PATHS):sys.path.insert(0,str(ROOT/name))
        yield
    finally:sys.path[:]=before


def bind(state):
    # This exact pending-parent gate precedes even the first ERP import.
    receipt=load('complete_DE_Native_actual_parent_before_ERP',HERE/'admission.py').parent_receipt()
    load('complete_DE_Native_closed_source',HERE/'source.py').preflight()
    origin=source_controls()
    guard=load('complete_DE_Native_whole_parent_source',ROOT/'scripts/cp7_complete_credit_de/composition.py')
    accepted=guard.qualified_parent_sources(receipt,state['complete_parent'])
    if state['qualified_complete_sources']!=accepted:
        raise ValueError('COMPLETE_DE_NATIVE_ACCEPTED_PARENT_SOURCE_PIN_CHANGED')
    with fixture_imports():
        product=importlib.import_module('cp7_complete_credit_de.composition')
        d1=importlib.import_module('cp7_credit_correction_de.cases')
        e=importlib.import_module('cp7_credit_correction_de.e_cases')
        fixture=importlib.import_module('cp7_credit_correction_de.native_fixture')
        for module,name in((product,'cp7_complete_credit_de/composition.py'),
            (d1,'cp7_credit_correction_de/cases.py'),(e,'cp7_credit_correction_de/e_cases.py'),
            (fixture,'cp7_credit_correction_de/native_fixture.py')):
            if Path(module.__file__).resolve()!=ROOT/'scripts'/name:
                raise ValueError('COMPLETE_DE_NATIVE_ACTUAL_MODULE_ORIGIN_REQUIRED:'+name)
        if(e.de is not d1 or d1.fixture is not fixture or state['sources']!=product.sources()
           or list(d1.IDS)!=origin['D1_case_ids']or list(e.IDS)!=origin['E_case_ids']):
            raise ValueError('COMPLETE_DE_NATIVE_NATURAL_BINDING_OR_ACTUAL_SOURCE_CHANGED')
    ids=tuple(origin['D1_case_ids']+origin['E_case_ids'])
    def cases(cursor,today):
        actual=d1.cases(cursor,today)+e.cases(cursor,today)
        if tuple(name for name,_ in actual)!=ids or any(not callable(fn)for _,fn in actual):
            raise ValueError('COMPLETE_DE_NATIVE30_EXACT_ORIGINAL_CALLBACKS_REQUIRED')
        return actual
    return SimpleNamespace(D1=d1,E=e,fixture=fixture,native=d1.native,product=product,IDS=ids,cases=cases,
        source_control=origin,actual_Native_cases=0)
