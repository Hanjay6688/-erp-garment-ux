"""Test archived supplier readers while a separate PostgreSQL session reverses the fixture transfer."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
from time import monotonic, sleep
from zipfile import ZipFile

from psycopg import connect
from psycopg.types.json import Jsonb

from loopback_postgres import cluster


AREA = Path(__file__).with_name('ow06-two-sessions')
NAMES = {
    'detail_v1': 'uuid',
    'child_detail_v1': 'uuid,jsonb',
    'review_v1': 'uuid,uuid',
}
GATE = 77241405
VALUES = {name: f'{index * 11111111:08d}-{index * 1111:04d}-{index * 1111:04d}-{index * 1111:04d}-{index * 111111111111:012d}'
          for index, name in enumerate(('transfer', 'purchase', 'supplier', 'payment', 'bank', 'journal', 'inverse'), 1)}
VALUES['timestamp'] = '2026-11-07T01:00:00Z'
AP = dict(id=VALUES['purchase'], number='AP-1', date='2026-11-07', final_ap='1000.00',
          paid='1.23', remaining='998.77', credit_delta='0.00', payment_status='PARTIAL_PAID')
INPUTS = {
    'detail_v1': (VALUES['transfer'],),
    'child_detail_v1': (VALUES['payment'], Jsonb(AP)),
    'review_v1': (VALUES['supplier'], VALUES['transfer']),
}


def pin(raw):
    return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def setup(conn):
    # Reuse the typed transfer, journal and AP fixture retained by the earlier
    # single-session replay. This time a separate backend does the writes.
    original = (AREA / 'replay_grouped.mjs').read_text()
    initial = original.split('try {\n  await db.exec(`', 1)[1].split('`)', 1)[0]
    sql = re.sub(r'\$\{(\w+)\}', lambda match: VALUES[match[1]], initial)
    conn.execute(sql, prepare=False)
    conn.execute(f"""create or replace function fixture.interleave(ident uuid) returns boolean
      language plpgsql volatile as $$
      begin
        if current_setting('fixture.reader_barrier', true) = 'on' then
          perform pg_advisory_xact_lock({GATE});
        end if;
        return true;
      end $$""")


def definitions(original):
    with ZipFile(original) as bundle:
        raw = bundle.read('SKU_GLOBAL_PARENT_ACTUAL_FULL25.json')
    assert pin(raw)['sha256'] == '5ff582717522b766c12024c1bf3299066475f14a3c6021a3543f378f829e0c07'
    recorded = dict(json.loads(raw)['functions'])
    results = {}
    for name, args in NAMES.items():
        signature = f'cp7_supplier_transfer.{name}({args})'
        sources = tuple((AREA / f'cp7_supplier_transfer.{name}.{kind}.sql').read_bytes()
                        for kind in ('preimage', 'replacement'))
        before, after = sources
        assert before.decode() == recorded[signature][0], signature
        assert before.count(b'\n SECURITY DEFINER\n') == 1
        assert before.replace(b'\n SECURITY DEFINER\n', b'\n STABLE SECURITY DEFINER\n', 1) == after
        results[name] = sources
    return results


def reset(conn):
    conn.execute("truncate fixture.transfers, erp.supplier_payments, erp.journal_entries")
    conn.execute("insert into fixture.transfers values (%s,'T-1',%s,'POSTED',%s,1.23,%s,'Catatan',%s)",
                 tuple(VALUES[k] for k in ('transfer', 'supplier', 'timestamp', 'bank', 'journal')))
    conn.execute("insert into erp.supplier_payments values (%s,%s,%s,1.23,'POSTED','PAY-1',%s)",
                 tuple(VALUES[k] for k in ('payment', 'purchase', 'bank', 'timestamp')))
    conn.execute("insert into erp.journal_entries values (%s,null,'J-1','POSTED','2026-11-07','2026-11-07',%s,false)",
                 tuple(VALUES[k] for k in ('journal', 'timestamp')))


def read(conn, name):
    arguments = ','.join('%s::' + kind for kind in NAMES[name].split(','))
    return conn.execute(f'select cp7_supplier_transfer.{name}({arguments})', INPUTS[name]).fetchone()[0]


def overlap(writer, reader, pool, name, commit):
    holder = writer.execute('select pg_backend_pid()').fetchone()[0]
    pid = reader.execute('select pg_backend_pid()').fetchone()[0]
    assert holder != pid
    reader.execute("set fixture.reader_barrier='on'")
    writer.execute('select pg_advisory_lock(%s)', (GATE,))
    pending = pool.submit(read, reader, name)
    try:
        deadline = monotonic() + 5
        while True:
            kind, event, blockers = writer.execute(
                "select wait_event_type,wait_event,pg_blocking_pids(pid) from pg_stat_activity where pid=%s",
                (pid,)).fetchone()
            if kind == 'Lock' and event == 'advisory':
                assert blockers == [holder]
                break
            assert not pending.done() and monotonic() < deadline, 'Reader missed the barrier'
            sleep(0.01)
        with writer.transaction(force_rollback=not commit):
            writer.execute('select fixture.reverse_transfer()')
        assert writer.execute('select status from fixture.transfers').fetchone()[0] == ('REVERSED' if commit else 'POSTED')
        assert not pending.done()
    finally:
        assert writer.execute('select pg_advisory_unlock(%s)', (GATE,)).fetchone() == (True,)
    value = pending.result(timeout=5)
    reader.execute("reset fixture.reader_barrier")
    assert reader.execute("show timezone").fetchone() == ('Asia/Jakarta',)
    return value


def exercise(conninfo, sources):
    with connect(**conninfo, autocommit=True) as writer, connect(**conninfo, autocommit=True) as reader, \
            ThreadPoolExecutor(max_workers=1) as pool:
        setup(writer)
        reader.execute("set timezone='Asia/Jakarta'")
        report = {}
        for variant, index in (('original', 0), ('stable', 1)):
            for pair in sources.values():
                writer.execute(pair[index].decode())
            report[variant] = {}
            for name in NAMES:
                reset(writer)
                before = read(reader, name)
                abort_read = overlap(writer, reader, pool, name, commit=False)
                assert abort_read == before == read(reader, name)
                racing = overlap(writer, reader, pool, name, commit=True)
                after = read(reader, name)
                assert before != after
                if variant == 'original':
                    assert racing != before and racing != after
                    if name == 'detail_v1':
                        assert racing['status'] == 'POSTED' and racing['journal']['status'] == 'REVERSED'
                    if name == 'child_detail_v1':
                        assert racing['transfer']['status'] == 'POSTED' and racing['status'] == 'REVERSED'
                else:
                    assert racing == before
                report[variant][name] = dict(definition=pin(sources[name][index]), writer_committed_while_reader_waited=True,
                                             transaction_abort_kept_before=True, read_matched_before=racing == before,
                                             next_read_matched_reversal=True)
        for pair in sources.values():
            writer.execute(pair[0].decode())
        for name, args in NAMES.items():
            signature = f'cp7_supplier_transfer.{name}({args})'
            assert writer.execute('select pg_get_functiondef(to_regprocedure(%s))', (signature,)).fetchone()[0].encode() == sources[name][0]
        return dict(status='PASS_EXACT_SUPPLIER_READERS_TWO_POSTGRESQL_SESSIONS', postgres=writer.execute('show server_version').fetchone()[0],
                    cases=report, original_definitions_restored=True, fixture_auth_and_ap=True, actual_ERP_cases=0)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pg', type=Path)
    p.add_argument('original', type=Path)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    sources = definitions(args.original)
    with cluster(args.pg) as conninfo:
        value = exercise(conninfo, sources)
    value['fixture_cluster_removed'] = True
    with args.output.open('x') as stream:
        stream.write(json.dumps(value, indent=2) + '\n')
    print(value['status'])


if __name__ == '__main__':
    main()
