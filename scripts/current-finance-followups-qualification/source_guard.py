"""The new outer probe retains the reviewed install and complete restore path."""
from hashlib import sha256
import ast
import json


def check(repo, here, override=None):
    rule = json.loads((here / 'ORIGIN.json').read_bytes())
    raw = (repo / rule['path']).read_bytes()
    assert sha256(raw).hexdigest() == rule['sha256'], 'FOLLOWUP_PARENT_PROBE_CHANGED'
    expected = raw.decode()
    for change in rule['changes']:
        assert expected.count(change['old']) == change['count'], 'FOLLOWUP_DERIVATION_ANCHOR_CHANGED'
        expected = expected.replace(change['old'], change['new'])
    actual = override if override is not None else (here / 'probe.py').read_text()
    assert actual == expected, 'FOLLOWUP_UNDECLARED_PROBE_CHANGE'
    assertions = sum(isinstance(node, ast.Assert) for node in ast.walk(ast.parse(actual)))
    assert assertions == rule['current_assertions']
    return dict(exact_declared_derivation=True, assertions=assertions,
                outer_full_baseline_restore_retained=True,
                used_guard_moved_to_each_isolated_committed_fixture=True,
                full_parent_inverse_repeated=False)
