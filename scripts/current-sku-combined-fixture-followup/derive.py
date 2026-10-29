"""Bounded private source derivation; frozen c163 modules are never mutated.

Only the existing random administrative brand tag enters its display name.
All other changes route private imports or close a historical scope endpoint.
Each complete module is compiled into its own namespace, with its original
file location so every undeclared relative dependency keeps its old meaning.
"""
from hashlib import sha256
from pathlib import Path
import ast

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-sku-combined-fixture-followup'
BASE = 'c163c1e9ff8f00b8dd8859c32aee0c2069766ad6'
TREE = 'c986f32ad995d69ff1d0a5fba63689b543172f77'
BRANCH = 'astra-a/sku-combined-unique-fixture-20261029'

# This inventory is fixed against c163 before materialization. It must never
# be filled from new current bytes by runtime admission.
SOURCES = {
    'fixture': ('scripts/current-sku-pair-conversion-qualification/fixture.py', '707c579a2bd923466fd0badb2bd09897634501d18b42f8b87c553ba19559ad8e'),
    'cost_native': ('scripts/current-sku-group-cost-qualification/native_fixture.py', '12871fbcf27caa62042c0bcd5b8c80ed81ae84ff014af64fdd26703853d51891'),
    'cost_cases': ('scripts/current-sku-group-cost-qualification/cases.py', '0536eda078071b8b9e87604ee1c722f34157c2b1d34adac8e6a483e5470a9e0c'),
    'races': ('scripts/current-sku-pair-conversion-qualification/races.py', '10361a994d0d26357399f9f7625e5b1828bc8d02a796609b12ff7567e7a034e8'),
    'auth_waits': ('scripts/current-sku-pair-conversion-qualification/auth_waits.py', '5e4e7d4d6f0e71da0817dec670d9e31b8bef9987f683eaf35c7ef198dbfec351'),
    'concurrency': ('scripts/current-sku-pair-concurrency-qualification/runner.py', 'bae687cb3faffc08cfed294b0106b134d8ad3de11d36612a05212644eb3cad8c'),
    'browser_fixture': ('scripts/current-sku-pair-browser-qualification/fixture.py', '4474517f582381deaffda79fb3a9bc187e55dc32e4b213e15ed372930cd91450'),
    'runner': ('scripts/current-sku-combined-followup-qualification/runner.py', '56da9dc93e51050e83fc2e8267f213a3c5ee3f506f92f8ec3ba471996b0fa8a2'),
    'probe': ('scripts/current-sku-combined-followup-qualification/probe.py', '14556c5249689336eaa6bbb29302558238559a4f7274a32129f5bc615e824fae'),
    'historical_admission': ('scripts/current-sku-combined-followup-qualification/admission.py', 'f040f7a7020e0a3d5f811ca5f4508641c84dfa6eda34fd94fa4d74edee80af55'),
    'browser': ('scripts/current-sku-pair-browser-qualification/browser.mjs', '436a3eb2ac8a75c1e6e6eeac1e9c3e49f9cb8b15d8cee833f8df9bfdf7ce313e'),
    'cases': ('scripts/current-sku-combined-followup-qualification/cases.mjs', 'f7c8d60d65de3a543530e6c2039280b43a0c8c676725a21ca3fd8aa11d38ca57'),
}
REPLACEMENTS = {
    'fixture': ((
        "cur.execute(\"insert into erp.brands(id,brand_code,brand_name,is_active)values(%s,%s,'SKU29 different brand',true)\",(brand,'S29B-'+tag))",
        "cur.execute(\"insert into erp.brands(id,brand_code,brand_name,is_active)values(%s,%s,%s,true)\",(brand,'S29B-'+tag,'SKU29 different brand '+tag))",
    ),),
    'cost_native': (("ROOT/'scripts/current-sku-pair-conversion-qualification/fixture.py'", "ROOT/'" + NS + "/fixture.py'"),),
    'cost_cases': (("HERE/'native_fixture.py'", "HERE.parent/'current-sku-combined-fixture-followup'/'cost_native.py'"),),
    'races': (("HERE/'fixture.py'", "HERE.parent/'current-sku-combined-fixture-followup'/'fixture.py'"),),
    'auth_waits': (("HERE/'fixture.py'", "HERE.parent/'current-sku-combined-fixture-followup'/'fixture.py'"),),
    'concurrency': (
        ("load('sku_concurrency_original_races', CALLBACKS / 'races.py')", "load('sku_concurrency_original_races', ROOT / '" + NS + "/races.py')"),
        ("load('sku_concurrency_original_permission_waits', CALLBACKS / 'auth_waits.py')", "load('sku_concurrency_original_permission_waits', ROOT / '" + NS + "/auth_waits.py')"),
    ),
    'browser_fixture': (("ROOT/'scripts/current-sku-pair-conversion-qualification/fixture.py'", "ROOT/'" + NS + "/fixture.py'"),),
    'runner': (
        ("ROOT / 'scripts/current-sku-group-cost-qualification/cases.py'", "ROOT / '" + NS + "/cost_cases.py'"),
        ("ROOT / 'scripts/current-sku-pair-concurrency-qualification/runner.py'", "ROOT / '" + NS + "/concurrency.py'"),
        ("script=HERE / 'cases.mjs'", "script=ROOT / '" + NS + "/cases.mjs'"),
    ),
    'probe': (
        ("HERE / 'runner.py'", "ROOT / '" + NS + "/runner.py'"),
        ("HERE / 'admission.py'", "ROOT / '" + NS + "/admission.py'"),
    ),
    'historical_admission': ((
        "'diff', '--name-only', gate.BASE, 'HEAD'",
        "'diff', '--name-only', gate.BASE, '" + BASE + "'",
    ),),
    'browser': (
        ("from './evidence.mjs'", "from '../current-sku-pair-browser-qualification/evidence.mjs'"),
        ("../auditor/scripts/current-sku-pair-browser-qualification/fixture.py", "../auditor/" + NS + "/browser_fixture.py"),
    ),
    'cases': (("from '../current-sku-pair-browser-qualification/browser.mjs'", "from './browser.mjs'"),),
}


