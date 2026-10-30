"""Explicit metadata launch; the global business runtime remains absent."""
from pathlib import Path
from types import ModuleType
import argparse
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def early():
    # Only own stdlib admission is loaded before the exact whole parent tree,
    # successor source, executable modes, profiles and untracked set pass.
    return load('global_census_first_source_admission', HERE / 'admission.py').preflight()


def runtime():
    early()
    sys.path.insert(0, str(ROOT / 'scripts'))
    transition = load('global_census_exact_argv_scope', ROOT / 'scripts/current-sku-managed-recovery-native27-qualification/transition.py')
    with transition.scoped_argv():
        deriver = load('global_census_complete_engine', HERE / 'derive.py')
        text, proof = deriver.engine()
        engine = ModuleType('global_census_complete_disposable_engine')
        engine.__file__ = str(ROOT / deriver.OLD)
        exec(compile(text, engine.__file__, 'exec'), engine.__dict__)
        engine.GLOBAL_CENSUS_ENGINE_DERIVATION = proof
        original = engine.admitted
        def admitted():
            with transition.scoped_argv(): return original()
        engine.admitted = admitted
    return engine


def main():
    parser = argparse.ArgumentParser(); group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--check', action='store_true')
    group.add_argument('--metadata-runtime', action='store_true')
    args = parser.parse_args()
    early()
    if args.check:
        context = load('global_census_source_no_database', ROOT / 'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
        with context.fenced_source_read() as guard:
            engine = runtime(); proof = engine.admitted()
        print(json.dumps(dict(status='EXACT_SOURCE_ONLY_NO_DATABASE', proof=proof, guard=guard,
            actual_Native_credit=0, runtime_entry=None, production_go=False, independent_acceptance=False), default=str))
        return
    engine = runtime()
    transition = load('global_census_metadata_execution_argv', ROOT / 'scripts/current-sku-managed-recovery-native27-qualification/transition.py')
    with transition.scoped_argv():
        engine.admitted()
        engine.package._writer_runtime = lambda browser_mode=False: engine.run()
        engine.package.run('install')


if __name__ == '__main__': main()
