"""Peer-informed reproduction, NOT part of the original blind oracle.

Run after lifecycle.py and before daily.py against the complete installed AC..BD
disposable schema.  Peer report/oracle were read; their code and fixtures were
not read or reused.  Uses our own original opening source and fresh real actor.
No product function, permission function, or business table is replaced by a stub.
"""
import hashlib
import json
import time
import traceback
from decimal import Decimal as D

import psycopg
from psycopg.types.json import Jsonb
import suite as s
import lifecycle as life

C = s.CTX
RESULTS = []
EVENTS = s.EVENTS
LABEL = 'peer-informed reproduction'
PERMISSION_KEYS = ['finance.hpp.manage', 'finance.hpp.view']
BOUNDARY = D(2**31 - 1) / D(100)
TABLES = life.FINANCIAL + life.PHYSICAL + life.BUSINESS


def save():
    (s.OUT / 'peer-recheck-results.json').write_text(json.dumps({
        'candidate': '08065a3b4da71c51ffbbab77f0a6b1ac7e6638ec',
        'classification': LABEL,
        'original_plan_sha256': hashlib.sha256((s.Path(__file__).parent / 'PLAN.md').read_bytes()).hexdigest(),
        'oracle': {
            'numeric': 'Public draft accepted numeric(18,2); valid quantity and policy; posting must conserve its exact amount without integer overflow.',
            'access': 'Current action permission is required for both fresh UUID and cached UUID; active identity alone is insufficient.',
        },
        'peer_exposure': ['BD_INDEPENDENT_AUDIT_20260927.md', 'BD_BLIND_ORACLE_20260927.md'],
        'scope': 'Real PostgreSQL schema and public RPC, real app actor/role permission changes, independently read ledger and atomicity',
        'limits': ['not HTTP/browser', 'opening uninvoiced source, not ordinary receipt lineage',
                   'coverage-by-size policy conclusion is not asserted by these tests',
                   'two successful amount controls do not qualify arbitrary numeric(18,2) amounts'],
        'results': RESULTS,
        'production_go': False,
    }, indent=2, default=str) + '\n')
    (s.OUT / 'peer-recheck-events.json').write_text(json.dumps(EVENTS, indent=2, default=str) + '\n')


def case(key, title, fn):
    start = time.monotonic()
    row = {'id': key, 'classification': LABEL, 'title': title,
           'layer': 'public SQL RPC on fully installed AC..BD schema'}
    try:
        row.update(status='PASS', observation=s.clean(fn()))
    except Exception as e:
        row.update(status='FAIL', error=str(e), traceback=traceback.format_exc())
    row['seconds'] = round(time.monotonic() - start, 4)
    RESULTS.append(row)
    save()
    print(json.dumps({k: row.get(k) for k in ['id', 'status', 'error']}, default=str), flush=True)


def setup():
    C.update(json.loads((s.OUT / 'lifecycle-fixture.json').read_text()))
    available = {n for n, in s.admin("select tablename from pg_tables where schemaname='erp'")}
    TABLES[:] = [n for n in TABLES if n in available]
    life.PHYSICAL[:] = [n for n in life.PHYSICAL if n in available]
    assert {'laundry_deliveries', 'laundry_receipts', 'journal_entries',
            'journal_lines', 'bd_laundry_invoices_v1', 'bd_requests_v1'} <= set(TABLES)
    s.eq(life.billed('ATOMIC'), 0, 'Our original negative-case source has unconsumed capacity')
    policy = s.admin("select value from erp.bd_policy_settings_v1 where policy_key='LAU_DEC06'", one=True)
    s.eq(policy['variance_mode'], 'VARIANCE_ACCOUNT', 'Run directly after lifecycle.py')
    s.eq(str(policy['variance_account_id']), C['expense'])
    for table, column in [('bd_laundry_invoices_v1', 'header_total'), ('bd_laundry_invoice_lines_v1', 'amount')]:
        shape = s.admin('select numeric_precision,numeric_scale from information_schema.columns where table_schema=%s and table_name=%s and column_name=%s', ('erp', table, column))[0]
        s.eq(shape, (18, 2), 'Installed schema accepts the tested amount precision')
        EVENTS.append({'installed_money_column': [table, column], 'precision_scale': shape})
    C['peer_admin'] = s.uid()
    with psycopg.connect(s.DSN) as conn:
        conn.execute("select set_config('app.change_reason','Peer-informed synthetic actor setup',true)")
        role_id = conn.execute("select id from erp.app_roles where role_code='ADMIN' and is_active").fetchone()[0]
        conn.execute('insert into erp.app_users(auth_user_id,full_name,role,role_id) values(%s,%s,%s,%s)',
                     (C['peer_admin'], 'AUD-peer-informed-recheck', 'ADMIN', role_id))
    C['peer_admin_role'] = str(role_id)
    return {'source': life.source('ATOMIC'), 'available_qty': 13, 'boundary_currency': BOUNDARY,
            'actor': C['peer_admin'], 'app_role': C['peer_admin_role']}


