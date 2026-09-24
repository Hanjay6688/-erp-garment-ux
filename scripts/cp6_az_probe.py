"""AZ T1_FAMILY probe: material recost corrections dated from the physical movement (owner, 24 Sep 2026).

Owner decision (quoted): "WIP: setujui prinsip max(tanggal ekonomi invoice, tanggal fisik potong) saat tanggal ekonomi
masih terbuka. WIP belum ada pada 1-2 Sep, jadi koreksi -Rp10 tidak boleh membuat saldo WIP negatif di dua hari itu.
Claude perlu membuktikan dulu kasusnya di database uji, lalu menguji alokasi nilai bahan sebelum dipotong, beberapa
tanggal potong, serta aturan jurnal bila periode sudah tertutup. Menggeser tanggal WIP saja belum cukup bila saldo bahan
menjadi salah." Also (AS approval): "Kalau kelak tanggal jual berbeda dari tanggal barang jadi, bagian HPP mengikuti
tanggal jual."

Label T1_FAMILY: targeted family evidence on the disposable chain AN -> AU -> AV -> AW -> AX -> AY (+ AZ in phase
'after'), never release evidence. Fixture: the AA estimated receipt (10 units at 10 on day d = today-3, 23:30) reused
unchanged; cutting groups are posted with the ordinary cutting RPC on the days each case names; a late supplier invoice
for all 10 units arrives with invoice date E (d unless the case says otherwise). Every case reads the daily ledger
(transaction date) before the fixture and after the invoice and checks, per day from d to today:
  - MATERIAL_INVENTORY carries the corrected value of the units still in stock that day (units x invoice price);
  - WIP of each fixture PO is never negative and receives the correction only from its cutting day;
  - the MATERIAL_COST_REVALUATION events and journals are dated on the cutting day (open E) or keep economic date E and
    are posted on the recognition day (closed E), as before AZ;
  - the supplier invoice journal stays on E.
Phase 'before' (without AZ) must show the finding: the correction of a later cut dated on E, the fixture PO's WIP
negative on E for a lower price, MATERIAL_INVENTORY at E not equal to the stock at the invoice price.
"""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,traceback,uuid
import psycopg

AUDITOR=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path.cwd()/'scripts'))
sys.path.append(str(AUDITOR/'scripts'))
import cp6_aw_probe as awp
import cp6_ax_probe as axp
import cp6_ay_probe as ayp
r1,api,boundary,prior,chain=awp.r1,awp.api,awp.boundary,awp.prior,awp.chain

OUT=AUDITOR/'cp6-proof/az'
AZ_SQL=AUDITOR/'supabase/dev/cp6_az_t1_family.sql'
LABEL='T1_FAMILY'
KEYS=('MATERIAL_INVENTORY','WIP','FG_INVENTORY','COGS')
FUNCTIONS=('erp.sync_material_cost_revaluation(uuid)','erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)','erp.sync_finished_po_wip_residual(uuid,date,text)',
           # AZ rev2 (round six): the rest of the family (handoff §23.7, independent review of AY rev7).
           'erp.guard_pocket_period_v1()','erp.sync_initial_import_bs_value_v1(uuid,date)',
           'erp.sync_non_po_product_hpp_to_gl_v2620f(uuid,date,text,uuid,text)','erp.refresh_accessory_hpp_after_material_recost(uuid,text)',
           'erp.reverse_qc(uuid,text)','erp.reverse_rework_completion(uuid,text)','erp.complete_initial_import_wip_v1(jsonb)',
           'erp.post_material_supplier_invoice(uuid)','erp.post_material_purchase_cost_correction(uuid)')


def dev_source(signature):
    """The body of one AZ function exactly as the committed dev file defines it."""
    import re
    name=signature.split('(')[0]
    text=AZ_SQL.read_text()
    head=re.search(r'(?i)create or replace function '+re.escape(name)+r'\(',text).start()
    start=re.compile(r'(?i)\bas \$function\$').search(text,head).end();end=text.index('$function$;',start)
    return text[start:end]


def az_installed(cur):
    return cur.execute("select count(*) from erp.schema_migrations where version='v2.6.20az'").fetchone()[0]==1


def az_verified(cur):
    base=ayp.ay_verified(cur)
    assert az_installed(cur),'AZ_T1_MARKER'
    for signature in FUNCTIONS:
        src=cur.execute('select prosrc from pg_proc where oid=%s::regprocedure',(signature,)).fetchone()[0]
        assert src==dev_source(signature),('AZ_T1_FUNCTION_NOT_CURRENT',signature)
    return dict(base,stage='AV_PLUS_AW_AX_AY_AZ_T1',az_sql_sha256=hashlib.sha256(AZ_SQL.read_bytes()).hexdigest())


def install_az():
    with psycopg.connect(boundary.PG,autocommit=True) as conn,conn.cursor() as cur:cur.execute(AZ_SQL.read_text(),prepare=False)
    with psycopg.connect(boundary.ADMIN) as conn,conn.cursor() as cur:
        result=az_verified(cur);conn.rollback()
    return result


def dec(v):return Decimal(str(v))


def ledger_days(cur,days,pos):
    """Closing balance per day (transaction date) of the four inventory/cost accounts, and WIP of each fixture PO."""
    api.admin(cur)
    rows=cur.execute("""select j.transaction_date,a.mapping_key,l.po_id,sum(l.debit-l.credit)
      from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id and j.status in('POSTED','REVERSED')
      join erp.accounting_account_mappings a on a.account_id=l.account_id
      where a.mapping_key=any(%s) group by 1,2,3""",(list(KEYS),)).fetchall()
    out={}
    for day in days:
        v={k:Decimal(0) for k in KEYS};po={str(p):Decimal(0) for p in pos}
        for tdate,key,p,amount in rows:
            if tdate<=day:
                v[key]+=dec(amount)
                if key=='WIP' and p is not None and str(p) in po:po[str(p)]+=dec(amount)
        out[str(day)]=dict({k:str(x) for k,x in v.items()},WIP_PO={k:str(x) for k,x in po.items()})
    return out


def cut(cur,fx,day,qty,hour=8):
    """One cutting group of `qty` units of the fixture roll for a new PO on `day` (ordinary cutting RPC; the reported
    remaining of the issued quantity is 0, the RPC requires issued = consumed + remaining)."""
    prod=chain.production
    api.admin(cur)
    po=uuid.uuid4()
    cur.execute("""insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)
      values(%s,%s,%s,%s,'CUTTING','CUTTING',%s,'AZ probe cutting day')""",(po,'AZ-PO-'+str(po),prod.MODEL,qty,prod.at(day,7)))
    payload=dict(action='SAVE_DRAFT',po_id=po,pattern_id=prod.PATTERN,source_location_id=fx['location'],cut_at=prod.at(day,hour),
                 change_reason='AZ probe cutting of %s units'%qty,size_slots=[dict(slot_no=1,size_id=prod.base.SIZE,drawing_no=1)],
                 rolls=[dict(roll_id=fx['roll'],qty_issued=qty,qty_consumed=qty,qty_reported_remaining=0,yields=[dict(slot_no=1,qty_pcs=qty)])])
    draft=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',payload)
    group=uuid.UUID(draft['cutting_group_id'])
    prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(payload,id=group,action='POST'),expected_version=int(draft['row_version']))
    api.admin(cur)
    return po


def adjust(cur,fx,day,qty):
    """A posted material adjustment (count correction) of -qty units of the fixture roll on `day` (as AS adjustment_date)."""
    api.admin(cur)
    adjustment=cur.execute("""insert into erp.material_adjustments(adjustment_number,physical_at,location_id,reason_code,notes,status)
        values(%s,%s,%s,'COUNT_CORRECTION','AZ probe adjustment day','DRAFT') returning id""",
        ('AZ-'+uuid.uuid4().hex,chain.production.at(day,12),fx['location'])).fetchone()[0]
    cur.execute('insert into erp.material_adjustment_items(adjustment_id,material_id,roll_id,qty_signed) values(%s,%s,%s,%s)',(adjustment,fx['material'],fx['roll'],-qty))
    version=cur.execute('select row_version from erp.material_adjustments where id=%s',(adjustment,)).fetchone()[0]
    api.ordinary(cur);cur.execute('select erp.post_material_adjustment_v2(%s,%s,%s,%s)',(adjustment,uuid.uuid4(),version,'AZ probe count correction'))
    api.admin(cur)
    return adjustment


def invoice(cur,fx,today,price,invoice_date,zone='Asia/Jakarta'):
    prod=chain.production
    api.admin(cur)
    version=int(cur.execute('select row_version from erp.material_purchase_headers where id=%s',(fx['purchase'],)).fetchone()[0])
    payload=dict(purchase_id=fx['purchase'],supplier_invoice_number='AZ-'+uuid.uuid4().hex[:12],invoice_date=invoice_date,
                 received_at=prod.at(today-timedelta(days=1),15),reason='AZ late supplier invoice at '+price,
                 lines=[dict(purchase_item_id=fx['item'],qty_invoiced=10,final_unit_price=price)])
    prod.zone(cur,zone)
    response=prod.rpc(cur,'erp.finalize_material_purchase_invoice_v2',payload,uuid.uuid4(),version)
    api.admin(cur)
    prod.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');api.admin(cur)
    return response


