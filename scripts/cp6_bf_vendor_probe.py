"""Owner-corrected vendor oracles. Native disposable transactions, never production."""
import copy, json, uuid
from datetime import timedelta
import cp6_bf_probe as bf
b, one = bf.b, bf.one


def historical_workspace(cur, today):
    roots = [p for p, _ in bf.products(cur, ('31', '32', '33', '34'))]
    now = one(cur, 'select clock_timestamp()'); t0 = now-timedelta(minutes=4); t1 = now-timedelta(minutes=2)
    a = bf.group(cur, roots[:3], t0); z = bf.group(cur, roots[3:], t0)
    bf.save(cur, [a,z], t0)
    a2 = bf.group(cur, roots, t1, sku=a['sku'], gid=a['id'], revision=1)
    z2 = bf.group(cur, roots[3:], t1, sku=z['sku'], gid=z['id'], revision=1)
    z2.update(members=[], legacy_basis=[]); bf.save(cur, [a2,z2], t1)
    def view(at):
        b.chain.production.owner(cur)
        r=one(cur,'select public.erp_get_sku_workspace_v1(%s::jsonb)',json.dumps(dict(at=at.isoformat(),roots=roots)))
        b.api.admin(cur);return r
    old, new = view(t0), view(t1)
    def sizes(w, sid):return {m['id'] for g in w['related_groups'] if g['id']==sid for m in g['members']}
    return b.verdict(dict(old_a=sizes(old,a['id'])==set(roots[:3]), old_b=sizes(old,z['id'])==set(roots[3:]),
        new_a=sizes(new,a['id'])==set(roots), new_b=sizes(new,z['id'])==set(),
        physical_old=next(p for p in old['selected_products'] if p['id']==roots[3])['group_id']==z['id'],
        write_revision=all(g['revision']=='2' and g['selected_revision']=='1' for g in old['related_groups'])))


def stale_wave(cur, today, pinned=False):
    rows=bf.products(cur,('31','34')); roots=[p for p,s in rows]
    now=one(cur,'select clock_timestamp()'); t0=now-timedelta(minutes=6); t1=now-timedelta(minutes=3)
    a=bf.group(cur,roots[:1],t0); z=bf.group(cur,roots[1:],t0)
    z['settings']['work_rates']=[dict(work_component_id=b.chain.production.COMPONENT,rate='17.00')]
    bf.save(cur,[a,z],t0); result={}
    def setup(cur,po,wave,batch,yields,when):
        bf.call(cur,'BIND_WAVE',dict(cutting_group_id=wave,expected_version=one(cur,'select erp.bf_wave_revision_v1(%s)',wave),
            references=[dict(size_id=rows[1][1],sku_id=z['id'])]))
        cur.execute('insert into erp.po_work_component_snapshots(po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at) values(%s,%s,1,3,%s)',(po,b.chain.production.COMPONENT,t0))
        if pinned:cur.execute('select erp.bf_ensure_work_v1(%s,%s)',(po,t1-timedelta(seconds=1)))
        a2=bf.group(cur,roots,t1,sku=a['sku'],gid=a['id'],revision=1)
        z2=bf.group(cur,roots[1:],t1,sku=z['sku'],gid=z['id'],revision=1,settings=z['settings']);z2.update(members=[],legacy_basis=[])
        bf.save(cur,[a2,z2],t1)
        if pinned:
            cur.execute('select erp.bf_ensure_work_v1(%s,%s)',(po,t1+timedelta(seconds=1)))
            result['pin_retained']=one(cur,'select count(*) from erp.po_work_component_snapshots x join erp.bf_sku_versions_v1 v on v.id=x.bf_sku_version_id where x.po_id=%s and v.sku_id=%s and v.revision=1 and x.rate_per_pcs_snapshot=17',po,z['id'])==1
        else:
            result['stale_refused']=b.refused(cur,lambda:cur.execute('select erp.bf_ensure_work_v1(%s,%s)',(po,t1+timedelta(seconds=1))),'BF_WAVE_REFERENCE_STALE')['ok']
            result['no_stale_snapshot']=one(cur,'select count(*) from erp.po_work_component_snapshots where po_id=%s and bf_sku_version_id is not null',po)==0
            bf.call(cur,'BIND_WAVE',dict(cutting_group_id=wave,expected_version=one(cur,'select erp.bf_wave_revision_v1(%s)',wave),references=[dict(size_id=rows[1][1],sku_id=a['id'])]))
            cur.execute('select erp.bf_ensure_work_v1(%s,%s)',(po,t1+timedelta(seconds=1)))
            result['explicit_rebind']=one(cur,'select count(*) from erp.po_work_component_snapshots x join erp.bf_sku_versions_v1 v on v.id=x.bf_sku_version_id where x.po_id=%s and v.sku_id=%s',po,a['id'])==1
    b.two_size_fixture(cur,b.case_day(today),'PR30-D02',size_quantities=[(rows[1][1],2)],clock=lambda h,m=0:t0+timedelta(seconds=h*4+m/15),work_setup=setup)
    return b.verdict(result)


