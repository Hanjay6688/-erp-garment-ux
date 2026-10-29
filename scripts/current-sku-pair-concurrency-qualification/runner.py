"""Prepared SKU followup: existing committed-copy race engine, full restore/case.

No install, CLI, package, workflow, HTTP/Auth server, browser or new race engine.
The outer caller must first run actual Native7 + used guard on its exact SKU
installation, and still owns the complete preinstall restore/package gates.
"""
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
import ast
from hashlib import sha256
import importlib.util
import json
import sys

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CALLBACKS = ROOT / 'scripts/current-sku-pair-conversion-qualification'
CASE = 'SKU_PAIR_CONVERSION_RACES3_NATIVE_PERMISSION_WAITS6'
RACE_DB = 'cp6_auditor_race'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


controls = load('sku_concurrency_controls', HERE / 'controls.py')


def ids(path):
    tree = ast.parse(path.read_text())
    return next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'IDS' for target in node.targets))


def plan():
    races, permissions = ids(CALLBACKS / 'races.py'), ids(CALLBACKS / 'auth_waits.py')
    assert len(races) == 3 and len(permissions) == 6 and len(set(races + permissions)) == 9
    return dict(status='PREPARED', case_id=CASE, race_ids=list(races), permission_wait_ids=list(permissions),
                permission_actor_fixture='NEW_USER_EXISTING_ADMIN_NOT_OWNER; administrative rows, no real Auth login',
                actual_Native_cases=0, actual_two_session_races=0, actual_Auth_HTTP_cases=0,
                actual_browser_cases=0, full_dump_restore_after_each_case_required=True,
                production_go=False, independent_acceptance=False)


def require_local(url, name):
    parsed = urlparse(url)
    if (parsed.scheme not in ('postgres', 'postgresql') or parsed.hostname not in ('127.0.0.1', 'localhost') or
            parsed.port != 54322 or parsed.path != '/' + name or parsed.query or parsed.fragment):
        raise ValueError('SKU_CONCURRENCY_EXACT_LOCAL_DISPOSABLE_DATABASE_REQUIRED')


def admit_sources():
    declaration = json.loads((HERE / 'SOURCE.json').read_bytes())
    assert declaration['status'] == 'PREPARED' and declaration['actual_concurrency_executed'] is False
    assert declaration['input_head'] == '805922690d85818d3146966e6bcc9295d97b0f84'
    for name, expected in declaration['files'].items():
        raw = (ROOT / name).read_bytes()
        if len(raw) != expected['bytes'] or sha256(raw).hexdigest() != expected['sha256']:
            raise ValueError('SKU_CONCURRENCY_DECLARED_SOURCE_CHANGED:' + name)
    return dict(status='EXACT_PREPARED_CALLBACKS_AND_REUSED_TOOLS', files=len(declaration['files']),
                complete_installation_graph_still_owned_by_outer=True, actual_concurrency_executed=False)


def runtime():
    # These are the exact existing vendor-followup tools and complete dump
    # restoration helpers, selected lazily only after the Native7 gate.
    import cp6_auditor_modes as modes
    from cp7_sku_pair_conversion import composition as product
    from cp7_p21_current_chain_rehearsal_probe import helper
    import cp7_p21_current_chain_rehearsal_probe as chain
    from cp6_t3_aligned_install import advisors
    vendor = load('sku_concurrency_retained_vendor_followup', ROOT / 'scripts/current-vendor-receivable-followup/runner.py')
    restoration = load('sku_concurrency_always_restore', ROOT / 'scripts/current-factory-initial-stage/restoration.py')
    database = load('sku_concurrency_existing_copy_restore', ROOT / 'scripts/ow04-payment-used-restore-qualification/restore_database.py')
    # One explicit qualifier-only alias to an already fixed local disposable
    # copy; _restore's implementation/authority/error oracles are unchanged.
    assert database.SOURCE == 'cp6_rollback' and database.RESTORED == 'ow04_payment_restore'
    database.RESTORED = RACE_DB
    return SimpleNamespace(modes=modes, product=product, control=helper.control, chain=chain,
                           advisors=advisors, vendor=vendor, restoration=restoration, copy_restore=database)


