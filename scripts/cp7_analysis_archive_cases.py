"""Current-authority durable original pointers; no stock/money facts in index."""
import json,sys,uuid
def pointer(e):
 return dict(runId=e['run_id'],requestId=e['request_id'],query=e['query'],capturedAt=e['analysis']['snapshot']['generated_at'],sourceHash=e['analysis']['snapshot']['source_hash'],semanticHash=e['analysis']['semantic_hash'])
def listing(cur,parent,before=None,limit=25,subject=None):
 return parent.schedule.rpc(cur,'erp_cp7_list_analysis_archives_v1',(json.dumps(dict(before_run=before,limit=limit)),),subject)
def checked(e,subject,limit):
 assert set(e)=={'contract_version','actor_scope_id','rows','total_visible','next_before_run','page_complete','read_at'}and e['contract_version']=='cp7.native-analysis-archives.v1'
 assert e['actor_scope_id']==subject and e['page_complete']and len(e['rows'])<=limit and isinstance(e['total_visible'],str)
 assert all(set(r)=={'runId','requestId','query','capturedAt','sourceHash','semanticHash'}for r in e['rows'])
 assert len({r['runId']for r in e['rows']})==len(e['rows'])
 if e['next_before_run']is not None:assert len(e['rows'])==limit and e['next_before_run']==e['rows'][-1]['runId']
 return e
