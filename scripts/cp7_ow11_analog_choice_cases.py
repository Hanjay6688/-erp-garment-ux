"""Native confirmation metadata controls; no forecast, browser or race credit."""
from datetime import timedelta
from decimal import Decimal
from time import monotonic
import json
import uuid
import cp7_product_analog_choice_stage as stage
import cp7_ow11_analog_reader_cases as reader
from cp7_ow04_restore_bundle import _catalog_rows

bounded,volume,plan=reader.bounded,reader.volume,reader.plan
CONTRACT='cp7.ow11.analog-choice-native.v1'
IDS=dict(native=['OW11_ANALOG_CHOICE_CATALOG22_PREUSE_AND_DEPENDENCY',
                 'OW11_ANALOG_CHOICE_APPEND_CLEAR_REPLAY_CAS_AND_CLOCKS',
                 'OW11_ANALOG_CHOICE_REVIEW_SCALE_SIZE_UNKNOWN_AND_SELF',
                 'OW11_ANALOG_CHOICE_STALE_FOREIGN_K2_AND_CURRENT_ACCESS',
                 'OW11_ANALOG_CHOICE_ATOMIC_LAST_TABLE_FAULT',
                 'OW11_ANALOG_CHOICE_DENSE2000_202000_THREE_WRITES_UNDER8S'])
REQUIRED=dict(native=6)
EXPECTED=DECLARED=6
FUNCTIONS=(*reader.FUNCTIONS,'erp_cp7_get_product_analog_choices_v1','erp_cp7_save_product_analog_choice_v1')
SCHEDULES=reader.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None


def install(cur):
    reader.PARENT_CHECKER=PARENT_CHECKER
    before,rs=reader.install(cur)
    from cp7_ow11_analog_browser_probe import verify_composed
    cs=stage.install_delta(cur,lambda c:verify_composed(c,PARENT_CHECKER,rs))
    return before,rs,cs


def prepare(cur,today,subject=None,dense=False):
    x=plan.fixture(cur,today)
    imported=volume.import_batch(cur,today,11,volume.Phases())
    historical=reader.historical.seed(cur,imported)
    target=imported[0]['target']
    source=next(p['target']for p in historical if p['target'].split(':')[1]==target.split(':')[1])
    different=next(p['target']for p in historical if p['target'].split(':')[1]!=target.split(':')[1])
    reader.explicit_profile(cur,imported[0]['root'])
    size=bounded.work.dense.seed(cur)if dense else None
    f=reader.from_current(cur,today,x,subject);bounded.finish(cur,f)
    f.update(target=target,source=source,different=different,imported=imported,size=size)
    f['payload']=dict(contract_version='cp7.product-analog-choice-command.v1',source_request=f['key'],
                      source_hash=f['pages']['reference']['source_hash'],access_epoch=f['pages']['access_epoch'],
                      target_key=target,source_key=source,scale_factor='1.25',
                      reason='Explicit SYNTHETIC test comparison; not an owner factory setting',reviewed=True,
                      expected_revision='0',action='CONFIRM')
    return f


def save(cur,p,key=None,subject=None):
    started=monotonic()
    result=plan.rpc(cur,'erp_cp7_save_product_analog_choice_v1',(json.dumps(p),key or uuid.uuid4()),subject)
    elapsed=(monotonic()-started)*1000
    assert elapsed<8000,('ANALOG_CHOICE_WRITE_OVER8S',elapsed)
    return result,round(elapsed,3)


def get(cur,target,subject=None):
    return plan.rpc(cur,'erp_cp7_get_product_analog_choices_v1',([target],),subject)


def metadata(cur):
    plan.b.api.admin(cur)
    zone=cur.execute('show TimeZone').fetchone()[0]
    cur.execute("set local TimeZone='UTC'")
    try:
        return {t:cur.execute('select md5(coalesce(jsonb_agg(to_jsonb(x)order by to_jsonb(x)::text),\'[]\')::text)from '+t+' x').fetchone()[0]for t in stage.TABLES}
    finally:cur.execute("select set_config('TimeZone',%s,true)",(zone,))


