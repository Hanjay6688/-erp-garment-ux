"""Closed before product/runtime imports; reuse the complete frozen D1 engine."""
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
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def runtime():
    # This must precede every product/fixture/package import.
    gate = load('e1_before_any_runtime_closed_gate', HERE/'gate.py')
    gate.selected(json.loads((HERE/'CONFIG.json').read_bytes()))
    for relative in ('scripts', 'scripts/cp7_customer_credit/consumer',
                     'scripts/cp7_customer_credit/reconciliation/native', 'scripts/cp7_customer_credit/native',
                     'scripts/cp7_customer_credit/initial-settlement'):
        sys.path.insert(0, str(ROOT/relative))
    original = ROOT/'scripts/current-vendor-receivable-qualification/probe.py'
    code, derivation = load('e1_frozen_D1_engine_derivation', HERE/'derive.py').derive(original.read_bytes())
    engine = ModuleType('e1_complete_D1_package_engine'); engine.__file__ = str(original)
    exec(compile(code, str(original), 'exec'), engine.__dict__)
    from cp7_credit_correction_de import e_composition as product
    component = load('e1_actual_native17_component', HERE/'component.py')
    engine.product = product
    engine.runner = SimpleNamespace(CASE=component.CASE, exercise=component.exercise, scheduler_quiet=component.scheduler_quiet)
    engine.IDS = (component.CASE,)
    engine.LABEL = 'CP7_CREDIT_E1_NATIVE17'
    engine.PRE_DUMP = '/tmp/credit_e1_native17_pre.dump'
    engine.OUT = ROOT/'cp6-proof/t3'/(engine.LABEL+'.json')
    engine.admitted = lambda: load('e1_full_actual_source_admission', HERE/'admission.py').admitted(product, derivation)
    return engine


def execute():
    load('e1_execute_closed_before_confirmation', HERE/'gate.py').selected(json.loads((HERE/'CONFIG.json').read_bytes()))
    if os.environ.get('E1_NATIVE_CONFIRM') != 'cp6_rollback':
        raise ValueError('E1_EXPLICIT_DISPOSABLE_QUALIFICATION_CONFIRMATION_REQUIRED')
    engine = runtime()
    engine.admitted()
    engine.package._writer_runtime = lambda browser_mode=False: engine.run()
    engine.package.run('install')


if __name__ == '__main__':
    execute()
