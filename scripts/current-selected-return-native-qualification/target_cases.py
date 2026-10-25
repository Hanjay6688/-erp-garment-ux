"""Five B selected-return business cases with explicit full-A setup/used inverse.

Original B source stays untouched. Only three rollback calls and their named
full-composition refusal change. The six-case B catalog anchor is excluded;
the complete A catalog inverse is exercised by the outer Native qualifier.
"""
from time import monotonic
import json,uuid
import cp7_model_target_consumer_stage as stage
import cp7_ow11_baseline_freshness_cases as fresh
import cp7_ow11_model_evaluation_v2_cases as model
import cp7_ow11_model_target_consumer_cases as original
import cp7_current_selected_return_installation as product
import cp7_p21_current_chain_rehearsal_probe as chain
plan,baseline,bounded,policy=fresh.plan,fresh.baseline,fresh.bounded,model.policy
IDS=tuple(original.IDS['native'][1:])
STATE=CHECKER=None
SETUP_ADMISSIONS=[]


def install(cur):
    assert STATE is not None and callable(CHECKER)
    plan.b.api.admin(cur)
    proof=CHECKER(cur)
    SETUP_ADMISSIONS.append(dict(stage='FULL_SELECTED_RETURN',actual_full_current_verification=proof))
    return dict(current=STATE)


def rollback_full(cur,state):
    assert state is STATE
    with chain.helper.control.product_catalog(cur):
        return product.rollback_preuse(cur,state)


def call(cur,name,args,subject=None):
    start=monotonic();r=plan.rpc(cur,name,args,subject)
    ms=(monotonic()-start)*1000;assert ms<8000,('MODEL_TARGET_OVER8S',name,ms)
    return r

def capture(cur,q,key=None,subject=None):return call(cur,'erp_cp7_capture_baseline_v1',(json.dumps(q),key or uuid.uuid4()),subject)

def read(cur,run,subject=None):return call(cur,'erp_cp7_read_baseline_v1',(run,),subject)


