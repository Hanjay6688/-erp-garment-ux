"""Four private-source Native controls; no persisted model or Auth claim."""
from copy import deepcopy
from datetime import timedelta
from time import monotonic
import json
import uuid
import cp7_model_history_scope as stage
import cp7_ow13c_bounded_stage_cases as parent
import cp7_planning_history_cases as history
from cp7_ow04_restore_bundle import _catalog_rows

plan,work=parent.plan,parent.work
CONTRACT='cp7.ow11.model-history-scope-native.v1'
IDS=dict(native=['OW11_MODEL_HISTORY_SCOPE_CATALOG22_PRIVATE_INVERSE',
 'OW11_MODEL_HISTORY_SCOPE_ACTUAL_DRAFT_POST_RETURN_INVERSE',
 'OW11_MODEL_HISTORY_SCOPE_DENSE2000_202000_SINGLE_ROOT',
 'OW11_MODEL_HISTORY_SCOPE_ACTUAL_SOURCE_AND_BOTH_CLOCKS'])
REQUIRED=dict(native=4)
EXPECTED=DECLARED=4
FUNCTIONS,SCHEDULES=parent.FUNCTIONS,parent.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None


def install(cur):
    plan.b.api.admin(cur)
    return stage.install_delta(cur,PARENT_CHECKER)


def target(cur,root):
    plan.b.api.admin(cur)
    return cur.execute('select coalesce(identity_root_id,id)::text||\':\'||size_id::text from erp.products where id=%s',(root,)).fetchone()[0]


def capture(cur,key,q,inputs=True):
    plan.b.api.admin(cur)
    cur.execute('set local role cp7_capture')
    start=monotonic()
    result=cur.execute('select cp7_model_history_scope.capture(%s,%s::jsonb,%s)',(key,json.dumps(q),inputs)).fetchone()[0]
    elapsed=(monotonic()-start)*1000
    assert elapsed<8000,('MODEL_HISTORY_SCOPE_OVER8S',elapsed)
    plan.b.api.admin(cur)
    return result,round(elapsed,3)


def stock_operands(row):
    row=deepcopy(row)
    row['availability']['inputs'].update(snapshot_id='HASH',scope_id='SCOPE')
    return row


def parity(cur,f,q,physical,reserved,available,gross,returned='0'):
    key=target(cur,f['product']);before=work.metadata(cur)
    scoped,ms=capture(cur,key,q)
    cur.execute('set local role cp7_capture')
    whole=cur.execute('select cp7_planning.history_build(cp7_planning.history_source(),%s::jsonb)',(json.dumps(q),)).fetchone()[0]
    plan.b.api.admin(cur)
    row=scoped['result']['history']['rows'][0]
    assert scoped['result']['history']['rows']==[r for r in whole['history']['rows']if r['target_key']==key]
    assert list(map(stock_operands,scoped['result']['current_stock']))==[
        stock_operands(r)for r in whole['current_stock']if r['target_key']==key]
    assert row['gross_observed_pcs']==gross and row['days'][0]['returned_pcs']==returned
    a=scoped['result']['current_stock'][0]['availability']
    assert [a[k]for k in('physical_fg_pcs','reserved_pcs','available_fg_pcs')]==[physical,reserved,available]
    assert scoped['result']['history']['scope_id']=='SINGLE_CURRENT_PHYSICAL_ROOT'
    assert scoped['result']['training_known_at']==scoped['captured_at']
    assert scoped['result']['model_eligibility']=='HISTORICAL_AVAILABILITY_KNOWLEDGE_NOT_BACKFILLED'
    assert work.metadata(cur)==before
    return dict(millis=ms,gross=gross,returned=returned,stock=[physical,reserved,available])


