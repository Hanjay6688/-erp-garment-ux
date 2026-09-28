"""Original PLAN IND-28/29: own claim source and public credit allocations.
Oracle fixed before execution: 1234.57 = 501.23 + 733.34; one economic credit,
two document applications, no physical or cash mutation. No peer test reuse.
"""
import daily as d
import suite as s
import json,traceback,time
from decimal import Decimal as D
from psycopg.types.json import Jsonb
import psycopg
C=s.CTX;F=d.F;E=s.EVENTS;R=[]
def save():
    (s.OUT/'credit-results.json').write_text(json.dumps({'candidate':'e96db5a270da5aa6d0f12c3812ac1c0542df938e','scope':'Own native daily claim plus real public credit RPC','results':R,'production_go':False},indent=2,default=str)+'\n')
    (s.OUT/'credit-events.json').write_text(json.dumps(E,indent=2,default=str)+'\n')
s.save=save
def case(id,title,fn,needs=()):
    missing=[k for k in needs if k not in C]
    if missing:R.append(dict(id=id,title=title,status='BLOCKED',missing=missing));save();return
    x=dict(id=id,title=title);start=time.monotonic()
    try:x.update(status='PASS',observation=fn())
    except Exception as e:x.update(status='FAIL',error=str(e),traceback=traceback.format_exc())
    x['seconds']=time.monotonic()-start;R.append(x);save();print(json.dumps({k:x.get(k) for k in ['id','status','error']},default=str),flush=True)
def fp():
    before=d.fp()
    for n in ['vendor_payments','laundry_claims','bd_claim_credit_applications_v1']:
        before[n]=s.admin("select md5(coalesce(string_agg(to_jsonb(t)::text,'' order by to_jsonb(t)::text),'')) from erp."+n+' t',one=True)
    return before
def native(q,args):
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],));c.execute("select set_config('app.change_reason','Independent claim lifecycle',true)")
        r=c.execute(q,args).fetchone()[0]
    E.append({'layer':'ERP native claim; not HTTP authorization proof','query':q,'args':args,'response':r});return r
def ap():
    return s.admin("select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.vendor_id=%s and l.account_id=erp.account_id('AP_VENDOR') and j.status in('POSTED','REVERSED')",(C['daily_vendor'],),one=True)
def setup():
    state=json.loads((s.OUT/'daily-fixture.json').read_text());C.update(state['identity']);F.update(state['sources'])
    assert all('invoice' in F.get(k,{}) for k in ['K','U']),'Daily invoice prerequisites not established'
    C['credit_before_ap']=ap();s.eq(C['credit_before_ap'],D('122492.48'))
    d.precursor('C');d.ship('C')
    return {'claim_physical_source':F['C'],'initial_ap':'122492.48'}
def claim():
    before=ap();p={'action':'SAVE','claim_number':'AUD-CLAIM-INDEP','vendor_id':C['daily_vendor'],'delivery_id':F['C']['delivery'],'qty_claimed':1,'claim_type':'MISSING','compensation_amount':'1234.57','opened_at':'2026-09-24T08:00:00+07:00','resolution_date':'2026-09-25','change_reason':'Independent missing piece with agreed compensation'}
    r=native('select erp.save_laundry_claim_v2(%s,%s::uuid,null)',(Jsonb(p),s.uid()));C['credit_claim']=r['laundry_claim_id'];s.eq(ap(),before,'Open claim is not settled credit')
    native('select erp.resolve_laundry_claim(%s,%s,%s)',(C['credit_claim'],'SETTLED','Independent vendor accepted compensation'))
    s.eq(ap(),before-D('1234.57'));C['credit_post_settlement_ap']=ap()
    s.eq(s.admin('select sum(qty_good_received+qty_bs_laundry) from erp.laundry_receipt_lines l join erp.laundry_receipts r on r.id=l.receipt_id where r.delivery_id=%s',(F['C']['delivery'],),one=True),None,'Claim cannot fabricate returned goods')
    return {'claim':d.row('laundry_claims',C['credit_claim']),'ap_before':before,'ap_after':ap()}
