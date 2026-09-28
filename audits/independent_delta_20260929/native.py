"""Independent expectations on borrowed disposable setup, no product mutations."""
import copy
import json
import uuid
from datetime import timedelta
from decimal import Decimal as D
import cp6_bf_probe as bf
import cp6_bf_supplier_probe as setup

INSTALL_BF = True
b, one, bc = bf.b, bf.one, bf.b.bcp


def result(checks, **evidence):
    failed = [k for k, value in checks.items() if value is not True]
    return dict(status='FAIL' if failed else 'PASS', checks=checks, failed=failed, **evidence)


def money_state(cur, f):
    values = [D(one(cur, 'select erp.material_purchase_final_ap_total(%s)', p)) for p in f['purchases']]
    movements = cur.execute('select id::text,qty_signed,unit_cost_snapshot from erp.material_stock_movements where material_id=%s order by id', (f['material'],)).fetchall()
    return values, movements


def credit_lifecycle(cur, today, fabric=False):
    f = setup.fixture(cur, today, fabric=fabric)
    a, z, k = f['purchases']
    before, original_movements = money_state(cur, f)
    first_payload = setup.payload(cur, f, [(z, '7.13'), (k, '2.87')])
    key = str(uuid.uuid4())
    setup.call(cur, first_payload, key)
    split, split_movements = money_state(cur, f)
    setup.call(cur, setup.payload(cur, f, [(z, '3.01')]))
    replacement, _ = money_state(cur, f)
    events_before = one(cur, 'select count(*) from erp.bf_supplier_credit_moves_v1 where return_id=%s', f['ret'])
    replay = setup.call(cur, first_payload, key)
    after_replay, _ = money_state(cur, f)
    events_after = one(cur, 'select count(*) from erp.bf_supplier_credit_moves_v1 where return_id=%s', f['ret'])
    wrong = copy.deepcopy(first_payload)
    wrong['allocations'][0]['amount'] = '7.14'
    refused = b.refused(cur, lambda: setup.call(cur, wrong, key), 'CLIENT_REQUEST_ID_CONFLICT')
    setup.call(cur, setup.payload(cur, f, []))
    restored, restored_movements = money_state(cur, f)
    return result(dict(original=before == [80,100,60],
        split=split == [D('90'),D('92.87'),D('57.13')],
        replacement=replacement == [D('83.01'),D('96.99'),D('60')],
        conserved=all(sum(x)==D('240') for x in [before,split,replacement,restored]),
        physical_cost_facts_unchanged=original_movements==split_movements==restored_movements,
        old_replay_no_new_effect=replay.get('replayed') is True and after_replay==replacement and events_before==events_after,
        changed_payload_refused=refused['ok'], inverse=restored==before),
        before=list(map(str,before)),split=list(map(str,split)),replacement=list(map(str,replacement)),fabric=fabric)


def dated_credit_payment(cur,today):
    f=setup.fixture(cur,today)
    a,z,k=f['purchases']
    setup.call(cur,setup.payload(cur,f,[(z,'20.00')]))
    balances,_=money_state(cur,f)
    denied_id=bc.supplier_payment(cur,a,'90.00',f['cash'],today-timedelta(days=1))
    refusal=bc.denied(cur,lambda:bc.internal(cur,'post_supplier_payment',denied_id),'Supplier payment exceeds remaining payable')
    denied_status=one(cur,'select status from erp.supplier_payments where id=%s',denied_id)
    valid_id=bc.supplier_payment(cur,a,'70.00',f['cash'],today-timedelta(days=1))
    bc.internal(cur,'post_supplier_payment',valid_id)
    valid_status=one(cur,'select status from erp.supplier_payments where id=%s',valid_id)
    old_deltas=[one(cur,'select erp.bf_supplier_credit_delta_v1(%s,%s)',p,today-timedelta(days=1)) for p in f['purchases']]
    current_deltas=[one(cur,'select erp.bf_supplier_credit_delta_v1(%s,%s)',p,today) for p in f['purchases']]
    setup.call(cur,setup.payload(cur,f,[]))
    restored,_=money_state(cur,f)
    paid=one(cur,"select coalesce(sum(amount),0) from erp.supplier_payments where purchase_id=%s and status='POSTED'",a)
    return result(dict(current_allocation=balances==[100,80,60],
        future_credit_not_borrowed=refusal['ok'] and denied_status=='DRAFT',
        allowed_past_payment=valid_status=='POSTED' and paid==70,
        historical_delta_zero=old_deltas==[0,0,0],today_delta=current_deltas==[20,-20,0],
        inverse_outstanding=restored==[80,100,60] and restored[0]-paid==10),refusal=refusal)


