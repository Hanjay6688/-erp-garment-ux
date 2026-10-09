"""Independent discount, size attribution, identity and combined late-invoice flow."""
import json,uuid
from decimal import Decimal as D
import cases_business as b
from cases_stage import admin,check,wrap,refusal,digest_rows

def balanced(cur):
    admin(cur)
    bad=cur.execute('select journal_entry_id,sum(debit-credit) from erp.journal_lines group by journal_entry_id having sum(debit-credit)<>0').fetchall()
    check(not bad,'Every journal balances independently',bad=bad)

def cases(cur,today):
    def discounts():
        rows=[];l=b.laundry
        for gross,disc in [('21474836.48','0.01'),('22000000.01','13.17')]:
            f=l.fixture(cur,today,'ASCDISC');l.process_rate(cur,f,'17.37');l.invoice_policies(cur)
            l.policy(cur,'LAU_DEC03',dict(discount='ALLOWED',extra='REFUSED',rounding='REFUSED'))
            line=l.receipt_line(cur,l.receive(cur,l.plain_delivery(cur,f,10,11),f,10,13)['receipt_id'])
            before=D(l.wip(cur,f['po']));ap_before=D(l.ap(cur,f['vendor']));net=D(gross)-D(disc)
            draft,posted=l.invoice(cur,f,[dict(line=line,qty=10,amount=gross)],str(net),discount_amount=disc)
            ln=posted['lines'][0]
            check(D(l.ap(cur,f['vendor']))-ap_before==net and D(ln['net_amount'])==net and D(ln['discount_share'])==D(disc),'Nonzero discount at large nominal yields exact payable and line allocation',gross=gross,discount=disc,line=ln)
            check(D(l.wip(cur,f['po']))-before==net-D('173.70'),'Exact invoice variance lands in the real WIP source',before=before,after=l.wip(cur,f['po']),expected=net-D('173.70'))
            balanced(cur);rows.append(dict(gross=gross,discount=disc,net=str(net),posted=posted))
        return rows

    def sizes():
        l=b.laundry;base=l.chain.base;f=l.two_size_fixture(cur,l.case_day(today),'ASCSIZE',q1=11,q2=7)
        common=l.component(cur,f,'AS-COMMON','1.37');extra=l.component(cur,f,'AS-THREE','2.03');l.terms(cur,f,'COMPONENTS')
        payload=dict(distribution_batch_id=f['batch'],vendor_id=f['vendor'],wash_process_id=f['process'],target_dyeing_color='Astra explicit size service',physical_at=l.iso(l.chain.production.at(f['day'],11)),reason='Extra only3 of7 second-size pieces',lines=[dict(size_id=base.SIZE,qty_sent_pcs=11),dict(size_id=f['size2'],qty_sent_pcs=7)])
        pricing=dict(components=[dict(component_id=common,covered_qty=18),dict(component_id=extra,covered_qty=3,coverage=[dict(size_id=f['size2'],qty=3)])])
        sent=l.bd(cur,'POST_PRICED_DELIVERY',dict(delivery=payload,expected_version=str(base.group_version(cur,f['group'])),pricing=pricing));admin(cur)
        ds=dict(cur.execute('select s.size_id::text,s.id::text from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines d on d.id=s.delivery_line_id where d.delivery_id=%s',(sent['delivery_id'],)).fetchall())
        expected={base.SIZE:D('15.07'),f['size2']:D('15.68')}
        estimates={s:D(cur.execute('select known_amount from erp.bd_laundry_size_estimates_v1 where delivery_batch_size_line_id=%s',(i,)).fetchone()[0]) for s,i in ds.items()}
        check(estimates==expected and sum(estimates.values())==D('30.75'),'No extra charge to eleven ineligible pieces',expected=expected,actual=estimates)
        rec=l.chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=sent['delivery_id'],wash_process_id=f['process'],physical_at=l.iso(l.chain.production.at(f['day'],13)),reason='Astra full two-size receipt',lines=[dict(delivery_batch_size_line_id=ds[s],qty_good_received=q,qty_bs_laundry=0,bs_product_id=None) for s,q in [(base.SIZE,11),(f['size2'],7)]]),base.delivery_version(cur,sent['delivery_id']));admin(cur)
        line=l.receipt_line(cur,rec['receipt_id']);rs=dict(cur.execute('select ds.size_id::text,s.id::text from erp.laundry_receipt_batch_size_lines s join erp.laundry_delivery_batch_size_lines ds on ds.id=s.delivery_batch_size_line_id where s.receipt_line_id=%s',(line,)).fetchall())
        allocated={s:D(cur.execute('select amount from erp.bd_laundry_receipt_allocations_v1 where receipt_batch_size_line_id=%s',(i,)).fetchone()[0]) for s,i in rs.items()}
        check(allocated==expected,'Actual receipt conserves explicit eligible-size amounts',actual=allocated)
        products={s:l.sized_product(cur,s,'ASCS-'+uuid.uuid4().hex[:8]) for s in ds}
        l.chain.laundry_action(cur,'POST_FINAL_SKU',dict(cutting_group_id=f['group'],destination_location_id=base.LOCATION,physical_at=l.iso(l.chain.production.at(f['day'],14)),reason='Astra18 real FG pieces',good_qty_pcs=18,completion_mode='ALL_READY',lines=[dict(final_product_id=products[s],qty_good_pcs=q,qty_bs_pcs=0,source_laundry_receipt_line_id=line,source_laundry_receipt_batch_size_line_id=rs[s]) for s,q in [(base.SIZE,11),(f['size2'],7)]]),base.group_version(cur,f['group']));admin(cur)
        values={s:D(l.lot_value(cur,cur.execute("select id from erp.fg_lots where po_id=%s and product_id=%s and lot_origin='PRODUCTION'",(f['po'],p)).fetchone()[0])) for s,p in products.items()}
        other=[(values[base.SIZE]-expected[base.SIZE])/11,(values[f['size2']]-expected[f['size2']])/7]
        check(abs(other[0]-other[1])<D('0.000001'),'Equal non-laundry per-piece cost keeps size-specific service attribution',lot_values=values,other_cost_per_piece=other)
        balanced(cur);return dict(quantities=[11,7],extra_eligible=3,estimates=estimates,allocations=allocated,lot_values=values,other_per_piece=other)

    def actor_uuid():
        p=b.procurement;f=p.fixture(cur,today,'23','7.19',True)
        left,_=p.custom(cur,p.OPS+('finance.ap.view',));right,_=p.custom(cur,p.OPS+('finance.ap.view',));key=uuid.uuid4()
        first=p.command(cur,'SAVE_DRAFT',f['payload'],key,subject=left);facts=digest_rows(cur,'erp','material_purchase_headers')
        other=refusal(cur,lambda:p.command(cur,'SAVE_DRAFT',f['payload'],key,subject=right))
        check(other['refused'] or other['result'].get('purchase_id')!=first['purchase_id'],'Other actor cannot replay original successful UUID',original=first,other=other)
        check(digest_rows(cur,'erp','material_purchase_headers')==facts and p.qty(cur,f)==(0,0),'Cross-actor probe leaves no physical side effect')
        # Savepoint wrapper observes action binding but rolls back any valid distinct POST.
        action=refusal(cur,lambda:p.post(cur,first,key,subject=left))
        check(action['refused'] or action['result'].get('status')=='POSTED','POST cannot replay a SAVE_DRAFT response',save=first,cross_action=action)
        posted=p.post(cur,first,uuid.uuid4(),subject=left)
        check(p.qty(cur,f)==(D(23),1),'Exactly one committed physical receipt')
        balanced(cur);return dict(cross_actor=other,cross_action=action,posted=posted)

    def combined():
        f=b.production(cur,today,final=False);initial=b.gl(cur)
        b.drafts.create(cur,f,b.drafts.payload(f,'13','29.91'));p,v=b.cmd.review(cur,f);b.cmd.command(cur,'POST',p,v)
        b.returns.payments.pay(cur,f,'137.03');f['allocations']=b.returns.read(cur,f)['page']['rows'];p,v=b.returns.payload(cur,f,qty='4',refund='119.64');b.cmd.command(cur,'RETURN',p,v)
        sold=b.gl(cur);check(b.fg_qty(cur,f)==32,'Initial sale/return physical32')
        f['receipt']=dict(purchase_id=f['purchase']);f['item']=str(cur.execute('select id from erp.material_purchase_items where purchase_id=%s',(f['purchase'],)).fetchone()[0])
        one=b.invoices.finalize(cur,f,'17','13.11');two=b.invoices.finalize(cur,f,'56','11.91')
        # Accepted maintenance queue is explicit; P09 facade does not promise to run it.
        b.native(cur,'select erp.process_cost_recalc_queue(100)')
        ap,grni,raw,average=b.invoices.amounts(cur,f);check((ap,grni,raw)==(D('889.83'),D(0),D(32)),'All73 invoiced exactly once;32raw remain')
        unit=D('889.83')/73+D('1.13')+D('.89')+D('2.07')
        expected_state=(b.money(41*unit),b.money(32*unit),b.money(9*unit))
        state=cur.execute('select hpp_total_cost,fg_value,cogs_value from erp.po_hpp_gl_state where po_id=%s',(f['po'],)).fetchone()
        check(state==expected_state,'Independent fractional invoice blend splits41production into32FG+9net-sold',unit=str(unit),expected=expected_state,actual=state)
        wanted={b.account(cur,'AP_SUPPLIER'):D('-889.83'),b.account(cur,'GRNI_MATERIAL'):D('903.01'),b.account(cur,'MATERIAL_INVENTORY'):b.money(D(32)*D('889.83')/73)-D('395.84'),b.account(cur,'FG_INVENTORY'):expected_state[1]-D('526.72'),b.account(cur,'COGS'):expected_state[2]-D('148.14')}
        actual=b.delta(sold,b.gl(cur));check(actual=={k:v for k,v in wanted.items() if v},'Every late recost destination independently exact',expected=wanted,actual=actual)
        ar=D(b.returns.source.read(cur,f)['detail']['financial']['open_balance']);check(ar==D('132.16') and b.fg_qty(cur,f)==32,'Late invoice changes no revenue, receivable, physical quantity')
        check(D(b.laundry.wip(cur,f['po']))==0,'Finished production retains zero WIP')
        balanced(cur);return dict(AP=ap,GRNI=grni,raw=raw,FG=32,AR=ar,unit=unit,hpp_state=state,expected_hpp=expected_state,recost_delta=actual,documents=[one,two])

    return [wrap('AS20C-07-DISCOUNT',discounts),wrap('AS20C-08-SIZE',sizes),wrap('AS20C-04-ACTOR',actor_uuid),wrap('AS20C-50-LATE',combined)]
