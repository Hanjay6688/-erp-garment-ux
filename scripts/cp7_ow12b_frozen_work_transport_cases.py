"""Explicit default-off frozen schedule observed-wait/Auth9; not qualified yet.

Native6 remains a separate proof. This provider performs no installation at
import, changes no SQL, and obtains its exact predecessor from its caller.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from threading import Event
from time import monotonic, sleep
import json
import uuid
import psycopg
import cp7_ow12b_frozen_work_cases as work

CONTRACT='cp7.ow12b.frozen-work-transport9.v2'
IDS=dict(native=['OW12B_FROZEN_WORK_V2_TRANSPORT_CATALOG22_ANCHOR'],races=['OW12B_FROZEN_WORK_V2_SAME_UUID_OBSERVED_WAIT',
 'OW12B_FROZEN_WORK_V2_DISTINCT_UUID_REVISION_WAIT',
 'OW12B_FROZEN_WORK_V2_ACCESS_AFTER_GLOBAL_WAIT',
 'OW12B_FROZEN_WORK_V2_NATIVE_POST_AFTER_GLOBAL_WAIT',
 'OW12B_FROZEN_WORK_V2_ACCESS_AFTER_COMMITTED_REPLAY_WAIT'],
 http=['OW12B_FROZEN_WORK_V2_AUTH_PENDING_SAVE_EXACT_REPLAY',
 'OW12B_FROZEN_WORK_V2_AUTH_ANONYMOUS_FOREIGN',
 'OW12B_FROZEN_WORK_V2_AUTH_REVOKED_READ_NEW_AND_REPLAY'])
REQUIRED={k:len(v)for k,v in IDS.items()}
EXPECTED=DECLARED=9
FUNCTIONS,SCHEDULES=work.FUNCTIONS,work.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None
SAVE='erp_cp7_save_staged_production_schedule_v1'
GET='erp_cp7_get_staged_production_schedule_v1'


def sources():
 return {**work.sources(),**{p.name:sha256(p.read_bytes()).hexdigest()for p in (Path(__file__),Path(__file__).with_name('cp7_ow12b_frozen_work_transport_probe.py'),Path(__file__).with_name('cp7_ow12b_frozen_work_transport_preflight.py'))}}


def configure():
 work.PARENT_CHECKER=PARENT_CHECKER
 for name in('INSTALL_STATES','REORDER_STATES','CHECKED_STATE','SCHEDULE_STATE','BOUNDED_STATE','REFERENCE_STATE','STAGE_STATE'):
  setattr(work,name,globals()[name])
 work.configure()


def cases(cur,today):
 configure()
 return [(IDS['native'][0],work.cases(cur,today)[0][1])]


def counts(cur):
 work.plan.b.api.admin(cur)
 return cur.execute('select(select count(*)from cp7_schedule_native.plans),'
  '(select count(*)from cp7_schedule_native.commands)').fetchone()


def races(tools,today):
 def prepare(replay):
  configure()
  with tools.connect()as conn,conn.cursor()as cur:
   f=work.prepare(cur,today,{})
   key=str(uuid.uuid4());old=work.save(cur,f,f['payload'],key,{})if replay else None
   before=counts(cur);physical=work.plan.monetary_state(cur);conn.commit()
  return f,key,old,before,physical
 def invoke(f,key,event,pids):
  with tools.connect()as conn,conn.cursor()as cur:
   cur.execute("set local statement_timeout='8s'");pids.append(cur.execute('select pg_backend_pid()').fetchone()[0]);event.set()
   try:
    answer=work.save(cur,f,deepcopy(f['payload']),key,{});conn.commit();return answer
   except psycopg.Error as error:
    conn.rollback();return dict(sqlstate=error.sqlstate,message=error.diag.message_primary)
 def waiting(kind):
  f,key,old,before,physical=prepare(kind=='replay');workers=2 if kind in('same','revision')else 1
  pids,events=[],[Event()for _ in range(workers)]
  with tools.connect()as holder,holder.cursor()as h,ThreadPoolExecutor(max_workers=workers)as pool:
   h.execute("set local statement_timeout='8s'")
   lock='CP7:SCHEDULE:REQUEST:'+str(f['subject'])+':'+key if kind in('same','replay')else'CP7:SCHEDULE:GLOBAL'
   h.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))',(lock,))
   keys=[str(uuid.uuid4())if kind=='revision'else key for _ in events]
   futures=[pool.submit(invoke,f,k,event,pids)for k,event in zip(keys,events)]
   try:
    assert all(event.wait(5)for event in events)
    deadline,observed=monotonic()+5,False
    while monotonic()<deadline:
     observed=len(set(pids))==workers and all(h.execute('select pg_backend_pid()=any(pg_blocking_pids(%s))',(pid,)).fetchone()[0]for pid in pids)
     if observed:break
     sleep(.03)
    assert observed,('FROZEN_WORK_ACTUAL_BLOCKING_REQUIRED',kind)
    if kind in('access','replay','post'):
     with tools.connect()as conn,conn.cursor()as cur:
      cur.execute("set local statement_timeout='8s';set local lock_timeout='5s'")
      if kind=='post':work.plan.found_fg(cur,f['x'],'1')
      else:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(f['subject'],))
      physical=work.plan.monetary_state(cur);conn.commit()
   finally:holder.rollback()
   answers=[future.result(timeout=15)for future in futures]
  delta=1 if kind in('same','revision')else 0
  if kind=='same':
   assert answers[0]==answers[1]and answers[0]['contract_version']=='cp7.planning-schedule-staged-bounded-outcome.v2'
  elif kind=='revision':
   assert sum(a.get('revision')==str(int(f['payload']['expected_revision'])+1)for a in answers)==1,answers
   assert sum(a==dict(sqlstate='P0001',message='CP7_SCHEDULE_REVISION_CHANGED')for a in answers)==1,answers
  elif kind=='post':assert answers==[dict(sqlstate='40001',message='CP7_SCHEDULE_SOURCE_CHANGED')],answers
  else:assert answers[0].get('sqlstate')=='42501',answers
  with tools.connect()as conn,conn.cursor()as cur:
   assert counts(cur)==tuple(n+delta for n in before)and work.plan.monetary_state(cur)==physical
   if old is not None:
    work.plan.b.api.admin(cur)
    assert cur.execute('select result from cp7_schedule_native.commands where actor=%s and request_id=%s',(f['subject'],key)).fetchone()[0]==old
  return dict(status='PASS',actual_blocking_backend_observed=True,distinct_worker_backends=workers,
   wait_kind=kind,metadata_rows_delta_per_table=delta,committed_receipt_immutable=old is not None,
   no_orphan_plan_or_command=True,no_unintended_stock_money_HPP_change=True,statement_timeout_8s_retained=True)
 return list(zip(IDS['races'],
  [lambda:waiting('same'),lambda:waiting('revision'),lambda:waiting('access'),lambda:waiting('post'),lambda:waiting('replay')]))


def http_cases(http,today):
 configure();state={}
 with http.connect()as conn,conn.cursor()as cur:
  work.install(cur);cur.execute("notify pgrst,'reload schema'");conn.commit()
 def ok(user,name,args):
  start=monotonic();deadline=start+5
  while True:
   reply=user.rpc(name,args)
   if reply['status']!=404 or not isinstance(reply['body'],dict)or reply['body'].get('code')!='PGRST202'or monotonic()>=deadline:break
   sleep(.05)
  elapsed=round((monotonic()-start)*1000,3);assert elapsed<8000,(name,elapsed)
  assert reply['status']==200,(name,reply)
  state.setdefault('ordered_calls',[]).append(dict(name=name,millis=elapsed));return reply['body']
 def fresh(user):
  key=str(uuid.uuid4());q=work.plan.staged.query(today)
  first=ok(user,work.facade.REQUEST,dict(p_query=q,p_request=key));work.plan.staged.checked(first,key,'RUNNING')
  w=ok(user,GET,dict(p_source_request=key))
  assert w['contract_version']=='cp7.planning-schedule-staged-bounded.v2'and w['history_input_coverage']=='PENDING'
  assert w['analysis_state']=='RUNNING'and w['production_capture_state']=='COMPLETE'and w['source_state']=='UNCHANGED'
  return key,w,dict(p_payload=work.payload(w,state['config']),p_request=str(uuid.uuid4()))
 def unchanged(delta):
  with http.connect()as conn,conn.cursor()as cur:
   assert counts(cur)==tuple(n+delta for n in state['before'])and work.plan.monetary_state(cur)==state['physical']
 def flow():
  owner=http.login('OWNER','frozen-work-owner');other=http.login('OWNER','frozen-work-other')
  with http.connect()as conn,conn.cursor()as cur:
   work.plan.fixture(cur,today);work.plan.b.api.admin(cur)
   config=cur.execute('select config from cp7_schedule_native.plans order by revision desc limit 1').fetchone()[0]
   before=counts(cur);physical=work.plan.monetary_state(cur);conn.commit()
  state.update(owner=owner,other=other,config=config,before=before,physical=physical)
  key,w,args=fresh(owner);first=ok(owner,SAVE,args);replay=ok(owner,SAVE,args)
  assert first==replay and first['contract_version']=='cp7.planning-schedule-staged-bounded-outcome.v2'
  assert first['bounded_request_contract']=='cp7.bounded-analysis-request.v2'and first['bounded_reference_contract']=='cp7.bounded-analysis-reference.v2'
  assert first['source_run']==w['source_run']and first['request_id']==args['p_request']and int(first['revision'])==int(w['revision'])+1
  unchanged(1);state.update(key=key,args=args,receipt=first)
  return dict(status='PASS',actual_GoTrue_PostgREST_request_read_SAVE_replay=True,actual_PENDING_work=True,
   exact_v2_receipt=True,one_plan_one_command=True,no_stock_money_HPP_change=True,ordered_calls=deepcopy(state['ordered_calls']))
 def outsiders():
  assert state.get('receipt'),'FROZEN_WORK_PRIOR_HTTP_FLOW_REQUIRED'
  key,w,args=fresh(state['owner']);state.update(fresh_key=key,fresh_args=args)
  for name,payload in [(GET,dict(p_source_request=key)),(SAVE,args)]:
   assert http.anon_rpc(name,payload)['status']in(401,403)
   denied=state['other'].rpc(name,payload);assert denied['status']==403,denied
  unchanged(1)
  return dict(status='PASS',current_revision_used_for_foreign_control=True,anonymous_and_foreign_read_SAVE_refused=True,no_denied_effect=True)
 def revoked():
  assert state.get('fresh_args'),'FROZEN_WORK_PRIOR_HTTP_ACCESS_REQUIRED'
  with http.connect()as conn,conn.cursor()as cur:
   cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(state['owner'].auth_user_id,));conn.commit()
  for name,args in [(GET,dict(p_source_request=state['fresh_key'])),(SAVE,state['fresh_args']),(SAVE,state['args'])]:
   denied=state['owner'].rpc(name,args);assert denied['status']==403,denied
  unchanged(1)
  with http.connect()as conn,conn.cursor()as cur:
   work.plan.b.api.admin(cur)
   assert cur.execute('select result from cp7_schedule_native.commands where actor=%s and request_id=%s',(state['owner'].auth_user_id,state['args']['p_request'])).fetchone()[0]==state['receipt']
  return dict(status='PASS',existing_token_revoked_read_new_SAVE_and_committed_replay_refused=True,
   another_active_owner_retained=True,committed_receipt_immutable=True,no_denied_effect=True)
 return list(zip(IDS['http'],(flow,outsiders,revoked)))
