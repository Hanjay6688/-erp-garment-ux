"""The one tested A panel replacement; historical UI proof remains historical."""
from pathlib import Path
from hashlib import sha256
import json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
PANEL='src/NativeAnalysisFinancePanel.tsx'
TEST='src/NativeAnalysisFinancePanel.progress.dom.test.tsx'
OLD='c8490f5de4335a6d97e2f37e6523bc8c303f16cacbd9f3dab29b7481e65df149'
HEAD='2790a9e5726e7724070f2fa01a2468061f2bae98'
TREE='d4d9d3d1a9c440f0d3615842ad14cdfa113d99fc'
BASE='3a062d099739b4dc8758d71357f7ab1c4bba085b'
B='51a9e72a89b4576283fe30cb17b56dd26fc57668'
EVIDENCE='docs/cp7/d17-18/a-finance-progress-observer-20261028/'
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def checked(*,overrides=None):
    def read(path):return (overrides or{}).get(path,(ROOT/path).read_bytes())
    assert git('rev-parse',HEAD+'^{tree}').decode().strip()==TREE
    receipt_raw=read(EVIDENCE+'SOURCE_SUCCESSOR.json')
    assert receipt_raw==git('show',HEAD+':'+EVIDENCE+'SOURCE_SUCCESSOR.json')
    receipt=json.loads(receipt_raw);files=receipt['files']
    assert set(files)=={PANEL,TEST}and receipt['base_head']==BASE
    assert receipt['status']=='PASS_LOCAL_UNIT_DOM_ONLY_PREPARED'
    assert receipt['server_job_mutation']is receipt['production_go']is receipt['independent_acceptance']is False
    assert receipt['observation_limit_ms']==150000 and receipt['source_manifest_rewrites']==0
    previous=git('show',BASE+':'+PANEL);assert previous==git('show',B+':'+PANEL)
    assert sha256(previous).hexdigest()==OLD==receipt['previous_panel']['sha256']
    for path,proof in files.items():
        raw=read(path);assert len(raw)==proof['bytes']and sha256(raw).hexdigest()==proof['sha256'],path
        assert raw==git('show',HEAD+':'+path),path
    raw=read(EVIDENCE+'LOCAL_TEST_RESULTS.json');proof=receipt['local_tests']
    assert raw==git('show',HEAD+':'+EVIDENCE+'LOCAL_TEST_RESULTS.json')
    assert len(raw)==proof['report_bytes']and sha256(raw).hexdigest()==proof['report_sha256']
    result=json.loads(raw)
    assert result['success']is True and result['numTotalTests']==result['numPassedTests']==95
    assert result['numFailedTests']==result['numPendingTests']==result['numTodoTests']==0
    assert proof['typecheck']=='PASS'and proof['current_component_and_parser_tests']==29
    new=[r for r in result['testResults']if r['name'].endswith('/'+TEST)]
    assert len(new)==1 and len(new[0]['assertionResults'])==4
    prefix=new[0]['name'][:-len(Path(TEST).name)]
    current=[r for r in result['testResults']if r['name'].startswith(prefix)]
    assert len(current)==3 and sum(len(r['assertionResults'])for r in current)==29
    assert all(a['status']=='passed'for r in result['testResults']for a in r['assertionResults'])
    return dict(files={p:v['sha256']for p,v in files.items()},replaced_historical_path=PANEL,old_digest=OLD,
        tested_UI_head=HEAD,tested_UI_tree=TREE,B_preimage_exact=True,current_unit_DOM_tests=29,
        retained_frozen_tests=66,new_controls=4,actual_ERP_Auth_browser_cases=0,
        historical_manifests_rewritten=False,backend_or_browser_unlock=False)
def derivation(*,actual=None):
    rule=json.loads((HERE/'ORIGIN.json').read_bytes());raw=(ROOT/rule['path']).read_bytes()
    assert sha256(raw).hexdigest()==rule['sha256']and raw==git('show',BASE+':'+rule['path'])
    expected=raw.decode()
    for change in rule['changes']:
        assert expected.count(change['old'])==1;expected=expected.replace(change['old'],change['new'],1)
    assert (actual if actual is not None else(HERE/'check.py').read_text())==expected,'UNDECLARED_UI_SOURCE_ORACLE_CHANGE'
    return True
