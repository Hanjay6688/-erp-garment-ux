"""Prepared Native fixture routes for the closed SKU 457 Global owner."""

from contextlib import contextmanager
import json
import os
from uuid import UUID, uuid4


POSITIVE_IDS = (
    'D_AFTER_ACTIVE_APPLY', 'D_REPLAY_EXACT_UUID',
    'E_SAME_UUID_AND_CHANGED_INTENT', 'E_UNDO_ORIGINAL_80_AND_OLD_RECEIPT',
    'OW04_SIGNED_RETURN_REVERSE_UNCONSUMED_CREDIT',
    'OW04_SIGNED_PAYMENT_REVERSE_UNCONSUMED_CREDIT',
)
PERMISSION = (
    ('D_ACCESS_REVOKED_NO_EFFECT', 'CP7_RETURN_CORRECTION_DENIED'),
    ('E_CURRENT_ACCESS_REVOKED_REFUSES', 'CP7_NOTE_ACCESS_DENIED'),
)
USED_ERROR = 'GLOBAL_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE:cp7_global_nonpo_envelope.scope_completions_v1'
DAY = 'SKU_CURRENT_AUTOMATIC_WIB_BUSINESS_DAY'
INSPECT = 'select cp7_global_nonpo_native_graph.inspect_v1(%s::uuid[])'
RELEVANT = "select cp7_global_nonpo_native_graph.capture_v1(jsonb_build_object('support',%s::jsonb),false)"
CONVERSION = 'select to_jsonb(c)::text from erp.product_conversions c where id=%s'


def require(value, reason):
    if not value:
        raise ValueError(reason)


def actual_day(cur):
    day, = cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()
    require(day.isoformat() == os.environ.get(DAY), 'GLOBAL_FIXTURE_EXACT_REAL_WIB_DAY_REQUIRED')
    return day


@contextmanager
def rollback_on_failure(conn):
    try:
        yield
    except BaseException:
        conn.rollback()
        raise


def complete_group(report, expected):
    require(report.get('status') == 'PASS' and report.get('counts') == {'PASS': len(expected)}
            and report.get('planned_case_ids') == list(expected)
            and list(report.get('cases', {})) == list(expected)
            and report.get('complete_boundary_restored') is True
            and not report.get('business_day_retried') and not report.get('business_day_first_attempt'),
            'GLOBAL_FIXTURE_EXACT_ORIGINAL_STRICT_GROUP_REQUIRED')
    for key, case in report['cases'].items():
        require(case.get('status') == 'PASS' and case.get('full_boundary_restored') is True
                and case.get('public_schema_unchanged') is True and not case.get('business_day_rollover')
                and case.get('session_leaks', {}).get('advisory_locks') == 0
                and case.get('session_leaks', {}).get('other_sessions') == [],
                'GLOBAL_FIXTURE_EXACT_RESTORED_NATIVE_CASE_REQUIRED:' + key)
    return report


def document(value, *, status):
    require(type(value) is dict and value.get('status') == status, 'GLOBAL_FIXTURE_EXACT_CONVERSION_STATUS_REQUIRED:' + status)
    return value


def inspect(cur, sale, outside_id, *, outside_status):
    observed, = cur.execute(INSPECT, ([sale],)).fetchone()
    require(observed['contract'] == 'cp7.global-nonpo-native-graph.readonly-inspector.v1'
            and observed['status'] == 'OBSERVED_QUIESCENT_SOURCE_ONLY' and observed['issues'] == []
            and observed['read_only'] is True
            and observed['authority']['known_functions_exact'] is True
            and observed['authority']['new_private_acl_closed'] is True,
            'GLOBAL_FIXTURE_EXACT_QUIESCENT_PRIVATE_OBSERVATION_REQUIRED')
    outside = observed['outside_source']
    require(outside['facts']['BE_context_rows'] == []
            and outside_id not in observed['scope']['relevant']['conversion_ids']
            and outside_id in outside['identity_domain']['conversion_ids'], 'GLOBAL_FIXTURE_DISJOINT_OUTSIDE_SKU_ID_REQUIRED')
    matches = [row for row in outside['facts']['conversions'] if row['id'] == outside_id]
    require(len(matches) == 1, 'GLOBAL_FIXTURE_EXACT_OUTSIDE_SKU_CONVERSION_REQUIRED')
    document(matches[0], status=outside_status)
    relevant, = cur.execute(RELEVANT, (json.dumps(observed['scope']['relevant']),)).fetchone()
    require(relevant['identity_domain'] == observed['scope']['relevant'],
            'GLOBAL_FIXTURE_EXACT_RAW_RELEVANT_DOMAIN_REQUIRED')
    return dict(inspector=observed, relevant_facts=relevant)


