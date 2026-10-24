"""Four Native scoped-model-input controls; no v3 model/forecast acceptance."""
from time import monotonic
import json
import uuid
import cp7_ow11_model_history_runtime_cases as history
import cp7_ow11_model_evaluation_v2_cases as model
import cp7_model_scoped_dataset as stage
from cp7_ow04_restore_bundle import _catalog_rows

plan = history.plan
CONTRACT = 'cp7.ow11.model-scoped-dataset-native.v1'
IDS = dict(native=['OW11_MODEL_SCOPED_DATASET_CATALOG22_COMPOSED_INVERSE',
    'OW11_MODEL_SCOPED_DATASET_ACTUAL_CAPTURE_AND_POLICY_CLOCK',
    'OW11_MODEL_SCOPED_DATASET_ACTUAL_POST_REVISION_AND_ACCESS',
    'OW11_MODEL_SCOPED_DATASET_DENSE2000_SINGLE_TARGET'])
REQUIRED = dict(native=4)
EXPECTED = DECLARED = 4
FUNCTIONS = tuple(dict.fromkeys((*history.FUNCTIONS, *model.FUNCTIONS)))
SCHEDULES = history.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE, SCHEDULE_STATE, BOUNDED_STATE, REFERENCE_STATE, STAGE_STATE = {}, {}, {}, {}, {}, {}, {}
PARENT_CHECKER = None


def install(cur):
    model.PARENT_CHECKER = PARENT_CHECKER
    ps, ms = model.install(cur)
    def model_parent(c):
        PARENT_CHECKER(c)
        model.policy.stage.verify(c, ps)
        model.stage.verify(c, ms)
    history.PARENT_CHECKER = model_parent
    hs, hr = history.install(cur)
    def parents(c):
        model_parent(c)
        history.source.stage.verify(c, hs)
        history.stage.verify(c, hr)
    ds = stage.install_delta(cur, parents)
    return ps, ms, hs, hr, ds


def query(run, q):
    return dict(history_run_id=run['run_id'], target_key=q['target_key'], horizon_days='7')


def dataset(cur, q, actor):
    history.history.auth.actor(cur, actor)
    cur.execute('set local role cp7_capture')
    start = monotonic()
    answer = cur.execute('select cp7_model_scoped_dataset.dataset(%s::jsonb,%s::uuid)', (json.dumps(q), actor)).fetchone()[0]
    millis = (monotonic() - start) * 1000
    plan.b.api.admin(cur)
    assert millis < 8000, ('SCOPED_MODEL_DATASET_OVER8S', millis)
    return answer, round(millis, 3)


def prepare(cur, today, actor):
    f = history.history.fixture(cur, today)
    q = history.query(cur, f, today)
    run = history.capture(cur, q, subject=actor)
    return f, q, run


