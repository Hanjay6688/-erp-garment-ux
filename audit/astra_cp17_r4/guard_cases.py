"""Astra independent r4 guard oracles. Synthetic private contexts are explicit
fixtures, not claims that browser users can insert private rows. The product
guard is never replaced; a second function retains its exact predecessor.
"""
import json, uuid, hashlib
import psycopg
import cp7_cp17_fix_cases as f
import cp7_r3_audit_cases as a

NATIVE=['ASTRA_R4_INTERNAL_ROLE_IDENTITY_MATRIX','ASTRA_R4_CONTEXT_IDENTITY_AND_FINE_REFUSAL']
RACE=['ASTRA_R4_UNASSIGNED_XID_AND_CROSS_BACKEND_CONTEXT']
EXPECTED=3
DENIED='P0001:Internal ERP access required'
FINE='42501:CP7_SALES_WRITE_DENIED'

def one(cur,sql,args=()):return cur.execute(sql,args).fetchone()[0]

def prepare(cur):
 f.b.api.admin(cur)
 # Independently isolate the one added top-level block; require byte-exact
 # rest of the installed body, without using the writer's unpatched helper.
 definition=one(cur,"select pg_get_functiondef('erp.require_internal()'::regprocedure)")
 start=definition.index(' -- R4-05 one context probe')
 end=definition.index('\n end if;',start)+len('\n end if;')
 old=definition[:start]+definition[end:]
 assert '-- R4-05' not in old and old.count("if v_jwt_role='service_role' then return;end if;")==1
 cur.execute('create schema astra_r4_guard',prepare=False)
 cur.execute(old.replace('erp.require_internal()', 'astra_r4_guard.prior()',1),prepare=False)
 cur.execute("""create function astra_r4_guard.answer(p_old boolean)returns text language plpgsql
 security definer set search_path=''as $$begin
 if p_old then perform astra_r4_guard.prior();else perform erp.require_internal();end if;
 return 'ALLOW';exception when others then return sqlstate||':'||sqlerrm;end$$;
 revoke all on function astra_r4_guard.prior()from public;
 revoke all on function astra_r4_guard.answer(boolean)from public;
 grant usage on schema astra_r4_guard to authenticated,anon,service_role;
 grant execute on function astra_r4_guard.answer(boolean)to authenticated,anon,service_role;""",prepare=False)
 identities={}
 for code in ('OWNER','ADMIN','STAFF','GUDANG'):
  subject,user=a.person(cur,code,'Astra r4 '+code)
  identities[code]=subject
 # Legacy STAFF is deliberately activated only in this disposable fixture.
 cur.execute("update erp.app_roles set is_active=true where role_code='STAFF'")
 disabled,user=a.person(cur,'ADMIN','Astra disabled')
 cur.execute('update erp.app_users set is_active=false where id=%s',(user,))
 identities.update(DISABLED=disabled,UNKNOWN=str(uuid.uuid4()),NONE=None)
 custom,_=a.custom(cur,['sales.invoice.view'],'Astra sales read only')
 identities['CUSTOM_READ_ONLY']=custom
 return identities,dict(candidate_sha256=hashlib.sha256(definition.encode()).hexdigest(),prior_sha256=hashlib.sha256(old.encode()).hexdigest())

def pair(cur,subject,expected,jwt_role='authenticated',db_role='authenticated'):
 f.b.api.admin(cur)
 claims={'role':jwt_role}
 if subject is not None:claims['sub']=subject
 cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(claims),))
 cur.execute('set session authorization authenticator')
 cur.execute('set local role '+db_role)
 try:
  new=one(cur,'select astra_r4_guard.answer(false)')
  old=one(cur,'select astra_r4_guard.answer(true)')
  assert new==old==expected,(subject,jwt_role,db_role,new,old,expected)
  return dict(candidate=new,predecessor=old,expected=expected)
 finally:
  cur.execute('reset role');cur.execute('reset session authorization');f.b.api.admin(cur)

