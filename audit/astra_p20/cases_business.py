"""Astra independent numerical/business cases; all constants chosen before probe code.
Master/draft and transport helper origin: existing writer fixtures. New business input/oracle: Astra.
No stock/HPP/journal result is inserted by the auditor.
"""
import json,uuid
from datetime import timedelta
from decimal import Decimal as D,ROUND_HALF_UP
import cp7_f03_e01_cases as transport
import cp7_procurement_cases as procurement
import cp7_invoice_cases as invoices
import cp7_supplier_payment_create_cases as supplier_pay
import cp7_sales_draft_cases as drafts
import cp7_sales_return_cases as returns
import cp7_finance_cases as finance
import cp7_nota_cases as nota
import cp7_settlement_cases as settlement
import cp6_bd_probe as laundry
from cases_stage import wrap as common_wrap,check,admin,save,refusal,digest_rows
prod,base=transport.prod,transport.base
cmd=returns.cmd

def gl(cur):
    admin(cur)
    return {str(a):D(v) for a,v in cur.execute("select l.account_id,sum(l.debit-l.credit) from erp.journal_lines l join erp.journal_entries h on h.id=l.journal_entry_id where h.status in('POSTED','REVERSED') group by l.account_id").fetchall()}
def delta(a,z):return {k:z.get(k,D(0))-a.get(k,D(0)) for k in set(a)|set(z) if z.get(k,D(0))!=a.get(k,D(0))}
def account(cur,k):return str(cur.execute('select erp.account_id(%s)',(k,)).fetchone()[0])
def money(n):return D(n).quantize(D('.01'),rounding=ROUND_HALF_UP)
def native(cur,q,args=()):return transport.native(cur,q,args)
def fg_qty(cur,f):
    admin(cur);return D(cur.execute('select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id where l.po_id=%s',(f['po'],)).fetchone()[0])

