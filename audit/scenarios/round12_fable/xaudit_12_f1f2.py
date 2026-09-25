"""XA12 (Fable, round 12 pre-BC): independent reproduction of the writer's two 'pre-existing' findings named in commit 7c9d00a
(BC probe), on the product WITHOUT BC (the release package is byte-identical between 4c61aca and 7c9d00a; BC lives only in
supabase/dev and is not installed by cp6-auditor-scenario).
  F2: erp.run_v255_material_cost_integrity_checks() row MATERIAL_RECOST_GL_STATE_DRIFT reports drift after ordinary native
      flows whose books are exact (writer: stale per-movement check predating v2.6.20t / BA W8). The writer's BC probe EXCLUDES
      this row from its own findings delta. Oracle here: the books must be exact (M:6632 totals, M:835 per-document rounding,
      owner T3 option A); a detector that reports ERROR/CRITICAL on exact books is a defect of the detector (pre-existing),
      a detector that is right means real drift. Either is a COUNTEREXAMPLE on this pre-BC product; PASS only when the books
      are exact and the detector stays silent.
  F1: erp.run_v265_gudang_write_integrity_checks() row contractor_issue_price_provenance_gap (CRITICAL) counts a mandor note
      line priced by the owner-decided manual retail price (M:1066 / ACC-DEC02). Oracle: a valid manual-price line is not a
      provenance gap. COUNTEREXAMPLE when the count rises for such a line.
Vocabulary: PASS / COUNTEREXAMPLE / INCOMPLETE (no FAIL: this product predates BC; the run stays green so the evidence is kept).
"""
from datetime import timedelta
from decimal import Decimal,ROUND_HALF_UP
import json,traceback,uuid
import psycopg
import cp6_aw_probe as awp
import cp6_az_probe as azp
api=awp.api;chain=awp.chain;prod=chain.production
D=Decimal
DRIFT='MATERIAL_RECOST_GL_STATE_DRIFT';GAP='contractor_issue_price_provenance_gap'
V255='run_v255_material_cost_integrity_checks';V265='run_v265_gudang_write_integrity_checks'
def cents(v):return D(str(v)).quantize(D('0.01'),rounding=ROUND_HALF_UP)
def one(cur,sql,*args):
    api.admin(cur);return cur.execute(sql,args).fetchone()[0]
def detector(cur,fn):
    api.admin(cur)
    return {r[0]:dict(severity=str(r[1]),count=int(r[2] or 0),details=str(r[3])[:300]) for r in cur.execute('select check_name,severity,issue_count,details from erp.'+fn+'()').fetchall()}
def delta(b,a):
    return {k:a[k]['count']-b.get(k,{}).get('count',0) for k in a if a[k]['count']-b.get(k,{}).get('count',0)!=0}
def flagged(d):return {k:v['count'] for k,v in d.items() if v['count'] and v['severity'].upper() in('ERROR','CRITICAL')}
def gl(cur,key):return D(str(one(cur,'select coalesce(sum(debit-credit),0) from erp.journal_lines where account_id=erp.account_id(%s)',key)))
def subledger(cur):return D(str(one(cur,'select round(coalesce(sum(cached_stock_qty*moving_average_cost),0),2) from erp.materials')))
def material_state(cur,material):
    api.admin(cur)
    q,c,mac=cur.execute('select coalesce((select sum(qty_signed) from erp.material_stock_movements where material_id=m.id),0),m.cached_stock_qty,m.moving_average_cost from erp.materials m where m.id=%s',(material,)).fetchone()
    ev=cur.execute('select count(*) from erp.material_cost_revaluation_events where material_id=%s',(material,)).fetchone()[0]
    return dict(raw_qty=str(q),cached_qty=str(c),moving_average_cost=str(mac),revaluation_events=int(ev))
def prosrc(cur,fn):return one(cur,"select p.prosrc from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='erp' and p.proname=%s",fn) or ''
def excerpt(src,needle,before=1400,after=1400):
    i=src.find(needle);return None if i<0 else src[max(0,i-before):i+after]
def bc_absent(cur):
    return dict(marker=not one(cur,"select exists(select 1 from erp.schema_migrations where version='v2.6.20bc')"),
                service_facade=not one(cur,"select exists(select 1 from pg_proc where proname='erp_save_accessory_service_action_v1')"),
                issue_facade_present=bool(one(cur,"select exists(select 1 from pg_proc where proname='erp_save_accessory_issue_action_v1')")))
