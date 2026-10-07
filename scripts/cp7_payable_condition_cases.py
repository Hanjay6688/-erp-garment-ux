"""Actual accepted supplier AP/GRNI/credit/payment conditions; no new ledger."""
import json,uuid
from decimal import Decimal
from datetime import timedelta
import cp7_receivable_condition_cases as ar
import cp7_invoice_cases as invoice
import cp7_supplier_return_cases as returned
parent,auth,b=ar.parent,ar.auth,ar.b
bc=invoice.receipt.bc
def get(cur,run,subject=None):return ar.attention.rpc(cur,'erp_cp7_get_analysis_payable_conditions_v1',(run,),subject)
def row(e,purchase):return next(x for x in e['source']['rows']if x['liability']['purchase_id']==purchase)
def checked(e,original):
 assert e['contract_version']=='cp7.native-material-ap-conditions.v1'and e['analysis']['analysis']==original['analysis']and e['analysis']['financial_source']==original['financial_source']
 s=e['source'];assert s['contract_version']=='cp7.native-material-ap-source.v2'and s['page_complete']and len(s['rows'])==int(s['total'])and len({r['liability']['purchase_id']for r in s['rows']})==int(s['total'])
 return e
def native_balance(cur,f):
 auth.actor(cur);e=cur.execute('select public.erp_get_supplier_credit_v1(%s::jsonb)',(json.dumps(dict(supplier_id=f['payload']['supplier_id'],page=1)),)).fetchone()[0];b.api.admin(cur)
 return next(x for x in e['purchases']if x['id']==f['receipt']['purchase_id'])
def payment(cur,f,today,amount):
 bank=bc.bank_account(cur,'P16AP'+uuid.uuid4().hex[:10]);p=bc.supplier_payment(cur,f['receipt']['purchase_id'],amount,bank,today);bc.internal(cur,'post_supplier_payment',p);b.api.admin(cur);return p
def inverse(cur,p):bc.internal(cur,'reverse_supplier_payment',p,'P16 actual Native supplier payment inverse');b.api.admin(cur)
def prepared(cur,today):
 parent.setup(cur,today);f=invoice.fixture(cur,today,qty='20',price='25');return f,parent.capture(cur,today)
def finalize(cur,f,today):
 p=invoice.payload(f,'20','25');p['due_date']=(today-timedelta(days=1)).isoformat();return invoice.finalize(cur,f,'20','25',p=p)
