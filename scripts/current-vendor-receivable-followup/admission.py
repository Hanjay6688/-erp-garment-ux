"""Exact source and complete Native prerequisite; rejects partial/other runtime."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,subprocess


def admitted(repo,here,product):
    config=json.loads((here/'CONFIG.json').read_bytes())
    source=json.loads((here/'SOURCE.json').read_bytes())
    assert config['contract']=='cp7.vendor-receivable-race-auth-followup.v1'
    assert config['production_go']is config['independent_acceptance']is False
    for path,digest in source['files'].items():
        assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    changed=subprocess.check_output(['git','-C',str(repo),'diff','--name-only',config['base_head'],'HEAD'],text=True).splitlines()
    assert set(changed)<=set(source['allowed_changes']),'UNDECLARED_VENDOR_FOLLOWUP_DELTA'
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no']).strip()
    spec=importlib.util.spec_from_file_location('vendor_followup_exact_gate',here/'gate.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    from cp7_vendor_receivable.cases import IDS
    selected=config.get('accepted_native7')
    if selected is None:raise ValueError('VENDOR_FOLLOWUP_CLOSED_NATIVE7_ACTUAL_PASS_REQUIRED')
    originals=Path(os.environ['CP7_VENDOR_NATIVE7_ORIGINALS'])
    current=product.sources()
    prerequisite=gate.checked(config,(originals/selected['original']['name']).read_bytes(),
        (originals/selected['package']['name']).read_bytes(),current,IDS)
    parent=current['predecessor']
    whole=sha256(json.dumps(parent,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    assert whole==config['whole_backend_sha256'],'VENDOR_FOLLOWUP_QUALIFIED_PARENT_CHANGED'
    cases_spec=importlib.util.spec_from_file_location('vendor_followup_id_contract',here/'cases.py')
    cases=importlib.util.module_from_spec(cases_spec);cases_spec.loader.exec_module(cases)
    assert config['race_ids']==list(cases.RACE_IDS)and config['http_ids']==list(cases.HTTP_IDS)
    return dict(status='EXACT_NATIVE7_AND_PACKAGE_PASS_FOLLOWUP_ADMITTED',qualification=source,
        current_installation=current,whole_backend_sha256=whole,prerequisite=prerequisite,
        Native7_repeated=False,race_ids=list(cases.RACE_IDS),http_ids=list(cases.HTTP_IDS),
        predecessor_B_browser_retained_not_reexecuted=True,production_go=False,independent_acceptance=False)
