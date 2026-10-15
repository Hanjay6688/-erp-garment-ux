"""CP17 browser fixtures (SG-01 pickup reversal, SG-02 fabric return, D14-6 kasbon, D14-5 dozens over a size series, D14-14 G1
sewing completion on the WIP & Sewing page) in the
disposable browser database only.

The same Native-writer fixtures as the native CP17 cases (cp7_cp17_fix_cases.pickup_fixture / fabric_fixture, the
settlement review payroll and a funded bank for kasbon); the state
readback is direct SQL on the rows the screens change, never the CP7 command's own answer.

D14-5: one SKU in three sizes (31/32/33, stock 10/11/12) and one SKU in one size (27, stock 20), each size a product of
its own with the SKU shared (commercial SKU = product SKU without a BF group), stock found at opname through the accepted
AX command (owner value only where no HPP reference exists yet, as the command requires).
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
    def sku(name,sizes):
        model=uuid.uuid4();out={}
        cur.execute('insert into erp.product_models(id,model_code,model_name,is_active) values(%s,%s,%s,true)',(model,'D145-'+model.hex[:10],'D14-5 '+name))
        for order,(code,qty) in enumerate(sizes):
            cur.execute('insert into erp.sizes(size_code,sort_order,is_active) values(%s,%s,true) on conflict(size_code) do nothing',(code,int(code)))
            size=cur.execute('select id from erp.sizes where size_code=%s',(code,)).fetchone()[0];product=uuid.uuid4()
            cur.execute('insert into erp.product_model_sizes(model_id,size_id,sort_order) values(%s,%s,%s) on conflict(model_id,size_id) do nothing',(model,size,order))
            cur.execute("""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from,is_active,is_portal_visible)
                select %s,%s,%s,brand_id,'D145',%s,%s,%s,effective_from,true,true from erp.products where id=%s""",(product,name,model,size,'Celana '+name,product,ax.chain.base.BASE_PRODUCT))
            cur.execute("insert into erp.accessory_bom_versions(product_id,version_label,effective_from,is_active,notes) values(%s,'D145-EMPTY','2026-01-01',true,'Explicit empty BOM')",(product,))
            tier=cur.execute('select erp.fg_unsourced_valuation_v1(%s,%s)',(product,at)).fetchone()[0]['tier']
            value=dict(owner_unit_value='10',owner_value_reason='D14-5 explicit independently supplied value') if tier=='OWNER_INPUT_REQUIRED' else {}
            posted=ax.post(cur,dict(source_kind='FOUND_AT_OPNAME',product_id=str(product),location_id=base.LOCATION,qty_pcs=qty,physical_at=at.isoformat(),reason='D14-5 series stock found at opname',**value))
            out[code]=dict(product=str(product),lot=cur.execute('select lot_id::text from erp.fg_unsourced_receipts_v1 where id=%s',(posted['receipt_id'],)).fetchone()[0],stock=qty)
        return out
    three=sku(tag+'-SERI',[('31',10),('32',11),('33',12)]);one=sku(tag+'-TUNGGAL',[('27',20)])
    customer=str(base.create_customer(cur,tag));ax.api.admin(cur)
    return dict(tag=tag,customer=customer,sale_at=(ax.r1.now(cur)-timedelta(minutes=7)).isoformat(),series_sku=tag+'-SERI',single_sku=tag+'-TUNGGAL',sizes=dict(three,**one),location=str(base.LOCATION))

def series_state(cur,p):
    import cp7_sales_cases as sales
    stock={code:int(cur.execute('select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s',(x['lot'],)).fetchone()[0]) for code,x in p['sizes'].items()}
    found=cur.execute('select id::text,status from erp.sales_headers where sale_number=%s',(p['tag'],)).fetchone()
    if not found:return dict(sale=None,stock=stock,gl=[[str(x) for x in r] for r in sales.gl(cur)])
    by_product={x['product']:code for code,x in p['sizes'].items()}
    items=cur.execute('select product_id::text,qty_pcs from erp.sales_items where sale_id=%s',(found[0],)).fetchall()
    return dict(sale=found[0],status=found[1],qty={by_product[pid]:int(q) for pid,q in items},lines=len(items),stock=stock,gl=[[str(x) for x in r] for r in sales.gl(cur)])

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
        elif operation=='series':out=series(cur,date.fromisoformat(p['today']))
        elif operation=='series_state':out=series_state(cur,p)
        else:raise ValueError('Unknown CP17 browser fixture operation')
        cases.b.api.admin(cur)
        if not had:cur.execute('revoke usage on schema erp from authenticated')
        assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]==acl
        conn.commit()
    print(json.dumps(out,default=str))
if __name__=='__main__':main()
