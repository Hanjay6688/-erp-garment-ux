"""Closed before all product/package imports; complete unchanged D1 engine."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import importlib.util
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name,path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


@load('continuation_scoped_runtime_arguments',HERE/'argv_scope.py').inherited_entrypoint
def runtime():
    load('continuation_before_any_runtime_gate',HERE/'gate.py').selected(json.loads((HERE/'CONFIG.json').read_bytes()))
    for relative in ('scripts','scripts/cp7_customer_credit/consumer','scripts/cp7_customer_credit/reconciliation/native',
                     'scripts/cp7_customer_credit/native','scripts/cp7_customer_credit/initial-settlement'):
        sys.path.insert(0,str(ROOT/relative))
    original = ROOT/'scripts/current-vendor-receivable-qualification/probe.py'
    code, derivation = load('continuation_exact_engine_derivation',HERE/'derive.py').derive(original.read_bytes())
    engine = ModuleType('continuation_complete_existing_D1_package_engine'); engine.__file__ = str(original)
    exec(compile(code,str(original),'exec'),engine.__dict__)
    from cp7_credit_correction_de import composition as product
    component = load('continuation_native3_component',HERE/'component.py')
    engine.product = product
    engine.runner = SimpleNamespace(CASE=component.CASE,exercise=component.exercise,scheduler_quiet=component.scheduler_quiet)
    engine.IDS = (component.CASE,)
    engine.LABEL = 'CP7_CREDIT_D1_CONTINUATION_NATIVE3'
    engine.PRE_DUMP = '/tmp/credit_d1_continuation3_pre.dump'
    engine.OUT = ROOT/'cp6-proof/t3'/(engine.LABEL+'.json')
    engine.admitted = lambda:load('continuation_complete_source_admission',HERE/'admission.py').admitted(product,derivation)
    return engine


def execute():
    load('continuation_execute_closed_gate',HERE/'gate.py').selected(json.loads((HERE/'CONFIG.json').read_bytes()))
    if os.environ.get('D1_CONT_NATIVE_CONFIRM') != 'cp6_rollback':
        raise ValueError('D1_CONT_EXPLICIT_DISPOSABLE_QUALIFICATION_CONFIRMATION_REQUIRED')
    engine = runtime(); engine.admitted()
    engine.package._writer_runtime = lambda browser_mode=False:engine.run()
    engine.package.run('install')


if __name__ == '__main__':
    if sys.argv[1:]:
        raise SystemExit('D1 continuation Native3 execution accepts no arguments.')
    execute()
