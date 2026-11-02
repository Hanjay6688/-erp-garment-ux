"""Independent read-only intake of original three new authority model controls.

No product code, database, network, case runner or old test is imported. The
projection is reconstructed from raw observations, not from the product helper.
"""
from pathlib import Path
from hashlib import sha256
import argparse,copy,json,subprocess,zipfile
from intake_common import require,exact,pin

HEAD='091d8394a1be3de2fb805dcba3eae715345cad9b'
TREE='3aaec0de113baf8f37f3ca0448f8a2a2439b8a3a'
PARENT='6774e244eade7bf6c07fc97df1e44afea203a6b0'
ARCHIVE=dict(bytes=34761,sha256='ee1f20dc899d2bf7a538abb114919517a98f7c91b32c5a04b2b0d0214915cd01')
REPORT=dict(bytes=806043,sha256='8250026f08df48805b3f7b96abae08829160277d6dcee13e1c54ecd5d073c4b5')
IDS=['ACTUAL_NONSUPERUSER_PRIVATE_PURE_HELPER_AND_REAL_THREE_OID_RECREATIONS_PRESERVE_EXACT_OTHER_FIELDS',
 'SEVEN_REAL_MODELED_DDL_MUTATIONS_AND_EVERY_COMPLETE19_JSON_CELL_REMAIN_SENSITIVE',
 'EIGHT_TYPED_REFUSALS_THREE_EXTERNAL_DENIALS_AND_UNUSED_NARROW_INVERSE_ALL22']


def projection(value):
    result=copy.deepcopy(value)
    for name in('session_user','current_user','runtime_entry','required_final_parent','actual_Native_qualification_credit','production_go'):result.pop(name,None)
    for field,count in(('functions',19),('new_private_functions',4)):
        exact(len(result[field]),count,'PORTABLE_RAW_OBSERVED_COUNT:'+field)
        for row in result[field]:
            require(type(row['oid'])is int,'PORTABLE_RAW_OBSERVED_OID_TYPE');del row['oid']
    require(type(result['view']['oid'])is int,'PORTABLE_RAW_VIEW_OID_TYPE');del result['view']['oid']
    return result


def reconstructed(observed,proof):
    value=projection(observed)
    exact(proof['projected'],value,'PORTABLE_RAW_ALL_FIELDS_PROJECTION')
    exact(json.loads(proof['canonical_DB_jsonb_preimage']),value,'PORTABLE_ORIGINAL_DB_CANONICAL_PREIMAGE_CONTENT')
    exact(sha256(proof['canonical_DB_jsonb_preimage'].encode()).hexdigest(),proof['sha256'],'PORTABLE_ORIGINAL_DB_CANONICAL_PREIMAGE_SHA')
    return value


