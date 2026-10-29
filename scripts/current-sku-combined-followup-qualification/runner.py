"""One installed SKU: base Native7, cost Native3, race3/wait6, full-App browser4."""
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import os
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CASE = 'SKU_BASE_NATIVE7_COST_NATIVE3_RACES3_NATIVE_WAITS6_AUTH_BROWSER4'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


gate = load('sku_combined_group_gate', HERE / 'gate.py')


def scheduler_quiet(url):
    return load('sku_combined_existing_quiet', ROOT / 'scripts/current-vendor-receivable-qualification/native_runner.py').scheduler_quiet(url)


def snapshot(url, state, product):
    import psycopg
    from cp7_p21_current_chain_rehearsal_probe import helper
    catalog = product.runtime()[-1]
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        raw, data = catalog._catalog_rows(cur), catalog._data(cur)
        with helper.control.product_catalog(cur): product.verify(cur, state)
        conn.rollback()
    return dict(catalog=raw, data=data)


def cost_group(state, first, retained, report):
    from cp7_p21_current_chain_rehearsal_probe import helper
    from cp7_sku_pair_conversion import composition as product
    from cp7_catalog_state import exact_public_catalog
    cost = load('sku_combined_unchanged_cost_callbacks', ROOT / 'scripts/current-sku-group-cost-qualification/cases.py')
    report['dependency'] = cost.admit_native7(first['native'], original_report_sha256=retained['original_sha256'], backend_commit=gate.BASE)
    def verify(cur):
        with helper.control.product_catalog(cur): return product.verify(cur, state)
    label = 'CP7_SKU_GROUP_COST_NATIVE3'
    try:
        with exact_public_catalog(helper.control.native, retain_raw=True) as public:
            actual = helper.control.native.strict_group(label, cost.cases, verify)
    finally:
        # Retain the exact frozen runner's own outputs on an incomplete group.
        out = ROOT / 'cp6-proof/t3'; out.mkdir(parents=True, exist_ok=True)
        for name in (label + '.json', label + '_BUSINESS_DAY_FIRST_ATTEMPT.json'):
            original = helper.control.native.r1.OUT / name
            if original.is_file(): (out / name).write_bytes(original.read_bytes())
    report.update(native=actual, public_catalog_observation=public)
    gate.exact_native(actual, cost.IDS, 3)
    safety = actual['cases'][cost.IDS[0]]
    assert safety['group_recovery_supported'] is False and safety['full_group_recovery_acceptance'] is False
    report.update(status='PASS', actual_cost_Native_cases=3, group_recovery_supported=False,
                  recovery_case_scope='SAFETY_REFUSAL_ONLY')


def browser_group(conn, cur, database, url, report, state):
    from cp7_sku_pair_conversion import composition as product
    browser = load('sku_combined_existing_Auth_browser_runner', ROOT / 'scripts/current-vendor-money-browser/runner.py')
    browser.product = product  # Child caller; retained runner file stays exact.
    ids = load('sku_combined_prepared_plan', HERE / 'plan.py').BROWSER_IDS
    assert os.environ.get('AUDITOR_UI_MODE', 'DISPOSABLE') == 'DISPOSABLE'
    assert Path(os.environ['D17_18_SELECTED_BACKEND_ROOT']).resolve() == ROOT
    prior = os.environ.get('AUDITOR_BROWSER_CASE_TIMEOUT_MS')
    os.environ['AUDITOR_BROWSER_CASE_TIMEOUT_MS'] = '600000'
    try:
        browser.exercise_browser(conn, cur, database, url, report, state, script=HERE / 'cases.mjs', ids=ids, tag='sku_combined4')
    finally:
        if prior is None: os.environ.pop('AUDITOR_BROWSER_CASE_TIMEOUT_MS', None)
        else: os.environ['AUDITOR_BROWSER_CASE_TIMEOUT_MS'] = prior
    gate.browser(report['browser'], ids)
    report.update(used_guard_evidence='FRESH_SAME_INSTALLATION_NATIVE7_AND_CALLBACKS9',
                  actual_Auth_browser_cases=4, actual_Auth_HTTP_cases=0)


