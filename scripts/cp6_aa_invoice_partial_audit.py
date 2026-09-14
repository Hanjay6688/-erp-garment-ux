#!/usr/bin/env python3
"""Independent ordinary-owner late invoice and partial production audit.

Sixteen bounded cases, each rolled back. No installed function is patched for
testing. The expected costs are arithmetic from the physical fixture, not a
second invocation of an ERP cost calculator. This does not close other rows
of the expanded competition audit ledger.
"""
from __future__ import annotations

import hashlib
import json
import os
import traceback
import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

import cp6_z_expanded_integrity_audit as prior
import cp6_v2620aa_runtime as runtime
import cp6_v2620ab_runtime as ab_runtime


HEAD_AA = '7d824f780fa06fc16385c347759a9b96d0138e9d'
TREE_AA = '0bfda3d552a3a3c37b4563d895a9eb387f64acb4'
PHASE = os.environ.get('CP6_AB_PHASE', 'AA_AUDIT')
AUDIT_ROOT = Path('cp6-proof/independent-ab' if PHASE == 'AB_REGRESSION' else 'cp6-proof/independent-aa')
REPORT = AUDIT_ROOT / 'AA_INVOICE_PARTIAL_AUDIT.json'
base, one = prior.base, prior.one
admin, owner, zone = prior.as_admin, prior.as_owner, prior.set_zone
boundary = prior.stable_boundary
PATTERN = 'c8c10000-0000-4000-8000-000000000001'
MODEL = 'a2000000-0000-0000-0000-000000000001'
CONTRACTOR = 'a1000000-0000-0000-0000-000000000001'
COMPONENT = 'a4000000-0000-0000-0000-000000000001'
LEDGER_KEYS = ('MATERIAL_INVENTORY', 'WIP', 'FG_INVENTORY', 'COGS', 'AP_SUPPLIER', 'GRNI_MATERIAL')
REPORT_KEYS = dict(MATERIAL_INVENTORY='material_inventory', WIP='wip_inventory',
                   FG_INVENTORY='fg_inventory', AP_SUPPLIER='supplier_final_ap',
                   GRNI_MATERIAL='grni_estimated_liability')


def persist(result):
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(result, indent=2, default=str, sort_keys=True) + '\n')


def at(day, hour, minute=0):
    return datetime.combine(day, time(hour, minute), tzinfo=prior.JAKARTA)


def rpc(cur, name, payload, request_id=None, expected_version=None):
    # Only constant function names supplied by this module are interpolated.
    permitted = {
        'erp.save_material_purchase_draft_v2',
        'erp.finalize_material_purchase_invoice_v2',
        'public.erp_save_cutting_group_before_sewing_v2',
        'public.erp_save_cutting_pickup_v1',
        'erp.save_sale_draft_v2',
    }
    if name not in permitted:
        raise AssertionError('AA_AUDIT_UNKNOWN_RPC')
    owner(cur)
    return one(cur, f'select {name}(%s::jsonb,%s::uuid,%s::bigint)',
               (json.dumps(payload, default=str), request_id or uuid.uuid4(), expected_version))


