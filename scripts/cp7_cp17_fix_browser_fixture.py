"""CP17 browser fixtures (SG-01 pickup reversal, SG-02 fabric return, D14-6 kasbon, D14-5 dozens over a size series, D14-14 G1
sewing completion on the WIP & Sewing page; Sol R2-10 the same per SKU of a wave Potongan) in the
disposable browser database only.

The same Native-writer fixtures as the native CP17 cases (cp7_cp17_fix_cases.pickup_fixture / fabric_fixture, the
settlement review payroll and a funded bank for kasbon); the state
readback is direct SQL on the rows the screens change, never the CP7 command's own answer.

D14-5: one SKU in three sizes (31/32/33, stock 10/11/12) and one SKU in one size (27, stock 20), each size a product of
its own with the SKU shared (commercial SKU = product SKU without a BF group), stock found at opname through the accepted
AX command (owner value only where no HPP reference exists yet, as the command requires).
R2-06 (Astra ASTRA-C17-01): a second brand carries the same series SKU in size 32 (stock 5), so picking the first
brand's series must add its three sizes only; the other brand's row stays out of the invoice and its stock unchanged.
"""
from datetime import date
from urllib.parse import urlparse
from datetime import timedelta
import json,os,sys,uuid
import psycopg
import cp7_cp17_fix_cases as cases

def series(cur,today):
    import cp7_fg_cases as fg
    ax=fg.ax;base=fg.base;tag='D145-'+uuid.uuid4().hex[:8].upper();at=ax.r1.now(cur)-timedelta(minutes=50);ax.api.admin(cur)
    def sku(name,sizes,brand=None):
        model=uuid.uuid4();out={}
        cur.execute('insert into erp.product_models(id,model_code,model_name,is_active) values(%s,%s,%s,true)',(model,'D145-'+model.hex[:10],'D14-5 '+name))
        for order,(code,qty) in enumerate(sizes):
            cur.execute('insert into erp.sizes(size_code,sort_order,is_active) values(%s,%s,true) on conflict(size_code) do nothing',(code,int(code)))
            size=cur.execute('select id from erp.sizes where size_code=%s',(code,)).fetchone()[0];product=uuid.uuid4()
            cur.execute('insert into erp.product_model_sizes(model_id,size_id,sort_order) values(%s,%s,%s) on conflict(model_id,size_id) do nothing',(model,size,order))
            cur.execute("""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from,is_active,is_portal_visible)
                select %s,%s,%s,coalesce(%s,brand_id),'D145',%s,%s,%s,effective_from,true,true from erp.products where id=%s""",(product,name,model,brand,size,'Celana '+name,product,ax.chain.base.BASE_PRODUCT))
            cur.execute("insert into erp.accessory_bom_versions(product_id,version_label,effective_from,is_active,notes) values(%s,'D145-EMPTY','2026-01-01',true,'Explicit empty BOM')",(product,))
            tier=cur.execute('select erp.fg_unsourced_valuation_v1(%s,%s)',(product,at)).fetchone()[0]['tier']
            value=dict(owner_unit_value='10',owner_value_reason='D14-5 explicit independently supplied value') if tier=='OWNER_INPUT_REQUIRED' else {}
            posted=ax.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=str(product),location_id=base.LOCATION,qty_pcs=qty,physical_at=at.isoformat(),reason='D14-5 series stock found at opname',**value))
            out[code]=dict(product=str(product),lot=cur.execute('select lot_id::text from erp.fg_unsourced_receipts_v1 where id=%s',(posted['receipt_id'],)).fetchone()[0],stock=qty)
        return out
    three=sku(tag+'-SERI',[('31',10),('32',11),('33',12)]);one=sku(tag+'-TUNGGAL',[('27',20)])
    brand=cur.execute('select b.brand_name from erp.products p join erp.brands b on b.id=p.brand_id where p.id=%s',(ax.chain.base.BASE_PRODUCT,)).fetchone()[0]
    other_brand=cur.execute('insert into erp.brands(brand_code,brand_name) values(%s,%s) returning id,brand_name',(tag+'-B',tag+' Merek Lain')).fetchone()
    other=sku(tag+'-SERI',[('32',5)],other_brand[0])['32']
    customer=str(base.create_customer(cur,tag));ax.api.admin(cur)
    return dict(tag=tag,customer=customer,sale_at=(ax.r1.now(cur)-timedelta(minutes=7)).isoformat(),series_sku=tag+'-SERI',single_sku=tag+'-TUNGGAL',brand=brand,
                other_brand=other_brand[1],other=other,sizes=dict(three,**one),location=str(base.LOCATION))