class CopyBoundary:
    """Check, dump and fully restore ONE existing race copy, then dispose it.

    The next callback runs on a new exact TEMPLATE copy. This does not activate
    the fresh dump restore, rebind an OID seal, or replace product state.
    """
    def __init__(self, tools, database, deps, state, key):
        self.tools, self.database, self.d, self.state, self.key = tools, database, deps, state, key
        require_local(tools.admin, RACE_DB)
        self.catalog = deps.product.runtime()[-1]
        self.path = '/tmp/sku_pair_concurrency_' + key.lower() + '.dump'
        self.observed = dict(complete=False)
        self.always = deps.restoration.always

    def capture(self):
        d, catalog = self.d, self.catalog
        with self.tools.connect() as connection, connection.cursor() as cursor:
            assert cursor.execute('select current_database()').fetchone() == (RACE_DB,)
            with d.control.product_catalog(cursor):
                d.product.verify(cursor, self.state)
            self.before_catalog = catalog._portable(catalog._catalog_rows(cursor))
            assert len(self.before_catalog) == 22
            self.before_data = catalog._data(cursor)
            self.before_roles = self.database._roles(cursor)
            self.before_cp6 = d.chain.previous.restore_state.capture(cursor, d.chain.package.boundary.snapshot,
                                  d.chain.core.predecessor.public_state, d.chain.p09.functions)
            connection.rollback()
        self.before_hashes = d.chain.drill.data_hashes(RACE_DB)
        self.profile = d.copy_restore._database_profile(RACE_DB)
        self.before_advisors = d.advisors(self.tools.admin)
        assert self.before_advisors['status'] == 'RECORDED', 'SKU_CONCURRENCY_BASELINE_ADVISORS_NOT_RECORDED'
        self.dump_bytes = d.chain.dump.dump(RACE_DB, self.path)
        assert self.dump_bytes > 0
        # No writer or background progress may enter the fixture baseline.
        with self.tools.connect() as connection, connection.cursor() as cursor:
            assert catalog._portable(catalog._catalog_rows(cursor)) == self.before_catalog
            assert catalog._data(cursor) == self.before_data and self.database._roles(cursor) == self.before_roles
            connection.rollback()

    def observe(self):
        d, catalog = self.d, self.catalog
        self.observed['source_scheduler_quiet'] = d.vendor.scheduler_quiet(d.chain.package.boundary.ADMIN)
        leaks = d.modes.session_leaks(RACE_DB)
        self.observed['sessions_before_restore'] = leaks
        assert not leaks, 'SKU_CONCURRENCY_SESSION_LEFT_BEFORE_FULL_RESTORE'
        with self.tools.connect() as connection, connection.cursor() as cursor:
            raw, data = catalog._catalog_rows(cursor), catalog._data(cursor)
            self.observed.update(all22_portable_unchanged=catalog._portable(raw) == self.before_catalog,
                                 committed_fixture_data_changed=data != self.before_data)
            assert self.observed['all22_portable_unchanged'], 'SKU_CONCURRENCY_UNDECLARED_CATALOG_CHANGE'
            with d.control.product_catalog(cursor):
                held, observed_data = catalog._catalog_rows(cursor), catalog._data(cursor)
                try:
                    d.product.rollback_delta_preuse(cursor, self.state)
                except ValueError as error:
                    assert str(error) == d.product.USED_ERROR, str(error)
                else:
                    raise AssertionError('SKU_CONCURRENCY_USED_INVERSE_NOT_REFUSED')
                assert catalog._catalog_rows(cursor) == held and catalog._data(cursor) == observed_data
            connection.rollback()
        self.observed.update(complete=True, used_guard_refused_before_DDL=True,
                             baseline_already_contains_same_call_Native_used_witness=True)
        return self.observed

    def restore(self):
        # Invoke the retained complete pg_dump/pg_restore path, never selected
        # DELETEs, sequence resets, grants over a wrong catalog or new engine.
        result = self.d.copy_restore._restore(self.path, RACE_DB, self.profile)
        assert result['only_pg_cron_errors'], result
        return result

    def verify(self, restored):
        d, catalog = self.d, self.catalog
        assert d.chain.drill.data_hashes(RACE_DB) == self.before_hashes
        with self.tools.connect() as connection, connection.cursor() as cursor:
            assert catalog._portable(catalog._catalog_rows(cursor)) == self.before_catalog
            assert catalog._data(cursor) == self.before_data
            assert self.database._roles(cursor) == self.before_roles
            cp6 = d.chain.previous.restore_state.prove(cursor, self.before_cp6, d.chain.package.boundary.snapshot,
                            d.chain.core.predecessor.public_state, d.chain.p09.functions, self.observed)
            assert cp6 is True, 'SKU_CONCURRENCY_COPY_CP6_SIGNATURE_NOT_RESTORED'
            connection.rollback()
        current_advisors = d.advisors(self.tools.admin)
        assert current_advisors == self.before_advisors, 'SKU_CONCURRENCY_ADVISORS_NOT_RESTORED'
        return dict(complete_database_dump_restored=True, all22_all_rows_all_sequences_roles_exact=True,
                    cp6_restored=True, advisors_equal=True, only_pg_cron_errors=restored['only_pg_cron_errors'],
                    selected_table_cleanup=False, dump_bytes=self.dump_bytes,
                    restored_copy_reactivated=False, Native_source_guard_rebound=False)

    def cleanup(self):
        self.d.chain.drill.docker('rm', '-f', self.path, check=False)


