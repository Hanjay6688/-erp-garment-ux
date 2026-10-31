"""One actual repaired Owner-access callback; unchanged whole outer package."""
from pathlib import Path
from types import ModuleType,SimpleNamespace
from hashlib import sha256
import argparse,importlib.util,json,os

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
LABEL='CP7_CURRENT_S03_SKU_S05_OWNER_ACCESS_NATIVE1'
COUNTS="""report['actual_two_session_races']=0
            report['actual_Native_cases']=1
            report['actual_Auth_HTTP_cases']=0
            report['actual_browser_cases']=0
            report['actual_business_cases']=1
            report['retained_full37_fresh_case_credit']=0
            report['real_Auth_HTTP_qualified']=False
            report['real_Auth_browser_claim']=False"""


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def derive(raw):
    original=load('owner_focus_exact_current_whole_engine',HERE/'engine.py')
    text,parent=original.derive(raw)
    if text.count(original.COUNTS_AFTER)!=1 or COUNTS in text:raise ValueError('OWNER_FOCUS_EXACT_ENGINE_SCOPE_REQUIRED')
    result=text.replace(original.COUNTS_AFTER,COUNTS,1)
    if result.replace(COUNTS,original.COUNTS_AFTER,1)!=text:raise ValueError('OWNER_FOCUS_ORIGINAL_WHOLE_ENGINE_NOT_RECOVERED')
    return result,dict(parent=parent,scope_changes=1,whole_current_engine_recovered=True,
        derived_sha256=sha256(result.encode()).hexdigest(),actual_Native_cases=0,planned_Native_cases=1,
        full37_qualified=False,production_go=False)


def runtime():
    admission=load('owner_focus_full_current_parent_admission',HERE/'admission.py');admission.admitted()
    with admission.import_scope():
        path=ROOT/'scripts/current-vendor-receivable-qualification/probe.py'
        text,derivation=derive(path.read_bytes());engine=ModuleType('owner_focus_original_complete_package_engine')
        engine.__file__=str(path);exec(compile(text,str(path),'exec'),engine.__dict__)
        from cp7_s03_sku_composition import composition as product
        component,component_proof=load('owner_focus_unchanged_access_component',HERE/'owner_focus_native.py').component()
        engine.product=product
        engine.runner=SimpleNamespace(CASE=component.CASE,exercise=component.exercise,scheduler_quiet=component.scheduler_quiet)
        engine.IDS=(component.CASE,);engine.LABEL=LABEL;engine.OUT=ROOT/'cp6-proof/t3'/(LABEL+'.json')
        engine.PRE_DUMP='/tmp/current_S05_owner_access_focused1_full_pre.dump'
        def admitted():
            current=admission.admitted()
            if product.sources()!=current['current_installation']:raise ValueError('OWNER_FOCUS_CURRENT_ACTUAL_SOURCE_CHANGED')
            return dict(current,complete_engine_derivation=derivation,focused_component_derivation=component_proof)
        engine.admitted=admitted
    return engine,admission


