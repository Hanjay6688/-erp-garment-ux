"""Predeclared owning receipt-correction oracles ("Benerin penerimaan").

Masters, locations and deliberate access/failure controls are isolated test
setup. Every receipt, cutting, sewing, laundry, QC, sale, payment, transfer
and correction effect is produced by accepted Native writers or the public
CP7 commands. No fixture inserts stock, HPP, AP or journal results.
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timedelta
from decimal import Decimal as D
from pathlib import Path
import copy,json,threading,time,uuid
import psycopg
import cp7_procurement_cases as receipt
import cp7_material_cases as material
import cp7_invoice_cases as invoice
import cp7_procurement_uom_cases as uom
import cp7_f03_e01_cases as e01
import cp7_sales_draft_cases as drafts
import cp7_sales_return_cases as returned
import cp6_ao_ap_installed as imports
import cp6_initial_import_prepayment_trial as prepaid
auth,b,bc,aa=receipt.auth,receipt.b,receipt.bc,receipt.aa
cmd,source=drafts.cmd,drafts.source
ROOT=Path(__file__).resolve().parents[1]
MANIFEST=json.loads((ROOT/'scripts/cp7_receipt_correction_manifest.json').read_text())
assert MANIFEST['schema']=='cp7-receipt-correction-native-manifest-v1'
REQUIRED=MANIFEST['required_counts']
EXPECTED=MANIFEST['expected_case_executions']
assert EXPECTED==sum(REQUIRED.values())

def ws(cur,purchase,subject=None):
    auth.actor(cur,subject)
    out=cur.execute('select public.erp_cp7_get_receipt_correction_v1(%s)',(purchase,)).fetchone()[0]
    b.api.admin(cur);return out

def fix(cur,payload,version,key=None,subject=None):
    auth.actor(cur,subject)
    out=cur.execute('select public.erp_cp7_correct_receipt_v1(%s,%s,%s)',(json.dumps(payload),key or uuid.uuid4(),version)).fetchone()[0]
    b.api.admin(cur);return out

def instants(v):
    """Card rows compared by instant: timestamps render in the session time zone."""
    if isinstance(v,list):return [instants(x) for x in v]
    if isinstance(v,dict):return {k:(datetime.fromisoformat(x) if k.endswith('_at') and isinstance(x,str) else instants(x)) for k,x in v.items()}
    return v

def name_ws(cur,material,subject=None):
    auth.actor(cur,subject)
    out=cur.execute('select public.erp_cp7_get_material_name_v1(%s)',(material,)).fetchone()[0]
    b.api.admin(cur);return out

def rename(cur,payload,version,key=None,subject=None):
    auth.actor(cur,subject)
    out=cur.execute('select public.erp_cp7_rename_material_v1(%s,%s,%s)',(json.dumps(payload),key or uuid.uuid4(),version)).fetchone()[0]
    b.api.admin(cur);return out

def card(cur,material_id,roll,location,offset=0,limit=100,subject=None,version=2):
    auth.actor(cur,subject)
    out=cur.execute('select public.erp_cp7_get_material_ledger_v%s(%%s,%%s,%%s,%%s,%%s)'%version,(material_id,roll,location,offset,limit)).fetchone()[0]
    b.api.admin(cur);return out

def full_card(cur,material_id,roll,location,version=2):
    rows=[];offset=0
    while True:
        page=card(cur,material_id,roll,location,offset,100,version=version)
        rows+=page['page']['rows']
        if page['page']['next_offset'] is None:break
        offset=page['page']['next_offset']
    assert len(rows)==int(page['page']['total'])
    return rows

def payload(w,reason='Jumlah/bahan pada penerimaan salah ketik; dicek dengan surat jalan',**edit):
    """Corrected document from the reviewed workspace. edit(line, roll) can change values."""
    lines=[]
    for n,line in enumerate(w['lines']):
        item=dict(replaces_item_id=line['item_id'],material_id=line['material_id'],unit_price=line['unit_price'],
          price_state=line['price_state'],price_source=line['price_source'],
          rolls=[dict(replaces_roll_id=r['roll_id'],roll_number=r['roll_number'],qty=r['qty'].rstrip('0').rstrip('.') if '.' in r['qty'] else r['qty']) for r in line['rolls']])
        if not line['rolls']:item['qty']=line['qty']
        if 'line' in edit:edit['line'](n,item)
        lines.append(item)
    if 'lines' in edit:lines=edit['lines'](lines)
    return dict(purchase_id=w['current_purchase_id'],review_token=w['review_token'],change_reason=reason,lines=lines)

def raw(cur,material_id):
    return cur.execute('select coalesce(sum(qty_signed),0),coalesce(sum(qty_signed*unit_cost_snapshot),0) from erp.material_stock_movements where material_id=%s',(material_id,)).fetchone()

def ledger(cur):
    return dict(cur.execute("select m.mapping_key,sum(l.debit-l.credit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id join erp.accounting_account_mappings m on m.account_id=l.account_id where j.status in('POSTED','REVERSED') group by 1 having sum(l.debit-l.credit)<>0").fetchall())

def ledger_delta(before,after):
    return {k:after.get(k,D(0))-before.get(k,D(0)) for k in set(before)|set(after) if after.get(k,D(0))!=before.get(k,D(0))}

CHECKS=None
def checks(cur):
    global CHECKS
    if CHECKS is None:
        CHECKS=[r[0] for r in cur.execute("select p.oid::regprocedure::text from pg_proc p where pronamespace='erp'::regnamespace and proname ~ '^run_v[0-9a-z]+_.*checks$' and pronargs=0 and proname not like '%%performance%%' and proname not like '%%security%%' order by 1").fetchall()]
    out={}
    for f in CHECKS:
        cur.execute('savepoint rf_check')
        try:
            rows=cur.execute('select * from '+f).fetchall();cols=[d.name for d in cur.description]
            ni=next((i for i,c in enumerate(cols) if c in('issue_count','violations','count','issues')),None)
            for r in rows:
                if ni is not None:out[f+':'+str(r[0])]=int(r[ni] or 0)
        except psycopg.Error as e:out[f+':ERROR']=str(e).splitlines()[0][:200]
        finally:cur.execute('release savepoint rf_check')
    return out

def same_checks(before,after):
    changed={k:(before.get(k),after.get(k)) for k in set(before)|set(after) if before.get(k)!=after.get(k)}
    assert not changed,('RF_INTEGRITY_CHECK_CHANGED',changed)

def reversal_dates(cur):
    rows=cur.execute("select check_name,issue_count from erp.run_v267_financial_truth_checks() where check_name='V2620U_JOURNAL_REVERSAL_BUSINESS_DATE'").fetchall()
    assert rows==[('V2620U_JOURNAL_REVERSAL_BUSINESS_DATE',0)],rows

def hpp(cur,f):
    h=e01.native(cur,'select to_jsonb(h) from erp.get_hpp_completeness(%s) h',(f['po'],))
    return D(str(h['current_hpp_total'])),D(str(h['hpp_per_pcs'])),h['pending_reason_count']

def facts(cur,purchase):
    """Immutable posted source: header identity, lines and its own stock/journal rows."""
    tz=cur.execute('show TimeZone').fetchone()[0];cur.execute("select set_config('TimeZone','UTC',true)")
    try:return cur.execute("""select jsonb_build_object(
     'header',(select to_jsonb(h)-array['status','payment_status','row_version','updated_at'] from erp.material_purchase_headers h where id=%s),
     'items',(select jsonb_agg(to_jsonb(i)-array['invoice_match_state'] order by id) from erp.material_purchase_items i where purchase_id=%s),
     'journal',(select jsonb_agg(jsonb_build_array(j.id,j.economic_date,j.transaction_date) order by j.id) from erp.journal_entries j where j.source_type in('MATERIAL_PURCHASE','MATERIAL_PURCHASE_GRNI_RECLASS') and j.source_id=%s),
     'lines',(select jsonb_agg(jsonb_build_array(l.account_id,l.debit,l.credit) order by l.id) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where j.source_type='MATERIAL_PURCHASE' and j.source_id=%s))""",(purchase,purchase,purchase,purchase)).fetchone()[0]
    finally:cur.execute("select set_config('TimeZone',%s,true)",(tz,))

def movement_rows(cur,purchase):
    return cur.execute("""select m.id,m.qty_signed,m.physical_at,m.system_created_at,m.material_id,m.roll_id from erp.material_stock_movements m
      where m.movement_type='PURCHASE' and (m.source_type='MATERIAL_PURCHASE_ROLL' and m.source_id in(select r.id from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=%s)
       or m.source_type='MATERIAL_PURCHASE_ITEM' and m.source_id in(select id from erp.material_purchase_items where purchase_id=%s)) order by m.id""",(purchase,purchase)).fetchall()

def snapshot(cur):
    b.api.admin(cur)
    return dict(native=b.boundary.snapshot(cur),metadata=cur.execute("""select jsonb_build_object(
      'requests',(select count(*) from cp7_receipt_fix.requests),'revisions',(select count(*) from cp7_receipt_fix.revisions),
      'rolls',(select count(*) from cp7_receipt_fix.roll_lineage),'moves',(select count(*) from cp7_receipt_fix.movement_lineage),
      'links',(select count(*) from cp7_receipt_fix.ledger_links),'journals',(select count(*) from cp7_receipt_fix.journal_restatements),
      'payments',(select count(*) from cp7_receipt_fix.payment_replays),'context',(select count(*) from cp7_receipt_fix.context),
      'invoices',(select count(*) from cp7_receipt_fix.invoice_replays),'invoice_dates',(select count(*) from cp7_receipt_fix.invoice_restatements),
      'name_requests',(select count(*) from cp7_receipt_fix.name_requests),'names',(select count(*) from cp7_receipt_fix.material_names))""").fetchone()[0])

def refused(cur,op,code):
    before=snapshot(cur);detail=auth.refused(cur,op,code);assert snapshot(cur)==before,('RF_REFUSAL_LEFT_EFFECTS',code);return detail

def clone(cur,tag='cp7-fix'):
    return str(aa.prior.clone_material(cur,tag))

def production(cur,today,final=True):
    f=e01.production(cur,today,receipt_final=final)
    f['line']=ws(cur,f['purchase'])['lines'][0]
    return f

def invoiced_production(cur,today,price='12'):
    """E01 with an estimated receipt (100 x10) finalized by a P09 supplier invoice 100 x price."""
    f=production(cur,today,final=False)
    f['item']=f['line']['item_id'];f['receipt']=dict(purchase_id=f['purchase'])
    invoice.finalize(cur,f,p=invoice.payload(f,qty='100',price=price))
    return f

def invoices(w,qty=None,price=None):
    """Every posted invoice of the reviewed receipt, line by line, optionally corrected."""
    return [dict(replaces_invoice_id=v['invoice_id'],lines=[dict(replaces_invoice_line_id=l['invoice_line_id'],qty_invoiced=qty or l['qty_invoiced'],
      unit_price=price or l['unit_price'],discount_amount=l['discount_amount']) for l in v['lines']]) for v in w['invoices']]

def by_date(cur):
    return {(d,k):v for d,k,v in cur.execute("select j.economic_date,m.mapping_key,sum(l.debit-l.credit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id join erp.accounting_account_mappings m on m.account_id=l.account_id where j.status in('POSTED','REVERSED') group by 1,2").fetchall()}

def dated_delta(before,after):
    out={}
    for k in set(before)|set(after):
        v=after.get(k,D(0))-before.get(k,D(0))
        if v:out.setdefault(k[0],{})[k[1]]=v
    return out

def roll_receipt(cur,today,rolls=('50','50','50'),price='10',final=True,day_offset=None):
    """A posted fabric receipt with several declared rolls, through the public receipt command."""
    f=receipt.fixture(cur,today,qty=str(sum(D(r) for r in rolls)),price=price,final=final)
    if day_offset is not None:
        f['day']=today-timedelta(days=day_offset);aa.prior.set_open_period(cur,f['day']-timedelta(days=1))
        # Before 10:00 WIB, a current-day fixture must use a real past time.
        # Preserve its date (the advance guard compares business dates) and
        # retain Native's future-event refusal unchanged.
        planned=aa.at(f['day'],10)
        clock=cur.execute('select clock_timestamp()').fetchone()[0]
        f['payload']['physical_at']=min(planned,clock-timedelta(seconds=1)).isoformat()
    f['payload']['lines'][0]['rolls']=[dict(roll_number=f['tag']+'-R%d'%(n+1),qty=q) for n,q in enumerate(rolls)]
    d=receipt.command(cur,'SAVE_DRAFT',f['payload']);f['receipt']=receipt.post(cur,d);f['purchase']=f['receipt']['purchase_id']
    f['rolls']=[str(r[0]) for r in cur.execute('select r.id from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=%s order by r.roll_number',(f['purchase'],)).fetchall()]
    f['roll']=f['rolls'][0];f['destination']=str(uuid.uuid4())
    cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,%s,'RAW_MATERIAL_WAREHOUSE',true)",(f['destination'],f['tag']+'-TO',f['tag']+' destination'))
    return f

def transfer(cur,f,qty,roll=None,at=None):
    """An ordinary posted warehouse transfer through the public P09 command. The
    number is sequential per fixture: 364 random 6-hex suffixes collided in run
    37029649347 (duplicate transfer_number, a fixture defect)."""
    f['transfers']=f.get('transfers',0)+1
    p=dict(transfer_number='%s-T%04d'%(f['tag'],f['transfers']),from_location_id=f['location'],to_location_id=f['destination'],
      physical_at=at or aa.at(f['day']+timedelta(days=1),10).isoformat(),change_reason='P09 ordinary warehouse transfer',
      items=[dict(material_id=f['material'],roll_id=roll or f['roll'],qty=qty)])
    return material.post(cur,material.command(cur,'SAVE_TRANSFER',p))

def cases(cur,today):
    def qty_down():
        f=production(cur,today);before,chk,orig=ledger(cur),checks(cur),facts(cur,f['purchase'])
        w=ws(cur,f['purchase']);assert w['can_correct'] and w['blockers']==[] and w['lines'][0]['rolls'][0]['min_qty']=='60.000000',w
        out=fix(cur,payload(w,line=lambda n,i:i['rolls'][0].update(qty='80')),w['purchase']['row_version'])
        assert raw(cur,f['material'])==(D(20),D(200)),raw(cur,f['material'])
        assert hpp(cur,f)==(D(900),D(15),0),hpp(cur,f)
        assert cur.execute('select erp.material_purchase_final_ap_total(%s)',(out['purchase_id'],)).fetchone()[0]==800
        assert ledger_delta(before,ledger(cur))=={'MATERIAL_INVENTORY':D(-200),'AP_SUPPLIER':D(200)},ledger_delta(before,ledger(cur))
        assert facts(cur,f['purchase'])==orig and cur.execute('select status from erp.material_purchase_headers where id=%s',(f['purchase'],)).fetchone()[0]=='REVERSED'
        roll=cur.execute('select r.id::text,r.original_qty,r.cached_qty,i.purchase_id::text from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where r.id=%s',(f['roll'],)).fetchone()
        assert roll==(f['roll'],D(80),D(20),out['purchase_id']),roll
        assert cur.execute('select roll_id::text from erp.cutting_group_rolls where cutting_group_id=%s',(f['group'],)).fetchone()[0]==f['roll']
        rows=full_card(cur,f['material'],f['roll'],f['raw_location'])
        first=rows[-1];assert first['movement_type']=='PURCHASE' and first['qty_signed']=='80.000000' and first['original_qty_signed']=='100.000000' and first['correction_count']=='2' and first['running_qty']=='80.000000',first
        assert len(rows)==2 and rows[0]['running_qty']=='20.000000' and rows[0]['qty_signed']=='-60.000000',rows
        assert full_card(cur,f['material'],f['roll'],f['raw_location'],version=1)[0]['running_qty']=='20.000000'
        h=ws(cur,f['purchase']);assert h['current_purchase_id']==out['purchase_id'] and len(h['history'])==1 and h['history'][0]['previous_document']['lines'][0]['rolls'][0]['qty']=='100.000000'
        same_checks(chk,checks(cur));reversal_dates(cur)
        return dict(status='PASS',received_100_used_60_corrected_80=True,remaining_20_value_200=True,hpp_900_unchanged=True,ap_800=True,same_physical_roll_kept=True,
          cutting_link_unchanged=True,original_receipt_immutable_and_reversed=True,main_card_first_row_effective_80_original_100=True,later_running_balance_20=True,all_integrity_checks_unchanged=True)
    def qty_up():
        f=production(cur,today);before,chk=ledger(cur),checks(cur);w=ws(cur,f['purchase'])
        out=fix(cur,payload(w,line=lambda n,i:i['rolls'][0].update(qty='120')),w['purchase']['row_version'])
        assert raw(cur,f['material'])==(D(60),D(600)) and hpp(cur,f)==(D(900),D(15),0)
        assert ledger_delta(before,ledger(cur))=={'MATERIAL_INVENTORY':D(200),'AP_SUPPLIER':D(-200)}
        rows=full_card(cur,f['material'],f['roll'],f['raw_location']);assert rows[-1]['qty_signed']=='120.000000' and rows[0]['running_qty']=='60.000000'
        same_checks(chk,checks(cur));reversal_dates(cur)
        return dict(status='PASS',received_100_corrected_120=True,remaining_60_value_600=True,ap_1200=True,all_integrity_checks_unchanged=True,replacement=out['purchase_id'])
    def price_after_sale():
        f=production(cur,today);report_before=e01.ready_report(cur,today)
        drafts.create(cur,f,drafts.payload(f,'20','25'));p,v=cmd.review(cur,f);cmd.command(cur,'POST',p,v)
        returned.payments.pay(cur,f,'200');f['allocations']=returned.read(cur,f)['page']['rows']
        rp,rv=returned.payload(cur,f,qty='5',refund='125');cmd.command(cur,'RETURN',rp,rv)
        assert e01.physical(cur,f)==45
        before,chk=ledger(cur),checks(cur);w=ws(cur,f['purchase'])
        fix(cur,payload(w,line=lambda n,i:i.update(unit_price='12')),w['purchase']['row_version'])
        assert raw(cur,f['material'])==(D(40),D(480)) and hpp(cur,f)==(D(1020),D(17),0),(raw(cur,f['material']),hpp(cur,f))
        delta=ledger_delta(before,ledger(cur))
        assert delta=={'AP_SUPPLIER':D(-200),'MATERIAL_INVENTORY':D(80),'FG_INVENTORY':D(90),'COGS':D(30)},delta
        report=e01.ready_report(cur,today)
        same_checks(chk,checks(cur));reversal_dates(cur)
        return dict(status='PASS',price_10_to_12_after_cutting_sale_payment_return=True,raw40_value480=True,hpp17=True,fg45_plus90=True,net_sold15_cogs_plus30=True,ap_plus200=True,
          report_confidence=report['snapshot']['data_confidence']['status'],all_integrity_checks_unchanged=True)
    def wrong_material(price=None):
        f=production(cur,today);B=clone(cur,'cp7-fix-b');before,chk=ledger(cur),checks(cur);w=ws(cur,f['purchase'])
        movement=str(cur.execute("select id from erp.material_stock_movements where source_type='CUTTING_GROUP' and source_id=%s",(f['group'],)).fetchone()[0])
        def change(n,i):
            i['material_id']=B
            if price:i['unit_price']=price
        out=fix(cur,payload(w,line=change),w['purchase']['row_version'])
        new_roll=str(cur.execute('select r.id from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=%s',(out['purchase_id'],)).fetchone()[0])
        unit=D(price or 10)
        assert raw(cur,f['material'])==(D(0),D(0)) and raw(cur,B)==(D(40),D(40)*unit),(raw(cur,f['material']),raw(cur,B))
        assert cur.execute('select material_id::text,roll_id::text,qty_signed from erp.material_stock_movements where id=%s',(movement,)).fetchone()==(B,new_roll,D(-60))
        assert cur.execute('select roll_id::text from erp.cutting_group_rolls where cutting_group_id=%s',(f['group'],)).fetchone()[0]==new_roll
        assert cur.execute('select old_material_id::text,old_roll_id::text,new_material_id::text from cp7_receipt_fix.movement_lineage where movement_id=%s',(movement,)).fetchone()==(f['material'],f['roll'],B)
        assert cur.execute('select cached_qty,status from erp.material_rolls where id=%s',(f['roll'],)).fetchone()==(D(0),'EXHAUSTED')
        old=full_card(cur,f['material'],f['roll'],f['raw_location']);assert len(old)==1 and old[0]['qty_signed']=='0.000000' and old[0]['original_qty_signed']=='100.000000',old
        new=full_card(cur,B,new_roll,f['raw_location']);assert [r['running_qty'] for r in new]==['40.000000','100.000000'],new
        delta=ledger_delta(before,ledger(cur))
        if price:
            assert hpp(cur,f)==(D(1020),D(17),0) and delta=={'AP_SUPPLIER':D(-200),'MATERIAL_INVENTORY':D(80),'FG_INVENTORY':D(120)},(hpp(cur,f),delta)
        else:assert hpp(cur,f)==(D(900),D(15),0) and delta=={},(hpp(cur,f),delta)
        same_checks(chk,checks(cur));reversal_dates(cur)
        return dict(status='PASS',material_A_to_B_after_cutting=True,A_history_zero=True,B_on_hand_40=True,cutting_use_same_row_time_qty_now_B=True,
          prior_attribute_recorded=True,price_changed=bool(price),all_integrity_checks_unchanged=True)
    def roll_count():
        f=roll_receipt(cur,today);transfer(cur,f,'4');before,chk=ledger(cur),checks(cur);w=ws(cur,f['purchase'])
        out=fix(cur,payload(w,lines=lambda ls:[dict(ls[0],rolls=ls[0]['rolls'][:2])]),w['purchase']['row_version'])
        assert raw(cur,f['material'])==(D(100),D(1000)) and cur.execute('select erp.material_purchase_final_ap_total(%s)',(out['purchase_id'],)).fetchone()[0]==1000
        assert ledger_delta(before,ledger(cur))=={'MATERIAL_INVENTORY':D(-500),'AP_SUPPLIER':D(500)}
        kinds=sorted(r[0] for r in cur.execute('select kind from cp7_receipt_fix.roll_lineage where correction_id=%s',(out['revision_id'],)).fetchall())
        assert kinds==['REMOVED','REPARENTED','REPARENTED'],kinds
        assert cur.execute('select cached_qty,status from erp.material_rolls where id=%s',(f['rolls'][2],)).fetchone()==(D(0),'EXHAUSTED')
        same_checks(chk,checks(cur))
        return dict(status='PASS',typed_three_rolls_actual_two=True,unused_third_roll_closed=True,used_roll_identity_kept=True,ap_1500_to_1000=True,all_integrity_checks_unchanged=True)
    def removed_used():
        f=roll_receipt(cur,today);transfer(cur,f,'4');w=ws(cur,f['purchase'])
        refused(cur,lambda:fix(cur,payload(w,lines=lambda ls:[dict(ls[0],rolls=ls[0]['rolls'][1:])]),w['purchase']['row_version']),'CP7_RECEIPT_FIX_REMOVED_ROLL_USED')
        return dict(status='PASS',used_roll_cannot_disappear=True,no_partial_effect=True)
    def below_use():
        f=production(cur,today);w=ws(cur,f['purchase'])
        refused(cur,lambda:fix(cur,payload(w,line=lambda n,i:i['rolls'][0].update(qty='50')),w['purchase']['row_version']),'CP7_RECEIPT_FIX_ROLL_BELOW_USE')
        return dict(status='PASS',corrected_50_below_used_60_refused=True,no_partial_effect=True)
    def paid(amount,expect):
        f=roll_receipt(cur,today,rolls=('100',));masters=bc.fixture(cur,today,purchase=False,zones=False)
        payment=bc.supplier_payment(cur,f['purchase'],amount,masters['cash'],today);bc.internal(cur,'post_supplier_payment',payment);b.api.admin(cur)
        cash_before=cur.execute('select sum(l.debit-l.credit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id join erp.cash_accounts c on c.coa_account_id=l.account_id where c.id=%s and j.status in(\'POSTED\',\'REVERSED\')',(masters['cash'],)).fetchone()[0]
        before=ledger(cur);w=ws(cur,f['purchase']);p=payload(w,line=lambda n,i:i['rolls'][0].update(qty='80'))
        if not expect:
            # Owner decision 2 Oct 2026: the excess is credit cut from another nota of the same supplier; without a chosen nota it is refused.
            refused(cur,lambda:fix(cur,p,w['purchase']['row_version']),'CP7_RECEIPT_FIX_CREDIT_ALLOCATION_REQUIRED')
            small=roll_receipt(cur,today,rolls=('10',))
            refused(cur,lambda:fix(cur,dict(p,credit_allocations=[dict(purchase_id=small['purchase'],amount='200')]),w['purchase']['row_version']),'CP7_RECEIPT_FIX_CREDIT_TARGET_EXCEEDS_REMAINING')
            refused(cur,lambda:fix(cur,dict(p,credit_allocations=[dict(purchase_id=f['purchase'],amount='200')]),w['purchase']['row_version']),'CP7_RECEIPT_FIX_CREDIT_TARGET_INVALID')
            refused(cur,lambda:fix(cur,dict(p,credit_allocations=[dict(purchase_id=small['purchase'],amount='50')]),w['purchase']['row_version']),'CP7_RECEIPT_FIX_CREDIT_ALLOCATION_MISMATCH')
            return dict(status='PASS',payment_1000_exceeds_corrected_800=True,credit_target_required=True,target_remaining_checked=True,
              own_receipt_not_a_target=True,allocation_must_equal_credit=True,no_partial_effect=True,supplier_refund_flow_not_invented=True)
        out=fix(cur,p,w['purchase']['row_version'])
        replay=cur.execute('select r.replacement_payment_id,s.amount,s.payment_date,s.status,o.payment_date from cp7_receipt_fix.payment_replays r join erp.supplier_payments s on s.id=r.replacement_payment_id join erp.supplier_payments o on o.id=r.previous_payment_id where r.previous_payment_id=%s',(payment,)).fetchone()
        assert replay and replay[1]==D(amount) and replay[2]==replay[4] and replay[3]=='POSTED',replay
        assert cur.execute('select status from erp.supplier_payments where id=%s',(payment,)).fetchone()[0]=='REVERSED'
        cash_after=cur.execute('select sum(l.debit-l.credit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id join erp.cash_accounts c on c.coa_account_id=l.account_id where c.id=%s and j.status in(\'POSTED\',\'REVERSED\')',(masters['cash'],)).fetchone()[0]
        assert cash_after==cash_before
        assert cur.execute('select payment_status from erp.material_purchase_headers where id=%s',(out['purchase_id'],)).fetchone()[0]=='PARTIAL'
        assert cur.execute('select erp.material_purchase_payable_total(%s)',(out['purchase_id'],)).fetchone()[0]==800
        assert ledger_delta(before,ledger(cur))=={'MATERIAL_INVENTORY':D(-200),'AP_SUPPLIER':D(200)}
        assert cur.execute('select count(*) from cp7_receipt_fix.journal_restatements where previous_purchase_id=%s',(f['purchase'],)).fetchone()[0]>=1
        reversal_dates(cur)
        return dict(status='PASS',real_payment_300_reversed_and_replayed_same_date_amount=True,cash_unchanged=True,payable_800_remaining_500=True,economic_dates_restated=True)
    def overpaid_credit():
        f=roll_receipt(cur,today,rolls=('100',),day_offset=10);t=roll_receipt(cur,today,rolls=('100',),day_offset=2)
        masters=bc.fixture(cur,today,purchase=False,zones=False);pay_day=f['day']+timedelta(days=1)
        # A payment cancelled before the correction keeps its own cancellation date.
        early=bc.supplier_payment(cur,f['purchase'],'50',masters['cash'],pay_day);bc.internal(cur,'post_supplier_payment',early)
        bc.internal(cur,'reverse_supplier_payment',early,'RF payment cancelled before the correction');b.api.admin(cur)
        cancel=cur.execute("select v.id,v.economic_date from erp.journal_entries v join erp.journal_entries o on o.id=v.reversal_of_id where v.source_type='JOURNAL_REVERSAL' and o.source_type='SUPPLIER_PAYMENT' and o.source_id=%s",(early,)).fetchone()
        payment=bc.supplier_payment(cur,f['purchase'],'1000',masters['cash'],pay_day);bc.internal(cur,'post_supplier_payment',payment);b.api.admin(cur)
        cash=lambda:cur.execute("select sum(l.debit-l.credit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id join erp.cash_accounts c on c.coa_account_id=l.account_id where c.id=%s and j.status in('POSTED','REVERSED')",(masters['cash'],)).fetchone()[0]
        state=lambda pid:cur.execute("select round(erp.material_purchase_payable_total(h.id),2),coalesce((select sum(amount) from erp.supplier_payments where purchase_id=h.id and status='POSTED'),0),h.payment_status from erp.material_purchase_headers h where h.id=%s",(pid,)).fetchone()
        before,dated,chk,cash_before=ledger(cur),by_date(cur),checks(cur),cash()
        w=ws(cur,f['purchase']);assert [x['remaining'] for x in w['credit_targets'] if x['purchase_id']==t['purchase']]==['1000.00'],w['credit_targets']
        p=payload(w,reason='Surat jalan asli 80 yard; 20 yard tidak pernah diterima',line=lambda n,i:i['rolls'][0].update(qty='80'))
        out=fix(cur,dict(p,credit_allocations=[dict(purchase_id=t['purchase'],amount='200')]),w['purchase']['row_version'])
        assert cur.execute('select original_qty,cached_qty from erp.material_rolls where id=%s',(f['roll'],)).fetchone()==(D(80),D(80))
        assert state(out['purchase_id'])==(D(800),D(800),'PAID') and state(t['purchase'])==(D(1000),D(200),'PARTIAL'),(state(out['purchase_id']),state(t['purchase']))
        moved=cur.execute("select s.amount,s.payment_date,s.cash_account_id::text,s.notes,r.kind from cp7_receipt_fix.payment_replays r join erp.supplier_payments s on s.id=r.replacement_payment_id where r.previous_payment_id=%s order by r.kind",(payment,)).fetchall()
        assert [(m[0],m[4]) for m in moved]==[(D(800),'CORRECTED_RECEIPT'),(D(200),'CREDIT_TO_OTHER_RECEIPT')],moved
        original_date=cur.execute('select payment_date from erp.supplier_payments where id=%s',(payment,)).fetchone()[0]
        assert all(m[1]==original_date and m[2]==masters['cash'] for m in moved) and 'barang tidak pernah diterima' in moved[1][3],moved
        assert cash()==cash_before
        delta=ledger_delta(before,ledger(cur));assert delta=={'MATERIAL_INVENTORY':D(-200),'AP_SUPPLIER':D(200)},delta
        dd=dated_delta(dated,by_date(cur));assert dd=={f['day']:{'MATERIAL_INVENTORY':D(-200),'AP_SUPPLIER':D(200)}},dd
        same_checks(chk,checks(cur));reversal_dates(cur)
        assert cur.execute('select economic_date from erp.journal_entries where id=%s',(cancel[0],)).fetchone()[0]==cancel[1]
        assert not cur.execute('select exists(select 1 from cp7_receipt_fix.journal_restatements where inverse_journal_id=%s)',(cancel[0],)).fetchone()[0]
        return dict(status='PASS',paid_1000_corrected_800=True,earlier_cancellation_keeps_its_own_date=True,credit_200_cut_from_next_nota=True,next_nota_received_later_paid_200_partial=True,
          same_cash_account_and_original_date=True,note_retur_bayangan_barang_tidak_pernah_diterima=True,cash_unchanged=True,
          effects_on_receipt_date_only=True,all_integrity_checks_unchanged=True)
    def credit_restored():
        """A supplier credit moved onto a receipt and later moved back no longer blocks correcting it."""
        import cp6_bf_supplier_probe as bfs
        f=bfs.fixture(cur,today);a,z,k=f['purchases'];code='CP7_RECEIPT_FIX_SUPPLIER_CREDIT_ACTIVE'
        codes=lambda pid:[x['code'] for x in ws(cur,pid)['blockers']]
        bfs.call(cur,bfs.payload(cur,f,[(z,'20.00')]));b.api.admin(cur);assert code in codes(z),codes(z)
        bfs.call(cur,bfs.payload(cur,f,[]));b.api.admin(cur)
        assert cur.execute('select count(*) from erp.bf_supplier_credit_moves_v1 where target_purchase_id=%s',(z,)).fetchone()[0]==2
        assert code not in codes(z),codes(z)
        return dict(status='PASS',moved_credit_blocks=True,restored_credit_net_zero_unblocks=True,append_only_history_kept=True)
    def opening_advance():
        """Receipt paid 60 from the supplier's opening advance (uang muka saldo awal) and 400 cash, corrected twice."""
        # Every date is in the past at any hour (a receipt at today 10:00 WIB is
        # refused as future before 10:00): cutover today-2, advance used today-2,
        # the later nota received today-1, the earlier one today-4.
        f=roll_receipt(cur,today,rolls=('100',),day_offset=3);late=roll_receipt(cur,today,rolls=('100',),day_offset=1);early=roll_receipt(cur,today,rolls=('100',),day_offset=4)
        aa.prior.set_open_period(cur,today-timedelta(days=5));masters=bc.fixture(cur,today,purchase=False,zones=False)
        cash_pay=bc.supplier_payment(cur,f['purchase'],'400',masters['cash'],f['day']);bc.internal(cur,'post_supplier_payment',cash_pay);b.api.admin(cur)
        supplier=cur.execute('select supplier_id from erp.material_purchase_headers where id=%s',(f['purchase'],)).fetchone()[0]
        w=prepaid.fixture(imports,cur,today-timedelta(days=1),'SUPPLIER',party=supplier,bill=None)
        prepaid.manage(imports,cur,w,'APPLY',today-timedelta(days=2),target_id=f['purchase'],amount='60');b.api.admin(cur)
        advance_pay=cur.execute('select payment_id from erp.initial_import_prepayment_payments where advance_id=%s',(w['advance'],)).fetchone()[0]
        cash=lambda:cur.execute("select sum(l.debit-l.credit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id join erp.cash_accounts c on c.coa_account_id=l.account_id where c.id=%s and j.status in('POSTED','REVERSED')",(masters['cash'],)).fetchone()[0]
        state=lambda pid:cur.execute("select round(erp.material_purchase_payable_total(h.id),2),coalesce((select sum(amount) from erp.supplier_payments where purchase_id=h.id and status='POSTED'),0),h.payment_status from erp.material_purchase_headers h where h.id=%s",(pid,)).fetchone()
        replays=lambda prev:cur.execute("""select r.kind,r.target_purchase_id::text,s.amount,s.payment_date=o.payment_date,s.cash_account_id::text,s.payment_method,l.advance_id::text,s.notes
          from cp7_receipt_fix.payment_replays r join erp.supplier_payments s on s.id=r.replacement_payment_id join erp.supplier_payments o on o.id=r.previous_payment_id
          left join erp.initial_import_prepayment_payments l on l.supplier_payment_id=s.id where r.previous_payment_id=%s order by r.kind,s.amount""",(prev,)).fetchall()
        wallet=lambda:(prepaid.state(imports,cur,w)['remaining_amount'],prepaid.bank(cur,w))
        assert wallet()==('7.25',100),wallet()
        before,dated,chk,cash_before=ledger(cur),by_date(cur),checks(cur),cash()
        w1=ws(cur,f['purchase']);assert w1['can_correct'] and w1['paid_total']=='460.00',w1
        n1=fix(cur,payload(w1,line=lambda n,i:i['rolls'][0].update(qty='80')),w1['purchase']['row_version'])['purchase_id']
        r=replays(cash_pay);assert [x[:5]+(x[6],) for x in r]==[('CORRECTED_RECEIPT',n1,D(400),True,masters['cash'],None)],r
        r=replays(advance_pay);assert [x[:7] for x in r]==[('CORRECTED_RECEIPT',n1,D(60),True,None,'OPENING_ADVANCE',str(w['advance']))],r
        assert state(n1)==(D(800),D(460),'PARTIAL') and wallet()==('7.25',100) and cash()==cash_before,(state(n1),wallet())
        delta=ledger_delta(before,ledger(cur));assert delta=={'MATERIAL_INVENTORY':D(-200),'AP_SUPPLIER':D(200)},delta
        dd=dated_delta(dated,by_date(cur));assert dd=={f['day']:{'MATERIAL_INVENTORY':D(-200),'AP_SUPPLIER':D(200)}},dd
        same_checks(chk,checks(cur));reversal_dates(cur)
        # 80 -> 40: payable 400 is covered by the 400 cash; the 60 from the
        # advance becomes credit on another nota at the advance use date.
        replayed=cur.execute("select replacement_payment_id from cp7_receipt_fix.payment_replays where previous_payment_id=%s",(advance_pay,)).fetchone()[0]
        before,chk=ledger(cur),checks(cur);w2=ws(cur,f['purchase']);p=payload(w2,line=lambda n,i:i['rolls'][0].update(qty='40'))
        refused(cur,lambda:fix(cur,dict(p,credit_allocations=[dict(purchase_id=late['purchase'],amount='60')]),w2['purchase']['row_version']),'CP7_RECEIPT_FIX_CREDIT_TARGET_AFTER_ADVANCE_USE')
        n2=fix(cur,dict(p,credit_allocations=[dict(purchase_id=early['purchase'],amount='60')]),w2['purchase']['row_version'])['purchase_id']
        r=replays(replayed);assert [x[:7] for x in r]==[('CREDIT_TO_OTHER_RECEIPT',early['purchase'],D(60),True,None,'OPENING_ADVANCE',str(w['advance']))] and 'barang tidak pernah diterima' in r[0][7],r
        assert state(n2)==(D(400),D(400),'PAID') and state(early['purchase'])==(D(1000),D(60),'PARTIAL'),(state(n2),state(early['purchase']))
        assert wallet()==('7.25',100) and cash()==cash_before,wallet()
        delta=ledger_delta(before,ledger(cur));assert delta=={'MATERIAL_INVENTORY':D(-400),'AP_SUPPLIER':D(400)},delta
        same_checks(chk,checks(cur));reversal_dates(cur)
        return dict(status='PASS',advance_60_and_cash_400_replayed=True,advance_payment_funded_from_same_advance=True,wallet_remaining_7_25_unchanged=True,
          cash_unchanged=True,excess_from_advance_credited_to_earlier_nota=True,later_nota_before_advance_use_named_refusal=True,all_integrity_checks_unchanged=True)
    def invoice_price_after_sale():
        f=invoiced_production(cur,today)
        drafts.create(cur,f,drafts.payload(f,'20','25'));p,v=cmd.review(cur,f);cmd.command(cur,'POST',p,v)
        returned.payments.pay(cur,f,'200');f['allocations']=returned.read(cur,f)['page']['rows']
        rp,rv=returned.payload(cur,f,qty='5',refund='125');cmd.command(cur,'RETURN',rp,rv)
        assert e01.physical(cur,f)==45 and hpp(cur,f)==(D(1020),D(17),0)
        before,dated,chk=ledger(cur),by_date(cur),checks(cur);w=ws(cur,f['purchase'])
        assert w['can_correct'] and w['lines'][0]['price_state']=='ESTIMATED' and w['lines'][0]['invoice_match_state']=='MATCHED' and len(w['invoices'])==1,w
        old=w['invoices'][0]
        out=fix(cur,dict(payload(w,reason='Harga final di invoice supplier salah ketik; 11 per meter'),invoices=invoices(w,price='11')),w['purchase']['row_version'])
        assert raw(cur,f['material'])==(D(40),D(440)) and hpp(cur,f)==(D(960),D(16),0),(raw(cur,f['material']),hpp(cur,f))
        delta=ledger_delta(before,ledger(cur));assert delta=={'AP_SUPPLIER':D(100),'MATERIAL_INVENTORY':D(-40),'FG_INVENTORY':D(-45),'COGS':D(-15)},delta
        # Each effect on its own date: the invoice on its book date, the cutting
        # revaluation and FG on the production day, the sold pieces on the sale day.
        dd=dated_delta(dated,by_date(cur))
        assert dd=={f['day']:{'AP_SUPPLIER':D(100),'MATERIAL_INVENTORY':D(-100)},f['production_day']:{'MATERIAL_INVENTORY':D(60),'FG_INVENTORY':D(-60)},
          today:{'FG_INVENTORY':D(15),'COGS':D(-15)}},dd
        new=cur.execute('select v.id::text,v.status,v.invoice_date,l.qty_invoiced,l.unit_price from erp.material_supplier_invoices v join erp.material_supplier_invoice_lines l on l.invoice_id=v.id join erp.material_purchase_items i on i.id=l.purchase_item_id where i.purchase_id=%s',(out['purchase_id'],)).fetchone()
        assert (new[1],str(new[2]),new[3],new[4])==('POSTED',old['invoice_date'][:10],D(100),D(11)),new
        assert cur.execute('select status from erp.material_supplier_invoices where id=%s',(old['invoice_id'],)).fetchone()[0]=='REVERSED'
        assert cur.execute('select replacement_invoice_id::text from cp7_receipt_fix.invoice_replays where previous_invoice_id=%s',(old['invoice_id'],)).fetchone()[0]==new[0]
        assert cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s)',(out['purchase_id'],out['purchase_id'])).fetchone()==(D(1100),D(0))
        h=ws(cur,f['purchase']);assert h['history'][0]['previous_document']['invoices'][0]['lines'][0]['unit_price']=='12.000000' and h['history'][0]['corrected_document']['invoices'][0]['lines'][0]['unit_price']=='11.000000'
        same_checks(chk,checks(cur));reversal_dates(cur)
        return dict(status='PASS',invoice_final_12_to_11_after_cutting_sale_return=True,hpp_1020_to_960=True,ap_1200_to_1100=True,
          invoice_book_date_ap_and_inventory=str(f['day']),production_day_revaluation_fg=str(f['production_day']),sold_pieces_on_sale_day=True,
          old_invoice_reversed_new_invoice_same_date=True,all_integrity_checks_unchanged=True)
    def invoiced_qty_down():
        f=invoiced_production(cur,today);masters=bc.fixture(cur,today,purchase=False,zones=False)
        payment=bc.supplier_payment(cur,f['purchase'],'500',masters['cash'],today);bc.internal(cur,'post_supplier_payment',payment);b.api.admin(cur)
        before,dated,chk=ledger(cur),by_date(cur),checks(cur);w=ws(cur,f['purchase'])
        out=fix(cur,dict(payload(w,line=lambda n,i:i['rolls'][0].update(qty='80')),invoices=invoices(w,qty='80')),w['purchase']['row_version'])
        assert raw(cur,f['material'])==(D(20),D(240)) and hpp(cur,f)==(D(1020),D(17),0),(raw(cur,f['material']),hpp(cur,f))
        assert cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s)',(out['purchase_id'],out['purchase_id'])).fetchone()==(D(960),D(0))
        delta=ledger_delta(before,ledger(cur));assert delta=={'MATERIAL_INVENTORY':D(-240),'AP_SUPPLIER':D(240)},delta
        dd=dated_delta(dated,by_date(cur));assert dd=={f['day']:{'MATERIAL_INVENTORY':D(-240),'AP_SUPPLIER':D(240)}},dd
        replay=cur.execute('select s.amount,s.status,s.payment_date=o.payment_date from cp7_receipt_fix.payment_replays r join erp.supplier_payments s on s.id=r.replacement_payment_id join erp.supplier_payments o on o.id=r.previous_payment_id where r.previous_payment_id=%s',(payment,)).fetchone()
        assert replay==(D(500),'POSTED',True),replay
        assert cur.execute('select payment_status from erp.material_purchase_headers where id=%s',(out['purchase_id'],)).fetchone()[0]=='PARTIAL'
        rows=full_card(cur,f['material'],f['roll'],f['raw_location']);assert rows[-1]['qty_signed']=='80.000000' and rows[-1]['original_qty_signed']=='100.000000' and rows[0]['running_qty']=='20.000000',rows
        same_checks(chk,checks(cur));reversal_dates(cur)
        return dict(status='PASS',invoiced_receipt_100_used_60_corrected_80=True,invoice_qty_80_x12=True,ap_1200_to_960=True,grni_zero=True,
          all_effects_on_invoice_book_date=True,supplier_payment_500_replayed_same_date=True,all_integrity_checks_unchanged=True)
    def invoice_refusals():
        f=invoiced_production(cur,today);w=ws(cur,f['purchase'])
        refused(cur,lambda:fix(cur,payload(w),w['purchase']['row_version']),'CP7_RECEIPT_FIX_INVOICE_DECISION_REQUIRED')
        over=dict(payload(w,line=lambda n,i:i['rolls'][0].update(qty='80')),invoices=invoices(w))
        refused(cur,lambda:fix(cur,over,w['purchase']['row_version']),'CP7_RECEIPT_FIX_INVOICE_EXCEEDS_RECEIPT')
        partial=dict(payload(w),invoices=[dict(x,lines=[]) for x in invoices(w)])
        refused(cur,lambda:fix(cur,partial,w['purchase']['row_version']),'CP7_RECEIPT_FIX_FIELDS')
        return dict(status='PASS',invoice_decision_required=True,invoice_qty_above_corrected_receipt_refused=True,every_invoice_line_required=True,
          refusals_without_effect=True)
    def shared_invoice():
        g=invoice.fixture(cur,today);k=invoice.fixture(cur,today);auth.actor(cur)
        shared=dict(invoice_number=g['tag']+'-SHARED',supplier_id=str(aa.prior.BASE_SUPPLIER),invoice_date=str(g['day']),received_at=aa.at(g['day']+timedelta(days=2),15).isoformat(),
          change_reason='Satu invoice supplier untuk dua penerimaan',lines=[dict(purchase_item_id=x['item'],qty_invoiced='2',unit_price='12.5',discount_amount='0') for x in (g,k)])
        d=cur.execute('select erp.save_material_supplier_invoice_draft_v2(%s::jsonb,%s,null)',(json.dumps(shared),uuid.uuid4())).fetchone()[0]
        cur.execute('select erp.post_material_supplier_invoice_v2(%s,%s,%s,%s)',(d['supplier_invoice_id'],uuid.uuid4(),d['row_version'],'Invoice gabungan dua penerimaan'));b.api.admin(cur)
        masters=bc.fixture(cur,today,purchase=False,zones=False);kp=k['receipt']['purchase_id']
        payment=bc.supplier_payment(cur,kp,'25',masters['cash'],today);bc.internal(cur,'post_supplier_payment',payment);b.api.admin(cur)
        state=lambda pid:cur.execute("select round(erp.material_purchase_payable_total(h.id),2),coalesce((select sum(amount) from erp.supplier_payments where purchase_id=h.id and status='POSTED'),0),h.payment_status from erp.material_purchase_headers h where h.id=%s",(pid,)).fetchone()
        k_before,k_facts=state(kp),facts(cur,kp)
        before,dated,chk=ledger(cur),by_date(cur),checks(cur);w=ws(cur,g['receipt']['purchase_id'])
        assert w['can_correct'] and w['blockers']==[] and len(w['invoices'])==1 and [x['purchase_id'] for x in w['invoices'][0]['other_receipts']]==[kp],w
        assert [l['purchase_item_id'] for l in w['invoices'][0]['lines']]==[g['item']],w['invoices']
        old=w['invoices'][0]
        out=fix(cur,dict(payload(w,reason='Harga g di invoice gabungan salah ketik; 11 per meter'),invoices=invoices(w,price='11')),w['purchase']['row_version'])
        assert cur.execute('select status from erp.material_supplier_invoices where id=%s',(old['invoice_id'],)).fetchone()[0]=='REVERSED'
        new=cur.execute('select replacement_invoice_id::text from cp7_receipt_fix.invoice_replays where previous_invoice_id=%s',(old['invoice_id'],)).fetchone()[0]
        lines=cur.execute('select v.status,v.invoice_date,i.purchase_id::text,l.qty_invoiced,l.unit_price from erp.material_supplier_invoices v join erp.material_supplier_invoice_lines l on l.invoice_id=v.id join erp.material_purchase_items i on i.id=l.purchase_item_id where v.id=%s order by l.unit_price',(new,)).fetchall()
        assert lines==[('POSTED',g['day'],out['purchase_id'],D(2),D(11)),('POSTED',g['day'],kp,D(2),D('12.5'))],lines
        moved=cur.execute('select s.amount,s.payment_date=o.payment_date,s.cash_account_id::text,s.status,r.kind,r.target_purchase_id::text from cp7_receipt_fix.payment_replays r join erp.supplier_payments s on s.id=r.replacement_payment_id join erp.supplier_payments o on o.id=r.previous_payment_id where r.previous_payment_id=%s',(payment,)).fetchall()
        assert moved==[(D(25),True,masters['cash'],'POSTED','SHARED_INVOICE_RECEIPT',kp)],moved
        assert cur.execute('select status from erp.supplier_payments where id=%s',(payment,)).fetchone()[0]=='REVERSED'
        assert state(kp)==k_before and k_before[2]=='PAID',(state(kp),k_before)
        # The other receipt keeps its source; only the Native price-finalized
        # time follows the re-posted invoice (the reversed one keeps its own).
        kf=facts(cur,kp)
        for x in (kf,k_facts):
            for i in x['items']:i.pop('price_finalized_at')
        assert kf==k_facts,{x:(k_facts[x],kf[x]) for x in kf if kf[x]!=k_facts[x]}
        assert cur.execute('select status from erp.material_purchase_headers where id=%s',(kp,)).fetchone()[0]=='POSTED'
        delta=ledger_delta(before,ledger(cur));assert delta=={'AP_SUPPLIER':D(3),'MATERIAL_INVENTORY':D(-3)},delta
        dd=dated_delta(dated,by_date(cur));assert dd=={g['day']:{'AP_SUPPLIER':D(3),'MATERIAL_INVENTORY':D(-3)}},dd
        same_checks(chk,checks(cur));reversal_dates(cur)
        # Then the other receipt corrects the same shared invoice (2 x 12.5 -> 2 x 13):
        # invoice numbers are unique per supplier, so it takes the next suffix.
        before,chk=ledger(cur),checks(cur);wk=ws(cur,kp);assert [x['purchase_id'] for x in wk['invoices'][0]['other_receipts']]==[out['purchase_id']],wk['invoices']
        outk=fix(cur,dict(payload(wk,reason='Harga k di invoice gabungan salah ketik; 13 per meter'),invoices=invoices(wk,price='13')),wk['purchase']['row_version'])
        numbers=cur.execute("select invoice_number,status from erp.material_supplier_invoices where invoice_number like %s order by invoice_number",(g['tag']+'-SHARED%',)).fetchall()
        assert numbers==[(g['tag']+'-SHARED','REVERSED'),(g['tag']+'-SHARED · R1','REVERSED'),(g['tag']+'-SHARED · R2','POSTED')],numbers
        lines=cur.execute("select i.purchase_id::text,l.qty_invoiced,l.unit_price from erp.material_supplier_invoices v join erp.material_supplier_invoice_lines l on l.invoice_id=v.id join erp.material_purchase_items i on i.id=l.purchase_item_id where v.invoice_number=%s order by l.unit_price",(g['tag']+'-SHARED · R2',)).fetchall()
        assert lines==[(out['purchase_id'],D(2),D(11)),(outk['purchase_id'],D(2),D(13))],lines
        assert state(outk['purchase_id'])==(D(26),D(25),'PARTIAL'),state(outk['purchase_id'])
        delta=ledger_delta(before,ledger(cur));assert delta=={'AP_SUPPLIER':D(-1),'MATERIAL_INVENTORY':D(1)},delta
        same_checks(chk,checks(cur));reversal_dates(cur)
        return dict(status='PASS',shared_invoice_two_receipts_corrected_whole=True,second_receipt_corrects_same_shared_invoice_next_number_R2=True,corrected_line_2x12_5_to_2x11=True,other_receipt_line_2x12_5_unchanged=True,
          new_invoice_same_date=True,other_receipt_payment_25_replayed_same_date_cash=True,other_receipt_still_paid=True,other_receipt_source_untouched=True,
          ap_and_inventory_minus_3_on_invoice_date=True,all_integrity_checks_unchanged=True)
    def closed_period():
        f=production(cur,today);aa.prior.set_open_period(cur,f['production_day'])
        closed=cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]
        assert closed==f['production_day'],closed
        seen={r[0] for r in cur.execute('select id from erp.journal_entries').fetchall()}
        before,dated,chk=ledger(cur),by_date(cur),checks(cur);w=ws(cur,f['purchase'])
        assert w['can_correct'],w['blockers']
        fix(cur,payload(w,line=lambda n,i:i['rolls'][0].update(qty='80')),w['purchase']['row_version'])
        assert raw(cur,f['material'])==(D(20),D(200)) and hpp(cur,f)==(D(900),D(15),0),(raw(cur,f['material']),hpp(cur,f))
        made=[(e,t) for i,e,t in cur.execute('select id,economic_date,transaction_date from erp.journal_entries').fetchall() if i not in seen]
        assert made and all(t>closed for e,t in made) and any(e<=closed for e,t in made),(closed,made)
        dd=dated_delta(dated,by_date(cur));assert dd=={f['day']:{'MATERIAL_INVENTORY':D(-200),'AP_SUPPLIER':D(200)}},dd
        same_checks(chk,checks(cur));reversal_dates(cur)
        return dict(status='PASS',period_closed_through_production_day=True,correction_accepted=True,economic_date_kept_in_closed_period=True,
          transaction_date_after_close=True,stock_20_hpp_900=True,effects_on_receipt_date_only=True,all_integrity_checks_unchanged=True)
    def repeated():
        f=production(cur,today);w=ws(cur,f['purchase'])
        fix(cur,payload(w,line=lambda n,i:i['rolls'][0].update(qty='80')),w['purchase']['row_version'])
        w=ws(cur,f['purchase']);fix(cur,payload(w,line=lambda n,i:i['rolls'][0].update(qty='90')),w['purchase']['row_version'])
        h=ws(cur,f['purchase']);assert [x['revision'] for x in h['history']]==['1','2'] and raw(cur,f['material'])==(D(30),D(300))
        rows=full_card(cur,f['material'],f['roll'],f['raw_location']);assert rows[-1]['qty_signed']=='90.000000' and rows[-1]['original_qty_signed']=='100.000000' and rows[-1]['correction_count']=='4' and rows[0]['running_qty']=='30.000000',rows
        return dict(status='PASS',two_revisions_100_80_90=True,latest_wins=True,one_card_row_with_four_audit_members=True)
    def replay():
        f=production(cur,today);w=ws(cur,f['purchase']);p=payload(w,line=lambda n,i:i['rolls'][0].update(qty='80'));key=uuid.uuid4()
        a=fix(cur,p,w['purchase']['row_version'],key);before=snapshot(cur)
        assert fix(cur,p,w['purchase']['row_version'],key)==a and snapshot(cur)==before
        changed=copy.deepcopy(p);changed['lines'][0]['rolls'][0]['qty']='70'
        refused(cur,lambda:fix(cur,changed,w['purchase']['row_version'],key),'CP7_RECEIPT_FIX_REQUEST_CHANGED')
        refused(cur,lambda:fix(cur,p,w['purchase']['row_version']),'CP7_RECEIPT_FIX_ACTIVE_POSTED_ONLY')
        return dict(status='PASS',same_uuid_same_outcome_no_second_effect=True,changed_intent_refused=True,superseded_source_refused=True)
    def review_changed():
        f=roll_receipt(cur,today);w=ws(cur,f['purchase']);transfer(cur,f,'4')
        refused(cur,lambda:fix(cur,payload(w,line=lambda n,i:i['rolls'][0].update(qty='40')),w['purchase']['row_version']),'CP7_RECEIPT_FIX_REVIEW_CHANGED')
        return dict(status='PASS',use_after_review_changes_token=True,refused_without_effect=True)
    def access():
        f=production(cur,today);w=ws(cur,f['purchase']);p=payload(w,line=lambda n,i:i['rolls'][0].update(qty='80'))
        subject,role=receipt.custom(cur,receipt.OPS+('warehouse.procurement.reverse','finance.ap.view'))
        auth.refused(cur,lambda:ws(cur,f['purchase'],subject),'CP7_RECEIPT_FIX_OWNER_ADMIN_REQUIRED')
        refused(cur,lambda:fix(cur,p,w['purchase']['row_version'],subject=subject),'CP7_RECEIPT_FIX_OWNER_ADMIN_REQUIRED')
        auth.actor(cur,None,'anon');cur.execute('savepoint rf_anon')
        try:cur.execute('select public.erp_cp7_correct_receipt_v1(%s,%s,%s)',(json.dumps(p),uuid.uuid4(),w['purchase']['row_version']));denied=False
        except psycopg.Error:denied=True
        cur.execute('rollback to savepoint rf_anon');b.api.admin(cur);assert denied
        # A second, deactivatable ADMIN (the last active OWNER is Native-protected).
        admin,_=invoice.admin_actor(cur);assert ws(cur,f['purchase'],admin)['review_token']==w['review_token']
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(admin,))
        refused(cur,lambda:fix(cur,p,w['purchase']['row_version'],subject=admin),'CP7_RECEIPT_FIX_ACCESS_DENIED')
        return dict(status='PASS',staff_with_permissions_refused_owner_admin_only=True,anonymous_denied=True,admin_admitted_then_deactivation_refused=True)
    def year_history(count=364):
        f=roll_receipt(cur,today,rolls=('1000',),day_offset=count+2)
        for n in range(count):transfer(cur,f,'1',at=aa.at(f['day']+timedelta(days=n+1),10).isoformat())
        before=full_card(cur,f['material'],f['roll'],f['location']);w=ws(cur,f['purchase'])
        fix(cur,payload(w,line=lambda n,i:i['rolls'][0].update(qty='990')),w['purchase']['row_version'])
        after=full_card(cur,f['material'],f['roll'],f['location'])
        assert len(before)==len(after)==count+1
        b_by={r['movement_id']:r for r in before}
        for r in after:
            if r['movement_type']=='PURCHASE':assert r['qty_signed']=='990.000000' and r['original_qty_signed']=='1000.000000';continue
            assert D(b_by[r['movement_id']]['running_qty'])-D(r['running_qty'])==10 and r['qty_signed']=='-1.000000',(r,b_by[r['movement_id']])
        for offset in (25,100,325):
            page=card(cur,f['material'],f['roll'],f['location'],offset,25)
            for r in page['page']['rows']:assert r['running_qty']==next(x for x in after if x['movement_id']==r['movement_id'])['running_qty']
        assert after[0]['running_qty']==str(D(990-count).quantize(D('0.000001')))
        return dict(status='PASS',receipt_a_year_ago_corrected_1000_to_990=True,later_transfers_checked=count,each_later_running_balance_minus_10=True,
          original_transfer_quantities_unchanged=True,complete_prefix_before_paging=True)
    def year_final_invoice(months=12):
        """A FINAL supplier-invoice price from a year ago: receipt and invoice 366 days back, the roll moved
        every month since, and the invoice price (12 -> 11) corrected today. Every effect stays on the invoice
        book date; the transfers' cost history is restated, and nothing new is dated today."""
        f=roll_receipt(cur,today,rolls=('1000',),final=False,day_offset=366)
        f['item']=ws(cur,f['purchase'])['lines'][0]['item_id']
        invoice.finalize(cur,f,p=invoice.payload(f,qty='1000',price='12'))
        for n in range(months):transfer(cur,f,'10',at=aa.at(f['day']+timedelta(days=30*n+5),10).isoformat())
        moved=lambda:[r[0] for r in cur.execute("select unit_cost_snapshot from erp.material_stock_movements where roll_id=%s and source_type='MATERIAL_TRANSFER' and reversal_of_id is null order by physical_at,id",(f['roll'],)).fetchall()]
        assert raw(cur,f['material'])==(D(1000),D(12000)) and set(moved())=={D(12)} and len(moved())==2*months,(raw(cur,f['material']),moved())
        before,dated,chk=ledger(cur),by_date(cur),checks(cur);w=ws(cur,f['purchase'])
        assert w['can_correct'] and w['lines'][0]['invoice_match_state']=='MATCHED' and len(w['invoices'])==1 and w['invoices'][0]['invoice_date']==str(f['day']),w
        old=w['invoices'][0]
        out=fix(cur,dict(payload(w,reason='Harga final di invoice supplier setahun lalu salah ketik; 11 per meter'),invoices=invoices(w,price='11')),w['purchase']['row_version'])
        assert raw(cur,f['material'])==(D(1000),D(11000)) and set(moved())=={D(11)},(raw(cur,f['material']),moved())
        delta=ledger_delta(before,ledger(cur));assert delta=={'AP_SUPPLIER':D(1000),'MATERIAL_INVENTORY':D(-1000)},delta
        dd=dated_delta(dated,by_date(cur));assert dd=={f['day']:{'AP_SUPPLIER':D(1000),'MATERIAL_INVENTORY':D(-1000)}},dd
        new=cur.execute('select v.status,v.invoice_date,l.qty_invoiced,l.unit_price from erp.material_supplier_invoices v join erp.material_supplier_invoice_lines l on l.invoice_id=v.id join erp.material_purchase_items i on i.id=l.purchase_item_id where i.purchase_id=%s',(out['purchase_id'],)).fetchone()
        assert (new[0],str(new[1]),new[2],new[3])==('POSTED',str(f['day']),D(1000),D(11)),new
        assert cur.execute('select status from erp.material_supplier_invoices where id=%s',(old['invoice_id'],)).fetchone()[0]=='REVERSED'
        assert cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s)',(out['purchase_id'],out['purchase_id'])).fetchone()==(D(11000),D(0))
        same_checks(chk,checks(cur));reversal_dates(cur)
        return dict(status='PASS',receipt_and_final_invoice_366_days_ago=str(f['day']),monthly_transfers=months,invoice_final_12_to_11=True,
          ap_12000_to_11000_on_invoice_date=True,transfer_costs_restated_12_to_11=True,nothing_dated_today=True,all_integrity_checks_unchanged=True)
    def draft_roll_use():
        """An unposted cutting group or transfer already binds a roll of the receipt: the correction waits until it is posted or cancelled."""
        f=e01.production(cur,today,cutting_draft_only=True);b.api.admin(cur)
        dest=str(uuid.uuid4());cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,%s,'RAW_MATERIAL_WAREHOUSE',true)",(dest,f['tag']+'-TO',f['tag']+' destination'))
        moved=dict(transfer_number=f['tag']+'-T0001',from_location_id=f['raw_location'],to_location_id=dest,physical_at=aa.at(f['day']+timedelta(days=1),7).isoformat(),
          change_reason='P09 ordinary warehouse transfer',items=[dict(material_id=f['material'],roll_id=f['roll'],qty='5')])
        t=material.command(cur,'SAVE_TRANSFER',moved);b.api.admin(cur)
        w=ws(cur,f['purchase']);block=[x for x in w['blockers'] if x['code']=='CP7_RECEIPT_FIX_DRAFT_ROLL_USE']
        assert not w['can_correct'] and len(block)==1 and sorted((d['type'],d['number']) for d in block[0]['documents'])==[('CUTTING_GROUP',f['group_number']),('MATERIAL_TRANSFER',f['tag']+'-T0001')],w['blockers']
        refused(cur,lambda:fix(cur,payload(w,line=lambda n,i:i['rolls'][0].update(qty='90')),w['purchase']['row_version']),'CP7_RECEIPT_FIX_DEPENDENCY')
        material.post(cur,t);b.api.admin(cur)
        version=cur.execute('select row_version from erp.cutting_groups where id=%s',(f['group'],)).fetchone()[0]
        e01.prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(f['cut_payload'],id=f['group'],action='POST'),expected_version=int(version));b.api.admin(cur)
        w=ws(cur,f['purchase']);assert w['can_correct'] and w['blockers']==[],w['blockers']
        out=fix(cur,payload(w,line=lambda n,i:i['rolls'][0].update(qty='90')),w['purchase']['row_version'])
        assert raw(cur,f['material'])[0]==D(30),raw(cur,f['material'])
        return dict(status='PASS',draft_cutting_and_transfer_named_as_blockers=True,correction_refused_while_draft=True,posted_drafts_then_corrected_100_to_90=True)
    def duplicate_lines():
        """Two lines of the same accessory with the same quantity and price, each with its own lot and notes."""
        f=uom.fixture(cur,today,qty='2',price='120');l=f['payload']['lines'][0]
        f['payload']['lines']=[dict(l,lot_number='LOT-A',notes='Baris A'),dict(l,lot_number='LOT-B',notes='Baris B')]
        r=receipt.post(cur,receipt.command(cur,'SAVE_DRAFT',f['payload']));w=ws(cur,r['purchase_id'])
        assert [(x['lot_number'],x['notes'],x['qty']) for x in sorted(w['lines'],key=lambda x:x['lot_number'])]==[('LOT-A','Baris A','24.000000'),('LOT-B','Baris B','24.000000')],w['lines']
        # Both lines stay identical in material, quantity and price; only line A states a new lot.
        a=next(n for n,x in enumerate(w['lines']) if x['lot_number']=='LOT-A')
        out=fix(cur,payload(w,line=lambda n,i:i.update(qty='20',**({'lot_number':'LOT-A2'} if n==a else {}))),w['purchase']['row_version'])
        rows=cur.execute('select lot_number,notes,qty from erp.material_purchase_items where purchase_id=%s order by lot_number',(out['purchase_id'],)).fetchall()
        assert rows==[('LOT-A2','Baris A',D(20)),('LOT-B','Baris B',D(20))],rows
        pairs=sorted(cur.execute("""select mi.notes,oi.notes,oi.lot_number from cp7_receipt_fix.ledger_links z
          join erp.material_stock_movements m on m.id=z.member_id join erp.material_purchase_items mi on mi.id=m.source_id
          join erp.material_stock_movements o on o.id=z.origin_id join erp.material_purchase_items oi on oi.id=o.source_id where mi.purchase_id=%s""",(out['purchase_id'],)).fetchall())
        assert pairs==[('Baris A','Baris A','LOT-A'),('Baris B','Baris B','LOT-B')],pairs
        return dict(status='PASS',two_identical_lines_keep_their_own_lot_and_notes=True,stated_lot_changes_only_its_line=True,card_links_follow_exact_line=True)
    def late_failure():
        f=production(cur,today);w=ws(cur,f['purchase']);p=payload(w,line=lambda n,i:i['rolls'][0].update(qty='80'))
        cur.execute("create function cp7_receipt_fix.rf_test_fail() returns trigger language plpgsql as $$begin raise exception 'RF_TEST_INJECTED_AFTER_STOCK_COST_JOURNAL';end$$")
        cur.execute('create trigger rf_test_fail before insert on cp7_receipt_fix.revisions for each row execute function cp7_receipt_fix.rf_test_fail()')
        try:refused(cur,lambda:fix(cur,p,w['purchase']['row_version']),'RF_TEST_INJECTED_AFTER_STOCK_COST_JOURNAL')
        finally:cur.execute('drop trigger rf_test_fail on cp7_receipt_fix.revisions;drop function cp7_receipt_fix.rf_test_fail()')
        assert raw(cur,f['material'])==(D(40),D(400)) and cur.execute('select status from erp.material_purchase_headers where id=%s',(f['purchase'],)).fetchone()[0]=='POSTED'
        return dict(status='PASS',failure_after_all_stock_cost_hpp_journal_payment_steps_rolls_back_everything=True)
    def accessory():
        f=uom.fixture(cur,today,qty='2',price='120');d=receipt.command(cur,'SAVE_DRAFT',f['payload']);r=receipt.post(cur,d)
        # 16 of the 24 pcs already left the receipt location (ordinary transfer).
        location=str(cur.execute('select location_id from erp.material_purchase_headers where id=%s',(r['purchase_id'],)).fetchone()[0]);destination=str(uuid.uuid4())
        cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,%s,'RAW_MATERIAL_WAREHOUSE',true)",(destination,f['tag']+'-TO',f['tag']+' destination'))
        moved=dict(transfer_number=f['tag']+'-T0001',from_location_id=location,to_location_id=destination,physical_at=aa.at(f['day']+timedelta(days=1),10).isoformat(),
          change_reason='P09 ordinary warehouse transfer',items=[dict(material_id=f['material'],roll_id=None,qty='16')])
        material.post(cur,material.command(cur,'SAVE_TRANSFER',moved))
        before=ledger(cur);chk=checks(cur);w=ws(cur,r['purchase_id']);assert w['lines'][0]['rolls']==[] and D(w['lines'][0]['qty'])==24 and w['lines'][0]['min_qty']=='16.000000',w['lines']
        refused(cur,lambda:fix(cur,payload(w,line=lambda n,i:i.update(qty='10')),w['purchase']['row_version']),'CP7_RECEIPT_FIX_LINE_BELOW_USE')
        out=fix(cur,payload(w,line=lambda n,i:i.update(qty='20')),w['purchase']['row_version'])
        assert raw(cur,f['material'])[0]==20 and cur.execute('select qty,unit_price from erp.material_purchase_items where purchase_id=%s',(out['purchase_id'],)).fetchone()==(D(20),D(10))
        delta=ledger_delta(before,ledger(cur));assert delta=={'MATERIAL_INVENTORY':D(-40),'GRNI_MATERIAL':D(40)},delta
        same_checks(chk,checks(cur))
        return dict(status='PASS',accessory_24_pcs_16_moved_out_corrected_10_refused=True,accessory_24_pcs_corrected_20=True,estimated_receipt_grni_follows=True,all_integrity_checks_unchanged=True)
    def roll_number_typo():
        """Roll numbers typed wrong on a posted receipt whose first roll is already used: swapped R1/R2 and a typo on R3."""
        f=roll_receipt(cur,today);transfer(cur,f,'4');t=f['tag']
        before,dated,chk=ledger(cur),by_date(cur),checks(cur);w=ws(cur,f['purchase'])
        assert [r['roll_number'] for r in w['lines'][0]['rolls']]==[t+'-R1',t+'-R2',t+'-R3'] and w['lines'][0]['rolls'][0]['used_qty']=='4.000000',w['lines']
        number=lambda k,v:(lambda n,i:i['rolls'][k].update(roll_number=v))
        refused(cur,lambda:fix(cur,payload(w,line=lambda n,i:(i['rolls'][1].update(roll_number=t+'-R9'),i['rolls'][2].update(roll_number=t+'-R9'))),w['purchase']['row_version']),'CP7_RECEIPT_FIX_ROLL_NUMBER_TAKEN')
        refused(cur,lambda:fix(cur,payload(w,line=lambda n,i:i['rolls'].append(dict(roll_number=t+'-R1',qty='5'))),w['purchase']['row_version']),'CP7_RECEIPT_FIX_ROLL_NUMBER_TAKEN')
        moved=cur.execute('select id,roll_id,qty_signed,physical_at from erp.material_stock_movements where roll_id=%s and source_type=%s order by id',(f['rolls'][0],'MATERIAL_TRANSFER')).fetchall()
        out=fix(cur,payload(w,reason='Nomor roll tertukar dan salah ketik; dicek dengan label fisik',
          line=lambda n,i:(i['rolls'][0].update(roll_number=t+'-R2'),i['rolls'][1].update(roll_number=t+'-R1'),i['rolls'][2].update(roll_number=t+'-R30'))),w['purchase']['row_version'])
        rolls=cur.execute('select r.id::text,r.roll_number,r.original_qty from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=%s order by r.id',(out['purchase_id'],)).fetchall()
        assert sorted(rolls)==sorted([(f['rolls'][0],t+'-R2',D(50)),(f['rolls'][1],t+'-R1',D(50)),(f['rolls'][2],t+'-R30',D(50))]),rolls
        assert cur.execute('select id,roll_id,qty_signed,physical_at from erp.material_stock_movements where roll_id=%s and source_type=%s order by id',(f['rolls'][0],'MATERIAL_TRANSFER')).fetchall()==moved
        lineage=cur.execute("select old_roll_id::text,previous_roll_number,roll_number from cp7_receipt_fix.roll_lineage where correction_id=%s and kind='REPARENTED' order by roll_number",(out['revision_id'],)).fetchall()
        assert sorted(lineage)==sorted([(f['rolls'][0],t+'-R1',t+'-R2'),(f['rolls'][1],t+'-R2',t+'-R1'),(f['rolls'][2],t+'-R3',t+'-R30')]),lineage
        h=ws(cur,f['purchase'])['history'][0]
        assert [r['roll_number'] for r in h['previous_document']['lines'][0]['rolls']]==[t+'-R1',t+'-R2',t+'-R3'],h
        assert sorted(r['roll_number'] for r in h['corrected_document']['lines'][0]['rolls'])==sorted([t+'-R1',t+'-R2',t+'-R30']),h
        assert raw(cur,f['material'])==(D(150),D(1500)),raw(cur,f['material'])
        assert ledger_delta(before,ledger(cur))=={} and dated_delta(dated,by_date(cur))=={},(ledger_delta(before,ledger(cur)),dated_delta(dated,by_date(cur)))
        same_checks(chk,checks(cur));reversal_dates(cur)
        return dict(status='PASS',used_roll_number_typo_fixed_same_roll=True,numbers_swapped_between_rolls=True,roll_ids_use_and_transfer_kept=True,
          duplicate_number_refused=True,new_roll_cannot_take_existing_number=True,lineage_previous_and_corrected_number=True,no_stock_or_ledger_effect=True,
          all_integrity_checks_unchanged=True)
    def header_typo():
        """The receipt (delivery-note) number typed wrong; later revisions keep the corrected number."""
        f=roll_receipt(cur,today,rolls=('100',));other=roll_receipt(cur,today,rolls=('10',))
        number=lambda pid:cur.execute('select purchase_number from erp.material_purchase_headers where id=%s',(pid,)).fetchone()[0]
        old,taken,fixed=number(f['purchase']),number(other['purchase']),f['tag']+'-SJ-BENAR'
        before,chk=ledger(cur),checks(cur);w=ws(cur,f['purchase'])
        refused(cur,lambda:fix(cur,dict(payload(w),purchase_number=taken),w['purchase']['row_version']),'CP7_RECEIPT_FIX_PURCHASE_NUMBER_TAKEN')
        out=fix(cur,dict(payload(w,reason='Nomor surat jalan salah ketik'),purchase_number=' '+fixed+' '),w['purchase']['row_version'])
        assert number(out['purchase_id']).startswith(fixed+' · R1-') and number(f['purchase'])==old,(number(out['purchase_id']),old)
        assert ledger_delta(before,ledger(cur))=={},ledger_delta(before,ledger(cur))
        w2=ws(cur,f['purchase']);out2=fix(cur,payload(w2,line=lambda n,i:i['rolls'][0].update(qty='90')),w2['purchase']['row_version'])
        assert number(out2['purchase_id']).startswith(fixed+' · R2-'),number(out2['purchase_id'])
        h=ws(cur,f['purchase'])['history']
        assert (h[0]['previous_document']['purchase_number'],h[0]['corrected_document']['purchase_number'][:len(fixed)])==(old,fixed),h[0]
        assert ledger_delta(before,ledger(cur))=={'MATERIAL_INVENTORY':D(-100),'AP_SUPPLIER':D(100)},ledger_delta(before,ledger(cur))
        same_checks(chk,checks(cur));reversal_dates(cur)
        return dict(status='PASS',delivery_note_number_typo_corrected=True,later_revision_keeps_corrected_number=True,
          number_of_another_receipt_refused=True,source_receipt_number_kept_in_history=True,no_ledger_effect_for_number_only=True,all_integrity_checks_unchanged=True)
    def invoice_header_typo():
        """A posted supplier invoice with the wrong number, date and due date."""
        f=invoice.fixture(cur,today);invoice.finalize(cur,f);other=invoice.fixture(cur,today);invoice.finalize(cur,other);b.api.admin(cur)
        pid=f['receipt']['purchase_id'];w=ws(cur,pid);v=w['invoices'][0]
        other_number=cur.execute('select v.invoice_number from erp.material_supplier_invoices v join erp.material_supplier_invoice_lines l on l.invoice_id=v.id join erp.material_purchase_items i on i.id=l.purchase_item_id where i.purchase_id=%s',(other['receipt']['purchase_id'],)).fetchone()[0]
        refused(cur,lambda:fix(cur,dict(payload(w),invoices=[dict(x,invoice_number=other_number) for x in invoices(w)]),w['purchase']['row_version']),'CP7_RECEIPT_FIX_INVOICE_NUMBER_TAKEN')
        before,dated,chk=ledger(cur),by_date(cur),checks(cur)
        day=datetime.fromisoformat(v['invoice_date']).date();new_day,due=day+timedelta(days=1),day+timedelta(days=30)
        inv=[dict(x,invoice_number=f['tag']+'-INV-BENAR',invoice_date=str(new_day),due_date=str(due)) for x in invoices(w)]
        fix(cur,dict(payload(w,reason='Nomor, tanggal dan jatuh tempo invoice supplier salah ketik'),invoices=inv),w['purchase']['row_version'])
        new=cur.execute('select v.invoice_number,v.invoice_date,v.due_date,v.status from cp7_receipt_fix.invoice_replays r join erp.material_supplier_invoices v on v.id=r.replacement_invoice_id where r.previous_invoice_id=%s',(v['invoice_id'],)).fetchone()
        assert new==(f['tag']+'-INV-BENAR · R1',new_day,due,'POSTED'),new
        assert cur.execute('select status from erp.material_supplier_invoices where id=%s',(v['invoice_id'],)).fetchone()[0]=='REVERSED'
        assert ledger_delta(before,ledger(cur))=={},ledger_delta(before,ledger(cur))
        # The same amounts move from the typed date to the corrected invoice date.
        dd=dated_delta(dated,by_date(cur))
        assert set(dd)=={day,new_day} and dd[day]=={k:-x for k,x in dd[new_day].items()} and dd[new_day],dd
        same_checks(chk,checks(cur));reversal_dates(cur)
        return dict(status='PASS',supplier_invoice_number_date_due_corrected=True,same_amounts_move_to_corrected_invoice_date=True,
          number_of_another_invoice_refused=True,old_invoice_reversed=True,all_integrity_checks_unchanged=True)
    def arrival_date():
        """The arrival time typed wrong: earlier and later, never after the first use of a roll."""
        f=roll_receipt(cur,today,rolls=('50','50'),day_offset=6);aa.prior.set_open_period(cur,f['day']-timedelta(days=5))
        transfer(cur,f,'4',at=aa.at(f['day']+timedelta(days=2),10).isoformat())
        before,dated,chk=ledger(cur),by_date(cur),checks(cur);w=ws(cur,f['purchase'])
        at=lambda d,h:aa.at(d,h).isoformat()
        refused(cur,lambda:fix(cur,dict(payload(w),physical_at=at(f['day']+timedelta(days=3),9)),w['purchase']['row_version']),'CP7_RECEIPT_FIX_DATE_AFTER_USE')
        refused(cur,lambda:fix(cur,dict(payload(w),physical_at=(datetime.now().astimezone()+timedelta(days=2)).isoformat()),w['purchase']['row_version']),'CP7_RECEIPT_FIX_DATE_FUTURE')
        early=f['day']-timedelta(days=1)
        out=fix(cur,dict(payload(w,reason='Tanggal datang salah ketik; dicek dengan surat jalan'),physical_at=at(early,9)),w['purchase']['row_version'])
        head=cur.execute('select physical_at,location_id::text,supplier_id from erp.material_purchase_headers where id=%s',(out['purchase_id'],)).fetchone()
        assert head[0]==aa.at(early,9) and head[1]==w['purchase']['location_id'],head
        assert cur.execute('select received_at from erp.material_rolls where id=%s',(f['roll'],)).fetchone()[0]==aa.at(early,9)
        assert ledger_delta(before,ledger(cur))=={},ledger_delta(before,ledger(cur))
        dd=dated_delta(dated,by_date(cur))
        assert dd=={f['day']:{'MATERIAL_INVENTORY':D(-1000),'AP_SUPPLIER':D(1000)},early:{'MATERIAL_INVENTORY':D(1000),'AP_SUPPLIER':D(-1000)}},dd
        rows=full_card(cur,f['material'],f['roll'],f['location'])
        assert rows[0]['running_qty']=='46.000000' and any(r['movement_type']=='PURCHASE' and r['qty_signed']=='50.000000' and datetime.fromisoformat(r['physical_at'])==aa.at(early,9) for r in rows),rows
        # Later again, still before the first use: allowed.
        w2=ws(cur,f['purchase']);later=f['day']+timedelta(days=1)
        fix(cur,dict(payload(w2,reason='Tanggal datang yang benar sehari sesudahnya'),physical_at=at(later,9)),w2['purchase']['row_version'])
        dd=dated_delta(dated,by_date(cur))
        assert dd=={f['day']:{'MATERIAL_INVENTORY':D(-1000),'AP_SUPPLIER':D(1000)},later:{'MATERIAL_INVENTORY':D(1000),'AP_SUPPLIER':D(-1000)}},dd
        same_checks(chk,checks(cur));reversal_dates(cur)
        return dict(status='PASS',arrival_moved_earlier_then_later=True,effects_move_to_corrected_date=True,roll_received_at_follows=True,
          card_row_at_corrected_time=True,date_after_first_use_refused=True,future_date_refused=True,all_integrity_checks_unchanged=True)
    def warehouse():
        """The receiving warehouse picked wrong, for rolls not yet used or moved."""
        f=roll_receipt(cur,today,rolls=('50','50'));before,chk=ledger(cur),checks(cur);w=ws(cur,f['purchase'])
        out=fix(cur,dict(payload(w,reason='Gudang penerimaan salah pilih'),location_id=f['destination']),w['purchase']['row_version'])
        assert cur.execute('select location_id::text from erp.material_purchase_headers where id=%s',(out['purchase_id'],)).fetchone()[0]==f['destination']
        on=lambda loc:cur.execute('select coalesce(sum(qty_signed),0) from erp.material_stock_movements where material_id=%s and location_id=%s',(f['material'],loc)).fetchone()[0]
        assert (on(f['location']),on(f['destination']))==(0,100),(on(f['location']),on(f['destination']))
        assert full_card(cur,f['material'],f['roll'],f['destination'])[0]['running_qty']=='50.000000'
        assert ledger_delta(before,ledger(cur))=={};same_checks(chk,checks(cur))
        g=roll_receipt(cur,today,rolls=('50',));transfer(cur,g,'4');wg=ws(cur,g['purchase'])
        refused(cur,lambda:fix(cur,dict(payload(wg),location_id=g['destination']),wg['purchase']['row_version']),'CP7_RECEIPT_FIX_LOCATION_USED')
        return dict(status='PASS',warehouse_corrected_stock_at_right_warehouse=True,old_warehouse_zero=True,card_at_right_warehouse=True,
          no_ledger_effect=True,used_roll_warehouse_change_refused=True)
    def supplier():
        """The supplier picked wrong: debt, payment and supplier invoice move to the right supplier."""
        right=str(cur.execute("insert into erp.suppliers(supplier_code,supplier_name,supplier_type) values(%s,'Supplier yang benar','MATERIAL') returning id",('RF-SUP-'+uuid.uuid4().hex[:8],)).fetchone()[0])
        f=roll_receipt(cur,today,rolls=('100',));masters=bc.fixture(cur,today,purchase=False,zones=False)
        payment=bc.supplier_payment(cur,f['purchase'],'300',masters['cash'],f['day']);bc.internal(cur,'post_supplier_payment',payment);b.api.admin(cur)
        before,chk=ledger(cur),checks(cur);w=ws(cur,f['purchase'])
        out=fix(cur,dict(payload(w,reason='Supplier salah pilih'),supplier_id=right),w['purchase']['row_version'])
        assert cur.execute('select supplier_id::text from erp.material_purchase_headers where id=%s',(out['purchase_id'],)).fetchone()[0]==right
        assert cur.execute('select supplier_id::text from erp.material_rolls where id=%s',(f['roll'],)).fetchone()[0]==right
        r=cur.execute('select s.purchase_id::text,s.amount,s.payment_date=o.payment_date,s.cash_account_id::text,s.status from cp7_receipt_fix.payment_replays x join erp.supplier_payments s on s.id=x.replacement_payment_id join erp.supplier_payments o on o.id=x.previous_payment_id where x.previous_payment_id=%s',(payment,)).fetchone()
        assert r==(out['purchase_id'],D(300),True,masters['cash'],'POSTED'),r
        owed=lambda sup:cur.execute("select coalesce(sum(round(erp.material_purchase_payable_total(h.id),2)-coalesce((select sum(amount) from erp.supplier_payments p where p.purchase_id=h.id and p.status='POSTED'),0)),0) from erp.material_purchase_headers h where h.supplier_id=%s and h.status='POSTED' and h.id in(%s,%s)",(sup,f['purchase'],out['purchase_id'])).fetchone()[0]
        assert owed(right)==700 and owed(w['purchase']['supplier_id'])==0,(owed(right),owed(w['purchase']['supplier_id']))
        assert ledger_delta(before,ledger(cur))=={};same_checks(chk,checks(cur));reversal_dates(cur)
        # A posted supplier invoice moves with the receipt to the right supplier.
        g=invoice.fixture(cur,today);invoice.finalize(cur,g);b.api.admin(cur);wg=ws(cur,g['receipt']['purchase_id']);old=wg['invoices'][0]['invoice_id']
        fix(cur,dict(payload(wg,reason='Supplier salah pilih'),supplier_id=right,invoices=invoices(wg)),wg['purchase']['row_version'])
        new=cur.execute('select v.supplier_id::text,v.status from cp7_receipt_fix.invoice_replays r join erp.material_supplier_invoices v on v.id=r.replacement_invoice_id where r.previous_invoice_id=%s',(old,)).fetchone()
        assert new==(right,'POSTED'),new
        # An invoice shared with another receipt of the old supplier stays with it.
        a=invoice.fixture(cur,today);k=invoice.fixture(cur,today);auth.actor(cur)
        shared=dict(invoice_number=a['tag']+'-SHARED',supplier_id=str(aa.prior.BASE_SUPPLIER),invoice_date=str(a['day']),received_at=aa.at(a['day']+timedelta(days=2),15).isoformat(),
          change_reason='Satu invoice supplier untuk dua penerimaan',lines=[dict(purchase_item_id=x['item'],qty_invoiced='2',unit_price='12.5',discount_amount='0') for x in (a,k)])
        d=cur.execute('select erp.save_material_supplier_invoice_draft_v2(%s::jsonb,%s,null)',(json.dumps(shared),uuid.uuid4())).fetchone()[0]
        cur.execute('select erp.post_material_supplier_invoice_v2(%s,%s,%s,%s)',(d['supplier_invoice_id'],uuid.uuid4(),d['row_version'],'Invoice gabungan dua penerimaan'));b.api.admin(cur)
        wa=ws(cur,a['receipt']['purchase_id'])
        refused(cur,lambda:fix(cur,dict(payload(wa),supplier_id=right,invoices=invoices(wa)),wa['purchase']['row_version']),'CP7_RECEIPT_FIX_SUPPLIER_SHARED_INVOICE')
        return dict(status='PASS',supplier_corrected_debt_moves=True,payment_300_replayed_same_date_cash=True,rolls_follow_supplier=True,
          supplier_invoice_moves_to_right_supplier=True,shared_invoice_supplier_change_refused=True,no_ledger_total_effect=True,all_integrity_checks_unchanged=True)
    def sku_typo():
        """The code (SKU) of the same material typed wrong; nothing else changes."""
        f=production(cur,today);other=clone(cur,'cp7-sku-b');before,chk=ledger(cur),checks(cur)
        IDENT='select material_name,material_type,unit_code,accessory_category_id,is_active,cached_stock_qty,moving_average_cost from erp.materials where id=%s'
        ident=cur.execute(IDENT,(f['material'],)).fetchone();card_before=full_card(cur,f['material'],f['roll'],f['raw_location'])
        w=name_ws(cur,f['material']);old=w['material_sku'];other_sku=cur.execute('select material_sku from erp.materials where id=%s',(other,)).fetchone()[0]
        p=dict(material_id=f['material'],material_name=w['material_name'],material_sku=old+'-B',change_reason='Kode bahan salah ketik di master')
        refused(cur,lambda:rename(cur,dict(p,material_sku=other_sku.lower()),w['row_version']),'CP7_MATERIAL_NAME_SKU_TAKEN')
        refused(cur,lambda:rename(cur,dict(p,material_sku=old),w['row_version']),'CP7_MATERIAL_NAME_UNCHANGED')
        out=rename(cur,p,w['row_version'])
        assert (out['previous_sku'],out['material_sku'],out['previous_name'],out['material_name'])==(old,old+'-B',w['material_name'],w['material_name']),out
        assert cur.execute(IDENT,(f['material'],)).fetchone()==ident and cur.execute('select material_sku from erp.materials where id=%s',(f['material'],)).fetchone()[0]==old+'-B'
        assert instants(full_card(cur,f['material'],f['roll'],f['raw_location']))==instants(card_before)
        assert ws(cur,f['purchase'])['lines'][0]['material_sku']==old+'-B' and hpp(cur,f)==(D(900),D(15),0)
        h=name_ws(cur,f['material']);assert [(x['previous_sku'],x['corrected_sku'],x['previous_name'],x['corrected_name']) for x in h['history']]==[(old,old+'-B',w['material_name'],w['material_name'])],h
        assert ledger_delta(before,ledger(cur))=={};same_checks(chk,checks(cur))
        return dict(status='PASS',same_material_code_fixed=True,code_of_another_material_refused=True,name_type_unit_stock_cost_unchanged=True,
          card_unchanged=True,receipt_shows_new_code=True,history_kept=True,no_journal=True)
    def name_typo():
        f=production(cur,today);before,chk=ledger(cur),checks(cur)
        IDENT='select material_sku,material_type,unit_code,accessory_category_id,is_active,cached_stock_qty,moving_average_cost from erp.materials where id=%s'
        ident=cur.execute(IDENT,(f['material'],)).fetchone()
        moves=cur.execute('select count(*),sum(qty_signed),sum(qty_signed*unit_cost_snapshot) from erp.material_stock_movements where material_id=%s',(f['material'],)).fetchone()
        card_before=full_card(cur,f['material'],f['roll'],f['raw_location'])
        w=name_ws(cur,f['material']);old=w['material_name'];new=old+' Combed'
        p=dict(material_id=f['material'],material_name='  '+old+'   Combed ',change_reason='Salah ketik nama bahan di master');key=uuid.uuid4()
        out=rename(cur,p,w['row_version'],key)
        assert (out['previous_name'],out['material_name'])==(old,new),out
        snap=snapshot(cur);assert rename(cur,p,w['row_version'],key)==out and snapshot(cur)==snap
        refused(cur,lambda:rename(cur,dict(p,material_name=old+' Combat'),w['row_version'],key),'CP7_MATERIAL_NAME_REQUEST_CHANGED')
        refused(cur,lambda:rename(cur,dict(p,material_name=old+' Combat'),w['row_version']),'CP7_MATERIAL_NAME_REVIEW_CHANGED')
        assert cur.execute(IDENT,(f['material'],)).fetchone()==ident
        assert cur.execute('select count(*),sum(qty_signed),sum(qty_signed*unit_cost_snapshot) from erp.material_stock_movements where material_id=%s',(f['material'],)).fetchone()==moves
        assert instants(full_card(cur,f['material'],f['roll'],f['raw_location']))==instants(card_before)
        assert ws(cur,f['purchase'])['lines'][0]['material_name']==new and hpp(cur,f)==(D(900),D(15),0)
        h=name_ws(cur,f['material']);assert h['material_name']==new and [(x['previous_name'],x['corrected_name']) for x in h['history']]==[(old,new)],h
        assert ledger_delta(before,ledger(cur))=={};same_checks(chk,checks(cur))
        return dict(status='PASS',same_material_renamed=True,sku_type_unit_category_stock_cost_unchanged=True,rolls_movements_card_unchanged=True,
          receipt_and_card_show_new_name=True,one_uuid_one_effect=True,changed_intent_and_stale_review_refused=True,history_kept=True,no_journal=True)
    def name_refusals():
        f=roll_receipt(cur,today);other=clone(cur,'cp7-name-b')
        other_name=cur.execute('select material_name from erp.materials where id=%s',(other,)).fetchone()[0]
        w=name_ws(cur,f['material']);p=dict(material_id=f['material'],material_name=w['material_name']+' Benar',change_reason='Salah ketik nama bahan')
        refused(cur,lambda:rename(cur,dict(p,material_name=other_name.upper()),w['row_version']),'CP7_MATERIAL_NAME_TAKEN')
        refused(cur,lambda:rename(cur,dict(p,material_name=w['material_name']),w['row_version']),'CP7_MATERIAL_NAME_UNCHANGED')
        refused(cur,lambda:rename(cur,dict(p,change_reason='typo'),w['row_version']),'CP7_MATERIAL_NAME_REASON_REQUIRED')
        refused(cur,lambda:rename(cur,dict(p,unit_code='KG'),w['row_version']),'CP7_MATERIAL_NAME_FIELDS')
        subject,role=receipt.custom(cur,receipt.OPS+('master.fabric.manage','warehouse.material.view'))
        auth.refused(cur,lambda:name_ws(cur,f['material'],subject),'CP7_MATERIAL_NAME_OWNER_ADMIN_REQUIRED')
        refused(cur,lambda:rename(cur,p,w['row_version'],subject=subject),'CP7_MATERIAL_NAME_OWNER_ADMIN_REQUIRED')
        auth.actor(cur,None,'anon');cur.execute('savepoint rf_anon')
        try:cur.execute('select public.erp_cp7_rename_material_v1(%s,%s,%s)',(json.dumps(p),uuid.uuid4(),w['row_version']));denied=False
        except psycopg.Error:denied=True
        cur.execute('rollback to savepoint rf_anon');b.api.admin(cur);assert denied
        admin,_=invoice.admin_actor(cur);assert name_ws(cur,f['material'],admin)['row_version']==w['row_version']
        cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(admin,))
        refused(cur,lambda:rename(cur,p,w['row_version'],subject=admin),'CP7_MATERIAL_NAME_ACCESS_DENIED')
        assert name_ws(cur,f['material'])['material_name']==w['material_name']
        return dict(status='PASS',name_of_another_material_refused_as_identity=True,unchanged_name_refused=True,reason_required=True,
          unit_or_other_identity_field_refused=True,staff_refused=True,anonymous_denied=True,deactivated_admin_refused=True,refusals_without_effect=True)
    tests=[('RF_QTY_DOWN_AFTER_CUTTING',qty_down),('RF_QTY_UP_AFTER_CUTTING',qty_up),('RF_PRICE_AFTER_SALE_AND_RETURN',price_after_sale),
      ('RF_WRONG_MATERIAL_AFTER_CUTTING',lambda:wrong_material()),('RF_WRONG_MATERIAL_AND_PRICE',lambda:wrong_material('12')),
      ('RF_ROLL_COUNT_TYPO_UNUSED_ROLL',roll_count),('RF_REMOVED_ROLL_USED_REFUSED',removed_used),('RF_ROLL_BELOW_USE_REFUSED',below_use),('RF_ROLL_NUMBER_TYPO_USED_ROLL',roll_number_typo),('RF_HEADER_TYPO',header_typo),('RF_INVOICE_HEADER_TYPO',invoice_header_typo),('RF_ARRIVAL_DATE_TYPO',arrival_date),('RF_WAREHOUSE_TYPO',warehouse),('RF_SUPPLIER_TYPO',supplier),
      ('RF_PAYMENT_REPLAY',lambda:paid('300',True)),('RF_PAID_EXCEEDS_CORRECTED_REFUSED',lambda:paid('1000',False)),('RF_OVERPAID_CREDIT_TO_NEXT_NOTA',overpaid_credit),('RF_OPENING_ADVANCE_PAYMENT_REPLAY',opening_advance),
      ('RF_INVOICE_PRICE_AFTER_SALE',invoice_price_after_sale),('RF_INVOICED_QTY_DOWN_WITH_PAYMENT',invoiced_qty_down),
      ('RF_INVOICE_INCOMPLETE_REFUSED',invoice_refusals),('RF_SHARED_INVOICE_CORRECTED',shared_invoice),('RF_CLOSED_PERIOD_CORRECTION',closed_period),('RF_REPEATED_REVISIONS',repeated),('RF_REPLAY_SAME_REQUEST',replay),
      ('RF_REVIEW_CHANGED_REFUSED',review_changed),('RF_ACCESS_CURRENT_AUTHORITY',access),('RF_YEAR_HISTORY_364',year_history),('RF_YEAR_FINAL_INVOICE_PRICE',year_final_invoice),
      ('RF_DRAFT_ROLL_USE_BLOCKS',draft_roll_use),('RF_CREDIT_RESTORED_UNBLOCKS',credit_restored),('RF_DUPLICATE_LINES_KEEP_LOT',duplicate_lines),
      ('RF_LATE_FAILURE_ATOMIC',late_failure),('RF_ACCESSORY_LINE_QTY',accessory),('RF_MATERIAL_NAME_TYPO',name_typo),('RF_MATERIAL_SKU_TYPO',sku_typo),('RF_MATERIAL_NAME_REFUSALS',name_refusals)]
    assert [n for n,_ in tests]==MANIFEST['groups']['native']
    return tests

