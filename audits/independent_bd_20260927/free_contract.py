"""Fresh independently authored revision tests; expectations frozen in RETEST_PLAN.

The revised public contract explicitly permits reasoned FREE/WAIVED. Exercise
that contract through physical receipt and final SKU; do not seed priced rows.
"""
import json,copy,traceback
from decimal import Decimal as D
import suite as s, daily as d
C=s.CTX;A=s.admin;eq=s.eq

def save():
    (s.OUT/'free-contract-results.json').write_text(json.dumps({'candidate':'23e9c9830c32dce10604c43d17e4476d2707b55d','origin':'independent revision retest, peer-informed coverage additions labeled','results':s.RESULTS,'production_go':False},indent=2,default=str)+'\n')
    (s.OUT/'free-contract-events.json').write_text(json.dumps(s.EVENTS,indent=2,default=str)+'\n')
s.save=save

def complete(key):
    f=d.F[key];r=d.rpc('POST_RECEIPT',d.rp(key),d.ver('laundry_deliveries',f['delivery']));f.update(receipt=r['receipt_id'],receipt_line=A('select id::text from erp.laundry_receipt_lines where receipt_id=%s',(r['receipt_id'],),one=True))
    q=d.rpc('POST_FINAL_SKU',d.qp(key),d.ver('cutting_groups',f['group']));eq(d.qty(key),13);return {'receipt':r,'final':q}

def new_vendor(code):
    ident=s.uid();A('insert into erp.laundry_vendors(id,vendor_code,vendor_name) values(%s,%s,%s)',(ident,code,code));s.terms('COMPONENTS',vendor=ident);return ident

def own_free(status):
    key='REV_'+status;d.precursor(key);vendor=new_vendor('AUD-REV-'+status);comp=s.component(vendor,'AUD-REV-'+status)
    master=s.rate(comp,'0.00',status=status)
    p=d.dp(key);p['delivery']['vendor_id']=vendor;p['pricing']={'components':[{'component_id':comp,'covered_qty':13}]}
    r=s.command('POST_PRICED_DELIVERY',p);f=d.F[key];f.update(delivery=r['delivery_id'],delivery_line=A('select id::text from erp.laundry_delivery_lines where delivery_id=%s',(r['delivery_id'],),one=True))
    eq(D(r['pricing']['total_known']),D(0));eq(r['pricing']['total_complete'],True)
    ch=A('select rate_status,unit_rate,amount,price_reason from erp.bd_laundry_charge_lines_v1 where delivery_line_id=%s',(f['delivery_line'],));eq(ch[0][:3],(status,D(0),D(0)));assert ch[0][3]
    done=complete(key);values=d.costeq(key,'1300.00')
    accrued=A("select coalesce(sum(l.credit-l.debit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.po_id=%s and l.account_id=erp.account_id('ACCRUED_MANUFACTURING') and j.status in('POSTED','REVERSED')",(f['po'],),one=True);eq(accrued,D(0))
    return {'master':master,'shipment':r,'physical':done,'charges':ch,'hpp_labor_only':'1300.00','hpp':values,'laundry_accrual':'0.00'}

def resolve_free(status):
    key='REV_U_'+status;d.precursor(key);d.ship(key,True);done=complete(key);f=d.F[key]
    ch=A("select id::text from erp.bd_laundry_charge_lines_v1 where delivery_line_id=%s and rate_status='UNKNOWN'",(f['delivery_line'],),one=True)
    before=d.qty(key);r=s.command('SET_CHARGE_PRICE',{'charge_line_id':ch,'rate_status':status,'rate_per_pcs':'0.00','reason':'Independent explicit owner waiver after physical receipt and QC'})
    eq(r['complete'],True);eq(D(r['total_known']),D('56174.17'));eq(d.qty(key),before)
    values=d.costeq(key,'57474.17');shares=A('select s.size_id::text,sh.covered_qty,sh.amount from erp.bd_laundry_charge_shares_v1 sh join erp.laundry_delivery_batch_size_lines s on s.id=sh.delivery_batch_size_line_id where sh.charge_line_id=%s order by s.size_id',(ch,))
    eq({z[0]:(z[1],z[2]) for z in shares},{C['s1']:(0,D(0)),C['s2']:(5,D(0))})
    return {'resolution':r,'physical_unchanged':before,'coverage_preserved':shares,'hpp':values,'physical':done}

