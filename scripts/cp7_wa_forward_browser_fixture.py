"""Disposable controls for the WA-4b browser cases (cp7_wa_forward_browser.mjs) on the browser copy only.

prepare   TEST_RESET (labelled): the module's own rows and the Vault key removed on the disposable copy, so each journey
          starts from "never saved"; pg_net created as postgres; the transport pointed at the fake CallMeBot of the CI
          stack; the pg_net worker pointed at this copy (as the race cases do). Answers the fake server's request count.
tick      one tick exactly as pg_cron runs it (role postgres, no request identity, the 8 s limit).
deliver   waits until the fake server's answer for a dispatch is stored, then one send tick records it.
fabric    a fabric whose minimum is above its stock, through the master screen's facade.
configure the owner settings saved once by a seeded OWNER (WhatsApp off, no key) and one collect tick: system
          reminders exist for a non-owner journey.
state     read back: the latest settings row, whether the Vault key equals the one given (a boolean only, the key is
          never printed), dispatches, alerts with their outbox state, the fake server's requests after an index, and the
          kinds a user may read (the permissions of the source screens).
restore   the pg_net worker back to its default database.
fg        SS-1 (owner D17-8, D17-9): one new finished good whose free stock is at or under its formula reorder point, made
          with the Native commands of cp7_stock_formula_cases (stock found at opname, PATTERN sold and posted over the 30
          complete WIB days before today, planning profile lead time 7 days): its ids, label, the oracle's point and its
          free stock. Today is the copy's WIB date.
fg_state  read back: the item's evaluation row (to_jsonb of cp7_stock_formula.evaluations) and its latest manual point row.
The answer on stdout is JSON only; nothing else is printed, and no key appears in it."""
from contextlib import redirect_stdout
from urllib.parse import urlparse
import json
import os
import sys
import time

import psycopg

import cp7_stock_formula_cases as formula
import cp7_wa_forward_cases as wa

RESET_ORDER = ('dispatch_items', 'outbox', 'dispatches', 'alerts', 'key_events', 'source_state', 'ticks', 'analysis_runs',
               'analysis_requests', 'settings')


def committed(target, op):
    with psycopg.connect(target) as conn, conn.cursor() as cur:
        out = op(cur)
        conn.commit()
        return out


def answered(target, dispatch_id, seconds=60):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        with psycopg.connect(target) as conn, conn.cursor() as cur:
            if cur.execute('select exists(select 1 from net._http_response r join cp7_alert_native.dispatches d on d.net_request_id=r.id '
                           'where d.id=%s)', (dispatch_id,)).fetchone()[0]:
                return True
        time.sleep(1)
    return False


def worker(target, database):
    """The pg_net worker on one database (None: its default), restarted there."""
    if database:
        wa.docker_admin("alter system set pg_net.database_name='%s'" % database)
    else:
        wa.docker_admin('alter system reset pg_net.database_name')
    wa.docker_admin('select pg_reload_conf()')
    time.sleep(1)
    url = urlparse(target)._replace(path='/' + (database or 'postgres')).geturl()
    with psycopg.connect(url, autocommit=True) as c:
        if c.execute("select exists(select 1 from pg_extension where extname='pg_net')").fetchone()[0]:
            c.execute('select net.worker_restart()')
    time.sleep(2)


def with_erp_usage(cur, op):
    """The Native fixtures act as authenticated users; the browser copy has no test usage grant, so it is given for the
    fixture's own transaction and taken back before commit (as the reminders v2 browser fixture does)."""
    had = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
    acl = cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0]
    if not had:
        cur.execute('grant usage on schema erp to authenticated')
    out = op()
    wa.b.api.admin(cur)
    if not had:
        cur.execute('revoke usage on schema erp from authenticated')
    assert cur.execute("select nspacl::text from pg_namespace where nspname='erp'").fetchone()[0] == acl
    return out


