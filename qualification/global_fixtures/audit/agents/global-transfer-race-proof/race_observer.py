"""Observe a selected-data snapshot and a writer on two actual backends."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
import json
from time import monotonic, sleep

from psycopg import sql
from psycopg.pq import TransactionStatus


PG_VERSION = 170006
WAIT_SECONDS = 5
LOCK_SECONDS = 25
STATEMENT_SECONDS = 30
OBSERVE = """
select jsonb_build_object(
    'sampled_at', clock_timestamp(), 'database_oid', a.datid::bigint,
    'reader_pid', a.pid, 'writer_pid', pg_backend_pid(),
    'backend_start', a.backend_start, 'query_start', a.query_start,
    'query', a.query, 'state', a.state, 'wait_type', a.wait_event_type,
    'wait_event', a.wait_event, 'blockers', pg_blocking_pids(a.pid),
    'reader_xid', a.backend_xid::text, 'reader_xmin', a.backend_xmin::text,
    'locks', (
        select jsonb_agg(jsonb_build_object(
            'pid', l.pid, 'database_oid', l.database::bigint, 'relation_oid', l.relation::bigint,
            'type', l.locktype, 'mode', l.mode, 'granted', l.granted,
            'transaction_id', l.transactionid::text, 'wait_start', l.waitstart
        ) order by l.pid, l.locktype, l.relation, l.mode)
        from pg_locks l where l.pid in (a.pid, pg_backend_pid())
    )
) from pg_stat_activity a where a.pid = %s
"""


class Refusal(ValueError):
    def __init__(self, reason, evidence=None):
        super().__init__(reason)
        self.evidence = evidence


def require(condition, reason, evidence=None):
    if not condition:
        raise Refusal(reason, evidence)


def idle(connection):
    require(connection.info.transaction_status == TransactionStatus.IDLE,
            "OW06_RACE_FRESH_IDLE_CONNECTION_REQUIRED")
    connection.autocommit = True
    return connection


def begin(connection, *, read_only):
    connection.execute("BEGIN ISOLATION LEVEL READ COMMITTED " + ("READ ONLY" if read_only else "READ WRITE"))
    connection.execute("select set_config('statement_timeout', %s, true), "
                       "set_config('lock_timeout', %s, true), "
                       "set_config('idle_in_transaction_session_timeout', '35s', true)",
                       (f"{STATEMENT_SECONDS}s", f"{LOCK_SECONDS}s" if read_only else "5s"))
    identity = connection.execute("""
        select pg_backend_pid(), d.oid::bigint, d.datname, pg_postmaster_start_time(),
               current_setting('server_version_num')::int, current_setting('transaction_isolation'),
               current_setting('transaction_read_only')
        from pg_database d where d.datname = current_database()
    """).fetchone()
    require(identity[4:] == (PG_VERSION, "read committed", "on" if read_only else "off"),
            "OW06_RACE_EXACT_PG176_READ_COMMITTED_REQUIRED", identity)
    return identity


def relation_oid(cur, relation):
    row = cur.execute("""
        select c.oid::bigint, c.relkind, c.relpersistence
        from pg_class c where c.oid = to_regclass(%s)
    """, (relation,)).fetchone()
    require(row is not None and row[1:] == ("r", "p"),
            "OW06_RACE_PERMANENT_TABLE_OID_REQUIRED", relation)
    return row[0]


def witness(cur, reader, writer, pause, prefix, statement, future):
    deadline = monotonic() + WAIT_SECONDS
    sample = None
    while monotonic() < deadline and not future.done():
        cur.execute("select pg_stat_clear_snapshot()")
        row = cur.execute(OBSERVE, (reader[0],)).fetchone()
        sample = row[0] if row else None
        if sample and sample["state"] == "active" and sample["wait_type"] == "Lock":
            locks = sample["locks"]
            relevant = [lock for lock in locks if lock["type"] == "relation" and lock["database_oid"] == reader[1]]
            held = {(lock["pid"], lock["relation_oid"], lock["mode"]) for lock in relevant if lock["granted"]}
            waiting = [lock for lock in relevant if lock["pid"] == reader[0] and not lock["granted"]]
            require(sample["database_oid"] == reader[1] and sample["writer_pid"] == writer[0]
                    and sample["query"] == statement and sample["wait_event"] == "relation"
                    and sample["blockers"] == [writer[0]] and len(waiting) == 1
                    and waiting[0]["relation_oid"] == pause and waiting[0]["mode"] == "AccessShareLock"
                    and (writer[0], pause, "AccessExclusiveLock") in held,
                    "OW06_RACE_EXACT_READER_WRITER_OID_WAIT_REQUIRED", sample)
            require(prefix <= {oid for pid, oid, mode in held if pid == reader[0] and mode == "AccessShareLock"}
                    and all(mode == "AccessShareLock" for pid, _, mode in held if pid == reader[0])
                    and sample["reader_xmin"] is not None and sample["reader_xid"] is None
                    and not any(lock["type"] == "transactionid" and lock["pid"] == reader[0] for lock in locks),
                    "OW06_RACE_POST_SNAPSHOT_PREFIX_AND_READ_ONLY_LOCKS_REQUIRED", sample)
            require(sample["query_start"] is not None and waiting[0]["wait_start"] is not None
                    and stamp(sample["query_start"]) <= stamp(waiting[0]["wait_start"]) <= stamp(sample["sampled_at"]),
                    "OW06_RACE_ORDERED_WAIT_TIMESTAMPS_REQUIRED", sample)
            return dict(activity=sample, wait_start=waiting[0]["wait_start"])
        sleep(0.025)
    if future.done():
        future.result()
    raise Refusal("OW06_RACE_BOUNDED_WAIT_NOT_OBSERVED", sample)


def stamp(value):
    return datetime.fromisoformat(value)


def reply_bytes(value):
    require(type(value) is dict and type(value.get("captured_at")) is str,
            "OW06_RACE_CAPTURED_REPLY_REQUIRED", value)
    return json.dumps({key: item for key, item in value.items() if key != "captured_at"},
                      sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()


def observe(connect, *, pause_relation, prefix_relations, reader_statement, read, write, terminal, database_anchor=None):
    """Stage the write and sample the same blocked query again before releasing it."""
    require(terminal in ("ABORT", "COMMIT") and prefix_relations and pause_relation not in prefix_relations,
            "OW06_RACE_EXACT_SCHEDULE_REQUIRED")
    with closing(connect()) as reader, closing(connect()) as writer, ThreadPoolExecutor(max_workers=1) as pool:
        idle(reader)
        idle(writer)
        initial = begin(reader, read_only=True)
        require(database_anchor is None or initial[1:5] == database_anchor,
                "OW06_RACE_EXACT_SAME_OWNING_DATABASE_REQUIRED")
        with reader.cursor() as cur:
            old = read(cur)
        reader.execute("ROLLBACK")
        rid = begin(reader, read_only=True)
        wid = begin(writer, read_only=False)
        require(rid[0] != wid[0] and initial[1:5] == rid[1:5] == wid[1:5],
                "OW06_RACE_DISTINCT_SAME_DATABASE_BACKENDS_REQUIRED")
        with writer.cursor() as cur:
            pause = relation_oid(cur, pause_relation)
            prefix = {relation_oid(cur, name) for name in prefix_relations}
            cur.execute(sql.SQL("LOCK TABLE ONLY {} IN ACCESS EXCLUSIVE MODE NOWAIT").format(
                sql.Identifier(*pause_relation.split("."))))

            def read_selected():
                with reader.cursor() as reader_cur:
                    return read(reader_cur)

            wait_before = wait_after = outcome = None
            try:
                future = pool.submit(read_selected)
                wait_before = witness(cur, rid, wid, pause, prefix, reader_statement, future)
                outcome = write(cur, old)
                staged = read(cur)
                wait_after = witness(cur, rid, wid, pause, prefix, reader_statement, future)
                before, after = wait_before["activity"], wait_after["activity"]
                writer_xids = [lock["transaction_id"] for lock in after["locks"] if lock["pid"] == wid[0]
                               and lock["type"] == "transactionid" and lock["mode"] == "ExclusiveLock" and lock["granted"]]
                require(all(before[key] == after[key] for key in ("backend_start", "query_start", "reader_xmin"))
                        and wait_before["wait_start"] == wait_after["wait_start"] and writer_xids,
                        "OW06_RACE_SAME_WAIT_MUST_SPAN_WRITER", (wait_before, wait_after))
                tag = cur.execute(terminal).statusmessage
                require(tag == ("COMMIT" if terminal == "COMMIT" else "ROLLBACK")
                        and writer.info.transaction_status == TransactionStatus.IDLE,
                        "OW06_RACE_EXACT_WRITER_TERMINAL_TAG_REQUIRED", tag)
                active = future.result(timeout=STATEMENT_SECONDS + 2)
            except BaseException as error:
                # Release the wait before the executor joins the reader thread.
                if writer.info.transaction_status != TransactionStatus.IDLE:
                    writer.execute("ROLLBACK")
                if not isinstance(error, Exception):
                    raise
                evidence = dict(before=wait_before, after=wait_after, staged_outcome=outcome,
                                sqlstate=getattr(error, "sqlstate", None), detail=getattr(error, "evidence", None))
                raise Refusal(str(error), evidence) from error
        reader.execute("ROLLBACK")
        begin(reader, read_only=True)
        with reader.cursor() as cur:
            following = read(cur)
        reader.execute("ROLLBACK")
        evidence = dict(terminal=terminal, command_tag=tag, reader_pid=rid[0], writer_pid=wid[0],
                        database_oid=rid[1], database=rid[2], pg_version=rid[4], isolation=rid[5],
                        pause_relation=pause_relation, pause_oid=pause, prefix_oids=sorted(prefix),
                        wait_before_writer=wait_before, wait_after_writer=wait_after,
                        writer_xids=writer_xids, writer_outcome=outcome, old=old, active=active,
                        staged=staged, following=following)
        require(reply_bytes(active) == reply_bytes(old)
                and stamp(active["captured_at"]) == stamp(wait_before["activity"]["query_start"])
                and reply_bytes(staged) != reply_bytes(old)
                and reply_bytes(following) == reply_bytes(staged if terminal == "COMMIT" else old),
                "OW06_RACE_OLD_ACTIVE_AND_FOLLOWING_SNAPSHOT_ORACLE_REQUIRED", evidence)
    return evidence
