"""Paid-source supplier-credit continuations on the explicit full F03 stack.

The accepted Native credit allocator, payments, journals and guards are reused.
No paid-refund policy, accounting engine or new supplier balance is introduced.
"""
from decimal import Decimal as D
import cp6_bf_supplier_probe as credit
import cp6_bb_probe as opening

def prepare(cur,today):
 f=credit.fixture(cur,today)
 credit.call(cur,credit.payload(cur,f,[(f['purchases'][1],'20.00')]))
 f['bank_before']=str(opening.bank(cur,f))
 payment=credit.bc.supplier_payment(cur,f['purchases'][1],'80.00',f['cash'],today)
 credit.bc.internal(cur,'post_supplier_payment',payment)
 credit.b.api.admin(cur)
 f.update(today=str(today),payment_id=str(payment),return_number=credit.one(cur,'select return_number from erp.material_supplier_returns where id=%s',f['ret']),
  numbers=[credit.one(cur,'select purchase_number from erp.material_purchase_headers where id=%s',p)for p in f['purchases']],initial=credit.state(cur,f))
 return f

def observe(cur,f):
 credit.b.api.admin(cur)
 state=credit.state(cur,f)
 payments=[str(credit.one(cur,"select coalesce(sum(amount),0)::numeric(20,2) from erp.supplier_payments where purchase_id=%s and status='POSTED'",p))for p in f['purchases']]
 remaining=[str((D(ap)-D(paid)).quantize(D('.01')))for ap,paid in zip(state['ap'],payments)]
 bank=str(opening.bank(cur,f))
 return dict(state,paid=payments,remaining=remaining,bank=bank,bank_delta=str((D(bank)-D(f['bank_before'])).quantize(D('.01'))),
  move_event_count=credit.one(cur,'select count(*) from erp.bf_supplier_credit_moves_v1 where return_id=%s',f['ret']))

def cases(cur,today):
 def paid_carry():
  r=credit.cash_and_reallocation(cur,today);assert r['status']=='PASS',r
  return dict(r,actual_Native_paid_target_reopens_owed20=True,source_return_credit_original_restorable_after_payment_inverse=True,
   stock_HPP_and_net_AP_unchanged_by_reallocation=True,current_original_payment_blocks_credit_reuse=True,full_family_acceptance=False)
 return [('F03_P09_NATIVE_PAID_SUPPLIER_CREDIT_CARRY',paid_carry)]

def races(tools,today):
 def competing():
  r=credit.race(tools,today,True);assert r['status']=='PASS',r
  return dict(r,actual_Native_credit_source_wait=True,no_two_target_use_of_one_supplier_credit=True)
 return [('F03_P09_REAL_SUPPLIER_CREDIT_SOURCE_RACE',competing)]

def http_cases(http,today):
 return [('F03_P09_REAL_HTTP_SUPPLIER_CREDIT_CURRENT_AUTHORITY',operation)for _,operation in credit.http_cases(http,today)]
