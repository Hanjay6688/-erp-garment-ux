"""AUDITOR SCENARIO — DATE FAMILY 1 (independent auditor, blind phase 1).
Oracle source: contract ERP-DEC01 (Master Pulih 1057-1062 / Perubahan 999-1004): a cost/invoice correction on an OPEN
period follows the INVOICE DATE, consistently across inventory value, journals, WIP, FG, COGS, dated reports and
readiness; a CLOSED period keeps the existing controlled-adjustment path (Master 1061). Fixtures reuse the writer's data
generators only (estimated receipt of 10 units at 10 on d=today-3, ordinary cutting RPC, ordinary invoice RPC); every
expected value here is computed by the auditor, never taken from writer assertions.
Statuses: PASS / COUNTEREXAMPLE / INCOMPLETE. For the contract-ambiguous shape (invoice dated before the physical
cut/goods day) both readings are evaluated and reported; status follows the contract as written (STRICT)."""
from datetime import timedelta
from decimal import Decimal
import json,traceback,uuid
import cp6_aw_probe as awp
import cp6_az_probe as azp
api,boundary,chain=awp.api,awp.boundary,awp.chain
KEYS=azp.KEYS
D=lambda v:Decimal(str(v))
C=None

def new_journals(cur,old_ids):
    api.admin(cur)
    return [dict(id=str(r[0]),source=r[1],economic=str(r[2]),transaction=str(r[3]),status=r[4]) for r in cur.execute(
        "select id,source_type,economic_date,transaction_date,status from erp.journal_entries where id<>all(%s::uuid[]) order by transaction_date,source_type",
        ([str(i) for i in old_ids],)).fetchall()]

def reval_events(cur,material,old):
    api.admin(cur)
    return [dict(id=str(r[0]),effective=str(r[1]),delta=str(r[2]),counterpart=r[3],po=str(r[4]) if r[4] else None,economic=str(r[5]),transaction=str(r[6])) for r in cur.execute(
        """select e.id,e.effective_date,e.delta_amount,e.counterpart_mapping_key,e.po_id,j.economic_date,j.transaction_date
           from erp.material_cost_revaluation_events e join erp.journal_entries j on j.id=e.journal_entry_id
           where e.material_id=%s order by j.transaction_date,e.id""",(material,)).fetchall() if r[0] not in old]

def moves(before,after,days):
    return {str(day):{k:str(D(after[str(day)][k])-D(before[str(day)][k])) for k in KEYS} for day in days}

def negative_blocker(cur,day):
    pre=awp.preflight(cur,day)
    return dict(status=pre and pre['status'],negative=[b for b in (pre['blockers'] if pre else []) if b['code']=='GL_INVENTORY_NEGATIVE_ASOF'],codes=awp.codes(pre))

