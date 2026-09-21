#!/usr/bin/env python3
"""Twelve native direct-DRAFT item/post schedules with observed row blocking."""
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
import json, os, threading, time, traceback, uuid
import psycopg
import cp6_v2620al_value_review as values
import cp6_v2620h_maintenance_rollback_matrix as matrix

review, oracle = values.setup, values.oracle
ROOT = Path('cp6-proof/writer-al/direct-concurrency')
CLONE = matrix.CLONE.replace('postgres:postgres@', 'supabase_admin:postgres@')


def seed_case(cur, balance):
    cur.execute("set local timezone='Asia/Jakarta'")
    day = cur.execute("select (statement_timestamp() at time zone 'Asia/Jakarta')::date").fetchone()[0]
    material = None
    if balance == 'MATERIAL':
        batch, material = oracle.gaps.raw_batch(cur, day, 'VALID')
        assert oracle.validate(cur, batch)['counts'] == (1, 1, 0)
        ident = oracle.prepare(cur, batch)
        oracle.run_owner(cur, 'update erp.opening_balance_items set unit_cost_snapshot=2.75 where opening_id=%s', (ident,))
    else:
        ident = oracle.run_owner(cur,
            "insert into erp.opening_balance_headers(opening_number,opening_date,status) values(%s,%s,'DRAFT') returning id",
            ('ALC-'+uuid.uuid4().hex, day-timedelta(days=1))).fetchone()[0]
        oracle.run_owner(cur, 'insert into erp.opening_balance_items(opening_id,balance_type,qty,amount,unit_cost_snapshot) values(%s,%s,%s,%s,%s)',
            (ident, balance, 2 if balance == 'BS' else None, Decimal('3.75') if balance == 'WIP' else None, None))
    return ident, material


def run_case(balance, direction, commit):
    with psycopg.connect(CLONE) as seed, seed.cursor() as cur:
        ident, material = seed_case(cur, balance)
    first = second = thread = None
    try:
        first = psycopg.connect(CLONE, application_name='al-direct-first')
        second = psycopg.connect(CLONE, application_name='al-direct-second')
        for conn in (first, second):
            conn.execute("set statement_timeout='15s';set lock_timeout='12s'")
            conn.commit()

        def edit(cur):
            column, value = ('amount', '-5.25') if balance == 'WIP' else ('qty', '20' if balance == 'MATERIAL' else '1.5')
            oracle.run_owner(cur, 'update erp.opening_balance_items set '+column+'=%s where opening_id=%s', (value, ident))

        def post(cur):
            oracle.post(cur, ident)

        before_fn, after_fn = (edit, post) if direction == 'EDIT_POST' else (post, edit)
        before_fn(first.cursor())
        result = {}

        def worker():
            try:
                after_fn(second.cursor())
                second.commit()
                result.update(success=True)
            except Exception as exc:
                second.rollback()
                result.update(success=False, sqlstate=getattr(exc, 'sqlstate', None), error=str(exc))

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        blocked = False
        with psycopg.connect(CLONE, autocommit=True) as observer:
            deadline = time.monotonic()+6
            while time.monotonic() < deadline and thread.is_alive():
                blocked = observer.execute('select %s=any(pg_blocking_pids(%s))',
                    (first.info.backend_pid, second.info.backend_pid)).fetchone()[0]
                if blocked:
                    break
                time.sleep(.03)
        assert blocked, 'Second session was not observed waiting on the first'
        first.commit() if commit else first.rollback()
        thread.join(18)
        assert not thread.is_alive(), 'Second session did not finish'
        expected_success = (balance == 'MATERIAL' or not commit) if direction == 'EDIT_POST' else not commit
        assert result['success'] == expected_success, result
        if not expected_success:
            assert result['sqlstate'] == 'P0001', result
            if direction == 'EDIT_POST':
                assert ('AL_BS_REQUIRES_POSITIVE_WHOLE_PCS' if balance == 'BS' else 'AL_WIP_VALUE_MUST_BE_NONNEGATIVE') in result['error'], result
        posted = result['success'] if direction == 'EDIT_POST' else commit
        with psycopg.connect(CLONE) as observer, observer.cursor() as cur:
            state = oracle.opening_state(cur, ident)
            assert state['header'][2] == ('POSTED' if posted else 'DRAFT'), state
            journal = dict(state['journal'])
            if balance == 'MATERIAL':
                qty = (20 if commit else 10) if direction == 'EDIT_POST' else (10 if commit else 0)
                stock = cur.execute('select coalesce(sum(qty_signed),0),coalesce(sum(qty_signed*unit_cost_snapshot),0) from erp.material_stock_movements where material_id=%s', (material,)).fetchone()
                assert stock == (qty, Decimal(qty)*Decimal('2.75')), stock
                assert journal.get('MATERIAL_INVENTORY', 0) == Decimal(qty)*Decimal('2.75'), state
            elif balance == 'BS':
                assert state['bs'] == ([(2,)] if posted else []), state
            else:
                assert journal.get('WIP', 0) == (Decimal('3.75') if posted else 0), state
            if not posted:
                assert not state['journal'] and not state['bs'], state
        return dict(status='PASS', blocking_observed=True, first_committed=commit, second=result, state=state)
    finally:
        for conn in (first, second):
            if conn is not None:
                if thread and thread.is_alive():
                    conn.cancel()
                conn.close()
        if thread:
            thread.join(2)


