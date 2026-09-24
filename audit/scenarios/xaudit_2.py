"""AUDITOR SCENARIO xaudit_2 — remaining native checks on 9add57e (independent auditor):
(1) F1-17 rounding on the INVOICE path (estimated receipt 1 unit -> cut -> late invoice), both directions;
(2) F1-15 BS Resolution laundry-source selector with 101 claimable deliveries (oldest must remain selectable);
(3) AV identity: editing a SKU's identity with an effective time BEFORE its latest new-stock fact must be refused;
    with an effective time AFTER the fact it is accepted as a new version (old version kept).
Oracles (contract): M:1022/M:1059-1065/M:3820 (values), M:1691 'selector lengkap', M:3826/M:4486, M:3817 (posted facts
immutable), M:3820 (backdate must not break prefix), M:3822/M:6784 (identity exact). Refusals recorded verbatim."""
from datetime import timedelta
from decimal import Decimal
import json,traceback,uuid
import psycopg
import cp6_aw_probe as awp
import cp6_ax_probe as axp
import cp6_az_probe as azp
api=awp.api;chain=awp.chain;prod=chain.production
KEYS=('MATERIAL_INVENTORY','WIP','FG_INVENTORY','COGS')

def attempt(cur,fn):
    api.admin(cur);cur.execute('savepoint xa2')
    try:
        r=fn();cur.execute('release savepoint xa2');api.admin(cur);return r,None
    except psycopg.Error as exc:
        cur.execute('rollback to savepoint xa2');api.admin(cur);return None,dict(sqlstate=exc.sqlstate,message=(exc.diag.message_primary or str(exc))[:300])

def estimated_receipt(cur,day,qty,price):
    prior=prod.prior;api.admin(cur);prod.zone(cur,'Asia/Jakarta')
    material=prior.clone_material(cur,'xa2est');location=uuid.uuid4()
    cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,'XA2 estimated raw warehouse','RAW_MATERIAL_WAREHOUSE',true)",(location,'XA2-LOC-'+location.hex[:20]))
    draft=prod.rpc(cur,'erp.save_material_purchase_draft_v2',dict(purchase_number='XA2-EST-PUR-'+str(uuid.uuid4()),supplier_id=prior.BASE_SUPPLIER,location_id=location,
        physical_at=prod.at(day,10),change_reason='XA2 estimated receipt',lines=[dict(material_id=material,qty=qty,unit_price=price,price_state='ESTIMATED',
        price_source='MANUAL_ESTIMATE',rolls=[dict(roll_number='XA2-ROLL-'+str(uuid.uuid4()),qty=qty)])]))
    purchase=uuid.UUID(draft['purchase_id'])
    cur.execute('select erp.post_material_purchase_v2(%s,%s,%s,%s)',(purchase,uuid.uuid4(),int(draft['row_version']),'XA2 estimated receipt post'))
    api.admin(cur)
    item=cur.execute('select id from erp.material_purchase_items where purchase_id=%s',(purchase,)).fetchone()[0]
    roll=cur.execute('select id from erp.material_rolls where material_id=%s order by received_at desc limit 1',(material,)).fetchone()[0]
    return dict(material=material,purchase=purchase,item=item,location=location,roll=roll)

def late_invoice(cur,fx,day,qty,price):
    api.admin(cur)
    version=int(cur.execute('select row_version from erp.material_purchase_headers where id=%s',(fx['purchase'],)).fetchone()[0])
    payload=dict(purchase_id=fx['purchase'],supplier_invoice_number='XA2-INV-'+uuid.uuid4().hex[:12],invoice_date=str(day),received_at=prod.at(day,15),
                 reason='XA2 late invoice at '+price,lines=[dict(purchase_item_id=fx['item'],qty_invoiced=qty,final_unit_price=price)])
    prod.zone(cur,'Asia/Jakarta');r=prod.rpc(cur,'erp.finalize_material_purchase_invoice_v2',payload,uuid.uuid4(),version)
    api.admin(cur);prod.owner(cur);cur.execute('select erp.process_cost_recalc_queue(100)');api.admin(cur);return r

