"""Predeclared P15 Native publication lifecycle. No synthetic financial facts."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
import hashlib,json,threading,time,uuid
import psycopg

KINDS=('DAILY','PERIOD','EXCEPTIONS','ARCHIVE')
def payload(e,kind='PERIOD',prior=None,title='Laporan ERP yang ditinjau',reason='Operator telah meninjau sumber asli'):
 return dict(run_id=e['run_id'],source_hash=e['analysis']['snapshot']['source_hash'],semantic_hash=e['analysis']['semantic_hash'],kind=kind,series_id=prior['series_id']if prior else None,expected_revision=prior['revision']if prior else None,title=title,reason=reason,explicit_review=True)
def command(cur,parent,p,key=None,subject=None,lookup=False):
 return parent.schedule.rpc(cur,'erp_cp7_get_report_request_v1'if lookup else'erp_cp7_publish_report_v1',(json.dumps(p),key or uuid.uuid4()),subject)
def read(cur,parent,ident,subject=None):return parent.schedule.rpc(cur,'erp_cp7_read_report_v1',(ident,),subject)
def listing(cur,parent,subject=None,before=None,limit=25):return parent.schedule.rpc(cur,'erp_cp7_list_reports_v1',(json.dumps(dict(before_id=before,limit=limit)),),subject)
def compare(cur,parent,before,after,subject=None):return parent.schedule.rpc(cur,'erp_cp7_compare_reports_v1',(before,after),subject)
def checked(c,e,p,key=None):
 assert set(c)=={'contract_version','request_id','status','document','analysis','production_go'}and c['contract_version']=='cp7.report-command.v1'and not c['production_go']
 assert c['status']in('COMMITTED','CLOSED_UNCOMMITTED')and c['analysis']['analysis']==e['analysis']and c['analysis']['financial_source']==e['financial_source']
 if key:assert c['request_id']==str(key)
 d=c['document']
 if c['status']=='CLOSED_UNCOMMITTED':assert d is None;return None
 assert d['contract_version']=='cp7.report-publication.v1'and d['actor_scope_id']==e['analysis']['scope']['actor_scope_id']and not d['production_go']
 assert d['run_id']==e['run_id']and d['request_id']==c['request_id']and d['kind']==p['kind']and d['period_query']==e['query']
 assert d['source_hash']==p['source_hash']and d['semantic_hash']==p['semantic_hash']and d['title']==p['title'].strip()and d['reason']==p['reason'].strip()
 assert d['body_sha256']==hashlib.sha256(d['body'].encode()).hexdigest()and d['template_version']=='native-report-1'
 assert d['analysis']['analysis']==e['analysis']and d['analysis']['financial_source']==e['financial_source']
 assert d['body'].startswith(d['title'])and p['source_hash']in d['body']and p['semantic_hash']in d['body']and'WIB'in d['body']and'Issue bukan bukti pemasangan'in d['body']
 for label in e['product_labels']:assert label['sku']in d['body']
 return d

def cases(cur,today,parent):
 auth,b=parent.auth,parent.b
 def templates():
  parent.setup(cur,today);e=parent.capture(cur,today);parent.checked(e);before=b.boundary.snapshot(cur);docs=[]
  for kind in KINDS:
   p=payload(e,kind);d=checked(command(cur,parent,p),e,p);docs.append(d)
   assert d['source_state']=='UNCHANGED'and d['revision']=='1'and d['is_latest']
  assert len({d['series_id']for d in docs})==4 and b.boundary.snapshot(cur)==before
  assert parent.read(cur,e['run_id'])['source_state']=='UNCHANGED'
  return dict(status='PASS',four_Native_templates_render_same_original_no_reallocation=True,exact_Native_financial_values_unknowns_and_source_provenance=True,no_business_DML=True)
 def replay():
  parent.setup(cur,today);e=parent.capture(cur,today);p=payload(e);key=uuid.uuid4();one=checked(command(cur,parent,p,key),e,p,key);two=checked(command(cur,parent,p,key,lookup=True),e,p,key)
  assert one==two and checked(command(cur,parent,p,key),e,p,key)==one
  assert cur.execute('select count(*)from cp7_analysis_native.publications where request_id=%s',(key,)).fetchone()[0]==1
  changed={**p,'title':'Judul permintaan berbeda'};auth.refused(cur,lambda:command(cur,parent,changed,key),'CP7_REPORT_REQUEST_CHANGED')
  return dict(status='PASS',lost_reply_UUID_one_immutable_publication=True,current_protected_lookup_and_publish_replay_identical=True,changed_same_UUID_payload_refused=True)
 def absent():
  parent.setup(cur,today);e=parent.capture(cur,today);p=payload(e);key=uuid.uuid4();one=command(cur,parent,p,key,lookup=True);checked(one,e,p,key)
  assert one['status']=='CLOSED_UNCOMMITTED'and command(cur,parent,p,key)['status']=='CLOSED_UNCOMMITTED'
  assert cur.execute('select count(*)from cp7_analysis_native.publications where request_id=%s',(key,)).fetchone()[0]==0
  assert cur.execute('select status from cp7_analysis_native.report_requests where request_id=%s',(key,)).fetchone()[0]=='CLOSED_UNCOMMITTED'
  return dict(status='PASS',absent_resolution_seals_old_UUID_late_publication_cannot_commit=True)
 def revisions():
  parent.setup(cur,today);e=parent.capture(cur,today);p=payload(e);one=checked(command(cur,parent,p),e,p);old=one['body'];p2=payload(e,prior=one,title='Laporan revisi kedua',reason='Penjelasan operator ditambah');two=checked(command(cur,parent,p2),e,p2)
  assert two['series_id']==one['series_id']and two['revision']=='2'and two['is_latest']
  old_now=read(cur,parent,one['id']);assert old_now['body']==old and old_now['body_sha256']==one['body_sha256']and not old_now['is_latest']and old_now['analysis']['analysis']==e['analysis']
  auth.refused(cur,lambda:command(cur,parent,p2),'CP7_REPORT_REVISION_CHANGED')
  for changed in({**payload(e,prior=two),'kind':'DAILY'},{**payload(e,prior=two),'expected_revision':'1'}):auth.refused(cur,lambda changed=changed:command(cur,parent,changed),'CP7_REPORT_SERIES_SCOPE_CHANGED'if changed['kind']=='DAILY'else'CP7_REPORT_REVISION_CHANGED')
  return dict(status='PASS',revision_CAS_preserves_earlier_immutable_body_and_Original=True,series_kind_and_period_not_relabelled=True)
 def actual_comparison():
  f,root,s,p=parent.setup(cur,today);e=parent.capture(cur,today);one=command(cur,parent,payload(e))['document']
  parent.previous.production.b.bbp.complete(cur,f,f['cutover']+timedelta(days=2),3)
  fresh=parent.capture(cur,today);p2=payload(fresh,prior=one,title='Tiga barang jadi tercatat');two=checked(command(cur,parent,p2),fresh,p2)
  assert read(cur,parent,one['id'])['source_state']=='ARCHIVED_STALE'and read(cur,parent,one['id'])['body']==one['body']
  before=b.boundary.snapshot(cur);c=compare(cur,parent,one['id'],two['id']);assert c['contract_version']=='cp7.report-comparison.v1'and not c['production_go']
  row=next(r for r in c['rows']if r['metric_id'].startswith('AVAILABLE_FG_PCS:')and r['scope_key'].split(':')[0]==root)
  assert row['before']['value']['value']=='0'and row['after']['value']['value']=='3'and row['difference']==dict(state='KNOWN',unit='PCS',value='3')
  for r in c['rows']:
   if r['difference']['state']!='UNKNOWN':assert Decimal(r['difference']['value'])==Decimal(r['after']['value']['value'])-Decimal(r['before']['value']['value'])
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_Native_output3_before0_after3_delta3=True,server_exact_decimal_comparison_not_second_financial_engine=True,older_published_body_immutable_source_stale=True)
 def unknown():
  parent.setup(cur,today);e=parent.capture(cur,today);one=command(cur,parent,payload(e))['document'];c=compare(cur,parent,one['id'],one['id']);unknown=[r for r in c['rows']if r['before']['value']['state']=='UNKNOWN']
  assert unknown and all(r['difference']['state']=='UNKNOWN'and'value'not in r['difference']for r in unknown)
  assert'Belum diketahui'in one['body']and all(r['difference']['value']=='0'for r in c['rows']if r['difference']['state']!='UNKNOWN')
  return dict(status='PASS',actual_Native_blocked_valuation_unknown_even_same_report_not_zero=True,actual_known_self_comparison_exact_zero=True)
 def periods():
  parent.setup(cur,today);left=parent.previous.baseline.history.query(today);left.update(from_date=str(today-timedelta(days=6)),through_date=str(today-timedelta(days=3)));right={**left,'from_date':str(today-timedelta(days=2)),'through_date':str(today)}
  e1=parent.capture(cur,today,q=left);one=command(cur,parent,payload(e1))['document'];e2=parent.capture(cur,today,q=right);two=command(cur,parent,payload(e2))['document'];c=compare(cur,parent,one['id'],two['id'])
  assert c['before']['period_query']==left and c['after']['period_query']==right
  for r in c['rows']:
   if r['before']:assert r['before']in e1['analysis']['metrics']
   if r['after']:assert r['after']in e2['analysis']['metrics']
  auth.refused(cur,lambda:command(cur,parent,payload(e2,prior=one)),'CP7_REPORT_SERIES_SCOPE_CHANGED')
  return dict(status='PASS',two_actual_dated_Native_reads_not_relabelled_same_fixture=True,original_metric_periods_versions_units_and_knowledge_preserved=True,revision_cannot_replace_series_period=True)
 def engine_version():
  parent.setup(cur,today);e=parent.capture(cur,today);one=command(cur,parent,payload(e))['document'];definition=cur.execute("select pg_get_functiondef('cp7_analysis_native.fact(text,text,jsonb,jsonb)'::regprocedure)").fetchone()[0]
  cur.execute(definition.replace('SOURCE_INPUT_NOT_PROVEN','SOURCE_INPUT_NOT_PROVEN_REPORT_VERSION'),prepare=False);fresh=parent.capture(cur,today);two=command(cur,parent,payload(fresh))['document'];c=compare(cur,parent,one['id'],two['id'])
  assert c['rows']and all(r['difference']['state']=='UNKNOWN'and r['difference']['reason']=='ENGINE_VERSIONS_NOT_COMPARABLE'for r in c['rows'])
  assert read(cur,parent,one['id'])['body']==one['body']
  return dict(status='PASS',actual_compiler_version_change_not_comparable_never_silent_delta=True,older_template_body_preserved=True)
 def closed_payload():
  parent.setup(cur,today);e=parent.capture(cur,today);p=payload(e);before=b.boundary.snapshot(cur)
  for field,value in [('explicit_review',False),('explicit_review',None),('kind','AUTO_POST'),('title',''),('reason',''),('title',7),('series_id',7),('run_id',str(uuid.uuid4()).replace('-',''))]:auth.refused(cur,lambda field=field,value=value:command(cur,parent,{**p,field:value}),'CP7_REPORT_REVIEW')
  for field,value in [('source_hash','0'*64),('semantic_hash','0'*64)]:auth.refused(cur,lambda field=field,value=value:command(cur,parent,{**p,field:value}),'CP7_REPORT_ORIGINAL_CHANGED')
  auth.refused(cur,lambda:command(cur,parent,{**p,'auto_apply':True}),'CP7_WIP_FIELDS');auth.refused(cur,lambda:command(cur,parent,{**p,'expected_revision':'0'}),'CP7_REPORT_REVISION')
  assert b.boundary.snapshot(cur)==before and cur.execute('select count(*)from cp7_analysis_native.publications').fetchone()[0]==0
  return dict(status='PASS',strict_review_source_semantic_kind_title_reason_UUID_and_exact_keys=True,no_native_business_or_publication_on_refusal=True)
 def ops_auth():
  parent.setup(cur,today);subject,role=auth.custom_actor(cur);e=parent.capture(cur,today,subject=subject);p=payload(e);key=uuid.uuid4();d=command(cur,parent,p,key,subject)['document'];cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'",(role,))
  for call in(lambda:read(cur,parent,d['id'],subject),lambda:listing(cur,parent,subject),lambda:compare(cur,parent,d['id'],d['id'],subject),lambda:command(cur,parent,p,key,subject),lambda:command(cur,parent,p,key,subject,True)):auth.refused(cur,call,'CP7_ACCESS_DENIED')
  return dict(status='PASS',current_four_Native_Ops_permissions_before_read_list_compare_cached_UUID_and_resolution=True)
 def actor_scope():
  parent.setup(cur,today);subject,_=auth.custom_actor(cur);other,_=auth.custom_actor(cur);e=parent.capture(cur,today,subject=subject);p=payload(e);d=command(cur,parent,p,subject=subject)['document'];own=parent.capture(cur,today,subject=other)
  assert listing(cur,parent,other)['total']=='0'and listing(cur,parent,other)['rows']==[]
  auth.refused(cur,lambda:read(cur,parent,d['id'],other),'CP7_REPORT_UNAVAILABLE');auth.refused(cur,lambda:compare(cur,parent,d['id'],d['id'],other),'CP7_REPORT_UNAVAILABLE');auth.refused(cur,lambda:listing(cur,parent,other,d['id']),'CP7_REPORT_INDEX_CURSOR_UNAVAILABLE')
  auth.refused(cur,lambda:command(cur,parent,payload(own,prior=d),subject=other),'CP7_REPORT_REVISION_CHANGED')
  assert not any(k in d['body']for k in('unit_hpp','unit_price','cost_amount'))and d['analysis']['financial_source']is None
  return dict(status='PASS',foreign_actor_publication_series_cursor_compare_and_protected_original_unavailable=True,no_finance_facts_in_operational_report=True)
 def finance_auth():
  parent.setup(cur,today);subject,role=parent.financial_cases.admin_actor(cur,parent);e=parent.capture(cur,today,subject=subject);p=payload(e);key=uuid.uuid4();d=command(cur,parent,p,key,subject)['document'];assert e['financial_source']['report']['close_preflight']is not None
  for permission in('finance.reports.view','finance.period_close.manage'):
   cur.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s',(role,permission))
   assert listing(cur,parent,subject)['rows']==[]and listing(cur,parent,subject)['total']=='0'
   for call in(lambda:read(cur,parent,d['id'],subject),lambda:compare(cur,parent,d['id'],d['id'],subject),lambda:command(cur,parent,p,key,subject),lambda:command(cur,parent,p,key,subject,True)):auth.refused(cur,call,'CP7_ANALYSIS_FINANCE_ACCESS_DENIED')
   cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',(role,permission));assert read(cur,parent,d['id'],subject)['body']==d['body']
  return dict(status='PASS',current_report_and_close_preflight_rights_before_any_protected_content_title_and_cached_reply=True,restore_reopens_identical_body=True)
 def immutable():
  parent.setup(cur,today);e=parent.capture(cur,today);d=command(cur,parent,payload(e))['document']
  for table in('publications','report_requests'):
   for sql in('delete from cp7_analysis_native.'+table,'update cp7_analysis_native.'+table+' set actor=gen_random_uuid()'):auth.refused(cur,lambda sql=sql:cur.execute(sql),'CP7_RUN_IMMUTABLE')
  assert read(cur,parent,d['id'])['body_sha256']==d['body_sha256']
  return dict(status='PASS',immutable_publications_and_positive_negative_receipts_even_admin_cannot_edit_or_delete=True)
 def pages():
  parent.setup(cur,today);subject,_=auth.custom_actor(cur);e=parent.capture(cur,today,subject=subject);docs=[command(cur,parent,payload(e,title='Laporan '+str(i)),subject=subject)['document']for i in range(5)]
  rows=[];cursor=None
  for _ in range(3):
   page=listing(cur,parent,subject,cursor,2);assert page['total']=='5'and page['page_complete']and not page['production_go'];rows+=page['rows'];cursor=page['next_before_id']
  assert cursor is None and [r['id']for r in rows]==[d['id']for d in reversed(docs)]and all('body'not in r and'analysis'not in r for r in rows)
  for q in(dict(before_id=None,limit=51),dict(before_id=None,limit=0),dict(before_id=None,limit=25,body=True)):
   auth.refused(cur,lambda q=q:parent.schedule.rpc(cur,'erp_cp7_list_reports_v1',(json.dumps(q),),subject),'CP7_WIP_FIELDS'if'body'in q else'CP7_REPORT_INDEX_QUERY')
  return dict(status='PASS',keyset_page_complete_exactly_five_no_duplicate_or_body_fact_cache=True,declared_limit_closed_query=True)
 declared=[('TEMPLATES',templates),('UUID_REPLAY',replay),('ABSENT_FENCE',absent),('REVISION',revisions),('ACTUAL_COMPARISON',actual_comparison),('UNKNOWN_NOT_ZERO',unknown),('PERIOD_SCOPE',periods),('ENGINE_VERSION',engine_version),('CLOSED_PAYLOAD',closed_payload),('CURRENT_OPS_AUTH',ops_auth),('ACTOR_SCOPE',actor_scope),('CURRENT_FINANCE_AUTH',finance_auth),('IMMUTABLE',immutable),('DURABLE_PAGES',pages)]
 assert len(declared)==14
 return [('P15_REPORT_NATIVE_'+n,f)for n,f in declared]

def races(tools,today,parent):
 def fixture(subject=False):
  with tools.connect()as conn,conn.cursor()as cur:
   parent.setup(cur,today);actor,role=parent.auth.custom_actor(cur)if subject else(None,None);e=parent.capture(cur,today,subject=actor);conn.commit()
  return e,actor,role
 def concurrent(senders):
  barrier=threading.Barrier(2)
  def send(args):
   p,key,actor,lookup=args
   with tools.connect()as conn,conn.cursor()as cur:
    barrier.wait(timeout=5)
    try:r=command(cur,parent,p,key,actor,lookup);conn.commit();return r
    except psycopg.Error as e:conn.rollback();return dict(sqlstate=e.sqlstate,error=str(e))
  with ThreadPoolExecutor(max_workers=2)as pool:return [j.result(60)for j in[pool.submit(send,a)for a in senders]]
 def same_uuid():
  e,actor,_=fixture();p=payload(e);key=uuid.uuid4();rs=concurrent([(p,key,actor,False)]*2);assert all(r.get('status')=='COMMITTED'for r in rs)and rs[0]['document']==rs[1]['document']
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_analysis_native.publications where request_id=%s',(key,)).fetchone()[0]==1
  return dict(status='PASS',two_actual_publication_transactions_one_UUID_one_document=True)
 def absent_race():
  e,actor,_=fixture();p=payload(e);key=uuid.uuid4();rs=concurrent([(p,key,actor,False),(p,key,actor,True)]);assert rs[0]['status']==rs[1]['status']in('COMMITTED','CLOSED_UNCOMMITTED')
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_analysis_native.publications where request_id=%s',(key,)).fetchone()[0]==int(rs[0]['status']=='COMMITTED')
  return dict(status='PASS',actual_lookup_vs_commit_race_linearized_one_positive_or_sealed_negative_receipt=True)
 def revision_race():
  e,actor,_=fixture()
  with tools.connect()as conn,conn.cursor()as cur:one=command(cur,parent,payload(e))['document'];conn.commit()
  p=payload(e,prior=one);rs=concurrent([(p,uuid.uuid4(),actor,False),(p,uuid.uuid4(),actor,False)])
  assert sum(r.get('status')=='COMMITTED'for r in rs)==1 and any(r.get('sqlstate')=='40001'and'CP7_REPORT_REVISION_CHANGED'in r.get('error','')for r in rs),rs
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_analysis_native.publications where series_id=%s',(one['series_id'],)).fetchone()[0]==2
  return dict(status='PASS',actual_series_CAS_two_same_expected_revision_exactly_one_second_revision=True)
 def current_after_wait():
  e,actor,role=fixture(True);p=payload(e);key=uuid.uuid4()
  with tools.connect()as conn,conn.cursor()as cur:command(cur,parent,p,key,actor);conn.commit()
  with tools.connect()as holder,holder.cursor()as h:
   h.execute("select pg_advisory_xact_lock(hashtextextended('CP7:REPORT_REQUEST:'||%s||':'||%s,0))",(actor,str(key)))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=command(cur,parent,p,key,actor,True);conn.commit();return r
     except psycopg.Error as ex:conn.rollback();return dict(sqlstate=ex.sqlstate,error=str(ex))
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send);waiting=False;deadline=time.monotonic()+8
    try:
     with tools.connect(autocommit=True)as inspect,inspect.cursor()as c:
      while time.monotonic()<deadline:
       waiting=c.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like 'select public.erp_cp7_get_report_request_v1%')").fetchone()[0]
       if waiting:break
       time.sleep(.03)
     assert waiting,'P15_ACTUAL_PUBLICATION_REQUEST_LOCK_NOT_OBSERVED'
     with tools.connect()as conn,conn.cursor()as c:c.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'",(role,));conn.commit()
    finally:holder.rollback()
    r=job.result(60)
  assert r.get('sqlstate')=='42501'and'CP7_ACCESS_DENIED'in r.get('error',''),r
  return dict(status='PASS',observed_real_request_lock_current_rights_after_wait_before_cached_positive_receipt=True)
 return [('P15_REPORT_RACE_'+n,f)for n,f in [('UUID',same_uuid),('ABSENT_FENCE',absent_race),('REVISION',revision_race),('CURRENT_AUTH',current_after_wait)]]

def http_cases(http,today,parent):
 def lifecycle():
  owner=http.login('OWNER','p15-publication-owner');other=http.login('OWNER','p15-publication-other')
  with http.connect()as conn,conn.cursor()as cur:parent.setup(cur,today);conn.commit()
  captured=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=parent.previous.baseline.history.query(today),p_request=str(uuid.uuid4())));assert captured['status']==200,captured;e=captured['body'];p=payload(e);key=str(uuid.uuid4());args=dict(p_payload=p,p_request=key)
  one=owner.rpc('erp_cp7_publish_report_v1',args);assert one['status']==200,one;d=checked(one['body'],e,p,key);same=owner.rpc('erp_cp7_get_report_request_v1',args);assert same['status']==200 and same['body']['document']==d
  assert other.rpc('erp_cp7_read_report_v1',dict(p_id=d['id']))['status']==403 and http.anon_rpc('erp_cp7_read_report_v1',dict(p_id=d['id']))['status']in(401,403)
  assert other.rpc('erp_cp7_list_reports_v1',dict(p_query=dict(before_id=None,limit=25)))['body']['rows']==[]
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  for name,params in [('erp_cp7_read_report_v1',dict(p_id=d['id'])),('erp_cp7_publish_report_v1',args),('erp_cp7_get_report_request_v1',args),('erp_cp7_list_reports_v1',dict(p_query=dict(before_id=None,limit=25))),('erp_cp7_compare_reports_v1',dict(p_before=d['id'],p_after=d['id']))]:assert owner.rpc(name,params)['status']==403
  return dict(status='PASS',actual_Auth_PostgREST_publication_UUID_body_original_and_current403_all_consumers=True,anonymous_and_foreign_actor_refused=True)
 def absent():
  owner=http.login('OWNER','p15-publication-absent')
  with http.connect()as conn,conn.cursor()as cur:parent.setup(cur,today);conn.commit()
  c=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=parent.previous.baseline.history.query(today),p_request=str(uuid.uuid4())));assert c['status']==200;e=c['body'];args=dict(p_payload=payload(e),p_request=str(uuid.uuid4()))
  r=owner.rpc('erp_cp7_get_report_request_v1',args);assert r['status']==200 and r['body']['status']=='CLOSED_UNCOMMITTED'and r['body']['document']is None
  later=owner.rpc('erp_cp7_publish_report_v1',args);assert later['status']==200 and later['body']['status']=='CLOSED_UNCOMMITTED'
  with http.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_analysis_native.publications where request_id=%s',(args['p_request'],)).fetchone()[0]==0
  return dict(status='PASS',actual_Auth_HTTP_absent_lookup_permanently_closes_late_old_UUID_without_publication=True)
 return [('P15_REPORT_HTTP_CURRENT_AUTH',lifecycle),('P15_REPORT_HTTP_ABSENT_FENCE',absent)]