def series_state(cur,p):
    import cp7_sales_cases as sales
    stock={code:int(cur.execute('select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s',(x['lot'],)).fetchone()[0]) for code,x in p['sizes'].items()}
    other=int(cur.execute('select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s',(p['other']['lot'],)).fetchone()[0])
    found=cur.execute('select id::text,status from erp.sales_headers where sale_number=%s',(p['tag'],)).fetchone()
    if not found:return dict(sale=None,stock=stock,other_brand_stock=other,gl=[[str(x) for x in r] for r in sales.gl(cur)])
    by_product={x['product']:code for code,x in p['sizes'].items()}
    items=cur.execute('select product_id::text,qty_pcs from erp.sales_items where sale_id=%s',(found[0],)).fetchall()
    return dict(sale=found[0],status=found[1],qty={by_product.get(pid,'OTHER_BRAND'):int(q) for pid,q in items},lines=len(items),stock=stock,other_brand_stock=other,gl=[[str(x) for x in r] for r in sales.gl(cur)])

# Owner D15-3 (FABLE-017): the master screens. Fixtures give each case its own records (a fresh model, a customer with an
# open sales draft, a stocked warehouse, a posted cutting without a Mandor); the state readback is direct SQL on the Native
# tables the screens change, never the facade's own reader (cp7_master.entity).
def master_state(cur,p):
    kind,code=p['kind'],p['code'];one=lambda sql,args:cur.execute(sql,args).fetchone()
    sql={'CUSTOMER':"select id::text,customer_name,is_active,phone,address from erp.customers where lower(customer_code)=lower(%s)",
         'SUPPLIER':"select id::text,supplier_name,is_active,supplier_type,phone from erp.suppliers where lower(supplier_code)=lower(%s)",
         'LAUNDRY_VENDOR':"select id::text,vendor_name,is_active,phone,notes from erp.laundry_vendors where lower(vendor_code)=lower(%s)",
         'MANDOR':"select id::text,contractor_name,is_active,attendance_required,contractor_type from erp.contractors where lower(contractor_code)=lower(%s)",
         'LOCATION':"select id::text,location_name,is_active,location_type,null from erp.locations where lower(location_code)=lower(%s)",
         'FABRIC':"select id::text,material_name,is_active,upper(unit_code),material_type from erp.materials where lower(material_sku)=lower(%s) and material_type='FABRIC'",
         'ACCESSORY_CATEGORY':"select id::text,category_name,is_active,base_uom_code,notes from erp.accessory_categories where lower(category_code)=lower(%s)",
         'ACCESSORY':"select id::text,material_name,is_active,accessory_category_id::text,material_type from erp.materials where lower(material_sku)=lower(%s) and material_type='ACCESSORY'"}[kind]
    rows=cur.execute(sql,(code,)).fetchall()
    if not rows:return dict(found=False,count=0)
    id,name,active,a,b=rows[0]
    out=dict(found=True,count=len(rows),id=id,name=name,active=active,a=a,b=b,
             history=one('select count(*) from cp7_master.history where entity_id=%s',(id,))[0],
             history_actions=[r[0] for r in cur.execute('select action from cp7_master.history where entity_id=%s order by id',(id,)).fetchall()])
    if kind=='MANDOR':
        out['policies']=[[x,str(f),None if t is None else str(t)] for x,f,t in cur.execute(
            'select is_special,effective_from,effective_to from erp.contractor_hpp_policy_versions where contractor_id=%s order by effective_from',(id,)).fetchall()]
    if kind=='FABRIC':
        prof=one('select width_cm::text,color_name,fabric_category,composition from erp.fabric_master_profiles where material_id=%s',(id,))
        out['profile']=None if prof is None else list(prof)
        out['benchmarks']=[[str(x),str(f)] for x,f in cur.execute("select benchmark_price_per_base_uom::text,(effective_from at time zone 'Asia/Jakarta')::date from erp.fabric_benchmark_price_versions where material_id=%s order by effective_from",(id,)).fetchall()]
    if kind=='ACCESSORY_CATEGORY':
        out['prices']=[[c,str(x),u] for c,x,u in cur.execute('select contractor_id::text,selling_price::text,selling_uom_code from erp.contractor_accessory_price_versions where category_id=%s order by effective_from',(id,)).fetchall()]
        out['active_variants']=one("select count(*) from erp.materials where accessory_category_id=%s and is_active and material_type='ACCESSORY'",(id,))[0]
    return out

def rate_state(cur,p):
    m=cur.execute('select id from erp.contractors where lower(contractor_code)=lower(%s)',(p['mandor_code'],)).fetchone()
    rates=[] if m is None else [[c,str(r),str(f),None if t is None else str(t)] for c,r,f,t in cur.execute("""select k.component_code,w.rate_per_pcs::text,
        (w.effective_from at time zone 'Asia/Jakarta')::date,(w.effective_to at time zone 'Asia/Jakarta')::date from erp.contractor_work_rates w
        join erp.work_components k on k.id=w.work_component_id where w.contractor_id=%s and w.model_id=%s order by k.component_code,w.effective_from""",(m[0],p['model'])).fetchall()]
    bom=[[v,str(f),c,str(r)] for v,f,c,r in cur.execute("""select v.version_no,(v.effective_from at time zone 'Asia/Jakarta')::date,k.component_code,i.default_rate::text
        from erp.work_bom_versions v join erp.work_bom_items i on i.bom_version_id=v.id join erp.work_components k on k.id=i.work_component_id
        where v.model_id=%s and v.is_active order by v.version_no,i.sequence_no""",(p['model'],)).fetchall()]
    return dict(rates=rates,bom=bom)

