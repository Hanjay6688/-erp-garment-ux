"""Actual Native capture parity for private scoped-model physical binding."""
from pathlib import Path
from hashlib import sha256
from time import monotonic
import json
import cp7_ow11_model_history_scope_cases as parent
import cp7_model_target_binding as stage
from cp7_ow04_restore_bundle import _catalog_rows

plan,work,history = parent.plan,parent.work,parent.history
CONTRACT = 'cp7.ow11.model-target-physical-binding-native.v1'
IDS = dict(native=['OW11_MODEL_TARGET_BINDING_CATALOG22_COMPOSED_INVERSE',
 'OW11_MODEL_TARGET_BINDING_ACTUAL_DRAFT_POST_RETURN_INVERSE',
 'OW11_MODEL_TARGET_BINDING_DENSE2000_OMITTED_GLOBAL_STOCK',
 'OW11_MODEL_TARGET_BINDING_ACTUAL_SYSTEM_CLOCK_SOURCE_CHANGE'])
REQUIRED = dict(native=4)
EXPECTED = DECLARED = 4
FUNCTIONS,SCHEDULES = parent.FUNCTIONS,parent.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE = {},{},{},{},{},{},{}
PARENT_CHECKER = None


def sources():
    root=Path(__file__).resolve().parent
    return dict(stage.sources(),**{str(p.relative_to(root)):sha256(p.read_bytes()).hexdigest()
      for p in [Path(__file__),root/'cp7_ow11_model_target_binding_probe.py',Path(parent.__file__)]})


def install(cur):
    parent.PARENT_CHECKER=PARENT_CHECKER
    ps=parent.install(cur)
    before=_catalog_rows(cur)
    def checked(c):
        assert _catalog_rows(c)==before,'MODEL_TARGET_BINDING_PARENT22_CHANGED'
        parent.stage.verify(c,ps)
    return ps,stage.install_delta(cur,checked)


def binding(cur,f,q):
    key=parent.target(cur,f['product'])
    scoped,_=parent.capture(cur,key,q,False)
    before=work.metadata(cur)
    cur.execute('set local role cp7_capture')
    start=monotonic()
    c=cur.execute('select cp7_reorder_inputs.capture_history(5000)').fetchone()[0]
    dg=cur.execute('select cp7_history_reference.stock_digest(%s::jsonb,%s::timestamptz)',
      (json.dumps(scoped['source']['facts']['products']),c['captured_at'])).fetchone()[0]
    answer=cur.execute('select cp7_model_target_binding.reference(%s::jsonb,%s,5000,%s::jsonb,%s)',
      (json.dumps(c),key,json.dumps(dg),scoped['producer_hash'])).fetchone()[0]
    ms=(monotonic()-start)*1000
    plan.b.api.admin(cur)
    assert answer['scoped_source_hash']==scoped['source_hash'],'BASELINE_SCOPED_PHYSICAL_IDENTITY_DIFFERS'
    assert answer['global_raw_capture_status']==c['status']
    assert answer['raw_native_capture_status_overridden']is False
    assert work.metadata(cur)==before
    assert ms<8000,('MODEL_TARGET_BINDING_OVER8S',ms)
    return answer,c,scoped,round(ms,3)


