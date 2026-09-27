"""Independent daily BD continuation. Controlled production precursor; no writer tests."""
import suite as s
import json,traceback,hashlib,copy
from decimal import Decimal as D
from psycopg.types.json import Jsonb
import psycopg
C=s.CTX;R=s.RESULTS;E=s.EVENTS;admin=s.admin;eq=s.eq;cmd=s.command;uid=s.uid
F={}
def save():
    (s.OUT/'daily-results.json').write_text(json.dumps({'candidate':'08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec','scope':'Independent daily laundry/QC/HPP continuation','results':R,'production_go':False},indent=2,default=str)+'\n')
    (s.OUT/'daily-events.json').write_text(json.dumps(E,indent=2,default=str)+'\n')
    (s.OUT/'daily-fixture.json').write_text(json.dumps({'identity':C,'sources':F},indent=2,default=str)+'\n')
s.save=save
def row(table,id):return admin('select to_jsonb(t) from erp.'+table+' t where id=%s',(id,),one=True)
def ver(table,id):return admin('select row_version from erp.'+table+' where id=%s',(id,),one=True)
def rpc(action,payload,version,request=None):
    req=request or uid();event={'api':'public.erp_save_laundry_qc_action_v1','action':action,'payload':payload,'version':version,'request':req}
    try:
        with s.actor_conn() as c:r=c.execute('select public.erp_save_laundry_qc_action_v1(%s,%s,%s::uuid,%s)',(action,Jsonb(payload),req,version)).fetchone()[0]
        event['response']=r;return r
    except psycopg.Error as e:event.update(error=str(e),sqlstate=e.sqlstate);raise
    finally:E.append(event)
def fp():
    names=['laundry_deliveries','laundry_delivery_lines','laundry_receipts','laundry_receipt_lines','wip_stage_events','fg_stock_movements','fg_lots','hpp_versions','journal_entries','journal_lines','bd_requests_v1','bd_laundry_priced_lines_v1','bd_laundry_charge_lines_v1','bd_laundry_invoices_v1','bd_laundry_invoice_lines_v1']
    return {n:admin("select md5(coalesce(string_agg(to_jsonb(t)::text,'' order by to_jsonb(t)::text),'')) from erp."+n+' t',one=True) for n in names}
def refuse(fn):
    before=fp()
    try:fn()
    except psycopg.Error as e:
        eq(e.sqlstate,'P0001','Expected domain refusal, not broken adapter');eq(fp(),before,'Rejected transaction left no effects')
        return {'sqlstate':e.sqlstate,'message':str(e),'unchanged':before}
    raise AssertionError('Expected refusal; operation accepted')