def chain(cur,today):
    import cp7_master_cases as master
    g=master.cutting_only(cur,today);cases.b.api.admin(cur);one=lambda sql,args:cur.execute(sql,args).fetchone()
    roll,size=one("""select mr.roll_number,s.size_code from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
        join erp.material_rolls mr on mr.id=r.roll_id join erp.cutting_group_size_slots z on z.id=y.size_slot_id join erp.sizes s on s.id=z.size_id
        where r.cutting_group_id=%s""",(g['group'],))
    model=one('select model_code from erp.product_models where id=%s',(g['model'],))[0]
    def bom_at(at):
        return [r[0] for r in cur.execute("""select k.component_code from erp.work_bom_items i join erp.work_components k on k.id=i.work_component_id
            where i.bom_version_id=(select v.id from erp.work_bom_versions v where v.model_id=%s and v.is_active and v.effective_from<=%s
              and(v.effective_to is null or v.effective_to>%s)and exists(select 1 from erp.work_bom_items x where x.bom_version_id=v.id)
              order by v.effective_from desc,v.version_no desc,v.id desc limit 1) order by i.sequence_no,i.id""",(g['model'],at,at)).fetchall()]
    return dict(group=g['group'],po=g['po'],number=g['number'],model=g['model'],model_code=model,day=str(g['day']),roll_number=roll,size_code=size,
                bom_at_sewing=bom_at(g['at'](10)),bom_now=bom_at(cur.execute('select clock_timestamp()').fetchone()[0]))

def chain_state(cur,p):
    one=lambda sql,args:cur.execute(sql,args).fetchone()
    po=one('select c.contractor_code from erp.production_orders o left join erp.contractors c on c.id=o.contractor_id where o.id=%s',(p['po'],))
    pick=one("select count(*) filter(where status='POSTED') from erp.cutting_pickups where cutting_group_id=%s",(p['group'],))
    works=cur.execute("select id::text from erp.work_completion_events where cutting_group_id=%s and status='POSTED' order by created_at",(p['group'],)).fetchall()
    snaps=[[c,str(r),str(d)] for c,r,d in cur.execute("""select k.component_code,s.rate_per_pcs_snapshot::text,(s.committed_at at time zone 'Asia/Jakarta')::date
        from erp.po_work_component_snapshots s join erp.work_components k on k.id=s.work_component_id where s.po_id=%s and s.bf_sku_version_id is null order by s.sequence_no""",(p['po'],)).fetchall()]
    return dict(po_mandor=po[0],posted_pickups=pick[0],sewn=cases.sewn_ready(cur,dict(group=p['group']))[0],posted_work=len(works),
                wage=[[str(x) for x in cases.wage_journal(cur,w[0])] for w in works],snapshots=snaps)

def auto_po(cur,today):
    """Owner D15-6: a posted estimated receipt of one roll (10) at its own raw warehouse, what the Buat Potongan screen needs
    to find it, and the next free PO number of the cutting day (the oracle's own count, as in the Native cases)."""
    import cp7_auto_po_cases as autopo
    f=autopo.receipt(cur,today);p=autopo.prod();cases.b.api.admin(cur);one=lambda sql,args:cur.execute(sql,args).fetchone()
    day=f['purchase_day']+timedelta(days=1);pre=autopo.prefix(cur,p.at(day,8).isoformat())
    model_code,model_name=one('select model_code,model_name from erp.product_models where id=%s',(p.MODEL,))
    pattern_code,revision=one('select pattern_code,revision from erp.production_patterns where id=%s',(p.PATTERN,))
    sizes=[r[0] for r in cur.execute("""select s.size_code from erp.product_model_sizes pms join erp.sizes s on s.id=pms.size_id
        where pms.model_id=%s and s.is_active order by pms.sort_order,s.sort_order,s.size_code""",(p.MODEL,)).fetchall()]
    return dict(model=str(p.MODEL),model_code=model_code,model_name=model_name,pattern_code=pattern_code,pattern_revision=revision,
        location=str(f['location']),roll=str(f['roll']),roll_number=one('select roll_number from erp.material_rolls where id=%s',(f['roll'],))[0],
        size_code=one('select size_code from erp.sizes where id=%s',(autopo.base().SIZE,))[0],sizes=sizes,cut_local=f'{day:%Y-%m-%d}T08:00',
        prefix=pre,expected=autopo.next_number(cur,pre))