def same_intent_after_outside_change(old, new):
    for kind, key in (('D1', 'credit_review_token'), ('E', 'credit_carry_review')):
        prior, current = old[kind], new[kind]
        require(prior['version'] == current['version']
                and {name: value for name, value in prior['payload'].items() if name != key}
                == {name: value for name, value in current['payload'].items() if name != key},
                'GLOBAL_FIXTURE_STALE_UNCHANGED_NATIVE_VERSION_AND_INTENT_REQUIRED:' + kind)
        if kind == 'D1':
            require(prior['review']['state'] == current['review']['state'] == 'READY'
                    and prior['review']['issues'] == current['review']['issues'] == []
                    and prior['review']['source_authority_proven'] is current['review']['source_authority_proven'] is True
                    and prior['payload'][key] != current['payload'][key], 'GLOBAL_FIXTURE_D1_STALE_PUBLIC_TOKEN_REQUIRED')
        else:
            old_carry, new_carry = prior['payload'][key], current['payload'][key]
            require(prior['review']['issues'] == current['review']['issues'] == []
                    and old_carry['transfer_amount'] == new_carry['transfer_amount'] == '80.00'
                    and {name: value for name, value in old_carry.items() if name != 'basis_sha256'}
                    == {name: value for name, value in new_carry.items() if name != 'basis_sha256'}
                    and old_carry['basis_sha256'] != new_carry['basis_sha256'], 'GLOBAL_FIXTURE_E_STALE_PUBLIC_BASIS_REQUIRED')
        before, after = prior['graph']['inspector'], current['graph']['inspector']
        require(before['scope']['relevant'] == after['scope']['relevant']
                and prior['graph']['relevant_facts'] == current['graph']['relevant_facts']
                and before['outside_source'] != after['outside_source']
                and before['basis_sha256'] != after['basis_sha256'],
                'GLOBAL_FIXTURE_ACTUAL_STALE_OUTSIDE_TRANSITION_REQUIRED:' + kind)


