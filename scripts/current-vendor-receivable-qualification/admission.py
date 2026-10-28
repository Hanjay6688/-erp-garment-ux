from pathlib import Path
from hashlib import sha256
import json,os,subprocess

def admitted(repo,here,product):
    cfg=json.loads((here/'CONFIG.json').read_bytes());source=json.loads((here/'SOURCE.json').read_bytes())
    assert cfg['contract']=='cp7.vendor-receivable-native.v1'
    assert cfg['production_go']is cfg['independent_acceptance']is False
    for path,digest in source['files'].items():assert sha256((repo/path).read_bytes()).hexdigest()==digest,path
    changed=subprocess.check_output(['git','-C',str(repo),'diff','--name-only',cfg['base_head'],'HEAD'],text=True).splitlines()
    assert set(changed)<=set(source['allowed_changes']),'UNDECLARED_VENDOR_DELTA'
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no']).strip()
    parent=product.parent().sources()
    whole=sha256(json.dumps(parent,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    assert whole==cfg['whole_backend_sha256'],'QUALIFIED_PARENT_BACKEND_CHANGED'
    proof=cfg['backend_original'];raw=(Path(os.environ['CP7_VENDOR_BACKEND_ORIGINALS'])/proof['name']).read_bytes()
    assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert actual['status']=='PASS'and actual['qualification_commit']==cfg['backend_head']
    assert actual['source_declaration']['current_installation']==parent
    # Retain the exact first incomplete result. A successor declaration never
    # rewrites that result to pretend its six passes covered this observer.
    failure=cfg['first_failure_original']
    failed_raw=(Path(os.environ['CP7_VENDOR_BACKEND_ORIGINALS'])/failure['name']).read_bytes()
    assert len(failed_raw)==failure['bytes']and sha256(failed_raw).hexdigest()==failure['sha256']
    failed=json.loads(failed_raw)
    assert failed['status']=='INCOMPLETE'and failed['qualification_commit']==failure['head']
    failed_group=failed['committed']['VENDOR_RECEIVABLE_NATIVE7_AND_USED_INVERSE']['native']
    assert failed_group['counts']=={'PASS':6,'INCOMPLETE':1}
    assert failed_group['cases']['OW08B_VENDOR_REFUND_REPLAY_INVERSE_HISTORY']['status']=='INCOMPLETE'
    from cp7_vendor_receivable.cases import IDS
    assert cfg['native_case_ids']==list(IDS)
    current=product.sources();assert current['predecessor']==parent
    assert current==failed['source_declaration']['current_installation'],'VENDOR_RUNTIME_CHANGED_SINCE_FIRST_ATTEMPT'
    return dict(status='QUALIFIED_BACKEND3194_AND_VENDOR_DELTA_ADMITTED',qualification=source,
        current_installation=current,qualified_parent_installation=parent,backend_head=cfg['backend_head'],
        whole_backend_sha256=whole,Native_case_ids=list(IDS),
        first_failure=dict(failure,counts=failed_group['counts']),runtime_identical_to_first_attempt=True,
        predecessor_browser_B_retained_not_reexecuted=True,production_go=False,independent_acceptance=False)
