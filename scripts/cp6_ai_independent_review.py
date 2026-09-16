#!/usr/bin/env python3
"""Independent business observations on exact AI-R2 and disposable data only.

Existing helpers supply physical fixtures and session switching. Expected
amounts, state transitions and concurrent outcomes are specified here.
The candidate checkout and its installed functions are never edited.
"""
from pathlib import Path
from datetime import timedelta
from decimal import Decimal
import argparse
import hashlib
import json
import os
import subprocess
import sys
import threading
import traceback
import uuid

sys.path.insert(0, str(Path.cwd() / 'scripts'))
import psycopg
import cp6_ah_independent_review as fixture
import cp6_v2620ai_runtime as runtime
import cp6_v2620af_concurrency as sessions
from cp6_v2620n_rollback_guards import function_catalog
from cp6_v2620u_install_diagnostic import snapshot

HEAD = '25fa4736329e5148dfdb3572bc169952cba23251'
TREE = 'a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d'
ROOT = Path('cp6-proof/independent-ai')
URL = 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'
ADMIN = URL.replace('postgres:postgres@', 'supabase_admin:postgres@')
actors, base, prior, peer = fixture.actors, fixture.base, fixture.prior, fixture.peer


def save(name, value):
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / (name + '.json')).write_text(json.dumps(value, indent=2, default=str) + '\n')


def normalized(value):
    return json.loads(json.dumps(value, default=str))


def verify_source():
    git = lambda *args: subprocess.check_output(['git', *args], text=True).strip()
    assert (git('rev-parse', 'HEAD'), git('rev-parse', 'HEAD^{tree}')) == (HEAD, TREE)
    assert not git('diff', '--name-only', 'HEAD'), 'Candidate tracked files changed'
    assert os.environ.get('PGURL') == URL
    assert os.environ.get('CP6_AI_INDEPENDENT_CONFIRM') == 'postgres'
    runtime.verify_source_files()


def observe(cur, completion):
    return fixture.work_state(cur, completion)


def total(state):
    return sum((Decimal(str(line['debit'])) for line in state['journal_lines'] or []), Decimal(0))


def success(operation):
    assert not operation['refused'], operation
    return operation


def call(cur, query, params=(), *, ordinary=True):
    if ordinary:
        peer.ordinary(cur)
    identity = cur.execute('select current_user,session_user,erp.current_app_role()').fetchone()
    cur.execute('savepoint ai_operation')
    record = dict(identity=identity, refused=False)
    try:
        cur.execute(query, params)
        record['changed'] = cur.rowcount
        record['rows'] = cur.fetchall() if cur.description else []
    except psycopg.Error as exc:
        record.update(refused=True, sqlstate=exc.sqlstate, error=str(exc))
        cur.execute('rollback to savepoint ai_operation')
    cur.execute('release savepoint ai_operation')
    return record


def clean_refusal(cur, query, params=()):
    actors.admin(cur)
    before = actors.boundary(cur)
    record = call(cur, query, params)
    assert record['refused'], record
    assert record['sqlstate'] in ('P0001', '23514', '23505', '42501'), record
    actors.admin(cur)
    assert actors.boundary(cur) == before, 'Refused operation changed data'
    return record


def ready(cur, day):
    report = peer.confidence(cur, day)
    assert report['data_confidence']['status'] == 'READY', report
    return report


def draft(cur, day, rate=Decimal('1.25')):
    return fixture.work_draft(cur, day, rate)


def second_draft(cur, f, qty, payable):
    peer.ordinary(cur)
    ident = uuid.uuid4()
    cur.execute("""insert into erp.work_completion_events
      (id,completion_number,po_id,contractor_id,cutting_group_id,physical_at,status,notes,created_by)
      select %s,%s,po_id,contractor_id,cutting_group_id,physical_at,'DRAFT',
        'Independent AI second ordinary draft',created_by
      from erp.work_completion_events where id=%s""", (ident, 'AI-PEER-' + ident.hex, f['completion']))
    cur.execute("""insert into erp.work_completion_lines
      (completion_id,po_component_snapshot_id,work_component_id,qty_completed,qty_payable,rate_snapshot)
      values(%s,%s,%s,%s,%s,0)""", (ident, f['snapshot'], f['component'], qty, payable))
    return ident


