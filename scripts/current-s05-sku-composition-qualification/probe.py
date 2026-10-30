"""Prepared complete integration caller. Pending SKU27 blocks runtime imports."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import argparse
import importlib.util
import json
import os
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def source():
    return load('s05_sku_complete_outer_source', HERE/'source.py').preflight()


def runtime():
    source()
    prerequisite = load('s05_sku_actual_qualified_parent', HERE/'prerequisite.py')
    prerequisite.admitted()  # Fails before ERP imports until actual root intake.
    boundary = load('s05_sku_retained_import_argv', ROOT/'scripts/current-sku-managed-recovery-native27-qualification/transition.py')
    with boundary.scoped_argv():
        sys.path.insert(0, str(ROOT/'scripts'))
        original = ROOT/'scripts/current-vendor-receivable-qualification/probe.py'
        text, derivation = load('s05_sku_complete_outer_derivation', HERE/'engine.py').derive(original.read_bytes())
        engine = ModuleType('s05_sku_complete_retained_package_engine'); engine.__file__ = str(original)
        exec(compile(text, str(original), 'exec'), engine.__dict__)
        from cp7_sku_pair_conversion import composition as product
        component = load('s05_sku_actual_current_component', HERE/'component.py')
        engine.product = product
        engine.runner = SimpleNamespace(CASE=component.CASE, exercise=component.exercise, scheduler_quiet=component.scheduler_quiet)
        engine.IDS = (component.CASE,)
        engine.LABEL = 'CP7_S05_ON_CURRENT_SKU_NATIVE10_BROWSER2'
        engine.PRE_DUMP = '/tmp/s05_current_sku_complete_pre.dump'
        engine.OUT = ROOT/'cp6-proof/t3'/(engine.LABEL+'.json')
        def admitted():
            current_source = source(); actual = prerequisite.admitted()
            installation = product.sources()
            if json.dumps(installation, sort_keys=True, default=str) != json.dumps(actual['current_installation'], sort_keys=True):
                raise ValueError('S05_NATURAL_SKU_SOURCE_MUST_EQUAL_ACTUAL_QUALIFIED_PARENT')
            return dict(status='S05_CURRENT_SOURCE_AND_ACTUAL_QUALIFIED_SKU27', current_source=current_source,
                current_installation=installation, actual_qualified_SKU27=actual, complete_engine_derivation=derivation,
                current_S05_cases_credited=0, production_go=False, independent_acceptance=False)
        engine.admitted = admitted
    return engine, boundary


def main(argv=None):
    parser = argparse.ArgumentParser(); mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true'); mode.add_argument('--runtime', action='store_true')
    args = parser.parse_args(argv)
    if args.check:
        print(json.dumps(dict(source=source(), prerequisite=load('s05_sku_pending_check', HERE/'prerequisite.py').specification(),
            actual_runtime_cases=0, runtime_imported=False), indent=2)); return
    if os.environ.get('S05_SKU_CONFIRM') != 'cp6_rollback':
        raise ValueError('S05_EXPLICIT_LOCAL_OUTER_QUALIFICATION_REQUIRED')
    attempts = load('s05_sku_single_attempt_day_window', ROOT/'scripts/current-sku-managed-recovery-native27-qualification/attempt_policy.py')
    print(json.dumps(dict(attempt_policy=attempts.require_window())))
    engine, boundary = runtime()
    with boundary.scoped_argv():
        engine.admitted()
        engine.package._writer_runtime = lambda browser_mode=False: engine.run()
        import cp6_auditor_business_day as business_day
        with attempts.single_attempt(business_day): engine.package.run('install')


if __name__ == '__main__': main()
