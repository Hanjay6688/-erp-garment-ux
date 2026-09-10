#!/usr/bin/env python3
"""G01 qualification: exact F/G rollback vs real backend operations.

Five operations x four orders x two rollback targets. These are native SQL
business-function races with the configured operator JWT, not HTTP/Auth proof.
No manual lock is taken by the writer. Only ROLLBACK_FIRST uses a third-session
gate; pg_blocking_pids must identify the actual rollback as the writer blocker.
Each case uses a fresh, physically cloned, exact-loopback disposable database.
"""
from __future__ import annotations
import hashlib
import json
import os
import subprocess
import threading
import time
import uuid
from decimal import Decimal
from pathlib import Path

import psycopg

import cp6_v2620e_counterexample_regression as base

ROOT = Path('cp6-proof/G_EXPANDED_ROLLBACK')
SOURCE = 'postgresql://postgres:postgres@127.0.0.1:54322/postgres'
MAINTENANCE = 'postgresql://postgres:postgres@127.0.0.1:54322/template1'
CLONE = 'postgresql://postgres:postgres@127.0.0.1:54322/cp6_rollback'
CONTAINER = 'supabase_db_cp5-local'
TARGETS = {
    'F': ('20260909174713', 'erp_v2_6_20f_cp6_final_runtime_reliability', 'v2.6.20f', 'v2.6.20e'),
    'G': ('20260910031103', 'erp_v2_6_20g_cp6_independent_audit_closure', 'v2.6.20g', 'v2.6.20f'),
}
OPERATIONS = ('SALE', 'RETURN', 'CONVERSION', 'REPORT', 'FK_SYNC')
MODES = ('WRITER_FIRST', 'ROLLBACK_FIRST', 'WRITER_ABORT', 'ROLLBACK_LOCK_TIMEOUT')


def path(target, rollback=False):
    stamp, name, _, _ = TARGETS[target]
    folder, suffix = ('rollbacks', '.rollback.sql') if rollback else ('migrations', '.sql')
    return Path(f'supabase/{folder}/{stamp}_{name}{suffix}')


def connect(name):
    return psycopg.connect(CLONE, autocommit=False, application_name=name)


def scalar(query, params=()):
    with connect('g-rollback-observer') as conn, conn.cursor() as cur:
        return base.one(cur, query, params)


def command(args, log):
    with log.open('w') as output:
        subprocess.run(args, stdout=output, stderr=subprocess.STDOUT, check=True, timeout=180)


def drop_clone():
    # Exact validated target; never derive a destructive target from broad paths.
    subprocess.run(['docker', 'exec', CONTAINER, 'dropdb', '-U', 'supabase_admin',
                    '--if-exists', '--force', '--maintenance-db=template1', 'cp6_rollback'],
                   check=True, timeout=30, stdout=subprocess.DEVNULL)
    remaining = subprocess.check_output(['docker', 'exec', CONTAINER, 'psql', '-U',
        'supabase_admin', '-d', 'template1', '-X', '-At', '-v', 'ON_ERROR_STOP=1',
        '-c', "select count(*) from pg_database where datname='cp6_rollback'"], text=True).strip()
    if remaining != '0':
        raise AssertionError('Disposable clone cleanup not proven')


def operator(cur):
    cur.execute("select set_config('request.jwt.claims',%s,true)",
                (json.dumps({'sub': base.OPERATOR_AUTH, 'role': 'authenticated'}),))
    cur.execute("select set_config('app.physical_at','',true)")
    cur.execute("select set_config('app.change_reason','G native backend rollback qualification',true)")