def production(cur,today,laundry_amount=None,final=True):
    """New worksheet73x12.37, cut41, sew17+24x1.13, accessory .89, laundry2.07.
    Schema/master construction follows accepted entrypoint shapes; all business effects use commands.
    """
    f=procurement.fixture(cur,today,qty='73',price='12.37',final=final)
    d=procurement.command(cur,'SAVE_DRAFT',f['payload']);p=procurement.post(cur,d);f['purchase']=p['purchase_id']
    f['roll']=str(cur.execute('select r.id from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=%s',(f['purchase'],)).fetchone()[0])
    day=f['day']+timedelta(days=1);at=lambda hour,minute=0:prod.at(day,hour,minute)
    model,contractor,po,product=[str(uuid.uuid4()) for _ in range(4)];tag='AS20-'+uuid.uuid4().hex[:10]
    cur.execute('insert into erp.product_models(id,model_code,model_name)values(%s,%s,%s)',(model,tag,tag))
    cur.execute('insert into erp.product_model_sizes(model_id,size_id,sort_order)values(%s,%s,1)',(model,base.SIZE))
    cur.execute("insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,attendance_required)values(%s,%s,%s,'MANDOR',false)",(contractor,tag,tag))
    bom=cur.execute('insert into erp.work_bom_versions(model_id,version_no,effective_from,notes)values(%s,1,%s,%s)returning id',(model,at(0),'Astra synthetic work tariff1.13')).fetchone()[0]
    cur.execute('insert into erp.work_bom_items(bom_version_id,work_component_id,sequence_no,default_rate)values(%s,%s,1,1.13)',(bom,prod.COMPONENT))
    cur.execute('insert into erp.contractor_work_rates(contractor_id,model_id,work_component_id,rate_per_pcs,effective_from)values(%s,%s,%s,1.13,%s)',(contractor,model,prod.COMPONENT,at(0)))
    cur.execute("insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from,is_active,is_portal_visible)select %s,%s,%s,brand_id,'Astra Indigo',size_id,%s,%s,%s,true,true from erp.products where id=%s",(product,tag,model,tag,product,at(0),base.BASE_PRODUCT))
    pcs=cur.execute("select unit_code from erp.uom_definitions where upper(unit_code)='PCS' and dimension='COUNT' and is_active").fetchone()[0]
    cat=cur.execute('insert into erp.accessory_categories(category_code,category_name,base_uom_code,is_active)values(%s,%s,%s,true)returning id',(tag,'Astra button',pcs)).fetchone()[0]
    accessory=cur.execute('insert into erp.accessory_bom_versions(product_id,version_label,effective_from,notes)values(%s,%s,%s,%s)returning id',(product,tag,at(0),'Astra own .89 per GOOD')).fetchone()[0]
    cur.execute("insert into erp.accessory_bom_items(bom_version_id,category_id,qty_per_good_fg_base,hpp_method,hpp_standard_rate,hpp_uom_code,reimbursement_rate,reimbursement_uom_code)values(%s,%s,1,'BOM_STANDARD',.89,%s,.89,%s)",(accessory,cat,pcs,pcs))
    location=returns.location(cur,tag)
    cur.execute("insert into erp.production_orders(id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at,notes)values(%s,%s,%s,%s,41,'CUTTING','CUTTING',%s,%s)",(po,tag,model,contractor,at(7),'Astra own41PCS worksheet'))
    f.update(po=po,model=model,contractor=contractor,product=product,sku=tag,tag=tag,raw_location=f['location'],location=location,destination=location,production_day=day)
    cut_payload=dict(action='SAVE_DRAFT',po_id=po,pattern_id=prod.PATTERN,source_location_id=f['raw_location'],cut_at=at(8),change_reason='Astra41 of73',size_slots=[dict(slot_no=1,size_id=base.SIZE,drawing_no=1)],rolls=[dict(roll_id=f['roll'],qty_issued=41,qty_consumed=41,qty_reported_remaining=0,yields=[dict(slot_no=1,qty_pcs=41)])])
    cut=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',cut_payload)
    cut=prod.rpc(cur,'public.erp_save_cutting_group_before_sewing_v2',dict(cut_payload,id=cut['cutting_group_id'],action='POST'),expected_version=int(cut['row_version']));admin(cur);f['group']=cut['cutting_group_id']
    y=str(cur.execute('select y.id from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id where r.cutting_group_id=%s',(f['group'],)).fetchone()[0])
    pp=dict(action='SAVE_DRAFT',cutting_group_id=f['group'],contractor_id=contractor,picked_up_at=at(9),allocation_mode='ROLL',expected_group_version=int(cut['row_version']),change_reason='Astra exact pickup41',batches=[dict(batch_no=1,allocations=[dict(cutting_roll_yield_id=y,qty_pcs=41)])])
    pickup=prod.rpc(cur,'public.erp_save_cutting_pickup_v1',pp)
    pickup=prod.rpc(cur,'public.erp_save_cutting_pickup_v1',dict(pp,id=pickup['pickup_id'],action='POST'),expected_version=int(pickup['row_version']));admin(cur)
    f['batch']=str(cur.execute('select id from erp.cutting_distribution_batches where pickup_id=%s',(pickup['pickup_id'],)).fetchone()[0])
    native(cur,'select erp.ensure_po_work_component_snapshots_v2(%s,%s,%s)',(po,at(9,30),uuid.uuid4()))
    snap=cur.execute('select id from erp.po_work_component_snapshots where po_id=%s',(po,)).fetchone()[0]
    for qty,minute in ((17,0),(24,30)):
        completion=str(uuid.uuid4());laundry.chain.peer.ordinary(cur)
        cur.execute("insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by)values(%s,%s,%s,%s,%s,%s,'DRAFT',%s,%s)",(completion,'AS20W-'+completion,po,contractor,f['group'],at(10,minute),'Independent unequal sewing legs',base.OPERATOR_APP))
        cur.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot)values(%s,%s,%s,%s,%s,1.13)',(completion,snap,prod.COMPONENT,qty,qty))
        native(cur,'select erp.post_work_completion(%s)',(completion,))
        native(cur,'select public.erp_record_sewing_terminal_v1(%s::jsonb,%s)',(json.dumps(dict(work_completion_id=completion,qty_pcs=qty,reason='Astra own physical sewing leg')),uuid.uuid4()))
    vendor,process=str(uuid.uuid4()),str(uuid.uuid4())
    cur.execute('insert into erp.laundry_vendors(id,vendor_code,vendor_name)values(%s,%s,%s)',(vendor,tag,tag))
    cur.execute('insert into erp.wash_processes(id,process_code,process_name)values(%s,%s,%s)',(process,tag,'Astra wash'))
    wash=dict(vendor=vendor,process=process,day=day,start=at(0),batch=f['batch'],group=f['group']);laundry.process_rate(cur,wash,'2.07')
    delivery=laundry.post_priced(cur,wash,{},qty=41,hour=11);receipt=laundry.receive(cur,delivery['delivery_id'],wash,41,13);admin(cur)
    line=laundry.receipt_line(cur,receipt['receipt_id']);size=str(cur.execute('select id from erp.laundry_receipt_batch_size_lines where receipt_line_id=%s',(line,)).fetchone()[0])
    qc=laundry.chain.laundry_action(cur,'POST_FINAL_SKU',dict(cutting_group_id=f['group'],destination_location_id=location,physical_at=at(15).isoformat(),reason='Astra all41 exact source',good_qty_pcs=41,completion_mode='ALL_READY',lines=[dict(final_product_id=product,qty_good_pcs=41,qty_bs_pcs=0,source_laundry_receipt_line_id=line,source_laundry_receipt_batch_size_line_id=size)]),base.group_version(cur,f['group']));admin(cur)
    laundry.invoice_policies(cur,billable=('GOOD',),mode='PRODUCT_COST',after='CORRECTION_DOCUMENT')
    amount=laundry_amount or '84.87';inv,posted=laundry.invoice(cur,wash,[dict(line=line,qty=41,amount=amount)],amount)
    native(cur,'select erp.finish_production_order(%s)',(po,));native(cur,'select erp.process_cost_recalc_queue(100)')
    f.update(vendor=vendor,laundry_invoice=inv['invoice_id'],wash=wash,laundry_line=line,laundry_amount=amount)
    f['customer']=str(base.create_customer(cur,tag));f['sale_at']=(returns.source.fg.ax.r1.now(cur)-timedelta(minutes=5)).isoformat()
    f['bank']=str(returns.source.bc.bank_account(cur,tag+'B'));f['cash_coa']=returns.payments.bank_account(cur,f)
    return f

