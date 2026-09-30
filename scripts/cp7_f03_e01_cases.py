"""Frozen E01 worksheet, one lawful production source through cash and return.

Only masters and a PO/draft work header are administrative fixtures. Stock,
accruals, entitlements, HPP, invoices, cash and return effects use accepted
writers. No result HPP/stock inserts and no caller-supplied sale cost.
"""
from datetime import timedelta
from decimal import Decimal as D
import json
import uuid

import cp7_procurement_cases as procurement
import cp7_sales_draft_cases as drafts
import cp7_sales_return_cases as returns
import cp7_finance_cases as finance
import cp7_wip_source_cases as wip
import cp6_bd_probe as laundry

b, prod, base = laundry, laundry.chain.production, laundry.chain.base
cmd, source, payments = returns.cmd, returns.source, returns.payments


def native(cur, sql, args=()):
    prod.owner(cur)
    value = cur.execute(sql, args).fetchone()[0]
    b.api.admin(cur)
    return value


def step(name, **values):
    result = dict(checkpoint=name, **values)
    print(json.dumps(dict(label='CP7_E01_CHECKPOINT', **result), default=str), flush=True)
    return result


def physical(cur, f):
    return int(cur.execute('select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m join erp.fg_lots l on l.id=m.lot_id where l.po_id=%s', (f['po'],)).fetchone()[0])