def estimated_receipt(cur, today):
    admin(cur)
    zone(cur, 'Asia/Jakarta')
    material = prior.clone_material(cur, 'invoice-partial')
    purchase_day = today - timedelta(days=3)
    prior.set_open_period(cur, purchase_day - timedelta(days=1))
    location = uuid.uuid4()
    cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) "
                "values(%s,%s,'AA invoice raw warehouse','RAW_MATERIAL_WAREHOUSE',true)",
                (location, 'AA-LOC-' + location.hex[:20]))
    draft = rpc(cur, 'erp.save_material_purchase_draft_v2', {
        'purchase_number': 'AA-INV-PUR-' + str(uuid.uuid4()),
        'supplier_id': prior.BASE_SUPPLIER, 'location_id': location,
        'physical_at': at(purchase_day, 23, 30),
        'change_reason': 'AA independent estimated receipt',
        'lines': [{'material_id': material, 'qty': 10, 'unit_price': 10,
                   'price_state': 'ESTIMATED', 'price_source': 'MANUAL_ESTIMATE',
                   'rolls': [{'roll_number': 'AA-INV-ROLL-' + str(uuid.uuid4()), 'qty': 10}]}],
    })
    purchase = uuid.UUID(draft['purchase_id'])
    cur.execute('select erp.post_material_purchase_v2(%s,%s,%s,%s)',
                (purchase, uuid.uuid4(), int(draft['row_version']), 'AA ordinary estimated receipt post'))
    admin(cur)
    rows = cur.execute("""select i.id,r.id,m.id
      from erp.material_purchase_items i join erp.material_rolls r on r.purchase_item_id=i.id
      join erp.material_stock_movements m on m.source_type='MATERIAL_PURCHASE_ROLL'
        and m.source_id=r.id and m.movement_type='PURCHASE'
      where i.purchase_id=%s and m.material_id=%s and m.qty_signed=10""",
      (purchase, material)).fetchall()
    if len(rows) != 1:
        raise AssertionError('AA_ESTIMATED_RECEIPT_LINEAGE_NOT_QUALIFIED:' + str(rows))
    item, roll, movement = rows[0]
    return dict(material=material, purchase=purchase, item=item, roll=roll,
                movement=movement, location=location, purchase_day=purchase_day)


