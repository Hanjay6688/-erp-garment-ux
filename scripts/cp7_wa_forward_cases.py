"""WA-3b (owner D17-3..D17-6): Pengingat sistem and their forwarding to the owner's WhatsApp, on the closed Native harness.

Owner: "semua hal yg masuk ke reminder harus langsung forward wa biar realtime" and "tiap kena safety stock dll auto
kirim terus, yg sehari 2kali itu juga mau kan ringkasan". Design: docs/cp7/WA_CALLMEBOT_DESIGN_20261019.md.

Sources are made only by Native writers and public facades: a fabric and its minimum through the master screen
(erp_cp7_save_master_v1), stock through Pembelian & Penerimaan, a sale with a due date, its post and payments, a
supplier receipt with a final invoice and its payments, owner and staff reminders through erp_save_my_reminder_v1.
Oracles are independent: raw movement sums for fabric, Ringkasan Gudang's own answer, the fixture's own amounts and
dates, the queued pg_net request decoded back to phone/text/key. The provider is only the fake CallMeBot of the CI
stack (scripts/cp7_wa_fake_callmebot.py) and the test number +620000000000 with FAKEKEY-* keys.
SYNTHETIC steps are labelled where used: provider answers written into net._http_response in the savepoint cases
(SYNTHETIC_PROVIDER_ANSWER; the race cases use the real fake server), and clocks moved back on rows of the module's
own tables to stand for minutes or hours passing (TEST_CLOCK_OVERRIDE, session_replication_role=replica inside the
case's transaction only).

WA-2b analysis kinds: the owner's own staged analysis is made by the plan v2 fixture through the public analysis RPCs, the
owner's reminder rule through erp_cp7_save_reminder_policy_v2, and the reminders' own read-only recheck is the oracle for
every alert opened, refreshed or resolved. The automatic-analysis case moves the capture time of the owner's finished job
20 minutes back (TEST_CLOCK_OVERRIDE, labelled, inside the case's transaction only) to stand for the interval passing,
and drives the job the tick asked for with the ordinary step RPC in the owner's name (the K4 runner's role in production).
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal as D
from urllib.parse import parse_qs, urlparse, urlunparse
import json
import math
import os
import subprocess
import time
import uuid

import psycopg

import cp7_snapshot_cases as auth
import cp7_master_cases as master
import cp7_procurement_cases as receipt
import cp7_sales_cases as sales
import cp7_invoice_cases as invoice
import cp7_payable_condition_cases as payables
import cp7_p19_reminder_v2_cases as remv2
planv2 = remv2.planv2
import cp7_alert_bundle as bundle
import cp7_stock_formula_cases as formula

b = auth.b
IDS = dict(
    native=['WAF_COLLECT_WAITS_FOR_OWNER_SETTINGS', 'WAF_FABRIC_EQUALS_WAREHOUSE_SUMMARY', 'WAF_AR_AP_FROM_ACCEPTED_SOURCES',
            'WAF_OWNER_REMINDERS_ONLY_WHEN_DUE', 'WAF_SEND_ONE_REQUEST_EXACT_TEXT', 'WAF_ROLLBACK_QUEUES_NOTHING',
            'WAF_RESOLVED_BEFORE_SEND_NOT_SENT', 'WAF_ANSWERS_ACCEPTED_REFUSED_UNKNOWN', 'WAF_PACING_BURST_QUIET_DIGEST_REPEAT',
            'WAF_OFF_OR_NO_KEY_SENDS_NOTHING', 'WAF_KEY_WRITE_ONLY_AND_MASKED', 'WAF_PRIVACY_AND_LIST_PERMISSIONS',
            'WAF_TICKS_PRIVATE_AND_LIMITED', 'WAF_ANALYSIS_GAP_FORWARDED_AND_RECHECKED', 'WAF_ANALYSIS_AUTOMATIC_RUN',
            # SS-1 (D17-8/D17-9): finished goods at or under their reorder point, and the formula itself (cp7_stock_formula_cases).
            'WAF_FG_REORDER_POINT_FORWARDED', 'WAF_FG_RESOLVED_BEFORE_SEND'] + formula.NATIVE_IDS,
    races=['WAF_RACE_TWO_SEND_TICKS_ONE_MESSAGE', 'WAF_RACE_COLLECT_AND_SEND_OPEN_ONCE', 'WAF_RACE_FAKE_CALLMEBOT_END_TO_END',
           'WAF_RACE_PG_CRON_RUNS_TICKS', 'WAF_RACE_FG_BUSY_RECHECKS_LIVE_STOCK'],
    http=['WAF_HTTP_OWNER_SETS_UP_AND_TESTS', 'WAF_HTTP_OTHERS_REFUSED', 'WAF_HTTP_FG_REORDER_SCREEN'],
    # WA-4b: scripts/cp7_wa_forward_browser.mjs (real Auth, PostgREST and UI on the browser copy; fake CallMeBot only).
    browser=['WAF_BROWSER_DESKTOP_OWNER_SETS_UP_TESTS_AND_FORWARDS', 'WAF_BROWSER_MOBILE_OWNER_SETS_UP_TESTS_AND_FORWARDS',
             'WAF_BROWSER_ADMIN_SEES_SYSTEM_REMINDERS_WITHOUT_WA', 'WAF_BROWSER_FG_REORDER_DESKTOP', 'WAF_BROWSER_FG_REORDER_MOBILE'],
)
REQUIRED = {key: len(value) for key, value in IDS.items()}
EXPECTED = sum(REQUIRED.values())
DECLARED = 41
CONTRACT = 'cp7.wa.forward.v1'
FUNCTIONS = ('erp_cp7_get_alerts_v1', 'erp_cp7_get_wa_settings_v1', 'erp_cp7_save_wa_settings_v1', 'erp_cp7_set_wa_key_v1',
             'erp_cp7_send_wa_test_v1', 'erp_cp7_resolve_wa_dispatch_v1')
SCHEDULES = list(bundle.SCHEDULES)
KEY = 'FAKEKEY-WA3B'
PHONE = '+620000000000'
FAKE = 'http://fake-callmebot:8080/whatsapp.php'
KINDS = ['MANUAL_REMINDER', 'FABRIC_BELOW_MINIMUM', 'AR_DUE', 'AP_DUE']
ANALYSIS = ['PRODUCTION_GAP', 'FABRIC_NEED']
PLANNING = {'master.product.view', 'production.wip.view', 'warehouse.stock.view', 'sales.invoice.view'}
SETTINGS = dict(enabled=False, phone_e164=PHONE, detail='SUMMARY', digest_times=[], kinds=KINDS, repeat_minutes=1440, burst_after_per_day=30,
                burst_merge_minutes=30, max_items=10, quiet_enabled=False, quiet_start='21:00', quiet_end='06:00', analysis_every_minutes=60,
                analysis_start='07:00', analysis_end='20:00')
CONTAINER = os.environ.get('CP6_DATABASE_CONTAINER', 'supabase_db_cp5-local')


def one(cur, sql, args=None):
    return cur.execute(sql, args).fetchone()[0]


def rpc(cur, name, args, subject):
    """One public RPC as the subject, as PostgREST runs it (role authenticated, the subject's claims)."""
    auth.actor(cur, subject)
    out = cur.execute('select public.' + name + '(' + ','.join(['%s'] * len(args)) + ')', args).fetchone()[0]
    b.api.admin(cur)
    return out


def refusal(cur, op):
    """(sqlstate, message) of an operation that must fail; the case's transaction goes on."""
    b.api.admin(cur)
    cur.execute('savepoint waf_refusal')
    try:
        op()
    except psycopg.Error as e:
        cur.execute('rollback to savepoint waf_refusal')
        b.api.admin(cur)
        return e.sqlstate, e.diag.message_primary
    cur.execute('rollback to savepoint waf_refusal')
    b.api.admin(cur)
    raise AssertionError('WAF_EXPECTED_REFUSAL')


def tick(cur, name, timeout='8s'):
    """One tick exactly as pg_cron runs it: role postgres, no request identity, the 8 s statement limit."""
    b.api.admin(cur)
    prior = one(cur, 'show statement_timeout')
    cur.execute("select set_config('statement_timeout',%s,true),set_config('request.jwt.claims','',true),set_config('request.jwt.claim.sub','',true)",
                (timeout,))
    cur.execute('set local role postgres')
    out = one(cur, 'select cp7_alert_native.' + name + '()')
    cur.execute('reset role')
    b.api.admin(cur)
    cur.execute("select set_config('statement_timeout',%s,true)", (prior,))
    return out


def pg_net(cur):
    """pg_net is preloaded on the stack but not created (WA-0); created as postgres, inside the case."""
    b.api.admin(cur)
    if not one(cur, "select exists(select 1 from pg_extension where extname='pg_net')"):
        cur.execute('set local role postgres')
        cur.execute('create extension pg_net')
        cur.execute('reset role')
        b.api.admin(cur)


def settings_payload(revision, **values):
    return json.dumps(dict(SETTINGS, expected_revision=revision, **values))


def revision(cur):
    b.api.admin(cur)
    return one(cur, 'select coalesce(max(revision),0) from cp7_alert_native.settings')


def save(cur, owner, **values):
    return rpc(cur, 'erp_cp7_save_wa_settings_v1', (settings_payload(revision(cur), **values), str(uuid.uuid4())), owner)


def setup(cur, enabled=True, key=True, **values):
    """An owner (seeded OWNER role) who saves the settings, sets the fake key and, by default, switches WhatsApp on;
    the transport points at the fake CallMeBot."""
    pg_net(cur)
    owner = master.role_actor(cur, 'OWNER')
    user = one(cur, 'select id::text from erp.app_users where auth_user_id=%s', (owner,))
    save(cur, owner, **dict(values, enabled=False))
    if key:
        rpc(cur, 'erp_cp7_set_wa_key_v1', (KEY, str(uuid.uuid4())), owner)
    b.api.admin(cur)
    cur.execute('update cp7_alert_native.transport set base_url=%s', (FAKE,))
    if enabled:
        save(cur, owner, **dict(values, enabled=True))
    return dict(owner=owner, user=user)


def test_clock(cur, sql, args=None):
    """TEST_CLOCK_OVERRIDE (labelled): move the module's own time columns back inside this transaction only."""
    b.api.admin(cur)
    cur.execute('set local session_replication_role=replica')
    cur.execute(sql, args)
    cur.execute('set local session_replication_role=origin')


def age_dispatches(cur, minutes):
    test_clock(cur, "update cp7_alert_native.dispatches set queued_at=queued_at-make_interval(mins=>%s),answered_at=answered_at-make_interval(mins=>%s)",
               (minutes, minutes))


def answer(cur, dispatch, status, content='', timed_out=False, error=None):
    """SYNTHETIC_PROVIDER_ANSWER (labelled): the row pg_net would write for this dispatch's request."""
    b.api.admin(cur)
    req = one(cur, 'select net_request_id from cp7_alert_native.dispatches where id=%s', (dispatch,))
    cur.execute('insert into net._http_response(id,status_code,content,timed_out,error_msg,created)values(%s,%s,%s,%s,%s,now())',
                (req, status, content, timed_out, error))


def queued(cur, after=0):
    """pg_net requests queued in this transaction, decoded back to their parameters."""
    b.api.admin(cur)
    rows = cur.execute('select id,url from net.http_request_queue where id>%s order by id', (after,)).fetchall()
    out = []
    for rid, url in rows:
        u = urlparse(url)
        q = {k: v[0] for k, v in parse_qs(u.query, keep_blank_values=True).items()}
        out.append(dict(id=rid, base=urlunparse(u._replace(query='')), **q))
    return out


def last_request(cur):
    b.api.admin(cur)
    return one(cur, 'select coalesce(max(id),0) from net.http_request_queue')


def fabric(cur, minimum, label='WA'):
    t = master.tag()
    created = master.create(cur, 'FABRIC', master.fabric_fields(label + '-' + t, name='Kain ' + label + ' ' + t, minimum_stock_qty=str(minimum)))
    b.api.admin(cur)
    return str(created['id'])


def receive(cur, today, material, qty):
    """Stock for the fabric through Pembelian & Penerimaan (save draft, post)."""
    f = receipt.fixture(cur, today, qty=str(qty))
    f['payload']['lines'][0]['material_id'] = material
    d = receipt.command(cur, 'SAVE_DRAFT', f['payload'])
    receipt.post(cur, d)
    b.api.admin(cur)


def ar_overdue(cur, today):
    """A sale of 20 x 25 due yesterday, posted, 200 paid: 300 open (the rule-source fixture without its capture)."""
    f = sales.fixture(cur, today, qty=20, price='25', stock=30)
    version = one(cur, 'select row_version from erp.sales_headers where id=%s', (f['sale'],))
    p = dict(sale_id=f['sale'], sale_number=f['tag'], customer_id=f['customer'], source_location_id=f['location'], sale_date=f['sale_at'],
             due_date=(today - timedelta(days=1)).isoformat(), reason='WA overdue receivable fixture',
             items=[dict(product_id=f['product'], qty_pcs=20, unit_price_snapshot='25', discount_amount='0')])
    f['draft'] = b.chain.production.rpc(cur, 'erp.save_sale_draft_v2', p, uuid.uuid4(), version)
    b.api.admin(cur)
    sales.fg.post_sale(cur, f['draft'])
    sales.payment(cur, f, today, '200')
    b.api.admin(cur)
    f['key'] = 'AR:' + f['sale']
    f['party'] = one(cur, 'select customer_name from erp.customers where id=%s', (f['customer'],))
    return f


def ap_overdue(cur, today):
    """A supplier receipt of 20 x 25 with its final invoice due yesterday: 500 open."""
    f = invoice.fixture(cur, today, qty='20', price='25')
    payables.finalize(cur, f, today)
    b.api.admin(cur)
    f['key'] = 'AP_MATERIAL:' + f['receipt']['purchase_id']
    f['party'] = one(cur, 'select supplier_name from erp.suppliers where id=%s', (f['payload']['supplier_id'],))
    return f


def reminder(cur, subject, title, due, note=''):
    r = rpc(cur, 'erp_save_my_reminder_v1', (json.dumps(dict(title=title, note=note, due_at=due.isoformat(), priority='NORMAL', module='Operasional')),
                                            str(uuid.uuid4()), None), subject)
    return r['reminder']


def now(cur):
    b.api.admin(cur)
    return one(cur, 'select clock_timestamp()')


def hours_without_now(cur):
    """Analysis hours (start, end) that do not contain the current WIB time."""
    b.api.admin(cur)
    h = one(cur, "select extract(hour from clock_timestamp() at time zone 'Asia/Jakarta')::integer")
    return ('00:00', '%02d:00' % h) if h >= 1 else ('02:00', '23:59')


def past_midnight_if_close(cur, margin=180):
    """Within margin seconds of WIB midnight, wait until the new day has begun."""
    b.api.admin(cur)
    left = float(one(cur, "select extract(epoch from date_trunc('day',clock_timestamp() at time zone 'Asia/Jakarta')+interval'1 day'"
                          "-(clock_timestamp() at time zone 'Asia/Jakarta'))"))
    if left < margin:
        time.sleep(left + 2)


def alerts(cur, kind, state='OPEN'):
    b.api.admin(cur)
    rows = cur.execute('select subject_key,episode,title,detail,party_names,resolution,id::text from cp7_alert_native.alerts where kind=%s and state=%s',
                       (kind, state)).fetchall()
    return {r[0]: dict(episode=r[1], title=r[2], detail=r[3], party_names=r[4], resolution=r[5], id=r[6]) for r in rows}


def outbox(cur, item_id=None):
    b.api.admin(cur)
    rows = cur.execute("""select o.id,o.item_kind,o.item_id::text,o.item_episode,o.round,o.alert_kind,o.state,o.reason,o.dispatch_id,o.attempts
        from cp7_alert_native.outbox o where %s::uuid is null or o.item_id=%s::uuid order by o.id""", (item_id, item_id)).fetchall()
    return [dict(id=r[0], item_kind=r[1], item_id=r[2], episode=r[3], round=r[4], kind=r[5], state=r[6], reason=r[7], dispatch=r[8], attempts=r[9])
            for r in rows]


def alert_item(cur, kind, subject):
    b.api.admin(cur)
    return one(cur, "select id::text from cp7_alert_native.alerts where kind=%s and subject_key=%s and state='OPEN'", (kind, subject))


def dispatch(cur, did):
    b.api.admin(cur)
    r = cur.execute('select id,kind,status,body,net_request_id,http_status,provider_text,resolved_outcome from cp7_alert_native.dispatches where id=%s',
                    (did,)).fetchone()
    return dict(id=r[0], kind=r[1], status=r[2], body=r[3], net=r[4], http=r[5], text=r[6], resolved=r[7])


def source_errors(cur):
    b.api.admin(cur)
    return cur.execute('select kind,last_error from cp7_alert_native.source_state where last_error is not null').fetchall()


def wa_num(d):
    """A number as the message writes it (cp7_alert_native.num: two decimals at most, no trailing zeros, comma)."""
    return format(D(d).quantize(D('0.01'), rounding=ROUND_HALF_UP).normalize(), 'f').replace('.', ',')


def drain(cur, bound=400):
    """Analysis ticks until the owner's latest run is worked through (or nothing is left to do); the outcomes in order."""
    outs = []
    for _ in range(bound):
        out = tick(cur, 'analysis_tick')
        outs.append(out['outcome'])
        if out['outcome'] not in ('CONDITION_SET_STEP', 'ANALYSIS_CHECKING'):
            return outs
    raise AssertionError(('WAF_ANALYSIS_DID_NOT_FINISH', outs[-5:]))


def visible(cur, subject):
    """The kinds Pengingat sistem may show this user: the permissions of the source screens (independent of the module)."""
    b.api.admin(cur)
    keys = {r[0] for r in cur.execute('select p.permission_key from erp.app_role_permissions p join erp.app_users u on u.role_id=p.role_id '
                                      'where u.auth_user_id=%s', (subject,)).fetchall()}
    out = set()
    if {'warehouse.material.view', 'master.fabric.view'} <= keys:
        out.add('FABRIC_BELOW_MINIMUM')
    if 'warehouse.fg.view' in keys:
        out.add('FG_AT_REORDER_POINT')
    if 'finance.ar.view' in keys:
        out.add('AR_DUE')
    if 'finance.ap.view' in keys:
        out.add('AP_DUE')
    if PLANNING <= keys:
        out |= set(ANALYSIS)
    return out


def summary_low(cur, owner):
    s = rpc(cur, 'erp_cp7_get_warehouse_summary_v1', (json.dumps(dict(limit=1)),), owner)
    return next(x for x in s['attention'] if x['kind'] == 'FABRIC_BELOW_MINIMUM')


def raw_low(cur):
    """Independent oracle: active FABRIC with a minimum above zero whose summed movements (all locations, physical at or
    before now) are under the minimum."""
    b.api.admin(cur)
    rows = cur.execute("""select m.id::text,fp.minimum_stock_qty,
         coalesce((select sum(sm.qty_signed) from erp.material_stock_movements sm where sm.material_id=m.id and sm.physical_at<=statement_timestamp()),0)
        from erp.materials m join erp.fabric_master_profiles fp on fp.material_id=m.id
        where m.material_type='FABRIC' and m.is_active and fp.minimum_stock_qty>0""").fetchall()
    return {r[0]: (D(r[2]), D(r[1])) for r in rows if D(r[2]) < D(r[1])}


def cases(cur, today):
    def waits_for_owner():
        pg_net(cur)
        b.api.admin(cur)
        before = one(cur, 'select count(*) from cp7_alert_native.alerts')
        first = tick(cur, 'collect_tick')
        assert first['outcome'] == 'NOT_CONFIGURED' and before == 0 and one(cur, 'select count(*) from cp7_alert_native.alerts') == 0, first
        staff = master.role_actor(cur, 'GUDANG')
        assert refusal(cur, lambda: rpc(cur, 'erp_cp7_save_wa_settings_v1', (settings_payload(0), str(uuid.uuid4())), staff)) == ('42501', 'CP7_WA_OWNER_ONLY')
        owner = master.role_actor(cur, 'OWNER')
        key = str(uuid.uuid4())
        saved = rpc(cur, 'erp_cp7_save_wa_settings_v1', (settings_payload(0), key), owner)
        replay = rpc(cur, 'erp_cp7_save_wa_settings_v1', (settings_payload(0), key), owner)
        assert saved['settings']['revision'] == 1 and replay['replay'] is True and replay['settings'] == saved['settings'], (saved, replay)
        assert refusal(cur, lambda: rpc(cur, 'erp_cp7_save_wa_settings_v1', (settings_payload(0, max_items=5), key), owner))[1] == 'CP7_WA_REQUEST_REUSED'
        assert refusal(cur, lambda: rpc(cur, 'erp_cp7_save_wa_settings_v1', (settings_payload(0), str(uuid.uuid4())), owner))[1] == 'CP7_WA_SETTINGS_STALE'
        assert refusal(cur, lambda: rpc(cur, 'erp_cp7_save_wa_settings_v1', (settings_payload(1, quiet_enabled=True, digest_times=['22:00']),
                                                                             str(uuid.uuid4())), owner))[1] == 'CP7_WA_DIGEST_IN_QUIET_HOURS'
        assert refusal(cur, lambda: rpc(cur, 'erp_cp7_save_wa_settings_v1', (settings_payload(1, enabled=True), str(uuid.uuid4())), owner))[1] \
            == 'CP7_WA_ENABLE_NEEDS_PHONE_AND_KEY'
        assert refusal(cur, lambda: rpc(cur, 'erp_cp7_save_wa_settings_v1', (settings_payload(1, repeat_minutes=30), str(uuid.uuid4())), owner))[1] \
            == 'CP7_WA_SETTINGS_INVALID'
        assert refusal(cur, lambda: cur.execute('update cp7_alert_native.settings set enabled=true'))[1] == 'CP7_ALERT_APPEND_ONLY'
        second = tick(cur, 'collect_tick')
        assert second['outcome'] == 'COLLECTED' and source_errors(cur) == [], (second, source_errors(cur))
        return dict(status='PASS', before_settings='NOT_CONFIGURED', staff_refused='42501', replay_same=True, reused_request_refused=True,
                    stale_refused=True, digest_in_quiet_refused=True, enable_without_key_refused=True, invalid_repeat_refused=True,
                    settings_append_only=True, after_settings=second['outcome'], kinds_read_without_error=sorted(second['kinds']))

    def fabric_equals_summary():
        s = setup(cur, enabled=False)
        below = fabric(cur, 50)
        above = fabric(cur, 5)
        receive(cur, today, above, 10)
        partly = fabric(cur, 20)
        receive(cur, today, partly, 10)
        out = tick(cur, 'collect_tick')
        assert out['kinds']['FABRIC_BELOW_MINIMUM'].get('error') is None, out
        open_ = alerts(cur, 'FABRIC_BELOW_MINIMUM')
        oracle = raw_low(cur)
        assert set(open_) == set(oracle) and {below, partly} <= set(open_) and above not in open_, (sorted(open_), sorted(oracle))
        for k, (qty, minimum) in oracle.items():
            assert D(open_[k]['detail']['qty']) == qty and D(open_[k]['detail']['minimum_qty']) == minimum, (k, open_[k])
        low = summary_low(cur, s['owner'])
        # Same count; the summary's first rows (its own order, database collation) are alerts with the same numbers.
        assert int(low['count']) == len(open_) and len(low['rows']) == min(10, len(open_)), (low['count'], len(open_), len(low['rows']))
        mine = {(a['detail']['material_id'], a['detail']['qty'], a['detail']['minimum_qty']) for a in open_.values()}
        assert {(r['material_id'], r['qty'], r['minimum_qty']) for r in low['rows']} <= mine, (low['rows'], sorted(mine)[:10])
        assert open_[below]['detail']['qty'] == '0' and D(open_[partly]['detail']['qty']) == 10 and open_[below]['party_names'] == []
        receive(cur, today, below, 60)
        tick(cur, 'collect_tick')
        gone = alerts(cur, 'FABRIC_BELOW_MINIMUM', 'RESOLVED')
        after = alerts(cur, 'FABRIC_BELOW_MINIMUM')
        assert below in gone and gone[below]['resolution'] == 'AT_OR_ABOVE_MINIMUM' and below not in after and set(after) == set(raw_low(cur))
        assert int(summary_low(cur, s['owner'])['count']) == len(after)
        return dict(status='PASS', open_equals_raw_movements=len(open_), equals_summary_count_and_first_rows=True, above_minimum_not_open=True,
                    received_stock_resolves='AT_OR_ABOVE_MINIMUM', fixtures=dict(below=below, partly=partly, above=above))

    def ar_ap_sources():
        setup(cur, enabled=False)
        ar = ar_overdue(cur, today)
        ap = ap_overdue(cur, today)
        out = tick(cur, 'collect_tick')
        assert out['kinds']['AR_DUE'].get('error') is None and out['kinds']['AP_DUE'].get('error') is None, out
        a = alerts(cur, 'AR_DUE')[ar['key']]
        assert a['detail']['open_balance'] == '300.00' and a['detail']['due_date'] == (today - timedelta(days=1)).isoformat() \
            and a['detail']['state'] == 'OVERDUE' and a['party_names'] == [ar['party']] and ar['party'] not in a['title'], a
        p = alerts(cur, 'AP_DUE')[ap['key']]
        assert D(p['detail']['remaining']) == D('500') and p['detail']['state'] == 'OVERDUE' and p['party_names'] == [ap['party']] \
            and ap['party'] not in p['title'], p
        final = sales.payment(cur, dict(ar, tag=ar['tag'] + '-final'), today, '300')
        payables.payment(cur, ap, today, '500')
        b.api.admin(cur)
        tick(cur, 'collect_tick')
        assert alerts(cur, 'AR_DUE', 'RESOLVED')[ar['key']]['resolution'] == 'ZERO_BALANCE'
        assert alerts(cur, 'AP_DUE', 'RESOLVED')[ap['key']]['resolution'] == 'ZERO_BALANCE'
        assert ar['key'] not in alerts(cur, 'AR_DUE') and ap['key'] not in alerts(cur, 'AP_DUE')
        sales.native(cur, 'select erp.reverse_sales_payment(%s,%s)', (final, 'WA reopened receivable'))
        tick(cur, 'collect_tick')
        again = alerts(cur, 'AR_DUE')[ar['key']]
        assert again['episode'] == 2 and again['detail']['open_balance'] == '300.00', again
        assert [o['round'] for o in outbox(cur, again['id'])] == [0]
        return dict(status='PASS', receivable_open_300_overdue=True, payable_open_500_overdue=True, party_names_kept_apart=True,
                    paid_resolves='ZERO_BALANCE', payment_reversed_new_episode=2)

    def owner_reminders_only():
        s = setup(cur, enabled=False)
        # Another internal user with reminders of their own (the Native actor rule lets only OWNER, ADMIN and STAFF keep them).
        staff = master.role_actor(cur, 'ADMIN')
        t = now(cur)
        due = reminder(cur, s['owner'], 'WA bayar listrik', t - timedelta(minutes=5))
        later = reminder(cur, s['owner'], 'WA rapat besok', t + timedelta(days=1))
        theirs = reminder(cur, staff, 'WA catatan staf', t - timedelta(minutes=5), 'rahasia staf')
        out = tick(cur, 'collect_tick')
        mine = outbox(cur, due['id'])
        assert out['manual_queued'] >= 1 and len(mine) == 1 and mine[0]['kind'] == 'MANUAL_REMINDER' and mine[0]['round'] == 0, (out, mine)
        assert outbox(cur, later['id']) == [] and outbox(cur, theirs['id']) == []
        tick(cur, 'collect_tick')
        assert len(outbox(cur, due['id'])) == 1, 'WAF_REMINDER_QUEUED_TWICE'
        moved = rpc(cur, 'erp_save_my_reminder_v1', (json.dumps(dict(id=due['id'], title='WA bayar listrik', note='', due_at=(t - timedelta(minutes=1)).isoformat(),
                                                                       priority='NORMAL', module='Operasional')), str(uuid.uuid4()), int(due['row_version'])),
                    s['owner'])
        tick(cur, 'collect_tick')
        rows = outbox(cur, due['id'])
        assert len(rows) == 2 and rows[0]['episode'] != rows[1]['episode'], rows
        b.api.admin(cur)
        staff_text = one(cur, "select count(*) from cp7_alert_native.outbox o join erp.manual_reminders r on r.id=o.item_id where r.owner_user_id<>%s::uuid",
                         (s['user'],))
        assert staff_text == 0
        return dict(status='PASS', owner_due_queued_once=True, future_not_queued=True, staff_never_read=True, rescheduled_new_episode=True,
                    moved_version=moved['reminder']['row_version'])

    def send_one_request():
        setup(cur)
        mat = fabric(cur, 40, 'WAKIRIM')
        tick(cur, 'collect_tick')
        before = last_request(cur)
        pending = [o for o in outbox(cur) if o['state'] == 'PENDING']
        out = tick(cur, 'send_tick')
        assert out['outcome'] == 'SENT' and out['items'] == len(pending), (out, len(pending))
        d = dispatch(cur, out['dispatch_id'])
        reqs = queued(cur, before)
        assert len(reqs) == 1 and reqs[0]['id'] == d['net'] and reqs[0]['base'] == FAKE and reqs[0]['phone'] == PHONE and reqs[0]['apikey'] == KEY, \
            [dict(r, apikey='?') for r in reqs]
        assert reqs[0]['text'] == d['body'] and d['status'] == 'QUEUED' and d['kind'] == 'INSTANT', d
        name = one(cur, 'select material_name from erp.materials where id=%s', (mat,))
        lines = d['body'].split('\n')
        assert lines[0].startswith('⚠ ERP Enteng · ') and lines[-1] == 'Buka ERP > Reminder' and len(d['body']) <= 1000, lines
        assert '- ' + name + ': sisa 0 YD, minimum 40 YD' in lines or any(l.startswith('- dan ') for l in lines), lines
        rows = outbox(cur)
        sent = [o for o in rows if o['dispatch'] == d['id']]
        assert len(sent) == len(pending) and all(o['state'] == 'DISPATCHED' and o['attempts'] == 1 for o in sent)
        b.api.admin(cur)
        assert one(cur, 'select count(*) from cp7_alert_native.dispatch_items where dispatch_id=%s', (d['id'],)) == len(pending)
        return dict(status='PASS', one_request=True, phone_text_key_decoded=True, text_equals_body=True, items=len(pending),
                    header=lines[0][:14], max_chars=len(d['body']))

    def rollback_nothing():
        setup(cur)
        tick(cur, 'collect_tick')
        tick(cur, 'send_tick')
        age_dispatches(cur, 2)
        b.api.admin(cur)
        counts = lambda: tuple(one(cur, 'select count(*) from ' + t) for t in ('cp7_alert_native.alerts', 'cp7_alert_native.outbox',
                                                                               'cp7_alert_native.dispatches', 'net.http_request_queue'))
        before = counts()
        cur.execute('savepoint waf_rollback')
        fabric(cur, 70, 'WABATAL')
        tick(cur, 'collect_tick')
        out = tick(cur, 'send_tick')
        inside = counts()
        cur.execute('rollback to savepoint waf_rollback')
        b.api.admin(cur)
        after = counts()
        assert out['outcome'] == 'SENT' and inside[0] > before[0] and inside[3] > before[3] and after == before, (before, inside, after, out)
        return dict(status='PASS', inside=inside, after_rollback=after, request_gone_with_transaction=True)

    def resolved_before_send():
        s = setup(cur)
        tick(cur, 'collect_tick')
        tick(cur, 'send_tick')
        age_dispatches(cur, 2)
        mat = fabric(cur, 30, 'WABERES')
        rem = reminder(cur, s['owner'], 'WA sudah beres', now(cur) - timedelta(minutes=2))
        tick(cur, 'collect_tick')
        item = alert_item(cur, 'FABRIC_BELOW_MINIMUM', mat)
        assert [o['state'] for o in outbox(cur, item)] == ['PENDING'] and [o['state'] for o in outbox(cur, rem['id'])] == ['PENDING']
        receive(cur, today, mat, 30)
        rpc(cur, 'erp_set_my_reminder_done_v1', (rem['id'], True, str(uuid.uuid4()), int(rem['row_version'])), s['owner'])
        out = tick(cur, 'send_tick')
        a, r = outbox(cur, item)[0], outbox(cur, rem['id'])[0]
        assert (a['state'], a['reason'], a['dispatch']) == ('RESOLVED_BEFORE_SEND', 'AT_OR_ABOVE_MINIMUM', None), a
        assert (r['state'], r['reason'], r['dispatch']) == ('RESOLVED_BEFORE_SEND', 'REMINDER_DONE', None), r
        b.api.admin(cur)
        assert one(cur, 'select count(*) from cp7_alert_native.dispatch_items where outbox_id in (%s,%s)', (a['id'], r['id'])) == 0
        return dict(status='PASS', stock_received_before_send=a['reason'], reminder_done_before_send=r['reason'], tick=out['outcome'])

    def answers():
        s = setup(cur)
        fabric(cur, 15, 'WAAWAL')
        tick(cur, 'collect_tick')
        first = tick(cur, 'send_tick')
        assert first['outcome'] == 'SENT', first
        answer(cur, first['dispatch_id'], 200, 'Message queued apikey=' + KEY)
        tick(cur, 'send_tick')
        d = dispatch(cur, first['dispatch_id'])
        assert (d['status'], d['http']) == ('PROVIDER_ACCEPTED', 200) and KEY not in d['text'] and '***' in d['text'], d
        assert all(o['state'] == 'ACCEPTED' for o in outbox(cur) if o['dispatch'] == d['id'])
        results = {}
        for label, status, error, expect, outbox_state in (('refused', 500, None, 'PROVIDER_REFUSED', 'PENDING'),
                                                           ('no_route', None, "Couldn't resolve host name", 'TRANSPORT_FAILED', 'PENDING'),
                                                           ('timeout', None, 'Timeout was reached', 'UNKNOWN', 'UNKNOWN')):
            age_dispatches(cur, 10)
            mat = fabric(cur, 15, 'WA' + label.upper().replace('_', ''))
            tick(cur, 'collect_tick')
            out = tick(cur, 'send_tick')
            assert out['outcome'] == 'SENT', (label, out)
            answer(cur, out['dispatch_id'], status, 'error' if status else None, label == 'timeout', error)
            waiting = tick(cur, 'send_tick')
            d = dispatch(cur, out['dispatch_id'])
            mine = outbox(cur, alert_item(cur, 'FABRIC_BELOW_MINIMUM', mat))[0]
            assert d['status'] == expect and mine['state'] == outbox_state, (label, d, mine)
            if expect != 'UNKNOWN':
                assert waiting['outcome'] == 'WAITING' and mine['reason'] == expect, (label, waiting, mine)
                age_dispatches(cur, 6)
                again = tick(cur, 'send_tick')
                resent = outbox(cur, alert_item(cur, 'FABRIC_BELOW_MINIMUM', mat))[0]
                assert again['outcome'] == 'SENT' and resent['state'] == 'DISPATCHED' and resent['attempts'] == 2, (label, again, resent)
                answer(cur, again['dispatch_id'], 200, 'Message queued')
                tick(cur, 'send_tick')
            results[label] = expect
        silent = tick(cur, 'send_tick')
        age_dispatches(cur, 11)
        mat = fabric(cur, 15, 'WADIAM')
        tick(cur, 'collect_tick')
        out = tick(cur, 'send_tick')
        age_dispatches(cur, 11)
        tick(cur, 'send_tick')
        d = dispatch(cur, out['dispatch_id'])
        assert d['status'] == 'UNKNOWN' and outbox(cur, alert_item(cur, 'FABRIC_BELOW_MINIMUM', mat))[0]['state'] == 'UNKNOWN', d
        staff = master.role_actor(cur, 'GUDANG')
        payload = json.dumps(dict(dispatch_id=d['id'], outcome='NOT_DELIVERED'))
        assert refusal(cur, lambda: rpc(cur, 'erp_cp7_resolve_wa_dispatch_v1', (payload, str(uuid.uuid4())), staff))[0] == '42501'
        rkey = str(uuid.uuid4())
        resolved = rpc(cur, 'erp_cp7_resolve_wa_dispatch_v1', (payload, rkey), s['owner'])
        assert resolved['resolved_outcome'] == 'NOT_DELIVERED' and rpc(cur, 'erp_cp7_resolve_wa_dispatch_v1', (payload, rkey), s['owner'])['replay'] is True
        assert outbox(cur, alert_item(cur, 'FABRIC_BELOW_MINIMUM', mat))[0]['state'] == 'PENDING'
        assert refusal(cur, lambda: rpc(cur, 'erp_cp7_resolve_wa_dispatch_v1', (payload, str(uuid.uuid4())), s['owner']))[1] == 'CP7_WA_RESOLVE_NOT_UNKNOWN'
        results['silence_10_minutes'] = 'UNKNOWN'
        return dict(status='PASS', accepted_key_masked=True, results=results, refused_rest_then_resent=True, unknown_never_resent=True,
                    owner_not_delivered_waits_again=True, staff_resolve_refused=True, silent_tick=silent['outcome'], label='SYNTHETIC_PROVIDER_ANSWER')

    def pacing_burst_quiet_digest_repeat():
        s = setup(cur, burst_after_per_day=1, burst_merge_minutes=30)
        fabric(cur, 25, 'WAAWAL')
        tick(cur, 'collect_tick')
        first = tick(cur, 'send_tick')
        assert first['outcome'] == 'SENT', first
        answer(cur, first['dispatch_id'], 200, 'Message queued')
        tick(cur, 'send_tick')
        fabric(cur, 25, 'WAPACE')
        tick(cur, 'collect_tick')
        assert tick(cur, 'send_tick')['outcome'] == 'WAITING'
        age_dispatches(cur, 2)
        burst = tick(cur, 'send_tick')
        assert burst['outcome'] == 'WAITING' and burst['sent_today'] == 1, burst
        age_dispatches(cur, 31)
        merged = tick(cur, 'send_tick')
        assert merged['outcome'] == 'SENT', merged
        answer(cur, merged['dispatch_id'], 200, 'Message queued')
        tick(cur, 'send_tick')
        # Quiet hours around now (WIB): held, nothing queued; switched off: sent.
        age_dispatches(cur, 31)
        wib = one(cur, "select (clock_timestamp() at time zone 'Asia/Jakarta')")
        quiet = dict(quiet_enabled=True, quiet_start=(wib - timedelta(hours=1)).strftime('%H:%M'), quiet_end=(wib + timedelta(hours=1)).strftime('%H:%M'))
        save(cur, s['owner'], **dict(quiet, enabled=True, burst_after_per_day=200))
        fabric(cur, 25, 'WATENANG')
        tick(cur, 'collect_tick')
        before = last_request(cur)
        held = tick(cur, 'send_tick')
        assert held['outcome'] == 'HELD_QUIET' and queued(cur, before) == [] and any(o['state'] == 'HELD_QUIET' for o in outbox(cur)), held
        save(cur, s['owner'], enabled=True, burst_after_per_day=200)
        released = tick(cur, 'send_tick')
        assert released['outcome'] == 'SENT' and len(queued(cur, before)) == 1, released
        answer(cur, released['dispatch_id'], 200, 'Message queued')
        tick(cur, 'send_tick')
        # Digest at the current WIB minute, WhatsApp switched on five minutes earlier (TEST_CLOCK_OVERRIDE on saved_at).
        slot = one(cur, "select to_char(clock_timestamp() at time zone 'Asia/Jakarta','HH24:MI')")
        save(cur, s['owner'], enabled=True, burst_after_per_day=200, digest_times=[slot])
        test_clock(cur, "update cp7_alert_native.settings set saved_at=saved_at-interval'5 minutes'")
        age_dispatches(cur, 2)
        digest = tick(cur, 'send_tick')
        assert digest['outcome'] == 'DIGEST', digest
        d = dispatch(cur, digest['dispatch_id'])
        b.api.admin(cur)
        open_count = one(cur, "select count(*) from cp7_alert_native.alerts where state='OPEN'")
        assert d['kind'] == 'DIGEST' and d['body'].startswith('\U0001f4cb Ringkasan ERP Enteng · ') and digest['items'] >= open_count, (d, open_count)
        age_dispatches(cur, 2)
        assert tick(cur, 'send_tick')['outcome'] in ('IDLE', 'WAITING'), 'WAF_DIGEST_TWICE_IN_ONE_SLOT'
        answer(cur, d['id'], 200, 'Message queued')
        tick(cur, 'send_tick')
        # Repeat: accepted 25 hours ago and still open -> one more round, "Masih terbuka".
        save(cur, s['owner'], enabled=True, burst_after_per_day=200)
        test_clock(cur, "update cp7_alert_native.outbox set settled_at=settled_at-interval'25 hours' where state='ACCEPTED'")
        age_dispatches(cur, 2)
        rep = tick(cur, 'send_tick')
        assert rep['repeats'] >= 1 and rep['outcome'] == 'SENT', rep
        rounds = [o for o in outbox(cur) if o['round'] == 1]
        assert rounds and all(o['state'] == 'DISPATCHED' for o in rounds)
        assert dispatch(cur, rep['dispatch_id'])['body'].startswith('\U0001f501 Masih terbuka')
        return dict(status='PASS', one_per_minute=True, burst_after_1_then_30_minutes=True, quiet_held_then_sent=True, digest_once_per_slot=True,
                    repeat_after_24h=len(rounds), label='TEST_CLOCK_OVERRIDE+SYNTHETIC_PROVIDER_ANSWER')

    def off_or_no_key():
        s = setup(cur, enabled=False)
        fabric(cur, 45, 'WAMATI')
        tick(cur, 'collect_tick')
        before = last_request(cur)
        off = tick(cur, 'send_tick')
        assert off['outcome'] == 'WA_OFF' and queued(cur, before) == [] and all(o['state'] == 'DISABLED' for o in outbox(cur)), off
        save(cur, s['owner'], enabled=True)
        b.api.admin(cur)
        cur.execute("delete from vault.secrets where name='cp7_callmebot_apikey'")
        fabric(cur, 45, 'WATANPAKUNCI')
        tick(cur, 'collect_tick')
        nokey = tick(cur, 'send_tick')
        assert nokey['outcome'] == 'KEY_MISSING' and queued(cur, before) == [] and all(o['state'] == 'DISABLED' for o in outbox(cur)), nokey
        assert refusal(cur, lambda: rpc(cur, 'erp_cp7_send_wa_test_v1', (str(uuid.uuid4()),), s['owner']))[1] == 'CP7_WA_KEY_MISSING'
        return dict(status='PASS', wa_off_disabled=True, key_missing_disabled=True, test_refused_without_key=True, requests=0)

    def key_write_only():
        s = setup(cur)
        fabric(cur, 15, 'WAKUNCI')
        tick(cur, 'collect_tick')
        out = tick(cur, 'send_tick')
        answer(cur, out['dispatch_id'], 200, 'Message queued apikey=' + KEY)
        tick(cur, 'send_tick')
        test = rpc(cur, 'erp_cp7_send_wa_test_v1', (str(uuid.uuid4()),), s['owner'])
        read = rpc(cur, 'erp_cp7_get_wa_settings_v1', (), s['owner'])
        listed = rpc(cur, 'erp_cp7_get_alerts_v1', (json.dumps({}),), s['owner'])
        assert read['key_present'] is True and KEY not in json.dumps(read) and KEY not in json.dumps(listed), 'WAF_KEY_IN_ANSWER'
        b.api.admin(cur)
        tables = [r[0] for r in cur.execute("""select c.oid::regclass::text from pg_class c join pg_namespace n on n.oid=c.relnamespace
            where c.relkind='r' and (n.nspname in('erp','public') or n.nspname like 'cp7%%')""").fetchall()]
        leaks = [t for t in tables if one(cur, 'select count(*) from ' + t + ' x where strpos(to_jsonb(x)::text,%s)>0', (KEY,))]
        assert leaks == [], leaks
        assert one(cur, "select count(*) from vault.decrypted_secrets where name='cp7_callmebot_apikey' and decrypted_secret=%s", (KEY,)) == 1
        for who in ('anon', 'authenticated', 'service_role'):
            for sig in bundle.KEY_FUNCTIONS:
                assert not one(cur, "select has_function_privilege(%s,%s,'EXECUTE')", (who, 'cp7_alert_native.' + sig)), (who, sig)
        rkey = str(uuid.uuid4())
        rpc(cur, 'erp_cp7_set_wa_key_v1', ('FAKEKEY-WA3B-2', rkey), s['owner'])
        replay = rpc(cur, 'erp_cp7_set_wa_key_v1', ('FAKEKEY-OTHER', rkey), s['owner'])
        b.api.admin(cur)
        assert replay['replay'] is True and one(cur, "select decrypted_secret from vault.decrypted_secrets where name='cp7_callmebot_apikey'") == 'FAKEKEY-WA3B-2'
        assert refusal(cur, lambda: rpc(cur, 'erp_cp7_set_wa_key_v1', ('bad key!', str(uuid.uuid4())), s['owner']))[1] == 'CP7_WA_KEY_FORMAT'
        return dict(status='PASS', tables_scanned=len(tables), key_in_no_table=True, key_in_no_answer=True, provider_text_masked=True,
                    vault_holds_key=True, key_functions_private=True, replayed_request_keeps_first_key=True, test_dispatch=test['dispatch_id'])

    def privacy_permissions():
        s = setup(cur)
        ar = ar_overdue(cur, today)
        ap = ap_overdue(cur, today)
        tick(cur, 'collect_tick')
        out = tick(cur, 'send_tick')
        body = dispatch(cur, out['dispatch_id'])['body']
        assert ar['party'] not in body and ap['party'] not in body and 'Piutang pelanggan jatuh tempo: ' in body and 'Tagihan supplier jatuh tempo: ' in body, body
        answer(cur, out['dispatch_id'], 200, 'Message queued')
        tick(cur, 'send_tick')
        save(cur, s['owner'], enabled=True, detail='DETAILED', max_items=20)
        test_clock(cur, "update cp7_alert_native.outbox set settled_at=settled_at-interval'25 hours' where state='ACCEPTED'")
        age_dispatches(cur, 2)
        detailed = tick(cur, 'send_tick')
        dbody = dispatch(cur, detailed['dispatch_id'])['body']
        assert detailed['outcome'] == 'SENT' and (ar['party'] in dbody or '- dan ' in dbody), dbody
        owner_view = rpc(cur, 'erp_cp7_get_alerts_v1', (json.dumps({}),), s['owner'])
        assert {'FABRIC_BELOW_MINIMUM', 'FG_AT_REORDER_POINT', 'AR_DUE', 'AP_DUE', 'PRODUCTION_GAP', 'FABRIC_NEED'} == {k['kind'] for k in owner_view['kinds']} \
            == visible(cur, s['owner']), owner_view['kinds']
        assert any(r['wa'] is not None for r in owner_view['rows'])
        staff = master.role_actor(cur, 'GUDANG')
        expect = visible(cur, staff)
        staff_view = rpc(cur, 'erp_cp7_get_alerts_v1', (json.dumps({}),), staff)
        assert {k['kind'] for k in staff_view['kinds']} == expect and {r['kind'] for r in staff_view['rows']} <= expect, (expect, staff_view['kinds'])
        assert all(r['wa'] is None for r in staff_view['rows']) and (staff_view['analysis'] is None) == ('PRODUCTION_GAP' not in expect), staff_view['analysis']
        for name, args in (('erp_cp7_get_wa_settings_v1', ()), ('erp_cp7_send_wa_test_v1', (str(uuid.uuid4()),)),
                           ('erp_cp7_set_wa_key_v1', ('FAKEKEY-STAFF', str(uuid.uuid4())))):
            assert refusal(cur, lambda name=name, args=args: rpc(cur, name, args, staff)) == ('42501', 'CP7_WA_OWNER_ONLY'), name
        b.api.admin(cur)
        for sig in bundle.PUBLIC:
            assert not one(cur, "select has_function_privilege('anon',%s,'EXECUTE')", (sig,)), sig
        return dict(status='PASS', summary_hides_party_names=True, detailed_shows_them=True, owner_sees_six_kinds=True,
                    staff_kinds=sorted(expect), staff_no_wa_status=True, staff_refused_on_owner_rpcs=True, anon_no_execute=True)

    def ticks_private():
        setup(cur)
        details = {}
        for bad in ('0', '9s', '1h'):
            state, message = refusal(cur, lambda bad=bad: tick(cur, 'send_tick', bad))
            assert (state, message) == ('55000', 'CP7_ALERT_STATEMENT_LIMIT_REQUIRED'), (bad, state, message)
            details[bad] = state
        assert tick(cur, 'collect_tick', '3s')['outcome'] == 'COLLECTED'
        b.api.admin(cur)
        defs = one(cur, 'select cp7_alert_native.schedules()')
        unit = 'begin; select cp7_alert_native.analysis_tick(); commit;'
        commands = {'erp-wa-collect': "set statement_timeout to '8s'; select cp7_alert_native.collect_tick()",
                    'erp-wa-send': "set statement_timeout to '8s'; select cp7_alert_native.send_tick()",
                    'erp-wa-analysis': "set statement_timeout to '8s'; " + ' '.join([unit] * 6)}
        assert [d['name'] for d in defs] == SCHEDULES and all(d['schedule'] == '* * * * *' and d['timezone'] == 'UTC' and d['command'] == commands[d['name']]
                                                             for d in defs), defs
        state, message = refusal(cur, lambda: tick(cur, 'analysis_tick', '0'))
        assert (state, message) == ('55000', 'CP7_ALERT_STATEMENT_LIMIT_REQUIRED'), (state, message)
        for sig in ('cp7_alert_native.collect_tick()', 'cp7_alert_native.send_tick()', 'cp7_alert_native.analysis_tick()'):
            assert one(cur, "select has_function_privilege('postgres',%s,'EXECUTE')", (sig,))
            for who in ('anon', 'authenticated', 'service_role'):
                assert not one(cur, "select has_function_privilege(%s,%s,'EXECUTE')", (who, sig)), (who, sig)
        state, _ = refusal(cur, lambda: (cur.execute("select set_config('statement_timeout','8s',true)"), cur.execute('set local role authenticated'),
                                         cur.execute('select cp7_alert_native.send_tick()')))
        assert state == '42501', state
        assert one(cur, "select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname like '%%tick%%'") == 0
        if one(cur, "select to_regclass('cron.job') is not null"):
            assert one(cur, "select count(*) from cron.job where jobname like 'erp-wa-%%'") == 0
        return dict(status='PASS', refused_without_limit=details, stricter_limit_allowed=True, schedules=SCHEDULES, ticks_postgres_only=True,
                    authenticated_refused='42501', no_public_tick=True, schedule_not_installed=True)

    def analysis_gap():
        # Analysis hours that do not contain the current WIB time: they gate only a new automatic analysis, never the
        # owner's own run, which is read and checked at any hour.
        start, end = hours_without_now(cur)
        s = setup(cur, kinds=KINDS + ANALYSIS, analysis_start=start, analysis_end=end)
        first = tick(cur, 'analysis_tick')
        assert first['outcome'] == 'NO_OWNER_ANALYSIS_YET', first
        # The owner's own finished staged analysis with an open exact-size production gap; the owner's reminder rule for
        # production gaps switched on (threshold 1 PCS); no rule for fabric needs.
        x = planv2.single(cur, today, s['owner'])
        r = dict(run=x['run'], identity=remv2.identity(cur, x['run']), target=x['target'])
        remv2.policy(cur, r, 'PRODUCTION_GAP', 'PCS', subject=s['owner'])
        outs = drain(cur)
        assert outs[-1] == 'ANALYSIS_CHECKED' and 'CONDITION_SET_STEP' in outs, outs
        assert tick(cur, 'analysis_tick')['outcome'] == 'OUTSIDE_ANALYSIS_HOURS'
        key = 'PRODUCTION_GAP:' + r['target']
        rows = remv2.conditions(cur, r['run'], subject=s['owner'])
        c = remv2.row(rows, key)
        gap = D(c['value']['value'])
        assert c['state'] == 'ACTIVE' and gap >= 2, c
        # Oracle: the reminders' own read and read-only recheck, condition by condition.
        expect_open, expect_off = set(), 0
        for row in rows:
            if row['state'] != 'ACTIVE' or row['rule_id'] not in ANALYSIS:
                continue
            if row['eligibility'] not in ('LOCAL_PREVIEW_ELIGIBLE', 'QUIET', 'COOLDOWN'):
                expect_off += 1
                continue
            v = remv2.recheck(cur, r['run'], row['key'], s['owner'])
            if v['verdict'] == 'STILL_OPEN' and v['policy_binding']['policy']['config']['enabled'] is True:
                expect_open.add((row['rule_id'], row['key']))
        got = {(k, sk) for k in ANALYSIS for sk in alerts(cur, k)}
        assert got == expect_open and ('PRODUCTION_GAP', key) in got, (sorted(got), sorted(expect_open))
        assert not alerts(cur, 'FABRIC_NEED'), 'WAF_FABRIC_NEED_WITHOUT_RULE_OPENED'
        b.api.admin(cur)
        run_row = cur.execute('select phase,checked,still_open,rule_off from cp7_alert_native.analysis_runs where run_id=%s', (r['run'],)).fetchone()
        assert run_row[0] == 'DONE' and run_row[2] == len(expect_open) and run_row[3] == expect_off, (run_row, len(expect_open), expect_off)
        a = alerts(cur, 'PRODUCTION_GAP')[key]
        v = remv2.recheck(cur, r['run'], key, s['owner'])
        assert a['title'] == 'Kekurangan produksi: ' + c['label'] and a['detail']['run_id'] == r['run'] and D(a['detail']['need_now_pcs']) == gap \
            and D(v['numbers']['need_now_pcs']) == gap and a['party_names'] == [], (a, v['numbers'])
        assert [o['state'] for o in outbox(cur, a['id'])] == ['PENDING']
        # One piece found after the snapshot: the send checks again and states the need now (gap - 1), not the snapshot.
        planv2.found_fg(cur, x, 1)
        before = last_request(cur)
        sent = tick(cur, 'send_tick')
        assert sent['outcome'] == 'SENT' and sent['analysis']['checked'].get('PRODUCTION_GAP', 0) >= 1, sent
        q = queued(cur, before)
        line = c['label'] + ': kurang ' + wa_num(gap - 1) + ' pcs'
        assert len(q) == 1 and q[0]['phone'] == PHONE and 'Kekurangan produksi · analisis ' in q[0]['text'] and line in q[0]['text'], q
        assert D(alerts(cur, 'PRODUCTION_GAP')[key]['detail']['need_now_pcs']) == gap - 1
        answer(cur, sent['dispatch_id'], 200, 'Message queued')
        tick(cur, 'send_tick')
        # The rest found: the repeat a day later is checked again, resolved, never sent.
        planv2.found_fg(cur, x, int(math.ceil(gap)))
        test_clock(cur, "update cp7_alert_native.outbox set settled_at=settled_at-interval'25 hours' where state='ACCEPTED'")
        age_dispatches(cur, 2)
        before = last_request(cur)
        again = tick(cur, 'send_tick')
        mine = outbox(cur, a['id'])
        assert queued(cur, before) == [] and [o['state'] for o in mine] == ['ACCEPTED', 'RESOLVED_BEFORE_SEND'] \
            and mine[1]['reason'] == 'RECHECK_RESOLVED_NOW', (again, mine)
        gone = alerts(cur, 'PRODUCTION_GAP', 'RESOLVED')[key]
        assert gone['resolution'] == 'RECHECK_RESOLVED_NOW' and remv2.recheck(cur, r['run'], key, s['owner'])['verdict'] == 'RESOLVED_NOW', gone
        # The reminders module's own records are untouched: its rechecks here are read-only, nothing claimed.
        assert remv2.claims_of(cur, key) == 0 and remv2.rechecks_of(cur, key) == 0
        staff = master.role_actor(cur, 'GUDANG')
        staff_view = rpc(cur, 'erp_cp7_get_alerts_v1', (json.dumps(dict(resolved_days=7)),), staff)
        assert ('PRODUCTION_GAP' in {k['kind'] for k in staff_view['kinds']}) == ('PRODUCTION_GAP' in visible(cur, staff))
        return dict(status='PASS', ticks=outs[:3] + ['...', outs[-1]], set_built_by_tick=True, checked_outside_analysis_hours=[start, end],
                    opened=sorted(k for _, k in got), rule_off=expect_off, sent_need_now=str(gap - 1), snapshot_gap=str(gap),
                    resolved_before_send='RECHECK_RESOLVED_NOW', reminder_claims=0)

    def analysis_automatic():
        # 00:00-23:59 leaves out the last minute of the day; a case that would reach it waits for the new day, and the
        # business-day control runs the group again from a fresh copy.
        past_midnight_if_close(cur)
        s = setup(cur, kinds=KINDS + ANALYSIS, analysis_every_minutes=15, analysis_start='00:00', analysis_end='23:59')
        x = planv2.single(cur, today, s['owner'])
        assert drain(cur)[-1] == 'ANALYSIS_CHECKED'
        assert tick(cur, 'analysis_tick')['outcome'] == 'NOT_DUE'
        b.api.admin(cur)
        job = cur.execute('select query,request_id from cp7_analysis_stage.jobs where run_id=%s', (x['run'],)).fetchone()
        # TEST_CLOCK_OVERRIDE (labelled): the owner's finished job captured 20 minutes ago; a change recorded after it.
        test_clock(cur, "update cp7_analysis_stage.jobs set captured_at=captured_at-interval'20 minutes' where run_id=%s", (x['run'],))
        planv2.found_fg(cur, x, 1)
        due = tick(cur, 'analysis_tick')
        # Oracle: the same period length as the owner's last analysis, ending yesterday (WIB, the database clock), same grouping.
        yday = one(cur, "select ((clock_timestamp() at time zone 'Asia/Jakarta')::date-1)")
        span = date.fromisoformat(job[0]['through_date']) - date.fromisoformat(job[0]['from_date'])
        expect_q = dict(from_date=str(yday - span), through_date=str(yday), group_mode=job[0]['group_mode'])
        assert due['outcome'] == 'ANALYSIS_DUE' and due['query'] == expect_q and due['freshness'] == 'CHANGES_RECORDED', (due, expect_q)
        asked = tick(cur, 'analysis_tick')
        assert asked['outcome'] == 'ANALYSIS_REQUESTED' and asked['request_id'] == due['request_id'] and asked['job_state'] == 'RUNNING', asked
        b.api.admin(cur)
        new = cur.execute('select state,query,actor::text from cp7_analysis_stage.jobs where request_id=%s', (due['request_id'],)).fetchone()
        assert new == ('RUNNING', expect_q, s['owner']), new
        assert tick(cur, 'analysis_tick')['outcome'] == 'ANALYSIS_RUNNING'
        done, _ = remv2.staged.drive(cur, due['request_id'], s['owner'])
        assert done['state'] == 'DONE', done
        outs = drain(cur)
        assert outs[-1] == 'ANALYSIS_CHECKED', outs
        b.api.admin(cur)
        runs = cur.execute('select run_id::text,phase from cp7_alert_native.analysis_runs order by started_at').fetchall()
        assert runs == [(x['run'], 'DONE'), (done['run_id'], 'DONE')], runs
        assert tick(cur, 'analysis_tick')['outcome'] == 'NOT_DUE'
        start, end = hours_without_now(cur)
        save(cur, s['owner'], enabled=True, kinds=KINDS + ANALYSIS, analysis_every_minutes=15, analysis_start=start, analysis_end=end)
        outside = tick(cur, 'analysis_tick')['outcome']
        save(cur, s['owner'], enabled=True, kinds=KINDS + ANALYSIS, analysis_every_minutes=0, analysis_start='00:00', analysis_end='23:59')
        off = tick(cur, 'analysis_tick')['outcome']
        assert outside == 'OUTSIDE_ANALYSIS_HOURS' and off == 'AUTO_ANALYSIS_OFF', (outside, off)
        status = rpc(cur, 'erp_cp7_get_wa_settings_v1', (), s['owner'])['analysis']
        assert status['request']['request_id'] == due['request_id'] and status['request']['state'] == 'REQUESTED' and status['run']['run_id'] == done['run_id']
        return dict(status='PASS', due_query=expect_q, requested_in_owner_name=True, job_driven_by_step_rpc=True, new_run_checked=True,
                    not_due_after=True, outside_hours=outside, auto_off=off, label='TEST_CLOCK_OVERRIDE on the finished job capture time')

    def fg_low(stock=140):
        """An item whose free stock is at or under its formula point: PATTERN sold over 30 days, lead 7 days in its profile."""
        f = formula.item(cur, today, stock)
        formula.sell_days(cur, f, today, formula.PATTERN)
        formula.profile(cur, f, lead_days=7)
        o = formula.oracle(stock, formula.PATTERN, today, lead=7)
        free = stock - sum(formula.PATTERN)
        assert free <= o['point'], (free, o)
        b.api.admin(cur)
        name, size = cur.execute('select p.product_name,s.size_code from erp.products p join erp.sizes s on s.id=p.size_id where p.id=%s',
                                 (f['product'],)).fetchone()
        return f, o['point'], free, name + ' ' + size

    def fg_forwarded():
        s = setup(cur, kinds=KINDS + ['FG_AT_REORDER_POINT'])
        f, point, free, label = fg_low()
        out = tick(cur, 'collect_tick')
        assert out['kinds']['FG_AT_REORDER_POINT'].get('error') is None and out['kinds']['FG_AT_REORDER_POINT']['opened'] >= 1, out
        item = alert_item(cur, 'FG_AT_REORDER_POINT', f['target'])
        b.api.admin(cur)
        detail = one(cur, 'select detail from cp7_alert_native.alerts where id=%s', (item,))
        assert (detail['free_pcs'], detail['reorder_point_pcs'], detail['wip_status'], detail['wip_pcs'], detail['basis']) == \
            (str(free), str(point), 'COMPLETE', '0', 'FORMULA'), detail
        before = last_request(cur)
        sent = tick(cur, 'send_tick')
        assert sent['outcome'] == 'SENT', sent
        d = dispatch(cur, sent['dispatch_id'])
        reqs = queued(cur, before)
        line = '- %s: sisa %s pcs, sedang diproduksi 0 pcs, titik pesan ulang %s pcs' % (label, free, point)
        assert len(reqs) == 1 and reqs[0]['text'] == d['body'] and reqs[0]['phone'] == PHONE, [dict(r, apikey='?') for r in reqs]
        lines = d['body'].split('\n')
        assert 'Stok barang jadi menipis (1):' in lines and line in lines, lines
        mine = outbox(cur, item)
        assert [(o['state'], o['dispatch']) for o in mine] == [('DISPATCHED', d['id'])], mine
        owner_view = rpc(cur, 'erp_cp7_get_alerts_v1', ('{}',), s['owner'])
        assert [r['kind'] for r in owner_view['rows'] if r['subject_key'] == f['target']] == ['FG_AT_REORDER_POINT'], owner_view['rows']
        blind = formula.staff_with(cur, 'warehouse.stock.view')
        assert not [r for r in rpc(cur, 'erp_cp7_get_alerts_v1', ('{}',), blind)['rows'] if r['kind'] == 'FG_AT_REORDER_POINT']
        return dict(status='PASS', line=line, free=free, point=point, staff_without_fg_view_sees_none=True)

    def fg_resolved_before_send():
        setup(cur, kinds=KINDS + ['FG_AT_REORDER_POINT'])
        tick(cur, 'collect_tick')
        tick(cur, 'send_tick')
        age_dispatches(cur, 2)
        f, point, free, _ = fg_low()
        tick(cur, 'collect_tick')
        item = alert_item(cur, 'FG_AT_REORDER_POINT', f['target'])
        assert [o['state'] for o in outbox(cur, item)] == ['PENDING']
        formula.found(cur, f, today, point - free + 1, hour=0)
        out = tick(cur, 'send_tick')
        a = outbox(cur, item)[0]
        assert (a['state'], a['reason'], a['dispatch']) == ('RESOLVED_BEFORE_SEND', 'ABOVE_REORDER_POINT', None), (a, out)
        return dict(status='PASS', stock_found_before_send=a['reason'], tick=out['outcome'])

    named = [waits_for_owner, fabric_equals_summary, ar_ap_sources, owner_reminders_only, send_one_request, rollback_nothing, resolved_before_send,
             answers, pacing_burst_quiet_digest_repeat, off_or_no_key, key_write_only, privacy_permissions, ticks_private, analysis_gap,
             analysis_automatic, fg_forwarded, fg_resolved_before_send]
    named += [op for _, op in formula.cases(cur, today)]
    assert len(named) == len(IDS['native'])
    return list(zip(IDS['native'], named))


# ----------------------------------------------------------------------------------------------------- races --
def docker_admin(sql):
    """The stack's superuser inside the database container (the harness already uses it for copies)."""
    out = subprocess.run(['docker', 'exec', CONTAINER, 'psql', '-U', 'supabase_admin', '-d', 'postgres', '-X', '-At', '-v', 'ON_ERROR_STOP=1', '-c', sql],
                         capture_output=True, text=True, timeout=60)
    if out.returncode:
        raise AssertionError('WAF_DOCKER_ADMIN: ' + out.stderr[-500:])
    return out.stdout.strip()


def fake_log():
    out = subprocess.run(['docker', 'logs', 'fake-callmebot'], capture_output=True, text=True, timeout=30).stdout
    return [json.loads(line[len('FAKE_REQUEST '):]) for line in out.splitlines() if line.startswith('FAKE_REQUEST ')]


def races(tools, today):
    database = urlparse(tools.admin).path.lstrip('/')

    def committed(op):
        with tools.connect() as conn, conn.cursor() as cur:
            out = op(cur)
            conn.commit()
            return out

    def ready(**values):
        return committed(lambda cur: setup(cur, **values))

    def server_tick(name):
        return committed(lambda cur: tick(cur, name))

    def worker_on(db):
        """Point the pg_net worker at one database (as the stack's superuser), restart it there."""
        docker_admin("alter system set pg_net.database_name='%s'" % db)
        docker_admin('select pg_reload_conf()')
        time.sleep(1)
        with psycopg.connect(urlunparse(urlparse(tools.admin)._replace(path='/' + db)), autocommit=True) as c:
            c.execute('select net.worker_restart()')
        time.sleep(2)

    def worker_back():
        docker_admin('alter system reset pg_net.database_name')
        docker_admin('select pg_reload_conf()')
        time.sleep(1)
        with psycopg.connect(urlunparse(urlparse(tools.admin)._replace(path='/postgres')), autocommit=True) as c:
            if c.execute("select exists(select 1 from pg_extension where extname='pg_net')").fetchone()[0]:
                c.execute('select net.worker_restart()')

    def wait_answer(dispatch_id, seconds=40):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            with tools.connect() as conn, conn.cursor() as cur:
                b.api.admin(cur)
                if one(cur, 'select exists(select 1 from net._http_response r join cp7_alert_native.dispatches d on d.net_request_id=r.id where d.id=%s)',
                       (dispatch_id,)):
                    return True
            time.sleep(1)
        return False

    def two_sends():
        ready()
        committed(lambda cur: (fabric(cur, 35, 'WARACE'), tick(cur, 'collect_tick')))
        with ThreadPoolExecutor(max_workers=2) as pool:
            outs = list(pool.map(lambda _: server_tick('send_tick'), range(2)))
        kinds = sorted(o['outcome'] for o in outs)
        n = committed(lambda cur: (b.api.admin(cur), one(cur, "select count(*) from cp7_alert_native.dispatches where kind='INSTANT'"))[1])
        assert kinds in (['BUSY', 'SENT'], ['SENT', 'WAITING']) and n == 1, (outs, n)
        holder = tools.connect()
        try:
            holder.execute("select pg_advisory_xact_lock(hashtextextended('CP7:WA:SEND',0))")
            started = time.monotonic()
            busy = server_tick('send_tick')
            waited = time.monotonic() - started
        finally:
            holder.rollback()
            holder.close()
        assert busy['outcome'] == 'BUSY' and waited < 1.5, (busy, waited)
        return dict(status='PASS', concurrent_outcomes=kinds, instant_dispatches=n, held_lock_busy_s=round(waited, 3))

    def collect_and_send():
        ready()
        committed(lambda cur: (fabric(cur, 35, 'WAPERTAMA'), tick(cur, 'collect_tick')))
        mat = committed(lambda cur: fabric(cur, 35, 'WABERSAMA'))
        with ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(server_tick, 'collect_tick')
            s = pool.submit(server_tick, 'send_tick')
            outs = (a.result(60), s.result(60))
        rows = committed(lambda cur: (b.api.admin(cur), cur.execute("""select a.episode,(select count(*) from cp7_alert_native.outbox o where o.item_id=a.id)
            from cp7_alert_native.alerts a where a.kind='FABRIC_BELOW_MINIMUM' and a.subject_key=%s""", (mat,)).fetchall())[1])
        assert rows == [(1, 1)], (rows, outs)
        return dict(status='PASS', one_alert_one_outbox_row=True, outcomes=[o['outcome'] for o in outs])

    def end_to_end():
        before = len(fake_log())
        s = ready()
        try:
            worker_on(database)
            committed(lambda cur: (fabric(cur, 55, 'WANYATA'), tick(cur, 'collect_tick')))
            sent = server_tick('send_tick')
            assert sent['outcome'] == 'SENT' and wait_answer(sent['dispatch_id']), sent
            server_tick('send_tick')
            d = committed(lambda cur: dispatch(cur, sent['dispatch_id']))
            log = fake_log()[before:]
            assert (d['status'], d['http']) == ('PROVIDER_ACCEPTED', 200) and KEY not in d['text'] and '***' in d['text'], d
            assert len(log) == 1 and log[0]['phone'] == PHONE and log[0]['key_ok'] is True and log[0]['text'] == d['body'], log
            test = committed(lambda cur: rpc(cur, 'erp_cp7_send_wa_test_v1', (str(uuid.uuid4()),), s['owner']))
            assert wait_answer(test['dispatch_id'])
            server_tick('send_tick')
            log = fake_log()[before:]
            assert len(log) == 2 and log[1]['text'].startswith('✅ Pesan uji ERP Enteng'), log[-1:]
            committed(lambda cur: (age_dispatches(cur, 2), fabric(cur, 55, 'WAFAIL'), tick(cur, 'collect_tick')))
            failing = server_tick('send_tick')
            assert failing['outcome'] == 'SENT' and wait_answer(failing['dispatch_id'])
            server_tick('send_tick')
            f = committed(lambda cur: dispatch(cur, failing['dispatch_id']))
            assert (f['status'], f['http']) == ('PROVIDER_REFUSED', 500) and fake_log()[before:][-1]['status'] == 500, f
        finally:
            worker_back()
        return dict(status='PASS', delivered_to_fake=True, phone_text_key_as_sent=True, stored_answer_masked=True, test_message_delivered=True,
                    answer_500_refused=True, requests=len(fake_log()) - before)

    def pg_cron_ticks():
        before = len(fake_log())
        s = ready()
        committed(lambda cur: reminder(cur, s['owner'], 'WA cron bayar listrik', now(cur) - timedelta(minutes=1)))
        cron_url = urlunparse(urlparse(tools.admin)._replace(path='/postgres'))
        ids = []
        try:
            worker_on(database)
            with psycopg.connect(cron_url, autocommit=True) as cc:
                assert cc.execute("select extversion from pg_extension where extname='pg_cron'").fetchone(), 'WAF_PG_CRON_NOT_AVAILABLE'
                defs = committed(lambda cur: (b.api.admin(cur), one(cur, 'select cp7_alert_native.schedules()'))[1])
                # TEST_SCHEDULE_OVERRIDE (labelled): every 5 seconds on this disposable copy only.
                ids = [cc.execute('select cron.schedule_in_database(%s,%s,%s,%s,%s,true)', (d['name'] + '@' + database, '5 seconds', d['command'], database,
                                                                                           'postgres')).fetchone()[0] for d in defs]
                deadline = time.monotonic() + 150
                while time.monotonic() < deadline and not any('WA cron bayar listrik' in r['text'] for r in fake_log()[before:]):
                    time.sleep(3)
                for jid in ids:
                    cc.execute('select cron.unschedule(%s::bigint)', (jid,))
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline and cc.execute("select count(*) from pg_stat_activity where datname=%s and application_name='pg_cron'",
                                                                (database,)).fetchone()[0]:
                    time.sleep(0.5)
                deadline = time.monotonic() + 60
                while time.monotonic() < deadline and cc.execute("select count(*) from cron.job_run_details where jobid=any(%s) and status not in('succeeded','failed')",
                                                                (ids,)).fetchone()[0]:
                    time.sleep(0.5)
                runs = dict(cc.execute('select status,count(*) from cron.job_run_details where jobid=any(%s) group by 1', (ids,)).fetchall())
                cc.execute('delete from cron.job_run_details where jobid=any(%s)', (ids,))
                left = cc.execute("select count(*) from cron.job where jobname like 'erp-wa-%%'").fetchone()[0]
        finally:
            worker_back()
        log = fake_log()[before:]
        assert any('WA cron bayar listrik' in r['text'] and r['key_ok'] is True for r in log), log
        assert runs.get('succeeded', 0) >= 3 and runs.get('failed', 0) == 0 and left == 0, (runs, left)
        ticked = committed(lambda cur: (b.api.admin(cur), dict(cur.execute('select job,outcome->>%s from cp7_alert_native.ticks', ('outcome',)).fetchall()))[1])
        assert set(ticked) == {'COLLECT', 'SEND', 'ANALYSIS'} and ticked['ANALYSIS'] == 'NO_OWNER_ANALYSIS_YET', ticked
        return dict(status='PASS', pg_cron_runs=runs, owner_reminder_delivered=True, schedules_removed=True, test_schedule_override='5 seconds',
                    ticks=ticked)

    def fg_busy_recheck():
        """While another evaluation holds the formula lock, the collector checks the items at or under their point against the
        free stock now (not the stored evaluation) and writes no evaluation; a refresh from the screen is refused as busy."""
        s = ready(kinds=KINDS + ['FG_AT_REORDER_POINT'])

        def low(cur):
            f = formula.item(cur, today, 140)
            formula.sell_days(cur, f, today, formula.PATTERN)
            formula.profile(cur, f, lead_days=7)
            return f
        f = committed(low)
        o = formula.oracle(140, formula.PATTERN, today, lead=7)
        free = 140 - sum(formula.PATTERN)
        committed(lambda cur: tick(cur, 'collect_tick'))
        state = lambda cur: (b.api.admin(cur), cur.execute(
            "select e.state,a.state,a.resolution from cp7_stock_formula.evaluations e left join cp7_alert_native.alerts a "
            "on a.kind='FG_AT_REORDER_POINT' and a.subject_key=e.target_key where e.target_key=%s order by a.episode desc nulls last limit 1",
            (f['target'],)).fetchone())[1]
        assert committed(state) == ('AT_OR_BELOW', 'OPEN', None), committed(state)
        committed(lambda cur: formula.found(cur, f, today, o['point'] - free + 1, hour=0))
        holder = tools.connect()
        try:
            holder.execute("select pg_advisory_xact_lock(hashtextextended('CP7:FORMULA:FG',0))")
            out = server_tick('collect_tick')
            during = committed(state)
            busy = committed(lambda cur: refusal(cur, lambda: rpc(cur, 'erp_cp7_refresh_fg_reorder_v1', (), s['owner'])))
        finally:
            holder.rollback()
            holder.close()
        assert out['kinds']['FG_AT_REORDER_POINT'].get('error') is None, out
        assert during == ('AT_OR_BELOW', 'RESOLVED', 'ABOVE_REORDER_POINT'), during
        assert busy == ('55P03', 'CP7_FORMULA_BUSY'), busy
        committed(lambda cur: tick(cur, 'collect_tick'))
        after = committed(state)
        assert after == ('ABOVE', 'RESOLVED', 'ABOVE_REORDER_POINT'), after
        return dict(status='PASS', resolved_from_live_stock_while_busy=True, evaluation_untouched_while_busy=True, refresh_busy=busy[1],
                    next_tick_evaluates=after[0])

    return list(zip(IDS['races'], (two_sends, collect_and_send, end_to_end, pg_cron_ticks, fg_busy_recheck)))


# ------------------------------------------------------------------------------------------------------- http --
def http_cases(http, today):
    def prepare_copy():
        with http.connect() as conn, conn.cursor() as cur:
            pg_net(cur)
            cur.execute('update cp7_alert_native.transport set base_url=%s', (FAKE,))
            conn.commit()

    def owner_flow():
        prepare_copy()
        owner = http.login('OWNER', 'waf-owner')
        saved = owner.rpc('erp_cp7_save_wa_settings_v1', dict(p=dict(SETTINGS, expected_revision=0), p_request=str(uuid.uuid4())))
        assert saved['status'] == 200 and saved['body']['settings']['revision'] == 1, saved
        key = owner.rpc('erp_cp7_set_wa_key_v1', dict(p_key=KEY, p_request=str(uuid.uuid4())))
        assert key['status'] == 200 and key['body']['key_present'] is True and KEY not in json.dumps(key['body']), key
        on = owner.rpc('erp_cp7_save_wa_settings_v1', dict(p=dict(SETTINGS, enabled=True, expected_revision=1), p_request=str(uuid.uuid4())))
        assert on['status'] == 200 and on['body']['settings']['enabled'] is True, on
        test = owner.rpc('erp_cp7_send_wa_test_v1', dict(p_request=str(uuid.uuid4())))
        assert test['status'] == 200 and test['body']['status'] == 'QUEUED', test
        read = owner.rpc('erp_cp7_get_wa_settings_v1', {})
        assert read['status'] == 200 and read['body']['key_present'] is True and KEY not in json.dumps(read['body']), read['status']
        assert [d['kind'] for d in read['body']['dispatches']] == ['TEST'] and read['body']['transport_is_callmebot'] is False
        listed = owner.rpc('erp_cp7_get_alerts_v1', dict(p={}))
        assert listed['status'] == 200 and listed['body']['configured'] is True, listed['status']
        with http.connect() as conn, conn.cursor() as cur:
            b.api.admin(cur)
            q = queued(cur)
            assert len(q) == 1 and q[0]['phone'] == PHONE and q[0]['apikey'] == KEY and q[0]['text'].startswith('✅ Pesan uji'), [dict(r, apikey='?') for r in q]
        return dict(status='PASS', real_Auth_owner=True, settings_saved=True, key_set_not_returned=True, enabled=True, test_queued=True,
                    settings_read_without_key=True, alerts_listed=True)

    def others_refused():
        staff = http.login('GUDANG', 'waf-staff')
        refusals = {}
        for name, args in (('erp_cp7_get_wa_settings_v1', {}), ('erp_cp7_save_wa_settings_v1', dict(p=dict(SETTINGS, expected_revision=0),
                                                                                                    p_request=str(uuid.uuid4()))),
                           ('erp_cp7_set_wa_key_v1', dict(p_key='FAKEKEY-STAFF', p_request=str(uuid.uuid4()))),
                           ('erp_cp7_send_wa_test_v1', dict(p_request=str(uuid.uuid4()))),
                           ('erp_cp7_resolve_wa_dispatch_v1', dict(p=dict(dispatch_id=1, outcome='DELIVERED'), p_request=str(uuid.uuid4())))):
            x = staff.rpc(name, args)
            assert x['status'] >= 400 and 'CP7_WA_OWNER_ONLY' in json.dumps(x['body']), (name, x)
            refusals[name] = x['status']
            y = http.anon_rpc(name, args)
            assert y['status'] >= 400, (name, y)
        listed = staff.rpc('erp_cp7_get_alerts_v1', dict(p={}))
        assert listed['status'] == 200 and all(r['wa'] is None for r in listed['body']['rows']), listed['status']
        for name in ('collect_tick', 'send_tick', 'wa_post', 'vault_key_write', 'erp_cp7_wa_tick_v1'):
            x = staff.rpc(name, {})
            assert x['status'] >= 400, (name, x)
        with http.connect() as conn, conn.cursor() as cur:
            b.api.admin(cur)
            assert one(cur, "select count(*) from vault.secrets where name='cp7_callmebot_apikey' and secret like %s", ('%STAFF%',)) == 0
        return dict(status='PASS', staff_refused=refusals, anon_refused=True, staff_alerts_without_wa_status=True, private_functions_not_exposed=True)

    def fg_reorder_screen():
        """The finished-goods reorder RPCs through PostgREST with real Auth: the owner reads and refreshes, the admin sets a
        manual point, the owner the service level; a warehouse user may only read (with the permission), anon nothing."""
        with http.connect() as conn, conn.cursor() as cur:
            f = formula.item(cur, today, 140)
            formula.sell_days(cur, f, today, formula.PATTERN)
            formula.profile(cur, f, lead_days=7)
            conn.commit()
        o = formula.oracle(140, formula.PATTERN, today, lead=7)
        owner = http.login('OWNER', 'ss1-owner')
        r = owner.rpc('erp_cp7_refresh_fg_reorder_v1', {})
        assert r['status'] == 200 and r['body']['items'] >= 1, r
        w = owner.rpc('erp_cp7_get_fg_reorder_v1', dict(p_query=dict(q=f['sku'])))
        assert w['status'] == 200 and w['body']['can_manage'] is True, w
        row = w['body']['page']['rows'][0]
        assert (row['target_key'], row['point'], row['basis'], row['state']) == (f['target'], o['point'], 'FORMULA', 'AT_OR_BELOW'), row
        admin = http.login('ADMIN', 'ss1-admin')
        m = admin.rpc('erp_cp7_save_fg_reorder_manual_v1', dict(p_payload=dict(root_id=f['product'], expected_revision=0, reorder_point_pcs=10,
                                                                                reason='SS-1 HTTP manual'), p_request=str(uuid.uuid4())))
        assert m['status'] == 200 and (m['body']['evaluation']['basis'], m['body']['evaluation']['state']) == ('MANUAL', 'ABOVE'), m
        st = owner.rpc('erp_cp7_save_stock_formula_settings_v1', dict(p_payload=dict(expected_revision=0, service_level='0.99', window_days=30,
                                                                                    reason='SS-1 HTTP level'), p_request=str(uuid.uuid4())))
        assert st['status'] == 200 and st['body']['settings']['service_level'] == '0.99', st
        staff = http.login('GUDANG', 'ss1-staff')
        with http.connect() as conn, conn.cursor() as cur:
            b.api.admin(cur)
            sees = one(cur, "select exists(select 1 from erp.app_role_permissions p join erp.app_roles r on r.id=p.role_id "
                            "where r.role_code='GUDANG' and p.permission_key='warehouse.fg.view')")
        read = staff.rpc('erp_cp7_get_fg_reorder_v1', dict(p_query={}))
        assert (read['status'] == 200) == sees and (sees or 'CP7_FORMULA_ACCESS_DENIED' in json.dumps(read['body'])), read
        for name, args in (('erp_cp7_save_fg_reorder_manual_v1', dict(p_payload=dict(root_id=f['product'], expected_revision=1, reorder_point_pcs=99,
                                                                                         reason='staff'), p_request=str(uuid.uuid4()))),
                           ('erp_cp7_save_stock_formula_settings_v1', dict(p_payload=dict(expected_revision=1, service_level='0.90', window_days=30,
                                                                                          reason='staff'), p_request=str(uuid.uuid4())))):
            x = staff.rpc(name, args)
            assert x['status'] >= 400 and 'CP7_FORMULA_ACCESS_DENIED' in json.dumps(x['body']), (name, x)
        for name, args in (('erp_cp7_get_fg_reorder_v1', dict(p_query={})), ('erp_cp7_refresh_fg_reorder_v1', {}),
                           ('erp_cp7_save_fg_reorder_manual_v1', dict(p_payload={}, p_request=str(uuid.uuid4()))),
                           ('erp_cp7_save_stock_formula_settings_v1', dict(p_payload={}, p_request=str(uuid.uuid4())))):
            assert http.anon_rpc(name, args)['status'] >= 400, name
        for name in ('compute', 'fg_source', 'model_wip'):
            assert staff.rpc(name, {})['status'] >= 400, name
        return dict(status='PASS', real_Auth=True, owner_reads_and_refreshes=True, admin_manual=True, owner_level=True, gudang_reads=sees,
                    staff_cannot_change=True, anon_refused=True)

    return list(zip(IDS['http'], (owner_flow, others_refused, fg_reorder_screen)))
