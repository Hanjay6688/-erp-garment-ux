"""Eighteen real Auth/HTTP cases on the exact qualified OW04 core, disposable only.

This imports the separately qualified Native core verifier/installer; it does not rerun
or relabel historical Native evidence. The tested core identity is explicit.
"""
from pathlib import Path
import hashlib,json,os,subprocess,sys,traceback
REPO=Path(os.environ.get('ERP_REPO',Path(__file__).resolve().parents[2])).resolve()
sys.path.insert(0,str(REPO/'scripts'))
# The complete signed-source mode selects the same atomic qualified backend.
# This entry point itself accepts no connection/authority/mode overrides.
if len(sys.argv)>1:raise SystemExit('OW04 HTTP entry accepts no arguments')
sys.argv.append('--signed-source')
import cp7_ow04_probe as core
import cp7_ow04_http_cases as initial_http
import cp7_ow04_source_http_cases as source_http
import cp7_ow04_all_http_cases as http_cases
import cp7_ow04_dependency_http_cases as dependency_http
import full_backend
import cp6_auditor_modes as modes
import psycopg
from cp6_t3_aligned_install import advisors,advisor_delta
p09,package,credit=core.p09,core.package,core.credit
OUT=p09.bundle.ROOT/'cp6-proof/t3/CP7_OW04_HTTP.json'
DECLARATION_BYTES=Path(__file__).with_name('EXPECTED.json').read_bytes()
DECLARATION=json.loads(DECLARATION_BYTES)
assert tuple(x['id']for x in DECLARATION['cases'])==initial_http.IDS and len(initial_http.IDS)==8
SOURCE_DECLARATION_BYTES=Path(__file__).with_name('SOURCE_HTTP_EXPECTED.json').read_bytes()
SOURCE_DECLARATION=source_http.expected()
assert tuple(x['id']for x in SOURCE_DECLARATION['cases'])==source_http.IDS and len(source_http.IDS)==6
DEPENDENCY_DECLARATION_BYTES=Path(__file__).with_name('DEPENDENCY_HTTP_EXPECTED.json').read_bytes()
DEPENDENCY_DECLARATION=json.loads(DEPENDENCY_DECLARATION_BYTES)
assert tuple(r['id']for r in DEPENDENCY_DECLARATION['cases'])==dependency_http.IDS and DEPENDENCY_DECLARATION['required_full_native_count']==73
assert http_cases.IDS==initial_http.IDS+source_http.IDS+dependency_http.IDS and len(http_cases.IDS)==len(set(http_cases.IDS))==18


def git(*args):
    return subprocess.run(['git','-C',str(REPO),*args],check=True,capture_output=True,text=True).stdout.strip()


