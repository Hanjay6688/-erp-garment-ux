"""The public AA production fixture, ending at five posted QC units. The caller qualifies costing before sale."""
from cp6_aa_invoice_partial_audit import admin,at,base,CONTRACTOR,MODEL,PATTERN,COMPONENT,owner,rpc
from datetime import timedelta
import uuid,json
def prepare_lot(cur, fixture):
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
    fixture.update(po=po,group=group,product=product,customer=customer,day=day,delivery=delivery_id,receipt=receipt['receipt_id'],final=final)
    admin(cur)