def large_invoice(name, amount):
    amount = D(amount)
    text_amount = format(amount, '.2f')
    initial_qty = life.billed('ATOMIC')
    draft = life.draft(name, [life.line('ATOMIC', 1, text_amount)], text_amount)
    raw = life.read_invoice(draft['invoice_id'])
    s.eq(D(str(raw['header_total'])), amount)
    s.eq((D(raw['discount_amount']), D(raw['tax_amount']), D(raw['rounding_amount'])), (D(0), D(0), D(0)))
    state_before = life.fingerprint(TABLES)
    observation = {'amount': text_amount, 'qty': 1, 'source': life.source('ATOMIC'),
                   'draft_accepted': draft, 'before': state_before, 'expected': 'POSTED with exact balanced ledger'}
    try:
        posted = life.post(draft)
    except psycopg.Error as e:
        state_after = life.fingerprint(TABLES)
        observation.update(actual_error=str(e), sqlstate=e.sqlstate, after=state_after,
                           state_after_failure=life.read_invoice(draft['invoice_id']))
        EVENTS.append({'large_invoice': observation})
        s.eq(state_after, state_before, 'Failed posting must remain atomic')
        s.eq(life.billed('ATOMIC'), initial_qty)
        raise AssertionError({'expected': 'POSTED', 'actual': 'SQL error', 'amount': text_amount,
                              'sqlstate': e.sqlstate, 'error': str(e), 'atomic': True}) from e
    # The original synthetic source is 13 PCS at 4,321.09 each.  Each amount
    # probe bills one PCS; neither passing control exhausts the source.
    release = D('4321.09')
    ledger = life.assert_journal(posted['journal_id'], {
        C['AP_VENDOR']: (D(0), amount),
        C['ACCRUED_MANUFACTURING']: (release, D(0)),
        C['expense']: (amount - release, D(0)),
    })
    s.eq(posted['status'], 'POSTED')
    s.eq(life.billed('ATOMIC'), initial_qty + 1)
    s.eq(life.fingerprint(life.PHYSICAL), {n: state_before[n] for n in life.PHYSICAL})
    observation.update(posted=posted, journal=ledger)
    EVENTS.append({'large_invoice': observation})
    return observation


def actor_identity():
    with s.actor_conn('peer_admin') as conn:
        auth_id, app_id, role = conn.execute('select auth.uid(),erp.current_app_user_id(),erp.current_app_role()').fetchone()
    s.eq(str(auth_id), C['peer_admin'])
    assert app_id is not None
    s.eq(role, 'ADMIN')
    return {'auth_id': str(auth_id), 'app_user_id': str(app_id), 'role': role,
            'session_user': 'authenticator', 'current_user': 'authenticated'}


