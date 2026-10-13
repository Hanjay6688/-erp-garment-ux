"""Pure diagnostic controls; synthetic members, no native database claim."""
from pathlib import Path
import copy, json, hashlib, sys
ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
from cp6_auditor_difference import state_difference

before = {'functions': [['public.a()', 'definition-a|owner-a|acl-a'],
                        ['public.b()', 'definition-b|owner-b|acl-b'],
                        ['public.a()', 'definition-a|owner-a|acl-a']]}
changes = [
    ('ORDER_ONLY', [before['functions'][1], before['functions'][0], before['functions'][2]], 'ORDER_ONLY'),
    ('DUPLICATE_REMOVED', before['functions'][:2], 'CONTENT'),
    ('DEFINITION_CHANGED', [['public.a()', 'changed-definition|owner-a|acl-a'], *before['functions'][1:]], 'CONTENT'),
    ('OWNER_CHANGED', [['public.a()', 'definition-a|changed-owner|acl-a'], *before['functions'][1:]], 'CONTENT'),
    ('ACL_CHANGED', [['public.a()', 'definition-a|owner-a|changed-acl'], *before['functions'][1:]], 'CONTENT'),
]
rows = []
for case_id, members, expected in changes:
    a, b = copy.deepcopy(before), {'functions': copy.deepcopy(members)}
    saved = copy.deepcopy((a, b))
    observed = state_difference({}, {}, a, b)
    assert observed['public.functions']['kind'] == expected
    assert (a, b) == saved
    assert a != b
    rows.append(dict(id=case_id, status='PASS', observed=observed,
                     original_equality_remains_false=True, inputs_unchanged=True))
print(json.dumps(dict(qualification='LOCAL_QUALIFIED', cases=rows,
                     source_sha256=hashlib.sha256((REPO / 'scripts/cp6_auditor_difference.py').read_bytes()).hexdigest()), indent=2))