def seed(cur, operation):
    operator(cur)
    base.load_fixture_foundation(cur)
    operator(cur)
    product = base.create_product(cur, f'G-RB-{operation}')
    customer = base.create_customer(cur, f'G-RB-{operation}')
    fixture = {'product': product, 'customer': customer, 'request': str(uuid.uuid4())}
    if operation == 'CONVERSION':
        po = {'po': 'c8c40000-0000-4000-8000-000000000001',
              'group': 'c8c40000-0000-4000-8000-000000000003',
              'batch': 'c8c40000-0000-4000-8000-000000000008'}
        delivery = base.post_delivery(cur, po, base.BASE_PROCESS, '2026-09-01T11:00:00Z')
        _, size, line = base.post_receipt(cur, delivery['delivery_id'], base.BASE_PROCESS, '2026-09-02T11:00:00Z')
        base.post_final(cur, po, product, size, line, '2026-09-02T13:00:00Z')
        target_product = base.create_product(cur, 'G-RB-CONVERT-TARGET')
        conversion = str(uuid.uuid4())
        cur.execute("""insert into erp.product_conversions(id,conversion_number,from_product_id,
          to_product_id,location_id,qty_pcs,conversion_type,physical_at,status,conversion_cost_total,
          notes,created_by) values(%s,%s,%s,%s,%s,2,'RELABEL','2026-09-03T09:00:00Z',
          'DRAFT',0,'G actual value-preserving backend conversion',%s)""",
          (conversion, 'G-RB-' + conversion, product, target_product, base.LOCATION, base.OPERATOR_APP))
        fixture.update(conversion=conversion, target_product=target_product, po=po['po'])
    else:
        opening = str(uuid.uuid4())
        cur.execute("""insert into erp.opening_balance_headers(id,opening_number,opening_date,status,created_by)
          values(%s,%s,'2026-09-01','DRAFT',%s)""", (opening, 'G-RB-' + opening, base.OPERATOR_APP))
        cur.execute("""insert into erp.opening_balance_items(opening_id,balance_type,product_id,
          location_id,qty,unit_cost_snapshot,quality_grade,hpp_input_method)
          values(%s,'FINISHED_GOODS',%s,%s,10,%s,'GRADE_A','MANUAL')""",
          (opening, product, base.LOCATION, Decimal('.011') if operation == 'FK_SYNC' else Decimal('7')))
        base.one(cur, 'select erp.post_opening_balance(%s)', (opening,))
        if operation in ('SALE', 'RETURN', 'FK_SYNC'):
            sale = base.create_sale(cur, product, customer, 4 if operation == 'FK_SYNC' else 5)
            fixture.update(sale=sale['sale_id'], version=int(sale['row_version']))
            if operation in ('RETURN', 'FK_SYNC'):
                base.one(cur, 'select erp.post_sale(%s)', (sale['sale_id'],))
            if operation == 'RETURN':
                fixture['return'] = base.insert_return(cur, sale['sale_id'], customer, 2, Decimal('40'), 0)
            if operation == 'FK_SYNC':
                next_sale = base.create_sale(cur, product, customer, 1)
                fixture.update(next_sale=next_sale['sale_id'], next_version=int(next_sale['row_version']))
    return fixture


def capture_capsule(target):
    name = f'erp.cp6_v2620{target.lower()}_rollback_capsule'
    return scalar(f"""select jsonb_agg(jsonb_build_object('identity',object_regidentity,
      'before_sha256',definition_sha256,'installed_sha256',installed_definition_sha256,
      'owner',owner_snapshot,'acl',acl_snapshot) order by object_regidentity) from {name}""")


def verify_functions(capsule, installed):
    observed = []
    for obj in capsule:
        actual = scalar("""select jsonb_build_object(
          'sha256',encode(extensions.digest(convert_to(pg_get_functiondef(p.oid),'UTF8'),'sha256'),'hex'),
          'owner',pg_get_userbyid(p.proowner),'acl',case when p.proacl is null then null
            else to_jsonb(array(select a::text from unnest(p.proacl) a order by a::text)) end)
          from pg_proc p where p.oid=to_regprocedure(%s)""", (obj['identity'],))
        expected = {'sha256': obj['installed_sha256' if installed else 'before_sha256'],
                    'owner': obj['owner'], 'acl': obj['acl']}
        if actual != expected:
            raise AssertionError(f'Exact function/ACL restoration mismatch {obj["identity"]}: {actual} != {expected}')
        observed.append({'identity': obj['identity'], 'expected': expected, 'actual': actual})
    return observed


