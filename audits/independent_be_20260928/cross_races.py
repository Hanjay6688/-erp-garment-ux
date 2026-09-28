"""Independent interleavings missing from the first BE report.
Every command is real; standalone controls roll back, competing executions commit.
"""
import threading,copy
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal as D
from psycopg.types.json import Jsonb
import psycopg
import native as n,flows as f,suite as s,daily as d,extended as e
C=n.C;A=n.A;eq=n.eq;uid=n.uid

def public(c,name,args):return c.execute('select public.'+name+'('+','.join(['%s']*len(args))+')',[Jsonb(x) if isinstance(x,dict) else x for x in args]).fetchone()[0]
def compete(operations):
    barrier=threading.Barrier(2)
    def invoke(i):
        barrier.wait()
        try:return {'index':i,'accepted':True,'result':operations[i]()}
        except psycopg.Error as ex:return {'index':i,'accepted':False,'sqlstate':ex.sqlstate,'error':str(ex)}
    with ThreadPoolExecutor(2) as pool:out=list(pool.map(invoke,[0,1]))
    n.E.append({'independent_real_concurrency':out});return out

def conversion_sale():
    loc=e.location('AUD-REV-RACE-STOCK');receipt=n.rpc('erp_post_fg_unsourced_receipt_v1',[{'source_kind':'FOUND_AT_OPNAME','product_id':C['product'],'location_id':loc,'qty_pcs':13,'physical_at':'2026-09-13T08:00:00+07:00','owner_unit_value':'1234.57','owner_value_reason':'Independent controlled race source','reason':'Independent shared stock for conversion and sale'},uid()]);lot=receipt['lot_id']
    row=n.ws({'source_lot_id':lot})['lots'][0];cp={'source_lot_id':lot,'target_product_id':C['target'],'location_id':loc,'qty_pcs':8,'physical_at':'2026-09-15T08:00:00+07:00','expected_version':row['source_revision'],'reason':'Independent conversion8 competing with sale8 from13'}
    sp={'sale_number':'AUD-REV-RACE-SALE','customer_id':C['customer'],'source_location_id':loc,'sale_date':'2026-09-16T08:00:00+07:00','reason':'Independent sale8 competing with conversion8 from13','items':[{'product_id':C['product'],'qty_pcs':8,'unit_price_snapshot':'20000.00','discount_amount':'0.00'}]};cr,sr=uid(),uid()
    def sell(c):
        c.execute("select set_config('request.jwt.claim.sub',%s,true)",(C['admin'],));r=c.execute('select erp.save_sale_draft_v2(%s,%s::uuid,null)',(Jsonb(sp),sr)).fetchone()[0];c.execute('select erp.post_sale(%s)',(r['sale_id'],));return r
    controls=[]
    with s.actor_conn() as c:
        controls.append({'operation':'conversion','response':public(c,'erp_save_product_conversion_action_v1',['POST',cp,cr]),'rolled_back':True});c.rollback()
    with psycopg.connect(s.DSN) as c:controls.append({'operation':'sale','response':sell(c),'rolled_back':True});c.rollback()
    before=e.gl()
    def post_conversion():return n.cmd('POST',cp,cr)
    def post_sale():
        with psycopg.connect(s.DSN) as c:return sell(c)
    out=compete([post_conversion,post_sale]);eq(sum(x['accepted'] for x in out),1);eq(n.lotqty(lot),5)
    failed=next(x for x in out if not x['accepted']);assert failed['sqlstate']=='P0001',failed
    now=e.gl();eq(sum(now[k]-before[k] for k in ['FG_INVENTORY','WIP','COGS']),D(0));eq(n.value(lot),D('6172.85'))
    winner=next(x for x in out if x['accepted'])
    if winner['index']==0:eq(n.lotqty(winner['result']['destination_lot_id']),8);eq(n.value(winner['result']['destination_lot_id']),D('9876.56'))
    else:eq(now['COGS']-before['COGS'],D('9876.56'))
    return {'controls':controls,'outcomes':out,'source_remaining':5,'source_value':'6172.85','eight_piece_value':'9876.56','inventory_plus_cogs_conserved':True,'layer':'Public authenticated conversion versus actual native sales posting under distinct owner/admin identities; native sale is not an HTTP authorization claim'}

