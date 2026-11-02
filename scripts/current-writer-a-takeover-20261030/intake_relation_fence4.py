"""Read actual17 originals: retained install1 and remaining relation controls3.

No database, network, ERP callback or old capability test runs here. Recompute
raw metadata transitions and observations without relabelling model capability
as actual ERP installation, source-input closure or business qualification.
"""
from pathlib import Path,PurePosixPath
import argparse,json,re,stat,zipfile
from intake_common import GitBytes,exact,fields,pin,require
from intake_sku27 import strict
from intake_catalog_fence4 import acl_set

HEAD='26568709f946c1875c2f22f600a9167bb091dbe0'
TREE='f23bb5f0f8e1c17d84820d0c53dd4e45d3977c6b'
RUN=41450281470
JOB=125293494362
FIRST_HEAD='358626fcc7be18041bda524d7f978b18129d1367'
FIRST_TREE='a497a9331aa32775c75e5df48a7f0e97de3e8b85'
BASE_TREE='af091b98196f984da562270d83a2301a06db18d9'
NS='scripts/current-global-relation-bridge-capability/'
WF='.github/workflows/cp7-global-relation-bridge-capability.yml'
SIG='cp7_global_catalog_fence.lock_relations_v1(text)'
FIRST_ARCHIVE=dict(bytes=26994,sha256='751c7504790b99c592778e1498cd574fa456155003bd5697c310acf67d21ca50')
ARCHIVE=dict(bytes=36891,sha256='31479ba31bb1da800cc33dbd3633b06724c004cefa1e6c8ba2f151f29f26cd7b')
FIRST_IDS=['EXACT_ONE_NEW_PRIVATE_RELATION_FUNCTION_NO_BROAD_DATA_OR_CATALOG_GRANTS']
FRESH_IDS=['ACTUAL_NON_SUPERUSER_RETAINS_43_DECLARED_LOCKS_AND_CALLS_OWNER_WRITER_WITHOUT_DIRECT_DML',
 'PROFILE_FENCE_DUPLICATE_CHANGED_AUTHORITY_AND_SECOND_BACKEND_REFUSALS',
 'DROP_ONLY_NEW_FUNCTION_RESTORES_ALL22_PUBLIC_AND_RETAINED_CATALOG_HELPER']


def source(g):
    base=g.entries(BASE_TREE)
    for n,v in base.items():exact(g.tree.get(n),v,'RELATION_ENTIRE_PARENT_UNCHANGED:'+n)
    own={NS+n for n in('probe.py','BASE_FENCE.sql','RELATION_FENCE.sql','PROFILE_SCHEMA.sql','INVERSE.sql',
        'SOURCE_PROOF.json','RETAINED_FIRST_CONTROL.json','SOURCE.json')}|{WF}
    exact(set(g.tree)-set(base),own,'RELATION_EXACT_NINE_OWN_PATHS')
    manifest=strict(g.read(NS+'SOURCE.json'))
    fields(manifest,dict(classification='SEALED_PROFILE_RELATION_FENCE_ACTUAL17_MODEL_CAPABILITY_ONLY',
        exact_new_control_families=3,retained_control_families=1,all_four_are_NOT_fresh_in_one_attempt=True,
        actual_ERP_parent_installation=False,actual_Native_cases=0,production_go=False,independent_acceptance=False),
        'RELATION_SOURCE_CLOSED_SCOPE')
    required=(own-{NS+'SOURCE.json'})|{'scripts/current-global-catalog-bridge-capability/probe.py',
        'scripts/cp7_ow04_restore_bundle.py','scripts/current-finance-combined-composition/disposable_start.py'}
    exact(set(manifest['files']),required,'RELATION_ELEVEN_EXACT_SOURCE_PINS')
    for n,v in manifest['files'].items():g.verify_pin(n,v)
    for n in('BASE_FENCE.sql','RELATION_FENCE.sql','PROFILE_SCHEMA.sql','INVERSE.sql','SOURCE_PROOF.json'):
        exact(g.read(NS+n),g.read(NS+n,FIRST_HEAD),'RELATION_FIRST_ACTUAL_SOURCE_RETAINED_EXACT:'+n)
    sql=g.read(NS+'RELATION_FENCE.sql').decode()
    exact(re.findall(r'^create function ([a-z0-9_.]+)\(([^)]*)\)',sql,re.M),
        [('cp7_global_catalog_fence.lock_relations_v1','p_profile text')],'RELATION_ONLY_ONE_PROFILE_ARGUMENT_HELPER')
    for part in("expected_relations into targets_",'CP7_GLOBAL_COMPLETE_CATALOG_FENCE_REQUIRED_FIRST',
        'CP7_GLOBAL_PREEXISTING_TRANSACTION_REVIEW_AGAIN','exclusive mode nowait',
        'CP7_GLOBAL_FINAL_RELATION_PROFILE_CHANGED'):
        require(part in sql,'RELATION_REQUIRED_BOUNDARY_SOURCE:'+part)
    inverse=g.read(NS+'INVERSE.sql').decode()
    require('drop function '+SIG+';'in inverse and'cascade'not in inverse.lower()and'drop owned'not in inverse.lower(),
        'RELATION_DROP_ONLY_NEW_FUNCTION')
    return dict(source_pins=11,new_paths=9,unchanged_parent_paths=len(base),
        model_tables=42,new_product_roles=0,actual_ERP_imports=0,actual_SQL_executed=0)


