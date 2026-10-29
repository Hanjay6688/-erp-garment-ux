"""Complete preserved package engine; the source gate precedes runtime imports."""
from pathlib import Path
from types import ModuleType
import argparse
import importlib.util
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runtime():
    admission = load('sku23_probe_source_gate', HERE / 'admission.py')
    admission.preflight()
    t = load('sku23_probe_argv_scope', HERE / 'transition.py')
    with t.scoped_argv():
        d = load('sku23_probe_private_derive', HERE / 'derive.py')
        module = ModuleType('sku23_private_complete_probe')
        module.__file__ = str(HERE / 'probe.py')
        d.execute('probe', module.__dict__)
        # Lazy admission imports share the same scoped argv discipline.
        original = module.admitted
        def admitted():
            with t.scoped_argv():
                return original()
        module.admitted = admitted
        module.engine.admitted = admitted
    return module


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', action='store_true', required=True)
    parser.parse_args(argv)
    module = runtime()
    t = load('sku23_execution_argv_scope', HERE / 'transition.py')
    with t.scoped_argv():
        module.admitted()
        module.engine.package._writer_runtime = lambda browser_mode=False: module.engine.run()
        module.engine.package.run('install')


if __name__ == '__main__':
    main()
