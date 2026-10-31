"""Read-only exact-current composite intake; partial or retained cases refuse."""
from pathlib import Path
from hashlib import sha256
import argparse,ast,json,re,zipfile
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict,literal,group,full_census,declared_files

HEAD='1d52f8a2cf48c07d6af86dbaf114989cb2f5bece'
TREE='abdae9ea30b7e6a32d77fbe0e8151196f9e8ff7f'
BASE='b25eaae55a144aa03cc05f8f77109f5d0b02fbfb'
NS='scripts/current-s03-sku-s05-composite-qualification/'
CASE='CURRENT_S03_SKU_S05_NATIVE31_BROWSER6'
MAIN='CP7_CURRENT_S03_SKU_S05_NATIVE31_BROWSER6.json'
RUN=41200818043
JOB=124536087695
GATES=dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=True)

def source(g):
    manifest=strict(g.read(NS+'SOURCE.json'))
    fields(manifest,dict(status='PREPARED_CURRENT_COMPOSITE37_NOT_EXECUTED',base_head=BASE,
        base_tree='e08f5eba90fd9a2deeb53a0a483c49e7a080e31c',actual_cases=0,
        planned=dict(SKU_Native7=7,S03_Native14=14,S05_Native10=10,S03_browser4=4,S05_browser2=2,total=37),
        production_go=False,independent_acceptance=False),'EXACT_CURRENT_JOIN_SOURCE')
    exact(len(manifest['files']),52,'EXACT_SOURCE52')
    for name,digest in manifest['files'].items():g.verify_pin(name,digest)
    base=g.entries(BASE);exact(len(base),14000,'EXACT_JOINED_BASE14000')
    for name,entry in base.items():exact(g.tree.get(name),entry,'UNCHANGED_PARENT_BLOB_AND_MODE:'+name)
    exact(set(g.tree)-set(base),set(manifest['files'])|{NS+'SOURCE.json'},'CLOSED_CURRENT_JOIN53_PATHS')
    ids={
        'S03_Native11':list(literal(g,'scripts/current-s03-sku-native14-binding/retained-s03-f42e/cases.py','IDS')),
        'S03_reader3':list(literal(g,'scripts/current-s03-sku-native14-binding/retained-s03-f42e/reader_cases.py','IDS')),
        'SKU_Native7':list(literal(g,'scripts/current-sku-pair-conversion-qualification/cases.py','IDS')),
        'S05_Native10':list(literal(g,'scripts/cp7_accessory_standard_report/cases.py','IDS')),
        'S05_browser2':manifest['browser_case_ids'],
    }
    text=g.read(NS+'evidence.mjs').decode()
    ids['S03_browser4']=ast.literal_eval(re.search(r'export const IDS\s*=\s*(\[.*?\])',text,re.S).group(1))
    exact([len(ids[key])for key in ('S03_Native11','S03_reader3','SKU_Native7','S05_Native10','S03_browser4','S05_browser2')],
        [11,3,7,10,4,2],'EXACT_SIX_SOURCE_GROUPS')
    exact(len({item for values in ids.values()for item in values}),37,'EXACT_37_UNIQUE_SOURCE_IDS')
    return dict(manifest=pin(g.read(NS+'SOURCE.json')),source_files=52,unchanged_base_blobs_and_modes=14000,
        current_paths=53,case_ids=ids,actual_case_credit=0)

def browser(value,ids,g,script,label):
    fields(value,dict(status='RUN_COMPLETE',counts={'PASS':len(ids)},planned_case_ids=ids,
        real_auth=True,jwt_signed_by_runtime=False,host_exit=0,host_status='RUN_COMPLETE',database_remaining=0,
        console_errors=0,auth_cleanup_failures=[],session_leaks=[],
        auth_counts=dict(before=[0,0,0,0],after=[0,0,0,0],restored=True)),label)
    exact(list(value['cases']),ids,label+'_EXACT_ORDER')
    exact(value['script_sha256'],sha256(g.read(script)).hexdigest(),label+'_ACTUAL_SCRIPT')
    for row in value['cases'].values():
        fields(row,dict(status='PASS'),label+'_CASE')
        require(not row.get('business_day_rollover'),label+'_REAL_BUSINESS_DAY')
    require(not any(value.get(key)for key in ('cleanup_failures','error','host_error','business_day_retried','business_day_first_attempt')),
        label+'_SINGLE_ATTEMPT_AND_CLEANUP')

