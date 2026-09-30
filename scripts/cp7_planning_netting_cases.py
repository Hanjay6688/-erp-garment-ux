"""Source-derived matching/netting oracles, real Native writers and current Auth."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
import json,threading,uuid
import cp7_planning_schedule_cases as schedule
import cp7_identity_cases as policies
import cp6_bf_probe as bf
supply=schedule.supply
baseline=schedule.baseline
production=schedule.production
auth=schedule.auth
b=schedule.b

def capture(cur,today,key=None,subject=None):return schedule.rpc(cur,'erp_cp7_capture_netting_v1',(json.dumps(baseline.history.query(today)),key or uuid.uuid4()),subject)
def read(cur,run,subject=None):return schedule.rpc(cur,'erp_cp7_read_netting_v1',(run,),subject)

def select_profiles(cur,root,all_policies=False):
 c=cur.execute('select cp7_baseline_native.source()').fetchone()[0]
 roots=[p['root_id']for p in c['facts']['products']]
 for p in baseline.get(cur,roots)['rows']:
  baseline.save(cur,dict(root_id=p['root_id'],product_version_id=p['product_version_id'],expected_revision=p['revision'],
   reason='Explicit selected Native netting fixture, zero mean on comparison roots is an assumption',
   config=dict(mean_mode='SELECTED_MANUAL',daily_pcs='10'if p['root_id']==root else '0',minimum_available_days='20',lead_days='3',review_days='7',buffer_days='0')))
 if all_policies:
  # Native commercial memberships and current production policies are written
  # through their unchanged public commands, not patched into source DTOs.
  c=cur.execute('select cp7_baseline_native.source()').fetchone()[0]
  for p in c['facts']['products']:
   if not p['commercial']:
    at=cur.execute('select clock_timestamp()').fetchone()[0]
    bf.save(cur,[bf.group(cur,[p['root_id']],at,settings=dict(price=None,bom=None,work_rates=[],laundry_rates=[]))],at)
  c=cur.execute('select cp7_baseline_native.source()').fetchone()[0]
  skus=list({s['sku_id']for p in c['facts']['products']for s in p['commercial']})
  w=policies.get(cur,skus)
  policies.apply(cur,[policies.proposal(p,'ACTIVE')for p in w['rows']])

def setup(cur,today,full=False):
 f=schedule.opening(cur,today)
 root=cur.execute('select product_id::text from erp.opening_balance_items where id=%s',(f['item'],)).fetchone()[0]
 select_profiles(cur,root,full);r=supply.capture(cur,today);p=schedule.payload(cur,r)
 return f,root,r,p

def row(r,root):return next(x for x in r['rows']if x['target_key'].split(':')[0]==root)

def cases(cur,today):
 def directed():
  f,root,r,p=setup(cur,today);schedule.save(cur,p);before=b.boundary.snapshot(cur);n=capture(cur,today);x=row(n,root)
  assert x['raw_gap_pcs']=='100'and x['directed_on_time_good_pcs']=='7'and x['base_gap_pcs']=='93',x
  m=next(x for x in n['match_results']if x['position_key']==p['config']['positions'][0]['position_key']and x['target_key'].split(':')[0]==root)
  assert m['result']['match']=='CONFIRMED_TARGET'and n['apply_enabled']is False
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',native_opening_product_binds_exact_root_size=True,selected_native8_yield7_target100_FG0_gap93=True,no_business_DML=True)
 def unknown():
  f,root,r,p=setup(cur,today);n=capture(cur,today);x=row(n,root)
  assert x['raw_gap_pcs']=='100'and x['base_gap_pcs']is None and x['net']['status']=='UNKNOWN',x
  assert x['net']['reason']=='TARGET_FG_OR_ELIGIBLE_SUPPLY_UNKNOWN'
  return dict(status='PASS',native_bound8_without_selected_yield_or_ETA_not_zero_supply=True)
 def global_allocation():
  f,root,r,p=setup(cur,today,True);schedule.save(cur,p);before=b.boundary.snapshot(cur);n=capture(cur,today)
  assert n['allocation']['status']=='SCENARIO',n['allocation']
  edges=n['allocation']['allocation']['edges'];assert len(edges)==1 and edges[0]['input_pcs']=='8'and edges[0]['projected_good_pcs']=='7',edges
  assert n['existing_timed_projected_good_budget_pcs']=='7'and n['new_start_capacity']['capacity_pcs']=='37'
  x=row(n,root);assert x['base_gap_pcs']==x['conditional_gap_pcs']=='93'and x['timeline']['end_balance_pcs']=='-93.000000000000'
  assert b.boundary.snapshot(cur)==before and n['apply_enabled']is False
  return dict(status='PASS',all_native_target_profiles_and_current_policy_selected=True,one_source_global_edge8_to7=True,existing_good_budget_separate_from_new_capacity37=True)
 def occupied():
  f,root,r,p=setup(cur,today,True)
  start=schedule.datetime.fromisoformat(p['config']['windows'][0]['starts_at'].replace('Z','+00:00'))
  p['config']['windows'][0]['ends_at']=schedule.stamp(start+timedelta(minutes=45));schedule.save(cur,p);n=capture(cur,today)
  assert n['new_start_capacity']['capacity_pcs']=='0'and n['allocation']['status']=='SCENARIO',n
  assert n['allocation']['allocation']['edges'][0]['projected_good_pcs']=='7'and row(n,root)['base_gap_pcs']=='93'
  return dict(status='PASS',all45_minutes_occupied_new_capacity0_still_allows_existing_Good7=True,no_existing_work_double_capacity_subtraction=True)
 def late():
  f,root,r,p=setup(cur,today,True);at=cur.execute('select clock_timestamp()').fetchone()[0]
  p['config']['windows'][0]['starts_at']=schedule.stamp(at+timedelta(days=11));p['config']['windows'][0]['ends_at']=schedule.stamp(at+timedelta(days=11,hours=2));p['config']['through_at']=schedule.stamp(at+timedelta(days=12))
  schedule.save(cur,p);n=capture(cur,today);x=row(n,root)
  assert x['base_gap_pcs']=='100'and x['directed_on_time_good_pcs']=='0'and not n['allocation']['allocation']['edges'],x
  assert x['net']['excluded'][0]['reason']=='AFTER_DEADLINE'and x['timeline']['first_known_gap']is not None
  return dict(status='PASS',native8_projected7_after_target_horizon_not_deducted_late_supply_never_erases_prior_gap=True)
 def unbound():
  f=production.cut.fixture(cur,today);n=capture(cur,today)
  matches=[x for x in n['match_results']if x['target_key'].split(':')[0]==f['product']]
  assert matches and all(x['result']['match']!='CONFIRMED_TARGET'for x in matches)
  assert any(x['result']['match']=='NEEDS_CHECK'for x in matches),matches
  return dict(status='PASS',native_cut_pattern_model_or_tariff_not_final_brand_color_confirmation=True,critical_missing_identity_remains_needs_check=True)
 def immutable():
  f,root,r,p=setup(cur,today);schedule.save(cur,p);key=uuid.uuid4();n=capture(cur,today,key)
  stored=cur.execute('select facts,result from cp7_netting_native.runs where id=%s',(n['run_id'],)).fetchone()
  assert capture(cur,today,key)['run_id']==n['run_id']
  production.b.bbp.complete(cur,f,f['cutover']+timedelta(days=2),3)
  old=read(cur,n['run_id']);assert old['source_state']=='ARCHIVED_STALE'and row(old,root)['base_gap_pcs']=='93'
  assert cur.execute('select facts,result from cp7_netting_native.runs where id=%s',(n['run_id'],)).fetchone()==stored
  assert cur.execute('select count(*)from cp7_netting_native.runs where request_id=%s',(key,)).fetchone()[0]==1
  auth.refused(cur,lambda:cur.execute('delete from cp7_netting_native.runs'),'CP7_RUN_IMMUTABLE')
  return dict(status='PASS',original_native_net_and_clock_immutable_after_actual_source_output3=True)
 def authority():
  production.opening(cur,today);subject,role=auth.custom_actor(cur);key=uuid.uuid4();n=capture(cur,today,key,subject)
  auth.refused(cur,lambda:read(cur,n['run_id']),'CP7_NETTING_RUN_UNAVAILABLE')
  q=baseline.history.query(today);q['matching']={'match':'CONFIRMED_TARGET'}
  auth.refused(cur,lambda:schedule.rpc(cur,'erp_cp7_capture_netting_v1',(json.dumps(q),uuid.uuid4()),subject),'CP7_WIP_FIELDS')
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'",(role,))
  auth.refused(cur,lambda:capture(cur,today,key,subject),'CP7_ACCESS_DENIED')
  auth.refused(cur,lambda:read(cur,n['run_id'],subject),'CP7_ACCESS_DENIED')
  return dict(status='PASS',native_actor_bound_current_four_permissions_before_cached_netting_no_client_match_label=True)
 added=[('BOUND_GAP93',directed),('BOUND_UNKNOWN_YIELD',unknown),('GLOBAL_ONE_EDGE',global_allocation),('EXISTING_WORK_DISTINCT',occupied),('LATE_NOT_NETTED',late),('UNBOUND_NEEDS_CHECK',unbound),('IMMUTABLE_AFTER_NATIVE_OUTPUT',immutable),('CURRENT_AUTH_CLOSED_QUERY',authority)]
 return schedule.cases(cur,today)+[('P06_NETTING_NATIVE_'+n,f)for n,f in added]

def races(tools,today):
 def same_uuid():
  with tools.connect()as conn,conn.cursor()as cur:setup(cur,today);conn.commit()
  key=uuid.uuid4();gate=threading.Barrier(2)
  def send():
   with tools.connect()as conn,conn.cursor()as cur:gate.wait(timeout=5);r=capture(cur,today,key);conn.commit();return r
  with ThreadPoolExecutor(max_workers=2)as pool:rs=[j.result(30)for j in[pool.submit(send),pool.submit(send)]]
  assert rs[0]['run_id']==rs[1]['run_id']and rs[0]['rows']==rs[1]['rows']
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_netting_native.runs where request_id=%s',(key,)).fetchone()[0]==1
  return dict(status='PASS',two_real_native_transactions_one_global_netting_UUID_run=True)
 return schedule.races(tools,today)+[('P06_NETTING_RACE_UUID',same_uuid)]

def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','p06-netting-owner');other=http.login('OWNER','p06-netting-other')
  with http.connect()as conn,conn.cursor()as cur:production.opening(cur,today);conn.commit()
  a=dict(p_query=baseline.history.query(today),p_request=str(uuid.uuid4()));r=owner.rpc('erp_cp7_capture_netting_v1',a);assert r['status']==200,r
  assert r['body']['apply_enabled']is False and owner.rpc('erp_cp7_capture_netting_v1',a)['body']['run_id']==r['body']['run_id']
  args=dict(p_run=r['body']['run_id']);assert other.rpc('erp_cp7_read_netting_v1',args)['status']==403
  assert http.anon_rpc('erp_cp7_read_netting_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_capture_netting_v1',a)['status']==403 and owner.rpc('erp_cp7_read_netting_v1',args)['status']==403
  return dict(status='PASS',real_Auth_server_netting_current403_actor_scope_no_fake_apply=True)
 return schedule.http_cases(http,today)+[('P06_NETTING_HTTP_AUTH',flow)]