def cases(cur,today):
    def catalog():
        before,rs,cs=install(cur)
        assert stage.verify(cur,cs)['new_tables']==2
        snap=_catalog_rows(cur)
        cur.execute("create view public.ow11_choice_inverse_guard as select target_key from cp7_product_analog_choice.choices")
        guarded=_catalog_rows(cur)
        try:stage.rollback_preuse(cur,cs)
        except Exception as e:assert getattr(e,'sqlstate',None)=='2BP01',str(e)
        else:raise AssertionError('ANALOG_CHOICE_DEPENDENT_VIEW_REMOVED')
        assert _catalog_rows(cur)==guarded
        cur.execute('drop view public.ow11_choice_inverse_guard')
        assert _catalog_rows(cur)==snap
        stage.rollback_preuse(cur,cs);reader.remove(cur,before,rs)
        return dict(status='PASS',source_owner_ACL_RLS_GUC_exact=True,private4_public2_tables2_replacements0=True,
                    exact_preuse_catalog22_inverse=True,dependent_view_failure_restores_partial_DDL=True,
                    forecast_applied=False)

    def lifecycle():
        _,_,cs=install(cur);f=prepare(cur,today)
        physical=plan.monetary_state(cur);key=str(uuid.uuid4())
        before=get(cur,f['target'])['rows'][0];assert before['state']=='UNREVIEWED'and before['revision']=='0'
        first,ms=save(cur,f['payload'],key)
        assert first['revision']=='1'and first['state']=='CONFIRMED_ASSUMPTION'and first['forecast_applied']is False
        evidence=first['evidence']
        assert evidence['available_total_pcs']=='0'and evidence['available_days']=='1'and evidence['scale_factor']=='1.25'
        assert evidence['source_key']==f['source']and evidence['analysis_source_hash']==f['payload']['source_hash']
        assert save(cur,f['payload'],key)[0]==first
        snap=metadata(cur)
        plan.refused(cur,lambda:save(cur,dict(f['payload'],reason='changed'),key),'CP7_ANALOG_CHOICE_REQUEST_CHANGED')
        plan.refused(cur,lambda:save(cur,f['payload']),'CP7_ANALOG_CHOICE_REVISION_CHANGED')
        assert metadata(cur)==snap
        clear=dict(f['payload'],action='CLEAR',expected_revision='1',source_request=None,source_hash=None,
                   source_key=None,scale_factor=None,reason='Explicit test withdrawal')
        cleared,_=save(cur,clear);assert cleared['revision']=='2'and cleared['state']=='CLEARED'
        assert get(cur,f['target'])['rows'][0]['state']=='CLEARED'
        assert save(cur,f['payload'],key)[0]==first # Exact receipt remains after later corrections.
        plan.b.api.admin(cur)
        current=cur.execute('select cp7_product_analog_choice.source_at(%s,%s::timestamptz)',
                            ([f['target']],first['recorded_at'])).fetchone()[0][0]
        assert current['revision']=='1'and current['choice_id']==first['choice_id']
        earlier=cur.execute("select cp7_product_analog_choice.source_at(%s,%s::timestamptz-interval'1 microsecond')",
                            ([f['target']],first['recorded_at'])).fetchone()[0][0]
        assert earlier['revision']=='0'
        snap=_catalog_rows(cur)
        try:stage.rollback_preuse(cur,cs)
        except ValueError as e:assert str(e)=='ANALOG_CHOICE_AFTER_USE_REQUIRES_BACKUP_RESTORE'
        else:raise AssertionError('ANALOG_CHOICE_USED_INVERSE_ALLOWED')
        assert _catalog_rows(cur)==snap
        def mutate():
            plan.b.api.admin(cur)
            cur.execute("update cp7_product_analog_choice.choices set reason='changed'where id=%s",(first['choice_id'],))
        assert plan.refusal(cur,mutate)[0]=='55000'
        assert plan.monetary_state(cur)==physical
        return dict(status='PASS',explicit_scale_reason_and_AVAILABLE_zero=True,append_clear_revision_CAS=True,
                    exact_UUID_payload_replay_after_later_clear=True,recorded_clock_no_backdate=True,
                    immutable_choice_update_denied=True,used_inverse_refused_before_DDL=True,
                    no_physical_stock_money_HPP_change=True,write_millis=ms,forecast_applied=False)

    def validation():
        install(cur);f=prepare(cur,today);snap=metadata(cur)
        unknown=next(p['target']for p in f['imported']if p['target']!=f['target']and p['target'].split(':')[1]==f['target'].split(':')[1])
        cases=[(dict(reviewed=False),'CP7_ANALOG_CHOICE_REVIEW'),(dict(scale_factor='0'),'CP7_ANALOG_CHOICE_SCALE'),
               (dict(scale_factor=None),'CP7_F04_DECIMAL'),(dict(reason=' '),'CP7_ANALOG_CHOICE_REVIEW'),
               (dict(source_key=f['target']),'CP7_ANALOG_CHOICE_SELF'),
               (dict(source_key=f['different']),'CP7_ANALOG_CHOICE_SIZE'),
               (dict(source_key=unknown),'CP7_ANALOG_CHOICE_INSUFFICIENT')]
        for changed,message in cases:plan.refused(cur,lambda:save(cur,dict(f['payload'],**changed)),message,
                                                 '22023'if message=='CP7_F04_DECIMAL'else'P0001')
        assert metadata(cur)==snap
        return dict(status='PASS',explicit_review_scale_reason_required=True,self_and_cross_size_refused=True,
                    actual_new_import_UNKNOWN_not_zero=True,all_refusals_leave_both_tables_exact=True,
                    no_default_scale_or_minimum=True)

    def stale_access():
        install(cur)
        actor=bounded.work.base.retained.master.role_actor(cur,'OWNER')
        stranger=bounded.work.base.retained.master.role_actor(cur,'OWNER')
        f=prepare(cur,today,actor);key=str(uuid.uuid4())
        first,_=save(cur,f['payload'],key,actor)
        foreign=dict(f['payload'],expected_revision='1',access_epoch=reader.epoch(cur,stranger))
        plan.refused(cur,lambda:save(cur,foreign,subject=stranger),'CP7_PRODUCT_ANALOG_RUN_UNAVAILABLE','42501')
        plan.found_fg(cur,f['x'],'1');snap=metadata(cur)
        plan.refused(cur,lambda:save(cur,dict(f['payload'],expected_revision='1'),subject=actor),'CP7_ANALOG_CHOICE_SOURCE_CHANGED','40001')
        assert save(cur,f['payload'],key,actor)[0]==first
        plan.b.api.admin(cur);bounded.retention.age(cur,f['done']['run_id'],timedelta(days=8))
        plan.refused(cur,lambda:save(cur,dict(f['payload'],expected_revision='1'),subject=actor),bounded.retention.EXPIRED)
        assert save(cur,f['payload'],key,actor)[0]==first
        plan.b.api.admin(cur);cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(actor,))
        for operation in(lambda:save(cur,f['payload'],key,actor),lambda:get(cur,f['target'],actor)):
            assert plan.refusal(cur,operation)[0]=='42501'
        assert metadata(cur)==snap
        return dict(status='PASS',actual_Native_stock_change_refuses_new_confirmation=True,
                    foreign_current_actor_epoch_and_K2_refused=True,committed_receipt_survives_source_change_and_K2=True,
                    current_deactivated_actor_cannot_replay_or_read=True,actual_Auth_HTTP_credit=False,concurrency_test=False)

    def atomic():
        install(cur);f=prepare(cur,today);plan.b.api.admin(cur)
        cur.execute("create function pg_temp.ow11_choice_fault()returns trigger language plpgsql as $$begin raise exception 'OW11_CHOICE_METADATA_FAULT';end;$$")
        cur.execute('create trigger ow11_choice_fault before insert on cp7_product_analog_choice.commands for each row execute function pg_temp.ow11_choice_fault()')
        snap=metadata(cur);physical=plan.monetary_state(cur)
        plan.refused(cur,lambda:save(cur,f['payload']),'OW11_CHOICE_METADATA_FAULT')
        assert metadata(cur)==snap and plan.monetary_state(cur)==physical
        return dict(status='PASS',failure_after_choice_insert_rolls_both_metadata_tables_back=True,
                    no_physical_stock_money_HPP_change=True)

    def dense():
        install(cur);f=prepare(cur,today,dense=True);c=f['row']['reference']
        assert c['status']=='INCOMPLETE'and int(c['bounded_stock_reference']['row_count'])>=202000
        physical=plan.monetary_state(cur);times=[];receipts=[];keys=[]
        for n in range(3):
            key=str(uuid.uuid4());p=dict(f['payload'],expected_revision=str(n))
            result,ms=save(cur,p,key);times.append(ms);keys.append(key);receipts.append(result)
            assert result['revision']==str(n+1)
        assert save(cur,f['payload'],keys[0])[0]==receipts[0]
        assert plan.monetary_state(cur)==physical
        return dict(status='PASS',**f['size'],actual_products=len(c['facts']['products']),
                    full_stock_digest_rows=int(c['bounded_stock_reference']['row_count']),
                    actual_DONE_reference=True,raw_native_INCOMPLETE_not_promoted=True,
                    fresh_unique_UUIDs=3,exact_first_UUID_replay=True,write_millis=times,
                    full_source_checks_inside_measured_writer=2,statement_limit='8s',wall_limit_ms=8000,
                    no_source_or_hash_override=True,factory_SLA=False,forecast_applied=False)

    return list(zip(IDS['native'],[catalog,lifecycle,validation,stale_access,atomic,dense]))
