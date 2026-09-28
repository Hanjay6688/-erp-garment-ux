"""Writer CP6 continuation: real combined range/QC/rework/sale/invoice transactions.

Only disposable PostgreSQL fixtures. Unequal size quantities expose accidental
averaging; expected stock, source identity and money are checked independently.
"""
import copy
import json
import uuid
from datetime import timedelta
import cp6_bf_probe as bf

b, one = bf.b, bf.one
prod, base = b.chain.production, b.chain.base


def fixture(cur, today, recipe=False):
    now = one(cur, 'select clock_timestamp()')
    at = now - timedelta(minutes=4)
    when = lambda hour, minute=0: now - timedelta(seconds=(30-hour-minute/60)*6)
    rows = bf.products(cur, ('31', '32', '33', '34'))
    roots, sizes, qtys = [p for p,s in rows], [s for p,s in rows], [5,8,3,4]
    bom = []
    if recipe:
        unit = one(cur, "select unit_code from erp.uom_definitions where upper(unit_code)='PCS' and dimension='COUNT' and is_active")
        cat = one(cur, "insert into erp.accessory_categories(category_code,category_name,base_uom_code,is_active) values(%s,'Combined range buttons',%s,true) returning id::text", 'BFC-'+uuid.uuid4().hex[:8],unit)
        # This is the mandor-provided accessory route, so its reimbursement must
        # match the nonzero BOM cost. Zero reimbursement requires actual company
        # material issues and would refuse before the range oracle is reached.
        bom = [dict(category_id=cat,qty_per_good_fg_base='1',hpp_method='BOM_STANDARD',hpp_standard_rate='3.17',hpp_uom_code=unit,reimbursement_rate='3.17',reimbursement_uom_code=unit)]
    def settings(rate):
        return dict(price='185000.00',bom=copy.deepcopy(bom),work_rates=[dict(work_component_id=prod.COMPONENT,rate=rate)],laundry_rates=[])
    a = bf.group(cur,roots[:3],at,settings=settings('10.00'))
    z = bf.group(cur,roots[3:],at,settings=settings('30.00'))
    saved = bf.save(cur,[a,z],at)
    versions = {x['sku_id'] if 'sku_id' in x else x['id']:x['version_id'] for x in saved['groups']}
    snapshots = {}
    def work(cur,po,wave,batch,yields,clock):
        bf.call(cur,'BIND_WAVE',dict(cutting_group_id=wave,expected_version=one(cur,'select erp.bf_wave_revision_v1(%s)',wave),references=[dict(size_id=s,sku_id=a['id'] if i<3 else z['id']) for i,s in enumerate(sizes)]))
        cur.execute('insert into erp.po_work_component_snapshots(po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at) values(%s,%s,1,3,%s)',(po,prod.COMPONENT,clock(9,30)))
        prod.owner(cur)
        cur.execute('select erp.ensure_po_work_component_snapshots_v2(%s,%s,%s)',(po,clock(10),uuid.uuid4()))
        b.api.admin(cur)
        for group,qty in ((a,16),(z,4)):
            snap = one(cur,'select s.id::text from erp.po_work_component_snapshots s join erp.bf_sku_versions_v1 v on v.id=s.bf_sku_version_id where s.po_id=%s and v.sku_id=%s and s.work_component_id=%s',po,group['id'],prod.COMPONENT)
            snapshots[group['id']] = snap
            event = str(uuid.uuid4())
            b.chain.peer.ordinary(cur)
            cur.execute("insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by) values(%s,%s,%s,%s,%s,%s,'DRAFT','Combined range actual sewing',%s)",(event,'BFC-'+event,po,prod.CONTRACTOR,wave,clock(10),base.OPERATOR_APP))
            cur.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot) values(%s,%s,%s,%s,%s,0)',(event,snap,prod.COMPONENT,qty,qty))
            cur.execute('select erp.post_work_completion(%s)',(event,))
            prod.owner(cur)
            cur.execute('select public.erp_record_sewing_terminal_v1(%s::jsonb,%s)',(json.dumps(dict(work_completion_id=event,qty_pcs=qty,reason='Combined range physical sewing')),uuid.uuid4()))
            b.api.admin(cur)
    fx = b.two_size_fixture(cur,b.case_day(today),'COMBINED',size_quantities=list(zip(sizes,qtys)),clock=when,work_setup=work)
    fx.update(now=now,when=when,rows=rows,roots=roots,size_ids=sizes,qtys=qtys,a=a,z=z,versions=versions,snapshots=snapshots)
    fx['day'] = one(cur,'select erp.bb_business_today_v1()')
    b.process_rate(cur,fx,'7.00')
    b.invoice_policies(cur,after='CORRECTION_DOCUMENT')
    return fx