def snapshot(cur):return dict(v255=detector(cur,V255),gl_material=gl(cur,'MATERIAL_INVENTORY'),gl_wip=gl(cur,'WIP'),sub=subledger(cur))

# ---------------------------------------------------------------- fixtures (ordinary purchase RPCs, as xaudit_8)
def receipt(cur,day,price,kind,first=None,qty=1):
    prior=prod.prior;api.admin(cur);prod.zone(cur,'Asia/Jakarta')
    if first:material,location=first['material'],first['location']
    else:
        material=prior.clone_material(cur,'xa12');location=uuid.uuid4()
        cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,'XA12 raw warehouse','RAW_MATERIAL_WAREHOUSE',true)",(location,'XA12-LOC-'+location.hex[:20]))
    line=dict(material_id=material,qty=qty,unit_price=price,rolls=[dict(roll_number='XA12-ROLL-'+str(uuid.uuid4()),qty=qty)])
    payload=dict(purchase_number='XA12-PUR-'+str(uuid.uuid4()),supplier_id=prior.BASE_SUPPLIER,location_id=location,physical_at=prod.at(day,10),change_reason='XA12 receipt',lines=[line])
    if kind=='DIRECT':line.update(price_state='FINAL',price_source='SUPPLIER_INVOICE');payload['supplier_invoice_number']='XA12-INV-'+uuid.uuid4().hex[:12]
    else:line.update(price_state='ESTIMATED',price_source='MANUAL_ESTIMATE')
    draft=prod.rpc(cur,'erp.save_material_purchase_draft_v2',payload);purchase=uuid.UUID(draft['purchase_id'])
    cur.execute('select erp.post_material_purchase_v2(%s,%s,%s,%s)',(purchase,uuid.uuid4(),int(draft['row_version']),'XA12 receipt post'));api.admin(cur)
    item,roll=cur.execute('select i.id,r.id from erp.material_purchase_items i join erp.material_rolls r on r.purchase_item_id=i.id where i.purchase_id=%s',(purchase,)).fetchone()
    return dict(material=material,purchase=purchase,item=item,location=location,roll=roll,qty=qty)
def late_invoice(cur,fx,day,price):
    api.admin(cur)
    version=int(cur.execute('select row_version from erp.material_purchase_headers where id=%s',(fx['purchase'],)).fetchone()[0])
    payload=dict(purchase_id=fx['purchase'],supplier_invoice_number='XA12-LINV-'+uuid.uuid4().hex[:12],invoice_date=str(day),received_at=prod.at(day,15),reason='XA12 late invoice at '+price,lines=[dict(purchase_item_id=fx['item'],qty_invoiced=fx['qty'],final_unit_price=price)])
    prod.zone(cur,'Asia/Jakarta');r=prod.rpc(cur,'erp.finalize_material_purchase_invoice_v2',payload,uuid.uuid4(),version);api.admin(cur);return r
def queue(cur):
    prod.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');api.admin(cur)
def classify(books_exact,drift_delta):
    if drift_delta and books_exact:return 'COUNTEREXAMPLE','detector reports MATERIAL_RECOST_GL_STATE_DRIFT on exact books: pre-existing detector defect (writer F2 CONFIRMED)'
    if drift_delta:return 'COUNTEREXAMPLE','detector reports drift AND the books are not exact: real drift (writer F2 exact-books claim REFUTED for this path)'
    if books_exact:return 'PASS','books exact, detector silent (F2 not reproduced by this path)'
    return 'COUNTEREXAMPLE','books not exact while the detector stays silent'
def f2_result(cur,base,materials,expected_wip=None,expected_material=None):
    now=snapshot(cur)
    d_gl=now['gl_material']-base['gl_material'];d_sub=now['sub']-base['sub'];d_wip=now['gl_wip']-base['gl_wip']
    checks=dict(gl_material_equals_subledger_exact=d_gl==d_sub,gl_material_within_1_cent=abs(d_gl-d_sub)<=D('0.01'))
    if expected_wip is not None:checks['wip_total_equals_documents_rounded']=d_wip==expected_wip
    if expected_material is not None:checks['material_value_expected']=d_gl==expected_material
    books_exact=all(checks.values())
    dd=delta(base['v255'],now['v255']);drift=dd.get(DRIFT,0)
    status,why=classify(books_exact,drift)
    return dict(status=status,classification=why,checks=checks,gl_material_delta=str(d_gl),subledger_delta=str(d_sub),wip_delta=str(d_wip),
                detector_delta=dd,drift_row=now['v255'].get(DRIFT),flagged_after=flagged(now['v255']),materials=[material_state(cur,m) for m in materials])

