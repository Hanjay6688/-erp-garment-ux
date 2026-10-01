"""Current vendor-price regressions. Disposable transactions; not independent closure.

The production fixture buys/consumes fabric worth 100.00 through ordinary APIs.
Arithmetic oracle: 16 PCS (5/8/3), work 127.19 => 2035.04, laundry zero;
including that explicitly known fabric, HPP is 2135.04 (667.20/1067.52/400.32).
This does not pretend to reproduce the auditor's zero-fabric prerequisite.
"""
import copy,json,uuid
from datetime import timedelta
import cp6_bf_probe as bf

b=bf.b
one=bf.one


def master_fixture(cur,all_statuses=False):
    now=one(cur,'select clock_timestamp()');at=now-timedelta(minutes=4)
    rows=bf.products(cur);vendor,process=str(uuid.uuid4()),str(uuid.uuid4());tag=uuid.uuid4().hex[:8]
    cur.execute("insert into erp.laundry_vendors(id,vendor_code,vendor_name,is_active) values(%s,%s,'SKU free service',true)",(vendor,'FREE-'+tag))
    cur.execute("insert into erp.wash_processes(id,process_code,process_name,is_active) values(%s,%s,'SKU free wash',true)",(process,'FREE-'+tag))
    statuses=['FREE','WAIVED']+(['KNOWN','UNKNOWN'] if all_statuses else [])
    rates=[]
    for status in statuses:
        component=b.bd(cur,'SAVE_COMPONENT',dict(vendor_id=vendor,component_code=status,component_name='SKU '+status,is_active=True,reason='Synthetic free SKU master prerequisite'))['component_id']
        rate=dict(vendor_id=vendor,kind='COMPONENT',ref_id=component,rate_status=status,
                  rate=None if status=='UNKNOWN' else '101.23' if status=='KNOWN' else '0.00',reason='Disposable vendor fixture '+status)
        payload=dict(component_id=component,rate_status=status,effective_from=at.isoformat(),reason=rate['reason'])
        if status!='UNKNOWN':payload['rate_per_pcs']=rate['rate']
        b.bd(cur,'SAVE_COMPONENT_RATE',payload)
        rates.append(rate)
    settings=dict(price='185000.00',bom=[],work_rates=[dict(contractor_id=None,work_component_id=b.chain.production.COMPONENT,rate='127.19')],laundry_rates=[])
    g=bf.group(cur,[p for p,_ in rows],at,settings=settings)
    return dict(rows=rows,now=now,at=at,g=g,vendor=vendor,process=process,rates=rates)


def master_statuses(cur,today):
    f=master_fixture(cur,True);key=str(uuid.uuid4())
    first=bf.save(cur,[f['g']],f['at'],key);again=bf.save(cur,[f['g']],f['at'],key)
    vid=first['groups'][0]['version_id']
    settings=one(cur,'select settings from erp.bf_sku_versions_v1 where id=%s',vid)
    native=cur.execute('select c.id::text,r.rate_status,r.rate_per_pcs,r.reason from erp.bd_laundry_components_v1 c join erp.bd_laundry_component_rates_v1 r on r.component_id=c.id where c.vendor_id=%s order by c.component_code',(f['vendor'],)).fetchall()
    expected=sorted([(r['ref_id'],r['rate_status'],None if r['rate'] is None else b.D(r['rate']),r['reason']) for r in f['rates']],key=lambda r:r[1])
    return b.verdict(dict(all_four_vendor_statuses=native==expected,sku_has_no_laundry_authority=settings['laundry_rates']==[],
        one_shared_version=one(cur,'select count(*) from erp.bf_sku_members_v1 where version_id=%s',vid)==3,
        replay=again['replayed'] and again['groups']==first['groups'],
        once=one(cur,'select revision from erp.bf_skus_v1 where id=%s',f['g']['id'])==1),vendor_rates=native)