def prepare(target, operation, folder):
    command(['bash', 'scripts/clone-cp6-disposable-database.sh', SOURCE, MAINTENANCE,
             CLONE, 'cp6_rollback', CONTAINER, str(folder / 'PHYSICAL_BOUNDARY')], folder / 'clone.log')
    # Source is final G. Roll it back pre-use; seed under the actual predecessor
    # before installing a fresh target capsule. Never forge installation times.
    command(['psql', CLONE, '-X', '-v', 'ON_ERROR_STOP=1', '-f', str(path('G', True))], folder / 'strip_g.log')
    if target == 'F':
        command(['psql', CLONE, '-X', '-v', 'ON_ERROR_STOP=1', '-f', str(path('F', True))], folder / 'strip_f.log')
    with connect('g-rollback-predecessor-fixture') as conn, conn.cursor() as cur:
        fixture = seed(cur, operation)
        conn.commit()
    command(['psql', CLONE, '-X', '-v', 'ON_ERROR_STOP=1', '-f', str(path(target))], folder / 'install.log')
    stamp, name, _, _ = TARGETS[target]
    with connect('g-rollback-exact-platform-ledger') as conn, conn.cursor() as cur:
        cur.execute('insert into supabase_migrations.schema_migrations(version,name,statements) values(%s,%s,%s)',
                    (stamp, name, [path(target).read_text()]))
        conn.commit()
    capsule = capture_capsule(target)
    if len(capsule) != (8 if target == 'F' else 7):
        raise AssertionError('Wrong target capsule count')
    verify_functions(capsule, True)
    return fixture, capsule


def business(cur, operation, f):
    operator(cur)
    if operation == 'SALE':
        return base.one(cur, 'select erp.post_sale_v2(%s,%s,%s)', (f['sale'], f['request'], f['version']))
    if operation == 'RETURN':
        base.one(cur, 'select erp.post_sales_return(%s)', (f['return'],))
        return {'return_posted': f['return']}
    if operation == 'CONVERSION':
        base.one(cur, 'select erp.post_product_conversion(%s)', (f['conversion'],))
        return {'conversion_posted': f['conversion']}
    if operation == 'FK_SYNC':
        base.one(cur, 'select erp.post_sale_v2(%s,%s,%s)', (f['next_sale'], f['request'], f['next_version']))
        base.one(cur, "select erp.reverse_sale(%s,'G native actual linked sale reversal')", (f['sale'],))
        # F's append-only synchronizer must really insert a row whose product,
        # journal and created_by foreign keys reference the locked parent tables.
        present = base.one(cur, "select to_regclass('erp.non_po_hpp_gl_sync_events_v2620f') is not null")
        count = base.one(cur, 'select count(*) from erp.non_po_hpp_gl_sync_events_v2620f where product_id=%s', (f['product'],)) if present else None
        if present and count < 1:
            raise AssertionError('FK_SYNC did not exercise the real F event-table FK insert')
        return {'fk_event_rows': count, 'predecessor_without_f_event_table': not present}
    return base.one(cur, "select erp.get_owner_financial_snapshot_v2('2026-09-01',current_date,current_date)")


