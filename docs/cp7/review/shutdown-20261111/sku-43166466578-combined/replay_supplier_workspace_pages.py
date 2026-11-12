"""Exercise the exact supplier workspace with 26 transfers and an overlapping write."""

from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from time import monotonic, sleep
from uuid import UUID
from zipfile import ZipFile

from psycopg import connect
from psycopg.types.json import Jsonb

from loopback_postgres import cluster
from replay_supplier_two_sessions import AREA, GATE, VALUES, setup as base_fixture


WORKSPACE = 'cp7_supplier_transfer.workspace_v1(jsonb)'
PUBLIC = 'public.erp_cp7_get_supplier_transfer_v1(jsonb)'
QUERY = dict(supplier_id=VALUES['supplier'], purchase_offset=25, transfer_offset=25)


def setup(conn, original):
    base_fixture(conn)
    with ZipFile(original) as z:
        raw = z.read('SKU_GLOBAL_PARENT_ACTUAL_FULL25.json')
    assert sha256(raw).hexdigest() == '5ff582717522b766c12024c1bf3299066475f14a3c6021a3543f378f829e0c07'
    definitions = dict(json.loads(raw)['functions'])
    conn.execute("""
      create role authenticated;
      create table erp.chart_accounts(id uuid primary key,is_active boolean,is_postable boolean);
      alter table erp.cash_accounts add column coa_account_id uuid,add column is_active boolean;
      alter table fixture.transfers add column recorded_at timestamptz;
      create or replace view cp7_supplier_transfer.transfers_v1 as
        select * from fixture.transfers where fixture.interleave(id);
      create or replace function public.erp_get_supplier_credit_v1(p jsonb) returns jsonb
        language sql stable as $$
        select jsonb_build_object('purchases',coalesce(jsonb_agg(jsonb_build_object(
             'id',h.id,'remaining',(1000-coalesce(x.paid,0))::text)),'[]'::jsonb))
        from erp.material_purchase_headers h
        left join lateral (select sum(amount) paid from erp.supplier_payments
                            where purchase_id=h.id and status='POSTED') x on true
        where h.supplier_id=(p->>'supplier_id')::uuid $$;
    """, prepare=False)
    for name in ('detail_v1', 'review_v1'):
        conn.execute((AREA / f'cp7_supplier_transfer.{name}.replacement.sql').read_text())
    before, after = ((AREA / f'cp7_supplier_transfer.workspace_v1.{kind}.sql').read_text()
                     for kind in ('preimage', 'replacement'))
    assert before == definitions[WORKSPACE][0]
    assert sha256(after.encode()).hexdigest() == '3b400eb865aed0d5e2edf984640acde32d755a84ee431d2fdc00247ae7735c79'
    conn.execute(before)
    conn.execute(definitions[PUBLIC][0])
    conn.execute('revoke all on function ' + PUBLIC + ' from public; grant execute on function '
                 + PUBLIC + ' to authenticated', prepare=False)
    return before, after


def seed(conn):
    conn.execute('truncate fixture.transfers; truncate erp.material_purchase_headers', prepare=False)
    for i in range(1, 27):
        ident = UUID(int=3 * (1 << 120) + i)
        conn.execute("insert into erp.material_purchase_headers values(%s,%s,'POSTED',%s, "
                     "'2026-11-07'::date + %s)", (ident, VALUES['supplier'], f'AP-{i:02d}', i))
        if i < 26:
            insert_transfer(conn, i)


def insert_transfer(conn, i):
    ident = UUID(int=4 * (1 << 120) + i)
    conn.execute("insert into fixture.transfers values(%s,%s,%s,'POSTED','2026-11-07',1.23,%s,'',%s, "
                 "'2026-11-07'::date - %s)", (ident, f'T-{i:02d}', VALUES['supplier'], VALUES['bank'], VALUES['journal'], i))


def read(conn, query=QUERY):
    value = conn.execute('select public.erp_cp7_get_supplier_transfer_v1(%s)',
                         (Jsonb(query),)).fetchone()[0]
    return {name: value[name] for name in ('transfers', 'receipts')}