def intake(root,path,metadata):
    fields(metadata,dict(head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,run_attempt=1,
        conclusion='success',expired=False),'EXACT_TERMINAL_API_ARTIFACT_METADATA')
    expected=metadata['archive'];fields(expected,dict(bytes=expected['bytes'],sha256=expected['sha256']),'ARCHIVE_SHAPE')
    require(type(expected['bytes'])is int and expected['bytes']>0,'ACTUAL_ARCHIVE_POSITIVE_INTEGER_BYTES')
    require(type(expected['sha256'])is str and re.fullmatch('[0-9a-f]{64}',expected['sha256'])is not None,'ACTUAL_ARCHIVE_SHA256')
    path=Path(path)
    exact(path.stat().st_size,expected['bytes'],'EXACT_CANONICAL_ZIP_SIZE')
    with path.open('rb')as stream:actual=__import__('hashlib').file_digest(stream,'sha256').hexdigest()
    exact(actual,expected['sha256'],'EXACT_CANONICAL_ZIP_DIGEST')
    with GitBytes(root,HEAD,TREE)as g,zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(set(names)),len(names),'NO_DUPLICATE_CANONICAL_MEMBERS')
        for name in names:safe_path(name)
        require(z.testzip()is None,'ACTUAL_ARCHIVE_CRC')
        admitted=source(g);ids=admitted['case_ids'];raw_pins={}
        def original(name):
            raw=z.read(name);raw_pins[name]=pin(raw);return strict(raw)
        main=original(MAIN);package=original('T3_PACKAGE_INSTALL.json');restore=original('T3_BACKUP_RESTORE_DRILL.json')
        fields(main,dict(status='PASS',qualification_commit=HEAD,required_case_ids=[CASE],required_case_ids_pass=True,
            actual_Native_cases=31,actual_browser_cases=6,actual_business_cases=37,actual_Auth_HTTP_cases=0,
            actual_two_session_races=0,baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,
            cp6_restored=True,baseline_advisors_equal=True,advisor_gate=True,used_guard_refused_before_DDL=True,
            production_go=False,independent_acceptance=False),'CURRENT_FRESH37_AND_COMPLETE_RESTORE')
        exact(set(main['committed']),{CASE},'ONE_CURRENT_JOIN_COMPONENT')
        part=main['committed'][CASE]
        fields(part,dict(status='PASS',business_counts={'PASS':37},actual_Native_cases=31,actual_browser_cases=6,
            actual_Auth_HTTP_cases=0,actual_two_session_races=0,retained_SKU27_fresh_case_credit=0,
            Afui_positive_HPP_zero_reimbursement_coverage=False,global_writer_or_permission_or_lock_closure=False,
            used_guard_refused_before_DDL=True),'EXACT_COMPONENT_NO_UNPROVEN_CREDIT')
        all_ids={name for values in ids.values()for name in values}
        exact(set(part['business_cases']),all_ids,'ONE_FRESH_37_UNIQUE_UNION')
        for row in part['business_cases'].values():fields(row,dict(status='PASS'),'CURRENT_CASE')
        first=part['fresh_S03_Native14'];second=part['fresh_SKU_Native7'];third=part['fresh_S05_Native10']
        for component,count in ((first,14),(second,7),(third,10)):
            fields(component,dict(status='PASS',actual_Native_cases=count,used_guard_refused_before_DDL=True),'CURRENT_NATIVE_COMPONENT')
        raw_groups=[('S03_Native11',first['native'],'CP7_S03_ATTENDANCE_CHOICE_NATIVE11_CASES.json'),
            ('S03_reader3',first['reader_native3'],'CP7_S03_ATTENDANCE_CHOICE_READER_NATIVE3_CASES.json'),
            ('SKU_Native7',second['native'],'CP7_SKU_PAIR_CONVERSION_NATIVE7.json'),
            ('S05_Native10',third['native'],'CP7_S05_ON_SKU_NATIVE10_CASES.json')]
        for label,embedded,name in raw_groups:
            value=original(name);exact(value,embedded,'RAW_CURRENT_GROUP_EQUALS_EMBEDDED:'+label);group(value,ids[label])
        capture=first['actual_installed_capture'];delta={}
        exec(compile(g.read('scripts/cp7_s03_sku_composition/native_delta.py'),'root_join_pure_captured_deriver','exec'),delta)
        exact(set(capture['originals']),set(delta['SIGNATURES']),'ACTUAL_FIFTEEN_CAPTURE_IDENTITIES')
        exact(capture['definitions'],delta['patched'](capture['originals']),'EXACT_FIFTEEN_CURRENT_DERIVATIONS')
        exact(capture['clones'],delta['clones'](capture['originals']),'EXACT_TWO_NATIVE_CLONES')
        before=first['used_inverse_refusal_before'];exact(before,first['used_inverse_refusal_after'],'RAW_S03_USED_INVERSE_ZERO_EFFECT')
        used=full_census(before['actual_all22'],before['full_data_and_sequences'])
        witness=third['separate_committed_business_witness']
        fields(witness,dict(status='NATIVE_BUSINESS_COMMITTED',Native10_case_credit=0,report_business_DML=False),
            'S05_ACTUAL_NATIVE_USED_WITNESS_NOT_REPORT_DML')
        browser(part['fresh_S03_browser4']['browser'],ids['S03_browser4'],g,NS+'s03_cases.mjs','S03_CURRENT_AUTH_BROWSER4')
        browser(part['fresh_S05_browser2']['browser'],ids['S05_browser2'],g,NS+'browser.mjs','S05_CURRENT_AUTH_BROWSER2')
        exact(package['gate'],GATES,'ALL_FIVE_ACTUAL_PACKAGE_GATES')
        fields(package['run_identity'],dict(tool_head=HEAD,github_sha=HEAD,run_id=str(RUN),run_attempt='1'),'EXACT_CURRENT_PACKAGE_RUN')
        fields(restore,dict(status='RESTORED_IDENTICAL'),'EXACT_ACTUAL_BACKUP_DRILL')
        require(all(type(v)is bool and v for v in restore['checks'].values()),'ALL_TYPED_BACKUP_CHECKS')
        exact(restore['data']['differ'],{},'NO_BACKUP_ROW_DIFFERENCE')
        fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'ALL_BASELINE_ROLES_RESTORED')
        fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,database_owner_acl_and_settings_preserved=True),
            'COMPLETE_OUTER_RESTORE_RECEIPT')
        maps=declared_files(g,main['source_declaration']['current_installation'])
        return dict(status='ROOT_VERIFIED_CURRENT_JOIN_NATIVE31_BROWSER6_ALL5',head=HEAD,tree=TREE,run_id=RUN,
            job_id=JOB,artifact_id=metadata['artifact_id'],archive=dict(expected,members=len(names)),originals=raw_pins,
            source_admission=admitted,actual_product_source_maps=maps,complete37_qualified=True,
            qualified_financial_sources=pin(json.dumps(main['source_declaration']['current_installation'],
                sort_keys=True,separators=(',',':')).encode()),
            actual_Native_cases=31,actual_browser_cases=6,package_all_five=True,package_gates=package['gate'],
            actual_S03_used_refusal_raw_full_boundary=used,outer_restore_source_bound_receipts=True,
            prior_runs_aggregated=False,retained_SKU27_fresh_case_credit=0,S05_reader_qualified_as_bounded_intervals=True,
            permanent_complete_assembly_qualified=False,global_writer_or_permission_or_lock_closure=False,
            Afui_positive_HPP_zero_reimbursement_coverage=False,production_go=False,independent_acceptance=False)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--check-source',action='store_true');parser.add_argument('--archive',type=Path)
    parser.add_argument('--artifact-metadata',type=Path);parser.add_argument('--output',type=Path);args=parser.parse_args()
    if args.check_source:
        with GitBytes(args.source,HEAD,TREE)as git:proof=source(git)
        print(json.dumps(dict(status='EXACT_CURRENT_JOIN_SOURCE_AND_37_IDS_ONLY',source_files=proof['source_files'],
            unchanged_base_blobs_and_modes=proof['unchanged_base_blobs_and_modes'],actual_new_cases=0)))
    else:
        require(all((args.archive,args.artifact_metadata,args.output)),'CANONICAL_ARCHIVE_METADATA_AND_OUTPUT_REQUIRED')
        value=intake(args.source,args.archive,strict(args.artifact_metadata.read_bytes()))
        args.output.write_text(json.dumps(value,indent=2)+'\n')
        print(json.dumps({key:value[key]for key in ('status','complete37_qualified','package_all_five')}))
