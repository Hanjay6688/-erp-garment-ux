"""Four Native controls for actor/version-bound batched target sources."""
import json
from pathlib import Path
from hashlib import sha256
from time import monotonic
import cp7_ow11_model_selection_cases as parent
import cp7_model_target_binding as binding
import cp7_model_target_source_v2 as stage
from cp7_ow04_restore_bundle import _catalog_rows

history, model, plan = parent.history, parent.model, parent.plan
scoped = parent.parent
CONTRACT = 'cp7.ow11.model-target-source-v2-native.v1'
IDS = dict(native=['OW11_MODEL_SOURCE_V2_CATALOG22_COMPOSED_INVERSE',
 'OW11_MODEL_SOURCE_V2_ACTUAL_LATEST_VERSION_AND_POST',
 'OW11_MODEL_SOURCE_V2_ACTUAL_ACCESS_AND_WAREHOUSE_BOUNDARY',
 'OW11_MODEL_SOURCE_V2_DENSE2000_BATCHED_PHYSICAL_SOURCE'])
REQUIRED = dict(native=4)
EXPECTED = DECLARED = 4
FUNCTIONS, SCHEDULES = parent.FUNCTIONS, parent.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE, SCHEDULE_STATE, BOUNDED_STATE, REFERENCE_STATE, STAGE_STATE = {}, {}, {}, {}, {}, {}, {}
PARENT_CHECKER = None


def sources():
    root = Path(__file__).resolve().parent
    return dict(stage.sources(), **binding.sources(), **parent.sources(), **{
      str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest()
      for p in [Path(__file__),root/'cp7_ow11_model_target_source_v2_probe.py']})


def install(cur):
    parent.PARENT_CHECKER = PARENT_CHECKER
    ps = parent.install(cur)
    before = _catalog_rows(cur)
    def selected(c):
        assert _catalog_rows(c) == before, 'MODEL_SOURCE_V2_SELECTION_PARENT22_CHANGED'
        parent.stage.verify(c, ps[-1])
    bs = binding.install_delta(cur, selected)
    composed = _catalog_rows(cur)
    def checked(c):
        assert _catalog_rows(c) == composed, 'MODEL_SOURCE_V2_PHYSICAL_PARENT22_CHANGED'
        binding.verify(c, bs)
    return ps, bs, stage.install_delta(cur, checked)


def private(cur, actor, capture=None, warehouse=False):
    history.history.auth.actor(cur, actor)
    cur.execute('reset session authorization')
    cur.execute('set local role cp7_capture')
    assert cur.execute('select current_user,auth.uid()::text').fetchone() == ('cp7_capture', str(actor))
    start = monotonic()
    if capture is None:
        capture = cur.execute('select cp7_reorder_inputs.capture_history(5000)').fetchone()[0]
    fn = 'capture_for_reorder' if warehouse else 'capture'
    answer = cur.execute('select cp7_model_target_source_v2.'+fn+'(%s::jsonb,5000)', (json.dumps(capture),)).fetchone()[0]
    ms = (monotonic()-start)*1000
    plan.b.api.admin(cur)
    assert ms < 8000, ('MODEL_SOURCE_V2_OVER8S',ms)
    return answer, capture, round(ms,3)


def row(answer, key):
    return next(x for x in answer['rows'] if x['target_key']==key)


