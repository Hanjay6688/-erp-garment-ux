"""Admit frozen predecessor gates and explicitly declared current source changes."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess


def admitted(repo,here,steps,product,recovery):
    path=repo/'scripts/current-analog-choice-browser-qualification/frozen_admission.py'
    spec=importlib.util.spec_from_file_location('consumer_frozen_predecessor',path)
    frozen=importlib.util.module_from_spec(spec);spec.loader.exec_module(frozen)
    predecessor=frozen.invoke()
    assert predecessor['current_installation']==product.predecessor.sources(),'CONSUMER_PREDECESSOR_PRODUCT_SOURCE_CHANGED'
    pins=json.loads((here/'SOURCE.json').read_bytes())
    for name,digest in pins['files'].items():
        assert sha256((repo/name).read_bytes()).hexdigest()==digest,('CURRENT_CONSUMER_SOURCE_CHANGED',name)
    assert pins['required_steps']==list(steps)
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--',str(here)],text=True).strip()
    changed={};root=Path(os.environ['CURRENT_ANALOG_FROZEN_SOURCE_ROOT'])
    for declaration in pins['frozen_declarations']:
        path=root/declaration['path'];assert sha256(path.read_bytes()).hexdigest()==declaration['sha256']
        for name,digest in json.loads(path.read_bytes())['files'].items():
            current=sha256((repo/name).read_bytes()).hexdigest()
            if current!=digest:
                row=dict(frozen_sha256=digest,current_sha256=current)
                assert name not in changed or changed[name]==row
                changed[name]=row
    assert changed==pins['explicit_current_source_changes'],'UNDECLARED_FROZEN_SOURCE_DIFFERENCE'
    originals={}
    for variable,proof in pins['actual_qualification_originals'].items():
        raw=Path(os.environ[variable]).read_bytes()
        assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],variable
        actual=json.loads(raw);assert actual['status']=='PASS'and actual['cp6_restored']and actual['advisor_gate'],variable
        if variable=='COMPOSED_ANALOG_ORIGINAL_REPORT':
            assert actual['required_steps_pass']and actual['baseline_advisors_equal']
            assert actual['source_declaration']['current_installation']==product.predecessor.sources()
        else:
            assert actual['observed_case_count']==proof['observed_case_count']and actual['required_case_ids_pass']and actual['required_case_counts_pass']
            assert actual['consumer_source_sha256']==product.consumer.verify_sources()
            if variable!='CONSUMER_NATIVE_ORIGINAL_REPORT':
                assert actual['provenance_source_sha256']==product.provenance.verify_sources()
        originals[variable]=dict(proof,observed_status=actual['status'])
    return dict(immutable_predecessor_admission=predecessor,explicit_current_source_changes=changed,
        current_installation=product.sources(),recovery=recovery.sources(),qualification=pins,
        actual_originals_verified=originals,overall_cancelled_transport_job_not_claimed_success=True)