def production(cur, today):
    """100 raw x10; consume60; sew30+30 x2; wash30+30 x2; QC20+40.

    Accessory60 is the accepted BOM_STANDARD/Mandor reimbursement path: one
    accessory per GOOD at1, owed to the contractor, not a second raw issue.
    """
    f = procurement.fixture(cur, today, qty='100', price='10', final=True)
    f['trace'] = []
    received = procurement.command(cur, 'SAVE_DRAFT', f['payload'])
    posted = procurement.post(cur, received)
    f['purchase'] = posted['purchase_id']
    f['roll'] = str(cur.execute('select r.id from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=%s', (f['purchase'],)).fetchone()[0])
    assert procurement.qty(cur, f)[0] == 100
    assert cur.execute('select erp.material_purchase_final_ap_total(%s),erp.material_purchase_grni_total(%s)', (f['purchase'], f['purchase'])).fetchone() == (D(1000), D(0))
    f['trace'].append(step('RECEIPT', raw_qty=100, raw_value=1000, supplier_ap=1000))
    day = f['day'] + timedelta(days=1)
    when = lambda hour, minute=0: prod.at(day, hour, minute)
    tag = 'E01-' + uuid.uuid4().hex[:12]
    model, contractor, po, product = [str(uuid.uuid4()) for _ in range(4)]
    cur.execute('insert into erp.product_models(id,model_code,model_name) values(%s,%s,%s)', (model, tag, tag))
    cur.execute('insert into erp.product_model_sizes(model_id,size_id,sort_order) values(%s,%s,1)', (model, base.SIZE))
    cur.execute("insert into erp.contractors(id,contractor_code,contractor_name,contractor_type,attendance_required) values(%s,%s,%s,'MANDOR',false)", (contractor, tag, tag))
    work_bom = cur.execute('insert into erp.work_bom_versions(model_id,version_no,effective_from,notes) values(%s,1,%s,%s) returning id', (model, when(0), 'E01 declared single sewing component')).fetchone()[0]
    cur.execute('insert into erp.work_bom_items(bom_version_id,work_component_id,sequence_no,default_rate) values(%s,%s,1,2)', (work_bom, prod.COMPONENT))
    cur.execute('insert into erp.contractor_work_rates(contractor_id,model_id,work_component_id,rate_per_pcs,effective_from) values(%s,%s,%s,2,%s)', (contractor, model, prod.COMPONENT, when(0)))
    cur.execute("insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from,is_active,is_portal_visible) select %s,%s,%s,brand_id,'E01 NAVY',size_id,%s,%s,%s,true,true from erp.products where id=%s", (product, tag, model, tag, product, when(0), base.BASE_PRODUCT))
    pcs = cur.execute("select unit_code from erp.uom_definitions where upper(unit_code)='PCS' and dimension='COUNT' and is_active").fetchone()[0]
    category = cur.execute('insert into erp.accessory_categories(category_code,category_name,base_uom_code,is_active) values(%s,%s,%s,true) returning id', (tag, 'E01 contractor-supplied button', pcs)).fetchone()[0]
    bom = cur.execute('insert into erp.accessory_bom_versions(product_id,version_label,effective_from,notes) values(%s,%s,%s,%s) returning id', (product, tag, when(0), 'One contractor accessory x1 per GOOD')).fetchone()[0]
    cur.execute("insert into erp.accessory_bom_items(bom_version_id,category_id,qty_per_good_fg_base,hpp_method,hpp_standard_rate,hpp_uom_code,reimbursement_rate,reimbursement_uom_code) values(%s,%s,1,'BOM_STANDARD',1,%s,1,%s)", (bom, category, pcs, pcs))
    fg_location = returns.location(cur, tag + ' FG')
    cur.execute("insert into erp.production_orders(id,po_number,model_id,contractor_id,target_qty_pcs,status,current_stage,physical_start_at,notes) values(%s,%s,%s,%s,60,'CUTTING','CUTTING',%s,%s)", (po, tag, model, contractor, when(7), 'E01 isolated sixty GOOD source'))
    f.update(po=po, model=model, contractor=contractor, product=product, sku=tag, tag=tag, raw_location=f['location'], location=fg_location, destination=fg_location, production_day=day)
    cut_p = dict(action='SAVE_DRAFT', po_id=po, pattern_id=prod.PATTERN, source_location_id=f['raw_location'], cut_at=when(8), change_reason='E01 consume sixty of hundred; forty remains at warehouse', size_slots=[dict(slot_no=1, size_id=base.SIZE, drawing_no=1)], rolls=[dict(roll_id=f['roll'], qty_issued=60, qty_consumed=60, qty_reported_remaining=0, yields=[dict(slot_no=1, qty_pcs=60)])])
    cut = prod.rpc(cur, 'public.erp_save_cutting_group_before_sewing_v2', cut_p)
    cut = prod.rpc(cur, 'public.erp_save_cutting_group_before_sewing_v2', dict(cut_p, id=cut['cutting_group_id'], action='POST'), expected_version=int(cut['row_version']))
    b.api.admin(cur)
    f['group'] = cut['cutting_group_id']
    raw = cur.execute('select sum(qty_signed),sum(qty_signed*unit_cost_snapshot) from erp.material_stock_movements where material_id=%s', (f['material'],)).fetchone()
    assert raw == (D(40), D(400)), ('E01_RAW_REMAINDER', raw)
    f['trace'].append(step('CUTTING', raw_qty=40, raw_value=400, consumed_value=600, produced_pcs=60))
    yield_id = str(cur.execute('select y.id from erp.cutting_roll_yields y join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id where r.cutting_group_id=%s', (f['group'],)).fetchone()[0])
    pick_p = dict(action='SAVE_DRAFT', cutting_group_id=f['group'], contractor_id=contractor, picked_up_at=when(9), allocation_mode='ROLL', expected_group_version=int(cut['row_version']), change_reason='E01 exact sixty pickup', batches=[dict(batch_no=1, allocations=[dict(cutting_roll_yield_id=yield_id, qty_pcs=60)])])
    pickup = prod.rpc(cur, 'public.erp_save_cutting_pickup_v1', pick_p)
    pickup = prod.rpc(cur, 'public.erp_save_cutting_pickup_v1', dict(pick_p, id=pickup['pickup_id'], action='POST'), expected_version=int(pickup['row_version']))
    b.api.admin(cur)
    f['batch'] = str(cur.execute('select id from erp.cutting_distribution_batches where pickup_id=%s', (pickup['pickup_id'],)).fetchone()[0])
    native(cur, 'select erp.ensure_po_work_component_snapshots_v2(%s,%s,%s)', (po, when(9, 30), uuid.uuid4()))
    snapshots = cur.execute('select id,work_component_id,rate_per_pcs_snapshot,source_bom_version_id,source_contractor_rate_id from erp.po_work_component_snapshots where po_id=%s', (po,)).fetchall()
    assert len(snapshots) == 1 and snapshots[0][2] == 2 and snapshots[0][3] == work_bom and snapshots[0][4] is not None, ('E01_LAWFUL_WORK_RATE', snapshots)
    completion_ids = []
    for minute in (0, 30):
        completion = str(uuid.uuid4())
        b.chain.peer.ordinary(cur)
        cur.execute("insert into erp.work_completion_events(id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by) values(%s,%s,%s,%s,%s,%s,'DRAFT',%s,%s)", (completion, 'E01-W-'+completion, po, contractor, f['group'], when(10, minute), 'Thirty sewing pieces at source tariff two', base.OPERATOR_APP))
        cur.execute('insert into erp.work_completion_lines(completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot) values(%s,%s,%s,30,30,2)', (completion, snapshots[0][0], prod.COMPONENT))
        native(cur, 'select erp.post_work_completion(%s)', (completion,))
        native(cur, 'select public.erp_record_sewing_terminal_v1(%s::jsonb,%s)', (json.dumps(dict(work_completion_id=completion, qty_pcs=30, reason='E01 physical sewing leg thirty')), uuid.uuid4()))
        completion_ids.append(completion)
    assert cur.execute("select sum(l.qty_completed),sum(l.amount_payable) from erp.work_completion_lines l join erp.work_completion_events e on e.id=l.completion_id where e.po_id=%s and e.status='POSTED'", (po,)).fetchone() == (60, D(120))
    f['trace'].append(step('SEWING', legs=[30, 30], cost=120, completion_ids=completion_ids))
    vendor, process = [str(uuid.uuid4()) for _ in range(2)]
    cur.execute('insert into erp.laundry_vendors(id,vendor_code,vendor_name) values(%s,%s,%s)', (vendor, tag, tag))
    cur.execute('insert into erp.wash_processes(id,process_code,process_name) values(%s,%s,%s)', (process, tag, 'E01 Garment'))
    wash = dict(vendor=vendor, process=process, day=day, start=when(0), batch=f['batch'], group=f['group'])
    laundry.process_rate(cur, wash, '2.00')
    receipts = []
    for n in range(2):
        delivery = laundry.post_priced(cur, wash, {}, qty=30, hour=11+n)
        receipt = laundry.receive(cur, delivery['delivery_id'], wash, 30, 13+n)
        b.api.admin(cur)
        line = laundry.receipt_line(cur, receipt['receipt_id'])
        size = str(cur.execute('select id from erp.laundry_receipt_batch_size_lines where receipt_line_id=%s', (line,)).fetchone()[0])
        receipts.append(dict(line=line, size=size, delivery=delivery['delivery_id'], receipt=receipt['receipt_id']))
    f.update(vendor=vendor, receipts=receipts)
    def qc(parts, hour):
        b.api.admin(cur)
        lines = [dict(final_product_id=product, qty_good_pcs=qty, qty_bs_pcs=0, source_laundry_receipt_line_id=receipts[i]['line'], source_laundry_receipt_batch_size_line_id=receipts[i]['size']) for i, qty in parts]
        result = b.chain.laundry_action(cur, 'POST_FINAL_SKU', dict(cutting_group_id=f['group'], destination_location_id=fg_location, physical_at=when(hour).isoformat(), reason='E01 exact partial GOOD source allocation', good_qty_pcs=sum(q for _, q in parts), completion_mode='PARTIAL_SELECTION' if hour == 15 else 'ALL_READY', lines=lines), base.group_version(cur, f['group']))
        b.api.admin(cur)
        return result
    f['qc'] = [qc([(0, 20)], 15)]
    assert physical(cur, f) == 20
    f['qc'].append(qc([(0, 10), (1, 30)], 16))
    assert physical(cur, f) == 60
    f['trace'].append(step('LAUNDRY_QC', laundry_legs=[30, 30], qc=[20, 40], fg=60))
    # Disposable worksheet: only GOOD exists and invoice equals the vendor
    # quote. Declare the accepted policy; never bypass its pending gate.
    laundry.invoice_policies(cur, billable=('GOOD',), mode='PRODUCT_COST', after='REFUSE')
    invoice, _ = laundry.invoice(cur, wash, [dict(line=r['line'], qty=30, amount='60.00') for r in receipts], '120.00')
    b.api.admin(cur)
    f['laundry_invoice'] = invoice['invoice_id']
    native(cur, 'select erp.finish_production_order(%s)', (po,))
    native(cur, 'select erp.process_cost_recalc_queue(100)')
    costs = cur.execute('select sum(s.total_hpp_cost),sum(s.total_reimbursement) from erp.fg_accessory_cost_snapshots s where s.po_id=%s', (po,)).fetchone()
    assert costs == (D(60), D(60)), ('E01_ACCESSORY_SOURCE', costs)
    hpp = native(cur, 'select to_jsonb(h) from erp.get_hpp_completeness(%s) h', (po,))
    assert D(str(hpp['current_hpp_total'])) == 900 and D(str(hpp['hpp_per_pcs'])) == 15 and hpp['qty_basis_pcs'] == 60 and hpp['pending_reason_count'] == 0, ('E01_FINAL_HPP', hpp)
    lots = cur.execute('select l.id::text,l.initial_qty_pcs,h.hpp_per_pcs,h.total_cost from erp.fg_lots l join erp.v_current_hpp h on h.lot_id=l.id where l.po_id=%s order by l.produced_at,l.id', (po,)).fetchall()
    assert sorted(q for _, q, _, _ in lots) == [10, 20, 30] and all(rate == 15 and total == qty*15 for _, qty, rate, total in lots), ('E01_LOT_COSTS', lots)
    f['lots'] = [l for l, _, _, _ in lots]
    w = wip.capture(cur, [f['group']])['result']
    assert w['status'] == 'COMPLETE' and [wip.total(w, k+'_pcs') for k in ('input', 'wip', 'fg', 'bs')] == [60, 0, 60, 0], ('E01_PHYSICAL_CONSERVATION', w)
    assert laundry.wip(cur, po) == 0 and D(laundry.ap(cur, vendor)) == 120
    f['trace'].append(step('FINAL_FG', fg=60, value=900, hpp=15, wip=0, raw=600, sewing=120, accessory=60, laundry=120, hpp_completeness=hpp))
    f['customer'] = str(base.create_customer(cur, tag))
    f['sale_at'] = (source.fg.ax.r1.now(cur)-timedelta(minutes=5)).isoformat()
    f['bank'] = str(source.bc.bank_account(cur, tag+'BANK'))
    f['bank_code'] = cur.execute('select cash_account_code from erp.cash_accounts where id=%s', (f['bank'],)).fetchone()[0]
    f['cash_coa'] = payments.bank_account(cur, f)
    f['mapping'] = {k:cmd.mapping(cur, k) for k in ('AR_CUSTOMER', 'SALES_REVENUE', 'FG_INVENTORY', 'COGS')}
    return f


