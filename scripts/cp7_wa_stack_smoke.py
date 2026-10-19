"""WA-3a (owner D17-6): alerts.sql on a bare Supabase stack, end to end, before the long Native suite.

Installs scripts/cp7-src/alerts/alerts.sql as postgres (not a superuser, as on the hosted project) over the small
stand-ins of scripts/cp7_wa_smoke_stubs.sql, then proves on the stack's own Vault, pg_net and pg_cron, against the fake
CallMeBot container (fake-callmebot:8080, started by the workflow): the bundle verifier holds after install; the owner
sets settings and the key through the public RPCs (staff refused); a fabric below its minimum opens an alert, the send
tick queues one request and the fake server receives phone, text and the key; the answer is read back with the key
masked; a test message arrives; pg_cron runs the two ticks from cp7_alert_native.schedules() and an owner reminder
arrives; an answer 500 leaves the item waiting; a rolled-back transaction sends nothing; the key is in no table of the
module; uninstall (drop owned by cp7_alert, Vault secret deleted) leaves nothing. Prints "WA_SMOKE <step> <json>".
No real number, no real key: +620000000000 and FAKEKEY-SMOKE only.
"""
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import cp7_alert_bundle as bundle  # noqa: E402

PG = 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'
FAKE = 'http://fake-callmebot:8080/whatsapp.php'
PHONE = '+620000000000'
KEY = 'FAKEKEY-SMOKE'
OWNER = str(uuid.UUID(int=0xA1))
STAFF = str(uuid.UUID(int=0xB1))
PERMS = ['warehouse.dashboard.view', 'warehouse.material.view', 'master.fabric.view', 'finance.ar.view', 'finance.ap.view']
SETTINGS = dict(enabled=False, phone_e164=PHONE, detail='SUMMARY', digest_times=[], kinds=['MANUAL_REMINDER', 'FABRIC_BELOW_MINIMUM', 'AR_DUE', 'AP_DUE'],
                repeat_minutes=1440, burst_after_per_day=30, burst_merge_minutes=30, max_items=10, quiet_enabled=False, quiet_start='21:00',
                quiet_end='06:00', analysis_every_minutes=60, analysis_start='07:00', analysis_end='20:00')
FAILED = []


def say(step, **detail):
    print('WA_SMOKE', step, json.dumps(detail, default=str), flush=True)


def check(step, ok, **detail):
    say(step, ok=bool(ok), **detail)
    if not ok:
        FAILED.append(step)


def conn():
    c = psycopg.connect(PG, autocommit=True)
    c.execute("set statement_timeout='8s'")
    return c


def one(sql, args=None):
    with conn() as c:
        return c.execute(sql, args).fetchone()[0]


def rpc(subject, name, *args):
    """A public RPC as PostgREST runs it: role authenticated, the subject's claims, the 8 s limit."""
    with psycopg.connect(PG) as c, c.cursor() as cur:
        cur.execute("set local statement_timeout='8s'")
        cur.execute("select set_config('request.jwt.claims',%s,true)", (json.dumps(dict(sub=subject, role='authenticated')),))
        cur.execute('set local role authenticated')
        try:
            out = cur.execute('select public.' + name + '(' + ','.join(['%s'] * len(args)) + ')', args).fetchone()[0]
            c.commit()
            return dict(ok=True, body=out)
        except psycopg.Error as e:
            c.rollback()
            return dict(ok=False, sqlstate=e.sqlstate, message=e.diag.message_primary)


def tick(name):
    with conn() as c:
        return c.execute('select cp7_alert_native.' + name + '()').fetchone()[0]


def fake_log():
    out = subprocess.run(['docker', 'logs', 'fake-callmebot'], capture_output=True, text=True).stdout
    return [json.loads(line[len('FAKE_REQUEST '):]) for line in out.splitlines() if line.startswith('FAKE_REQUEST ')]