def wash(cur,f,indexes,hour,pending=False,pricing=None):
    payload = dict(distribution_batch_id=f['batch'],vendor_id=f['vendor'],wash_process_id=f['process'],target_dyeing_color='COMBINED-BLUE',physical_at=f['when'](hour).isoformat(),reason='Combined range exact service recipients',lines=[dict(size_id=f['size_ids'][i],qty_sent_pcs=f['qtys'][i]) for i in indexes])
    sent = b.bd(cur,'POST_PRICED_DELIVERY',dict(delivery=payload,expected_version=str(base.group_version(cur,f['group'])),pricing=pricing if pricing is not None else {'deferred':True} if pending else {}))
    ds = dict(cur.execute('select s.size_id::text,s.id::text from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where l.delivery_id=%s',(sent['delivery_id'],)).fetchall())
    rec = b.chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=sent['delivery_id'],wash_process_id=f['process'],physical_at=f['when'](hour+1).isoformat(),reason='Combined range exact-size receipts',lines=[dict(delivery_batch_size_line_id=ds[f['size_ids'][i]],qty_good_received=f['qtys'][i],qty_bs_laundry=0,bs_product_id=None) for i in indexes]),base.delivery_version(cur,sent['delivery_id']))
    line = b.receipt_line(cur,rec['receipt_id'])
    rs = dict(cur.execute('select d.size_id::text,r.id::text from erp.laundry_receipt_batch_size_lines r join erp.laundry_delivery_batch_size_lines d on d.id=r.delivery_batch_size_line_id where r.receipt_line_id=%s',(line,)).fetchall())
    return dict(sent=sent,line=line,rs=rs)


def finish(cur,f,washes,indexes,hour,bs=None,partial=False,quantities=None,location=None):
    bs = bs or {}
    lines=[]
    for i in indexes:
        source=next(w for w in washes if f['size_ids'][i] in w['rs'])
        lines.append(dict(final_product_id=f['roots'][i],qty_good_pcs=(quantities or {}).get(i,f['qtys'][i])-bs.get(i,0),qty_bs_pcs=bs.get(i,0),source_laundry_receipt_line_id=source['line'],source_laundry_receipt_batch_size_line_id=source['rs'][f['size_ids'][i]]))
    return b.chain.laundry_action(cur,'POST_FINAL_SKU',dict(cutting_group_id=f['group'],destination_location_id=location or base.LOCATION,physical_at=f['when'](hour).isoformat(),reason='Combined range QC with exact physical sources',good_qty_pcs=sum(x['qty_good_pcs'] for x in lines),completion_mode='PARTIAL_SELECTION' if partial else 'ALL_READY',lines=lines),base.group_version(cur,f['group']))


def move34(cur,f,hour,changed_recipe=False):
    at=f['when'](hour)
    settings=copy.deepcopy(f['a']['settings'])
    if changed_recipe:settings['bom'][0]['qty_per_good_fg_base']='2'
    settings['work_rates'][0]['rate']='90.00'
    a=bf.group(cur,f['roots'],at,sku=f['a']['sku'],gid=f['a']['id'],revision=1,settings=settings)
    z=bf.group(cur,f['roots'][3:],at,sku=f['z']['sku'],gid=f['z']['id'],revision=1,settings=copy.deepcopy(f['z']['settings']))
    z.update(members=[],legacy_basis=[])
    z['settings']['work_rates'][0]['rate']='45.00'
    return bf.save(cur,[a,z],at)


def lots(cur,f):
    return [one(cur,"select (select id::text from erp.fg_lots where po_id=%s and product_id=%s and lot_origin='PRODUCTION')",f['po'],p) for p in f['roots']]


def stock(cur,lot):
    return one(cur,'select coalesce(sum(qty_signed),0) from erp.fg_stock_movements where lot_id=%s',lot)


def books(cur):
    return {k:b.gl(cur,k) for k in ('FG_INVENTORY','COGS','WIP')}


def report(cur,query,at=None,**filters):
    prod.owner(cur)
    result=cur.execute('select public.erp_get_sku_hpp_v1(%s::jsonb)',(json.dumps(dict(query=query,**({'at':at.isoformat()} if at else {}),**filters)),)).fetchone()[0]
    b.api.admin(cur)
    return result


def sale(cur,f,index,qty,hour):
    customer=base.create_customer(cur,'BFC-'+uuid.uuid4().hex[:8])
    prod.owner(cur)
    draft=cur.execute('select erp.save_sale_draft_v2(%s::jsonb,%s::uuid,null)',(json.dumps(dict(sale_number='BFC-'+uuid.uuid4().hex[:12],customer_id=customer,source_location_id=base.LOCATION,sale_date=f['when'](hour).isoformat(),reason='Combined range sale before membership move',items=[dict(product_id=f['roots'][index],qty_pcs=qty,unit_price_snapshot='185000',discount_amount=0)])),uuid.uuid4())).fetchone()[0]
    b.api.admin(cur)
    version=one(cur,'select row_version from erp.sales_headers where id=%s',draft['sale_id'])
    prod.owner(cur)
    cur.execute('select erp.post_sale_v2(%s,%s,%s)',(draft['sale_id'],uuid.uuid4(),version))
    b.api.admin(cur)
    return draft['sale_id']


def return_one(cur,f,sale_id,hour):
    ret=str(uuid.uuid4())
    prod.owner(cur)
    cur.execute("insert into erp.sales_returns(id,return_number,sale_id,customer_id,physical_at,created_by) select %s,%s,id,customer_id,%s,erp.current_app_user_id() from erp.sales_headers where id=%s",(ret,'BFC-RET-'+ret,f['when'](hour),sale_id))
    cur.execute("insert into erp.sales_return_items(return_id,sale_stock_allocation_id,product_id,lot_id,location_id,qty_pcs,refund_amount) select %s,a.id,l.product_id,l.id,a.location_id,1,185000 from erp.sale_stock_allocations a join erp.fg_lots l on l.id=a.lot_id where a.sale_item_id in(select id from erp.sales_items where sale_id=%s)",(ret,sale_id))
    cur.execute('select erp.post_sales_return(%s)',(ret,))
    b.api.admin(cur)
    return ret