def auto_po_state(cur,p):
    """Read directly from the Native rows: the POs whose cutting took this roll, the roll's stock at its warehouse, the
    facade's drafts and requests for this roll, and whether the expected PO number is taken."""
    one=lambda sql,args:cur.execute(sql,args).fetchone()
    pos=[list(r) for r in cur.execute("""select o.po_number,o.status,o.current_stage,o.model_id::text,o.target_qty_pcs,
        (select count(*) from erp.cutting_groups g where g.po_id=o.id),(select count(*) from erp.cutting_groups g where g.po_id=o.id and g.material_issue_posted),
        (select string_agg(g.group_number,',' order by g.group_number) from erp.cutting_groups g where g.po_id=o.id)
        from erp.production_orders o where exists(select 1 from erp.cutting_groups g join erp.cutting_group_rolls r on r.cutting_group_id=g.id
        where g.po_id=o.id and r.roll_id=%s) order by o.po_number""",(p['roll'],)).fetchall()]
    drafts=[list(r) for r in cur.execute("""select d.id::text,d.status,d.row_version,(select o.po_number from erp.production_orders o where o.id=d.posted_po_id)
        from cp7_cutting_correction.auto_po_drafts d where d.cutting->'rolls'->0->>'roll_id'=%s order by d.created_at,d.id""",(p['roll'],)).fetchall()]
    return dict(pos=pos,drafts=drafts,
        requests=one("select count(*) from cp7_cutting_correction.auto_po_requests where payload->'cutting'->'rolls'->0->>'roll_id'=%s",(p['roll'],))[0],
        stock=str(one('select coalesce(sum(qty_signed),0) from erp.material_stock_movements where roll_id=%s and location_id=%s',(p['roll'],p['location']))[0]),
        taken=one('select count(*) from erp.production_orders where po_number=%s',(p['expected'],))[0])

# R2-07 (FABLE-016, ASTRA-C17-07, Sol BROWSER-CHAIN): one chain on the screens only, from masters and opening WIP
# imported through "Impor data awal" to the customer's payment, with the books closed in the middle. The fixture gives only
# what no screen creates (a bank account) and the test harness state the chain needs: the books opened back to the chain's
# own month (closed_through moved to the day before it, as every fixture's set_open_period does; the previous value is
# returned and put back at the end) and the seed's open items for those days cleared the way the owner would
# (cp6_aw_probe.quiet_seed, as the P13 period case does). Readback is direct SQL on the Native rows.
def r207_prepare(cur,today):
    import cp7_period_cases as period
    code='R207'+uuid.uuid4().hex[:8].upper();day=today-timedelta(days=30);out_day=day+timedelta(days=1)
    prev=cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]
    cur.execute("""update erp.accounting_period_control set closed_through=%s,updated_at=clock_timestamp(),updated_by=null,
        change_reason='CP17 R2-07 chain month' where singleton_id=1""",(day-timedelta(days=1),))
    quiet=period.aw.quiet_seed(cur,day-timedelta(days=1),out_day);cases.b.api.admin(cur)
    bank=str(cases.bc.bank_account(cur,code));cases.b.api.admin(cur)
    return dict(code=code,day=str(day),output_day=str(out_day),opened_closed=str(day-timedelta(days=1)),previous_closed=None if prev is None else str(prev),
                bank=bank,bank_code=cur.execute('select cash_account_code from erp.cash_accounts where id=%s',(bank,)).fetchone()[0],
                quiet=dict(attendance=len(quiet['attendance']),approved=len(quiet['approved']),work_payrolls=len(quiet['work_payrolls']),refused=quiet['refused']))

