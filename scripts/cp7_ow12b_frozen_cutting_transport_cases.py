"""Frozen checked cutting: actual lock waits and real Auth, disposable copies.

SAVE retains a reviewed draft; it does not post a cutting group or reserve stock.
The repeated Native catalog anchor grants no new feature qualification.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic,sleep
from copy import deepcopy
from decimal import Decimal
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import uuid
import psycopg
import cp7_ow12b_frozen_cutting_cases as native

plan=native.plan
stage=native.facade.stage
CONTRACT='cp7.ow12b.frozen-cutting-transport10.v2'
IDS=dict(native=['OW12B_FROZEN_CUTTING_V2_TRANSPORT_CATALOG22_ANCHOR'],
 races=['OW12B_FROZEN_CUTTING_V2_RACE_SAME_UUID',
        'OW12B_FROZEN_CUTTING_V2_RACE_CHANGED_PAYLOAD_SAME_UUID',
        'OW12B_FROZEN_CUTTING_V2_RACE_ACCESS_AFTER_REQUEST',
        'OW12B_FROZEN_CUTTING_V2_RACE_ACCESS_AFTER_CAPACITY',
        'OW12B_FROZEN_CUTTING_V2_RACE_REPLAY_ACCESS_AFTER_REQUEST',
        'OW12B_FROZEN_CUTTING_V2_RACE_STOCK_AFTER_CAPACITY'],
 http=['OW12B_FROZEN_CUTTING_V2_AUTH_OPTIONS_SAVE_EXACT_REPLAY',
       'OW12B_FROZEN_CUTTING_V2_AUTH_K3_STALE_AND_RECEIPT',
       'OW12B_FROZEN_CUTTING_V2_AUTH_FOREIGN_ANON_CURRENT_REVOKED'])
REQUIRED={k:len(v)for k,v in IDS.items()}
EXPECTED=DECLARED=sum(REQUIRED.values())
assert EXPECTED==10
FUNCTIONS,SCHEDULES=native.FUNCTIONS,native.SCHEDULES
INSTALL_STATES,REORDER_STATES,CHECKED_STATE,SCHEDULE_STATE,BOUNDED_STATE,REFERENCE_STATE,STAGE_STATE={},{},{},{},{},{},{}
PARENT_CHECKER=None
SAVE='erp_cp7_save_cutting_suggestion_v1'
OPTIONS='erp_cp7_get_plan_options_v2'
GROWING=('cp7_plan_native.drafts','cp7_plan_native.staged_drafts','cp7_cutting_checked.receipts')


def sources():
 return {**native.sources(),**{p.name:sha256(p.read_bytes()).hexdigest()for p in
  (Path(__file__),Path(__file__).with_name('cp7_ow12b_frozen_cutting_transport_probe.py'),
   Path(__file__).with_name('cp7_ow12b_frozen_cutting_transport_preflight.py'))}}


def configure():
 native.PARENT_CHECKER=PARENT_CHECKER
 for name in('INSTALL_STATES','REORDER_STATES','CHECKED_STATE','SCHEDULE_STATE','BOUNDED_STATE','REFERENCE_STATE','STAGE_STATE'):
  setattr(native,name,globals()[name])


def install(cur):
 configure();return native.install(cur)


def cases(cur,today):
 configure();return [(IDS['native'][0],native.cases(cur,today)[0][1])]


def prepare_frozen(cur,today,actor):
 x=plan.fixture(cur,today)
 # Keep another active owner when the actual capturing actor is deactivated.
 native.native.native.policy.master.role_actor(cur,'OWNER')
 f=native.facade.capture(cur,today,actor)
 assert f['row']['reference']['bounded_request_contract']=='cp7.bounded-analysis-request.v2'
 o,q,p=plan.draft_payload(cur,x,f['done']['run_id'],actor)
 assert o['production_state']=='ACTIVE'and Decimal(o['needed_pcs'])>=2 and Decimal(o['capacity_pcs'])>=2
 rec=next(r for r in f['original']['analysis']['recommendations']if r['target']['key']==x['target'])
 assert rec['q_conditional']['state']!='UNKNOWN'and Decimal(rec['q_conditional']['value'])==Decimal(o['needed_pcs'])
 assert o['identity_hash']==f['pages']['identity_hash']
 assert datetime.fromisoformat(o['data_as_of'].replace('Z','+00:00'))==datetime.fromisoformat(f['pages']['reference']['captured_at'].replace('Z','+00:00'))
 x.update(run=f['done']['run_id'],key=f['key'],options=o,query=q,payload=p)
 f.update(x=x,payload=native.checked.payload(x));return f


def check(cur,before,delta):
 after=native.metadata(cur)
 assert after['physical']==before['physical']
 for table,value in before['rows'].items():
  if table in GROWING and delta:assert after['rows'][table][0]==value[0]+delta
  else:assert after['rows'][table]==value


def receipt(out,f,key):
 assert out['contract_version']=='cp7.plan-draft.v2'and out['state']=='SAVED'and out['request_id']==key
 g=out['cutting_save_guard']
 assert g['contract_version']=='cp7.cutting-checked-save.v1'and g['feasible']is True
 assert(g['run_id'],g['target_key'],g['identity_hash'])==(f['done']['run_id'],f['x']['target'],f['pages']['identity_hash'])
 assert out['production_go']is False


def races(tools,today):
 def prepare(replay=False):
  with tools.connect()as conn,conn.cursor()as cur:
   install(cur);actor=native.native.native.policy.master.role_actor(cur,'OWNER')
   f=prepare_frozen(cur,today,actor);key=str(uuid.uuid4())
   if replay:f['committed_receipt']=native.save(cur,f,key,{})
   before=native.metadata(cur);conn.commit()
  return f,key,before

 def save(f,key,p,backends,started):
  with tools.connect()as conn,conn.cursor()as cur:
   cur.execute("set local statement_timeout='8s'")
   backends.append(cur.execute('select pg_backend_pid()').fetchone()[0]);started.set()
   try:
    answer=native.save(cur,f,key,{},p=p);conn.commit();return answer
   except psycopg.Error as error:
    conn.rollback();return dict(sqlstate=error.sqlstate,message=error.diag.message_primary)

 def observed_wait(h,backends,number):
  deadline=monotonic()+5
  while monotonic()<deadline:
   if len(set(backends))==number and all(h.execute('select pg_backend_pid()=any(pg_blocking_pids(%s))',(pid,)).fetchone()[0]for pid in backends):return True
   sleep(.03)
  raise AssertionError('FROZEN_CUTTING_ACTUAL_BLOCKED_WORKERS_REQUIRED')

 def simultaneous(changed):
  f,key,before=prepare();backends=[];events=[Event(),Event()]
  payloads=[deepcopy(f['payload']),dict(f['payload'],reason='Other reviewed reason')if changed else deepcopy(f['payload'])]
  with tools.connect()as holder,holder.cursor()as h,ThreadPoolExecutor(max_workers=2)as pool:
   h.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))',('CP7:PLAN_SAVE:'+f['subject']+':'+key,))
   futures=[pool.submit(save,f,key,p,backends,e)for p,e in zip(payloads,events)]
   try:
    assert all(e.wait(5)for e in events);observed_wait(h,backends,2)
   finally:holder.rollback()
   answers=[future.result(timeout=15)for future in futures]
  if changed:
   wins=[a for a in answers if a.get('state')=='SAVED'];assert len(wins)==1,answers;receipt(wins[0],f,key)
   assert sum(a==dict(sqlstate='P0001',message='CP7_PLAN_REQUEST_CHANGED')for a in answers)==1,answers
  else:
   assert answers[0]==answers[1];receipt(answers[0],f,key)
  with tools.connect()as conn,conn.cursor()as cur:check(cur,before,1)
  return dict(status='PASS',two_actual_backends_blocked=True,same_UUID_exact_replay=not changed,
   changed_payload_same_UUID_one_winner=changed,one_draft_snapshot_and_checked_receipt=True,
   no_Native_group_intent_or_physical_effect=True)

 def waiting(lock,replay=False,stock=False):
  f,key,before=prepare(replay);started=Event();backends=[]
  lock_key='CP7:PLAN_SAVE:'+f['subject']+':'+key if lock=='request'else'CP7:PLAN_CAPACITY'
  with tools.connect()as holder,holder.cursor()as h,ThreadPoolExecutor(max_workers=1)as pool:
   h.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))',(lock_key,))
   future=pool.submit(save,f,key,deepcopy(f['payload']),backends,started)
   try:
    assert started.wait(5);observed_wait(h,backends,1)
    if stock:plan.found_fg(h,f['x'],'1')
    else:h.execute('update erp.app_users set is_active=false where auth_user_id=%s',(f['subject'],))
    # Only the deliberately posted Native stock is allowed to differ.
    before['physical']=plan.monetary_state(h);holder.commit()
   finally:holder.rollback()
   answer=future.result(timeout=15)
  if stock:assert answer==dict(sqlstate='40001',message='CP7_CUTTING_SUGGESTION_SOURCE_CHANGED'),answer
  else:assert answer.get('sqlstate')=='42501',answer
  with tools.connect()as conn,conn.cursor()as cur:
   check(cur,before,0)
   if replay:assert cur.execute('select result from cp7_cutting_checked.receipts where actor=%s and request_id=%s',(f['subject'],key)).fetchone()[0]==f['committed_receipt']
  return dict(status='PASS',actual_lock_wait_observed=lock,committed_replay_wait=replay,
   current_access_revoked_during_wait=not stock,actual_Native_stock_post_during_wait=stock,
   no_denied_draft_snapshot_receipt_or_physical_effect=True)

 return list(zip(IDS['races'],[lambda:simultaneous(False),lambda:simultaneous(True),
  lambda:waiting('request'),lambda:waiting('capacity'),lambda:waiting('request',replay=True),
  lambda:waiting('capacity',stock=True)]))


def http_cases(http,today):
 with http.connect()as conn,conn.cursor()as cur:
  state=install(cur);cur.execute("notify pgrst,'reload schema'");conn.commit()

 def prepare(label):
  user=http.login('OWNER',label)
  with http.connect()as conn,conn.cursor()as cur:
   stage.verify(cur,state['current']);f=prepare_frozen(cur,today,user.auth_user_id)
   before=native.metadata(cur);conn.commit()
  return user,f,dict(p_payload=f['payload'],p_request=str(uuid.uuid4())),before

 def options(user,f):
  deadline=monotonic()+5
  while True:
   r=user.rpc(OPTIONS,dict(p_query=f['x']['query']))
   if r['status']!=404 or not isinstance(r['body'],dict)or r['body'].get('code')!='PGRST202'or monotonic()>=deadline:return r
   sleep(.05)

 def unchanged(before,delta):
  with http.connect()as conn,conn.cursor()as cur:check(cur,before,delta)

 def flow():
  user,f,args,before=prepare('frozen-cutting-flow')
  o=options(user,f);assert o['status']==200 and o['body']==f['x']['options'],o
  first=user.rpc(SAVE,args);repeat=user.rpc(SAVE,args)
  assert first['status']==repeat['status']==200 and first['body']==repeat['body'],(first,repeat)
  receipt(first['body'],f,args['p_request'])
  changed=user.rpc(SAVE,dict(args,p_payload=dict(f['payload'],reason='changed same UUID')))
  assert changed['status']!=200 and changed['body']['message']=='CP7_PLAN_REQUEST_CHANGED',changed
  unchanged(before,1)
  return dict(status='PASS',real_Auth_options_match_complete_Native_source=True,
   checked_SAVE_exact_replay=True,changed_payload_refused=True,one_draft_snapshot_checked_receipt=True,
   no_Native_group_intent_stock_money_HPP_effect=True)

 def stale():
  user,f,args,before=prepare('frozen-cutting-stale');assert options(user,f)['status']==200
  with http.connect()as conn,conn.cursor()as cur:
   purged=cur.execute('select cp7_analysis_stage.purge_intermediates(%s)',(f['row']['id'],)).fetchone()[0]
   assert purged['removed']['target_rows']>0;conn.commit()
  o=options(user,f);assert o['status']==200 and o['body']==f['x']['options'],o
  first=user.rpc(SAVE,args);assert first['status']==200,first;receipt(first['body'],f,args['p_request'])
  with http.connect()as conn,conn.cursor()as cur:
   plan.found_fg(cur,f['x'],'1');before['physical']=plan.monetary_state(cur);conn.commit()
  denied=user.rpc(SAVE,dict(args,p_request=str(uuid.uuid4())))
  assert denied['status']==500 and denied['body']['code']=='40001'and denied['body']['message']=='CP7_CUTTING_SUGGESTION_SOURCE_CHANGED',denied
  repeat=user.rpc(SAVE,args);assert repeat['status']==200 and repeat['body']==first['body'],repeat
  unchanged(before,1)
  return dict(status='PASS',actual_K3_options_and_checked_SAVE=True,actual_Native_stock_post_stale_newSAVE_refused=True,
   committed_receipt_exact_after_post=True,no_unexpected_metadata_or_physical_effect=True)

 def access():
  user,f,args,before=prepare('frozen-cutting-access');assert options(user,f)['status']==200
  other=http.login('OWNER','frozen-cutting-foreign')
  assert options(other,f)['status']==403
  assert other.rpc(SAVE,args)['status']==403
  assert http.anon_rpc(OPTIONS,dict(p_query=f['x']['query']))['status']in(401,403)
  assert http.anon_rpc(SAVE,args)['status']in(401,403)
  unchanged(before,0)
  first=user.rpc(SAVE,args);assert first['status']==200,first
  with http.connect()as conn,conn.cursor()as cur:
   cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(user.auth_user_id,));conn.commit()
  assert options(user,f)['status']==403
  assert user.rpc(SAVE,args)['status']==403
  assert user.rpc(SAVE,dict(args,p_request=str(uuid.uuid4())))['status']==403
  unchanged(before,1)
  return dict(status='PASS',real_foreign_and_anonymous_options_SAVE_refused=True,
   old_token_current_revoked_options_newSAVE_committed_replay_refused=True,no_denied_effect=True)

 return list(zip(IDS['http'],[flow,stale,access]))