def partial_production(cur, fixture):
    """All movements arise from ordinary postings; only masters/drafts are seeded."""
    admin(cur)
    day = fixture['purchase_day'] + timedelta(days=1)
    po = uuid.uuid4()
    cur.execute("""insert into erp.production_orders(
      id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes)
      values(%s,%s,%s,10,'CUTTING','CUTTING',%s,'AA independent physical ten-piece lot')""",
      (po, 'AA-INV-PO-' + str(po), MODEL, at(day, 7)))
    product = base.create_product(cur, uuid.uuid4().hex[:16])
    customer = base.create_customer(cur, uuid.uuid4().hex[:16])
    cut_payload = dict(action='SAVE_DRAFT', po_id=po, pattern_id=PATTERN,
                       source_location_id=fixture['location'], cut_at=at(day, 8),
                       change_reason='AA independent exact ten-piece cutting',
                       size_slots=[dict(slot_no=1, size_id=base.SIZE, drawing_no=1)],
                       rolls=[dict(roll_id=fixture['roll'], qty_issued=10, qty_consumed=10,
                                   qty_reported_remaining=0, yields=[dict(slot_no=1, qty_pcs=10)])])
    cut = rpc(cur, 'public.erp_save_cutting_group_before_sewing_v2', cut_payload)
    group = uuid.UUID(cut['cutting_group_id'])
    cut = rpc(cur, 'public.erp_save_cutting_group_before_sewing_v2',
              dict(cut_payload, id=group, action='POST'), expected_version=int(cut['row_version']))
    admin(cur)
    yields = cur.execute("""select y.id from erp.cutting_roll_yields y
      join erp.cutting_group_rolls r on r.id=y.cutting_group_roll_id
      where r.cutting_group_id=%s and y.qty_pcs=10""", (group,)).fetchall()
    if len(yields) != 1:
        raise AssertionError('AA_CUTTING_TEN_PIECE_LINEAGE_NOT_QUALIFIED')
    pickup_payload = dict(action='SAVE_DRAFT', cutting_group_id=group,
                          contractor_id=CONTRACTOR, picked_up_at=at(day, 9), allocation_mode='ROLL',
                          expected_group_version=int(cut['row_version']),
                          change_reason='AA independent complete pickup allocation',
                          batches=[dict(batch_no=1, allocations=[dict(cutting_roll_yield_id=yields[0][0], qty_pcs=10)])])
    pickup = rpc(cur, 'public.erp_save_cutting_pickup_v1', pickup_payload)
    pickup = rpc(cur, 'public.erp_save_cutting_pickup_v1',
                 dict(pickup_payload, id=pickup['pickup_id'], action='POST'),
                 expected_version=int(pickup['row_version']))
    admin(cur)
    batches = cur.execute('select id from erp.cutting_distribution_batches where pickup_id=%s',
                          (pickup['pickup_id'],)).fetchall()
    if len(batches) != 1:
        raise AssertionError('AA_PICKUP_SINGLE_BATCH_NOT_QUALIFIED')
    component_snapshot, completion = uuid.uuid4(), uuid.uuid4()
    cur.execute("""insert into erp.po_work_component_snapshots(
      id,po_id,work_component_id,sequence_no,rate_per_pcs_snapshot,committed_at)
      values(%s,%s,%s,1,0,%s)""", (component_snapshot, po, COMPONENT, at(day, 9, 30)))
    cur.execute("""insert into erp.work_completion_events(
      id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by)
      values(%s,%s,%s,%s,%s,%s,'DRAFT','AA zero-rate sewing draft',%s)""",
      (completion, 'AA-INV-WC-' + str(completion), po, CONTRACTOR, group, at(day, 10), base.OPERATOR_APP))
    cur.execute("""insert into erp.work_completion_lines(
      completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot)
      values(%s,%s,%s,10,10,0)""", (completion, component_snapshot, COMPONENT))
    owner(cur)
    cur.execute('select erp.post_work_completion(%s)', (completion,))
    cur.execute('select public.erp_record_sewing_terminal_v1(%s::jsonb,%s::uuid)',
                (json.dumps(dict(work_completion_id=str(completion), qty_pcs=10,
                                 reason='AA ten-piece ordinary sewing terminal')), uuid.uuid4()))
    admin(cur)
    gv = base.group_version(cur, str(group))
    owner(cur)
    delivery = base.action(cur, 'POST_DELIVERY', {
        'distribution_batch_id': str(batches[0][0]), 'vendor_id': base.VENDOR,
        'wash_process_id': base.BASE_PROCESS, 'target_dyeing_color': 'CP6-E-NAVY',
        'physical_at': at(day, 11).isoformat(), 'reason': 'AA ordinary ten-piece laundry delivery',
        'lines': [dict(size_id=base.SIZE, qty_sent_pcs=10)],
    }, gv)
    delivery_id = delivery['delivery_id']
    admin(cur)
    size_line = base.delivery_size_line(cur, delivery_id)
    dv = base.delivery_version(cur, delivery_id)
    owner(cur)
    receipt = base.action(cur, 'POST_RECEIPT', {
        'delivery_id': delivery_id, 'wash_process_id': base.BASE_PROCESS,
        'physical_at': at(day, 12).isoformat(), 'reason': 'AA partial eight-piece laundry receipt',
        'lines': [dict(delivery_batch_size_line_id=size_line, qty_good_received=8,
                       qty_bs_laundry=0, bs_product_id=None)],
    }, dv)
    admin(cur)
    receipt_rows = cur.execute("""select s.id,s.receipt_line_id from erp.laundry_receipt_batch_size_lines s
      join erp.laundry_receipt_lines l on l.id=s.receipt_line_id where l.receipt_id=%s""",
      (receipt['receipt_id'],)).fetchall()
    if len(receipt_rows) != 1:
        raise AssertionError('AA_PARTIAL_RECEIPT_LINEAGE_NOT_QUALIFIED')
    receipt_size, receipt_line = receipt_rows[0]
    gv = base.group_version(cur, str(group))
    owner(cur)
    final = base.action(cur, 'POST_FINAL_SKU', {
        'cutting_group_id': str(group), 'destination_location_id': base.LOCATION,
        'physical_at': at(day, 13).isoformat(), 'reason': 'AA partial five-piece FG allocation',
        'good_qty_pcs': 5, 'completion_mode': 'PARTIAL_SELECTION',
        'lines': [dict(final_product_id=product, qty_good_pcs=5, qty_bs_pcs=0,
                       source_laundry_receipt_line_id=str(receipt_line),
                       source_laundry_receipt_batch_size_line_id=str(receipt_size))],
    }, gv)
    sale = rpc(cur, 'erp.save_sale_draft_v2', {
        'sale_number': 'AA-INV-SALE-' + str(uuid.uuid4()), 'customer_id': customer,
        'source_location_id': base.LOCATION, 'sale_date': at(day, 14),
        'reason': 'AA sell two of five completed pieces',
        'items': [dict(product_id=product, qty_pcs=2, unit_price_snapshot=40, discount_amount=0)],
    })
    cur.execute('select erp.post_sale_v2(%s,%s,%s)',
                (sale['sale_id'], uuid.uuid4(), int(sale['row_version'])))
    fixture.update(po=po, group=group, product=product, sale=sale['sale_id'],
                   delivery=delivery_id, receipt=receipt['receipt_id'], final=final)