def final_gate():
    out=ROOT/'cp6-proof/t3';main=json.loads((out/(LABEL+'.json')).read_bytes())
    case=load('owner_focus_literal_case_identity',HERE/'owner_focus_native.py').CASE
    package=json.loads((out/'T3_PACKAGE_INSTALL.json').read_bytes())
    if(main.get('status')!='PASS'or main.get('actual_Native_cases')!=1 or main.get('actual_browser_cases')!=0
       or main.get('actual_business_cases')!=1 or main.get('required_case_ids')!=[case]
       or main.get('required_case_ids_pass')is not True or main.get('cp6_restored')is not True
       or main.get('baseline_full22_all_rows_all_sequences_equal')is not True or main.get('advisor_gate')is not True
       or package['gate']!=dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=True)):
        raise ValueError('OWNER_FOCUS_EXACT_ACTUAL_NATIVE1_ALL5_AND_FULL_RESTORE_REQUIRED')
    row=main['committed'][case]
    seeded=row.get('focused_additional_owner_fixture',{})
    if(row.get('status')!='PASS'or row.get('actual_Native_cases')!=1
       or row.get('native',{}).get('counts')!={'PASS':1}or seeded.get('active_owners_after',0)<2
       or row.get('used_guard_refused_before_DDL')is not True):
        raise ValueError('OWNER_FOCUS_REPAIRED_ACCESS_WITH_REAL_EXTRA_OWNER_REQUIRED')
    actual=row['native']['cases']['S05_NATIVE_CURRENT_ACCESS_PRIVATE_ACL']
    observations=actual.get('original_owner_fixture_observations',[])
    original=next((x for x in observations if x.get('kind')=='EXPLICIT_ISOLATED_ORIGINAL_LAST_OWNER_ROSTER'),{})
    guarded={x['label']:x for x in observations if x.get('kind')=='ACTUAL_NATIVE_FIXTURE_REFUSAL_NO_EFFECT'}
    for label,message in(('LAST_ACTIVE_OWNER_UNCHANGED','LAST_ACTIVE_OWNER_PROTECTED'),
        ('PROTECTED_OWNER_ROLE_UNCHANGED','PROTECTED_OWNER_ROLE_CANNOT_BE_CHANGED')):
        event=guarded.get(label,{})
        if(event.get('actual_error',{}).get('sqlstate')!='42501'
           or event.get('actual_error',{}).get('message','').splitlines()[0:1]!=[message]
           or event.get('all22_catalog_equal')is not True or event.get('all_rows_and_every_sequence_equal')is not True):
            raise ValueError('OWNER_FOCUS_ACTUAL_UNCHANGED_NATIVE_GUARD_AND_RAW_NO_EFFECT_REQUIRED:'+label)
    if len(original.get('before',[]))<2 or original.get('original_last_owner_precondition_retained')is not True:
        raise ValueError('OWNER_FOCUS_ACTUAL_MULTIPLE_TO_ONE_OWNER_FIXTURE_REQUIRED')
    value=dict(status='ACTUAL_OWNER_ACCESS_NATIVE1_ALL5_COMPLETE_RESTORE',actual_Native_cases=1,
        full37_qualified=False,prior_current30_relabelled_as_fresh=False,production_go=False,independent_acceptance=False)
    (out/'OWNER_FOCUS_FINAL_GATE.json').write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(value))


def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--runtime',action='store_true');mode.add_argument('--check',action='store_true');mode.add_argument('--final-gate',action='store_true')
    args=parser.parse_args()
    if args.final_gate:return final_gate()
    if args.check:
        fence=load('owner_focus_original_source_fence',ROOT/'scripts/current-sku-managed-recovery-native27-qualification/source_context.py')
        with fence.fenced_source_read()as guard:
            engine,_=runtime();proof=engine.admitted()
        print(json.dumps(dict(status=proof['status'],source_DB_guard=guard,actual_Native_cases=0)));return
    if os.environ.get('JOIN_CONFIRM')!='cp6_rollback':raise ValueError('OWNER_FOCUS_EXPLICIT_DISPOSABLE_CONFIRMATION_REQUIRED')
    attempts=load('owner_focus_same_actual_job_and_real_WIB_budget',HERE/'owner_focus_attempt_policy.py')
    print(json.dumps(dict(attempt_policy=attempts.require_window())),flush=True)
    notes=load('owner_focus_exact_diagnostic_only_monitor',HERE/'runtime_note.py')
    with notes.monitor(),notes.phase('OWNER_ACCESS_NATIVE1_WHOLE_PACKAGE'):
        engine,admission=runtime();engine.admitted()
        with admission.import_scope():
            original=engine.package._writer_runtime
            try:
                engine.package._writer_runtime=lambda browser_mode=False:engine.run()
                import cp6_auditor_business_day as business_day
                with attempts.single_attempt(business_day):engine.package.run('install')
            finally:engine.package._writer_runtime=original


if __name__=='__main__':main()
