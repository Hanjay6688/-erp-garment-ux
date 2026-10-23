"""SS-1 (owner D17-8, D17-9): finished-goods reorder point by formula, declared cases (docs/cp7/wa/STOCK_FORMULA.json).

Every business row comes from the accepted Native commands (stock found at opname, sale draft and post, the production
chain's cutting, laundry and QC); only masters are inserted, as the other CP7 suites do. The oracle recomputes the
reorder point in Python from the fixture's own numbers (days, quantities, settings), never from the module's tables.
"""
from datetime import timedelta
from decimal import Decimal as D, ROUND_CEILING, ROUND_HALF_UP, localcontext
from fractions import Fraction as F
import json
import math
import statistics
import time
import uuid

import psycopg

import cp6_bc_probe as bc
import cp7_master_cases as master
import cp7_planning_history_cases as hist
import cp7_wip_source_cases as wsrc

sales = hist.sales
receipt = hist.receipt
auth = hist.auth
b = hist.b
Z = {'0.90': D('1.2816'), '0.95': D('1.6449'), '0.99': D('2.3263')}


def at(day, hour=10, minute=0):
    return receipt.aa.at(day, hour, minute)


def one(cur, sql, args=None):
    return cur.execute(sql, args).fetchone()[0]


# ------------------------------------------------------------------ fixture
def item(cur, today, stock, stock_day=None, effective_days=90, stock_hour=8):
    """A new SKU with stock found at stock_hour WIB (default08),40 days ago unless stock_day is explicit."""
    stock_day = stock_day or today - timedelta(days=40)
    product, _ = sales.fg.ax.owner_only_model_product(cur, effective_from=at(today - timedelta(days=effective_days), 0))
    found = sales.fg.ax.post(cur, dict(source_kind='FOUND_AT_OPNAME', product_id=product, location_id=sales.fg.base.LOCATION, qty_pcs=stock,
                                       physical_at=at(stock_day, stock_hour).isoformat(), reason='SS-1 stock found at opname',
                                       owner_unit_value='10', owner_value_reason='SS-1 explicit value'))
    b.api.admin(cur)
    customer = str(sales.fg.base.create_customer(cur, 'SS1' + uuid.uuid4().hex[:6]))
    row = cur.execute('select size_id::text,model_id::text,sku from erp.products where id=%s', (product,)).fetchone()
    return dict(product=product, size=row[0], model=row[1], sku=row[2], customer=customer, target=product + ':' + row[0],
                found=found['receipt_id'], stock=stock, stock_day=stock_day)


def sell(cur, f, day, qty, hour=10, post=True):
    """One sale of qty pieces at hour WIB of day: draft (reserves) and, by default, posted."""
    tag = 'SS1-' + uuid.uuid4().hex[:12]
    draft = b.chain.production.rpc(cur, 'erp.save_sale_draft_v2', dict(
        sale_number=tag, customer_id=f['customer'], source_location_id=sales.fg.base.LOCATION, sale_date=at(day, hour).isoformat(),
        reason='SS-1 sale', items=[dict(product_id=f['product'], qty_pcs=qty, unit_price_snapshot='20', discount_amount='0')]), uuid.uuid4(), None)
    b.api.admin(cur)
    if post:
        b.chain.production.owner(cur)
        cur.execute('select erp.post_sale_v2(%s,%s,%s)', (draft['sale_id'], uuid.uuid4(), int(draft['row_version'])))
        b.api.admin(cur)
    return draft


def sell_days(cur, f, today, pattern, window=30):
    """pattern[i] pieces sold on day today-window+i (0 = no sale that day)."""
    for i, qty in enumerate(pattern):
        if qty:
            sell(cur, f, today - timedelta(days=window - i), qty)


def profile(cur, f, lead_days=None, buffer_days=None, subject=None):
    """The item's planning profile (the owner's reviewed assumptions), saved through the accepted Native-side RPC."""
    rev = one(cur, 'select coalesce(max(revision),0) from cp7_profile.profiles where root_id=%s', (f['product'],))
    auth.actor(cur, subject)
    cfg = dict(mean_mode='OWN_AVAILABLE_HISTORY', daily_pcs=None, minimum_available_days='14',
               lead_days=None if lead_days is None else str(lead_days), review_days=None,
               buffer_days=None if buffer_days is None else str(buffer_days))
    r = cur.execute('select public.erp_cp7_save_planning_profile_v1(%s::jsonb,%s)', (json.dumps(dict(
        root_id=f['product'], product_version_id=f['product'], expected_revision=str(rev), config=cfg, reason='SS-1 lead time assumption')),
        uuid.uuid4())).fetchone()[0]
    b.api.admin(cur)
    return r


# ------------------------------------------------------------------- oracle
def oracle(stock, pattern, today, window=30, lead=None, level='0.95', buffer_days=None, extra_moves=()):
    """The reorder point from the fixture's own numbers: day d counts when it sold or started with free stock."""
    start = stock
    days = []
    for i, qty in enumerate(pattern):
        day_moves = sum(q for d, q in extra_moves if d == i)
        if qty > 0 or start > 0:
            days.append(qty)
        start = start - qty + day_moves
    total = sum(pattern)
    if total <= 0:
        return dict(basis='NO_SALES', point=None, counted=len(days))
    if len(days) < 14:
        return dict(basis='NOT_ENOUGH_DATA', point=None, counted=len(days), reason='FEWER_THAN_14_COUNTED_DAYS')
    if lead is None:
        return dict(basis='NOT_ENOUGH_DATA', point=None, counted=len(days), reason='NO_LEAD_TIME')
    mean = D(sum(days)) / D(len(days))
    sd = D(str(statistics.stdev([float(x) for x in days]))) if len(days) > 1 else D(0)
    lead = D(str(lead))
    # The point in exact fractions: the mean is sum / days, never a rounded decimal (a rounded-up mean pushed a whole
    # number of pieces up by one, E25v).
    exact_mean = F(sum(days), len(days))
    if buffer_days is not None:
        safety = mean * D(str(buffer_days))
        point = math.ceil(exact_mean * (F(str(lead)) + F(str(buffer_days))))
    else:
        safety = Z[level] * sd * lead.sqrt()
        point = math.ceil(exact_mean * F(str(lead)) + F(str(safety)))
    return dict(basis='FORMULA', point=point, counted=len(days), mean=mean, sd=sd, safety=safety)


# --------------------------------------------------------------- the module
def compute(cur):
    cur.execute('set local role cp7_capture')
    r = one(cur, "select cp7_stock_formula.compute(clock_timestamp(),interval'5 seconds')")
    cur.execute('reset role')
    return r


def evaluation(cur, f):
    return cur.execute('select to_jsonb(e) from cp7_stock_formula.evaluations e where target_key=%s', (f['target'],)).fetchone()[0]


def workspace(cur, subject=None, **query):
    auth.actor(cur, subject)
    r = one(cur, 'select public.erp_cp7_get_fg_reorder_v1(%s::jsonb)', (json.dumps(query),))
    b.api.admin(cur)
    return r


NATIVE_IDS = ['SS1_FORMULA_FROM_POSTED_SALES', 'SS1_OUT_OF_STOCK_DAYS_NOT_ZERO_DEMAND', 'SS1_LEAD_TIME_MEASURED_FROM_PRODUCTION',
              'SS1_DAYS_BUFFER_NOT_STACKED', 'SS1_SETTINGS_SERVICE_LEVEL_AND_WINDOW', 'SS1_MANUAL_POINT_REPLACES_AND_CLEARS',
              'SS1_NOT_ENOUGH_DATA_NEVER_GUESSES', 'SS1_REVERSED_SALE_NOT_DEMAND', 'SS1_IN_PRODUCTION_COUNTS_TOWARD_POSITION', 'SS1_SOURCE_AND_ACCESS',
              'SS1_VOLUME_2000_ITEMS_EVERY_MINUTE']
MATERIAL_IDS = ['SS2_FABRIC_FORMULA_FROM_CUTTING_USE', 'SS2_FABRIC_OUT_OF_STOCK_DAYS_NOT_ZERO_USE', 'SS2_FABRIC_REVERSED_ISSUE_NOT_USE',
                'SS2_FABRIC_MINIMUM_STAYS_BELOW_MINIMUM', 'SS2_FABRIC_ON_ORDER_COUNTS_TOWARD_POSITION', 'SS2_NO_LEAD_TIME_NEVER_GUESSES',
                'SS3_ACCESSORY_USAGE_SHOWN_NO_FORMULA', 'SS3_SERVICE_ZONES_NOT_FREE_STOCK', 'SS3_ACCESSORY_MANUAL_MINIMUM_ZERO_NEVER',
                'SS3_MATERIAL_SOURCE_AND_ACCESS', 'SS3_ACCESSORY_MINIMUM_FROM_OWNER_ESTIMATE']
NATIVE_IDS = NATIVE_IDS + MATERIAL_IDS
VOLUME_LIMIT_MS = 3000
PATTERN = [3, 5, 0, 4, 6, 2, 5, 3, 7, 4, 0, 5, 6, 3, 4, 5, 2, 6, 4, 3, 5, 0, 4, 6, 3, 5, 4, 2, 6, 5]
# Fabric (YD) and accessory (PCS) use per day of the 30-day window (0 = none that day).
MAT_PATTERN = [12, 0, 9, 15, 0, 7, 11, 0, 14, 8, 10, 0, 13, 6, 9, 12, 0, 10, 7, 11, 0, 9, 14, 8, 0, 12, 10, 6, 0, 11]


