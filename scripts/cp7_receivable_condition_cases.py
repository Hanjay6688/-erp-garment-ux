"""Read-only current Native AR conditions, not another balance/cash engine."""
import json,uuid
import cp7_attention_cases as attention
parent=attention.parent;auth,b=parent.auth,parent.b
sales=parent.previous.baseline.history.sales
def get(cur,run,subject=None):return attention.rpc(cur,'erp_cp7_get_analysis_receivable_conditions_v1',(run,),subject)
def documents(e):return[x for p in e['source']['pages']for x in p['page']['rows']]
def condition(e,source_id):return next(x for x in e['source']['conditions']if x['source_id']==source_id)
def checked(e,original):
 assert e['contract_version']=='cp7.native-ar-conditions.v1'and e['analysis']['analysis']==original['analysis']and e['analysis']['financial_source']==original['financial_source']
 s=e['source'];assert s['contract_version']=='cp7.native-ar-source.v1'and s['page_complete']and s['basis']=='ACCEPTED_P11_CURRENT_NATIVE_DOCUMENT'
 assert len(documents(e))==len(s['conditions'])==int(s['total'])and len({r['id']for r in documents(e)})==int(s['total'])
 assert all(p['read_at']==s['read_at']and p['financial_captured']and p['page']['total']==s['total']for p in s['pages'])
 return e
def cases(cur,today):
 def same_balance():
  parent.setup(cur,today);f=sales.fixture(cur,today,qty=20,price='25',stock=30);sales.fg.post_sale(cur,f['draft']);sales.payment(cur,f,today,'200')
  original=parent.capture(cur,today);before=b.boundary.snapshot(cur);e=checked(get(cur,original['run_id']),original)
  native=sales.read(cur,f);r=next(r for r in documents(e)if r['id']==f['sale']);assert r==native['page']['rows'][0]and r['financial']['open_balance']=='300.00'
  assert r['due_date']is None and condition(e,f['sale'])['state']=='MISSING_DUE_DATE'and not condition(e,f['sale'])['business_resolved']
  assert b.boundary.snapshot(cur)==before
  final=sales.payment(cur,dict(f,tag=f['tag']+'-final'),today,'300');paid=checked(get(cur,original['run_id']),original);assert condition(paid,f['sale'])['state']=='ZERO_BALANCE'and condition(paid,f['sale'])['business_resolved']
  sales.native(cur,'select erp.reverse_sales_payment(%s,%s)',(final,'P16 actual Native payment inverse'));reopened=checked(get(cur,original['run_id']),original)
  r=next(r for r in documents(reopened)if r['id']==f['sale']);assert r['financial']['open_balance']=='300.00'and condition(reopened,f['sale'])['state']=='MISSING_DUE_DATE'and not condition(reopened,f['sale'])['business_resolved']
  return dict(status='PASS',accepted_Native_header_identical_no_second_AR_calculator=True,actual500_invoice_paid200_remaining300_missing_due_not_invented=True,actual300_settlement_zero_and_inverse_reopens300=True,original_analysis_immutable_and_current_observation_read_only=True)
 def authority():
  original,e,subject=attention.prepared(cur,today,True);role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(subject,)).fetchone()[0]
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.ar.view')on conflict do nothing",(role,));observed=checked(get(cur,original['run_id'],subject),original)
  assert observed['actor_scope_id']==subject
  auth.refused(cur,lambda:get(cur,original['run_id']),'CP7_ANALYSIS_RUN_UNAVAILABLE')
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ar.view'",(role,));auth.refused(cur,lambda:get(cur,original['run_id'],subject),'CP7_REMINDER_AR_ACCESS_DENIED')
  assert parent.read(cur,original['run_id'],subject)['analysis']==original['analysis']
  return dict(status='PASS',Native_current_actor_and_AR_permission_before_any_AR_source=True,four_Ops_without_AR_keeps_original_Ops_but_refuses_money=True,active_disposable_STAFF_control_preserves_Native_policy=True)
 def full_scope():
  parent.setup(cur,today);ids=[]
  for i in range(26):ids.append(sales.fixture(cur,today,qty=1,price='25',stock=1,tag='P16-AR-PAGE-'+uuid.uuid4().hex[:12])['sale'])
  original=parent.capture(cur,today);before=b.boundary.snapshot(cur);e=checked(get(cur,original['run_id']),original)
  assert len(e['source']['pages'])>=2 and set(ids)<={r['id']for r in documents(e)}and all(condition(e,id)['state']=='DRAFT_ONLY'and not condition(e,id)['business_resolved']for id in ids)
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual26_Native_documents_all_complete_beyond_first25_page=True,drafts_do_not_create_debt_or_healthy_zero_conditions=True,one_native_statement_clock_no_business_DML=True)
 return attention.cases(cur,today)+[('P16_NATIVE_AR_CONDITION_'+n,f)for n,f in [('ACTUAL_BALANCE_DUE_SETTLE_INVERSE',same_balance),('CURRENT_ACTOR_AR_AUTH',authority),('COMPLETE_SOURCE26',full_scope)]]
def races(tools,today):return attention.races(tools,today)
def http_cases(http,today):
 def actual():
  owner=http.login('OWNER','p16-current-ar-source');other=http.login('OWNER','p16-current-ar-other')
  with http.connect()as conn,conn.cursor()as cur:
   parent.setup(cur,today);f=sales.fixture(cur,today,qty=20,price='25',stock=30);sales.fg.post_sale(cur,f['draft']);sales.payment(cur,f,today,'200');conn.commit()
  original=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=parent.previous.baseline.history.query(today),p_request=str(uuid.uuid4())));assert original['status']==200,original
  args=dict(p_run=original['body']['run_id']);e=owner.rpc('erp_cp7_get_analysis_receivable_conditions_v1',args);assert e['status']==200,e;checked(e['body'],original['body']);assert next(r for r in documents(e['body'])if r['id']==f['sale'])['financial']['open_balance']=='300.00'
  assert other.rpc('erp_cp7_get_analysis_receivable_conditions_v1',args)['status']==403 and http.anon_rpc('erp_cp7_get_analysis_receivable_conditions_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_get_analysis_receivable_conditions_v1',args)['status']==403
  return dict(status='PASS',actual_Auth_PostgREST_Native_AR_source500_200_300=True,foreign_anonymous_and_deactivated_actor_refused=True)
 return attention.http_cases(http,today)+[('P16_AR_SOURCE_HTTP_CURRENT_AUTH',actual)]