def positive(mode):
    def case(cur, day):
        rate = Decimal('0') if mode == 'ZERO_RATE' else Decimal('1.27')
        f = draft(cur, day, rate)
        qty, payable = (10, 0) if mode == 'UNPAID' else (7, 5) if mode == 'PARTIAL_PAY' else (10, 10)
        success(call(cur, 'update erp.work_completion_lines set qty_completed=%s,qty_payable=%s where completion_id=%s',
                     (qty, payable, f['completion'])))
        if mode == 'TIMEZONE':
            cur.execute("set local timezone='Pacific/Kiritimati'")
        operation = success(call(cur, 'select erp.post_work_completion(%s)', (f['completion'],)))
        state = observe(cur, f['completion'])
        expected = rate * payable
        assert state['header']['status'] == 'POSTED' and total(state) == expected, state
        assert len(state['journal'] or []) == (1 if expected else 0), state
        if expected:
            physical = cur.execute("select (physical_at at time zone 'Asia/Jakarta')::date from erp.work_completion_events where id=%s", (f['completion'],)).fetchone()[0]
            assert all(j['transaction_date'] == physical.isoformat() and j['economic_date'] == physical.isoformat()
                       for j in state['journal']), state
        report = ready(cur, day)
        return dict(status='CONTROL_PASS', expected_amount=expected, operation=operation, state=state, report=report)
    return case


def refusal_case(mode):
    def case(cur, day):
        f = draft(cur, day)
        params = (f['completion'],)
        if mode == 'DIRECT_POST':
            query = "update erp.work_completion_events set status='POSTED' where id=%s"
        elif mode == 'PO_CONTRACTOR':
            query, params = 'update erp.production_orders set contractor_id=null where id=%s', (f['po'],)
        elif mode == 'SNAPSHOT_DELETE':
            query, params = 'delete from erp.po_work_component_snapshots where id=%s', (f['snapshot'],)
        elif mode == 'PAYABLE_EXCEEDS_COMPLETED':
            query = 'update erp.work_completion_lines set qty_payable=11 where completion_id=%s'
        elif mode == 'NEGATIVE_PAYABLE':
            query = 'update erp.work_completion_lines set qty_payable=-1 where completion_id=%s'
        elif mode == 'EMPTY_POST':
            success(call(cur, 'delete from erp.work_completion_lines where completion_id=%s', params))
            query = 'select erp.post_work_completion(%s)'
        elif mode in ('BEFORE_PICKUP', 'FUTURE'):
            delta = "interval '-2 hours'" if mode == 'BEFORE_PICKUP' else "interval '30 days'"
            success(call(cur, f'update erp.work_completion_events set physical_at=physical_at+{delta} where id=%s', params))
            query = 'select erp.post_work_completion(%s)'
        else:
            success(call(cur, 'select erp.post_work_completion(%s)', params))
            query = {
                'DOUBLE_POST': 'select erp.post_work_completion(%s)',
                'POSTED_EDIT': 'update erp.work_completion_lines set qty_payable=1 where completion_id=%s',
                'POSTED_DELETE': 'delete from erp.work_completion_lines where completion_id=%s',
                'POSTED_HEADER': 'update erp.work_completion_events set physical_at=physical_at+interval \'1 minute\' where id=%s',
            }[mode]
        refusal = clean_refusal(cur, query, params)
        return dict(status='CONTROL_PASS', refusal=refusal, state=observe(cur, f['completion']))
    return case


def reverse_and_reuse(cur, day):
    f = draft(cur, day)
    success(call(cur, 'select erp.post_work_completion(%s)', (f['completion'],)))
    success(call(cur, "select erp.reverse_work_completion(%s,'Independent complete correction')", (f['completion'],)))
    actors.admin(cur)
    before = actors.boundary(cur)
    success(call(cur, "select erp.reverse_work_completion(%s,'Independent complete correction')", (f['completion'],)))
    actors.admin(cur)
    assert actors.boundary(cur) == before, 'Repeated reversal changed data'
    ident = second_draft(cur, f, 10, 10)
    success(call(cur, 'select erp.post_work_completion(%s)', (ident,)))
    state = observe(cur, ident)
    assert state['header']['status'] == 'POSTED' and total(state) == Decimal('12.50'), state
    return dict(status='CONTROL_PASS', repeated_reversal_unchanged=True, replacement=state, report=ready(cur, day))


