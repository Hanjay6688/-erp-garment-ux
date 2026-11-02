"""FREE3 focused successor: exact retained cases plus a fresh committed witness.

The failed origin is immutable. A success is closed until the sole actual
successor run/job and all five fresh package gates are bound and verified.
"""
from pathlib import Path
from hashlib import file_digest
from types import SimpleNamespace
import argparse,ast,json,zipfile
import intake_free3 as original
import retain_free3 as retained
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict,literal,full_census
from current_graph_sources import declared_files

PREPARED_HEAD='91a7b46ed13c4ad6094114871a4a39fa6765d140'
PREPARED_TREE='01c4807d932af1d534477c4c182715b1378bd39b'
HEAD='91a7b46ed13c4ad6094114871a4a39fa6765d140'
TREE='01c4807d932af1d534477c4c182715b1378bd39b'
RUN=41399754004
JOB=125128803743
NS=original.NS
ROOT_HEAD='3a26a27530525e0407be996e6ee2cbabe3314076'
ROOT_TREE='f9d56f07f1d2ca329b658cde8afabe75d04cd240'
ROOT_PATH='docs/cp7/d17-14/ow15/FREE41_AD986_ROOT_RETAINED3_20261102.json'
ROOT_PIN={'bytes':9721,'sha256':'7ddda623e3417b3c04d0db2d7f7ce309718a2128c0dfc4fa22f8d7ee0edeb375'}
CHANGED_PINS={'.github/workflows/cp7-current-complete-de-free-date-native3.yml': {'bytes': 33872, 'sha256': '9288618f18de1d860398acdeadbb8e1ad4d2951913abddb84b73f9fe956e6ca8'}, 'scripts/current-de-free-date-preparation/FOCUSED_COMMITTED_ORIGIN.json': {'bytes': 25424, 'sha256': '8a6dee4d49e3d045fce66b816eaa36e4b527b42391c3813ea05f61fad95677d9'}, 'scripts/current-de-free-date-preparation/ROOT_RETAINED3.json': {'bytes': 9721, 'sha256': '7ddda623e3417b3c04d0db2d7f7ce309718a2128c0dfc4fa22f8d7ee0edeb375'}, 'scripts/current-de-free-date-preparation/SOURCE.json': {'bytes': 9047, 'sha256': '7f4c71b35fe8f9690ff11cdd9d67a7d8e6992491c30458347baedf95f0e52454'}, 'scripts/current-de-free-date-preparation/component.py': {'bytes': 11362, 'sha256': 'd20ee2b228747c3ce3dc332e3afe5dcb762e0c054b78c9379eddf1d8b779c420'}, 'scripts/current-de-free-date-preparation/engine.py': {'bytes': 2195, 'sha256': 'ca070675d08d504c5cf0c1d97953cc079c509945ea6f765fcae0d2fda4642d70'}, 'scripts/current-de-free-date-preparation/fetch_retained3.py': {'bytes': 4364, 'sha256': 'eea54b75d33bebe78d8dc7d269426783bebc737baaad240c5ceb55d56a7de267'}, 'scripts/current-de-free-date-preparation/final_gate.py': {'bytes': 15583, 'sha256': 'a8b8b8667ff334808798e5f3e3f41b008884b6891c6bcb89349498aebca9483e'}, 'scripts/current-de-free-date-preparation/native3.workflow.yml.txt': {'bytes': 33872, 'sha256': '9288618f18de1d860398acdeadbb8e1ad4d2951913abddb84b73f9fe956e6ca8'}, 'scripts/current-de-free-date-preparation/probe.py': {'bytes': 4758, 'sha256': '0248d743ff20f15be1dc37024e868012a20923bafc8236a5d164d2fac4ac0200'}, 'scripts/current-de-free-date-preparation/retained3.py': {'bytes': 4894, 'sha256': '17d2ac3fa96590acc7744f7c5536517174605302c1671525ac7cd6b8a8ae3015'}, 'scripts/current-de-free-date-preparation/workflow.py': {'bytes': 6347, 'sha256': 'e0c0708f5f4e2a681e3ea0ffb2d229ddd966573a90f4950db6045613c48925b2'}}
NEW={NS+n for n in('retained3.py','fetch_retained3.py','ROOT_RETAINED3.json','FOCUSED_COMMITTED_ORIGIN.json')}


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def root_receipt(g):
    raw=g.verify_pin(NS+'ROOT_RETAINED3.json',ROOT_PIN)
    exact(raw,g.read(ROOT_PATH,ROOT_HEAD),'FREE_FOCUSED_EXACT_PUBLISHED_ROOT_RETENTION_BYTES')
    value=strict(raw)
    fields(value,dict(status='ROOT_RETAINED_FREE3_NOT_AGGREGATE_PASS',head=retained.HEAD,tree=retained.TREE,
        run_id=retained.RUN,job_id=retained.JOB,artifact_id=retained.ARTIFACT,archive=retained.ARCHIVE,
        retained_Native_cases=3,actual_new_Native_cases=0,actual_new_browser_cases=0,
        retained_cases_are_not_fresh=True,retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
        package_all_five=False,complete3_qualified=False,missing_committed_use_and_inverse_refusal=True,
        actual_outer_restoration_verified=True,actual_backup_restore_verified=True,
        actual_primary_unchanged=True,actual_advisors_equal=True,failed_worker_reaped=True,
        source_invariant_reuse_required=True,all_five_new_package_gates_still_required=True,
        production_go=False,independent_acceptance=False),'FREE_FOCUSED_EXACT_ACTUAL_RETAINED3_NO_AGGREGATE_PASS')
    return value


