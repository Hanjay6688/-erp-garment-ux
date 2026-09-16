#!/usr/bin/env python3
"""Controlled-wall-clock native PostgreSQL audit across Jakarta midnight.

A stopped physical copy runs in a separate container made from the exact
source image. The PostgreSQL executable and full ERP catalog/table boundary
must match before fixtures. Only the copied server receives the clock shim;
monotonic time and the source server retain their real clocks. All business
functions remain unchanged. Four paired cases exercise ordinary scrap posting
and linked reversal. This is controlled-clock evidence, not an overnight soak.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import traceback
from datetime import datetime, time as daytime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import psycopg

import cp6_aa_invoice_partial_audit as invoice
import cp6_v2620w_scrap_business_date_regression as scrap


prior, one, base = invoice.prior, invoice.one, invoice.base
SOURCE_CONTAINER = 'supabase_db_cp5-local'
TARGET_CONTAINER = 'cp6-aa-midnight'
TARGET = 'postgresql://supabase_admin:postgres@127.0.0.1:54323/postgres'
ROOT = Path('cp6-proof/final-audit/midnight')
REPORT = ROOT / 'AI_MIDNIGHT_AUDIT.json'
C_SOURCE = Path('supabase/tests/support/cp6_clock_offset.c')
OFFSET_FILE = '/tmp/cp6-aa-clock.offset'
DATA = '/tmp/cp6-aa-clock-data'


def command(args, *, data=None, timeout=120):
    result = subprocess.run(args, input=data, text=True, capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError('AA_CLOCK_COMMAND_FAILED:' + json.dumps(
            dict(command=args[:4], code=result.returncode, stdout=result.stdout[-2000:], stderr=result.stderr[-4000:])))
    return result.stdout.strip()


def inspect(name, expression):
    return command(['docker', 'inspect', '--format', expression, name])


def set_clock(local_time):
    offset = int(local_time.timestamp() * 1000000) - time.time_ns() // 1000
    if abs(offset) > 172800000000:
        raise AssertionError('AA_CLOCK_OFFSET_EXCEEDS_TWO_DAYS')
    # Atomic rename prevents a backend from seeing a partially written offset.
    command(['docker', 'exec', '-i', TARGET_CONTAINER, 'sh', '-c',
             'cat > /tmp/cp6-aa-clock.offset.next && mv /tmp/cp6-aa-clock.offset.next /tmp/cp6-aa-clock.offset'],
            data=str(offset) + '\n')
    return dict(target_jakarta=local_time.isoformat(), offset_microseconds=offset,
                host_wall_utc=datetime.now(timezone.utc).isoformat(), host_monotonic=time.monotonic())


def connect(source=False):
    target = ('postgresql://supabase_admin:postgres@127.0.0.1:54322/postgres' if source else TARGET)
    return psycopg.connect(target, application_name='cp6-aa-midnight-audit', connect_timeout=3)


def clocks(cur):
    row = cur.execute('select transaction_timestamp(),statement_timestamp(),clock_timestamp(),txid_current()').fetchone()
    return dict(transaction=row[0], statement=row[1], wall=row[2], transaction_id=row[3], host_monotonic=time.monotonic())


def verify_repository_source():
    head='25fa4736329e5148dfdb3572bc169952cba23251'
    tree='a5cb1e43d776a9ffc058f99c8d5c96ac7f6a9c0d'
    if command(['git','rev-parse','HEAD']) != head or command(['git','rev-parse','HEAD^{tree}']) != tree:
        raise AssertionError('AI_CLOCK_EXACT_CANDIDATE_REQUIRED')
    if command(['git','diff','--name-only','HEAD']):
        raise AssertionError('AI_CLOCK_CANDIDATE_CHANGED')
    return 'AI_REGRESSION', head, tree


def verify_source_runtime(cur):
    import cp6_v2620ai_runtime as runtime
    objects=runtime.verified_successor(cur)
    if len(objects) != 690:
        raise AssertionError('AI_CLOCK_690_OBJECTS_REQUIRED')
    return objects


def wait_for_source():
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        try:
            with connect(source=True) as conn:
                conn.execute('select 1')
            return
        except psycopg.OperationalError:
            time.sleep(.5)
    raise AssertionError('AA_CLOCK_SOURCE_DID_NOT_RESTART')


def paired_case(old_day, long_transaction, source_today):
    old_start = datetime.combine(old_day, daytime(23, 59, 50), tzinfo=prior.JAKARTA)
    new_start = datetime.combine(old_day+timedelta(days=1), daytime(0, 0, 5), tzinfo=prior.JAKARTA)
    setup_clock = set_clock(old_start if long_transaction else new_start)
    with connect() as conn, conn.cursor() as cur:
        cur.execute("set local timezone='Asia/Jakarta';set local statement_timeout='60s';set local lock_timeout='8s'")
        before = prior.stable_boundary(cur)
        initial_clock = clocks(cur)
        change_clock = set_clock(new_start) if long_transaction else None
        after_clock = clocks(cur)
        if initial_clock['transaction_id'] != after_clock['transaction_id'] or initial_clock['transaction'] != after_clock['transaction']:
            raise AssertionError('AA_CLOCK_TRANSACTION_NOT_PRESERVED')
        wanted_start_day = old_day if long_transaction else old_day+timedelta(days=1)
        if (after_clock['transaction'].astimezone(prior.JAKARTA).date() != wanted_start_day
                or after_clock['wall'].astimezone(prior.JAKARTA).date() != old_day+timedelta(days=1)
                or after_clock['statement'].astimezone(prior.JAKARTA).date() != old_day+timedelta(days=1)):
            raise AssertionError('AA_CLOCK_MIDNIGHT_NOT_QUALIFIED')
        physical_day = old_day+timedelta(days=1) if source_today else old_day
        physical = datetime.combine(physical_day, daytime(0, 0, 1) if source_today else daytime(23, 0), tzinfo=prior.JAKARTA)
        prior.as_owner(cur)
        cash = one(cur, 'select id from erp.cash_accounts where is_active order by id limit 1')
        days = (str(old_day), str(old_day+timedelta(days=1)))
        before_reports = scrap.reports(cur, days)
        if any(r['data_confidence']['status'] != 'READY' for r in before_reports.values()):
            raise AssertionError('AA_CLOCK_REQUIRES_HEALTHY_BASELINE_REPORTS')
        transaction = scrap.draft(cur, cash, physical=physical.isoformat())
        if scrap.reports(cur, days) != before_reports:
            raise AssertionError('AA_CLOCK_DRAFT_CHANGED_REPORT')
        cur.execute('savepoint clock_post')
        post_error = None
        try:
            cur.execute('select erp.post_scrap_sale(%s)', (transaction,))
        except psycopg.Error as exc:
            post_error = dict(sqlstate=exc.sqlstate, message=exc.diag.message_primary)
            cur.execute('rollback to savepoint clock_post')
        cur.execute('release savepoint clock_post')
        result = dict(status='INCOMPLETE', long_transaction=long_transaction, source_today=source_today,
                      source_physical_at=physical.isoformat(), setup_clock=setup_clock, change_clock=change_clock,
                      initial_clock=initial_clock, after_clock=after_clock, post_error=post_error,
                      actual_source=transaction, expected_post_day=str(physical_day),
                      expected_reversal_day=str(old_day+timedelta(days=1)))
        if post_error:
            result['classification'] = 'POST_REJECTION_REQUIRES_FRESH_TRANSACTION_CONTROL'
        else:
            prior.as_admin(cur)
            posted = scrap.book(cur, transaction)
            prior.as_owner(cur)
            after_post_reports = scrap.reports(cur, days)
            cur.execute('savepoint clock_reverse')
            reverse_error = None
            try:
                cur.execute('select erp.reverse_scrap_sale(%s,%s)', (transaction, 'AA linked reversal after Jakarta midnight'))
            except psycopg.Error as exc:
                reverse_error = dict(sqlstate=exc.sqlstate, message=exc.diag.message_primary)
                cur.execute('rollback to savepoint clock_reverse')
            cur.execute('release savepoint clock_reverse')
            after_reverse_reports = scrap.reports(cur, days)
            prior.as_admin(cur)
            rows = scrap.book(cur, transaction)
            originals = [r for r in rows if r['source_type'] == 'SCRAP_SALE']
            inverses = [r for r in rows if r['source_type'] == 'JOURNAL_REVERSAL']
            errors = {}
            if len(posted) != 1 or len(originals) != 1 or len(inverses) != 1 or reverse_error:
                errors['linked_journal_cardinality'] = dict(posted=posted, final=rows, reverse_error=reverse_error)
            else:
                original, inverse = originals[0], inverses[0]
                if (original['economic_date'], original['transaction_date']) != (str(physical_day), str(physical_day)):
                    errors['post_business_day'] = original
                if (inverse['economic_date'], inverse['transaction_date']) != (days[1], days[1]):
                    errors['reverse_business_day'] = inverse
                if inverse['reversal_of_id'] != original['id'] or any(Decimal(r[k]) != Decimal('.03') for r in rows for k in ('debit','credit')):
                    errors['linked_inverse_or_cents'] = rows
            cash_deltas = {}
            for day in days:
                posted_cash = Decimal(str(after_post_reports[day]['financial_position']['cash']))-Decimal(str(before_reports[day]['financial_position']['cash']))
                reversed_cash = Decimal(str(after_reverse_reports[day]['financial_position']['cash']))-Decimal(str(before_reports[day]['financial_position']['cash']))
                expected_post = Decimal('.03') if day >= str(physical_day) else Decimal(0)
                expected_reverse = expected_post-(Decimal('.03') if day == days[1] else Decimal(0))
                cash_deltas[day] = dict(posted=posted_cash, expected_posted=expected_post,
                                        reversed=reversed_cash, expected_reversed=expected_reverse,
                                        confidence=after_reverse_reports[day]['data_confidence'])
                if posted_cash != expected_post or reversed_cash != expected_reverse:
                    errors['daily_cash.' + day] = cash_deltas[day]
                for phase, report in (('posted', after_post_reports[day]), ('reversed', after_reverse_reports[day])):
                    if report['data_confidence']['status'] != 'READY':
                        errors[phase + '_report_confidence.' + day] = report['data_confidence']
            result.update(status='COUNTEREXAMPLE' if errors else 'CONTROL_PASS', severity='P2' if errors else None,
                          classification='CONTROLLED_NATIVE_CLOCK_BUSINESS_LIFECYCLE',
                          journals=rows, cash_by_day=cash_deltas, mismatches=errors,
                          before_reports=before_reports, after_post_reports=after_post_reports,
                          after_reverse_reports=after_reverse_reports)
            result['silent_if_ready'] = bool(errors) and after_reverse_reports[days[1]]['data_confidence']['status'] == 'READY'
        conn.rollback()
        prior.as_admin(cur)
        result['full_boundary_restored'] = prior.stable_boundary(cur) == before
        conn.rollback()
        if not result['full_boundary_restored']:
            result['status'] = 'INCOMPLETE'
    return result


def run():
    if os.environ.get('PGURL') != 'postgresql://postgres:postgres@127.0.0.1:54322/postgres' or os.environ.get('CP6_DATABASE_CONTAINER') != SOURCE_CONTAINER:
        raise AssertionError('AA_CLOCK_EXACT_SOURCE_REQUIRED')
    if os.environ.get('CP6_AA_MIDNIGHT_AUDIT_CONFIRM') != 'postgres':
        raise AssertionError('AA_CLOCK_EXPLICIT_DISPOSABLE_CONFIRM_REQUIRED')
    phase, head, tree = verify_repository_source()
    runtime_generation = {
        'AA_AUDIT': 'AA', 'AB_REGRESSION': 'AB', 'AC_REGRESSION': 'AC', 'AI_REGRESSION':'AI-R2',
    }.get(phase)
    if runtime_generation is None:
        raise AssertionError('AA_CLOCK_UNKNOWN_SUCCESSOR_PHASE')
    if command(['docker', 'ps', '-aq', '--filter', 'name=^/' + TARGET_CONTAINER + '$']):
        raise AssertionError('AA_CLOCK_TARGET_ALREADY_EXISTS')
    ROOT.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='cp6-aa-midnight-'))
    created = None
    source_before = None
    restart_source = False
    result = dict(format='CP6_AI_FINAL_MIDNIGHT_AUDIT_V1', status='INCOMPLETE', head=head,
                  tree=tree, phase=phase, runtime_generation=runtime_generation,
                  audited_business_head=head if phase != 'AA_AUDIT' else invoice.HEAD_AA,
                  audited_business_tree=tree if phase != 'AA_AUDIT' else invoice.TREE_AA,
                  business_source_head=head,
                  harness_head=os.environ['CP6_AUDIT_HARNESS_HEAD'],
                  oracle_origin='Unchanged four-case AA/AB clock oracle reexecuted on AI-R2; not new case designs',
                  source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  run_id=os.environ.get('GITHUB_RUN_ID'), production_go=False, independent_acceptance_complete=False,
                  evidence_kind='CONTROLLED_WALL_CLOCK_NATIVE_POSTGRESQL_NOT_OVERNIGHT_SOAK',
                  synthetic_fixture_only=True, hosted_database_used=False, expected_cases=4, cases={},
                  extension_preloads_disabled_in_copy=True, logical_replication_workers_disabled_in_copy=True,
                  autovacuum_disabled_in_copy=True, wall_clock_shift_scope='COPIED_POSTGRES_PROCESSES_ONLY',
                  copy_strategy='CLEAN_STOP_PHYSICAL_DATA_DIRECTORY_COPY',
                  application_function_modifications=0, clock_source_sha256=hashlib.sha256(C_SOURCE.read_bytes()).hexdigest())
    def save():
        REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
    save()
    try:
        with connect(source=True) as conn, conn.cursor() as cur:
            source_before = prior.stable_boundary(cur)
            verified = verify_source_runtime(cur)
            result['legacy_verified_ab_functions'] = (
                list(verified.values()) if phase not in ('AC_REGRESSION','AI_REGRESSION') else []
            )
            result['verified_runtime_objects'] = (
                list(verified.values()) if phase in ('AC_REGRESSION','AI_REGRESSION') else []
            )
            result['source_engine'] = one(cur, 'select version()')
            source_data = one(cur, "select current_setting('data_directory')")
            if (not source_data.startswith('/var/lib/postgresql/') or '..' in Path(source_data).parts
                    or one(cur, 'select pg_is_in_recovery()')
                    or one(cur, "select count(*) from pg_tablespace where spcname not in('pg_default','pg_global')")):
                raise AssertionError('AA_CLOCK_UNSUPPORTED_SOURCE_LAYOUT')
            result['source_data_directory'] = source_data
        image = inspect(SOURCE_CONTAINER, '{{.Image}}')
        if not image.startswith('sha256:'):
            raise AssertionError('AA_CLOCK_SOURCE_IMAGE_NOT_CONTENT_ADDRESSED')
        command(['cc', '-std=c11', '-shared', '-fPIC', '-O2', '-Wall', '-Wextra', '-Werror', str(C_SOURCE), '-o', str(temp/'clock.so')])
        result['clock_library_sha256'] = hashlib.sha256((temp/'clock.so').read_bytes()).hexdigest()
        # The exact disposable CI source is restarted before any clock shift.
        # Copying a cleanly stopped cluster needs no replication/HBA changes.
        restart_source = True
        command(['docker', 'stop', '--signal', 'SIGINT', '--timeout', '30', SOURCE_CONTAINER], timeout=45)
        if inspect(SOURCE_CONTAINER, '{{.State.ExitCode}}') != '0':
            raise AssertionError('AA_CLOCK_SOURCE_SHUTDOWN_NOT_CLEAN')
        command(['docker', 'cp', SOURCE_CONTAINER+':'+source_data, str(temp/'data')], timeout=180)
        command(['docker', 'start', SOURCE_CONTAINER])
        wait_for_source()
        restart_source = False
        if (not (temp/'data').is_dir() or (temp/'data').is_symlink()
                or (temp/'data'/'postmaster.pid').exists() or (temp/'data'/'pg_wal').is_symlink()):
            raise AssertionError('AA_CLOCK_PHYSICAL_COPY_NOT_SELF_CONTAINED')
        auto_config = temp/'data'/'postgresql.auto.conf'
        if auto_config.is_symlink():
            raise AssertionError('AA_CLOCK_COPY_AUTO_CONFIG_SYMLINK')
        result['copied_auto_config_sha256'] = hashlib.sha256(auto_config.read_bytes()).hexdigest() if auto_config.exists() else None
        auto_config.write_text('# CP6 isolated clock test: use only the explicit copied-server configuration.\n')
        created = command(['docker', 'create', '--name', TARGET_CONTAINER, '--label', 'cp6.audit=aa-midnight',
                           '-p', '127.0.0.1:54323:5432', '--entrypoint', 'sh', image, '-c', 'exec tail -f /dev/null'])
        command(['docker', 'start', created])
        if inspect(TARGET_CONTAINER, '{{.Image}}') != image:
            raise AssertionError('AA_CLOCK_COPY_IMAGE_MISMATCH')
        command(['docker', 'cp', str(temp/'data'), TARGET_CONTAINER+':'+DATA], timeout=180)
        command(['docker', 'cp', str(temp/'clock.so'), TARGET_CONTAINER+':/tmp/cp6-aa-clock.so'])
        config = "listen_addresses='*'\nport=5432\nshared_preload_libraries=''\nshared_buffers='32MB'\nmax_connections=30\nmax_wal_senders=0\nmax_logical_replication_workers=0\nautovacuum=off\narchive_mode=off\nhot_standby=off\nunix_socket_directories='/tmp'\nhba_file='/tmp/cp6-aa-clock-hba.conf'\nssl=off\ntimezone='UTC'\n"
        result['copied_server_configuration'] = config
        (temp/'postgresql.conf').write_text(config)
        (temp/'pg_hba.conf').write_text('local all all trust\nhost all all 0.0.0.0/0 scram-sha-256\n')
        command(['docker', 'cp', str(temp/'postgresql.conf'), TARGET_CONTAINER+':/tmp/cp6-aa-clock-postgresql.conf'])
        command(['docker', 'cp', str(temp/'pg_hba.conf'), TARGET_CONTAINER+':/tmp/cp6-aa-clock-hba.conf'])
        command(['docker', 'exec', TARGET_CONTAINER, 'chown', '-R', 'postgres:postgres', DATA])
        control_data = command(['docker', 'exec', '-e', 'LC_ALL=C', TARGET_CONTAINER, 'pg_controldata', DATA])
        (ROOT/'PHYSICAL_COPY_CONTROL_DATA.txt').write_text(control_data + '\n')
        state_lines = [line.split(':', 1)[1].strip() for line in control_data.splitlines()
                       if line.startswith('Database cluster state:')]
        if state_lines != ['shut down']:
            raise AssertionError('AA_CLOCK_COPY_REQUIRES_CLEAN_SHUTDOWN_STATE')
        command(['docker', 'exec', '-i', TARGET_CONTAINER, 'sh', '-c', 'cat > /tmp/cp6-aa-clock.offset'], data='0\n')
        for target in (SOURCE_CONTAINER, TARGET_CONTAINER):
            executable = command(['docker', 'exec', target, 'sh', '-c', 'command -v postgres'])
            digest = command(['docker', 'exec', target, 'sha256sum', executable]).split()[0]
            result['source_postgres_sha256' if target == SOURCE_CONTAINER else 'copy_postgres_sha256'] = digest
        if result['source_postgres_sha256'] != result['copy_postgres_sha256']:
            raise AssertionError('AA_CLOCK_POSTGRES_EXECUTABLE_CHANGED')
        result['copied_postgres_clock_library_load_control'] = command([
            'docker', 'exec', '-u', 'postgres', '-e', 'LD_PRELOAD=/tmp/cp6-aa-clock.so',
            '-e', 'CP6_CLOCK_OFFSET_FILE='+OFFSET_FILE, TARGET_CONTAINER, 'postgres', '--version'])
        command(['docker', 'exec', '-u', 'postgres', '-e', 'LD_PRELOAD=/tmp/cp6-aa-clock.so',
                 '-e', 'CP6_CLOCK_OFFSET_FILE='+OFFSET_FILE, TARGET_CONTAINER, 'pg_ctl', '-D', DATA,
                 '-l', '/tmp/cp6-aa-clock-postgres.log', '-o', '-c config_file=/tmp/cp6-aa-clock-postgresql.conf', '-w', 'start'], timeout=90)
        with connect() as conn, conn.cursor() as cur:
            result['copy_engine'] = one(cur, 'select version()')
            result['physical_copy_boundary_exact'] = prior.stable_boundary(cur) == source_before
            if result['copy_engine'] != result['source_engine'] or not result['physical_copy_boundary_exact']:
                raise AssertionError('AA_CLOCK_PHYSICAL_COPY_NOT_EXACT')
            verify_source_runtime(cur)
        old_day = datetime.now(prior.JAKARTA).date()-timedelta(days=1)
        set_clock(datetime.combine(old_day, daytime(23, 0), tzinfo=prior.JAKARTA))
        with connect() as conn, conn.cursor() as cur:
            cur.execute("set local timezone='UTC';set local statement_timeout='180s'")
            cur.execute('grant usage on schema erp to authenticated')
            prior.actors.claims(cur, dict(sub=base.OPERATOR_AUTH, role='authenticated'))
            base.load_fixture_foundation(cur)
            conn.commit()
        # Fresh-transaction controls qualify the same physical input before
        # a rejected long-transaction call may be called a counterexample.
        for source_today in (False, True):
            for long_transaction in (False, True):
                name = ('LONG:' if long_transaction else 'FRESH:')+('CURRENT_DAY_SOURCE' if source_today else 'PRIOR_DAY_SOURCE')
                try:
                    row = paired_case(old_day, long_transaction, source_today)
                except Exception as exc:
                    row = dict(status='INCOMPLETE', error=str(exc), traceback=traceback.format_exc())
                if row.get('post_error') and long_transaction:
                    control = result['cases'].get('FRESH:' + ('CURRENT_DAY_SOURCE' if source_today else 'PRIOR_DAY_SOURCE'), {})
                    error = row['post_error']
                    date_refusal = (error.get('sqlstate') == 'P0001' and
                                    any(token in error.get('message', '').lower() for token in ('future', 'masa depan')))
                    if control.get('status') == 'CONTROL_PASS' and row.get('full_boundary_restored') and date_refusal:
                        row.update(status='COUNTEREXAMPLE', severity='P2', classification='LAWFUL_POST_REJECTED_AFTER_MIDNIGHT_IN_LONG_TRANSACTION')
                result['cases'][name] = row
                save()
                print(json.dumps(dict(case=name, status=row['status'])), flush=True)
        result['controls'] = sum(c['status'] == 'CONTROL_PASS' for c in result['cases'].values())
        result['counterexamples'] = sum(c['status'] == 'COUNTEREXAMPLE' for c in result['cases'].values())
        result['incomplete'] = sum(c['status'] == 'INCOMPLETE' for c in result['cases'].values())
    except Exception as exc:
        result.update(error=str(exc), traceback=traceback.format_exc())
    finally:
        cleanup_errors = []
        if restart_source:
            try:
                command(['docker', 'start', SOURCE_CONTAINER])
                wait_for_source()
            except Exception as exc:
                cleanup_errors.append('SOURCE_RESTART:' + str(exc))
        if created:
            try:
                if inspect(TARGET_CONTAINER, '{{.Id}}') != created or inspect(TARGET_CONTAINER, '{{index .Config.Labels "cp6.audit"}}') != 'aa-midnight':
                    raise AssertionError('AA_CLOCK_CLEANUP_CONTAINER_IDENTITY_CHANGED')
                try:
                    logs = command(['docker', 'exec', TARGET_CONTAINER, 'sh', '-c', 'test ! -f /tmp/cp6-aa-clock-postgres.log || cat /tmp/cp6-aa-clock-postgres.log'])
                    (ROOT/'POSTGRES.log').write_text(logs + '\n')
                finally:
                    command(['docker', 'rm', '-f', '-v', TARGET_CONTAINER])
            except Exception as exc:
                cleanup_errors.append('COPY_DISPOSAL:' + str(exc))
        try:
            shutil.rmtree(temp)
        except Exception as exc:
            cleanup_errors.append('TEMP_DISPOSAL:' + str(exc))
        try:
            result['remaining_clock_containers'] = len(command(['docker', 'ps', '-aq', '--filter', 'name=^/' + TARGET_CONTAINER + '$']).splitlines())
            with connect(source=True) as conn, conn.cursor() as cur:
                result['source_boundary_unchanged'] = source_before is not None and prior.stable_boundary(cur) == source_before
                source_wall = one(cur, 'select clock_timestamp()')
            result['source_clock_still_real'] = abs(source_wall.timestamp()-time.time()) < 3
        except Exception as exc:
            cleanup_errors.append('SOURCE_VERIFICATION:' + str(exc))
        result['cleanup_errors'] = cleanup_errors
        if (not cleanup_errors and result.get('remaining_clock_containers') == 0 and result.get('source_boundary_unchanged')
                and result.get('source_clock_still_real') and len(result['cases']) == 4):
            result['status'] = ('FAIL_NEW_COUNTEREXAMPLE' if result.get('counterexamples') else
                                'PASS_BOUNDED_AUDIT' if result.get('controls') == 4 else 'INCOMPLETE')
        save()
    return result


if __name__ == '__main__':
    try:
        result = run()
    except Exception as exc:
        result = json.loads(REPORT.read_text()) if REPORT.exists() else {}
        result.update(status='INCOMPLETE', error=str(exc), traceback=traceback.format_exc(), production_go=False)
        ROOT.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, indent=2, default=str) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'cases'}, default=str))
    raise SystemExit(0 if result['status'] == 'PASS_BOUNDED_AUDIT' else
                     1 if result['status'] == 'FAIL_NEW_COUNTEREXAMPLE' else 2)
