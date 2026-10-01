"""Bounded durable review attention, delegated unchanged Native manual writers.

These cases prove saved review metadata and own-user tasks. They do not assert
business episode reconciliation, AR/AP due truth, delivery or family acceptance.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json,threading,time,uuid
import psycopg
import cp7_analysis_cases as parent

auth,b=parent.auth,parent.b
def rpc(cur,name,args,subject=None):return parent.schedule.rpc(cur,name,args,subject)
def get(cur,run,subject=None):return rpc(cur,'erp_cp7_get_analysis_attention_v1',(run,),subject)
def command(cur,p,key=None,subject=None):return rpc(cur,'erp_cp7_save_analysis_attention_v1',(json.dumps(p),key or uuid.uuid4()),subject)
def resolve(cur,p,key,subject=None):return rpc(cur,'erp_cp7_get_analysis_attention_request_v1',(json.dumps(p),key),subject)
def intent(e,action='ACK',row=None,**details):
 row=row or e['rows'][0]
 if row['manual']is not None:details['expected_native_revision']=row['manual']['row_version']
 return dict(run_id=e['analysis']['run_id'],action_key=row['action_key'],action=action,expected_revision=row['attention']['revision'],details=details)
def row_for(e,p):return next(r for r in e['rows']if r['action_key']==p['action_key'])
def prepared(cur,today,custom=False):
 parent.setup(cur,today);subject=auth.custom_actor(cur)[0]if custom else None
 if custom:
  # Delegate to the real Native STAFF policy. A custom four-Ops role is not
  # admitted by Native personal reminders; never broaden that Native guard.
  role=cur.execute("select id from erp.app_roles where role_code='STAFF'").fetchone()[0]
  # Native ships the legacy STAFF role disabled. Activate only this disposable
  # fixture control, exactly as the accepted CP6 internal-role control does.
  cur.execute('update erp.app_roles set is_active=true where id=%s',(role,))
  cur.execute("update erp.app_users set role_id=%s where auth_user_id=%s",(role,subject))
  for permission in auth.PERMS:cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,permission))
 original=parent.capture(cur,today,subject=subject);return original,get(cur,original['run_id'],subject),subject
def manual_save(cur,p,version=None,subject=None):return rpc(cur,'erp_save_my_reminder_v1',(json.dumps(p),uuid.uuid4(),version),subject)
def schedule(cur,e,today,subject=None):return command(cur,intent(e,'SCHEDULE',title='Periksa bahan sumber asli',note='Ditinjau operator',due_at=(today+timedelta(days=2)).isoformat()+'T08:30:00+07:00',priority='NORMAL'),subject=subject)

def cases(cur,today):
 def review():
  original,e,subject=prepared(cur,today);before=b.boundary.snapshot(cur)
  for action in('ACK','DONE','NEW'):
   p=intent(e,action);e=command(cur,p);r=row_for(e,p);assert r['attention']['state']==action and r['business_resolved']is False and r['condition']=='REVIEW_REQUIRED'
  at=cur.execute('select clock_timestamp()').fetchone()[0]+timedelta(days=1);p=intent(e,'SNOOZE',resume_at=at.isoformat());e=command(cur,p)
  assert row_for(e,p)['attention']['state']=='SNOOZED'and not row_for(e,p)['attention']['resume_due']
  assert e['analysis']['analysis']==original['analysis']and e['analysis']['financial_source']==original['financial_source']and b.boundary.snapshot(cur)==before
  return dict(status='PASS',persisted_ACK_DONE_NEW_SNOOZED_metadata_only=True,original_stock_money_HPP_body_unchanged=True,business_never_closed_by_review=True,no_external_delivery=True)
 def lifecycle():
  original,e,subject=prepared(cur,today);e=schedule(cur,e,today);native=e['rows'][0]['manual'];assert native['status']=='OPEN'and native['row_version']=='1'
  stored=cur.execute('select title,status,due_at from erp.manual_reminders where id=%s',(native['id'],)).fetchone();assert stored[0]==native['title']and stored[1]=='OPEN'
  p=intent(e,'DONE');e=command(cur,p);assert row_for(e,p)['manual']['status']=='DONE'and row_for(e,p)['business_resolved']is False
  p=intent(e,'NEW');e=command(cur,p);assert row_for(e,p)['manual']['status']=='OPEN'
  at=cur.execute('select clock_timestamp()').fetchone()[0]+timedelta(days=3);p=intent(e,'SNOOZE',resume_at=at.isoformat());e=command(cur,p);assert row_for(e,p)['manual']['due_at']==row_for(e,p)['attention']['resume_at']
  p=intent(e,'CANCEL_SCHEDULE',reason='Operator mengubah jadwal');e=command(cur,p);assert row_for(e,p)['manual']['status']=='CANCELLED'and row_for(e,p)['attention']['state']=='SNOOZED'
  old=row_for(e,p)['manual']['id'];e=schedule(cur,e,today);assert e['rows'][0]['manual']['id']!=old and e['rows'][0]['manual']['status']=='OPEN'
  assert cur.execute('select status from erp.manual_reminders where id=%s',(old,)).fetchone()[0]=='CANCELLED'
  assert e['analysis']['analysis']==original['analysis']
  if e['analysis']['source_state']!='UNCHANGED':
   fresh=parent.capture(cur,today);oldfacts=cur.execute('select facts from cp7_analysis_native.runs where id=%s',(original['run_id'],)).fetchone()[0];newfacts=cur.execute('select facts from cp7_analysis_native.runs where id=%s',(fresh['run_id'],)).fetchone()[0]
   def diff(a,b,path=''):
    if a==b:return[]
    if isinstance(a,dict)and isinstance(b,dict):return[x for k in sorted(set(a)|set(b))for x in diff(a.get(k),b.get(k),path+'/'+k)]
    return[dict(path=path,before=a,after=b)]
   raise AssertionError(json.dumps(dict(code='P16_NATIVE_TASK_SOURCE_UNEXPECTED_CHANGE',old_hash=original['analysis']['snapshot']['source_hash'],new_hash=fresh['analysis']['snapshot']['source_hash'],difference=diff(oldfacts,newfacts)),default=str))
  return dict(status='PASS',unchanged_native_create_done_reopen_edit_cancel_new_lifecycle=True,Native_original_cancelled_task_retained=True,manual_tasks_never_change_stock_money_HPP_source=True)
 def replay():
  original,e,subject=prepared(cur,today);p=intent(e);key=uuid.uuid4();saved=command(cur,p,key);again=command(cur,p,key);assert saved['request_result']==again['request_result']and row_for(again,p)['attention']['revision']=='1'
  auth.refused(cur,lambda:command(cur,dict(p,action='DONE'),key),'CP7_REMINDER_REQUEST_CHANGED')
  auth.refused(cur,lambda:command(cur,p),'CP7_REMINDER_STALE_REVISION')
  assert cur.execute('select count(*)from cp7_reminder_native.requests where request_id=%s',(key,)).fetchone()[0]==1
  return dict(status='PASS',same_UUID_one_immutable_attention_result=True,changed_intent_and_stale_attention_revision_refused=True)
 def sealed_absent():
  original,e,subject=prepared(cur,today);p=intent(e,'SCHEDULE',title='Late request must stay absent',due_at=(today+timedelta(days=1)).isoformat()+'T08:00:00+07:00',priority='NORMAL');key=uuid.uuid4();before=b.boundary.snapshot(cur)
  sealed=resolve(cur,p,key);assert sealed['request_result']['status']=='NOT_COMMITTED'
  late=command(cur,p,key);assert late['request_result']==sealed['request_result']and row_for(late,p)['attention']['revision']=='0'and row_for(late,p)['manual']is None
  assert b.boundary.snapshot(cur)==before
  auth.refused(cur,lambda:cur.execute("update cp7_reminder_native.requests set result='{}'where request_id=%s",(key,)),'CP7_REMINDER_REQUEST_IMMUTABLE')
  return dict(status='PASS',serialized_absent_resolution_creates_immutable_negative_fence=True,late_original_same_UUID_cannot_create_task=True,no_business_DML=True)
 def ownership():
  original,e,subject=prepared(cur,today,True);p=intent(e);key=uuid.uuid4();saved=command(cur,p,key,subject);assert saved['request_result']['status']=='COMMITTED'
  custom,_=auth.custom_actor(cur);unsupported=parent.capture(cur,today,subject=custom)
  auth.refused(cur,lambda:get(cur,unsupported['run_id'],custom),'CP7_REMINDER_INTERNAL_ROLE_REQUIRED')
  auth.refused(cur,lambda:get(cur,original['run_id']),'CP7_ANALYSIS_RUN_UNAVAILABLE')
  auth.refused(cur,lambda:resolve(cur,p,key),'CP7_ANALYSIS_RUN_UNAVAILABLE')
  role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(subject,)).fetchone()[0];cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'",(role,))
  for fn in(lambda:get(cur,original['run_id'],subject),lambda:command(cur,p,key,subject),lambda:resolve(cur,p,key,subject)):auth.refused(cur,fn,'CP7_REMINDER_ACCESS_DENIED')
  return dict(status='PASS',actual_Native_STAFF_current_actor_and_permission_before_rows_cached_UUID_and_resolution=True,another_user_cannot_read_or_replay_original=True,custom_four_Ops_role_not_broadened_to_Native_personal_tasks=True)
 def native_version():
  original,e,subject=prepared(cur,today);e=schedule(cur,e,today);p=intent(e,'DONE');old=e['rows'][0]['manual'];changed=manual_save(cur,dict(id=old['id'],title='Edited in Native management',note=old['note'],due_at=old['due_at'],priority=old['priority'],module=old['module']),int(old['row_version']))
  auth.refused(cur,lambda:command(cur,p),'CP7_REMINDER_NATIVE_STALE_REVISION')
  fresh=get(cur,original['run_id']);assert fresh['rows'][0]['manual']['title']==changed['reminder']['title']and fresh['rows'][0]['attention']['revision']=='1'
  return dict(status='PASS',actual_Native_management_edit_cannot_be_overwritten_by_stale_bound_task=True,attention_revision_unchanged_on_native_conflict=True)
 def full_page():
  original,e,subject=prepared(cur,today);e=schedule(cur,e,today);linked=e['rows'][0]['manual']['id']
  for i in range(201):manual_save(cur,dict(title='Unrelated own Native task '+str(i),note='',due_at=today.isoformat()+'T08:00:00+07:00',priority='URGENT',module='Operasional'))
  page=rpc(cur,'erp_list_my_reminders_v1',('ALL',200));assert len(page['items'])==200 and not any(x['id']==linked for x in page['items'])
  fresh=get(cur,original['run_id']);assert fresh['native_manual_page_complete']and fresh['rows'][0]['manual']['id']==linked
  assert sum(r['manual']is not None for r in fresh['rows'])==1
  return dict(status='PASS',actual_201_unrelated_Native_tasks_do_not_truncate_bound_analysis_source=True,only_linked_own_tasks_returned=True)
 def archive_condition():
  original,e,subject=prepared(cur,today);e=command(cur,intent(e,'DONE'));definition=cur.execute("select pg_get_functiondef('cp7_analysis_native.fact(text,text,jsonb,jsonb)'::regprocedure)").fetchone()[0]
  assert 'SOURCE_INPUT_NOT_PROVEN'in definition;cur.execute(definition.replace('SOURCE_INPUT_NOT_PROVEN','SOURCE_INPUT_NOT_PROVEN_ATTENTION_REVISED'),prepare=False)
  # The real function definition is itself a source dependency. A saved DONE
  # state cannot turn the original archived source into a resolved condition.
  archived=get(cur,original['run_id']);assert archived['analysis']['source_state']=='ARCHIVED_STALE'and archived['analysis']['analysis']==original['analysis']
  assert archived['rows'][0]['attention']['state']=='DONE'and archived['rows'][0]['condition']=='SOURCE_CHANGED'and not archived['rows'][0]['business_resolved']
  return dict(status='PASS',actual_source_definition_change_keeps_original_archived_body=True,DONE_attention_never_means_source_changed_condition_resolved=True)
 return parent.cases(cur,today)+[('P16_NATIVE_ATTENTION_'+n,f)for n,f in [('REVIEW_METADATA',review),('NATIVE_TASK_LIFECYCLE',lifecycle),('IMMUTABLE_UUID_CAS',replay),('SEALED_ABSENT',sealed_absent),('CURRENT_ACTOR_AUTH',ownership),('NATIVE_TASK_CAS',native_version),('FULL_BOUND_SOURCE201',full_page),('ARCHIVE_CONDITION',archive_condition)]]

def races(tools,today):
 def duplicate():
  with tools.connect()as conn,conn.cursor()as cur:original,e,subject=prepared(cur,today);p=intent(e,'SCHEDULE',title='One Native task',note='',due_at=(today+timedelta(days=1)).isoformat()+'T08:00:00+07:00',priority='NORMAL');conn.commit()
  key=uuid.uuid4();gate=threading.Barrier(2)
  def send():
   with tools.connect()as conn,conn.cursor()as cur:gate.wait(timeout=5);result=command(cur,p,key);conn.commit();return result
  with ThreadPoolExecutor(max_workers=2)as pool:results=[x.result(60)for x in[pool.submit(send),pool.submit(send)]]
  assert results[0]['request_result']==results[1]['request_result']and row_for(results[0],p)['manual']['id']==row_for(results[1],p)['manual']['id']
  return dict(status='PASS',two_actual_transactions_one_request_one_Native_manual_task=True)
 def revoke():
  with tools.connect()as conn,conn.cursor()as cur:original,e,subject=prepared(cur,today,True);role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(subject,)).fetchone()[0];p=intent(e);key=uuid.uuid4();conn.commit()
  with tools.connect()as holder,holder.cursor()as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||%s||':'||%s,0))",(subject,str(key)))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=command(cur,p,key,subject);conn.commit();return r
     except psycopg.Error as ex:conn.rollback();return str(ex)
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send);waiting=False;deadline=time.monotonic()+10
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as c:
      while time.monotonic()<deadline:
       waiting=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_save_analysis_attention_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'P16_REAL_ATTENTION_LOCK_NOT_OBSERVED'
     with tools.connect()as conn,conn.cursor()as c:c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'",(role,));conn.commit()
    finally:holder.rollback()
    result=job.result(60)
  assert isinstance(result,str)and'CP7_REMINDER_ACCESS_DENIED'in result,result
  with tools.connect()as conn,conn.cursor()as c:assert c.execute('select count(*)from cp7_reminder_native.requests where actor=%s and request_id=%s',(subject,key)).fetchone()[0]==0
  return dict(status='PASS',permission_revoked_during_observed_request_lock_wait_refuses_without_metadata_commit=True)
 return parent.races(tools,today)+[('P16_ATTENTION_RACE_UUID',duplicate),('P16_ATTENTION_RACE_CURRENT_AUTH',revoke)]

def http_cases(http,today):
 def real_flow():
  owner=http.login('OWNER','p16-attention-http')
  with http.connect()as conn,conn.cursor()as c:parent.setup(c,today);conn.commit()
  captured=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=parent.previous.baseline.history.query(today),p_request=str(uuid.uuid4())));assert captured['status']==200,captured
  run=captured['body']['run_id'];e=owner.rpc('erp_cp7_get_analysis_attention_v1',dict(p_run=run));assert e['status']==200,e
  p=intent(e['body'],'SCHEDULE',title='Actual Auth own task',note='',due_at=(today+timedelta(days=1)).isoformat()+'T08:00:00+07:00',priority='NORMAL');args=dict(p_payload=p,p_request=str(uuid.uuid4()));saved=owner.rpc('erp_cp7_save_analysis_attention_v1',args);assert saved['status']==200,saved
  replay=owner.rpc('erp_cp7_save_analysis_attention_v1',args);assert replay['status']==200 and replay['body']['request_result']==saved['body']['request_result']
  with http.connect()as conn,conn.cursor()as c:c.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  for name,params in [('erp_cp7_get_analysis_attention_v1',dict(p_run=run)),('erp_cp7_save_analysis_attention_v1',args),('erp_cp7_get_analysis_attention_request_v1',args)]:assert owner.rpc(name,params)['status']==403
  return dict(status='PASS',actual_Auth_PostgREST_one_Native_schedule_exact_UUID_replay=True,deactivated_user_current403_get_replay_resolve=True)
 return parent.http_cases(http,today)+[('P16_ATTENTION_HTTP_NATIVE_CURRENT_AUTH',real_flow)]
