"""D1-only lawful two-piece fixture; importing never runs SQL.

Ten reversible substitutions change only the unposted return request and its
physical-fixture-dependent cost assertions. All retained financial, source,
history, period and journal checks survive. Imported modules are never patched.
The closed Native qualifier, not this adapter, owns execution and restoration.
"""
import ast
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import cp7_ow04_consumer_fixture as retained

native = retained.native
ROOT = Path(__file__).resolve().parents[2]
CONTRACT = 'cp7.credit-d1-two-piece-fixture.v1'
SOURCES = {
    'native': ('scripts/cp7_customer_credit/native/cp7_ow04_native_source_fixture.py',
               '4984926b221df459e6e88c2f282da3e553d4810d177208ea489c9c3b1d264497'),
    'initial': ('scripts/cp7_customer_credit/initial-settlement/cp7_ow04_initial_settlement_cases.py',
                '6d4e2389e0090333ae076fc3091ec4333492e886e08fc1a96c4eea9282f93602'),
    'signed': ('scripts/cp7_customer_credit/reconciliation/native/cp7_ow04_signed_source_cases.py',
               '82831d767c85199ab182c21aa5a56fe46e7cba0c7e70ccba6c89477b755de640'),
    'consumer': ('scripts/cp7_customer_credit/consumer/cp7_ow04_consumer_fixture.py',
                 '75a6d5d573de0827a2efa712d49059a14e1ee83e3ee2635598e005b4bc1afeed'),
}
SETUP_ANCHOR = '    x = native.prepared(cur, today, "1000.00", "OPEN")'
SETUP_TWO_PIECES = SETUP_ANCHOR + '''
    # This is still an unposted operator request, not a posted-row mutation.
    assert len(x["return_payload"]["items"]) == 1
    assert x["return_payload"]["items"][0]["qty_pcs"] == "1"
    assert D(x["return_payload"]["items"][0]["refund_amount"]) == D("200.00")
    x["return_payload"]["items"][0]["qty_pcs"] = "2"
    x["return_payload"]["notes"] = "D1 explicit return2/value200; unitHPP10, actual HPP20"
    x["D1_fixture_binding"] = dict(contract=CONTRACT, base_fixture_id=x["fixture_id"],
        returned_qty="2", return_amount="200.00", unit_HPP="10.00", return_HPP="20.00",
        source_stock_qty="7", source_stock_HPP="70.00", net_FG_COGS="30.00")'''
TRANSFORMS = {
    ('native', 'assert_first_settlement_gl'): (
        ("{(f['location'],'GRADE_A'):5,(f['destination'],'GRADE_A'):1}",
         "{(f['location'],'GRADE_A'):5,(f['destination'],'GRADE_A'):2}"),
        ("rows[0][:3]==(1,D('10.00'),D('200.00'))", "rows[0][:3]==(2,D('10.00'),D('200.00'))"),
        ("cmd.mapping(cur,'FG_INVENTORY'):D('-40.00'),\n          cmd.mapping(cur,'COGS'):D('40.00')",
         "cmd.mapping(cur,'FG_INVENTORY'):D('-30.00'),\n          cmd.mapping(cur,'COGS'):D('30.00')"),
        ("d['returned_qty']=='1'", "d['returned_qty']=='2'"),
    ),
    ('initial', '_assert_quote'): (
        ("'JOURNAL_EXPECTED', '200.00', '10.00'), p", "'JOURNAL_EXPECTED', '200.00', '20.00'), p"),
    ),
    ('initial', '_assert_actual'): (
        ('== (6, True)', '== (7, True)'),
        ("== (6, D('60.00'))", "== (7, D('70.00'))"),
        ("'SALE_RETURN', f['product'], f['lot'], f['destination'], 'GRADE_A', 1, D('10.00')",
         "'SALE_RETURN', f['product'], f['lot'], f['destination'], 'GRADE_A', 2, D('10.00')"),
        ("(native.cmd.mapping(cur, 'FG_INVENTORY'), D('10.00')), (native.cmd.mapping(cur, 'COGS'), D('-10.00'))",
         "(native.cmd.mapping(cur, 'FG_INVENTORY'), D('20.00')), (native.cmd.mapping(cur, 'COGS'), D('-20.00'))"),
    ),
    ('signed', '_setup'): ((SETUP_ANCHOR, SETUP_TWO_PIECES),),
    ('consumer', 'prepare'): (),
}


