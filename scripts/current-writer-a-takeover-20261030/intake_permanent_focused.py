"""Current permanent reader: actual retained4 plus fresh browser2, never fresh6."""
from pathlib import Path
from hashlib import file_digest
import argparse,json,re,zipfile
import intake_permanent6 as prior
import retain_permanent4 as retained
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict,literal,full_census,declared_files
from intake_join37 import browser
from intake_s05_focused import browser_assets

HEAD='15a2170cea88cd03a4d1bcaa0873a969d495b9fa'
TREE='3fe772a1314ae6bc7c4f36f72e3fda8738eb70fc'
RUN=41354607179
JOB=124991886417
PREPARED_HEAD='15a2170cea88cd03a4d1bcaa0873a969d495b9fa'
PREPARED_TREE='3fe772a1314ae6bc7c4f36f72e3fda8738eb70fc'
ROOT_HEAD='8efe21a9211b9ee2a617a37b7ff69233499e3a61'
ROOT_TREE='591c92b8b71f30271ee1c232cdc3b3422aaf7a77'
ROOT_PATH='docs/cp7/d17-14/ow15/CURRENT_PERMANENT23E_ROOT_RETAINED4_20261102.json'
ROOT_PIN=dict(bytes=7661,sha256='2d63531df996ff6e5fb9400ec2a0dc4a4e47283750f8c560e435819b54abf3af')
NS=prior.NS
ROUTED={NS+n for n in('PERSISTENT_BROWSER_DERIVATIONS.json','PERSISTENT_BROWSER_SOURCE.json',
    'SUPERVISION_DERIVATIONS.json','WORKFLOW_DERIVATION.json','admission.py','component.py','controls.py',
    'engine.py','fetch_parent37.py','final_gate.py','persistent_browser_fixture.py','test_focused_parent_receipt.py')}
ROUTED.add('.github/workflows/cp7-final-s03-sku-s05.yml')
ADDED={NS+n for n in('FOCUSED_BROWSER2_ORIGIN.json','ROOT_RETAINED4.json','retained4.py','fetch_retained4.py','test_focused_browser2.py')}


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()


