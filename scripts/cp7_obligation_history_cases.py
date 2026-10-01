"""Read-only current-authority Native business-episode history."""
import json,uuid
import cp7_obligation_episode_cases as previous
parent,ar,auth,b,attention=previous.parent,previous.ar,previous.auth,previous.b,previous.attention
def payload(original,source,domain='AR',before=None,through=None,limit=25):
 return dict(run_id=original['run_id'],domain=domain,source_id=source,before_episode=before,through_episode=through,limit=limit)
def history(cur,p,subject=None):
 return attention.rpc(cur,'erp_cp7_get_obligation_episode_history_v1',(json.dumps(p),),subject)
def signature(cur):
 result={}
 for name in('attention','requests','obligation_episodes','obligation_observations'):
  result[name]=cur.execute('select md5(coalesce(string_agg(x.body,\',\'order by x.body),\'\'))from(select row_to_json(t)::text as body from cp7_reminder_native.'+name+' t)x').fetchone()[0]
 return result
def cases(cur,today):
 def lifecycle():
  f,original=previous.ar_fixture(cur,today);one=previous.evaluate(cur,original);first=previous.row(one,f['sale'])['episode']
  # Actual accepted Native settlement/inverse creates every recurrence. No
  # fabricated money, direct monitoring inserts or force-mutated history rows.
  for i in range(25):
   paid=ar.sales.payment(cur,dict(f,tag=f['tag']+'-history-'+str(i)),today,'300');closed=previous.evaluate(cur,original);assert previous.row(closed,f['sale'])['episode']['state']=='RESOLVED'
   ar.sales.native(cur,'select erp.reverse_sales_payment(%s,%s)',(paid,'Native history recurrence inverse'));opened=previous.evaluate(cur,original);assert previous.row(opened,f['sale'])['episode']['number']==str(i+2)
  before=b.boundary.snapshot(cur);saved=signature(cur);one=history(cur,payload(original,f['sale']));assert one['contract_version']=='cp7.native-obligation-history.v1'and one['read_kind']=='SAVED_EPISODE_HISTORY'and one['total']=='26'and one['through_episode']=='26'and one['next_before_episode']=='2'and len(one['rows'])==25
  assert one['analysis']['analysis']==original['analysis']and one['analysis']['financial_source']==original['financial_source'];assert one['rows'][0]['episode']['number']=='26'and one['rows'][0]['episode']['state']=='ACTIVE'
  two=history(cur,payload(original,f['sale'],before='2',through='26'));assert two['total']=='26'and two['next_before_episode']is None and len(two['rows'])==1
  old=two['rows'][0]['episode'];assert old['id']==first['id']and old['number']=='1'and old['state']=='RESOLVED'
  joined=one['rows']+two['rows'];assert len({x['episode']['id']for x in joined})==26 and [x['episode']['number']for x in joined]==[str(i)for i in range(26,0,-1)]
  assert all(not any(k in x for k in('remaining','paid','final_ap','open_balance','gross_total','actor','analysis_run_id'))for x in joined)
  assert b.boundary.snapshot(cur)==before and signature(cur)==saved
  # Same private-source incompleteness control used by the Native episode
  # suite. Restore the actual source before reading saved UNKNOWN history.
  definition=cur.execute("select pg_get_functiondef('cp7_reminder_native.receivable_source()'::regprocedure)").fetchone()[0]
  try:
   b.api.admin(cur);cur.execute("create or replace function cp7_reminder_native.receivable_source() returns jsonb language plpgsql stable security invoker set search_path='' set TimeZone='UTC' as $$begin raise exception 'CP7_REMINDER_AR_SOURCE_INCOMPLETE'; end$$",prepare=False)
   incomplete=previous.row(previous.evaluate(cur,original),f['sale']);assert incomplete['episode']['freshness']=='UNKNOWN'
  finally:b.api.admin(cur);cur.execute(definition,prepare=False)
  saved_unknown=signature(cur);unknown=history(cur,payload(original,f['sale']));last=unknown['rows'][0]
  assert last['episode']['id']==one['rows'][0]['episode']['id']and last['episode']['freshness']=='UNKNOWN'and last['condition_state']==one['rows'][0]['condition_state']and last['reason']=='SOURCE_INCOMPLETE'
  assert signature(cur)==saved_unknown and b.boundary.snapshot(cur)==before
  auth.refused(cur,lambda:history(cur,payload(original,f['sale'],before='27',through='27')),'CP7_OBLIGATION_HISTORY_CURSOR')
  auth.refused(cur,lambda:history(cur,dict(payload(original,f['sale']),remaining='0')),'CP7_OBLIGATION_HISTORY_PAYLOAD')
  return dict(status='PASS',actual26_Native_settlement_inverse_episodes_complete_keyset25_plus1=True,closed_original_and_latest_recurrence_retained=True,all_ERP_business_and_monitoring_metadata_unchanged_by_history_read=True,actual_saved_UNKNOWN_retains_last_known_condition_without_false_current_knowledge=True,no_foreign_actor_run_or_money_fields_in_history_rows=True)
 def authority():
  f,original=previous.ar_fixture(cur,today);first=previous.row(previous.evaluate(cur,original),f['sale'])['episode'];subject,_=auth.custom_actor(cur)
  role=cur.execute("select id from erp.app_roles where role_code='STAFF'").fetchone()[0];cur.execute('update erp.app_roles set is_active=true where id=%s',(role,));cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject))
  for perm in(*auth.PERMS,'finance.ar.view'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,perm))
  own=parent.capture(cur,today,subject=subject);got=history(cur,payload(own,f['sale']),subject);assert got['actor_scope_id']==str(subject)and got['rows'][0]['episode']['id']==first['id']and got['analysis'].get('financial_source')is None
  auth.refused(cur,lambda:history(cur,payload(original,f['sale']),subject),'CP7_ANALYSIS_RUN_UNAVAILABLE')
  auth.refused(cur,lambda:history(cur,payload(own,str(uuid.uuid4())),subject),'CP7_OBLIGATION_HISTORY_SOURCE_UNAVAILABLE')
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ar.view'",(role,))
  auth.refused(cur,lambda:history(cur,payload(own,f['sale']),subject),'CP7_OBLIGATION_ACCESS_DENIED');assert parent.read(cur,own['run_id'],subject)['analysis']==own['analysis']
  return dict(status='PASS',authorized_actors_share_saved_business_history_only_with_own_Original=True,foreign_Original_and_outside_current_Native_source_denied=True,current_AR_only_revocation_refuses_previous_history_while_Ops_Original_remains_readable=True)
 return previous.cases(cur,today)+[('P16_HISTORY_NATIVE_COMPLETE26_READONLY',lifecycle),('P16_HISTORY_NATIVE_CURRENT_SCOPE_AUTH',authority)]