def late_invoice_return(cur,today,pending=False):
    f=fixture(cur,today)
    if pending:b.policy(cur,'LAU_DEC04',dict(sale_with_unknown_laundry='ALLOW_PENDING'))
    regular=wash(cur,f,[0,1,2],11)
    target=wash(cur,f,[3],13,pending)
    finish(cur,f,[regular,target],range(4),15)
    ls=lots(cur,f)
    old=[b.lot_value(cur,l) for l in ls]
    sid=sale(cur,f,3,4,16)
    allocated=cur.execute('select to_jsonb(a) from erp.sale_stock_allocations a where sale_item_id in(select id from erp.sales_items where sale_id=%s)',(sid,)).fetchall()
    old_report=report(cur,f['z']['sku'],f['when'](15,30))
    move34(cur,f,17)
    before=books(cur);truth=b.all_truth(cur)
    amount='160.00' if pending else '188.00'
    _,invoice=b.invoice(cur,f,[dict(line=target['line'],qty=4,amount=amount)],amount)
    after=books(cur);priced=[b.lot_value(cur,l) for l in ls]
    ret=return_one(cur,f,sid,19)
    returned=books(cur)
    current=report(cur,f['a']['sku'])
    return_source=cur.execute('select product_id::text,lot_id::text,qty_pcs from erp.sales_return_items where return_id=%s',(ret,)).fetchone()
    checks=dict(invoice_only_target=priced[:3]==old[:3] and priced[3]-old[3]==160,
        sold_variance=after['COGS']-before['COGS']==160 and after['FG_INVENTORY']==before['FG_INVENTORY'] and after['WIP']==before['WIP'],
        same_original_lot=return_source==(f['roots'][3],ls[3],1),stock_exact=[stock(cur,l) for l in ls]==[5,8,3,1],
        return_cost=returned['FG_INVENTORY']-after['FG_INVENTORY']==priced[3]/4 and returned['COGS']-after['COGS']==-priced[3]/4,
        immutable_sale=allocated==cur.execute('select to_jsonb(a) from erp.sale_stock_allocations a where sale_item_id in(select id from erp.sales_items where sale_id=%s)',(sid,)).fetchall(),
        historical_membership=len(old_report['groups'])==1 and old_report['groups'][0]['qty']=='4',
        current_one_group=len(current['groups'])==1 and current['groups'][0]['qty']=='17' and len(current['groups'][0]['lots'])==4,
        current_value=b.D(current['groups'][0]['value'])==sum(priced[:3])+priced[3]/4,
        invoice_clears=not one(cur,'select erp.bd_lot_laundry_unknown_v1(%s)',ls[3]),truth=b.truth_quiet(truth,b.all_truth(cur)))
    b.bd(cur,'REVERSE_INVOICE',dict(invoice_id=invoice['invoice_id'],expected_version=invoice['row_version'],reason='Combined range inverse after original-lot return'))
    inverse=books(cur)
    checks.update(inverse_exact=[b.lot_value(cur,l) for l in ls]==old,
        inverse_distribution=inverse['FG_INVENTORY']-returned['FG_INVENTORY']==-40 and inverse['COGS']-returned['COGS']==-120,
        unknown_restored=one(cur,'select erp.bd_lot_laundry_unknown_v1(%s)',ls[3])==pending,
        stock_after_inverse=[stock(cur,l) for l in ls]==[5,8,3,1])
    return b.verdict(checks,lot_values_before=list(map(str,old)),lot_values_after=list(map(str,priced)),invoice=amount,variance='160.00',pending=pending)


def new_member_running_po(cur,today,mismatch=False):
    f=fixture(cur,today,True)
    w=wash(cur,f,range(4),11)
    finish(cur,f,[w],range(3),13,partial=True)
    original=lots(cur,f)[:3]
    old=[b.lot_value(cur,l) for l in original]
    move34(cur,f,14,changed_recipe=mismatch)
    before=b.all_truth(cur)
    if mismatch:
        refused=b.refused(cur,lambda:finish(cur,f,[w],[3],15),'BF_PO_NEW_MEMBER')
        return b.verdict(dict(refused=refused['ok'],old_lots_unchanged=[b.lot_value(cur,l) for l in original]==old,
            no_new_lot=lots(cur,f)[3] is None,physical_unchanged=[stock(cur,l) for l in original]==[5,8,3],truth=b.truth_quiet(before,b.all_truth(cur))),refusal=refused)
    finish(cur,f,[w],[3],15)
    ls=lots(cur,f)
    recipe=one(cur,'select erp.bf_recipe_basis_v1(bom_version_id) from erp.po_accessory_bom_commitments where po_id=%s and product_id=%s',f['po'],f['roots'][3])
    return b.verdict(dict(all_sizes=[stock(cur,l) for l in ls]==[5,8,3,4],old_lots_unchanged=[b.lot_value(cur,l) for l in original]==old,
        original_pin=one(cur,'select version_id::text from erp.bf_po_boms_v1 where po_id=%s and sku_id=%s',f['po'],f['a']['id'])==f['versions'][f['a']['id']],
        exact_recipe=recipe[0]['qty']==1 and b.D(str(recipe[0]['standard']))==b.D('3.17'),
        work_still_original=one(cur,"select erp.cp6_lot_work_cost_v2620c(%s,'LABOR')",ls[3])==120,
        positive_hpp=b.lot_value(cur,ls[3])>0,truth=b.truth_quiet(before,b.all_truth(cur))),values=list(map(str,[b.lot_value(cur,l) for l in ls])))


