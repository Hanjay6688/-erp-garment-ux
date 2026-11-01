"""Prepared normal-App reader witness; the qualified outer caller owns use.

Fixtures are created on the actual SKU parent before installing the reader.
The browser receives a committed copy with the reader already installed, so
there is no DDL or schema-cache race inside a screen journey.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
import importlib.util
import json
import os

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IDS = ('PERMANENT_S05_SKU_NORMAL_APP_DESKTOP_SOURCE_AND_LATE_REPLY',
       'PERMANENT_S05_SKU_NORMAL_APP_MOBILE390_UNKNOWN_ZERO_AND_CURRENT_ACCESS')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def save(name, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, default=str)+'\n').encode()
    path = ROOT/'cp6-proof/t3'/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    return dict(name=name, bytes=len(raw), sha256=sha256(raw).hexdigest())


@contextmanager
def environment(report):
    changes = {'S05_SKU_BROWSER_CONFIRM': 'cp6_auditor_browser', 'AUDITOR_BROWSER_CASE_TIMEOUT_MS': '600000',
               'S05_SKU_BROWSER_FIXTURES_SHA256': report['browser_fixture_original']['sha256'],
               'S05_SKU_BROWSER_READER_STATE_SHA256': report['browser_reader_state_original']['sha256']}
    before = {key: os.environ.get(key) for key in changes}
    os.environ.update(changes)
    try:
        yield
    finally:
        for key, value in before.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value


@contextmanager
def reader_interval(url, sku_state, report):
    import psycopg
    from cp7_current_s03_sku_s05 import composition as complete
    from cp7_p21_current_chain_rehearsal_probe import helper
    prepared = load('permanent_S05_actual_native_browser_prerequisites', HERE/'persistent_browser_prepare.py')
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        with helper.control.product_catalog(cur):
            complete.verify(cur, sku_state)
        today = cur.execute("select(statement_timestamp()at time zone'Asia/Jakarta')::date").fetchone()[0]
        fixture = prepared.prepare(cur, today, sku_state)
        report['browser_fixture_original'] = save('S05_PERMANENT_BROWSER_FIXTURES.json', fixture)
        with helper.control.product_catalog(cur):
            complete.verify(cur, sku_state)
        reader_state = sku_state['reader']
        conn.commit()
    report['browser_reader_state_original'] = save('S05_PERMANENT_BROWSER_READER_STATE.json', reader_state)
    try:
        yield reader_state
    finally:
        with psycopg.connect(url) as conn, conn.cursor() as cur:
            with helper.control.product_catalog(cur):
                report['reader_after_browser_still_installed'] = complete.verify(cur, sku_state)
            conn.rollback()

def require_browser(actual, admissions):
    if (actual.get('status') != 'RUN_COMPLETE' or actual.get('counts') != {'PASS': len(IDS)}
            or actual.get('planned_case_ids') != list(IDS) or set(actual.get('cases', {})) != set(IDS)
            or any(row.get('status') != 'PASS' for row in actual.get('cases', {}).values())
            or actual.get('error') or actual.get('host_error')):
        raise ValueError('S05_SKU_COMPLETE_FRESH_BROWSER2_REQUIRED')
    if (actual.get('database_remaining') != 0 or actual.get('cleanup_failures')
            or actual.get('auth_counts', {}).get('restored') is not True
            or actual.get('session_leaks') or actual.get('console_errors') != 0
            or actual.get('auth_cleanup_failures') != []
            or actual.get('host_exit') != 0 or actual.get('host_status') != 'RUN_COMPLETE'
            or actual.get('real_auth') is not True or actual.get('jwt_signed_by_runtime') is not False
            or len(admissions) != 1 or admissions[0].get('all22_groups_equal_original_install') is not True):
        raise ValueError('S05_SKU_COMPLETE_BROWSER_AND_AUTH_RESTORE_REQUIRED')


def exercise(url, sku_state, report, *, raw_parent_receipt):
    load('permanent_S05_requires_exact_accepted_join37', HERE/'persistent_financial.py').qualified_receipt(raw_parent_receipt)
    if os.environ.get('S05_SKU_CONFIRM') != 'cp6_rollback':
        raise ValueError('S05_SKU_EXPLICIT_OUTER_DISPOSABLE_QUALIFICATION_REQUIRED')
    parsed = urlparse(url)
    if parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.port != 54322 or parsed.path != '/cp6_rollback':
        raise ValueError('S05_SKU_LOCAL_INSTALLED_PARENT_ONLY')
    load('permanent_S05_before_browser_runtime', HERE/'persistent_source.py').preflight()
    import psycopg
    modes = load('joined_private_browser_modes', ROOT/'scripts/current-s03-sku-s05-composite-qualification/modes.py')
    import cp6_auditor_business_day as business_day
    from cp7_s05_s03_sku_composition import stage
    from cp7_p21_current_chain_rehearsal_probe import helper
    attempts = load('s05_sku_preserve_first_browser_attempt', ROOT/'scripts/current-sku-managed-recovery-native27-qualification/attempt_policy.py')
    with reader_interval(url, sku_state, report) as reader_state:
        catalog = stage.parent().runtime()[-1]

        def verify(cursor, state=reader_state):
            with helper.control.product_catalog(cursor):
                return stage.verify(cursor, state)

        # Bind the complete observed source catalog, including the inherited
        # local harness capability. Do not project or rewrite the stage state.
        with psycopg.connect(url) as conn, conn.cursor() as cur:
            verify(cur)
            copy_catalog = catalog._catalog_rows(cur)
            conn.rollback()
        report['browser_source_raw_catalog_original'] = save('S05_PERMANENT_BROWSER_SOURCE_CATALOG.json', copy_catalog)
        adapter = load('s05_sku_exact_browser_copy_authority', ROOT/'scripts/ow04-payment-current-qualification/copy_authority.py')
        previous_copy = modes.copy_db
        adapter.ORIGINAL_COPY_DATABASE = previous_copy
        adapter.PRODUCT = SimpleNamespace(catalog=catalog, verify=verify)
        adapter.STATE = dict(reader_state, installed_catalog=copy_catalog)
        try:
            modes.copy_db = adapter.copy_database
            with environment(report), attempts.single_attempt(business_day):
                report['browser'] = modes.run_browser(HERE/'persistent_browser.mjs', verify, 's05_on_sku_reader2')
        finally:
            modes.copy_db = previous_copy
            report['copy_catalog_admissions'] = list(adapter.COPY_ADMISSIONS)
        require_browser(report['browser'], adapter.COPY_ADMISSIONS)
    report.update(status='PASS', actual_browser_cases=2, actual_Native_cases=0,
        actual_Auth_HTTP_case_credit=0, actual_two_session_cases=0,
        fixture_screen_creation_claim=False, complete_outer_package_restore_still_required=True,
        Afui_positive_HPP_zero_reimbursement_coverage=False,
        production_go=False, independent_acceptance=False)
