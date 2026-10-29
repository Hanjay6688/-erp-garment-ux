"""New wrapper of the exact complete vendor41c package engine.

No database work on import or --check. Actual execution requires the explicit
disposable confirmation supplied only by the new workflow/root caller.
"""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import importlib.util
import os
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def runtime():
    # This is the candidate checkout's frozen vendor composition. SKU/D1 are
    # never imported or installed. The historical module bytes stay unchanged.
    sys.path.insert(0, str(ROOT/'scripts'))
    os.environ['S05_CANDIDATE_SOURCE_ROOT'] = str(ROOT)
    source, derivation = load('s05_exact_engine_derivation', HERE/'derive.py').derive((HERE/'frozen_vendor/probe.py').read_bytes())
    engine = ModuleType('s05_complete_qualified_vendor41c_engine')
    engine.__file__ = str(HERE/'frozen_vendor/probe.py')
    exec(compile(source, engine.__file__, 'exec'), engine.__dict__)
    component = load('s05_actual_unchanged_native_component', HERE/'component.py')
    engine.runner = SimpleNamespace(CASE=component.CASE, exercise=component.exercise, scheduler_quiet=component.scheduler_quiet)
    engine.IDS = (component.CASE,)
    engine.LABEL = 'CP7_S05_ACCESSORY_STANDARD_NATIVE10'
    engine.PRE_DUMP = '/tmp/s05_accessory_standard_native10_pre.dump'
    engine.OUT = ROOT/'cp6-proof/t3'/(engine.LABEL+'.json')
    engine.admitted = lambda: load('s05_actual_source_admission', HERE/'admission.py').admitted(ROOT, HERE, engine.product, derivation)
    return engine


def check():
    boundary = load('s05_source_import_arguments', HERE/'import_argv.py')
    with boundary.source_import_arguments():
        return runtime().admitted()


def execute():
    if os.environ.get('S05_NATIVE_CONFIRM') != 'cp6_rollback':
        raise ValueError('S05_EXPLICIT_LOCAL_QUALIFICATION_CONFIRMATION_REQUIRED')
    # Admission, including actual vendor11/package, precedes package.run and
    # every connection. No fallback when source or prior Original is absent.
    engine = runtime()
    engine.admitted()
    engine.package._writer_runtime = lambda browser_mode=False: engine.run()
    engine.package.run('install')


if __name__ == '__main__':
    if sys.argv[1:] == ['--check']:
        import json
        print(json.dumps(check(), indent=2, default=str))
    elif not sys.argv[1:]:
        execute()
    else:
        raise SystemExit('Use --check for source-only admission, or the root-controlled disposable workflow for execution.')
