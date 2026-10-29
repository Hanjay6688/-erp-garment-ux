"""CLOSED before every product/ERP import; complete six-change vendor engine."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import argparse
import importlib
import importlib.util
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'scripts/current-credit-e1-native-qualification'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def runtime():
    load('e1_current_closed_before_any_product', HERE / 'gate.py').selected(json.loads((HERE / 'CONFIG.json').read_bytes()))
    load('e1_current_complete_source_before_runtime', HERE / 'admission.py').source_only()
    boundary = load('e1_current_private_import_boundary', HERE / 'argv_boundary.py')
    with boundary.inherited_imports():
        for relative in ('scripts', 'scripts/cp7_customer_credit/consumer', 'scripts/cp7_customer_credit/reconciliation/native',
                         'scripts/cp7_customer_credit/native', 'scripts/cp7_customer_credit/initial-settlement'):
            sys.path.insert(0, str(ROOT / relative))
        path = ROOT / 'scripts/current-vendor-receivable-qualification/probe.py'
        code, derivation = load('e1_current_exact_six_change_engine', OLD / 'derive.py').derive(path.read_bytes())
        engine = ModuleType('e1_current_private_complete_vendor_engine')
        engine.__file__ = str(path)
        exec(compile(code, str(path), 'exec'), engine.__dict__)
        product = importlib.import_module('cp7_credit_correction_de.e_composition')
        component = load('e1_current_byte_exact_native17_component', OLD / 'component.py')
        engine.product = product
        engine.runner = SimpleNamespace(CASE=component.CASE, exercise=component.exercise, scheduler_quiet=component.scheduler_quiet)
        engine.IDS = (component.CASE,)
        engine.LABEL = 'CP7_CREDIT_E1_NATIVE17'
        engine.PRE_DUMP = '/tmp/credit_e1_current_d1_native17_pre.dump'
        engine.OUT = ROOT / 'cp6-proof/t3' / (engine.LABEL + '.json')
        def admitted():
            with boundary.inherited_imports():
                return load('e1_current_full_runtime_admission', HERE / 'admission.py').admitted(product, derivation)
        engine.admitted = admitted
        return engine


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    if not args.check and os.environ.get('E1_NATIVE_CONFIRM') != 'cp6_rollback':
        # Still report the root prerequisite first while it is deliberately null.
        load('e1_current_closed_before_confirmation', HERE / 'gate.py').selected(json.loads((HERE / 'CONFIG.json').read_bytes()))
        raise ValueError('E1_EXPLICIT_DISPOSABLE_QUALIFICATION_CONFIRMATION_REQUIRED')
    engine = runtime()
    if args.check:
        proof = engine.admitted()
        print(json.dumps(dict(status=proof['status'], actual_Native_cases=0, retained_D1=proof['retained_D1'], production_go=False)))
    else:
        engine.admitted()
        engine.package._writer_runtime = lambda browser_mode=False: engine.run()
        engine.package.run('install')


if __name__ == '__main__':
    main()
