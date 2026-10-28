"""Scoped tooling successor; historical manifests keep their original meaning."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,subprocess
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
SCRIPT='scripts/cp7_ow10_statistical_local.mjs'
OLD='e14024bd85397aa0eb06f61354dc3400fd57fa6318e83bdbb4c00df3aa5d7685'
A='a6bb16bd898ade9cf5cf3588e6f39d4ecabef8a8'
B='4fcc1adc2b219304c73e2de6dc6df2b7810106d9'
FILES={SCRIPT:'2f2d02ed883a3fa018f8bd422e7879b58bb6ab7e4076232df3c63c372e729f57',
    'scripts/cp7_first_failure_evidence.mjs':'41b059ed810c57c97f2ee05f4722ad7c415b7828b1e24c9c098962ee9cd9f34d',
    'scripts/cp7_first_failure_evidence.test.mjs':'f14383aa6966513256496a0871b0175809697e941720010a08d7787210453c21'}
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def checked(*,overrides=None,receipt=None):
    receipt=receipt if receipt is not None else json.loads((ROOT/'docs/cp7/d17-14/ow15/A_B_OW10_FIRST_FAILURE_INTAKE_20261028.json').read_bytes())
    assert receipt['status']=='PASS_A_SELECTIVE_B_JAVASCRIPT_INTEGRATION'
    assert receipt['files']==FILES and receipt['B_tested_head']==B
    actual=receipt['A_actual']
    assert actual['head']==A and (actual['run_id'],actual['job_id'])==(40658882798,122716611807)
    assert (actual['filesystem_tests_passed'],actual['filesystem_tests_failed'],actual['codeql_queries'],actual['codeql_results'])==(4,0,103,0)
    assert actual['analysis_successful']is actual['file_system_race_query_present']is True
    assert actual['zip_sha256']=='893fe8ea1573775f257f464604f3187a558e2e7a08a3e3739dff1a4ef43a3ae3'
    for path,digest in FILES.items():
        raw=(overrides or{}).get(path,(ROOT/path).read_bytes())
        assert sha256(raw).hexdigest()==digest,path
        assert raw==git('show',A+':'+path)==git('show',B+':'+path),path
    assert sha256(git('show','7657bbee5d55277855a0ab53126438c2e9c63118:'+SCRIPT)).hexdigest()==OLD
    return dict(files=FILES,replaced_historical_path=SCRIPT,old_digest=OLD,A_qualified_head=A,B_qualified_head=B,
        actual_JS_receipt_verified=True,historical_manifests_rewritten=False,backend_or_browser_unlock=False)
def derivation(*,actual=None):
    rule=json.loads((HERE/'ORIGIN.json').read_bytes());raw=(ROOT/rule['path']).read_bytes()
    assert sha256(raw).hexdigest()==rule['sha256']
    expected=raw.decode()
    for change in rule['changes']:
        assert expected.count(change['old'])==1;expected=expected.replace(change['old'],change['new'],1)
    assert (actual if actual is not None else(HERE/'check.py').read_text())==expected,'UNDECLARED_SOURCE_ORACLE_CHANGE'
    return True
