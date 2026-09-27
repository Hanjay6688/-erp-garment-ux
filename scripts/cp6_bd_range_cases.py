"""Owner 28 Sep: commercial SKU ranges, physical-size stock, weighted SKU HPP.
Synthetic tariff amounts; disposable writer evidence, never independent closure.
No tariff is inferred from the number of sizes in a shipment.
"""
import uuid
from decimal import Decimal as D


def range_fixture(b,cur,today,label,quantities):
    b.chain.actors.admin(cur)
    sizes=[]
    for code,n in quantities:
        found=b.q(cur,'select id::text from erp.sizes where size_code=%s',(code))
        sid=found[0][0] if found else str(uuid.uuid4())
        if not found:cur.execute('insert into erp.sizes(id,size_code,sort_order,is_active) values(%s,%s,%s,true)',(sid,code,int(code)))
        cur.execute('insert into erp.product_model_sizes(model_id,size_id,sort_order) select %s,%s,%s where not exists(select 1 from erp.product_model_sizes where model_id=%s and size_id=%s)',
            (b.chain.production.MODEL,sid,int(code),b.chain.production.MODEL,sid))
        sizes.append((sid,n))
    fx=b.two_size_fixture(cur,today,label,size_quantities=sizes)
    fx['codes']={code:sid for (code,_),(sid,_) in zip(quantities,sizes)}
    return fx


def payload(b,fx,hour=11):
    return dict(b.delivery_payload(fx,hour=hour),lines=[dict(size_id=s,qty_sent_pcs=n) for s,n in fx['sizes']])


def post(b,cur,fx,pricing,hour=11):
    return b.bd(cur,'POST_PRICED_DELIVERY',dict(delivery=payload(b,fx,hour),pricing=pricing,
        expected_version=str(b.chain.base.group_version(cur,fx['group']))))


def same_rate(b,cur,today):
    fixtures=[range_fixture(b,cur,today,'RANGE-'+name,sizes) for name,sizes in [
        ('31-33',[('31',4),('32',7),('33',2)]),('32-ONLY',[('32',6)]),('27-SINGLE',[('27',3)])]]
    first=fixtures[0];b.process_rate(cur,first,'1731.29');b.terms(cur,first,'RATE')
    evidence=[];checks={};version_ids=set()
    for fx in fixtures:
        fx.update(vendor=first['vendor'],process=first['process'])
        sent=post(b,cur,fx,{})
        charges=sent['pricing']['charges'];total=sum(n for _,n in fx['sizes'])
        checks[str(list(fx['codes']))]=D(str(sent['estimated_cost']))==D('1731.29')*total and all(D(c['unit_rate'])==D('1731.29') for c in charges)
        # The public receipt deliberately omits internal price-version IDs. Read actual stored snapshots.
        versions=b.q(cur,'select c.version_id::text from erp.bd_laundry_charge_lines_v1 c join erp.laundry_delivery_lines l on l.id=c.delivery_line_id where l.delivery_id=%s',sent['delivery_id'])
        assert len(versions)==len(charges) and all(v for v, in versions),'STORED_PRICE_VERSION_REQUIRED'
        version_ids.update(v for v, in versions)
        stored=b.q(cur,'select s.size_id::text,s.qty_sent_pcs from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where l.delivery_id=%s',sent['delivery_id'])
        checks['physical_'+fx['batch']]=dict(stored)==dict(fx['sizes'])
        evidence.append(dict(sizes=fx['codes'],quantities=stored,delivery=sent['delivery_id'],pricing=sent['pricing'],stored_version_ids=[v for v, in versions]))
    # Owner's 27 is a distinct commercial SKU, e.g. 32007-27, not a size-price override in the range SKU.
    # This case only proves delivery arithmetic and no implicit surcharge. It does not prove a SKU tariff resolver.
    checks.update(same_master_version=len(version_ids)==1,singleton_27_no_implicit_surcharge=b.line_state(cur,evidence[2]['delivery'])['known']=='5193.87')
    return b.verdict(checks,shipments=evidence)


