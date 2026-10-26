"""Real Native documents and the actual capture-owned retention tick.

Only ageing a finished job is synthetic; no document or reference is inserted
by SQL. No delivery, production cron or real Auth HTTP claim is made here.
"""
from datetime import timedelta
from copy import deepcopy
from decimal import Decimal
from time import monotonic
import uuid
import cp7_k2_retention_cases as retention
import cp7_p19_reminder_v2_cases as reminder
from cp7_current_choice_preparation import retention_access


def tick(cur,plan,observed):
    plan.b.api.admin(cur);prior=cur.execute('show statement_timeout').fetchone()[0]
    cur.execute("set local statement_timeout='8s'")
    try:
        started=monotonic();result=cur.execute('select cp7_ops.retention_tick()').fetchone()[0]
        elapsed=round((monotonic()-started)*1000,3)
        assert elapsed<8000,('RETENTION_TICK_OVER8S',elapsed)
        observed.setdefault('retention_tick_millis',[]).append(elapsed)
        return result
    finally:
        if cur.connection.info.transaction_status.name!='INERROR':
            cur.execute("select set_config('statement_timeout',%s,true)",(prior,))


def reviewed_capture(cur,today,observed,plan,native,actor):
    """Review the same calendar against v2 work identity through the public CAS.

    The legacy fixture's calendar has a legacy source hash. A request-only
    snapshot supplies the v2 review identity; no units are driven for that job.
    Saving the review makes its old snapshot stale, so exactly one subsequent
    full capture supplies the actual plan/reminder documents.
    """
    plan.b.api.admin(cur)
    legacy=cur.execute('select revision,source_hash,config from cp7_schedule_native.plans order by revision desc limit 1').fetchone()
    physical=plan.monetary_state(cur);key=str(uuid.uuid4())
    initial=native.request(cur,plan.staged.query(today),key,actor,observed)
    plan.staged.checked(initial,key,'RUNNING');assert initial['units_done']==0
    work=native.bounded.work
    before=work.get(cur,key,actor)
    assert before['bounded_request_contract']=='cp7.bounded-analysis-request.v2'
    assert before['source_state']=='UNCHANGED'and before['plan_state']=='SOURCE_CHANGED',before
    assert before['source_hash']!=legacy[1]and before['revision']==str(legacy[0])
    payload=dict(source_run=before['source_run'],source_hash=before['source_hash'],
        expected_revision=before['revision'],config=deepcopy(legacy[2]),
        reason='Retention qualification: review unchanged calendar against the exact frozen v2 source',
        staged_review_contract='cp7.schedule-staged-review.v1')
    request=str(uuid.uuid4());saved=work.save(cur,payload,request,actor)
    assert saved['bounded_request_contract']=='cp7.bounded-analysis-request.v2'
    assert saved['quality']=='SELECTED_ASSUMPTIONS'and saved['source_hash']==before['source_hash']
    assert saved['revision']==str(legacy[0]+1)and work.save(cur,payload,request,actor)==saved
    assert work.get(cur,key,actor)['source_state']=='ARCHIVED_STALE'
    plan.b.api.admin(cur)
    selected=cur.execute('select revision,source_hash,config from cp7_schedule_native.plans order by revision desc limit 1').fetchone()
    assert selected==(legacy[0]+1,before['source_hash'],legacy[2]),selected
    assert plan.monetary_state(cur)==physical
    f=native.capture(cur,today,actor,observed)
    current=work.get(cur,f['key'],actor)
    assert current['source_state']=='UNCHANGED'and current['plan_state']=='SELECTED_ASSUMPTIONS',current
    assert current['source_hash']==saved['source_hash']and current['revision']==saved['revision']
    assert plan.staged.job_row(cur,key,actor)['units_done']==0
    witness=dict(request_only_review_job=key,full_capture_job=f['key'],
        legacy_source_hash=legacy[1],reviewed_v2_source_hash=saved['source_hash'],
        revision_before=str(legacy[0]),revision_after=saved['revision'],
        unchanged_calendar_config=True,public_review_CAS_and_UUID_replay=True,
        old_review_snapshot_stale=True,fresh_capture_current=True,
        review_job_units_executed=0,full_captures=1,no_money_stock_HPP_change=True)
    observed['retention_schedule_review']=witness
    return f,witness