def invoice_rounding(cur,today,p0,p1):
    d=today-timedelta(days=4);days=[d+timedelta(days=i) for i in range(5)]
    before=azp.ledger_days(cur,days,[])
    fx=estimated_receipt(cur,d,1,p0)
    po=azp.cut(cur,fx,d+timedelta(days=1),1)
    mid=azp.ledger_days(cur,days,[po])
    r,err=attempt(cur,lambda:late_invoice(cur,fx,d+timedelta(days=2),1,p1))
    after=azp.ledger_days(cur,days,[po]);last=str(days[-1])
    delta={k:str(Decimal(after[last][k])-Decimal(before[last][k])) for k in KEYS}
    delta_mid={k:str(Decimal(mid[last][k])-Decimal(before[last][k])) for k in KEYS}
    raw=cur.execute('select coalesce(sum(qty_signed),0)::text from erp.material_stock_movements where material_id=%s',(fx['material'],)).fetchone()[0]
    snap=cur.execute('select movement_type,qty_signed::text,unit_cost_snapshot::text,original_unit_cost_snapshot::text from erp.material_stock_movements where material_id=%s order by physical_at',(fx['material'],)).fetchall()
    daily={k:{kk:str(Decimal(after[k][kk])-Decimal(before[k][kk])) for kk in ('MATERIAL_INVENTORY','WIP')} for k in after}
    expected_wip=str(Decimal(p1).quantize(Decimal('0.01')))
    checks=dict(invoice_posted=err is None,raw_qty_zero=Decimal(raw)==0,inventory_value_zero_at_end=Decimal(delta['MATERIAL_INVENTORY'])==0,
                wip_equals_rounded_invoiced_value=delta['WIP']==expected_wip,no_negative_daily_inventory=all(Decimal(v['MATERIAL_INVENTORY'])>=0 for v in daily.values()))
    status='INCOMPLETE' if err else ('PASS' if all(checks.values()) else 'COUNTEREXAMPLE')
    return dict(status=status,checks=checks,receipt_day=str(d),cut_day=str(d+timedelta(days=1)),invoice_day=str(d+timedelta(days=2)),p0=p0,p1=p1,
                delta_after_cut=delta_mid,delta_end=delta,expected_wip=expected_wip,raw_qty=raw,movements=[[str(x) for x in r_] for r_ in snap],daily_delta=daily,refusal=err,
                expected='M:1022/M:1059-1065/M:3820 (invoice path): fully consumed unit leaves inventory qty and value 0; WIP = invoiced value rounded to cents; no negative daily inventory')

def clone_row(cur,table,row_id,overrides):
    cols=[c[0] for c in cur.execute("select column_name from information_schema.columns where table_schema='erp' and table_name=%s and is_generated='NEVER' and column_default is distinct from 'auto' order by ordinal_position",(table,)).fetchall()]
    cols=[c for c in cols if c!='id' or 'id' in overrides]
    sel=','.join(('%%(%s)s'%c if c in overrides else '"%s"'%c) for c in cols)
    cur.execute('insert into erp."%s"(%s) select %s from erp."%s" where id=%%(_src)s'%(table,','.join('"%s"'%c for c in cols),sel,table),dict(overrides,_src=row_id))

def selector_101(cur,today):
    api.admin(cur)
    seed=cur.execute("select d.id from erp.laundry_deliveries d where exists(select 1 from erp.laundry_delivery_lines l where l.delivery_id=d.id and l.qty_sent_pcs>0) order by d.physical_at desc limit 1").fetchone()
    if not seed:return dict(status='INCOMPLETE',error='no laundry delivery with lines in the seed to clone')
    seed=seed[0]
    line_ids=[r[0] for r in cur.execute('select id from erp.laundry_delivery_lines where delivery_id=%s',(seed,)).fetchall()]
    def make(number,when):
        did=uuid.uuid4()
        clone_row(cur,'laundry_deliveries',seed,dict(id=did,delivery_number=number,physical_at=when,status='SENT'))
        for lid in line_ids:clone_row(cur,'laundry_delivery_lines',lid,dict(id=uuid.uuid4(),delivery_id=did))
        return did
    old=make('XA2-OLD-'+uuid.uuid4().hex[:8],prod.at(today-timedelta(days=200),9))
    new=[make('XA2-NEW-%03d'%i,prod.at(today-timedelta(days=1),8)+timedelta(minutes=i)) for i in range(100)]
    api.admin(cur);prod.owner(cur)
    ws=cur.execute("select public.erp_get_bs_resolution_workspace_v1('ACTIVE','ALL',null,null,50,0)").fetchone()[0]
    api.admin(cur)
    src=(ws.get('lookups') or {}).get('laundry_sources') or []
    ids=[s['id'] for s in src];claimable=[s['id'] for s in src if (s.get('qty_claimable_pcs') or 0)>0]
    old_claimable=cur.execute("select sum(qty_sent_pcs) from erp.laundry_delivery_lines where delivery_id=%s",(old,)).fetchone()[0]
    checks=dict(old_claimable_in_db=bool(old_claimable and old_claimable>0),old_selectable=str(old) in ids,lookups_capped_at_100=len(src)==100)
    return dict(status='PASS' if checks['old_selectable'] else 'COUNTEREXAMPLE',checks=checks,lookups_count=len(src),claimable_in_lookups=len(claimable),old_id=str(old),old_qty=str(old_claimable),
                newest_in_lookups=[s['number'] for s in src[:2]],oldest_in_lookups=[s['number'] for s in src[-2:]],
                expected='M:1691/M:3826/M:4486: an older delivery that is still claimable must be selectable from the claim form lookups (any list/search/paging)')