def cases(cur, today):
    def catalog():
        before = _catalog_rows(cur)
        ps, bs, ss = install(cur)
        assert stage.verify(cur,ss)['private_functions'] == 11
        installed = _catalog_rows(cur)
        cur.execute('create view public.ow11_source_v2_inverse_guard as select cp7_model_target_source_v2.capture(null::jsonb,5000) value')
        guarded = _catalog_rows(cur)
        try: stage.rollback_preuse(cur,ss)
        except Exception as e: assert getattr(e,'sqlstate',None)=='2BP01',str(e)
        else: raise AssertionError('MODEL_SOURCE_V2_DEPENDENT_VIEW_REMOVED')
        assert _catalog_rows(cur)==guarded
        cur.execute('drop view public.ow11_source_v2_inverse_guard')
        cur.execute("create function public.ow11_source_legacy_inverse_guard()returns text language plpgsql as $$begin return cp7_model_target_source.engine();end$$")
        guarded = _catalog_rows(cur)
        try: stage.rollback_preuse(cur,ss)
        except ValueError as e: assert str(e)=='MODEL_TARGET_SOURCE_V2_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE'
        else: raise AssertionError('MODEL_SOURCE_V2_LEGACY_CALLER_REMOVED')
        assert _catalog_rows(cur)==guarded
        cur.execute('drop function public.ow11_source_legacy_inverse_guard()')
        assert _catalog_rows(cur)==installed
        try: binding.rollback_preuse(cur,bs)
        except ValueError as e: assert str(e)=='MODEL_TARGET_BINDING_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE'
        else: raise AssertionError('MODEL_SOURCE_V2_BINDING_PARENT_REMOVED')
        stage.rollback_preuse(cur,ss)
        binding.rollback_preuse(cur,bs)
        states, ms, selection_state = ps
        parent.stage.rollback_preuse(cur,selection_state)
        scoped.stage.rollback_preuse(cur,ms)
        scoped.rollback_parents(cur,states)
        assert _catalog_rows(cur)==before
        PARENT_CHECKER(cur)
        return dict(status='PASS',exact_catalog22_composed_inverse=True,legacy4_verbatim_plus_batched7=True,
          private11_RPC0_table0_replacement0=True,partial_inverse_atomic=True,both_owned_schema_callers_protected=True,
          physical_parent_cannot_be_removed=True,source_sha256=stage.sources())

    def versions_post():
        install(cur)
        actor = model.master.role_actor(cur,'OWNER')
        f, gh, gq = model.legacy.prepared(cur,today,1,actor)
        model.capture(cur,gq,actor)
        q = history.query(cur,f,today)
        h = history.capture(cur,q,subject=actor)
        m,_ = scoped.capture(cur,scoped.parent.query(h,q),actor)
        frozen = scoped.stored(cur,m['run_id'])
        before = plan.monetary_state(cur)
        a,c,_ = private(cur,actor)
        b,_,_ = private(cur,actor)
        r = row(a,q['target_key'])
        assert r['run_id']==m['run_id'] and r['runtime']=='SCOPED_V3'
        assert r['read_method']=='erp_cp7_read_model_evaluation_v3'
        assert r['history_source_hash']==r['physical_source_hash']==h['source_hash']
        assert r['state']=='BASELINE_REQUIRED' and r['forecast'] is None
        assert a['source_hash']==b['source_hash'] and plan.monetary_state(cur)==before
        newer = model.capture(cur,gq,actor)
        v2,_,_ = private(cur,actor)
        assert row(v2,q['target_key'])['run_id']==newer['run_id']
        assert row(v2,q['target_key'])['runtime']=='GLOBAL_V2'
        newest,_ = scoped.capture(cur,scoped.parent.query(h,q),actor)
        history.history.sales.fg.post_sale(cur,f['draft'])
        stale,_,_ = private(cur,actor)
        r = row(stale,q['target_key'])
        assert r['run_id']==newest['run_id'] and r['reason']=='NATIVE_HISTORY_SOURCE_CHANGED'
        assert r['history_source_hash']!=r['physical_source_hash']
        assert plan.refusal(cur,lambda:private(cur,actor,c))[0]=='40001'
        assert scoped.stored(cur,m['run_id'])==frozen
        return dict(status='PASS',actual_v2_v3_latest_method_and_actor_bound=True,unchanged_hash_clock_stable=True,
          current_actual_SALE_changes_physical_identity=True,old_capture_refused=True,old_immutable_model_unchanged=True,
          policy_UNKNOWN_no_forecast=True)

    def access():
        install(cur)
        actor,role = history.history.auth.custom_actor(cur)
        _,q,h = scoped.parent.prepare(cur,today,actor)
        m,_ = scoped.capture(cur,scoped.parent.query(h,q),actor)
        before = scoped.stored(cur,m['run_id'])
        own,c,_ = private(cur,actor)
        assert row(own,q['target_key'])['run_id']==m['run_id']
        other,_ = history.history.auth.custom_actor(cur)
        foreign,_,_ = private(cur,other)
        assert all(x['run_id'] is None and x['runtime'] is None for x in foreign['rows'])
        cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(role,))
        assert plan.refusal(cur,lambda:private(cur,actor,c))[0]=='42501'
        warehouse,_,_ = private(cur,actor,c,True)
        assert warehouse['policy_source'] is None and warehouse['selection'] is None
        for r in warehouse['rows']:
            assert r['reason']=='MODEL_CURRENT_ACCESS_REQUIRED'
            assert all(r[k] is None for k in ('run_id','runtime','read_method','history_run_id','history_query','history_source_hash','physical_source_hash','model_source_hash','selected_model','forecast'))
        assert scoped.stored(cur,m['run_id'])==before
        return dict(status='PASS',current_four_permission_enforced=True,foreign_actor_model_null=True,
          warehouse_only_still_reads_without_archive_or_policy=True,immutable_assessment_unchanged=True)

    def dense():
        install(cur)
        actor = model.master.role_actor(cur,'OWNER')
        _,q,_ = scoped.parent.prepare(cur,today,actor)
        volume = history.work.dense.seed(cur)
        h = history.capture(cur,q,subject=actor)
        m,_ = scoped.capture(cur,scoped.parent.query(h,q),actor)
        product = cur.execute("select id from erp.products where sku='OW13CSV-1'").fetchone()[0]
        q2 = dict(q,target_key=history.source.target(cur,product))
        h2 = history.capture(cur,q2,subject=actor)
        m2,_ = scoped.capture(cur,scoped.parent.query(h2,q2),actor)
        before = plan.monetary_state(cur)
        answer,c,ms = private(cur,actor)
        assert c['status']=='INCOMPLETE' and c['stock_raw_omitted'] is True
        assert len(answer['rows'])==len(c['facts']['products'])>=2000
        for qx,hx,mx in ((q,h,m),(q2,h2,m2)):
            r = row(answer,qx['target_key'])
            assert r['run_id']==mx['run_id'] and r['runtime']=='SCOPED_V3'
            assert r['history_source_hash']==r['physical_source_hash']==hx['source_hash']
            assert r['state']=='BASELINE_REQUIRED' and r['forecast'] is None
        assert plan.monetary_state(cur)==before
        return dict(status='PASS',label='SYNTHETIC_VOLUME_ACTUAL_NATIVE_MULTI_MODEL_BATCH_SOURCE',**volume,
          millis=ms,wall_limit_ms=8000,rows=len(answer['rows']),scoped_models=2,all_missing_models_explicit=True,
          raw_stock_omitted_not_zero=True,exact_scoped_physical_identity=True,factory_SLA_claim=False,target_caller_integrated=False)

    return list(zip(IDS['native'],(catalog,versions_post,access,dense)))


def races(tools,today): return []
def http_cases(http,today): return []
