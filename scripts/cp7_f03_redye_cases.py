"""X04 paid-redye source versions through the installed CP7 stock/report stack.

Amounts come from the fixed four-piece vendor worksheet: rate50 is cost200;
one piece sold and an invoice240 add FG30/COGS10, without another movement.
Current commercial grouping and later vendor tariffs cannot reprice that source.
"""
import copy
import json
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import cp6_be_probe as be
import cp6_bf_probe as bf
import cp6_bf_combined_probe as combined
import cp7_f03_x04_cases as x04

b, chain = be.bdp, be.chain


def fixture(cur, today, known=False):
    # Use the already qualified same-day source clock. A new SKU master cannot
    # be backdated to the old AV fixture's work day. All price/version guards
    # remain in force; the target group precedes its first actual conversion.
    f = combined.fixture(cur,today,True)
    washed=combined.wash(cur,f,range(4),11)
    combined.finish(cur,f,[washed],range(4),13,bs={3:4})
    bs=b.one(cur,"select id::text from erp.bs_cases where po_id=%s and product_id=%s and status='OPEN'",f['po'],f['roots'][3])
    chain.bs_action(cur,'CLASSIFY_BS',dict(bs_case_id=bs,cause_source='UNKNOWN',
        components=[dict(work_component_id=combined.prod.COMPONENT,completed_before_bs_qty=4)],
        change_reason='X04 original sewing earned before the paid redye'),chain.version(cur,'bs_cases',bs))
    f.update(bs=bs,product=f['roots'][3])
    b.api.admin(cur)
    process = b.one(cur, """insert into erp.wash_processes(process_code,process_name)
        values(%s,'X04 real paid redye') returning id::text""", 'X04-'+uuid.uuid4().hex[:10])
    identity = 'X04-DYE-'+uuid.uuid4().hex[:8]
    target = b.sized_product(cur, f['size_ids'][3], identity)
    anchor = bf.products(cur, ('A',), tag=identity)[0][0]
    identities = cur.execute('select brand_id,model_id,color_name from erp.products where id=any(%s::uuid[])',([target,anchor],)).fetchall()
    assert len(identities)==2 and identities[0]==identities[1], 'X04_TARGET_GROUP_PHYSICAL_IDENTITY'
    start = f['when'](13,15)
    initial = bf.group(cur, [target], start, settings=dict(price='185000.00',
        bom=None, work_rates=[], laundry_rates=[]))
    successor = bf.group(cur, [anchor], start, settings=dict(price='999999.00',
        bom=None, work_rates=[], laundry_rates=[]))
    saved = bf.save(cur, [initial, successor], start)
    if known:
        b.process_rate(cur, dict(vendor=chain.base.VENDOR,process=process,start=start), '50.00')
    b.api.admin(cur)
    # Rework reviews the PO commitment at the actual service time, rather than
    # an arbitrary active master row which can predate the BF shared recipe.
    bom = b.one(cur, 'select erp.resolve_rework_accessory_bom_v1(%s,%s)::text', f['bs'], f['when'](14))
    assert bom is not None, 'X04_EFFECTIVE_REWORK_BOM_REQUIRED'
    number = 'X04-DYE-'+uuid.uuid4().hex[:12]
    order = dict(rework_number=number,bs_case_id=str(f['bs']),destination_type='LAUNDRY',
        contractor_id=None,vendor_id=chain.base.VENDOR,qty_sent=4,
        physical_sent_at=b.iso(f['when'](14)),status='IN_PROGRESS',
        return_fg_location_id=chain.base.LOCATION,accessory_bom_version_id=bom,
        accessory_bom_item_ids=[],components=[])
    made = be.be(cur,'SAVE_REDYE',dict(order=order,target_product_id=target,
        wash_process_id=process,price_status='KNOWN' if known else 'UNKNOWN',
        reason='X04 actual paid service has its original economic source'))
    rid = made['rework_id']
    chain.bs_action(cur,'COMPLETE_REWORK',dict(rework_order_id=rid,qty_good=4,qty_bs=0,
        completed_at=b.iso(f['when'](16)),return_fg_location_id=chain.base.LOCATION,
        change_reason='X04 four pieces actually returned'),chain.version(cur,'rework_orders',rid))
    dest = b.one(cur,"""select a.destination_lot_id::text from erp.be_conversion_sources_v1 s
        join erp.product_conversion_allocations a on a.conversion_id=s.conversion_id
        where s.rework_id=%s""",rid)
    po = b.one(cur,'select po_id::text from erp.bs_cases where id=%s',f['bs'])
    return dict(f,redye=rid,target=target,dest=dest,po=po,process=process,
        vendor=chain.base.VENDOR,location=chain.base.LOCATION,number=number,
        initial_group=initial,successor_group=successor,initial_save=saved,
        anchor=anchor,today=str(today),known=known,
        target_sku=b.one(cur,'select sku from erp.products where id=%s',target))