def pending_invoice(cur, today, selected_unknown=False):
    fx=b.fixture(cur,b.case_day(today),'VENDOR-PENDING');b.terms(cur,fx,'COMPONENTS')
    pricing={'components':[]}
    if selected_unknown:
        known=b.component(cur,fx,'GARMENT','2.00');unknown=b.component(cur,fx,'SPRAY',None,'UNKNOWN')
        pricing={'components':[dict(component_id=c,covered_qty=10) for c in [known,unknown]]}
    b.invoice_policies(cur,after='CORRECTION_DOCUMENT')
    b.policy(cur,'LAU_DEC04',dict(sale_with_unknown_laundry='ALLOW_PENDING'))
    payload=dict(delivery=b.delivery_payload(fx),expected_version=str(b.chain.base.group_version(cur,fx['group'])),pricing=pricing)
    key=str(uuid.uuid4());sent=b.bd(cur,'POST_PRICED_DELIVERY',payload,key);replay=b.bd(cur,'POST_PRICED_DELIVERY',payload,key)
    state=b.line_state(cur,sent['delivery_id']);rec=b.receive(cur,sent['delivery_id'],fx,10,13);line=b.receipt_line(cur,rec['receipt_id'])
    product,lot=b.finish_goods(cur,fx,rec['receipt_id'],10,14);sale=b.sell(cur,fx,product,4,15)
    before=b.lot_value(cur,lot);known_total=b.D(20 if selected_unknown else 0)
    before_unknown=one(cur,'select erp.bd_lot_laundry_unknown_v1(%s)',lot)
    _,first=b.invoice(cur,fx,[dict(line=line,qty=4,amount='28.00')],'28.00')
    partial_unknown=one(cur,'select erp.bd_lot_laundry_unknown_v1(%s)',lot)
    invoice_day=dict(fx,day=fx['day']+timedelta(days=1))
    _,second=b.invoice(cur,invoice_day,[dict(line=line,qty=6,amount='45.17')],'45.17')
    after=b.lot_value(cur,lot);paid=b.D(b.ap(cur,fx['vendor']));complete=not one(cur,'select erp.bd_lot_laundry_unknown_v1(%s)',lot)
    current_blockers=b.blockers(cur,invoice_day['day'],sent['delivery_id'])
    earlier_blockers=b.blockers(cur,fx['day'],sent['delivery_id'])
    immutable=True
    if selected_unknown:
        charge=one(cur,"select id::text from erp.bd_laundry_charge_lines_v1 where delivery_line_id=%s and rate_status='UNKNOWN'",state['line'])
        immutable=b.refused(cur,lambda:b.bd(cur,'SET_CHARGE_PRICE',dict(charge_line_id=charge,rate_per_pcs='9.00',reason='Cannot rewrite invoiced quote')),'BD_ALREADY_INVOICED')['ok']
    b.bd(cur,'REVERSE_INVOICE',dict(invoice_id=second['invoice_id'],expected_version=second['row_version'],reason='Vendor replaces second bill'))
    reopened=one(cur,'select erp.bd_lot_laundry_unknown_v1(%s)',lot)
    return b.verdict(dict(rate_unknown=state['rate'] is None and sent['estimated_cost'] is None,
        no_fake_component=state['charges']==(2 if selected_unknown else 0),replay=replay['replayed'] and replay['delivery_id']==sent['delivery_id'],
        pending_before=before_unknown,pending_partial=partial_unknown,invoice_clears=complete,
        exact_hpp_delta=after-before==b.D('73.17')-known_total,ap_once=paid==b.D('73.17'),
        close_current='BD_LAUNDRY_COMPONENT_PRICE_UNKNOWN' not in current_blockers,
        close_historical='BD_LAUNDRY_COMPONENT_PRICE_UNKNOWN' in earlier_blockers,
        immutable_quote=immutable,reversal_reopens=reopened and b.D(b.ap(cur,fx['vendor']))==28,
        sale_recorded=one(cur,'select count(*) from erp.bd_pending_price_sales_v1 where sale_id=%s',sale)==1),
        hpp_before=str(before),hpp_after=str(after),ap=str(paid),blockers=current_blockers)


def vendor_authority(cur,today):
    fx=b.fixture(cur,b.case_day(today),'VENDOR-AUTHORITY');b.process_rate(cur,fx,'7.13')
    root=b.sized_product(cur,b.chain.base.SIZE,'VENDOR-'+uuid.uuid4().hex[:8])
    g=bf.group(cur,[root],fx['start']);saved=bf.save(cur,[g],fx['start']);vid=saved['groups'][0]['version_id']
    # Existing wrong configuration is a fixture of the previous product, never a
    # new public master mutation. It must have no monetary authority after repair.
    override=dict(vendor_id=fx['vendor'],kind='PROCESS',ref_id=fx['process'],rate_status='KNOWN',rate='999.00',reason='Legacy wrong authority')
    cur.execute("update erp.bf_sku_versions_v1 set settings=jsonb_set(settings,'{laundry_rates}',%s::jsonb) where id=%s",(json.dumps([override]),vid))
    cur.execute('insert into erp.bf_wave_skus_v1 values(%s,%s,%s,clock_timestamp(),erp.current_app_user_id(),%s)',(fx['group'],b.chain.base.SIZE,g['id'],uuid.uuid4()))
    computed=b.compute(cur,b.delivery_payload(fx),{})
    c=b.component(cur,fx,'GARMENT','3.17');comp=b.compute(cur,b.delivery_payload(fx),dict(components=[dict(component_id=c,covered_qty=10)]))
    g2=bf.group(cur,[root],fx['start']+timedelta(seconds=1),sku=g['sku'],gid=g['id'],revision=1);g2['settings']['laundry_rates']=[override]
    rejected=b.refused(cur,lambda:bf.save(cur,[g2],fx['start']+timedelta(seconds=1)),'BF_LAUNDRY_VENDOR_AUTHORITY')
    return b.verdict(dict(vendor_rate=b.D(computed['total_known'])==b.D('71.30'),vendor_components=b.D(comp['total_known'])==b.D('31.70'),
        source_not_sku=all(c.get('bf_sku_version_id') is None for c in computed['charges']),new_sku_override_refused=rejected['ok']))
