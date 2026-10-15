"""Own literal cash/correction contract over real Auth and PostgREST.
The control and spent-income scenarios use fresh source-bound public workspace
tokens. No fixture session timezone or mocked response reaches the HTTP caller.
"""
from decimal import Decimal as D
import uuid
import cp7_payment_correction_cases as edit
import cp7_supplier_payment_create_cases as pay
import cp7_cp17_fix_cases as cash

IDS=['SOL_HTTP_UNSPENT_INCOME_CORRECTION_CONTROL',
 'SOL_HTTP_SPENT_INCOME_CORRECTION_FINAL_POSITIVE',
 'SOL_HTTP_SPENT_INCOME_NOTE_ONLY_CORRECTION',
 'SOL_HTTP_SPENT_INCOME_GENUINE_NEGATIVE_REFUSAL']

def http_cases(http,today):
 def scenario(label,spent,replacement,note_only=False):
  owner=http.login('OWNER',label)
  with http.connect()as conn,conn.cursor()as cur:
   f=edit.fixture(cur,today,amount='30.01')
   if spent:
    out=pay.fixture(cur,today);out['cash']=f['bank']
    pay.command(cur,pay.payload(cur,out,'20.00'))
   before=cash.balance(cur,f['bank']);assert before==D('10.01'if spent else'30.01')
   facts=edit.payment_fact(cur,f['payment']);conn.commit()
  workspace=owner.rpc(edit.READ,dict(p_query=dict(sale_id=f['sale'],payment_id=f['payment'])))
  assert workspace['status']==200 and workspace['body']['eligible'],workspace
  w=workspace['body'];doc=w['document']
  p=dict(sale_id=f['sale'],payment_id=f['payment'],review_token=w['review_token'],change_reason='Sol independent correction cash audit',
   replacement=dict(payment_number=doc['number'],payment_date=doc['physical_at'],amount=replacement,cash_account_id=doc['cash_account_id'],
    payment_method=doc['method'],reference_number=doc['reference'],notes='Sol note corrected after receipt used'if note_only else doc['notes']))
  with http.connect()as conn,conn.cursor()as cur:boundary=pay.b.boundary.snapshot(cur);private=edit.private_state(cur);conn.rollback()
  result=owner.rpc(edit.RPC,dict(p_payload=p,p_request=str(uuid.uuid4()),p_expected=w['row_version']))
  expected=D(replacement)-D('20.00'if spent else'0')
  with http.connect()as conn,conn.cursor()as cur:
   after=cash.balance(cur,f['bank']);unchanged=pay.b.boundary.snapshot(cur)==boundary and edit.private_state(cur)==private
   original_immutable=edit.payment_fact(cur,f['payment'])==facts
   conn.rollback()
  error=result.get('body')or{}
  if expected<0:
   assert result['status']>=400 and 'CP7_CASH_NEGATIVE'in error.get('message','') and unchanged and after==before,result
   status='PASS'
  elif result['status']==200:
   assert after==expected and original_immutable,(after,expected,result)
   status='PASS'
  else:
   assert unchanged and after==before
   status='COUNTEREXAMPLE'if 'CP7_CASH_NEGATIVE'in error.get('message','')else'INCOMPLETE'
  return dict(status=status,evidence_origin='INDEPENDENT_NATIVE_RERUN',oracle_origin='SOL_LITERAL_ATOMIC_CORRECTION_AND_D14_3',
   fixture_origin='SYNTHETIC_REUSED_NATIVE_BUILDERS',session_role='OWNER',transport='REAL_AUTH_AND_POSTGREST',
   original_receipt='30.01',supplier_payment='20.00'if spent else'0',replacement_receipt=replacement,
   note_only=note_only,expected_final_bank=str(expected),bank_before=str(before),actual_bank=str(after),
   response=result,business_and_private_state_unchanged=unchanged,original_posted_facts_immutable=original_immutable,production_go=False)
 return [
  (IDS[0],lambda:scenario('sol-unspent-control',False,'25.01')),
  (IDS[1],lambda:scenario('sol-spent-positive',True,'25.01')),
  (IDS[2],lambda:scenario('sol-spent-notes',True,'30.01',True)),
  (IDS[3],lambda:scenario('sol-spent-negative',True,'15.01')),
 ]