def documents(cur,today,observed,plan,native):
    x=plan.fixture(cur,today);actor=native.native.policy.master.role_actor(cur,'OWNER')
    f,review=reviewed_capture(cur,today,observed,plan,native,actor)
    run=f['done']['run_id'];job=f['row']['id']
    options,_,payload=plan.draft_payload(cur,x,run,actor)
    plan.b.api.admin(cur)
    scope=cur.execute('select scope from cp7_analysis_stage.plan_scope where job_id=%s',(job,)).fetchone()[0]
    assert scope['alloc_status']=='SCENARIO'and scope['capacity']['status']=='SCENARIO',scope
    assert options['production_state']=='ACTIVE'and options['needed_pcs']is not None and options['capacity_pcs']is not None,options
    assert Decimal(options['needed_pcs'])>=2 and Decimal(options['capacity_pcs'])>=2,options
    draft=plan.save(cur,payload,subject=actor)
    ready,calls=reminder.ready_set(cur,run,actor)
    assert ready['state']=='DONE'and calls and max(calls)<8000
    plan.b.api.admin(cur)

    def rows(table,key,value):
        # Table/key are closed constants owned by this qualification.
        return cur.execute('select coalesce(jsonb_agg(to_jsonb(x)order by to_jsonb(x)::text),\'[]\'::jsonb)from '+table+' x where '+key+'=%s',(value,)).fetchone()[0]

    tables=(('cp7_plan_native.drafts','id',draft['draft_id']),
            ('cp7_plan_native.staged_drafts','draft_id',draft['draft_id']),
            ('cp7_reminder_native.staged_condition_sets','run_id',run),
            ('cp7_reminder_native.staged_conditions','run_id',run),
            ('cp7_analysis_stage.pages','run_id',run))
    before_rows={table:rows(table,key,value)for table,key,value in tables}
    assert len(before_rows['cp7_plan_native.staged_drafts'])==len(before_rows['cp7_reminder_native.staged_condition_sets'])==1
    before=retention.counts(cur,job,run);assert before['pages']>0
    money=plan.monetary_state(cur);authority=retention_access.check_permissions(cur)

    def as_role(role,query,args=()):
        assert role in('cp7_capture','anon','authenticated','service_role')
        cur.execute('set local role '+role)
        return cur.execute(query,args).fetchone()

    counted={}
    for table in retention_access.TARGETS:
        plan.b.api.admin(cur)
        counted[table]=as_role('cp7_capture','select count(*)from '+table+' where run_id=%s',(run,))[0]
        assert counted[table]==1
        for statement in ('select *from '+table+' limit 1','update '+table+' set run_id=run_id where run_id=%s'):
            args=(run,)if '%s'in statement else()
            assert plan.refusal(cur,lambda q=statement,a=args:as_role('cp7_capture',q,a))[0]=='42501'
        for role in('anon','authenticated','service_role'):
            assert plan.refusal(cur,lambda r=role:as_role(r,'select run_id from '+table+' limit 1'))[0]=='42501'

    plan.b.api.admin(cur);retention.age(cur,run,timedelta(days=8))
    out=tick(cur,plan,observed)
    mine=[row for row in out['purged']if row['job_id']==str(job)]
    assert len(mine)==1 and mine[0]['documents']=={'plan_v2_drafts':1,'reminder_v2_sets':1}
    assert 'pages'not in mine[0]['removed']
    after=retention.counts(cur,job,run)
    assert all(after[name]==0 for name in retention.TEMPORARY)
    assert all(after[name]==before[name]for name in retention.KEPT+('pages',))
    assert {table:rows(table,key,value)for table,key,value in tables}==before_rows
    assert plan.read(cur,draft['draft_id'],subject=actor)['draft_id']==draft['draft_id']
    plan.refused(cur,lambda:plan.preview(cur,draft['draft_id'],subject=actor),retention.EXPIRED)
    plan.b.api.admin(cur)
    log=rows('cp7_analysis_stage.retention_log','job_id',job);assert len(log)==1
    repeated=tick(cur,plan,observed)
    assert all(row['job_id']!=str(job)for row in repeated['purged'])
    assert rows('cp7_analysis_stage.retention_log','job_id',job)==log
    for statement in ('update cp7_analysis_stage.retention_log set removed=removed where job_id=%s',
                      'delete from cp7_analysis_stage.retention_log where job_id=%s'):
        plan.refused(cur,lambda q=statement:cur.execute(q,(job,)),'CP7_RUN_IMMUTABLE')
    assert plan.monetary_state(cur)==money
    return dict(actual_private_tick=True,synthetic_finished_at_aged_days=8,
        frozen_v2_schedule_review=review,plan_allocation_and_capacity='SCENARIO',
        real_Native_plan_draft=True,real_Native_reminder_conditions=True,
        private_capture_reference_counts=counted,retained_documents=mine[0]['documents'],
        referenced_pages_and_document_contents_exact=True,draft_readable_preview_expired=True,
        expired_temporary_rows_removed=True,retention_log_immutable_and_replay_exact=True,
        payload_and_write_and_browser_SQL_refused=True,authority=authority,
        no_money_stock_HPP_change=True,actual_cron_claim=False,actual_Auth_HTTP_credit=False)
