"""Independent original metadata intake for two model-only actual17 capabilities.

No SQL, ERP module, existing test, network client or business callback runs.
Read complete immutable public source and original archives; never promote
catalogue/owner capability to financial, Auth/browser or final-parent acceptance.
"""
from pathlib import Path,PurePosixPath
from hashlib import sha256
import argparse,json,re,stat,zipfile
from intake_common import GitBytes,exact,fields,pin,require
from intake_sku27 import strict

REPO='Hanjay6688/-erp-garment-ux'
FP_HEAD='6774e244eade7bf6c07fc97df1e44afea203a6b0'
FP_TREE='0cf377f091b4476b47c2bb601e27211e07cff891'
FP_BASE='f23bb5f0f8e1c17d84820d0c53dd4e45d3977c6b'
FP_NS='scripts/current-global-catalogue-profile-capability/'
FP_ARCHIVE=dict(bytes=288710,sha256='ca4b5cac21e16fcac0a257b3c3414a45e69f14d6b64712a57ad1b1754a4e357b')
FP_SIG='cp7_global_nonpo_envelope.catalogue_fingerprint_v1()'
M_HEAD='297dc4586d428a93f29e20dbcc04228731fc0d9d'
M_TREE='f96442bc60c5a219df969cfaa16ef9e5528e9079'
M_MODULE_HEAD='816f63735d4be2a882a78e01dfba4b284de429b3'
M_NS='scripts/current-mandor-install-plan-capability/'
MODULE='scripts/cp7_mandor_shop/'
M_ARCHIVE=dict(bytes=195632,sha256='4359cd01117fa12e635fe9ae63b1fd63804dd853ec68488ed115f06fd82a2602')


def original(path,expected,suffix):
    exact(pin(path.read_bytes()),expected,'MODELS_COMPLETE_ORIGINAL_ARCHIVE_PIN')
    with zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(names),len(set(names)),'MODELS_NO_DUPLICATE_MEMBERS')
        for name in names:
            p=PurePosixPath(name);require(not p.is_absolute()and'..'not in p.parts and'\\'not in name,'MODELS_SAFE_MEMBER')
            require(stat.S_IFMT(z.getinfo(name).external_attr>>16)in(0,stat.S_IFDIR,stat.S_IFREG),'MODELS_NO_SPECIAL_MEMBER')
        require(z.testzip()is None,'MODELS_CANONICAL_CRC_FAILURE')
        chosen=[n for n in names if n.endswith(suffix)];exact(len(chosen),1,'MODELS_ONE_OWNING_REPORT')
        raw=z.read(chosen[0])
    return strict(raw),dict(member=chosen[0],**pin(raw))


def source(g,ns,base,own):
    previous=g.entries(base)
    for n,v in previous.items():exact(g.tree.get(n),v,'MODELS_ENTIRE_PARENT_UNCHANGED:'+n)
    exact(set(g.tree)-set(previous),own,'MODELS_EXACT_ADDITIVE_PATH_SET')
    m=strict(g.read(ns+'SOURCE.json'))
    for n,v in m['files'].items():g.verify_pin(n,v)
    return m,dict(source_pins=len(m['files']),new_paths=len(own),unchanged_parent_paths=len(previous))


def observed25(value):
    rows=value['catalogues'];exact(len(rows),25,'FIXED25_COMPLETE_GROUPS')
    text=value['canonical_DB_jsonb_preimage'];exact(strict(text.encode()),rows,'FIXED25_ORIGINAL_DB_PREIMAGE_EQUALS_RAW25')
    expected=dict(contract='cp7.global-catalogue-fingerprint.v1',groups=25,
        sha256=sha256(text.encode()).hexdigest(),counts={n:len(v)for n,v in rows.items()})
    exact(value['helper_fingerprint'],expected,'FIXED25_SHA256_AND_COUNTS_RECOMPUTED')
    return expected


