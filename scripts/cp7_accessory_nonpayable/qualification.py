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

def fixture_browser_date_preflight():
    """Refuse a success fixture that collides with immutable posted GOOD."""
    import io,unittest
    from cp7_accessory_nonpayable.test_native_preparation import NativePreparationControls
    name='test_browser_save_dates_follow_posted_good_without_relabeling_physical_day'
    output=io.StringIO()
    result=unittest.TextTestRunner(stream=output,verbosity=0).run(
        unittest.TestSuite([NativePreparationControls(name)]))
    if result.testsRun!=1 or not result.wasSuccessful() or result.skipped or result.expectedFailures:
        raise ValueError('NONPAYABLE_FIXTURE_BROWSER_DATE_PREFLIGHT_FAILED:'+output.getvalue())
    return dict(status='FUTURE_BROWSER_SAVE_DATE_PRESERVES_POSTED_GOOD_DAY',
        tests_run=1,calendar_variants=4,actual_SQL_executed=0,actual_browser_cases=0)

def fixture_committed_identity_preflight():
    """Refuse the missing cold-copy foundation before the long owning run."""
    import io,unittest
    from cp7_accessory_nonpayable.test_committed_preparation import CommittedPreparationControls
    output=io.StringIO()
    result=unittest.TextTestRunner(stream=output,verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(CommittedPreparationControls))
    if result.testsRun!=5 or not result.wasSuccessful()or result.skipped or result.expectedFailures:
        raise ValueError('NONPAYABLE_COMMITTED_IDENTITY_PREFLIGHT_FAILED:'+output.getvalue())
    return dict(status='COLD_COPY_ORIGINAL_OWNER_SETUP_AND_INVALID_IDENTITY_REFUSALS_PASS',
        tests_run=5,existing_role_promotion=False,actual_SQL_executed=0,actual_Native_cases=0)

def fixture_browser_observer_preflight():
    """Reproduce the legacy cold-process failure and require exact raw22."""
    import io,unittest
    from cp7_accessory_nonpayable.test_browser_observer import BrowserObserverControls
    output=io.StringIO();result=unittest.TextTestRunner(stream=output,verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(BrowserObserverControls))
    if result.testsRun!=6 or not result.wasSuccessful()or result.skipped or result.expectedFailures:
        raise ValueError('NONPAYABLE_COLD_BROWSER_OBSERVER_PREFLIGHT_FAILED:'+output.getvalue())
    return dict(status='COLD_BROWSER_ORIGINAL_FAILURE_REPRODUCED_EXACT_RAW22_READER_PASS',tests_run=6,
        inherited_process_STATE_required=False,Native_overlay_applied=False,
        actual_SQL_executed=0,actual_Native_cases=0,actual_browser_cases=0)

def fixture_case_output_preflight():
    """Verify exact complete files and bounded receipts before provisioning."""
    import io,unittest
    from cp7_accessory_nonpayable.test_case_output import CaseOutputControls
    output=io.StringIO();result=unittest.TextTestRunner(stream=output,verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(CaseOutputControls))
    if result.testsRun!=7 or not result.wasSuccessful()or result.skipped or result.expectedFailures:
        raise ValueError('NONPAYABLE_COMPLETE_CASE_OUTPUT_PREFLIGHT_FAILED:'+output.getvalue())
    return dict(status='COMPLETE_ORIGINAL_CASE_BYTES_BOUNDED_CONSOLE_AND_UNCHANGED_RESULTS_PASS',
        tests_run=7,routed_print_sites=3,actual_SQL_executed=0,actual_Native_cases=0)

def fixture_progress_preflight():
    """Bound diagnostics and preserve original failures and restoration."""
    import io,unittest
    from cp7_accessory_nonpayable.test_progress import ProgressControls
    output=io.StringIO();result=unittest.TextTestRunner(stream=output,verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ProgressControls))
    if result.testsRun!=5 or not result.wasSuccessful()or result.skipped or result.expectedFailures:
        raise ValueError('NONPAYABLE_BOUNDED_PROGRESS_PREFLIGHT_FAILED:'+output.getvalue())
    return dict(status='BOUNDED_PHASE_RECEIPTS_PRESERVE_RESULTS_ERRORS_AND_CLEANUP',tests_run=5,
        new_timers_or_workers=0,actual_SQL_executed=0,actual_Native_cases=0)

def fixture_report_io_preflight():
    """Check bytes, snapshot isolation and bounded memory before any DB."""
    import io,unittest
    from cp7_accessory_nonpayable.test_report_io import ReportIOControls
    output=io.StringIO();result=unittest.TextTestRunner(stream=output,verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(ReportIOControls))
    if result.testsRun!=8 or not result.wasSuccessful()or result.skipped or result.expectedFailures:
        raise ValueError('NONPAYABLE_REPORT_IO_PREFLIGHT_FAILED:'+output.getvalue())
    return dict(status='EXACT_COMPLETE_JSON_INDEPENDENT_SNAPSHOTS_AND_MEMORY_LIMIT_PASS',
        tests_run=8,actual_SQL_executed=0,actual_Native_cases=0)

def fixture_complete_original_io_preflight():
    """Check every remaining complete snapshot writer before provisioning."""
    import io,unittest
    from contextlib import redirect_stdout
    from cp7_accessory_nonpayable.test_complete_original_io import CompleteOriginalStorage
    output=io.StringIO()
    with redirect_stdout(output):
        result=unittest.TextTestRunner(stream=output,verbosity=0).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(CompleteOriginalStorage))
    if result.testsRun!=9 or not result.wasSuccessful()or result.skipped or result.expectedFailures:
        raise ValueError('NONPAYABLE_COMPLETE_ORIGINAL_STORAGE_PREFLIGHT_FAILED:'+output.getvalue())
    return dict(status='EXACT_SORTED_JSON_GZIP_COPY_AND_IMMUTABLE_COMPLETE_ORIGINALS_PASS',
        tests_run=9,memory_control_limit_MiB=160,actual_SQL_executed=0,actual_Native_cases=0,
        runner_shutdown_origin_proven=False)

