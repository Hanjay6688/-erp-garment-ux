"""Reuse pinned case declarations without replacing historical runtime guards."""
from __future__ import annotations

import ast
import hashlib
import importlib
import json
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PINS = ROOT / 'docs/evidence/cp6-successor-oracles.json'


def pins():
    result = json.loads(PINS.read_text())
    for relative, expected in result['oracle_sha256'].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
    return result


def declarations(path, function, start_target, end_target):
    """Select an exact contiguous AST slice from a hash-verified source file."""
    relative = str(path.relative_to(ROOT))
    expected = pins()['oracle_sha256'][relative]
    source = path.read_bytes()
    assert hashlib.sha256(source).hexdigest() == expected
    module = ast.parse(source, filename=str(path))
    run = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == function)
    blocks = [n for n in run.body if isinstance(n, ast.With)]
    assert len(blocks) == 1, (relative, function, 'with boundary')
    body = blocks[0].body

    def target(node):
        return ast.unparse(node.targets[0]) if isinstance(node, ast.Assign) else None

    starts = [i for i, node in enumerate(body) if target(node) == start_target]
    ends = [i for i, node in enumerate(body) if target(node) == end_target]
    assert len(starts) == len(ends) == 1 and starts[0] < ends[0]
    return ast.Module(body=body[starts[0]:ends[0]], type_ignores=[])


def cases(group, today):
    """Only the declarations execute here; every business oracle stays original."""
    p = pins()
    module_name = p['groups'][group]['module']
    module = importlib.import_module(module_name)
    namespace = dict(vars(module), today=today, day=today-timedelta(days=3), old=False,
                     original_mode=False, report={})
    path = ROOT / 'scripts' / (module_name + '.py')
    if group == 'business':
        code = declarations(path, 'run_cases', 'specs', "result['reused_evidence']")
    elif group == 'imports':
        code = declarations(path, 'run', 'specs', "report['planned_case_ids']")
    else:
        assert group == 'values'
        oracle_path = ROOT / 'scripts/cp6_final_ak_independent.py'
        namespace.update(day=today, path=oracle_path,
                         declarations=declarations(oracle_path, 'run', 'specs', "report['planned_case_ids']"))
        code = declarations(path, 'run', 'namespace', "report['planned_case_ids']")
    exec(compile(code, str(path), 'exec'), namespace)
    result = namespace['specs']
    assert [name for name, _ in result] == p['groups'][group]['case_ids'], group
    assert len({name for name, _ in result}) == len(result)
    return result


if __name__ == '__main__':
    from datetime import date
    # This validates declaration completeness only; it makes no database claim.
    for group in ('business', 'imports', 'values'):
        print(group, len(cases(group, date(2026, 9, 23))), 'STATIC_DECLARATIONS_ONLY')
