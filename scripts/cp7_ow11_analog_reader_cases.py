"""Native advisory facade controls; no Auth HTTP, selection or forecast credit."""
from datetime import timedelta
from decimal import Decimal
from time import monotonic
import json
import uuid
import cp7_product_analog_reader_stage as stage
import cp7_ow11_analog_candidates_cases as private
from cp7_ow04_restore_bundle import _catalog_rows

bounded,volume,plan=private.bounded,private.volume,private.plan
CONTRACT='cp7.ow11.analog-reader-native.v1'
IDS=dict(native=['OW11_ANALOG_READER_CATALOG22_INVERSE_AND_EXTERNAL_CALLER',
                 'OW11_ANALOG_READER_DONE_BINDING_CLEANUP_AND_STALE_ADVISORY',
                 'OW11_ANALOG_READER_CURRENT_ACTOR_EPOCH_K2_AND_RUNNING',
                 'OW11_ANALOG_READER_NATIVE_IMPORT_PHYSICAL_SIZE_AND_AVAILABLE_ZERO'])
REQUIRED=dict(native=4)
EXPECTED=DECLARED=4
FUNCTIONS=(*private.FUNCTIONS,'erp_cp7_read_product_analog_candidates_v1')
SCHEDULES=private.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
RPC='erp_cp7_read_product_analog_candidates_v1'
PARENT_CHECKER=None


def install(cur):
    plan.b.api.admin(cur)
    before=_catalog_rows(cur)
    state=stage.install_delta(cur,PARENT_CHECKER)
    return before,state


def remove(cur,before,state):
    plan.b.api.admin(cur)
    stage.rollback_readonly(cur,state)
    assert _catalog_rows(cur)==before,'ANALOG_READER_CATALOG22_NOT_RESTORED'


def call(cur,f,target=None,access=None,subject=None,offset=0):
    start=monotonic()
    value=plan.rpc(cur,RPC,(f['key'],target or f['x']['target'],offset,50,
                            f['pages']['access_epoch']if access is None else access),subject or f.get('subject'))
    elapsed=(monotonic()-start)*1000
    assert elapsed<8000,('ANALOG_READER_OVER8S',elapsed)
    return value,round(elapsed,3)


def explicit_profile(cur,root,minimum='1'):
    row=volume.baseline.get(cur,[root])['rows'][0]
    config=dict(volume.SYNTHETIC['profile']);config['minimum_available_days']=minimum
    volume.baseline.save(cur,dict(root_id=root,product_version_id=row['product_version_id'],expected_revision=row['revision'],
                                 config=config,reason='Explicit SYNTHETIC analog reader minimum; not factory policy'))


def from_current(cur,today,x,subject=None):
    key=str(uuid.uuid4());initial=bounded.request(cur,today,key,subject)
    row=plan.staged.job_row(cur,key,subject)
    return dict(x=x,key=key,initial=initial,row=row,subject=subject)


def epoch(cur,subject):
    plan.staged.auth.actor(cur,subject)
    value=cur.execute("select encode(pg_catalog.sha256(convert_to(cp7_schedule_native.access_now(false)::text,'UTF8')),'hex')").fetchone()[0]
    plan.b.api.admin(cur)
    return value


