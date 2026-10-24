"""Direct-reader regression and Native current-source controls, separate budget."""
from time import monotonic
import json
import uuid
import cp7_ow11_analog_provenance_cases as parent
import cp7_baseline_freshness_stage as stage
import cp7_planning_baseline_cases as baseline
from cp7_ow04_restore_bundle import _catalog_rows

consumer,choice,reader,plan,bounded=parent.consumer,parent.choice,parent.reader,parent.plan,parent.bounded
CONTRACT='cp7.ow11.baseline-freshness-native.v1'
IDS=dict(native=['OW11_BASELINE_FRESHNESS_CATALOG22_PREUSE',
 'OW11_BASELINE_FRESHNESS_ACTUAL_REGRESSION_CONFIRM_CLEAR_REPLAY',
 'OW11_BASELINE_FRESHNESS_POST_PROFILE_CURRENT_ACCESS'])
REQUIRED=dict(native=3)
EXPECTED=DECLARED=3
FUNCTIONS=parent.FUNCTIONS
SCHEDULES=parent.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None


def install_parent(cur):
    parent.PARENT_CHECKER=PARENT_CHECKER
    return parent.install(cur)


def install(cur):
    parents=install_parent(cur)
    s=stage.install_delta(cur,lambda c:parent.stage.verify(c,parents[-1]))
    return parents,s


def call(cur,name,args,subject=None):
    start=monotonic();result=plan.rpc(cur,name,args,subject)
    ms=(monotonic()-start)*1000;assert ms<8000,('BASELINE_FRESHNESS_OVER8S',name,ms)
    return result


def capture(cur,q,key=None,subject=None):
    return call(cur,'erp_cp7_capture_baseline_v1',(json.dumps(q),key or uuid.uuid4()),subject)


def read(cur,run,subject=None):
    return call(cur,'erp_cp7_read_baseline_v1',(run,),subject)


def stored(cur,run):
    plan.b.api.admin(cur)
    return cur.execute('select to_jsonb(r)from cp7_baseline_native.runs r where id=%s',(run,)).fetchone()[0]


def cases(cur,today):
    def catalog():
        before=_catalog_rows(cur);parents,s=install(cur)
        assert stage.verify(cur,s)['existing_replacements']==1
        stage.rollback_preuse(cur,s);parent.stage.verify(cur,parents[-1])
        original,rs,cs,consumer_state,provenance_state=parents
        parent.stage.rollback_preuse(cur,provenance_state);consumer.stage.rollback_preuse(cur,consumer_state)
        choice.stage.rollback_preuse(cur,cs);reader.remove(cur,original,rs)
        assert _catalog_rows(cur)==before
        return dict(status='PASS',exact_catalog22_inverse=True,replacement1_newfunctions0_tables0_public0=True,
                    all_old_owner_ACL_GUC_unchanged=True,source_sha256=stage.verify_sources())

    def lifecycle():
        parents=install_parent(cur);f=consumer.prepare(cur,today);p=consumer.payload(f);choice.save(cur,p)
        q=f['row']['query'];key=uuid.uuid4();physical=plan.monetary_state(cur)
        original=capture(cur,q,key);assert original['source_state']=='ARCHIVED_STALE'
        frozen=stored(cur,original['run_id'])
        s=stage.install_delta(cur,lambda c:parent.stage.verify(c,parents[-1]))
        current=read(cur,original['run_id']);assert current['source_state']=='UNCHANGED'
        assert {k:v for k,v in current.items()if k!='source_state'}=={k:v for k,v in original.items()if k!='source_state'}
        assert capture(cur,q,key)==current and stored(cur,original['run_id'])==frozen
        assert plan.refusal(cur,lambda:capture(cur,dict(q,group_mode='RESTATED'),key))[1]=='CP7_BASELINE_REQUEST_CHANGED'
        clear=dict(p,action='CLEAR',expected_revision='1',source_request=None,source_hash=None,
          source_key=None,scale_factor=None,reason='Direct baseline reader freshness withdrawal')
        choice.save(cur,clear);old=read(cur,original['run_id']);assert old==original
        fresh=capture(cur,q);assert fresh['source_state']=='UNCHANGED'
        target=next(x for x in fresh['rows']if x['target_key']==f['target'])
        assert target['target']['target_pcs']is None and target['analog_resolution']['reason']=='ANALOG_CHOICE_CLEARED'
        assert stored(cur,original['run_id'])==frozen and plan.monetary_state(cur)==physical
        try:stage.rollback_preuse(cur,s)
        except ValueError as e:assert str(e)=='BASELINE_FRESHNESS_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE'
        else:raise AssertionError('BASELINE_FRESHNESS_AFTER_USE_INVERSE_ALLOWED')
        return dict(status='PASS',actual_predecessor_false_stale_reproduced=True,
          same_stored_result_recognized_current_after_fix=True,exact_UUID_one_immutable_run=True,
          actual_CLEAR_retires_old_source_new_UNKNOWN_not_zero=True,no_stock_money_HPP_change=True)

    def source_access():
        install(cur);f=baseline.history.fixture(cur,today);subject,role=baseline.custom_writer(cur)
        p=baseline.payload(cur,f);baseline.save(cur,p,subject=subject);q=baseline.history.query(today)
        one=capture(cur,q,subject=subject);assert one['source_state']=='UNCHANGED';frozen=stored(cur,one['run_id'])
        p['expected_revision']='1';p['config']['daily_pcs']='20';baseline.save(cur,p,subject=subject)
        assert read(cur,one['run_id'],subject)['source_state']=='ARCHIVED_STALE'
        two=capture(cur,q,subject=subject);assert two['source_state']=='UNCHANGED'
        baseline.history.sales.fg.post_sale(cur,f['draft'])
        assert read(cur,two['run_id'],subject)['source_state']=='ARCHIVED_STALE'
        current=capture(cur,q,subject=subject);assert current['source_state']=='UNCHANGED'
        assert baseline.row(current,f)['target']['target_pcs']=='200'
        other,_=baseline.auth.custom_actor(cur)
        assert plan.refusal(cur,lambda:read(cur,one['run_id'],other))[1]=='CP7_BASELINE_RUN_UNAVAILABLE'
        plan.b.api.admin(cur);cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(role,))
        assert plan.refusal(cur,lambda:read(cur,current['run_id'],subject))[0]=='42501'
        assert plan.refusal(cur,lambda:capture(cur,q,current['request_id'],subject))[0]=='42501'
        assert stored(cur,one['run_id'])==frozen
        return dict(status='PASS',actual_profile_revision_and_posted_SALE_retire_source=True,
          fresh_capture_current=True,manual_target200_preserved=True,current_permission_before_read_replay=True,
          foreign_actor_refused=True,immutable_history_preserved=True,actual_Auth_HTTP_credit=False)

    return list(zip(IDS['native'],(catalog,lifecycle,source_access)))


def races(tools,today):return []
def http_cases(http,today):return []
