"""Writer regressions for audit 507931d of 08065a3. Oracles precede execution.
Synthetic disposable fixtures only. This evidence cannot close independent findings.
The factory keeps the existing T1/T2 harness module and rollback boundaries intact.
"""
import uuid
from decimal import Decimal as D


def coverage(b, cur, today, unknown=False):
    if not b.bd_installed(cur): return b.no_route(cur, lambda: b.route_call(cur))
    fx=b.two_size_fixture(cur,today,'REV-COVERAGE',7,6);base=b.chain.base
    wash=b.component(cur,fx,'WASH','4321.09')
    finish=b.component(cur,fx,'FINISH',None if unknown else '678.91',status='UNKNOWN' if unknown else 'KNOWN')
    b.terms(cur,fx,'COMPONENTS')
    payload=b.delivery_payload(fx,7)
    payload['lines'].append(dict(size_id=fx['size2'],qty_sent_pcs=6))
    pricing=dict(components=[dict(component_id=wash,covered_qty=13),dict(component_id=finish,covered_qty=5,
        coverage=[dict(size_id=fx['size2'],qty=5)])])
    ambiguous=b.refused(cur,lambda:b.compute(cur,payload,dict(components=[dict(component_id=finish,covered_qty=5)])),'BD_COVERAGE_REQUIRED')
    foreign=b.refused(cur,lambda:b.compute(cur,payload,dict(components=[dict(component_id=finish,covered_qty=5,
        coverage=[dict(size_id=str(uuid.uuid4()),qty=5)])])),'BD_COVERAGE_INVALID')
    sent=b.bd(cur,'POST_PRICED_DELIVERY',dict(delivery=payload,pricing=pricing,expected_version=str(base.group_version(cur,fx['group']))))
    delivery=sent['delivery_id']
    response_exact=sent['estimated_cost'] is None if unknown else D(str(sent['estimated_cost']))==D('59568.72')
    sizes=dict(b.q(cur,"select s.size_id::text,s.id::text from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines l on l.id=s.delivery_line_id where l.delivery_id=%s",delivery))
    # A first partial receipt of both sizes followed by their remainders.
    receipts=[]
    for hour,quantities in [(12,[(base.SIZE,3),(fx['size2'],2)]),(13,[(base.SIZE,4),(fx['size2'],4)])]:
        rec=b.chain.laundry_action(cur,'POST_RECEIPT',dict(delivery_id=delivery,wash_process_id=fx['process'],
            physical_at=b.iso(b.chain.production.at(fx['day'],hour)),reason='Audit revision partial return',
            lines=[dict(delivery_batch_size_line_id=sizes[s],qty_good_received=n,qty_bs_laundry=0,bs_product_id=None) for s,n in quantities]),base.delivery_version(cur,delivery))
        receipts.append(rec['receipt_id'])
    initial=b.q(cur,"select s.size_id::text,e.known_amount,e.complete from erp.bd_laundry_size_estimates_v1 e join erp.laundry_delivery_batch_size_lines s on s.id=e.delivery_batch_size_line_id where s.id=any(%s::uuid[])",list(sizes.values()))
    unrelated_complete=next(r for r in initial if r[0]==base.SIZE)[2] is True
    if unknown:
        charge=b.one(cur,"select c.id::text from erp.bd_laundry_charge_lines_v1 c join erp.laundry_delivery_lines l on l.id=c.delivery_line_id where l.delivery_id=%s and c.ref_id=%s",delivery,finish)
        b.bd(cur,'SET_CHARGE_PRICE',dict(charge_line_id=charge,rate_per_pcs='678.91',reason='Audited finish price confirmed'))
    # Changing the master must not reprice either stored delivery or earlier receipts.
    b.bd(cur,'SAVE_COMPONENT_RATE',dict(component_id=finish,rate_status='KNOWN',rate_per_pcs='9000.17',
        effective_from=b.iso(b.chain.production.at(fx['day'],14)),reason='Later master price, old snapshot frozen'))
    charges=b.q(cur,"select s.size_id::text,sh.covered_qty,sh.amount from erp.bd_laundry_charge_shares_v1 sh join erp.bd_laundry_charge_lines_v1 c on c.id=sh.charge_line_id join erp.laundry_delivery_batch_size_lines s on s.id=sh.delivery_batch_size_line_id where c.ref_id=%s",finish)
    allocated=dict(b.q(cur,"select s.size_id::text,sum(a.amount) from erp.bd_laundry_receipt_allocations_v1 a join erp.laundry_delivery_batch_size_lines s on s.id=a.delivery_batch_size_line_id where s.id=any(%s::uuid[]) group by s.size_id",list(sizes.values())))
    products={s:b.sized_product(cur,s,'REVC-'+uuid.uuid4().hex[:8]) for s in sizes}
    lines=b.q(cur,"select d.size_id::text,r.id::text,r.receipt_line_id::text,r.qty_good_received from erp.laundry_receipt_batch_size_lines r join erp.laundry_delivery_batch_size_lines d on d.id=r.delivery_batch_size_line_id where d.id=any(%s::uuid[])",list(sizes.values()))
    b.chain.laundry_action(cur,'POST_FINAL_SKU',dict(cutting_group_id=fx['group'],destination_location_id=base.LOCATION,
        physical_at=b.iso(b.chain.production.at(fx['day'],15)),reason='Audit revision covered size lots',good_qty_pcs=13,completion_mode='ALL_READY',
        lines=[dict(final_product_id=products[s],qty_good_pcs=n,qty_bs_pcs=0,source_laundry_receipt_line_id=l,source_laundry_receipt_batch_size_line_id=r) for s,r,l,n in lines]),base.group_version(cur,fx['group']))
    lot_costs=dict(b.q(cur,"select p.size_id::text,sum(h.total_cost) from erp.fg_lots l join erp.products p on p.id=l.product_id join erp.hpp_versions h on h.lot_id=l.id and h.is_current where l.po_id=%s group by p.size_id",fx['po']))
    expected={base.SIZE:D('30247.63'),fx['size2']:D('29321.09')}
    b.bd_ws(cur,dict(vendor_id=fx['vendor']))
    return b.verdict(dict(ambiguous_refused=ambiguous['ok'],foreign_refused=foreign['ok'],response_exact=response_exact,
        unrelated_size_complete=unrelated_complete,finish_only_recipient=dict((s,(n,a)) for s,n,a in charges)=={base.SIZE:(0,D(0)),fx['size2']:(5,D('3394.55'))},
        partial_receipts_conserve=allocated==expected,
        # Fixture input is 10 units at 10 each (cp6_aa_invoice_partial_audit.estimated_receipt), fully consumed.
        # HPP uses six decimals: assert each exact lot, not equality after dividing repeating fractions by 7/6.
        lot_laundry_conserved=lot_costs=={base.SIZE:expected[base.SIZE]+(D(100)*7/13).quantize(D('0.000001')),
            fx['size2']:expected[fx['size2']]+(D(100)*6/13).quantize(D('0.000001'))},
        total_cost_conserved=sum(lot_costs.values())==D('59668.72')),
        estimates=initial,finish_shares=charges,receipt_totals=allocated,lot_costs=lot_costs,response=sent['estimated_cost'])


