"""Lazy Native13 child of the unchanged complete qualified vendor engine."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import argparse
import importlib
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runtime():
    closure = load('d1_product_phase_source_before_runtime', HERE / 'source_check.py')
    closure.check(require_bound=True)  # CLOSED before any ERP/product/runtime import.
    boundary = load('d1_product_phase_import_argv', HERE / 'argv_boundary.py')
    with boundary.inherited_imports():
        retained = ROOT / 'scripts/current-credit-de-native-qualification'
        original = ROOT / 'scripts/current-vendor-receivable-qualification/probe.py'
        legacy_derive = load('d1_product_phase_retained_vendor_derivation', retained / 'derive.py')
        code, derivation = legacy_derive.derive(original.read_bytes())
        sys.path.insert(0, str(ROOT / 'scripts'))
        engine = ModuleType('d1_product_phase_private_complete_vendor_engine')
        engine.__file__ = str(original)
        exec(compile(code, str(original), 'exec'), engine.__dict__)
        product = importlib.import_module('cp7_credit_correction_de.composition')
        cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
        augmentation = load('d1_product_phase_reviewed_native_business_factory', ROOT / cfg['native_augmentation']['factory_path'])
        private_derive = load('d1_product_phase_single_native_import_derivation', HERE / 'derive.py')
        native_path = retained / 'native_runner.py'
        native_code, native_derivation = private_derive.native_runner(native_path.read_bytes())
        component = ModuleType('d1_product_phase_private_native13')
        component.__file__ = str(native_path)
        component.__D1_BUSINESS_FACTORY__ = augmentation.business
        exec(compile(native_code, str(native_path), 'exec'), component.__dict__)
        native_parent = load('d1_product_phase_unchanged_scheduler_quiet',
                             ROOT / 'scripts/current-vendor-receivable-qualification/native_runner.py')
        engine.product = product
        engine.runner = SimpleNamespace(CASE='CREDIT_DE_NATIVE13_AND_USED_INVERSE',
            exercise=component.exercise, scheduler_quiet=native_parent.scheduler_quiet)
        engine.IDS = (engine.runner.CASE,)
        engine.LABEL = 'CP7_CREDIT_DE_NATIVE13'
        engine.PRE_DUMP = '/tmp/credit_de_native13_pre.dump'
        engine.OUT = ROOT / 'cp6-proof/t3' / (engine.LABEL + '.json')

        def admitted():
            # sources()/parent admission also contain deferred old imports.
            with boundary.inherited_imports():
                proof = load('d1_product_phase_runtime_admission', HERE / 'admission.py').admitted(ROOT, HERE, product, derivation)
                proof['private_native_runner_derivation'] = native_derivation
                return proof

        engine.admitted = admitted
        return engine


def check():
    return runtime().admitted()


def execute():
    engine = runtime()
    engine.admitted()
    # Inherited complete package's supported writer entry point, unchanged.
    engine.package._writer_runtime = lambda browser_mode=False: engine.run()
    engine.package.run('install')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='full source/parent admission only; no SQL')
    args = parser.parse_args(argv)
    if args.check:
        proof = check()
        print(json.dumps(dict(status=proof['status'], actual_Native_cases=0,
            prerequisite=proof['qualified_parent'], production_go=False)))
    else:
        execute()


if __name__ == '__main__':
    main()