def run():
    assert os.environ['PGURL'] == matrix.SOURCE and os.environ['CP6_ROLLBACK_RACE_PGURL'] == matrix.CLONE
    head, tree = review.runtime.verify_audit_source()
    report = dict(status='INCOMPLETE', writer_head=head, writer_tree=tree, cases={}, production_go=False, independent_acceptance=False)
    ROOT.mkdir(parents=True, exist_ok=True)

    def save():
        (ROOT/'manifest.json').write_text(json.dumps(report, indent=2, default=str)+'\n')

    try:
        matrix.command(['bash', 'scripts/clone-cp6-disposable-database.sh', matrix.SOURCE, matrix.MAINTENANCE,
            matrix.CLONE, 'cp6_rollback', matrix.CONTAINER, str(ROOT/'PHYSICAL_BOUNDARY')], ROOT/'clone.log')
        with psycopg.connect(CLONE) as conn, conn.cursor() as cur:
            assert len(review.runtime.verified_successor(cur)) == 690
            cur.execute('grant usage on schema erp to authenticated')
            review.actors.actors.claims(cur, dict(sub=review.base.OPERATOR_AUTH, role='authenticated'))
            review.base.load_fixture_foundation(cur)
            review.actors.admin(cur)
        for balance in ('MATERIAL', 'BS', 'WIP'):
            for direction in ('EDIT_POST', 'POST_EDIT'):
                for commit in (True, False):
                    name = balance+':'+direction+(':_COMMIT' if commit else ':_ABORT')
                    try:
                        row = run_case(balance, direction, commit)
                    except Exception as exc:
                        row = dict(status='INCOMPLETE', error=str(exc), traceback=traceback.format_exc())
                    report['cases'][name] = row
                    save()
                    print(json.dumps(dict(case=name, status=row['status'], error=row.get('error'))), flush=True)
    finally:
        matrix.legacy.drop_clone()
    with psycopg.connect(matrix.MAINTENANCE) as conn:
        report['clone_removed'] = conn.execute("select count(*) from pg_database where datname='cp6_rollback'").fetchone()[0] == 0
    if report['clone_removed'] and len(report['cases']) == 12 and all(row['status'] == 'PASS' for row in report['cases'].values()):
        report['status'] = 'WRITER_PASS'
    save()
    return report


if __name__ == '__main__':
    result = run()
    print(json.dumps(result, default=str))
    raise SystemExit(0 if result['status'] == 'WRITER_PASS' else 1)