def derived_sources():
    """Fail closed on any source/anchor drift; return inspectable Python only."""
    texts = {}
    for key, (path, digest) in SOURCES.items():
        raw = (ROOT/path).read_bytes()
        if sha256(raw).hexdigest() != digest:
            raise ValueError('D1_FIXTURE_RETAINED_SOURCE_CHANGED:' + path)
        texts[key] = raw.decode()
    answer = {}
    for (module, name), changes in TRANSFORMS.items():
        tree = ast.parse(texts[module])
        functions = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
        if len(functions) != 1:
            raise ValueError('D1_FIXTURE_EXACT_FUNCTION_REQUIRED:' + name)
        before = ast.get_source_segment(texts[module], functions[0])
        after = before
        for old, new in changes:
            if after.count(old) != 1:
                raise ValueError('D1_FIXTURE_EXACT_ANCHOR_CHANGED:' + name + ':' + old)
            after = after.replace(old, new, 1)
        reverse = after
        for old, new in reversed(changes):
            if reverse.count(new) != 1:
                raise ValueError('D1_FIXTURE_EXACT_REVERSE_ANCHOR_CHANGED:' + name)
            reverse = reverse.replace(new, old, 1)
        if reverse != before:
            raise ValueError('D1_FIXTURE_NOT_EXACTLY_REVERSIBLE:' + name)
        # Every old assertion remains. Only setup adds the explicit draft checks.
        old_asserts = sum(isinstance(n, ast.Assert) for n in ast.walk(ast.parse(before)))
        new_asserts = sum(isinstance(n, ast.Assert) for n in ast.walk(ast.parse(after)))
        if new_asserts != old_asserts + (3 if name == '_setup' else 0):
            raise ValueError('D1_FIXTURE_ASSERTION_SET_CHANGED:' + name)
        answer[module + '.' + name] = dict(before=before, after=after,
            original_sha256=sha256(before.encode()).hexdigest(), derived_sha256=sha256(after.encode()).hexdigest(),
            substitutions=len(changes), original_assertions=old_asserts, derived_assertions=new_asserts)
    if sum(row['substitutions'] for row in answer.values()) != 10 or len(answer) != 5:
        raise ValueError('D1_FIXTURE_EXACT_TEN_SUBSTITUTIONS_REQUIRED')
    return answer


def inventory():
    return dict(contract=CONTRACT, classification='PREPARED_ACTUAL_NATIVE_FIXTURE_NOT_EXECUTED_BY_IMPORT',
        Native_execution=False, frozen_sources={path: digest for path, digest in SOURCES.values()},
        functions={key: {k: v for k, v in row.items() if k not in ('before', 'after')}
                   for key, row in derived_sources().items()}, substitutions=10,
        preserved='all monetary/history/source/period/journal assertions; unitHPP10; no posted seeding or module monkeypatch')


def _private_module(module, source_key, sources, **overrides):
    # A cached import from another checkout must not supply unchecked globals.
    # Identical frozen bytes at an alternate path are legitimate.
    imported = Path(module.__file__).read_bytes()
    if sha256(imported).hexdigest() != SOURCES[source_key][1]:
        raise ValueError('D1_FIXTURE_IMPORTED_GLOBALS_SOURCE_CHANGED:' + source_key)
    namespace = dict(vars(module), **overrides)
    namespace['__name__'] = 'cp7_credit_correction_de._fixture_' + source_key
    namespace['CONTRACT'] = CONTRACT
    for name in [name for key, name in TRANSFORMS if key == source_key]:
        exec(compile(sources[source_key + '.' + name]['after'], str(ROOT/SOURCES[source_key][0]), 'exec'), namespace)
    return SimpleNamespace(**namespace)


def prepare(cur, today, initial_mode='CREDIT'):
    sources = derived_sources()
    # Only function globals are private. Shared imports retain their exact values.
    own_native = _private_module(native, 'native', sources)
    own_initial = _private_module(retained.signed.initial, 'initial', sources, native=own_native)
    own_signed = _private_module(retained.signed, 'signed', sources, native=own_native, initial=own_initial)
    own_consumer = _private_module(retained, 'consumer', sources, native=own_native, signed=own_signed)
    pair = own_consumer.prepare(cur, today, initial_mode)
    pair['D1_fixture_derivation'] = inventory()
    return pair