def main():
    target = os.environ['AUDITOR_BROWSER_DB_URL']
    url = urlparse(target)
    assert url.hostname in ('localhost', '127.0.0.1') and url.path == '/cp6_auditor_browser', 'DISPOSABLE_BROWSER_ONLY'
    database = url.path.lstrip('/')
    op, p = sys.argv[1], json.load(sys.stdin)
    with redirect_stdout(sys.stderr):
        if op == 'prepare':
            def reset(cur):
                # TEST_RESET (labelled): disposable browser copy only; the module's guards are bypassed for this delete alone.
                cur.execute('set local session_replication_role=replica')
                for name in RESET_ORDER:
                    cur.execute('delete from cp7_alert_native.' + name)
                cur.execute("delete from vault.secrets where name='cp7_callmebot_apikey'")
                cur.execute('set local session_replication_role=origin')
                wa.pg_net(cur)
                cur.execute('update cp7_alert_native.transport set base_url=%s', (wa.FAKE,))
                return cur.execute('select base_url from cp7_alert_native.transport').fetchone()[0]
            base = committed(target, reset)
            worker(target, database)
            out = dict(test_reset=True, transport=base, fake_requests=len(wa.fake_log()))
        elif op == 'tick':
            assert p['name'] in ('collect_tick', 'send_tick', 'analysis_tick'), p
            out = committed(target, lambda cur: wa.tick(cur, p['name']))
        elif op == 'deliver':
            ok = answered(target, int(p['dispatch']))
            after = committed(target, lambda cur: wa.tick(cur, 'send_tick')) if ok else None
            out = dict(answered=ok, tick=after, dispatch=committed(target, lambda cur: wa.dispatch(cur, int(p['dispatch']))))
        elif op == 'fabric':
            def fabric(cur):
                material = with_erp_usage(cur, lambda: wa.fabric(cur, int(p.get('minimum', 55)), p.get('label', 'WA4B')))
                name = cur.execute('select material_name from erp.materials where id=%s', (material,)).fetchone()[0]
                return dict(material_id=material, name=name)
            out = committed(target, fabric)
        elif op == 'configure':
            def configure(cur):
                owner = with_erp_usage(cur, lambda: wa.setup(cur, enabled=False, key=False))['owner']
                return dict(owner_settings_saved=True, seeded_owner=owner, collect=wa.tick(cur, 'collect_tick')['outcome'])
            out = committed(target, configure)
        elif op == 'state':
            def state(cur):
                wa.b.api.admin(cur)
                s = cur.execute('select revision,enabled,phone_e164,detail,digest_times,kinds,quiet_enabled,actor::text from cp7_alert_native.settings '
                                'order by revision desc limit 1').fetchone()
                key = None
                if 'key' in p:
                    key = cur.execute("select coalesce((select decrypted_secret=%s from vault.decrypted_secrets where name='cp7_callmebot_apikey'),false)",
                                      (p['key'],)).fetchone()[0]
                ds = cur.execute('select id,kind,status,http_status,body,provider_text from cp7_alert_native.dispatches order by id').fetchall()
                al = cur.execute("""select a.kind,a.subject_key,a.title,a.state,(select o.state from cp7_alert_native.outbox o where o.item_id=a.id
                    order by o.id desc limit 1) from cp7_alert_native.alerts a order by a.kind,a.subject_key""").fetchall()
                vis = sorted(wa.visible(cur, p['subject'])) if p.get('subject') else None
                return dict(settings=None if s is None else dict(revision=s[0], enabled=s[1], phone=s[2], detail=s[3], digest_times=s[4], kinds=s[5],
                                                                 quiet_enabled=s[6], actor=s[7]),
                            key_matches=key, dispatches=[dict(id=d[0], kind=d[1], status=d[2], http=d[3], body=d[4], provider_text=d[5]) for d in ds],
                            alerts=[dict(kind=a[0], subject=a[1], title=a[2], state=a[3], outbox=a[4]) for a in al], visible=vis)
            out = committed(target, state)
            out['fake'] = wa.fake_log()[int(p.get('after', 0)):]
        elif op == 'fg':
            def fg(cur):
                today = cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
                stock = int(p.get('stock', 140))

                def made():
                    f = formula.item(cur, today, stock)
                    formula.sell_days(cur, f, today, formula.PATTERN)
                    formula.profile(cur, f, lead_days=7)
                    return f
                f = with_erp_usage(cur, made)
                # The oracle uses the settings in force on the copy (none saved: 95% and 30 days). PATTERN covers the 30 days
                # before today; a shorter window reads only its last days, with the stock left before them.
                s = cur.execute('select cp7_stock_formula.current_settings()').fetchone()[0]
                window, cut = int(s['window_days']), 30 - int(s['window_days'])
                assert 14 <= window <= 30, ('WAF_FG_FIXTURE_WINDOW_OVER_30', s)
                o = formula.oracle(stock - sum(formula.PATTERN[:cut]), formula.PATTERN[cut:], today, window=window, lead=7, level=s['service_level'])
                free = stock - sum(formula.PATTERN)
                assert o['basis'] == 'FORMULA' and free <= o['point'], ('WAF_FG_FIXTURE_NOT_AT_OR_UNDER', free, o)
                wa.b.api.admin(cur)
                name, size = cur.execute('select p.product_name::text,s.size_code::text from erp.products p join erp.sizes s on s.id=p.size_id where p.id=%s',
                                         (f['product'],)).fetchone()
                return dict(product_id=f['product'], root_id=f['product'], size_id=f['size'], sku=f['sku'], target_key=f['target'], product_name=name,
                            size_code=size, label=name + ' ' + size, point=o['point'], free=free, today=str(today), label_note='TEST_FIXTURE SS-1')
            out = committed(target, fg)
        elif op == 'fg_state':
            def fg_state(cur):
                wa.b.api.admin(cur)
                key = str(p['target_key'])
                e = cur.execute('select to_jsonb(e) from cp7_stock_formula.evaluations e where e.target_key=%s', (key,)).fetchone()
                m = cur.execute('select revision,reorder_point_pcs,reason from cp7_stock_formula.manual_points where root_id=%s order by revision desc limit 1',
                                (key.split(':')[0],)).fetchone()
                return dict(evaluation=None if e is None else e[0],
                            manual=None if m is None else dict(revision=m[0], reorder_point_pcs=m[1], reason=m[2]))
            out = committed(target, fg_state)
        elif op == 'restore':
            worker(target, None)
            out = dict(worker='default')
        else:
            raise ValueError('UNKNOWN_WA_FORWARD_BROWSER_CONTROL')
    print(json.dumps(out, default=str))


if __name__ == '__main__':
    main()
