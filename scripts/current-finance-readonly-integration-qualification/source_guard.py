"""Only declared focused-probe changes; every original cron assertion retained."""
from hashlib import sha256
import ast
import json


def check(repo, here, probe_override=None, helper_overrides=None):
    rule = json.loads((here / 'ORIGIN.json').read_bytes())
    raw = (repo / rule['probe']['path']).read_bytes()
    assert sha256(raw).hexdigest() == rule['probe']['sha256'], 'PRIOR_PROBE_CHANGED'
    expected = raw.decode()
    for change in rule['probe']['changes']:
        assert expected.count(change['old']) == change['count'], 'FOCUSED_PROBE_ANCHOR_CHANGED'
        expected = expected.replace(change['old'], change['new'])
    actual = probe_override if probe_override is not None else (here / 'probe.py').read_text()
    assert actual == expected, 'UNDECLARED_PROBE_OPERATION_OR_ORACLE_CHANGE'
    assert sum(isinstance(n, ast.Assert) for n in ast.walk(ast.parse(raw))) == rule['original_probe_assertions'] == 10
    assert sum(isinstance(n, ast.Assert) for n in ast.walk(ast.parse(actual))) == rule['focused_probe_assertions']
    for path, digest in rule['exact_helpers'].items():
        assert sha256((repo / path).read_bytes()).hexdigest() == digest, path
    runner = (repo / 'scripts/current-choice-finance-cron-qualification/runner.py').read_text()
    assert sum(isinstance(n, ast.Assert) for n in ast.walk(ast.parse(runner))) == rule['unchanged_cron_assertions'] == 36
    derived = {}
    for name, source in rule['derived_helpers'].items():
        raw = (repo / source['path']).read_bytes()
        assert sha256(raw).hexdigest() == source['sha256'], 'PRIOR_HELPER_CHANGED'
        expected = raw.decode()
        for change in source['changes']:
            assert expected.count(change['old']) == change['count'], 'OBSERVER_HELPER_ANCHOR_CHANGED'
            expected = expected.replace(change['old'], change['new'])
        actual = (helper_overrides or {}).get(name, (here / name).read_text())
        assert actual == expected, 'UNDECLARED_HELPER_OPERATION_OR_ORACLE_CHANGE:' + name
        before = sum(isinstance(n, ast.Assert) for n in ast.walk(ast.parse(raw)))
        after = sum(isinstance(n, ast.Assert) for n in ast.walk(ast.parse(actual)))
        assert before == after == source['original_assertions'] == source['current_assertions']
        derived[name] = after
    assert rule['full_parent_inverse_repeated'] is rule['full_final_qualification_claim'] is False
    return dict(original_probe_assertions_retained=10, focused_probe_assertions=rule['focused_probe_assertions'],
                unchanged_cron_assertions=36, exact_cron_and_restore_helpers=True,
                observer_helper_assertions_retained=derived,
                full_parent_inverse_repeated=False, full_final_qualification_claim=False)
