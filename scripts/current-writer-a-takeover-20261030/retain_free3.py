"""Retain the actual three FREE cases; the committed-witness failure stays failed.

Only original canonical bytes and exact source are read. No ERP import,
database, Auth, runtime retry, or synthetic successful report is produced.
"""
from pathlib import Path
from hashlib import file_digest
from types import SimpleNamespace
import argparse,ast,json,zipfile
import intake_free3 as original
from intake_common import GitBytes,exact,fields,pin,require,safe_path
from intake_sku27 import strict,group,full_census
from current_graph_sources import declared_files

HEAD='ad986b9a9d432f2ffac2b961710c3852c6c2ef90'
TREE='80bc5471330b89497991ba1e67615287b01e59c1'
RUN=41388877929
JOB=125095681990
ARTIFACT=13119648673
ARCHIVE=dict(bytes=28320283,sha256='8827d2262f51781fd7f3be977192ba7f315ee9d5b94444546121b723a9dbdc9d',members=127)
ERROR='FREE_DATE_NATIVE_ORIGINAL_ACTIVE_OWNER_REQUIRED_WITHOUT_PROMOTION'


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def case_validator(g):
    """Execute the unchanged actual case-only statements of the original gate.

    The surrounding aggregate and missing committed witness are deliberately
    NOT fed a fabricated PASS. Every original case assertion remains present.
    """
    pure,proof=original.report_validator(g)
    raw=g.read(original.NS+'final_gate.py');tree=ast.parse(raw)
    validate=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='validate')
    first=[i for i,n in enumerate(validate.body)if isinstance(n,ast.Expr)
        and isinstance(n.value,ast.Call)and isinstance(n.value.func,ast.Attribute)
        and n.value.func.attr=='fields'and n.value.args and isinstance(n.value.args[0],ast.Name)
        and n.value.args[0].id=='raw']
    last=[i for i,n in enumerate(validate.body)if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Name)and t.id=='used'for t in n.targets)]
    exact(len(first),1,'EXACT_ORIGINAL_CASE_GATE_START');exact(len(last),1,'EXACT_ORIGINAL_COMMITTED_GATE_START')
    require(first[0]<last[0],'ORIGINAL_CASE_GATE_PRECEDES_COMMITTED_WITNESS')
    body=validate.body[first[0]:last[0]]
    fn=ast.FunctionDef(name='validate_actual_retained_cases',
        args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=n)for n in('p','raw','ids')],
            kwonlyargs=[],kw_defaults=[],defaults=[]),body=body,decorator_list=[])
    program=ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[]))
    namespace=dict(pure.__dict__);exec(compile(program,'<exact-original-FREE3-case-gate>','exec'),namespace)
    return namespace[fn.name],dict(original_gate=pin(raw),original_pure_gate=proof,
        original_statement_range=[first[0],last[0]],original_case_assertion_statements=len(body),
        original_case_AST=pin(ast.dump(program,include_attributes=False).encode()),
        original_report_modified=False,synthetic_successful_report=False)


