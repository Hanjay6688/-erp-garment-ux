"""Read-only wait observation tested on an isolated PostgreSQL 17 cluster."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from time import monotonic, sleep
import json
import sys

import psycopg


def observe(connection, backend_pid):
    row = connection.execute(
        """select state, wait_event_type, wait_event, cardinality(pg_blocking_pids(pid))
           from pg_stat_activity
           where datname = current_database() and backend_type = 'client backend'
             and pid = %s and pid <> pg_backend_pid()""", (backend_pid,)).fetchone()
    if row is None:
        return None
    return dict(zip(('state', 'wait_type', 'wait_event', 'blocker_count'), row))


def lock_control(connection, target, statement, expected_event):
    with ThreadPoolExecutor(max_workers=1) as worker:
        pending = worker.submit(target.execute, statement)
        try:
            deadline = monotonic() + 3
            while monotonic() < deadline:
                report = observe(connection, target.info.backend_pid)
                if report and report['wait_type'] == 'Lock':
                    assert report == dict(state='active', wait_type='Lock', wait_event=expected_event, blocker_count=1), report
                    return report
                sleep(0.03)
            raise AssertionError('Expected known blocked control')
        finally:
            target.cancel_safe(timeout=2)
            try:
                pending.result(timeout=3)
            except psycopg.errors.QueryCanceled:
                target.rollback()
            else:
                raise AssertionError('Expected blocked statement to cancel')


def main(data_dir, port):
    assert data_dir.is_dir() and data_dir.is_absolute()
    config = dict(host='127.0.0.1', port=port, dbname='postgres', user='cp7_diagnostic', connect_timeout=3)
    with ExitStack() as stack:
        monitor = stack.enter_context(psycopg.connect(**config, autocommit=True))
        owner = stack.enter_context(psycopg.connect(**config))
        target = stack.enter_context(psycopg.connect(**config))
        actual_dir, = monitor.execute('show data_directory').fetchone()
        assert Path(actual_dir).resolve() == data_dir.resolve()
        monitor.execute("set statement_timeout = '2s'")
        target.execute("set statement_timeout = '6s'")
        target.commit()
        version, = monitor.execute('show server_version').fetchone()
        assert version == '17.6'
        monitor.execute('create role cp7_diagnostic_scoped')
        monitor.execute('create table test_wait_lock (id integer)')
        owner.execute('select pg_advisory_xact_lock(4917, 181)')
        owner.execute('savepoint nested_install')
        owner.execute('set local role cp7_diagnostic_scoped')
        owner.execute('select pg_advisory_xact_lock(4917, 181)')
        owner.execute('rollback to savepoint nested_install')
        assert owner.execute('select current_user, session_user').fetchone() == ('cp7_diagnostic', 'cp7_diagnostic')
        advisory = lock_control(monitor, target, 'select pg_advisory_xact_lock(4917, 181)', 'advisory')
        owner.rollback()
        owner.execute('lock table test_wait_lock in access share mode')
        relation = lock_control(monitor, target, 'lock table test_wait_lock in access exclusive mode', 'relation')
        owner.rollback()
        target.execute('lock table test_wait_lock in access exclusive mode nowait')
        target.rollback()
        assert observe(monitor, target.info.backend_pid)['blocker_count'] == 0
        assert observe(monitor, monitor.info.backend_pid) is None
        print(json.dumps(dict(postgres=version, same_backend_reentry_passed=True, role_restored=True,
                              advisory_wait=advisory, relation_wait=relation, lock_released_after_rollback=True,
                              observed_query_text=False, external_runner_cause_verified=False,
                              actual_SKU_case_credit=0), indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1]), int(sys.argv[2]))
