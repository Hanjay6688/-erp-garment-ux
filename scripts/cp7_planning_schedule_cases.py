"""Real native source, public metadata/scenario APIs and explicit calendar oracles."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime,timedelta,timezone
import json,threading,time,uuid
import psycopg
import cp7_planning_supply_cases as supply
production=supply.production
baseline=supply.baseline
auth=supply.auth
b=supply.b

def stamp(at):return at.astimezone(timezone.utc).isoformat().replace('+00:00','Z')

def opening(cur,today):
 rows=production.b.bbp.production_rows()
 for payloads in rows.values():
  for p in payloads:
   for k,v in list(p.items()):
    if k.endswith('_name')and isinstance(v,str):p[k]='{C} '+v
 f=production.b.bbp.production_post(cur,today,rows)
 f['item']=production.b.bbp.source_of(cur,f)['opening_item_id'];return f

def rpc(cur,name,args,subject=None):
 auth.actor(cur,subject)
 placeholders=','.join('%s'for _ in args)
 r=cur.execute('select public.'+name+'('+placeholders+')',args).fetchone()[0]
 b.api.admin(cur);return r

def get(cur,run,subject=None):return rpc(cur,'erp_cp7_get_production_schedule_v1',(run,),subject)
def save(cur,p,key=None,subject=None):return rpc(cur,'erp_cp7_save_production_schedule_v1',(json.dumps(p),key or uuid.uuid4()),subject)
def capture(cur,today,key=None,subject=None):return rpc(cur,'erp_cp7_capture_planning_scenario_v1',(json.dumps(baseline.history.query(today)),key or uuid.uuid4()),subject)
def read(cur,run,subject=None):return rpc(cur,'erp_cp7_read_planning_scenario_v1',(run,),subject)

def payload(cur,r,revision='0'):
 at=cur.execute('select clock_timestamp()').fetchone()[0].replace(microsecond=0)+timedelta(hours=1)
 # Exact model/size comes from the retained native capture, not fixture labels.
 facts=cur.execute('select facts from cp7_supply_native.runs where id=%s',(r['run_id'],)).fetchone()[0]
 positions=[]
 for p in r['wip']['positions']:
  if int(p['remaining_pcs'])==0:continue
  model=cur.execute('select cp7_schedule_native.position_model(%s,%s)',(json.dumps(facts),json.dumps(p))).fetchone()[0]
  target=next((x for x in facts['facts']['products']if x['model_id']==model and x['size_id']==p['size_id']),None)
  stages=cur.execute('select cp7_schedule_native.route(%s)',(p['stage'],)).fetchone()[0]
  if stages is None:continue
  positions.append(dict(position_key=p['key'],target_key=target['root_id']+':'+target['size_id']if target and p['eligible_company_wip']else None,
   eligible_input_pcs=p['remaining_pcs'],yield_numerator='9'if p['eligible_company_wip']else None,yield_denominator='10'if p['eligible_company_wip']else None,
   remaining_steps=[dict(stage=s,remaining_minutes=str({'SEWING':15,'LAUNDRY':20,'QC':10,'REWORK':15,'REWASH':20}[s]))for s in stages]))
 return dict(source_run=r['run_id'],source_hash=r['source_hash'],expected_revision=revision,
  reason='Explicit reviewed selected work/yield scenario on native source; no production posting',
  config=dict(basis='SELECTED_ASSUMPTIONS',resource_scope='SINGLE_HOMOGENEOUS_SELECTED_CENTRE',
   work_centre_key='reviewed-centre',through_at=stamp(at+timedelta(hours=3)),unit_minutes='2',
   windows=[dict(key='work-1',starts_at=stamp(at),ends_at=stamp(at+timedelta(hours=2)),other_load_minutes='0')],positions=positions))

def cases(cur,today):
 def absent():
  opening(cur,today);r=supply.capture(cur,today);w=get(cur,r['run_id']);s=capture(cur,today)
  assert w['revision']=='0'and w['plan']is None and s['schedule_state']=='UNREVIEWED'
  assert s['capacity']['status']=='UNKNOWN'and s['final_gap_pcs']is None and s['apply_enabled']is False
  return dict(status='PASS',no_implicit_calendar_yield_unit_time_or_free_capacity=True)
 def metadata():
  opening(cur,today);r=supply.capture(cur,today);p=payload(cur,r);key=uuid.uuid4();before=b.boundary.snapshot(cur)
  s=save(cur,p,key);assert save(cur,p,key)==s
  assert get(cur,r['run_id'])['plan']['config']==p['config']and s['revision']=='1'
  bad=deepcopy(p);bad['reason']='different';auth.refused(cur,lambda:save(cur,bad,key),'CP7_SCHEDULE_REQUEST_CHANGED')
  assert cur.execute('select count(*)from cp7_schedule_native.plans').fetchone()[0]==1 and b.boundary.snapshot(cur)==before
  return dict(status='PASS',one_UUID_immutable_metadata_revision_no_native_business_write=True)
 def strict():
  opening(cur,today);r=supply.capture(cur,today);p=payload(cur,r)
  mutations=[('eligible_input_pcs','9'),('eligible_input_pcs',8),('yield_numerator','11'),('yield_denominator','0'),('position_key','invented'),('target_key',str(uuid.uuid4())+':'+str(uuid.uuid4()))]
  for k,v in mutations:
   bad=deepcopy(p);bad['config']['positions'][0][k]=v;auth.refused(cur,lambda bad=bad:save(cur,bad),'CP7_')
  bad=deepcopy(p);bad['config']['positions'][0]['remaining_steps']=[dict(stage='QC',remaining_minutes='0')]
  auth.refused(cur,lambda:save(cur,bad),'CP7_SCHEDULE_REMAINING_ROUTE')
  bad=deepcopy(p);bad['config']['windows'].append(deepcopy(bad['config']['windows'][0]));bad['config']['windows'][1]['key']='overlap'
  auth.refused(cur,lambda:save(cur,bad),'CP7_SCHEDULE_WINDOW')
  bad=deepcopy(p);bad['config']['complete_scope']=True;auth.refused(cur,lambda:save(cur,bad),'CP7_WIP_FIELDS')
  assert cur.execute('select count(*)from cp7_schedule_native.plans').fetchone()[0]==0
  return dict(status='PASS',native_quantity_model_size_full_route_closed_shape_and_dated_nonoverlap=True)
 def source_stale():
  f=opening(cur,today);r=supply.capture(cur,today);p=payload(cur,r);save(cur,p);s=capture(cur,today)
  production.b.bbp.complete(cur,f,f['cutover']+timedelta(days=2),3)
  w=get(cur,r['run_id']);assert w['source_state']=='ARCHIVED_STALE'and w['plan_state']=='SOURCE_CHANGED'
  assert w['source_hash']==r['source_hash']and w['captured_at']==r['captured_at']and w['position_requirements'][0]['remaining_pcs']=='8'
  fresh=supply.capture(cur,today);assert get(cur,fresh['run_id'])['position_requirements'][0]['remaining_pcs']=='5'
  bad=deepcopy(p);bad['expected_revision']='1';auth.refused(cur,lambda:save(cur,bad),'CP7_SCHEDULE_SOURCE_CHANGED')
  assert read(cur,s['run_id'])['source_state']=='ARCHIVED_STALE'and capture(cur,today)['schedule_state']=='SOURCE_CHANGED'
  return dict(status='PASS',real_native_completed3_invalidates_old_work_and_source_bound_save=True)
 def revision():
  opening(cur,today);r=supply.capture(cur,today);p=payload(cur,r);save(cur,p);s=capture(cur,today)
  auth.refused(cur,lambda:save(cur,p),'CP7_SCHEDULE_REVISION_CHANGED')
  p['expected_revision']='1';p['config']['positions'][0]['yield_numerator']='1';p['config']['positions'][0]['yield_denominator']='1';save(cur,p)
  old=read(cur,s['run_id']);assert old['source_state']=='ARCHIVED_STALE'and old['schedule']['revision']=='1'
  assert old['wip']==s['wip']and capture(cur,today)['schedule']['revision']=='2'
  return dict(status='PASS',revision_conflict_atomic_old_yield_calendar_run_immutable=True)
 def yield7():
  opening(cur,today);r=supply.capture(cur,today);save(cur,payload(cur,r));before=b.boundary.snapshot(cur);s=capture(cur,today)
  assert len(s['wip']['positions'])==1 and s['wip']['positions'][0]['projection']['projected_good_pcs']=='7',s
  assert int(s['wip']['totals'][0]['wip_pcs'])==8 and int(s['wip']['totals'][0]['fg_pcs'])==0
  assert s['final_gap_pcs']is None and s['allocation']['status']=='UNKNOWN'and b.boundary.snapshot(cur)==before
  return dict(status='PASS',selected9_over10_of_native8_projects7_never_posts_Good_or_BS=True)
 def remaining():
  opening(cur,today);r=supply.capture(cur,today);p=payload(cur,r);save(cur,p);s=capture(cur,today)
  assert s['capacity']['status']=='SCENARIO'and s['capacity']['capacity_pcs']=='37',s['capacity']
  eta=s['etas'][0]['result'];assert eta['status']=='CONDITIONAL'and eta['on_time']is True,eta
  start=datetime.fromisoformat(p['config']['windows'][0]['starts_at'].replace('Z','+00:00'))
  assert datetime.fromisoformat(eta['eta'].replace('Z','+00:00'))==start+timedelta(minutes=45),eta
  return dict(status='PASS',native_remaining15_20_10_minute_route_one_future120_window_new_capacity37=True,selected_ETA45_not_full_route_or_wall_clock_guess=True)
 def missing_load():
  opening(cur,today);r=supply.capture(cur,today);p=payload(cur,r);p['config']['windows'][0]['other_load_minutes']=None;save(cur,p);s=capture(cur,today)
  assert s['capacity']['status']=='UNKNOWN'and s['capacity']['capacity_pcs']is None and all(x['result']['status']=='UNKNOWN'for x in s['etas'])
  return dict(status='PASS',null_other_load_not_zero_or_free_capacity=True)
 def placed_load():
  opening(cur,today);r=supply.capture(cur,today);p=payload(cur,r);p['config']['windows'][0]['other_load_minutes']='20';save(cur,p);s=capture(cur,today)
  assert s['capacity']['capacity_pcs']=='27'and s['etas'][0]['result']['reason']=='OTHER_LOAD_DATED_PLACEMENT_NOT_SELECTED'
  return dict(status='PASS',selected_other_load20_reduces_capacity_but_unplaced_load_never_fakes_exact_ETA=True)
 def overflow_carried():
  # PL-4: other load a window cannot hold is still owed and carries into the
  # next window (120 - 40 carried - 45 captured = 35 min -> 17 pcs at 2 min);
  # load left after the last window makes capacity UNKNOWN, never '0' or free.
  opening(cur,today);r=supply.capture(cur,today);p=payload(cur,r)
  start=datetime.fromisoformat(p['config']['windows'][0]['starts_at'].replace('Z','+00:00'))
  p['config']['windows']=[dict(key='work-1',starts_at=stamp(start),ends_at=stamp(start+timedelta(minutes=60)),other_load_minutes='100'),
   dict(key='work-2',starts_at=stamp(start+timedelta(minutes=60)),ends_at=stamp(start+timedelta(minutes=180)),other_load_minutes='0')]
  save(cur,p);s=capture(cur,today);c=s['capacity']
  assert c['status']=='SCENARIO'and c['capacity_pcs']=='17'and c['kernel_version']=='calendar-capacity-2',c
  assert int(c['inputs']['windows'][0]['existing_load_minutes'].split('.')[0])==100,c['inputs']['windows']
  late=deepcopy(p);late['expected_revision']='1';late['config']['windows'][0]['other_load_minutes']='200';save(cur,late);s=capture(cur,today);c=s['capacity']
  assert c['status']=='UNKNOWN'and c['capacity_pcs']is None and c['reason']=='EXISTING_LOAD_EXCEEDS_CALENDAR',c
  return dict(status='PASS',overflow40_carried_into_next_window_capacity17_not_37=True,load_left_after_calendar_unknown_not_zero=True)
 def shared():
  opening(cur,today);opening(cur,today);r=supply.capture(cur,today);p=payload(cur,r);assert len(p['config']['positions'])==2
  missing=deepcopy(p);missing['config']['positions']=missing['config']['positions'][:1];save(cur,missing);s=capture(cur,today)
  assert s['capacity']['status']=='UNKNOWN'and all(x['result']['status']=='UNKNOWN'for x in s['etas'])
  p['expected_revision']='1';save(cur,p);s=capture(cur,today)
  assert s['capacity']['capacity_pcs']=='15'and len(s['etas'])==2
  assert all(x['result']['status']=='CONDITIONAL'for x in s['etas'])
  assert s['etas'][0]['result']['eta']!=s['etas'][1]['result']['eta']
  return dict(status='PASS',two_native_pools_share_one_remaining_queue_and_one_capacity_budget=True,unreviewed_pool_not_free=True)
 def private():
  opening(cur,today);r=supply.capture(cur,today);save(cur,payload(cur,r));capture(cur,today)
  for table in('plans','commands','runs'):
   auth.refused(cur,lambda table=table:cur.execute('delete from cp7_schedule_native.'+table),'CP7_RUN_IMMUTABLE')
   for who in('anon','authenticated','service_role'):
    assert not cur.execute('select has_table_privilege(%s,%s,\'SELECT,INSERT,UPDATE,DELETE\')',(who,'cp7_schedule_native.'+table)).fetchone()[0]
  assert not cur.execute("select exists(select 1 from pg_class t join pg_namespace n on n.oid=t.relnamespace where n.nspname='erp'and t.relkind in('r','p','v')and has_table_privilege('cp7_capture',t.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
  return dict(status='PASS',three_private_immutable_falseRLS_tables_no_operational_or_native_DML=True)
 def authority():
  opening(cur,today);subject,role=baseline.custom_writer(cur);r=supply.capture(cur,today,subject=subject);p=payload(cur,r);key=uuid.uuid4();save(cur,p,key,subject);s=capture(cur,today,subject=subject)
  auth.refused(cur,lambda:get(cur,r['run_id']),'CP7_SUPPLY_RUN_UNAVAILABLE');auth.refused(cur,lambda:read(cur,s['run_id']),'CP7_SCHEDULE_RUN_UNAVAILABLE')
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='master.product.manage'",(role,))
  auth.refused(cur,lambda:save(cur,p,key,subject),'CP7_SCHEDULE_ACCESS_DENIED')
  assert read(cur,s['run_id'],subject)['run_id']==s['run_id']
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'",(role,))
  auth.refused(cur,lambda:read(cur,s['run_id'],subject),'CP7_ACCESS_DENIED')
  return dict(status='PASS',current_master_write_permission_before_cached_UUID_and_current_four_domain_read=True)
 def customer_work():
  opening(cur,today);f=opening(cur,today)
  customer=auth.base.create_customer(cur,'P06CW-'+uuid.uuid4().hex[:6])
  # Administrative ownership source fixture after ordinary import: qualifies
  # read/queue semantics, not a public customer-production posting workflow.
  cur.execute('set local session_replication_role=replica')
  cur.execute('update erp.opening_balance_items set customer_id=%s where id=%s',(customer,f['item']))
  cur.execute('set local session_replication_role=origin')
  r=supply.capture(cur,today);p=payload(cur,r);assert len(p['config']['positions'])==2
  only_company=deepcopy(p);only_company['config']['positions']=[x for x in only_company['config']['positions']if x['yield_numerator']is not None]
  save(cur,only_company);s=capture(cur,today);assert s['capacity']['status']=='UNKNOWN'
  p['expected_revision']='1';save(cur,p);s=capture(cur,today)
  assert s['capacity']['capacity_pcs']=='15'and len(s['etas'])==2,s
  owned=[x for x in s['wip']['positions']if x['eligible_company_wip']];assert len(owned)==1 and owned[0]['projection']['projected_good_pcs']=='7'
  bad=deepcopy(p);bad['expected_revision']='2';x=next(x for x in bad['config']['positions']if x['yield_numerator']is None);x['yield_numerator']='1';x['yield_denominator']='1'
  auth.refused(cur,lambda:save(cur,bad),'CP7_SCHEDULE_CUSTOMER_WORK_ONLY')
  return dict(status='PASS',administrative_native_ownership_source_fixture=True,customer8_consumes45_minutes_shared_capacity15_never_company_good=True)
 added=[('UNREVIEWED',absent),('UUID_METADATA',metadata),('STRICT_SOURCE_ROUTE',strict),('SOURCE_STALE',source_stale),('REVISION_STALE',revision),('YIELD7',yield7),('REMAINING45_CAPACITY37',remaining),('NULL_LOAD',missing_load),('OTHER_LOAD_PLACEMENT',placed_load),('PL4_OVERFLOW_CARRIED',overflow_carried),('SHARED_QUEUE',shared),('PRIVATE_CAPABILITIES',private),('CURRENT_AUTH',authority),('CUSTOMER_WORK_ONLY',customer_work)]
 return supply.cases(cur,today)+[('P06_SCHEDULE_NATIVE_'+n,f)for n,f in added]

def races(tools,today):
 def revision():
  with tools.connect()as conn,conn.cursor()as cur:
   opening(cur,today);r=supply.capture(cur,today);p=payload(cur,r);conn.commit()
  gate=threading.Barrier(2)
  def send():
   with tools.connect()as conn,conn.cursor()as cur:
    gate.wait(timeout=5)
    try:r=save(cur,p);conn.commit();return r
    except psycopg.Error as e:conn.rollback();return str(e)
  with ThreadPoolExecutor(max_workers=2)as pool:rs=[j.result(30)for j in[pool.submit(send),pool.submit(send)]]
  assert len([r for r in rs if isinstance(r,dict)and r['revision']=='1'])==1 and len([r for r in rs if isinstance(r,str)and'CP7_SCHEDULE_REVISION_CHANGED'in r])==1,rs
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_schedule_native.plans').fetchone()[0]==1
  return dict(status='PASS',two_native_transactions_global_revision_one_selected_plan=True)
 def revoked():
  with tools.connect()as conn,conn.cursor()as cur:
   opening(cur,today);subject,role=baseline.custom_writer(cur);r=supply.capture(cur,today,subject=subject);p=payload(cur,r);key=uuid.uuid4();save(cur,p,key,subject);conn.commit()
  with tools.connect()as holder,holder.cursor()as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:SCHEDULE:REQUEST:'||%s||':'||%s,0))",(subject,str(key)))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=save(cur,p,key,subject);conn.commit();return r
     except psycopg.Error as e:conn.rollback();return str(e)
   with ThreadPoolExecutor(max_workers=1)as pool:
    j=pool.submit(send);waiting=False;deadline=time.monotonic()+8
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as c:
      while time.monotonic()<deadline:
       waiting=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_save_production_schedule_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'SCHEDULE_CACHED_UUID_NATIVE_LOCK_NOT_OBSERVED'
     with tools.connect()as conn,conn.cursor()as cur:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='master.product.manage'",(role,));conn.commit()
    finally:holder.rollback()
    result=j.result(30)
  assert isinstance(result,str)and'CP7_SCHEDULE_ACCESS_DENIED'in result,result
  return dict(status='PASS',current_native_master_revoke_during_observed_cached_UUID_wait=True)
 return supply.races(tools,today)+[('P06_SCHEDULE_RACE_REVISION',revision),('P06_SCHEDULE_RACE_CACHED_AUTH',revoked)]

def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','p06-schedule-owner');other=http.login('OWNER','p06-schedule-other')
  with http.connect()as conn,conn.cursor()as cur:opening(cur,today);conn.commit()
  q=baseline.history.query(today);a=dict(p_query=q,p_request=str(uuid.uuid4()));r=owner.rpc('erp_cp7_capture_production_supply_v1',a);assert r['status']==200,r
  with http.connect()as conn,conn.cursor()as cur:p=payload(cur,r['body']);conn.rollback()
  args=dict(p_payload=p,p_request=str(uuid.uuid4()));s=owner.rpc('erp_cp7_save_production_schedule_v1',args);assert s['status']==200,s
  assert owner.rpc('erp_cp7_save_production_schedule_v1',args)['body']==s['body']
  expected=(120-sum(int(x['remaining_minutes'])for pos in p['config']['positions']for x in pos['remaining_steps']))//2
  sc=owner.rpc('erp_cp7_capture_planning_scenario_v1',dict(p_query=q,p_request=str(uuid.uuid4())));assert sc['status']==200 and sc['body']['capacity']['capacity_pcs']==str(expected),sc
  read_args=dict(p_run=sc['body']['run_id']);assert other.rpc('erp_cp7_read_planning_scenario_v1',read_args)['status']==403
  assert http.anon_rpc('erp_cp7_read_planning_scenario_v1',read_args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_save_production_schedule_v1',args)['status']==403 and owner.rpc('erp_cp7_read_planning_scenario_v1',read_args)['status']==403
  return dict(status='PASS',real_Auth_metadata_and_native_scenario_actor_immutable_current403=True)
 def reader():
  owner=http.login('OWNER','p06-schedule-unreviewed-owner')
  with http.connect()as conn,conn.cursor()as cur:
   had_plan=cur.execute('select exists(select 1 from cp7_schedule_native.plans)').fetchone()[0]
   opening(cur,today);conn.commit()
  a=dict(p_query=baseline.history.query(today),p_request=str(uuid.uuid4()));r=owner.rpc('erp_cp7_capture_planning_scenario_v1',a)
  expected='SOURCE_CHANGED'if had_plan else 'UNREVIEWED'
  assert r['status']==200 and r['body']['schedule_state']==expected and r['body']['capacity']['capacity_pcs']is None,r
  assert owner.rpc('erp_cp7_capture_planning_scenario_v1',a)['body']['run_id']==r['body']['run_id']
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_capture_planning_scenario_v1',a)['status']==403
  return dict(status='PASS',real_Auth_unreviewed_work_never_free_current_replay_denial=True)
 return supply.http_cases(http,today)+[('P06_SCHEDULE_HTTP_FLOW',flow),('P06_SCHEDULE_HTTP_UNREVIEWED',reader)]