def precursor(key):
    f={k:uid() for k in ['po','group','cb','roll','groll','pickup','batch','work','snap']};f['key']=key
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('app.change_reason','Independent controlled prerequisite',true)")
        c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],))
        c.execute("insert into erp.production_orders(id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at) values(%s,%s,%s,%s,13,'SEWING','SEWING','2026-09-10T08:00:00+07:00')",(f['po'],'AUD-DAY-'+key,C['model'],C['mandor']))
        c.execute("insert into erp.cutting_batches(id,po_id,batch_number,cut_at) values(%s,%s,%s,'2026-09-10T08:00:00+07:00')",(f['cb'],f['po'],'AUD-CUT-'+key))
        c.execute("insert into erp.cutting_groups(id,po_id,group_number,cut_at,picked_up_at,status,cutting_batch_id,pattern_id,source_location_id,material_issue_posted) values(%s,%s,%s,'2026-09-10T08:00:00+07:00','2026-09-11T08:00:00+07:00','SEWING',%s,%s,%s,true)",(f['group'],f['po'],'AUD-GROUP-'+key,f['cb'],C['pattern'],C['rawloc']))
        c.execute("insert into erp.material_rolls(id,material_id,roll_number,original_qty,cached_qty,received_at) values(%s,%s,%s,13,0,'2026-09-09T08:00:00+07:00')",(f['roll'],C['material'],'AUD-ROLL-'+key))
        c.execute("insert into erp.cutting_group_rolls(id,cutting_group_id,roll_id,qty_issued,qty_consumed,qty_reported_remaining,unit_cost_snapshot) values(%s,%s,%s,13,13,0,0)",(f['groll'],f['group'],f['roll']))
        c.execute("insert into erp.cutting_pickups(id,cutting_group_id,contractor_id,picked_up_at,allocation_mode,status,created_by,posted_by,posted_at) values(%s,%s,%s,'2026-09-11T08:00:00+07:00','SIZE','POSTED',%s,%s,'2026-09-11T08:00:00+07:00')",(f['pickup'],f['group'],C['mandor'],C['app_owner'],C['app_owner']))
        c.execute('insert into erp.cutting_distribution_batches(id,pickup_id,batch_no) values(%s,%s,1)',(f['batch'],f['pickup']))
        for slot,(size,qty) in enumerate([(C['s1'],7),(C['s2'],6)],1):
            sid,yid=uid(),uid()
            c.execute('insert into erp.cutting_group_size_slots(id,cutting_group_id,slot_no,size_id,drawing_no) values(%s,%s,%s,%s,1)',(sid,f['group'],slot,size))
            c.execute('insert into erp.cutting_roll_yields(id,cutting_group_roll_id,size_slot_id,qty_pcs) values(%s,%s,%s,%s)',(yid,f['groll'],sid,qty))
            c.execute('insert into erp.cutting_distribution_allocations(batch_id,cutting_roll_yield_id,qty_pcs) values(%s,%s,%s)',(f['batch'],yid,qty))
        c.execute("insert into erp.wip_stage_events(po_id,cutting_group_id,stage_from,stage_to,qty_pcs,contractor_id,source_type,source_id,physical_at,created_by) values(%s,%s,'CUTTING','SEWING',13,%s,'AUDIT_PREREQUISITE',%s,'2026-09-11T08:00:00+07:00',%s)",(f['po'],f['group'],C['mandor'],f['pickup'],C['app_owner']))
        c.execute("insert into erp.po_work_component_snapshots(id,po_id,work_component_id,rate_per_pcs_snapshot,committed_at) values(%s,%s,%s,100,'2026-09-11T08:00:00+07:00')",(f['snap'],f['po'],C['work_component']))
        c.execute("insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,created_by) values(%s,%s,%s,%s,%s,'2026-09-12T08:00:00+07:00',%s)",(f['work'],'AUD-WORK-'+key,f['po'],C['mandor'],f['group'],C['app_owner']))
        c.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot) values(%s,%s,%s,13,13,100)',(f['work'],f['snap'],C['work_component']))
        c.execute('select erp.post_work_completion(%s)',(f['work'],))
        r=c.execute('select erp.record_sewing_terminal_v1(%s,%s::uuid)',(Jsonb({'work_completion_id':f['work'],'qty_pcs':13,'reason':'Independent production prerequisite'}),uid())).fetchone()[0]
        f['sewing_terminal']=r
    F[key]=f
    eq(admin('select total_pcs from erp.v_cutting_group_totals where cutting_group_id=%s',(f['group'],),one=True),13)
    eq(admin('select unsent_ready_qty_pcs from erp.v_wip_control_status_v1 where cutting_group_id=%s',(f['group'],),one=True),13)
    E.append({'setup_boundary':'Seed cut and pickup; native posted work and sewing terminal. Not cutting/pickup acceptance proof.','fixture':f})
    return f
