"""Moving-average successor through the unchanged complete package engine."""
from pathlib import Path
from types import ModuleType,SimpleNamespace
import importlib.util
import sys

sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

deriver=load('sku_movavg_package_derivation',HERE/'derive.py')
original=ROOT/'scripts/current-vendor-receivable-qualification/probe.py'
code,derivation=deriver.derive(original.read_bytes())
engine=ModuleType('sku_movavg_complete_package_engine');engine.__file__=str(original)
exec(compile(code,str(original),'exec'),engine.__dict__)
from cp7_sku_moving_average import composition as product
component=load('sku_movavg_native_component',HERE/'runner.py')
native_parent=load('sku_movavg_scheduler_quiet',ROOT/'scripts/current-vendor-receivable-qualification/native_runner.py')
engine.product=product
engine.runner=SimpleNamespace(CASE='SKU_MOVING_AVERAGE_NATIVE5_AND_USED_INVERSE',exercise=component.exercise,scheduler_quiet=native_parent.scheduler_quiet)
engine.IDS=(engine.runner.CASE,)
engine.LABEL='CP7_SKU_MOVING_AVERAGE_QUALIFICATION'
engine.PRE_DUMP='/tmp/sku_moving_average_pre.dump'
engine.OUT=ROOT/'cp6-proof/t3'/(engine.LABEL+'.json')

def admitted():return load('sku_movavg_source_admission',HERE/'admission.py').admitted(ROOT,HERE,product,derivation)

engine.admitted=admitted
if __name__=='__main__':
    admitted();engine.package._writer_runtime=lambda browser_mode=False:engine.run();engine.package.run('install')
