"""Four actual Native controls for the private version-bound evaluation selector."""
import json
import uuid
from time import monotonic
from pathlib import Path
from hashlib import sha256
import cp7_ow11_model_scoped_evaluation_cases as parent
import cp7_model_evaluation_selection as stage
from cp7_ow04_restore_bundle import _catalog_rows

history, model, plan = parent.history, parent.model, parent.plan
CONTRACT = 'cp7.ow11.model-selection-native.v1'
IDS = dict(native=['OW11_MODEL_SELECTION_CATALOG22_COMPOSED_INVERSE',
 'OW11_MODEL_SELECTION_ACTUAL_V2_V3_LATEST_METHOD',
 'OW11_MODEL_SELECTION_POST_SOURCE_ACTOR_ACCESS',
 'OW11_MODEL_SELECTION_DENSE2000_PRIVATE_CURRENT'])
REQUIRED = dict(native=4)
EXPECTED = DECLARED = 4
FUNCTIONS, SCHEDULES = parent.FUNCTIONS, parent.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE, SCHEDULE_STATE, BOUNDED_STATE, REFERENCE_STATE, STAGE_STATE = {}, {}, {}, {}, {}, {}, {}
PARENT_CHECKER = None


def sources():
    root = Path(__file__).resolve().parent
    return dict(stage.sources(), **{str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest()
      for p in [Path(__file__),root/'cp7_ow11_model_selection_probe.py',
                root/'cp7_ow11_model_scoped_evaluation_cases.py',root/'cp7_ow11_model_scoped_dataset_cases.py']})


def install(cur):
    parent.PARENT_CHECKER = PARENT_CHECKER
    states, ms = parent.install(cur)
    catalog = _catalog_rows(cur)
    def checked(c):
        assert _catalog_rows(c) == catalog, 'MODEL_SELECTION_PARENT22_CHANGED'
        parent.stage.verify(c, ms)
    return states, ms, stage.install_delta(cur, checked)


def current(cur, target, actor, known=None):
    history.history.auth.actor(cur, actor)
    cur.execute('reset session authorization')
    cur.execute('set local role cp7_capture')
    assert cur.execute('select current_user,auth.uid()::text').fetchone() == ('cp7_capture', str(actor))
    start = monotonic()
    result = cur.execute('select cp7_model_evaluation_selection.current(%s,coalesce(%s::timestamptz,clock_timestamp()))', (target,known)).fetchone()[0]
    ms = (monotonic()-start)*1000
    plan.b.api.admin(cur)
    assert ms < 8000, ('MODEL_SELECTION_CURRENT_OVER8S',ms)
    return result, round(ms,3)