def position(f):
    return dict(product=f['target'],lot=f['dest'],location=f['location'],sku=f['target_sku'])


def physical_card(card):
    # The reader explicitly restates valuation from current information. A
    # lawful late price may change that projection, never the movement facts.
    return x04.canonical_card([{k:v for k,v in row.items() if k!='valuation'}
        for row in card['page']['rows']])


def observe(cur, f):
    p=position(f)
    card=x04.fg.ledger(cur,p,limit=100)
    ws=x04.fg.workspace(cur,p,show_zero=True,limit=100)
    row=next(r for r in ws['page']['rows'] if r['lot_id']==f['dest'] and r['location_id']==f['location'] and r['quality_grade']=='GRADE_A')
    report=x04.finance.read(cur,f['today'],**{'from':str(f['day'])})
    service=b.one(cur,'select to_jsonb(s) from erp.be_redye_services_v1 s where id=%s',f['redye'])
    for key in ('sent_at','created_at'):
        service[key]=datetime.fromisoformat(service[key]).astimezone(timezone.utc).isoformat(timespec='microseconds')
    return dict(card=card,row=row,report=report,service=service,
        rate=b.one(cur,'select erp.be_redye_rate_v1(%s)',f['redye']),
        cost=b.one(cur,'select erp.be_redye_cost_v1(%s)',f['redye']),
        pending=b.one(cur,'select erp.bd_lot_laundry_unknown_v1(%s)',f['dest']),
        value=b.lot_value(cur,f['dest']),qty=be.qty(cur,f['dest']),
        accounts={k:b.gl(cur,k) for k in ('WIP','FG_INVENTORY','COGS')},
        price_event_count=b.one(cur,'select count(*) from erp.be_redye_price_events_v1 where service_id=%s',f['redye']))


def regroup(cur, f):
    before=observe(cur,f)
    at=b.one(cur,'select clock_timestamp()')
    a=bf.group(cur,[f['target']],at,sku=f['initial_group']['sku'],gid=f['initial_group']['id'],revision=1,
        settings=copy.deepcopy(f['initial_group']['settings']))
    a.update(members=[],legacy_basis=[])
    z=bf.group(cur,[f['anchor'],f['target']],at,sku=f['successor_group']['sku'],
        gid=f['successor_group']['id'],revision=1,settings=copy.deepcopy(f['successor_group']['settings']))
    bf.save(cur,[a,z],at)
    # Later vendor tariff99 is legal but belongs to later service attempts.
    b.process_rate(cur,dict(vendor=f['vendor'],process=f['process'],start=at),'99.00')
    after=observe(cur,f)
    assert after['service']==before['service']
    assert after['rate']==before['rate'] and after['cost']==before['cost']
    assert after['value']==before['value'] and after['qty']==before['qty']
    assert after['accounts']==before['accounts']
    assert x04.canonical_card(after['card']['page']['rows'])==x04.canonical_card(before['card']['page']['rows'])
    assert after['card']['position']['commercial_sku']==f['successor_group']['sku']
    assert after['card']['page']['rows'] and all(r['commercial_sku_at_transaction']==f['initial_group']['sku'] for r in after['card']['page']['rows'])
    return after


