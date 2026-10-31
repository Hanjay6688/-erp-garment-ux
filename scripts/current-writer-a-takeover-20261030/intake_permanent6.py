"""Read-only actual permanent6 intake; activation identity deliberately pending.

Source-only checks are possible on the prepared tree. Full intake requires
the exact activated head/run/job, canonical artifact and every raw gate.
No product import, SQL, Auth, browser or network operation is supplied here.
"""
from pathlib import Path
from hashlib import file_digest
import argparse,ast,json,re,zipfile
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict,literal,group,full_census,declared_files
from intake_join37 import browser

HEAD=None
TREE=None
RUN=None
JOB=None
PREPARED_HEAD='a5944f25a5e3ba1f1f537a18abe923eb753f922f'
PREPARED_TREE='42011c517ae4f8ecf69ebf6ce565c5da2c75eea5'
BASE='33988923ab3bad708b21f3c74002f1309a3644e1'
NS='scripts/current-final-s03-sku-s05-preparation/'
MAIN='CP7_PERMANENT_S05_S03_SKU_NATIVE4_BROWSER2.json'
NATIVE='CP7_PERMANENT_S05_S03_FINANCIAL_NATIVE4.json'
CASE='PERMANENT_S05_S03_SKU_NATIVE4_BROWSER2'
GATES=dict(installed=True,primary_unchanged=True,backup_restore_drill=True,security_advisors=True,writer_runtime=True)


def source(g):
    declaration=strict(g.read(NS+'PREPARATION.json'))
    fields(declaration,dict(base_head=BASE,actual_new_Native_cases=0,production_go=False,
        independent_acceptance=False),'PERMANENT_SOURCE_PREPARATION_NOT_CASE_CREDIT')
    base=g.entries(BASE);exact(len(base),14050,'PERMANENT_UNCHANGED_FINANCIAL_BASE14050')
    for name,value in base.items():exact(g.tree.get(name),value,'PERMANENT_BASE_BLOB_AND_MODE:'+name)
    allowed=set(declaration['files'])|{NS+'PREPARATION.json'}
    require(all(name.startswith(('scripts/cp7_current_s03_sku_s05/',NS))
        or name=='.github/workflows/cp7-final-s03-sku-s05.yml'for name in allowed),'PERMANENT_ONLY_OWN_SOURCE_SCOPE')
    exact(set(g.tree)-set(base),allowed,'PERMANENT_EXACT_CLOSED_ADDITIVE_SOURCE')
    for name,value in declaration['files'].items():g.verify_pin(name,value)
    originals=list(literal(g,NS+'persistent_financial.py','ORIGINAL_IDS'))
    all_financial=list(literal(g,'scripts/current-s03-sku-native14-binding/retained-s03-f42e/cases.py','IDS'))
    require(len(originals)==4 and set(originals)<=set(all_financial),'PERMANENT_EXACT_FOUR_ORIGINAL_FINANCIAL_CALLBACKS')
    native=['PERMANENT_S05_'+name for name in originals]
    text=g.read(NS+'persistent_browser.mjs').decode()
    match=re.search(r'export const IDS\s*=\s*(\[.*?\])',text,re.S)
    require(match is not None,'PERMANENT_EXPLICIT_BROWSER_IDS_REQUIRED')
    brows=ast.literal_eval(match.group(1));exact(len(brows),2,'PERMANENT_EXACT_TWO_BROWSER_IDS')
    exact(len(set(native+brows)),6,'PERMANENT_EXACT_SIX_UNIQUE_SOURCE_IDS')
    return dict(source_pins=len(declaration['files']),own_paths=len(allowed),unchanged_base=14050,
        native_ids=native,browser_ids=brows,source_manifest=pin(g.read(NS+'PREPARATION.json')),actual_case_credit=0)


