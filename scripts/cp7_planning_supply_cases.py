"""Real native postings and global source oracles; no fake business insertion."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json,threading,time,uuid
import psycopg
import cp7_planning_baseline_cases as baseline
import cp7_wip_production_cases as production
auth=baseline.auth
b=baseline.b

def capture(cur,today,key=None,subject=None):
 return capture_query(cur,baseline.history.query(today),key,subject)

def capture_query(cur,q,key=None,subject=None):
 auth.actor(cur,subject)
 r=cur.execute('select public.erp_cp7_capture_production_supply_v1(%s,%s)',
  (json.dumps(q),key or uuid.uuid4())).fetchone()[0]
 b.api.admin(cur);return r

def read(cur,run,subject=None):
 auth.actor(cur,subject)
 r=cur.execute('select public.erp_cp7_read_production_supply_v1(%s)',(run,)).fetchone()[0]
 b.api.admin(cur);return r

# PL-8: SYNTHETIC administrative clones of one posted cutting group and the
# rows the CP7 capture reads for it. Labelled; never an ordinary Native posting
# and never a business fixture. Triggers (and so FK checks) are off only while
# the rows are copied inside the case transaction; every id of the copied
# closure is mapped per clone, and one column of each other unique key is made
# distinct, so no Native row is shared or changed.
CLONE_TABLES=(
 ('cutting_groups','id=%(g)s'),
 ('cutting_group_rolls','cutting_group_id=%(g)s'),
 ('cutting_group_size_slots','id in(select y.size_slot_id from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id where r.cutting_group_id=%(g)s)'),
 ('cutting_roll_yields','cutting_group_roll_id in(select id from erp.cutting_group_rolls where cutting_group_id=%(g)s)'),
 ('cutting_pickups','cutting_group_id=%(g)s'),
 ('cutting_distribution_batches','pickup_id in(select id from erp.cutting_pickups where cutting_group_id=%(g)s)'),
 ('cutting_distribution_allocations','batch_id in(select b.id from erp.cutting_distribution_batches b join erp.cutting_pickups p on p.id=b.pickup_id where p.cutting_group_id=%(g)s)'),
 ('laundry_deliveries','id in(select delivery_id from erp.laundry_delivery_lines where cutting_group_id=%(g)s)'),
 ('laundry_delivery_lines','cutting_group_id=%(g)s'),
 ('laundry_delivery_batch_size_lines','delivery_line_id in(select id from erp.laundry_delivery_lines where cutting_group_id=%(g)s)'),
 ('laundry_receipts','id in(select l.receipt_id from erp.laundry_receipt_lines l join erp.laundry_delivery_lines d on d.id=l.delivery_line_id where d.cutting_group_id=%(g)s)'),
 ('laundry_receipt_lines','delivery_line_id in(select id from erp.laundry_delivery_lines where cutting_group_id=%(g)s)'),
 ('laundry_receipt_batch_size_lines','receipt_line_id in(select l.id from erp.laundry_receipt_lines l join erp.laundry_delivery_lines d on d.id=l.delivery_line_id where d.cutting_group_id=%(g)s)'),
 ('qc_inspections','id in(select inspection_id from erp.qc_inspection_items where cutting_group_id=%(g)s)'),
 ('qc_inspection_items','cutting_group_id=%(g)s'),
 ('bs_cases','cutting_group_id=%(g)s'),
)

def clone_groups(cur,group,n,label):
 """n SYNTHETIC clones of posted group `group`; returns the clone group ids (text)."""
 assert label and 1<=n<=5000
 g=dict(g=str(group))
 ids=[r[0] for t,where in CLONE_TABLES for r in cur.execute(f'select id::text from erp.{t} where {where}',g).fetchall()]
 assert len(ids)==len(set(ids)) and str(group) in ids,('PL8_CLONE_CLOSURE',len(ids))
 cur.execute("select set_config('session_replication_role','replica',true)")
 try:
  for table,where in CLONE_TABLES:
   rows=cur.execute(f'select to_jsonb(x) from erp.{table} x where {where}',g).fetchall()
   if not rows:continue
   cols=cur.execute("""select attname,format_type(atttypid,atttypmod),attidentity<>'' from pg_attribute
     where attrelid=%s::regclass and attnum>0 and not attisdropped and attgenerated='' order by attnum""",('erp.'+table,)).fetchall()
   kinds={c:t for c,t,_ in cols}
   # One column of every unique key that holds no mapped id is made distinct.
   distinct=set()
   for keys,expression in cur.execute("""select array_agg(a.attname order by k.o),i.indexprs is not null from pg_index i
     cross join lateral unnest(i.indkey)with ordinality k(n,o) left join pg_attribute a on a.attrelid=i.indrelid and a.attnum=k.n
     where i.indrelid=%s::regclass and i.indisunique and not i.indisprimary group by i.indexrelid,i.indexprs""",('erp.'+table,)).fetchall():
    keys=[k for k in keys if k]
    if any(all(str(r[0].get(k)) in ids for r in rows) for k in keys) and not expression:continue
    pick=next((k for k in keys if kinds[k] in('text','character varying')or kinds[k].startswith('character varying')),None) \
     or next((k for k in keys if kinds[k]=='uuid'),None)
    if expression and pick is None:pick=next((c for c,t,_ in cols if t=='text'),None)
    assert pick,('PL8_CLONE_UNIQUE_KEY_UNHANDLED',table,keys)
    distinct.add(pick)
   names=[c for c,_,_ in cols];identity=any(i for _,_,i in cols)
   cur.execute(f"""insert into erp.{table}({','.join('"'+c+'"' for c in names)}){' overriding system value' if identity else ''}
    select {','.join('(r)."'+c+'"' for c in names)} from(select jsonb_populate_record(null::erp.{table},(select jsonb_object_agg(e.key,
      case when e.value#>>'{{}}'=any(%(ids)s)then to_jsonb(md5((e.value#>>'{{}}')||':PL8:'||k)::uuid)
       when e.key=any(%(distinct)s)and jsonb_typeof(e.value)='string'and %(kinds)s::jsonb->>e.key='uuid'then to_jsonb(md5((e.value#>>'{{}}')||':PL8U:'||k)::uuid)
       when e.key=any(%(distinct)s)and jsonb_typeof(e.value)='string'and length((e.value#>>'{{}}')||'-SX'||k)>coalesce((%(limits)s::jsonb->>e.key)::int,2147483647)
        then to_jsonb(left(e.value#>>'{{}}',greatest((%(limits)s::jsonb->>e.key)::int-11,0))||'-'||left(md5((e.value#>>'{{}}')||':PL8T:'||k),10))
       when e.key=any(%(distinct)s)and jsonb_typeof(e.value)='string'then to_jsonb((e.value#>>'{{}}')||'-SX'||k)
       else e.value end)from jsonb_each(x.v)e))r
     from(select to_jsonb(t) v from erp.{table} t where {where})x cross join generate_series(1,%(n)s)k)s""",
    dict(g,ids=ids,distinct=list(distinct),kinds=json.dumps(kinds),n=n,
     # A distinct text value keeps the column's varchar(n) limit: when the
     # plain suffix would not fit, the value is cut and a 10-hex hash suffix
     # of (value, clone) keeps it unique.
     limits=json.dumps({c:int(t[len('character varying('):-1])for c,t in kinds.items()if t.startswith('character varying(')})))
 finally:cur.execute("select set_config('session_replication_role','origin',true)")
 return [r[0] for r in cur.execute("select md5(%s||':PL8:'||k)::uuid::text from generate_series(1,%s)k",(str(group),n)).fetchall()]

def vector(r):
 assert r['wip']['status']=='COMPLETE',r
 return [production.total(r['wip'],k+'_pcs')for k in('input','wip','fg','bs','withheld','exited')]

def cases(cur,today):
 def mixed():
  c=production.cut.fixture(cur,today);o=production.opening(cur,today)
  before=b.boundary.snapshot(cur);r=capture(cur,today)
  assert vector(r)==[108,88,15,5,0,0],r
  assert r['wip']['scope']=='GLOBAL_NATIVE_POSTED_PRODUCTION_ORIGINS'
  assert c['group']in r['production_scope']['cutting_groups']and o['item']in r['production_scope']['opening_items']
  assert len(r['wip']['totals'])==3 and b.boundary.snapshot(cur)==before
  assert r['apply_enabled']is False and r['allocation_state']=='UNKNOWN'
  return dict(status='PASS',native_global_mixed108_wip88_fg15_bs5=True,one_graph_no_native_write=True)
 def lifecycle():
  f=production.opening(cur,today,'CUTTING');r=capture(cur,today);assert vector(r)==[8,8,0,0,0,0]
  production.b.bbp.wip_op(cur,f,'PICKUP',contractor_code=f['code'],date=str(f['cutover']+timedelta(days=1)))
  out=production.b.bbp.complete(cur,f,f['cutover']+timedelta(days=2),3)
  production.b.bbp.split(cur,f,f['cutover']+timedelta(days=3),2)
  done=capture(cur,today);assert vector(done)==[8,3,3,2,0,0]
  production.b.bbp.wip_op(cur,f,'REVERSE',output_id=out['output_id'])
  assert vector(capture(cur,today))==[8,6,0,2,0,0]
  assert read(cur,done['run_id'])['wip']==done['wip']and read(cur,done['run_id'])['source_state']=='ARCHIVED_STALE'
  return dict(status='PASS',native_opening_pickup_good_bs_and_inverse_conserve_original8=True)
 def claims():
  f=production.opening(cur,today,claims=((None,'MISSING','2'),));assert vector(capture(cur,today))==[8,6,0,0,2,0]
  production.b.claim_op(cur,f,'RECOVER_CLAIM',production.b.claim_of(cur,f),qty_pcs='1',date=str(today))
  assert vector(capture(cur,today))==[8,7,0,0,1,0]
  production.b.claim_op(cur,f,'RESOLVE_CLAIM',production.b.claim_of(cur,f),resolution='WRITTEN_OFF',date=str(today))
  assert vector(capture(cur,today))==[8,7,0,0,1,0]
  return dict(status='PASS',native_claim_recovery_writeoff_not_free_good=True)
 def unsourced():
  f=production.ax.stocked_product(cur,today);at=production.ax.r1.now(cur)
  # This factory posts real cutting/laundry/QC10 before creating the found BS.
  # Supply v2 (PL-8): every one of those 10 cut pieces reached FG, so the global
  # capture lists the group as exhausted; its zero positions are not netted.
  b.api.admin(cur);cut_qty=cur.execute('select sum(y.qty_pcs)from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id where r.cutting_group_id=%s',(f['group'],)).fetchone()[0]
  assert cut_qty==10
  case=production.ax.manual_bs(cur,f['product'],'OUT_OF_NOWHERE',5,at-timedelta(minutes=15))['result']['bs_case_id']
  first=capture(cur,today);expected=[5,0,0,5,0,0]
  assert vector(first)==expected and first['production_scope']['unsourced_bs']==[str(case)],(vector(first),expected,first['production_scope'])
  assert first['contract_version']=='cp7.native-supply.v2'and first['production_scope']['cutting_groups']==[]
  assert first['production_scope']['exhausted_cutting_groups']==[str(f['group'])]
  assert not any(t['pool_key'].startswith('CUT:')for t in first['wip']['totals'])
  out=production.ax.post(cur,dict(source_kind='GOOD_FROM_UNSOURCED_BS',bs_case_id=case,location_id=production.base.LOCATION,
   qty_pcs=3,physical_at=(at-timedelta(minutes=5)).isoformat(),reason='P06 native global unsourced recovery'))
  assert vector(capture(cur,today))==[5,0,3,2,0,0]
  production.ax.reverse(cur,out['receipt_id'],'P06 retain original BS lineage')
  assert vector(capture(cur,today))==expected
  return dict(status='PASS',native_unsourced_original5_good3_then_inverse_not_duplicate_supply=True,native_spent_production_listed_exhausted_not_netted=True,independent_native_cut_yield=int(cut_qty),expected_initial_global=expected)
 def global56():
  fs=[]
  for _ in range(56):
   rows=production.b.bbp.production_rows()
   # Native master names are unique as well as codes. Keep every fixture an
   # ordinary public import, and make its visible names unique before upload.
   for payloads in rows.values():
    for payload in payloads:
     for field,value in list(payload.items()):
      if field.endswith('_name')and isinstance(value,str):payload[field]='{C} '+value
   f=production.b.bbp.production_post(cur,today,rows)
   f['item']=production.b.bbp.source_of(cur,f)['opening_item_id'];fs.append(f)
  r=capture(cur,today);assert len(r['production_scope']['opening_items'])==56
  assert set(r['production_scope']['opening_items'])=={f['item']for f in fs}
  assert vector(r)==[448,448,0,0,0,0]and len(r['wip']['totals'])==56
  return dict(status='PASS',native56_origins_two_read_batches_one_global448_graph=True,no_first50_or_double_pool=True)
 def no_alias():
  c=production.cut.fixture(cur,today);o=production.opening(cur,today)
  r=capture(cur,today);assert vector(r)==[108,88,15,5,0,0]
  assert not r['production_scope']['unsourced_bs']
  assert len({x['pool_key']for x in r['wip']['totals']})==3
  return dict(status='PASS',native_cutting_BS_not_recaptured_as_nonPO=True)
 def immutable():
  f=production.opening(cur,today);key=uuid.uuid4();r=capture(cur,today,key);assert capture(cur,today,key)==r
  stored=cur.execute('select facts,result from cp7_supply_native.runs where id=%s',(r['run_id'],)).fetchone()
  production.b.bbp.complete(cur,f,f['cutover']+timedelta(days=2),3)
  old=read(cur,r['run_id']);assert old['source_state']=='ARCHIVED_STALE'and vector(old)==[8,8,0,0,0,0]
  assert vector(capture(cur,today))==[8,5,3,0,0,0]
  assert cur.execute('select facts,result from cp7_supply_native.runs where id=%s',(r['run_id'],)).fetchone()==stored
  assert cur.execute('select count(*)from cp7_supply_native.runs where request_id=%s',(key,)).fetchone()[0]==1
  q=baseline.history.query(today);q['from_date']=str(today-timedelta(days=2))
  auth.refused(cur,lambda:capture_query(cur,q,key),'CP7_SUPPLY_REQUEST_CHANGED')
  return dict(status='PASS',one_UUID_run_prior_graph_immutable_native_changes_stale=True)
 def authority():
  production.opening(cur,today);subject,role=auth.custom_actor(cur);key=uuid.uuid4();r=capture(cur,today,key,subject)
  auth.refused(cur,lambda:read(cur,r['run_id']),'CP7_SUPPLY_RUN_UNAVAILABLE')
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'",(role,))
  auth.refused(cur,lambda:capture(cur,today,key,subject),'CP7_ACCESS_DENIED')
  auth.refused(cur,lambda:read(cur,r['run_id'],subject),'CP7_ACCESS_DENIED')
  return dict(status='PASS',current_native_authority_before_cached_UUID_and_archive_actor_bound=True)
 def caps():
  production.opening(cur,today);r=capture(cur,today)
  auth.refused(cur,lambda:cur.execute('delete from cp7_supply_native.runs where id=%s',(r['run_id'],)),'CP7_RUN_IMMUTABLE')
  for who in('anon','authenticated','service_role'):
   assert not cur.execute("select has_schema_privilege(%s,'cp7_supply_native','USAGE')or has_table_privilege(%s,'cp7_supply_native.runs','SELECT,INSERT,UPDATE,DELETE')",(who,who)).fetchone()[0]
  assert not cur.execute("select exists(select 1 from pg_class t join pg_namespace n on n.oid=t.relnamespace where n.nspname='erp'and t.relkind in('r','p','v')and has_table_privilege('cp7_capture',t.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
  return dict(status='PASS',immutable_private_native_read_principal_no_business_DML=True)
 def query():
  production.opening(cur,today)
  for k,value in [('complete_scope',True),('cutting_groups',[]),('capacity_pcs','1000'),('matching',{'status':'CONFIRMED_TARGET'})]:
   q=baseline.history.query(today);q[k]=value
   auth.refused(cur,lambda q=q:capture_query(cur,q),'CP7_WIP_FIELDS')
  assert cur.execute('select count(*)from cp7_supply_native.runs').fetchone()[0]==0
  return dict(status='PASS',client_scope_match_capacity_and_completeness_not_trusted=True)
 def zones():
  production.opening(cur,today);key=uuid.uuid4();r=capture(cur,today,key)
  for zone in('UTC','Asia/Jakarta','America/Los_Angeles'):
   cur.execute("select set_config('TimeZone',%s,true)",(zone,));assert capture(cur,today,key)==r
  return dict(status='PASS',three_caller_timezones_same_immutable_native_source_hash=True)
 def same_clock():
  production.opening(cur,today);r=capture(cur,today);f=cur.execute('select facts from cp7_supply_native.runs where id=%s',(r['run_id'],)).fetchone()[0]
  assert f['captured_at']==f['production_sources']['captured_at']==r['captured_at']
  assert r['wip']['snapshot_id']==r['captured_at']and r['baseline_run_result']['captured_at']==r['captured_at']
  assert all(r[k]=='UNKNOWN'for k in('matching_state','yield_state','calendar_state','capacity_state','allocation_state'))
  assert r['apply_enabled']is False and r['production_go']is False
  return dict(status='PASS',one_native_clock_target_and_all_production_origins=True,unknown_future_good_ETA_calendar_capacity_not_zero=True)
 added=[('MIXED',mixed),('OPENING_LIFECYCLE',lifecycle),('CLAIMS',claims),('UNSOURCED_BS',unsourced),('GLOBAL56',global56),
  ('NO_ALIAS',no_alias),('IMMUTABLE_UUID',immutable),('CURRENT_AUTH',authority),('PRIVATE_CAPS',caps),('CLOSED_QUERY',query),('TIMEZONES',zones),('ONE_CLOCK',same_clock)]
 return baseline.cases(cur,today)+[('P06_SUPPLY_NATIVE_'+n,f)for n,f in added]

def races(tools,today):
 def same_uuid():
  with tools.connect()as conn,conn.cursor()as cur:production.opening(cur,today);conn.commit()
  key=uuid.uuid4();gate=threading.Barrier(2)
  def send():
   with tools.connect()as conn,conn.cursor()as cur:gate.wait(timeout=5);r=capture(cur,today,key);conn.commit();return r
  with ThreadPoolExecutor(max_workers=2)as pool:rs=[j.result(30)for j in[pool.submit(send),pool.submit(send)]]
  assert rs[0]==rs[1]and vector(rs[0])==[8,8,0,0,0,0]
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_supply_native.runs where request_id=%s',(key,)).fetchone()[0]==1
  return dict(status='PASS',two_native_transactions_one_UUID_one_global_supply_run=True)
 def revoke_waiting():
  with tools.connect()as conn,conn.cursor()as cur:
   production.opening(cur,today);subject,role=auth.custom_actor(cur);key=uuid.uuid4();r=capture(cur,today,key,subject);conn.commit()
  with tools.connect()as holder,holder.cursor()as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:SUPPLY:'||%s||':'||%s,0))",(subject,str(key)))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=capture(cur,today,key,subject);conn.commit();return r
     except psycopg.Error as e:conn.rollback();return str(e)
   with ThreadPoolExecutor(max_workers=1)as pool:
    j=pool.submit(send);waiting=False;deadline=time.monotonic()+8
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as c:
      while time.monotonic()<deadline:
       waiting=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_capture_production_supply_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'SUPPLY_NATIVE_UUID_LOCK_NOT_OBSERVED'
     with tools.connect()as conn,conn.cursor()as cur:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'",(role,));conn.commit()
    finally:holder.rollback()
    result=j.result(30)
  assert isinstance(result,str)and'CP7_ACCESS_DENIED'in result,result
  return dict(status='PASS',current_native_revocation_during_observed_cached_supply_UUID_wait=True)
 def coherent():
  with tools.connect()as conn,conn.cursor()as cur:
   c=production.cut.fixture(cur,today);o=production.opening(cur,today);conn.commit()
  ready=threading.Event();done=threading.Event();pairs=[];overlap=0
  def writer():
   with tools.connect()as conn,conn.cursor()as cur:
    for i in range(24):
     good,qty=(29,8)if i%2==0 else(30,9)
     # Administrative atomic corrections exercise MVCC; they neither authorize
     # posted-document edits nor substitute for the real business fixtures.
     cur.execute('set local session_replication_role=replica')
     cur.execute('update erp.laundry_receipt_lines set qty_good_received=%s where id=%s',(good,c['receipt_line']))
     cur.execute('update erp.laundry_receipt_batch_size_lines set qty_good_received=%s where id=%s',(good,c['receipt_size']))
     cur.execute('update erp.initial_import_production_sources set qty_pcs=%s where opening_item_id=%s',(qty,o['item']))
     cur.execute('update erp.opening_balance_items set qty=%s where id=%s',(qty,o['item']))
     cur.execute('set local session_replication_role=origin');conn.commit();ready.set();time.sleep(.03)
   done.set()
  with ThreadPoolExecutor(max_workers=1)as pool:
   w=pool.submit(writer);assert ready.wait(8)
   with tools.connect()as conn,conn.cursor()as cur:
    for _ in range(12):
     r=capture(cur,today);assert r['wip']['status']=='COMPLETE',r
     facts=cur.execute('select facts from cp7_supply_native.runs where id=%s',(r['run_id'],)).fetchone()[0]['production_sources']['facts'];conn.commit()
     pairs.append((int(facts['cutting']['receipts'][0]['good_pcs']),int(facts['other']['origins'][0]['qty_pcs'])))
     if not done.is_set():overlap+=1
   w.result(timeout=20)
  assert overlap>0 and set(pairs)<={(29,8),(30,9)},(overlap,pairs)
  return dict(status='PASS',native_global_cross_origin_one_MVCC_snapshot=True,administrative_source_correction_test=True,overlap=overlap,captures=12,observed_pairs=sorted(set(pairs)))
 return baseline.races(tools,today)+[('P06_SUPPLY_RACE_UUID',same_uuid),('P06_SUPPLY_RACE_REVOKE',revoke_waiting),('P06_SUPPLY_RACE_ONE_MVCC',coherent)]

def http_cases(http,today):
 def flow():
  owner=http.login('OWNER','p06-global-supply-owner');other=http.login('OWNER','p06-global-supply-other')
  with http.connect()as conn,conn.cursor()as cur:production.opening(cur,today);conn.commit()
  args=dict(p_query=baseline.history.query(today),p_request=str(uuid.uuid4()))
  r=owner.rpc('erp_cp7_capture_production_supply_v1',args);assert r['status']==200,r
  assert vector(r['body'])==[8,8,0,0,0,0]and r['body']['apply_enabled']is False
  assert owner.rpc('erp_cp7_capture_production_supply_v1',args)['body']==r['body']
  read_args=dict(p_run=r['body']['run_id'])
  assert other.rpc('erp_cp7_read_production_supply_v1',read_args)['status']==403
  assert http.anon_rpc('erp_cp7_read_production_supply_v1',read_args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_capture_production_supply_v1',args)['status']==403
  assert owner.rpc('erp_cp7_read_production_supply_v1',read_args)['status']==403
  return dict(status='PASS',real_Auth_native_global_supply_immutable_UUID_current403=True)
 return baseline.http_cases(http,today)+[('P06_SUPPLY_HTTP_AUTH',flow)]