def facts(f):
    with connect('g-rollback-business-facts') as conn, conn.cursor() as cur:
        result = {'stock': base.one(cur, 'select coalesce(sum(cached_qty_pcs),0) from erp.fg_lots where product_id=%s', (f['product'],)),
                  'unbalanced_journals': base.one(cur, 'select count(*) from(select journal_entry_id from erp.journal_lines group by journal_entry_id having sum(debit-credit)<>0)x'),
                  'execution_context': base.one(cur, 'select count(*) from erp.cp6_laundry_qc_execution_context')}
        for key, table in [('sale', 'sales_headers'), ('return', 'sales_returns'), ('conversion', 'product_conversions')]:
            if key in f:
                result[key + '_status'] = base.one(cur, f'select status from erp.{table} where id=%s', (f[key],))
        if 'po' in f:
            result['po_value'] = [str(v) for v in base.row(cur, 'select fg_value,cogs_value,other_out_value from erp.po_hpp_gl_state where po_id=%s', (f['po'],))]
            result['destination_stock'] = base.one(cur, 'select coalesce(sum(cached_qty_pcs),0) from erp.fg_lots where product_id=%s', (f['target_product'],))
        else:
            result['book'] = [str(v) for v in base.row(cur, """select
              coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('FG_INVENTORY')),0),
              coalesce(sum(l.debit-l.credit) filter(where l.account_id=erp.account_id('COGS')),0)
              from erp.journal_lines l join erp.journal_entries e on e.id=l.journal_entry_id
              where l.product_id=%s and e.status in('POSTED','REVERSED')""", (f['product'],))]
        return result


