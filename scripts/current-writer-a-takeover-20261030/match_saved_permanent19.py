"""Match full Native19 definitions/metadata and view13 in actual saved cases.

Uses the Root-retained strict financial4 Original. No database, SQL, writer,
real Auth, browser, new test execution or final global acceptance is supplied.
"""
from pathlib import Path
from hashlib import file_digest
import argparse,json,zipfile
from intake_common import exact,fields,pin,require
from intake_sku27 import strict,group
import preflight_saved_global_profile as profile
import intake_permanent_focused as current
import retain_permanent4 as retained


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def match(root,directory,archive,root_receipt):
    raw=Path(root_receipt).read_bytes();exact(pin(raw),current.ROOT_PIN,'EXACT_ROOT_RETAINED_FINANCIAL4_RECEIPT')
    receipt=strict(raw)
    fields(receipt,dict(status='ROOT_RETAINED_PERMANENT_FINANCIAL4_NOT_AGGREGATE_PASS',
        head=retained.HEAD,tree=retained.TREE,run_id=retained.RUN,job_id=retained.JOB,
        retained_Native_cases=4,actual_outer_restoration_verified=True,failed_run_relabelled_PASS=False),
        'EXACT_ACTUAL_ORIGINAL_CONTEXT_NOT_AGGREGATE_PASS')
    expected,source=profile.profile(root,directory)
    capture=strict((Path(directory)/'CAPTURE.json').read_bytes())
    authority=strict((Path(directory)/'AUTHORITY.json').read_bytes())
    view_name=authority['Native_view']['name'];view=capture['view_relation']
    exact(len(view),13,'EXACT_FULL_NATIVE_VIEW13_PROFILE')
    archive=Path(archive);exact(archive.stat().st_size,retained.ARCHIVE['bytes'],'EXACT_ORIGINAL_FULL_ARCHIVE_SIZE')
    with archive.open('rb')as stream:exact(file_digest(stream,'sha256').hexdigest(),retained.ARCHIVE['sha256'],'EXACT_ORIGINAL_FULL_ARCHIVE_SHA')
    with zipfile.ZipFile(archive)as z:
        name=retained.NATIVE;wanted=receipt['originals'][name]
        exact(z.getinfo(name).file_size,wanted['bytes'],'EXACT_ORIGINAL_STRICT_NATIVE4_SIZE')
        with z.open(name)as stream:exact(file_digest(stream,'sha256').hexdigest(),wanted['sha256'],'EXACT_ORIGINAL_STRICT_NATIVE4_SHA')
        with z.open(name)as stream:native=json.load(stream)
    group(native,receipt['retained_case_ids'])
    observations=[]
    for case,row in native['cases'].items():
        read=row['permanent_S05_read']
        fields(read,dict(status='PASS',reader_remained_installed=True,all_fields_retained=True,business_DML=False),
            'ACTUAL_SAVED_FINANCIAL_CASE_READER_INTERVAL')
        for boundary in('before','after'):
            catalog=read[boundary]['actual_all22'];functions=catalog['functions']
            selected={name:functions[name]for name in expected}
            exact(selected,expected,'EVERY_FULL_NATIVE19_FIELD_AND_DEFINITION_EQUALS_ACTUAL_PUBLISHED_PROFILE')
            exact(catalog['relations'][view_name],view,'EVERY_FULL_NATIVE_VIEW13_FIELD_EQUALS_ACTUAL_PROFILE')
            observations.append(dict(case=case,boundary=boundary,all_namespace_function_count=len(functions),
                full19_profile=pin(canonical(selected)),view13_profile=pin(canonical(catalog['relations'][view_name]))))
    exact(len(observations),8,'ALL_EIGHT_ACTUAL_BEFORE_AFTER_NATIVE19_OBSERVATIONS')
    return dict(status='ACTUAL_SAVED_PERMANENT4_FULL_NATIVE19_AND_VIEW13_PROFILE_MATCH',
        actual_head=retained.HEAD,actual_tree=retained.TREE,actual_run_id=retained.RUN,actual_job_id=retained.JOB,
        artifact_id=retained.ARTIFACT,archive=retained.ARCHIVE,strict_Native4_original=wanted,
        root_retained4=current.ROOT_PIN,actual_complete_product_sources=receipt['qualified_complete_sources'],
        published_profile_source=source,functions=19,fields_each=19,includes_exact_pg_get_functiondef=True,
        includes_exact_arguments_result_and_support=True,includes_full_expanded_EXECUTE_acl=True,
        Native_view=view_name,Native_view_fields=13,observations=observations,
        raw_NULL_vs_explicit_acl_inferred=False,raw_function_or_relation_acl_observed=False,
        metadata_compatibility_only=True,new_Native_Auth_browser_or_race_cases=0,
        prior_profile_models_not_rerun=True,final_composite_accepted=False,
        global_writer_current_rights_and_phantom_lock_qualified=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--profile-directory',type=Path,required=True);p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--root-retained4',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    require(not a.output.exists(),'ACTUAL_NATIVE19_PROFILE_RESULT_NOT_OVERWRITTEN')
    value=match(a.source,a.profile_directory,a.archive,a.root_retained4)
    with a.output.open('x')as out:out.write(json.dumps(value,indent=2)+'\n')
    print(json.dumps({k:value[k]for k in('status','functions','fields_each','Native_view_fields','new_Native_Auth_browser_or_race_cases')}))
