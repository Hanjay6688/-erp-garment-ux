"""Real Native production, complete staged jobs and private global supply reads.

All126 initial/WA/fabric controls remain unchanged. Policy/calendar numbers
below belong to the accepted test fixture; none become production defaults.
"""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
import json

import cp7_ow13a_initial_cases as retained
import cp7_p19_staged_cases as staged
import cp7_reorder_supply as supply_stage
from cp7_ow04_restore_bundle import _catalog_rows

analysis = staged.analysis
b, auth = analysis.b, analysis.auth
CONTRACT = 'cp7.ow10.global-supply-native.v1'
FUNCTIONS, SCHEDULES = retained.FUNCTIONS, retained.SCHEDULES
ADDED_NATIVE = [
    'OW10_SUPPLY_NATIVE_COMPLETE_PRODUCER_FRESH_READER',
    'OW10_SUPPLY_NATIVE_K3_KEEPS_BUDGET_AND_FULL_RESULT',
    'OW10_SUPPLY_NATIVE_SOURCE_PROFILE_PERIOD_CHANGED',
    'OW10_SUPPLY_NATIVE_UNREVIEWED_IS_UNKNOWN',
    'OW10_SUPPLY_NATIVE_LATE_TO_LEAD_NOT_TARGET',
    'OW10_SUPPLY_NATIVE_ENGINE_HASH_INVALIDATES_CACHE',
    'OW10_SUPPLY_NATIVE_PRIVATE_ACL_AND_AFTER_USE_GUARD',
]
IDS = {group: list(ids) + (ADDED_NATIVE if group == 'native' else [])
       for group, ids in retained.IDS.items()}
REQUIRED = {group: len(ids) for group, ids in IDS.items()}
EXPECTED = DECLARED = sum(REQUIRED.values())
assert REQUIRED == dict(native=75, races=36, http=9, browser=13) and EXPECTED == 133
INSTALL_STATES = {}


def private(cur, sql, args=()):
    """Run actual private readers as their non-superuser owning role."""
    b.api.admin(cur)
    with cur.connection.transaction():
        cur.execute("set local statement_timeout='8s';set local role cp7_capture")
        row = cur.execute(sql, args).fetchone()[0]
        cur.execute('reset role')
    b.api.admin(cur)
    return row


def current(cur):
    return private(cur, "select cp7_analysis_native.source_within("
                   "(cp7_analysis_stage.bounds()->>'job_targets')::integer,"
                   "(cp7_analysis_stage.bounds()->>'job_matching_products')::integer)"
                   "||jsonb_build_object('financial_source',null,'financial_capture','DEFERRED')")


def fingerprint(cur, source):
    return private(cur, 'select cp7_analysis_native.fingerprint(%s::jsonb)', (json.dumps(source),))


def read(cur, source, query):
    return private(cur, 'select cp7_reorder_supply.read_job(%s::jsonb,%s::jsonb)',
                   (json.dumps(source), json.dumps(query)))


def complete(cur, today, reviewed=True, late=False):
    f, root, _, proposal = analysis.setup(cur, today, review=False)
    if late:
        at = cur.execute('select clock_timestamp()').fetchone()[0]
        window = proposal['config']['windows'][0]
        window['starts_at'] = analysis.schedule.stamp(at + timedelta(days=5))
        window['ends_at'] = analysis.schedule.stamp(at + timedelta(days=5, hours=2))
        proposal['config']['through_at'] = analysis.schedule.stamp(at + timedelta(days=6))
    if reviewed:
        analysis.schedule.save(cur, proposal)
    before = b.boundary.snapshot(cur)
    key, first, done, calls = staged.staged_done(cur, today)
    job = staged.job_row(cur, key)
    assert job['reference']['reorder_supply_engine'] == 'cp7.reorder-supply.v1'
    assert b.boundary.snapshot(cur) == before
    scope = cur.execute('select scope from cp7_analysis_stage.plan_scope where job_id=%s',
                        (job['id'],)).fetchone()[0]
    scenario = cur.execute("select cp7_analysis_stage.output(%s,'SCENARIO')->'scenario'",
                           (job['id'],)).fetchone()[0]
    produced = private(cur, 'select cp7_reorder_supply.budgets(%s::jsonb,%s::jsonb)',
                       (json.dumps(scenario['wip']), json.dumps(scenario['etas'])))
    assert scope['reorder_supply_budget'] == produced
    source = current(cur)
    assert fingerprint(cur, source) == job['source_hash'], 'FRESH_NATIVE_SOURCE_NOT_SAME_DEPENDENCIES'
    return dict(f=f, root=root, job=job, scope=scope, scenario=scenario, source=source,
                result=read(cur, source, job['query']), calls=len(calls))


