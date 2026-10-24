"""Three Native public explanation cases; actual browser is a separate proof."""
import uuid
import cp7_ow11_analog_consumer_cases as consumer
import cp7_product_analog_provenance_stage as stage
from cp7_ow04_restore_bundle import _catalog_rows

choice,reader,bounded,plan=consumer.choice,consumer.reader,consumer.bounded,consumer.plan
CONTRACT='cp7.ow11.analog-provenance-native.v1'
IDS=dict(native=['OW11_ANALOG_PROVENANCE_CATALOG22_PREUSE_DEPENDENCY',
 'OW11_ANALOG_PROVENANCE_RETAINED_READER_V2_CURRENT_ACCESS',
 'OW11_ANALOG_PROVENANCE_PUBLIC_REORDER_V2_OWN_HISTORY_AND_CLEAR'])
REQUIRED=dict(native=3)
EXPECTED=DECLARED=3
FUNCTIONS=consumer.FUNCTIONS
SCHEDULES=consumer.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None


def install(cur):
    consumer.PARENT_CHECKER=PARENT_CHECKER
    before,rs,cs,state=consumer.install(cur)
    ps=stage.install_delta(cur,lambda c:consumer.stage.verify(c,state))
    return before,rs,cs,state,ps


def cases(cur,today):
    def catalog():
        before,rs,cs,state,ps=install(cur)
        assert stage.verify(cur,ps)['existing_replacements']==4
        snap=_catalog_rows(cur)
        cur.execute('create view public.ow11_provenance_inverse_guard as select cp7_product_analog_consumer.provenance(null,null,null,null,null,null)value')
        guarded=_catalog_rows(cur)
        try:stage.rollback_preuse(cur,ps)
        except Exception as e:assert getattr(e,'sqlstate',None)=='2BP01',str(e)
        else:raise AssertionError('PROVENANCE_DEPENDENT_VIEW_DROPPED')
        assert _catalog_rows(cur)==guarded
        cur.execute('drop view public.ow11_provenance_inverse_guard');assert _catalog_rows(cur)==snap
        stage.rollback_preuse(cur,ps);consumer.stage.rollback_preuse(cur,state)
        choice.stage.rollback_preuse(cur,cs);reader.remove(cur,before,rs)
        return dict(status='PASS',source_sha256=stage.verify_sources(),helper1_replacements4_tables0_public0=True,
                    exact_catalog22_inverse=True,dependent_view_failure_restores_partial_DDL=True)

    def retained_reader():
        _,_,_,_,ps=install(cur);f=consumer.prepare(cur,today);p=consumer.payload(f)
        initial,_=reader.call(cur,f,f['target'])
        assert initial['contract_version']=='cp7.product-analog-candidates-read.v2'
        assert initial['consumer_capability']=='REVIEWED_ANALOG_FOR_FRESH_CAPTURES'
        assert initial['target_demand']['basis']=='UNKNOWN'
        receipt,_=choice.save(cur,p);new=consumer.fresh(cur,today,f)
        current,ms=reader.call(cur,new,new['target']);d=current['target_demand']
        assert d==consumer.row(new)['demand_provenance']
        assert d['basis']==consumer.BASIS and d['target_pcs']=='0'
        assert d['own_total_pcs']=='0'and d['own_available_days']=='0'
        assert d['analog']['choice_id']==receipt['choice_id']and d['analog']['scale_factor']=='1'
        assert reader.call(cur,f,f['target'])[0]==initial # Immutable old result, explicitly captured.
        plan.b.api.admin(cur);actor=receipt['actor_scope_id']
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(actor,))
        assert plan.refusal(cur,lambda:reader.call(cur,new,new['target']))[0]=='42501'
        plan.b.api.admin(cur)
        try:stage.rollback_preuse(cur,ps)
        except ValueError as e:assert str(e)=='ANALOG_PROVENANCE_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE'
        else:raise AssertionError('PROVENANCE_USED_INVERSE_ALLOWED')
        return dict(status='PASS',actual_public_reader_v2=True,current_access_rechecked=True,
          old_retained_result_unchanged=True,captured_target_own_history_and_choice_bound=True,read_millis=ms,
          actual_Auth_HTTP_credit=False)

    def public_reorder():
        install(cur);f=consumer.prepare(cur,today);p=consumer.payload(f);choice.save(cur,p)
        import cp7_ow10_reorder_cases as reorder
        plan.b.api.admin(cur)
        sku=cur.execute('select sku from erp.products where id=%s',(f['target'].split(':')[0],)).fetchone()[0]
        physical=plan.monetary_state(cur)
        reorder.refresh(cur,None);w=reorder.workspace(cur,None,dict(sku=sku))
        r=next(x for x in w['page']['rows']if x['target_key']==f['target']);d=r['projection']['target_demand']
        assert r['projection']['contract_version']=='cp7.fg-reorder-projection.v2'
        assert r['sales_pcs']=='0'and r['counted_days']==0
        assert r['point']==d['reorder_point_pcs']=='0'and d['basis']==consumer.BASIS
        assert r['daily_sd']==d['daily_sd']
        clear=dict(p,action='CLEAR',expected_revision='1',source_request=None,source_hash=None,
          source_key=None,scale_factor=None,reason='Public projection withdrawal test')
        choice.save(cur,clear);reorder.refresh(cur,None)
        w=reorder.workspace(cur,None,dict(sku=sku));r=next(x for x in w['page']['rows']if x['target_key']==f['target'])
        assert r['point']is None and r['projection']['target_demand']['analog']['reason']=='ANALOG_CHOICE_CLEARED'
        assert plan.monetary_state(cur)==physical
        return dict(status='PASS',actual_public_reorder_refresh_and_workspace=True,
          own_sales_PCS_and_days_unchanged=True,one_shared_kernel=True,CLEAR_invalidates_threshold_cache=True,
          UNKNOWN_not_zero=True,no_physical_stock_money_HPP_change=True)

    return list(zip(IDS['native'],[catalog,retained_reader,public_reorder]))
