"""Current A-chain admission with one exact, additive App navigation successor.

Historical stage source declarations and Original bytes remain unchanged.
The only admitted difference is two counted Master callbacks in App.tsx.
Every other source is checked byte-for-byte by the retained P21 admission.
The actual current bytes are never hidden from a verifier or substituted.
"""
from pathlib import Path
from hashlib import sha256
import json,os,subprocess
import cp7_p21_current_chain_rehearsal_probe as a

REPO,HERE,OW05_HERE=a.REPO,a.HERE,a.OW05_HERE
adapter,restore=a.adapter,a.restore
SLICE_C,OW05_STEPS,CHAIN_STEPS,CHAIN_SCOPE_NOTES=a.SLICE_C,a.OW05_STEPS,a.CHAIN_STEPS,a.CHAIN_SCOPE_NOTES
OLD_APP_SHA256='0bca1e95f69c51d3fb394028b41d9df1d5829858c185f0df008202dbaf1c08c4'
MASTER_CALLBACKS=(
 ('<ConnectedFgStockPage purpose="CARD"/>',"<ConnectedFgStockPage purpose=\"CARD\" onOpenMaster={()=>setPage('master-products')}/>"),
 ('<ConnectedFgStockPage/>',"<ConnectedFgStockPage onOpenMaster={()=>setPage('master-products')}/>"),
)


def admit_master_navigation(raw,declared):
    if declared!=OLD_APP_SHA256:raise ValueError('AB_UI_ORIGINAL_APP_PIN_CHANGED')
    text=raw.decode('utf-8')
    for old,new in MASTER_CALLBACKS:
        if text.count(new)!=1 or old in text:raise ValueError('AB_UI_MASTER_CALLBACK_COUNT_CHANGED')
        text=text.replace(new,old,1)
    if sha256(text.encode('utf-8')).hexdigest()!=declared:
        raise ValueError('AB_UI_UNDECLARED_APP_CHANGE')
    return dict(path='src/App.tsx',qualified_original_sha256=declared,
        current_sha256=sha256(raw).hexdigest(),counted_additive_callbacks=2,
        unchanged_other_App_bytes=True,historical_Original_relabelled=False)


def admitted():
    # The legacy restore helper already admitted its closed CLI flags. Do not
    # import a second CLI entry point with a conflicting argv contract.
    declared={};ui_successor=None
    for module in adapter.chain():
        stage=module.__name__.split('.')[0]
        declared[stage]=json.loads((REPO/'scripts'/stage/'SOURCE.json').read_bytes())
        for path,digest in declared[stage]['files'].items():
            raw=(REPO/path).read_bytes()
            if stage=='cp7_contractor_guidance'and path=='src/App.tsx':
                ui_successor=admit_master_navigation(raw,digest)
            else:assert sha256(raw).hexdigest()==digest,('CHAIN_DECLARED_SOURCE_CHANGED',stage,path)
    base_raw=Path(os.environ['OW04_NATIVE32_ORIGINAL_REPORT']).read_bytes()
    assert len(base_raw)==8166263 and sha256(base_raw).hexdigest()=='9a66b07743087e107e3d7d9298d9e517b786077f848cee79ffc326a8246c3a50'
    base=json.loads(base_raw)
    assert base['status']=='PASS'and base['native']['counts']=={'PASS':32}
    assert base['cp6_restored']and base['advisor_gate']and base['required_case_ids_pass']
    assert base['current_financial_sources']==restore.ow05.predecessor.sources()
    pins=json.loads((HERE/'SOURCE.json').read_bytes())
    for path,digest in pins['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('CHAIN_P21_SOURCE_CHANGED',path)
    proof=pins['native_original'];raw=Path(os.environ['OW04BC_NATIVE7_ORIGINAL_REPORT']).read_bytes()
    assert proof['name']==SLICE_C+'.json'and len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256']
    actual=json.loads(raw)
    assert actual['label']==SLICE_C and actual['status']=='PASS'and actual['native']['counts']=={'PASS':7}and actual['races']['counts']=={'PASS':1}
    assert actual['required_case_ids_pass']and actual['required_race_ids_pass']and actual['cp6_restored']and actual['advisor_gate']
    assert actual['source_declaration']['OW04BC_declared_source']==declared['cp7_credit_incoming']
    raw=(OW05_HERE/'EXPECTED_P21_RESTORE.json').read_bytes()
    assert sha256(raw).hexdigest()=='643081adcec37ffd3c4d83c25e7522522da634e81cb8af551796202c16bc2cf9'
    assert pins['OW05_steps']==list(OW05_STEPS)and pins['chain_steps']==list(CHAIN_STEPS)
    assert pins['chain_scope_notes']==[n['id']for n in CHAIN_SCOPE_NOTES]and not set(pins['chain_scope_notes'])&set(CHAIN_STEPS)
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',str(HERE),str(OW05_HERE),
        'scripts/cp7_p21_current_chain_rehearsal_probe.py','scripts/cp7_chain_restore.py','scripts/cp7_p21_chain_adapter.py'],text=True).strip()
    return dict(actual_slice_C_chain_original=proof,chain_stages_declared_sources_verified=sorted(declared),
        slice_C_actually_rerun_here=False,current_UI_successor=ui_successor),json.loads(raw)
