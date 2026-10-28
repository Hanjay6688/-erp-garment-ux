"""Bind current product sources to the retained, exact frozen source admission.

Historical admission still runs only against its frozen checkout. Its manifest
is deliberately not treated as a manifest for the newly tested JS tool.
This bridge gives source equivalence only, never runtime/backend eligibility.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util,json,os,sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def checked_bytes(path,expected):
    raw=path.read_bytes()
    assert len(raw)==expected['bytes']and sha256(raw).hexdigest()==expected['sha256'],str(path)
    return json.loads(raw)
def admitted():
    cfg=json.loads((HERE/'CONFIG.json').read_bytes())
    source=load('backend_assembly_scoped_source_check',HERE/'check.py').check()
    retained=checked_bytes(Path(os.environ['CP7_INITIAL11C_FROZEN_SOURCE_ADMISSION']),cfg['retained_frozen_source_admission'])
    assert retained['qualification']==json.loads((ROOT/'scripts/current-factory-initial-stage/SOURCE.json').read_bytes())
    expected=retained['current_installation']
    product=load('backend_assembly_current_exact_product',ROOT/'scripts/current-factory-initial-stage/composition.py')
    actual=product.sources()
    assert actual==expected,'CURRENT_PRODUCT_SOURCE_DIFFERS_FROM_FROZEN_BACKEND'
    return dict(status='PASS_SCOPED_TOOLING_AND_EXACT_FROZEN_BACKEND_SOURCE_ONLY',
        source=source,frozen_backend_head=cfg['proposed_backend_head'],frozen_backend_tree=cfg['proposed_backend_tree'],
        current_installation=actual,entire_current_installation_exact=True,
        frozen_source_admission=cfg['retained_frozen_source_admission'],
        direct_historical_admission_on_changed_tooling='REFUSED_AS_EXPECTED_OLD_JS_DIGEST',
        historical_manifests_rewritten=0,historical_checks_disabled=0,
        runtime_backend_eligible=False,actual_DB_Auth_browser_cases=0,
        default_adopted=False,production_go=False,independent_acceptance=False)
if __name__=='__main__':
    import psycopg
    calls=[]
    def refuse(*a,**k):calls.append(1);raise AssertionError('SOURCE_BRIDGE_MUST_NOT_CONNECT_DATABASE')
    psycopg.connect=refuse
    result=admitted();assert not calls
    out=Path(os.environ['CP7_ASSEMBLY_SOURCE_OUTPUT']);out.parent.mkdir(parents=True,exist_ok=True)
    assert not out.exists(),'PRESERVE_FIRST_SOURCE_BRIDGE_RESULT'
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status=result['status'],database_connection_attempts=len(calls),runtime_backend_eligible=False)))
