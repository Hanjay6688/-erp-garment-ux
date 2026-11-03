"""Exact money successor through the retained owning full package engine."""
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

def runtime():
    admission=load('sku_money_before_runtime_source',HERE/'admission.py')
    admission.source_only(ROOT,HERE)
    deriver=load('sku_money_whole_package_derivation',HERE/'derive.py')
    original=ROOT/'scripts/current-vendor-receivable-qualification/probe.py'
    code,derivation=deriver.derive(original.read_bytes())
    engine=ModuleType('sku_money_complete_package_engine');engine.__file__=str(original)
    exec(compile(code,str(original),'exec'),engine.__dict__)
    from cp7_sku_cost_components import composition as product
    component=load('sku_money_native_component',HERE/'runner.py')
    native_parent=load('sku_money_scheduler_quiet',ROOT/'scripts/current-vendor-receivable-qualification/native_runner.py')
    engine.product=product
    engine.runner=SimpleNamespace(CASE='SKU_COST_MONEY_NATIVE19_AND_USED_INVERSE',exercise=component.exercise,scheduler_quiet=native_parent.scheduler_quiet)
    engine.IDS=(engine.runner.CASE,)
    engine.LABEL='CP7_SKU_COST_MONEY_QUALIFICATION'
    engine.PRE_DUMP='/tmp/sku_cost_money_pre.dump'
    engine.OUT=ROOT/'cp6-proof/t3'/(engine.LABEL+'.json')
    engine.admitted=lambda:admission.admitted(ROOT,HERE,product,derivation)
    return engine

def main():
    attempts=load('sku_money_single_attempt_and_real_day',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/attempt_policy.py')
    attempts.require_window()
    engine=runtime();engine.admitted()
    engine.package._writer_runtime=lambda browser_mode=False:engine.run()
    import cp6_auditor_business_day as business_day
    with attempts.single_attempt(business_day):engine.package.run('install')

if __name__=='__main__':main()
