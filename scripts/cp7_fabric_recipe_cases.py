"""Declared Native recipe-input slice; no installation/factory-readiness credit."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D
from queue import Queue
import copy,json,time,uuid
import psycopg
import cp7_plan_native_cases as plan
parent=plan.analysis;b=parent.b;auth=parent.auth
REQUIRED=dict(native=8,races=2,http=1,browser=2)
EXPECTED=sum(REQUIRED.values())
IDS=dict(native=['P08_FABRIC_MISSING','P08_FABRIC_GROSS170','P08_FABRIC_CLOCK','P08_FABRIC_SUCCESSOR255','P08_FABRIC_MASTER_CHANGED','P08_FABRIC_STRICT_CAS','P08_FABRIC_OWN_ACTOR_PRIVATE','P08_FABRIC_CATALOG'],
 races=['P08_FABRIC_REAL_TWO_WRITER_CAS_WAIT','P08_FABRIC_REAL_WAIT_REVOKED'],http=['P08_FABRIC_REAL_AUTH_HTTP'],browser=['P08_FABRIC_BROWSER_DESKTOP','P08_FABRIC_BROWSER_MOBILE'])
def save(cur,p,key=None,subject=None):return plan.rpc(cur,'erp_cp7_save_fabric_recipe_v1',(json.dumps(p),key or uuid.uuid4()),subject)
def workspace(cur,q,subject=None):return plan.rpc(cur,'erp_cp7_get_fabric_recipe_v1',(json.dumps(q),),subject)
def rows(e,target):return[m for m in e['analysis']['material_needs']if m['target_key']==target and(m['material_key']or'').startswith('FABRIC_')]
def unknown(row):
 assert all(row[k]['state']=='UNKNOWN'and'value'not in row[k]for k in('installed_proven','unused_allocated_proven','additional_external')),row
def physical(row,gross):
 # P08 successor oracle. The same fixture holds exactly one posted ten-unit roll
 # of the reviewed fabric, no linked/manual draft, no open commitment and no
 # other new-start claimant: the unique free-stock allocation10. Its unbound
 # same-model/size WIP is NEEDS_CHECK (brand/color unproved): PCS of this
 # target may already be cut, so installation is UNKNOWN and the external
 # addition is UNKNOWN with only the exact upper bound gross-10 in the reason.
 i,u,e=(row[k]for k in('installed_proven','unused_allocated_proven','additional_external'))
 assert i['state']=='UNKNOWN'and'value'not in i and i['reason']=='FABRIC_WIP_IDENTITY_UNRESOLVED',row
 assert u['state']=='ASSUMED'and D(u['value'])==10 and any(r['kind']=='CP7_FABRIC_FREE_STOCK'for r in u['refs']),row
 assert e['state']=='UNKNOWN'and'value'not in e and e['reason']=='FABRIC_WIP_IDENTITY_UNRESOLVED'and f'paling banyak {D(gross)-10} 'in row['reason'],row
def setup(cur,today,subject=None):
 f=plan.setup(cur,today,subject);roll=next(r for r in f['options']['rolls']if r['id']==f['payload']['cutting']['rolls'][0]['roll_id']);sku=cur.execute('select material_sku from erp.materials where id=%s',(roll['material_id'],)).fetchone()[0]
 q=dict(run_id=f['original']['run_id'],target_key=f['payload']['target_key'],material_query=sku,material_offset='0',pattern_offset='0',limit='50')
 w=workspace(cur,q,subject);roll=next(r for r in f['options']['rolls']if r['id']==f['payload']['cutting']['rolls'][0]['roll_id']);material=next(m for m in w['materials']if m['id']==roll['material_id']);pattern=w['patterns'][0]
 assert D(f['options']['needed_pcs'])==85,dict(needed=f['options']['needed_pcs'],root=f['root'])
 cfg=dict(basis='SELECTED_ASSUMPTIONS',effective_from=parent.schedule.stamp(cur.execute('select clock_timestamp()').fetchone()[0]-timedelta(minutes=1)),effective_to=None,
  material_id=material['id'],material_hash=material['source_hash'],unit=material['unit'],qty_per_good_pcs='2',pattern_id=pattern['id'],pattern_hash=pattern['source_hash'])
 p=dict(run_id=w['run_id'],target_key=w['target_key'],source_hash=w['source_hash'],expected_revision=w['revision'],config=cfg,reason='Explicit synthetic fixture rate2 per PCS; not factory recipe or consumption')
 return dict(plan=f,workspace=w,query=q,payload=p,target=w['target_key'])
def cases(cur,today):
 def missing():
  f=setup(cur,today);before=b.boundary.snapshot(cur);m=rows(f['plan']['original'],f['target']);assert len(m)==1 and m[0]['material_key']=='FABRIC_UNREVIEWED:'+f['target']and m[0]['gross']['state']=='UNKNOWN';unknown(m[0]);assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',exact_Native_root_size_unreviewed_fabric_not_zero=True,complete_material_row=m[0],Native_boundary_unchanged_by_read=True)
 def gross():
  f=setup(cur,today);before=b.boundary.snapshot(cur);key=uuid.uuid4();out=save(cur,f['payload'],key);assert save(cur,f['payload'],key)==out
  old=parent.read(cur,f['plan']['original']['run_id']);assert old['source_state']=='ARCHIVED_STALE'and old['analysis']==f['plan']['original']['analysis']
  fresh=parent.capture(cur,today);parent.checked(fresh);m=rows(fresh,f['target'])[0];assert m['gross']['state']=='ASSUMED'and D(m['gross']['value'])==170 and m['gross']['unit']==f['payload']['config']['unit'];physical(m,170)
  assert out['recipe_id']in m['gross']['assumption_ids']and any(r['kind']=='erp.materials'and r['id']==f['payload']['config']['material_id']for r in m['gross']['refs'])
  assert parent.recommendation(fresh['analysis'],f['plan']['root'])['feasible_new']['state']=='UNKNOWN'and b.boundary.snapshot(cur)==before
  return dict(status='PASS',Native_gap85_selected_rate2_gross170=True,same_UUID_one_immutable_recipe=True,all_Native_stock_money_HPP_unchanged=True,original_preserved=True,complete_material_row=m)
 def clock():
  f=setup(cur,today);now=cur.execute('select clock_timestamp()').fetchone()[0];p=copy.deepcopy(f['payload']);p['config'].update(effective_from=parent.schedule.stamp(now+timedelta(hours=1)),effective_to=parent.schedule.stamp(now+timedelta(hours=2)));out=save(cur,p)
  source=cur.execute('select facts from cp7_analysis_native.runs where id=%s',(f['plan']['original']['run_id'],)).fetchone()[0];at=cur.execute('select clock_timestamp()').fetchone()[0]
  read=lambda t:cur.execute('select cp7_fabric_native.source(%s::jsonb,%s)',(json.dumps(source['facts']['products']),t)).fetchone()[0]
  early=read(at);same=read(at+timedelta(minutes=1));active=read(now+timedelta(hours=1,seconds=1));expired=read(now+timedelta(hours=2))
  assert {k:v for k,v in early.items()if k!='captured_at'}=={k:v for k,v in same.items()if k!='captured_at'}
  assert not any(r['target_key']==f['target']for r in early['selected'])and any(r['id']==out['recipe_id']for r in active['selected'])and not any(r['target_key']==f['target']for r in expired['selected'])
  assert not read(now-timedelta(days=1))['versions']
  return dict(status='PASS',actual_recorded_recipe_half_open_effective_and_known_clocks=True,clock_only_stable_before_transition=True,early_selection=False,expired_selection=False,complete_sources=dict(early=early,active=active,expired=expired))
 def successor():
  f=setup(cur,today);one=save(cur,f['payload']);original=parent.capture(cur,today);old=copy.deepcopy(rows(original,f['target'])[0]);assert D(old['gross']['value'])==170
  q={**f['query'],'run_id':original['run_id']};w=workspace(cur,q);p=copy.deepcopy(f['payload']);p.update(run_id=original['run_id'],source_hash=w['source_hash'],expected_revision=one['revision']);p['config']['qty_per_good_pcs']='3';two=save(cur,p)
  archived=parent.read(cur,original['run_id']);fresh=parent.capture(cur,today);parent.checked(fresh);m=rows(fresh,f['target'])[0]
  assert archived['source_state']=='ARCHIVED_STALE'and archived['analysis']==original['analysis']and D(m['gross']['value'])==255 and two['recipe_id']in m['gross']['assumption_ids'];physical(m,255)
  auth.refused(cur,lambda:cur.execute('update cp7_fabric_native.recipes set reason=%s where id=%s',('rewrite',one['recipe_id'])),'CP7_RUN_IMMUTABLE')
  return dict(status='PASS',original170_immutable_successor255=True,complete_old_row=old,complete_new_row=m)
 def changed():
  f=setup(cur,today);save(cur,f['payload']);original=parent.capture(cur,today);b.api.admin(cur)
  # Native master identity counterfixture, not a fabricated stock/installation
  # event. Stock/cost cache rewrites (every receipt or issue) no longer void a
  # review; a real master field revision still does (P08 successor).
  cur.execute("update erp.materials set material_name=material_name||' (revisi master)'where id=%s",(f['payload']['config']['material_id'],))
  archived=parent.read(cur,original['run_id']);fresh=parent.capture(cur,today);m=rows(fresh,f['target'])[0];assert archived['source_state']=='ARCHIVED_STALE'and archived['analysis']==original['analysis']and m['gross']['state']=='UNKNOWN';unknown(m)
  return dict(status='PASS',Native_master_identity_revision_counterfixture_stales_original=True,unreviewed_new_identity_rate_UNKNOWN=True,complete_material_row=m)
 def strict():
  f=setup(cur,today);before=b.boundary.snapshot(cur)
  for change,error in[({'qty_per_good_pcs':'0'},'CP7_FABRIC_RATE'),({'qty_per_good_pcs':'-1'},'CP7_FABRIC_RATE'),({'unit':'WRONG'},'CP7_FABRIC_NATIVE_MATERIAL_CHANGED'),({'material_hash':'0'*64},'CP7_FABRIC_NATIVE_MATERIAL_CHANGED')]:
   p=copy.deepcopy(f['payload']);p['config'].update(change);auth.refused(cur,lambda p=p:save(cur,p),error)
  key=uuid.uuid4();out=save(cur,f['payload'],key);auth.refused(cur,lambda:save(cur,{**f['payload'],'reason':'changed'},key),'CP7_FABRIC_REQUEST_CHANGED');auth.refused(cur,lambda:save(cur,f['payload']),'CP7_FABRIC_REVISION_CHANGED')
  assert cur.execute('select count(*)from cp7_fabric_native.recipes').fetchone()[0]==1 and cur.execute('select count(*)from cp7_fabric_native.commands').fetchone()[0]==1 and b.boundary.snapshot(cur)==before
  return dict(status='PASS',zero_negative_unit_hash_changed_payload_stale_revision_refused=True,one_recipe_one_request_no_orphan=True,complete_outcome=out)
 def private():
  f=setup(cur,today);other,_=auth.custom_actor(cur);auth.refused(cur,lambda:workspace(cur,f['query'],other),'CP7_ANALYSIS_RUN_UNAVAILABLE')
  from cp7_fabric_verify import verify
  verify(cur)
  return dict(status='PASS',own_analysis_actor_not_foreign=True,private_RLS_ACLs_immutable_tables_and_two_SELECT_only_Native_grants=True,no_Native_DML_grant_or_new_role=True)
 def catalog():
  f=setup(cur,today);q={**f['query'],'material_query':f['workspace']['materials'][0]['sku'],'limit':'1'};w=workspace(cur,q)
  assert len(w['materials'])==min(1,int(w['page']['material_total']))and w['analysis']==f['plan']['original']and w['page']['recipe_history_scope']=='LATEST_50_REVISIONS'
  after=workspace(cur,{**q,'material_offset':w['page']['material_total']});assert not after['materials']
  return dict(status='PASS',explicit_search_true_total_page_no_silent_cap=True,complete_first_page=w,complete_end_page=after)
 return list(zip(IDS['native'],[missing,gross,clock,successor,changed,strict,private,catalog]))

def races(tools,today):
 def prepared(custom=False):
  with tools.connect()as conn,conn.cursor()as cur:
   subject=role=None
   if custom:
    subject,role=auth.custom_actor(cur)
    # The reused Native85 fixture reads cutting options before the fabric race.
    # Grant that initial read, then revoke only fabric's master manage at the
    # observed target wait. Never weaken either production authorization guard.
    for permission in('master.product.manage','production.cutting.view'):
     cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,permission))
   f=setup(cur,today,subject);before=plan.monetary_state(cur);conn.commit();return f,subject,role,before
 def waited(revoke=False):
  f,subject,role,before=prepared(revoke);pids=Queue();count=1 if revoke else 2
  def send():
   with tools.connect()as conn,conn.cursor()as cur:
    pids.put(cur.execute('select pg_backend_pid()').fetchone()[0])
    try:r=save(cur,f['payload'],subject=subject);conn.commit();return r
    except psycopg.Error as e:conn.rollback();return dict(error=e.diag.message_primary,sqlstate=e.sqlstate)
  with tools.connect()as holder,holder.cursor()as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:FABRIC:TARGET:'||%s,0))",(f['target'],))
   with ThreadPoolExecutor(max_workers=count)as pool:
    jobs=[pool.submit(send)for _ in range(count)];workers=[pids.get(timeout=5)for _ in range(count)];observed=[]
    try:
     with tools.connect(autocommit=True)as inspector,inspector.cursor()as cur:
      deadline=time.monotonic()+12
      while time.monotonic()<deadline:
       observed=cur.execute("select pid,locktype,database,classid,objid,objsubid,granted from pg_locks where pid=any(%s)and locktype='advisory'and not granted order by pid",(workers,)).fetchall()
       if len(observed)==count:break
       time.sleep(.05)
      assert len(observed)==count and(count==1 or observed[0][1:]==observed[1][1:]),observed
      if revoke:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='master.product.manage'",(role,))
    finally:holder.commit()
    results=[j.result(45)for j in jobs]
  if revoke:assert results[0].get('sqlstate')=='42501'and results[0].get('error')=='CP7_SCHEDULE_ACCESS_DENIED',results
  else:assert len([r for r in results if r.get('contract_version')=='cp7.fabric-outcome.v1'])==1 and len([r for r in results if r.get('sqlstate')=='40001'and r.get('error')=='CP7_FABRIC_REVISION_CHANGED'])==1,results
  with tools.connect()as conn,conn.cursor()as cur:
   assert cur.execute('select count(*)from cp7_fabric_native.recipes').fetchone()[0]==(0 if revoke else 1)and cur.execute('select count(*)from cp7_fabric_native.commands').fetchone()[0]==(0 if revoke else 1)
   assert plan.monetary_state(cur)==before
  return dict(status='PASS',actual_distinct_backend_pids=workers,exact_waiting_lock_rows=observed,complete_results=results,current_authority_after_observed_wait=revoke,Native_stock_money_HPP_unchanged=True)
 return[(IDS['races'][0],lambda:waited()),(IDS['races'][1],lambda:waited(True))]

def http_cases(http,today):
 def actual():
  owner=http.login('OWNER','p08-fabric-owner');other=http.login('OWNER','p08-fabric-foreign')
  with http.connect()as conn,conn.cursor()as cur:f=setup(cur,today,owner.auth_user_id);before=plan.monetary_state(cur);conn.commit()
  key=str(uuid.uuid4());args=dict(p_payload=f['payload'],p_request=key);one=owner.rpc('erp_cp7_save_fabric_recipe_v1',args);assert one['status']==200,one;assert owner.rpc('erp_cp7_save_fabric_recipe_v1',args)['body']==one['body']
  fresh=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=f['plan']['original']['query'],p_request=str(uuid.uuid4())));assert fresh['status']==200,fresh;parent.checked(fresh['body']);m=rows(fresh['body'],f['target'])[0];assert D(m['gross']['value'])==170;physical(m,170)
  assert other.rpc('erp_cp7_get_fabric_recipe_v1',dict(p_query={**f['query'],'run_id':fresh['body']['run_id']}))['status']==403 and http.anon_rpc('erp_cp7_save_fabric_recipe_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:assert plan.monetary_state(cur)==before;cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_save_fabric_recipe_v1',args)['status']==403
  return dict(status='PASS',actual_Auth_HTTP_same_UUID_one_recipe_gross170=True,foreign_anonymous_current_deactivation_denied=True,Native_stock_money_HPP_unchanged=True,complete_material_row=m)
 return[(IDS['http'][0],actual)]