def stock_hpp(b,cur,today):
    from cp6_be_pocket_probe import return_sale
    fx=range_fixture(b,cur,today,'SKU-HPP',[('31',4),('32',7),('33',2)])
    wash=b.component(cur,fx,'RANGE_WASH','4321.09');finish=b.component(cur,fx,'RANGE_FINISH','678.91');b.terms(cur,fx,'COMPONENTS')
    sent=post(b,cur,fx,dict(components=[dict(component_id=wash,covered_qty=13,coverage=[dict(size_id=s,qty=n) for s,n in fx['sizes']]),
        dict(component_id=finish,covered_qty=5,coverage=[dict(size_id=fx['codes']['32'],qty=5)])]))
    delivery=sent['delivery_id'];base=b.chain.base
    sources=dict(b.q(cur,'select s.size_id::text,s.id::text from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where l.delivery_id=%s',delivery))
    rec=b.chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=delivery,wash_process_id=fx['process'],physical_at=b.iso(b.chain.production.at(fx['day'],13)),
        reason='SKU range receipt',lines=[dict(delivery_batch_size_line_id=sources[s],qty_good_received=n,qty_bs_laundry=0,bs_product_id=None) for s,n in fx['sizes']]),base.delivery_version(cur,delivery))
    rline=b.receipt_line(cur,rec['receipt_id'])
    received=dict(b.q(cur,'select d.size_id::text,r.id::text from erp.laundry_receipt_batch_size_lines r join erp.laundry_delivery_batch_size_lines d on d.id=r.delivery_batch_size_line_id where r.receipt_line_id=%s',rline))
    # One human SKU/model/brand/colour, different immutable physical product IDs.
    label='RANGE-SKU-'+uuid.uuid4().hex[:8];products={s:b.sized_product(cur,s,label) for s,_ in fx['sizes']}
    b.chain.laundry_action(cur,'POST_FINAL_SKU',dict(cutting_group_id=fx['group'],destination_location_id=base.LOCATION,
        physical_at=b.iso(b.chain.production.at(fx['day'],14)),reason='SKU range exact-size FG',good_qty_pcs=13,completion_mode='ALL_READY',
        lines=[dict(final_product_id=products[s],qty_good_pcs=n,qty_bs_pcs=0,source_laundry_receipt_line_id=rline,source_laundry_receipt_batch_size_line_id=received[s]) for s,n in fx['sizes']]),base.group_version(cur,fx['group']))
    def rows():return b.q(cur,"""select s.size_code,l.id::text,l.product_id::text,p.sku,
        coalesce((select sum(qty_signed) from erp.fg_stock_movements m where m.lot_id=l.id),0),h.hpp_per_pcs,h.total_cost
        from erp.fg_lots l join erp.products p on p.id=l.product_id join erp.sizes s on s.id=p.size_id
        join erp.hpp_versions h on h.lot_id=l.id and h.is_current where l.po_id=%s order by s.size_code""",fx['po'])
    def summary(rs):
        qty=sum(r[4] for r in rs);value=sum(r[4]*r[5] for r in rs)
        return dict(qty=qty,value=value,weighted=value/qty if qty else None)
    before=rows();total=sum(r[6] for r in before)
    estimates=dict(b.q(cur,'select s.size_code,e.known_amount from erp.bd_laundry_size_estimates_v1 e join erp.laundry_delivery_batch_size_lines d on d.id=e.delivery_batch_size_line_id join erp.sizes s on s.id=d.size_id where d.id=any(%s::uuid[])',list(sources.values())))
    sale=b.sell(cur,fx,products[fx['codes']['32']],2,16);after_sale=rows()
    allocation=b.q(cur,'select a.lot_id::text,a.qty_pcs from erp.sale_stock_allocations a join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s',sale)
    b.invoice_policies(cur);g0={k:b.gl(cur,k) for k in ['FG_INVENTORY','COGS','WIP']}
    _,invoice=b.invoice(cur,fx,[dict(line=rline,qty=13,amount='59581.72')],'59581.72')
    after_invoice=rows();delta={k:b.gl(cur,k)-v for k,v in g0.items()}
    ret=return_sale(cur,sale,fx['day']);after_return=rows()
    returned=b.q(cur,'select product_id::text,lot_id::text,qty_pcs from erp.sales_return_items where return_id=%s',ret)
    lot32=next(r[1] for r in before if r[0]=='32')
    return b.verdict(dict(one_commercial_sku=len({r[3] for r in before})==1,three_physical_products=len({r[2] for r in before})==3,
        stock_by_size={r[0]:r[4] for r in before}=={'31':4,'32':7,'33':2},
        finish_only_32=estimates=={'31':D('17284.36'),'32':D('33642.18'),'33':D('8642.18')},
        total_hpp_preserved=total==D('59668.72'),
        weighted_not_unweighted=summary(before)['weighted']!=sum(r[5] for r in before)/3,
        stock_after_sale={r[0]:r[4] for r in after_sale}=={'31':4,'32':5,'33':2},sale_from_exact_size=allocation==[(lot32,2)],
        invoice_updates_each_source_once=all(b1[6]-b0[6]==b0[4] for b0,b1 in zip(before,after_invoice)),
        sold_unsold_conserve=delta=={'FG_INVENTORY':D(11),'COGS':D(2),'WIP':D(0)},
        stock_after_return={r[0]:r[4] for r in after_return}=={'31':4,'32':6,'33':2},
        return_same_product_lot=returned==[(products[fx['codes']['32']],lot32,1)]),
        estimates=estimates,lots=dict(before=before,after_sale=after_sale,after_invoice=after_invoice,after_return=after_return),
        sku_summaries=[summary(rs) for rs in [before,after_sale,after_invoice,after_return]],ledger_delta=delta,invoice=invoice['invoice_id'])


def cases(b,cur,today):
    return [('RANGE:SAME_SERVICE_VERSION_MIXED_SINGLE_32_SINGLETON_27',lambda:same_rate(b,cur,today)),
        ('RANGE:SKU_WEIGHTED_HPP_PHYSICAL_STOCK_SALE_RETURN_INVOICE',lambda:stock_hpp(b,cur,today))]
