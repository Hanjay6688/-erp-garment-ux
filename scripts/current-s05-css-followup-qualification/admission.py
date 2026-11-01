"""Actual Root retention and immutable source proof precede every ERP import."""
from pathlib import Path
from hashlib import sha256
import importlib.util,json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PARENT=ROOT/'scripts/current-s03-sku-s05-composite-qualification'
ROOT_HEAD='dd5011d1453f5d8ac75bb11520e0e2c7cf38459b'
ROOT_TREE='186c94227610e202629c5d321ecbcea8b75c9f62'
ROOT_PATH='docs/cp7/d17-14/ow15/CURRENT38_ROOT_RETAINED35_20261101.json'
RECEIPT=dict(bytes=10877,sha256='4743e60ed6fdf33682a9e576ce180675923ed7287fda5a6372f56509a89f39c0')

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def json_pin(value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
    return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())

def retained():
    source=load('focused_before_ERP_closed_source',HERE/'source.py');invariance=source.preflight()
    p=load('focused_actual_Root_typed_receipt',PARENT/'parents.py')
    prerequisite=p.strict((HERE/'PREREQUISITE.json').read_bytes())
    p.fields(prerequisite,dict(root_head=ROOT_HEAD,root_tree=ROOT_TREE,root_path=ROOT_PATH,receipt=RECEIPT,
        parent_head=source.BASE,parent_tree=source.TREE,retained_case_count=35,fresh_case_credit=0,
        production_go=False,independent_acceptance=False),'EXACT_ACTUAL_ROOT_RETENTION_PREREQUISITE')
    git=load('focused_Root_immutable_git_bytes',PARENT/'source.py').git
    p.exact(git('rev-parse',ROOT_HEAD+'^{tree}').decode().strip(),ROOT_TREE,'EXACT_PUBLIC_ROOT_RECEIPT_TREE')
    raw=(HERE/'ROOT_RETAINED35.json').read_bytes()
    p.exact(dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),RECEIPT,'EXACT_COPIED_ROOT_RECEIPT_DIGEST')
    p.exact(raw,git('show',ROOT_HEAD+':'+ROOT_PATH),'EXACT_PUBLIC_ROOT_RECEIPT_BYTES')
    receipt=p.strict(raw)
    p.fields(receipt,dict(status='ROOT_RETAINED_CURRENT38_NATIVE31_S03_BROWSER4_NOT_AGGREGATE_PASS',
        head='08ef3bee814e6452b9193b53efc05d53abca2d9d',tree='abf7e8b78bd56907ace9fb30211d956b63d68797',
        run_id=41291621885,job_id=124803871870,artifact_id=13082560860,original_run_conclusion='failure',
        retained_Native_cases=31,retained_S03_browser_cases=4,retained_cases_require_successor_source_invariance=True,
        fresh_case_credit=0,original_restore_and_backup_valid=True,failed_run_relabelled_PASS=False,
        full37_qualified=False,package_all_five=False,production_go=False,independent_acceptance=False),
        'ONLY_ACTUALLY_RETAINED_CURRENT38_PROOF_NOT_AGGREGATE_ACCEPTANCE')
    ids=receipt['source_admission']['case_ids']
    expected={case for label,values in ids.items()if label!='S05_browser2'for case in values}
    p.exact(len(expected),35,'EXACT_THIRTY_FIVE_RETAINED_IDENTITIES')
    p.exact(set(receipt['retained_cases']),expected,'EXACT_RETAINED_CASE_SET')
    for row in receipt['retained_cases'].values():p.fields(row,dict(status='PASS',retained=True,fresh_case_credit=0),'RETAINED_NOT_FRESH')
    p.exact(receipt['missing_case_ids'],ids['S05_browser2'],'ONLY_TWO_MISSING_BROWSER_CASES')
    return dict(source_invariance=invariance,receipt=receipt,root_head=ROOT_HEAD,root_receipt=RECEIPT)

def parent_admission():return load('focused_natural_current_parent_admission',PARENT/'admission.py')

def admitted():
    proof=retained()
    parent=parent_admission().admitted()
    p=load('focused_complete_financial_source_comparison',PARENT/'parents.py')
    p.exact(json_pin(parent['current_installation']),proof['receipt']['qualified_financial_sources'],
        'RETAINED_NATIVE35_WHOLE_FINANCIAL_SOURCE_GRAPH_UNCHANGED')
    return dict(status='ACTUAL_RETAINED35_AND_EXACT_CURRENT_PRODUCT_ADMITTED_FOR_FRESH_BROWSER2',
        **proof,current_installation=parent['current_installation'],natural_parent_admission=parent,
        retained_case_credit_is_not_fresh=True,actual_new_cases=0,production_go=False,independent_acceptance=False)

def import_scope():return parent_admission().import_scope()
