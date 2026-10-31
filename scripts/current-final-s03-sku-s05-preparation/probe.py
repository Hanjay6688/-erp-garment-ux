"""Executable owning composite caller; admission precedes all ERP imports."""
from pathlib import Path
from types import ModuleType,SimpleNamespace
import argparse,importlib.util,json,os

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def runtime():
    admission=load('joined_outer_complete_admission',HERE/'admission.py');proof=admission.admitted()
    with admission.import_scope():
        original=ROOT/'scripts/current-vendor-receivable-qualification/probe.py'
        text,derivation=load('joined_outer_complete_engine_derivation',HERE/'engine.py').derive(original.read_bytes())
        engine=ModuleType('joined_outer_complete_retained_package_engine');engine.__file__=str(original)
        exec(compile(text,str(original),'exec'),engine.__dict__)
        from cp7_current_s03_sku_s05 import composition as product
        component=load('joined_outer_actual_37_component',HERE/'component.py')
        engine.product=product
        engine.runner=SimpleNamespace(CASE=component.CASE,exercise=component.exercise,scheduler_quiet=component.scheduler_quiet)
        engine.IDS=(component.CASE,);engine.LABEL='CP7_PERMANENT_S05_S03_SKU_NATIVE4_BROWSER2'
        engine.PRE_DUMP='/tmp/permanent_s05_s03_sku_full_pre.dump'
        engine.OUT=ROOT/'cp6-proof/t3'/(engine.LABEL+'.json')
        def admitted():
            current=admission.admitted()
            if product.sources()!=current['current_installation']:raise ValueError('JOIN_OUTER_CURRENT_SOURCE_CHANGED')
            return dict(current,complete_engine_derivation=derivation)
        engine.admitted=admitted
    return engine,admission


def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-static',action='store_true');mode.add_argument('--check',action='store_true');mode.add_argument('--runtime',action='store_true')
    args=parser.parse_args()
    if args.check_static:
        print(json.dumps(dict(source=load('joined_static_only_source',HERE/'persistent_source.py').preflight(),
            actual_cases=0,runtime_imported=False)));return
    if args.check:
        fence=load('joined_no_DB_current_import_fence',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
        with fence.fenced_source_read()as guard:
            engine,_=runtime();proof=engine.admitted()
        print(json.dumps(dict(status=proof['status'],source_DB_guard=guard,actual_new_cases=0,
            whole_natural_product_source_graph_evaluated=True,production_go=False),sort_keys=True));return
    if os.environ.get('PERMANENT_S05_CONFIRM')!='cp6_rollback':raise ValueError('JOIN_EXPLICIT_LOCAL_DISPOSABLE_CONFIRMATION_REQUIRED')
    attempts=load('joined_single_attempt_real_WIB_window',HERE/'attempt_policy.py')
    print(json.dumps(dict(attempt_policy=attempts.require_window())))
    notes=load('permanent_actual_published_runner_diagnostics',HERE/'runtime_note.py')
    with notes.monitor():
        with notes.phase('PERMANENT_SOURCE_ADMISSION'):
            engine,admission=runtime()
        with admission.import_scope():
            engine.admitted();original=engine.package._writer_runtime
            try:
                engine.package._writer_runtime=lambda browser_mode=False:engine.run()
                import cp6_auditor_business_day as business_day
                with attempts.single_attempt(business_day),notes.phase('PERMANENT_COMPLETE_PACKAGE_AND_RESTORE'):
                    engine.package.run('install')
            finally:engine.package._writer_runtime=original


if __name__=='__main__':main()