def cases(cur,today,parent):
 auth,b=parent.auth,parent.b
 def pages():
  parent.setup(cur,today);subject,_=auth.custom_actor(cur);original=[]
  for mode in('AS_SOLD','RESTATED','AS_SOLD'):
   q=parent.previous.baseline.history.query(today);q['group_mode']=mode;original.append(parent.capture(cur,today,subject=subject,q=q))
  key=original[0]['request_id'];assert parent.capture(cur,today,key,subject)['run_id']==original[0]['run_id']
  before=b.boundary.snapshot(cur);first=checked(listing(cur,parent,limit=2,subject=subject),subject,2);second=checked(listing(cur,parent,first['next_before_run'],2,subject),subject,2)
  assert first['total_visible']==second['total_visible']=='3'and second['next_before_run']is None
  assert first['rows']+second['rows']==[pointer(e)for e in reversed(original)]
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',durable_actor_originals_keyset_pages_complete_no_duplicate_cached_UUID=True,exact_original_query_capture_hashes_no_cached_facts=True,no_business_DML=True)
 def ownership():
  parent.setup(cur,today);subject,_=auth.custom_actor(cur);other,_=auth.custom_actor(cur);original=parent.capture(cur,today,subject=subject)
  assert listing(cur,parent,subject=subject)['rows']==[pointer(original)]and listing(cur,parent,subject=other)['rows']==[]
  auth.refused(cur,lambda:listing(cur,parent,original['run_id'],subject=other),'CP7_ANALYSIS_ARCHIVE_CURSOR_UNAVAILABLE')
  for q in[dict(before_run=None,limit=51),dict(before_run=None,limit=0),dict(before_run=None,limit=25,financial_source={}),dict(limit=25)]:
   auth.refused(cur,lambda q=q:parent.schedule.rpc(cur,'erp_cp7_list_analysis_archives_v1',(json.dumps(q),),subject),'CP7_ANALYSIS_ARCHIVE_QUERY')
  return dict(status='PASS',only_current_actor_originals_visible=True,another_actor_cursor_and_extra_query_keys_refused=True)
 def finance(preflight=False):
  parent.setup(cur,today);subject,role=parent.financial_cases.admin_actor(cur,parent);original=parent.capture(cur,today,subject=subject)
  assert original['financial_source']is not None and original['financial_source']['report']['close_preflight']is not None
  key='finance.period_close.manage'if preflight else'finance.reports.view';cur.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s',(role,key))
  assert listing(cur,parent,subject=subject)['rows']==[]
  auth.refused(cur,lambda:listing(cur,parent,original['run_id'],subject=subject),'CP7_ANALYSIS_ARCHIVE_CURSOR_UNAVAILABLE')
  fresh=parent.capture(cur,today,subject=subject);visible=listing(cur,parent,subject=subject);assert visible['total_visible']=='1'and visible['rows']==[pointer(fresh)]
  cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)',(role,key));restored=listing(cur,parent,subject=subject)
  assert restored['total_visible']=='2'and restored['rows']==[pointer(fresh),pointer(original)]
  assert parent.read(cur,original['run_id'],subject)['analysis']==original['analysis']
  return dict(status='PASS',revoked_permission=key,current_capability_filters_before_page_and_total=True,protected_original_cursor_unavailable=True,restored_capability_reopens_identical_original=True)
 def revoked():
  parent.setup(cur,today);subject,role=auth.custom_actor(cur);original=parent.capture(cur,today,subject=subject)
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='production.wip.view'",(role,))
  auth.refused(cur,lambda:listing(cur,parent,subject=subject),'CP7_ACCESS_DENIED');auth.refused(cur,lambda:listing(cur,parent,original['run_id'],subject=subject),'CP7_ACCESS_DENIED')
  return dict(status='PASS',current_four_Ops_authority_before_any_index_or_cursor=True)
 def stale():
  parent.setup(cur,today);original=parent.capture(cur,today);before=listing(cur,parent)
  definition=cur.execute("select pg_get_functiondef('cp7_analysis_native.fact(text,text,jsonb,jsonb)'::regprocedure)").fetchone()[0];assert'SOURCE_INPUT_NOT_PROVEN'in definition
  cur.execute(definition.replace('SOURCE_INPUT_NOT_PROVEN','SOURCE_INPUT_NOT_PROVEN_ARCHIVE_REVISED'),prepare=False)
  assert listing(cur,parent)['rows']==before['rows'];read=parent.read(cur,original['run_id'])
  assert read['source_state']=='ARCHIVED_STALE'and read['analysis']==original['analysis']and read['financial_source']==original['financial_source']
  return dict(status='PASS',index_never_recalculates_or_changes_original_report=True,opening_uses_actual_current_source_check_preserves_original_body=True)
 return [('P15_NATIVE_ARCHIVE_'+n,f)for n,f in [('DURABLE_PAGES',pages),('ACTOR_QUERY_BOUNDARY',ownership),('CURRENT_REPORT_AUTH',finance),('CURRENT_PREFLIGHT_AUTH',lambda:finance(True)),('CURRENT_OPS_AUTH',revoked),('ORIGINAL_SOURCE_CHANGED',stale)]]
def http_cases(http,today,parent):
 def current():
  owner=http.login('OWNER','p15-server-archive-owner');other=http.login('OWNER','p15-server-archive-other')
  with http.connect()as conn,conn.cursor()as cur:parent.setup(cur,today);conn.commit()
  args=dict(p_query=parent.previous.baseline.history.query(today),p_request=str(uuid.uuid4()));capture=owner.rpc('erp_cp7_capture_analysis_v1',args);assert capture['status']==200,capture
  params=dict(p_query=dict(before_run=None,limit=25));first=owner.rpc('erp_cp7_list_analysis_archives_v1',params);assert first['status']==200 and first['body']['rows']==[pointer(capture['body'])]
  assert other.rpc('erp_cp7_list_analysis_archives_v1',params)['body']['rows']==[]
  assert other.rpc('erp_cp7_list_analysis_archives_v1',dict(p_query=dict(before_run=capture['body']['run_id'],limit=25)))['status']==403
  assert http.anon_rpc('erp_cp7_list_analysis_archives_v1',params)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_list_analysis_archives_v1',params)['status']==403
  return dict(status='PASS',actual_Auth_PostgREST_durable_original_index_actor_cursor_boundary=True,anonymous_and_current_deactivation_refused=True)
 return [('P15_ARCHIVE_HTTP_CURRENT_AUTH',current)]