def setup():
    C.update(json.loads((s.OUT/'fixture-identities.json').read_text()))
    C['app_owner']=str(admin('select id from erp.app_users where auth_user_id=%s',(C['owner'],),one=True))
    C.update({k:uid() for k in ['model','brand','brand2','mandor','material','rawloc','fg','pattern','work_component','customer','daily_vendor']})
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('app.change_reason','Independent daily master prerequisite',true)")
        c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],))
        for key in ['brand','brand2']:c.execute('insert into erp.brands(id,brand_code,brand_name) values(%s,%s,%s)',(C[key],'AUD-'+key,'AUD-'+key))
        c.execute("insert into erp.product_models(id,model_code,model_name) values(%s,'AUD-DAY','Independent daily model')",(C['model'],))
        c.execute("insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,attendance_required) values(%s,'AUD-DAY','Independent mandor','MANDOR',false)",(C['mandor'],))
        c.execute("insert into erp.materials(id,material_sku,material_name,material_type,unit_code) values(%s,'AUD-DAY-FABRIC','Controlled zero-value source fabric','FABRIC','METER')",(C['material'],))
        for key,kind in [('rawloc','RAW_MATERIAL_WAREHOUSE'),('fg','FG_WAREHOUSE')]:c.execute('insert into erp.locations(id,location_code,location_name,location_type) values(%s,%s,%s,%s)',(C[key],'AUD-'+key,'AUD-'+key,kind))
        c.execute("insert into erp.production_patterns(id,pattern_code,pattern_name) values(%s,'AUD-DAY','Independent pattern')",(C['pattern'],))
        c.execute("insert into erp.work_components(id,component_code,component_name) values(%s,'AUD-DAY-SEW','Independent sewing work')",(C['work_component'],))
        c.execute("insert into erp.customers(id,customer_code,customer_name) values(%s,'AUD-DAY','Independent customer')",(C['customer'],))
        c.execute("insert into erp.laundry_vendors(id,vendor_code,vendor_name) values(%s,'AUD-DAY','Independent daily vendor')",(C['daily_vendor'],))
        C['products']={}
        for size in [C['s1'],C['s2']]:
            for brand in [C['brand'],C['brand2']]:
                pid=uid();C['products'][size+':'+brand]=pid
                c.execute("insert into erp.products(id,identity_root_id,sku,model_id,brand_id,color_name,size_id,product_name,effective_from) values(%s,%s,%s,%s,%s,'AUD-NAVY',%s,'Independent same-SKU different-brand product','2026-09-01T08:00:00+07:00')",(pid,pid,'AUD-DAY-'+str([C['s1'],C['s2']].index(size)),C['model'],brand,size))
    C['daily_wash']=s.component(C['daily_vendor'],'AUD-WASH');C['daily_finish']=s.component(C['daily_vendor'],'AUD-FINISH');C['daily_unknown']=s.component(C['daily_vendor'],'AUD-UNKNOWN')
    s.rate(C['daily_wash'],'4321.09');s.rate(C['daily_finish'],'678.91');s.rate(C['daily_unknown'],None,status='UNKNOWN')
    s.policy('LAU_DEC01',{'units':['BATCH']});s.terms('COMPONENTS',vendor=C['daily_vendor'])
    s.policy('LAU_DEC02',{'billable':['GOOD']});s.policy('LAU_DEC04',{'sale_with_unknown_laundry':'ALLOW_PENDING'})
    s.policy('LAU_DEC06',{'variance_mode':'PRODUCT_COST','after_payment':'CORRECTION_DOCUMENT'})
    for key in ['K','U','R']:precursor(key)
    return {'sources':F,'controlled_labor_cost_each':'1300.00'}
def dp(key,unknown=False,at='2026-09-15T00:01:00+07:00'):
    f=F[key]
    return {'expected_version':str(ver('cutting_groups',f['group'])),'delivery':{'distribution_batch_id':f['batch'],'vendor_id':C['daily_vendor'],'wash_process_id':C['process'],'target_dyeing_color':'AUD-NAVY','physical_at':at,'reason':'Independent daily shipment','lines':[{'size_id':C['s1'],'qty_sent_pcs':7},{'size_id':C['s2'],'qty_sent_pcs':6}]},'pricing':{'components':[{'component_id':C['daily_wash'],'covered_qty':13},{'component_id':C['daily_unknown'] if unknown else C['daily_finish'],'covered_qty':5}]}}