def produced(cur, product, cut_day, lead):
    """One production run of the chain's base model through the accepted chain: cut at 08:00 WIB of cut_day (100 pieces,
    60 of the base size), 40 of the base size washed, 30 back good and QC 15 good + 5 BS into `product` at 14:00 WIB of
    cut_day + lead days. Lead time of its lot: lead + 0.25 days."""
    wb, base = wsrc.b, wsrc.base
    f = wb.two_size_fixture(cur, cut_day + timedelta(days=2), 'SS1-' + uuid.uuid4().hex[:6], q1=60, q2=40)
    assert f['day'] == cut_day, f['day']
    wb.api.admin(cur)
    payload = dict(distribution_batch_id=f['batch'], vendor_id=f['vendor'], wash_process_id=f['process'], target_dyeing_color='SS1',
                   physical_at=f['send'].isoformat(), reason='SS-1 lead time send', lines=[dict(size_id=base.SIZE, qty_sent_pcs=40)])
    sent = wb.bd(cur, 'POST_PRICED_DELIVERY', dict(delivery=payload, expected_version=str(base.group_version(cur, f['group'])), pricing=dict(deferred=True)))
    delivery = sent['delivery_id']
    wb.api.admin(cur)
    ds = wb.one(cur, 'select s.id::text from erp.laundry_delivery_batch_size_lines s join erp.laundry_delivery_lines l on l.id=s.delivery_line_id '
                     'where l.delivery_id=%s', delivery)
    back = cut_day + timedelta(days=lead)
    rec = wb.chain.laundry_action(cur, 'POST_RECEIPT', dict(
        delivery_id=delivery, wash_process_id=f['process'], physical_at=wb.chain.production.at(back, 13).isoformat(), reason='SS-1 back from wash',
        lines=[dict(delivery_batch_size_line_id=ds, qty_good_received=30, qty_bs_laundry=0, bs_product_id=None)]), base.delivery_version(cur, delivery))
    wb.api.admin(cur)
    line = wb.receipt_line(cur, rec['receipt_id'])
    rs = wb.one(cur, 'select id::text from erp.laundry_receipt_batch_size_lines where receipt_line_id=%s', line)
    wb.chain.laundry_action(cur, 'POST_FINAL_SKU', dict(
        cutting_group_id=f['group'], destination_location_id=base.LOCATION, physical_at=wb.chain.production.at(back, 14).isoformat(),
        reason='SS-1 QC into the warehouse', good_qty_pcs=15, completion_mode='PARTIAL_SELECTION',
        lines=[dict(final_product_id=product, qty_good_pcs=15, qty_bs_pcs=5, source_laundry_receipt_line_id=line,
                    source_laundry_receipt_batch_size_line_id=rs)]), base.group_version(cur, f['group']))
    wb.api.admin(cur)
    return f


def base_item(cur, today, stock, stock_day):
    """A new SKU of the chain's base model in its base size (so production runs of that model reach it)."""
    wb, base = wsrc.b, wsrc.base
    product = wb.sized_product(cur, base.SIZE, 'SS1-' + uuid.uuid4().hex[:8])
    sales.fg.ax.post(cur, dict(source_kind='FOUND_AT_OPNAME', product_id=product, location_id=sales.fg.base.LOCATION, qty_pcs=stock,
                               physical_at=at(stock_day, 8).isoformat(), reason='SS-1 stock found at opname',
                               owner_unit_value='10', owner_value_reason='SS-1 explicit value'))
    b.api.admin(cur)
    customer = str(sales.fg.base.create_customer(cur, 'SS1' + uuid.uuid4().hex[:6]))
    row = cur.execute('select size_id::text,model_id::text,sku from erp.products where id=%s', (product,)).fetchone()
    return dict(product=product, size=row[0], model=row[1], sku=row[2], customer=customer, target=product + ':' + row[0], stock=stock)


def found(cur, f, day, qty, hour=8):
    """More stock found at opname at hour WIB of day (Native FOUND_AT_OPNAME)."""
    sales.fg.ax.post(cur, dict(source_kind='FOUND_AT_OPNAME', product_id=f['product'], location_id=sales.fg.base.LOCATION, qty_pcs=qty,
                               physical_at=at(day, hour).isoformat(), reason='SS-1 more stock found', owner_unit_value='10',
                               owner_value_reason='SS-1 explicit value'))
    b.api.admin(cur)


def as_actor(cur, subject, sql, args=None):
    """One statement as the subject (role authenticated, its claims); a failure is left to the caller's savepoint."""
    auth.actor(cur, subject)
    out = one(cur, sql, args)
    b.api.admin(cur)
    return out


def refused(cur, op):
    """(sqlstate, message) of an operation that must fail; the case goes on."""
    b.api.admin(cur)
    cur.execute('savepoint ss1_refusal')
    try:
        op()
    except psycopg.Error as e:
        cur.execute('rollback to savepoint ss1_refusal')
        b.api.admin(cur)
        return e.sqlstate, e.diag.message_primary
    cur.execute('rollback to savepoint ss1_refusal')
    b.api.admin(cur)
    raise AssertionError('SS1_EXPECTED_REFUSAL')


def staff_with(cur, *perms):
    """An active ERP user of a fixture role holding exactly these permissions."""
    b.api.admin(cur)
    role, subject = uuid.uuid4(), str(uuid.uuid4())
    cur.execute("insert into erp.app_roles(id,role_code,role_name,is_system,is_protected,is_active) values(%s,%s,%s,false,false,true)",
                (role, 'SS1_' + role.hex[:12].upper(), 'SS-1 fixture ' + role.hex))
    for key in perms:
        cur.execute('insert into erp.app_role_permissions(role_id,permission_key) values(%s,%s)', (role, key))
    cur.execute("insert into erp.app_users(id,auth_user_id,full_name,role,role_id,is_active) values(%s,%s,'SS-1 staff','STAFF',%s,true)",
                (uuid.uuid4(), subject, role))
    return subject


def save_settings(cur, subject, level, window, reason='SS-1 service level', request=None, expected=None):
    rev = expected if expected is not None else one(cur, 'select coalesce(max(revision),0) from cp7_stock_formula.settings')
    return as_actor(cur, subject, 'select public.erp_cp7_save_stock_formula_settings_v1(%s::jsonb,%s)', (json.dumps(dict(
        expected_revision=rev, service_level=level, window_days=window, reason=reason)), request or str(uuid.uuid4())))


def save_manual(cur, subject, f, qty, reason='SS-1 manual point', request=None, expected=None):
    rev = expected if expected is not None else one(cur, 'select coalesce(max(revision),0) from cp7_stock_formula.manual_points where root_id=%s',
                                                    (f['product'],))
    return as_actor(cur, subject, 'select public.erp_cp7_save_fg_reorder_manual_v1(%s::jsonb,%s)', (json.dumps(dict(
        root_id=f['product'], expected_revision=rev, reorder_point_pcs=qty, reason=reason)), request or str(uuid.uuid4())))


def _fg_source(cur, subject):
    """The source as cp7_alert calls it: role cp7_alert with the subject's claims (the owner who saved the WA settings)."""
    b.api.admin(cur)
    cur.execute("select set_config('request.jwt.claims',%s,true),set_config('request.jwt.claim.sub','',true)",
                (json.dumps(dict(sub=subject, role='authenticated')),))
    cur.execute('set local role cp7_alert')
    out = one(cur, 'select cp7_stock_formula.fg_source()')
    cur.execute('reset role')
    b.api.admin(cur)
    return out


def business(cur):
    return b.boundary.snapshot(cur)


# ------------------------------------------------------ materials (SS-2, SS-3)
def day_of(today, i, window=30):
    return today - timedelta(days=window - i)


def receive_fabric(cur, material, qty, day, location=None, hour=9):
    """qty YD of the fabric in one roll at hour WIB of day through Pembelian & Penerimaan (save draft, post), into `location`
    or a new raw-material warehouse. Returns (location, roll)."""
    tag = 'SS2-' + uuid.uuid4().hex[:12]
    b.api.admin(cur)
    if location is None:
        location = str(uuid.uuid4())
        cur.execute("insert into erp.locations(id,location_code,location_name,location_type,is_active) values(%s,%s,%s,'RAW_MATERIAL_WAREHOUSE',true)",
                    (location, tag, tag))
    d = receipt.command(cur, 'SAVE_DRAFT', dict(
        purchase_number=tag, supplier_id=str(receipt.aa.prior.BASE_SUPPLIER), location_id=location, physical_at=at(day, hour).isoformat(),
        change_reason='SS-2 fabric received', lines=[dict(material_id=material, qty=str(qty), unit_price='10', price_state='ESTIMATED',
                                                          price_source='MANUAL_ESTIMATE', rolls=[dict(roll_number=tag + '-R', qty=str(qty))])]))
    receipt.post(cur, d)
    b.api.admin(cur)
    roll = one(cur, 'select r.id::text from erp.material_rolls r join erp.material_purchase_items i on i.id=r.purchase_item_id where i.purchase_id=%s',
               (d['purchase_id'],))
    return location, roll