def cases(cur,today):
 def identities():
  ids,hashes=prepare(cur);observed={}
  for key,subject in ids.items():observed[key]=pair(cur,subject,'ALLOW' if key in ('OWNER','ADMIN','STAFF') else DENIED)
  observed['ANON_NO_USER']=pair(cur,None,DENIED,'anon','anon')
  observed['SERVICE_ROLE_NO_USER']=pair(cur,None,'ALLOW','service_role','service_role')
  return dict(status='PASS',hashes=hashes,observed=observed,fixture_staff_role_activated=True,product_definition_unchanged=True)
 def contexts():
  ids,hashes=prepare(cur);observed={}
  # Same transaction and PID must not lend another actor's context. Foreign
  # backend/transaction must not trigger fine checks in this one. No caching:
  # removing/inserting a context changes the answer on the very next call.
  for state in ('HERE','OTHER_ACTOR','OTHER_TX','OTHER_PID'):
   cur.execute('savepoint astra_context')
   pid,tx=cur.execute('select pg_backend_pid(),txid_current()').fetchone()
   actor=ids['CUSTOM_READ_ONLY'] if state!='OTHER_ACTOR' else ids['OWNER']
   cur.execute("insert into cp7_sales.command_context(backend_pid,transaction_id,actor,action)values(%s,%s,%s,'POST')",(pid+(100000 if state=='OTHER_PID'else 0),tx-(1 if state=='OTHER_TX'else 0),actor))
   observed[state]=pair(cur,ids['CUSTOM_READ_ONLY'],FINE if state=='HERE' else DENIED)
   cur.execute('rollback to savepoint astra_context');cur.execute('release savepoint astra_context')
  observed['AFTER_CONTEXT_REMOVED']=pair(cur,ids['CUSTOM_READ_ONLY'],DENIED)
  # Revoking a permission cannot be hidden by the optimized no-context path.
  role=one(cur,'select role_id from erp.app_users where auth_user_id=%s',(ids['CUSTOM_READ_ONLY'],))
  for key in ('finance.ar.view','sales.invoice.post'):
   cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',(role,key))
  cur.execute("insert into cp7_sales.command_context(backend_pid,transaction_id,actor,action)values(pg_backend_pid(),txid_current(),%s,'POST')",(ids['CUSTOM_READ_ONLY'],))
  observed['GRANTED']=pair(cur,ids['CUSTOM_READ_ONLY'],'ALLOW')
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ar.view'",(role,))
  observed['REVOKED_SAME_TX']=pair(cur,ids['CUSTOM_READ_ONLY'],FINE)
  return dict(status='PASS',hashes=hashes,observed=observed,context_fixture='private rows inserted as disposable setup; not public reachability evidence')
 return list(zip(NATIVE,[identities,contexts]))

def races(tools,today):
 def unassigned():
  with tools.connect()as conn,conn.cursor()as cur:
   ids,hashes=prepare(cur);conn.commit()
  observed={}
  for who,expected in [('OWNER','ALLOW'),('ADMIN','ALLOW'),('STAFF','ALLOW'),('GUDANG',DENIED),('UNKNOWN',DENIED),('NONE',DENIED)]:
   with tools.connect()as conn,conn.cursor()as cur:
    # SET and identity reads must leave xid unassigned before the fast path.
    claims={'role':'authenticated'}
    if ids[who] is not None:claims['sub']=ids[who]
    cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(claims),))
    cur.execute('set session authorization authenticator');cur.execute('set local role authenticated')
    xid_before=one(cur,'select txid_current_if_assigned()')
    assert xid_before is None,('FIXTURE_ALREADY_ASSIGNED_XID',xid_before)
    new=one(cur,'select astra_r4_guard.answer(false)')
    xid_after=one(cur,'select txid_current_if_assigned()')
    old=one(cur,'select astra_r4_guard.answer(true)')
    assert new==old==expected,(who,new,old,expected)
    observed[who]=dict(candidate=new,prior=old,xid_before=xid_before,xid_after_candidate=xid_after)
  # An actually concurrent uncommitted context belongs to a different backend.
  holder=tools.connect()
  try:
   with holder.cursor()as h:
    h.execute("insert into cp7_sales.command_context(backend_pid,transaction_id,actor,action)values(pg_backend_pid(),txid_current(),%s,'POST')",(ids['CUSTOM_READ_ONLY'],))
    pid,tx=h.execute('select pg_backend_pid(),txid_current()').fetchone()
   with tools.connect()as conn,conn.cursor()as cur:
    assert one(cur,"select state from pg_stat_activity where pid=%s",(pid,))=='idle in transaction'
    observed['OTHER_BACKEND_HELD']=pair(cur,ids['CUSTOM_READ_ONLY'],DENIED)
    observed['OTHER_BACKEND_HELD'].update(holder_pid=pid,holder_tx=tx,holder_state='idle in transaction')
   holder.commit()
   with tools.connect()as conn,conn.cursor()as cur:observed['OTHER_BACKEND_COMMITTED']=pair(cur,ids['CUSTOM_READ_ONLY'],DENIED)
  finally:holder.close()
  return dict(status='PASS',hashes=hashes,observed=observed,scope='Native exact guard decisions; synthetic context fixture, no business write or hosted access')
 return [(RACE[0],unassigned)]