def invalid_rates():
    return [
      ('FREE_MISSING_REASON',dict(rate_status='FREE',rate_per_pcs='0.00',reason=None),'BD_REASON_REQUIRED'),
      ('FREE_BLANK_REASON',dict(rate_status='FREE',rate_per_pcs='0.00',reason='   '),'BD_REASON_REQUIRED'),
      ('WAIVED_MISSING_REASON',dict(rate_status='WAIVED',rate_per_pcs='0.00',reason=None),'BD_REASON_REQUIRED'),
      ('WAIVED_BLANK_REASON',dict(rate_status='WAIVED',rate_per_pcs='0.00',reason='   '),'BD_REASON_REQUIRED'),
      ('FREE_NONZERO',dict(rate_status='FREE',rate_per_pcs='0.01'),'BD_FREE_REQUIRES_ZERO'),
      ('WAIVED_NONZERO',dict(rate_status='WAIVED',rate_per_pcs='0.01'),'BD_FREE_REQUIRES_ZERO'),
      ('KNOWN_ZERO',dict(rate_status='KNOWN',rate_per_pcs='0.00'),'BD_AMOUNT_INVALID'),
      ('NEGATIVE',dict(rate_status='FREE',rate_per_pcs='-0.01'),'BD_AMOUNT_INVALID'),
      ('UNKNOWN_NUMERIC',dict(rate_status='UNKNOWN',rate_per_pcs='0.00'),'BD_RATE_STATUS'),
    ]


def atomic_rejections(cur,today):
    f=master_fixture(cur);bf.save(cur,[f['g']],f['at']);g=f['g'];at=f['now']-timedelta(minutes=2)
    update=bf.group(cur,[p for p,_ in f['rows']],at,sku=g['sku'],gid=g['id'],revision=1,settings=copy.deepcopy(g['settings']))
    update['settings']['price']='190000.00'
    def state():
        return [one(cur,'select revision from erp.bf_skus_v1 where id=%s',g['id']),
            one(cur,'select count(*) from erp.bf_requests_v1'),
            one(cur,'select count(*) from erp.bf_sku_versions_v1'),
            one(cur,'select count(*) from erp.bd_requests_v1'),
            cur.execute('select id::text,rate_status,rate_per_pcs,effective_from,effective_to,reason from erp.bd_laundry_component_rates_v1 order by id').fetchall(),
            [one(cur,'select erp.resolve_product_price_at(%s,%s)',p,f['now']) for p,_ in f['rows']]]
    before=state();checks={};evidence=[]
    for label,patch,code in invalid_rates():
        bad=dict(component_id=f['rates'][0]['ref_id'],effective_from=at.isoformat(),reason='Rejected vendor rate fixture',**{k:v for k,v in patch.items() if k!='reason'})
        if 'reason' in patch:bad['reason']=patch['reason']
        result=b.refused(cur,lambda:b.bd(cur,'SAVE_COMPONENT_RATE',bad),code)
        checks[label]=result['ok'] and state()==before;evidence.append(dict(case=label,result=result))
    bad=copy.deepcopy(update);bad['settings']['laundry_rates']=[copy.deepcopy(f['rates'][0])]
    result=b.refused(cur,lambda:bf.save(cur,[bad],at),'BF_LAUNDRY_VENDOR_AUTHORITY')
    checks['SKU_OVERRIDE_REFUSED']=result['ok'] and state()==before
    return b.verdict(checks,evidence=evidence)