def fabric(cur, stock, stock_day, minimum='0'):
    """A new fabric through Master Data (Kain & Benchmark fields, its minimum included) with `stock` YD received at 09:00 WIB
    of stock_day (stock 0: none) into its own raw-material warehouse."""
    t = master.tag()
    created = master.create(cur, 'FABRIC', master.fabric_fields('SS2-' + t, name='Kain SS2 ' + t, minimum_stock_qty=str(minimum)))
    b.api.admin(cur)
    material = str(created['id'])
    receipt.aa.prior.set_open_period(cur, stock_day - timedelta(days=1))
    location, roll = receive_fabric(cur, material, stock, stock_day) if stock else (None, None)
    row = cur.execute('select material_sku,material_name from erp.materials where id=%s', (material,)).fetchone()
    return dict(material=material, location=location, roll=roll, sku=row[0], name=row[1], stock=stock)


def cut(cur, m, day, qty, remaining=0, hour=8):
    """One posted cutting (Buat Potongan, its Native writers) of qty YD from the fabric's current roll at hour WIB of day:
    qty - remaining consumed, remaining reported left over (the PO row is inserted as the chain fixtures do)."""
    p, base = wsrc.b.chain.production, wsrc.base
    b.api.admin(cur)
    po = str(uuid.uuid4())
    cur.execute("insert into erp.production_orders(id,po_number,model_id,target_qty_pcs,status,current_stage,physical_start_at,notes) "
                "values(%s,%s,%s,10,'CUTTING','CUTTING',%s,'SS-2 cutting fixture')", (po, 'SS2-PO-' + po, p.MODEL, p.at(day, hour - 1)))
    payload = dict(action='SAVE_DRAFT', po_id=po, pattern_id=p.PATTERN, source_location_id=m['location'], cut_at=p.at(day, hour),
                   change_reason='SS-2 cutting', size_slots=[dict(slot_no=1, size_id=base.SIZE, drawing_no=1)],
                   rolls=[dict(roll_id=m['roll'], qty_issued=qty, qty_consumed=qty - remaining, qty_reported_remaining=remaining,
                               yields=[dict(slot_no=1, qty_pcs=10)])])
    saved = p.rpc(cur, 'public.erp_save_cutting_group_before_sewing_v2', payload)
    saved = p.rpc(cur, 'public.erp_save_cutting_group_before_sewing_v2', dict(payload, id=saved['cutting_group_id'], action='POST'),
                  expected_version=int(saved['row_version']))
    b.api.admin(cur)
    return dict(group=saved['cutting_group_id'], po=po, roll=m['roll'])


def cut_days(cur, m, today, pattern, skip=()):
    return {i: cut(cur, m, day_of(today, i), qty) for i, qty in enumerate(pattern) if qty and i not in skip}


def return_fabric(cur, g, qty, day):
    """Fabric left from a cutting back to the warehouse (Kembalikan sisa kain, SG-02; Native post_cutting_material_returns)."""
    w = as_actor(cur, None, 'select public.erp_cp7_get_cutting_return_v1(%s)', (g['group'],))
    p = dict(group_id=w['group_id'], po_id=w['po_id'], review_token=w['review_token'], returned_at=at(day, 15).isoformat(),
             change_reason='SS-2 sisa kain kembali ke gudang', rolls=[dict(cutting_group_roll_id=w['rolls'][0]['cutting_group_roll_id'], qty_returned=str(qty))])
    return as_actor(cur, None, 'select public.erp_cp7_return_cutting_fabric_v1(%s,%s,%s)', (json.dumps(p), str(uuid.uuid4()), w['row_version']))


def reopen_cutting(cur, g):
    """A posted, unpicked cutting cancelled (Buka ulang potongan; Native inverse of its fabric issue)."""
    w = as_actor(cur, None, 'select public.erp_cp7_get_cutting_correction_v1(%s)', (g['group'],))
    p = dict(group_id=w['group_id'], po_id=w['po_id'], review_token=w['review_token'], change_reason='SS-2 potongan dibatalkan')
    return as_actor(cur, None, 'select public.erp_cp7_reopen_cutting_v1(%s,%s,%s)', (json.dumps(p), str(uuid.uuid4()), w['row_version']))


def commitment(cur, today, m, remaining):
    """ALL-P04 opening OPEN_PURCHASE_ORDER of the fabric through the unchanged import validate/finalize (as P08)."""
    import cp6_bb_probe as bb
    line = dict(po_number='PO-{C}', po_line_number='1', po_date=str(today - timedelta(days=15)), supplier_code='{C}', location_code='{C}',
                material_sku=m['sku'], ordered_qty=str(remaining), received_before_cutover_qty='0', cancelled_before_cutover_qty='0',
                remaining_qty=str(remaining), unit_price='3', expected_date=str(today + timedelta(days=5)))
    rows = {'SUPPLIER': [dict(supplier_code='{C}', supplier_name='SS-2 PO supplier', supplier_type='MATERIAL')],
            'LOCATION': [dict(location_code='{C}', location_name='SS-2 PO gudang', location_type='RAW_MATERIAL_WAREHOUSE')],
            'OPEN_PURCHASE_ORDER': [line]}
    batch, _, _ = bb.post_batch(cur, today, rows, prefix='SS2')
    b.api.admin(cur)
    return batch


def accessory(cur, today, stock, days=40):
    """An accessory (PCS) with `stock` received `days` days ago at 2.00 into a main warehouse, with the service zones, a mandor
    and a cash account (the BC fixture, its Native and facade writers)."""
    fx = bc.fixture(cur, today, stock_qty=stock, days=days)
    b.api.admin(cur)
    row = cur.execute('select material_sku,material_name from erp.materials where id=%s', (fx['material'],)).fetchone()
    return dict(fx, sku=row[0], name=row[1], stock=stock)


def accessory_days(cur, a, today, pattern):
    """pattern[i] PCS used on day i: a posted nota mandor (CONTRACTOR_ISSUE) on even days, factory use (INTERNAL_USE) on odd."""
    notes = {}
    for i, qty in enumerate(pattern):
        if not qty:
            continue
        if i % 2:
            bc.use(cur, a, a['main'], [(qty, day_of(today, i), 10, 'FACTORY_USE')])
        else:
            notes[i] = bc.note(cur, a, qty, '3.00', day_of(today, i))
        b.api.admin(cur)
    return notes


def credit_back(cur, a, item, qty, day, condition='USABLE'):
    """Part of a nota mandor returned (received, inspected) and credited: USABLE to the main warehouse, DAMAGED to the damaged
    area (ACC_DEC05 set to credit both)."""
    lot = bc.receive(cur, a, 'NOTE_RETURN', day=day, hour=9, note_item_id=item, qty=str(qty))['lot_ids'][0]
    if condition == 'USABLE':
        bc.inspect(cur, lot, bc.local_at(day, 11), 'Ani', usable=qty)
    else:
        bc.inspect(cur, lot, bc.local_at(day, 11), 'Ani', damaged=qty)
    bc.policy(cur, 'ACC_DEC05', dict(mode='CREDIT_UNPAID_ONLY', credit_conditions=['USABLE', 'DAMAGED']))
    bc.credit(cur, lot, condition, qty, bc.local_at(day, 15), a['main'] if condition == 'USABLE' else a['DAMAGED'])
    b.api.admin(cur)
    return lot


def save_material(cur, subject, material, lead=None, manual=None, reason='SS-2 lama kirim', request=None, expected=None, estimate=None):
    """estimate (D17-12, accessories): dict of moq, usage_month_qty, buffer_days; the keys are sent only when given."""
    rev = expected if expected is not None else one(cur, 'select coalesce(max(revision),0) from cp7_stock_formula.material_settings where material_id=%s',
                                                    (material,))
    payload = dict(material_id=material, expected_revision=rev, lead_days=None if lead is None else str(lead),
                   manual_point=None if manual is None else str(manual), reason=reason)
    payload.update({k: None if v is None else str(v) for k, v in (estimate or {}).items()})
    return as_actor(cur, subject, 'select public.erp_cp7_save_material_reorder_v1(%s::jsonb,%s)', (json.dumps(payload), request or str(uuid.uuid4())))


def estimate_oracle(usage_month, lead, buffer):
    """D17-12: the accessory minimum from the owner's own numbers, ceiling to 0.01, exact decimals."""
    cents = math.ceil(F(str(usage_month)) * (F(str(lead)) + F(str(buffer))) * 100 / 30)
    return (D(cents) / 100).quantize(D('0.01'))


def material_evaluation(cur, material):
    return cur.execute('select to_jsonb(e) from cp7_stock_formula.material_evaluations e where material_id=%s', (material,)).fetchone()[0]


def material_workspace(cur, subject=None, **query):
    return as_actor(cur, subject, 'select public.erp_cp7_get_material_reorder_v1(%s::jsonb)', (json.dumps(query),))


def material_source(cur, subject, kind):
    """The source as cp7_alert calls it (role cp7_alert with the owner's claims)."""
    b.api.admin(cur)
    cur.execute("select set_config('request.jwt.claims',%s,true),set_config('request.jwt.claim.sub','',true)",
                (json.dumps(dict(sub=subject, role='authenticated')),))
    cur.execute('set local role cp7_alert')
    out = one(cur, 'select cp7_stock_formula.material_source(%s)', (kind,))
    cur.execute('reset role')
    b.api.admin(cur)
    return out