def ship(key,unknown=False):
    f=F[key];p=dp(key,unknown);req=uid();r=cmd('POST_PRICED_DELIVERY',p,req);f.update(delivery=r['delivery_id'],shipment_request=req,shipment_payload=p)
    line=admin('select id::text from erp.laundry_delivery_lines where delivery_id=%s',(r['delivery_id'],),one=True);f['delivery_line']=line
    eq(D(r['pricing']['total_known']),D('56174.17' if unknown else '59568.72'));eq(r['pricing']['total_complete'],not unknown);eq(r['pricing']['qty_sent'],13)
    eq(admin("select sum(qty_pcs) from erp.wip_stage_events where source_type='LAUNDRY_DELIVERY_LINE' and source_id=%s",(line,),one=True),13)
    f['pricing_snapshot']=r['pricing'];return r
def replay_ship():
    f=F['K'];before=fp();r=cmd('POST_PRICED_DELIVERY',f['shipment_payload'],f['shipment_request']);eq(fp(),before);eq(r['delivery_id'],f['delivery']);return r
def day_boundary():
    f=F['K']
    physical=admin("select physical_at::text,(physical_at at time zone 'Asia/Jakarta')::date::text from erp.laundry_deliveries where id=%s",(f['delivery'],))[0]
    dates=admin("select distinct transaction_date::text,economic_date::text from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id where l.po_id=%s and l.account_id=erp.account_id('ACCRUED_MANUFACTURING')",(f['po'],))
    eq(physical[1],'2026-09-15');eq(dates,[('2026-09-15','2026-09-15')])
    return {'physical_utc_and_business_date':physical,'accrual_dates':dates}
def reverse_unused():
    f=F['R'];ship('R');r=rpc('REVERSE_DELIVERY',{'delivery_id':f['delivery'],'reason':'Independent unused shipment reversal'},ver('laundry_deliveries',f['delivery']))
    eq(r['status'],'REVERSED')
    eq(admin('select unsent_ready_qty_pcs from erp.v_wip_control_status_v1 where cutting_group_id=%s',(f['group'],),one=True),13)
    eq(admin("select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.po_id=%s and l.account_id=erp.account_id('ACCRUED_MANUFACTURING') and j.status in('POSTED','REVERSED')",(f['po'],),one=True),D(0))
    f['reversed']=r;return r
def snapshot():
    f=F['K'];before=row('laundry_delivery_lines',f['delivery_line']);prices=admin('select to_jsonb(t) from erp.bd_laundry_charge_lines_v1 t where delivery_line_id=%s order by line_no',(f['delivery_line'],))
    s.rate(C['daily_wash'],'9000.17','2026-09-20T08:00:00+07:00')
    eq(row('laundry_delivery_lines',f['delivery_line']),before);eq(admin('select to_jsonb(t) from erp.bd_laundry_charge_lines_v1 t where delivery_line_id=%s order by line_no',(f['delivery_line'],)),prices)
    return {'posted_snapshot_preserved':prices}
def rp(key,at='2026-09-21T00:01:00+07:00',extra=0):
    f=F[key];xs=admin('select id::text,qty_sent_pcs from erp.laundry_delivery_batch_size_lines where delivery_line_id=%s order by size_id',(f['delivery_line'],))
    return {'delivery_id':f['delivery'],'wash_process_id':C['process'],'physical_at':at,'reason':'Independent receipt','lines':[{'delivery_batch_size_line_id':i,'qty_good_received':n+(extra if k==0 else 0),'qty_bs_laundry':0,'bs_product_id':None} for k,(i,n) in enumerate(xs)]}
def receive(key):
    f=F[key];r=rpc('POST_RECEIPT',rp(key),ver('laundry_deliveries',f['delivery']));f['receipt']=r['receipt_id'];f['receipt_line']=admin('select id::text from erp.laundry_receipt_lines where receipt_id=%s',(f['receipt'],),one=True)
    eq(r['good_qty_pcs'],13);eq(r['bs_qty_pcs'],0)
    if key=='K':eq(D(r['actual_cost']),D('59568.72'))
    eq(admin('select sum(qty_good_received+qty_bs_laundry) from erp.laundry_receipt_lines where receipt_id=%s',(f['receipt'],),one=True),13)
    return r