def payload(target,amount):return {'source_kind':'DAILY_CLAIM','source_id':C['credit_claim'],'target_kind':'VENDOR_INVOICE','target_id':target,'amount':amount,'date':'2026-09-25','reason':'Independent claim credit allocation'}
def use(key,amount,left):
    before=ap();target=F[key]['invoice']['invoice_id'];req=s.uid();p=payload(target,amount);r=s.command('APPLY_CLAIM_CREDIT',p,req)
    s.eq(D(r['credit_left']),D(left));s.eq(D(r['remaining']),D('61246.24')-D(amount));s.eq(ap(),before,'Applying existing credit cannot reduce payable a second time')
    C['credit_'+key]=r;C['credit_request_'+key]=req;C['credit_payload_'+key]=p
    return {'response':r,'ap_before_after':before,'application':d.row('bd_claim_credit_applications_v1',r['application_id'])}
def rejected(fn):
    before=fp()
    try:fn()
    except psycopg.Error as e:
        s.eq(e.sqlstate,'P0001');s.eq(fp(),before);return {'refused':str(e),'sqlstate':e.sqlstate,'unchanged':before}
    raise AssertionError('Invalid credit accepted')
def other_vendor():
    target=s.admin("select id::text from erp.bd_laundry_invoices_v1 where invoice_number='AUD-PART-6'",one=True)
    return rejected(lambda:s.command('APPLY_CLAIM_CREDIT',payload(target,'10.00')))
def replay():
    before=fp();r=s.command('APPLY_CLAIM_CREDIT',C['credit_payload_K'],C['credit_request_K']);s.eq(r['application_id'],C['credit_K']['application_id']);s.eq(fp(),before);return r
def reconcile():
    rows=s.admin('select a.id::text,a.amount,p.vendor_invoice_id::text,p.payment_method,p.cash_account_id from erp.bd_claim_credit_applications_v1 a join erp.vendor_payments p on p.id=a.vendor_payment_id where a.laundry_claim_id=%s order by a.amount',(C['credit_claim'],))
    s.eq(len(rows),2);s.eq([x[1] for x in rows],[D('501.23'),D('733.34')]);s.eq(sum(x[1] for x in rows),D('1234.57'));s.eq({x[2] for x in rows},{F[k]['invoice']['invoice_id'] for k in ['K','U']});assert all(x[4] is None for x in rows)
    s.eq(ap(),D('121257.91'));return {'separate_applications':rows,'remaining_vendor_ap':ap(),'total_credit':'1234.57'}
def main():
    try:E.append({'setup':setup()})
    except Exception as e:R.append({'id':'SETUP.CREDIT','status':'BLOCKED','error':str(e),'traceback':traceback.format_exc()});save();return 1
    case('IND-28.SOURCE','Native claim creates exactly 1234.57 credit without return fabrication',claim)
    case('IND-28.VENDOR','Claim credit cannot settle another vendor invoice',other_vendor,['credit_claim'])
    case('IND-28.FIRST','501.23 settles one invoice without another economic credit',lambda:use('K','501.23','733.34'),['credit_claim'])
    case('IND-19.CREDIT','Same credit application UUID has one effect',replay,['credit_K'])
    case('IND-29.SECOND','Remaining 733.34 applies to a distinct invoice with its own allocation',lambda:use('U','733.34','0.00'),['credit_K'])
    case('IND-29.RECONCILE','Two linked allocations conserve 1234.57 and ledger matches documents',reconcile,['credit_U'])
    case('IND-28.EXCESS','One extra cent after credit exhausted is refused atomically',lambda:rejected(lambda:s.command('APPLY_CLAIM_CREDIT',payload(F['K']['invoice']['invoice_id'],'0.01'))),['credit_U'])
    case('IND-28.REVERSAL','Claim with active credit allocations cannot be reversed',lambda:rejected(lambda:native('select erp.reverse_laundry_claim_resolution(%s,%s)',(C['credit_claim'],'Independent reversal of used credit'))),['credit_U'])
    save();return int(any(r['status']!='PASS' for r in R))
if __name__=='__main__':raise SystemExit(main())
