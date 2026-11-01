"""Retain actual financial4 from the failed browser attempt; never accept its run.

Read the complete canonical archive, original strict Native group, every raw
reader boundary and the actual outer restoration. This supplies no database,
Auth, browser, qualification activation or fresh case execution.
"""
from pathlib import Path
from hashlib import file_digest
import argparse,json,zipfile
import intake_permanent6 as original
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict,group,full_census,declared_files

HEAD=original.HEAD
TREE=original.TREE
RUN=original.RUN
JOB=original.JOB
ARTIFACT=13101464593
ARCHIVE=dict(bytes=48925129,sha256='95d7ccbe4be056c27968ba0c2c312dcce16a0608c3cca0406aa796535a09fa44',members=134)
NATIVE=original.NATIVE
MAIN=original.MAIN
CASE=original.CASE


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def checked(g,main,native,package,backup,supervised,raw_pins):
    admitted=original.source(g)
    fields(main,dict(status='INCOMPLETE',qualification_commit=HEAD,required_case_ids=[CASE],
        required_case_ids_pass=False,error='S05_SKU_COMPLETE_FRESH_BROWSER2_REQUIRED',
        baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,cp6_restored=True,
        baseline_advisors_equal=True,advisor_gate=True,production_go=False,independent_acceptance=False),
        'FAILED_PERMANENT_BROWSER_RUN_STAYS_INCOMPLETE')
    exact(set(main['committed']),{CASE},'EXACT_ORIGINAL_PERMANENT_COMPONENT')
    part=main['committed'][CASE]
    fields(part,dict(status='INCOMPLETE',actual_Native_cases=0,actual_browser_cases=0,
        retained_join37_fresh_case_credit=0,permanent_reader_remains_installed=True,
        production_go=False,independent_acceptance=False),'FAILED_COMPOSITE_NOT_RECOUNTED_PASS')
    first=part['fresh_permanent_financial4']
    fields(first,dict(status='PASS',actual_Native_cases=4,reader_remains_installed=True,
        retained_join37_fresh_case_credit=0,production_go=False,independent_acceptance=False),
        'ACTUAL_FOUR_FINANCIAL_CASES_COMPLETED_BEFORE_BROWSER_FAILURE')
    exact(first['native'],native,'ORIGINAL_STRICT_NATIVE4_EQUALS_EMBEDDED_ORIGINAL')
    exact(first['strict_group_originals'],[dict(name=NATIVE,**raw_pins[NATIVE])],
        'ORIGINAL_STRICT_GROUP_PRODUCER_BOUND_BYTES')
    ids=admitted['native_ids'];group(native,ids)
    reads={}
    for name,row in native['cases'].items():
        read=row['permanent_S05_read']
        fields(read,dict(status='PASS',reader_remained_installed=True,business_DML=False,all_fields_retained=True),
            'EVERY_FINANCIAL_CASE_RETAINS_COMPLETE_PUBLIC_READER')
        exact(read['before'],read['after'],'EVERY_ACTUAL_READER_HAS_FULL_RAW_ZERO_EFFECT')
        boundary=full_census(read['before']['actual_all22'],read['before']['full_data_and_sequences'])
        reads[name]=dict(status='PASS',full_boundary_restored=True,public_schema_unchanged=True,
            read_boundary=boundary,raw_before_after_equal=True,raw_boundary=pin(canonical(read['before'])),
            unchanged_original_financial_case=row['unchanged_original_financial_case'])
    witness=part['separate_committed_Native_use']
    fields(witness,dict(status='NATIVE_BUSINESS_COMMITTED',Native_case_credit=0,
        used_inverse_guard_refused_before_DDL=True,reader_remains_installed=True),
        'ORIGINAL_ACTUAL_COMMITTED_USE_AND_INVERSE_REFUSAL')
    exact(witness['before'],witness['after'],'COMMITTED_USED_INVERSE_REFUSAL_RAW_ZERO_EFFECT')
    witness_boundary=full_census(witness['before']['actual_all22'],witness['before']['full_data_and_sequences'])
    fresh=part['fresh_permanent_browser2'];browser=fresh['browser']
    fields(fresh,dict(status='INCOMPLETE'),'MISSING_BROWSER_QUALIFICATION_NOT_RETAINED')
    fields(browser,dict(status='INCOMPLETE',counts={'INCOMPLETE':2},real_auth=True,jwt_signed_by_runtime=False,
        host_exit=0,host_status='RUN_COMPLETE',console_errors=0,database_remaining=0,
        auth_cleanup_failures=[],session_leaks=[],
        auth_counts=dict(before=[0,0,0,0],after=[0,0,0,0],restored=True)),
        'FAILED_BROWSER_ACTUAL_AUTH_AND_COPY_CLEANUP')
    exact(set(browser['cases']),set(admitted['browser_ids']),'EXACT_TWO_MISSING_BROWSER_IDENTITIES')
    failures={}
    for name,row in browser['cases'].items():
        fields(row,dict(status='INCOMPLETE'),'NEITHER_BROWSER_HAS_CASE_CREDIT')
        error=row['error']
        require(type(error)is str and "expected=STATE['installed_catalog']['schemas']['erp']"in error
            and "TypeError: 'NoneType' object is not subscriptable"in error
            and 'persistent_browser_fixture.py'in error,'EXACT_OBSERVED_FRESH_PROCESS_HELPER_STATE_FAILURE')
        failures[name]=dict(status='INCOMPLETE',error_sha256=pin(error.encode())['sha256'],
            cause='FRESH_BROWSER_FIXTURE_HELPER_STATE_NOT_INITIALIZED')
    require(not browser.get('cleanup_failures')and not browser.get('business_day_retried')
        and not browser.get('business_day_first_attempt'),'NO_CLEANUP_FAILURE_OR_HIDDEN_BROWSER_RETRY')
    exact(package['gate'],dict(installed=True,primary_unchanged=True,backup_restore_drill=True,
        security_advisors=True,writer_runtime=False),'FOUR_RAW_PACKAGE_GATES_AND_FAILED_RUNTIME_NOT_ALL5')
    fields(package['run_identity'],dict(tool_head=HEAD,github_sha=HEAD,run_id=str(RUN),run_attempt='1'),
        'EXACT_OWNING_FAILED_PACKAGE_RUN')
    fields(backup,dict(status='RESTORED_IDENTICAL'),'ACTUAL_ORIGINAL_BACKUP_RESTORE_DRILL')
    require(bool(backup['checks'])and all(type(x)is bool and x for x in backup['checks'].values()),
        'ALL_TYPED_BACKUP_CHECKS_TRUE')
    exact(backup['data']['differ'],{},'NO_BACKUP_ROW_DIFFERENCE')
    fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'ALL_ORIGINAL_ROLES_RESTORED')
    fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,
        database_owner_acl_and_settings_preserved=True),'FULL_OUTER_RESTORE_DESPITE_BROWSER_FAILURE')
    fields(supervised,dict(status='INCOMPLETE',qualification_commit=HEAD,github_run_id=str(RUN),
        github_run_attempt='1',worker_exit=1,signals=[],deadline_reached=False,external_signal=None,
        orphaned_child=False,process_group_empty=True,process_tree_empty=True,job_budget_seconds=21600,
        work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600,
        actual_case_credit=0,production_go=False),'ACTUAL_FAILED_WORKER_COMPLETED_AND_CHILDREN_REAPED')
    graph=main['source_declaration']['current_installation'];maps=declared_files(g,graph)
    parent_raw=g.read(original.NS+'JOIN37_ROOT_ACTUAL_INTAKE.json')
    exact(pin(parent_raw),original.PARENT_RECEIPT,'EXACT_ALREADY_ACCEPTED_PARENT_RECEIPT_RETAINED')
    parent=strict(parent_raw)
    exact(pin(canonical(graph['financial_parent'])),parent['qualified_financial_sources'],
        'WHOLE_FINANCIAL_PARENT_EQUALS_ALREADY_ACCEPTED_SOURCE')
    return dict(status='ROOT_RETAINED_PERMANENT_FINANCIAL4_NOT_AGGREGATE_PASS',head=HEAD,tree=TREE,
        run_id=RUN,job_id=JOB,artifact_id=ARTIFACT,archive=ARCHIVE,originals=raw_pins,
        source_admission=admitted,actual_product_source_maps=maps,
        qualified_complete_sources=pin(canonical(graph)),qualified_financial_sources=pin(canonical(graph['financial_parent'])),
        financial_callback_source=pin(g.read(original.NS+'persistent_financial.py')),
        retained_Native_cases=4,actual_new_Native_cases=0,actual_new_browser_cases=0,
        retained_cases_are_not_fresh=True,retained_case_ids=ids,missing_case_ids=admitted['browser_ids'],
        financial_cases=reads,actual_used_refusal_raw_boundary=witness_boundary,
        actual_outer_restoration_verified=True,actual_backup_restore_verified=True,
        actual_primary_unchanged=True,actual_advisors_equal=True,actual_Auth_and_browser_copy_cleanup=True,
        failed_worker_reaped=True,package_all_five=False,complete6_qualified=False,
        retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
        missing_browser_cases=failures,source_invariant_reuse_required=True,
        all_five_new_package_gates_still_required=True,production_go=False,independent_acceptance=False)