def qp(key):
    f=F[key];xs=admin('select id::text,size_id::text,qty_good_received from erp.laundry_receipt_batch_size_lines where receipt_line_id=%s order by size_id',(f['receipt_line'],))
    return {'cutting_group_id':f['group'],'destination_location_id':C['fg'],'physical_at':'2026-09-21T08:00:00+07:00','reason':'Independent final SKU','good_qty_pcs':13,'completion_mode':'ALL_READY','lines':[{'final_product_id':C['products'][size+':'+(C['brand2'] if key=='U' else C['brand'])],'qty_good_pcs':qty,'qty_bs_pcs':0,'source_laundry_receipt_line_id':f['receipt_line'],'source_laundry_receipt_batch_size_line_id':i} for i,size,qty in xs]}
def hpp(key):
    return admin('select l.id::text,l.product_id::text,l.initial_qty_pcs,l.cached_qty_pcs,h.total_cost,h.hpp_per_pcs,h.cost_state from erp.fg_lots l join erp.hpp_versions h on h.lot_id=l.id and h.is_current where l.po_id=%s order by l.product_id',(F[key]['po'],))
def qty(key):return admin('select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id where l.po_id=%s',(F[key]['po'],),one=True)
def costeq(key,expected):
    values=hpp(key);eq(sum(x[4] for x in values).quantize(D('.01')),D(expected),'Independent total HPP');return values
def finalsku(key):
    f=F[key];r=rpc('POST_FINAL_SKU',qp(key),ver('cutting_groups',f['group']));f['qc']=r['qc_inspection_id'];eq(qty(key),13)
    expected='60868.72' if key=='K' else '57474.17';values=costeq(key,expected)
    eq({x[1] for x in values},{C['products'][z+':'+(C['brand2'] if key=='U' else C['brand'])] for z in [C['s1'],C['s2']]},'Exact product identities')
    return {'response':r,'hpp':values,'net_fg':qty(key)}
def sell(key):
    f=F[key];payload={'sale_number':'AUD-DAY-'+key,'customer_id':C['customer'],'source_location_id':C['fg'],'sale_date':'2026-09-22T08:00:00+07:00','reason':'Independent pending-cost sale','items':[{'product_id':C['products'][C['s1']+':'+(C['brand2'] if key=='U' else C['brand'])],'qty_pcs':4,'unit_price_snapshot':'20000.00','discount_amount':'0.00'}]}
    # The existing sales interface exposes native ERP commands; privileged calls
    # here test accounting integration, not a public HTTP authorization boundary.
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],))
        r=c.execute('select erp.save_sale_draft_v2(%s,%s::uuid,null)',(Jsonb(payload),uid())).fetchone()[0]
        sid=r['sale_id'];c.execute('select erp.post_sale(%s)',(sid,))
    f['sale']=sid;E.append({'native_sales_payload':payload,'response':r,'layer':'ERP native under postgres with owner identity; NOT HTTP proof'})
    # Both fixture POs use the same products: FIFO must bind the sale's actual lot.
    alloc=admin('select a.id::text,l.po_id::text,a.qty_pcs,a.unit_hpp_snapshot from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id join erp.fg_lots l on l.id=a.lot_id where i.sale_id=%s',(sid,))
    eq(sum(x[2] for x in alloc),4);f['sale_allocations']=alloc
    if any(x[1]!=f['po'] for x in alloc):raise AssertionError('Fixture FIFO selected sibling PO; independent source isolation required: '+str(alloc))
    eq(qty(key),9)
    markers=admin('select to_jsonb(t) from erp.bd_pending_price_sales_v1 t where sale_id=%s',(sid,))
    if key=='U':assert markers,'Unknown-priced sale missing pending marker'
    return {'sale_id':sid,'allocation':alloc,'pending_markers':markers,'fg_qty':qty(key)}