def handoff_source(url, d, state):
    # Same physical Native -> committed-copy handoff as the existing vendor
    # combined runner, with the current SKU verifier instead of its parent.
    import psycopg
    catalog = d.product.runtime()[-1]
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        raw, data = catalog._catalog_rows(cursor), catalog._data(cursor)
        with d.control.product_catalog(cursor):
            d.product.verify(cursor, state)
        if raw != state['after']:
            cursor.execute('revoke usage on schema erp from authenticated')
        assert catalog._catalog_rows(cursor) == state['after'], 'SKU_CONCURRENCY_HANDOFF_NOT_EXACT22'
        assert catalog._data(cursor) == data, 'SKU_CONCURRENCY_HANDOFF_CHANGED_BUSINESS_DATA'
        d.product.verify(cursor, state)
        connection.commit()
    return dict(only_declared_harness_usage_removed=raw != state['after'], all22_exact=True,
                committed_Native_business_rows_and_sequences_unchanged=True)


def exercise(conn, cur, database, url, report, state, *, native7):
    # The same outer invocation passes its freshly executed Native7 result.
    # A historical PASS JSON or simply having an installed function is not a
    # substitute. Root still binds the complete candidate and package itself.
    declared = admit_sources()
    from cp7_sku_pair_conversion import composition as product
    admission = controls.prerequisite(native7, ids(CALLBACKS / 'cases.py'), state.get('sources'), product.sources())
    require_local(url, 'cp6_rollback')
    assert conn.info.host in ('127.0.0.1', 'localhost') and conn.info.port == 54322
    assert cur.execute('select current_database()').fetchone() == ('cp6_rollback',)
    conn.rollback(); cur.close(); conn.close()
    d = runtime()
    report.update(status='INCOMPLETE', source_declaration=declared, prepared_plan=plan(), prerequisite=admission,
                  handoff=handoff_source(url, d, state), production_go=False, independent_acceptance=False)
    business = load('sku_concurrency_original_races', CALLBACKS / 'races.py')
    permissions = load('sku_concurrency_original_permission_waits', CALLBACKS / 'auth_waits.py')
    expected = tuple(business.IDS) + tuple(permissions.IDS)
    assert list(expected) == report['prepared_plan']['race_ids'] + report['prepared_plan']['permission_wait_ids']
    copy_adapter = load('sku_concurrency_existing_copy_authority', ROOT / 'scripts/ow04-payment-current-races-qualification/copy_authority.py')
    original_copy = d.modes.copy_db
    copy_adapter.ORIGINAL_COPY_DATABASE = original_copy
    copy_adapter.PRODUCT = SimpleNamespace(catalog=product.runtime()[-1], verify=product.verify)
    copy_adapter.STATE = dict(state, installed_catalog=state['after'])
    halted = False

    class Selected:
        @staticmethod
        def races(tools, today):
            options = ((True, True), (False, True), (False, False))
            planned = [(key, lambda same=same, commit=commit: business.exercise(tools, today, same_uuid=same, first_commit=commit))
                       for key, (same, commit) in zip(business.IDS, options)] + list(permissions.cases(tools, today))
            assert tuple(key for key, _ in planned) == expected
            def invoke(key, operation):
                nonlocal halted
                if halted:
                    raise ValueError('SKU_CONCURRENCY_PREVIOUS_RESTORE_FAILED_NO_NEW_FIXTURE')
                boundary = CopyBoundary(tools, database, d, state, key)
                try:
                    boundary.capture()
                    result = controls.execute(operation, boundary)
                    if result.get('restore_error'):
                        halted = True
                    return result
                finally:
                    boundary.cleanup()
            return [(key, lambda key=key, operation=operation: invoke(key, operation)) for key, operation in planned]

    def copy(name):
        if halted:
            raise ValueError('SKU_CONCURRENCY_PREVIOUS_RESTORE_FAILED_NO_NEW_COPY')
        if name != RACE_DB:
            raise ValueError('SKU_CONCURRENCY_UNDECLARED_COPY_DATABASE')
        return copy_adapter.copy_database(name)

    try:
        d.modes.copy_db = copy
        report['concurrency'] = d.modes.run_races(Selected, lambda cursor: verify(cursor, d, state), 'sku_pair_conversion9')
    finally:
        d.modes.copy_db = original_copy
        report['copy_catalog_admissions'] = list(copy_adapter.COPY_ADMISSIONS)
    result = controls.complete(report['concurrency'], expected)
    assert len(copy_adapter.COPY_ADMISSIONS) == 9
    assert all(row['all22_groups_equal_original_install'] is True for row in copy_adapter.COPY_ADMISSIONS)
    report.update(result, used_guard_refused_before_DDL=True,
                  full_installed_copy_restores=9, outer_full_preinstall_restore_and_package_still_required=True)


def verify(cursor, d, state):
    with d.control.product_catalog(cursor):
        return d.product.verify(cursor, state)
