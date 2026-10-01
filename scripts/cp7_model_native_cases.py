"""Six Native adapter controls plus three explicit installed-kernel oracles.

No historical Native capture/configuration timestamp is backdated. Positive
rolling vectors are labelled synthetic private-kernel evidence, never Native
past-availability or public model-promotion evidence.
"""
import json,uuid,threading,time,copy
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor
import psycopg
import cp7_planning_history_cases as previous
auth,b=previous.auth,previous.b
def query(original,f,h='1'):
 return dict(history_run_id=original['run_id'],target_key=previous.row(original,f)['target_key'],horizon_days=h)
def capture(cur,q,key=None,subject=None):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_capture_model_evaluation_v1(%s,%s)',(json.dumps(q),key or uuid.uuid4())).fetchone()[0];b.api.admin(cur);return r
def read(cur,run,subject=None):
 auth.actor(cur,subject);r=cur.execute('select public.erp_cp7_read_model_evaluation_v1(%s)',(run,)).fetchone()[0];b.api.admin(cur);return r
def prepared(cur,today,days=1,subject=None):
 f=previous.fixture(cur,today);original=previous.capture(cur,today,subject=subject,q=previous.query(today,days));return f,original,query(original,f)
def stored(cur,run):return cur.execute('select input,result from cp7_model_native.runs where id=%s',(run,)).fetchone()
def kernel_input(cur):
 # A standalone numerical oracle, deliberately NOT a captured ERP dataset.
 config=cur.execute('select configuration from cp7_model_native.registry').fetchone()[0]
 return dict(query=dict(horizon_days='1'),from_date='2026-01-01',through_date='2026-01-12',
  target_key='SYNTHETIC-M',size_id='M',history_run_id=str(uuid.uuid4()),known_as_of='2026-01-30T10:00:00.000000Z',
  series=[dict(date=f'2026-01-{i:02}',known_at=f'2026-01-{i:02}T10:00:00.000000Z',revision='1',state='OBSERVED',value=str(i),refs=[dict(kind='SYNTHETIC_ORACLE',id=str(i),revision='1')])for i in range(1,13)],
  registry_id='cp7.native-model-policy.v1',registered_at='2025-12-31T00:00:00.000000Z',configuration=config,
  source_hash='a'*64,knowledge_basis='SYNTHETIC_KERNEL_ORACLE_ONLY',fallback_daily_mean='6.5',
  refs=[dict(kind='SYNTHETIC_ORACLE',id='independent-linear-demand',revision='1')],product_sku='SYNTHETIC',product_name='Private kernel vector')