def observe_overlap(writer, reader, pool, commit):
    pid = reader.execute('select pg_backend_pid()').fetchone()[0]
    holder = writer.execute('select pg_backend_pid()').fetchone()[0]
    assert pid != holder
    reader.execute("set fixture.reader_barrier='on'")
    writer.execute('select pg_advisory_lock(%s)', (GATE,))
    waiting = pool.submit(read, reader)
    try:
        deadline = monotonic() + 5
        while writer.execute('select pg_blocking_pids(%s)', (pid,)).fetchone()[0] != [holder]:
            assert not waiting.done() and monotonic() < deadline, 'Workspace read missed the intended barrier'
            sleep(0.01)
        with writer.transaction(force_rollback=not commit):
            insert_transfer(writer, 26)
        assert not waiting.done()
    finally:
        assert writer.execute('select pg_advisory_unlock(%s)', (GATE,)).fetchone() == (True,)
    result = waiting.result(timeout=5)
    reader.execute('reset fixture.reader_barrier')
    return result


def page(value):
    return dict(total=value['total'], numbers=[row['number'] for row in value['rows']],
                offset=value['offset'], limit=value['limit'], next_offset=value['next_offset'])


def exercise(conninfo, original):
    with (
        connect(**conninfo, autocommit=True) as writer,
        connect(**conninfo, autocommit=True) as reader,
        ThreadPoolExecutor(max_workers=1) as pool,
    ):
        sources = setup(writer, original)
        reader.execute('set role authenticated')
        results = {}
        for mode, source in zip(('original', 'one_statement'), sources, strict=True):
            writer.execute(source)
            assert writer.execute('select provolatile from pg_proc where oid=to_regprocedure(%s)', (WORKSPACE,)).fetchone() == ('v',)
            seed(writer)
            initial = read(reader)
            assert page(initial['transfers']) == dict(total='25', numbers=[], offset=25, limit=25, next_offset=None)
            assert page(initial['receipts']) == dict(total='26', numbers=['AP-26'], offset=25, limit=25, next_offset=None)
            first = read(reader, dict(QUERY, purchase_offset=0, transfer_offset=0))
            assert page(first['receipts'])['next_offset'] == 25 and page(first['transfers'])['next_offset'] is None
            assert observe_overlap(writer, reader, pool, commit=False) == initial
            during = observe_overlap(writer, reader, pool, commit=True)
            after = read(reader)
            assert page(after['transfers']) == dict(total='26', numbers=['T-26'], offset=25, limit=25, next_offset=None)
            expected_during = {'total': '25', 'numbers': ['T-26'] if mode == 'original' else [],
                               'offset': 25, 'limit': 25, 'next_offset': None}
            assert page(during['transfers']) == expected_during
            assert during['receipts'] == after['receipts'] == initial['receipts']
            second = read(reader, dict(QUERY, purchase_offset=0, transfer_offset=0))
            assert page(second['transfers'])['next_offset'] == 25
            names = page(second['transfers'])['numbers'] + page(after['transfers'])['numbers']
            assert len(names) == len(set(names)) == 26
            results[mode] = dict(before=page(initial['transfers']), during=page(during['transfers']),
                                 after=page(after['transfers']), receipt_second_page=page(after['receipts']),
                                 abort_unchanged=True, no_cross_page_duplicate=True)
        writer.execute(sources[0])
        assert writer.execute('select pg_get_functiondef(to_regprocedure(%s))', (WORKSPACE,)).fetchone()[0] == sources[0]
        return dict(status='EXACT_SUPPLIER_WORKSPACE_PAGE_BOUNDARIES_VERIFIED', cases=results,
                    fixture_AP_and_authorization=True, original_definition_restored=True, actual_ERP_cases=0)


if __name__ == '__main__':
    with cluster('cp7-pg17/package/native/bin') as ci:
        result = exercise(ci, 'cp7-intake/SKU_43132617378_ORIGINAL_FAILURE.zip')
    result['disposable_cluster_removed'] = True
    print(json.dumps(result, indent=2))
