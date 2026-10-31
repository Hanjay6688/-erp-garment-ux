"""Closed owning Native30 package caller; no execution is triggered by import."""
from pathlib import Path
from types import ModuleType,SimpleNamespace
import argparse,importlib.util,json,os

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def runtime():
    admission=load('complete_DE_parent_before_ERP',HERE/'admission.py')
    admission.parent_receipt()
    load('complete_DE_closed_source_before_ERP',HERE/'source.py').preflight()
    with admission.import_scope():
        original=ROOT/'scripts/current-vendor-receivable-qualification/probe.py'
        text,derivation=load('complete_DE_whole_engine_derivation',HERE/'engine.py').derive(original.read_bytes())
        engine=ModuleType('complete_DE_unchanged_full_package_engine');engine.__file__=str(original)
        exec(compile(text,str(original),'exec'),engine.__dict__)
        from cp7_complete_credit_de import composition as product
        component=load('complete_DE_original_native30_component',HERE/'component.py')
        engine.product=product
        engine.runner=SimpleNamespace(CASE=component.CASE,exercise=component.exercise,scheduler_quiet=component.scheduler_quiet)
        engine.IDS=(component.CASE,);engine.LABEL='CP7_CURRENT_COMPLETE_D1_E_NATIVE30'
        engine.PRE_DUMP='/tmp/current_complete_D1_E_full_pre.dump'
        engine.OUT=ROOT/'cp6-proof/t3'/(engine.LABEL+'.json')
        def admitted():return dict(admission.admitted(),complete_engine_derivation=derivation)
        engine.admitted=admitted
    return engine,admission


def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check',action='store_true');mode.add_argument('--runtime',action='store_true')
    args=parser.parse_args()
    load('complete_DE_parent_before_mode_selection',HERE/'admission.py').parent_receipt()
    if args.check:
        fence=load('complete_DE_three_entrypoint_source_fence',
            ROOT/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
        with fence.fenced_source_read()as guard:
            engine,_=runtime();proof=engine.admitted()
        print(json.dumps(dict(status=proof['status'],source_DB_guard=guard,actual_Native_cases=0,
            entire_natural_product_source_graph_evaluated=True,production_go=False)));return
    if os.environ.get('COMPLETE_DE_CONFIRM')!='cp6_rollback':
        raise ValueError('COMPLETE_DE_EXPLICIT_DISPOSABLE_CONFIRMATION_REQUIRED')
    attempts=load('complete_DE_original_single_attempt_WIB_window',
        ROOT/'scripts/current-sku-managed-recovery-native27-qualification/attempt_policy.py')
    monitor=load('complete_DE_diagnostic_only_runtime',HERE/'runtime_note.py')
    with monitor.monitor(),monitor.phase('DE_SOURCE_ADMISSION_AND_WHOLE_PACKAGE_RUNTIME'):
        print(json.dumps(dict(attempt_policy=attempts.require_window())),flush=True)
        engine,admission=runtime();engine.admitted()
        with admission.import_scope():
            original=engine.package._writer_runtime
            try:
                engine.package._writer_runtime=lambda browser_mode=False:engine.run()
                import cp6_auditor_business_day as business_day
                with attempts.single_attempt(business_day):engine.package.run('install')
            finally:engine.package._writer_runtime=original


if __name__=='__main__':main()
