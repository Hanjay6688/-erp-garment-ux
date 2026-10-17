"""One deliberate three-session schedule: an older allocated audit id commits after the first page.
All customer writes use the ordinary public master facade and Native audit trigger.
"""
import uuid
import cp7_r3_audit_cases as a
import cp7_master_cases as master

EXPECTED=1
ID='ASTRA_R3_AUDIT_LOWER_ID_LATE_COMMIT'

def races(tools,today):
 def schedule():
  tag='A3P'+uuid.uuid4().hex[:9].upper();reason='Astra audit paging '+tag
  with tools.connect()as conn,conn.cursor()as cur:
   subject,_=a.person(cur,'OWNER',tag)
   for i in range(7):master.create(cur,'CUSTOMER',master.customer_fields(tag+str(i),'Astra seed '+str(i)),reason=reason+' seed '+str(i),subject=subject)
   conn.commit()
  held=tools.connect();h=held.cursor()
  try:
   delayed=master.create(h,'CUSTOMER',master.customer_fields(tag+'A','Astra lower id late commit'),reason=reason+' HELD',subject=subject)['id']
   held_id=a.one(h,"select max(id) from erp.audit_logs where entity_id=%s and change_reason=%s",(delayed,reason+' HELD'))
   # A second writer commits a higher sequence id while the lower one is still invisible.
   with tools.connect()as conn,conn.cursor()as cur:
    higher=master.create(cur,'CUSTOMER',master.customer_fields(tag+'B','Astra higher id first commit'),reason=reason+' HIGHER',subject=subject)['id']
    higher_id=a.one(cur,"select max(id) from erp.audit_logs where entity_id=%s and change_reason=%s",(higher,reason+' HIGHER'));conn.commit()
   with tools.connect()as conn,conn.cursor()as cur:
    first=a.read(cur,dict(q=reason,limit=3),subject)
    invisible=a.one(cur,'select count(*) from erp.audit_logs where id=%s',(held_id,))==0
    session=a.one(cur,"select state from pg_stat_activity where pid=%s",(held.info.backend_pid,))
   asof=first['snapshot']['as_of']
   assert invisible and held_id<higher_id<=int(asof) and session=='idle in transaction',(invisible,held_id,higher_id,asof,session)
   assert first['page']['total']=='8' and first['page']['next_after'] is not None,first
   held.commit()
  finally:
   held.close()
  pages=[first]
  for _ in range(10):
   cursor=pages[-1]['page']['next_after']
   if cursor is None:break
   with tools.connect()as conn,conn.cursor()as cur:
    pages.append(a.read(cur,dict(q=reason,limit=3,as_of=asof,after=cursor),subject))
  assert pages[-1]['page']['next_after'] is None
  with tools.connect()as conn,conn.cursor()as cur:
   fresh=a.read(cur,dict(q=reason,limit=100,as_of=asof),subject)
   actual=[str(r[0])for r in cur.execute('select id from erp.audit_logs where change_reason like %s order by changed_at desc,id desc',(reason+'%',)).fetchall()]
  walked=[r['id']for p in pages for r in p['page']['rows']]
  current=[r['id']for r in fresh['page']['rows']]
  assert current==actual and len(actual)==9 and str(held_id) in actual,(current,actual)
  signalled=any(p['snapshot']['newer']for p in pages[1:])
  missed=sorted(set(actual)-set(walked))
  bad=bool(missed) and not signalled
  return dict(status='COUNTEREXAMPLE' if bad else 'PASS',expected='a committed row inside the listing cutoff is either visited or an explicit new-data indication requests reload',
              ordinary_master_writes=True,native_audit_trigger=True,held_id=held_id,higher_committed_id=higher_id,as_of=asof,
              observed_holder_state=session,held_row_invisible_at_first_page=invisible,first_count=8,final_count=9,
              page_totals=[p['page']['total']for p in pages],page_ids=[[r['id']for r in p['page']['rows']]for p in pages],
              all_native_ids=actual,missed_ids=missed,newer_signalled=signalled,fresh_same_cutoff_ids=current)
 return [(ID,schedule)]