def races(tools,today):
    def compete(same_uuid=False,use=False):
        with tools.connect() as conn,conn.cursor() as cur:
            f=roll_receipt(cur,today,rolls=('100',));w=ws(cur,f['purchase']);p=payload(w,line=lambda n,i:i['rolls'][0].update(qty='80'))
            q=payload(w,line=lambda n,i:i['rolls'][0].update(qty='90'));conn.commit()
        barrier=threading.Barrier(2);key=uuid.uuid4()
        def send(n):
            with tools.connect() as conn,conn.cursor() as cur:
                barrier.wait()
                try:
                    if use and n==1:result=dict(action='TRANSFER',out=transfer(cur,f,'95'))
                    else:result=fix(cur,p if (n==0 or same_uuid) else q,w['purchase']['row_version'],key if same_uuid else uuid.uuid4())
                    conn.commit();return result
                except psycopg.Error as error:conn.rollback();return str(error).splitlines()[0]
        with ThreadPoolExecutor(max_workers=2) as pool:jobs=[pool.submit(send,n) for n in (0,1)];results=[j.result(90) for j in jobs]
        good=[r for r in results if isinstance(r,dict)];assert len(good)==(2 if same_uuid else 1),results
        with tools.connect() as conn,conn.cursor() as cur:
            revs=cur.execute('select count(*) from cp7_receipt_fix.revisions where root_purchase_id=%s',(f['purchase'],)).fetchone()[0]
            stock=raw(cur,f['material'])[0]
            if use:
                assert (revs,stock) in ((1,D(80)),(0,D(100))),(revs,stock,results)
                assert cur.execute('select min(cached_qty) from erp.material_rolls where id=%s',(f['roll'],)).fetchone()[0]>=0
            else:
                assert revs==1 and stock in (D(80),D(90)),(revs,stock)
                if same_uuid:assert good[0]==good[1]
        return dict(status='PASS',real_concurrent_transactions=True,same_uuid=same_uuid,correction_versus_physical_use=use,one_economic_effect=True,no_negative_roll=True,results=[r if isinstance(r,str) else r.get('action') for r in results])
    tests=[('RF_RACE_TWO_REQUESTS',lambda:compete()),('RF_RACE_SAME_UUID',lambda:compete(True)),('RF_RACE_CUTTING_USE',lambda:compete(use=True))]
    assert [n for n,_ in tests]==MANIFEST['groups']['races']
    return tests