def ledger(cur):
    admin(cur)
    values = dict(cur.execute("""select a.mapping_key,coalesce(sum(l.debit-l.credit),0)
      from erp.accounting_account_mappings a left join (
        erp.journal_lines l join erp.journal_entries j on j.id=l.journal_entry_id
          and j.status in('POSTED','REVERSED')) on l.account_id=a.account_id
      where a.mapping_key=any(%s) group by a.mapping_key""", (list(LEDGER_KEYS),)).fetchall())
    if set(values) != set(LEDGER_KEYS):
        raise AssertionError('AA_INVOICE_REQUIRED_LEDGER_MAPPINGS_MISSING')
    return values


def reports(cur, today):
    owner(cur)
    return {str(day): one(cur, 'select erp.get_owner_financial_snapshot_v2(%s,%s,%s)',
                         (today-timedelta(days=3), day, day))
            for day in (today-timedelta(days=1), today)}


def observe(cur, fixture, today):
    admin(cur)
    state = one(cur, """select jsonb_build_object(
      'raw_qty',m.cached_stock_qty,'raw_average',m.moving_average_cost,
      'purchase_cost',s.unit_cost_snapshot,'input_cost',s.input_unit_cost,
      'ap',erp.material_purchase_final_ap_total(%s),'grni',erp.material_purchase_grni_total(%s))
      from erp.materials m join erp.material_stock_movements s on s.id=%s where m.id=%s""",
      (fixture['purchase'], fixture['purchase'], fixture['movement'], fixture['material']))
    if state is None:
        raise AssertionError('AA_INVOICE_OBSERVATION_MISSING')
    state['ledger_delta'] = {key: value-fixture['ledger_baseline'][key] for key, value in ledger(cur).items()}
    if 'po' in fixture:
        state['production'] = one(cur, """select jsonb_build_object(
          'base_output',s.base_output_qty,'hpp_total',s.hpp_total_cost,'fg_value',s.fg_value,
          'cogs_value',s.cogs_value,'other_value',s.other_out_value,
          'fg_qty',(select coalesce(sum(m.qty_signed),0) from erp.fg_stock_movements m
            join erp.fg_lots f on f.id=m.lot_id where f.po_id=s.po_id),
          'wip_value',(select coalesce(sum(j.debit-j.credit),0) from erp.journal_lines j
            join erp.accounting_account_mappings a on a.account_id=j.account_id
            where a.mapping_key='WIP' and j.po_id=s.po_id))
          from erp.po_hpp_gl_state s where s.po_id=%s""", (fixture['po'],))
        state['custody'] = one(cur, """select jsonb_build_object(
          'sent',(select sum(qty_sent_pcs) from erp.laundry_delivery_lines where delivery_id=%s),
          'received',(select sum(s.qty_good_received) from erp.laundry_receipt_batch_size_lines s
            join erp.laundry_receipt_lines l on l.id=s.receipt_line_id where l.receipt_id=%s),
          'sold',(select sum(a.qty_pcs) from erp.sale_stock_allocations a
            join erp.sales_items i on i.id=a.sale_item_id where i.sale_id=%s))""",
          (fixture['delivery'], fixture['receipt'], fixture['sale']))
        state['queue'] = cur.execute("""select id,status,attempt_count,error_message
          from erp.cost_recalc_queue where entity_type='PO' and entity_id=%s order by queued_at,id""",
          (fixture['po'],)).fetchall()
        state['revaluation_events'] = cur.execute("""select id,effective_date,delta_amount,counterpart_mapping_key
          from erp.material_cost_revaluation_events where material_id=%s
          order by effective_date,delta_amount,counterpart_mapping_key""", (fixture['material'],)).fetchall()
        state['hpp_events'] = cur.execute("""select id,effective_date,fg_delta,cogs_delta,other_delta
          from erp.po_hpp_gl_events where po_id=%s order by effective_date,fg_delta,cogs_delta,other_delta""",
          (fixture['po'],)).fetchall()
    state['reports_by_day'] = reports(cur, today)
    current = state['reports_by_day'][str(today)]
    original = fixture['report_baseline'][str(today)]
    state['confidence'] = current['data_confidence']
    state['report_delta'] = {
        k: Decimal(str(current['financial_position'][field]))-Decimal(str(original['financial_position'][field]))
        for k, field in REPORT_KEYS.items()}
    state['report_delta']['COGS'] = Decimal(str(current['performance']['cogs_gl']))-Decimal(str(original['performance']['cogs_gl']))
    return state


