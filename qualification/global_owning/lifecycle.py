"""Global child installation and case routes inside the existing SKU owner."""

from contextlib import contextmanager
from dataclasses import dataclass
from types import SimpleNamespace

from .package_routes import require


INVERSE_FLAGS = dict(full25_and_Native_raw_authority_restored=True,
                     timezone_and_nota_original_full19_restored=True,
                     snapshot_full25_inverse_restored=True,
                     all_preuse_rows_and_sequences_restored=True,
                     used_rows_removed=False, cascade_or_DROP_OWNED_used=False)
VERIFY_FLAGS = dict(full25_verified=True, existing_functions_changed=22, new_private_functions=19)
CASE_COUNTS = dict(native='actual_Native_cases', races='actual_two_session_races',
                   http='actual_Auth_HTTP_cases', browser='actual_browser_cases')


def exact_fields(result, fields, error):
    require(type(result) is dict and all(type(result.get(key)) is type(value) and result[key] == value
                                         for key, value in fields.items()), error)
    return result


def existing_native_usage(cur):
    require(cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone() == (True,),
            'GLOBAL_CALLER_EXISTING_NATIVE_ERP_USAGE_REQUIRED_BEFORE_SEAL')


def idle_observer(conn, cur):
    require(cur.connection is conn and not conn.autocommit and conn.info.host in ('localhost', '127.0.0.1')
            and conn.info.port == 54322 and conn.info.dbname == 'cp6_rollback'
            and conn.info.transaction_status.name == 'IDLE',
            'GLOBAL_CALLER_CLOSE_OR_END_OBSERVER_TRANSACTION_BEFORE_INDEPENDENT_SESSION')


@dataclass(frozen=True)
class Installed:
    sku: dict
    global_installation: dict