def material_shape(cur,today,price,cuts,invoice_offset,closed=None):
    """Fixture as the writer generates it (material_case sequence), oracle by the auditor."""
    prod=chain.production
    d=today-timedelta(days=3);E=d+timedelta(days=invoice_offset)
    days=[d+timedelta(days=i) for i in range(4)]
    boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    awp.quiet_seed(cur,d,today-timedelta(days=1),exclude=[prod.CONTRACTOR])
    fx=prod.estimated_receipt(cur,today)
    if fx['purchase_day']!=d:return dict(status='INCOMPLETE',error='purchase day %s != d %s'%(fx['purchase_day'],d))
    pos=[]
    for offset,qty in sorted(cuts):pos.append(azp.cut(cur,fx,d+timedelta(days=offset),qty))
    awp.quiet_seed(cur,d,today-timedelta(days=1))
    closed_through=None;closed_before=None
    if closed is not None:
        closed_through=d+timedelta(days=closed)
        ready=awp.preflight(cur,closed_through)
        if ready is None or ready['status']!='READY':return dict(status='INCOMPLETE',error='fixture not READY before close',blockers=awp.blockers_brief(ready))
        closed_before=awp.close(cur,closed_through,'auditor close before the late invoice')
        if closed_before[0]!='ACCEPTED':return dict(status='INCOMPLETE',error='fixture close refused',closed_before=closed_before)
    before=azp.ledger_days(cur,days,pos)
    api.admin(cur)
    old_ev={r[0] for r in cur.execute('select id from erp.material_cost_revaluation_events where material_id=%s',(fx['material'],)).fetchall()}
    old_j={r[0] for r in cur.execute('select id from erp.journal_entries').fetchall()}
    response=azp.invoice(cur,fx,today,price,E)
    after=azp.ledger_days(cur,days,pos)
    ev=reval_events(cur,fx['material'],old_ev);journals=new_journals(cur,old_j)
    x=D(price)-10;mv=moves(before,after,days)
    cut_day={str(p):d+timedelta(days=o) for p,(o,q) in zip(pos,sorted(cuts))}
    cut_units={str(p):q for p,(o,q) in zip(pos,sorted(cuts))}
    in_stock=lambda day:10-sum(q for o,q in cuts if d+timedelta(days=o)<=day)
    total=sum(D(e['delta']) for e in ev)
    obs=dict(receipt_day=str(d),invoice_date=str(E),price=price,x=str(x),cuts=[(str(d+timedelta(days=o)),q) for o,q in cuts],closed_through=str(closed_through) if closed_through else None,
             closed_before=closed_before,new_revaluation_events=ev,new_journals=journals,daily_move=mv,
             wip_po_after={day:after[day]['WIP_PO'] for day in mv},negative=negative_blocker(cur,today))
    inv_j=[j for j in journals if j['source']=='MATERIAL_SUPPLIER_INVOICE']
    checks={}
    checks['supplier_invoice_journal_created']=bool(inv_j)
    checks['revaluation_total_equals_10x']=total==10*x or (closed is not None and E<=closed_through and total==10*x)  # conservation of the whole correction
    if closed is None or E>closed_through:
        # OPEN period: contract = invoice date for every leg.
        checks['supplier_invoice_dated_E']=all(j['economic']==str(E) and j['transaction']==str(E) for j in inv_j)
        checks['STRICT_every_revaluation_dated_E']=bool(ev) and all(e['economic']==str(E) and e['transaction']==str(E) and e['effective']==str(E) for e in ev)
        checks['days_before_E_unchanged']=all(all(D(v)==0 for v in mv[str(day)].values()) for day in days if day<E)
        checks['material_inventory_from_E_equals_x_times_units_in_stock']=all(D(mv[str(day)]['MATERIAL_INVENTORY'])==x*in_stock(day) for day in days if day>=E)
        checks['no_negative_daily_inventory_blocker']=obs['negative']['negative']==[]
        checks['wip_never_negative_any_day']=all(D(v)>=0 for day in days for v in after[str(day)]['WIP_PO'].values())
        # Informational second reading (writer-quoted 24 Sep rule, NOT contract): WIP leg on max(E, cut day).
        physical=bool(ev) and all(e['transaction']==str(max(E,cut_day.get(e['po'],E))) for e in ev if e['counterpart']=='WIP')
        obs['reading_PHYSICAL_max_E_cutday_matches']=physical
        ambiguous=any(cd>E for cd in cut_day.values())
        obs['contract_shape']='UNAMBIGUOUS (invoice on/after every cut)' if not ambiguous else 'AMBIGUOUS (invoice dated before a cut): contract says invoice date, which would date WIP before the cut exists; DECISION_MISSING in contract'
    else:
        # CLOSED period: contract keeps the existing controlled path; the closed days must not move and nothing may be posted inside the closed period.
        checks['no_new_journal_posted_inside_closed_period']=all(j['transaction']>str(closed_through) for j in journals)
        checks['closed_days_ledger_unchanged']=all(all(D(v)==0 for v in mv[str(day)].values()) for day in days if day<=closed_through)
        checks['economic_date_E_retained_on_events']=bool(ev) and all(e['economic']==str(E) for e in ev)
        checks['correction_visible_by_today']=D(mv[str(days[-1])]['MATERIAL_INVENTORY'])+D(mv[str(days[-1])]['WIP'])+D(mv[str(days[-1])]['FG_INVENTORY'])+D(mv[str(days[-1])]['COGS'])==10*x
        checks['no_negative_daily_inventory_blocker']=obs['negative']['negative']==[]
    ok=all(checks.values())
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',checks=checks,observed=obs,
                expected='ERP-DEC01 (Master 1057-1062): open period -> every leg on the invoice date E; closed period -> existing controlled adjustment, closed days untouched')

