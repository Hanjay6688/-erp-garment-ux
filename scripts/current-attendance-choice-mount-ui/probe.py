"""Closed full-engine S03 mounted browser preparation; --check is source only."""
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
    # No ERP import/proof materialization/DB import until a reviewed actual-proof binder exists.
    proof = load('s03_mount_ui_pre_runtime_gate', HERE / 'source_check.py').require_execution()
    prepared = ROOT / 'scripts/current-attendance-period-choice-native11-qualification'
    inputs = load('s03_mount_ui_retained_proof_inputs', prepared / 'proof_inputs.py')
    inputs.materialize()
    boundary = load('s03_mount_ui_retained_argv_boundary', prepared / 'argv_boundary.py')
    with boundary.inherited_imports():
        sys.path.insert(0, str(ROOT / 'scripts'))
        original = ROOT / 'scripts/current-vendor-receivable-qualification/probe.py'
        code, derivation = load('s03_mount_ui_exact_engine_derivation', HERE / 'derive.py').derive(original.read_bytes())
        engine = ModuleType('s03_mount_ui_private_complete_vendor_engine')
        engine.__file__ = str(original)
        exec(compile(code, str(original), 'exec'), engine.__dict__)
        product = importlib.import_module('cp7_attendance_period_choice.composition')
        component = load('s03_mount_ui_browser_component', HERE / 'browser_adapter.py')
        parent = load('s03_mount_ui_retained_scheduler_quiet', ROOT / 'scripts/current-vendor-receivable-qualification/native_runner.py')
        engine.product = product
        engine.runner = SimpleNamespace(CASE=component.CASE, exercise=component.exercise, scheduler_quiet=parent.scheduler_quiet)
        engine.IDS = (component.CASE,)
        engine.LABEL = 'CP7_S03_MOUNTED_FULL_APP_BROWSER4'
        engine.PRE_DUMP = '/tmp/s03_mounted_full_app_browser4_pre.dump'
        engine.OUT = ROOT / 'cp6-proof/t3' / (engine.LABEL + '.json')
        engine.admitted = lambda: dict(proof, component_derivation=derivation)
        return engine


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    if args.check:
        print(json.dumps(load('s03_mount_ui_source_only_probe', HERE / 'source_check.py').check(), sort_keys=True))
        return
    engine = runtime()
    engine.package._writer_runtime = lambda browser_mode=False: engine.run()
    engine.package.run('install')


if __name__ == '__main__':
    main()