def build(cur,d):return cur.execute('select cp7_model_native.build(%s)',(json.dumps(d),)).fetchone()[0]
def cases(cur,today):
 def short():
  f,original,q=prepared(cur,today);before=b.boundary.snapshot(cur);key=uuid.uuid4();one=capture(cur,q,key)
  assert one['reason']=='INSUFFICIENT_CHRONOLOGICAL_HISTORY'and one['selection_status']=='BASELINE_RETAINED'and one['evaluation']is None and one['forecast']is None
  assert one['history_run_id']==original['run_id']and one['target_key']==q['target_key']and not one['automatic_activation']and not one['apply_allowed']
  assert capture(cur,q,key)==one and read(cur,one['run_id'])==one and b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_Native_snapshot_short_history_explicit_fallback=True,one_UUID_one_original_no_business_write_or_activation=True)
 def registry_time():
  _,original,q=prepared(cur,today,12);one=capture(cur,q)
  assert one['reason']=='REGISTRY_NOT_KNOWN_BEFORE_VALIDATION'and one['evaluation']is None and one['selected_model_id']=='mean-1'
  d,_=stored(cur,one['run_id']);assert d['registered_at']==one['registry_registered_at']
  assert all(x['known_at']>=one['registry_registered_at']and x['state']=='UNKNOWN'and x['value']is None for x in d['series'])
  assert d['known_as_of']==original['captured_at']and d['no_retrospective_availability_backfill']
  return dict(status='PASS',actual_current_install_registry_not_backdated_before_old_validation=True,actual_capture_knowledge_not_physical_date_or_invented_observed_zero=True)
 def late_source():
  f,original,q=prepared(cur,today);one=capture(cur,q);frozen=stored(cur,one['run_id'])
  previous.sales.fg.post_sale(cur,f['draft']);later=previous.capture(cur,today);two=capture(cur,query(later,f))
  assert read(cur,one['run_id'])['source_state']=='ARCHIVED_STALE'and stored(cur,one['run_id'])==frozen
  assert previous.history(later,f)['gross_observed_pcs']=='24'and previous.history(original,f)['gross_observed_pcs']=='0'
  d,_=stored(cur,two['run_id']);assert d['known_as_of']==later['captured_at']and all(x['known_at']<=later['captured_at']for x in d['series'])
  assert all(x['state']!='OBSERVED'and x['value']is None for x in d['series'])
  return dict(status='PASS',actual_Native_post24_new_history_does_not_rewrite_old_evaluation=True,unknown_historical_availability_never_observed_zero=True,no_future_capture_in_older_Original=True)
 def current_auth():
  f,original,q=prepared(cur,today);one=capture(cur,q);other,role=auth.custom_actor(cur)
  auth.refused(cur,lambda:capture(cur,q,subject=other),'CP7_MODEL_NATIVE_HISTORY_UNAVAILABLE')
  auth.refused(cur,lambda:read(cur,one['run_id'],other),'CP7_MODEL_NATIVE_RUN_UNAVAILABLE')
  own=previous.capture(cur,today,subject=other);own_q=query(own,f);key=uuid.uuid4();native=capture(cur,own_q,key,other)
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(role,))
  auth.refused(cur,lambda:capture(cur,own_q,key,other),'CP7_ACCESS_DENIED');auth.refused(cur,lambda:read(cur,native['run_id'],other),'CP7_ACCESS_DENIED')
  return dict(status='PASS',foreign_history_and_model_Original_denied=True,current_permission_loss_before_cached_replay_or_archive=True)
 def closed():
  _,_,q=prepared(cur,today)
  for key in('series','models','policy','actor','registered_at','complete'):
   auth.refused(cur,lambda key=key:capture(cur,{**q,key:'forged'}),'CP7_WIP_FIELDS')
  for h in('0','91'):
   auth.refused(cur,lambda h=h:capture(cur,{**q,'horizon_days':h}),'CP7_MODEL_NATIVE_HORIZON')
  one=capture(cur,q);auth.refused(cur,lambda:capture(cur,{**q,'horizon_days':'2'},one['request_id']),'CP7_MODEL_NATIVE_REQUEST_CHANGED')
  return dict(status='PASS',closed_public_query_cannot_supply_forecasts_history_completeness_knowledge_or_policy=True,UUID_payload_change_rejected=True)
 def private():
  _,_,q=prepared(cur,today);one=capture(cur,q)
  for op in(lambda:cur.execute("update cp7_model_native.registry set registered_at=registered_at-interval'1 year'"),lambda:cur.execute('delete from cp7_model_native.runs where id=%s',(one['run_id'],))):auth.refused(cur,op,'CP7_RUN_IMMUTABLE')
  for who in('anon','authenticated','service_role'):
   assert not cur.execute("select has_table_privilege(%s,'cp7_model_native.registry','SELECT,INSERT,UPDATE,DELETE')or has_function_privilege(%s,'cp7_model_native.dataset(jsonb,uuid)','EXECUTE')",(who,who)).fetchone()[0]
  return dict(status='PASS',registry_and_evaluation_immutable_even_direct_admin_controls=True,no_public_private_kernel_or_metadata_access=True)
 def ses():
  r=cur.execute("select cp7_models.predict('SES','[\"20\",\"30\"]','{\"alpha\":\"0.5\",\"initial_level\":\"10\"}',1)").fetchone()[0]
  from decimal import Decimal
  assert Decimal(r['forecasts'][0])==Decimal('22.5')
  return dict(status='PASS',evidence_kind='SYNTHETIC_INSTALLED_PRIVATE_KERNEL_ORACLE',independent_X13_SES10_20_30_next22_5=True,Native_history_promotion_claim=False)
 def positive():
  d=kernel_input(cur);one=build(cur,d);assert one['selection_status']=='CHALLENGER_RECOMMENDED'and one['evaluation']['holdout']['used_for_selection']is False
  challenger=next(x for x in one['evaluation']['challengers']if x['model']['id']==one['selected_model_id']);assert challenger['decision']['promote']and challenger['summary']['fold_count']=='3'
  changed=copy.deepcopy(d);changed['series'][-1]['value']='999';two=build(cur,changed);assert one['selected_model_id']==two['selected_model_id']and one['evaluation']['baseline']==two['evaluation']['baseline']and one['evaluation']['challengers']==two['evaluation']['challengers']and one['evaluation']['holdout']!=two['evaluation']['holdout']
  return dict(status='PASS',evidence_kind='SYNTHETIC_INSTALLED_PRIVATE_ROLLING_ORACLE',positive_three_complete_fold_promotion_and_outer_holdout_separation=True,Native_history_promotion_claim=False)
 def no_leakage():
  d=kernel_input(cur);one=build(cur,d);changed=copy.deepcopy(d)
  changed['series'].append(dict(changed['series'][0],revision='2',known_at='2026-01-29T10:00:00.000000Z',value='999'))
  two=build(cur,changed);assert one['selected_model_id']==two['selected_model_id']
  for a,z in zip([one['evaluation']['baseline']]+one['evaluation']['challengers'],[two['evaluation']['baseline']]+two['evaluation']['challengers']):
   assert a['summary']==z['summary']and all(x['training']==y['training']for x,y in zip(a['folds'],z['folds']))
  blank=copy.deepcopy(d);blank['series']=[];missing=build(cur,blank);assert missing['reason']=='HISTORICAL_NATIVE_KNOWLEDGE_INSUFFICIENT'and missing['evaluation']['baseline']['summary']['fold_count']=='0'and missing['forecast']['status']=='INELIGIBLE'
  return dict(status='PASS',evidence_kind='SYNTHETIC_INSTALLED_PRIVATE_KNOWLEDGE_ORACLE',known_later_changes_no_old_training_or_model_selection=True,missing_not_zero_no_fake_fold=True,Native_history_promotion_claim=False)
 return previous.cases(cur,today)+[(name,fn)for name,fn in[('P07_NATIVE_SHORT',short),('P07_NATIVE_REGISTRY_TIME',registry_time),('P07_NATIVE_LATE_SOURCE',late_source),('P07_NATIVE_CURRENT_AUTH',current_auth),('P07_NATIVE_CLOSED_QUERY',closed),('P07_NATIVE_PRIVATE',private),('X13_PRIVATE_SES_ORACLE',ses),('X14_X15_PRIVATE_POSITIVE_HOLDOUT',positive),('M03_PRIVATE_KNOWLEDGE_LEAKAGE',no_leakage)]]
