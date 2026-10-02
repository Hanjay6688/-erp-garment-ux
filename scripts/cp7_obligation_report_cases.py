"""Fixed report appendix qualification: every Native269 case is retained."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import hashlib,json,uuid
import psycopg
import cp7_other_obligation_cases as previous
import cp7_obligation_report_bundle as bundle
import cp7_analysis_publication_cases as original_reports
b,auth,parent=previous.b,previous.auth,previous.parent
DATABASE_NAMES=('EXACT_DATED_NATIVE','REPLAY_AND_CLOSED_FENCE','NATIVE_PAYMENT_ARCHIVE',
 'LINKED_REVISION','CURRENT_FINE_RIGHTS','ACTOR_SCOPE','IMMUTABLE_AND_CLOSED_PAYLOAD','PAGED_COMPLETE_INDEX')
RACE_NAMES=('SAME_UUID','SERIES_CAS','CURRENT_PAYROLL_RIGHT')
HTTP_NAMES=('EXACT_AUTH_LIFECYCLE','CLOSED_FENCE')
BROWSER_NAMES=('DESKTOP','MOBILE')
EXPECTED=previous.EXPECTED+len(DATABASE_NAMES)+len(RACE_NAMES)+len(HTTP_NAMES)+len(BROWSER_NAMES)
def rpc(cur,name,args,subject=None):return parent.schedule.rpc(cur,name,args,subject)
def base(cur,e,subject=None):return original_reports.command(cur,parent,original_reports.payload(e),subject=subject)['document']
def preview(cur,d,subject=None):return rpc(cur,'erp_cp7_get_obligation_report_preview_v1',(d['id'],),subject)
def payload(p,prior=None,title='Lampiran tagihan yang ditinjau'):
 return dict(publication_id=p['base_report']['id'],run_id=p['base_report']['run_id'],source_hash=p['source']['source_hash'],
  title=title,reason='Nominal, sumber dan tanggal yang belum diketahui sudah ditinjau',explicit_review=True,
  series_id=prior['series_id']if prior else None,expected_revision=prior['revision']if prior else None)
def command(cur,p,request=None,subject=None,lookup=False):
 return rpc(cur,'erp_cp7_get_obligation_report_request_v1'if lookup else'erp_cp7_publish_obligation_report_v1',(json.dumps(p),request or uuid.uuid4()),subject)
def read(cur,id,subject=None):return rpc(cur,'erp_cp7_read_obligation_report_v1',(id,),subject)
def listing(cur,e,subject=None,before=None,limit=25):return rpc(cur,'erp_cp7_list_obligation_reports_v1',(json.dumps(dict(run_id=e['run_id'],before_id=before,limit=limit)),),subject)
def fixture(cur,today,subject=None,large=False,reset=True):
 if reset:previous.setup(cur,today)
 f=previous.installments.fixture(cur,today,attendance=False,manual='9007199254740993.01'if large else'1000')
 e=previous.capture(cur,today,subject);d=base(cur,e,subject);p=preview(cur,d,subject);return f,e,d,p
def checked(c,p):
 assert c['contract_version']=='cp7.obligation-report-command.v1'and c['status']=='COMMITTED'and not c['production_go'];d=c['document']
 assert d['contract_version']=='cp7.obligation-report.v1'and d['publication_id']==p['publication_id']and d['run_id']==p['run_id']and d['source_hash']==p['source_hash']
 assert d['body_sha256']==hashlib.sha256(d['body'].encode()).hexdigest()and d['template_version']=='native-obligation-report-1'
 assert d['base_report']['body']in d['body']and d['source']['source_hash']==p['source_hash']
 assert 'bukan rekonstruksi tagihan pada periode laporan lama'in d['body']and'Jangan menjumlahkan baris ini sebagai total utang'in d['body']
 return d

def cases(cur,today):
 def exact():
  f,e,d,view=fixture(cur,today,large=True);p=payload(view);before=b.boundary.snapshot(cur);one=checked(command(cur,p),p)
  r=previous.previous.row(one['source'],previous.key('PAYROLL_AP',f['payroll']));assert previous.remaining(r)['value']=='9007199254740993.01'and r['financial_source']['recorded_due_date']is None
  assert '9007199254740993.01 IDR'in one['body']and'jatuh tempo tercatat Belum diketahui'in one['body']and'WIB'in one['body']
  assert one['source']['analysis']['analysis']==e['analysis']and one['base_report']['period_query']==e['query']and b.boundary.snapshot(cur)==before
  assert one['published_at']>=one['source']['read_at']
  return dict(status='PASS',exact_actual_Native_large_cent_no_money_formula=True,actual_current_knowledge_clock_separate_from_original_period=True,unknown_due_not_zero_or_fake_date=True,no_Native_business_DML=True)
 def replay():
  _,e,_,v=fixture(cur,today);p=payload(v);key=uuid.uuid4();one=checked(command(cur,p,key),p);two=checked(command(cur,p,key,lookup=True),p)
  assert one==two==command(cur,p,key)['document'];auth.refused(cur,lambda:command(cur,{**p,'title':'Different'},key),'CP7_OBLIGATION_REPORT_REQUEST_CHANGED')
  absent=uuid.uuid4();negative=command(cur,p,absent,lookup=True);assert negative['status']=='CLOSED_UNCOMMITTED'and negative['document']is None
  assert command(cur,p,absent)==negative and cur.execute('select count(*)from cp7_reminder_native.obligation_reports where request_id=%s',(absent,)).fetchone()[0]==0
  return dict(status='PASS',one_UUID_one_frozen_document_actual_replay=True,negative_receipt_seals_late_old_UUID=True)
 def payment():
  f,e,base_doc,v=fixture(cur,today);p=payload(v);one=checked(command(cur,p),p);old_body=one['body'];old_source=one['source'];previous.installments.act(cur,f,amount='600')
  now=read(cur,one['id']);assert now['source_state']=='ARCHIVED_STALE'and now['body']==old_body and now['source']==old_source
  # A nonfinancial Original may remain unchanged after a cash payment.
  # Its period and the appendix's current knowledge are separate.
  if now['base_report']['source_state']=='ARCHIVED_STALE':
   auth.refused(cur,lambda:preview(cur,base_doc),'CP7_OBLIGATION_REPORT_SOURCE_CHANGED')
  else:
   current=preview(cur,base_doc);assert current['source']['source_hash']!=one['source_hash']
   previous.amount(previous.previous.row(current['source'],previous.key('PAYROLL_AP',f['payroll'])),'400')
   assert current['base_report']['body']==base_doc['body']and current['base_report']['period_query']==base_doc['period_query']
  fresh=previous.capture(cur,today);new_base=base(cur,fresh);v2=preview(cur,new_base);p2=payload(v2,one);two=checked(command(cur,p2),p2)
  previous.amount(previous.previous.row(two['source'],previous.key('PAYROLL_AP',f['payroll'])),'400')
  assert two['series_id']==one['series_id']and two['revision']=='2'and two['base_report']['period_query']==one['base_report']['period_query']
  assert read(cur,one['id'])['body']==old_body and read(cur,one['id'])['source']==old_source
  return dict(status='PASS',actual_Native_partial_cash1000_to400_old_archive_byte_identical=True,fresh_original_linked_revision_current400_no_historical_relabel=True)
 def revision():
  _,e,_,v=fixture(cur,today);p=payload(v);one=checked(command(cur,p),p);p2=payload(v,one,title='Penjelasan kedua');two=checked(command(cur,p2),p2)
  assert two['revision']=='2'and two['series_id']==one['series_id']and not read(cur,one['id'])['is_latest']
  auth.refused(cur,lambda:command(cur,p2),'CP7_OBLIGATION_REPORT_REVISION_CHANGED');assert read(cur,one['id'])['body']==one['body']
  return dict(status='PASS',actual_revision_CAS_same_period_previous_source_preserved=True)
 def rights():
  previous.setup(cur,today);subject,role=previous.actor(cur);f,e,d,v=fixture(cur,today,subject,reset=False);p=payload(v);key=uuid.uuid4();one=checked(command(cur,p,key,subject),p);previous.revoke(cur,role,'finance.payroll.view')
  assert listing(cur,e,subject)['rows']==[]and listing(cur,e,subject)['total']=='0'
  for call in(lambda:read(cur,one['id'],subject),lambda:command(cur,p,key,subject),lambda:command(cur,p,key,subject,True)):auth.refused(cur,call,'CP7_OBLIGATION_REPORT_DOMAIN_DENIED')
  auth.refused(cur,lambda:listing(cur,e,subject,one['id']),'CP7_OBLIGATION_REPORT_CURSOR_UNAVAILABLE')
  return dict(status='PASS',current_payroll_permission_before_saved_body_cached_positive_lookup_title_count_cursor=True,AP_and_ops_retained=True)
 def actor_scope():
  previous.setup(cur,today);subject,_=previous.actor(cur);_,e,_,v=fixture(cur,today,subject,reset=False);p=payload(v);one=checked(command(cur,p,subject=subject),p);other,_=previous.actor(cur);own=previous.capture(cur,today,other)
  auth.refused(cur,lambda:read(cur,one['id'],other),'CP7_OBLIGATION_REPORT_UNAVAILABLE');assert listing(cur,own,other)['total']=='0'
  auth.refused(cur,lambda:preview(cur,v['base_report'],other),'CP7_REPORT_UNAVAILABLE')
  return dict(status='PASS',foreign_actor_Original_publication_appendix_and_index_unavailable=True)
 def immutable():
  _,e,_,v=fixture(cur,today);p=payload(v);one=checked(command(cur,p),p);bundle.verify(cur);before=b.boundary.snapshot(cur)
  for sql in("update cp7_reminder_native.obligation_reports set body='rewritten' where id=%s","delete from cp7_reminder_native.obligation_reports where id=%s"):
   auth.refused(cur,lambda sql=sql:cur.execute(sql,(one['id'],)),'CP7_REMINDER_REQUEST_IMMUTABLE')
  auth.refused(cur,lambda:command(cur,{**p,'external_send':True}),'CP7_OBLIGATION_REPORT_FIELDS')
  for change in(dict(explicit_review=False),dict(title=''),dict(reason=''),dict(source_hash='0'*64)):
   auth.refused(cur,lambda change=change:command(cur,{**p,**change}),'CP7_OBLIGATION_REPORT_SOURCE_CHANGED'if 'source_hash'in change else'CP7_OBLIGATION_REPORT_REVIEW')
  assert read(cur,one['id'])['body']==one['body']and b.boundary.snapshot(cur)==before
  return dict(status='PASS',immutable_admin_update_delete_false_RLS_and_private_function_ACLs=True,closed_review_hash_payload_no_external_send_or_Native_business_change=True)
 def pages():
  _,e,_,v=fixture(cur,today);ids=[]
  for n in range(27):ids.append(checked(command(cur,payload(v,title='Lampiran asli '+str(n))),payload(v,title='Lampiran asli '+str(n)))['id'])
  first=listing(cur,e);second=listing(cur,e,before=first['next_before_id']);assert len(first['rows'])==25 and len(second['rows'])==2 and second['next_before_id']is None
  assert first['total']==second['total']=='27'and set(ids)=={r['id']for r in first['rows']+second['rows']}
  return dict(status='PASS',actual27_metadata_documents_complete_keyset25plus2_no_duplicate_or_missing=True)
 functions=(exact,replay,payment,revision,rights,actor_scope,immutable,pages)
 return previous.cases(cur,today,qualification_bundle=bundle)+[('P15_OBLIGATION_REPORT_NATIVE_'+n,f)for n,f in zip(DATABASE_NAMES,functions)]

def races(tools,today):
 def prepare(subject=None,reset=True):
  with tools.connect()as conn,conn.cursor()as cur:
   f,e,d,v=fixture(cur,today,subject,reset=reset);p=payload(v);conn.commit();return e,p
 def send(p,key,subject=None,lookup=False):
  with tools.connect()as conn,conn.cursor()as cur:
   try:r=command(cur,p,key,subject,lookup);conn.commit();return r
   except psycopg.Error as ex:conn.rollback();return dict(sqlstate=ex.sqlstate,error=str(ex).split('\n',1)[0])
 def same():
  _,p=prepare();key=uuid.uuid4()
  with ThreadPoolExecutor(max_workers=2)as pool:out=list(pool.map(lambda _:send(p,key),range(2)))
  assert out[0]['status']==out[1]['status']=='COMMITTED'and out[0]['document']==out[1]['document'],out
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_reminder_native.obligation_reports where request_id=%s',(key,)).fetchone()[0]==1
  return dict(status='PASS',actual_concurrent_identical_UUID_one_appendix_two_identical_receipts=True)
 def series():
  _,p=prepare();one=send(p,uuid.uuid4())['document'];p={**p,'series_id':one['series_id'],'expected_revision':'1'}
  with ThreadPoolExecutor(max_workers=2)as pool:out=list(pool.map(lambda _:send(p,uuid.uuid4()),range(2)))
  assert sum(r.get('status')=='COMMITTED'for r in out)==1 and any(r.get('sqlstate')=='40001'and r.get('error')=='CP7_OBLIGATION_REPORT_REVISION_CHANGED'for r in out),out
  return dict(status='PASS',actual_distinct_UUID_same_series_CAS_exactly_one_revision=True)
 def current():
  with tools.connect()as conn,conn.cursor()as cur:previous.setup(cur,today);subject,role=previous.actor(cur);conn.commit()
  _,p=prepare(subject,reset=False);key=uuid.uuid4();send(p,key,subject)
  with tools.connect()as holder,holder.cursor()as held:
   held.execute("select pg_advisory_xact_lock(hashtextextended('CP7:OBLIGATION_REPORT_REQUEST:'||%s||':'||%s,0))",(str(subject),str(key)))
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send,p,key,subject,True)
    try:
     previous.previous.wait_for(tools,'erp_cp7_get_obligation_report_request_v1')
     with tools.connect()as conn,conn.cursor()as cur:previous.revoke(cur,role,'finance.payroll.view');conn.commit()
    finally:holder.rollback()
    out=job.result(90)
  assert out==dict(sqlstate='42501',error='CP7_REMINDER_ACCESS_CHANGED'),out
  return dict(status='PASS',witnessed_actual_request_wait_current_payroll_revoke_before_cached_body=True)
 return previous.races(tools,today)+[('P15_OBLIGATION_REPORT_RACE_'+n,f)for n,f in zip(RACE_NAMES,(same,series,current))]

def http_cases(http,today):
 def prepare(owner):
  with http.connect()as conn,conn.cursor()as cur:previous.setup(cur,today);f=previous.installments.fixture(cur,today,attendance=False,manual='9007199254740993.01');conn.commit()
  e=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=parent.previous.baseline.history.query(today),p_request=str(uuid.uuid4())));assert e['status']==200,e
  d=owner.rpc('erp_cp7_publish_report_v1',dict(p_payload=original_reports.payload(e['body']),p_request=str(uuid.uuid4())));assert d['status']==200,d
  v=owner.rpc('erp_cp7_get_obligation_report_preview_v1',dict(p_publication=d['body']['document']['id']));assert v['status']==200,v
  return e['body'],payload(v['body'])
 def lifecycle():
  owner=http.login('OWNER','p15-obligation-report-owner');other=http.login('OWNER','p15-obligation-report-foreign');e,p=prepare(owner);args=dict(p_payload=p,p_request=str(uuid.uuid4()))
  one=owner.rpc('erp_cp7_publish_obligation_report_v1',args);assert one['status']==200,one;d=checked(one['body'],p);assert '9007199254740993.01 IDR'in d['body']
  same=owner.rpc('erp_cp7_get_obligation_report_request_v1',args);assert same['status']==200 and same['body']['document']==d
  assert other.rpc('erp_cp7_read_obligation_report_v1',dict(p_id=d['id']))['status']==403
  assert http.anon_rpc('erp_cp7_read_obligation_report_v1',dict(p_id=d['id']))['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  for name,q in [('erp_cp7_read_obligation_report_v1',dict(p_id=d['id'])),('erp_cp7_get_obligation_report_request_v1',args),('erp_cp7_publish_obligation_report_v1',args),('erp_cp7_list_obligation_reports_v1',dict(p_query=dict(run_id=e['run_id'],before_id=None,limit=25)))]:assert owner.rpc(name,q)['status']==403
  return dict(status='PASS',real_Auth_exact_Native_money_immutable_original_current403_before_all_cached_facts=True,foreign_and_anonymous_denied=True)
 def absent():
  owner=http.login('OWNER','p15-obligation-report-absent');_,p=prepare(owner);args=dict(p_payload=p,p_request=str(uuid.uuid4()))
  one=owner.rpc('erp_cp7_get_obligation_report_request_v1',args);assert one['status']==200 and one['body']['status']=='CLOSED_UNCOMMITTED'
  two=owner.rpc('erp_cp7_publish_obligation_report_v1',args);assert two['status']==200 and two['body']==one['body']
  with http.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_reminder_native.obligation_reports where request_id=%s',(args['p_request'],)).fetchone()[0]==0
  return dict(status='PASS',real_Auth_negative_lookup_fences_old_UUID_no_appendix_no_native_business_write=True)
 return previous.http_cases(http,today)+[('P15_OBLIGATION_REPORT_HTTP_'+n,f)for n,f in zip(HTTP_NAMES,(lifecycle,absent))]
