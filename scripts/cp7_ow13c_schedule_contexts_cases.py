"""Retain Native8; add DONE, actual failed-history metadata and expiry controls.

FAILED is a computation state, not permission to forge a successful analysis.
Only an unchanged, retained real reference may still supply work metadata.
"""
from datetime import timedelta
import cp7_ow13c_schedule_cases as retained
import cp7_k2_retention_cases as retention

plan = retained.plan
CONTRACT = 'cp7.ow13c.staged-schedule-contexts.v1'
NEW_NATIVE = ['OW13C_SCHEDULE_NATIVE_DONE_CONTEXT_SAVE',
              'OW13C_SCHEDULE_NATIVE_DONE_EXPIRED_CONTEXT_REFUSED',
              'OW13C_SCHEDULE_NATIVE_FAILED_HISTORY_METADATA_ONLY_AND_EXPIRED']
IDS = dict(native=[*retained.IDS['native'], *NEW_NATIVE])
REQUIRED = dict(native=11)
EXPECTED = DECLARED = 11
FUNCTIONS, SCHEDULES = retained.FUNCTIONS, retained.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE, SCHEDULE_STATE = {}, {}, {}, {}


def cases(cur, today):
    retained.INSTALL_STATES, retained.REORDER_STATES = INSTALL_STATES, REORDER_STATES
    retained.CHECKED_STATE, retained.SCHEDULE_STATE = CHECKED_STATE, SCHEDULE_STATE

    def done():
        f = retained.prepare(cur, today)
        completed, calls = plan.staged.drive(cur, f['request'])
        assert completed['state'] == 'DONE' and completed['run_id'] == f['workspace']['source_run'], completed
        before = retained.metadata(cur)
        w = retained.get(cur, f['request'])
        assert w['analysis_state'] == 'DONE' and w['source_state'] == 'UNCHANGED', w
        assert retained.metadata(cur) == before
        physical = plan.monetary_state(cur)
        out = retained.save(cur, f['payload'])
        assert out['source_run'] == completed['run_id']
        assert plan.monetary_state(cur) == physical
        return dict(status='PASS', actual_compiler_reached_DONE=True, actual_work_context_READ_SAVE=True,
                    physical_stock_money_HPP_unchanged=True, completed_units=len(calls))

    def expired():
        f = retained.prepare(cur, today)
        completed, _ = plan.staged.drive(cur, f['request'])
        assert completed['state'] == 'DONE'
        # Reuse the unchanged K2 negative fixture: only the finish timestamp is
        # administratively aged. Neither physical dates nor the DB clock moves.
        retention.age(cur, completed['run_id'], timedelta(days=8))
        before = retained.metadata(cur)
        plan.refused(cur, lambda: retained.get(cur, f['request']), retention.EXPIRED)
        plan.refused(cur, lambda: retained.save(cur, f['payload']), retention.EXPIRED)
        assert retained.metadata(cur) == before
        return dict(status='PASS', owner_K2_seven_day_retention_preserved=True,
                    actual_DONE_reference_READ_SAVE_expired_refused=True,
                    synthetic_finish_timestamp_aging_only=True, no_metadata_or_physical_effect=True)

    def failed():
        f = retained.prepare(cur, today, dense_fixture=True)
        stopped = plan.staged.step(cur, f['request'])
        assert stopped['state'] == 'FAILED' and stopped['failure']['code'] == 'CP7_PLANNING_CAPTURE_INCOMPLETE', stopped
        before = retained.metadata(cur)
        w = retained.get(cur, f['request'])
        assert w['analysis_state'] == 'FAILED' and w['history_capture_state'] == 'INCOMPLETE', w
        assert w['production_capture_state'] == 'COMPLETE' and w['source_state'] == 'UNCHANGED', w
        assert retained.metadata(cur) == before
        physical = plan.monetary_state(cur)
        out = retained.save(cur, f['payload'])
        assert out['source_run'] == f['workspace']['source_run'] and plan.monetary_state(cur) == physical
        plan.b.api.admin(cur)
        state = cur.execute('select state from cp7_analysis_stage.jobs where run_id=%s', (out['source_run'],)).fetchone()[0]
        assert state == 'FAILED', state
        q = dict(run_id=out['source_run'], target_key=f['x']['target'], location_id=str(f['x']['fabric']['location']),
                 po_query='', roll_query='', po_offset='0', roll_offset='0', pattern_offset='0', limit='50')
        plan.refused(cur, lambda: plan.options(cur, q), 'CP7_PLAN_V2_SNAPSHOT_UNAVAILABLE', '42501')
        # The FAILED job is finished for K2 too. Its metadata reference must
        # not evade the same retention guard after it expires.
        retention.age(cur, out['source_run'], timedelta(days=8))
        before = retained.metadata(cur)
        plan.refused(cur, lambda: retained.get(cur, f['request']), retention.EXPIRED)
        expired_payload = dict(f['payload'], expected_revision=out['revision'])
        plan.refused(cur, lambda: retained.save(cur, expired_payload), retention.EXPIRED)
        assert retained.metadata(cur) == before
        return dict(status='PASS', actual_dense_history_step_failed=True, history_remains_INCOMPLETE=True,
                    actual_FAILED_reference_work_metadata_only=True, no_fake_DONE_or_production_quantity=True,
                    plan_options_for_failed_run_still_denied=True, FAILED_reference_K2_expiry_preserved=True,
                    synthetic_finish_timestamp_aging_only=True, physical_stock_money_HPP_unchanged=True)

    return [*retained.cases(cur, today), *zip(NEW_NATIVE, [done, expired, failed])]