def assert_first_price(cur, f, before):
    after=observe(cur,f)
    assert before['rate'] is None and before['pending'] and before['row']['valuation']['state']=='UNKNOWN'
    assert after['rate']==50 and after['cost']==200 and after['price_event_count']==1
    assert after['value']-D(str(before['value']))==200 and after['qty']==before['qty']==4
    assert after['accounts']['FG_INVENTORY']-D(str(before['accounts']['FG_INVENTORY']))==200
    assert after['accounts']['WIP']==D(str(before['accounts']['WIP']))
    assert after['accounts']['COGS']==D(str(before['accounts']['COGS']))
    assert physical_card(after['card'])==physical_card(before['card'])
    # Redye pending is cleared; other source costs may still be estimated.
    assert b.one(cur,"""select count(*) from erp.period_blockers_v1(%s,%s)
        where code='BE_REDYE_PRICE_UNKNOWN'""",f['day'],f['day'])==0
    old=after['report']['snapshot'];prior=before['report']['snapshot']
    assert D(old['financial_position']['fg_inventory'])-D(prior['financial_position']['fg_inventory'])==200
    assert old['performance']['cogs_gl']==prior['performance']['cogs_gl']
    assert after['service']==before['service']
    return after


def unknown(cur,today):
    f=fixture(cur,today)
    before=regroup(cur,f)
    key=str(uuid.uuid4());payload=dict(service_id=f['redye'],rate='50.00',reason='X04 first known vendor service price after regroup')
    first=be.be(cur,'SET_REDYE_PRICE',payload,key)
    again=be.be(cur,'SET_REDYE_PRICE',payload,key)
    assert first==again
    after=assert_first_price(cur,f,before)
    refused=b.refused(cur,lambda:be.be(cur,'SET_REDYE_PRICE',dict(payload,rate='60.00')),'BE_PRICE_ALREADY_KNOWN')
    assert refused['ok'],refused
    final=observe(cur,f)
    assert final['value']==after['value'] and final['cost']==200 and final['price_event_count']==1
    return dict(status='PASS',original_group=f['initial_group']['sku'],current_group=f['successor_group']['sku'],
        quantity=4,vendor_first_rate='50.00',redye_cost='200.00',future_vendor_rate='99.00',
        UNKNOWN_never_inferred_from_current_group=True,original_service_fact_immutable=True,
        exact_replay=True,known_overwrite_refusal=refused,report_FG_delta='200.00',
        source_groups_in_old_movements_preserved=True,whole_HPP_final_claim=False)


def invoice_inverse(cur,today):
    f=fixture(cur,today,True)
    sale=combined.sale(cur,dict(f,roots=[f['target']]),0,1,17)
    allocation=cur.execute('select to_jsonb(a) from erp.sale_stock_allocations a where sale_item_id in(select id from erp.sales_items where sale_id=%s)',(sale,)).fetchall()
    before=regroup(cur,f)
    assert before['rate']==50 and before['cost']==200 and before['qty']==3
    b.invoice_policies(cur,after='CORRECTION_DOCUMENT')
    ap=b.D(b.ap(cur,f['vendor']))
    draft=b.bd(cur,'SAVE_INVOICE_DRAFT',dict(vendor_id=f['vendor'],invoice_number='X04-INV-'+uuid.uuid4().hex[:10],
        invoice_date=str(f['day']),header_total='240.00',lines=[dict(line_kind='BILL',
        rework_service_id=f['redye'],category='GOOD',qty=4,amount='240.00')]))
    posted=b.post_draft(cur,draft)
    after=observe(cur,f)
    assert after['cost']==240 and after['value']-before['value']==40
    assert after['accounts']['FG_INVENTORY']-before['accounts']['FG_INVENTORY']==30
    assert after['accounts']['COGS']-before['accounts']['COGS']==10
    assert after['accounts']['WIP']==before['accounts']['WIP'] and after['qty']==3
    assert b.D(b.ap(cur,f['vendor']))-ap==240
    assert D(after['report']['snapshot']['financial_position']['fg_inventory'])-D(before['report']['snapshot']['financial_position']['fg_inventory'])==30
    assert D(after['report']['snapshot']['performance']['cogs_gl'])-D(before['report']['snapshot']['performance']['cogs_gl'])==10
    assert after['service']==before['service']
    assert physical_card(after['card'])==physical_card(before['card'])
    b.bd(cur,'REVERSE_INVOICE',dict(invoice_id=posted['invoice_id'],expected_version=posted['row_version'],
        reason='X04 invoice inverse retains original source tariff and allocation'))
    inverse=observe(cur,f)
    assert inverse['cost']==200 and inverse['value']==before['value'] and inverse['qty']==3
    assert inverse['accounts']==before['accounts'] and b.D(b.ap(cur,f['vendor']))==ap
    assert inverse['service']==before['service'] and inverse['rate']==50
    assert physical_card(inverse['card'])==physical_card(before['card'])
    assert allocation==cur.execute('select to_jsonb(a) from erp.sale_stock_allocations a where sale_item_id in(select id from erp.sales_items where sale_id=%s)',(sale,)).fetchall()
    for key in ['financial_position','performance']:
        assert inverse['report']['snapshot'][key]==before['report']['snapshot'][key]
    return dict(status='PASS',original_vendor_rate='50.00',future_vendor_rate='99.00',
        estimated_redye_cost='200.00',invoice='240.00',sold_quantity=1,stock_quantity=3,
        invoice_FG_delta='30.00',invoice_COGS_delta='10.00',invoice_AP_delta='240.00',
        original_allocation_immutable=True,invoice_inverse_exact=True,
        grouping_never_reprices_original_service=True)


