"""Admit only unchanged successful components of the exact failed Current38.

The run remains INCOMPLETE. This receipt grants no fresh cases and cannot by
itself admit the current product. A separately qualified successor must prove
source invariance, the missing two browsers, and all five owning package gates.
"""
from pathlib import Path
from hashlib import sha256,file_digest
import argparse,json,zipfile
import intake_join37 as old
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict,group,full_census,declared_files

HEAD='08ef3bee814e6452b9193b53efc05d53abca2d9d'
TREE='abf7e8b78bd56907ace9fb30211d956b63d68797'
RUN=41291621885
JOB=124803871870
ARTIFACT=13082560860
ARCHIVE=dict(bytes=688425402,sha256='3ee9b053a947e4dee14602dd07a9574191c6707813dfb27cbadfbc08b28e7b0c')

def intake(root,path,metadata):
    fields(metadata,dict(head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,artifact_id=ARTIFACT,
        run_attempt=1,conclusion='failure',expired=False,archive=ARCHIVE),
        'ONLY_EXACT_ACTUAL_FAILED_CURRENT38')
    path=Path(path)
    exact(path.stat().st_size,ARCHIVE['bytes'],'COMPLETE_CANONICAL_ARCHIVE_SIZE')
    with path.open('rb')as stream:actual=file_digest(stream,'sha256').hexdigest()
    exact(actual,ARCHIVE['sha256'],'COMPLETE_CANONICAL_ARCHIVE_DIGEST')
    with GitBytes(root,HEAD,TREE)as git,zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(names),len(set(names)),'UNIQUE_CANONICAL_MEMBERS')
        for name in names:safe_path(name)
        require(z.testzip()is None,'COMPLETE_CANONICAL_CRC')
        source=old.source(git);ids=source['case_ids'];pins={}
        def original(name):
            raw=z.read(name);pins[name]=pin(raw);return strict(raw)
        main=original(old.MAIN);package=original('T3_PACKAGE_INSTALL.json')
        backup=original('T3_BACKUP_RESTORE_DRILL.json')
        supervision=original('JOIN_RUNTIME_SUPERVISION.json')
        fields(main,dict(status='INCOMPLETE',qualification_commit=HEAD,required_case_ids=[old.CASE],
            required_case_ids_pass=False,error='S05_SKU_COMPLETE_FRESH_BROWSER2_REQUIRED',
            baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,
            cp6_restored=True,baseline_advisors_equal=True,advisor_gate=True,
            production_go=False,independent_acceptance=False),'EXACT_FAILED_JOIN_WITH_COMPLETE_RESTORE')
        fields(supervision,dict(status='INCOMPLETE',qualification_commit=HEAD,github_run_id=str(RUN),
            github_run_attempt='1',worker_exit=1,deadline_reached=False,external_signal=None,
            orphaned_child=False,process_group_empty=True,process_tree_empty=True,signals=[],
            job_budget_seconds=21600,work_budget_seconds=19800,recovery_reserve_seconds=1200,
            artifact_reserve_seconds=600,actual_case_credit=0,production_go=False),
            'FAILED_WORKER_REAPED_WITHOUT_CLOCK_OR_PROCESS_FAILURE')
        exact(package['gate'],dict(old.GATES,writer_runtime=False),'EXACT_PRIOR_FOUR_GATES_NOT_ALL_FIVE')
        fields(package['run_identity'],dict(tool_head=HEAD,github_sha=HEAD,run_id=str(RUN),run_attempt='1'),
            'EXACT_FAILED_PACKAGE_RUN_IDENTITY')
        exact(set(main['committed']),{old.CASE},'ONE_ACTUAL_JOIN_COMPONENT')
        part=main['committed'][old.CASE]
        fields(part,dict(status='INCOMPLETE',actual_Native_cases=0,actual_browser_cases=0,
            production_go=False,independent_acceptance=False),'NO_FAILED_AGGREGATE_CREDIT')
        first=part['fresh_S03_Native14'];second=part['fresh_SKU_Native7'];third=part['fresh_S05_Native10']
        for component,count in ((first,14),(second,7),(third,10)):
            fields(component,dict(status='PASS',actual_Native_cases=count,used_guard_refused_before_DDL=True),
                'UNCHANGED_SUCCESSFUL_NATIVE_COMPONENT')
        groups=[('S03_Native11',first['native'],'CP7_S03_ATTENDANCE_CHOICE_NATIVE11_CASES.json'),
            ('S03_reader3',first['reader_native3'],'CP7_S03_ATTENDANCE_CHOICE_READER_NATIVE3_CASES.json'),
            ('SKU_Native7',second['native'],'CP7_SKU_PAIR_CONVERSION_NATIVE7.json'),
            ('S05_Native10',third['native'],'CP7_S05_ON_SKU_NATIVE10_CASES.json')]
        retained={}
        for label,embedded,name in groups:
            value=original(name);exact(value,embedded,'RAW_STRICT_GROUP_EQUALS_ACTUAL_EMBEDDED:'+label)
            group(value,ids[label])
            for case_id in ids[label]:
                require(case_id not in retained,'UNIQUE_RETAINED_CASE_ID')
                retained[case_id]=dict(status='PASS',retained=True,fresh_case_credit=0)
        capture=first['actual_installed_capture'];delta={}
        exec(compile(git.read('scripts/cp7_s03_sku_composition/native_delta.py'),
            'root_retained_exact_captured_native_deriver','exec'),delta)
        exact(set(capture['originals']),set(delta['SIGNATURES']),'EXACT_FIFTEEN_CAPTURE_IDENTITIES')
        exact(capture['definitions'],delta['patched'](capture['originals']),'EXACT_FIFTEEN_NATIVE_BODIES')
        exact(capture['clones'],delta['clones'](capture['originals']),'EXACT_TWO_NATIVE_CLONES')
        before=first['used_inverse_refusal_before']
        exact(before,first['used_inverse_refusal_after'],'ACTUAL_USED_INVERSE_ZERO_EFFECT')
        used=full_census(before['actual_all22'],before['full_data_and_sequences'])
        fields(third['separate_committed_business_witness'],dict(status='NATIVE_BUSINESS_COMMITTED',
            Native10_case_credit=0,report_business_DML=False),'ACTUAL_USED_READER_WITNESS_NOT_REPORT_DML')
        fourth=part['fresh_S03_browser4']
        fields(fourth,dict(status='PASS',actual_browser_cases=4),'RETAINED_REAL_AUTH_S03_BROWSER4')
        old.browser(fourth['browser'],ids['S03_browser4'],git,old.NS+'s03_cases.mjs','EXACT_RETAINED_AUTH_BROWSER4')
        for case_id in ids['S03_browser4']:
            require(case_id not in retained,'UNIQUE_RETAINED_BROWSER_ID')
            retained[case_id]=dict(status='PASS',retained=True,fresh_case_credit=0)
        exact(len(retained),35,'EXACT_35_VALID_RETAINED_COMPONENT_CASES')
        fifth=part['fresh_S05_browser2'];fields(fifth,dict(status='INCOMPLETE'),'MISSING_S05_BROWSER2_NOT_PASS')
        for suffix,expected in [('DESKTOP','UNMEASURED_SKU_TEXT_SURFACE'),('MOBILE390','430 !== 390')]:
            name='S05_SKU_'+suffix+'_8CEA71E86A09496DB0E82ACA8CEECD74_FIRST_FAILURE.json'
            failure=original(name)
            require(expected in failure['error'],'ONLY_THE_ACTUAL_FIRST_S05_VISUAL_FAILURE:'+suffix)
            fields(failure,dict(progress={},routeErrors=[],console_errors=[],page_errors=[]),
                'NO_HIDDEN_ROUTE_OR_CONSOLE_SUCCESSOR_FAILURE:'+suffix)
        fields(backup,dict(status='RESTORED_IDENTICAL'),'EXACT_ACTUAL_BACKUP_DRILL')
        require(all(type(v)is bool and v for v in backup['checks'].values()),'ALL_TYPED_BACKUP_CHECKS')
        exact(backup['data']['differ'],{},'NO_BACKUP_DATA_DIFFERENCE')
        fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'ALL_ROLES_RESTORED')
        fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,
            database_owner_acl_and_settings_preserved=True),'COMPLETE_OUTER_RESTORE')
        maps=declared_files(git,main['source_declaration']['current_installation'])
        return dict(status='ROOT_RETAINED_CURRENT38_NATIVE31_S03_BROWSER4_NOT_AGGREGATE_PASS',
            head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,artifact_id=ARTIFACT,original_run_conclusion='failure',
            archive=dict(ARCHIVE,members=len(names)),originals=pins,source_admission=source,
            actual_product_source_maps=maps,qualified_financial_sources=pin(json.dumps(
                main['source_declaration']['current_installation'],sort_keys=True,separators=(',',':')).encode()),
            retained_cases=retained,retained_Native_cases=31,retained_S03_browser_cases=4,
            retained_cases_require_successor_source_invariance=True,fresh_case_credit=0,
            missing_case_ids=ids['S05_browser2'],original_package_gates=package['gate'],
            original_restore_and_backup_valid=True,actual_S03_used_refusal_raw_full_boundary=used,
            failed_run_relabelled_PASS=False,full37_qualified=False,package_all_five=False,
            production_go=False,independent_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--artifact-metadata',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    value=intake(args.source,args.archive,strict(args.artifact_metadata.read_bytes()))
    with args.output.open('x')as stream:stream.write(json.dumps(value,indent=2)+'\n')
    print(json.dumps({k:value[k]for k in ('status','retained_Native_cases','retained_S03_browser_cases','fresh_case_credit','full37_qualified')}))
