"""Local PostgreSQL check of the exact S06 catalogue delta and its test transport."""
import ast
import json
import re
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import psycopg
from cp7_global_nonpo_envelope import catalogue_profile
from p21.s06_catalogue import bind
from p21 import s06_transport

runner = Path(__file__).resolve().parents[2]
root = runner.parent
source = runner / 'qualification/global_owning/p20/retained_installer.py'
names = {'capture', 'fingerprint', 'metadata_context', 'as_role', 'require'}
nodes = [n for n in ast.parse(source.read_bytes()).body if isinstance(n, ast.FunctionDef) and n.name in names]
exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec'))

with psycopg.connect('host=127.0.0.1 port=55486 dbname=postgres user=supabase_admin') as conn, conn.cursor() as cur:
    cur.execute('''
        create role postgres superuser; set local role postgres;
        create role anon; create role authenticated; create role service_role; create role cp7_capture;
        create schema erp; create schema cp7_reminder_native; create schema cp7_stock_formula;
        create schema cp7_analysis_stage; create schema cp7_global_nonpo_envelope;
        create table erp.manual_reminders(id uuid,owner_user_id uuid,title text,note text,status text,due_at timestamptz);
        create table erp.materials(id uuid); create table erp.material_stock_movements(id uuid);
        create table erp.fabric_master_profiles(id uuid); create table erp.locations(id uuid);
        create table cp7_analysis_stage.jobs(actor uuid,run_id uuid,state text,query jsonb,captured_at timestamptz,created_at timestamptz);
        set local check_function_bodies=off; set local search_path=''; set local timezone='UTC';
    ''', prepare=False)
    sql = (root / 's06-product/scripts/cp7-src/alerts/alerts.sql').read_text()
    header = sql.split('-- ------------------------------------------------------------------ tables --')[0]
    for group in re.findall(r'grant execute on function(.*?)to cp7_alert;', header, re.S):
        for name, types in re.findall(r'([\w.]+)\(([^)]*)\)', group):
            return_type = 'boolean' if name in ('erp.has_permission','cp7_reminder_native.condition_domain_access') else 'jsonb'
            cur.execute(f'create function {name}({types}) returns {return_type} language sql as $$$$;')
            cur.execute(f'revoke all on function {name}({types}) from public;')
    # The retained full installer uses its Supabase Admin authority.
    cur.execute('reset role')
    cur.execute(sql, prepare=False)
    cur.execute(catalogue_profile.derive()[0], prepare=False)
    cur.execute('reset role; alter role postgres nosuperuser createrole bypassrls')
    provider = SimpleNamespace(capture=capture, as_role=as_role, metadata_context=metadata_context,
        _repair_readers_preseal=lambda c: 'base-repairs',
        _repair_predecessor_image=lambda before, after: before == after,
        _repair_restore_unused=lambda c, state: None)
    receipt = bind(provider, root / 's06-product', lambda state: {'base': 'g04'})
    before = capture(cur)
    before_fp = fingerprint(cur, before)
    assert cur.execute("select pg_has_role('postgres','cp7_alert','USAGE')").fetchone() == (False,)
    from global_owning import owning
    change = owning.load('s06_original_role_check', root / 's06-product/scripts/cp7_s06_reminder_forward.py')
    cur.execute('savepoint old_role_probe')
    try:
        with as_role(cur, 'postgres'):
            change.install(cur)
    except psycopg.errors.InsufficientPrivilege as error:
        assert error.sqlstate == '42501'
        assert error.diag.message_primary == 'permission denied for schema cp7_alert_native'
        print('PASS old installer role reproduces SQLSTATE 42501 on cp7_alert_native')
    else:
        raise AssertionError('old installer unexpectedly acquired alert ownership')
    cur.execute('rollback to savepoint old_role_probe; release savepoint old_role_probe')
    assert capture(cur) == before
    assert provider._repair_readers_preseal(cur) == 'base-repairs'
    installed = capture(cur)
    assert installed != before
    assert provider._repair_predecessor_image(before, installed)
    assert fingerprint(cur, installed) != before_fp
    r = receipt({})
    assert r['s06']['changed_function_count'] == 3 and r['s06']['install_replay']
    cur.execute('savepoint changed_grant')
    cur.execute('grant execute on function cp7_alert_native.send_tick() to anon')
    try:
        provider._repair_predecessor_image(before, capture(cur))
    except ValueError as e:
        assert str(e) == 'CP7_S06_INSTALLED_FUNCTION_DRIFT'
    else:
        raise AssertionError('grant drift was accepted')
    cur.execute('rollback to savepoint changed_grant; release savepoint changed_grant')
    provider._repair_restore_unused(cur, {})
    assert capture(cur) == before and fingerprint(cur, before) == before_fp
    provider._repair_readers_preseal(cur)
    assert capture(cur) == installed
    print('PASS S06 exact three-function install, idempotency, grant drift rejection, inverse and reinstall')

    cur.execute('savepoint fake_sender')
    s06_transport.install(cur)
    with as_role(cur,'postgres'):
        answer = cur.execute("select net.http_get('https://api.callmebot.com/whatsapp.php',%s::jsonb)",
            (json.dumps({'phone':'+620000000000','text':'S06 local transport','apikey':s06_transport.FAKE_KEY}),)).fetchone()[0]
    assert s06_transport.read_requests(cur) == [('+620000000000','S06 local transport')]
    assert cur.execute('select status_code, timed_out from net._http_response where id=%s',(answer,)).fetchone() == (200,False)
    cur.execute('rollback to savepoint fake_sender; release savepoint fake_sender')
    assert capture(cur) == installed
    print('PASS synthetic pg_net records one message and transactional removal restores catalogue')