def http_cases(http,today):
    def correction():
        owner=http.login('OWNER','receipt-correction-owner')
        with http.connect() as conn,conn.cursor() as cur:
            f=roll_receipt(cur,today,rolls=('100',));w=ws(cur,f['purchase']);p=payload(w,line=lambda n,i:i['rolls'][0].update(qty='80'));conn.commit()
        args=dict(p_payload=p,p_request=str(uuid.uuid4()),p_expected=w['purchase']['row_version'])
        assert http.anon_rpc('erp_cp7_correct_receipt_v1',args)['status'] in (401,403)
        out=owner.rpc('erp_cp7_correct_receipt_v1',args);assert out['status']==200,out
        assert owner.rpc('erp_cp7_correct_receipt_v1',args)['body']==out['body']
        h=owner.rpc('erp_cp7_get_receipt_correction_v1',dict(p_purchase=f['purchase']));assert h['status']==200 and h['body']['current_purchase_id']==out['body']['purchase_id'],h
        c=owner.rpc('erp_cp7_get_material_ledger_v2',dict(p_material=f['material'],p_roll=f['roll'],p_location=f['location'],p_offset=0,p_limit=25))
        assert c['status']==200 and c['body']['page']['rows'][0]['qty_signed']=='80.000000' and c['body']['page']['rows'][0]['original_qty_signed']=='100.000000',c
        with http.connect() as conn,conn.cursor() as cur:
            assert raw(cur,f['material'])[0]==80;cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(owner.auth_user_id,));conn.commit()
        assert owner.rpc('erp_cp7_correct_receipt_v1',args)['status']==403 and owner.rpc('erp_cp7_get_receipt_correction_v1',dict(p_purchase=f['purchase']))['status']==403
        return dict(status='PASS',real_Auth_PostgREST_receipt_correction=True,one_uuid_one_effect=True,effective_card_row_visible=True,current_deactivation_hides_cached_outcome=True)
    tests=[('RF_HTTP_COMMAND_REPLAY_AUTH',correction)]
    assert [n for n,_ in tests]==MANIFEST['groups']['http']
    return tests