def source(g):
    require(bool(CHANGED_PINS),'FREE_FOCUSED_REVIEWED_EXACT_SOURCE_PINS_REQUIRED')
    declaration=strict(g.read(NS+'SOURCE.json'))
    allowed=set(declaration['files'])|{NS+'SOURCE.json'}
    exact(len(allowed),45,'FREE_FOCUSED_EXACT_CLOSED_OWN45')
    exact(len(declaration['files']),44,'FREE_FOCUSED_EXACT44_PINS')
    for name,value in declaration['files'].items():g.verify_pin(name,value)
    for name,value in CHANGED_PINS.items():g.verify_pin(name,value)
    with GitBytes(g.root,retained.HEAD,retained.TREE)as old:
        origin=original.source(old);before=strict(old.read(NS+'SOURCE.json'))
        exact(set(g.tree)-set(old.tree),NEW,'FREE_FOCUSED_ONLY_FOUR_NEW_OWN_FILES')
        changed={name for name in old.tree if g.tree.get(name)!=old.tree[name]}
        exact(changed,set(CHANGED_PINS)-NEW,'FREE_FOCUSED_ONLY_EIGHT_REVIEWED_OLD_FILES_CHANGED')
        for name in set(old.tree)-changed:
            exact(g.tree.get(name),old.tree[name],'FREE_FOCUSED_ALL_OTHER_BLOBS_AND_MODES_UNCHANGED:'+name)
        record=strict(g.read(NS+'FOCUSED_COMMITTED_ORIGIN.json'))
        fields(record,dict(classification='FREE3_EXACT_RETAINED_CASES_AND_EMPTY_CLONE_ORIGINAL_SEED_COMMITTED_WITNESS_SUCCESSOR',
            origin_head=retained.HEAD,origin_tree=retained.TREE,Root_head=ROOT_HEAD,Root_tree=ROOT_TREE,
            Root_receipt=ROOT_PIN,retained_Native_cases=3,actual_new_Native_cases=0,financial_groups_rerun=False,
            product_graph_or_business_case_bodies_changed=False,original_fixture_or_strict_runner_changed=False,
            existing_actor_promoted=False,all_five_new_package_gates_required=True,
            exact_counted_reversible_routes=20,every_original_modified_file_byte_recovered=True,
            production_go=False,independent_acceptance=False),'FREE_FOCUSED_EXACT_COMMITTED_WITNESS_SOURCE_REPAIR')
        exact(set(record['files']),changed-{NS+'SOURCE.json'},'FREE_FOCUSED_EXACT_SEVEN_ROUTED_FILES')
        routes=0
        for name,item in record['files'].items():
            raw=old.read(name);exact(pin(raw),item['before'],'FREE_FOCUSED_ORIGINAL_BYTE_PIN:'+name)
            current=g.read(name);exact(pin(current),item['after'],'FREE_FOCUSED_DERIVED_BYTE_PIN:'+name)
            text=raw.decode()
            for route in item['changes']:
                exact(route['count'],1,'FREE_FOCUSED_EVERY_ROUTE_SINGLE_OCCURRENCE')
                exact(text.count(route['before']),1,'FREE_FOCUSED_EXACT_ROUTE_BEFORE_ANCHOR')
                text=text.replace(route['before'],route['after'],1);routes+=1
            exact(text.encode(),current,'FREE_FOCUSED_ONLY_DECLARED_SOURCE_ROUTES:'+name)
            for route in reversed(item['changes']):
                exact(text.count(route['after']),1,'FREE_FOCUSED_EXACT_ROUTE_INVERSE_ANCHOR')
                text=text.replace(route['after'],route['before'],1)
            exact(text.encode(),raw,'FREE_FOCUSED_ENTIRE_ORIGINAL_SOURCE_RECOVERED:'+name)
        exact(routes,20,'FREE_FOCUSED_EXACT_TWENTY_REVERSIBLE_ROUTES')
        expected=dict(before);expected['files']=dict(before['files'],**{n:v for n,v in CHANGED_PINS.items()if n!=NS+'SOURCE.json'})
        expected['focused_committed_witness_successor']=dict(origin=NS+'FOCUSED_COMMITTED_ORIGIN.json',
            retained_Native_cases=3,actual_new_Native_cases=0,financial_groups_rerun=False)
        exact(declaration,expected,'FREE_FOCUSED_ONLY_REVIEWED_SOURCE_PINS_AND_FOCUSED_DECLARATION')
        exact(g.read(NS+'native_free.py'),old.read(NS+'native_free.py'),'FREE_FOCUSED_ALL_THREE_NATIVE_CASE_BODIES_UNCHANGED')
        for name in('money','posted','case_boundary'):
            def function(raw):return next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name==name)
            exact(ast.dump(function(g.read(NS+'final_gate.py'))),ast.dump(function(old.read(NS+'final_gate.py'))),
                'FREE_FOCUSED_ORIGINAL_PURE_FINANCIAL_ORACLE_UNCHANGED:'+name)
        def case_statements(raw):
            fn=next(n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef)and n.name=='validate')
            start=next(i for i,n in enumerate(fn.body)if isinstance(n,ast.Expr)and isinstance(n.value,ast.Call)
                and isinstance(n.value.func,ast.Attribute)and n.value.func.attr=='fields'
                and isinstance(n.value.args[0],ast.Name)and n.value.args[0].id=='raw')
            stop=next(i for i,n in enumerate(fn.body)if isinstance(n,ast.Assign)
                and any(isinstance(t,ast.Name)and t.id=='used'for t in n.targets))
            return [ast.dump(n)for n in fn.body[start:stop]]
        exact(case_statements(g.read(NS+'final_gate.py')),case_statements(old.read(NS+'final_gate.py')),
            'FREE_FOCUSED_ALL_ORIGINAL_CASE_ASSERTIONS_UNCHANGED')
        exercise=next(n for n in ast.parse(g.read(NS+'component.py')).body
            if isinstance(n,ast.FunctionDef)and n.name=='exercise')
        require(not any(isinstance(n,ast.Call)and isinstance(n.func,ast.Attribute)and n.func.attr=='strict_group'
            for n in ast.walk(exercise)),'FREE_FOCUSED_COMPLETED_STRICT_GROUP_CANNOT_RUN_AGAIN')
    receipt=root_receipt(g)
    bindings=dict(ROOT_HEAD=ROOT_HEAD,ROOT_TREE=ROOT_TREE,ROOT_PATH=ROOT_PATH,ROOT_PIN=ROOT_PIN,
        ORIGIN_HEAD=retained.HEAD,ORIGIN_TREE=retained.TREE,RUN=retained.RUN,JOB=retained.JOB,
        ARTIFACT=retained.ARTIFACT,ARCHIVE=retained.ARCHIVE,
        NATIVE_SOURCE_PIN=pin(g.read(NS+'native_free.py')))
    for name,value in bindings.items():exact(literal(g,NS+'retained3.py',name),value,'FREE_FOCUSED_EXACT_RETENTION_BINDING:'+name)
    exact(g.read(original.WORKFLOW),g.read(NS+'native3.workflow.yml.txt'),'FREE_FOCUSED_ACTIVE_WORKFLOW_EQUALS_REVIEWED_TEMPLATE')
    return dict(status='EXACT_FREE45_RETAINED3_AND_MISSING_COMMITTED_WITNESS_SOURCE_ONLY',own_paths=45,
        source_pins=44,unchanged_base=14265,unchanged_original_own_paths=33,reversible_routes=20,
        original_source=origin,root_receipt=ROOT_PIN,retained_Native_cases=3,actual_Native_cases=0,
        business_case_sources_and_original_assertions_unchanged=True,financial_groups_rerun=False,
        product_SQL_or_graph_changed=False,original_seed_API_unchanged=True,existing_actor_promoted=False,
        actual_ERP_cases=0,production_go=False,independent_acceptance=False)