def wait_for(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(.025)
    raise AssertionError('Required native lock observation timed out')


def blocked(waiter, holder):
    return holder in scalar('select pg_blocking_pids(%s)', (waiter,))


def lock_snapshot(pids):
    return scalar("""select coalesce(jsonb_agg(jsonb_build_object('pid',pid,'mode',mode,'granted',granted,
      'relation',case when relation is not null then relation::regclass::text else locktype end)
      order by pid,granted,relation,mode),'[]'::jsonb) from pg_locks where pid=any(%s::int[])""", (pids,))


def run_case(target, operation, mode, folder):
    fixture, capsule = prepare(target, operation, folder)
    before = facts(fixture)
    ready, release = threading.Event(), threading.Event()
    worker = {}
    gate = None
    rollback = None
    thread = None
    logs = []

    def write():
        try:
            with connect('g-rollback-actual-' + operation.lower()) as conn, conn.cursor() as cur:
                cur.execute("set local lock_timeout='20s'; set local statement_timeout='45s'")
                worker['pid'] = base.one(cur, 'select pg_backend_pid()')
                if mode == 'ROLLBACK_FIRST':
                    ready.set()
                worker['response'] = business(cur, operation, fixture)
                if mode != 'ROLLBACK_FIRST':
                    ready.set()
                    if not release.wait(25):
                        raise AssertionError('Writer release did not arrive')
                if mode == 'WRITER_ABORT':
                    conn.rollback()
                    worker['outcome'] = 'ABORTED'
                else:
                    conn.commit()
                    worker['outcome'] = 'COMMITTED'
        except Exception as exc:
            worker.update(outcome='ERROR', error=str(exc), sqlstate=getattr(exc, 'sqlstate', None))
            ready.set()

    def start_rollback():
        app = f'g-exact-{target.lower()}-rollback'
        process = subprocess.Popen(['psql', CLONE, '-X', '-v', 'ON_ERROR_STOP=1', '-f', str(path(target, True))],
            env={**os.environ, 'PGAPPNAME': app}, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        pid = wait_for(lambda: scalar('select pid from pg_stat_activity where application_name=%s', (app,)))
        return process, pid

    try:
        if mode == 'ROLLBACK_FIRST':
            gate = connect('g-rollback-last-relation-gate')
            with gate.cursor() as cur:
                gate_pid = base.one(cur, 'select pg_backend_pid()')
                cur.execute('lock table erp.wip_stage_events in access exclusive mode')
            rollback, rollback_pid = start_rollback()
            wait_for(lambda: blocked(rollback_pid, gate_pid))
        thread = threading.Thread(target=write, daemon=True)
        thread.start()
        if not ready.wait(20) or worker.get('outcome') == 'ERROR':
            raise AssertionError(f'Actual writer failed before barrier: {worker}')
        if mode == 'ROLLBACK_FIRST':
            wait_for(lambda: blocked(worker['pid'], rollback_pid))
            observed = lock_snapshot([gate_pid, rollback_pid, worker['pid']])
            gate.rollback()
            gate.close()
            gate = None
        else:
            rollback, rollback_pid = start_rollback()
            wait_for(lambda: blocked(rollback_pid, worker['pid']))
            observed = lock_snapshot([rollback_pid, worker['pid']])
            if mode != 'ROLLBACK_LOCK_TIMEOUT':
                release.set()
        stdout, stderr = rollback.communicate(timeout=30)
        (folder / 'rollback.stdout.log').write_text(stdout)
        (folder / 'rollback.stderr.log').write_text(stderr)
        release.set()
        thread.join(30)
        if thread.is_alive() or worker.get('outcome') == 'ERROR':
            raise AssertionError(f'Actual writer did not finish: {worker}')
        expected_rollback = mode in ('ROLLBACK_FIRST', 'WRITER_ABORT') or (mode == 'WRITER_FIRST' and operation == 'REPORT')
        if expected_rollback:
            if rollback.returncode != 0:
                raise AssertionError(f'Pre-use rollback failed: {stderr}')
        elif mode == 'ROLLBACK_LOCK_TIMEOUT':
            if rollback.returncode == 0 or 'lock timeout' not in stderr:
                raise AssertionError(f'Exact rollback did not hit its configured lock timeout: {stderr}')
        elif rollback.returncode == 0 or 'post-install reconciliation or business history exists' not in stderr:
            raise AssertionError(f'Writer-first rollback failed to refuse real post-use: {stderr}')
        final_functions = verify_functions(capsule, not expected_rollback)
        _, name, marker, predecessor = TARGETS[target]
        present = scalar('select count(*) from erp.schema_migrations where version=%s', (marker,))
        platform_present = scalar('select count(*) from supabase_migrations.schema_migrations where name=%s', (name,))
        if present != (0 if expected_rollback else 1) or present != platform_present:
            raise AssertionError('Application/platform marker residue')
        capsule_present = scalar('select to_regclass(%s) is not null', (f'erp.cp6_v2620{target.lower()}_rollback_capsule',))
        f_events_present = scalar("select to_regclass('erp.non_po_hpp_gl_sync_events_v2620f') is not null")
        if capsule_present != (not expected_rollback) or f_events_present != (target == 'G' or not expected_rollback):
            raise AssertionError('Rollback-created object residue or missing predecessor object')
        after = facts(fixture)
        if after['unbalanced_journals'] or after['execution_context']:
            raise AssertionError(f'Business residue: {after}')
        if mode == 'WRITER_ABORT' or operation == 'REPORT':
            if before != after:
                raise AssertionError(f'Abort/read changed business facts: {before} -> {after}')
        elif operation == 'SALE':
            if after['stock'] != 5 or after['sale_status'] != 'POSTED' or tuple(map(Decimal, after['book'])) != (Decimal(35), Decimal(35)):
                raise AssertionError(f'Sale post-condition: {after}')
        elif operation == 'RETURN':
            if after['stock'] != 7 or after['return_status'] != 'POSTED' or tuple(map(Decimal, after['book'])) != (Decimal(49), Decimal(21)):
                raise AssertionError(f'Return post-condition: {after}')
        elif operation == 'CONVERSION':
            if after['stock'] != 8 or after['destination_stock'] != 2 or after['conversion_status'] != 'POSTED' or tuple(map(Decimal, after['po_value'])) != (Decimal(70), Decimal(0), Decimal(0)):
                raise AssertionError(f'Conversion post-condition: {after}')
        elif operation == 'FK_SYNC':
            if after['stock'] != 9 or after['sale_status'] != 'REVERSED' or tuple(map(Decimal, after['book'])) != (Decimal('.10'), Decimal('.01')):
                raise AssertionError(f'Actual FK synchronization post-condition: {after}')
        return {'status': 'PASS', 'target': marker, 'operation': operation, 'mode': mode,
                'actual_backend_sql': {'SALE': 'erp.post_sale_v2', 'RETURN': 'erp.post_sales_return',
                  'CONVERSION': 'erp.post_product_conversion', 'REPORT': 'erp.get_owner_financial_snapshot_v2',
                  'FK_SYNC': 'erp.post_sale_v2 -> erp.reverse_sale -> erp.sync_non_po_product_hpp_to_gl_v2620f'}[operation],
                'synthetic_business_marker': False, 'manual_writer_prelock': False,
                'rollback_pid': rollback_pid, 'writer': worker, 'lock_observation': observed,
                'exact_rollback_pid_is_writer_blocker': mode == 'ROLLBACK_FIRST',
                'exact_writer_pid_is_rollback_blocker': mode != 'ROLLBACK_FIRST',
                'rollback_committed': expected_rollback, 'predecessor_if_restored': predecessor if expected_rollback else None,
                'functions_owner_acl_exact': True, 'before': before, 'after': after,
                'function_hash_observations': final_functions,
                'final_schema': {'application_marker': present, 'platform_marker': platform_present,
                  'target_capsule_present': capsule_present, 'f_event_table_present': f_events_present},
                'migration_sha256': hashlib.sha256(path(target).read_bytes()).hexdigest(),
                'rollback_sha256': hashlib.sha256(path(target, True).read_bytes()).hexdigest()}
    finally:
        release.set()
        if gate is not None:
            gate.rollback()
            gate.close()
        if rollback is not None and rollback.poll() is None:
            rollback.terminate()
            rollback.communicate(timeout=10)
        if thread is not None:
            thread.join(25)


def main():
    if (os.environ.get('PGURL'), os.environ.get('CP6_MAINTENANCE_PGURL'),
        os.environ.get('CP6_ROLLBACK_RACE_PGURL'), os.environ.get('CP6_DATABASE_CONTAINER')) != (SOURCE, MAINTENANCE, CLONE, CONTAINER):
        raise SystemExit('Refusing non-allowlisted disposable database target')
    ROOT.mkdir(parents=True, exist_ok=True)
    report = {'head': os.environ.get('GITHUB_SHA', 'LOCAL_UNBOUND'), 'production_go': False,
              'classification': 'NATIVE_BACKEND_SQL_ROLLBACK_RACES_NOT_HTTP_AUTH', 'cases': []}
    try:
        for target in TARGETS:
            for operation in OPERATIONS:
                for mode in MODES:
                    folder = ROOT / f'{target}_{operation}_{mode}'
                    folder.mkdir()
                    try:
                        case = run_case(target, operation, mode, folder)
                    except Exception as exc:
                        case = {'status': 'FAIL', 'target': target, 'operation': operation,
                                'mode': mode, 'error': str(exc)}
                    finally:
                        drop_clone()
                    case['remaining_clone_databases'] = 0
                    (folder / 'result.json').write_text(json.dumps(case, indent=2) + '\n')
                    report['cases'].append(case)
                    (ROOT / 'progress.json').write_text(json.dumps(report, indent=2) + '\n')
                    print(json.dumps({k: v for k, v in case.items() if k in ('status', 'target', 'operation', 'mode', 'error')}), flush=True)
                    if case['status'] != 'PASS':
                        raise AssertionError('Native expanded rollback schedule failed')
        if len(report['cases']) != 40:
            raise AssertionError('Incomplete native rollback matrix')
        report['status'] = 'PASS'
    except Exception as exc:
        report.update(status='FAIL', error=str(exc))
    (ROOT / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    if report['status'] != 'PASS':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