def range_rework(cur,today,committed=True,different=False):
    f=fixture(cur,today,True)
    w=wash(cur,f,range(4),11)
    count=2 if committed else 4
    finish(cur,f,[w],range(4),13,bs={3:count})
    bs=one(cur,"select id::text from erp.bs_cases where po_id=%s and product_id=%s and status='OPEN'",f['po'],f['roots'][3])
    old_bom=one(cur,'select (select bom_version_id::text from erp.po_accessory_bom_commitments where po_id=%s and product_id=%s)',f['po'],f['roots'][3])
    b.chain.bs_action(cur,'CLASSIFY_BS',dict(bs_case_id=bs,cause_source='UNKNOWN',components=[dict(work_component_id=prod.COMPONENT,completed_before_bs_qty=count)],change_reason='Original work earned before range move'),b.chain.version(cur,'bs_cases',bs))
    move34(cur,f,14,changed_recipe=committed)
    contractor=prod.CONTRACTOR
    if different:
        contractor=one(cur,"insert into erp.contractors(contractor_code,contractor_name,contractor_type,attendance_required,is_active) values(%s,'Combined alternate mandor','MANDOR',false,true) returning id::text",'BFC-'+uuid.uuid4().hex[:8])
    component=one(cur,'select id::text from erp.bs_case_components where bs_case_id=%s and work_component_id=%s',bs,prod.COMPONENT)
    bom=one(cur,'select erp.resolve_rework_accessory_bom_v1(%s,%s)::text',bs,f['when'](15))
    payload=dict(rework_number='BFC-RW-'+uuid.uuid4().hex[:10],bs_case_id=bs,destination_type='CONTRACTOR',contractor_id=contractor,vendor_id=None,qty_sent=count,physical_sent_at=f['when'](15).isoformat(),status='IN_PROGRESS',return_fg_location_id=base.LOCATION,accessory_bom_version_id=bom,accessory_bom_item_ids=[],change_reason='Rework after range move preserves physical provenance',components=[dict(bs_case_component_id=component,qty_performed=count)])
    made=b.chain.bs_action(cur,'SAVE_REWORK',payload)
    rid=made['result']['rework_order_id']
    b.api.admin(cur)
    line=cur.execute('select rate_snapshot,rate_basis,source_po_component_snapshot_id::text,bf_sku_version_id::text from erp.rework_component_lines where rework_order_id=%s',(rid,)).fetchone()
    truth=b.all_truth(cur)
    completed=b.chain.bs_action(cur,'COMPLETE_REWORK',dict(rework_order_id=rid,qty_good=count,qty_bs=0,completed_at=f['when'](16).isoformat(),return_fg_location_id=base.LOCATION,change_reason='All actual rework pieces returned'),b.chain.version(cur,'rework_orders',rid))
    lot=completed['result']['good_fg_lot_id']
    value=b.lot_value(cur,lot)
    result=b.verdict(dict(recipe_origin=(bom==old_bom if committed else old_bom is None),
        correct_work_rate=line[0]==(45 if different else 30),correct_work_source=line[1]==('SKU_RATE' if different else 'PO_SNAPSHOT'),
        original_snapshot=different or line[2]==f['snapshots'][f['z']['id']],
        physical_identity=one(cur,'select product_id::text from erp.fg_lots where id=%s',lot)==f['roots'][3],
        recovered=count==stock(cur,lot),positive_hpp=value>0,truth=b.truth_quiet(truth,b.all_truth(cur))),committed=committed,different_contractor=different,rate=str(line[0]),basis=line[1],hpp=str(value))
    b.chain.bs_action(cur,'REVERSE_REWORK_COMPLETION',dict(rework_order_id=rid,change_reason='Combined range recovery inverse'),b.chain.version(cur,'rework_orders',rid))
    result['checks']['inverse_stock']=stock(cur,lot)==0
    result['failed']=[key for key,ok in result['checks'].items() if not ok]
    result['status']='FAIL' if result['failed'] else 'PASS'
    return result


def unknown_bs_scope(cur,today):
    f=fixture(cur,today)
    payload=dict(distribution_batch_id=f['batch'],vendor_id=f['vendor'],wash_process_id=f['process'],target_dyeing_color='BS-SCOPE',physical_at=f['when'](11).isoformat(),reason='BS before final product identity',lines=[dict(size_id=s,qty_sent_pcs=q) for s,q in zip(f['size_ids'],f['qtys'])])
    sent=b.bd(cur,'POST_PRICED_DELIVERY',dict(delivery=payload,expected_version=str(base.group_version(cur,f['group'])),pricing={}))
    ds=dict(cur.execute('select s.size_id::text,s.id::text from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where l.delivery_id=%s',(sent['delivery_id'],)).fetchall())
    receipt=dict(delivery_id=sent['delivery_id'],wash_process_id=f['process'],physical_at=f['when'](12).isoformat(),reason='Two BS pieces with physical source not identified',lines=[dict(delivery_batch_size_line_id=ds[s],qty_good_received=q-(2 if i==1 else 0),qty_bs_laundry=2 if i==1 else 0,bs_product_id=None) for i,(s,q) in enumerate(zip(f['size_ids'],f['qtys']))])
    before=books(cur)
    refused=b.refused(cur,lambda:b.chain.laundry_action(cur,'POST_RECEIPT',receipt,base.delivery_version(cur,sent['delivery_id'])),'bind every Laundry BS to a product')
    b.api.admin(cur)
    checks=dict(unidentified_receipt_refused=refused['ok'],no_partial_receipt=one(cur,'select count(*) from erp.laundry_receipts where delivery_id=%s',sent['delivery_id'])==0,
        no_guessed_entitlement=one(cur,'select count(*) from erp.bs_cases where po_id=%s',f['po'])==0,money_unchanged=books(cur)==before)
    receipt['lines'][1]['bs_product_id']=f['roots'][1]
    b.chain.laundry_action(cur,'POST_RECEIPT',receipt,base.delivery_version(cur,sent['delivery_id']))
    bs=one(cur,"select id::text from erp.bs_cases where po_id=%s and status='OPEN'",f['po'])
    b.chain.bs_action(cur,'CLASSIFY_BS',dict(bs_case_id=bs,cause_source='UNKNOWN',components=[dict(work_component_id=prod.COMPONENT,completed_before_bs_qty=2)],change_reason='Physical size32 identified explicitly'),b.chain.version(cur,'bs_cases',bs))
    checks['identified_scope']=one(cur,'select po_component_snapshot_id::text from erp.bs_case_components where bs_case_id=%s',bs)==f['snapshots'][f['a']['id']]
    checks['no_fg']=one(cur,'select count(*) from erp.fg_lots where po_id=%s',f['po'])==0
    return b.verdict(checks,refusal=refused)


