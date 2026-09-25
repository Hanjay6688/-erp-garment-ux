"""rev2: column names fixed (system_created_at; target_wash_process_id on the delivery header); oracles unchanged.
AUDITOR SCENARIO xaudit_8 (round 9, Fable, independent): W8 several-receipt cents and LAU-T14 rate at send time.
Tool head d1bc8ad (writer round 9). Oracles from the contract only:
 W8  M:1022/M:1059-1065/M:3818/M:3820 + rounding half away from zero (M:485): each purchase document is rounded on its own;
     when every unit of the material is consumed the material inventory carries qty 0 and value 0, and WIP carries the sum of
     the separately rounded document values. Cases: 2 receipts (DIRECT correction and late INVOICE, UP and DOWN) and 3 receipts.
 LAU-T14 M:4474 LAU-DEC03 ('snapshot kesepakatan; jangan reprice otomatis menurut tanggal kembali'): a rate version that starts
     between send and return must not change the actual cost of that delivery; the actual rate is the one effective at send time.
     Cases: rate UP between send and receipt; rate DOWN; control without change; a GAP (no version effective at send time) must be
     refused (no silent zero, no return-date rate) with no residue.
Every unexpected error is INCOMPLETE. Refusals are recorded verbatim."""
from datetime import timedelta
from decimal import Decimal,ROUND_HALF_UP
import json,traceback,uuid
import psycopg
import cp6_aw_probe as awp
import cp6_az_probe as azp
import cp6_au_r1_probe as r1
api=awp.api;chain=awp.chain;prod=chain.production
KEYS=('MATERIAL_INVENTORY','WIP','FG_INVENTORY','COGS')
D=Decimal
def cents(v):return D(str(v)).quantize(D('0.01'),rounding=ROUND_HALF_UP)

def attempt(cur,fn):
    api.admin(cur);cur.execute('savepoint xa8')
    try:
        r=fn();cur.execute('release savepoint xa8');api.admin(cur);return r,None
    except psycopg.Error as exc:
        cur.execute('rollback to savepoint xa8');api.admin(cur);return None,dict(sqlstate=exc.sqlstate,message=(exc.diag.message_primary or str(exc))[:400])

# ---------------------------------------------------------------- W8 fixtures (ordinary purchase RPCs, own material + warehouse)
def receipt(cur,day,price,kind,first=None):
    """One receipt of 1 unit at `price` on `day` 10:00. kind DIRECT = FINAL with supplier invoice number; INVOICE = ESTIMATED.
    With `first`, the same material and warehouse are used (a second/third document of the same material)."""
    prior=prod.prior;api.admin(cur);prod.zone(cur,'Asia/Jakarta')
    if first:material,location=first['material'],first['location']
    else:
        material=prior.clone_material(cur,'xa8');location=uuid.uuid4()
        cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,'XA8 raw warehouse','RAW_MATERIAL_WAREHOUSE',true)",(location,'XA8-LOC-'+location.hex[:20]))
    line=dict(material_id=material,qty=1,unit_price=price,rolls=[dict(roll_number='XA8-ROLL-'+str(uuid.uuid4()),qty=1)])
    payload=dict(purchase_number='XA8-PUR-'+str(uuid.uuid4()),supplier_id=prior.BASE_SUPPLIER,location_id=location,physical_at=prod.at(day,10),change_reason='XA8 receipt of one unit',lines=[line])
    if kind=='DIRECT':line.update(price_state='FINAL',price_source='SUPPLIER_INVOICE');payload['supplier_invoice_number']='XA8-INV-'+uuid.uuid4().hex[:12]
    else:line.update(price_state='ESTIMATED',price_source='MANUAL_ESTIMATE')
    draft=prod.rpc(cur,'erp.save_material_purchase_draft_v2',payload)
    purchase=uuid.UUID(draft['purchase_id'])
    cur.execute('select erp.post_material_purchase_v2(%s,%s,%s,%s)',(purchase,uuid.uuid4(),int(draft['row_version']),'XA8 receipt post'))
    api.admin(cur)
    item,roll=cur.execute('select i.id,r.id from erp.material_purchase_items i join erp.material_rolls r on r.purchase_item_id=i.id where i.purchase_id=%s',(purchase,)).fetchone()
    return dict(material=material,purchase=purchase,item=item,location=location,roll=roll)