def material_case(cur,today,price,cuts,closed=None,invoice_offset=0,adjustments=(),zone='Asia/Jakarta'):
    """cuts: [(day offset from d, units)], adjustments: [(day offset, units)]; closed: None or a day offset closed before
    the invoice; invoice_offset: E = d + offset."""
    prod=chain.production
    d=today-timedelta(days=3);E=d+timedelta(days=invoice_offset)
    days=[d+timedelta(days=i) for i in range(4)]
    boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    quiet=awp.quiet_seed(cur,d,today-timedelta(days=1),exclude=[prod.CONTRACTOR])
    fx=prod.estimated_receipt(cur,today)
    assert fx['purchase_day']==d,('AZ_PURCHASE_DAY',fx['purchase_day'],d)
    left=10;pos=[];adjs=[]
    events=[(o,'CUT',q) for o,q in cuts]+[(o,'ADJ',q) for o,q in adjustments]
    for offset,kind,qty in sorted(events):
        left-=qty
        if kind=='CUT':pos.append(cut(cur,fx,d+timedelta(days=offset),qty))
        else:adjs.append(adjust(cur,fx,d+timedelta(days=offset),qty))
    # The seed contractor was left out of the first quieting (as in the AY probe); clear it now over the fixture window.
    quiet_fixture=awp.quiet_seed(cur,d,today-timedelta(days=1))
    closed_through=d+timedelta(days=closed) if closed is not None else None
    closed_before=None
    if closed is not None:
        ready=awp.preflight(cur,closed_through)
        if ready is None or ready['status']!='READY':
            return dict(status='INCOMPLETE',reason='fixture not READY before the close',blockers=awp.blockers_brief(ready))
        closed_before=awp.close(cur,closed_through,'AZ close before the late invoice')
        if closed_before[0]!='ACCEPTED':return dict(status='INCOMPLETE',reason='fixture close refused',closed_before=closed_before)
    before=ledger_days(cur,days,pos)
    api.admin(cur)
    old_events={r[0] for r in cur.execute('select id from erp.material_cost_revaluation_events where material_id=%s',(fx['material'],)).fetchall()}
    old_journals={r[0] for r in cur.execute('select id from erp.journal_entries').fetchall()}
    response=invoice(cur,fx,today,price,E,zone)
    after=ledger_days(cur,days,pos)
    new_events=[(str(r[0]),r[1],dec(r[2]),r[3],str(r[4]) if r[4] else None,r[5],r[6]) for r in cur.execute(
        """select e.id,e.effective_date,e.delta_amount,e.counterpart_mapping_key,e.po_id,j.economic_date,j.transaction_date
           from erp.material_cost_revaluation_events e join erp.journal_entries j on j.id=e.journal_entry_id
           where e.material_id=%s order by j.transaction_date,e.id""",(fx['material'],)).fetchall() if r[0] not in old_events]
    new_adj_journals=[str(r[0]) for r in cur.execute(
        "select id from erp.journal_entries where source_type='MATERIAL_ADJUSTMENT_REVALUATION'").fetchall() if r[0] not in old_journals]
    adj_facts=[(str(r[0]),r[1],r[2],r[3]) for r in cur.execute(
        """select f.adjustment_id,f.effective_date,j.economic_date,j.transaction_date from erp.material_adjustment_revaluation_facts f
           join erp.journal_entries j on j.id=f.journal_entry_id where f.adjustment_id=any(%s::uuid[]) and f.journal_entry_id=any(%s::uuid[])
           order by f.created_at""",([str(a) for a in adjs],new_adj_journals)).fetchall()]
    invoice_journals=[(r[0],r[1]) for r in cur.execute(
        "select economic_date,transaction_date from erp.journal_entries where source_type='MATERIAL_SUPPLIER_INVOICE' and id<>all(%s::uuid[])",
        ([str(j) for j in old_journals],)).fetchall()]
    x=dec(price)-10
    # Expected, per day: units in stock, units cut into each PO.
    stock={str(day):10-sum(q for o,q in cuts+list(adjustments) if d+timedelta(days=o)<=day) for day in days}
    move={str(day):{k:dec(after[str(day)][k])-dec(before[str(day)][k]) for k in KEYS} for day in days}
    wip_po={str(day):{p:dec(v) for p,v in after[str(day)]['WIP_PO'].items()} for day in days}
    recognition=today if closed is not None else None
    checks=dict(
        revaluation_events_created=bool(new_events),
        revaluation_event_totals=sum(e[2] for e in new_events)==-x*sum(q for _,q in cuts),
        supplier_invoice_on_invoice_date=bool(invoice_journals) and all(ec==E and tr==(recognition if closed is not None and E<=closed_through else E) for ec,tr in invoice_journals))
    if closed is not None and E<=closed_through:
        # As before AZ: economic date E, posted on the recognition day; no day before today moves.
        checks.update(revaluation_on_E_posted_today=all(e[5]==E and e[6]==today and e[1]==today for e in new_events),
                      history_before_today_unchanged=all(move[str(day)]==dict.fromkeys(KEYS,Decimal(0)) for day in days if day<today))
    else:
        cut_days={str(p):d+timedelta(days=o) for p,(o,q) in zip(pos,sorted(cuts))}
        checks.update(
            revaluation_on_cutting_day=all(e[5]==e[6]==e[1]==max(E,cut_days.get(e[4],E)) for e in new_events if e[3]=='WIP'),
            material_before_cut_at_invoice_price=all(move[str(day)]['MATERIAL_INVENTORY']==x*stock[str(day)] for day in days if day>=E),
            wip_po_never_negative=all(v>=0 for day in days for v in wip_po[str(day)].values()),
            wip_po_zero_before_its_cut=all(wip_po[str(day)][p]==0 for p,cd in cut_days.items() for day in days if day<cd))
    if adjustments:
        adj_days=[d+timedelta(days=o) for o,_ in adjustments]
        if closed is not None and E<=closed_through:
            checks['adjustment_revaluation_on_E_posted_today']=bool(adj_facts) and all(f[2]==E and f[3]==today for f in adj_facts)
        else:
            checks['adjustment_revaluation_on_adjustment_day']=bool(adj_facts) and all(f[1]==f[2]==f[3]==max(E,adj_days[0]) for f in adj_facts)
    pre=awp.preflight(cur,today)
    negative=[b for b in pre['blockers'] if b['code']=='GL_INVENTORY_NEGATIVE_ASOF'] if pre else None
    checks['no_negative_daily_inventory']=negative==[]
    ok=all(checks.values())
    status='PASS' if ok else ('COUNTEREXAMPLE' if not az_installed(cur) else 'FAIL')
    return dict(status=status,price=price,receipt_day=str(d),invoice_date=str(E),cuts=[(str(d+timedelta(days=o)),q) for o,q in cuts],
                adjustments=[(str(d+timedelta(days=o)),q) for o,q in adjustments],closed_through=str(closed_through) if closed_through else None,
                checks=checks,new_revaluation_events=[[str(v) for v in e] for e in new_events],adjustment_facts=[[str(v) for v in f] for f in adj_facts],
                invoice_journals=[[str(v) for v in j] for j in invoice_journals],stock_units=stock,
                daily_move={k:{kk:str(vv) for kk,vv in v.items()} for k,v in move.items()},wip_po={k:{kk:str(vv) for kk,vv in v.items()} for k,v in wip_po.items()},
                negative_blockers=negative,closed_before=closed_before,invoice=response,quiet=[quiet,quiet_fixture])


