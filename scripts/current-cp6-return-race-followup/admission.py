from pathlib import Path
from hashlib import sha256
import json,os,subprocess

def admitted(repo,here,product):
    cfg=json.loads((here/'CONFIG.json').read_bytes());source=json.loads((here/'SOURCE.json').read_bytes())
    assert cfg['contract']=='cp7.current-return-reverse-race-successor.v1'
    assert cfg['production_go']is cfg['independent_acceptance']is False
    for p,h in source['files'].items():assert sha256((repo/p).read_bytes()).hexdigest()==h,p
    changed=subprocess.check_output(['git','-C',str(repo),'diff','--name-only',cfg['base_head'],'HEAD'],text=True).splitlines()
    allowed={'docs/cp7/OPEN_WORK_D17_14_20261020.md','docs/cp7/handoff/CP75_CP7C_CP8_SAMBUNGAN_PREPARED_20261028.md','docs/cp7/d17-14/KOORDINASI.md',source['workflow']}
    assert all(p in allowed or p.startswith('scripts/current-cp6-return-race-followup/')for p in changed),'UNDECLARED_PRODUCT_CHANGE'
    assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain','--untracked-files=no']).strip()
    # The current runtime composition actually computes these sources.
    current=product.sources();whole=sha256(json.dumps(current,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    assert whole==cfg['whole_backend_sha256'],'WHOLE_BACKEND_CHANGED'
    directory=Path(os.environ['CP7_RETURN_RACE_ORIGINALS']);values={}
    for kind in ('backend_original','retained'):
        p=cfg[kind];raw=(directory/p['name']).read_bytes()
        assert len(raw)==p['bytes']and sha256(raw).hexdigest()==p['sha256'],kind
        values[kind]=json.loads(raw)
    new,old=values['backend_original'],values['retained']
    assert new['status']=='PASS'and new['qualification_commit']==cfg['backend_head']
    assert new['source_declaration']['current_installation']==current
    assert old['status']=='INCOMPLETE'and old['qualification_commit']==cfg['retained']['head']
    assert old['changed_case_statuses']=={'SALE_REVERSE_COMMIT':{'baseline':'PASS','current':'INCOMPLETE'}}
    baseline={n:old['baseline']['races'][n]for n in cfg['case_ids']}
    assert all(v['status']=='PASS'for v in baseline.values())
    assert 'CP7_NATIVE_EMPTY_ACTIVE_SOURCE_REQUIRED' in old['races']['races']['SALE_REVERSE_COMMIT']['error']
    return dict(status='SOURCE_AND_EXACT_BACKEND_ADMITTED',qualification=source,current_installation=current,
        backend_head=cfg['backend_head'],whole_backend_sha256=whole,retained_original_status='INCOMPLETE',retained_baseline_cases=baseline,
        old_current_case_status='INCOMPLETE',production_go=False,independent_acceptance=False)
