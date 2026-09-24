"""AUDITOR SCENARIO xaudit_1 — native verification of the second independent auditor's NOT_RUN items on 9add57e:
U02 (WIP opening re-completion dated before the reversal of an earlier completion), U03 (rounding of a 1-unit receipt
fully consumed then cost-corrected, both directions), SI03 (idempotent replay: same UUID + different payload).
Oracles (contract only): M:369-371 (WIP opening: over-quantity/stale/dates refused; reversal keeps linked events),
M:3816-3826 (backdate must not break qty/value prefix; UUID same + payload different refused), M:1022/M:1059-1065
(value consistency of inventory/WIP after cost correction). Data generators: writer helpers cp6_initial_import_production_trial
(fixture/finalize/output/reverse_output), cp6_az_probe (final_receipt/cut/ledger_days). Refusals are recorded verbatim."""
from datetime import timedelta
from decimal import Decimal
import json,traceback,uuid
import psycopg
import cp6_aw_probe as awp
import cp6_az_probe as azp
import cp6_initial_import_production_trial as pt
api=awp.api;chain=awp.chain;prod=chain.production
KEYS=('MATERIAL_INVENTORY','WIP','FG_INVENTORY','COGS')

def attempt(cur,fn):
    api.admin(cur);cur.execute('savepoint xa')
    try:
        r=fn();cur.execute('release savepoint xa');api.admin(cur);return r,None
    except psycopg.Error as exc:
        cur.execute('rollback to savepoint xa');api.admin(cur);return None,dict(sqlstate=exc.sqlstate,message=(exc.diag.message_primary or str(exc))[:300])

def stage_balance_by_day(cur,po,stage,days):
    api.admin(cur)
    rows=cur.execute("select (physical_at at time zone 'Asia/Jakarta')::date,stage_from,stage_to,qty_pcs from erp.wip_stage_events where po_id=%s",(po,)).fetchall()
    out={}
    for d in days:
        bal=Decimal(0)
        for pd,sf,st,q in rows:
            if pd<=d:
                if st==stage:bal+=Decimal(q)
                if sf==stage:bal-=Decimal(q)
        out[str(d)]=str(bal)
    return out

def wip_recompletion(cur,today):
    f=pt.fixture(api,cur,today)
    receipt,sources=pt.finalize(api,cur,f)
    api.admin(cur)
    po=cur.execute('select id from erp.production_orders where po_number=%s',(f['code'],)).fetchone()[0]
    s=sources['WIP']
    stage=cur.execute('select stage from erp.initial_import_production_sources where opening_item_id=%s',(s['opening_item_id'],)).fetchone()[0]
    cutover=cur.execute('select h.opening_date from erp.opening_balance_headers h join erp.opening_balance_items i on i.opening_id=h.id where i.id=%s',(s['opening_item_id'],)).fetchone()[0]
    days=[cutover+timedelta(days=i) for i in range((today-cutover).days+1)]
    o=pt.output(api,cur,f,today,qty='8')      # first completion, dated today-3 (writer helper)
    rv=pt.reverse_output(api,cur,f,o)          # reversal, physical_at = now (today)
    mid_stage=stage_balance_by_day(cur,po,stage,days)
    s2=next(x for x in api.read(cur,f['batch'])['batch']['production_sources'] if x['balance_type']=='WIP')
    payload=dict(batch_id=f['batch'],opening_item_id=s2['opening_item_id'],expected_remaining=str(s2['remaining_qty_pcs']),operation='COMPLETE',
                 qty_pcs='8',product_sku=f['code'],location_code=f['code']+'F',date=str(today-timedelta(days=1)),reason='auditor re-completion dated before the reversal')
    second,err=attempt(cur,lambda:api.call(cur,'WIP_OUTPUT',payload,uuid.uuid4()))
    after_stage=stage_balance_by_day(cur,po,stage,days);after_gl=azp.ledger_days(cur,days,[po])
    neg_stage=[d for d,v in after_stage.items() if Decimal(v)<0]
    neg_gl=[d for d,v in after_gl.items() if Decimal(v['WIP_PO'][str(po)])<0]
    checks=dict(second_completion_refused=err is not None,no_negative_stage_prefix=not neg_stage,no_negative_wip_gl_prefix=not neg_gl)
    ok=checks['second_completion_refused'] or (checks['no_negative_stage_prefix'] and checks['no_negative_wip_gl_prefix'])
    return dict(status='PASS' if ok else 'COUNTEREXAMPLE',checks=checks,cutover=str(cutover),stage=stage,first_completion_date=str(today-timedelta(days=3)),reversal_day=str(today),
                second_completion_date=str(today-timedelta(days=1)),second_result=str(second)[:200] if second else None,refusal=err,
                remaining_before_second=s2['remaining_qty_pcs'],stage_balance_mid=mid_stage,stage_balance_after=after_stage,
                wip_gl_po_after={d:v['WIP_PO'][str(po)] for d,v in after_gl.items()},negative_stage_days=neg_stage,negative_gl_days=neg_gl,
                expected='M:369-371/M:3820: a completion dated before the reversal of an earlier completion is refused, or the stage qty and WIP GL prefix stay non-negative on every day')