def cases(cur,today):
 def lifecycle():
  f,original=prepared(cur,today);ident=f['receipt']['purchase_id'];before=b.boundary.snapshot(cur);e=checked(get(cur,original['run_id']),original);r=row(e,ident)
  assert r['balance']['remaining']=='0.00'and Decimal(r['liability']['grni_estimated_amount'])==Decimal('500')and r['condition']['state']=='INVOICE_PENDING'and not r['condition']['business_resolved']
  assert b.boundary.snapshot(cur)==before
  finalize(cur,f,today);payment(cur,f,today,'200');before=b.boundary.snapshot(cur);r=row(checked(get(cur,original['run_id']),original),ident)
  assert r['balance']==native_balance(cur,f)and r['balance']['remaining']=='300.00'and r['condition']['state']=='OVERDUE'and not r['condition']['invoice_pending']and not r['condition']['business_resolved'];assert b.boundary.snapshot(cur)==before
  final=payment(cur,f,today,'300');r=row(checked(get(cur,original['run_id']),original),ident);assert r['condition']['state']=='ZERO_BALANCE'and r['condition']['business_resolved']
  inverse(cur,final);r=row(checked(get(cur,original['run_id']),original),ident);assert r['balance']['remaining']=='300.00'and not r['condition']['business_resolved']
  return dict(status='PASS',actual_Native_estimated_GRNI500_final_balance0_still_pending=True,actual_final_invoice500_paid200_remaining300_overdue=True,unchanged_BF_signed_purchase_balance_copied_without_second_AP_engine=True,Native_final300_settlement_and_inverse_reopens300=True,original_finance_immutable_and_source_read_only=True)
 def credit():
  parent.setup(cur,today);f=invoice.fixture(cur,today,qty='10',price='10',final=True);paid=payment(cur,f,today,'100');original=parent.capture(cur,today)
  d,p=returned.save(cur,f,'4');before=b.boundary.snapshot(cur)
  auth.refused(cur,lambda:returned.post(cur,f,d),'Reverse/correct supplier payment first')
  assert b.boundary.snapshot(cur)==before
  r=row(checked(get(cur,original['run_id']),original),f['receipt']['purchase_id']);assert r['balance']==native_balance(cur,f)and r['balance']['remaining']=='0.00'
  # Respect the unchanged Native overpayment guard: reverse the real payment
  # before posting this return. Do not manufacture a negative paid-AP source.
  inverse(cur,paid);returned.post(cur,f,d);before=b.boundary.snapshot(cur);r=row(checked(get(cur,original['run_id']),original),f['receipt']['purchase_id'])
  assert r['balance']==native_balance(cur,f)and r['balance']['final_ap']=='60.00'and r['balance']['paid']=='0.00'and r['balance']['remaining']=='60.00'and not r['condition']['business_resolved']
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual_paid100_return_projected60_refused_by_unchanged_Native_guard=True,actual_payment_inverse_then_return_final60_remaining60=True,signed_negative_receiver_is_standin_only_not_claimed_as_lawful_Native_return=True,no_invented_refund_carry_policy_or_business_closure=True)
 def authority():
  original,e,subject=ar.attention.prepared(cur,today,True);role=cur.execute('select role_id from erp.app_users where auth_user_id=%s',(subject,)).fetchone()[0]
  cur.execute("insert into erp.app_role_permissions(role_id,permission_key)values(%s,'finance.ap.view')on conflict do nothing",(role,));assert checked(get(cur,original['run_id'],subject),original)['actor_scope_id']==subject
  auth.refused(cur,lambda:get(cur,original['run_id']),'CP7_ANALYSIS_RUN_UNAVAILABLE');cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='finance.ap.view'",(role,))
  auth.refused(cur,lambda:get(cur,original['run_id'],subject),'CP7_REMINDER_AP_ACCESS_DENIED');assert parent.read(cur,original['run_id'],subject)['analysis']==original['analysis']
  return dict(status='PASS',actual_active_disposable_STAFF_current_actor_and_AP_before_source=True,AP_only_loss_keeps_original_Ops_but_refuses_money=True)
 def complete():
  parent.setup(cur,today);ids={invoice.fixture(cur,today,qty='1',price='25')['receipt']['purchase_id']for _ in range(26)};original=parent.capture(cur,today);before=b.boundary.snapshot(cur);e=checked(get(cur,original['run_id']),original)
  assert ids<={r['liability']['purchase_id']for r in e['source']['rows']}and all(row(e,id)['condition']['state']=='INVOICE_PENDING'and not row(e,id)['condition']['business_resolved']for id in ids)
  assert b.boundary.snapshot(cur)==before
  return dict(status='PASS',actual26_posted_receipts_complete_current_balances_beyond25_display_rows=True,pending_uninvoiced_receipts_not_healthy_zero=True,read_only_current_statement_source=True)
 def oldest_due_rule():
  # AP-5 (owner decision 7 Oct 2026): Native records supplier payments against
  # the receipt only. The reminder applies them to the receipt's invoices oldest
  # due first, labels the result as a rule and changes no payment or journal.
  parent.setup(cur,today);f=invoice.fixture(cur,today,qty='20',price='25');original=parent.capture(cur,today);ident=f['receipt']['purchase_id']
  old=invoice.payload(f,'10','25');old['due_date']=(today-timedelta(days=3)).isoformat();invoice.finalize(cur,f,'10','25',p=old)
  new=invoice.payload(f,'10','25');new['due_date']=(today+timedelta(days=5)).isoformat();invoice.finalize(cur,f,'10','25',p=new)
  payment(cur,f,today,'249.99');r=row(checked(get(cur,original['run_id']),original),ident);u=r['due_rule']
  assert r['balance']==native_balance(cur,f)and r['balance']['remaining']=='250.01'
  assert(u['rule'],u['evidence'],u['recorded_invoice_allocation'])==('OLDEST_DUE_FIRST_WITHIN_RECEIPT','RULE_RESULT_NOT_PER_INVOICE_PAYMENT_EVIDENCE','NONE_IN_NATIVE_PAYMENTS_ARE_RECEIPT_BOUND')
  assert[(p['kind'],p['due_date'],Decimal(p['amount']))for p in u['portions']]==[('POSTED_INVOICE',old['due_date'],Decimal('250')),('POSTED_INVOICE',new['due_date'],Decimal('250'))],u
  assert(u['payments_applied'],u['outcome'],u['open_portion'],u['recorded_due_date'])==('249.99','OPEN_PORTION',0,old['due_date'])
  assert(r['due_date'],r['due_basis'],r['condition']['state'])==(old['due_date'],'RULE_OLDEST_DUE_FIRST_WITHIN_RECEIPT','OVERDUE')
  # One more cent settles the older invoice under the rule: the newer one is not yet due.
  cent=payment(cur,f,today,'0.01');books=cur.execute('select(select count(*)from erp.journal_entries),(select count(*)from erp.journal_lines),(select count(*)from erp.supplier_payments where purchase_id=%s)',(ident,)).fetchone()
  before=b.boundary.snapshot(cur);r=row(checked(get(cur,original['run_id']),original),ident);u=r['due_rule']
  assert(u['payments_applied'],u['outcome'],u['open_portion'],u['recorded_due_date'])==('250.00','OPEN_PORTION',1,old['due_date'])
  assert(r['due_date'],r['due_basis'],r['condition']['state'],r['balance']['remaining'])==(new['due_date'],'RULE_OLDEST_DUE_FIRST_WITHIN_RECEIPT','NOT_DUE_YET','250.00')
  assert b.boundary.snapshot(cur)==before and cur.execute('select(select count(*)from erp.journal_entries),(select count(*)from erp.journal_lines),(select count(*)from erp.supplier_payments where purchase_id=%s)',(ident,)).fetchone()==books
  # Reversing the cent reopens the older invoice under the same rule.
  inverse(cur,cent);r=row(checked(get(cur,original['run_id']),original),ident)
  assert(r['due_date'],r['condition']['state'],r['due_rule']['open_portion'])==(old['due_date'],'OVERDUE',0)
  return dict(status='PASS',payments_receipt_bound_no_recorded_invoice_allocation=True,oldest_due_first_within_receipt=True,
   cent_boundary_exact=True,rule_result_labelled_not_per_invoice_evidence=True,recorded_earliest_due_kept_alongside=True,
   no_payment_journal_or_business_change=True,payment_inverse_reopens_older_due=True)
 return ar.cases(cur,today)+[('P16_NATIVE_AP_CONDITION_'+n,f)for n,f in [('GRNI_FINAL_PAYMENT_INVERSE',lifecycle),('SIGNED_RETURN_CREDIT',credit),('CURRENT_ACTOR_AP_AUTH',authority),('COMPLETE_SOURCE26',complete),('AP5_OLDEST_DUE_FIRST',oldest_due_rule)]]