def reuse(value,receipt):
    fields(value,dict(status='ROOT_VALIDATED_FREE3_RETAINED_BY_COMPLETE_SOURCE_IDENTITY',root_head=ROOT_HEAD,
        root_tree=ROOT_TREE,root_path=ROOT_PATH,root_receipt=ROOT_PIN,original_head=retained.HEAD,
        original_tree=retained.TREE,original_run_id=retained.RUN,original_job_id=retained.JOB,
        artifact_id=retained.ARTIFACT,archive=retained.ARCHIVE,original_native=receipt['originals'][original.RAW],
        retained_Native_cases=3,actual_new_Native_cases=0,retained_cases_are_not_fresh=True,
        financial_groups_rerun=False,retained_case_ids=original.IDS,
        qualified_complete_DE_FREE_date_sources=receipt['qualified_complete_DE_FREE_date_sources'],
        source_invariant_reuse=True,retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,
        all_five_new_package_gates_still_required=True,production_go=False,independent_acceptance=False),
        'FREE_FOCUSED_EXACT_HONEST_SOURCE_INVARIANT_RETENTION')


def intake(root,path,metadata):
    require(all(v is not None for v in(HEAD,TREE,RUN,JOB)),'FREE_FOCUSED_ACTUAL_OWNING_RUN_AND_JOB_NOT_YET_PINNED')
    fields(metadata,dict(head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,run_attempt=1,conclusion='success',expired=False),
        'FREE_FOCUSED_EXACT_TERMINAL_SUCCESS_METADATA')
    require(type(metadata['artifact_id'])is int and metadata['artifact_id']>0,'FREE_FOCUSED_ACTUAL_ARTIFACT_ID')
    expected=metadata['archive'];path=Path(path)
    exact(path.stat().st_size,expected['bytes'],'FREE_FOCUSED_CANONICAL_SIZE')
    with path.open('rb')as stream:exact(file_digest(stream,'sha256').hexdigest(),expected['sha256'],'FREE_FOCUSED_CANONICAL_DIGEST')
    with GitBytes(root,HEAD,TREE)as g,zipfile.ZipFile(path)as z:
        admitted=source(g);receipt=root_receipt(g);names=z.namelist()
        exact(len(set(names)),len(names),'FREE_FOCUSED_NO_DUPLICATE_CANONICAL_MEMBERS')
        for name in names:safe_path(name)
        require(z.testzip()is None,'FREE_FOCUSED_COMPLETE_CANONICAL_CRC');pins={}
        def read(name):
            raw=z.read(name);pins[name]=pin(raw);return strict(raw)
        main=read(original.MAIN);raw=read(original.RAW);package=read('T3_PACKAGE_INSTALL.json')
        backup=read('T3_BACKUP_RESTORE_DRILL.json');supervised=read('FREE_DATE_RUNTIME_SUPERVISION.json')
        fields(supervised,dict(status='WORKER_COMPLETED_AND_REAPED',qualification_commit=HEAD,
            github_run_id=str(RUN),github_run_attempt='1',worker_exit=0,deadline_reached=False,
            external_signal=None,orphaned_child=False,process_group_empty=True,process_tree_empty=True,
            signals=[],actual_case_credit=0,production_go=False,job_budget_seconds=21600,
            work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600),
            'FREE_FOCUSED_CURRENT_WORKER_COMPLETED_AND_REAPED')
        pure,validator=original.report_validator(g)
        gate=pure.validate(SimpleNamespace(fields=fields,exact=exact,GATES=original.GATES),
            main,raw,package,backup,original.IDS,HEAD)
        fields(gate,dict(status='CURRENT_COMPLETE_DE_FREE_DATE_RETAINED3_COMMITTED_ALL5_PASS',
            actual_fresh_cases=0,retained_Native_cases=3,candidate_case_coverage=3,
            retained_cases_are_not_fresh=True,financial_groups_rerun=False,source_invariant_reuse=True,
            prior_runs_aggregated=True),'FREE_FOCUSED_ORIGINAL_CASES_AND_NEW_COMPLETE_PACKAGE_GATES')
        exact(pins[original.RAW],receipt['originals'][original.RAW],'FREE_FOCUSED_RAW_CASE_ORIGINAL_BYTES_UNCHANGED')
        part=main['committed'][original.CASE];reuse(part['retained_FREE3'],receipt)
        exact(main['source_declaration']['retained_FREE3'],part['retained_FREE3'],'FREE_FOCUSED_SOURCE_AND_RUNTIME_SAME_RETENTION')
        archive_admission=read('FREE3_RETAINED_ORIGINAL_ADMISSION.json')
        exact(part['retained3_original_admission'],archive_admission,'FREE_FOCUSED_EMBEDDED_ORIGINAL_CANONICAL_ADMISSION')
        fields(archive_admission,dict(status='EXACT_FAILED_CANONICAL_FREE3_ORIGINALS_ADMITTED_NOT_RERUN',
            root_receipt=ROOT_PIN,original_head=retained.HEAD,original_run_id=retained.RUN,
            original_job_id=retained.JOB,artifact_id=retained.ARTIFACT,archive=retained.ARCHIVE,
            original_native=receipt['originals'][original.RAW],retained_Native_cases=3,actual_new_Native_cases=0,
            financial_groups_rerun=False,retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False),
            'FREE_FOCUSED_ORIGINAL_ARCHIVE_BOUND_BEFORE_REUSE')
        used=part['separate_committed_Native_use']
        fields(used,dict(existing_actor_promoted=False),'FREE_FOCUSED_NO_EXISTING_ACTOR_PROMOTION')
        require(type(used['original_fixture_seeded_on_empty_clone'])is bool,'FREE_FOCUSED_TYPED_ORIGINAL_FIXTURE_SEED_OBSERVATION')
        pure.posted(SimpleNamespace(fields=fields),used['posted_snapshot'],used['actual_issue_id'],used['physical_at'])
        delta={key:pure.money(value)for key,value in used['ledger_delta'].items()}
        require(delta.get('MATERIAL_INVENTORY')==-6 and sum(delta.values())==0
            and all(delta.get(k,0)==0 for k in('CONTRACTOR_RECEIVABLE','CASH','BANK','OTHER_INCOME')),
            'FREE_FOCUSED_NEW_COMMITTED_WITNESS_EXACT_STOCK_GL_ECONOMICS')
        boundary=full_census(used['before']['actual_all22'],used['before']['full_data_and_sequences'])
        fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'FREE_FOCUSED_ALL_ROLES_RESTORED')
        fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,
            database_owner_acl_and_settings_preserved=True),'FREE_FOCUSED_COMPLETE_OUTER_RESTORATION')
        graph=main['source_declaration']['current_installation'];maps=declared_files(g,graph)
        exact(pin(canonical(graph)),receipt['qualified_complete_DE_FREE_date_sources'],'FREE_FOCUSED_ENTIRE_PRODUCT_GRAPH_REUSE')
        return dict(status='ROOT_VERIFIED_CURRENT_COMPLETE_DE_FREE_DATE_RETAINED3_COMMITTED_ALL5',
            head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,artifact_id=metadata['artifact_id'],
            archive=dict(expected,members=len(names)),originals=pins,source_admission=admitted,
            pure_report_validator=validator,actual_product_source_maps=maps,
            qualified_complete_DE_FREE_date_sources=pin(canonical(graph)),runtime_supervision=supervised,
            actual_Native_cases=0,actual_business_cases=0,actual_browser_cases=0,actual_Auth_HTTP_cases=0,
            actual_two_session_races=0,retained_Native_cases=3,retained_cases_are_not_fresh=True,
            candidate_case_coverage=3,complete3_qualified=True,package_all_five=True,
            source_invariant_reuse=True,prior_runs_aggregated=True,financial_groups_rerun=False,
            retained_original_run_conclusion='failure',failed_run_relabelled_PASS=False,retained_root_receipt=ROOT_PIN,
            actual_new_committed_witness=True,actual_used_refusal_raw_boundary=boundary,
            retained_actual_full22_case_boundaries=receipt['actual_full22_case_boundaries'],
            retained_DE30_fresh_case_credit=0,GOOD_eligibility_policy_decided=False,
            Afui_GOOD_nonpayable_path_complete=False,D_complete=False,E_complete=False,
            global_writer_or_permission_or_lock_closure=False,production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--check-source',action='store_true')
    p.add_argument('--archive',type=Path);p.add_argument('--artifact-metadata',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.check_source:
        with GitBytes(a.source,HEAD or PREPARED_HEAD,TREE or PREPARED_TREE)as g:value=source(g)
        print(json.dumps(value))
    else:
        require(all((a.archive,a.artifact_metadata,a.output)),'FREE_FOCUSED_CANONICAL_METADATA_AND_OUTPUT_REQUIRED')
        value=intake(a.source,a.archive,strict(a.artifact_metadata.read_bytes()))
        with a.output.open('x')as out:out.write(json.dumps(value,indent=2)+'\n')
        print(json.dumps(dict(status=value['status'],retained_Native_cases=3,actual_fresh_Native_cases=0)))