def intake(root,path,metadata):
    run=metadata['run'];fields(run,dict(id=RUN,head_sha=HEAD,run_attempt=1,status='completed',
        conclusion='failure',event='push'),'EXACT_ACTUAL_FAILED_RUN_API')
    fields(run['head_commit'],dict(id=HEAD,tree_id=TREE),'EXACT_ACTUAL_FAILED_SOURCE_TREE_API')
    jobs=metadata['jobs'];require(type(jobs)is list and len(jobs)==1,'ONE_OWNING_ACTUAL_JOB')
    fields(jobs[0],dict(id=JOB,run_id=RUN,status='completed',conclusion='failure'),
        'EXACT_TERMINAL_FAILED_JOB_API')
    exact([(s['number'],s['name'])for s in jobs[0]['steps']if s['conclusion']=='failure'],
        [(70,'Run actual permanent reader financial4 normal App browser2 and complete outer restoration')],
        'ONLY_ACTUAL_BROWSER_RUNTIME_STEP_FAILED')
    artifact=metadata['artifact'];fields(artifact,dict(id=ARTIFACT,expired=False,size_in_bytes=ARCHIVE['bytes'],
        digest='sha256:'+ARCHIVE['sha256']),'EXACT_ACTUAL_UNEXPIRED_FULL_CANONICAL_API')
    fields(artifact['workflow_run'],dict(id=RUN,head_sha=HEAD),'CANONICAL_BELONGS_TO_ORIGINAL_RUN')
    path=Path(path);exact(path.stat().st_size,ARCHIVE['bytes'],'EXACT_FULL_CANONICAL_BYTES')
    with path.open('rb')as stream:exact(file_digest(stream,'sha256').hexdigest(),ARCHIVE['sha256'],'EXACT_FULL_CANONICAL_SHA')
    with GitBytes(root,HEAD,TREE)as g,zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(names),ARCHIVE['members'],'ALL_ORIGINAL_CANONICAL_MEMBERS')
        exact(len(set(names)),len(names),'NO_DUPLICATE_ORIGINALS')
        for name in names:safe_path(name)
        require(z.testzip()is None,'ALL_ORIGINAL_CANONICAL_CRCS')
        pins={}
        def read(name):
            raw=z.read(name);pins[name]=pin(raw);return strict(raw)
        main=read(MAIN);native=read(NATIVE);package=read('T3_PACKAGE_INSTALL.json')
        backup=read('T3_BACKUP_RESTORE_DRILL.json');supervised=read('PERMANENT_RUNTIME_SUPERVISION.json')
        return checked(g,main,native,package,backup,supervised,pins)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--metadata',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    value=intake(a.source,a.archive,strict(a.metadata.read_bytes()))
    with a.output.open('x')as out:out.write(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(status=value['status'],retained_Native_cases=4,actual_new_cases=0,
        package_all_five=False,failed_run_relabelled_PASS=False)))
