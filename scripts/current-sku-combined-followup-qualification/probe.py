"""Reuse the frozen complete vendor package engine; source remains closed."""
from pathlib import Path
from types import ModuleType, SimpleNamespace
import importlib.util
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


deriver = load('sku_full_counted_vendor_derivation', HERE / 'derive.py')
original = ROOT / 'scripts/current-vendor-receivable-qualification/probe.py'
code, derivation = deriver.derive(original.read_bytes())
engine = ModuleType('sku_combined_existing_complete_package_engine'); engine.__file__ = str(original)
exec(compile(code, str(original), 'exec'), engine.__dict__)
from cp7_sku_pair_conversion import composition as product
component = load('sku_combined_actual_component', HERE / 'runner.py')
engine.product = product
engine.runner = SimpleNamespace(CASE=component.CASE, exercise=component.exercise, scheduler_quiet=component.scheduler_quiet)
engine.IDS = (component.CASE,); engine.LABEL = 'CP7_SKU_COMBINED_FOLLOWUP23'
engine.PRE_DUMP = '/tmp/sku_combined_followup_pre.dump'
engine.OUT = ROOT / 'cp6-proof/t3' / (engine.LABEL + '.json')


def admitted():
    return load('sku_combined_full_admission', HERE / 'admission.py').admitted(product, derivation)


engine.admitted = admitted
if __name__ == '__main__':
    admitted()
    engine.package._writer_runtime = lambda browser_mode=False: engine.run()
    engine.package.run('install')
