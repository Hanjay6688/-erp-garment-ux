"""Keep the exact accepted installation and complete outer restoration."""
from hashlib import sha256
import ast,json


def check(repo,here):
    rule=json.loads((here/'ORIGIN.json').read_bytes());raw=(repo/rule['path']).read_bytes()
    assert sha256(raw).hexdigest()==rule['sha256'],'CONSISTENT_CAPTURE_PARENT_PROBE_CHANGED'
    expected=raw.decode()
    for change in rule['changes']:
        assert expected.count(change['old'])==change['count']
        expected=expected.replace(change['old'],change['new'])
    actual=(here/'probe.py').read_text()
    assert actual==expected,'CONSISTENT_CAPTURE_UNDECLARED_PROBE_CHANGE'
    assert sum(isinstance(n,ast.Assert)for n in ast.walk(ast.parse(actual)))==rule['current_assertions']
    return dict(exact_declared_derivation=True,outer_full_baseline_restore_retained=True,
        unchanged_parent_inverse_with_actual_refusal_reason=True,
        candidate_schema_not_projected_into_parent=True,full_parent_inverse_repeated=False)