def cents(value):
    return Decimal(value).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def differences(observed, unit_cost, partial, invoiced):
    unit_cost = Decimal(unit_cost)
    expected = dict(raw_qty=0 if partial else 10, raw_average=0 if partial else unit_cost,
                    purchase_cost=unit_cost, input_cost=unit_cost,
                    ap=cents(10 * unit_cost) if invoiced else 0, grni=0 if invoiced else 100)
    mismatches = {k: dict(expected=v, actual=observed.get(k)) for k, v in expected.items()
                  if observed.get(k) is None or Decimal(str(observed[k])) != Decimal(v)}
    expected_ledger = dict(MATERIAL_INVENTORY=0 if partial else cents(10 * unit_cost),
                           WIP=0, FG_INVENTORY=0, COGS=0,
                           AP_SUPPLIER=-expected['ap'], GRNI_MATERIAL=-expected['grni'])
    if partial:
        # 10 sewn, 8 received, 5 finished, 2 sold: WIP has 3 ready + 2 at laundry.
        # Ten material units at the selected cost plus laundry at 7 per piece.
        per_piece = unit_cost + 7
        hpp, fg, cogs = cents(5 * per_piece), cents(3 * per_piece), cents(2 * per_piece)
        expected_po = dict(base_output=5, hpp_total=hpp, fg_qty=3,
                           fg_value=fg, cogs_value=cogs, other_value=hpp-fg-cogs,
                           wip_value=cents(10 * per_piece)-hpp)
        expected_ledger.update(WIP=expected_po['wip_value'], FG_INVENTORY=fg, COGS=cogs)
        actual = observed.get('production') or {}
        mismatches.update({'production.' + k: dict(expected=v, actual=actual.get(k))
                           for k, v in expected_po.items()
                           if actual.get(k) is None or Decimal(str(actual[k])) != Decimal(v)})
        if observed.get('custody') != dict(sent=10, received=8, sold=2):
            mismatches['custody'] = dict(expected=dict(sent=10, received=8, sold=2), actual=observed.get('custody'))
    actual_ledger = observed.get('ledger_delta') or {}
    mismatches.update({'ledger.' + k: dict(expected=v, actual=actual_ledger.get(k))
                       for k, v in expected_ledger.items()
                       if actual_ledger.get(k) is None or Decimal(str(actual_ledger[k])) != Decimal(v)})
    actual_report = observed.get('report_delta') or {}
    expected_report = {k: -v if k in ('AP_SUPPLIER', 'GRNI_MATERIAL') else v
                       for k, v in expected_ledger.items()}
    mismatches.update({'report.' + k: dict(expected=v, actual=actual_report.get(k))
                       for k, v in expected_report.items()
                       if actual_report.get(k) is None or Decimal(str(actual_report[k])) != Decimal(v)})
    return mismatches


