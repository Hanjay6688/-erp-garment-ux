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
    from cp7_vendor_receivable.cases import IDS
    assert cfg['native_case_ids']==list(IDS)
    current=product.sources();assert current['predecessor']==parent
    return dict(status='QUALIFIED_BACKEND3194_AND_VENDOR_DELTA_ADMITTED',qualification=source,
        current_installation=current,qualified_parent_installation=parent,backend_head=cfg['backend_head'],
        whole_backend_sha256=whole,Native_case_ids=list(IDS),
        predecessor_browser_B_retained_not_reexecuted=True,production_go=False,independent_acceptance=False)