def free_path(b,cur,today):
    if not b.bd_installed(cur): return b.no_route(cur,lambda:b.route_call(cur))
    checks={};evidence=[]
    for status in ['FREE','WAIVED']:
        fx=b.fixture(cur,today,'REV-'+status);b.terms(cur,fx,'COMPONENTS')
        cid=b.bd(cur,'SAVE_COMPONENT',dict(vendor_id=fx['vendor'],component_code=status,component_name=status,is_active=True,reason='Audited legitimate free service'))['component_id']
        payload=dict(component_id=cid,rate_status=status,rate_per_pcs='0.00',effective_from=b.iso(fx['start']),reason='Owner agreed '+status)
        invalid=b.refused(cur,lambda:b.bd(cur,'SAVE_COMPONENT_RATE',dict(payload,rate_per_pcs='0.01')),'BD_FREE_REQUIRES_ZERO')
        missing=b.bcp.denied(cur,lambda:b.bd(cur,'SAVE_COMPONENT_RATE',dict(payload,reason='  ')),'')
        known_zero=b.refused(cur,lambda:b.bd(cur,'SAVE_COMPONENT_RATE',dict(payload,rate_status='KNOWN')),'BD_AMOUNT_INVALID')
        denied=b.bcp.denied(cur,lambda:b.bd(cur,'SAVE_COMPONENT_RATE',payload,auth=b.user(cur,'GUDANG')),'')
        b.bd(cur,'SAVE_COMPONENT_RATE',payload)
        sent=b.post_priced(cur,fx,dict(components=[dict(component_id=cid,covered_qty=10)]))
        rec=b.receive(cur,sent['delivery_id'],fx,10,13)
        _,lot=b.finish_goods(cur,fx,rec['receipt_id'],10,14)
        state=b.line_state(cur,sent['delivery_id']);cost=b.lot_value(cur,lot)
        ws=b.bd_ws(cur,dict(vendor_id=fx['vendor']));charge=ws['priced_deliveries'][0]['charges'][0]
        checks[status]=all([invalid['ok'],missing['ok'],known_zero['ok'],denied['ok'],state['complete'],D(state['known'])==0,D(state['rate'])==0,
            charge['rate_status']==status,charge['price_reason']=='Owner agreed '+status,D(charge['amount'])==0,D(b.accrual(cur,fx['po'])['booked'])==0])
        evidence.append(dict(status=status,charge=charge,lot_value=str(cost),checks=dict(nonzero=invalid,reason=missing,known_zero=known_zero,role=denied)))
    # Resolving a genuinely unknown charge to a documented waiver must clear the pending marker without adding value.
    fx=b.fixture(cur,today,'REV-UNKNOWN-WAIVED');b.terms(cur,fx,'COMPONENTS')
    cid=b.component(cur,fx,'PENDING',None,status='UNKNOWN')
    sent=b.post_priced(cur,fx,dict(components=[dict(component_id=cid,covered_qty=10)]));rec=b.receive(cur,sent['delivery_id'],fx,10,13)
    _,lot=b.finish_goods(cur,fx,rec['receipt_id'],10,14);cost=b.lot_value(cur,lot)
    ws=b.bd_ws(cur,dict(vendor_id=fx['vendor']));charge=ws['priced_deliveries'][0]['charges'][0]
    key=str(uuid.uuid4());payload=dict(charge_line_id=charge['id'],rate_status='WAIVED',rate_per_pcs='0.00',reason='Owner documented later waiver')
    first=b.bd(cur,'SET_CHARGE_PRICE',payload,key=key);again=b.bd(cur,'SET_CHARGE_PRICE',payload,key=key)
    checks['unknown_to_waived']=charge['amount'] is None and first['complete'] and D(first['total_known'])==0 and again['replayed'] and b.lot_value(cur,lot)==cost
    b.bd_ws(cur,dict(vendor_id=fx['vendor']))
    return b.verdict(checks,evidence=evidence,completion=first)