def material_oracle(stock, pattern, lead, level='0.95', extra_moves=()):
    """The material reorder point from the fixture's own numbers: the finished goods' counted-day rule, the material's unit,
    ceiling to 0.01; exact decimals. pattern[i] is net use on day i; extra_moves (day, qty) are other stock changes there."""
    with localcontext() as ctx:
        ctx.prec = 40
        start, days = D(stock), []
        for i, qty in enumerate(pattern):
            qty = D(str(qty))
            if qty > 0 or start > 0:
                days.append(qty)
            start = start - qty + sum((D(str(q)) for d, q in extra_moves if d == i), D(0))
        total = sum((D(str(q)) for q in pattern), D(0))
        if total <= 0:
            return dict(basis='NO_USAGE', point=None, counted=len(days), free=start)
        if len(days) < 14:
            return dict(basis='NOT_ENOUGH_DATA', point=None, counted=len(days), reason='FEWER_THAN_14_COUNTED_DAYS', free=start)
        if lead is None:
            return dict(basis='NOT_ENOUGH_DATA', point=None, counted=len(days), reason='NO_LEAD_TIME', free=start)
        n = len(days)
        mean = sum(days, D(0)) / n
        sd = (sum(((x - mean) ** 2 for x in days), D(0)) / (n - 1)).sqrt()
        lead = D(str(lead))
        safety = Z[level] * sd * lead.sqrt()
        cents = math.ceil((F(str(sum(days, D(0)))) / n * F(str(lead)) + F(str(safety))) * 100)
        point = D(cents) / 100
        return dict(basis='FORMULA', point=point.quantize(D('0.01')), counted=n, mean=mean, sd=sd, safety=safety, free=start, usage=total)


