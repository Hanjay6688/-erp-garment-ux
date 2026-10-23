"""P21 administrative entry point for the complete current OW-15 chain owner (top: OW-04b slice C).

The shape of cp7_p21_ow05_adapter.py with the chain top as owner. The caller owns the transaction. No connection,
commit, provider, schedule or production admission happens on import or through installation.

rollback_preuse adds one chain-wide guard before any DDL: every private table (all cp7_* schemas, every stage's own,
and the OW04 credit schemas) is locked ACCESS EXCLUSIVE NOWAIT, and any row that differs from the rows recorded right
after install refuses with CP7_FULL_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE. Each stage's own guard still runs inside
owner.rollback_preuse; the v_customer_receivables round-trip repair is the one of the OW05 adapter, unchanged.
"""
from hashlib import sha256
from pathlib import Path

from psycopg import sql

from cp7_credit_incoming import composition as owner
import cp7_chain_restore as recovery

ROOT=Path(__file__).resolve().parents[1]
catalog=owner.catalog
atomic=owner.atomic
base=recovery.ow05.predecessor.base
USED_ERROR='CP7_FULL_ROLLBACK_AFTER_USE_REQUIRES_BACKUP_RESTORE'
RECEIVABLES='erp.v_customer_receivables'
ARRAY_CAST="ANY ((ARRAY['POSTED'::character varying, 'PARTIAL_PAID'::character varying, 'PAID'::character varying])::text[])"
ARRAY_ELEMENTS="ANY (ARRAY[('POSTED'::character varying)::text, ('PARTIAL_PAID'::character varying)::text, ('PAID'::character varying)::text])"
ARRAY_IMPLICIT="ANY (ARRAY['POSTED'::character varying, 'PARTIAL_PAID'::character varying, 'PAID'::character varying])"


def sources():
    return dict(financial_product=owner.sources(),administrative_restore=recovery.sources(),
        adapter_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        default_P21_entrypoint_sha256=sha256((ROOT/'scripts/cp7_p21_full_rehearsal_probe.py').read_bytes()).hexdigest())


def chain():
    """The fixed chain from the top to OW05; catalog, atomic and the private-row reader are the OW05 ones."""
    modules=recovery.chain_modules()
    ow05=recovery.ow05
    if catalog is not ow05.predecessor.catalog or atomic is not ow05.predecessor.atomic or base is not ow05.predecessor.base:
        raise ValueError('P21_CHAIN_SHARED_INTERFACE_CHANGED')
    return modules


def install(cur):
    chain()
    before=catalog._catalog_rows(cur)
    state=owner.install(cur)
    state['p21_preinstall_catalog']=before
    state['installed_catalog']=state['after']  # Same full 22-group catalog, no projection.
    if catalog._catalog_rows(cur)!=state['installed_catalog']:raise ValueError('P21_CHAIN_INSTALLED_CATALOG_CHANGED')
    # Every private table of every stage (all cp7_* schemas and the OW04 credit schemas), right after install.
    state['p21_seeded_private_rows']=base.private_rows(cur)
    recovery.ow05_state(state)
    return state


def verify(cur,state):return owner.verify(cur,state)


def _lock_private_tables(cur,state):
    # Names come from the verified installed catalog, never from a trusted prefix alone.
    names=sorted(state['p21_seeded_private_rows'])
    if not names or any(name not in state['installed_catalog']['relations']for name in names):
        raise ValueError('P21_CHAIN_PRIVATE_LOCK_SET_CHANGED')
    cur.execute(sql.SQL('lock table {} in access exclusive mode nowait').format(
        sql.SQL(',').join(sql.Identifier(*name.split('.'))for name in names)))


def rollback_preuse(cur,state):
    with atomic(cur):
        chain()
        verify(cur,state)
        _lock_private_tables(cur,state)
        # Global "already used" guard before any DDL: a changed, added or removed row anywhere refuses.
        if base.private_rows(cur)!=state['p21_seeded_private_rows']:
            raise ValueError(USED_ERROR)
        before=state['p21_preinstall_catalog']
        removed=owner.rollback_preuse(cur,state)
        after=catalog._catalog_rows(cur)
        if after!=before:
            # PostgreSQL's view deparser renders this implicit array coercion
            # as an explicit cast. Re-parsing that text pushes casts into the
            # elements. Restore the original parse using its implicit cast;
            # do not normalize or ignore either catalog representation.
            changes={group:{key for key in set(before[group])|set(after[group])
                if before[group].get(key)!=after[group].get(key)}
                for group in before if before[group]!=after[group]}
            if changes!={'relations':{RECEIVABLES},'rules':{RECEIVABLES+':_RETURN'}}:
                raise ValueError('P21_PREUSE_UNDECLARED_CATALOG_CHANGE')
            for group,key,index in (('relations',RECEIVABLES,9),('rules',RECEIVABLES+':_RETURN',3)):
                old,new=before[group][key],after[group][key]
                wanted=old.copy()
                if old[index].count(ARRAY_CAST)!=1:
                    raise ValueError('P21_PREUSE_ORIGINAL_VIEW_ARRAY_SOURCE_CHANGED')
                wanted[index]=old[index].replace(ARRAY_CAST,ARRAY_ELEMENTS)
                if new!=wanted:
                    raise ValueError('P21_PREUSE_VIEW_ROUNDTRIP_NOT_DECLARED')
            definition=before['relations'][RECEIVABLES][9].replace(ARRAY_CAST,ARRAY_IMPLICIT)
            cur.execute('create or replace view erp.v_customer_receivables with(security_invoker=true)as '+definition,
                prepare=False)
            if catalog._catalog_rows(cur)!=before:
                raise ValueError('P21_PREUSE_ORIGINAL_FULL_CATALOG_NOT_RESTORED')
        return dict(**removed,p21_original_all22_catalog_groups_equal=True,
            catalog_comparison_not_normalized=True,p21_chain_used_guard_before_any_DDL=True,
            p21_chain_private_tables_locked_nowait=len(state['p21_seeded_private_rows']))


def export_manifest(cur,state):return recovery.export_manifest(cur,state)


def rebind_restored(cur,backup,expected_sha256,*,expected_database):
    return recovery.rebind_restored(cur,backup,expected_sha256,expected_database=expected_database)