class Lifecycle:
    def __init__(self, sku, provider, parent_raw, profile_raw, fixtures):
        self.sku = sku
        self.provider = provider
        self.parent_raw = parent_raw
        self.profile_raw = profile_raw
        self.fixtures = fixtures

    def install_cycle(self, cur, timings, report):
        measure = self.sku.measured
        prior = measure(timings, 'ACTUAL_CURRENT_MANDOR_MOVING_AND_MONEY_PARENT_INSTALL',
                        self.sku._sku_install_parent, cur)
        sku = measure(timings, 'ACTUAL_SKU_AUTOMATIC_PARENT_INSTALL', self.sku._sku_install_delta, cur, prior)
        report['verified_SKU_before_Global'] = measure(timings, 'SKU_VERIFY_BEFORE_GLOBAL',
                                                        self.sku._sku_verify_installed, cur, sku)
        existing_native_usage(cur)
        first = measure(timings, 'FIRST_GLOBAL_INSTALL', self.provider.install, cur, self.parent_raw, self.profile_raw)
        inverse = measure(timings, 'GLOBAL_UNUSED_INVERSE', self.provider.rollback_preuse, cur, first)
        report['focused_preuse_removal'] = exact_fields(inverse, INVERSE_FLAGS,
                                                        'GLOBAL_CALLER_COMPLETE_UNUSED_INVERSE_REQUIRED')
        report['verified_SKU_after_Global_unused_inverse'] = measure(timings, 'SKU_VERIFY_AFTER_GLOBAL_UNUSED_INVERSE',
                                                                     self.sku._sku_verify_installed, cur, sku)
        installed = measure(timings, 'SECOND_GLOBAL_INSTALL', self.provider.install, cur, self.parent_raw, self.profile_raw)
        return Installed(sku, installed)

    def verify(self, cur, state):
        return exact_fields(self.provider.verify(cur, state.global_installation), VERIFY_FLAGS,
                            'GLOBAL_CALLER_COMPLETE_INSTALLED_CHILD_REQUIRED')

    def dispatch_catalogue(self, cur):
        groups = self.provider.catalogue_profile.EXTRA
        require(set(groups) == {'operators', 'casts', 'languages'}, 'GLOBAL_CALLER_EXACT_DISPATCH_GROUPS_REQUIRED')
        with self.provider.metadata_context(cur):
            return {name: cur.execute('select k,v from(' + query + ')q(k,v) order by k collate "C",v::text collate "C"').fetchall()
                    for name, query in sorted(groups.items())}

    def capture_advisors(self, cur, state):
        return dict(sku=self.sku.current_advisor.capture(cur), Global=self.fixtures.capture_advisors(cur, state),
                    global_tables=tuple(state.global_installation['plan']['tables']))

    def review_advisors(self, delta, manifest, captured, predecessor_review):
        def table_info(row):
            meta = row.get('metadata') or {}
            return (row.get('name') == 'rls_enabled_no_policy' and row.get('level') == 'INFO'
                    and meta.get('type') == 'table' and f"{meta.get('schema')}.{meta.get('name')}" in captured['global_tables'])

        added = delta.get('added', [])
        own = [row for row in added if table_info(row)]
        remainder = dict(delta, added=[row for row in added if not table_info(row)])
        sku = self.sku.current_advisor.review(remainder, manifest, captured['sku'], predecessor_review)
        current = self.fixtures.review_advisors(own, captured['Global'])
        identities = [(row['metadata']['schema'], row['metadata']['name']) for row in own]
        gate = sku.get('gate') is True and current.get('gate') is True and len(identities) == len(set(identities))
        return dict(gate=gate, retained_SKU=sku, Global=current, complete_original_delta=delta)

    def actual_counts(self, report):
        plan = self.fixtures.CASE_IDS
        cases = report.get('business_cases')
        exact_fields(report, {'status': 'PASS', 'used_guard_refused_before_DDL': True},
                     'GLOBAL_CALLER_ACTUAL_CASES_AND_USED_REFUSAL_REQUIRED')
        require(type(cases) is dict and set(cases) == {key for ids in plan.values() for key in ids}
                and all(type(value) is dict and value.get('status') == 'PASS' for value in cases.values()),
                'GLOBAL_CALLER_EXACT_ACTUAL_CASE_ORIGINALS_REQUIRED')
        counts = {report_key: len(plan[mode]) for mode, report_key in CASE_COUNTS.items()}
        return dict(counts, actual_business_cases=sum(counts.values()), real_Auth_HTTP_qualified=bool(plan['http']),
                    real_Auth_browser_claim=bool(plan['browser']))

    def observe_installed_scope(self, conn, cur, report, state, observe):
        idle_observer(conn, cur)
        key = 'live_candidate_scope_observation'
        require(key not in report, 'GLOBAL_SCOPE_ONE_OWNING_OBSERVATION_REQUIRED')
        installation = state.global_installation
        names = installation['inputs']['relations']
        sealed = installation['sealed']['expected_relations']
        proof = report[key] = dict(status='INCOMPLETE', relation_count=len(names))
        try:
            require(names == ['.'.join(row[:2]) for row in sealed], 'GLOBAL_SCOPE_ACTUAL_SEALED_RELATIONS_REQUIRED')
            observed, issues = observe(cur, names)
            proof.update(observed=observed, issues=issues)
            fields = ('relkind', 'relpersistence', 'owner', 'relrowsecurity', 'relforcerowsecurity', 'raw_acl')
            metadata = [row['qualified_name'].split('.', 1) + [row[field] for field in fields]
                        for row in observed['relations']]
            require(not issues and not observed['outside_origin_RI'] and metadata == sealed,
                    'GLOBAL_SCOPE_ACTUAL_CANDIDATE_OBSERVATION_REFUSED')
        except Exception:
            proof['status'] = 'REFUSED'
            raise
        finally:
            conn.rollback()
        idle_observer(conn, cur)
        proof['status'] = 'OBSERVED_EXACT_SEALED_SCOPE'

    def runner(self, positives, *, observe_scope):
        def exercise(conn, cur, database, url, report, state):
            def require_quiet():
                idle_observer(conn, cur)

            def observe_native(outside_conversion_id):
                require_quiet()
                require('original_Native_D1_E_SOURCE' not in report, 'GLOBAL_CALLER_ONE_NATIVE_GROUP_ATTEMPT_REQUIRED')
                report['original_Native_D1_E_SOURCE'] = dict(status='INCOMPLETE')
                group = positives.run(self, state, outside_conversion_id)
                report['original_Native_D1_E_SOURCE'] = group
                return group

            self.observe_installed_scope(conn, cur, report, state, observe_scope)
            result = self.fixtures.exercise(conn, cur, database, url, report, state,
                                            verify=lambda cursor: self.verify(cursor, state),
                                            observe_native=observe_native, require_quiet=require_quiet)
            require_quiet()
            positive = report.get('original_Native_D1_E_SOURCE', {})
            require(positive.get('status') == 'PASS' and set(positive.get('cases', {})) == set(positives.ids),
                    'GLOBAL_CALLER_ACTUAL_D1_E_SOURCE_ORIGINALS_REQUIRED')
            self.actual_counts(report)
            return result

        return SimpleNamespace(CASE=self.fixtures.CASE, exercise=exercise,
                               scheduler_quiet=self.sku.runner.scheduler_quiet)


class NativePositives:
    GROUP = 'GLOBAL_FIRST_NATIVE_D1_E_SOURCE'

    def __init__(self, observer, runner, factories, output, originals, report_io):
        self.observer = observer
        self.runner = runner
        self.factories = factories
        self.output = output
        self.originals = originals
        self.report_io = report_io
        self.ids = tuple(key for _, _, expected in factories for key in expected)

    @contextmanager
    def output_scope(self):
        original = self.runner.r1.OUT
        with self.report_io.group_scope(self.runner.r1):
            self.runner.r1.OUT = self.output
            try:
                yield
            finally:
                self.runner.r1.OUT = original

    def run(self, lifecycle, state, outside_conversion_id):
        def retain(case_id, original):
            require(case_id in self.ids, 'GLOBAL_CALLER_EXACT_NATIVE_CASE_ID_REQUIRED')
            return self.originals.save_sorted(self.output / (case_id + '_GLOBAL_OBSERVATION.json'), original,
                                              'GLOBAL_CALLER_NATIVE_OBSERVATION_ORIGINAL_CONFLICT')

        observed = [self.observer.bind(lifecycle.provider, lifecycle.parent_raw, lifecycle.profile_raw,
                                       state.global_installation, root, factory, expected,
                                       outside_conversion_id, retain=retain)
                    for root, factory, expected in self.factories]

        def cases(cur, today):
            return [case for factory in observed for case in factory(cur, today)]

        def verify(cur):
            existing_native_usage(cur)
            return lifecycle.verify(cur, state)

        self.output.mkdir(parents=True, exist_ok=True)
        with self.output_scope():
            return self.runner.strict_group(self.GROUP, cases, verify)
