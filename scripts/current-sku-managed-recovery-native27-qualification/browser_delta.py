"""Exact a18 first-failure successor: named comboboxes and Native prepare RC.

No product change, response fixture, financial amount or observation-census
change. Wrapped selects have correct accessible names; Playwright's
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
DISPLAY = ("toContainText('nilai sumber Rp60,06')", "toContainText('nilai sumber Rp 60,06')", 1)
STAGED_GROUP = ("getByLabel('Pengelompokan',{exact:true})", "getByRole('combobox',{name:'Pengelompokan',exact:true})", 1)
STAGED_TIMESTAMPS = (
    ("last_recorded_at:c.last_recorded_at===null?null:instant(c.last_recorded_at)",
     "last_recorded_at:c.last_recorded_at", 1),
    ("checkedAt:instant(f.last_full_check.checked_at)", "checkedAt:f.last_full_check.checked_at", 1),
)
RECOVERY_AND_HISTORY = (
    ("async function openConversion(){await menu(page,'Gudang','Ganti Merek');await expect(conversion().getByRole('heading',{name:'Ganti Merek / SKU',exact:true})).toBeVisible();await expect(conversion().getByRole('combobox',{name:'SKU asal dan gudang',exact:true})).toBeEnabled()}",
     """async function openConversion(pendingRecovery=false){
  await menu(page,'Gudang','Ganti Merek');await expect(conversion().getByRole('heading',{name:'Ganti Merek / SKU',exact:true})).toBeVisible()
  const source=conversion().getByRole('combobox',{name:'SKU asal dan gudang',exact:true})
  if(pendingRecovery){await expect(source).toBeDisabled();await expect(conversion().getByRole('button',{name:'Reconcile transaksi',exact:true})).toBeEnabled()}
  else await expect(source).toBeEnabled()
 }""", 1),
    ("await page.unroute(endpoint);await page.reload();await openConversion()",
     "await page.unroute(endpoint);await page.reload();await openConversion(true)", 1),
    ("  let posted=state('POSTED');postedOracle(posted,f,made)",
     "  await expect(conversion().getByRole('combobox',{name:'SKU asal dan gudang',exact:true})).toBeEnabled()\n  let posted = state('POSTED');postedOracle(posted,f,made)", 1),
    ("  await row.getByRole('button',{name:'Batalkan '+f.products.source.sku,exact:true}).click()",
     "  await expect(row).toContainText(f.group_labels[groupSource].sku+' → '+f.group_labels[groupTarget].sku);await expect(row).toContainText('POSTED')\n  await row.getByRole('button',{name:'Batalkan '+f.group_labels[groupSource].sku,exact:true}).click()", 1),
)
STAGED = {
    'staged_ai_cases.mjs': ('scripts/current-staged-ai-browser-qualification/cases.mjs',
        '6d28e7da173c4170f9441f55c9f39b56b34779dc17ba930abee4fb680ba2b5d7',
        "resolve(HERE,'fixture.py')", "resolve(HERE,'staged_ai_fixture.py')"),
    'staged_ai_fixture.py': ('scripts/current-staged-ai-browser-qualification/fixture.py',
        '06ca4d87cad916c7af3663e3239beca7761ed3588abd28b1fc6b2e12ba8136b9',
        "cur.execute('set transaction isolation level repeatable read')",
        "cur.execute('set transaction isolation level read committed' if op in ('prepare', 'read') else 'set transaction isolation level repeatable read')"),
}


def changes(key):
    return LOCATORS + (DISPLAY,) + RECOVERY_AND_HISTORY if key == 'browser' else (ROUTE,) if key == 'cases' else ()


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
    reverse = derived
    extra = 0
    if name == 'staged_ai_cases.mjs':
        edits = (STAGED_GROUP,) + STAGED_TIMESTAMPS
        for old, new, count in edits:
            if derived.count(old) != count or new in derived.replace(old, ''):
                raise ValueError('SKU27_STAGED_EXACT_GROUP_OR_TIMESTAMP_ANCHOR_REQUIRED')
            derived = derived.replace(old, new, count)
        reverse = derived
        for old, new, count in reversed(edits):
            reverse = reverse.replace(new, old, count)
        extra = sum(count for _, _, count in edits)
    if reverse.replace(after, before, 1) != text:
        raise ValueError('SKU27_STAGED_REVERSE_NOT_EXACT:' + name)
    if name.endswith('.py'): compile(derived, str(HERE / name), 'exec')
    return derived, dict(source=path, original_sha256=expected,
        derived_sha256=sha256(derived.encode()).hexdigest(), counted_changes=1 + extra,
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
    latest = json.loads((HERE / 'FIRST_8A080_BROWSER_FAILURE.json').read_bytes())
    if latest['head'] != '8a08024fda704162481e3123efa5fa7fbfc5663d' or latest['browser_counts'] != {'INCOMPLETE': 4}:
        raise ValueError('SKU27_FIRST_8A080_FAILURE_MUST_REMAIN_FAILED')
    current = json.loads((HERE / 'FIRST_0938_BROWSER_FAILURE.json').read_bytes())
    if current['head'] != '0938b693dee868ba74323f4ff61db70efdd11e89' or current['browser_counts'] != {'INCOMPLETE': 4}:
        raise ValueError('SKU27_FIRST_0938_FAILURE_MUST_REMAIN_FAILED')
    latest = json.loads((HERE / 'FIRST_E925_TIMESTAMP_FAILURE.json').read_bytes())
    if (latest['head'] != 'e9256772579f387df77dde949f8ea619cbd86856'
            or latest['browser_counts'] != {'PASS': 2, 'INCOMPLETE': 2}
            or latest['complete27_qualified'] is not False
            or latest['archive']['sha256'] != '06d8605b40b05c62b6a9cc7115444560f403d6c1844aa114e901e76a26ac9ac0'):
        raise ValueError('SKU27_FIRST_E925_FAILURE_MUST_REMAIN_FAILED')
    return dict(status='EXACT_A18_BROWSER_FIRST_FAILURE_SOURCE_SUCCESSOR_ONLY',
        named_combobox_locator_changes=9, exact_accessible_names_retained=True,
        staged_group_combobox_changes=1, currency_display_whitespace_changes=1,
        staged_lossless_timestamp_copy_assertion_changes=2,
        recovery_and_history_counted_changes=len(RECOVERY_AND_HISTORY),
        pending_recovery_requires_locked_source_and_enabled_reconcile=True,
        authoritative_recovery_requires_enabled_source=True,
        inverse_matches_exact_document_and_current_fixture_commercial_labels=True,
        expected_source_value_still='60.06', Native_financial_oracles_unchanged=True,
        stage_cases_route_changes=1, staged_derivations=proofs,
        actual_materialized_SKU_and_staged_caller_routes_exact=True,
        prepare_isolation='READ COMMITTED', read_isolation='READ COMMITTED', state_isolation='REPEATABLE READ',
        product_sources_changed=0, financial_oracles_changed=0,
        original_browser_journey_whole_body_identity_claim=False,
        actual_new_browser_cases=0, actual_new_Native_cases=0,
        production_go=False, independent_acceptance=False)