def races(tools,today):
 import threading,time
 from concurrent.futures import ThreadPoolExecutor
 import psycopg
 def revoke_history():
  with tools.connect()as conn,conn.cursor()as cur:
   f,original=previous.ar_fixture(cur,today);first=previous.row(previous.evaluate(cur,original),f['sale'])['episode'];subject,_=auth.custom_actor(cur)
   role=cur.execute("select id from erp.app_roles where role_code='STAFF'").fetchone()[0]
   cur.execute('update erp.app_roles set is_active=true where id=%s',(role,));cur.execute('update erp.app_users set role_id=%s where auth_user_id=%s',(role,subject))
   for perm in(*auth.PERMS,'finance.ar.view'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,perm))
   own=parent.capture(cur,today,subject=subject);saved=signature(cur);conn.commit()
  with tools.connect()as holder,holder.cursor()as held:
   held.execute('lock table cp7_reminder_native.obligation_episodes in access exclusive mode')
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:result=history(cur,payload(own,f['sale']),subject);conn.commit();return result
     except psycopg.Error as ex:conn.rollback();return str(ex)
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send);waiting=False;deadline=time.monotonic()+10
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as cur:
      while time.monotonic()<deadline:
       waiting=cur.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event_type='Lock'and wait_event='relation'and query like 'select public.erp_cp7_get_obligation_episode_history_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'P16_HISTORY_REAL_TABLE_WAIT_NOT_OBSERVED'
     with tools.connect()as conn,conn.cursor()as cur:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ar.view'",(role,));conn.commit()
    finally:holder.rollback()
    result=job.result(60)
  assert isinstance(result,str)and'CP7_OBLIGATION_ACCESS_DENIED'in result,result
  with tools.connect()as conn,conn.cursor()as cur:assert signature(cur)==saved
  return dict(status='PASS',current_AR_only_revoked_during_actual_observed_history_read_lock_refuses=True,all_monitoring_metadata_unchanged=True)
 def revoke_finance_at_request_wait():
  from cp7_analysis_finance_cases import admin_actor
  with tools.connect()as conn,conn.cursor()as cur:
   parent.setup(cur,today);subject,role=admin_actor(cur,parent)
   original=parent.capture(cur,today,subject=subject)
   assert original['financial_source']['report']['close_preflight']is not None
   workspace=attention.get(cur,original['run_id'],subject)
   intent=attention.intent(workspace);key=uuid.uuid4();conn.commit()
  with tools.connect()as holder,holder.cursor()as held:
   held.execute("select pg_advisory_xact_lock(hashtextextended('CP7:REMINDER_REQUEST:'||%s||':'||%s,0))",(str(subject),str(key)))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:result=attention.command(cur,intent,key,subject);conn.commit();return result
     except psycopg.Error as ex:conn.rollback();return str(ex)
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send);waiting=False;deadline=time.monotonic()+10
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as cur:
      while time.monotonic()<deadline:
       waiting=cur.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_save_analysis_attention_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'P16_REAL_FINANCE_REQUEST_WAIT_NOT_OBSERVED'
     with tools.connect()as conn,conn.cursor()as cur:
      cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.period_close.manage'",(role,));conn.commit()
    finally:holder.rollback()
    result=job.result(60)
  assert isinstance(result,str)and'CP7_ANALYSIS_FINANCE_ACCESS_DENIED'in result,result
  with tools.connect()as conn,conn.cursor()as cur:
   assert cur.execute('select count(*)from cp7_reminder_native.requests where actor=%s and request_id=%s',(subject,key)).fetchone()[0]==0
   assert cur.execute('select count(*)from cp7_reminder_native.attention where actor=%s and run_id=%s',(subject,original['run_id'])).fetchone()[0]==0
  return dict(status='PASS',current_financial_close_capability_revoked_during_actual_request_lock_wait_refuses=True,no_attention_or_request_metadata_commit=True,source_reader_deduplication_preserves_protected_Original_authority=True)
 return previous.races(tools,today)+[('P16_HISTORY_RACE_CURRENT_AR_WAIT',revoke_history),('P16_RECHECK_RACE_CURRENT_FINANCE_REQUEST_WAIT',revoke_finance_at_request_wait)]