def intake(root,path,metadata):
    run=metadata['run'];fields(run,dict(id=RUN,head_sha=HEAD,run_attempt=1,status='completed',
        conclusion='failure',event='push'),'EXACT_FAILED_FREE41_TERMINAL_RUN_API')
    fields(run['head_commit'],dict(id=HEAD,tree_id=TREE),'EXACT_FAILED_FREE41_TREE_API')
    jobs=metadata['jobs'];require(type(jobs)is list and len(jobs)==1,'EXACT_ONE_FAILED_FREE41_JOB')
    fields(jobs[0],dict(id=JOB,run_id=RUN,status='completed',conclusion='failure'),'EXACT_FAILED_FREE41_JOB_API')
    exact([(s['number'],s['name'])for s in jobs[0]['steps']if s['conclusion']=='failure'],
        [(71,'Run Native FREE date3 and complete outer restoration')],'ONLY_FREE41_NATIVE_OUTER_STEP_FAILED')
    artifact=metadata['artifact'];fields(artifact,dict(id=ARTIFACT,expired=False,size_in_bytes=ARCHIVE['bytes'],
        digest='sha256:'+ARCHIVE['sha256']),'EXACT_FAILED_FREE41_FULL_CANONICAL_API')
    fields(artifact['workflow_run'],dict(id=RUN,head_sha=HEAD),'FREE41_CANONICAL_ACTUAL_ORIGIN')
    path=Path(path);exact(path.stat().st_size,ARCHIVE['bytes'],'FREE41_FULL_ORIGINAL_ARCHIVE_SIZE')
    with path.open('rb')as stream:exact(file_digest(stream,'sha256').hexdigest(),ARCHIVE['sha256'],'FREE41_FULL_ORIGINAL_ARCHIVE_DIGEST')
    with GitBytes(root,HEAD,TREE)as g,zipfile.ZipFile(path)as z:
        names=z.namelist();exact(len(names),ARCHIVE['members'],'FREE41_ALL_ORIGINAL_MEMBERS')
        exact(len(set(names)),len(names),'FREE41_NO_DUPLICATE_ORIGINALS')
        for name in names:safe_path(name)
        require(z.testzip()is None,'FREE41_FULL_ORIGINAL_ARCHIVE_CRC')
        pins={}
        def read(name):
            raw=z.read(name);pins[name]=pin(raw);return strict(raw)
        main=read(original.MAIN);native=read(original.RAW);package=read('T3_PACKAGE_INSTALL.json')
        backup=read('T3_BACKUP_RESTORE_DRILL.json');supervised=read('FREE_DATE_RUNTIME_SUPERVISION.json')
        admitted=original.source(g)
        fields(main,dict(status='INCOMPLETE',qualification_commit=HEAD,required_case_ids=[original.CASE],
            required_case_ids_pass=False,error=ERROR,baseline_full22_all_rows_all_sequences_equal=True,
            restore_raw_public_equal=True,cp6_restored=True,baseline_advisors_equal=True,advisor_gate=True,
            production_go=False,independent_acceptance=False),'ORIGINAL_FREE41_FAILURE_NOT_RELABELED_PASS')
        exact(set(main['committed']),{original.CASE},'ONE_ACTUAL_FREE41_COMPONENT')
        part=main['committed'][original.CASE]
        fields(part,dict(status='INCOMPLETE',actual_Native_cases=0,actual_browser_cases=0,
            actual_Auth_HTTP_cases=0,actual_two_session_races=0,retained_DE30_fresh_case_credit=0,
            production_go=False,independent_acceptance=False),'FAILED_COMPONENT_GRANTS_NO_AGGREGATE_CREDIT')
        require('separate_committed_Native_use'not in part,'MISSING_COMMITTED_WITNESS_NOT_INVENTED')
        exact(part['native'],native,'ORIGINAL_FREE3_EMBEDDED_EQUALS_COMPLETE_STRICT_ORIGINAL')
        exact(part['strict_group_originals'],[dict(name=original.RAW,**pins[original.RAW])],
            'EXACT_STRICT_ORIGINAL_PRODUCER_BYTE_BINDING')
        trace=main['traceback'];require(type(trace)is str and 'component.py' in trace
            and 'committed_use' in trace and 'native_free.py' in trace and 'bridge.post_one' in trace
            and trace.rstrip().endswith('ValueError: '+ERROR),'EXACT_POST_CASE_COMMITTED_SETUP_FAILURE')
        validate,validator=case_validator(g);validate(SimpleNamespace(fields=fields,exact=exact),native,original.IDS)
        group(native,original.IDS);boundaries={}
        for key,row in native['cases'].items():
            b=row['actual_full22_case_boundary']
            boundaries[key]=dict(before=full_census(b['before']['actual_all22'],b['before']['full_data_and_sequences']),
                after=full_census(b['after']['actual_all22'],b['after']['full_data_and_sequences']),
                audited_sequence_boundary=b['verification'])
        exact(package['gate'],dict(installed=True,primary_unchanged=True,backup_restore_drill=True,
            security_advisors=True,writer_runtime=False),'FREE41_FOUR_PACKAGE_GATES_NOT_ALL5')
        fields(package['run_identity'],dict(tool_head=HEAD,github_sha=HEAD,run_id=str(RUN),run_attempt='1'),
            'EXACT_FAILED_FREE41_PACKAGE_ORIGIN')
        fields(backup,dict(status='RESTORED_IDENTICAL'),'FREE41_ORIGINAL_BACKUP_RESTORE')
        require(bool(backup['checks'])and all(type(v)is bool and v for v in backup['checks'].values()),'FREE41_ALL_TYPED_BACKUP_CHECKS')
        exact(backup['data']['differ'],{},'FREE41_NO_BACKUP_DATA_DIFFERENCE')
        fields(main['baseline_role_cleanup'],dict(baseline_roles_exact=True),'FREE41_ALL_ROLES_RESTORED')
        fields(main['baseline_restore'],dict(unexplained=[],only_pg_cron_errors=True,
            database_owner_acl_and_settings_preserved=True),'FREE41_COMPLETE_OUTER_RESTORATION')
        fields(supervised,dict(status='INCOMPLETE',qualification_commit=HEAD,github_run_id=str(RUN),
            github_run_attempt='1',worker_exit=1,signals=[],deadline_reached=False,external_signal=None,
            orphaned_child=False,process_group_empty=True,process_tree_empty=True,job_budget_seconds=21600,
            work_budget_seconds=19800,recovery_reserve_seconds=1200,artifact_reserve_seconds=600,
            actual_case_credit=0,production_go=False),'FREE41_FAILED_WORKER_REAPED_WITHOUT_DEADLINE')
        graph=main['source_declaration']['current_installation'];maps=declared_files(g,graph)
        parent_raw=g.read(original.NS+'DE30_PARENT_ROOT_ACTUAL_INTAKE.json');parent=strict(parent_raw)
        exact(pin(parent_raw),original.literal(g,original.NS+'admission.py','PARENT_RECEIPT'),'FREE41_ACTUAL_DE30_ROOT_PARENT_PIN')
        exact(pin(canonical(graph['parent'])),parent['qualified_complete_DE_sources'],'FREE41_ENTIRE_ACCEPTED_DE30_GRAPH')
        return dict(status='ROOT_RETAINED_FREE3_NOT_AGGREGATE_PASS',head=HEAD,tree=TREE,run_id=RUN,job_id=JOB,
            artifact_id=ARTIFACT,archive=ARCHIVE,originals=pins,source_admission=admitted,
            original_case_validator=validator,actual_product_source_maps=maps,
            qualified_complete_DE_FREE_date_sources=pin(canonical(graph)),
            retained_Native_cases=3,actual_new_Native_cases=0,actual_new_browser_cases=0,
            retained_cases_are_not_fresh=True,retained_case_ids=original.IDS,
            actual_full22_case_boundaries=boundaries,retained_original_run_conclusion='failure',
            failed_run_relabelled_PASS=False,package_all_five=False,complete3_qualified=False,
            actual_outer_restoration_verified=True,actual_backup_restore_verified=True,
            actual_primary_unchanged=True,actual_advisors_equal=True,failed_worker_reaped=True,
            missing_committed_use_and_inverse_refusal=True,missing_error=ERROR,
            source_invariant_reuse_required=True,all_five_new_package_gates_still_required=True,
            production_go=False,independent_acceptance=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--archive',type=Path,required=True);p.add_argument('--metadata',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    value=intake(a.source,a.archive,strict(a.metadata.read_bytes()))
    with a.output.open('x')as out:out.write(json.dumps(value,indent=2)+'\n')
    print(json.dumps(dict(status=value['status'],retained_Native_cases=3,actual_new_cases=0,
        package_all_five=False,failed_run_relabelled_PASS=False)))