def r207_state(cur,p):
    import cp7_period_cases as period
    c=p['code'];one=lambda sql,args=():cur.execute(sql,args).fetchone()
    batch=one('select id::text,status from erp.migration_batches where batch_code=%s',(c,))
    prods=dict(cur.execute('select sku,id::text from erp.products where sku in(%s,%s)',(c+'A',c+'B')).fetchall())
    loc=one('select id::text from erp.locations where location_code=%s',(c+'F',))
    customer=one('select id::text from erp.customers where customer_code=%s',(c,))
    wip=one("""select s.opening_item_id::text from erp.initial_import_production_sources s join erp.opening_balance_items i on i.id=s.opening_item_id
        where s.batch_id=%s and i.balance_type='WIP'""",(batch[0],)) if batch else None
    def stock(sku):
        if sku not in prods:return None
        return int(one('select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id where l.product_id=%s',(prods[sku],))[0])
    lots=[r[0] for r in cur.execute('select l.id::text from erp.fg_lots l where l.product_id=%s order by l.produced_at,l.id',(prods.get(c+'A'),)).fetchall()] if c+'A' in prods else []
    conv=[list(r) for r in cur.execute("""select status,(physical_at at time zone 'Asia/Jakarta')::text from erp.product_conversions
        where from_product_id=%s and to_product_id=%s order by physical_at""",(prods.get(c+'A'),prods.get(c+'B'))).fetchall()] if len(prods)==2 else []
    sale=one("""select h.id::text,h.status,(select coalesce(sum(i.qty_pcs),0) from erp.sales_items i where i.sale_id=h.id)
        from erp.sales_headers h where h.sale_number=%s""",(c,))
    paid=one("""select coalesce(sum(jl.debit),0)::text from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
        where je.status='POSTED' and jl.account_id=(select a.coa_account_id from erp.cash_accounts a where a.id=%s)""",(p['bank'],))[0] if p.get('bank') else None
    # The books on or before the closed day, by economic date: what the archive closed must not move later in the chain.
    through=p.get('output_day')
    books=dict((str(a),str(v)) for a,v in cur.execute("""select jl.account_id,sum(jl.debit-jl.credit) from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
        where je.status in('POSTED','REVERSED') and je.economic_date<=%s group by jl.account_id having sum(jl.debit-jl.credit)<>0""",(through,)).fetchall()) if through else {}
    fg_through=cur.execute("""select md5(coalesce(jsonb_agg(jsonb_build_array(m.id,m.qty_signed) order by m.id)::text,'[]')) from erp.fg_stock_movements m
        where (m.physical_at at time zone 'Asia/Jakarta')::date<=%s""",(through,)).fetchone()[0] if through else None
    closed=one('select closed_through::text from erp.accounting_period_control where singleton_id=1')[0]
    filings=len(period.filings(cur))
    return dict(batch=None if not batch else dict(id=batch[0],status=batch[1]),products=prods,location=None if not loc else loc[0],
        customer=None if not customer else customer[0],wip_item=None if not wip else wip[0],stock_a=stock(c+'A'),stock_b=stock(c+'B'),lots_a=lots,
        conversions=conv,sale=None if not sale else dict(id=sale[0],status=sale[1],qty=int(sale[2])),bank_debit=paid,
        books_through=books,fg_through=fg_through,closed_through=closed,filings=filings)

def r207b_prepare(cur,today):
    """The second R2-07 chain (BS -> rework -> Nota -> payroll -> paid) in its own earlier month, the same harness state as
    r207_prepare, and owner capital for exactly the rework wage (3 pcs x 1000) into its bank on the payment day (D14-3: an
    empty bank stays empty; the capital is the only money the chain receives)."""
    import cp7_period_cases as period,cp7_cash_funding as funding
    code='R207B'+uuid.uuid4().hex[:7].upper();day=today-timedelta(days=20)
    prev=cur.execute('select closed_through from erp.accounting_period_control where singleton_id=1').fetchone()[0]
    cur.execute("""update erp.accounting_period_control set closed_through=%s,updated_at=clock_timestamp(),updated_by=null,
        change_reason='CP17 R2-07 rework chain month' where singleton_id=1""",(day-timedelta(days=1),))
    quiet=period.aw.quiet_seed(cur,day-timedelta(days=1),day+timedelta(days=2));cases.b.api.admin(cur)
    bank=str(cases.bc.bank_account(cur,code));cases.b.api.admin(cur);funding.fund(cur,bank,'3000',today);cases.b.api.admin(cur)
    return dict(code=code,day=str(day),output_day=str(day+timedelta(days=1)),rework_day=str(day+timedelta(days=2)),opened_closed=str(day-timedelta(days=1)),
                previous_closed=None if prev is None else str(prev),bank=bank,
                bank_code=cur.execute('select cash_account_code from erp.cash_accounts where id=%s',(bank,)).fetchone()[0],
                quiet=dict(attendance=len(quiet['attendance']),approved=len(quiet['approved']),work_payrolls=len(quiet['work_payrolls']),refused=quiet['refused']))