def reprice(cur,fx,kind,day,price):
    """DIRECT: a purchase cost correction (product's own AO path) dated `day`. INVOICE: the late supplier invoice dated `day`."""
    api.admin(cur)
    if kind=='DIRECT':
        cid=uuid.uuid4()
        cur.execute("insert into erp.material_purchase_cost_corrections(id,correction_number,purchase_id,supplier_invoice_number,invoice_date,reason,status) values(%s,%s,%s,%s,%s,'XA8 cost correction','DRAFT')",(cid,'XA8-CC-'+cid.hex[:12],fx['purchase'],'XA8-CCINV-'+cid.hex[:12],day))
        cur.execute('insert into erp.material_purchase_cost_correction_items(correction_id,purchase_item_id,new_unit_price) values(%s,%s,%s)',(cid,fx['item'],price))
        prod.owner(cur);cur.execute('select erp.post_material_purchase_cost_correction(%s)',(cid,));api.admin(cur);return str(cid)
    version=int(cur.execute('select row_version from erp.material_purchase_headers where id=%s',(fx['purchase'],)).fetchone()[0])
    payload=dict(purchase_id=fx['purchase'],supplier_invoice_number='XA8-LINV-'+uuid.uuid4().hex[:12],invoice_date=str(day),received_at=prod.at(day,15),reason='XA8 late invoice at '+price,lines=[dict(purchase_item_id=fx['item'],qty_invoiced=1,final_unit_price=price)])
    prod.zone(cur,'Asia/Jakarta');r=prod.rpc(cur,'erp.finalize_material_purchase_invoice_v2',payload,uuid.uuid4(),version);api.admin(cur);return r

def multi_receipt(cur,today,kind,n,p0,p1):
    d=today-timedelta(days=5);days=[d+timedelta(days=i) for i in range(6)]
    awp.boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    before=azp.ledger_days(cur,days,[])
    fxs=[];pos=[]
    for i in range(n):
        fx=receipt(cur,d,p0,kind,fxs[0] if fxs else None);fxs.append(fx)
    for fx in fxs:pos.append(azp.cut(cur,fx,d+timedelta(days=1),1,8+len(pos)))
    mid=azp.ledger_days(cur,days,pos)
    docs=[]
    for fx in fxs:
        r,err=attempt(cur,lambda fx=fx:reprice(cur,fx,kind,d+timedelta(days=2),p1))
        docs.append(dict(result=str(r)[:200] if r is not None else None,refusal=err))
        if err:break
    prod.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');api.admin(cur)
    after=azp.ledger_days(cur,days,pos);last=str(days[-1])
    delta={k:str(D(after[last][k])-D(before[last][k])) for k in KEYS}
    delta_mid={k:str(D(mid[last][k])-D(before[last][k])) for k in KEYS}
    daily={k:{kk:str(D(after[k][kk])-D(before[k][kk])) for kk in ('MATERIAL_INVENTORY','WIP')} for k in after}
    raw=cur.execute('select coalesce(sum(qty_signed),0)::text from erp.material_stock_movements where material_id=%s',(fxs[0]['material'],)).fetchone()[0]
    moves=cur.execute('select movement_type,qty_signed::text,unit_cost_snapshot::text,original_unit_cost_snapshot::text,physical_at::text from erp.material_stock_movements where material_id=%s order by physical_at,system_created_at',(fxs[0]['material'],)).fetchall()
    expected_wip=str(cents(p1)*n);expected_wip_before=str(cents(p0)*n)
    errs=[x['refusal'] for x in docs if x['refusal']]
    checks=dict(all_documents_posted=not errs,raw_qty_zero=D(raw)==0,inventory_value_zero_at_end=D(delta['MATERIAL_INVENTORY'])==0,
                wip_before_reprice_equals_sum_of_rounded_documents=delta_mid['WIP']==expected_wip_before,
                wip_equals_sum_of_rounded_documents=delta['WIP']==expected_wip,no_negative_daily_inventory=all(D(v['MATERIAL_INVENTORY'])>=0 for v in daily.values()),
                wip_per_po_each_equals_rounded_document=all(D(after[last]['WIP_PO'][str(p)])==cents(p1) for p in pos))
    status='INCOMPLETE' if errs else ('PASS' if all(checks.values()) else 'COUNTEREXAMPLE')
    return dict(status=status,checks=checks,kind=kind,receipts=n,p0=p0,p1=p1,receipt_day=str(d),cut_day=str(d+timedelta(days=1)),reprice_day=str(d+timedelta(days=2)),
                delta_after_cut=delta_mid,delta_end=delta,expected_wip=expected_wip,expected_wip_before=expected_wip_before,raw_qty=raw,daily_delta=daily,
                wip_per_po_end={k:v for k,v in after[last]['WIP_PO'].items()},movements=[[str(x) for x in m] for m in moves],documents=docs,
                expected='M:1022/M:1059-1065/M:3818/M:3820 + M:485 rounding: %d documents of 1 unit each rounded on their own; consumed material leaves qty 0 and value 0; WIP = %s; each PO carries its own rounded document value'%(n,expected_wip))