def role_case(mode):
    def case(cur, day):
        f = draft(cur, day)
        fixture.qualified_work_control(cur, f)
        actors.admin(cur)
        claims = {'sub': str(uuid.uuid4()), 'role': 'authenticated'}
        if mode == 'INACTIVE_OWNER':
            # Keep the last active owner intact. Only this separate synthetic
            # app user is inactive; its OWNER role remains the original role.
            cur.execute("""insert into erp.app_users
              select (jsonb_populate_record(null::erp.app_users,to_jsonb(u)||
                jsonb_build_object('id',%s::text,'auth_user_id',%s::text,
                  'full_name','Independent inactive owner','is_active',false))).*
              from erp.app_users u where id=%s""", (str(uuid.uuid4()), claims['sub'], base.OPERATOR_APP))
        if mode == 'EMPTY_CLAIMS':
            claims = {}
        actors.actors.claims(cur, claims)
        before = actors.boundary(cur)
        actors.actors.session(cur, 'authenticated')
        record = call(cur, 'select erp.post_work_completion(%s)', (f['completion'],), ordinary=False)
        assert record['identity'] == ('authenticated', 'authenticated', None), record
        state = observe(cur, f['completion'])
        if record['refused']:
            assert actors.boundary(cur) == before
            return dict(status='CONTROL_PASS', role_context=mode, operation=record, state=state)
        assert state['header']['status'] == 'POSTED' and total(state) == Decimal('12.50'), state
        return dict(status='BUG_PROVEN', family='WORK_POSTING_REQUIRES_ACTIVE_APP_USER', role_context=mode,
                    operation=record, state=state, expected='No active ERP role: posting must be refused without data changes.',
                    native_sql_only=True, schema_usage_fixture_grant=True, production_functions_unchanged=True)
    return case


def work_through_hpp(rate):
    def case(cur, day):
        production = fixture.production
        ledger_before = production.ledger(cur)
        reports_before = production.reports(cur, day)
        f = production.estimated_receipt(cur, day)
        f.update(ledger_baseline=ledger_before, report_baseline=reports_before)
        class WorkRateCursor:
            def __getattr__(self, name):
                return getattr(cur, name)
            def execute(self, query, params=None, **kwargs):
                text = str(query)
                if 'insert into erp.po_work_component_snapshots(' in text:
                    assert 'values(%s,%s,%s,1,0,%s)' in text
                    query = text.replace('values(%s,%s,%s,1,0,%s)', 'values(%s,%s,%s,1,%s,%s)')
                    params = (*params[:3], rate, params[3])
                if 'insert into erp.work_completion_events(' in text or 'insert into erp.work_completion_lines(' in text:
                    peer.ordinary(cur)
                return cur.execute(query, params, **kwargs)
        production.partial_production(WorkRateCursor(), f)
        state = production.observe(cur, f, day)
        # Physical fixture: ten raw units at 10, ten wash units at 7,
        # ten completed/payable work units at the independently supplied rate.
        # Five pieces become FG, two are sold, three remain, five remain WIP.
        unit = Decimal('17') + rate
        expected_po = dict(base_output=5, hpp_total=5 * unit, fg_qty=3,
                           fg_value=3 * unit, cogs_value=2 * unit, other_value=0, wip_value=5 * unit)
        expected_ledger = dict(MATERIAL_INVENTORY=0, WIP=5 * unit, FG_INVENTORY=3 * unit,
                               COGS=2 * unit, AP_SUPPLIER=0, GRNI_MATERIAL=-100)
        mismatches = {}
        for key, expected in expected_po.items():
            actual = (state.get('production') or {}).get(key)
            if actual is None or Decimal(str(actual)) != expected:
                mismatches['production.' + key] = dict(expected=expected, actual=actual)
        for key, expected in expected_ledger.items():
            if state['ledger_delta'][key] != expected:
                mismatches['ledger.' + key] = dict(expected=expected, actual=state['ledger_delta'][key])
            report_expected = -expected if key in ('AP_SUPPLIER', 'GRNI_MATERIAL') else expected
            if state['report_delta'][key] != report_expected:
                mismatches['report.' + key] = dict(expected=report_expected, actual=state['report_delta'][key])
        assert state['raw_qty'] == 0 and state['custody'] == dict(sent=10, received=8, sold=2), state
        assert not mismatches, mismatches
        assert state['confidence']['status'] == 'READY', state['confidence']
        return dict(status='CONTROL_PASS', supplied_work_rate=rate, independent_unit_cost=unit,
                    expected_production=expected_po, state=state)
    return case