def qualified_core():
    binding_path=Path(__file__).with_name('QUALIFIED_CORE.json')
    value=json.loads(binding_path.read_bytes())
    count=value['native_case_count']
    assert value['status']=='PASS'and count in(44,58,63,73,87),'OW04_HTTP_NATIVE_NOT_QUALIFIED'
    assert git('rev-parse','HEAD:scripts/cp7_customer_credit')==value['core_directory_tree'],'OW04_HTTP_CORE_CHANGED'
    assert git('rev-parse','HEAD:scripts/cp7_ow04_probe.py')==value['native_probe_blob'],'OW04_HTTP_NATIVE_PROBE_CHANGED'
    changed=git('diff','--name-only',value['candidate'],'--','scripts','src','supabase').splitlines()
    extra=[p for p in changed if not p.startswith('scripts/ow04-qualification/')]
    # This administrative API is not imported by the ordinary qualified
    # product. It has its OWN exact source binding and actual restore proof;
    # Native87 never gets relabelled as having executed it. Every pre-existing
    # product/installer dependency above/below still has to be byte exact.
    admin_path='scripts/cp7_ow04_restore_bundle.py'
    separate_admin=None
    if extra:
        assert count==87 and extra==[admin_path],('OW04_HTTP_QUALIFIED_DEPENDENCY_CHANGED',changed)
        declared=REPO/'docs/cp7/d17-14/ow04/USED_RESTORE_QUALIFICATION.json'
        assert declared.is_file(),'OW04_ADMIN_RESTORE_DECLARATION_REQUIRED'
        admin_declaration=json.loads(declared.read_bytes())
        assert admin_declaration.get('required_native_case_count')==87 \
            and admin_declaration.get('expected_scenario_count')==1 \
            and admin_declaration.get('required_restore_module')==admin_path \
            and admin_declaration.get('scenario_id')=='OW04_USED_CREDIT_REFUND_RESTORE_CONTINUE','OW04_ADMIN_RESTORE_DECLARATION_CHANGED'
        admin=admin_declaration.get('separate_administrative_source',{})
        assert admin.get('path')==admin_path and admin.get('native_runtime_covered')is False \
            and admin.get('classification')=='SEPARATE_ADMIN_RESTORE_REQUIRES_OWN_ACTUAL_RUNTIME','OW04_ADMIN_RESTORE_SCOPE_CHANGED'
        assert (REPO/admin_path).is_file(),'OW04_ADMIN_RESTORE_SOURCE_MISSING'
        assert git('rev-parse','HEAD:'+admin_path)==admin.get('git_blob') \
            and hashlib.sha256((REPO/admin_path).read_bytes()).hexdigest()==admin.get('sha256'),'OW04_ADMIN_RESTORE_SOURCE_CHANGED'
        separate_admin=admin
    if count in(73,87):
        assert value.get('classification')==f'REUSED_FULL_NATIVE{count}_RUNTIME_EXACT_CORE_BINDING_NOT_NEW_TRANSPORT_EXECUTION','OW04_HTTP_FULL_BINDING_CLASS_CHANGED'
        assert git('rev-parse','HEAD:scripts/cp7_full_owning_install.py')==value['owning_installer_blob'],'OW04_HTTP_FULL_OWNING_INSTALLER_CHANGED'
        assert git('rev-parse','HEAD:scripts/cp7_full_ow04_probe.py')==value['native_full_probe_blob'],'OW04_HTTP_FULL_NATIVE_PROBE_CHANGED'
    receipt=(REPO/value['receipt']).read_bytes()
    assert hashlib.sha256(receipt).hexdigest()==value['receipt_sha256'],'OW04_HTTP_NATIVE_RECEIPT_CHANGED'
    actual=json.loads(receipt)
    summary=actual['summary']
    assert actual['candidate']==value['candidate']and actual['tree']==value['tree'] \
        and summary['status']=='PASS'and actual['counts']=={'PASS':count},'OW04_HTTP_NATIVE_BINDING_INVALID'
    assert summary['expected_case_count']==summary['observed_case_count']==count \
        and summary['cp6_restored']is True and summary['advisor_gate']is True,'OW04_HTTP_NATIVE_RESTORE_OR_COUNT_INVALID'
    declaration_name={44:'NATIVE_EMPTY_QUALIFICATION.json',58:'NATIVE_FRACTIONAL_QUALIFICATION.json',
                      63:'NATIVE_SIGNED_SOURCE_QUALIFICATION.json',73:'CREDIT_DEPENDENCY_NATIVE_QUALIFICATION.json',
                      87:'DIRECT_NATIVE_FRACTIONAL_QUALIFICATION.json'}[count]
    declaration_path=REPO/'docs/cp7/d17-14/ow04'/declaration_name
    declaration_bytes=declaration_path.read_bytes();declaration=json.loads(declaration_bytes)
    if count in(58,63,73,87):
        assert value['qualification_declaration']=='docs/cp7/d17-14/ow04/'+declaration_name \
            and value['qualification_declaration_sha256']==hashlib.sha256(declaration_bytes).hexdigest(),'OW04_HTTP_NATIVE_DECLARATION_CHANGED'
        gates=actual['package_gate']
        assert set(gates)=={'installed','primary_unchanged','backup_restore_drill','security_advisors','writer_runtime'} \
            and all(v is True for v in gates.values()),'OW04_HTTP_NATIVE_PACKAGE_INCOMPLETE'
        assert actual['workflow_conclusion']=='success'and actual['run_id']==value['run_id'] \
            and actual['job_id']==value['job_id'],'OW04_HTTP_NATIVE_WORKFLOW_NOT_SUCCESS'
    expected_ids=declaration['required_case_ids'];rows=actual['cases']
    assert declaration['expected_count']==len(expected_ids)==len(set(expected_ids))==count \
        and len(rows)==count and{r['id']for r in rows}==set(expected_ids) \
        and all(r['status']=='PASS'for r in rows),'OW04_HTTP_NATIVE_CASE_SET_INVALID'
    if count in(73,87):
        old_name='docs/cp7/d17-14/ow04/FULL_INSTALL_QUALIFICATION.json'
        old_bytes=(REPO/old_name).read_bytes();old_declaration=json.loads(old_bytes)
        assert value.get('retained_native64_declaration')==old_name and value.get('retained_native64_declaration_sha256')==hashlib.sha256(old_bytes).hexdigest(),'OW04_HTTP_RETAINED_NATIVE64_DECLARATION_CHANGED'
        assert old_declaration['expected_count']==len(old_declaration['required_case_ids'])==64 and expected_ids[:64]==old_declaration['required_case_ids'],'OW04_HTTP_RETAINED_NATIVE64_CASE_SET_CHANGED'
        composed=actual.get('full_composition',{})
        assert composed.get('owning_installer_blob')==value['owning_installer_blob'] and composed.get('native_full_probe_blob')==value['native_full_probe_blob'],'OW04_HTTP_FULL_NATIVE_COMPOSITION_CHANGED'
        assert composed.get('retained_case_count')==64 and composed.get('additional_readonly_case_count')==9 and composed.get('preuse_exact_CP6_restore')is True and composed.get('used_rollback_refused')is True,'OW04_HTTP_FULL_NATIVE_COMPOSITION_INCOMPLETE'
        assert all(r.get('full_boundary_restored')is True and r.get('public_schema_unchanged')is True
            and r.get('session_leaks')=={'advisory_locks':0,'advisory_lock_keys':[],'other_sessions':[]}for r in rows),'OW04_HTTP_FULL_NATIVE_BOUNDARY_NOT_RESTORED'
        if count==87:
            retained_name='docs/cp7/d17-14/ow04/CREDIT_DEPENDENCY_NATIVE_QUALIFICATION.json'
            retained_bytes=(REPO/retained_name).read_bytes();retained=json.loads(retained_bytes)
            assert value.get('retained_native73_declaration')==retained_name and value.get('retained_native73_declaration_sha256')==hashlib.sha256(retained_bytes).hexdigest(),'OW04_HTTP_RETAINED_NATIVE73_DECLARATION_CHANGED'
            assert retained['expected_count']==len(retained['required_case_ids'])==73 and expected_ids[:73]==retained['required_case_ids'],'OW04_HTTP_RETAINED_NATIVE73_CASE_SET_CHANGED'
            native_expected=(REPO/'scripts/cp7_customer_credit/hpp-fractional/NATIVE_EXPECTED.json').read_bytes()
            native_expected_sha=hashlib.sha256(native_expected).hexdigest()
            assert declaration.get('retained_native73_declaration_sha256')==hashlib.sha256(retained_bytes).hexdigest(),'OW04_HTTP_NATIVE87_RETENTION_PROOF_CHANGED'
            assert declaration.get('direct_native_fractional_expected_sha256')==native_expected_sha and composed.get('direct_native_fractional_expected_sha256')==native_expected_sha,'OW04_HTTP_NATIVE87_EXPECTED_CHANGED'
            assert composed.get('additional_direct_native_case_count')==14 and expected_ids[73:]==[r['id']for r in json.loads(native_expected)['cases']],'OW04_HTTP_NATIVE87_DIRECT_CASES_INCOMPLETE'
    result=dict(**value,binding_sha256=hashlib.sha256(binding_path.read_bytes()).hexdigest())
    if separate_admin is not None:result['separately_bound_administrative_source']=separate_admin
    return result