def source(g):
    with GitBytes(g.root,retained.HEAD,retained.TREE)as old:
        origin=prior.source(old);base=old.tree
        record=strict(g.read(NS+'FOCUSED_BROWSER2_ORIGIN.json'))
        fields(record,dict(status='EXACT_BROWSER_ONLY_CALLER_SUCCESSOR_NOT_CASE_CREDIT',
            origin_head=retained.HEAD,origin_tree=retained.TREE,financial_callback_source_changed=False,
            product_SQL_or_reader_changed=False,retained_Native_cases=4,fresh_browser_cases=2,actual_ERP_cases=0),
            'EXACT_FOCUSED_BROWSER_ONLY_SUCCESSOR')
        exact(set(record['files']),ROUTED,'CLOSED_THIRTEEN_REVIEWED_CALLER_PATHS')
        for name,item in record['files'].items():
            raw=old.read(name);exact(pin(raw),item['original'],'EXACT_ORIGINAL_CALLER:'+name)
            text=raw.decode();require(bool(item['changes']),'COUNTED_FOCUSED_ROUTES_REQUIRED')
            for change in item['changes']:
                exact(change['count'],1,'ONE_EXACT_CONTEXTUAL_CALLER_HUNK')
                exact(text.count(change['before']),1,'ONE_EXACT_CALLER_ANCHOR:'+name)
                text=text.replace(change['before'],change['after'],1)
            exact(text.encode(),g.read(name),'ONLY_COUNTED_REVIEWED_CALLER_BYTES:'+name)
            exact(pin(text.encode()),item['derived'],'EXACT_DERIVED_CALLER_PIN:'+name)
            for change in reversed(item['changes']):
                exact(text.count(change['after']),1,'ONE_EXACT_CALLER_INVERSE:'+name)
                text=text.replace(change['after'],change['before'],1)
            exact(text.encode(),raw,'COMPLETE_ORIGINAL_CALLER_RECOVERED:'+name)
        for name,value in base.items():
            if name not in ROUTED|{NS+'PREPARATION.json'}:
                exact(g.tree.get(name),value,'ALL_OTHER_PRODUCT_SQL_READER_CALLBACK_BLOBS_AND_MODES_UNCHANGED:'+name)
        exact(set(g.tree)-set(base),ADDED,'EXACT_FIVE_NEW_OWN_SOURCE_INPUTS')
        exact(set(base)-set(g.tree),set(),'NO_ORIGINAL_SOURCE_REMOVED')
        old_manifest=strict(old.read(NS+'PREPARATION.json'));manifest=strict(g.read(NS+'PREPARATION.json'))
        exact(set(manifest['files']),set(old_manifest['files'])|ADDED,'ALL_AND_ONLY_61_CURRENT_SOURCE_PINS')
        exact({k:v for k,v in manifest.items()if k not in('files','focused_browser_followup')},
            {k:v for k,v in old_manifest.items()if k!='files'},'ORIGINAL_PREPARATION_CONTRACT_RETAINED')
        fields(manifest['focused_browser_followup'],dict(origin_head=retained.HEAD,retained_Native_cases=4,
            fresh_Native_cases=0,fresh_browser_cases=2,financial_groups_rerun=False,source_invariant_reuse=True,
            root_receipt=ROOT_PIN,all_five_new_package_gates_required=True),'HONEST_FOCUSED_CASE_COUNTS')
        for name,value in manifest['files'].items():g.verify_pin(name,value)
        fixture=NS+'persistent_browser_fixture.py';raw=old.read(fixture)
        anchor=b'    state = json.loads(state_raw)\n'
        initialization=(b"    # This fixture runs in a fresh Python process. Rebind the frozen helper's\n"
            b'    # catalog expectation from the exact reader state before its first use;\n'
            b'    # the parent qualification process cannot share module globals with us.\n'
            b"    helper.control.STATE = dict(installed_catalog=state['after'])\n")
        exact(raw.count(anchor),1,'ONE_ORIGINAL_HASH_VERIFIED_READER_STATE_PARSE')
        exact(g.read(fixture),raw.replace(anchor,anchor+initialization,1),'ONLY_EXACT_FRESH_PROCESS_OBSERVER_INITIALIZATION')
        before=strict(old.read(NS+'PERSISTENT_BROWSER_SOURCE.json'));after=strict(g.read(NS+'PERSISTENT_BROWSER_SOURCE.json'))
        exact({k:v for k,v in before.items()if k!='files'},{k:v for k,v in after.items()if k!='files'},
            'ALL_ORIGINAL_BROWSER_IDS_AND_CASE_CONTRACTS_RETAINED')
        exact(set(before['files']),set(after['files']),'SAME_NINETEEN_BROWSER_INPUT_NAMES')
        for name,digest in after['files'].items():g.verify_pin(name,digest)
        native_source=pin(g.read(NS+'persistent_financial.py'))
    with GitBytes(g.root,ROOT_HEAD,ROOT_TREE)as root:
        raw=root.read(ROOT_PATH);exact(pin(raw),ROOT_PIN,'EXACT_PUBLISHED_ROOT_RETAINED4_RECEIPT')
    exact(g.read(NS+'ROOT_RETAINED4.json'),raw,'COPIED_ROOT_RETENTION_BYTES_UNMODIFIED')
    receipt=strict(raw);exact(native_source,receipt['financial_callback_source'],'ALL_FOUR_RETAINED_CALLBACK_SOURCE_BYTES')
    for name,value in dict(ROOT_HEAD=ROOT_HEAD,ROOT_TREE=ROOT_TREE,ROOT_PATH=ROOT_PATH,ROOT_PIN=ROOT_PIN,
        ORIGIN_HEAD=retained.HEAD,ORIGIN_TREE=retained.TREE,RUN=retained.RUN,JOB=retained.JOB,
        ARTIFACT=retained.ARTIFACT,ARCHIVE=retained.ARCHIVE).items():
        exact(literal(g,NS+'retained4.py',name),value,'EXACT_FROZEN_ACTUAL_RETENTION_BINDING:'+name)
    return dict(status='EXACT_PERMANENT_BROWSER2_ONLY_SUCCESSOR_AND_RETAINED4_SOURCE',
        unchanged_prior_release_blobs=len(base)-len(ROUTED)-1,unchanged_financial_base=14107,
        routed_original_paths=len(ROUTED),new_own_paths=5,own_paths=62,source_pins=61,
        complete_original_caller_bytes_recovered=True,product_SQL_reader_and_financial_callback_source_unchanged=True,
        original_source_admission=origin,retained_root_receipt=ROOT_PIN,retained_head=retained.HEAD,
        qualified_complete_sources=receipt['qualified_complete_sources'],
        retained_native_original=receipt['originals'][prior.NATIVE],
        native_ids=receipt['retained_case_ids'],browser_ids=receipt['missing_case_ids'],
        actual_fresh_Native_cases=0,retained_Native_cases=4,fresh_browser_cases=2,
        actual_ERP_case_credit=0,production_go=False,independent_acceptance=False)


