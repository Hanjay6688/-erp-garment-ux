"""Independently compare raw22 and lock/ACL originals for the new fixed helper.

This capability proves no Global business, writer, input or phantom closure.
No ERP module, SQL client, network or financial callback is imported/executed.
"""
from pathlib import Path,PurePosixPath
from hashlib import sha256
import argparse,json,re,stat,zipfile
from intake_common import GitBytes,exact,fields,pin,require
from intake_sku27 import strict

HEAD='ca88d4a37936b24fd67a94deb79e8345091d9704'
TREE='af091b98196f984da562270d83a2301a06db18d9'
RUN=41441132562
JOB=125263004143
BASE_TREE='4fc70e1da0bc0ae1ca72f0b00fbca2d7001ca00c'
NS='scripts/current-global-catalog-bridge-capability/'
WF='.github/workflows/cp7-global-catalog-bridge-capability.yml'
SIG='cp7_global_catalog_fence.lock_v1()'
ARCHIVE=dict(bytes=12275,sha256='c4ac07353e64cd58f9af2ce03e70127cd5ff3fd35f6b8c65852d5b4a4874dbc2')
IDS=['DECLARED_PLATFORM_BOOTSTRAP_ADDS_ONLY_ONE_PRIVATE_SCHEMA_AND_EXACT_ZERO_ARGUMENT_FUNCTION',
 'ACTUAL_POSTGRES_CALL_RETURNS_TO_NON_SUPERUSER_WITH_ALL64_TRANSACTION_LOCKS_AND_ORDINARY_DML',
 'ANON_AUTHENTICATED_AND_SERVICE_HAVE_NO_SCHEMA_OR_FUNCTION_ACCESS_AND_ACTUAL_CALLS_REFUSE',
 'EXPLICIT_NARROW_PLATFORM_REMOVAL_RESTORES_ALL22_RAW_PUBLIC_AND_ROLE_CONTEXT']


def source(g):
    base=g.entries(BASE_TREE)
    for name,value in base.items():exact(g.tree.get(name),value,'FENCE4_ENTIRE_CAPABILITY_PARENT_UNCHANGED:'+name)
    own={NS+n for n in('probe.py','FENCE.sql','INVERSE.sql','BRIDGE_SOURCE_PROOF.json','SOURCE.json')}|{WF}
    exact(set(g.tree)-set(base),own,'FENCE4_EXACT_SIX_ADDITIVE_CAPSULE_PATHS')
    manifest=strict(g.read(NS+'SOURCE.json'))
    fields(manifest,dict(classification='FIXED_PLATFORM_CATALOG_FENCE_ACTUAL17_CAPABILITY_ONLY_NOT_GLOBAL_RUNTIME',
        exact_new_controls=4,old_Afui_Mandor_catalog_and_relation_controls_NOT_rerun=True,
        actual_global_parent_or_financial_qualification=False,actual_Native_cases=0,
        production_go=False,independent_acceptance=False),'FENCE4_CLOSED_SCOPE')
    required=(own-{NS+'SOURCE.json'})|{'scripts/cp7_ow04_restore_bundle.py',
        'scripts/current-finance-combined-composition/disposable_start.py'}
    exact(set(manifest['files']),required,'FENCE4_EXACT_SEVEN_PINNED_INPUTS')
    for name,value in manifest['files'].items():g.verify_pin(name,value)
    proof=strict(g.read(NS+'BRIDGE_SOURCE_PROOF.json'))
    exact(proof['platform_source'],pin(g.read(NS+'FENCE.sql')),'FENCE4_EXACT_PREPARED_PLATFORM_SOURCE')
    fields(proof,dict(platform_helper=SIG,platform_helper_owner='supabase_admin',allowed_external_invoker='postgres',
        new_roles=0,new_browser_or_service_grants=0,postgres_catalog_DML_or_MAINTAIN_grants=0,
        actual_SQL_executed=0,actual_Native_cases=0),'FENCE4_NARROW_CAPABILITY_SOURCE')
    sql=g.read(NS+'FENCE.sql').decode()
    exact(re.findall(r'^create function ([a-z0-9_.]+)\(([^)]*)\)',sql,re.M),[('cp7_global_catalog_fence.lock_v1','')],'FENCE4_ONE_ZERO_ARGUMENT_HELPER')
    require("execute format('lock table pg_catalog.%I in share mode nowait',entry_->>1)"in sql,'FENCE4_FIXED_SYSTEM_CATALOG_SCHEMA')
    require('create role 'not in sql and'grant maintain'not in sql and'grant update'not in sql,'FENCE4_NO_BROAD_PRIVILEGES')
    inverse=g.read(NS+'INVERSE.sql').decode();require('cascade'not in inverse.lower()and'drop owned'not in inverse.lower(),'FENCE4_NARROW_INVERSE')
    return dict(status='ROOT_FIXED_PLATFORM_FENCE_SOURCE_ONLY',source_pins=7,new_paths=6,
        unchanged_parent_paths=len(base),private_platform_owner='supabase_admin',actual_ERP_imports=0,actual_SQL_executed=0)


