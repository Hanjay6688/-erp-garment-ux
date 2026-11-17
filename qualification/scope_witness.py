"""Read PostgreSQL 17.6 relation-write evidence on an existing owning cursor."""

from dataclasses import dataclass
from hashlib import sha256
import json

from psycopg.pq import TransactionStatus


BASE = '8a08df4cb3a8c0f29731ec644be0748b4200e24998b5a36138ca0140098ac841'
S02_DELTA = '96a1b5b3ef05e5bdc30163ea6608271822f79b6f0afb701edbe7e1b79f48458b'
OPENING_CLAIM = 'erp.bd_opening_laundry_claim_events_v1'
FILING = 'erp.accounting_close_filings_v1'
RECOST_TEMP = 'pg_temp.erp_accessory_hpp_changed_pos'
COUNTERS = """
select c.oid, n.oid, n.nspname, c.relname, c.relkind, c.relpersistence,
       s.n_tup_ins, s.n_tup_upd, s.n_tup_del
from pg_catalog.{view} s
join pg_catalog.pg_class c on c.oid=s.relid
join pg_catalog.pg_namespace n on n.oid=c.relnamespace
where n.nspname not in ('pg_catalog','information_schema')
  and (n.nspname !~ '^pg_' or (c.relpersistence='t' and n.oid=pg_catalog.pg_my_temp_schema()))
order by c.oid
"""
CONTEXT = """
select d.oid, d.datname, pg_catalog.pg_backend_pid(), a.backend_start,
       pg_catalog.transaction_timestamp(), pg_catalog.pg_my_temp_schema(), s.stats_reset,
       pg_catalog.current_setting('server_version_num'),
       pg_catalog.current_setting('session_replication_role'),
       pg_catalog.current_setting('track_counts')
from pg_catalog.pg_database d
join pg_catalog.pg_stat_activity a on a.datid=d.oid and a.pid=pg_catalog.pg_backend_pid()
join pg_catalog.pg_stat_database s on s.datid=d.oid
where d.datname=pg_catalog.current_database()
"""
LOCAL_TEMP = """
select c.oid, c.relname, c.relkind
from pg_catalog.pg_class c
where c.relnamespace=pg_catalog.pg_my_temp_schema() and c.relpersistence='t'
  and c.relkind in ('r','p','m','S')
order by c.oid
"""


def require(condition, message):
    if not condition:
        raise ValueError(message)


def candidate_inputs(base_raw, delta_raw, *, opening_claim_or_visible_workspace=False, filing_read_or_close=False):
    """Return the reviewed static lower bound, with explicit scenario additions."""
    require(sha256(base_raw).hexdigest() == BASE and sha256(delta_raw).hexdigest() == S02_DELTA,
            'GLOBAL_WITNESS_PINNED_SCOPE_INPUTS_REQUIRED')
    base, delta = json.loads(base_raw), json.loads(delta_raw)
    names = base['relations']
    added = set(delta['direct_additions'])
    require(len(names) == 438 and names == sorted(set(names)) and len(added) == 5 and not added & set(names)
            and base['complete_input_review'] is False and delta['live_auth_and_observed_relation_scope_pending'] is True
            and delta['conditional_claim_source_peers'] == [OPENING_CLAIM]
            and delta['actual_close_filing_additional_relation'] == FILING
            and not {OPENING_CLAIM, FILING} & (set(names) | added), 'GLOBAL_WITNESS_STATIC_SCOPE_CHANGED')
    if opening_claim_or_visible_workspace:
        added.add(OPENING_CLAIM)
    if filing_read_or_close:
        added.add(FILING)
    return sorted(set(names) | added)


@dataclass(frozen=True)
class Observation:
    database: tuple
    backend: tuple
    transaction: object
    temp_namespace: int
    statistics_reset: object
    mode: str
    counters: dict
    temp_relations: dict


def other_clients(cur, application_name):
    """Give the observer client identities only, without SQL or payloads."""
    return cur.execute("""
        select pid, backend_start, usename, state, backend_xid is not null
        from pg_catalog.pg_stat_activity
        where datname=current_database() and pid<>pg_catalog.pg_backend_pid()
          and backend_type='client backend' and application_name=%s
        order by pid
    """, (application_name,)).fetchall()


