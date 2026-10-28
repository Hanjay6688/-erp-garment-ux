"""Six Native retained scoped-model controls; no model target or HTTP credit."""
from time import monotonic
import json
import uuid
import cp7_ow11_model_scoped_dataset_cases as parent
import cp7_model_scoped_evaluation as stage
from cp7_ow04_restore_bundle import _catalog_rows

history, model, plan = parent.history, parent.model, parent.plan
CONTRACT = 'cp7.ow11.model-scoped-evaluation-native.v1'
IDS = dict(native=['OW11_SCOPED_EVALUATION_CATALOG22_COMPOSED_INVERSE',
 'OW11_SCOPED_EVALUATION_ACTUAL_CAPTURE_REPLAY_IMMUTABLE',
 'OW11_SCOPED_EVALUATION_PROSPECTIVE_POLICY_CLOCK',
 'OW11_SCOPED_EVALUATION_ACTUAL_POST_CURRENT_ACCESS',
 'OW11_SCOPED_EVALUATION_DENSE2000_SINGLE_TARGET',
 'OW11_SCOPED_EVALUATION_FINAL_FAULT_AND_ENGINE'])
REQUIRED = dict(native=6)
EXPECTED = DECLARED = 6
FUNCTIONS = (*parent.FUNCTIONS, 'erp_cp7_capture_model_evaluation_v3', 'erp_cp7_read_model_evaluation_v3')
SCHEDULES = parent.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE, SCHEDULE_STATE, BOUNDED_STATE, REFERENCE_STATE, STAGE_STATE = {}, {}, {}, {}, {}, {}, {}
PARENT_CHECKER = None


def install(cur):
    parent.PARENT_CHECKER = PARENT_CHECKER
    states = parent.install(cur)
    # Parent install already checks exact22 at each composition boundary.
    # Freeze that entire catalog; no masking or dropped catalog dimensions.
    catalog = _catalog_rows(cur)
    def checked(c):
        assert _catalog_rows(c) == catalog, 'SCOPED_EVALUATION_PARENT22_CHANGED'
        parent.stage.verify(c, states[-1])
    current = stage.install_delta(cur, checked)
    return states, current


def rollback_parents(cur, states):
    ps, ms, hs, hr, ds = states
    parent.stage.rollback_preuse(cur, ds)
    history.stage.rollback_preuse(cur, hr)
    history.source.stage.rollback_preuse(cur, hs)
    model.stage.rollback_preuse(cur, ms)
    model.policy.stage.rollback_preuse(cur, ps)


def capture(cur, q, actor, request=None):
    start = monotonic()
    r = plan.rpc(cur, 'erp_cp7_capture_model_evaluation_v3', (json.dumps(q), request or uuid.uuid4()), actor)
    ms = (monotonic()-start)*1000
    assert ms < 8000, ('SCOPED_EVALUATION_OVER8S', ms)
    return r, round(ms, 3)


def read(cur, run, actor):
    return plan.rpc(cur, 'erp_cp7_read_model_evaluation_v3', (run,), actor)


def stored(cur, run):
    plan.b.api.admin(cur)
    return cur.execute('select to_jsonb(r)from cp7_model_scoped_evaluation.runs r where id=%s', (run,)).fetchone()[0]