def target(result, root):
    return next(row for row in result['projection']['rows'] if row['target_key'].split(':')[0] == root)


def cases(cur, today):
    # Retained rollback cases refer to the exact initial/target install states.
    retained.INSTALL_STATES = INSTALL_STATES

    def producer():
        r = complete(cur, today)
        budget = r['scope']['reorder_supply_budget']
        assert budget['status'] == 'COMPLETE' and len(budget['rows']) == 1, budget
        assert budget['rows'][0]['projected_good_pcs'] == '7' and budget['rows'][0]['eta']
        assert r['scenario']['wip']['positions'][0]['remaining_pcs'] == '8'
        assert r['result']['status'] == 'SCENARIO', r['result']
        row = target(r['result'], r['root'])
        assert row['net']['lead_position_base_pcs'] == '7'
        assert row['net']['q_base_pcs'] == '93' and row['net']['base_reorder_state'] == 'AT_OR_BELOW'
        stored = cur.execute("select payload from cp7_analysis_stage.target_rows where job_id=%s "
                             "and kind='NETROW' and key=%s", (r['job']['id'], row['target_key'])).fetchone()[0]
        for field in ('lead_position_base_pcs', 'lead_position_conditional_pcs', 'q_base_pcs',
                      'q_conditional_pcs', 'base_reorder_state', 'conditional_reorder_state'):
            assert row['net'][field] == stored['net'][field], field
        assert sum(Decimal(x['net']['directed_on_time_pcs']) for x in r['result']['projection']['rows']
                   if x['net'] is not None) == Decimal(7)
        return dict(status='PASS', actual_Native_raw8_projected7_once=True,
                    actual_complete_run_unit_and_fresh_native_capture=True,
                    same_actual_Native_net_fields=6, private_reader_role='cp7_capture',
                    unit_calls_under_8s=r['calls'], ROP_caller_qualified=False)

    def cleanup():
        r = complete(cur, today)
        assert r['result']['status'] == 'SCENARIO', r['result']
        before = staged.fetch(cur, r['job']['run_id'])
        cleaned = private(cur, 'select cp7_analysis_stage.clean_done(%s)', (r['job']['id'],))
        assert cleaned['state'] == 'CLEANED' and cleaned['removed']['outputs'] > 0, cleaned
        assert cur.execute('select scope from cp7_analysis_stage.plan_scope where job_id=%s',
                           (r['job']['id'],)).fetchone()[0] == r['scope']
        assert read(cur, r['source'], r['job']['query']) == r['result']
        assert fingerprint(cur, current(cur)) == r['job']['source_hash']
        assert staged.fetch(cur, r['job']['run_id']) == before
        again = private(cur, 'select cp7_analysis_stage.clean_done(%s)', (r['job']['id'],))
        assert again['state'] == 'ALREADY_CLEANED'
        return dict(status='PASS', actual_Native_K3_clean_done=True,
                    full_private_supply_JSON_and_scope_unchanged=True,
                    all_public_header_pages_hashes_unchanged=True, repeated_cleanup_idempotent=True,
                    removed=cleaned['removed'])

    def changed():
        r = complete(cur, today)
        assert r['result']['status'] == 'SCENARIO', r['result']
        sealed = staged.fetch(cur, r['job']['run_id'])
        for key, value in [('group_mode', 'RESTATED'),
                           ('from_date', str(today - timedelta(days=2)))]:
            query = {**r['job']['query'], key: value}
            assert query != r['job']['query']
            answer = read(cur, r['source'], query)
            assert answer['status'] == 'UNKNOWN' and answer['projection'] is None, answer
        profile = analysis.previous.baseline.get(cur, [r['root']])['rows'][0]
        config = deepcopy(profile['config']);config['lead_days'] = '4'
        analysis.previous.baseline.save(cur, dict(root_id=profile['root_id'],
            product_version_id=profile['product_version_id'], expected_revision=profile['revision'],
            reason='TEST_FIXTURE_ONLY explicit lead change must stale retained supply', config=config))
        profile_source = current(cur)
        assert fingerprint(cur, profile_source) != r['job']['source_hash']
        answer = read(cur, profile_source, r['job']['query'])
        assert answer['reason'] == 'GLOBAL_ANALYSIS_STALE_OR_EXPIRED' and answer['projection'] is None
        analysis.previous.production.b.bbp.complete(cur, r['f'], r['f']['cutover'] + timedelta(days=2), 3)
        output_source = current(cur)
        assert fingerprint(cur, output_source) != fingerprint(cur, profile_source)
        answer = read(cur, output_source, r['job']['query'])
        assert answer['status'] == 'UNKNOWN' and answer['projection'] is None
        assert staged.job_row(cur, r['job']['request_id'])['reference'] == r['job']['reference']
        # Pages remain the exact archive; access/freshness metadata may report stale.
        after = staged.fetch(cur, r['job']['run_id'])
        assert after[0] == sealed[0] and after[1]['header'] == sealed[1]['header']
        return dict(status='PASS', changed_period_and_group_refuse_old_allocation=True,
                    actual_reviewed_profile_lead_change_and_Native_output3_change_hash=True,
                    stale_supply_not_current_zero=True, sealed_original_unchanged=True)

    def unreviewed():
        r = complete(cur, today, reviewed=False)
        rows = r['scope']['reorder_supply_budget']['rows']
        assert rows and all(x['projected_good_pcs'] is None and x['eta'] is None for x in rows)
        assert r['result']['status'] == 'UNKNOWN' and r['result']['projection'] is None
        assert r['result']['reason'] == 'GLOBAL_SCHEDULE_UNREVIEWED', r['result']
        return dict(status='PASS', actual_Native_unreviewed_yield_and_ETA_null=True,
                    no_zero_or_raw8_credit=True)

    def late():
        r = complete(cur, today, late=True)
        assert r['result']['status'] == 'SCENARIO', r['result']
        net = target(r['result'], r['root'])['net']
        assert net['lead_position_base_pcs'] == '0', net
        assert net['q_base_pcs'] == '93' and net['base_reorder_state'] == 'AT_OR_BELOW'
        assert net['lead_net']['directed_on_time_pcs'] == '0' and net['directed_on_time_pcs'] == '7'
        return dict(status='PASS', actual_reviewed_Native_good7_at_day5=True,
                    no_credit_at_lead3_credit_at_target10=True, same_allocation_both_horizons=True)

    def engine():
        r = complete(cur, today)
        assert r['result']['status'] == 'SCENARIO', r['result']
        definition = cur.execute("select pg_get_functiondef('cp7_reorder_supply.budgets(jsonb,jsonb)'::regprocedure)").fetchone()[0]
        assert definition.count('GLOBAL_WIP_INCOMPLETE') == 1
        # Administrative code-change control, not a Native business-row edit.
        cur.execute(definition.replace('GLOBAL_WIP_INCOMPLETE', 'GLOBAL_WIP_INCOMPLETE_ENGINE_CONTROL'), prepare=False)
        changed_source = current(cur)
        assert fingerprint(cur, changed_source) != r['job']['source_hash']
        answer = read(cur, changed_source, r['job']['query'])
        assert answer['projection'] is None and answer['reason'] == 'GLOBAL_ANALYSIS_STALE_OR_EXPIRED'
        cur.execute(definition, prepare=False)
        assert fingerprint(cur, current(cur)) == r['job']['source_hash']
        assert read(cur, r['source'], r['job']['query']) == r['result']
        return dict(status='PASS', actual_helper_body_in_Native_engine_signature=True,
                    changed_engine_never_reuses_old_allocation=True, exact_definition_restored=True)

    def authority():
        for role in ('anon', 'authenticated', 'service_role', 'cp7_alert'):
            assert not cur.execute("select has_schema_privilege(%s,'cp7_reorder_supply','USAGE')",
                                   (role,)).fetchone()[0]
            for signature in supply_stage.FUNCTIONS:
                assert not cur.execute('select has_function_privilege(%s,%s,\'EXECUTE\')',
                                       (role, signature)).fetchone()[0]
        r = complete(cur, today)
        before = _catalog_rows(cur)
        try:
            supply_stage.rollback_preuse(cur, INSTALL_STATES['supply'])
        except ValueError as error:
            assert str(error) == 'OW10_SUPPLY_AFTER_USE_REQUIRES_BACKUP_RESTORE'
        else:
            raise AssertionError('OW10_SUPPLY_AFTER_USE_DID_NOT_REFUSE')
        assert _catalog_rows(cur) == before
        return dict(status='PASS', no_outsider_schema_or_function_access=True,
                    after_real_Native_capture_guard_before_any_DDL=True, all_catalog_groups_exact=22)

    return retained.cases(cur, today) + list(zip(ADDED_NATIVE, [producer, cleanup, changed, unreviewed, late, engine, authority]))


def races(tools, today):
    return retained.races(tools, today)


def http_cases(http, today):
    return retained.http_cases(http, today)
