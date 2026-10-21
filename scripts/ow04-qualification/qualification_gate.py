"""Require both complete runtime groups after independent disposable entries."""
from pathlib import Path
import hashlib,json,os,subprocess,sys


def require(root,candidate,step_outcomes=None):
    assert step_outcomes=={'HTTP':'success','RACES':'success'},('OW04_FINAL_COMMAND_OUTCOME',step_outcomes)
    expected_dir=Path(__file__).resolve().parent
    binding_bytes=(expected_dir/'QUALIFIED_CORE.json').read_bytes()
    binding=json.loads(binding_bytes)
    assert binding.get('status')=='PASS'and binding.get('native_case_count')in(63,73,87),'OW04_FINAL_NATIVE_NOT_QUALIFIED'
    full=binding['native_case_count']in(73,87)
    expected_binding=dict(**binding,binding_sha256=hashlib.sha256(binding_bytes).hexdigest())
    admin_path=expected_dir.parent/'cp7_ow04_restore_bundle.py'
    if admin_path.is_file():
        declared=expected_dir.parents[1]/'docs/cp7/d17-14/ow04/USED_RESTORE_QUALIFICATION.json'
        assert declared.is_file()and binding['native_case_count']==87,'OW04_FINAL_ADMIN_RESTORE_DECLARATION_REQUIRED'
        admin=json.loads(declared.read_bytes()).get('separate_administrative_source',{})
        raw=admin_path.read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        assert admin.get('path')=='scripts/cp7_ow04_restore_bundle.py' \
            and admin.get('native_runtime_covered')is False \
            and admin.get('classification')=='SEPARATE_ADMIN_RESTORE_REQUIRES_OWN_ACTUAL_RUNTIME' \
            and admin.get('sha256')==hashlib.sha256(raw).hexdigest() \
            and admin.get('git_blob')==blob,'OW04_FINAL_ADMIN_RESTORE_SOURCE_CHANGED'
        expected_binding['separately_bound_administrative_source']=admin
    counts={};reports={}
    for label,file,group,declaration,count in (
        ('HTTP','CP7_OW04_HTTP.json','http','EXPECTED.json',18 if full else 14),
        ('RACES','CP7_OW04_RACES.json','races','RACE_EXPECTED.json',6)):
        declaration_bytes=(expected_dir/declaration).read_bytes()
        ids=[r['id']for r in json.loads(declaration_bytes)['cases']]
        initial_ids=list(ids)
        source_ids=[]
        if label=='HTTP':
            source_bytes=(expected_dir/'SOURCE_HTTP_EXPECTED.json').read_bytes()
            assert hashlib.sha256(source_bytes).hexdigest()=='58ee491c469a08ede6c3751353cd4a373804c4df6898cf447f8f93b75d167140','OW04_FINAL_SOURCE_DECLARATION_CHANGED'
            source=json.loads(source_bytes)
            source_ids=[r['id']for r in source['cases']]
            assert len(initial_ids)==8 and len(source_ids)==6 and source['required_native_count']==63,'OW04_FINAL_SOURCE_DECLARATION_COUNT'
            ids+=source_ids
            if full:
                dependency_bytes=(expected_dir/'DEPENDENCY_HTTP_EXPECTED.json').read_bytes()
                dependency=json.loads(dependency_bytes)
                dependency_ids=[r['id']for r in dependency['cases']]
                assert dependency['required_full_native_count']==73 and dependency['case_count']==len(dependency_ids)==4 and dependency['total_http_count']==18,'OW04_FINAL_DEPENDENCY_DECLARATION_COUNT'
                assert not(set(dependency_ids)&set(ids)),'OW04_FINAL_DEPENDENCY_ID_COLLISION'
                ids+=dependency_ids
        assert len(ids)==len(set(ids))==count,('OW04_FINAL_DECLARATION_CHANGED',label)
        report=json.loads((Path(root)/file).read_text());runtime=report.get(group,{})
        rows=runtime.get('cases'if label=='HTTP'else'races',{})
        assert report.get('candidate_commit')==candidate,('OW04_FINAL_CANDIDATE_CHANGED',label)
        assert report.get('reused_native_binding')==expected_binding,('OW04_FINAL_NATIVE_BINDING_CHANGED',label)
        assert report.get('predeclared_case_sha256')==hashlib.sha256(declaration_bytes).hexdigest(),('OW04_FINAL_DECLARATION_HASH_CHANGED',label)
        assert report.get('core_directory_tree')==binding['core_directory_tree'],('OW04_FINAL_CORE_CHANGED',label)
        assert report.get('native_probe_blob')==binding['native_probe_blob'],('OW04_FINAL_NATIVE_PROBE_CHANGED',label)
        assert report.get('status')=='PASS'and report.get('expected_case_count')==count and report.get('observed_case_count')==count,('OW04_FINAL_INCOMPLETE',label)
        assert report.get('required_case_ids')==ids,('OW04_FINAL_REQUIRED_CASE_IDS',label)
        assert report.get('cp6_restored')is True and report.get('advisor_gate')is True,('OW04_FINAL_RESTORE_OR_ADVISOR',label)
        assert runtime.get('status')in('PASS','RUN_COMPLETE')and runtime.get('counts')=={'PASS':count},('OW04_FINAL_COUNTS',label)
        assert set(rows)==set(ids)and all(r.get('status')=='PASS'for r in rows.values()),('OW04_FINAL_CASE_SET',label)
        assert runtime.get('database_remaining')==0,('OW04_FINAL_DATABASE_REMAINS',label)
        if label=='HTTP':
            assert report.get('source_predeclared_case_sha256')==hashlib.sha256(source_bytes).hexdigest(),'OW04_FINAL_SOURCE_DECLARATION_HASH'
            assert report.get('initial_required_case_ids')==initial_ids and report.get('source_required_case_ids')==source_ids,'OW04_FINAL_SOURCE_SUBGROUP_MEMBERSHIP'
            assert report.get('expected_subgroup_counts')==({'INITIAL':8,'SOURCE':6,'DEPENDENCY':4}if full else{'INITIAL':8,'SOURCE':6}),'OW04_FINAL_SOURCE_SUBGROUP_COUNTS'
            for key,name in (('http_cases_sha256','cp7_ow04_http_cases.py'),('source_http_cases_sha256','cp7_ow04_source_http_cases.py'),
                             ('http_composition_sha256','cp7_ow04_all_http_cases.py'),('transport_probe_sha256','transport_probe.py')):
                assert report.get(key)==hashlib.sha256((expected_dir/name).read_bytes()).hexdigest(),('OW04_FINAL_HTTP_IMPLEMENTATION_CHANGED',key)
            if full:
                assert report.get('dependency_predeclared_case_sha256')==hashlib.sha256(dependency_bytes).hexdigest(),'OW04_FINAL_DEPENDENCY_DECLARATION_HASH'
                assert report.get('dependency_required_case_ids')==dependency_ids,'OW04_FINAL_DEPENDENCY_CASE_SET'
                assert report.get('dependency_http_cases_sha256')==hashlib.sha256((expected_dir/'cp7_ow04_dependency_http_cases.py').read_bytes()).hexdigest(),'OW04_FINAL_DEPENDENCY_IMPLEMENTATION_CHANGED'
            assert(runtime.get('auth_counts')or{}).get('restored')is True and not runtime.get('cleanup_failures'), 'OW04_FINAL_AUTH_NOT_RESTORED'
        else:
            source_race_bytes=(expected_dir/'SOURCE_RACE_EXPECTED.json').read_bytes()
            assert hashlib.sha256(source_race_bytes).hexdigest()=='6d1ccc9252446a2cd99b4b605fea5328e195c06cf3cb8e485bbc4544de2d8fb1','OW04_FINAL_SOURCE_RACE_DECLARATION_CHANGED'
            source_race_declaration=json.loads(source_race_bytes)
            source_race_ids=[r['id']for r in source_race_declaration['cases']]
            assert source_race_declaration['required_actual_native_case_count']==63 \
                and len(source_race_ids)==len(set(source_race_ids))==2 and not(set(source_race_ids)&set(ids)),'OW04_FINAL_SOURCE_RACE_DECLARATION_COUNT'
            assert report.get('source_predeclared_case_sha256')==hashlib.sha256(source_race_bytes).hexdigest(),'OW04_FINAL_SOURCE_RACE_DECLARATION_HASH'
            assert report.get('source_proposal_source_candidate')==source_race_declaration['candidate'],'OW04_FINAL_SOURCE_RACE_PROPOSAL_PROVENANCE'
            preserved={name:source_race_declaration[field]for name,field in(
                ('old6_cases_sha256','preserved_old6_cases_sha256'),('old6_expected_sha256','preserved_old6_expected_sha256'),
                ('signed_expected_sha256','preserved_signed_expected_sha256'),('zero_difference_expected_sha256','preserved_zero_difference_expected_sha256'))}
            assert report.get('preserved_source_race_inputs')==preserved,'OW04_FINAL_SOURCE_RACE_PRESERVED_INPUTS_CHANGED'
            assert report.get('race_cases_sha256')==preserved['old6_cases_sha256']==hashlib.sha256((expected_dir/'cp7_ow04_race_cases.py').read_bytes()).hexdigest(),'OW04_FINAL_RETAINED_RACE_IMPLEMENTATION_CHANGED'
            assert hashlib.sha256(declaration_bytes).hexdigest()==preserved['old6_expected_sha256'],'OW04_FINAL_RETAINED_RACE_DECLARATION_CHANGED'
            assert report.get('transport_entry_sha256')==hashlib.sha256((expected_dir/'transport_probe.py').read_bytes()).hexdigest(),'OW04_FINAL_RACE_TRANSPORT_ENTRY_CHANGED'
            assert report.get('source_required_case_ids')==source_race_ids \
                and report.get('expected_source_case_count')==report.get('observed_source_case_count')==2 \
                and report.get('expected_subgroup_counts')=={'RETAINED':6,'SOURCE':2} \
                and report.get('expected_total_case_count')==report.get('observed_total_case_count')==8,'OW04_FINAL_SOURCE_RACE_COUNTS'
            source_runtime=report.get('source_races',{});source_rows=source_runtime.get('races',{})
            assert source_runtime.get('status')in('PASS','RUN_COMPLETE')and source_runtime.get('counts')=={'PASS':2} \
                and set(source_rows)==set(source_race_ids)and all(r.get('status')=='PASS'for r in source_rows.values()),'OW04_FINAL_SOURCE_RACE_CASE_SET'
            assert source_runtime.get('database_remaining')==0,'OW04_FINAL_SOURCE_RACE_DATABASE_REMAINS'
            for key,name in(('source_race_cases_sha256','cp7_ow04_source_inverse_race_cases.py'),('race_probe_sha256','race_probe.py')):
                assert report.get(key)==hashlib.sha256((expected_dir/name).read_bytes()).hexdigest(),('OW04_FINAL_SOURCE_RACE_IMPLEMENTATION_CHANGED',key)
            counts['SOURCE_RACES']=2
        if full:
            assert report.get('full_backend_sha256')==hashlib.sha256((expected_dir/'full_backend.py').read_bytes()).hexdigest(),('OW04_FINAL_FULL_BACKEND_IMPLEMENTATION_CHANGED',label)
            assert (report.get('full_owning_source_manifest')or{}).get('predecessor_sql_sha256')=='e7701eaada592cfd74a8555cf4cdcb7df8d180448213d3bbf5698c3bfa025127',('OW04_FINAL_FULL_PREDECESSOR_NOT_INSTALLED',label)
        package_dir=Path(root).parent/'ow04-http-completed'if label=='HTTP'else Path(root)
        package_bytes=(package_dir/'T3_PACKAGE_INSTALL.json').read_bytes()
        package=json.loads(package_bytes);package_gate=package.get('gate',{})
        assert set(package_gate)=={'installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime'}and all(v is True for v in package_gate.values()),('OW04_FINAL_PACKAGE_GATE',label,package_gate)
        assert package.get('mode')=='install'and package.get('status')=='ALL_STAGES_INSTALLED',('OW04_FINAL_PACKAGE_STATE',label)
        counts[label]=count;reports[label]=dict(candidate=report['candidate_commit'],core=report['core_directory_tree'])
        reports[label].update(package_gate=package_gate,package_sha256=hashlib.sha256(package_bytes).hexdigest())
    return dict(label='OW04_HTTP_RACE_FINAL',status='PASS',candidate=candidate,counts=counts,
        native_reused_candidate=binding['candidate'],native_reused_case_count=binding['native_case_count'],native_rerun=False,
        reports=reports,step_outcomes=step_outcomes,
        feature_complete=False,audit_complete=False,production_go=False)


if __name__=='__main__':
    assert len(sys.argv)==2,'OW04 final gate expects only the proof directory'
    candidate=subprocess.check_output(['git','-C',str(Path(__file__).resolve().parents[2]),'rev-parse','HEAD'],text=True).strip()
    outcomes={'HTTP':os.environ.get('OW04_HTTP_STEP_OUTCOME'),'RACES':os.environ.get('OW04_RACE_STEP_OUTCOME')}
    try:result=require(Path(sys.argv[1]),candidate,outcomes)
    except Exception as error:
        result=dict(label='OW04_HTTP_RACE_FINAL',status='INCOMPLETE',candidate=candidate,error=str(error),production_go=False)
        Path(sys.argv[1]).mkdir(parents=True,exist_ok=True)
        (Path(sys.argv[1])/'OW04_HTTP_RACE_FINAL.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result),flush=True);raise
    (Path(sys.argv[1])/'OW04_HTTP_RACE_FINAL.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
