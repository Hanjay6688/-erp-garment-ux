"""Root-only successor wrapper; exact retained full engine, no DB on import/check."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import importlib.util
import os
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INHERITED = ROOT/'scripts/current-s05-native10-qualification'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def runtime():
    admission = load('s05_acl_successor_offline_admission', HERE/'admission.py')
    admission.offline()  # Every closed source pin is checked before runtime imports.
    sys.path.insert(0, str(ROOT/'scripts'))
    os.environ['S05_CANDIDATE_SOURCE_ROOT'] = str(ROOT)
    source, derivation = load('s05_acl_unchanged_engine_derivation', INHERITED/'derive.py').derive(
        (INHERITED/'frozen_vendor/probe.py').read_bytes())
    engine = ModuleType('s05_acl_complete_qualified_vendor41c_engine')
    engine.__file__ = str(INHERITED/'frozen_vendor/probe.py')
    exec(compile(source, engine.__file__, 'exec'), engine.__dict__)
    component = load('s05_acl_unchanged_native_component', INHERITED/'component.py')
    engine.runner = SimpleNamespace(CASE=component.CASE, exercise=component.exercise,
                                    scheduler_quiet=component.scheduler_quiet)
    engine.IDS = (component.CASE,)
    engine.LABEL = 'CP7_S05_ACCESSORY_STANDARD_NATIVE10'
    engine.PRE_DUMP = '/tmp/s05_accessory_standard_native10_pre.dump'
    engine.OUT = ROOT/'cp6-proof/t3'/(engine.LABEL+'.json')
    engine.admitted = lambda: admission.admitted(ROOT, HERE, engine.product, derivation)
    return engine


def check():
    boundary = load('s05_acl_retained_source_import_arguments', INHERITED/'import_argv.py')
    with boundary.source_import_arguments():
        return runtime().admitted()


def execute():
    if os.environ.get('S05_NATIVE_CONFIRM') != 'cp6_rollback':
        raise ValueError('S05_EXPLICIT_LOCAL_QUALIFICATION_CONFIRMATION_REQUIRED')
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
        raise SystemExit('Use --check for source-only admission; only root runs the disposable qualification.')
