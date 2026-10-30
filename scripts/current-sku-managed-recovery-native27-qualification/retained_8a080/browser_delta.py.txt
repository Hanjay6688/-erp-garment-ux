"""Exact a18 first-failure successor: named comboboxes and Native prepare RC.

No product change, response fixture, financial assertion or observation-census
change. The three wrapped selects have correct accessible names; Playwright's
label-text selector includes option text. Role selectors retain exact names.
"""
from hashlib import sha256
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
NS = 'scripts/current-sku-managed-recovery-native27-qualification'
LOCATORS = (
    ("getByLabel('SKU padanan',{exact:true})", "getByRole('combobox',{name:'SKU padanan',exact:true})", 2),
    ("getByLabel('SKU tujuan',{exact:true})", "getByRole('combobox',{name:'SKU tujuan',exact:true})", 5),
    ("getByLabel('SKU asal dan gudang',{exact:true})", "getByRole('combobox',{name:'SKU asal dan gudang',exact:true})", 2),
)
ROUTE = ("from '../current-staged-ai-browser-qualification/cases.mjs'", "from './staged_ai_cases.mjs'", 1)
STAGED = {
    'staged_ai_cases.mjs': ('scripts/current-staged-ai-browser-qualification/cases.mjs',
        '6d28e7da173c4170f9441f55c9f39b56b34779dc17ba930abee4fb680ba2b5d7',
        "resolve(HERE,'fixture.py')", "resolve(HERE,'staged_ai_fixture.py')"),
    'staged_ai_fixture.py': ('scripts/current-staged-ai-browser-qualification/fixture.py',
        '06ca4d87cad916c7af3663e3239beca7761ed3588abd28b1fc6b2e12ba8136b9',
        "cur.execute('set transaction isolation level repeatable read')",
        "cur.execute('set transaction isolation level read committed' if op == 'prepare' else 'set transaction isolation level repeatable read')"),
}


def changes(key):
    return LOCATORS if key == 'browser' else (ROUTE,) if key == 'cases' else ()


def adapt(text, key, *, reverse=False):
    items = changes(key)
    for before, after, count in reversed(items) if reverse else items:
        a, b = (after, before) if reverse else (before, after)
        if text.count(a) != count or b in text:
            raise ValueError('SKU27_BROWSER_EXACT_COUNTED_CHANGE:' + key + ':' + a)
        text = text.replace(a, b)
    return text


def staged(name):
    path, expected, before, after = STAGED[name]
    raw = (ROOT / path).read_bytes()
    if sha256(raw).hexdigest() != expected:
        raise ValueError('SKU27_FROZEN_STAGED_SOURCE_CHANGED:' + path)
    text = raw.decode()
    if text.count(before) != 1 or after in text:
        raise ValueError('SKU27_STAGED_EXACT_ONE_ANCHOR:' + name)
    derived = text.replace(before, after, 1)
    if derived.replace(after, before, 1) != text:
        raise ValueError('SKU27_STAGED_REVERSE_NOT_EXACT:' + name)
    if name.endswith('.py'): compile(derived, str(HERE / name), 'exec')
    return derived, dict(source=path, original_sha256=expected,
        derived_sha256=sha256(derived.encode()).hexdigest(), counted_changes=1,
        byte_exact_reversible=True, financial_and_full_census_assertions_unchanged=True)


def verify():
    proofs = {}
    manifest=json.loads((HERE/'retained_a18/SOURCE.json').read_bytes())
    for key in ('browser','cases'):
        original=(HERE/'retained_a18'/(key+'.mjs')).read_bytes()
        expected=manifest['files'][NS+'/'+key+'.mjs']
        if len(original)!=expected['bytes']or sha256(original).hexdigest()!=expected['sha256']:
            raise ValueError('SKU27_RETAINED_A18_BROWSER_BYTES_CHANGED:'+key)
        if (HERE/(key+'.mjs')).read_bytes()!=adapt(original.decode(),key).encode():
            raise ValueError('SKU27_ACTUAL_BROWSER_CALLER_DERIVATIVE_CHANGED:'+key)
    for name in STAGED:
        text, proof = staged(name)
        if (HERE / name).is_symlink() or (HERE / name).read_bytes() != text.encode():
            raise ValueError('SKU27_STAGED_DERIVED_PHYSICAL_BYTES_CHANGED:' + name)
        proofs[name] = proof
    retained = json.loads((HERE / 'FIRST_A18_BROWSER_FAILURE.json').read_bytes())
    if retained['head'] != 'a18ceb797840934f2cc45222b704b581a00cecf0' or retained['counts'] != {'PASS': 23, 'INCOMPLETE': 4}:
        raise ValueError('SKU27_FIRST_A18_FAILURE_MUST_REMAIN_FAILED')
    return dict(status='EXACT_A18_BROWSER_FIRST_FAILURE_SOURCE_SUCCESSOR_ONLY',
        named_combobox_locator_changes=9, exact_accessible_names_retained=True,
        stage_cases_route_changes=1, staged_derivations=proofs,
        actual_materialized_SKU_and_staged_caller_routes_exact=True,
        prepare_isolation='READ COMMITTED', state_and_read_isolation='REPEATABLE READ',
        product_sources_changed=0, financial_oracles_changed=0,
        original_browser_journey_whole_body_identity_claim=False,
        actual_new_browser_cases=0, actual_new_Native_cases=0,
        production_go=False, independent_acceptance=False)
