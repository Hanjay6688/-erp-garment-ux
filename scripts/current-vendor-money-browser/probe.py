"""A money-screen browser2 after exact complete backend11/package admission.

Retains the established install/restoration runtime, no new browser runner.
"""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess,sys,traceback
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO/'scripts'))
import cp7_p21_current_chain_rehearsal_probe as chain
import cp7_current_choice_preparation.installation as predecessor
import importlib.util
from cp7_vendor_receivable import composition as product
_readonly_spec=importlib.util.spec_from_file_location('combined_readonly_installer',REPO/'scripts/current-finance-readonly-integration-qualification/composition.py')
readonly=importlib.util.module_from_spec(_readonly_spec);_readonly_spec.loader.exec_module(readonly)
_spec=importlib.util.spec_from_file_location('full_current_finance_model_cron',HERE/'runner.py')
runner=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(runner)
_spec=importlib.util.spec_from_file_location('full_current_finance_model_native_admission',REPO/'scripts/current-frozen-public-native-qualification/probe.py')
qualified_native=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(qualified_native)
_spec=importlib.util.spec_from_file_location('bounded_finance_current_native',REPO/'scripts/current-analog-consumer-opening-qualification/probe.py')
current_native=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(current_native)
import psycopg
from cp6_t3_aligned_install import advisors,advisor_delta
from cp7_catalog_state import exact_public_catalog
control=chain.helper.control
previous,native,package,core,p09=chain.previous,control.native,chain.package,chain.core,chain.p09
IDS=(runner.CASE,)
LABEL='CP7_VENDOR_MONEY_BROWSER2'
PRE_DUMP='/tmp/vendor_money_browser_pre.dump'
database,drill,dump=current_native.database,current_native.drill,current_native.dump
sql=current_native.sql
OUT=REPO/'cp6-proof/t3'/f'{LABEL}.json'
STATE=None
_spec=importlib.util.spec_from_file_location('current_choice_cron_timing',REPO/'scripts/current-choice-finance-cron-qualification/phase_timing.py')
phase_timing=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(phase_timing)
measured=phase_timing.measured
_spec=importlib.util.spec_from_file_location('current_choice_cron_roles',REPO/'scripts/current-choice-finance-cron-qualification/restore_roles.py')
role_cleanup=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(role_cleanup)
_spec=importlib.util.spec_from_file_location('current_choice_cron_advisors',REPO/'scripts/current-choice-preparation-native-qualification/advisor_review.py')
current_advisor=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(current_advisor)


def admitted():
    return load_admission().admitted(REPO,HERE,product)