def append_only(cur,today):
    f=setup.fixture(cur,today)
    setup.call(cur,setup.payload(cur,f,[(f['purchases'][1],'4.27')]))
    event=one(cur,'select id from erp.bf_supplier_credit_moves_v1 where return_id=%s',f['ret'])
    update=b.refused(cur,lambda:cur.execute('update erp.bf_supplier_credit_moves_v1 set amount=1 where id=%s',(event,)),'BF_CREDIT_APPEND_ONLY')
    delete=b.refused(cur,lambda:cur.execute('delete from erp.bf_supplier_credit_moves_v1 where id=%s',(event,)),'BF_CREDIT_APPEND_ONLY')
    amount=one(cur,'select amount from erp.bf_supplier_credit_moves_v1 where id=%s',event)
    return result(dict(update_refused=update['ok'],delete_refused=delete['ok'],original_amount=amount==D('4.27')))


def alias_boundary(cur,today,future=False):
    rows=bf.products(cur,('31','34'))
    roots=[r[0] for r in rows]
    now=one(cur,'select clock_timestamp()')
    t0=now-timedelta(minutes=4)
    t1=now+timedelta(days=1) if future else now-timedelta(minutes=1)
    a=bf.group(cur,roots[:1],t0)
    z=bf.group(cur,roots[1:],t0)
    bf.save(cur,[a,z],t0)
    old_physical=cur.execute('select id::text,identity_root_id::text,sku from erp.products where id=any(%s::uuid[]) order by id',(roots,)).fetchall()
    a2=bf.group(cur,roots,t1,sku=a['sku'],gid=a['id'],revision=1)
    z2=bf.group(cur,roots[1:],t1,sku=z['sku'],gid=z['id'],revision=1)
    z2['members']=[];z2['legacy_basis']=[]
    bf.save(cur,[a2,z2],t1)
    def label(at):return one(cur,'select erp.bf_commercial_sku_at_v1(%s,%s)',roots[1],at)
    before_label=label(t1-timedelta(microseconds=1))
    at_label=label(t1)
    current_label=label(now)
    physical=cur.execute('select id::text,identity_root_id::text,sku from erp.products where id=any(%s::uuid[]) order by id',(roots,)).fetchall()
    cardinalities=[one(cur,'select count(*) from erp.bf_sku_members_v1 m join erp.bf_sku_versions_v1 v on v.id=m.version_id where m.product_root=%s and v.effective_from<=%s and (v.effective_to is null or v.effective_to>%s)',roots[1],at,at) for at in [t0,t1-timedelta(microseconds=1),t1,now]]
    return result(dict(old_label=before_label==z['sku'],boundary_label=at_label==a['sku'],
        current_label=current_label==(z['sku'] if future else a['sku']),
        one_membership=cardinalities==[1,1,1,1],physical_unchanged=physical==old_physical),
        future=future,old=before_label,boundary=at_label,current=current_label)


def pending_snapshot(cur,today):
    f=b.fixture(cur,b.case_day(today),'DELTA-HPP-HISTORY')
    b.terms(cur,f,'COMPONENTS')
    sent=b.bd(cur,'POST_PRICED_DELIVERY',dict(delivery=b.delivery_payload(f),expected_version=str(b.chain.base.group_version(cur,f['group'])),pricing={'components':[]}))
    receipt=b.receive(cur,sent['delivery_id'],f,10,13)
    line=b.receipt_line(cur,receipt['receipt_id'])
    product,lot=b.finish_goods(cur,f,receipt['receipt_id'],10,14)
    before_at=one(cur,'select clock_timestamp()')
    def read(at):
        b.chain.production.owner(cur)
        data=one(cur,'select public.erp_get_sku_hpp_v1(%s::jsonb)',json.dumps(dict(at=at.isoformat())))
        b.api.admin(cur)
        return next(l for g in data['groups'] for l in g['lots'] if l['lot_id']==lot)
    before=read(before_at)
    _,invoice=b.invoice(cur,f,[dict(line=line,qty=10,amount='73.17')],'73.17')
    historical=read(before_at)
    current=read(one(cur,'select clock_timestamp()'))
    b.bd(cur,'REVERSE_INVOICE',dict(invoice_id=invoice['invoice_id'],expected_version=invoice['row_version'],reason='Independent snapshot inverse'))
    reversed_now=read(one(cur,'select clock_timestamp()'))
    return result(dict(before_provisional=before['provisional'] is True,
        historical_money_stable=historical['value']==before['value'] and historical['hpp_version_id']==before['hpp_version_id'],
        historical_readiness_stable=historical['provisional']==before['provisional'],
        actual_cost_arrives=D(current['value'])-D(before['value'])==D('73.17'),
        inverse_unknown=reversed_now['provisional'] is True,
        inverse_money=D(reversed_now['value'])==D(before['value'])),before=before,historical_after_invoice=historical,current=current,after_inverse=reversed_now)


