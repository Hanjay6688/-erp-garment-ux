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
FUNCTIONS=('erp.sync_material_cost_revaluation(uuid)','erp._cp6_sync_material_adjustment_revaluation(uuid,uuid)')


def dev_source(signature):
    """The body of one AZ function exactly as the committed dev file defines it."""
    name=signature.split('(')[0]
    text=AZ_SQL.read_text()
    head=text.index('CREATE OR REPLACE FUNCTION '+name+'(')
    start=text.index('AS $function$',head)+len('AS $function$');end=text.index('$function$;',start)
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


def cut(cur,fx,day,qty,remaining,hour=8):
    """One cutting group of `qty` units of the fixture roll for a new PO on `day` (ordinary cutting RPC)."""
    prod=chain.production
    api.admin(cur)
    po=uuid.uuid4()
    cur.execute("""insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)
      values(%s,%s,%s,%s,'CUTTING','CUTTING',%s,'AZ probe cutting day')""",(po,'AZ-PO-'+str(po),prod.MODEL,qty,prod.at(day,7)))
    payload=dict(action='SAVE_DRAFT',po_id=po,pattern_id=prod.PATTERN,source_location_id=fx['location'],cut_at=prod.at(day,hour),
                 change_reason='AZ probe cutting of %s units'%qty,size_slots=[dict(slot_no=1,size_id=prod.base.SIZE,drawing_no=1)],
                 rolls=[dict(roll_id=fx['roll'],qty_issued=qty,qty_consumed=qty,qty_reported_remaining=remaining,yields=[dict(slot_no=1,qty_pcs=qty)])])
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
        if kind=='CUT':pos.append(cut(cur,fx,d+timedelta(days=offset),qty,left))
        else:adjs.append(adjust(cur,fx,d+timedelta(days=offset),qty))
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
                negative_blockers=negative,closed_before=closed_before,invoice=response,quiet=quiet)


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
            ('AZ:SALE_AFTER_GOODS_DAY',lambda:sale_after_goods(cur,today,'8.25'))]


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