def run():
    # Fail before opening a connection if any previously qualified product or
    # installer dependency differs. Only this explicit qualification may differ.
    reused=qualified_core()
    assert reused['native_case_count']==87,'OW04_HTTP_FULL_NATIVE87_REQUIRED'
    report=dict(label='CP7_OW04_HTTP',status='INCOMPLETE',expected_case_count=18,required_case_ids=list(http_cases.IDS),
        candidate_commit=git('rev-parse','HEAD'),core_directory_tree=git('rev-parse','HEAD:scripts/cp7_customer_credit'),
        native_probe_blob=git('rev-parse','HEAD:scripts/cp7_ow04_probe.py'),source_sha256=credit.source_files(native_empty=True),
        qualification_only=True,independent_acceptance=False,production_go=False,feature_complete=False,
        predeclared_case_sha256=hashlib.sha256(DECLARATION_BYTES).hexdigest(),
        http_cases_sha256=hashlib.sha256(Path(initial_http.__file__).read_bytes()).hexdigest(),
        source_predeclared_case_sha256=hashlib.sha256(SOURCE_DECLARATION_BYTES).hexdigest(),
        source_http_cases_sha256=hashlib.sha256(Path(source_http.__file__).read_bytes()).hexdigest(),
        http_composition_sha256=hashlib.sha256(Path(http_cases.__file__).read_bytes()).hexdigest(),
        initial_required_case_ids=list(initial_http.IDS),source_required_case_ids=list(source_http.IDS),
        expected_subgroup_counts={'INITIAL':8,'SOURCE':6,'DEPENDENCY':4},
        dependency_predeclared_case_sha256=hashlib.sha256(DEPENDENCY_DECLARATION_BYTES).hexdigest(),
        dependency_required_case_ids=list(dependency_http.IDS),
        dependency_http_cases_sha256=hashlib.sha256(Path(dependency_http.__file__).read_bytes()).hexdigest(),
        full_backend_sha256=hashlib.sha256(Path(full_backend.__file__).read_bytes()).hexdigest(),
        transport_probe_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        reused_native_binding=reused,
        scope='REAL_AUTH_FULL_OWNING_INITIAL8_SOURCE6_DEPENDENCY4',
        limits=['Native qualification is separate evidence; no inference from this HTTP group','No browser/race/crash recovery proof','No default installation or production deployment'])
    installed=False;originals={}
    try:
        with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
            p09.wip.policy.bf.verified(cur)
            before=core.restore_state.capture(cur,package.boundary.snapshot,core.predecessor.public_state,p09.functions);conn.rollback()
            originals=full_backend.install(cur,report)
            report['verified_predecessor_info_manifest']=core.predecessor_info_manifest(cur)
            report['integrated_source_verification']=full_backend.verify(cur)
            conn.commit();installed=True;conn.rollback()
        report['advisors_with_cp7']=advisors(package.boundary.PG)
        report['http']=modes.run_http(http_cases,full_backend.verify,'cp7_ow04_settlement')
    except Exception as error:report.update(error=str(error),traceback=traceback.format_exc())
    finally:
        if installed:
            try:
                with psycopg.connect(package.boundary.ADMIN)as conn,conn.cursor()as cur:
                    full_backend.uninstall(cur,originals)
                    conn.commit()
                    report['cp6_restored']=core.restore_state.prove(cur,before,package.boundary.snapshot,core.predecessor.public_state,p09.functions,report)
                    conn.rollback();p09.wip.policy.bf.verified(cur);conn.rollback()
                report['advisor_delta']=advisor_delta(advisors(package.boundary.PG),report['advisors_with_cp7'])
                report['advisor_disposition']=core.advisor_disposition(report['advisor_delta'],report['verified_predecessor_info_manifest'])
                report['advisor_gate']=report['advisor_disposition']['gate']
            except Exception as error:report.update(restore_error=str(error),restore_traceback=traceback.format_exc(),cp6_restored=False,advisor_gate=False)
        group=report.get('http',{});report['observed_case_count']=sum(group.get('counts',{}).values())
        report['required_case_ids_pass']=set(group.get('cases',{}))==set(http_cases.IDS)
        if not report.get('error')and report.get('cp6_restored')and report.get('advisor_gate') \
            and group.get('status')in('PASS','RUN_COMPLETE')and group.get('counts')=={'PASS':18} \
            and report['required_case_ids_pass']and group.get('database_remaining',1)==0 \
            and(group.get('auth_counts')or{}).get('restored')and not group.get('cleanup_failures'):
            report['status']='PASS'
        OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(report,indent=2,default=str)+'\n')
        print(json.dumps({k:report.get(k)for k in ('label','status','candidate_commit','core_directory_tree','expected_case_count','observed_case_count','cp6_restored','advisor_gate','error','traceback','restore_error')},default=str),flush=True)
    return dict(status=report['status'],production_go=False,independent_acceptance=False,feature_complete=False)


if __name__=='__main__':
    package._writer_runtime=lambda browser_mode=False:run()
    package.run('install')