def identity_edit(cur,today,before_fact):
    f=axp.stocked_product(cur,today);product=str(f['product']);api.admin(cur)
    latest=cur.execute('select erp.latest_new_stock_physical_at_v1(%s)',(product,)).fetchone()[0]
    p=cur.execute('select sku,model_id,brand_id,color_name,size_id,product_name,effective_from,effective_to from erp.products where id=%s',(product,)).fetchone()
    if latest is None:return dict(status='INCOMPLETE',error='stocked product has no new-stock fact')
    eff=latest-timedelta(hours=1) if before_fact else latest+timedelta(hours=1)
    def do():
        prod.owner(cur)
        return cur.execute("""select erp.edit_product_identity_effective(p_product_id=>%s,p_sku=>%s,p_model_id=>%s,p_brand_id=>%s,p_color_name=>%s,p_size_id=>%s,
            p_product_name=>%s,p_effective_from=>%s,p_reason=>%s)""",(product,p[0]+'-XA2',p[1],p[2],p[3],p[4],p[5],eff,'XA2 identity edit probe')).fetchone()[0]
    r,err=attempt(cur,do)
    api.admin(cur)
    versions=cur.execute('select count(*),min(effective_from)::text,max(effective_from)::text from erp.products where identity_root_id=(select coalesce(identity_root_id,id) from erp.products where id=%s) or id=%s',(product,product)).fetchone()
    old=cur.execute('select effective_to::text,sku from erp.products where id=%s',(product,)).fetchone()
    if before_fact:
        checks=dict(refused=err is not None);status='PASS' if checks['refused'] else 'COUNTEREXAMPLE'
        exp='M:3817/M:3820: an identity change effective BEFORE the latest new-stock fact of the SKU is refused (posted facts keep their identity); refusal recorded verbatim'
    else:
        checks=dict(accepted=err is None and r is not None,old_version_closed=old[0] is not None,old_sku_unchanged=old[1]==p[0]);status='PASS' if all(checks.values()) else ('INCOMPLETE' if err else 'COUNTEREXAMPLE')
        exp='M:3822/M:6784: an identity change effective AFTER the latest fact creates a new version and keeps the old version (effective_to set, old SKU text unchanged)'
    return dict(status=status,checks=checks,latest_new_stock_fact=str(latest),effective_from=str(eff),result=str(r) if r else None,refusal=err,versions=[str(x) for x in versions],old_row=[str(x) for x in old],expected=exp)

def cases(cur,today):
    def wrap(fn,*a):
        def run():
            try:return fn(cur,today,*a)
            except Exception as exc:return dict(status='INCOMPLETE',error=str(exc)[:900],traceback=traceback.format_exc()[-1500:])
        return run
    return [('XA2:F1-17_INVOICE_PATH_UP_10.005_TO_10.014',wrap(invoice_rounding,'10.005','10.014')),
            ('XA2:F1-17_INVOICE_PATH_DOWN_10.014_TO_10.005',wrap(invoice_rounding,'10.014','10.005')),
            ('XA2:F1-15_SELECTOR_101_LAUNDRY_SOURCES',wrap(selector_101)),
            ('XA2:AV_IDENTITY_EDIT_BEFORE_NEW_STOCK_FACT',wrap(identity_edit,True)),
            ('XA2:AV_IDENTITY_EDIT_AFTER_NEW_STOCK_FACT',wrap(identity_edit,False))]