def expect_delta(cur, f, before, ar, revenue, fg, cogs, cash=0):
    wanted = {f['mapping']['AR_CUSTOMER']:D(ar), f['mapping']['SALES_REVENUE']:D(-revenue), f['mapping']['FG_INVENTORY']:D(fg), f['mapping']['COGS']:D(cogs), f['cash_coa']:D(cash)}
    wanted = {k:v for k,v in wanted.items() if v != 0}
    observed = cmd.delta(before, cmd.accounts(cur))
    assert observed == wanted, ('E01_LEDGER', wanted, observed)


def journey(cur, today):
    f = production(cur, today)
    before = cmd.accounts(cur)
    report_before = finance.read(cur, today)
    created = drafts.create(cur, f, drafts.payload(f, '20', '25'))
    assert physical(cur, f) == 40 and cmd.accounts(cur) == before
    f['trace'].append(step('DRAFT_SALE', available=40, no_gl=True))
    p, version = cmd.review(cur, f)
    cmd.command(cur, 'POST', p, version)
    assert physical(cur, f) == 40
    expect_delta(cur, f, before, 500, 500, -300, 300)
    pay = payments.pay(cur, f, '200')
    assert source.read(cur, f)['detail']['financial']['open_balance'] == '300.00' and physical(cur, f) == 40
    expect_delta(cur, f, before, 300, 500, -300, 300, 200)
    f['trace'].append(step('PAYMENT', cash=200, ar=300, revenue=500, cogs=300, fg=40, fg_value=600))
    f['allocations'] = returns.read(cur, f)['page']['rows']
    assert len(f['allocations']) == 1 and f['allocations'][0]['allocated_qty'] == '20', ('E01_FIFO_FIRST_LOT', f['allocations'])
    payload, version = returns.payload(cur, f, qty='5', refund='125')
    key = uuid.uuid4()
    returned = cmd.command(cur, 'RETURN', payload, version, key)
    assert physical(cur, f) == 45
    expect_delta(cur, f, before, 175, 375, -225, 225, 200)
    boundary = b.boundary.snapshot(cur)
    assert cmd.command(cur, 'RETURN', payload, version, key) == returned and b.boundary.snapshot(cur) == boundary
    report_after = finance.read(cur, today)
    for section, name, expected in [('financial_position', 'cash', 200), ('financial_position', 'customer_ar', 175), ('financial_position', 'fg_inventory', -225), ('performance', 'sales_revenue_gl', 375), ('performance', 'cogs_gl', 225), ('performance', 'gross_profit', 150)]:
        assert finance.change(report_before, report_after, section, name) == expected, ('E01_REPORT', section, name, report_after)
    detail = source.read(cur, f)['detail']
    assert detail['financial']['net_total'] == '375.00' and detail['financial']['paid_total'] == '200.00' and detail['financial']['open_balance'] == '175.00'
    f['trace'].append(step('RETURN_AND_REPORT', fg=45, fg_value=675, cogs=225, revenue=375, ar=175, cash=200, gross_profit=150, replay_no_second_effect=True))
    return dict(status='PASS',journey='E01',execution='NATIVE_PUBLIC_CP7_COMMANDS_AND_ACCEPTED_CP6_PRODUCTION',checkpoints=f['trace'],source_ids={k:f[k] for k in ('po','purchase','group','laundry_invoice','sale')},payment=pay,returned=returned,report_confidence=report_after['snapshot']['data_confidence'],full_browser_journey=False,full_family_acceptance=False)