def rounding(cur,today,p0,p1):
    d=today-timedelta(days=4);days=[d+timedelta(days=i) for i in range(5)]
    before=azp.ledger_days(cur,days,[])
    fx=azp.final_receipt(cur,d,qty=1,price=p0)
    api.admin(cur)
    fx['roll']=cur.execute('select id from erp.material_rolls where material_id=%s order by received_at desc limit 1',(fx['material'],)).fetchone()[0]
    po=azp.cut(cur,fx,d+timedelta(days=1),1)
    mid=azp.ledger_days(cur,days,[po])
    api.admin(cur)
    corr=cur.execute("insert into erp.material_purchase_cost_corrections(correction_number,purchase_id,invoice_date,reason) values(%s,%s,%s,%s) returning id",
                     ('XA-CC-'+uuid.uuid4().hex[:12],fx['purchase'],d+timedelta(days=2),'auditor rounding probe')).fetchone()[0]
    cur.execute('insert into erp.material_purchase_cost_correction_items(correction_id,purchase_item_id,new_unit_price) values(%s,%s,%s)',(corr,fx['item'],p1))
    def post():
        prod.owner(cur);cur.execute('select erp.post_material_purchase_cost_correction(%s)',(corr,))
        prod.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');api.admin(cur)
    _,err=attempt(cur,post)
    after=azp.ledger_days(cur,days,[po]);last=str(days[-1])
    delta={k:str(Decimal(after[last][k])-Decimal(before[last][k])) for k in KEYS}
    delta_mid={k:str(Decimal(mid[last][k])-Decimal(before[last][k])) for k in KEYS}
    raw=cur.execute('select coalesce(sum(qty_signed),0)::text from erp.material_stock_movements where material_id=%s',(fx['material'],)).fetchone()[0]
    snap=cur.execute('select movement_type,qty_signed::text,unit_cost_snapshot::text,original_unit_cost_snapshot::text from erp.material_stock_movements where material_id=%s order by physical_at',(fx['material'],)).fetchall()
    expected_wip=str(Decimal(p1).quantize(Decimal('0.01')))
    daily={k:{kk:str(Decimal(after[k][kk])-Decimal(before[k][kk])) for kk in ('MATERIAL_INVENTORY','WIP')} for k in after}
    checks=dict(correction_posted=err is None,raw_qty_zero=Decimal(raw)==0,inventory_value_zero_at_end=Decimal(delta['MATERIAL_INVENTORY'])==0,
                wip_equals_rounded_corrected_value=delta['WIP']==expected_wip,no_negative_daily_inventory=all(Decimal(v['MATERIAL_INVENTORY'])>=0 for v in daily.values()))
    status='INCOMPLETE' if err else ('PASS' if all(checks.values()) else 'COUNTEREXAMPLE')
    return dict(status=status,checks=checks,receipt_day=str(d),cut_day=str(d+timedelta(days=1)),correction_day=str(d+timedelta(days=2)),p0=p0,p1=p1,
                delta_after_cut=delta_mid,delta_end=delta,expected_wip=expected_wip,raw_qty=raw,movements=[[str(x) for x in r] for r in snap],daily_delta=daily,refusal=err,
                expected='M:1022/M:1059-1065/M:3820: one unit received and fully consumed leaves raw qty and inventory value 0 at the end; WIP carries the corrected value rounded to cents (1 x p1); daily inventory never negative')

def replay(cur,today):
    key=uuid.uuid4();tag='XA'+uuid.uuid4().hex[:10];cut=str(today-timedelta(days=1))
    first=api.call(cur,'CREATE',dict(batch_code=tag,cutover_date=cut),key)
    same,err0=attempt(cur,lambda:api.call(cur,'CREATE',dict(batch_code=tag,cutover_date=cut),key))
    diff,err=attempt(cur,lambda:api.call(cur,'CREATE',dict(batch_code=tag+'X',cutover_date=str(today-timedelta(days=2))),key))
    checks=dict(same_payload_replays_identically=(err0 is None and same==first),different_payload_refused=err is not None)
    return dict(status='PASS' if all(checks.values()) else 'COUNTEREXAMPLE',checks=checks,first=str(first)[:200],replay=str(same)[:200] if same else None,replay_error=err0,
                different_payload_result=str(diff)[:200] if diff else None,refusal=err,
                expected="M:3819: same UUID + same payload replays exactly; same UUID + different payload is refused (message recorded verbatim; the second auditor's expected text is not present in the candidate SQL)")

def cases(cur,today):
    def wrap(fn,*a):
        def run():
            try:return fn(cur,today,*a)
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:900],traceback=traceback.format_exc()[-1500:])
        return run
    return [('XA:U02_WIP_RECOMPLETION_DATED_BEFORE_REVERSAL',wrap(wip_recompletion)),
            ('XA:U03_ROUNDING_UP_10.005_TO_10.014',wrap(rounding,'10.005','10.014')),
            ('XA:U03_ROUNDING_DOWN_10.014_TO_10.005',wrap(rounding,'10.014','10.005')),
            ('XA:SI03_IDEMPOTENT_REPLAY_DIFFERENT_PAYLOAD',wrap(replay))]
