"""Eight Native-only controls for the additive staged work-metadata route.

This does not close dense SAVE2000: it preserves incomplete history as such.
It does not claim new Auth/PostgREST/browser/race or after-use restore proof.
"""
from decimal import Decimal as D
import copy
import json
import uuid
import cp7_ow13c_checked_cases as base
import cp7_ow13c_checked_scale_cases as dense
import cp7_schedule_staged_review as stage
from cp7_ow04_restore_bundle import _catalog_rows

plan = base.plan
CONTRACT = 'cp7.ow13c.staged-schedule-native.v1'
IDS = dict(native=['OW13C_SCHEDULE_NATIVE_PRIVATE_CATALOG22',
                   'OW13C_SCHEDULE_NATIVE_RUNNING_SAVE_REPLAY',
                   'OW13C_SCHEDULE_NATIVE_STALE_REFUSED',
                   'OW13C_SCHEDULE_NATIVE_FOREIGN_AND_CURRENT_ACCESS',
                   'OW13C_SCHEDULE_NATIVE_REVISION_AND_OLD_UUID',
                   'OW13C_SCHEDULE_NATIVE_USED_INVERSE_BEFORE_DDL',
                   'OW13C_SCHEDULE_NATIVE_ATOMIC_METADATA_FAULT',
                   'OW13C_SCHEDULE_NATIVE_METADATA2000_HISTORY_INCOMPLETE_HONEST'])
REQUIRED = dict(native=8)
EXPECTED = DECLARED = 8
FUNCTIONS = (*base.FUNCTIONS, 'erp_cp7_get_staged_production_schedule_v1',
             'erp_cp7_save_staged_production_schedule_v1')
SCHEDULES = base.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE, SCHEDULE_STATE = {}, {}, {}, {}


def get(cur, key, subject=None):
    return plan.rpc(cur, 'erp_cp7_get_staged_production_schedule_v1', (key,), subject)


def save(cur, p, key=None, subject=None):
    return plan.rpc(cur, 'erp_cp7_save_staged_production_schedule_v1',
                    (json.dumps(p), key or uuid.uuid4()), subject)


def metadata(cur):
    plan.b.api.admin(cur)
    plans = cur.execute("select md5(coalesce(jsonb_agg(to_jsonb(p)order by p.revision),'[]')::text)from cp7_schedule_native.plans p").fetchone()[0]
    commands = cur.execute("select md5(coalesce(jsonb_agg(to_jsonb(c)order by c.actor,c.request_id),'[]')::text)from cp7_schedule_native.commands c").fetchone()[0]
    return dict(plans=plans, commands=commands, physical=plan.monetary_state(cur),
                native=plan.b.boundary.snapshot(cur))


def prepare(cur, today, subject=None, dense_fixture=False):
    x = plan.fixture(cur, today)
    plan.b.api.admin(cur)
    selected = copy.deepcopy(cur.execute('select config from cp7_schedule_native.plans order by revision desc limit 1').fetchone()[0])
    if dense_fixture:
        dense.seed(cur)
    key = str(uuid.uuid4())
    initial = plan.staged.request(cur, today, key, subject=subject)
    assert initial['state'] == 'RUNNING' and initial['run_id'] is None and initial['units_done'] == 0, initial
    before = metadata(cur)
    w = get(cur, key, subject)
    assert metadata(cur) == before, 'STAGED_SCHEDULE_GET_WROTE_DATA'
    assert w['contract_version'] == 'cp7.planning-schedule-staged.v1' and w['source_request_id'] == key, w
    assert w['source_state'] == 'UNCHANGED' and w['analysis_state'] == 'RUNNING', w
    assert w['production_capture_state'] == 'COMPLETE' and w['staged_review_contract'] == stage.render.CONTRACT, w
    payload = dict(source_run=w['source_run'], source_hash=w['source_hash'], expected_revision=w['revision'],
                   config=selected, reason='Explicit fixture work review from a real Native staged reference; metadata only',
                   staged_review_contract=stage.render.CONTRACT)
    return dict(x=x, request=key, workspace=w, payload=payload, subject=subject)