def fixed25(g,path):
    own={FP_NS+n for n in('probe.py','FINGERPRINT.sql','QUERIES25.json','SOURCE_PROOF.json','INVERSE.sql','SOURCE.json')}
    own.add('.github/workflows/cp7-global-catalogue-profile-capability.yml')
    m,s=source(g,FP_NS,FP_BASE,own);exact(s['source_pins'],9,'FIXED25_EXACT9_SOURCE_PINS')
    exact(set(m['files']),own-{FP_NS+'SOURCE.json'}|{'scripts/current-global-catalog-bridge-capability/probe.py',
        'scripts/cp7_ow04_restore_bundle.py','scripts/current-finance-combined-composition/disposable_start.py'},'FIXED25_DECLARED_PIN_SET')
    proof=strict(g.read(FP_NS+'SOURCE_PROOF.json'));queries=strict(g.read(FP_NS+'QUERIES25.json'))
    exact(proof['generated_source'],pin(g.read(FP_NS+'FINGERPRINT.sql')),'FIXED25_EXACT_GENERATED_SOURCE')
    exact(set(queries),set(proof['query_pins']),'FIXED25_ALL_FIXED_QUERY_INPUTS')
    for n,q in queries.items():exact(pin(q.encode()),proof['query_pins'][n],'FIXED25_QUERY_PIN:'+n)
    r,raw=original(path,FP_ARCHIVE,'CATALOGUE_FINGERPRINT_NEW3.json')
    fields(r,dict(status='ACTUAL_SUPABASE17_FIXED25_CATALOGUE_FINGERPRINT_NEW3_PASS_NOT_GLOBAL_RUNTIME',
        all_application_objects_are_models=True,actual_global_installer_or_parent_adoption=False,
        global_writer_or_permission_or_phantom_closure=False,actual_Native_cases=0,actual_Auth_HTTP_cases=0,
        actual_browser_cases=0,capability_DB_removed=True,global_roles_and_memberships_restored=True,
        production_go=False,independent_acceptance=False),'FIXED25_REPORT_SCOPE')
    fields(r['source'],dict(head=FP_HEAD,tree=FP_TREE,source_pins=9),'FIXED25_OWNING_SOURCE')
    ids=['FIXED25_EXACT_SOURCE_PRIVATE_STABLE_HELPER_MATCHES_INDEPENDENT_QUERY_PREIMAGE',
        'MODEL_ROW_AND_NEXTVAL_LEAVE_ALL25_FINGERPRINT_UNCHANGED_SEQUENCE_EXPLICITLY_RESET',
        'OPERATOR_CAST_LANGUAGE_CHANGES_EACH_DETECTED_AND_NARROW_INVERSES_RESTORE_ALL25']
    exact(r['checks'],[dict(id=n,status='PASS')for n in ids],'FIXED25_EXACT3_NEW_CASES')
    v=r['raw'];before=v['baseline_catalogues'];installed=v['installed'];after=installed['catalogues'];basehash=observed25(installed)
    for group,rows in before.items():
        old,new=dict(rows),dict(after[group]);exact(len(old),len(rows),'FIXED25_NO_OLD_KEY_COLLISION')
        exact(len(new),len(after[group]),'FIXED25_NO_NEW_KEY_COLLISION')
        exact(set(new)-set(old),{FP_SIG}if group=='functions'else set(),'FIXED25_ONLY_DECLARED_HELPER_ADDED:'+group)
        for n,value in old.items():exact(new.get(n),value,'FIXED25_EXISTING_METADATA_PRESERVED:'+group+':'+n)
    fn=dict(after['functions'])[FP_SIG];exact(len(fn),19,'FIXED25_COMPLETE19')
    exact(fn[1:5],['postgres','sql','f',True],'FIXED25_OWNER_LANGUAGE_DEFINER');exact(fn[8],'s','FIXED25_STABLE')
    exact(set(fn[12]),{'search_path=""','TimeZone=UTC'},'FIXED25_CONFIG')
    exact({tuple(x)for x in fn[18]},{('postgres','postgres','EXECUTE',False)},'FIXED25_OWNER_ONLY_EXECUTE')
    exact(v['function_raw_ACL'],'{postgres=X/postgres}','FIXED25_RAW_ACL')
    body=re.search(r'as \$catalogue\$(.*?)\$catalogue\$;',g.read(FP_NS+'FINGERPRINT.sql').decode(),re.S)
    require(body is not None and body[1]in fn[0],'FIXED25_ACTUAL_SOURCE_BODY')
    exact(v['actual_non_superuser_profile'],['postgres','postgres',False,170006],'FIXED25_REAL_SESSION')
    observed25(v['after_model_data_and_nextval']);exact(v['after_model_data_and_nextval'],installed,'FIXED25_DATA_SEQUENCE_POSITION_INVARIANCE')
    exact([x['group']for x in v['dispatch_mutations']],['operators','casts','languages'],'FIXED25_DISPATCH3')
    for change in v['dispatch_mutations']:
        changed=change['changed'];fp=observed25(changed);require(fp['sha256']!=basehash['sha256'],'FIXED25_CHANGED_DISPATCH_HASH')
        for group,rows in after.items():
            if group==change['group']:
                old,new=dict(rows),dict(changed['catalogues'][group]);exact(len(new)-len(old),1,'FIXED25_ONE_DISPATCH_ADDITION')
                for n,value in old.items():exact(new.get(n),value,'FIXED25_PREVIOUS_DISPATCH_PRESERVED')
            else:exact(changed['catalogues'][group],rows,'FIXED25_OTHER24_GROUPS_UNCHANGED')
        require(change['narrow_inverse_all25_equal']is True,'FIXED25_NARROW_INVERSE_ASSERTION')
    exact(v['final_catalogues'],before,'FIXED25_FULL_RAW_FINAL_EQUAL')
    return dict(status='ROOT_VERIFIED_ACTUAL17_FIXED25_CATALOGUE_NEW3_RAW_PREIMAGES_AND_METADATA_NOT_GLOBAL_RUNTIME',
        head=FP_HEAD,tree=FP_TREE,run_id=41453242844,job_id=125303395021,source=s,archive=FP_ARCHIVE,original_report=raw,
        new_controls=3,raw25_transition_preimages_SHA256_counts_and_final_independently_recomputed=True,
        data_and_sequence_restore_and_environment_cleanup_are_source_bound_NOT_financial_inverse=True,
        actual_Native_cases=0,actual_final_parent_adoption=False,production_go=False,independent_acceptance=False)


