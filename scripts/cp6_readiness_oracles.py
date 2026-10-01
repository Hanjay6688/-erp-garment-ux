"""New oracles derived during readiness review, not replay labels or an audit signoff.

Native fixture helpers create real source documents. Expectations below derive
from the owner decisions and decimal arithmetic, not the helper's expected map.
Only the existing disposable runner may execute these cases.
"""
import json,uuid
from decimal import Decimal,ROUND_HALF_UP
from datetime import timedelta
import cp6_bf_probe as bf
import cp6_ba_probe as ba
b,one=bf.b,bf.one

def invoice_prerequisites(cur,today):
    fx=b.fixture(cur,b.case_day(today),'READINESS-POLICY');b.terms(cur,fx,'RATE');b.process_rate(cur,fx,'1.23')
    b.policy(cur,'LAU_DEC02',operation='CLEAR');b.policy(cur,'LAU_DEC06',operation='CLEAR')
    sent=b.post_priced(cur,fx,{})
    received=b.receive(cur,sent['delivery_id'],fx,10,13);line=b.receipt_line(cur,received['receipt_id'])
    draft,_=b.invoice(cur,fx,[dict(line=line,qty=10,amount='12.30')],'12.30',post=False)
    def state():
        return cur.execute('select status,row_version from erp.bd_laundry_invoices_v1 where id=%s',(draft['invoice_id'],)).fetchone(), b.ap(cur,fx['vendor']),b.accrual(cur,fx['po'])
    before=state()
    both=b.refused(cur,lambda:b.post_draft(cur,draft),'BD_POLICY_PENDING')
    unchanged_both=state()==before
    b.policy(cur,'LAU_DEC02',dict(billable=['GOOD']))
    one_missing=b.refused(cur,lambda:b.post_draft(cur,draft),'BD_POLICY_PENDING')
    unchanged_one=state()==before
    b.policy(cur,'LAU_DEC06',dict(variance_mode='PRODUCT_COST',after_payment='CORRECTION_DOCUMENT'))
    posted=b.post_draft(cur,draft)
    checks=dict(pcs_shipping_and_receipt_without_optional_policy=one(cur,'select qty_good_received from erp.laundry_receipt_lines where id=%s',line)==10,
      draft_allowed=draft['status']=='DRAFT',pending_refuses_atomic=both['ok'] and unchanged_both,
      second_required_policy_refuses_atomic=one_missing['ok'] and unchanged_one,
      applies_real_policy_then_posts=posted['status']=='POSTED' and Decimal(b.ap(cur,fx['vendor']))==Decimal('12.30'),
      estimate_replaced_once=Decimal(b.accrual(cur,fx['po'])['desired'])==0 and Decimal(b.accrual(cur,fx['po'])['booked'])==0)
    return b.verdict(checks,oracle={'pcs':10,'invoice':'12.30','no_policy_draft':'ALLOWED','no_policy_post':'REFUSED'})

def mixed_zero_unknown(cur,today):
    fx=b.fixture(cur,b.case_day(today),'READINESS-MIXED');b.terms(cur,fx,'COMPONENTS')
    components=[]
    for status,qty,amount in [('FREE',10,'0.00'),('WAIVED',3,'0.00'),('UNKNOWN',1,None),('KNOWN',9,'3.17')]:
        c=b.bd(cur,'SAVE_COMPONENT',dict(vendor_id=fx['vendor'],component_code=status,component_name='Readiness '+status,is_active=True,reason='Disposable prerequisite'))['component_id']
        payload=dict(component_id=c,rate_status=status,effective_from=fx['start'].isoformat(),reason='Explicit '+status)
        if amount is not None:payload['rate_per_pcs']=amount
        b.bd(cur,'SAVE_COMPONENT_RATE',payload);components.append(dict(component_id=c,covered_qty=qty))
    pricing=dict(components=components);sent=b.post_priced(cur,fx,pricing);state=b.line_state(cur,sent['delivery_id'])
    rows=cur.execute('select rate_status,covered_qty,unit_rate,amount,bf_sku_version_id from erp.bd_laundry_charge_lines_v1 where delivery_line_id=%s order by line_no',(state['line'],)).fetchall()
    expected=[('FREE',10,Decimal('0'),Decimal('0'),None),('WAIVED',3,Decimal('0'),Decimal('0'),None),('UNKNOWN',1,None,None,None),('KNOWN',9,Decimal('3.17'),Decimal('28.53'),None)]
    return b.verdict(dict(exact_status_and_vendor_source=rows==expected,partial_known_sum=Decimal(state['known'])==Decimal('28.53'),
      unknown_is_not_zero=state['rate'] is None and not state['complete'] and sent['estimated_cost'] is None,
      physical_qty=state['qty']==10),oracle={'known':'28.53','unknown':None,'free':'0.00','waived':'0.00'},observed=rows)

def rounding_seven(cur,today,kind):
    observed=ba.a4_stacked(cur,today,kind,7,'10.004','10.006')
    day=b.case_day(today)
    # The fixture operates on exactly the day passed to it; no expectation is
    # read from observed['expected'] or from its final PASS/FAIL label.
    old=(Decimal('10.004').quantize(Decimal('.01'),rounding=ROUND_HALF_UP))*7
    new=(Decimal('10.006').quantize(Decimal('.01'),rounding=ROUND_HALF_UP))*7
    checks={}
    for raw_date,row in observed['observed'].items():
        when=__import__('datetime').date.fromisoformat(raw_date)
        amount=new if when>=today-timedelta(days=2) else old
        debit='MATERIAL_INVENTORY' if when<today-timedelta(days=3) else 'WIP'
        liability='AP_SUPPLIER' if kind=='DIRECT' or when>=today-timedelta(days=2) else 'GRNI_MATERIAL'
        expected={key:Decimal('0') for key in row};expected[debit]=amount;expected[liability]=-amount
        checks[raw_date]=all(Decimal(str(row[key]))==value for key,value in expected.items())
    checks['no_value_lost_between_pos']=sum(Decimal(v) for v in observed['per_po'].values())==Decimal('70.07')
    checks['zero_stock_and_native_source_trail']=all(observed['checks'][k] for k in ('used_up_zero','trail_cuts','trail_adjustments'))
    return b.verdict(checks,oracle={'rounded_each_document':'70.07','round_only_combined':'70.04','per_po_cent_limit':None},native_observation=observed)

def cases(cur,today):
    return [('READINESS:POST_REQUIRES_BOTH_POLICIES_DRAFT_PHYSICAL_ALLOWED',lambda:invoice_prerequisites(cur,today)),
      ('READINESS:FREE_WAIVED_UNKNOWN_KNOWN_KEEP_DISTINCT',lambda:mixed_zero_unknown(cur,today)),
      ('READINESS:W8_SEVEN_DOCUMENTS_DIRECT_DECIMAL_ORACLE',lambda:rounding_seven(cur,today,'DIRECT')),
      ('READINESS:W8_SEVEN_DOCUMENTS_INVOICE_DECIMAL_ORACLE',lambda:rounding_seven(cur,today,'INVOICE'))]