def sale_after_goods(cur,today,price):
    """AY rule the owner restated: the sold part follows the sale date. AA production (5 FG on d+1, 2 sold on d+1) plus
    one more piece sold on d+2; the COGS change of that piece must be on d+2, FG never negative, WIP of the PO never
    negative (the cut is on d+1)."""
    prod=chain.production
    d=today-timedelta(days=3);d2=d+timedelta(days=1);d3=d+timedelta(days=2)
    days=[d+timedelta(days=i) for i in range(4)]
    boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    quiet=awp.quiet_seed(cur,d,today-timedelta(days=1),exclude=[prod.CONTRACTOR])
    fx=prod.estimated_receipt(cur,today)
    prod.partial_production(awp.OrdinaryDraftCursor(cur),fx);api.admin(cur)
    customer=prod.base.create_customer(cur,uuid.uuid4().hex[:16])
    sale=prod.rpc(cur,'erp.save_sale_draft_v2',{'sale_number':'AZ-SALE-'+str(uuid.uuid4()),'customer_id':customer,
        'source_location_id':prod.base.LOCATION,'sale_date':prod.at(d3,14),'reason':'AZ one more piece sold a day later',
        'items':[dict(product_id=fx['product'],qty_pcs=1,unit_price_snapshot=40,discount_amount=0)]})
    cur.execute('select erp.post_sale_v2(%s,%s,%s)',(sale['sale_id'],uuid.uuid4(),int(sale['row_version'])))
    api.admin(cur)
    quiet_fixture=awp.quiet_seed(cur,d,today-timedelta(days=1))
    before=ledger_days(cur,days,[fx['po']])
    old={r[0] for r in cur.execute('select id from erp.po_hpp_gl_events where po_id=%s',(fx['po'],)).fetchall()}
    response=invoice(cur,fx,today,price,d)
    after=ledger_days(cur,days,[fx['po']])
    new=[(str(r[0]),r[1],dec(r[2]),dec(r[3])) for r in cur.execute(
        'select id,effective_date,fg_delta,cogs_delta from erp.po_hpp_gl_events where po_id=%s order by effective_date,id',(fx['po'],)).fetchall() if r[0] not in old]
    x=dec(price)-10
    move={str(day):{k:dec(after[str(day)][k])-dec(before[str(day)][k]) for k in KEYS} for day in days}
    wip_po={str(day):dec(after[str(day)]['WIP_PO'][str(fx['po'])]) for day in days}
    by_day={}
    for e in new:by_day.setdefault(str(e[1]),[Decimal(0),Decimal(0)]);by_day[str(e[1])][0]+=e[2];by_day[str(e[1])][1]+=e[3]
    pre=awp.preflight(cur,today)
    negative=[b for b in pre['blockers'] if b['code']=='GL_INVENTORY_NEGATIVE_ASOF'] if pre else None
    checks=dict(hpp_events_on_goods_and_sale_days=set(by_day)=={str(d2),str(d3)},
                cogs_of_later_sale_on_its_day=by_day.get(str(d3),[None,None])[1]==x and by_day.get(str(d3),[None,None])[0]==-x,
                cogs_of_first_sale_on_goods_day=by_day.get(str(d2),[None,None])[1]==2*x,
                fg_day_moves=move[str(d2)]['FG_INVENTORY']==3*x and move[str(d3)]['FG_INVENTORY']==2*x,
                receipt_day_fg_cogs_unchanged=move[str(d)]['FG_INVENTORY']==0 and move[str(d)]['COGS']==0,
                wip_po_never_negative=all(v>=0 for v in wip_po.values()),wip_po_zero_before_cut=wip_po[str(d)]==0,
                no_negative_daily_inventory=negative==[])
    status='PASS' if all(checks.values()) else ('COUNTEREXAMPLE' if not az_installed(cur) else 'FAIL')
    return dict(status=status,price=price,receipt_day=str(d),goods_day=str(d2),later_sale_day=str(d3),checks=checks,
                hpp_events=[[str(v) for v in e] for e in new],hpp_by_day={k:[str(v) for v in vs] for k,vs in by_day.items()},
                daily_move={k:{kk:str(vv) for kk,vv in v.items()} for k,v in move.items()},wip_po={k:str(v) for k,v in wip_po.items()},
                negative_blockers=negative,invoice=response,quiet=[quiet,quiet_fixture])


PRODUCED={}


def cut_only(cur,fx,po,day,units,pcs,batch=None):
    """One posted cutting group (material issued, not picked up) of `units` units yielding `pcs` pieces for the existing PO
    `po` on `day`, optionally in cutting batch `batch` (ordinary cutting RPC). Returns the group and the RPC response."""
    prod=chain.production;base=prod.base
    api.admin(cur)
    payload=dict(action='SAVE_DRAFT',po_id=po,pattern_id=prod.PATTERN,source_location_id=fx['location'],cut_at=prod.at(day,8),
                 change_reason='AZ multi-cut probe: %s units into %s pcs'%(units,pcs),size_slots=[dict(slot_no=1,size_id=base.SIZE,drawing_no=1)],
                 rolls=[dict(roll_id=fx['roll'],qty_issued=units,qty_consumed=units,qty_reported_remaining=0,yields=[dict(slot_no=1,qty_pcs=pcs)])])
    cut=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',payload)
    group=uuid.UUID(cut['cutting_group_id'])
    if batch is not None:
        # Fixture setup only: erp.assign_cutting_group_to_batch is internal (no RPC in the current flow) and the batch link
        # is locked after physical use (validate_cutting_batch_link), so the draft is linked before the cut is posted.
        api.admin(cur)
        cur.execute('select erp.assign_cutting_group_to_batch(%s,%s)',(group,batch))
        cut['row_version']=cur.execute('select row_version from erp.cutting_groups where id=%s',(group,)).fetchone()[0]
    cut=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(payload,id=group,action='POST'),expected_version=int(cut['row_version']))
    api.admin(cur)
    if batch is not None:
        linked=cur.execute('select cutting_batch_id from erp.cutting_groups where id=%s',(group,)).fetchone()[0]
        assert linked==batch,('AZ_M2_BATCH_LINK_NOT_KEPT',linked)
    return group,cut


def produce(cur,fx,po,product,day,units,pcs,batch=None):
    """One cutting group of `units` units yielding `pcs` pieces for the existing PO `po` on `day`, carried through pickup,
    sewing, laundry and final SKU (ALL_READY) to one FG lot of `pcs` pieces on the same day (ordinary RPCs; the AA recipe
    with the quantities as parameters)."""
    prod=chain.production;base=prod.base
    group,cut=cut_only(cur,fx,po,day,units,pcs,batch)
    y=cur.execute("""select y.id from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
      where r.cutting_group_id=%s and y.qty_pcs=%s""",(group,pcs)).fetchall()
    assert len(y)==1,('AZ_MULTI_CUT_YIELD',y)
    pick=dict(action='SAVE_DRAFT',cutting_group_id=group,contractor_id=prod.CONTRACTOR,picked_up_at=prod.at(day,9),allocation_mode='ROLL',
              expected_group_version=int(cut['row_version']),change_reason='AZ multi-cut probe pickup',
              batches=[dict(batch_no=1,allocations=[dict(cutting_roll_yield_id=y[0][0],qty_pcs=pcs)])])
    pickup=prod.rpc(cur,'public.erp_save_cutting_pickup_v1',pick)
    pickup=prod.rpc(cur,'public.erp_save_cutting_pickup_v1',dict(pick,id=pickup['pickup_id'],action='POST'),expected_version=int(pickup['row_version']))
    api.admin(cur)
    batches=cur.execute('select id from erp.cutting_distribution_batches where pickup_id=%s',(pickup['pickup_id'],)).fetchall()
    assert len(batches)==1,('AZ_MULTI_CUT_BATCH',batches)
    completion=uuid.uuid4()
    # One zero-rate component snapshot per PO, shared by both cutting groups.
    snapshot=cur.execute('select id from erp.po_work_component_snapshots where po_id=%s and work_component_id=%s',(po,prod.COMPONENT)).fetchone()
    if snapshot:snapshot=snapshot[0]
    else:
        snapshot=uuid.uuid4()
        cur.execute("""insert into erp.po_work_component_snapshots(id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at)
          values(%s,%s,%s,1,0,%s)""",(snapshot,po,prod.COMPONENT,prod.at(day,9,30)))
    ordinary=awp.OrdinaryDraftCursor(cur)
    ordinary.execute("""insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by)
      values(%s,%s,%s,%s,%s,%s,'DRAFT','AZ multi-cut zero-rate sewing draft',%s)""",
      (completion,'AZ-WC-'+str(completion),po,prod.CONTRACTOR,group,prod.at(day,10),base.OPERATOR_APP))
    ordinary.execute("""insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot)
      values(%s,%s,%s,%s,%s,0)""",(completion,snapshot,prod.COMPONENT,pcs,pcs))
    prod.owner(cur)
    cur.execute('select erp.post_work_completion(%s)',(completion,))
    cur.execute('select public.erp_record_sewing_terminal_v1(%s::jsonb,%s::uuid)',
                (json.dumps(dict(work_completion_id=str(completion),qty_pcs=pcs,reason='AZ multi-cut sewing terminal')),uuid.uuid4()))
    api.admin(cur)
    gv=base.group_version(cur,str(group))
    prod.owner(cur)
    delivery=base.action(cur,'POST_DELIVERY',{'distribution_batch_id':str(batches[0][0]),'vendor_id':base.VENDOR,'wash_process_id':base.BASE_PROCESS,
        'target_dyeing_color':'CP6-E-NAVY','physical_at':prod.at(day,11).isoformat(),'reason':'AZ multi-cut laundry delivery',
        'lines':[dict(size_id=base.SIZE,qty_sent_pcs=pcs)]},gv)
    api.admin(cur)
    line=base.delivery_size_line(cur,delivery['delivery_id']);dv=base.delivery_version(cur,delivery['delivery_id'])
    prod.owner(cur)
    receipt=base.action(cur,'POST_RECEIPT',{'delivery_id':delivery['delivery_id'],'wash_process_id':base.BASE_PROCESS,
        'physical_at':prod.at(day,12).isoformat(),'reason':'AZ multi-cut laundry receipt',
        'lines':[dict(delivery_batch_size_line_id=line,qty_good_received=pcs,qty_bs_laundry=0,bs_product_id=None)]},dv)
    api.admin(cur)
    rows=cur.execute("""select s.id,s.receipt_line_id from erp.laundry_receipt_batch_size_lines s
      join erp.laundry_receipt_lines l on l.id=s.receipt_line_id where l.receipt_id=%s""",(receipt['receipt_id'],)).fetchall()
    assert len(rows)==1,('AZ_MULTI_CUT_RECEIPT',rows)
    gv=base.group_version(cur,str(group))
    prod.owner(cur)
    final_sku=lambda at,version:base.action(cur,'POST_FINAL_SKU',{'cutting_group_id':str(group),'destination_location_id':base.LOCATION,
        'physical_at':at,'reason':'AZ multi-cut final SKU','good_qty_pcs':pcs,'completion_mode':'ALL_READY',
        'lines':[dict(final_product_id=product,qty_good_pcs=pcs,qty_bs_pcs=0,source_laundry_receipt_line_id=str(rows[0][1]),
                      source_laundry_receipt_batch_size_line_id=str(rows[0][0]))]},version)
    final=final_sku(prod.at(day,13).isoformat(),gv)
    api.admin(cur)
    PRODUCED[str(group)]=dict(final=final,redo=final_sku)
    return group