# ---------------------------------------------------------------- LAU-T14 (rate at send time)
def lau_ledger(cur,day):
    api.admin(cur)
    rows=cur.execute("""select a.mapping_key,sum(l.debit-l.credit)::text from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id and j.status in('POSTED','REVERSED')
      join erp.accounting_account_mappings a on a.account_id=l.account_id where a.mapping_key in('LAUNDRY_COST','ACCRUED_MANUFACTURING','AP_VENDOR') and j.transaction_date<=%s group by 1""",(day,)).fetchall()
    return {k:v for k,v in rows}

def lau_t14(cur,today,mode):
    f=r1.production(cur,today);api.admin(cur)
    day=f['day'];sent=f['delivery']
    vendor,process,sent_at=cur.execute('select vendor_id,target_wash_process_id,physical_at from erp.laundry_deliveries where id=%s',(sent,)).fetchone()
    versions=cur.execute('select id,rate_per_pcs::text,effective_from::text,effective_to::text from erp.laundry_vendor_rate_versions where vendor_id=%s and wash_process_id=%s and effective_from<=%s and (effective_to is null or effective_to>%s) order by effective_from',(vendor,process,sent_at,sent_at)).fetchall()
    if len(versions)!=1:return dict(status='INCOMPLETE',error='expected exactly one rate version effective at send time',versions=[[str(x) for x in v] for v in versions])
    vid,r0=versions[0][0],D(versions[0][1])
    estimate=cur.execute('select estimated_rate_snapshot::text,qty_sent_pcs::text from erp.laundry_delivery_lines where delivery_id=%s',(sent,)).fetchone()
    ledger_before=lau_ledger(cur,day)
    cut=sent_at+timedelta(minutes=30);later=r0+2 if mode=='UP' else (r0-2 if mode=='DOWN' else None)
    if mode in('UP','DOWN'):
        if later<0:return dict(status='INCOMPLETE',error='send-time rate too low for a DOWN version',r0=str(r0))
        cur.execute('update erp.laundry_vendor_rate_versions set effective_to=%s where id=%s',(cut,vid))
        cur.execute("insert into erp.laundry_vendor_rate_versions(vendor_id,wash_process_id,rate_per_pcs,effective_from,notes) values(%s,%s,%s,%s,'XA8 later master version')",(vendor,process,later,cut))
    elif mode=='GAP':
        # the send-time version is cut off BEFORE the send; the new version starts after the send: nothing is effective at send time
        cur.execute('update erp.laundry_vendor_rate_versions set effective_to=%s where id=%s',(sent_at-timedelta(minutes=30),vid))
        cur.execute("insert into erp.laundry_vendor_rate_versions(vendor_id,wash_process_id,rate_per_pcs,effective_from,notes) values(%s,%s,%s,%s,'XA8 later master version after a gap')",(vendor,process,r0+2,cut))
    api.admin(cur);snap=awp.boundary.snapshot(cur)
    r,err=attempt(cur,lambda:r1.receipt(cur,f,prod.at(day,12),0))
    api.admin(cur);unchanged=awp.boundary.snapshot(cur)==snap
    if mode=='GAP':
        checks=dict(refused=err is not None,no_residue=unchanged,no_receipt_row=cur.execute('select count(*) from erp.laundry_receipts where delivery_id=%s',(sent,)).fetchone()[0]==0)
        return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,mode=mode,send_rate=str(r0),refusal=err,
                    expected='M:4474 LAU-DEC03: with no agreed rate effective at send time the receipt must be refused (no return-date rate, no silent zero), atomically')
    if err:return dict(status='INCOMPLETE',mode=mode,refusal=err,send_rate=str(r0))
    rl=cur.execute('select actual_rate_snapshot::text,actual_cost::text,actual_cost_status,qty_good_received+qty_bs_laundry from erp.laundry_receipt_lines l join erp.laundry_receipts h on h.id=l.receipt_id where h.delivery_id=%s',(sent,)).fetchone()
    ledger_after=lau_ledger(cur,day)
    qty=D(str(rl[3]));expected_cost=str(cents(r0*qty))
    checks=dict(actual_rate_is_send_time_rate=D(rl[0])==r0,actual_cost_is_qty_times_send_rate=D(rl[1])==D(expected_cost),
                estimate_unchanged=D(estimate[0])==r0,receipt_did_not_post_return_rate=(D(ledger_after.get('LAUNDRY_COST','0'))-D(ledger_before.get('LAUNDRY_COST','0'))) not in (later*qty,later*qty-r0*qty) if later is not None else True)
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,mode=mode,send_rate=str(r0),later_rate=str(later) if later is not None else None,version_cut_at=str(cut),
                receipt_line=[str(x) for x in rl],delivery_estimate=[str(x) for x in estimate],ledger_delta={k:str(D(ledger_after.get(k,'0'))-D(ledger_before.get(k,'0'))) for k in set(ledger_before)|set(ledger_after)},
                expected='M:4474 LAU-DEC03 / LAU-T14: actual rate = rate effective at send time (%s), actual cost = qty x that rate (%s); a version starting between send and return does not reprice'%(r0,expected_cost))

def cases(cur,today):
    def wrap(fn,*a):
        def run():
            try:return fn(cur,today,*a)
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:900],traceback=traceback.format_exc()[-1500:])
        return run
    out=[]
    for kind in ('DIRECT','INVOICE'):
        for label,p0,p1 in (('UP','10.00','10.005'),('DOWN','10.01','10.004')):
            out.append(('XA8:W8_TWO_RECEIPTS_%s_%s'%(kind,label),wrap(multi_receipt,kind,2,p0,p1)))
    out.append(('XA8:W8_THREE_RECEIPTS_INVOICE_UP',wrap(multi_receipt,'INVOICE',3,'10.00','10.005')))
    out.append(('XA8:W8_THREE_RECEIPTS_DIRECT_DOWN',wrap(multi_receipt,'DIRECT',3,'10.01','10.004')))
    for mode in ('UP','DOWN','CONTROL','GAP'):
        out.append(('XA8:LAU_T14_RATE_%s_BETWEEN_SEND_AND_RECEIPT'%mode,wrap(lau_t14,mode)))
    return out
