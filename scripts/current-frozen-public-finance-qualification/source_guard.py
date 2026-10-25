"""Only the exact full composer import and two explicit public request names change."""
from pathlib import Path
from hashlib import sha256
import ast,json

CHANGES={
 'import cp7_current_versioned_performance_installation as product':'import cp7_current_frozen_public_installation as product',
 "REQUEST='erp_cp7_request_bounded_finance_analysis_v1'":"REQUEST='erp_cp7_request_bounded_frozen_finance_analysis_v2'",
 "OPERATIONAL='erp_cp7_request_bounded_staged_analysis_v1'":"OPERATIONAL='erp_cp7_request_bounded_staged_analysis_v2'",
}

def check(repo,here,case_text=None,snapshot_bytes=None):
    prior=repo/'scripts/current-versioned-performance-finance-qualification/cases.py'
    old=prior.read_text();expected=old
    for a,b in CHANGES.items():
        assert expected.count(a)==1,('RETAINED_SOURCE_ANCHOR_CHANGED',a)
        expected=expected.replace(a,b)
    current=(here/'cases.py').read_text()if case_text is None else case_text
    assert current==expected,'ONLY_PRODUCT_AND_TWO_PUBLIC_REQUEST_NAMES_MAY_CHANGE'
    raw=(here/'utc_snapshot.py').read_bytes()if snapshot_bytes is None else snapshot_bytes
    assert raw==(prior.parent/'utc_snapshot.py').read_bytes(),'FULL23_CAPTURE_OBSERVER_CHANGED'
    tree=ast.parse(current);assert sum(isinstance(n,ast.Assert)for n in ast.walk(tree))==55
    def literal(node):
        if isinstance(node,ast.Call):
            assert isinstance(node.func,ast.Name)and node.func.id=='dict'and not node.args
            assert all(k.arg is not None for k in node.keywords)
            return {k.arg:ast.literal_eval(k.value)for k in node.keywords}
        return ast.literal_eval(node)
    assignments={n.targets[0].id:literal(n.value)for n in tree.body
        if isinstance(n,ast.Assign)and isinstance(n.targets[0],ast.Name)and n.targets[0].id in('REQUEST','OPERATIONAL','IDS')}
    assert assignments['REQUEST']=='erp_cp7_request_bounded_frozen_finance_analysis_v2'
    assert assignments['OPERATIONAL']=='erp_cp7_request_bounded_staged_analysis_v2'
    ids=assignments['IDS'];assert len(ids['http'])==3 and len(ids['races'])==7
    return dict(retained_cases_sha256=sha256(prior.read_bytes()).hexdigest(),
        current_cases_sha256=sha256(current.encode()).hexdigest(),retained_assertions=55,
        only_product_import_and_two_request_constants_changed=True,
        full23_capture_observer_unchanged=True,actual_Auth_HTTP_credit=False)
