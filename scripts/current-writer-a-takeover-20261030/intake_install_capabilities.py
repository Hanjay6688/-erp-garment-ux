"""Read-only pairing of actual Supabase17 capability originals; zero ERP credit.

Only Afui is fresh in the successor. Mandor and the unsupported catalog lock
remain exact observations from the failed first run. Source-bound reports are
not independently recomputed raw all22 financial censuses.
"""
from pathlib import Path,PurePosixPath
from hashlib import sha256
import argparse,json,stat,zipfile
from intake_common import GitBytes,exact,fields,pin,require
from intake_sku27 import strict

HEAD='adb03eaa3e06ad98243e6d15b9273f1fcd9c37dc'
TREE='4fc70e1da0bc0ae1ca72f0b00fbca2d7001ca00c'
RUN=41438058379
JOB=125252703138
BASE_HEAD='b8c572d28f944ad9a5947ffc164e134558ed6641'
BASE_TREE='300254b48a70162356ce70c9416e2a4c1a33b62d'
NS='scripts/current-install-authority-capability/'
WF='.github/workflows/cp7-install-authority-capability.yml'
FIRST=dict(bytes=8631,sha256='3cffb9cf3138ba973b651971e7d9cd968c830fe65329e89d76e1201825c3ba68')
SUCCESS=dict(bytes=9239,sha256='9453300702b8b8b5d68ece53b8193a8ed914caad6d69770760e9ed51c1b7bf56')
OWN={NS+n for n in('MANDOR_ACTUAL_CREATOR_ACL_REFERENCE.json','MANDOR_COMPOSED.sql',
 'MANDOR_COMPOSITION_SOURCE.json','MANDOR_EXPECTED_BODIES.json','MANDOR_INVERSE.sql',
 'MANDOR_MODEL_BASE.sql','RETAINED_MANDOR_AND_CATALOG_OBSERVATIONS.json','SOURCE.json','probe.py')}|{WF}


def source(g):
    base=g.entries(BASE_TREE)
    for name,entry in base.items():exact(g.tree.get(name),entry,'CAPABILITY_ENTIRE_AFUI100_PARENT_UNCHANGED:'+name)
    exact(set(g.tree)-set(base),OWN,'CAPABILITY_ONLY_EXACT_TEN_NEW_CAPSULE_PATHS')
    declaration=strict(g.read(NS+'SOURCE.json'))
    fields(declaration,dict(classification='ISOLATED_ACTUAL_SUPABASE17_INSTALL_AUTHORITY_CAPABILITIES_NOT_ERP',
        retained_Mandor_and_Global_NOT_rerun=True,only_new_actual_capability='AFUI',
        genuine_six_hour_financial_policy_unchanged=True,no_actual_parent_or_business_qualification=True,
        actual_Native_cases=0,production_go=False,independent_acceptance=False),'CAPABILITY_FIXED_SUCCESSOR_SCOPE')
    inherited={'scripts/cp7_accessory_nonpayable/'+n for n in('function_acl_capability.py','settings_stage.py',
        'settings.sql','policy.sql','basis.sql','test_settings.mjs','ACTUAL_FUNCTION_DEFAULT_ACL_REFERENCE.json',
        'composition.py','SOURCE.json','FIRST_POSTGRES17_CAPABILITY_FAILURE_AND_REPAIR.json')}
    inherited|={'scripts/cp7_ow04_restore_bundle.py','scripts/current-finance-combined-composition/disposable_start.py'}
    exact(set(declaration['files']),(OWN-{NS+'SOURCE.json'})|inherited,'CAPABILITY_COMPLETE_EXACT21_INPUT_PINS')
    for name,value in declaration['files'].items():g.verify_pin(name,value)
    g.verify_pin(NS+'probe.py',dict(bytes=14253,sha256='f938478ef9c030f67ca66c8f5e172581ccf2525d2ec315dad93e1b2d22c29e48'))
    composition=strict(g.read(NS+'MANDOR_COMPOSITION_SOURCE.json'))
    exact(pin(g.read(NS+'MANDOR_COMPOSED.sql')),composition['source']['derived_SQL'],'CAPABILITY_EXACT_MANDOR_DERIVED_SOURCE')
    require(composition['source']['all_nine_function_bodies_unchanged']is True,'CAPABILITY_NINE_ORIGINAL_MANDOR_BODIES')
    exact(len(strict(g.read(NS+'MANDOR_EXPECTED_BODIES.json'))),9,'CAPABILITY_EXACT_NINE_MANDOR_BODIES')
    return dict(status='ROOT_EXACT21_CAPABILITY_INPUTS_AND_UNCHANGED_AFUI100_PARENT_SOURCE',
        source_pins=21,new_paths=10,unchanged_parent_paths=len(base),only_fresh_capability='AFUI',
        retained_Mandor_and_catalog_not_rerun=True,actual_ERP_imports=0,actual_SQL_executed=0)


