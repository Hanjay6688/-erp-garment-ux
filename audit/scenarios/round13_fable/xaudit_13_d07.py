"""XA13-D07 (Fable, round 13): the retuned MATERIAL_RECOST_GL_STATE_DRIFT (D07: document level, adjustments read from the v2.6.20t facts)
must stay silent on correct books (covered by xaudit_12_f1f2 in the same round) AND must still fire when a recost record is tampered.
Negative controls (each inside a savepoint, rolled back afterwards; the detector must return to its baseline):
  XA13:D07_NEG_STATE_TAMPER   after 3 stacked receipts, cut, late invoices (books exact): one cutting movement's applied_inventory_delta += 0.05
                              in material_cost_revaluation_state -> the document-level sum no longer matches -> drift row count must rise by 1.
  XA13:D07_NEG_FACT_TAMPER    after receipt, native adjustment, late invoice: the adjustment's material_adjustment_revaluation_facts.ledger_delta
                              amended by +0.05 on one account -> the detector (reading facts) must rise by 1 (or the facts table refuses the write:
                              then INCOMPLETE with the refusal, stated).
  XA13:D07_SILENT_ON_EXACT    the same two flows untampered: drift delta 0 (consistency with xaudit_12_f1f2).
Oracle: owner D07 (OWNER_DECISIONS_CP6_DRAFT.md) — the alarm is retuned, not disabled; a wrong recost must still be reported.
"""
from datetime import timedelta
from decimal import Decimal,ROUND_HALF_UP
import json,traceback,uuid
import psycopg
import cp6_aw_probe as awp
import cp6_az_probe as azp
api=awp.api;chain=awp.chain;prod=chain.production;D=Decimal
DRIFT='MATERIAL_RECOST_GL_STATE_DRIFT';V255='run_v255_material_cost_integrity_checks'
def one(cur,sql,*args):
    api.admin(cur);return cur.execute(sql,args).fetchone()[0]
def drift(cur):
    api.admin(cur);rows={r[0]:int(r[2] or 0) for r in cur.execute('select check_name,severity,issue_count,details from erp.'+V255+'()').fetchall()}
    return rows.get(DRIFT,0)
def receipt(cur,day,price,first=None,qty=1):
    prior=prod.prior;api.admin(cur);prod.zone(cur,'Asia/Jakarta')
    if first:material,location=first['material'],first['location']
    else:
        material=prior.clone_material(cur,'xa13');location=uuid.uuid4()
        cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,'XA13 raw warehouse','RAW_MATERIAL_WAREHOUSE',true)",(location,'XA13-LOC-'+location.hex[:20]))
    line=dict(material_id=material,qty=qty,unit_price=price,rolls=[dict(roll_number='XA13-ROLL-'+str(uuid.uuid4()),qty=qty)],price_state='ESTIMATED',price_source='MANUAL_ESTIMATE')
    payload=dict(purchase_number='XA13-PUR-'+str(uuid.uuid4()),supplier_id=prior.BASE_SUPPLIER,location_id=location,physical_at=prod.at(day,10),change_reason='XA13 receipt',lines=[line])
    draft=prod.rpc(cur,'erp.save_material_purchase_draft_v2',payload);purchase=uuid.UUID(draft['purchase_id'])
    cur.execute('select erp.post_material_purchase_v2(%s,%s,%s,%s)',(purchase,uuid.uuid4(),int(draft['row_version']),'XA13 receipt post'));api.admin(cur)
    item,roll=cur.execute('select i.id,r.id from erp.material_purchase_items i join erp.material_rolls r on r.purchase_item_id=i.id where i.purchase_id=%s',(purchase,)).fetchone()
    return dict(material=material,purchase=purchase,item=item,location=location,roll=roll,qty=qty)
def late_invoice(cur,fx,day,price):
    api.admin(cur);version=int(cur.execute('select row_version from erp.material_purchase_headers where id=%s',(fx['purchase'],)).fetchone()[0])
    payload=dict(purchase_id=fx['purchase'],supplier_invoice_number='XA13-LINV-'+uuid.uuid4().hex[:12],invoice_date=str(day),received_at=prod.at(day,15),reason='XA13 late invoice',lines=[dict(purchase_item_id=fx['item'],qty_invoiced=fx['qty'],final_unit_price=price)])
    prod.zone(cur,'Asia/Jakarta');r=prod.rpc(cur,'erp.finalize_material_purchase_invoice_v2',payload,uuid.uuid4(),version);api.admin(cur);return r