def invalid_free():
    comp=s.component(C['daily_vendor'],'AUD-REV-INVALID');out=[]
    for status,amount,reason in [('KNOWN','0.00','Zero is not known positive'),('FREE','1.00','Positive cannot be free'),('WAIVED','-1.00','Negative is not waived'),('FREE','0.00','')]:
        out.append(s.reject(lambda status=status,amount=amount,reason=reason:s.command('SAVE_COMPONENT_RATE',{'component_id':comp,'rate_status':status,'rate_per_pcs':amount,'effective_from':'2026-09-01T08:00:00+07:00','reason':reason})))
    out.append(s.reject(lambda:s.command('SAVE_COMPONENT_RATE',{'component_id':comp,'rate_status':'FREE','rate_per_pcs':'0.00','effective_from':'2026-09-01T08:00:00+07:00','reason':'No privilege'},who='staff')))
    return out

def coverage():
    # Peer concern independently recalculated: L-only five pieces at1000 must
    # allocate exactly0 to M and5000 to L, regardless of7:6 shipment proportions.
    vendor=new_vendor('AUD-REV-COVERAGE');comp=s.component(vendor,'AUD-REV-L-ONLY');s.rate(comp,'1000.00')
    p={'components':[{'component_id':comp,'covered_qty':5,'coverage':[{'size_id':C['s2'],'qty':5}]}]}
    delivery=s.delivery(vendor=vendor);r=s.pricing(p,delivery);eq(D(r['total_known']),D('5000.00'))
    shares=r['charges'][0]['shares'];eq({x['size_id']:D(x['amount']) for x in shares},{C['s1']:D(0),C['s2']:D(5000)})
    rejected=[]
    for cov in [None,[{'size_id':C['s1'],'qty':4}],[{'size_id':C['s2'],'qty':7}],[{'size_id':s.uid(),'qty':5}],[{'size_id':C['s2'],'qty':2},{'size_id':C['s2'],'qty':3}]]:
        bad=copy.deepcopy(p)
        if cov is None:bad['components'][0].pop('coverage')
        else:bad['components'][0]['coverage']=cov
        rejected.append(s.helper_refuse(bad,delivery))
    return {'origin':'peer-informed independent calculation','shares':shares,'invalid_or_ambiguous_coverage':rejected}

def main():
    fixture=json.loads((s.OUT/'daily-fixture.json').read_text());C.update(fixture['identity']);d.F.update(fixture['sources'])
    for status in ['FREE','WAIVED']:
        s.case('REV.FREE.'+status,'Legitimate '+status+' dispatch receipt final SKU and zero laundry GL',lambda status=status:own_free(status),'public SQL physical lifecycle')
        s.case('REV.UNKNOWN.'+status,'Actual unknown charge resolves to '+status+' with exact preserved recipients',lambda status=status:resolve_free(status),'public SQL physical and financial lifecycle')
    s.case('REV.FREE.INVALID','Invalid free values and unauthorized actor fail closed',invalid_free,'public SQL authenticated')
    s.case('REV.COVERAGE','Only the five actual L recipients get5000 service cost',coverage,'pricing readback + invalid public input contract')
    d.precursor('REV_UI_EXTRA');(s.OUT/'revision-browser-fixture.json').write_text(json.dumps({'identity':C,'source':d.F['REV_UI_EXTRA']},default=str))
    save()
if __name__=='__main__':
    try:main()
    except Exception as e:s.RESULTS.append({'id':'REV.SETUP','status':'BLOCKED','error':str(e),'traceback':traceback.format_exc()});save()
    print(json.dumps(s.RESULTS,default=str),flush=True)