def commercial_selectors(cur,today):
    f=fixture(cur,today)
    w=wash(cur,f,range(4),11);finish(cur,f,[w],range(4),13)
    ls=lots(cur,f);physical=one(cur,'select sku from erp.products where id=%s',f['roots'][1])
    target=b.sized_product(cur,f['size_ids'][1],'BFC-DEST-'+uuid.uuid4().hex[:8])
    target_group=bf.group(cur,[target],f['when'](14));bf.save(cur,[target_group],f['when'](14))
    def workspace(**filters):
        prod.owner(cur)
        r=cur.execute('select public.erp_get_product_conversion_workspace_v1(%s::jsonb)',(json.dumps(filters),)).fetchone()[0]
        b.api.admin(cur);return r
    selected=workspace(query=f['a']['sku'],source_lot_id=ls[1],target_query=target_group['sku'])
    legacy=workspace(query=physical,source_lot_id=ls[1])
    before=[stock(cur,l) for l in ls]
    out=bf.be.be(cur,'POST',dict(source_lot_id=ls[1],target_product_id=target,location_id=base.LOCATION,qty_pcs=1,physical_at=f['when'](15).isoformat(),reason='Commercial code selects exact physical size32',expected_version=one(cur,'select erp.be_source_revision_v1(%s,%s)',ls[1],base.LOCATION)))
    dest=out['destination_lot_id'];doc=next(d for d in workspace()['documents'] if d['id']==out['conversion_id'])
    after=[stock(cur,l) for l in ls]
    checks=dict(commercial_source=len(selected['lots'])==1 and selected['lots'][0]['product_id']==f['roots'][1] and selected['lots'][0]['sku']==f['a']['sku'],
        commercial_target=len(selected['targets'])==1 and selected['targets'][0]['id']==target,
        legacy_search=len(legacy['lots'])==1 and legacy['lots'][0]['id']==ls[1],
        exact_size=after==[before[0],before[1]-1,before[2],before[3]] and stock(cur,dest)==1,
        document_labels=doc['source_sku']==f['a']['sku'] and doc['target_sku']==target_group['sku'],
        immutable_physical_code=one(cur,'select sku from erp.products where id=%s',f['roots'][1])==physical)
    bf.be.be(cur,'REVERSE',dict(conversion_id=out['conversion_id'],reason='Commercial selector exact inverse'))
    checks['inverse']=stock(cur,dest)==0 and [stock(cur,l) for l in ls]==before
    return b.verdict(checks)


def historical_import_identity(cur,today):
    """Resolver fixture at exact cutover instants; full import posting/replay is
    covered separately by BF:IMPORT_EXACT_SIZE_SALES_CUSTODY_COGS_REPLAY.
    Batch timestamps below are explicit prerequisites, not an owner mutation.
    """
    f=fixture(cur,today)
    received=wash(cur,f,range(4),10.25)
    finish(cur,f,[received],range(4),11.5)
    batch=b.api.call(cur,'CREATE',dict(batch_code='BFC-IMPORT-'+uuid.uuid4().hex[:8],cutover_date=str(today)))['batch_id']
    b.api.admin(cur)
    cur.execute('update erp.migration_batches set cutover_at=%s where id=%s',(f['when'](11),batch))
    size=one(cur,'select size_code from erp.sizes where id=%s',f['size_ids'][3])
    def resolve(**values):return one(cur,'select erp.bf_resolve_import_product_v1(%s,%s::jsonb,false)::text',batch,json.dumps(values))
    old=resolve(product_sku=f['z']['sku'],size_code=size)
    move34(cur,f,12)
    historical=resolve(product_sku=f['z']['sku'],size_code=size)
    future=b.refused(cur,lambda:resolve(product_sku=f['a']['sku'],size_code=size),'BF_IMPORT_PRODUCT_NOT_FOUND')
    cur.execute('update erp.migration_batches set cutover_at=%s where id=%s',(f['when'](13),batch))
    current=resolve(product_sku=f['a']['sku'],size_code=size)
    aggregate=b.refused(cur,lambda:resolve(product_sku=f['a']['sku']),'SIZE_ALLOCATION_REQUIRED')
    # A valid public physical successor creates a second historical identity of
    # the same root/size. It must remain ambiguous until product_id is supplied.
    physical=cur.execute('select id,sku,model_id,brand_id,color_name,size_id from erp.products where id=%s',(f['roots'][3],)).fetchone()
    prod.owner(cur)
    successor=cur.execute('select erp.edit_product_identity_effective(%s,%s,%s,%s,%s,%s,%s,%s,%s)',
        (physical[0],physical[1]+'-V2',*physical[2:],'Combined successor with the same construction',f['when'](14),'New physical code; commercial range and historical root stay traceable')).fetchone()[0]
    b.api.admin(cur)
    current_id=one(cur,'select id::text from erp.products where supersedes_product_id=%s',f['roots'][3])
    cur.execute('update erp.migration_batches set cutover_at=%s where id=%s',(f['when'](15),batch))
    ambiguous=b.refused(cur,lambda:resolve(product_sku=f['a']['sku'],size_code=size),'SIZE_ALLOCATION_REQUIRED')
    exact=resolve(product_sku=f['a']['sku'],product_id=f['roots'][3],size_code=size)
    newest=resolve(product_sku=f['a']['sku'],product_id=current_id,size_code=size)
    return b.verdict(dict(old_exact=old==f['roots'][3],historical_membership=historical==old,future_membership_refused=future['ok'],
        current_alias=current==old,no_aggregate_split=aggregate['ok'],two_versions_ambiguous=ambiguous['ok'],
        explicit_old=exact==old,explicit_new=newest==current_id,distinct_versions=old!=current_id),successor=successor)