def multi_cut(cur,today,price,batch=False):
    """Independent review finding (24 Sep, open): one PO cut on two days with a FG lot between the cuts and different yields.
    Cut 1 on d+1: 4 units into 8 pcs, FG lot of 8 pcs on d+1; cut 2 on d+2: 6 units into 3 pcs, FG lot of 3 pcs on d+2.
    The lot HPP is allocated per cutting-group lineage (erp.rebuild_po_hpp: group material x lot pcs / group pcs), so a late
    invoice changes lot 1 by 4x and lot 2 by 6x (x = price - 10). AY rev3 spread the PO change 10x over the lot dates by
    pieces (8/11 and 3/11), i.e. 7.27x on d+1 while only 4x of corrected material was cut by then: run 35968507694 showed
    the PO's WIP at -2.29 on d+1 for a higher price (FG +5.09 instead of +2.80). AY rev4 posts each lot's own change. Expected here (the physical principle the owner approved): FG change on d+1 = 4x and
    on d+2 = 6x, WIP of the PO never negative, material at the invoice price for the units in stock."""
    prod=chain.production
    d=today-timedelta(days=3);d2=d+timedelta(days=1);d3=d+timedelta(days=2)
    days=[d+timedelta(days=i) for i in range(4)]
    boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    quiet=awp.quiet_seed(cur,d,today-timedelta(days=1),exclude=[prod.CONTRACTOR])
    fx=prod.estimated_receipt(cur,today)
    api.admin(cur)
    po=uuid.uuid4();product=prod.base.create_product(cur,uuid.uuid4().hex[:16])
    cur.execute("""insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)
      values(%s,%s,%s,11,'CUTTING','CUTTING',%s,'AZ multi-cut probe')""",(po,'AZ-MC-PO-'+str(po),prod.MODEL,prod.at(d2,7)))
    pool=None
    if batch:
        # Independent review 24 Sep, M2 (suspected): both cutting groups in one cutting batch, cut on different days;
        # erp.rebuild_po_hpp then pools the batch material over the batch pieces.
        pool=uuid.uuid4()
        cur.execute("insert into erp.cutting_batches(id,po_id,batch_number,cut_at,status,notes) values(%s,%s,%s,%s,'OPEN','AZ M2 probe batch')",
                    (pool,po,'AZ-M2-'+pool.hex[:12],prod.at(d2,8)))
    g1=produce(cur,fx,po,product,d2,4,8,batch=pool)
    g2=produce(cur,fx,po,product,d3,6,3,batch=pool)
    quiet_fixture=awp.quiet_seed(cur,d,today-timedelta(days=1))
    lots=[(str(r[0]),r[1],r[2]) for r in cur.execute("""select cutting_group_id,erp._cp3_business_date(produced_at),initial_qty_pcs
      from erp.fg_lots where po_id=%s and lot_origin='PRODUCTION' order by produced_at""",(po,)).fetchall()]
    before=ledger_days(cur,days,[po])
    old={r[0] for r in cur.execute('select id from erp.po_hpp_gl_events where po_id=%s',(po,)).fetchall()}
    response=invoice(cur,fx,today,price,d)
    after=ledger_days(cur,days,[po])
    new=[(str(r[0]),r[1],dec(r[2]),dec(r[3])) for r in cur.execute(
        'select id,effective_date,fg_delta,cogs_delta from erp.po_hpp_gl_events where po_id=%s order by effective_date,id',(po,)).fetchall() if r[0] not in old]
    x=dec(price)-10
    move={str(day):{k:dec(after[str(day)][k])-dec(before[str(day)][k]) for k in KEYS} for day in days}
    wip_po={str(day):dec(after[str(day)]['WIP_PO'][str(po)]) for day in days}
    stock={str(d):10,str(d2):6,str(d3):0,str(today):0}
    pre=awp.preflight(cur,today)
    negative=[b for b in pre['blockers'] if b['code']=='GL_INVENTORY_NEGATIVE_ASOF'] if pre else None
    checks=dict(fixture_two_lots_two_days=[(l[1],l[2]) for l in lots]==[(d2,8),(d3,3)] and [l[0] for l in lots]==[str(g1),str(g2)],
                fg_change_by_lineage=move[str(d2)]['FG_INVENTORY']==4*x and move[str(d3)]['FG_INVENTORY']==10*x,
                material_at_invoice_price=all(move[str(day)]['MATERIAL_INVENTORY']==x*stock[str(day)] for day in days),
                wip_po_never_negative=all(v>=0 for v in wip_po.values()),
                wip_po_correction_zero_each_day=all(move[str(day)]['WIP']==0 for day in days),
                no_negative_daily_inventory=negative==[])
    status='PASS' if all(checks.values()) else ('COUNTEREXAMPLE' if not az_installed(cur) else 'FAIL')
    return dict(status=status,finding='independent review 24 Sep #3; proven by run 35968507694 on AY rev3; AY rev4 dates each lot its own change',price=price,receipt_day=str(d),lots=lots,checks=checks,
                hpp_events=[[str(v) for v in e] for e in new],daily_move={k:{kk:str(vv) for kk,vv in v.items()} for k,v in move.items()},
                wip_po={k:str(v) for k,v in wip_po.items()},negative_blockers=negative,invoice=response,quiet=[quiet,quiet_fixture])


def write_off(cur,today,price):
    """Independent review 24 Sep (B1): pieces that leave a lot other than by sale. One cut of 10 units into 10 pcs and a FG
    lot of 10 pcs on d+1, 4 pcs written off (FG adjustment LOSS) on d+2, late invoice on d (open). Expected: FG +10x on
    d+1, -4x on d+2 (the written-off pieces' correction leaves FG on the write-off day), the PO's WIP change 0 every day,
    and the write-off itself (posted before the invoice, outside the invoice path) dated d+2 as before AY (M1)."""
    prod=chain.production
    d=today-timedelta(days=3);d2=d+timedelta(days=1);d3=d+timedelta(days=2)
    days=[d+timedelta(days=i) for i in range(4)]
    boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    quiet=awp.quiet_seed(cur,d,today-timedelta(days=1),exclude=[prod.CONTRACTOR])
    fx=prod.estimated_receipt(cur,today)
    api.admin(cur)
    po=uuid.uuid4();product=prod.base.create_product(cur,uuid.uuid4().hex[:16])
    cur.execute("""insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)
      values(%s,%s,%s,10,'CUTTING','CUTTING',%s,'AZ write-off probe')""",(po,'AZ-WO-PO-'+str(po),prod.MODEL,prod.at(d2,7)))
    produce(cur,fx,po,product,d2,10,10)
    lot=cur.execute("select id from erp.fg_lots where po_id=%s and lot_origin='PRODUCTION'",(po,)).fetchone()[0]
    prior_ledger=ledger_days(cur,days,[po])
    prod.owner(cur)
    adjustment=cur.execute('select erp.save_fg_adjustment_draft_v2(%s::jsonb,%s::uuid,null)',(json.dumps(dict(
        adjustment_number='AZ-WO-'+uuid.uuid4().hex,location_id=str(prod.base.LOCATION),physical_at=prod.at(d3,12).isoformat(),
        reason_code='LOSS',reason='AZ write-off after the lot day',change_reason='AZ B1 probe write-off',
        items=[dict(lot_id=str(lot),product_id=str(product),quality_grade='GRADE_A',qty_signed=-4,notes='AZ written off')])),str(uuid.uuid4()))).fetchone()[0]
    # erp.post_fg_adjustment is not granted to authenticated (postgres, service_role); as in the E regression it is called
    # by the privileged session with the owner claims kept (require_owner_admin reads the claims).
    prod.prior.actors.session(cur,'supabase_admin')
    cur.execute('select erp.post_fg_adjustment(%s)',(adjustment['fg_adjustment_id'],))
    api.admin(cur)
    quiet_fixture=awp.quiet_seed(cur,d,today-timedelta(days=1))
    before=ledger_days(cur,days,[po])
    response=invoice(cur,fx,today,price,d)
    after=ledger_days(cur,days,[po])
    x=dec(price)-10
    move={str(day):{k:dec(after[str(day)][k])-dec(before[str(day)][k]) for k in KEYS} for day in days}
    wip_po={str(day):dec(after[str(day)]['WIP_PO'][str(po)]) for day in days}
    write_off_day={str(day):dec(before[str(day)]['FG_INVENTORY'])-dec(prior_ledger[str(day)]['FG_INVENTORY']) for day in days}
    stock={str(d):10,str(d2):0,str(d3):0,str(today):0}
    pre=awp.preflight(cur,today)
    negative=[b for b in pre['blockers'] if b['code']=='GL_INVENTORY_NEGATIVE_ASOF'] if pre else None
    checks=dict(fg_change_follows_pieces=move[str(d2)]['FG_INVENTORY']==10*x and move[str(d3)]['FG_INVENTORY']==6*x and move[str(today)]['FG_INVENTORY']==6*x,
                material_at_invoice_price=all(move[str(day)]['MATERIAL_INVENTORY']==x*stock[str(day)] for day in days),
                wip_po_never_negative=all(v>=0 for v in wip_po.values()),
                wip_po_correction_zero_each_day=all(move[str(day)]['WIP']==0 for day in days),
                write_off_posted_on_its_day=write_off_day[str(d2)]==0 and write_off_day[str(d3)]<0,
                no_negative_daily_inventory=negative==[])
    status='PASS' if all(checks.values()) else ('COUNTEREXAMPLE' if not az_installed(cur) else 'FAIL')
    return dict(status=status,finding='independent review 24 Sep B1 (write-off) and M1 (write-off date outside the invoice path)',price=price,
                receipt_day=str(d),checks=checks,daily_move={k:{kk:str(vv) for kk,vv in v.items()} for k,v in move.items()},
                wip_po={k:str(v) for k,v in wip_po.items()},write_off_fg_by_day={k:str(v) for k,v in write_off_day.items()},
                negative_blockers=negative,invoice=response,quiet=[quiet,quiet_fixture])