def races(tools,today):return ar.races(tools,today)
def http_cases(http,today):
 def actual():
  owner=http.login('OWNER','p16-current-ap-source');other=http.login('OWNER','p16-current-ap-other')
  with http.connect()as conn,conn.cursor()as cur:f,_=prepared(cur,today);finalize(cur,f,today);payment(cur,f,today,'200');conn.commit()
  original=owner.rpc('erp_cp7_capture_analysis_v1',dict(p_query=parent.previous.baseline.history.query(today),p_request=str(uuid.uuid4())));assert original['status']==200,original
  args=dict(p_run=original['body']['run_id']);e=owner.rpc('erp_cp7_get_analysis_payable_conditions_v1',args);assert e['status']==200,e;checked(e['body'],original['body']);assert row(e['body'],f['receipt']['purchase_id'])['balance']['remaining']=='300.00'
  assert other.rpc('erp_cp7_get_analysis_payable_conditions_v1',args)['status']==403 and http.anon_rpc('erp_cp7_get_analysis_payable_conditions_v1',args)['status']in(401,403)
  with http.connect()as conn,conn.cursor()as cur:cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
  assert owner.rpc('erp_cp7_get_analysis_payable_conditions_v1',args)['status']==403
  return dict(status='PASS',actual_Auth_PostgREST_Native_supplier_AP500_200_300=True,foreign_anonymous_deactivated_actor_refused=True)
 return ar.http_cases(http,today)+[('P16_AP_SOURCE_HTTP_CURRENT_AUTH',actual)]