def cases(cur, today):
    w0 = today - timedelta(days=30)

    def formula_from_sales():
        f = item(cur, today, 200)
        sell_days(cur, f, today, PATTERN)
        profile(cur, f, lead_days=7)
        before = business(cur)
        compute(cur)
        assert business(cur) == before, 'SS1_COMPUTE_WROTE_BUSINESS'
        e = evaluation(cur, f)
        o = oracle(200, PATTERN, today, lead=7)
        free = 200 - sum(PATTERN)
        assert e['basis'] == 'FORMULA' and e['point'] == o['point'] and D(str(e['free_pcs'])) == free, (e, o)
        assert e['counted_days'] == o['counted'] == 30 and e['lead_basis'] == 'PROFILE' and D(str(e['lead_days'])) == 7, e
        assert e['buffer_mode'] == 'STATISTICAL' and D(str(e['z'])) == Z['0.95'], e
        assert abs(D(str(e['daily_mean'])) - o['mean']) < D('0.0001') and abs(D(str(e['daily_sd'])) - o['sd']) < D('0.0001'), (e, o)
        assert e['state'] == ('AT_OR_BELOW' if free <= o['point'] else 'ABOVE'), e
        return dict(status='PASS', point=o['point'], free=free, counted=o['counted'], mean=str(o['mean']), sd=str(o['sd']), business_unchanged=True)

    def out_of_stock_days():
        # 40 found 40 days ago, sold out within the window, 60 more found 10 days ago (before that day's sale).
        pattern = [4, 5, 6, 5, 4, 6, 5, 5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 4, 5, 3, 6, 5, 4, 3, 5, 6, 4]
        f = item(cur, today, 40)
        found(cur, f, today - timedelta(days=10), 60)
        sell_days(cur, f, today, pattern)
        profile(cur, f, lead_days=5)
        compute(cur)
        e = evaluation(cur, f)
        o = oracle(40, pattern, today, lead=5, extra_moves=[(19, 60)])
        naive = [D(x) for x in pattern]
        naive_mean = sum(naive) / len(naive)
        naive_point = int((naive_mean * 5 + Z['0.95'] * D(str(statistics.stdev([float(x) for x in pattern]))) * D(5).sqrt())
                          .to_integral_value(rounding=ROUND_CEILING))
        assert o['counted'] == 18 and e['counted_days'] == 18 and e['point'] == o['point'] and e['basis'] == 'FORMULA', (e, o)
        assert o['point'] != naive_point, (o, naive_point)
        return dict(status='PASS', counted=18, of_days=30, point=o['point'], point_if_stockout_days_were_zero_demand=naive_point)

    def lead_time_measured():
        f = base_item(cur, today, 200, today - timedelta(days=80))
        b.api.admin(cur)
        prior = one(cur, "select count(*) from erp.fg_lots l join erp.cutting_groups g on g.id=l.cutting_group_id join erp.production_orders po on po.id=g.po_id "
                         "where po.model_id=%s and l.lot_origin='PRODUCTION' and l.produced_at>now()-interval'365 days'", (f['model'],))
        assert prior == 0, ('SS1_BASE_MODEL_HAS_LOTS', prior)
        for cut_day, lead in ((today - timedelta(days=70), 6), (today - timedelta(days=60), 9), (today - timedelta(days=55), 12)):
            produced(cur, f['product'], cut_day, lead)
        sell_days(cur, f, today, PATTERN)
        profile(cur, f, lead_days=30)
        compute(cur)
        e = evaluation(cur, f)
        lead = D('9.25')
        o = oracle(200 + 45, PATTERN, today, lead=lead)
        assert e['lead_basis'] == 'MEASURED' and D(str(e['lead_days'])) == lead and e['lead_groups'] == 3 and e['lead_lots'] == 3, e
        assert e['basis'] == 'FORMULA' and e['point'] == o['point'] and D(str(e['free_pcs'])) == 245 - sum(PATTERN), (e, o)
        return dict(status='PASS', lead_days=str(lead), lots=3, groups=3, measured_over_profile=True, point=o['point'])

    def days_buffer():
        f = item(cur, today, 200)
        sell_days(cur, f, today, PATTERN)
        profile(cur, f, lead_days=7, buffer_days=3)
        compute(cur)
        e = evaluation(cur, f)
        o = oracle(200, PATTERN, today, lead=7, buffer_days=3)
        assert e['buffer_mode'] == 'DAYS' and D(str(e['buffer_days'])) == 3 and e['point'] == o['point'], (e, o)
        assert abs(D(str(e['safety_pcs'])) - o['mean'] * 3) < D('0.0001'), e
        # Whole-piece boundary (E25v): 20 sold over 30 days, lead 2 + buffer 1 is exactly 2 pieces; the rounded mean
        # (0.6666...67) times 3 would have pushed it to 3.
        edge = [1 if i % 3 != 2 else 0 for i in range(30)]
        g = item(cur, today, 200)
        sell_days(cur, g, today, edge)
        profile(cur, g, lead_days=2, buffer_days=1)
        compute(cur)
        eg = evaluation(cur, g)
        og = oracle(200, edge, today, lead=2, buffer_days=1)
        assert og['point'] == 2 and eg['buffer_mode'] == 'DAYS' and eg['counted_days'] == 30 and eg['point'] == 2, (eg, og)
        return dict(status='PASS', point=o['point'], safety=str(o['safety']), sigma_not_used=True,
                    whole_piece_boundary=dict(sold=sum(edge), days=30, lead_days=2, buffer_days=1, point=2))

    def settings_level_and_window():
        f = item(cur, today, 200)
        sell_days(cur, f, today, PATTERN)
        profile(cur, f, lead_days=7)
        owner = master.role_actor(cur, 'OWNER')
        admin = master.role_actor(cur, 'ADMIN')
        staff = staff_with(cur, 'warehouse.fg.view')
        assert refused(cur, lambda: save_settings(cur, staff, '0.99', 30))[0] == '42501'
        req = str(uuid.uuid4())
        r = save_settings(cur, owner, '0.99', 30, request=req)
        assert r['replay'] is False and r['settings']['service_level'] == '0.99' and r['settings']['revision'] == 1, r
        assert save_settings(cur, owner, '0.99', 30, request=req, expected=0)['replay'] is True
        assert refused(cur, lambda: save_settings(cur, owner, '0.95', 30, request=req, expected=0))[1] == 'CP7_FORMULA_REQUEST_REUSED'
        assert refused(cur, lambda: save_settings(cur, owner, '0.95', 30, expected=0))[1] == 'CP7_FORMULA_SETTINGS_STALE'
        assert refused(cur, lambda: save_settings(cur, owner, '0.97', 30))[1] == 'CP7_FORMULA_SETTINGS_INVALID'
        assert refused(cur, lambda: save_settings(cur, owner, '0.95', 13))[1] == 'CP7_FORMULA_SETTINGS_INVALID'
        e = evaluation(cur, f)
        o = oracle(200, PATTERN, today, lead=7, level='0.99')
        assert e['point'] == o['point'] and D(str(e['z'])) == Z['0.99'], (e, o)
        r = save_settings(cur, admin, '0.90', 14)
        e = evaluation(cur, f)
        o14 = oracle(200 - sum(PATTERN[:16]), PATTERN[16:], today, window=14, lead=7, level='0.90')
        assert r['settings']['revision'] == 2 and e['counted_days'] == 14 and e['point'] == o14['point'], (e, o14)
        assert refused(cur, lambda: cur.execute("update cp7_stock_formula.settings set window_days=30"))[1] == 'CP7_FORMULA_APPEND_ONLY'
        return dict(status='PASS', point_99=o['point'], point_90_14days=o14['point'], staff_refused=True, replay=True, stale_refused=True)

    def manual_point():
        f = item(cur, today, 200)
        sell_days(cur, f, today, PATTERN)
        profile(cur, f, lead_days=7)
        admin = master.role_actor(cur, 'ADMIN')
        staff = staff_with(cur, 'warehouse.fg.view')
        free = 200 - sum(PATTERN)
        o = oracle(200, PATTERN, today, lead=7)
        assert refused(cur, lambda: save_manual(cur, staff, f, 500))[0] == '42501'
        r = save_manual(cur, admin, f, free)
        e = r['evaluation']
        assert e['basis'] == 'MANUAL' and e['point'] == free and e['formula_point'] == o['point'] and e['state'] == 'AT_OR_BELOW', e
        assert refused(cur, lambda: save_manual(cur, admin, f, 10, expected=0))[1] == 'CP7_FORMULA_MANUAL_STALE'
        assert refused(cur, lambda: save_manual(cur, admin, dict(f, product=str(uuid.uuid4())), 10, expected=0))[1] == 'CP7_FORMULA_ITEM_UNKNOWN'
        r = save_manual(cur, admin, f, 0)
        assert r['evaluation']['basis'] == 'MANUAL' and r['evaluation']['state'] == 'NO_POINT', r
        r = save_manual(cur, admin, f, None)
        e = r['evaluation']
        assert e['basis'] == 'FORMULA' and e['point'] == o['point'] and e['manual_point'] is None and r['revision'] == 3, e
        assert refused(cur, lambda: cur.execute('delete from cp7_stock_formula.manual_points'))[1] == 'CP7_FORMULA_APPEND_ONLY'
        return dict(status='PASS', manual=free, zero_means_never=True, cleared_back_to_formula=o['point'], staff_refused=True)

    def not_enough_data():
        short = item(cur, today, 100, stock_day=today - timedelta(days=10), effective_days=12)
        sell_days(cur, short, today, [0] * 20 + [3] * 10)
        profile(cur, short, lead_days=7)
        nolead = item(cur, today, 200)
        sell_days(cur, nolead, today, PATTERN)
        nosale = item(cur, today, 50)
        compute(cur)
        a, b2, c = evaluation(cur, short), evaluation(cur, nolead), evaluation(cur, nosale)
        assert (a['basis'], a['reason'], a['counted_days']) == ('NOT_ENOUGH_DATA', 'FEWER_THAN_14_COUNTED_DAYS', 10), a
        assert (b2['basis'], b2['reason']) == ('NOT_ENOUGH_DATA', 'NO_LEAD_TIME'), b2
        assert (c['basis'], c['reason']) == ('NO_SALES', 'NO_POSTED_SALES_IN_WINDOW'), c
        assert all(x['point'] is None and x['state'] == 'NO_POINT' for x in (a, b2, c))
        return dict(status='PASS', fewer_days=a['counted_days'], no_lead=True, no_sales=True, no_guessed_number=True)

    def reversed_sale():
        f = item(cur, today, 200)
        sell_days(cur, f, today, PATTERN)
        extra = sell(cur, f, today - timedelta(days=5), 40)
        profile(cur, f, lead_days=7)
        compute(cur)
        with_it = evaluation(cur, f)
        sales.native(cur, 'select erp.reverse_sale(%s,%s)', (extra['sale_id'], 'SS-1 sale undone'))
        compute(cur)
        e = evaluation(cur, f)
        o = oracle(200, PATTERN, today, lead=7)
        p40 = list(PATTERN)
        p40[25] += 40
        o40 = oracle(200, p40, today, lead=7)
        assert with_it['point'] == o40['point'] and e['point'] == o['point'] and D(str(e['sales_pcs'])) == sum(PATTERN), (with_it, e, o, o40)
        return dict(status='PASS', with_sale=o40['point'], after_inverse=o['point'])

    def in_production():
        f = base_item(cur, today, 150, today - timedelta(days=40))
        sell_days(cur, f, today, PATTERN)
        profile(cur, f, lead_days=7)
        compute(cur)
        o = oracle(150, PATTERN, today, lead=7)
        free = 150 - sum(PATTERN)
        e = evaluation(cur, f)
        assert free <= o['point'] and e['state'] == 'AT_OR_BELOW' and D(str(e['wip_pcs'] or 0)) == 0, (e, o)
        groups_before = [r[0] for r in cur.execute(
            "select g.id::text from erp.cutting_groups g join erp.production_orders po on po.id=g.po_id where po.model_id=%s "
            "and po.status not in('FINISHED','CANCELLED') and g.material_issue_posted", (f['model'],)).fetchall()]
        w = wsrc.b.two_size_fixture(cur, today, 'SS1-WIP', q1=60, q2=40)
        groups = groups_before + [w['group']]
        compute(cur)
        e2 = evaluation(cur, f)
        wip = D(0)
        for i in range(0, len(groups), 50):
            r = wsrc.capture(cur, groups[i:i + 50])
            assert r['result']['status'] == 'COMPLETE', r
            wip += sum(D(t['wip_pcs']) for t in r['result']['totals']
                       if t['pool_key'].startswith('CUT:') and t['ownership'] == 'COMPANY' and t['size_id'] == f['size'])
        assert e2['wip_status'] == 'COMPLETE' and D(str(e2['wip_pcs'])) == wip and wip >= 60, (e2, wip)
        assert e2['point'] == o['point'] == e['point'], (e, e2, o)
        expect = 'AT_OR_BELOW' if free + wip <= o['point'] else 'ABOVE'
        assert e2['state'] == expect, (e2, expect)
        return dict(status='PASS', free=free, wip=str(wip), point=o['point'], state_before='AT_OR_BELOW', state=expect, groups=len(groups), other_size_not_counted=True)

    def source_and_access():
        f = item(cur, today, 200)
        sell_days(cur, f, today, PATTERN)
        profile(cur, f, lead_days=7)
        free = 200 - sum(PATTERN)
        admin = master.role_actor(cur, 'ADMIN')
        save_manual(cur, admin, f, free + 1)
        owner = master.role_actor(cur, 'OWNER')
        src = _fg_source(cur, owner)
        mine = [x for x in src['rows'] if x['subject_key'] == f['target']]
        assert len(mine) == 1 and f['target'] not in src['states'], src
        d = mine[0]['detail']
        assert (d['free_pcs'], d['reorder_point_pcs'], d['basis'], d['wip_status']) == (str(free), str(free + 1), 'MANUAL', 'COMPLETE'), d
        assert mine[0]['title'].startswith('Stok barang jadi menipis: ') and mine[0]['party_names'] == [], mine
        nofg = staff_with(cur, 'warehouse.stock.view')
        assert refused(cur, lambda: _fg_source(cur, nofg))[1] == 'CP7_FORMULA_FG_SOURCE_DENIED'
        assert refused(cur, lambda: workspace(cur, nofg))[1] == 'CP7_FORMULA_ACCESS_DENIED'
        viewer = staff_with(cur, 'warehouse.fg.view')
        w = workspace(cur, viewer, filter='AT_OR_BELOW', q=f['sku'])
        assert w['can_manage'] is False and [r['target_key'] for r in w['page']['rows']] == [f['target']], w
        found(cur, f, today, 5, hour=0)
        src = _fg_source(cur, owner)
        assert src['states'].get(f['target']) == 'ABOVE_REORDER_POINT' and not [x for x in src['rows'] if x['subject_key'] == f['target']], src
        for who in ('anon', 'authenticated', 'service_role'):
            assert not one(cur, "select has_schema_privilege(%s,'cp7_stock_formula','USAGE')", (who,)), who
        return dict(status='PASS', alert_row_exact=True, resolved_when_stock_back=True, fg_view_required=True, viewer_cannot_manage=True)

    def volume():
        """SYNTHETIC_VOLUME (labelled, timing only): 2,000 items of 200 models, 800 pieces each 130 days ago and 100 sales each
        over the last 120 days (202,000 movements), written with session_replication_role=replica inside this case's
        transaction and rolled back with it. The evaluation the tick runs every minute must finish within VOLUME_LIMIT_MS."""
        b.api.admin(cur)
        cur.execute('set local session_replication_role=replica')
        cur.execute("""insert into erp.product_models(id,model_code,model_name,is_active)
            select gen_random_uuid(),'SS1V-M'||g,'SS-1 volume model '||g,true from generate_series(1,200)g""")
        cur.execute("""insert into erp.products(id,sku,model_id,brand_id,color_name,size_id,product_name,identity_root_id,effective_from,is_active,is_portal_visible)
            select x.id,'SS1V-'||x.n,m.id,b.brand_id,'SS1V',b.size_id,'SS-1 volume '||x.n,x.id,b.effective_from,true,true
            from(select gen_random_uuid()id,g n from generate_series(1,2000)g)x
            join(select id,row_number()over(order by model_code)rn from erp.product_models where model_code like 'SS1V-M%%')m on m.rn=1+(x.n%%200)
            cross join(select * from erp.products where id=%s)b""", (sales.fg.base.BASE_PRODUCT,))
        cur.execute("""insert into erp.fg_stock_movements(id,product_id,lot_id,location_id,quality_grade,movement_type,qty_signed,unit_hpp_snapshot,source_type,physical_at,system_created_at)
            select gen_random_uuid(),p.id,null,%s,'GRADE_A','OPENING',800,10,'SS1_VOLUME',now()-interval'130 days',now()-interval'130 days'
            from erp.products p where p.sku like 'SS1V-%%'""", (sales.fg.base.LOCATION,))
        cur.execute("""insert into erp.fg_stock_movements(id,product_id,lot_id,location_id,quality_grade,movement_type,qty_signed,unit_hpp_snapshot,source_type,physical_at,system_created_at)
            select gen_random_uuid(),p.id,null,%s,'GRADE_A','SALE',-(1+(g%%6)),10,'SS1_VOLUME',now()-((g%%120)||' days')::interval-interval'2 hours',now()-interval'1 hour'
            from erp.products p cross join generate_series(1,100)g where p.sku like 'SS1V-%%'""", (sales.fg.base.LOCATION,))
        cur.execute('set local session_replication_role=origin')
        cur.execute('analyze erp.fg_stock_movements')
        moves = one(cur, "select count(*) from erp.fg_stock_movements where source_type='SS1_VOLUME'")
        times = []
        for _ in range(3):
            t = time.monotonic()
            r = compute(cur)
            times.append(round((time.monotonic() - t) * 1000))
        b.api.admin(cur)
        n = one(cur, "select count(*) from cp7_stock_formula.evaluations where sku like 'SS1V-%%' and counted_days=30")
        assert moves == 202000 and n == 2000 and r['items'] >= 2000, (moves, n, r)
        assert max(times[1:]) <= VOLUME_LIMIT_MS, times
        return dict(status='PASS', label='SYNTHETIC_VOLUME', items=2000, movements=moves, millis=times, limit_ms=VOLUME_LIMIT_MS)

    named = [formula_from_sales, out_of_stock_days, lead_time_measured, days_buffer, settings_level_and_window, manual_point, not_enough_data,
             reversed_sale, in_production, source_and_access, volume]
    assert len(named) == len(NATIVE_IDS) - len(MATERIAL_IDS)
    return list(zip(NATIVE_IDS, named)) + material_cases(cur, today)