def capture(cur, *, expected_database, mode):
    """Sample the current writer transaction or the current database counters."""
    connection = cur.connection
    require(connection.info.host in ('127.0.0.1', 'localhost') and mode in ('transaction', 'database'),
            'GLOBAL_WITNESS_LOCAL_CURSOR_AND_MODE_REQUIRED')
    if mode == 'transaction':
        status = connection.info.transaction_status
        require(status == TransactionStatus.INTRANS or (status == TransactionStatus.IDLE and not connection.autocommit),
                'GLOBAL_WITNESS_TRANSACTION_MODE_REQUIRES_EXISTING_WRITER_TRANSACTION')
    # Discard only this observer's cached cumulative statistics.
    cur.execute('select pg_catalog.pg_stat_clear_snapshot()')
    oid, name, pid, started, xact, namespace, reset, version, trigger_mode, track = cur.execute(CONTEXT).fetchone()
    require(name == expected_database and version == '170006' and trigger_mode == 'origin' and track == 'on',
            'GLOBAL_WITNESS_EXACT_DATABASE_OR_STATISTICS_REQUIRED')
    view = 'pg_stat_xact_all_tables' if mode == 'transaction' else 'pg_stat_all_tables'
    rows = cur.execute(COUNTERS.format(view=view)).fetchall()
    counters = {
        oid: ((f'pg_temp.{rel}' if persistence == 't' else f'{schema}.{rel}', kind, persistence, ns), (ins, upd, dele))
        for oid, ns, schema, rel, kind, persistence, ins, upd, dele in rows
    }
    temp_relations = {f'pg_temp.{name}': (oid, kind) for oid, name, kind in cur.execute(LOCAL_TEMP).fetchall()}
    return Observation((name, oid), (pid, started), xact, namespace, reset, mode, counters, temp_relations)


def compare(before, after, relations, *, allowed_temp=()):
    """Return scoped row attempts. Keep transport, row census and DDL checks."""
    require(before.database == after.database and before.mode == after.mode
            and before.statistics_reset == after.statistics_reset, 'GLOBAL_WITNESS_CAPTURE_BOUNDARY_CHANGED')
    if before.mode == 'transaction':
        require((before.backend, before.transaction) == (after.backend, after.transaction),
                'GLOBAL_WITNESS_WRITER_TRANSACTION_CHANGED')
    elif before.temp_relations or after.temp_relations:
        raise ValueError('GLOBAL_WITNESS_CUMULATIVE_OBSERVER_MUST_HAVE_NO_TEMP_RELATIONS')
    scope = set(relations)
    permitted_temp = set(allowed_temp)
    require(permitted_temp <= {RECOST_TEMP}, 'GLOBAL_WITNESS_UNREVIEWED_TEMPORARY_EXCEPTION')
    changed, outside, temp_attempts, identity = {}, {}, {}, []
    for oid in sorted(before.counters.keys() | after.counters.keys()):
        old = before.counters.get(oid)
        new = after.counters.get(oid)
        if (old and old[0][2] == 't') or (new and new[0][2] == 't'):
            if old and not new:
                continue
            require(old is None or old[0] == new[0], 'GLOBAL_WITNESS_TEMP_IDENTITY_CHANGED')
            name = new[0][0]
            old_counts = old[1] if old else (0, 0, 0)
            delta = tuple(right - left for left, right in zip(old_counts, new[1], strict=True))
            require(min(delta) >= 0, 'GLOBAL_WITNESS_TEMP_COUNTER_MOVED_BACKWARDS')
            if any(delta):
                temp_attempts[name] = delta
            continue
        if old is None or new is None or old[0] != new[0]:
            identity.append((old[0][0] if old else None, new[0][0] if new else None))
            continue
        name, _, _, _ = new[0]
        delta = tuple(right - left for left, right in zip(old[1], new[1], strict=True))
        require(min(delta) >= 0, 'GLOBAL_WITNESS_RELATION_COUNTER_MOVED_BACKWARDS ' + name)
        if any(delta):
            changed[name] = delta
            if name not in scope:
                outside[name] = delta
    return dict(mode=before.mode, write_attempts=changed, outside_write_attempts=outside,
                relation_identity_changes=identity, temporary_write_attempts=temp_attempts,
                removed_temporary_relations=sorted(before.temp_relations.keys() - after.temp_relations.keys()),
                unexpected_temporary_relations=sorted((before.temp_relations.keys() | after.temp_relations.keys()) - permitted_temp),
                counts_order=['insert', 'update', 'delete'])


def temp_terminal(staged, terminal):
    """Read the exact temporary table after COMMIT/ABORT on its original backend."""
    require(staged.database == terminal.database and staged.backend == terminal.backend
            and staged.transaction != terminal.transaction, 'GLOBAL_WITNESS_TEMP_TERMINAL_BACKEND_REQUIRED')
    require(set(staged.temp_relations) == {RECOST_TEMP}
            and staged.temp_relations[RECOST_TEMP][1] == 'r' and staged.temp_namespace != 0
            and not terminal.temp_relations, 'GLOBAL_WITNESS_EXACT_RECOST_TEMP_LIFECYCLE_REQUIRED')
    return dict(recost_table_removed=True, original_backend_observed=True,
                namespace_remains=terminal.temp_namespace != 0,
                fresh_backend_required_before_next_global_lock=terminal.temp_namespace != 0)


def outside_state(before, after, relations):
    """Compare all row/sequence fingerprints from the retained full snapshot."""
    require(before.keys() == after.keys(), 'GLOBAL_WITNESS_EXACT_COMPLETE_STATE_KEYS_REQUIRED')
    scope = set(relations)
    changed = {key for key, value in before.items() if after[key] != value}
    return dict(changed_tables_outside_scope=sorted(key for key in changed if key not in scope and not key.startswith('sequence:')),
                changed_sequences=sorted(key.removeprefix('sequence:') for key in changed if key.startswith('sequence:')))