def intake(archive,repository,api):
    exact(pin(archive),ARCHIVE,'PORTABLE_CANONICAL_ARCHIVE_BYTES')
    with zipfile.ZipFile(__import__('io').BytesIO(archive))as z:
        require(z.testzip()is None,'PORTABLE_COMPLETE_ZIP_CRC');names=[n for n in z.namelist()if n.endswith('PORTABLE_AUTHORITY_MODEL3.json')]
        exact(len(names),1,'PORTABLE_ONE_ORIGINAL_REPORT');raw=z.read(names[0])
    exact(pin(raw),REPORT,'PORTABLE_ORIGINAL_FULL_REPORT_BYTES');v=json.loads(raw);r=v['raw']
    exact(v['source']['head'],HEAD,'PORTABLE_RUN_SOURCE_HEAD');exact(v['source']['tree'],TREE,'PORTABLE_RUN_SOURCE_TREE')
    run,jobs=api['run'],api['jobs']['jobs'];exact((run['id'],run['head_sha'],run['status'],run['conclusion']),(41468884812,HEAD,'completed','success'),'PORTABLE_TERMINAL_EXACT_RUN')
    exact(len(jobs),1,'PORTABLE_SINGLE_JOB');exact((jobs[0]['id'],jobs[0]['status'],jobs[0]['conclusion']),(125356915071,'completed','success'),'PORTABLE_TERMINAL_EXACT_JOB')
    exact(v['status'],'ACTUAL_SUPABASE17_PORTABLE_AUTHORITY_MODEL3_PASS_NOT_GLOBAL_RUNTIME','PORTABLE_ORIGINAL_STATUS')
    exact(v['checks'],[dict(id=x,status='PASS')for x in IDS],'PORTABLE_DECLARED_THREE_CHECKS')
    exact(r['actual_non_superuser_session'],['postgres','postgres',False,170006],'PORTABLE_ACTUAL_SESSION_IDENTITY')
    first=reconstructed(r['original_model_authority'],r['independent_projection_before'])
    second=reconstructed(r['after_actual_recreation'],r['independent_projection_after'])
    exact(first,second,'PORTABLE_THREE_RECREATIONS_KEEP_COMPLETE_OTHER_FIELDS')
    for path in(('functions',0),('new_private_functions',0)):
        require(r['original_model_authority'][path[0]][path[1]]['oid']!=r['after_actual_recreation'][path[0]][path[1]]['oid'],'PORTABLE_ACTUAL_FUNCTION_OID_MUST_CHANGE')
    require(r['original_model_authority']['view']['oid']!=r['after_actual_recreation']['view']['oid'],'PORTABLE_ACTUAL_VIEW_OID_MUST_CHANGE')
    exact(first['sentinel_nested_identity'],dict(oid=42,business_reference='MUST_REMAIN_EXACT'),'PORTABLE_UNRELATED_IDENTITY_NOT_REMOVED')
    real=[x for x in r['sensitivity_controls']if x['kind']=='ACTUAL_MODELED_DDL']
    exact({x['field']for x in real},{'body','native_function_ACL','private_helper_ACL','configuration','view_definition','view_ACL','view_options'},'PORTABLE_EXACT_SEVEN_ACTUAL_DDL_CONTROLS')
    for row in real:
        reconstructed(row['authority'],row['projection'])
        require(row['projection']['sha256']!=r['independent_projection_before']['sha256'],'PORTABLE_REAL_DDL_MUTATION_MUST_REMAIN_VISIBLE')
    sentinels=[x for x in r['sensitivity_controls']if x['kind']=='SYNTHETIC_JSON_FIELD_SENTINEL']
    exact([x['function_catalogue_cell']for x in sentinels],list(range(19)),'PORTABLE_ALL19_SYNTHETIC_FIELD_SENTINELS')
    require(all(x['sha256']!=r['independent_projection_before']['sha256']for x in sentinels),'PORTABLE_SYNTHETIC_CELL_MUTATION_MUST_REMAIN_VISIBLE')
    exact(len(r['malformed_refusals']),8,'PORTABLE_EIGHT_MALFORMED_CONTROLS')
    require(all(x['SQLSTATE']=='P0001'and x['message']=='CP7_GLOBAL_COMPLETE_TYPED_AUTHORITY_REQUIRED'for x in r['malformed_refusals']),'PORTABLE_TYPED_REFUSALS')
    exact({x['role']for x in r['external_role_denials']},{'anon','authenticated','service_role'},'PORTABLE_EXACT_EXTERNAL_ROLES')
    require(all(x['SQLSTATE']=='42501'for x in r['external_role_denials']),'PORTABLE_EXTERNAL_REAL_CALLS_REFUSED')
    exact(len(r['baseline_all22']),22,'PORTABLE_FULL22_BASELINE');exact(r['final_all22'],r['baseline_all22'],'PORTABLE_COMPLETE_FINAL22_EQUAL')
    require(v['capability_DB_removed']is True and v['global_roles_and_memberships_restored']is True,'PORTABLE_EXPLICIT_ENVIRONMENT_CLEANUP_FLAGS')
    def git(*args):return subprocess.check_output(['git','-C',str(repository),*args])
    exact(git('rev-parse',HEAD+'^{tree}').decode().strip(),TREE,'PORTABLE_ORIGINAL_PUBLIC_GIT_TREE')
    def entries(ref):return{line.split(b'\t',1)[1]:line.split(b'\t',1)[0]for line in git('ls-tree','-rz',ref).split(b'\0')if line}
    base,current=entries(PARENT),entries(HEAD)
    require(all(current.get(k)==x for k,x in base.items()),'PORTABLE_COMPLETE_PARENT_BLOBS_AND_MODES_PRESERVED')
    return dict(status='ROOT_VERIFIED_PORTABLE_AUTHORITY_ACTUAL17_MODEL3_NOT_GLOBAL_RUNTIME_OR_BUSINESS',
        head=HEAD,tree=TREE,run_id=41468884812,job_id=125356915071,archive=ARCHIVE,original_report=REPORT,
        unchanged_parent_blobs=len(base),new_paths=len(set(current)-set(base)),model_controls=3,
        original_DB_preimages_recomputed=True,actual_model_DDL_sensitivity_controls=7,synthetic_full19_cells_separately_labeled=True,
        actual_business_cases=0,actual_Native_cases=0,actual_parent_or_runtime_adoption=False,
        explicit_complete_installer_unused_inverse_qualified=False,financial_or_full_restore_credit=False,
        raw_complete_final22_equal=True,environment_cleanup_flags_are_not_financial_restore=True,
        old_tests_rerun=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--repository',type=Path,required=True);p.add_argument('--api',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=intake(a.archive.read_bytes(),a.repository,json.loads(a.api.read_bytes()))
    a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