def derive(key, raw=None):
    relative, expected = SOURCES[key]
    raw = (ROOT / relative).read_bytes() if raw is None else raw
    if sha256(raw).hexdigest() != expected:
        raise ValueError('SKU_UNIQUE_FROZEN_SOURCE_CHANGED:' + relative)
    text = raw.decode()
    for before, after in REPLACEMENTS[key]:
        if text.count(before) != 1 or after in text:
            raise ValueError('SKU_UNIQUE_EXACT_ONE_ANCHOR_REQUIRED:' + key)
        text = text.replace(before, after, 1)
    inverse = text
    for before, after in reversed(REPLACEMENTS[key]):
        if inverse.count(after) != 1:
            raise ValueError('SKU_UNIQUE_EXACT_REVERSAL_REQUIRED:' + key)
        inverse = inverse.replace(after, before, 1)
    assert inverse.encode() == raw
    if relative.endswith('.py'):
        old, new = ast.parse(raw), ast.parse(text)
        assert sum(isinstance(n, ast.Assert) for n in ast.walk(old)) == sum(isinstance(n, ast.Assert) for n in ast.walk(new))
        compile(text, str(ROOT / relative), 'exec')
    return text, dict(key=key, source=relative, original_sha256=expected,
        derived_sha256=sha256(text.encode()).hexdigest(), counted_changes=len(REPLACEMENTS[key]),
        byte_exact_reversible=True, assertions_removed=0,
        administrative_name_changes=1 if key == 'fixture' else 0)


def execute(key, namespace):
    text, proof = derive(key)
    namespace['__file__'] = str(ROOT / SOURCES[key][0])
    namespace['__SKU_UNIQUE_DERIVATION__'] = proof
    exec(compile(text, namespace['__file__'], 'exec'), namespace)


def inventory():
    result = {key: derive(key)[1] for key in SOURCES}
    assert sum(row['counted_changes'] for row in result.values()) == 17
    assert sum(row['administrative_name_changes'] for row in result.values()) == 1
    return result
