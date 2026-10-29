"""Exact-source Native SKU child through the existing complete package engine."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(HERE))
from derive import derive


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


original = ROOT / 'scripts/current-vendor-receivable-qualification/probe.py'
code, derivation = derive(original.read_bytes())
engine = ModuleType('sku_actual_existing_complete_package_engine')
engine.__file__ = str(original)
exec(compile(code, str(original), 'exec'), engine.__dict__)
from cp7_sku_pair_conversion import composition as product

component = load('sku_actual_native_component', ROOT / 'scripts/current-sku-pair-conversion-qualification/runner.py')
native_parent = load('sku_unchanged_scheduler_quiet', ROOT / 'scripts/current-vendor-receivable-qualification/native_runner.py')
engine.product = product
engine.runner = SimpleNamespace(CASE='SKU_PAIR_CONVERSION_NATIVE_AND_USED_INVERSE',
                               exercise=component.exercise,
                               scheduler_quiet=native_parent.scheduler_quiet)
engine.IDS = (engine.runner.CASE,)
engine.LABEL = 'CP7_SKU_PAIR_CONVERSION_NATIVE'
engine.PRE_DUMP = '/tmp/sku_pair_conversion_native_pre.dump'
engine.OUT = ROOT / 'cp6-proof/t3' / (engine.LABEL + '.json')


def admitted():
    return load('sku_exact_source_admission', HERE / 'admission.py').admitted(ROOT, HERE, product, derivation)


engine.admitted = admitted

if __name__ == '__main__':
    admitted()
    engine.package._writer_runtime = lambda browser_mode=False: engine.run()
    engine.package.run('install')