def cases(cur, today):
    def catalog():
        before = _catalog_rows(cur)
        ps, ms, hs, hr, ds = install(cur)
        assert stage.verify(cur, ds)['private_functions'] == 3
        installed = _catalog_rows(cur)
        cur.execute('create view public.ow11_scoped_dataset_inverse_guard as select cp7_model_scoped_dataset.native_dataset(null::jsonb,null::uuid) value')
        guarded = _catalog_rows(cur)
        try:
            stage.rollback_preuse(cur, ds)
        except Exception as e:
            assert getattr(e, 'sqlstate', None) == '2BP01', str(e)
        else:
            raise AssertionError('SCOPED_DATASET_DEPENDENT_VIEW_REMOVED')
        assert _catalog_rows(cur) == guarded
        cur.execute('drop view public.ow11_scoped_dataset_inverse_guard')
        assert _catalog_rows(cur) == installed
        try:
            history.stage.rollback_preuse(cur, hr)
        except ValueError as e:
            assert str(e) == 'MODEL_HISTORY_RUNTIME_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE'
        else:
            raise AssertionError('SCOPED_HISTORY_PARENT_REMOVED_BELOW_DATASET')
        stage.rollback_preuse(cur, ds)
        history.stage.rollback_preuse(cur, hr)
        history.source.stage.rollback_preuse(cur, hs)
        model.stage.rollback_preuse(cur, ms)
        model.policy.stage.rollback_preuse(cur, ps)
        assert _catalog_rows(cur) == before
        PARENT_CHECKER(cur)
        return dict(status='PASS', exact_catalog22_composed_inverse=True,
            private3_RPC0_table0_replacement0=True, partial_inverse_atomic=True,
            history_parent_cannot_be_removed=True, source_sha256=stage.sources())

    def clocks():
        install(cur)
        actor = model.master.role_actor(cur, 'OWNER')
        _, q, run = prepare(cur, today, actor)
        frozen = history.stored(cur, run['run_id'])
        before, _ = dataset(cur, query(run, q), actor)
        assert before['policy_source'] is None
        assert all(row['known_at'] == run['captured_at'] and row['refs'][0]['kind'] == 'NATIVE_SCOPED_HISTORY_RUN' for row in before['series'])
        assert before['series'][0]['state'] == 'UNKNOWN' and before['series'][0]['value'] is None
        # Explicit test policy is prospective. It cannot retroactively approve
        # a history capture made before the policy was recorded.
        policy = model.policy.save(cur, model.policy.payload(cur, actor), actor)
        late, _ = dataset(cur, query(run, q), actor)
        assert late['policy_source'] is None and late['series'] == before['series']
        fresh = history.capture(cur, q, subject=actor)
        current, _ = dataset(cur, query(fresh, q), actor)
        assert current['policy_source']['policy']['id'] == policy['policy']['id']
        assert current['series'] == before['series']
        assert history.stored(cur, run['run_id']) == frozen
        assert cur.execute('select count(*)from cp7_model_registry_adapter.runs').fetchone()[0] == 0
        return dict(status='PASS', actual_Native_capture_times=True, unknown_never_zero=True,
            unchanged_snapshots_do_not_create_revisions=True, policy_cannot_approve_older_history=True,
            fresh_capture_uses_actual_explicit_test_policy=True, no_model_run_or_forecast=True)

    def posted_access():
        install(cur)
        actor, role = history.history.auth.custom_actor(cur)
        f, q, one = prepare(cur, today, actor)
        first, _ = dataset(cur, query(one, q), actor)
        frozen = history.stored(cur, one['run_id'])
        history.history.sales.fg.post_sale(cur, f['draft'])
        refused = plan.refusal(cur, lambda: dataset(cur, query(one, q), actor))
        assert refused[0:2] == ('P0001', 'CP7_SCOPED_MODEL_HISTORY_STALE')
        two = history.capture(cur, q, subject=actor)
        current, _ = dataset(cur, query(two, q), actor)
        assert two['history']['history']['rows'][0]['gross_observed_pcs'] == '24'
        assert two['history']['current_stock'][0]['native_available_pcs'] == '76'
        # UNKNOWN availability stays UNKNOWN even when actual posted sales change.
        assert current['series'] == first['series']
        other, _ = history.history.auth.custom_actor(cur)
        assert plan.refusal(cur, lambda: dataset(cur, query(two, q), other))[0] == '42501'
        plan.b.api.admin(cur)
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'", (role,))
        assert plan.refusal(cur, lambda: dataset(cur, query(two, q), actor))[0] == '42501'
        assert history.stored(cur, one['run_id']) == frozen
        return dict(status='PASS', actual_Native_sale_retires_old_source=True, gross24_available76=True,
            unknown_training_not_invented_from_sales=True, unchanged_unknown_meaning_not_new_revision=True,
            current_four_permission_revocation_and_foreign_actor_denied=True)

    def dense():
        install(cur)
        actor = model.master.role_actor(cur, 'OWNER')
        _, q, one = prepare(cur, today, actor)
        initial, _ = dataset(cur, query(one, q), actor)
        size = history.work.dense.seed(cur)
        physical = plan.monetary_state(cur)
        two = history.capture(cur, q, subject=actor)
        current, ms = dataset(cur, query(two, q), actor)
        assert current['series'] == initial['series']
        assert current['history_source_hash'] == initial['history_source_hash']
        cur.execute('set local role cp7_capture')
        whole = cur.execute('select cp7_planning.history_source()').fetchone()[0]
        plan.b.api.admin(cur)
        assert whole['status'] == 'INCOMPLETE'
        assert plan.monetary_state(cur) == physical
        return dict(status='PASS', label='SYNTHETIC_VOLUME_ACTUAL_SCOPED_CAPTURE_AND_PRIVATE_DATASET',
            **size, millis=ms, wall_limit_ms=8000, original_global_bound_unchanged=True,
            factory_SLA_claim=False, model_evaluation_runtime_integrated=False)

    return list(zip(IDS['native'], (catalog, clocks, posted_access, dense)))


def races(tools, today): return []
def http_cases(http, today): return []