def goods_shape(cur,today,price,invoice_on_goods_day):
    """AA recipe (10 units at 10 on d; 5 FG on d+1, 2 sold on d+1) then a late invoice dated d+1 (unambiguous) or d (ambiguous)."""
    prod=chain.production
    d=today-timedelta(days=3);d2=d+timedelta(days=1);E=d2 if invoice_on_goods_day else d
    days=[d+timedelta(days=i) for i in range(4)]
    boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    awp.quiet_seed(cur,d,d2,exclude=[prod.CONTRACTOR])
    fx=prod.estimated_receipt(cur,today)
    if fx['purchase_day']!=d:return dict(status='INCOMPLETE',error='purchase day mismatch')
    prod.partial_production(awp.OrdinaryDraftCursor(cur),fx);api.admin(cur)
    awp.quiet_seed(cur,d,d2)
    ready=awp.preflight(cur,d2)
    if ready is None or ready['status']!='READY':return dict(status='INCOMPLETE',error='fixture not READY before invoice',blockers=awp.blockers_brief(ready))
    pos=[fx['po']]
    before=azp.ledger_days(cur,days,pos)
    api.admin(cur)
    old_j={r[0] for r in cur.execute('select id from erp.journal_entries').fetchall()}
    old_h={r[0] for r in cur.execute('select id from erp.po_hpp_gl_events where po_id=%s',(fx['po'],)).fetchall()}
    version=int(cur.execute('select row_version from erp.material_purchase_headers where id=%s',(fx['purchase'],)).fetchone()[0])
    payload=dict(purchase_id=fx['purchase'],supplier_invoice_number='AUD-'+uuid.uuid4().hex[:12],invoice_date=E,received_at=prod.at(today-timedelta(days=1),15),
                 reason='auditor late supplier invoice at '+price,lines=[dict(purchase_item_id=fx['item'],qty_invoiced=10,final_unit_price=price)])
    prod.zone(cur,'Asia/Jakarta')
    response=prod.rpc(cur,'erp.finalize_material_purchase_invoice_v2',payload,uuid.uuid4(),version)
    api.admin(cur);prod.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');api.admin(cur)
    after=azp.ledger_days(cur,days,pos)
    journals=new_journals(cur,old_j)
    hpp=[dict(id=str(r[0]),effective=str(r[1]),fg=str(r[2]),cogs=str(r[3]),other=str(r[4])) for r in cur.execute(
        'select id,effective_date,fg_delta,cogs_delta,other_delta from erp.po_hpp_gl_events where po_id=%s order by effective_date,id',(fx['po'],)).fetchall() if r[0] not in old_h]
    x=D(price)-10;mv=moves(before,after,days);last=mv[str(days[-1])]
    conserved=sum(D(last[k]) for k in KEYS)
    pre_today=negative_blocker(cur,today);pre_d2=awp.preflight(cur,d2)
    close_after=awp.close(cur,d2,'auditor close after the late invoice')
    checks=dict(
        supplier_invoice_dated_E=any(j['source']=='MATERIAL_SUPPLIER_INVOICE' and j['economic']==str(E)==j['transaction'] for j in journals),
        correction_conserved_in_four_accounts_by_today=conserved==10*x,
        STRICT_every_new_journal_dated_E=all(j['transaction']==str(E) for j in journals),
        days_before_E_unchanged=all(all(D(v)==0 for v in mv[str(day)].values()) for day in days if day<E),
        no_negative_daily_inventory_blocker=pre_today['negative']==[],
        readiness_goods_day_ready_after_invoice=bool(pre_d2) and pre_d2['status']=='READY',
        close_goods_day_accepted_after_invoice=close_after[0]=='ACCEPTED')
    ok=all(checks.values())
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',checks=checks,
                observed=dict(receipt_day=str(d),goods_and_sale_day=str(d2),invoice_date=str(E),price=price,x=str(x),daily_move=mv,new_journals=journals,new_hpp_events=hpp,
                              conserved_by_today=str(conserved),negative=pre_today,readiness_d2=pre_d2 and pre_d2['status'],readiness_d2_codes=awp.codes(pre_d2),close_after=close_after,
                              contract_shape='UNAMBIGUOUS (invoice on goods/sale day)' if invoice_on_goods_day else 'AMBIGUOUS (invoice before goods day): DECISION_MISSING in contract'),
                expected='ERP-DEC01: every leg (material, WIP, FG, COGS) of the 10x correction dated on invoice date E; readiness consistent; close accepted')

def cases(cur,today):
    global C;C=cur
    def wrap(fn,*a):
        def run():
            try:return fn(cur,today,*a)
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:900],traceback=traceback.format_exc()[-1500:])
        return run
    return [('DATE:OPEN:INVOICE_AFTER_CUT:HIGHER_12',wrap(material_shape,'12',[(0,4)],2)),
            ('DATE:OPEN:INVOICE_AFTER_CUT:LOWER_8',wrap(material_shape,'8',[(0,4)],2)),
            ('DATE:OPEN:TWO_CUTS_INVOICE_LAST_DAY:LOWER_8',wrap(material_shape,'8',[(0,3),(1,4)],2)),
            ('DATE:OPEN:INVOICE_BEFORE_CUT_AMBIGUOUS:LOWER_8',wrap(material_shape,'8',[(1,4)],0)),
            ('DATE:CLOSED:RECEIPT_AND_CUT_CLOSED_INVOICE_IN_CLOSED:HIGHER_12',wrap(material_shape,'12',[(0,4)],0,1)),
            ('DATE:GOODS:INVOICE_ON_GOODS_DAY:LOWER_8',wrap(goods_shape,'8',True)),
            ('DATE:GOODS:INVOICE_ON_GOODS_DAY:HIGHER_12',wrap(goods_shape,'12',True)),
            ('DATE:GOODS:INVOICE_BEFORE_GOODS_AMBIGUOUS:LOWER_8',wrap(goods_shape,'8',False))]