def races(tools,today):
 def same_uuid():
  with tools.connect()as conn,conn.cursor()as cur:_,_,q=prepared(cur,today);conn.commit()
  key=uuid.uuid4();gate=threading.Barrier(2)
  def send():
   with tools.connect()as conn,conn.cursor()as cur:gate.wait(timeout=5);r=capture(cur,q,key);conn.commit();return r
  with ThreadPoolExecutor(max_workers=2)as pool:jobs=[pool.submit(send)for _ in range(2)];one,two=[j.result(30)for j in jobs]
  assert one==two
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_model_native.runs where request_id=%s',(key,)).fetchone()[0]==1
  return dict(status='PASS',two_real_native_transactions_one_UUID_one_immutable_evaluation=True)
 def revoke():
  with tools.connect()as conn,conn.cursor()as cur:subject,role=auth.custom_actor(cur);_,_,q=prepared(cur,today,subject=subject);conn.commit()
  key=uuid.uuid4()
  with tools.connect()as holder,holder.cursor()as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:MODEL_EVALUATION:'||%s||':'||%s,0))",(subject,str(key)))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=capture(cur,q,key,subject);conn.commit();return r
     except psycopg.Error as e:conn.rollback();return str(e)
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send);waiting=False;deadline=time.monotonic()+8
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as c:
      while time.monotonic()<deadline:
       waiting=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_capture_model_evaluation_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'P07_REAL_REQUEST_WAIT_NOT_OBSERVED'
     with tools.connect()as conn,conn.cursor()as c:c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='sales.invoice.view'",(role,));conn.commit()
    finally:holder.rollback()
    result=job.result(30)
  assert isinstance(result,str)and'CP7_ACCESS_DENIED'in result,result
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_model_native.runs where request_id=%s',(key,)).fetchone()[0]==0
  return dict(status='PASS',current_permission_revoked_during_observed_actual_request_lock_no_evaluation_commit=True)
 return previous.races(tools,today)+[('P07_RACE_UUID',same_uuid),('P07_RACE_CURRENT_AUTH',revoke)]
def http_cases(http,today):
 def actual():
  owner=http.login('OWNER','p07-model-http');foreign=http.login('OWNER','p07-model-foreign')
  with http.connect()as conn,conn.cursor()as cur:f=previous.fixture(cur,today);conn.commit()
  original=owner.rpc('erp_cp7_capture_demand_history_v1',dict(p_query=previous.query(today,12),p_request=str(uuid.uuid4())));assert original['status']==200,original
  args=dict(p_query=query(original['body'],f),p_request=str(uuid.uuid4()));one=owner.rpc('erp_cp7_capture_model_evaluation_v1',args);assert one['status']==200,one
  assert one['body']['reason']=='REGISTRY_NOT_KNOWN_BEFORE_VALIDATION'and owner.rpc('erp_cp7_capture_model_evaluation_v1',args)['body']==one['body']
  assert foreign.rpc('erp_cp7_capture_model_evaluation_v1',args)['status']==403 and http.anon_rpc('erp_cp7_capture_model_evaluation_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_capture_model_evaluation_v1',args)['status']==403 and owner.rpc('erp_cp7_read_model_evaluation_v1',dict(p_run=one['body']['run_id']))['status']==403
  return dict(status='PASS',real_Auth_PostgREST_own_Native_history_fallback_exact_UUID=True,anonymous_foreign_deactivated_cached_read_denied=True)
 return previous.http_cases(http,today)+[('P07_HTTP_CURRENT_AUTH',actual)]