def acl_set(text):
    require(type(text)is str and text.startswith('{')and text.endswith('}'),'FENCE4_EXPLICIT_RAW_ACL_REQUIRED')
    return set(text[1:-1].split(','))


def intake(g,path):
    admitted=source(g);exact(pin(path.read_bytes()),ARCHIVE,'FENCE4_COMPLETE_ORIGINAL_ARCHIVE_PIN')
    with zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(set(names)),len(names),'FENCE4_NO_DUPLICATE_MEMBERS')
        for n in names:
            p=PurePosixPath(n);require(not p.is_absolute()and'..'not in p.parts and'\\'not in n,'FENCE4_SAFE_MEMBER')
            require(stat.S_IFMT(z.getinfo(n).external_attr>>16)in(0,stat.S_IFDIR,stat.S_IFREG),'FENCE4_NO_SPECIAL_MEMBER')
        require(z.testzip()is None,'FENCE4_ALL_CANONICAL_CRCS_VALID')
        selected=[n for n in names if n.endswith('PLATFORM_CATALOG_FENCE_FOCUSED4.json')]
        exact(len(selected),1,'FENCE4_ONE_ORIGINAL_REPORT');report_raw=z.read(selected[0]);report=strict(report_raw)
    fields(report,dict(status='ACTUAL_SUPABASE17_FIXED_PLATFORM_CATALOG_FENCE_FOCUSED4_PASS_NOT_GLOBAL_RUNTIME',
        all_base_tables_are_models=True,new_privileged_function_is_actual_fixed_prepared_source=True,
        old_completed_capability_and_catalog_and_relation_controls_NOT_rerun=True,
        actual_global_installer_or_parent_adoption=False,global_writer_or_permission_or_phantom_closure=False,
        actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,capability_DB_removed=True,
        global_roles_and_memberships_restored=True,production_go=False,independent_acceptance=False),'FENCE4_ACTUAL_REPORT_LIMITS')
    fields(report['source'],dict(head=HEAD,tree=TREE,source_pins=7,actual_Native_cases=0),'FENCE4_EXACT_OWNING_SOURCE')
    exact(report['checks'],[dict(id=n,status='PASS')for n in IDS],'FENCE4_EXACT_FOUR_NEW_CONTROLS')
    before=report['raw']['baseline_all22'];after=report['raw']['installed_all22'];final=report['raw']['final_all22']
    exact(len(before),22,'FENCE4_ALL22_PRESENT');exact(set(after),set(before),'FENCE4_NO_CATALOG_GROUP_OMITTED')
    for group,rows in before.items():
        added={'cp7_global_catalog_fence'}if group=='schemas'else{SIG}if group=='functions'else set()
        exact(set(after[group])-set(rows),added,'FENCE4_ONLY_DECLARED_CATALOG_ADDITIONS:'+group)
        for name,value in rows.items():exact(after[group].get(name),value,'FENCE4_EVERY_EXISTING_CATALOG_VALUE_UNCHANGED:'+group+':'+name)
    exact(final,before,'FENCE4_ENTIRE_RAW_ALL22_AFTER_INVERSE_EQUALS_ORIGINAL')
    function=after['functions'][SIG];exact(len(function),19,'FENCE4_ALL19_FUNCTION_ATTRIBUTES_PRESENT')
    exact(function[1],'supabase_admin','FENCE4_ACTUAL_PLATFORM_OWNER');exact(function[2],'plpgsql','FENCE4_ACTUAL_PLPGSQL')
    exact(function[4],True,'FENCE4_ACTUAL_SECURITY_DEFINER');exact(function[8],'v','FENCE4_ACTUAL_VOLATILE')
    exact(set(function[12]),{'search_path=""','TimeZone=UTC'},'FENCE4_FIXED_SEARCH_PATH_AND_ZONE')
    sql=g.read(NS+'FENCE.sql').decode();body=re.search(r'create function cp7_global_catalog_fence\.lock_v1\(\).*?as \$\$(.*?)\$\$;',sql,re.S)
    require(body is not None,'FENCE4_PINNED_SOURCE_BODY_REQUIRED')
    exact(report['raw']['function_definition_body'],body[1],'FENCE4_ACTUAL_EXACT_SOURCE_BODY')
    require(body[1]in function[0],'FENCE4_RAW19_DEFINITION_CONTAINS_EXACT_SOURCE_BODY')
    exact(acl_set(report['raw']['function_raw_ACL']),{'supabase_admin=X/supabase_admin','postgres=X/supabase_admin'},'FENCE4_EXACT_RAW_FUNCTION_OWNER_AND_ONLY_POSTGRES_EXECUTE')
    exact(acl_set(report['raw']['schema_raw_ACL']),{'supabase_admin=UC/supabase_admin','postgres=U/supabase_admin'},'FENCE4_EXACT_RAW_PRIVATE_SCHEMA_USAGE')
    exact({tuple(x)for x in function[18]},{('postgres','supabase_admin','EXECUTE',False),('supabase_admin','supabase_admin','EXECUTE',False)},'FENCE4_RAW_AND_EXPANDED_EXECUTE_AGREE')
    raw=report['raw'];exact(raw['actual_non_superuser_profile'],['postgres','postgres',False,170006],'FENCE4_REAL_POSTGRES_SESSION_NOT_ADMIN_SET_ROLE')
    catalogs=raw['returned_catalogues'];held=raw['actual_held_locks'];exact(len(catalogs),64,'FENCE4_ACTUAL_COMPLETE64_CATALOGS')
    exact(len({tuple(r[:2])for r in catalogs}),64,'FENCE4_DISTINCT_CATALOG_IDENTITIES')
    require(all(type(r)is list and len(r)==8 and r[0]=='pg_catalog'and r[2]in('r','p')for r in catalogs),'FENCE4_TYPED_CATALOG_RELATIONS_ONLY')
    exact([r[:2]for r in held],[r[:2]for r in catalogs],'FENCE4_EXACT_SAME_RETURNED_AND_ACTUALLY_HELD_IDENTITIES')
    require(all(r[2:]==['ShareLock',True]for r in held),'FENCE4_ALL64_GRANTED_SHARE_LOCKS_REMAIN_AFTER_DEFINER_RETURN')
    required={'pg_class','pg_namespace','pg_proc','pg_aggregate','pg_authid','pg_auth_members','pg_cast','pg_operator','pg_type','pg_policy','pg_trigger','pg_event_trigger'}
    require(required<={r[1]for r in catalogs},'FENCE4_AUTHORITY_AND_DISPATCH_CATALOGS_NOT_OMITTED')
    denials=raw['actual_external_role_denials'];exact({r['role']for r in denials},{'anon','authenticated','service_role'},'FENCE4_EXACT_THREE_STANDARD_EXTERNAL_ROLES')
    require(len(denials)==3 and all(r['SQLSTATE']=='42501'for r in denials),'FENCE4_ACTUAL_ROLE_CALLS_DENIED')
    return dict(status='ROOT_VERIFIED_ACTUAL_SUPABASE17_FIXED_CATALOG_FENCE4_RAW22_ACL_AND_LOCKS_NOT_GLOBAL_RUNTIME',
        head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,source=admitted,archive=ARCHIVE,
        original_report=dict(member=selected[0],**pin(report_raw)),
        actual_PostgreSQL=170006,new_controls=4,raw_all22_transition_and_final_equality_independently_recomputed=True,
        raw_function_and_schema_ACLs_independently_matched=True,actual_all64_same_backend_transaction_locks_independently_matched=True,
        platform_capability_for_postgres_observed=True,postgres_direct_catalog_privileges_expanded=False,
        capability_DB_removed=True,global_roles_and_memberships_restored=True,
        model_row_rollback_is_source_bound_assertion_not_financial_inverse=True,
        actual_global_installer_or_parent_adoption=False,actual_Native_cases=0,
        global_writer_or_permission_or_phantom_closure=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    with GitBytes(a.source,HEAD,TREE)as g:v=intake(g,a.archive)
    a.output.write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(dict(status=v['status'],actual_Native_cases=0)))