def cases(cur, today):
    def catalog():
        verified = stage.verify(cur, SCHEDULE_STATE)
        assert verified['public_rpcs'] == 2 and verified['private_functions'] == 3 and verified['old_function_replacements'] == 0
        assert len(_catalog_rows(cur)) == 22
        return dict(status='PASS', private_schema_three_functions_two_reviewed_facades=True,
                    seven_Native_bodies_and_eleven_dependency_authorities_exact=True,
                    new_tables=0, old_function_replacements=0)

    def replay():
        f = prepare(cur, today)
        before = plan.monetary_state(cur)
        key = str(uuid.uuid4())
        out = save(cur, f['payload'], key)
        assert out['contract_version'] == 'cp7.planning-schedule-staged-outcome.v1' and out['staged_review_contract'] == stage.render.CONTRACT, out
        assert out['source_run'] == f['workspace']['source_run'] and int(out['revision']) == int(f['payload']['expected_revision'])+1, out
        assert save(cur, f['payload'], key) == out
        plan.refused(cur, lambda: save(cur, dict(f['payload'], reason='changed same UUID'), key), 'CP7_SCHEDULE_REQUEST_CHANGED')
        assert plan.monetary_state(cur) == before
        plan.b.api.admin(cur)
        row = cur.execute('select source_run::text,config from cp7_schedule_native.plans where id=%s', (out['plan_id'],)).fetchone()
        assert row == (f['workspace']['source_run'], f['payload']['config']), row
        return dict(status='PASS', actual_RUNNING_reference_not_fake_completed_analysis=True,
                    public_SAVE_exact_UUID_replay=True, explicit_same_work_config=True, physical_stock_money_HPP_unchanged=True)

    def stale():
        f = prepare(cur, today)
        plan.found_fg(cur, f['x'], '1')
        before = metadata(cur)
        assert get(cur, f['request'])['source_state'] == 'ARCHIVED_STALE'
        plan.refused(cur, lambda: save(cur, f['payload']), 'CP7_SCHEDULE_SOURCE_CHANGED', '40001')
        assert metadata(cur) == before
        return dict(status='PASS', actual_stock_writer_changed_reference=True, stale_SAVE_exact40001=True,
                    no_schedule_command_or_physical_effect=True)

    def access():
        actor = base.retained.master.role_actor(cur, 'OWNER')
        f = prepare(cur, today, subject=actor)
        stranger = base.retained.master.role_actor(cur, 'OWNER')
        plan.refused(cur, lambda: get(cur, f['request'], stranger), 'CP7_SCHEDULE_STAGED_RUN_UNAVAILABLE', '42501')
        out = save(cur, f['payload'], subject=actor)
        plan.b.api.admin(cur)
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (actor,))
        before = metadata(cur)
        for operation in (lambda: get(cur, f['request'], actor), lambda: save(cur, f['payload'], subject=actor)):
            state, _, _ = plan.refusal(cur, operation)
            assert state == '42501', state
        assert metadata(cur) == before
        return dict(status='PASS', real_other_owner_cannot_read_foreign_reference=True,
                    current_deactivated_actor_READ_and_SAVE_denied=True, no_denied_effect=True)

    def revision_and_old():
        f = prepare(cur, today)
        key = str(uuid.uuid4())
        out = save(cur, f['payload'], key)
        before = metadata(cur)
        plan.refused(cur, lambda: save(cur, f['payload']), 'CP7_SCHEDULE_REVISION_CHANGED')
        assert save(cur, f['payload'], key) == out and metadata(cur) == before
        # An actual old-route command is never re-labelled by the new facade.
        plan.b.api.admin(cur)
        old = cur.execute("select request_id::text,payload from cp7_schedule_native.commands where not(payload?'staged_review_contract')order by request_id limit 1").fetchone()
        assert old is not None
        plan.refused(cur, lambda: save(cur, f['payload'], old[0]), 'CP7_SCHEDULE_REQUEST_CHANGED')
        assert metadata(cur) == before
        return dict(status='PASS', stale_revision_refused_exact_old_contract=True, committed_UUID_replay_after_revision_change=True,
                    actual_old_UUID_cannot_become_staged=True)

    def used():
        f = prepare(cur, today)
        save(cur, f['payload'])
        plan.b.api.admin(cur)
        before, rows = _catalog_rows(cur), metadata(cur)
        try:
            stage.rollback_preuse(cur, SCHEDULE_STATE)
        except ValueError as error:
            assert str(error) == 'STAGED_SCHEDULE_AFTER_USE_REQUIRES_BACKUP_RESTORE'
        else:
            raise AssertionError('STAGED_SCHEDULE_USED_INVERSE_ALLOWED')
        assert _catalog_rows(cur) == before and metadata(cur) == rows
        return dict(status='PASS', actual_immutable_tagged_command_blocks_inverse_before_DDL=True)

    def atomic():
        f = prepare(cur, today)
        plan.b.api.admin(cur)
        cur.execute("create function pg_temp.ow13c_schedule_fault()returns trigger language plpgsql as $$begin raise exception 'OW13C_SCHEDULE_METADATA_FAULT';end;$$")
        cur.execute('create trigger ow13c_schedule_fault before insert on cp7_schedule_native.commands for each row execute function pg_temp.ow13c_schedule_fault()')
        before = metadata(cur)
        plan.refused(cur, lambda: save(cur, f['payload']), 'OW13C_SCHEDULE_METADATA_FAULT')
        assert metadata(cur) == before
        return dict(status='PASS', injected_failure_after_schedule_insert_rolls_both_metadata_tables_back=True,
                    physical_stock_money_HPP_unchanged=True)

    def large():
        f = prepare(cur, today, dense_fixture=True)
        assert f['workspace']['history_capture_state'] == 'INCOMPLETE', f['workspace']['history_capture_state']
        before = plan.monetary_state(cur)
        out = save(cur, f['payload'])
        assert out['quality'] == 'SELECTED_ASSUMPTIONS' and out['staged_review_contract'] == stage.render.CONTRACT, out
        assert plan.monetary_state(cur) == before
        plan.b.api.admin(cur)
        n = cur.execute("select count(*)from erp.fg_stock_movements where source_type='OW13C_SAVE_VOLUME'").fetchone()[0]
        assert n == 202000
        return dict(status='PASS', products=2000, movements=n, history_state='INCOMPLETE',
                    actual_RUNNING_reference_work_metadata_only=True, global_production_WIP_complete=True,
                    no_fake_completed_job_or_override=True, actual_checked_SAVE2000_qualified=False,
                    old_dense_history_refusal_not_relaxed=True, statement_limit='8s')

    return list(zip(IDS['native'], [catalog, replay, stale, access, revision_and_old, used, atomic, large]))