def assess(cur,f):
    admin(cur)
    raw=cur.execute('select sum(qty_signed),sum(qty_signed*unit_cost_snapshot) from erp.material_stock_movements where material_id=%s',(f['material'],)).fetchone()
    lots=cur.execute('select l.id::text,l.initial_qty_pcs,h.hpp_per_pcs,h.total_cost from erp.fg_lots l join erp.v_current_hpp h on h.lot_id=l.id where l.po_id=%s',(f['po'],)).fetchall()
    check(raw==(D(32),D('395.84')),'Raw physical/value conservation',observed=raw)
    expected_total=D(41)*(D('12.37')+D('1.13')+D('.89'))+D(f['laundry_amount'])
    check(sum(D(x[3]) for x in lots)==expected_total,'Independent landed production cost',expected=expected_total,lots=lots)
    check(sum(x[1] for x in lots)==41,'Exactly41 units finished',lots=lots)
    ap=cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s)',(f['purchase'],f['purchase'])).fetchone()
    check(ap==(D('903.01'),D(0)),'Exact supplier AP',observed=ap)
    check(D(laundry.ap(cur,f['vendor']))==D(f['laundry_amount']),'Vendor AP exact')
    check(D(laundry.wip(cur,f['po']))==0,'No WIP after all41 finished')
    return dict(raw=raw,lots=lots,AP=ap,production_cost=expected_total)