def r207b_state(cur,p):
    c=p['code'];one=lambda sql,args=():cur.execute(sql,args).fetchone()
    batch=one('select id::text,status from erp.migration_batches where batch_code=%s',(c,))
    loc=one('select id::text from erp.locations where location_code=%s',(c+'F',))
    mandor=one('select id::text from erp.contractors where contractor_code=%s',(c,))
    po=one('select id::text from erp.production_orders where po_number=%s',(c,))
    wip=one("""select s.opening_item_id::text from erp.initial_import_production_sources s join erp.opening_balance_items i on i.id=s.opening_item_id
        where s.batch_id=%s and i.balance_type='WIP'""",(batch[0],)) if batch else None
    bs=one('select id::text,bs_number,qty_pcs from erp.bs_cases where po_id=%s order by created_at desc limit 1',(po[0],)) if po else None
    comps=cur.execute('''select wc.component_code,bcc.completed_before_bs_qty from erp.bs_case_components bcc
        join erp.work_components wc on wc.id=bcc.work_component_id where bcc.bs_case_id=%s order by 1''',(bs[0],)).fetchall() if bs else []
    rw=one('select status,qty_good_returned,qty_bs_returned from erp.rework_orders where rework_number=%s',(c+'-RW',))
    recipe=[r[0] for r in cur.execute('''select(select count(*)from erp.accessory_bom_items i where i.bom_version_id=v.id)::int
        from erp.accessory_bom_versions v join erp.products p on p.id=v.product_id where p.sku=%s and p.identity_root_id=p.id
        order by v.effective_from,v.id''',(c+'A',)).fetchall()]
    note=one('select status,posted_payroll_id::text from cp7_payroll.notes where contractor_id=%s order by created_at desc limit 1',(mandor[0],)) if mandor else None
    payroll=one('select id::text,status,labor_total::text,net_payable::text from erp.payroll_settlements where contractor_id=%s order by created_at desc limit 1',(mandor[0],)) if mandor else None
    bank=one("""select coalesce(sum(jl.debit-jl.credit),0)::text from erp.journal_lines jl join erp.journal_entries je on je.id=jl.journal_entry_id
        where je.status='POSTED' and jl.account_id=(select a.coa_account_id from erp.cash_accounts a where a.id=%s)""",(p['bank'],))[0]
    return dict(batch=None if not batch else dict(id=batch[0],status=batch[1]),location=None if not loc else loc[0],mandor=None if not mandor else mandor[0],
        wip_item=None if not wip else wip[0],bs=None if not bs else dict(id=bs[0],number=bs[1],qty=int(bs[2]),components=[[k,int(q)] for k,q in comps]),
        recipe=recipe,rework=None if not rw else dict(status=rw[0],good=int(rw[1] or 0),bs=int(rw[2] or 0)),
        note=None if not note else dict(status=note[0],payroll=note[1]),
        payroll=None if not payroll else dict(id=payroll[0],status=payroll[1],labor=payroll[2],net=payroll[3]),bank_balance=bank)

def r207_restore(cur,p):
    cur.execute("""update erp.accounting_period_control set closed_through=%s,updated_at=clock_timestamp(),updated_by=null,
        change_reason='CP17 R2-07 harness state restored' where singleton_id=1""",(p['previous_closed'],))
    return dict(closed_through=p['previous_closed'])