SPARSE = [10 if i % 3 == 0 else 0 for i in range(30)]


def material_cases(cur, today):
    """SS-2 (fabric) and SS-3 (accessories): the same formula on posted material use, lead time from the material setting."""
    day = lambda i: day_of(today, i)
    stock_day = today - timedelta(days=40)

    def low_state(free, point):
        return 'AT_OR_BELOW' if free <= point else 'ABOVE'

    def fabric_formula():
        m = fabric(cur, 280, stock_day)
        cut_days(cur, m, today, MAT_PATTERN, skip=(5,))
        g = cut(cur, m, day(5), MAT_PATTERN[5] + 2, remaining=2)
        return_fabric(cur, g, 2, day(5))
        admin = master.role_actor(cur, 'ADMIN')
        saved = save_material(cur, admin, m['material'], lead=6)
        assert saved['replay'] is False and saved['revision'] == 1, saved
        before = business(cur)
        compute(cur)
        assert business(cur) == before, 'SS2_COMPUTE_WROTE_BUSINESS'
        e = material_evaluation(cur, m['material'])
        o = material_oracle(280, MAT_PATTERN, 6)
        assert e['basis'] == 'FORMULA' and D(str(e['point'])) == o['point'] and D(str(e['free_qty'])) == o['free'] == 56, (e, o)
        assert D(str(e['usage_qty'])) == 224 and e['counted_days'] == 30 and D(str(e['on_order_qty'])) == 0 and D(str(e['lead_days'])) == 6, e
        assert e['state'] == low_state(o['free'], o['point']) == 'AT_OR_BELOW', (e, o)
        issued = one(cur, "select sum(-qty_signed) from erp.material_stock_movements where material_id=%s and movement_type='CUTTING_ISSUE'", (m['material'],))
        back = one(cur, "select sum(qty_signed) from erp.material_stock_movements where material_id=%s and movement_type='CUTTING_RETURN'", (m['material'],))
        assert (issued, back) == (226, 2), (issued, back)
        return dict(status='PASS', point=str(o['point']), free=str(o['free']), usage='224', issued=str(issued), returned=str(back),
                    lead_days='6', counted=30, compute_wrote_no_business_row=True)

    def fabric_out_of_stock():
        pattern = [12, 0, 9, 15, 0, 7, 7, 0, 0, 0, 0, 0, 13, 6, 9, 12, 0, 10, 7, 11, 0, 9, 14, 8, 0, 12, 10, 6, 0, 11]
        m = fabric(cur, 50, stock_day)
        cut_days(cur, m, today, pattern[:12])
        assert one(cur, 'select sum(qty_signed) from erp.material_stock_movements where material_id=%s', (m['material'],)) == 0
        m['location'], m['roll'] = receive_fabric(cur, m['material'], 300, day(12), location=m['location'])
        cut(cur, m, day(12), pattern[12], hour=10)
        cut_days(cur, m, today, [q if i > 12 else 0 for i, q in enumerate(pattern)])
        save_material(cur, master.role_actor(cur, 'ADMIN'), m['material'], lead=6)
        compute(cur)
        e = material_evaluation(cur, m['material'])
        o = material_oracle(50, pattern, 6, extra_moves=[(12, 300)])
        zero = material_oracle(10 ** 6, pattern, 6)
        assert o['counted'] == 25 and e['counted_days'] == 25 and D(str(e['point'])) == o['point'] and e['basis'] == 'FORMULA', (e, o)
        assert zero['counted'] == 30 and zero['point'] != o['point'], (zero, o)
        return dict(status='PASS', counted=25, empty_days_not_counted=5, point=str(o['point']), point_if_empty_days_were_zero_use=str(zero['point']))

    def fabric_reversed():
        m = fabric(cur, 300, stock_day)
        cut_days(cur, m, today, SPARSE)
        g = cut(cur, m, day(20), 25)
        reopen_cutting(cur, g)
        inverse = one(cur, "select count(*) from erp.material_stock_movements r join erp.material_stock_movements o on o.id=r.reversal_of_id "
                           "where o.source_type='CUTTING_GROUP' and o.source_id=%s", (g['group'],))
        save_material(cur, master.role_actor(cur, 'ADMIN'), m['material'], lead=6)
        compute(cur)
        e = material_evaluation(cur, m['material'])
        o = material_oracle(300, SPARSE, 6)
        counted_in = material_oracle(300, [q + (25 if i == 20 else 0) for i, q in enumerate(SPARSE)], 6)
        assert inverse == 1 and D(str(e['usage_qty'])) == 100 and D(str(e['free_qty'])) == 200 and D(str(e['point'])) == o['point'], (inverse, e, o)
        assert counted_in['point'] != o['point'], (counted_in, o)
        return dict(status='PASS', cancelled_cutting_and_its_inverse_not_use=True, usage='100', point=str(o['point']),
                    point_if_cancelled_cut_counted=str(counted_in['point']))

    def fabric_minimum():
        m = fabric(cur, 300, stock_day, minimum='500')
        cut_days(cur, m, today, SPARSE)
        admin = master.role_actor(cur, 'ADMIN')
        save_material(cur, admin, m['material'], lead=6)
        equal = fabric(cur, 300, stock_day, minimum='300')
        compute(cur)
        e, q = material_evaluation(cur, m['material']), material_evaluation(cur, equal['material'])
        o = material_oracle(300, SPARSE, 6)
        assert (e['basis'], e['manual_source'], D(str(e['point'])), e['state']) == ('MANUAL', 'FABRIC_MINIMUM', 500, 'AT_OR_BELOW'), e
        assert D(str(e['formula_point'])) == o['point'], (e, o)
        assert (q['basis'], D(str(q['free_qty'])), D(str(q['point'])), q['state']) == ('MANUAL', 300, 300, 'ABOVE'), q
        owner = master.role_actor(cur, 'OWNER')
        src = material_source(cur, owner, 'FABRIC')
        assert not [r for r in src['rows'] if r['subject_key'] in (m['material'], equal['material'])], src
        assert src['states'].get(m['material']) == src['states'].get(equal['material']) == 'MANUAL_MINIMUM_IN_FORCE', src['states']
        code = refused(cur, lambda: save_material(cur, admin, m['material'], lead=6, manual=10))
        assert code == ('22023', 'CP7_FORMULA_MATERIAL_INVALID'), code
        return dict(status='PASS', minimum_replaces_formula=True, strict_below_like_fabric_below_minimum=True,
                    formula_point_kept_for_view=str(o['point']), fabric_manual_point_refused=True)

    def fabric_on_order():
        m = fabric(cur, 130, stock_day)
        cut_days(cur, m, today, SPARSE)
        save_material(cur, master.role_actor(cur, 'ADMIN'), m['material'], lead=6)
        compute(cur)
        e0 = material_evaluation(cur, m['material'])
        o = material_oracle(130, SPARSE, 6)
        assert (D(str(e0['free_qty'])), D(str(e0['on_order_qty'])), e0['state']) == (30, 0, 'AT_OR_BELOW') and D(str(e0['point'])) == o['point'] < 50, (e0, o)
        commitment(cur, today, m, 20)
        compute(cur)
        e = material_evaluation(cur, m['material'])
        assert (D(str(e['free_qty'])), D(str(e['on_order_qty'])), D(str(e['point'])), e['state']) == (30, 20, o['point'], 'ABOVE'), e
        return dict(status='PASS', free='30', on_order='20', point=str(o['point']), state_before='AT_OR_BELOW', state_after='ABOVE')

    def no_lead_time():
        admin = master.role_actor(cur, 'ADMIN')
        m = fabric(cur, 300, stock_day)
        cut_days(cur, m, today, SPARSE)
        late = fabric(cur, 0, stock_day)
        late['location'], late['roll'] = receive_fabric(cur, late['material'], 100, day(20))
        few = [10 if i in (21, 24, 27) else 0 for i in range(30)]
        cut_days(cur, late, today, few)
        save_material(cur, admin, late['material'], lead=6)
        idle = fabric(cur, 50, stock_day)
        save_material(cur, admin, idle['material'], lead=6)
        compute(cur)
        e, l, i = (material_evaluation(cur, x['material']) for x in (m, late, idle))
        ol = material_oracle(0, few, 6, extra_moves=[(20, 100)])
        assert (e['basis'], e['reason'], e['point'], e['state']) == ('NOT_ENOUGH_DATA', 'NO_LEAD_TIME', None, 'NO_POINT'), e
        assert (l['basis'], l['reason'], l['point'], l['counted_days']) == ('NOT_ENOUGH_DATA', 'FEWER_THAN_14_COUNTED_DAYS', None, ol['counted']), (l, ol)
        assert ol['counted'] == 9, ol
        assert (i['basis'], i['reason'], i['point']) == ('NO_USAGE', 'NO_POSTED_USAGE_IN_WINDOW', None), i
        src = material_source(cur, master.role_actor(cur, 'OWNER'), 'FABRIC')
        assert all(src['states'].get(x['material']) == 'NO_REORDER_POINT' for x in (m, late, idle)), src['states']
        w = material_workspace(cur, admin, material_type='FABRIC', filter='NOT_ENOUGH_DATA', q='Kain SS2')
        listed = {r['material_id'] for r in w['page']['rows']}
        assert {m['material'], late['material']} <= listed and idle['material'] not in listed, w
        save_material(cur, admin, m['material'], lead=6)
        e = material_evaluation(cur, m['material'])
        assert e['basis'] == 'FORMULA' and D(str(e['point'])) == material_oracle(300, SPARSE, 6)['point'], e
        return dict(status='PASS', no_lead_time='NOT_ENOUGH_DATA', fewer_than_14_counted=ol['counted'], no_use='NO_USAGE', lead_saved_then_formula=True)

    # Owner D17-10: accessories have no formula. The usage is still measured (shown to help choose the minimum); without a
    # minimum (typed, or worked out from the owner's numbers, D17-12) there is no point and no reminder; a lead time alone is
    # not enough.
    def accessory_usage():
        a = accessory(cur, today, 270)
        notes = accessory_days(cur, a, today, MAT_PATTERN)
        credit_back(cur, a, notes[2][1], 4, day(3))
        pattern = [q - (4 if i == 3 else 0) for i, q in enumerate(MAT_PATTERN)]
        admin, owner = master.role_actor(cur, 'ADMIN'), master.role_actor(cur, 'OWNER')
        save_material(cur, admin, a['material'], lead=5, reason='SS-3 lama kirim saja')
        before = business(cur)
        compute(cur)
        assert business(cur) == before, 'SS3_COMPUTE_WROTE_BUSINESS'
        e = material_evaluation(cur, a['material'])
        o = material_oracle(270, pattern, 1)
        kinds = dict(cur.execute("select movement_type||coalesce(':'||source_type,''),count(*) from erp.material_stock_movements where material_id=%s "
                                 "and movement_type in('CONTRACTOR_ISSUE','INTERNAL_USE','ADJUSTMENT') group by 1", (a['material'],)).fetchall())
        assert (e['basis'], e['reason'], e['point'], e['formula_point'], e['estimate_point'], e['safety_qty'], D(str(e['lead_days'])), e['state']) == (
            'NOT_SET', 'NO_MINIMUM_OR_ESTIMATE', None, None, None, None, 5, 'NO_POINT'), e
        assert D(str(e['free_qty'])) == o['free'] == 50 and D(str(e['usage_qty'])) == 220 and e['counted_days'] == o['counted'] == 30, (e, o)
        assert D(str(e['daily_mean'])) == o['mean'].quantize(D('0.0001'), rounding=ROUND_HALF_UP), (e['daily_mean'], o['mean'])
        assert kinds == {'CONTRACTOR_ISSUE:CONTRACTOR_MATERIAL_ISSUE_ITEM': 10, 'INTERNAL_USE:MATERIAL_ADJUSTMENT_ITEM': 12,
                         'ADJUSTMENT:BC_NOTE_RETURN_CREDIT': 1}, kinds
        src = material_source(cur, owner, 'ACCESSORY')
        assert not [x for x in src['rows'] if x['subject_key'] == a['material']] and src['states'].get(a['material']) == 'NO_REORDER_POINT', src
        w = material_workspace(cur, admin, material_type='ACCESSORY', filter='NOT_SET', q=a['sku'])
        assert [r['material_id'] for r in w['page']['rows']] == [a['material']] and w['counts']['formula'] == 0, w
        return dict(status='PASS', basis='NOT_SET', free='50', usage='220 (224 used, 4 credited back usable)', daily_mean=str(e['daily_mean']),
                    lead_time_alone_no_point=True, no_reminder_without_minimum=True, movements=kinds)

    def service_zones():
        a = accessory(cur, today, 300)
        notes = accessory_days(cur, a, today, SPARSE)
        credit_back(cur, a, notes[0][1], 5, day(1), condition='DAMAGED')
        bc.fill(cur, a, 40, day(25))
        bc.use(cur, a, a['SERVICE_POST'], [(15, day(26), 10, 'FACTORY_USE')])
        b.api.admin(cur)
        # The minimum is just above the warehouse stock alone (160) and below warehouse + service post (185): the reminder
        # rings only because the service post is not free stock.
        save_material(cur, master.role_actor(cur, 'ADMIN'), a['material'], manual='170', reason='SS-3 batas minimum')
        compute(cur)
        e = material_evaluation(cur, a['material'])
        pattern = [q + (15 if i == 26 else 0) for i, q in enumerate(SPARSE)]
        o = material_oracle(300, pattern, 1, extra_moves=[(25, -40), (26, 15)])
        zones = {k: D(str(bc.stock(cur, a['material'], a[k]))) for k in ('main', 'SERVICE_POST', 'DAMAGED')}
        assert zones == dict(main=160, SERVICE_POST=25, DAMAGED=5), zones
        assert (D(str(e['free_qty'])), D(str(e['usage_qty']))) == (160, 115) and o['free'] == 160, (e, o)
        assert (e['basis'], D(str(e['point'])), e['state']) == ('MANUAL', 170, 'AT_OR_BELOW'), e
        return dict(status='PASS', free_main_only='160', service_post_not_free='25', damaged_area_not_free='5',
                    damaged_credit_not_subtracted_from_use=True, use_at_service_post_counted='15', minimum='170', state='AT_OR_BELOW')

    def accessory_manual():
        a = accessory(cur, today, 280)
        accessory_days(cur, a, today, SPARSE)
        admin = master.role_actor(cur, 'ADMIN')
        owner = master.role_actor(cur, 'OWNER')
        assert material_oracle(280, SPARSE, 1)['free'] == 180
        steps = []
        # Stock 180: a minimum of 80 is above, 180 (equal) and 250 ring, 0 never rings, clearing it leaves no minimum (D17-10:
        # no formula to fall back to; no estimate entered here).
        for manual, expect in (('80', ('MANUAL', D(80), 'ABOVE')), ('180', ('MANUAL', D(180), 'AT_OR_BELOW')),
                               ('250', ('MANUAL', D(250), 'AT_OR_BELOW')), ('0', ('MANUAL', D(0), 'NO_POINT')), (None, ('NOT_SET', None, 'NO_POINT'))):
            r = save_material(cur, admin, a['material'], manual=manual, reason='SS-3 batas minimum')
            e = r['evaluation']
            got = (e['basis'], None if e['point'] is None else D(str(e['point'])), e['state'])
            assert got == expect and e['lead_days'] is None and e['formula_point'] is None, (manual, got, expect, e)
            src = material_source(cur, owner, 'ACCESSORY')
            mine = [x for x in src['rows'] if x['subject_key'] == a['material']]
            assert (len(mine) == 1) == (expect[2] == 'AT_OR_BELOW'), (manual, src)
            if expect[2] == 'NO_POINT':
                assert src['states'].get(a['material']) == 'NO_REORDER_POINT', src['states']
            steps.append(dict(manual=manual, basis=got[0], point=None if got[1] is None else str(got[1]), state=got[2]))
        assert one(cur, 'select max(revision) from cp7_stock_formula.material_settings where material_id=%s', (a['material'],)) == 5
        code = refused(cur, lambda: cur.execute("update cp7_stock_formula.material_settings set reason='x' where material_id=%s", (a['material'],)))
        assert code[0] == 'P0001' or 'APPEND' in code[1].upper(), code
        return dict(status='PASS', steps=steps, equal_rings=True, zero_means_never=True, cleared_means_no_minimum=True, history_append_only=True)

    def source_and_access():
        fm = fabric(cur, 130, stock_day)
        cut_days(cur, fm, today, SPARSE)
        a = accessory(cur, today, 280)
        accessory_days(cur, a, today, SPARSE)
        admin, owner = master.role_actor(cur, 'ADMIN'), master.role_actor(cur, 'OWNER')
        save_material(cur, admin, fm['material'], lead=6)
        save_material(cur, admin, a['material'], manual='250')
        o = material_oracle(130, SPARSE, 6)
        src = material_source(cur, owner, 'FABRIC')
        mine = [x for x in src['rows'] if x['subject_key'] == fm['material']]
        assert len(mine) == 1 and mine[0]['title'] == 'Stok kain di bawah minimum: ' + fm['name'] and mine[0]['party_names'] == [], mine
        d = mine[0]['detail']
        assert (D(d['free_qty']), D(d['on_order_qty']), D(d['reorder_point_qty']), d['basis'], D(d['lead_days']), d['service_level']) == (
            30, 0, o['point'], 'FORMULA', 6, '0.95'), d
        acc = [x for x in material_source(cur, owner, 'ACCESSORY')['rows'] if x['subject_key'] == a['material']]
        assert len(acc) == 1 and acc[0]['title'] == 'Stok aksesori menipis: ' + a['name'], acc
        assert (D(acc[0]['detail']['reorder_point_qty']), acc[0]['detail']['basis'], acc[0]['detail']['safety_qty'], acc[0]['detail']['service_level'],
                acc[0]['detail']['lead_days']) == (250, 'MANUAL', None, None, None), acc
        material_only = staff_with(cur, 'warehouse.material.view')
        assert refused(cur, lambda: material_source(cur, material_only, 'FABRIC'))[1] == 'CP7_FORMULA_MATERIAL_SOURCE_DENIED'
        assert refused(cur, lambda: material_workspace(cur, material_only, material_type='FABRIC'))[1] == 'CP7_FORMULA_ACCESS_DENIED'
        fabric_viewer = staff_with(cur, 'warehouse.material.view', 'master.fabric.view')
        w = material_workspace(cur, fabric_viewer, material_type='FABRIC', filter='AT_OR_BELOW', q=fm['sku'])
        assert w['can_manage'] is False and [r['material_id'] for r in w['page']['rows']] == [fm['material']], w
        assert refused(cur, lambda: save_material(cur, fabric_viewer, fm['material'], lead=7))[1] == 'CP7_FORMULA_ACCESS_DENIED'
        acc_viewer = staff_with(cur, 'warehouse.accessory.view')
        assert material_workspace(cur, acc_viewer, material_type='ACCESSORY', q=a['sku'])['page']['rows'][0]['material_id'] == a['material']
        assert refused(cur, lambda: material_workspace(cur, acc_viewer, material_type='FABRIC'))[1] == 'CP7_FORMULA_ACCESS_DENIED'
        assert refused(cur, lambda: save_material(cur, admin, fm['material'], lead=7, expected=0)) == ('40001', 'CP7_FORMULA_MATERIAL_STALE')
        request = str(uuid.uuid4())
        first = save_material(cur, admin, fm['material'], lead=7, request=request)
        again = save_material(cur, admin, fm['material'], lead=7, request=request, expected=1)
        assert first['revision'] == 2 and again == dict(replay=True, material_id=fm['material'], revision=2), (first, again)
        assert refused(cur, lambda: save_material(cur, admin, fm['material'], lead=8, request=request, expected=2))[1] == 'CP7_FORMULA_REQUEST_REUSED'
        for bad in (dict(lead='0'), dict(lead='366'), dict(lead='6', manual='10')):
            assert refused(cur, lambda: save_material(cur, admin, fm['material'], **bad))[1] == 'CP7_FORMULA_MATERIAL_INVALID', bad
        assert refused(cur, lambda: save_material(cur, admin, str(uuid.uuid4()), lead=6, expected=0))[1] == 'CP7_FORMULA_ITEM_UNKNOWN'
        receive_fabric(cur, fm['material'], 100, today, location=fm['location'], hour=0)
        src = material_source(cur, owner, 'FABRIC')
        assert src['states'].get(fm['material']) == 'ABOVE_REORDER_POINT' and not [x for x in src['rows'] if x['subject_key'] == fm['material']], src
        for who in ('anon', 'authenticated', 'service_role'):
            assert not one(cur, "select has_schema_privilege(%s,'cp7_stock_formula','USAGE')", (who,)), who
        return dict(status='PASS', alert_rows_exact=True, fabric_needs_material_and_fabric_view=True, accessory_view_separate=True,
                    viewer_cannot_change=True, stale_reused_invalid_unknown_refused=True, resolved_when_stock_back=True)

    # Owner D17-12: the accessory minimum worked out in the app from the owner's own numbers (MOQ, monthly use, lead time,
    # buffer), checked against estimate_oracle(); a typed minimum wins; a missing number leaves no minimum.
    def accessory_estimate():
        a = accessory(cur, today, 280)
        accessory_days(cur, a, today, SPARSE)
        admin, owner = master.role_actor(cur, 'ADMIN'), master.role_actor(cur, 'OWNER')
        est = dict(moq='10000', usage_month_qty='1000', buffer_days='7')
        r = save_material(cur, admin, a['material'], lead=21, estimate=est, reason='SS-3 isian hitung minimum')
        e = r['evaluation']
        point = estimate_oracle(1000, 21, 7)
        assert point == D('933.34'), point
        assert (e['basis'], D(str(e['point'])), D(str(e['estimate_point'])), D(str(e['moq'])), D(str(e['usage_month_qty'])), D(str(e['buffer_days'])),
                D(str(e['lead_days'])), e['manual_point'], e['formula_point'], e['safety_qty'], e['state']) == (
            'ESTIMATE', point, point, 10000, 1000, 7, 21, None, None, None, 'AT_OR_BELOW'), e
        src = material_source(cur, owner, 'ACCESSORY')
        mine = [x for x in src['rows'] if x['subject_key'] == a['material']]
        assert len(mine) == 1 and mine[0]['title'] == 'Stok aksesori menipis: ' + a['name'], src
        d = mine[0]['detail']
        assert (D(d['reorder_point_qty']), d['basis'], D(d['lead_days']), d['safety_qty'], d['service_level'], D(d['free_qty'])) == (
            point, 'ESTIMATE', 21, None, None, 180), d
        # Whole-cent boundaries (E25v): dividing first (500 / 30 rounded, then x 21) gave 350.01 where the exact answer is 350.
        bounds = []
        for usage, lead, buf, want in (('500', 14, '7', D('350.00')), ('200', 10, '5', D('100.00'))):
            assert estimate_oracle(usage, lead, buf) == want, (usage, lead, buf)
            e = save_material(cur, admin, a['material'], lead=lead, estimate=dict(moq='10000', usage_month_qty=usage, buffer_days=buf),
                              reason='SS-3 batas pembulatan')['evaluation']
            assert (e['basis'], D(str(e['point'])), D(str(e['estimate_point']))) == ('ESTIMATE', want, want), (usage, lead, buf, e)
            bounds.append(dict(usage_month=usage, lead_days=lead, buffer_days=buf, minimum=str(want)))
        steps = []
        for manual, more, expect in ((None, dict(buffer_days='0'), ('ESTIMATE', estimate_oracle(1000, 21, 0), 'AT_OR_BELOW')),
                                     ('100', {}, ('MANUAL', D(100), 'ABOVE')), (None, {}, ('ESTIMATE', estimate_oracle(1000, 21, 0), 'AT_OR_BELOW')),
                                     (None, dict(usage_month_qty=None), ('NOT_SET', None, 'NO_POINT'))):
            est = {**est, **more}
            e = save_material(cur, admin, a['material'], lead=21, manual=manual, estimate=est, reason='SS-3 isian hitung minimum')['evaluation']
            got = (e['basis'], None if e['point'] is None else D(str(e['point'])), e['state'])
            assert got == expect, (manual, more, got, expect, e)
            steps.append(dict(manual=manual, changed=more, basis=got[0], point=None if got[1] is None else str(got[1]), state=got[2]))
        assert estimate_oracle(1000, 21, 0) == D('700.00')
        w = material_workspace(cur, admin, material_type='ACCESSORY', filter='NOT_SET', q=a['sku'])
        assert [r['material_id'] for r in w['page']['rows']] == [a['material']], w
        fm = fabric(cur, 130, stock_day)
        for bad in (dict(moq='100'), dict(usage_month_qty='100'), dict(buffer_days='3')):
            assert refused(cur, lambda: save_material(cur, admin, fm['material'], lead=6, estimate=bad))[1] == 'CP7_FORMULA_MATERIAL_INVALID', bad
        for bad in (dict(moq='0'), dict(usage_month_qty='0'), dict(buffer_days='366'), dict(buffer_days='-1')):
            assert refused(cur, lambda: save_material(cur, admin, a['material'], lead=21, estimate=bad))[1] == 'CP7_FORMULA_MATERIAL_INVALID', bad
        return dict(status='PASS', minimum=str(point), rule='perkiraan per bulan x (lama kirim + cadangan) / 30, dikali dulu baru dibagi, ke atas 0,01', steps=steps,
                    whole_cent_boundaries=bounds, typed_minimum_wins=True, missing_number_no_minimum=True, fabric_refuses_estimate=True,
                    invalid_refused=True)

    named = [fabric_formula, fabric_out_of_stock, fabric_reversed, fabric_minimum, fabric_on_order, no_lead_time,
             accessory_usage, service_zones, accessory_manual, source_and_access, accessory_estimate]
    assert len(named) == len(MATERIAL_IDS)
    return list(zip(MATERIAL_IDS, named))