def contractor_after_lot(cur,today,price):
    """Independent review of AY rev6 (M-1): a material fact behind the lot HPP that happens after the lot. One cut of 6 units
    into 10 pcs and a FG lot of 10 pcs on d+1; 4 units of the same fabric issued to the PO's contractor on d+2 (non-accessory:
    erp.rebuild_po_hpp shares it over the PO's source quantity, 10 pcs); late invoice on d (open). The contractor issue does
    not rebuild the HPP, so the invoice brings the contractor material into the lot for the first time. Expected (AY rev7):
    FG +6x on d+1 (the cut material only), the rest of the lot change (the contractor material and its correction) on d+2,
    the PO's WIP never negative, and material at the invoice price for the units in stock."""
    prod=chain.production
    d=today-timedelta(days=3);d2=d+timedelta(days=1);d3=d+timedelta(days=2)
    days=[d+timedelta(days=i) for i in range(4)]
    boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    quiet=awp.quiet_seed(cur,d,today-timedelta(days=1),exclude=[prod.CONTRACTOR])
    fx=prod.estimated_receipt(cur,today)
    api.admin(cur)
    po=uuid.uuid4();product=prod.base.create_product(cur,uuid.uuid4().hex[:16])
    cur.execute("""insert into erp.production_orders(id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at,notes)
      values(%s,%s,%s,%s,10,'CUTTING','CUTTING',%s,'AZ contractor material probe')""",(po,'AZ-CM-PO-'+str(po),prod.MODEL,prod.CONTRACTOR,prod.at(d2,7)))
    produce(cur,fx,po,product,d2,6,10)
    lot=cur.execute("select id from erp.fg_lots where po_id=%s and lot_origin='PRODUCTION'",(po,)).fetchone()[0]
    # A contractor issue needs the contractor selling price of the material in effect at the issue time (AO,
    # normalize_contractor_issue_item_uom_price); it only drives the contractor receivable, not the checked accounts.
    cur.execute("""insert into erp.contractor_material_price_versions(material_id,contractor_id,selling_price,effective_from,notes)
      values(%s,%s,12,%s,'AZ probe contractor selling price')""",(fx['material'],prod.CONTRACTOR,prod.at(d,0)))
    # The issue line takes the material's unit as its transaction unit (fk_contractor_issue_transaction_uom). The AA base
    # material the fixture clones carries the legacy unit 'yd', not registered in erp.uom_definitions of the test chain
    # (materials entering through the import must use a registered unit), so the fixture registers it.
    cur.execute("""insert into erp.uom_definitions(unit_code,unit_name,dimension,is_active)
      select m.unit_code,'AZ probe fabric unit','LENGTH',true from erp.materials m where m.id=%s
      and not exists(select 1 from erp.uom_definitions u where u.unit_code=m.unit_code)""",(fx['material'],))
    prod.owner(cur)
    # erp.save_contractor_material_issue_draft_v2 / erp.post_contractor_material_issue are internal (require_internal): the
    # privileged session with the owner claims kept, as in the write-off fixture.
    prod.prior.actors.session(cur,'supabase_admin')
    draft=cur.execute('select erp.save_contractor_material_issue_draft_v2(%s::jsonb,%s::uuid,null)',(json.dumps(dict(
        issue_number='AZ-CM-'+uuid.uuid4().hex,contractor_id=str(prod.CONTRACTOR),po_id=str(po),physical_at=prod.at(d3,10).isoformat(),
        location_id=str(fx['location']),change_reason='AZ M-1 probe: contractor material after the lot',
        items=[dict(material_id=str(fx['material']),roll_id=str(fx['roll']),qty=4)])),str(uuid.uuid4()))).fetchone()[0]
    cur.execute('select erp.post_contractor_material_issue(%s)',(draft['contractor_material_issue_id'],))
    api.admin(cur)
    issued=cur.execute("""select erp._cp3_business_date(m.physical_at),m.qty_signed from erp.material_stock_movements m
      join erp.contractor_material_issue_items i on i.id=m.source_id where m.source_type='CONTRACTOR_MATERIAL_ISSUE_ITEM'
      and i.issue_id=%s""",(draft['contractor_material_issue_id'],)).fetchall()
    quiet_fixture=awp.quiet_seed(cur,d,today-timedelta(days=1))
    hpp=lambda:dec(cur.execute('select total_cost from erp.hpp_versions where lot_id=%s and is_current',(lot,)).fetchone()[0])
    material=lambda:dec(cur.execute("""select c.total_cost from erp.hpp_version_components c join erp.hpp_versions v on v.id=c.hpp_version_id
      where v.lot_id=%s and v.is_current and c.component_type='MATERIAL'""",(lot,)).fetchone()[0])
    hpp_before=hpp();material_before=material()
    before=ledger_days(cur,days,[po])
    response=invoice(cur,fx,today,price,d)
    after=ledger_days(cur,days,[po])
    hpp_after=hpp();material_after=material()
    x=dec(price)-10
    move={str(day):{k:dec(after[str(day)][k])-dec(before[str(day)][k]) for k in KEYS} for day in days}
    wip_po={str(day):dec(after[str(day)]['WIP_PO'][str(po)]) for day in days}
    stock={str(d):10,str(d2):4,str(d3):0,str(today):0}
    state=[[r[0][:2],str(r[1])] for r in cur.execute("""select source_key,material_value from erp.po_hpp_gl_material_state_v1
      where po_id=%s order by 1""",(po,)).fetchall()] if az_installed(cur) or ayp.ay_installed(cur) else None
    pre=awp.preflight(cur,today)
    negative=[b for b in pre['blockers'] if b['code']=='GL_INVENTORY_NEGATIVE_ASOF'] if pre else None
    # The contractor material (4 units at 10) the HPP did not carry before the invoice (0 or 40).
    gap=10*10-material_before
    checks=dict(fixture_issue_after_lot=[(r[0],dec(r[1])) for r in issued]==[(d3,Decimal(-4))],
                hpp_material_cut_plus_contractor=material_after==10*dec(price) and hpp_after-hpp_before==material_after-material_before,
                fg_lot_day_cut_material_only=move[str(d2)]['FG_INVENTORY']==6*x,
                fg_rest_on_contractor_day=move[str(d3)]['FG_INVENTORY']==hpp_after-hpp_before and move[str(today)]['FG_INVENTORY']==hpp_after-hpp_before,
                material_at_invoice_price=all(move[str(day)]['MATERIAL_INVENTORY']==x*stock[str(day)] for day in days),
                wip_po_never_negative=all(v>=0 for v in wip_po.values()),
                wip_po_change_only_the_contractor_material=move[str(d)]['WIP']==0 and move[str(d2)]['WIP']==0 and move[str(d3)]['WIP']==-gap and move[str(today)]['WIP']==-gap,
                no_negative_daily_inventory=negative==[])
    status='PASS' if all(checks.values()) else ('COUNTEREXAMPLE' if not az_installed(cur) else 'FAIL')
    return dict(status=status,finding='independent review of AY rev6, M-1 (material fact after the lot); AY rev7 dates each material fact on its own day',
                price=price,receipt_day=str(d),hpp_before=str(hpp_before),hpp_after=str(hpp_after),material_before=str(material_before),material_after=str(material_after),issued=[[str(a),str(b)] for a,b in issued],
                material_state=state,checks=checks,daily_move={k:{kk:str(vv) for kk,vv in v.items()} for k,v in move.items()},
                wip_po={k:str(v) for k,v in wip_po.items()},negative_blockers=negative,invoice=response,quiet=[quiet,quiet_fixture])