def check_reuse(value,admitted):
    fields(value,dict(status='ROOT_VALIDATED_FINANCIAL4_RETAINED_BY_COMPLETE_SOURCE_IDENTITY',
        root_head=ROOT_HEAD,root_tree=ROOT_TREE,root_path=ROOT_PATH,root_receipt=ROOT_PIN,
        original_head=retained.HEAD,original_tree=retained.TREE,original_run_id=retained.RUN,
        original_job_id=retained.JOB,artifact_id=retained.ARTIFACT,archive=retained.ARCHIVE,
        original_native=admitted['retained_native_original'],
        retained_Native_cases=4,retained_case_ids=admitted['native_ids'],missing_case_ids=admitted['browser_ids'],
        actual_new_Native_cases=0,retained_cases_are_not_fresh=True,financial_groups_rerun=False,
        qualified_complete_sources=admitted['qualified_complete_sources'],source_invariant_reuse=True,
        retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
        all_five_new_package_gates_still_required=True,production_go=False,independent_acceptance=False),
        'EXACT_RETAINED4_WITH_NO_FRESH_OR_AGGREGATE_CREDIT')


def intake(root,path,metadata):
    require(all(x is not None for x in(HEAD,TREE,RUN,JOB)),'FOCUSED_PERMANENT_ACTUAL_RUN_IDENTITY_PENDING')
    fields(metadata,dict(head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,run_attempt=1,conclusion='success',expired=False),
        'EXACT_TERMINAL_FOCUSED_BROWSER2_API_METADATA')
    expected=metadata['archive'];path=Path(path)
    require(type(expected['bytes'])is int and expected['bytes']>0,'POSITIVE_FULL_CANONICAL_ARCHIVE_BYTES')
    require(type(expected['sha256'])is str and re.fullmatch('[0-9a-f]{64}',expected['sha256'])is not None,
        'FULL_CANONICAL_ARCHIVE_SHA256_FORMAT')
    exact(path.stat().st_size,expected['bytes'],'FULL_FOCUSED_CANONICAL_ARCHIVE_BYTES')
    with path.open('rb')as stream:exact(file_digest(stream,'sha256').hexdigest(),expected['sha256'],'FULL_FOCUSED_CANONICAL_SHA')
    with GitBytes(root,HEAD,TREE)as g,zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(set(names)),len(names),'NO_DUPLICATE_FOCUSED_CANONICAL_ORIGINALS')
        for name in names:safe_path(name)
        require(z.testzip()is None,'FULL_FOCUSED_CANONICAL_CRC')
        admitted=source(g);pins={}
        def read(name):
            raw=z.read(name);pins[name]=pin(raw);return strict(raw)
        main=read(prior.MAIN);package=read('T3_PACKAGE_INSTALL.json');backup=read('T3_BACKUP_RESTORE_DRILL.json')
        supervised=read('PERMANENT_RUNTIME_SUPERVISION.json')
        fields(supervised,dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit=HEAD,github_run_id=str(RUN),
            github_run_attempt='1',worker_exit=0,signals=[],deadline_reached=False,external_signal=None,orphaned_child=False,
            process_group_empty=True,process_tree_empty=True,job_budget_seconds=21600,work_budget_seconds=19800,
            recovery_reserve_seconds=1200,artifact_reserve_seconds=600,actual_case_credit=0,production_go=False),
            'ACTUAL_FOCUSED_WORKER_REAPED_BEFORE_DATABASE_STOP')
        fields(main,dict(status='PASS',qualification_commit=HEAD,required_case_ids=[prior.CASE],required_case_ids_pass=True,
            actual_Native_cases=0,actual_browser_cases=2,actual_business_cases=2,actual_Auth_HTTP_cases=0,actual_two_session_races=0,
            retained_Native_cases=4,retained_cases_are_not_fresh=True,candidate_case_coverage=6,financial_groups_rerun=False,
            source_invariant_reuse=True,prior_runs_aggregated=True,retained_join37_fresh_case_credit=0,
            used_guard_refused_before_DDL=True,baseline_full22_all_rows_all_sequences_equal=True,
            restore_raw_public_equal=True,cp6_restored=True,baseline_advisors_equal=True,advisor_gate=True,
            production_go=False,independent_acceptance=False),'ACTUAL_FRESH_BROWSER2_RETAINED4_AND_FULL_OUTER_RESTORE')
        exact(set(main['committed']),{prior.CASE},'ONE_CURRENT_FOCUSED_COMPONENT')
        part=main['committed'][prior.CASE]
        fields(part,dict(status='PASS',business_counts={'PASS':2},actual_Native_cases=0,actual_browser_cases=2,
            retained_Native_cases=4,retained_cases_are_not_fresh=True,candidate_case_coverage=6,financial_groups_rerun=False,
            source_invariant_reuse=True,prior_runs_aggregated=True,retained_join37_fresh_case_credit=0,
            permanent_reader_remains_installed=True,global_writer_or_permission_or_lock_closure=False,
            Afui_positive_HPP_zero_reimbursement_coverage=False),'HONEST_CURRENT_COMPONENT_CASE_COUNTS')
        require('fresh_permanent_financial4'not in part and prior.NATIVE not in names,'FOUR_VALID_FINANCIAL_CASES_NOT_RERUN')
        exact(set(part['business_cases']),set(admitted['browser_ids']),'ONLY_MISSING_BROWSER_CASES_ARE_FRESH')
        for row in part['business_cases'].values():fields(row,dict(status='PASS'),'ACTUAL_CURRENT_BROWSER_CASE_PASS')
        check_reuse(part['retained_permanent_financial4'],admitted)
        exact(main['source_declaration']['retained_permanent_financial4'],part['retained_permanent_financial4'],
            'RETENTION_BOUND_BEFORE_ERP_AND_AT_COMPONENT_EXECUTION')
        original=read('PERMANENT_RETAINED4_ORIGINAL_ADMISSION.json')
        exact(part['retained4_original_admission'],original,'ORIGINAL_FAILED_ARCHIVE_ADMISSION_EQUALS_EMBEDDED')
        fields(original,dict(status='EXACT_FAILED_CANONICAL_FINANCIAL4_ORIGINALS_ADMITTED_NOT_RERUN',root_receipt=ROOT_PIN,
            original_head=retained.HEAD,original_run_id=retained.RUN,original_job_id=retained.JOB,artifact_id=retained.ARTIFACT,
            archive=retained.ARCHIVE,retained_Native_cases=4,actual_new_Native_cases=0,financial_groups_rerun=False,
            original_native=admitted['retained_native_original'],
            retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False),
            'EXACT_CANONICAL_ORIGINAL_FINANCIAL4_ADMITTED_BEFORE_DATABASE')
        fields(part['source_connection_release'],dict(phase='AFTER_PERMANENT_INSTALL_BEFORE_COMMITTED_WITNESS_AND_BROWSER_COPY',
            database='cp6_rollback',cursor_closed=True,connection_closed=True,foreign_backends_terminated=0,actual_Native_case_credit=0),
            'OWN_SOURCE_CONNECTION_RELEASED_WITHOUT_FOREIGN_SESSION_TERMINATION')
        witness=part['separate_committed_Native_use']
        fields(witness,dict(status='NATIVE_BUSINESS_COMMITTED',Native_case_credit=0,
            used_inverse_guard_refused_before_DDL=True,reader_remains_installed=True),'ACTUAL_COMMITTED_NATIVE_WITNESS_NOT_CASE_CREDIT')
        exact(witness['before'],witness['after'],'USED_REFUSAL_COMPLETE_RAW_ZERO_EFFECT')
        used=full_census(witness['before']['actual_all22'],witness['before']['full_data_and_sequences'])
        fresh=part['fresh_permanent_browser2']
        browser(fresh['browser'],admitted['browser_ids'],g,NS+'persistent_browser.mjs','CURRENT_PERMANENT_ACTUAL_AUTH_BROWSER2')
        assets=browser_assets(z,fresh,g,source_path=NS+'PERSISTENT_BROWSER_SOURCE.json')
        exact(package['gate'],prior.GATES,'EVERY_FRESH_PACKAGE_GATE_REQUIRED')
        fields(package['run_identity'],dict(tool_head=HEAD,github_sha=HEAD,run_id=str(RUN),run_attempt='1'),'ACTUAL_CURRENT_PACKAGE_IDENTITY')
        fields(backup,dict(status='RESTORED_IDENTICAL'),'CURRENT_BACKUP_RESTORE_DRILL')
        require(bool(backup['checks'])and all(type(x)is bool and x for x in backup['checks'].values()),'ALL_TYPED_BACKUP_CHECKS')
        exact(backup['data']['differ'],{},'NO_CURRENT_BACKUP_ROW_DIFFERENCE')
        fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'ALL_BASELINE_ROLES_RESTORED')
        fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,database_owner_acl_and_settings_preserved=True),
            'COMPLETE_CURRENT_OUTER_RESTORATION')
        graph=main['source_declaration']['current_installation'];maps=declared_files(g,graph)
        exact(pin(canonical(graph)),admitted['qualified_complete_sources'],'WHOLE_CURRENT_PRODUCT_GRAPH_EQUALS_ROOT_RETAINED4')
        return dict(status='ROOT_VERIFIED_PERMANENT_S05_RETAINED4_FRESH_BROWSER2_ALL5',head=HEAD,tree=TREE,
            run_id=RUN,job_id=JOB,artifact_id=metadata['artifact_id'],archive=dict(expected,members=len(names)),originals=pins,
            source_admission=admitted,actual_product_source_maps=maps,qualified_complete_sources=pin(canonical(graph)),
            qualified_parent37=dict(head=prior.BASE,run_id=prior.PARENT_RUN,root_intake=prior.PARENT_RECEIPT),
            actual_Native_cases=0,actual_browser_cases=2,fresh_cases=2,retained_Native_cases=4,retained_cases=4,
            retained_cases_are_not_fresh=True,candidate_case_coverage=6,complete6_qualified=True,package_all_five=True,
            actual_current_browser_raw_assets=assets,fresh6_one_attempt=False,prior_runs_aggregated=True,
            source_invariant_reuse=True,financial_groups_rerun=False,retained_original_run_conclusion='failure',
            failed_run_relabelled_PASS=False,retained_root_receipt=ROOT_PIN,retained_join37_fresh_case_credit=0,
            reader_remains_installed=True,actual_used_refusal_raw_boundary=used,runtime_supervision=supervised,
            global_writer_or_permission_or_lock_closure=False,Afui_positive_HPP_zero_reimbursement_coverage=False,
            D1_E_qualified=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--check-source',action='store_true')
    p.add_argument('--archive',type=Path);p.add_argument('--metadata',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.check_source:
        require(PREPARED_TREE is not None,'FOCUSED_PREPARED_TREE_PENDING')
        with GitBytes(a.source,HEAD or PREPARED_HEAD,TREE or PREPARED_TREE)as g:value=source(g)
    else:
        require(all((a.archive,a.metadata)),'FULL_CANONICAL_AND_ACTUAL_METADATA_REQUIRED')
        value=intake(a.source,a.archive,strict(a.metadata.read_bytes()))
    with a.output.open('x')as out:out.write(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(status=value['status'],actual_new_Native_cases=0)))