def intake(root,path,metadata):
    require(all(value is not None for value in(HEAD,TREE,RUN,JOB)),'PERMANENT_ACTIVATED_EXACT_RUN_INTAKE_NOT_YET_PINNED')
    fields(metadata,dict(head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,run_attempt=1,
        conclusion='success',expired=False),'PERMANENT_EXACT_TERMINAL_API_METADATA')
    expected=metadata['archive']
    require(type(expected['bytes'])is int and expected['bytes']>0,'PERMANENT_POSITIVE_CANONICAL_ARCHIVE_BYTES')
    require(type(expected['sha256'])is str and re.fullmatch('[0-9a-f]{64}',expected['sha256'])is not None,
        'PERMANENT_CANONICAL_ARCHIVE_SHA256')
    path=Path(path);exact(path.stat().st_size,expected['bytes'],'PERMANENT_CANONICAL_ARCHIVE_SIZE')
    with path.open('rb')as stream:exact(file_digest(stream,'sha256').hexdigest(),expected['sha256'],'PERMANENT_CANONICAL_ARCHIVE_DIGEST')
    with GitBytes(root,HEAD,TREE)as g,zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(set(names)),len(names),'PERMANENT_NO_DUPLICATE_ARCHIVE_MEMBERS')
        for name in names:safe_path(name)
        require(z.testzip()is None,'PERMANENT_CANONICAL_ARCHIVE_CRC')
        admitted=source(g);pins={}
        def original(name):
            raw=z.read(name);pins[name]=pin(raw);return strict(raw)
        main=original(MAIN);package=original('T3_PACKAGE_INSTALL.json');backup=original('T3_BACKUP_RESTORE_DRILL.json')
        fields(main,dict(status='PASS',qualification_commit=HEAD,required_case_ids=[CASE],required_case_ids_pass=True,
            actual_Native_cases=4,actual_browser_cases=2,actual_business_cases=6,actual_Auth_HTTP_cases=0,
            actual_two_session_races=0,retained_join37_fresh_case_credit=0,used_guard_refused_before_DDL=True,
            baseline_full22_all_rows_all_sequences_equal=True,restore_raw_public_equal=True,cp6_restored=True,
            baseline_advisors_equal=True,advisor_gate=True,production_go=False,independent_acceptance=False),
            'PERMANENT_CURRENT_FRESH6_AND_FULL_RESTORE')
        exact(set(main['committed']),{CASE},'PERMANENT_ONE_ACTUAL_COMPONENT')
        part=main['committed'][CASE]
        fields(part,dict(status='PASS',business_counts={'PASS':6},actual_Native_cases=4,actual_browser_cases=2,
            retained_join37_fresh_case_credit=0,permanent_reader_remains_installed=True,
            global_writer_or_permission_or_lock_closure=False,Afui_positive_HPP_zero_reimbursement_coverage=False),
            'PERMANENT_COMPONENT_NO_UNPROVEN_CREDIT')
        ids=admitted['native_ids'];browser_ids=admitted['browser_ids']
        exact(set(part['business_cases']),set(ids+browser_ids),'PERMANENT_SIX_ACTUAL_CASE_IDENTITIES')
        for row in part['business_cases'].values():fields(row,dict(status='PASS'),'PERMANENT_ACTUAL_CASE')
        first=part['fresh_permanent_financial4'];fields(first,dict(status='PASS',actual_Native_cases=4),'PERMANENT_NATIVE4_COMPONENT')
        native=original(NATIVE);exact(native,first['native'],'PERMANENT_RAW_NATIVE4_EQUALS_EMBEDDED');group(native,ids)
        for row in native['cases'].values():
            read=row['permanent_S05_read']
            fields(read,dict(status='PASS',reader_remained_installed=True,business_DML=False,all_fields_retained=True),
                'PERMANENT_EVERY_ACTUAL_PUBLIC_READER')
            exact(read['before'],read['after'],'PERMANENT_EVERY_READER_RAW_ZERO_EFFECT')
            full_census(read['before']['actual_all22'],read['before']['full_data_and_sequences'])
        witness=part['separate_committed_Native_use']
        fields(witness,dict(status='NATIVE_BUSINESS_COMMITTED',Native_case_credit=0,
            used_inverse_guard_refused_before_DDL=True,reader_remains_installed=True),'PERMANENT_REAL_COMMITTED_NATIVE_USE')
        exact(witness['before'],witness['after'],'PERMANENT_USED_REFUSAL_RAW_ZERO_EFFECT')
        used=full_census(witness['before']['actual_all22'],witness['before']['full_data_and_sequences'])
        browser(part['fresh_permanent_browser2']['browser'],browser_ids,g,NS+'persistent_browser.mjs','PERMANENT_REAL_AUTH_BROWSER2')
        exact(package['gate'],GATES,'PERMANENT_ALL_FIVE_PACKAGE_GATES')
        fields(package['run_identity'],dict(tool_head=HEAD,github_sha=HEAD,run_id=str(RUN),run_attempt='1'),
            'PERMANENT_EXACT_CURRENT_OWNING_RUN')
        fields(backup,dict(status='RESTORED_IDENTICAL'),'PERMANENT_ACTUAL_BACKUP_DRILL')
        require(bool(backup['checks'])and all(type(x)is bool and x for x in backup['checks'].values()),
            'PERMANENT_ALL_TYPED_BACKUP_CHECKS')
        exact(backup['data']['differ'],{},'PERMANENT_BACKUP_NO_ROW_DIFFERENCE')
        fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'PERMANENT_EXACT_ROLE_RESTORE')
        fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,
            database_owner_acl_and_settings_preserved=True),'PERMANENT_OUTER_RESTORE')
        graph=main['source_declaration']['current_installation'];maps=declared_files(g,graph)
        parent_raw=g.read(NS+'JOIN37_ROOT_ACTUAL_INTAKE.json');parent=strict(parent_raw)
        fields(parent,dict(status='ROOT_VERIFIED_CURRENT_JOIN_NATIVE31_BROWSER6_ALL5',complete37_qualified=True,
            package_all_five=True,prior_runs_aggregated=False),'PERMANENT_EXACT_QUALIFIED_PARENT37')
        return dict(status='ROOT_VERIFIED_PERMANENT_S05_NATIVE4_BROWSER2_ALL5',head=HEAD,tree=TREE,
            run_id=RUN,job_id=JOB,artifact_id=metadata['artifact_id'],archive=dict(expected,members=len(names)),originals=pins,
            source_admission=admitted,actual_product_source_maps=maps,
            qualified_complete_sources=pin(json.dumps(graph,sort_keys=True,separators=(',',':')).encode()),
            qualified_parent37=dict(head=parent['head'],run_id=parent['run_id'],root_intake=pin(parent_raw)),
            actual_Native_cases=4,actual_browser_cases=2,complete6_qualified=True,package_all_five=True,
            prior_runs_aggregated=False,retained_join37_fresh_case_credit=0,reader_remains_installed=True,
            actual_used_refusal_raw_boundary=used,global_writer_or_permission_or_lock_closure=False,
            Afui_positive_HPP_zero_reimbursement_coverage=False,D1_E_qualified=False,
            production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--check-source',action='store_true')
    p.add_argument('--archive',type=Path);p.add_argument('--artifact-metadata',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.check_source:
        with GitBytes(a.source,HEAD or PREPARED_HEAD,TREE or PREPARED_TREE)as g:value=source(g)
        print(json.dumps(dict(status='EXACT_PERMANENT_SOURCE_AND_SIX_IDS_ONLY',source=value,actual_Native_cases=0)))
    else:
        require(all((a.archive,a.artifact_metadata,a.output)),'PERMANENT_CANONICAL_ARCHIVE_API_METADATA_AND_OUTPUT_REQUIRED')
        value=intake(a.source,a.archive,strict(a.artifact_metadata.read_bytes()))
        a.output.write_text(json.dumps(value,indent=2)+'\n');print(json.dumps(dict(status=value['status'],complete6_qualified=True)))
