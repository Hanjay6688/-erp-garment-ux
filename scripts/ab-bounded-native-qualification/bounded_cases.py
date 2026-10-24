"""Six Native controls: real bounded staged DONE, full freshness, no fake SAVE credit."""
from time import monotonic
from datetime import timedelta
import copy
import json
import uuid
import cp7_ab_bounded_stage as stage
import cp7_ow13c_schedule_cases as work
import cp7_k2_retention_cases as retention
from cp7_ow04_restore_bundle import _catalog_rows

plan=work.plan
CONTRACT='cp7.ow13c.bounded-staged-native.v1'
IDS=dict(native=['OW13C_BOUNDED_STAGE_CATALOG22_AND_LEGACY_HASH',
                 'OW13C_BOUNDED_STAGE_LEGACY_AND_CROSS_METHOD_UUID',
                 'OW13C_BOUNDED_STAGE_REAL_DONE_AND_PAGES',
                 'OW13C_BOUNDED_STAGE_DENSE2000_202000_DONE_FRESHNESS',
                 'OW13C_BOUNDED_STAGE_WORK_REVIEW_REPLAY_AND_STALE',
                 'OW13C_BOUNDED_STAGE_CURRENT_ACCESS_K2_AND_USED_INVERSE'])
REQUIRED=dict(native=6)
EXPECTED=DECLARED=6
FUNCTIONS=(*work.FUNCTIONS,'erp_cp7_request_bounded_staged_analysis_v1')
SCHEDULES=work.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}


def request(cur,today,key,subject=None,q=None):
    return plan.staged.limited(cur,'erp_cp7_request_bounded_staged_analysis_v1',
                              (json.dumps(q or plan.staged.query(today)),key),subject)


def prepare(cur,today,subject=None,dense=False):
    x=plan.fixture(cur,today)
    plan.b.api.admin(cur)
    config=copy.deepcopy(cur.execute('select config from cp7_schedule_native.plans order by revision desc limit 1').fetchone()[0])
    size=work.dense.seed(cur) if dense else None
    key=str(uuid.uuid4())
    started=monotonic()
    initial=request(cur,today,key,subject)
    elapsed=(monotonic()-started)*1000
    plan.staged.checked(initial,key,'RUNNING')
    assert initial['units_done']==0 and initial['run_id'] is None
    row=plan.staged.job_row(cur,key,subject)
    c=row['reference']
    assert c['bounded_request_contract']==stage.source.REQUEST and c['bounded_reference_contract']==stage.source.REFERENCE
    assert c['bounded_history_inputs']['coverage']=='COMPLETE' and c['bounded_history_inputs']['raw_native_status_overridden'] is False
    assert c['bounded_history_inputs']['raw_native_capture_status']==c['status']
    assert elapsed<8000,('BOUNDED_REQUEST_OVER8S',elapsed)
    return dict(x=x,key=key,initial=initial,row=row,config=config,size=size,request_millis=round(elapsed,3),subject=subject)


def finish(cur,f):
    done,calls=plan.staged.drive(cur,f['key'],f['subject'])
    assert done['state']=='DONE',dict(done=done,call_count=len(calls),last_calls=calls[-4:])
    assert all(c['ms']<8000 for c in calls),max(c['ms'] for c in calls)
    original,pages,meta=plan.staged.fetch(cur,done['run_id'],f['subject'])
    row=plan.staged.job_row(cur,f['key'],f['subject'])
    assert row['state']=='DONE' and row['reference']==f['row']['reference']
    assert done['units_done']==done['unit_count'] and done['reference']==f['initial']['reference']
    assert pages['targets_total']==len(row['reference']['facts']['products'])
    assert original['analysis']['snapshot']['capture_complete'] is True
    assert original['analysis']['quality']['quantity']=='COMPLETE'
    assert original['analysis']['financial_readiness']=='BLOCKED' and original['financial_source'] is None
    f.update(done=done,calls=calls,original=original,pages=pages,page_meta=meta)
    return f


def work_payload(cur,f):
    w=work.get(cur,f['key'],f['subject'])
    assert w['contract_version']=='cp7.planning-schedule-staged-bounded.v1'
    assert w['source_state']=='UNCHANGED' and w['history_input_coverage']=='COMPLETE'
    return w,dict(source_run=w['source_run'],source_hash=w['source_hash'],expected_revision=w['revision'],
                  config=f['config'],reason='Explicit bounded-reference Native work review; no physical or monetary write',
                  staged_review_contract='cp7.schedule-staged-review.v1')


