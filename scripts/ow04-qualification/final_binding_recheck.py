"""Actual final-gate counterexamples on labelled synthetic files; zero DB calls."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import tempfile

REPO=Path(__file__).resolve().parents[2]
SOURCE=REPO/'scripts/ow04-qualification/qualification_gate.py'
NODE=next(n for n in ast.parse(SOURCE.read_text()).body if isinstance(n,ast.FunctionDef)and n.name=='require')
CODE=compile(ast.Module(body=[NODE],type_ignores=[]),str(SOURCE),'exec')
GATES=('installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime')
IMPLEMENTATIONS={'http_cases_sha256':'cp7_ow04_http_cases.py','source_http_cases_sha256':'cp7_ow04_source_http_cases.py',
 'http_composition_sha256':'cp7_ow04_all_http_cases.py','transport_probe_sha256':'transport_probe.py',
 'dependency_http_cases_sha256':'cp7_ow04_dependency_http_cases.py','full_backend_sha256':'full_backend.py'}
RACE_IMPLEMENTATIONS={'source_race_cases_sha256':'cp7_ow04_source_inverse_race_cases.py','race_probe_sha256':'race_probe.py',
 'race_cases_sha256':'cp7_ow04_race_cases.py','transport_entry_sha256':'transport_probe.py','full_backend_sha256':'full_backend.py'}
sha=lambda raw:hashlib.sha256(raw).hexdigest()


def exercise(mutation):
    control_id=mutation;full87=mutation.startswith('full87:');full=mutation.startswith(('full73:','full87:'))
    if full:mutation=mutation.split(':',1)[1]
    with tempfile.TemporaryDirectory(prefix='SYNTHETIC-ow04-final-source-gate-')as folder:
        base=Path(folder);expected=base/'scripts/ow04-qualification';proof=base/'proof/t3';old_package=proof.parent/'ow04-http-completed'
        for directory in(expected,proof,old_package):directory.mkdir(parents=True,exist_ok=True)
        candidate='a'*40
        binding=dict(status='PASS',native_case_count=87 if full87 else 73 if full else 63,candidate='b'*40,core_directory_tree='c'*40,native_probe_blob='d'*40)
        if mutation=='binding_incomplete':binding['status']='INCOMPLETE'
        if mutation=='binding_unsupported32':binding['native_case_count']=32
        if mutation=='binding_old58':binding['native_case_count']=58
        if mutation=='binding_native64':binding['native_case_count']=64
        binding_bytes=(json.dumps(binding)+'\n').encode();(expected/'QUALIFIED_CORE.json').write_bytes(binding_bytes)
        admin=None
        if mutation.startswith('admin_'):
            data=b'"""Synthetic administrative restore control only."""\n'
            admin=dict(path='scripts/cp7_ow04_restore_bundle.py',sha256=sha(data),
                git_blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),
                native_runtime_covered=False,classification='SEPARATE_ADMIN_RESTORE_REQUIRES_OWN_ACTUAL_RUNTIME')
            if mutation=='admin_native_coverage_faked':admin['native_runtime_covered']=True
            (base/admin['path']).write_bytes(data+b'changed'if mutation=='admin_source_changed'else data)
            declared=base/'docs/cp7/d17-14/ow04/USED_RESTORE_QUALIFICATION.json'
            declared.parent.mkdir(parents=True)
            declared.write_text(json.dumps({'separate_administrative_source':admin}))
        for name in (*IMPLEMENTATIONS.values(),*RACE_IMPLEMENTATIONS.values()):(expected/name).write_bytes((SOURCE.parent/name).read_bytes())
        source_bytes=(SOURCE.parent/'SOURCE_HTTP_EXPECTED.json').read_bytes();(expected/'SOURCE_HTTP_EXPECTED.json').write_bytes(source_bytes)
        source_ids=[r['id']for r in json.loads(source_bytes)['cases']]
        if mutation=='source_declaration_changed':(expected/'SOURCE_HTTP_EXPECTED.json').write_bytes(source_bytes+b' ')
        race_source_bytes=(SOURCE.parent/'SOURCE_RACE_EXPECTED.json').read_bytes()
        (expected/'SOURCE_RACE_EXPECTED.json').write_bytes(race_source_bytes)
        race_source=json.loads(race_source_bytes);race_source_ids=[r['id']for r in race_source['cases']]
        if mutation=='source_race_declaration_changed':(expected/'SOURCE_RACE_EXPECTED.json').write_bytes(race_source_bytes+b' ')
        if full:
            dependency_bytes=(SOURCE.parent/'DEPENDENCY_HTTP_EXPECTED.json').read_bytes()
            (expected/'DEPENDENCY_HTTP_EXPECTED.json').write_bytes(dependency_bytes)
            dependency_ids=[r['id']for r in json.loads(dependency_bytes)['cases']]
            if mutation=='dependency_declaration_changed':
                (expected/'DEPENDENCY_HTTP_EXPECTED.json').write_bytes(dependency_bytes+b' ')
            if mutation=='dependency_count_wrong':
                changed=json.loads(dependency_bytes);changed['case_count']=3
                (expected/'DEPENDENCY_HTTP_EXPECTED.json').write_text(json.dumps(changed))
        for label,filename,group,declaration,count in(
            ('HTTP','CP7_OW04_HTTP.json','http','EXPECTED.json',18 if full else 14),('RACES','CP7_OW04_RACES.json','races','RACE_EXPECTED.json',6)):
            raw=(SOURCE.parent/declaration).read_bytes();(expected/declaration).write_bytes(raw)
            initial_ids=[r['id']for r in json.loads(raw)['cases']];ids=initial_ids+source_ids if label=='HTTP'else initial_ids
            if full and label=='HTTP':ids+=dependency_ids
            reused=dict(**copy.deepcopy(binding),binding_sha256=sha(binding_bytes))
            if admin is not None and mutation!='admin_receipt_missing':
                reused['separately_bound_administrative_source']=copy.deepcopy(admin)
            report=dict(candidate_commit=candidate,core_directory_tree=binding['core_directory_tree'],native_probe_blob=binding['native_probe_blob'],
                status='PASS',expected_case_count=count,observed_case_count=count,required_case_ids=ids,cp6_restored=True,advisor_gate=True,
                reused_native_binding=reused,predeclared_case_sha256=sha(raw))
            report[group]=dict(status='PASS',counts={'PASS':count},database_remaining=0,auth_counts={'restored':True},cleanup_failures=[])
            if full:
                report['full_owning_source_manifest']={'predecessor_sql_sha256':'e7701eaada592cfd74a8555cf4cdcb7df8d180448213d3bbf5698c3bfa025127'}
                if label=='HTTP':
                    report.update(dependency_predeclared_case_sha256=sha(dependency_bytes),
                        dependency_required_case_ids=dependency_ids.copy())
            rows_key='cases'if label=='HTTP'else'races'
            report[group][rows_key]={ident:{'status':'PASS'}for ident in ids}
            if mutation=='reports_reused44_current_binding63':report['reused_native_binding']['native_case_count']=44
            if mutation=='report_declaration_hash_wrong':report['predeclared_case_sha256']='0'*64
            if label=='HTTP':
                report.update(source_predeclared_case_sha256=sha(source_bytes),initial_required_case_ids=initial_ids,
                    source_required_case_ids=source_ids.copy(),expected_subgroup_counts=({'INITIAL':8,'SOURCE':6,'DEPENDENCY':4}if full else{'INITIAL':8,'SOURCE':6}))
                report.update({key:sha((expected/name).read_bytes())for key,name in IMPLEMENTATIONS.items()})
                if mutation=='only_old8_HTTP_rows':
                    report['expected_case_count']=report['observed_case_count']=8
                    report[group]['counts']={'PASS':8};report[group][rows_key]={ident:{'status':'PASS'}for ident in initial_ids}
                if mutation=='missing_source_HTTP_ID':report[group][rows_key].pop(source_ids[-1])
                if mutation=='source_group_collides_initial':report['source_required_case_ids'][0]=initial_ids[0]
                if mutation=='source_subgroup_count_wrong':report['expected_subgroup_counts']['SOURCE']=5
                if mutation=='source_declaration_hash_wrong':report['source_predeclared_case_sha256']='0'*64
                if mutation=='source_module_changed':report['source_http_cases_sha256']='0'*64
                if mutation=='auth_not_restored':report[group]['auth_counts']['restored']=False
                if mutation=='cleanup_failure':report[group]['cleanup_failures']=['LABELLED_SYNTHETIC_FAILURE']
                if mutation=='source_case_failed':report[group][rows_key][source_ids[0]]['status']='FAIL'
                if mutation=='required_ID_list_missing_source':report['required_case_ids']=initial_ids
            else:
                report.update(source_predeclared_case_sha256=sha(race_source_bytes),
                    source_proposal_source_candidate=race_source['candidate'],source_required_case_ids=race_source_ids.copy(),
                    expected_source_case_count=2,observed_source_case_count=2,
                    expected_subgroup_counts={'RETAINED':6,'SOURCE':2},expected_total_case_count=8,observed_total_case_count=8)
                report['preserved_source_race_inputs']={
                    'old6_cases_sha256':race_source['preserved_old6_cases_sha256'],
                    'old6_expected_sha256':race_source['preserved_old6_expected_sha256'],
                    'signed_expected_sha256':race_source['preserved_signed_expected_sha256'],
                    'zero_difference_expected_sha256':race_source['preserved_zero_difference_expected_sha256']}
                report.update({key:sha((expected/name).read_bytes())for key,name in RACE_IMPLEMENTATIONS.items()})
                if mutation=='retained_race_hash_wrong':report['race_cases_sha256']='0'*64
                if mutation=='retained_race_hash_missing':report.pop('race_cases_sha256')
                if mutation=='transport_entry_hash_wrong':report['transport_entry_sha256']='0'*64
                if mutation=='transport_entry_hash_missing':report.pop('transport_entry_sha256')
                if mutation=='retained_race_bytes_changed':(expected/'cp7_ow04_race_cases.py').write_bytes(b'LABELLED_SYNTHETIC_DRIFT')
                if mutation=='retained_declaration_bytes_changed':
                    (expected/'RACE_EXPECTED.json').write_bytes(raw+b' ')
                    report['predeclared_case_sha256']=sha(raw+b' ')
                report['source_races']=dict(status='PASS',counts={'PASS':2},database_remaining=0,
                    races={ident:{'status':'PASS'}for ident in race_source_ids})
                if mutation=='only_retained6_races':report.pop('source_races')
                if mutation=='missing_source_race_ID':report['source_races']['races'].pop(race_source_ids[-1])
                if mutation=='source_race_failed':report['source_races']['races'][race_source_ids[0]]['status']='FAIL'
                if mutation=='source_race_database_remains':report['source_races']['database_remaining']=1
                if mutation=='source_race_module_changed':report['source_race_cases_sha256']='0'*64
                if mutation=='source_race_proposal_provenance_changed':report['source_proposal_source_candidate']='e'*40
                if mutation=='source_race_total_count_wrong':report['observed_total_case_count']=6
                if mutation=='source_race_preserved_inputs_changed':report['preserved_source_race_inputs']['old6_cases_sha256']='0'*64
            (proof/filename).write_text(json.dumps(report))
            package=dict(mode='install',status='ALL_STAGES_INSTALLED',gate={key:True for key in GATES})
            if mutation=='package_backup_gate_failed':package['gate']['backup_restore_drill']=False
            if full and label=='HTTP':
                if mutation=='only_old14_HTTP_rows':
                    report['http']['cases']={key:value for key,value in report['http']['cases'].items()if key not in dependency_ids}
                    report['observed_case_count']=14
                if mutation=='missing_dependency_HTTP_ID':report['http']['cases'].pop(dependency_ids[-1])
                if mutation=='dependency_hash_wrong':report['dependency_predeclared_case_sha256']='0'*64
                if mutation=='dependency_module_changed':
                    module=expected/'cp7_ow04_dependency_http_cases.py';module.write_bytes(module.read_bytes()+b' ')
                if mutation=='dependency_ID_collides_initial':report['dependency_required_case_ids'][0]=initial_ids[0]
                if mutation=='full_backend_hash_wrong':report['full_backend_sha256']='0'*64
                if mutation=='full_owning_source_wrong':report['full_owning_source_manifest']['predecessor_sql_sha256']='0'*64
                if mutation=='native_reuse63_wrong':report['reused_native_binding']['native_case_count']=63
                (proof/filename).write_text(json.dumps(report))
            package_path=old_package if label=='HTTP'else proof
            (package_path/'T3_PACKAGE_INSTALL.json').write_text(json.dumps(package))
        namespace=dict(Path=Path,json=json,hashlib=hashlib,__file__=str(expected/'qualification_gate.py'));exec(CODE,namespace)
        outcomes={'HTTP':'success','RACES':'success'}
        if mutation=='HTTP_command_failed':outcomes['HTTP']='failure'
        if mutation=='RACES_command_failed':outcomes['RACES']='failure'
        try:
            result=namespace['require'](proof,candidate,outcomes)
            return dict(id=control_id,accepted=True,answer=result)
        except Exception as error:return dict(id=control_id,accepted=False,error=str(error),error_type=type(error).__name__)


if __name__=='__main__':
    names=('valid','binding_incomplete','binding_unsupported32','reports_reused44_current_binding63','report_declaration_hash_wrong',
        'binding_old58','only_old8_HTTP_rows','missing_source_HTTP_ID','source_group_collides_initial','source_subgroup_count_wrong',
        'source_declaration_changed','source_declaration_hash_wrong','source_module_changed','auth_not_restored','cleanup_failure',
        'source_case_failed','required_ID_list_missing_source','package_backup_gate_failed','HTTP_command_failed',
        'source_race_declaration_changed','only_retained6_races','missing_source_race_ID','source_race_failed',
        'source_race_database_remains','source_race_module_changed','source_race_proposal_provenance_changed',
        'source_race_total_count_wrong','source_race_preserved_inputs_changed','RACES_command_failed',
        'retained_race_hash_wrong','retained_race_hash_missing','transport_entry_hash_wrong','transport_entry_hash_missing',
        'retained_race_bytes_changed','retained_declaration_bytes_changed')
    names+=tuple('full73:'+name for name in(
        'valid','only_old14_HTTP_rows','missing_dependency_HTTP_ID','dependency_hash_wrong',
        'dependency_module_changed','dependency_ID_collides_initial','full_backend_hash_wrong',
        'full_owning_source_wrong','binding_native64','native_reuse63_wrong',
        'HTTP_command_failed','RACES_command_failed','source_race_failed',
        'dependency_declaration_changed','dependency_count_wrong'))
    names+=tuple('full87:'+name for name in(
        'valid','only_old14_HTTP_rows','missing_dependency_HTTP_ID','dependency_hash_wrong',
        'dependency_module_changed','dependency_ID_collides_initial','full_backend_hash_wrong',
        'full_owning_source_wrong','binding_native64','native_reuse63_wrong',
        'HTTP_command_failed','RACES_command_failed','source_race_failed',
        'dependency_declaration_changed','dependency_count_wrong'))
    names+=tuple('full87:'+name for name in('admin_valid','admin_source_changed','admin_native_coverage_faked','admin_receipt_missing'))
    rows=[exercise(name)for name in names]
    assert all(row['accepted']is(row['id']in('valid','full73:valid','full87:valid','full87:admin_valid'))
        and(row['accepted']or row['error_type']=='AssertionError')for row in rows),rows
    print(json.dumps(dict(classification='SYNTHETIC_ACTUAL_FUNCTION_NOT_RUNTIME',status='PASS',count=len(rows),
        gate_source_sha256=sha(SOURCE.read_bytes()),database_calls=0,rows=rows),indent=2))
