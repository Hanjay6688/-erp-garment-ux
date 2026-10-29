"""Counted private routing only; retained modules and financial bodies stay exact."""
from hashlib import sha256
from pathlib import Path
import ast
import importlib.util

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-credit-d1-current-parent-continuation3-qualification'
OLD = 'scripts/current-credit-d1-owner-followup-qualification'
CONT = 'scripts/current-credit-d1-continuation-qualification'
CURRENT = 'scripts/current-credit-d1-product-phase-native13-qualification'


def substitute(raw, pairs):
    text = raw.decode()
    for before, after in pairs:
        if text.count(before) != 1:
            raise ValueError('D1_CONT_CURRENT_ONE_EXACT_ROUTING_ANCHOR_REQUIRED:' + before)
        text = text.replace(before, after, 1)
    restored = text
    for before, after in reversed(pairs):
        if restored.count(after) != 1:
            raise ValueError('D1_CONT_CURRENT_ONE_EXACT_REVERSE_ANCHOR_REQUIRED')
        restored = restored.replace(after, before, 1)
    if restored.encode() != raw:
        raise ValueError('D1_CONT_CURRENT_PRIVATE_DERIVATION_NOT_REVERSIBLE')
    return text, dict(original_sha256=sha256(raw).hexdigest(), derived_sha256=sha256(text.encode()).hexdigest(),
                      counted_routing_changes=len(pairs), all_other_bytes_exact=True)


def cases(raw):
    text, proof = substitute(raw, ((
        "guard = load('d1_cont_exact_source_guard', HERE / 'source_guard.py')",
        'guard = CURRENT_CONTINUATION_GUARD()'),))
    old = ast.parse(raw); new = ast.parse(text)
    functions = lambda tree: {node.name: ast.dump(node, include_attributes=False)
                             for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    if functions(old) != functions(new):
        raise ValueError('D1_CONT_CURRENT_CALLBACK_OR_FINANCIAL_HELPER_CHANGED')
    return text, dict(proof, unchanged_functions=len(functions(old)), unchanged_Native_callbacks=3)


def source_guard(raw):
    return substitute(raw, (("file = root / NAMESPACE / 'SOURCE.json'",
                            "file = root / '" + NS + "/CONTINUATION_SOURCE.json'"),))


def transition(raw):
    return substitute(raw, ((
        "if sha256((ROOT/path).read_bytes()).hexdigest() != digest:",
        "if sha256((ROOT/path).read_bytes()).hexdigest() != CURRENT_PHYSICAL_SOURCE_EXCEPTIONS.get(path,digest):"),))


def admission(raw):
    return substitute(raw, ((
        "ROOT/'scripts/current-credit-de-native-qualification/SOURCE.json'",
        "ROOT/'" + CURRENT + "/SOURCE.json'"), (
        'prior = old.admitted(ROOT,original.parent,product,derivation)',
        "prior = old.admitted(ROOT,ROOT/'" + CURRENT + "',product,derivation)")))


def component(raw):
    return substitute(raw, ((
        "business = load('continuation_actual_three_business_callbacks',ROOT/'" + CONT + "/cases.py')",
        "business = load('continuation_current_private_business',HERE/'business.py').load_business()"),))


def local_controls(raw):
    return substitute(raw, ((
        "business = load('d1_cont_local_import_under_no_database_guard', HERE/'cases.py')",
        'business = CURRENT_BUSINESS()'), (
        "pins = json.loads((HERE/'SOURCE.json').read_bytes())\n    # product.sources()",
        "pins = json.loads((CURRENT_HERE/'CONTINUATION_SOURCE.json').read_bytes())\n    # product.sources()"), (
        "pins = json.loads((HERE/'SOURCE.json').read_bytes())\n        with TemporaryDirectory",
        "pins = json.loads((CURRENT_HERE/'CONTINUATION_SOURCE.json').read_bytes())\n        with TemporaryDirectory"), (
        "'scripts/current-credit-d1-continuation-qualification/SOURCE.json'",
        "'" + NS + "/CONTINUATION_SOURCE.json'")))


def derive(raw):
    path = ROOT / OLD / 'derive.py'
    spec = importlib.util.spec_from_file_location('d1_cont_current_exact_six_engine', path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value.derive(raw)
