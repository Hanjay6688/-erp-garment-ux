"""Prepared NULL gate precedes ERP imports, Originals, GET and database access."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import argparse
import importlib
import importlib.util
import sys
from midnight_common import HERE, ROOT, CASE, LABEL, document
import midnight_gate as gate

sys.dont_write_bytecode = True


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runtime():
    cfg = document((HERE / 'CONFIG.json').read_bytes())
    gate.selected(cfg)
    closure = load('midnight_actual_current_source', HERE / 'source_check.py').check(require_bound=True)
    boundary = load('midnight_exact_argument_boundary',
        ROOT / 'scripts/current-attendance-period-choice-native11-qualification/argv_boundary.py')
    with boundary.inherited_imports():
        sys.path.insert(0, str(ROOT / 'scripts'))
        derive = load('midnight_private_exact_engine', HERE / 'midnight_derive.py')
        original = ROOT / 'scripts/current-vendor-receivable-qualification/probe.py'
        code, derivation = derive.engine(original.read_bytes())
        engine = ModuleType('midnight_private_complete_outer_engine')
        engine.__file__ = str(original)
        exec(compile(code, str(original), 'exec'), engine.__dict__)
        product = importlib.import_module('cp7_attendance_period_choice.composition')
        intake = importlib.import_module('midnight_admission')
        accepted = intake.admitted(product, cfg)
        component = importlib.import_module('midnight_runner')
        component.BOUND_PARENT = accepted
        scheduler = load('midnight_exact_parent_scheduler',
            ROOT / 'scripts/current-vendor-receivable-qualification/native_runner.py')
        engine.product = product
        engine.runner = SimpleNamespace(CASE=CASE, exercise=component.exercise, scheduler_quiet=scheduler.scheduler_quiet)
        engine.IDS = (CASE,)
        engine.LABEL = LABEL
        engine.PRE_DUMP = '/tmp/attendance_midnight_native1_pre.dump'
        engine.OUT = ROOT / 'cp6-proof/t3' / (LABEL + '.json')

        def admitted():
            actual = intake.admitted(product, cfg)
            return dict(status=actual['proof']['status'], current_installation=product.sources(),
                current_qualification=closure, accepted_parent14=actual['proof'],
                engine_derivation=derivation, actual_Native_cases=0,
                retained_parent14_reexecuted=False, production_go=False, independent_acceptance=False)
        engine.admitted = admitted
        return engine


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    engine = runtime()
    if args.check:
        print(engine.admitted())
    else:
        engine.admitted()
        engine.package._writer_runtime = lambda browser_mode=False: engine.run()
        engine.package.run('install')


if __name__ == '__main__':
    main()
