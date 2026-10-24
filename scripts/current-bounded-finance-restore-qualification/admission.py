"""Preserve both actual predecessor qualifications before the new used restore."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess


def admitted(repo,here,steps,product,recovery):
    path=repo/'scripts/current-bounded-finance-native-qualification/probe.py'
    spec=importlib.util.spec_from_file_location('bounded_finance_restore_native_admission',path)
    native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
    predecessor=native.admitted()
    pins=json.loads((here/'SOURCE.json').read_bytes())
    for name,digest in pins['files'].items():
        assert sha256((repo/name).read_bytes()).hexdigest()==digest,('BOUNDED_FINANCE_RESTORE_SOURCE_CHANGED',name)
    assert pins['required_steps']==list(steps)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    for name in('fixture.py','opening_fixture.py'):
        assert (here/name).read_bytes()==(repo/'scripts/current-analog-consumer-opening-qualification'/name).read_bytes()
    originals={}
    for variable,proof in pins['actual_qualification_originals'].items():
        raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        actual=json.loads(raw)
        assert actual['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate'],variable
        if variable=='CURRENT_CONSUMER_ORIGINAL_REPORT':
            assert actual['source_declaration']['current_installation']==product.predecessor.sources()
            assert actual['required_steps_pass']and actual['baseline_advisors_equal']
        elif variable=='CURRENT_BOUNDED_FINANCE_ORIGINAL_REPORT':
            assert actual['source_declaration']['current_installation']==product.sources()
            assert actual['observed_case_count']==5 and actual['required_case_ids_pass']
            assert actual['native']['counts']=={'PASS':5}
            assert actual['required_case_ids']==list(native.IDS)
        else:raise ValueError('BOUNDED_FINANCE_UNDECLARED_PREREQUISITE: '+variable)
        originals[variable]=dict(proof,observed_status=actual['status'])
    assert set(originals)=={'CURRENT_CONSUMER_ORIGINAL_REPORT','CURRENT_BOUNDED_FINANCE_ORIGINAL_REPORT'}
    return dict(qualified_current_bounded_finance=predecessor,current_installation=product.sources(),
        recovery=recovery.sources(),qualification=pins,actual_originals_verified=originals)