def large_money(b,cur,today):
    if not b.bd_installed(cur): return b.no_route(cur,lambda:b.route_call(cur))
    fx=b.fixture(cur,today,'REV-MONEY');b.process_rate(cur,fx,'4321.09');b.invoice_policies(cur)
    delivery=b.plain_delivery(cur,fx,10,11)
    lines=[b.receipt_line(cur,b.receive(cur,delivery,fx,5,h)['receipt_id']) for h in [12,13]]
    checks={};posted=[];total=D(0)
    for amount in ['21474836.47','21474836.48','28123456.78']:
        _,p=b.invoice(cur,fx,[dict(line=lines[0],qty=1,amount=amount)],amount)
        posted.append(p);total+=D(amount);checks[amount]=p['status']=='POSTED'
    b.policy(cur,'LAU_DEC03',dict(discount='ALLOWED',extra='ALLOWED',rounding='LAST_LINE',tax_account_id=None))
    amount=D('28123456.78')+D('21474836.48')-D('1.23')
    draft,p=b.invoice(cur,fx,[dict(line=lines[0],qty=1,amount='28123456.78'),dict(line=lines[1],qty=1,amount='21474836.48')],str(amount),discount_amount='1.23')
    total+=amount
    amounts=b.q(cur,'select amount,discount_share,net_amount from erp.bd_laundry_invoice_lines_v1 where invoice_id=%s order by line_no',draft['invoice_id'])
    checks.update(discount_exact=sum(r[1] for r in amounts)==D('1.23') and sum(r[2] for r in amounts)==amount,ap_exact=D(b.ap(cur,fx['vendor']))==total,
        balanced=all(b.one(cur,'select sum(debit-credit) from erp.journal_lines where journal_entry_id=%s',x['journal_id'])==0 for x in posted+[p]))
    return b.verdict(checks,amounts=amounts,ap=b.ap(cur,fx['vendor']),expected_ap=str(total))