def http_cases(http,today):
 def actual():
  owner=http.login('OWNER','p16-history-http');other=http.login('OWNER','p16-history-foreign')
  with http.connect()as conn,conn.cursor()as cur:f,_=previous.ar_fixture(cur,today);conn.commit()
  original=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=parent.previous.baseline.history.query(today),p_request=str(uuid.uuid4())));assert original['status']==200
  observed=owner.rpc('erp_cp7_evaluate_obligation_episodes_v1',dict(p_payload=dict(run_id=original['body']['run_id'],domain='AR'),p_request=str(uuid.uuid4())));assert observed['status']==200
  args=dict(p_payload=payload(original['body'],f['sale']));got=owner.rpc('erp_cp7_get_obligation_episode_history_v1',args);assert got['status']==200 and got['body']['total']=='1'and got['body']['rows'][0]['episode']['id']==previous.row(observed['body'],f['sale'])['episode']['id']
  assert got['body']['analysis']['analysis']==original['body']['analysis']and got['body']['analysis']['financial_source']==original['body']['financial_source'];assert other.rpc('erp_cp7_get_obligation_episode_history_v1',args)['status']==403
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_get_obligation_episode_history_v1',args)['status']==403
  return dict(status='PASS',actual_Auth_PostgREST_complete_saved_Native_business_episode_history=True,exact_Owner_original_body_current_deactivation_and_foreign_Original_denial=True)
 return previous.http_cases(http,today)+[('P16_HISTORY_HTTP_CURRENT_AUTH',actual)]
