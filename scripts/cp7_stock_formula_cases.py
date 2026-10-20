"""SS-1 (owner D17-8, D17-9): finished-goods reorder point by formula, declared cases (docs/cp7/wa/STOCK_FORMULA.json).

Every business row comes from the accepted Native commands (stock found at opname, sale draft and post, the production
chain's cutting, laundry and QC); only masters are inserted, as the other CP7 suites do. The oracle recomputes the
reorder point in Python from the fixture's own numbers (days, quantities, settings), never from the module's tables.
"""
from datetime import timedelta
from decimal import Decimal as D, ROUND_CEILING
import json
import math
import statistics
import time
import uuid

import psycopg

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
def item(cur, today, stock, stock_day=None, effective_days=90):
    """A new SKU of a new model with `stock` pieces found at opname at 08:00 WIB of stock_day (default: 40 days ago)."""
    stock_day = stock_day or today - timedelta(days=40)
    product, _ = sales.fg.ax.owner_only_model_product(cur, effective_from=at(today - timedelta(days=effective_days), 0))
    found = sales.fg.ax.post(cur, dict(source_kind='FOUND_AT_OPNAME', product_id=product, location_id=sales.fg.base.LOCATION, qty_pcs=stock,
                                       physical_at=at(stock_day, 8).isoformat(), reason='SS-1 stock found at opname',
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
    if buffer_days is not None:
        safety = mean * D(str(buffer_days))
    else:
        safety = Z[level] * sd * lead.sqrt()
    point = int((mean * lead + safety).to_integral_value(rounding=ROUND_CEILING))
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
VOLUME_LIMIT_MS = 3000
PATTERN = [3, 5, 0, 4, 6, 2, 5, 3, 7, 4, 0, 5, 6, 3, 4, 5, 2, 6, 4, 3, 5, 0, 4, 6, 3, 5, 4, 2, 6, 5]


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
        return dict(status='PASS', point=o['point'], safety=str(o['safety']), sigma_not_used=True)

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
    assert len(named) == len(NATIVE_IDS)
    return list(zip(NATIVE_IDS, named))