def batch_partner(cur,today,price):
    """Independent review of AY rev7 (batch partner not queued): erp.rebuild_po_hpp pools cutting material over the cutting
    batch, groups of other POs included, but _recalculate_material_cost_core queued only the POs whose own groups used the
    recosted material. Fixture: PO A cuts 4 units of the invoiced fabric into 8 pcs on d+1 in a cutting batch; PO B cuts 6
    units of another fabric into 3 pcs on d+1 into the same batch. Late invoice for the first fabric on d. T1 run 35992859006:
    the product refuses the cross-PO batch (validate_cutting_batch_link), so the case records that refusal and the core is
    not changed; should the product ever accept it, the case checks that PO B is rebuilt and synced (sentinel)."""
    prod=chain.production
    d=today-timedelta(days=3);d2=d+timedelta(days=1)
    days=[d+timedelta(days=i) for i in range(4)]
    boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    quiet=awp.quiet_seed(cur,d,today-timedelta(days=1),exclude=[prod.CONTRACTOR])
    fx=prod.estimated_receipt(cur,today)
    fx2=prod.estimated_receipt(cur,today)
    api.admin(cur)
    po_a=uuid.uuid4();po_b=uuid.uuid4()
    product_a=prod.base.create_product(cur,uuid.uuid4().hex[:16]);product_b=prod.base.create_product(cur,uuid.uuid4().hex[:16])
    for po,label in ((po_a,'A'),(po_b,'B')):
        cur.execute("""insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)
          values(%s,%s,%s,11,'CUTTING','CUTTING',%s,'AZ batch partner probe')""",(po,'AZ-BP-%s-%s'%(label,po),prod.MODEL,prod.at(d2,7)))
    pool=uuid.uuid4()
    cur.execute("insert into erp.cutting_batches(id,po_id,batch_number,cut_at,status,notes) values(%s,%s,%s,%s,'OPEN','AZ batch partner probe')",
                (pool,po_a,'AZ-BP-'+pool.hex[:12],prod.at(d2,8)))
    produce(cur,fx,po_a,product_a,d2,4,8,batch=pool)
    cur.execute('savepoint az_batch_partner')
    try:
        produce(cur,fx2,po_b,product_b,d2,6,3,batch=pool)
    except psycopg.Error as exc:
        cur.execute('rollback to savepoint az_batch_partner');api.admin(cur)
        refused='Cutting batch must belong to the same production order' in str(exc)
        return dict(status='PASS' if refused else 'FAIL',finding='independent review of AY rev7: batch partner PO not queued',
                    checks=dict(cross_po_batch_refused_by_product=refused),error=str(exc)[:400],
                    note='The product refuses a cutting group of another PO in a cutting batch; the partner queue of AZ rev2 is a no-op.')
    api.admin(cur)
    lot_b=cur.execute("select id from erp.fg_lots where po_id=%s and lot_origin='PRODUCTION'",(po_b,)).fetchone()[0]
    version=lambda:cur.execute('select id,total_cost from erp.hpp_versions where lot_id=%s and is_current',(lot_b,)).fetchone()
    quiet_fixture=awp.quiet_seed(cur,d,today-timedelta(days=1))
    before_b=version()
    response=invoice(cur,fx,today,price,d)
    after_b=version()
    target=cur.execute('select round(hpp_total_cost,2) from erp.compute_po_hpp_gl_targets_v2620d(%s)',(po_b,)).fetchone()[0]
    posted=cur.execute('select hpp_total_cost from erp.po_hpp_gl_state where po_id=%s',(po_b,)).fetchone()
    pre=awp.preflight(cur,today)
    negative=[b for b in pre['blockers'] if b['code']=='GL_INVENTORY_NEGATIVE_ASOF'] if pre else None
    checks=dict(partner_hpp_rebuilt=after_b[0]!=before_b[0] and dec(after_b[1])!=dec(before_b[1]),
                partner_posted_hpp_equals_target=posted is not None and dec(posted[0])==dec(target),
                no_negative_daily_inventory=negative==[])
    status='PASS' if all(checks.values()) else ('COUNTEREXAMPLE' if not az_installed(cur) else 'FAIL')
    return dict(status=status,finding='independent review of AY rev7: batch partner PO not queued',price=price,checks=checks,
                partner_hpp=[str(before_b[1]),str(after_b[1])],partner_target=str(target),partner_posted=str(posted[0]) if posted else None,
                negative_blockers=negative,invoice=response,quiet=[quiet,quiet_fixture])


def invoice_before_receipt(cur,today,price):
    """Owner decision 24 Sep 2026 (option 1): a supplier invoice dated before its goods were received is booked on the
    receipt day; the invoice date stays the document date. Fixture: the AA estimated receipt (10 units at 10 on d, 23:30);
    the invoice is dated d-1 (open). Expected: the MATERIAL_SUPPLIER_INVOICE journal and the recost context on d, the
    invoice document keeps d-1, no ledger change on d-1, material at the invoice price from d."""
    prod=chain.production
    d=today-timedelta(days=3);d0=d-timedelta(days=1)
    days=[d0+timedelta(days=i) for i in range(5)]
    boundary.historical.prior.set_open_period(cur,d0-timedelta(days=1))
    quiet=awp.quiet_seed(cur,d0,today-timedelta(days=1),exclude=[prod.CONTRACTOR])
    fx=prod.estimated_receipt(cur,today)
    api.admin(cur)
    before=ledger_days(cur,days,[])
    response=invoice(cur,fx,today,price,d0)
    after=ledger_days(cur,days,[])
    inv=cur.execute("""select h.id,h.invoice_date from erp.material_supplier_invoices h join erp.material_supplier_invoice_lines l on l.invoice_id=h.id
      where l.purchase_item_id=%s order by h.invoice_date,h.id desc limit 1""",(fx['item'],)).fetchone()
    booked=[r[0] for r in cur.execute("""select distinct transaction_date from erp.journal_entries
      where source_type='MATERIAL_SUPPLIER_INVOICE' and source_id=%s""",(inv[0],)).fetchall()]
    x=dec(price)-10
    move={str(day):{k:dec(after[str(day)][k])-dec(before[str(day)][k]) for k in KEYS} for day in days}
    pre=awp.preflight(cur,today)
    negative=[b for b in pre['blockers'] if b['code']=='GL_INVENTORY_NEGATIVE_ASOF'] if pre else None
    checks=dict(invoice_document_date_kept=inv[1]==d0,
                journal_on_receipt_day=booked==[d],
                nothing_before_receipt=all(v==0 for v in move[str(d0)].values()),
                material_at_invoice_price_from_receipt=move[str(d)]['MATERIAL_INVENTORY']==10*x,
                no_negative_daily_inventory=negative==[])
    status='PASS' if all(checks.values()) else ('COUNTEREXAMPLE' if not az_installed(cur) else 'FAIL')
    return dict(status=status,finding='owner decision 24 Sep 2026 option 1: invoice dated before the receipt is booked on the receipt day',
                price=price,receipt_day=str(d),invoice_date=str(d0),booked=[str(b) for b in booked],checks=checks,
                daily_move={k:{kk:str(vv) for kk,vv in v.items()} for k,v in move.items()},negative_blockers=negative,
                invoice=response,quiet=quiet)


def final_receipt(cur,day,qty=10,price=10):
    """A direct FINAL receipt (supplier invoice number on the receipt, price SUPPLIER_INVOICE) of `qty` units at `price` on
    `day` 10:00, as the AO direct-correction trial (ordinary purchase RPCs)."""
    prod=chain.production;prior=prod.prior
    api.admin(cur);prod.zone(cur,'Asia/Jakarta')
    material=prior.clone_material(cur,'az-cost-correction')
    location=uuid.uuid4()
    cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,'AZ cost correction raw warehouse','RAW_MATERIAL_WAREHOUSE',true)",
                (location,'AZ-LOC-'+location.hex[:20]))
    draft=prod.rpc(cur,'erp.save_material_purchase_draft_v2',dict(purchase_number='AZ-CC-PUR-'+str(uuid.uuid4()),supplier_id=prior.BASE_SUPPLIER,
        location_id=location,supplier_invoice_number='AZ-CC-INV-'+uuid.uuid4().hex[:12],physical_at=prod.at(day,10),
        change_reason='AZ direct final receipt',lines=[dict(material_id=material,qty=qty,unit_price=price,price_state='FINAL',
        price_source='SUPPLIER_INVOICE',rolls=[dict(roll_number='AZ-CC-ROLL-'+str(uuid.uuid4()),qty=qty)])]))
    purchase=uuid.UUID(draft['purchase_id'])
    cur.execute('select erp.post_material_purchase_v2(%s,%s,%s,%s)',(purchase,uuid.uuid4(),int(draft['row_version']),'AZ direct final receipt post'))
    api.admin(cur)
    item=cur.execute('select id from erp.material_purchase_items where purchase_id=%s',(purchase,)).fetchone()[0]
    return dict(material=material,purchase=purchase,item=item,location=location)