def main():
    target=os.environ['AUDITOR_BROWSER_DB_URL'];url=urlparse(target)
    assert url.hostname in('localhost','127.0.0.1')and url.path=='/cp6_auditor_browser','DISPOSABLE_BROWSER_ONLY'
    p=json.load(sys.stdin);operation=sys.argv[1]
    with psycopg.connect(target)as conn,conn.cursor()as cur:
        had=cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        acl=cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
        if not had:cur.execute('grant usage on schema erp to authenticated')
        one=lambda sql,args=():cur.execute(sql,args).fetchone()
        if operation=='pickup':
            f=cases.pickup_fixture(cur,date.fromisoformat(p['today']));cases.b.api.admin(cur)
            out=dict(group=f['group'],po=f['po'],pickup=f['pickup'],mandor=f['mandor'],executor=f['executor'],
                     po_before=[None if x is None else str(x) for x in f['po_before']],
                     number=one('select group_number from erp.cutting_groups where id=%s',(f['group'],))[0])
        elif operation=='sewing':
            f=cases.pickup_fixture(cur,date.fromisoformat(p['today']));cases.work_rates(cur,f);cases.b.api.admin(cur)
            out=dict(group=f['group'],po=f['po'],mandor=f['mandor'],number=one('select group_number from erp.cutting_groups where id=%s',(f['group'],))[0])
        elif operation=='sewing_state':
            ready=cases.sewn_ready(cur,dict(group=p['group']))
            works=cur.execute("select id::text from erp.work_completion_events where cutting_group_id=%s and status='POSTED' order by created_at",(p['group'],)).fetchall()
            wage=[[str(x) for x in cases.wage_journal(cur,w[0])] for w in works]
            out=dict(sewn=ready[0],ready=ready[1],posted_work=len(works),wage=wage,
                     history=one('select count(*) from cp7_cutting_correction.sewing_history where group_id=%s',(p['group'],))[0])
        elif operation=='finish':
            f=cases.finish_fixture(cur,date.fromisoformat(p['today']));cases.b.api.admin(cur)
            out=dict(po=f['po'],number=f['number'])
        elif operation=='finish_state':
            st=cases.po_state(cur,p['po']);total,qty=cases.po_hpp(cur,p['po'])
            per=(total/qty).quantize(cases.D('0.01'),rounding=cases.ROUND_HALF_UP) if qty else None
            text=None if per is None else (lambda w,c:'{:,}'.format(int(w)).replace(',','.')+('' if c=='00' else ','+c))(*str(per).split('.'))
            closes=one("""select count(*) filter(where j.status='POSTED'),coalesce(sum(e.residual_amount) filter(where j.status='REVERSED'),0)
                from erp.po_wip_close_events e join erp.journal_entries j on j.id=e.journal_entry_id where e.po_id=%s and j.source_type='PO_WIP_RESIDUAL_CLOSE'""",(p['po'],))
            # erp.get_hpp_completeness lists a PO only for an OWNER/ADMIN/STAFF caller (erp.current_app_role()); read it as the
            # production owner, as the screen's facade does for its user, then return to the admin session.
            cases.b.chain.production.owner(cur);display=one('select x.display_status from erp.get_hpp_completeness(%s) x',(p['po'],))[0];cases.b.api.admin(cur)
            out=dict(status=st['status'],wip=str(cases.D(st['wip']).quantize(cases.D('0.01'))),history=st['history'],per_pcs=None if per is None else str(per),per_pcs_text=text,
                     display_status=display,posted_closes=closes[0],
                     reversed_residual=str(cases.D(closes[1]).quantize(cases.D('0.01'))),
                     reopen_history=one('select count(*) from cp7_cutting_correction.po_reopen_history where po_id=%s',(p['po'],))[0])
        elif operation=='pickup_state':
            pk=one('select status,reversal_reason from erp.cutting_pickups where id=%s',(p['pickup'],))
            g=one('select status,picked_up_at,executor_name,material_issue_posted from erp.cutting_groups where id=%s',(p['group'],))
            po=one('select status,current_stage,contractor_id from erp.production_orders where id=%s',(p['po'],))
            out=dict(pickup_status=pk[0],reversal_reason=pk[1],group_status=g[0],picked_up_at=g[1],executor=g[2],fabric_posted=g[3],
                     po=[None if x is None else str(x) for x in po],
                     history=one('select count(*) from cp7_cutting_correction.pickup_history where pickup_id=%s',(p['pickup'],))[0],
                     active_pickups=one("select count(*) from erp.cutting_pickups where cutting_group_id=%s and status in('DRAFT','POSTED')",(p['group'],))[0])
        elif operation=='fabric':
            f=cases.fabric_fixture(cur,date.fromisoformat(p['today']));cases.b.api.admin(cur)
            out=dict(f,number=one('select group_number from erp.cutting_groups where id=%s',(f['group'],))[0],
                     roll_number=one('select roll_number from erp.material_rolls where id=%s',(f['roll'],))[0],
                     stock=str(one('select coalesce(sum(qty_signed),0) from erp.material_stock_movements where roll_id=%s and location_id=%s',(f['roll'],f['location']))[0]))
        elif operation=='fabric_state':
            out=dict(stock=str(one('select coalesce(sum(qty_signed),0) from erp.material_stock_movements where roll_id=%s and location_id=%s',(p['roll'],p['location']))[0]),
                     returns=one("select count(*) from erp.material_stock_movements where source_type='CUTTING_GROUP_RETURN' and source_id=%s",(p['group'],))[0],
                     return_posted=one('select material_return_posted from erp.cutting_groups where id=%s',(p['group'],))[0],
                     history=one('select count(*) from cp7_cutting_correction.return_history where group_id=%s',(p['group'],))[0],
                     active=one("select count(*) from erp.material_stock_movements m where m.source_type='CUTTING_GROUP_RETURN' and m.source_id=%s and not exists(select 1 from erp.material_stock_movements v where v.reversal_of_id=m.id)",(p['group'],))[0],
                     active_qty=str(one("select coalesce(sum(m.qty_signed),0) from erp.material_stock_movements m where m.source_type='CUTTING_GROUP_RETURN' and m.source_id=%s and not exists(select 1 from erp.material_stock_movements v where v.reversal_of_id=m.id)",(p['group'],))[0]),
                     reversal_history=one('select count(*) from cp7_cutting_correction.return_reversal_history where group_id=%s',(p['group'],))[0])
        elif operation=='kasbon':
            # A work-only payroll draft (6000.00, Native Nota) for a fresh Mandor and a bank holding owner capital.
            f=cases.s.review.fixture(cur,date.fromisoformat(p['today']));bank=cases.s.cash(cur);cases.b.api.admin(cur)
            label='Mandor Kasbon '+uuid.uuid4().hex[:8]
            cur.execute('update erp.contractors set contractor_name=%s where id=%s',(label,f['contractor']))
            out=dict(contractor=str(f['contractor']),payroll=str(f['payroll']),bank=str(bank),label=label,
                     payroll_number=one('select payroll_number from erp.payroll_settlements where id=%s',(f['payroll'],))[0])
        elif operation=='kasbon_state':
            advances=cur.execute('select number,amount::text,status,advance_date::text from cp7_kasbon.advances where contractor_id=%s order by created_at',(p['contractor'],)).fetchall()
            pay=one('select status,deduction_total::text,net_payable::text from erp.payroll_settlements where id=%s',(p['payroll'],))
            out=dict(advances=[list(a) for a in advances],payroll=list(pay),bank=str(cases.balance(cur,p['bank'])),receivable=str(cases.receivable(cur,p['contractor'])),
                     links=one('select count(*) from cp7_kasbon.deduction_links where payroll_id=%s',(p['payroll'],))[0],
                     kasbon_journals=one("select count(*) from erp.journal_entries j join cp7_kasbon.advances a on a.journal_id=j.id where a.contractor_id=%s and j.status='POSTED'",(p['contractor'],))[0])
        elif operation=='master_state':out=master_state(cur,p)
        elif operation=='rate_state':out=rate_state(cur,p)
        elif operation=='master_model':
            code='MDL-'+uuid.uuid4().hex[:8].upper()
            out=dict(code=code,model=str(cur.execute('insert into erp.product_models(model_code,model_name)values(%s,%s)returning id',(code,'Model layar '+code)).fetchone()[0]))
        elif operation=='master_used_customer':
            import cp7_sales_draft_cases as draft
            f=draft.fixture(cur,date.fromisoformat(p['today']));d=draft.create(cur,f);cases.b.api.admin(cur)
            out=dict(customer=f['customer'],sale=d['sale_id'],code=one('select customer_code from erp.customers where id=%s',(f['customer'],))[0])
        elif operation=='master_stocked_location':
            f=cases.cut.cutting.qc.physical.b.chain.production.estimated_receipt(cur,date.fromisoformat(p['today']));cases.b.api.admin(cur)
            out=dict(location=str(f['location']),code=one('select location_code from erp.locations where id=%s',(f['location'],))[0])
        elif operation=='chain':out=chain(cur,date.fromisoformat(p['today']))
        elif operation=='auto_po':out=auto_po(cur,date.fromisoformat(p['today']))
        elif operation=='cutover_state':
            import cp7_cutover_cases as cutover
            v,d=cutover.control(cur);out=dict(version=v,cutover_date=None if d is None else str(d),latest_allowed=str(cutover.latest(cur)[0]))
        elif operation=='cutover_reset':
            import cp7_cutover_cases as cutover
            cutover.reset(cur,cutover.owner(cur));v,d=cutover.control(cur);out=dict(version=v,cutover_date=str(d))
        elif operation=='wave_sewing':
            # Sol R2-10: the native cases' wave fixture (three sizes, SKU A on S+M, SKU B on L), committed.
            import cp7_wave_sewing_cases as wave
            g=wave.fixture(cur,date.fromisoformat(p['today']));cases.b.api.admin(cur)
            out=dict(group=g['group'],po=g['po'],number=g['number'],A=dict(id=g['A']['id'],sku=g['A']['sku']),B=dict(id=g['B']['id'],sku=g['B']['sku']))
        elif operation=='wave_sewing_state':
            # Native rows only: per POSTED completion its SKU (from the line snapshots), pieces and wage journal.
            ready=cases.sewn_ready(cur,dict(group=p['group']))
            works=cur.execute("""select e.id::text,(select string_agg(distinct k.sku,',') from erp.work_completion_lines l join erp.po_work_component_snapshots x on x.id=l.po_component_snapshot_id
                join erp.bf_sku_versions_v1 v on v.id=x.bf_sku_version_id join erp.bf_skus_v1 k on k.id=v.sku_id where l.completion_id=e.id),
                (select max(l.qty_completed) from erp.work_completion_lines l where l.completion_id=e.id)
                from erp.work_completion_events e where e.cutting_group_id=%s and e.status='POSTED' order by 2""",(p['group'],)).fetchall()
            out=dict(sewn=ready[0],ready=ready[1],posted=[[sku,int(q),[str(x) for x in cases.wage_journal(cur,w)]] for w,sku,q in works],
                     history=one('select count(*) from cp7_cutting_correction.sewing_wave_history where group_id=%s',(p['group'],))[0])
        elif operation=='r207_prepare':out=r207_prepare(cur,date.fromisoformat(p['today']))
        elif operation=='r207_state':out=r207_state(cur,p)
        elif operation=='r207_restore':out=r207_restore(cur,p)
        elif operation=='r207b_prepare':out=r207b_prepare(cur,date.fromisoformat(p['today']))
        elif operation=='r207b_state':out=r207b_state(cur,p)
        elif operation=='auto_po_state':out=auto_po_state(cur,p)
        elif operation=='chain_state':out=chain_state(cur,p)
        elif operation=='series':out=series(cur,date.fromisoformat(p['today']))
        elif operation=='series_state':out=series_state(cur,p)
        else:raise ValueError('Unknown CP17 browser fixture operation')
        cases.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
