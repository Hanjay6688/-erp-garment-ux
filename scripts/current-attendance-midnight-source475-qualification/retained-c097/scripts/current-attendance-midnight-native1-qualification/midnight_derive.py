"""Bounded exact engine/used-witness derivations, never a new financial oracle."""
from hashlib import sha256
from types import ModuleType
import ast
import importlib.util
from midnight_common import ROOT

OLD = ROOT / 'scripts/current-attendance-period-choice-native11-qualification'
ANCHOR = "    with psycopg.connect(url) as connection, connection.cursor() as cursor:\n"
COUNT_BEFORE = "report.update(status='PASS', actual_Native_cases=11, used_guard_refused_before_DDL=True,"
COUNT_AFTER = "report.update(status='PASS', actual_Native_cases=1, used_guard_refused_before_DDL=True,"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def engine(raw):
    helper = load('midnight_exact_inherited_six_engine_selections', OLD / 'derive.py')
    code, proof = helper.derive(raw)
    restored = code
    for before, after in reversed(helper.REPLACEMENTS):
        if restored.count(after) != 1:
            raise ValueError('MIDNIGHT_ONE_EXACT_ENGINE_REVERSE_ANCHOR_REQUIRED')
        restored = restored.replace(after, before, 1)
    if restored.encode() != raw:
        raise ValueError('MIDNIGHT_ALL_OTHER_ENGINE_BYTES_MUST_REMAIN_EXACT')
    return code, proof


def witness(raw):
    """Keep the complete committed ALLOCATE + all22/data/sequence refusal block."""
    text = raw.decode()
    tree = ast.parse(text)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'exercise')
    lines = text.splitlines(keepends=True)
    function_text = ''.join(lines[function.lineno - 1:function.end_lineno])
    if function_text.count(ANCHOR) != 1:
        raise ValueError('MIDNIGHT_ONE_EXACT_USED_WITNESS_START_REQUIRED')
    original = function_text[function_text.index(ANCHOR):]
    if original.count(COUNT_BEFORE) != 1:
        raise ValueError('MIDNIGHT_ONE_USED_WITNESS_COUNT_ANCHOR_REQUIRED')
    body = original.replace(COUNT_BEFORE, COUNT_AFTER, 1)
    if body.count(COUNT_AFTER) != 1 or body.replace(COUNT_AFTER, COUNT_BEFORE, 1) != original:
        raise ValueError('MIDNIGHT_USED_WITNESS_NOT_REVERSIBLE')
    header = ('def committed_used_witness(native, control, state, report, url, business, product, '
              'financial_truth, psycopg, require_local, sequence_prefix):\n')
    code = header + body
    # Exact helper function bodies; no original exercise/strict11 is executed.
    for name in ('require_local', 'sequence_prefix'):
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
        code += '\n' + ''.join(lines[node.lineno - 1:node.end_lineno])
    compile(code, 'midnight-exact-used-block', 'exec')
    return code, dict(original_module_sha256=sha256(raw).hexdigest(),
        original_used_block_sha256=sha256(original.encode()).hexdigest(),
        derived_used_block_sha256=sha256(body.encode()).hexdigest(),
        counted_body_changes=1, only_change='actual_Native_cases metadata11 to1',
        committed_ALLOCATE_truth_accrual_source_all22_rows_sequences_guard_exact=True,
        original11_factory_and_callbacks_executed=False)