def free_production(cur,today):
    f=master_fixture(cur);g=f['g'];saved=bf.save(cur,[g],f['at']);vid=saved['groups'][0]['version_id']
    prod,base=b.chain.production,b.chain.base
    rows=f['rows'];sizes=[s for _,s in rows];qtys=[5,8,3]
    clock=lambda hour,minute=0:f['now']-timedelta(seconds=(19-hour-minute/60)*10)
    def setup(cur,po,wave,batch,yields,when):
        bf.call(cur,'BIND_WAVE',dict(cutting_group_id=wave,expected_version=one(cur,'select erp.bf_wave_revision_v1(%s)',wave),
            references=[dict(size_id=s,sku_id=g['id']) for s in sizes]))
        cur.execute('insert into erp.po_work_component_snapshots(po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at) values(%s,%s,1,3,%s)',(po,prod.COMPONENT,when(9,30)))
        prod.owner(cur);cur.execute('select erp.ensure_po_work_component_snapshots_v2(%s,%s,%s)',(po,when(10),uuid.uuid4()));b.api.admin(cur)
        snap=one(cur,'select id::text from erp.po_work_component_snapshots where po_id=%s and bf_sku_version_id=%s and work_component_id=%s',po,vid,prod.COMPONENT)
        e=str(uuid.uuid4());b.chain.peer.ordinary(cur)
        cur.execute("insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by) values(%s,%s,%s,%s,%s,%s,'DRAFT','SKU free native work',%s)",(e,'FREE-'+e,po,prod.CONTRACTOR,wave,when(10),base.OPERATOR_APP))
        cur.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot) values(%s,%s,%s,16,16,0)',(e,snap,prod.COMPONENT))
        cur.execute('select erp.post_work_completion(%s)',(e,));prod.owner(cur)
        cur.execute('select public.erp_record_sewing_terminal_v1(%s::jsonb,%s)',(json.dumps(dict(work_completion_id=e,qty_pcs=16,reason='SKU free actual sewing')),uuid.uuid4()));b.api.admin(cur)
    fx=b.two_size_fixture(cur,b.case_day(today),'SKU-FREE',size_quantities=list(zip(sizes,qtys)),clock=clock,work_setup=setup,service_refs=(f['vendor'],f['process']))
    b.terms(cur,fx,'COMPONENTS')
    delivery_payload=dict(distribution_batch_id=fx['batch'],vendor_id=f['vendor'],wash_process_id=f['process'],target_dyeing_color='FREE-BLUE',physical_at=clock(11).isoformat(),reason='SKU free actual recipients',lines=[dict(size_id=s,qty_sent_pcs=q) for s,q in zip(sizes,qtys)])
    pricing=dict(components=[dict(component_id=f['rates'][0]['ref_id'],covered_qty=16),dict(component_id=f['rates'][1]['ref_id'],covered_qty=3,coverage=[dict(size_id=sizes[1],qty=3)])])
    key=str(uuid.uuid4());payload=dict(delivery=delivery_payload,expected_version=str(base.group_version(cur,fx['group'])),pricing=pricing)
    sent=b.bd(cur,'POST_PRICED_DELIVERY',payload,key);again=b.bd(cur,'POST_PRICED_DELIVERY',payload,key)
    delivery=sent['delivery_id']
    ds=dict(cur.execute('select s.size_id::text,s.id::text from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where l.delivery_id=%s',(delivery,)).fetchall())
    received=b.chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=delivery,wash_process_id=f['process'],physical_at=clock(13).isoformat(),reason='SKU free exact-size return',
        lines=[dict(delivery_batch_size_line_id=ds[s],qty_good_received=q,qty_bs_laundry=0,bs_product_id=None) for s,q in zip(sizes,qtys)]),base.delivery_version(cur,delivery))
    line=b.receipt_line(cur,received['receipt_id'])
    rs=dict(cur.execute('select d.size_id::text,r.id::text from erp.laundry_receipt_batch_size_lines r join erp.laundry_delivery_batch_size_lines d on d.id=r.delivery_batch_size_line_id where r.receipt_line_id=%s',(line,)).fetchall())
    b.chain.laundry_action(cur,'POST_FINAL_SKU',dict(cutting_group_id=fx['group'],destination_location_id=base.LOCATION,physical_at=clock(14).isoformat(),reason='SKU free exact-size final goods',good_qty_pcs=16,completion_mode='ALL_READY',
        lines=[dict(final_product_id=p,qty_good_pcs=q,qty_bs_pcs=0,source_laundry_receipt_line_id=line,source_laundry_receipt_batch_size_line_id=rs[s]) for (p,s),q in zip(rows,qtys)]),base.group_version(cur,fx['group']))
    lots=[one(cur,"select id::text from erp.fg_lots where po_id=%s and product_id=%s and lot_origin='PRODUCTION'",fx['po'],p) for p,_ in rows]
    def costs():return [b.lot_value(cur,l) for l in lots]
    labor=[one(cur,"select erp.cp6_lot_work_cost_v2620c(%s,'LABOR')",l) for l in lots]
    laundry=[one(cur,'select amount from erp.bd_laundry_receipt_allocations_v1 where receipt_batch_size_line_id=%s',rs[s]) for s in sizes]
    physical=[one(cur,'select sum(qty_signed) from erp.fg_stock_movements where lot_id=%s',l) for l in lots]
    charges=cur.execute('select c.ref_id::text,c.rate_status,c.unit_rate,c.amount,c.price_reason,c.bf_sku_version_id::text from erp.bd_laundry_charge_lines_v1 c join erp.laundry_delivery_lines l on l.id=c.delivery_line_id where l.delivery_id=%s order by c.line_no',(delivery,)).fetchall()
    shares=cur.execute('select s.size_id::text,x.covered_qty,x.amount from erp.bd_laundry_charge_shares_v1 x join erp.bd_laundry_charge_lines_v1 c on c.id=x.charge_line_id join erp.laundry_delivery_batch_size_lines s on s.id=x.delivery_batch_size_line_id where c.ref_id=%s',(f['rates'][1]['ref_id'],)).fetchall()
    before=costs()
    for rate in f['rates']:
        b.bd(cur,'SAVE_COMPONENT_RATE',dict(component_id=rate['ref_id'],rate_status='KNOWN',rate_per_pcs='913.27',effective_from=clock(15).isoformat(),reason='Later paid vendor rate must not rewrite free shipment'))
    changed=copy.deepcopy(g['settings']);changed['price']='190000.00'
    g2=bf.group(cur,[p for p,_ in rows],clock(15),sku=g['sku'],gid=g['id'],revision=1,settings=changed);bf.save(cur,[g2],clock(15))
    prod.owner(cur);report=one(cur,'select public.erp_get_sku_hpp_v1(%s::jsonb)',json.dumps(dict(query=g['sku'])));b.api.admin(cur)
    hpp=report['groups'][0];state=b.line_state(cur,delivery)
    return b.verdict(dict(physical_sizes=physical==qtys,labor=labor==list(map(b.D,['635.95','1017.52','381.57'])),
        laundry_zero=laundry==[0,0,0] and one(cur,'select actual_cost from erp.laundry_receipt_lines where id=%s',line)==0,
        hpp_exact=before==list(map(b.D,['667.20','1067.52','400.32'])) and sum(before)==b.D('2135.04'),
        known_zero_complete=state['complete'] and b.D(state['known'])==0 and sent['estimated_cost']==0,
        no_laundry_payable=b.D(b.ap(cur,f['vendor']))==0 and b.D(b.accrual(cur,fx['po'])['desired'])==0,
        provenance=charges==[(r['ref_id'],r['rate_status'],0,0,r['reason'],None) for r in f['rates']],
        waived_only_three_middle=dict((s,(q,a)) for s,q,a in shares)=={sizes[0]:(0,0),sizes[1]:(3,0),sizes[2]:(0,0)},
        shipment_replay=again['replayed'] and again['delivery_id']==delivery,
        later_paid_master_keeps_old_costs=costs()==before,
        weighted_hpp=hpp['qty']=='16' and b.D(hpp['value'])==b.D('2135.04') and b.D(hpp['hpp_per_pcs'])==b.D('133.44')),
        labor=list(map(str,labor)),laundry=list(map(str,laundry)),costs=list(map(str,before)),charges=charges,shares=shares,
        oracle=dict(fabric='100.00',labor='2035.04',laundry='0.00',total='2135.04'))