def queue(cur):
    prod.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');api.admin(cur)
def stacked(cur,today,n=3):
    d=today-timedelta(days=5);awp.boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    fxs=[]
    for i in range(n):fxs.append(receipt(cur,d,'10.00',fxs[0] if fxs else None))
    for i,fx in enumerate(fxs):azp.cut(cur,fx,d+timedelta(days=1),1,8+i)
    for fx in fxs:late_invoice(cur,fx,d+timedelta(days=2),'10.005')
    queue(cur);return fxs[0]['material']
def adjusted(cur,today):
    d=today-timedelta(days=5);awp.boundary.historical.prior.set_open_period(cur,d-timedelta(days=1))
    fx=receipt(cur,d,'10.00',qty=10);azp.adjust(cur,fx,d+timedelta(days=1),3);late_invoice(cur,fx,d+timedelta(days=2),'2.10');queue(cur);return fx['material']
def tamper(cur,sql,args,name):
    api.admin(cur);cur.execute('savepoint xa13_'+name)
    try:
        cur.execute(sql,args);n=cur.rowcount;during=drift(cur);err=None
    except psycopg.Error as exc:
        n=0;during=None;err=dict(sqlstate=exc.sqlstate,message=(exc.diag.message_primary or str(exc))[:300])
    cur.execute('rollback to savepoint xa13_'+name);api.admin(cur)
    return dict(rows=n,drift_during=during,refusal=err,drift_after_rollback=drift(cur))
def state_tamper(cur,today):
    base=drift(cur);m=stacked(cur,today);clean=drift(cur)
    t=tamper(cur,"""update erp.material_cost_revaluation_state s set applied_inventory_delta=applied_inventory_delta+0.05
        where s.movement_id=(select id from erp.material_stock_movements where material_id=%s and source_type='CUTTING_GROUP' order by physical_at limit 1)""",(m,),'state')
    ok=clean==base and t['rows']==1 and t['drift_during'] is not None and t['drift_during']==clean+1 and t['drift_after_rollback']==clean
    status='PASS' if ok else ('INCOMPLETE' if t['refusal'] or t['rows']!=1 else 'FAIL')
    return dict(status=status,baseline=base,after_flow=clean,tamper=t,oracle='D07: exact books silent; +0.05 on one applied delta -> document sum off -> drift +1; rollback -> silent')
def fact_tamper(cur,today):
    base=drift(cur);m=adjusted(cur,today);clean=drift(cur)
    api.admin(cur);fact=cur.execute('select id,ledger_delta from erp.material_adjustment_revaluation_facts where triggering_material_id=%s order by created_at limit 1',(m,)).fetchone()
    if not fact:return dict(status='INCOMPLETE',error='no adjustment fact for the material',baseline=base,after_flow=clean)
    fid,ledger=fact;key=next(iter(ledger));bad=dict(ledger);bad[key]=float(D(str(bad[key]))+D('0.05'))
    t=tamper(cur,'update erp.material_adjustment_revaluation_facts set ledger_delta=%s::jsonb where id=%s',(json.dumps(bad),fid),'fact')
    ok=clean==base and t['rows']==1 and t['drift_during'] is not None and t['drift_during']==clean+1 and t['drift_after_rollback']==clean
    status='PASS' if ok else ('INCOMPLETE' if t['refusal'] or t['rows']!=1 else 'FAIL')
    return dict(status=status,baseline=base,after_flow=clean,tamper=t,fact_id=str(fid),tampered_key=key,oracle='D07: adjustment recost read from facts; a wrong fact amount -> drift +1; rollback -> silent')
def silent(cur,today):
    base=drift(cur);stacked(cur,today);a=drift(cur);adjusted(cur,today);b=drift(cur)
    ok=a==base and b==base
    return dict(status='PASS' if ok else 'FAIL',baseline=base,after_stacked=a,after_adjusted=b,oracle='D07: no alarm on exact books (stacked n=3; adjustment + late invoice)')
def cases(cur,today):
    def wrap(fn):
        def run():
            try:return fn()
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:600],trace=traceback.format_exc()[-1500:])
        return run
    return [('XA13:D07_SILENT_ON_EXACT',wrap(lambda:silent(cur,today))),
            ('XA13:D07_NEG_STATE_TAMPER',wrap(lambda:state_tamper(cur,today))),
            ('XA13:D07_NEG_FACT_TAMPER',wrap(lambda:fact_tamper(cur,today)))]
