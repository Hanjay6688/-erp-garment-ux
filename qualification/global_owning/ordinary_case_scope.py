"""Observe persisted changes between the reviewed case phases on the owning database."""

from scope_witness import capture, compare, outside_state

from .package_routes import require


PHASES = ('S05_SETUP', 'NATIVE_AND_COMMITTED_E', 'OW06_TRANSFER', 'AUTH_ORDINARY', 'OUTSIDE_REVERSE_AND_STALE')
DATABASE = 'cp6_rollback'


def bind(lifecycle):
    previous = None

    def observe(label, conn, cur, report, require_quiet):
        nonlocal previous
        phases = report.setdefault('case_relation_scope', {})
        names = lifecycle.relations
        require(len(names) == 461 and cur.connection is conn and not conn.autocommit,
                'GLOBAL_ORDINARY_SCOPE_EXACT_OBSERVER_REQUIRED')
        expected = 'START' if previous is None else PHASES[len(phases)]
        require(label == expected, 'GLOBAL_ORDINARY_SCOPE_PHASE_ORDER_CHANGED')
        require_quiet()
        with conn.transaction():
            cur.execute('set transaction isolation level repeatable read, read only')
            writes = capture(cur, expected_database=DATABASE, mode='database')
            rows_and_sequences = lifecycle.provider._timezone_snapshot(cur, lock=False)
        require_quiet()
        if previous is not None:
            old_writes, old_rows = previous
            proof = phases[label] = dict(status='INCOMPLETE')
            counters = compare(old_writes, writes, names)
            changed = outside_state(old_rows, rows_and_sequences, names)
            proof.update(counters=counters, fingerprints=changed,
                         database_oid=writes.database[1], origin_relation_count=len(names),
                         changed_tables=sorted(name for name in old_rows
                                               if not name.startswith('sequence:') and old_rows[name] != rows_and_sequences[name]))
            require(writes.temp_namespace == old_writes.temp_namespace == 0 and proof['changed_tables']
                    and not changed['changed_tables_outside_scope']
                    and not any(counters[key] for key in ('outside_write_attempts', 'relation_identity_changes',
                                                          'unexpected_temporary_relations')),
                    'GLOBAL_ORDINARY_CASE_PHASE_SCOPE_REFUSED:' + label)
            proof['status'] = 'OBSERVED_SCOPED_CHANGES'
        previous = writes, rows_and_sequences

    return observe