def invoice(key,amount='61246.24',date='2026-09-23'):
    f=F[key];before=qty(key)
    d=cmd('SAVE_INVOICE_DRAFT',{'vendor_id':C['daily_vendor'],'invoice_number':'AUD-DAY-INVOICE-'+key,'invoice_date':date,'header_total':amount,'lines':[{'line_kind':'BILL','receipt_line_id':f['receipt_line'],'category':'GOOD','qty':13,'amount':amount,'note':'Independent daily invoice'}]})
    r=cmd('POST_INVOICE',{'invoice_id':d['invoice_id'],'expected_version':str(d['row_version'])});f['invoice']=r
    eq(qty(key),before,'Invoice cannot change physical stock');values=costeq(key,'62546.24')
    line=admin('select released_estimate,variance,product_variance from erp.bd_laundry_invoice_lines_v1 where invoice_id=%s',(r['invoice_id'],))[0];eq(line,(D('59568.72'),D('1677.52'),D('1677.52')))
    return {'response':r,'released_variance':line,'hpp':values,'qty_preserved':before}
def resolve_unknown():
    f=F['U'];ch=admin("select id::text from erp.bd_laundry_charge_lines_v1 where delivery_line_id=%s and rate_status='UNKNOWN'",(f['delivery_line'],),one=True)
    before=qty('U');r=cmd('SET_CHARGE_PRICE',{'charge_line_id':ch,'rate_per_pcs':'678.91','reason':'Independent agreement after physical processing'});eq(D(r['total_known']),D('59568.72'));eq(r['complete'],True);eq(qty('U'),before);values=costeq('U','60868.72')
    return {'response':r,'hpp':values,'fg_unchanged':before}
def return_one(key):
    f=F[key];allocation=f['sale_allocations'][0][0];ret=uid()
    with psycopg.connect(s.DSN) as c:
        c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['owner'],));c.execute("select set_config('app.change_reason','Independent linked customer return',true)")
        c.execute("insert into erp.sales_returns(id,return_number,sale_id,customer_id,physical_at,created_by) values(%s,%s,%s,%s,'2026-09-24T08:00:00+07:00',%s)",(ret,'AUD-RETURN-'+key,f['sale'],C['customer'],C['app_owner']))
        c.execute('insert into erp.sales_return_items(return_id,sale_stock_allocation_id,product_id,lot_id,location_id,qty_pcs,refund_amount) select %s,a.id,l.product_id,l.id,a.location_id,1,20000 from erp.sale_stock_allocations a join erp.fg_lots l on l.id=a.lot_id where a.id=%s',(ret,allocation))
        c.execute('select erp.post_sales_return(%s)',(ret,))
    f['return']=ret;eq(qty(key),10);return {'return':row('sales_returns',ret),'items':admin('select to_jsonb(t) from erp.sales_return_items t where return_id=%s',(ret,)),'stock_qty':10}
def ledger(key):
    f=F[key];rows=admin("select a.account_code,a.account_name,sum(l.debit-l.credit) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id join erp.chart_accounts a on a.id=l.account_id where l.po_id=%s and j.status in('POSTED','REVERSED') group by a.id order by a.account_code",(f['po'],))
    # Inspect direct accounting rows; no product target-computation helper is oracle.
    E.append({'direct_po_ledger':key,'rows':rows})
    gl={m:D(admin("select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id where l.po_id=%s and l.account_id=erp.account_id(%s) and j.status in('POSTED','REVERSED')",(f['po'],m),one=True)) for m in ['WIP','FG_INVENTORY','COGS','AP_VENDOR','ACCRUED_MANUFACTURING']}
    # AP is recorded per vendor/invoice; it need not repeat a PO dimension.
    gl['AP_VENDOR']=D(admin("select coalesce(sum(l.debit-l.credit),0) from erp.journal_lines l where l.journal_entry_id=%s and l.account_id=erp.account_id('AP_VENDOR')",(f['invoice']['journal_id'],),one=True))
    total=D('62546.24');eq(gl['WIP'],D(0));eq(gl['FG_INVENTORY']+gl['COGS'],total,'FG plus COGS retains all labor and final laundry cost');eq(gl['AP_VENDOR'],-D('61246.24'));eq(gl['ACCRUED_MANUFACTURING'],D(0))
    return {'gl':gl,'raw_accounts':rows,'hpp':hpp(key),'fg_qty':qty(key)}
def case(id,title,fn,needs=()):
    missing=[k for key,k in needs if k not in F.get(key,{})]
    if missing:R.append({'id':id,'title':title,'status':'BLOCKED','dependency_missing':missing});save();return
    s.case(id,title,fn,'Public laundry/QC RPC; direct independent ledger readback; sales layer labeled separately')