def cost_correction_before_receipt(cur,today,price):
    """Owner decision 24 Sep 2026 (option 1) applied to the purchase cost correction (erp.post_material_purchase_cost_correction,
    which carries an invoice date like a supplier invoice): a direct FINAL receipt of 10 units at 10 on d; a cost correction
    to `price` with invoice date d-1 (open). Expected: its journals on d (economic and transaction date), nothing on d-1,
    the correction keeps d-1 as its document date, material at `price` from d."""
    prod=chain.production
    d=today-timedelta(days=3);d0=d-timedelta(days=1)
    days=[d0+timedelta(days=i) for i in range(5)]
    boundary.historical.prior.set_open_period(cur,d0-timedelta(days=1))
    quiet=awp.quiet_seed(cur,d0,today-timedelta(days=1),exclude=[prod.CONTRACTOR])
    fx=final_receipt(cur,d)
    before=ledger_days(cur,days,[])
    api.admin(cur)
    corr=cur.execute("""insert into erp.material_purchase_cost_corrections(correction_number,purchase_id,invoice_date,reason)
      values(%s,%s,%s,%s) returning id""",('AZ-CC-'+uuid.uuid4().hex[:12],fx['purchase'],d0,'AZ cost correction dated before the receipt')).fetchone()[0]
    cur.execute('insert into erp.material_purchase_cost_correction_items(correction_id,purchase_item_id,new_unit_price) values(%s,%s,%s)',(corr,fx['item'],price))
    ids=[r[0] for r in cur.execute('select id from erp.journal_entries').fetchall()]
    cur.execute('savepoint az_cost_correction')
    try:
        prod.owner(cur);cur.execute('select erp.post_material_purchase_cost_correction(%s)',(corr,))
    except psycopg.Error as exc:
        # The product may refuse a correction dated before its receipt; then there is nothing to date (recorded as such).
        cur.execute('rollback to savepoint az_cost_correction');api.admin(cur)
        return dict(status='PASS',finding='product refuses a purchase cost correction dated before its receipt',refused=str(exc).splitlines()[0],
                    receipt_day=str(d),invoice_date=str(d0),quiet=quiet)
    prod.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');api.admin(cur)
    after=ledger_days(cur,days,[])
    fresh=[(r[0],r[1],r[2]) for r in cur.execute("""select source_type,economic_date,transaction_date from erp.journal_entries
      where id<>all(%s::uuid[]) order by source_type,economic_date""",(ids,)).fetchall()]
    kept=cur.execute('select invoice_date,status from erp.material_purchase_cost_corrections where id=%s',(corr,)).fetchone()
    x=dec(price)-10
    move={str(day):{k:dec(after[str(day)][k])-dec(before[str(day)][k]) for k in KEYS} for day in days}
    pre=awp.preflight(cur,today)
    negative=[b for b in pre['blockers'] if b['code']=='GL_INVENTORY_NEGATIVE_ASOF'] if pre else None
    checks=dict(correction_document_date_kept=kept[0]==d0 and kept[1]=='POSTED',
                journals_on_receipt_day=bool(fresh) and all(e==d and t==d for _,e,t in fresh),
                nothing_before_receipt=all(v==0 for v in move[str(d0)].values()),
                material_at_corrected_price_from_receipt=all(move[str(day)]['MATERIAL_INVENTORY']==10*x for day in days[1:]),
                no_negative_daily_inventory=negative==[])
    status='PASS' if all(checks.values()) else ('COUNTEREXAMPLE' if not az_installed(cur) else 'FAIL')
    return dict(status=status,finding='owner decision 24 Sep 2026 option 1, same rule for the purchase cost correction',price=price,
                receipt_day=str(d),invoice_date=str(d0),journals=[[a,str(b),str(c)] for a,b,c in fresh],checks=checks,
                daily_move={k:{kk:str(vv) for kk,vv in v.items()} for k,v in move.items()},negative_blockers=negative,quiet=quiet)


def goods_flow(cur,today,price,flow):
    """Branches without a native fixture until 24 Sep (independent review): a lot of 10 pcs (one cut of 10 units) on d+1,
    then RETURN (3 pcs sold on d+1, 1 returned on d+2), REVERSED (all 10 sold on d+2, the sale reversed today before the
    invoice; review F1), CONVERSION (4 pcs relabelled to another product on d+2), CONVERSION_SALE (the same, then 2
    relabelled pcs sold today; review F4) or QC_REDO (the Final SKU reversed and posted again today; review F2); late
    invoice on d (open). Expected: FG gets each piece's
    correction from the day it entered FG, COGS from the sale day, the return back on the return day; a reversed sale
    counts as not sold (as the target counts it); a conversion moves FG to FG; the PO's WIP change is 0 every day."""
    prod=chain.production
    d=today-timedelta(days=3);d2=d+timedelta(days=1);d3=d+timedelta(days=2)
    days=[d+timedelta(days=i) for i in range(4)]
    boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    quiet=awp.quiet_seed(cur,d,today-timedelta(days=1),exclude=[prod.CONTRACTOR])
    fx=prod.estimated_receipt(cur,today)
    api.admin(cur)
    po=uuid.uuid4();product=prod.base.create_product(cur,uuid.uuid4().hex[:16])
    cur.execute("""insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)
      values(%s,%s,%s,10,'CUTTING','CUTTING',%s,'AZ goods flow probe')""",(po,'AZ-GF-PO-'+str(po),prod.MODEL,prod.at(d2,7)))
    group=produce(cur,fx,po,product,d2,10,10)
    fixture={}
    if flow=='QC_REDO':
        # Independent review F2: the Final SKU is reversed (the lot becomes VOIDED_PRODUCTION) and posted again today.
        done=PRODUCED[str(group)]
        prod.owner(cur)
        reversed_=prod.base.action(cur,'REVERSE_FINAL_SKU',{'qc_inspection_id':str(done['final']['qc_inspection_id']),
            'reason':'AZ QC reversed after the lot day'},int(done['final']['qc_row_version']))
        api.admin(cur)
        assert reversed_.get('status')=='REVERSED',('AZ_QC_REDO_REVERSE',reversed_)
        gv=prod.base.group_version(cur,str(group))
        prod.owner(cur)
        again=done['redo'](cur.execute('select statement_timestamp()').fetchone()[0].isoformat(),gv)
        api.admin(cur)
        fixture.update(reversed=reversed_.get('status'),redo=again.get('qc_inspection_id'),
                       voided=cur.execute("select count(*) from erp.fg_lots where po_id=%s and lot_origin='VOIDED_PRODUCTION'",(po,)).fetchone()[0])
    if flow in('RETURN','REVERSED'):
        customer=prod.base.create_customer(cur,uuid.uuid4().hex[:16])
        sale=prod.rpc(cur,'erp.save_sale_draft_v2',{'sale_number':'AZ-GF-SALE-'+str(uuid.uuid4()),'customer_id':customer,
            'source_location_id':prod.base.LOCATION,'sale_date':prod.at(d2 if flow=='RETURN' else d3,14 if flow=='RETURN' else 10),
            'reason':'AZ goods flow sale','items':[dict(product_id=product,qty_pcs=3 if flow=='RETURN' else 10,unit_price_snapshot=40,discount_amount=0)]})
        cur.execute('select erp.post_sale_v2(%s,%s,%s)',(sale['sale_id'],uuid.uuid4(),int(sale['row_version'])))
        api.admin(cur)
        if flow=='RETURN':
            allocation=cur.execute("""select a.id from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id
              where i.sale_id=%s""",(sale['sale_id'],)).fetchall()
            assert len(allocation)==1,('AZ_GF_ALLOCATION',allocation)
            rid=uuid.uuid4()
            cur.execute("insert into erp.sales_returns(id,return_number,sale_id,customer_id,physical_at,status) values(%s,%s,%s,%s,%s,'DRAFT')",
                        (rid,'AZ-GF-RET-'+rid.hex,sale['sale_id'],customer,prod.at(d3,12)))
            cur.execute("""insert into erp.sales_return_items(return_id,sale_stock_allocation_id,location_id,qty_pcs,refund_amount,quality_grade)
              values(%s,%s,%s,1,40,'GRADE_A')""",(rid,allocation[0][0],prod.base.LOCATION))
            prod.owner(cur);cur.execute('select erp.post_sales_return(%s)',(rid,));api.admin(cur)
            fixture['return']=str(rid)
        else:
            prod.owner(cur);cur.execute('select erp.reverse_sale(%s,%s)',(sale['sale_id'],'AZ goods flow: sale reversed before the invoice'));api.admin(cur)
        fixture['sale']=str(sale['sale_id'])
    elif flow in('CONVERSION','CONVERSION_SALE'):
        target=prod.base.create_product(cur,uuid.uuid4().hex[:16])
        conversion=uuid.uuid4()
        cur.execute("""insert into erp.product_conversions(id,conversion_number,from_product_id,to_product_id,location_id,qty_pcs,conversion_type,
            physical_at,status,conversion_cost_total,notes,created_by) values(%s,%s,%s,%s,%s,4,'RELABEL',%s,'DRAFT',0,'AZ goods flow conversion',%s)""",
            (conversion,'AZ-GF-CONV-'+conversion.hex,product,target,prod.base.LOCATION,prod.at(d3,9),prod.base.OPERATOR_APP))
        prod.owner(cur);prod.prior.actors.session(cur,'supabase_admin')
        cur.execute('select erp.post_product_conversion(%s)',(conversion,));api.admin(cur)
        fixture['conversion']=str(conversion)
        if flow=='CONVERSION_SALE':
            # Independent review F4: the relabelled lot has no sync of its own; a later leg (2 relabelled pcs sold today).
            customer=prod.base.create_customer(cur,uuid.uuid4().hex[:16])
            sale=prod.rpc(cur,'erp.save_sale_draft_v2',{'sale_number':'AZ-GF-SALE-'+str(uuid.uuid4()),'customer_id':customer,
                'source_location_id':prod.base.LOCATION,'sale_date':cur.execute("select statement_timestamp()").fetchone()[0],
                'reason':'AZ relabelled pieces sold','items':[dict(product_id=target,qty_pcs=2,unit_price_snapshot=40,discount_amount=0)]})
            cur.execute('select erp.post_sale_v2(%s,%s,%s)',(sale['sale_id'],uuid.uuid4(),int(sale['row_version'])))
            api.admin(cur)
            fixture['sale']=str(sale['sale_id'])
    quiet_fixture=awp.quiet_seed(cur,d,today-timedelta(days=1))
    before=ledger_days(cur,days,[po])
    response=invoice(cur,fx,today,price,d)
    after=ledger_days(cur,days,[po])
    x=dec(price)-10
    move={str(day):{k:dec(after[str(day)][k])-dec(before[str(day)][k]) for k in KEYS} for day in days}
    wip_po={str(day):dec(after[str(day)]['WIP_PO'][str(po)]) for day in days}
    fg={str(d):0,str(d2):10,str(d3):10,str(today):10};cogs=dict.fromkeys(fg,0)
    if flow=='RETURN':fg.update({str(d2):7,str(d3):8,str(today):8});cogs.update({str(d2):3,str(d3):2,str(today):2})
    # A sale reversed later: the pieces leave FG on the sale day and come back on the reversal day (review F1).
    if flow=='REVERSED':fg.update({str(d3):0});cogs.update({str(d3):10,str(today):0})
    if flow=='CONVERSION_SALE':fg.update({str(today):8});cogs.update({str(today):2})
    pre=awp.preflight(cur,today)
    negative=[b for b in pre['blockers'] if b['code']=='GL_INVENTORY_NEGATIVE_ASOF'] if pre else None
    checks=dict(material_at_invoice_price=move[str(d)]['MATERIAL_INVENTORY']==10*x and all(move[str(day)]['MATERIAL_INVENTORY']==0 for day in days[1:]),
                fg_on_goods_days=all(move[k]['FG_INVENTORY']==v*x for k,v in fg.items()) if flow not in('CONVERSION',)
                    else move[str(d2)]['FG_INVENTORY']==10*x and move[str(d)]['FG_INVENTORY']==0,
                cogs_on_sale_days=all(move[k]['COGS']==v*x for k,v in cogs.items()),
                wip_po_never_negative=all(v>=0 for v in wip_po.values()),
                wip_po_correction_zero_each_day=all(move[str(day)]['WIP']==0 for day in days),
                no_negative_daily_inventory=negative==[])
    status='PASS' if all(checks.values()) else ('COUNTEREXAMPLE' if not az_installed(cur) else 'FAIL')
    return dict(status=status,flow=flow,price=price,receipt_day=str(d),checks=checks,fixture=fixture,
                daily_move={k:{kk:str(vv) for kk,vv in v.items()} for k,v in move.items()},wip_po={k:str(v) for k,v in wip_po.items()},
                negative_blockers=negative,invoice=response,quiet=[quiet,quiet_fixture])


