"""One transaction for the complete CP7 owner and bounded consumer extension.

The unchanged predecessor verifier runs before the source-derived consumer
delta. Subsequent administrative checks compare every installed catalog member
exactly, including all 22 existing backup catalog groups. They do not present
old definitions to a verifier or claim a raw legacy-verifier pass. No product
connection, commit, provider, scheduling, or production admission is performed.
"""
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path

from psycopg import sql

import cp7_full_owning_install as base
import cp7_ow04_restore_bundle as catalog
from cp7_customer_credit.consumer import composition as consumer

ROOT = Path(__file__).resolve().parents[1]
USED_ERROR = 'CP7_FULL_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE'


def sources():
    return dict(installer_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        base=base.source_manifest(), consumer=consumer.sources(),
        catalog_reader_sha256=sha256(Path(catalog.__file__).read_bytes()).hexdigest())


@contextmanager
def atomic(cur):
    """A nested savepoint; the caller's outer transaction is never committed."""
    if cur.connection.autocommit:
        raise ValueError('CP7_COMPOSED_CALLER_TRANSACTION_REQUIRED')
    # Start the caller's implicit transaction before entering transaction(), so
    # its exit is RELEASE SAVEPOINT even when the connection began idle.
    cur.execute('select txid_current()')
    with cur.connection.transaction():
        yield


def install(cur):
    with atomic(cur):
        source = sources()
        predecessor = base.install(cur)
        predecessor_proof = base.verify(cur, predecessor)
        extension = consumer.install(cur)
        installed_catalog = catalog._catalog_rows(cur)
        if set(installed_catalog) != set(catalog.QUERIES) or len(installed_catalog) != 22:
            raise ValueError('CP7_COMPOSED_COMPLETE_CATALOG_GROUP_SET_CHANGED')
        state = dict(sources=source, predecessor=predecessor,
            predecessor_proof_before_extension=predecessor_proof,
            consumer=extension, installed_catalog=installed_catalog,
            seeded_private_rows=base.private_rows(cur),
            production_go=False, formal_CP7C_started=False)
        verify(cur, state)
        return state


def verify(cur, state):
    """Exact current metadata after a verified source-owned install transition."""
    if state['sources'] != sources():
        raise ValueError('CP7_COMPOSED_PRODUCT_SOURCE_CHANGED')
    extension = consumer.verify(cur, state['consumer'])
    current = catalog._catalog_rows(cur)
    if current != state['installed_catalog']:
        changed = {kind:sorted(key for key in set(current.get(kind, {})) |
            set(state['installed_catalog'].get(kind, {}))
            if current.get(kind, {}).get(key) != state['installed_catalog'].get(kind, {}).get(key))
            for kind in set(current) | set(state['installed_catalog'])
            if current.get(kind) != state['installed_catalog'].get(kind)}
        raise ValueError('CP7_COMPOSED_INSTALLED_CATALOG_CHANGED: '+catalog.canonical(changed))
    return dict(classification='SOURCE_VALIDATED_COMPLETE_COMPOSED_CATALOG_NOT_RAW_LEGACY_PASS',
        catalog_groups=len(current), catalog_members=sum(map(len, current.values())),
        exact_catalog_sha256=catalog.digest(current), consumer=extension,
        predecessor_verified_before_source_derived_extension=True,
        legacy_definitions_projected=False, production_go=False,
        feature_complete=False, independent_acceptance=False)


def _lock_private_tables(cur, state):
    # Lock the complete installed private table set before the used-state test.
    # A writer cannot add a request/fact between that test and removal. Names
    # come from the already-verified source-owned installation, not a prefix
    # that is trusted to admit arbitrary objects.
    names = [name for name in state['installed_catalog']['relations']
        if name in state['seeded_private_rows']]
    if set(names) != set(state['seeded_private_rows']) or not names:
        raise ValueError('CP7_COMPOSED_PRIVATE_LOCK_SET_CHANGED')
    cur.execute(sql.SQL('lock table {} in access exclusive mode nowait').format(
        sql.SQL(',').join(sql.Identifier(*name.split('.')) for name in sorted(names))))


def rollback_preuse(cur, state):
    """Used base OR consumer refuses before any uninstall or destructive DDL."""
    with atomic(cur):
        verify(cur, state)
        _lock_private_tables(cur, state)
        if base.private_rows(cur) != state['seeded_private_rows']:
            raise ValueError(USED_ERROR)
        removed = consumer.uninstall_preuse(cur, state['consumer'])
        # After exact removal, run the original real predecessor verifier and
        # its own original pre-use guard. An error rolls the entire nested
        # savepoint back, including the consumer removal.
        predecessor_proof = base.verify(cur, state['predecessor'])
        base.rollback_preuse(cur, state['predecessor'])
        return dict(status='COMPLETE_COMPOSED_PREUSE_REMOVED', consumer=removed,
            predecessor_restored_verification=predecessor_proof,
            used_guard_before_any_uninstall=True, financial_facts_deleted=False,
            production_go=False)