def cases(cur, today):
    def catalog():
        before = _catalog_rows(cur)
        states, current = install(cur)
        assert stage.verify(cur, current)['private_functions'] == 4
        installed = _catalog_rows(cur)
        cur.execute('create view public.ow11_scoped_model_inverse_guard as select id from cp7_model_scoped_evaluation.runs')
        guarded = _catalog_rows(cur)
        try: stage.rollback_preuse(cur, current)
        except Exception as e: assert getattr(e, 'sqlstate', None) == '2BP01', str(e)
        else: raise AssertionError('SCOPED_MODEL_DEPENDENT_VIEW_REMOVED')
        assert _catalog_rows(cur) == guarded
        cur.execute('drop view public.ow11_scoped_model_inverse_guard')
        assert _catalog_rows(cur) == installed
        try: parent.stage.rollback_preuse(cur, states[-1])
        except ValueError as e: assert str(e) == 'MODEL_SCOPED_DATASET_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE'
        else: raise AssertionError('SCOPED_DATASET_PARENT_REMOVED')
        stage.rollback_preuse(cur, current)
        rollback_parents(cur, states)
        assert _catalog_rows(cur) == before
        PARENT_CHECKER(cur)
        return dict(status='PASS', exact_catalog22_composed_inverse=True,
          private4_RPC2_table1_replacement0=True, exact_parent_FK_triggers_declared=True,
          partial_inverse_atomic=True, dataset_parent_cannot_be_removed=True, source_sha256=stage.sources())

    def replay():
        _, current = install(cur)
        actor = model.master.role_actor(cur, 'OWNER')
        _, q, h = parent.prepare(cur, today, actor)
        p = parent.query(h, q)
        physical = plan.monetary_state(cur)
        m, _ = capture(cur, p, actor, h['request_id'])
        frozen = stored(cur, m['run_id'])
        assert m['contract_version'] == 'cp7.scoped-model-run.v3'
        assert m['assessment']['activation']['state'] == 'BASELINE_REQUIRED'
        assert m['assessment']['activation']['reason'] == 'EXPLICIT_ACTIVATION_POLICY_REQUIRED'
        assert frozen['input']['known_as_of'] == h['captured_at']
        assert all(row['known_at'] == h['captured_at'] and row['state'] == 'UNKNOWN' and row['value'] is None for row in frozen['input']['series'])
        history.same_archive(m, capture(cur, p, actor, m['request_id'])[0])
        history.same_archive(m, read(cur, m['run_id'], actor))
        assert plan.refusal(cur, lambda: capture(cur, dict(p, horizon_days='8'), actor, m['request_id']))[0:2] == ('P0001', 'CP7_SCOPED_EVALUATION_REQUEST_CHANGED')
        for command in ('update cp7_model_scoped_evaluation.runs set input=input', 'delete from cp7_model_scoped_evaluation.runs'):
            assert plan.refusal(cur, lambda: cur.execute(command))[0:2] == ('55000', 'CP7_RUN_IMMUTABLE')
        assert stored(cur, m['run_id']) == frozen and plan.monetary_state(cur) == physical
        try: stage.rollback_preuse(cur, current)
        except ValueError as e: assert str(e) == 'MODEL_SCOPED_EVALUATION_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE'
        else: raise AssertionError('SCOPED_MODEL_AFTER_USE_INVERSE_ALLOWED')
        assert cur.execute('select count(*)from cp7_model_scoped_evaluation.runs').fetchone()[0] == 1
        assert cur.execute('select count(*)from cp7_model_registry_adapter.runs').fetchone()[0] == 0
        return dict(status='PASS', actual_scoped_history_and_retained_model=True, exact_UUID_replay=True,
          same_UUID_separate_method_namespace=True, old_model_table_unchanged=True,
          actual_knowledge_clock_preserved=True, UNKNOWN_not_zero=True, after_use_inverse_refused=True)

    def clocks():
        install(cur)
        actor = model.master.role_actor(cur, 'OWNER')
        _, q, h = parent.prepare(cur, today, actor)
        original, _ = capture(cur, parent.query(h, q), actor)
        frozen = stored(cur, original['run_id'])
        explicit = model.policy.save(cur, model.policy.payload(cur, actor), actor)
        late, _ = capture(cur, parent.query(h, q), actor)
        assert late['assessment']['policy_source'] is None
        assert late['assessment']['activation']['state'] == 'BASELINE_REQUIRED'
        fresh = history.capture(cur, q, subject=actor)
        current, _ = capture(cur, parent.query(fresh, q), actor)
        assert current['assessment']['policy_source']['policy']['id'] == explicit['policy']['id']
        assert current['assessment']['activation']['state'] == 'BASELINE_REQUIRED'
        assert current['assessment']['activation']['forecast'] is None
        old = read(cur, original['run_id'], actor)
        history.same_archive(original, old)
        assert old['current_guard']['reason'] == 'ACTIVATION_POLICY_CHANGED'
        assert stored(cur, original['run_id']) == frozen
        return dict(status='PASS', explicit_synthetic_policy_prospective=True, no_posthoc_approval=True,
          fresh_history_uses_recorded_policy=True, UNKNOWN_has_no_invented_winner=True,
          old_assessment_preserved_and_current_policy_rechecked=True)

    def posted():
        install(cur)
        actor, role = history.history.auth.custom_actor(cur)
        f, q, h = parent.prepare(cur, today, actor)
        m, _ = capture(cur, parent.query(h, q), actor)
        frozen = stored(cur, m['run_id'])
        history.history.sales.fg.post_sale(cur, f['draft'])
        old = read(cur, m['run_id'], actor)
        history.same_archive(m, old)
        assert old['current_guard']['reason'] == 'NATIVE_HISTORY_SOURCE_CHANGED'
        assert plan.refusal(cur, lambda: capture(cur, parent.query(h, q), actor))[0:2] == ('P0001', 'CP7_SCOPED_EVALUATION_HISTORY_STALE')
        fresh = history.capture(cur, q, subject=actor)
        current, _ = capture(cur, parent.query(fresh, q), actor)
        assert fresh['history']['history']['rows'][0]['gross_observed_pcs'] == '24'
        assert fresh['history']['current_stock'][0]['native_available_pcs'] == '76'
        assert current['assessment']['activation']['state'] == 'BASELINE_REQUIRED'
        foreign, _ = history.history.auth.custom_actor(cur)
        assert plan.refusal(cur, lambda: read(cur, m['run_id'], foreign))[0] == '42501'
        plan.b.api.admin(cur)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'", (role,))
        assert plan.refusal(cur, lambda: read(cur, current['run_id'], actor))[0] == '42501'
        assert plan.refusal(cur, lambda: capture(cur, parent.query(fresh, q), actor, current['request_id']))[0] == '42501'
        assert stored(cur, m['run_id']) == frozen
        return dict(status='PASS', actual_SALE_retires_old_model_without_rewriting=True,
          fresh_gross24_available76=True, current_access_before_read_and_replay=True, foreign_read_denied=True)

    def dense():
        install(cur)
        actor = model.master.role_actor(cur, 'OWNER')
        _, q, _ = parent.prepare(cur, today, actor)
        size = history.work.dense.seed(cur)
        h = history.capture(cur, q, subject=actor)
        physical = plan.monetary_state(cur)
        m, ms = capture(cur, parent.query(h, q), actor)
        assert m['assessment']['source']['target_key'] == q['target_key']
        assert m['assessment']['activation']['state'] == 'BASELINE_REQUIRED'
        assert plan.monetary_state(cur) == physical
        return dict(status='PASS', label='SYNTHETIC_VOLUME_ACTUAL_NATIVE_SCOPED_MODEL_FACADE',
          **size, millis=ms, wall_limit_ms=8000, factory_SLA_claim=False, model_target_consumer_integrated=False)

    def final_fault():
        install(cur)
        actor = model.master.role_actor(cur, 'OWNER')
        _, q, h = parent.prepare(cur, today, actor)
        p = parent.query(h, q)
        cur.execute("create function public.ow11_scoped_model_fault()returns trigger language plpgsql as $$begin raise exception 'SCOPED_MODEL_LAST_ROW_FAULT';end$$")
        cur.execute('create trigger ow11_scoped_model_fault before insert on cp7_model_scoped_evaluation.runs for each row execute function public.ow11_scoped_model_fault()')
        assert plan.refusal(cur, lambda: capture(cur, p, actor))[0:2] == ('P0001', 'SCOPED_MODEL_LAST_ROW_FAULT')
        plan.b.api.admin(cur)
        assert cur.execute('select count(*)from cp7_model_scoped_evaluation.runs').fetchone()[0] == 0
        cur.execute('drop trigger ow11_scoped_model_fault on cp7_model_scoped_evaluation.runs')
        m, _ = capture(cur, p, actor)
        frozen = stored(cur, m['run_id'])
        cur.execute('create function cp7_model_scoped_evaluation.fixture_engine_change()returns boolean language sql as $$select true$$')
        old = read(cur, m['run_id'], actor)
        history.same_archive(m, old)
        assert old['current_guard']['reason'] == 'MODEL_ENGINE_CHANGED'
        assert stored(cur, m['run_id']) == frozen
        return dict(status='PASS', actual_public_final_insert_fault_atomic=True,
          runtime_engine_change_archives_original=True, no_after_use_restore_credit=True)

    return list(zip(IDS['native'], (catalog, replay, clocks, posted, dense, final_fault)))


def races(tools, today): return []
def http_cases(http, today): return []