# ---------------------------------------------------------------- F2 paths
def f2_stacked(cur,today,n,p0,p1):
    """n receipts of 1 unit at p0 (ESTIMATED) on d, one cut per receipt to its own PO on d+1 (stock pooled when cut), each
    document invoiced at p1 on d+2, queue. Owner T3 option A: WIP total = n x cents(p1); material qty 0 value 0."""
    d=today-timedelta(days=5);awp.boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    base=snapshot(cur);fxs=[];pos=[]
    for i in range(n):fxs.append(receipt(cur,d,p0,'INVOICE',fxs[0] if fxs else None))
    for fx in fxs:pos.append(azp.cut(cur,fx,d+timedelta(days=1),1,8+len(pos)))
    for fx in fxs:late_invoice(cur,fx,d+timedelta(days=2),p1)
    queue(cur)
    r=f2_result(cur,base,[fxs[0]['material']],expected_wip=cents(p1)*n,expected_material=D('0'))
    r.update(n=n,p0=p0,p1=p1,path='n stacked receipts, cut pooled, late invoices');return r
def f2_adjust_then_invoice(cur,today,qty,adj,p0,p1):
    """One receipt of `qty` units at p0 (ESTIMATED) on d, a native posted count correction of -adj units on d+1
    (erp.post_material_adjustment_v2), the late invoice at p1 on d+2, queue. Books: remaining (qty-adj) units at p1, the
    document rounded once (M:835); GL MATERIAL_INVENTORY delta = subledger delta."""
    d=today-timedelta(days=5);awp.boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    base=snapshot(cur);fx=receipt(cur,d,p0,'INVOICE',qty=qty)
    azp.adjust(cur,fx,d+timedelta(days=1),adj)
    late_invoice(cur,fx,d+timedelta(days=2),p1);queue(cur)
    r=f2_result(cur,base,[fx['material']])
    r.update(qty=qty,adjusted=-adj,p0=p0,p1=p1,path='receipt, native adjustment, late invoice');return r
def f2_control(cur,today,qty,p0,p1):
    """Control: one receipt, late invoice only (no adjustment, no cut)."""
    d=today-timedelta(days=5);awp.boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    base=snapshot(cur);fx=receipt(cur,d,p0,'INVOICE',qty=qty);late_invoice(cur,fx,d+timedelta(days=2),p1);queue(cur)
    r=f2_result(cur,base,[fx['material']],expected_material=cents(D(p1)*qty))
    r.update(qty=qty,p0=p0,p1=p1,path='receipt, late invoice (control)');return r