def cases():
    result = [('WORK_' + mode, positive(mode)) for mode in ('CENTS', 'ZERO_RATE', 'UNPAID', 'PARTIAL_PAY', 'TIMEZONE')]
    result += [(mode, refusal_case(mode)) for mode in ('DIRECT_POST', 'PO_CONTRACTOR', 'SNAPSHOT_DELETE',
               'PAYABLE_EXCEEDS_COMPLETED', 'NEGATIVE_PAYABLE', 'EMPTY_POST', 'BEFORE_PICKUP', 'FUTURE',
               'DOUBLE_POST', 'POSTED_EDIT', 'POSTED_DELETE', 'POSTED_HEADER')]
    result += [('REVERSE_REUSE', reverse_and_reuse)]
    result += [('ROLE_' + mode, role_case(mode)) for mode in ('UNREGISTERED', 'INACTIVE_OWNER', 'EMPTY_CLAIMS')]
    result += [('HPP_THROUGH_SALE_' + str(rate), work_through_hpp(rate)) for rate in (Decimal('0'), Decimal('1.27'))]
    return result


def business():
    result = dict(status='INCOMPLETE', candidate_head=HEAD, candidate_tree=TREE,
                  harness_head=os.environ['CP6_AUDIT_HARNESS_HEAD'], source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  cases={}, production_go=False, http_ui_csv_reachability_proven=False)
    with psycopg.connect(ADMIN) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='180s';set local lock_timeout='8s'")
        assert len(runtime.verified_successor(cur)) == 690
        catalog, untouched = function_catalog(cur), actors.boundary(cur)
        usage = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0]
        result['schema_usage_fixture_grant'] = not usage
        if not usage:
            cur.execute('grant usage on schema erp to authenticated')
        actors.actors.claims(cur, {'sub': base.OPERATOR_AUTH, 'role': 'authenticated'})
        base.load_fixture_foundation(cur)
        actors.admin(cur)
        day = base.one(cur, "select (statement_timestamp() at time zone 'Asia/Jakarta')::date") - timedelta(days=3)
        prior.set_open_period(cur, day - timedelta(days=5))
        save('LIVE_WORK_CONTRACT', cur.execute("""select p.oid::regprocedure::text,pg_get_functiondef(p.oid),p.proacl
          from pg_proc p where p.oid in('erp.require_internal()'::regprocedure,'erp.current_app_role()'::regprocedure,
          'erp.post_work_completion(uuid)'::regprocedure) order by 1""").fetchall())
        for name, fn in cases():
            actors.admin(cur)
            before = actors.boundary(cur)
            cur.execute('savepoint independent_case')
            try:
                record = fn(cur, day)
            except Exception as exc:
                record = dict(status='INCOMPLETE', error=str(exc), traceback=traceback.format_exc())
            finally:
                cur.execute('rollback to savepoint independent_case')
                actors.admin(cur)
                cur.execute('release savepoint independent_case')
            record['full_boundary_restored'] = actors.boundary(cur) == before
            if not record['full_boundary_restored']:
                record['status'] = 'INCOMPLETE'
            result['cases'][name] = record
            save('RESULT', result)
            print(json.dumps(dict(case=name, status=record['status'], error=record.get('error'))), flush=True)
        actors.admin(cur)
        result['function_catalog_unchanged'] = function_catalog(cur) == catalog
        conn.rollback()
        cur.execute("set local timezone='Asia/Jakarta'")
        result['unseeded_boundary_restored'] = actors.boundary(cur) == untouched
        result['schema_usage_restored'] = cur.execute("select has_schema_privilege('authenticated','erp','USAGE')").fetchone()[0] == usage
        result['auth_users'], result['app_users'] = cur.execute('select (select count(*) from auth.users),(select count(*) from erp.app_users)').fetchone()
        conn.rollback()
    result.update(controls=sum(c['status'] == 'CONTROL_PASS' for c in result['cases'].values()),
                  bugs=sum(c['status'] == 'BUG_PROVEN' for c in result['cases'].values()),
                  incomplete=sum(c['status'] == 'INCOMPLETE' for c in result['cases'].values()))
    if all(result[k] for k in ('function_catalog_unchanged', 'unseeded_boundary_restored', 'schema_usage_restored')) and result['auth_users'] == result['app_users'] == result['incomplete'] == 0:
        result['status'] = 'BUG_PROVEN' if result['bugs'] else 'PASS_REVIEWED_SCOPE'
    save('RESULT', result)
    return result