def completion_invoice():
    f.start_redye('RACE');r=f.rsource('RACE');version=d.ver('rework_orders',r['order'])
    cp={'rework_order_id':r['order'],'qty_good':5,'qty_bs':2,'completed_at':'2026-09-18T08:00:00+07:00','return_fg_location_id':C['fg'],'change_reason':'Independent completion racing vendor invoice'}
    ip={'vendor_id':C['daily_vendor'],'invoice_number':'AUD-REV-COMPLETE-INVOICE','invoice_date':'2026-09-19','header_total':'1400.03','lines':[{'line_kind':'BILL','rework_service_id':r['service'],'category':'GOOD','qty':5,'amount':'1000.01'},{'line_kind':'BILL','rework_service_id':r['service'],'category':'BS','qty':2,'amount':'400.02'}]};comp_req,draft_req,post_req=uid(),uid(),uid()
    def complete(c):return public(c,'erp_save_bs_resolution_action_v1',['COMPLETE_REWORK',cp,comp_req,version])
    def invoice(c):
        draft=public(c,'erp_save_laundry_bd_action_v1',['SAVE_INVOICE_DRAFT',ip,draft_req]);post=public(c,'erp_save_laundry_bd_action_v1',['POST_INVOICE',{'invoice_id':draft['invoice_id'],'expected_version':str(draft['row_version'])},post_req]);return {'draft':draft,'posted':post}
    with s.actor_conn() as c:
        control_complete=complete(c);control_invoice=invoice(c);c.rollback()
    def actual_complete():
        with s.actor_conn() as c:return complete(c)
    def actual_invoice():
        with s.actor_conn('admin') as c:return invoice(c)
    # Active ADMIN must be capable of the exact invoice; verify it after a
    # rolled-back completion in the same connection before interpreting refusal.
    with s.actor_conn('admin') as c:
        admin_complete=complete(c);admin_invoice=invoice(c);c.rollback()
    out=compete([actual_complete,actual_invoice]);assert out[0]['accepted'],out
    if not out[1]['accepted']:assert out[1]['sqlstate']=='P0001' and 'PERMISSION' not in out[1]['error'],out
    # If invoice lost the race it is now a valid retry. If it won, both request
    # UUIDs replay; no duplicate invoice or cost is allowed in either outcome.
    final=actual_invoice();eq(f.poqty(r['po']),5);eq(f.pogl(r['po']),D('14289.74'))
    rows=A("select count(*),sum(qty),sum(net_amount),sum(released_estimate),sum(product_variance) from erp.bd_laundry_invoice_lines_v1 where invoice_id=%s",(final['posted']['invoice_id'],))[0];eq(rows,(2,7,D('1400.03'),D('1381.17'),D('18.86')))
    eq(A("select count(*) from erp.bd_laundry_invoices_v1 where invoice_number='AUD-REV-COMPLETE-INVOICE' and status='POSTED'",one=True),1)
    phy=f.physical_fingerprint();again=actual_invoice();eq(f.physical_fingerprint(),phy);eq(f.pogl(r['po']),D('14289.74'))
    return {'standalone_completion':control_complete,'standalone_invoice':control_invoice,'admin_positive':admin_invoice,'outcomes':out,'same_uuid_retry':final,'invoice_lines':rows,'final_po_cost':'14289.74','good':5,'bad_returned':2,'source_not_sent':2,'final_replay_unchanged':True}

def run():
    n.setup();f.new_products();f.redye_sources()
    n.case('REV.RACE.CONVERSION_SALE','Conversion8 and sale8 compete for the same13 PCS',conversion_sale)
    n.case('REV.RACE.COMPLETION_INVOICE','Celup completion and first vendor billing serialize or refuse then retry once',completion_invoice)
