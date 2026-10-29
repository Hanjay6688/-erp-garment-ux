"""Closed before ERP imports/GET/DB; unchanged complete six-change vendor engine."""
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
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def runtime():
    cfg = json.loads((HERE / 'CONFIG.json').read_bytes())
    load('s03_native14_first_closed_gate', HERE / 'gate.py').selected(cfg)
    load('s03_native14_source_before_ERP', HERE / 'source_check.py').check(require_bound=True)
    materialized = load('s03_native14_exact_four_original_materializer', HERE / 'proof_inputs.py').materialize()
    boundary = load('s03_native14_original_argument_boundary', HERE / 'argv_boundary.py')
    with boundary.inherited_imports():
        sys.path.insert(0, str(ROOT / 'scripts'))
        original = ROOT / 'scripts/current-vendor-receivable-qualification/probe.py'
        code, derivation = load('s03_native14_frozen_six_engine_derivation', HERE / 'derive.py').derive(original.read_bytes())
        engine = ModuleType('s03_native14_private_complete_vendor_engine')
        engine.__file__ = str(original)
        exec(compile(code, str(original), 'exec'), engine.__dict__)
        product = importlib.import_module('cp7_attendance_period_choice.composition')
        component = load('s03_native14_current_component', HERE / 'native_runner.py').runtime()
        parent = load('s03_native14_unchanged_parent_scheduler', ROOT / 'scripts/current-vendor-receivable-qualification/native_runner.py')
        engine.product = product
        engine.runner = SimpleNamespace(CASE='S03_ATTENDANCE_NATIVE14_AND_USED_INVERSE',
            exercise=component.exercise, scheduler_quiet=parent.scheduler_quiet)
        engine.IDS = (engine.runner.CASE,)
        engine.LABEL = 'CP7_S03_ATTENDANCE_CHOICE_NATIVE14'
        engine.PRE_DUMP = '/tmp/s03_attendance_choice_native14_pre.dump'
        engine.OUT = ROOT / 'cp6-proof/t3' / (engine.LABEL + '.json')

        def admitted():
            with boundary.inherited_imports():
                result = load('s03_native14_current_original_intake', HERE / 'admission.py').admitted(ROOT, HERE, product, derivation)
                result['historical_proof_inputs'] = materialized
                return result
        engine.admitted = admitted
        return engine


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    engine = runtime()
    if args.check:
        proof = engine.admitted(); print(json.dumps(dict(status=proof['status'], actual_Native_cases=0, production_go=False)))
    else:
        engine.admitted()
        engine.package._writer_runtime = lambda browser_mode=False: engine.run()
        engine.package.run('install')


if __name__ == '__main__':
    main()