def main():
    try:setup()
    except Exception as e:R.append({'id':'SETUP.DAILY','status':'BLOCKED','error':str(e),'traceback':traceback.format_exc()});save();raise
    case('IND-01.DAILY','13 physical PCS with partial component; posted 59568.72 estimate',lambda:ship('K'))
    case('IND-19.DELIVERY','Replay posted shipment has one physical and financial effect',replay_ship,[('K','delivery')])
    case('IND-35.DAILY','00:01 WIB shipment uses the local business day for accrual',day_boundary,[('K','delivery')])
    case('IND-05.POSTED','New master rate preserves posted charge snapshots',snapshot,[('K','delivery')])
    case('IND-12.DELIVERY','Second shipment cannot reuse consumed distribution capacity',lambda:refuse(lambda:cmd('POST_PRICED_DELIVERY',dp('K'))),[('K','delivery')])
    case('IND-33.PHYSICAL','Receipt before dispatch refused atomically',lambda:refuse(lambda:rpc('POST_RECEIPT',rp('K','2026-09-14T23:59:00+07:00'),ver('laundry_deliveries',F['K']['delivery']))),[('K','delivery')])
    case('IND-18.RECEIPT','Excess receipt leaves no partial physical/financial effects',lambda:refuse(lambda:rpc('POST_RECEIPT',rp('K',extra=1),ver('laundry_deliveries',F['K']['delivery']))),[('K','delivery')])
    case('IND-05.RECEIPT','Receipt after new master uses original 59568.72 estimate',lambda:receive('K'),[('K','delivery')])
    case('IND-06.FG','13 PCS enter exact FG identities with 60868.72 total HPP',lambda:finalsku('K'),[('K','receipt')])
    case('IND-30.KNOWN','Native sale moves four of thirteen PCS',lambda:sell('K'),[('K','qc')])
    case('IND-31.DAILY','Later invoice recosts 1677.52 without moving goods',lambda:invoice('K'),[('K','qc')])
    case('IND-32.DAILY','Native linked one-piece return after recost retains source',lambda:return_one('K'),[('K','sale_allocations')])
    case('IND-31.CONSERVATION','Independent WIP/FG/COGS/AP conservation after sale, invoice and return',lambda:ledger('K'),[('K','invoice'),('K','return')])
    case('IND-07.DELIVERY','Unknown component dispatches with incomplete price, not free',lambda:ship('U',True))
    case('IND-07.RECEIPT','Unknown price permits physical receipt',lambda:receive('U'),[('U','delivery')])
    case('IND-07.FG','Unknown price permits FG while preserving known costs',lambda:finalsku('U'),[('U','receipt')])
    # Separate product identity for U sales will be supplied by fixture isolation if FIFO requires it.
    case('IND-30.UNKNOWN','ALLOW_PENDING sale retains explicit unknown-laundry marker',lambda:sell('U'),[('U','qc')])
    case('IND-09.DAILY','Resolving unknown cost after processing updates HPP without stock duplication',resolve_unknown,[('U','qc')])
    case('IND-31.UNKNOWN','Invoice after resolving unknown price reconciles sold and remaining goods',lambda:invoice('U'),[('U','qc')])
    case('IND-10.OVERWRITE','Known posted charge cannot be overwritten',lambda:refuse(lambda:cmd('SET_CHARGE_PRICE',{'charge_line_id':admin('select id::text from erp.bd_laundry_charge_lines_v1 where delivery_line_id=%s order by line_no limit 1',(F['K']['delivery_line'],),one=True),'rate_per_pcs':'1.00','reason':'Independent overwrite attempt'})),[('K','delivery')])
    case('IND-25.DELIVERY','Unused shipment reversal restores sewing capacity and clears accrual',reverse_unused)
    save();print(json.dumps({'daily_counts':{x:sum(r['status']==x for r in R) for x in ['PASS','FAIL','BLOCKED']}}),flush=True)
    return int(any(r['status']!='PASS' for r in R))
if __name__=='__main__':raise SystemExit(main())
