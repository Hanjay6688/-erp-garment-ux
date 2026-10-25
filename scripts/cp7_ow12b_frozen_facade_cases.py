"""Prepared public-v2 Native/access/transport controls; not wired or qualified."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path
from threading import Event
from time import monotonic, sleep
import json
import traceback
import uuid
import psycopg
import cp7_frozen_analysis_facade_v2 as stage
import cp7_ow12b_frozen_units_cases as native
from cp7_ow04_restore_bundle import _catalog_rows

plan, bounded = native.plan, native.bounded
REQUEST = 'erp_cp7_request_bounded_staged_analysis_v2'
CONTRACT = 'cp7.ow12b.frozen-facade-transport.v2'
IDS = dict(native=[
 'OW12B_FROZEN_FACADE_V2_CATALOG22_EXACT_PREUSE',
 'OW12B_FROZEN_FACADE_V2_PUBLIC_REQUEST_UNITS_REPLAY',
 'OW12B_FROZEN_FACADE_V2_CURRENT_ACCESS_USED_INVERSE'], races=[
 'OW12B_FROZEN_FACADE_V2_SAME_UUID_OBSERVED_WAIT',
 'OW12B_FROZEN_FACADE_V2_ACCESS_AFTER_SOURCE_WAIT',
 'OW12B_FROZEN_FACADE_V2_ACCESS_AFTER_REPLAY_WAIT'], http=[
 'OW12B_FROZEN_FACADE_V2_AUTH_REQUEST_ALL_PAGES',
 'OW12B_FROZEN_FACADE_V2_AUTH_REVOKED_FOREIGN_ANONYMOUS'])
REQUIRED = {k: len(v) for k, v in IDS.items()}
EXPECTED = DECLARED = sum(REQUIRED.values())
FUNCTIONS = (*native.FUNCTIONS, REQUEST)
SCHEDULES = native.SCHEDULES
INSTALL_STATES, REORDER_STATES, CHECKED_STATE, SCHEDULE_STATE, BOUNDED_STATE, REFERENCE_STATE, STAGE_STATE = {}, {}, {}, {}, {}, {}, {}
PARENT_CHECKER = None


def sources():
 return {**native.sources(), **{'cp7_frozen_analysis_facade_v2/'+k: v for k, v in stage.sources().items()},
  Path(__file__).name: sha256(Path(__file__).read_bytes()).hexdigest()}


def install(cur):
 native.PARENT_CHECKER = PARENT_CHECKER
 for name in ('INSTALL_STATES','REORDER_STATES','CHECKED_STATE','SCHEDULE_STATE','BOUNDED_STATE','REFERENCE_STATE','STAGE_STATE'):
  setattr(native, name, globals()[name])
 parents = native.install(cur)
 own = stage.install_delta(cur, lambda c: native.stage.verify(c, parents['current']))
 return dict(parents=parents, current=own)


def request(cur, q, key, actor):
 return plan.staged.limited(cur, REQUEST, (json.dumps(q), key), actor)


def count(cur, actor):
 plan.b.api.admin(cur)
 return cur.execute('select count(*)from cp7_analysis_stage.jobs where actor=%s', (actor,)).fetchone()[0]


def capture(cur, today, actor):
 q, key = plan.staged.query(today), str(uuid.uuid4())
 initial = request(cur, q, key, actor)
 plan.staged.checked(initial, key, 'RUNNING')
 row = plan.staged.job_row(cur, key, actor)
 assert initial['units_done'] == 0 and native.coverage(cur, row['id']) == 'PENDING'
 f = dict(key=key, initial=initial, row=row, subject=actor)
 w = bounded.work.get(cur, key, actor)
 assert w['contract_version'] == 'cp7.planning-schedule-staged-bounded.v2'
 assert w['history_input_coverage'] == 'PENDING' and w['source_state'] == 'UNCHANGED'
 bounded.finish(cur, f)
 assert native.coverage(cur, row['id']) == 'COMPLETE'
 assert native.prepared_cache(cur, row['id'])['inputs'] == native.frozen.original_compile(cur, row['reference'], q, {})
 assert request(cur, q, key, actor) == f['done']
 return f


def cases(cur, today):
 def catalog():
  before = _catalog_rows(cur); s = install(cur)
  verified = stage.verify(cur, s['current'])
  assert (verified['new_public_rpcs'], verified['new_tables'], verified['existing_replacements']) == (1, 0, 0)
  cur.execute("create view public.frozen_facade_inverse_guard as select public."+REQUEST+"(null::jsonb,null::uuid)value")
  held = _catalog_rows(cur)
  cur.execute('savepoint frozen_facade_view_guard')
  try: stage.rollback_preuse(cur, s['current'])
  except psycopg.Error as error:
   assert error.sqlstate == '2BP01'; cur.execute('rollback to savepoint frozen_facade_view_guard')
  else: raise AssertionError('FROZEN_FACADE_DEPENDENT_VIEW_NOT_REFUSED')
  finally: cur.execute('release savepoint frozen_facade_view_guard')
  assert _catalog_rows(cur) == held
  cur.execute('drop view public.frozen_facade_inverse_guard')
  stage.rollback_preuse(cur, s['current']); native.unwind(cur, s['parents'])
  assert _catalog_rows(cur) == before
  return dict(status='PASS', exact22_composed_inverse=True, dependent_view_refused_atomically=True,
   one_explicit_authenticated_facade_no_old_replacement=True)
 def flow():
  install(cur); plan.fixture(cur, today)
  actor = native.native.policy.master.role_actor(cur, 'OWNER')
  physical = plan.monetary_state(cur); f = capture(cur, today, actor)
  q = f['row']['query']; key = f['key']
  plan.refused(cur, lambda: request(cur, {**q, 'group_mode': 'RESTATED' if q['group_mode']=='AS_SOLD' else 'AS_SOLD'}, key, actor), 'CP7_ANALYSIS_REQUEST_CHANGED')
  plan.refused(cur, lambda: bounded.request(cur, today, key, actor), 'CP7_ANALYSIS_REQUEST_CHANGED')
  plan.refused(cur, lambda: request(cur, dict(initial_auto='ENSURE'), str(uuid.uuid4()), actor), 'CP7_WIP_FIELDS')
  assert count(cur, actor) == 1 and plan.monetary_state(cur) == physical
  assert plan.staged.job_row(cur, key, actor)['reference'] == f['row']['reference']
  return dict(status='PASS', real_public_v2_request_and_unchanged_public_steps_pages=True,
   whole_cached_inputs_equal_unchanged_compiler=True, actual_pending_then_complete_coverage=True,
   exact_method_query_UUID_replay=True, reference_immutable=True, no_ERP_write=True,
   step_millis=[c['ms'] for c in f['calls']], page_count=f['pages']['page_count'])
 def access():
  s = install(cur); plan.fixture(cur, today)
  actor = native.native.policy.master.role_actor(cur, 'OWNER'); f = capture(cur, today, actor)
  held = _catalog_rows(cur)
  try: stage.rollback_preuse(cur, s['current'])
  except ValueError as error: assert str(error) == 'FROZEN_FACADE_AFTER_USE_REQUIRES_COMPOSED_BACKUP_RESTORE'
  else: raise AssertionError('FROZEN_FACADE_USED_INVERSE_ACCEPTED')
  assert _catalog_rows(cur) == held
  cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (actor,))
  for operation in (lambda: request(cur, f['row']['query'], f['key'], actor),
                    lambda: plan.staged.step(cur, f['key'], actor), lambda: bounded.work.get(cur, f['key'], actor)):
   assert plan.refusal(cur, operation)[0] == '42501'
  assert count(cur, actor) == 1
  return dict(status='PASS', used_inverse_refused_before_DDL=True, current_access_rechecked_on_replay_step_workspace=True)
 def checked(fn):
  def run():
   try: return fn()
   except Exception as error: return dict(status='INCOMPLETE', error=str(error), traceback=traceback.format_exc(), production_go=False)
  return run
 return list(zip(IDS['native'], map(checked, (catalog, flow, access))))


def races(tools, today):
 def prepare(replay=False):
  with tools.connect() as conn, conn.cursor() as cur:
   install(cur); plan.fixture(cur, today)
   actor = str(native.native.policy.master.role_actor(cur, 'OWNER'))
   q, key = plan.staged.query(today), str(uuid.uuid4())
   old = request(cur, q, key, actor) if replay else None
   before, physical = count(cur, actor), plan.monetary_state(cur); conn.commit()
  return q, key, actor, old, before, physical
 def call(q, key, actor, started, pids):
  with tools.connect() as conn, conn.cursor() as cur:
   cur.execute("set local statement_timeout='8s'")
   pids.append(cur.execute('select pg_backend_pid()').fetchone()[0]); started.set()
   try:
    result = request(cur, q, key, actor); conn.commit(); return result
   except psycopg.Error as error:
    conn.rollback(); return dict(sqlstate=error.sqlstate, message=error.diag.message_primary)
 def waiting(kind):
  q, key, actor, old, before, physical = prepare(kind=='replay')
  workers = 2 if kind=='same' else 1
  pids, events = [], [Event() for _ in range(workers)]
  with tools.connect() as holder, holder.cursor() as h, ThreadPoolExecutor(max_workers=workers) as pool:
   if kind=='source': h.execute('lock table erp.products in access exclusive mode')
   else: h.execute('select pg_advisory_xact_lock(hashtextextended(%s,0))', ('CP7:ANALYSIS-REQUEST:'+actor+':'+key,))
   futures = [pool.submit(call, q, key, actor, event, pids) for event in events]
   try:
    assert all(event.wait(5) for event in events)
    deadline, observed = monotonic()+5, False
    while monotonic() < deadline:
     observed = len(set(pids)) == workers and all(h.execute('select pg_backend_pid()=any(pg_blocking_pids(%s))', (pid,)).fetchone()[0] for pid in pids)
     if observed: break
     sleep(.03)
    assert observed, ('FROZEN_FACADE_ACTUAL_WAIT_REQUIRED', kind)
    if kind!='same': h.execute('update erp.app_users set is_active=false where auth_user_id=%s', (actor,))
    holder.commit()
   finally: holder.rollback()
   answers = [future.result(timeout=15) for future in futures]
  if kind=='same':
   assert answers[0] == answers[1]
   plan.staged.checked(answers[0], key, 'RUNNING')
  else: assert answers[0].get('sqlstate') == '42501', answers
  with tools.connect() as conn, conn.cursor() as cur:
   assert count(cur, actor) == before+(1 if kind=='same' else 0)
   assert plan.monetary_state(cur) == physical
   if old is not None:
    plan.b.api.admin(cur)
    assert cur.execute('select units_done from cp7_analysis_stage.jobs where actor=%s and request_id=%s', (actor,key)).fetchone()[0] == 0
  return dict(status='PASS', actual_blocking_backend_observed=True, distinct_worker_backends=workers,
   same_UUID_one_job=kind=='same', current_access_after_source_wait=kind=='source',
   current_access_after_committed_replay_wait=kind=='replay', no_orphan_job_or_ERP_effect=True)
 return list(zip(IDS['races'], (lambda: waiting('same'), lambda: waiting('source'), lambda: waiting('replay'))))


def http_cases(http, today):
 state = {}
 with http.connect() as conn, conn.cursor() as cur:
  install(cur); cur.execute("notify pgrst,'reload schema'"); conn.commit()
 def ok(user, name, payload):
  deadline = monotonic()+5
  while True:
   r = user.rpc(name, payload)
   if r['status']!=404 or not isinstance(r['body'],dict) or r['body'].get('code')!='PGRST202' or monotonic()>=deadline: break
   sleep(.05)
  assert r['status'] == 200, (name, r)
  return r['body']
 def flow():
  owner = http.login('OWNER', 'frozen-v2-owner')
  other = http.login('OWNER', 'frozen-v2-other')
  with http.connect() as conn, conn.cursor() as cur:
   plan.fixture(cur, today); physical = plan.monetary_state(cur); conn.commit()
  q, key = plan.staged.query(today), str(uuid.uuid4()); args = dict(p_query=q, p_request=key)
  first = ok(owner, REQUEST, args); plan.staged.checked(first, key, 'RUNNING')
  assert ok(owner, REQUEST, args) == first
  job, calls = first, 0
  while job['state']=='RUNNING':
   assert calls < plan.staged.DRIVER_CALLS
   job = ok(owner, 'erp_cp7_step_staged_analysis_v1', dict(p_request=key)); calls += 1
  assert job['state']=='DONE' and ok(owner, REQUEST, args)==job
  pages = ok(owner, 'erp_cp7_read_staged_analysis_pages_v1', dict(p_run=job['run_id']))
  bodies = [ok(owner, 'erp_cp7_read_staged_analysis_page_v1', dict(p_run=job['run_id'], p_index=i, p_access=pages['access_epoch'])) for i in range(pages['page_count'])]
  assert all(plan.staged.sha(e['body'])==e['sha256'] and e['identity_hash']==pages['identity_hash'] for e in bodies)
  assert pages['identity_hash']==plan.staged.sha(pages['header']['sha256']+'\n'+'\n'.join(e['sha256'] for e in bodies))
  with http.connect() as conn, conn.cursor() as cur:
   assert count(cur, owner.auth_user_id)==1 and plan.monetary_state(cur)==physical
   row = plan.staged.job_row(cur, key, owner.auth_user_id)
   assert row['reference']['bounded_history_inputs'] is None and native.coverage(cur, row['id'])=='COMPLETE'
  state.update(owner=owner, other=other, key=key, args=args, run=job['run_id'], epoch=pages['access_epoch'])
  return dict(status='PASS', actual_GoTrue_PostgREST=True, exact_public_v2_replay=True,
   all_actual_pages_hash_checked=True, actual_HTTP_steps=calls, no_ERP_write=True)
 def access():
  assert state, 'FROZEN_FACADE_PRIOR_HTTP_FLOW_REQUIRED'
  owner, other = state['owner'], state['other']
  endpoints = [(REQUEST, state['args']), ('erp_cp7_step_staged_analysis_v1',dict(p_request=state['key'])),
   ('erp_cp7_get_staged_analysis_v1',dict(p_request=state['key'])), ('erp_cp7_read_staged_analysis_pages_v1',dict(p_run=state['run'])),
   ('erp_cp7_read_staged_analysis_page_v1',dict(p_run=state['run'],p_index=0,p_access=state['epoch'])),
   ('erp_cp7_check_staged_analysis_source_v1',dict(p_run=state['run']))]
  assert all(http.anon_rpc(name,args)['status'] in (401,403) for name,args in endpoints)
  assert all(other.rpc(name,args)['status']==403 for name,args in endpoints[3:])
  foreign = other.rpc('erp_cp7_get_staged_analysis_v1',dict(p_request=state['key']))
  assert foreign['status']==400 and 'CP7_ANALYSIS_JOB_UNAVAILABLE' in json.dumps(foreign['body'])
  with http.connect() as conn, conn.cursor() as cur:
   cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,)); conn.commit()
  assert [owner.rpc(name,args)['status'] for name,args in endpoints]==[403]*6
  with http.connect() as conn, conn.cursor() as cur: assert count(cur,owner.auth_user_id)==1
  return dict(status='PASS', actual_existing_token_revoked_all_six_refused=True,
   foreign_pages_source_refused=True, foreign_request_absent=True, anonymous_all_six_refused=True)
 return list(zip(IDS['http'], (flow, access)))