def cases(cur,today):
    def flow():
        admin(cur);transport.attendance.quiet_seed(cur,today-timedelta(days=4),today)
        g0=gl(cur);f=production(cur,today);physical=assess(cur,f)
        check(all(D(x[2])==D('16.46') for x in physical['lots']),'Landed HPP per PCS16.46')
        # Independent payroll oracle: 41x1.13 labor +41x.89 accessories, attendance0.
        cards=nota.read(cur,'SOURCES',contractor_id=f['contractor'])['page']['rows']
        check(sum(D(c['remaining_amount']) for c in cards)==D('46.33'),'Labor rights from actual unequal legs')
        note=nota.command(cur,'SAVE',dict(contractor_id=f['contractor'],note_date=str(today),period_start=str(f['production_day']),period_end=str(today),cards=[dict(card_key=c['card_key'],source_token=c['source_token']) for c in cards],notes='Astra independent payroll'))
        note=nota.act(cur,'POST',note);pid=note['payroll_id'];settlement.act(cur,'PREPARE',settlement.doc(cur,pid));reviewed=settlement.doc(cur,pid)
        check((D(reviewed['labor_total']),D(reviewed['attendance_total']),D(reviewed['net_payable']))==(D('46.33'),D(0),D('82.82')),'Attendance not wage; exact accessories once',payroll=reviewed)
        settlement.act(cur,'APPROVE',reviewed)
        g_pre_sale=gl(cur);original_payroll=digest_rows(cur,'erp','payroll_work_allocations') if cur.execute("select to_regclass('erp.payroll_work_allocations')").fetchone()[0] else None
        report0=finance.fixture_read(cur,today,f['sale_at'])
        created=drafts.create(cur,f,drafts.payload(f,'13','29.91'))
        check(fg_qty(cur,f)==28 and gl(cur)==g_pre_sale,'Draft reserves13 once with no journal')
        payload,version=cmd.review(cur,f);key=uuid.uuid4();posted=cmd.command(cur,'POST',payload,version,key)
        check(fg_qty(cur,f)==28,'Posting creates no second stock reservation')
        after_post=gl(cur);check(cmd.command(cur,'POST',payload,version,key)==posted and gl(cur)==after_post,'Replay has one effect')
        returns.payments.pay(cur,f,'137.03')
        f['allocations']=returns.read(cur,f)['page']['rows']
        p,v=returns.payload(cur,f,qty='4',refund='119.64');ret=cmd.command(cur,'RETURN',p,v)
        check(fg_qty(cur,f)==32,'Return4 restores original physical source')
        ar=D(returns.source.read(cur,f)['detail']['financial']['open_balance'])
        check(ar==D('132.16'),'AR =9x29.91 minus137.03',observed=ar)
        g_sales=delta(g_pre_sale,gl(cur));expected={account(cur,'AR_CUSTOMER'):D('132.16'),account(cur,'SALES_REVENUE'):D('-269.19'),account(cur,'FG_INVENTORY'):D('-148.14'),account(cur,'COGS'):D('148.14'),f['cash_coa']:D('137.03')}
        check(g_sales==expected,'Independent exact net-sale journal',observed=g_sales,expected=expected)
        r_after=finance.fixture_read(cur,today,f['sale_at'])
        perf0=report0['snapshot']['performance'];perf1=r_after['snapshot']['performance']
        for k,want in [('sales_revenue_gl',D('269.19')),('cogs_gl',D('148.14')),('gross_profit',D('121.05'))]:
            check(D(perf1[k])-D(perf0[k])==want,'Authoritative report exact '+k,observed=[perf0[k],perf1[k]],expected=want)
        check(sum(delta(g0,gl(cur)).values(),D(0))==0,'Whole lifecycle trial balance')
        per_entry=cur.execute("select j.id::text,sum(l.debit-l.credit) from erp.journal_entries j join erp.journal_lines l on l.journal_entry_id=j.id group by j.id having sum(l.debit-l.credit)<>0").fetchall()
        check(not per_entry,'Every journal independently balances',unbalanced=per_entry)
        return dict(inputs=dict(receipt_pcs=73,raw_price='12.37',cut=41,labor='1.13',accessory='.89',laundry='2.07',sale=13,price='29.91',paid='137.03',returned=4),final=dict(raw_pcs=32,raw_value='395.84',fg_pcs=32,fg_value='526.72',net_revenue='269.19',net_cogs='148.14',AR='132.16',labor='46.33',payroll='82.82'),actual_journal=g_sales,report=r_after['snapshot'],source=f,return_document=ret)

    def big():
        outputs=[]
        # Separate savepoints isolate each magnitude; none is rounded down to fit int32.
        for amount in ('21474836.47','21474836.48','22000000.01'):
            admin(cur);cur.execute('savepoint astra_big')
            try:
                f=production(cur,today,laundry_amount=amount);obs=assess(cur,f)
                outputs.append(dict(amount=amount,status='PASS',observed=obs))
            except Exception as e:
                outputs.append(dict(amount=amount,status='FAILED',error=str(e),sqlstate=getattr(e,'sqlstate',None)))
            finally:
                cur.execute('rollback to savepoint astra_big');admin(cur);cur.execute('release savepoint astra_big')
        save('AS20-07_amounts',outputs)
        check(all(x['status']=='PASS' for x in outputs),'Schema-valid amounts survive all intermediate arithmetic',cases=outputs)
        return outputs

    def precision():
        f=procurement.fixture(cur,today,qty='7.123457',price='8.654321',final=True)
        before=gl(cur);key=uuid.uuid4();d=procurement.command(cur,'SAVE_DRAFT',f['payload'],key)
        check(procurement.qty(cur,f)==(0,0),'Draft has no physical effect')
        check(procurement.command(cur,'SAVE_DRAFT',f['payload'],key)==d,'Same UUID/body one draft')
        bad=refusal(cur,lambda:procurement.command(cur,'SAVE_DRAFT',dict(f['payload'],notes='changed intent'),key))
        check(bad['refused'],'Changed payload UUID refused')
        postkey=uuid.uuid4();p=procurement.post(cur,d,postkey);posted_state=gl(cur)
        check(procurement.post(cur,d,postkey)==p and gl(cur)==posted_state,'One receipt post effect on replay')
        expected=(D('7.123457')*D('8.654321')).quantize(D('.000001'),rounding=ROUND_HALF_UP)
        line=procurement.workspace(cur,dict(purchase_id=p['purchase_id']))['detail']['items'][0]
        check(D(line['finance']['line_total'])==expected,'Six decimal line arithmetic independent',expected=expected,observed=line['finance'])
        ap=cur.execute('select erp.material_purchase_final_ap_total(%s)',(p['purchase_id'],)).fetchone()[0]
        # This helper is an exact operand; the contract rounds at payable/journal boundary.
        check(D(ap)==D('7.123457')*D('8.654321'),'Exact unrounded AP operand retained',observed=ap)
        bank=supplier_pay.bc.fixture(cur,today,zones=False,purchase=False)
        payment_f=dict(receipt=p,cash=bank['cash'])
        payable=supplier_pay.read(cur,payment_f)
        check(D(payable['Native_AP']['remaining'])==money(expected),'Public payable boundary rounds once to cents',observed=payable['Native_AP'])
        payment_payload=supplier_pay.payload(cur,payment_f,str(money(expected)))
        paid=supplier_pay.command(cur,payment_payload)
        after_pay=supplier_pay.read(cur,payment_f)
        check(D(after_pay['Native_AP']['remaining'])==0 and not after_pay['eligible'],'Exact public cents payment fully settles without fractional ghost debt',observed=after_pay['Native_AP'])
        check(procurement.qty(cur,f)==(D('7.123457'),1),'Exact quantity once')
        check(sum(delta(before,gl(cur)).values(),D(0))==0,'Precision journal balance')
        return dict(input=f['payload'],line=line,ap=ap,changed_uuid=bad)

    def receipt_access():
        f=procurement.fixture(cur,today,qty='19',price='3.17',final=True);actor,role=procurement.custom(cur,procurement.OPS+('finance.ap.view',))
        key=uuid.uuid4();d=procurement.command(cur,'SAVE_DRAFT',f['payload'],key,subject=actor);pkey=uuid.uuid4();p=procurement.post(cur,d,pkey,actor)
        before=gl(cur);stock=procurement.qty(cur,f)
        admin(cur);cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key='warehouse.procurement.post'",(role,))
        replay=refusal(cur,lambda:procurement.post(cur,d,pkey,actor))
        check(replay['refused'],'Revoked post permission checked before success replay',result=replay)
        check(gl(cur)==before and procurement.qty(cur,f)==stock,'Refused replay is effect-free')
        return dict(receipt=p,revoked_replay=replay,stock=stock)

    return [wrap('AS20-06_13_18_50_FULL_FLOW',flow),wrap('AS20-07_LARGE_INVOICE',big),wrap('AS20-04_08_PRECISION',precision),wrap('AS20-01_RECEIPT_REPLAY',receipt_access)]


def wrap(case, op):
    name, original = common_wrap(case, op)
    def run():
        result = original()
        result['fixture_origin'] = 'ASTRA_INPUTS_AND_MASTER_FIXTURE_WITH_WRITER_TRANSPORT_HELPERS'
        save(case, result)
        return result
    return name, run