def report(path,expected):
    exact(pin(path.read_bytes()),expected,'RELATION_COMPLETE_ORIGINAL_ARCHIVE_PIN')
    with zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(names),len(set(names)),'RELATION_NO_DUPLICATE_MEMBERS')
        for name in names:
            p=PurePosixPath(name)
            require(not p.is_absolute()and'..'not in p.parts and'\\'not in name,'RELATION_SAFE_MEMBER')
            require(stat.S_IFMT(z.getinfo(name).external_attr>>16)in(0,stat.S_IFDIR,stat.S_IFREG),'RELATION_NO_SPECIAL_MEMBER')
        require(z.testzip()is None,'RELATION_ALL_CANONICAL_CRCS_VALID')
        chosen=[n for n in names if n.endswith('PLATFORM_RELATION_FENCE_NEW4.json')]
        exact(len(chosen),1,'RELATION_ONE_RAW_OWNING_REPORT');raw=z.read(chosen[0])
    return strict(raw),dict(member=chosen[0],**pin(raw))


def transition(raw):
    before=raw['baseline_all22'];after=raw['installed_all22']
    exact(len(before),22,'RELATION_ALL22_PRESENT');exact(set(before),set(after),'RELATION_NO_GROUP_OMITTED')
    for group,rows in before.items():
        exact(set(after[group])-set(rows),{SIG}if group=='functions'else set(),'RELATION_ONLY_ONE_CATALOG_ADDITION:'+group)
        for n,v in rows.items():exact(after[group].get(n),v,'RELATION_EVERY_EXISTING_CATALOG_VALUE_UNCHANGED:'+group+':'+n)