def exercise(conn, cur, database, url, report, state):
    import psycopg
    from cp7_sku_pair_conversion import composition as product
    admission = load('sku_combined_runtime_retained_admission', HERE / 'admission.py')
    retained = admission.retained(product)
    report.update(status='INCOMPLETE', retained_native_prerequisite=retained, production_go=False, independent_acceptance=False)
    native = load('sku_combined_unchanged_fresh_native7', ROOT / 'scripts/current-sku-pair-conversion-qualification/runner.py')
    first = report.setdefault('fresh_base_native7', dict(status='INCOMPLETE'))
    native.exercise(conn, cur, database, url, first, state)
    ids = load('sku_combined_actual_plan', HERE / 'plan.py').NATIVE_IDS
    gate.exact_native(first.get('native', {}), ids, 7)
    assert first['status'] == 'PASS' and first['used_guard_refused_before_DDL'] is True
    before = snapshot(url, state, product)
    cost = report.setdefault('fresh_cost_native3', dict(status='INCOMPLETE'))
    cost_group(state, first, retained, cost)
    cost_ids = load('sku_combined_cost_plan', HERE / 'plan.py').COST_IDS
    gate.exact_native(cost.get('native', {}), cost_ids, 3)
    assert cost['status'] == 'PASS' and cost['group_recovery_supported'] is False
    assert snapshot(url, state, product) == before, 'SKU_COMBINED_COST_NATIVE_SAVEPOINT_CHANGED_SOURCE_ROWS_OR_CATALOG'
    follow = load('sku_combined_unchanged_callbacks9', ROOT / 'scripts/current-sku-pair-concurrency-qualification/runner.py')
    second = report.setdefault('fresh_callbacks9', dict(status='INCOMPLETE'))
    with psycopg.connect(url) as current, current.cursor() as cursor:
        follow.exercise(current, cursor, database, url, second, state, native7=first)
    assert second['status'] == 'PASS'
    plans = load('sku_combined_callback_plan', HERE / 'plan.py')
    assert second['concurrency']['counts'] == {'PASS': 9}
    assert set(second['concurrency']['races']) == set(plans.RACE_IDS + plans.WAIT_IDS)
    assert all(row['status'] == 'PASS' for row in second['concurrency']['races'].values())
    after_callbacks = snapshot(url, state, product)
    assert after_callbacks['data'] == before['data'] and after_callbacks['catalog'] == state['after']
    catalog = product.runtime()[-1]
    raw_sha = catalog.digest(after_callbacks['catalog'])
    assert len(second['copy_catalog_admissions']) == 9
    assert all(row['all22_groups_equal_original_install'] is True and row['exact_catalog_sha256'] == raw_sha for row in second['copy_catalog_admissions'])
    report['Native_to_copy_handoff'] = dict(second['handoff'], source_all_rows_sequences_unchanged_after_callbacks=True,
        raw_current_catalog=after_callbacks['catalog'], raw_current_catalog_sha256=raw_sha,
        raw_native_before_handoff_sha256=catalog.digest(before['catalog']),
        full_data_and_sequences_before_handoff=before['data'], full_data_and_sequences_after_callbacks=after_callbacks['data'],
        every_race_copy_exact_admission_sha256=[row['exact_catalog_sha256'] for row in second['copy_catalog_admissions']])
    third = report.setdefault('fresh_real_Auth_browser4', dict(status='INCOMPLETE'))
    with psycopg.connect(url) as current, current.cursor() as cursor:
        browser_group(current, cursor, database, url, third, state)
    assert third['status'] == 'PASS'
    gate.browser(third['browser'], plans.BROWSER_IDS)
    assert len(third['copy_catalog_admissions']) == 1
    assert all(row['all22_groups_equal_original_install'] is True and row['exact_catalog_sha256'] == raw_sha for row in third['copy_catalog_admissions'])
    report['Native_to_copy_handoff']['browser_copy_exact_admission_sha256'] = third['copy_catalog_admissions'][0]['exact_catalog_sha256']
    assert snapshot(url, state, product) == after_callbacks, 'SKU_COMBINED_BROWSER_CHANGED_NATIVE_SOURCE_DATABASE'
    groups = (first['native']['cases'], cost['native']['cases'], second['concurrency']['races'], third['browser']['cases'])
    cases = {key: dict(status=value['status']) for group in groups for key, value in group.items()}
    assert sum(map(len, groups)) == len(cases) == 23 and all(row['status'] == 'PASS' for row in cases.values())
    report.update(status='PASS', business_cases=cases, business_counts={'PASS': 23}, actual_Native_cases=10,
                  base_Native_cases=7, cost_Native_cases=3, actual_two_session_races=3,
                  actual_Native_session_permission_waits=6, actual_Auth_HTTP_cases=0, actual_browser_cases=4,
                  used_guard_refused_before_DDL=True, group_recovery_supported=False,
                  permission_wait_fixture='ADMINISTRATIVE_APPLICATION_ACTOR_NOT_REAL_AUTH',
                  acceptance_requires_complete_outer_restore_and_five_package_gates=True)