def cases(cur, today):
    return [('F03_E01_NATIVE_60_TO_CASH_RETURN', lambda:journey(cur, today))]


def http_cases(http, today):
    def flow():
        owner = http.login('OWNER', 'e01-owner')
        with http.connect() as conn, conn.cursor() as cur:
            # Legacy work DRAFT inserts are fixture setup only. Restore this
            # schema grant before any real Auth/HTTP call is made.
            had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
            acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
            if not had: cur.execute('grant usage on schema erp to authenticated')
            f = production(cur, today)
            b.api.admin(cur)
            if not had: cur.execute('revoke usage on schema erp from authenticated')
            assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
            before = cmd.accounts(cur)
            report_before = finance.read(cur, today)
            conn.commit()
        def send(action, payload, version=None, key=None):
            args = dict(p_action=action, p_payload=payload, p_request=str(key or uuid.uuid4()), p_expected=version)
            result = owner.rpc('erp_cp7_save_sale_v1', args)
            assert result['status'] == 200, ('E01_HTTP_COMMAND', action, result)
            return result['body'], args
        created, _ = send('CREATE', drafts.payload(f, '20', '25'))
        f['sale'] = created['sale_id']
        with http.connect() as conn, conn.cursor() as cur:
            assert physical(cur, f) == 40 and cmd.accounts(cur) == before
            payload, version = cmd.review(cur, f)
        send('POST', payload, version)
        with http.connect() as conn, conn.cursor() as cur:
            assert physical(cur, f) == 40
            expect_delta(cur, f, before, 500, 500, -300, 300)
            payload, version = payments.payment_payload(cur, f, '200')
        send('PAYMENT', payload, version)
        with http.connect() as conn, conn.cursor() as cur:
            expect_delta(cur, f, before, 300, 500, -300, 300, 200)
            f['allocations'] = returns.read(cur, f)['page']['rows']
            payload, version = returns.payload(cur, f, qty='5', refund='125')
        args = dict(p_action='RETURN', p_payload=payload, p_request=str(uuid.uuid4()), p_expected=version)
        assert http.anon_rpc('erp_cp7_save_sale_v1', args)['status'] in (401, 403)
        returned = owner.rpc('erp_cp7_save_sale_v1', args)
        assert returned['status'] == 200, returned
        replayed = owner.rpc('erp_cp7_save_sale_v1', args)
        assert replayed['status'] == 200 and replayed['body'] == returned['body']
        with http.connect() as conn, conn.cursor() as cur:
            assert physical(cur, f) == 45
            expect_delta(cur, f, before, 175, 375, -225, 225, 200)
            report_after = finance.read(cur, today)
            for section, name, expected in [('financial_position','cash',200),('financial_position','customer_ar',175),('financial_position','fg_inventory',-225),('performance','sales_revenue_gl',375),('performance','cogs_gl',225),('performance','gross_profit',150)]:
                assert finance.change(report_before, report_after, section, name) == expected
            assert returns.read(cur, f, 'RETURNS')['page']['total'] == '1'
            cur.execute('update erp.app_users set is_active=false where auth_user_id=%s', (owner.auth_user_id,))
            conn.commit()
        assert owner.rpc('erp_cp7_save_sale_v1', args)['status'] == 403
        return dict(status='PASS',journey='E01',real_Auth_HTTP_sale_create_post_payment_return=True,source_production_native_qualified=True,stock45_value675_revenue375_COGS225_AR175_cash200_gross150=True,same_request_one_return=True,current_actor_revoked_replay_denied=True,anonymous_denied=True,full_family_acceptance=False)
    return [('F03_E01_HTTP_60_TO_CASH_RETURN', flow)]