def cases(cur,today):
    def catalog():
        v=stage.verify(cur,STAGE_STATE)
        assert (v['private_functions'],v['public_rpcs'],v['existing_function_replacements'],v['new_tables'])==(13,1,7,0)
        plan.fixture(cur,today)
        plan.b.api.admin(cur)
        c=cur.execute('select cp7_schedule_staged_review.current_source()').fetchone()[0]
        old,new=cur.execute('select cp7_bounded_analysis_stage.native_work_fingerprint(%s::jsonb),cp7_supply_native.fingerprint(%s::jsonb)',
                            (json.dumps(c),json.dumps(c))).fetchone()
        assert old==new and len(_catalog_rows(cur))==22
        return dict(status='PASS',explicit_seven_replacements_preserve_owners_and_ACLs=True,
                    legacy_work_fingerprint_exact=True,new_public_request_authenticated_only=True)

    def legacy():
        f=work.prepare(cur,today)
        auto=plan.staged.limited(cur,'erp_cp7_request_staged_analysis_v1',(json.dumps(dict(initial_auto='STATUS')),None))
        assert auto['contract_version']=='cp7.initial-analysis.v1'
        plan.refused(cur,lambda:request(cur,today,str(uuid.uuid4()),q=dict(initial_auto='ENSURE')),'CP7_WIP_FIELDS')
        out=work.save(cur,f['payload'])
        assert out['contract_version']=='cp7.planning-schedule-staged-outcome.v1'
        assert 'bounded_request_contract' not in out
        plan.refused(cur,lambda:request(cur,today,f['request']),'CP7_ANALYSIS_REQUEST_CHANGED')
        key=str(uuid.uuid4())
        one=request(cur,today,key)
        assert request(cur,today,key)==one
        plan.refused(cur,lambda:plan.staged.request(cur,today,key),'CP7_ANALYSIS_REQUEST_CHANGED')
        q=plan.staged.query(today)
        q=dict(q,group_mode='RESTATED' if q['group_mode']=='AS_SOLD' else 'AS_SOLD')
        plan.refused(cur,lambda:request(cur,today,key,q=q),'CP7_ANALYSIS_REQUEST_CHANGED')
        return dict(status='PASS',legacy_work_response_and_SAVE_contract_exact=True,
                    actual_old_initial_auto_dispatch_preserved=True,new_route_cannot_enter_initial_auto=True,
                    exact_new_method_request_replay=True,both_cross_method_UUID_routes_refused=True,changed_query_refused=True)

    def done():
        f=prepare(cur,today)
        physical=plan.monetary_state(cur)
        finish(cur,f)
        assert f['row']['reference']['status']=='COMPLETE'
        assert plan.monetary_state(cur)==physical
        assert plan.staged.limited(cur,'erp_cp7_check_staged_analysis_source_v1',(f['done']['run_id'],))['source_state']=='UNCHANGED'
        return dict(status='PASS',real_Native_request_step_DONE_header_and_all_pages=True,
                    immutable_reference_and_real_units_retained=True,request_millis=f['request_millis'],
                    step_count=len(f['calls']),slowest_step_millis=max(c['ms'] for c in f['calls']),**f['page_meta'],
                    financial_deferred_and_genuine_unknowns_preserved=True,no_physical_stock_money_HPP_write=True)

    def dense():
        f=prepare(cur,today,dense=True)
        c=f['row']['reference']
        assert c['status']=='INCOMPLETE' and c['stock_raw_omitted'] is True
        assert int(c['bounded_stock_reference']['row_count'])>=202000
        physical=plan.monetary_state(cur)
        finish(cur,f)
        assert 'RAW_NATIVE_CAPTURE_INCOMPLETE_COMPLETE_SQL_HISTORY_INPUTS' in f['original']['analysis']['generation_warnings']
        times=[]
        for _ in range(3):
            started=monotonic()
            checked=plan.staged.limited(cur,'erp_cp7_check_staged_analysis_source_v1',(f['done']['run_id'],))
            elapsed=(monotonic()-started)*1000
            assert checked['source_state']=='UNCHANGED' and elapsed<8000,(checked,elapsed)
            times.append(round(elapsed,3))
        assert plan.monetary_state(cur)==physical
        plan.found_fg(cur,f['x'],'1')
        before=work.metadata(cur)
        stale=plan.staged.limited(cur,'erp_cp7_check_staged_analysis_source_v1',(f['done']['run_id'],))
        assert stale['source_state']=='ARCHIVED_STALE'
        assert work.get(cur,f['key'])['source_state']=='ARCHIVED_STALE'
        assert work.metadata(cur)==before
        return dict(status='PASS',**f['size'],actual_products=len(c['facts']['products']),
                    raw_native_capture_remains_INCOMPLETE=True,real_Native_bounded_staged_DONE=True,
                    full_raw_stock_digest_rows=int(c['bounded_stock_reference']['row_count']),request_millis=f['request_millis'],
                    step_count=len(f['calls']),slowest_step_millis=max(c['ms'] for c in f['calls']),
                    full_source_check_millis=times,statement_limit='8s',wall_limit_ms=8000,**f['page_meta'],
                    actual_Native_stock_change_stales_job_and_work=True,no_ERP_write_by_analysis_or_freshness=True,
                    actual_checked_SAVE2000_qualified=False)

    def review():
        f=prepare(cur,today)
        w,p=work_payload(cur,f)
        physical=plan.monetary_state(cur)
        key=str(uuid.uuid4())
        result=work.save(cur,p,key)
        assert result['contract_version']=='cp7.planning-schedule-staged-bounded-outcome.v1'
        assert result['bounded_request_contract']==stage.source.REQUEST and work.save(cur,p,key)==result
        assert work.get(cur,f['key'])['source_state']=='ARCHIVED_STALE' # Its actual calendar changed.
        fresh=str(uuid.uuid4())
        request(cur,today,fresh)
        assert work.get(cur,fresh)['source_state']=='UNCHANGED'
        plan.found_fg(cur,f['x'],'1')
        before=work.metadata(cur)
        fresh_work=work.get(cur,fresh)
        p.update(source_run=fresh_work['source_run'],source_hash=fresh_work['source_hash'],expected_revision=result['revision'])
        plan.refused(cur,lambda:work.save(cur,p),'CP7_SCHEDULE_SOURCE_CHANGED','40001')
        assert work.metadata(cur)==before
        # The only physical change above is the real explicit stock fixture.
        assert physical!=plan.monetary_state(cur)
        return dict(status='PASS',new_response_variant_explicit=True,exact_SAVE_UUID_replay=True,
                    own_calendar_write_stales_old_analysis_new_capture_current=True,actual_stock_change_SAVE_refused40001=True,
                    no_refused_command_or_plan_or_ERP_effect=True)

    def access_used():
        actor=work.base.retained.master.role_actor(cur,'OWNER')
        f=prepare(cur,today,subject=actor)
        stranger=work.base.retained.master.role_actor(cur,'OWNER')
        plan.refused(cur,lambda:work.get(cur,f['key'],stranger),'CP7_SCHEDULE_STAGED_RUN_UNAVAILABLE','42501')
        plan.b.api.admin(cur)
        before=_catalog_rows(cur)
        try:
            stage.rollback_preuse(cur,STAGE_STATE)
        except ValueError as e:
            assert str(e)=='BOUNDED_ANALYSIS_AFTER_USE_REQUIRES_BACKUP_RESTORE'
        else:
            raise AssertionError('BOUNDED_USED_INVERSE_ALLOWED')
        assert _catalog_rows(cur)==before
        # Real completed job, then the existing K2 finish clock is moved by
        # the established expiration fixture; no source status is promoted.
        finish(cur,f)
        plan.b.api.admin(cur)
        retention.age(cur,f['done']['run_id'],timedelta(days=8))
        plan.refused(cur,lambda:work.get(cur,f['key'],actor),retention.EXPIRED)
        plan.refused(cur,lambda:plan.staged.limited(cur,'erp_cp7_check_staged_analysis_source_v1',(f['done']['run_id'],),actor),retention.EXPIRED)
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(actor,))
        assert plan.refusal(cur,lambda:request(cur,today,f['key'],actor))[0]=='42501'
        return dict(status='PASS',actual_new_job_blocks_inverse_before_any_DDL=True,
                    foreign_actor_denied=True,current_deactivated_request_denied=True,actual_DONE_K2_work_and_source_readers_refuse=True)

    return list(zip(IDS['native'],[catalog,legacy,done,dense,review,access_used]))