def helper_acl(cur,today):
    names=['erp.bf_supplier_credit_allocate_v1(jsonb,uuid)','erp.bf_supplier_credit_source_v1(uuid,uuid)',
           'erp.bf_commercial_sku_at_v1(uuid,timestamp with time zone)','erp.bf_resolve_import_product_v1(uuid,jsonb,boolean,boolean)']
    rows=[]
    for name in names:
        for role in ['anon','authenticated']:
            rows.append([role,name,one(cur,'select has_function_privilege(%s,%s,\'EXECUTE\')',role,name)])
    return result(dict(private_helpers_unexecutable=all(not r[2] for r in rows)),privileges=rows)


def vendor_version(cur,today,status):
    f=b.fixture(cur,b.case_day(today),'DELTA-VENDOR-'+status)
    at=f['start']
    component=b.bd(cur,'SAVE_COMPONENT',dict(vendor_id=f['vendor'],component_code='D'+status,component_name='Independent '+status,is_active=True,reason='Independent version fixture'))['component_id']
    first=dict(component_id=component,rate_status=status,effective_from=at.isoformat(),reason='Explicit vendor state fixture')
    if status!='UNKNOWN':first['rate_per_pcs']='0.00'
    b.bd(cur,'SAVE_COMPONENT_RATE',first)
    later=at+timedelta(hours=1)
    b.bd(cur,'SAVE_COMPONENT_RATE',dict(component_id=component,rate_status='KNOWN',rate_per_pcs='7.13',effective_from=later.isoformat(),reason='Later paid version cannot rewrite earlier quote'))
    def read(when):return one(cur,'select erp.bf_laundry_rate_v1(%s,%s,%s,%s,%s,%s)','COMPONENT',component,f['vendor'],f['group'],b.chain.base.SIZE,when)
    old,new=read(at),read(later)
    return result(dict(old_state=old['rate_status']==status,
        old_amount=old['rate'] is None if status=='UNKNOWN' else D(old['rate'])==0,
        paid_state=new['rate_status']=='KNOWN' and D(new['rate'])==D('7.13'),
        version_separate=old['version_id']!=new['version_id'],no_sku_tariff=old['sku_version_id'] is None and new['sku_version_id'] is None),
        before=old,after=new)


def cases(cur,today):
    return [
      ('DELTA:CREDIT_ACCESSORY_DECIMAL_REPLACE_OLD_REPLAY',lambda:credit_lifecycle(cur,today)),
      ('DELTA:CREDIT_FABRIC_DECIMAL_REPLACE_OLD_REPLAY',lambda:credit_lifecycle(cur,today,True)),
      ('DELTA:CREDIT_CANNOT_FINANCE_PAST_PAYMENT',lambda:dated_credit_payment(cur,today)),
      ('DELTA:CREDIT_HISTORY_APPEND_ONLY',lambda:append_only(cur,today)),
      ('DELTA:COMMERCIAL_ALIAS_EXACT_BOUNDARY',lambda:alias_boundary(cur,today)),
      ('DELTA:COMMERCIAL_ALIAS_FUTURE_MEMBERSHIP',lambda:alias_boundary(cur,today,True)),
      ('DELTA:PENDING_HPP_HISTORICAL_READINESS',lambda:pending_snapshot(cur,today)),
      ('DELTA:NEW_HELPERS_PRIVATE',lambda:helper_acl(cur,today)),
    ]+[(f'DELTA:VENDOR_{s}_TO_PAID_HISTORY',lambda s=s:vendor_version(cur,today,s)) for s in ['FREE','WAIVED','UNKNOWN']]


def http_cases(http,today):
    def permission():
        owner=http.login('OWNER','delta-credit-owner')
        viewer=http.login('PRODUKSI_QC','delta-credit-viewer')
        args={'p_filters':{}}
        allowed=owner.rpc('erp_get_supplier_credit_v1',args)
        denied=viewer.rpc('erp_get_supplier_credit_v1',args)
        anonymous=http.anon_rpc('erp_get_supplier_credit_v1',args)
        return result(dict(owner=allowed['status']==200 and isinstance(allowed['body'],dict),
            viewer=denied['status']>=400,anon=anonymous['status']>=400),statuses=[allowed['status'],denied['status'],anonymous['status']])
    return [('DELTA_HTTP:SUPPLIER_REMINDER_SOURCE_PERMISSION',permission)]