def invoice_case(cur, caller_zone, today, partial, final_cost):
    ledger_baseline = ledger(cur)
    report_baseline = reports(cur, today)
    fixture = estimated_receipt(cur, today)
    fixture['ledger_baseline'] = ledger_baseline
    fixture['report_baseline'] = report_baseline
    if partial:
        partial_production(cur, fixture)
    owner(cur)
    cur.execute('select erp.close_accounting_through(%s,%s)',
                (fixture['purchase_day'], 'AA close receipt day before true late invoice'))
    before = observe(cur, fixture, today)
    pre_errors = differences(before, 10, partial, False)
    if pre_errors:
        return dict(status='COUNTEREXAMPLE', severity='P1', stage='BEFORE_INVOICE',
                    ordinary_postings_completed=True, expected_physical_pieces=10 if partial else None,
                    fixture=fixture, actual=before, mismatches=pre_errors)
    admin(cur)
    version = int(one(cur, 'select row_version from erp.material_purchase_headers where id=%s',
                      (fixture['purchase'],)))
    payload = dict(purchase_id=fixture['purchase'], supplier_invoice_number='AA-FINAL-' + str(uuid.uuid4()),
                   invoice_date=fixture['purchase_day'], received_at=at(today - timedelta(days=1), 15),
                   reason='AA true late invoice at final cost ' + str(final_cost),
                   lines=[dict(purchase_item_id=fixture['item'], qty_invoiced=10, final_unit_price=final_cost)])
    request_id = uuid.uuid4()
    zone(cur, caller_zone)
    clocks = cur.execute('select transaction_timestamp(),statement_timestamp(),clock_timestamp()').fetchone()
    if any(value.astimezone(prior.JAKARTA).date() != today for value in clocks):
        raise AssertionError('AA_INVOICE_DAY_CHANGED_REQUIRES_SEPARATE_MIDNIGHT_CASE')
    before_call = boundary(cur)
    cur.execute('savepoint aa_invoice_call')
    call_error = None
    try:
        response = rpc(cur, 'erp.finalize_material_purchase_invoice_v2', payload, request_id, version)
    except psycopg.Error as exc:
        call_error = dict(sqlstate=exc.sqlstate, message=exc.diag.message_primary)
        cur.execute('rollback to savepoint aa_invoice_call')
    cur.execute('release savepoint aa_invoice_call')
    if call_error:
        admin(cur)
        return dict(status='INCOMPLETE', stage='INVOICE_REFUSAL_REQUIRES_JAKARTA_CONTROL',
                    caller_zone=caller_zone, partial=partial, final_unit_cost=final_cost,
                    fixture=fixture, before=before, invoice_call_error=call_error,
                    rejection_boundary_exact=boundary(cur) == before_call,
                    invocation_clocks=dict(zip(('transaction','statement','wall'), clocks, strict=True)))
    admin(cur)
    before_replay = boundary(cur)
    replay = rpc(cur, 'erp.finalize_material_purchase_invoice_v2', payload, request_id, version)
    admin(cur)
    replay_exact = response == replay and boundary(cur) == before_replay
    owner(cur)
    processed = one(cur, 'select erp.process_cost_recalc_queue(100)') if partial else None
    after = observe(cur, fixture, today)
    errors = differences(after, final_cost, partial, True)
    if one(cur, "select current_setting('TimeZone')") != caller_zone:
        errors['caller_zone'] = dict(expected=caller_zone, actual=one(cur, "select current_setting('TimeZone')"))
    if partial:
        # The recost delta is recognized on the current business day, independent
        # of caller timezone. Historical source and invoice dates stay explicit.
        for key in ('revaluation_events', 'hpp_events'):
            old_ids = {row[0] for row in before[key]}
            new_events = [row for row in after[key] if row[0] not in old_ids]
            if not new_events or any(row[1] != today for row in new_events):
                errors[key + '.business_day'] = dict(expected=str(today), actual=new_events)
    # Receipt/invoice economic day was closed before this correction. Every
    # new adjustment belongs to today's open business day. Yesterday's GL
    # report must retain the amounts observed immediately before the invoice.
    previous_day = str(today-timedelta(days=1))
    old_report = before['reports_by_day'][previous_day]
    new_report = after['reports_by_day'][previous_day]
    report_fields = [('financial_position', field) for field in REPORT_KEYS.values()]
    report_fields.append(('performance', 'cogs_gl'))
    for section, field in report_fields:
        expected_value = Decimal(str(old_report[section][field]))
        actual_value = Decimal(str(new_report[section][field]))
        if actual_value != expected_value:
            errors['prior_report.' + field + '.business_day'] = dict(
                day=previous_day, expected=expected_value, actual=actual_value)
    if not replay_exact:
        errors['invoice_replay'] = dict(expected='exact response and table boundary', actual='changed')
    if partial and (not after['queue'] or any(row[1] != 'DONE' for row in after['queue'])):
        errors['po_queue'] = dict(expected='all target PO entries DONE', actual=after['queue'])
    severity = ('P2' if all(k.endswith('.business_day') for k in errors) else 'P1') if errors else None
    return dict(status='COUNTEREXAMPLE' if errors else 'CONTROL_PASS', severity=severity,
                stage='AFTER_INVOICE', caller_zone=caller_zone, partial=partial, final_unit_cost=final_cost, fixture=fixture,
                invoice_response=response, replay_boundary_exact=replay_exact, processed=processed,
                invocation_clocks=dict(zip(('transaction','statement','wall'), clocks, strict=True)),
                before=before, after=after, mismatches=errors,
                silent_if_ready=bool(errors) and (after.get('confidence') or {}).get('status') == 'READY')


