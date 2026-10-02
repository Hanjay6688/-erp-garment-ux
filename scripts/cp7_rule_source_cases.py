"""Fixed extension: 18 DB, five actual races and four real Auth/HTTP cases.

Every retained policy/material/attention case remains. Local capture is never
external delivery. Fault controls and pure episode kernels are labelled.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
import hashlib,json,threading,time,uuid
import psycopg
import cp7_rule_policy_cases as previous
import cp7_obligation_episode_cases as obligations
parent,auth,b,attention=previous.parent,previous.auth,previous.b,previous.attention
ar,ap=obligations.ar,obligations.previous

def rpc(cur,name,p,subject=None):return attention.rpc(cur,name,p,subject)
def source(cur,e,subject=None):return rpc(cur,'erp_cp7_get_rule_conditions_v1',(e['run_id'],),subject)
def local(cur,e,subject=None):return rpc(cur,'erp_cp7_get_local_reminders_v1',(e['run_id'],),subject)
def command(cur,op,p,key=None,subject=None,lookup=False):
 key=key or uuid.uuid4()
 names=dict(EPISODES='erp_cp7_evaluate_rule_episodes_v1',BINDING='erp_cp7_save_local_binding_v1',PREVIEW='erp_cp7_claim_local_preview_v1',OUTCOME='erp_cp7_finish_local_preview_v1',RESOLUTION='erp_cp7_resolve_local_preview_v1')
 if lookup:return rpc(cur,'erp_cp7_get_rule_episode_request_v1'if op=='EPISODES'else'erp_cp7_get_local_reminder_request_v1',(json.dumps(p),key)if op=='EPISODES'else(json.dumps(p),key,op),subject)
 return rpc(cur,names[op],(json.dumps(p),key),subject)
def observe(cur,e,subject=None,key=None,p=None,lookup=False):
 s=source(cur,e,subject)if p is None else None
 return command(cur,'EPISODES',p or dict(run_id=e['run_id'],source_hash=s['source_hash']),key,subject,lookup)
def row(s,key):return next(r for r in s['rows']if r['key']==key)
def observation(e,key):return next(r for r in e['result']['rows']if r['condition']['key']==key)
def binding_payload(e,revision='0',enabled=True,rules=None):return dict(run_id=e['run_id'],expected_revision=revision,enabled=enabled,label='Tujuan pemeriksaan lokal · bukan penerima WhatsApp',environment='LOCAL_TEST_SINK',rules=rules or['AR_DUE'],reason='Explicit disposable Native local rehearsal; not an operating setting')
def bind(cur,e,revision='0',enabled=True,subject=None,rules=None):return command(cur,'BINDING',binding_payload(e,revision,enabled,rules),subject=subject)
def claim_payload(e,w,key):return dict(run_id=e['run_id'],condition_key=key,source_hash=w['source']['source_hash'],binding_id=w['binding']['id'])
def claim(cur,e,key,subject=None,request=None):return command(cur,'PREVIEW',claim_payload(e,local(cur,e,subject),key),request,subject)
def claim_row(e):return next(c for c in e['workspace']['claims']if c['id']==e['result']['claim_id'])
def outcome_payload(e,c,outcome='LOCAL_CAPTURE'):return dict(run_id=e['run_id'],claim_id=c['id'],fence=c['fence'],outcome=outcome)
def finish(cur,e,c,outcome='LOCAL_CAPTURE',subject=None,key=None):return command(cur,'OUTCOME',outcome_payload(e,c,outcome),key,subject)
def resolution_payload(e,c,outcome='NOT_CAPTURED_CONFIRMED'):return dict(run_id=e['run_id'],claim_id=c['id'],fence=c['fence'],outcome=outcome,reason='Operator explicitly inspected the local result; no automatic resend')
def resolve(cur,e,c,outcome='NOT_CAPTURED_CONFIRMED',subject=None,key=None):return command(cur,'RESOLUTION',resolution_payload(e,c,outcome),key,subject)
def counts(cur):return tuple(cur.execute('select count(*)from cp7_reminder_native.'+t).fetchone()[0]for t in('rule_episodes','rule_observations','local_bindings','local_claims','local_resolutions','requests'))
def due_fixture(cur,today,due=True,subject=None,setup=True):
 if setup:parent.setup(cur,today)
 f=ar.sales.fixture(cur,today,qty=20,price='25',stock=30)
 if due:
  version=cur.execute('select row_version from erp.sales_headers where id=%s',(f['sale'],)).fetchone()[0]
  p=dict(sale_id=f['sale'],sale_number=f['tag'],customer_id=f['customer'],source_location_id=f['location'],sale_date=f['sale_at'],due_date=(today-timedelta(days=1)).isoformat(),reason='Native rule rehearsal explicit recorded due date',items=[dict(product_id=f['product'],qty_pcs=20,unit_price_snapshot='25',discount_amount='0')])
  f['draft']=b.chain.production.rpc(cur,'erp.save_sale_draft_v2',p,uuid.uuid4(),version);b.api.admin(cur)
 ar.sales.fg.post_sale(cur,f['draft']);ar.sales.payment(cur,f,today,'200')
 e=parent.capture(cur,today,subject=subject);return f,e,'AR_DUE:'+f['sale']
def configure(cur,e,rule='AR_DUE',c=None,revision='0',subject=None):return previous.command(cur,previous.intent(e,rule,revision,c or previous.ready(unit='DAY'if rule in('AR_DUE','AP_DUE')else'PCS')),subject=subject)
def prepared(cur,today,subject=None,setup=True):
 f,e,key=due_fixture(cur,today,subject=subject,setup=setup);configure(cur,e,subject=subject);bind(cur,e,subject=subject);observe(cur,e,subject);return f,e,key
def managed_actor(cur):
 subject,role=previous.admin(cur)
 for permission in('finance.ar.view','finance.ap.view'):cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,permission))
 return subject,role
def history(cur,e,before=None,through=None,subject=None):
 p=dict(run_id=e['run_id'],rule_id='PRODUCTION_GAP',scope_kind='GLOBAL',scope_key='*',before_revision=before,through_revision=through,limit=25)
 return rpc(cur,'erp_cp7_get_reminder_policy_history_v1',(json.dumps(p),),subject)

def cases(cur,today):
 def history_pages():
  e=previous.fixture(cur,today);before=b.boundary.snapshot(cur)
  for n in range(27):configure(cur,e,'PRODUCTION_GAP',dict(previous.ready(),enabled=n%2==0),str(n))
  first=history(cur,e);assert len(first['rows'])==25 and first['total']=='27'and first['through_revision']=='27'and first['next_before_revision']=='3'
  configure(cur,e,'PRODUCTION_GAP',previous.ready(), '27');second=history(cur,e,first['next_before_revision'],first['through_revision'])
  assert [r['revision']for r in second['rows']]==['2','1']and second['total']=='27'and second['next_before_revision']is None
  all_rows=first['rows']+second['rows'];assert len({r['policy_id']for r in all_rows})==27 and all_rows[-1]['previous_id']is None
  assert all(a['previous_id']==z['policy_id']for a,z in zip(all_rows,all_rows[1:]))and b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual27_saved_versions_complete25_plus2_fixed_history_boundary_survives_new28=True,immutable_predecessor_links_no_business_effect=True)
 def history_auth():
  e=previous.fixture(cur,today);configure(cur,e,'PRODUCTION_GAP');assert history(cur,e)['rows']
  subject,_=managed_actor(cur);own=parent.capture(cur,today,subject=subject)
  auth.refused(cur,lambda:history(cur,e,subject=subject),'CP7_ANALYSIS_RUN_UNAVAILABLE')
  auth.refused(cur,lambda:history(cur,own,through='99',subject=subject),'CP7_POLICY_HISTORY_BOUNDARY')
  cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(subject,));auth.refused(cur,lambda:history(cur,own,subject=subject),'CP7_REMINDER_ACCESS_DENIED')
  return dict(status='PASS',history_current_own_Original_actor_and_exact_boundary_not_arbitrary_cursor=True)
 def exact_source():
  f,e,key=due_fixture(cur,today);before=b.boundary.snapshot(cur);s=source(cur,e);s2=source(cur,e)
  assert s['page_complete']and len(s['rows'])==int(s['total'])and s['source_hash']==s2['source_hash']and s['analysis']['analysis']==e['analysis']and s['analysis']['financial_source']==e['financial_source']
  assert row(s,key)['state']=='ACTIVE'and row(s,key)['value']['value']=='1'and not row(s,key)['business_resolved']
  assert row(s,key)['label']==f['tag']+' · '+ar.sales.read(cur,f)['detail']['customer_name']
  for r in s['rows']:
   if r['rule_id']=='PRODUCTION_GAP':assert r['value']==next(a['q_conditional']for a in e['analysis']['recommendations']if a['target']['key']==r['target_key'])
   if r['rule_id']=='ACCESSORY_NEED':assert r['value']==next(a['additional_external']for a in e['analysis']['material_needs']if a['target_key']==r['target_key']and a['material_key']==r['material_key'])
  assert s['contract_version']=='cp7.native-rule-conditions.v2'
  assert s['coverage']['opening_ar']==s['coverage']['opening_ap']=='COMPLETE_NATIVE_DOCUMENT_SCOPE_CONTRACTOR_CASH_ADVANCE_EXCLUDED'
  assert s['coverage']['payroll_ap']=='COMPLETE_NATIVE_DOCUMENT_SCOPE'
  assert s['coverage']['accessory_ap']=='COMPLETE_NATIVE_RETURN_CARRY_SCOPE_UNKNOWN_UNALLOCATED_BALANCE_RETAINED'
  assert s['coverage']['laundry_ap']=='COMPLETE_NATIVE_INVOICE_RECEIPT_AND_OPENING_UNINVOICED_SCOPE_UNKNOWN_PENDING_RETAINED'
  assert not s['full_family_acceptance']and b.boundary.snapshot(cur)==before
  # This admission helper can inspect only the current actor's immutable
  # identity/capability flags. It must not replace the final fresh Native read.
  auth.actor(cur);claims=cur.execute("select current_setting('request.jwt.claims',true)").fetchone()[0]
  b.api.admin(cur);cur.execute('savepoint authority_fresh_read_control')
  try:
   cur.execute("select set_config('request.jwt.claims',%s,true)",(claims,));cur.execute('set local role cp7_reminder')
   pocket=cur.execute('select cp7_reminder_native.original_authority(%s)',(e['run_id'],)).fetchone()[0]
   assert pocket['analysis']['analysis']['semantic_hash']==e['analysis']['semantic_hash']
   assert [r['target']['key']for r in pocket['analysis']['analysis']['recommendations']]==[r['target']['key']for r in e['analysis']['recommendations']]
   assert 'source_state'not in pocket['analysis']and all(set(r)=={'target'}and set(r['target'])=={'key'}for r in pocket['analysis']['analysis']['recommendations'])
   b.api.admin(cur)
   cur.execute("create or replace function cp7_analysis_native.source(q jsonb)returns jsonb language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$begin raise exception 'CP7_TEST_FRESH_NATIVE_READER_REQUIRED';end $$",prepare=False)
   cur.execute("select set_config('request.jwt.claims',%s,true)",(claims,));cur.execute('set local role cp7_reminder')
   assert cur.execute('select cp7_reminder_native.original_authority(%s)',(e['run_id'],)).fetchone()[0]==pocket
   auth.refused(cur,lambda:source(cur,e),'CP7_TEST_FRESH_NATIVE_READER_REQUIRED')
  finally:
   cur.execute('rollback to savepoint authority_fresh_read_control');cur.execute('release savepoint authority_fresh_read_control');b.api.admin(cur)
  assert source(cur,e)['analysis']==s['analysis']and b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_current_Native_AR_recorded_due_and_exact_original_production_material_facts=True,stable_semantic_source_hash_no_clock_noise_no_hidden_complete_claim=True,private_admission_contains_only_original_identity_targets_capability_flags=True,failed_fresh_Native_reader_cannot_be_replaced_by_private_admission=True)
 def missing_zero():
  f,e,key=due_fixture(cur,today,False);s=source(cur,e);r=row(s,key);assert r['state']=='DATA_REVIEW'and r['value']['state']=='UNKNOWN'and not r['business_resolved']
  ar.sales.payment(cur,dict(f,tag=f['tag']+'-final'),today,'300');r=row(source(cur,e),key);assert r['state']=='RESOLVED'and r['business_resolved']and r['value']['state']=='UNKNOWN'
  return dict(status='PASS',actual_missing_due_not_zero_days_or_healthy=True,actual_zero_balance_resolves_business_even_without_due_date=True)
 def material_invoice():
  f,e=ap.prepared(cur,today);key='AP_DUE:MATERIAL:'+f['receipt']['purchase_id'];r=row(source(cur,e),key)
  assert r['state']=='DATA_REVIEW'and r['reason']=='INVOICE_PENDING'and not r['business_resolved']
  ap.finalize(cur,f,today);ap.payment(cur,f,today,'200');r=row(source(cur,e),key);assert r['state']=='ACTIVE'and r['value']['value']=='1'
  ap.payment(cur,f,today,'300');r=row(source(cur,e),key);assert r['state']=='RESOLVED'and r['business_resolved']
  return dict(status='PASS',actual_GRNI500_balance0_not_false_resolution=True,Native_final500_paid200_then300_due_and_resolution_copied_no_second_AP_formula=True)
 def domain_scope():
  parent.setup(cur,today);subject,role=managed_actor(cur);f,e,key=due_fixture(cur,today,subject=subject,setup=False);assert row(source(cur,e,subject),key)
  cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key in('finance.ar.view','finance.ap.view')",(role,));s=source(cur,e,subject)
  assert s['coverage']['sales_ar']==s['coverage']['material_ap']=='EXCLUDED_BY_CURRENT_RIGHTS'and all(r['rule_id']not in('AR_DUE','AP_DUE')for r in s['rows'])
  return dict(status='PASS',current_domain_rights_filter_complete_authorized_source_not_fabricated_zero=True,own_Ops_original_remains_visible=True)
 def recurrence():
  f,e,key=due_fixture(cur,today);one=observation(observe(cur,e),key)['episode'];again=observation(observe(cur,e),key)['episode'];assert one['id']==again['id']and one['first_observed_at']==again['first_observed_at']
  paid=ar.sales.payment(cur,dict(f,tag=f['tag']+'-final'),today,'300');closed=observation(observe(cur,e),key)['episode'];assert closed['id']==one['id']and closed['state']=='RESOLVED'
  ar.sales.native(cur,'select erp.reverse_sales_payment(%s,%s)',(paid,'Native generic rule recurrence control'));r=observation(observe(cur,e),key)
  assert r['transition']=='REOPENED_NEW_EPISODE'and r['episode']['number']=='2'and r['episode']['previous_id']==one['id']and r['episode']['id']!=one['id']
  auth.refused(cur,lambda:cur.execute("update cp7_reminder_native.rule_episodes set state='ACTIVE',resolved_at=null where id=%s",(one['id'],)),'CP7_RULE_EPISODE_IMMUTABLE')
  return dict(status='PASS',actual_recorded_due_AR500_200_300_inverse_linked_recurrence=True,age_persisted_closed_episode_immutable=True)
 def review_not_resolution():
  f,e,key=due_fixture(cur,today);first=observation(observe(cur,e),key)['episode'];before=b.boundary.snapshot(cur)
  w=attention.get(cur,e['run_id']);attention.command(cur,attention.intent(w,'DONE'));last=observation(observe(cur,e),key)
  assert last['episode']['id']==first['id']and last['episode']['first_observed_at']==first['first_observed_at']and last['episode']['state']=='ACTIVE'and not last['condition']['business_resolved']and b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_DONE_review_never_closes_unpaid_business_condition_or_resets_its_age=True)
 def unknown_retained():
  f,e,key=due_fixture(cur,today);first=observation(observe(cur,e),key)['episode'];before=b.boundary.snapshot(cur)
  definition=cur.execute("select pg_get_functiondef('cp7_reminder_native.receivable_source()'::regprocedure)").fetchone()[0]
  # Explicit private-source corruption control: keep real Native rows and only
  # replace due evidence. Never fabricate an actual financial balance/event.
  try:
   cur.execute(definition.replace('cp7_reminder_native.receivable_source()', 'cp7_reminder_native.rule_test_real_ar_source()'))
   cur.execute("create or replace function cp7_reminder_native.receivable_source()returns jsonb language plpgsql stable security invoker set search_path=''set TimeZone='UTC'as $$declare s jsonb;v jsonb;begin s:=cp7_reminder_native.rule_test_real_ar_source();select jsonb_agg(case when x->>'source_id'=%s then x||jsonb_build_object('state','MISSING_DUE_DATE','business_resolved',false)else x end)into v from jsonb_array_elements(s->'conditions')x;return s||jsonb_build_object('conditions',v);end$$".replace('%s',"'"+f['sale']+"'"))
   r=observation(observe(cur,e),key);assert r['transition']=='UNKNOWN_RETAINED'and r['episode']['id']==first['id']and r['episode']['freshness']=='UNKNOWN'and r['episode']['first_observed_at']==first['first_observed_at']and not r['condition']['business_resolved']
  finally:cur.execute(definition);cur.execute('drop function cp7_reminder_native.rule_test_real_ar_source()')
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',fixture_kind='EXPLICIT_PRIVATE_SOURCE_FAULT_CONTROL',unknown_keeps_original_active_episode_and_age_no_false_heal=True,no_fabricated_Native_financial_balance=True)
 def episode_recovery():
  f,e,key=due_fixture(cur,today);s=source(cur,e);p=dict(run_id=e['run_id'],source_hash=s['source_hash']);request=uuid.uuid4();one=command(cur,'EPISODES',p,request);before=counts(cur)
  assert command(cur,'EPISODES',p,request,lookup=True)['result']==one['result']and counts(cur)==before
  auth.refused(cur,lambda:command(cur,'EPISODES',dict(p,source_hash='0'*64),request),'CP7_REMINDER_REQUEST_CHANGED')
  absent=uuid.uuid4();sealed=command(cur,'EPISODES',p,absent,lookup=True);before=counts(cur);late=command(cur,'EPISODES',p,absent)
  assert sealed['result']==late['result']and sealed['result']['status']=='NOT_COMMITTED'and counts(cur)==before
  configure(cur,e);auth.refused(cur,lambda:command(cur,'EPISODES',p),'CP7_RULE_EPISODE_SOURCE_CHANGED')
  return dict(status='PASS',actual_exact_replay_sealed_absent_and_stale_source_refusal_no_extra_episode=True)
 def binding_versions():
  f,e,key=due_fixture(cur,today);before=b.boundary.snapshot(cur);p=binding_payload(e);request=uuid.uuid4();one=command(cur,'BINDING',p,request);two=bind(cur,e,'1',False)
  assert one['workspace']['binding']['id']==two['workspace']['binding']['previous_id']and two['workspace']['binding']['revision']=='2'and not two['workspace']['binding']['enabled']
  assert command(cur,'BINDING',p,request)['result']==one['result']and command(cur,'BINDING',p,request)['workspace']['binding']==two['workspace']['binding']
  auth.refused(cur,lambda:bind(cur,e),'CP7_LOCAL_BINDING_STALE');auth.refused(cur,lambda:command(cur,'BINDING',dict(p,environment='WHATSAPP_LIVE')),'CP7_LOCAL_BINDING_PAYLOAD')
  auth.refused(cur,lambda:cur.execute("update cp7_reminder_native.local_bindings set enabled=false where id=%s",(one['result']['binding_id'],)),'CP7_REMINDER_REQUEST_IMMUTABLE')
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_actor_bound_immutable_versions_CAS_explicit_local_environment=True,no_live_binding_or_ERP_effect=True)
 def capture_body():
  f,e,key=prepared(cur,today);before=b.boundary.snapshot(cur);request=uuid.uuid4();w=local(cur,e);p=claim_payload(e,w,key);one=command(cur,'PREVIEW',p,request);c=claim_row(one)
  assert c['status']=='CLAIMED'and c['body_sha256']==hashlib.sha256(c['body'].encode()).hexdigest()and f['tag']in c['body']and 'BELUM DIKIRIM'in c['body']
  two=command(cur,'PREVIEW',p);assert two['result']['claim_id']==c['id']and command(cur,'PREVIEW',p,request,lookup=True)['result']==one['result']
  final=finish(cur,e,c);assert claim_row(final)['status']=='LOCAL_SINK_CAPTURED'and not final['workspace']['sent']and not final['workspace']['external_delivery_enabled']and not row(final['workspace']['source'],key)['business_resolved']
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_same_occurrence_new_UUID_dedup_exact_UTF8_body_and_hash=True,local_capture_not_SENT_or_business_resolution_entire_ERP_unchanged=True)
 def ambiguity():
  f,e,key=prepared(cur,today);c=claim_row(claim(cur,e,key));held=finish(cur,e,c,'UNKNOWN');assert claim_row(held)['status']=='UNKNOWN'
  bind(cur,e,'1');observe(cur,e);auth.refused(cur,lambda:claim(cur,e,key),'CP7_LOCAL_AMBIGUOUS_EPISODE_NO_NEW_OCCURRENCE')
  assert cur.execute('select count(*)from cp7_reminder_native.local_claims where condition_key=%s',(key,)).fetchone()[0]==1
  return dict(status='PASS',actual_unknown_outcome_new_binding_and_new_UUID_cannot_manufacture_second_occurrence=True,uncertain_claim_and_fence_retained=True)
 def manual_resolution():
  f,e,key=prepared(cur,today);c=claim_row(claim(cur,e,key));finish(cur,e,c,'UNKNOWN');request=uuid.uuid4();p=resolution_payload(e,c);resolved=command(cur,'RESOLUTION',p,request)
  assert claim_row(resolved)['status']=='UNKNOWN'and claim_row(resolved)['resolution']['outcome']=='NOT_CAPTURED_CONFIRMED'
  assert command(cur,'RESOLUTION',p,request,lookup=True)['result']==resolved['result'];auth.refused(cur,lambda:resolve(cur,e,c),'CP7_LOCAL_ALREADY_RESOLVED')
  next_claim=claim_row(claim(cur,e,key));assert next_claim['id']!=c['id']and next_claim['fence']!=c['fence']and next_claim['occurrence_key']!=c['occurrence_key']
  auth.refused(cur,lambda:cur.execute("delete from cp7_reminder_native.local_resolutions where claim_id=%s",(c['id'],)),'CP7_REMINDER_REQUEST_IMMUTABLE')
  return dict(status='PASS',explicit_reviewed_non_capture_allows_one_new_manual_attempt_original_UNKNOWN_body_fence_immutable=True,no_automatic_resend_or_business_resolution=True)
 def suppress_changed():
  f,e,key=prepared(cur,today);c=claim_row(claim(cur,e,key));configure(cur,e,c=dict(previous.ready(unit='DAY'),enabled=False),revision='1');final=finish(cur,e,c)
  assert claim_row(final)['status']=='SUPPRESSED'and claim_row(final)['body']is None
  assert cur.execute('select state from cp7_reminder_native.rule_episodes where id=%s',(c['episode_id'],)).fetchone()[0]=='ACTIVE'
  return dict(status='PASS',actual_policy_disabled_after_claim_suppresses_delayed_callback_and_old_body=True,disabled_delivery_not_business_healing=True)
 def actual_heal():
  f,e,key=prepared(cur,today);c=claim_row(claim(cur,e,key));ar.sales.payment(cur,dict(f,tag=f['tag']+'-finish'),today,'300');observation_now=observation(observe(cur,e),key);final=finish(cur,e,c)
  assert observation_now['episode']['state']=='RESOLVED'and claim_row(final)['status']=='SUPPRESSED'and row(final['workspace']['source'],key)['business_resolved']
  return dict(status='PASS',actual_Native_full_payment_heals_source_episode_and_suppresses_old_callback=True)
 def fencing_absence():
  f,e,key=prepared(cur,today);c=claim_row(claim(cur,e,key));before=counts(cur);wrong=outcome_payload(e,c);wrong['fence']=str(uuid.uuid4());auth.refused(cur,lambda:command(cur,'OUTCOME',wrong),'CP7_LOCAL_FENCE_DENIED');assert counts(cur)==before
  p=outcome_payload(e,c);request=uuid.uuid4();sealed=command(cur,'OUTCOME',p,request,lookup=True);late=command(cur,'OUTCOME',p,request);assert sealed['result']==late['result']and claim_row(late)['status']=='CLAIMED'
  for who in('anon','authenticated','service_role'):
   for table in('local_bindings','local_claims','local_resolutions','rule_episodes','rule_observations'):assert not cur.execute('select has_table_privilege(%s,%s,\'SELECT,INSERT,UPDATE,DELETE\')',(who,'cp7_reminder_native.'+table)).fetchone()[0]
  assert not cur.execute("select exists(select 1 from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='erp'and c.relkind in('r','p','v')and has_table_privilege('cp7_reminder',c.oid,'INSERT,UPDATE,DELETE,TRUNCATE,TRIGGER'))").fetchone()[0]
  return dict(status='PASS',wrong_fence_refused_no_write_absent_outcome_sealed_against_late_callback=True,no_private_access_or_ERP_business_DML_grant=True)
 def cooldown():
  f,e,key=prepared(cur,today);c=claim_row(claim(cur,e,key));finish(cur,e,c,'UNKNOWN');resolve(cur,e,c,'CAPTURE_CONFIRMED');configure(cur,e,c=previous.ready(unit='DAY',cooldown='30'),revision='1');bind(cur,e,'1');observe(cur,e)
  auth.refused(cur,lambda:claim(cur,e,key),'CP7_LOCAL_COOLDOWN_OR_QUIET');assert cur.execute('select count(*)from cp7_reminder_native.local_claims where condition_key=%s',(key,)).fetchone()[0]==1
  return dict(status='PASS',actual_manual_capture_confirmation_counts_for_current_cooldown_across_binding_and_policy_versions=True,UNKNOWN_history_stays_immutable=True)
 extra=[('POLICY_HISTORY_PAGES',history_pages),('POLICY_HISTORY_AUTH',history_auth),('EXACT_CURRENT_SOURCE',exact_source),('MISSING_DUE_ZERO',missing_zero),('NATIVE_MATERIAL_AP',material_invoice),('CURRENT_DOMAIN_SCOPE',domain_scope),('EPISODE_RECURRENCE',recurrence),('REVIEW_NOT_RESOLUTION',review_not_resolution),('UNKNOWN_AGE_RETAINED',unknown_retained),('EPISODE_UUID_RECOVERY',episode_recovery),('LOCAL_BINDING_VERSIONS',binding_versions),('LOCAL_UTF8_CAPTURE',capture_body),('LOCAL_AMBIGUITY',ambiguity),('LOCAL_MANUAL_RESOLUTION',manual_resolution),('LOCAL_DISABLED_SUPPRESSION',suppress_changed),('LOCAL_NATIVE_HEAL',actual_heal),('LOCAL_FENCE_ABSENCE_ACL',fencing_absence),('LOCAL_ACTUAL_COOLDOWN',cooldown)]
 assert len(extra)==18
 return previous.cases(cur,today)+[('P16_RULE_SOURCE_'+name,fn)for name,fn in extra]

def wait_for(tools,sql_name):
 deadline=time.monotonic()+12
 with tools.connect(autocommit=True)as conn,conn.cursor()as cur:
  while time.monotonic()<deadline:
   if cur.execute("select exists(select 1 from pg_stat_activity where datname=current_database()and wait_event='advisory'and query like %s)",('select public.'+sql_name+'%',)).fetchone()[0]:return
   time.sleep(.03)
 raise AssertionError('RULE_SOURCE_REAL_WAIT_NOT_OBSERVED:'+sql_name)

def races(tools,today):
 def duplicate():
  with tools.connect()as conn,conn.cursor()as cur:f,e,key=prepared(cur,today);p=claim_payload(e,local(cur,e),key);conn.commit()
  gate=threading.Barrier(2)
  def send():
   with tools.connect()as conn,conn.cursor()as cur:gate.wait(5);r=command(cur,'PREVIEW',p);conn.commit();return r
  with ThreadPoolExecutor(max_workers=2)as pool:results=[j.result(90)for j in[pool.submit(send),pool.submit(send)]]
  assert results[0]['result']['claim_id']==results[1]['result']['claim_id']and results[0]['result']['fence']==results[1]['result']['fence']
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_reminder_native.local_claims where condition_key=%s',(key,)).fetchone()[0]==1
  return dict(status='PASS',two_actual_transactions_distinct_UUID_same_occurrence_one_fenced_local_claim=True)
 def revoke_manage():
  with tools.connect()as conn,conn.cursor()as cur:parent.setup(cur,today);subject,role=managed_actor(cur);f,e,key=prepared(cur,today,subject,False);p=claim_payload(e,local(cur,e,subject),key);request=uuid.uuid4();conn.commit()
  with tools.connect()as holder,holder.cursor()as held:
   held.execute("select pg_advisory_xact_lock(hashtextextended('CP7:LOCAL_BINDING:'||%s,0))",(str(subject),))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=command(cur,'PREVIEW',p,request,subject);conn.commit();return r
     except psycopg.Error as ex:conn.rollback();return str(ex)
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send)
    try:
     wait_for(tools,'erp_cp7_claim_local_preview_v1')
     with tools.connect()as conn,conn.cursor()as cur:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='master.product.manage'",(role,));conn.commit()
    finally:holder.rollback()
    r=job.result(90)
  assert isinstance(r,str)and'CP7_REMINDER_ACCESS_CHANGED'in r,r
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_reminder_native.requests where actor=%s and request_id=%s',(subject,request)).fetchone()[0]==0
  return dict(status='PASS',manage_revoked_during_observed_actual_binding_wait_refuses_claim_and_receipt=True)
 def revoke_domain():
  with tools.connect()as conn,conn.cursor()as cur:parent.setup(cur,today);subject,role=managed_actor(cur);f,e,key=due_fixture(cur,today,subject=subject,setup=False);p=binding_payload(e);request=uuid.uuid4();conn.commit()
  with tools.connect()as holder,holder.cursor()as held:
   held.execute("select pg_advisory_xact_lock(hashtextextended('CP7:LOCAL_BINDING:'||%s,0))",(str(subject),))
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=command(cur,'BINDING',p,request,subject);conn.commit();return r
     except psycopg.Error as ex:conn.rollback();return (ex.sqlstate,str(ex))
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send)
    try:
     wait_for(tools,'erp_cp7_save_local_binding_v1')
     with tools.connect()as conn,conn.cursor()as cur:cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ar.view'",(role,));conn.commit()
    finally:holder.rollback()
    r=job.result(90)
  assert isinstance(r,tuple)and r[0]=='42501'and(r[1].split('\n',1)[0]in('CP7_OBLIGATION_ACCESS_DENIED','CP7_REMINDER_ACCESS_CHANGED')),r
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_reminder_native.local_bindings where actor=%s',(subject,)).fetchone()[0]==0 and cur.execute('select count(*)from cp7_reminder_native.requests where actor=%s and request_id=%s',(subject,request)).fetchone()[0]==0
  return dict(status='PASS',current_AR_permission_loss_during_observed_binding_wait_no_binding_or_receipt=True)
 def callback_heal():
  with tools.connect()as conn,conn.cursor()as cur:f,e,key=prepared(cur,today);c=claim_row(claim(cur,e,key));conn.commit()
  with tools.connect()as holder,holder.cursor()as held:
   held.execute("select pg_advisory_xact_lock(hashtextextended('CP7:RULE_EPISODES:CURRENT_SOURCE',0))")
   def send():
    with tools.connect()as conn,conn.cursor()as cur:r=finish(cur,e,c);conn.commit();return r
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send)
    try:
     wait_for(tools,'erp_cp7_finish_local_preview_v1')
     with tools.connect()as conn,conn.cursor()as cur:ar.sales.payment(cur,dict(f,tag=f['tag']+'-wait'),today,'300');conn.commit()
    finally:holder.rollback()
    r=job.result(90)
  assert claim_row(r)['status']=='SUPPRESSED'and row(r['workspace']['source'],key)['business_resolved']
  return dict(status='PASS',Native_full_payment_during_observed_callback_episode_wait_suppresses_old_claim=True)
 def shared():
  with tools.connect()as conn,conn.cursor()as cur:f,e,key=due_fixture(cur,today);subject,_=managed_actor(cur);own=parent.capture(cur,today,subject=subject);conn.commit()
  gate=threading.Barrier(2)
  def send(original,subject):
   with tools.connect()as conn,conn.cursor()as cur:gate.wait(5);r=observe(cur,original,subject);conn.commit();return observation(r,key)['episode']
  with ThreadPoolExecutor(max_workers=2)as pool:results=[j.result(90)for j in[pool.submit(send,e,None),pool.submit(send,own,subject)]]
  assert results[0]['id']==results[1]['id']and results[0]['first_observed_at']==results[1]['first_observed_at']
  return dict(status='PASS',two_actual_authorized_actors_own_Originals_one_shared_business_episode_age=True)
 return previous.races(tools,today)+[('P16_RULE_RACE_'+n,f)for n,f in [('OCCURRENCE_DEDUP',duplicate),('CURRENT_MANAGE',revoke_manage),('CURRENT_DOMAIN',revoke_domain),('CALLBACK_NATIVE_HEAL',callback_heal),('SHARED_EPISODE',shared)]]

def http_cases(http,today):
 def capture(owner):
  r=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=parent.previous.baseline.history.query(today),p_request=str(uuid.uuid4())));assert r['status']==200,r;return r['body']
 def send(owner,op,p,request=None,lookup=False):
  name={'EPISODES':'erp_cp7_evaluate_rule_episodes_v1','BINDING':'erp_cp7_save_local_binding_v1','PREVIEW':'erp_cp7_claim_local_preview_v1','OUTCOME':'erp_cp7_finish_local_preview_v1','RESOLUTION':'erp_cp7_resolve_local_preview_v1'}[op]
  args=dict(p_payload=p,p_request=request or str(uuid.uuid4()))
  if lookup:name='erp_cp7_get_rule_episode_request_v1'if op=='EPISODES'else'erp_cp7_get_local_reminder_request_v1';args.update({}if op=='EPISODES'else dict(p_operation=op))
  r=owner.rpc(name,args);assert r['status']==200,r;return r['body']
 def configured(owner,e,key):
  current=owner.rpc('erp_cp7_get_reminder_policy_v1',dict(p_run=e['run_id']));assert current['status']==200,current
  revision=next((r['revision']for r in current['body']['rows']if r['rule_id']=='AR_DUE'and r['scope_kind']=='GLOBAL'),'0')
  p=previous.intent(e,'AR_DUE',revision,c=previous.ready(unit='DAY'));r=owner.rpc('erp_cp7_save_reminder_policy_v1',dict(p_payload=p,p_request=str(uuid.uuid4())));assert r['status']==200,r
  send(owner,'BINDING',binding_payload(e));w=owner.rpc('erp_cp7_get_local_reminders_v1',dict(p_run=e['run_id']));assert w['status']==200,w
  send(owner,'EPISODES',dict(run_id=e['run_id'],source_hash=w['body']['source']['source_hash']));return w['body']
 def actual():
  owner=http.login('OWNER','p16-rule-local-http')
  with http.connect()as conn,conn.cursor()as cur:f,_,key=due_fixture(cur,today);conn.commit()
  e=capture(owner);w=configured(owner,e,key);request=str(uuid.uuid4());p=claim_payload(e,w,key);one=send(owner,'PREVIEW',p,request);again=send(owner,'PREVIEW',p,request,True);assert again['result']==one['result'];c=claim_row(one);final=send(owner,'OUTCOME',outcome_payload(e,c))
  assert claim_row(final)['status']=='LOCAL_SINK_CAPTURED'and not final['workspace']['sent']and not row(final['workspace']['source'],key)['business_resolved']
  return dict(status='PASS',actual_Auth_PostgREST_source_episode_binding_UTF8_claim_recovery_local_capture=True,no_external_delivery_or_false_business_resolution=True)
 def authority():
  owner=http.login('OWNER','p16-rule-local-authority');other=http.login('OWNER','p16-rule-local-foreign')
  with http.connect()as conn,conn.cursor()as cur:f,_,key=due_fixture(cur,today);conn.commit()
  e=capture(owner);w=configured(owner,e,key);p=claim_payload(e,w,key);request=str(uuid.uuid4());one=send(owner,'PREVIEW',p,request)
  assert other.rpc('erp_cp7_get_rule_conditions_v1',dict(p_run=e['run_id']))['status']==403
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  for name,args in [('erp_cp7_get_rule_conditions_v1',dict(p_run=e['run_id'])),('erp_cp7_get_local_reminders_v1',dict(p_run=e['run_id'])),('erp_cp7_get_local_reminder_request_v1',dict(p_payload=p,p_request=request,p_operation='PREVIEW')),('erp_cp7_finish_local_preview_v1',dict(p_payload=outcome_payload(e,claim_row(one)),p_request=str(uuid.uuid4())))]:assert owner.rpc(name,args)['status']==403
  return dict(status='PASS',actual_foreign_Original_current_deactivation_read_cached_lookup_callback_refused=True)
 def unknown():
  owner=http.login('OWNER','p16-rule-local-unknown')
  with http.connect()as conn,conn.cursor()as cur:f,_,key=due_fixture(cur,today);conn.commit()
  e=capture(owner);w=configured(owner,e,key);p=claim_payload(e,w,key);c=claim_row(send(owner,'PREVIEW',p));held=send(owner,'OUTCOME',outcome_payload(e,c,'UNKNOWN'));assert claim_row(held)['status']=='UNKNOWN'
  resolved=send(owner,'RESOLUTION',resolution_payload(e,c));assert claim_row(resolved)['status']=='UNKNOWN';second=claim_row(send(owner,'PREVIEW',p));assert second['id']!=c['id']and second['fence']!=c['fence']
  return dict(status='PASS',actual_Auth_explicit_UNKNOWN_and_manual_non_capture_resolution_no_automatic_resend=True)
 def absence():
  owner=http.login('OWNER','p16-rule-local-absence')
  with http.connect()as conn,conn.cursor()as cur:f,_,key=due_fixture(cur,today);conn.commit()
  e=capture(owner);p=binding_payload(e);request=str(uuid.uuid4());sealed=send(owner,'BINDING',p,request,True);late=send(owner,'BINDING',p,request)
  assert sealed['result']==late['result']and sealed['result']['status']=='NOT_COMMITTED'and late['workspace']['binding']is None
  assert http.anon_rpc('erp_cp7_get_local_reminders_v1',dict(p_run=e['run_id']))['status']in(401,403)
  return dict(status='PASS',actual_Auth_absent_binding_sealed_before_delayed_write_anonymous_denied=True)
 return previous.http_cases(http,today)+[('P16_RULE_HTTP_'+n,f)for n,f in [('LOCAL_LIFECYCLE',actual),('CURRENT_AUTH',authority),('UNKNOWN_MANUAL_RESOLUTION',unknown),('SEALED_ABSENT',absence)]]