def cases(cur,today):
    return [('F03_X04_REDYE_UNKNOWN_GROUP_FIRST_PRICE',lambda:x04.continuation(cur,today,unknown)),
        ('F03_X04_REDYE_GROUP_INVOICE_SOLD_INVERSE',lambda:x04.continuation(cur,today,invoice_inverse))]


def http_cases(http,today):
    def price():
        with http.connect() as conn,conn.cursor() as cur:
            had=b.one(cur,"select has_schema_privilege('authenticated','erp','USAGE')")
            acl=b.one(cur,"select nspacl::text from pg_namespace where nspname='erp'")
            if not had:cur.execute('grant usage on schema erp to authenticated')
            f=fixture(cur,today);before=regroup(cur,f)
            b.api.admin(cur)
            if not had:cur.execute('revoke usage on schema erp from authenticated')
            assert b.one(cur,"select nspacl::text from pg_namespace where nspname='erp'")==acl
            conn.commit()
        owner=http.login('OWNER','x04-redye-owner');warehouse=http.login('GUDANG','x04-redye-warehouse')
        args=dict(p_action='SET_REDYE_PRICE',p_payload=dict(service_id=f['redye'],rate='50.00',
            reason='X04 real authenticated vendor price after commercial regroup'),p_client_request_id=str(uuid.uuid4()))
        assert http.anon_rpc('erp_save_product_conversion_action_v1',args)['status'] in (401,403)
        denied=warehouse.rpc('erp_save_product_conversion_action_v1',args);assert denied['status']>=400,denied
        with http.connect() as conn,conn.cursor() as cur:
            untouched=observe(cur,f);assert untouched['rate'] is None and untouched['accounts']==before['accounts'];conn.rollback()
        done=owner.rpc('erp_save_product_conversion_action_v1',args)
        again=owner.rpc('erp_save_product_conversion_action_v1',args)
        assert done['status']==200 and done==again,(done,again)
        with http.connect() as conn,conn.cursor() as cur:
            after=assert_first_price(cur,f,before);conn.rollback()
        card=owner.rpc('erp_cp7_get_fg_ledger_v1',dict(p_query=dict(product_id=f['target'],lot_id=f['dest'],
            location_id=f['location'],quality_grade='GRADE_A',limit=100)))
        assert card['status']==200 and x04.canonical_card(card['body']['page'])==x04.canonical_card(after['card']['page']),card
        report=owner.rpc('erp_cp7_get_finance_report_v1',dict(p_query=x04.finance.query(today,**{'from':str(f['day'])})))
        assert report['status']==200,report
        for key in ['financial_position','performance']:assert report['body']['snapshot'][key]==after['report']['snapshot'][key]
        return dict(status='PASS',real_Auth_HTTP=True,warehouse_write_refused_before_effect=True,
            owner_first_price_exact_replay=True,stock4_FG_value_delta200=True,
            public_CP7_cards_and_finance_agree=True,no_fixture_ERP_schema_grant_during_HTTP=True)
    return [('F03_X04_REDYE_HTTP_AUTH_SOURCE_PRICE_AND_CP7',price)]