def mandor(g,path):
    module_manifest=strict(g.read(MODULE+'SOURCE.json'));module_paths=set(module_manifest['files'])|{MODULE+'SOURCE.json'}
    own=module_paths|{M_NS+n for n in('probe.py','TYPED_MODEL_PARENT.json','SOURCE_PROOF.json','SOURCE.json','COMPILED440_ALL22_SOURCE_REVIEW.json')}
    own.add('.github/workflows/cp7-mandor-install-plan-capability.yml')
    m,s=source(g,M_NS,FP_TREE,own);exact(s['source_pins'],92,'MANDOR_EXACT92_SOURCE_PINS')
    exact(len(module_manifest['files']),83,'MANDOR_MODULE83_SOURCE_PINS')
    for n in module_paths:exact(g.read(n),g.read(n,M_MODULE_HEAD),'MANDOR_EXACT_REVIEWED_MODULE_BLOB:'+n)
    for n,v in module_manifest['files'].items():g.verify_pin(n,v)
    r,raw=original(path,M_ARCHIVE,'MANDOR_COMPLETE_INSTALL_PLAN_NEW3.json')
    fields(r,dict(status='ACTUAL_SUPABASE17_COMPLETE_MANDOR_MODEL_INSTALL_PLAN_NEW3_PASS_NOT_NATIVE_BUSINESS',
        model_parent_tables=45,exact_Native_source_definitions_reproduced_in_MODEL=11,mocked_helpers=12,
        Native_table_constraints_defaults_generated_RLS_Auth_and_domain_constraints_NOT_reproduced=True,
        actual_parent_gate_NEVER_opened=True,actual_global_or_Mandor_final_parent_adoption=False,
        actual_Native_cases=0,actual_Auth_HTTP_cases=0,actual_browser_cases=0,capability_DB_removed=True,
        model_roles_removed_and_global_roles_restored=True,production_go=False,independent_acceptance=False),'MANDOR_MODEL_SCOPE')
    fields(r['source'],dict(head=M_HEAD,tree=M_TREE,source_pins=92),'MANDOR_OWNING_SOURCE')
    ids=['COMPLETE_MODEL_STAGE40_FUNCTIONS27_TRIGGERS9_OWNER_ADAPTERS_AND_CLOSED_REAL_GATE',
        'UNCHANGED_NATIVE_PUBLIC_SALES_FACADE_DELEGATES_WITHOUT_NEW_EXECUTE_GRANTS_OR_ROLE_LEAK',
        'PENDING_MODEL_CONTEXT_REFUSED_THEN_EXPLICIT_UNUSED_FULL_STAGE_INVERSE_RESTORES_ALL22_AND_RAW_AUTHORITY']
    exact(r['checks'],[dict(id=n,status='PASS')for n in ids],'MANDOR_EXACT3_NEW_CASES')
    v=r['raw'];before,after=v['before_all22'],v['installed_all22'];exact(len(before),22,'MANDOR_ALL22');exact(set(after),set(before),'MANDOR_ALL_GROUPS')
    exact(v['compiled_model_before_all22'],before,'MANDOR_SAME_COMPILED_BASE');exact(v['compiled_model_after_all22'],after,'MANDOR_SAME_COMPILED_INSTALL')
    plan=strict(g.read(MODULE+'INSTALL_PLAN.json'));private,public=plan['private_functions'],plan['public_functions']
    exact(len(private),34,'MANDOR_PRIVATE34');exact(len(public),6,'MANDOR_PUBLIC6');exact(len(plan['tables']),15,'MANDOR_TABLES15')
    exact(set(after['functions'])-set(before['functions']),set(private+public),'MANDOR_ONLY_NEW40_FUNCTIONS')
    payment=strict(g.read(MODULE+'NATIVE_PAYMENT_OWNER_REFERENCE.json'))['functions'];sales=strict(g.read(MODULE+'NATIVE_SALES_COMMAND_REFERENCE.json'))['functions']
    fixture=strict(g.read(M_NS+'TYPED_MODEL_PARENT.json'))
    for sig,row in fixture['original_functions'].items():
        exact(row,(payment|sales)[sig],'MANDOR_ORIGINAL11_REVIEWED_REFERENCE');exact(before['functions'][sig],row,'MANDOR_ACTUAL_MODEL_COMPLETE19_BEFORE:'+sig)
    for sig in private:
        row=after['functions'][sig];exact(row[1],'postgres','MANDOR_PRIVATE_OWNER')
        expected={('postgres','postgres','EXECUTE',False)}|{(role,'postgres','EXECUTE',False)for role in plan['private_execute_grants'].get(sig,[])}
        exact({tuple(x)for x in row[18]},expected,'MANDOR_PRIVATE_EXACT_ACL:'+sig)
    api='cp7_mandor_shop_api'
    for sig in public:
        row=after['functions'][sig];exact(row[1],api,'MANDOR_PUBLIC_OWNER');exact(row[4],True,'MANDOR_PUBLIC_DEFINER')
        exact({tuple(x)for x in row[18]},{(api,api,'EXECUTE',False),('authenticated',api,'EXECUTE',False)},'MANDOR_PUBLIC_EXACT_ACL:'+sig)
    for table in plan['tables']:
        row=after['relations'][table];exact(row[0],'postgres','MANDOR_TABLE_OWNER');exact(row[3],True,'MANDOR_TABLE_RLS')
        require(all(x[0]==x[1]=='postgres'for x in row[12]),'MANDOR_TABLE_OWNER_ONLY_ACL')
    exact(before['schemas']['public'][0],after['schemas']['public'][0],'MANDOR_PUBLIC_SCHEMA_OWNER_PRESERVED')
    exact({tuple(x)for x in after['schemas']['public'][1]},
        {tuple(x)for x in before['schemas']['public'][1]}|{(api,before['schemas']['public'][0],'USAGE',False)},'MANDOR_ONLY_DECLARED_PUBLIC_USAGE')
    identities=v['original_Native_model_identity'];exact(len(identities),9,'MANDOR_NINE_ADAPTER_IDENTITIES')
    exact(v['final_Native_model_identity'],identities,'MANDOR_ALL9_ORIGINAL_OIDS_RAW_ACLS_AND_SCHEMAS_RESTORED')
    exact(v['final_all22'],before,'MANDOR_COMPLETE_FINAL_RAW22_EQUALS_ORIGINAL')
    exact(v['actual_non_superuser_profile'],['postgres','postgres',False,170006],'MANDOR_REAL_NONSUPERUSER_SESSION')
    exact(v['direct_private_command_denial']['SQLSTATE'],'42501','MANDOR_PRIVATE_COMMAND_REFUSED')
    exact(v['authorized_existing_facade_modeled_response'],dict(owner='cp7_sales_write',session='postgres'),'MANDOR_EXISTING_FACADE_DISPATCH_CONTEXT')
    exact(v['modeled_pending_context_refusal'],'MANDOR_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE:cp7_mandor_shop.command_context','MANDOR_PENDING_CONTEXT_REFUSAL')
    exact(v['gate_refusal'],'CP7_MANDOR_SHOP_ACTUAL_FINAL_ACCEPTED_PARENT_PENDING','MANDOR_REAL_INSTALL_GATE_STAYS_CLOSED')
    require(v['preuse_inverse']['all22_and_Native_raw_authority_restored']is True,'MANDOR_PREUSE_INVERSE_SOURCE_ASSERTION')
    return dict(status='ROOT_VERIFIED_ACTUAL17_COMPLETE_MANDOR_MODEL_PLAN3_NOT_NATIVE_BUSINESS',
        head=M_HEAD,tree=M_TREE,run_id=41463719530,job_id=125339000446,module_head=M_MODULE_HEAD,source=s,
        archive=M_ARCHIVE,original_report=raw,new_controls=3,all_original_failed_attempts_remain_failed=True,
        complete_model_raw22_final_equality_and_40_function_ACLs_and_15_table_RLS_independently_matched=True,
        actual_model9_OIDs_raw_function_and_schema_ACLs_independently_matched=True,
        model_context_refusal_and_environment_cleanup_are_source_bound_NOT_financial_inverse=True,
        actual_Native_cases=0,actual_final_parent_adoption=False,actual_Auth_HTTP_cases=0,actual_browser_cases=0,
        production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--kind',choices=('fixed25','mandor'),required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    head,tree=(FP_HEAD,FP_TREE)if a.kind=='fixed25'else(M_HEAD,M_TREE)
    with GitBytes(a.source,head,tree)as g:value=(fixed25 if a.kind=='fixed25'else mandor)(g,a.archive)
    a.output.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(dict(status=value['status'],actual_Native_cases=0)))