def cases(cur,today):
    def catalog():
        before=_catalog_rows(cur);state=install(cur)
        v=stage.verify(cur,state)
        assert(v['private_functions'],v['new_tables'],v['public_rpcs'],v['existing_replacements'])==(4,0,0,0)
        current=_catalog_rows(cur)
        # raw is dropped last: a dependent view proves partial inverse is
        # savepoint-atomic, not merely that the first DROP was rejected.
        cur.execute('create view public.ow11_scoped_history_inverse_guard as select cp7_model_history_scope.raw(null::uuid)value')
        guarded=_catalog_rows(cur)
        try:stage.rollback_preuse(cur,state)
        except Exception as e:assert getattr(e,'sqlstate',None)=='2BP01',str(e)
        else:raise AssertionError('MODEL_HISTORY_SCOPE_DEPENDENT_VIEW_REMOVED')
        assert _catalog_rows(cur)==guarded
        cur.execute('drop view public.ow11_scoped_history_inverse_guard')
        assert _catalog_rows(cur)==current
        for role in('anon','authenticated','service_role','cp7_alert'):
            def denied_read():
                cur.execute('set local role '+role)
                cur.execute('select cp7_model_history_scope.raw(null::uuid)')
            denied=plan.refusal(cur,denied_read)
            assert denied[0]=='42501',denied
        stage.rollback_preuse(cur,state);assert _catalog_rows(cur)==before
        PARENT_CHECKER(cur)
        return dict(status='PASS',exact_catalog22_inverse=True,private4_tables0_RPC0_replacements0=True,
          partial_inverse_restored_after_dependent_view=True,direct_client_roles_denied=True,source_sha256=stage.sources())

    def lifecycle():
        install(cur);f=history.fixture(cur,today);q=history.query(today)
        points=[parity(cur,f,q,'100','24','76','0')]
        history.sales.fg.post_sale(cur,f['draft']);points.append(parity(cur,f,q,'76','0','76','24'))
        returned=history.sales.returned(cur,f);points.append(parity(cur,f,q,'77','0','77','24','1'))
        history.sales.native(cur,'select erp.reverse_sales_return(%s,%s)',(returned,'Scoped history actual return inverse'))
        history.sales.native(cur,'select erp.reverse_sale(%s,%s)',(f['sale'],'Scoped history actual sale inverse'))
        points.append(parity(cur,f,q,'100','0','100','0'))
        key=target(cur,f['product'])
        for invalid in (str(uuid.uuid4())+':'+key.split(':')[1],key.split(':')[0]+':'+str(uuid.uuid4())):
            assert plan.refusal(cur,lambda:capture(cur,invalid,q))[0]=='P0001'
        for query in(dict(q,through_date=str(today)),dict(q,from_date=str(today-timedelta(days=367))),dict(q,scope='GLOBAL')):
            assert plan.refusal(cur,lambda:capture(cur,key,query))[0] is not None
        return dict(status='PASS',actual_Native_draft_post_return_inverse=True,whole_Native_operands_exact=True,
          no_double_stock_subtraction=True,closed_query_absent_target_and_wrong_size_refused=True,
          readings=points,no_persisted_model_or_backfilled_knowledge=True)

    def dense():
        install(cur);f=history.fixture(cur,today);key=target(cur,f['product']);q=history.query(today)
        initial,_=capture(cur,key,q);size=work.dense.seed(cur)
        before=work.metadata(cur)
        cur.execute('set local role cp7_capture')
        whole=cur.execute('select cp7_planning.history_source()').fetchone()[0]
        plan.b.api.admin(cur)
        assert whole['status']=='INCOMPLETE'
        cur.execute("set local statement_timeout='8s'")
        current,ms=capture(cur,key,q)
        assert current['source_hash']==initial['source_hash']
        assert current['result']['history']['rows']==initial['result']['history']['rows']
        assert list(map(stock_operands,current['result']['current_stock']))==list(map(stock_operands,initial['result']['current_stock']))
        root=cur.execute("select id from erp.products where sku='OW13CSV-1'").fetchone()[0]
        selected,selected_ms=capture(cur,target(cur,root),q)
        assert selected['raw_capture_status']=='COMPLETE' and selected['source']['stock_reference']['row_count']=='101'
        assert len(selected['source']['facts']['products'])==1 and len(selected['source']['facts']['stock'])==101
        assert work.metadata(cur)==before
        return dict(status='PASS',label='SYNTHETIC_VOLUME_WITH_ACTUAL_PRIVATE_SOURCE',**size,
          original1000_global_bound_unchanged=True,single_explicit_root_only=True,unrelated_products_do_not_change_source=True,
          selected_stock_rows=101,millis=[ms,selected_ms],wall_limit_ms=8000,no_factory_SLA_claim=True)

    def clocks():
        install(cur);f=history.fixture(cur,today);key=target(cur,f['product']);q=history.query(today)
        first,_=capture(cur,key,q);same,_=capture(cur,key,q,False)
        assert same['source_hash']==first['source_hash'] and same['result'] is None
        old_ids=[m['id']for m in first['source']['facts']['stock']]
        plan.found_fg(cur,dict(root=f['product']),'1')
        at,recorded,n=cur.execute('select min(physical_at),min(system_created_at),count(*)from erp.fg_stock_movements '
            'where product_id=%s and not(id=any(%s::uuid[]))',(f['product'],old_ids)).fetchone()
        assert n>0 and at<recorded
        before=work.metadata(cur);new,_=capture(cur,key,q)
        assert new['source_hash']!=first['source_hash']
        assert int(new['source']['stock_reference']['row_count'])==int(first['source']['stock_reference']['row_count'])+n
        cur.execute('set local role cp7_capture')
        old_digest=cur.execute('select cp7_history_reference.stock_digest(%s::jsonb,%s)',
          (json.dumps(first['source']['facts']['products']),first['captured_at'])).fetchone()[0]
        plan.b.api.admin(cur)
        assert old_digest==first['source']['stock_reference']
        assert work.metadata(cur)==before
        return dict(status='PASS',actual_Native_stock_writer=True,physical_before_system_recording=True,
          prior_cutoff_still_excludes_later_recorded_stock=True,current_source_changes_without_rewriting_old_input=True,
          actual_server_training_clock=True,no_clock_or_posted_row_rewrite=True)

    return list(zip(IDS['native'],(catalog,lifecycle,dense,clocks)))


def races(tools,today):return []
def http_cases(http,today):return []