def load_admission():
    spec=importlib.util.spec_from_file_location('vendor_money_browser_source_admission',HERE/'admission.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def verify(cur):
    if STATE is None:raise ValueError('OW12A_INSTALLATION_REQUIRED')
    # The retained SQL harness alone may grant ERP USAGE; it is removed only
    # while the product catalog is compared, never projected into the product.
    with control.product_catalog(cur):
        return product.verify(cur,STATE)


def run_inner():
    global STATE
    timings=[]
    report=dict(label=LABEL,status='INCOMPLETE',source_declaration=measured(timings,'SOURCE_ADMISSION',admitted),stage_timings=timings,
        qualification_commit=subprocess.check_output(['git','-C',str(REPO),'rev-parse','HEAD'],text=True).strip(),
        expected_case_count=len(IDS),required_case_ids=list(IDS),formal_CP7C_started=False,real_Auth_browser_claim=False,real_Auth_HTTP_qualified=False,factory3600_claim=False,
        full_OW11_acceptance=False,production_go=False,independent_acceptance=False,
        committed={},native={},actual_cron_claim=False,manual_steps=0,changed_schedule=False,additional_initial_schedule=False,
        manual_steps_scope='ACTUAL_AUTH_MONEY_UI_ON_ISOLATED_COMMITTED_BROWSER_COPY',native20_repeated_unchanged=False,retained_race_baseline=True,
        full_parent_inverse_repeated=False,focused_preuse_delta_only=True)
    installed=False;pre_dumped=False;before=None;new_roles=set()
    try:
        assert drill.SOURCE==database.SOURCE=='cp6_rollback'and drill.CONTAINER=='supabase_db_cp5-local'
        with psycopg.connect(package.boundary.ADMIN)as check,check.cursor()as cursor:
            assert STREAM_CONTEXT['original'](cursor)==STREAM_CONTEXT['candidate'](cursor)
            report['exact_streaming_data_validation']={'status':'PASS_REAL_BASELINE_EQUALITY_ONLY','prior_large_regression_repeated':False}
            check.rollback()
        report['streaming_data_source_guard']={k:v for k,v in STREAM_CONTEXT.items()if k not in ('original','candidate')}
        report['baseline_advisors']=measured(timings,'BASELINE_ADVISORS',advisors,package.boundary.PG)
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            assert conn.info.host in('127.0.0.1','localhost')and cur.execute('select current_database()').fetchone()==(database.SOURCE,)
            p09.wip.policy.bf.verified(cur)
            before_roles=database._roles(cur)
            baseline_catalog=predecessor.catalog._portable(predecessor.catalog._catalog_rows(cur))
            baseline_data=predecessor.catalog._data(cur)
            before=previous.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions)
            conn.rollback()
        pre_data=drill.data_hashes(database.SOURCE);pre_profile=database._database_profile(database.SOURCE)
        measured(timings,'BASELINE_DUMP',dump.dump,database.SOURCE,PRE_DUMP);pre_dumped=True
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            try:
                report['install_boundary_lock']=current_native.acquire_boundary(cur)
                # Exercise the existing complete candidate entry point directly.
                # Its parent performs the same qualified readonly/3194 chain;
                # legacy installation inventory remains inside that chain.
                STATE=measured(timings,'EXACT_CURRENT_CANDIDATE_INSTALL',product.install,cur)
                # Exact backend11/package admission already proves this identical
                # delta's unused inverse. Reinstall only once on this new VM.
                report['focused_preuse_removal']=dict(status='RETAINED_EXACT_BACKEND11_PREUSE_INVERSE',
                    head=report['source_declaration']['prerequisite']['head'],fresh_inverse_execution=False,
                    used_guard_before_DDL=True)
            except Exception:
                # Keep the exact predecessor definitions for diagnosis of a changed anchor.
                report['installation_failed_before_commit']=True
                raise
            control.STATE=dict(installed_catalog=STATE['after'])
            report['complete_installed_verification']=product.verify(cur,STATE)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            report['current_private_info_authority']=current_advisor.capture(cur)
            new_roles=database._roles(cur)-before_roles
            conn.commit();installed=True
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        case=report['committed'].setdefault(runner.CASE,dict(status='INCOMPLETE'))
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            measured(timings,'ISOLATED_DIAGNOSTICS',runner.exercise,conn,cur,database,package.boundary.ADMIN,case,STATE)
        assert case['used_guard_refused_before_DDL'] is True
        report['used_guard_refused_before_DDL']=True
    except Exception as error:
        report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if before is not None and pre_dumped:
            try:
                if report['committed']:
                    report['scheduler_quiet_before_baseline_restore']=runner.scheduler_quiet(package.boundary.ADMIN)
                # This case commits real Native posting and runner progress. Restore the
                # complete preinstall dump; never reset selected sequences or
                # weaken the product's global all-data guard.
                restored=measured(timings,'BASELINE_RESTORE',database._restore,PRE_DUMP,database.SOURCE,pre_profile)
                assert restored['only_pg_cron_errors']
                report['baseline_restore']=restored
                assert drill.data_hashes(database.SOURCE)==pre_data
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    report['baseline_role_cleanup']=role_cleanup.restore_roles(cur,before_roles,new_roles,database._roles)
                    conn.commit();assert database._roles(cur)==before_roles
                    assert predecessor.catalog._portable(predecessor.catalog._catalog_rows(cur))==baseline_catalog
                    assert predecessor.catalog._data(cur)==baseline_data
                    report['baseline_full22_all_rows_all_sequences_equal']=True
                    report['cp6_restored']=previous.restore_state.prove(cur,before,package.boundary.snapshot,
                        core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['baseline_advisors_equal']=advisors(package.boundary.PG)==report['baseline_advisors']
                if 'advisors_with_cp7'in report:
                    report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                    report['advisor_disposition']=current_advisor.review(report['advisor_delta'],report['verified_predecessor_info_manifest'],report['current_private_info_authority'],core.advisor_disposition)
                    report['advisor_gate']=report['advisor_disposition']['gate']and report['baseline_advisors_equal']
                else:report['advisor_gate']=report['baseline_advisors_equal']
            except Exception as error:
                report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        drill.docker('rm','-f',PRE_DUMP,check=False)
        cases=report['committed']
        report['observed_case_count']=len(cases)
        report['required_case_ids_pass']=set(cases)==set(IDS)and all(c['status']=='PASS'for c in cases.values())
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate')and report.get('baseline_full22_all_rows_all_sequences_equal')and report.get('focused_preuse_removal')and report['required_case_ids_pass']and report.get('used_guard_refused_before_DDL'):
            report['status']='PASS'
            report['actual_cron_claim']=False
            report['actual_two_session_races']=0
            report['actual_Auth_HTTP_cases']=0
            report['actual_Native_cases']=0
            report['retained_backend11_cases']=11
            report['actual_browser_cases']=2
            report['real_Auth_browser_claim']=True
            report['new_vendor_money_UI_qualified']=True
            report['used_guard_evidence']='RETAINED_EXACT_COMPLETE_BACKEND11_NOT_RERUN'
            report['combined_component_qualified']=False
            report['focused_factory_closure']=False
            report['performance_qualification']=False
            report['full_combined_final_qualification']=False
            report['default_adopted']=False
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({key:report.get(key)for key in('label','status','observed_case_count','cp6_restored','advisor_gate','error','restore_error')},default=str),flush=True)
        for name,case in cases.items():
            print(json.dumps(dict(case=name,status=case.get('status'),error=case.get('error')),default=str)[:3000],flush=True)
    return dict(status=report['status'],full_OW11_acceptance=False,production_go=False,independent_acceptance=False)


_stream_spec=importlib.util.spec_from_file_location('exact_streamed_whole_data_guard',REPO/'scripts/current-factory-initial-stage/stream_data.py')
stream_data=importlib.util.module_from_spec(_stream_spec);_stream_spec.loader.exec_module(stream_data)
STREAM_CONTEXT=None


def run():
    global STREAM_CONTEXT
    _,_,_,_,catalog=product.runtime()
    with stream_data.bound(catalog)as context:
        STREAM_CONTEXT=context
        try:return run_inner()
        finally:STREAM_CONTEXT=None


if __name__=='__main__':
    admitted();package._writer_runtime=lambda browser_mode=False:run();package.run('install')
