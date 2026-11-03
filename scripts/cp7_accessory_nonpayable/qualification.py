"""Closed whole-package qualifier; source checks do not execute ERP work."""
from pathlib import Path
from types import ModuleType,SimpleNamespace
import argparse,importlib.util,json,os,sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def fixture_actor_preflight():
    """Refuse the private-read regression before provisioning any database."""
    import io,unittest
    from cp7_accessory_nonpayable.test_native_preparation import NativePreparationControls
    name='test_policy_reads_private_version_as_observer_then_writes_as_ordinary_owner'
    output=io.StringIO()
    result=unittest.TextTestRunner(stream=output,verbosity=0).run(
        unittest.TestSuite([NativePreparationControls(name)]))
    if result.testsRun!=1 or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise ValueError('NONPAYABLE_FIXTURE_ACTOR_PREFLIGHT_FAILED:'+output.getvalue())
    return dict(status='OBSERVER_PRIVATE_READ_AND_ORDINARY_OWNER_COMMAND_CONTROL_PASS',
        tests_run=1,effective_policy_variants=2,actual_SQL_executed=0,actual_Native_cases=0)

def runtime():
    from cp7_accessory_nonpayable import admission,source,package_engine
    admission.parent_receipt()  # Before any ERP import or runtime construction.
    source.preflight()
    with admission.parent_scope():
        original=ROOT/package_engine.ORIGINAL
        text,derivation=package_engine.derive(original.read_bytes())
        engine=ModuleType('afui_exact_original_whole_package_engine');engine.__file__=str(original)
        exec(compile(text,str(original),'exec'),engine.__dict__)
        from cp7_accessory_nonpayable import assembly,native_fixture,advisor_review,qualification_component as component
        engine.product=assembly
        engine.runner=SimpleNamespace(CASE=component.CASE,exercise=component.exercise,scheduler_quiet=component.scheduler_quiet)
        engine.current_advisor=advisor_review
        engine.IDS=(component.CASE,);engine.LABEL=component.LABEL
        engine.PRE_DUMP='/tmp/current_afui_good_nonpayable_full_pre.dump'
        engine.OUT=ROOT/'cp6-proof/t3'/(component.LABEL+'.json')
        def admitted():
            receipt=admission.parent_receipt();static=source.preflight();graph=assembly.sources()
            return dict(status='ACTUAL_FREE3_PARENT_AND_COMPLETE_NONPAYABLE_SOURCE_GRAPH_ADMITTED',
                parent_head=receipt['head'],parent_tree=receipt['tree'],parent_run=receipt['run_id'],
                own_source=static,complete_sources=graph,whole_engine_derivation=derivation,
                actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,
                production_go=False,independent_acceptance=False)
        engine.admitted=admitted
        assembly.runtime()  # Include the complete real inherited import path.
        engine.native_domain_binding=native_fixture.domain_modules()[1]
    return engine,admission

def main():
    parser=argparse.ArgumentParser();modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check-static',action='store_true');modes.add_argument('--check',action='store_true')
    modes.add_argument('--runtime',action='store_true');args=parser.parse_args()
    from cp7_accessory_nonpayable import admission,source,package_engine,copy_context
    if args.check_static:
        static=source.preflight()
        actors=fixture_actor_preflight()
        _,engine=package_engine.derive((ROOT/package_engine.ORIGINAL).read_bytes())
        _,copies=copy_context.derive((ROOT/copy_context.ORIGINAL).read_bytes())
        print(json.dumps(dict(status='NONPAYABLE_STATIC_WHOLE_QUALIFIER_PREPARED_NOT_EXECUTED',source=static,
            whole_engine=engine,copy_authority=copies,fixture_actor_preflight=actors,actual_SQL_executed=0,actual_Native_cases=0,
            actual_Auth_HTTP_cases=0,actual_two_session_cases=0,actual_browser_cases=0,
            production_go=False,independent_acceptance=False),sort_keys=True));return
    admission.parent_receipt()
    if args.check:
        fence=load('afui_exact_original_three_entrypoint_source_fence',
            ROOT/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
        with fence.fenced_source_read()as guard:engine,_=runtime();proof=engine.admitted()
        print(json.dumps(dict(status=proof['status'],source_DB_guard=guard,
            actual_domain_and_caller_binding=engine.native_domain_binding,
            entire_natural_product_source_graph_evaluated=True,actual_Native_cases=0,production_go=False),sort_keys=True));return
    if os.environ.get('AFUI_CONFIRM')!='cp6_rollback':raise ValueError('NONPAYABLE_EXPLICIT_DISPOSABLE_QUALIFICATION_REQUIRED')
    attempts=load('afui_unchanged_real_six_hour_WIB_single_attempt',ROOT/'scripts/current-de-free-date-preparation/attempt_policy.py')
    print(json.dumps(dict(attempt_policy=attempts.require_window())),flush=True)
    engine,admission=runtime();engine.admitted()
    with admission.parent_scope():
        import cp6_auditor_business_day as business_day
        original=engine.package._writer_runtime
        try:
            engine.package._writer_runtime=lambda browser_mode=False:engine.run()
            with attempts.single_attempt(business_day):engine.package.run('install')
        finally:engine.package._writer_runtime=original

if __name__=='__main__':
    sys.path.insert(0,str(ROOT/'scripts'));main()