def replay_after_revocation():
    payload = life.payload('PEER-ACCESS', [life.line('ATOMIC', 1, '1731.29')], '1731.29')
    req = s.uid()
    first = s.command('SAVE_INVOICE_DRAFT', payload, req, who='peer_admin')
    s.eq(D(first['header_total']), D('1731.29'))
    before_control = life.fingerprint(TABLES)
    normal_replay = s.command('SAVE_INVOICE_DRAFT', payload, req, who='peer_admin')
    s.eq(normal_replay['invoice_id'], first['invoice_id'])
    s.eq(normal_replay['replayed'], True)
    s.eq(life.fingerprint(TABLES), before_control)
    identity = actor_identity()
    role = C['peer_admin_role']
    saved = s.admin('select role_id::text,permission_key,granted_by::text,granted_at from erp.app_role_permissions where role_id=%s and permission_key=any(%s) order by permission_key', (role, PERMISSION_KEYS))
    assert any(x[1] == 'finance.hpp.manage' for x in saved), 'Positive ADMIN permission fixture absent'
    observation = {'request': req, 'payload': payload, 'first': first, 'valid_replay': normal_replay,
                   'identity_before': identity, 'permission_rows_before': saved}
    # Real rows change; no function is replaced. Restore exact grant rows in
    # finally so subsequent own native/browser suites keep their access fixture.
    try:
        s.admin('delete from erp.app_role_permissions where role_id=%s and permission_key=any(%s)', (role, PERMISSION_KEYS))
        observation['identity_after_revoke'] = actor_identity()
        remaining = s.admin('select permission_key from erp.app_role_permissions where role_id=%s and permission_key=any(%s)', (role, PERMISSION_KEYS))
        s.eq(remaining, [])
        with s.actor_conn('peer_admin') as conn:
            workspace = conn.execute('select public.erp_get_laundry_bd_workspace_v1(%s)', (Jsonb({'vendor_id': C['v1']}),)).fetchone()[0]
        s.eq(workspace['money_visible'], False)
        s.eq(workspace['invoices'], None)
        observation['normal_read_redacted'] = {'money_visible': workspace['money_visible'], 'invoices': workspace['invoices']}
        # Snapshot AFTER permission revocation: administrative fixture changes
        # are not falsely counted as command side effects.
        before = life.fingerprint(TABLES)
        try:
            s.command('SAVE_INVOICE_DRAFT', payload, s.uid(), who='peer_admin')
        except psycopg.Error as e:
            s.eq(e.sqlstate, '42501')
            assert 'finance.hpp.manage' in str(e), str(e)
            observation['fresh_uuid_denied'] = {'sqlstate': e.sqlstate, 'error': str(e)}
        else:
            raise AssertionError('Fresh UUID accepted after real financial permission revocation')
        s.eq(life.fingerprint(TABLES), before)
        try:
            replay = s.command('SAVE_INVOICE_DRAFT', payload, req, who='peer_admin')
        except psycopg.Error as e:
            s.eq(e.sqlstate, '42501')
            assert 'finance.hpp.manage' in str(e), str(e)
            observation['cached_uuid_denied'] = {'sqlstate': e.sqlstate, 'error': str(e)}
            s.eq(life.fingerprint(TABLES), before)
            return observation
        observation['cached_uuid_actual'] = replay
        observation['business_state_unchanged'] = life.fingerprint(TABLES) == before
        s.eq(life.fingerprint(TABLES), before, 'Replay caused no additional business posting')
        raise AssertionError({'expected': 'permission refusal for cached UUID', 'actual': replay,
                              'fresh_uuid_denied': True, 'normal_read_redacted': True,
                              'duplicate_posting': False})
    finally:
        with psycopg.connect(s.DSN) as conn:
            for row in saved:
                conn.execute('insert into erp.app_role_permissions(role_id,permission_key,granted_by,granted_at) values(%s,%s,%s,%s) on conflict(role_id,permission_key) do update set granted_by=excluded.granted_by,granted_at=excluded.granted_at', row)
        restored = s.admin('select role_id::text,permission_key,granted_by::text,granted_at from erp.app_role_permissions where role_id=%s and permission_key=any(%s) order by permission_key', (role, PERMISSION_KEYS))
        observation['permission_rows_restored'] = restored
        EVENTS.append({'revocation_replay': observation})
        s.eq(restored, saved, 'Exact original role permissions restored for subsequent tests')


def main():
    try:
        EVENTS.append({'setup': setup()})
    except Exception as e:
        RESULTS.append({'id': 'SETUP.PEER-RECHECK', 'classification': LABEL, 'status': 'BLOCKED',
                        'error': str(e), 'traceback': traceback.format_exc()})
        save()
        print(json.dumps(RESULTS[-1]), flush=True)
        return 1
    case('PEER-NUMERIC.SMALL', 'Independent small invoice proves valid source, policy and ledger path', lambda: large_invoice('PEER-SMALL', D('18931.27')))
    case('PEER-NUMERIC.BELOW', 'Accepted invoice one cent below int-cent boundary posts exact ledger', lambda: large_invoice('PEER-LOW', BOUNDARY - D('0.01')))
    case('PEER-NUMERIC.AT', 'Accepted invoice at int-cent boundary posts exact ledger', lambda: large_invoice('PEER-EDGE', BOUNDARY))
    case('PEER-NUMERIC.ABOVE', 'Accepted invoice one cent above int-cent boundary posts exact ledger', lambda: large_invoice('PEER-HIGH', BOUNDARY + D('0.01')))
    case('PEER-NUMERIC.LARGE', 'Accepted 28,123,456.78 invoice posts without incidental integer limit', lambda: large_invoice('PEER-LARGE', D('28123456.78')))
    case('PEER-ACCESS.REVOKED', 'Real permission revocation denies both new and cached UUID', replay_after_revocation)
    save()
    print(json.dumps({'peer_recheck_counts': {x: sum(r['status'] == x for r in RESULTS) for x in ['PASS', 'FAIL', 'BLOCKED']}}), flush=True)
    return 1 if any(r['status'] != 'PASS' for r in RESULTS) else 0


if __name__ == '__main__':
    raise SystemExit(main())