def hpp_locations_pending(cur,today):
    f=fixture(cur,today)
    w=wash(cur,f,range(4),11,True)
    location=one(cur,"insert into erp.locations(location_code,location_name,location_type,is_active) values(%s,'Combined second FG warehouse','FG_WAREHOUSE',true) returning id::text",'BFC-'+uuid.uuid4().hex[:8])
    finish(cur,f,[w],[0],13,partial=True,quantities={0:2})
    finish(cur,f,[w],[0,1,2],14,partial=True,quantities={0:3},location=location)
    move34(cur,f,15)
    before=report(cur,f['a']['sku']);left=report(cur,f['a']['sku'],location_id=base.LOCATION);right=report(cur,f['a']['sku'],location_id=location)
    old=report(cur,f['a']['sku'],f['when'](12));grade=report(cur,f['a']['sku'],grade='GRADE_B')
    _,invoice=b.invoice(cur,f,[dict(line=w['line'],qty=20,amount='123.20')],'123.20')
    after=report(cur,f['a']['sku']);a=after['groups'][0];v=before['groups'][0]
    checks=dict(physical_denominator=v['qty']=='16' and len(v['lots'])==4,
        zero_stock_member=all(x['product_id']!=f['roots'][3] for x in v['lots']),
        locations=left['groups'][0]['qty']=='2' and right['groups'][0]['qty']=='14',
        value_conserved=b.D(v['value'])==b.D(left['groups'][0]['value'])+b.D(right['groups'][0]['value']),
        unknown_visible=v['provisional'] is True,known_cost_positive=b.D(v['value'])>0,
        report_before_receipt_empty=old['groups']==[],grade_filter_no_fictitious_stock=grade['groups']==[],
        invoice_exact_fg_share=b.D(a['value'])-b.D(v['value'])==b.D('98.56'),
        weighted=b.D(a['hpp_per_pcs'])==b.D(a['value'])/16)
    b.bd(cur,'REVERSE_INVOICE',dict(invoice_id=invoice['invoice_id'],expected_version=invoice['row_version'],reason='Combined location report inverse'))
    inverse=report(cur,f['a']['sku'])['groups'][0]
    checks['inverse']=inverse['value']==v['value'] and inverse['qty']=='16' and inverse['provisional'] is True
    return b.verdict(checks,before=v['value'],after=a['value'],locations=[left['groups'][0]['qty'],right['groups'][0]['qty']])


def same_size_two_skus(cur,today):
    first,size=bf.products(cur,('32',))[0]
    second=b.sized_product(cur,size,'BFC-SECOND-'+uuid.uuid4().hex[:8])
    at=one(cur,"select clock_timestamp()-interval '4 minutes'")
    a=bf.group(cur,[first],at);z=bf.group(cur,[second],at);bf.save(cur,[a,z],at)
    checks={};waves=[]
    def setup(group,overlap=False):
        def bind(cur,po,wave,batch,yields,when):
            waves.append(wave)
            def request(refs):return bf.call(cur,'BIND_WAVE',dict(cutting_group_id=wave,
                expected_version=one(cur,'select erp.bf_wave_revision_v1(%s)',wave),references=refs))
            request([dict(size_id=size,sku_id=group['id'])])
            if overlap:
                result=b.refused(cur,lambda:request([dict(size_id=size,sku_id=a['id']),dict(size_id=size,sku_id=z['id'])]),'BF_DUPLICATE_SIZE')
                checks['ambiguous_same_wave_refused']=result['ok']
                checks['original_binding_unchanged']=one(cur,'select sku_id::text from erp.bf_wave_skus_v1 where cutting_group_id=%s',wave)==a['id']
        return bind
    for group,qty in ((a,4),(z,7)):
        b.two_size_fixture(cur,b.case_day(today),'SAME-SIZE',size_quantities=[(size,qty)],
            clock=lambda h,m=0:at+timedelta(seconds=h*4+m/15),work_setup=setup(group,group is a))
    checks['separate_waves_supported']=len(set(waves))==2 and set(one(cur,'select sku_id::text from erp.bf_wave_skus_v1 where cutting_group_id=%s',w) for w in waves)=={a['id'],z['id']}
    return b.verdict(checks,supported_boundary='Same-size distinct work references use distinct physical waves')