def concurrent_case(kind, abort):
    with sessions.connect('ai-independent-fixture') as conn, conn.cursor() as cur:
        day = base.one(cur, "select (statement_timestamp() at time zone 'Asia/Jakarta')::date") - timedelta(days=3)
        f = draft(cur, day)
        if kind == 'GROUP_TWO_POST':
            success(call(cur, 'update erp.work_completion_lines set qty_completed=6,qty_payable=6 where completion_id=%s', (f['completion'],)))
            f['second'] = second_draft(cur, f, 6, 6)
    def post(cur, f):
        peer.ordinary(cur)
        cur.execute('select erp.post_work_completion(%s)', (f['completion'],))
    def other_post(cur, f):
        peer.ordinary(cur)
        cur.execute('select erp.post_work_completion(%s)', (f['second'],))
    def quantity(cur, f):
        peer.ordinary(cur)
        cur.execute('update erp.work_completion_lines set qty_completed=6,qty_payable=4 where completion_id=%s', (f['completion'],))
    def delete(cur, f):
        peer.ordinary(cur)
        cur.execute('delete from erp.work_completion_lines where completion_id=%s', (f['completion'],))
    first_fn, second_fn = {'DOUBLE_POST': (post, post), 'QTY_POST': (quantity, post), 'POST_QTY': (post, quantity),
                           'DELETE_POST': (delete, post), 'POST_DELETE': (post, delete), 'GROUP_TWO_POST': (post, other_post)}[kind]
    response, thread = {}, None
    with sessions.connect('ai-independent-first') as first, sessions.connect('ai-independent-second') as second:
        try:
            with first.cursor() as cur:
                first_fn(cur, f)
            thread = threading.Thread(target=sessions.worker, args=(second, second_fn, f, response), daemon=True)
            thread.start()
            lock = sessions.await_lock(second.info.backend_pid)
            assert first.info.backend_pid in lock[2], lock
            first.rollback() if abort else first.commit()
            thread.join(30)
            assert not thread.is_alive(), 'Second session did not finish'
        finally:
            first.rollback()
            if thread is not None and thread.is_alive():
                second.cancel()
                thread.join(5)
    expected_commit = abort or kind == 'QTY_POST'
    assert bool(response.get('committed')) == expected_commit, response
    if not expected_commit:
        assert response.get('sqlstate') == 'P0001', response
    with sessions.connect('ai-independent-observe') as conn, conn.cursor() as cur:
        state = observe(cur, f['completion'])
        posted = kind in ('DOUBLE_POST', 'QTY_POST') or (kind in ('POST_QTY', 'POST_DELETE', 'GROUP_TWO_POST') and not abort) or (kind == 'DELETE_POST' and abort)
        expected = Decimal('7.50') if kind == 'GROUP_TWO_POST' else Decimal('5') if kind == 'QTY_POST' and not abort else Decimal('12.50')
        assert state['header']['status'] == ('POSTED' if posted else 'DRAFT'), state
        assert total(state) == (expected if posted else 0), state
        if kind == 'GROUP_TWO_POST':
            other = observe(cur, f['second'])
            assert other['header']['status'] == ('POSTED' if abort else 'DRAFT'), other
            assert total(state) + total(other) == Decimal('7.50'), (state, other)
        if kind == 'POST_QTY' and abort:
            success(call(cur, 'select erp.post_work_completion(%s)', (f['completion'],)))
            assert total(observe(cur, f['completion'])) == Decimal('5')
        report = ready(cur, day)
    return dict(status='CONTROL_PASS', kind=kind, first_aborted=abort, observed_lock=lock, second=response, state=state, report=report)