def cases(cur,today):
    return [('AZ:ONE_CUT_LOWER',lambda:material_case(cur,today,'8.25',[(1,10)])),
            ('AZ:ONE_CUT_HIGHER',lambda:material_case(cur,today,'10.70',[(1,10)])),
            ('AZ:TWO_CUT_DAYS_LOWER',lambda:material_case(cur,today,'8.25',[(1,5),(2,5)])),
            ('AZ:TWO_CUT_DAYS_KIRITIMATI',lambda:material_case(cur,today,'10.70',[(1,4),(2,6)],zone='Pacific/Kiritimati')),
            ('AZ:INVOICE_AFTER_CUT',lambda:material_case(cur,today,'8.25',[(1,10)],invoice_offset=2)),
            ('AZ:CLOSED_RECEIPT_OPEN_CUT',lambda:material_case(cur,today,'8.25',[(1,10)],closed=0)),
            ('AZ:CLOSED_THROUGH_CUT',lambda:material_case(cur,today,'8.25',[(1,10)],closed=1)),
            ('AZ:ADJUSTMENT_AFTER_RECEIPT',lambda:material_case(cur,today,'8.25',[(2,8)],adjustments=[(1,2)])),
            ('AZ:ADJUSTMENT_CLOSED_RECEIPT',lambda:material_case(cur,today,'8.25',[(2,8)],adjustments=[(1,2)],closed=0)),
            ('AZ:SALE_AFTER_GOODS_DAY',lambda:sale_after_goods(cur,today,'8.25')),
            ('AZ:MULTI_CUT_HIGHER',lambda:multi_cut(cur,today,'10.70')),
            ('AZ:MULTI_CUT_LOWER',lambda:multi_cut(cur,today,'8.25')),
            ('AZ:WRITE_OFF_AFTER_LOT_HIGHER',lambda:write_off(cur,today,'10.70')),
            ('AZ:WRITE_OFF_AFTER_LOT_LOWER',lambda:write_off(cur,today,'8.25')),
            ('AZ:SALE_THEN_RETURN',lambda:goods_flow(cur,today,'10.70','RETURN')),
            ('AZ:SALE_REVERSED_BEFORE_INVOICE',lambda:goods_flow(cur,today,'8.25','REVERSED')),
            ('AZ:CONVERSION_AFTER_LOT',lambda:goods_flow(cur,today,'10.70','CONVERSION')),
            ('AZ:CONVERSION_THEN_SALE',lambda:goods_flow(cur,today,'10.70','CONVERSION_SALE')),
            ('AZ:QC_REVERSED_AND_REDONE',lambda:goods_flow(cur,today,'8.25','QC_REDO')),
            ('AZ:BATCH_ACROSS_DAYS_HIGHER',lambda:multi_cut(cur,today,'10.70',batch=True)),
            ('AZ:BATCH_ACROSS_DAYS_LOWER',lambda:multi_cut(cur,today,'8.25',batch=True)),
            ('AZ:CONTRACTOR_AFTER_LOT_HIGHER',lambda:contractor_after_lot(cur,today,'10.70')),
            ('AZ:CONTRACTOR_AFTER_LOT_LOWER',lambda:contractor_after_lot(cur,today,'8.25')),
            ('AZ:BATCH_PARTNER_PO',lambda:batch_partner(cur,today,'10.70')),
            ('AZ:INVOICE_BEFORE_RECEIPT_LOWER',lambda:invoice_before_receipt(cur,today,'8.25')),
            ('AZ:COST_CORRECTION_BEFORE_RECEIPT_LOWER',lambda:cost_correction_before_receipt(cur,today,'8.25'))]


def run(phase):
    assert os.environ.get('CP6_AR_CONFIRM')=='cp6_rollback' and os.environ.get('CP6_DATABASE_CONTAINER')=='supabase_db_cp5-local'
    r1.OUT=OUT
    report=dict(status='INCOMPLETE',label=LABEL,phase=phase,source=r1.source(),production_go=False,independent_acceptance=False,release_evidence=False)
    r1.save('RESULT_'+phase.upper(),report)
    primary=None
    try:
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:prior.verified(cur,'AN');primary=boundary.snapshot(cur)
        r1.writer.install_at()
        control_url=os.environ['CP6_ADMISSION_CONTROL_PGURL']
        report['au_install']=awp.au_runtime.change('install',boundary.PG,control_url)['status']
        report['av_install']=awp.av_runtime.change('install',boundary.PG,control_url)['status']
        report['aw_install']=awp.install_aw();report['ax_install']=axp.install_ax();report['ay_install']=ayp.install_ay();verify=ayp.ay_verified
        if phase=='after':report['az_install']=install_az();verify=az_verified
        r1.save('RESULT_'+phase.upper(),report)
        print(json.dumps(dict(az_probe_setup={k:report.get(k) for k in ('au_install','av_install','ay_install','az_install')}),default=str),flush=True)
        group=r1.group('AZ_CASES_'+phase.upper(),cases,verify)
        report['az_cases']={k:group[k] for k in ('status','counts')}
        report['status']='REVIEW_COMPLETE' if group['status']!='INCOMPLETE' else 'INCOMPLETE'
    except Exception as exc:report.update(status='INCOMPLETE',error=str(exc),traceback=traceback.format_exc())
    finally:
        subprocess.run(['docker','exec','supabase_db_cp5-local','dropdb','-U','supabase_admin','--if-exists','--force','--maintenance-db=template1','cp6_rollback'],check=True)
        with psycopg.connect(boundary.PRIMARY_ADMIN) as conn,conn.cursor() as cur:
            prior.verified(cur,'AN');report['primary_unchanged']=primary is not None and boundary.snapshot(cur)==primary
            report['clone_remaining']=cur.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0]
        if not report['primary_unchanged'] or report['clone_remaining']:report['status']='INCOMPLETE'
        r1.save('RESULT_'+phase.upper(),report)
    print(json.dumps(dict(az_probe_phase=phase,**{k:v for k,v in report.items() if k!='source'}),default=str),flush=True)
    assert report['status']=='REVIEW_COMPLETE',report.get('error','AZ_PROBE_INCOMPLETE')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=('before','after'),required=True)
    run(parser.parse_args().phase)