def cases(cur,today):
    def catalog():
        before=_catalog_rows(cur);ps,bs=install(cur)
        assert stage.verify(cur,bs)['private_functions']==2
        cur.execute('create view public.ow11_target_binding_guard as select cp7_model_target_binding.non_stock(null::jsonb,null::text,5000)value')
        guarded=_catalog_rows(cur)
        try:stage.rollback_preuse(cur,bs)
        except Exception as e:assert getattr(e,'sqlstate',None)=='2BP01',str(e)
        else:raise AssertionError('TARGET_BINDING_DEPENDENT_VIEW_REMOVED')
        assert _catalog_rows(cur)==guarded
        cur.execute('drop view public.ow11_target_binding_guard')
        stage.rollback_preuse(cur,bs);parent.stage.rollback_preuse(cur,ps)
        assert _catalog_rows(cur)==before;PARENT_CHECKER(cur)
        return dict(status='PASS',exact_catalog22_composed_inverse=True,private2_public0_table0_replacement0=True,
          partial_inverse_atomic=True,source_sha256=stage.sources())

    def lifecycle():
        install(cur);f=history.fixture(cur,today);q=history.query(today)
        points=[]
        def read():
            x,c,_,ms=binding(cur,f,q);assert c['status']=='COMPLETE'
            points.append(dict(hash=x['scoped_source_hash'],stock_rows=x['stock_reference']['row_count'],millis=ms))
        read();history.sales.fg.post_sale(cur,f['draft']);read()
        ret=history.sales.returned(cur,f);read()
        history.sales.native(cur,'select erp.reverse_sales_return(%s,%s)',(ret,'Binding return inverse'))
        history.sales.native(cur,'select erp.reverse_sale(%s,%s)',(f['sale'],'Binding sale inverse'));read()
        assert len({x['hash']for x in points})==4
        return dict(status='PASS',actual_draft_post_return_inverse=True,global_to_scoped_physical_identity_exact=True,
          original_and_reversal_journals_retained=True,posted_history_immutable=True,points=points)

    def dense():
        install(cur);f=history.fixture(cur,today);q=history.query(today)
        first,_,_,_=binding(cur,f,q);volume=work.dense.seed(cur)
        current,c,scoped,ms=binding(cur,f,q)
        assert c['status']=='INCOMPLETE'and c['stock_raw_omitted']is True and c['facts']['stock']==[]
        assert scoped['raw_capture_status']=='COMPLETE'
        assert current['scoped_source_hash']==first['scoped_source_hash']
        assert int(current['stock_reference']['row_count'])>0
        root=cur.execute("select id from erp.products where sku='OW13CSV-1'").fetchone()[0]
        other,_,_,other_ms=binding(cur,dict(product=root),q)
        assert other['stock_reference']['row_count']=='101'
        return dict(status='PASS',label='SYNTHETIC_VOLUME_ACTUAL_NATIVE_CAPTURE_BINDING',**volume,
          global_omitted_stock_not_zero=True,unchanged_target_identity=True,selected_target_stock_rows=101,
          millis=[ms,other_ms],wall_limit_ms=8000,factory_SLA_claim=False,target_caller_integrated=False)

    def clocks():
        install(cur);f=history.fixture(cur,today);q=history.query(today)
        first,c,scoped,_=binding(cur,f,q)
        plan.found_fg(cur,dict(root=f['product']),'1')
        second,_,_,_=binding(cur,f,q)
        assert second['scoped_source_hash']!=first['scoped_source_hash']
        cur.execute('set local role cp7_capture')
        old_digest=cur.execute('select cp7_history_reference.stock_digest(%s::jsonb,%s::timestamptz)',
          (json.dumps(scoped['source']['facts']['products']),c['captured_at'])).fetchone()[0]
        assert old_digest==first['stock_reference']
        old=cur.execute('select cp7_model_target_binding.reference(%s::jsonb,%s,5000,%s::jsonb,%s)',
          (json.dumps(c),first['target_key'],json.dumps(old_digest),scoped['producer_hash'])).fetchone()[0]
        assert old==first
        plan.b.api.admin(cur)
        bad=dict(first['stock_reference'],rows_sha256='0'*64)
        refusal=plan.refusal(cur,lambda:cur.execute('select cp7_model_target_binding.reference(%s::jsonb,%s,5000,%s::jsonb,%s)',
          (json.dumps(c),first['target_key'],json.dumps(bad),scoped['producer_hash'])))
        assert refusal[0:2]==('P0001','CP7_MODEL_TARGET_BINDING_STOCK_MISMATCH')
        return dict(status='PASS',actual_backdated_physical_new_system_stock=True,old_cutoff_digest_and_binding_unchanged=True,
          changed_current_source_new_binding=True,raw_complete_stock_disagreement_refused=True)

    return list(zip(IDS['native'],(catalog,lifecycle,dense,clocks)))


def races(tools,today):return []
def http_cases(http,today):return []