def wait_answer(dispatch, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        found = one('select exists(select 1 from net._http_response r join cp7_alert_native.dispatches d on d.net_request_id=r.id where d.id=%s)', (dispatch,))
        if found:
            return True
        time.sleep(1)
    return False


def low_fabric(name, minimum=60, stock=42):
    with conn() as c:
        loc = c.execute("select id from erp.locations where location_code='WA-SMOKE'").fetchone()[0]
        m = c.execute("insert into erp.materials(material_sku,material_name,material_type,unit_code)values(%s,%s,'FABRIC','kg')returning id",
                      ('SMK-' + uuid.uuid4().hex[:6], name)).fetchone()[0]
        c.execute('insert into erp.fabric_master_profiles values(%s,%s)', (m, minimum))
        c.execute("insert into erp.material_stock_movements(material_id,location_id,qty_signed,physical_at)values(%s,%s,%s,now()-interval'1 hour')", (m, loc, stock))
        return str(m)


def last_dispatch():
    with conn() as c:
        return c.execute('select id,kind,status,http_status,provider_text,body from cp7_alert_native.dispatches order by id desc limit 1').fetchone()


def main():
    stubs = (ROOT / 'scripts/cp7_wa_smoke_stubs.sql').read_text()
    alerts = (ROOT / 'scripts/cp7-src/alerts/alerts.sql').read_text()
    # CP7C install fact (not WA itself): every CP7 bundle hands objects to the roles it creates. As postgres (not a
    # superuser) PostgreSQL 16+ allows that only with SET ROLE on the role; the session setting createrole_self_grant
    # grants each new role to its creator. Proved here on a throw-away role, both without and with the setting.
    for setting in ('', 'set, inherit'):
        with psycopg.connect(PG) as c, c.cursor() as cur:
            cur.execute("select set_config('createrole_self_grant',%s,true)", (setting,))
            cur.execute('create role wa_install_probe nologin')
            try:
                cur.execute('create schema wa_install_probe_s authorization wa_install_probe')
                say('cp7c_install_fact', createrole_self_grant=setting or '(empty)', handoff_allowed=True)
            except psycopg.Error as e:
                say('cp7c_install_fact', createrole_self_grant=setting or '(empty)', handoff_allowed=False, error=e.diag.message_primary)
            c.rollback()
    with psycopg.connect(PG) as c, c.cursor() as cur:
        say('cp7c_install_fact_grant_options', **{f'{schema}_{priv}': cur.execute(
            "select has_schema_privilege('postgres',%s,%s)", (schema, priv + ' WITH GRANT OPTION')).fetchone()[0]
            for schema in ('auth', 'vault', 'net', 'cron', 'extensions') for priv in ('USAGE',)
            if cur.execute('select exists(select 1 from pg_namespace where nspname=%s)', (schema,)).fetchone()[0]})
        say('whoami', user=cur.execute('select current_user').fetchone()[0], superuser=cur.execute("select rolsuper from pg_roles where rolname=current_user").fetchone()[0])
        cur.execute(stubs, prepare=False)
        cur.execute(alerts, prepare=False)
        c.commit()
        verified = bundle.verify_alert(cur)
        c.rollback()
    check('install_as_postgres_and_verify', True, stage=verified['stage'])
    with conn() as c:
        c.execute('create extension if not exists pg_net')
        c.execute('create extension if not exists pg_cron')
        c.execute("insert into erp.test_users values(%s,'OWNER',true,%s),(%s,'GUDANG',true,%s)", (OWNER, PERMS, STAFF, PERMS[:3]))
        c.execute("insert into erp.locations(location_code,location_name,location_type)values('WA-SMOKE','Gudang Smoke','RAW_MATERIAL_WAREHOUSE')")
    check('not_configured', tick('collect_tick')['outcome'] == 'NOT_CONFIGURED')

    saved = rpc(OWNER, 'erp_cp7_save_wa_settings_v1', json.dumps(dict(SETTINGS, expected_revision=0)), str(uuid.uuid4()))
    staff = [rpc(STAFF, n, *a) for n, a in (('erp_cp7_get_wa_settings_v1', ()), ('erp_cp7_set_wa_key_v1', ('X1234', str(uuid.uuid4()))),
                                            ('erp_cp7_send_wa_test_v1', (str(uuid.uuid4()),)))]
    key = rpc(OWNER, 'erp_cp7_set_wa_key_v1', KEY, str(uuid.uuid4()))
    check('owner_settings_and_key_staff_refused', saved['ok'] and key['ok'] and key['body']['key_present'] is True
          and all((not s['ok']) and s['sqlstate'] == '42501' for s in staff), saved=saved, staff=staff)
    with conn() as c:
        c.execute('update cp7_alert_native.transport set base_url=%s', (FAKE,))
        secret = c.execute("select count(*) from vault.secrets where name='cp7_callmebot_apikey'").fetchone()[0]
    enabled = rpc(OWNER, 'erp_cp7_save_wa_settings_v1', json.dumps(dict(SETTINGS, enabled=True, expected_revision=1)), str(uuid.uuid4()))
    check('enabled', enabled['ok'] and enabled['body']['settings']['enabled'] is True and secret == 1, enabled=enabled)

    low_fabric('Katun Smoke Hitam')
    collected = tick('collect_tick')
    sent = tick('send_tick')
    check('first_message_queued', collected['kinds']['FABRIC_BELOW_MINIMUM']['opened'] == 1 and sent['outcome'] == 'SENT', collected=collected, sent=sent)
    first = sent['dispatch_id']
    check('first_answer_arrived', wait_answer(first))
    tick('send_tick')
    d = last_dispatch()
    log = fake_log()
    check('first_message_delivered_to_fake', d[0] == first and d[2] == 'PROVIDER_ACCEPTED' and d[3] == 200 and KEY not in (d[4] or '') and '***' in (d[4] or '')
          and len(log) == 1 and log[0]['phone'] == PHONE and log[0]['key_ok'] is True and 'Katun Smoke Hitam' in log[0]['text'],
          dispatch=d[:5], fake=log)

    test = rpc(OWNER, 'erp_cp7_send_wa_test_v1', str(uuid.uuid4()))
    check('test_answer_arrived', test['ok'] and wait_answer(test['body']['dispatch_id']), test=test)
    tick('send_tick')
    log = fake_log()
    check('test_message_delivered', len(log) == 2 and 'Pesan uji ERP Enteng' in log[1]['text']
          and one('select status from cp7_alert_native.dispatches where id=%s', (test['body']['dispatch_id'],)) == 'PROVIDER_ACCEPTED', fake=log[-1:])

    # pg_cron runs the two ticks exactly as schedules() defines them (every 5 seconds here, TEST_SCHEDULE_OVERRIDE).
    with conn() as c:
        c.execute("insert into erp.manual_reminders(owner_user_id,title,due_at)values(%s,'Bayar listrik smoke',now()-interval'1 minute')", (OWNER,))
        c.execute("insert into erp.manual_reminders(owner_user_id,title,due_at)values(%s,'Catatan staf smoke',now()-interval'1 minute')", (STAFF,))
        jobs = c.execute('select cp7_alert_native.schedules()').fetchone()[0]
        ids = [c.execute("select cron.schedule(%s,'5 seconds',%s)", (j['name'] + '-smoke', j['command'])).fetchone()[0] for j in jobs]
    try:
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline and not any('Bayar listrik smoke' in r['text'] for r in fake_log()):
            time.sleep(3)
    finally:
        with conn() as c:
            for j in jobs:
                c.execute('select cron.unschedule(%s)', (j['name'] + '-smoke',))
        time.sleep(6)
    log = fake_log()
    with conn() as c:
        runs = c.execute("select status,count(*) from cron.job_run_details where jobid=any(%s) group by 1", (ids,)).fetchall()
        staff_queued = c.execute("select count(*) from cp7_alert_native.outbox o join erp.manual_reminders r on r.id=o.item_id where r.owner_user_id=%s", (STAFF,)).fetchone()[0]
    check('pg_cron_ticks_deliver_owner_reminder', any('Bayar listrik smoke' in r['text'] for r in log) and not any('staf' in r['text'] for r in log)
          and staff_queued == 0 and dict(runs).get('failed', 0) == 0, runs=runs, fake=log[-1:])
    with conn() as c:
        say('ticks_after_cron', ticks={r[0]: r[1] for r in c.execute('select job,outcome from cp7_alert_native.ticks').fetchall()})

    # An answer 500: refused, the item waits again and nothing is marked sent.
    time.sleep(56)
    low_fabric('Kain FAIL Smoke')
    tick('collect_tick')
    sent = tick('send_tick')
    ok = sent['outcome'] == 'SENT' and wait_answer(sent['dispatch_id'])
    tick('send_tick')
    with conn() as c:
        d = c.execute('select status,http_status from cp7_alert_native.dispatches where id=%s', (sent.get('dispatch_id'),)).fetchone()
        waiting = c.execute("""select o.state,o.reason from cp7_alert_native.outbox o join cp7_alert_native.alerts a on a.id=o.item_id
            where a.title like '%%FAIL Smoke%%'""").fetchall()
    check('answer_500_refused_item_waits', ok and d == ('PROVIDER_REFUSED', 500) and waiting == [('PENDING', 'PROVIDER_REFUSED')], dispatch=d, outbox=waiting)

    # A rolled-back transaction queues and sends nothing.
    before = (one('select count(*) from cp7_alert_native.outbox'), len(fake_log()))
    with psycopg.connect(PG) as c, c.cursor() as cur:
        cur.execute("set local statement_timeout='8s'")
        loc = cur.execute("select id from erp.locations where location_code='WA-SMOKE'").fetchone()[0]
        m = cur.execute("insert into erp.materials(material_sku,material_name,material_type,unit_code)values('SMK-RB','Kain Rollback','FABRIC','kg')returning id").fetchone()[0]
        cur.execute('insert into erp.fabric_master_profiles values(%s,10)', (m,))
        cur.execute("insert into erp.material_stock_movements(material_id,location_id,qty_signed,physical_at)values(%s,%s,1,now()-interval'1 hour')", (m, loc))
        inside = cur.execute('select cp7_alert_native.collect_tick()').fetchone()[0]
        c.rollback()
    time.sleep(5)
    after = (one('select count(*) from cp7_alert_native.outbox'), len(fake_log()))
    check('rollback_sends_nothing', inside['kinds']['FABRIC_BELOW_MINIMUM']['opened'] == 1 and before == after, before=before, after=after)

    with conn() as c:
        tables = [r[0] for r in c.execute("select c.oid::regclass::text from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname in('cp7_alert_native','erp','public')and c.relkind='r'").fetchall()]
        leaks = [t for t in tables if c.execute('select count(*) from ' + t + ' x where to_jsonb(x)::text like %s', ('%' + KEY + '%',)).fetchone()[0]]
    read = rpc(OWNER, 'erp_cp7_get_wa_settings_v1')
    check('key_in_no_table_or_answer', leaks == [] and read['ok'] and KEY not in json.dumps(read['body']), leaks=leaks, scanned=len(tables))

    # Uninstall: the Vault secret, then everything cp7_alert owns.
    with psycopg.connect(PG) as c, c.cursor() as cur:
        cur.execute("delete from vault.secrets where name='cp7_callmebot_apikey'")
        cur.execute('drop owned by cp7_alert cascade;drop role cp7_alert', prepare=False)
        c.commit()
        left = cur.execute("""select (select count(*) from pg_namespace where nspname='cp7_alert_native'),
            (select count(*) from pg_proc where proname like 'erp_cp7_%%wa%%' or proname='erp_cp7_get_alerts_v1'),
            (select count(*) from pg_roles where rolname='cp7_alert'),(select count(*) from vault.secrets where name='cp7_callmebot_apikey'),
            (select count(*) from cron.job where jobname like 'erp-wa-%%')""").fetchone()
    check('uninstall_leaves_nothing', left == (0, 0, 0, 0, 0), left=left)
    say('result', status='PASS' if not FAILED else 'FAIL', failed=FAILED)
    return 0 if not FAILED else 1


if __name__ == '__main__':
    raise SystemExit(main())