def archive(path,expected):
    exact(pin(path.read_bytes()),expected,'CAPABILITY_EXACT_COMPLETE_ORIGINAL_ARCHIVE')
    with zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(names),len(set(names)),'CAPABILITY_UNIQUE_ARCHIVE_MEMBERS')
        for n in names:
            p=PurePosixPath(n);require(not p.is_absolute()and'..'not in p.parts and'\\'not in n,'CAPABILITY_SAFE_ARCHIVE_PATH')
            require(stat.S_IFMT(z.getinfo(n).external_attr>>16)in(0,stat.S_IFDIR,stat.S_IFREG),'CAPABILITY_NO_SPECIAL_MEMBER')
        require(z.testzip()is None,'CAPABILITY_COMPLETE_ORIGINAL_CRC')
        selected=[n for n in names if n.endswith('INSTALL_AUTHORITY_CAPABILITIES.json')]
        exact(len(selected),1,'CAPABILITY_ONE_ORIGINAL_CAPABILITY_REPORT')
        raw=z.read(selected[0]);return strict(raw),dict(member=selected[0],**pin(raw))


def intake(g,first_path,success_path):
    proof=source(g);first,first_pin=archive(first_path,FIRST);latest,latest_pin=archive(success_path,SUCCESS)
    fields(first['source'],dict(head='018d3bc3fc2e1b5e2749cc25a466edf8df78c2d2',
        tree='f854965791b8f7a22bd4b862477a9e88d9d6ad14',actual_Native_cases=0),'CAPABILITY_EXACT_FIRST_SOURCE')
    exact(first['status'],'INCOMPLETE','CAPABILITY_FIRST_FAILURE_REMAINS_INCOMPLETE')
    exact(first['failed_capabilities'],['AFUI'],'CAPABILITY_EXACT_FIRST_AFUI_FAILURE')
    fields(latest['source'],dict(head=HEAD,tree=TREE,actual_Native_cases=0),'CAPABILITY_EXACT_SUCCESSOR_SOURCE')
    fields(latest,dict(status='ACTUAL_SUPABASE17_SCHEMA_CAPABILITIES_REPORTED_NOT_ERP',
        retained_Mandor_and_Global_NOT_rerun=True,all_three_fresh_one_attempt=False,
        global_catalog_capability_unsupported=True,all_runtime_capabilities_available=False,
        actual_ERP_cases=0,actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,
        production_go=False,independent_acceptance=False),'CAPABILITY_CLOSED_NONFINANCIAL_LIMITS')
    exact(set(latest['results']),{'AFUI'},'CAPABILITY_ONLY_AFUI_FRESH')
    retained=strict(g.read(NS+'RETAINED_MANDOR_AND_CATALOG_OBSERVATIONS.json'))
    exact(latest['retained_observations'],retained,'CAPABILITY_EXACT_RETAINED_SOURCE_RECEIPT')
    exact(retained['results'],{n:first['results'][n]for n in('MANDOR','GLOBAL_CATALOG_AUTHORITY')},'CAPABILITY_RETAINED_ORIGINAL_VALUES_NOT_SYNTHETIC')
    exact(retained['original_report'],first_pin,'CAPABILITY_EXACT_ORIGINAL_RETAINED_REPORT_BYTES')
    mandor=retained['results']['MANDOR'];catalog=retained['results']['GLOBAL_CATALOG_AUTHORITY']
    fields(mandor,dict(status='ACTUAL_SUPABASE17_MANDOR_NINE_FUNCTION_AUTHORITY_AND_PREUSE_ALL22_PASS_NOT_ERP',
        creator=['postgres','postgres',False,True,170006],capability_DB_removed=True,
        global_roles_and_memberships_restored=True,all_synthetic_DDL_rolled_back=True,actual_Native_cases=0),'CAPABILITY_ACTUAL17_MANDOR_RETAINED')
    fields(catalog,dict(status='ACTUAL_SUPABASE17_CATALOG_CAPABILITY_UNAVAILABLE_RUNTIME_MUST_REMAIN_CLOSED',
        creator=['postgres','postgres',False,170006],SQLSTATE='42501',catalogue_count=64,
        all_catalogue_SHARE_locks_observed=False,transaction_rolled_back=True,
        global_runtime_installed=False,global_writer_closure=False),'CAPABILITY_GLOBAL_PRIVILEGE_REFUSAL_PRESERVED')
    afui=latest['results']['AFUI']
    fields(afui,dict(status='ACTUAL_POSTGRES17_NON_SUPERUSER_SIX_FUNCTION_ACL_CAPABILITY_PASS_NOT_ERP',
        actual_creator_profile=['postgres','postgres',False,True,'supabase_admin',170006],
        exact_all22_transition=True,exact_six_bodies_and_role_exposure=True,
        exact_preuse_all22_restored=True,raw_public_schema_restored=True,
        actual_default_function_privileges_unchanged=True,all_synthetic_DDL_rolled_back=True,
        capability_DB_removed=True,global_roles_and_memberships_restored=True,actual_ERP_Native_cases=0),'CAPABILITY_ACTUAL17_AFUI_FRESH')
    for name,value in afui['source_sha256'].items():exact(pin(g.read('scripts/cp7_accessory_nonpayable/'+name))['sha256'],value,'CAPABILITY_AFUI_ACTUAL_SOURCE:'+name)
    expected=[]
    for signature in('cp7_accessory_nonpayable.settings_access_v1(boolean)','cp7_accessory_nonpayable.settings_event_v1(uuid)',
        'cp7_accessory_nonpayable.settings_save_v1(jsonb,uuid,boolean)','cp7_accessory_nonpayable.settings_workspace_v1(jsonb)',
        'public.erp_cp7_get_good_policy_dates_v1(jsonb)','public.erp_cp7_save_good_policy_date_v1(jsonb,uuid,boolean)'):
        raw=('{cp7_good_policy_date=X/cp7_good_policy_date,authenticated=X/cp7_good_policy_date}'if signature.startswith('public.')
            else'{postgres=X/postgres,cp7_good_policy_date=X/postgres}'if '.settings_save_'in signature or'.settings_workspace_'in signature
            else'{postgres=X/postgres}')
        expected.append([signature,raw])
    exact(afui['actual_six_function_ACLs'],expected,'CAPABILITY_SIX_RAW_ACTUAL_FUNCTION_ACLS_INDEPENDENTLY_MATCHED')
    return dict(status='ROOT_VERIFIED_ACTUAL_SUPABASE17_AFUI_FRESH_MANDOR_RETAINED_AND_UNSUPPORTED_GLOBAL_CAPABILITY_NOT_ERP',
        head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,first_failed_run_id=41437248634,first_failed_job_id=125250039172,
        source=proof,first_archive=FIRST,successor_archive=SUCCESS,first_original_report=first_pin,successor_original_report=latest_pin,
        actual_PostgreSQL_version_num=170006,Afui_schema_capability=True,Mandor_schema_capability=True,
        fresh_Afui_observation=1,retained_Mandor_observation=1,retained_global_permission_refusal=1,
        original_first_failure_preserved=True,raw_six_Afui_ACLs_independently_matched=True,
        raw_all22_capability_censuses_not_retained_or_independently_recomputed=True,
        capability_reports_are_source_bound_runtime_assertions_not_financial_cases=True,
        global_catalog_barrier_available_to_postgres=False,global_writer_or_permission_or_phantom_closure=False,
        full_Afui15_or_Mandor_Native_business_acceptance=False,actual_Native_cases=0,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--first',type=Path,required=True)
    p.add_argument('--successor',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    with GitBytes(a.source,HEAD,TREE)as g:result=intake(g,a.first,a.successor)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],actual_Native_cases=0)))