def intake(g,first_path,path):
    admitted=source(g);first,first_pin=report(first_path,FIRST_ARCHIVE);r,report_pin=report(path,ARCHIVE)
    fields(first,dict(status='INCOMPLETE',capability_DB_removed=True,global_roles_and_memberships_restored=True,
        actual_Native_cases=0),'RELATION_FIRST_FAILED_ORIGINAL_LIMITS')
    fields(first['source'],dict(head=FIRST_HEAD,tree=FIRST_TREE,source_pins=10),'RELATION_FIRST_OWNING_SOURCE')
    exact(first['checks'],[dict(id=n,status='PASS')for n in FIRST_IDS],'RELATION_FIRST_EXACT_RETAINED_CONTROL')
    require('unterminated quoted identifier'in first['error'],'RELATION_ORIGINAL_OBSERVATION_QUERY_FAILURE_PRESERVED')
    transition(first['raw']);retained=strict(g.read(NS+'RETAINED_FIRST_CONTROL.json'))
    exact(retained['original_report'],{k:v for k,v in first_pin.items()if k!='member'},'RELATION_RETAIN_EXACT_ORIGINAL_REPORT')
    exact(retained['checks'],first['checks'],'RELATION_EXACT_RETAINED_CHECKS')
    fields(r,dict(status='ACTUAL_SUPABASE17_SEALED_PROFILE_RELATION_FENCE_RETAIN1_FRESH3_PASS_NOT_GLOBAL_RUNTIME',
        retained_control_families=1,first_attempt_remains_failure=True,all_four_are_NOT_fresh_in_one_attempt=True,
        model_profile_is_NOT_accepted_final_ERP_parent=True,all_42_application_tables_are_models=True,
        actual_global_installer_or_parent_adoption=False,global_writer_or_permission_or_phantom_closure=False,
        actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,capability_DB_removed=True,
        global_roles_and_memberships_restored=True,production_go=False,independent_acceptance=False),'RELATION_SUCCESSOR_LIMITS')
    fields(r['source'],dict(head=HEAD,tree=TREE,source_pins=11),'RELATION_SUCCESSOR_EXACT_SOURCE')
    exact(r['checks'],[dict(id=n,status='PASS')for n in FRESH_IDS],'RELATION_EXACT_THREE_NEW_CONTROL_FAMILIES')
    exact(r['retained_first_control'],retained,'RELATION_SUCCESSOR_RETAINS_SOURCE_BOUND_ORIGINAL')
    transition(r['raw']);raw=r['raw'];after=raw['installed_all22']
    exact(raw['final_all22'],raw['baseline_all22'],'RELATION_ENTIRE_RAW22_AFTER_INVERSE_EQUAL')
    function=after['functions'][SIG];exact(len(function),19,'RELATION_COMPLETE19_ACTUAL_ATTRIBUTES')
    exact(function[1:5],['supabase_admin','plpgsql','f',True],'RELATION_OWNER_LANGUAGE_KIND_AND_DEFINER')
    exact(function[8],'v','RELATION_VOLATILE');exact(set(function[12]),{'search_path=""','TimeZone=UTC'},'RELATION_FIXED_CONFIG')
    sql=g.read(NS+'RELATION_FENCE.sql').decode();body=re.search(r'create function cp7_global_catalog_fence\.lock_relations_v1\(p_profile text\).*?as \$\$(.*?)\$\$;',sql,re.S)
    require(body is not None and body[1]in function[0],'RELATION_ACTUAL19_DEFINITION_EXACT_SOURCE_BODY')
    exact(first['raw']['function_definition_body'],body[1],'RELATION_RETAINED_RAW_SOURCE_BODY')
    exact(acl_set(first['raw']['function_raw_ACL']),{'supabase_admin=X/supabase_admin','postgres=X/supabase_admin'},'RELATION_EXACT_RAW_FUNCTION_ACL')
    exact(acl_set(first['raw']['schema_raw_ACL']),{'supabase_admin=UC/supabase_admin','postgres=U/supabase_admin'},'RELATION_EXACT_RAW_PRIVATE_SCHEMA_ACL')
    exact({tuple(v)for v in function[18]},{('postgres','supabase_admin','EXECUTE',False),('supabase_admin','supabase_admin','EXECUTE',False)},'RELATION_CURRENT_EXPANDED_EXECUTE')
    exact(raw['actual_non_superuser_profile'],['postgres','postgres',False,170006],'RELATION_REAL_AUTHENTICATED_NONSUPERUSER_SESSION')
    targets=raw['actual_model_targets'];exact(len(targets),42,'RELATION_EXACT42_MODEL_TABLES')
    require(all(len(v)==8 and v[0]=='cp7_relation_modeldata'and v[2]=='r'and v[4]=='cp7_relation_model_owner'for v in targets),
        'RELATION_ONLY_DECLARED_OTHER_OWNER_MODEL_TARGETS')
    exact(raw['actual_returned_relations'],targets,'RELATION_FRESH_ACTUAL_RETURNED_TARGETS_EQUAL')
    expected=[['cp7_global_nonpo_envelope','profiles','ExclusiveLock',True]]+[v[:2]+['ExclusiveLock',True]for v in targets]
    exact(raw['actual_held_application_locks'],expected,'RELATION_ACTUAL43_LOCK_IDENTITIES_AND_MODES')
    for n in('direct_lock_denial','direct_DML_denial'):exact(raw[n]['SQLSTATE'],'42501','RELATION_NO_DIRECT_PRIVILEGE:'+n)
    refusals=raw['new_relation_refusals'];expected_cases={
        'missing_catalog_fence':('P0001','CP7_GLOBAL_COMPLETE_CATALOG_FENCE_REQUIRED_FIRST'),
        'preexisting_permanent_XID':('55P03','CP7_GLOBAL_PREEXISTING_TRANSACTION_REVIEW_AGAIN'),
        'wrong_profile':('P0001','CP7_GLOBAL_COMPLETE_EXACT_RELATION_PROFILE_REQUIRED'),
        'second_profile':('P0001','CP7_GLOBAL_ONE_ACTUAL_FINAL_PARENT_PROFILE_REQUIRED'),
        'changed_target_ACL':('P0001','CP7_GLOBAL_RELATION_IDENTITY_OR_AUTHORITY_CHANGED'),
        'other_backend_owner_writer':('55P03','canceling statement due to lock timeout')}
    exact({v['case']:(v['SQLSTATE'],v['error'])for v in refusals},expected_cases,'RELATION_EXACT_SIX_NEW_BOUNDARY_OBSERVATIONS')
    denials=raw['actual_new_function_external_role_denials']
    exact({v['role']for v in denials},{'anon','authenticated','service_role'},'RELATION_ALL_THREE_EXTERNAL_ROLES')
    require(len(denials)==3 and all(v['SQLSTATE']=='42501'for v in denials),'RELATION_EXTERNAL_CALLS_REFUSED')
    return dict(status='ROOT_VERIFIED_ACTUAL17_RELATION_CAPABILITY_RETAIN1_FRESH3_NOT_GLOBAL_RUNTIME',
        head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,source=admitted,first_archive=FIRST_ARCHIVE,archive=ARCHIVE,
        first_original_report=first_pin,original_report=report_pin,retained_controls=1,new_controls=3,coverage=4,
        first_attempt_remains_failure=True,all_four_are_NOT_fresh_one_attempt=True,actual_PostgreSQL=170006,
        original_raw22_transitions_and_final_equality_independently_recomputed=True,
        raw_function_and_schema_ACLs_and_actual43_locks_independently_matched=True,
        relation_capability_for_other_owner_tables_observed=True,direct_postgres_DML_privileges_expanded=False,
        capability_DB_removed=True,global_roles_and_memberships_restored=True,
        modeled_owner_writer_and_rollback_are_source_bound_assertions_NOT_financial_inverse=True,
        actual_global_installer_or_parent_adoption=False,actual_Native_cases=0,
        global_writer_or_permission_or_phantom_closure=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--first-archive',type=Path,required=True)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    with GitBytes(a.source,HEAD,TREE)as g:v=intake(g,a.first_archive,a.archive)
    a.output.write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(dict(status=v['status'],actual_Native_cases=0)))