def fixture_lossless_state_preflight():
    import io,unittest
    from cp7_accessory_nonpayable.test_lossless_state import LosslessStateControls
    output=io.StringIO()
    result=unittest.TextTestRunner(stream=output,verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(LosslessStateControls))
    if result.testsRun!=12 or not result.wasSuccessful()or result.skipped or result.expectedFailures:
        raise ValueError('NONPAYABLE_COMPLETE_LOSSLESS_STATE_PREFLIGHT_FAILED:'+output.getvalue())
    return dict(status='EVERY_CANONICAL_STATE_BYTE_AND_INDEPENDENT_CONTAINER_VERIFIED',tests_run=12,
        dropped_keys_or_values=0,actual_SQL_executed=0,actual_browser_case_credit=0)

def fixture_complete_state_preflight():
    import io,unittest
    from cp7_accessory_nonpayable.test_state_prepare import StatePreparationControls
    output=io.StringIO()
    result=unittest.TextTestRunner(stream=output,verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromTestCase(StatePreparationControls))
    if result.testsRun!=12 or not result.wasSuccessful()or result.skipped or result.expectedFailures:
        raise ValueError('NONPAYABLE_EARLY_COMPLETE_STATE_PREFLIGHT_FAILED:'+output.getvalue())
    return dict(status='EARLY_COMPLETE_HOT_STATE_RESOURCE_AND_FIRST_ORIGINAL_GUARDS_PASS',tests_run=12,
        actual_allocation_refusal_verified=True,actual_SQL_executed=0,actual_case_credit=0,
        previous_runner_shutdown_origin_proven=False)

def runtime():
    from cp7_accessory_nonpayable import admission,source,package_engine
    admission.parent_receipt()  # Before any ERP import or runtime construction.
    source.preflight()
    with admission.parent_scope():
        original=ROOT/package_engine.ORIGINAL
        text,derivation=package_engine.derive(original.read_bytes())
        from cp7_accessory_nonpayable import report_io
        text,report_io_derivation=report_io.derive_engine(text)
        engine=ModuleType('afui_exact_original_whole_package_engine');engine.__file__=str(original)
        exec(compile(text,str(original),'exec'),engine.__dict__)
        engine.__dict__[report_io.HELPER]=report_io.write_complete
        from cp7_accessory_nonpayable import assembly,native_fixture,advisor_review,case_output,qualification_component as component
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
                whole_report_IO_derivation=report_io_derivation,
                actual_owning_report_IO_binding=engine.report_io_binding,
                actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,
                production_go=False,independent_acceptance=False)
        engine.admitted=admitted
        assembly.runtime()  # Include the complete real inherited import path.
        modules,engine.native_domain_binding=native_fixture.domain_modules()
        case_output.binding(modules.control.native,'native')
        _,_,engine.report_io_binding=report_io.binding(modules.control.native.r1)
        copies=component.load('afui_preDB_original_copy_modes',ROOT/case_output.SOURCES['copies'][0])
        case_output.binding(copies,'copies')
        case_output.sources()
    return engine,admission

def main():
    parser=argparse.ArgumentParser();modes=parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--check-static',action='store_true');modes.add_argument('--check',action='store_true')
    modes.add_argument('--runtime',action='store_true');args=parser.parse_args()
    from cp7_accessory_nonpayable import admission,source,package_engine,copy_context
    if args.check_static:
        static=source.preflight()
        actors=fixture_actor_preflight()
        browser_dates=fixture_browser_date_preflight()
        committed_identity=fixture_committed_identity_preflight()
        browser_observer=fixture_browser_observer_preflight()
        case_output=fixture_case_output_preflight()
        progress=fixture_progress_preflight()
        report_io=fixture_report_io_preflight()
        complete_original_io=fixture_complete_original_io_preflight()
        lossless_state=fixture_lossless_state_preflight()
        complete_state=fixture_complete_state_preflight()
        _,engine=package_engine.derive((ROOT/package_engine.ORIGINAL).read_bytes())
        _,copies=copy_context.derive((ROOT/copy_context.ORIGINAL).read_bytes())
        print(json.dumps(dict(status='NONPAYABLE_STATIC_WHOLE_QUALIFIER_PREPARED_NOT_EXECUTED',source=static,
            whole_engine=engine,copy_authority=copies,fixture_actor_preflight=actors,fixture_browser_date_preflight=browser_dates,
            fixture_committed_identity_preflight=committed_identity,
            fixture_browser_observer_preflight=browser_observer,
            fixture_case_output_preflight=case_output,
            fixture_progress_preflight=progress,
            fixture_report_io_preflight=report_io,
            fixture_complete_original_io_preflight=complete_original_io,
            fixture_lossless_state_preflight=lossless_state,
            fixture_complete_state_preflight=complete_state,
            actual_SQL_executed=0,actual_Native_cases=0,
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
        from cp7_accessory_nonpayable import progress
        original=engine.package._writer_runtime
        try:
            engine.package._writer_runtime=lambda browser_mode=False:engine.run()
            with attempts.single_attempt(business_day),progress.phase('WHOLE_PACKAGE'):engine.package.run('install')
        finally:engine.package._writer_runtime=original

if __name__=='__main__':
    sys.path.insert(0,str(ROOT/'scripts'));main()