def concurrency():
    result = dict(status='INCOMPLETE', candidate_head=HEAD, cases=[], production_go=False, schema_usage_fixture_grant=True)
    ROOT.mkdir(parents=True, exist_ok=True)
    try:
        sessions.matrix.command(['bash', 'scripts/clone-cp6-disposable-database.sh', sessions.SOURCE,
          sessions.matrix.MAINTENANCE, sessions.matrix.CLONE, 'cp6_rollback', sessions.matrix.CONTAINER,
          str(ROOT / 'CLONE_BOUNDARY')], ROOT / 'clone.log')
        with sessions.connect('ai-independent-foundation') as conn, conn.cursor() as cur:
            cur.execute('grant usage on schema erp to authenticated')
            actors.actors.claims(cur, {'sub': base.OPERATOR_AUTH, 'role': 'authenticated'})
            base.load_fixture_foundation(cur)
            actors.admin(cur)
            day = base.one(cur, "select (statement_timestamp() at time zone 'Asia/Jakarta')::date") - timedelta(days=3)
            prior.set_open_period(cur, day - timedelta(days=5))
        for kind in ('DOUBLE_POST', 'QTY_POST', 'POST_QTY', 'DELETE_POST', 'POST_DELETE', 'GROUP_TWO_POST'):
            for abort in (False, True):
                try:
                    record = concurrent_case(kind, abort)
                except Exception as exc:
                    record = dict(status='INCOMPLETE', kind=kind, first_aborted=abort, error=str(exc), traceback=traceback.format_exc())
                result['cases'].append(record)
                save('CONCURRENCY', result)
                print(json.dumps({k: v for k, v in record.items() if k in ('status', 'kind', 'first_aborted', 'error')}), flush=True)
    finally:
        sessions.matrix.legacy.drop_clone()
    with psycopg.connect(sessions.matrix.MAINTENANCE) as conn:
        result['clone_removed'] = conn.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0] == 0
    if result['clone_removed'] and len(result['cases']) == 12 and all(c['status'] == 'CONTROL_PASS' for c in result['cases']):
        result['status'] = 'PASS_REVIEWED_SCOPE'
    save('CONCURRENCY', result)
    return result


def capture_ah():
    with psycopg.connect(ADMIN) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta'")
        runtime.verify_predecessor(cur)
        save('OWN_AH_BASELINE', dict(catalog=function_catalog(cur), boundary=snapshot(cur)))
    return dict(status='PASS_REVIEWED_SCOPE', captured='Original AH before AI installation')


def rollback():
    import cp6_preuse_rollback_maintenance as maintenance
    before = json.loads((ROOT / 'OWN_AH_BASELINE.json').read_text())
    with psycopg.connect(ADMIN) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta'")
        assert len(runtime.verified_successor(cur)) == 690
    operation = maintenance.run_maintenance_rollback(target_name='AI', target_pgurl=URL,
        maintenance_pgurl=os.environ['CP6_ADMISSION_CONTROL_PGURL'], report_path=ROOT / 'MAINTENANCE.json',
        drain_timeout=10, natural_grace=0, terminate_after_grace=True)
    with psycopg.connect(ADMIN) as conn, conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta'")
        runtime.verify_predecessor(cur)
        actual = normalized(dict(catalog=function_catalog(cur), boundary=snapshot(cur)))
        users = cur.execute('select (select count(*) from auth.users),(select count(*) from erp.app_users)').fetchone()
    assert before == actual, 'Independent AH boundary differs after rollback'
    assert len(actual['catalog']) == 533 and len(actual['boundary']['tables']) == 223 and users == (0, 0)
    result = dict(status='PASS_REVIEWED_SCOPE', functions=533, tables=223, full_boundary_exact=True,
                  auth_users=users[0], app_users=users[1], operation=operation, production_go=False)
    save('EXACT_RESTORE', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=('capture', 'business', 'concurrency', 'rollback'), required=True)
    args = parser.parse_args()
    try:
        verify_source()
        result = {'capture': capture_ah, 'business': business, 'concurrency': concurrency, 'rollback': rollback}[args.phase]()
    except Exception as exc:
        result = dict(status='INCOMPLETE', error=str(exc), traceback=traceback.format_exc(), production_go=False)
        save(args.phase.upper() + '_FAILURE', result)
    print(json.dumps({k: v for k, v in result.items() if k not in ('cases', 'operation')}, default=str))
    raise SystemExit(0 if result['status'] == 'PASS_REVIEWED_SCOPE' else 1)
