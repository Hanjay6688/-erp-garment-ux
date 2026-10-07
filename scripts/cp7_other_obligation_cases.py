"""Fixed actual Native obligation transitions; retains every predecessor case.

No business-source mock, second amount formula, date substitute or weaker gate.
The 14 additional database, three real race, three Auth/HTTP and two browser
cases are declared before execution. Native setup writers are accepted controls.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
import json,time,uuid
import psycopg
import cp7_rule_source_cases as previous
import cp7_other_obligation_bundle as bundle
import cp7_installment_cases as installments
import cp7_opening_payroll_cases as opening
import cp6_bc_probe as bc
import cp6_bd_probe as bd

b,auth,parent=previous.b,previous.auth,previous.parent
FINER=('finance.payroll.view','warehouse.accessory.view','production.laundry.view','finance.hpp.view')
DATABASE_NAMES=('PRIVATE_READER_ACL','OPENING_CANONICAL','OPENING_ALLOCATION_PAYMENT_INVERSE',
 'PAYROLL_PARTIAL_FINAL_INVERSE','PAYROLL_EXACT_CENTS','PAYROLL_INACTIVE','UNKNOWN_DUE_EPISODE_AGE',
 'ACCESSORY_ALLOCATION_NOT_PAID','ACCESSORY_PAID_INVERSE','LAUNDRY_PENDING_UNKNOWN',
 'LAUNDRY_INVOICE_PAYMENT_INVERSE','LAUNDRY_OPENING_PENDING','CURRENT_NARROWER_RIGHTS','SOURCE_CONSERVATION')
RACE_NAMES=('PAYROLL_PERMISSION_WAIT','LAUNDRY_PAYMENT_SNAPSHOT','SHARED_UNKNOWN_EPISODE')
HTTP_NAMES=('PAYROLL_CURRENT_AUTH','EXACT_CURRENT_SOURCE','LOCAL_NATIVE_INVOICE')
BROWSER_NAMES=('DESKTOP','MOBILE')
EXPECTED=249+len(DATABASE_NAMES)+len(RACE_NAMES)+len(HTTP_NAMES)+len(BROWSER_NAMES)

def setup(cur,today):parent.setup(cur,today)
def capture(cur,today,subject=None):return parent.capture(cur,today,subject=subject)
def source(cur,e,subject=None):return previous.source(cur,e,subject)
def key(domain,id):return('AR_DUE'if domain=='OPENING_AR'else'AP_DUE')+':'+domain+':'+str(id)
def row(cur,e,domain,id,subject=None):return previous.row(source(cur,e,subject),key(domain,id))
def remaining(r):return r['financial_source']['remaining']
def amount(r,value):assert remaining(r)['state']=='KNOWN'and Decimal(remaining(r)['value'])==Decimal(value),r
def unknown(r):assert remaining(r)['state']=='UNKNOWN'and not r['business_resolved'],r
def episode(cur,e,domain,id,subject=None):return previous.observation(previous.observe(cur,e,subject),key(domain,id))
def actor(cur):
 subject,role=previous.managed_actor(cur)
 for p in FINER:cur.execute('insert into erp.app_role_permissions(role_id,permission_key)values(%s,%s)on conflict do nothing',(role,p))
 return subject,role
def revoke(cur,role,p):cur.execute('delete from erp.app_role_permissions where role_id=%s and permission_key=%s',(role,p))

def accessory_fixture(cur,today):
 day=today-timedelta(days=1);fx=bc.fixture(cur,day,days=8)
 _,item=bc.note(cur,fx,10,'3.00',day-timedelta(days=5))
 old=bc.payroll(cur,fx,day,'100.00',5);bc.pay_through(cur,old)
 lot=bc.receive(cur,fx,'NOTE_RETURN',day=day-timedelta(days=2),note_item_id=item,qty='4')['lot_ids'][0]
 bc.inspect(cur,lot,bc.local_at(day-timedelta(days=2),12),'P16 Native inspector',usable=4)
 bc.policy(cur,'ACC_DEC05',dict(mode='CREDIT_THEN_CARRY',credit_conditions=['USABLE']))
 credit=bc.credit(cur,lot,'USABLE',4,bc.local_at(day-timedelta(days=1),10),fx['main'])
 payroll=bc.payroll(cur,fx,day,'0.00',1)
 return dict(fx=fx,credit=credit,payroll=payroll,day=day)
def allocate_accessory(cur,f):
 bc.svc(cur,'ALLOCATE_CARRY',dict(event_id=f['credit']['event_id'],payroll_id=f['payroll'],amount='12.00',reason='Actual Native carry allocation is not cash payment'))
def pay_accessory(cur,f):
 for name in('approve_payroll','post_payroll_payment'):bc.internal(cur,name,f['payroll'])

def laundry_fixture(cur,today,invoice=False):
 day=today-timedelta(days=1);fx=bd.fixture(cur,day,'P16 Native obligation');bd.invoice_policies(cur)
 # Native posting requires one effective vendor/process rate. A known receipt
 # estimate still does not establish the final invoice payable.
 bd.process_rate(cur,fx,'1731.29')
 delivery=bd.plain_delivery(cur,fx,10,11)
 receipt=bd.receive(cur,delivery,fx,10,13)['receipt_id'];line=bd.receipt_line(cur,receipt)
 result=dict(fx=fx,day=day,delivery=delivery,receipt=receipt,line=line)
 if invoice:
  draft,posted=bd.invoice(cur,fx,[dict(line=line,qty=10,amount='17312.90')],'17312.90',due_date=str(day))
  result.update(draft=draft,invoice=draft['invoice_id'],posted=posted)
 return result
def laundry_opening_fixture(cur,today):
 rows=bd.bbp.masters();old=str(today-timedelta(days=12))
 rows['OPENING_LAUNDRY_UNINVOICED']=[dict(document_number='{C}-P16-KNOWN',vendor_code='{C}',receipt_date=old,category='GOOD',qty='10',estimated_amount='70000.00'),dict(document_number='{C}-P16-UNKNOWN',vendor_code='{C}',receipt_date=old,category='FAILED_ATTEMPT',qty='2')]
 batch,code,cutover=bd.bbp.post_batch(cur,today,rows);vendor=bd.one(cur,'select id::text from erp.laundry_vendors where vendor_code=%s',code)
 ids={r['category']:r['id']for r in bd.bd_ws(cur,dict(vendor_id=vendor))['opening_uninvoiced']}
 return dict(batch=batch,vendor=vendor,ids=ids,code=code)

def cases(cur,today,qualification_bundle=None):
 def acl():
  (qualification_bundle or bundle).verify(cur)
  for principal in('anon','authenticated','service_role'):
   assert not cur.execute("select pg_has_role(%s,'cp7_obligation_read','MEMBER')",(principal,)).fetchone()[0]
   assert not cur.execute("select has_function_privilege(%s,'cp7_reminder_native.other_obligation_source()','EXECUTE')",(principal,)).fetchone()[0]
  assert not cur.execute("select has_function_privilege('cp7_obligation_read','public.erp_cp7_save_payroll_installment_v1(text,jsonb,uuid,text)','EXECUTE')").fetchone()[0]
  return dict(status='PASS',exact20_Native_SELECT_tables_private_nonlogin_reader_no_Native_writer_or_direct_client=True)
 def opening_canonical():
  setup(cur,today);f=opening.fixture(cur,today);e=capture(cur,today);before=b.boundary.snapshot(cur);s=source(cur,e)
  for n,v in(('UPAH-OLD','65.00'),('REIMB-OLD','20.00')):amount(previous.row(s,key('OPENING_AP',f['balances'][n])),v)
  assert all(r['source_id']!=f['balances']['KASBON-OLD']for r in s['rows'])
  assert len([r for r in s['rows']if r['source_id']==f['balances']['UPAH-OLD']])==1
  r=previous.row(s,key('OPENING_AP',f['balances']['UPAH-OLD']));assert r['financial_source']['recorded_due_date']is None and r['value']['state']=='UNKNOWN'
  assert r['financial_source']['revision_basis']=='NATIVE_DOCUMENT_CONTENT_SHA256'and r['value']['refs'][0]['revision']==r['financial_source']['document_sha256']
  assert b.boundary.snapshot(cur)==before and s['analysis']['analysis']==e['analysis']
  return dict(status='PASS',actual_Native_opening65_and20_one_canonical_identity_cash_advance_excluded=True,no_fake_due_version_or_money_recalculation=True)
 def opening_cycle():
  setup(cur,today);f=opening.fixture(cur,today);e=capture(cur,today);pid=f['payroll'];opening.all_sources(cur,f)
  for n,v in(('UPAH-OLD','65'),('REIMB-OLD','20')):amount(row(cur,e,'OPENING_AP',f['balances'][n]),v)
  opening.s.act(cur,'PREPARE',opening.s.doc(cur,pid));opening.s.act(cur,'APPROVE',opening.s.doc(cur,pid))
  amount(row(cur,e,'OPENING_AP',f['balances']['UPAH-OLD']),'65')
  opening.s.act(cur,'PAY',opening.s.doc(cur,pid),payment_date=str(today),cash_account_id=f['cash'])
  for n in('UPAH-OLD','REIMB-OLD'):
   r=row(cur,e,'OPENING_AP',f['balances'][n]);amount(r,'0');assert r['business_resolved']
  opening.s.act(cur,'REVERSE',opening.s.doc(cur,pid));amount(row(cur,e,'OPENING_AP',f['balances']['UPAH-OLD']),'65')
  return dict(status='PASS',actual_BB_allocation_and_approval_not_payment_Native_paid65_20_inverse_restores65=True)
 def payroll_cycle():
  setup(cur,today);f=installments.fixture(cur,today);e=capture(cur,today);amount(row(cur,e,'PAYROLL_AP',f['payroll']),'1000')
  first=installments.act(cur,f);amount(row(cur,e,'PAYROLL_AP',f['payroll']),'400');installments.act(cur,f,amount='400.00')
  r=row(cur,e,'PAYROLL_AP',f['payroll']);amount(r,'0');assert r['business_resolved']
  installments.act(cur,f,'REVERSE_PAYMENT',payment=first['payment_id']);r=row(cur,e,'PAYROLL_AP',f['payroll']);amount(r,'600');assert r['economic_state']=='OPEN'and not r['business_resolved']
  return dict(status='PASS',actual_E05_1000_600_400_final400_inverse600_copied_from_Native_only=True)
 def exact_cents():
  setup(cur,today);f=installments.fixture(cur,today,attendance=False,manual='9007199254740993.01');e=capture(cur,today)
  assert remaining(row(cur,e,'PAYROLL_AP',f['payroll']))['value']=='9007199254740993.01'
  installments.act(cur,f,amount='9007199254740993.00');assert remaining(row(cur,e,'PAYROLL_AP',f['payroll']))['value']=='0.01'
  installments.act(cur,f,amount='0.01');r=row(cur,e,'PAYROLL_AP',f['payroll']);amount(r,'0');assert r['business_resolved']
  return dict(status='PASS',actual_Native_large_integer_plus_cent_remaining_one_cent_then_settled_no_JS_Number=True)
 def inactive():
  setup(cur,today);f=installments.fixture(cur,today);e=capture(cur,today);installments.act(cur,f);installments.act(cur,f,'REVERSE_PAYROLL');r=row(cur,e,'PAYROLL_AP',f['payroll'])
  assert r['economic_state']=='INACTIVE'and r['state']=='NO_CURRENT_GAP';unknown(r)
  pid=str(cur.execute('insert into erp.payroll_settlements(payroll_number,contractor_id,period_start,period_end)values(%s,%s,%s,%s)returning id',('P16DRAFT-'+uuid.uuid4().hex,f['contractor'],today,today)).fetchone()[0])
  r=row(cur,e,'PAYROLL_AP',pid);assert r['reason']=='DRAFT_ONLY'and r['economic_state']=='INACTIVE';unknown(r)
  return dict(status='PASS',actual_draft_and_Native_reversed_headers_retained_not_zero_balance_or_implicit_heal=True)
 def age():
  setup(cur,today);f=installments.fixture(cur,today);e=capture(cur,today);one=episode(cur,e,'PAYROLL_AP',f['payroll'])['episode']
  assert one['freshness']=='UNKNOWN'and one['state']=='ACTIVE'
  first=installments.act(cur,f);two=episode(cur,e,'PAYROLL_AP',f['payroll'])['episode'];assert two['id']==one['id']and two['first_observed_at']==one['first_observed_at']
  installments.act(cur,f,amount='400.00');closed=episode(cur,e,'PAYROLL_AP',f['payroll'])['episode'];assert closed['id']==one['id']and closed['state']=='RESOLVED'
  installments.act(cur,f,'REVERSE_PAYMENT',payment=first['payment_id']);again=episode(cur,e,'PAYROLL_AP',f['payroll'])['episode'];assert again['id']!=one['id']and again['previous_id']==one['id']and again['number']=='2'
  return dict(status='PASS',actual_open_missing_due_unknown_age_survives_partial_cash_settles_only_Native_zero_inverse_links_new_episode=True)
 def accessory_allocation():
  setup(cur,today);f=accessory_fixture(cur,today);e=capture(cur,today);id=f['credit']['event_id'];amount(row(cur,e,'ACCESSORY_AP',id),'12');one=episode(cur,e,'ACCESSORY_AP',id)['episode']
  allocate_accessory(cur,f);assert bc.one(cur,'select erp.bc_carry_remaining_v1(%s)',id)==0
  r=row(cur,e,'ACCESSORY_AP',id);unknown(r);assert r['reason']=='ALLOCATION_NOT_SETTLEMENT'
  two=episode(cur,e,'ACCESSORY_AP',id)['episode'];assert two['id']==one['id']and two['freshness']=='UNKNOWN'and two['first_observed_at']==one['first_observed_at']
  return dict(status='PASS',actual_BC_credit12_then_full_unpaid_allocation_Native_allocatable0_not_settled0_no_age_reset=True)
 def accessory_inverse():
  setup(cur,today);f=accessory_fixture(cur,today);e=capture(cur,today);allocate_accessory(cur,f);pay_accessory(cur,f)
  r=row(cur,e,'ACCESSORY_AP',f['credit']['event_id']);amount(r,'0');assert r['business_resolved']
  bc.internal(cur,'reverse_paid_payroll',f['payroll'],'Actual Native carry payment inverse')
  r=row(cur,e,'ACCESSORY_AP',f['credit']['event_id']);amount(r,'12');assert not r['business_resolved']
  return dict(status='PASS',actual_Native_all_allocations_PAID_proves_zero_inverse_reopens12_without_attributing_partial_installments=True)
 def laundry_unknown():
  setup(cur,today);f=laundry_fixture(cur,today);e=capture(cur,today);r=row(cur,e,'LAUNDRY_RECEIPT',f['line']);unknown(r)
  assert r['reason']=='VALUE_PENDING'and r['financial_source']['recorded_due_date']is None
  assert r['financial_source']['document']['receipt']['actual_cost_status']=='ESTIMATED'
  assert r['financial_source']['document']['native_billable']['receipt_line_id']==f['line']
  first=episode(cur,e,'LAUNDRY_RECEIPT',f['line'])['episode'];assert first['freshness']=='UNKNOWN'and first['state']=='ACTIVE'
  return dict(status='PASS',actual_lawfully_priced_receipt_estimate_not_final_invoice_AP_or_zero_unknown_review_age_created=True)
 def laundry_cycle():
  setup(cur,today);f=laundry_fixture(cur,today,invoice=True);e=capture(cur,today);r=row(cur,e,'LAUNDRY_AP',f['invoice']);amount(r,'17312.90');assert r['state']=='ACTIVE'and r['value']['value']=='1'
  unknown(row(cur,e,'LAUNDRY_RECEIPT',f['line']));first=bd.pay(cur,f['invoice'],'7312.90',f['day']);amount(row(cur,e,'LAUNDRY_AP',f['invoice']),'10000')
  bd.pay(cur,f['invoice'],'10000.00',f['day']);r=row(cur,e,'LAUNDRY_AP',f['invoice']);amount(r,'0');assert r['business_resolved']
  r=row(cur,e,'LAUNDRY_RECEIPT',f['line']);amount(r,'0');assert r['business_resolved']
  bd.internal(cur,'reverse_vendor_payment',first,'Actual Native laundry payment inverse');amount(row(cur,e,'LAUNDRY_AP',f['invoice']),'7312.90');unknown(row(cur,e,'LAUNDRY_RECEIPT',f['line']))
  return dict(status='PASS',actual_Native_invoice17312_90_partial_final_inverse_and_receipt_proof_no_double_final_amount=True)
 def laundry_opening():
  setup(cur,today);f=laundry_opening_fixture(cur,today);e=capture(cur,today)
  for id in f['ids'].values():unknown(row(cur,e,'LAUNDRY_OPENING_UNINVOICED',id))
  s=source(cur,e);assert all(len([r for r in s['rows']if r['source_id']==id])==1 for id in f['ids'].values())
  bd.invoice_policies(cur);draft=bd.opening_invoice(cur,f['vendor'],today-timedelta(days=1),[dict(source=f['ids']['GOOD'],qty=10,amount='70000.00')],'70000.00')
  unknown(row(cur,e,'LAUNDRY_OPENING_UNINVOICED',f['ids']['GOOD']))
  amount(row(cur,e,'LAUNDRY_AP',draft['invoice_id']),'70000')
  return dict(status='PASS',actual_known_estimate_and_missing_price_opening_receipts_complete_unique_not_AP_money_until_Native_invoice=True)
 def narrower():
  setup(cur,today);f=installments.fixture(cur,today);subject,role=actor(cur);e=capture(cur,today,subject);s=source(cur,e,subject);p=dict(run_id=e['run_id'],source_hash=s['source_hash']);request=uuid.uuid4();saved=previous.command(cur,'EPISODES',p,request,subject)
  assert any(r['condition']['domain']=='PAYROLL_AP'for r in saved['result']['rows'])
  revoke(cur,role,'finance.payroll.view');current=source(cur,e,subject);assert current['coverage']['payroll_ap']=='EXCLUDED_BY_CURRENT_RIGHTS'and all(r['domain']!='PAYROLL_AP'for r in current['rows'])
  auth.refused(cur,lambda:previous.command(cur,'EPISODES',p,request,subject,True),'CP7_RULE_EPISODE_DOMAIN_DENIED')
  assert current['coverage']['material_ap']=='COMPLETE_NATIVE_DOCUMENT_SCOPE'
  return dict(status='PASS',actual_payroll_right_only_revoked_AP_and_Ops_retained_cached_old_observation_denied=True)
 def conservation():
  setup(cur,today);f=installments.fixture(cur,today);e=capture(cur,today);before=b.boundary.snapshot(cur);one=source(cur,e);two=source(cur,e)
  assert one['source_hash']==two['source_hash']and one['analysis']['analysis']==two['analysis']['analysis']==e['analysis']and b.boundary.snapshot(cur)==before
  for r in one['rows']:
   if r['financial_source']is not None:
    assert r['financial_source']['remaining']['state']in('KNOWN','UNKNOWN')
    def walk(x):
     assert not isinstance(x,(int,float))or isinstance(x,bool)
     if isinstance(x,dict):
      for v in x.values():walk(v)
     elif isinstance(x,list):
      for v in x:walk(v)
    walk(r['financial_source']['document'])
  return dict(status='PASS',same_current_Native_documents_one_stable_complete_source_exact_text_numbers_frozen_Original_and_ERP_unchanged=True)
 functions=(acl,opening_canonical,opening_cycle,payroll_cycle,exact_cents,inactive,age,accessory_allocation,accessory_inverse,laundry_unknown,laundry_cycle,laundry_opening,narrower,conservation)
 assert len(functions)==len(DATABASE_NAMES)==14
 return previous.cases(cur,today)+[('P16_OTHER_NATIVE_'+n,f)for n,f in zip(DATABASE_NAMES,functions)]

def races(tools,today):
 def permission_wait():
  with tools.connect()as conn,conn.cursor()as cur:setup(cur,today);f=installments.fixture(cur,today);subject,role=actor(cur);e=capture(cur,today,subject);s=source(cur,e,subject);p=dict(run_id=e['run_id'],source_hash=s['source_hash']);request=uuid.uuid4();conn.commit()
  with tools.connect()as holder,holder.cursor()as held:
   held.execute("select pg_advisory_xact_lock(hashtextextended('CP7:RULE_EPISODES:CURRENT_SOURCE',0))")
   def send():
    with tools.connect()as conn,conn.cursor()as cur:
     try:r=previous.command(cur,'EPISODES',p,request,subject);conn.commit();return r
     except psycopg.Error as ex:conn.rollback();return(ex.sqlstate,str(ex).split('\n',1)[0])
   with ThreadPoolExecutor(max_workers=1)as pool:
    job=pool.submit(send)
    try:
     previous.wait_for(tools,'erp_cp7_evaluate_rule_episodes_v1')
     with tools.connect()as conn,conn.cursor()as cur:revoke(cur,role,'finance.payroll.view');conn.commit()
    finally:holder.rollback()
    result=job.result(90)
  assert result==('42501','CP7_REMINDER_ACCESS_CHANGED'),result
  with tools.connect()as conn,conn.cursor()as cur:assert cur.execute('select count(*)from cp7_reminder_native.requests where actor=%s and request_id=%s',(subject,request)).fetchone()[0]==0
  return dict(status='PASS',actual_witnessed_episode_lock_payroll_only_revoke_no_cached_body_episode_or_receipt=True)
 def payment_snapshot():
  with tools.connect()as conn,conn.cursor()as cur:setup(cur,today);f=laundry_fixture(cur,today,invoice=True);e=capture(cur,today);conn.commit()
  with tools.connect()as conn,conn.cursor()as cur:
   pid=bd.pay(cur,f['invoice'],'7312.90',f['day'])
   with tools.connect()as reader,reader.cursor()as read:before=row(read,e,'LAUNDRY_AP',f['invoice']);amount(before,'17312.90')
   conn.commit()
  with tools.connect()as conn,conn.cursor()as cur:after=row(cur,e,'LAUNDRY_AP',f['invoice']);amount(after,'10000')
  assert before['financial_source']['document_sha256']!=after['financial_source']['document_sha256']
  return dict(status='PASS',actual_uncommitted_Native_payment_invisible_then_committed_exact_new_remaining_one_snapshot_no_mixed_ledger=True)
 def shared_unknown():
  with tools.connect()as conn,conn.cursor()as cur:setup(cur,today);f=installments.fixture(cur,today);e=capture(cur,today);subject,_=actor(cur);own=capture(cur,today,subject);conn.commit()
  def send(original,who):
   with tools.connect()as conn,conn.cursor()as cur:r=episode(cur,original,'PAYROLL_AP',f['payroll'],who)['episode'];conn.commit();return r
  with ThreadPoolExecutor(max_workers=2)as pool:rows=[j.result(90)for j in[pool.submit(send,e,None),pool.submit(send,own,subject)]]
  assert rows[0]['id']==rows[1]['id']and rows[0]['first_observed_at']==rows[1]['first_observed_at']and rows[0]['freshness']==rows[1]['freshness']=='UNKNOWN'
  return dict(status='PASS',actual_two_actors_concurrent_Native_known_debt_missing_due_one_shared_unknown_episode_no_duplicate_age=True)
 return previous.races(tools,today)+[('P16_OTHER_RACE_'+n,f)for n,f in zip(RACE_NAMES,(permission_wait,payment_snapshot,shared_unknown))]

def http_cases(http,today):
 def read(owner,e):
  r=owner.rpc('erp_cp7_get_rule_conditions_v1',dict(p_run=e['run_id']));assert r['status']==200,r;return r['body']
 def capture_http(owner):
  r=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=parent.previous.baseline.history.query(today),p_request=str(uuid.uuid4())));assert r['status']==200,r;return r['body']
 def payroll_auth():
  owner=http.login('OWNER','p16-other-payroll-http');other=http.login('OWNER','p16-other-payroll-foreign')
  with http.connect()as conn,conn.cursor()as cur:setup(cur,today);f=installments.fixture(cur,today);conn.commit()
  e=capture_http(owner);s=read(owner,e);amount(previous.row(s,key('PAYROLL_AP',f['payroll'])),'1000')
  assert other.rpc('erp_cp7_get_rule_conditions_v1',dict(p_run=e['run_id']))['status']==403
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_get_rule_conditions_v1',dict(p_run=e['run_id']))['status']==403
  return dict(status='PASS',actual_Auth_Native_payroll_source_foreign_actor_and_current_deactivation403_no_old_source=True)
 def exact_http():
  owner=http.login('OWNER','p16-other-exact-http')
  with http.connect()as conn,conn.cursor()as cur:setup(cur,today);f=installments.fixture(cur,today,attendance=False,manual='9007199254740993.01');conn.commit()
  e=capture_http(owner);one=read(owner,e);r=previous.row(one,key('PAYROLL_AP',f['payroll']));assert remaining(r)['value']=='9007199254740993.01'and r['value']['state']=='UNKNOWN'and not r['business_resolved']
  assert one['page_complete']and len(one['rows'])==int(one['total'])and one['source_hash']==read(owner,e)['source_hash']and one['analysis']['analysis']==e['analysis']
  return dict(status='PASS',actual_Auth_PostgREST_exact_large_cent_text_no_false_due_complete_current_source_same_frozen_Original=True)
 def local_invoice():
  owner=http.login('OWNER','p16-other-invoice-http')
  with http.connect()as conn,conn.cursor()as cur:setup(cur,today);f=laundry_fixture(cur,today,invoice=True);conn.commit()
  e=capture_http(owner);s=read(owner,e);current=owner.rpc('erp_cp7_get_reminder_policy_v1',dict(p_run=e['run_id']));assert current['status']==200,current
  rev=next((r['revision']for r in current['body']['rows']if r['rule_id']=='AP_DUE'and r['scope_kind']=='GLOBAL'),'0')
  p=previous.previous.intent(e,'AP_DUE',rev,c=previous.previous.ready(unit='DAY'))
  r=owner.rpc('erp_cp7_save_reminder_policy_v1',dict(p_payload=p,p_request=str(uuid.uuid4())));assert r['status']==200,r
  binding=owner.rpc('erp_cp7_save_local_binding_v1',dict(p_payload=previous.binding_payload(e,rules=['AP_DUE']),p_request=str(uuid.uuid4())));assert binding['status']==200,binding
  s=read(owner,e);r=owner.rpc('erp_cp7_evaluate_rule_episodes_v1',dict(p_payload=dict(run_id=e['run_id'],source_hash=s['source_hash']),p_request=str(uuid.uuid4())));assert r['status']==200,r
  p=dict(run_id=e['run_id'],condition_key=key('LAUNDRY_AP',f['invoice']),source_hash=s['source_hash'],binding_id=binding['body']['workspace']['binding']['id'])
  started=time.monotonic();r=owner.rpc('erp_cp7_claim_local_preview_v1',dict(p_payload=p,p_request=str(uuid.uuid4())));elapsed_ms=round((time.monotonic()-started)*1000);assert r['status']==200,r;c=previous.claim_row(r['body'])
  assert 'Sisa tagihan: 17312.90 IDR'in c['body']and'Sisa tagihan: 0'not in c['body']
  assert 'Jatuh tempo tercatat: '+str(f['day'])in c['body']and not r['body']['workspace']['sent']
  return dict(status='PASS',actual_Auth_current_Native_invoice_local_UTF8_body_copies_remaining_due_no_provider_or_SENT=True,actual_PostgREST_claim_elapsed_ms=elapsed_ms,Native_statement_timeout_unchanged=True)
 return previous.http_cases(http,today)+[('P16_OTHER_HTTP_'+n,f)for n,f in zip(HTTP_NAMES,(payroll_auth,exact_http,local_invoice))]
