"""Normal full App browser4 qualification preparation; CLOSED until bound actual backend14."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
from contextlib import contextmanager
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


@contextmanager
def runtime():
    proof = load('s03_browser4_source_before_ERP_or_DB', HERE / 'source_guard.py').admitted()
    prepared = ROOT / 'scripts/current-attendance-period-choice-native11-qualification'
    inputs = load('s03_browser4_retained_actual_vendor_proofs', prepared / 'proof_inputs.py')
    inputs.materialize()
    boundary = load('s03_browser4_retained_argv_scope', prepared / 'argv_boundary.py')
    loader = load('s03_browser4_actual_backend_package', HERE / 'backend_runtime.py')
    with loader.actual_backend(proof) as product:
        with boundary.inherited_imports():
            original = ROOT / 'scripts/current-vendor-receivable-qualification/probe.py'
            code, derivation = load('s03_browser4_private_counted_derivation', HERE / 'derive.py').derive(original.read_bytes())
            engine = ModuleType('s03_browser4_private_unchanged_complete_vendor_engine')
            engine.__file__ = str(original)
            exec(compile(code, str(original), 'exec'), engine.__dict__)
            if product.sources() != proof['current_installation']:
                raise ValueError('S03_BROWSER4_EXACT_WHOLE_QUALIFIED_SOURCE_GRAPH_REQUIRED')
            component = load('s03_browser4_actual_browser_component', HERE / 'component.py')
            engine.product = product
            engine.runner = SimpleNamespace(CASE=component.CASE, exercise=component.exercise, scheduler_quiet=component.scheduler_quiet)
            engine.IDS = (component.CASE,)
            engine.LABEL = 'CP7_S03_MOUNTED_FULL_APP_BROWSER4'
            engine.PRE_DUMP = '/tmp/s03_mounted_full_app_browser4_pre.dump'
            engine.OUT = ROOT / 'cp6-proof/t3' / (engine.LABEL + '.json')
            engine.admitted = lambda: dict(proof, browser_derivation=derivation)
        yield engine


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--check-actual-source', action='store_true')
    options = parser.parse_args(argv)
    if options.check:
        checked = load('s03_browser4_offline_source_only', HERE / 'source_guard.py').check()
        print(json.dumps(dict(status=checked['status'], exact_sources=checked['exact_sources'],
            execution_closed=checked['config']['accepted_originals'] is None, actual_Native_Auth_browser_cases=0)))
        return
    if not options.check_actual_source:
        attempts = load('s03_single_attempt_policy', HERE / 'attempt_policy.py')
        print(json.dumps(dict(attempt_policy=attempts.require_window()), sort_keys=True))
    with runtime() as engine:
        if options.check_actual_source:
            proof = engine.admitted()
            print(json.dumps(dict(status=proof['status'], exact_actual_parent_Native_cases=14,
                current_product_source_graph_equal_actual_Original=True, actual_new_Native_Auth_browser_cases=0,
                production_go=False)))
            return
        original = engine.package._writer_runtime
        try:
            engine.package._writer_runtime = lambda browser_mode=False: engine.run()
            import cp6_auditor_business_day as business_day
            with attempts.single_attempt(business_day):
                engine.package.run('install')
        finally:
            engine.package._writer_runtime = original


if __name__ == '__main__':
    main()