def cases(cur,today):

    def replay():
        s=install(cur);f=baseline.history.fixture(cur,today);p=baseline.payload(cur,f);baseline.save(cur,p)
        q=baseline.history.query(today);key=uuid.uuid4();physical=plan.monetary_state(cur)
        before_job=stage.usage_state(cur);cur.execute('savepoint model_target_queued_usage')
        try:
            queued=call(cur,'erp_cp7_request_operational_analysis_job_v1',(json.dumps(q),uuid.uuid4()))
            assert queued['state']=='WAITING'and queued['run_id']is None
            after_job=stage.usage_state(cur)
            assert [name for name in after_job if after_job[name]!=before_job.get(name)]==['cp7_analysis_jobs.jobs']
            try:rollback_full(cur,s['current'])
            except ValueError as e:assert str(e)=='CURRENT_SELECTED_RETURN_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
            else:raise AssertionError('MODEL_TARGET_QUEUED_JOB_AFTER_USE_INVERSE_ALLOWED')
        finally:
            cur.execute('rollback to savepoint model_target_queued_usage');cur.execute('release savepoint model_target_queued_usage')
        assert stage.usage_state(cur)==before_job
        # A raw operational capture persists no staged job/baseline/history run.
        # That sole immutable analysis run must still make pre-use removal fail.
        before_raw=stage.usage_state(cur);raw_key=uuid.uuid4()
        raw=call(cur,'erp_cp7_capture_operational_analysis_v1',(json.dumps(q),raw_key))
        after_raw=stage.usage_state(cur)
        assert [name for name in after_raw if after_raw[name]!=before_raw.get(name)]==['cp7_analysis_native.runs']
        assert raw['analysis']['versions']['models']=='policy-gated-dated-model-target-1'
        assert raw['source_state']=='UNCHANGED'and raw['production_go']is False
        raw_frozen=cur.execute('select to_jsonb(r)from cp7_analysis_native.runs r where id=%s',(raw['run_id'],)).fetchone()[0]
        try:rollback_full(cur,s['current'])
        except ValueError as e:assert str(e)=='CURRENT_SELECTED_RETURN_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
        else:raise AssertionError('MODEL_TARGET_RAW_REPORT_AFTER_USE_INVERSE_ALLOWED')
        assert call(cur,'erp_cp7_capture_operational_analysis_v1',(json.dumps(q),raw_key))==raw
        assert cur.execute('select to_jsonb(r)from cp7_analysis_native.runs r where id=%s',(raw['run_id'],)).fetchone()[0]==raw_frozen
        one=capture(cur,q,key);frozen=fresh.stored(cur,one['run_id'])
        assert one['contract_version']=='cp7.native-baseline.v3'and one['source_state']=='UNCHANGED'
        r=baseline.row(one,f);assert r['target']['target_pcs']=='100'
        assert r['model_resolution']['state']=='BASELINE_RETAINED'and r['model_resolution']['forecast_applied']is False
        assert r['model_resolution']['baseline_target']==r['target']and r['demand_provenance']['contract_version']=='cp7.target-demand-provenance.v2'
        assert capture(cur,q,key)==one and read(cur,one['run_id'])==one
        assert plan.refusal(cur,lambda:capture(cur,dict(q,group_mode='RESTATED'),key))[1]=='CP7_BASELINE_REQUEST_CHANGED'
        assert fresh.stored(cur,one['run_id'])==frozen and plan.monetary_state(cur)==physical
        try:rollback_full(cur,s['current'])
        except ValueError as e:assert str(e)=='CURRENT_SELECTED_RETURN_AFTER_USE_REQUIRES_FULL_BACKUP_RESTORE'
        else:raise AssertionError('MODEL_TARGET_USED_INVERSE_ALLOWED')
        return dict(status='PASS',actual_Native_v3_baseline100_current=True,exact_UUID_replay_and_immutable_result=True,
          actual_raw_operational_capture_replay_immutable=True,raw_report_alone_blocks_preuse_inverse=True,
          actual_queued_job_without_run_alone_blocks_preuse_inverse=True,
          no_model_fabricated=True,no_stock_money_HPP_change=True,after_use_requires_composed_restore=True)

    def current_policy():
        install(cur);subject=policy.master.role_actor(cur,'OWNER')
        f,h,mq=model.legacy.prepared(cur,today,12,subject)
        # Use the actual captured history query; no historical row/policy edits.
        plan.b.api.admin(cur);q=cur.execute('select query from cp7_planning.history_runs where id=%s',(h['run_id'],)).fetchone()[0]
        one=model.capture(cur,mq,subject);frozen=model.stored(cur,one['run_id'])
        b1=capture(cur,q,subject=subject);br1=next(x for x in b1['rows']if x['target_key']==mq['target_key'])
        assert br1['model_resolution']['run_id']==one['run_id']and br1['model_resolution']['forecast_applied']is False
        policy.save(cur,policy.payload(cur,subject),subject)
        assert read(cur,b1['run_id'],subject)['source_state']=='ARCHIVED_STALE'
        newer=model.capture(cur,mq,subject);b2=capture(cur,q,subject=subject)
        br2=next(x for x in b2['rows']if x['target_key']==mq['target_key'])
        assert br2['model_resolution']['run_id']==newer['run_id']and newer['run_id']!=one['run_id']
        assert br2['model_resolution']['forecast_applied']is False and br2['model_resolution']['forecast']is None
        assert model.stored(cur,one['run_id'])==frozen and b1['source_hash']!=b2['source_hash']
        assert read(cur,b1['run_id'],subject)['rows']==b1['rows']
        return dict(status='PASS',actual_policy_clock_and_latest_own_v2_selection=True,no_posthoc_model_promotion=True,
          old_baseline_stale_but_immutable=True,old_v2_result_immutable=True,actual_historical_positive_winner=False)

    def source_access():
        install(cur);f=baseline.history.fixture(cur,today);subject,role=baseline.custom_writer(cur)
        p=baseline.payload(cur,f);baseline.save(cur,p,subject=subject);q=baseline.history.query(today)
        old=capture(cur,q,subject=subject);frozen=fresh.stored(cur,old['run_id'])
        p['expected_revision']='1';p['config']['daily_pcs']='20';baseline.save(cur,p,subject=subject)
        assert read(cur,old['run_id'],subject)['source_state']=='ARCHIVED_STALE'
        two=capture(cur,q,subject=subject);assert baseline.row(two,f)['target']['target_pcs']=='200'
        baseline.history.sales.fg.post_sale(cur,f['draft']);assert read(cur,two['run_id'],subject)['source_state']=='ARCHIVED_STALE'
        new=capture(cur,q,subject=subject);assert new['source_state']=='UNCHANGED'
        other,_=baseline.auth.custom_actor(cur);assert plan.refusal(cur,lambda:read(cur,old['run_id'],other))[1]=='CP7_BASELINE_RUN_UNAVAILABLE'
        plan.b.api.admin(cur);cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(role,))
        assert plan.refusal(cur,lambda:read(cur,new['run_id'],subject))[0]=='42501'
        assert plan.refusal(cur,lambda:capture(cur,q,new['request_id'],subject))[0]=='42501'
        assert fresh.stored(cur,old['run_id'])==frozen
        return dict(status='PASS',actual_profile_and_posted_SALE_retire_source=True,manual_target200_retained=True,
          current_access_before_read_replay=True,foreign_actor_refused=True,old_history_immutable=True)

    def warehouse():
        install(cur);f=baseline.history.fixture(cur,today);baseline.save(cur,baseline.payload(cur,f))
        call(cur,'erp_cp7_refresh_fg_reorder_v1',())
        subject,role=baseline.custom_writer(cur);plan.b.api.admin(cur)
        cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
        cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'warehouse.fg.view')",(role,))
        # The factory already has more than one page of products. Bind the
        # actual Native fixture SKU instead of assuming it sorts in page one.
        sku=cur.execute('select sku from erp.products where id=%s',(f['product'],)).fetchone()[0]
        query=dict(q=sku,filter='ALL',offset=0,limit=100)
        refused=plan.refusal(cur,lambda:call(cur,'erp_cp7_get_fg_reorder_v1',(json.dumps(query),),subject))
        assert refused==('40001','CP7_MODEL_TARGET_REORDER_REFRESH_REQUIRED',None),refused
        # Workspace reads the committed evaluation cache; it does not refresh
        # after a newly posted product/profile. Exercise the actual refresh as
        # the FG-only actor before reading, not a private/admin seed.
        refreshed=call(cur,'erp_cp7_refresh_fg_reorder_v1',(),subject)
        assert refreshed['items']>0
        w=call(cur,'erp_cp7_get_fg_reorder_v1',(json.dumps(query),),subject)
        found=[x for x in w['page']['rows']if x['root_id']==str(f['product'])]
        assert len(found)==1,('MODEL_TARGET_FG_FIXTURE_LOOKUP',sku,w['page'])
        r=found[0]
        m=r['projection']['target_demand']['model']
        assert r['projection']['contract_version']=='cp7.fg-reorder-projection.v3'
        assert r['projection']['target_pcs']=='100'and r['formula_point']=='30'
        assert m['state']=='BASELINE_RETAINED'and m['forecast']is None and m['run_id']is None and m['policy_source']is None
        assert plan.refusal(cur,lambda:capture(cur,baseline.history.query(today),subject=subject))[0]=='42501'
        plan.b.api.admin(cur);cur.execute('delete from erp.app_role_permissions where role_id=%s',(role,))
        assert plan.refusal(cur,lambda:call(cur,'erp_cp7_get_fg_reorder_v1',(json.dumps(query),),subject))[0]=='42501'
        return dict(status='PASS',actual_existing_FG_only_permission=True,actual_FG_only_refresh_then_cached_read=True,baseline_target100_point30_preserved=True,
          no_model_policy_history_disclosed=True,strict_model_and_revoked_FG_denied=True,actual_Auth_HTTP_credit=False)

    def bounded_analog():
        install(cur);f=fresh.consumer.prepare(cur,today);p=fresh.consumer.payload(f);fresh.choice.save(cur,p)
        new=fresh.consumer.fresh(cur,today,f);a=fresh.consumer.row(new);b=fresh.consumer.staged_row(cur,new)
        assert a['target']==b['target']and a['demand_provenance']==b['demand_provenance']
        assert a['demand_provenance']['basis']==fresh.consumer.BASIS
        assert a['model_resolution']['state']=='BASELINE_RETAINED'and a['model_resolution']['forecast_applied']is False
        assert a['target']['target_pcs']is not None
        direct=capture(cur,new['row']['query']);d=next(x for x in direct['rows']if x['target_key']==f['target'])
        assert direct['source_state']=='UNCHANGED'and d['target']['target_pcs']==a['target']['target_pcs']
        assert d['demand_provenance']['daily_total_pcs']==a['demand_provenance']['daily_total_pcs']
        return dict(status='PASS',actual_bounded_and_staged_analog_target_parity=True,direct_same_target_and_history_operands=True,
          analog_not_silently_promoted_to_model=True,actual_positive_model_target=False)

    return list(zip(IDS,(replay,current_policy,source_access,warehouse,bounded_analog)))