def cases(cur,today):
    def catalog():
        before,state=install(cur)
        v=stage.verify(cur,state)
        assert(v['private_functions'],v['public_rpcs'],v['new_tables'],v['old_replacements'])==(2,1,0,0)
        def anonymous():
            plan.b.api.admin(cur)
            cur.execute('set local role anon')
            cur.execute('select public.'+RPC+'(%s,%s,0,50,%s)',(uuid.uuid4(),'missing','0'*64))
        assert plan.refusal(cur,anonymous)[0]=='42501'
        snapshot=_catalog_rows(cur)
        cur.execute("create function public.ow11_analog_external_guard()returns jsonb language sql set search_path=''as $$select cp7_product_analog_stage.candidates(null,null,0,1)$$")
        with_external=_catalog_rows(cur)
        try:stage.rollback_readonly(cur,state)
        except ValueError as e:assert str(e)=='PRODUCT_ANALOG_READER_EXTERNAL_CALLER_REQUIRES_COMPOSED_RESTORE',str(e)
        else:raise AssertionError('ANALOG_READER_EXTERNAL_INVERSE_ALLOWED')
        assert _catalog_rows(cur)==with_external
        cur.execute('drop function public.ow11_analog_external_guard()restrict')
        assert _catalog_rows(cur)==snapshot
        remove(cur,before,state)
        return dict(status='PASS',source_sha256=stage.verify_sources(),kernel_manifest=stage.kernel.verify_sources(),
                    private2_public1_tables0_replacements0=True,source_body_owner_ACL_GUC_exact=True,
                    anonymous_SQL_denied=True,external_caller_blocks_inverse_before_DDL=True,
                    exact_catalog22_inverse=True,actual_Auth_HTTP_credit=False)

    def binding():
        before,state=install(cur)
        f=bounded.prepare(cur,today);bounded.finish(cur,f)
        physical=plan.monetary_state(cur)
        one,elapsed=call(cur,f)
        assert one['contract_version']=='cp7.product-analog-candidates-read.v1'
        assert one['request_id']==f['key']and one['run_id']==f['done']['run_id']
        assert one['identity_hash']==f['pages']['identity_hash']and one['access_epoch']==f['pages']['access_epoch']
        assert one['reference']==f['pages']['reference']and one['query']==f['row']['query']
        assert one['producer_hash']==f['row']['reference']['bounded_producer_hash']
        assert one['source_state']=='CAPTURED_NOT_CHECKED'and one['captured_source_only']is True
        assert not one['selected']and not one['reviewed']and not one['forecast_applied']
        assert call(cur,f)[0]==one
        plan.b.api.admin(cur)
        cleaned=cur.execute('select cp7_analysis_stage.clean_done(%s)',(f['row']['id'],)).fetchone()[0]
        assert cleaned['state']=='CLEANED'
        assert call(cur,f)[0]==one
        assert plan.monetary_state(cur)==physical
        plan.found_fg(cur,f['x'],'1')
        assert plan.staged.limited(cur,'erp_cp7_check_staged_analysis_source_v1',(f['done']['run_id'],))['source_state']=='ARCHIVED_STALE'
        assert call(cur,f)[0]==one # Still an explicitly captured advisory, never UNCHANGED.
        remove(cur,before,state)
        return dict(status='PASS',real_DONE_request_run_query_reference_identity_epoch_producer_bound=True,
                    exact_repeated_read=True,actual_K3_cleanup_retains_candidate_context=True,
                    actual_Native_stock_change_stales_source_but_reader_stays_explicitly_captured=True,
                    no_candidate_reader_ERP_write=True,read_millis=elapsed,statement_limit='8s',
                    selected=False,reviewed=False,forecast_applied=False)

    def access():
        before,state=install(cur)
        actor=bounded.work.base.retained.master.role_actor(cur,'OWNER')
        stranger=bounded.work.base.retained.master.role_actor(cur,'OWNER')
        f=bounded.prepare(cur,today,subject=actor)
        f['pages']=dict(access_epoch=epoch(cur,actor))
        plan.refused(cur,lambda:call(cur,f),'CP7_PRODUCT_ANALOG_RUN_UNAVAILABLE','42501')
        bounded.finish(cur,f)
        call(cur,f)
        plan.refused(cur,lambda:call(cur,f,access='0'*64),'CP7_ANALYSIS_ACCESS_CHANGED','42501')
        foreign_epoch=epoch(cur,stranger)
        plan.refused(cur,lambda:call(cur,f,access=foreign_epoch,subject=stranger),'CP7_PRODUCT_ANALOG_RUN_UNAVAILABLE','42501')
        plan.b.api.admin(cur)
        bounded.retention.age(cur,f['done']['run_id'],timedelta(days=8))
        plan.refused(cur,lambda:call(cur,f),bounded.retention.EXPIRED)
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(actor,))
        assert plan.refusal(cur,lambda:call(cur,f))[0]=='42501'
        remove(cur,before,state)
        return dict(status='PASS',running_job_refused=True,foreign_actor_with_own_current_epoch_refused=True,
                    wrong_epoch_refused=True,actual_K2_expired_refused=True,current_deactivated_actor_refused=True,
                    actual_Auth_HTTP_credit=False,concurrency_test=False)

    def sizes():
        before,state=install(cur)
        x=plan.fixture(cur,today)
        imported=volume.import_batch(cur,today,11,volume.Phases())
        target=imported[0]['target'];same=[p for p in imported[1:]if p['target'].split(':')[1]==target.split(':')[1]]
        other=[p for p in imported if p['target'].split(':')[1]!=target.split(':')[1]]
        assert len(same)==1 and len(other)==9
        explicit_profile(cur,imported[0]['root'])
        f=from_current(cur,today,x);bounded.finish(cur,f)
        physical=plan.monetary_state(cur)
        value,elapsed=call(cur,f,target)
        result=value['result'];assert result['total']==1 and len(result['candidates'])==1,result
        item=result['candidates'][0]
        assert item['target_key']==same[0]['target']and item['size_id']==target.split(':')[1]
        assert int(item['available_days'])==1 and Decimal(item['observed_available_daily_mean'])==0
        assert item['suggested']and 'SAME_CAPTURED_BRAND'in item['reasons']
        history={r['target_key']:r for r in f['row']['reference']['bounded_history_inputs']['inputs']['history']}
        assert all(int(history[p['target']]['available_days'])==1 and Decimal(history[p['target']]['available_sales_mean'])==0 for p in other)
        assert not{p['target']for p in other}&{r['target_key']for r in result['candidates']}
        assert plan.monetary_state(cur)==physical
        remove(cur,before,state)
        return dict(status='PASS',actual_public_BB_import11_products10_physical_sizes=True,
                    actual_same_physical_size_available_zero_candidate=True,
                    nine_other_available_zero_sizes_excluded_despite_same_captured_brand=True,
                    actual_Native_history_not_mutated_or_promoted=True,read_millis=elapsed,
                    selected=False,reviewed=False,forecast_applied=False,full_OW11_acceptance=False)

    return list(zip(IDS['native'],[catalog,binding,access,sizes]))
