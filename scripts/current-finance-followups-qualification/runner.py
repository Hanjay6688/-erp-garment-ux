"""Two isolated diagnostics share one verified installation, never their data."""
from pathlib import Path
import importlib.util
import psycopg

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
INSTALLED_DUMP = '/tmp/d17_18_followups_unused_installed.dump'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


visibility = load('followup_visibility_case', ROOT / 'scripts/current-finance-source-visibility-diagnostic/runner.py')
single = load('followup_single_check_case', ROOT / 'scripts/current-finance-single-check-diagnostic/runner.py')
isolated = load('followup_isolation_contract', HERE / 'isolated_cases.py')
retained = load('followup_retained_restore_dependencies', ROOT / 'scripts/current-analog-consumer-opening-qualification/probe.py')
product = load('followup_readonly_product', ROOT / 'scripts/current-finance-readonly-integration-qualification/composition.py')
scheduler_quiet = visibility.race.scheduler_quiet
CASE = 'FINANCE_CHILD_VISIBILITY_AND_SINGLE_CHECK_ISOLATED_DIAGNOSTICS'
CHILDREN = ((visibility.CASE, visibility.exercise), (single.CASE, single.exercise))


def exercise(conn, cur, database, url, report, installation_state):
    assert conn.info.host in ('localhost', '127.0.0.1') and conn.info.port == 54322
    assert cur.execute('select current_database()').fetchone() == ('cp6_rollback',)
    conn.rollback()
    # Complete-database restoration requires no borrowed connection to survive.
    conn.close()
    predecessor, _, _, _ = product.runtime()
    catalog = predecessor.catalog
    with psycopg.connect(url) as baseline, baseline.cursor() as b:
        before_catalog = catalog._portable(catalog._catalog_rows(b))
        before_data = catalog._data(b)
        before_roles = database._roles(b)
        baseline.rollback()
    before_hashes = retained.drill.data_hashes(database.SOURCE)
    profile = database._database_profile(database.SOURCE)
    retained.dump.dump(database.SOURCE, INSTALLED_DUMP)
    report.update(case_id=CASE, status='INCOMPLETE', diagnostic_only=True,
                  shared_installation_only=True, shared_fixture_data=False,
                  actual_cron_claim=False, production_go=False,
                  independent_acceptance=False, product_adoption=False,
                  performance_qualification=False, factory3600_claim=False)

    def run(operation, result):
        with psycopg.connect(url) as current, current.cursor() as c:
            assert catalog._portable(catalog._catalog_rows(c)) == before_catalog
            assert catalog._data(c) == before_data
            assert database._roles(c) == before_roles
            current.rollback()
            operation(current, c, database, url, result)

    def restore():
        quiet = scheduler_quiet(url)
        with psycopg.connect(url) as current, current.cursor() as c:
            actual = catalog._data(c)
            changed = actual != before_data
            if changed:
                held = catalog._catalog_rows(c)
                try:
                    product.rollback_preuse(c, installation_state)
                except ValueError as error:
                    assert str(error) == product.USED_ERROR
                else:
                    raise AssertionError('FOLLOWUP_USED_INVERSE_NOT_REFUSED')
                assert catalog._catalog_rows(c) == held and catalog._data(c) == actual
            current.rollback()
        restored = database._restore(INSTALLED_DUMP, database.SOURCE, profile)
        assert restored['only_pg_cron_errors']
        assert retained.drill.data_hashes(database.SOURCE) == before_hashes
        with psycopg.connect(url) as current, current.cursor() as c:
            assert catalog._portable(catalog._catalog_rows(c)) == before_catalog
            assert catalog._data(c) == before_data
            assert database._roles(c) == before_roles
            current.rollback()
        return dict(all22_all_rows_all_sequences_roles_exact=True,
                    complete_database_dump_restored=True, scheduler_quiet=quiet,
                    restore=restored, selected_table_cleanup=False,
                    used_guard_applicable=changed, used_guard_refused_before_DDL=changed)

    try:
        isolated.exercise(CHILDREN, run, restore, report)
    finally:
        retained.drill.docker('rm', '-f', INSTALLED_DUMP, check=False)
    assert all(c['installed_baseline_restoration']['used_guard_refused_before_DDL']
               for c in report['cases'].values()), 'FOLLOWUP_BOTH_COMMITTED_FIXTURES_REQUIRED'
    report.update(status='PASS', diagnostic_collection_completed=True,
                  source_visibility_case_pass=True, single_check_comparison_pass=True,
                  used_guard_refused_before_DDL=True)
