"""Exact current product and original Native32 evidence; no import execution."""
from hashlib import sha256
from pathlib import Path
import json,os,subprocess

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
NATIVE32_SHA256='9a66b07743087e107e3d7d9298d9e517b786077f848cee79ffc326a8246c3a50'


def admitted(product):
    source=json.loads((HERE/'SOURCE.json').read_bytes())
    assert source['base_candidate']=='8c437dbe0d6e62e246b2cf0cda75fb6c19330357'
    assert source['product_sources']==product.sources()
    for path,digest in source['files'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest,('FINAL_DECLARED_SOURCE_CHANGED',path)
    changed=subprocess.check_output(['git','-C',str(REPO),'diff','--name-only',source['base_candidate'],'HEAD',
        '--','scripts','src','supabase','tests','.github/workflows'],text=True).splitlines()
    assert set(changed)<=set(source['files'])|{'scripts/ow04-final-qualification/SOURCE.json'},changed
    assert not subprocess.check_output(['git','-C',str(REPO),'status','--porcelain','--',
        'scripts','src','supabase','tests','.github/workflows'],text=True).strip()
    for path,digest in source['unchanged_expectations'].items():
        assert sha256((REPO/path).read_bytes()).hexdigest()==digest
    raw=Path(os.environ['OW04_NATIVE32_ORIGINAL_REPORT']).read_bytes()
    assert len(raw)==8166263 and sha256(raw).hexdigest()==NATIVE32_SHA256
    native=json.loads(raw)
    assert native['candidate_commit']=='8c437dbe0d6e62e246b2cf0cda75fb6c19330357'
    assert native['status']=='PASS'and native['native']['counts']=={'PASS':32}
    assert native['current_financial_sources']==product.sources()
    assert native['cp6_restored']and native['advisor_gate']and native['required_case_ids_pass']
    assert len(native['native']['cases'])==32 and all(r['status']=='PASS'for r in native['native']['cases'].values())
    return dict(candidate=native['candidate_commit'],raw_sha256=NATIVE32_SHA256,
        actual_counts=native['native']['counts'],financial_source_equal=True,
        run_id=39734958661,job_id=119678374447,Native32_actually_rerun_here=False)