def cases(cur,today):
    def catalog():
        before = _catalog_rows(cur)
        states, ms, ss = install(cur)
        assert stage.verify(cur,ss)['private_functions'] == 2
        installed = _catalog_rows(cur)
        cur.execute('create view public.ow11_model_selection_inverse_guard as select cp7_model_evaluation_selection.current(null::text,null::timestamptz) value')
        guarded = _catalog_rows(cur)
        try: stage.rollback_preuse(cur,ss)
        except Exception as e: assert getattr(e,'sqlstate',None) == '2BP01',str(e)
        else: raise AssertionError('MODEL_SELECTION_DEPENDENT_VIEW_REMOVED')
        assert _catalog_rows(cur) == guarded
        cur.execute('drop view public.ow11_model_selection_inverse_guard')
        assert _catalog_rows(cur) == installed
        try: parent.stage.rollback_preuse(cur,ms)
        except ValueError as e: assert str(e) == 'MODEL_SCOPED_EVALUATION_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE'
        else: raise AssertionError('MODEL_SELECTION_PARENT_REMOVED')
        stage.rollback_preuse(cur,ss)
        parent.stage.rollback_preuse(cur,ms)
        parent.rollback_parents(cur,states)
        assert _catalog_rows(cur) == before
        PARENT_CHECKER(cur)
        return dict(status='PASS',exact_catalog22_composed_inverse=True,private2_public0_table0_replacement0=True,
          partial_inverse_atomic=True,scoped_parent_cannot_be_removed=True,source_sha256=stage.sources())

    def versions():
        install(cur)
        actor = model.master.role_actor(cur,'OWNER')
        f, gh, gq = model.legacy.prepared(cur,today,1,actor)
        request = uuid.uuid4()
        old = model.capture(cur,gq,actor,request)
        q = history.query(cur,f,today)
        sh = history.capture(cur,q,subject=actor)
        newer,_ = parent.capture(cur,parent.parent.query(sh,q),actor,request)
        before = plan.monetary_state(cur)
        scoped,_ = current(cur,q['target_key'],actor)
        assert scoped['selection']['run_id'] == newer['run_id']
        assert scoped['selection']['runtime'] == 'SCOPED_V3'
        assert scoped['selection']['read_method'] == 'erp_cp7_read_model_evaluation_v3'
        history.same_archive(newer,scoped['model'])
        assert old['request_id'] == newer['request_id'] and old['run_id'] != newer['run_id']
        assert plan.refusal(cur,lambda:current(cur,q['target_key'],actor,old['captured_at']))[0:2] == ('40001','CP7_MODEL_SELECTION_NEWER_EVALUATION')
        latest = model.capture(cur,gq,actor)
        global_current,_ = current(cur,q['target_key'],actor)
        assert global_current['selection']['runtime'] == 'GLOBAL_V2'
        assert global_current['selection']['run_id'] == latest['run_id']
        assert global_current['selection']['read_method'] == 'erp_cp7_read_model_evaluation_v2'
        history.same_archive(latest,global_current['model'])
        assert global_current['model']['current_guard']['state'] == scoped['model']['current_guard']['state'] == 'BASELINE_REQUIRED'
        assert global_current['source_hash'] != scoped['source_hash']
        assert plan.monetary_state(cur) == before
        return dict(status='PASS',actual_public_v2_and_v3_runs=True,same_request_UUID_distinct_runtime=True,
          exact_runtime_reader_body_preserved=True,newer_v2_beats_older_v3=True,old_cutoff_refused=True,
          latest_baseline_never_searches_older_winner=True,forecast_applied=False)

    def posted_access():
        install(cur)
        actor,role = history.history.auth.custom_actor(cur)
        f,q,h = parent.parent.prepare(cur,today,actor)
        empty,_ = current(cur,q['target_key'],actor)
        assert empty['selection']['run_id'] is None and empty['model'] is None
        m,_ = parent.capture(cur,parent.parent.query(h,q),actor)
        frozen = parent.stored(cur,m['run_id'])
        one,_ = current(cur,q['target_key'],actor)
        two,_ = current(cur,q['target_key'],actor)
        assert one['source_hash'] == two['source_hash']
        history.history.sales.fg.post_sale(cur,f['draft'])
        stale,_ = current(cur,q['target_key'],actor)
        history.same_archive(m,stale['model'])
        assert stale['model']['current_guard']['reason'] == 'NATIVE_HISTORY_SOURCE_CHANGED'
        assert stale['source_hash'] != one['source_hash']
        other,_ = history.history.auth.custom_actor(cur)
        foreign,_ = current(cur,q['target_key'],other)
        assert foreign['model'] is None and foreign['selection']['run_id'] is None
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(role,))
        assert plan.refusal(cur,lambda:current(cur,q['target_key'],actor))[0] == '42501'
        assert parent.stored(cur,m['run_id']) == frozen
        return dict(status='PASS',no_model_is_null_not_zero=True,current_source_after_actual_SALE=True,
          current_access_before_reference=True,actor_isolation=True,immutable_assessment_preserved=True)

    def dense():
        install(cur)
        actor = model.master.role_actor(cur,'OWNER')
        _,q,_ = parent.parent.prepare(cur,today,actor)
        volume = history.work.dense.seed(cur)
        h = history.capture(cur,q,subject=actor)
        m,_ = parent.capture(cur,parent.parent.query(h,q),actor)
        before = plan.monetary_state(cur)
        answer,ms = current(cur,q['target_key'],actor)
        assert answer['selection']['run_id'] == m['run_id']
        assert answer['selection']['runtime'] == 'SCOPED_V3'
        assert answer['model']['current_guard']['state'] == 'BASELINE_REQUIRED'
        assert plan.monetary_state(cur) == before
        return dict(status='PASS',label='SYNTHETIC_VOLUME_ACTUAL_NATIVE_MODELS_PRIVATE_SELECTOR',
          **volume,millis=ms,wall_limit_ms=8000,factory_SLA_claim=False,target_caller_integrated=False)

    return list(zip(IDS['native'],(catalog,versions,posted_access,dense)))


def races(tools,today): return []
def http_cases(http,today): return []