class NativeLanes:
    """Source-bound lanes for a future reviewed full fixture driver."""

    def __init__(self, *, provider, parent_raw, profile_raw, state, graph, trusted_connection, verify, retain):
        parent, profile = provider.admission.runtime_admission(parent_raw, profile_raw)
        current = state.global_installation
        require(current['parent'] == parent and current['inputs'] == profile and current['contract'] == provider.CONTRACT,
                'GLOBAL_FIXTURE_ACTUAL_INSTALLED_PROFILE_REQUIRED')
        self.provider, self.state, self.graph = provider, current, graph
        self.installed, self.verify_child = state, verify
        self.parent_raw, self.profile_raw = parent_raw, profile_raw
        self.trusted_connection, self.retain = trusted_connection, retain

    def exercise_native(self, conn, cur, report, *, observe_native, require_quiet):
        require('outside_SKU' not in report, 'GLOBAL_FIXTURE_ONE_COMMITTED_SETUP_ATTEMPT_REQUIRED')
        report['outside_SKU'] = dict(status='INCOMPLETE')
        outside = self.seed_outside(conn, cur, require_quiet)
        report['outside_SKU'] = outside
        report['positive_originals'] = self.observe_positives(outside, observe_native)
        report['permission_originals'] = self.observe_permissions(outside, require_quiet)
        committed_e = self.commit_e(conn, cur, outside, require_quiet)
        report['committed_E'] = committed_e
        report['used_inverse'] = self.used_inverse(committed_e, require_quiet)
        # The exact stale transition reverses the same anchor needed by the earlier groups.
        report['stale_outside_inverse'] = self.stale_after_exact_outside_inverse(conn, cur, outside, require_quiet)

    def seed_outside(self, conn, cur, require_quiet):
        require_quiet()
        moving = self.graph.moving
        with rollback_on_failure(conn):
            self.verify_child(cur)
            self.graph.existing_usage(cur)
            if not cur.execute('select count(*) from erp.app_users').fetchone()[0]:
                moving.f.b.api.seed(cur)
            today = actual_day(cur)
            fixture = moving.canonical(cur, today)
            posted, preview = moving.forward(cur, fixture)
            ident = posted['conversion_id']
            require(type(ident) is str and str(UUID(ident)) == ident, 'GLOBAL_FIXTURE_EXACT_PUBLIC_CONVERSION_UUID_REQUIRED')
            cur.execute('set constraints all immediate')
            raw, = cur.execute(CONVERSION, (ident,)).fetchone()
            document(json.loads(raw), status='POSTED')
            actual_day(cur)
            conn.commit()
        require_quiet()
        return dict(conversion_id=ident, business_day=today, fixture=fixture, public_post=posted,
                    public_review=preview, committed_conversion_raw=raw, Native_case_credit=0)

    def observe_positives(self, outside, observe_native):
        return complete_group(observe_native(outside['conversion_id']), POSITIVE_IDS)

    def verify(self, cur, state):
        require(state is self.installed, 'GLOBAL_FIXTURE_EXACT_INSTALLED_CHILD_REQUIRED')
        return self.verify_child(cur)

    def observe_permissions(self, outside, require_quiet):
        require_quiet()
        # Original D1/E callbacks change authority inside their retained savepoints.
        factories = [(root, factory, {key: ()}) for (root, factory, _), (key, _) in zip(self.graph.factories[:2], PERMISSION, strict=True)]
        positives = self.graph.native_observer(factories)
        positives.GROUP = 'GLOBAL_FIRST_NATIVE_D1_E_CURRENT_PERMISSION'
        report = complete_group(positives.run(self, self.installed, outside['conversion_id']),
                                tuple(key for key, _ in PERMISSION))
        for key, message in PERMISSION:
            require(report['cases'][key]['actual_refusal']['message'] == message
                    and report['cases'][key]['actual_refusal']['sqlstate'] == '42501'
                    and report['cases'][key]['Global_completion_operations'] == [],
                    'GLOBAL_FIXTURE_CURRENT_PERMISSION_SQLSTATE_AND_NO_COMPLETION_REQUIRED:' + key)
        require_quiet()
        return report

    def commit_e(self, conn, cur, outside, require_quiet):
        require_quiet()
        observer = self.graph.observer

        def observe(cursor, previous=None):
            current = observer.capture(cursor)
            if previous is None:
                return current
            require(observer.checked_delta(previous, current, self.state['profile_id'], outside['conversion_id']) == ['E'],
                    'GLOBAL_FIXTURE_ONE_ACTUAL_E_COMPLETION_BEFORE_COMMIT_REQUIRED')
            old = {row[0] for row in previous['rows']}
            operation, = [row[0] for row in current['rows'] if row[0] not in old]
            original = self.retain('GLOBAL_COMMITTED_E_OBSERVATION', dict(before=previous, after=current))
            require(original['bytes'] > 0 and len(original['sha256']) == 64,
                    'GLOBAL_FIXTURE_EXACT_RAW_E_ORIGINAL_REQUIRED')
            return dict(global_operation_id=operation, global_observation_original=original)

        with rollback_on_failure(conn):
            self.verify_child(cur)
            result = self.graph.commit_e(conn, cur, self.graph.e, self.graph.financial_truth, observe)
        require_quiet()
        return result

    def full_state(self, cur):
        return dict(full25=self.provider.capture(cur), full_rows_and_sequences=self.provider._timezone_snapshot(cur, lock=False))

    def used_inverse(self, committed_e, require_quiet):
        require_quiet()
        require(committed_e.get('status') == 'NATIVE_E_CORRECTION_COMMITTED' and committed_e.get('E_Native_case_credit') == 0,
                'GLOBAL_FIXTURE_ACTUAL_COMMITTED_E_REQUIRED_BEFORE_USED_INVERSE')
        with self.trusted_connection() as conn, conn.cursor() as cur:
            try:
                self.provider.verify(cur, self.state)
                operation = committed_e['global_operation_id']
                match, = cur.execute("select count(*) from cp7_global_nonpo_envelope.scope_completions_v1 "
                                      "where operation_id=%s and operation='E' and profile_id=%s",
                                      (operation, self.state['profile_id'])).fetchone()
                require(match == 1, 'GLOBAL_FIXTURE_ACTUAL_COMMITTED_E_RECEIPT_REQUIRED')
                before = self.full_state(cur)
                try:
                    self.provider.rollback_preuse(cur, self.state)
                except ValueError as error:
                    if str(error) != USED_ERROR:
                        raise
                    refusal = str(error)
                else:
                    raise ValueError('GLOBAL_FIXTURE_USED_INVERSE_DID_NOT_REFUSE')
                after = self.full_state(cur)
                require(before == after, 'GLOBAL_FIXTURE_USED_REFUSAL_CHANGED_FULL25_ROWS_OR_SEQUENCES')
                self.provider.verify(cur, self.state)
            finally:
                conn.rollback()
        require_quiet()
        return dict(used_guard_refused_before_DDL=True, message=refusal, operation_id=operation,
                    original=self.retain('GLOBAL_USED_INVERSE_FULL_STATE', dict(before=before, after=after)), Native_case_credit=0)

    def isolated_full_state(self):
        with self.trusted_connection() as conn, conn.cursor() as cur:
            try:
                return self.full_state(cur)
            finally:
                conn.rollback()

    def stale_after_exact_outside_inverse(self, conn, cur, outside, require_quiet):
        """Prepare both public reviews, commit one lawful outside reverse, then refuse both."""
        require_quiet()
        d1, e, moving = self.graph.d1, self.graph.e, self.graph.moving
        ident, x = outside['conversion_id'], outside['fixture']

        def reviews(outside_status):
            p, v, q = d1.payload(cur, pair_d1)
            ep, ev, basis = e.intent(cur, pair_e)
            return {'D1': dict(payload=p, version=v, review=q, graph=inspect(cur, p['sale_id'], ident, outside_status=outside_status)),
                    'E': dict(payload=ep, version=ev, review=basis, graph=inspect(cur, ep['sale_id'], ident, outside_status=outside_status))}

        with rollback_on_failure(conn):
            today = actual_day(cur)
            require(today == outside['business_day'], 'GLOBAL_FIXTURE_STALE_REAL_WIB_DAY_CHANGED')
            pair_d1 = d1.fixture.prepare(cur, today)
            pair_e = e.fixture.prepare(cur, today)
            e.basic.apply(cur, pair_e, '80.00')
            e.native.b.api.admin(cur)
            cur.execute('set constraints all immediate')
            conn.commit()
            old = reviews('POSTED')
            conn.rollback()
            require_quiet()
            # Run the same retained public inverse and postcondition as the frozen SKU case.
            inverse = self.graph.reverse_existing(cur, x, ident)
            actual_day(cur)
            conn.commit()
            require_quiet()
            new = reviews('REVERSED')
            same_intent_after_outside_change(old, new)
            conn.rollback()

            outcomes = {}
            commands = (
                ('D1', d1, pair_d1, d1.correction.correct, 'CP7_CREDIT_DE_STALE_REVIEW'),
                ('E', e, pair_e, e.note.correct, 'CP7_CREDIT_NOTE_CARRY_STALE_REVIEW'),
            )
            for name, business, pair, command, message in commands:
                require_quiet()
                before = self.isolated_full_state()
                prior = old[name]
                outcome = business.refusal(cur, pair, lambda: command(cur, prior['payload'], prior['version'], uuid4()), message)
                require(inspect(cur, prior['payload']['sale_id'], ident, outside_status='REVERSED') == new[name]['graph'],
                        'GLOBAL_FIXTURE_STALE_REFUSAL_CHANGED_RAW_GRAPH:' + name)
                actual_day(cur)
                conn.rollback()
                require_quiet()
                after = self.isolated_full_state()
                require(outcome['sqlstate'] == 'P0001' and before == after,
                        'GLOBAL_FIXTURE_STALE_REFUSAL_CHANGED_FULL25_ROWS_OR_SEQUENCES:' + name)
                outcomes[name] = dict(refusal=outcome, original=self.retain('GLOBAL_STALE_' + name, dict(before=before, after=after)))
            return dict(public_outside_inverse=inverse, old_reviews=old, current_reviews=new, refusals=outcomes)