def run():
    params = conninfo_to_dict(os.environ.get('PGURL', ''))
    if params != dict(user='postgres', password='postgres', host='127.0.0.1', port='54322', dbname='postgres'):
        raise AssertionError('AA_INVOICE_EXACT_DISPOSABLE_ENDPOINT_REQUIRED')
    if os.environ.get('CP6_AA_INVOICE_AUDIT_CONFIRM') != 'postgres':
        raise AssertionError('AA_INVOICE_DISPOSABLE_CONFIRM_REQUIRED')
    phase, head, tree = ab_runtime.verify_audit_source()
    result = dict(format='CP6_AA_INVOICE_PARTIAL_AUDIT_V1', status='INCOMPLETE', head=head,
                  tree=tree, phase=phase, runtime_generation='AB' if phase == 'AB_REGRESSION' else 'AA',
                  audited_business_head=head if phase == 'AB_REGRESSION' else HEAD_AA,
                  audited_business_tree=tree if phase == 'AB_REGRESSION' else TREE_AA,
                  business_predecessor_head=HEAD_AA, run_id=os.environ.get('GITHUB_RUN_ID'),
                  synthetic_fixture_only=True, hosted_database_used=False, production_go=False,
                  independent_acceptance_complete=False, expected_cases=16, cases={},
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    persist(result)
    with psycopg.connect(**dict(params, user='supabase_admin')) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='UTC';set local statement_timeout='180s';set local lock_timeout='8s'")
        baseline = boundary(cur)
        result['engine'] = one(cur, 'select version()')
        if not str(one(cur, "select current_setting('server_version')")).startswith('17.6'):
            raise AssertionError('AA_INVOICE_PINNED_POSTGRES_REQUIRED')
        installed = runtime.verified_successor(cur)
        if len(installed) != 2:
            raise AssertionError('AA_INVOICE_EXACT_INSTALLED_AA_REQUIRED')
        result['installed_functions'] = list(installed.values())
        result['verified_ab_functions'] = list(ab_runtime.verify_audit_runtime(cur).values())
        usage = one(cur, "select has_schema_privilege('authenticated','erp','USAGE')")
        if not usage:
            cur.execute('grant usage on schema erp to authenticated')
        prior.actors.claims(cur, dict(sub=base.OPERATOR_AUTH, role='authenticated'))
        base.load_fixture_foundation(cur)
        today = one(cur, "select (clock_timestamp() at time zone 'Asia/Jakarta')::date")
        specs = [(partial, caller_zone, final_cost) for partial in (False, True)
                 for caller_zone in prior.ZONES for final_cost in ('20', '20.003')]
        for partial, caller_zone, final_cost in specs:
            name = ('PARTIAL_CHAIN:' if partial else 'ESTIMATED_RECEIPT:') + caller_zone + ':' + final_cost
            admin(cur)
            cur.execute('savepoint aa_invoice_case')
            before_case = boundary(cur)
            try:
                evidence = invoice_case(cur, caller_zone, today, partial, final_cost)
            except Exception as exc:
                evidence = dict(status='INCOMPLETE', error=str(exc), traceback=traceback.format_exc())
            finally:
                cur.execute('rollback to savepoint aa_invoice_case')
                admin(cur)
                cur.execute('release savepoint aa_invoice_case')
            evidence['full_boundary_restored'] = boundary(cur) == before_case
            if not evidence['full_boundary_restored']:
                evidence['status'] = 'INCOMPLETE'
            elif evidence.get('invoice_call_error') and caller_zone != 'Asia/Jakarta':
                control_name = ('PARTIAL_CHAIN:' if partial else 'ESTIMATED_RECEIPT:')+'Asia/Jakarta:'+final_cost
                control = result['cases'].get(control_name, {})
                error = evidence['invoice_call_error']
                if (control.get('status') == 'CONTROL_PASS' and evidence.get('rejection_boundary_exact')
                        and error.get('sqlstate') == 'P0001'
                        and any(token in error.get('message', '').lower() for token in ('future', 'masa depan'))):
                    evidence.update(status='COUNTEREXAMPLE', severity='P2', paired_control=control_name,
                                    stage='LAWFUL_LATE_INVOICE_REFUSED_BY_CALLER_ZONE')
            result['cases'][name] = evidence
            persist(result)
            print(json.dumps(dict(case=name, status=evidence['status'], restored=evidence['full_boundary_restored'])), flush=True)
        conn.rollback()
        result['entire_unseeded_runtime_restored'] = boundary(cur) == baseline
        result['schema_usage_restored'] = one(cur, "select has_schema_privilege('authenticated','erp','USAGE')") == usage
        conn.rollback()
    result['controls'] = sum(x['status'] == 'CONTROL_PASS' for x in result['cases'].values())
    result['counterexamples'] = sum(x['status'] == 'COUNTEREXAMPLE' for x in result['cases'].values())
    result['incomplete'] = sum(x['status'] == 'INCOMPLETE' for x in result['cases'].values())
    restored = result['entire_unseeded_runtime_restored'] and result['schema_usage_restored']
    if restored and len(result['cases']) == 16:
        result['status'] = ('FAIL_NEW_COUNTEREXAMPLE' if result['counterexamples'] else
                            'PASS_BOUNDED_AUDIT' if result['controls'] == 16 else 'INCOMPLETE')
    persist(result)
    return result


if __name__ == '__main__':
    try:
        result = run()
    except Exception as exc:
        result = json.loads(REPORT.read_text()) if REPORT.exists() else {}
        result.update(status='INCOMPLETE', error=str(exc), traceback=traceback.format_exc(), production_go=False)
        persist(result)
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}, default=str))
    raise SystemExit(0 if result['status'] == 'PASS_BOUNDED_AUDIT' else
                     1 if result['status'] == 'FAIL_NEW_COUNTEREXAMPLE' else 2)
