"""Lazy S03 Native11 through the unchanged complete vendor package engine."""
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
    closure = load('s03_native11_source_before_runtime', HERE / 'source_check.py')
    closure.check()  # Before product/ERP imports or proof materialization.
    inputs = load('s03_native11_frozen_proof_materializer', HERE / 'proof_inputs.py')
    materialized = inputs.materialize()
    boundary = load('s03_native11_inherited_argv_boundary', HERE / 'argv_boundary.py')
    with boundary.inherited_imports():
        sys.path.insert(0, str(ROOT / 'scripts'))
        original = ROOT / 'scripts/current-vendor-receivable-qualification/probe.py'
        derive = load('s03_native11_private_vendor_derivation', HERE / 'derive.py')
        code, derivation = derive.derive(original.read_bytes())
        engine = ModuleType('s03_native11_private_complete_vendor_engine')
        engine.__file__ = str(original)
        exec(compile(code, str(original), 'exec'), engine.__dict__)
        product = importlib.import_module('cp7_attendance_period_choice.composition')
        component = load('s03_native11_actual_component', HERE / 'native_runner.py')
        parent = load('s03_native11_unchanged_parent_scheduler',
            ROOT / 'scripts/current-vendor-receivable-qualification/native_runner.py')
        engine.product = product
        engine.runner = SimpleNamespace(CASE='S03_ATTENDANCE_NATIVE11_AND_USED_INVERSE',
            exercise=component.exercise, scheduler_quiet=parent.scheduler_quiet)
        engine.IDS = (engine.runner.CASE,)
        engine.LABEL = 'CP7_S03_ATTENDANCE_CHOICE_NATIVE11'
        engine.PRE_DUMP = '/tmp/s03_attendance_choice_native11_pre.dump'
        engine.OUT = ROOT / 'cp6-proof/t3' / (engine.LABEL + '.json')

        def admitted():
            with boundary.inherited_imports():
                proof = load('s03_native11_actual_admission', HERE / 'admission.py').admitted(ROOT, HERE, product, derivation)
                proof['historical_proof_inputs'] = materialized
                return proof

        engine.admitted = admitted
        return engine


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='full source/parent admission only; no SQL')
    args = parser.parse_args(argv)
    engine = runtime()
    if args.check:
        proof = engine.admitted()
        print(json.dumps(dict(status=proof['status'], source_declaration=proof['source_declaration'],
            qualified_parent=proof['qualified_parent'], actual_Native_cases=0, production_go=False)))
    else:
        engine.admitted()
        engine.package._writer_runtime = lambda browser_mode=False: engine.run()
        engine.package.run('install')


if __name__ == '__main__':
    main()