def revoked_replay(b,cur,today):
    if not b.bd_installed(cur): return b.no_route(cur,lambda:b.route_call(cur))
    fx=b.fixture(cur,today,'REV-REPLAY');b.process_rate(cur,fx,'1731.29')
    line=b.receipt_line(cur,b.receive(cur,b.plain_delivery(cur,fx,10,11),fx,10,13)['receipt_id'])
    actor=b.user(cur,'ADMIN',('finance.hpp.manage','finance.hpp.view','production.laundry.view'))
    payload=dict(vendor_id=fx['vendor'],invoice_number='REV-ACCESS-'+uuid.uuid4().hex[:8],invoice_date=str(fx['day']),header_total='1731.29',
        lines=[dict(line_kind='BILL',receipt_line_id=line,category='GOOD',qty=1,amount='1731.29')])
    key=str(uuid.uuid4());first=b.bd(cur,'SAVE_INVOICE_DRAFT',payload,key=key,auth=actor)
    replay=b.bd(cur,'SAVE_INVOICE_DRAFT',payload,key=key,auth=actor)
    role=b.one(cur,'select role_id from erp.app_users where auth_user_id=%s',actor)
    cur.execute('savepoint revoke_finance')
    cur.execute("delete from erp.app_role_permissions where role_id=%s and permission_key in('finance.hpp.manage','finance.hpp.view')",(role,))
    fresh=b.bcp.denied(cur,lambda:b.bd(cur,'SAVE_INVOICE_DRAFT',payload,auth=actor),'')
    cached=b.bcp.denied(cur,lambda:b.bd(cur,'SAVE_INVOICE_DRAFT',payload,key=key,auth=actor),'')
    ws=b.bd_ws(cur,dict(vendor_id=fx['vendor']),auth=actor)
    b.api.admin(cur);cur.execute('rollback to savepoint revoke_finance');cur.execute('release savepoint revoke_finance')
    restored=b.bd(cur,'SAVE_INVOICE_DRAFT',payload,key=key,auth=actor)
    n=b.one(cur,'select count(*) from erp.bd_laundry_invoices_v1 where vendor_id=%s',fx['vendor'])
    # An inactive ERP identity also must not get its old response.
    cur.execute('savepoint deactivate_actor');cur.execute('update erp.app_users set is_active=false where auth_user_id=%s',(actor,))
    inactive=b.bcp.denied(cur,lambda:b.bd(cur,'SAVE_INVOICE_DRAFT',payload,key=key,auth=actor),'')
    b.api.admin(cur);cur.execute('rollback to savepoint deactivate_actor');cur.execute('release savepoint deactivate_actor')
    return b.verdict(dict(authorized_replay=replay.get('replayed') is True,revoke_fresh=fresh['ok'],revoke_replay=cached['ok'],inactive=inactive['ok'],
        hidden=not ws['money_visible'] and ws['invoices'] is None,restored=restored.get('replayed') is True and restored['invoice_id']==first['invoice_id'],one_effect=n==1),
        fresh=fresh,cached=cached,inactive=inactive)


def paging_fixture(b,cur,today):
    fx=b.two_size_fixture(cur,today,'REV-PAGES',201,1);b.process_rate(cur,fx,'1.00')
    delivery=b.plain_delivery(cur,fx,201,11)
    sources=[b.receipt_line(cur,b.receive(cur,delivery,fx,1,13)['receipt_id']) for _ in range(201)]
    invoices=[b.invoice(cur,fx,[dict(line=sources[0],qty=1,amount='1.00')],'1.00',post=False)[0]['invoice_id'] for _ in range(55)]
    return fx,sources,invoices


def pagination(b,cur,today):
    if not b.bd_installed(cur): return b.no_route(cur,lambda:b.route_call(cur))
    fx,sources,invoices=paging_fixture(b,cur,today)
    first=b.bd_ws(cur,dict(vendor_id=fx['vendor']));page=first['pagination']
    # This new invoice must not displace entries on the already captured continuation.
    later=b.invoice(cur,fx,[dict(line=sources[0],qty=1,amount='1.00')],'1.00',post=False)[0]['invoice_id']
    second=b.bd_ws(cur,dict(vendor_id=fx['vendor'],page_as_of=page['as_of'],invoice_after=page['invoice_next'],receipt_after=page['receipt_next']))
    all_invoices=[x['invoice_id'] for p in [first,second] for x in p['invoices']]
    all_sources=[x['receipt_line_id'] for p in [first,second] for x in p['billable_receipts']]
    wrong=b.refused(cur,lambda:b.bd_ws(cur,dict(vendor_id=fx['vendor'],page_as_of=page['as_of'],invoice_after=str(uuid.uuid4()))),'BD_PAGE_INVALID')
    return b.verdict(dict(first_limits=len(first['invoices'])==50 and len(first['billable_receipts'])==200,
        remaining=len(second['invoices'])==5 and len(second['billable_receipts'])==1,
        no_lost_or_duplicate_invoices=len(all_invoices)==55 and set(all_invoices)==set(invoices),
        no_lost_or_duplicate_sources=len(all_sources)==201 and set(all_sources)==set(sources),new_insert_excluded=later not in all_invoices,
        end=second['pagination']['invoice_next'] is None and second['pagination']['receipt_next'] is None,invalid_cursor=wrong['ok']),
        counts=[len(all_invoices),len(all_sources)],first_page=page,last_page=second['pagination'])


def revision_plan(b):
    return [(name,'NO_ROUTE',lambda c,t,f=fn:f(b,c,t)) for name,fn in [
        ('REV:X01_EXPLICIT_SIZE_COVERAGE_AND_RESPONSE',coverage),
        ('REV:X01_UNKNOWN_COMPLETION_PRESERVES_COVERAGE',lambda b,c,t:coverage(b,c,t,True)),
        ('REV:OWN02_FREE_WAIVED_LEGAL_PATH',free_path),
        ('REV:X02_MONEY_OVER_INT32',large_money),
        ('REV:X03_AUTH_BEFORE_REPLAY',revoked_replay),
        ('REV:X05_PAGES_55_INVOICES_201_SOURCES',pagination),
    ]]