# ---------------------------------------------------------------- F1: manual-price note line vs provenance detector
def f1_manual_note(cur,today):
    api.admin(cur);code='XA12'+uuid.uuid4().hex[:10];prod.zone(cur,'Asia/Jakarta')
    awp.boundary.historical.prior.set_open_period(cur,today-timedelta(days=12))
    pcs=one(cur,"select unit_code from erp.uom_definitions where upper(unit_code)='PCS' and dimension='COUNT' and is_active")
    cat=one(cur,"insert into erp.accessory_categories(category_code,category_name,base_uom_code,is_active) values(%s,'XA12 kancing',%s,true) returning id",code,pcs)
    mat=one(cur,"insert into erp.materials(material_sku,material_name,material_type,unit_code,accessory_category_id) values(%s,'XA12 kancing','ACCESSORY',%s,%s) returning id",code,pcs,cat)
    loc=one(cur,"insert into erp.locations(location_code,location_name,location_type,is_active) values(%s,'XA12 W','RAW_MATERIAL_WAREHOUSE',true) returning id",code+'W')
    mandor=one(cur,"insert into erp.contractors(contractor_code,contractor_name,contractor_type,attendance_required,is_active) values(%s,'XA12 mandor','MANDOR',false,true) returning id",code)
    received=today-timedelta(days=6)
    payload=dict(purchase_number=code+'P',supplier_id=prod.prior.BASE_SUPPLIER,location_id=loc,physical_at=prod.at(received,9),change_reason='XA12 fixture receipt',
                 lines=[dict(material_id=mat,qty=100,unit_price='2.00',price_state='ESTIMATED',price_source='MANUAL_ESTIMATE')])
    draft=prod.rpc(cur,'erp.save_material_purchase_draft_v2',payload);purchase=uuid.UUID(draft['purchase_id'])
    cur.execute('select erp.post_material_purchase_v2(%s,%s,%s,%s)',(purchase,uuid.uuid4(),int(draft['row_version']),'XA12 fixture post'));api.admin(cur)
    before=detector(cur,V265);present=bc_absent(cur)['issue_facade_present']
    route=None;err=None;item=None
    if present:
        route='public.erp_save_accessory_issue_action_v1 POST mode MANUAL'
        cur.execute("select set_config('request.jwt.claims',%s,true)",(json.dumps(dict(sub=api.base.OPERATOR_AUTH,role='authenticated')),))
        cur.execute('set local session authorization authenticated')
        try:
            res=cur.execute('select public.erp_save_accessory_issue_action_v1(%s,%s::jsonb,%s)',('POST',json.dumps(dict(number=code+'N',contractor_id=str(mandor),location_id=str(loc),po_id=None,
                physical_at=prod.at(today-timedelta(days=1),8),notes='XA12 note',reason='XA12 note',items=[dict(material_id=str(mat),qty='2',mode='MANUAL',manual_price='3.00')]),default=str),str(uuid.uuid4()))).fetchone()[0]
            api.admin(cur);item=cur.execute('select id,manual_retail_unit_price,accessory_price_version_id,unit_sale_price_snapshot from erp.contractor_material_issue_items where issue_id=%s',(res['id'],)).fetchone()
        except psycopg.Error as exc:
            err=dict(sqlstate=exc.sqlstate,message=(exc.diag.message_primary or str(exc))[:400]);api.admin(cur)
    if item is None:
        return dict(status='INCOMPLETE',route=route,refusal=err,issue_facade_present=present,note='no route to a posted manual-price note line on this product')
    after=detector(cur,V265);dd=delta(before,after);gap=dd.get(GAP,0)
    src=prosrc(cur,V265);detector_ignores_manual='manual_retail_unit_price' in src
    return dict(status='COUNTEREXAMPLE' if gap>0 else 'PASS',route=route,gap_delta=gap,detector_delta=dd,gap_row=after.get(GAP),
                item=dict(manual_retail_unit_price=str(item[1]),accessory_price_version_id=str(item[2]),unit_sale_price_snapshot=str(item[3])),
                detector_mentions_manual_retail_unit_price=detector_ignores_manual,
                classification='valid manual-price note line counted as CRITICAL provenance gap (writer F1 CONFIRMED pre-existing)' if gap>0 else 'manual-price line not flagged (writer F1 REFUTED on this product)')

# ---------------------------------------------------------------- cases
def cases(cur,today):
    out={}
    def run(cid,fn):
        try:out[cid]=fn()
        except Exception as exc:out[cid]=dict(status='INCOMPLETE',error=str(exc)[:600],trace=traceback.format_exc()[-1500:])
    def absent():
        a=bc_absent(cur);ok=a['marker'] and a['service_facade']
        return dict(status='PASS' if ok else 'FAIL',bc=a,note='this run is the product without BC (release package identical 4c61aca..7c9d00a)')
    run('XA12:BC_ABSENT',absent)
    def source():
        s255=prosrc(cur,V255);s265=prosrc(cur,V265)
        return dict(status='PASS',v255_len=len(s255),v265_len=len(s265),drift_excerpt=excerpt(s255,DRIFT),gap_excerpt=excerpt(s265,GAP,700,700),
                    baseline_flagged_v255=flagged(detector(cur,V255)),baseline_flagged_v265=flagged(detector(cur,V265)))
    run('XA12:DETECTOR_SOURCE_AND_BASELINE',source)
    run('XA12:F2_CONTROL_LATE_INVOICE_ONLY',lambda:f2_control(cur,today,10,'10.00','10.005'))
    run('XA12:F2_ADJUST_THEN_LATE_INVOICE',lambda:f2_adjust_then_invoice(cur,today,10,3,'10.00','10.005'))
    run('XA12:F2_ADJUST_THEN_LATE_INVOICE_EVEN',lambda:f2_adjust_then_invoice(cur,today,10,3,'10.00','2.10'))
    run('XA12:F2_STACKED_INVOICE_N3',lambda:f2_stacked(cur,today,3,'10.00','10.005'))
    run('XA12:F2_STACKED_INVOICE_N10',lambda:f2_stacked(cur,today,10,'10.00','10.005'))
    run('XA12:F1_MANUAL_PRICE_NOTE_LINE',lambda:f1_manual_note(cur,today))
    return out
