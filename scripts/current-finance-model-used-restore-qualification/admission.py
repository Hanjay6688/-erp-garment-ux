"""Admit actual full model Native15 and committed finance restore prerequisites."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess


def predecessor_admission(repo):
    path=repo/'scripts/current-finance-model-qualification/probe.py'
    spec=importlib.util.spec_from_file_location('current_model_used_restore_native_admission',path)
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    return native.admitted()


def admitted(repo,here,steps,product,recovery):
    predecessor=predecessor_admission(repo)
    assert predecessor['current_installation']==product.sources()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    assert pins['required_steps']==list(steps)and len(steps)==8
    for path,digest in pins['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,('CURRENT_MODEL_USED_RESTORE_SOURCE_CHANGED',path)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    for name in('fixture.py','opening_fixture.py'):
        assert(here/name).read_bytes()==(repo/'scripts/current-analog-consumer-opening-qualification'/name).read_bytes()
    assert(here/'finance_fixture.py').read_bytes()==(repo/'scripts/current-bounded-finance-restore-qualification/finance_fixture.py').read_bytes()
    assert(here/'model_fixture.py').read_bytes()==(repo/'scripts/current-finance-model-restore-qualification/model_fixture.py').read_bytes()
    originals={}
    for variable,proof in pins['actual_qualification_originals'].items():
        raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        actual=json.loads(raw)
        assert actual['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate'],variable
        if variable=='CURRENT_FINANCE_MODEL_ORIGINAL_REPORT':
            assert actual['source_declaration']['current_installation']==product.sources()
            assert actual['native']['counts']=={'PASS':15}and actual['observed_case_count']==15
            assert actual['required_case_ids_pass']and actual['required_case_ids']==predecessor['qualification']['case_ids']
            assert actual['complete_preuse_removal']and actual['baseline_full22_all_rows_all_sequences_equal']and actual['baseline_advisors_equal']
        elif variable=='CURRENT_BOUNDED_FINANCE_RESTORE_ORIGINAL_REPORT':
            assert actual['source_declaration']['current_installation']==product.predecessor.sources()
            assert actual['required_steps_pass']and actual['required_steps']==list(steps)and actual['baseline_advisors_equal']
            assert [row['step']for row in actual['steps']]==list(steps)
            assert all(row['status']=='PASS'for row in actual['steps'])
            checks=actual['finance_full_restore_checks']
            assert [row['label']for row in checks]==['BEFORE_RESTORED_CLEAR','AFTER_NEXT_NATIVE_RETURN']
            assert all(row['exact_capture_report_provenance_and_operational_pages']and row['READY_read_and_same_UUID_replay']and row['captures_for_job']==1 for row in checks)
        else:raise ValueError('CURRENT_MODEL_USED_RESTORE_UNDECLARED_PREREQUISITE: '+variable)
        originals[variable]=dict(proof,observed_status='PASS')
    assert set(originals)=={'CURRENT_FINANCE_MODEL_ORIGINAL_REPORT','CURRENT_BOUNDED_FINANCE_RESTORE_ORIGINAL_REPORT'}
    return dict(qualified_current_finance_model=predecessor,current_installation=product.sources(),
        recovery=recovery.sources(),qualification=pins,actual_originals_verified=originals)
