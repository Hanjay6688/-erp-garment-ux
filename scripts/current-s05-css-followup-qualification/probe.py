"""Fresh S05 browsers under the complete unchanged owning installer engine."""
from pathlib import Path
from types import ModuleType,SimpleNamespace
import argparse,importlib.util,json,os

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-s03-sku-s05-composite-qualification'
LABEL='CP7_CURRENT_S05_CSS_RETAIN35_BROWSER2'

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def runtime():
    admission=load('focused_outer_before_ERP_admission',HERE/'admission.py');proof=admission.admitted()
    with admission.import_scope():
        original=ROOT/'scripts/current-vendor-receivable-qualification/probe.py'
        text,derivation=load('focused_complete_owning_engine_derivation',HERE/'engine.py').derive(original.read_bytes())
        engine=ModuleType('focused_complete_original_package_engine');engine.__file__=str(original)
        exec(compile(text,str(original),'exec'),engine.__dict__)
        from cp7_s03_sku_composition import composition as product
        component=load('focused_only_missing_real_browsers',HERE/'component.py')
        engine.product=product
        engine.runner=SimpleNamespace(CASE=component.CASE,exercise=component.exercise,scheduler_quiet=component.scheduler_quiet,
            foundation_precheck=component.foundation_precheck)
        engine.IDS=(component.CASE,);engine.LABEL=LABEL
        engine.PRE_DUMP='/tmp/current_s05_css_followup_pre.dump'
        engine.OUT=ROOT/'cp6-proof/t3'/(LABEL+'.json')
        def admitted():
            current=admission.admitted()
            if product.sources()!=current['current_installation']:raise ValueError('FOCUSED_CURRENT_FINANCIAL_SOURCE_CHANGED')
            return dict(current,complete_engine_derivation=derivation)
        engine.admitted=admitted
    return engine,admission

def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-static',action='store_true');mode.add_argument('--check',action='store_true');mode.add_argument('--runtime',action='store_true')
    args=parser.parse_args()
    if args.check_static:
        proof=load('focused_static_retention_before_ERP',HERE/'admission.py').retained()
        print(json.dumps(dict(status=proof['source_invariance']['status'],retained_cases=35,actual_new_cases=0,runtime_imported=False)));return
    if args.check:
        fence=load('focused_unchanged_no_DB_import_fence',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
        with fence.fenced_source_read()as guard:engine,_=runtime();proof=engine.admitted()
        print(json.dumps(dict(status=proof['status'],source_DB_guard=guard,actual_new_cases=0,
            whole_natural_product_source_graph_evaluated=True,production_go=False),sort_keys=True));return
    if os.environ.get('JOIN_CONFIRM')!='cp6_rollback':raise ValueError('FOCUSED_EXPLICIT_LOCAL_DISPOSABLE_CONFIRMATION_REQUIRED')
    attempts=load('focused_real_WIB_one_attempt_window',HERE/'attempt_policy.py')
    print(json.dumps(dict(attempt_policy=attempts.require_window())))
    notes=load('focused_unchanged_resource_and_phase_diagnostics',PARENT/'runtime_note.py')
    with notes.monitor():
        with notes.phase('FOCUSED_SOURCE_ADMISSION_BEFORE_ERP'):engine,admission=runtime()
        with admission.import_scope():
            engine.admitted();original=engine.package._writer_runtime
            try:
                engine.package._writer_runtime=lambda browser_mode=False:engine.run()
                import cp6_auditor_business_day as business_day
                with attempts.single_attempt(business_day),notes.phase('COMPLETE_PACKAGE_INSTALL_BROWSER2_RESTORE'):
                    engine.package.run('install')
            finally:engine.package._writer_runtime=original

if __name__=='__main__':main()