def partial_attempts_credit(cur,today):
    """Two paid retries of size32 at the vendor, then 18 GOOD/1 BS/1 missing.
    Package/extra shares, source invoice corrections and claim allocation all
    traverse the ordinary posting routes; no monetary SKU override is used.
    """
    f=fixture(cur,today)
    garment=b.component(cur,f,'GARMENT','5.00');spray=b.component(cur,f,'SPRAY','1.00')
    extra=b.component(cur,f,'WHISKER','0.19')
    package=b.bd(cur,'SAVE_PACKAGE',dict(vendor_id=f['vendor'],package_code='BFC-PACK',package_name='Garment spray',component_ids=[garment,spray],is_active=True,reason='Combined real package'))['package_id']
    b.bd(cur,'SAVE_PACKAGE_RATE',dict(package_id=package,rate_per_pcs='6.17',effective_from=f['start'].isoformat(),reason='Combined vendor package'))
    b.terms(cur,f,'PACKAGE');b.policy(cur,'LAU_DEC03',dict(discount='REFUSED',extra='ALLOWED',rounding='REFUSED'))
    payload=dict(distribution_batch_id=f['batch'],vendor_id=f['vendor'],wash_process_id=f['process'],target_dyeing_color='BFC-ATTEMPTS',physical_at=f['when'](11).isoformat(),reason='Combined package and selected recipients',lines=[dict(size_id=s,qty_sent_pcs=q) for s,q in zip(f['size_ids'],f['qtys'])])
    pricing=dict(package_id=package,extras=[dict(component_id=extra,covered_qty=2,coverage=[dict(size_id=f['size_ids'][1],qty=2)],reason='Whisker only two size32 pieces')])
    def send(p):return b.bd(cur,'POST_PRICED_DELIVERY',dict(delivery=payload,expected_version=str(base.group_version(cur,f['group'])),pricing=p))
    duplicate=b.refused(cur,lambda:send(dict(package_id=package,extras=[dict(component_id=garment,covered_qty=20,reason='Already included')])), 'BD_COMPONENT_ALREADY_INCLUDED')
    sent=send(pricing);delivery=sent['delivery_id'];state=b.line_state(cur,delivery)
    ds=dict(cur.execute('select s.size_id::text,s.id::text from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where l.delivery_id=%s',(delivery,)).fetchall())
    attempts=[]
    for hour in (12,13):
        r=b.chain.laundry_action(cur,'POST_FAILED_WASH',dict(delivery_id=delivery,wash_process_id=f['process'],custody_outcome='RETRY_AT_VENDOR',physical_at=f['when'](hour).isoformat(),reason='Real paid retry only two size32 pieces',lines=[dict(delivery_batch_size_line_id=ds[f['size_ids'][1]],qty_attempted_pcs=2)]),base.delivery_version(cur,delivery))
        attempts.append(b.receipt_line(cur,r['receipt_id']))
    rec=b.chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=delivery,wash_process_id=f['process'],physical_at=f['when'](14).isoformat(),reason='18 good, one BS and one remains missing',lines=[dict(delivery_batch_size_line_id=ds[s],qty_good_received=6 if i==1 else q,qty_bs_laundry=1 if i==1 else 0,bs_product_id=f['roots'][i] if i==1 else None) for i,(s,q) in enumerate(zip(f['size_ids'],f['qtys']))]),base.delivery_version(cur,delivery))
    line=b.receipt_line(cur,rec['receipt_id'])
    rs=dict(cur.execute('select d.size_id::text,r.id::text from erp.laundry_receipt_batch_size_lines r join erp.laundry_delivery_batch_size_lines d on d.id=r.delivery_batch_size_line_id where r.receipt_line_id=%s',(line,)).fetchall())
    finish(cur,f,[dict(line=line,rs=rs)],range(4),15,quantities={1:6})
    ls=lots(cur,f);truth=b.all_truth(cur)
    _,normal=b.invoice(cur,f,[dict(line=line,qty=18,amount='111.11'),dict(line=line,category='BS',qty=1,amount='12.67')],'123.78')
    before=[b.lot_value(cur,l) for l in ls];ledger=books(cur)
    _,retry=b.invoice(cur,f,[dict(line=attempts[0],category='FAILED_ATTEMPT',qty=2,amount='17.11')],'17.11')
    after=[b.lot_value(cur,l) for l in ls];ledger_after=books(cur)
    _,retry2=b.invoice(cur,f,[dict(line=attempts[1],category='FAILED_ATTEMPT',qty=2,amount='14.00')],'14.00')
    _,correction=b.invoice(cur,f,[dict(line=attempts[0],category='FAILED_ATTEMPT',kind='CORRECTION',amount='0.89')],'0.89')
    corrected=[b.lot_value(cur,l) for l in ls]
    b.bd(cur,'REVERSE_INVOICE',dict(invoice_id=correction['invoice_id'],expected_version=correction['row_version'],reason='Exact correction inverse'))
    inverse=[b.lot_value(cur,l) for l in ls]
    name='BFC-CLAIM-'+uuid.uuid4().hex[:8]
    b.d12_bs(cur,'SAVE_CLAIM',dict(action='SAVE',claim_number=name,vendor_id=f['vendor'],delivery_id=delivery,qty_claimed=1,claim_type='MISSING',compensation_amount=0,opened_at=f['when'](16).isoformat(),change_reason='One exact missing piece after repeated wash'))
    claim=one(cur,'select id::text from erp.laundry_claims where claim_number=%s',name)
    b.d12_bs(cur,'SAVE_CLAIM',dict(id=claim,action='SAVE',status='ACCEPTED',compensation_amount=10,resolution_date=str(f['day']),change_reason='Vendor accepts compensation'),one(cur,'select row_version from erp.laundry_claims where id=%s',claim))
    ap_before=b.D(b.ap(cur,f['vendor']))
    b.d12_bs(cur,'RESOLVE_CLAIM',dict(laundry_claim_id=claim,resolution='SETTLED',change_reason='Settle missing piece'),one(cur,'select row_version from erp.laundry_claims where id=%s',claim))
    settled=b.D(b.ap(cur,f['vendor']))
    credit=dict(source_kind='DAILY_CLAIM',source_id=claim,target_kind='VENDOR_INVOICE',target_id=retry['invoice_id'],amount='10.00',date=str(f['day']),reason='Use credit against retry invoice')
    key=uuid.uuid4();b.bd(cur,'APPLY_CLAIM_CREDIT',credit,key=key)
    replay=b.bd(cur,'APPLY_CLAIM_CREDIT',credit,key=key)
    too_much=b.refused(cur,lambda:b.bd(cur,'APPLY_CLAIM_CREDIT',dict(credit,amount='0.01')),'BD_CLAIM_CREDIT_EXCEEDS_AVAILABLE')
    applied=b.D(b.ap(cur,f['vendor']));b.bd(cur,'REVERSE_VENDOR_SETTLEMENT',dict(target_kind='VENDOR_INVOICE',settlement_id=str(key),reason='Return claim credit to available balance'))
    screen=b.d12_screen(cur,f['vendor'])
    # The returned BS piece gets two warranty rewash attempts: first still BS,
    # second physically GOOD. Ordinary LAUNDRY rework has no new vendor fee;
    # paid redye is a separate service. The same BS balance must not be doubled.
    bs=one(cur,"select id::text from erp.bs_cases where po_id=%s and product_id=%s and status='OPEN'",f['po'],f['roots'][1])
    b.chain.bs_action(cur,'CLASSIFY_BS',dict(bs_case_id=bs,cause_source='UNKNOWN',components=[dict(work_component_id=prod.COMPONENT,completed_before_bs_qty=1)],change_reason='One returned BS piece, original work earned'),b.chain.version(cur,'bs_cases',bs))
    bom=one(cur,'select erp.resolve_rework_accessory_bom_v1(%s,%s)::text',bs,f['when'](17))
    money_before=books(cur);repair_lot=None
    for hour,good in ((17,0),(20,1)):
        made=b.chain.bs_action(cur,'SAVE_REWORK',dict(rework_number='BFC-FREE-'+uuid.uuid4().hex[:10],bs_case_id=bs,destination_type='LAUNDRY',contractor_id=None,vendor_id=f['vendor'],qty_sent=1,physical_sent_at=f['when'](hour).isoformat(),status='IN_PROGRESS',return_fg_location_id=base.LOCATION,accessory_bom_version_id=bom,accessory_bom_item_ids=[],components=[],change_reason='Warranty rewash of the same BS piece'))
        rid=made['result']['rework_order_id']
        done=b.chain.bs_action(cur,'COMPLETE_REWORK',dict(rework_order_id=rid,qty_good=good,qty_bs=1-good,completed_at=f['when'](hour+1).isoformat(),return_fg_location_id=base.LOCATION,change_reason='Physical result of this warranty attempt'),b.chain.version(cur,'rework_orders',rid))
        if good:repair_lot=done['result']['good_fg_lot_id']
    money_after=books(cur)
    return b.verdict(dict(package_once=state['known']=='123.78' and state['charges']==2 and duplicate['ok'],
        exact_retry_sources=one(cur,'select count(*) from erp.laundry_failed_wash_batch_size_lines where size_id=%s and qty_attempted_pcs=2',f['size_ids'][1])==2,
        physical_stock=[stock(cur,l) for l in ls]==[5,6,3,4],
        only32_cost_changed=all(before[i]==after[i] for i in (0,2,3)) and after[1]>before[1],
        variance_conserved=sum(ledger_after[k]-ledger[k] for k in ledger)==b.D('3.11'),
        correction_exact=corrected[1]>after[1] and inverse==after,
        claim_lowers_ap_once=ap_before-settled==10 and applied==settled and b.D(b.ap(cur,f['vendor']))==settled,
        credit_replay=replay.get('replayed') is True,credit_cannot_double_spend=too_much['ok'],
        reversed_credit_available=screen['ledger']['credit_available']=='10.00' and screen['ledger']['matches'] is True,
        warranty_one_physical_recovery=repair_lot is not None and stock(cur,repair_lot)==1 and one(cur,'select product_id::text from erp.fg_lots where id=%s',repair_lot)==f['roots'][1],
        warranty_not_paid_redye=one(cur,'select erp.be_redye_po_cost_v1(%s)',f['po'])==0 and sum(money_after.values())==sum(money_before.values()),
        truth=b.truth_quiet(truth,b.all_truth(cur))),lot_before=list(map(str,before)),lot_after=list(map(str,after)),
        ap_before=str(ap_before),ap_after=str(settled))
